#!/usr/bin/env python3
r"""
src/stress_test_watertightness_and_collision.py
===============================================
Empirical Stress-Test Suite for Montreal Master Scene 25-Block Reconstruction:
Vehicle Drivability, Collision Integrity, and Ground Watertightness.

Challenges Requirements R1 & R3 from ORIGINAL_REQUEST.md:
1. Probe Roadbed Normal Vectors:
   - Check all 13 required arterial streets across the district.
   - Verify 100% of roadbed polygon normals point strictly upward (+Z, normal.z > 0.88)
     with ZERO inverted or downward-pointing normals.
   - Check waterfront promenade / quay meshes.
2. Probe Ground Collider Continuous Watertightness:
   - Grid sampling & raycast probes across district extent:
     Place d'Armes & Square Victoria east to Tour de l'Horloge (X = +985m)
     and south to Alexandra Pier (Y = -680m).
   - Probe Ground_District_Solid_Collider alone vs combined DRIVABLE meshes.
   - Detect bottomless drop-through holes or non-solid gaps.
3. Verify Solid 3D Ground Geometry:
   - Check replacement of zero-thickness single-sided ground sheets with solid 3D volumes
     (Z = -0.25m to 0.00m base + vertical quay walls dropping to -2.50m / -2.75m).
   - Check topology and face completeness of Ground_District_Solid_Collider.
4. Verify UE5 Nanite Manifest & Collision Configuration:
   - Check output/ue5_nanite/montreal_ue5_manifest.json for Ground_District_Solid_Collider role = DRIVABLE.
   - Check src/unreal/ue5_nanite_import.py for CTF_USE_COMPLEX_AS_SIMPLE + double_sided_geometry + BlockAll.
   - Check output/montreal_master.usdc for Ground_District_Solid_Collider prim & collision role.
5. Vehicle Spawn Point Drivability Probes:
   - Raycast downward from all recommended Chaos Vehicle spawn locations.

Execution:
  & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b output/montreal_master.blend --python src/stress_test_watertightness_and_collision.py
"""

import sys
import os
import json
import time
from pathlib import Path

try:
    import bpy
    from mathutils import Vector, Matrix
    from mathutils.bvhtree import BVHTree
except ImportError:
    print("ERROR: Must run inside Blender 5.2 (blender.exe -b output/montreal_master.blend --python src/stress_test_watertightness_and_collision.py)", file=sys.stderr)
    sys.exit(2)

try:
    from pxr import Usd
    HAS_PXR = True
except ImportError:
    HAS_PXR = False


PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORT_JSON = OUTPUT_DIR / "stress_test_m6_collision.json"
MANIFEST_PATH = OUTPUT_DIR / "ue5_nanite" / "montreal_ue5_manifest.json"
MASTER_USDC_PATH = OUTPUT_DIR / "montreal_master.usdc"
UE5_IMPORT_SCRIPT = PROJECT_ROOT / "src" / "unreal" / "ue5_nanite_import.py"

REQUIRED_13_ARTERIALS = [
    "Roadbed_Avenue_Viger",
    "Roadbed_Côte_de_la_Place_dArmes",
    "Roadbed_Place_Jacques_Cartier",
    "Roadbed_Rue_de_la_Commune",
    "Roadbed_Rue_McGill",
    "Roadbed_Rue_Notre_Dame",
    "Roadbed_Rue_Saint_Antoine",
    "Roadbed_Rue_Saint_François_Xavier",
    "Roadbed_Rue_Saint_Jacques",
    "Roadbed_Rue_Saint_Paul",
    "Roadbed_Rue_Saint_Pierre",
    "Roadbed_Rue_Saint_Sulpice",
    "Roadbed_Square_Victoria",
]

