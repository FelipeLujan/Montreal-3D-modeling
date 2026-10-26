#!/usr/bin/env python3
"""
src/adversarial_roof_probe.py
==============================
Adversarial verification probe for complex building roofs in Old Montreal:
- MTL-VM-0007 (Compacted building interfaces & Cours Le Royer)
- MTL-VM-0011 (World Trade Centre glass/bronze atrium edges & mansards)
- MTL-VM-0013 (Palais de Justice stepped roof & Cormier annex)
- MTL-VM-0015 (Pointe-à-Callière Custom House roof/tower & Éperon belfry)

Probing Methods:
1. Standard & Relaxed Acceptance Criteria (Z > 3m, Area > 0.5m², overlap > 0.5m², |Δz| < 0.05m)
2. Slanted & Pitched Coplanar Face Audit (arbitrary normal vector alignment dot(n1, n2) > 0.98, plane distance < 0.03m)
3. Ray-Cast Depth Probing (BVH dense downward & angled camera rays to detect coplanar surfaces with |Δd| < 0.04m)
4. Deep-dive inspection of target landmark assemblies
"""

import sys
import os
import math
import time
from collections import defaultdict
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

EXCLUDED_KEYWORDS = (
    "tree", "jacaranda", "shrub", "statue", "lamp", "bench",
    "clock_bezel", "grate", "signage", "furniture", "bollard"
)

def get_visible_mesh_objs():
    objs = []
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.data and not o.hide_render:
            nl = o.name.lower()
            if not any(k in nl for k in EXCLUDED_KEYWORDS):
                objs.append(o)
    return objs

# -----------------------------------------------------------------------------
# 1. UPWARD FLAT ROOF AUDIT (Parameterized thresholds)
# -----------------------------------------------------------------------------
def audit_upward_roofs(mesh_objs, min_z=3.0, min_area=0.5, min_overlap=0.5, max_dz=0.05):
    print(f"\n--- Upward Roof Audit (Z > {min_z}m, Area > {min_area}m², Overlap > {min_overlap}m², |Δz| < {max_dz}m) ---")
    roof_faces = []
    for obj in mesh_objs:
        me = obj.data
        mw = obj.matrix_world
        rot_3x3 = mw.to_3x3()
        mats = [m.name if m else "None" for m in me.materials]
        for p in me.polygons:
            wn = (rot_3x3 @ p.normal).normalized()
            if wn.z > 0.88 and p.area > min_area:
                wc = mw @ p.center
                if wc.z > min_z:
                    mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                    xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                    ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                    roof_faces.append({
                        "obj": obj.name, "z": wc.z,
                        "xmin": min(xs), "xmax": max(xs),
                        "ymin": min(ys), "ymax": max(ys),
                        "mat": mat_name, "idx": p.index, "area": p.area,
                        "center": (wc.x, wc.y, wc.z)
                    })

    print(f"Collected {len(roof_faces)} upward roof polygons.")
    conflicts = []
    bucket_size = max_dz
    buckets = defaultdict(list)
    for f in roof_faces:
        b_idx = int(math.floor(f["z"] / bucket_size))
        buckets[b_idx].append(f)

    for b_idx in buckets:
        buckets[b_idx].sort(key=lambda f: f["xmin"])

    checked_pairs = 0
    for b_idx, faces_a in buckets.items():
        len_a = len(faces_a)
        # Check within bucket
        for i in range(len_a):
            f1 = faces_a[i]
            for j in range(i + 1, len_a):
                f2 = faces_a[j]
                if f2["xmin"] > f1["xmax"]:
                    break
                checked_pairs += 1
                if abs(f1["z"] - f2["z"]) < max_dz:
                    oy = min(f1["ymax"], f2["ymax"]) - max(f1["ymin"], f2["ymin"])
                    if oy > 0.0:
                        ox = min(f1["xmax"], f2["xmax"]) - f2["xmin"]
                        if ox * oy > min_overlap:
                            if f1["obj"] != f2["obj"] or f1["mat"] != f2["mat"]:
                                conflicts.append((f1, f2, ox * oy, abs(f1["z"] - f2["z"])))

        # Check adjacent bucket
        if (b_idx + 1) in buckets:
            faces_b = buckets[b_idx + 1]
            for f1 in faces_a:
                for f2 in faces_b:
                    if f2["xmin"] > f1["xmax"]:
                        break
                    if f2["xmax"] < f1["xmin"]:
                        continue
                    checked_pairs += 1
                    if abs(f1["z"] - f2["z"]) < max_dz:
                        oy = min(f1["ymax"], f2["ymax"]) - max(f1["ymin"], f2["ymin"])
                        if oy > 0.0:
                            ox = min(f1["xmax"], f2["xmax"]) - max(f1["xmin"], f2["xmin"])
                            if ox * oy > min_overlap:
                                if f1["obj"] != f2["obj"] or f1["mat"] != f2["mat"]:
                                    conflicts.append((f1, f2, ox * oy, abs(f1["z"] - f2["z"])))

    print(f"Result: {len(conflicts)} upward roof conflict pairs found.")
    for c in conflicts[:10]:
        f1, f2, o_area, dz = c
        print(f"  CONFLICT: {f1['obj']}[{f1['mat']}] (z={f1['z']:.2f}) <-> {f2['obj']}[{f2['mat']}] (z={f2['z']:.2f}) | Overlap: {o_area:.2f}m², Δz: {dz:.3f}m")
    return conflicts

