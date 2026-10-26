"""
Build Script for Montreal Block MTL-VM-0009
(Vieux-Séminaire / Rue Notre-Dame Ouest & Rue Saint-Pierre / Rue McGill Block, 260 Rue Notre-Dame Ouest)

Executes in headless Blender 5.2 (`blender.exe -b --python src/blocks/build_MTL_VM_0009.py`).
Adheres strictly to:
- Shared Master World Origin (`45.50472° N, -73.55661° W` = `(0, 0, 0)` in meters)
- Ownership deduplication:
  * `Block_MTL-VM-0009_Owned` (`is_primary_owner == True`, 82 buildings + streets/curbs/park/trees/lamps)
  * `Block_MTL-VM-0009_Context_Proxy` (`is_primary_owner == False`, 16 neighbor buildings + skyline context)
- High-Poly AAA Architecture:
  * Real Poly Haven 2K PBR textures (`projection='BOX'`) & `kloppenheim_06_puresky_2k.hdr` HDRI lighting
  * Deeply recessed (`0.48m+`) 3D window bays with stone sills, lintels, mullions, flat-shaded reflective glass (`Roughness=0.03, IOR=1.52`)
  * Real Poly Haven 3D `jacaranda_tree_LOD0` trees & `street_lamp_01` heritage cast-iron streetlamps from `assets/montreal_kit.blend`
"""

import os
import sys
import json
import math
import random
import bpy
import bmesh
from mathutils import Vector

ROOT_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0009"
DOSSIER_PATH = os.path.join(ROOT_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(ROOT_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_BLOCKS_DIR = os.path.join(ROOT_DIR, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(ROOT_DIR, "output", "renders")
POLYHAVEN_DIR = os.path.join(ROOT_DIR, "assets", "polyhaven")
KIT_BLEND_PATH = os.path.join(ROOT_DIR, "assets", "montreal_kit.blend")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_BLOCKS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def get_or_create_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        if parent:
            parent.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)
    return col


def load_image_cached(path, non_color=False):
    if not os.path.exists(path):
        return None
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def apply_polyhaven_2k_pbr(mat, prefix_name, uv_scale=(0.28, 0.28, 0.28), tint_rgb=None, tint_factor=0.72, roughness_mult=1.0, normal_str=1.0):
    diff_path = os.path.join(POLYHAVEN_DIR, f"{prefix_name}_Diffuse_2k.jpg")
    rough_path = os.path.join(POLYHAVEN_DIR, f"{prefix_name}_Rough_2k.jpg")
    nor_path = os.path.join(POLYHAVEN_DIR, f"{prefix_name}_nor_gl_2k.jpg")

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(out.inputs["Surface"], bsdf.outputs["BSDF"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = uv_scale
    links.new(mapping.inputs["Vector"], tex_coord.outputs["Object"])

    diff_img = load_image_cached(diff_path, non_color=False)
    if diff_img:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = diff_img
        tex_d.projection = "BOX"
        tex_d.projection_blend = 0.25
        links.new(tex_d.inputs["Vector"], mapping.outputs["Vector"])
        if tint_rgb:
            mix = nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = tint_factor
            mix.inputs[7].default_value = (*tint_rgb, 1.0)
            links.new(mix.inputs[6], tex_d.outputs["Color"])
            links.new(bsdf.inputs["Base Color"], mix.outputs[2])
        else:
            links.new(bsdf.inputs["Base Color"], tex_d.outputs["Color"])
    elif tint_rgb:
        bsdf.inputs["Base Color"].default_value = (*tint_rgb, 1.0)

    rough_img = load_image_cached(rough_path, non_color=True)
    if rough_img:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = rough_img
        tex_r.projection = "BOX"
        tex_r.projection_blend = 0.25
        links.new(tex_r.inputs["Vector"], mapping.outputs["Vector"])
        if roughness_mult != 1.0:
            math_r = nodes.new("ShaderNodeMath")
            math_r.operation = "MULTIPLY"
            math_r.inputs[1].default_value = roughness_mult
            links.new(math_r.inputs[0], tex_r.outputs["Color"])
            links.new(bsdf.inputs["Roughness"], math_r.outputs["Value"])
        else:
            links.new(bsdf.inputs["Roughness"], tex_r.outputs["Color"])

    nor_img = load_image_cached(nor_path, non_color=True)
    if nor_img:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = nor_img
        tex_n.projection = "BOX"
        tex_n.projection_blend = 0.25
        links.new(tex_n.inputs["Vector"], mapping.outputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal_str
        links.new(nmap.inputs["Color"], tex_n.outputs["Color"])
        links.new(bsdf.inputs["Normal"], nmap.outputs["Normal"])

    return mat


def create_upgraded_palette():
    palette = kit.create_montreal_material_palette()
    apply_polyhaven_2k_pbr(palette["Mat_MTL_PierreGrise_Limestone"], "sandstone_blocks_05", (0.30, 0.30, 0.30), (0.50, 0.53, 0.56), 0.78, 0.98, 1.25)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_WarmBuff_Limestone"], "sandstone_blocks_05", (0.28, 0.28, 0.28), (0.86, 0.76, 0.60), 0.70, 0.95, 1.1)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Red_Sandstone"], "castle_brick_02_red", (0.28, 0.28, 0.28), (0.76, 0.36, 0.26), 0.76, 0.95, 1.15)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Heritage_RedBrick"], "castle_brick_02_red", (0.38, 0.38, 0.38), (0.70, 0.28, 0.20), 0.76, 0.95, 1.15)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Fieldstone_Rubble"], "sandstone_blocks_05", (0.36, 0.36, 0.36), (0.58, 0.57, 0.55), 0.78, 1.0, 1.2)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Cobblestone"], "cobblestone_floor_08", (0.36, 0.36, 0.36), (0.62, 0.61, 0.59), 0.55, 0.95, 1.2)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Street_Asphalt"], "asphalt_02", (0.24, 0.24, 0.24), (0.32, 0.33, 0.35), 0.58, 0.95, 1.1)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Plaza_Light_Granite"], "sandstone_blocks_05", (0.28, 0.28, 0.28), (0.76, 0.75, 0.72), 0.76, 0.92, 0.9)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Plaza_Charcoal_Granite"], "asphalt_02", (0.28, 0.28, 0.28), (0.40, 0.41, 0.43), 0.68, 0.90, 1.0)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Slate_Roof_Dark"], "cobblestone_floor_08", (0.38, 0.38, 0.38), (0.22, 0.24, 0.27), 0.84, 0.88, 1.1)

    mat_cream = bpy.data.materials.new("Mat_MTL_Indiana_Cream_Limestone")
    apply_polyhaven_2k_pbr(mat_cream, "sandstone_blocks_05", (0.26, 0.26, 0.26), (0.94, 0.89, 0.79), 0.60, 0.88, 1.05)
    palette["Mat_MTL_Indiana_Cream_Limestone"] = mat_cream

    mat_ochre = bpy.data.materials.new("Mat_MTL_Ochre_Victorian_Sandstone")
    apply_polyhaven_2k_pbr(mat_ochre, "sandstone_blocks_05", (0.28, 0.28, 0.28), (0.82, 0.62, 0.38), 0.78, 0.92, 1.15)
    palette["Mat_MTL_Ochre_Victorian_Sandstone"] = mat_ochre

    mat_stucco = bpy.data.materials.new("Mat_MTL_Stucco_Beige_PartyWall")
    apply_polyhaven_2k_pbr(mat_stucco, "asphalt_02", (0.16, 0.16, 0.16), (0.76, 0.70, 0.58), 0.82, 1.05, 0.95)
    palette["Mat_MTL_Stucco_Beige_PartyWall"] = mat_stucco

    mat_grass = bpy.data.materials.new("Mat_MTL_Park_Grass")
    apply_polyhaven_2k_pbr(mat_grass, "asphalt_02", (0.65, 0.65, 0.65), (0.34, 0.48, 0.20), 0.88, 1.10, 0.95)
    palette["Mat_MTL_Park_Grass"] = mat_grass

    mat_fence = bpy.data.materials.new("Mat_MTL_Green_Mesh_Fence")
    apply_polyhaven_2k_pbr(mat_fence, "asphalt_02", (0.85, 0.85, 0.85), (0.12, 0.36, 0.22), 0.88, 0.88, 1.25)
    palette["Mat_MTL_Green_Mesh_Fence"] = mat_fence

    mat_dumpster = bpy.data.materials.new("Mat_MTL_Dumpster_Blue")
    apply_polyhaven_2k_pbr(mat_dumpster, "asphalt_02", (0.45, 0.45, 0.45), (0.12, 0.34, 0.72), 0.88, 0.62, 0.85)
    palette["Mat_MTL_Dumpster_Blue"] = mat_dumpster

    mat_soil = bpy.data.materials.new("Mat_MTL_Soil_Mulch")
    apply_polyhaven_2k_pbr(mat_soil, "asphalt_02", (0.60, 0.60, 0.60), (0.20, 0.15, 0.10), 0.88, 1.1, 1.2)
    palette["Mat_MTL_Soil_Mulch"] = mat_soil

    mat_avis = kit.get_or_create_pbr_material("Mat_MTL_Sign_Yellow_Avis", "#EAB325", roughness=0.35)
    palette["Mat_MTL_Sign_Yellow_Avis"] = mat_avis

    palette["Mat_MTL_Heritage_GreenFrame"] = kit.get_or_create_pbr_material("Mat_MTL_Heritage_GreenFrame", "#1E3B2B", roughness=0.42, metallic=0.18)
    palette["Mat_MTL_Awning_Red"] = kit.get_or_create_pbr_material("Mat_MTL_Awning_Red", "#8B221E", roughness=0.72)

    mat_white_wire = kit.get_or_create_pbr_material("Mat_MTL_White_Wire_Dome", "#F4F6F8", roughness=0.25)
    bsdf_w = next(n for n in mat_white_wire.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Emission Color" in bsdf_w.inputs:
        bsdf_w.inputs["Emission Color"].default_value = (1.0, 0.96, 0.84, 1.0)
        bsdf_w.inputs["Emission Strength"].default_value = 1.4
    palette["Mat_MTL_White_Wire_Dome"] = mat_white_wire

    # Upgrade Window Glass & Storefront Glass with flat-shaded specular reflection + subtle horizontal Venetian blind banding
    glass_mat = palette["Mat_MTL_Window_Glass_Dark"]
    glass_mat.use_nodes = True
    gnodes = glass_mat.node_tree.nodes
    glinks = glass_mat.node_tree.links
    gnodes.clear()
    g_out = gnodes.new("ShaderNodeOutputMaterial")
    g_bsdf = gnodes.new("ShaderNodeBsdfPrincipled")
    g_bsdf.inputs["Roughness"].default_value = 0.035
    g_bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in g_bsdf.inputs:
        g_bsdf.inputs["Specular IOR Level"].default_value = 0.92
    tcoord = gnodes.new("ShaderNodeTexCoord")
    wave = gnodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 8.5
    wave.inputs["Distortion"].default_value = 0.2
    ramp = gnodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.04, 0.06, 0.08, 1.0)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.16, 0.14, 0.11, 1.0)
    glinks.new(wave.inputs["Vector"], tcoord.outputs["Object"])
    glinks.new(ramp.inputs["Fac"], wave.outputs["Color"])
    glinks.new(g_bsdf.inputs["Base Color"], ramp.outputs["Color"])
    if "Emission Color" in g_bsdf.inputs:
        g_bsdf.inputs["Emission Color"].default_value = (0.24, 0.19, 0.12, 1.0)
        g_bsdf.inputs["Emission Strength"].default_value = 0.06
    glinks.new(g_out.inputs["Surface"], g_bsdf.outputs["BSDF"])

    # Storefront glass shares the same realistic dark reflective glass with subtle interior depth
    palette["Mat_MTL_Storefront_Warm_Interior"] = glass_mat

    return palette