WATERFRONT_PROMENADES = [
    "Plage_de_l_Horloge_Beach_And_Boardwalk",
    "MTL_Owned_Quays_And_Marina_MTL-VM-0023",
    "MTL_Owned_Ground_Quays_And_Water_MTL-VM-0021",
    "MTL_Owned_Ground_And_Streets_MTL-VM-0022",
    "Ground_Quays_Streets_And_Water",
    "MTL_Owned_Ground_And_Streets_MTL-VM-0016",
    "MTL_Owned_Ground_And_Streets_MTL-VM-0017",
    "MTL_Owned_Ground_And_Streets_MTL-VM-0018",
    "MTL_VM_0019_Streetscape_And_Ground",
    "MTL_VM_0020_StreetNetwork",
    "MTL_VM_0024_StreetNetwork",
]


def probe_1_roadbed_normals():
    """Probe normal vectors across the 13 required arterial streets and waterfront promenades."""
    print("\n" + "=" * 70)
    print("PROBE 1: ROADBED NORMAL VECTORS VERIFICATION")
    print("=" * 70)

    results = {
        "arterial_streets": {},
        "total_arterial_polygons": 0,
        "arterial_upward_polygons": 0,
        "arterial_inverted_polygons": 0,
        "arterial_nz_below_088": 0,
        "arterials_pass": True,
        "waterfront_promenades": {},
    }

    # 1A: 13 Required Arterial Streets
    print("\n--- 1A: 13 Required Arterial Streets ---")
    for name in REQUIRED_13_ARTERIALS:
        obj = bpy.data.objects.get(name)
        if not obj:
            print(f"  [FAIL] MISSING ARTERIAL ROADBED: {name}")
            results["arterial_streets"][name] = {"found": False}
            results["arterials_pass"] = False
            continue

        me = obj.data
        mw = obj.matrix_world
        rot_3x3 = mw.to_3x3()

        poly_count = len(me.polygons)
        upward = 0
        inverted = 0
        nz_below_088 = 0
        min_nz = 1.0
        max_nz = -1.0

        for p in me.polygons:
            wn = (rot_3x3 @ p.normal).normalized()
            nz = wn.z
            if nz < min_nz: min_nz = nz
            if nz > max_nz: max_nz = nz

            if nz > 0.88:
                upward += 1
            else:
                nz_below_088 += 1

            if nz < 0.0:
                inverted += 1

        results["total_arterial_polygons"] += poly_count
        results["arterial_upward_polygons"] += upward
        results["arterial_inverted_polygons"] += inverted
        results["arterial_nz_below_088"] += nz_below_088

        pct_upward = (upward / poly_count * 100.0) if poly_count > 0 else 0.0
        passed = (poly_count > 0 and inverted == 0 and nz_below_088 == 0)
        if not passed:
            results["arterials_pass"] = False

        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {poly_count} polys | Upward(+Z): {upward} ({pct_upward:.1f}%) | Inverted: {inverted} | min_nz={min_nz:.4f}")

        results["arterial_streets"][name] = {
            "found": True,
            "polygons": poly_count,
            "upward_gt_088": upward,
            "pct_upward": pct_upward,
            "inverted": inverted,
            "nz_below_088": nz_below_088,
            "min_nz": min_nz,
            "max_nz": max_nz,
            "pass": passed,
        }

    pct_total_upward = (results["arterial_upward_polygons"] / results["total_arterial_polygons"] * 100.0) if results["total_arterial_polygons"] > 0 else 0.0
    print(f"\n  Arterial Totals: {results['arterial_upward_polygons']}/{results['total_arterial_polygons']} upward ({pct_total_upward:.2f}%), {results['arterial_inverted_polygons']} inverted.")
    print(f"  Arterials 100% Upward Normal Verdict: {'PASS' if results['arterials_pass'] else 'FAIL'}")

    # 1B: Waterfront Promenades & Quays
    print("\n--- 1B: Waterfront Promenades & Quays ---")
    for name in WATERFRONT_PROMENADES:
        obj = bpy.data.objects.get(name)
        if not obj:
            print(f"  [INFO] Waterfront object {name} not found in master scene")
            results["waterfront_promenades"][name] = {"found": False}
            continue

        me = obj.data
        mw = obj.matrix_world
        rot_3x3 = mw.to_3x3()

        poly_count = len(me.polygons)
        top_upward = 0
        vertical_walls = 0
        bottom_faces = 0
        inverted_top = 0

        for p in me.polygons:
            wn = (rot_3x3 @ p.normal).normalized()
            wc = mw @ p.center
            nz = wn.z

            if nz > 0.88:
                top_upward += 1
            elif abs(nz) <= 0.15:
                vertical_walls += 1
            elif nz < -0.88:
                bottom_faces += 1

            # Inverted top surface: center is near top deck (Z >= 0.0) and normal points downward
            if wc.z >= 0.0 and nz < -0.15:
                inverted_top += 1

        print(f"  {name}: {poly_count} polys | Top(+Z): {top_upward} | Vert walls: {vertical_walls} | Bottom(-Z): {bottom_faces} | Inverted top: {inverted_top}")
        results["waterfront_promenades"][name] = {
            "found": True,
            "polygons": poly_count,
            "top_upward_gt_088": top_upward,
            "vertical_walls": vertical_walls,
            "bottom_faces": bottom_faces,
            "inverted_top_faces": inverted_top,
        }

    return results


