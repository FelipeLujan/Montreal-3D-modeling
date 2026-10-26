#!/usr/bin/env python3
"""
Refine & Build MTL-OLY-0010 — Iteration 2 (Le Village olympique — Twin 19-Story Stepped
Brutalist Pyramids, Rue Sherbrooke Est, Boulevard Viau, Stade Saputo & Parc Maisonneuve)
=============================================================================================
Implements all Iteration 2 surgical remodeling prescriptions (`RSI-011`):
  1. Partitioned Parkland & Urban Land-Use Ground Hierarchy (`MTL_Park_Paths_Lawns_And_Courts`):
     - Converts exposed block terrain to rich Poly Haven PBR grass lawns (`Mat_PH_Lush_Park_Grass`)
       boolean-clipped against the street/curb/sidewalk union so zero monochromatic grey base
       remains in `Google_Maps_Satellite_TopDown` or `SE_Iso`/`SW_Iso`/`NW_Iso`/`NE_Iso`.
     - Builds dark-asphalt surface parking courts (`Mat_MTL_Base_Asphalt` / `roof_bitumen`) with
       3D white parking stall striping and planted tree islands north & west of the Twin Pyramids
       (fixing `NE_Iso`), around Hôtel Universel, 5100 Boulevard Viau, and east of Stade Saputo.
     - Builds sculpted green forecourt berms, diagonal concrete pedestrian walkways, and the
       secondary turf training field near Stade Saputo.
  2. Le Village Olympique Twin 19-Story Stepped Brutalist Pyramids (`Mat_OLY_Warm_Buff_Precast`):
     - Authentic warm sand / ochre-buff precast concrete (`#C8BBA8`) on all 19 stepped balcony
       parapets, inclined structural A-frame buttress ribs, vertical unit-bay party-wall fins,
       and monumental elevator/service core towers.
     - Continuous lush green balcony planter troughs (`park_grass`) along BOTH flanks and the
       stepped noses of every floor tier (`fl = 0..18`).
     - Central triangular/pyramidal glazed skylight atrium & 2–3 story horizontal commercial
       podium along Rue Sherbrooke Est with warm precast spandrels and rooftop garden terraces.
  3. Commercial & Institutional Rooftop Realism (`V6–V8` in Satellite & `SE_Iso`):
     - Eliminates all flat white roofs on eastern/southeastern buildings, replacing them with
       weathered gravel ballast (`roof_light_gravel`), dark grey membrane (`roof_grey_tiles`),
       raised perimeter parapet copings, 3D rooftop HVAC condenser banks, and linear skylights.
  4. Stade Saputo Structural Steel Space-Frame Canopy Trusses & Bowl Detailing:
     - Adds exposed galvanized steel truss ribs & cantilevered diagonal struts across the stadium
       canopy roofs, vomitory portals, and perimeter concourse gates.
  5. Lush Mature Deciduous Canopy Framing (`1.6x–2.1x` crown scale) across `H3–H6` in all 4
     Street View corridors.
"""

import json
import math
import os
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
REPO_ROOT = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import blender_lib
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union
from blender_lib import (
    clean_scene,
    setup_render_engine,
    load_dossier,
    setup_world_lighting,
    setup_collection_hierarchy,
    build_ground_and_streets,
    build_corridor_material_palette,
    build_corridor_context_buildings,
    build_corridor_foliage_and_props,
    create_pbr_material,
    add_box_local,
    add_cylinder_along,
    apply_world_box_uv,
    append_kit_object,
    export_block_artifacts,
    POLYHAVEN_DIR,
)

BLOCK_ID = "MTL-OLY-0010"


