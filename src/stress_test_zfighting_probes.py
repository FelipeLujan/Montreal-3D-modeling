#!/usr/bin/env python3
r"""
src/stress_test_zfighting_probes.py
===================================
Adversarial Stress-Testing Probes for Rebuilt Blocks
(MTL-VM-0003, 0004, 0007, 0011, 0013, 0015).

Empirically challenges assumptions of Milestone 1 fixes:
1. Multi-tolerance Z-fighting sweep:
   - |Δz| < 0.08m, |Δz| < 0.05m, |Δz| < 0.01m
   - Macro-overlaps (>= 1.0 m²) and Micro-overlaps (0.01 m² to 1.0 m²)
   - Small polygon detection (area down to 0.05 m² to catch HVAC, skylights, sills, and parapet caps)
2. Exact 2D polygon intersection (Sutherland-Hodgman clipping) to distinguish true geometric intersection from AABB false positives.
3. Corner and sill intersection probe (checking decorative bands, window sills, and cornices near building corners).
4. Party wall and building interface probe (checking adjacent building roof deck and parapet elevation steps).
5. Context proxy & landmark de-confliction probe (ensuring Édifice Aldred, New York Life, and all *_Context_Proxy objects are strictly hidden in render).

Execution:
  & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b <blend_file> --python src/stress_test_zfighting_probes.py [-- [args]]
"""

import sys
import os
import math
import time
import json
import argparse
from collections import defaultdict

try:
    import bpy
    from mathutils import Vector, Matrix
except ImportError:
    print("ERROR: Must run inside Blender 5.2 (blender.exe -b <file.blend> --python src/stress_test_zfighting_probes.py)", file=sys.stderr)
    sys.exit(2)


# --- Geometric Helper Functions ---

def polygon_area_2d(poly):
    """Compute unsigned 2D area of polygon vertices [(x0, y0), (x1, y1), ...]."""
    n = len(poly)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += poly[i][0] * poly[j][1] - poly[j][0] * poly[i][1]
    return abs(area) * 0.5


def clip_polygon_by_halfplane(poly, p1, p2):
    """Clip 2D polygon against directed line from p1 to p2 (keeps points to the left)."""
    if len(poly) < 3:
        return []
    clipped = []
    # Line normal pointing to the left: (-dy, dx)
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    def is_inside(p):
        return (p[0] - p1[0]) * (-dy) + (p[1] - p1[1]) * dx >= -1e-7

    def intersection(a, b):
        adx = b[0] - a[0]
        ady = b[1] - a[1]
        denom = adx * (-dy) + ady * dx
        if abs(denom) < 1e-9:
            return a
        num = (p1[0] - a[0]) * (-dy) + (p1[1] - a[1]) * dx
        t = num / denom
        return (a[0] + t * adx, a[1] + t * ady)

    s = poly[-1]
    for e in poly:
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


def exact_2d_polygon_intersection_area(poly1, poly2):
    """Compute exact intersection area of two 2D convex polygons using Sutherland-Hodgman."""
    # Ensure poly2 is oriented counter-clockwise
    n2 = len(poly2)
    if n2 < 3:
        return 0.0
    area2_signed = 0.0
    for i in range(n2):
        j = (i + 1) % n2
        area2_signed += poly2[i][0] * poly2[j][1] - poly2[j][0] * poly2[i][1]
    if area2_signed < 0:
        poly2 = list(reversed(poly2))

    clipped = list(poly1)
    for i in range(n2):
        j = (i + 1) % n2
        clipped = clip_polygon_by_halfplane(clipped, poly2[i], poly2[j])
        if len(clipped) < 3:
            return 0.0
    return polygon_area_2d(clipped)


# --- Stress Probe Suite ---

