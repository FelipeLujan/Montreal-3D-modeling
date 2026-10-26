import bpy
import bmesh

obj = bpy.data.objects.get("Bldg_Remaining_Owned.001")
if obj:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    # Pick a face
    test_face = bm.faces[0]
    print("Test face:", test_face.index, "area:", test_face.calc_area())
    res = bmesh.ops.split(bm, geom=[test_face], use_only_faces=False)
    print("split res keys:", res.keys())
    print("split res geom types:", [type(e) for e in res["geom"]])
    bm.free()
