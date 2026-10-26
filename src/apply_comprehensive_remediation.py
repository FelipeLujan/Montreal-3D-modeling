import bpy
import bmesh
from mathutils import Vector, geometry
import math
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("APPLYING COMPREHENSIVE SOLVE FOR ALL REMAINING ISSUES")
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

# 4. Ground_District_Solid_Collider: fix bottom face normals and East buffer top face
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
            
            # East buffer top face at (510, 150):
            if abs(c.x - 510.0) < 50.0 and abs(c.y - 150.0) < 50.0 and c.z > -0.20:
                for v in f.verts:
                    v.co.z = -0.080
    
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()
    print("  Ground_District_Solid_Collider: corrected face orientations and East buffer elevation.")

# 5. In-Memory Audits
print("\n" + "=" * 80)
print("RUNNING IN-MEMORY VERIFICATION AUDITS")
print("=" * 80)

# Audit A: tests/adversarial/stress_test_boundary_and_coplanar.py
from tests.adversarial.stress_test_boundary_and_coplanar import MontrealBoundaryAndCoplanarChallenger
tester = MontrealBoundaryAndCoplanarChallenger()
pass_1 = tester.test_hidden_and_proxy_meshes()
pass_2 = tester.test_cross_block_building_deduplication()
pass_3 = tester.test_roof_membrane_insets_blocks_16_to_25()
pass_4 = tester.test_inter_block_boundary_coplanar_sweep()

print(f"\n--- Adversarial Suite Results ---")
print(f"  Test 1 (Hidden & Proxies): {'PASS' if pass_1 else 'FAIL'}")
print(f"  Test 2 (Deduplication):   {'PASS' if pass_2 else 'FAIL'}")
print(f"  Test 3 (Roof Insets):     {'PASS' if pass_3 else 'FAIL'}")
print(f"  Test 4 (Boundary Contact):{'PASS' if pass_4 else 'FAIL'}")

# Audit B: src/stress_test_watertightness_and_collision.py
from src.stress_test_watertightness_and_collision import (
    probe_1_roadbed_normals, probe_2_ground_collider_solidity,
    probe_3_watertightness_and_raycasts, probe_4_ue5_nanite_manifest_and_collision
)
p1 = probe_1_roadbed_normals()
p2 = probe_2_ground_collider_solidity()
p3 = probe_3_watertightness_and_raycasts()
p4 = probe_4_ue5_nanite_manifest_and_collision()

c1_pass = p1["arterials_pass"] and (p1["arterial_inverted_polygons"] == 0)
c2_pass = (p3["unified_drivable_probes"]["misses"] == 0)
c3_pass = p2["is_solid_closed_volume"]
c4_pass = (p4["ground_district_solid_collider_role"] == "DRIVABLE")

print(f"\n--- Watertightness & Collision Suite Results ---")
print(f"  Criterion 1 (Normals Upward):  {'APPROVE' if c1_pass else 'REJECT'}")
print(f"  Criterion 2 (Watertightness):  {'APPROVE' if c2_pass else 'REJECT'}")
print(f"  Criterion 3 (Solid Collider):  {'APPROVE' if c3_pass else 'REJECT'}")
print(f"  Criterion 4 (UE5 Collision):   {'APPROVE' if c4_pass else 'REJECT'}")

# Audit C: src/audit_zfighting_headless.py
from src.audit_zfighting_headless import MontrealZFightingAuditor
auditor = MontrealZFightingAuditor()
auditor.inspect_scene_inventory()
r1 = auditor.audit_roof_cornice_zfighting()
r2 = auditor.audit_ground_street_sidewalk_zfighting()
r3 = auditor.audit_cross_block_building_duplication()
r4 = auditor.audit_street_network_completeness()
r5 = auditor.audit_hidden_meshes()

z_pass = r1["passed"] and r2["passed"] and r3["passed"] and r4["passed"] and r5["passed"]
print(f"\n--- Z-Fighting Suite Results ---")
print(f"  Roof/Cornice:  {'PASS' if r1['passed'] else 'FAIL'}")
print(f"  Ground/Street: {'PASS' if r2['passed'] else 'FAIL'}")
print(f"  Duplicates:    {'PASS' if r3['passed'] else 'FAIL'}")
print(f"  13 Streets:    {'PASS' if r4['passed'] else 'FAIL'}")
print(f"  Hidden Meshes: {'PASS' if r5['passed'] else 'FAIL'}")

overall_success = (pass_1 and pass_2 and pass_3 and pass_4 and
                   c1_pass and c2_pass and c3_pass and c4_pass and
                   z_pass)

print("\n" + "=" * 80)
print(f"OVERALL UNIFIED STATUS: {'100% PERFECT PASS ON ALL SUITES!' if overall_success else 'ISSUES REMAIN'}")
print("=" * 80)

if overall_success:
    master_blend = str(PROJECT_ROOT / "output" / "montreal_master.blend")
    tmp_blend = master_blend + ".tmp.blend"
    if os.path.exists(tmp_blend):
        try: os.remove(tmp_blend)
        except Exception: pass
    print("Saving clean master blend file...")
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
    os.replace(tmp_blend, master_blend)
    print("SUCCESSFULLY SAVED output/montreal_master.blend!")
