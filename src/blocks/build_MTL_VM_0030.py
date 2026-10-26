"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0030
(Cité du Multimédia, 21e Arrondissement & Rue Wellington / Rue King Industrial Loft Corridor)

Iteration 1 Complete Photorealistic Remodel:
1. Full World-Space Box/Planar UV Generation (`assign_world_uvs`) on all BMesh geometry so all
   2K Poly Haven PBR image textures (water, leafy grass, limestone, brick, concrete pavers,
   asphalt) render with crisp 2K surface detail and zero stretched/black UV artifacts.
2. Exact Concave Polygon Triangulation (`mathutils.geometry.tessellate_polygon`) and
   Edge-Normal Insetting so complex L/U-shaped buildings (`766574909`, `1083559150`, `455546170`,
   `378269133`, `402069143`, `650010119`, `340068506`, `47175244`) have crisp courtyards and zero bridging.
3. 4 Rooftop Swimming Pools (cyan-blue pools on white sun decks + mechanical penthouses) matching
   `satellite_topdown.png` (`650010119` top-right, `1083559150` upper-left, `378269133` lower-left,
   `402069143` lower-center) plus the central green courtyard park (`Z = +0.195m`) and Grand Plaza.
4. Exact Camera-Matched Hero Architectural Articulation across all 4 Street View viewpoints:
   - `Cite_Multimedia_Main_Portal` (`[-141.928, -570.423]`, heading `172.4°`):
     4-story warm orange-red industrial brick flatiron loft (`47175244`, Montreal Stencil) with
     segmental arched windows, dual dark garage doors in grey stone base, and black steel exterior
     fire-escape stairs on the right wall, plus 10-story modern white/glass condo (`766574909`) in background left.
   - `Rue_Wellington_Industrial_Canyon` (`[-149.647, -661.439]`, heading `148.0°`):
     Pedestrian garden promenade (`Square / Passage du 21e Arrondissement`) with paved walkway,
     low concrete curb walls, lamp post, lush green hydrangea/shrub beds (`Z = +0.195m`),
     white precast/glass/dark-brick facade of `1083559150` on the left, and `455546170` on the far right.
   - `Corner_King_and_Queen` (`[-81.555, -556.758]`, heading `196.1°`) &
     `Rue_Duke_Tech_Corridor` (`[-86.961, -547.171]`, heading `193.3°`):
     3-story red-brick base with cantilevered dark-blue/grey glass curtain-wall upper cube on left
     (`499597178`, Avantscène Mobilier), 6-story heritage red-brick loft with 2-story grey cut-limestone
     base (`340068506`, Place Saint Paul), 8-to-10-story white precast & glass loft (`766574909`),
     and 5-story red-brick industrial warehouse (`340069043` / right side of Rue Saint-Paul Ouest),
     complete with parked cars, fire hydrant, traffic sign post, and green/orange bollard.
5. 100% Real High-Poly Poly Haven 3D Botanical Trees (`jacaranda_tree`, `searsia_burchellii`,
   `tree_small_02`, `shrub_02`), `street_lamp_01`, and `painted_wooden_bench` / `modular_street_seating`
   appended via `kit.append_polyhaven_model()` — zero primitive lollipop trees.
6. Micro-stepped `z_eps` across all road, sidewalk, and curb prisms so Cycles renders zero black
   coplanar Z-fighting faces, and `bpy.ops.file.pack_all()` called before saving `.blend`.
