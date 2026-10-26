import bpy
import bmesh
from mathutils import Vector, geometry
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("TESTING ADVERSARIAL AND COLLIDER REMEDIATION")
print("=" * 80)

# 1. Delete legacy shallow water faces (Z > -1.0m) from Block 21 and Block 35 ground objects
for obj_name in ["MTL_Owned_Ground_Quays_And_Water_MTL-VM-0021", "Peninsula_Ground_Quays_Park_And_Water"]:
    obj = bpy.data.objects.get(obj_name)
    if obj and obj.data:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        mats = [m.name if m else "" for m in obj.data.materials]
        to_del = []
        for f in bm.faces:
            mat_name = mats[f.material_index] if f.material_index < len(mats) else ""
            if "water" in mat_name.lower():
                c = f.calc_center_median()
                if c.z > -1.0:
                    to_del.append(f)
        if to_del:
            print(f"{obj_name}: deleting {len(to_del)} shallow legacy water faces at Z > -1.0m.")
            bmesh.ops.delete(bm, geom=to_del, context="FACES")
            bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

# 2. Fix Vieux Palais spike vertex and inset roof faces
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
    
    # Snap spike vertex if present
    snapped = False
    for v in bm.verts:
        if abs(v.co.x - 78.2011) < 0.2 and abs(v.co.y - 305.1005) < 0.2:
            v.co.x = 95.892
            v.co.y = 337.251
            snapped = True
            break
    if snapped:
        print("Vieux Palais: snapped boundary spike vertex.")
    
    # Inset upper flat roof faces
    to_inset = [f for f in bm.faces if f.normal.z > 0.95 and f.calc_area() > 0.2 and (mw @ f.calc_center_median()).z >= min_z + 0.40 * height]
    print(f"Vieux Palais: insetting {len(to_inset)} roof faces.")
    if to_inset:
        bmesh.ops.inset_individual(bm, faces=to_inset, thickness=0.20, depth=-0.12, use_even_offset=True)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()

# 3. Ground_District_Solid_Collider: fix bottom face normals and East buffer top face
col = bpy.data.objects.get("Ground_District_Solid_Collider")
if col and col.data:
    me = col.data
    # For all boxes in collider:
    # Any face with abs(normal.z) > 0.88:
    # If center.z is the bottom of its box (e.g. z < -0.20 and not the basin floor at -2.50), normal should be -Z!
    # Specifically:
    # Top faces should point up (normal.z > 0.88), Bottom faces should point down (normal.z < -0.88).
    # Let's inspect each box or face in bm:
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    
    # Also adjust Face 87 (East Mainland Buffer at (510, 150)) to Z = -0.080
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(f.normal.z) > 0.88:
            # Check if this is a bottom face that was flipped up:
            # Bottom faces sit at z = -0.280, -0.350, -2.750, -3.500
            is_bottom = (abs(c.z - (-0.280)) < 0.02 or abs(c.z - (-0.350)) < 0.02 or 
                         abs(c.z - (-2.750)) < 0.02 or abs(c.z - (-3.500)) < 0.02)
            if is_bottom and f.normal.z > 0:
                f.normal_flip()
            
            # East buffer top face at (510, 150):
            if abs(c.x - 510.0) < 50.0 and abs(c.y - 150.0) < 50.0 and c.z > -0.20:
                for v in f.verts:
                    v.co.z = -0.080
    
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()
    print("Ground_District_Solid_Collider: corrected face orientations and East buffer elevation.")

# 4. Now run Test 3 and Test 4 from stress_test_boundary_and_coplanar
print("\n--- RUNNING TEST 3 & 4 AUDIT ---")
from tests.adversarial.stress_test_boundary_and_coplanar import MontrealBoundaryAndCoplanarChallenger
tester = MontrealBoundaryAndCoplanarChallenger()
pass_3 = tester.test_roof_membrane_insets_blocks_16_to_25()
pass_4 = tester.test_inter_block_boundary_coplanar_sweep()
print(f"Test 3 Result: {'PASS' if pass_3 else 'FAIL'}")
print(f"Test 4 Result: {'PASS' if pass_4 else 'FAIL'}")

# 5. Run Probe 2 & 3 from stress_test_watertightness_and_collision
print("\n--- RUNNING STRESS TEST PROBE 2 ---")
from src.stress_test_watertightness_and_collision import probe_2_ground_collider_solidity
p2 = probe_2_ground_collider_solidity()
print(f"Probe 2 Closed 3D Volume: {'PASS' if p2['is_solid_closed_volume'] else 'FAIL'}")

all_ok = pass_3 and pass_4 and p2["is_solid_closed_volume"]
print(f"\nOVERALL REMEDIATION STATUS: {'ALL CHECKS PASSED!' if all_ok else 'SOME CHECKS STILL FAILED'}")

if all_ok:
    master_blend = str(PROJECT_ROOT / "output" / "montreal_master.blend")
    tmp_blend = master_blend + ".tmp.blend"
    import os
    if os.path.exists(tmp_blend):
        try: os.remove(tmp_blend)
        except Exception: pass
    print("Saving master blend...")
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
    os.replace(tmp_blend, master_blend)
    print("SUCCESSFULLY SAVED output/montreal_master.blend!")
