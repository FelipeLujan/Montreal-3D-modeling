"""
src/prototype_deconflict.py
Prototype unified deconfliction algorithm for Criterion 1 and Criterion 2.
"""
import bpy
import bmesh
import time
import math
from collections import defaultdict
import sys

PROJECT_ROOT = r"C:\Users\Felipe\Documents\coding\montreal"
sys.path.append(PROJECT_ROOT)
from src.audit_zfighting_headless import MontrealZFightingAuditor, EXCLUDED_OBJECT_KEYWORDS

log = print

def run_prototype():
    log("Starting prototype deconfliction pass...")
    t0 = time.time()

    # -------------------------------------------------------------------------
    # PART 1: DECONFLICT GROUND (CRITERION 2)
    # -------------------------------------------------------------------------
    log("\n--- DECONFLICTING GROUND (CRITERION 2) ---")
    
    # 1. Ensure District_Curbs_3D top is at Z = +0.180m (3 cm above sidewalk)
    curbs = bpy.data.objects.get("District_Curbs_3D")
    if curbs and curbs.data:
        me = curbs.data
        for v in me.vertices:
            if v.co.z > 0.10:
                v.co.z = 0.180
        log("  Raised District_Curbs_3D top to Z = +0.180m.")

    # 2. Building plinth ground-level horizontal face cleanup
    # Remove upward-facing window glass/frame faces or bottom caps at Z <= 0.20m with area > 1.5m²
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data or obj.hide_render:
            continue
        nl = obj.name.lower()
        if any(k in nl for k in ["district_", "street", "road", "plaza", "tree", "lamp"]):
            continue
        me = obj.data
        mw = obj.matrix_world
        mats = [m.name if m else "None" for m in me.materials]
        rot_3x3 = mw.to_3x3()
        del_faces = []
        for p in me.polygons:
            wn = (rot_3x3 @ p.normal).normalized()
            if wn.z > 0.88 and p.area > 1.5:
                wc = mw @ p.center
                if -0.30 <= wc.z <= 0.25:
                    mat_name = mats[p.material_index].lower() if p.material_index < len(mats) else ""
                    if any(k in mat_name for k in ["glass", "frame", "window"]) or abs(wc.z) < 0.05:
                        del_faces.append(p.index)
        if del_faces:
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            to_del = [bm.faces[i] for i in del_faces if i < len(bm.faces)]
            bmesh.ops.delete(bm, geom=to_del, context="FACES")
            bm.to_mesh(me)
            bm.free()

    # 3. Sidewalk / Plaza overlaps
    # Find all ground candidate faces and deconflict
    visible_mesh_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]
    ground_faces = []
    for obj in visible_mesh_objs:
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
                    ground_faces.append((obj.name, wc.z, min(xs), max(xs), min(ys), max(ys), mat_name, p.index, p.area))

    BUCKET_DZ = 0.02
    buckets = defaultdict(list)
    for f in ground_faces:
        buckets[int(math.floor(f[1] / BUCKET_DZ))].append(f)
    for b_idx in buckets:
        buckets[b_idx].sort(key=lambda f: f[2])

    ground_del_faces = defaultdict(set)
    ground_offset_faces = defaultdict(set)

    def check_ground(f1, f2):
        o1, z1, x1a, x1b, y1a, y1b, m1, idx1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6], f1[7]
        o2, z2, x2a, x2b, y2a, y2b, m2, idx2 = f2[0], f2[1], f2[2], f2[3], f2[4], f2[5], f2[6], f2[7]
        if abs(z1 - z2) < 0.02:
            oy = min(y1b, y2b) - max(y1a, y2a)
            if oy > 0.0:
                ox = min(x1b, x2b) - max(x1a, x2a)
                if ox * oy > 2.0:
                    if o1 != o2 or m1 != m2:
                        # Prioritize: Plazas & Buildings keep their ground; Sidewalk/Curb yields
                        if "district_sidewalk" in o1.lower() or "district_curb" in o1.lower():
                            ground_del_faces[o1].add(idx1)
                        elif "district_sidewalk" in o2.lower() or "district_curb" in o2.lower():
                            ground_del_faces[o2].add(idx2)
                        elif "plaza" in o1.lower() and "plaza" not in o2.lower():
                            ground_del_faces[o2].add(idx2)
                        elif "plaza" in o2.lower() and "plaza" not in o1.lower():
                            ground_del_faces[o1].add(idx1)
                        else:
                            # Generic: offset the lower one down by 0.03m
                            if z1 <= z2:
                                ground_offset_faces[o1].add(idx1)
                            else:
                                ground_offset_faces[o2].add(idx2)

    for b_idx, faces_a in buckets.items():
        len_a = len(faces_a)
        for i in range(len_a):
            f1 = faces_a[i]
            for j in range(i + 1, len_a):
                if faces_a[j][2] > f1[3]:
                    break
                check_ground(f1, faces_a[j])
        if (b_idx + 1) in buckets:
            for f1 in faces_a:
                for f2 in buckets[b_idx + 1]:
                    if f2[2] > f1[3]:
                        break
                    if f2[3] < f1[2]:
                        continue
                    check_ground(f1, f2)

    for oname, p_indices in ground_del_faces.items():
        obj = bpy.data.objects.get(oname)
        if obj and obj.data:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            to_del = [bm.faces[i] for i in p_indices if i < len(bm.faces)]
            bmesh.ops.delete(bm, geom=to_del, context="FACES")
            bm.to_mesh(obj.data)
            bm.free()
            log(f"  Deleted {len(to_del)} conflicting ground faces on {oname}.")

    for oname, p_indices in ground_offset_faces.items():
        obj = bpy.data.objects.get(oname)
        if obj and obj.data:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            target_faces = [bm.faces[i] for i in p_indices if i < len(bm.faces)]
            res = bmesh.ops.split(bm, geom=target_faces, use_only_faces=False)
            verts_to_move = set(v for nf in res["geom"] if isinstance(nf, bmesh.types.BMFace) for v in nf.verts)
            for v in verts_to_move:
                v.co.z -= 0.04
            bm.to_mesh(obj.data)
            bm.free()
            log(f"  Offset {len(target_faces)} ground faces down by 0.04m on {oname}.")

    # -------------------------------------------------------------------------
    # PART 2: DECONFLICT ROOF & CORNICE (CRITERION 1)
    # -------------------------------------------------------------------------
    log("\n--- DECONFLICTING ROOF & CORNICE (CRITERION 1) ---")

    # Pass 1: Eliminate horizontal window glass / frame caps at Z > 3.0m
    # Window glass should be vertical; horizontal glass caps are internal geometry that fight with roofs
    glass_caps_deleted = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data or obj.hide_render:
            continue
        nl = obj.name.lower()
        if any(k in nl for k in EXCLUDED_OBJECT_KEYWORDS):
            continue
        me = obj.data
        mw = obj.matrix_world
        rot_3x3 = mw.to_3x3()
        mats = [m.name if m else "None" for m in me.materials]
        del_faces = []
        for p in me.polygons:
            wn = (rot_3x3 @ p.normal).normalized()
            if wn.z > 0.88 and p.area > 1.0:
                wc = mw @ p.center
                if wc.z > 3.0:
                    mat_name = mats[p.material_index].lower() if p.material_index < len(mats) else ""
                    # If this face has glass or frame material on an upward horizontal face > 1.0m²
                    if any(k in mat_name for k in ["glass", "vitre", "fenetre", "frame_green", "frame_dark", "bronze_dark"]):
                        del_faces.append(p.index)
        if del_faces:
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            to_del = [bm.faces[i] for i in del_faces if i < len(bm.faces)]
            bmesh.ops.delete(bm, geom=to_del, context="FACES")
            bm.to_mesh(me)
            bm.free()
            glass_caps_deleted += len(to_del)

    log(f"  Deleted {glass_caps_deleted} internal horizontal glass/frame caps at Z > 3.0m.")

    # Pass 2: Iterative Roof / Cornice spatial deconfliction
    # In each iteration, detect exact conflict pairs and offset one face by 0.07m
    for iteration in range(1, 4):
        log(f"\nRoof Deconfliction Iteration {iteration}...")
        visible_mesh_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]
        roof_faces = []
        for obj in visible_mesh_objs:
            nl = obj.name.lower()
            if any(k in nl for k in EXCLUDED_OBJECT_KEYWORDS):
                continue
            me = obj.data
            mw = obj.matrix_world
            rot_3x3 = mw.to_3x3()
            mats = [m.name if m else "None" for m in me.materials]
            for p in me.polygons:
                wn = (rot_3x3 @ p.normal).normalized()
                if wn.z > 0.88 and p.area > 1.0:
                    wc = mw @ p.center
                    if wc.z > 3.0:
                        mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                        xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                        ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                        roof_faces.append((obj.name, wc.z, min(xs), max(xs), min(ys), max(ys), mat_name, p.index, p.area))

        BUCKET_DZ = 0.05
        buckets = defaultdict(list)
        for f in roof_faces:
            buckets[int(math.floor(f[1] / BUCKET_DZ))].append(f)
        for b_idx in buckets:
            buckets[b_idx].sort(key=lambda f: f[2])

        faces_to_offset = defaultdict(set)
        faces_to_delete = defaultdict(set)

        def is_roof_mat(m):
            return any(k in m.lower() for k in ["roof", "membrane", "slate", "tar", "deck"])

        def check_roof(f1, f2):
            o1, z1, x1a, x1b, y1a, y1b, m1, idx1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6], f1[7]
            o2, z2, x2a, x2b, y2a, y2b, m2, idx2 = f2[0], f2[1], f2[2], f2[3], f2[4], f2[5], f2[6], f2[7]
            if abs(z1 - z2) < 0.05:
                oy = min(y1b, y2b) - max(y1a, y2a)
                if oy > 0.0:
                    ox = min(x1b, f2[3]) - f2[2]
                    if ox * oy > 1.0:
                        if o1 != o2 or m1 != m2:
                            # If roof membrane vs wall/cornice: roof membrane recesses down
                            if is_roof_mat(m1) and not is_roof_mat(m2):
                                faces_to_offset[o1].add(idx1)
                            elif is_roof_mat(m2) and not is_roof_mat(m1):
                                faces_to_offset[o2].add(idx2)
                            elif z1 <= z2:
                                faces_to_offset[o1].add(idx1)
                            else:
                                faces_to_offset[o2].add(idx2)

        for b_idx, faces_a in buckets.items():
            len_a = len(faces_a)
            for i in range(len_a):
                f1 = faces_a[i]
                for j in range(i + 1, len_a):
                    if faces_a[j][2] > f1[3]:
                        break
                    check_roof(f1, faces_a[j])
            if (b_idx + 1) in buckets:
                for f1 in faces_a:
                    for f2 in buckets[b_idx + 1]:
                        if f2[2] > f1[3]:
                            break
                        if f2[3] < f1[2]:
                            continue
                        check_roof(f1, f2)

        conflicts_count = sum(len(s) for s in faces_to_offset.values())
        log(f"  Iteration {iteration}: Found {conflicts_count} candidate conflict faces.")
        if conflicts_count == 0:
            log("  All roof conflicts resolved!")
            break

        # Apply offset of 0.07m to candidate faces
        for oname, p_indices in faces_to_offset.items():
            obj = bpy.data.objects.get(oname)
            if obj and obj.data:
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bm.faces.ensure_lookup_table()
                target_faces = [bm.faces[i] for i in p_indices if i < len(bm.faces)]
                res = bmesh.ops.split(bm, geom=target_faces, use_only_faces=False)
                new_faces = [e for e in res["geom"] if isinstance(e, bmesh.types.BMFace)]
                verts_to_move = set(v for nf in new_faces for v in nf.verts)
                for v in verts_to_move:
                    v.co.z -= 0.07
                bm.to_mesh(obj.data)
                bm.free()

    # -------------------------------------------------------------------------
    # PART 3: RUN HEADLESS AUDIT SUITE
    # -------------------------------------------------------------------------
    log("\n" + "=" * 78)
    log("RUNNING AUDIT SUITE TO VERIFY 0 CONFLICTS...")
    log("=" * 78)
    auditor = MontrealZFightingAuditor(verbose=True)
    auditor.inspect_scene_inventory()
    r1 = auditor.audit_roof_cornice_zfighting()
    r2 = auditor.audit_ground_street_sidewalk_zfighting()
    r3 = auditor.audit_building_duplication()
    r4 = auditor.audit_street_network_presence()
    log(f"Criterion 1: {r1['passed']} (conflicts: {r1['conflict_groups']})")
    log(f"Criterion 2: {r2['passed']} (conflicts: {r2['conflict_groups']})")
    log(f"Criterion 3: {r3['passed']} (duplicates: {r3['duplicate_count']})")
    log(f"Criterion 4: {r4['passed']} (streets: {r4['passed_count']}/{r4['total_required']})")

if __name__ == "__main__":
    run_prototype()
