"""
Ingest the 4 Contiguous Corridor Superblocks connecting Pont Jacques-Cartier / Old Port East
(`MTL-VM-0039`, `MTL-VM-0040`, `MTL-VM-0042`) to the Montreal Olympic Park (`MTL-OLY-0001`):
  - `MTL-OLY-0002`: Maison de Radio-Canada Tower, Village Pied-du-Courant & Parc Bellerive Waterfront
  - `MTL-OLY-0003`: Sucrerie Lantic Heritage Refinery, Quai Sutherland & Hochelaga Sainte-Catherine Corridor
  - `MTL-OLY-0004`: Marché Maisonneuve Beaux-Arts Dome, Bain Morgan & Promenade Avenue Morgan Axis
  - `MTL-OLY-0005`: Château Dufresne Beaux-Arts Museum, Boulevard Pie-IX & Rue Sherbrooke Est Olympic Gateway
"""
import os
import sys
import json
import math
import ssl
import shutil
import urllib.request
import urllib.parse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingest_all_blocks import (
    BASE_DIR, BLOCKS_DIR, MASTER_ORIGIN_LAT, MASTER_ORIGIN_LON,
    latlon_to_local_xy, query_sv_meta, is_official_google_outdoor_pano,
    find_guaranteed_outdoor_pano, download_sv_image, api_key
)

CORRIDOR_SPECS = [
    {
        "block_id": "MTL-OLY-0002",
        "name": "Maison de Radio-Canada Tower, Village Pied-du-Courant & Parc Bellerive Waterfront Promenade",
        "street_address": "1400 Boulevard René-Lévesque Est / Parc Bellerive, Montréal, QC H2L 2M2",
        "lat": 45.5240,
        "lon": -73.5465,
        "bbox": "45.5190,-73.5535,45.5290,-73.5395",
        "sat_zoom": 17,
        "archetype": "23-Story Hexagonal Brutalist/Modernist Tour de Radio-Canada, New Broadcast Glass Complex, Parc Bellerive St. Lawrence Riverfront Promenade & Rue Notre-Dame Est Corridor",
        "streetview_points": [
            {"label": "Tour_Radio_Canada_ReneLevesque_South", "lat": 45.5212, "lon": -73.5508, "heading": 35, "pitch": 16},
            {"label": "Parc_Bellerive_Waterfront_Promenade", "lat": 45.5262, "lon": -73.5425, "heading": 125, "pitch": 10},
            {"label": "Rue_NotreDameEst_Papineau_Corridor", "lat": 45.5228, "lon": -73.5462, "heading": 40, "pitch": 12},
            {"label": "Rue_SainteCatherineEst_DeLorimier", "lat": 45.5250, "lon": -73.5495, "heading": 65, "pitch": 12},
        ],
    },
    {
        "block_id": "MTL-OLY-0003",
        "name": "Sucrerie Lantic Heritage Refinery, Quai Sutherland & Hochelaga Sainte-Catherine Est Corridor",
        "street_address": "4026 Rue Notre-Dame Est / Quai Sutherland, Montréal, QC H1W 2K3",
        "lat": 45.5345,
        "lon": -73.5450,
        "bbox": "45.5315,-73.5495,45.5378,-73.5405",
        "sat_zoom": 17,
        "archetype": "Monumental Red-Brick & Copper-Roofed St. Lawrence Sugar Refinery (Sucrerie Lantic), Port of Montreal Quai Sutherland Pier & Cranes, and Hochelaga Victorian Triplex Streetscape",
        "streetview_points": [
            {"label": "Sucrerie_Lantic_NotreDameEst_Facade", "lat": 45.5375, "lon": -73.5418, "heading": 55, "pitch": 14},
            {"label": "Rue_NotreDameEst_Port_Rail_Corridor", "lat": 45.5335, "lon": -73.5435, "heading": 35, "pitch": 12},
            {"label": "Rue_SainteCatherineEst_Hochelaga_Plaza", "lat": 45.5355, "lon": -73.5465, "heading": 45, "pitch": 12},
            {"label": "Rue_OntarioEst_Moreau_Heritage", "lat": 45.5370, "lon": -73.5495, "heading": 60, "pitch": 12},
        ],
    },
    {
        "block_id": "MTL-OLY-0004",
        "name": "Marché Maisonneuve Beaux-Arts Dome, Bain Morgan & Promenade Avenue Morgan Civic Axis",
        "street_address": "4445 Rue Ontario Est / 1875 Avenue Morgan, Montréal, QC H1V 1K5",
        "lat": 45.5455,
        "lon": -73.5460,
        "bbox": "45.5400,-73.5535,45.5510,-73.5385",
        "sat_zoom": 17,
        "archetype": "1914 Beaux-Arts Limestone Marché Maisonneuve with Copper Dome & La Fermière Fountain, Neoclassical Bain Public Morgan, and Tree-Lined Avenue Morgan Boulevard Vista",
        "streetview_points": [
            {"label": "Marche_Maisonneuve_BeauxArts_Fountain", "lat": 45.5502, "lon": -73.5495, "heading": 315, "pitch": 14},
            {"label": "Bain_Morgan_Avenue_Morgan_Facade", "lat": 45.5482, "lon": -73.5472, "heading": 310, "pitch": 14},
            {"label": "Promenade_Avenue_Morgan_North_Vista", "lat": 45.5455, "lon": -73.5442, "heading": 312, "pitch": 12},
            {"label": "Rue_SainteCatherineEst_Morgan_Square", "lat": 45.5440, "lon": -73.5425, "heading": 315, "pitch": 12},
        ],
    },
    {
        "block_id": "MTL-OLY-0005",
        "name": "Château Dufresne Beaux-Arts Museum, Boulevard Pie-IX & Rue Sherbrooke Est Olympic Gateway",
        "street_address": "2929 Rue Jeanne-d'Arc / Boulevard Pie-IX & Rue Sherbrooke Est, Montréal, QC H1W 3W2",
        "lat": 45.5532,
        "lon": -73.5532,
        "bbox": "45.5490,-73.5590,45.5565,-73.5475",
        "sat_zoom": 17,
        "archetype": "1918 Beaux-Arts Limestone Château Dufresne Mansion with Twin Ionic Colonnades & Balustraded Roof, Boulevard Pie-IX BRT Corridor & Rue Sherbrooke Est Olympic Stadium Gateway",
        "streetview_points": [
            {"label": "Chateau_Dufresne_PieIX_Sherbrooke_Facade", "lat": 45.5536, "lon": -73.5540, "heading": 95, "pitch": 14},
            {"label": "Boulevard_PieIX_North_to_Olympic_Stadium", "lat": 45.5522, "lon": -73.5518, "heading": 32, "pitch": 14},
            {"label": "Rue_Sherbrooke_Est_Olympic_Approach", "lat": 45.5515, "lon": -73.5552, "heading": 42, "pitch": 14},
            {"label": "Rue_Jeanne_dArc_Chateau_Gardens", "lat": 45.5532, "lon": -73.5525, "heading": 295, "pitch": 12},
        ],
    },
]


