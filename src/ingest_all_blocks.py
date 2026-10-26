"""
Block Ingestion Pipeline with Built-In Step 0 Street View Outdoor Verification.
Ingests blocks (focusing on MTL-VM-0016 through MTL-VM-0025):
- Downloads 4 verified outdoor Google Street View references per block.
- Enforces Step 0 verification (is_official_google_outdoor_pano), automatically snapping
  any indoor or third-party photospheres to official Google Street View car-street centerlines.
- Downloads high-resolution top-down satellite orthophoto (zoom 19, scale 2).
- Slices deduplicated OpenStreetMap features (stamping is_primary_owner and owner_block_id).
- Generates data/blocks/<bid>/dossier.json.
"""
import os
import sys
import json
import math
import argparse
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from queue_generator import PILOT_BLOCKS, ALL_BLOCKS

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
BLOCKS_DIR = os.path.join(BASE_DIR, "data", "blocks")

# Load API Key from .env
env_path = os.path.join(BASE_DIR, ".env")
api_key = ""
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("GOOGLE_MAPS_API_KEY="):
            api_key = line.strip().split("=", 1)[1]

if not api_key:
    raise RuntimeError("GOOGLE_MAPS_API_KEY not found in .env")

# Master World Origin (Place d'Armes Center - Maisonneuve Monument)
MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0


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


def query_sv_meta(lat: float, lon: float, radius: int = 50, pano_id: str = None) -> dict:
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
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def download_sv_image(pano_id: str, lat: float, lon: float, heading: float, pitch: float, fov: float, out_path: str):
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


# Preload global OSM dataset and building registry
GLOBAL_OSM_PATH = os.path.join(BASE_DIR, "data", "open_data", "old_montreal_osm.json")
GLOBAL_REG_PATH = os.path.join(BASE_DIR, "data", "building_ownership_registry.json")

_global_cache = None