"""

import os
import sys
import json
import math
import shutil
import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.geometry import tessellate_polygon

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0030"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")
SNAPSHOT_PATH = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.usdc")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
HDRI_PATH = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT_PATH), exist_ok=True)


# ---------------------------------------------------------------------------
# 1. PBR MATERIAL PALETTE WITH TINTED 2K POLY HAVEN TEXTURES
# ---------------------------------------------------------------------------
def make_tinted_pbr_mat(name, asset_id, tint_rgb=(1.0, 1.0, 1.0), tint_fac=0.65,
                        uv_scale=1.0, roughness_val=0.75, metallic=0.0, bump_strength=0.65):
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = (tint_rgb[0], tint_rgb[1], tint_rgb[2], 1.0)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness_val
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (uv_scale, uv_scale, uv_scale)
    links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])

    diff_path = kit._find_polyhaven_map(asset_id, ["Diffuse_2k", "diff_2k", "col_2k"])
    rough_path = kit._find_polyhaven_map(asset_id, ["Roughness_2k", "Rough_2k", "rough_2k"])
    nor_path = kit._find_polyhaven_map(asset_id, ["nor_gl_2k", "nor_2k", "normal_2k"])

    if diff_path and os.path.isfile(diff_path):
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = kit.get_or_load_image(diff_path, "sRGB")
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])

        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MIX"
        mix.inputs["Factor"].default_value = tint_fac
        mix.inputs["B"].default_value = (tint_rgb[0], tint_rgb[1], tint_rgb[2], 1.0)
        links.new(tex_d.outputs["Color"], mix.inputs["A"])
        links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (tint_rgb[0], tint_rgb[1], tint_rgb[2], 1.0)

    if rough_path and os.path.isfile(rough_path):
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = kit.get_or_load_image(rough_path, "Non-Color")
        links.new(mapping.outputs["Vector"], tex_r.inputs["Vector"])
        links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])

    if nor_path and os.path.isfile(nor_path):
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = kit.get_or_load_image(nor_path, "Non-Color")
        links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = bump_strength
        links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def create_block_palette():
    palette = kit.create_montreal_material_palette()

    # Dedicated tuned materials matching MTL-VM-0030 Ground Truth photos & satellite
    palette["Mat_Stencil_WarmOrangeBrick"] = make_tinted_pbr_mat(
        "Mat_Stencil_WarmOrangeBrick", "brick_wall_04",
        tint_rgb=(0.68, 0.28, 0.16), tint_fac=0.58, uv_scale=1.35, roughness_val=0.74, bump_strength=0.65
    )
    palette["Mat_Avantscene_RedBrick"] = make_tinted_pbr_mat(
        "Mat_Avantscene_RedBrick", "castle_brick_02_red",
        tint_rgb=(0.62, 0.25, 0.18), tint_fac=0.58, uv_scale=1.3, roughness_val=0.75, bump_strength=0.65
    )
    palette["Mat_PlaceStPaul_Brick"] = make_tinted_pbr_mat(
        "Mat_PlaceStPaul_Brick", "brick_wall_04",
        tint_rgb=(0.58, 0.27, 0.20), tint_fac=0.55, uv_scale=1.3, roughness_val=0.76, bump_strength=0.60
    )
    palette["Mat_Rusticated_GreyLimestone"] = make_tinted_pbr_mat(
        "Mat_Rusticated_GreyLimestone", "stone_brick_wall_001",
        tint_rgb=(0.56, 0.55, 0.52), tint_fac=0.58, uv_scale=1.1, roughness_val=0.74, bump_strength=0.65
    )
    palette["Mat_White_Precast_Panel"] = make_tinted_pbr_mat(
        "Mat_White_Precast_Panel", "concrete_pavement_02",
        tint_rgb=(0.86, 0.85, 0.82), tint_fac=0.78, uv_scale=1.0, roughness_val=0.55, bump_strength=0.25
    )
    palette["Mat_Dark_Charcoal_Brick"] = make_tinted_pbr_mat(
        "Mat_Dark_Charcoal_Brick", "dark_brick_wall",
        tint_rgb=(0.24, 0.22, 0.20), tint_fac=0.62, uv_scale=1.4, roughness_val=0.76, bump_strength=0.60
    )
    palette["Mat_CurtainWall_BlueGlass"] = make_tinted_pbr_mat(
        "Mat_CurtainWall_BlueGlass", "concrete_pavement_02",
        tint_rgb=(0.14, 0.22, 0.32), tint_fac=0.94, uv_scale=1.0, roughness_val=0.06, metallic=0.65, bump_strength=0.02
    )
    palette["Mat_Reflective_Window_Glass"] = make_tinted_pbr_mat(
        "Mat_Reflective_Window_Glass", "concrete_pavement_02",
        tint_rgb=(0.06, 0.10, 0.15), tint_fac=0.95, uv_scale=1.0, roughness_val=0.06, metallic=0.55, bump_strength=0.02
    )
    palette["Mat_Frosted_GreenGlass"] = make_tinted_pbr_mat(
        "Mat_Frosted_GreenGlass", "concrete_pavement_02",
        tint_rgb=(0.36, 0.48, 0.44), tint_fac=0.88, uv_scale=1.0, roughness_val=0.18, metallic=0.35, bump_strength=0.02
    )
    palette["Mat_Roof_BrightWhite"] = make_tinted_pbr_mat(
        "Mat_Roof_BrightWhite", "concrete_pavement_02",
        tint_rgb=(0.84, 0.84, 0.82), tint_fac=0.78, uv_scale=0.8, roughness_val=0.68, bump_strength=0.22
    )
    palette["Mat_Roof_LightSilver"] = make_tinted_pbr_mat(
        "Mat_Roof_LightSilver", "gravel_concrete_02",
        tint_rgb=(0.68, 0.69, 0.70), tint_fac=0.72, uv_scale=0.8, roughness_val=0.78, bump_strength=0.30
    )
    palette["Mat_Roof_WarmTan"] = make_tinted_pbr_mat(
        "Mat_Roof_WarmTan", "gravel_concrete_02",
        tint_rgb=(0.58, 0.46, 0.36), tint_fac=0.68, uv_scale=0.8, roughness_val=0.82, bump_strength=0.38
    )
    palette["Mat_Roof_DarkSlate"] = make_tinted_pbr_mat(
        "Mat_Roof_DarkSlate", "gravel_concrete_02",
        tint_rgb=(0.24, 0.26, 0.29), tint_fac=0.72, uv_scale=0.8, roughness_val=0.85, bump_strength=0.40
    )
    palette["Mat_Pool_Turquoise_Water"] = make_tinted_pbr_mat(
        "Mat_Pool_Turquoise_Water", "water_river",
        tint_rgb=(0.14, 0.64, 0.88), tint_fac=0.84, uv_scale=2.0, roughness_val=0.05, metallic=0.05, bump_strength=0.22
    )
    palette["Mat_Road_LightAsphalt"] = make_tinted_pbr_mat(
        "Mat_Road_LightAsphalt", "worn_asphalt",
        tint_rgb=(0.36, 0.36, 0.37), tint_fac=0.58, uv_scale=0.9, roughness_val=0.85, bump_strength=0.45
    )
    palette["Mat_Sidewalk_LightGranite"] = make_tinted_pbr_mat(
        "Mat_Sidewalk_LightGranite", "concrete_pavers",
        tint_rgb=(0.62, 0.60, 0.57), tint_fac=0.55, uv_scale=1.4, roughness_val=0.76, bump_strength=0.45
    )
    palette["Mat_Plaza_WarmSandstone"] = make_tinted_pbr_mat(
        "Mat_Plaza_WarmSandstone", "concrete_pavers",
        tint_rgb=(0.78, 0.72, 0.60), tint_fac=0.62, uv_scale=1.3, roughness_val=0.74, bump_strength=0.40
    )
    palette["Mat_Curb_Granite"] = make_tinted_pbr_mat(
        "Mat_Curb_Granite", "stone_block_wall",
        tint_rgb=(0.48, 0.46, 0.44), tint_fac=0.55, uv_scale=1.2, roughness_val=0.78, bump_strength=0.50
    )
    palette["Mat_Lawn_LushGreen"] = make_tinted_pbr_mat(
        "Mat_Lawn_LushGreen", "leafy_grass",
        tint_rgb=(0.18, 0.38, 0.11), tint_fac=0.42, uv_scale=1.5, roughness_val=0.88, bump_strength=0.65
    )
    palette["Mat_MTL_Grass_Lawn_PBR"] = palette["Mat_Lawn_LushGreen"]

    palette["Mat_Car_White"] = kit.get_or_create_pbr_material("Mat_Car_White", "#EAEAE6", roughness=0.22, metallic=0.45, bump_strength=0.0)
    palette["Mat_Car_Silver"] = kit.get_or_create_pbr_material("Mat_Car_Silver", "#B8BEC4", roughness=0.22, metallic=0.75, bump_strength=0.0)
    palette["Mat_Car_Dark"] = kit.get_or_create_pbr_material("Mat_Car_Dark", "#1E2226", roughness=0.25, metallic=0.65, bump_strength=0.0)
    palette["Mat_Hydrant_Red"] = kit.get_or_create_pbr_material("Mat_Hydrant_Red", "#B81D18", roughness=0.35, metallic=0.40, bump_strength=0.0)
    palette["Mat_Bollard_Green"] = kit.get_or_create_pbr_material("Mat_Bollard_Green", "#2B7A3B", roughness=0.35, bump_strength=0.0)

    return palette


# ---------------------------------------------------------------------------
# 2. 2D GEOMETRY, TRIANGULATION & WORLD-SPACE UV UTILITIES
# ---------------------------------------------------------------------------
def clean_poly_pts(coords_xy):
    pts = [[float(p[0]), float(p[1])] for p in coords_xy]
    if len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05:
        pts = pts[:-1]
    filtered = []
    for p in pts:
        if not filtered or math.hypot(p[0] - filtered[-1][0], p[1] - filtered[-1][1]) > 0.05:
            filtered.append(p)
    return filtered


def ensure_ccw(pts):
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
    if area < 0.0:
        return pts[::-1]
    return pts


def polygon_area_2d(pts):
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
    return 0.5 * abs(area)


def inset_polygon_2d(pts, inset_dist):
    pts_ccw = ensure_ccw(pts)
    n = len(pts_ccw)
    if n < 3:
        return pts_ccw
    new_pts = []
    for i in range(n):
        p_prev = Vector(pts_ccw[(i - 1) % n])
        p_curr = Vector(pts_ccw[i])
        p_next = Vector(pts_ccw[(i + 1) % n])
        d1 = p_curr - p_prev
        d2 = p_next - p_curr
        if d1.length < 1e-4 or d2.length < 1e-4:
            new_pts.append([p_curr.x, p_curr.y])
            continue
        d1.normalize()
        d2.normalize()
        n1 = Vector((-d1.y, d1.x))
        n2 = Vector((-d2.y, d2.x))
        bis = n1 + n2
        if bis.length < 1e-4:
            offset_vec = n1 * inset_dist
        else:
            bis.normalize()
            cos_half = max(0.35, bis.dot(n1))
            offset_vec = bis * min(inset_dist * 2.2, inset_dist / cos_half)
        cand = p_curr + offset_vec
        new_pts.append([cand.x, cand.y])
    return new_pts


def assign_world_uvs(bm, uv_scale=0.22):
    """Assigns clean world-space Box/Planar UVs to every face loop in `bm`."""
    uv_layer = bm.loops.layers.uv.verify()
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.normal_update()
        nx, ny, nz = abs(f.normal.x), abs(f.normal.y), abs(f.normal.z)
        for loop in f.loops:
            co = loop.vert.co
            if nz >= nx and nz >= ny:
                u, v = co.x * uv_scale, co.y * uv_scale
            elif nx >= ny:
                u, v = co.y * uv_scale, co.z * uv_scale
            else:
                u, v = co.x * uv_scale, co.z * uv_scale
            loop[uv_layer].uv = (u, v)


def pt_seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    if l2 < 1e-6:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    proj = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - proj[0], p[1] - proj[1])


def point_in_poly_2d(pt, poly):
    x, y = pt[0], pt[1]
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i][0], poly[i][1]
        xj, yj = poly[j][0], poly[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def is_party_wall(p1, p2, other_polys, threshold=0.45):
    if not other_polys:
        return False
    pts = [
        ((p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5),
        (p1[0] * 0.75 + p2[0] * 0.25, p1[1] * 0.75 + p2[1] * 0.25),
        (p1[0] * 0.25 + p2[0] * 0.75, p1[1] * 0.25 + p2[1] * 0.75),
    ]
    for pt in pts:
        for poly in other_polys:
            n = len(poly)
            for i in range(n):
                q1, q2 = poly[i], poly[(i + 1) % n]
                if pt_seg_dist(pt, q1, q2) < threshold:
                    return True
    return False


def are_adjacent(poly_a, poly_b, threshold=0.55):
    for p in poly_a:
        n = len(poly_b)
        for i in range(n):
            if pt_seg_dist(p, poly_b[i], poly_b[(i + 1) % n]) < threshold:
                return True
    return False


def add_box_between(bm, p1, p2, z0, z1, thickness=0.30, offset_out=0.0, mat_idx=0):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    seg_len = math.hypot(dx, dy)
    if seg_len < 1e-4 or z1 <= z0:
        return
    ux, uy = dx / seg_len, dy / seg_len
    nx, ny = dy / seg_len, -dx / seg_len  # Outward normal for CCW polygon

    half_t = thickness * 0.5
    c1x = p1[0] + nx * offset_out
    c1y = p1[1] + ny * offset_out
    c2x = p2[0] + nx * offset_out
    c2y = p2[1] + ny * offset_out

    v0 = bm.verts.new((c1x - nx * half_t, c1y - ny * half_t, z0))
    v1 = bm.verts.new((c2x - nx * half_t, c2y - ny * half_t, z0))
    v2 = bm.verts.new((c2x + nx * half_t, c2y + ny * half_t, z0))
    v3 = bm.verts.new((c1x + nx * half_t, c1y + ny * half_t, z0))

    v4 = bm.verts.new((c1x - nx * half_t, c1y - ny * half_t, z1))
    v5 = bm.verts.new((c2x - nx * half_t, c2y - ny * half_t, z1))
    v6 = bm.verts.new((c2x + nx * half_t, c2y + ny * half_t, z1))
    v7 = bm.verts.new((c1x + nx * half_t, c1y + ny * half_t, z1))

    for verts in ((v3, v2, v1, v0), (v4, v5, v6, v7), (v0, v1, v5, v4),
                  (v1, v2, v6, v5), (v2, v3, v7, v6), (v3, v0, v4, v7)):
        try:
            f = bm.faces.new(verts)
            f.material_index = mat_idx
        except ValueError:
            pass


def add_rotated_box(bm, cx, cy, z0, z1, size_x, size_y, angle_deg=0.0, mat_idx=0, mat_top=None):
    rad = math.radians(angle_deg)
    ux, uy = math.cos(rad) * 0.5 * size_x, math.sin(rad) * 0.5 * size_x
    vx, vy = -math.sin(rad) * 0.5 * size_y, math.cos(rad) * 0.5 * size_y
    pts = [
        (cx - ux - vx, cy - uy - vy),
        (cx + ux - vx, cy + uy - vy),
        (cx + ux + vx, cy + uy + vy),
        (cx - ux + vx, cy - uy + vy),
    ]
    extrude_prism_in_bm(bm, pts, z0, z1, mat_side=mat_idx, mat_top=(mat_top if mat_top is not None else mat_idx), cap_top=True)


def extrude_prism_in_bm(bm, pts, z0, z1, mat_side=0, mat_top=1, mat_bottom=None, cap_top=True, cap_bottom=True):
    """Extrudes an arbitrary (convex or concave) 2D polygon using exact ear-clipping triangulation."""
    if len(pts) < 3 or z1 <= z0:
        return
    pts_clean = ensure_ccw(pts)
    n = len(pts_clean)
    v_bot = [bm.verts.new((p[0], p[1], z0)) for p in pts_clean]
    v_top = [bm.verts.new((p[0], p[1], z1)) for p in pts_clean]

    for i in range(n):
        j = (i + 1) % n
        try:
            fs = bm.faces.new((v_bot[i], v_bot[j], v_top[j], v_top[i]))
            fs.material_index = mat_side
        except ValueError:
            pass

    vec_loop = [Vector((p[0], p[1], 0.0)) for p in pts_clean]
    tris = tessellate_polygon([vec_loop])
    b_mat = mat_bottom if mat_bottom is not None else mat_side
    for i0, i1, i2 in tris:
        if cap_bottom:
            try:
                fb = bm.faces.new((v_bot[i2], v_bot[i1], v_bot[i0]))
                fb.material_index = b_mat
            except ValueError:
                pass
        if cap_top:
            try:
                ft = bm.faces.new((v_top[i0], v_top[i1], v_top[i2]))
                ft.material_index = mat_top
            except ValueError:
                pass


def add_curved_voussoir_arch(bm, p1, p2, z_spring, arch_h, thickness=0.68, offset_out=0.24, mat_stone=4, n_seg=6):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    span = math.hypot(dx, dy)
    if span < 0.2:
        return
    for i in range(n_seg):
        t0 = i / n_seg
        t1 = (i + 1) / n_seg
        q1 = (p1[0] + dx * t0, p1[1] + dy * t0)
        q2 = (p1[0] + dx * t1, p1[1] + dy * t1)
        az0 = z_spring + arch_h * math.sin(math.pi * t0)
        az1 = z_spring + arch_h * math.sin(math.pi * t1)
        add_box_between(bm, q1, q2, min(az0, az1), max(az0, az1) + 0.30, thickness=thickness, offset_out=offset_out, mat_idx=mat_stone)


# ---------------------------------------------------------------------------
# 3. HIGH-POLY ARCHITECTURAL DETAILED FACADE GENERATOR
# ---------------------------------------------------------------------------
def build_detailed_facade_building(
    name, coords_xy, height, floor_height, mat_wall, mat_roof,
    mat_window, mat_frame, mat_plinth, collection,
    bay_target_width=3.6, mat_top_cornice=None,
    other_polys=None, custom_fl_count=None,
    add_balconies=False, mat_balcony=None, mat_railing=None,
    plinth_height=None, arched_windows=False, style="standard"
):
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    if len(pts) < 3:
        return None

    # Anti-clipping party-wall separation (>= 0.02m)
    if other_polys:
        adjusted_pts = []
        n = len(pts)
        for i in range(n):
            p = pts[i]
            p_prev = pts[(i - 1) % n]
            p_next = pts[(i + 1) % n]
            is_pw = is_party_wall(p_prev, p, other_polys) or is_party_wall(p, p_next, other_polys)
            if is_pw:
                cx = sum(pt[0] for pt in pts) / n
                cy = sum(pt[1] for pt in pts) / n
                vx, vy = cx - p[0], cy - p[1]
                vl = math.hypot(vx, vy)
                if vl > 1e-4:
                    adjusted_pts.append([p[0] + (vx / vl) * 0.015, p[1] + (vy / vl) * 0.015])
                else:
                    adjusted_pts.append(p)
            else:
                adjusted_pts.append(p)
        pts = ensure_ccw(adjusted_pts)

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    mats = [mat_wall, mat_roof, mat_window, mat_frame, mat_plinth]
    for m in mats:
        obj.data.materials.append(m)

    cornice_idx = 4
    if mat_top_cornice is not None:
        obj.data.materials.append(mat_top_cornice)
        cornice_idx = len(obj.data.materials) - 1

    balc_idx = cornice_idx
    if mat_balcony is not None:
        obj.data.materials.append(mat_balcony)
        balc_idx = len(obj.data.materials) - 1

    rail_idx = 3
    if mat_railing is not None:
        obj.data.materials.append(mat_railing)
        rail_idx = len(obj.data.materials) - 1

    bm = bmesh.new()

    # Inset core building shell by 0.36m so deeply recessed window glass (offset_out=-0.20m)
    # and 3D mullions (offset_out=-0.10m) sit cleanly IN FRONT of the solid core shell!
    core_pts = inset_polygon_2d(pts, 0.36)
    extrude_prism_in_bm(bm, core_pts, 0.0, height - 0.20, mat_side=0, cap_top=False, cap_bottom=False)

    ground_h = plinth_height if plinth_height is not None else min(4.4, max(3.2, height * 0.22))
    if custom_fl_count is not None:
        n_upper = max(1, custom_fl_count - 1)
    else:
        n_upper = max(1, int(round((height - ground_h) / floor_height)))
    actual_fl_h = max(2.6, (height - ground_h) / n_upper)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        if other_polys and is_party_wall(p1, p2, other_polys):
            # Solid party wall flush along shared boundary
            add_box_between(bm, p1, p2, 0.0, height - 0.15, thickness=0.38, offset_out=-0.18, mat_idx=0)
            continue
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.3:
            add_box_between(bm, p1, p2, 0.0, height - 0.15, thickness=0.38, offset_out=-0.18, mat_idx=0)
            continue

        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        p1_in = (p1[0] + dx * 0.10, p1[1] + dy * 0.10)
        p2_in = (p2[0] - dx * 0.10, p2[1] - dy * 0.10)
        n_bays = max(1, int(round(seg_len / bay_target_width)))
        bay_w = seg_len / n_bays
        pier_w = min(1.15, max(0.46, bay_w * 0.32))

        if style == "wellington_modern":
            add_box_between(bm, p1_in, p2_in, 0.0, 0.55, thickness=0.52, offset_out=0.16, mat_idx=cornice_idx)
            add_box_between(bm, p1_in, p2_in, 3.65, 4.35, thickness=0.68, offset_out=0.28, mat_idx=cornice_idx)
        else:
            # Ground plinth & belt course
            add_box_between(bm, p1_in, p2_in, 0.0, 0.85, thickness=0.54, offset_out=0.14, mat_idx=4)
            add_box_between(bm, p1_in, p2_in, ground_h - 0.30, ground_h + 0.14, thickness=0.56, offset_out=0.22, mat_idx=cornice_idx)

        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.08:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            # Ground floor pier (plinth material) + upper floor pier (wall/precast material)
            add_box_between(bm, q1, q2, 0.0, ground_h, thickness=0.68, offset_out=0.16, mat_idx=(cornice_idx if style == "wellington_modern" else 4))
            add_box_between(bm, q1, q2, ground_h, height - 0.25, thickness=0.68, offset_out=0.16, mat_idx=(cornice_idx if style == "wellington_modern" else 0))

        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            win_w = bs1 - bs0
            if win_w < 0.28:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            # Deeply recessed dark reflective glass (-0.20m vs +0.28m pier outer face -> 0.48m reveal!)
            add_box_between(bm, wp1, wp2, 0.55 if style == "wellington_modern" else 0.85, height - 0.35, thickness=0.10, offset_out=-0.20, mat_idx=2)

            # Vertical center mullion & side frame jambs
            for m_frac in (0.04, 0.50, 0.96):
                ms = bs0 + win_w * m_frac
                mp1 = (p1[0] + dx * (ms - 0.035), p1[1] + dy * (ms - 0.035))
                mp2 = (p1[0] + dx * (ms + 0.035), p1[1] + dy * (ms + 0.035))
                add_box_between(bm, mp1, mp2, 0.55 if style == "wellington_modern" else 0.85, height - 0.35, thickness=0.14, offset_out=-0.12, mat_idx=3)

            # Ground floor window transom bar
            add_box_between(bm, wp1, wp2, ground_h * 0.58, ground_h * 0.58 + 0.08, thickness=0.14, offset_out=-0.12, mat_idx=3)

            for fl in range(n_upper):
                fz0 = ground_h + fl * actual_fl_h
                fz1 = fz0 + actual_fl_h
                sp_h = min(0.90, actual_fl_h * 0.26)
                # Spandrel wall panel between floors
                add_box_between(bm, wp1, wp2, fz0, fz0 + sp_h, thickness=0.52, offset_out=0.06, mat_idx=0)
                # Protruding stone window sill (0.16m projection beyond wall)
                add_box_between(bm, wp1, wp2, fz0 + sp_h - 0.06, fz0 + sp_h + 0.10, thickness=0.42, offset_out=0.22, mat_idx=cornice_idx)
                # Protruding window lintel header
                add_box_between(bm, wp1, wp2, fz1 - 0.28, fz1, thickness=0.40, offset_out=0.20, mat_idx=cornice_idx)
                # Horizontal mid-window sash mullion bar
                mid_wz = 0.5 * (fz0 + sp_h + fz1 - 0.28)
                add_box_between(bm, wp1, wp2, mid_wz - 0.035, mid_wz + 0.035, thickness=0.14, offset_out=-0.12, mat_idx=3)

                if arched_windows:
                    add_curved_voussoir_arch(bm, wp1, wp2, fz1 - 0.58, 0.24, thickness=0.52, offset_out=0.20, mat_stone=0, n_seg=6)

                # Projecting residential balconies & railings
                if add_balconies and fl >= 1 and (b % 2 == 0) and seg_len >= 5.5:
                    add_box_between(bm, wp1, wp2, fz0 - 0.08, fz0 + 0.14, thickness=1.15, offset_out=0.68, mat_idx=balc_idx)
                    add_box_between(bm, wp1, wp2, fz0 + 0.15, fz0 + 1.05, thickness=0.06, offset_out=1.20, mat_idx=rail_idx)
                    add_box_between(bm, wp1, wp2, fz0 + 1.02, fz0 + 1.10, thickness=0.10, offset_out=1.20, mat_idx=balc_idx)

        # Top cornice and perimeter parapet wall
        add_box_between(bm, p1_in, p2_in, height - 0.38, height + 0.12, thickness=0.52, offset_out=0.18, mat_idx=cornice_idx)
        add_box_between(bm, p1_in, p2_in, height + 0.13, height + 0.48, thickness=0.36, offset_out=0.08, mat_idx=3)

    # Inset flat roof deck inside parapet (triangulated for concave polygons, zero Z-fighting)
    inner_roof = inset_polygon_2d(pts, 0.35)
    extrude_prism_in_bm(bm, inner_roof, height - 0.25, height - 0.12, mat_side=0, mat_top=1, cap_top=True, cap_bottom=False)

    # Automatic Rooftop Mechanical HVAC Units, Skylight Frames & Parapet Detail for Satellite Top-Down Density
    r_area = polygon_area_2d(inner_roof)
    if r_area > 120.0:
        rcx = sum(p[0] for p in inner_roof) / len(inner_roof)
        rcy = sum(p[1] for p in inner_roof) / len(inner_roof)
        if point_in_poly_2d((rcx, rcy), inner_roof):
            # Central mechanical HVAC skid & condenser louvers
            add_rotated_box(bm, rcx, rcy, height - 0.11, height + 1.35, 3.8, 2.6, angle_deg=-36.0, mat_idx=cornice_idx, mat_top=3)
            add_rotated_box(bm, rcx + 2.6, rcy - 1.8, height - 0.11, height + 0.85, 2.2, 1.8, angle_deg=-36.0, mat_idx=3, mat_top=cornice_idx)
            if r_area > 380.0:
                for off_x, off_y in ((-4.5, 3.2), (4.5, -3.2), (-3.2, -4.5), (3.2, 4.5)):
                    px_r, py_r = rcx + off_x, rcy + off_y
                    if point_in_poly_2d((px_r, py_r), inner_roof):
                        add_rotated_box(bm, px_r, py_r, height - 0.11, height + 0.65, 2.4, 1.5, angle_deg=54.0, mat_idx=3, mat_top=cornice_idx)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign_world_uvs(bm, uv_scale=0.22)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# ---------------------------------------------------------------------------
# 4. ROOFTOP SWIMMING POOLS, PENTHOUSES & CAMERA-MATCHED HERO FEATURES
# ---------------------------------------------------------------------------
def build_rooftop_pools_and_hero_features(palette, col_owned):
    """
    Constructs:
    1. The 4 bright cyan-blue rooftop swimming pools on white sun decks + rooftop penthouses
       and skylights visible in `satellite_topdown.png`:
       - Pool #1 on `650010119` (`X=-90.0, Y=-655.0, Z=34.5m`)
       - Pool #2 on `1083559150` (`X=-128.5, Y=-663.5, Z=27.5m`)
       - Pool #3 on `378269133` (`X=-166.5, Y=-714.5, Z=27.5m`)
       - Pool #4 on `402069143` (`X=-121.5, Y=-722.5, Z=24.0m`)
    2. Camera 1 (`Cite_Multimedia_Main_Portal`, `[-141.928, -570.423]`, heading `172.4°`):
       - Dual dark garage portals on `47175244` north-east facade (`(-139.9, -577.7)` to `(-122.0, -590.2)`)
       - Black steel exterior fire-escape stairs & balconies on `47175244` north-west wall (`(-139.9, -577.7)` to `(-152.5, -597.3)`)
       - Parked white SUV on left (`(-135.2, -583.5)`) and dark sedan on right (`(-147.8, -589.5)`).
    3. Camera 3 (`Corner_King_and_Queen`, `[-81.555, -556.758]`, heading `196.1°`) &
       Camera 4 (`Rue_Duke_Tech_Corridor`, `[-86.961, -547.171]`, heading `193.3°`):
       - `499597178` (`Avantscène Mobilier`): 3-story red-brick base (`Z=0..11.2m`) with rusticated grey stone plinth
         and cantilevered 2-story dark blue-grey reflective glass curtain-wall upper cube (`Z=11.2..19.5m`)
       - `340068506` (`Place Saint Paul`): 6-story heritage red-brick loft (`Z=0..22.5m`) with 2-story grey cut-limestone base
       - East-side red-brick industrial loft wing (`X=-108..-92, Y=-595..-558, Z=0..17.5m`) framing the right side of the street canyon
       - Parked silver hatchback (`(-79.8, -568.5)`), dark sedans (`(-85.2, -563.5)`, `(-86.5, -570.5)`),
         red fire hydrant (`(-85.8, -555.2)`), traffic sign pole (`(-85.3, -551.4)`), and green/orange bollard (`(-84.5, -549.5)`).
    """
    mesh = bpy.data.meshes.new(f"MTL_Owned_Hero_Features_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"MTL_Owned_Hero_Features_{BLOCK_ID}", mesh)
    col_owned.objects.link(obj)

    mats = [
        palette["Mat_White_Precast_Panel"],          # 0: White sun deck / precast frame
        palette["Mat_Pool_Turquoise_Water"],         # 1: Turquoise pool water
        palette["Mat_Roof_LightSilver"],             # 2: Light grey roof / penthouse
        palette["Mat_Avantscene_RedBrick"],          # 3: Avantscène red brick
        palette["Mat_CurtainWall_BlueGlass"],        # 4: Blue-grey curtain wall glass
        palette["Mat_MTL_CastIron_Black"],           # 5: Black steel fire escape, garage doors & mullions
        palette["Mat_Rusticated_GreyLimestone"],     # 6: Grey cut limestone plinth
        palette["Mat_PlaceStPaul_Brick"],            # 7: Place Saint Paul warm red brick
        palette["Mat_Lawn_LushGreen"],               # 8: Lush green grass / rooftop garden
        palette["Mat_Car_White"],                    # 9: White SUV
        palette["Mat_Car_Silver"],                   # 10: Silver hatchback
        palette["Mat_Car_Dark"],                     # 11: Dark sedan
        palette["Mat_Hydrant_Red"],                  # 12: Red fire hydrant
        palette["Mat_Bollard_Green"],                # 13: Green bollard
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # --- A. 4 ROOFTOP SWIMMING POOLS & ROOFTOP PENTHOUSES (Clamped Strictly Inside Solid Wing Roofs) ---
    # 1. Pool #1 on 650010119 roof (X=-88.5, Y=-653.5, Z=34.5m, angle=-36 deg)
    add_rotated_box(bm, -88.5, -653.5, 34.35, 34.65, 11.2, 8.2, angle_deg=-36.0, mat_idx=0, mat_top=0)
    add_rotated_box(bm, -88.5, -653.5, 34.66, 34.82, 8.2, 5.4, angle_deg=-36.0, mat_idx=0, mat_top=1)
    add_rotated_box(bm, -74.0, -666.0, 34.30, 37.50, 12.0, 7.5, angle_deg=-36.0, mat_idx=0, mat_top=2)
    # Green-roof planter beds on 650010119
    add_rotated_box(bm, -96.5, -647.5, 34.35, 34.75, 8.5, 3.2, angle_deg=-36.0, mat_idx=0, mat_top=8)

    # 2. Pool #2 on 1083559150 solid NW wing roof (X=-136.5, Y=-669.5, Z=27.5m, angle=54 deg — ZERO cantilever over courtyard!)
    add_rotated_box(bm, -136.5, -669.5, 27.35, 27.65, 12.5, 6.4, angle_deg=54.0, mat_idx=0, mat_top=0)
    add_rotated_box(bm, -136.5, -669.5, 27.66, 27.82, 9.8, 3.8, angle_deg=54.0, mat_idx=0, mat_top=1)
    add_rotated_box(bm, -124.5, -655.5, 27.35, 27.75, 7.5, 5.2, angle_deg=54.0, mat_idx=0, mat_top=8)

    # 3. Pool #3 on 378269133 roof (X=-166.5, Y=-714.5, Z=27.5m, angle=-36 deg)
    add_rotated_box(bm, -166.5, -714.5, 27.35, 27.65, 14.5, 7.8, angle_deg=-36.0, mat_idx=0, mat_top=0)
    add_rotated_box(bm, -166.5, -714.5, 27.66, 27.82, 10.8, 4.2, angle_deg=-36.0, mat_idx=0, mat_top=1)
    add_rotated_box(bm, -176.5, -707.5, 27.30, 30.20, 8.2, 5.6, angle_deg=-36.0, mat_idx=0, mat_top=2)

    # 4. Pool #4 on 402069143 roof (X=-120.5, Y=-721.5, Z=24.0m, angle=54 deg)
    add_rotated_box(bm, -120.5, -721.5, 23.85, 24.15, 16.5, 6.8, angle_deg=54.0, mat_idx=0, mat_top=0)
    add_rotated_box(bm, -120.5, -721.5, 24.16, 24.32, 12.8, 3.6, angle_deg=54.0, mat_idx=0, mat_top=1)
    add_rotated_box(bm, -133.5, -738.5, 23.80, 26.80, 9.5, 6.5, angle_deg=54.0, mat_idx=2, mat_top=2)
    add_rotated_box(bm, -112.5, -711.5, 23.85, 24.25, 8.0, 4.2, angle_deg=54.0, mat_idx=0, mat_top=8)

    # 5. Rooftop Penthouse & Green Planters on 455546170 (center tower X=-152.0, Y=-686.0, Z=31.0m)
    add_rotated_box(bm, -152.0, -686.0, 30.85, 33.80, 13.0, 7.2, angle_deg=-36.0, mat_idx=0, mat_top=2)
    add_rotated_box(bm, -144.0, -692.0, 30.85, 31.25, 7.5, 4.5, angle_deg=-36.0, mat_idx=0, mat_top=8)

    # --- B. CAMERA 1 (`Cite_Multimedia_Main_Portal`): MONTREAL STENCIL (`47175244`) DETAILS ---
    # Dual dark garage portals on NE wall (-139.9, -577.7) -> (-122.0, -590.2)
    add_box_between(bm, (-139.2, -578.2), (-135.8, -580.6), 0.18, 3.10, thickness=0.65, offset_out=0.22, mat_idx=5)
    add_box_between(bm, (-139.4, -578.1), (-135.6, -580.7), 3.10, 3.42, thickness=0.72, offset_out=0.26, mat_idx=0)
    add_box_between(bm, (-135.0, -581.1), (-131.6, -583.5), 0.18, 3.10, thickness=0.65, offset_out=0.22, mat_idx=5)
    add_box_between(bm, (-135.2, -581.0), (-131.4, -583.6), 3.10, 3.42, thickness=0.72, offset_out=0.26, mat_idx=0)

    # Exterior black steel fire-escape balconies & diagonal stairs on NW wall (-139.9, -577.7) -> (-152.5, -597.3)
    for fl_fe, z_fe in enumerate((4.2, 8.2, 12.2, 15.8)):
        add_rotated_box(bm, -143.6, -581.8, z_fe, z_fe + 0.18, 2.8, 1.6, angle_deg=57.0, mat_idx=5, mat_top=5)
        add_rotated_box(bm, -143.6, -581.8, z_fe + 0.19, z_fe + 1.05, 2.9, 1.7, angle_deg=57.0, mat_idx=5, mat_top=5)
    add_rotated_box(bm, -144.2, -581.2, 0.18, 16.8, 0.12, 0.12, angle_deg=57.0, mat_idx=5, mat_top=5)
    add_rotated_box(bm, -143.0, -582.4, 0.18, 16.8, 0.12, 0.12, angle_deg=57.0, mat_idx=5, mat_top=5)

    # Parked white SUV on left (-133.2, -581.2) and dark sedan on right (-149.2, -589.5)
    add_rotated_box(bm, -133.2, -581.2, 0.05, 1.15, 4.4, 1.85, angle_deg=-35.0, mat_idx=9, mat_top=9)
    add_rotated_box(bm, -133.2, -581.2, 1.16, 1.72, 2.6, 1.65, angle_deg=-35.0, mat_idx=4, mat_top=9)
    add_rotated_box(bm, -149.2, -589.5, 0.05, 1.05, 4.3, 1.80, angle_deg=57.0, mat_idx=11, mat_top=11)
    add_rotated_box(bm, -149.2, -589.5, 1.06, 1.55, 2.4, 1.60, angle_deg=57.0, mat_idx=4, mat_top=11)

    # Camera 1 Foreground Sidewalk Expansion Joints, Curb Bevels & Manhole Discs (H7-H8 detail boost!)
    for j_idx in range(12):
        jx = -148.0 + j_idx * 1.45
        jy = -572.5 - j_idx * 1.05
        add_rotated_box(bm, jx, jy, 0.173, 0.185, 0.06, 4.2, angle_deg=-35.0, mat_idx=5, mat_top=5)
    for mh_x, mh_y in ((-141.2, -574.8), (-143.5, -576.2), (-139.2, -573.8)):
        add_rotated_box(bm, mh_x, mh_y, 0.02, 0.045, 0.78, 0.78, angle_deg=22.0, mat_idx=5, mat_top=5)

    # --- C. CAMERA 2 (`Rue_Wellington_Industrial_Canyon`, `[-149.647, -661.439]`, heading `148°`) ---
    # Modern steel pedestrian lamp pole on left of walkway (-147.1, -665.2)
    add_rotated_box(bm, -147.1, -665.2, 0.22, 4.65, 0.14, 0.14, angle_deg=32.0, mat_idx=2, mat_top=2)
    add_rotated_box(bm, -146.7, -665.0, 4.50, 4.68, 0.85, 0.28, angle_deg=32.0, mat_idx=2, mat_top=2)
    # Low concrete retaining curbs & transverse paver joints along pedestrian garden walkway (H7-H8 detail boost!)
    add_box_between(bm, (-147.4, -664.2), (-132.2, -688.5), 0.18, 0.42, thickness=0.32, offset_out=0.0, mat_idx=0)
    add_box_between(bm, (-149.2, -665.3), (-134.0, -689.6), 0.18, 0.42, thickness=0.32, offset_out=0.0, mat_idx=0)
    for w_step in range(18):
        t_w = w_step / 17.0
        wx = -149.0 + (-133.5 - (-149.0)) * t_w
        wy = -663.5 + (-688.0 - (-663.5)) * t_w
        add_rotated_box(bm, wx, wy, 0.256, 0.268, 2.3, 0.06, angle_deg=32.0, mat_idx=6, mat_top=6)

    # --- D. CAMERA 3 & 4 (`Corner_King_and_Queen` & `Rue_Duke_Tech_Corridor`) ---
    # Cantilevered 2-Story Dark Blue-Grey Reflective Glass Curtain-Wall Upper Cube on `499597178` (`Avantscène Mobilier`, Z = 11.25 .. 19.60m)
    av_glass_pts = ensure_ccw([(-41.0, -575.8), (-73.6, -559.8), (-84.6, -573.6), (-53.8, -594.1)])
    extrude_prism_in_bm(bm, av_glass_pts, 11.25, 19.60, mat_side=4, mat_top=2, cap_top=True, cap_bottom=True)
    # 3D Curtain-Wall Mullion Grid (vertical & horizontal metallic mullions) on all sides of the cantilevered glass cube!
    for idx_edge in range(len(av_glass_pts)):
        gp1 = av_glass_pts[idx_edge]
        gp2 = av_glass_pts[(idx_edge + 1) % len(av_glass_pts)]
        glen = math.hypot(gp2[0] - gp1[0], gp2[1] - gp1[1])
        n_mull = max(2, int(round(glen / 1.65)))
        for m_i in range(n_mull + 1):
            mt = m_i / n_mull
            mx = gp1[0] + (gp2[0] - gp1[0]) * mt
            my = gp1[1] + (gp2[1] - gp1[1]) * mt
            mp_a = (mx - (gp2[0] - gp1[0]) / glen * 0.04, my - (gp2[1] - gp1[1]) / glen * 0.04)
            mp_b = (mx + (gp2[0] - gp1[0]) / glen * 0.04, my + (gp2[1] - gp1[1]) / glen * 0.04)
            add_box_between(bm, mp_a, mp_b, 11.25, 19.60, thickness=0.14, offset_out=0.05, mat_idx=5)
        for hz in (11.30, 13.95, 15.40, 18.05, 19.50):
            add_box_between(bm, gp1, gp2, hz - 0.06, hz + 0.06, thickness=0.16, offset_out=0.06, mat_idx=5)

    # Streetscape Cars (parked cleanly in the asphalt road lane, NOT on the sidewalk!), Fire Hydrant, Sign Post & Sidewalk Joints
    # Silver hatchback parked on left curb (-79.5, -567.8)
    add_rotated_box(bm, -79.5, -567.8, 0.05, 1.05, 4.1, 1.78, angle_deg=51.0, mat_idx=10, mat_top=10)
    add_rotated_box(bm, -79.5, -567.8, 1.06, 1.52, 2.3, 1.55, angle_deg=51.0, mat_idx=4, mat_top=10)
    # Second silver car further down left curb (-86.8, -576.8)
    add_rotated_box(bm, -86.8, -576.8, 0.05, 1.05, 4.1, 1.78, angle_deg=51.0, mat_idx=10, mat_top=10)
    add_rotated_box(bm, -86.8, -576.8, 1.06, 1.52, 2.3, 1.55, angle_deg=51.0, mat_idx=4, mat_top=10)
    # Dark sedans parked cleanly along the roadbed curb at (-84.8, -563.2) and (-89.8, -569.5)
    for cx_d, cy_d in ((-84.8, -563.2), (-89.8, -569.5)):
        add_rotated_box(bm, cx_d, cy_d, 0.05, 1.02, 4.1, 1.76, angle_deg=51.0, mat_idx=11, mat_top=11)
        add_rotated_box(bm, cx_d, cy_d, 1.03, 1.48, 2.3, 1.54, angle_deg=51.0, mat_idx=4, mat_top=11)

    # Foreground traffic sign post in Camera 4 (`Rue_Duke_Tech_Corridor`, `[-86.961, -547.171]`, heading `193.3°`)
    add_rotated_box(bm, -86.1, -550.8, 0.18, 2.45, 0.05, 0.05, angle_deg=0.0, mat_idx=5, mat_top=5)
    add_rotated_box(bm, -86.1, -550.8, 1.85, 2.38, 0.36, 0.04, angle_deg=15.0, mat_idx=0, mat_top=0)
    # Red fire hydrant on right sidewalk (-86.8, -554.8)
    add_rotated_box(bm, -86.8, -554.8, 0.18, 0.92, 0.24, 0.24, angle_deg=0.0, mat_idx=12, mat_top=12)
    # Green/orange bollard in bottom-right corner of Camera 4 (-85.7, -549.2)
    add_rotated_box(bm, -85.7, -549.2, 0.18, 0.72, 0.28, 0.28, angle_deg=0.0, mat_idx=13, mat_top=13)
    # Sidewalk paver expansion seams, granite curb joints & storm grates along Camera 3 & 4 foreground (H7-H8 detail boost!)
    for s_step in range(22):
        t_s = s_step / 21.0
        sx_r = -82.5 + (-102.5 - (-82.5)) * t_s
        sy_r = -548.0 + (-574.0 - (-548.0)) * t_s
        add_rotated_box(bm, sx_r, sy_r, 0.177, 0.188, 0.06, 3.5, angle_deg=51.0, mat_idx=5, mat_top=5)
        sx_l = -76.5 + (-96.5 - (-76.5)) * t_s
        sy_l = -552.5 + (-578.5 - (-552.5)) * t_s
        add_rotated_box(bm, sx_l, sy_l, 0.175, 0.186, 0.06, 3.4, angle_deg=51.0, mat_idx=5, mat_top=5)
    for gr_x, gr_y in ((-82.8, -559.2), (-84.2, -553.5), (-87.5, -551.8)):
        add_rotated_box(bm, gr_x, gr_y, 0.036, 0.052, 0.75, 0.55, angle_deg=51.0, mat_idx=5, mat_top=5)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign_world_uvs(bm, uv_scale=0.22)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# ---------------------------------------------------------------------------
# 5. WATERTIGHT ROADBED, SIDEWALKS, PARK LAWNS (Z=+0.195m) & PLAZAS
# ---------------------------------------------------------------------------
def build_ground_streets_and_parks(dossier, palette, col_owned, all_bldg_polys):
    """
    Constructs:
    1. Full-bleed watertight district ground base slab (`Z = -0.25m .. +0.005m`).
    2. Micro-stepped (`z_eps = (hw_idx * 17 + k) * 0.00025`) roadbeds, sidewalks, and curbs
       so overlapping segments at street corners/intersections never Z-fight in Cycles.
    3. Lush green park lawns (`Mat_Lawn_LushGreen` / `leafy_grass_Diffuse_2k.jpg` at `Z = +0.195m`)
       and warm sandstone/granite pedestrian plazas (`Z = +0.245m..+0.255m`) across:
       - Central 21e Arrondissement Courtyard Lawn (`X = -152..-118, Y = -720..-675`)
       - Rue Wellington / Rue Saint-Paul Ouest Linear Garden & Promenade (`X = -158..-112, Y = -695..-652`)
       - Grand Plaza of 21e Arrondissement (`X = -112..-72, Y = -698..-658`)
       - Place du Sable-Gris (`OSM 1307356192`)
    """
    mesh = bpy.data.meshes.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}", mesh)
    col_owned.objects.link(obj)

    # 0: Road_LightAsphalt
    # 1: Sidewalk_LightGranite
    # 2: Plaza_WarmSandstone
    # 3: Lawn_LushGreen (Z = +0.195m)
    # 4: Curb_Granite (Z = +0.225m)
    for m in (
        palette["Mat_Road_LightAsphalt"],
        palette["Mat_Sidewalk_LightGranite"],
        palette["Mat_Plaza_WarmSandstone"],
        palette["Mat_Lawn_LushGreen"],
        palette["Mat_Curb_Granite"],
    ):
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Full-bleed base asphalt stratum (Z = -0.25m to +0.005m)
    g_pts = [(-660.0, -960.0), (110.0, -960.0), (110.0, -470.0), (-660.0, -470.0)]
    extrude_prism_in_bm(bm, g_pts, -0.25, 0.005, mat_side=0, mat_top=0)

    # 2. OSM Highways & Flanking Sidewalks with micro-stepped z_eps
    for hw_idx, hw in enumerate(dossier.get("osm_features", {}).get("highways", [])):
        pts = hw.get("coords_xy", [])
        if len(pts) < 2:
            continue
        hw_name = (hw.get("tags", {}).get("name") or hw.get("name") or "").lower()
        hw_type = hw.get("tags", {}).get("highway", "residential")
        is_ped = hw_type in ("pedestrian", "footway", "path", "steps")

        if "bourassa" in hw_name or hw_type in ("secondary", "trunk_link"):
            w = 14.0
        elif "wellington" in hw_name:
            w = 10.0
        elif is_ped:
            w = 2.8
        else:
            w = 8.2

        mat_road = 1 if is_ped else 0
        z_top_base = 0.142 if is_ped else 0.018

        for k in range(len(pts) - 1):
            p1, p2 = pts[k], pts[k + 1]
            z_eps = (hw_idx * 17 + k) * 0.00022
            add_box_between(bm, p1, p2, -0.04 + z_eps, z_top_base + z_eps, thickness=w, offset_out=0.0, mat_idx=mat_road)

            if not is_ped:
                def sidewalk_intersects_building(sp1, sp2):
                    mid = ((sp1[0] + sp2[0]) * 0.5, (sp1[1] + sp2[1]) * 0.5)
                    for bpoly in all_bldg_polys:
                        if point_in_poly_2d(mid, bpoly):
                            return True
                        for idx_pt in range(len(bpoly)):
                            if pt_seg_dist(mid, bpoly[idx_pt], bpoly[(idx_pt + 1) % len(bpoly)]) < 1.15:
                                return True
                    return False

                for s_idx, side_sign in enumerate((1.0, -1.0)):
                    nx = -(p2[1] - p1[1]) / max(1e-4, math.hypot(p2[0] - p1[0], p2[1] - p1[1]))
                    ny = (p2[0] - p1[0]) / max(1e-4, math.hypot(p2[0] - p1[0], p2[1] - p1[1]))
                    off = side_sign * (w * 0.5 + 1.35)
                    sp1 = (p1[0] + nx * off, p1[1] + ny * off)
                    sp2 = (p2[0] + nx * off, p2[1] + ny * off)
                    if not sidewalk_intersects_building(sp1, sp2):
                        z_sw_eps = z_eps + s_idx * 0.00011
                        add_box_between(bm, p1, p2, -0.02 + z_sw_eps, 0.148 + z_sw_eps, thickness=2.6, offset_out=off, mat_idx=1)
                        add_box_between(bm, p1, p2, -0.02 + z_sw_eps, 0.162 + z_sw_eps, thickness=0.20, offset_out=side_sign * (w * 0.5 + 0.10), mat_idx=4)

    # 3. Dedicated Camera-Matched Plazas, Courtyards & Lush Green Park Lawns (Z = +0.195m)
    # A. Central 21e Arrondissement Courtyard Lawn (visible in Satellite H4..H6, V3..V5)
    courtyard_21e_pts = [
        (-152.0, -718.0), (-122.0, -696.0), (-108.0, -714.0),
        (-136.0, -746.0), (-158.0, -730.0)
    ]
    extrude_prism_in_bm(bm, courtyard_21e_pts, 0.02, 0.195, mat_side=4, mat_top=3, cap_top=True, cap_bottom=False)

    # B. Grand Pedestrian Plaza between 1083559150, 650010119 & 402069143 (Satellite H3..H5, V5..V7)
    grand_plaza_pts = [
        (-125.0, -682.0), (-92.0, -658.0), (-72.0, -684.0), (-104.0, -708.0)
    ]
    extrude_prism_in_bm(bm, grand_plaza_pts, 0.02, 0.175, mat_side=4, mat_top=2, cap_top=True, cap_bottom=False)

    # C. Camera 2 (`Rue_Wellington_Industrial_Canyon`, `[-149.647, -661.439]`, heading `148°`):
    # Lush green hydrangea/shrub garden beds on right and left of pedestrian walkway (`Z = +0.195m`)
    # plus crisp non-coplanar paved pedestrian walkway (`Z = +0.255m`)
    add_box_between(bm, (-152.0, -658.0), (-125.0, -700.0), 0.02, 0.195, thickness=9.5, offset_out=0.0, mat_idx=3)
    add_box_between(bm, (-150.5, -659.5), (-128.0, -695.0), 0.03, 0.255, thickness=2.2, offset_out=0.6, mat_idx=1)

    # D. NW Green Lawn Strip along Rue Saint-Paul Ouest (`X = -195..-155, Y = -720..-665`)
    add_box_between(bm, (-198.0, -722.0), (-154.0, -660.0), 0.02, 0.198, thickness=5.5, offset_out=0.0, mat_idx=3)

    # E. Camera 1 (`Cite_Multimedia_Main_Portal`, `[-141.928, -570.423]`, heading `172.4°`):
    # Foreground concrete sidewalk slab & driveway apron in front of Montreal Stencil (`47175244`)
    add_box_between(bm, (-152.0, -572.0), (-132.0, -586.0), 0.02, 0.172, thickness=4.2, offset_out=0.0, mat_idx=1)
    add_box_between(bm, (-152.5, -570.0), (-131.5, -584.5), 0.02, 0.184, thickness=0.24, offset_out=0.0, mat_idx=4)

    # F. Camera 3 & 4 (`Corner_King_and_Queen` & `Rue_Duke_Tech_Corridor`):
    # Clean asphalt roadbed & flanking concrete sidewalks along Rue Saint-Paul Ouest
    add_box_between(bm, (-75.0, -545.0), (-105.0, -585.0), 0.01, 0.035, thickness=10.5, offset_out=0.0, mat_idx=0)
    add_box_between(bm, (-71.0, -548.0), (-101.0, -588.0), 0.02, 0.174, thickness=3.4, offset_out=0.0, mat_idx=1)
    add_box_between(bm, (-79.5, -542.0), (-109.5, -582.0), 0.02, 0.176, thickness=3.6, offset_out=0.0, mat_idx=1)

    # G. Place du Sable-Gris (`OSM 1307356192`)
    for pk in dossier.get("osm_features", {}).get("parks_squares", []):
        pk_pts = clean_poly_pts(pk.get("coords_xy", []))
        if len(pk_pts) >= 3:
            extrude_prism_in_bm(bm, pk_pts, 0.02, 0.195, mat_side=4, mat_top=3, cap_top=True, cap_bottom=False)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign_world_uvs(bm, uv_scale=0.20)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# ---------------------------------------------------------------------------
# 6. ALL 60 PRIMARY OWNED BUILDINGS (CAMERA-MATCHED MATERIALS & HEIGHTS)
# ---------------------------------------------------------------------------
def build_all_primary_buildings(dossier, palette, col_owned):
    blds = [b for b in dossier.get("osm_features", {}).get("buildings", []) if b.get("is_primary_owner", False)]
    print(f"[{BLOCK_ID}] Total primary owned buildings in dossier: {len(blds)}")

    facade_materials = [
        palette["Mat_MTL_PierreGrise_Limestone"],
        palette["Mat_MTL_WarmBuff_Limestone"],
        palette["Mat_MTL_Red_Sandstone"],
        palette["Mat_MTL_Heritage_RedBrick"],
        palette["Mat_MTL_Victorian_Brick"],
        palette["Mat_MTL_Yellow_Buff_Brick"],
        palette["Mat_MTL_Dark_Loft_Brick"],
        palette["Mat_MTL_Whitewash_Fieldstone"],
        palette["Mat_MTL_Precast_Concrete"],
        palette["Mat_MTL_Granite_Plinth"],
        palette["Mat_MTL_Weathered_Metal"],
        palette["Mat_MTL_Limestone_Tile"],
    ]

    all_polys = [ensure_ccw(clean_poly_pts(b["coords_xy"])) for b in blds]
    n = len(blds)

    adj = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if are_adjacent(all_polys[i], all_polys[j], threshold=0.55):
                adj[i].add(j)
                adj[j].add(i)

    mat_usage = {m: 0 for m in facade_materials}
    mat_assignment = {}
    order = sorted(range(n), key=lambda idx: -len(adj[idx]))
    for idx in order:
        neighbor_mats = {mat_assignment[nb] for nb in adj[idx] if nb in mat_assignment}
        valid = [m for m in facade_materials if m not in neighbor_mats and mat_usage[m] < 10]
        if not valid:
            valid = [m for m in facade_materials if mat_usage[m] < 12]
        valid.sort(key=lambda m: (mat_usage[m], facade_materials.index(m)))
        chosen = valid[0]
        mat_assignment[idx] = chosen
        mat_usage[chosen] += 1

    built_count = 0
    mat_glass = palette["Mat_Reflective_Window_Glass"]
    mat_frame = palette["Mat_MTL_CastIron_Black"]
    mat_balcony = palette["Mat_White_Precast_Panel"]
    mat_railing = palette["Mat_CurtainWall_BlueGlass"]

    for i, b in enumerate(blds):
        bid = b["id"]
        tags = b.get("tags", {})
        raw_name = b.get("name") or tags.get("name", "")
        safe_name = "".join(c if c.isalnum() else "_" for c in raw_name).strip("_")
        if not safe_name:
            safe_name = f"Building_{bid}"
        obj_name = f"MTL_Owned_{bid}_{safe_name}"

        levels_str = tags.get("building:levels")
        if levels_str:
            try:
                levels = float(levels_str)
            except Exception:
                levels = 4.0
        else:
            area = polygon_area_2d(all_polys[i])
            if area > 1800:
                levels = 8.0
            elif area > 900:
                levels = 6.0
            elif area > 400:
                levels = 4.0
            else:
                levels = 3.5

        fl_h = 3.55
        ground_h = 4.0
        total_h = ground_h + max(0.0, levels - 1.0) * fl_h

        mat_wall = mat_assignment[i]
        mat_roof = palette["Mat_Roof_LightSilver"]
        mat_plinth = palette["Mat_Rusticated_GreyLimestone"]
        mat_cornice = palette["Mat_White_Precast_Panel"]
        bay_w = 3.5
        add_balc = False
        plinth_h = None
        arched = (bid % 2 == 0)
        style = "standard"

        # Camera-Specific Ground-Truth Overrides
        if bid == 47175244:
            # Camera 1 Hero: Montreal Stencil 4-story warm orange-red brick flatiron loft
            total_h = 16.5
            levels = 4.0
            plinth_h = 3.4
            mat_wall = palette["Mat_Stencil_WarmOrangeBrick"]
            mat_plinth = palette["Mat_Rusticated_GreyLimestone"]
            mat_cornice = palette["Mat_Rusticated_GreyLimestone"]
            mat_roof = palette["Mat_Roof_DarkSlate"]
            bay_w = 3.6
            arched = True
        elif bid in (766574909, 1083559150, 455546170, 378269133, 402069143, 650010119):
            # 21e Arrondissement & Cité du Multimédia contemporary residential/tech towers
            # Featured in Satellite View (with white roofs & pools), Camera 1 background, Camera 2 canyon, Camera 3/4 background
            if bid == 650010119:
                total_h = 34.3
                levels = 10.0
            elif bid == 455546170:
                total_h = 30.8
                levels = 9.0
            elif bid == 766574909:
                total_h = 30.5
                levels = 9.0
            elif bid in (1083559150, 378269133):
                total_h = 27.3
                levels = 8.0
            else:
                total_h = 23.8
                levels = 7.0
            mat_wall = palette["Mat_Dark_Charcoal_Brick"]
            mat_plinth = palette["Mat_White_Precast_Panel"]
            mat_cornice = palette["Mat_White_Precast_Panel"]
            mat_roof = palette["Mat_Roof_BrightWhite"]
            bay_w = 3.8
            add_balc = True
            arched = False
            style = "wellington_modern"
        elif bid == 499597178:
            # Camera 3 & 4 Left Foreground: Avantscène Mobilier 3-story red-brick base (supporting cantilevered glass upper cube)
            total_h = 11.2
            levels = 3.0
            plinth_h = 2.8
            mat_wall = palette["Mat_Avantscene_RedBrick"]
            mat_plinth = palette["Mat_Rusticated_GreyLimestone"]
            mat_cornice = palette["Mat_Rusticated_GreyLimestone"]
            mat_roof = palette["Mat_Roof_DarkSlate"]
            bay_w = 3.2
            arched = False
        elif bid == 340068506:
            # Camera 3 & 4 Left Midground: Place Saint Paul 6-story heritage red-brick loft with 2-story grey cut-limestone base
            total_h = 22.8
            levels = 6.0
            plinth_h = 7.4
            mat_wall = palette["Mat_PlaceStPaul_Brick"]
            mat_plinth = palette["Mat_Rusticated_GreyLimestone"]
            mat_cornice = palette["Mat_Rusticated_GreyLimestone"]
            mat_roof = palette["Mat_Roof_LightSilver"]
            bay_w = 3.4
            arched = True
        elif bid in (47175693, 47175695):
            # Southern industrial brick lofts in Satellite View H7..H8 (warm tan/taupe & dark slate roofs)
            total_h = 16.0
            levels = 4.0
            mat_wall = palette["Mat_Avantscene_RedBrick"]
            mat_roof = palette["Mat_Roof_WarmTan"] if bid == 47175693 else palette["Mat_Roof_DarkSlate"]
            arched = True
        elif bid in (117751910, 117751911, 117751912, 117751913, 117751914, 117751915, 117751916, 117751917, 117751918):
            # SE Cité du Multimédia lofts in Satellite View H5..H8, V6..V8
            total_h = 21.5
            levels = 6.0
            mat_wall = palette["Mat_PlaceStPaul_Brick"] if (bid % 2 == 0) else palette["Mat_White_Precast_Panel"]
            mat_roof = palette["Mat_Roof_BrightWhite"] if (bid % 2 == 1) else palette["Mat_Roof_LightSilver"]
            add_balc = True
            arched = False

        other_footprints = [all_polys[k] for k in range(n) if k != i]

        build_detailed_facade_building(
            name=obj_name,
            coords_xy=b["coords_xy"],
            height=total_h,
            floor_height=fl_h,
            mat_wall=mat_wall,
            mat_roof=mat_roof,
            mat_window=mat_glass,
            mat_frame=mat_frame,
            mat_plinth=mat_plinth,
            collection=col_owned,
            bay_target_width=bay_w,
            mat_top_cornice=mat_cornice,
            other_polys=other_footprints,
            custom_fl_count=int(round(levels)),
            add_balconies=add_balc,
            mat_balcony=mat_balcony,
            mat_railing=mat_railing,
            plinth_height=plinth_h,
            arched_windows=arched,
            style=style,
        )
        built_count += 1

    # Also build the 5-story West-Side Red-Brick Industrial Loft framing the right side (V4..V8) of Camera 3 & 4
    # with full multi-story deeply recessed windows, limestone sills/lintels, mullions, and cornice parapet!
    west_loft_coords = [(-108.5, -562.0), (-94.2, -571.5), (-112.5, -596.0), (-126.5, -586.5)]
    build_detailed_facade_building(
        name="MTL_Owned_West_SaintPaul_Industrial_Loft",
        coords_xy=west_loft_coords,
        height=17.8,
        floor_height=3.45,
        mat_wall=palette["Mat_PlaceStPaul_Brick"],
        mat_roof=palette["Mat_Roof_LightSilver"],
        mat_window=mat_glass,
        mat_frame=mat_frame,
        mat_plinth=palette["Mat_Rusticated_GreyLimestone"],
        collection=col_owned,
        bay_target_width=3.2,
        mat_top_cornice=palette["Mat_Rusticated_GreyLimestone"],
        other_polys=all_polys,
        custom_fl_count=5,
        add_balconies=False,
        plinth_height=3.6,
        arched_windows=True,
        style="standard",
    )
    all_polys.append(ensure_ccw(clean_poly_pts(west_loft_coords)))

    print(f"[{BLOCK_ID}] Successfully built {built_count} primary owned buildings in Block_{BLOCK_ID}_Owned.")
    return all_polys


# ---------------------------------------------------------------------------
# 7. REAL HIGH-POLY POLY HAVEN 3D TREES, SHRUBS, STREET LAMPS & BENCHES
# ---------------------------------------------------------------------------
def scatter_polyhaven_trees_and_props(dossier, col_owned, all_bldg_polys):
    """
    Replaces 100% of primitive box/cylinder trees with real high-poly Poly Haven 3D
    botanical models (`jacaranda_tree`, `searsia_burchellii`, `tree_small_02`, `shrub_02`),
    `street_lamp_01`, and `painted_wooden_bench` / `modular_street_seating` via
    `kit.append_polyhaven_model()`.
    """
    def is_inside_any_building(px, py, min_dist=0.85):
        for poly in all_bldg_polys:
            if point_in_poly_2d((px, py), poly):
                return True
            for k in range(len(poly)):
                if pt_seg_dist((px, py), poly[k], poly[(k + 1) % len(poly)]) < min_dist:
                    return True
        return False

    tree_cycle = ["jacaranda_tree", "searsia_burchellii", "tree_small_02"]
    placed_trees = []

    def place_tree(tx, ty, tz, asset_id, scale, rot_deg, tag_prefix="PH_Tree"):
        idx = len(placed_trees)
        kit.append_polyhaven_model(
            asset_id=asset_id,
            collection=col_owned,
            instance_name=f"MTL_Owned_{tag_prefix}_{idx}",
            location=(tx, ty, tz),
            rotation_z=math.radians(rot_deg),
            scale=scale,
        )
        placed_trees.append((tx, ty))

    # --- 1. CAMERA-EXACT FOREGROUND & COURTYARD TREES ---
    # A. Camera 2 (`Rue_Wellington_Industrial_Canyon`, `[-149.647, -661.439]`, heading `148°`)
    # Lush foreground shrub beds (`H6..H8, V3..V8`) + young street trees along right of walkway (`V4..V6, H4..H6`)
    # and tree foliage on far left (`V1..V2, H1..H5`)
    wellington_canyon_trees = [
        (-146.5, -664.2, "shrub_02", 1.55, 25.0),
        (-145.6, -665.8, "shrub_02", 1.65, 85.0),
        (-144.8, -667.4, "shrub_02", 1.50, 145.0),
        (-143.8, -669.0, "shrub_02", 1.60, 210.0),
        (-149.5, -666.5, "shrub_02", 1.45, 55.0),
        (-148.4, -668.5, "shrub_02", 1.45, 115.0),
        (-145.2, -666.8, "tree_small_02", 0.58, 40.0),
        (-143.2, -670.2, "tree_small_02", 0.62, 130.0),
        (-141.0, -673.8, "tree_small_02", 0.65, 220.0),
        (-149.8, -669.5, "tree_small_02", 0.92, 15.0),
        (-147.5, -674.0, "jacaranda_tree", 1.05, 95.0),
        (-136.0, -685.0, "jacaranda_tree", 1.15, 175.0),
    ]
    for tx, ty, model_id, sc, rot in wellington_canyon_trees:
        place_tree(tx, ty, 0.195, model_id, sc, rot, "Wellington_Tree")

    # B. Camera 1 (`Cite_Multimedia_Main_Portal`, `[-141.928, -570.423]`, heading `172.4°`)
    # Framing deciduous trees on far left (`V1..V2, H1..H3`) and far right (`V7..V8, H1..H5`)
    portal_trees = [
        (-128.5, -579.5, "jacaranda_tree", 1.35, 15.0),
        (-150.5, -584.5, "searsia_burchellii", 1.35, 75.0),
        (-155.0, -608.0, "tree_small_02", 0.95, 35.0),
        (-162.0, -618.0, "searsia_burchellii", 1.10, 125.0),
    ]
    for tx, ty, model_id, sc, rot in portal_trees:
        place_tree(tx, ty, 0.18, model_id, sc, rot, "Portal_Tree")

    # C. Camera 3 (`Corner_King_and_Queen`, `[-81.555, -556.758]`, heading `196.1°`) &
    #    Camera 4 (`Rue_Duke_Tech_Corridor`, `[-86.961, -547.171]`, heading `193.3°`)
    # Overarching street tree canopies (`H1..H3`) + sidewalk trees along Rue Saint-Paul Ouest!
    duke_trees = [
        (-89.4, -553.5, "jacaranda_tree", 1.48, 25.0),
        (-81.8, -553.2, "searsia_burchellii", 1.42, 115.0),
        (-91.8, -559.8, "searsia_burchellii", 1.45, 205.0),
        (-78.5, -562.5, "jacaranda_tree", 1.38, 295.0),
        (-93.8, -565.5, "jacaranda_tree", 1.32, 45.0),
        (-97.5, -571.5, "tree_small_02", 0.88, 135.0),
        (-102.0, -578.0, "tree_small_02", 0.85, 225.0),
    ]
    for tx, ty, model_id, sc, rot in duke_trees:
        place_tree(tx, ty, 0.18, model_id, sc, rot, "Duke_Tree")

    # D. Satellite Top-Down Central Courtyard, Grand Plaza & NW Rue Saint-Paul Canopy
    sat_canopy_coords = [
        # Central 21e Arrondissement Courtyard (X=-148..-122, Y=-738..-698)
        (-138.0, -708.0, 1.15), (-132.0, -714.0, 1.25), (-142.0, -718.0, 1.20),
        (-135.0, -724.0, 1.30), (-145.0, -728.0, 1.25), (-138.0, -734.0, 1.25),
        (-128.0, -720.0, 1.20), (-150.0, -736.0, 1.25), (-156.0, -742.0, 1.20),
        # Grand Plaza & Linear Park (X=-125..-85, Y=-695..-662)
        (-118.0, -674.0, 1.15), (-110.0, -679.0, 1.20), (-102.0, -685.0, 1.25),
        (-94.0, -672.0, 1.15), (-86.0, -684.0, 1.25), (-76.0, -692.0, 1.30),
        # NW Rue Saint-Paul Ouest Tree Line (H1..H3, V1..V3)
        (-168.0, -645.0, 1.30), (-175.0, -655.0, 1.35), (-182.0, -665.0, 1.30),
        (-189.0, -675.0, 1.35), (-160.0, -636.0, 1.25),
        # East Edge Rue Queen / Rue William Tree Line (V6..V8, H2..H6)
        (-62.0, -648.0, 1.25), (-58.0, -662.0, 1.30), (-68.0, -702.0, 1.30),
    ]
    for idx_c, (tx, ty, sc) in enumerate(sat_canopy_coords):
        if not is_inside_any_building(tx, ty, min_dist=0.6):
            model_id = tree_cycle[idx_c % len(tree_cycle)]
            place_tree(tx, ty, 0.195, model_id, sc, (idx_c * 47.0) % 360.0, "Courtyard_Tree")

    # --- 2. SURVEYED OSM TREES WITHIN ACTIVE SATELLITE CORRIDOR ---
    for idx_osm, t in enumerate(dossier.get("osm_features", {}).get("trees", [])):
        tx, ty = float(t["x"]), float(t["y"])
        if tx < -220.0 or tx > -30.0 or ty < -810.0 or ty > -530.0:
            continue
        if is_inside_any_building(tx, ty, min_dist=1.60):
            continue
        if any(math.hypot(tx - px, ty - py) < 5.5 for px, py in placed_trees):
            continue
        # Keep immediate camera lenses unobstructed
        if (math.hypot(tx + 141.9, ty + 570.4) < 16.0 or
                math.hypot(tx + 149.6, ty + 661.4) < 12.0 or
                math.hypot(tx + 81.6, ty + 556.8) < 12.0 or
                math.hypot(tx + 87.0, ty + 547.2) < 12.0):
            continue
        model_id = tree_cycle[idx_osm % len(tree_cycle)]
        place_tree(tx, ty, 0.16, model_id, 0.95, (idx_osm * 67.0) % 360.0, "OSM_Tree")

    # --- 3. HERITAGE STREET LAMPS (`street_lamp_01`) & BENCHES (`modular_street_seating` / `painted_wooden_bench`) ---
    lamp_coords = [
        (-136.5, -580.0, 0.0),
        (-142.0, -672.0, 32.0),
        (-132.0, -686.0, 32.0),
        (-82.5, -562.0, 50.0),
        (-92.0, -574.0, 50.0),
        (-102.0, -586.0, 50.0),
        (-105.0, -682.0, 0.0),
        (-92.0, -674.0, 0.0),
    ]
    for idx_l, (lx, ly, rot_deg) in enumerate(lamp_coords):
        kit.append_polyhaven_model(
            asset_id="street_lamp_01",
            collection=col_owned,
            instance_name=f"MTL_Owned_StreetLamp_{idx_l}",
            location=(lx, ly, 0.18),
            rotation_z=math.radians(rot_deg),
            scale=1.05,
        )

    bench_coords = [
        ("modular_street_seating", (-104.0, -680.0, 0.18), 35.0),
        ("modular_street_seating", (-96.0, -674.0, 0.18), 35.0),
        ("painted_wooden_bench", (-138.0, -714.0, 0.20), 54.0),
        ("painted_wooden_bench", (-132.0, -722.0, 0.20), 54.0),
        ("painted_wooden_bench", (-144.0, -671.0, 0.20), -32.0),
    ]
    for idx_b, (b_asset, b_loc, rot_deg) in enumerate(bench_coords):
        kit.append_polyhaven_model(
            asset_id=b_asset,
            collection=col_owned,
            instance_name=f"MTL_Owned_Bench_{idx_b}",
            location=b_loc,
            rotation_z=math.radians(rot_deg),
            scale=1.05,
        )

    print(f"[{BLOCK_ID}] Appended {len(placed_trees)} high-poly Poly Haven 3D trees, {len(lamp_coords)} lamps, and {len(bench_coords)} benches.")


# ---------------------------------------------------------------------------
# 8. WORLD LIGHTING & CAMERA RENDERS
# ---------------------------------------------------------------------------
def configure_world_and_lighting():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    if hasattr(scene, "cycles"):
        scene.cycles.device = "CPU"
        scene.cycles.samples = 16
        scene.cycles.use_denoising = False

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    w_out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.55
    links.new(w_out.inputs["Surface"], bg.outputs["Background"])

    if os.path.isfile(HDRI_PATH):
        env = nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(HDRI_PATH, check_existing=True)
        links.new(bg.inputs["Color"], env.outputs["Color"])
    else:
        bg.inputs["Color"].default_value = (0.68, 0.78, 0.92, 1.0)

    sun_data = bpy.data.lights.new(name=f"MTL_Sun_{BLOCK_ID}", type="SUN")
    sun_data.energy = 3.8
    sun_data.color = (1.0, 0.97, 0.90)
    sun_data.angle = math.radians(2.5)
    sun_obj = bpy.data.objects.new(name=f"MTL_Sun_{BLOCK_ID}", object_data=sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(14.0), math.radians(-135.0))

    fill_data = bpy.data.lights.new(name=f"MTL_FillSun_{BLOCK_ID}", type="SUN")
    fill_data.energy = 2.1
    fill_data.color = (1.0, 0.95, 0.86)
    fill_data.angle = math.radians(8.0)
    fill_obj = bpy.data.objects.new(name=f"MTL_FillSun_{BLOCK_ID}", object_data=fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(52.0), math.radians(-18.0), math.radians(38.0))


def render_cameras(dossier, cam_col):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640

    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        cx, cy = cam_info["blender_cam_xy_m"]
        heading_deg = float(cam_info.get("heading", cam_info.get("heading_deg", 0.0)))
        pitch_deg = float(cam_info.get("pitch_deg", 10.0))
        fov_deg = float(cam_info.get("fov_deg", 90.0))

        cam_data = bpy.data.cameras.new(name=f"SV_Cam_{label}")
        cam_data.angle = math.radians(fov_deg)
        cam_data.clip_start = 0.20
        cam_data.clip_end = 1500.0
        cam_obj = bpy.data.objects.new(name=f"SV_Cam_{label}", object_data=cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cx, cy, 1.75)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch_deg), 0.0, math.radians(-heading_deg))

    ov_data = bpy.data.cameras.new(name=f"Overview_Cam_{BLOCK_ID}")
    ov_data.angle = math.radians(52.0)
    ov_data.clip_start = 1.0
    ov_data.clip_end = 2500.0
    ov_obj = bpy.data.objects.new(name=f"Overview_Cam_{BLOCK_ID}", object_data=ov_data)
    cam_col.objects.link(ov_obj)

    target = Vector((-124.0, -700.0, 12.0))
    ov_obj.location = (-10.0, -575.0, 150.0)
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = SNAPSHOT_PATH
    try:
        bpy.ops.render.render(write_still=True)
        print(f"[{BLOCK_ID}] Rendered Block Overview Snapshot -> {SNAPSHOT_PATH}")
    except Exception as e:
        print(f"[{BLOCK_ID}] Overview snapshot skipped: {e}")


# ---------------------------------------------------------------------------
# 9. MAIN EXECUTION PIPELINE
# ---------------------------------------------------------------------------
def main():
    skip_render = False
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if "--skip-render" in args:
            skip_render = True

    print(f"[{BLOCK_ID}] Initializing headless Iteration 1 reconstruction for MTL-VM-0030...")
    bpy.ops.wm.read_factory_settings(use_empty=True)

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    master_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(master_col)
    col_owned = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    master_col.children.link(col_owned)
    cam_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Cameras")
    master_col.children.link(cam_col)

    palette = create_block_palette()

    print(f"[{BLOCK_ID}] Constructing all 60 primary owned buildings with triangulated roofs & balconies...")
    all_bldg_polys = build_all_primary_buildings(dossier, palette, col_owned)

    print(f"[{BLOCK_ID}] Constructing rooftop pools, sun decks, penthouses & hero architectural features...")
    build_rooftop_pools_and_hero_features(palette, col_owned)

    print(f"[{BLOCK_ID}] Building ground stratum, streets, sidewalks & lush green park lawns at Z=+0.195m...")
    build_ground_streets_and_parks(dossier, palette, col_owned, all_bldg_polys)

    print(f"[{BLOCK_ID}] Appending high-poly Poly Haven 3D trees, shrubs, street lamps & benches...")
    scatter_polyhaven_trees_and_props(dossier, col_owned, all_bldg_polys)

    print(f"[{BLOCK_ID}] Configuring world HDRI environment and sun lighting BEFORE saving .blend...")
    configure_world_and_lighting()

    if not skip_render:
        render_cameras(dossier, cam_col)

    print(f"[{BLOCK_ID}] Packing all 2K PBR textures and saving clean .blend / .usdc...")
    try:
        bpy.ops.file.pack_all()
        print(f"[{BLOCK_ID}] Packed all 2K PBR textures into .blend")
    except Exception as e:
        print(f"[{BLOCK_ID}] pack_all note: {e}")

    tmp_blend = BLEND_OUT_PATH + ".tmp.blend"
    for p in (tmp_blend, BLEND_OUT_PATH + "@", BLEND_OUT_PATH + "@1"):
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
    try:
        shutil.move(tmp_blend, BLEND_OUT_PATH)
    except Exception:
        shutil.copyfile(tmp_blend, BLEND_OUT_PATH)

    try:
        bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, selected_objects_only=False, visible_objects_only=True)
    except Exception:
        bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, selected_objects_only=False)
    print(f"[{BLOCK_ID}] Saved {BLEND_OUT_PATH} and exported {USDC_OUT_PATH}.")


if __name__ == "__main__":
    main()
