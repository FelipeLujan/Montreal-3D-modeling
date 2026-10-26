import bpy
import bmesh
import math
from collections import defaultdict

obj = bpy.data.objects.get("Bldg_Remaining_Owned.001")
me = obj.data
mw = obj.matrix_world
rot_3x3 = mw.to_3x3()
mats = [m.name if m else "None" for m in me.materials]

p60151 = me.polygons[60151]
print("p60151 z:", (mw @ p60151.center).z, "mat:", mats[p60151.material_index], "area:", p60151.area)
xs1 = [(mw @ me.vertices[vi].co).x for vi in p60151.vertices]
ys1 = [(mw @ me.vertices[vi].co).y for vi in p60151.vertices]
min_x1, max_x1 = min(xs1), max(xs1)
min_y1, max_y1 = min(ys1), max(ys1)

conflicts = []
for p in me.polygons:
    if p.index == 60151:
        continue
    wn = (rot_3x3 @ p.normal).normalized()
    if wn.z > 0.88 and p.area > 1.0:
        wc = mw @ p.center
        if abs(wc.z - (mw @ p60151.center).z) < 0.05:
            xs2 = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
            ys2 = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
            oy = min(max_y1, max(ys2)) - max(min_y1, min(ys2))
            if oy > 0:
                ox = min(max_x1, max(xs2)) - max(min_x1, min(xs2))
                if ox * oy > 1.0:
                    mat2 = mats[p.material_index] if p.material_index < len(mats) else "None"
                    if mat2 != mats[p60151.material_index]:
                        conflicts.append((p.index, mat2, wc.z, ox * oy))

print(f"Conflicts for 60151: {len(conflicts)}")
for c in conflicts[:10]:
    print("  Conflicting face:", c)
