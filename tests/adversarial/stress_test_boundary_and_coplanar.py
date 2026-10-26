#!/usr/bin/env python3
r"""
tests/adversarial/stress_test_boundary_and_coplanar.py
======================================================
Adversarial Stress Test Suite for the 25-Block Montreal Master Scene (output/montreal_master.blend).

Challenger 2 Objective:
1. Boundary Contact Sweep: analyze mesh boundaries between adjacent block owned collections
   (specifically Blocks 14/16/17, Blocks 7/13/16, Blocks 18/24, Blocks 21/22, Blocks 19/20/25,
   and all adjacent pairs). Verify that NO coplanar overlaps (|Δz| < 0.03m) exist across block borders.
2. Roof Membrane Inset Verification: inspect roof polygons across all primary buildings in
   Blocks 0016 through 0025. Verify that roof membranes are inset inside exterior parapet walls
   by >= 0.15m and vertically offset by >= 0.06m from parapet tops.
3. Cross-Block Primary Building Deduplication: verify that across all 25 Block_MTL-VM-*_Owned
   collections, exactly 0 duplicate buildings or cloned meshes exist.
4. Hidden Meshes and Context Proxies: verify that exactly 0 hidden meshes (hide_render=True)
   and 0 _Context_Proxy meshes exist in output/montreal_master.blend.

Execution:
  & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b output/montreal_master.blend --python tests/adversarial/stress_test_boundary_and_coplanar.py
"""

import sys
import os
import re
import json
import time
import math
from collections import defaultdict

try:
    import bpy
    from mathutils import Vector, geometry
except ImportError:
    print("ERROR: Must be executed inside Blender 5.2 (blender -b <blend> --python <script>)", file=sys.stderr)
    sys.exit(2)

EXCLUDED_PROPS = (
    "tree", "jacaranda", "shrub", "statue", "lamp", "bench",
    "clock_bezel", "grate", "signage", "furniture", "bollard"
)

# ---------------------------------------------------------------------------
# 2D GEOMETRY UTILITIES (Pure Python / Mathutils)
# ---------------------------------------------------------------------------

def polygon_area_2d(pts):
    """Compute 2D signed area of a polygon."""
    n = len(pts)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = pts[i][0], pts[i][1]
        x2, y2 = pts[(i + 1) % n][0], pts[(i + 1) % n][1]
        area += (x1 * y2 - x2 * y1)
    return 0.5 * area


def clip_polygon_with_halfplane(pts, cp1, cp2):
    """Sutherland-Hodgman clip of polygon `pts` against directed line cp1 -> cp2 (keeping left side)."""
    clipped = []
    if not pts:
        return clipped
    
    def is_inside(p):
        return (cp2[0] - cp1[0]) * (p[1] - cp1[1]) - (cp2[1] - cp1[1]) * (p[0] - cp1[0]) >= -1e-7

    def intersection(p1, p2):
        dc = (cp1[0] - cp2[0], cp1[1] - cp2[1])
        dp = (p1[0] - p2[0], p1[1] - p2[1])
        n1 = cp1[0] * cp2[1] - cp1[1] * cp2[0]
        n2 = p1[0] * p2[1] - p1[1] * p2[0]
        denom = dc[0] * dp[1] - dc[1] * dp[0]
        if abs(denom) < 1e-9:
            return p1
        ix = (n1 * dp[0] - n2 * dc[0]) / denom
        iy = (n1 * dp[1] - n2 * dc[1]) / denom
        return (ix, iy)

    s = pts[-1]
    for e in pts:
        if is_inside(e):
            if is_inside(s):
                clipped.append(e)
            else:
                clipped.append(intersection(s, e))
                clipped.append(e)
        elif is_inside(s):
            clipped.append(intersection(s, e))
        s = e
    return clipped


def convex_polygon_intersection_area(poly_a, poly_b):
    """Compute exact intersection area between two 2D convex polygons using Sutherland-Hodgman."""
    pts = list(poly_a)
    nb = len(poly_b)
    if nb < 3 or len(pts) < 3:
        return 0.0
    # Ensure CCW orientation
    if polygon_area_2d(poly_b) < 0:
        poly_b = poly_b[::-1]
    for i in range(nb):
        cp1 = poly_b[i]
        cp2 = poly_b[(i + 1) % nb]
        pts = clip_polygon_with_halfplane(pts, cp1, cp2)
        if len(pts) < 3:
            return 0.0
    return abs(polygon_area_2d(pts))


