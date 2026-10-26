import bpy

b21 = bpy.data.objects.get("MTL_Owned_Ground_Quays_And_Water_MTL-VM-0021")
me = b21.data
mats = [m.name if m else "" for m in me.materials]

for p in me.polygons:
    mat = mats[p.material_index] if p.material_index < len(mats) else ""
    if "railing" in mat.lower():
        print(f"Face {p.index}: mat={mat}, center={p.center}, area={p.area:.2f}, normal={p.normal}")
        for vi in p.vertices:
            v = me.vertices[vi]
            print(f"   v[{vi}]: ({v.co.x:.2f}, {v.co.y:.2f}, {v.co.z:.3f})")