def _add_stepped_pyramid_wing(
    bm: bmesh.types.BMesh,
    core_xy: Vector,
    u_wing: Vector,
    wing_max_len: float,
    wing_base_w: float,
    n_floors: int = 19,
    floor_h: float = 3.12,
    step_per_floor: float = 4.6,
    mat_conc: int = 0,
    mat_trim: int = 11,
    mat_glass: int = 2,
    mat_metal: int = 10,
    mat_grass: int = 7,
    mat_roof: int = 12,
    mat_sky_glass: int = 3,
):
    """
    Builds one flared 19-story stepped Brutalist wing of Le Village olympique:
    - Warm sand/ochre-buff cantilevered precast concrete balcony parapets with shadow grooves
    - Continuous lush green balcony planter troughs along BOTH longitudinal flanks & stepped nose
    - Projecting vertical precast fin party-wall dividers between apartment bays every 3.6m
    - Floor-by-floor recessed dark-bronze glazing ribbons with vertical mullions & deep soffits
    - Inclined structural concrete A-frame buttress ribs on the stepped nose
    - Weathered gravel roof deck with skylights & mechanical penthouses
    """
    uz = Vector((0.0, 0.0, 1.0))
    u_perp = Vector((-u_wing.y, u_wing.x, 0.0)).normalized()

    for fl in range(n_floors):
        z0 = fl * floor_h
        z1 = z0 + floor_h
        w_len = max(18.0, wing_max_len - fl * step_per_floor)
        w_width = max(14.5, wing_base_w - fl * 0.24)
        mid_s = 6.0 + w_len * 0.5
        c_fl = core_xy + u_wing * mid_s

        # 1. Warm sand/buff cantilevered concrete floor slab & angled Brutalist balcony parapet (lower 1.30m)
        add_box_local(
            bm,
            c_fl + uz * (z0 + 0.65),
            u_wing,
            u_perp,
            uz,
            w_len,
            w_width,
            1.30,
            mat_idx=mat_conc if fl % 2 == 0 else mat_trim,
        )
        # Warm buff precast coping & deep horizontal shadow-gap groove
        add_box_local(
            bm,
            c_fl + uz * (z0 + 1.26),
            u_wing,
            u_perp,
            uz,
            w_len + 0.28,
            w_width + 0.28,
            0.16,
            mat_idx=mat_trim,
        )
        # Continuous green balcony planter troughs along both longitudinal balcony ledges (+u_perp & -u_perp)
        for side_s in (-1.0, 1.0):
            add_box_local(
                bm,
                c_fl + u_perp * (side_s * (w_width * 0.5 - 0.42)) + uz * (z0 + 1.36),
                u_wing,
                u_perp,
                uz,
                w_len - 1.2,
                0.72,
                0.24,
                mat_idx=mat_grass,
            )

        # 2. Recessed dark-bronze residential glazing band (Z = z0 + 1.30 .. z1 - 0.28)
        glaz_h = floor_h - 1.58
        glaz_z = z0 + 1.30 + glaz_h * 0.5
        glaz_len = max(12.0, w_len - 2.0)
        glaz_w = w_width - 1.8
        add_box_local(
            bm,
            c_fl + uz * glaz_z,
            u_wing,
            u_perp,
            uz,
            glaz_len,
            glaz_w,
            glaz_h,
            mat_idx=mat_glass,
        )
        # Projecting vertical precast fin party-wall dividers & dark-bronze mullions every 3.6m
        n_bays = max(3, int(glaz_len // 3.6))
        for b_i in range(n_bays + 1):
            s_bay = -glaz_len * 0.5 + (b_i / n_bays) * glaz_len
            p_bay = c_fl + u_wing * s_bay + uz * glaz_z
            is_fin = (b_i % 2 == 0)
            for side_s in (-1.0, 1.0):
                add_box_local(
                    bm,
                    p_bay + u_perp * (side_s * (glaz_w * 0.5 + (0.38 if is_fin else 0.08))),
                    u_wing,
                    u_perp,
                    uz,
                    0.36 if is_fin else 0.16,
                    0.85 if is_fin else 0.24,
                    glaz_h + 0.12,
                    mat_idx=mat_conc if is_fin else mat_metal,
                )

        # 3. Upper floor slab overhang (deep balcony soffit)
        add_box_local(
            bm,
            c_fl + uz * (z1 - 0.14),
            u_wing,
            u_perp,
            uz,
            w_len,
            w_width,
            0.28,
            mat_idx=mat_conc,
        )

        # 4. Stepped end terrace greenery planter bed + structural inclined A-frame buttress fins on nose
        nose_s = 6.0 + w_len
        nose_pt = core_xy + u_wing * (nose_s - 1.9)
        add_box_local(
            bm,
            nose_pt + uz * (z0 + 1.40),
            u_wing,
            u_perp,
            uz,
            3.6,
            w_width - 1.0,
            0.34,
            mat_idx=mat_grass,
        )
        for fin_y in (-w_width * 0.38, -w_width * 0.14, w_width * 0.14, w_width * 0.38):
            add_box_local(
                bm,
                core_xy + u_wing * (nose_s - 0.5) + u_perp * fin_y + uz * (z0 + floor_h * 0.5),
                u_wing,
                u_perp,
                uz,
                2.6,
                0.62,
                floor_h + 0.18,
                mat_idx=mat_trim,
            )

    # Top roof deck (Z = n_floors * floor_h) with weathered gravel membrane, parapet & skylights
    top_z = n_floors * floor_h
    top_len = max(18.0, wing_max_len - (n_floors - 1) * step_per_floor)
    top_w = max(14.5, wing_base_w - (n_floors - 1) * 0.24)
    top_c = core_xy + u_wing * (6.0 + top_len * 0.5)
    add_box_local(bm, top_c + uz * (top_z + 0.20), u_wing, u_perp, uz, top_len - 1.0, top_w - 1.0, 0.40, mat_idx=mat_roof)
    for sk_i in range(3):
        sk_s = -top_len * 0.32 + sk_i * (top_len * 0.32)
        sk_p = top_c + u_wing * sk_s + uz * (top_z + 0.95)
        add_box_local(bm, sk_p, u_wing, u_perp, uz, 4.0, 3.4, 1.35, mat_idx=mat_conc)
        add_box_local(bm, sk_p + uz * 0.78, u_wing, u_perp, uz, 3.6, 3.0, 0.35, mat_idx=mat_sky_glass)


def _add_rooftop_hvac_and_skylights(
    bm: bmesh.types.BMesh,
    center_xy: Vector,
    u_dir: Vector,
    v_dir: Vector,
    roof_z: float,
    span_u: float,
    span_v: float,
    mat_pent: int = 11,
    mat_metal: int = 10,
    mat_glass: int = 3,
    mat_dark_roof: int = 14,
):
    """Populates a commercial/institutional flat roof with articulated 3D HVAC units, chillers, and skylights."""
    uz = Vector((0.0, 0.0, 1.0))
    # Central mechanical penthouse with dark bitumen roof & louvered equipment screen
    pw = min(18.0, span_u * 0.32)
    pd = min(12.0, span_v * 0.30)
    pc = center_xy + uz * (roof_z + 1.25)
    add_box_local(bm, pc, u_dir, v_dir, uz, pw, pd, 2.5, mat_idx=mat_pent)
    add_box_local(bm, pc + uz * 1.35, u_dir, v_dir, uz, pw + 0.4, pd + 0.4, 0.25, mat_idx=mat_dark_roof)
    # Arrayed HVAC condenser banks & fan cowls
    for hx_i in (-1, 1):
        for hy_i in (-1, 1):
            hc = center_xy + u_dir * (hx_i * span_u * 0.26) + v_dir * (hy_i * span_v * 0.24) + uz * (roof_z + 0.75)
            add_box_local(bm, hc, u_dir, v_dir, uz, 4.2, 3.2, 1.5, mat_idx=mat_metal)
            add_cylinder_along(bm, hc + uz * 0.75, hc + uz * 1.15, 1.05, 1.05, segs=10, mat_idx=mat_dark_roof)
    # Linear glazed rooftop skylights
    for sy_i in (-0.14, 0.14):
        sk_c = center_xy + v_dir * (span_v * sy_i) + uz * (roof_z + 0.45)
        add_box_local(bm, sk_c, u_dir, v_dir, uz, min(22.0, span_u * 0.45), 2.4, 0.65, mat_idx=mat_metal)
        add_box_local(bm, sk_c + uz * 0.38, u_dir, v_dir, uz, min(21.4, span_u * 0.44), 2.1, 0.22, mat_idx=mat_glass)


def build_parkland_lawns_paths_and_parking(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Creates the dedicated `MTL_Park_Paths_Lawns_And_Courts` mesh (protected from pavement
    sanitization and boolean-clipped against `_LAST_ROAD_UNION`) so the block ground is
    richly partitioned into PBR grass lawns, dark asphalt parking courts with white stall
    markings, and concrete walkways/plazas (`RSI-011`).
    """
    # 1. Convert MTL_Ground_Base and outer superblock ground to rich botanical park grass
    #    so zero barren grey void exists anywhere outside paved lots/plazas/roads!
    for gname in ("MTL_Ground_Base", f"{BLOCK_ID}_Ground_And_River"):
        g_obj = bpy.data.objects.get(gname)
        if g_obj and g_obj.type == "MESH" and g_obj.data:
            if gname == "MTL_Ground_Base":
                g_obj.data.materials.clear()
                g_obj.data.materials.append(mats["park_grass"])
            elif len(g_obj.data.materials) >= 1:
                g_obj.data.materials[0] = mats["park_grass"]

    mesh = bpy.data.meshes.new("MTL_Park_Paths_Lawns_And_Courts")
    obj = bpy.data.objects.new("MTL_Park_Paths_Lawns_And_Courts", mesh)
    col.objects.link(obj)

    # Materials on MTL_Park_Paths_Lawns_And_Courts:
    # 0: park_grass (Lush PBR turf berms & training fields)
    # 1: plaza_beige (Concrete plazas, stadium concourse & park paths)
    # 2: roof_bitumen (Dark asphalt surface parking courts)
    # 3: white_trim (3D white parking stall stripes & soccer training pitch lines)
    # 4: concrete_podium (Curbed median islands & retaining walls)
    for k in ("park_grass", "plaza_beige", "roof_bitumen", "white_trim", "concrete_podium"):
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    ux = Vector((1.0, 0.0, 0.0))
    uy = Vector((0.0, 1.0, 0.0))
    uz = Vector((0.0, 0.0, 1.0))
    u_viau = Vector((0.4226, 0.9063, 0.0)).normalized()
    u_sher = Vector((0.9063, -0.4226, 0.0)).normalized()
    u_pitch = Vector((-0.212, 0.977, 0.0)).normalized()
    r_pitch = Vector((u_pitch.y, -u_pitch.x, 0.0)).normalized()

    road_u = getattr(blender_lib, "_LAST_ROAD_UNION", None) or dossier.get("_road_union")
    road_keepout = road_u.buffer(2.55) if (road_u is not None and not road_u.is_empty) else Polygon()

    def _add_clipped_box_2d(center_xy: Vector, u_ax: Vector, v_ax: Vector, sx: float, sy: float, z_top: float, mat_idx: int, z_bot: float = 0.005):
        hx, hy = sx * 0.5, sy * 0.5
        pts = [
            (center_xy.x - u_ax.x * hx - v_ax.x * hy, center_xy.y - u_ax.y * hx - v_ax.y * hy),
            (center_xy.x + u_ax.x * hx - v_ax.x * hy, center_xy.y + u_ax.y * hx - v_ax.y * hy),
            (center_xy.x + u_ax.x * hx + v_ax.x * hy, center_xy.y + u_ax.y * hx + v_ax.y * hy),
            (center_xy.x - u_ax.x * hx + v_ax.x * hy, center_xy.y - u_ax.y * hx + v_ax.y * hy),
        ]
        poly = Polygon(pts)
        if not road_keepout.is_empty:
            poly = poly.difference(road_keepout)
        if poly.is_empty:
            return
        blender_lib._extrude_shapely_to_bmesh(bm, poly, z_bot=z_bot, z_top=z_top, mat_idx_top=mat_idx, mat_idx_side=mat_idx, max_step=4.0)

    def _add_parking_stalls(lot_c: Vector, u_row: Vector, v_stall: Vector, row_offsets: list, n_stalls: int, stall_spacing: float = 2.85, stall_len: float = 4.8, z_stripe: float = 0.056):
        for r_off in row_offsets:
            row_origin = lot_c + v_stall * r_off
            span_row = n_stalls * stall_spacing
            # Spine line
            p_s0 = row_origin - u_row * (span_row * 0.5)
            p_s1 = row_origin + u_row * (span_row * 0.5)
            if road_keepout.is_empty or not road_keepout.intersects(LineString([(p_s0.x, p_s0.y), (p_s1.x, p_s1.y)])):
                add_box_local(bm, row_origin + uz * z_stripe, u_row, v_stall, uz, span_row, 0.18, 0.016, mat_idx=3)
            for s_i in range(-n_stalls // 2, n_stalls // 2 + 1):
                sp_c = row_origin + u_row * (s_i * stall_spacing)
                if not road_keepout.is_empty and road_keepout.contains(Point(sp_c.x, sp_c.y)):
                    continue
                add_box_local(bm, sp_c + uz * z_stripe, u_row, v_stall, uz, 0.14, stall_len, 0.016, mat_idx=3)

    # -------------------------------------------------------------------------
    # A. DARK ASPHALT SURFACE PARKING COURTS WITH WHITE STALL STRIPING & ISLANDS
    # -------------------------------------------------------------------------
    # 1. West Pyramid Western Parking Court (X=18..104, Y=6880..6978, H1..H2, V1..V2)
    w_lot_c = Vector((58.0, 6932.0, 0.0))
    _add_clipped_box_2d(w_lot_c, ux, uy, 82.0, 92.0, z_top=0.045, mat_idx=2)
    _add_parking_stalls(w_lot_c, uy, ux, [-26.0, -8.0, 10.0, 28.0], n_stalls=22)
    # Planted green islands inside West Pyramid lot
    for ix_o in (-17.0, 1.0, 19.0):
        _add_clipped_box_2d(w_lot_c + Vector((ix_o, 0.0, 0.0)), ux, uy, 3.2, 74.0, z_top=0.085, mat_idx=0, z_bot=0.040)

    # 2. North Concave Rear Parking & Service Courts behind West & East Pyramids (Fixing NE_Iso!)
    n_rear_w = Vector((145.0, 7015.0, 0.0))
    _add_clipped_box_2d(n_rear_w, u_sher, u_viau, 115.0, 68.0, z_top=0.045, mat_idx=2)
    _add_parking_stalls(n_rear_w, u_sher, u_viau, [-18.0, 0.0, 18.0], n_stalls=26)
    n_rear_e = Vector((265.0, 7095.0, 0.0))
    _add_clipped_box_2d(n_rear_e, u_sher, u_viau, 110.0, 64.0, z_top=0.045, mat_idx=2)
    _add_parking_stalls(n_rear_e, u_sher, u_viau, [-16.0, 2.0, 18.0], n_stalls=24)

    # 3. Hôtel Universel Curved Front & Side Asphalt Parking Court (X=205..272, Y=6735..6848, H3..H5, V4..V5)
    hu_lot_c = Vector((242.0, 6788.0, 0.0))
    _add_clipped_box_2d(hu_lot_c, u_viau, u_sher, 104.0, 62.0, z_top=0.045, mat_idx=2)
    _add_parking_stalls(hu_lot_c, u_viau, u_sher, [-18.0, -2.0, 14.0], n_stalls=24)

    # 4. 5100 Boulevard Viau Eastern Surface Parking Lot (X=335..405, Y=6855..6978, H1..H3, V6..V7)
    viau_lot_c = Vector((352.0, 6912.0, 0.0))
    _add_clipped_box_2d(viau_lot_c, u_viau, u_sher, 128.0, 44.0, z_top=0.045, mat_idx=2)
    _add_parking_stalls(viau_lot_c, u_viau, u_sher, [-12.0, 8.0], n_stalls=30)

    # 5. Eastern Industrial Concrete Loading Apron & Truck Yard (X=385..520, Y=6885..6976, H1..H2, V7..V8)
    yard_c = Vector((458.0, 6922.0, 0.0))
    _add_clipped_box_2d(yard_c, u_viau, u_sher, 78.0, 114.0, z_top=0.042, mat_idx=1)
    # East Sherbrooke Institutional Complex Apron & Parking Lot (X=435..533, Y=6605..6845, H3..H6, V8)
    e_apron_c = Vector((488.0, 6725.0, 0.0))
    _add_clipped_box_2d(e_apron_c, u_viau, u_sher, 210.0, 88.0, z_top=0.038, mat_idx=1)
    e_west_lot = Vector((452.0, 6705.0, 0.0))
    _add_clipped_box_2d(e_west_lot, u_viau, u_sher, 94.0, 32.0, z_top=0.046, mat_idx=2)
    _add_parking_stalls(e_west_lot, u_viau, u_sher, [-7.0, 7.0], n_stalls=22)

    # 6. Stade Saputo Perimeter Concourse Plaza & Eastern Tree-Lined Parking Lot (H6..H8, V5..V8)
    saputo_apron = Vector((308.0, 6525.0, 0.0))
    _add_clipped_box_2d(saputo_apron, r_pitch, u_pitch, 152.0, 165.0, z_top=0.038, mat_idx=1)
    e_sap_lot = Vector((478.0, 6498.0, 0.0))
    _add_clipped_box_2d(e_sap_lot, r_pitch, u_pitch, 104.0, 116.0, z_top=0.045, mat_idx=2)
    _add_parking_stalls(e_sap_lot, u_pitch, r_pitch, [-34.0, -12.0, 10.0, 32.0], n_stalls=26)
    for sx_isl in (-23.0, -1.0, 21.0):
        _add_clipped_box_2d(e_sap_lot + r_pitch * sx_isl, r_pitch, u_pitch, 3.6, 96.0, z_top=0.095, mat_idx=0, z_bot=0.040)

    # -------------------------------------------------------------------------
    # B. SCULPTED GREEN FORECOURT BERMS, TRAINING TURF FIELDS & PARK WALKWAYS
    # -------------------------------------------------------------------------
    # 1. Sculpted Green Forecourt Berm in front of West Pyramid (V2..V4, H2..H4)
    berm_c = Vector((142.0, 6842.0, 0.0))
    _add_clipped_box_2d(berm_c, u_viau, u_sher, 132.0, 78.0, z_top=0.065, mat_idx=0)
    _add_clipped_box_2d(berm_c + u_viau * 8.0, u_viau, u_sher, 84.0, 44.0, z_top=0.18, mat_idx=0, z_bot=0.055)

    # 2. Diagonal Concrete Walkways across the Olympic Village Forecourt & Parc Maisonneuve
    for p_w0, p_w1, w_walk in (
        (Vector((84.0, 6818.0, 0.0)), Vector((156.0, 6752.0, 0.0)), 3.6),
        (Vector((118.0, 6872.0, 0.0)), Vector((156.0, 6758.0, 0.0)), 3.2),
        (Vector((118.0, 6872.0, 0.0)), Vector((172.0, 6912.0, 0.0)), 3.2),
        (Vector((74.0, 6805.0, 0.0)), Vector((138.0, 6935.0, 0.0)), 4.8),
        # Parc Maisonneuve sinuous concrete trails (V1..V3, H4..H8)
        (Vector((-1.5, 6738.0, 0.0)), Vector((38.0, 6695.0, 0.0)), 4.0),
        (Vector((38.0, 6695.0, 0.0)), Vector((58.0, 6635.0, 0.0)), 4.0),
        (Vector((58.0, 6635.0, 0.0)), Vector((62.0, 6545.0, 0.0)), 4.0),
        (Vector((62.0, 6545.0, 0.0)), Vector((76.0, 6443.0, 0.0)), 4.0),
        (Vector((-1.5, 6685.0, 0.0)), Vector((38.0, 6640.0, 0.0)), 3.2),
        (Vector((38.0, 6640.0, 0.0)), Vector((88.0, 6550.0, 0.0)), 3.2),
        (Vector((58.0, 6672.0, 0.0)), Vector((142.0, 6718.0, 0.0)), 3.4),
    ):
        dv = p_w1 - p_w0
        dlen = dv.length
        if dlen > 1.0:
            uw_dir = dv.normalized()
            uw_perp = Vector((-uw_dir.y, uw_dir.x, 0.0))
            _add_clipped_box_2d(p_w0.lerp(p_w1, 0.5), uw_dir, uw_perp, dlen, w_walk, z_top=0.088, mat_idx=1, z_bot=0.020)

    # 3. Secondary Green Lawn & Turf Pad between Hôtel Universel & Industrial Complex (X=330..385, Y=6745..6835, H3..H5, V6..V7)
    e_lawn_c = Vector((362.0, 6785.0, 0.0))
    _add_clipped_box_2d(e_lawn_c, u_viau, u_sher, 86.0, 54.0, z_top=0.072, mat_idx=0, z_bot=0.020)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.22)
    print(f"[{BLOCK_ID}] Built partitioned parkland lawns, walkways & asphalt parking courts ({len(mesh.polygons):,} faces).")
    return obj


def build_olympic_village_and_campus_landmarks(col: bpy.types.Collection, mats: dict):
    """
    Builds the primary BMesh hero assembly for MTL-OLY-0010 (Iteration 2):
      - Le Village olympique Twin 19-Story Stepped Brutalist Pyramids in authentic warm
        sand/ochre-buff precast concrete (`Mat_OLY_Warm_Buff_Precast`) with continuous
        balcony planter greenery, vertical bay fin dividers, central pyramidal skylight
        atrium, and Rue Sherbrooke Est commercial podium
      - Hôtel Universel Montréal (5000 Rue Sherbrooke Est) & 5100 Boulevard Viau Complex
      - Stade Saputo with exposed galvanized steel space-frame canopy trusses & bowl tiers
      - Eastern Commercial & Institutional Complexes with weathered gravel/bitumen roofs,
        parapet copings, rooftop HVAC condenser banks, and linear skylights
    """
    # Create dedicated warm sand/ochre-buff precast concrete materials for Le Village olympique (`RSI-011`)
    mat_warm_buff = create_pbr_material(
        "Mat_OLY_Warm_Buff_Precast",
        base_color=(0.79, 0.71, 0.58, 1.0),
        roughness=0.68,
        diffuse_tex=str(POLYHAVEN_DIR / "sandstone_blocks_04_diff_2k.jpg"),
        normal_tex=str(POLYHAVEN_DIR / "sandstone_blocks_04_nor_gl_2k.jpg"),
        rough_tex=str(POLYHAVEN_DIR / "sandstone_blocks_04_rough_2k.jpg"),
        tint_color=(0.80, 0.72, 0.58),
        tint_strength=0.58,
        uv_scale=0.24,
    )
    mat_warm_trim = create_pbr_material(
        "Mat_OLY_Warm_Buff_Trim",
        base_color=(0.84, 0.77, 0.65, 1.0),
        roughness=0.62,
        diffuse_tex=str(POLYHAVEN_DIR / "concrete_tile_facade_diff_2k.jpg"),
        normal_tex=str(POLYHAVEN_DIR / "concrete_tile_facade_nor_gl_2k.jpg"),
        tint_color=(0.84, 0.77, 0.65),
        tint_strength=0.62,
        uv_scale=0.25,
    )

    mesh = bpy.data.meshes.new("MTL_Olympic_Village_And_Saputo_Hero")
    obj = bpy.data.objects.new("MTL_Olympic_Village_And_Saputo_Hero", mesh)
    col.objects.link(obj)

    mat_list = [
        mat_warm_buff,                  # 0: Warm sand/ochre-buff precast Brutalist pyramid concrete
        mats["concrete_podium"],        # 1: Podiums, retaining walls & stadium structure
        mats["dark_glass"],             # 2: Recessed dark-bronze glazing ribbons & windows
        mats["blue_curtain_glass"],     # 3: Stade Saputo blue seating bowl & skylights
        mats["white_trim"],             # 4: Stade Saputo canopy roof & pitch lines
        mats["cream_stucco"],           # 5: Hôtel Universel cream precast facade
        mats["water_river"],            # 6: Hôtel Universel courtyard swimming pool
        mats["park_grass"],             # 7: Balcony planter greenery & soccer pitch turf
        mats["plaza_beige"],            # 8: Concrete coping & plaza trim
        mats["terracotta_vivid"],       # 9: Accent vehicles & architectural signage totems
        mats["dark_metal"],             # 10: Mullions, canopies, stadium steel trusses & HVAC banks
        mat_warm_trim,                  # 11: Warm buff precast balcony coping & buttress ribs
        mats["roof_light_gravel"],      # 12: Weathered gravel ballast flat roof decks
        mats["roof_grey_tiles"],        # 13: Industrial/institutional dark grey roof membranes
        mats["roof_bitumen"],           # 14: Dark bitumen mechanical penthouse roofs
        mats["sandstone_brick"],        # 15: Olympic Village reddish-brown brick annex
    ]
    for m in mat_list:
        obj.data.materials.append(m)

    bm = bmesh.new()
    ux = Vector((1.0, 0.0, 0.0))
    uy = Vector((0.0, 1.0, 0.0))
    uz = Vector((0.0, 0.0, 1.0))

    u_viau = Vector((0.4226, 0.9063, 0.0)).normalized()
    u_sher = Vector((0.9063, -0.4226, 0.0)).normalized()

    # =========================================================================
    # 1. LE VILLAGE OLYMPIQUE — TWIN 19-STORY STEPPED BRUTALIST PYRAMIDS
    #    Warm Sand/Ochre-Buff Precast Concrete, Continuous Balcony Planters,
    #    Vertical Bay Fin Dividers, Central Skylight Atrium & Sherbrooke Podium
    # =========================================================================
    west_core = Vector((156.0, 6962.0, 0.0))
    # Primary 144m SSW Wing extending down toward Rue Sherbrooke Est along -u_viau
    _add_stepped_pyramid_wing(
        bm,
        core_xy=west_core,
        u_wing=-u_viau,
        wing_max_len=144.0,
        wing_base_w=22.5,
        n_floors=19,
        floor_h=3.12,
        step_per_floor=4.8,
    )
    # Secondary NNW Wing & ENE Wing flaring from the northern core
    u_nnw = Vector((-0.78, 0.625, 0.0)).normalized()
    _add_stepped_pyramid_wing(
        bm,
        core_xy=west_core,
        u_wing=u_nnw,
        wing_max_len=84.0,
        wing_base_w=20.5,
        n_floors=19,
        floor_h=3.12,
        step_per_floor=3.2,
    )
    # Central Triangular/Pyramidal Skylight Atrium & 2-Story Commercial Podium Base ([136, 6888])
    podium_c = Vector((134.0, 6892.0, 0.0))
    add_box_local(bm, podium_c + uz * 3.8, u_viau, u_sher, uz, 46.0, 34.0, 7.6, mat_idx=0)
    add_box_local(bm, podium_c + uz * 7.8, u_viau, u_sher, uz, 47.0, 35.0, 0.45, mat_idx=11)
    add_box_local(bm, podium_c + uz * 8.1, u_viau, u_sher, uz, 43.0, 31.0, 0.25, mat_idx=7)
    for fl_pod in (2.2, 5.6):
        add_box_local(bm, podium_c - u_sher * 17.1 + uz * fl_pod, u_viau, u_sher, uz, 40.0, 0.25, 1.85, mat_idx=2)
        add_box_local(bm, podium_c + u_sher * 17.1 + uz * fl_pod, u_viau, u_sher, uz, 40.0, 0.25, 1.85, mat_idx=2)
    # Pyramidal Glazed Skylight Atrium Crown above the Podium (Z = 8.2m .. 13.5m)
    for sk_tier in range(4):
        sk_w = 18.0 - sk_tier * 3.8
        sk_z = 8.4 + sk_tier * 1.15
        add_box_local(bm, podium_c + uz * sk_z, u_viau, u_sher, uz, sk_w, sk_w, 1.10, mat_idx=3 if sk_tier > 0 else 10)

    # Monumental 22-story Vertical Brutalist Elevator & Service Core Tower on SE flank ([164, 6938])
    elev_tower_c = Vector((164.0, 6938.0, 0.0))
    tower_h = 67.5
    add_box_local(bm, elev_tower_c + uz * (tower_h * 0.5), u_viau, u_sher, uz, 15.8, 13.8, tower_h, mat_idx=11)
    add_box_local(bm, elev_tower_c + uz * (tower_h + 1.2), u_viau, u_sher, uz, 16.5, 14.5, 2.4, mat_idx=0)
    for fl_t in range(21):
        zt = 2.5 + fl_t * 3.05
        for side_s in (-1.0, 1.0):
            add_box_local(bm, elev_tower_c + u_sher * (side_s * 6.95) + uz * zt, u_viau, u_sher, uz, 8.5, 0.24, 1.55, mat_idx=2)
            add_box_local(bm, elev_tower_c + u_viau * (side_s * 7.95) + uz * zt, u_sher, u_viau, uz, 6.5, 0.24, 1.55, mat_idx=2)

    # 4-Story Reddish-Brown Brick & Precast Annex East of the Core ([188, 6956], H1, V3..V4 in satellite)
    annex_c = Vector((188.0, 6956.0, 0.0))
    annex_h = 15.5
    add_box_local(bm, annex_c + uz * 2.0, u_viau, u_sher, uz, 34.0, 22.0, 4.0, mat_idx=0)
    add_box_local(bm, annex_c + uz * (4.0 + (annex_h - 4.0) * 0.5), u_viau, u_sher, uz, 33.5, 21.5, annex_h - 4.0, mat_idx=15)
    add_box_local(bm, annex_c + uz * (annex_h + 0.35), u_viau, u_sher, uz, 34.4, 22.4, 0.70, mat_idx=11)
    add_box_local(bm, annex_c + uz * (annex_h + 0.15), u_viau, u_sher, uz, 31.5, 19.5, 0.30, mat_idx=12)
    for fl_a in range(4):
        za = 2.2 + fl_a * 3.3
        for b_a in range(-3, 4):
            for s_side in (-1.0, 1.0):
                wp = annex_c + u_viau * (b_a * 4.2) + u_sher * (s_side * 10.85) + uz * za
                add_box_local(bm, wp, u_viau, u_sher, uz, 2.4, 0.22, 1.65, mat_idx=2)
                add_box_local(bm, wp - uz * 0.92, u_viau, u_sher, uz, 2.6, 0.32, 0.16, mat_idx=11)

    # East Pyramid (`Pavillon Est`) & Southern Flyover Pyramid Pair in matching warm buff precast
    for py_cx, py_cy, py_ang_deg in (
        (255.0, 7045.0, 14.0),
        (185.0, 6310.0, -18.0),
        (335.0, 6360.0, 14.0),
    ):
        p_core = Vector((py_cx, py_cy, 0.0))
        base_rad = math.radians(py_ang_deg)
        u_b0 = Vector((math.cos(base_rad), math.sin(base_rad), 0.0))
        u_b1 = Vector((-u_b0.y, u_b0.x, 0.0))
        add_box_local(bm, p_core + uz * 32.0, u_b0, u_b1, uz, 20.0, 17.0, 64.0, mat_idx=11)
        for w_deg in (0.0, 115.0, -115.0):
            w_rad = base_rad + math.radians(w_deg)
            uw = Vector((math.cos(w_rad), math.sin(w_rad), 0.0))
            _add_stepped_pyramid_wing(
                bm,
                core_xy=p_core,
                u_wing=uw,
                wing_max_len=78.0,
                wing_base_w=19.8,
                n_floors=19,
                floor_h=3.10,
                step_per_floor=3.15,
            )

    # Parked 3D Vehicles in West Pyramid Lot ([58, 6935])
    w_lot_c = Vector((58.0, 6932.0, 0.0))
    for row_x in (-24.0, -6.0, 12.0, 28.0):
        for k_car in range(-4, 5, 2):
            cp = w_lot_c + Vector((row_x + 3.2, k_car * 6.5, 0.0))
            c_mat = 4 if (k_car + int(row_x)) % 3 == 0 else (10 if k_car % 2 == 0 else 9)
            add_box_local(bm, cp + uz * 0.65, ux, uy, uz, 4.4, 1.85, 1.15, mat_idx=c_mat)
            add_box_local(bm, cp + uz * 1.35, ux, uy, uz, 2.4, 1.65, 0.65, mat_idx=2)

    # =========================================================================
    # 2. HÔTEL UNIVERSEL MONTRÉAL (5000 Rue Sherbrooke Est, X=250..328, Y=6748..6838)
    #    & 5100 BOULEVARD VIAU STEPPED OFFICE COMPLEX (X=265..385, Y=6855..6978)
    # =========================================================================
    hu_c = Vector((286.0, 6786.0, 0.0))
    # White traffic gore markings at intersection foreground (matching Cam 1 H8, V5..V7)
    gore_c = Vector((241.0, 6734.0, 0.0))
    add_box_local(bm, gore_c + uz * 0.055, u_viau, u_sher, uz, 8.5, 0.35, 0.04, mat_idx=4)
    add_box_local(bm, gore_c + u_sher * 2.2 + uz * 0.055, u_viau + u_sher * 0.5, u_sher, uz, 9.0, 0.35, 0.04, mat_idx=4)

    # Parked cars in Hôtel Universel front lot (visible in Cam 1 H6)
    for off_v, off_s, c_mat in [
        (-22.0, -34.0, 4), (-14.0, -32.0, 10), (-5.0, -30.0, 10),
        (6.0, -42.0, 4), (14.0, -40.0, 10), (22.0, -26.0, 3),
        (-18.0, -48.0, 9), (2.0, -50.0, 4), (18.0, -48.0, 10),
    ]:
        p_car = hu_c + u_viau * off_v + u_sher * off_s
        add_box_local(bm, p_car + uz * 0.65, u_sher, u_viau, uz, 4.5, 1.9, 1.15, mat_idx=c_mat)
        add_box_local(bm, p_car + uz * 1.38, u_sher, u_viau, uz, 2.5, 1.7, 0.65, mat_idx=2)

    # Hôtel Universel U-Shaped Building Wings framing the Central Courtyard Swimming Pool
    w_wing_c = hu_c - u_sher * 14.0
    add_box_local(bm, w_wing_c + uz * 5.8, u_viau, u_sher, uz, 56.0, 16.0, 11.6, mat_idx=5)
    add_box_local(bm, w_wing_c + uz * 11.8, u_viau, u_sher, uz, 56.6, 16.6, 0.55, mat_idx=10)
    add_box_local(bm, w_wing_c + uz * 11.65, u_viau, u_sher, uz, 54.5, 14.5, 0.25, mat_idx=12)
    _add_rooftop_hvac_and_skylights(bm, w_wing_c, u_viau, u_sher, 11.8, 52.0, 14.0)
    # Sloped dark-bronze ground-floor entrance awning along the front facade (-u_sher)
    add_box_local(bm, w_wing_c - u_sher * 9.2 + uz * 3.8, u_viau, u_sher, uz, 44.0, 2.8, 0.85, mat_idx=10)
    # Porte-Cochère Canopy on North-West side ([254, 6812])
    add_box_local(bm, w_wing_c + u_viau * 22.0 - u_sher * 14.5 + uz * 4.4, u_viau, u_sher, uz, 11.0, 14.0, 0.90, mat_idx=11)
    for b_hu in range(-5, 6):
        vy_off = b_hu * 4.8
        add_box_local(bm, w_wing_c + u_viau * vy_off - u_sher * 8.15 + uz * 6.0, u_viau, u_sher, uz, 0.55, 0.38, 11.2, mat_idx=5)
        if b_hu < 5:
            for z_win in (2.0, 5.8, 9.2):
                add_box_local(
                    bm,
                    w_wing_c + u_viau * (vy_off + 2.4) - u_sher * 8.05 + uz * z_win,
                    u_viau,
                    u_sher,
                    uz,
                    3.9,
                    0.20,
                    1.85,
                    mat_idx=2,
                )

    # Vertical 5-Story Elevator/Stair Tower at South-West Corner of Hôtel Universel (Cam 1 H5, V7)
    hu_tower_c = w_wing_c - u_viau * 24.0 - u_sher * 2.0
    add_box_local(bm, hu_tower_c + uz * 8.2, u_viau, u_sher, uz, 9.5, 9.5, 16.4, mat_idx=5)
    add_box_local(bm, hu_tower_c + uz * 16.6, u_viau, u_sher, uz, 10.0, 10.0, 0.55, mat_idx=10)

    # North Wing & East 7-Story Hotel Tower Wing framing the Pool Courtyard (with weathered gravel roofs!)
    n_wing_c = hu_c + u_viau * 24.0 + u_sher * 4.0
    add_box_local(bm, n_wing_c + uz * 6.2, u_viau, u_sher, uz, 16.0, 42.0, 12.4, mat_idx=5)
    add_box_local(bm, n_wing_c + uz * 12.5, u_viau, u_sher, uz, 14.5, 40.5, 0.30, mat_idx=12)
    e_wing_c = hu_c - u_viau * 4.0 + u_sher * 20.0
    e_wing_h = 22.5
    add_box_local(bm, e_wing_c + uz * (e_wing_h * 0.5), u_viau, u_sher, uz, 54.0, 16.5, e_wing_h, mat_idx=11)
    add_box_local(bm, e_wing_c + uz * (e_wing_h + 0.3), u_viau, u_sher, uz, 52.0, 14.5, 0.35, mat_idx=12)
    _add_rooftop_hvac_and_skylights(bm, e_wing_c, u_viau, u_sher, e_wing_h + 0.35, 48.0, 13.5)
    for fl_e in range(6):
        ze = 2.6 + fl_e * 3.3
        for b_e in range(-5, 6):
            for s_side in (-1.0, 1.0):
                add_box_local(
                    bm,
                    e_wing_c + u_viau * (b_e * 4.4) + u_sher * (s_side * 8.3) + uz * ze,
                    u_viau,
                    u_sher,
                    uz,
                    2.8,
                    0.22,
                    1.65,
                    mat_idx=2,
                )

    # Courtyard Sun Deck & Turquoise Outdoor Swimming Pool ([288, 6788], H4-V5 in satellite_topdown.png)
    add_box_local(bm, hu_c + u_sher * 2.0 + uz * 0.14, u_viau, u_sher, uz, 34.0, 20.0, 0.16, mat_idx=8)
    add_box_local(bm, hu_c + u_sher * 2.0 + uz * 0.25, u_viau, u_sher, uz, 18.0, 9.5, 0.10, mat_idx=3)

    # 5100 Boulevard Viau 8-Story Stepped Precast Concrete Complex (X=265..385, Y=6855..6978)
    viau_bldg_c = Vector((312.0, 6916.0, 0.0))
    add_box_local(bm, viau_bldg_c + uz * 4.2, u_viau, u_sher, uz, 124.0, 44.0, 8.4, mat_idx=0)
    add_box_local(bm, viau_bldg_c + uz * 8.55, u_viau, u_sher, uz, 122.0, 42.0, 0.30, mat_idx=12)
    for off_v_blk, blk_len, blk_h in ((-28.0, 52.0, 27.5), (30.0, 54.0, 27.5), (1.0, 22.0, 21.0)):
        bc = viau_bldg_c + u_viau * off_v_blk
        add_box_local(bm, bc + uz * (blk_h * 0.5), u_viau, u_sher, uz, blk_len, 28.0, blk_h, mat_idx=0)
        add_box_local(bm, bc + uz * (blk_h + 0.35), u_viau, u_sher, uz, blk_len + 0.6, 28.6, 0.70, mat_idx=11)
        add_box_local(bm, bc + uz * (blk_h + 0.20), u_viau, u_sher, uz, blk_len - 1.5, 25.5, 0.35, mat_idx=12)
        _add_rooftop_hvac_and_skylights(bm, bc, u_viau, u_sher, blk_h + 0.35, blk_len * 0.85, 24.0)
        n_fl_v = int(blk_h // 3.35)
        for fl_v in range(n_fl_v):
            zv = 2.2 + fl_v * 3.35
            for s_side in (-1.0, 1.0):
                add_box_local(
                    bm,
                    bc + u_sher * (s_side * 14.12) + uz * zv,
                    u_viau,
                    u_sher,
                    uz,
                    blk_len - 2.4,
                    0.22,
                    1.65,
                    mat_idx=2,
                )
                add_box_local(
                    bm,
                    bc + u_sher * (s_side * 14.22) + uz * (zv - 0.95),
                    u_viau,
                    u_sher,
                    uz,
                    blk_len - 1.8,
                    0.35,
                    0.25,
                    mat_idx=11,
                )
                add_box_local(
                    bm,
                    bc + u_viau * (s_side * (blk_len * 0.5 + 0.12)) + uz * zv,
                    u_sher,
                    u_viau,
                    uz,
                    24.5,
                    0.22,
                    1.65,
                    mat_idx=2,
                )

    # =========================================================================
    # 3. STADE SAPUTO (CF MONTRÉAL SOCCER STADIUM, X=225..415, Y=6442..6620)
    #    Exposed Galvanized Steel Space-Frame Canopy Trusses, Tiered Bowl & Gates
    # =========================================================================
    saputo_c = Vector((306.5, 6506.0, 0.0))
    u_pitch = Vector((-0.212, 0.977, 0.0)).normalized()
    r_pitch = Vector((u_pitch.y, -u_pitch.x, 0.0)).normalized()

    # Lush Green Natural Grass Soccer Pitch (112m x 74m at Z=0.08m)
    add_box_local(bm, saputo_c + uz * 0.07, r_pitch, u_pitch, uz, 76.0, 116.0, 0.12, mat_idx=7)
    pitch_w, pitch_l = 68.0, 105.0
    for sx_p in (-pitch_w * 0.5, pitch_w * 0.5):
        add_box_local(bm, saputo_c + r_pitch * sx_p + uz * 0.145, r_pitch, u_pitch, uz, 0.35, pitch_l, 0.03, mat_idx=4)
    for sy_p in (-pitch_l * 0.5, 0.0, pitch_l * 0.5):
        add_box_local(bm, saputo_c + u_pitch * sy_p + uz * 0.145, r_pitch, u_pitch, uz, pitch_w, 0.35, 0.03, mat_idx=4)
    for end_s in (-1.0, 1.0):
        pen_y = end_s * (pitch_l * 0.5 - 8.25)
        add_box_local(bm, saputo_c + u_pitch * (end_s * (pitch_l * 0.5 - 16.5)) + uz * 0.145, r_pitch, u_pitch, uz, 40.3, 0.32, 0.03, mat_idx=4)
        for px_side in (-20.15, 20.15):
            add_box_local(bm, saputo_c + r_pitch * px_side + u_pitch * pen_y + uz * 0.145, r_pitch, u_pitch, uz, 0.32, 16.5, 0.03, mat_idx=4)
    for seg_i in range(24):
        a0 = (seg_i / 24.0) * math.tau
        a1 = ((seg_i + 1) / 24.0) * math.tau
        p_c0 = saputo_c + r_pitch * (math.cos(a0) * 9.15) + u_pitch * (math.sin(a0) * 9.15) + uz * 0.145
        p_c1 = saputo_c + r_pitch * (math.cos(a1) * 9.15) + u_pitch * (math.sin(a1) * 9.15) + uz * 0.145
        dv_c = p_c1 - p_c0
        add_box_local(bm, p_c0.lerp(p_c1, 0.5), dv_c.normalized(), uz.cross(dv_c.normalized()), uz, dv_c.length, 0.30, 0.03, mat_idx=4)

    # Tiered Blue Grandstands with Concrete Vomitory Portals & Aisle Steps
    # West Grandstand (-r_pitch)
    for tier_i in range(7):
        r_off = -41.0 - tier_i * 2.8
        z_t = 1.2 + tier_i * 1.65
        add_box_local(bm, saputo_c + r_pitch * r_off + uz * (z_t * 0.5), r_pitch, u_pitch, uz, 2.9, 108.0, z_t, mat_idx=3 if tier_i % 3 != 2 else 1)
    add_box_local(bm, saputo_c - r_pitch * 49.5 + uz * 14.8, r_pitch, u_pitch, uz, 23.0, 110.0, 0.85, mat_idx=4)
    # Exposed Steel Roof Truss Ribs across West Canopy Roof
    for wk_i in range(-5, 6):
        w_rib = saputo_c - r_pitch * 49.5 + u_pitch * (wk_i * 9.8)
        add_box_local(bm, w_rib + uz * 15.55, r_pitch, u_pitch, uz, 22.8, 0.48, 0.65, mat_idx=10)
        add_cylinder_along(bm, w_rib - r_pitch * 10.5 + uz * 18.2, w_rib + r_pitch * 9.5 + uz * 15.3, 0.16, 0.16, segs=6, mat_idx=10)

    # East Grandstand (+r_pitch)
    for tier_i in range(8):
        r_off = 41.0 + tier_i * 2.9
        z_t = 1.2 + tier_i * 1.75
        add_box_local(bm, saputo_c + r_pitch * r_off + uz * (z_t * 0.5), r_pitch, u_pitch, uz, 3.0, 118.0, z_t, mat_idx=3 if tier_i % 3 != 2 else 1)
    add_box_local(bm, saputo_c + r_pitch * 51.0 + uz * 16.2, r_pitch, u_pitch, uz, 25.0, 122.0, 0.95, mat_idx=4)

    # North Grandstand (+u_pitch) + NE Beveled Corner Roof
    for tier_i in range(8):
        u_off = 60.0 + tier_i * 2.8
        z_t = 1.2 + tier_i * 1.75
        add_box_local(bm, saputo_c + u_pitch * u_off + uz * (z_t * 0.5), r_pitch, u_pitch, uz, 82.0 + tier_i * 2.2, 2.9, z_t, mat_idx=3 if tier_i % 3 != 2 else 1)
    add_box_local(bm, saputo_c + u_pitch * 69.5 + uz * 16.2, r_pitch, u_pitch, uz, 92.0, 24.0, 0.95, mat_idx=4)
    u_ne_diag = (r_pitch + u_pitch).normalized()
    r_ne_diag = Vector((-u_ne_diag.y, u_ne_diag.x, 0.0))
    add_box_local(bm, saputo_c + r_pitch * 41.0 + u_pitch * 58.0 + uz * 16.3, u_ne_diag, r_ne_diag, uz, 24.0, 34.0, 0.95, mat_idx=4)
    add_box_local(bm, saputo_c + r_pitch * 42.0 + u_pitch * 59.0 + uz * 7.5, u_ne_diag, r_ne_diag, uz, 22.0, 32.0, 15.0, mat_idx=1)

    # Exposed Steel Roof Support Ribs, Cantilevered Tension Struts & Rear Space-Frame Trusses
    for rib_k in range(-5, 6):
        p_rib_n = saputo_c + r_pitch * (rib_k * 8.6) + u_pitch * 79.5
        add_box_local(bm, p_rib_n + uz * 9.8, r_pitch, u_pitch, uz, 0.65, 1.8, 19.6, mat_idx=10)
        add_box_local(bm, p_rib_n - u_pitch * 9.5 + uz * 17.0, r_pitch, u_pitch, uz, 0.52, 23.5, 0.80, mat_idx=10)
        add_cylinder_along(bm, p_rib_n + uz * 19.5, p_rib_n - u_pitch * 19.5 + uz * 16.7, 0.16, 0.16, segs=6, mat_idx=10)

        p_rib_e = saputo_c + r_pitch * 61.5 + u_pitch * (rib_k * 10.5)
        add_box_local(bm, p_rib_e + uz * 9.8, r_pitch, u_pitch, uz, 1.8, 0.65, 19.6, mat_idx=10)
        add_box_local(bm, p_rib_e - r_pitch * 9.5 + uz * 17.0, r_pitch, u_pitch, uz, 23.5, 0.52, 0.80, mat_idx=10)
        add_cylinder_along(bm, p_rib_e + uz * 19.5, p_rib_e - r_pitch * 19.5 + uz * 16.7, 0.16, 0.16, segs=6, mat_idx=10)

    # 4 Tall Stadium Floodlight Towers (Z = 35m)
    for fl_x, fl_y in ((-54.0, 68.0), (56.0, 68.0), (-54.0, -56.0), (56.0, -56.0)):
        m_pt = saputo_c + r_pitch * fl_x + u_pitch * fl_y
        add_cylinder_along(bm, m_pt, m_pt + uz * 34.0, 0.55, 0.32, segs=10, mat_idx=10)
        add_box_local(bm, m_pt + uz * 34.8, r_pitch, u_pitch, uz, 5.2, 1.2, 2.8, mat_idx=10)
        add_box_local(bm, m_pt - r_pitch * (0.2 if fl_x > 0 else -0.2) + uz * 34.8, r_pitch, u_pitch, uz, 4.8, 1.4, 2.4, mat_idx=4)

    # Stadium Entry Ticket Pavilions & Blue/White Kiosks near Rue Sherbrooke Est ([414, 6608], Cam 3 V2..V3)
    kiosk_c = Vector((414.0, 6608.0, 0.0))
    add_box_local(bm, kiosk_c + uz * 1.8, u_sher, u_viau, uz, 5.5, 4.2, 3.6, mat_idx=4)
    add_box_local(bm, kiosk_c + uz * 3.8, u_sher, u_viau, uz, 6.4, 5.0, 0.45, mat_idx=3)
    add_box_local(bm, kiosk_c + u_sher * 9.5 + uz * 1.6, u_sher, u_viau, uz, 4.2, 3.6, 3.2, mat_idx=4)
    add_box_local(bm, kiosk_c + u_sher * 16.5 + uz * 2.2, u_sher, u_viau, uz, 1.4, 1.4, 4.4, mat_idx=3)

    # =========================================================================
    # 4. EASTERN INSTITUTIONAL & COMMERCIAL WAREHOUSE COMPLEXES (X=370..534, Y=6590..6978)
    #    Weathered Gravel/Bitumen Roofs, Parapet Copings, Rooftop HVAC & Skylights (`RSI-011`)
    # =========================================================================
    # L-Shaped Industrial/Commercial Building (X=374..486, Y=6780..6895, H2..H4, V7..V8)
    ind_c = Vector((432.0, 6832.0, 0.0))
    ind_h = 10.8
    add_box_local(bm, ind_c + uz * (ind_h * 0.5), u_viau, u_sher, uz, 74.0, 96.0, ind_h, mat_idx=0)
    add_box_local(bm, ind_c + uz * (ind_h + 0.40), u_viau, u_sher, uz, 74.8, 96.8, 0.80, mat_idx=1)
    add_box_local(bm, ind_c + uz * (ind_h + 0.22), u_viau, u_sher, uz, 72.2, 94.2, 0.40, mat_idx=13)
    _add_rooftop_hvac_and_skylights(bm, ind_c, u_viau, u_sher, ind_h + 0.40, 68.0, 88.0)

    # SE projecting wing of the L-shaped building
    ind_se = ind_c - u_viau * 28.0 + u_sher * 26.0
    add_box_local(bm, ind_se + uz * (ind_h * 0.5), u_viau, u_sher, uz, 44.0, 44.0, ind_h, mat_idx=0)
    add_box_local(bm, ind_se + uz * (ind_h + 0.40), u_viau, u_sher, uz, 44.8, 44.8, 0.80, mat_idx=1)
    add_box_local(bm, ind_se + uz * (ind_h + 0.22), u_viau, u_sher, uz, 42.2, 42.2, 0.40, mat_idx=12)
    _add_rooftop_hvac_and_skylights(bm, ind_se, u_viau, u_sher, ind_h + 0.40, 38.0, 38.0)

    for fl_i in range(3):
        zi = 2.2 + fl_i * 3.1
        for b_i in range(-7, 8):
            for s_side in (-1.0, 1.0):
                add_box_local(bm, ind_c + u_sher * (b_i * 5.8) + u_viau * (s_side * 37.15) + uz * zi, u_sher, u_viau, uz, 3.2, 0.22, 1.5, mat_idx=2)
                add_box_local(bm, ind_c + u_viau * (b_i * 4.4) + u_sher * (s_side * 48.15) + uz * zi, u_viau, u_sher, uz, 2.8, 0.22, 1.5, mat_idx=2)

    # Arrayed White Semi-Trailers in Northern Truck Yard (X=395..515, Y=6890..6972, H1..H2, V7..V8)
    yard_c = ind_c + u_viau * 66.0 + u_sher * 8.0
    for tr_i in range(-5, 6):
        tr_p = yard_c - u_viau * 14.0 + u_sher * (tr_i * 4.2 - 12.0)
        add_box_local(bm, tr_p + uz * 1.9, u_viau, u_sher, uz, 13.5, 2.5, 3.2, mat_idx=4)
        add_box_local(bm, tr_p + uz * 0.45, u_viau, u_sher, uz, 12.0, 2.2, 0.7, mat_idx=10)

    # East Sherbrooke Institutional Complex (X=468..533, Y=6615..6845, H3..H6, V8 in satellite)
    # Replaced flat white roofs with weathered gravel/bitumen + parapet copings + HVAC & skylights!
    e_inst_n = Vector((512.0, 6785.0, 0.0))
    add_box_local(bm, e_inst_n + uz * 6.5, u_viau, u_sher, uz, 108.0, 52.0, 13.0, mat_idx=15)
    add_box_local(bm, e_inst_n + uz * 13.35, u_viau, u_sher, uz, 108.8, 52.8, 0.75, mat_idx=1)
    add_box_local(bm, e_inst_n + uz * 13.20, u_viau, u_sher, uz, 106.0, 50.0, 0.35, mat_idx=14)
    _add_rooftop_hvac_and_skylights(bm, e_inst_n, u_viau, u_sher, 13.35, 96.0, 44.0)

    e_inst_s = Vector((504.0, 6678.0, 0.0))
    add_box_local(bm, e_inst_s + uz * 7.2, u_viau, u_sher, uz, 96.0, 56.0, 14.4, mat_idx=11)
    add_box_local(bm, e_inst_s + uz * 14.75, u_viau, u_sher, uz, 96.8, 56.8, 0.75, mat_idx=1)
    add_box_local(bm, e_inst_s + uz * 14.60, u_viau, u_sher, uz, 94.0, 54.0, 0.35, mat_idx=12)
    _add_rooftop_hvac_and_skylights(bm, e_inst_s, u_viau, u_sher, 14.75, 86.0, 48.0)

    for fl_ei in range(4):
        zei = 2.2 + fl_ei * 3.2
        for b_ei in range(-7, 8):
            add_box_local(bm, e_inst_s + u_viau * (b_ei * 5.8) - u_sher * 28.15 + uz * zei, u_viau, u_sher, uz, 3.4, 0.24, 1.65, mat_idx=2)
            add_box_local(bm, e_inst_n + u_viau * (b_ei * 6.2) - u_sher * 26.15 + uz * zei, u_viau, u_sher, uz, 3.4, 0.24, 1.65, mat_idx=2)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.22)
    print(f"[{BLOCK_ID}] Built Iteration 2 hero Olympic Village & Stade Saputo assembly ({len(mesh.polygons):,} faces).")
    return obj


def refine_superblock():
    print(f"\n=== Refining & Building {BLOCK_ID} — Iteration 2 (Le Village olympique, Stade Saputo & Rue Sherbrooke Est) ===")
    blend_path = REPO_ROOT / "output" / "blocks" / f"{BLOCK_ID}.blend"
    dossier = load_dossier(BLOCK_ID)

    if blend_path.exists():
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))
        for obj in list(bpy.data.objects):
            nl = obj.name.lower()
            if any(k in nl for k in ("streets_sidewalks_and_parks", "street_trees_3d", "cam_", "sun", "light", "hero", "mtl_")):
                bpy.data.objects.remove(obj, do_unlink=True)
            elif "ground_and_river" in nl and obj.type == "MESH":
                for v in obj.data.vertices:
                    if v.co.z > -0.10:
                        v.co.z = -0.030
                obj.data.update()
            elif "buildings_fabric" in nl and obj.type == "MESH":
                bm_f = bmesh.new()
                bm_f.from_mesh(obj.data)
                to_del = []
                for f in bm_f.faces:
                    fc = f.calc_center_median()
                    if (-25.0 <= fc.x <= 550.0 and 6435.0 <= fc.y <= 6985.0) or (120.0 <= fc.x <= 395.0 and 6250.0 <= fc.y <= 6435.0):
                        to_del.append(f)
                if to_del:
                    bmesh.ops.delete(bm_f, geom=to_del, context="FACES")
                    bm_f.to_mesh(obj.data)
                    obj.data.update()
                bm_f.free()
    else:
        clean_scene()

    setup_render_engine()
    setup_world_lighting(dossier)

    owned_col = bpy.data.collections.get(f"Block_{BLOCK_ID}_Owned")
    if not owned_col:
        owned_col, _ = setup_collection_hierarchy(BLOCK_ID)

    # 1. Build raised 3D sidewalks, granite curbs, road markings, zebra crosswalks & Poly Haven streetlamps
    build_ground_and_streets(owned_col, dossier)
    mats = build_corridor_material_palette()

    # 2. Build partitioned parkland lawns, walkways & dark asphalt parking courts (`MTL_Park_Paths_Lawns_And_Courts`)
    build_parkland_lawns_paths_and_parking(owned_col, dossier, mats)

    # 3. Build bespoke 3D Hero Landmarks (Warm Buff Twin Pyramids, Hôtel Universel, Viau Office Complex, Stade Saputo)
    build_olympic_village_and_campus_landmarks(owned_col, mats)

    # 4. Build remaining OSM context buildings with floor-by-floor 3D fenestration
    skip_boxes = [
        (-20.0, 545.0, 6435.0, 6985.0),
        (120.0, 395.0, 6250.0, 6435.0),
    ]
    build_corridor_context_buildings(owned_col, dossier, mats, skip_boxes=skip_boxes, max_buildings=120)

    # 5. Place lush, full-volume 9-lobe 3D Poly Haven trees (`1.55x..2.10x` scale) matching H3..H6 across all 4 Street Views!
    extra_trees = []
    # (a) Dense Mature Park Forest along Boulevard Viau / de l'Assomption (`Olympic_Village_West_Pyramid_Assomption` H3..H6, V1..V8)
    for i_t in range(22):
        ty = 6450.0 + i_t * 13.0
        extra_trees.append((134.0 - (i_t % 2) * 7.0, ty, 1.65 + (i_t % 3) * 0.18))
        extra_trees.append((102.0 + (i_t % 3) * 8.0, ty + 5.0, 1.55 + (i_t % 4) * 0.15))
        extra_trees.append((32.0 + (i_t % 2) * 16.0, ty, 1.60))

    # (b) Wooded Park Triangle East of Boulevard Viau & South of Rue Sherbrooke Est (directly visible in Cam 2 H3..H6, V1..V8)
    for gx, gy, sc in [
        (170.0, 6628.0, 1.85), (176.0, 6638.0, 1.95), (184.0, 6648.0, 1.90),
        (192.0, 6658.0, 1.85), (202.0, 6668.0, 1.80), (212.0, 6678.0, 1.85),
        (224.0, 6688.0, 1.75), (186.0, 6624.0, 1.85), (200.0, 6636.0, 1.90),
        (216.0, 6648.0, 1.85), (232.0, 6660.0, 1.80), (248.0, 6672.0, 1.75),
        (268.0, 6662.0, 1.70), (288.0, 6654.0, 1.75), (312.0, 6652.0, 1.70),
        (338.0, 6646.0, 1.75), (362.0, 6638.0, 1.80), (386.0, 6628.0, 1.75),
    ]:
        extra_trees.append((gx, gy, sc))

    # (c) Framing Cam 1 (`Olympic_Village_Pyramids_Sherbrooke_South`), Cam 3 (`Olympic_Village_East_Pyramid_Viau`),
    #     and Cam 4 (`Rue_Sherbrooke_Est_Olympic_Village_Front`)
    for tx, ty, sc in [
        # Cam 1 foreground left & center-right trees (H3..H6)
        (229.0, 6750.0, 1.82), (222.0, 6762.0, 1.75), (264.0, 6754.0, 1.45), (306.0, 6752.0, 1.65),
        # Cam 4 left foreground canopy & center-right intersection trees (keeping V2..V3 West Pyramid clear!)
        (134.0, 6768.0, 1.88), (124.0, 6785.0, 1.65), (154.0, 6786.0, 1.48),
        (188.0, 6766.0, 1.60), (204.0, 6758.0, 1.55), (235.0, 6835.0, 1.65),
        # Cam 3 left & right bordering trees along Rue Sherbrooke Est (`Olympic_Village_East_Pyramid_Viau` V1..V2 & V6..V8)
        (442.0, 6604.0, 1.85), (426.0, 6610.0, 1.80), (402.0, 6618.0, 1.75),
        (442.0, 6630.0, 1.95), (420.0, 6640.0, 1.88), (396.0, 6652.0, 1.82),
        (370.0, 6664.0, 1.78), (344.0, 6676.0, 1.72),
        # Olympic Village Forecourt & Stade Saputo East Parking Lot trees
        (55.0, 6835.0, 1.65), (35.0, 6855.0, 1.60), (185.0, 6885.0, 1.55),
        (455.0, 6485.0, 1.45), (455.0, 6525.0, 1.45), (485.0, 6485.0, 1.45), (485.0, 6525.0, 1.45),
    ]:
        extra_trees.append((tx, ty, sc))

    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=80)

    # 6. Export packed .blend and .usdc
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== {BLOCK_ID} Iteration 2 Refinement Complete ===")


if __name__ == "__main__":
    refine_superblock()
