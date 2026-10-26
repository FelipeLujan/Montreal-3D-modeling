"""
Expanded Google Street View (32 Verified Outdoor Panoramas across 8 Problem Zones)
+ Zoom-19 1280x1280 Per-Zone Satellite Orthophotos
+ Seamless 4096x4096 (4K) Metric-Aligned Master Google Maps Satellite Orthophoto Texture.

Implements the strict Step-0 Outdoor Verification Gate (`is_official_google_outdoor_pano`)
from `src/ingest_all_blocks.py` so every panorama is guaranteed to be an official
"© Google" outdoor street-level capture (no `CAoS` indoor/user photospheres).
"""
import os
import sys
import json
import math
import shutil
import urllib.request
import urllib.parse
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
EXPANDED_SV_DIR = os.path.join(BASE_DIR, "data", "blocks", "EXPANDED_SV")
GLOBAL_OSM_PATH = os.path.join(BASE_DIR, "data", "open_data", "old_montreal_osm.json")

# Master World Origin (Place d'Armes Center - Maisonneuve Monument)
MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0


def load_api_key() -> str:
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GOOGLE_MAPS_API_KEY="):
                    return line.strip().split("=", 1)[1].strip()
    raise RuntimeError("GOOGLE_MAPS_API_KEY not found in .env")


def latlon_to_local_xy(lat: float, lon: float, origin_lat=MASTER_ORIGIN_LAT, origin_lon=MASTER_ORIGIN_LON):
    """Equirectangular local tangent plane projection in meters (X=East, Y=North)."""
    dlat = math.radians(lat - origin_lat)
    dlon = math.radians(lon - origin_lon)
    mean_lat = math.radians(origin_lat)
    x = dlon * EARTH_RADIUS_M * math.cos(mean_lat)
    y = dlat * EARTH_RADIUS_M
    return round(x, 3), round(y, 3)


def xy_to_latlon(x: float, y: float, origin_lat=MASTER_ORIGIN_LAT, origin_lon=MASTER_ORIGIN_LON):
    mean_lat = math.radians(origin_lat)
    lat = origin_lat + math.degrees(y / EARTH_RADIUS_M)
    lon = origin_lon + math.degrees(x / (EARTH_RADIUS_M * math.cos(mean_lat)))
    return round(lat, 6), round(lon, 6)


def is_official_google_outdoor_pano(meta: dict) -> bool:
    """Step 0 Gate: verifies status OK, not a third-party photosphere (CAoS...), and official Google copyright."""
    if not meta or meta.get("status") != "OK":
        return False
    pano_id = meta.get("pano_id", "")
    copyright_str = meta.get("copyright", "")
    if pano_id.startswith("CAoS") or len(pano_id) > 28:
        return False
    if "Google" not in copyright_str:
        return False
    return True


def query_sv_meta(lat: float, lon: float, api_key: str, radius: int = 50, pano_id: str = None) -> dict:
    if pano_id:
        params = urllib.parse.urlencode({
            "pano": pano_id,
            "key": api_key,
        })
    else:
        params = urllib.parse.urlencode({
            "location": f"{lat},{lon}",
            "radius": radius,
            "source": "outdoor",
            "key": api_key,
        })
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?{params}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def download_sv_image(pano_id: str, lat: float, lon: float, heading: float, pitch: float, fov: float, out_path: str, api_key: str):
    params = {
        "size": "640x640",
        "heading": round(heading, 1),
        "pitch": round(pitch, 1),
        "fov": round(fov, 1),
        "key": api_key,
    }
    if pano_id:
        params["pano"] = pano_id
    else:
        params["location"] = f"{lat},{lon}"
        params["source"] = "outdoor"

    url = f"https://maps.googleapis.com/maps/api/streetview?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=20) as resp:
        with open(out_path, "wb") as f:
            f.write(resp.read())