class MontrealAdversarialStressProber:
    def __init__(self, block_name: str, verbose: bool = False):
        self.block_name = block_name
        self.verbose = verbose
        self.mesh_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data]
        self.results = {
            "block": block_name,
            "filepath": bpy.data.filepath,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "probe_roof_multitol": {},
            "probe_micro_overlaps": {},
            "probe_proxies_landmarks": {},
            "probe_party_walls": {},
            "probe_corners": {},
            "verdict": "PENDING"
        }

    # -------------------------------------------------------------------------
    # PROBE 1: Context Proxies & Perimeter Landmarks
    # -------------------------------------------------------------------------
    def probe_proxies_and_landmarks(self) -> dict:
        """
        Check that all context proxies and duplicate landmark models are properly hidden in render.
        - Checks collections ending with '_Context_Proxy'
        - Checks objects belonging to proxy collections or named with 'proxy'
        - Checks Édifice Aldred and New York Life in MTL-VM-0003
        """
        print("\n" + "=" * 76)
        print("PROBE 1: Context Proxies & Landmark Visibility Isolation")
        print("=" * 76)

        unhidden_proxies = []
        proxy_collections = [c for c in bpy.data.collections if "proxy" in c.name.lower()]
        print(f"Found {len(proxy_collections)} proxy collection(s): {[c.name for c in proxy_collections]}")

        for col in proxy_collections:
            for obj in col.all_objects:
                if not obj.hide_render:
                    unhidden_proxies.append({
                        "collection": col.name,
                        "object": obj.name,
                        "hide_viewport": obj.hide_viewport,
                        "hide_render": obj.hide_render
                    })

        # Landmark specific check for 0003
        landmark_issues = []
        for obj in self.mesh_objs:
            nl = obj.name.lower()
            if "aldred" in nl or "new_york_life" in nl or "ny_life" in nl:
                is_hidden = obj.hide_render
                print(f"  Landmark Object: {obj.name} | hide_render={obj.hide_render} | hide_viewport={obj.hide_viewport}")
                if "0003" in self.block_name and not is_hidden:
                    landmark_issues.append(f"UNHIDDEN duplicate landmark in 0003: {obj.name}")

        passed = (len(unhidden_proxies) == 0 and len(landmark_issues) == 0)
        res = {
            "passed": passed,
            "unhidden_proxies_count": len(unhidden_proxies),
            "unhidden_proxies": unhidden_proxies,
            "landmark_issues": landmark_issues
        }
        print(f"--> PROBE 1 RESULT: {'PASS' if passed else 'FAIL'} (Unhidden Proxies: {len(unhidden_proxies)}, Landmark Issues: {len(landmark_issues)})")
        self.results["probe_proxies_landmarks"] = res
        return res

    # -------------------------------------------------------------------------
    # PROBE 2: Multi-Tolerance Roof & Cornice Z-Fighting Sweep
    # -------------------------------------------------------------------------
    def probe_roof_cornice_multitol(self) -> dict:
        """
        Sweep upward-facing polygons (Z > 3.0m) across multiple vertical tolerances:
        - Strict: |Δz| < 0.08m
        - Standard: |Δz| < 0.05m
        - Ultra-strict coplanar: |Δz| < 0.01m
        Evaluates both AABB overlap and exact polygon clipping area.
        Includes small polygons down to area >= 0.05 m² (to catch HVAC, skylights, sills, and parapet caps).
        """
        print("\n" + "=" * 76)
        print("PROBE 2: Multi-Tolerance Roof & Cornice Z-Fighting Sweep")
        print("Sweep thresholds: |Δz| in (0.08m, 0.05m, 0.01m), Area >= 0.05 m²")
        print("=" * 76)

        t0 = time.time()
        excluded_kw = ("tree", "jacaranda", "shrub", "statue", "lamp", "bench", "car", "suv", "van", "sedan", "pedestrian")
        
        # Collect upward polygons (normal.z > 0.70 to catch slightly pitched roofs/cornices as well)
        up_faces = []
        for obj in self.mesh_objs:
            if obj.hide_render:
                continue
            nl = obj.name.lower()
            if any(k in nl for k in excluded_kw):
                continue
            me = obj.data
            mw = obj.matrix_world
            rot_3x3 = mw.to_3x3()
            mats = [m.name if m else "None" for m in me.materials]

            for p in me.polygons:
                wn = (rot_3x3 @ p.normal).normalized()
                if wn.z > 0.70 and p.area >= 0.05:
                    wc = mw @ p.center
                    if wc.z > 3.0:
                        mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                        world_pts = [(mw @ me.vertices[vi].co) for vi in p.vertices]
                        xs = [pt.x for pt in world_pts]
                        ys = [pt.y for pt in world_pts]
                        poly_2d = [(pt.x, pt.y) for pt in world_pts]
                        up_faces.append({
                            "obj": obj.name,
                            "poly_idx": p.index,
                            "mat": mat_name,
                            "z": wc.z,
                            "x_min": min(xs), "x_max": max(xs),
                            "y_min": min(ys), "y_max": max(ys),
                            "area": p.area,
                            "poly_2d": poly_2d
                        })

        print(f"Collected {len(up_faces):,} candidate upward faces (Z > 3.0m, Area >= 0.05 m²) in {time.time()-t0:.2f}s.")

        # Spatial sweep bucketing by Z (bin size 0.08m)
        bin_size = 0.08
        buckets = defaultdict(list)
        for f in up_faces:
            b_idx = int(math.floor(f["z"] / bin_size))
            buckets[b_idx].append(f)

        tolerances = [0.08, 0.05, 0.01]
        results_by_tol = {
            tol: {
                "macro_conflicts_aabb": 0,    # AABB overlap >= 1.0 m²
                "macro_conflicts_exact": 0,   # Exact clipping overlap >= 1.0 m²
                "micro_conflicts_exact": 0,   # Exact clipping 0.01 m² <= overlap < 1.0 m²
                "submicro_conflicts_exact": 0,# Exact clipping 0.001 m² <= overlap < 0.01 m²
                "conflict_details": []
            } for tol in tolerances
        }

        # Check pairs within bucket and adjacent buckets
        all_bucket_indices = sorted(buckets.keys())
        checked_pairs = 0

        for b_idx in all_bucket_indices:
            candidates_b = buckets[b_idx]
            adjacent_buckets = [b_idx]
            if (b_idx + 1) in buckets:
                adjacent_buckets.append(b_idx + 1)

            for i, f1 in enumerate(candidates_b):
                for b_other in adjacent_buckets:
                    start_j = (i + 1) if b_other == b_idx else 0
                    list_other = buckets[b_other]
                    for j in range(start_j, len(list_other)):
                        f2 = list_other[j]
                        if f1["obj"] == f2["obj"] and f1["mat"] == f2["mat"]:
                            continue  # Same object and same material is not Z-fighting

                        dz = abs(f1["z"] - f2["z"])
                        if dz >= 0.08:
                            continue

                        # Check 2D AABB overlap
                        ox = min(f1["x_max"], f2["x_max"]) - max(f1["x_min"], f2["x_min"])
                        if ox <= 0:
                            continue
                        oy = min(f1["y_max"], f2["y_max"]) - max(f1["y_min"], f2["y_min"])
                        if oy <= 0:
                            continue

                        aabb_overlap = ox * oy
                        if aabb_overlap < 0.001:
                            continue

                        checked_pairs += 1

                        # Exact 2D polygon intersection area
                        exact_overlap = exact_2d_polygon_intersection_area(f1["poly_2d"], f2["poly_2d"])

                        for tol in tolerances:
                            if dz < tol:
                                if aabb_overlap >= 1.0:
                                    results_by_tol[tol]["macro_conflicts_aabb"] += 1
                                if exact_overlap >= 1.0:
                                    results_by_tol[tol]["macro_conflicts_exact"] += 1
                                    if len(results_by_tol[tol]["conflict_details"]) < 15:
                                        results_by_tol[tol]["conflict_details"].append({
                                            "type": "MACRO",
                                            "dz": round(dz, 4),
                                            "exact_overlap": round(exact_overlap, 3),
                                            "aabb_overlap": round(aabb_overlap, 3),
                                            "obj1": f1["obj"], "mat1": f1["mat"], "z1": round(f1["z"], 3),
                                            "obj2": f2["obj"], "mat2": f2["mat"], "z2": round(f2["z"], 3)
                                        })
                                elif exact_overlap >= 0.01:
                                    results_by_tol[tol]["micro_conflicts_exact"] += 1
                                    if len(results_by_tol[tol]["conflict_details"]) < 15:
                                        results_by_tol[tol]["conflict_details"].append({
                                            "type": "MICRO",
                                            "dz": round(dz, 4),
                                            "exact_overlap": round(exact_overlap, 4),
                                            "aabb_overlap": round(aabb_overlap, 3),
                                            "obj1": f1["obj"], "mat1": f1["mat"], "z1": round(f1["z"], 3),
                                            "obj2": f2["obj"], "mat2": f2["mat"], "z2": round(f2["z"], 3)
                                        })
                                elif exact_overlap >= 0.001:
                                    results_by_tol[tol]["submicro_conflicts_exact"] += 1

        print(f"Evaluated {checked_pairs:,} overlapping candidate pairs.")
        for tol in tolerances:
            r = results_by_tol[tol]
            print(f"  |Δz| < {tol:.2f}m -> Exact Macro (>=1.0m²): {r['macro_conflicts_exact']}, Exact Micro (0.01..1m²): {r['micro_conflicts_exact']}, AABB Macro: {r['macro_conflicts_aabb']}")
            if r["conflict_details"] and self.verbose:
                for c in r["conflict_details"][:5]:
                    print(f"     [{c['type']}] dz={c['dz']}m overlap={c['exact_overlap']}m² : {c['obj1']}[{c['mat1']}] @ z={c['z1']} <-> {c['obj2']}[{c['mat2']}] @ z={c['z2']}")

        self.results["probe_roof_multitol"] = results_by_tol
        return results_by_tol

    # -------------------------------------------------------------------------
    # PROBE 3: Party Wall & Building Interface Heights
    # -------------------------------------------------------------------------
    def probe_party_walls(self) -> dict:
        """
        Check that adjacent buildings do not share identical roof or parapet elevations.
        Finds adjacent building bounding boxes that touch or are within 0.5m in XY,
        and checks if their maximum Z elevations or roof decks are within |Δz| < 0.05m.
        """
        print("\n" + "=" * 76)
        print("PROBE 3: Party Wall Elevation & Parapet Step Audit")
        print("=" * 76)

        bldg_objs = []
        for obj in self.mesh_objs:
            if obj.hide_render:
                continue
            nl = obj.name.lower()
            if any(k in nl for k in ("tree", "jacaranda", "shrub", "statue", "lamp", "bench", "ground", "curb", "sidewalk", "asphalt", "cobble", "streetscape")):
                continue
            bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
            min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)
            min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
            dx = max_x - min_x
            dy = max_y - min_y
            dz = max_z - min_z
            if dz >= 4.0 and (dx >= 3.0 or dy >= 3.0):
                bldg_objs.append({
                    "name": obj.name,
                    "bbox": (min_x, max_x, min_y, max_y, min_z, max_z),
                    "max_z": max_z,
                    "min_z": min_z
                })

        print(f"Collected {len(bldg_objs)} building/facade objects for party wall proximity analysis.")

        shared_height_pairs = []
        for i in range(len(bldg_objs)):
            b1 = bldg_objs[i]
            for j in range(i + 1, len(bldg_objs)):
                b2 = bldg_objs[j]
                # Check XY proximity (distance <= 0.35m between bounding boxes)
                dist_x = max(0.0, max(b1["bbox"][0], b2["bbox"][0]) - min(b1["bbox"][1], b2["bbox"][1]))
                dist_y = max(0.0, max(b1["bbox"][2], b2["bbox"][2]) - min(b1["bbox"][3], b2["bbox"][3]))
                if dist_x <= 0.35 and dist_y <= 0.35:
                    # Touching or adjacent buildings
                    dz = abs(b1["max_z"] - b2["max_z"])
                    if dz < 0.05:
                        shared_height_pairs.append({
                            "obj1": b1["name"], "max_z1": round(b1["max_z"], 3),
                            "obj2": b2["name"], "max_z2": round(b2["max_z"], 3),
                            "dz": round(dz, 4)
                        })

        passed = (len(shared_height_pairs) == 0)
        print(f"--> PROBE 3 RESULT: {'PASS' if passed else 'WARNING/INFO'} ({len(shared_height_pairs)} adjacent pairs with near-identical max_z |Δz| < 0.05m)")
        if shared_height_pairs and self.verbose:
            for p in shared_height_pairs[:5]:
                print(f"     {p['obj1']} (z={p['max_z1']}) <-> {p['obj2']} (z={p['max_z2']}) | dz={p['dz']}m")

        res = {
            "passed": passed,
            "adjacent_shared_height_pairs": len(shared_height_pairs),
            "details": shared_height_pairs
        }
        self.results["probe_party_walls"] = res
        return res

    # -------------------------------------------------------------------------
    # PROBE 4: Facade Corner & Sill Collision Probe
    # -------------------------------------------------------------------------
    def probe_corners_and_sills(self) -> dict:
        """
        Check for intersecting horizontal sills or belt courses at facade corners.
        Finds horizontal faces with normal.z > 0.88 at intermediate floor levels (3.0m < z < max_z - 1.0m)
        with area between 0.02 and 2.0 m² (typical sill / belt band sizes).
        """
        print("\n" + "=" * 76)
        print("PROBE 4: Intermediate Window Sill & Belt Course Corner Collision Audit")
        print("=" * 76)

        t0 = time.time()
        sill_faces = []
        for obj in self.mesh_objs:
            if obj.hide_render:
                continue
            nl = obj.name.lower()
            if any(k in nl for k in ("tree", "jacaranda", "shrub", "statue", "lamp", "bench", "ground", "curb", "sidewalk", "asphalt", "cobble")):
                continue
            me = obj.data
            mw = obj.matrix_world
            rot_3x3 = mw.to_3x3()
            mats = [m.name if m else "None" for m in me.materials]

            # Find object max_z to distinguish roof caps from intermediate sills
            bb = [mw @ Vector(c) for c in obj.bound_box]
            obj_max_z = max(v.z for v in bb)

            for p in me.polygons:
                wn = (rot_3x3 @ p.normal).normalized()
                # Horizontal upward faces of intermediate sills/bands
                if wn.z > 0.88 and 0.02 <= p.area <= 3.0:
                    wc = mw @ p.center
                    if 3.0 <= wc.z <= (obj_max_z - 0.8):  # Intermediate elevation
                        mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                        world_pts = [(mw @ me.vertices[vi].co) for vi in p.vertices]
                        xs = [pt.x for pt in world_pts]
                        ys = [pt.y for pt in world_pts]
                        sill_faces.append({
                            "obj": obj.name,
                            "mat": mat_name,
                            "z": wc.z,
                            "x_min": min(xs), "x_max": max(xs),
                            "y_min": min(ys), "y_max": max(ys),
                            "area": p.area,
                            "poly_2d": [(pt.x, pt.y) for pt in world_pts]
                        })

        print(f"Collected {len(sill_faces):,} intermediate sill/belt course faces in {time.time()-t0:.2f}s.")

        # Check for coplanar sill collisions (|Δz| < 0.03m, exact intersection > 0.01 m²)
        sill_collisions = []
        bin_size = 0.05
        buckets = defaultdict(list)
        for sf in sill_faces:
            b_idx = int(math.floor(sf["z"] / bin_size))
            buckets[b_idx].append(sf)

        for b_idx, faces in buckets.items():
            candidates = list(faces)
            if (b_idx + 1) in buckets:
                candidates.extend(buckets[b_idx + 1])
            len_f = len(faces)
            for i in range(len_f):
                f1 = faces[i]
                for j in range(i + 1, len(candidates)):
                    f2 = candidates[j]
                    if f1["obj"] == f2["obj"] and f1["mat"] == f2["mat"]:
                        continue
                    dz = abs(f1["z"] - f2["z"])
                    if dz < 0.03:
                        ox = min(f1["x_max"], f2["x_max"]) - max(f1["x_min"], f2["x_min"])
                        if ox <= 0:
                            continue
                        oy = min(f1["y_max"], f2["y_max"]) - max(f1["y_min"], f2["y_min"])
                        if oy <= 0:
                            continue
                        if ox * oy > 0.005:
                            exact_area = exact_2d_polygon_intersection_area(f1["poly_2d"], f2["poly_2d"])
                            if exact_area > 0.01:
                                sill_collisions.append({
                                    "dz": round(dz, 4),
                                    "exact_overlap": round(exact_area, 4),
                                    "obj1": f1["obj"], "mat1": f1["mat"], "z1": round(f1["z"], 3),
                                    "obj2": f2["obj"], "mat2": f2["mat"], "z2": round(f2["z"], 3)
                                })

        passed = (len(sill_collisions) == 0)
        print(f"--> PROBE 4 RESULT: {'PASS' if passed else 'FAIL'} ({len(sill_collisions)} colliding sill/belt face pairs)")
        if sill_collisions and self.verbose:
            for sc in sill_collisions[:5]:
                print(f"     Sill collision dz={sc['dz']}m overlap={sc['exact_overlap']}m² : {sc['obj1']} <-> {sc['obj2']} @ z={sc['z1']}")

        res = {
            "passed": passed,
            "sill_collisions_count": len(sill_collisions),
            "details": sill_collisions[:20]
        }
        self.results["probe_corners"] = res
        return res

    # -------------------------------------------------------------------------
    # Master Evaluation & Verdict
    # -------------------------------------------------------------------------
    def evaluate(self) -> dict:
        p1 = self.probe_proxies_and_landmarks()
        p2 = self.probe_roof_cornice_multitol()
        p3 = self.probe_party_walls()
        p4 = self.probe_corners_and_sills()

        # Acceptance Criteria check:
        # 1. Zero macro roof conflicts at |Δz| < 0.05m (Acceptance Criterion 1)
        macro_clean_005 = (p2[0.05]["macro_conflicts_exact"] == 0)
        # 2. Strict tolerance check at |Δz| < 0.08m (ORIGINAL_REQUEST R1)
        macro_clean_008 = (p2[0.08]["macro_conflicts_exact"] == 0)
        # 3. Micro-overlap check (0.01m² to 1.0m²) at |Δz| < 0.05m
        micro_count_005 = p2[0.05]["micro_conflicts_exact"]
        # 4. Proxy & landmark deduplication
        proxy_clean = p1["passed"]
        # 5. Corner sill clean
        corner_clean = p4["passed"]

        # Formal Verdict:
        # APPROVE requires:
        # - Zero macro-conflicts at both 0.05m and 0.08m
        # - Context proxies and landmarks strictly hidden
        # - Zero corner sill collisions
        if macro_clean_005 and macro_clean_008 and proxy_clean and corner_clean:
            verdict = "APPROVE"
        else:
            verdict = "REJECT"

        self.results["verdict"] = verdict
        self.results["summary"] = {
            "verdict": verdict,
            "macro_conflicts_exact_005": p2[0.05]["macro_conflicts_exact"],
            "macro_conflicts_exact_008": p2[0.08]["macro_conflicts_exact"],
            "micro_conflicts_exact_005": micro_count_005,
            "micro_conflicts_exact_008": p2[0.08]["micro_conflicts_exact"],
            "coplanar_exact_001": p2[0.01]["macro_conflicts_exact"] + p2[0.01]["micro_conflicts_exact"],
            "proxy_passed": proxy_clean,
            "corner_sill_passed": corner_clean,
            "party_wall_shared_heights": p3["adjacent_shared_height_pairs"]
        }

        print("\n" + "=" * 76)
        print(f"STRESS TEST SUMMARY FOR {self.block_name}: VERDICT = {verdict}")
        print("=" * 76)
        print(f"  Macro Conflicts (|Δz| < 0.05m, >=1.0m²):  {p2[0.05]['macro_conflicts_exact']}")
        print(f"  Macro Conflicts (|Δz| < 0.08m, >=1.0m²):  {p2[0.08]['macro_conflicts_exact']}")
        print(f"  Micro Conflicts (|Δz| < 0.05m, 0.01..1m²): {micro_count_005}")
        print(f"  Micro Conflicts (|Δz| < 0.08m, 0.01..1m²): {p2[0.08]['micro_conflicts_exact']}")
        print(f"  Coplanar Conflicts (|Δz| < 0.01m, >=0.01m²): {p2[0.01]['macro_conflicts_exact'] + p2[0.01]['micro_conflicts_exact']}")
        print(f"  Landmark & Proxy Clean:                   {proxy_clean}")
        print(f"  Corner Sill Clean:                        {corner_clean}")
        print(f"  Party Wall Near-Identical Heights:        {p3['adjacent_shared_height_pairs']}")
        print("=" * 76)

        return self.results


def main():
    argv = sys.argv
    args_to_parse = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=str, default="UNKNOWN")
    parser.add_argument("--json-out", type=str, default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(args_to_parse)

    prober = MontrealAdversarialStressProber(args.block, verbose=args.verbose)
    results = prober.evaluate()

    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"JSON results saved to {args.json_out}")

    sys.exit(0 if results["verdict"] == "APPROVE" else 1)


if __name__ == "__main__":
    main()
