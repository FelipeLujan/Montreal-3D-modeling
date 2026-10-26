import bpy

pen = bpy.data.objects.get("Peninsula_Ground_Quays_Park_And_Water")
me = pen.data
mats = [m.name if m else "None" for m in me.materials]

print(f"Peninsula materials: {mats}")
habitat_faces = []
for p in me.polygons:
    c = p.center
    if 940 <= c.x <= 1080 and -750 <= c.y <= -350:
        mat = mats[p.material_index] if p.material_index < len(mats) else "None"
        habitat_faces.append((p.index, mat, c, p.area, p.normal.z))

print(f"Total faces in Peninsula around Habitat 67: {len(habitat_faces)}")
for idx, mat, c, area, nz in habitat_faces:
    print(f"  Face {idx:4d} | Mat: {mat:30s} | Center: ({c.x:7.2f}, {c.y:7.2f}, {c.z:6.3f}) | Area: {area:7.2f} | nz: {nz:.2f}")
