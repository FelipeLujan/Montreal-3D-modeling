#!/usr/bin/env python3
"""
High-Poly 3D Architecture, Monumental Steel Cantilever Bridge & Waterfront Modeler — Block `MTL-VM-0039`
(`Pont Jacques-Cartier Monumental Steel Cantilever Bridge & Pied-du-Courant Heritage Park`)
"""

import os
import sys
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.blender_lib import (
    clear_scene,
    setup_world_sky,
    load_dossier,
    apply_world_box_uv,
    build_ground_and_streets,
    build_corridor_material_palette,
    build_corridor_context_buildings,
    build_corridor_foliage_and_props,
    add_box_local,
    add_cylinder_along,
    append_kit_object,
    export_block_artifacts,
)

BLOCK_ID = "MTL-VM-0039"


def build_jacques_cartier_bridge_and_port(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Models the monumental green-painted steel cantilever truss spans and stone/concrete piers of
    Pont Jacques-Cartier (`bridge_green_steel`), the Port of Montreal multi-track intermodal rail yard
    and warehouse roofs seen in `satellite_topdown.png`, and the fluted concrete industrial facade
    along Rue Notre-Dame Est seen in Camera 1 (`Pont_Jacques_Cartier_Main_Span_South`).
    """
    mesh = bpy.data.meshes.new("MTL_VM_0039_JacquesCartier_and_Port")
    obj = bpy.data.objects.new("MTL_VM_0039_JacquesCartier_and_Port", mesh)
    col.objects.link(obj)
    for k in (
        "bridge_green_steel",   # 0: Iconic Pont Jacques-Cartier Green Painted Steel Truss
        "concrete_podium",      # 1: Fluted Precast Concrete Industrial Wall & Bridge Piers
        "roof_bitumen",         # 2: Dark Bitumen Port Warehouse Roofs
        "roof_light_gravel",    # 3: Light Gravel Warehouse Roofs
        "dark_glass",           # 4: Upper Clerestory Glazing
        "white_trim",           # 5: White Road Markings & Roof Parapets
        "dark_metal",           # 6: Steel Rail Tracks, Corrugated Upper Cladding & Lamp Poles
        "sandstone_brick",      # 7: Orange/Red Intermodal Freight Containers
    ):
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    uz = Vector((0.0, 0.0, 1.0))
    f_corr = Vector((math.sin(math.radians(14.0)), math.cos(math.radians(14.0)), 0.0)).normalized()
    r_corr = Vector((f_corr.y, -f_corr.x, 0.0)).normalized()

    # 1. Port Industrial Warehouses on West Half of Satellite Top-Down (`X = 695..755, Y = 1320..1455`)
    wh_c = Vector((725.0, 1389.0, 0.0))
    add_box_local(bm, wh_c - r_corr * 14.0 + uz * 7.5, r_corr, f_corr, uz, 48.0, 128.0, 15.0, mat_idx=1)
    add_box_local(bm, wh_c - r_corr * 14.0 + uz * 15.1, r_corr, f_corr, uz, 46.5, 126.0, 0.25, mat_idx=2)
    add_box_local(bm, wh_c + f_corr * 42.0 + r_corr * 8.0 + uz * 8.5, r_corr, f_corr, uz, 26.0, 44.0, 17.0, mat_idx=7)
    add_box_local(bm, wh_c + f_corr * 42.0 + r_corr * 8.0 + uz * 17.1, r_corr, f_corr, uz, 24.5, 42.5, 0.25, mat_idx=3)

    # 2. Multi-Track Intermodal Rail Yard & Freight Train (`X = 755..815, Y = 1320..1455`)
    ry_c = Vector((782.0, 1389.0, 0.0))
    add_box_local(bm, ry_c + uz * 0.06, r_corr, f_corr, uz, 44.0, 142.0, 0.12, mat_idx=3)
    for t_i in range(-5, 5):
        add_box_local(bm, ry_c + r_corr * (t_i * 3.6) + uz * 0.14, r_corr, f_corr, uz, 1.45, 140.0, 0.08, mat_idx=6)
    for c_step in range(-5, 6):
        for t_s in (-10.8, -7.2, -3.6):
            cp = ry_c + r_corr * t_s + f_corr * (c_step * 12.0)
            add_box_local(bm, cp + uz * 1.65, r_corr, f_corr, uz, 2.45, 11.0, 2.65, mat_idx=7 if (c_step + int(t_s)) % 2 == 0 else 5)

    # 3. Monumental Pont Jacques-Cartier Green Steel Cantilever Bridge Span (`Y ~ 1435..1495`, rising from NW to SE across the harbour)
    b_start = Vector((580.0, 1490.0, 28.0))
    b_end = Vector((860.0, 1395.0, 46.0))
    b_vec = b_end - b_start
    b_len = b_vec.length
    b_dir = b_vec / b_len
    b_right = Vector((b_dir.y, -b_dir.x, 0.0)).normalized()
    # Bridge highway deck (5 lanes + pedestrian walkways, width = 22.0m)
    n_b_segs = 18
    for s_i in range(n_b_segs):
        t0 = s_i / n_b_segs
        t1 = (s_i + 1) / n_b_segs
        p0 = b_start.lerp(b_end, t0)
        p1 = b_start.lerp(b_end, t1)
        pm = p0.lerp(p1, 0.5)
        seg_l = (p1 - p0).length
        # Roadway deck & underside steel floor beams
        add_box_local(bm, pm, b_right, b_dir, uz, 22.0, seg_l + 0.2, 1.4, mat_idx=2)
        add_box_local(bm, pm - uz * 1.8, b_right, b_dir, uz, 22.6, seg_l + 0.2, 2.2, mat_idx=0)
        # Overhead Warren/Cantilever Steel Truss Chords, Verticals & Diagonals on both sides
        truss_h = 14.0 + 8.0 * math.sin(math.pi * (t0 + t1) * 0.5)
        for side_t in (-10.4, 10.4):
            off_r = b_right * side_t
            # Vertical posts
            add_cylinder_along(bm, p0 + off_r, p0 + off_r + uz * truss_h, 0.48, 0.45, segs=8, mat_idx=0)
            # Top chord
            add_cylinder_along(bm, p0 + off_r + uz * truss_h, p1 + off_r + uz * truss_h, 0.55, 0.55, segs=8, mat_idx=0)
            # Diagonal X-bracing
            add_cylinder_along(bm, p0 + off_r, p1 + off_r + uz * truss_h, 0.36, 0.36, segs=8, mat_idx=0)
            add_cylinder_along(bm, p0 + off_r + uz * truss_h, p1 + off_r, 0.36, 0.36, segs=8, mat_idx=0)
        # Overhead lateral sway-bracing portal every 2 bays
        if s_i % 2 == 0:
            add_cylinder_along(bm, p0 - b_right * 10.4 + uz * truss_h, p0 + b_right * 10.4 + uz * truss_h, 0.42, 0.42, segs=8, mat_idx=0)
        # Massive concrete bridge support piers every 4 bays
        if s_i in (3, 8, 13):
            for p_side in (-8.5, 8.5):
                pier_base = Vector((p0.x, p0.y, 0.0)) + b_right * p_side
                add_box_local(bm, pier_base + uz * (p0.z * 0.5), b_right, b_dir, uz, 3.6, 5.2, p0.z, mat_idx=1)

    # 4. Camera 1 Foreground (`Pont_Jacques_Cartier_Main_Span_South`: pos=(611.632, 1383.253), hdg=135°)
    # Shows the long fluted brutalist concrete industrial wall with vertical ribs & dark corrugated penthouse on the left!
    cam1 = Vector((611.632, 1383.253, 0.0))
    f1 = Vector((math.sin(math.radians(135.0)), math.cos(math.radians(135.0)), 0.0)).normalized()
    r1 = Vector((f1.y, -f1.x, 0.0)).normalized()
    # Concrete sidewalk & curb along Camera 1
    add_box_local(bm, cam1 + f1 * 14.0 + uz * 0.12, r1, f1, uz, 36.0, 28.0, 0.24, mat_idx=1)
    # Fluted precast concrete industrial building across Camera 1 (dist = 11.5m, Z = 0..8.8m)
    w_c = cam1 + f1 * 12.5 + r1 * 2.0
    add_box_local(bm, w_c + uz * 4.4, r1, f1, uz, 36.0, 3.2, 8.8, mat_idx=1)
    for fl_k in range(-28, 29):
        fp = cam1 + f1 * 10.85 + r1 * (2.0 + fl_k * 0.62)
        add_box_local(bm, fp + uz * 4.4, r1, f1, uz, 0.14, 0.22, 8.6, mat_idx=1)
    # Upper dark corrugated penthouse on the left (V1..V2, H1..H3 in Camera 1)
    pent_c = cam1 + f1 * 11.5 - r1 * 11.5
    add_box_local(bm, pent_c + uz * 10.8, r1, f1, uz, 10.5, 4.5, 4.2, mat_idx=6)
    add_box_local(bm, pent_c - f1 * 2.3 + uz * 9.8, r1, f1, uz, 9.8, 0.15, 1.8, mat_idx=4)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.25)


def main():
    print(f"\n=== Building {BLOCK_ID}: Pont Jacques-Cartier & Pied-du-Courant ===")
    clear_scene()
    setup_world_sky()
    dossier = load_dossier(BLOCK_ID)

    owned_col = bpy.data.collections.new(f"{BLOCK_ID}_Owned")
    bpy.context.scene.collection.children.link(owned_col)

    mats = build_corridor_material_palette()
    build_ground_and_streets(owned_col, dossier)
    build_jacques_cartier_bridge_and_port(owned_col, dossier, mats)
    build_corridor_context_buildings(owned_col, dossier, mats)

    extra_trees = [
        (745.0, 1340.0, 1.18),
        (748.0, 1365.0, 1.24),
        (752.0, 1390.0, 1.20),
        (755.0, 1412.0, 1.28),
    ]
    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=55)
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Build Successfully ===")


if __name__ == "__main__":
    main()
