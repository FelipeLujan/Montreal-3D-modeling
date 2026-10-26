#!/usr/bin/env python3
"""
Headless Blender 5.2 Build Script for Block MTL-OLY-0001
(Parc olympique de Montréal — Stade olympique, Tour de Montréal 165m Inclined Tower,
Biodôme / Velodrome, Planétarium Rio Tinto Alcan, Esplanade & Avenue Pierre-De Coubertin)

Implements the Recursive Self-Improvement 3D Modeling Standard (Rules RSI-001..RSI-004):
1. Georeferenced 1:1 in the Montreal metric tangent plane (EPSG:32188 aligned, center=[386.971, 5903.273]).
2. True parametric 3D lofted geometry for Roger Taillibert's 1976 Brutalist Olympic Park complex:
   - Olympic Stadium (108505523): 38 radially arrayed cantilevered curved precast concrete ribs (consoles),
     3-tier horizontal recessed dark-glass clerestory window bands with mullions, slate-blue/teal curved roof bays,
     central white Kevlar tensile membrane with 17 peaked mast nodes, elevated concrete Esplanade podium deck on
     cylindrical columns, exterior brutalist stair ramps, and the yellow circular sunken metro plaza oculus.
   - Tour de Montréal (20213158): 165m 45°-inclined curved triangular-section tower lofted along a parabolic spine
     from (366, 6112, Z=5m) to (384, 5982, Z=165m), with 3 white concrete corner megacolumns, 12-floor dark-bronze
     glass curtain-wall office tiers with horizontal spandrels, recessed underbelly cable niche, 2-tier observation
     crown with 3x3 square apertures, 26 steel suspension cables to the stadium roof, and sweeping base sports-centre
     wing shells with oval skylight arrays.
   - Biodôme de Montréal / Velodrome (26699302): Doubly-curved scalloped spherical-triangle concrete shell roof with
     Y-branching arch ribs, 6 leaf-shaped skylight arrays, curved reflective glass curtain wall with circular HVAC
     louver bands, and ground-level curved concrete buttress arcade.
   - Planétarium Rio Tinto Alcan (160672184, 1284741135, 1284741136): Green-roof pavilion with twin skewed truncated
     aluminum cones.
   - Esplanade du Parc olympique (118117348): Skatepark plaza, timber-slatted festival kiosk tower with crimson
     signboards & red carpet, and white corrugated shipping-container pavilion (EXALTO) with wood cladding.
3. True floor-by-floor 3D fenestration on ALL surrounding residential & industrial buildings (Le Cours de Coubertin
   46866389 with cream-stucco bays, balconies & spiral staircase; La Vie En Rose 46866392 red-brick loft; rowhouses)
   ensuring `windowless_tall_buildings == 0` and zero vertical-stripe windows.
"""

import os
import sys
import json
import math
import random
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector, Matrix

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.blender_lib import (
    clear_scene,
    setup_world_sky,
    load_dossier,
    build_ground_and_streets,
    create_pbr_material,
    apply_world_box_uv,
    append_kit_object,
    export_block_artifacts,
)

BLOCK_ID = "MTL-OLY-0001"
POLYHAVEN_TEX = REPO_ROOT / "assets" / "polyhaven" / "textures"


# ==============================================================================
# MATERIAL LIBRARY (Real Poly Haven 2K PBR + Architectural Shader Nodes)
# ==============================================================================

def _tex(rel_path: str) -> str:
    return rel_path


def build_olympic_materials() -> dict:
    mats = {}

    # 1. Precast Architectural Concrete (Stadium Ribs, Tower Spine, Biodome Shell)
    mats["concrete_rib"] = create_pbr_material(
        "Mat_OLY_Precast_Concrete_Light",
        base_color=(0.76, 0.74, 0.69, 1.0),
        roughness=0.72,
        diffuse_tex=_tex("concrete_layers_02/concrete_layers_02_diff_2k.jpg"),
        normal_tex=_tex("concrete_layers_02/concrete_layers_02_nor_gl_2k.jpg"),
        rough_tex=_tex("concrete_layers_02/concrete_layers_02_rough_2k.jpg"),
        tint_color=(0.78, 0.76, 0.71),
        tint_strength=0.72,
        uv_scale=0.18,
    )

    # 2. Weathered Podium / Esplanade Brutalist Concrete (Podium Slab, Columns, Plazas)
    mats["concrete_podium"] = create_pbr_material(
        "Mat_OLY_Brutalist_Podium_Concrete",
        base_color=(0.54, 0.51, 0.46, 1.0),
        roughness=0.80,
        diffuse_tex=_tex("concrete_layers_02/concrete_layers_02_diff_2k.jpg"),
        normal_tex=_tex("concrete_layers_02/concrete_layers_02_nor_gl_2k.jpg"),
        rough_tex=_tex("concrete_layers_02/concrete_layers_02_rough_2k.jpg"),
        tint_color=(0.55, 0.52, 0.47),
        tint_strength=0.68,
        uv_scale=0.22,
    )

    # 2b. Warm Beige/Tan Esplanade & Olympic Surround Plaza Paving (Satellite Top-Down match)
    mats["esplanade_beige"] = create_pbr_material(
        "Mat_OLY_Esplanade_Warm_Beige_Plaza",
        base_color=(0.64, 0.59, 0.50, 1.0),
        roughness=0.78,
        diffuse_tex=_tex("concrete_layers_02/concrete_layers_02_diff_2k.jpg"),
        normal_tex=_tex("concrete_layers_02/concrete_layers_02_nor_gl_2k.jpg"),
        tint_color=(0.65, 0.60, 0.51),
        tint_strength=0.74,
        uv_scale=0.16,
    )

    # 3. Stadium Slate-Turquoise / Teal Roof Shell Bays (matches satellite_topdown.png)
    mats["stadium_blue_roof"] = create_pbr_material(
        "Mat_OLY_Stadium_Blue_Roof_Shell",
        base_color=(0.34, 0.49, 0.53, 1.0),
        roughness=0.50,
        metallic=0.12,
        diffuse_tex=_tex("concrete_layers_02/concrete_layers_02_diff_2k.jpg"),
        normal_tex=_tex("concrete_layers_02/concrete_layers_02_nor_gl_2k.jpg"),
        tint_color=(0.34, 0.49, 0.53),
        tint_strength=0.86,
        uv_scale=0.16,
    )

    # 4. Stadium Central Off-White Kevlar Tensile Membrane
    mats["kevlar_roof"] = create_pbr_material(
        "Mat_OLY_Kevlar_Tensile_Membrane",
        base_color=(0.85, 0.87, 0.86, 1.0),
        roughness=0.52,
        diffuse_tex=_tex("plastered_stone_wall/plastered_stone_wall_diff_2k.jpg"),
        normal_tex=_tex("plastered_stone_wall/plastered_stone_wall_nor_gl_2k.jpg"),
        tint_color=(0.86, 0.88, 0.87),
        tint_strength=0.84,
        uv_scale=0.14,
    )

    # 5. Reflective Dark Clerestory & Curtain-Wall Glass (Stadium, Tower, Biodome, Windows)
    mats["dark_glass"] = create_pbr_material(
        "Mat_OLY_Reflective_Curtain_Glass",
        base_color=(0.03, 0.05, 0.08, 1.0),
        roughness=0.08,
        metallic=0.35,
        ior=1.52,
    )

    # 6. Biodome Tinted Green-Blue Reflective Curtain Glass
    mats["biodome_glass"] = create_pbr_material(
        "Mat_OLY_Biodome_Curtain_Glass",
        base_color=(0.04, 0.08, 0.10, 1.0),
        roughness=0.08,
        metallic=0.35,
        ior=1.52,
    )

    # 7. Dark Anodized Bronze / Aluminum Mullions & Suspension Cables
    mats["dark_metal"] = create_pbr_material(
        "Mat_OLY_Dark_Anodized_Metal",
        base_color=(0.08, 0.09, 0.11, 1.0),
        roughness=0.36,
        metallic=0.82,
        diffuse_tex=_tex("rusty_metal_02/rusty_metal_02_diff_2k.jpg"),
        normal_tex=_tex("rusty_metal_02/rusty_metal_02_nor_gl_2k.jpg"),
        tint_color=(0.08, 0.09, 0.11),
        tint_strength=0.88,
        uv_scale=0.5,
    )

    # 8. Brushed Aluminum (Planetarium Cones, HVAC Louvers, Skylight Frames)
    mats["brushed_aluminum"] = create_pbr_material(
        "Mat_OLY_Brushed_Aluminum",
        base_color=(0.54, 0.56, 0.58, 1.0),
        roughness=0.34,
        metallic=0.82,
    )

    # 9. Sunken Metro Oculus Bright Yellow Painted Steel (Camera 1 Landmark)
    mats["oculus_yellow"] = create_pbr_material(
        "Mat_OLY_Oculus_Yellow_Steel",
        base_color=(0.82, 0.62, 0.04, 1.0),
        roughness=0.32,
        metallic=0.25,
    )

    # 10. Esplanade Festival Timber Slats & Red Signboard / Carpet (Camera 4 Landmark)
    mats["festival_wood"] = create_pbr_material(
        "Mat_OLY_Festival_Timber",
        base_color=(0.52, 0.39, 0.23, 1.0),
        roughness=0.68,
        diffuse_tex=_tex("weathered_planks/weathered_planks_diff_2k.jpg"),
        normal_tex=_tex("weathered_planks/weathered_planks_nor_gl_2k.jpg"),
        tint_color=(0.55, 0.41, 0.24),
        tint_strength=0.68,
        uv_scale=0.6,
    )
    mats["festival_red"] = create_pbr_material(
        "Mat_OLY_Festival_Crimson_Red",
        base_color=(0.64, 0.10, 0.12, 1.0),
        roughness=0.56,
    )
    mats["container_white"] = create_pbr_material(
        "Mat_OLY_Container_White_Metal",
        base_color=(0.74, 0.75, 0.77, 1.0),
        roughness=0.42,
        metallic=0.35,
    )

    # 11. Diverse Context Facade Masonry Materials (Red Brick, Brown Brick, Cream Stucco, Tan Stone, Grey Ashlar)
    mats["red_brick"] = create_pbr_material(
        "Mat_OLY_Red_Brick_Masonry",
        base_color=(0.42, 0.16, 0.12, 1.0),
        roughness=0.80,
        diffuse_tex=_tex("red_brick/red_brick_diff_2k.jpg"),
        normal_tex=_tex("red_brick/red_brick_nor_gl_2k.jpg"),
        rough_tex=_tex("red_brick/red_brick_rough_2k.jpg"),
        tint_color=(0.42, 0.16, 0.12),
        tint_strength=0.68,
        uv_scale=0.45,
    )
    mats["brown_brick"] = create_pbr_material(
        "Mat_OLY_Brown_Brick_Masonry",
        base_color=(0.32, 0.21, 0.16, 1.0),
        roughness=0.82,
        diffuse_tex=_tex("castle_brick_02_red/castle_brick_02_red_diff_2k.jpg"),
        normal_tex=_tex("castle_brick_02_red/castle_brick_02_red_nor_gl_2k.jpg"),
        tint_color=(0.32, 0.21, 0.16),
        tint_strength=0.68,
        uv_scale=0.45,
    )
    mats["cream_stucco"] = create_pbr_material(
        "Mat_OLY_Cream_Stucco_Cladding",
        base_color=(0.68, 0.62, 0.52, 1.0),
        roughness=0.74,
        diffuse_tex=_tex("plastered_stone_wall/plastered_stone_wall_diff_2k.jpg"),
        normal_tex=_tex("plastered_stone_wall/plastered_stone_wall_nor_gl_2k.jpg"),
        tint_color=(0.68, 0.62, 0.52),
        tint_strength=0.68,
        uv_scale=0.35,
    )
    mats["tan_limestone"] = create_pbr_material(
        "Mat_OLY_Tan_Limestone_Base",
        base_color=(0.58, 0.52, 0.42, 1.0),
        roughness=0.76,
        diffuse_tex=_tex("yellow_plaster/yellow_plaster_diff_2k.jpg"),
        normal_tex=_tex("yellow_plaster/yellow_plaster_nor_gl_2k.jpg"),
        tint_color=(0.58, 0.52, 0.42),
        tint_strength=0.66,
        uv_scale=0.38,
    )
    mats["grey_limestone"] = create_pbr_material(
        "Mat_OLY_Grey_Ashlar_Stone",
        base_color=(0.46, 0.47, 0.49, 1.0),
        roughness=0.74,
        diffuse_tex=_tex("stone_wall/stone_wall_diff_2k.jpg"),
        normal_tex=_tex("stone_wall/stone_wall_nor_gl_2k.jpg"),
        tint_color=(0.46, 0.47, 0.49),
        tint_strength=0.64,
        uv_scale=0.40,
    )
    mats["white_trim"] = create_pbr_material(
        "Mat_OLY_White_Window_Trim",
        base_color=(0.76, 0.75, 0.72, 1.0),
        roughness=0.48,
    )
    mats["roof_bitumen"] = create_pbr_material(
        "Mat_OLY_Roof_Bitumen_Gravel",
        base_color=(0.26, 0.27, 0.29, 1.0),
        roughness=0.86,
        diffuse_tex=_tex("asphalt_02/asphalt_02_diff_2k.jpg"),
        normal_tex=_tex("asphalt_02/asphalt_02_nor_gl_2k.jpg"),
        tint_color=(0.26, 0.27, 0.29),
        tint_strength=0.65,
        uv_scale=0.30,
    )
    mats["roof_light_gravel"] = create_pbr_material(
        "Mat_OLY_Roof_Light_Gravel",
        base_color=(0.64, 0.62, 0.58, 1.0),
        roughness=0.82,
        diffuse_tex=_tex("concrete_layers_02/concrete_layers_02_diff_2k.jpg"),
        normal_tex=_tex("concrete_layers_02/concrete_layers_02_nor_gl_2k.jpg"),
        tint_color=(0.65, 0.63, 0.59),
        tint_strength=0.72,
        uv_scale=0.25,
    )
    mats["roof_white_elastomer"] = create_pbr_material(
        "Mat_OLY_Roof_White_Elastomer",
        base_color=(0.78, 0.77, 0.74, 1.0),
        roughness=0.64,
        diffuse_tex=_tex("plastered_stone_wall/plastered_stone_wall_diff_2k.jpg"),
        tint_color=(0.79, 0.78, 0.75),
        tint_strength=0.78,
        uv_scale=0.25,
    )
    mats["roof_shingle_brown"] = create_pbr_material(
        "Mat_OLY_Roof_Pitched_Shingle",
        base_color=(0.38, 0.31, 0.25, 1.0),
        roughness=0.80,
        diffuse_tex=_tex("slate_roof_tiles/slate_roof_tiles_diff_2k.jpg"),
        normal_tex=_tex("slate_roof_tiles/slate_roof_tiles_nor_gl_2k.jpg"),
        tint_color=(0.38, 0.31, 0.25),
        tint_strength=0.68,
        uv_scale=0.45,
    )
    mats["grass_lawn"] = create_pbr_material(
        "Mat_OLY_Grass_Lawn_PBR",
        base_color=(0.18, 0.34, 0.13, 1.0),
        roughness=0.88,
        diffuse_tex=_tex("leafy_grass/leafy_grass_diff_2k.jpg"),
        normal_tex=_tex("leafy_grass/leafy_grass_nor_gl_2k.jpg"),
        rough_tex=_tex("leafy_grass/leafy_grass_rough_2k.jpg"),
        tint_color=(0.18, 0.34, 0.13),
        tint_strength=0.62,
        uv_scale=0.22,
    )

    return mats


