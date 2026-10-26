import bpy
import sys
from collections import defaultdict
import math

# Load audit logic to find the exact faces
visible_mesh_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]

candidate_faces = []
for obj in visible_mesh_objs:
    nl = obj.name.lower()
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
                candidate_faces.append((
                    obj.name, wc.z, min(xs), max(xs), min(ys), max(ys),
                    mat_name, p.index, p.area, wc.x, wc.y
                ))

BUCKET_DZ = 0.02
buckets = defaultdict(list)
for f in candidate_faces:
    b_idx = int(math.floor(f[1] / BUCKET_DZ))
    buckets[b_idx].append(f)

for b_idx in buckets:
    buckets[b_idx].sort(key=lambda f: f[2])

print("FINDING EXACT CONFLICTING PAIRS:")
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
                            print(f"\nConflict:")
                            print(f"  Obj1: {f1[0]} (mat: {f1[6]}, poly_idx: {f1[7]}, center: ({f1[9]:.2f}, {f1[10]:.2f}, {f1[1]:.3f}), bbox: [{f1[2]:.2f}..{f1[3]:.2f}, {f1[4]:.2f}..{f1[5]:.2f}])")
                            print(f"  Obj2: {f2[0]} (mat: {f2[6]}, poly_idx: {f2[7]}, center: ({f2[9]:.2f}, {f2[10]:.2f}, {f2[1]:.3f}), bbox: [{f2[2]:.2f}..{f2[3]:.2f}, {f2[4]:.2f}..{f2[5]:.2f}])")
                            print(f"  Overlap area: {ox*oy:.2f} m2, dz: {abs(f1[1]-f2[1]):.4f}")

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
                                print(f"\nConflict across buckets:")
                                print(f"  Obj1: {f1[0]} (mat: {f1[6]}, poly_idx: {f1[7]}, center: ({f1[9]:.2f}, {f1[10]:.2f}, {f1[1]:.3f}), bbox: [{f1[2]:.2f}..{f1[3]:.2f}, {f1[4]:.2f}..{f1[5]:.2f}])")
                                print(f"  Obj2: {f2[0]} (mat: {f2[6]}, poly_idx: {f2[7]}, center: ({f2[9]:.2f}, {f2[10]:.2f}, {f2[1]:.3f}), bbox: [{f2[2]:.2f}..{f2[3]:.2f}, {f2[4]:.2f}..{f2[5]:.2f}])")
                                print(f"  Overlap area: {ox*oy:.2f} m2, dz: {abs(f1[1]-f2[1]):.4f}")
