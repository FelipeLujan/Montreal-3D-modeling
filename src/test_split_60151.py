import bpy
import bmesh

obj = bpy.data.objects.get("Bldg_Remaining_Owned.001")
bm = bmesh.new()
bm.from_mesh(obj.data)
bm.faces.ensure_lookup_table()

f = bm.faces[60151]
print("Before: f center z:", f.calc_center_median().z)

# Test 1: split
res = bmesh.ops.split(bm, geom=[f], use_only_faces=False)
new_faces = [e for e in res["geom"] if isinstance(e, bmesh.types.BMFace)]
print("New faces count:", len(new_faces))
for nf in new_faces:
    for v in nf.verts:
        v.co.z -= 0.12

print("After in bmesh: f center z:", f.calc_center_median().z)
if new_faces:
    print("After in bmesh: nf center z:", new_faces[0].calc_center_median().z)

bm.free()