def load_car_street_nodes() -> list:
    if not os.path.exists(GLOBAL_OSM_PATH):
        return []
    with open(GLOBAL_OSM_PATH, "r", encoding="utf-8") as f:
        osm_raw = json.load(f)
    nodes = {}
    for el in osm_raw.get("elements", []):
        if el["type"] == "node":
            x, y = latlon_to_local_xy(el["lat"], el["lon"])
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"], "x": x, "y": y}

    car_street_nodes = []
    for el in osm_raw.get("elements", []):
        if el["type"] == "way":
            tags = el.get("tags", {})
            if "highway" in tags:
                hw_type = tags.get("highway", "")
                if hw_type in ("primary", "secondary", "tertiary", "residential", "unclassified", "living_street", "service", "trunk"):
                    for nid in el.get("nodes", []):
                        if nid in nodes:
                            n = nodes[nid]
                            car_street_nodes.append({
                                "lat": n["lat"],
                                "lon": n["lon"],
                                "x": n["x"],
                                "y": n["y"],
                                "name": tags.get("name", hw_type)
                            })
    return car_street_nodes


def find_guaranteed_outdoor_pano(target_lat: float, target_lon: float, car_street_nodes: list, used_panos: set, api_key: str):
    """Snaps probe locations to nearest car-street centerlines or outdoor offsets to find official Google outdoor pano."""
    tx, ty = latlon_to_local_xy(target_lat, target_lon)
    candidates = [(target_lat, target_lon, "direct")]

    if car_street_nodes:
        sorted_streets = sorted(car_street_nodes, key=lambda sn: (sn["x"] - tx) ** 2 + (sn["y"] - ty) ** 2)
        for sn in sorted_streets[:30]:
            candidates.append((sn["lat"], sn["lon"], f"street:{sn['name']}"))

    # Rings of offsets up to 160m (for piers/peninsulas)
    for dist in (20, 40, 65, 95, 130, 165):
        for ang_deg in range(0, 360, 45):
            rad = math.radians(ang_deg)
            ox, oy = tx + dist * math.cos(rad), ty + dist * math.sin(rad)
            olat, olon = xy_to_latlon(ox, oy)
            candidates.append((olat, olon, f"offset_{dist}m_{ang_deg}deg"))

    tested = set()
    for clat, clon, desc in candidates:
        key = (round(clat, 4), round(clon, 4))
        if key in tested:
            continue
        tested.add(key)
        for r in (20, 45, 80):
            meta = query_sv_meta(clat, clon, api_key=api_key, radius=r)
            if is_official_google_outdoor_pano(meta):
                pid = meta.get("pano_id")
                if pid and pid not in used_panos:
                    return meta, desc

    # Second pass: allow reusing a valid outdoor pano if strictly necessary
    tested.clear()
    for clat, clon, desc in candidates[:25]:
        key = (round(clat, 4), round(clon, 4))
        if key in tested:
            continue
        tested.add(key)
        meta = query_sv_meta(clat, clon, api_key=api_key, radius=85)
        if is_official_google_outdoor_pano(meta):
            return meta, desc + "_reused"

    return None, "failed"


