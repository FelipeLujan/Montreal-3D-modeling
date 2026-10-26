#!/usr/bin/env python3
"""
High-Poly 3D Architecture, Heritage Industrial Gasholder & Streetscape Modeler — Block `MTL-VM-0041`
(`Griffintown Heritage Block — New City Gas Victorian Gasholder Complex, REM Viaduct & Rue Ottawa`)
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

BLOCK_ID = "MTL-VM-0041"


def _add_wall_fenestration_grid(
    bm: bmesh.types.BMesh,
    wall_base_center: Vector,
    u_tan: Vector,
    u_out: Vector,
    width: float,
    height: float,
    n_floors: int,
    n_cols: int,
    glass_mat: int = 7,
    frame_mat: int = 9,
    sill_mat: int = 1,
):
    """Populates a vertical exterior wall face with floor-by-floor 3D windows, frames, sills & spandrel courses."""
    uz = Vector((0.0, 0.0, 1.0))
    floor_h = (height - 0.65) / max(1, n_floors)
    bay_w = width / max(1, n_cols)
    win_w = min(2.1, bay_w * 0.56)
    win_h = min(1.85, floor_h * 0.54)

    for r_fl in range(n_floors):
        z_fl = 0.45 + (r_fl + 0.52) * floor_h
        sp_pos = wall_base_center + u_out * 0.08 + uz * (0.35 + r_fl * floor_h)
        add_box_local(bm, sp_pos, u_tan, u_out, uz, width + 0.08, 0.16, 0.20, mat_idx=sill_mat)
        for c_bay in range(n_cols):
            x_off = -0.5 * width + (c_bay + 0.5) * bay_w
            w_pos = wall_base_center + u_tan * x_off + uz * z_fl
            add_box_local(bm, w_pos + u_out * 0.06, u_tan, u_out, uz, win_w + 0.22, 0.12, win_h + 0.20, mat_idx=frame_mat)
            add_box_local(bm, w_pos + u_out * 0.11, u_tan, u_out, uz, win_w, 0.08, win_h, mat_idx=glass_mat)
            add_box_local(bm, w_pos + u_out * 0.15 - uz * (win_h * 0.5 + 0.08), u_tan, u_out, uz, win_w + 0.32, 0.24, 0.14, mat_idx=sill_mat)


def _sanitize_street_normals_and_coplanar_slabs():
    """
    Eliminates inverted (-Z) road/walkway ribbon normals caused by `bmesh.ops.recalc_face_normals`
    on open 2D street meshes and guarantees strictly monotonic Z offsets so zero black coplanar patches appear.
    """
    for obj_name in ("MTL_OSM_Streets_and_Walkways", "MTL_OSM_Parks_Grass"):
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        for idx_f, f in enumerate(bm.faces):
            f.normal_update()
            if f.normal.z < 0.0:
                f.normal_flip()
            if obj_name == "MTL_OSM_Streets_and_Walkways":
                # Keep vehicular asphalt at Z = 0.032..0.068m and footways at Z = 0.072..0.110m (strictly monotonic)
                base_z = 0.032 if f.material_index == 0 else 0.075
                dz = (idx_f % 180) * 0.00018
                for v in f.verts:
                    v.co.z = base_z + dz
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()


def _add_pitched_roof_hall(
    bm: bmesh.types.BMesh,
    center_xy: Vector,
    u_len: Vector,
    u_wid: Vector,
    length: float,
    width: float,
    wall_h: float,
    ridge_h: float,
    wall_mat: int,
    base_mat: int,
    roof_mat: int,
    trim_mat: int,
):
    """Builds a 3D gabled hall with stone plinth, upper masonry walls, gable triangles, and overhanging pitched roof slabs."""
    uz = Vector((0.0, 0.0, 1.0))
    add_box_local(bm, center_xy + uz * 1.15, u_len, u_wid, uz, length + 0.16, width + 0.16, 2.1, mat_idx=base_mat)
    add_box_local(bm, center_xy + uz * (wall_h * 0.5 + 0.05), u_len, u_wid, uz, length, width, wall_h - 0.10, mat_idx=wall_mat)

    hl = length * 0.5
    hw = width * 0.5
    for s_end in (-1.0, 1.0):
        end_c = center_xy + u_len * (s_end * hl)
        v_l = bm.verts.new(end_c - u_wid * hw + uz * wall_h)
        v_r = bm.verts.new(end_c + u_wid * hw + uz * wall_h)
        v_top = bm.verts.new(end_c + uz * ridge_h)
        try:
            f = bm.faces.new((v_l, v_r, v_top) if s_end > 0 else (v_r, v_l, v_top))
            f.material_index = wall_mat
        except ValueError:
            pass

    rise = ridge_h - wall_h
    run = hw + 0.45
    slope_w = math.hypot(run, rise)
    ang = math.atan2(rise, run)
    for side in (-1.0, 1.0):
        u_slope = (u_wid * side * math.cos(ang) + uz * math.sin(ang)).normalized()
        u_norm = (-u_wid * side * math.sin(ang) + uz * math.cos(ang)).normalized()
        slope_c = center_xy + u_wid * (side * run * 0.5) + uz * (wall_h + rise * 0.5)
        add_box_local(bm, slope_c, u_len, u_slope, u_norm, length + 0.8, slope_w, 0.28, mat_idx=roof_mat)
        eave_c = center_xy + u_wid * (side * (hw + 0.22)) + uz * (wall_h - 0.12)
        add_box_local(bm, eave_c, u_len, u_wid, uz, length + 0.8, 0.45, 0.28, mat_idx=trim_mat)


def _add_rooftop_love_me_letters(
    bm: bmesh.types.BMesh,
    hall_center: Vector,
    u_len: Vector,
    u_wid: Vector,
    wall_h: float,
    ridge_h: float,
    half_w: float,
    mat_idx: int,
):
    """Models the iconic white 'LOVE ME' block letters painted across the NE dark-slate roof slope of New City Gas."""
    uz = Vector((0.0, 0.0, 1.0))
    rise = ridge_h - wall_h
    run = half_w + 0.45
    ang = math.atan2(rise, run)
    u_down = (-u_wid * math.cos(ang) + uz * math.sin(ang)).normalized()
    u_norm = (u_wid * math.sin(ang) + uz * math.cos(ang)).normalized()
    u_char = -u_len
    slope_mid = hall_center + u_wid * (half_w * 0.48) + uz * (wall_h + rise * 0.52) + u_norm * 0.20

    def _bar(cx_char: float, cy_down: float, sx: float, sy: float):
        p = slope_mid + u_char * cx_char + u_down * cy_down
        add_box_local(bm, p, u_char, u_down, u_norm, sx, sy, 0.12, mat_idx=mat_idx)

    # E (leftmost in satellite view: x = -14.5)
    _bar(-13.2, 0.0, 0.78, 5.6)
    _bar(-14.5, -2.4, 2.6, 0.78)
    _bar(-14.3, 0.0, 2.2, 0.78)
    _bar(-14.5, 2.4, 2.6, 0.78)
    # M (x = -8.0)
    _bar(-6.2, 0.0, 0.78, 5.6)
    _bar(-8.0, 0.4, 0.78, 4.4)
    _bar(-9.8, 0.0, 0.78, 5.6)
    _bar(-8.0, 2.4, 3.8, 0.78)
    # E (x = 0.0)
    _bar(1.3, 0.0, 0.78, 5.6)
    _bar(0.0, -2.4, 2.6, 0.78)
    _bar(0.2, 0.0, 2.2, 0.78)
    _bar(0.0, 2.4, 2.6, 0.78)
    # V (x = 5.2)
    _bar(4.1, 0.4, 0.78, 4.8)
    _bar(6.3, 0.4, 0.78, 4.8)
    _bar(5.2, -2.4, 2.4, 0.78)
    # O (x = 10.6)
    _bar(9.2, 0.0, 0.78, 5.6)
    _bar(12.0, 0.0, 0.78, 5.6)
    _bar(10.6, -2.4, 2.8, 0.78)
    _bar(10.6, 2.4, 2.8, 0.78)
    # L (x = 15.6)
    _bar(16.8, 0.0, 0.78, 5.6)
    _bar(15.4, -2.4, 2.4, 0.78)


def build_new_city_gas_and_griffintown_heroes(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Constructs the 1861 New City Gas heritage complex, Lowney sur Ville towers & rooftop pools,
    elevated REM/CN railway viaduct with catenary portals, NW circular pavilion, and camera-matched
    Griffintown industrial brick & limestone facades with full 4-sided 3D fenestration.
    """
    mesh = bpy.data.meshes.new("MTL_VM_0041_Hero_Landmarks")
    obj = bpy.data.objects.new("MTL_VM_0041_Hero_Landmarks", mesh)
    col.objects.link(obj)

    palette_order = (
        "grey_limestone",        # 0: 1861 Pierre-Grise cut-limestone walls
        "tan_limestone",         # 1: Dressed tan limestone quoins, sills & cornices
        "victorian_brick",       # 2: Victorian red-brown industrial brick
        "brown_brick",           # 3: Dark brown Griffintown loft brick
        "concrete_tile_facade",  # 4: Lowney sur Ville white/light-grey glazed brick facade
        "concrete_podium",       # 5: Exposed concrete columns, slabs & viaduct piers
        "concrete_brick_wall",   # 6: Concrete block window infill panels
        "dark_glass",            # 7: Recessed industrial & residential window glazing
        "blue_glass",            # 8: Frosted/blue glass balcony railings & pool water accent
        "white_trim",            # 9: White window frames, roof lettering, pavilion & hoarding
        "dark_metal",            # 10: Dark steel mullions, banners, railings & rail tracks
        "roof_light_gravel",     # 11: Tan/beige gravel flat roof (New City Gas West wing)
        "roof_white_elastomer",  # 12: Bright white elastomer flat roof
        "roof_bitumen",          # 13: Dark slate/bitumen pitched roof ('LOVE ME' hall)
        "terracotta_vivid",      # 14: Terracotta-red pitched roof (New City Gas SE hall)
        "bridge_green_steel",    # 15: Green steel railway bridge girders
        "park_grass",            # 16: Rooftop & courtyard lawns + green recycling bins
        "water_river",           # 17: Rooftop swimming pool water
        "plaza_beige",           # 18: Courtyard & rooftop stone pavers
    )
    for k in palette_order:
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    uz = Vector((0.0, 0.0, 1.0))

    # Dominant Griffintown street grid axes from satellite & OSM:
    u_ott = Vector((0.884, -0.468, 0.0)).normalized()
    u_ann = Vector((0.468, 0.884, 0.0)).normalized()

    # ==========================================================================
    # 1. NEW CITY GAS COMPLEX (Satellite Center-North & East: X=-135..-25, Y=-1095..-1015)
    # ==========================================================================
    # 1A. West Industrial Loft Wing (Tan/beige flat roof in satellite center-left: 64m x 22m)
    ncg_west_c = Vector((-99.5, -1065.0, 0.0))
    add_box_local(bm, ncg_west_c + uz * 1.15, u_ott, u_ann, uz, 64.4, 22.4, 2.1, mat_idx=0)
    add_box_local(bm, ncg_west_c + uz * 6.85, u_ott, u_ann, uz, 64.0, 22.0, 13.5, mat_idx=2)
    add_box_local(bm, ncg_west_c + uz * 13.7, u_ott, u_ann, uz, 62.8, 20.8, 0.35, mat_idx=11)
    for rib_x in (-31.6, -10.5, 10.5, 31.6):
        add_box_local(bm, ncg_west_c + u_ott * rib_x + uz * 14.05, u_ott, u_ann, uz, 0.55, 21.8, 0.55, mat_idx=1)
    for side_y in (-10.7, 10.7):
        add_box_local(bm, ncg_west_c + u_ann * side_y + uz * 14.05, u_ott, u_ann, uz, 64.0, 0.55, 0.55, mat_idx=1)
    pent_c = ncg_west_c + u_ott * 2.5 + u_ann * 7.8 + uz * 14.9
    add_box_local(bm, pent_c, u_ott, u_ann, uz, 7.5, 5.2, 2.2, mat_idx=11)
    add_box_local(bm, pent_c - u_ott * 2.2 - u_ann * 1.2, u_ott, u_ann, uz, 2.8, 2.2, 2.4, mat_idx=14)

    # 1B. North-West White Elastomer Roof Wing (X=-102, Y=-1031, 27m x 19m)
    ncg_nw_c = Vector((-102.0, -1031.5, 0.0))
    add_box_local(bm, ncg_nw_c + uz * 5.25, u_ott, u_ann, uz, 27.0, 19.5, 10.3, mat_idx=0)
    add_box_local(bm, ncg_nw_c + uz * 10.55, u_ott, u_ann, uz, 25.8, 18.4, 0.35, mat_idx=12)
    for hx_off in (-6.5, 0.0, 6.5):
        add_box_local(bm, ncg_nw_c + u_ott * hx_off + uz * 10.85, u_ott, u_ann, uz, 0.45, 13.5, 0.35, mat_idx=10)
    add_box_local(bm, ncg_nw_c + uz * 10.85, u_ott, u_ann, uz, 16.0, 0.45, 0.35, mat_idx=10)
    add_box_local(bm, ncg_nw_c - u_ott * 14.2 + uz * 0.25, u_ott, u_ann, uz, 2.2, 14.5, 0.08, mat_idx=14)

    # 1C. North-East Dark-Slate Gabled Hall with 'LOVE ME' Roof Art (X=-64, Y=-1046, 62m x 22m)
    ncg_ne_c = Vector((-63.5, -1045.5, 0.0))
    _add_pitched_roof_hall(
        bm,
        ncg_ne_c,
        u_ott,
        u_ann,
        length=62.0,
        width=22.0,
        wall_h=12.4,
        ridge_h=16.8,
        wall_mat=0,
        base_mat=1,
        roof_mat=13,
        trim_mat=1,
    )
    _add_rooftop_love_me_letters(bm, ncg_ne_c, u_ott, u_ann, wall_h=12.4, ridge_h=16.8, half_w=11.0, mat_idx=9)
    sky_gal_c = ncg_ne_c - u_ann * 13.2
    add_box_local(bm, sky_gal_c + uz * 4.85, u_ott, u_ann, uz, 44.0, 5.2, 9.5, mat_idx=9)
    for sk_i in range(-8, 9):
        add_box_local(bm, sky_gal_c + u_ott * (sk_i * 2.4) + uz * 9.7, u_ott, u_ann, uz, 1.7, 4.4, 0.25, mat_idx=7)

    # 1D. South-East Terracotta-Red Pitched Roof Victorian Heritage Hall (X=-56, Y=-1082, 48m x 22m)
    ncg_se_c = Vector((-56.5, -1082.5, 0.0))
    _add_pitched_roof_hall(
        bm,
        ncg_se_c,
        u_ott,
        u_ann,
        length=48.0,
        width=22.5,
        wall_h=13.2,
        ridge_h=17.8,
        wall_mat=0,
        base_mat=1,
        roof_mat=14,
        trim_mat=1,
    )
    for v_off in (-9.5, 8.5):
        vc = ncg_se_c + u_ott * v_off + uz * 18.2
        add_box_local(bm, vc, u_ott, u_ann, uz, 4.2, 3.2, 1.8, mat_idx=11)
        add_box_local(bm, vc + uz * 1.0, u_ott, u_ann, uz, 4.6, 3.6, 0.25, mat_idx=9)

    # ==========================================================================
    # 2. LOWNEY SUR VILLE CONDOS & ROOFTOP POOLS (Satellite SW & S Quadrant)
    # ==========================================================================
    # 2A. Lowney sur Ville Phase 4 (South-Center: X=-98, Y=-1104, 56m x 18.5m, height=25m)
    low4_c = Vector((-98.0, -1104.5, 0.0))
    add_box_local(bm, low4_c + uz * 2.05, u_ott, u_ann, uz, 56.0, 18.8, 3.9, mat_idx=5)
    add_box_local(bm, low4_c + uz * 12.85, u_ott, u_ann, uz, 55.6, 18.4, 25.5, mat_idx=4)
    add_box_local(bm, low4_c - u_ott * 14.5 + uz * 26.6, u_ott, u_ann, uz, 25.0, 16.5, 2.0, mat_idx=12)
    add_box_local(bm, low4_c + u_ott * 12.5 + uz * 25.75, u_ott, u_ann, uz, 28.5, 17.2, 0.30, mat_idx=18)
    add_box_local(bm, low4_c + u_ott * 11.0 + u_ann * 4.2 + uz * 25.95, u_ott, u_ann, uz, 21.0, 4.8, 0.18, mat_idx=16)
    add_box_local(bm, low4_c + u_ott * 12.0 - u_ann * 2.2 + uz * 25.98, u_ott, u_ann, uz, 22.8, 4.6, 0.22, mat_idx=9)
    add_box_local(bm, low4_c + u_ott * 12.0 - u_ann * 2.2 + uz * 26.06, u_ott, u_ann, uz, 21.8, 3.8, 0.14, mat_idx=8)

    # 2B. Lowney sur Ville Phase 2 (`990 Rue Ann`, South-West: X=-144, Y=-1094, 18m x 36m along Rue Ann)
    low2_c = Vector((-144.5, -1094.0, 0.0))
    add_box_local(bm, low2_c + uz * 2.05, u_ott, u_ann, uz, 18.5, 36.0, 3.9, mat_idx=5)
    add_box_local(bm, low2_c + uz * 11.25, u_ott, u_ann, uz, 18.2, 35.6, 22.3, mat_idx=4)
    add_box_local(bm, low2_c + uz * 22.55, u_ott, u_ann, uz, 17.2, 34.4, 0.30, mat_idx=18)
    add_box_local(bm, low2_c - u_ott * 2.8 + uz * 22.75, u_ott, u_ann, uz, 5.2, 20.5, 0.22, mat_idx=9)
    add_box_local(bm, low2_c - u_ott * 2.8 + uz * 22.82, u_ott, u_ann, uz, 4.2, 19.5, 0.14, mat_idx=8)
    # Courtyard raised cleanly above street/sidewalk level (z_bot = 0.23m, z_top = 0.31m)
    cy_c = Vector((-125.0, -1107.0, 0.0))
    add_box_local(bm, cy_c + uz * 0.27, u_ott, u_ann, uz, 20.0, 26.0, 0.08, mat_idx=18)
    for gx_o in (-5.5, 0.0, 5.5):
        for gy_o in (-7.0, 0.0, 7.0):
            add_box_local(bm, cy_c + u_ott * gx_o + u_ann * gy_o + uz * 0.34, u_ott, u_ann, uz, 3.6, 4.2, 0.08, mat_idx=16)

    # ==========================================================================
    # 3. ELEVATED REM / CN RAILWAY VIADUCT (Satellite NE Quadrant) & NW PAVILION
    # ==========================================================================
    rail_p0 = Vector((-102.0, -988.0, 0.0))
    rail_p1 = Vector((-20.0, -1052.0, 0.0))
    u_rail = (rail_p1 - rail_p0).normalized()
    u_rail_perp = Vector((-u_rail.y, u_rail.x, 0.0)).normalized()
    rail_mid = (rail_p0 + rail_p1) * 0.5
    rail_len = (rail_p1 - rail_p0).length
    add_box_local(bm, rail_mid + uz * 5.8, u_rail, u_rail_perp, uz, rail_len, 16.5, 1.1, mat_idx=11)
    for s_rp in (-7.9, 7.9):
        add_box_local(bm, rail_mid + u_rail_perp * s_rp + uz * 6.65, u_rail, u_rail_perp, uz, rail_len, 0.55, 0.85, mat_idx=9)
    for tr_off in (-5.2, -1.8, 1.8, 5.2):
        add_box_local(bm, rail_mid + u_rail_perp * tr_off + uz * 6.42, u_rail, u_rail_perp, uz, rail_len, 0.22, 0.16, mat_idx=10)
    for k_pier in range(-2, 3):
        pc = rail_mid + u_rail * (k_pier * 20.0)
        for s_col in (-5.5, 5.5):
            add_box_local(bm, pc + u_rail_perp * s_col + uz * 2.75, u_rail, u_rail_perp, uz, 1.4, 1.4, 5.1, mat_idx=5)
            add_box_local(bm, pc + u_rail_perp * s_col + uz * 9.2, u_rail, u_rail_perp, uz, 0.32, 0.32, 5.8, mat_idx=10)
        add_box_local(bm, pc + uz * 11.9, u_rail, u_rail_perp, uz, 0.35, 12.2, 0.42, mat_idx=10)

    nw_pk = Vector((-137.8, -1010.5, 0.0))
    add_box_local(bm, nw_pk + uz * 0.26, u_ott, u_ann, uz, 16.0, 22.0, 0.08, mat_idx=16)
    add_box_local(bm, nw_pk - u_ann * 3.5 + uz * 0.33, u_ott, u_ann, uz, 8.5, 9.5, 0.08, mat_idx=18)
    add_cylinder_along(bm, nw_pk + uz * 0.36, nw_pk + uz * 3.6, 3.8, 3.8, segs=24, mat_idx=5, cap_ends=True)
    add_cylinder_along(bm, nw_pk + uz * 3.6, nw_pk + uz * 4.1, 5.2, 5.2, segs=28, mat_idx=12, cap_ends=True)

    # ==========================================================================
    # 4. STREET VIEW CAMERA-ALIGNED HERO FACADES & FOREGROUND PROPS (ALL 4 SIDES FENESTRATED)
    # ==========================================================================
    # CAMERA 1 (`New_City_Gas_Heritage_Gable`: pos=(-140.099, -1043.397), hdg=155°)
    cam1 = Vector((-140.099, -1043.397, 0.0))
    f1 = Vector((math.sin(math.radians(155.0)), math.cos(math.radians(155.0)), 0.0)).normalized()
    r1 = Vector((f1.y, -f1.x, 0.0)).normalized()
    c1_wall_c = cam1 + f1 * 18.0 + r1 * 8.0
    add_box_local(bm, c1_wall_c + uz * 2.5, f1, r1, uz, 34.0, 4.4, 4.8, mat_idx=3)
    add_box_local(bm, c1_wall_c + uz * 7.6, f1, r1, uz, 34.0, 4.4, 5.0, mat_idx=3)
    add_box_local(bm, c1_wall_c + uz * 10.3, f1, r1, uz, 33.6, 4.0, 0.30, mat_idx=12)
    # Front (-r1) AND Back (+r1) pilasters & industrial windows on the brown connector wing
    for side_s in (-1.0, 1.0):
        for b_idx in range(-3, 4):
            pil_p = c1_wall_c + f1 * (b_idx * 5.2) + r1 * (side_s * 2.25)
            add_box_local(bm, pil_p + uz * 5.1, f1, r1, uz, 0.78, 0.42, 10.2, mat_idx=2)
        for w_idx in range(-3, 3):
            wp = c1_wall_c + f1 * ((w_idx + 0.5) * 5.2) + r1 * (side_s * 2.22)
            add_box_local(bm, wp + uz * 7.5, f1, r1, uz, 3.2, 0.18, 2.9, mat_idx=7)
            add_box_local(bm, wp + uz * 5.95 + r1 * (side_s * 0.08), f1, r1, uz, 3.5, 0.30, 0.22, mat_idx=1)
            for m_off in (-0.95, 0.0, 0.95):
                add_box_local(bm, wp + f1 * m_off + uz * 7.5 + r1 * (side_s * 0.06), f1, r1, uz, 0.08, 0.22, 2.9, mat_idx=10)
            add_box_local(bm, wp + uz * 4.3 + r1 * (side_s * 0.08), f1, r1, uz, 3.9, 0.28, 0.62, mat_idx=5)
            add_box_local(bm, wp + uz * 2.3, f1, r1, uz, 3.1, 0.16, 2.6, mat_idx=7 if (w_idx < 0 or side_s > 0) else 1)
    # Both end walls (-f1 and +f1) of c1_wall_c
    for end_s in (-1.0, 1.0):
        _add_wall_fenestration_grid(bm, c1_wall_c + f1 * (end_s * 17.0), r1 * end_s, f1 * end_s, 4.4, 10.0, 3, 1)
    for ban_d in (10.5, 20.9):
        bp = cam1 + f1 * ban_d + r1 * 5.05 + uz * 5.2
        add_box_local(bm, bp, f1, r1, uz, 0.12, 1.10, 2.5, mat_idx=10)
    ovp_c = cam1 + f1 * 55.0 - r1 * 3.0
    add_box_local(bm, ovp_c + uz * 5.6, r1, f1, uz, 32.0, 5.2, 1.4, mat_idx=15)
    add_box_local(bm, ovp_c + uz * 4.4, r1, f1, uz, 32.0, 5.0, 1.1, mat_idx=5)
    for p_side in (-11.0, 6.0):
        add_box_local(bm, ovp_c + r1 * p_side + uz * 2.3, r1, f1, uz, 2.2, 5.0, 4.2, mat_idx=5)
        add_box_local(bm, ovp_c + r1 * p_side + uz * 8.5, r1, f1, uz, 0.28, 0.28, 4.8, mat_idx=10)
    add_box_local(bm, ovp_c - r1 * 2.5 + uz * 10.8, r1, f1, uz, 17.5, 0.28, 0.32, mat_idx=10)

    # CAMERA 2 (`Rue_Ottawa_Dalhousie_Corner`: pos=(-76.789, -1016.702), hdg=235°)
    cam2 = Vector((-76.789, -1016.702, 0.0))
    f2 = Vector((math.sin(math.radians(235.0)), math.cos(math.radians(235.0)), 0.0)).normalized()
    r2 = Vector((f2.y, -f2.x, 0.0)).normalized()
    c2_gable = cam2 + f2 * 11.2 - r2 * 3.8
    add_box_local(bm, c2_gable + uz * 2.05, r2, f2, uz, 11.6, 8.0, 3.9, mat_idx=0)
    add_box_local(bm, c2_gable + uz * 5.9, r2, f2, uz, 11.6, 8.0, 3.8, mat_idx=0)
    add_box_local(bm, c2_gable + uz * 9.8, r2, f2, uz, 11.5, 7.9, 4.0, mat_idx=2)
    add_box_local(bm, c2_gable + uz * 11.9 - f2 * 0.25, r2, f2, uz, 12.2, 8.6, 0.38, mat_idx=14)
    quoin_c = c2_gable + r2 * 5.35 - f2 * 4.02
    add_box_local(bm, quoin_c + uz * 4.0, r2, f2, uz, 0.95, 0.22, 8.0, mat_idx=1)
    door_c = c2_gable - r2 * 1.4 - f2 * 4.02
    add_box_local(bm, door_c + uz * 1.65, r2, f2, uz, 1.95, 0.24, 3.3, mat_idx=1)
    add_box_local(bm, door_c + uz * 1.55 - f2 * 0.06, r2, f2, uz, 1.35, 0.14, 2.9, mat_idx=9)
    add_box_local(bm, door_c + uz * 3.45 - f2 * 0.12, r2, f2, uz, 2.45, 0.42, 0.28, mat_idx=1)
    add_box_local(bm, door_c + uz * 4.35 - f2 * 0.08, r2, f2, uz, 1.25, 0.22, 1.25, mat_idx=1)
    win2_c = c2_gable + r2 * 2.1 - f2 * 4.02
    add_box_local(bm, win2_c + uz * 3.8, r2, f2, uz, 1.75, 0.22, 4.6, mat_idx=1)
    add_box_local(bm, win2_c + uz * 3.8 - f2 * 0.06, r2, f2, uz, 1.45, 0.14, 4.3, mat_idx=7)
    for m2_z in (2.4, 3.2, 4.0, 4.8, 5.5):
        add_box_local(bm, c2_gable + r2 * 2.1 - f2 * 4.10 + uz * m2_z, r2, f2, uz, 1.45, 0.08, 0.06, mat_idx=1)
    add_box_local(bm, win2_c + uz * 9.1 - f2 * 0.05, r2, f2, uz, 1.45, 0.18, 2.5, mat_idx=7)
    add_box_local(bm, win2_c + uz * 7.75 - f2 * 0.10, r2, f2, uz, 1.85, 0.28, 0.18, mat_idx=1)
    # Fenestrate back (+f2) and sides (-r2, +r2) of c2_gable
    _add_wall_fenestration_grid(bm, c2_gable + f2 * 4.0, -r2, f2, 11.5, 11.6, 3, 3)
    for s2_r in (-1.0, 1.0):
        _add_wall_fenestration_grid(bm, c2_gable + r2 * (s2_r * 5.8), f2 * s2_r, r2 * s2_r, 8.0, 11.6, 3, 2)
    for bx_off, b_mat in [(-3.2, 16), (-2.3, 16), (-1.3, 10), (-0.4, 10)]:
        bin_p = c2_gable + r2 * bx_off - f2 * 4.45
        add_box_local(bm, bin_p + uz * 0.55, r2, f2, uz, 0.62, 0.68, 1.10, mat_idx=b_mat)
    fence_c = cam2 + f2 * 14.5 + r2 * 7.8
    add_box_local(bm, fence_c + uz * 1.35, r2, f2, uz, 11.5, 4.5, 2.1, mat_idx=9)

    # CAMERA 3 (`Rue_Wellington_West_Corridor`: pos=(-132.100, -1147.886), hdg=45°)
    # 4-story Griffintown brick warehouse with exposed concrete column/slab grid & windows on ALL 4 SIDES!
    cam3 = Vector((-132.100, -1147.886, 0.0))
    f3 = Vector((math.sin(math.radians(45.0)), math.cos(math.radians(45.0)), 0.0)).normalized()
    r3 = Vector((f3.y, -f3.x, 0.0)).normalized()
    c3_bldg = cam3 + f3 * 12.8
    for tier_i in range(4):
        add_box_local(bm, c3_bldg + uz * (2.10 + tier_i * 4.1), r3, f3, uz, 32.0, 9.0, 4.0, mat_idx=2)
    add_box_local(bm, c3_bldg + uz * 16.5, r3, f3, uz, 31.2, 8.4, 0.30, mat_idx=13)
    # Front (-f3) AND Back (+f3) exposed concrete slabs, columns & window bays
    for side_f3 in (-1.0, 1.0):
        for z_slab in (3.8, 7.8, 11.8, 15.6):
            add_box_local(bm, c3_bldg + f3 * (side_f3 * 4.55) + uz * z_slab, r3, f3, uz, 32.2, 0.26, 0.58, mat_idx=5)
        for col_x in (-11.2, -5.6, 0.0, 5.6, 11.2):
            add_box_local(bm, c3_bldg + r3 * col_x + f3 * (side_f3 * 4.58) + uz * 8.2, r3, f3, uz, 0.62, 0.32, 16.4, mat_idx=5)
        for bay_x in (-13.6, -8.4, -2.8, 2.8, 8.4, 13.6):
            for fl_z in (2.0, 5.8, 9.8, 13.7):
                wp3 = c3_bldg + r3 * bay_x + f3 * (side_f3 * 4.52) + uz * fl_z
                if side_f3 < 0 and abs(bay_x - 2.8) < 0.5 and fl_z < 3.0:
                    add_box_local(bm, wp3, r3, f3, uz, 2.6, 0.18, 2.9, mat_idx=8)
                    add_box_local(bm, wp3 + uz * 1.55 - f3 * 0.06, r3, f3, uz, 3.0, 0.26, 0.32, mat_idx=5)
                elif abs(bay_x) < 10.0:
                    add_box_local(bm, wp3, r3, f3, uz, 3.2, 0.16, 2.1, mat_idx=6)
                    add_box_local(bm, wp3 + f3 * (side_f3 * 0.05), r3, f3, uz, 1.35, 0.14, 1.85, mat_idx=7)
                else:
                    add_box_local(bm, wp3 + f3 * (side_f3 * 0.04), r3, f3, uz, 2.1, 0.16, 2.0, mat_idx=7)
                    add_box_local(bm, wp3 + f3 * (side_f3 * 0.10) - uz * 1.08, r3, f3, uz, 2.4, 0.26, 0.16, mat_idx=1)
    # Left (-r3) AND Right (+r3) end walls of c3_bldg (visible on far-left of SE_Iso!)
    for side_r3 in (-1.0, 1.0):
        _add_wall_fenestration_grid(bm, c3_bldg + r3 * (side_r3 * 16.0), f3 * side_r3, r3 * side_r3, 9.0, 16.2, 4, 2)

    # CAMERA 4 (`Rue_Ann_Industrial_Facade`: pos=(-158.868, -1078.818), hdg=110°)
    cam4 = Vector((-158.868, -1078.818, 0.0))
    f4 = Vector((math.sin(math.radians(110.0)), math.cos(math.radians(110.0)), 0.0)).normalized()
    r4 = Vector((f4.y, -f4.x, 0.0)).normalized()
    c4_bldg = cam4 + f4 * 12.6
    for tier_4 in range(5):
        add_box_local(bm, c4_bldg + uz * (2.15 + tier_4 * 4.2), r4, f4, uz, 28.0, 5.6, 4.1, mat_idx=4)
    add_box_local(bm, c4_bldg - f4 * 2.82 + uz * 2.0, r4, f4, uz, 26.0, 0.18, 3.8, mat_idx=7)
    for pier_x in (-11.0, -5.5, 1.5, 7.5):
        add_box_local(bm, c4_bldg + r4 * pier_x - f4 * 2.88 + uz * 2.0, r4, f4, uz, 0.95, 0.32, 4.0, mat_idx=9)
    for fl_idx in range(1, 6):
        z_fl = 4.0 + (fl_idx - 1) * 3.5
        add_box_local(bm, c4_bldg - f4 * 2.86 + uz * z_fl, r4, f4, uz, 28.2, 0.28, 0.85, mat_idx=9)
        for w4_x in (-8.5, -4.2, -0.5, 4.2, 9.2):
            w4_p = c4_bldg + r4 * w4_x - f4 * 2.82 + uz * (z_fl + 1.75)
            add_box_local(bm, w4_p, r4, f4, uz, 3.1, 0.16, 2.3, mat_idx=7)
            if abs(w4_x - (-4.2)) < 0.5 or abs(w4_x - 4.2) < 0.5:
                add_box_local(bm, w4_p - f4 * 0.45 - uz * 0.55, r4, f4, uz, 2.8, 0.08, 1.05, mat_idx=8)
    # Fenestrate back (+f4) and sides (-r4, +r4) of c4_bldg
    _add_wall_fenestration_grid(bm, c4_bldg + f4 * 2.8, -r4, f4, 28.0, 21.0, 6, 7)
    for s4_r in (-1.0, 1.0):
        _add_wall_fenestration_grid(bm, c4_bldg + r4 * (s4_r * 14.0), f4 * s4_r, r4 * s4_r, 5.6, 21.0, 6, 2)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.25)