# -----------------------------------------------------------------------------
# 2. SLANTED & ARBITRARY NORMAL COPLANAR AUDIT (Pitched, Mansard, Domes)
# -----------------------------------------------------------------------------
def audit_arbitrary_coplanar_roofs(mesh_objs, min_z=3.0, min_area=0.5, max_plane_dist=0.03):
    print(f"\n--- Arbitrary Normal Coplanar Audit (Z > {min_z}m, Area > {min_area}m², Plane Dist < {max_plane_dist}m) ---")
    faces = []
    for obj in mesh_objs:
        me = obj.data
        mw = obj.matrix_world
        rot_3x3 = mw.to_3x3()
        mats = [m.name if m else "None" for m in me.materials]
        for p in me.polygons:
            wc = mw @ p.center
            if wc.z < min_z or p.area < min_area:
                continue
            wn = (rot_3x3 @ p.normal).normalized()
            # Only exterior/upward-ish faces (normal.z > -0.1)
            if wn.z < -0.1:
                continue
            mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
            # Get world vertices
            w_verts = [mw @ me.vertices[vi].co for vi in p.vertices]
            xs = [v.x for v in w_verts]
            ys = [v.y for v in w_verts]
            zs = [v.z for v in w_verts]
            faces.append({
                "obj": obj.name, "mat": mat_name, "idx": p.index,
                "normal": wn, "center": wc, "area": p.area,
                "bbox": (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)),
                "verts": w_verts
            })

    print(f"Collected {len(faces)} exterior/slanted/flat roof polygons (Z > {min_z}m).")
    
    # Spatial hash / grid for broadphase
    grid_size = 5.0
    grid = defaultdict(list)
    for idx, f in enumerate(faces):
        bb = f["bbox"]
        gx0, gx1 = int(math.floor(bb[0] / grid_size)), int(math.floor(bb[1] / grid_size))
        gy0, gy1 = int(math.floor(bb[2] / grid_size)), int(math.floor(bb[3] / grid_size))
        gz0, gz1 = int(math.floor(bb[4] / grid_size)), int(math.floor(bb[5] / grid_size))
        for gx in range(gx0, gx1 + 1):
            for gy in range(gy0, gy1 + 1):
                for gz in range(gz0, gz1 + 1):
                    grid[(gx, gy, gz)].append(idx)

    tested_pairs = set()
    coplanar_conflicts = []

    for cell, face_indices in grid.items():
        n_in_cell = len(face_indices)
        for i in range(n_in_cell):
            idx1 = face_indices[i]
            for j in range(i + 1, n_in_cell):
                idx2 = face_indices[j]
                pair_key = (min(idx1, idx2), max(idx1, idx2))
                if pair_key in tested_pairs:
                    continue
                tested_pairs.add(pair_key)

                f1 = faces[idx1]
                f2 = faces[idx2]

                # Same object AND same material -> not a Z-fighting conflict
                if f1["obj"] == f2["obj"] and f1["mat"] == f2["mat"]:
                    continue

                # Normal parallel check
                dot_n = f1["normal"].dot(f2["normal"])
                if dot_n < 0.98:
                    continue

                # Bounding box overlap in 3D
                b1, b2 = f1["bbox"], f2["bbox"]
                if (b1[1] < b2[0] or b2[1] < b1[0] or
                    b1[3] < b2[2] or b2[3] < b1[2] or
                    b1[5] < b2[4] or b2[5] < b1[4]):
                    continue

                # Perpendicular plane distance: distance from f2 center to f1 plane
                plane_d = abs(f1["normal"].dot(f2["center"] - f1["center"]))
                if plane_d < max_plane_dist:
                    # 3D bounding box overlap volume or 2D overlap on common projection
                    ox = max(0.0, min(b1[1], b2[1]) - max(b1[0], b2[0]))
                    oy = max(0.0, min(b1[3], b2[3]) - max(b1[2], b2[2]))
                    oz = max(0.0, min(b1[5], b2[5]) - max(b1[4], b2[4]))
                    # Projected overlap check
                    if (ox > 0.3 and oy > 0.3) or (ox * oy > 0.2):
                        coplanar_conflicts.append((f1, f2, plane_d, dot_n, ox * oy))

    print(f"Result: {len(coplanar_conflicts)} arbitrary coplanar conflict pairs found.")
    for c in coplanar_conflicts[:10]:
        f1, f2, pd, dot_n, a_est = c
        print(f"  COPLANAR: {f1['obj']}[{f1['mat']}] <-> {f2['obj']}[{f2['mat']}] | PlaneDist: {pd*100:.1f}cm, dot: {dot_n:.4f}, approx XY: {a_est:.2f}m²")
    return coplanar_conflicts

