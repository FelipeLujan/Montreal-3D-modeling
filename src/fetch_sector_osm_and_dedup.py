"""
Single-Request Overpass Sector Fetcher & Global Voronoi Ownership Deduplicator.
Queries the expanded Old Montreal 25-block district (bbox: 45.5000, -73.5640, 45.5140, -73.5435),
saves data/open_data/old_montreal_osm.json (1,080 buildings and signature landmarks),
assigns a single deterministic owner_block_id to every building across blocks MTL-VM-0001..0025,
saves data/building_ownership_registry.json, and slices deduplicated osm_features into block dossiers.
"""
import os
import json
import math
import ssl
import urllib.request
import urllib.parse
from collections import Counter

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
BLOCKS_DIR = os.path.join(BASE_DIR, "data", "blocks")

MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0


def latlon_to_local_xy(lat: float, lon: float, origin_lat=MASTER_ORIGIN_LAT, origin_lon=MASTER_ORIGIN_LON):
    dlat = math.radians(lat - origin_lat)
    dlon = math.radians(lon - origin_lon)
    mean_lat = math.radians(origin_lat)
    x = dlon * EARTH_RADIUS_M * math.cos(mean_lat)
    y = dlat * EARTH_RADIUS_M
    return round(x, 3), round(y, 3)


def polygon_centroid_latlon(coords_latlon):
    lats = [p[0] for p in coords_latlon]
    lons = [p[1] for p in coords_latlon]
    return (sum(lats) / len(lats), sum(lons) / len(lons))