def main():
    print(f"\n=== Building {BLOCK_ID}: Griffintown Heritage Block — New City Gas & Rue Ottawa ===")
    clear_scene()
    setup_world_sky()
    dossier = load_dossier(BLOCK_ID)
    dossier["block_center_xy_m"] = dossier.get("blender_center_xy_m", [-92.842, -1059.762])

    owned_col = bpy.data.collections.new(f"{BLOCK_ID}_Owned")
    bpy.context.scene.collection.children.link(owned_col)

    mats = build_corridor_material_palette()
    build_ground_and_streets(owned_col, dossier)
    build_new_city_gas_and_griffintown_heroes(owned_col, dossier, mats)

    skip_ids = {
        "340223814",   # New City Gas
        "331868177",   # Lowney sur Ville - Phase 2
        "442597527",   # Lowney sur Ville - Phase 4
        "305021902",   # Lowney sur Ville - Phase 1
        "442597210",   # Lowney sur Ville - Phase 3
        "47175688",    # Entreposage Domestik
        "1321450945",  # NW circular pavilion
        "1293527959",  # Gallery footprint
    }
    skip_boxes = [(-170.0, -18.0, -1152.0, -990.0)]
    build_corridor_context_buildings(owned_col, dossier, mats, skip_ids=skip_ids, skip_boxes=skip_boxes)

    # Satellite-matched trees along New City Gas courtyard, Rue Ottawa, NW pavilion & Camera 2 right edge
    extra_trees = [
        (-125.0, -1039.5, 1.25),
        (-117.5, -1043.5, 1.32),
        (-110.0, -1047.5, 1.28),
        (-102.5, -1051.5, 1.35),
        (-95.0, -1055.5, 1.22),
        (-115.0, -1011.0, 1.40),
        (-104.5, -1017.5, 1.30),
        (-88.0, -1089.0, 1.28),
        (-74.0, -1097.0, 1.35),
        (-65.0, -1102.0, 1.32),
        (-56.0, -1107.0, 1.28),
        (-30.0, -1093.0, 1.38),
        (-92.0, -1014.0, 1.32),
    ]
    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=55)
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Build Successfully ===")


if __name__ == "__main__":
    main()
