import bpy
import math
from collections import defaultdict

EXCLUDED_OBJECT_KEYWORDS = (
    "tree", "jacaranda", "shrub", "statue", "lamp", "bench",
    "clock_bezel", "grate", "signage", "furniture", "bollard"
)

visible_mesh_objs = [o for o in list(bpy.data.objects) if o is not None and o.type == "MESH" and o.data and not o.hide_render]
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

inter_obj_conflicts = defaultdict(int)

for b_idx, faces_a in buckets.items():
    len_a = len(faces_a)
    for i in range(len_a):
        f1 = faces_a[i]
        o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
        for j in range(i + 1, len_a):
            f2 = faces_a[j]
            if f2[2] > x1b:
                break
            if abs(z1 - f2[1]) < 0.05:
                oy = min(y1b, f2[5]) - max(y1a, f2[4])
                if oy > 0.0:
                    ox = min(x1b, f2[3]) - f2[2]
                    if ox * oy > 1.0:
                        if o1 != f2[0]:
                            key = tuple(sorted([o1, f2[0]]))
                            inter_obj_conflicts[key] += 1

    if (b_idx + 1) in buckets:
        faces_b = buckets[b_idx + 1]
        for f1 in faces_a:
            o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
            for f2 in faces_b:
                if f2[2] > x1b:
                    break
                if f2[3] < x1a:
                    continue
                if abs(z1 - f2[1]) < 0.05:
                    oy = min(y1b, f2[5]) - max(y1a, f2[4])
                    if oy > 0.0:
                        ox = min(x1b, f2[3]) - max(x1a, f2[2])
                        if ox * oy > 1.0:
                            if o1 != f2[0]:
                                key = tuple(sorted([o1, f2[0]]))
                                inter_obj_conflicts[key] += 1

print(f"\nUnique inter-object conflict pairs: {len(inter_obj_conflicts)}")
for pair, cnt in sorted(inter_obj_conflicts.items(), key=lambda x: -x[1])[:30]:
    o1 = bpy.data.objects.get(pair[0])
    o2 = bpy.data.objects.get(pair[1])
    c1 = [c.name for c in o1.users_collection] if o1 else []
    c2 = [c.name for c in o2.users_collection] if o2 else []
    print(f"  [{cnt:3d} pairs] {pair[0]} ({c1}) <==> {pair[1]} ({c2})")