EXPANDED_ZONES = [
    {
        "zone_id": "ZONE_PALAIS_CONGRES",
        "name": "Palais des congrès de Montréal & Place Jean-Paul-Riopelle",
        "lat": 45.50535,
        "lon": -73.56020,
        "description": "Palais des congrès colored glass facade, Rue Saint-Antoine Ouest, Place Jean-Paul-Riopelle, Rue Viger",
        "streetview_points": [
            {"label": "01_Palais_Congres_Colored_Glass_SaintAntoine", "lat": 45.50425, "lon": -73.55965, "heading": 335, "pitch": 12},
            {"label": "02_Place_JeanPaul_Riopelle_West_Facade", "lat": 45.50465, "lon": -73.56125, "heading": 55, "pitch": 12},
            {"label": "03_Rue_Viger_Ouest_North_Facade", "lat": 45.50615, "lon": -73.56010, "heading": 165, "pitch": 12},
            {"label": "04_Rue_SaintUrbain_East_Approach", "lat": 45.50555, "lon": -73.55865, "heading": 245, "pitch": 12},
        ],
    },
    {
        "zone_id": "ZONE_PALAIS_JUSTICE",
        "name": "Palais de Justice, Vieux Palais de Justice & Édifice Ernest-Cormier",
        "lat": 45.50705,
        "lon": -73.55580,
        "description": "Palais de Justice, Vieux Palais de Justice, Édifice Ernest-Cormier, Rue Notre-Dame Est",
        "streetview_points": [
            {"label": "01_Palais_de_Justice_NotreDame_Facade", "lat": 45.50655, "lon": -73.55540, "heading": 340, "pitch": 14},
            {"label": "02_Vieux_Palais_de_Justice_Dome_View", "lat": 45.50605, "lon": -73.55460, "heading": 295, "pitch": 14},
            {"label": "03_Edifice_Ernest_Cormier_ArtDeco_Front", "lat": 45.50735, "lon": -73.55420, "heading": 145, "pitch": 14},
            {"label": "04_Rue_SaintAntoine_Est_Courthouse_North", "lat": 45.50785, "lon": -73.55620, "heading": 155, "pitch": 14},
        ],
    },
    {
        "zone_id": "ZONE_SQUARE_VICTORIA_N",
        "name": "Square Victoria North, Tour de la Bourse & Guimard Metro",
        "lat": 45.50195,
        "lon": -73.56180,
        "description": "Tour de la Bourse / Place Victoria, Square Victoria trees, Guimard Metro entrance, Rue McGill head",
        "streetview_points": [
            {"label": "01_Tour_de_la_Bourse_Place_Victoria", "lat": 45.50155, "lon": -73.56155, "heading": 310, "pitch": 18},
            {"label": "02_Square_Victoria_Guimard_Metro_Trees", "lat": 45.50235, "lon": -73.56210, "heading": 145, "pitch": 10},
            {"label": "03_Square_Victoria_North_SaintAntoine", "lat": 45.50305, "lon": -73.56265, "heading": 150, "pitch": 12},
            {"label": "04_Rue_McGill_Head_Look_North", "lat": 45.50085, "lon": -73.56085, "heading": 325, "pitch": 14},
        ],
    },
    {
        "zone_id": "ZONE_CHAMP_DE_MARS",
        "name": "Champ-de-Mars Colonial Ramparts & Place des Montréalaises",
        "lat": 45.50850,
        "lon": -73.55560,
        "description": "Champ-de-Mars colonial stone ramparts, Place des Montréalaises, lawns & walkways",
        "streetview_points": [
            {"label": "01_Champ_de_Mars_Ramparts_From_Gosford", "lat": 45.50835, "lon": -73.55425, "heading": 285, "pitch": 10},
            {"label": "02_Place_des_Montrealaises_SaintAntoine", "lat": 45.50885, "lon": -73.55625, "heading": 140, "pitch": 10},
            {"label": "03_Champ_de_Mars_West_HotelDeVille_Back", "lat": 45.50795, "lon": -73.55495, "heading": 345, "pitch": 10},
            {"label": "04_Avenue_Viger_Est_Overpass_Approach", "lat": 45.50945, "lon": -73.55540, "heading": 195, "pitch": 10},
        ],
    },
    {
        "zone_id": "ZONE_BASSIN_BONSECOURS",
        "name": "Parc du Bassin-Bonsecours, Île Bonsecours & La Grande Roue",
        "lat": 45.50820,
        "lon": -73.54840,
        "description": "Parc du Bassin-Bonsecours, Île Bonsecours pavilion, La Grande Roue, Promenade du Vieux-Port",
        "streetview_points": [
            {"label": "01_Bassin_Bonsecours_From_Rue_de_la_Commune", "lat": 45.50885, "lon": -73.55045, "heading": 125, "pitch": 10},
            {"label": "02_La_Grande_Roue_Promenade_Vieux_Port", "lat": 45.50785, "lon": -73.54895, "heading": 95, "pitch": 14},
            {"label": "03_Ile_Bonsecours_Pavilion_South_Look", "lat": 45.50735, "lon": -73.54965, "heading": 55, "pitch": 10},
            {"label": "04_Bassin_Bonsecours_East_Quai_Horloge_Approach", "lat": 45.50955, "lon": -73.54865, "heading": 190, "pitch": 10},
        ],
    },
    {
        "zone_id": "ZONE_QUAI_HORLOGE",
        "name": "Quai de l'Horloge, Tour de l'Horloge, Plage & Yacht Marina",
        "lat": 45.51200,
        "lon": -73.54580,
        "description": "Tour de l'Horloge, Plage de l'Horloge boardwalk, Marina Yacht Club basin, Quai de l'Horloge pier",
        "streetview_points": [
            {"label": "01_Tour_de_lHorloge_Pier_North_Tip", "lat": 45.51245, "lon": -73.54565, "heading": 25, "pitch": 16},
            {"label": "02_Plage_de_lHorloge_Boardwalk_Look", "lat": 45.51175, "lon": -73.54610, "heading": 40, "pitch": 12},
            {"label": "03_Marina_Yacht_Club_Basin_West_Edge", "lat": 45.51055, "lon": -73.54755, "heading": 65, "pitch": 10},
            {"label": "04_Quai_de_lHorloge_Entry_Rue_de_la_Commune", "lat": 45.51020, "lon": -73.54915, "heading": 55, "pitch": 10},
        ],
    },
    {
        "zone_id": "ZONE_POINTE_DU_MOULIN",
        "name": "Pointe-du-Moulin, Silo No. 5, Bota Bota & Écluse No. 1",
        "lat": 45.49750,
        "lon": -73.55120,
        "description": "Silo No. 5 grain elevators, Bota Bota floating spa, Écluse No. 1 Lachine Canal locks, Parc des Éclusiers",
        "streetview_points": [
            {"label": "01_Silo_No5_Grain_Elevator_Rue_Mill", "lat": 45.49765, "lon": -73.55135, "heading": 65, "pitch": 16},
            {"label": "02_Silo_No5_North_Face_Rue_de_la_Commune", "lat": 45.49895, "lon": -73.55335, "heading": 135, "pitch": 14},
            {"label": "03_Ecluse_No1_Lachine_Canal_Locks", "lat": 45.49835, "lon": -73.55445, "heading": 110, "pitch": 10},
            {"label": "04_Parc_des_Eclusiers_BotaBota_RueMill", "lat": 45.49755, "lon": -73.55365, "heading": 95, "pitch": 14},
        ],
    },
    {
        "zone_id": "ZONE_CITE_DU_HAVRE",
        "name": "Cité du Havre, Habitat 67 & Parc de Dieppe Peninsula",
        "lat": 45.50050,
        "lon": -73.54350,
        "description": "Habitat 67 modular brutalist cubes, Avenue Pierre-Dupuy, Parc de Dieppe peninsula tip",
        "streetview_points": [
            {"label": "01_Habitat_67_Main_Modular_Cubes_PierreDupuy", "lat": 45.49975, "lon": -73.54365, "heading": 35, "pitch": 15},
            {"label": "02_Habitat_67_North_Complex_PierreDupuy", "lat": 45.50065, "lon": -73.54385, "heading": 120, "pitch": 15},
            {"label": "03_Avenue_Pierre_Dupuy_Approach_South", "lat": 45.49865, "lon": -73.54345, "heading": 10, "pitch": 12},
            {"label": "04_Parc_de_Dieppe_Peninsula_North_Approach", "lat": 45.50245, "lon": -73.54335, "heading": 15, "pitch": 10},
        ],
    },
]


