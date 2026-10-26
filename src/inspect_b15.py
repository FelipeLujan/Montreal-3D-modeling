import bpy

obj = bpy.data.objects.get("Bldg_Remaining_Owned.001")
if obj:
    me = obj.data
    mw = obj.matrix_world
    mats = [m.name if m else "None" for m in me.materials]
    for p in me.polygons:
        mname = mats[p.material_index] if p.material_index < len(mats) else "None"
        if "roof" in mname.lower() or "membrane" in mname.lower():
            wc = mw @ p.center
            print(f"Roof face {p.index}: mat={mname}, z={wc.z:.4f}, normal.z={p.normal.z:.4f}, area={p.area:.2f}")
