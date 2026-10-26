#!/usr/bin/env python3
"""
src/test_remediation.py
Remediation script for 13 Poly Haven 3D models, prop clearances, and UE5 spawn point.
"""
import os
import sys
import math
sys.path.insert(0, r"C:\Users\Felipe\Documents\coding\montreal")
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
MODELS_DIR = os.path.join(BASE_DIR, "assets", "polyhaven", "models")
MASTER_BLEND = os.path.join(BASE_DIR, "output", "montreal_master.blend")

MODEL_REPRESENTATIVES = {
    "jacaranda_tree": "jacaranda_tree_LOD0",
    "tree_small_02": "tree_small_02_LOD0",
    "searsia_burchellii": "searsia_burchellii_medium_LOD0",
    "pine_tree_01": "pine_tree_01_a_LOD0",
    "fir_tree_01": "fir_tree_01_a_LOD0",
    "shrub_01": "shrub_01_b_LOD0",
    "shrub_02": "shrub_02_b_LOD0",
    "street_lamp_01": "street_lamp_01",
    "street_lamp_02": "street_lamp_02",
    "Lantern_01": "Lantern_01",
    "modular_electricity_poles": "preset_01_pole",
    "modular_street_seating": "seat_bench",
    "fire_hydrant": "fire_hydrant"
}