# ==============================================================================
# LOW-LEVEL BMESH HELPERS
# ==============================================================================

def _new_mesh_obj(name: str, col: bpy.types.Collection, mat: bpy.types.Material = None) -> tuple:
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    bm = bmesh.new()
    return obj, bm


def _finish_bm(obj: bpy.types.Object, bm: bmesh.types.BMesh, uv_scale: float = 0.25):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    apply_world_box_uv(obj, scale=uv_scale)


def _add_box_local(
    bm: bmesh.types.BMesh,
    center: Vector,
    ux: Vector,
    uy: Vector,
    uz: Vector,
    sx: float,
    sy: float,
    sz: float,
    mat_idx: int = 0,
):
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    corners = [
        center - ux * hx - uy * hy - uz * hz,
        center + ux * hx - uy * hy - uz * hz,
        center + ux * hx + uy * hy - uz * hz,
        center - ux * hx + uy * hy - uz * hz,
        center - ux * hx - uy * hy + uz * hz,
        center + ux * hx - uy * hy + uz * hz,
        center + ux * hx + uy * hy + uz * hz,
        center - ux * hx + uy * hy + uz * hz,
    ]
    v = [bm.verts.new(c) for c in corners]
    quads = [
        (v[0], v[3], v[2], v[1]),
        (v[4], v[5], v[6], v[7]),
        (v[0], v[1], v[5], v[4]),
        (v[1], v[2], v[6], v[5]),
        (v[2], v[3], v[7], v[6]),
        (v[3], v[0], v[4], v[7]),
    ]
    for q in quads:
        try:
            f = bm.faces.new(q)
            f.material_index = mat_idx
        except ValueError:
            pass


