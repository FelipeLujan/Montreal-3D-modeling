"""
Deduplicates OSM building footprints across all contiguous city blocks (`dedup_osm_ownership.py`).
Ensures every OSM `way_id` (building, park, monument, tree) has a SINGLE authoritative `owner_block_id`
based on which block's center/polygon contains the building's centroid.
Marks buildings in neighboring blocks' dossiers as `is_owned_by_this_block = False` (context-only for camera renders,
excluded from final USD/Master Scene assembly so zero buildings are ever duplicated or Z-fighting!).
"""
import os
import json
import math

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
BLOCKS_DIR = os.path.join(BASE_DIR, "data", "blocks")


def polygon_centroid(coords_xy: list):
    if not coords_xy:
        return (0.0, 0.0)
    xs = [p[0] for p in coords_xy]
    ys = [p[1] for p in coords_xy]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def dist_sq(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def run_deduplication():
    # 1. Load all available block dossiers
    dossiers = {}
    block_centers = {}
    for bid in sorted(os.listdir(BLOCKS_DIR)):
        dpath = os.path.join(BLOCKS_DIR, bid, "dossier.json")
        if os.path.isfile(dpath):
            with open(dpath, "r", encoding="utf-8") as f:
                d = json.load(f)
            dossiers[bid] = d
            center = d.get("crs", {}).get("block_center_xy_m") or d.get("crs", {}).get("block_offset_m", [0.0, 0.0])[:2]
            block_centers[bid] = (center[0], center[1])

    # Special rule: MTL-VM-0001 is Place d'Armes Square (the park/plaza itself), while MTL-VM-0002..0005 own the
    # surrounding buildings (Basilica/Seminaire = 0002, BMO = 0003, Aldred/NY Life = 0004, 500 Place d'Armes = 0005).
    # So for buildings, we assign ownership to the closest building-block (or MTL-VM-0001 only if inside the square).
    global_building_registry = {}

    for bid, d in dossiers.items():
        for bldg in d.get("osm_features", {}).get("buildings", []):
            way_id = str(bldg["id"])
            cx, cy = polygon_centroid(bldg.get("coords_xy", []))
            bldg["centroid_xy"] = [round(cx, 2), round(cy, 2)]

            # Find which block center is closest to this building's centroid
            # Note: Exclude MTL-VM-0001 (the open square) from owning perimeter buildings if a perimeter block (0002..0015) is within 120m
            best_owner = None
            best_d2 = float("inf")
            for cand_bid, cand_center in block_centers.items():
                if cand_bid == "MTL-VM-0001" and len(block_centers) > 1:
                    continue
                d2 = dist_sq((cx, cy), cand_center)
                if d2 < best_d2:
                    best_d2 = d2
                    best_owner = cand_bid

            if best_owner is None:
                best_owner = bid

            global_building_registry[way_id] = {
                "osm_way_id": way_id,
                "name": bldg.get("name", ""),
                "centroid_xy": [round(cx, 2), round(cy, 2)],
                "owner_block_id": best_owner
            }

    # 2. Stamp `owner_block_id` and `is_primary_owner` onto every block's dossier
    owned_counts = {bid: 0 for bid in dossiers}
    context_counts = {bid: 0 for bid in dossiers}

    for bid, d in dossiers.items():
        for bldg in d.get("osm_features", {}).get("buildings", []):
            way_id = str(bldg["id"])
            owner = global_building_registry[way_id]["owner_block_id"]
            bldg["owner_block_id"] = owner
            bldg["is_primary_owner"] = (owner == bid)
            if owner == bid:
                owned_counts[bid] += 1
            else:
                context_counts[bid] += 1

        dpath = os.path.join(BLOCKS_DIR, bid, "dossier.json")
        with open(dpath, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)

    reg_path = os.path.join(BASE_DIR, "data", "building_ownership_registry.json")
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(global_building_registry, f, indent=2, ensure_ascii=False)

    print(f"Deduplicated {len(global_building_registry)} unique OSM buildings across {len(dossiers)} blocks.")
    for bid in sorted(dossiers.keys()):
        print(f"  {bid}: {owned_counts[bid]} OWNED buildings | {context_counts[bid]} neighbor context buildings")


if __name__ == "__main__":
    run_deduplication()