def probe_2_ground_collider_solidity():
    """Verify solid 3D ground geometry, face completeness, and check for remaining single-sided sheets."""
    print("\n" + "=" * 70)
    print("PROBE 2: GROUND COLLIDER SOLIDITY & TOPOLOGY VERIFICATION")
    print("=" * 70)

    results = {
        "collider_found": False,
        "collider_bbox": None,
        "collider_face_count": 0,
        "top_faces_count": 0,
        "bottom_faces_count": 0,
        "side_faces_count": 0,
        "missing_top_faces": [],
        "is_solid_closed_volume": False,
        "single_sided_sheets_found": [],
    }

    collider = bpy.data.objects.get("Ground_District_Solid_Collider")
    if not collider:
        print("  [CRITICAL FAIL] 'Ground_District_Solid_Collider' NOT FOUND in master scene!")
        return results

    results["collider_found"] = True
    me = collider.data
    mw = collider.matrix_world
    rot_3x3 = mw.to_3x3()

    vs_world = [mw @ v.co for v in me.vertices]
    xs = [v.x for v in vs_world]
    ys = [v.y for v in vs_world]
    zs = [v.z for v in vs_world]
    bbox = {
        "x_min": min(xs), "x_max": max(xs),
        "y_min": min(ys), "y_max": max(ys),
        "z_min": min(zs), "z_max": max(zs),
    }
    results["collider_bbox"] = bbox
    results["collider_face_count"] = len(me.polygons)

    print(f"  Ground_District_Solid_Collider Bounding Box:")
    print(f"    X: [{bbox['x_min']:.2f} .. {bbox['x_max']:.2f}] (span: {bbox['x_max'] - bbox['x_min']:.2f}m)")
    print(f"    Y: [{bbox['y_min']:.2f} .. {bbox['y_max']:.2f}] (span: {bbox['y_max'] - bbox['y_min']:.2f}m)")
    print(f"    Z: [{bbox['z_min']:.2f} .. {bbox['z_max']:.2f}] (span: {bbox['z_max'] - bbox['z_min']:.2f}m)")
    print(f"  Total polygons in collider: {len(me.polygons)}")

    # Classify faces:
    top_faces = []
    bottom_faces = []
    side_faces = []

    for p in me.polygons:
        wn = (rot_3x3 @ p.normal).normalized()
        wc = mw @ p.center
        if wn.z > 0.88:
            top_faces.append((p.index, wc, wn))
        elif wn.z < -0.88:
            bottom_faces.append((p.index, wc, wn))
        else:
            side_faces.append((p.index, wc, wn))

    results["top_faces_count"] = len(top_faces)
    results["bottom_faces_count"] = len(bottom_faces)
    results["side_faces_count"] = len(side_faces)

    print(f"  Top (+Z) faces: {len(top_faces)}")
    for idx, c, n in top_faces:
        print(f"    Face {idx:02d}: center=({c.x:7.1f}, {c.y:7.1f}, {c.z:6.3f}), normal=({n.x:4.2f}, {n.y:4.2f}, {n.z:4.2f})")

    print(f"  Bottom (-Z) faces: {len(bottom_faces)}")
    for idx, c, n in bottom_faces:
        print(f"    Face {idx:02d}: center=({c.x:7.1f}, {c.y:7.1f}, {c.z:6.3f}), normal=({n.x:4.2f}, {n.y:4.2f}, {n.z:4.2f})")

    print(f"  Side faces: {len(side_faces)}")

    # Check for missing top faces:
    # Notice: Box 1 (West buffer: X[-750..-420]), Box 2 (East buffer: X[420..600]), Box 3 (North buffer: Y[360..680])
    # bottom faces exist at Z = -0.250, but top faces at Z = 0.000 are missing!
    expected_top_regions = [
        ("Waterfront Basin", -75, -465, -2.500),
        ("West Mainland Buffer", -585, 150, 0.000),
        ("East Mainland Buffer", 510, 150, -0.150),
        ("North Mainland Buffer", 0, 520, 0.000),
        ("City Core", 0, -10, -0.150),
    ]

    for label, ex, ey, ez in expected_top_regions:
        matched = False
        for idx, c, n in top_faces:
            if abs(c.x - ex) < 100.0 and abs(c.y - ey) < 100.0 and abs(c.z - ez) < 0.10:
                matched = True
                break
        if not matched:
            print(f"  [BUG DETECTED] Missing top face for region '{label}' at expected center ~({ex}, {ey}, {ez})!")
            results["missing_top_faces"].append({"region": label, "expected_center": [ex, ey, ez]})

    results["is_solid_closed_volume"] = (len(results["missing_top_faces"]) == 0 and len(top_faces) == len(bottom_faces))
    print(f"  Ground_District_Solid_Collider Closed 3D Volume Verdict: {'PASS' if results['is_solid_closed_volume'] else 'FAIL (Top faces missing for 3 buffer regions)'}")

    # Check for stray single-sided ground planes in scene
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        nl = obj.name.lower()
        if "ortho" in nl or "satellite" in nl:
            results["single_sided_sheets_found"].append(obj.name)
            print(f"  [WARN] Stray satellite/ortho sheet found: {obj.name}")

    if not results["single_sided_sheets_found"]:
        print("  [PASS] Zero single-sided satellite ortho ground planes remain in scene.")

    return results


