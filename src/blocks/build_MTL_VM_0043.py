#!/usr/bin/env python3
"""
High-Poly 3D Architecture, Streetscape & Urban Promenade Modeler — Block `MTL-VM-0043`
(`Place d'Youville East, Édifice des Douanes South & Rue Saint-Pierre Heritage Warehouses`)
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

BLOCK_ID = "MTL-VM-0043"


def add_fenestrated_wing(
    bm: bmesh.types.BMesh,
    center_xy: Vector,
    ux: Vector,
    uy: Vector,
    sx: float,
    sy: float,
    height: float,
    n_floors: int,
    wall_mat: int,
    base_mat: int,
    trim_mat: int,
    glass_mat: int,
    roof_mat: int,
    metal_mat: int,
    pitched_roof: bool = False,
    quoins: bool = False,
):
    """
    Builds a multi-part 3D heritage masonry building wing with rusticated ground base,
    corner quoins, floor-by-floor recessed windows, stone sills/lintels, cornice, and roof.
    """
    uz = Vector((0.0, 0.0, 1.0))
    base_h = min(3.4, height * 0.25)
    upper_h = height - base_h

    # Ground base & upper masonry mass
    add_box_local(bm, center_xy + uz * (base_h * 0.5), ux, uy, uz, sx + 0.16, sy + 0.16, base_h, mat_idx=base_mat)
    add_box_local(bm, center_xy + uz * (base_h + upper_h * 0.5), ux, uy, uz, sx, sy, upper_h, mat_idx=wall_mat)

    # Belt course above ground floor & projecting crown cornice
    add_box_local(bm, center_xy + uz * base_h, ux, uy, uz, sx + 0.32, sy + 0.32, 0.28, mat_idx=trim_mat)
    add_box_local(bm, center_xy + uz * (height - 0.18), ux, uy, uz, sx + 0.44, sy + 0.44, 0.36, mat_idx=trim_mat)
    add_box_local(bm, center_xy + uz * (height + 0.22), ux, uy, uz, sx + 0.18, sy + 0.18, 0.44, mat_idx=base_mat)
    add_box_local(bm, center_xy + uz * (height + 0.06), ux, uy, uz, sx - 0.55, sy - 0.55, 0.16, mat_idx=roof_mat)

    if pitched_roof:
        # Gabled/mansard slate roof tier
        add_box_local(bm, center_xy + uz * (height + 1.35), ux, uy, uz, sx - 1.4, sy - 1.4, 2.3, mat_idx=roof_mat)
        add_box_local(bm, center_xy + uz * (height + 2.58), ux, uy, uz, sx - 2.6, sy - 2.6, 0.24, mat_idx=metal_mat)

    if quoins:
        # Rusticated limestone corner quoins
        n_q = int(height // 0.85)
        for q_i in range(n_q):
            zq = 0.42 + q_i * 0.85
            q_len = 0.85 if (q_i % 2 == 0) else 0.52
            for cx_s in (-1.0, 1.0):
                for cy_s in (-1.0, 1.0):
                    cp = center_xy + ux * (cx_s * sx * 0.5) + uy * (cy_s * sy * 0.5) + uz * zq
                    add_box_local(bm, cp, ux, uy, uz, q_len, q_len, 0.38, mat_idx=trim_mat)

    # Floor-by-floor recessed windows on all 4 facades
    floor_h = (height - 0.7) / max(1, n_floors)
    for u_tan, u_out, face_len, face_depth in (
        (ux, -uy, sx, sy * 0.5),
        (-ux, uy, sx, sy * 0.5),
        (uy, ux, sy, sx * 0.5),
        (-uy, -ux, sy, sx * 0.5),
    ):
        if face_len < 4.5:
            continue
        n_bays = max(2, min(11, int(face_len // 3.4)))
        bay_w = face_len / n_bays
        win_w = min(1.65, bay_w * 0.52)
        win_h = min(1.75, floor_h * 0.56)
        face_c = center_xy + u_out * face_depth
        for fl in range(n_floors):
            z_fl = 0.45 + (fl + 0.52) * floor_h
            for b_i in range(n_bays):
                x_off = -0.5 * face_len + (b_i + 0.5) * bay_w
                wp = face_c + u_tan * x_off + uz * z_fl
                # Window frame, recessed glazing, sill & lintel
                add_box_local(bm, wp + u_out * 0.05, u_tan, u_out, uz, win_w + 0.22, 0.12, win_h + 0.20, mat_idx=trim_mat)
                add_box_local(bm, wp + u_out * 0.10, u_tan, u_out, uz, win_w, 0.06, win_h, mat_idx=glass_mat)
                add_box_local(bm, wp + u_out * 0.10, u_tan, u_out, uz, 0.06, 0.09, win_h, mat_idx=metal_mat)
                add_box_local(bm, wp + u_out * 0.14 - uz * (win_h * 0.5 + 0.08), u_tan, u_out, uz, win_w + 0.34, 0.24, 0.12, mat_idx=trim_mat)
                add_box_local(bm, wp + u_out * 0.13 + uz * (win_h * 0.5 + 0.10), u_tan, u_out, uz, win_w + 0.28, 0.18, 0.16, mat_idx=trim_mat)


def build_place_dyouville_and_landmarks(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Constructs:
    1. Place d'Youville East Landscaped Median Promenade (`X = 95..162, Y = -410..-225`), granite paths,
       Pioneer Obelisk Monument (`X = 149.2, Y = -284.5`), raised stone planter curbs & benches.
    2. Pointe-à-Callière / Éperon & Édifice des Douanes South Facade (`X = 163..206, Y = -263..-208`)
       with cut-ashlar grey limestone blocks, horizontal recessed shadow reveals & glazed atrium colonnade (Camera 2).
    3. Uville Hotel & Red-Brick / Limestone Corner Prow (`X = 161..190, Y = -298..-263`) right beside Camera 1.
    4. Rue de la Commune / Rue du Port 5-Storey Cut-Limestone Corner Warehouse with Quoins (`X = 185..211, Y = -330..-268`)
       in front of Camera 3 (`(221.68, -334.59)`, hdg 305°).
    5. Rue Saint-Pierre 2-Storey Grey-Stone Gabled Heritage House with Black Awnings (`X = 128..160, Y = -363..-351`)
       & Turreted 4-Storey Corner Building in front of Camera 4 (`(124.56, -359.34)`, hdg 55°).
    """
    mesh = bpy.data.meshes.new("MTL_VM_0043_Hero_Landmarks")
    obj = bpy.data.objects.new("MTL_VM_0043_Hero_Landmarks", mesh)
    col.objects.link(obj)
    for k in (
        "plaza_beige",        # 0: Place d'Youville granite promenade & courtyard paving
        "park_grass",         # 1: Place d'Youville landscaped lawn beds & courtyard garden
        "grey_limestone",     # 2: Montreal Pierre Grise cut-limestone ashlar masonry
        "tan_limestone",      # 3: Warm Chomedey limestone trim, quoins, cornices & obelisk
        "victorian_brick",    # 4: Red-brick heritage facade (Camera 1 left wall & mid-block wings)
        "dark_glass",         # 5: Recessed window glazing & Pointe-à-Callière curtain wall
        "white_trim",         # 6: White/cream window frames, crosswalk stripes & curb coping
        "dark_metal",         # 7: Black wrought-iron fencing, canopies/awnings, mullions & bollards
        "roof_slates",        # 8: Heritage slate pitched roofs & turret cone
        "roof_light_gravel",  # 9: Flat gravel/elastomer roofs
        "copper_verdigris",   # 10: Patinated copper roof accents
    ):
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    ux = Vector((1.0, 0.0, 0.0))
    uy = Vector((0.0, 1.0, 0.0))
    uz = Vector((0.0, 0.0, 1.0))

    # Orientation vectors along Place d'Youville axis (~34° NE)
    youv_dir = Vector((0.555, 0.832, 0.0)).normalized()
    youv_perp = Vector((0.832, -0.555, 0.0)).normalized()

    # --------------------------------------------------------------------------
    # 1. Place d'Youville East Tree-Lined Median Esplanade & Pioneer Obelisk
    # --------------------------------------------------------------------------
    prom_c = Vector((132.0, -312.0, 0.0))
    add_box_local(bm, prom_c + uz * 0.10, youv_perp, youv_dir, uz, 15.5, 165.0, 0.20, mat_idx=0)
    # Raised granite planter curbs & lush green lawn strips along the median
    for seg_y in (-62.0, -28.0, 8.0, 42.0):
        bed_c = prom_c + youv_dir * seg_y
        add_box_local(bm, bed_c + uz * 0.22, youv_perp, youv_dir, uz, 9.6, 24.0, 0.22, mat_idx=3)
        add_box_local(bm, bed_c + uz * 0.28, youv_perp, youv_dir, uz, 8.6, 22.8, 0.14, mat_idx=1)

    # Pioneer Obelisk Monument on Place d'Youville median (visible in Camera 1 at X=150.5, Y=-282.0)
    ob_c = Vector((150.5, -282.0, 0.20))
    add_box_local(bm, ob_c + uz * 0.35, youv_perp, youv_dir, uz, 4.2, 4.2, 0.70, mat_idx=2)
    add_box_local(bm, ob_c + uz * 1.15, youv_perp, youv_dir, uz, 2.8, 2.8, 1.10, mat_idx=3)
    add_cylinder_along(bm, ob_c + uz * 1.70, ob_c + uz * 8.40, 0.82, 0.42, segs=4, mat_idx=3, cap_ends=True)
    add_cylinder_along(bm, ob_c + uz * 8.40, ob_c + uz * 9.35, 0.42, 0.02, segs=4, mat_idx=3, cap_ends=True)

    # --------------------------------------------------------------------------
    # 2. Camera 1 Left Wall: Red-Brick Heritage Prow on Limestone Base (X=164..170, Y=-258..-248)
    #    & Uville Hotel / Place d'Youville South-East Row (X=161..188, Y=-298..-264)
    #    Positioned carefully on the East/Left side of Camera 1 (`(170.34, -260.51)`, hdg 215°)
    #    so the left 35% of Camera 1 shows the red-brick wall + limestone base while the right 65%
    #    opens onto the sunny Place d'Youville tree walk & obelisk.
    # --------------------------------------------------------------------------
    cam1_wall_c = Vector((171.2, -269.0, 0.0))
    add_fenestrated_wing(
        bm, cam1_wall_c, youv_perp, youv_dir,
        sx=7.6, sy=12.0, height=16.5, n_floors=4,
        wall_mat=4, base_mat=2, trim_mat=3, glass_mat=5, roof_mat=9, metal_mat=7,
        pitched_roof=False, quoins=True,
    )
    # Uville Hotel & adjacent Place d'Youville East heritage facades (facing NW toward median)
    uville_c = Vector((178.8, -278.5, 0.0))
    add_fenestrated_wing(
        bm, uville_c, youv_perp, youv_dir,
        sx=18.0, sy=16.5, height=15.2, n_floors=4,
        wall_mat=3, base_mat=2, trim_mat=6, glass_mat=5, roof_mat=9, metal_mat=7,
        pitched_roof=False, quoins=True,
    )
    mid_youv_c = Vector((171.5, -294.5, 0.0))
    add_fenestrated_wing(
        bm, mid_youv_c, youv_perp, youv_dir,
        sx=19.5, sy=16.0, height=15.8, n_floors=4,
        wall_mat=2, base_mat=2, trim_mat=3, glass_mat=5, roof_mat=8, metal_mat=7,
        pitched_roof=True, quoins=True,
    )

    # --------------------------------------------------------------------------
    # 3. Camera 2 Hero: Pointe-à-Callière / Édifice des Douanes South Facade
    #    (`X = 165..206, Y = -262..-215`) directly in front of Camera 2 (`(190.73, -263.77)`, hdg 35°)
    #    Features precision grey ashlar limestone, horizontal shadow-reveal channels & glazed colonnade on right.
    # --------------------------------------------------------------------------
    pac_u_tan = Vector((0.982, -0.190, 0.0)).normalized()
    pac_u_in = Vector((0.190, 0.982, 0.0)).normalized()
    pac_c = Vector((187.5, -242.0, 0.0))
    add_box_local(bm, pac_c + uz * 9.5, pac_u_tan, pac_u_in, uz, 38.0, 32.0, 19.0, mat_idx=2)
    add_box_local(bm, pac_c + uz * 19.15, pac_u_tan, pac_u_in, uz, 38.6, 32.6, 0.35, mat_idx=3)
    add_box_local(bm, pac_c + uz * 19.25, pac_u_tan, pac_u_in, uz, 36.8, 30.8, 0.20, mat_idx=9)

    # South wall directly facing Camera 2: horizontal stone reveal bands + vertical glazed curtain wall on East end
    south_wall_c = Vector((191.5, -258.2, 0.0))
    add_box_local(bm, south_wall_c + uz * 8.2, pac_u_tan, pac_u_in, uz, 26.0, 2.4, 16.4, mat_idx=2)
    for z_rev in (1.4, 2.6, 3.8, 5.0, 6.2, 9.5, 12.8):
        add_box_local(bm, south_wall_c - pac_u_in * 1.24 + uz * z_rev, pac_u_tan, pac_u_in, uz, 26.2, 0.14, 0.09, mat_idx=7)
    # Tall vertical-mullion glass curtain-wall bay on right side of Camera 2
    glass_bay_c = south_wall_c + pac_u_tan * 9.5 - pac_u_in * 1.15
    add_box_local(bm, glass_bay_c + uz * 4.8, pac_u_tan, pac_u_in, uz, 7.6, 0.18, 9.2, mat_idx=5)
    for m_i in range(-5, 6):
        add_box_local(bm, glass_bay_c + pac_u_tan * (m_i * 0.68) - pac_u_in * 0.08 + uz * 4.8, pac_u_tan, pac_u_in, uz, 0.09, 0.22, 9.2, mat_idx=7)

    # --------------------------------------------------------------------------
    # 4. Camera 3 Hero: Rue de la Commune / Rue du Port 5-Storey Cut-Limestone Corner Building
    #    (`X = 186..210, Y = -330..-270`) directly in front of Camera 3 (`(221.68, -334.59)`, hdg 305°)
    # --------------------------------------------------------------------------
    port_u_x = Vector((0.990, -0.140, 0.0)).normalized()
    port_u_y = Vector((0.140, 0.990, 0.0)).normalized()
    # South corner 5-storey ashlar limestone warehouse (ID 339872704 & 339872897)
    comm_corner_c = Vector((197.8, -315.5, 0.0))
    add_fenestrated_wing(
        bm, comm_corner_c, port_u_x, port_u_y,
        sx=22.5, sy=26.5, height=17.8, n_floors=5,
        wall_mat=2, base_mat=2, trim_mat=3, glass_mat=5, roof_mat=9, metal_mat=7,
        pitched_roof=False, quoins=True,
    )
    # Stepped parapet gable on the East facade facing Rue de la Commune
    add_box_local(bm, comm_corner_c + port_u_x * 11.1 + uz * 18.4, port_u_x, port_u_y, uz, 0.45, 7.5, 1.1, mat_idx=3)
    # Adjacent North 4-storey limestone buildings along Rue de la Commune (ID 339872966 & 339873280)
    comm_north_c = Vector((197.5, -286.5, 0.0))
    add_fenestrated_wing(
        bm, comm_north_c, port_u_x, port_u_y,
        sx=19.5, sy=29.0, height=14.6, n_floors=4,
        wall_mat=3, base_mat=2, trim_mat=2, glass_mat=5, roof_mat=8, metal_mat=7,
        pitched_roof=True, quoins=True,
    )
    # South-East block across Rue du Port (Left side of Camera 3: ID 339873329, X=181..213, Y=-358..-337)
    comm_south_c = Vector((196.5, -347.8, 0.0))
    add_fenestrated_wing(
        bm, comm_south_c, port_u_x, port_u_y,
        sx=29.5, sy=17.5, height=15.5, n_floors=4,
        wall_mat=2, base_mat=2, trim_mat=3, glass_mat=5, roof_mat=8, metal_mat=7,
        pitched_roof=True, quoins=True,
    )
    # Foreground twin wooden/metal waste bins on corner sidewalk in Camera 3 (X=211.8, Y=-329.2)
    for b_off in (-0.38, 0.38):
        bc = Vector((211.8 + b_off, -329.2, 0.0))
        add_cylinder_along(bm, bc + uz * 0.20, bc + uz * 1.02, 0.28, 0.30, segs=12, mat_idx=4, cap_ends=True)

    # --------------------------------------------------------------------------
    # 5. Camera 4 Hero: Rue Saint-Pierre & Place d'Youville South-West Heritage Buildings
    #    In front of Camera 4 (`(124.56, -359.34)`, hdg 55°):
    #    - 2-Storey Grey-Stone Gabled Heritage Building (ID 188992664, `X=128..160, Y=-363..-351`) with black awnings
    #    - 4-Storey Corner Turreted Limestone Building (`X=146..166, Y=-323..-294`, ID 339872703) with octagonal corner turret
    # --------------------------------------------------------------------------
    sp_u_x = Vector((0.982, -0.188, 0.0)).normalized()
    sp_u_y = Vector((0.188, 0.982, 0.0)).normalized()
    # 2-Storey Grey-Stone Gabled Heritage Building (right foreground of Camera 4)
    st_pierre_house_c = Vector((144.2, -357.5, 0.0))
    add_fenestrated_wing(
        bm, st_pierre_house_c, sp_u_x, sp_u_y,
        sx=30.5, sy=7.2, height=8.4, n_floors=2,
        wall_mat=2, base_mat=2, trim_mat=3, glass_mat=5, roof_mat=8, metal_mat=7,
        pitched_roof=True, quoins=True,
    )
    # Black canvas window awnings on the West gable end facing Camera 4
    west_gable_c = st_pierre_house_c - sp_u_x * 15.3
    for y_awn in (-1.6, 1.6):
        ap = west_gable_c + sp_u_y * y_awn + uz * 3.15
        add_box_local(bm, ap - sp_u_x * 0.45, sp_u_y, sp_u_x, uz, 1.75, 0.85, 0.65, mat_idx=7)
    # Wrought-iron fence along the right foreground of Camera 4
    for f_i in range(8):
        fp = west_gable_c - sp_u_y * (3.8 + f_i * 0.85)
        add_box_local(bm, fp + uz * 0.95, sp_u_x, sp_u_y, uz, 0.06, 0.06, 1.9, mat_idx=7)

    # 4-Storey Turreted Corner Heritage Building (center-left midground of Camera 4, ID 339872703)
    turret_bldg_c = Vector((156.5, -309.5, 0.0))
    add_fenestrated_wing(
        bm, turret_bldg_c, youv_perp, youv_dir,
        sx=18.5, sy=26.0, height=15.6, n_floors=4,
        wall_mat=3, base_mat=2, trim_mat=2, glass_mat=5, roof_mat=8, metal_mat=7,
        pitched_roof=True, quoins=True,
    )
    # Iconic Corner Cylindrical/Octagonal Turret & Conical Slate Spire at SW prow (`X = 144.8, Y = -318.8`)
    tur_p = Vector((144.8, -318.8, 0.0))
    add_cylinder_along(bm, tur_p + uz * 0.0, tur_p + uz * 17.5, 2.35, 2.35, segs=12, mat_idx=3, cap_ends=True)
    add_cylinder_along(bm, tur_p + uz * 17.5, tur_p + uz * 21.8, 2.55, 0.08, segs=12, mat_idx=8, cap_ends=True)

    # Landscaped Private Courtyard Garden in the SE quadrant (`X = 165..205, Y = -370..-352`) seen in satellite view
    court_c = Vector((184.0, -362.0, 0.0))
    add_box_local(bm, court_c + uz * 0.09, port_u_x, port_u_y, uz, 38.0, 14.5, 0.18, mat_idx=0)
    add_box_local(bm, court_c - port_u_x * 6.0 + uz * 0.19, port_u_x, port_u_y, uz, 18.0, 8.5, 0.10, mat_idx=1)
    fount_se = Vector((193.5, -363.2, 0.0))
    add_cylinder_along(bm, fount_se + uz * 0.18, fount_se + uz * 0.45, 2.4, 2.4, segs=20, mat_idx=6, cap_ends=True)
    add_cylinder_along(bm, fount_se + uz * 0.45, fount_se + uz * 0.50, 1.9, 1.9, segs=20, mat_idx=5, cap_ends=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.25)


