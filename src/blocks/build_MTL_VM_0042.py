#!/usr/bin/env python3
"""
High-Poly 3D Architecture, Streetscape & Urban Park Modeler — Block `MTL-VM-0042`
(`Square Viger Redesigned Urban Agora, Édifice Jacques-Viger & Avenue Viger Est`)
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

BLOCK_ID = "MTL-VM-0042"


def build_square_viger_and_intersections(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Models the redesigned Square Viger Urban Agora on the East half of the block (`X = 148..210, Y = 830..968`),
    the monumental Beaux-Arts limestone Édifice Jacques-Viger with 6 rooftop skylights (`X = 82..155, Y = 928..968`),
    the 4-way Rue Berri x Avenue Viger Est boulevard intersection with 4 continental zebra crosswalks,
    and the concrete pergola canopy & fountain basin seen in Camera 1 (`Square_Viger_West_Pergola_Lawn`).
    """
    mesh = bpy.data.meshes.new("MTL_VM_0042_Hero_Landmarks")
    obj = bpy.data.objects.new("MTL_VM_0042_Hero_Landmarks", mesh)
    col.objects.link(obj)
    for k in (
        "plaza_beige",        # 0: Square Viger tan/beige stone plaza & walkways
        "park_grass",         # 1: Square Viger manicured lawns
        "tan_limestone",      # 2: Beaux-Arts Édifice Jacques-Viger ashlar limestone
        "concrete_podium",    # 3: Brutalist concrete pergola columns & beam canopy
        "dark_glass",         # 4: Recessed window glazing & rooftop skylights
        "white_trim",         # 5: White road zebra stripes, cornice trim & fountain curb
        "dark_metal",         # 6: Anodized dark metal bollards, railings & bins
        "victorian_brick",    # 7: Red/brown brick mid-rise facade on SW corner
        "roof_light_gravel",  # 8: Light gravel roof membrane
    ):
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    ux = Vector((1.0, 0.0, 0.0))
    uy = Vector((0.0, 1.0, 0.0))
    uz = Vector((0.0, 0.0, 1.0))

    # 1. Square Viger East Park Lawns, Tan Stone Walkways & Circular Fountain Agora (X = 148..208, Y = 832..948)
    add_box_local(bm, Vector((178.0, 888.0, 0.09)), ux, uy, uz, 58.0, 112.0, 0.18, mat_idx=0)
    # Two large manicured green lawn quadrants (North-East & South-East) separated by diagonal tan walkway
    add_box_local(bm, Vector((182.0, 912.0, 0.20)), ux, uy, uz, 38.0, 36.0, 0.08, mat_idx=1)
    add_box_local(bm, Vector((176.0, 862.0, 0.20)), ux, uy, uz, 36.0, 34.0, 0.08, mat_idx=1)
    # Circular fountain plaza on the East edge (X = 202.0, Y = 884.0)
    fount_c = Vector((201.0, 884.0, 0.0))
    add_cylinder_along(bm, fount_c + uz * 0.16, fount_c + uz * 0.34, 11.5, 11.5, segs=28, mat_idx=0, cap_ends=True)
    add_cylinder_along(bm, fount_c + uz * 0.34, fount_c + uz * 0.52, 7.2, 7.2, segs=24, mat_idx=5, cap_ends=True)
    add_cylinder_along(bm, fount_c + uz * 0.52, fount_c + uz * 0.58, 6.4, 6.4, segs=24, mat_idx=4, cap_ends=True)

    # 2. Iconic Square Viger Brutalist Concrete Pergola Canopy (Right side of Camera 1: pos=(117.68, 855.82), hdg=65°)
    cam1 = Vector((117.676, 855.815, 0.0))
    f1 = Vector((math.sin(math.radians(65.0)), math.cos(math.radians(65.0)), 0.0)).normalized()
    r1 = Vector((f1.y, -f1.x, 0.0)).normalized()
    # Broad light-granite pedestrian plaza in front of Camera 1 (dist = 3m..38m, right = -2m..+22m)
    add_box_local(bm, cam1 + f1 * 18.0 + r1 * 8.5 + uz * 0.11, r1, f1, uz, 26.0, 36.0, 0.22, mat_idx=0)
    # Concrete Pergola Frame (dist = 16m..32m, right = +7.5m..+15.5m, Z = 0.22..4.4m)
    perg_c = cam1 + f1 * 22.0 + r1 * 11.0
    add_box_local(bm, perg_c + uz * 4.15, r1, f1, uz, 9.5, 16.0, 0.65, mat_idx=3)
    for px_s in (-4.1, 0.0, 4.1):
        for py_s in (-6.8, -2.2, 2.2, 6.8):
            col_p = perg_c + r1 * px_s + f1 * py_s
            add_box_local(bm, col_p + uz * 2.05, r1, f1, uz, 0.68, 0.68, 3.85, mat_idx=3)
    # Foreground wooden/metal cylindrical waste bins & bollard on right of Camera 1 (dist = 5.2m, right = +2.6m)
    for b_off in (-0.38, 0.38):
        bc = cam1 + f1 * 5.0 + r1 * (2.6 + b_off)
        add_cylinder_along(bm, bc + uz * 0.22, bc + uz * 1.05, 0.28, 0.30, segs=14, mat_idx=6, cap_ends=True)
    bol_c = cam1 + f1 * 6.8 + r1 * 1.15
    add_box_local(bm, bol_c + uz * 0.62, r1, f1, uz, 0.12, 0.12, 0.85, mat_idx=6)

    # 3. 4-Way Intersection Zebra Crosswalks at Rue Berri x Avenue Viger Est (Center = (115.0, 862.0))
    int_c = Vector((115.0, 862.0, 0.0))
    berri_dir = Vector((0.53, 0.85, 0.0)).normalized()
    viger_dir = Vector((0.85, -0.53, 0.0)).normalized()
    for cross_pos, bar_dir, span_dir in [
        (int_c + berri_dir * 12.5, berri_dir, viger_dir),
        (int_c - berri_dir * 12.5, berri_dir, viger_dir),
        (int_c + viger_dir * 12.5, viger_dir, berri_dir),
        (int_c - viger_dir * 12.5, viger_dir, berri_dir),
    ]:
        for k_bar in range(-6, 7):
            bp = cross_pos + span_dir * (k_bar * 1.15)
            add_box_local(bm, bp + uz * 0.052, span_dir, bar_dir, uz, 0.52, 2.8, 0.015, mat_idx=5)

    # 4. Beaux-Arts Édifice Jacques-Viger (NW Quadrant: X = 90..150, Y = 935..966, height = 22.0m) with 6 Rooftop Skylights
    jv_c = Vector((120.0, 950.0, 0.0))
    add_box_local(bm, jv_c + uz * 11.0, viger_dir, berri_dir, uz, 56.0, 32.0, 22.0, mat_idx=2)
    add_box_local(bm, jv_c + uz * 11.2, viger_dir, berri_dir, uz, 53.5, 29.5, 21.8, mat_idx=8)
    for sk_i in range(-2, 4):
        sk_p = jv_c + viger_dir * (sk_i * 3.2 - 2.0) + uz * 22.25
        add_box_local(bm, sk_p, viger_dir, berri_dir, uz, 1.8, 12.5, 0.45, mat_idx=4)
        add_box_local(bm, sk_p - uz * 0.15, viger_dir, berri_dir, uz, 2.1, 12.8, 0.25, mat_idx=5)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.25)


def main():
    print(f"\n=== Building {BLOCK_ID}: Square Viger & Avenue Viger Est ===")
    clear_scene()
    setup_world_sky()
    dossier = load_dossier(BLOCK_ID)

    owned_col = bpy.data.collections.new(f"{BLOCK_ID}_Owned")
    bpy.context.scene.collection.children.link(owned_col)

    mats = build_corridor_material_palette()
    build_ground_and_streets(owned_col, dossier)
    build_square_viger_and_intersections(owned_col, dossier, mats)
    build_corridor_context_buildings(owned_col, dossier, mats)

    # Extra trees inside Square Viger Park & along Rue Berri
    extra_trees = [
        (162.0, 895.0, 1.35),
        (168.0, 908.0, 1.42),
        (175.0, 922.0, 1.30),
        (156.0, 875.0, 1.28),
        (165.0, 862.0, 1.38),
        (188.0, 925.0, 1.25),
        (192.0, 868.0, 1.32),
        (145.0, 918.0, 1.35),
        (98.0, 845.0, 1.40),
    ]
    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=75)
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Build Successfully ===")


if __name__ == "__main__":
    main()
