import bpy
import bmesh
from mathutils import Vector
from collections import defaultdict
import math

# Apply the same logic as test_and_apply_ground_fix
pen = bpy.data.objects.get("Peninsula_Ground_Quays_Park_And_Water")
if pen and pen.data:
    bm = bmesh.new()
    bm.from_mesh(pen.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        c = f.calc_center_median()
        if 940 <= c.x <= 1080 and -750 <= c.y <= -350:
            if 0.04 <= c.z <= 0.08:
                for v in f.verts:
                    if v.co.z > 0.04:
                        v.co.z = 0.010
    bm.to_mesh(pen.data)
    bm.free()
    pen.data.update()

col = bpy.data.objects.get("Ground_District_Solid_Collider")
if col and col.data:
    bm = bmesh.new()
    bm.from_mesh(col.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        if f.normal.z > 0.88:
            c = f.calc_center_median()
            if 600 <= c.x <= 1050 and -380 <= c.y <= 860:
                if abs(c.z - (-0.120)) < 0.02:
                    for v in f.verts:
                        if abs(v.co.z - (-0.120)) < 0.02:
                            v.co.z = -0.180
    bm.to_mesh(col.data)
    bm.free()
    col.data.update()

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
                    mat_name, p.index, p.area, wc.x, wc.y
                ))

BUCKET_DZ = 0.02
buckets = defaultdict(list)
for f in ground_faces:
    b_idx = int(math.floor(f[1] / BUCKET_DZ))
    buckets[b_idx].append(f)

for b_idx in buckets:
    buckets[b_idx].sort(key=lambda f: f[2])

print("\nREMAINING CONFLICTS IN DETAIL:")
for b_idx, faces_a in buckets.items():
    len_a = len(faces_a)
    for i in range(len_a):
        f1 = faces_a[i]
        for j in range(i + 1, len_a):
            f2 = faces_a[j]
            if f2[2] > f1[3]:
                break
            if abs(f1[1] - f2[1]) < 0.02:
                oy = min(f1[5], f2[5]) - max(f1[4], f2[4])
                if oy > 0.0:
                    ox = min(f1[3], f2[3]) - f2[2]
                    if ox * oy > 2.0:
                        if f1[0] != f2[0] or f1[6] != f2[6]:
                            print(f"\nConflict (same bucket {b_idx}):")
                            print(f"  F1: {f1[0]} | mat={f1[6]} | idx={f1[7]} | z={f1[1]:.3f} | center=({f1[9]:.2f}, {f1[10]:.2f}) | bbox=[{f1[2]:.2f}..{f1[3]:.2f}, {f1[4]:.2f}..{f1[5]:.2f}]")
                            print(f"  F2: {f2[0]} | mat={f2[6]} | idx={f2[7]} | z={f2[1]:.3f} | center=({f2[9]:.2f}, {f2[10]:.2f}) | bbox=[{f2[2]:.2f}..{f2[3]:.2f}, {f2[4]:.2f}..{f2[5]:.2f}]")
                            print(f"  overlap={ox*oy:.2f} m2, dz={abs(f1[1]-f2[1]):.4f}")

    if (b_idx + 1) in buckets:
        faces_b = buckets[b_idx + 1]
        for f1 in faces_a:
            for f2 in faces_b:
                if f2[2] > f1[3]:
                    break
                if f2[3] < f1[2]:
                    continue
                if abs(f1[1] - f2[1]) < 0.02:
                    oy = min(f1[5], f2[5]) - max(f1[4], f2[4])
                    if oy > 0.0:
                        ox = min(f1[3], f2[3]) - max(f1[2], f2[2])
                        if ox * oy > 2.0:
                            if f1[0] != f2[0] or f1[6] != f2[6]:
                                print(f"\nConflict (adjacent buckets {b_idx} & {b_idx+1}):")
                                print(f"  F1: {f1[0]} | mat={f1[6]} | idx={f1[7]} | z={f1[1]:.3f} | center=({f1[9]:.2f}, {f1[10]:.2f}) | bbox=[{f1[2]:.2f}..{f1[3]:.2f}, {f1[4]:.2f}..{f1[5]:.2f}]")
                                print(f"  F2: {f2[0]} | mat={f2[6]} | idx={f2[7]} | z={f2[1]:.3f} | center=({f2[9]:.2f}, {f2[10]:.2f}) | bbox=[{f2[2]:.2f}..{f2[3]:.2f}, {f2[4]:.2f}..{f2[5]:.2f}]")
                                print(f"  overlap={ox*oy:.2f} m2, dz={abs(f1[1]-f2[1]):.4f}")
