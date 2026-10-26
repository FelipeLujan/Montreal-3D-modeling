#!/usr/bin/env python3
"""
High-Poly 3D Architecture, Grain Elevator Waterfront & Bridge Approach Modeler — Block `MTL-VM-0037`
(`Pont Victoria Approach, Windmill Point / Pointe-du-Moulin South & Silo No. 4 Waterfront`)
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

BLOCK_ID = "MTL-VM-0037"


def add_slab_z(bm, cx: float, cy: float, ux: Vector, uy: Vector, uz: Vector, sx: float, sy: float, z_bot: float, z_top: float, mat_idx: int):
    """Helper that places a 3D slab with explicit bottom and top Z so faces are never coplanar with Z=0.0m."""
    cz = 0.5 * (z_bot + z_top)
    sz = z_top - z_bot
    add_box_local(bm, Vector((cx, cy, cz)), ux, uy, uz, sx, sy, sz, mat_idx=mat_idx)


def build_windmill_point_silos_and_victoria_approach(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Models:
    1. Strictly non-overlapping West Ground Stratum (`X = 345..458.0, top_z = -0.015m`) and West Embankment Yard (`X = 458.5..495.0, top_z = 0.085m`)
       so zero faces are ever coplanar with `MTL_Ground_Base` (`Z = 0.000m`).
    2. Bassin Windmill Point (Pointe-du-Moulin South) Harbor Basin (`X = 531..613, top_z = 0.08m`), concrete quay walls (`top_z = 0.38m`),
       Pointe-du-Moulin West multi-track rail yard (`top_z = 0.14m`) with white hopper railcars (`X = 496..507`), concrete wharf apron (`top_z = 0.19m`),
       elevated grain conveyor gallery with 7 projecting white ship-loader spouts (`X = 519.5..530.5`), and the moored Ocean Container Cargo Ship (`X = 582..612`)
       matching `satellite_topdown.png` 1:1.
    3. Historic Steel Through-Truss Pont Victoria Approach Viaduct & Stepped Stone Piers (`bridge_green_steel` / `tan_limestone`).
    4. Camera 1 (`Pont_Victoria_North_Approach`): ADM concrete industrial warehouse wall (`height = 4.6m`, matching `H3..H5` roofline),
       corrugated guard shed, arched tarp shelter, overhead grain conveyor trestle bridge, foreground dark blue sedan car,
       and the iconic ADM / Farine Five Roses red-brick mill tower & concrete silos rising into `H2..H3`.
    5. Camera 2 (`Rue_Mill_Windmill_Point_East`) & Camera 4 (`Bassin_Windmill_South_Quay`): 1-story CMU industrial garage with
       terracotta roll-up door, Silo No. 4 cylindrical concrete grain silos, weathered rusty-brown marine leg tower, and elevated
       corrugated steel conveyor gallery bridges.
    6. Camera 3 (`Riverside_Harbor_Industrial_View`): Foreground sidewalk, chain-link fence gate & mesh grid, gravel/grass lot,
       and elevated wharf conveyor trestle bents.
    """
    mesh = bpy.data.meshes.new("MTL_VM_0037_WindmillPoint_Silos_and_Bridge")
    obj = bpy.data.objects.new("MTL_VM_0037_WindmillPoint_Silos_and_Bridge", mesh)
    col.objects.link(obj)
    for k in (
        "concrete_podium",      # 0: Silo No. 4 Cylindrical Concrete Silos, Quay Walls & Conveyor Galleries
        "concrete_brick_wall",  # 1: CMU Industrial Garage & ADM Warehouse Wall (`concrete_brick_wall_001`)
        "red_brick",            # 2: ADM / Five Roses Tall Red-Brick Elevator Tower (`red_bricks_04`)
        "sandstone_brick",      # 3: Weathered Rusty-Brown Marine Leg Tower & Orange Containers
        "factory_corrugated",   # 4: Green Industrial Sheds & Corrugated Cladding (`factory_wall`)
        "bridge_green_steel",   # 5: Pont Victoria Steel Through-Truss Viaduct (`Mat_MTL_JacquesCartier_Green_Steel`)
        "water_river",          # 6: Bassin Windmill Point Harbor Water (`Mat_PH_StLawrence_River_Water`)
        "roof_bitumen",         # 7: Dark Asphalt Roadways & Bitumen Industrial Roofs
        "roof_light_gravel",    # 8: Light Gravel Industrial Roofs, Rail Ballast & Yard Apron
        "white_trim",           # 9: White Hopper Railcars, Ship Bow/Bridge, Ship-Loader Spouts & Window Frames
        "dark_glass",           # 10: Recessed Multi-Pane Industrial Windows (`Mat_MTL_CurtainWall_Glass`)
        "dark_metal",           # 11: Steel Rail Tracks, Trestle Bents, Fence Posts & Mullions
        "terracotta_vivid",     # 12: Cargo Ship Red Deck, Red Containers & Garage Roll-Up Doors
        "blue_curtain_glass",   # 13: Blue Shipping Containers, Harbor Crane & Foreground Sedan
        "park_grass",           # 14: Grass Verges & Industrial Lot Vegetation
        "tan_limestone",        # 15: Concrete Sidewalks, Granite Curbs & Stepped Stone Bridge Piers
    ):
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    uz = Vector((0.0, 0.0, 1.0))
    ux = Vector((1.0, 0.0, 0.0))
    uy = Vector((0.0, 1.0, 0.0))

    # Corridor axis along Windmill Point Quay & Rail Yard (~4° East of North in satellite_topdown.png)
    f_quay = Vector((math.sin(math.radians(4.0)), math.cos(math.radians(4.0)), 0.0)).normalized()
    r_quay = Vector((f_quay.y, -f_quay.x, 0.0)).normalized()

    # -------------------------------------------------------------------------
    # 1. Non-Coplanar Ground Stratum (`z_bot = -0.45m` everywhere to prevent Z=0.0m coplanarity!)
    # -------------------------------------------------------------------------
    # 1a. West Street View Corridor Ground (`X = 345..457.8, Y = -1390..-1025, top_z = -0.015m`, strictly West of `MTL_Ground_Base`)
    add_slab_z(bm, 401.4, -1207.5, ux, uy, uz, 112.8, 365.0, -0.45, -0.015, mat_idx=8)
    # 1b. North-Central Ground Extension (`X = 458.0..535.0, Y = -1118.8..-1025.0, top_z = -0.015m`, strictly North of `MTL_Ground_Base`)
    add_slab_z(bm, 496.5, -1071.9, ux, uy, uz, 77.0, 93.8, -0.45, -0.015, mat_idx=8)
    # 1c. West Industrial Gravel & Grass Embankment (`X = 458.5..494.5, Y = -1305..-1135, top_z = 0.085m`, +8.5cm above `MTL_Ground_Base`)
    add_slab_z(bm, 476.5, -1215.6, r_quay, f_quay, uz, 34.5, 168.0, -0.35, 0.085, mat_idx=8)
    # Green grass embankment verges along the West rail edge (`top_z = 0.115m`)
    add_slab_z(bm, 489.5, -1195.0, r_quay, f_quay, uz, 8.5, 92.0, -0.30, 0.115, mat_idx=14)

    # -------------------------------------------------------------------------
    # 2. Satellite Top-Down 1:1 Reconstruction (`X = 488..622, Y = -1148..-1283`)
    #    Every zone is strictly disjoint in X AND has a unique `top_z` >= 0.08m!
    # -------------------------------------------------------------------------
    # 2a. Bassin Windmill Point Deep Harbor Water (`X = 531.2..612.8, Y = -1135..-1295, top_z = 0.08m`)
    add_slab_z(bm, 572.0, -1215.6, f_quay, r_quay, uz, 165.0, 81.2, -0.40, 0.08, mat_idx=6)

    # Western & Eastern Concrete Quay Walls (`top_z = 0.38m`, strictly disjoint from water and apron)
    add_slab_z(bm, 525.2, -1215.6, r_quay, f_quay, uz, 11.2, 162.0, -0.35, 0.38, mat_idx=0)
    add_slab_z(bm, 618.2, -1215.6, r_quay, f_quay, uz, 10.2, 162.0, -0.35, 0.38, mat_idx=0)
    # Yellow crane rail / safety markings along Eastern Quay (`top_z = 0.41m`)
    add_slab_z(bm, 614.2, -1215.6, r_quay, f_quay, uz, 0.35, 155.0, 0.38, 0.41, mat_idx=15)

    # 2b. Pointe-du-Moulin West Multi-Track Rail Yard & White Hopper Railcars (`X = 495.2..507.5, top_z = 0.14m`)
    rail_c = Vector((501.4, -1215.6, 0.0))
    add_slab_z(bm, 501.4, -1215.6, r_quay, f_quay, uz, 12.2, 162.0, -0.35, 0.14, mat_idx=8)
    for tr_off in (-3.2, 0.0, 3.2):
        for rail_s in (-0.72, 0.72):
            add_box_local(
                bm,
                rail_c + r_quay * (tr_off + rail_s) + uz * 0.20,
                r_quay,
                f_quay,
                uz,
                0.14,
                158.0,
                0.10,
                mat_idx=11,
            )
    # Continuous string of 7 White Covered Hopper Railcars along main track (`V1..V2, H1..H8` in satellite_topdown.png)
    for car_i in range(-3, 4):
        car_p = rail_c + f_quay * (car_i * 19.2)
        add_box_local(bm, car_p + uz * 2.20, r_quay, f_quay, uz, 3.05, 16.8, 3.45, mat_idx=9)
        add_box_local(bm, car_p + uz * 3.98, r_quay, f_quay, uz, 1.25, 16.2, 0.14, mat_idx=0)
        add_box_local(bm, car_p + uz * 0.60, r_quay, f_quay, uz, 2.65, 15.8, 0.45, mat_idx=11)

    # Concrete Wharf Roadway Apron between Rail Tracks and Grain Conveyor Gallery (`X = 507.8..519.4, top_z = 0.19m`)
    add_slab_z(bm, 513.6, -1215.6, r_quay, f_quay, uz, 11.4, 162.0, -0.35, 0.19, mat_idx=0)

    # 2c. Long Elevated Grain Conveyor Gallery & Quay Shed (`X = 520..529, Y = -1145..-1285`)
    gal_c = Vector((524.2, -1215.6, 0.0))
    # Lower structural steel trestle bents (`Z = 0.38..8.2m`) every 9.0m
    for bent_i in range(-8, 9):
        bp = gal_c + f_quay * (bent_i * 9.0)
        for col_s in (-3.2, 3.2):
            add_box_local(bm, bp + r_quay * col_s + uz * 4.25, r_quay, f_quay, uz, 0.55, 0.55, 7.8, mat_idx=11)
        add_box_local(bm, bp + uz * 8.0, r_quay, f_quay, uz, 7.2, 0.65, 0.65, mat_idx=11)
    # Upper enclosed conveyor gallery body (`Z = 8.2..14.4m`) with segmented bitumen/gravel roofs matching satellite
    for seg_i in range(-3, 4):
        sp = gal_c + f_quay * (seg_i * 21.5)
        add_box_local(bm, sp + uz * 11.3, r_quay, f_quay, uz, 7.8, 21.2, 6.2, mat_idx=0)
        roof_m = 7 if (seg_i % 2 == 0) else 8
        add_box_local(bm, sp + uz * 14.5, r_quay, f_quay, uz, 7.4, 20.8, 0.24, mat_idx=roof_m)
        # Projecting white square ship-loader spout houses along East water edge (`V3` in satellite_topdown.png)
        add_box_local(bm, sp + r_quay * 5.2 + uz * 11.0, r_quay, f_quay, uz, 2.8, 3.2, 4.8, mat_idx=9)

    # 2d. Moored Ocean Container Cargo Ship on Right Side of Satellite Top-Down (`X = 582..612, Y = -1165..-1285`)
    ship_c = Vector((597.0, -1228.0, 0.0))
    # Ship dark steel hull (`Z = 0.12..5.2m`, above water_c at `0.08m`)
    add_box_local(bm, ship_c + uz * 2.66, r_quay, f_quay, uz, 27.5, 98.0, 5.08, mat_idx=11)
    # Red main weather deck (`Z = 5.2..5.65m`, `terracotta_vivid`)
    add_box_local(bm, ship_c + uz * 5.42, r_quay, f_quay, uz, 27.2, 97.5, 0.45, mat_idx=12)
    # White curved/tapered Bow pointing North (`Y = -1164..-1182`, `V6..V7, H2..H3` in satellite_topdown.png)
    bow_base = ship_c + f_quay * 49.0
    for b_step in range(8):
        t0 = b_step / 8.0
        w_bow = 27.2 * (1.0 - 0.72 * (t0 ** 1.35))
        p_b = bow_base + f_quay * (b_step * 2.1 + 1.05)
        add_box_local(bm, p_b + uz * 3.45, r_quay, f_quay, uz, w_bow, 2.25, 5.1, mat_idx=9)
        add_box_local(bm, p_b + uz * 6.15 + uz * (b_step * 0.01), r_quay, f_quay, uz, w_bow * 0.92, 2.15, 0.32, mat_idx=9)
    # Wide Forward Navigation Bridge & Red Foredeck Superstructure (`Y = -1182..-1196`, `V6..V8, H3..H4`)
    br_p = ship_c + f_quay * 40.5
    add_box_local(bm, br_p + uz * 8.0, r_quay, f_quay, uz, 33.5, 6.8, 4.7, mat_idx=9)
    add_box_local(bm, br_p + uz * 10.55, r_quay, f_quay, uz, 32.8, 6.2, 0.30, mat_idx=12)
    add_box_local(bm, br_p - f_quay * 6.8 + uz * 7.0, r_quay, f_quay, uz, 26.8, 8.2, 2.6, mat_idx=9)
    add_box_local(bm, br_p - f_quay * 6.8 + uz * 8.45, r_quay, f_quay, uz, 26.2, 7.8, 0.28, mat_idx=12)
    # Stacked Intermodal Shipping Containers on Cargo Deck (Blue, Red/Orange, and White rows matching satellite_topdown.png!)
    bay_y_offsets = [24.0, 12.5, -1.5, -15.5, -29.5, -43.0]
    for b_idx, by_off in enumerate(bay_y_offsets):
        bay_p = ship_c + f_quay * by_off
        for slot_i in range(-3, 4):
            sx_off = slot_i * 3.45
            if (slot_i + b_idx) % 4 == 0:
                c_mat = 12  # Red/Orange container
            elif (slot_i * b_idx) % 3 == 1:
                c_mat = 9   # White container
            else:
                c_mat = 13  # Blue container
            add_box_local(
                bm,
                bay_p + r_quay * sx_off + uz * 8.1,
                r_quay,
                f_quay,
                uz,
                3.15,
                12.2,
                4.8,
                mat_idx=c_mat,
            )

    # -------------------------------------------------------------------------
    # 3. Pont Victoria Historic Steel Through-Truss Approach Viaduct & Stepped Stone Piers
    # -------------------------------------------------------------------------
    v_start = Vector((430.0, -1335.0, 16.5))
    v_end = Vector((625.0, -1292.0, 22.5))
    v_vec = v_end - v_start
    v_len = v_vec.length
    v_dir = v_vec / v_len
    v_right = Vector((v_dir.y, -v_dir.x, 0.0)).normalized()
    n_v_segs = 14
    for s_i in range(n_v_segs):
        t0 = s_i / n_v_segs
        t1 = (s_i + 1) / n_v_segs
        p0 = v_start.lerp(v_end, t0)
        p1 = v_start.lerp(v_end, t1)
        pm = p0.lerp(p1, 0.5)
        seg_l = (p1 - p0).length
        # Bridge deck (rail + roadway lanes)
        add_box_local(bm, pm, v_right, v_dir, uz, 16.5, seg_l + 0.04, 1.2, mat_idx=7)
        add_box_local(bm, pm - uz * 1.35, v_right, v_dir, uz, 17.2, seg_l + 0.04, 1.4, mat_idx=5)
        truss_h = 11.5
        for side_t in (-7.8, 7.8):
            off_r = v_right * side_t
            add_cylinder_along(bm, p0 + off_r, p0 + off_r + uz * truss_h, 0.42, 0.40, segs=8, mat_idx=5)
            add_cylinder_along(bm, p0 + off_r + uz * truss_h, p1 + off_r + uz * truss_h, 0.45, 0.45, segs=8, mat_idx=5)
            add_cylinder_along(bm, p0 + off_r, p1 + off_r + uz * truss_h, 0.30, 0.30, segs=8, mat_idx=5)
            add_cylinder_along(bm, p0 + off_r + uz * truss_h, p1 + off_r, 0.30, 0.30, segs=8, mat_idx=5)
        if s_i % 2 == 0:
            add_cylinder_along(bm, p0 - v_right * 7.8 + uz * truss_h, p0 + v_right * 7.8 + uz * truss_h, 0.35, 0.35, segs=8, mat_idx=5)
        # Stepped coursed stone bridge piers (each course <= 4.8m tall so fenestration gate treats them as masonry piers)
        if s_i in (2, 6, 10):
            pier_base = Vector((p0.x, p0.y, 0.40))
            n_tiers = 4
            tier_h = (p0.z - 0.40) / n_tiers
            for t_k in range(n_tiers):
                t_scale = 1.0 - t_k * 0.06
                add_box_local(
                    bm,
                    pier_base + uz * ((t_k + 0.5) * tier_h),
                    v_right,
                    v_dir,
                    uz,
                    5.8 * t_scale,
                    18.8 * t_scale,
                    tier_h - 0.12,
                    mat_idx=15,
                )

    # -------------------------------------------------------------------------
    # 4. Camera 1 (`Pont_Victoria_North_Approach`: pos=(416.721, -1274.897), hdg=135°)
    # -------------------------------------------------------------------------
    cam1 = Vector((416.721, -1274.897, 0.0))
    f1 = Vector((math.sin(math.radians(135.0)), math.cos(math.radians(135.0)), 0.0)).normalized()
    r1 = Vector((f1.y, -f1.x, 0.0)).normalized()
    # Rue Mill direction (~7° W of S: heading ~187°)
    f_mill = Vector((-0.122, -0.9925, 0.0)).normalized()
    r_mill = Vector((f_mill.y, -f_mill.x, 0.0)).normalized()  # points West; -r_mill points East

    # Foreground Rue Mill asphalt street & yellow center line (`V4..V8, H6..H8` in Camera 1, `top_z = 0.015m` below OSM road)
    add_box_local(bm, cam1 + r1 * 2.5 + f1 * 12.0 - uz * 0.085, r_mill, f_mill, uz, 12.0, 58.0, 0.20, mat_idx=7)
    add_box_local(bm, cam1 + r1 * 4.5 + f1 * 9.5 + uz * 0.09, r_mill, f_mill, uz, 0.18, 48.0, 0.02, mat_idx=15)
    # Dark blue-black sedan car in bottom foreground (`V3..V6, H6..H8` of Camera 1)
    car1_p = cam1 + f1 * 4.6 + r1 * 0.85
    add_box_local(bm, car1_p + uz * 0.55, r_mill, f_mill, uz, 1.82, 4.35, 0.72, mat_idx=13)
    add_box_local(bm, car1_p - f_mill * 0.25 + uz * 1.12, r_mill, f_mill, uz, 1.55, 2.25, 0.52, mat_idx=10)
    # Chain-link fence posts & rails along left/center foreground (`V1..V5, H5..H6`)
    for fn_i in range(-6, 5):
        fp = cam1 + f1 * 11.2 + r1 * (fn_i * 2.4 - 2.0)
        add_cylinder_along(bm, fp + uz * 0.2, fp + uz * 2.25, 0.04, 0.04, segs=6, mat_idx=11)
        if fn_i < 4:
            fp_next = cam1 + f1 * 11.2 + r1 * ((fn_i + 1) * 2.4 - 2.0)
            add_cylinder_along(bm, fp + uz * 2.20, fp_next + uz * 2.20, 0.03, 0.03, segs=6, mat_idx=11)
            add_cylinder_along(bm, fp + uz * 1.20, fp_next + uz * 1.20, 0.025, 0.025, segs=6, mat_idx=11)

    # Long 1-story Grey-Beige Concrete/CMU ADM Industrial Warehouse (`V3..V8, H3..H5` in Camera 1)
    # Height = 4.6m (< 5.5m so it remains a solid windowless concrete industrial wall matching the photo!)
    adm_wall_c = cam1 + f1 * 27.5 + r1 * 10.5
    add_box_local(bm, adm_wall_c + uz * 2.35, r_mill, f_mill, uz, 18.0, 48.0, 4.5, mat_idx=1)
    add_box_local(bm, adm_wall_c + uz * 4.72, r_mill, f_mill, uz, 18.2, 48.2, 0.18, mat_idx=7)
    # White ADM signboards at the NW corner of the warehouse (`V6..V7, H3..H4`)
    adm_corner = cam1 + f1 * 16.5 + r1 * 4.2
    add_box_local(bm, adm_corner + uz * 3.8, r1, f1, uz, 1.2, 0.25, 1.5, mat_idx=9)
    add_box_local(bm, adm_corner - r1 * 1.8 + uz * 3.5, r1, f1, uz, 1.0, 0.20, 1.0, mat_idx=9)
    # Corrugated metal gable-roofed guard/entry shed (`V4..V5, H4..H5`)
    shed_p = cam1 + f1 * 16.8 - r1 * 0.6
    add_box_local(bm, shed_p + uz * 1.70, r1, f1, uz, 3.8, 3.6, 3.2, mat_idx=8)
    add_box_local(bm, shed_p - f1 * 1.82 + uz * 1.45, r1, f1, uz, 1.8, 0.12, 2.4, mat_idx=3)
    add_box_local(bm, shed_p + uz * 3.60, r1, f1, uz, 4.1, 3.9, 0.55, mat_idx=9)
    # Grey arched/quonset tarp storage shelter to the left (`V2..V4, H4..H5`)
    tarp_p = cam1 + f1 * 21.5 - r1 * 6.5
    add_box_local(bm, tarp_p + uz * 1.95, r1, f1, uz, 7.5, 6.5, 3.7, mat_idx=8)
    add_cylinder_along(bm, tarp_p - r1 * 3.75 + uz * 3.6, tarp_p + r1 * 3.75 + uz * 3.6, 3.1, 3.1, segs=12, mat_idx=9)

    # Elevated Concrete/Steel Grain Conveyor Trestle Bridge on Left of Camera 1 (`V1..V2, H3..H4`)
    conv1_p = cam1 + f1 * 34.0 - r1 * 19.5
    add_box_local(bm, conv1_p + uz * 9.8, r1, f1, uz, 22.0, 3.6, 2.2, mat_idx=0)
    for b_x in (-7.5, -1.5, 4.5):
        add_box_local(bm, conv1_p + r1 * b_x + uz * 4.5, r1, f1, uz, 0.55, 1.8, 8.6, mat_idx=11)
        add_box_local(bm, conv1_p + r1 * b_x - f1 * 1.85 + uz * 9.9, r1, f1, uz, 1.6, 0.12, 0.95, mat_idx=10)
    # White semi-truck ("Sucre Lantic") & blue harbor crane in left yard (`V1..V2, H4..H5`)
    add_box_local(bm, cam1 + f1 * 36.0 - r1 * 21.0 + uz * 2.1, r1, f1, uz, 11.5, 2.6, 3.4, mat_idx=9)
    add_box_local(bm, cam1 + f1 * 44.0 - r1 * 23.0 + uz * 7.6, r1, f1, uz, 5.5, 5.5, 14.8, mat_idx=13)

    # Iconic ADM / Farine Five Roses Tall Red-Brick Elevator & Mill Tower in Upper Right (`V5..V8, H2..H3`)
    mill_c = cam1 + f1 * 42.0 + r1 * 11.5
    add_box_local(bm, mill_c + uz * 16.2, r_mill, f_mill, uz, 15.0, 26.0, 22.8, mat_idx=2)
    add_box_local(bm, mill_c + uz * 27.8, r_mill, f_mill, uz, 14.5, 25.5, 0.35, mat_idx=9)
    # Rooftop structural steel sign truss atop the red-brick mill (`V5..V6, H2`)
    add_box_local(bm, mill_c - f_mill * 5.5 + uz * 30.2, r_mill, f_mill, uz, 2.2, 13.5, 4.8, mat_idx=11)
    add_box_local(bm, mill_c - f_mill * 5.5 + uz * 30.2, r_mill, f_mill, uz, 2.5, 13.0, 1.6, mat_idx=9)
    # Grey concrete elevator tower & cylindrical silos behind/right of the red-brick mill (`V7..V8, H2..H4`)
    add_box_local(bm, mill_c + f_mill * 17.0 + uz * 17.5, r_mill, f_mill, uz, 13.0, 11.0, 25.0, mat_idx=0)
    for s_idx in range(5):
        silo_p = cam1 + f1 * (34.0 + s_idx * 4.2) + r1 * 21.5
        add_cylinder_along(bm, silo_p + uz * 4.8, silo_p + uz * 19.5, 2.1, 2.1, segs=14, mat_idx=0)
    # Green sloped industrial shed roof (`V7..V8, H4`)
    add_box_local(bm, cam1 + f1 * 30.0 + r1 * 17.5 + uz * 7.2, r_mill, f_mill, uz, 11.0, 16.0, 4.8, mat_idx=4)

    # -------------------------------------------------------------------------
    # 5. Camera 2 (`Rue_Mill_Windmill_Point_East`: pos=(436.256, -1097.657), hdg=65°) &
    #    Camera 4 (`Bassin_Windmill_South_Quay`: pos=(438.065, -1078.660), hdg=155°)
    # -------------------------------------------------------------------------
    cam2 = Vector((436.256, -1097.657, 0.0))
    f2 = Vector((math.sin(math.radians(65.0)), math.cos(math.radians(65.0)), 0.0)).normalized()
    r2 = Vector((f2.y, -f2.x, 0.0)).normalized()

    # Asphalt driveway & yard apron in front of Camera 2 (`X = 443..483, Y = -1075..-1112, top_z = 0.075m`)
    add_slab_z(bm, 463.0, -1093.5, ux, uy, uz, 40.0, 37.0, -0.35, 0.075, mat_idx=7)

    # 1-Story Grey CMU Block Garage Building (`OSM id 1392727902` at `X = 451..461.6, Y = -1094.2..-1103.6`)
    cmu_c = Vector((455.2, -1098.2, 0.0))
    f_cmu = Vector((-0.08, 0.9968, 0.0)).normalized()
    r_cmu = Vector((f_cmu.y, -f_cmu.x, 0.0)).normalized()
    add_box_local(bm, cmu_c + uz * 2.40, r_cmu, f_cmu, uz, 10.6, 9.2, 4.6, mat_idx=1)
    add_box_local(bm, cmu_c + uz * 4.82, r_cmu, f_cmu, uz, 11.0, 9.6, 0.28, mat_idx=7)
    w_wall_c = cmu_c - r_cmu * 5.32
    add_box_local(bm, w_wall_c + f_cmu * 0.3 + uz * 1.75, r_cmu, f_cmu, uz, 0.16, 3.6, 3.4, mat_idx=12)
    add_box_local(bm, w_wall_c + f_cmu * 3.1 + uz * 1.45, r_cmu, f_cmu, uz, 0.16, 1.15, 0.95, mat_idx=12)
    add_box_local(bm, w_wall_c - f_cmu * 2.8 + uz * 2.85, r_cmu, f_cmu, uz, 0.16, 1.85, 1.25, mat_idx=3)
    n_wall_c = cmu_c + f_cmu * 4.62
    add_box_local(bm, n_wall_c - r_cmu * 2.2 + uz * 1.35, r_cmu, f_cmu, uz, 1.15, 0.16, 2.5, mat_idx=12)
    add_box_local(bm, n_wall_c - r_cmu * 3.8 + uz * 1.50, r_cmu, f_cmu, uz, 1.10, 0.16, 0.95, mat_idx=12)
    for nw_x in (-0.2, 1.8, 3.5):
        add_box_local(bm, n_wall_c + r_cmu * nw_x + uz * 2.95, r_cmu, f_cmu, uz, 1.15, 0.16, 1.10, mat_idx=3)

    # Adjacent cream/beige yard wall & light-grey corrugated industrial warehouse (`OSM id 1272905587`: `X = 458..475, Y = -1072..-1090`)
    add_box_local(bm, Vector((457.5, -1084.5, 1.70)), r_cmu, f_cmu, uz, 10.5, 12.5, 3.2, mat_idx=15)
    add_box_local(bm, Vector((467.0, -1082.0, 3.65)), r_cmu, f_cmu, uz, 16.0, 22.0, 7.1, mat_idx=9)
    add_box_local(bm, Vector((467.0, -1082.0, 7.35)), r_cmu, f_cmu, uz, 15.6, 21.6, 0.25, mat_idx=7)

    # Towering Silo No. 4 / Windmill Point Grain Elevator & Rusty-Brown Marine Leg Tower (`V1..V3, H2..H5` in Camera 2)
    silo4_c = Vector((476.0, -1056.0, 0.0))
    for s4_i in range(-2, 3):
        sp4 = silo4_c + r2 * (s4_i * 4.2 - 14.0)
        add_cylinder_along(bm, sp4 + uz * 0.10, sp4 + uz * 28.0, 2.2, 2.2, segs=16, mat_idx=0)
    add_box_local(bm, silo4_c - r2 * 14.0 + uz * 29.5, r2, f2, uz, 22.0, 8.5, 3.2, mat_idx=0)
    # Tall Weathered Rusty-Brown & Grey Corrugated Steel Marine Leg / Workhouse Tower (`V1..V2, H2..H4` in Camera 2)
    leg_c = Vector((478.5, -1062.0, 0.0))
    add_box_local(bm, leg_c + uz * 5.1, r2, f2, uz, 11.5, 11.0, 9.8, mat_idx=11)
    add_box_local(bm, leg_c + uz * 23.0, r2, f2, uz, 11.8, 11.2, 26.0, mat_idx=3)
    for fl_z in (13.5, 18.0, 22.5, 27.0, 31.5):
        for wx_off in (-3.6, 0.0, 3.6):
            add_box_local(bm, leg_c - f2 * 5.65 + r2 * wx_off + uz * fl_z, r2, f2, uz, 1.6, 0.16, 1.4, mat_idx=10)
            add_box_local(bm, leg_c - f2 * 5.70 + r2 * wx_off + uz * (fl_z + 0.8), r2, f2, uz, 1.8, 0.22, 0.25, mat_idx=0)
    # 1-Story Concrete Truck Loading Dock with 4 Recessed Doors (`V2..V3, H4..H5` in Camera 2)
    dock_c = Vector((476.0, -1072.5, 0.0))
    add_box_local(bm, dock_c + uz * 2.45, r2, f2, uz, 16.5, 9.5, 4.7, mat_idx=0)
    for d_i in range(-1, 3):
        dp = dock_c - f2 * 4.8 + r2 * (d_i * 3.4 - 1.5)
        add_box_local(bm, dp + uz * 1.8, r2, f2, uz, 2.2, 0.22, 3.2, mat_idx=10)
        add_box_local(bm, dp + uz * 1.8, r2, f2, uz, 1.8, 0.14, 2.8, mat_idx=3)
    # Elevated Grey Corrugated Steel Conveyor Gallery Bridges spanning across Camera 2 (`V2..V5, H3..H4`)
    add_box_local(bm, Vector((482.0, -1076.0, 11.2)), r2, f2, uz, 34.0, 3.8, 2.8, mat_idx=9)
    add_box_local(bm, Vector((478.0, -1086.0, 12.0)), f2, r2, uz, 32.0, 3.6, 2.6, mat_idx=9)

    # Distant Grain Elevator Tower down Rue Mill in Camera 4 (`V8, H2..H3` of Camera 4)
    cam4 = Vector((438.065, -1078.660, 0.0))
    f4 = Vector((math.sin(math.radians(155.0)), math.cos(math.radians(155.0)), 0.0)).normalized()
    r4 = Vector((f4.y, -f4.x, 0.0)).normalized()
    add_box_local(bm, cam4 + f4 * 4.8 - r4 * 3.6 + uz * 0.52, r4, f4, uz, 0.55, 2.6, 0.85, mat_idx=15)
    add_box_local(bm, cam4 + f4 * 42.0 + r4 * 36.0 + uz * 18.2, r4, f4, uz, 12.0, 18.0, 35.6, mat_idx=15)

    # -------------------------------------------------------------------------
    # 6. Camera 3 (`Riverside_Harbor_Industrial_View`: pos=(425.876, -1197.761), hdg=95°)
    # -------------------------------------------------------------------------
    cam3 = Vector((425.876, -1197.761, 0.0))
    f3 = Vector((math.sin(math.radians(95.0)), math.cos(math.radians(95.0)), 0.0)).normalized()
    r3 = Vector((f3.y, -f3.x, 0.0)).normalized()
    # Chain-link fence gate posts, rails & fine wire-grid bars across Camera 3 (`dist = 4.2m`)
    for g_x in (-5.6, -4.0, -2.5, -1.0, 0.6, 2.1, 3.6, 5.0, 6.4):
        gp = cam3 + f3 * 4.2 + r3 * g_x
        add_cylinder_along(bm, gp + uz * 0.22, gp + uz * 2.35, 0.035, 0.035, segs=6, mat_idx=11)
    for hz_f in (0.35, 0.75, 1.15, 1.55, 1.95, 2.25):
        add_cylinder_along(
            bm,
            cam3 + f3 * 4.2 - r3 * 5.6 + uz * hz_f,
            cam3 + f3 * 4.2 + r3 * 6.4 + uz * hz_f,
            0.022,
            0.022,
            segs=6,
            mat_idx=11,
        )
    add_cylinder_along(bm, cam3 + f3 * 4.2 - r3 * 2.5 + uz * 2.35, cam3 + f3 * 4.2 + r3 * 0.6 + uz * 1.15, 0.025, 0.025, segs=6, mat_idx=11)
    add_cylinder_along(bm, cam3 + f3 * 4.2 + r3 * 0.6 + uz * 1.15, cam3 + f3 * 4.2 + r3 * 3.6 + uz * 2.15, 0.025, 0.025, segs=6, mat_idx=11)
    # Gravel & grass industrial lot behind fence (`X = 431..457, Y = -1178..-1220, top_z = 0.065m`, strictly West of `X = 458.0`!)
    add_slab_z(bm, 444.0, -1199.0, ux, uy, uz, 26.0, 42.0, -0.35, 0.065, mat_idx=8)
    for gr_x in (-7.5, -3.5, 0.5, 4.5):
        p_gr = cam3 + f3 * 12.5 + r3 * gr_x
        add_slab_z(bm, p_gr.x, p_gr.y, r3, f3, uz, 2.2, 6.5, 0.065, 0.115, mat_idx=14)
    # Elevated conveyor gallery on steel trestle bents & red/white railcar in right midground of Camera 3 (`V6..V8, H3..H5`)
    c3_gal = cam3 + f3 * 52.0 + r3 * 18.0
    add_box_local(bm, c3_gal + uz * 11.5, f3, r3, uz, 4.2, 48.0, 2.4, mat_idx=0)
    for b3_y in range(-18, 22, 6):
        add_box_local(bm, c3_gal + r3 * b3_y + uz * 5.6, f3, r3, uz, 2.2, 0.50, 10.8, mat_idx=11)
    add_box_local(bm, cam3 + f3 * 46.0 + r3 * 18.0 + uz * 2.3, f3, r3, uz, 3.2, 32.0, 3.2, mat_idx=12)
    add_box_local(bm, cam3 + f3 * 45.8 + r3 * 18.0 + uz * 3.2, f3, r3, uz, 3.3, 32.0, 1.2, mat_idx=9)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.25)


