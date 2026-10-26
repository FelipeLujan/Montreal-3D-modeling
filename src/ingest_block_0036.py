"""
Ingest Block MTL-VM-0036: Farine Five Roses Flour Mill & Bassin Peel Waterfront
Adds MTL-VM-0036 cleanly to data/blocks/MTL-VM-0036/dossier.json without disturbing running blocks 0026..0035.
"""
import os
import json
import math
import ssl
import shutil
import urllib.request
import urllib.parse
from src.ingest_all_blocks import (
    BASE_DIR, BLOCKS_DIR, MASTER_ORIGIN_LAT, MASTER_ORIGIN_LON,
    latlon_to_local_xy, query_sv_meta, is_official_google_outdoor_pano,
    find_guaranteed_outdoor_pano, download_sv_image, api_key
)

BLOCK_0036 = {
    "block_id": "MTL-VM-0036",
    "name": "Farine Five Roses Flour Mill & Bassin Peel / Rue Mill Industrial Waterfront",
    "street_address": "380 Rue Mill, Montréal, QC H3C 1Y4",
    "lat": 45.49585,
    "lon": -73.55185,
    "bbox": "45.4942,-73.5542,45.4971,-73.5498",
    "archetype": "Iconic Farine Five Roses Flour Mill & Giant Red Neon Sign, Concrete Grain Silos, Bassin Peel Waterfront & Rue Mill Bridge",
    "streetview_points": [
        {"label": "Farine_Five_Roses_Mill_North", "lat": 45.49645, "lon": -73.55195, "heading": 185},
        {"label": "Rue_Mill_Industrial_Corridor", "lat": 45.49595, "lon": -73.55135, "heading": 245},
        {"label": "Bassin_Peel_North_Quay", "lat": 45.49685, "lon": -73.55315, "heading": 150},
        {"label": "Pointe_du_Moulin_West_Silos", "lat": 45.49525, "lon": -73.55225, "heading": 35}
    ]
}