def fetch_or_load_expanded_osm(force: bool = False):
    sector_bbox = "45.4965,-73.5645,45.5145,-73.5405"
    open_data_path = os.path.join(BASE_DIR, "data", "open_data", "old_montreal_osm.json")

    osm_raw = None
    if not force and os.path.exists(open_data_path) and os.path.getsize(open_data_path) > 1000000:
        try:
            print(f"Loading existing expanded sector OSM from {open_data_path} ...")
            with open(open_data_path, "r", encoding="utf-8") as f:
                osm_raw = json.load(f)
            if osm_raw and "elements" in osm_raw and len(osm_raw["elements"]) > 25000:
                print(f"Loaded {len(osm_raw['elements'])} elements from disk cache.")
                return osm_raw
        except Exception as e:
            print(f"Failed loading disk cache: {e}")

    overpass_query = f"""
    [out:json][timeout:60];
    (
      way["building"]({sector_bbox});
      relation["building"]({sector_bbox});
      way["leisure"="park"]({sector_bbox});
      way["place"="square"]({sector_bbox});
      way["highway"]({sector_bbox});
      node["historic"="monument"]({sector_bbox});
      way["historic"="monument"]({sector_bbox});
      node["natural"="tree"]({sector_bbox});
      way["man_made"]({sector_bbox});
    );
    out body;
    >;
    out skel qt;
    """
    ctx = ssl._create_unverified_context()
    endpoints = [
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]
    osm_raw = None
    for url in endpoints:
        try:
            print(f"Querying expanded sector Overpass request from {url} ...")
            req = urllib.request.Request(
                url,
                data=urllib.parse.urlencode({"data": overpass_query}).encode("utf-8"),
                headers={"User-Agent": "Montreal3DTwin/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
                osm_raw = json.loads(r.read().decode("utf-8"))
            if osm_raw and "elements" in osm_raw:
                print(f"Fetched {len(osm_raw['elements'])} OSM elements in 1 request!")
                break
        except Exception as e:
            print(f"Endpoint {url} warning: {e}")

    if not osm_raw:
        # Fallback to existing old_montreal_osm.json if available
        if os.path.exists(open_data_path):
            with open(open_data_path, "r", encoding="utf-8") as f:
                osm_raw = json.load(f)

    if not osm_raw or "elements" not in osm_raw:
        raise RuntimeError("Failed to fetch or load expanded OSM sector dataset.")

    os.makedirs(os.path.join(BASE_DIR, "data", "open_data"), exist_ok=True)
    with open(open_data_path, "w", encoding="utf-8") as f:
        json.dump(osm_raw, f)
    print(f"Saved expanded OSM sector ({len(osm_raw['elements'])} elements) to {open_data_path}")

    return osm_raw


def process_and_deduplicate(osm_raw=None):
    if osm_raw is None:
        osm_raw = fetch_or_load_expanded_osm()

    from queue_generator import PILOT_BLOCKS

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
    for el in osm_raw.get("elements", []):
        if el["type"] == "way":
            tags = el.get("tags", {})
            way_nodes = [nodes[nid] for nid in el.get("nodes", []) if nid in nodes]
            if not way_nodes:
                continue
            coords_xy = [[n["x"], n["y"]] for n in way_nodes]
            coords_ll = [[n["lat"], n["lon"]] for n in way_nodes]
            clat, clon = polygon_centroid_latlon(coords_ll)
            cx, cy = latlon_to_local_xy(clat, clon)
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
                buildings.append(item)
            elif "highway" in tags:
                highways.append(item)
            elif tags.get("leisure") == "park" or tags.get("place") == "square":
                parks.append(item)

    # Compute block centers in local XY across all 25 blocks
    block_meta = {b["block_id"]: b for b in PILOT_BLOCKS}
    block_centers_xy = {}
    for bid, b in block_meta.items():
        block_centers_xy[bid] = latlon_to_local_xy(b["lat"], b["lon"])

    # Global Voronoi Deduplication: assign single authoritative owner_block_id (excluding open square MTL-VM-0001)
    global_registry = {}
    for bldg in buildings:
        cx, cy = bldg["centroid_xy"]
        best_bid = None
        best_d2 = float("inf")
        for cand_bid, (bx, by) in block_centers_xy.items():
            if cand_bid == "MTL-VM-0001":
                continue
            d2 = (cx - bx) ** 2 + (cy - by) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_bid = cand_bid
        # Transfer / ensure Habitat 67 is strictly owned by MTL-VM-0035
        if bldg["id"] == 440195613:
            best_bid = "MTL-VM-0035"
        bldg["owner_block_id"] = best_bid
        global_registry[str(bldg["id"])] = {
            "osm_way_id": str(bldg["id"]),
            "name": bldg["name"],
            "centroid_xy": [cx, cy],
            "owner_block_id": best_bid
        }

    registry_path = os.path.join(BASE_DIR, "data", "building_ownership_registry.json")
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(global_registry, f, indent=2, ensure_ascii=False)
    print(f"Saved global building ownership registry ({len(global_registry)} buildings) to {registry_path}")

    # Verify signature landmarks across 35 blocks
    landmarks = {
        87389029: ("Marché Bonsecours", "MTL-VM-0018"),
        87389036: ("Chapelle Notre-Dame-de-Bon-Secours", "MTL-VM-0019"),
        161206731: ("Tour de l'Horloge", "MTL-VM-0025"),
        677248941: ("Grand Quai / Gare Maritime Iberville", "MTL-VM-0022"),
        87415550: ("Château Ramezay", "MTL-VM-0017"),
        46866809: ("Centre des Sciences de Montréal", "MTL-VM-0021"),
        87415545: ("Caserne Centrale de Pompiers (335 Youville)", "MTL-VM-0026"),
        339686094: ("Édifice Gerald-Godin (Grand Trunk)", "MTL-VM-0027"),
        46866814: ("Ancienne Gare Viger", "MTL-VM-0033"),
        46866829: ("Gare Dalhousie", "MTL-VM-0034"),
        440195613: ("Habitat 67", "MTL-VM-0035"),
    }
    print("\n--- Signature Landmark Ownership Audit (All 35 Blocks) ---")
    for wid, (name, expected_owner) in landmarks.items():
        actual_owner = global_registry.get(str(wid), {}).get("owner_block_id", "NOT_FOUND")
        status = "PASS" if actual_owner == expected_owner else "MISMATCH"
        print(f"  [{status}] {name} (Way {wid}) -> Owner: {actual_owner} (Expected: {expected_owner})")

    # Slice features into each block's dossier.json (if directory/dossier exists)
    slice_features_into_dossiers(PILOT_BLOCKS, buildings, highways, parks, monuments, trees)

    return {
        "total_elements": len(osm_raw.get("elements", [])),
        "total_buildings": len(buildings),
        "total_highways": len(highways),
        "total_trees": len(trees),
        "buildings_registry": global_registry
    }


def slice_features_into_dossiers(blocks, buildings, highways, parks, monuments, trees):
    pad = 0.00045  # ~50m bounding box expansion for streetscape/context

    for b in blocks:
        bid = b["block_id"]
        dpath = os.path.join(BLOCKS_DIR, bid, "dossier.json")
        if not os.path.isfile(dpath):
            continue

        with open(dpath, "r", encoding="utf-8") as f:
            dossier = json.load(f)

        s, w, n, e = [float(v) for v in b["bbox"].split(",")]

        b_bldgs = []
        owned_count = 0
        for bldg in buildings:
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
        for hw in highways:
            hw_in_bbox = any(s - pad <= pt[0] <= n + pad and w - pad <= pt[1] <= e + pad for pt in hw.get("coords_ll", []))
            if hw_in_bbox:
                hw_clean = {k: v for k, v in hw.items() if k != "coords_ll"}
                b_hw.append(hw_clean)

        b_trees = [
            t for t in trees
            if (s - pad <= t["lat"] <= n + pad) and (w - pad <= t["lon"] <= e + pad)
        ]
        b_parks = [
            {k: v for k, v in pk.items() if k != "coords_ll"} for pk in parks
            if (s - pad <= pk["centroid_latlon"][0] <= n + pad) and (w - pad <= pk["centroid_latlon"][1] <= e + pad)
        ]

        b_monuments = [
            m for m in monuments
            if (s - pad <= m["lat"] <= n + pad) and (w - pad <= m["lon"] <= e + pad)
        ]
        if bid == "MTL-VM-0001" and not b_monuments:
            b_monuments = monuments

        dossier["osm_features"] = {
            "buildings": b_bldgs,
            "highways": b_hw,
            "parks_squares": b_parks,
            "monuments": b_monuments,
            "trees": b_trees
        }

        with open(dpath, "w", encoding="utf-8") as f:
            json.dump(dossier, f, indent=2, ensure_ascii=False)

        print(f"  {bid}: {owned_count} STRICTLY OWNED buildings | {len(b_bldgs) - owned_count} context buildings | {len(b_hw)} streets | {len(b_trees)} trees")


def main():
    fetch_or_load_expanded_osm()
    process_and_deduplicate()


if __name__ == "__main__":
    main()