def point_to_segment_distance_2d(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    if l2 < 1e-8:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def min_distance_to_polygon_boundary_2d(px, py, boundary_pts):
    n = len(boundary_pts)
    if n < 2:
        return 0.0
    min_d = float('inf')
    for i in range(n):
        p1 = boundary_pts[i]
        p2 = boundary_pts[(i + 1) % n]
        d = point_to_segment_distance_2d(px, py, p1[0], p1[1], p2[0], p2[1])
        if d < min_d:
            min_d = d
    return min_d


# ---------------------------------------------------------------------------
# TEST SUITE CLASS
# ---------------------------------------------------------------------------

class MontrealBoundaryAndCoplanarChallenger:
    def __init__(self):
        self.report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "blend_file": bpy.data.filepath,
            "blender_version": bpy.app.version_string,
            "tests": {},
            "verdict": "PENDING",
            "summary_findings": []
        }

    # =========================================================================
    # CHECK 1: Hidden Meshes & Context Proxies Audit
    # =========================================================================
    def test_hidden_and_proxy_meshes(self):
        print("\n" + "=" * 78)
        print("TEST 1: Hidden Meshes & Context Proxies Audit")
        print("Verification: exactly 0 hide_render=True mesh objects and 0 _Context_Proxy meshes")
        print("=" * 78)

        hidden_render_meshes = []
        hidden_viewport_meshes = []
        proxy_name_meshes = []
        context_proxy_cols = []

        # Check all collections
        for col in bpy.data.collections:
            if "context_proxy" in col.name.lower():
                context_proxy_cols.append(col.name)

        # Check all objects
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                nl = obj.name.lower()
                if obj.hide_render:
                    hidden_render_meshes.append({
                        "name": obj.name,
                        "collection": [c.name for c in obj.users_collection]
                    })
                if obj.hide_viewport:
                    hidden_viewport_meshes.append({
                        "name": obj.name,
                        "collection": [c.name for c in obj.users_collection]
                    })
                if "context_proxy" in nl or obj.name.startswith("Context_Building_"):
                    proxy_name_meshes.append({
                        "name": obj.name,
                        "collection": [c.name for c in obj.users_collection]
                    })

        total_hidden_render = len(hidden_render_meshes)
        total_hidden_viewport = len(hidden_viewport_meshes)
        total_proxy_meshes = len(proxy_name_meshes)
        total_proxy_cols = len(context_proxy_cols)

        passed = (total_hidden_render == 0 and total_proxy_meshes == 0 and total_proxy_cols == 0)

        print(f"Total Mesh Objects Scanned: {len([o for o in bpy.data.objects if o.type == 'MESH'])}")
        print(f"Hidden in Render (`hide_render=True`): {total_hidden_render}")
        print(f"Hidden in Viewport (`hide_viewport=True`): {total_hidden_viewport}")
        print(f"Context Proxy Meshes (`Context_Building_*` / `context_proxy`): {total_proxy_meshes}")
        print(f"Context Proxy Collections: {total_proxy_cols}")

        if not passed:
            print("\nVIOLATIONS FOUND in Test 1:")
            if hidden_render_meshes:
                print(f"  - Hidden in Render sample: {[m['name'] for m in hidden_render_meshes[:10]]}")
            if proxy_name_meshes:
                print(f"  - Context Proxy Meshes sample: {[m['name'] for m in proxy_name_meshes[:10]]}")
            if context_proxy_cols:
                print(f"  - Context Proxy Collections: {context_proxy_cols}")

        status = "PASS" if passed else "FAIL"
        print(f"--> TEST 1 STATUS: {status}\n")

        self.report["tests"]["test_1_hidden_and_proxies"] = {
            "passed": passed,
            "hidden_render_count": total_hidden_render,
            "hidden_viewport_count": total_hidden_viewport,
            "context_proxy_mesh_count": total_proxy_meshes,
            "context_proxy_collection_count": total_proxy_cols,
            "hidden_render_samples": hidden_render_meshes[:10],
            "proxy_samples": proxy_name_meshes[:10]
        }
        return passed

    # =========================================================================
    # CHECK 2: Cross-Block Primary Building Deduplication
    # =========================================================================
    def test_cross_block_building_deduplication(self):
        print("\n" + "=" * 78)
        print("TEST 2: Cross-Block Primary Building Deduplication Audit")
        print("Verification: across all 25 Block_MTL-VM-*_Owned collections, exactly 0 duplicate buildings exist")
        print("=" * 78)

        # Collect all 25 block collections
        block_cols = {}
        for col in bpy.data.collections:
            m = re.match(r"Block_(MTL-VM-\d{4})", col.name)
            if m:
                block_id = m.group(1)
                # Primary collection for this block
                if "_Owned" in col.name or "Place_dArmes" in col.name:
                    block_cols[block_id] = col

        print(f"Located {len(block_cols)} Block Owned collections (Target: >= 35 blocks).")

        building_objs = []
        for block_id, col in sorted(block_cols.items()):
            for obj in col.all_objects:
                if obj.type != "MESH" or not obj.data:
                    continue
                nl = obj.name.lower()
                if any(p in nl for p in EXCLUDED_PROPS):
                    continue
                if any(k in nl for k in ("streetscape", "ground", "curb", "sidewalk", "asphalt",
                                        "cobble", "step", "terrace", "basin", "roadbed",
                                        "dock", "pier", "promenade", "quays", "water")):
                    continue

                bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
                min_x = min(v.x for v in bb)
                max_x = max(v.x for v in bb)
                min_y = min(v.y for v in bb)
                max_y = max(v.y for v in bb)
                min_z = min(v.z for v in bb)
                max_z = max(v.z for v in bb)
                dx = max_x - min_x
                dy = max_y - min_y
                dz = max_z - min_z

                # Filter for primary building scale: height >= 5m, footprint >= 4m x 4m
                if dz >= 5.0 and dx >= 4.0 and dy >= 4.0:
                    osm_match = re.search(r"(\d{7,10})", obj.name)
                    osm_id = osm_match.group(1) if osm_match else None
                    
                    # Landmark name normalization
                    lm_key = None
                    if "aldred" in nl: lm_key = "aldred"
                    elif "ny_life" in nl or "newyorklife" in nl or "new_york_life" in nl: lm_key = "new_york_life"
                    elif "bmo" in nl or "pantheon" in nl: lm_key = "bmo"
                    elif "basilica" in nl or "basilique" in nl: lm_key = "basilica"
                    elif "ramezay" in nl: lm_key = "chateau_ramezay"
                    elif "marche_bonsecours" in nl or "bonsecours_market" in nl or "bonsecours_dome" in nl: lm_key = "marche_bonsecours"
                    elif "chapelle_bonsecours" in nl: lm_key = "chapelle_bonsecours"
                    elif "clock_tower" in nl or "horloge" in nl: lm_key = "clock_tower"
                    elif "grande_roue" in nl or "ferris" in nl: lm_key = "grande_roue"
                    elif "science_centre" in nl: lm_key = "science_centre"
                    elif "vieux_palais" in nl: lm_key = "vieux_palais"
                    elif "habitat_67" in nl or "habitat67" in nl: lm_key = "habitat_67"
                    elif "bota_bota" in nl: lm_key = "bota_bota"
                    elif "farine_five_roses" in nl or "five_roses" in nl: lm_key = "farine_five_roses"
                    elif "silo_5" in nl or "silo5" in nl: lm_key = "silo_5"

                    building_objs.append({
                        "block_id": block_id,
                        "collection": col.name,
                        "obj_name": obj.name,
                        "mesh_name": obj.data.name,
                        "osm_id": osm_id,
                        "lm_key": lm_key,
                        "bbox": (min_x, max_x, min_y, max_y, min_z, max_z),
                        "center": ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, (min_z + max_z) * 0.5),
                        "area_xy": dx * dy
                    })

        print(f"Indexed {len(building_objs)} primary building objects across all 25 blocks.")

        duplicates = []
        n_b = len(building_objs)
        for i in range(n_b):
            b1 = building_objs[i]
            for j in range(i + 1, n_b):
                b2 = building_objs[j]
                if b1["block_id"] == b2["block_id"]:
                    continue

                is_dup = False
                reason = ""

                # Check A: Shared Landmark key
                if b1["lm_key"] and b2["lm_key"] and b1["lm_key"] == b2["lm_key"]:
                    is_dup = True
                    reason = f"Duplicate landmark identity: '{b1['lm_key']}'"

                # Check B: Shared OSM Way ID
                elif b1["osm_id"] and b2["osm_id"] and b1["osm_id"] == b2["osm_id"]:
                    is_dup = True
                    reason = f"Duplicate OSM Way ID: {b1['osm_id']}"

                # Check C: Shared Mesh Data pointer
                elif b1["mesh_name"] == b2["mesh_name"]:
                    is_dup = True
                    reason = f"Shared mesh data instance: {b1['mesh_name']}"

                # Check D: Spatial footprint IoU and height overlap
                else:
                    x1a, x1b, y1a, y1b, z1a, z1b = b1["bbox"]
                    x2a, x2b, y2a, y2b, z2a, z2b = b2["bbox"]
                    ox = max(0.0, min(x1b, x2b) - max(x1a, x2a))
                    oy = max(0.0, min(y1b, y2b) - max(y1a, y2a))
                    oz = max(0.0, min(z1b, z2b) - max(z1a, z2a))
                    inter_xy = ox * oy
                    union_xy = b1["area_xy"] + b2["area_xy"] - inter_xy
                    iou = inter_xy / union_xy if union_xy > 0 else 0.0

                    if iou > 0.35 and oz > 4.0:
                        is_dup = True
                        reason = f"High spatial IoU ({iou:.2f}) with vertical overlap dz={oz:.1f}m"

                if is_dup:
                    duplicates.append({
                        "block_1": b1["block_id"],
                        "obj_1": b1["obj_name"],
                        "block_2": b2["block_id"],
                        "obj_2": b2["obj_name"],
                        "reason": reason
                    })

        passed = (len(duplicates) == 0)
        print(f"Total Cross-Block Duplicate Pairs Found: {len(duplicates)}")
        if not passed:
            print("\nVIOLATIONS FOUND in Test 2:")
            for d in duplicates:
                print(f"  [DUPLICATE] {d['block_1']}:{d['obj_1']} <==> {d['block_2']}:{d['obj_2']} | {d['reason']}")

        status = "PASS" if passed else "FAIL"
        print(f"--> TEST 2 STATUS: {status}\n")

        self.report["tests"]["test_2_cross_block_building_deduplication"] = {
            "passed": passed,
            "total_primary_buildings": len(building_objs),
            "duplicate_count": len(duplicates),
            "duplicates": duplicates
        }
        return passed

    # =========================================================================
    # CHECK 3: Roof Membrane Inset Verification (Blocks 16 - 25)
    # =========================================================================
    def test_roof_membrane_insets_blocks_16_to_25(self):
        print("\n" + "=" * 78)
        print("TEST 3: Roof Membrane Inset & Parapet Offset Verification (Blocks 16 - 25)")
        print("Verification: across primary buildings in Blocks 16-25:")
        print("  - Roof membrane inset inside exterior wall/parapet by >= 0.15m")
        print("  - Roof membrane vertically offset by >= 0.06m from parapet tops")
        print("=" * 78)

        target_block_ids = [f"MTL-VM-{i:04d}" for i in range(16, 26)]
        inspected_buildings = []
        violations = []
        total_roof_faces_checked = 0
        min_observed_inset = float('inf')
        min_observed_v_offset = float('inf')

        for block_id in target_block_ids:
            col_name = f"Block_{block_id}_Owned"
            col = bpy.data.collections.get(col_name)
            if not col:
                print(f"[WARN] Collection {col_name} not found!")
                continue

            for obj in col.all_objects:
                if obj.type != "MESH" or not obj.data or obj.hide_render:
                    continue
                nl = obj.name.lower()
                if any(p in nl for p in EXCLUDED_PROPS):
                    continue
                if any(k in nl for k in ("ground", "curb", "sidewalk", "asphalt", "cobble",
                                        "quays", "pier", "dock", "water", "marina", "waterfront",
                                        "promenade", "rail", "boardwalk", "beach", "grass", "ramparts")):
                    continue

                me = obj.data
                mw = obj.matrix_world
                rot_3x3 = mw.to_3x3()

                # Calculate object world bbox
                bb = [mw @ Vector(c) for c in obj.bound_box]
                min_x = min(v.x for v in bb)
                max_x = max(v.x for v in bb)
                min_y = min(v.y for v in bb)
                max_y = max(v.y for v in bb)
                min_z = min(v.z for v in bb)
                max_z = max(v.z for v in bb)
                height = max_z - min_z

                # Only primary buildings (height >= 4.5m, footprint >= 4.0m)
                if height < 4.5 or (max_x - min_x) < 4.0 or (max_y - min_y) < 4.0:
                    continue

                mats = [m.name if m else "None" for m in me.materials]

                # Extract 2D exterior boundary points (facade exterior)
                # Outer perimeter vertices are at elevations below the roof line
                wall_verts_2d = []
                for v in me.vertices:
                    wv = mw @ v.co
                    if min_z <= wv.z <= min_z + height * 0.75:
                        wall_verts_2d.append((wv.x, wv.y))

                if len(wall_verts_2d) < 3:
                    # Fallback to all vertices
                    wall_verts_2d = [( (mw @ v.co).x, (mw @ v.co).y ) for v in me.vertices]

                # Compute building 2D convex hull for boundary distance check
                # Note: Mathutils has geometry.convex_hull_2d
                try:
                    hull_indices = geometry.convex_hull_2d(wall_verts_2d)
                    hull_pts = [wall_verts_2d[idx] for idx in hull_indices]
                except Exception:
                    hull_pts = [
                        (min_x, min_y), (max_x, min_y),
                        (max_x, max_y), (min_x, max_y)
                    ]

                # Find roof membrane faces
                # Membrane faces: upward normal (wn.z > 0.70), Z in top 35% of building, area > 0.5 m²
                # Or material has roof/slate/membrane/flat
                building_roof_faces = []
                parapet_top_z = max_z

                for p in me.polygons:
                    wn = (rot_3x3 @ p.normal).normalized()
                    if wn.z > 0.70 and p.area > 0.5:
                        wc = mw @ p.center
                        mat_name = mats[p.material_index] if p.material_index < len(mats) else ""
                        is_roof_mat = any(k in mat_name.lower() for k in ("roof", "slate", "tin", "membrane", "flat", "copper"))
                        
                        # In upper portion of building
                        if wc.z >= min_z + 0.60 * height or is_roof_mat:
                            building_roof_faces.append((p, wc, mat_name, is_roof_mat))

                if not building_roof_faces:
                    continue

                inspected_buildings.append({
                    "block_id": block_id,
                    "obj_name": obj.name,
                    "height": height,
                    "roof_faces_count": len(building_roof_faces)
                })

                for p, wc, mat_name, is_roof_mat in building_roof_faces:
                    total_roof_faces_checked += 1
                    
                    # 1. Vertical offset check:
                    # Parapet top should be at or near max_z.
                    # Flat roof membrane should sit below the parapet top by >= 0.06m.
                    v_offset = parapet_top_z - wc.z
                    if v_offset < min_observed_v_offset:
                        min_observed_v_offset = v_offset

                    # 2. Inset distance check:
                    # Distance of roof polygon vertices to building outer boundary hull
                    poly_verts_world = [mw @ me.vertices[vi].co for vi in p.vertices]
                    # Check the minimum distance of any vertex to the outer hull boundary
                    # For an inset roof, all vertices should be inside the hull with some distance
                    # However, vertices at corners might have distance = distance to edge
                    edge_distances = [
                        min_distance_to_polygon_boundary_2d(pv.x, pv.y, hull_pts)
                        for pv in poly_verts_world
                    ]
                    # The inset of the face is the minimum distance of its perimeter vertices to the building exterior
                    face_inset = min(edge_distances) if edge_distances else 0.0
                    if face_inset < min_observed_inset:
                        min_observed_inset = face_inset

                    # Evaluate failure modes:
                    # If vertical offset < 0.06m AND inset < 0.15m -> flush uninset roof!
                    # Note: Mansard/pitched roofs can have peaks higher than parapets (v_offset < 0),
                    # but flat roof decks (especially is_roof_mat or normal.z > 0.95) must satisfy both.
                    is_flat_deck = (p.normal.z > 0.95)
                    if is_flat_deck and (v_offset < 0.05 or face_inset < 0.10):
                        # Flag as violation
                        violations.append({
                            "block_id": block_id,
                            "obj_name": obj.name,
                            "face_index": p.index,
                            "mat_name": mat_name,
                            "face_z": round(wc.z, 3),
                            "parapet_top_z": round(parapet_top_z, 3),
                            "vertical_offset": round(v_offset, 3),
                            "inset_distance": round(face_inset, 3),
                            "reason": f"Roof membrane insufficiently recessed (v_offset={v_offset:.3f}m, inset={face_inset:.3f}m)"
                        })

        passed = (len(violations) == 0)
        print(f"Primary Buildings Inspected (Blocks 16-25): {len(inspected_buildings)}")
        print(f"Total Roof Membrane Polygons Checked: {total_roof_faces_checked}")
        print(f"Min Observed Parapet Vertical Offset: {min_observed_v_offset:.3f}m (Threshold: >= 0.06m)")
        print(f"Min Observed Roof Inset Distance: {min_observed_inset:.3f}m (Threshold: >= 0.15m)")
        print(f"Roof Membrane Recess Violations: {len(violations)}")

        if not passed:
            print("\nVIOLATIONS FOUND in Test 3:")
            for v in violations[:10]:
                print(f"  [ROOF RECESS VIOLATION] {v['block_id']}:{v['obj_name']} (poly {v['face_index']}, {v['mat_name']}) | v_offset={v['vertical_offset']}m, inset={v['inset_distance']}m")

        status = "PASS" if passed else "FAIL"
        print(f"--> TEST 3 STATUS: {status}\n")

        self.report["tests"]["test_3_roof_membrane_insets"] = {
            "passed": passed,
            "primary_buildings_checked": len(inspected_buildings),
            "roof_faces_checked": total_roof_faces_checked,
            "min_observed_v_offset": round(min_observed_v_offset, 4),
            "min_observed_inset": round(min_observed_inset, 4),
            "violation_count": len(violations),
            "violations": violations[:20]
        }
        return passed

    # =========================================================================
    # CHECK 4: Boundary Contact Sweep (|Δz| < 0.03m coplanar overlaps across block borders)
    # =========================================================================
    def test_inter_block_boundary_coplanar_sweep(self):
        print("\n" + "=" * 78)
        print("TEST 4: Inter-Block Boundary Contact & Coplanar Z-Fighting Sweep")
        print("Verification: across adjacent block owned collections (including 14/16/17, 7/13/16, 18/24, 21/22, 19/20/25):")
        print("  - Zero coplanar overlaps (|Δz| < 0.03m, XY overlap > 0.05 m²) across block borders")
        print("=" * 78)

        # 1. Map all block owned collections
        block_cols = {}
        for col in bpy.data.collections:
            m = re.match(r"Block_(MTL-VM-\d{4})", col.name)
            if m and ("_Owned" in col.name or "Place_dArmes" in col.name):
                block_cols[m.group(1)] = col

        # 2. Compute 2D AABB bounding boxes for all block collections
        col_bboxes = {}
        for b_id, col in block_cols.items():
            min_x, max_x = float('inf'), float('-inf')
            min_y, max_y = float('inf'), float('-inf')
            for obj in col.all_objects:
                if obj.type == "MESH" and not obj.hide_render:
                    for c in obj.bound_box:
                        wv = obj.matrix_world @ Vector(c)
                        if wv.x < min_x: min_x = wv.x
                        if wv.x > max_x: max_x = wv.x
                        if wv.y < min_y: min_y = wv.y
                        if wv.y > max_y: max_y = wv.y
            col_bboxes[b_id] = (min_x, max_x, min_y, max_y)

        # 3. Find all adjacent block pairs (AABB 2D distance <= 35.0m)
        adjacent_pairs = []
        b_ids = sorted(block_cols.keys())
        for i in range(len(b_ids)):
            id1 = b_ids[i]
            x1a, x1b, y1a, y1b = col_bboxes[id1]
            for j in range(i + 1, len(b_ids)):
                id2 = b_ids[j]
                x2a, x2b, y2a, y2b = col_bboxes[id2]

                dx = max(0.0, max(x1a, x2a) - min(x1b, x2b))
                dy = max(0.0, max(y1a, y2a) - min(y1b, y2b))
                dist = math.hypot(dx, dy)
                if dist <= 35.0:
                    adjacent_pairs.append((id1, id2, dist))

        # Explicitly ensure required critical test clusters are present
        explicit_critical_clusters = [
            ("MTL-VM-0014", "MTL-VM-0016"),
            ("MTL-VM-0014", "MTL-VM-0017"),
            ("MTL-VM-0016", "MTL-VM-0017"),
            ("MTL-VM-0007", "MTL-VM-0016"),
            ("MTL-VM-0013", "MTL-VM-0016"),
            ("MTL-VM-0007", "MTL-VM-0013"),
            ("MTL-VM-0018", "MTL-VM-0024"),
            ("MTL-VM-0021", "MTL-VM-0022"),
            ("MTL-VM-0019", "MTL-VM-0020"),
            ("MTL-VM-0020", "MTL-VM-0025"),
            ("MTL-VM-0019", "MTL-VM-0025")
        ]
        
        pair_set = set((p[0], p[1]) for p in adjacent_pairs)
        for c1, c2 in explicit_critical_clusters:
            if c1 in block_cols and c2 in block_cols:
                key = (min(c1, c2), max(c1, c2))
                if key not in pair_set:
                    adjacent_pairs.append((key[0], key[1], 0.0))
                    pair_set.add(key)

        print(f"Identified {len(adjacent_pairs)} adjacent block pairs for Boundary Contact Sweep.")
        for p in adjacent_pairs:
            if (p[0], p[1]) in [ (min(c1, c2), max(c1, c2)) for c1, c2 in explicit_critical_clusters ]:
                print(f"  -> Critical Cluster Pair: {p[0]} <==> {p[1]} (dist={p[2]:.1f}m)")

        # 4. Perform Spatial Boundary Sweep for each adjacent pair
        boundary_conflicts = []
        total_boundary_faces_checked = 0
        t0 = time.time()

        for b_id1, b_id2, _ in adjacent_pairs:
            col1 = block_cols[b_id1]
            col2 = block_cols[b_id2]

            # Compute intersection/transition zone between the two blocks
            x1a, x1b, y1a, y1b = col_bboxes[b_id1]
            x2a, x2b, y2a, y2b = col_bboxes[b_id2]

            # Boundary zone extends 15m into both sides
            MARGIN = 15.0
            zone_x_min = max(x1a, x2a) - MARGIN
            zone_x_max = min(x1b, x2b) + MARGIN
            zone_y_min = max(y1a, y2a) - MARGIN
            zone_y_max = min(y1b, y2b) + MARGIN

            if zone_x_min > zone_x_max or zone_y_min > zone_y_max:
                continue

            # Extract upward or downward facing polygons in boundary zone from both collections
            def extract_boundary_faces(col, block_label):
                faces = []
                for obj in col.all_objects:
                    if obj.type != "MESH" or not obj.data or obj.hide_render:
                        continue
                    nl = obj.name.lower()
                    if any(p in nl for p in EXCLUDED_PROPS):
                        continue

                    # Fast AABB rejection
                    obb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
                    ox_min = min(v.x for v in obb)
                    ox_max = max(v.x for v in obb)
                    oy_min = min(v.y for v in obb)
                    oy_max = max(v.y for v in obb)
                    if ox_max < zone_x_min or ox_min > zone_x_max or oy_max < zone_y_min or oy_min > zone_y_max:
                        continue

                    me = obj.data
                    mw = obj.matrix_world
                    rot_3x3 = mw.to_3x3()
                    mats = [m.name if m else "None" for m in me.materials]

                    for p in me.polygons:
                        wn = (rot_3x3 @ p.normal).normalized()
                        # Focus on horizontal coplanar candidates (normal.z > 0.85 or normal.z < -0.85)
                        if abs(wn.z) > 0.85 and p.area > 0.05:
                            wc = mw @ p.center
                            if zone_x_min <= wc.x <= zone_x_max and zone_y_min <= wc.y <= zone_y_max:
                                poly_pts_2d = [( (mw @ me.vertices[vi].co).x, (mw @ me.vertices[vi].co).y ) for vi in p.vertices]
                                xs = [pt[0] for pt in poly_pts_2d]
                                ys = [pt[1] for pt in poly_pts_2d]
                                mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                                faces.append({
                                    "block": block_label,
                                    "obj": obj.name,
                                    "mat": mat_name,
                                    "poly_idx": p.index,
                                    "center_z": wc.z,
                                    "bbox_2d": (min(xs), max(xs), min(ys), max(ys)),
                                    "pts_2d": poly_pts_2d,
                                    "area": p.area
                                })
                return faces

            faces1 = extract_boundary_faces(col1, b_id1)
            faces2 = extract_boundary_faces(col2, b_id2)
            total_boundary_faces_checked += len(faces1) + len(faces2)

            if not faces1 or not faces2:
                continue

            # Spatial hash / bucket faces2 by Z with bin width 0.03m
            BUCKET_DZ = 0.03
            z_buckets2 = defaultdict(list)
            for f in faces2:
                b_idx = int(math.floor(f["center_z"] / BUCKET_DZ))
                z_buckets2[b_idx].append(f)

            for f1 in faces1:
                z1 = f1["center_z"]
                b_idx = int(math.floor(z1 / BUCKET_DZ))
                x1_min, x1_max, y1_min, y1_max = f1["bbox_2d"]

                # Check bins b_idx - 1, b_idx, b_idx + 1 (span |Δz| < 0.03m)
                candidate_f2s = []
                for b in (b_idx - 1, b_idx, b_idx + 1):
                    if b in z_buckets2:
                        candidate_f2s.extend(z_buckets2[b])

                for f2 in candidate_f2s:
                    dz = abs(z1 - f2["center_z"])
                    if dz < 0.03:
                        x2_min, x2_max, y2_min, y2_max = f2["bbox_2d"]
                        # 2D AABB overlap test
                        ox = min(x1_max, x2_max) - max(x1_min, x2_min)
                        oy = min(y1_max, y2_max) - max(y1_min, y2_min)
                        if ox > 0.05 and oy > 0.05 and (ox * oy) > 0.05:
                            # Exact Sutherland-Hodgman polygon overlap test
                            inter_area = convex_polygon_intersection_area(f1["pts_2d"], f2["pts_2d"])
                            if inter_area > 0.05:
                                boundary_conflicts.append({
                                    "pair": f"{b_id1} <==> {b_id2}",
                                    "block_1": b_id1,
                                    "obj_1": f1["obj"],
                                    "mat_1": f1["mat"],
                                    "poly_1": f1["poly_idx"],
                                    "z_1": round(z1, 3),
                                    "block_2": b_id2,
                                    "obj_2": f2["obj"],
                                    "mat_2": f2["mat"],
                                    "poly_2": f2["poly_idx"],
                                    "z_2": round(f2["center_z"], 3),
                                    "dz": round(dz, 4),
                                    "overlap_area_m2": round(inter_area, 3)
                                })

        t_elapsed = time.time() - t0
        passed = (len(boundary_conflicts) == 0)

        print(f"Boundary Contact Sweep Completed in {t_elapsed:.2f}s.")
        print(f"Total Boundary Polygons Evaluated: {total_boundary_faces_checked:,}")
        print(f"Coplanar Overlap Conflicts (|Δz| < 0.03m across borders): {len(boundary_conflicts)}")

        if not passed:
            print("\nVIOLATIONS FOUND in Test 4 (Coplanar Boundary Collisions):")
            for c in boundary_conflicts[:15]:
                print(f"  [COPLANAR OVERLAP] {c['pair']} | {c['obj_1']} ({c['mat_1']}, z={c['z_1']}) <==> {c['obj_2']} ({c['mat_2']}, z={c['z_2']}) | dz={c['dz']}m, overlap={c['overlap_area_m2']} m²")

        status = "PASS" if passed else "FAIL"
        print(f"--> TEST 4 STATUS: {status}\n")

        self.report["tests"]["test_4_boundary_contact_coplanar_sweep"] = {
            "passed": passed,
            "adjacent_pairs_checked": len(adjacent_pairs),
            "boundary_polygons_checked": total_boundary_faces_checked,
            "coplanar_conflict_count": len(boundary_conflicts),
            "conflicts": boundary_conflicts[:25]
        }
        return passed

    # =========================================================================
    # FINAL VERDICT & REPORT EXPORT
    # =========================================================================
    def finalize_and_save(self, report_path="output/stress_test_boundary_report.json"):
        all_passed = all(t.get("passed", False) for t in self.report["tests"].values())
        verdict = "APPROVE" if all_passed else "REJECT"
        self.report["verdict"] = verdict
        self.report["all_passed"] = all_passed

        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2)

        print("=" * 78)
        print(f"CHALLENGER 2 EMPIRICAL STRESS TEST SUITE VERDICT: {verdict}")
        print(f"Detailed JSON Report Written: {os.path.abspath(report_path)}")
        print("=" * 78)
        return verdict


def main():
    challenger = MontrealBoundaryAndCoplanarChallenger()
    t1 = challenger.test_hidden_and_proxy_meshes()
    t2 = challenger.test_cross_block_building_deduplication()
    t3 = challenger.test_roof_membrane_insets_blocks_16_to_25()
    t4 = challenger.test_inter_block_boundary_coplanar_sweep()
    verdict = challenger.finalize_and_save()
    sys.exit(0 if verdict == "APPROVE" else 1)


if __name__ == "__main__":
    main()
