import bpy
import bmesh
from mathutils import Vector
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
sys.path.insert(0, str(PROJECT_ROOT))
from src.audit_zfighting_headless import MontrealZFightingAuditor

def check_c2(label):
    aud = MontrealZFightingAuditor()
    aud.verbose = True
    aud.inspect_scene_inventory()
    res = aud.audit_ground_street_sidewalk_zfighting()
    print(f"\n>>> C2 STATUS after '{label}': {res['conflict_groups']} groups ({res['collision_pairs']} pairs) <<<\n")
    return res['conflict_groups']

print("--- Step 0: Baseline on master blend ---")
check_c2("Baseline")

# Step 1: Water deletion
print("\n--- Testing Step 1: Deleting shallow water faces ---")
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
            print(f"  {obj_name}: deleting {len(to_del)} faces.")
            bmesh.ops.delete(bm, geom=to_del, context="FACES")
            bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

check_c2("Step 1 (Water Deletion)")

# Step 2: Elevate railing vertices
print("\n--- Testing Step 2: Elevating B21 railing vertices ---")
b21 = bpy.data.objects.get("MTL_Owned_Ground_Quays_And_Water_MTL-VM-0021")
if b21 and b21.data:
    bm = bmesh.new()
    bm.from_mesh(b21.data)
    bm.faces.ensure_lookup_table()
    mats = [m.name if m else "" for m in b21.data.materials]
    for f in bm.faces:
        mat_name = mats[f.material_index] if f.material_index < len(mats) else ""
        if "railing" in mat_name.lower():
            for v in f.verts:
                if abs(v.co.z - (-0.050)) < 0.02:
                    v.co.z = -0.010
    bm.to_mesh(b21.data)
    bm.free()
    b21.data.update()

check_c2("Step 2 (B21 Railing)")

# Step 3: Vieux Palais
print("\n--- Testing Step 3: Vieux Palais Insets ---")
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
            break
    to_inset = [f for f in bm.faces if f.normal.z > 0.95 and f.calc_area() > 0.2 and (mw @ f.calc_center_median()).z >= min_z + 0.40 * height]
    if to_inset:
        bmesh.ops.inset_individual(bm, faces=to_inset, thickness=0.20, depth=-0.12, use_even_offset=True)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()

check_c2("Step 3 (Vieux Palais)")

# Step 4: Collider
print("\n--- Testing Step 4: Collider Normals & East Buffer Elevation ---")
col = bpy.data.objects.get("Ground_District_Solid_Collider")
if col and col.data:
    me = col.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(f.normal.z) > 0.88:
            is_bottom = (abs(c.z - (-0.280)) < 0.02 or abs(c.z - (-0.350)) < 0.02 or 
                         abs(c.z - (-2.750)) < 0.02 or abs(c.z - (-3.500)) < 0.02)
            if is_bottom and f.normal.z > 0:
                f.normal_flip()
            if abs(c.x - 510.0) < 50.0 and abs(c.y - 150.0) < 50.0 and c.z > -0.20:
                for v in f.verts:
                    v.co.z = -0.080
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()

check_c2("Step 4 (Collider)")