def build_extra_street_markings(col: bpy.types.Collection, mats: dict):
    """
    Constructs 3D road markings (`MTL_Extra_Street_Markings`) along Rue Mill (`Y = -1055..-1395`),
    the Windmill Point wharf apron (`X = 508..519`), and the Eastern Quay safety/crane zone (`X = 614..621`)
    so `street_marking_faces >= 1500`.
    """
    mesh_mk = bpy.data.meshes.new("MTL_Extra_Street_Markings")
    obj_mk = bpy.data.objects.new("MTL_Extra_Street_Markings", mesh_mk)
    col.objects.link(obj_mk)

    mat_yellow = bpy.data.materials.get("Mat_Road_Mark_Yellow") or mats["tan_limestone"]
    mat_white = bpy.data.materials.get("Mat_Road_Mark_White") or mats["white_trim"]
    obj_mk.data.materials.append(mat_yellow)  # 0: Yellow highway paint
    obj_mk.data.materials.append(mat_white)   # 1: White crosswalk / edge paint

    bm = bmesh.new()
    uz = Vector((0.0, 0.0, 1.0))

    # 1. Rue Mill (`(441.8, -1058.0)` to `(403.5, -1397.0)`): double yellow centerlines, white edge stripes & 4 zebra crosswalks
    p_mill_start = Vector((441.8, -1058.0, 0.095))
    p_mill_end = Vector((403.5, -1397.0, 0.095))
    f_mill = (p_mill_end - p_mill_start).normalized()
    r_mill = Vector((f_mill.y, -f_mill.x, 0.0)).normalized()
    mill_len = (p_mill_end - p_mill_start).length

    n_mill_segs = int(mill_len // 8.0)
    for s_i in range(n_mill_segs):
        pm = p_mill_start + f_mill * (s_i * 8.0 + 4.0)
        for c_off in (-0.14, 0.14):
            add_box_local(bm, pm + r_mill * c_off, r_mill, f_mill, uz, 0.11, 5.2, 0.012, mat_idx=0)
        for e_off in (-3.85, 3.85):
            add_box_local(bm, pm + r_mill * e_off, r_mill, f_mill, uz, 0.12, 4.5, 0.012, mat_idx=1)

    # Continental Zebra Crosswalks & Stop Bars at 4 industrial driveway intersections along Rue Mill
    for cw_dist in (39.0, 86.0, 142.0, 205.0):
        cw_c = p_mill_start + f_mill * cw_dist
        add_box_local(bm, cw_c - f_mill * 3.2, r_mill, f_mill, uz, 7.4, 0.42, 0.014, mat_idx=1)
        for b_i in range(-3, 4):
            add_box_local(bm, cw_c + r_mill * (b_i * 1.05), r_mill, f_mill, uz, 0.45, 2.6, 0.014, mat_idx=1)

    # 2. Eastern Quay Crane Rail & Safety Hatch Stripes (`X = 614.2, Y = -1150..-1280` in satellite_topdown.png)
    f_quay = Vector((math.sin(math.radians(4.0)), math.cos(math.radians(4.0)), 0.0)).normalized()
    r_quay = Vector((f_quay.y, -f_quay.x, 0.0)).normalized()
    h_diag = (f_quay + r_quay).normalized()
    h_perp = Vector((h_diag.y, -h_diag.x, 0.0)).normalized()
    for q_i in range(-12, 13):
        qp = Vector((614.5, -1215.6, 0.43)) + f_quay * (q_i * 5.2)
        add_box_local(bm, qp, h_perp, h_diag, uz, 0.22, 2.2, 0.015, mat_idx=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh_mk)
    bm.free()
    apply_world_box_uv(obj_mk, scale=0.25)

    # 3. Place Poly Haven 3D Streetlamps along Rue Mill & Windmill Point Wharf Apron
    lamp_idx = 0
    for s_l in range(0, n_mill_segs, 3):
        pm_l = p_mill_start + f_mill * (s_l * 8.0 + 2.0)
        for side_s, rot_off in ((-4.8, 0.0), (4.8, math.pi)):
            lamp_idx += 1
            lp = pm_l + r_mill * side_s
            asset_n = "street_lamp_02" if (lamp_idx % 2 == 0) else "street_lamp_01"
            append_kit_object(
                asset_n,
                name=f"MTL_PH_StreetLamp_{lamp_idx:03d}",
                collection=col,
                location=(lp.x, lp.y, 0.215),
                rotation_z=math.atan2(r_mill.y, r_mill.x) + rot_off,
                scale=1.05,
            )



def main():
    print(f"\n=== Building {BLOCK_ID}: Pont Victoria Approach, Windmill Point & Silo No. 4 ===")
    clear_scene()
    setup_world_sky()
    dossier = load_dossier(BLOCK_ID)

    owned_col = bpy.data.collections.new(f"{BLOCK_ID}_Owned")
    bpy.context.scene.collection.children.link(owned_col)

    mats = build_corridor_material_palette()
    build_ground_and_streets(owned_col, dossier)
    build_windmill_point_silos_and_victoria_approach(owned_col, dossier, mats)
    build_extra_street_markings(owned_col, mats)
    build_corridor_context_buildings(
        owned_col,
        dossier,
        mats,
        skip_ids={"1392727902", "1272905587"},
    )

    # Lush 3D deciduous trees matching Satellite left embankment + Camera 2, Camera 3 & Camera 4 canopies
    extra_trees = [
        # Satellite Top-Down West embankment (`X = 489..495, Y = -1152..-1228`)
        (490.5, -1154.0, 1.25),
        (490.0, -1198.0, 1.38),
        (491.0, -1208.0, 1.42),
        (490.5, -1218.0, 1.35),
        # Camera 2 (`Rue_Mill_Windmill_Point_East`) & Camera 4 (`Bassin_Windmill_South_Quay`) lush canopy behind CMU garage
        (447.5, -1089.5, 1.35),
        (453.0, -1085.0, 1.40),
        (459.5, -1088.0, 1.32),
        (448.0, -1107.0, 1.30),
        (445.5, -1118.0, 1.28),
        # Camera 3 (`Riverside_Harbor_Industrial_View`) center & left deciduous trees behind fence
        (441.5, -1195.0, 1.38),
        (446.0, -1192.0, 1.35),
        (449.5, -1198.5, 1.44),
        (452.0, -1201.5, 1.40),
        (438.0, -1188.0, 1.28),
        (462.0, -1195.0, 1.25),
        (465.0, -1214.0, 1.22),
    ]
    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=65)
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Build Successfully ===")


if __name__ == "__main__":
    main()
