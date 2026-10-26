import bpy

pen = bpy.data.objects.get("Peninsula_Ground_Quays_Park_And_Water")
me = pen.data
indices = [2213, 2263, 2839, 2248, 2253]

for idx in indices:
    p = me.polygons[idx]
    mat = me.materials[p.material_index].name if p.material_index < len(me.materials) else "None"
    print(f"\nFace {idx}: mat={mat}, area={p.area:.2f}, normal={p.normal}, center={p.center}")
    for vi in p.vertices:
        v = me.vertices[vi]
        print(f"  v[{vi}]: ({v.co.x:.2f}, {v.co.y:.2f}, {v.co.z:.3f})")