def main():
    bid = BLOCK_0036["block_id"]
    block_dir = os.path.join(BLOCKS_DIR, bid)
    sv_dir = os.path.join(block_dir, "streetview")
    renders_dir = os.path.join(block_dir, "renders")
    snapshots_dir = os.path.join(block_dir, "snapshots")
    os.makedirs(sv_dir, exist_ok=True)
    os.makedirs(renders_dir, exist_ok=True)
    os.makedirs(snapshots_dir, exist_ok=True)

    # Fetch OSM for bbox
    bbox = BLOCK_0036["bbox"]
    overpass_query = f"""
    [out:json][timeout:30];
    (
      way["building"]({bbox});
      relation["building"]({bbox});
      way["leisure"="park"]({bbox});
      way["highway"]({bbox});
      node["natural"="tree"]({bbox});
      way["man_made"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    ctx = ssl._create_unverified_context()
    osm_raw = None
    for url in ["https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]:
        try:
            req = urllib.request.Request(
                url,
                data=urllib.parse.urlencode({"data": overpass_query}).encode("utf-8"),
                headers={"User-Agent": "Montreal3DTwin/1.0"}
            )
            with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
                osm_raw = json.loads(r.read().decode("utf-8"))
            if osm_raw and "elements" in osm_raw:
                break
        except Exception as e:
            print("Overpass warning:", e)

    # Also merge with existing global OSM cache if needed
    global_osm_path = os.path.join(BASE_DIR, "data", "open_data", "old_montreal_osm.json")
    global_reg_path = os.path.join(BASE_DIR, "data", "building_ownership_registry.json")
    existing_reg = {}
    if os.path.exists(global_reg_path):
        with open(global_reg_path, "r", encoding="utf-8") as f:
            existing_reg = json.load(f)

    # Find which building IDs are already in the bbox of 0028 or 0029
    claimed_by_28_29 = set()
    for nbid in ("MTL-VM-0028", "MTL-VM-0029"):
        ndpath = os.path.join(BLOCKS_DIR, nbid, "dossier.json")
        if os.path.exists(ndpath):
            with open(ndpath, "r", encoding="utf-8") as f:
                nd = json.load(f)
            for b in nd.get("osm_features", {}).get("buildings", []):
                if b.get("is_primary_owner"):
                    claimed_by_28_29.add(b["id"])

    elements = osm_raw.get("elements", []) if osm_raw else []
    nodes = {}
    trees = []
    for el in elements:
        if el["type"] == "node":
            x, y = latlon_to_local_xy(el["lat"], el["lon"])
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"], "x": x, "y": y, "tags": el.get("tags", {})}
            if el.get("tags", {}).get("natural") == "tree":
                trees.append({"id": el["id"], "lat": el["lat"], "lon": el["lon"], "x": x, "y": y})

    buildings = []
    highways = []
    parks = []
    car_street_nodes = []
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
                "coords_xy": coords_xy
            }
            if "building" in tags or tags.get("man_made") in ("silo", "works", "storage_tank"):
                is_owner = (el["id"] not in claimed_by_28_29) and (clat <= 45.49715)
                item["owner_block_id"] = bid if is_owner else "MTL-VM-0029"
                item["is_primary_owner"] = is_owner
                buildings.append(item)
            elif "highway" in tags:
                highways.append(item)
                for n in way_nodes:
                    car_street_nodes.append({"lat": n["lat"], "lon": n["lon"], "x": n["x"], "y": n["y"], "name": tags.get("name", "street")})
            elif tags.get("leisure") == "park":
                parks.append(item)

    block_cx, block_cy = latlon_to_local_xy(BLOCK_0036["lat"], BLOCK_0036["lon"])
    downloaded_views = []
    used_panos = set()

    for vp in BLOCK_0036["streetview_points"]:
        label = vp["label"]
        pitch = 12
        tlat, tlon = vp["lat"], vp["lon"]
        tx, ty = latlon_to_local_xy(tlat, tlon)
        meta = query_sv_meta(tlat, tlon, radius=50)
        source_desc = "direct"
        if not is_official_google_outdoor_pano(meta) or meta.get("pano_id") in used_panos:
            new_meta, source_desc = find_guaranteed_outdoor_pano(tlat, tlon, car_street_nodes, used_panos)
            if new_meta:
                meta = new_meta
        pano_id = meta.get("pano_id", "")
        if pano_id:
            used_panos.add(pano_id)
        loc = meta.get("location", {})
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
            "date": meta.get("date", ""),
            "copyright": meta.get("copyright", "© Google"),
            "refetched_source": source_desc,
            "image_path": img_path,
            "google_maps_url": f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={alat:.5f},{alon:.5f}&heading={heading}&pitch={pitch}&fov=90&pano={pano_id}"
        })

    sat_path = os.path.join(sv_dir, "satellite_topdown.png")
    sat_url = (
        f"https://maps.googleapis.com/maps/api/staticmap"
        f"?center={BLOCK_0036['lat']},{BLOCK_0036['lon']}&zoom=19&size=640x640&scale=2"
        f"&maptype=satellite&key={api_key}"
    )
    urllib.request.urlretrieve(sat_url, sat_path)
    shutil.copy2(sat_path, os.path.join(snapshots_dir, "satellite_topdown.png"))
    meters_per_px_z19 = (156543.03392 * math.cos(math.radians(BLOCK_0036["lat"]))) / (2 ** 19)
    sat_span_meters = round(meters_per_px_z19 * 640, 2)

    dossier = {
        "block_id": bid,
        "name": BLOCK_0036["name"],
        "street_address": BLOCK_0036["street_address"],
        "archetype": BLOCK_0036["archetype"],
        "blender_center_xy_m": [block_cx, block_cy],
        "crs": {
            "projection": "Local Metric Tangent Plane (EPSG:32188 / MTM Zone 8 aligned)",
            "master_origin_wgs84": [MASTER_ORIGIN_LAT, MASTER_ORIGIN_LON],
            "block_center_wgs84": [BLOCK_0036["lat"], BLOCK_0036["lon"]],
            "block_center_xy_m": [block_cx, block_cy],
            "unit": "meters"
        },
        "satellite": {
            "image_path": sat_path,
            "span_meters": sat_span_meters,
            "center_xy_m": [block_cx, block_cy]
        },
        "streetview_cameras": downloaded_views,
        "osm_features": {
            "buildings": buildings,
            "highways": highways,
            "parks_squares": parks,
            "monuments": [],
            "trees": trees
        }
    }

    dossier_path = os.path.join(block_dir, "dossier.json")
    with open(dossier_path, "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)

    owned = sum(1 for b in buildings if b["is_primary_owner"])
    print(f"[OK] Ingested {bid}: {owned} owned / {len(buildings)} total buildings, {len(highways)} streets, 4 outdoor Street Views, 1 Satellite ({sat_span_meters}m)")

if __name__ == "__main__":
    main()
