import bpy

# 1. Inspect MTL_VM_0024_BasinAndBoardwalks
b24 = bpy.data.objects.get("MTL_VM_0024_BasinAndBoardwalks")
if b24:
    mats = [m.name if m else "" for m in b24.data.materials]
    water_faces = []
    for p in b24.data.polygons:
        mat = mats[p.material_index] if p.material_index < len(mats) else ""
        if "water" in mat.lower() or "basin" in mat.lower():
            if p.center.z > -1.0:
                water_faces.append((p.index, mat, p.center, p.area))
    print(f"Block 24 shallow water/basin faces: {len(water_faces)}")
    for f in water_faces[:10]:
        print(f"  Face {f[0]}: mat={f[1]}, center={f[2]}, area={f[3]:.2f}")

# 2. Inspect Block 21 Safety Railing faces at z=-0.05
b21 = bpy.data.objects.get("MTL_Owned_Ground_Quays_And_Water_MTL-VM-0021")
if b21:
    mats = [m.name if m else "" for m in b21.data.materials]
    railing_faces = []
    for p in b21.data.polygons:
        mat = mats[p.material_index] if p.material_index < len(mats) else ""
        if "railing" in mat.lower() or abs(p.center.z - (-0.05)) < 0.02:
            railing_faces.append((p.index, mat, p.center, p.area))
    print(f"\nBlock 21 railing/z=-0.05 faces: {len(railing_faces)}")
    for f in railing_faces[:10]:
        print(f"  Face {f[0]}: mat={f[1]}, center={f[2]}, area={f[3]:.2f}")