def clean_poly_pts(coords_xy):
    pts = [(float(p[0]), float(p[1])) for p in coords_xy]
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-3:
        pts = pts[:-1]
    cleaned = []
    for p in pts:
        if not cleaned or math.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > 0.08:
            cleaned.append(p)
    return cleaned


def polygon_signed_area(pts):
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def ensure_ccw(pts):
    return list(reversed(pts)) if polygon_signed_area(pts) < 0 else list(pts)


def inset_polygon_toward_centroid(pts, factor):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return [(cx + (p[0] - cx) * factor, cy + (p[1] - cy) * factor) for p in pts]


def add_box_between(bm, p1, p2, z0, z1, thickness=0.35, offset_out=0.0, mat_idx=0):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-4 or z1 <= z0:
        return
    nx = dy / length
    ny = -dx / length
    d_front = offset_out + thickness * 0.5
    d_back = offset_out - thickness * 0.5

    v0 = bm.verts.new((p1[0] + nx * d_back, p1[1] + ny * d_back, z0))
    v1 = bm.verts.new((p2[0] + nx * d_back, p2[1] + ny * d_back, z0))
    v2 = bm.verts.new((p2[0] + nx * d_front, p2[1] + ny * d_front, z0))
    v3 = bm.verts.new((p1[0] + nx * d_front, p1[1] + ny * d_front, z0))
    v4 = bm.verts.new((p1[0] + nx * d_back, p1[1] + ny * d_back, z1))
    v5 = bm.verts.new((p2[0] + nx * d_back, p2[1] + ny * d_back, z1))
    v6 = bm.verts.new((p2[0] + nx * d_front, p2[1] + ny * d_front, z1))
    v7 = bm.verts.new((p1[0] + nx * d_front, p1[1] + ny * d_front, z1))

    quads = [
        (v3, v2, v1, v0),
        (v4, v5, v6, v7),
        (v2, v3, v7, v6),
        (v0, v1, v5, v4),
        (v3, v0, v4, v7),
        (v1, v2, v6, v5),
    ]
    for q in quads:
        try:
            f = bm.faces.new(q)
            f.material_index = mat_idx
            f.smooth = False
        except ValueError:
            pass


def extrude_prism_in_bm(bm, pts_2d, z0, z1, mat_side=0, mat_top=1):
    pts = ensure_ccw(pts_2d)
    if len(pts) < 3 or z1 <= z0:
        return
    b_verts = [bm.verts.new((x, y, z0)) for x, y in pts]
    t_verts = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        try:
            f = bm.faces.new((b_verts[i], b_verts[j], t_verts[j], t_verts[i]))
            f.material_index = mat_side
            f.smooth = False
        except ValueError:
            pass
    try:
        ft = bm.faces.new(t_verts)
        ft.material_index = mat_top
        ft.smooth = False
        fb = bm.faces.new(list(reversed(b_verts)))
        fb.material_index = mat_side
        fb.smooth = False
    except ValueError:
        pass


