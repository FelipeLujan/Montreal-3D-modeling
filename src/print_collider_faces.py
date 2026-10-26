import bpy

col = bpy.data.objects.get("Ground_District_Solid_Collider")
me = col.data

print(f"Total polygons in collider: {len(me.polygons)}")
for p in me.polygons:
    print(f"Face {p.index:2d}: norm=({p.normal.x:4.2f}, {p.normal.y:4.2f}, {p.normal.z:4.2f}), center=({p.center.x:7.1f}, {p.center.y:7.1f}, {p.center.z:6.3f}), area={p.area:.1f}")
