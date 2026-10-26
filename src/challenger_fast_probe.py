#!/usr/bin/env python3
r"""
src/challenger_fast_probe.py
============================
High-Performance Adversarial Verification Probe for Master Scene (output/montreal_master.blend).
Executes fast geometric sweeps and site inspections in < 15 seconds.
"""

import sys
import os
import math
import time
import json
from collections import defaultdict

try:
    import bpy
    from mathutils import Vector
except ImportError:
    print("ERROR: Must run inside Blender 5.2", file=sys.stderr)
    sys.exit(2)

EXCLUDED_KEYWORDS = (
    "tree", "jacaranda", "shrub", "statue", "lamp", "bench",
    "clock_bezel", "grate", "signage", "furniture", "bollard"
)

def run_challenger_probes():
    t0 = time.time()
    results = {}

    visible_meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]
    print(f"Loaded {len(visible_meshes)} visible mesh objects.")

    # -------------------------------------------------------------------------
    # 1. Multi-Tolerance Roof Z-Fighting Probes (|Δz| < 0.08m, 0.05m, 0.01m)
    # -------------------------------------------------------------------------
    roof_faces = []
    for obj in visible_meshes:
        nl = obj.name.lower()
        if any(k in nl for k in EXCLUDED_KEYWORDS):
            continue
        me = obj.data
        mw = obj.matrix_world
        rot_3x3 = mw.to_3x3()
        mats = [m.name if m else "None" for m in me.materials]
        for p in me.polygons:
            wn = (rot_3x3 @ p.normal).normalized()
            if wn.z > 0.88 and p.area > 0.20:
                wc = mw @ p.center
                if wc.z > 3.0:
                    mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                    xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                    ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                    roof_faces.append((obj.name, wc.z, min(xs), max(xs), min(ys), max(ys), mat_name, p.area))

    print(f"Collected {len(roof_faces):,} roof candidate polygons (Z > 3m, Area > 0.2m²).")

    # Bucket by 0.08m
    BUCKET_DZ = 0.08
    buckets = defaultdict(list)
    for f in roof_faces:
        b_idx = int(math.floor(f[1] / BUCKET_DZ))
        buckets[b_idx].append(f)
    for b in buckets.values():
        b.sort(key=lambda item: item[2])

    tol_counts = {
        "0.08": {"macro": 0, "micro": 0, "pairs": []},
        "0.05": {"macro": 0, "micro": 0, "pairs": []},
        "0.01": {"macro": 0, "micro": 0, "pairs": []}
    }

    for b_idx, faces_a in buckets.items():
        candidates = [faces_a]
        if (b_idx + 1) in buckets:
            candidates.append(buckets[b_idx + 1])
        len_a = len(faces_a)
        for i in range(len_a):
            f1 = faces_a[i]
            for c_list in candidates:
                start_j = (i + 1) if c_list is faces_a else 0
                for j in range(start_j, len(c_list)):
                    f2 = c_list[j]
                    if f2[2] > f1[3]:
                        break
                    if f2[3] < f1[2]:
                        continue
                    if f1[0] == f2[0] and f1[6] == f2[6]:
                        continue
                    dz = abs(f1[1] - f2[1])
                    if dz >= 0.08:
                        continue
                    oy = min(f1[5], f2[5]) - max(f1[4], f2[4])
                    if oy <= 0.0:
                        continue
                    ox = min(f1[3], f2[3]) - max(f1[2], f2[2])
                    if ox <= 0.0:
                        continue
                    ov = ox * oy
                    for tol_str, tol_val in (("0.08", 0.08), ("0.05", 0.05), ("0.01", 0.01)):
                        if dz < tol_val:
                            if ov >= 1.0:
                                tol_counts[tol_str]["macro"] += 1
                                if len(tol_counts[tol_str]["pairs"]) < 5:
                                    tol_counts[tol_str]["pairs"].append((f1[0], f2[0], round(dz, 4), round(ov, 2)))
                            elif ov >= 0.05:
                                tol_counts[tol_str]["micro"] += 1

    print("\n--- Roof Multi-Tolerance Sweep Results ---")
    for t in ("0.08", "0.05", "0.01"):
        print(f"  |Δz| < {t}m : Macro (>=1.0m²) = {tol_counts[t]['macro']}, Micro (0.05..1.0m²) = {tol_counts[t]['micro']}")
    results["roof_tolerances"] = tol_counts

    # -------------------------------------------------------------------------
    # 2. Street, Sidewalk, and Curb Seam Checks
    # -------------------------------------------------------------------------
    curb_obj = bpy.data.objects.get("District_Curbs_3D")
    sidewalk_obj = bpy.data.objects.get("District_Sidewalks_Raised")
    road_objs = [o for o in visible_meshes if any(k in o.name.lower() for k in ("roadbed", "street", "asphalt", "cobble"))]

    curb_normals = set(round(p.normal.z, 2) for p in curb_obj.data.polygons) if curb_obj else set()
    curb_zs = [(curb_obj.matrix_world @ v.co).z for v in curb_obj.data.vertices] if curb_obj else []
    sidewalk_zs = [(sidewalk_obj.matrix_world @ v.co).z for v in sidewalk_obj.data.vertices] if sidewalk_obj else []

    print("\n--- Street, Sidewalk & Curb Seam Integrity ---")
    print(f"  District_Curbs_3D: face count = {len(curb_obj.data.polygons) if curb_obj else 0}")
    print(f"  Curb Normal Z values: {curb_normals} (Expected 3D normals: {0.0, 1.0, -1.0})")
    print(f"  Curb Z range: [{min(curb_zs):.3f}m, {max(curb_zs):.3f}m]" if curb_zs else "None")
    print(f"  Sidewalk Z range: [{min(sidewalk_zs):.3f}m, {max(sidewalk_zs):.3f}m]" if sidewalk_zs else "None")

    is_curb_2d_flat = (curb_normals == {1.0} and (max(curb_zs) - min(curb_zs) < 0.001)) if curb_zs else False
    print(f"  --> Curb Geometry Integrity: {'FAIL (FLAT 2D RIBBON HOVERING IN AIR)' if is_curb_2d_flat else 'PASS (REAL 3D PRISM)'}")

    # Check Sidewalk Penetration into Buildings
    bldg_objs = [
        o for o in visible_meshes
        if not any(k in o.name.lower() for k in ("street", "road", "curb", "sidewalk", "asphalt", "cobble", "plaza", "tree", "lamp", "bench", "grate", "sign"))
    ]
    bldg_bboxes = []
    for b in bldg_objs:
        bb = [b.matrix_world @ Vector(c) for c in b.bound_box]
        min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
        min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)
        min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
        if max_z > 3.0 and (max_x - min_x) > 3.0 and (max_y - min_y) > 3.0:
            bldg_bboxes.append((b.name, min_x, max_x, min_y, max_y))

    penetrated_buildings = set()
    if sidewalk_obj:
        mw = sidewalk_obj.matrix_world
        me = sidewalk_obj.data
        for p in me.polygons:
            wc = mw @ p.center
            for bname, bx1, bx2, by1, by2 in bldg_bboxes:
                if bx1 + 0.5 <= wc.x <= bx2 - 0.5 and by1 + 0.5 <= wc.y <= by2 - 0.5:
                    penetrated_buildings.add(bname)

    print(f"  Sidewalk Building Interior Penetrations: {len(penetrated_buildings)} buildings penetrated by sidewalk ribbon!")
    results["curb_2d_flat"] = is_curb_2d_flat
    results["sidewalk_building_penetrations_count"] = len(penetrated_buildings)

    # -------------------------------------------------------------------------
    # 3. PBR Texture and UV Layer Inspection
    # -------------------------------------------------------------------------
    street_mats = [
        "Mat_MTL_Asphalt_Road", "Mat_MTL_Cobblestone_Historic", "Mat_MTL_Granite_Curb",
        "Mat_MTL_Sidewalk_Concrete", "Mat_MTL_Road_Markings"
    ]
    mat_tex_counts = {}
    for mn in street_mats:
        m = bpy.data.materials.get(mn)
        tex_nodes = [n.name for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'] if (m and m.node_tree) else []
        mat_tex_counts[mn] = len(tex_nodes)

    street_objects = [o for o in visible_meshes if any(k in o.name.lower() for k in ("roadbed", "district_curb", "district_sidewalk", "district_crosswalk"))]
    objects_without_uvs = [o.name for o in street_objects if len(o.data.uv_layers) == 0]

    print("\n--- PBR Texture & UV Map Integrity ---")
    print(f"  Materials Image Texture Nodes Count: {mat_tex_counts}")
    print(f"  Street Objects without UV Layers: {len(objects_without_uvs)} / {len(street_objects)}")
    results["mat_tex_counts"] = mat_tex_counts
    results["objects_without_uvs_count"] = len(objects_without_uvs)

    # -------------------------------------------------------------------------
    # 4. Probing Complex Collision Sites
    # -------------------------------------------------------------------------
    print("\n--- Probing 5 Critical Collision Sites ---")
    sites = {
        "Site1_Palais_de_Justice_Block13": {"kw": ["0013", "palais", "cormier", "justice"]},
        "Site2_InterContinental_WTC_Block11": {"kw": ["0011", "wtc", "intercontinental", "royal_bank"]},
        "Site3_SaintPaul_Block7": {"kw": ["0007", "saint_paul", "saint_sulpice", "cours_le_royer"]},
        "Site4_PlaceDArmes_BMO_Block1_3": {"kw": ["0001", "0003", "bmo", "pantheon", "beauxarts", "place_darmes"]},
        "Site5_PlaceJacquesCartier": {"kw": ["jacques", "cartier", "promenade", "ramezay"]}
    }

    site_results = {}
    for s_name, s_info in sites.items():
        site_objs = [o for o in visible_meshes if any(k in o.name.lower() for k in s_info["kw"])]
        site_roofs = [f for f in roof_faces if any(f[0] == o.name for o in site_objs)]
        site_conflicts = 0
        for i in range(len(site_roofs)):
            f1 = site_roofs[i]
            for j in range(i + 1, len(site_roofs)):
                f2 = site_roofs[j]
                if f1[0] == f2[0] and f1[6] == f2[6]:
                    continue
                if abs(f1[1] - f2[1]) < 0.08:
                    if min(f1[3], f2[3]) > max(f1[2], f2[2]) and min(f1[5], f2[5]) > max(f1[4], f2[4]):
                        site_conflicts += 1
        site_results[s_name] = {
            "objects_count": len(site_objs),
            "roof_faces_count": len(site_roofs),
            "conflicts_at_008": site_conflicts
        }
        print(f"  {s_name:35s}: objs={len(site_objs):3d} | roof_faces={len(site_roofs):4d} | conflicts(|Δz|<0.08m)={site_conflicts}")

    results["sites"] = site_results

    # Summary
    elapsed = time.time() - t0
    print(f"\nChallenger probe completed in {elapsed:.2f} seconds.")
    return results

if __name__ == "__main__":
    run_challenger_probes()
