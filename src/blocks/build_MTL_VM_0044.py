#!/usr/bin/env python3
"""
High-Poly 3D Architecture, Streetscape & Waterfront Modeler — Block `MTL-VM-0044`
(`Casino de Montréal Iconic Stepped Cantilevered Pavilions & Île Notre-Dame Lagoon Waterfront`)

Constructs:
  1. Hero Landmark: Casino de Montréal Main Rotunda (former Expo 67 Pavilion of France by Jean Faugeron) —
     8 stepped cantilevered circular floor decks (`Z = 0..34.5m`), 48-sided wrap-around glass curtain wall
     (`dark_glass` & `blue_glass`), 72 radial white sun-breaker louver fins (`white_trim` & `concrete_tile_facade`),
     stepped West cantilevered balcony prows, rooftop diagonal structural spine, HVAC courts, and tall spire (`Z = 54m`).
  2. West Sweeping Porte-Cochère Canopy, Small Circular Radial Skylight Dome (`R = 9.2m`), and 4-Tier
     Stepped Concrete Garden Planters & Hedges (`Casino_Montreal_Main_Rotunda_West`, Camera 1).
  3. North-East Triangular Cantilevered Wing, V-Prow Pillar, Swept Entry Canopy with Golden Feature Wall,
     and Circular Sunken Sun-Clock Water Garden Amphitheatre (`Ile_Notre_Dame_North_Water_Garden`, Camera 4).
  4. South-East White Triangular Lagoon Pavilion & Curved Floating Boardwalk Bridge over the Île Notre-Dame
     Regatta Lagoon (`water_river`).
  5. South Stepped Podium, Exterior Monumental Staircases, Elevator Tower, Arched Tubular Skybridge,
     Pavillon du Québec Glass Cube, and Avenue du Casino Bridge Guardrails (`Cameras 2 & 3`).
  6. Georeferenced roads, raised 3D sidewalks & curbs (`MTL_Sidewalks_and_Curbs`), 3D street markings
     (`MTL_Street_Markings`), context buildings, and Poly Haven 3D streetlamps & lush green trees.
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
    setup_render_engine,
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

BLOCK_ID = "MTL-VM-0044"


def _add_prism_polygon(bm: bmesh.types.BMesh, pts_xy: list, z0: float, z1: float, mat_top: int, mat_wall: int):
    if len(pts_xy) < 3:
        return
    v_bot = [bm.verts.new(Vector((x, y, z0))) for x, y in pts_xy]
    v_top = [bm.verts.new(Vector((x, y, z1))) for x, y in pts_xy]
    n = len(pts_xy)
    for i in range(n):
        ni = (i + 1) % n
        try:
            f = bm.faces.new((v_bot[i], v_bot[ni], v_top[ni], v_top[i]))
            f.material_index = mat_wall
        except ValueError:
            pass
    try:
        ft = bm.faces.new(v_top)
        ft.material_index = mat_top
        fb = bm.faces.new(list(reversed(v_bot)))
        fb.material_index = mat_wall
    except ValueError:
        pass


def build_casino_montreal_and_lagoon(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Builds the Casino de Montréal Stepped Louvered Rotunda (former Expo 67 French Pavilion),
    the North-East & South-East Triangular Wings, the Circular Water Garden Amphitheatre,
    the South Stepped Podium & Tubular Skybridge, the Pavillon du Québec Glass Cube,
    and the Île Notre-Dame Lagoon & Floating Boardwalk Bridge.
    """
    mesh = bpy.data.meshes.new("MTL_VM_0044_Casino_de_Montreal_Hero")
    obj = bpy.data.objects.new("MTL_VM_0044_Casino_de_Montreal_Hero", mesh)
    col.objects.link(obj)

    mat_keys = [
        "white_trim",            # 0: Iconic white sun-breaker fins, cantilevered slabs & canopies
        "concrete_tile_facade",  # 1: Precast architectural concrete panels & elevator shafts
        "concrete_podium",       # 2: Brutalist concrete retaining walls, curbs, bridge & stairs
        "dark_glass",            # 3: Recessed dark curtain-wall glazing
        "blue_glass",            # 4: Reflective blue-tinted pavilion curtain-wall glazing
        "plaza_beige",           # 5: Promenade pavers, circular amphitheatre plaza & boardwalk
        "park_grass",            # 6: Terraced garden hedges, lawns & island banks
        "water_river",           # 7: Île Notre-Dame Lagoon & sunken water garden channels
        "roof_white_elastomer",  # 8: White membrane roofs on triangular wings & podiums
        "roof_light_gravel",     # 9: Main rotunda gravel roof deck
        "dark_metal",            # 10: Bridge guardrails, window mullions & HVAC grilles
        "yellow_brick",          # 11: Golden-yellow curved entrance feature wall (Camera 4)
        "copper_verdigris",      # 12: Green architectural sign pillar & accents (Camera 1)
        "tan_limestone",         # 13: Sunken circular water garden radial stone blocks
    ]
    for k in mat_keys:
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    ux = Vector((1.0, 0.0, 0.0))
    uy = Vector((0.0, 1.0, 0.0))
    uz = Vector((0.0, 0.0, 1.0))

    # =========================================================================
    # 1. ÎLE NOTRE-DAME LAGOON BASINS, QUAY WALLS & FLOATING BOARDWALK BRIDGE
    # =========================================================================
    # East Lagoon Basin (visible in satellite_topdown.png right half: X = 2426..2530, Y = 30..108)
    add_box_local(bm, Vector((2478.0, 69.0, 0.025)), ux, uy, uz, 106.0, 78.0, 0.05, mat_idx=7)
    # North concrete quay wall bounding the East Lagoon at Y = 108.5 (X = 2436..2525)
    add_box_local(bm, Vector((2480.0, 108.8, 0.55)), ux, uy, uz, 88.0, 2.4, 1.10, mat_idx=2)
    add_box_local(bm, Vector((2480.0, 109.2, 1.15)), ux, uy, uz, 88.4, 2.8, 0.18, mat_idx=0)

    # South Lagoon Basin around Pavillon du Québec & under Bridge (X = 2310..2510, Y = -55..33)
    add_box_local(bm, Vector((2415.0, -10.0, 0.02)), ux, uy, uz, 190.0, 86.0, 0.04, mat_idx=7)
    # Green landscaped shoreline bank along South edge of Casino podium (X = 2395..2438, Y = 28..35)
    add_box_local(bm, Vector((2416.0, 31.5, 0.35)), ux, uy, uz, 42.0, 7.5, 0.70, mat_idx=6)

    # Floating Boardwalk Bridge across East Lagoon (matches OSM 697836073: X = 2438..2534, Y = 44..85)
    boardwalk_pts = [
        (2438.5, 44.5),
        (2478.0, 44.8),
        (2492.0, 47.0),
        (2506.0, 53.0),
        (2520.0, 63.5),
        (2534.0, 82.0),
    ]
    for i_bw in range(len(boardwalk_pts) - 1):
        p0 = Vector((boardwalk_pts[i_bw][0], boardwalk_pts[i_bw][1], 0.35))
        p1 = Vector((boardwalk_pts[i_bw + 1][0], boardwalk_pts[i_bw + 1][1], 0.35))
        seg_v = p1 - p0
        seg_l = seg_v.length
        seg_u = seg_v.normalized()
        seg_r = Vector((seg_u.y, -seg_u.x, 0.0))
        mid = (p0 + p1) * 0.5
        add_box_local(bm, mid, seg_r, seg_u, uz, 6.2, seg_l + 0.6, 0.45, mat_idx=5)
        for s_rail in (-2.9, 2.9):
            add_box_local(bm, mid + seg_r * s_rail + uz * 0.45, seg_r, seg_u, uz, 0.25, seg_l + 0.6, 0.55, mat_idx=0)

    # =========================================================================
    # 2. HERO LANDMARK: CASINO DE MONTRÉAL MAIN ROTUNDA (Center X=2407.5, Y=94.0)
    #    (Former Expo 67 Pavilion of France — Cantilevered Stepped Louvered Drum)
    # =========================================================================
    rot_cx, rot_cy = 2407.5, 94.0
    rot_c = Vector((rot_cx, rot_cy, 0.0))

    # 2a. Ground Podium & 48-Sided Recessed Curtain Wall Drum (Z = 0.0 .. 33.6m)
    n_drum = 48
    for fl in range(8):
        z0 = fl * 4.2
        z1 = z0 + 4.2
        # Cantilevered outward flare on upper floors + slight NW shift matching Faugeron's design
        r_glass = 31.2 + fl * 0.62
        r_slab = 33.0 + fl * 0.88
        shift_x = -fl * 0.28
        shift_y = fl * 0.24
        fl_c = Vector((rot_cx + shift_x, rot_cy + shift_y, 0.0))

        # Curtain wall glass ring for this floor
        pts_glass = [
            (
                fl_c.x + r_glass * math.cos(2.0 * math.pi * k / n_drum),
                fl_c.y + r_glass * math.sin(2.0 * math.pi * k / n_drum),
            )
            for k in range(n_drum)
        ]
        _add_prism_polygon(bm, pts_glass, z0 + 0.15, z1 - 0.35, mat_top=9, mat_wall=3 if (fl % 2 == 0) else 4)

        # Projecting white horizontal floor slab ring (cantilevered deck)
        pts_slab = [
            (
                fl_c.x + r_slab * math.cos(2.0 * math.pi * k / n_drum),
                fl_c.y + r_slab * math.sin(2.0 * math.pi * k / n_drum),
            )
            for k in range(n_drum)
        ]
        _add_prism_polygon(bm, pts_slab, z1 - 0.52, z1, mat_top=9 if fl == 7 else 0, mat_wall=0)

    # 2b. 72 Radial Sun-Breaker Vertical/Inclined Louver Fins (Brise-Soleil Blades around Drum)
    n_fins = 72
    for k_f in range(n_fins):
        ang = 2.0 * math.pi * k_f / n_fins
        rad_dir = Vector((math.cos(ang), math.sin(ang), 0.0))
        tan_dir = Vector((-math.sin(ang), math.cos(ang), 0.0))

        # Extra radial projection on the dramatic NW, NE, and SE arcs visible in satellite & Street View
        deg = (math.degrees(ang)) % 360.0
        extra_flare = 0.0
        if 105.0 <= deg <= 175.0:
            # NW prow flare (visible in Camera 1 & Camera 4)
            extra_flare = 2.8 * math.sin(math.pi * (deg - 105.0) / 70.0)
        elif 30.0 <= deg <= 95.0:
            # NE flare (visible in Camera 4)
            extra_flare = 2.2 * math.sin(math.pi * (deg - 30.0) / 65.0)
        elif 260.0 <= deg <= 355.0:
            # SE/South-East lagoon louver sweep (visible in satellite_topdown.png)
            extra_flare = 2.5 * math.sin(math.pi * (deg - 260.0) / 95.0)

        # Build each radial sun-breaker blade in 3 vertical tiers to capture the outward-flaring profile
        for t_i, (zf0, zf1, rf_in, rf_out) in enumerate([
            (4.2, 14.5, 31.8, 34.8 + extra_flare * 0.45),
            (14.5, 24.5, 33.2, 37.2 + extra_flare * 0.78),
            (24.5, 34.6, 34.5, 39.6 + extra_flare),
        ]):
            shift_v = Vector((-0.28 * (t_i * 2.5 + 1.0), 0.24 * (t_i * 2.5 + 1.0), 0.0))
            r_mid = 0.5 * (rf_in + rf_out)
            depth_f = (rf_out - rf_in) + 0.6
            fin_c = rot_c + shift_v + rad_dir * r_mid + uz * (0.5 * (zf0 + zf1))
            add_box_local(bm, fin_c, tan_dir, rad_dir, uz, 0.36, depth_f, (zf1 - zf0) + 0.15, mat_idx=0)

        # Rooftop perimeter vertical fin extensions / flagpole standards (Z = 34.5 .. 37.8m)
        if k_f % 2 == 0:
            pole_p = rot_c + Vector((-2.0, 1.7, 0.0)) + rad_dir * (38.2 + extra_flare * 0.7)
            add_box_local(bm, pole_p + uz * 36.0, tan_dir, rad_dir, uz, 0.16, 0.28, 3.6, mat_idx=0)
            # Small blue Expo/Casino rooftop pennant flag at top of standard
            add_box_local(bm, pole_p + rad_dir * 0.35 + uz * 37.5, tan_dir, rad_dir, uz, 0.08, 0.65, 0.42, mat_idx=4)

    # 2c. West Stepped Cantilevered Balcony Prow (Camera 1 Hero Silhouette at X ≈ 2368..2382, Y ≈ 96..110)
    prow_dir = Vector((-0.94, 0.34, 0.0)).normalized()
    prow_tan = Vector((-prow_dir.y, prow_dir.x, 0.0))
    for p_lvl in range(6):
        zp = 10.5 + p_lvl * 3.8
        r_prow = 34.5 + p_lvl * 1.05
        prow_c = rot_c + prow_dir * r_prow + uz * zp
        add_box_local(bm, prow_c, prow_tan, prow_dir, uz, 11.5 - p_lvl * 0.35, 5.5, 1.25, mat_idx=0)
        add_box_local(bm, prow_c + prow_dir * 2.5 + uz * 0.85, prow_tan, prow_dir, uz, 11.2 - p_lvl * 0.35, 0.35, 0.95, mat_idx=0)
        add_box_local(bm, prow_c + prow_dir * 2.3 + uz * 1.45, prow_tan, prow_dir, uz, 10.8 - p_lvl * 0.35, 0.18, 0.65, mat_idx=3)

    # Iconic Tall Vertical Spire Mast on NW Crown of Rotunda (Z = 33.5 .. 54.5m, visible in Cameras 1, 3, 4)
    spire_xy = Vector((2383.5, 104.0, 0.0))
    add_box_local(bm, spire_xy + uz * 35.2, ux, uy, uz, 2.4, 2.4, 3.6, mat_idx=0)
    add_cylinder_along(bm, spire_xy + uz * 36.5, spire_xy + uz * 54.5, 0.42, 0.16, segs=12, mat_idx=0, cap_ends=True)

    # 2d. Rotunda Rooftop Architecture (visible in satellite_topdown.png: Diagonal Spine, HVAC Courts & Elevator Towers)
    # Recessed inner gravel roof deck & raised white parapet partitions
    diag_u = Vector((-0.44, 0.90, 0.0)).normalized()
    diag_r = Vector((diag_u.y, -diag_u.x, 0.0))
    add_box_local(bm, Vector((2404.0, 95.0, 34.8)), diag_r, diag_u, uz, 6.5, 38.0, 2.4, mat_idx=0)
    add_box_local(bm, Vector((2396.0, 92.0, 34.4)), ux, uy, uz, 4.2, 42.0, 1.8, mat_idx=8)
    # Rooftop dark blue solar/skylight array & chiller courts (NE & E quadrants of Rotunda roof)
    add_box_local(bm, Vector((2412.0, 104.0, 34.1)), ux, uy, uz, 16.0, 14.0, 0.9, mat_idx=4)
    add_box_local(bm, Vector((2421.0, 92.0, 34.3)), ux, uy, uz, 9.0, 16.0, 1.4, mat_idx=10)
    # South-West Stepped Elevator Penthouse Core (visible in Camera 1 right, Camera 2 & Camera 3)
    for st_i, (sx_e, sy_e, z_top_e) in enumerate([
        (2401.0, 71.0, 42.5),
        (2397.5, 66.5, 39.0),
        (2394.0, 62.5, 35.5),
    ]):
        add_box_local(bm, Vector((sx_e, sy_e, z_top_e * 0.5)), ux, uy, uz, 9.5, 8.5, z_top_e, mat_idx=1)
        add_box_local(bm, Vector((sx_e, sy_e, z_top_e + 0.25)), ux, uy, uz, 9.9, 8.9, 0.5, mat_idx=0)

    # =========================================================================
    # 3. WEST SWEEPING PORTE-COCHÈRE CANOPY, SMALL RADIAL ROTUNDA & TERRACED
    #    GARDEN PLANTERS (Camera 1 Foreground/Midground: X = 2334..2382, Y = 72..126)
    # =========================================================================
    # 3a. Small Circular Radial-Ribbed Skylight Dome at NW junction (X = 2362.5, Y = 114.5, R = 9.2m)
    sm_rot_c = Vector((2362.5, 114.5, 0.0))
    add_cylinder_along(bm, sm_rot_c + uz * 0.1, sm_rot_c + uz * 6.8, 9.2, 9.2, segs=24, mat_idx=4, cap_ends=True)
    add_cylinder_along(bm, sm_rot_c + uz * 6.6, sm_rot_c + uz * 7.4, 9.6, 9.6, segs=24, mat_idx=0, cap_ends=True)
    add_cylinder_along(bm, sm_rot_c + uz * 7.4, sm_rot_c + uz * 8.6, 1.8, 1.2, segs=16, mat_idx=0, cap_ends=True)
    for k_sr in range(16):
        a_sr = 2.0 * math.pi * k_sr / 16.0
        r_sr = Vector((math.cos(a_sr), math.sin(a_sr), 0.0))
        t_sr = Vector((-math.sin(a_sr), math.cos(a_sr), 0.0))
        add_box_local(bm, sm_rot_c + r_sr * 4.8 + uz * 7.55, t_sr, r_sr, uz, 0.24, 9.2, 0.35, mat_idx=0)

    # 3b. Sweeping White Cantilevered West Canopy & Glass Entrance Lobby (Camera 1 Center-Left)
    can_w_u = Vector((0.12, -0.9928, 0.0)).normalized()
    can_w_r = Vector((can_w_u.y, -can_w_u.x, 0.0))  # Points West toward Camera 1
    can_w_c = Vector((2364.0, 92.5, 0.0))
    # Recessed dark glass lobby curtain wall (Z = 0.2 .. 5.6m)
    add_box_local(bm, can_w_c + uz * 2.9, can_w_u, can_w_r, uz, 32.0, 12.0, 5.4, mat_idx=3)
    for m_i in range(-7, 8):
        mp = can_w_c + can_w_u * (m_i * 2.1) + can_w_r * 6.08 + uz * 2.9
        add_box_local(bm, mp, can_w_u, can_w_r, uz, 0.14, 0.18, 5.4, mat_idx=10)
    # Dramatic Cantilevered White Fascia Canopy projecting West toward Camera 1 (Z = 5.4 .. 6.5m)
    add_box_local(bm, can_w_c + can_w_r * 5.5 + uz * 5.95, can_w_u, can_w_r, uz, 38.0, 18.0, 0.95, mat_idx=0)
    # Swept North-West prow extension of the canopy (seen on the left of Camera 1)
    prow_nw_c = Vector((2350.5, 103.5, 6.25))
    prow_nw_u = Vector((0.82, -0.57, 0.0)).normalized()
    prow_nw_r = Vector((prow_nw_u.y, -prow_nw_u.x, 0.0))
    add_box_local(bm, prow_nw_c, prow_nw_u, prow_nw_r, uz, 22.0, 8.5, 1.05, mat_idx=0)
    # Vertical green "La Terrasse" sign pillar supporting the left side of the canopy (Camera 1 left)
    add_box_local(bm, Vector((2351.8, 100.2, 2.8)), ux, uy, uz, 0.85, 0.85, 5.6, mat_idx=12)

    # 3c. Camera 1 Foreground Promenade, 4-Tier Stepped Concrete Planters & Lush Green Hedge Mounds
    # Wide beige/grey stone walkway on left of Camera 1 (X = 2331..2362, Y = 97..109)
    walk_u = Vector((0.985, 0.17, 0.0)).normalized()
    walk_r = Vector((-walk_u.y, walk_u.x, 0.0))
    add_box_local(bm, Vector((2346.0, 102.5, 0.12)), walk_u, walk_r, uz, 32.0, 9.5, 0.24, mat_idx=5)
    add_box_local(bm, Vector((2346.0, 102.5, 0.14)), walk_u, walk_r, uz, 32.0, 1.8, 0.26, mat_idx=2)

    # 4 Stepped Concrete Terrace/Planter Walls in front of the West Canopy (X = 2340..2362, Y = 80..99)
    for st_p in range(4):
        xp = 2341.5 + st_p * 3.8
        zp = 0.35 + st_p * 0.38
        add_box_local(bm, Vector((xp, 91.5, zp * 0.5)), ux, uy, uz, 3.6, 16.5, zp, mat_idx=2)
        add_box_local(bm, Vector((xp - 1.65, 91.5, zp + 0.06)), ux, uy, uz, 0.45, 16.7, 0.12, mat_idx=0)

    # Lush manicured green lawn & dense rounded hedge bushes on Center-Right of Camera 1 (X = 2333..2362, Y = 72..94)
    add_box_local(bm, Vector((2346.0, 82.0, 0.12)), ux, uy, uz, 28.0, 22.0, 0.24, mat_idx=6)
    hedge_positions = [
        (2343.5, 89.2, 1.45, 2.4),
        (2346.5, 87.8, 1.55, 2.6),
        (2349.8, 90.0, 1.50, 2.5),
        (2353.0, 92.2, 1.45, 2.4),
        (2348.5, 83.5, 1.75, 3.2),
        (2352.5, 81.0, 1.85, 3.4),
        (2356.5, 78.5, 1.90, 3.5),
    ]
    for hx, hy, hz_c, hr in hedge_positions:
        ret_h = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=hr)
        for vh in ret_h.get("verts", []):
            vh.co.z *= 0.65
            vh.co.x += hx
            vh.co.y += hy
            vh.co.z += hz_c
            for fh in vh.link_faces:
                fh.material_index = 6

    # =========================================================================
    # 4. NORTH-EAST TRIANGULAR CANTILEVERED WING, SWEPT ENTRY CANOPY & CIRCULAR
    #    SUN-CLOCK WATER GARDEN (Camera 4 & Satellite Top-Right: X = 2390..2495, Y = 110..175)
    # =========================================================================
    # 4a. North-East Triangular Wing (matches OSM 439917766: apex at (2429.0, 157.5))
    ne_tri_pts = [
        (2395.0, 134.5),
        (2429.0, 157.5),
        (2425.5, 115.5),
    ]
    _add_prism_polygon(bm, ne_tri_pts, 0.0, 13.5, mat_top=8, mat_wall=3)
    _add_prism_polygon(bm, ne_tri_pts, 12.6, 14.2, mat_top=8, mat_wall=0)

    # Sculptural White V-Prow Pillar & Cantilevered North-East Entry Canopy (Camera 4 Right Focal Feature)
    vprow_c = Vector((2435.5, 127.5, 0.0))
    add_box_local(bm, vprow_c + uz * 9.0, ux, uy, uz, 4.5, 7.5, 18.0, mat_idx=0)
    # Swept White Porte-Cochère Roof projecting toward Camera 4 (X = 2418..2446, Y = 122..154, Z = 6.2..7.4m)
    can_ne_u = Vector((-0.62, 0.78, 0.0)).normalized()
    can_ne_r = Vector((can_ne_u.y, -can_ne_u.x, 0.0))
    add_box_local(bm, Vector((2431.0, 138.0, 6.6)), can_ne_r, can_ne_u, uz, 18.0, 32.0, 1.1, mat_idx=0)
    # Curved Golden-Yellow Feature Wall underneath the North-East Canopy (seen in Camera 4 right-center)
    gold_c = Vector((2432.5, 125.0, 0.0))
    add_cylinder_along(bm, gold_c + uz * 0.1, gold_c + uz * 5.6, 5.2, 5.2, segs=20, mat_idx=11, cap_ends=True)

    # 4b. Low 2-Story Modern Glass & White Annex Pavilion on East Side (seen on Left of Camera 4: X = 2466..2496, Y = 109..124)
    annex_c = Vector((2480.0, 116.0, 0.0))
    add_box_local(bm, annex_c + uz * 4.6, ux, uy, uz, 28.0, 13.0, 9.2, mat_idx=3)
    add_box_local(bm, annex_c + uz * 4.8, ux, uy, uz, 28.6, 13.6, 0.65, mat_idx=0)
    add_box_local(bm, annex_c + uz * 9.3, ux, uy, uz, 30.5, 15.5, 0.85, mat_idx=0)

    # 4c. Circular Sunken Sun-Clock Water Garden Amphitheatre (X = 2453.0, Y = 132.0, R = 19.5m)
    wg_c = Vector((2453.0, 132.0, 0.0))
    # Outer circular beige stone plaza ring (R = 26.5m)
    add_cylinder_along(bm, wg_c + uz * 0.04, wg_c + uz * 0.18, 26.5, 26.5, segs=36, mat_idx=5, cap_ends=True)
    # Sunken dark water basin (R = 18.2m)
    add_cylinder_along(bm, wg_c + uz * 0.05, wg_c + uz * 0.22, 18.2, 18.2, segs=32, mat_idx=7, cap_ends=True)
    # Central stone island dial (R = 9.2m)
    add_cylinder_along(bm, wg_c + uz * 0.06, wg_c + uz * 0.32, 9.2, 9.2, segs=24, mat_idx=5, cap_ends=True)
    # 24 Radial Stone Spokes & Low Circular Perimeter Wall (visible in satellite_topdown.png & Camera 4 center)
    for k_wg in range(24):
        a_wg = 2.0 * math.pi * k_wg / 24.0
        r_wg = Vector((math.cos(a_wg), math.sin(a_wg), 0.0))
        t_wg = Vector((-math.sin(a_wg), math.cos(a_wg), 0.0))
        # Radial spoke block across water channel (R = 9.5 .. 17.8m)
        add_box_local(bm, wg_c + r_wg * 13.6 + uz * 0.28, t_wg, r_wg, uz, 1.35, 8.0, 0.38, mat_idx=13)
        # Perimeter parapet curb segment at R = 18.6m (Z = 0.18 .. 0.88m, seen in Camera 4)
        add_box_local(bm, wg_c + r_wg * 18.6 + uz * 0.52, t_wg, r_wg, uz, 4.8, 0.65, 0.72, mat_idx=2)

    # 4d. Camera 4 Foreground Planted Island Curb & Tall White Light Mast (`[2458.93, 177.99]`, hdg=185°)
    add_box_local(bm, Vector((2466.0, 162.5, 0.16)), ux, uy, uz, 14.0, 16.0, 0.32, mat_idx=6)
    add_box_local(bm, Vector((2459.2, 162.5, 0.20)), ux, uy, uz, 0.45, 16.2, 0.40, mat_idx=2)
    mast_c = Vector((2461.2, 167.2, 0.0))
    add_cylinder_along(bm, mast_c + uz * 0.2, mast_c + uz * 9.2, 0.24, 0.12, segs=10, mat_idx=0, cap_ends=True)

    # =========================================================================
    # 5. SOUTH-EAST WHITE TRIANGULAR LAGOON PAVILION (Satellite Lower-Right)
    # =========================================================================
    se_tri_pts = [
        (2441.5, 91.5),
        (2440.0, 52.0),
        (2489.5, 49.3),
    ]
    _add_prism_polygon(bm, se_tri_pts, 0.0, 9.8, mat_top=8, mat_wall=3)
    _add_prism_polygon(bm, se_tri_pts, 8.9, 10.6, mat_top=8, mat_wall=0)

    # =========================================================================
    # 6. SOUTH STEPPED PODIUM, EXTERIOR MONUMENTAL STAIRS, ELEVATOR TOWER,
    #    ARCHED TUBULAR SKYBRIDGE & PAVILLON DU QUÉBEC (Cameras 2 & 3)
    # =========================================================================
    # 6a. South Podium Hall (X = 2362..2438, Y = 34..72, Z = 0..14.5m)
    add_box_local(bm, Vector((2402.0, 52.0, 7.2)), ux, uy, uz, 72.0, 35.0, 14.4, mat_idx=1)
    add_box_local(bm, Vector((2402.0, 52.0, 14.5)), ux, uy, uz, 73.0, 36.0, 0.6, mat_idx=8)
    # Rooftop skylights on South Podium (visible in satellite_topdown.png bottom center)
    add_box_local(bm, Vector((2408.0, 62.5, 15.0)), ux, uy, uz, 16.0, 6.5, 0.8, mat_idx=4)

    # Prominent South-West Rectangular Elevator/Stair Tower (visible in Camera 2 & Camera 3 right-center)
    add_box_local(bm, Vector((2364.5, 45.5, 11.5)), ux, uy, uz, 10.5, 11.0, 23.0, mat_idx=1)
    add_box_local(bm, Vector((2364.5, 45.5, 23.2)), ux, uy, uz, 10.9, 11.4, 0.5, mat_idx=0)

    # Exterior Monumental Stepped Staircases & Terraces facing West/South-West (Cameras 2 & 3)
    for st_s in range(6):
        zs = 1.2 + st_s * 1.65
        xs = 2354.0 + st_s * 1.8
        add_box_local(bm, Vector((xs, 55.0, zs * 0.5)), ux, uy, uz, 3.5, 14.0, zs, mat_idx=0)
        add_box_local(bm, Vector((xs + 4.0, 37.5, zs * 0.5)), ux, uy, uz, 12.0, 3.5, zs, mat_idx=0)

    # 6b. Elevated White Arched Tubular Skybridge connecting Casino to Pavillon du Québec (X = 2388, Y = 6..35)
    sky_p0 = Vector((2388.0, 6.5, 7.2))
    sky_p1 = Vector((2388.0, 35.5, 7.2))
    add_cylinder_along(bm, sky_p0, sky_p1, 4.2, 4.2, segs=16, mat_idx=0, cap_ends=True)
    add_box_local(bm, Vector((2388.0, 21.0, 5.2)), ux, uy, uz, 7.2, 29.0, 1.8, mat_idx=1)

    # 6c. Pavillon du Québec (X = 2361..2410, Y = -40..8, Z = 0..19.0m — Truncated Pyramid Glass Cube)
    pq_c = Vector((2385.5, -16.0, 0.0))
    add_box_local(bm, pq_c + uz * 2.2, ux, uy, uz, 50.0, 48.0, 4.4, mat_idx=2)
    add_box_local(bm, pq_c + uz * 11.5, ux, uy, uz, 48.0, 46.0, 14.5, mat_idx=4)
    add_box_local(bm, pq_c + uz * 19.0, ux, uy, uz, 49.0, 47.0, 0.8, mat_idx=8)
    for fl_q in range(4):
        zq = 5.5 + fl_q * 3.5
        add_box_local(bm, pq_c + uz * zq, ux, uy, uz, 48.6, 46.6, 0.35, mat_idx=0)

    # 6d. Camera 2 Foreground Avenue du Casino Bridge Parapet & Dark Metal Guardrail (`[2321.50, 45.76]`, hdg=65°)
    br_p0 = Vector((2316.0, 44.2, 0.0))
    br_p1 = Vector((2346.0, 39.5, 0.0))
    br_v = br_p1 - br_p0
    br_l = br_v.length
    br_u = br_v.normalized()
    br_r = Vector((br_u.y, -br_u.x, 0.0))
    br_mid = (br_p0 + br_p1) * 0.5
    # Concrete bridge curb
    add_box_local(bm, br_mid + uz * 0.16, br_r, br_u, uz, 0.45, br_l, 0.32, mat_idx=2)
    # 3 horizontal dark-metal bridge guardrail bars + vertical posts
    for z_bar in (0.48, 0.76, 1.04):
        add_box_local(bm, br_mid + uz * z_bar, br_r, br_u, uz, 0.12, br_l, 0.10, mat_idx=10)
    for k_post in range(14):
        pp = br_p0.lerp(br_p1, k_post / 13.0)
        add_box_local(bm, pp + uz * 0.62, br_r, br_u, uz, 0.16, 0.16, 1.15, mat_idx=10)

    # 6e. Camera 3 Foreground Planted Median Curb & White Security Gate (`[2318.48, -14.84]`, hdg=15°)
    add_box_local(bm, Vector((2332.0, 16.0, 0.18)), ux, uy, uz, 9.0, 26.0, 0.36, mat_idx=6)
    add_box_local(bm, Vector((2327.3, 16.0, 0.22)), ux, uy, uz, 0.45, 26.4, 0.44, mat_idx=2)
    # White security barrier gate on right of Camera 3 (`X = 2331..2342, Y = 3.2`)
    add_box_local(bm, Vector((2336.5, 3.2, 0.75)), ux, uy, uz, 9.5, 0.22, 1.35, mat_idx=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.24)
    return obj