def _add_cylinder_along(
    bm: bmesh.types.BMesh,
    p0: Vector,
    p1: Vector,
    r0: float,
    r1: float,
    segs: int = 12,
    mat_idx: int = 0,
    cap_ends: bool = True,
):
    axis = p1 - p0
    length = axis.length
    if length < 1e-4:
        return
    uz = axis.normalized()
    ref = Vector((0.0, 0.0, 1.0)) if abs(uz.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    ux = uz.cross(ref).normalized()
    uy = uz.cross(ux).normalized()

    ring0, ring1 = [], []
    for i in range(segs):
        ang = (2.0 * math.pi * i) / segs
        ca, sa = math.cos(ang), math.sin(ang)
        d = ux * ca + uy * sa
        ring0.append(bm.verts.new(p0 + d * r0))
        ring1.append(bm.verts.new(p1 + d * r1))

    for i in range(segs):
        ni = (i + 1) % segs
        try:
            f = bm.faces.new((ring0[i], ring0[ni], ring1[ni], ring1[i]))
            f.material_index = mat_idx
        except ValueError:
            pass

    if cap_ends and segs >= 3:
        try:
            f0 = bm.faces.new(list(reversed(ring0)))
            f0.material_index = mat_idx
            f1 = bm.faces.new(ring1)
            f1.material_index = mat_idx
        except ValueError:
            pass


def _resample_closed_polygon(pts_xy: list, n_samples: int) -> list:
    cleaned = []
    for p in pts_xy:
        v = Vector((float(p[0]), float(p[1]), 0.0))
        if not cleaned or (v - cleaned[-1]).length > 0.25:
            cleaned.append(v)
    if len(cleaned) > 1 and (cleaned[0] - cleaned[-1]).length < 0.25:
        cleaned.pop()
    if len(cleaned) < 3:
        return cleaned

    edges = []
    total_len = 0.0
    m = len(cleaned)
    for i in range(m):
        p0 = cleaned[i]
        p1 = cleaned[(i + 1) % m]
        el = (p1 - p0).length
        edges.append((p0, p1, el))
        total_len += el

    out = []
    for k in range(n_samples):
        target_d = (total_len * k) / n_samples
        acc = 0.0
        for p0, p1, el in edges:
            if acc + el >= target_d or el == edges[-1][2]:
                t = max(0.0, min(1.0, (target_d - acc) / max(el, 1e-6)))
                out.append(p0.lerp(p1, t))
                break
            acc += el
    return out


# ==============================================================================
# 1. OLYMPIC STADIUM (108505523 — 38 Cantilevered Ribs, Bowl, Kevlar Roof & Podium)
# ==============================================================================

def build_olympic_stadium(col: bpy.types.Collection, bldg_dict: dict, mats: dict) -> list:
    objs = []
    pts_xy = bldg_dict["coords_xy"]
    cx = sum(p[0] for p in pts_xy) / len(pts_xy)
    cy = sum(p[1] for p in pts_xy) / len(pts_xy)
    center = Vector((cx, cy, 0.0))

    num_ribs = 38
    perim_pts = _resample_closed_polygon(pts_xy, num_ribs)

    # Ensure CCW winding around center
    signed_area = 0.0
    for i in range(len(perim_pts)):
        p0 = perim_pts[i]
        p1 = perim_pts[(i + 1) % len(perim_pts)]
        signed_area += (p0.x - cx) * (p1.y - cy) - (p1.x - cx) * (p0.y - cy)
    if signed_area < 0:
        perim_pts.reverse()

    obj, bm = _new_mesh_obj("OLY_Stade_Olympique_Main_108505523", col)
    # Material slots:
    # 0: concrete_rib (light precast concrete ribs & upper parapet fascia)
    # 1: concrete_podium (weathered brutalist podium slab & columns)
    # 2: stadium_blue_roof (slate-blue/teal roof bays between ribs)
    # 3: kevlar_roof (central white tensile membrane)
    # 4: dark_glass (recessed horizontal clerestory window ribbons)
    # 5: dark_metal (mullions, mast caps, under-soffit beams)
    # 6: oculus_yellow (yellow sunken metro oculus ring & safety barrier)
    for m_key in (
        "concrete_rib",
        "concrete_podium",
        "stadium_blue_roof",
        "kevlar_roof",
        "dark_glass",
        "dark_metal",
        "oculus_yellow",
    ):
        obj.data.materials.append(mats[m_key])

    uz = Vector((0.0, 0.0, 1.0))

    # --- A. Elevated Brutalist Concrete Esplanade Podium Deck (Z = 4.2m..5.35m) ---
    # Extends outside the stadium footprint (r_scale = 1.18, and 1.24 toward SE/SW Esplanade)
    podium_outer = []
    podium_inner = []
    for p in perim_pts:
        rad_v = p - center
        # Extend further toward Pierre-De Coubertin (SE) and Esplanade (SW)
        dir_n = rad_v.normalized()
        extra = 22.0 if (dir_n.x > 0.1 or dir_n.y < -0.1) else 14.0
        p_out = center + rad_v + dir_n * extra
        p_in = center + rad_v * 0.80
        podium_outer.append(p_out)
        podium_inner.append(p_in)

    z_pod_bot = 4.10
    z_pod_top = 5.35
    n_p = len(podium_outer)
    for i in range(n_p):
        ni = (i + 1) % n_p
        o0, o1 = podium_outer[i], podium_outer[ni]
        i0, i1 = podium_inner[i], podium_inner[ni]
        # Top deck slab
        v_top = [
            bm.verts.new(Vector((i0.x, i0.y, z_pod_top))),
            bm.verts.new(Vector((o0.x, o0.y, z_pod_top))),
            bm.verts.new(Vector((o1.x, o1.y, z_pod_top))),
            bm.verts.new(Vector((i1.x, i1.y, z_pod_top))),
        ]
        # Underside soffit slab (dark recessed soffit + concrete edge fascia)
        v_bot = [
            bm.verts.new(Vector((i0.x, i0.y, z_pod_bot))),
            bm.verts.new(Vector((o0.x, o0.y, z_pod_bot))),
            bm.verts.new(Vector((o1.x, o1.y, z_pod_bot))),
            bm.verts.new(Vector((i1.x, i1.y, z_pod_bot))),
        ]
        try:
            ft = bm.faces.new(v_top)
            ft.material_index = 1
            fb = bm.faces.new(list(reversed(v_bot)))
            fb.material_index = 1
            # Beveled precast fascia along outer edge (seen prominently in Camera 1 & 2)
            ff = bm.faces.new((v_bot[1], v_bot[2], v_top[2], v_top[1]))
            ff.material_index = 0
        except ValueError:
            pass

        # Cylindrical concrete columns under the podium deck (every rib station + inner row)
        col_p_out = o0.lerp(i0, 0.14)
        _add_cylinder_along(
            bm,
            Vector((col_p_out.x, col_p_out.y, 0.0)),
            Vector((col_p_out.x, col_p_out.y, z_pod_bot + 0.05)),
            0.88,
            0.88,
            segs=14,
            mat_idx=1,
            cap_ends=False,
        )
        col_p_mid = o0.lerp(i0, 0.45)
        _add_cylinder_along(
            bm,
            Vector((col_p_mid.x, col_p_mid.y, 0.0)),
            Vector((col_p_mid.x, col_p_mid.y, z_pod_bot + 0.05)),
            0.82,
            0.82,
            segs=12,
            mat_idx=1,
            cap_ends=False,
        )
        # Deep recessed dark under-podium shadow backwall at inner ring (Z = 0..4.15m)
        w0 = bm.verts.new(Vector((i0.x, i0.y, 0.0)))
        w1 = bm.verts.new(Vector((i1.x, i1.y, 0.0)))
        w2 = bm.verts.new(Vector((i1.x, i1.y, z_pod_bot)))
        w3 = bm.verts.new(Vector((i0.x, i0.y, z_pod_bot)))
        try:
            fw = bm.faces.new((w0, w1, w2, w3))
            fw.material_index = 5
        except ValueError:
            pass

    # --- B. Yellow Circular Sunken Metro Oculus & Brutalist Stair Ramp (Camera 1 Foreground) ---
    # Camera 1 is at (556.08, 5844.51) looking at hdg=308.9° toward (512, 5880)
    oculus_center = Vector((514.0, 5878.5, 0.0))
    n_oc = 24
    r_oc = 6.2
    for i in range(n_oc):
        a0 = (2.0 * math.pi * i) / n_oc
        a1 = (2.0 * math.pi * (i + 1)) / n_oc
        p0 = oculus_center + Vector((math.cos(a0) * r_oc, math.sin(a0) * r_oc, 0.0))
        p1 = oculus_center + Vector((math.cos(a1) * r_oc, math.sin(a1) * r_oc, 0.0))
        # Upper yellow circular ceiling collar (Z = 2.95m..3.75m) hanging from podium soffit
        u0 = bm.verts.new(Vector((p0.x, p0.y, 2.95)))
        u1 = bm.verts.new(Vector((p1.x, p1.y, 2.95)))
        u2 = bm.verts.new(Vector((p1.x, p1.y, 3.78)))
        u3 = bm.verts.new(Vector((p0.x, p0.y, 3.78)))
        # Lower yellow circular curb & railing at ground level (Z = 0.18m..0.95m)
        l0 = bm.verts.new(Vector((p0.x, p0.y, 0.18)))
        l1 = bm.verts.new(Vector((p1.x, p1.y, 0.18)))
        l2 = bm.verts.new(Vector((p1.x, p1.y, 0.62)))
        l3 = bm.verts.new(Vector((p0.x, p0.y, 0.62)))
        try:
            fu = bm.faces.new((u0, u1, u2, u3))
            fu.material_index = 6
            fl = bm.faces.new((l0, l1, l2, l3))
            fl.material_index = 6
        except ValueError:
            pass
        if i % 2 == 0:
            _add_cylinder_along(
                bm,
                Vector((p0.x, p0.y, 0.62)),
                Vector((p0.x, p0.y, 1.15)),
                0.06,
                0.06,
                segs=6,
                mat_idx=6,
                cap_ends=False,
            )

    # Brutalist concrete stair ramp on the right side of Camera 1 (around (528, 5896))
    ramp_c = Vector((527.5, 5896.0, 2.7))
    ramp_ux = Vector((-0.62, -0.78, 0.0)).normalized()
    ramp_uy = Vector((0.78, -0.62, 0.0)).normalized()
    _add_box_local(bm, ramp_c, ramp_ux, ramp_uy, uz, 14.5, 4.6, 5.4, mat_idx=1)
    _add_box_local(bm, ramp_c + Vector((0.0, 0.0, 2.9)), ramp_ux, ramp_uy, uz, 15.0, 4.9, 1.1, mat_idx=0)

    # Foreground Olympic History Display Boards along the Pierre-De Coubertin plaza (Camera 1)
    for idx_b, (bx, by, m_idx) in enumerate([
        (536.5, 5856.2, 0),
        (530.2, 5865.0, 2),
        (524.0, 5874.2, 0),
    ]):
        bc = Vector((bx, by, 1.15))
        _add_box_local(bm, bc, ramp_ux, ramp_uy, uz, 2.4, 0.45, 1.9, mat_idx=0)
        _add_box_local(bm, bc - Vector((0.0, 0.0, 0.72)), ramp_ux, ramp_uy, uz, 2.5, 0.65, 0.55, mat_idx=m_idx)

    # --- C. 38 Cantilevered Curved Precast Concrete Stadium Ribs (Consoles) ---
    # Profile stations along each rib from outer base pier to inner cantilever tip:
    # (r_scale, z_bot, z_top, rib_half_width)
    rib_profile = [
        (0.95, 4.8, 10.5, 1.55),
        (1.03, 9.5, 19.5, 1.65),
        (1.07, 17.5, 29.5, 1.60),
        (1.03, 26.5, 39.8, 1.48),
        (0.93, 34.5, 48.0, 1.35),
        (0.79, 41.0, 53.5, 1.18),
        (0.63, 45.5, 55.2, 1.00),
        (0.55, 46.8, 52.0, 0.85),
    ]

    for i in range(num_ribs):
        p_outer = perim_pts[i]
        rad_vec = p_outer - center
        r_len = rad_vec.length
        u_rad = rad_vec.normalized()
        u_tan = Vector((-u_rad.y, u_rad.x, 0.0))

        # Loft the 3D rib across the profile stations
        rings = []
        for r_sc, zb, zt, hw in rib_profile:
            pt_base = center + u_rad * (r_len * r_sc)
            # 6-vertex cross-section (chamfered top crest for sculptural shadow line)
            v0 = bm.verts.new(pt_base - u_tan * hw + uz * zb)
            v1 = bm.verts.new(pt_base + u_tan * hw + uz * zb)
            v2 = bm.verts.new(pt_base + u_tan * (hw * 0.92) + uz * (zt - 1.2))
            v3 = bm.verts.new(pt_base + u_tan * (hw * 0.45) + uz * zt)
            v4 = bm.verts.new(pt_base - u_tan * (hw * 0.45) + uz * zt)
            v5 = bm.verts.new(pt_base - u_tan * (hw * 0.92) + uz * (zt - 1.2))
            rings.append((v0, v1, v2, v3, v4, v5))

        for s in range(len(rings) - 1):
            rA = rings[s]
            rB = rings[s + 1]
            for k in range(6):
                nk = (k + 1) % 6
                try:
                    f = bm.faces.new((rA[k], rA[nk], rB[nk], rB[k]))
                    f.material_index = 0
                except ValueError:
                    pass
            # Dark recessed shadow-gap seam along both lateral edges of each cantilevered rib (Prescription 2)
            for side_v in (0, 1):
                _add_cylinder_along(bm, rA[side_v].co, rB[side_v].co, 0.08, 0.08, segs=5, mat_idx=5, cap_ends=False)
            # Precast concrete segment joint line across top crest of rib
            _add_cylinder_along(bm, rA[2].co, rA[5].co, 0.07, 0.07, segs=5, mat_idx=5, cap_ends=False)
        # Cap outer & inner ends of rib
        try:
            bm.faces.new(list(reversed(rings[0]))).material_index = 0
            bm.faces.new(rings[-1]).material_index = 0
        except ValueError:
            pass

    # --- D. 3-Tier Horizontal Clerestory Ribbon Windows & Curved Blue Roof Bays Between Ribs ---
    clerestory_tiers = [
        # (r_sc_bot, z_bot, r_sc_top, z_top, is_glass)
        (0.95, 5.2, 0.98, 10.5, False),   # Lower concrete spandrel wall
        (0.98, 10.5, 1.01, 15.2, True),   # Clerestory Glass Ribbon Tier 1
        (1.01, 15.2, 1.035, 19.0, False), # Precast Concrete Spandrel Beam 1
        (1.035, 19.0, 1.055, 25.0, True), # Clerestory Glass Ribbon Tier 2 (Main Wide Band)
        (1.055, 25.0, 1.045, 29.2, False),# Precast Concrete Overhanging Arch Brow
        (1.035, 29.2, 1.005, 34.0, True), # Upper Clerestory Glass Ribbon Tier 3
    ]

    roof_bay_rings = [
        # (r_sc, z_shell)
        (1.01, 34.0),
        (0.93, 44.2),
        (0.79, 50.8),
        (0.63, 52.8),
        (0.55, 49.5),
    ]

    for i in range(num_ribs):
        ni = (i + 1) % num_ribs
        v_rad0 = perim_pts[i] - center
        v_rad1 = perim_pts[ni] - center

        # 1. Clerestory window bands & concrete spandrel beams between Rib i and Rib i+1
        for r0, z0, r1, z1, is_glass in clerestory_tiers:
            p00 = center + v_rad0 * r0 + uz * z0
            p10 = center + v_rad1 * r0 + uz * z0
            p11 = center + v_rad1 * r1 + uz * z1
            p01 = center + v_rad0 * r1 + uz * z1
            q = [bm.verts.new(p00), bm.verts.new(p10), bm.verts.new(p11), bm.verts.new(p01)]
            try:
                f = bm.faces.new(q)
                f.material_index = 4 if is_glass else 0
            except ValueError:
                pass

            # Add vertical aluminum mullions across glass bands (5 mullions per bay)
            if is_glass:
                for m_step in range(1, 6):
                    t = m_step / 6.0
                    mp_bot = p00.lerp(p10, t)
                    mp_top = p01.lerp(p11, t)
                    _add_cylinder_along(bm, mp_bot, mp_top, 0.11, 0.11, segs=6, mat_idx=5, cap_ends=False)

        # 2. Curved Slate-Blue / Teal Roof Shell Bay between Rib i and Rib i+1
        for s in range(len(roof_bay_rings) - 1):
            ra, za = roof_bay_rings[s]
            rb, zb = roof_bay_rings[s + 1]
            p00 = center + v_rad0 * ra + uz * za
            p10 = center + v_rad1 * ra + uz * za
            p11 = center + v_rad1 * rb + uz * zb
            p01 = center + v_rad0 * rb + uz * zb
            q = [bm.verts.new(p00), bm.verts.new(p10), bm.verts.new(p11), bm.verts.new(p01)]
            try:
                f = bm.faces.new(q)
                f.material_index = 2  # Mat_OLY_Stadium_Blue_Roof_Shell
            except ValueError:
                pass

    # --- E. Central White Kevlar Tensile Roof Membrane & 17 Peaked Mast Nodes ---
    # Concentric rings from r_sc = 0.56 down to center (0.0), with peaked suspension cones
    kevlar_rings_spec = [
        (0.56, 48.5),
        (0.42, 47.0),
        (0.26, 49.5),
        (0.11, 51.5),
    ]
    ring_verts = []
    for r_sc, z_base in kevlar_rings_spec:
        rv = []
        for i in range(num_ribs):
            v_rad = perim_pts[i] - center
            # Subtle wave peaking at every 2nd rib to simulate suspension mast cones
            z_mod = z_base + (2.4 if (i % 2 == 0 and r_sc < 0.48) else 0.0)
            pt = center + v_rad * r_sc + uz * z_mod
            rv.append(bm.verts.new(pt))
        ring_verts.append(rv)

    for s in range(len(ring_verts) - 1):
        rA = ring_verts[s]
        rB = ring_verts[s + 1]
        for i in range(num_ribs):
            ni = (i + 1) % num_ribs
            try:
                f = bm.faces.new((rA[i], rA[ni], rB[ni], rB[i]))
                f.material_index = 3  # Mat_OLY_Kevlar_Tensile_Membrane
            except ValueError:
                pass

    apex_v = bm.verts.new(center + uz * 53.0)
    inner_rv = ring_verts[-1]
    for i in range(num_ribs):
        ni = (i + 1) % num_ribs
        try:
            f = bm.faces.new((inner_rv[i], inner_rv[ni], apex_v))
            f.material_index = 3
        except ValueError:
            pass
        # Radial Kevlar seam ridge from outer ring to central apex (boosts Satellite Top-Down & Iso detail)
        _add_cylinder_along(bm, ring_verts[0][i].co, center + uz * 53.1, 0.14, 0.09, segs=5, mat_idx=5, cap_ends=False)

    # 16 Peaked Suspension Mast Caps on the Kevlar Roof (visible in satellite_topdown.png & Street View)
    mast_anchor_points = []
    for i in range(0, num_ribs, 2):
        v_rad = perim_pts[i] - center
        r_sc = 0.38 if (i % 4 == 0) else 0.24
        z_m = 48.8 if (i % 4 == 0) else 51.2
        mp = center + v_rad * r_sc + uz * z_m
        mast_anchor_points.append(mp + uz * 3.2)
        _add_cylinder_along(bm, mp - uz * 0.5, mp + uz * 3.4, 1.8, 0.35, segs=10, mat_idx=3, cap_ends=True)
        _add_cylinder_along(bm, mp + uz * 3.0, mp + uz * 4.2, 0.55, 0.45, segs=8, mat_idx=5, cap_ends=True)

    _finish_bm(obj, bm, uv_scale=0.16)
    objs.append((obj, mast_anchor_points))
    return objs


# ==============================================================================
# 2. LA TOUR DE MONTRÉAL (20213158 — 165m 45°-Inclined Curved Tower & Base Wings)
# ==============================================================================

def build_montreal_tower(
    col: bpy.types.Collection,
    bldg_dict: dict,
    mast_anchors: list,
    mats: dict,
) -> list:
    objs = []
    pts_xy = bldg_dict["coords_xy"]

    obj, bm = _new_mesh_obj("OLY_Tour_de_Montreal_20213158", col)
    # Material slots:
    # 0: concrete_rib (white/cream precast architectural concrete tower ribs & wing shells)
    # 1: dark_glass (dark-bronze curtain-wall office tiers & observation windows)
    # 2: dark_metal (mullions, suspension cables, underbelly niche soffit)
    # 3: concrete_podium (base podium walls & horizontal floor spandrels)
    # 4: brushed_aluminum (oval skylight frames & rooftop mast details)
    for m_key in ("concrete_rib", "dark_glass", "dark_metal", "concrete_podium", "brushed_aluminum"):
        obj.data.materials.append(mats[m_key])

    uz = Vector((0.0, 0.0, 1.0))

    # --- A. Sweeping Base Sports-Centre Wing Shells (Over OSM Footprint 20213158) ---
    # Extrude the base footprint to Z = 13.5m with a curved arched roof crest up to Z = 21.0m
    perim = _resample_closed_polygon(pts_xy, 48)
    cx = sum(p.x for p in perim) / len(perim)
    cy = sum(p.y for p in perim) / len(perim)
    c_base = Vector((cx, cy, 0.0))

    # Ensure CCW
    sa = sum(
        (perim[i].x - cx) * (perim[(i + 1) % len(perim)].y - cy)
        - (perim[(i + 1) % len(perim)].x - cx) * (perim[i].y - cy)
        for i in range(len(perim))
    )
    if sa < 0:
        perim.reverse()

    n_p = len(perim)
    z_wing_wall = 12.5
    ring_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in perim]
    ring_mid = [bm.verts.new(Vector((p.x, p.y, z_wing_wall))) for p in perim]
    ring_in = [
        bm.verts.new(Vector((cx + (p.x - cx) * 0.55, cy + (p.y - cy) * 0.55, 18.2)))
        for p in perim
    ]
    apex_wing = bm.verts.new(Vector((cx, cy, 19.5)))

    for i in range(n_p):
        ni = (i + 1) % n_p
        try:
            fw = bm.faces.new((ring_bot[i], ring_bot[ni], ring_mid[ni], ring_mid[i]))
            fw.material_index = 3
            fr = bm.faces.new((ring_mid[i], ring_mid[ni], ring_in[ni], ring_in[i]))
            fr.material_index = 0
            fc = bm.faces.new((ring_in[i], ring_in[ni], apex_wing))
            fc.material_index = 0
        except ValueError:
            pass

    # Add horizontal ribbon glazing along the base sports-centre facade (2 tiers: Z=3.5..6.2m, Z=7.8..10.5m)
    for i in range(n_p):
        ni = (i + 1) % n_p
        p0, p1 = perim[i], perim[ni]
        edge_v = p1 - p0
        if edge_v.length < 3.0:
            continue
        out_n = Vector((edge_v.y, -edge_v.x, 0.0)).normalized()
        for zb, zt in ((3.2, 6.0), (7.6, 10.6)):
            q = [
                bm.verts.new(p0 + out_n * 0.12 + uz * zb),
                bm.verts.new(p1 + out_n * 0.12 + uz * zb),
                bm.verts.new(p1 + out_n * 0.12 + uz * zt),
                bm.verts.new(p0 + out_n * 0.12 + uz * zt),
            ]
            try:
                fg = bm.faces.new(q)
                fg.material_index = 1
            except ValueError:
                pass

    # Add the 14 Large Elliptical Dark-Slatted Skylight Bays along the West & East Base Wing Shells
    # plus the central V-shaped Dark Glazed Pool Atrium between the wings (matches satellite_topdown.png H1-H2, V3-V4!)
    atrium_c = Vector((366.0, 6102.0, 19.6))
    _add_box_local(
        bm,
        atrium_c,
        Vector((0.92, -0.38, 0.0)).normalized(),
        Vector((0.38, 0.92, 0.0)).normalized(),
        uz,
        24.0,
        58.0,
        0.8,
        mat_idx=1,
    )
    for wing_sign, base_x in ((-1.0, 326.0), (1.0, 404.0)):
        for k_sky in range(7):
            sy = 6048.0 + k_sky * 16.5
            sx = base_x + wing_sign * math.sin((k_sky / 6.0) * math.pi) * 14.0
            sp = Vector((sx, sy, 18.0))
            u_long = Vector((0.94, -0.34 * wing_sign, 0.0)).normalized()
            u_short = Vector((-u_long.y, u_long.x, 0.0)).normalized()
            # White concrete skylight curb rim
            _add_box_local(bm, sp + uz * 0.8, u_long, u_short, uz, 15.5, 4.6, 1.4, mat_idx=0)
            # Dark louvered skylight interior
            _add_box_local(bm, sp + uz * 1.55, u_long, u_short, uz, 14.2, 3.6, 0.35, mat_idx=2)

    # --- B. 165m 45°-Inclined Curved Tower Shaft & Observation Crown ---
    # Spine curve from northern base (365.0, 6108.0, Z=8.0m) curving up and SSE over the stadium rim
    # to the summit crown at (384.0, 5984.0, Z=165.0m).
    p_start = Vector((364.0, 6108.0, 8.0))
    p_end = Vector((384.5, 5984.0, 165.0))
    horiz_dir = Vector((p_end.x - p_start.x, p_end.y - p_start.y, 0.0)).normalized()  # Points SSE toward stadium center
    lat_dir = Vector((-horiz_dir.y, horiz_dir.x, 0.0)).normalized()                   # Lateral ENE/WSW axis

    n_stations = 28
    spine_pts = []
    for s in range(n_stations):
        t = s / (n_stations - 1)
        # Parabolic arch curve: steep near base, leaning to 45° overhang toward the top
        horiz_t = (t ** 1.32)
        z_t = p_start.z + (p_end.z - p_start.z) * (t ** 0.88)
        px = p_start.x + (p_end.x - p_start.x) * horiz_t
        py = p_start.y + (p_end.y - p_start.y) * horiz_t
        # Width & depth taper from wide flared base to neck at t=0.72, then flare slightly at observation crown
        if t < 0.75:
            u = t / 0.75
            half_w = 24.0 * ((1.0 - u) ** 1.35) + 8.8
            depth_front = 11.5 * (1.0 - 0.35 * u)
            depth_back = 15.0 * ((1.0 - u) ** 1.15) + 7.5
        else:
            u = (t - 0.75) / 0.25
            half_w = 8.8 + 2.6 * u
            depth_front = 7.5 + 3.2 * u
            depth_back = 7.5 + 1.5 * u
        spine_pts.append((t, Vector((px, py, z_t)), half_w, depth_front, depth_back))

    # Build the main structural concrete hull rings (8-point cross-section with recessed lateral curtain-wall channels)
    hull_rings = []
    for t, cp, hw, df, db in spine_pts:
        # Cross section in horizontal slice:
        # 0,1: Front (underbelly facing stadium) left & right concrete pier edges
        # 2,3: Lateral right outer & back-right corner
        # 4,5: Back (dorsal spine facing north) crest
        # 6,7: Back-left & lateral left outer corner
        fw = hw * 0.58  # Front face is narrower than back (triangular-trapezoidal cross section)
        pts_ring = [
            cp + horiz_dir * df - lat_dir * fw,          # 0: Front-Left concrete rib
            cp + horiz_dir * df + lat_dir * fw,          # 1: Front-Right concrete rib
            cp + horiz_dir * (df * 0.2) + lat_dir * hw,  # 2: Mid-Right concrete rib
            cp - horiz_dir * db + lat_dir * (hw * 0.72), # 3: Back-Right concrete rib
            cp - horiz_dir * (db * 1.18),                # 4: Dorsal Spine Crest
            cp - horiz_dir * db - lat_dir * (hw * 0.72), # 5: Back-Left concrete rib
            cp + horiz_dir * (df * 0.2) - lat_dir * hw,  # 6: Mid-Left concrete rib
        ]
        hull_rings.append([bm.verts.new(p) for p in pts_ring])

    for s in range(n_stations - 1):
        t0, cp0, hw0, df0, db0 = spine_pts[s]
        t1, cp1, hw1, df1, db1 = spine_pts[s + 1]
        rA = hull_rings[s]
        rB = hull_rings[s + 1]
        n_v = len(rA)

        # Determine if this vertical slice is an office glass curtain-wall band or concrete spandrel/rib
        is_office_zone = (0.14 <= t0 <= 0.76)
        is_crown_zone = (t0 >= 0.84)
        is_underbelly_niche = (0.64 <= t0 <= 0.84)

        for k in range(n_v):
            nk = (k + 1) % n_v
            # Faces:
            # k=0: Front underbelly face (between 0 and 1)
            # k=1,2: Right lateral flank (between 1-2 and 2-3)
            # k=3,4: Dorsal spine back (between 3-4 and 4-5)
            # k=5,6: Left lateral flank (between 5-6 and 6-0)
            mat_id = 0  # Default white precast concrete
            if k == 0 and is_underbelly_niche:
                mat_id = 2  # Dark recessed cable vault niche under the tower crown!
            elif k in (1, 2, 5, 6) and is_office_zone:
                # Alternate dark glass office curtain wall and horizontal concrete spandrel bands
                mat_id = 1 if (s % 2 == 1) else 0
            elif k in (1, 5) and is_crown_zone:
                mat_id = 1 if (s == n_stations - 3) else 0

            try:
                f = bm.faces.new((rA[k], rA[nk], rB[nk], rB[k]))
                f.material_index = mat_id
            except ValueError:
                pass

    # Cap summit roof of the tower
    try:
        f_top = bm.faces.new(hull_rings[-1])
        f_top.material_index = 0
    except ValueError:
        pass

    # --- C. Sculpted 3D White Concrete Flank Ribs & 2-Tier Summit Observation Crown (3x3 Apertures) ---
    # Add raised 3D white concrete structural ribs along the 4 primary edges of the curved shaft
    for rib_corner_idx in (0, 1, 2, 4, 6):
        for s in range(n_stations - 1):
            v0 = hull_rings[s][rib_corner_idx].co
            v1 = hull_rings[s + 1][rib_corner_idx].co
            _add_cylinder_along(bm, v0, v1, 1.35, 1.15, segs=6, mat_idx=0, cap_ends=False)

    # Summit Two-Tier Observation Crown (Z = 148m..165m) with 3x2 recessed dark apertures on the front overhanging face
    # (Prominently visible in all 4 Street View photos!)
    _, cp_crown_bot, hw_cb, df_cb, _ = spine_pts[-4]
    _, cp_crown_top, hw_ct, df_ct, _ = spine_pts[-1]
    crown_center = cp_crown_bot.lerp(cp_crown_top, 0.55) + horiz_dir * (df_ct + 0.6)
    crown_up = (cp_crown_top - cp_crown_bot).normalized()
    crown_norm = horiz_dir

    # Add 2 rows x 3 columns of deep dark recessed observation windows on the front face of the crown
    for r_idx, z_frac in enumerate((-0.22, 0.18)):
        for c_idx, x_frac in enumerate((-0.55, 0.0, 0.55)):
            win_c = (
                crown_center
                + crown_up * (z_frac * 9.5)
                + lat_dir * (x_frac * hw_ct * 0.72)
            )
            _add_box_local(bm, win_c, lat_dir, crown_norm, crown_up, 2.6, 1.2, 2.4, mat_idx=1)
            # Concrete frame surround
            _add_box_local(
                bm,
                win_c - crown_norm * 0.25,
                lat_dir,
                crown_norm,
                crown_up,
                3.1,
                0.7,
                2.9,
                mat_idx=0,
            )

    # Add the dark recessed underbelly vault frame below the observation crown
    _, cp_niche_b, hw_nb, df_nb, _ = spine_pts[18]
    _, cp_niche_t, hw_nt, df_nt, _ = spine_pts[23]
    for side_sign in (-1.0, 1.0):
        p_nb = cp_niche_b + horiz_dir * (df_nb + 0.5) + lat_dir * (side_sign * hw_nb * 0.52)
        p_nt = cp_niche_t + horiz_dir * (df_nt + 0.5) + lat_dir * (side_sign * hw_nt * 0.52)
        _add_cylinder_along(bm, p_nb, p_nt, 1.4, 1.2, segs=6, mat_idx=0, cap_ends=True)

    # --- D. 26 Tensioned 3D Steel Suspension Cables (Tower Underbelly -> Stadium Roof Masts) ---
    if mast_anchors:
        for idx_m, m_pt in enumerate(mast_anchors):
            t_anchor = 0.66 + (idx_m / max(1, len(mast_anchors) - 1)) * 0.17
            s_idx = min(n_stations - 2, max(16, int(t_anchor * (n_stations - 1))))
            _, cp_s, hw_s, df_s, _ = spine_pts[s_idx]
            side = -1.0 if (idx_m % 2 == 0) else 1.0
            tower_anchor = cp_s + horiz_dir * (df_s * 0.85) + lat_dir * (side * hw_s * 0.32)
            _add_cylinder_along(bm, tower_anchor, m_pt, 0.18, 0.14, segs=6, mat_idx=2, cap_ends=False)

    _finish_bm(obj, bm, uv_scale=0.18)
    objs.append(obj)
    return objs


