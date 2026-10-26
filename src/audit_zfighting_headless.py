#!/usr/bin/env python3
r"""
src/audit_zfighting_headless.py
================================
Headless Blender 5.2 Programmatic Z-Fighting & Street Completeness Audit Suite
for the 15-Block Old Montreal Reconstruction (output/montreal_master.blend).

Evaluates the 4 strict Acceptance Criteria from ORIGINAL_REQUEST.md / PROJECT.md:
  1. Roof/Cornice Conflict Check:
     Z > 3.0m, Area > 1.0 m², normal.z > 0.88, overlap > 1.0 m², |Δz| < 0.05m -> 0 conflicts.
  2. Ground/Street/Sidewalk Conflict Check:
     -0.30m <= Z <= 0.50m, Area > 2.0 m², normal.z > 0.88, overlap > 2.0 m², |Δz| < 0.02m -> 0 conflicts.
  3. Building Duplication Check:
     0 duplicate primary buildings across different Block_MTL-VM-*_Owned collections.
  4. Street Presence Check:
     All 13 major streets have visible, unhidden 3D roadbed geometry with >= 85% centerline coverage.

Execution:
  & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b output/montreal_master.blend --python src/audit_zfighting_headless.py [-- [args]]

Exit Code:
  0 : All 4 Acceptance Criteria PASSED.
  1 : One or more Acceptance Criteria FAILED (conflicts or missing geometry detected).
"""

import sys
import os
import re
import json
import time
import math
import argparse
import unicodedata
from collections import defaultdict

try:
    import bpy
    from mathutils import Vector
except ImportError:
    print("ERROR: This script must be run within Blender 5.2 (e.g. blender -b <file.blend> --python src/audit_zfighting_headless.py)", file=sys.stderr)
    sys.exit(2)

# --- Configuration Constants ---
MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0

# District Bounds in Local Metric Tangent Plane [X_min, X_max], [Y_min, Y_max]
DISTRICT_BBOX = {
    "x_min": -950.0, "x_max": 1400.0,
    "y_min": -850.0, "y_max": 1050.0
}

# The 13 Major Historic & Arterial Streets required across Old Montreal
REQUIRED_STREETS = [
    "Rue Notre-Dame",
    "Rue Saint-Jacques",
    "Rue Saint-Antoine",
    "Rue Saint-Paul",
    "Rue de la Commune",
    "Rue McGill",
    "Rue Saint-Pierre",
    "Rue Saint-François-Xavier",
    "Rue Saint-Sulpice",
    "Côte de la Place d'Armes",
    "Place Jacques-Cartier",
    "Square Victoria",
    "Avenue Viger"
]

# Props and vegetation excluded from building roof & ground polygon audits
EXCLUDED_OBJECT_KEYWORDS = (
    "tree", "jacaranda", "shrub", "statue", "lamp", "bench",
    "clock_bezel", "grate", "signage", "furniture", "bollard"
)

# Objects explicitly excluded as roadbed geometry for street coverage (e.g. fallback planes, orthos)
EXCLUDED_ROADBED_OBJECTS = (
    "ground_street_asphalt_base",
    "ground_satellite_ortho",
    "ground_satellite_ortho.001",
    "georef_satellite_ortho"
)


def latlon_to_local_xy(lat: float, lon: float) -> tuple:
    """Project WGS84 lat/lon to local metric tangent plane relative to Place d'Armes origin."""
    dlat = math.radians(lat - MASTER_ORIGIN_LAT)
    dlon = math.radians(lon - MASTER_ORIGIN_LON)
    mean_lat = math.radians(MASTER_ORIGIN_LAT)
    x = dlon * EARTH_RADIUS_M * math.cos(mean_lat)
    y = dlat * EARTH_RADIUS_M
    return x, y