def main():
    print(f"\n=== Building {BLOCK_ID}: Place d'Youville East & Édifice des Douanes South ===")
    clear_scene()
    setup_world_sky()
    dossier = load_dossier(BLOCK_ID)

    owned_col = bpy.data.collections.new(f"{BLOCK_ID}_Owned")
    bpy.context.scene.collection.children.link(owned_col)

    mats = build_corridor_material_palette()
    build_ground_and_streets(owned_col, dossier)
    build_place_dyouville_and_landmarks(owned_col, dossier, mats)

    # Skip custom-modeled hero building IDs so context builder only fills remaining surrounding blocks
    skip_ids = {
        "87411702",   # Pointe-à-Callière / Éperon
        "339871601",  # Uville Hotel Montreal
        "339871602",  # Mid Place d'Youville East building
        "339872703",  # Turreted SW corner building
        "339872704",  # Rue de la Commune / Rue du Port corner building
        "339872897",  # Rue de la Commune mid building
        "339872966",  # Rue de la Commune north-mid building
        "339873280",  # Rue de la Commune north building
        "339873329",  # Rue de la Commune SE building across Rue du Port
        "188992664",  # Rue Saint-Pierre 2-storey stone heritage building
    }
    build_corridor_context_buildings(owned_col, dossier, mats, skip_ids=skip_ids)

    # Extra trees along Place d'Youville East median & Old Port promenade
    extra_trees = [
        (158.0, -250.0, 1.25),
        (153.5, -264.0, 1.32),
        (147.0, -274.0, 1.35),
        (141.0, -286.0, 1.40),
        (135.0, -298.0, 1.36),
        (128.0, -310.0, 1.42),
        (121.0, -322.0, 1.34),
        (114.0, -334.0, 1.38),
        (108.0, -346.0, 1.30),
        (171.0, -360.0, 1.25),
    ]
    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=80)
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Build Successfully ===")


if __name__ == "__main__":
    main()