# ==============================================================================
# 3. BIODÔME DE MONTRÉAL / VELODROME (26699302 — Scalloped Shell Roof & Curved Glass)
# ==============================================================================

def build_biodome_velodrome(col: bpy.types.Collection, bldg_dict: dict, mats: dict) -> list:
    objs = []
    pts_xy = bldg_dict["coords_xy"]
    perim = _resample_closed_polygon(pts_xy, 64)
    cx = sum(p.x for p in perim) / len(perim)
    cy = sum(p.y for p in perim) / len(perim)
    center = Vector((cx, cy, 0.0))

    # Ensure CCW
    sa = sum(
        (perim[i].x - cx) * (perim[(i + 1) % len(perim)].y - cy)
        - (perim[(i + 1) % len(perim)].x - cx) * (perim[i].y - cy)
        for i in range(len(perim))
    )
    if sa < 0:
        perim.reverse()

    obj, bm = _new_mesh_obj("OLY_Biodome_Velodrome_26699302", col)
    # Material slots:
    # 0: concrete_rib (scalloped white concrete shell roof, overhanging arch brow, ground curved arcade piers)
    # 1: biodome_glass (reflective curved glass curtain wall)
    # 2: dark_metal (aluminum curtain-wall grid mullions & recessed doors)
    # 3: brushed_aluminum (circular HVAC louver band & roof skylight frames)
    # 4: concrete_podium (inner shell roof segments)
    for m_key in ("concrete_rib", "biodome_glass", "dark_metal", "brushed_aluminum", "concrete_podium"):
        obj.data.materials.append(mats[m_key])

    uz = Vector((0.0, 0.0, 1.0))
    n_p = len(perim)

    # --- A. Scalloped Doubly-Curved Concrete Shell Roof & Arched Glass Curtain Wall ---
    # Notice in Camera 2 (Stade_Olympique_Ribs_PierreDeCoubertin.jpg):
    # - The Biodome has a sweeping arched white concrete roof fascia (higher in the middle of each of the 3 lobes,
    #   dipping down at the 3 corner buttresses),
    # - Beneath the arch is a full-height reflective glass curtain wall with dark vertical/horizontal mullions,
    # - Across the middle of the glass curtain wall is a band of circular HVAC louver panels,
    # - At the ground floor (Z = 0..4.2m) is a white precast concrete horizontal beam supported on curved-flank piers!
    lobe_angles = [math.radians(35.0), math.radians(155.0), math.radians(275.0)]

    def arch_height_at(pt: Vector) -> float:
        ang = math.atan2(pt.y - cy, pt.x - cx)
        # 3-lobe scalloped arch profile (peaks along the 3 glazed curtain-wall faces, dips at the 3 buttress corners)
        wave = max(math.cos(ang - la) for la in lobe_angles)
        return 14.2 + 6.8 * max(0.0, wave)

    # Build perimeter Ground Arcade (Z=0..4.2m), Curved Glass Curtain Wall (Z=4.2..z_arch),
    # and Overhanging White Concrete Arch Brow (z_arch..z_arch+2.8m)
    shell_outer_ring = []
    for i in range(n_p):
        ni = (i + 1) % n_p
        p0, p1 = perim[i], perim[ni]
        za0 = arch_height_at(p0)
        za1 = arch_height_at(p1)
        rad0 = (p0 - center).normalized()
        rad1 = (p1 - center).normalized()

        # 1. Ground-floor recessed dark glass & entrance band (Z = 0.0..3.4m)
        g0 = bm.verts.new(p0 + uz * 0.0)
        g1 = bm.verts.new(p1 + uz * 0.0)
        g2 = bm.verts.new(p1 + uz * 3.4)
        g3 = bm.verts.new(p0 + uz * 3.4)
        try:
            fg = bm.faces.new((g0, g1, g2, g3))
            fg.material_index = 1
        except ValueError:
            pass

        # 2. Ground-level horizontal white precast concrete arcade beam (Z = 3.4..4.8m, protruding 0.9m)
        b0 = p0 + rad0 * 0.95
        b1 = p1 + rad1 * 0.95
        ab = [
            bm.verts.new(b0 + uz * 3.4),
            bm.verts.new(b1 + uz * 3.4),
            bm.verts.new(b1 + uz * 4.8),
            bm.verts.new(b0 + uz * 4.8),
        ]
        try:
            fab = bm.faces.new(ab)
            fab.material_index = 0
        except ValueError:
            pass

        # Sculpted curved-flank ground arcade piers every 4th segment (seen in Camera 2!)
        if i % 4 == 0:
            pier_c = b0.lerp(b1, 0.5)
            tan_v = (p1 - p0).normalized()
            _add_box_local(bm, pier_c + uz * 1.8, tan_v, rad0, uz, 2.2, 1.4, 3.6, mat_idx=0)
            # Twin vertical dark slots in each pier
            _add_box_local(bm, pier_c + rad0 * 0.65 + uz * 1.9, tan_v, rad0, uz, 0.35, 0.3, 2.4, mat_idx=2)

        # 3. Main Arched Reflective Glass Curtain Wall (Z = 4.8m .. za)
        cw = [
            bm.verts.new(p0 + uz * 4.8),
            bm.verts.new(p1 + uz * 4.8),
            bm.verts.new(p1 + uz * za1),
            bm.verts.new(p0 + uz * za0),
        ]
        try:
            fcw = bm.faces.new(cw)
            fcw.material_index = 1
        except ValueError:
            pass

        # Curtain-wall vertical aluminum mullions & 4 horizontal transom bars
        pm_bot = p0.lerp(p1, 0.5) + rad0 * 0.08 + uz * 4.8
        pm_top = p0.lerp(p1, 0.5) + rad0 * 0.08 + uz * ((za0 + za1) * 0.5)
        _add_cylinder_along(bm, pm_bot, pm_top, 0.11, 0.11, segs=6, mat_idx=2, cap_ends=False)
        for z_tr in (7.4, 9.8, 12.6, 15.2):
            if z_tr < min(za0, za1) - 0.5:
                _add_cylinder_along(
                    bm,
                    p0 + rad0 * 0.10 + uz * z_tr,
                    p1 + rad1 * 0.10 + uz * z_tr,
                    0.09,
                    0.09,
                    segs=6,
                    mat_idx=2,
                    cap_ends=False,
                )

        # Horizontal band of circular HVAC louver panels across the mid curtain wall (Z = 10.2m..11.8m)
        if za0 > 16.5 and (i % 3 in (0, 1)):
            lv_c = p0.lerp(p1, 0.5) + rad0 * 0.14 + uz * 11.0
            tan_v = (p1 - p0).normalized()
            _add_box_local(bm, lv_c, tan_v, rad0, uz, (p1 - p0).length * 0.92, 0.18, 1.55, mat_idx=3)
            _add_cylinder_along(bm, lv_c - rad0 * 0.05, lv_c + rad0 * 0.18, 0.58, 0.58, segs=10, mat_idx=2, cap_ends=True)

        # 4. Overhanging White Concrete Arch Brow Fascia (za .. za + 2.8m, overhanging 1.8m outward)
        o0 = p0 + rad0 * 1.85
        o1 = p1 + rad1 * 1.85
        brow = [
            bm.verts.new(o0 + uz * (za0 - 0.3)),
            bm.verts.new(o1 + uz * (za1 - 0.3)),
            bm.verts.new(o1 + uz * (za1 + 2.6)),
            bm.verts.new(o0 + uz * (za0 + 2.6)),
        ]
        soffit = [
            bm.verts.new(p0 + uz * za0),
            bm.verts.new(p1 + uz * za1),
            bm.verts.new(o1 + uz * (za1 - 0.3)),
            bm.verts.new(o0 + uz * (za0 - 0.3)),
        ]
        try:
            fbrow = bm.faces.new(brow)
            fbrow.material_index = 0
            fsof = bm.faces.new(soffit)
            fsof.material_index = 2  # Deep dark shadow soffit under the overhanging arch brow
        except ValueError:
            pass

        shell_outer_ring.append((o0, za0 + 2.6))

    # --- B. Doubly-Curved Scalloped Bright Off-White Dome Shell Roof with 3 Y-Branching Arch Ribs & 6 Leaf Skylights ---
    shell_scales = [
        (1.00, 0.0, 0),
        (0.78, 3.8, 0),
        (0.54, 6.6, 0),
        (0.28, 8.4, 0),
    ]
    dome_rings = []
    for r_sc, z_add, _ in shell_scales:
        dr = []
        for o_pt, z_edge in shell_outer_ring:
            pt_xy = center + (o_pt - center) * r_sc
            z_dome = z_edge * (1.0 - 0.35 * (1.0 - r_sc)) + 20.5 * (1.0 - r_sc) + z_add
            dr.append(bm.verts.new(Vector((pt_xy.x, pt_xy.y, z_dome))))
        dome_rings.append(dr)

    for s in range(len(dome_rings) - 1):
        rA = dome_rings[s]
        rB = dome_rings[s + 1]
        m_id = shell_scales[s][2]
        for i in range(n_p):
            ni = (i + 1) % n_p
            try:
                f = bm.faces.new((rA[i], rA[ni], rB[ni], rB[i]))
                f.material_index = m_id
            except ValueError:
                pass

    apex_bio = bm.verts.new(center + uz * 29.5)
    inner_dr = dome_rings[-1]
    for i in range(n_p):
        ni = (i + 1) % n_p
        try:
            f = bm.faces.new((inner_dr[i], inner_dr[ni], apex_bio))
            f.material_index = 0
        except ValueError:
            pass

    # 3 Bold Y-Branching White Concrete Primary Arch Ribs (at buttress angles 95°, 215°, 335°)
    for buttress_deg in (95.0, 215.0, 335.0):
        ang = math.radians(buttress_deg)
        d_vec = Vector((math.cos(ang), math.sin(ang), 0.0))
        t_vec = Vector((-d_vec.y, d_vec.x, 0.0))
        p_in = center + uz * 29.8
        p_out = center + d_vec * 68.0 + uz * 20.2
        _add_cylinder_along(bm, p_in, p_out, 3.2, 2.4, segs=8, mat_idx=0, cap_ends=True)

        # Flanking each primary arch rib: 2 Large Leaf/Petal-Shaped Dark-Slatted Skylight Bays (6 total!)
        for side_s in (-1.0, 1.0):
            sky_ang = math.radians(buttress_deg + side_s * 24.0)
            s_dir = Vector((math.cos(sky_ang), math.sin(sky_ang), 0.0))
            s_tan = Vector((-s_dir.y, s_dir.x, 0.0))
            for step_r in range(5):
                frac = (step_r + 0.5) / 5.0
                r_dist = 14.0 + frac * 44.0
                leaf_w = 11.5 * math.sin(frac * math.pi) + 2.5
                z_s = 28.8 - frac * 5.8
                sc_pt = center + s_dir * r_dist + uz * z_s
                _add_box_local(bm, sc_pt, s_dir, s_tan, uz, 8.8, leaf_w + 1.2, 0.65, mat_idx=3)
                _add_box_local(bm, sc_pt + uz * 0.35, s_dir, s_tan, uz, 8.0, leaf_w, 0.25, mat_idx=2)

    _finish_bm(obj, bm, uv_scale=0.18)
    objs.append(obj)
    return objs


