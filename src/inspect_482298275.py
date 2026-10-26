import bpy

obj = bpy.data.objects.get("Bldg_482298275")
if obj:
    me = obj.data
    mw = obj.matrix_world
    mats = [m.name if m else "None" for m in me.materials]
    rot_3x3 = mw.to_3x3()
    print("Bldg_482298275 polygons around z=11.04:")
    for p in me.polygons:
        wn = (rot_3x3 @ p.normal).normalized()
        wc = mw @ p.center
        if wn.z > 0.88 and p.area > 1.0 and abs(wc.z - 11.04) < 0.15:
            mat = mats[p.material_index] if p.material_index < len(mats) else "None"
            print(f"  p[{p.index}]: z={wc.z:.4f}, mat={mat}, area={p.area:.2f}")
