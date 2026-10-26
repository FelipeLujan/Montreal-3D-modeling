#!/usr/bin/env python3
"""
High-Poly 3D Architecture, Civic Square & Heritage Landmark Modeler — Block `MTL-VM-0001`
(`Place d'Armes — Monument Maisonneuve, Civic Square & Notre-Dame Forecourt`)
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

BLOCK_ID = "MTL-VM-0001"


def _add_4sided_tier_windows(
    bm: bmesh.types.BMesh,
    center_xy: Vector,
    u_x: Vector,
    u_y: Vector,
    z0: float,
    z1: float,
    sx: float,
    sy: float,
    floor_h: float = 3.6,
    bay_spacing: float = 3.4,
    glass_idx: int = 4,
    trim_idx: int = 5,
    stone_idx: int = 2,
    add_pilasters: bool = True,
):
    """
    Populates all 4 vertical exterior faces (+u_x, -u_x, +u_y, -u_y) of a box tier
    extending from `z0` to `z1` with 3D window frames (`trim_idx`), dark glass panes (`glass_idx`),
    projecting sills (`stone_idx`), horizontal spandrel courses, and optional vertical Art Deco pilasters
    regardless of building height (`z0 > 42m` included!).
    """
    uz = Vector((0.0, 0.0, 1.0))
    dz = z1 - z0
    n_floors = max(1, int(round((dz - 0.6) / floor_h)))
    act_fh = (dz - 0.6) / n_floors

    faces_spec = [
        (u_x, u_y, sx * 0.5, sy),
        (-u_x, -u_y, sx * 0.5, sy),
        (u_y, -u_x, sy * 0.5, sx),
        (-u_y, u_x, sy * 0.5, sx),
    ]
    for u_out, u_tan, half_d, wall_w in faces_spec:
        face_base = Vector((center_xy.x, center_xy.y, z0)) + u_out * half_d
        n_cols = max(2, int(round(wall_w / bay_spacing)))
        bay_w = wall_w / n_cols
        win_w = min(1.85, bay_w * 0.56)
        win_h = min(1.75, act_fh * 0.56)

        if add_pilasters:
            for c_idx in range(n_cols + 1):
                px_off = -0.5 * wall_w + c_idx * bay_w
                pil_w = 0.42 if (0 < c_idx < n_cols) else 0.55
                add_box_local(
                    bm,
                    face_base + u_tan * px_off + u_out * 0.14 + uz * (dz * 0.5),
                    u_tan, u_out, uz,
                    pil_w, 0.28, dz - 0.2,
                    mat_idx=stone_idx,
                )

        for r_fl in range(n_floors):
            z_fl = 0.45 + (r_fl + 0.50) * act_fh
            # Horizontal spandrel belt course
            add_box_local(
                bm,
                face_base + u_out * 0.09 + uz * (0.32 + r_fl * act_fh),
                u_tan, u_out, uz,
                wall_w + 0.12, 0.18, 0.22,
                mat_idx=stone_idx,
            )
            for c_bay in range(n_cols):
                x_off = -0.5 * wall_w + (c_bay + 0.5) * bay_w
                wp = face_base + u_tan * x_off + uz * z_fl
                # White window frame
                add_box_local(bm, wp + u_out * 0.10, u_tan, u_out, uz, win_w + 0.24, 0.16, win_h + 0.22, mat_idx=trim_idx)
                # Dark reflective window glass plane in front of frame
                add_box_local(bm, wp + u_out * 0.17, u_tan, u_out, uz, win_w, 0.10, win_h, mat_idx=glass_idx)
                # Projecting stone sill below window
                add_box_local(bm, wp + u_out * 0.22 - uz * (win_h * 0.5 + 0.08), u_tan, u_out, uz, win_w + 0.34, 0.28, 0.15, mat_idx=stone_idx)


def build_place_darmes_and_landmarks(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Models Place d'Armes & its surrounding monumental architecture with 360-degree 3D fenestration:
    1. Place d'Armes Charcoal & Light Granite Paver Square (`X = -88..-10, Y = -28..42`),
       diagonal granite walkways, low perimeter stone walls & benches, and cast-iron bollards.
    2. Monument à Paul de Chomedey de Maisonneuve (`X = -31.5, Y = 5.5`): quatrefoil fountain basin,
       stepped grey granite plinth, 4 corner bronze pioneer/First Nations statues, and tall central
       bronze statue of Paul de Chomedey de Maisonneuve holding the fleur-de-lis banner.
    3. Basilique Notre-Dame de Montréal (`X = -8..102, Y = -72..10`): Neo-Gothic Pierre Grise limestone
       west facade, 3-arch recessed loggia with warm illuminated portals, twin 69m bell towers
       (`La Persévérance` & `La Tempérance`) with 4-sided recessed Gothic lancets, louvered belfries,
       and circular clock faces on all 4 sides, plus 74m pitched slate nave roof with 6 glass skylights.
    4. Bank of Montreal Main Branch (`X = -54, Y = 56`): Neoclassical hexastyle Corinthian portico,
       triangular pediment, 4-sided floor-by-floor fenestration, and 32m verdigris copper Pantheon dome
       with 16 clerestory drum windows around its base.
    5. New York Life Building (`X = -33, Y = 56`): 8-story Richardsonian red sandstone facade with
       51m SE corner clocktower and 4-sided upper fenestration & clock dials.
    6. Édifice Aldred (`X = -10.5, Y = 58.0`): 23-story stepped Art Deco limestone ziggurat skyscraper
       with full 4-sided floor-by-floor windows and Art Deco vertical pilasters across all 5 tiers (`Z = 0..88m`)
       plus its top lantern crown (`Z = 88..93m`).
    7. 500 Place d'Armes (`X = -76, Y = -44`): 32-story International Style dark anodized curtain-wall
       skyscraper with full 4-sided curtain-wall glazing and metallic mullions from `Z = 0..112m`.
    """
    mesh = bpy.data.meshes.new("MTL_VM_0001_Place_dArmes_Landmarks")
    obj = bpy.data.objects.new("MTL_VM_0001_Place_dArmes_Landmarks", mesh)
    col.objects.link(obj)
    for k in (
        "grey_limestone",       # 0: Pierre Grise Montreal limestone (Notre-Dame, BMO, Maisonneuve pedestal)
        "tan_limestone",        # 1: Warm buff limestone & Beaux-Arts ashlar (Aldred, 507 Place d'Armes)
        "plaza_beige",          # 2: Place d'Armes light granite walkways, parvis steps & fountain rim
        "concrete_podium",      # 3: Charcoal granite square pavers & fieldstone wall
        "dark_glass",           # 4: Recessed window glazing, 500 Place d'Armes curtain wall & skylights
        "white_trim",           # 5: White architectural trim, window frames, clock dials & zebra crosswalks
        "dark_metal",           # 6: Dark anodized metal mullions, bollards, railings & bronze statues
        "copper_verdigris",     # 7: BMO Pantheon dome verdigris copper & aged bronze patina
        "sandstone_brick",      # 8: New York Life Building Richardsonian red sandstone
        "roof_slates",          # 9: Notre-Dame pitched dark slate nave roof
        "water_river",          # 10: Monument Maisonneuve fountain basin water
    ):
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    uz = Vector((0.0, 0.0, 1.0))

    # Primary urban grid orientation of Place d'Armes & Notre-Dame (~27° CCW from East-West)
    # Vector along Rue Notre-Dame Ouest (SW -> NE):
    u_nd = Vector((0.454, 0.891, 0.0)).normalized()
    # Vector perpendicular to Rue Notre-Dame (NW -> SE, facing Basilica from Square):
    v_nd = Vector((0.891, -0.454, 0.0)).normalized()

    # ==========================================================================
    # 1. PLACE D'ARMES GRANITE PAVING, PARVIS APRON, DIAGONAL WALKWAYS & BOLLARDS
    # ==========================================================================
    sq_c = Vector((-38.0, 4.0, 0.0))
    # Main charcoal granite square slab (Z = 0.0..0.16m)
    add_box_local(bm, sq_c + uz * 0.08, u_nd, v_nd, uz, 68.0, 62.0, 0.16, mat_idx=3)
    # Light granite diagonal cross walkways & border bands (Z = 0.09..0.175m)
    d1 = (u_nd + v_nd).normalized()
    d2 = (u_nd - v_nd).normalized()
    add_box_local(bm, sq_c + uz * 0.09, d1, d2, uz, 74.0, 4.2, 0.175, mat_idx=2)
    add_box_local(bm, sq_c + uz * 0.09, d2, d1, uz, 74.0, 4.2, 0.175, mat_idx=2)
    # Semi-circular light granite forecourt parvis in front of Notre-Dame Basilica (`X = -10..2, Y = -14..8`)
    parvis_c = Vector((-4.5, -5.5, 0.0))
    add_cylinder_along(bm, parvis_c + uz * 0.04, parvis_c + uz * 0.185, 16.5, 16.5, segs=32, mat_idx=2, cap_ends=True)
    # Low granite perimeter seat walls & raised wooden/granite platform on NW side of square
    add_box_local(bm, Vector((-22.0, 26.0, 0.32)), u_nd, v_nd, uz, 8.5, 5.5, 0.36, mat_idx=6)
    add_box_local(bm, Vector((-56.0, 14.0, 0.42)), u_nd, v_nd, uz, 28.0, 0.65, 0.55, mat_idx=0)
    add_box_local(bm, Vector((-48.0, -14.0, 0.42)), u_nd, v_nd, uz, 26.0, 0.65, 0.55, mat_idx=0)

    # Cast-iron security bollards along Rue Notre-Dame Ouest between Square and Basilica Parvis
    for b_idx in range(-5, 6):
        bol_p = Vector((-6.5, -5.0, 0.0)) + u_nd * (b_idx * 4.2)
        add_cylinder_along(bm, bol_p + uz * 0.16, bol_p + uz * 1.02, 0.14, 0.13, segs=12, mat_idx=6, cap_ends=True)

    # ==========================================================================
    # 2. MONUMENT À PAUL DE CHOMEDEY DE MAISONNEUVE (Center = (-31.5, 5.5))
    # ==========================================================================
    mon_c = Vector((-31.5, 5.5, 0.0))
    # Quatrefoil / 4-lobed granite fountain basin (Z = 0.16..0.72m)
    add_cylinder_along(bm, mon_c + uz * 0.16, mon_c + uz * 0.72, 6.2, 6.0, segs=28, mat_idx=2, cap_ends=True)
    add_cylinder_along(bm, mon_c + uz * 0.20, mon_c + uz * 0.66, 5.4, 5.4, segs=28, mat_idx=10, cap_ends=True)
    for lobe_dir in (u_nd, -u_nd, v_nd, -v_nd):
        lp = mon_c + lobe_dir * 4.2
        add_cylinder_along(bm, lp + uz * 0.16, lp + uz * 0.72, 3.2, 3.1, segs=20, mat_idx=2, cap_ends=True)
        add_cylinder_along(bm, lp + uz * 0.20, lp + uz * 0.66, 2.6, 2.6, segs=20, mat_idx=10, cap_ends=True)

    # Stepped Grey Granite Pedestal & Plinth (Z = 0.65..6.2m)
    add_box_local(bm, mon_c + uz * 1.05, u_nd, v_nd, uz, 6.4, 6.4, 0.85, mat_idx=0)
    add_box_local(bm, mon_c + uz * 1.95, u_nd, v_nd, uz, 5.2, 5.2, 1.05, mat_idx=0)
    add_box_local(bm, mon_c + uz * 3.85, u_nd, v_nd, uz, 3.2, 3.2, 2.85, mat_idx=0)
    add_box_local(bm, mon_c + uz * 5.55, u_nd, v_nd, uz, 3.6, 3.6, 0.65, mat_idx=2)
    add_box_local(bm, mon_c + uz * 6.35, u_nd, v_nd, uz, 2.4, 2.4, 1.05, mat_idx=0)

    # 4 Seated Bronze Pioneer Statues at pedestal corners
    for sx in (-1.95, 1.95):
        for sy in (-1.95, 1.95):
            sp = mon_c + u_nd * sx + v_nd * sy
            add_box_local(bm, sp + uz * 2.55, u_nd, v_nd, uz, 0.95, 0.95, 0.45, mat_idx=0)
            add_cylinder_along(bm, sp + uz * 2.75, sp + uz * 4.15, 0.42, 0.28, segs=12, mat_idx=6, cap_ends=True)
            add_cylinder_along(bm, sp + uz * 4.15, sp + uz * 4.50, 0.20, 0.18, segs=10, mat_idx=6, cap_ends=True)

    # Central Hero Bronze Statue of Maisonneuve + Standard Banner (Z = 6.85..10.8m)
    add_cylinder_along(bm, mon_c + uz * 6.85, mon_c + uz * 9.35, 0.55, 0.38, segs=16, mat_idx=6, cap_ends=True)
    add_cylinder_along(bm, mon_c + uz * 9.35, mon_c + uz * 9.85, 0.26, 0.22, segs=12, mat_idx=6, cap_ends=True)
    flag_base = mon_c + u_nd * 0.35 + uz * 7.2
    flag_top = mon_c + u_nd * 0.55 + uz * 11.2
    add_cylinder_along(bm, flag_base, flag_top, 0.06, 0.04, segs=8, mat_idx=6, cap_ends=True)
    add_box_local(bm, flag_top - uz * 0.65 - u_nd * 0.45, u_nd, v_nd, uz, 0.95, 0.08, 1.15, mat_idx=7)

    # ==========================================================================
    # 3. BASILIQUE NOTRE-DAME DE MONTRÉAL (Hero Landmark SE of Place d'Armes)
    # ==========================================================================
    nd_front = Vector((0.85, -7.65, 0.0))
    # Stepped granite parvis stairs leading up to the 3-arch Gothic loggia
    for st_i in range(5):
        add_box_local(
            bm,
            nd_front - v_nd * (2.6 - st_i * 0.45) + uz * (0.12 * (st_i + 1)),
            u_nd, v_nd, uz,
            39.5 - st_i * 0.4, 2.8, 0.24,
            mat_idx=2,
        )
    # Main Nave Body (length = 74m along +v_nd, width = 38.8m along u_nd, height = 27m)
    nave_c = nd_front + v_nd * 39.0
    add_box_local(bm, nave_c + uz * 13.5, u_nd, v_nd, uz, 38.8, 74.0, 27.0, mat_idx=0)
    # Pitched dark slate gable roof over Nave (Z = 27.0..38.5m) with 6 pairs of glass skylights visible in Satellite!
    for r_step in range(10):
        frac = r_step / 10.0
        w_r = 38.4 * (1.0 - frac * 0.88)
        z_r = 27.0 + frac * 11.2
        add_box_local(bm, nave_c + uz * (z_r + 0.55), u_nd, v_nd, uz, w_r, 73.2, 1.15, mat_idx=9)
    for sk_row in (-18.0, 0.0, 18.0):
        for sk_side in (-7.5, 7.5):
            sk_p = nave_c + v_nd * sk_row + u_nd * sk_side + uz * 32.8
            add_box_local(bm, sk_p, u_nd, v_nd, uz, 4.8, 7.2, 0.65, mat_idx=4)
            add_box_local(bm, sk_p - uz * 0.15, u_nd, v_nd, uz, 5.2, 7.6, 0.35, mat_idx=5)

    # Central West Facade Gable & Crenellated Parapet between the Twin Towers (Z = 0..38.5m)
    add_box_local(bm, nd_front + v_nd * 2.2 + uz * 18.5, u_nd, v_nd, uz, 17.5, 4.4, 37.0, mat_idx=0)
    # 3 Deep Recessed Gothic Entrance Portals at Ground Level (Z = 0.8..12.5m)
    for p_x in (-5.4, 0.0, 5.4):
        port_c = nd_front + u_nd * p_x + v_nd * 0.15
        add_box_local(bm, port_c + uz * 6.5, u_nd, v_nd, uz, 3.8, 1.4, 11.5, mat_idx=4)
    for pier_x in (-8.2, -2.7, 2.7, 8.2):
        pier_c = nd_front + u_nd * pier_x - v_nd * 0.35
        add_box_local(bm, pier_c + uz * 18.5, u_nd, v_nd, uz, 1.35, 1.2, 37.0, mat_idx=0)
    # 3 Upper Sacred Statue Niches & Tracery Arches (Z = 16.0..29.5m)
    for n_x in (-5.4, 0.0, 5.4):
        niche_c = nd_front + u_nd * n_x - v_nd * 0.15 + uz * 22.5
        add_box_local(bm, niche_c, u_nd, v_nd, uz, 3.2, 0.65, 9.5, mat_idx=2)
        add_cylinder_along(bm, niche_c - v_nd * 0.25 - uz * 2.5, niche_c - v_nd * 0.25 + uz * 1.8, 0.48, 0.35, segs=10, mat_idx=1, cap_ends=True)
    # Also add Gothic Rose / Lancet Windows on the REAR (+v_nd) face of the central gable (Z = 28..36m) so SE_Iso never sees a blank rear wall!
    for r_x in (-4.8, 0.0, 4.8):
        rg_p = nd_front + u_nd * r_x + v_nd * 4.45 + uz * 32.0
        add_box_local(bm, rg_p, u_nd, v_nd, uz, 2.8, 0.32, 6.2, mat_idx=5)
        add_box_local(bm, rg_p + v_nd * 0.12, u_nd, v_nd, uz, 2.3, 0.18, 5.6, mat_idx=4)
    # Crenellated Gothic Battlements along central parapet (Z = 37.0..39.2m)
    for cr_i in range(-4, 5):
        add_box_local(bm, nd_front + u_nd * (cr_i * 1.8) + v_nd * 0.5 + uz * 38.0, u_nd, v_nd, uz, 0.95, 1.2, 2.2, mat_idx=0)

    # FIX 3: Twin 69m Neo-Gothic Bell Towers (`La Persévérance` & `La Tempérance`) with 4-SIDED Gothic Lancet & Louvered Belfry Openings!
    for tw_sign, tw_u in ((-1, -13.8), (1, 13.8)):
        tw_c = nd_front + u_nd * tw_u + v_nd * 3.8
        # Lower & Mid Tower Shaft (Z = 0..46.0m)
        add_box_local(bm, tw_c + uz * 23.0, u_nd, v_nd, uz, 10.6, 10.6, 46.0, mat_idx=0)
        # Upper Belfry Stage (Z = 46.0..64.5m)
        add_box_local(bm, tw_c + uz * 55.2, u_nd, v_nd, uz, 9.8, 9.8, 18.5, mat_idx=0)
        # 4 Corner Octagonal Buttress Turrets & Tall Spire Pinnacles (Z = 0..69.8m)
        for bx_s in (-5.1, 5.1):
            for by_s in (-5.1, 5.1):
                bp = tw_c + u_nd * bx_s + v_nd * by_s
                add_box_local(bm, bp + uz * 32.5, u_nd, v_nd, uz, 1.65, 1.65, 65.0, mat_idx=0)
                add_cylinder_along(bm, bp + uz * 65.0, bp + uz * 69.8, 0.95, 0.12, segs=8, mat_idx=0, cap_ends=True)
        # Horizontal Limestone String Courses on Towers
        for hz_t in (13.5, 26.5, 38.5, 46.2, 56.5, 64.5):
            add_box_local(bm, tw_c + uz * hz_t, u_nd, v_nd, uz, 11.4, 11.4, 0.65, mat_idx=2)

        # Populate ALL 4 FACES (-v_nd front, +v_nd rear, -u_nd SW flank, +u_nd NE flank) of BOTH towers from Z=6m to Z=63m!
        for f_out, f_tan in ((-v_nd, u_nd), (v_nd, -u_nd), (u_nd, v_nd), (-u_nd, -v_nd)):
            # Lower & Mid Tower Shafts (half_d = 5.30m): paired Gothic lancet windows at Z = 8.5m, 20.5m, 32.5m
            for wz_t, wh_t in ((8.5, 7.2), (20.5, 8.2), (32.5, 8.2)):
                for lx_off in (-1.65, 1.65):
                    lp_w = tw_c + f_out * 5.32 + f_tan * lx_off + uz * wz_t
                    add_box_local(bm, lp_w, f_tan, f_out, uz, 1.95, 0.28, wh_t + 0.4, mat_idx=2)
                    add_box_local(bm, lp_w + f_out * 0.12, f_tan, f_out, uz, 1.45, 0.18, wh_t, mat_idx=4)
                    # Gothic mullion & transom tracery bars
                    add_box_local(bm, lp_w + f_out * 0.20, f_tan, f_out, uz, 0.14, 0.12, wh_t, mat_idx=2)
                    add_box_local(bm, lp_w + f_out * 0.20 + uz * (wh_t * 0.18), f_tan, f_out, uz, 1.45, 0.12, 0.16, mat_idx=2)

            # Circular Clock Face at Z = 42.4m on ALL 4 sides of each tower!
            clk_p = tw_c + f_out * 5.35 + uz * 42.4
            add_cylinder_along(bm, clk_p, clk_p + f_out * 0.26, 1.85, 1.85, segs=24, mat_idx=6, cap_ends=True)
            add_cylinder_along(bm, clk_p + f_out * 0.26, clk_p + f_out * 0.34, 1.45, 1.45, segs=24, mat_idx=5, cap_ends=True)

            # Upper Belfry Stage (Z = 46.0..64.5m, half_d = 4.90m): tall twin Gothic louvered belfry openings on ALL 4 sides!
            for lx_off in (-1.55, 1.55):
                bf_p = tw_c + f_out * 4.92 + f_tan * lx_off + uz * 54.8
                # Projecting limestone Gothic hood molding & jamb surround
                add_box_local(bm, bf_p, f_tan, f_out, uz, 2.15, 0.34, 11.8, mat_idx=2)
                # Deep dark glass / shadow belfry opening
                add_box_local(bm, bf_p + f_out * 0.14, f_tan, f_out, uz, 1.60, 0.20, 11.0, mat_idx=4)
                # Central stone mullion & 4 horizontal acoustic belfry louvers
                add_box_local(bm, bf_p + f_out * 0.24, f_tan, f_out, uz, 0.16, 0.14, 11.0, mat_idx=2)
                for lv_z in (-3.6, -1.2, 1.2, 3.6):
                    add_box_local(bm, bf_p + f_out * 0.24 + uz * lv_z, f_tan, f_out, uz, 1.60, 0.14, 0.20, mat_idx=6)

    # Vieux Séminaire de Saint-Sulpice (1684 Historic Limestone Wing & Fieldstone Forecourt Wall SW of Basilica, seen on right of Camera 1)
    sem_c = Vector((-16.5, -38.0, 0.0))
    add_box_local(bm, sem_c + uz * 7.5, u_nd, v_nd, uz, 16.5, 22.0, 15.0, mat_idx=0)
    add_box_local(bm, sem_c - v_nd * 5.0 + uz * 16.2, u_nd, v_nd, uz, 14.5, 12.0, 2.4, mat_idx=9)
    wall_c = Vector((-21.5, -26.5, 0.0))
    add_box_local(bm, wall_c + uz * 1.65, u_nd, v_nd, uz, 22.0, 0.85, 3.3, mat_idx=3)
    add_box_local(bm, wall_c + uz * 3.40, u_nd, v_nd, uz, 22.4, 1.05, 0.25, mat_idx=0)

    # ==========================================================================
    # 4. BANK OF MONTREAL MAIN BRANCH (FIX 2: 4-Sided Fenestration, Portico & Clerestory Dome Drum)
    # ==========================================================================
    bmo_c = Vector((-54.0, 56.0, 0.0))
    # Main Neoclassical Pierre Grise Limestone Body (Z = 0..19.5m)
    add_box_local(bm, bmo_c + uz * 9.75, u_nd, v_nd, uz, 38.0, 28.0, 19.5, mat_idx=0)
    add_box_local(bm, bmo_c + uz * 19.8, u_nd, v_nd, uz, 39.2, 29.2, 0.95, mat_idx=2)
    # Explicit 4-sided classical windows & pilasters across all 4 walls of BMO Main Building
    _add_4sided_tier_windows(
        bm, bmo_c, u_nd, v_nd,
        z0=0.5, z1=19.2, sx=38.0, sy=28.0,
        floor_h=4.6, bay_spacing=4.2,
        glass_idx=4, trim_idx=5, stone_idx=2, add_pilasters=True,
    )
    # Rooftop Attic Pedestal / Skylight Monitor Box (Z = 19.5..22.8m) supporting the Pantheon Drum
    add_box_local(bm, bmo_c + uz * 21.15, u_nd, v_nd, uz, 26.5, 22.5, 3.3, mat_idx=0)
    add_box_local(bm, bmo_c + uz * 22.90, u_nd, v_nd, uz, 27.3, 23.3, 0.45, mat_idx=2)
    _add_4sided_tier_windows(
        bm, bmo_c, u_nd, v_nd,
        z0=19.6, z1=22.7, sx=26.5, sy=22.5,
        floor_h=2.8, bay_spacing=3.6,
        glass_idx=4, trim_idx=5, stone_idx=2, add_pilasters=True,
    )
    # Projecting Hexastyle Corinthian Portico & Triangular Pediment facing Place d'Armes (+v_nd)
    port_bmo = bmo_c + v_nd * 15.5
    add_box_local(bm, port_bmo + uz * 0.9, u_nd, v_nd, uz, 22.0, 5.5, 1.8, mat_idx=0)
    for col_i in range(6):
        cx_off = -9.5 + col_i * 3.8
        cp = port_bmo + u_nd * cx_off + v_nd * 1.8
        add_cylinder_along(bm, cp + uz * 1.8, cp + uz * 13.8, 0.68, 0.58, segs=20, mat_idx=0, cap_ends=True)
        add_box_local(bm, cp + uz * 14.2, u_nd, v_nd, uz, 1.45, 1.45, 0.85, mat_idx=2)
    # Classical Entablature & Stepped Triangular Pediment (Z = 14.6..19.8m)
    add_box_local(bm, port_bmo + uz * 15.6, u_nd, v_nd, uz, 22.8, 5.8, 2.0, mat_idx=0)
    for ped_i in range(5):
        pw = 22.4 * (1.0 - ped_i * 0.18)
        add_box_local(bm, port_bmo + uz * (16.9 + ped_i * 0.62), u_nd, v_nd, uz, pw, 5.6, 0.65, mat_idx=2)
    # Iconic Verdigris Copper Pantheon Dome & Clerestory Drum (Z = 22.8..34.5m)
    add_cylinder_along(bm, bmo_c + uz * 22.8, bmo_c + uz * 25.8, 11.2, 10.8, segs=28, mat_idx=0, cap_ends=True)
    # 16 Clerestory Windows around the 360-degree BMO Dome Drum Base (`Z = 23.2..25.5m`)
    for w_ang_i in range(16):
        ang_d = 2.0 * math.pi * w_ang_i / 16.0
        r_dir_d = u_nd * math.cos(ang_d) + v_nd * math.sin(ang_d)
        t_dir_d = Vector((-r_dir_d.y, r_dir_d.x, 0.0)).normalized()
        dp_w = bmo_c + r_dir_d * 11.05 + uz * 24.3
        add_box_local(bm, dp_w, t_dir_d, r_dir_d, uz, 1.85, 0.28, 2.05, mat_idx=5)
        add_box_local(bm, dp_w + r_dir_d * 0.12, t_dir_d, r_dir_d, uz, 1.45, 0.18, 1.65, mat_idx=4)
    for d_i in range(7):
        z0 = 25.8 + d_i * 1.15
        z1 = z0 + 1.18
        r0 = 10.6 * math.cos(math.radians(d_i * 11.5))
        r1 = 10.6 * math.cos(math.radians((d_i + 1) * 11.5))
        add_cylinder_along(bm, bmo_c + uz * z0, bmo_c + uz * z1, r0, max(1.2, r1), segs=28, mat_idx=7, cap_ends=True)

    # ==========================================================================
    # 5. NEW YORK LIFE BUILDING (8-Story Red Sandstone Landmark & Clocktower, Camera 2 Right)
    # ==========================================================================
    nyl_c = Vector((-33.0, 56.0, 0.0))
    add_box_local(bm, nyl_c + uz * 17.5, u_nd, v_nd, uz, 21.5, 31.0, 35.0, mat_idx=8)
    add_box_local(bm, nyl_c + uz * 35.4, u_nd, v_nd, uz, 22.4, 31.8, 0.95, mat_idx=8)
    # Iconic SE Corner Red Sandstone Clocktower (`X = -31.5, Y = 43.5`, Z = 0..47.5m) with 4-sided upper fenestration & clock dials!
    nyl_tw = Vector((-31.5, 43.5, 0.0))
    add_box_local(bm, nyl_tw + uz * 23.5, u_nd, v_nd, uz, 8.6, 8.6, 47.0, mat_idx=8)
    add_box_local(bm, nyl_tw + uz * 47.4, u_nd, v_nd, uz, 9.4, 9.4, 0.95, mat_idx=8)
    _add_4sided_tier_windows(
        bm, nyl_tw, u_nd, v_nd,
        z0=34.5, z1=46.8, sx=8.6, sy=8.6,
        floor_h=3.8, bay_spacing=3.6,
        glass_idx=4, trim_idx=5, stone_idx=8, add_pilasters=True,
    )
    add_cylinder_along(bm, nyl_tw - u_nd * 4.0 + v_nd * 4.0 + uz * 47.5, nyl_tw - u_nd * 4.0 + v_nd * 4.0 + uz * 51.5, 1.35, 0.15, segs=12, mat_idx=7, cap_ends=True)

    # ==========================================================================
    # 6. ÉDIFICE ALDRED (FIX 1: 23-Story Art Deco Ziggurat with Windows on ALL 5 Tiers + Lantern Crown!)
    # ==========================================================================
    ald_c = Vector((-10.5, 58.0, 0.0))
    # Stepped wedding-cake Art Deco tiers (Z = 0..88.0m) + Top Art Deco Lantern Crown (Z = 88.0..93.5m)
    for tier_z0, tier_z1, sx_t, sy_t in [
        (0.0, 16.0, 26.5, 48.0),
        (16.0, 36.0, 22.5, 41.0),
        (36.0, 56.0, 18.5, 33.0),
        (56.0, 74.0, 14.5, 25.0),
        (74.0, 88.0, 10.5, 18.0),
        (88.0, 93.5, 7.2, 11.5),
    ]:
        zm = 0.5 * (tier_z0 + tier_z1)
        zh = tier_z1 - tier_z0
        add_box_local(bm, ald_c + uz * zm, u_nd, v_nd, uz, sx_t, sy_t, zh, mat_idx=1)
        add_box_local(bm, ald_c + uz * tier_z1, u_nd, v_nd, uz, sx_t + 0.8, sy_t + 0.8, 0.65, mat_idx=2)
        # Explicitly add 4-sided recessed windows & vertical Art Deco pilasters on upper tiers (`tier_z0 >= 36.0m`)
        # where `ensure_landmark_3d_fenestration` skips `z_min > 42.0m`!
        if tier_z0 >= 36.0:
            _add_4sided_tier_windows(
                bm, ald_c, u_nd, v_nd,
                z0=tier_z0 + 0.2, z1=tier_z1 - 0.3, sx=sx_t, sy=sy_t,
                floor_h=3.5, bay_spacing=3.2,
                glass_idx=4, trim_idx=5, stone_idx=2, add_pilasters=True,
            )

    # 10-Story Flatiron Heritage Limestone Building East of Square (`X = 20.5, Y = 25.5`, Center of Camera 3!)
    flat_c = Vector((20.5, 25.5, 0.0))
    add_box_local(bm, flat_c + uz * 17.5, u_nd, v_nd, uz, 18.5, 16.5, 35.0, mat_idx=1)
    add_box_local(bm, flat_c + uz * 35.3, u_nd, v_nd, uz, 19.4, 17.4, 0.85, mat_idx=2)

    # ==========================================================================
    # 7. 500 PLACE D'ARMES (32-Story Dark Curtain-Wall Skyscraper, SW of Square, Camera 4!)
    # ==========================================================================
    b500_c = Vector((-76.0, -44.0, 0.0))
    # Ground colonnade podium + 32-story dark anodized curtain-wall tower (`Z = 0..112.0m`)
    add_box_local(bm, b500_c + uz * 56.0, u_nd, v_nd, uz, 38.0, 38.0, 112.0, mat_idx=6)
    add_box_local(bm, b500_c + uz * 112.4, u_nd, v_nd, uz, 39.2, 39.2, 0.85, mat_idx=5)
    # Full 4-sided curtain-wall window grid & vertical anodized mullions across all 30 upper floors (`Z = 6..111m`)
    _add_4sided_tier_windows(
        bm, b500_c, u_nd, v_nd,
        z0=4.0, z1=111.0, sx=38.0, sy=38.0,
        floor_h=3.7, bay_spacing=3.8,
        glass_idx=4, trim_idx=5, stone_idx=6, add_pilasters=True,
    )

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.25)


