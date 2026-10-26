import sys
from pathlib import Path
import json, unicodedata, math
import bpy
import bmesh
from mathutils import Vector

visible_meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]
bldg_objs = [
    o for o in visible_meshes
    if not any(k in o.name.lower() for k in ("street", "road", "curb", "sidewalk", "asphalt", "cobble", "plaza", "tree", "lamp", "bench", "grate", "sign"))
]
bldg_bboxes = []
for b in bldg_objs:
    bb = [b.matrix_world @ Vector(c) for c in b.bound_box]
    min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
    min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)
    min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
    if max_z > 3.0 and (max_x - min_x) > 3.0 and (max_y - min_y) > 3.0:
        bldg_bboxes.append((b.name, min_x, max_x, min_y, max_y))

cur_sw = bpy.data.objects.get("District_Sidewalks_Raised")
if cur_sw:
    me = cur_sw.data
    mw = cur_sw.matrix_world
    del_faces = []
    for p in me.polygons:
        wc = mw @ p.center
        for bname, bx1, bx2, by1, by2 in bldg_bboxes:
            if bx1 + 0.4 <= wc.x <= bx2 - 0.4 and by1 + 0.4 <= wc.y <= by2 - 0.4:
                del_faces.append(p.index)
                break
    print(f"Total sidewalk faces: {len(me.polygons)}, Faces inside buildings to delete: {len(del_faces)}")

    # If deleted in BMesh:
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    to_del = [bm.faces[i] for i in del_faces]
    bmesh.ops.delete(bm, geom=to_del, context="FACES")
    bm.to_mesh(me)
    bm.free()

    # Re-check penetrations
    penetrated = set()
    for p in me.polygons:
        wc = mw @ p.center
        for bname, bx1, bx2, by1, by2 in bldg_bboxes:
            if bx1 + 0.5 <= wc.x <= bx2 - 0.5 and by1 + 0.5 <= wc.y <= by2 - 0.5:
                penetrated.add(bname)
    print(f"Remaining penetrations after deletion: {len(penetrated)}")