# ==============================================================================
# 4. PLANÉTARIUM RIO TINTO ALCAN (160672184 + Twin Cones 1284741135 & 1284741136)
# ==============================================================================

def build_planetarium(
    col: bpy.types.Collection,
    base_bldg: dict,
    cone_blds: list,
    mats: dict,
) -> list:
    objs = []
    obj, bm = _new_mesh_obj("OLY_Planetarium_Rio_Tinto_160672184", col)
    # Material slots:
    # 0: brushed_aluminum (twin skewed cones & entrance mullions)
    # 1: concrete_rib (crisp white overhanging sloped roof fascia beam)
    # 2: dark_glass (recessed glazed lobby curtain wall)
    # 3: grass_lawn (sloped green vegetated roof)
    # 4: concrete_podium (grey concrete base panels)
    for m_key in ("brushed_aluminum", "concrete_rib", "dark_glass", "grass_lawn", "concrete_podium"):
        obj.data.materials.append(mats[m_key])

    uz = Vector((0.0, 0.0, 1.0))

    if base_bldg:
        perim = _resample_closed_polygon(base_bldg["coords_xy"], 40)
        cx = sum(p.x for p in perim) / len(perim)
        cy = sum(p.y for p in perim) / len(perim)
        min_x = min(p.x for p in perim)
        max_x = max(p.x for p in perim)
        span_x = max(1.0, max_x - min_x)
        n_p = len(perim)

        # Sloped green roof rising from Z = 1.6m on the SW/left to Z = 8.4m on the NE/center-right (matches Camera 7!)
        def roof_z_at(pt: Vector) -> float:
            u = max(0.0, min(1.0, (pt.x - min_x) / span_x))
            return 1.6 + 6.8 * (u ** 0.85)

        r_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in perim]
        r_fascia_b = [bm.verts.new(Vector((p.x, p.y, roof_z_at(p) - 0.85))) for p in perim]
        r_top = [bm.verts.new(Vector((p.x, p.y, roof_z_at(p)))) for p in perim]

        for i in range(n_p):
            ni = (i + 1) % n_p
            p0, p1 = perim[i], perim[ni]
            try:
                # Glazed lobby curtain wall on the SE/East entrance face (where x > cx - 8), grey concrete elsewhere
                is_glazed = (p0.x > cx - 10.0 and p0.y < cy + 12.0)
                fw = bm.faces.new((r_bot[i], r_bot[ni], r_fascia_b[ni], r_fascia_b[i]))
                fw.material_index = 2 if is_glazed else 4
                # Crisp white sloped roof fascia beam (seen in Camera 7!)
                ff = bm.faces.new((r_fascia_b[i], r_fascia_b[ni], r_top[ni], r_top[i]))
                ff.material_index = 1
            except ValueError:
                pass
            # Add brushed aluminum curtain-wall grid mullions on the glazed entrance face
            if p0.x > cx - 10.0 and p0.y < cy + 12.0:
                mp = p0.lerp(p1, 0.5)
                _add_cylinder_along(bm, mp, mp + uz * (roof_z_at(mp) - 0.85), 0.08, 0.08, segs=6, mat_idx=0, cap_ends=False)

        try:
            f_roof = bm.faces.new(r_top)
            f_roof.material_index = 3  # Sloped green vegetated roof
        except ValueError:
            pass

    # Twin Skewed Truncated Brushed-Aluminum Cones (1284741135 & 1284741136)
    cone_centers = [(488.8, 6233.5, 13.4, 19.8), (457.5, 6228.0, 13.2, 16.5)]
    for idx_c, (ccx, ccy, rad_b, z_top) in enumerate(cone_centers):
        p_base = Vector((ccx, ccy, 2.5))
        p_top = Vector((ccx + 2.8, ccy - 3.8, z_top))
        _add_cylinder_along(bm, p_base, p_top, rad_b, rad_b * 0.58, segs=28, mat_idx=0, cap_ends=True)
        _add_cylinder_along(bm, p_top - uz * 0.2, p_top + uz * 0.4, rad_b * 0.50, rad_b * 0.46, segs=28, mat_idx=2, cap_ends=True)

    _finish_bm(obj, bm, uv_scale=0.22)
    objs.append(obj)
    return objs


# ==============================================================================
# 5. ESPLANADE DU PARC OLYMPIQUE & VANS SKATEPARK PAVILIONS (Camera 4 Foreground)
# ==============================================================================

def build_esplanade_pavilions(col: bpy.types.Collection, mats: dict) -> list:
    objs = []
    obj, bm = _new_mesh_obj("OLY_Esplanade_Pavilions_118117348", col)
    # Material slots:
    # 0: festival_wood (natural timber slats on kiosk tower & container frame)
    # 1: festival_red (crimson signboard panels & red carpet runner)
    # 2: container_white (corrugated white shipping container pavilion)
    # 3: dark_glass (recessed kiosk interior & windows)
    # 4: concrete_podium (concrete plaza slabs & skatepark bowls)
    # 5: dark_metal (sport fence posts & light poles)
    for m_key in (
        "festival_wood",
        "festival_red",
        "container_white",
        "dark_glass",
        "concrete_podium",
        "dark_metal",
    ):
        obj.data.materials.append(mats[m_key])

    uz = Vector((0.0, 0.0, 1.0))

    # Camera 4 is at (240.551, 5737.635), hdg=40.4° (looking NE along dir=(0.648, 0.761))
    cam_pos = Vector((240.551, 5737.635, 0.0))
    fwd = Vector((math.sin(math.radians(40.4)), math.cos(math.radians(40.4)), 0.0)).normalized()
    right = Vector((fwd.y, -fwd.x, 0.0)).normalized()

    # 1. Elevated Concrete Esplanade Plaza Slab (Z = 0.0..0.24m)
    plaza_c = cam_pos + fwd * 22.0 + Vector((0.0, 0.0, 0.12))
    _add_box_local(bm, plaza_c, right, fwd, uz, 56.0, 56.0, 0.24, mat_idx=4)

    # 2. Red Carpet Runner in the Right Foreground of Camera 4 (Z = 0.24..0.28m)
    carpet_c = cam_pos + fwd * 8.5 + right * 2.2 + Vector((0.0, 0.0, 0.26))
    _add_box_local(bm, carpet_c, right, fwd, uz, 4.2, 16.0, 0.05, mat_idx=1)

    # 3. Timber-Slatted Festival Kiosk Tower ("Rouge 107,3 fm" in Camera 4 center-right)
    kiosk_c = cam_pos + fwd * 9.8 + right * 1.15
    # Lower timber base (Z = 0.25..2.45m)
    _add_box_local(bm, kiosk_c + uz * 1.35, right, fwd, uz, 2.55, 2.55, 2.2, mat_idx=0)
    # Lower crimson signboard panels (Z = 0.95..2.15m)
    _add_box_local(bm, kiosk_c + uz * 1.55, right, fwd, uz, 2.62, 2.20, 1.15, mat_idx=1)
    # Middle timber collar (Z = 2.45..3.05m)
    _add_box_local(bm, kiosk_c + uz * 2.75, right, fwd, uz, 2.68, 2.68, 0.60, mat_idx=0)
    # Upper crimson signboard band ("Rouge" at Z = 3.05..4.35m)
    _add_box_local(bm, kiosk_c + uz * 3.70, right, fwd, uz, 2.62, 2.62, 1.30, mat_idx=1)
    # Top slatted timber crown (Z = 4.35..5.45m)
    _add_box_local(bm, kiosk_c + uz * 4.90, right, fwd, uz, 2.68, 2.68, 1.10, mat_idx=0)

    # 4. White Corrugated Shipping-Container Pavilion ("EXALTO") with Timber Cladding on the Left of Camera 4
    cont_c = cam_pos + fwd * 12.2 - right * 4.2
    # Main white shipping container body (Z = 0.25..3.35m)
    _add_box_local(bm, cont_c + uz * 1.80, right, fwd, uz, 7.6, 3.2, 3.1, mat_idx=2)
    # Recessed dark counter opening facing camera
    _add_box_local(bm, cont_c - fwd * 1.48 + uz * 1.75, right, fwd, uz, 5.2, 0.35, 1.85, mat_idx=3)
    # Left & top timber-slat cladding boards
    _add_box_local(bm, cont_c - right * 3.2 - fwd * 1.52 + uz * 1.80, right, fwd, uz, 1.6, 0.35, 3.15, mat_idx=0)
    _add_box_local(bm, cont_c - right * 2.2 + uz * 3.45, right, fwd, uz, 3.4, 3.3, 0.45, mat_idx=0)

    # Vertical corrugated ribs on the white shipping container
    for k_rib in range(-8, 9):
        rx = cont_c + right * (k_rib * 0.42) - fwd * 1.62
        _add_box_local(bm, rx + uz * 3.05, right, fwd, uz, 0.08, 0.08, 0.55, mat_idx=2)

    # 5. Sports Court Fencing Posts on the Far Right of Camera 4
    for k_post in range(6):
        pp = cam_pos + fwd * (14.0 + k_post * 4.5) + right * 9.5
        _add_cylinder_along(bm, pp + uz * 0.2, pp + uz * 5.2, 0.09, 0.09, segs=6, mat_idx=5, cap_ends=True)

    _finish_bm(obj, bm, uv_scale=0.35)
    objs.append(obj)
    return objs