# -----------------------------------------------------------------------------
# 3. EMPIRICAL RAY-CASTING & MULTI-ANGLE CAMERA PROBE
# -----------------------------------------------------------------------------
def audit_raycast_depth(mesh_objs, bounds, ray_step=0.6, dz_thresh=0.035):
    """
    Constructs a BVH tree of visible roof geometry and fires dense rays from above
    and at 45 degree angles to empirically detect coplanar surfaces.
    """
    print(f"\n--- Empirical BVH Ray-Casting Audit (Step: {ray_step}m, Depth Threshold: {dz_thresh*100:.1f}cm) ---")
    
    # Build BVH tree from all visible objects
    t0 = time.time()
    all_polys = []
    all_verts = []
    face_meta = [] # (obj_name, mat_name, polygon_index)

    vert_offset = 0
    for obj in mesh_objs:
        me = obj.data
        mw = obj.matrix_world
        mats = [m.name if m else "None" for m in me.materials]
        for v in me.vertices:
            all_verts.append(mw @ v.co)
        for p in me.polygons:
            poly_v = [vi + vert_offset for vi in p.vertices]
            all_polys.append(poly_v)
            mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
            face_meta.append((obj.name, mat_name, p.index))
        vert_offset += len(me.vertices)

    print(f"Compiling BVH tree from {len(all_verts)} vertices and {len(all_polys)} polygons...")
    bvh = BVHTree.FromPolygons(all_verts, all_polys)
    t_bvh = time.time() - t0
    print(f"BVH built in {t_bvh:.2f}s.")

    # Ray patterns:
    # 1. Straight down (0, 0, -1) from Z=100m
    # 2. Angled at 30 deg from vertical (e.g., sun/aerial cam): (0.5, 0.3, -1).normalized()
    ray_dirs = [
        ("TopDown", Vector((0.0, 0.0, -1.0))),
        ("Angled_NE", Vector((0.35, 0.35, -0.87)).normalized()),
        ("Angled_SW", Vector((-0.35, -0.35, -0.87)).normalized())
    ]

    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    ray_conflicts = []
    total_rays = 0

    for mode_name, rdir in ray_dirs:
        mode_conflicts = 0
        cur_y = ymin
        while cur_y <= ymax:
            cur_x = xmin
            while cur_x <= xmax:
                total_rays += 1
                # Origin high above
                origin = Vector((cur_x, cur_y, zmax + 20.0))
                if mode_name != "TopDown":
                    origin -= rdir * 25.0

                # Cast ray
                hit1_loc, hit1_nor, hit1_idx, hit1_dist = bvh.ray_cast(origin, rdir)
                if hit1_loc is not None and hit1_loc.z > 3.0:
                    obj1, mat1, pidx1 = face_meta[hit1_idx]
                    # Nudge forward slightly past hit1 and cast again to see if another surface is right behind
                    nudge_origin = hit1_loc + rdir * 0.001
                    hit2_loc, hit2_nor, hit2_idx, hit2_dist = bvh.ray_cast(nudge_origin, rdir)
                    if hit2_loc is not None:
                        dist_between = (hit2_loc - hit1_loc).length
                        if dist_between < dz_thresh and hit2_loc.z > 3.0:
                            obj2, mat2, pidx2 = face_meta[hit2_idx]
                            # Only a conflict if different object or different material
                            if obj1 != obj2 or mat1 != mat2:
                                # Check if normals are facing towards the ray
                                dot1 = hit1_nor.dot(rdir)
                                dot2 = hit2_nor.dot(rdir)
                                if dot1 < 0 and dot2 < 0: # both facing ray
                                    ray_conflicts.append({
                                        "mode": mode_name,
                                        "pos": (hit1_loc.x, hit1_loc.y, hit1_loc.z),
                                        "obj1": obj1, "mat1": mat1,
                                        "obj2": obj2, "mat2": mat2,
                                        "gap": dist_between,
                                        "dot_n": hit1_nor.dot(hit2_nor)
                                    })
                                    mode_conflicts += 1
                cur_x += ray_step
            cur_y += ray_step
        print(f"  {mode_name:10s} cast complete: {mode_conflicts} coplanar ray collisions detected.")

    print(f"Total rays cast: {total_rays:,} | Total coplanar ray conflicts: {len(ray_conflicts)}")
    for rc in ray_conflicts[:15]:
        print(f"  RAY CONFLICT ({rc['mode']}): at ({rc['pos'][0]:.1f}, {rc['pos'][1]:.1f}, {rc['pos'][2]:.2f}) | {rc['obj1']}[{rc['mat1']}] <-> {rc['obj2']}[{rc['mat2']}] | Gap: {rc['gap']*100:.2f}cm, dot: {rc['dot_n']:.3f}")
    return ray_conflicts