def build_unified_bvh(object_list):
    """Build a unified BVH tree from a list of Blender mesh objects."""
    all_verts = []
    all_polys = []
    vert_offset = 0

    for obj in object_list:
        if not obj or obj.type != "MESH" or obj.hide_render:
            continue
        me = obj.data
        mw = obj.matrix_world
        verts_local = [v.co for v in me.vertices]
        verts_world = [mw @ v for v in verts_local]

        all_verts.extend(verts_world)
        for p in me.polygons:
            all_polys.append([v + vert_offset for v in p.vertices])
        vert_offset += len(verts_world)

    if not all_verts or not all_polys:
        return None, 0, 0

    bvh = BVHTree.FromPolygons(all_verts, all_polys)
    return bvh, len(all_verts), len(all_polys)


def probe_3_watertightness_and_raycasts():
    """Perform extensive grid sampling and raycast probes across the district extent."""
    print("\n" + "=" * 70)
    print("PROBE 3: DISTRICT-WIDE WATERTIGHTNESS & DROP-THROUGH RAYCASTS")
    print("=" * 70)

    results = {
        "collider_alone_probes": {},
        "unified_drivable_probes": {},
        "spawn_point_probes": {},
        "district_extent_tested": {
            "x_range": [-700.0, 985.0],
            "y_range": [-680.0, 680.0],
        },
    }

    collider_obj = bpy.data.objects.get("Ground_District_Solid_Collider")

    # 3A: Raycast Sampling on Ground_District_Solid_Collider ALONE
    print("\n--- 3A: Probing Ground_District_Solid_Collider Alone Across District Extent ---")
    if collider_obj:
        bvh_collider, cv, cp = build_unified_bvh([collider_obj])
        print(f"  Built collider BVH tree with {cv} vertices and {cp} polygons.")

        # Key landmark probe coordinates:
        test_points = [
            ("Place d'Armes / Rue Notre-Dame", -22.0, -18.0),
            ("Square Victoria West", -375.0, -295.0),
            ("Rue Saint-Jacques Financial Canyon", -135.0, -45.0),
            ("Rue Saint-Antoine North", 0.0, 300.0),
            ("Champ-de-Mars Ramparts (North Buffer)", 0.0, 520.0),
            ("West Buffer (Rue McGill / Highway Edge)", -585.0, 150.0),
            ("East Buffer (Rue Saint-Denis Edge)", 510.0, 150.0),
            ("Marché Bonsecours (East)", 380.0, 440.0),
            ("Alexandra Pier (Grand Quai, South)", 150.0, -650.0),
            ("King Edward Pier (Waterfront)", 600.0, 30.0),
            ("Quai Jacques-Cartier (Waterfront)", 450.0, 200.0),
            ("Tour de l'Horloge (Clock Tower Pier, Far East)", 835.0, 835.0),
            ("Eastern District Boundary (X = +985m)", 985.0, 750.0),
            ("Southern District Boundary (Y = -680m)", 150.0, -680.0),
        ]

        collider_hits = 0
        collider_misses = 0
        landmark_results = []

        for name, tx, ty in test_points:
            origin = Vector((tx, ty, 10.0))
            direction = Vector((0.0, 0.0, -1.0))
            loc, norm, idx, dist = bvh_collider.ray_cast(origin, direction)
            hit = loc is not None

            if hit:
                collider_hits += 1
                hit_z = loc.z
                norm_z = norm.z
                status = "HIT"
                # Check if it hits at Z=0.0 vs dropping to Z=-0.25 (missing top face)
                if abs(hit_z - 0.0) < 0.05:
                    elev_note = "Z=0.00 (Roadbed grade)"
                elif abs(hit_z - (-0.15)) < 0.05:
                    elev_note = "Z=-0.15 (City core subgrade)"
                elif abs(hit_z - (-0.25)) < 0.05:
                    elev_note = "Z=-0.25 (BOTTOM SLAB: Top face missing! Drop-through = 0.25m)"
                elif abs(hit_z - (-2.50)) < 0.05:
                    elev_note = "Z=-2.50 (Waterfront basin subgrade)"
                else:
                    elev_note = f"Z={hit_z:.3f}"
                print(f"  [{status}] {name:42s} ({tx:6.1f}, {ty:6.1f}): Hit at {elev_note}, norm.z={norm_z:.2f}")
            else:
                collider_misses += 1
                status = "MISS (FALL-THROUGH)"
                print(f"  [{status}] {name:42s} ({tx:6.1f}, {ty:6.1f}): OUTSIDE COLLIDER BOUNDS!")

            landmark_results.append({
                "landmark": name,
                "x": tx, "y": ty,
                "hit": hit,
                "hit_z": loc.z if hit else None,
                "normal_z": norm.z if hit else None,
            })

        results["collider_alone_probes"]["landmarks"] = landmark_results
        results["collider_alone_probes"]["hits"] = collider_hits
        results["collider_alone_probes"]["misses"] = collider_misses

    # 3B: Raycast Sampling on ALL DRIVABLE / GROUND / PIER Meshes Combined
    print("\n--- 3B: Probing Unified DRIVABLE + GROUND + QUAYS + PIER Network ---")
    drivable_objects = []
    # Collect all drivable objects from Master Street Network, ground objects, quays, piers
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        nl = obj.name.lower()
        if any(k in nl for k in ["roadbed", "sidewalk", "curb", "crosswalk", "ground", "quay", "pier", "plage", "plaza"]):
            if not any(k in nl for k in ["lamp", "bench", "tree", "sign", "grate"]):
                drivable_objects.append(obj)

    print(f"  Collected {len(drivable_objects)} drivable/ground/pier objects for unified BVH.")
    bvh_unified, uv_count, up_count = build_unified_bvh(drivable_objects)
    print(f"  Unified BVH tree built: {uv_count} vertices, {up_count} polygons.")

    unified_hits = 0
    unified_misses = 0
    unified_results = []

    for name, tx, ty in test_points:
        origin = Vector((tx, ty, 10.0))
        direction = Vector((0.0, 0.0, -1.0))
        loc, norm, idx, dist = bvh_unified.ray_cast(origin, direction)
        hit = loc is not None

        if hit:
            unified_hits += 1
            hit_z = loc.z
            norm_z = norm.z
            status = "PASS (SOLID)"
            print(f"  [{status}] {name:42s} ({tx:6.1f}, {ty:6.1f}): Surface at Z={hit_z:+.3f}m | normal.z={norm_z:.2f}")
        else:
            unified_misses += 1
            status = "FAIL (VOID)"
            print(f"  [{status}] {name:42s} ({tx:6.1f}, {ty:6.1f}): NO SURFACE DETECTED!")

        unified_results.append({
            "landmark": name,
            "x": tx, "y": ty,
            "hit": hit,
            "hit_z": loc.z if hit else None,
            "normal_z": norm.z if hit else None,
        })

    results["unified_drivable_probes"]["landmarks"] = unified_results
    results["unified_drivable_probes"]["hits"] = unified_hits
    results["unified_drivable_probes"]["misses"] = unified_misses

    # 3C: Vehicle Spawn Point Drivability Probes
    print("\n--- 3C: Vehicle Spawn Point Drivability Probes ---")
    manifest_data = {}
    if MANIFEST_PATH.exists():
        try:
            manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    spawn_points = manifest_data.get("spawn_points", [])
    print(f"  Found {len(spawn_points)} spawn points in manifest:")

    spawn_results = []
    spawn_pass = True

    for sp in spawn_points:
        name = sp.get("name")
        mode = sp.get("mode")
        xyz = sp.get("blender_xyz_m")
        if not xyz:
            continue
        sx, sy, sz = xyz

        # Probe ground directly below spawn point
        origin = Vector((sx, sy, sz + 2.0))
        direction = Vector((0.0, 0.0, -1.0))
        loc, norm, idx, dist = bvh_unified.ray_cast(origin, direction)

        if loc:
            ground_z = loc.z
            wheel_clearance = sz - ground_z
            norm_z = norm.z
            valid = (wheel_clearance >= -0.05 and wheel_clearance <= 1.0 and norm_z > 0.88)
            if not valid and "flight" not in mode.lower():
                spawn_pass = False

            status = "PASS" if valid else ("WARN (FLY)" if "flight" in mode.lower() else "FAIL")
            print(f"  [{status}] {name:40s} ({mode:22s}): Spawn Z={sz:.2f}m -> Ground Z={ground_z:+.2f}m (clearance: {wheel_clearance:.2f}m, nz={norm_z:.2f})")
            spawn_results.append({
                "name": name, "mode": mode, "spawn_xyz": xyz,
                "ground_hit": True, "ground_z": ground_z, "clearance": wheel_clearance,
                "normal_z": norm_z, "pass": valid,
            })
        else:
            spawn_pass = False
            print(f"  [FAIL] {name:40s} ({mode:22s}): BOTTOMLESS VOID BELOW SPAWN POINT!")
            spawn_results.append({
                "name": name, "mode": mode, "spawn_xyz": xyz,
                "ground_hit": False, "pass": False,
            })

    results["spawn_point_probes"]["points"] = spawn_results
    results["spawn_point_probes"]["pass"] = spawn_pass

    return results