def ingest_spec(spec):
    bid = spec["block_id"]
    print(f"\n=== Ingesting {bid}: {spec['name']} ===")
    block_dir = os.path.join(BLOCKS_DIR, bid)
    sv_dir = os.path.join(block_dir, "streetview")
    renders_dir = os.path.join(block_dir, "renders")
    snapshots_dir = os.path.join(block_dir, "snapshots")
    os.makedirs(sv_dir, exist_ok=True)
    os.makedirs(renders_dir, exist_ok=True)
    os.makedirs(snapshots_dir, exist_ok=True)

    bbox = spec["bbox"]
    overpass_query = f"""
    [out:json][timeout:60];
    (
      way["building"]({bbox});
      relation["building"]({bbox});
      way["leisure"]({bbox});
      relation["leisure"]({bbox});
      way["highway"]({bbox});
      way["man_made"]({bbox});
      way["tourism"]({bbox});
      node["natural"="tree"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    ctx = ssl._create_unverified_context()
    osm_raw = None
    for url in [
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    ]:
        try:
            req = urllib.request.Request(
                url,
                data=urllib.parse.urlencode({"data": overpass_query}).encode("utf-8"),
                headers={"User-Agent": "Montreal3DTwin/2.0"},
            )
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                osm_raw = json.loads(r.read().decode("utf-8"))
            if osm_raw and "elements" in osm_raw:
                print(f"[OSM] Fetched {len(osm_raw['elements'])} elements for {bid} from {url}")
                break
        except Exception as e:
            print(f"[OSM] Warning from {url}: {e}")

    elements = osm_raw.get("elements", []) if osm_raw else []
    nodes = {}
    ways_by_id = {}
    trees = []
    for el in elements:
        if el["type"] == "node":
            x, y = latlon_to_local_xy(el["lat"], el["lon"])
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"], "x": x, "y": y, "tags": el.get("tags", {})}
            if el.get("tags", {}).get("natural") == "tree":
                trees.append({"id": el["id"], "lat": el["lat"], "lon": el["lon"], "xy": [x, y], "x": x, "y": y})
        elif el["type"] == "way":
            ways_by_id[el["id"]] = el

    buildings = []
    highways = []
    parks = []
    car_street_nodes = []
    seen_bldg_ids = set()

    for el in elements:
        if el["type"] == "way":
            tags = el.get("tags", {})
            way_nodes = [nodes[nid] for nid in el.get("nodes", []) if nid in nodes]
            if not way_nodes:
                continue
            coords_xy = [[n["x"], n["y"]] for n in way_nodes]
            coords_ll = [[n["lat"], n["lon"]] for n in way_nodes]
            clat = sum(p[0] for p in coords_ll) / len(coords_ll)
            clon = sum(p[1] for p in coords_ll) / len(coords_ll)
            cx, cy = latlon_to_local_xy(clat, clon)
            item = {
                "id": el["id"],
                "name": tags.get("name", ""),
                "tags": tags,
                "centroid_latlon": [round(clat, 6), round(clon, 6)],
                "centroid_xy": [cx, cy],
                "coords_xy": coords_xy,
            }
            if (
                "building" in tags
                or "building:part" in tags
                or tags.get("leisure") in ("stadium", "sports_centre", "pitch")
                or tags.get("man_made") in ("tower", "bridge", "works", "silo", "chimney")
                or tags.get("tourism") in ("attraction", "museum", "viewpoint")
            ):
                item["owner_block_id"] = bid
                item["is_primary_owner"] = True
                buildings.append(item)
                seen_bldg_ids.add(el["id"])
            elif "highway" in tags:
                highways.append(item)
                if tags.get("highway") in ("primary", "secondary", "tertiary", "residential", "service", "unclassified"):
                    for n in way_nodes:
                        car_street_nodes.append({"lat": n["lat"], "lon": n["lon"], "x": n["x"], "y": n["y"], "name": tags.get("name", "street")})
            elif tags.get("leisure") in ("park", "garden"):
                parks.append(item)

        elif el["type"] == "relation":
            tags = el.get("tags", {})
            if "building" in tags or tags.get("leisure") in ("stadium", "sports_centre") or tags.get("tourism") in ("attraction", "museum"):
                outer_ways = [
                    ways_by_id[m["ref"]]
                    for m in el.get("members", [])
                    if m.get("type") == "way" and m.get("role") in ("outer", "") and m.get("ref") in ways_by_id
                ]
                for w in outer_ways:
                    if w["id"] in seen_bldg_ids:
                        continue
                    wn = [nodes[nid] for nid in w.get("nodes", []) if nid in nodes]
                    if len(wn) < 3:
                        continue
                    coords_xy = [[n["x"], n["y"]] for n in wn]
                    coords_ll = [[n["lat"], n["lon"]] for n in wn]
                    clat = sum(p[0] for p in coords_ll) / len(coords_ll)
                    clon = sum(p[1] for p in coords_ll) / len(coords_ll)
                    cx, cy = latlon_to_local_xy(clat, clon)
                    merged_tags = dict(tags)
                    merged_tags.update(w.get("tags", {}))
                    buildings.append({
                        "id": w["id"],
                        "relation_id": el["id"],
                        "name": merged_tags.get("name", ""),
                        "tags": merged_tags,
                        "centroid_latlon": [round(clat, 6), round(clon, 6)],
                        "centroid_xy": [cx, cy],
                        "coords_xy": coords_xy,
                        "owner_block_id": bid,
                        "is_primary_owner": True,
                    })
                    seen_bldg_ids.add(w["id"])

    block_cx, block_cy = latlon_to_local_xy(spec["lat"], spec["lon"])
    downloaded_views = []
    used_panos = set()

    for vp in spec["streetview_points"]:
        label = vp["label"]
        pitch = vp.get("pitch", 12)
        tlat, tlon = vp["lat"], vp["lon"]
        meta = query_sv_meta(tlat, tlon, radius=110)
        source_desc = "direct"
        if not is_official_google_outdoor_pano(meta) or meta.get("pano_id") in used_panos:
            new_meta, source_desc = find_guaranteed_outdoor_pano(tlat, tlon, car_street_nodes, used_panos)
            if new_meta:
                meta = new_meta
        pano_id = meta.get("pano_id", "") if meta else ""
        if pano_id:
            used_panos.add(pano_id)
        loc = meta.get("location", {}) if meta else {}
        alat = loc.get("lat", tlat)
        alon = loc.get("lng", tlon)
        cam_x, cam_y = latlon_to_local_xy(alat, alon)
        heading = round(vp["heading"], 1)
        img_path = os.path.join(sv_dir, f"{label}.jpg")
        download_sv_image(pano_id, alat, alon, heading, pitch, 90, img_path)
        shutil.copy2(img_path, os.path.join(snapshots_dir, f"{label}.jpg"))
        downloaded_views.append({
            "label": label,
            "requested_lat": tlat,
            "requested_lon": tlon,
            "actual_lat": alat,
            "actual_lon": alon,
            "blender_cam_xy_m": [cam_x, cam_y],
            "heading": heading,
            "heading_deg": heading,
            "pitch_deg": pitch,
            "fov_deg": 90,
            "pano_id": pano_id,
            "date": meta.get("date", "") if meta else "",
            "copyright": meta.get("copyright", "© Google") if meta else "© Google",
            "refetched_source": source_desc,
            "image_path": img_path,
            "google_maps_url": f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={alat:.5f},{alon:.5f}&heading={heading}&pitch={pitch}&fov=90&pano={pano_id}",
        })

    # Download Satellite Top-Down Orthophoto at Zoom 17 (640x640 scale=2 -> 1280x1280)
    zoom = spec.get("sat_zoom", 17)
    meters_per_px = 156543.03392 * math.cos(math.radians(spec["lat"])) / (2 ** zoom)
    span_meters = round(meters_per_px * 640.0, 2)
    sat_path = os.path.join(sv_dir, "satellite_topdown.png")
    sat_url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={spec['lat']},{spec['lon']}&zoom={zoom}&size=640x640&scale=2&maptype=satellite&key={api_key}"
    )
    try:
        urllib.request.urlretrieve(sat_url, sat_path)
        shutil.copy2(sat_path, os.path.join(snapshots_dir, "satellite_topdown.png"))
    except Exception as e:
        print(f"[SAT] Warning downloading satellite for {bid}: {e}")

    dossier = {
        "block_id": bid,
        "name": spec["name"],
        "street_address": spec["street_address"],
        "archetype": spec["archetype"],
        "blender_center_xy_m": [block_cx, block_cy],
        "crs": {
            "projection": "Local Metric Tangent Plane (EPSG:32188 / MTM Zone 8 aligned)",
            "master_origin_wgs84": [MASTER_ORIGIN_LAT, MASTER_ORIGIN_LON],
            "block_center_wgs84": [spec["lat"], spec["lon"]],
            "block_center_xy_m": [block_cx, block_cy],
            "unit": "meters",
        },
        "satellite": {
            "image_path": sat_path,
            "zoom": zoom,
            "span_meters": span_meters,
            "ground_width_m": span_meters,
            "center_xy_m": [block_cx, block_cy],
        },
        "streetview_cameras": downloaded_views,
        "osm_features": {
            "buildings": buildings,
            "highways": highways,
            "parks_squares": parks,
            "trees": trees,
        },
    }
    dossier_path = os.path.join(block_dir, "dossier.json")
    with open(dossier_path, "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved {dossier_path} ({len(buildings)} buildings, {len(highways)} highways, {len(parks)} parks, {len(trees)} trees)")


if __name__ == "__main__":
    for s in CORRIDOR_SPECS:
        dp = os.path.join(BLOCKS_DIR, s["block_id"], "dossier.json")
        if os.path.isfile(dp):
            try:
                existing = json.load(open(dp, encoding="utf-8"))
                if len(existing.get("osm_features", {}).get("buildings", [])) > 10:
                    print(f"[SKIP] {s['block_id']} already has {len(existing['osm_features']['buildings'])} buildings.")
                    continue
            except Exception:
                pass
        ingest_spec(s)