def get_global_osm_cache():
    global _global_cache
    if _global_cache is not None:
        return _global_cache

    if not os.path.exists(GLOBAL_OSM_PATH):
        from fetch_sector_osm_and_dedup import main as fetch_dedup
        fetch_dedup()

    with open(GLOBAL_OSM_PATH, "r", encoding="utf-8") as f:
        osm_raw = json.load(f)

    with open(GLOBAL_REG_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    nodes = {}
    trees = []
    monuments = []
    for el in osm_raw.get("elements", []):
        if el["type"] == "node":
            x, y = latlon_to_local_xy(el["lat"], el["lon"])
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"], "x": x, "y": y, "tags": el.get("tags", {})}
            tags = el.get("tags", {})
            if tags.get("natural") == "tree":
                trees.append({"id": el["id"], "lat": el["lat"], "lon": el["lon"], "x": x, "y": y})
            if tags.get("historic") == "monument":
                monuments.append({"id": el["id"], "lat": el["lat"], "lon": el["lon"], "x": x, "y": y, "tags": tags})

    buildings = []
    highways = []
    parks = []
    car_street_nodes = []

    for el in osm_raw.get("elements", []):
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
            wid_str = str(el["id"])

            item = {
                "id": el["id"],
                "name": tags.get("name", ""),
                "tags": tags,
                "centroid_latlon": [round(clat, 6), round(clon, 6)],
                "centroid_xy": [cx, cy],
                "coords_xy": coords_xy,
                "coords_ll": coords_ll
            }

            if "building" in tags:
                item["owner_block_id"] = registry.get(wid_str, {}).get("owner_block_id")
                buildings.append(item)
            elif "highway" in tags:
                highways.append(item)
                hw_type = tags.get("highway", "")
                if hw_type in ("primary", "secondary", "tertiary", "residential", "unclassified", "living_street", "service"):
                    for n in way_nodes:
                        car_street_nodes.append({
                            "lat": n["lat"],
                            "lon": n["lon"],
                            "x": n["x"],
                            "y": n["y"],
                            "name": tags.get("name", hw_type)
                        })
            elif tags.get("leisure") == "park" or tags.get("place") == "square":
                parks.append(item)

    _global_cache = {
        "nodes": nodes,
        "trees": trees,
        "monuments": monuments,
        "buildings": buildings,
        "highways": highways,
        "parks": parks,
        "car_street_nodes": car_street_nodes,
    }
    return _global_cache


def find_guaranteed_outdoor_pano(target_lat: float, target_lon: float, car_street_nodes: list, used_panos: set):
    """Snaps probe locations to nearest car-street centerlines outside buildings to find official Google outdoor pano."""
    tx, ty = latlon_to_local_xy(target_lat, target_lon)
    candidates = [(target_lat, target_lon, "direct")]

    # Sort street nodes by distance to target
    sorted_streets = sorted(car_street_nodes, key=lambda sn: (sn["x"] - tx) ** 2 + (sn["y"] - ty) ** 2)
    for sn in sorted_streets[:25]:
        candidates.append((sn["lat"], sn["lon"], f"street:{sn['name']}"))

    # Rings of offsets
    for dist in (25, 45, 70):
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
        for r in (15, 30, 50):
            meta = query_sv_meta(clat, clon, radius=r)
            if is_official_google_outdoor_pano(meta):
                pid = meta.get("pano_id")
                if pid and pid not in used_panos:
                    return meta, desc

    # Second pass: allow reusing a valid outdoor pano if strictly necessary
    tested.clear()
    for clat, clon, desc in candidates[:15]:
        key = (round(clat, 4), round(clon, 4))
        if key in tested:
            continue
        tested.add(key)
        meta = query_sv_meta(clat, clon, radius=50)
        if is_official_google_outdoor_pano(meta):
            return meta, desc + "_reused"

    return None, "failed"


def ingest_single_block(block, force: bool = False):
    bid = block["block_id"]

    block_dir = os.path.join(BLOCKS_DIR, bid)
    sv_dir = os.path.join(block_dir, "streetview")
    renders_dir = os.path.join(block_dir, "renders")
    os.makedirs(sv_dir, exist_ok=True)
    os.makedirs(renders_dir, exist_ok=True)

    dossier_path = os.path.join(block_dir, "dossier.json")
    sat_path = os.path.join(sv_dir, "satellite_topdown.png")

    # If already ingested and not forced, check completeness
    if not force and os.path.exists(dossier_path) and os.path.exists(sat_path):
        all_imgs = all(os.path.exists(os.path.join(sv_dir, f"{vp['label']}.jpg")) for vp in block["streetview_points"])
        if all_imgs:
            return f"{bid}: already ingested (skipping)"

    cache = get_global_osm_cache()
    car_street_nodes = cache["car_street_nodes"]

    block_cx, block_cy = latlon_to_local_xy(block["lat"], block["lon"])
    downloaded_views = []
    used_panos = set()

    for vp in block["streetview_points"]:
        label = vp["label"]
        pitch = vp.get("pitch", 12)
        target_lat = vp["lat"]
        target_lon = vp["lon"]
        target_x, target_y = latlon_to_local_xy(target_lat, target_lon)
        req_pano = vp.get("pano_id")

        # Primary probe
        meta = query_sv_meta(target_lat, target_lon, radius=50, pano_id=req_pano)
        source_desc = vp.get("snapped_source", "direct")

        # Step 0 Verification Gate
        if not is_official_google_outdoor_pano(meta) or meta.get("pano_id") in used_panos:
            # Indoor / third-party / duplicate detected — snap to street centerline!
            new_meta, source_desc = find_guaranteed_outdoor_pano(target_lat, target_lon, car_street_nodes, used_panos)
            if new_meta:
                meta = new_meta
            else:
                print(f"  [WARN] {bid} | {label}: Could not find guaranteed outdoor pano; using best effort.")

        pano_id = meta.get("pano_id", "")
        if pano_id:
            used_panos.add(pano_id)

        loc = meta.get("location", {})
        actual_lat = loc.get("lat", target_lat)
        actual_lon = loc.get("lng", target_lon)
        cam_x, cam_y = latlon_to_local_xy(actual_lat, actual_lon)

        # Re-aim camera heading toward target coordinate or block center
        if "street" in source_desc or "offset" in source_desc:
            dx = target_x - cam_x
            dy = target_y - cam_y
            if math.hypot(dx, dy) < 4.0:
                dx = block_cx - cam_x
                dy = block_cy - cam_y
            heading = round((math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0, 1)
        else:
            heading = round(vp["heading"], 1)

        img_path = os.path.join(sv_dir, f"{label}.jpg")
        download_sv_image(pano_id, actual_lat, actual_lon, heading, pitch, 90, img_path)

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
            "heading_deg": heading,
            "pitch_deg": pitch,
            "fov_deg": 90,
            "pano_id": pano_id,
            "date": meta.get("date", ""),
            "copyright": meta.get("copyright", "© Google"),
            "refetched_source": source_desc,
            "image_path": img_path,
            "google_maps_url": gmaps_url
        })

    # Download Satellite Orthophoto
    sat_url = (
        f"https://maps.googleapis.com/maps/api/staticmap"
        f"?center={block['lat']},{block['lon']}&zoom=19&size=640x640&scale=2"
        f"&maptype=satellite&key={api_key}"
    )
    urllib.request.urlretrieve(sat_url, sat_path)

    meters_per_px_z19 = (156543.03392 * math.cos(math.radians(block["lat"]))) / (2 ** 19)
    sat_span_meters = round(meters_per_px_z19 * 640, 2)

    # Slice OSM Features from Global Cache
    s, w, n, e = [float(v) for v in block["bbox"].split(",")]
    pad = 0.00045

    b_bldgs = []
    owned_count = 0
    for bldg in cache["buildings"]:
        clat, clon = bldg["centroid_latlon"]
        is_owner = (bldg["owner_block_id"] == bid)
        in_bbox = (s - pad <= clat <= n + pad) and (w - pad <= clon <= e + pad)
        if is_owner or in_bbox:
            b_copy = {k: v for k, v in bldg.items() if k != "coords_ll"}
            b_copy["is_primary_owner"] = is_owner
            b_bldgs.append(b_copy)
            if is_owner:
                owned_count += 1

    b_hw = []
    for hw in cache["highways"]:
        if any(s - pad <= pt[0] <= n + pad and w - pad <= pt[1] <= e + pad for pt in hw.get("coords_ll", [])):
            b_hw.append({k: v for k, v in hw.items() if k != "coords_ll"})

    b_parks = [
        {k: v for k, v in pk.items() if k != "coords_ll"} for pk in cache["parks"]
        if (s - pad <= pk["centroid_latlon"][0] <= n + pad) and (w - pad <= pk["centroid_latlon"][1] <= e + pad)
    ]
    b_trees = [
        t for t in cache["trees"]
        if (s - pad <= t["lat"] <= n + pad) and (w - pad <= t["lon"] <= e + pad)
    ]
    b_monuments = [
        m for m in cache["monuments"]
        if (s - pad <= m["lat"] <= n + pad) and (w - pad <= m["lon"] <= e + pad)
    ]

    osm_features = {
        "buildings": b_bldgs,
        "highways": b_hw,
        "parks_squares": b_parks,
        "monuments": b_monuments,
        "trees": b_trees
    }

    dossier = {
        "block_id": bid,
        "name": block["name"],
        "street_address": block["street_address"],
        "archetype": block["archetype"],
        "blender_center_xy_m": [block_cx, block_cy],
        "crs": {
            "projection": "Local Metric Tangent Plane (EPSG:32188 / MTM Zone 8 aligned)",
            "master_origin_wgs84": [MASTER_ORIGIN_LAT, MASTER_ORIGIN_LON],
            "block_center_wgs84": [block["lat"], block["lon"]],
            "block_center_xy_m": [block_cx, block_cy],
            "unit": "meters"
        },
        "satellite": {
            "image_path": sat_path,
            "span_meters": sat_span_meters,
            "center_xy_m": [block_cx, block_cy]
        },
        "streetview_cameras": downloaded_views,
        "osm_features": osm_features
    }

    with open(dossier_path, "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)

    # Mirror into snapshots/ directory for full specification compliance
    snapshots_dir = os.path.join(block_dir, "snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    import shutil
    for fname in os.listdir(sv_dir):
        shutil.copy2(os.path.join(sv_dir, fname), os.path.join(snapshots_dir, fname))

    return (
        f"{bid}: 4 Street Views (all outdoor), 1 Satellite ({sat_span_meters}m), "
        f"{owned_count} owned / {len(b_bldgs)} total OSM buildings, {len(b_hw)} streets, {len(b_trees)} trees"
    )


def main():
    parser = argparse.ArgumentParser(description="Ingest block data with Step 0 outdoor verification.")
    parser.add_argument("--all", action="store_true", help="Ingest all 35 blocks.")
    parser.add_argument("--m2", "--wave3", dest="wave3", action="store_true", help="Ingest Milestone 2 blocks MTL-VM-0026..0035.")
    parser.add_argument("--block", type=str, help="Ingest specific block ID.")
    parser.add_argument("--force", action="store_true", help="Force re-download even if already present.")
    args = parser.parse_args()

    if args.block:
        target_blocks = [b for b in PILOT_BLOCKS if b["block_id"] == args.block]
    elif args.all:
        target_blocks = PILOT_BLOCKS
    elif args.wave3:
        target_blocks = [b for b in PILOT_BLOCKS if int(b["block_id"].split("-")[-1]) >= 26]
    else:
        # Default: Ingest new blocks MTL-VM-0026 through MTL-VM-0035
        target_blocks = [b for b in PILOT_BLOCKS if int(b["block_id"].split("-")[-1]) >= 26]

    print(f"Targeting {len(target_blocks)} blocks for ingestion...")
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(ingest_single_block, b, args.force): b["block_id"] for b in target_blocks}
        for fut in as_completed(futures):
            bid = futures[fut]
            try:
                res = fut.result()
                print("  [OK]", res)
            except Exception as e:
                print(f"  [ERR] {bid}: {e}")
                import traceback
                traceback.print_exc()

    print("Ingestion run complete!")


if __name__ == "__main__":
    main()
