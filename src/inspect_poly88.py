import bpy

col = bpy.data.objects.get("Ground_District_Solid_Collider")
me = col.data
poly = me.polygons[88]
print(f"Poly 88: center={poly.center}, normal={poly.normal}, area={poly.area}")
for vi in poly.vertices:
    v = me.vertices[vi]
    print(f"  v[{vi}]: ({v.co.x:.2f}, {v.co.y:.2f}, {v.co.z:.3f})")