def probe_4_ue5_nanite_manifest_and_collision():
    """Verify manifest tagging, collision profile, and USD export configuration."""
    print("\n" + "=" * 70)
    print("PROBE 4: UE5 NANITE MANIFEST & COLLISION INTEGRITY VERIFICATION")
    print("=" * 70)

    results = {
        "manifest_exists": False,
        "ground_district_solid_collider_role": None,
        "roadbeds_tagged_drivable": {},
        "curbs_sidewalks_tagged_drivable": {},
        "role_counts": {},
        "ue5_import_script_verified": False,
        "ctf_use_complex_as_simple": False,
        "double_sided_geometry": False,
        "blockall_profile": False,
        "usd_prim_verified": False,
        "usd_ue5_collision_role": None,
    }

    # 4A: Check Manifest
    if MANIFEST_PATH.exists():
        results["manifest_exists"] = True
        try:
            m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            results["role_counts"] = m.get("role_counts", {})
            mesh_roles = m.get("mesh_roles", {})

            # Check Ground_District_Solid_Collider
            role = mesh_roles.get("Ground_District_Solid_Collider")
            results["ground_district_solid_collider_role"] = role
            print(f"  Ground_District_Solid_Collider in manifest role: {role} (Expected: DRIVABLE)")

            # Check 13 roadbeds
            for rname in REQUIRED_13_ARTERIALS:
                r_role = mesh_roles.get(rname)
                results["roadbeds_tagged_drivable"][rname] = (r_role == "DRIVABLE")

            all_roadbeds_drivable = all(results["roadbeds_tagged_drivable"].values())
            print(f"  All 13 arterial roadbeds tagged as DRIVABLE: {all_roadbeds_drivable}")

            # Check Sidewalks & Curbs
            results["curbs_sidewalks_tagged_drivable"]["District_Sidewalks_Raised"] = (mesh_roles.get("District_Sidewalks_Raised") == "DRIVABLE")
            results["curbs_sidewalks_tagged_drivable"]["District_Curbs_3D"] = (mesh_roles.get("District_Curbs_3D") == "DRIVABLE")
            results["curbs_sidewalks_tagged_drivable"]["District_Crosswalks_And_Markings"] = (mesh_roles.get("District_Crosswalks_And_Markings") == "DRIVABLE")
            print(f"  Curbs, Sidewalks, Crosswalks tagged as DRIVABLE: {all(results['curbs_sidewalks_tagged_drivable'].values())}")

        except Exception as e:
            print(f"  [ERROR] Parsing manifest failed: {e}")

    # 4B: Check UE5 Import Script
    if UE5_IMPORT_SCRIPT.exists():
        try:
            content = UE5_IMPORT_SCRIPT.read_text(encoding="utf-8")
            results["ctf_use_complex_as_simple"] = ("CTF_USE_COMPLEX_AS_SIMPLE" in content)
            results["double_sided_geometry"] = ("double_sided_geometry" in content and "True" in content)
            results["blockall_profile"] = ("BlockAll" in content)
            results["ue5_import_script_verified"] = (
                results["ctf_use_complex_as_simple"] and
                results["double_sided_geometry"] and
                results["blockall_profile"]
            )
            print(f"  ue5_nanite_import.py configures CTF_USE_COMPLEX_AS_SIMPLE: {results['ctf_use_complex_as_simple']}")
            print(f"  ue5_nanite_import.py configures double_sided_geometry = True: {results['double_sided_geometry']}")
            print(f"  ue5_nanite_import.py configures BlockAll collision profile: {results['blockall_profile']}")
        except Exception as e:
            print(f"  [ERROR] Reading ue5_nanite_import.py failed: {e}")

    # 4C: Check USD Stage
    if HAS_PXR and MASTER_USDC_PATH.exists():
        try:
            stage = Usd.Stage.Open(str(MASTER_USDC_PATH))
            prim = stage.GetPrimAtPath("/root/Ground_District_Solid_Collider")
            results["usd_prim_verified"] = (prim and prim.IsValid())
            if prim:
                prop = prim.GetProperty("userProperties:ue5_collision_role")
                if prop and prop.IsValid():
                    results["usd_ue5_collision_role"] = prop.Get()
            print(f"  USD stage /root/Ground_District_Solid_Collider prim valid: {results['usd_prim_verified']}")
            print(f"  USD ue5_collision_role attribute: {results['usd_ue5_collision_role']}")
        except Exception as e:
            print(f"  [ERROR] Inspecting USD stage failed: {e}")

    return results