def normalize_text(text: str) -> str:
    """Remove accents and normalize string for robust text matching."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )


def extract_osm_id(name: str):
    """Extract standard OSM Way ID (7 to 10 digits) from object name."""
    m = re.search(r"(\d{7,10})", name)
    return m.group(1) if m else None


def identify_landmark_key(name: str):
    """Identify landmark buildings known to have cross-block naming variations."""
    nl = normalize_text(name).replace("-", "_").replace(" ", "_")
    if "aldred" in nl:
        return "edifice_aldred"
    if "ny_life" in nl or "newyorklife" in nl or "new_york_life" in nl:
        return "new_york_life"
    if "bmo" in nl or "pantheon" in nl or "beauxarts_annex" in nl:
        return "bmo_complex"
    if ("basilica" in nl or "basilique" in nl or "cathedral" in nl) and ("notre_dame" in nl or "notredame" in nl):
        return "notre_dame_basilica"
    if name.startswith("Basilica_") or "basilica_notre_dame" in nl or "basilique_notre_dame" in nl:
        return "notre_dame_basilica"
    if "habitat" in nl:
        return "habitat_67"
    if "bota" in nl:
        return "bota_bota"
    if "silo" in nl and "5" in nl:
        return "silo_5"
    return None


class MontrealZFightingAuditor:
    """Automated E2E audit suite evaluating 3D geometry against all 4 acceptance criteria."""

    def __init__(self, verbose: bool = False, json_report_path: str = None):
        self.verbose = verbose
        self.json_report_path = json_report_path or os.path.join("output", "audit_zfighting_report.json")
        self.mesh_objs = []
        self.visible_mesh_objs = []
        self.report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "blend_file": bpy.data.filepath,
            "blender_version": bpy.app.version_string,
            "criteria": {},
            "summary": {
                "all_passed": False,
                "failed_criteria_count": 0,
                "passed_criteria_count": 0,
                "total_conflicts": 0,
                "execution_time_seconds": 0.0
            }
        }

    def inspect_scene_inventory(self):
        """Index all mesh objects in the active scene and evaluate render visibility."""
        self.mesh_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data]
        self.visible_mesh_objs = [o for o in self.mesh_objs if not o.hide_render]
        hidden_count = len(self.mesh_objs) - len(self.visible_mesh_objs)
        print(f"\n[Scene Inventory] Total Mesh Objects: {len(self.mesh_objs)} | Visible in Render: {len(self.visible_mesh_objs)} | Hidden Meshes: {hidden_count}")
        self.report["inventory"] = {
            "total_mesh_objects": len(self.mesh_objs),
            "visible_mesh_objects": len(self.visible_mesh_objs),
            "hidden_mesh_objects": hidden_count
        }

    # -------------------------------------------------------------------------
    # Criterion 1: Roof / Cornice Conflict Check
    # -------------------------------------------------------------------------
    def audit_roof_cornice_zfighting(self) -> dict:
        """
        Criterion 1: Roof & Cornice Z-Fighting Check.
        Requirements:
          - Visible mesh objects (excluding vegetation / street props)
          - Face normal tilted < 28.36° from vertical +Z (normal.z > 0.88 in world space)
          - Elevation Z > 3.0m
          - Polygon area > 1.0 m²
          - Overlap: 2D XY AABB overlap > 1.0 m² with vertical proximity |Δz| < 0.05m
          - Conflict if: Obj1 != Obj2 OR Mat1 != Mat2
          - Target: EXACTLY 0 conflicts
        """
        print("\n" + "=" * 78)
        print("CRITERION 1: Roof & Cornice Coplanar Z-Fighting Audit")
        print("Criteria: Z > 3.0m, Area > 1.0 m², normal.z > 0.88, overlap > 1.0 m², |Δz| < 0.05m")
        print("=" * 78)

        t0 = time.time()
        roof_faces = []

        for obj in self.visible_mesh_objs:
            nl = obj.name.lower()
            if any(k in nl for k in EXCLUDED_OBJECT_KEYWORDS):
                continue
            me = obj.data
            mw = obj.matrix_world
            rot_3x3 = mw.to_3x3()
            mats = [m.name if m else "None" for m in me.materials]

            for p in me.polygons:
                # World-space normal check
                wn = (rot_3x3 @ p.normal).normalized()
                if wn.z > 0.88 and p.area > 1.0:
                    wc = mw @ p.center
                    if wc.z > 3.0:
                        mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                        xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                        ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                        roof_faces.append((
                            obj.name, wc.z, min(xs), max(xs), min(ys), max(ys),
                            mat_name, p.index, p.area
                        ))

        t_collect = time.time() - t0
        print(f"Collected {len(roof_faces):,} candidate upward roof polygons (Z > 3.0m, Area > 1.0 m²) in {t_collect:.2f}s.")

        # Z-bucketed spatial sweep for exact O(N) evaluation
        t1 = time.time()
        BUCKET_DZ = 0.05
        buckets = defaultdict(list)
        for f in roof_faces:
            b_idx = int(math.floor(f[1] / BUCKET_DZ))
            buckets[b_idx].append(f)

        for b_idx in buckets:
            buckets[b_idx].sort(key=lambda f: f[2])  # Sort by x_min

        conflict_groups = {}
        total_collision_pairs = 0

        for b_idx, faces_a in buckets.items():
            # 1. Compare within the same bucket (b_idx vs b_idx)
            len_a = len(faces_a)
            for i in range(len_a):
                f1 = faces_a[i]
                o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
                for j in range(i + 1, len_a):
                    f2 = faces_a[j]
                    if f2[2] > x1b:
                        break
                    if abs(z1 - f2[1]) < 0.05:
                        oy = min(y1b, f2[5]) - max(y1a, f2[4])
                        if oy > 0.0:
                            ox = min(x1b, f2[3]) - f2[2]
                            if ox * oy > 1.0:
                                if o1 != f2[0] or m1 != f2[6]:
                                    total_collision_pairs += 1
                                    key = (o1, m1, f2[0], f2[6], round(z1, 2), round(f2[1], 2))
                                    conflict_groups[key] = conflict_groups.get(key, 0) + 1

            # 2. Compare against adjacent neighbor bucket (b_idx vs b_idx + 1)
            if (b_idx + 1) in buckets:
                faces_b = buckets[b_idx + 1]
                for f1 in faces_a:
                    o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
                    for f2 in faces_b:
                        if f2[2] > x1b:
                            break
                        if f2[3] < x1a:
                            continue
                        if abs(z1 - f2[1]) < 0.05:
                            oy = min(y1b, f2[5]) - max(y1a, f2[4])
                            if oy > 0.0:
                                ox = min(x1b, f2[3]) - max(x1a, f2[2])
                                if ox * oy > 1.0:
                                    if o1 != f2[0] or m1 != f2[6]:
                                        total_collision_pairs += 1
                                        key = (o1, m1, f2[0], f2[6], round(z1, 2), round(f2[1], 2))
                                        conflict_groups[key] = conflict_groups.get(key, 0) + 1

        t_eval = time.time() - t1
        num_groups = len(conflict_groups)
        passed = (num_groups == 0)

        print(f"Spatial Sweep Completed in {t_eval:.2f}s.")
        print(f"Result: {num_groups:,} distinct conflict groups ({total_collision_pairs:,} face collision pairs).")

        if num_groups > 0 and self.verbose:
            print("\nTop Roof/Cornice Conflict Groups:")
            for k, cnt in sorted(conflict_groups.items(), key=lambda item: -item[1])[:20]:
                print(f"  [{cnt:3d} pairs] {k[0]} [{k[1]}] (z={k[4]}) <==> {k[2]} [{k[3]}] (z={k[5]})")

        status_str = "PASS" if passed else "FAIL"
        print(f"--> CRITERION 1 STATUS: {status_str} (Target: 0, Actual: {num_groups})")

        return {
            "name": "Roof & Cornice Z-Fighting Check",
            "passed": passed,
            "target": 0,
            "conflict_groups": num_groups,
            "collision_pairs": total_collision_pairs,
            "candidate_faces": len(roof_faces),
            "eval_time_seconds": round(t_collect + t_eval, 3)
        }

    # -------------------------------------------------------------------------
    # Criterion 2: Ground / Street / Sidewalk Conflict Check
    # -------------------------------------------------------------------------
    def audit_ground_street_sidewalk_zfighting(self) -> dict:
        """
        Criterion 2: Ground & Streetscape Z-Fighting Check.
        Requirements:
          - Visible mesh objects (excluding props)
          - Elevation -0.30m <= Z <= 0.50m
          - Polygon area > 2.0 m²
          - Face normal tilted < 28.36° from vertical +Z (normal.z > 0.88)
          - Overlap: 2D XY AABB overlap > 2.0 m² with vertical proximity |Δz| < 0.02m
          - Conflict if: Obj1 != Obj2 OR Mat1 != Mat2
          - Target: EXACTLY 0 conflicts
        """
        print("\n" + "=" * 78)
        print("CRITERION 2: Ground, Street & Sidewalk Coplanar Z-Fighting Audit")
        print("Criteria: -0.30m <= Z <= 0.50m, Area > 2.0 m², normal.z > 0.88, overlap > 2.0 m², |Δz| < 0.02m")
        print("=" * 78)

        t0 = time.time()
        ground_faces = []

        for obj in self.visible_mesh_objs:
            nl = obj.name.lower()
            if any(k in nl for k in EXCLUDED_OBJECT_KEYWORDS):
                continue
            me = obj.data
            mw = obj.matrix_world
            rot_3x3 = mw.to_3x3()
            mats = [m.name if m else "None" for m in me.materials]

            for p in me.polygons:
                wn = (rot_3x3 @ p.normal).normalized()
                if wn.z > 0.88 and p.area > 2.0:
                    wc = mw @ p.center
                    if -0.30 <= wc.z <= 0.50:
                        mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                        xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                        ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                        ground_faces.append((
                            obj.name, wc.z, min(xs), max(xs), min(ys), max(ys),
                            mat_name, p.index, p.area
                        ))

        t_collect = time.time() - t0
        print(f"Collected {len(ground_faces):,} candidate upward ground polygons (-0.30m <= Z <= 0.50m, Area > 2.0 m²) in {t_collect:.2f}s.")

        t1 = time.time()
        BUCKET_DZ = 0.02
        buckets = defaultdict(list)
        for f in ground_faces:
            b_idx = int(math.floor(f[1] / BUCKET_DZ))
            buckets[b_idx].append(f)

        for b_idx in buckets:
            buckets[b_idx].sort(key=lambda f: f[2])

        conflict_groups = {}
        total_collision_pairs = 0

        for b_idx, faces_a in buckets.items():
            len_a = len(faces_a)
            # 1. Compare within same bucket
            for i in range(len_a):
                f1 = faces_a[i]
                o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
                for j in range(i + 1, len_a):
                    f2 = faces_a[j]
                    if f2[2] > x1b:
                        break
                    if abs(z1 - f2[1]) < 0.02:
                        oy = min(y1b, f2[5]) - max(y1a, f2[4])
                        if oy > 0.0:
                            ox = min(x1b, f2[3]) - f2[2]
                            if ox * oy > 2.0:
                                if o1 != f2[0] or m1 != f2[6]:
                                    total_collision_pairs += 1
                                    key = (o1, m1, f2[0], f2[6], round(z1, 3), round(f2[1], 3))
                                    conflict_groups[key] = conflict_groups.get(key, 0) + 1

            # 2. Compare against neighbor bucket
            if (b_idx + 1) in buckets:
                faces_b = buckets[b_idx + 1]
                for f1 in faces_a:
                    o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
                    for f2 in faces_b:
                        if f2[2] > x1b:
                            break
                        if f2[3] < x1a:
                            continue
                        if abs(z1 - f2[1]) < 0.02:
                            oy = min(y1b, f2[5]) - max(y1a, f2[4])
                            if oy > 0.0:
                                ox = min(x1b, f2[3]) - max(x1a, f2[2])
                                if ox * oy > 2.0:
                                    if o1 != f2[0] or m1 != f2[6]:
                                        total_collision_pairs += 1
                                        key = (o1, m1, f2[0], f2[6], round(z1, 3), round(f2[1], 3))
                                        conflict_groups[key] = conflict_groups.get(key, 0) + 1

        t_eval = time.time() - t1
        num_groups = len(conflict_groups)
        passed = (num_groups == 0)

        print(f"Spatial Sweep Completed in {t_eval:.2f}s.")
        print(f"Result: {num_groups:,} distinct ground conflict groups ({total_collision_pairs:,} face collision pairs).")

        if num_groups > 0 and self.verbose:
            print("\nTop Ground / Plinth Conflict Groups:")
            for k, cnt in sorted(conflict_groups.items(), key=lambda item: -item[1])[:20]:
                print(f"  [{cnt:3d} pairs] {k[0]} [{k[1]}] (z={k[4]}) <==> {k[2]} [{k[3]}] (z={k[5]})")

        status_str = "PASS" if passed else "FAIL"
        print(f"--> CRITERION 2 STATUS: {status_str} (Target: 0, Actual: {num_groups})")

        return {
            "name": "Ground & Streetscape Z-Fighting Check",
            "passed": passed,
            "target": 0,
            "conflict_groups": num_groups,
            "collision_pairs": total_collision_pairs,
            "candidate_faces": len(ground_faces),
            "eval_time_seconds": round(t_collect + t_eval, 3)
        }

    # -------------------------------------------------------------------------
    # Criterion 3: Building Duplication Check
    # -------------------------------------------------------------------------
    def audit_building_duplication(self) -> dict:
        """
        Criterion 3: Building Duplication Check.
        Requirements:
          - Zero duplicate primary buildings across different Block_MTL-VM-*_Owned collections.
          - Duplicate definition:
            a) Two visible primary building objects across different blocks share the same OSM Way ID.
            b) Two visible primary building objects across different blocks match the same landmark identity
               (e.g. Édifice Aldred, New York Life, BMO Pantheon/Annex, Notre-Dame Basilica).
            c) Two visible standalone building objects in different blocks exhibit high 3D spatial overlap
               (XY IoU > 0.40 and Z-overlap > 5.0m).
          - Target: EXACTLY 0 duplicate building pairs.
        """
        print("\n" + "=" * 78)
        print("CRITERION 3: Cross-Block Primary Building Duplication Audit")
        print("Criteria: Zero duplicate primary buildings across Block_MTL-VM-*_Owned collections")
        print("=" * 78)

        t0 = time.time()

        # Find all block owned collections (e.g. Block_MTL-VM-0001_Place_dArmes, Block_MTL-VM-0002_Owned, etc.)
        owned_cols = [
            c for c in bpy.data.collections
            if ("Block_MTL-VM-" in c.name and ("_Owned" in c.name or "0001" in c.name))
        ]
        print(f"Identified {len(owned_cols)} Block Owned collections.")

        building_candidates = []
        for col in owned_cols:
            for obj in col.all_objects:
                if obj.type == "MESH" and not obj.hide_render:
                    nl = obj.name.lower()
                    if any(k in nl for k in EXCLUDED_OBJECT_KEYWORDS) or any(k in nl for k in (
                        "streetscape", "ground", "curb", "sidewalk", "asphalt", "cobble",
                        "step", "hw_", "terrace", "basin", "monument", "props"
                    )):
                        continue

                    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
                    min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
                    min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)
                    min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
                    dx = max_x - min_x
                    dy = max_y - min_y
                    dz = max_z - min_z

                    # Must have primary building scale (height >= 6m, footprint >= 5m x 5m)
                    if dz >= 6.0 and dx >= 5.0 and dy >= 5.0:
                        osm_id = extract_osm_id(obj.name)
                        lm_key = identify_landmark_key(obj.name)
                        building_candidates.append({
                            "col": col.name,
                            "name": obj.name,
                            "bbox": (min_x, max_x, min_y, max_y, min_z, max_z),
                            "osm_id": osm_id,
                            "lm_key": lm_key,
                            "area": dx * dy
                        })

        print(f"Collected {len(building_candidates)} primary building candidates across block owned collections.")

        duplicates = []
        num_candidates = len(building_candidates)

        for i in range(num_candidates):
            b1 = building_candidates[i]
            for j in range(i + 1, num_candidates):
                b2 = building_candidates[j]
                if b1["col"] == b2["col"]:
                    continue

                is_duplicate = False
                reason = ""

                # Test 1: Shared Landmark Identity
                if b1["lm_key"] and b2["lm_key"] and b1["lm_key"] == b2["lm_key"]:
                    is_duplicate = True
                    reason = f"Duplicate Landmark: '{b1['lm_key']}'"

                # Test 2: Shared OSM Way ID
                elif b1["osm_id"] and b2["osm_id"] and b1["osm_id"] == b2["osm_id"]:
                    is_duplicate = True
                    reason = f"Duplicate OSM Way ID: {b1['osm_id']}"

                # Test 3: Spatial Footprint IoU & Height Overlap
                else:
                    x1a, x1b, y1a, y1b, z1a, z1b = b1["bbox"]
                    x2a, x2b, y2a, y2b, z2a, z2b = b2["bbox"]

                    ox = max(0.0, min(x1b, x2b) - max(x1a, x2a))
                    oy = max(0.0, min(y1b, y2b) - max(y1a, y2a))
                    oz = max(0.0, min(z1b, z2b) - max(z1a, z2a))

                    inter_xy = ox * oy
                    union_xy = b1["area"] + b2["area"] - inter_xy
                    iou_xy = (inter_xy / union_xy) if union_xy > 0 else 0.0

                    if iou_xy > 0.40 and oz > 5.0:
                        is_duplicate = True
                        reason = f"High spatial IoU ({iou_xy:.2f}) with Z-overlap={oz:.1f}m"

                if is_duplicate:
                    duplicates.append({
                        "block_a": b1["col"],
                        "object_a": b1["name"],
                        "block_b": b2["col"],
                        "object_b": b2["name"],
                        "reason": reason
                    })

        t_eval = time.time() - t0
        passed = (len(duplicates) == 0)

        print(f"Duplication Audit Completed in {t_eval:.2f}s.")
        print(f"Result: {len(duplicates)} duplicate primary building instances detected.")

        if duplicates:
            print("\nDetected Duplicate Primary Buildings:")
            for d in duplicates:
                print(f"  [DUPLICATE] {d['block_a']} :: {d['object_a']}  <===>  {d['block_b']} :: {d['object_b']} | {d['reason']}")

        status_str = "PASS" if passed else "FAIL"
        print(f"--> CRITERION 3 STATUS: {status_str} (Target: 0, Actual: {len(duplicates)})")

        return {
            "name": "Primary Building Duplication Check",
            "passed": passed,
            "target": 0,
            "duplicate_count": len(duplicates),
            "duplicates": duplicates,
            "eval_time_seconds": round(t_eval, 3)
        }

    # -------------------------------------------------------------------------
    # Criterion 4: Street Presence Check
    # -------------------------------------------------------------------------
    def audit_street_presence(self) -> dict:
        """
        Criterion 4: Street Presence Check.
        Requirements:
          - Ingests centerline geometry from data/open_data/old_montreal_osm.json for all 13 major streets.
          - Verifies that visible, unhidden 3D roadbed geometry exists covering >= 85% of each street's corridor
            within the district bounding box.
          - Excludes fallback planar bases (Ground_Street_Asphalt_Base, satellite orthos).
          - Target: ALL 13 streets PASS.
        """
        print("\n" + "=" * 78)
        print("CRITERION 4: Street Network Completeness Audit (13 Major Streets)")
        print("Criteria: All 13 streets have visible, unhidden 3D roadbed geometry (>= 85% coverage)")
        print("=" * 78)

        t0 = time.time()
        osm_path = os.path.join("data", "open_data", "old_montreal_osm.json")

        if not os.path.isfile(osm_path):
            print(f"ERROR: OSM dataset not found at {osm_path}", file=sys.stderr)
            return {
                "name": "Street Presence Check",
                "passed": False,
                "error": f"Missing OSM file: {osm_path}"
            }

        with open(osm_path, "r", encoding="utf-8") as f:
            osm_data = json.load(f)

        elements = osm_data.get("elements", [])
        nodes = {e["id"]: (e["lat"], e["lon"]) for e in elements if e.get("type") == "node" and "lat" in e}

        # Build local XY centerlines for the 13 required streets
        street_points = {s: [] for s in REQUIRED_STREETS}
        for e in elements:
            if e.get("type") == "way" and "tags" in e and "highway" in e["tags"]:
                name = e["tags"].get("name", "")
                norm_wname = normalize_text(name)
                for s in REQUIRED_STREETS:
                    if normalize_text(s) in norm_wname:
                        for nid in e.get("nodes", []):
                            if nid in nodes:
                                street_points[s].append(latlon_to_local_xy(*nodes[nid]))

        # Collect all visible 3D roadbed / streetscape meshes in the scene
        visible_road_objs = []
        for obj in self.visible_mesh_objs:
            nl = obj.name.lower()
            if any(k in nl for k in EXCLUDED_ROADBED_OBJECTS):
                continue
            bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
            min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
            min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)

            # Road elevation check (-0.30m <= Z <= 0.50m)
            if min_z < 0.50 and max_z > -0.30:
                mats = [m.name.lower() for m in obj.data.materials if m]
                is_road = (
                    any(k in nl for k in ("street", "road", "asphalt", "cobble", "ground", "plaza", "sidewalk", "highway", "hw_")) or
                    any(any(k in m for k in ("asphalt", "cobble", "street", "plaza", "road")) for m in mats)
                )
                if is_road:
                    visible_road_objs.append((obj.name, min_x, max_x, min_y, max_y))

        print(f"Collected {len(visible_road_objs)} visible detailed roadbed/streetscape objects (excluding fallback base plane).")

        street_results = {}
        all_passed = True

        for s in REQUIRED_STREETS:
            raw_pts = street_points[s]
            # Filter to district bounding box
            pts = [
                p for p in raw_pts
                if DISTRICT_BBOX["x_min"] <= p[0] <= DISTRICT_BBOX["x_max"] and
                   DISTRICT_BBOX["y_min"] <= p[1] <= DISTRICT_BBOX["y_max"]
            ]

            if not pts:
                street_results[s] = {"status": "FAIL", "coverage_pct": 0.0, "points": 0, "covered": 0}
                all_passed = False
                print(f"  {s:26s} : FAIL (No points found inside district bounds)")
                continue

            # Check coverage against specific roadbed object for this street (with 4m street margin)
            norm_s = normalize_text(s)
            safe_s = "roadbed_" + norm_s.replace(" ", "_").replace("'", "").replace("-", "_")
            matching_road_objs = [
                (oname, x1, x2, y1, y2)
                for oname, x1, x2, y1, y2 in visible_road_objs
                if safe_s in normalize_text(oname).replace("'", "").replace("-", "_")
                or norm_s in normalize_text(oname)
            ]

            covered_count = 0
            if matching_road_objs:
                for x, y in pts:
                    if any(x1 - 4.0 <= x <= x2 + 4.0 and y1 - 4.0 <= y <= y2 + 4.0 for _, x1, x2, y1, y2 in matching_road_objs):
                        covered_count += 1
            else:
                covered_count = 0

            cov_pct = (covered_count / len(pts)) * 100.0
            street_pass = (cov_pct >= 85.0)
            if not street_pass:
                all_passed = False

            status_str = "PASS" if street_pass else "FAIL"
            street_results[s] = {
                "status": status_str,
                "coverage_pct": round(cov_pct, 1),
                "total_points": len(pts),
                "covered_points": covered_count
            }
            print(f"  {s:26s} : {status_str:4s} ({covered_count:3d}/{len(pts):3d} pts = {cov_pct:5.1f}%)")

        t_eval = time.time() - t0
        passed_streets_count = sum(1 for r in street_results.values() if r["status"] == "PASS")
        status_overall = "PASS" if all_passed else "FAIL"

        print(f"Street Presence Audit Completed in {t_eval:.2f}s.")
        print(f"--> CRITERION 4 STATUS: {status_overall} ({passed_streets_count}/13 Streets Passed)")

        return {
            "name": "Street Presence Check (13 Major Streets)",
            "passed": all_passed,
            "target": "13/13 Streets PASS",
            "passed_count": passed_streets_count,
            "total_required": len(REQUIRED_STREETS),
            "streets": street_results,
            "eval_time_seconds": round(t_eval, 3)
        }

    # -------------------------------------------------------------------------
    # Master Execution & Report Emission
    # -------------------------------------------------------------------------
    def run_all_audits(self) -> bool:
        """Run all 4 audit checks sequentially and output structured summary."""
        start_time = time.time()
        print("\n" + "#" * 78)
        print("  OLD MONTREAL 3D RECONSTRUCTION: PROGRAMMATIC AUDIT SUITE")
        print("  Blender Headless Master World Verification")
        print("#" * 78)

        self.inspect_scene_inventory()

        c1 = self.audit_roof_cornice_zfighting()
        c2 = self.audit_ground_street_sidewalk_zfighting()
        c3 = self.audit_building_duplication()
        c4 = self.audit_street_presence()

        total_time = time.time() - start_time

        self.report["criteria"] = {
            "1_roof_cornice_zfighting": c1,
            "2_ground_street_sidewalk_zfighting": c2,
            "3_building_duplication": c3,
            "4_street_presence": c4
        }

        all_passed = c1["passed"] and c2["passed"] and c3["passed"] and c4["passed"]
        passed_count = sum(1 for c in (c1, c2, c3, c4) if c["passed"])
        failed_count = 4 - passed_count
        total_conflicts = c1.get("conflict_groups", 0) + c2.get("conflict_groups", 0) + c3.get("duplicate_count", 0)

        self.report["summary"] = {
            "all_passed": all_passed,
            "passed_criteria_count": passed_count,
            "failed_criteria_count": failed_count,
            "total_conflicts": total_conflicts,
            "execution_time_seconds": round(total_time, 3)
        }

        # Print Clean Summary Table
        print("\n" + "=" * 78)
        print("                     AUDIT SUITE FINAL SUMMARY")
        print("=" * 78)
        print(f" {'Criterion':<46} | {'Target':<10} | {'Actual':<10} | {'Status':<6}")
        print("-" * 78)
        c1_actual = f"{c1['conflict_groups']} groups"
        c1_status = "PASS" if c1["passed"] else "FAIL"
        print(f" 1. Roof/Cornice Z-Fighting (Z>3m, overlap>1m²)   | {'0 groups':<10} | {c1_actual:<10} | {c1_status:<6}")

        c2_actual = f"{c2['conflict_groups']} groups"
        c2_status = "PASS" if c2["passed"] else "FAIL"
        print(f" 2. Ground/Street Z-Fighting (-0.3m<=Z<=0.5m)    | {'0 groups':<10} | {c2_actual:<10} | {c2_status:<6}")

        c3_actual = f"{c3['duplicate_count']} dups"
        c3_status = "PASS" if c3["passed"] else "FAIL"
        print(f" 3. Duplicate Primary Buildings Across Blocks    | {'0 dups':<10} | {c3_actual:<10} | {c3_status:<6}")

        c4_actual = f"{c4['passed_count']}/13"
        c4_status = "PASS" if c4["passed"] else "FAIL"
        print(f" 4. Street Presence (13 Major Thoroughfares)     | {'13/13':<10} | {c4_actual:<10} | {c4_status:<6}")
        hidden_count = self.report.get("inventory", {}).get("hidden_mesh_objects", 0)
        h_status = "PASS" if hidden_count == 0 else "FAIL"
        print(f" 5. Hidden Proxy Meshes (hide_render=True)       | {'0 meshes':<10} | {hidden_count:<10} | {h_status:<6}")
        print("=" * 78)
        print(f" TOTAL CONFLICTS / ANOMALIES: {total_conflicts:,}")
        print(f" AUDIT RESULT: {'ALL ACCEPTANCE CRITERIA PASSED [OK]' if all_passed else 'CRITERIA UNMET [FAILURES DETECTED]'}")
        print(f" Total Execution Time: {total_time:.2f} seconds")
        print("=" * 78)

        # Write structured JSON report
        try:
            os.makedirs(os.path.dirname(self.json_report_path), exist_ok=True)
            with open(self.json_report_path, "w", encoding="utf-8") as f:
                json.dump(self.report, f, indent=2)
            print(f"[Report] Structured JSON report saved to: {self.json_report_path}\n")
        except Exception as e:
            print(f"[Report Warning] Could not write JSON report: {e}", file=sys.stderr)

        return all_passed


def main():
    # Parse CLI flags after '--' in Blender headless invocation
    argv = sys.argv
    if "--" in argv:
        args_to_parse = argv[argv.index("--") + 1:]
    else:
        args_to_parse = []

    parser = argparse.ArgumentParser(description="Old Montreal Headless Blender Z-Fighting & Street Network Audit")
    parser.add_argument("--json-report", type=str, default=None, help="Path to write JSON results report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed conflict group listings")
    parser.add_argument("--allow-baseline-failures", action="store_true", help="Exit 0 even if failures exist (for diagnostic inspections)")

    parsed_args = parser.parse_args(args_to_parse)

    auditor = MontrealZFightingAuditor(
        verbose=parsed_args.verbose,
        json_report_path=parsed_args.json_report
    )

    all_passed = auditor.run_all_audits()

    if all_passed or parsed_args.allow_baseline_failures:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
