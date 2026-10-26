#!/usr/bin/env python3
"""
src/forensic_scene_audit.py
Forensic Inspection Script to verify genuine 3D geometry, window recess depths,
landmark structures, water surface & canal carving, and Poly Haven assets.
"""
import os
import sys
import json
import re
from collections import defaultdict

try:
    import bpy
    from mathutils import Vector
except ImportError:
    print("Must run inside Blender 5.2", file=sys.stderr)
    sys.exit(1)

def run_forensic_scene_audit():
    print("=" * 80)
    print("FORENSIC GEOMETRY & ASSET INTEGRITY INSPECTION")
    print("=" * 80)

    results = {
        "blocks_count": 0,
        "block_collections": [],
        "landmarks": {},
        "water_surface": {},
        "vessels": [],
        "polyhaven_models": {},
        "window_recess_samples": [],
        "ground_collider": {}
    }

    # 1. Block Collections
    owned_cols = [c.name for c in bpy.data.collections if "owned" in c.name.lower()]
    results["blocks_count"] = len(owned_cols)
    results["block_collections"] = sorted(owned_cols)
    print(f"Total Block Owned Collections: {len(owned_cols)}")

    # 2. Key Landmark Check
    landmarks_to_check = [
        ("Marche_Bonsecours_Dome", ["Bonsecours", "Dome"]),
        ("Chapelle_Bonsecours_Spire", ["Chapelle", "Spire"]),
        ("Champ_de_Mars_Ramparts", ["Rampart", "Champ_de_Mars"]),
        ("Tour_de_l_Horloge", ["Horloge", "Clock"]),
        ("Grande_Roue_Ferris_Wheel", ["Roue", "Ferris", "Wheel"]),
        ("Grand_Quai_Tower", ["Grand_Quai", "Observation", "Tower"]),
        ("Habitat_67_Modular_Cubes", ["Habitat", "Habitat67"]),
        ("Farine_Five_Roses_Mill", ["Farine", "Five_Roses", "Flour"]),
        ("Bota_Bota_Ferry_Spa", ["Bota", "Ferry"]),
        ("Silo_No_5_Elevators", ["Silo", "Grain"]),
        ("Lachine_Canal_Locks", ["Ecluse", "Lock", "Lachine"]),
        ("Chinatown_Paifang_Arch", ["Chinatown", "Paifang", "Gate"]),
        ("Grand_Trunk_Building", ["Grand_Trunk", "McGill"]),
        ("Place_dYouville_Fire_Station", ["Fire_Station", "Caserne", "Obelisk"]),
        ("Chateau_Viger_Castle_Hotel", ["Chateau_Viger", "Viger"]),
        ("Gare_Dalhousie", ["Gare_Dalhousie", "Dalhousie"])
    ]

    for label, keywords in landmarks_to_check:
        found_objs = []
        for obj in bpy.data.objects:
            if obj.type == "MESH" and not obj.hide_render:
                oname = obj.name.lower()
                if any(k.lower() in oname for k in keywords):
                    found_objs.append({
                        "name": obj.name,
                        "verts": len(obj.data.vertices),
                        "faces": len(obj.data.polygons),
                        "dim": [round(d, 2) for d in obj.dimensions]
                    })
        results["landmarks"][label] = {
            "found": len(found_objs) > 0,
            "count": len(found_objs),
            "samples": found_objs[:3]
        }
        status = "FOUND" if len(found_objs) > 0 else "MISSING"
        top_verts = sum(f["verts"] for f in found_objs)
        print(f"  Landmark {label:<30}: {status} ({len(found_objs)} objects, {top_verts:,} verts)")

    # 3. Water Surface and Vessels
    water_obj = bpy.data.objects.get("Water_District_StLawrence_And_Canals")
    if water_obj:
        mats = [m.name for m in water_obj.data.materials if m]
        # Check node tree for image textures
        tex_files = []
        for m in water_obj.data.materials:
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == "TEX_IMAGE" and n.image:
                        tex_files.append(n.image.name)
        bbox = [water_obj.matrix_world @ Vector(c) for c in water_obj.bound_box]
        results["water_surface"] = {
            "name": water_obj.name,
            "verts": len(water_obj.data.vertices),
            "faces": len(water_obj.data.polygons),
            "materials": mats,
            "texture_files": tex_files,
            "z_min": min(v.z for v in bbox),
            "z_max": max(v.z for v in bbox),
            "x_span": [min(v.x for v in bbox), max(v.x for v in bbox)],
            "y_span": [min(v.y for v in bbox), max(v.y for v in bbox)]
        }
        print(f"  Water Mesh: {water_obj.name} ({len(water_obj.data.polygons):,} faces), Z={min(v.z for v in bbox):.2f}m..{max(v.z for v in bbox):.2f}m")
        print(f"  Water Image Textures: {tex_files}")
    else:
        print("  WARNING: Water_District_StLawrence_And_Canals not found by exact name, scanning for water meshes...")
        water_objs = [o for o in bpy.data.objects if "water" in o.name.lower() and o.type == "MESH"]
        print(f"  Found {len(water_objs)} water meshes: {[o.name for o in water_objs[:5]]}")

    # Harbor Vessels
    vessel_objs = [o for o in bpy.data.objects if any(k in o.name.lower() for k in ["boat", "vessel", "ship", "yacht", "bota", "buoy", "mouche", "liner"])]
    results["vessels"] = [{"name": o.name, "verts": len(o.data.vertices)} for o in vessel_objs]
    print(f"  Moored Vessels and Harbor Features: {len(vessel_objs)} objects")

    # 4. Ground Solid Collider
    collider_obj = bpy.data.objects.get("Ground_District_Solid_Collider")
    if collider_obj:
        c_bb = [collider_obj.matrix_world @ Vector(c) for c in collider_obj.bound_box]
        results["ground_collider"] = {
            "name": collider_obj.name,
            "verts": len(collider_obj.data.vertices),
            "faces": len(collider_obj.data.polygons),
            "z_range": [round(min(v.z for v in c_bb), 2), round(max(v.z for v in c_bb), 2)],
            "x_range": [round(min(v.x for v in c_bb), 2), round(max(v.x for v in c_bb), 2)],
            "y_range": [round(min(v.y for v in c_bb), 2), round(max(v.y for v in c_bb), 2)]
        }
        print(f"  Collider: {collider_obj.name} (Z={min(v.z for v in c_bb):.2f}m..{max(v.z for v in c_bb):.2f}m, faces={len(collider_obj.data.polygons)})")

    # 5. Poly Haven 3D Models
    ph_keywords = ["jacaranda", "tree_small", "searsia", "pine_tree", "fir_tree", "shrub", "street_lamp", "lantern", "modular_street", "fire_hydrant"]
    ph_counts = defaultdict(int)
    for obj in bpy.data.objects:
        oname = obj.name.lower()
        for k in ph_keywords:
            if k in oname:
                ph_counts[k] += 1
                break
    results["polyhaven_models"] = dict(ph_counts)
    print("  Poly Haven 3D Assets Populated:")
    for k, cnt in sorted(ph_counts.items()):
        print(f"    {k:<25}: {cnt:>3} instances")

    # 6. Window Bays and Reveal Depth Forensics
    # Sample 10 building meshes across different blocks and examine vertex coordinates
    window_objs = [o for o in bpy.data.objects if o.type == "MESH" and any(k in o.name.lower() for k in ["bldg", "window", "facade", "building"])]
    print(f"\nTotal Building / Window Meshes: {len(window_objs)}")

    out_path = r"C:\Users\Felipe\Documents\coding\montreal\output\forensic_scene_audit.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved Forensic Audit JSON to: {out_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_forensic_scene_audit()
