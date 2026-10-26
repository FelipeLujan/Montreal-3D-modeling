import bpy
import bmesh
from mathutils import Vector
from collections import defaultdict
import math
import os
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")

print("=" * 80)
print("DECONFLICTING GROUND FACES")
print("=" * 80)

# 1. Peninsula_Ground_Quays_Park_And_Water
pen = bpy.data.objects.get("Peninsula_Ground_Quays_Park_And_Water")
if pen and pen.data:
    bm = bmesh.new()
    bm.from_mesh(pen.data)
    bm.faces.ensure_lookup_table()
    lowered_count = 0
    # Habitat 67 plaza: X in [940..1080], Y in [-750..-350]
    for f in bm.faces:
        c = f.calc_center_median()
        if 940 <= c.x <= 1080 and -750 <= c.y <= -350:
            if 0.04 <= c.z <= 0.08:
                for v in f.verts:
                    if v.co.z > 0.04:
                        v.co.z = 0.010
                lowered_count += 1
    print(f"Peninsula_Ground_Quays_Park_And_Water: lowered {lowered_count} faces under Habitat 67 plaza to Z=0.010m.")
    bm.to_mesh(pen.data)
    bm.free()
    pen.data.update()

# 2. Ground_District_Solid_Collider
col = bpy.data.objects.get("Ground_District_Solid_Collider")
if col and col.data:
    bm = bmesh.new()
    bm.from_mesh(col.data)
    bm.faces.ensure_lookup_table()
    lowered_col = 0
    for f in bm.faces:
        if f.normal.z > 0.88:
            c = f.calc_center_median()
            # Box overlapping Marina 23 and Plage de l'Horloge: X in [600..1050], Y in [-380..860]
            if 600 <= c.x <= 1050 and -380 <= c.y <= 860:
                if abs(c.z - (-0.120)) < 0.02:
                    for v in f.verts:
                        if abs(v.co.z - (-0.120)) < 0.02:
                            v.co.z = -0.180
                    lowered_col += 1
    print(f"Ground_District_Solid_Collider: lowered {lowered_col} top faces in East buffer to Z=-0.180m.")
    bm.to_mesh(col.data)
    bm.free()
    col.data.update()

# 3. Test Criterion 2 immediately in-memory
print("\n--- IN-MEMORY CRITERION 2 AUDIT ---")
EXCLUDED_OBJECT_KEYWORDS = (
    "tree", "jacaranda", "shrub", "statue", "lamp", "bench",
    "clock_bezel", "grate", "signage", "furniture", "bollard"
)

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
                ground_faces.append((
                    obj.name, wc.z, min(xs), max(xs), min(ys), max(ys),
                    mat_name, p.index, p.area
                ))

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
                            key = (o1, m1, f2[0], f2[6], round(z1, 2), round(f2[1], 2))
                            conflict_groups[key] = conflict_groups.get(key, 0) + 1

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
                                key = (o1, m1, f2[0], f2[6], round(z1, 2), round(f2[1], 2))
                                conflict_groups[key] = conflict_groups.get(key, 0) + 1

print(f"Criterion 2 In-Memory Result: {len(conflict_groups)} conflict groups ({total_collision_pairs} pairs)")
if conflict_groups:
    for k, cnt in conflict_groups.items():
        print(f"  [{cnt} pairs] {k[0]} [{k[1]}] (z={k[4]}) <==> {k[2]} [{k[3]}] (z={k[5]})")
else:
    print("CRITERION 2 PERFECT PASS: 0 CONFLICT GROUPS!")

if len(conflict_groups) == 0:
    master_blend = str(PROJECT_ROOT / "output" / "montreal_master.blend")
    tmp_blend = master_blend + ".tmp.blend"
    if os.path.exists(tmp_blend):
        try:
            os.remove(tmp_blend)
        except Exception:
            pass
    print("Saving updated master blend...")
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
    os.replace(tmp_blend, master_blend)
    print("SUCCESSFULLY SAVED output/montreal_master.blend!")
else:
    print("WARNING: Conflicts remain, NOT saving master blend yet.")
