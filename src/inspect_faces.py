import bpy

obj = bpy.data.objects.get("Bldg_Remaining_Owned.001")
me = obj.data
mw = obj.matrix_world
for f_idx in [6, 240, 60151]:
    p = me.polygons[f_idx]
    mat = me.materials[p.material_index].name if p.material_index < len(me.materials) else "None"
    verts = [mw @ me.vertices[vi].co for vi in p.vertices]
    print(f"Face {f_idx}: mat={mat}, area={p.area:.2f}, normal={p.normal}, z={p.center.z:.4f}")
    print("  Verts count:", len(verts))
    for v in verts[:4]:
        print(f"    v: ({v.x:.2f}, {v.y:.2f}, {v.z:.2f})")