def main():
    print(f"\n=== Building {BLOCK_ID} (Iter 2): Place d'Armes, Monument Maisonneuve & Notre-Dame Forecourt ===")
    clear_scene()
    setup_world_sky()
    dossier = load_dossier(BLOCK_ID)

    owned_col = bpy.data.collections.new(f"{BLOCK_ID}_Owned")
    bpy.context.scene.collection.children.link(owned_col)

    mats = build_corridor_material_palette()
    build_ground_and_streets(owned_col, dossier)
    build_place_darmes_and_landmarks(owned_col, dossier, mats)

    # Skip custom-modeled hero landmark IDs and BMOMain Branch box so context buildings never overlap them
    skip_ids = {
        "4320792",    # Basilique Notre-Dame
        "102127873",  # Bank of Montreal Main Branch / NW parcel
        "102127874",  # Vieux Séminaire de Saint-Sulpice
        "102127875",  # Édifice Aldred
        "102127876",  # 500 Place d'Armes
        "339885417",  # New York Life Building
        "182859305",  # Flatiron Heritage Building East of Square
    }
    build_corridor_context_buildings(owned_col, dossier, mats, skip_ids=skip_ids)

    # Lush perimeter shade trees along the NE and SW edges of Place d'Armes (matching Satellite & Street View!)
    extra_trees = [
        (-56.0, 31.0, 1.35),
        (-44.0, 26.0, 1.40),
        (-34.0, 21.0, 1.32),
        (-25.0, 17.5, 1.28),
        (-70.0, 3.0, 1.38),
        (-58.0, -4.5, 1.42),
        (-46.0, -10.5, 1.36),
        (-38.0, -14.5, 1.30),
        (25.0, 5.5, 1.25),
        (38.0, 0.5, 1.28),
    ]
    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=75)
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Iter 2 Build Successfully ===")


if __name__ == "__main__":
    main()
