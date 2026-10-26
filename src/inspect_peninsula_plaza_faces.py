import bpy

pen = bpy.data.objects.get("Peninsula_Ground_Quays_Park_And_Water")
me = pen.data
mats = [m.name if m else "None" for m in me.materials]

plaza_faces = []
for p in me.polygons:
    mat = mats[p.material_index] if p.material_index < len(mats) else "None"
    if "plaza" in mat.lower() or "granite" in mat.lower():
        plaza_faces.append((p.index, mat, p.center, p.area, p.normal.z))

print(f"Total plaza/granite faces in Peninsula_Ground_Quays_Park_And_Water: {len(plaza_faces)}")
for idx, mat, c, area, nz in plaza_faces:
    print(f"  Face {idx:4d} | Mat: {mat:30s} | Center: ({c.x:7.2f}, {c.y:7.2f}, {c.z:6.3f}) | Area: {area:7.2f} | nz: {nz:.2f}")
