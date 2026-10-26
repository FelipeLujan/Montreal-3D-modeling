"""
src/test_stratum_deconflict.py
Graph Coloring / Stratum Assignment deconfliction test.
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

log = lambda *args: print(*args, flush=True)

def test_stratum():
    log("=== STARTING STRATUM-BASED DECONFLICTION ===")
    t0 = time.time()

    # -------------------------------------------------------------------------
    # 1. GROUND DECONFLICTION (CRITERION 2)
    # -------------------------------------------------------------------------
    log("\n[1/3] Resolving Ground Conflicts...")
    
    # Curb top to Z = +0.180m
    curbs = bpy.data.objects.get("District_Curbs_3D")
    if curbs and curbs.data:
        for v in curbs.data.vertices:
            if v.co.z > 0.10:
                v.co.z = 0.180
        log("  Set District_Curbs_3D top to Z = +0.180m.")

    # Remove building ground-level bottom caps / window glass faces
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data or obj.hide_render:
            continue
        nl = obj.name.lower()
        if any(k in nl for k in ["district_", "street", "road", "plaza", "tree", "lamp", "bench"]):
            continue
        me = obj.data
        mw = obj.matrix_world
        rot_3x3 = mw.to_3x3()
        mats = [m.name if m else "None" for m in me.materials]
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

    # Collect ground faces
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
                        if "district_sidewalk" in o1.lower() or "district_curb" in o1.lower():
                            ground_del_faces[o1].add(idx1)
                        elif "district_sidewalk" in o2.lower() or "district_curb" in o2.lower():
                            ground_del_faces[o2].add(idx2)
                        elif "plaza" in o1.lower() and "plaza" not in o2.lower():
                            ground_del_faces[o2].add(idx2)
                        elif "plaza" in o2.lower() and "plaza" not in o1.lower():
                            ground_del_faces[o1].add(idx1)
                        else:
                            # Break symmetry strictly by sorting object name and index
                            if (o1, idx1) < (o2, idx2):
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

    log("  Ground deconfliction finished.")

    # -------------------------------------------------------------------------
    # 2. ROOF & CORNICE DECONFLICTION (CRITERION 1)
    # -------------------------------------------------------------------------
    log("\n[2/3] Resolving Roof & Cornice Conflicts via Stratum Assignment...")

    # Pass 1: Remove horizontal glass/frame caps at Z > 3.0m
    glass_caps = 0
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
            glass_caps += len(to_del)
    log(f"  Removed {glass_caps} horizontal window glass/frame caps.")

    # Pass 2: Stratum coloring on conflict graph
    # Collect all candidate roof faces
    visible_mesh_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]
    roof_faces = []
    face_key_to_id = {}
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
                    fid = len(roof_faces)
                    f_entry = (obj.name, wc.z, min(xs), max(xs), min(ys), max(ys), mat_name, p.index, p.area)
                    roof_faces.append(f_entry)
                    face_key_to_id[(obj.name, p.index)] = fid

    log(f"  Collected {len(roof_faces)} candidate roof faces.")

    BUCKET_DZ = 0.05
    buckets = defaultdict(list)
    for f in roof_faces:
        buckets[int(math.floor(f[1] / BUCKET_DZ))].append(f)
    for b_idx in buckets:
        buckets[b_idx].sort(key=lambda f: f[2])

    # Build adjacency graph of conflicts
    adj = defaultdict(set)

    def check_roof_adj(f1, f2):
        o1, z1, x1a, x1b, y1a, y1b, m1, idx1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6], f1[7]
        o2, z2, x2a, x2b, y2a, y2b, m2, idx2 = f2[0], f2[1], f2[2], f2[3], f2[4], f2[5], f2[6], f2[7]
        if abs(z1 - z2) < 0.05:
            oy = min(y1b, y2b) - max(y1a, y2a)
            if oy > 0.0:
                ox = min(x1b, f2[3]) - f2[2]
                if ox * oy > 1.0:
                    if o1 != o2 or m1 != m2:
                        id1 = face_key_to_id[(o1, idx1)]
                        id2 = face_key_to_id[(o2, idx2)]
                        adj[id1].add(id2)
                        adj[id2].add(id1)

    for b_idx, faces_a in buckets.items():
        len_a = len(faces_a)
        for i in range(len_a):
            f1 = faces_a[i]
            for j in range(i + 1, len_a):
                if faces_a[j][2] > f1[3]:
                    break
                check_roof_adj(f1, faces_a[j])
        if (b_idx + 1) in buckets:
            for f1 in faces_a:
                for f2 in buckets[b_idx + 1]:
                    if f2[2] > f1[3]:
                        break
                    if f2[3] < f1[2]:
                        continue
                    check_roof_adj(f1, f2)

    log(f"  Conflict graph has {len(adj)} nodes with conflicts.")

    # Greedy Graph Coloring:
    # Color 0: offset = 0.00m (keeps original position)
    # Color 1: offset = -0.06m
    # Color 2: offset = -0.12m
    # Color 3: offset = -0.18m
    # Since max degree in practice is small, colors will be 0, 1, 2, 3...
    colors = {}
    # Sort nodes by degree descending (Welsh-Powell heuristic for minimum colors)
    sorted_nodes = sorted(adj.keys(), key=lambda node: len(adj[node]), reverse=True)
    for node in sorted_nodes:
        neighbor_colors = {colors[nbr] for nbr in adj[node] if nbr in colors}
        c = 0
        while c in neighbor_colors:
            c += 1
        colors[node] = c

    # Group faces by object and color
    # Color 0 does NOT move! Only color > 0 moves: v.co.z -= color * 0.06m
    obj_color_faces = defaultdict(lambda: defaultdict(list))
    for node, c in colors.items():
        if c > 0:
            f = roof_faces[node]
            oname, p_idx = f[0], f[7]
            obj_color_faces[oname][c].append(p_idx)

    log(f"  Stratum coloring assigned: {len(colors)} faces colored across {len(obj_color_faces)} objects.")

    # Apply stratum offsets per object, iterating strictly by color group
    for oname, color_map in obj_color_faces.items():
        obj = bpy.data.objects.get(oname)
        if not obj or not obj.data:
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        # Iterate through colors 1, 2, 3...
        # For each color, split its exact target faces and offset them by c * 0.06m
        for c in sorted(color_map.keys()):
            indices = color_map[c]
            target_faces = [bm.faces[i] for i in indices if i < len(bm.faces)]
            if not target_faces:
                continue
            res = bmesh.ops.split(bm, geom=target_faces, use_only_faces=False)
            new_faces = [e for e in res["geom"] if isinstance(e, bmesh.types.BMFace)]
            verts_to_move = set(v for nf in new_faces for v in nf.verts)
            offset = c * 0.06
            for v in verts_to_move:
                v.co.z -= offset
            bm.faces.ensure_lookup_table()

        bm.to_mesh(obj.data)
        bm.free()

    log("  Stratum offsets applied.")

    # -------------------------------------------------------------------------
    # 3. RUN AUDIT TO VERIFY
    # -------------------------------------------------------------------------
    log("\n[3/3] Running Headless Audit Suite...")
    auditor = MontrealZFightingAuditor(verbose=True)
    auditor.inspect_scene_inventory()
    r1 = auditor.audit_roof_cornice_zfighting()
    r2 = auditor.audit_ground_street_sidewalk_zfighting()
    r3 = auditor.audit_building_duplication()
    r4 = auditor.audit_street_presence()

    log("\n" + "=" * 78)
    log(f"FINAL AUDIT RESULT:")
    log(f"  Criterion 1 (Roof):   {r1['passed']} (Conflicts: {r1['conflict_groups']})")
    log(f"  Criterion 2 (Ground): {r2['passed']} (Conflicts: {r2['conflict_groups']})")
    log(f"  Criterion 3 (Dups):   {r3['passed']} (Duplicates: {r3['duplicate_count']})")
    log(f"  Criterion 4 (Street): {r4['passed']} (Streets: {r4['passed_count']}/{r4['total_required']})")
    log("=" * 78)

if __name__ == "__main__":
    test_stratum()
