#!/usr/bin/env python3
"""
High-Poly 3D Architecture, Heritage Brewery & Waterfront Modeler — Block `MTL-VM-0040`
(`Ancienne Brasserie Molson Heritage Waterfront, Clocktower & Quai des Convoyeurs`)
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

BLOCK_ID = "MTL-VM-0040"


def build_molson_brewery_and_rail_corridor(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Models the historic Ancienne Brasserie Molson red-brick industrial complex (`X = 590..655, Y = 1020..1155`),
    the Port of Montreal multi-track rail yard with colorful intermodal freight containers (`X = 640..695, Y = 1020..1155`),
    Rue Notre-Dame Est & residential brick/limestone apartment complex with rusticated white ground floor and arched upper windows
    seen in Camera 1 (`Molson_Brewery_Clocktower_Facade`), and the St. Lawrence River waterfront apron.
    """
    mesh = bpy.data.meshes.new("MTL_VM_0040_Molson_and_RailYard")
    obj = bpy.data.objects.new("MTL_VM_0040_Molson_and_RailYard", mesh)
    col.objects.link(obj)
    for k in (
        "red_brick",            # 0: Molson Heritage Red Brick & Residential Upper Facade (`red_bricks_04`)
        "tan_limestone",        # 1: Rusticated Cream/Tan Limestone Ground Plinth & Vertical Pilasters (`sandstone_blocks_04`)
        "roof_bitumen",         # 2: Dark Bitumen Industrial Roofs
        "roof_light_gravel",    # 3: Light Gravel Industrial Roofs
        "dark_glass",           # 4: Recessed Multi-Pane Arched Window Glass
        "white_trim",           # 5: White Cornice, Pilaster Trim & Roof Dividers
        "dark_metal",           # 6: Steel Rail Tracks, Canopies & Window Mullions
        "sandstone_brick",      # 7: Terracotta/Orange Freight Containers
        "copper_verdigris",     # 8: Molson Clocktower Copper Pyramid Roof
    ):
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    uz = Vector((0.0, 0.0, 1.0))
    # Corridor orientation along Rue Notre-Dame Est / Rail Yard (~19° East of North)
    f_corr = Vector((math.sin(math.radians(19.0)), math.cos(math.radians(19.0)), 0.0)).normalized()
    r_corr = Vector((f_corr.y, -f_corr.x, 0.0)).normalized()

    # 1. Molson Industrial Warehouse & Stepped Brewery Halls on West Side (V1..V4, H1..H8 in Satellite Top-Down)
    mol_c = Vector((618.0, 1088.0, 0.0))
    # Main North Hall (light gravel roof)
    add_box_local(bm, mol_c + f_corr * 38.0 - r_corr * 6.0 + uz * 9.0, r_corr, f_corr, uz, 54.0, 56.0, 18.0, mat_idx=0)
    add_box_local(bm, mol_c + f_corr * 38.0 - r_corr * 6.0 + uz * 18.1, r_corr, f_corr, uz, 52.0, 54.0, 0.25, mat_idx=3)
    # Central Brewery Hall (medium gravel/bitumen roof with white parapet dividers)
    add_box_local(bm, mol_c - r_corr * 8.0 + uz * 10.5, r_corr, f_corr, uz, 58.0, 38.0, 21.0, mat_idx=0)
    add_box_local(bm, mol_c - r_corr * 8.0 + uz * 21.1, r_corr, f_corr, uz, 56.0, 36.0, 0.25, mat_idx=2)
    add_box_local(bm, mol_c - r_corr * 8.0 + uz * 21.25, r_corr, f_corr, uz, 58.2, 0.65, 0.45, mat_idx=5)
    # South 4-Bay Segmented Warehouse Roof (V1..V4, H5..H8 in Satellite Top-Down)
    for b_idx in range(-2, 2):
        bay_p = mol_c - f_corr * 34.0 + r_corr * (b_idx * 13.5 + 2.0)
        add_box_local(bm, bay_p + uz * 8.0, r_corr, f_corr, uz, 12.8, 42.0, 16.0, mat_idx=0)
        add_box_local(bm, bay_p + uz * 16.1, r_corr, f_corr, uz, 12.2, 40.5, 0.22, mat_idx=2 if b_idx % 2 == 0 else 3)
        add_box_local(bm, bay_p + r_corr * 6.4 + uz * 16.25, r_corr, f_corr, uz, 0.45, 42.2, 0.45, mat_idx=5)

    # Molson Iconic Heritage Red-Brick Clocktower (X = 602.0, Y = 1112.0, height = 38.0m)
    clk_c = Vector((602.0, 1112.0, 0.0))
    add_box_local(bm, clk_c + uz * 16.0, r_corr, f_corr, uz, 11.5, 11.5, 32.0, mat_idx=0)
    add_box_local(bm, clk_c + uz * 32.5, r_corr, f_corr, uz, 12.2, 12.2, 1.2, mat_idx=5)
    add_cylinder_along(bm, clk_c + uz * 33.1, clk_c + uz * 39.5, 7.8, 0.4, segs=4, mat_idx=8, cap_ends=True)

    # 2. Port of Montreal Multi-Track Rail Yard & Intermodal Freight Train (Center strip V4..V6, H1..H8 in Satellite)
    rail_c = Vector((656.0, 1088.0, 0.0))
    add_box_local(bm, rail_c + uz * 0.06, r_corr, f_corr, uz, 22.0, 145.0, 0.12, mat_idx=3)
    for tr_i in range(-3, 4):
        tr_off = r_corr * (tr_i * 2.8)
        add_box_local(bm, rail_c + tr_off + uz * 0.14, r_corr, f_corr, uz, 1.45, 142.0, 0.08, mat_idx=6)
    # Colorful intermodal freight containers (red/orange and white) along tracks -1 and 0
    for c_step in range(-5, 6):
        for tr_s, m_cont in [(-2.8, 7), (0.0, 5 if c_step % 2 == 0 else 7)]:
            cp = rail_c + r_corr * tr_s + f_corr * (c_step * 12.2)
            add_box_local(bm, cp + uz * 1.65, r_corr, f_corr, uz, 2.45, 11.2, 2.65, mat_idx=m_cont)

    # 3. Camera 1 Hero Building (`Molson_Brewery_Clocktower_Facade`: pos=(694.026, 1075.839), hdg=125°)
    # Camera 1 looks SE at the 6-story red-brick & white-pilaster heritage loft building with rusticated ground floor & dark metal entrance canopies!
    cam1 = Vector((694.026, 1075.839, 0.0))
    f1 = Vector((math.sin(math.radians(125.0)), math.cos(math.radians(125.0)), 0.0)).normalized()
    r1 = Vector((f1.y, -f1.x, 0.0)).normalized()
    # Foreground concrete sidewalk & granite curb in front of Camera 1 (dist = 3.5..8.5m)
    add_box_local(bm, cam1 + f1 * 6.2 + uz * 0.12, r1, f1, uz, 36.0, 5.2, 0.24, mat_idx=1)
    # Heritage Red-Brick Loft Building (dist = 9.0m..28.0m, Z = 0..22.5m)
    bldg1_c = cam1 + f1 * 18.5
    # Ground floor white/cream rusticated limestone plinth (Z = 0..4.4m) with recessed dark entrance portals
    add_box_local(bm, bldg1_c - f1 * 8.2 + uz * 2.2, r1, f1, uz, 38.0, 2.6, 4.4, mat_idx=1)
    for p_off in (-2.2, 5.2):
        # Recessed dark lobby portal & projecting curved dark-metal entrance canopy
        port_p = cam1 + f1 * 9.2 + r1 * p_off
        add_box_local(bm, port_p + uz * 1.9, r1, f1, uz, 4.8, 1.8, 3.6, mat_idx=4)
        add_box_local(bm, port_p - f1 * 1.2 + uz * 3.85, r1, f1, uz, 5.2, 2.4, 0.28, mat_idx=6)
    # Upper 5 floors of red brick (`red_bricks_04`) with vertical white limestone pilasters (`Z = 4.4..22.5m`)
    add_box_local(bm, bldg1_c + uz * 13.4, r1, f1, uz, 38.0, 18.5, 18.0, mat_idx=0)
    add_box_local(bm, bldg1_c + uz * 22.5, r1, f1, uz, 36.5, 17.0, 0.25, mat_idx=3)
    for pil_x in (-14.0, -6.5, 1.5, 9.0, 16.0):
        add_box_local(bm, cam1 + f1 * 9.1 + r1 * pil_x + uz * 13.4, r1, f1, uz, 1.15, 0.35, 18.0, mat_idx=5)
    # Floor-by-floor multi-pane arched windows across the front facade of Camera 1
    for fl_i in range(4):
        z_w = 6.2 + fl_i * 3.8
        for w_x in (-11.5, -9.0, -4.0, -1.2, 4.0, 6.6, 11.5, 13.8):
            wp = cam1 + f1 * 9.15 + r1 * w_x + uz * z_w
            add_box_local(bm, wp, r1, f1, uz, 1.85, 0.22, 2.35, mat_idx=4)
            add_box_local(bm, wp - f1 * 0.08, r1, f1, uz, 0.08, 0.12, 2.35, mat_idx=6)
            add_box_local(bm, wp - f1 * 0.10 - uz * 1.22, r1, f1, uz, 2.05, 0.28, 0.16, mat_idx=1)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.25)


def main():
    print(f"\n=== Building {BLOCK_ID}: Ancienne Brasserie Molson & Waterfront ===")
    clear_scene()
    setup_world_sky()
    dossier = load_dossier(BLOCK_ID)

    owned_col = bpy.data.collections.new(f"{BLOCK_ID}_Owned")
    bpy.context.scene.collection.children.link(owned_col)

    mats = build_corridor_material_palette()
    build_ground_and_streets(owned_col, dossier)
    build_molson_brewery_and_rail_corridor(owned_col, dossier, mats)
    build_corridor_context_buildings(owned_col, dossier, mats)

    extra_trees = [
        (615.0, 1025.0, 1.25),
        (625.0, 1022.0, 1.32),
        (635.0, 1028.0, 1.28),
        (642.0, 1042.0, 1.18),
        (648.0, 1062.0, 1.22),
    ]
    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=65)
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Build Successfully ===")


if __name__ == "__main__":
    main()