# -----------------------------------------------------------------------------
# 4. TARGET ASSEMBLY DEEP DIVES
# -----------------------------------------------------------------------------
def inspect_target_assemblies(block_id):
    print(f"\n" + "=" * 78)
    print(f"TARGET ASSEMBLY AUDIT: {block_id}")
    print("=" * 78)
    
    if block_id == "MTL-VM-0013":
        # Palais de Justice & Cormier Annex
        pdj_objs = [o for o in bpy.data.objects if "PDJ_" in o.name or "Cormier_" in o.name or "626" in o.name]
        print(f"Found {len(pdj_objs)} Palais de Justice / Cormier / Rue Saint-Gabriel objects.")
        for o in pdj_objs:
            if o.type == 'MESH':
                mats = [m.name if m else "None" for m in o.data.materials]
                bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
                zmin, zmax = min(v.z for v in bb), max(v.z for v in bb)
                print(f"  {o.name:32s} | Z=[{zmin:.2f}, {zmax:.2f}] | Faces: {len(o.data.polygons):4d} | Mats: {mats}")

    elif block_id == "MTL-VM-0011":
        # WTC Atrium & Wings
        wtc_objs = [o for o in bpy.data.objects if "WTC" in o.name or "Atrium" in o.name or "1046748" in o.name]
        print(f"Found {len(wtc_objs)} WTC Atrium & South Wing objects.")
        for o in wtc_objs:
            if o.type == 'MESH':
                mats = [m.name if m else "None" for m in o.data.materials]
                bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
                zmin, zmax = min(v.z for v in bb), max(v.z for v in bb)
                print(f"  {o.name:32s} | Z=[{zmin:.2f}, {zmax:.2f}] | Faces: {len(o.data.polygons):4d} | Mats: {mats}")

    elif block_id == "MTL-VM-0015":
        # Pointe-à-Callière & Custom House
        pac_objs = [o for o in bpy.data.objects if "CustomHouse" in o.name or "PointeACalliere" in o.name or "87411" in o.name or "Obelisk" in o.name]
        print(f"Found {len(pac_objs)} Pointe-à-Callière & Custom House objects.")
        for o in pac_objs:
            if o.type == 'MESH':
                mats = [m.name if m else "None" for m in o.data.materials]
                bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
                zmin, zmax = min(v.z for v in bb), max(v.z for v in bb)
                print(f"  {o.name:32s} | Z=[{zmin:.2f}, {zmax:.2f}] | Faces: {len(o.data.polygons):4d} | Mats: {mats}")

    elif block_id == "MTL-VM-0007":
        # Compacted building interfaces
        bldg_objs = [o for o in bpy.data.objects if "Bldg_" in o.name and not o.hide_render]
        print(f"Found {len(bldg_objs)} visible building components in Block 7.")
        roof_objs = [o for o in bldg_objs if any(k in o.name for k in ("RoofCap", "Mansard", "PitchedRoof", "FlatDeck", "HVAC", "Skylight", "Solar"))]
        print(f"Found {len(roof_objs)} roof/roofcap/accessory objects:")
        for o in sorted(roof_objs, key=lambda x: x.name)[:25]:
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            zmin, zmax = min(v.z for v in bb), max(v.z for v in bb)
            mats = [m.name if m else "None" for m in o.data.materials]
            print(f"  {o.name:32s} | Z=[{zmin:.2f}, {zmax:.2f}] | Faces: {len(o.data.polygons):4d} | Mats: {mats}")


