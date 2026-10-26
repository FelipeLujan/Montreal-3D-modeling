import bpy

b21 = bpy.data.objects.get("MTL_Owned_Ground_Quays_And_Water_MTL-VM-0021")
pen = bpy.data.objects.get("Peninsula_Ground_Quays_Park_And_Water")

mats21 = [m.name if m else "" for m in b21.data.materials]
mats_pen = [m.name if m else "" for m in pen.data.materials]

b21_faces = []
for p in b21.data.polygons:
    mat = mats21[p.material_index] if p.material_index < len(mats21) else ""
    if "railing" in mat.lower() and abs(p.center.z - (-0.05)) < 0.02 and p.area > 0.05:
        b21_faces.append((p.index, mat, p.center, p.area))

pen_faces = []
for p in pen.data.polygons:
    mat = mats_pen[p.material_index] if p.material_index < len(mats_pen) else ""
    if "pierregrise" in mat.lower() and abs(p.center.z - (-0.05)) < 0.02 and p.area > 0.05:
        pen_faces.append((p.index, mat, p.center, p.area))

print(f"B21 railing candidates: {len(b21_faces)}")
print(f"Peninsula pierregrise candidates: {len(pen_faces)}")

for idx1, m1, c1, a1 in b21_faces:
    for idx2, m2, c2, a2 in pen_faces:
        if (c1 - c2).length < 50.0:
            print(f"Conflict candidate: B21 face {idx1} (c={c1}) vs Pen face {idx2} (c={c2})")
