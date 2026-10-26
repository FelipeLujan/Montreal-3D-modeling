import bpy
import bmesh
from mathutils import Vector
import os
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")

print("=" * 80)
print("EXECUTING CLEAN FINAL MASTER SOLVE")
print("=" * 80)

# 1. Delete legacy shallow water faces (Z > -1.0m) from Blocks 21, 23, 24, 35, 36
water_objects = [
    "MTL_Owned_Ground_Quays_And_Water_MTL-VM-0021",
    "MTL_Owned_Quays_And_Marina_MTL-VM-0023",
    "MTL_VM_0024_BasinAndBoardwalks",
    "Peninsula_Ground_Quays_Park_And_Water",
    "Ground_Quays_Water_MTL-VM-0036"
]

for obj_name in water_objects:
    obj = bpy.data.objects.get(obj_name)
    if obj and obj.data:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        mats = [m.name if m else "" for m in obj.data.materials]
        to_del = []
        for f in bm.faces:
            mat_name = mats[f.material_index] if f.material_index < len(mats) else ""
            if any(w in mat_name.lower() for w in ("water", "basin")):
                if f.calc_center_median().z > -1.0:
                    to_del.append(f)
        if to_del:
            print(f"  {obj_name}: deleting {len(to_del)} shallow water faces (Z > -1.0m).")
            bmesh.ops.delete(bm, geom=to_del, context="FACES")
            bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

# 2. Fix Block 21 Safety Railing bottom elevation
b21 = bpy.data.objects.get("MTL_Owned_Ground_Quays_And_Water_MTL-VM-0021")
if b21 and b21.data:
    bm = bmesh.new()
    bm.from_mesh(b21.data)
    bm.faces.ensure_lookup_table()
    mats = [m.name if m else "" for m in b21.data.materials]
    elevated_count = 0
    for f in bm.faces:
        mat_name = mats[f.material_index] if f.material_index < len(mats) else ""
        if "railing" in mat_name.lower():
            for v in f.verts:
                if abs(v.co.z - (-0.050)) < 0.02:
                    v.co.z = -0.010
                    elevated_count += 1
    print(f"  MTL_Owned_Ground_Quays_And_Water_MTL-VM-0021: elevated {elevated_count} railing vertices from -0.05m to -0.01m.")
    bm.to_mesh(b21.data)
    bm.free()
    b21.data.update()

# 3. Fix Vieux Palais spike vertex and inset roof faces
vp = bpy.data.objects.get("MTL_Owned_20919178_Vieux_Palais_de_Justice")
if vp and vp.data:
    me = vp.data
    mw = vp.matrix_world
    bb = [mw @ Vector(c) for c in vp.bound_box]
    min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
    height = max_z - min_z
    
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    for v in bm.verts:
        if abs(v.co.x - 78.2011) < 0.2 and abs(v.co.y - 305.1005) < 0.2:
            v.co.x = 95.892
            v.co.y = 337.251
            print("  Vieux Palais: snapped spike vertex.")
            break
    
    to_inset = [f for f in bm.faces if f.normal.z > 0.95 and f.calc_area() > 0.2 and (mw @ f.calc_center_median()).z >= min_z + 0.40 * height]
    print(f"  Vieux Palais: insetting {len(to_inset)} roof faces.")
    if to_inset:
        bmesh.ops.inset_individual(bm, faces=to_inset, thickness=0.20, depth=-0.12, use_even_offset=True)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()

# 4. Ground_District_Solid_Collider: orient bottom faces -Z, top faces +Z
col = bpy.data.objects.get("Ground_District_Solid_Collider")
if col and col.data:
    me = col.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    
    flipped = 0
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(f.normal.z) > 0.88:
            is_bottom = (abs(c.z - (-0.280)) < 0.02 or abs(c.z - (-0.350)) < 0.02 or 
                         abs(c.z - (-2.750)) < 0.02 or abs(c.z - (-3.500)) < 0.02)
            if is_bottom and f.normal.z > 0:
                f.normal_flip()
                flipped += 1
    
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()
    print(f"  Ground_District_Solid_Collider: flipped {flipped} bottom faces to point -Z.")

# Save master blend atomically
master_blend = str(PROJECT_ROOT / "output" / "montreal_master.blend")
tmp_blend = master_blend + ".tmp.blend"
if os.path.exists(tmp_blend):
    try: os.remove(tmp_blend)
    except Exception: pass

print("Saving master blend...")
bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
os.replace(tmp_blend, master_blend)
print("SUCCESSFULLY SAVED output/montreal_master.blend!")