def run_remediation():
    print("=" * 78)
    print("EXECUTING CLEAN POLY HAVEN PROPS REMEDIATION")
    print("=" * 78)

    from src.unreal.prepare_blender_for_ue5_nanite import export_ue5_nanite_usd

    # 1. Purge all existing legacy/clipping PolyHaven objects from master blend
    legacy_props = [o for o in list(bpy.data.objects) if o.type == "MESH" and (o.name.startswith("PolyHaven_") or "polyhaven" in o.name.lower())]
    print(f"Purging {len(legacy_props)} legacy PolyHaven objects...")
    for o in legacy_props:
        try:
            bpy.data.objects.remove(o, do_unlink=True)
        except Exception:
            pass

    # 2. Build Building Wall BVH (matching check_true_prop_distance.py exactly)
    print("Building Building Wall BVH from vertical exterior walls...")
    bm_walls = bmesh.new()
    for obj in bpy.data.objects:
        if obj.type == "MESH" and not obj.hide_render:
            nl = obj.name.lower()
            if any(k in nl for k in ["bldg", "owned"]) and not any(k in nl for k in ["tree", "lamp", "prop", "ground", "quay", "street", "sidewalk", "curb", "water", "vessel", "polyhaven"]):
                me = obj.to_mesh()
                mw = obj.matrix_world
                for poly in me.polygons:
                    norm = (mw.to_3x3() @ poly.normal).normalized()
                    if abs(norm.z) < 0.3:  # vertical exterior wall
                        v_cos = [mw @ me.vertices[vid].co for vid in poly.vertices]
                        bm_walls.faces.new([bm_walls.verts.new(co) for co in v_cos])
                obj.to_mesh_clear()

    bm_walls.verts.ensure_lookup_table()
    bm_walls.faces.ensure_lookup_table()
    print(f"Total wall faces in BVH: {len(bm_walls.faces)}")
    bvh_walls = BVHTree.FromBMesh(bm_walls)

    # 3. Build Drivable & Roadbed BVH
    drivable_objects = []
    roadbed_objects = []
    for obj in bpy.data.objects:
        if obj.type == "MESH" and not obj.hide_render:
            nl = obj.name.lower()
            if any(k in nl for k in ["roadbed", "sidewalk", "curb", "crosswalk", "ground", "quay", "pier", "plage", "plaza"]):
                if not any(k in nl for k in ["lamp", "bench", "tree", "sign", "grate", "water"]):
                    drivable_objects.append(obj)
            if "roadbed" in nl:
                roadbed_objects.append(obj)

    def build_bvh(objs):
        all_verts = []
        all_polys = []
        v_off = 0
        for o in objs:
            me = o.data
            mw = o.matrix_world
            verts_world = [mw @ v.co for v in me.vertices]
            all_verts.extend(verts_world)
            for p in me.polygons:
                all_polys.append([v + v_off for v in p.vertices])
            v_off += len(verts_world)
        if not all_verts or not all_polys:
            return None
        return BVHTree.FromPolygons(all_verts, all_polys)

    bvh_drivable = build_bvh(drivable_objects)
    bvh_roadbed = build_bvh(roadbed_objects)

    # 4. Cache template meshes from models
    cached_meshes = {}
    print("\nLoading and caching 13 Poly Haven model meshes...")
    for model_id, mesh_name in MODEL_REPRESENTATIVES.items():
        blend_path = os.path.join(MODELS_DIR, model_id, f"{model_id}.blend")
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            data_to.objects = [o for o in data_from.objects if o == mesh_name]
        obj = bpy.data.objects.get(mesh_name)
        if obj and obj.data:
            cached_meshes[model_id] = obj.data
            obj.data.use_fake_user = True
            bpy.data.objects.remove(obj, do_unlink=True)
            print(f"  [CACHED] {model_id:<26} -> {mesh_name} ({len(cached_meshes[model_id].vertices)} verts)")
        else:
            print(f"  [ERROR] Could not cache {model_id} -> {mesh_name}")

    assert len(cached_meshes) == 13, f"Expected 13 cached models, got {len(cached_meshes)}"

    prop_col = bpy.data.collections.get("Master_Streets_And_Props")
    if not prop_col:
        prop_col = bpy.data.collections.get("Master_Street_Network")
    if not prop_col:
        prop_col = bpy.context.scene.collection

    # 5. Curated Open Plaza & Park Locations (known to have huge clearance from any building walls)
    public_zones = [
        # Place d'Armes & Parvis (Block 1)
        (-35.0, -15.0), (-25.0, -5.0), (-10.0, -8.0), (0.0, -18.0), (-45.0, -20.0),
        # Place Jacques-Cartier (Block 6)
        (155.0, 275.0), (170.0, 295.0), (185.0, 315.0), (160.0, 335.0), (175.0, 355.0), (190.0, 375.0),
        # Square Victoria (Block 10)
        (-365.0, -265.0), (-345.0, -245.0), (-355.0, -225.0), (-335.0, -255.0), (-370.0, -235.0),
        # Champ-de-Mars Lawns (Block 20)
        (-15.0, 485.0), (15.0, 505.0), (45.0, 515.0), (75.0, 525.0), (105.0, 535.0), (125.0, 545.0),
        # Place d'Youville (Block 26)
        (-255.0, -185.0), (-235.0, -175.0), (-215.0, -165.0), (-195.0, -180.0), (-275.0, -195.0),
        # Quai King-Edward (Block 21)
        (545.0, 25.0), (575.0, 45.0), (615.0, 65.0), (530.0, 15.0),
        # Grand Quai / Quai Alexandra (Block 22)
        (210.0, -590.0), (250.0, -570.0), (290.0, -540.0), (180.0, -610.0),
        # Quai Jacques-Cartier Promenade (Block 23)
        (425.0, 185.0), (455.0, 215.0), (485.0, 245.0), (395.0, 155.0),
        # Bassin Bonsecours Park (Block 24)
        (355.0, 405.0), (385.0, 425.0), (405.0, 445.0), (335.0, 385.0),
        # Quai de l'Horloge Boardwalk (Block 25)
        (805.0, 755.0), (845.0, 785.0), (885.0, 815.0), (785.0, 735.0),
        # Lachine Canal Towpath / Silo 5 (Block 28/29)
        (-410.0, -370.0), (-380.0, -350.0), (-360.0, -340.0), (-430.0, -390.0),
        # Chinatown Sun Yat-sen Plaza (Block 31)
        (-145.0, 475.0), (-135.0, 490.0), (-155.0, 465.0),
        # Parc de Dieppe (Block 35)
        (945.0, -515.0), (965.0, -495.0), (985.0, -475.0), (1005.0, -455.0),
        # Chateau Viger Courtyard & Dalhousie (Block 33/34)
        (455.0, 535.0), (485.0, 555.0), (505.0, 575.0), (435.0, 515.0),
        # Old Port Waterfront promenade (Rue de la Commune Est)
        (220.0, 180.0), (260.0, 220.0), (300.0, 260.0), (340.0, 300.0),
        # Rue McGill wide plaza edge
        (-290.0, -120.0), (-270.0, -90.0), (-250.0, -60.0),
        # Place Royale / Pointe-a-Calliere
        (10.0, -150.0), (30.0, -130.0), (50.0, -110.0), (70.0, -90.0)
    ]

    model_keys = list(MODEL_REPRESENTATIVES.keys())
    placed_props = []
    placed_counts = {m: 0 for m in model_keys}

    print(f"\nEvaluating candidate coordinates across district...")
    for idx, (cand_x, cand_y) in enumerate(public_zones):
        loc, norm, _, _ = bvh_drivable.ray_cast(Vector((cand_x, cand_y, 10.0)), Vector((0, 0, -1)))
        if not loc or norm.z < 0.88 or loc.z < -0.20 or loc.z > 1.0:
            continue
        cand_z = loc.z

        _, _, _, dist_wall = bvh_walls.find_nearest(Vector((cand_x, cand_y, cand_z)))
        if dist_wall < 2.5:
            continue

        if bvh_roadbed:
            _, _, _, dist_road = bvh_roadbed.find_nearest(Vector((cand_x, cand_y, cand_z)))
            if dist_road < 1.2:
                continue

        too_close = False
        for (px, py, pz) in placed_props:
            if math.hypot(cand_x - px, cand_y - py) < 3.0:
                too_close = True
                break
        if too_close:
            continue

        model_id = model_keys[len(placed_props) % len(model_keys)]
        rot_z = (len(placed_props) * 53.0) % 360.0 * (math.pi / 180.0)
        scale = 1.0
        if "tree" in model_id or "fir" in model_id or "pine" in model_id:
            scale = 0.90 + (len(placed_props) % 4) * 0.05

        mesh_data = cached_meshes[model_id]
        inst_name = f"PolyHaven_{model_id}_{placed_counts[model_id]:03d}"
        inst = bpy.data.objects.new(inst_name, mesh_data)
        prop_col.objects.link(inst)
        inst.location = (cand_x, cand_y, cand_z)
        inst.rotation_euler = (0.0, 0.0, rot_z)
        inst.scale = (scale, scale, scale)

        placed_props.append((cand_x, cand_y, cand_z))
        placed_counts[model_id] += 1

    print(f"\nSuccessfully placed {len(placed_props)} props across all 13 models:")
    for m in model_keys:
        print(f"  - {m:<26}: {placed_counts[m]} instances")
        assert placed_counts[m] >= 3, f"Model {m} has fewer than 3 instances ({placed_counts[m]})!"

    # 6. Verify clearances matching check_true_prop_distance.py
    ph_objs = [o for o in bpy.data.objects if o.type == 'MESH' and (o.name.startswith("PolyHaven_") or "polyhaven" in o.name.lower())]
    print(f"\nVerifying true distance to walls on all {len(ph_objs)} Poly Haven props...")
    min_dist = float('inf')
    violations = 0
    for o in ph_objs:
        loc = o.matrix_world.translation
        _, _, _, d = bvh_walls.find_nearest(loc)
        if d < min_dist:
            min_dist = d
        if d < 1.8:
            violations += 1
            print(f"  [VIOLATION] {o.name} at ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f}) -> dist={d:.2f}m")
        else:
            print(f"  [OK] {o.name:<40} -> dist={d:.2f}m")

    print("\n" + "=" * 60)
    print(f"Min true distance to building walls: {min_dist:.2f}m (Threshold: >= 1.8m)")
    print(f"Violations: {violations} / {len(ph_objs)}")
    print("=" * 60)
    assert violations == 0, f"Found {violations} clearance violations!"
    assert min_dist >= 1.8, f"Min distance {min_dist:.2f}m < 1.8m!"

    # 7. Save master blend
    print(f"\nSaving updated master blend to {MASTER_BLEND}...")
    try:
        bpy.ops.wm.save_mainfile()
    except Exception:
        bpy.ops.wm.save_as_mainfile(filepath=MASTER_BLEND, check_existing=False)

    # 8. Re-export USD & Manifest
    print("Re-exporting UE5 USD stage and manifest...")
    export_ue5_nanite_usd()
    print("Remediation completed successfully!")

    bm_walls.free()

if __name__ == "__main__":
    run_remediation()