def main():
    print(f"\n=== Building {BLOCK_ID}: Casino de Montréal & Île Notre-Dame Lagoon ===")
    clear_scene()
    setup_render_engine()
    setup_world_sky()
    dossier = load_dossier(BLOCK_ID)

    owned_col = bpy.data.collections.new(f"{BLOCK_ID}_Owned")
    bpy.context.scene.collection.children.link(owned_col)

    mats = build_corridor_material_palette()
    build_ground_and_streets(owned_col, dossier)
    build_casino_montreal_and_lagoon(owned_col, dossier, mats)

    # Skip the raw OSM footprints of the Casino Rotunda, NE Wing & Boardwalk so our custom
    # cantilevered 3D architectural model is not intersected by flat generic boxes
    skip_boxes = [
        (2340.0, 2540.0, -45.0, 165.0),
    ]
    build_corridor_context_buildings(owned_col, dossier, mats, skip_boxes=skip_boxes)

    # Lush Île Notre-Dame park & waterfront trees matching all 4 Street View cameras + Satellite
    extra_trees = [
        # Camera 1 right-side conifer/hedgerow & left-side terrace trees
        (2360.0, 74.0, 1.25),
        (2364.0, 72.5, 1.30),
        (2368.0, 71.0, 1.28),
        (2342.0, 114.0, 1.35),
        (2335.0, 122.0, 1.40),
        # Camera 2 foreground/midground large park tree framing the Casino bridge view
        (2336.0, 52.5, 1.65),
        (2344.0, 62.0, 1.45),
        (2348.0, 26.0, 1.35),
        # Camera 3 left-side Chemin des Floralies dense tree line & midground island trees
        (2309.0, -4.0, 1.60),
        (2310.5, 8.0, 1.55),
        (2312.0, 20.0, 1.50),
        (2313.5, 32.0, 1.45),
        (2326.0, 36.0, 1.35),
        # North-West wooded park quadrant (visible in satellite_topdown.png top-left)
        (2365.0, 148.0, 1.45),
        (2378.0, 152.0, 1.50),
        (2392.0, 156.0, 1.42),
        (2405.0, 160.0, 1.38),
        # East water garden edge
        (2492.0, 145.0, 1.30),
    ]
    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=80)

    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Build Successfully ===")


if __name__ == "__main__":
    main()
