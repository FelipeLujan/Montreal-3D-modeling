import sys
import os
sys.path.append(os.getcwd())
import bpy
import math
from collections import defaultdict
from src.audit_zfighting_headless import EXCLUDED_OBJECT_KEYWORDS

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
                roof_faces.append((
                    obj.name, wc.z, min(xs), max(xs), min(ys), max(ys),
                    mat_name, p.index, p.area
                ))

print(f"Total candidate roof faces: {len(roof_faces)}")

obj_face_counts = defaultdict(int)
for f in roof_faces:
    obj_face_counts[f[0]] += 1

print(f"Total objects with candidate faces: {len(obj_face_counts)}")
top_objs = sorted(obj_face_counts.items(), key=lambda x: -x[1])[:10]
print("Top objects with most candidate faces:")
for oname, cnt in top_objs:
    print(f"  {oname}: {cnt}")