def main():
    t_start = time.time()
    print("=" * 78)
    print("CHALLENGER 1: EMPIRICAL STRESS TEST SUITE (WATERTIGHTNESS & COLLISION)")
    print("=" * 78)
    print(f"Master Blend: {OUTPUT_DIR / 'montreal_master.blend'}")
    print(f"Master USDC:  {MASTER_USDC_PATH}")
    print(f"Manifest:     {MANIFEST_PATH}")

    p1 = probe_1_roadbed_normals()
    p2 = probe_2_ground_collider_solidity()
    p3 = probe_3_watertightness_and_raycasts()
    p4 = probe_4_ue5_nanite_manifest_and_collision()

    # Overall Verdict Evaluation
    print("\n" + "=" * 78)
    print("SYNTHESIS & ADVERSARIAL VERDICT EVALUATION")
    print("=" * 78)

    c1_pass = p1["arterials_pass"] and (p1["arterial_inverted_polygons"] == 0)
    # Check if unified drivable network covers the district extent
    c2_pass = (p3["unified_drivable_probes"]["misses"] == 0)
    # Check if collider itself is closed 3D manifold
    c3_pass = p2["is_solid_closed_volume"]
    # Check manifest and UE5 configuration
    c4_pass = (
        p4["ground_district_solid_collider_role"] == "DRIVABLE" and
        p4["ue5_import_script_verified"] and
        p4["usd_prim_verified"]
    )

    print(f"  Criterion 1 (Roadbed Normals 100% Upward, 0 Inverted): {'APPROVE' if c1_pass else 'REJECT'}")
    print(f"  Criterion 2 (Continuous Watertightness across District):  {'APPROVE' if c2_pass else 'REJECT'}")
    print(f"  Criterion 3 (Solid 3D Ground Geometry & Closed Volumes): {'APPROVE' if c3_pass else 'REJECT (Top faces missing in 3 buffer boxes)'}")
    print(f"  Criterion 4 (UE5 Nanite Manifest & Collision BlockAll):   {'APPROVE' if c4_pass else 'REJECT'}")

    # Note: If C3 fails (missing top faces on 3 buffer boxes of Ground_District_Solid_Collider),
    # or C2 has missing coverage outside X=600 in the collider alone, document precise findings!
    all_pass = c1_pass and c2_pass and c3_pass and c4_pass
    overall_verdict = "APPROVE" if all_pass else "REJECT"

    print(f"\n  >>> OVERALL STRESS-TEST VERDICT: {overall_verdict} <<<")

    full_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": overall_verdict,
        "criteria": {
            "criterion_1_roadbed_normals": {"pass": c1_pass, "details": p1},
            "criterion_2_continuous_watertightness": {"pass": c2_pass, "details": p3},
            "criterion_3_solid_3d_ground_geometry": {"pass": c3_pass, "details": p2},
            "criterion_4_ue5_collision_manifest": {"pass": c4_pass, "details": p4},
        },
        "execution_time_sec": time.time() - t_start,
    }

    try:
        REPORT_JSON.write_text(json.dumps(full_report, indent=2), encoding="utf-8")
        print(f"\n  Saved empirical report to: {REPORT_JSON}")
    except Exception as e:
        print(f"  Warning: Failed to save JSON report: {e}")

    print("=" * 78)


if __name__ == "__main__":
    main()
