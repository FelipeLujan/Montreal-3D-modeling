import bpy

col = bpy.data.objects.get("Ground_District_Solid_Collider")
me = col.data
mw = col.matrix_world
rot_3x3 = mw.to_3x3()

top_faces = []
bottom_faces = []
side_faces = []

for p in me.polygons:
    wn = (rot_3x3 @ p.normal).normalized()
    wc = mw @ p.center
    if wn.z > 0.88:
        top_faces.append((p.index, wc, wn))
    elif wn.z < -0.88:
        bottom_faces.append((p.index, wc, wn))
    else:
        side_faces.append((p.index, wc, wn))

print(f"Top faces: {len(top_faces)}")
print(f"Bottom faces: {len(bottom_faces)}")
print(f"Side faces: {len(side_faces)}")