def add_pitched_mansard_roof_in_bm(bm, pts_2d, z_base, height=3.0, inset_factor=0.76, mat_slate=1, mat_trim=4, add_dormers=True):
    pts = ensure_ccw(pts_2d)
    if len(pts) < 3:
        return
    top_pts = inset_polygon_toward_centroid(pts, inset_factor)
    z_top = z_base + height
    b_verts = [bm.verts.new((x, y, z_base)) for x, y in pts]
    t_verts = [bm.verts.new((x, y, z_top)) for x, y in top_pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        try:
            f = bm.faces.new((b_verts[i], b_verts[j], t_verts[j], t_verts[i]))
            f.material_index = mat_slate
            f.smooth = False
        except ValueError:
            pass
        if add_dormers:
            seg_len = math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1])
            if seg_len >= 5.0:
                n_dorm = max(1, int(seg_len // 4.2))
                for d in range(n_dorm):
                    t0 = (d + 0.35) / n_dorm
                    t1 = (d + 0.65) / n_dorm
                    dp1 = (pts[i][0] + (pts[j][0] - pts[i][0]) * t0, pts[i][1] + (pts[j][1] - pts[i][1]) * t0)
                    dp2 = (pts[i][0] + (pts[j][0] - pts[i][0]) * t1, pts[i][1] + (pts[j][1] - pts[i][1]) * t1)
                    add_box_between(bm, dp1, dp2, z_base + 0.35, z_base + height * 0.78, thickness=0.75, offset_out=-0.15, mat_idx=mat_trim)
    try:
        ft = bm.faces.new(t_verts)
        ft.material_index = mat_slate
        ft.smooth = False
    except ValueError:
        pass


def add_curved_voussoir_arch(bm, wp1, wp2, z_spring, arch_rise, thickness=0.72, offset_out=0.25, mat_stone=4, mat_wall=0, add_keystone=True):
    dx = wp2[0] - wp1[0]
    dy = wp2[1] - wp1[1]
    span = math.hypot(dx, dy)
    if span < 0.35:
        return
    ux, uy = dx / span, dy / span
    segs = 8
    for s in range(segs):
        t0 = s / segs
        t1 = (s + 1) / segs
        a0 = math.pi * t0
        a1 = math.pi * t1
        z_curve0 = z_spring + math.sin(a0) * arch_rise
        z_curve1 = z_spring + math.sin(a1) * arch_rise
        z_low = min(z_curve0, z_curve1)
        p_s0 = (wp1[0] + dx * t0, wp1[1] + dy * t0)
        p_s1 = (wp1[0] + dx * t1, wp1[1] + dy * t1)
        # Spandrel corner infill above the curved arch intrados
        if z_spring + arch_rise + 0.18 > z_low + 0.04:
            add_box_between(bm, p_s0, p_s1, z_low, z_spring + arch_rise + 0.18, thickness=thickness - 0.06, offset_out=offset_out - 0.03, mat_idx=mat_wall)
        # Projecting curved voussoir archivolt ring
        add_box_between(bm, p_s0, p_s1, z_low - 0.04, max(z_curve0, z_curve1) + 0.16, thickness=thickness + 0.08, offset_out=offset_out + 0.04, mat_idx=mat_stone)

    if add_keystone:
        mid_x = 0.5 * (wp1[0] + wp2[0])
        mid_y = 0.5 * (wp1[1] + wp2[1])
        kw = min(0.18, span * 0.10)
        kp1 = (mid_x - ux * kw, mid_y - uy * kw)
        kp2 = (mid_x + ux * kw, mid_y + uy * kw)
        add_box_between(bm, kp1, kp2, z_spring + arch_rise - 0.10, z_spring + arch_rise + 0.32, thickness=thickness + 0.20, offset_out=offset_out + 0.10, mat_idx=mat_stone)


def build_detailed_facade_building(
    name,
    coords_xy,
    height,
    floor_height,
    mat_wall,
    mat_roof,
    mat_window,
    mat_frame,
    mat_plinth,
    collection,
    roof_style="cornice_flat",
    arched_second_floor=False,
    rusticated_piers=False,
    arched_ground_arcade=False,
    dark_castiron_storefront=False,
    mat_shop_glass=None,
    mat_top_cornice=None,
    bay_target_width=3.2,
    has_rooftop_penthouse=False,
    detail_tier="high",
):
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    if len(pts) < 3:
        return None

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    for m in (mat_wall, mat_roof, mat_window, mat_frame, mat_plinth):
        obj.data.materials.append(m)
    shop_glass_idx = 2
    if mat_shop_glass is not None:
        obj.data.materials.append(mat_shop_glass)
        shop_glass_idx = len(obj.data.materials) - 1
    cornice_mat_idx = 4
    if mat_top_cornice is not None:
        obj.data.materials.append(mat_top_cornice)
        cornice_mat_idx = len(obj.data.materials) - 1

    bm = bmesh.new()
    # Roof slab cap only at the top (prevents any interior core prism from poking through recessed windows!)
    extrude_prism_in_bm(bm, pts, max(0.5, height - 0.55), height, mat_side=0, mat_top=1)

    ground_h = min(4.3, max(3.7, height * 0.22))
    n_upper_floors = max(1, int(round((height - ground_h) / floor_height)))
    actual_fl_h = (height - ground_h) / n_upper_floors

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.2:
            add_box_between(bm, p1, p2, 0.0, height, thickness=0.60, offset_out=0.20, mat_idx=0)
            continue

        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / bay_target_width)))
        bay_w = seg_len / n_bays
        pier_w = min(1.05, max(0.42, bay_w * 0.34))

        # Plinth base & ground cornice
        plinth_mat = 3 if dark_castiron_storefront else 4
        add_box_between(bm, p1, p2, 0.0, 0.78, thickness=0.72, offset_out=0.26, mat_idx=plinth_mat)
        add_box_between(bm, p1, p2, ground_h - 0.38, ground_h + 0.16, thickness=0.82, offset_out=0.31, mat_idx=plinth_mat)

        # Vertical piers
        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.08:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            if dark_castiron_storefront:
                add_box_between(bm, q1, q2, 0.78, ground_h - 0.35, thickness=0.70, offset_out=0.25, mat_idx=3)
                add_box_between(bm, q1, q2, ground_h + 0.12, height - 0.35, thickness=0.68, offset_out=0.24, mat_idx=0)
            else:
                add_box_between(bm, q1, q2, 0.78, height - 0.35, thickness=0.68, offset_out=0.24, mat_idx=0)

            if rusticated_piers and detail_tier == "high":
                z_cur = ground_h + 0.25 if dark_castiron_storefront else 0.90
                while z_cur < height - 0.6:
                    add_box_between(bm, q1, q2, z_cur, z_cur + 0.36, thickness=0.78, offset_out=0.29, mat_idx=4)
                    z_cur += 0.44

        # Window bays & spandrels
        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            win_w = bs1 - bs0
            if win_w < 0.28:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            # Ground floor retail glass vs upper floor window glass
            add_box_between(bm, wp1, wp2, 0.78, ground_h - 0.35, thickness=0.12, offset_out=-0.16, mat_idx=shop_glass_idx)
            add_box_between(bm, wp1, wp2, ground_h + 0.12, height - 0.4, thickness=0.12, offset_out=-0.16, mat_idx=2)

            if detail_tier == "high":
                ms = 0.5 * (bs0 + bs1)
                mp1 = (p1[0] + dx * (ms - 0.045), p1[1] + dy * (ms - 0.045))
                mp2 = (p1[0] + dx * (ms + 0.045), p1[1] + dy * (ms + 0.045))
                add_box_between(bm, mp1, mp2, 0.78, height - 0.4, thickness=0.16, offset_out=-0.04, mat_idx=3)
                # Transom bar across ground floor storefront
                add_box_between(bm, wp1, wp2, ground_h - 1.15, ground_h - 1.02, thickness=0.22, offset_out=0.02, mat_idx=3)

                if arched_ground_arcade:
                    add_curved_voussoir_arch(bm, wp1, wp2, ground_h - 0.98, 0.58, thickness=0.68, offset_out=0.23, mat_stone=4, mat_wall=0, add_keystone=True)

            for fl in range(n_upper_floors):
                fz0 = ground_h + fl * actual_fl_h
                fz1 = fz0 + actual_fl_h
                sp_h = min(0.95, actual_fl_h * 0.27)
                add_box_between(bm, wp1, wp2, fz0, fz0 + sp_h, thickness=0.56, offset_out=0.18, mat_idx=0)
                add_box_between(bm, wp1, wp2, fz0 + sp_h - 0.06, fz0 + sp_h + 0.09, thickness=0.76, offset_out=0.28, mat_idx=4)
                add_box_between(bm, wp1, wp2, fz1 - 0.42, fz1, thickness=0.66, offset_out=0.23, mat_idx=4)

                if detail_tier == "high":
                    sz = fz0 + sp_h + (actual_fl_h - sp_h - 0.42) * 0.52
                    add_box_between(bm, wp1, wp2, sz - 0.035, sz + 0.035, thickness=0.16, offset_out=-0.04, mat_idx=3)

                    if arched_second_floor and fl in (0, 1):
                        add_curved_voussoir_arch(bm, wp1, wp2, fz1 - 0.82, 0.42, thickness=0.68, offset_out=0.24, mat_stone=4, mat_wall=0, add_keystone=True)

        # Roofline cornice + parapet
        add_box_between(bm, p1, p2, height - 0.58, height + 0.18, thickness=1.08, offset_out=0.42, mat_idx=cornice_mat_idx)
        add_box_between(bm, p1, p2, height + 0.18, height + 0.65, thickness=0.52, offset_out=0.20, mat_idx=0)

    if roof_style == "mansard":
        add_pitched_mansard_roof_in_bm(bm, pts, height + 0.18, height=3.8, inset_factor=0.74, mat_slate=1, mat_trim=cornice_mat_idx, add_dormers=(detail_tier == "high"))
    elif has_rooftop_penthouse:
        ph_pts = inset_polygon_toward_centroid(pts, 0.45)
        extrude_prism_in_bm(bm, ph_pts, height, height + 3.2, mat_side=4, mat_top=1)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def build_royal_trust_clock_tower_corner(coords_xy, palette, collection):
    """
    Builds OSM 339899881 (Royal Trust / Merchants Bank Victorian corner building on Rue Saint-Pierre)
    with its signature rounded corner bay and ornate rooftop Clock Tower visible on the right of
    `Corner_Rue_SaintPierre.jpg`, with zero window occlusion!
    """
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    obj = build_detailed_facade_building(
        name="MTL_Owned_339899881_RoyalTrust_ClockTower",
        coords_xy=pts,
        height=21.5,
        floor_height=3.8,
        mat_wall=palette["Mat_MTL_Ochre_Victorian_Sandstone"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_CastIron_Black"],
        mat_plinth=palette["Mat_MTL_WarmBuff_Limestone"],
        collection=collection,
        roof_style="cornice_flat",
        arched_second_floor=True,
        rusticated_piers=True,
        arched_ground_arcade=True,
        mat_shop_glass=palette["Mat_MTL_Storefront_Warm_Interior"],
        bay_target_width=3.2,
    )
    mat_clock = kit.get_or_create_pbr_material("Mat_MTL_ClockFace_Ivory", "#F4EFE0", roughness=0.3)
    obj.data.materials.append(mat_clock)  # slot 6

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Rounded corner bay & square Clock Tower at the street corner (-122.4, -222.2)
    tcx, tcy = -122.4, -222.2
    bay_r = 1.48
    bay_pts = [(tcx + bay_r * math.cos(a), tcy + bay_r * math.sin(a)) for a in [k * math.pi / 6 for k in range(12)]]
    # Core dark window column inside the corner oriel bay + stone spandrel rings & pilasters
    extrude_prism_in_bm(bm, inset_polygon_toward_centroid(bay_pts, 0.92), 0.0, 22.2, mat_side=2, mat_top=4)
    for bi in range(12):
        bp1, bp2 = bay_pts[bi], bay_pts[(bi + 1) % 12]
        if bi % 2 == 0:
            add_box_between(bm, bp1, bp2, 0.0, 22.2, thickness=0.38, offset_out=0.12, mat_idx=0)
        for fl_z in (0.0, 4.0, 7.8, 11.6, 15.4, 19.2, 21.6):
            add_box_between(bm, bp1, bp2, fl_z, fl_z + 0.85, thickness=0.45, offset_out=0.15, mat_idx=4)

    # Ornate Square Clock Tower rising from z=21.5m to z=28.5m
    tw = 2.35
    ang = math.radians(32.0)
    ca, sa = math.cos(ang), math.sin(ang)
    sq_local = [(-tw, -tw), (tw, -tw), (tw, tw), (-tw, tw)]
    t_pts = [(tcx + x * ca - y * sa, tcy + x * sa + y * ca) for x, y in sq_local]
    extrude_prism_in_bm(bm, t_pts, 21.5, 28.2, mat_side=0, mat_top=1)

    for ti in range(4):
        tp1, tp2 = t_pts[ti], t_pts[(ti + 1) % 4]
        # Balustrade & cornice bands
        add_box_between(bm, tp1, tp2, 22.0, 22.6, thickness=0.72, offset_out=0.26, mat_idx=4)
        add_box_between(bm, tp1, tp2, 24.2, 24.7, thickness=0.68, offset_out=0.24, mat_idx=4)
        add_box_between(bm, tp1, tp2, 27.6, 28.3, thickness=0.82, offset_out=0.30, mat_idx=3)
        tdx, tdy = (tp2[0] - tp1[0]) / (2 * tw), (tp2[1] - tp1[1]) / (2 * tw)
        # Corner pilasters on clock tower
        add_box_between(bm, tp1, (tp1[0] + tdx * 0.65, tp1[1] + tdy * 0.65), 22.0, 27.8, thickness=0.58, offset_out=0.20, mat_idx=4)
        add_box_between(bm, (tp2[0] - tdx * 0.65, tp2[1] - tdy * 0.65), tp2, 22.0, 27.8, thickness=0.58, offset_out=0.20, mat_idx=4)
        # 24-segment circular clock face & dark bezel ring
        cf1 = (tp1[0] + tdx * (tw - 0.90), tp1[1] + tdy * (tw - 0.90))
        cf2 = (tp1[0] + tdx * (tw + 0.90), tp1[1] + tdy * (tw + 0.90))
        add_box_between(bm, cf1, cf2, 24.9, 26.9, thickness=0.30, offset_out=0.18, mat_idx=3)
        cf_in1 = (tp1[0] + tdx * (tw - 0.74), tp1[1] + tdy * (tw - 0.74))
        cf_in2 = (tp1[0] + tdx * (tw + 0.74), tp1[1] + tdy * (tw + 0.74))
        add_box_between(bm, cf_in1, cf_in2, 25.06, 26.74, thickness=0.34, offset_out=0.21, mat_idx=6)
        # Clock hands
        ch1 = (tp1[0] + tdx * (tw - 0.08), tp1[1] + tdy * (tw - 0.08))
        ch2 = (tp1[0] + tdx * (tw + 0.08), tp1[1] + tdy * (tw + 0.08))
        add_box_between(bm, ch1, ch2, 25.85, 26.60, thickness=0.38, offset_out=0.25, mat_idx=3)
        add_box_between(bm, cf_in1, (tp1[0] + tdx * tw, tp1[1] + tdy * tw), 25.82, 25.98, thickness=0.38, offset_out=0.25, mat_idx=3)

    add_pitched_mansard_roof_in_bm(bm, t_pts, 28.2, height=2.8, inset_factor=0.18, mat_slate=1, mat_trim=3, add_dormers=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def build_pierre_grise_rusticated_339900341(coords_xy, palette, collection):
    """
    Builds OSM 339900341 (`Rue du Saint-Sacrement` 6-story Pierre Grise Neo-Classical building)
    facing camera `Rue_SaintPaul_Rear` (`-55.98, -271.91`, `heading=11.6°`).
    Features authentic rough-hewn dark-grey Pierre Grise limestone, curved segmental 2nd-floor
    stone voussoir arches with projecting keystones, and warm interior parallax reflection!
    """
    raw_pts = clean_poly_pts(coords_xy)
    adj_pts = []
    for x, y in raw_pts:
        if y < -258.0:
            adj_pts.append((x + 1.6, y + 2.1))
        else:
            adj_pts.append((x, y))
    pts = ensure_ccw(adj_pts)

    mesh = bpy.data.meshes.new("MTL_Owned_339900341_Rusticated_PierreGrise_Mesh")
    obj = bpy.data.objects.new("MTL_Owned_339900341_Rusticated_PierreGrise", mesh)
    collection.objects.link(obj)

    mat_stone = palette["Mat_MTL_PierreGrise_Limestone"]
    mat_roof = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_frame = palette["Mat_MTL_CastIron_Black"]
    mat_trim = palette["Mat_MTL_Fieldstone_Rubble"]
    mat_shop = palette["Mat_MTL_Storefront_Warm_Interior"]
    for m in (mat_stone, mat_roof, mat_glass, mat_frame, mat_trim, mat_shop):
        obj.data.materials.append(m)

    bm = bmesh.new()
    height = 22.8
    extrude_prism_in_bm(bm, pts, height - 0.55, height, mat_side=0, mat_top=1)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.5:
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / 3.8)))
        bay_w = seg_len / n_bays
        pier_w = bay_w * 0.36

        # Chamfered plinth base & continuous stone stringcourses
        add_box_between(bm, p1, p2, 0.0, 0.22, thickness=0.82, offset_out=0.30, mat_idx=4)
        add_box_between(bm, p1, p2, 4.15, 4.55, thickness=0.82, offset_out=0.30, mat_idx=0)
        add_box_between(bm, p1, p2, 8.20, 8.60, thickness=0.84, offset_out=0.31, mat_idx=0)
        add_box_between(bm, p1, p2, height - 0.65, height + 0.25, thickness=1.05, offset_out=0.40, mat_idx=0)

        # Horizontally rusticated Pierre Grise stone piers
        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.1:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            add_box_between(bm, q1, q2, 0.22, 1.05, thickness=0.84, offset_out=0.31, mat_idx=0)
            zc = 1.08
            while zc < height - 0.65:
                add_box_between(bm, q1, q2, zc, zc + 0.36, thickness=0.78, offset_out=0.28, mat_idx=0)
                add_box_between(bm, q1, q2, zc + 0.36, zc + 0.43, thickness=0.64, offset_out=0.21, mat_idx=4)
                zc += 0.43

        # Window bays
        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            win_w = bs1 - bs0
            if win_w < 0.35:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
            ms = 0.5 * (bs0 + bs1)
            mp1 = (p1[0] + dx * (ms - 0.045), p1[1] + dy * (ms - 0.045))
            mp2 = (p1[0] + dx * (ms + 0.045), p1[1] + dy * (ms + 0.045))

            # Deeply recessed reflective glass pane with horizontal Venetian blind banding
            add_box_between(bm, wp1, wp2, 0.22, height - 0.65, thickness=0.10, offset_out=-0.16, mat_idx=2)

            # Basement sill/lintel leaving basement window opening at z=0.25..0.72m
            add_box_between(bm, wp1, wp2, 0.72, 1.28, thickness=0.72, offset_out=0.25, mat_idx=0)
            add_box_between(bm, mp1, mp2, 0.24, 0.72, thickness=0.16, offset_out=-0.02, mat_idx=3)

            # 1st floor window frame, center vertical mullion, horizontal sash bar, and stone lintel/voussoir arch (z=1.28..4.15m)
            add_box_between(bm, wp1, wp2, 1.28, 1.40, thickness=0.58, offset_out=0.18, mat_idx=4)
            add_box_between(bm, wp1, wp2, 4.02, 4.15, thickness=0.58, offset_out=0.18, mat_idx=3)
            add_box_between(bm, mp1, mp2, 1.38, 4.05, thickness=0.18, offset_out=-0.02, mat_idx=3)
            add_box_between(bm, wp1, wp2, 2.72, 2.82, thickness=0.18, offset_out=-0.02, mat_idx=3)

            # 2nd floor curved segmental arched window (z=4.55..8.15m) with center mullion, curved voussoir arch, and keystone!
            add_box_between(bm, wp1, wp2, 4.55, 5.10, thickness=0.64, offset_out=0.21, mat_idx=0)
            add_box_between(bm, wp1, wp2, 5.02, 5.16, thickness=0.76, offset_out=0.27, mat_idx=4)
            add_box_between(bm, mp1, mp2, 5.10, 7.95, thickness=0.18, offset_out=-0.02, mat_idx=3)
            add_box_between(bm, wp1, wp2, 7.05, 7.14, thickness=0.18, offset_out=-0.02, mat_idx=3)

            # True 3D curved segmental stone arch + projecting keystone at z_spring=7.40m, rise=0.55m!
            add_curved_voussoir_arch(bm, wp1, wp2, 7.40, 0.55, thickness=0.74, offset_out=0.26, mat_stone=4, mat_wall=0, add_keystone=True)

            # Upper floors 3..6 (z=8.60..22.15m)
            for ufl in range(4):
                uz0 = 8.60 + ufl * 3.4
                add_box_between(bm, wp1, wp2, uz0, uz0 + 0.85, thickness=0.60, offset_out=0.19, mat_idx=0)
                add_box_between(bm, wp1, wp2, uz0 + 0.78, uz0 + 0.92, thickness=0.78, offset_out=0.28, mat_idx=4)
                add_box_between(bm, mp1, mp2, uz0 + 0.92, uz0 + 3.4, thickness=0.16, offset_out=-0.02, mat_idx=3)
                add_box_between(bm, wp1, wp2, uz0 + 2.15, uz0 + 2.23, thickness=0.16, offset_out=-0.02, mat_idx=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def build_park_and_parking_lot_1122507759(coords_xy, palette, collection):
    """
    Constructs OSM 1122507759 (`MTL_Owned_1122507759_Park_And_Terrace`) with:
    1. Real PBR grass turf lawn, diagonal concrete walkway, hollow metal planter box with soil & green shrubs,
       2 wooden picnic tables + park benches, and 2 slender tubular metal light domes with glowing warm stars (`NotreDame_Ouest_Front.jpg`),
    2. Weathered concrete retaining wall + green construction scrim fence + yellow `AVIS` sign + ribbed blue
       commercial dumpster with split black plastic lids (`Rue_SaintJean_Side.jpg`),
    3. Detailed NE heritage pavilion wing (zero blank boxes in `MTL-VM-0009_snapshot.png`).
    """
    mesh = bpy.data.meshes.new("MTL_Owned_1122507759_Park_And_Terrace_Mesh")
    obj = bpy.data.objects.new("MTL_Owned_1122507759_Park_And_Terrace", mesh)
    collection.objects.link(obj)

    mats = [
        palette["Mat_MTL_Park_Grass"],            # 0
        palette["Mat_MTL_Plaza_Light_Granite"],   # 1
        palette["Mat_MTL_CastIron_Black"],        # 2
        palette["Mat_MTL_Warm_Wood"],             # 3
        palette["Mat_MTL_White_Wire_Dome"],       # 4
        palette["Mat_MTL_Green_Mesh_Fence"],      # 5
        palette["Mat_MTL_Sign_Yellow_Avis"],      # 6
        palette["Mat_MTL_Dumpster_Blue"],         # 7
        palette["Mat_MTL_Soil_Mulch"],            # 8
        palette["Mat_MTL_Stucco_Beige_PartyWall"],# 9 (weathered concrete retaining wall)
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Grassy Park Lawn on the SW/NW portion (`NotreDame_Ouest_Front.jpg`)
    lawn_pts = [
        (-105.0, -193.0),
        (-98.0, -199.5),
        (-81.5, -211.5),
        (-54.0, -188.0),
        (-62.0, -162.0),
        (-86.0, -153.5),
    ]
    extrude_prism_in_bm(bm, lawn_pts, 0.0, 0.16, mat_side=1, mat_top=0)

    # Diagonal concrete park walkways across the lawn
    add_box_between(bm, (-104.5, -192.0), (-64.0, -172.0), 0.02, 0.18, thickness=1.8, offset_out=0.0, mat_idx=1)
    add_box_between(bm, (-96.5, -201.5), (-82.0, -211.8), 0.02, 0.17, thickness=2.6, offset_out=0.0, mat_idx=1)

    # Hollow weathered steel planter box in foreground of `NotreDame_Ouest_Front.jpg` at (-96.1, -200.4)
    pcx, pcy, pr = -96.10, -200.40, 0.36
    pl_corners = [(pcx - pr, pcy - pr), (pcx + pr, pcy - pr), (pcx + pr, pcy + pr), (pcx - pr, pcy + pr)]
    for pi in range(4):
        qp1, qp2 = pl_corners[pi], pl_corners[(pi + 1) % 4]
        add_box_between(bm, qp1, qp2, 0.16, 0.78, thickness=0.05, offset_out=0.0, mat_idx=2)
        add_box_between(bm, qp1, qp2, 0.75, 0.81, thickness=0.09, offset_out=0.02, mat_idx=2)
    # Dark soil/mulch bed inside the hollow planter box + small green foliage cluster
    soil_pts = [(pcx - pr + 0.04, pcy - pr + 0.04), (pcx + pr - 0.04, pcy - pr + 0.04), (pcx + pr - 0.04, pcy + pr - 0.04), (pcx - pr + 0.04, pcy + pr - 0.04)]
    extrude_prism_in_bm(bm, soil_pts, 0.18, 0.72, mat_side=8, mat_top=8)

    # Two picnic tables + park benches on the lawn
    for ptx, pty in [(-94.2, -189.2), (-83.8, -190.8)]:
        add_box_between(bm, (ptx - 0.9, pty - 0.4), (ptx + 0.9, pty + 0.4), 0.16, 0.22, thickness=1.6, offset_out=0.0, mat_idx=1)
        add_box_between(bm, (ptx - 0.75, pty - 0.35), (ptx + 0.75, pty + 0.35), 0.74, 0.80, thickness=0.72, offset_out=0.0, mat_idx=3)
        add_box_between(bm, (ptx - 0.75, pty - 0.35), (ptx + 0.75, pty + 0.35), 0.44, 0.49, thickness=1.35, offset_out=0.0, mat_idx=3)
        add_box_between(bm, (ptx - 0.55, pty - 0.25), (ptx - 0.45, pty - 0.20), 0.18, 0.74, thickness=0.95, offset_out=0.0, mat_idx=2)
        add_box_between(bm, (ptx + 0.45, pty + 0.20), (ptx + 0.55, pty + 0.25), 0.18, 0.74, thickness=0.95, offset_out=0.0, mat_idx=2)

    # Park benches along walkway
    for bx, by in [(-98.8, -193.2), (-80.5, -181.5)]:
        add_box_between(bm, (bx - 0.8, by - 0.3), (bx + 0.8, by + 0.3), 0.16, 0.52, thickness=0.52, offset_out=0.0, mat_idx=3)
        add_box_between(bm, (bx - 0.8, by - 0.25), (bx + 0.8, by + 0.35), 0.52, 0.88, thickness=0.10, offset_out=0.20, mat_idx=3)

    # Two slender tubular metal wire-frame light domes + glowing star ornaments inside (`NotreDame_Ouest_Front.jpg`)
    for dcx, dcy, dr in [(-90.5, -178.5, 2.85), (-74.5, -181.0, 2.85)]:
        for a_i in range(8):
            ang = a_i * math.pi / 8.0
            ca, sa = math.cos(ang), math.sin(ang)
            for s_i in range(16):
                t0 = math.pi * s_i / 16.0
                t1 = math.pi * (s_i + 1) / 16.0
                r0, z0 = dr * math.cos(t0), 0.18 + dr * math.sin(t0)
                r1, z1 = dr * math.cos(t1), 0.18 + dr * math.sin(t1)
                p_a = (dcx + r0 * ca, dcy + r0 * sa)
                p_b = (dcx + r1 * ca, dcy + r1 * sa)
                add_box_between(bm, p_a, p_b, min(z0, z1), max(z0, z1) + 0.035, thickness=0.035, offset_out=0.0, mat_idx=4)
        # Glowing 3D star light ornament inside each dome
        for st_ang in range(6):
            sa0 = st_ang * math.pi / 3.0
            add_box_between(
                bm,
                (dcx - 0.65 * math.cos(sa0), dcy - 0.65 * math.sin(sa0)),
                (dcx + 0.65 * math.cos(sa0), dcy + 0.65 * math.sin(sa0)),
                0.95,
                1.55,
                thickness=0.05,
                offset_out=0.0,
                mat_idx=4,
            )

    # 2. Weathered Concrete Retaining Wall + Green Construction Scrim Fence + Yellow AVIS Sign + Detailed Dumpster (`Rue_SaintJean_Side.jpg`)
    # Note: along f_pts, normal (nx, ny) points NE (+x, +y, away from camera at (-32.93, -195.82)), so negative offset_out faces the camera!
    f_pts = [(-28.4, -192.4), (-31.8, -188.5), (-35.2, -184.5), (-38.2, -181.2)]
    for fi in range(len(f_pts) - 1):
        fp1, fp2 = f_pts[fi], f_pts[fi + 1]
        # Weathered concrete retaining wall behind the green scrim mesh fence (+0.22) and low concrete curb base (z=0..0.44m)
        add_box_between(bm, fp1, fp2, 0.0, 2.28, thickness=0.32, offset_out=0.22, mat_idx=9)
        add_box_between(bm, fp1, fp2, 2.22, 2.34, thickness=0.42, offset_out=0.22, mat_idx=1)
        add_box_between(bm, fp1, fp2, 0.0, 0.44, thickness=0.26, offset_out=-0.04, mat_idx=9)
        # Green construction scrim fence & steel top/bottom rails + vertical fence posts facing camera (-0.06 to -0.10)
        add_box_between(bm, fp1, fp2, 0.42, 2.02, thickness=0.10, offset_out=-0.06, mat_idx=5)
        add_box_between(bm, fp1, fp2, 1.98, 2.06, thickness=0.14, offset_out=-0.08, mat_idx=2)
        for post_t in (0.0, 0.5, 1.0):
            px = fp1[0] + (fp2[0] - fp1[0]) * post_t
            py = fp1[1] + (fp2[1] - fp1[1]) * post_t
            add_box_between(bm, (px - 0.04, py - 0.04), (px + 0.04, py + 0.04), 0.40, 2.10, thickness=0.08, offset_out=-0.10, mat_idx=2)

    # Yellow `AVIS` parking sign with black border & directional arrow mounted on the camera-facing front of the green fence!
    add_box_between(bm, (-28.88, -191.82), (-29.62, -190.98), 1.02, 1.80, thickness=0.08, offset_out=-0.14, mat_idx=2)
    add_box_between(bm, (-28.92, -191.78), (-29.58, -191.02), 1.06, 1.76, thickness=0.08, offset_out=-0.16, mat_idx=6)
    add_box_between(bm, (-29.02, -191.66), (-29.48, -191.14), 1.38, 1.46, thickness=0.08, offset_out=-0.18, mat_idx=2)

    # Detailed Blue Commercial Dumpster (`Progressive`) on the left of `Rue_SaintJean_Side.jpg` at (-37.8, -183.2)
    dp1, dp2 = (-38.85, -183.85), (-36.90, -182.55)
    add_box_between(bm, dp1, dp2, 0.02, 1.46, thickness=1.35, offset_out=0.0, mat_idx=7)
    # Dual split black ribbed plastic lids on top
    add_box_between(bm, (-38.90, -183.88), (-37.90, -183.22), 1.45, 1.58, thickness=1.42, offset_out=0.0, mat_idx=2)
    add_box_between(bm, (-37.85, -183.18), (-36.85, -182.52), 1.45, 1.58, thickness=1.42, offset_out=0.0, mat_idx=2)
    # 5 vertical steel reinforcing ribs + side lifting lugs + white/yellow decal plates
    for r_i in range(5):
        rt = (r_i + 0.5) / 5.0
        rx = dp1[0] + (dp2[0] - dp1[0]) * rt
        ry = dp1[1] + (dp2[1] - dp1[1]) * rt
        add_box_between(bm, (rx - 0.04, ry - 0.03), (rx + 0.04, ry + 0.03), 0.08, 1.44, thickness=1.43, offset_out=0.0, mat_idx=7)
    # White stencil decal & yellow warning sticker on dumpster front
    add_box_between(bm, (-37.75, -183.12), (-37.30, -182.82), 1.05, 1.32, thickness=1.45, offset_out=0.0, mat_idx=4)
    add_box_between(bm, (-37.18, -182.74), (-36.96, -182.59), 1.12, 1.34, thickness=1.45, offset_out=0.0, mat_idx=6)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False

    # 3. Build the far-NE pavilion with full architectural fenestration so there is zero blank box in snapshot!
    pav_pts = [(-28.0, -148.0), (-8.0, -144.0), (-14.0, -132.0), (-32.0, -138.0)]
    build_detailed_facade_building(
        name="MTL_Owned_1122507759_NE_Pavilion",
        coords_xy=pav_pts,
        height=14.8,
        floor_height=3.6,
        mat_wall=palette["Mat_MTL_Indiana_Cream_Limestone"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_CastIron_Black"],
        mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
        collection=collection,
        roof_style="cornice_flat",
        bay_target_width=3.2,
        detail_tier="high",
    )
    return obj


def build_party_wall_building_339896149(coords_xy, palette, collection):
    """
    Constructs OSM 339896149 (`MTL_Context_Proxy_339896149`) on the right half of `Rue_SaintJean_Side.jpg`
    with its signature 5-story weathered beige stucco/concrete party wall (`(-31.5, -181.0)` to `(-18.5, -169.5)`),
    corner pilaster strips, and dark metal roof coping cap!
    """
    pts = [
        (-31.4, -181.2),
        (-25.8, -192.2),
        (-16.5, -182.5),
        (-14.2, -178.8),
        (-20.5, -170.5),
    ]
    pts = ensure_ccw(pts)
    mesh = bpy.data.meshes.new("MTL_Context_Proxy_339896149_Mesh")
    obj = bpy.data.objects.new("MTL_Context_Proxy_339896149", mesh)
    collection.objects.link(obj)

    mat_stucco = palette["Mat_MTL_Stucco_Beige_PartyWall"]
    mat_roof = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_iron = palette["Mat_MTL_CastIron_Black"]
    mat_stone = palette["Mat_MTL_PierreGrise_Limestone"]
    for m in (mat_stucco, mat_roof, mat_iron, mat_stone):
        obj.data.materials.append(m)

    bm = bmesh.new()
    h = 18.8
    extrude_prism_in_bm(bm, pts, 0.0, h, mat_side=0, mat_top=1)

    # Corner pilaster strips and top coping cap along the blank party wall facing (-32.93, -195.82)
    p1 = (-31.4, -181.2)
    p2 = (-25.8, -192.2)
    add_box_between(bm, p1, p2, h - 0.35, h + 0.25, thickness=0.55, offset_out=0.18, mat_idx=2)
    add_box_between(bm, p1, (-30.6, -182.8), 0.0, h, thickness=0.48, offset_out=0.14, mat_idx=3)
    add_box_between(bm, (-26.6, -190.6), p2, 0.0, h, thickness=0.48, offset_out=0.14, mat_idx=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def build_skyline_context_500_place_darmes(palette, collection):
    """
    Constructs the tall dark bronze/black curtain-wall skyscraper (`500 Place d'Armes`) at `(-56.0, -68.0)`
    which appears simultaneously in the background of `NotreDame_Ouest_Front.jpg`, `Corner_Rue_SaintPierre.jpg`,
    and `Rue_SaintJean_Side.jpg`!
    """
    mesh = bpy.data.meshes.new("MTL_Context_500_Place_dArmes_Skyscraper_Mesh")
    obj = bpy.data.objects.new("MTL_Context_500_Place_dArmes_Skyscraper", mesh)
    collection.objects.link(obj)

    mat_dark = palette["Mat_MTL_Dark_Bronze_CurtainWall"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_stone = palette["Mat_MTL_PierreGrise_Limestone"]
    for m in (mat_dark, mat_glass, mat_stone):
        obj.data.materials.append(m)

    bm = bmesh.new()
    cx, cy = -58.0, -72.0
    rx, ry = 14.5, 14.5
    ang = math.radians(28.0)
    ca, sa = math.cos(ang), math.sin(ang)
    t_pts = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in [(-rx, -ry), (rx, -ry), (rx, ry), (-rx, ry)]]
    h = 112.0
    extrude_prism_in_bm(bm, t_pts, 0.0, h, mat_side=1, mat_top=0)

    for i in range(4):
        p1, p2 = t_pts[i], t_pts[(i + 1) % 4]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        for m_i in range(13):
            s = m_i * (seg_len / 12.0)
            q1 = (p1[0] + dx * max(0.0, s - 0.24), p1[1] + dy * max(0.0, s - 0.24))
            q2 = (p1[0] + dx * min(seg_len, s + 0.24), p1[1] + dy * min(seg_len, s + 0.24))
            add_box_between(bm, q1, q2, 0.0, h, thickness=0.55, offset_out=0.18, mat_idx=0)
        for fl in range(28):
            fz = fl * 3.8
            add_box_between(bm, p1, p2, fz, fz + 1.05, thickness=0.45, offset_out=0.12, mat_idx=0)
        # Mechanical crown louvres at top
        add_box_between(bm, p1, p2, h - 6.5, h, thickness=0.65, offset_out=0.22, mat_idx=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def build_streets_sidewalks_and_curbs(dossier, palette, collection):
    sat_info = dossier.get("satellite", {})
    sat_cx, sat_cy = sat_info.get("center_xy_m", [-88.941, -230.431])
    sat_span = sat_info.get("span_meters", 133.93) * 3.2
    sat_img_path = sat_info.get("image_path", "")

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(sat_cx, sat_cy - 40.0, -0.06))
    ground_obj = bpy.context.active_object
    ground_obj.name = "Ground_Base_Asphalt"
    ground_obj.scale = (sat_span, sat_span, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for col in list(ground_obj.users_collection):
        col.objects.unlink(ground_obj)
    collection.objects.link(ground_obj)
    ground_obj.data.materials.append(palette["Mat_MTL_Street_Asphalt"])

    true_span = sat_info.get("span_meters", 133.93)
    if os.path.exists(sat_img_path):
        bpy.ops.mesh.primitive_plane_add(size=true_span, location=(sat_cx, sat_cy, -0.15))
        ortho_obj = bpy.context.active_object
        ortho_obj.name = "Ground_Satellite_Ortho"
        for col in list(ortho_obj.users_collection):
            col.objects.unlink(ortho_obj)
        collection.objects.link(ortho_obj)
        mat_sat = bpy.data.materials.new("Mat_MTL_Satellite_Ortho")
        mat_sat.use_nodes = True
        bsdf = next(n for n in mat_sat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Roughness"].default_value = 0.9
        tex = mat_sat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = load_image_cached(sat_img_path, non_color=False)
        mat_sat.node_tree.links.new(bsdf.inputs["Base Color"], tex.outputs["Color"])
        ortho_obj.data.materials.append(mat_sat)

    road_mesh = bpy.data.meshes.new("Streets_And_Sidewalks_Mesh")
    road_obj = bpy.data.objects.new("Streets_And_Sidewalks", road_mesh)
    collection.objects.link(road_obj)

    for m in (
        palette["Mat_MTL_Cobblestone"],
        palette["Mat_MTL_Street_Asphalt"],
        palette["Mat_MTL_Plaza_Light_Granite"],
        palette["Mat_MTL_Plaza_Charcoal_Granite"],
        palette["Mat_MTL_Indiana_Cream_Limestone"],
    ):
        road_obj.data.materials.append(m)

    bm = bmesh.new()
    for hw in dossier["osm_features"].get("highways", []):
        pts = hw.get("coords_xy", [])
        if len(pts) < 2:
            continue
        tags = hw.get("tags", {})
        hw_type = tags.get("highway", "")
        surface = tags.get("surface", "")
        name = hw.get("name", "")
        if hw_type == "footway":
            width, z_top, mat_i = 2.4, 0.14, 2
        elif surface in ("sett", "paving_stones") or "Saint-Sacrement" in name:
            width, z_top, mat_i = 8.0, 0.02, 0
        else:
            width, z_top, mat_i = 8.8, 0.02, 1

        for j in range(len(pts) - 1):
            add_box_between(bm, pts[j], pts[j + 1], -0.02, z_top, thickness=width, offset_out=0.0, mat_idx=mat_i)

    # White dashed traffic lane markings along Rue Saint-Pierre (`Corner_Rue_SaintPierre.jpg`)
    sp_start = (-142.0, -238.5)
    sp_end = (-92.0, -154.0)
    sp_len = math.hypot(sp_end[0] - sp_start[0], sp_end[1] - sp_start[1])
    sdx, sdy = (sp_end[0] - sp_start[0]) / sp_len, (sp_end[1] - sp_start[1]) / sp_len
    for d_i in range(14):
        s0 = d_i * 6.5
        s1 = s0 + 2.8
        if s1 < sp_len:
            lp1 = (sp_start[0] + sdx * s0, sp_start[1] + sdy * s0)
            lp2 = (sp_start[0] + sdx * s1, sp_start[1] + sdy * s1)
            add_box_between(bm, lp1, lp2, 0.01, 0.032, thickness=0.14, offset_out=-1.45, mat_idx=4)
            add_box_between(bm, lp1, lp2, 0.01, 0.032, thickness=0.14, offset_out=1.45, mat_idx=4)

    # Raised concrete sidewalks & granite curbs around the core sub-blocks of MTL-VM-0009
    sidewalk_aprons = [
        # Central block (260 Rue Notre-Dame Ouest / Rue Saint-Pierre / Rue du Saint-Sacrement / Rue Saint-Jean)
        [(-136.5, -237.5), (-113.0, -198.0), (-30.0, -264.0), (-68.0, -284.0)],
        # West side of Rue Saint-Pierre (in front of 339910667 & 339910666)
        [(-162.0, -258.0), (-142.5, -226.5), (-119.5, -189.5), (-178.0, -180.0)],
        # Park & Rue Notre-Dame Ouest sidewalk apron (in front of camera NotreDame_Ouest_Front at -98.47, -203.89)
        [(-108.0, -193.0), (-96.0, -203.5), (-80.0, -214.0), (-52.0, -189.0), (-86.0, -152.0)],
        # Southern block (Sonder Apollon / Rue du Saint-Sacrement & Rue Saint-Paul)
        [(-104.0, -276.0), (-56.0, -280.0), (14.0, -282.0), (-34.0, -344.0)],
    ]
    for sw_pts in sidewalk_aprons:
        ccw_pts = ensure_ccw(sw_pts)
        extrude_prism_in_bm(bm, ccw_pts, -0.02, 0.14, mat_side=3, mat_top=2)
        for k in range(len(ccw_pts)):
            q1, q2 = ccw_pts[k], ccw_pts[(k + 1) % len(ccw_pts)]
            add_box_between(bm, q1, q2, 0.0, 0.16, thickness=0.28, offset_out=0.0, mat_idx=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(road_mesh)
    bm.free()
    for poly in road_mesh.polygons:
        poly.use_smooth = False
    return road_obj


def place_polyhaven_trees_and_streetlamps(dossier, owned_col):
    if not os.path.exists(KIT_BLEND_PATH):
        return
    with bpy.data.libraries.load(KIT_BLEND_PATH, link=False) as (data_from, data_to):
        want = [n for n in ("jacaranda_tree_LOD0", "street_lamp_01", "bench_01") if n in data_from.objects]
        data_to.objects = want

    loaded = {o.name: o for o in data_to.objects if o is not None}
    tree_src = loaded.get("jacaranda_tree_LOD0")
    lamp_src = loaded.get("street_lamp_01")

    tree_coords = [(float(t["x"]), float(t["y"]), 0.14, 0.72) for t in dossier["osm_features"].get("trees", [])]
    # Add park trees visible in NotreDame_Ouest_Front.jpg and Rue_SaintJean_Side.jpg + shrub inside planter box!
    tree_coords.extend([
        (-99.5, -193.5, 0.14, 0.58),
        (-83.5, -191.5, 0.14, 0.55),
        (-74.0, -163.0, 0.14, 0.92),
        (-65.0, -166.0, 0.14, 0.98),
        (-55.0, -170.0, 0.14, 0.88),
        (-43.0, -173.0, 0.14, 0.85),
        (-48.5, -177.5, 0.14, 0.78),
        (-96.1, -200.4, 0.65, 0.14),  # Small shrub inside the foreground hollow metal planter box!
    ])

    rng = random.Random(9009)
    if tree_src:
        for idx, (tx, ty, tz, sc) in enumerate(tree_coords):
            inst = tree_src.copy()
            inst.name = f"PolyHaven_Tree_{idx:02d}"
            inst.location = (tx, ty, tz)
            s = sc * rng.uniform(0.92, 1.08)
            inst.scale = (s, s, s * rng.uniform(0.95, 1.08))
            inst.rotation_euler = (0.0, 0.0, rng.uniform(0.0, math.tau))
            owned_col.objects.link(inst)

    lamp_coords = [
        (-127.8, -227.6),  # Corner Rue Saint-Pierre right foreground lamp
        (-141.5, -224.5),  # Corner Rue Saint-Pierre left foreground lamp
        (-119.0, -211.5),
        (-102.0, -200.5),
        (-89.0, -216.0),
        (-66.0, -260.0),
        (-44.0, -277.0),
        (-31.0, -189.0),
    ]
    if lamp_src:
        for idx, (lx, ly) in enumerate(lamp_coords):
            inst = lamp_src.copy()
            inst.name = f"PolyHaven_StreetLamp_{idx:02d}"
            inst.location = (lx, ly, 0.14)
            inst.scale = (1.15, 1.15, 1.15)
            inst.rotation_euler = (0.0, 0.0, (idx * 1.1) % math.tau)
            owned_col.objects.link(inst)


def add_rooftop_mechanical_details(palette, owned_col):
    mesh = bpy.data.meshes.new("Rooftop_Mechanical_Details_Mesh")
    obj = bpy.data.objects.new("Rooftop_Mechanical_Details", mesh)
    owned_col.objects.link(obj)
    for m in (
        palette["Mat_MTL_Plaza_Light_Granite"],      # 0: HVAC housing
        palette["Mat_MTL_Dark_Bronze_CurtainWall"],  # 1: Dark louvres / fan grilles
        palette["Mat_MTL_Window_Glass_Dark"],        # 2: Skylight glass
        palette["Mat_MTL_Verdigris_Copper"],         # 3: Copper trim
        palette["Mat_MTL_Park_Grass"],               # 4: Green rooftop terrace turf
        palette["Mat_MTL_Awning_Red"],               # 5: Boutique red blade sign
        palette["Mat_MTL_CastIron_Black"],           # 6: Wrought-iron brackets & ducts
    ):
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Projecting red `Saint-Pierre` boutique blade sign + wrought-iron bracket on left foreground of Corner_Rue_SaintPierre.jpg!
    add_box_between(bm, (-141.2, -225.2), (-140.1, -224.6), 3.48, 3.55, thickness=0.06, offset_out=0.0, mat_idx=6)
    add_box_between(bm, (-140.9, -225.0), (-140.1, -224.6), 3.12, 3.46, thickness=0.09, offset_out=0.0, mat_idx=5)
    # Red street sign plate on the right-hand lamp post at (-127.8, -227.6)
    add_box_between(bm, (-128.3, -227.9), (-127.6, -227.5), 3.15, 3.52, thickness=0.08, offset_out=0.0, mat_idx=5)

    # Rooftop Green Terrace on 339900341 / 339892578 (bottom-right of satellite_topdown.png)
    terrace_pts = [(-56.0, -250.0), (-36.0, -266.0), (-43.0, -275.0), (-63.0, -259.0)]
    extrude_prism_in_bm(bm, terrace_pts, 22.8, 23.05, mat_side=0, mat_top=4)

    # Dense Rooftop HVAC chillers, condenser fan banks, ductwork & skylights matching satellite_topdown.png
    rooftop_units = [
        # 339910667 (West of Rue Saint-Pierre, z=30.5m)
        (-162.0, -214.0, 30.5, 4.5, 3.2, 2.8, 0),
        (-154.0, -225.0, 30.5, 2.4, 2.0, 1.8, 1),
        (-168.0, -202.0, 30.5, 3.2, 2.2, 2.1, 0),
        (-146.0, -216.0, 30.5, 1.8, 4.5, 1.4, 1),
        # 339899881 & 339899883 & 339903139 & 339900339 (Central-West Victorian block)
        (-112.0, -220.0, 21.5, 3.2, 2.4, 2.2, 0),
        (-103.0, -214.0, 20.5, 2.8, 2.2, 2.0, 1),
        (-121.0, -239.0, 17.8, 2.6, 2.0, 1.8, 0),
        (-83.5, -236.5, 19.2, 4.2, 3.0, 2.6, 0),
        (-76.0, -242.0, 19.2, 2.2, 1.8, 1.6, 1),
        (-90.0, -231.0, 19.2, 1.8, 3.6, 1.5, 2),
        # 339892576 Édifice Lewis central skylight, penthouse & condenser array (z=23.5m)
        (-48.5, -221.0, 23.5, 5.4, 4.0, 2.6, 2),
        (-56.0, -214.0, 23.5, 2.8, 2.2, 2.0, 0),
        (-42.0, -227.0, 23.5, 2.4, 1.8, 1.7, 1),
        # 339900340 & 339900341 & 339892577 & 339892579 (East wing)
        (-65.5, -248.0, 22.0, 3.2, 2.4, 2.1, 0),
        (-50.8, -259.5, 22.8, 3.6, 2.6, 2.2, 0),
        (-37.3, -238.5, 21.0, 3.0, 2.4, 2.1, 3),
        (-24.2, -234.8, 19.2, 2.8, 2.2, 1.9, 0),
        # 339903136, 339903137, 339903138, 339903436 (Southern central block)
        (-92.5, -273.5, 19.2, 4.5, 3.2, 2.4, 0),
        (-84.0, -268.0, 19.2, 1.6, 4.8, 1.5, 1),
        (-79.0, -289.0, 16.5, 3.4, 2.6, 2.0, 0),
        (-73.5, -304.0, 21.0, 3.8, 2.8, 2.2, 2),
        (-57.8, -284.8, 19.2, 3.0, 2.2, 1.9, 0),
        # 339704012 Sonder Apollon (z=25.5m)
        (-23.5, -308.0, 25.5, 5.5, 4.0, 3.0, 0),
        (-32.0, -315.0, 25.5, 2.6, 2.2, 1.9, 1),
        (-14.0, -298.0, 25.5, 3.2, 2.4, 2.1, 2),
    ]
    for cx, cy, z0, rx, ry, h, mat_i in rooftop_units:
        pts = [(cx - rx, cy - ry), (cx + rx, cy - ry), (cx + rx, cy + ry), (cx - rx, cy + ry)]
        extrude_prism_in_bm(bm, pts, z0, z0 + h, mat_side=mat_i, mat_top=1)
        # Add condenser fan unit banks & ductwork runs on top/side of each penthouse
        for fi in (-0.55, 0.55):
            fx, fy = cx + fi * rx * 0.55, cy
            f_pts = [(fx - 0.55, fy - 0.55), (fx + 0.55, fy - 0.55), (fx + 0.55, fy + 0.55), (fx - 0.55, fy + 0.55)]
            extrude_prism_in_bm(bm, f_pts, z0 + h, z0 + h + 0.45, mat_side=6, mat_top=1)
        add_box_between(bm, (cx - rx - 2.2, cy), (cx + rx + 2.2, cy), z0 + 0.35, z0 + 0.95, thickness=0.65, offset_out=0.0, mat_idx=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def setup_world_and_lighting():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True

    world = bpy.data.worlds.new("World_MTL_VM_0009") if not scene.world else scene.world
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.15
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(out.inputs["Surface"], bg.outputs["Background"])

    hdri_path = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")
    if os.path.exists(hdri_path):
        env_tex = nodes.new("ShaderNodeTexEnvironment")
        env_tex.image = load_image_cached(hdri_path, non_color=False)
        links.new(bg.inputs["Color"], env_tex.outputs["Color"])

    sun_data = bpy.data.lights.new(name="Sun_MTL_VM_0009", type="SUN")
    sun_data.energy = 3.8
    sun_data.color = (1.0, 0.96, 0.89)
    sun_data.angle = math.radians(1.2)
    sun_obj = bpy.data.objects.new(name="Sun_MTL_VM_0009", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(12.0), math.radians(-145.0))


def render_cameras(dossier, iter_num=2):
    scene = bpy.context.scene
    cam_col = get_or_create_collection("Cameras_MTL-VM-0009")

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.image_settings.file_format = "PNG"

    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        cx, cy = cam_info["blender_cam_xy_m"]
        cz = 1.7
        heading = float(cam_info.get("heading", cam_info.get("heading_deg", 0.0)))
        pitch = 10.0

        cam_data = bpy.data.cameras.new(f"Cam_{label}")
        cam_data.lens_unit = "FOV"
        cam_data.angle = math.radians(cam_info.get("fov_deg", 90.0))
        cam_data.clip_start = 0.2
        cam_data.clip_end = 1200.0

        cam_obj = bpy.data.objects.new(f"Cam_{label}", cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cx, cy, cz)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch), 0.0, math.radians(-heading))

        scene.camera = cam_obj
        out_path = os.path.join(RENDERS_DIR, f"iter{iter_num}_{label}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View Camera [{label}] -> {out_path}")

    # Overview Snapshot Camera framing the core MTL-VM-0009 block around (-88.94, -230.43)
    ov_data = bpy.data.cameras.new("Cam_Overview_MTL_VM_0009")
    ov_data.lens_unit = "FOV"
    ov_data.angle = math.radians(60.0)
    ov_data.clip_end = 1800.0
    ov_obj = bpy.data.objects.new("Cam_Overview_MTL_VM_0009", ov_data)
    cam_col.objects.link(ov_obj)

    ov_obj.location = (-205.0, -345.0, 128.0)
    target = Vector((-78.0, -232.0, 12.0))
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    snap_path = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
    scene.render.filepath = snap_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Block Overview Snapshot -> {snap_path}")


def main():
    clear_scene()
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    palette = create_upgraded_palette()
    master_col = get_or_create_collection(f"Block_{BLOCK_ID}")
    owned_col = get_or_create_collection(f"Block_{BLOCK_ID}_Owned", parent=master_col)
    proxy_col = get_or_create_collection(f"Block_{BLOCK_ID}_Context_Proxy", parent=master_col)

    build_streets_sidewalks_and_curbs(dossier, palette, owned_col)

    owned_count = 0
    proxy_count = 0

    for b in dossier["osm_features"]["buildings"]:
        bid = b["id"]
        coords = b["coords_xy"]
        cx, cy = b["centroid_xy"]
        is_owned = bool(b.get("is_primary_owner", False))
        tags = b.get("tags", {})
        levels_str = tags.get("building:levels")
        levels = int(levels_str) if (levels_str and str(levels_str).isdigit()) else None

        d_tier = "high" if cy > -335.0 else "standard"

        if is_owned:
            owned_count += 1
            if bid == 1122507759:
                build_park_and_parking_lot_1122507759(coords, palette, owned_col)
            elif bid == 339899881:
                build_royal_trust_clock_tower_corner(coords, palette, owned_col)
            elif bid == 339900341:
                build_pierre_grise_rusticated_339900341(coords, palette, owned_col)
            elif bid == 339910667:
                # Grand cream-limestone Beaux-Arts building on left of Corner_Rue_SaintPierre.jpg with dark cast-iron storefront!
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_RueSaintPierre_BeauxArts",
                    coords_xy=coords,
                    height=30.5,
                    floor_height=3.6,
                    mat_wall=palette["Mat_MTL_Indiana_Cream_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_WarmBuff_Limestone"],
                    collection=owned_col,
                    roof_style="cornice_flat",
                    dark_castiron_storefront=True,
                    mat_shop_glass=palette["Mat_MTL_Storefront_Warm_Interior"],
                    bay_target_width=3.2,
                    detail_tier="high",
                )
            elif bid == 339910666:
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_RueSaintPierre_North",
                    coords_xy=coords,
                    height=18.5,
                    floor_height=3.7,
                    mat_wall=palette["Mat_MTL_Ochre_Victorian_Sandstone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_WarmBuff_Limestone"],
                    collection=owned_col,
                    roof_style="mansard",
                    arched_second_floor=True,
                    dark_castiron_storefront=True,
                    mat_shop_glass=palette["Mat_MTL_Storefront_Warm_Interior"],
                    bay_target_width=3.1,
                    detail_tier="high",
                )
            elif bid == 339903139:
                # Immediate right foreground of Corner_Rue_SaintPierre.jpg: warm buff/ochre sandstone facade + dark green upper cornice!
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_Corner_GreenCornice",
                    coords_xy=coords,
                    height=17.8,
                    floor_height=3.8,
                    mat_wall=palette["Mat_MTL_WarmBuff_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_Ochre_Victorian_Sandstone"],
                    mat_top_cornice=palette["Mat_MTL_Heritage_GreenFrame"],
                    mat_shop_glass=palette["Mat_MTL_Storefront_Warm_Interior"],
                    collection=owned_col,
                    roof_style="mansard",
                    rusticated_piers=True,
                    bay_target_width=3.1,
                    detail_tier="high",
                )
            elif bid == 339899883:
                # Victorian Red Sandstone building north of Royal Trust on Rue Saint-Pierre
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_Victorian_RedSandstone",
                    coords_xy=coords,
                    height=20.5,
                    floor_height=3.7,
                    mat_wall=palette["Mat_MTL_Red_Sandstone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_WarmBuff_Limestone"],
                    mat_shop_glass=palette["Mat_MTL_Storefront_Warm_Interior"],
                    collection=owned_col,
                    roof_style="cornice_flat",
                    arched_second_floor=True,
                    bay_target_width=3.1,
                    detail_tier="high",
                )
            elif bid == 339892576:
                # Édifice Lewis (232 Rue De l'Hôpital, visible on right of NotreDame_Ouest_Front.jpg)
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_Edifice_Lewis",
                    coords_xy=coords,
                    height=23.5,
                    floor_height=3.7,
                    mat_wall=palette["Mat_MTL_Ochre_Victorian_Sandstone"],
                    mat_roof=palette["Mat_MTL_Red_Sandstone"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_WarmBuff_Limestone"],
                    mat_top_cornice=palette["Mat_MTL_Heritage_GreenFrame"],
                    collection=owned_col,
                    roof_style="cornice_flat",
                    arched_ground_arcade=True,
                    bay_target_width=3.3,
                    detail_tier="high",
                )
            elif bid == 339898462:
                # Low 2-story grey stone annex behind the park in NotreDame_Ouest_Front.jpg
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_Park_Annex",
                    coords_xy=coords,
                    height=8.2,
                    floor_height=3.8,
                    mat_wall=palette["Mat_MTL_PierreGrise_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=owned_col,
                    roof_style="cornice_flat",
                    bay_target_width=3.5,
                    detail_tier="high",
                )
            else:
                b_hash = int(bid) % 5
                default_h = [17.5, 19.2, 21.0, 16.5, 22.0][b_hash]
                h = (levels * 3.65) if levels else default_h
                wall_mats = [
                    palette["Mat_MTL_PierreGrise_Limestone"],
                    palette["Mat_MTL_WarmBuff_Limestone"],
                    palette["Mat_MTL_Ochre_Victorian_Sandstone"],
                    palette["Mat_MTL_Heritage_RedBrick"],
                    palette["Mat_MTL_Red_Sandstone"],
                ]
                r_style = "mansard" if (b_hash == 2 and h < 22.0) else "cornice_flat"
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}",
                    coords_xy=coords,
                    height=h,
                    floor_height=3.65,
                    mat_wall=wall_mats[b_hash],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=owned_col,
                    roof_style=r_style,
                    arched_second_floor=(b_hash in (1, 2)),
                    rusticated_piers=(b_hash == 0),
                    bay_target_width=3.3,
                    detail_tier=d_tier,
                )
        else:
            proxy_count += 1
            if bid == 339896149:
                build_party_wall_building_339896149(coords, palette, proxy_col)
            elif bid in (340057024, 340057025, 340057026, 340057027):
                # Left side of NotreDame_Ouest_Front.jpg: 4-story Victorian stone/brick row with prominent mansard roof (`krug`)
                has_mansard = bid in (340057024, 340057025)
                build_detailed_facade_building(
                    name=f"MTL_Context_Proxy_{bid}_RueSaintPierre_Victorian",
                    coords_xy=coords,
                    height=16.4 if has_mansard else 15.6,
                    floor_height=3.7,
                    mat_wall=palette["Mat_MTL_Ochre_Victorian_Sandstone"] if has_mansard else palette["Mat_MTL_WarmBuff_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    mat_shop_glass=palette["Mat_MTL_Storefront_Warm_Interior"],
                    collection=proxy_col,
                    roof_style="mansard" if has_mansard else "cornice_flat",
                    arched_second_floor=True,
                    arched_ground_arcade=True,
                    dark_castiron_storefront=True,
                    bay_target_width=2.8,
                    detail_tier="high",
                )
            elif bid in (340057028, 340057029):
                build_detailed_facade_building(
                    name=f"MTL_Context_Proxy_{bid}_RueSaintPierre_Cream",
                    coords_xy=coords,
                    height=13.5,
                    floor_height=3.6,
                    mat_wall=palette["Mat_MTL_Indiana_Cream_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_Indiana_Cream_Limestone"],
                    collection=proxy_col,
                    roof_style="cornice_flat",
                    bay_target_width=3.1,
                    detail_tier="high",
                )
            elif bid in (339898461, 339898458, 339898460):
                # 4-story red-brown brick buildings behind the park in NotreDame_Ouest_Front.jpg
                build_detailed_facade_building(
                    name=f"MTL_Context_Proxy_{bid}_BrickRear",
                    coords_xy=coords,
                    height=15.8,
                    floor_height=3.7,
                    mat_wall=palette["Mat_MTL_Heritage_RedBrick"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=proxy_col,
                    roof_style="cornice_flat",
                    bay_target_width=3.2,
                    detail_tier="high",
                )
            else:
                h = (levels * 3.6) if levels else 18.0
                build_detailed_facade_building(
                    name=f"MTL_Context_Proxy_{bid}",
                    coords_xy=coords,
                    height=h,
                    floor_height=3.6,
                    mat_wall=palette["Mat_MTL_WarmBuff_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=proxy_col,
                    roof_style="cornice_flat",
                    bay_target_width=3.4,
                    detail_tier="high",
                )

    build_skyline_context_500_place_darmes(palette, proxy_col)
    add_rooftop_mechanical_details(palette, owned_col)
    place_polyhaven_trees_and_streetlamps(dossier, owned_col)

    print(f"Built {owned_count} Owned buildings in Block_{BLOCK_ID}_Owned and {proxy_count} Context Proxy buildings in Block_{BLOCK_ID}_Context_Proxy.")

    setup_world_and_lighting()
    render_cameras(dossier, iter_num=2)

    blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.blend")
    usdc_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.usdc")
    for stale in (blend_path + "@", blend_path + "1"):
        if os.path.exists(stale):
            try:
                os.remove(stale)
            except OSError:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.wm.usd_export(filepath=usdc_path, selected_objects_only=False)
    print(f"Saved {blend_path} and exported {usdc_path}")


if __name__ == "__main__":
    main()

