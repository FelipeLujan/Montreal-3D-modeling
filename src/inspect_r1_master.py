"""
src/inspect_r1_master.py
Inspection script for Requirement R1:
- Hidden proxy meshes analysis
- Notre-Dame & Place d'Armes plaza/ground slabs analysis
- Ground/street thickness, normals, and continuous 3D collider analysis
"""
import sys
import os
import json
import bpy
import bmesh
from mathutils import Vector
from collections import defaultdict

def run_inspection():
    print("=" * 80)
    print("R1 INVESTIGATION: MONTREAL MASTER BLEND DEEP AUDIT")
    print("=" * 80)

    # 1. SCENE INVENTORY & HIDDEN OBJECTS
    all_objs = list(bpy.data.objects)
    mesh_objs = [o for o in all_objs if o.type == 'MESH']
    visible_mesh_objs = [o for o in mesh_objs if not o.hide_render]
    hidden_render_objs = [o for o in mesh_objs if o.hide_render]
    hidden_viewport_objs = [o for o in mesh_objs if o.hide_viewport]
    hidden_either = [o for o in mesh_objs if o.hide_render or o.hide_viewport]

    print(f"\n1. OBJECT INVENTORY:")
    print(f"Total Objects: {len(all_objs)}")
    print(f"Total Mesh Objects: {len(mesh_objs)}")
    print(f"Visible in Render: {len(visible_mesh_objs)}")
    print(f"Hidden in Render: {len(hidden_render_objs)}")
    print(f"Hidden in Viewport: {len(hidden_viewport_objs)}")
    print(f"Hidden in Render OR Viewport: {len(hidden_either)}")

    # Categorize hidden meshes
    categories = defaultdict(list)
    for o in hidden_render_objs:
        nl = o.name.lower()
        if "context_building_" in nl:
            categories["Context_Building_*"].append(o.name)
        elif "basilica" in nl:
            categories["Basilica_*"].append(o.name)
        elif "seminaire" in nl or "sem_" in nl:
            categories["Seminaire_*"].append(o.name)
        elif "bmo" in nl or "pantheon" in nl or "beauxarts" in nl:
            categories["BMO_*"].append(o.name)
        elif "aldred" in nl:
            categories["Aldred_*"].append(o.name)
        elif "nylife" in nl or "newyorklife" in nl:
            categories["NYLife_*"].append(o.name)
        elif "duluth" in nl:
            categories["Duluth_*"].append(o.name)
        elif "500_place_darmes" in nl or "tower_500" in nl:
            categories["Tower_500_*"].append(o.name)
        elif "satellite" in nl or "ortho" in nl:
            categories["Satellite_Ortho_*"].append(o.name)
        elif "streetscape" in nl or "streets_and_sidewalks" in nl:
            categories["Legacy_Streetscape_*"].append(o.name)
        elif "ground" in nl:
            categories["Ground_Plane_*"].append(o.name)
        elif "bldg_" in nl:
            categories["Other_Bldg_*"].append(o.name)
        else:
            categories["Other"].append(o.name)

    print("\nHidden in Render Breakdown:")
    total_cat_objs = 0
    for cat, objs in sorted(categories.items(), key=lambda x: -len(x[1])):
        print(f"  {cat}: {len(objs)} objects")
        total_cat_objs += len(objs)
        if len(objs) <= 10:
            print(f"    -> {', '.join(objs)}")
        else:
            print(f"    -> e.g. {', '.join(objs[:5])} ... (+{len(objs)-5} more)")

    # Collections holding hidden objects
    print("\nCollections containing hidden mesh objects:")
    col_counts = defaultdict(int)
    for o in hidden_render_objs:
        for c in o.users_collection:
            col_counts[c.name] += 1
    for cname, cnt in sorted(col_counts.items(), key=lambda x: -x[1]):
        print(f"  Collection '{cname}': {cnt} hidden objects")

    # 2. PLACE D'ARMES & NOTRE-DAME BASILICA GROUND / PLAZA OBJECTS
    print("\n" + "=" * 80)
    print("2. PLACE D'ARMES & NOTRE-DAME GROUND / PLAZA OBJECTS AUDIT")
    print("=" * 80)

    target_names = [
        "Plaza_Main_Dark_Granite_Slab",
        "Plaza_Basilica_Semicircular_Apron",
        "Sem_Forecourt_Paving",
        "Basilica_Stepped_Stone_Parvis",
        "Roadbed_Rue_Notre_Dame",
        "District_Sidewalks_Raised",
        "District_Curbs_3D",
        "District_Crosswalks_And_Markings",
        "MTL_VM_0001_Place_dArmes_Base",
        "Ground_Street_Asphalt_Base",
    ]

    # Also search for any object with 'plaza', 'apron', 'parvis', 'notre_dame', 'seminaire' in name
    extra_names = set()
    for o in bpy.data.objects:
        nl = o.name.lower()
        if any(k in nl for k in ["plaza", "apron", "parvis", "sem_", "seminaire", "notre_dame"]):
            extra_names.add(o.name)

    all_survey_names = list(dict.fromkeys(target_names + list(extra_names)))
    
    print(f"\nDetailed info on Place d'Armes & Notre-Dame Ground/Plaza Objects:")
    for name in all_survey_names:
        o = bpy.data.objects.get(name)
        if not o:
            # Check partial match
            matches = [obj.name for obj in bpy.data.objects if name.lower() in obj.name.lower()]
            if matches:
                print(f"[MISSING EXACT] '{name}' (Did you mean: {matches[:3]}?)")
            else:
                print(f"[NOT FOUND] '{name}'")
            continue
        
        if o.type != 'MESH' or not o.data:
            print(f"[NON-MESH] '{name}': type={o.type}")
            continue

        me = o.data
        mw = o.matrix_world
        bb = [mw @ Vector(c) for c in o.bound_box]
        min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
        min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)
        min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
        
        mats = [m.name for m in me.materials if m]
        
        # Check face normals and thickness
        up_faces = []
        down_faces = []
        vert_faces = []
        other_faces = []
        rot_3x3 = mw.to_3x3()

        for p in me.polygons:
            wn = (rot_3x3 @ p.normal).normalized()
            wc = mw @ p.center
            if wn.z > 0.7:
                up_faces.append((wc.z, p.area))
            elif wn.z < -0.7:
                down_faces.append((wc.z, p.area))
            elif abs(wn.z) <= 0.1:
                vert_faces.append((wc.z, p.area))
            else:
                other_faces.append((wc.z, p.area))

        up_z_vals = [f[0] for f in up_faces]
        avg_up_z = sum(up_z_vals) / len(up_z_vals) if up_z_vals else 0.0
        min_up_z = min(up_z_vals) if up_z_vals else 0.0
        max_up_z = max(up_z_vals) if up_z_vals else 0.0

        is_single_sided = (len(down_faces) == 0 and len(vert_faces) == 0)
        thickness = (max_z - min_z)

        print(f"\n--- Object: '{o.name}' ---")
        print(f"  Collections: {[c.name for c in o.users_collection]}")
        print(f"  Visibility: hide_render={o.hide_render}, hide_viewport={o.hide_viewport}")
        print(f"  Bounding Box: X=[{min_x:.2f}, {max_x:.2f}], Y=[{min_y:.2f}, {max_y:.2f}], Z=[{min_z:.3f}, {max_z:.3f}] (Δz={thickness:.3f}m)")
        print(f"  Materials: {mats}")
        print(f"  Geometry: verts={len(me.vertices)}, faces={len(me.polygons)}")
        print(f"  Face Breakdown: Up={len(up_faces)}, Down={len(down_faces)}, Vertical/Sides={len(vert_faces)}, Other={len(other_faces)}")
        print(f"  Upward Faces Z range: [{min_up_z:.3f} .. {max_up_z:.3f}] (avg={avg_up_z:.3f})")
        print(f"  Solid 3D vs 2D Plane: {'2D SINGLE-SIDED PLANE' if is_single_sided else '3D SOLID/EXTRUDED SLAB'}")

    # 3. INTER-OBJECT OVERLAPS & Z-PROXIMITY AROUND PLACE D'ARMES
    print("\n" + "=" * 80)
    print("3. OVERLAP ANALYSIS BETWEEN PLACE D'ARMES & NOTRE-DAME SLABS")
    print("=" * 80)

    # Inspect pairs among visible ground/plaza objects in Place d'Armes region
    # Region approx: X in [-100, 50], Y in [-80, 50]
    pda_objs = []
    for o in visible_mesh_objs:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
        min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)
        min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
        if max_x > -100 and min_x < 50 and max_y > -80 and min_y < 50 and min_z < 1.0 and max_z > -1.0:
            pda_objs.append(o)

    print(f"Found {len(pda_objs)} visible meshes intersecting Place d'Armes region [-100..50, -80..50, -1..1]:")
    for o in pda_objs:
        print(f"  - {o.name}")

    # Check upward-facing face collisions among these objects
    pda_faces = []
    for o in pda_objs:
        me = o.data
        mw = o.matrix_world
        rot_3x3 = mw.to_3x3()
        mats = [m.name for m in me.materials if m]
        for p in me.polygons:
            wn = (rot_3x3 @ p.normal).normalized()
            if wn.z > 0.88 and p.area > 0.5:
                wc = mw @ p.center
                if -0.30 <= wc.z <= 0.60:
                    xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                    ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                    mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                    pda_faces.append({
                        "obj": o.name,
                        "poly_idx": p.index,
                        "z": wc.z,
                        "x_min": min(xs), "x_max": max(xs),
                        "y_min": min(ys), "y_max": max(ys),
                        "mat": mat_name,
                        "area": p.area
                    })

    print(f"\nCandidate upward ground/plaza faces in Place d'Armes: {len(pda_faces)}")
    overlaps_found = []
    for i in range(len(pda_faces)):
        f1 = pda_faces[i]
        for j in range(i + 1, len(pda_faces)):
            f2 = pda_faces[j]
            if f1["obj"] == f2["obj"]:
                continue
            dz = abs(f1["z"] - f2["z"])
            if dz < 0.08:  # within 8cm
                ox = max(0.0, min(f1["x_max"], f2["x_max"]) - max(f1["x_min"], f2["x_min"]))
                oy = max(0.0, min(f1["y_max"], f2["y_max"]) - max(f1["y_min"], f2["y_min"]))
                overlap_area = ox * oy
                if overlap_area > 0.5:
                    overlaps_found.append((f1, f2, dz, overlap_area))

    print(f"Found {len(overlaps_found)} overlapping upward face pairs with |Δz| < 0.08m & area > 0.5m² in Place d'Armes:")
    overlap_pairs_summary = defaultdict(int)
    for f1, f2, dz, area in overlaps_found:
        pair_key = tuple(sorted([f1["obj"], f2["obj"]]))
        overlap_pairs_summary[pair_key] += 1
    for pair, cnt in overlap_pairs_summary.items():
        print(f"  {pair[0]} <==> {pair[1]}: {cnt} overlapping face pairs")

    # 4. DISTRICT-WIDE GROUND/STREET SOLID COLLIDER SURVEY
    print("\n" + "=" * 80)
    print("4. DISTRICT-WIDE GROUND / STREET SOLID COLLIDER SURVEY")
    print("=" * 80)

    # Check all Roadbeds, District_Sidewalks_Raised, District_Curbs_3D, Plazas, Base
    street_mesh_names = [o.name for o in visible_mesh_objs if any(k in o.name.lower() for k in [
        "roadbed_", "district_sidewalk", "district_curb", "district_crosswalk", "ground_", "plaza_"
    ])]
    print(f"Visible ground/street network objects ({len(street_mesh_names)}):")
    for sname in street_mesh_names:
        o = bpy.data.objects[sname]
        me = o.data
        mw = o.matrix_world
        bb = [mw @ Vector(c) for c in o.bound_box]
        min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
        thick = max_z - min_z
        # Check normals
        down_cnt = sum(1 for p in me.polygons if (mw.to_3x3() @ p.normal).normalized().z < -0.5)
        up_cnt = sum(1 for p in me.polygons if (mw.to_3x3() @ p.normal).normalized().z > 0.5)
        vert_cnt = sum(1 for p in me.polygons if abs((mw.to_3x3() @ p.normal).normalized().z) <= 0.2)
        print(f"  {sname}: Z=[{min_z:.3f}..{max_z:.3f}] (Δz={thick:.3f}m) | up={up_cnt}, down={down_cnt}, vert={vert_cnt} | faces={len(me.polygons)}")

    # Check if a continuous solid 3D ground base mesh exists
    base_objs = [o.name for o in all_objs if "ground" in o.name.lower() or "base" in o.name.lower()]
    print(f"\nAll objects with 'ground' or 'base' in scene ({len(base_objs)}):")
    for bname in base_objs:
        o = bpy.data.objects[bname]
        print(f"  {bname}: type={o.type}, hide_render={o.hide_render}, hide_viewport={o.hide_viewport}")

if __name__ == "__main__":
    run_inspection()