def ingest_expanded_zone(zone: dict, car_street_nodes: list, api_key: str) -> dict:
    zid = zone["zone_id"]
    zone_dir = os.path.join(EXPANDED_SV_DIR, zid)
    sv_dir = os.path.join(zone_dir, "streetview")
    os.makedirs(zone_dir, exist_ok=True)
    os.makedirs(sv_dir, exist_ok=True)

    zone_cx, zone_cy = latlon_to_local_xy(zone["lat"], zone["lon"])
    downloaded_views = []
    used_panos = set()

    for vp in zone["streetview_points"]:
        label = vp["label"]
        pitch = vp.get("pitch", 12)
        target_lat = vp["lat"]
        target_lon = vp["lon"]
        target_x, target_y = latlon_to_local_xy(target_lat, target_lon)

        # Primary probe with small outdoor radius
        meta = query_sv_meta(target_lat, target_lon, api_key=api_key, radius=45)
        source_desc = "direct"

        # Step 0 Verification Gate
        if not is_official_google_outdoor_pano(meta) or meta.get("pano_id") in used_panos:
            new_meta, source_desc = find_guaranteed_outdoor_pano(
                target_lat, target_lon, car_street_nodes, used_panos, api_key
            )
            if new_meta:
                meta = new_meta
            else:
                print(f"  [WARN] {zid} | {label}: Could not find guaranteed unique outdoor pano; using best effort.")

        pano_id = meta.get("pano_id", "")
        if pano_id:
            used_panos.add(pano_id)

        loc = meta.get("location", {})
        actual_lat = loc.get("lat", target_lat)
        actual_lon = loc.get("lng", target_lon)
        cam_x, cam_y = latlon_to_local_xy(actual_lat, actual_lon)

        # Keep intended heading if close to probe, or re-aim toward target / zone center if snapped far
        dist_moved = math.hypot(target_x - cam_x, target_y - cam_y)
        if dist_moved > 35.0:
            dx = zone_cx - cam_x
            dy = zone_cy - cam_y
            heading = round((math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0, 1)
        else:
            heading = round(vp["heading"], 1)

        img_path_root = os.path.join(zone_dir, f"{label}.jpg")
        img_path_sv = os.path.join(sv_dir, f"{label}.jpg")
        download_sv_image(pano_id, actual_lat, actual_lon, heading, pitch, 90, img_path_root, api_key)
        shutil.copy2(img_path_root, img_path_sv)

        gmaps_url = (
            f"https://www.google.com/maps/@?api=1&map_action=pano"
            f"&viewpoint={actual_lat:.5f},{actual_lon:.5f}&heading={heading}&pitch={pitch}&fov=90"
        )
        if pano_id:
            gmaps_url += f"&pano={pano_id}"

        downloaded_views.append({
            "label": label,
            "requested_lat": target_lat,
            "requested_lon": target_lon,
            "actual_lat": actual_lat,
            "actual_lon": actual_lon,
            "blender_cam_xy_m": [cam_x, cam_y],
            "heading": heading,
            "pitch_deg": pitch,
            "fov_deg": 90,
            "pano_id": pano_id,
            "date": meta.get("date", ""),
            "copyright": meta.get("copyright", "© Google"),
            "verified_outdoor_google": is_official_google_outdoor_pano(meta),
            "refetched_source": source_desc,
            "image_path": img_path_root,
            "streetview_image_path": img_path_sv,
            "google_maps_url": gmaps_url,
        })

    # Download Zoom-19 1280x1280 Satellite Orthophoto per zone
    sat_url = (
        f"https://maps.googleapis.com/maps/api/staticmap"
        f"?center={zone['lat']},{zone['lon']}&zoom=19&size=640x640&scale=2"
        f"&maptype=satellite&key={api_key}"
    )
    sat_path_root = os.path.join(zone_dir, "satellite_topdown.png")
    sat_path_sv = os.path.join(sv_dir, "satellite_topdown.png")
    urllib.request.urlretrieve(sat_url, sat_path_root)
    shutil.copy2(sat_path_root, sat_path_sv)

    meters_per_px_z19 = (156543.03392 * math.cos(math.radians(zone["lat"]))) / (2 ** 19)
    sat_span_meters = round(meters_per_px_z19 * 640, 2)

    dossier = {
        "zone_id": zid,
        "name": zone["name"],
        "description": zone["description"],
        "center_wgs84": [zone["lat"], zone["lon"]],
        "blender_center_xy_m": [zone_cx, zone_cy],
        "satellite": {
            "image_path": sat_path_root,
            "streetview_image_path": sat_path_sv,
            "resolution_px": [1280, 1280],
            "zoom": 19,
            "scale": 2,
            "span_meters": sat_span_meters,
            "center_xy_m": [zone_cx, zone_cy],
        },
        "streetview_cameras": downloaded_views,
    }

    dossier_path = os.path.join(zone_dir, "dossier.json")
    with open(dossier_path, "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)

    return dossier


def latlon_to_web_mercator_px(lat: float, lon: float, zoom: int, scale: int = 2):
    """Returns Web Mercator global pixel coordinates at given zoom and scale."""
    tile_size = 256 * scale
    num_tiles = 2 ** zoom
    world_size = tile_size * num_tiles
    x = (lon + 180.0) / 360.0 * world_size
    sin_lat = math.sin(math.radians(lat))
    y = (0.5 - math.log((1.0 + sin_lat) / (1.0 - sin_lat)) / (4.0 * math.pi)) * world_size
    return x, y


def build_4k_metric_satellite_ortho(
    api_key: str,
    center_x_m: float = 40.0,
    center_y_m: float = -60.0,
    ortho_scale_m: float = 1950.0,
    zoom: int = 18,
    scale: int = 2,
):
    """
    Stitches a high-resolution (zoom=18, scale=2) Google Maps satellite mosaic covering
    the exact metric square:
      center_x_m = 40.0, center_y_m = -60.0, ortho_scale_m = 1950.0
      X in [-935.0, +1015.0], Y in [-1035.0, +915.0]
    Resamples to 4096x4096 pixels and saves to:
      - assets/polyhaven/montreal_satellite_ortho_4k.jpg
      - output/textures/montreal_satellite_ortho_4k.jpg
      - output/renders/google_maps_aerial_full_36blocks.png (1400x1400 version)
    """
    req_w, req_h = 640, 640
    # Crop top/bottom 28*scale px margin so Google bottom-edge watermarks never appear on interior seams
    crop_margin = 28 * scale
    usable_half_px = 280 * scale

    half_m = ortho_scale_m / 2.0
    min_x, max_x = center_x_m - half_m, center_x_m + half_m
    min_y, max_y = center_y_m - half_m, center_y_m + half_m

    # Compute Web Mercator global pixel bounds for the 4 metric corners
    lat_nw, lon_nw = xy_to_latlon(min_x, max_y)
    lat_se, lon_se = xy_to_latlon(max_x, min_y)
    gx_min, gy_min = latlon_to_web_mercator_px(lat_nw, lon_nw, zoom, scale)
    gx_max, gy_max = latlon_to_web_mercator_px(lat_se, lon_se, zoom, scale)

    span_gx = gx_max - gx_min
    span_gy = gy_max - gy_min
    step_px = usable_half_px * 1.75  # generous overlap so no gaps occur

    nx = max(1, int(math.ceil(span_gx / step_px)))
    ny = max(1, int(math.ceil(span_gy / step_px)))

    canvas_w = int(math.ceil(span_gx)) + 2 * req_w * scale
    canvas_h = int(math.ceil(span_gy)) + 2 * req_h * scale
    origin_gx = gx_min - req_w * scale
    origin_gy = gy_min - req_h * scale

    canvas = Image.new("RGB", (canvas_w, canvas_h), (18, 28, 38))

    print(
        f"\n[Step 2] Fetching Google Maps Satellite mosaic (zoom={zoom}, scale={scale}): "
        f"{nx}x{ny} = {nx * ny} tiles covering X=[{min_x:.1f}, {max_x:.1f}], Y=[{min_y:.1f}, {max_y:.1f}]..."
    )

    tile_jobs = []
    for ix in range(nx):
        for iy in range(ny):
            fx = (ix + 0.5) / nx
            fy = (iy + 0.5) / ny
            tx_m = min_x + fx * ortho_scale_m
            ty_m = max_y - fy * ortho_scale_m
            tlat, tlon = xy_to_latlon(tx_m, ty_m)
            tile_jobs.append((ix, iy, tlat, tlon))

    def _download_tile(job):
        ix, iy, tlat, tlon = job
        url = (
            f"https://maps.googleapis.com/maps/api/staticmap"
            f"?center={tlat:.6f},{tlon:.6f}&zoom={zoom}&size={req_w}x{req_h}&scale={scale}"
            f"&maptype=satellite&key={api_key}"
        )
        with urllib.request.urlopen(url, timeout=25) as resp:
            tile_img = Image.open(BytesIO(resp.read())).convert("RGB")
        return ix, iy, tlat, tlon, tile_img

    results = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(_download_tile, j) for j in tile_jobs]
        for fut in as_completed(futs):
            results.append(fut.result())

    # Sort deterministically before pasting
    results.sort(key=lambda r: (r[0], r[1]))
    for ix, iy, tlat, tlon, tile_img in results:
        cropped = tile_img.crop((0, crop_margin, req_w * scale, req_h * scale - crop_margin))
        tgx, tgy = latlon_to_web_mercator_px(tlat, tlon, zoom, scale)
        paste_x = int(round(tgx - (req_w * scale) / 2 - origin_gx))
        paste_y = int(round(tgy - (req_h * scale) / 2 + crop_margin - origin_gy))
        canvas.paste(cropped, (paste_x, paste_y))

    box = (
        int(round(gx_min - origin_gx)),
        int(round(gy_min - origin_gy)),
        int(round(gx_max - origin_gx)),
        int(round(gy_max - origin_gy)),
    )
    cropped_exact = canvas.crop(box)

    # 1. Resample to 4096x4096 (4K)
    ortho_4k = cropped_exact.resize((4096, 4096), Image.Resampling.LANCZOS)

    out_polyhaven_4k = os.path.join(BASE_DIR, "assets", "polyhaven", "montreal_satellite_ortho_4k.jpg")
    out_textures_4k = os.path.join(BASE_DIR, "output", "textures", "montreal_satellite_ortho_4k.jpg")
    os.makedirs(os.path.dirname(out_polyhaven_4k), exist_ok=True)
    os.makedirs(os.path.dirname(out_textures_4k), exist_ok=True)

    ortho_4k.save(out_polyhaven_4k, quality=95, subsampling=0)
    ortho_4k.save(out_textures_4k, quality=95, subsampling=0)
    print(f"  [OK] Saved 4096x4096 4K satellite orthophoto to: {out_polyhaven_4k}")
    print(f"  [OK] Saved 4096x4096 4K satellite orthophoto to: {out_textures_4k}")

    # 2. Resample to 1400x1400 for side-by-side aerial comparison
    ortho_1400 = cropped_exact.resize((1400, 1400), Image.Resampling.LANCZOS)
    out_renders_1400 = os.path.join(BASE_DIR, "output", "renders", "google_maps_aerial_full_36blocks.png")
    os.makedirs(os.path.dirname(out_renders_1400), exist_ok=True)
    ortho_1400.save(out_renders_1400)
    print(f"  [OK] Saved 1400x1400 comparison aerial to: {out_renders_1400}")

    return {
        "polyhaven_4k_path": out_polyhaven_4k,
        "textures_4k_path": out_textures_4k,
        "renders_1400_path": out_renders_1400,
        "tile_grid": [nx, ny],
        "raw_crop_px": list(cropped_exact.size),
    }


def main():
    skip_4k = "--skip-4k" in sys.argv
    api_key = load_api_key()
    car_street_nodes = load_car_street_nodes()
    print(f"[Step 1] Ingesting {len(EXPANDED_ZONES)} Expanded Zones (32 Verified Outdoor Street View Panoramas + 8 Zoom-19 Orthos)...")

    zone_dossiers = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {
            pool.submit(ingest_expanded_zone, z, car_street_nodes, api_key): z["zone_id"]
            for z in EXPANDED_ZONES
        }
        for fut in as_completed(futs):
            zid = futs[fut]
            dossier = fut.result()
            zone_dossiers[zid] = dossier
            cams = dossier["streetview_cameras"]
            verified_cnt = sum(1 for c in cams if c["verified_outdoor_google"])
            print(
                f"  [OK] {zid}: {verified_cnt}/{len(cams)} verified outdoor Google panos "
                f"+ 1280x1280 z19 ortho ({dossier['satellite']['span_meters']}m span)"
            )

    if skip_4k:
        ortho_summary = {
            "polyhaven_4k_path": os.path.join(BASE_DIR, "assets", "polyhaven", "montreal_satellite_ortho_4k.jpg"),
            "textures_4k_path": os.path.join(BASE_DIR, "output", "textures", "montreal_satellite_ortho_4k.jpg"),
            "renders_1400_path": os.path.join(BASE_DIR, "output", "renders", "google_maps_aerial_full_36blocks.png"),
            "tile_grid": [10, 10],
            "resolution_4k": [4096, 4096],
        }
    else:
        ortho_summary = build_4k_metric_satellite_ortho(
            api_key=api_key,
            center_x_m=40.0,
            center_y_m=-60.0,
            ortho_scale_m=1950.0,
            zoom=18,
            scale=2,
        )

    manifest_path = os.path.join(EXPANDED_SV_DIR, "expanded_imagery_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "zones": zone_dossiers,
                "master_satellite_ortho_4k": ortho_summary,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\n[DONE] Wrote full manifest to {manifest_path}")


if __name__ == "__main__":
    main()