# -----------------------------------------------------------------------------
# MAIN RUNNER
# -----------------------------------------------------------------------------
def run_probe(block_id):
    print("\n" + "#" * 78)
    print(f"  ADVERSARIAL PROBE HARNESS: {block_id}")
    print("#" * 78)

    mesh_objs = get_visible_mesh_objs()
    print(f"Visible non-prop mesh objects: {len(mesh_objs)}")

    # Compute district/block bounding box
    all_bb = []
    for o in mesh_objs:
        for c in o.bound_box:
            all_bb.append(o.matrix_world @ Vector(c))
    if not all_bb:
        print("ERROR: No visible geometry found!")
        return
    bounds = (
        min(v.x for v in all_bb), max(v.x for v in all_bb),
        min(v.y for v in all_bb), max(v.y for v in all_bb),
        min(v.z for v in all_bb), max(v.z for v in all_bb)
    )
    print(f"Block Bounds: X=[{bounds[0]:.1f}, {bounds[1]:.1f}], Y=[{bounds[2]:.1f}, {bounds[3]:.1f}], Z=[{bounds[4]:.1f}, {bounds[5]:.1f}]")

    # 1. Target assembly inspection
    inspect_target_assemblies(block_id)

    # 2. Strict Project Criterion Audit (Z>3m, Area>1.0m², Overlap>1.0m², |Δz|<0.05m)
    c1 = audit_upward_roofs(mesh_objs, min_z=3.0, min_area=1.0, min_overlap=1.0, max_dz=0.05)

    # 3. Adversarial Stressed Criterion Audit (Z>3m, Area>0.3m², Overlap>0.3m², |Δz|<0.05m)
    c2 = audit_upward_roofs(mesh_objs, min_z=3.0, min_area=0.3, min_overlap=0.3, max_dz=0.05)

    # 4. Arbitrary Slanted & Pitched Coplanar Audit
    c3 = audit_arbitrary_coplanar_roofs(mesh_objs, min_z=3.0, min_area=0.5, max_plane_dist=0.03)

    # 5. Ray-Cast Depth Probing
    c4 = audit_raycast_depth(mesh_objs, bounds, ray_step=0.75, dz_thresh=0.035)

    print("\n" + "=" * 78)
    print(f"SUMMARY FOR {block_id}:")
    print(f"  1. Standard Roof Conflicts (Area>1m², Overlap>1m²): {len(c1)}")
    print(f"  2. Stressed Roof Conflicts (Area>0.3m², Overlap>0.3m²): {len(c2)}")
    print(f"  3. Slanted / Pitched Coplanar Conflicts: {len(c3)}")
    print(f"  4. Empirical Ray-Cast Coplanar Collisions: {len(c4)}")
    print("=" * 78)
    
    return {
        "block": block_id,
        "standard_conflicts": len(c1),
        "stressed_conflicts": len(c2),
        "slanted_conflicts": len(c3),
        "raycast_conflicts": len(c4)
    }

if __name__ == "__main__":
    block = sys.argv[-1] if len(sys.argv) > 1 and "MTL-VM" in sys.argv[-1] else "MTL-VM-0013"
    run_probe(block)
