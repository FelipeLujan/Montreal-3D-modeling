import bpy

m23 = bpy.data.objects.get("MTL_Owned_Quays_And_Marina_MTL-VM-0023")
mats = [m.name if m else "" for m in m23.data.materials]

near_faces = []
for p in m23.data.polygons:
    c = p.center
    if 400 <= c.x <= 620 and 50 <= c.y <= 250:
        mat = mats[p.material_index] if p.material_index < len(mats) else ""
        near_faces.append((p.index, mat, c, p.area, p.normal.z))

print(f"Marina 23 faces near (510, 150): {len(near_faces)}")
for idx, mat, c, area, nz in near_faces[:15]:
    print(f"  Face {idx}: mat={mat}, center=({c.x:.2f}, {c.y:.2f}, {c.z:.3f}), area={area:.2f}, nz={nz:.2f}")
