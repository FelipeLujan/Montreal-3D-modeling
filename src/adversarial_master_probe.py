#!/usr/bin/env python3
r"""
src/adversarial_master_probe.py
===============================
Adversarial Geometric Stress-Test & Vulnerability Mining Suite
for Old Montreal Master Scene (output/montreal_master.blend).

Challenger Mission:
1. Multi-tolerance sweep: |Δz| < 0.08m, |Δz| < 0.05m, |Δz| < 0.01m
2. Micro-overlap sweep: overlap < 1.0 m² (down to 0.05 m² and 0.01 m²)
3. Ground, street, and sidewalk seam & vertical hierarchy checks
4. Targeted deep-dive into 5 complex collision sites:
   - Site 1: Palais de Justice & Cormier annex stepped roofs (Block 13)
   - Site 2: InterContinental & Royal Bank atrium edges (Block 11)
   - Site 3: Saint-Paul / Saint-Sulpice perimeter buildings (Block 7)
   - Site 4: Place d'Armes apron & Bank of Montreal Pantheon / Annex (Block 1 & 3)
   - Site 5: Place Jacques-Cartier promenade & carriage corridor
5. Targeted close-up verification renders of the 5 sites

Execution:
  & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b output/montreal_master.blend --python src/adversarial_master_probe.py -- --verbose
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
    print("ERROR: Must run inside Blender 5.2 (blender -b <file.blend> --python src/adversarial_master_probe.py)", file=sys.stderr)
    sys.exit(2)

EXCLUDED_KEYWORDS = (
    "tree", "jacaranda", "shrub", "statue", "lamp", "bench",
    "clock_bezel", "grate", "signage", "furniture", "bollard",
    "car", "suv", "van", "sedan", "pedestrian"
)


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
    n2 = len(poly2)
    if n2 < 3 or len(poly1) < 3:
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


class MontrealAdversarialChallenger:
    def __init__(self, verbose=False, output_json="output/adversarial_probe_report.json"):
        self.verbose = verbose
        self.output_json = output_json
        self.mesh_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]
        self.results = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "blend_file": bpy.data.filepath,
            "total_visible_mesh_objs": len(self.mesh_objs),
            "probes": {},
            "landmark_sites": {},
            "verdict": "PENDING"
        }

    # =========================================================================
    # PROBE 1: Multi-Tolerance Roof & Cornice Sweep
    # =========================================================================
    def probe_roof_multitol(self):
        print("\n" + "=" * 78)
        print("ADVERSARIAL PROBE 1: Multi-Tolerance Roof & Cornice Z-Fighting Sweep")
        print("Tolerances tested: |Δz| < 0.08m, |Δz| < 0.05m, |Δz| < 0.01m")
        print("Overlap categories: Macro (>= 1.0 m²), Micro (0.05 to 1.0 m²), Sub-micro (0.01 to 0.05 m²)")
        print("=" * 78)

        t0 = time.time()
        roof_faces = []

        for obj in self.mesh_objs:
            nl = obj.name.lower()
            if any(k in nl for k in EXCLUDED_KEYWORDS):
                continue
            me = obj.data
            mw = obj.matrix_world
            rot_3x3 = mw.to_3x3()
            mats = [m.name if m else "None" for m in me.materials]

            for p in me.polygons:
                wn = (rot_3x3 @ p.normal).normalized()
                # Accept normal.z > 0.85 and area >= 0.05 m² (catches small skylights, caps, and parapet trims)
                if wn.z > 0.85 and p.area >= 0.05:
                    wc = mw @ p.center
                    if wc.z > 3.0:
                        mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                        world_pts = [(mw @ me.vertices[vi].co) for vi in p.vertices]
                        xs = [pt.x for pt in world_pts]
                        ys = [pt.y for pt in world_pts]
                        poly_2d = [(pt.x, pt.y) for pt in world_pts]
                        roof_faces.append({
                            "obj": obj.name, "mat": mat_name, "z": wc.z, "area": p.area,
                            "xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys),
                            "poly_2d": poly_2d
                        })

        t_collect = time.time() - t0
        print(f"Collected {len(roof_faces):,} candidate upward roof faces in {t_collect:.2f}s.")

        # Bucketing by Z (bin size = 0.08m)
        bin_size = 0.08
        buckets = defaultdict(list)
        for f in roof_faces:
            b_idx = int(math.floor(f["z"] / bin_size))
            buckets[b_idx].append(f)

        for b_idx in buckets:
            buckets[b_idx].sort(key=lambda item: item["xmin"])

        tolerances = [0.08, 0.05, 0.01]
        probe_data = {
            tol: {
                "macro_exact": 0,       # exact overlap >= 1.0 m²
                "macro_aabb": 0,        # AABB overlap >= 1.0 m²
                "micro_exact": 0,       # 0.05 <= exact overlap < 1.0 m²
                "submicro_exact": 0,    # 0.01 <= exact overlap < 0.05 m²
                "sample_conflicts": []
            } for tol in tolerances
        }

        checked_pairs = 0
        sorted_keys = sorted(buckets.keys())

        for b_idx in sorted_keys:
            faces_a = buckets[b_idx]
            len_a = len(faces_a)

            # Compare within bucket
            for i in range(len_a):
                f1 = faces_a[i]
                for j in range(i + 1, len_a):
                    f2 = faces_a[j]
                    if f2["xmin"] > f1["xmax"]:
                        break
                    if f1["obj"] == f2["obj"] and f1["mat"] == f2["mat"]:
                        continue

                    dz = abs(f1["z"] - f2["z"])
                    if dz >= 0.08:
                        continue

                    oy = min(f1["ymax"], f2["ymax"]) - max(f1["ymin"], f2["ymin"])
                    if oy <= 0.0:
                        continue
                    ox = min(f1["xmax"], f2["xmax"]) - f2["xmin"]
                    if ox <= 0.0:
                        continue

                    aabb_area = ox * oy
                    if aabb_area < 0.01:
                        continue

                    checked_pairs += 1
                    exact_area = exact_2d_polygon_intersection_area(f1["poly_2d"], f2["poly_2d"])
                    if exact_area < 0.01:
                        continue

                    for tol in tolerances:
                        if dz < tol:
                            if aabb_area >= 1.0:
                                probe_data[tol]["macro_aabb"] += 1
                            if exact_area >= 1.0:
                                probe_data[tol]["macro_exact"] += 1
                                if len(probe_data[tol]["sample_conflicts"]) < 10:
                                    probe_data[tol]["sample_conflicts"].append({
                                        "category": "MACRO", "dz": round(dz, 4), "exact_overlap": round(exact_area, 3),
                                        "obj1": f1["obj"], "mat1": f1["mat"], "z1": round(f1["z"], 3),
                                        "obj2": f2["obj"], "mat2": f2["mat"], "z2": round(f2["z"], 3)
                                    })
                            elif exact_area >= 0.05:
                                probe_data[tol]["micro_exact"] += 1
                                if len(probe_data[tol]["sample_conflicts"]) < 10:
                                    probe_data[tol]["sample_conflicts"].append({
                                        "category": "MICRO", "dz": round(dz, 4), "exact_overlap": round(exact_area, 4),
                                        "obj1": f1["obj"], "mat1": f1["mat"], "z1": round(f1["z"], 3),
                                        "obj2": f2["obj"], "mat2": f2["mat"], "z2": round(f2["z"], 3)
                                    })
                            else:
                                probe_data[tol]["submicro_exact"] += 1

            # Compare with next bucket (b_idx + 1)
            if (b_idx + 1) in buckets:
                faces_b = buckets[b_idx + 1]
                for f1 in faces_a:
                    for f2 in faces_b:
                        if f2["xmin"] > f1["xmax"]:
                            break
                        if f2["xmax"] < f1["xmin"]:
                            continue
                        if f1["obj"] == f2["obj"] and f1["mat"] == f2["mat"]:
                            continue

                        dz = abs(f1["z"] - f2["z"])
                        if dz >= 0.08:
                            continue

                        oy = min(f1["ymax"], f2["ymax"]) - max(f1["ymin"], f2["ymin"])
                        if oy <= 0.0:
                            continue
                        ox = min(f1["xmax"], f2["xmax"]) - max(f1["xmin"], f2["xmin"])
                        if ox <= 0.0:
                            continue

                        aabb_area = ox * oy
                        if aabb_area < 0.01:
                            continue

                        checked_pairs += 1
                        exact_area = exact_2d_polygon_intersection_area(f1["poly_2d"], f2["poly_2d"])
                        if exact_area < 0.01:
                            continue

                        for tol in tolerances:
                            if dz < tol:
                                if aabb_area >= 1.0:
                                    probe_data[tol]["macro_aabb"] += 1
                                if exact_area >= 1.0:
                                    probe_data[tol]["macro_exact"] += 1
                                    if len(probe_data[tol]["sample_conflicts"]) < 10:
                                        probe_data[tol]["sample_conflicts"].append({
                                            "category": "MACRO", "dz": round(dz, 4), "exact_overlap": round(exact_area, 3),
                                            "obj1": f1["obj"], "mat1": f1["mat"], "z1": round(f1["z"], 3),
                                            "obj2": f2["obj"], "mat2": f2["mat"], "z2": round(f2["z"], 3)
                                        })
                                elif exact_area >= 0.05:
                                    probe_data[tol]["micro_exact"] += 1
                                    if len(probe_data[tol]["sample_conflicts"]) < 10:
                                        probe_data[tol]["sample_conflicts"].append({
                                            "category": "MICRO", "dz": round(dz, 4), "exact_overlap": round(exact_area, 4),
                                            "obj1": f1["obj"], "mat1": f1["mat"], "z1": round(f1["z"], 3),
                                            "obj2": f2["obj"], "mat2": f2["mat"], "z2": round(f2["z"], 3)
                                        })
                                else:
                                    probe_data[tol]["submicro_exact"] += 1

        print(f"Evaluated {checked_pairs:,} overlapping candidate face pairs.")
        for tol in tolerances:
            d = probe_data[tol]
            print(f"  |Δz| < {tol:.2f}m : Exact Macro (>=1.0m²) = {d['macro_exact']}, Exact Micro (0.05..1.0m²) = {d['micro_exact']}, Sub-micro (0.01..0.05m²) = {d['submicro_exact']}, AABB Macro = {d['macro_aabb']}")
            if d["sample_conflicts"] and self.verbose:
                for sc in d["sample_conflicts"][:3]:
                    print(f"     [{sc['category']}] dz={sc['dz']}m ov={sc['exact_overlap']}m² : {sc['obj1']}[{sc['mat1']}] @ z={sc['z1']} <-> {sc['obj2']}[{sc['mat2']}] @ z={sc['z2']}")

        res = {
            "candidate_faces": len(roof_faces),
            "checked_pairs": checked_pairs,
            "tolerances": {str(tol): probe_data[tol] for tol in tolerances}
        }
        self.results["probes"]["roof_multitol"] = res
        return res

    # =========================================================================
    # PROBE 2: Ground, Street, Sidewalk & Curb Seam Sweep
    # =========================================================================
    def probe_ground_street_sidewalk_seams(self):
        print("\n" + "=" * 78)
        print("ADVERSARIAL PROBE 2: Ground, Street, Sidewalk & Curb Seam Audit")
        print("Checking vertical hierarchy: Roadbeds (0.0m), Markings (+0.002m), Sidewalks (+0.15m), Curbs (+0.18m)")
        print("Testing for micro-overlaps and elevation inversions")
        print("=" * 78)

        t0 = time.time()
        ground_faces = []
        for obj in self.mesh_objs:
            nl = obj.name.lower()
            if any(k in nl for k in EXCLUDED_KEYWORDS):
                continue
            me = obj.data
            mw = obj.matrix_world
            rot_3x3 = mw.to_3x3()
            mats = [m.name if m else "None" for m in me.materials]

            # Distinguish layer type by object/material name
            layer_type = "other"
            if any(k in nl for k in ("asphalt", "cobble", "road", "street")):
                layer_type = "roadbed"
            elif any(k in nl for k in ("sidewalk", "trottoir", "footway")):
                layer_type = "sidewalk"
            elif any(k in nl for k in ("curb", "bordure")):
                layer_type = "curb"
            elif any(k in nl for k in ("mark", "crosswalk", "zebra", "stripe", "paint")):
                layer_type = "marking"
            elif any(k in nl for k in ("plinth", "socle", "foundation", "bldg", "block")):
                layer_type = "building_base"

            for p in me.polygons:
                wn = (rot_3x3 @ p.normal).normalized()
                if wn.z > 0.88 and p.area >= 0.10:
                    wc = mw @ p.center
                    if -0.30 <= wc.z <= 0.60:
                        mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                        world_pts = [(mw @ me.vertices[vi].co) for vi in p.vertices]
                        xs = [pt.x for pt in world_pts]
                        ys = [pt.y for pt in world_pts]
                        ground_faces.append({
                            "obj": obj.name, "mat": mat_name, "layer": layer_type, "z": wc.z, "area": p.area,
                            "xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys),
                            "poly_2d": [(pt.x, pt.y) for pt in world_pts]
                        })

        print(f"Collected {len(ground_faces):,} upward ground/street/sidewalk faces in {time.time()-t0:.2f}s.")

        # Check layer elevation distributions
        elevations_by_layer = defaultdict(list)
        for gf in ground_faces:
            elevations_by_layer[gf["layer"]].append(gf["z"])

        print("\nGround Hierarchy Elevation Summary:")
        for layer, zs in sorted(elevations_by_layer.items()):
            min_z, max_z, avg_z = min(zs), max(zs), sum(zs)/len(zs)
            print(f"  {layer:15s}: count={len(zs):5d} | z in [{min_z:+.3f}m, {max_z:+.3f}m] | avg={avg_z:+.3f}m")

        # Check for coplanar ground collisions (|Δz| < 0.02m) at different overlap thresholds:
        # Macro (>= 2.0 m²), Medium (0.5 to 2.0 m²), Micro (0.05 to 0.5 m²)
        bin_size = 0.02
        buckets = defaultdict(list)
        for f in ground_faces:
            b_idx = int(math.floor(f["z"] / bin_size))
            buckets[b_idx].append(f)

        for b_idx in buckets:
            buckets[b_idx].sort(key=lambda item: item["xmin"])

        collisions = {
            "macro_2m": 0,
            "med_05m": 0,
            "micro_005m": 0,
            "details": []
        }

        for b_idx, faces_a in buckets.items():
            candidate_lists = [faces_a]
            if (b_idx + 1) in buckets:
                candidate_lists.append(buckets[b_idx + 1])

            len_a = len(faces_a)
            for i in range(len_a):
                f1 = faces_a[i]
                for c_list in candidate_lists:
                    start_j = (i + 1) if c_list is faces_a else 0
                    for j in range(start_j, len(c_list)):
                        f2 = c_list[j]
                        if f2["xmin"] > f1["xmax"]:
                            break
                        if f2["xmax"] < f1["xmin"]:
                            continue
                        if f1["obj"] == f2["obj"] and f1["mat"] == f2["mat"]:
                            continue

                        dz = abs(f1["z"] - f2["z"])
                        if dz >= 0.02:
                            continue

                        oy = min(f1["ymax"], f2["ymax"]) - max(f1["ymin"], f2["ymin"])
                        if oy <= 0.0:
                            continue
                        ox = min(f1["xmax"], f2["xmax"]) - max(f1["xmin"], f2["xmin"])
                        if ox <= 0.0:
                            continue

                        if ox * oy < 0.05:
                            continue

                        exact_area = exact_2d_polygon_intersection_area(f1["poly_2d"], f2["poly_2d"])
                        if exact_area >= 2.0:
                            collisions["macro_2m"] += 1
                            if len(collisions["details"]) < 10:
                                collisions["details"].append({
                                    "cat": "MACRO >=2m²", "dz": round(dz, 4), "ov": round(exact_area, 3),
                                    "f1": f"{f1['obj']}[{f1['mat']}]({f1['layer']}) @ z={f1['z']:.3f}",
                                    "f2": f"{f2['obj']}[{f2['mat']}]({f2['layer']}) @ z={f2['z']:.3f}"
                                })
                        elif exact_area >= 0.5:
                            collisions["med_05m"] += 1
                            if len(collisions["details"]) < 10:
                                collisions["details"].append({
                                    "cat": "MED 0.5-2m²", "dz": round(dz, 4), "ov": round(exact_area, 3),
                                    "f1": f"{f1['obj']}[{f1['mat']}]({f1['layer']}) @ z={f1['z']:.3f}",
                                    "f2": f"{f2['obj']}[{f2['mat']}]({f2['layer']}) @ z={f2['z']:.3f}"
                                })
                        elif exact_area >= 0.05:
                            collisions["micro_005m"] += 1

        print(f"\nGround Conflict Results (|Δz| < 0.02m):")
        print(f"  Macro conflicts (overlap >= 2.0 m²): {collisions['macro_2m']}")
        print(f"  Medium conflicts (0.5 <= ov < 2.0 m²): {collisions['med_05m']}")
        print(f"  Micro conflicts (0.05 <= ov < 0.5 m²): {collisions['micro_005m']}")
        if collisions["details"]:
            for d in collisions["details"]:
                print(f"     [{d['cat']}] dz={d['dz']}m ov={d['ov']}m² : {d['f1']} <-> {d['f2']}")

        res = {
            "ground_faces_count": len(ground_faces),
            "elevations": {k: {"count": len(v), "min": round(min(v), 3), "max": round(max(v), 3), "avg": round(sum(v)/len(v), 3)} for k, v in elevations_by_layer.items()},
            "collisions": collisions
        }
        self.results["probes"]["ground_seams"] = res
        return res

    # =========================================================================
    # PROBE 3: Targeted Deep-Dive into 5 Complex Collision Sites
    # =========================================================================
    def probe_landmark_sites(self):
        print("\n" + "=" * 78)
        print("ADVERSARIAL PROBE 3: Deep-Dive into 5 Complex Collision Sites")
        print("=" * 78)

        sites = {
            "Site_1_Palais_de_Justice_Block13": {
                "desc": "Palais de Justice & Cormier annex stepped roofs (Block 13)",
                "bbox": {"xmin": -50.0, "xmax": 260.0, "ymin": 200.0, "ymax": 500.0},
                "col_keywords": ["0013", "palais", "cormier", "justice", "court"]
            },
            "Site_2_InterContinental_WTC_Block11": {
                "desc": "InterContinental & Royal Bank atrium edges (Block 11)",
                "bbox": {"xmin": -360.0, "xmax": -80.0, "ymin": 150.0, "ymax": 420.0},
                "col_keywords": ["0011", "wtc", "intercontinental", "royal_bank", "atrium"]
            },
            "Site_3_SaintPaul_SaintSulpice_Block7": {
                "desc": "Saint-Paul / Saint-Sulpice perimeter buildings (Block 7)",
                "bbox": {"xmin": 40.0, "xmax": 260.0, "ymin": -260.0, "ymax": 20.0},
                "col_keywords": ["0007", "saint_paul", "saint_sulpice", "cours_le_royer"]
            },
            "Site_4_Place_dArmes_BMO_Block1_3": {
                "desc": "Place d'Armes apron & Bank of Montreal Pantheon / Annex (Block 1 & 3)",
                "bbox": {"xmin": -160.0, "xmax": 120.0, "ymin": -60.0, "ymax": 210.0},
                "col_keywords": ["0001", "0003", "bmo", "pantheon", "place_darmes", "beauxarts", "aldred", "ny_life"]
            },
            "Site_5_Place_JacquesCartier": {
                "desc": "Place Jacques-Cartier promenade and carriage corridor",
                "bbox": {"xmin": 280.0, "xmax": 520.0, "ymin": -120.0, "ymax": 220.0},
                "col_keywords": ["jacques", "cartier", "promenade", "ramezay", "vauquelin", "0002", "0005"]
            }
        }

        for site_key, site_info in sites.items():
            print(f"\n--- {site_key}: {site_info['desc']} ---")
            bb = site_info["bbox"]

            # Filter objects by spatial bounding box overlap and/or collection keywords
            site_objs = []
            for obj in self.mesh_objs:
                nl = obj.name.lower()
                if any(k in nl for k in EXCLUDED_KEYWORDS):
                    continue
                obb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
                oxmin, oxmax = min(v.x for v in obb), max(v.x for v in obb)
                oymin, oymax = min(v.y for v in obb), max(v.y for v in obb)

                # Check if object intersects site bounding box
                if (oxmin <= bb["xmax"] and oxmax >= bb["xmin"] and oymin <= bb["ymax"] and oymax >= bb["ymin"]):
                    site_objs.append(obj)
                elif any(k in nl for k in site_info["col_keywords"]):
                    site_objs.append(obj)

            # Deduplicate objects
            site_objs = list(set(site_objs))
            print(f"  Found {len(site_objs)} active mesh objects in site bounding box/keywords.")

            # Audit site roofs
            site_roof_faces = []
            site_ground_faces = []
            for obj in site_objs:
                me = obj.data
                mw = obj.matrix_world
                rot_3x3 = mw.to_3x3()
                mats = [m.name if m else "None" for m in me.materials]
                for p in me.polygons:
                    wn = (rot_3x3 @ p.normal).normalized()
                    if wn.z > 0.85:
                        wc = mw @ p.center
                        mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                        world_pts = [(mw @ me.vertices[vi].co) for vi in p.vertices]
                        xs = [pt.x for pt in world_pts]
                        ys = [pt.y for pt in world_pts]
                        f_dict = {
                            "obj": obj.name, "mat": mat_name, "z": wc.z, "area": p.area,
                            "xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys),
                            "poly_2d": [(pt.x, pt.y) for pt in world_pts]
                        }
                        if wc.z > 3.0 and p.area >= 0.05:
                            site_roof_faces.append(f_dict)
                        elif -0.30 <= wc.z <= 0.60 and p.area >= 0.05:
                            site_ground_faces.append(f_dict)

            print(f"  Candidate Faces: {len(site_roof_faces)} roof faces (Z>3m) | {len(site_ground_faces)} ground faces (-0.3..0.6m)")

            # Check roof conflicts in site (|Δz| < 0.08m, exact overlap >= 0.1 m²)
            site_roof_conflicts = []
            for i in range(len(site_roof_faces)):
                f1 = site_roof_faces[i]
                for j in range(i + 1, len(site_roof_faces)):
                    f2 = site_roof_faces[j]
                    if f1["obj"] == f2["obj"] and f1["mat"] == f2["mat"]:
                        continue
                    dz = abs(f1["z"] - f2["z"])
                    if dz < 0.08:
                        if max(f1["xmin"], f2["xmin"]) <= min(f1["xmax"], f2["xmax"]) and max(f1["ymin"], f2["ymin"]) <= min(f1["ymax"], f2["ymax"]):
                            exact_area = exact_2d_polygon_intersection_area(f1["poly_2d"], f2["poly_2d"])
                            if exact_area >= 0.1:
                                site_roof_conflicts.append({
                                    "dz": round(dz, 4), "exact_overlap": round(exact_area, 3),
                                    "obj1": f1["obj"], "mat1": f1["mat"], "z1": round(f1["z"], 3),
                                    "obj2": f2["obj"], "mat2": f2["mat"], "z2": round(f2["z"], 3)
                                })

            # Check ground conflicts in site (|Δz| < 0.02m, exact overlap >= 0.1 m²)
            site_ground_conflicts = []
            for i in range(len(site_ground_faces)):
                f1 = site_ground_faces[i]
                for j in range(i + 1, len(site_ground_faces)):
                    f2 = site_ground_faces[j]
                    if f1["obj"] == f2["obj"] and f1["mat"] == f2["mat"]:
                        continue
                    dz = abs(f1["z"] - f2["z"])
                    if dz < 0.02:
                        if max(f1["xmin"], f2["xmin"]) <= min(f1["xmax"], f2["xmax"]) and max(f1["ymin"], f2["ymin"]) <= min(f1["ymax"], f2["ymax"]):
                            exact_area = exact_2d_polygon_intersection_area(f1["poly_2d"], f2["poly_2d"])
                            if exact_area >= 0.1:
                                site_ground_conflicts.append({
                                    "dz": round(dz, 4), "exact_overlap": round(exact_area, 3),
                                    "obj1": f1["obj"], "mat1": f1["mat"], "z1": round(f1["z"], 3),
                                    "obj2": f2["obj"], "mat2": f2["mat"], "z2": round(f2["z"], 3)
                                })

            status = "PASS" if (len(site_roof_conflicts) == 0 and len(site_ground_conflicts) == 0) else "FAIL"
            print(f"  Result: {status} (Roof conflicts: {len(site_roof_conflicts)}, Ground conflicts: {len(site_ground_conflicts)})")
            if site_roof_conflicts:
                for c in site_roof_conflicts[:3]:
                    print(f"     [ROOF] dz={c['dz']}m ov={c['exact_overlap']}m² : {c['obj1']}[{c['mat1']}] <-> {c['obj2']}[{c['mat2']}]")
            if site_ground_conflicts:
                for c in site_ground_conflicts[:3]:
                    print(f"     [GROUND] dz={c['dz']}m ov={c['exact_overlap']}m² : {c['obj1']}[{c['mat1']}] <-> {c['obj2']}[{c['mat2']}]")

            self.results["landmark_sites"][site_key] = {
                "desc": site_info["desc"],
                "status": status,
                "objects_count": len(site_objs),
                "roof_conflicts": site_roof_conflicts,
                "ground_conflicts": site_ground_conflicts
            }

        return self.results["landmark_sites"]

    # =========================================================================
    # PROBE 4: Targeted Camera Setup & Rendering
    # =========================================================================
    def render_targeted_snapshots(self):
        print("\n" + "=" * 78)
        print("ADVERSARIAL PROBE 4: Rendering Targeted Close-up Snapshots")
        print("=" * 78)

        render_dir = os.path.join("output", "renders", "adversarial_checks")
        os.makedirs(render_dir, exist_ok=True)

        camera_targets = [
            {
                "name": "Site1_PalaisJustice_SteppedRoof",
                "pos": Vector((110.0, 310.0, 95.0)),
                "look_at": Vector((105.0, 350.0, 40.0)),
                "lens": 50
            },
            {
                "name": "Site2_InterContinental_WTC_Atrium",
                "pos": Vector((-220.0, 240.0, 85.0)),
                "look_at": Vector((-205.0, 275.0, 25.0)),
                "lens": 45
            },
            {
                "name": "Site3_SaintPaul_Perimeter_Roofscape",
                "pos": Vector((140.0, -140.0, 75.0)),
                "look_at": Vector((150.0, -90.0, 20.0)),
                "lens": 45
            },
            {
                "name": "Site4_PlaceDArmes_Apron_BMO",
                "pos": Vector((-15.0, 30.0, 45.0)),
                "look_at": Vector((-20.0, 75.0, 10.0)),
                "lens": 35
            },
            {
                "name": "Site5_PlaceJacquesCartier_Promenade",
                "pos": Vector((370.0, 20.0, 50.0)),
                "look_at": Vector((400.0, 70.0, 10.0)),
                "lens": 35
            }
        ]

        scene = bpy.context.scene
        # Set fast EEVEE settings for crisp snapshot verification
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'

        created_cam_obj = None
        for cam_spec in camera_targets:
            cam_name = cam_spec["name"]
            img_path = os.path.join(render_dir, f"{cam_name}.png")

            # Create or reuse camera
            cam_data = bpy.data.cameras.new(cam_name)
            cam_data.lens = cam_spec["lens"]
            cam_obj = bpy.data.objects.new(cam_name, cam_data)
            scene.collection.objects.link(cam_obj)

            # Position and orient camera towards look_at
            cam_obj.location = cam_spec["pos"]
            direction = cam_spec["look_at"] - cam_spec["pos"]
            rot_quat = direction.to_track_quat('-Z', 'Y')
            cam_obj.rotation_euler = rot_quat.to_euler()

            scene.camera = cam_obj
            scene.render.filepath = img_path

            t_rend0 = time.time()
            bpy.ops.render.render(write_still=True)
            t_rend = time.time() - t_rend0
            print(f"  Rendered {cam_name} in {t_rend:.2f}s -> {img_path}")

            # Clean up temporary camera object
            scene.collection.objects.unlink(cam_obj)
            bpy.data.objects.remove(cam_obj)
            bpy.data.cameras.remove(cam_data)

    # =========================================================================
    # Evaluation & Verdict
    # =========================================================================
    def evaluate(self):
        self.probe_roof_multitol()
        self.probe_ground_street_sidewalk_seams()
        self.probe_landmark_sites()
        self.render_targeted_snapshots()

        # Adversarial criteria for APPROVE:
        # 1. Macro roof conflicts at |Δz| < 0.05m must be 0
        r_tol005 = self.results["probes"]["roof_multitol"]["tolerances"]["0.05"]
        macro_005 = r_tol005["macro_exact"]

        # 2. Strict tolerance roof conflicts at |Δz| < 0.08m must be 0
        r_tol008 = self.results["probes"]["roof_multitol"]["tolerances"]["0.08"]
        macro_008 = r_tol008["macro_exact"]

        # 3. Ground macro conflicts (>= 2.0 m²) at |Δz| < 0.02m must be 0
        g_macro = self.results["probes"]["ground_seams"]["collisions"]["macro_2m"]

        # 4. Landmark sites must have 0 severe conflicts
        sites_failed = [k for k, v in self.results["landmark_sites"].items() if v["status"] == "FAIL"]

        if macro_005 == 0 and macro_008 == 0 and g_macro == 0 and len(sites_failed) == 0:
            verdict = "APPROVE"
        else:
            verdict = "REJECT"

        self.results["verdict"] = verdict
        self.results["summary"] = {
            "verdict": verdict,
            "macro_roof_conflicts_005": macro_005,
            "macro_roof_conflicts_008": macro_008,
            "micro_roof_conflicts_005": r_tol005["micro_exact"],
            "ground_macro_conflicts": g_macro,
            "landmark_sites_failed": sites_failed
        }

        print("\n" + "=" * 78)
        print(f"ADVERSARIAL CHALLENGE FINAL VERDICT: {verdict}")
        print("=" * 78)
        print(f"  Roof Macro Conflicts (|Δz| < 0.05m, >=1.0m²): {macro_005}")
        print(f"  Roof Macro Conflicts (|Δz| < 0.08m, >=1.0m²): {macro_008}")
        print(f"  Roof Micro Conflicts (|Δz| < 0.05m, 0.05..1m²): {r_tol005['micro_exact']}")
        print(f"  Ground Macro Conflicts (|Δz| < 0.02m, >=2.0m²): {g_macro}")
        print(f"  Landmark Sites Status: {len(sites_failed)} failed out of {len(self.results['landmark_sites'])}")
        print("=" * 78)

        # Save JSON
        try:
            os.makedirs(os.path.dirname(self.output_json), exist_ok=True)
            with open(self.output_json, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2)
            print(f"[Report] Adversarial probe results saved to: {self.output_json}")
        except Exception as e:
            print(f"[Warning] Failed to save JSON report: {e}")

        return verdict


def main():
    argv = sys.argv
    args_to_parse = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--json-out", type=str, default="output/adversarial_probe_report.json")
    args = parser.parse_args(args_to_parse)

    challenger = MontrealAdversarialChallenger(verbose=args.verbose, output_json=args.json_out)
    verdict = challenger.evaluate()

    sys.exit(0 if verdict == "APPROVE" else 1)


if __name__ == "__main__":
    main()
