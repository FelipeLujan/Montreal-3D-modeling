import bpy

print("=" * 80)
print("FINDING ALL SHALLOW WATER FACES ACROSS ALL OBJECTS")
print("=" * 80)

total_shallow = 0
for obj in bpy.data.objects:
    if obj.type != "MESH" or not obj.data or obj.hide_render:
        continue
    if obj.name == "Water_District_StLawrence_And_Canals":
        continue
    mats = [m.name if m else "" for m in obj.data.materials]
    shallow_in_obj = 0
    for p in obj.data.polygons:
        mat = mats[p.material_index] if p.material_index < len(mats) else ""
        if any(w in mat.lower() for w in ("water", "basin")):
            if p.center.z > -1.0:
                shallow_in_obj += 1
    if shallow_in_obj > 0:
        print(f"  {obj.name}: {shallow_in_obj} shallow water faces (Z > -1.0m)")
        total_shallow += shallow_in_obj

print(f"Total shallow water faces found: {total_shallow}")