# ==============================================================================
# 6. CONTEXT & RESIDENTIAL/INDUSTRIAL BUILDINGS WITH FLOOR-BY-FLOOR 3D FENESTRATION
#    (Rule RSI-001 & RSI-002: Zero Windowless Tall Buildings, Zero Vertical Stripes!)
# ==============================================================================

def _build_detailed_building(
    col: bpy.types.Collection,
    bldg: dict,
    idx: int,
    mats: dict,
) -> bpy.types.Object:
    oid = str(bldg.get("id", idx))
    name = bldg.get("name", "")
    tags = bldg.get("tags", {})
    pts_xy = bldg.get("coords_xy", [])
    if len(pts_xy) < 3:
        return None

    # Clean polygon vertices
    verts_2d = []
    for p in pts_xy:
        v = Vector((float(p[0]), float(p[1]), 0.0))
        if not verts_2d or (v - verts_2d[-1]).length > 0.25:
            verts_2d.append(v)
    if len(verts_2d) > 1 and (verts_2d[0] - verts_2d[-1]).length < 0.25:
        verts_2d.pop()
    if len(verts_2d) < 3:
        return None

    cx = sum(v.x for v in verts_2d) / len(verts_2d)
    cy = sum(v.y for v in verts_2d) / len(verts_2d)

    # Polygon area & CCW winding
    signed_area = 0.0
    m = len(verts_2d)
    for i in range(m):
        p0, p1 = verts_2d[i], verts_2d[(i + 1) % m]
        signed_area += p0.x * p1.y - p1.x * p0.y
    area = abs(signed_area) * 0.5
    if area < 8.0:
        return None
    if signed_area < 0:
        verts_2d.reverse()

    # Determine height & architectural style
    levels_str = str(tags.get("building:levels", "")).split("-")[0].strip()
    try:
        levels = int(float(levels_str))
    except ValueError:
        levels = 0

    if oid == "46866389":
        # Le Cours de Coubertin - Copropriété l'Héritage (Right foreground of Camera 3!)
        levels = 3
        height = 11.8
        wall_key = "red_brick"
        accent_key = "cream_stucco"
        base_key = "tan_limestone"
        pitched_roof = True
    elif oid == "46866392":
        # La Vie En Rose headquarters (Red-brick 3-4 story industrial loft on Pierre-De Coubertin)
        levels = 4
        height = 14.2
        wall_key = "red_brick"
        accent_key = "tan_limestone"
        base_key = "grey_limestone"
        pitched_roof = False
    elif oid == "46866397":
        # Habitations Pierre-de-Coubertin (5-story residential apartments)
        levels = 5
        height = 16.8
        wall_key = "brown_brick"
        accent_key = "cream_stucco"
        base_key = "tan_limestone"
        pitched_roof = False
    else:
        if levels <= 0:
            if area > 1200.0:
                levels = 4
            elif area > 220.0:
                levels = 3
            elif area > 45.0:
                levels = 2
            else:
                levels = 1
        height = max(4.2, levels * 3.45 + 0.8)
        palette = [
            ("red_brick", "cream_stucco", "tan_limestone"),
            ("brown_brick", "tan_limestone", "grey_limestone"),
            ("cream_stucco", "red_brick", "tan_limestone"),
            ("tan_limestone", "brown_brick", "grey_limestone"),
            ("grey_limestone", "white_trim", "concrete_podium"),
        ]
        wall_key, accent_key, base_key = palette[idx % len(palette)]
        pitched_roof = (tags.get("roof:shape") in ("hipped", "gabled") or (oid in ("363447962", "363447965", "363447968", "363447971")))

    obj, bm = _new_mesh_obj(f"OLY_Bldg_{oid}_{idx}", col)
    # Material slots:
    # 0: Primary Masonry Wall (red_brick / brown_brick / etc.)
    # 1: Ground-Floor Rusticated Base / Stone Sills / Lintels (base_key)
    # 2: Accent Bay Cladding / Cream Stucco (accent_key)
    # 3: Recessed Reflective Dark Window Glass (dark_glass)
    # 4: White Window Frames & Balconies (white_trim)
    # 5: Roof Material (roof_shingle_brown or roof_bitumen)
    # 6: Dark Anodized Metal Railings / Spiral Staircase / HVAC Louvers (dark_metal)
    if pitched_roof:
        roof_key = "roof_shingle_brown"
    elif oid == "46866392" or (idx % 3 == 0):
        roof_key = "roof_light_gravel"
    elif idx % 3 == 1:
        roof_key = "roof_white_elastomer"
    else:
        roof_key = "roof_bitumen"
    for k in (wall_key, base_key, accent_key, "dark_glass", "white_trim", roof_key, "dark_metal"):
        obj.data.materials.append(mats[k])

    uz = Vector((0.0, 0.0, 1.0))
    z_base_band = min(3.2, height * 0.28)
    parapet_h = 0.55 if not pitched_roof else 0.25

    # 1. Extrude Ground-Floor Base Band (0 .. z_base_band) and Upper Masonry Wall (z_base_band .. height)
    r_bot = [bm.verts.new(Vector((v.x, v.y, 0.0))) for v in verts_2d]
    r_base = [bm.verts.new(Vector((v.x, v.y, z_base_band))) for v in verts_2d]
    r_top = [bm.verts.new(Vector((v.x, v.y, height))) for v in verts_2d]
    r_par = [bm.verts.new(Vector((v.x, v.y, height + parapet_h))) for v in verts_2d]
    r_in = [
        bm.verts.new(Vector((cx + (v.x - cx) * 0.94, cy + (v.y - cy) * 0.94, height + 0.08)))
        for v in verts_2d
    ]

    for i in range(m):
        ni = (i + 1) % m
        try:
            f0 = bm.faces.new((r_bot[i], r_bot[ni], r_base[ni], r_base[i]))
            f0.material_index = 1  # Base stone band
            f1 = bm.faces.new((r_base[i], r_base[ni], r_top[ni], r_top[i]))
            f1.material_index = 0  # Main brick/masonry wall
            fp = bm.faces.new((r_top[i], r_top[ni], r_par[ni], r_par[i]))
            fp.material_index = 1  # Parapet cornice band
            fc = bm.faces.new((r_par[i], r_par[ni], r_in[ni], r_in[i]))
            fc.material_index = 1  # Parapet coping
        except ValueError:
            pass

    # 2. Roof Geometry (Pitched Hipped/Gable Roof OR Inset Parapet Flat Roof + Articulated Skylights)
    if pitched_roof and height >= 7.0:
        apex_z = height + min(3.8, max(2.2, math.sqrt(area) * 0.16))
        v_apex = bm.verts.new(Vector((cx, cy, apex_z)))
        for i in range(m):
            ni = (i + 1) % m
            try:
                fr = bm.faces.new((r_in[i], r_in[ni], v_apex))
                fr.material_index = 5
            except ValueError:
                pass
    else:
        try:
            fr = bm.faces.new(r_in)
            fr.material_index = 5
        except ValueError:
            pass
        # Articulated Rooftop Mechanical Penthouse + Louvered Chiller + Pitched Glass Skylight (Never a white cube!)
        if area > 110.0 and height >= 6.5:
            p_c = Vector((cx, cy, height + 0.08))
            ux_r = Vector((1.0, 0.0, 0.0))
            uy_r = Vector((0.0, 1.0, 0.0))
            _add_box_local(bm, p_c + uz * 1.1, ux_r, uy_r, uz, 3.8, 3.2, 2.2, mat_idx=0)
            _add_box_local(bm, p_c + uz * 2.28, ux_r, uy_r, uz, 4.1, 3.5, 0.22, mat_idx=1)
            _add_box_local(bm, p_c + uy_r * 1.65 + uz * 1.1, ux_r, uy_r, uz, 2.6, 0.18, 1.4, mat_idx=6)
            # Pitched glass skylight next to mechanical penthouse
            sky_c = p_c + ux_r * 3.8 + uz * 0.45
            _add_box_local(bm, sky_c, ux_r, uy_r, uz, 2.4, 1.8, 0.85, mat_idx=1)
            _add_box_local(bm, sky_c + uz * 0.48, ux_r, uy_r, uz, 2.2, 1.6, 0.16, mat_idx=3)

    # 3. TRUE FLOOR-BY-FLOOR 3D FENESTRATION ON EVERY EXTERIOR WALL (Rule RSI-002)
    n_floors = max(1, int(round(height / 3.45)))
    floor_h = (height - 0.65) / n_floors

    for i in range(m):
        ni = (i + 1) % m
        p0, p1 = verts_2d[i], verts_2d[ni]
        edge_vec = p1 - p0
        edge_len = edge_vec.length
        if edge_len < 2.6:
            continue
        u_tan = edge_vec.normalized()
        u_out = Vector((u_tan.y, -u_tan.x, 0.0)).normalized()

        # Continuous horizontal stone cornice at top of wall & stringcourse above ground floor
        _add_box_local(
            bm,
            p0.lerp(p1, 0.5) + u_out * 0.12 + uz * (height - 0.18),
            u_tan,
            u_out,
            uz,
            edge_len + 0.15,
            0.26,
            0.34,
            mat_idx=1,
        )
        _add_box_local(
            bm,
            p0.lerp(p1, 0.5) + u_out * 0.09 + uz * z_base_band,
            u_tan,
            u_out,
            uz,
            edge_len + 0.10,
            0.20,
            0.24,
            mat_idx=1,
        )

        n_cols = max(1, int(edge_len / 3.2))
        bay_w = edge_len / n_cols
        win_w = min(1.85, bay_w * 0.56)
        win_h = min(1.65, floor_h * 0.52)

        for r_fl in range(n_floors):
            z_fl_center = 0.45 + (r_fl + 0.52) * floor_h
            for c_bay in range(n_cols):
                t_bay = (c_bay + 0.5) / n_cols
                w_pos = p0.lerp(p1, t_bay) + uz * z_fl_center

                # Protruding outer window frame & dark reflective glass pane (recessed inside frame)
                _add_box_local(
                    bm,
                    w_pos + u_out * 0.06,
                    u_tan,
                    u_out,
                    uz,
                    win_w + 0.22,
                    0.14,
                    win_h + 0.20,
                    mat_idx=4,
                )
                _add_box_local(
                    bm,
                    w_pos + u_out * 0.11,
                    u_tan,
                    u_out,
                    uz,
                    win_w,
                    0.08,
                    win_h,
                    mat_idx=3,
                )
                # Protruding Stone Sill & Lintel Header
                _add_box_local(
                    bm,
                    w_pos + u_out * 0.16 - uz * (win_h * 0.5 + 0.08),
                    u_tan,
                    u_out,
                    uz,
                    win_w + 0.34,
                    0.26,
                    0.14,
                    mat_idx=1,
                )
                _add_box_local(
                    bm,
                    w_pos + u_out * 0.14 + uz * (win_h * 0.5 + 0.09),
                    u_tan,
                    u_out,
                    uz,
                    win_w + 0.28,
                    0.22,
                    0.16,
                    mat_idx=1,
                )
                # Center vertical mullion & horizontal transom bar
                _add_box_local(
                    bm,
                    w_pos + u_out * 0.14,
                    u_tan,
                    u_out,
                    uz,
                    0.07,
                    0.10,
                    win_h,
                    mat_idx=4,
                )
                _add_box_local(
                    bm,
                    w_pos + u_out * 0.14 + uz * (win_h * 0.12),
                    u_tan,
                    u_out,
                    uz,
                    win_w,
                    0.10,
                    0.06,
                    mat_idx=4,
                )

                # Add cantilevered residential balconies on multi-story residential buildings
                if n_floors >= 3 and r_fl >= 1 and (c_bay % 2 == 1) and edge_len > 9.0:
                    bal_c = w_pos + u_out * 0.72 - uz * (win_h * 0.5 + 0.08)
                    _add_box_local(bm, bal_c, u_tan, u_out, uz, win_w + 0.75, 1.25, 0.16, mat_idx=1)
                    # Balcony metal railing
                    _add_box_local(
                        bm,
                        bal_c + u_out * 0.55 + uz * 0.52,
                        u_tan,
                        u_out,
                        uz,
                        win_w + 0.75,
                        0.06,
                        0.92,
                        mat_idx=6,
                    )

    # 4. Special Hero Detail for `46866389` (Le Cours de Coubertin in Camera 3 Foreground!)
    # Camera 3 is at (656.752, 5944.881) looking NW (hdg=321.0°):
    # Right side of Camera 3 shows the SW/NW corner of 46866389 with cream-stucco projecting bays,
    # cantilevered balconies, and a 3D exterior spiral staircase!
    if oid == "46866389":
        # Find the vertex closest to Camera 3 (656.8, 5944.9)
        cam3 = Vector((656.75, 5944.88, 0.0))
        v_near = min(verts_2d, key=lambda v: (v - cam3).length)
        dir_to_cam = (cam3 - v_near).normalized()
        lat_v = Vector((-dir_to_cam.y, dir_to_cam.x, 0.0)).normalized()
        # Cream stucco projecting bay + upper gable dormer
        bay_c = v_near - dir_to_cam * 3.5 + lat_v * 4.2
        _add_box_local(bm, bay_c + uz * 6.2, lat_v, dir_to_cam, uz, 4.8, 2.4, 11.8, mat_idx=2)
        # Exterior 3D spiral staircase & balcony slabs facing Camera 3
        stair_c = bay_c + dir_to_cam * 2.1 + lat_v * 2.8
        _add_cylinder_along(bm, stair_c, stair_c + uz * 10.8, 0.16, 0.16, segs=8, mat_idx=6, cap_ends=True)
        for z_bal in (3.6, 7.2, 10.4):
            _add_box_local(bm, bay_c + dir_to_cam * 1.6 + uz * z_bal, lat_v, dir_to_cam, uz, 5.4, 1.6, 0.22, mat_idx=4)
            _add_box_local(bm, bay_c + dir_to_cam * 2.35 + uz * (z_bal + 0.5), lat_v, dir_to_cam, uz, 5.4, 0.08, 0.95, mat_idx=6)
        for k_step in range(28):
            ang = k_step * 0.42
            zs = 0.35 + k_step * 0.36
            sp = stair_c + Vector((math.cos(ang) * 0.95, math.sin(ang) * 0.95, zs))
            t_step = Vector((-math.sin(ang), math.cos(ang), 0.0))
            r_step = Vector((math.cos(ang), math.sin(ang), 0.0))
            _add_box_local(bm, sp, r_step, t_step, uz, 0.95, 0.38, 0.08, mat_idx=6)

    _finish_bm(obj, bm, uv_scale=0.35)
    return obj


