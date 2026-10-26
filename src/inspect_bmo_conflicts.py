import bpy
import bmesh
from collections import defaultdict
import math

obj = bpy.data.objects.get("Bldg_102127873_BMO_Stepped_Tower")
me = obj.data
mw = obj.matrix_world
rot_3x3 = mw.to_3x3()
mats = [m.name if m else "None" for m in me.materials]

candidate_faces = []
for p in me.polygons:
    wn = (rot_3x3 @ p.normal).normalized()
    if wn.z > 0.88 and p.area > 1.0:
        wc = mw @ p.center
        if wc.z > 3.0:
            mat = mats[p.material_index] if p.material_index < len(mats) else "None"
            xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
            ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
            candidate_faces.append((p.index, wc.z, min(xs), max(xs), min(ys), max(ys), mat, p.area))

print(f"BMO candidate roof faces: {len(candidate_faces)}")

# Check internal conflicts in BMO
conflicts = []
for i in range(len(candidate_faces)):
    f1 = candidate_faces[i]
    for j in range(i + 1, len(candidate_faces)):
        f2 = candidate_faces[j]
        if abs(f1[1] - f2[1]) < 0.05:
            oy = min(f1[5], f2[5]) - max(f1[4], f2[4])
            if oy > 0:
                ox = min(f1[3], f2[3]) - max(f1[2], f2[2])
                if ox * oy > 1.0:
                    if f1[6] != f2[6]:
                        conflicts.append((f1, f2, ox * oy))

print(f"BMO internal conflict pairs: {len(conflicts)}")
for c in conflicts[:10]:
    f1, f2, area = c
    print(f"  Conflict: p[{f1[0]}] ({f1[6]}, z={f1[1]:.2f}) vs p[{f2[0]}] ({f2[6]}, z={f2[2]:.2f}), overlap={area:.2f}")