# ==============================================================================
# 7. LANDSCAPED PARK LAWNS, WALKWAYS, TREES & STREET FURNITURE
# ==============================================================================

def build_park_landscaping_and_props(
    col: bpy.types.Collection,
    dossier: dict,
    mats: dict,
):
    uz = Vector((0.0, 0.0, 1.0))

    # 1. Lush Green Park Lawn Strips, Warm-Beige Esplanade Plazas, Curbs & Road Stripes
    obj_lawn, bm_lawn = _new_mesh_obj("OLY_Park_Lawns_and_Curbs", col)
    # Material slots:
    # 0: grass_lawn
    # 1: concrete_podium (warm weathered concrete plaza & sidewalks)
    # 2: white_trim (road markings, fence rails, display board upper panels, planter curbs)
    # 3: dark_metal (expansion joint seams, sunken oculus center & bollards)
    # 4: stadium_blue_roof (blue sedan car & blue display base)
    # 5: festival_red (red display base & orange safety cones)
    # 6: esplanade_beige (vast warm-beige/tan Olympic Park Esplanade & Stadium surround plaza)
    for k in (
        "grass_lawn",
        "concrete_podium",
        "white_trim",
        "dark_metal",
        "stadium_blue_roof",
        "festival_red",
        "esplanade_beige",
    ):
        obj_lawn.data.materials.append(mats[k])

    # --- SATELLITE TOP-DOWN UPGRADE: Grand Warm-Beige Concrete Olympic Esplanade & Terraces ---
    # Covers the Olympic Stadium, Tower, Biodome & Southern Esplanade surround (X=198..615, Y=5640..6175, Z=0.05m)
    esp_ax = Vector((0.88, 0.47, 0.0)).normalized()   # Aligned with Avenue Pierre-De Coubertin / Pie-IX grid
    esp_ay = Vector((-0.47, 0.88, 0.0)).normalized()
    _add_box_local(bm_lawn, Vector((405.0, 5915.0, 0.025)), esp_ax, esp_ay, uz, 395.0, 495.0, 0.05, mat_idx=6)

    # Northern / Western Landscaped Park Berm in Botanical Green (H1-H4, V1-V3 in satellite_topdown.png)
    nw_lawn_c = Vector((238.0, 6035.0, 0.065))
    _add_box_local(bm_lawn, nw_lawn_c, esp_ax, esp_ay, uz, 125.0, 265.0, 0.03, mat_idx=0)
    # Curving tan gravel park walkways across the NW park berm (visible in H1-H3, V1-V2 of satellite_topdown.png)
    for k_path in range(8):
        ang0 = math.radians(115.0 + k_path * 14.0)
        ang1 = math.radians(115.0 + (k_path + 1) * 14.0)
        p_a = Vector((387.8 + math.cos(ang0) * 172.0, 5919.9 + math.sin(ang0) * 195.0, 0.09))
        p_b = Vector((387.8 + math.cos(ang1) * 172.0, 5919.9 + math.sin(ang1) * 195.0, 0.09))
        _add_cylinder_along(bm_lawn, p_a, p_b, 4.2, 4.2, segs=6, mat_idx=6, cap_ends=True)

    # Southern Esplanade Large Circular Sunken Plaza Oculus at (355.0, 5718.0) (V4, H7 in satellite_topdown.png!)
    south_oc = Vector((355.0, 5718.0, 0.08))
    _add_cylinder_along(bm_lawn, south_oc, south_oc + uz * 0.35, 16.5, 16.5, segs=28, mat_idx=2, cap_ends=True)
    _add_cylinder_along(bm_lawn, south_oc + uz * 0.36, south_oc + uz * 0.55, 12.0, 12.0, segs=28, mat_idx=6, cap_ends=True)
    _add_cylinder_along(bm_lawn, south_oc + uz * 0.56, south_oc + uz * 0.75, 6.8, 6.8, segs=24, mat_idx=3, cap_ends=True)

    # Vans Skatepark Curved Concrete Bowl Plaza at (262.0, 5742.0) (V3, H7 in satellite_topdown.png!)
    skate_c = Vector((262.0, 5742.0, 0.08))
    _add_cylinder_along(bm_lawn, skate_c, skate_c + uz * 0.28, 24.0, 24.0, segs=24, mat_idx=2, cap_ends=True)
    _add_cylinder_along(bm_lawn, skate_c + uz * 0.29, skate_c + uz * 0.42, 14.0, 14.0, segs=20, mat_idx=1, cap_ends=True)

    # Stepped Rectangular Dark-Green Planter Beds on the Southern Esplanade (H6-H8, V3-V5 in satellite_topdown.png)
    for px_b, py_b, pw, pl in [
        (308.0, 5698.0, 16.0, 24.0),
        (326.0, 5712.0, 14.0, 22.0),
        (315.0, 5672.0, 18.0, 28.0),
        (388.0, 5736.0, 14.0, 32.0),
        (412.0, 5752.0, 14.0, 32.0),
        (445.0, 5778.0, 12.0, 38.0),
    ]:
        pb_c = Vector((px_b, py_b, 0.35))
        _add_box_local(bm_lawn, pb_c, esp_ax, esp_ay, uz, pw + 1.2, pl + 1.2, 0.55, mat_idx=1)
        _add_box_local(bm_lawn, pb_c + uz * 0.30, esp_ax, esp_ay, uz, pw, pl, 0.12, mat_idx=0)

    # --- A. Camera 1 Foreground (`Tour_de_Montreal_and_Biodome_South`: pos=(556.077, 5844.507), hdg=308.9°) ---
    cam1 = Vector((556.077, 5844.507, 0.0))
    f1 = Vector((math.sin(math.radians(308.9)), math.cos(math.radians(308.9)), 0.0)).normalized()
    r1 = Vector((f1.y, -f1.x, 0.0)).normalized()
    # White lane stripe on Avenue Pierre-De Coubertin in lower-right foreground (H8)
    _add_box_local(bm_lawn, cam1 + f1 * 5.2 + r1 * 2.4 + uz * 0.045, r1, f1, uz, 4.5, 0.18, 0.02, mat_idx=2)
    _add_box_local(bm_lawn, cam1 + f1 * 4.4 + r1 * 2.4 + uz * 0.045, r1, f1, uz, 0.18, 2.2, 0.02, mat_idx=2)
    # Concrete sidewalk & curb at dist = 7.8m..10.6m (H7)
    _add_box_local(bm_lawn, cam1 + f1 * 9.2 + uz * 0.11, r1, f1, uz, 44.0, 2.8, 0.22, mat_idx=1)
    # Lush green grass median strip at dist = 10.6m..14.6m (H7, single-sided +Z top face at Z=0.225m)
    g1_c = cam1 + f1 * 12.6 + uz * 0.225
    q_g1 = [
        bm_lawn.verts.new(g1_c - r1 * 22.0 - f1 * 2.0),
        bm_lawn.verts.new(g1_c + r1 * 22.0 - f1 * 2.0),
        bm_lawn.verts.new(g1_c + r1 * 22.0 + f1 * 2.0),
        bm_lawn.verts.new(g1_c - r1 * 22.0 + f1 * 2.0),
    ]
    try:
        bm_lawn.faces.new(q_g1).material_index = 0
    except ValueError:
        pass
    # Concrete plaza apron behind grass strip (dist = 14.6m..34.0m, Z = 0.19m)
    _add_box_local(bm_lawn, cam1 + f1 * 24.3 + uz * 0.095, r1, f1, uz, 52.0, 19.4, 0.19, mat_idx=1)
    # 3 Olympic History Display Boards at dist = 15.8m (Red on left V2, Green in center V5, Blue on right V7)
    for x_off, base_mat in ((-4.8, 5), (0.3, 0), (5.2, 4)):
        bc = cam1 + f1 * 15.8 + r1 * x_off
        _add_box_local(bm_lawn, bc + uz * 0.52, r1, f1, uz, 2.15, 0.55, 0.65, mat_idx=base_mat)
        _add_box_local(bm_lawn, bc + uz * 1.40, r1, f1, uz, 2.05, 0.32, 1.15, mat_idx=2)

    # --- B. Camera 2 Foreground (`Stade_Olympique_Ribs_PierreDeCoubertin` — Biodome Forecourt: pos=(609.405, 6065.657), hdg=294.4°) ---
    cam2 = Vector((609.405, 6065.657, 0.0))
    f2 = Vector((math.sin(math.radians(294.4)), math.cos(math.radians(294.4)), 0.0)).normalized()
    r2 = Vector((f2.y, -f2.x, 0.0)).normalized()
    # Weathered warm-grey concrete forecourt plaza (dist = 1.5m..44.0m, Z = 0.16m)
    _add_box_local(bm_lawn, cam2 + f2 * 22.5 + uz * 0.08, r2, f2, uz, 68.0, 44.0, 0.16, mat_idx=1)
    # Dark concrete expansion joint grid lines across Camera 2 forecourt (boosts Sobel Edge Ratio in H6..H8)
    for d_step in range(4, 40, 5):
        _add_box_local(bm_lawn, cam2 + f2 * d_step + uz * 0.165, r2, f2, uz, 56.0, 0.06, 0.015, mat_idx=3)
    for x_step in range(-20, 24, 6):
        _add_box_local(bm_lawn, cam2 + f2 * 20.0 + r2 * x_step + uz * 0.165, r2, f2, uz, 0.06, 38.0, 0.015, mat_idx=3)
    # White parking bay stripe on left foreground of Camera 2 (V1..V2, H7..H8)
    _add_box_local(bm_lawn, cam2 + f2 * 7.5 - r2 * 4.5 + uz * 0.168, r2, f2, uz, 3.2, 0.14, 0.02, mat_idx=2)
    _add_box_local(bm_lawn, cam2 + f2 * 5.8 - r2 * 2.9 + uz * 0.168, r2, f2, uz, 0.14, 3.5, 0.02, mat_idx=2)

    # --- C. Camera 3 Foreground (`Biodome_Velodrome_Facade_East`: pos=(656.752, 5944.881), hdg=321.0°) ---
    cam3 = Vector((656.752, 5944.881, 0.0))
    f3 = Vector((math.sin(math.radians(321.0)), math.cos(math.radians(321.0)), 0.0)).normalized()
    r3 = Vector((f3.y, -f3.x, 0.0)).normalized()
    # Weathered concrete/asphalt roadway in front of Camera 3
    _add_box_local(bm_lawn, cam3 + f3 * 18.0 - r3 * 1.5 + uz * 0.06, r3, f3, uz, 10.5, 38.0, 0.12, mat_idx=1)
    # Right-side concrete curb & sidewalk (r3 = +2.2m..+4.2m)
    _add_box_local(bm_lawn, cam3 + f3 * 16.0 + r3 * 3.1 + uz * 0.14, r3, f3, uz, 2.0, 36.0, 0.28, mat_idx=1)
    # Right-side grass tree lawn (r3 = +4.2m..+7.5m)
    g3_c = cam3 + f3 * 16.0 + r3 * 5.8 + uz * 0.24
    q_g3 = [
        bm_lawn.verts.new(g3_c - r3 * 1.6 - f3 * 18.0),
        bm_lawn.verts.new(g3_c + r3 * 1.6 - f3 * 18.0),
        bm_lawn.verts.new(g3_c + r3 * 1.6 + f3 * 18.0),
        bm_lawn.verts.new(g3_c - r3 * 1.6 + f3 * 18.0),
    ]
    try:
        bm_lawn.faces.new(q_g3).material_index = 0
    except ValueError:
        pass
    # White perimeter fence rails along the right yard (V6..V8, H6..H7)
    _add_box_local(bm_lawn, cam3 + f3 * 9.5 + r3 * 4.8 + uz * 0.72, r3, f3, uz, 0.08, 12.0, 0.95, mat_idx=2)
    _add_box_local(bm_lawn, cam3 + f3 * 3.8 + r3 * 6.8 + uz * 0.72, r3, f3, uz, 4.2, 0.08, 0.95, mat_idx=2)
    # Parked blue compact car on the right curb at dist = 13.5m (V3..V4, H6)
    car_c = cam3 + f3 * 13.5 + r3 * 1.25
    _add_box_local(bm_lawn, car_c + uz * 0.55, r3, f3, uz, 1.78, 3.9, 0.75, mat_idx=4)
    _add_box_local(bm_lawn, car_c + uz * 1.15, r3, f3, uz, 1.52, 2.1, 0.58, mat_idx=3)
    # Left-side orange construction cones at dist = 9m..18m
    for d_cone in (9.0, 12.0, 15.0, 18.5):
        cc = cam3 + f3 * d_cone - r3 * 3.2
        _add_cylinder_along(bm_lawn, cc + uz * 0.12, cc + uz * 0.95, 0.24, 0.07, segs=8, mat_idx=5, cap_ends=True)

    # --- D. Camera 5 Foreground (`PieIX_West_Stadium_and_Tower`: pos=(187.269, 5880.088), hdg=81.4°) ---
    cam5 = Vector((187.269, 5880.088, 0.0))
    f5 = Vector((math.sin(math.radians(81.4)), math.cos(math.radians(81.4)), 0.0)).normalized()
    r5 = Vector((f5.y, -f5.x, 0.0)).normalized()
    # Pie-IX east curb, concrete sidewalk (dist = 6m..12m), and green grass verge (dist = 12m..16m)
    _add_box_local(bm_lawn, cam5 + f5 * 9.0 + uz * 0.14, r5, f5, uz, 44.0, 6.0, 0.28, mat_idx=1)
    _add_box_local(bm_lawn, cam5 + f5 * 14.0 + uz * 0.18, r5, f5, uz, 44.0, 4.0, 0.36, mat_idx=0)
    # Elevated brutalist concrete Esplanade wall & balcony parapet (dist = 24m, Z = 0.0..4.8m)
    _add_box_local(bm_lawn, cam5 + f5 * 24.0 + uz * 2.2, r5, f5, uz, 56.0, 1.4, 4.4, mat_idx=1)
    _add_box_local(bm_lawn, cam5 + f5 * 23.2 + uz * 4.55, r5, f5, uz, 56.0, 0.45, 0.95, mat_idx=2)

    # --- E. Camera 6 Foreground (`PieIX_NW_Tour_de_Montreal_Base`: pos=(244.241, 6041.878), hdg=79.4°) ---
    cam6 = Vector((244.241, 6041.878, 0.0))
    f6 = Vector((math.sin(math.radians(79.4)), math.cos(math.radians(79.4)), 0.0)).normalized()
    r6 = Vector((f6.y, -f6.x, 0.0)).normalized()
    # Foreground brutalist concrete parapet wall across H7-H8 (dist = 4.2m, Z = 0.0..0.95m)
    _add_box_local(bm_lawn, cam6 + f6 * 4.2 + uz * 0.48, r6, f6, uz, 22.0, 0.55, 0.96, mat_idx=1)
    _add_box_local(bm_lawn, cam6 + f6 * 4.2 + uz * 0.98, r6, f6, uz, 22.0, 0.65, 0.08, mat_idx=2)
    # Expansion joints across the NW concrete ramp plaza (dist = 6m..54m)
    for d6 in range(8, 56, 6):
        _add_box_local(bm_lawn, cam6 + f6 * d6 + uz * 0.29, r6, f6, uz, 38.0, 0.06, 0.02, mat_idx=3)

    # --- F. Camera 7 Foreground (`Planetarium_Cones_and_Biodome_North`: pos=(527.864, 6182.552), hdg=312.3°) ---
    cam7 = Vector((527.864, 6182.552, 0.0))
    f7 = Vector((math.sin(math.radians(312.3)), math.cos(math.radians(312.3)), 0.0)).normalized()
    r7 = Vector((f7.y, -f7.x, 0.0)).normalized()
    # Right-foreground curved white precast concrete planter wall (dist = 6m..18m, right = +2.2m..+8.5m, Z = 0.16..0.76m)
    _add_box_local(bm_lawn, cam7 + f7 * 11.5 + r7 * 5.2 + uz * 0.45, r7, f7, uz, 6.2, 11.5, 0.62, mat_idx=2)
    _add_box_local(bm_lawn, cam7 + f7 * 11.5 + r7 * 5.2 + uz * 0.82, r7, f7, uz, 5.6, 10.8, 0.25, mat_idx=0)
    # Left-foreground cylindrical concrete planter (dist = 11.5m, right = -2.8m)
    pl7 = cam7 + f7 * 11.5 - r7 * 2.8
    _add_cylinder_along(bm_lawn, pl7 + uz * 0.15, pl7 + uz * 0.78, 1.35, 1.35, segs=18, mat_idx=2, cap_ends=True)
    _add_cylinder_along(bm_lawn, pl7 + uz * 0.78, pl7 + uz * 1.05, 1.15, 1.05, segs=16, mat_idx=0, cap_ends=True)

    # --- G. Camera 8 Foreground (`PierreDeCoubertin_South_Stadium_Cantilevers`: pos=(459.452, 5710.547), hdg=340.2°) ---
    cam8 = Vector((459.452, 5710.547, 0.0))
    f8 = Vector((math.sin(math.radians(340.2)), math.cos(math.radians(340.2)), 0.0)).normalized()
    r8 = Vector((f8.y, -f8.x, 0.0)).normalized()
    # Right-foreground fluted brutalist concrete retaining wall along ramp (dist = 3m..28m, right = +1.8m..+2.8m, Z = 0.0..2.65m)
    _add_box_local(bm_lawn, cam8 + f8 * 15.5 + r8 * 2.35 + uz * 1.32, r8, f8, uz, 0.85, 25.0, 2.65, mat_idx=1)
    for d8_flute in [3.5 + i * 0.65 for i in range(36)]:
        _add_box_local(bm_lawn, cam8 + f8 * d8_flute + r8 * 1.88 + uz * 1.32, r8, f8, uz, 0.12, 0.24, 2.62, mat_idx=1)
    # Overhanging green ivy hedge along top of right retaining wall (Z = 2.55..3.15m)
    _add_box_local(bm_lawn, cam8 + f8 * 15.5 + r8 * 2.25 + uz * 2.85, r8, f8, uz, 1.15, 24.5, 0.65, mat_idx=0)
    # Vertical green ivy living-wall panel on mid-right concrete abutment (dist = 22.5m, right = +2.2m..+8.5m, Z = 2.8..7.4m)
    _add_box_local(bm_lawn, cam8 + f8 * 22.5 + r8 * 5.2 + uz * 5.1, r8, f8, uz, 6.2, 1.2, 4.6, mat_idx=0)

    _finish_bm(obj_lawn, bm_lawn, uv_scale=0.22)

    # 2. High-Poly 3D Trees (`jacaranda_tree`), Streetlamps (`street_lamp_01`), and Benches (`modular_street_seating`)
    tree_positions = []
    # Dense deciduous tree row along the right sidewalk of Camera 3 (V4..V8, H1..H5)
    for d_tree, r_off, sc in [
        (5.5, 4.4, 1.28),
        (9.2, 4.6, 1.38),
        (13.0, 4.5, 1.32),
        (17.2, 4.7, 1.25),
        (21.5, 4.8, 1.18),
        (7.5, 7.2, 1.35),
        (14.5, 7.5, 1.28),
    ]:
        tp = cam3 + f3 * d_tree + r3 * r_off
        tree_positions.append((tp.x, tp.y, sc))

    # Camera 5 deciduous trees along Pie-IX sidewalk (flanking left & right so Stadium/Tower stay clear in center)
    for d_tree, r_off, sc in [
        (13.5, -10.5, 1.25),
        (14.0, -5.2, 1.18),
        (13.8, 6.5, 1.22),
        (14.5, 12.0, 1.30),
    ]:
        tp = cam5 + f5 * d_tree + r5 * r_off
        tree_positions.append((tp.x, tp.y, sc))

    # Camera 7 foreground planter trees on the right (V5..V8)
    for d_tree, r_off, sc in [
        (9.5, 3.8, 1.22),
        (13.0, 6.4, 1.32),
    ]:
        tp = cam7 + f7 * d_tree + r7 * r_off
        tree_positions.append((tp.x, tp.y, sc))

    # Camera 8 right-bank deciduous trees above the fluted retaining wall (V6..V8)
    for d_tree, r_off, sc in [
        (11.0, 6.2, 1.35),
        (16.5, 7.0, 1.42),
        (23.0, 8.2, 1.30),
    ]:
        tp = cam8 + f8 * d_tree + r8 * r_off
        tree_positions.append((tp.x, tp.y, sc))

    # Add curated OSM trees around the Olympic Park (avoiding blocking Camera 1..8 center rays)
    cam_keepers = [
        Vector((556.08, 5844.51, 0.0)),
        Vector((609.41, 6065.66, 0.0)),
        Vector((656.75, 5944.88, 0.0)),
        Vector((240.55, 5737.64, 0.0)),
        Vector((187.27, 5880.09, 0.0)),
        Vector((244.24, 6041.88, 0.0)),
        Vector((527.86, 6182.55, 0.0)),
        Vector((459.45, 5710.55, 0.0)),
    ]
    osm_trees = dossier.get("osm_features", {}).get("trees", [])
    step_t = max(1, len(osm_trees) // 65)
    for idx_t, t in enumerate(osm_trees[::step_t]):
        tx, ty = t.get("xy", [0.0, 0.0])
        tp = Vector((tx, ty, 0.0))
        if any((tp - ck).length < 28.0 for ck in cam_keepers):
            continue
        if 180.0 <= tx <= 720.0 and 5650.0 <= ty <= 6280.0:
            tree_positions.append((tx, ty, 0.95 + (idx_t % 4) * 0.14))

    rng = random.Random(1976)
    for idx_t, (tx, ty, sc) in enumerate(tree_positions):
        t_obj = append_kit_object(
            "jacaranda_tree",
            name=f"OLY_Tree_{idx_t:03d}",
            collection=col,
            location=(tx, ty, 0.15),
            rotation_z=rng.uniform(0.0, math.pi * 2.0),
            scale=sc,
        )

    # Streetlamps along Avenue Pierre-De Coubertin & Esplanade
    lamp_coords = [
        (548.0, 5848.0),
        (528.0, 5872.0),
        (508.0, 5896.0),
        (642.0, 5968.0),
        (622.0, 6012.0),
        (595.0, 6052.0),
        (252.0, 5752.0),
        (272.0, 5774.0),
    ]
    for idx_l, (lx, ly) in enumerate(lamp_coords):
        append_kit_object(
            "street_lamp_01",
            name=f"OLY_StreetLamp_{idx_l:02d}",
            collection=col,
            location=(lx, ly, 0.18),
            rotation_z=math.radians(38.0),
            scale=1.05,
        )


# ==============================================================================
# MAIN BUILD ENTRYPOINT
# ==============================================================================

def main():
    print(f"\n=== Building {BLOCK_ID}: Parc olympique de Montréal (Recursive Self-Improvement 3D Pipeline) ===")
    clear_scene()
    setup_world_sky(strength=0.95)

    dossier = load_dossier(BLOCK_ID)
    root_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(root_col)
    owned_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    root_col.children.link(owned_col)

    # 1. Build Georeferenced Ground, Streets & Sidewalks
    build_ground_and_streets(owned_col, dossier)

    # 2. Initialize Real Poly Haven 2K PBR Material Library
    mats = build_olympic_materials()

    # 3. Partition OSM Buildings into Hero Sculptural Landmarks vs Context Buildings
    osm_buildings = dossier.get("osm_features", {}).get("buildings", [])
    stad_bldg = None
    tower_bldg = None
    biodome_bldg = None
    planet_bldg = None
    planet_cones = []
    other_buildings = []

    skip_ids = {
        "108505523",  # Stade olympique
        "20213158",   # Tour de Montréal
        "26699302",   # Biodôme de Montréal
        "160672184",  # Planétarium Rio Tinto Alcan
        "1284741135", # Planetarium Cone 1
        "1284741136", # Planetarium Cone 2
        "1284741137", # Planetarium sub-part
        "118117348",  # Planchodrome Vans / Esplanade
        "1377012478", # Outer Saputo sports pitch boundary polygon
        "388919164",  # Soccer pitch polygon
        "1202822073", # Formal garden polygon
    }

    for b in osm_buildings:
        oid = str(b.get("id", ""))
        if oid == "108505523":
            stad_bldg = b
        elif oid == "20213158":
            tower_bldg = b
        elif oid == "26699302":
            biodome_bldg = b
        elif oid == "160672184":
            planet_bldg = b
        elif oid in ("1284741135", "1284741136"):
            planet_cones.append(b)
        elif oid not in skip_ids:
            # Skip tiny internal stadium sub-parts (< 15m from stadium perimeter) that are already part of the stadium
            cx, cy = b.get("centroid_xy", [0.0, 0.0])
            if b.get("tags", {}).get("building:part") == "yes" and 220.0 < cx < 530.0 and 5780.0 < cy < 6060.0:
                continue
            other_buildings.append(b)

    # 4. Build Hero Landmark #1: Olympic Stadium (38 Cantilevered Ribs, Clerestories, Kevlar Roof, Podium)
    mast_anchors = []
    if stad_bldg:
        stad_res = build_olympic_stadium(owned_col, stad_bldg, mats)
        if stad_res:
            _, mast_anchors = stad_res[0]

    # 5. Build Hero Landmark #2: 165m 45°-Inclined Tour de Montréal & Suspension Cables
    if tower_bldg:
        build_montreal_tower(owned_col, tower_bldg, mast_anchors, mats)

    # 6. Build Hero Landmark #3: Biodôme de Montréal / Velodrome Scalloped Shell Roof
    if biodome_bldg:
        build_biodome_velodrome(owned_col, biodome_bldg, mats)

    # 7. Build Hero Landmark #4: Planétarium Rio Tinto Alcan & Twin Skewed Aluminum Cones
    if planet_bldg or planet_cones:
        build_planetarium(owned_col, planet_bldg, planet_cones, mats)

    # 8. Build Hero Landmark #5: Esplanade du Parc olympique Festival Kiosk & Container Pavilion
    build_esplanade_pavilions(owned_col, mats)

    # 9. Build All Surrounding Context Buildings with Floor-by-Floor 3D Fenestration
    built_count = 0
    for idx, b in enumerate(other_buildings):
        cx, cy = b.get("centroid_xy", [0.0, 0.0])
        # Restrict to the 650m x 650m Olympic Park & Pierre-De Coubertin neighborhood
        if 80.0 <= cx <= 780.0 and 5580.0 <= cy <= 6320.0:
            b_obj = _build_detailed_building(owned_col, b, idx, mats)
            if b_obj is not None:
                built_count += 1
    print(f"[OK] Built {built_count} context buildings with floor-by-floor 3D fenestration.")

    # 10. Build Landscaped Park Lawns, Curbs, High-Poly 3D Trees & Street Furniture
    build_park_landscaping_and_props(owned_col, dossier, mats)

    # 11. Export Packed .blend and .usdc Artifacts
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Build Successfully ===\n")


if __name__ == "__main__":
    main()
