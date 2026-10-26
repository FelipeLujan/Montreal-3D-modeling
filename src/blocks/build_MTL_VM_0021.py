"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0021 (Iteration 2)
(Quai King-Edward & Montreal Science Centre Waterfront, 2 Rue de la Commune Ouest, Montréal, QC H2Y 4B2)
"""

import os
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import math
import shutil
import bpy
import bmesh
from mathutils import Vector

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0021"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
SNAPSHOT_PATH = os.path.join(BASE_DIR, "output", "renders", f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.usdc")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT_PATH), exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load_image_cached(path, non_color=False):
    if not path or not os.path.isfile(path):
        return None
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        try:
            img.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
    return img


def find_polyhaven_map(prefix, map_kind):
    candidates = []
    if map_kind == "diff":
        candidates = [f"{prefix}_Diffuse_2k.jpg", f"{prefix}_diff_2k.jpg", f"{prefix}_col_2k.jpg"]
    elif map_kind == "rough":
        candidates = [f"{prefix}_Rough_2k.jpg", f"{prefix}_rough_2k.jpg", f"{prefix}_Roughness_2k.jpg"]
    elif map_kind == "nor":
        candidates = [f"{prefix}_nor_gl_2k.jpg", f"{prefix}_nor_2k.jpg"]
    for cand in candidates:
        p1 = os.path.join(POLYHAVEN_DIR, cand)
        if os.path.isfile(p1):
            return p1
        p2 = os.path.join(POLYHAVEN_DIR, prefix, cand)
        if os.path.isfile(p2):
            return p2
    return ""


def apply_polyhaven_2k_pbr(mat, folder_prefix, scale_xyz=(0.25, 0.25, 0.25), tint_rgb=None, tint_factor=0.65, roughness_mult=1.0, normal_str=1.0):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(out.inputs["Surface"], bsdf.outputs["BSDF"])

    tcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = scale_xyz
    links.new(mapping.inputs["Vector"], tcoord.outputs["Object"])

    diff_img = load_image_cached(find_polyhaven_map(folder_prefix, "diff"), non_color=False)
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

    rough_img = load_image_cached(find_polyhaven_map(folder_prefix, "rough"), non_color=True)
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

    nor_img = load_image_cached(find_polyhaven_map(folder_prefix, "nor"), non_color=True)
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


def create_solid_material(name, color_rgba, roughness=0.5, metallic=0.0, ior=1.45, specular=0.5):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color_rgba
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = ior
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = specular
    return mat


def create_upgraded_palette():
    palette = kit.create_montreal_material_palette()

    # Poly Haven 2K PBR Ground & Masonry Materials
    apply_polyhaven_2k_pbr(palette["Mat_MTL_PierreGrise_Limestone"], "stone_brick_wall_001", (0.28, 0.28, 0.28), (0.68, 0.70, 0.72), 0.65, 0.90, 1.15)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_WarmBuff_Limestone"], "sandstone_blocks_05", (0.26, 0.26, 0.26), (0.86, 0.82, 0.74), 0.65, 0.90, 0.95)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Cobblestone"], "cobblestone_floor_08", (0.30, 0.30, 0.30), (0.64, 0.64, 0.62), 0.60, 0.92, 1.10)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Street_Asphalt"], "clean_asphalt", (0.18, 0.18, 0.18), (0.58, 0.56, 0.53), 0.50, 0.90, 0.85)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Plaza_Light_Granite"], "concrete_pavement_02", (0.20, 0.20, 0.20), (0.85, 0.81, 0.73), 0.62, 0.88, 0.65)

    # Lush Green Park Lawns (Mat_MTL_Grass_Lawn_PBR using leafy_grass_Diffuse_2k.jpg)
    mat_grass = bpy.data.materials.new("Mat_MTL_Grass_Lawn_PBR")
    apply_polyhaven_2k_pbr(mat_grass, "leafy_grass", (0.22, 0.22, 0.22), (0.42, 0.66, 0.28), 0.55, 0.95, 0.90)
    palette["Mat_MTL_Grass_Lawn_PBR"] = mat_grass

    # Stepped Granite Quay Bulkhead Wall & Coping Stones
    mat_quay = bpy.data.materials.new("Mat_MTL_Quay_Granite_Wall")
    apply_polyhaven_2k_pbr(mat_quay, "stone_block_wall", (0.22, 0.22, 0.22), (0.58, 0.57, 0.54), 0.72, 0.95, 1.35)
    palette["Mat_MTL_Quay_Granite_Wall"] = mat_quay

    # Dedicated 2K PBR St. Lawrence River Water Material (water_river_diffuse_2k.jpg, rough, nor_gl)
    mat_water = kit.get_or_create_water_pbr_material("Mat_MTL_River_Water", uv_scale=1.0)
    palette["Mat_MTL_River_Water"] = mat_water

    # Silver Standing-Seam & Corrugated Metal Cladding
    mat_silver_metal = bpy.data.materials.new("Mat_MTL_Silver_Metal")
    apply_polyhaven_2k_pbr(mat_silver_metal, "box_profile_metal_sheet", (0.35, 0.35, 0.35), (0.78, 0.81, 0.84), 0.60, 0.48, 0.75)
    bsdf_m = [n for n in mat_silver_metal.node_tree.nodes if n.type == "BSDF_PRINCIPLED"][0]
    bsdf_m.inputs["Metallic"].default_value = 0.72
    bsdf_m.inputs["Roughness"].default_value = 0.28
    palette["Mat_MTL_Silver_Metal"] = mat_silver_metal

    # Light Grey Weathered Shed Roof Membrane (matches Satellite Top-Down H2 & H5)
    mat_shed_roof = bpy.data.materials.new("Mat_MTL_Shed_Roof_LightGrey")
    apply_polyhaven_2k_pbr(mat_shed_roof, "concrete_pavement_02", (0.14, 0.14, 0.14), (0.73, 0.75, 0.77), 0.70, 0.88, 0.60)
    palette["Mat_MTL_Shed_Roof_LightGrey"] = mat_shed_roof

    # Bright White/Cream IMAX TELUS Roof & Facade Cladding (matches Satellite Top-Down H4..H5)
    mat_imax_white = bpy.data.materials.new("Mat_MTL_IMAX_White_Roof")
    apply_polyhaven_2k_pbr(mat_imax_white, "concrete_pavement_02", (0.18, 0.18, 0.18), (0.95, 0.94, 0.90), 0.82, 0.65, 0.35)
    palette["Mat_MTL_IMAX_White_Roof"] = mat_imax_white

    # Board-Formed Weathered Concrete Soffit for "LE BELVÉDÈRE" Overpass (matches H1..H3 of Crossing view)
    mat_soffit = bpy.data.materials.new("Mat_MTL_Belvedere_Concrete_Soffit")
    apply_polyhaven_2k_pbr(mat_soffit, "concrete_block_wall", (0.30, 0.30, 0.30), (0.68, 0.62, 0.52), 0.60, 0.85, 1.10)
    palette["Mat_MTL_Belvedere_Concrete_Soffit"] = mat_soffit

    # High-Specular Reflective Architectural Curtain-Wall Glass (reflects sky & clouds like Street View)
    glass_mat = palette["Mat_MTL_Window_Glass_Dark"]
    glass_mat.use_nodes = True
    gnodes = glass_mat.node_tree.nodes
    glinks = glass_mat.node_tree.links
    gnodes.clear()
    g_out = gnodes.new("ShaderNodeOutputMaterial")
    g_bsdf = gnodes.new("ShaderNodeBsdfPrincipled")
    g_bsdf.inputs["Base Color"].default_value = (0.14, 0.24, 0.30, 1.0)
    g_bsdf.inputs["Roughness"].default_value = 0.04
    g_bsdf.inputs["Metallic"].default_value = 0.25
    g_bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in g_bsdf.inputs:
        g_bsdf.inputs["Specular IOR Level"].default_value = 1.0
    glinks.new(g_out.inputs["Surface"], g_bsdf.outputs["BSDF"])

    # Additional Architectural & Prop Materials
    palette["Mat_MTL_Silver_Mullion"] = create_solid_material("Mat_MTL_Silver_Mullion", (0.68, 0.71, 0.74, 1.0), roughness=0.28, metallic=0.82)
    palette["Mat_MTL_Dark_Bronze_CurtainWall"] = create_solid_material("Mat_MTL_Dark_Bronze_CurtainWall", (0.18, 0.20, 0.22, 1.0), roughness=0.32, metallic=0.75)
    palette["Mat_MTL_IMAX_Charcoal_Zinc"] = create_solid_material("Mat_MTL_IMAX_Charcoal_Zinc", (0.58, 0.61, 0.64, 1.0), roughness=0.36, metallic=0.55)
    palette["Mat_MTL_CastIron_Black"] = create_solid_material("Mat_MTL_CastIron_Black", (0.06, 0.06, 0.07, 1.0), roughness=0.32, metallic=0.85)
    palette["Mat_MTL_Steel_Truss_Red"] = create_solid_material("Mat_MTL_Steel_Truss_Red", (0.82, 0.10, 0.10, 1.0), roughness=0.38, metallic=0.05)
    palette["Mat_MTL_Concrete_Structure"] = create_solid_material("Mat_MTL_Concrete_Structure", (0.74, 0.73, 0.69, 1.0), roughness=0.72, metallic=0.0)
    palette["Mat_MTL_Roof_Membrane"] = create_solid_material("Mat_MTL_Roof_Membrane", (0.28, 0.30, 0.32, 1.0), roughness=0.85, metallic=0.0)
    palette["Mat_MTL_Road_Marking_White"] = create_solid_material("Mat_MTL_Road_Marking_White", (0.94, 0.95, 0.96, 1.0), roughness=0.40)
    palette["Mat_MTL_Road_Marking_Yellow"] = create_solid_material("Mat_MTL_Road_Marking_Yellow", (0.95, 0.72, 0.08, 1.0), roughness=0.42)
    palette["Mat_MTL_Tower_Steel_Lattice"] = create_solid_material("Mat_MTL_Tower_Steel_Lattice", (0.20, 0.21, 0.19, 1.0), roughness=0.55, metallic=0.80)
    palette["Mat_MTL_Safety_Railing"] = create_solid_material("Mat_MTL_Safety_Railing", (0.62, 0.65, 0.68, 1.0), roughness=0.30, metallic=0.88)
    palette["Mat_MTL_Parking_Blue"] = create_solid_material("Mat_MTL_Parking_Blue", (0.08, 0.28, 0.62, 1.0), roughness=0.30, metallic=0.20)
    palette["Mat_MTL_Decalade_Banner"] = create_solid_material("Mat_MTL_Decalade_Banner", (0.10, 0.24, 0.22, 1.0), roughness=0.45, metallic=0.05)
    palette["Mat_MTL_Vessel_White"] = create_solid_material("Mat_MTL_Vessel_White", (0.94, 0.95, 0.96, 1.0), roughness=0.22, metallic=0.10)
    palette["Mat_MTL_Vessel_Navy"] = create_solid_material("Mat_MTL_Vessel_Navy", (0.06, 0.12, 0.24, 1.0), roughness=0.30, metallic=0.20)

    return palette


# --- Geometry & BMesh Helpers ---

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


def add_box_between(bm, p1, p2, z0, z1, thickness=0.35, offset_out=0.0, mat_idx=0, cap_top=True, cap_bot=True):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    seg_len = math.hypot(dx, dy)
    if seg_len < 1e-4 or z1 <= z0:
        return
    nx, ny = dy / seg_len, -dx / seg_len
    ht = thickness * 0.5
    ox, oy = nx * offset_out, ny * offset_out
    c = [
        (p1[0] + ox - nx * ht, p1[1] + oy - ny * ht),
        (p2[0] + ox - nx * ht, p2[1] + oy - ny * ht),
        (p2[0] + ox + nx * ht, p2[1] + oy + ny * ht),
        (p1[0] + ox + nx * ht, p1[1] + oy + ny * ht),
    ]
    v_bot = [bm.verts.new((x, y, z0)) for x, y in c]
    v_top = [bm.verts.new((x, y, z1)) for x, y in c]
    quads = [
        (v_bot[0], v_bot[1], v_top[1], v_top[0]),
        (v_bot[1], v_bot[2], v_top[2], v_top[1]),
        (v_bot[2], v_bot[3], v_top[3], v_top[2]),
        (v_bot[3], v_bot[0], v_top[0], v_top[3]),
    ]
    if cap_bot:
        quads.append((v_bot[3], v_bot[2], v_bot[1], v_bot[0]))
    if cap_top:
        quads.append((v_top[0], v_top[1], v_top[2], v_top[3]))
    for q in quads:
        try:
            f = bm.faces.new(q)
            f.material_index = mat_idx
        except ValueError:
            pass


def extrude_prism_in_bm(bm, pts, z0, z1, mat_side=0, mat_top=None, mat_bot=None):
    pts = ensure_ccw(pts)
    if len(pts) < 3 or z1 <= z0:
        return
    v_bot = [bm.verts.new((p[0], p[1], z0)) for p in pts]
    v_top = [bm.verts.new((p[0], p[1], z1)) for p in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        try:
            f = bm.faces.new((v_bot[i], v_bot[j], v_top[j], v_top[i]))
            f.material_index = mat_side
        except ValueError:
            pass
    if mat_top is not None:
        try:
            f_top = bm.faces.new(v_top)
            f_top.material_index = mat_top
        except ValueError:
            pass
    if mat_bot is not None:
        try:
            f_bot = bm.faces.new(list(reversed(v_bot)))
            f_bot.material_index = mat_bot
        except ValueError:
            pass


def add_cylinder_in_bm(bm, center_xy, z0, z1, r_bot, r_top, n_seg=16, mat_idx=0, cap_top=True, cap_bot=False):
    cx, cy = center_xy
    if z1 <= z0 or r_bot <= 0:
        return
    v_bot = []
    v_top = []
    for i in range(n_seg):
        th = (i / n_seg) * 2.0 * math.pi
        ct, st = math.cos(th), math.sin(th)
        v_bot.append(bm.verts.new((cx + r_bot * ct, cy + r_bot * st, z0)))
        v_top.append(bm.verts.new((cx + r_top * ct, cy + r_top * st, z1)))
    for i in range(n_seg):
        j = (i + 1) % n_seg
        try:
            f = bm.faces.new((v_bot[i], v_bot[j], v_top[j], v_top[i]))
            f.material_index = mat_idx
        except ValueError:
            pass
    if cap_top:
        try:
            f_top = bm.faces.new(v_top)
            f_top.material_index = mat_idx
        except ValueError:
            pass
    if cap_bot:
        try:
            f_bot = bm.faces.new(list(reversed(v_bot)))
            f_bot.material_index = mat_idx
        except ValueError:
            pass


def add_recessed_curtain_wall_bay(bm, p1, p2, z_sill, z_head, recess=0.48, mat_frame=0, mat_glass=1, mat_sill=2, n_panes=3, add_doors=False):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    bay_len = math.hypot(dx, dy)
    if bay_len < 0.60 or z_head <= z_sill:
        return
    ux, uy = dx / bay_len, dy / bay_len

    # Glass pane recessed inside bay
    add_box_between(bm, p1, p2, z_sill + 0.02, z_head - 0.02, thickness=0.08, offset_out=-0.05, mat_idx=mat_glass, cap_top=False, cap_bot=False)

    # Projecting Sill slab
    sp1 = (p1[0] - ux * 0.06, p1[1] - uy * 0.06)
    sp2 = (p2[0] + ux * 0.06, p2[1] + uy * 0.06)
    add_box_between(bm, sp1, sp2, z_sill - 0.18, z_sill, thickness=recess + 0.08, offset_out=recess * 0.45, mat_idx=mat_sill, cap_top=False)

    # Projecting Lintel slab
    add_box_between(bm, sp1, sp2, z_head, z_head + 0.20, thickness=recess + 0.06, offset_out=recess * 0.44, mat_idx=mat_sill, cap_top=False)

    # Projecting Jamb Pilasters
    jp1 = p1
    jp2 = (p1[0] + ux * 0.22, p1[1] + uy * 0.22)
    add_box_between(bm, jp1, jp2, z_sill, z_head, thickness=recess + 0.06, offset_out=recess * 0.45, mat_idx=mat_frame, cap_top=False, cap_bot=False)

    jp3 = (p2[0] - ux * 0.22, p2[1] - uy * 0.22)
    jp4 = p2
    add_box_between(bm, jp3, jp4, z_sill, z_head, thickness=recess + 0.06, offset_out=recess * 0.45, mat_idx=mat_frame, cap_top=False, cap_bot=False)

    # Vertical Mullions
    pane_w = (bay_len - 0.44) / n_panes
    for m in range(1, n_panes):
        mx = (p1[0] + ux * 0.22) + ux * (m * pane_w)
        my = (p1[1] + uy * 0.22) + uy * (m * pane_w)
        mp1 = (mx - ux * 0.04, my - uy * 0.04)
        mp2 = (mx + ux * 0.04, my + uy * 0.04)
        add_box_between(bm, mp1, mp2, z_sill, z_head, thickness=0.22, offset_out=0.08, mat_idx=mat_frame, cap_top=False, cap_bot=False)

    # Horizontal Transoms (multi-tier curtain wall grid as seen in Street View)
    h_span = z_head - z_sill
    if h_span > 2.2:
        for frac in (0.35, 0.70):
            zt = z_sill + h_span * frac
            add_box_between(bm, p1, p2, zt - 0.05, zt + 0.05, thickness=0.20, offset_out=0.08, mat_idx=mat_frame, cap_top=False, cap_bot=False)

    if add_doors:
        dp1 = (p1[0] + ux * (bay_len * 0.25), p1[1] + uy * (bay_len * 0.25))
        dp2 = (p1[0] + ux * (bay_len * 0.75), p1[1] + uy * (bay_len * 0.75))
        add_box_between(bm, dp1, dp2, z_sill, z_sill + 2.25, thickness=0.16, offset_out=0.05, mat_idx=mat_frame, cap_top=False, cap_bot=False)


def add_open_steel_lattice_pylon(bm, base_xy, z_base=0.15, z_peak=14.8, width=0.95, mat_steel=0, mat_banner=1):
    bx, by = base_xy
    hw = width * 0.5
    leg_th = 0.11

    corners = [
        (bx - hw, by - hw),
        (bx + hw, by - hw),
        (bx + hw, by + hw),
        (bx - hw, by + hw),
    ]

    # Concrete base plinth
    add_cylinder_in_bm(bm, (bx, by), 0.0, z_base + 0.45, hw * 1.15, hw * 1.05, n_seg=12, mat_idx=mat_steel, cap_top=True)

    for cx, cy in corners:
        lp1 = (cx - leg_th * 0.5, cy)
        lp2 = (cx + leg_th * 0.5, cy)
        add_box_between(bm, lp1, lp2, z_base, z_peak, thickness=leg_th, offset_out=0.0, mat_idx=mat_steel, cap_top=False)

    n_tiers = int((z_peak - z_base) / 2.0)
    for t in range(n_tiers):
        z0 = z_base + t * 2.0
        z1 = z0 + 2.0
        for i in range(4):
            c1 = corners[i]
            c2 = corners[(i + 1) % 4]
            add_box_between(bm, c1, c2, z0, z0 + 0.09, thickness=0.09, offset_out=0.0, mat_idx=mat_steel, cap_top=False)
            add_box_between(bm, c1, c2, z0, z1, thickness=0.06, offset_out=0.0, mat_idx=mat_steel, cap_top=False)

    # Vertical Vibrant Red Banner (#C62828) mounted on north/west side of mast
    bp1 = (bx - 0.45, by + hw + 0.05)
    bp2 = (bx + 0.45, by + hw + 0.05)
    add_box_between(bm, bp1, bp2, z_base + 4.5, z_base + 9.8, thickness=0.06, offset_out=0.0, mat_idx=mat_banner, cap_top=True)
    add_cylinder_in_bm(bm, (bx, by), z_peak, z_peak + 0.65, hw * 1.25, hw * 0.45, n_seg=12, mat_idx=mat_steel, cap_top=True)


# --- Building 46866809: Centre des sciences de Montréal & IMAX TELUS Pavilion ---

def build_science_centre_46866809(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_46866809_Centre_des_Sciences"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Silver_Metal"],             # 0: Silver metallic cladding & fascia
        palette["Mat_MTL_Window_Glass_Dark"],        # 1: Reflective sky-tinted curtain wall glass
        palette["Mat_MTL_Silver_Mullion"],           # 2: Silver aluminum curtain wall mullions
        palette["Mat_MTL_Concrete_Structure"],       # 3: Structural concrete plinth & columns
        palette["Mat_MTL_IMAX_Charcoal_Zinc"],       # 4: IMAX TELUS metallic facade panels
        palette["Mat_MTL_Shed_Roof_LightGrey"],      # 5: Light-grey industrial shed roof membrane
        palette["Mat_MTL_Steel_Truss_Red"],          # 6: Vibrant red banner accent
        palette["Mat_MTL_IMAX_White_Roof"],          # 7: Bright white/cream IMAX TELUS square roof
        palette["Mat_MTL_Grass_Lawn_PBR"],           # 8: Landscaped green rooftop planters
        palette["Mat_MTL_Dark_Bronze_CurtainWall"],  # 9: Dark anthracite pilasters & mechanical louvers
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Main shed height = 10.6m along North/South wings so roofline matches Street View H2..H4
    height_main = 10.60
    inner_core = inset_polygon_toward_centroid(pts, 0.96)
    extrude_prism_in_bm(bm, inner_core, 0.0, height_main, mat_side=0, mat_top=None)
    extrude_prism_in_bm(bm, pts, 0.0, 0.55, mat_side=3, mat_top=None)

    n = len(pts)
    bay_target_w = 3.8
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.0:
            add_box_between(bm, p1, p2, 0.0, height_main, thickness=0.50, offset_out=0.15, mat_idx=0, cap_top=False)
            continue

        ux, uy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / bay_target_w)))
        w_bay = seg_len / n_bays

        # Horizontal floor fascia & top silver aluminum cornice band
        add_box_between(bm, p1, p2, 4.10, 4.45, thickness=0.62, offset_out=0.30, mat_idx=0, cap_top=False)
        add_box_between(bm, p1, p2, height_main - 0.85, height_main + 0.35, thickness=0.68, offset_out=0.34, mat_idx=0, cap_top=True)

        for b in range(n_bays):
            bp1 = (p1[0] + ux * (b * w_bay), p1[1] + uy * (b * w_bay))
            bp2 = (p1[0] + ux * ((b + 1) * w_bay), p1[1] + uy * ((b + 1) * w_bay))

            add_recessed_curtain_wall_bay(bm, bp1, bp2, 0.55, 4.10, recess=0.50, mat_frame=2, mat_glass=1, mat_sill=3, n_panes=3, add_doors=(b % 2 == 0))
            add_recessed_curtain_wall_bay(bm, bp1, bp2, 4.45, height_main - 0.85, recess=0.48, mat_frame=2, mat_glass=1, mat_sill=0, n_panes=3)

    # Inset Light-Grey Main Shed Roof Membrane (matches Satellite Top-Down H5)
    inner_pts = inset_polygon_toward_centroid(pts, 0.94)
    extrude_prism_in_bm(bm, inner_pts, height_main - 0.20, height_main - 0.08, mat_side=5, mat_top=5)

    # Rooftop Circular & Square Exhaust Vents on West Wing (visible at X=410..420, Y=-6..-2 in satellite_topdown.png)
    add_cylinder_in_bm(bm, (411.2, -2.5), height_main - 0.08, height_main + 1.10, 1.35, 1.35, n_seg=16, mat_idx=7, cap_top=True)
    extrude_prism_in_bm(bm, [(409.5, -8.2), (412.5, -8.2), (412.5, -5.2), (409.5, -5.2)], height_main - 0.08, height_main + 0.90, mat_side=9, mat_top=7)
    extrude_prism_in_bm(bm, [(438.5, -6.5), (440.5, -6.5), (440.5, -4.5), (438.5, -4.5)], height_main - 0.08, height_main + 0.85, mat_side=7, mat_top=7)

    # --- Iconic IMAX TELUS Theater Volume & Mechanical Well (Exact Satellite Coordinates: X=442..477, Y=-18..+10) ---
    pier_dx, pier_dy = 0.9962, 0.0872
    norm_dx, norm_dy = -0.0872, 0.9962

    def pier_rect(x0, x1, y0_rel, y1_rel):
        base_x, base_y = 442.0, -21.0
        return [
            (base_x + x0 * pier_dx + y0_rel * norm_dx, base_y + x0 * pier_dy + y0_rel * norm_dy),
            (base_x + x1 * pier_dx + y0_rel * norm_dx, base_y + x1 * pier_dy + y0_rel * norm_dy),
            (base_x + x1 * pier_dx + y1_rel * norm_dx, base_y + x1 * pier_dy + y1_rel * norm_dy),
            (base_x + x0 * pier_dx + y1_rel * norm_dx, base_y + x0 * pier_dy + y1_rel * norm_dy),
        ]

    # 1. West HVAC Mechanical Well (X_rel = 0..9.5m, Y_rel = 2..28m)
    mech_outer = pier_rect(0.0, 9.5, 2.0, 28.5)
    extrude_prism_in_bm(bm, mech_outer, height_main - 0.08, 13.80, mat_side=4, mat_top=7)
    mech_inner = pier_rect(1.2, 8.3, 3.2, 27.3)
    extrude_prism_in_bm(bm, mech_inner, 13.80, 14.15, mat_side=9, mat_top=9)
    for m_y in (6.0, 12.0, 18.0, 23.5):
        chiller = pier_rect(2.2, 7.2, m_y, m_y + 3.8)
        extrude_prism_in_bm(bm, chiller, 14.15, 15.60, mat_side=0, mat_top=7)

    # 2. Main IMAX TELUS Cube (X_rel = 9.5..35.5m -> X=451.5..477.5, Y_rel = 2.0..29.5m)
    imax_pts = pier_rect(9.5, 35.5, 2.0, 29.5)
    extrude_prism_in_bm(bm, imax_pts, 0.0, 16.20, mat_side=4, mat_top=None)
    for k in range(4):
        cp1, cp2 = imax_pts[k], imax_pts[(k + 1) % 4]
        add_box_between(bm, cp1, cp2, 15.80, 16.55, thickness=0.65, offset_out=0.25, mat_idx=7, cap_top=True)
    # Bright White/Cream IMAX Square Roof (inset 0.35m, Z = 16.35m)
    imax_roof = inset_polygon_toward_centroid(imax_pts, 0.95)
    extrude_prism_in_bm(bm, imax_roof, 16.10, 16.38, mat_side=7, mat_top=7)

    # 3. Glazed Cylindrical/Faceted IMAX Entrance Rotunda on North Plaza (X=434..450, Y=7..14)
    add_cylinder_in_bm(bm, (441.5, 9.2), 0.0, 12.20, 5.2, 5.2, n_seg=18, mat_idx=1, cap_top=False)
    add_cylinder_in_bm(bm, (441.5, 9.2), 12.20, 12.85, 5.5, 5.5, n_seg=18, mat_idx=0, cap_top=True)

    # 4. South IMAX TELUS Stepped Fascia & Promenade Pergola Frame
    imax_south = pier_rect(9.0, 35.8, -1.8, 2.2)
    extrude_prism_in_bm(bm, imax_south, 0.0, 12.40, mat_side=7, mat_top=7)
    canopy_p1 = (380.0, -26.8)
    canopy_p2 = (530.0, -13.6)
    add_box_between(bm, canopy_p1, canopy_p2, 3.80, 4.15, thickness=2.4, offset_out=1.2, mat_idx=0, cap_top=True)

    # 5. Signature Promenade Light Pylons with Red Banners along North Sidewalk (matching Street View + Satellite shadows)
    pylon_line_p1 = (394.0, 8.2)
    pylon_line_p2 = (522.0, 19.3)
    dx_l = pylon_line_p2[0] - pylon_line_p1[0]
    dy_l = pylon_line_p2[1] - pylon_line_p1[1]
    n_pylons = 10
    for pi in range(n_pylons):
        frac = pi / (n_pylons - 1)
        px = pylon_line_p1[0] + dx_l * frac
        py = pylon_line_p1[1] + dy_l * frac
        add_open_steel_lattice_pylon(bm, (px, py), z_base=0.15, z_peak=14.6, width=0.92, mat_steel=2, mat_banner=6)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Building 46866806: O'Quai Bistro (North Entrance Waterfront Building) ---

def build_o_quai_bistro_46866806(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_46866806_O_Quai_Bistro"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Silver_Metal"],             # 0: Silver aluminum fascia & upper trim
        palette["Mat_MTL_Window_Glass_Dark"],        # 1: Reflective storefront & clerestory glass
        palette["Mat_MTL_Silver_Mullion"],           # 2: Crisp light-silver aluminum window frames
        palette["Mat_MTL_Concrete_Structure"],       # 3: Precast concrete columns & terrace slab
        palette["Mat_MTL_Shed_Roof_LightGrey"],      # 4: Light-grey industrial roof membrane
        palette["Mat_MTL_Safety_Railing"],           # 5: Terrace guardrail balustrade
        palette["Mat_MTL_Steel_Truss_Red"],          # 6: Red circular entrance sign badge
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Exact 2-level height (7.60m) so H1..H2 shows blue sky in Quai_King_Edward_North_Entrance
    height = 7.60
    inner_core = inset_polygon_toward_centroid(pts, 0.94)
    extrude_prism_in_bm(bm, inner_core, 0.0, height, mat_side=3, mat_top=None)
    extrude_prism_in_bm(bm, pts, 0.0, 0.35, mat_side=3, mat_top=None)

    n = len(pts)
    bay_target_w = 3.6
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.0:
            add_box_between(bm, p1, p2, 0.0, height, thickness=0.50, offset_out=0.15, mat_idx=3, cap_top=False)
            continue

        ux, uy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / bay_target_w)))
        w_bay = seg_len / n_bays

        # Prominent Precast Concrete Overhanging Terrace Slab & Fascia Band at Z = 3.85m..4.65m (H3..H4 in North_Entrance)
        add_box_between(bm, p1, p2, 3.85, 4.65, thickness=2.0, offset_out=0.95, mat_idx=3, cap_top=True)
        # Terrace Railing at Z = 4.65m..5.45m
        add_box_between(bm, p1, p2, 4.65, 5.45, thickness=0.08, offset_out=1.80, mat_idx=5, cap_top=False)
        # Upper Roof Cornice Trim at Z = 7.25m..7.75m
        add_box_between(bm, p1, p2, height - 0.35, height + 0.15, thickness=0.75, offset_out=0.30, mat_idx=0, cap_top=True)

        for b in range(n_bays):
            bp1 = (p1[0] + ux * (b * w_bay), p1[1] + uy * (b * w_bay))
            bp2 = (p1[0] + ux * ((b + 1) * w_bay), p1[1] + uy * ((b + 1) * w_bay))

            # Ground floor multi-pane curtain wall with entrance doors
            add_recessed_curtain_wall_bay(bm, bp1, bp2, 0.35, 3.85, recess=0.48, mat_frame=2, mat_glass=1, mat_sill=3, n_panes=3, add_doors=True)

            # Structural concrete column along colonnade
            cp1 = (bp1[0] - ux * 0.20, bp1[1] - uy * 0.20)
            cp2 = (bp1[0] + ux * 0.20, bp1[1] + uy * 0.20)
            add_box_between(bm, cp1, cp2, 0.0, 3.85, thickness=0.42, offset_out=0.45, mat_idx=3, cap_top=False)

            # Upper Clerestory Ribbon Window Band (Z = 4.75m..7.20m)
            add_recessed_curtain_wall_bay(bm, bp1, bp2, 4.75, 7.20, recess=0.45, mat_frame=2, mat_glass=1, mat_sill=3, n_panes=3)

    # Red Circular Bistro Signage Badge on South Facade (visible at V4/V5 in Quai_King_Edward_North_Entrance)
    add_box_between(bm, (394.6, 31.5), (395.5, 31.6), 2.95, 3.80, thickness=0.25, offset_out=1.95, mat_idx=6, cap_top=True)

    # Inset Light-Grey Roof Membrane & Rooftop Mechanical Vents (visible in Satellite Top-Down H1..H2, V1..V2)
    inner_pts = inset_polygon_toward_centroid(pts, 0.92)
    extrude_prism_in_bm(bm, inner_pts, height - 0.18, height - 0.06, mat_side=4, mat_top=4)
    for vx, vy in [(396.0, 44.0), (402.0, 48.0), (408.0, 45.0), (414.0, 50.0)]:
        add_cylinder_in_bm(bm, (vx, vy), height - 0.06, height + 0.55, 0.45, 0.45, n_seg=10, mat_idx=0, cap_top=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Building 161202894: "LE BELVÉDÈRE" Concrete Viaduct Overpass & Entrance Portal ---

def build_skybridge_161202894(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_161202894_Skybridge_Belvedere"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Silver_Metal"],                # 0: Silver metal roof cap
        palette["Mat_MTL_Window_Glass_Dark"],           # 1: Curtain wall glass
        palette["Mat_MTL_Silver_Mullion"],              # 2: Silver window frames & doors
        palette["Mat_MTL_Belvedere_Concrete_Soffit"],   # 3: Warm board-formed concrete soffit & beams
        palette["Mat_MTL_Concrete_Structure"],          # 4: Cylindrical concrete columns
        palette["Mat_MTL_Road_Marking_White"],          # 5: "LE BELVÉDÈRE" raised signage letters
        palette["Mat_MTL_Road_Marking_Yellow"],         # 6: Yellow traffic clearance sign
        palette["Mat_MTL_Steel_Truss_Red"],             # 7: Red signage accent on column
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Expand canopy footprint slightly west & north so camera (375.986, 15.268, 1.75) looking at 335.9 deg
    # sees the full concrete soffit & longitudinal/transverse beams across H1..H3 (V1..V8)!
    deck_pts = [
        (365.5, 1.5),
        (381.8, 2.2),
        (379.5, 30.2),
        (363.8, 29.0),
    ]
    extrude_prism_in_bm(bm, deck_pts, 4.95, 5.55, mat_side=3, mat_top=3, mat_bot=3)

    # Longitudinal Concrete Girders underneath soffit (running South-to-North, visible in H1..H3)
    for gx_bot, gx_top in [(366.8, 365.0), (370.8, 369.0), (374.8, 373.0), (378.8, 377.0)]:
        add_box_between(bm, (gx_bot, 2.0), (gx_top, 26.5), 4.45, 4.98, thickness=0.55, offset_out=0.0, mat_idx=3, cap_top=False, cap_bot=True)

    # Transverse Concrete Cross-Beams & "LE BELVÉDÈRE" Portal Fascia Beam at Y = 22.8m
    for gy in (12.0, 17.5, 22.8, 26.5):
        z_low = 4.25 if abs(gy - 22.8) < 0.5 else 4.50
        add_box_between(bm, (364.5, gy - 0.5), (380.5, gy + 0.8), z_low, 5.15, thickness=0.65, offset_out=0.0, mat_idx=3, cap_top=False, cap_bot=True)

    # 3D Raised White Lettering Strip for "LE BELVÉDÈRE ->" on South Face of Beam at Y = 22.4m (V5..V8, H3)
    for li in range(12):
        lx = 373.2 + li * 0.36
        ly = 22.15 + li * 0.03
        add_box_between(bm, (lx, ly), (lx + 0.22, ly + 0.02), 4.48, 4.76, thickness=0.12, offset_out=0.0, mat_idx=5, cap_top=True, cap_bot=True)

    # Cylindrical Concrete Support Columns at V2 (left) and V4/V7 (center-right) matching Street View
    col_positions = [
        (368.8, 21.8, 0.42),
        (373.5, 22.2, 0.44),
        (378.4, 22.7, 0.44),
        (369.8, 11.5, 0.42),
        (379.2, 12.2, 0.42),
    ]
    for cx, cy, rad in col_positions:
        add_cylinder_in_bm(bm, (cx, cy), 0.0, 4.95, rad, rad, n_seg=16, mat_idx=4, cap_top=False, cap_bot=False)

    # Yellow Clearance Sign & Red Column Panel on Center Column (373.5, 22.2)
    add_box_between(bm, (373.1, 21.7), (373.9, 21.75), 2.10, 3.20, thickness=0.12, offset_out=0.0, mat_idx=7, cap_top=True)
    add_box_between(bm, (368.4, 21.3), (369.1, 21.35), 2.40, 3.10, thickness=0.10, offset_out=0.0, mat_idx=6, cap_top=True)

    # Ground-Floor Glazed Entrance Lobby on Right Side (V4..V8, H4..H6 in Rue_de_la_Commune_Science_Crossing)
    lobby_edges = [
        ((373.5, 22.2), (379.5, 22.8)),
        ((379.5, 22.8), (378.8, 30.2)),
        ((373.5, 22.2), (372.8, 29.8)),
    ]
    for lp1, lp2 in lobby_edges:
        add_recessed_curtain_wall_bay(bm, lp1, lp2, 0.15, 4.30, recess=0.45, mat_frame=2, mat_glass=1, mat_sill=4, n_panes=4, add_doors=True)

    # Upper Enclosed Glass Gallery (Z = 5.55m .. 7.80m)
    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 0.8:
            continue
        add_recessed_curtain_wall_bay(bm, p1, p2, 5.55, 7.60, recess=0.45, mat_frame=2, mat_glass=1, mat_sill=3, n_panes=max(1, int(seg_len / 2.5)))
        add_box_between(bm, p1, p2, 7.60, 7.95, thickness=0.55, offset_out=0.15, mat_idx=0, cap_top=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Buildings 263735643 & 263735648: Historic King Edward Maritime Pier Sheds ---

def build_historic_pier_shed(bldg_data, palette, collection, prefix, height=10.50):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    bid = bldg_data["id"]
    name = f"MTL_Owned_{bid}_{prefix}"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Silver_Metal"],             # 0: Corrugated silver metal cladding
        palette["Mat_MTL_Window_Glass_Dark"],        # 1: Multi-pane clerestory & arcade glass
        palette["Mat_MTL_Silver_Mullion"],           # 2: Steel mullions & frames
        palette["Mat_MTL_Concrete_Structure"],       # 3: Heavy concrete dock plinth, columns & courtyard walls
        palette["Mat_MTL_Dark_Bronze_CurtainWall"],  # 4: Open steel rafters & cargo shutters
        palette["Mat_MTL_Shed_Roof_LightGrey"],      # 5: Light-grey flat shed roof membrane
        palette["Mat_MTL_Safety_Railing"],           # 6: Terrace railing
        palette["Mat_MTL_IMAX_White_Roof"],          # 7: Skylight panels & courtyard kiosk roof
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    if bid == 263735643:
        # North Shed has two distinct sectors in Satellite Top-Down (H1..H2):
        # 1) Open-Air Structural Steel Rafter Courtyard at X = 424.0..446.5, Y = 30.0..66.0 (V3..V4 in Satellite)
        # 2) Enclosed Light-Grey Standing-Seam Roof Shed from X = 446.5..714.0 (V4..V8 in Satellite)
        pier_dx, pier_dy = 0.9962, 0.0872
        norm_dx, norm_dy = -0.0872, 0.9962

        def north_rect(x0, x1, y0_rel, y1_rel):
            bx, by = 424.0, 30.2
            return [
                (bx + x0 * pier_dx + y0_rel * norm_dx, by + x0 * pier_dy + y0_rel * norm_dy),
                (bx + x1 * pier_dx + y0_rel * norm_dx, by + x1 * pier_dy + y0_rel * norm_dy),
                (bx + x1 * pier_dx + y1_rel * norm_dx, by + x1 * pier_dy + y1_rel * norm_dy),
                (bx + x0 * pier_dx + y1_rel * norm_dx, by + x0 * pier_dy + y1_rel * norm_dy),
            ]

        # Open Courtyard Perimeter Walls & Central White Kiosk (X_rel = 0..22.5m -> X = 424..446.5)
        court_walls = north_rect(0.0, 22.5, 0.0, 33.8)
        for k in range(4):
            cp1, cp2 = court_walls[k], court_walls[(k + 1) % 4]
            add_box_between(bm, cp1, cp2, 0.0, height, thickness=0.65, offset_out=0.0, mat_idx=3, cap_top=True)
        # Central Recessed Courtyard Framing & White Elevator Kiosk (clearly visible in Satellite V3..V4, H1..H2)
        inner_wall = north_rect(4.5, 18.0, 5.5, 28.5)
        for k in range(4):
            cp1, cp2 = inner_wall[k], inner_wall[(k + 1) % 4]
            add_box_between(bm, cp1, cp2, 0.0, height - 1.2, thickness=0.50, offset_out=0.0, mat_idx=3, cap_top=True)
        kiosk_pts = north_rect(8.5, 12.2, 13.0, 23.0)
        extrude_prism_in_bm(bm, kiosk_pts, 0.0, height + 0.5, mat_side=7, mat_top=7)

        # Open Structural Steel Roof Truss Grid over X_rel = 0..22.5m
        for rx in range(0, 23, 2):
            rp1 = (424.0 + rx * pier_dx, 30.2 + rx * pier_dy)
            rp2 = (rp1[0] + 33.8 * norm_dx, rp1[1] + 33.8 * norm_dy)
            add_box_between(bm, rp1, rp2, height - 0.35, height, thickness=0.22, offset_out=0.0, mat_idx=4, cap_top=True)
        for ry in range(0, 35, 4):
            rp1 = (424.0 + ry * norm_dx, 30.2 + ry * norm_dy)
            rp2 = (rp1[0] + 22.5 * pier_dx, rp1[1] + 22.5 * pier_dy)
            add_box_between(bm, rp1, rp2, height - 0.55, height - 0.15, thickness=0.25, offset_out=0.0, mat_idx=4, cap_top=True)

        # East Main Shed Volume (X_rel = 22.5..288.0m -> X = 446.5..712.0)
        east_shed = north_rect(22.5, 288.0, 0.0, 33.8)
        extrude_prism_in_bm(bm, east_shed, 0.0, height, mat_side=0, mat_top=None)
        east_roof = inset_polygon_toward_centroid(east_shed, 0.97)
        extrude_prism_in_bm(bm, east_roof, height - 0.18, height - 0.05, mat_side=5, mat_top=5)

        # Rectangular Skylight Strips on North Shed Roof (visible in Satellite Top-Down H1..H2, V4..V8)
        for sx in range(30, 280, 12):
            sky_pts = north_rect(sx, sx + 1.8, 9.0, 22.0)
            extrude_prism_in_bm(bm, sky_pts, height - 0.05, height + 0.18, mat_side=4, mat_top=7)
    else:
        inner_core = inset_polygon_toward_centroid(pts, 0.96)
        extrude_prism_in_bm(bm, inner_core, 0.0, height, mat_side=0, mat_top=None)
        extrude_prism_in_bm(bm, pts, 0.0, 0.85, mat_side=3, mat_top=None)
        inner_pts = inset_polygon_toward_centroid(pts, 0.95)
        extrude_prism_in_bm(bm, inner_pts, height - 0.20, height - 0.06, mat_side=5, mat_top=5)

    # Articulate Perimeter Facades with Recessed Curtain Walls, Columns & Canopies
    n = len(pts)
    bay_target_w = 5.5
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.0:
            continue

        ux, uy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / bay_target_w)))
        w_bay = seg_len / n_bays

        add_box_between(bm, p1, p2, 4.10, 4.50, thickness=1.5, offset_out=0.75, mat_idx=3, cap_top=True)
        add_box_between(bm, p1, p2, height - 0.30, height + 0.25, thickness=0.65, offset_out=0.25, mat_idx=0, cap_top=True)

        for b in range(n_bays):
            bp1 = (p1[0] + ux * (b * w_bay), p1[1] + uy * (b * w_bay))
            bp2 = (p1[0] + ux * ((b + 1) * w_bay), p1[1] + uy * ((b + 1) * w_bay))

            cp1 = (bp1[0] - ux * 0.22, bp1[1] - uy * 0.22)
            cp2 = (bp1[0] + ux * 0.22, bp1[1] + uy * 0.22)
            add_box_between(bm, cp1, cp2, 0.0, 4.10, thickness=0.48, offset_out=0.35, mat_idx=3, cap_top=False)

            add_recessed_curtain_wall_bay(bm, bp1, bp2, 0.65, 4.05, recess=0.50, mat_frame=2, mat_glass=1, mat_sill=3, n_panes=3, add_doors=True)
            add_recessed_curtain_wall_bay(bm, bp1, bp2, 4.65, height - 0.55, recess=0.48, mat_frame=2, mat_glass=1, mat_sill=0, n_panes=4)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Building 1248578233: Open-Lattice Marine Conveyor / Décalade Tower ---

def build_decalade_tower_1248578233(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_1248578233_Marine_Elevator_Tower"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Tower_Steel_Lattice"],       # 0: Dark weathered structural steel lattice
        palette["Mat_MTL_Silver_Metal"],              # 1: Upper corrugated metal cladding & headhouse
        palette["Mat_MTL_Window_Glass_Dark"],         # 2: Observation windows
        palette["Mat_MTL_Concrete_Structure"],        # 3: Concrete pier base
        palette["Mat_MTL_Decalade_Banner"],           # 4: "DECALADE.COM" banner sign at base
        palette["Mat_MTL_Road_Marking_Yellow"],       # 5: Yellow banner lettering & accents
        palette["Mat_MTL_Steel_Truss_Red"],           # 6: Colorful glazing & climbing wall accents
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    extrude_prism_in_bm(bm, pts, -2.50, 0.35, mat_side=3, mat_top=3)

    height_tower = 51.0
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    corners = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]

    # 1. Open Structural Steel Lattice Legs & Cross-Bracing (Z = 0.35m .. 34.5m — see-through steel truss!)
    for cx, cy in corners:
        p1 = (cx - 0.38, cy)
        p2 = (cx + 0.38, cy)
        add_box_between(bm, p1, p2, 0.35, height_tower, thickness=0.76, offset_out=0.0, mat_idx=0, cap_top=False)
    # Intermediate vertical truss columns on each face
    for i in range(4):
        c1, c2 = corners[i], corners[(i + 1) % 4]
        mx, my = 0.5 * (c1[0] + c2[0]), 0.5 * (c1[1] + c2[1])
        add_box_between(bm, (mx - 0.22, my), (mx + 0.22, my), 0.35, 36.0, thickness=0.44, offset_out=0.0, mat_idx=0, cap_top=False)

    n_tiers = 16
    dz = (35.0 - 0.35) / n_tiers
    for t in range(n_tiers):
        z0 = 0.35 + t * dz
        z1 = z0 + dz
        for i in range(4):
            c1 = corners[i]
            c2 = corners[(i + 1) % 4]
            # Horizontal girder
            add_box_between(bm, c1, c2, z0, z0 + 0.32, thickness=0.38, offset_out=0.0, mat_idx=0, cap_top=False)
            # X-bracing diagonals
            p_top_a = (c1[0], c1[1])
            p_bot_b = (c2[0], c2[1])
            for step in range(5):
                f0 = step / 5.0
                f1 = (step + 1) / 5.0
                sx0 = c1[0] + (c2[0] - c1[0]) * f0
                sy0 = c1[1] + (c2[1] - c1[1]) * f0
                sx1 = c1[0] + (c2[0] - c1[0]) * f1
                sy1 = c1[1] + (c2[1] - c1[1]) * f1
                add_box_between(bm, (sx0, sy0), (sx1, sy1), z0 + f0 * dz, z0 + f1 * dz, thickness=0.22, offset_out=0.0, mat_idx=0, cap_top=False)
                add_box_between(bm, (sx1, sy1), (sx0, sy0), z0 + f0 * dz, z0 + f1 * dz, thickness=0.22, offset_out=0.0, mat_idx=0, cap_top=False)

    # Slender internal stair/conveyor shaft with colorful climbing/glazing accents (leaves outer lattice open to sky!)
    cx_t = 0.5 * (x_min + x_max)
    cy_t = 0.5 * (y_min + y_max)
    core_box = [(cx_t - 2.2, cy_t - 2.2), (cx_t + 2.2, cy_t - 2.2), (cx_t + 2.2, cy_t + 2.2), (cx_t - 2.2, cy_t + 2.2)]
    extrude_prism_in_bm(bm, core_box, 0.35, 34.5, mat_side=0, mat_top=None)
    # Colorful red/yellow abseiling / Décalade accent panels on tower shaft
    add_box_between(bm, (x_min, y_min + 2.0), (x_min, y_max - 2.0), 14.0, 26.0, thickness=0.18, offset_out=0.10, mat_idx=6, cap_top=True)

    # 2. Upper Cladded Machinery House & Sloped Top Headhouse (Z = 34.5m .. 51.5m, matching V6..V7, H2..H3)
    upper_box = [
        (x_min + 0.4, y_min + 0.4),
        (x_max - 0.4, y_min + 0.4),
        (x_max - 0.4, y_max - 0.4),
        (x_min + 0.4, y_max - 0.4),
    ]
    extrude_prism_in_bm(bm, upper_box, 34.5, 45.5, mat_side=0, mat_top=None)
    cab_box = [
        (x_min - 0.4, y_min - 0.4),
        (x_max + 0.4, y_min - 0.4),
        (x_max + 0.4, y_max + 0.4),
        (x_min - 0.4, y_max + 0.4),
    ]
    extrude_prism_in_bm(bm, cab_box, 45.5, 51.2, mat_side=1, mat_top=1)
    for i in range(4):
        cp1, cp2 = cab_box[i], cab_box[(i + 1) % 4]
        add_recessed_curtain_wall_bay(bm, cp1, cp2, 46.8, 49.8, recess=0.40, mat_frame=0, mat_glass=2, mat_sill=1, n_panes=3)

    # 3. "DECALADE.COM" Banner & Security Fence at Base of Tower (V5..V8, H5..H6 in Quai_King_Edward_Pier_Tip)
    ban_p1 = (497.5, -116.5)
    ban_p2 = (504.5, -108.5)
    add_box_between(bm, ban_p1, ban_p2, 0.85, 2.45, thickness=0.12, offset_out=0.0, mat_idx=4, cap_top=True)
    # Yellow "DECALADE.COM" lettering strip across banner
    add_box_between(bm, (498.0, -116.0), (504.0, -109.0), 1.85, 2.25, thickness=0.16, offset_out=0.0, mat_idx=5, cap_top=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Generic Pavilion & Canopy (440195626, 1445521129, 263735642) ---

def build_pavilion_or_canopy(bldg_data, palette, collection, prefix, height=5.50, is_canopy=False):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    bid = bldg_data["id"]
    name = f"MTL_Owned_{bid}_{prefix}"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Silver_Metal"],             # 0: Metal roof cap
        palette["Mat_MTL_Dark_Bronze_CurtainWall"],  # 1: Structural columns
        palette["Mat_MTL_Window_Glass_Dark"],        # 2: Glass
        palette["Mat_MTL_Shed_Roof_LightGrey"],      # 3: Roof membrane
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    if is_canopy:
        n = len(pts)
        for i in range(n):
            p = pts[i]
            p1 = (p[0] - 0.20, p[1])
            p2 = (p[0] + 0.20, p[1])
            add_box_between(bm, p1, p2, 0.0, height - 0.35, thickness=0.40, offset_out=0.0, mat_idx=1, cap_top=False)
        extrude_prism_in_bm(bm, pts, height - 0.35, height, mat_side=0, mat_top=0, mat_bot=0)
    else:
        extrude_prism_in_bm(bm, pts, 0.0, height, mat_side=0, mat_top=None)
        n = len(pts)
        for i in range(n):
            p1, p2 = pts[i], pts[(i + 1) % n]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len > 1.2:
                add_recessed_curtain_wall_bay(bm, p1, p2, 0.80, height - 0.80, recess=0.45, mat_frame=1, mat_glass=2, mat_sill=0, n_panes=max(1, int(seg_len / 3.0)))
            add_box_between(bm, p1, p2, height - 0.20, height + 0.30, thickness=0.55, offset_out=0.15, mat_idx=0, cap_top=True)
        inner_pts = inset_polygon_toward_centroid(pts, 0.88)
        extrude_prism_in_bm(bm, inner_pts, height - 0.22, height - 0.10, mat_side=3, mat_top=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Wave-Rippled 2K PBR Water Basins, Stepped Granite Quays, Promenade Lawns, Vessels & Parked Cars ---

def build_water_mesh(collection_owned, palette):
    """Creates a subdivided, wave-rippled 2K PBR water surface at Z = -2.20m with 15m metric UV tiling."""
    mesh = bpy.data.meshes.new(f"MTL_Owned_StLawrence_Water_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"MTL_Owned_StLawrence_Water_{BLOCK_ID}", mesh)
    collection_owned.objects.link(obj)
    obj.data.materials.append(palette["Mat_MTL_River_Water"])

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Grid covering all harbor basins & St. Lawrence channel around Quai King-Edward
    x_min, x_max = 260.0, 920.0
    y_min, y_max = -240.0, 220.0
    nx, ny = 88, 64
    dx = (x_max - x_min) / nx
    dy = (y_max - y_min) / ny

    verts = []
    for j in range(ny + 1):
        row = []
        y = y_min + j * dy
        for i in range(nx + 1):
            x = x_min + i * dx
            # Subtle wave-displaced ripples around Z = -2.20m
            z = -2.20 + 0.055 * math.sin(x * 0.22 + y * 0.14) + 0.035 * math.cos(x * 0.37 - y * 0.29)
            row.append(bm.verts.new((x, y, z)))
        verts.append(row)

    for j in range(ny):
        for i in range(nx):
            v00 = verts[j][i]
            v10 = verts[j][i + 1]
            v11 = verts[j + 1][i + 1]
            v01 = verts[j + 1][i]
            f = bm.faces.new((v00, v10, v11, v01))
            f.material_index = 0
            f.smooth = True
            for loop in f.loops:
                co = loop.vert.co
                loop[uv_layer].uv = (co.x / 15.0, co.y / 15.0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    return obj


def add_moored_vessel(bm, center_xy, length, beam, heading_rad, mat_hull, mat_cabin, mat_glass, mat_deck):
    """Builds an articulated moored harbor excursion vessel / tugboat in the water basin."""
    cx, cy = center_xy
    ca, sa = math.cos(heading_rad), math.sin(heading_rad)

    def to_world(lx, ly):
        return (cx + lx * ca - ly * sa, cy + lx * sa + ly * ca)

    hl = length * 0.5
    hb = beam * 0.5
    hull_pts = [
        to_world(-hl, -hb * 0.82),
        to_world(hl * 0.65, -hb),
        to_world(hl, 0.0),
        to_world(hl * 0.65, hb),
        to_world(-hl, hb * 0.82),
    ]
    extrude_prism_in_bm(bm, hull_pts, -2.30, 0.65, mat_side=mat_hull, mat_top=mat_deck)

    cabin_pts = [
        to_world(-hl * 0.72, -hb * 0.72),
        to_world(hl * 0.45, -hb * 0.72),
        to_world(hl * 0.45, hb * 0.72),
        to_world(-hl * 0.72, hb * 0.72),
    ]
    extrude_prism_in_bm(bm, cabin_pts, 0.65, 3.10, mat_side=mat_cabin, mat_top=mat_cabin)
    extrude_prism_in_bm(bm, inset_polygon_toward_centroid(cabin_pts, 1.02), 1.40, 2.55, mat_side=mat_glass, mat_top=None)

    bridge_pts = [
        to_world(-hl * 0.35, -hb * 0.55),
        to_world(hl * 0.30, -hb * 0.55),
        to_world(hl * 0.30, hb * 0.55),
        to_world(-hl * 0.35, hb * 0.55),
    ]
    extrude_prism_in_bm(bm, bridge_pts, 3.10, 5.10, mat_side=mat_cabin, mat_top=mat_cabin)
    extrude_prism_in_bm(bm, inset_polygon_toward_centroid(bridge_pts, 1.02), 3.70, 4.70, mat_side=mat_glass, mat_top=None)


def build_ground_quays_and_water(dossier, palette, collection_owned):
    build_water_mesh(collection_owned, palette)

    mesh = bpy.data.meshes.new(f"MTL_Owned_Ground_Quays_And_Promenade_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"MTL_Owned_Ground_Quays_And_Promenade_{BLOCK_ID}", mesh)
    collection_owned.objects.link(obj)

    materials = [
        palette["Mat_MTL_Street_Asphalt"],           # 0: Roadway asphalt
        palette["Mat_MTL_Cobblestone"],              # 1: Pier cobblestone & granite paving
        palette["Mat_MTL_Plaza_Light_Granite"],      # 2: Warm light-buff concrete sidewalks & plazas
        palette["Mat_MTL_Quay_Granite_Wall"],        # 3: Stepped granite quay bulkhead & coping
        palette["Mat_MTL_Grass_Lawn_PBR"],           # 4: Promenade du Vieux-Port green grass lawns
        palette["Mat_MTL_Road_Marking_White"],       # 5: Painted crosswalks, arrows & stall lines
        palette["Mat_MTL_Road_Marking_Yellow"],      # 6: Painted yellow centerlines & toll islands
        palette["Mat_MTL_Safety_Railing"],           # 7: Quayside safety railings & wire fences
        palette["Mat_MTL_CastIron_Black"],           # 8: Cast-iron mooring bollards & dark cars
        palette["Mat_MTL_Warm_Timber"],              # 9: Timber boardwalk & wooden pier benches
        palette["Mat_MTL_Parking_Blue"],             # 10: Blue parking ticket kiosks & cars
        palette["Mat_MTL_Vessel_White"],             # 11: White excursion vessel superstructure & white cars
        palette["Mat_MTL_Vessel_Navy"],              # 12: Navy vessel hull
        palette["Mat_MTL_Window_Glass_Dark"],        # 13: Vessel & car windows
        palette["Mat_MTL_Heritage_RedBrick"],        # 14: Old Montreal red-brick heritage backdrop
        palette["Mat_MTL_PierreGrise_Limestone"],    # 15: Old Montreal grey-limestone heritage backdrop
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Exact Satellite-Aligned King-Edward Pier Deck Polygon (+5.0 deg pier orientation!)
    # North Quay edge: (335.0, 62.0) -> (715.0, 95.2)
    # South Quay edge: (335.0, -37.5) -> (715.0, -4.2)
    king_edward_pier_pts = ensure_ccw([
        (275.0, -55.0),
        (335.0, -37.5),
        (715.0, -4.2),
        (715.0, 95.2),
        (335.0, 62.0),
        (275.0, 95.0),
    ])
    extrude_prism_in_bm(bm, king_edward_pier_pts, -2.50, 0.00, mat_side=3, mat_top=0)

    # Stepped Granite Quay Coping Stones, Railings & Cast-Iron Mooring Bollards along King-Edward Pier Edges
    ke_quay_edges = [
        ((335.0, 62.0), (715.0, 95.2)),
        ((715.0, 95.2), (715.0, -4.2)),
        ((715.0, -4.2), (335.0, -37.5)),
    ]
    for qp1, qp2 in ke_quay_edges:
        # Stepped granite coping curb at Z = 0.00m .. +0.18m
        add_box_between(bm, qp1, qp2, -0.35, 0.18, thickness=1.10, offset_out=-0.45, mat_idx=3, cap_top=True)
        # Quayside safety railing at Z = 0.18m .. 1.15m
        add_box_between(bm, qp1, qp2, 0.18, 1.15, thickness=0.08, offset_out=-0.85, mat_idx=7, cap_top=False)
        # Mooring bollards every 18m
        seg_l = math.hypot(qp2[0] - qp1[0], qp2[1] - qp1[1])
        ux, uy = (qp2[0] - qp1[0]) / seg_l, (qp2[1] - qp1[1]) / seg_l
        for dist in range(10, int(seg_l - 6), 18):
            bx = qp1[0] + ux * dist
            by = qp1[1] + uy * dist
            add_cylinder_in_bm(bm, (bx, by), 0.18, 0.72, 0.22, 0.18, n_seg=10, mat_idx=8, cap_top=True)

    # Wide Warm Concrete South Promenade Apron along South Side of Science Centre (Y ~ -37m .. -4m, visible in Satellite H6)
    south_apron_pts = ensure_ccw([
        (335.0, -37.2),
        (714.5, -4.0),
        (714.5, 9.5),
        (335.0, -23.5),
    ])
    extrude_prism_in_bm(bm, south_apron_pts, 0.00, 0.15, mat_side=3, mat_top=2)
    # Orange Gangway / Boat Ramp Marker at X = 405m, Y = -28m (visible in Satellite H6, V1..V2)
    orange_ramp = ensure_ccw([(404.0, -30.8), (406.8, -30.5), (406.3, -25.2), (403.5, -25.5)])
    extrude_prism_in_bm(bm, orange_ramp, 0.15, 0.19, mat_side=6, mat_top=6)

    # Wide North Quay Walkway Apron along North Side of Shed (visible in Satellite H1)
    north_apron_pts = ensure_ccw([
        (335.0, 56.5),
        (714.5, 89.2),
        (714.5, 95.0),
        (335.0, 61.8),
    ])
    extrude_prism_in_bm(bm, north_apron_pts, 0.00, 0.15, mat_side=3, mat_top=2)

    # 2. Southern Pier Promenade Apron for Camera 4 (`Quai_King_Edward_Pier_Tip` at (449.185, -117.276))
    # Covers X = 290..540, Y = -195..-105m so Camera 4 stands on authentic rectangular concrete pavers with quay wall & fence!
    south_pier_pts = ensure_ccw([
        (290.0, -195.0),
        (540.0, -170.0),
        (522.0, -104.5),
        (315.0, -131.5),
    ])
    extrude_prism_in_bm(bm, south_pier_pts, -2.50, 0.08, mat_side=3, mat_top=2)
    # Expansion joint strips every 3.5m across south_pier_pts (Z = 0.085m) to match foreground concrete paver joints
    for jx in range(435, 515, 3):
        add_box_between(bm, (float(jx), -145.0), (float(jx) + 2.5, -106.0), 0.08, 0.088, thickness=0.05, offset_out=0.0, mat_idx=3, cap_top=True)
    for jy in range(-140, -106, 3):
        add_box_between(bm, (435.0, float(jy)), (512.0, float(jy) + 8.5), 0.08, 0.088, thickness=0.05, offset_out=0.0, mat_idx=3, cap_top=True)
    # Paver joint grid & quayside parapet wall along north edge (315.0, -131.5) -> (522.0, -104.5)
    add_box_between(bm, (315.0, -131.5), (501.0, -107.2), -0.40, 0.85, thickness=0.65, offset_out=-0.35, mat_idx=3, cap_top=True)
    # Wire-mesh security fence posts & top rails visible in Quai_King_Edward_Pier_Tip (V1..V8, H5..H7)
    fence_pts = [
        (438.0, -116.2),
        (465.0, -112.5),
        (492.0, -109.0),
        (497.5, -116.5),
        (504.5, -108.5),
    ]
    for k in range(len(fence_pts) - 1):
        fp1, fp2 = fence_pts[k], fence_pts[k + 1]
        add_box_between(bm, fp1, fp2, 0.08, 2.25, thickness=0.05, offset_out=0.0, mat_idx=7, cap_top=False)
        add_box_between(bm, fp1, fp2, 1.15, 1.22, thickness=0.06, offset_out=0.0, mat_idx=7, cap_top=False)
        seg_f = math.hypot(fp2[0] - fp1[0], fp2[1] - fp1[1])
        n_posts = max(2, int(seg_f / 2.6))
        for pi in range(n_posts + 1):
            frac = pi / n_posts
            px = fp1[0] + (fp2[0] - fp1[0]) * frac
            py = fp1[1] + (fp2[1] - fp1[1]) * frac
            add_cylinder_in_bm(bm, (px, py), 0.08, 2.30, 0.04, 0.04, n_seg=8, mat_idx=8, cap_top=True)
    # Wooden plank bench / parapet assembly along Pier Tip promenade
    add_box_between(bm, (454.0, -113.5), (484.0, -109.6), 0.08, 0.55, thickness=0.65, offset_out=-0.65, mat_idx=9, cap_top=True)

    # 3. Central Spine Sidewalks, Curbs, Crosswalks, Parking Stalls & 3D Parked Cars (matching Satellite H3..H4 & Street View)
    # North Sidewalk along O'Quai Bistro & North Shed (Y = 22.8m..34.5m on west, up to Y = 46m on east)
    north_sw_pts = ensure_ccw([
        (338.0, 19.8),
        (438.0, 28.5),
        (438.0, 35.5),
        (338.0, 27.0),
    ])
    extrude_prism_in_bm(bm, north_sw_pts, 0.00, 0.15, mat_side=3, mat_top=2)
    add_box_between(bm, (338.0, 19.8), (438.0, 28.5), 0.00, 0.18, thickness=0.28, offset_out=0.0, mat_idx=3, cap_top=True)

    # East North Sidewalk & Raised Median along Parking Stalls (X = 444..640)
    east_north_sw = ensure_ccw([
        (444.0, 27.5),
        (640.0, 44.6),
        (640.0, 50.5),
        (444.0, 33.5),
    ])
    extrude_prism_in_bm(bm, east_north_sw, 0.00, 0.15, mat_side=3, mat_top=2)

    # South Sidewalk along Science Centre North Facade (X = 335..640, Y = 2.0..15.5m)
    south_sw_pts = ensure_ccw([
        (335.0, -3.5),
        (640.0, 23.0),
        (640.0, 30.8),
        (335.0, 4.2),
    ])
    extrude_prism_in_bm(bm, south_sw_pts, 0.00, 0.15, mat_side=3, mat_top=2)
    add_box_between(bm, (335.0, 4.2), (640.0, 30.8), 0.00, 0.18, thickness=0.28, offset_out=0.0, mat_idx=3, cap_top=True)

    # Curving Double-Yellow Centerline & Toll Gate Islands (visible in Science_Centre_South_Promenade H6..H8 & Satellite H3..H4)
    yellow_curve = [
        (385.0, 14.5),
        (402.0, 15.8),
        (412.0, 15.2),
        (420.0, 13.8),
        (434.0, 14.8),
    ]
    for k in range(len(yellow_curve) - 1):
        add_box_between(bm, yellow_curve[k], yellow_curve[k + 1], 0.002, 0.012, thickness=0.22, offset_out=0.0, mat_idx=6, cap_top=True)

    # Automated Parking Toll Islands (X = 421..431, Y = 12.0..17.5m, visible in V3..V5, H5..H6 of South_Promenade)
    for ty in (11.8, 15.2):
        add_box_between(bm, (421.0, ty), (428.5, ty + 0.65), 0.00, 0.22, thickness=1.10, offset_out=0.0, mat_idx=3, cap_top=True)
        # Yellow safety bollards
        for bx in (421.5, 424.5, 427.8):
            add_cylinder_in_bm(bm, (bx, ty + 0.25), 0.22, 1.15, 0.14, 0.14, n_seg=10, mat_idx=6, cap_top=True)
        # Blue parking ticket kiosk
        add_box_between(bm, (423.2, ty + 0.15), (424.2, ty + 0.25), 0.22, 1.55, thickness=0.65, offset_out=0.0, mat_idx=10, cap_top=True)
        # White & orange barrier gate arm
        add_box_between(bm, (425.0, ty + 0.20), (425.0, ty - 2.20), 0.92, 1.02, thickness=0.08, offset_out=0.0, mat_idx=5, cap_top=True)

    # Prominent White Zebra Crosswalk at X = 439..445, Y = 11..28m (clearly visible in Satellite V3..V4, H3..H4)
    for si in range(11):
        cy_s = 12.2 + si * 1.45
        add_box_between(bm, (439.2, cy_s), (443.8, cy_s + 0.40), 0.004, 0.018, thickness=0.75, offset_out=0.0, mat_idx=5, cap_top=True)

    # Underpass Crosswalk at X = 371..378, Y = 16.5..21.5m (visible in H7..H8 of Rue_de_la_Commune_Science_Crossing)
    for si in range(6):
        cx_s = 370.5 + si * 1.35
        add_box_between(bm, (cx_s, 16.2), (cx_s - 0.35, 20.4), 0.004, 0.018, thickness=0.65, offset_out=0.0, mat_idx=5, cap_top=True)

    # Row of Angled/Perpendicular Parking Stalls & 3D Parked Cars at X = 472..526, Y = 19..25m (Satellite V5..V8, H3)
    car_mats = [8, 11, 10, 8, 11, 8, 10, 8, 11, 8, 10, 8]
    for ci, px in enumerate(range(474, 526, 4)):
        py = 21.8 + (px - 474) * 0.087
        # White stall line
        add_box_between(bm, (px - 1.4, py - 2.4), (px - 1.8, py + 2.4), 0.004, 0.015, thickness=0.12, offset_out=0.0, mat_idx=5, cap_top=True)
        # 3D Parked Car in stall
        cmat = car_mats[ci % len(car_mats)]
        add_box_between(bm, (px, py - 2.0), (px - 0.35, py + 2.0), 0.15, 0.95, thickness=1.78, offset_out=0.0, mat_idx=cmat, cap_top=True)
        add_box_between(bm, (px - 0.08, py - 0.9), (px - 0.25, py + 1.1), 0.95, 1.48, thickness=1.52, offset_out=0.0, mat_idx=13, cap_top=True)

    # 4. Promenade du Vieux-Port Lawns, Timber Boardwalk & Old Montreal Heritage Backdrop (West/North Landward Sector)
    # Lush Green Park Lawns (Z = +0.195m), Granite Curbs (+0.225m), Limestone Walkways (+0.245m) visible through Underpass (V1..V3, H4..H6)
    lawn_polys = [
        [(332.0, 26.0), (363.5, 28.5), (361.0, 62.0), (328.0, 58.0)],
        [(305.0, 52.0), (358.0, 64.0), (345.0, 140.0), (295.0, 125.0)],
        [(312.0, -35.0), (338.0, -32.0), (334.0, 12.0), (308.0, 10.0)],
    ]
    for lpts in lawn_polys:
        l_ccw = ensure_ccw(lpts)
        extrude_prism_in_bm(bm, l_ccw, 0.00, 0.195, mat_side=3, mat_top=4)
        for k in range(len(l_ccw)):
            add_box_between(bm, l_ccw[k], l_ccw[(k + 1) % len(l_ccw)], 0.00, 0.225, thickness=0.32, offset_out=0.0, mat_idx=3, cap_top=True)

    # Limestone Walkways (+0.245m) & Timber Boardwalk Strips (+0.255m) along Promenade du Vieux-Port
    add_box_between(bm, (345.0, 22.0), (332.0, 95.0), 0.00, 0.245, thickness=5.5, offset_out=0.0, mat_idx=2, cap_top=True)
    add_box_between(bm, (356.0, 26.0), (346.0, 88.0), 0.00, 0.255, thickness=3.6, offset_out=0.0, mat_idx=9, cap_top=True)

    # Old Montreal Heritage Red-Brick & Grey-Limestone Backdrop along Rue de la Commune (visible at V1..V3, H4..H5)
    heritage_blocks = [
        ([(310.0, 72.0), (342.0, 66.0), (346.0, 82.0), (314.0, 88.0)], 17.5, 14),
        ([(285.0, 42.0), (312.0, 38.0), (316.0, 62.0), (289.0, 66.0)], 19.0, 15),
    ]
    for hpts, hh, hmat in heritage_blocks:
        extrude_prism_in_bm(bm, hpts, 0.0, hh, mat_side=hmat, mat_top=3)

    # 5. Moored Harbor Excursion Vessel & Tugboat in Bassin King-Edward / Alexandra
    add_moored_vessel(bm, (465.0, -52.0), length=36.0, beam=8.2, heading_rad=math.radians(5.0), mat_hull=12, mat_cabin=11, mat_glass=13, mat_deck=9)
    add_moored_vessel(bm, (555.0, -68.0), length=22.0, beam=6.4, heading_rad=math.radians(8.0), mat_hull=8, mat_cabin=6, mat_glass=13, mat_deck=9)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Real High-Poly Poly Haven 3D Trees, Streetlamps & Benches ---

_KIT_CACHE = {}


def append_kit_asset(asset_name, collection, location, rotation_z=0.0, scale=1.0):
    # First try Poly Haven model library via build_montreal_kit
    ph_map = {
        "jacaranda_tree_LOD0": "jacaranda_tree",
        "street_lamp_01": "street_lamp_01",
        "Master_Street_Bench": "modular_street_seating",
    }
    ph_id = ph_map.get(asset_name, asset_name)
    res = kit.append_polyhaven_model(ph_id, collection, f"PH_{ph_id}", location=location, rotation_z=rotation_z, scale=scale)
    if res:
        return res

    kit_path = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
    if not _KIT_CACHE and os.path.isfile(kit_path):
        with bpy.data.libraries.load(kit_path, link=False) as (data_from, data_to):
            want = [n for n in ("jacaranda_tree_LOD0", "street_lamp_01", "Master_Street_Bench", "gothic_statue") if n in data_from.objects]
            data_to.objects = want
        for o in data_to.objects:
            if o is not None:
                _KIT_CACHE[o.name] = o
    src = _KIT_CACHE.get(asset_name)
    if src is None:
        return None
    inst = src.copy()
    inst.location = location
    inst.rotation_euler = (0.0, 0.0, rotation_z)
    inst.scale = (scale, scale, scale)
    collection.objects.link(inst)
    return inst


def scatter_quayside_props(palette, collection_owned):
    # Heritage Streetlamps along Promenade du Vieux-Port & North Shed (avoiding V2 of North_Entrance!)
    lamp_coords = [
        (342.0, 22.0, 0.20),
        (356.0, 24.5, 0.20),
        (366.0, 25.5, 0.20),
        (415.0, 26.5, 0.15),
        (445.0, 29.0, 0.15),
        (475.0, 31.5, 0.15),
        (505.0, 34.0, 0.15),
        (535.0, 36.5, 0.15),
    ]
    for loc in lamp_coords:
        append_kit_asset("street_lamp_01", collection=collection_owned, location=loc, rotation_z=math.radians(90.0), scale=1.0)

    bench_coords = [
        (352.0, 28.0, 0.22),
        (402.0, 26.5, 0.15),
        (448.0, 30.0, 0.15),
        (495.0, 33.5, 0.15),
    ]
    for loc in bench_coords:
        append_kit_asset("Master_Street_Bench", collection=collection_owned, location=loc, rotation_z=math.radians(85.0), scale=1.0)

    # Real High-Poly Poly Haven 3D Trees (jacaranda_tree) along Promenade du Vieux-Port & North Entrance Lawns
    # Placed so they appear in V1..V3 of Rue_de_la_Commune_Science_Crossing and V1..V2 of Science_Centre_South_Promenade!
    tree_coords = [
        (355.0, 38.0, 0.20),
        (348.0, 44.0, 0.20),
        (358.0, 50.0, 0.20),
        (342.0, 54.0, 0.20),
        (335.0, 48.0, 0.20),
        (330.0, 36.0, 0.20),
        (334.5, 191.3, 0.20),
        (332.4, 187.0, 0.20),
        (330.2, 182.3, 0.20),
        (327.9, 177.7, 0.20),
        (325.6, 173.2, 0.20),
        (326.4, 189.8, 0.20),
    ]
    for loc in tree_coords:
        append_kit_asset("jacaranda_tree_LOD0", collection=collection_owned, location=loc, rotation_z=math.radians(float(hash(loc) % 360)), scale=1.15)


# --- World, Lighting & Cameras ---

def configure_world_and_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 24

    world = bpy.data.worlds.new(name=f"MTL_World_{BLOCK_ID}")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.15
    links.new(out.inputs["Surface"], bg.outputs["Background"])

    hdri_path = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")
    if os.path.isfile(hdri_path):
        env = nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri_path, check_existing=True)
        links.new(bg.inputs["Color"], env.outputs["Color"])

    sun_data = bpy.data.lights.new(name=f"MTL_Sun_{BLOCK_ID}", type="SUN")
    sun_data.energy = 4.5
    sun_data.color = (1.0, 0.97, 0.90)
    sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name=f"MTL_Sun_{BLOCK_ID}", object_data=sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(12.0), math.radians(-135.0))

    # Warm fill lighting under the LE BELVÉDÈRE viaduct (161202894) so H1..H6 in Rue_de_la_Commune_Science_Crossing is well-lit
    for idx_l, (lx, ly, lz, l_ener) in enumerate([
        (373.5, 19.5, 4.10, 450.0),
        (370.5, 22.0, 4.10, 380.0),
        (376.5, 22.5, 3.80, 380.0),
    ]):
        pt_data = bpy.data.lights.new(name=f"MTL_Belvedere_Fill_{idx_l}", type="POINT")
        pt_data.energy = l_ener
        pt_data.color = (1.0, 0.94, 0.84)
        pt_data.shadow_soft_size = 2.5
        pt_obj = bpy.data.objects.new(name=f"MTL_Belvedere_Fill_{idx_l}", object_data=pt_data)
        scene.collection.objects.link(pt_obj)
        pt_obj.location = (lx, ly, lz)


def render_cameras(dossier, iter_num=2):
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
        cam_data.clip_end = 2500.0
        cam_obj = bpy.data.objects.new(name=f"SV_Cam_{label}", object_data=cam_data)
        scene.collection.objects.link(cam_obj)
        cam_obj.location = (cx, cy, 1.75)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch_deg), 0.0, math.radians(-heading_deg))

        scene.camera = cam_obj
        out_file = os.path.join(RENDERS_DIR, f"iter{iter_num}_{label}.png")
        scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View Camera [{label}] -> {out_file}")

    # True 1:1 Google Maps Satellite-Matched Nadir Top-Down Orthographic Camera
    sat_spec = dossier.get("satellite", {})
    sat_cx, sat_cy = sat_spec.get("center_xy_m", dossier.get("blender_center_xy_m", [457.968, 7.792]))
    sat_span = float(sat_spec.get("span_meters", 133.93))
    ortho_data = bpy.data.cameras.new(name=f"Cam_Satellite_TopDown_Ortho_{BLOCK_ID}")
    ortho_data.type = "ORTHO"
    ortho_data.ortho_scale = sat_span
    ortho_data.clip_start = 1.0
    ortho_data.clip_end = 1000.0
    ortho_obj = bpy.data.objects.new(name=f"Cam_Satellite_TopDown_Ortho_{BLOCK_ID}", object_data=ortho_data)
    scene.collection.objects.link(ortho_obj)
    ortho_obj.location = (sat_cx, sat_cy, 300.0)
    ortho_obj.rotation_euler = (0.0, 0.0, 0.0)

    scene.camera = ortho_obj
    ortho_out = os.path.join(RENDERS_DIR, f"iter{iter_num}_topdown_ortho.png")
    scene.render.filepath = ortho_out
    bpy.ops.render.render(write_still=True)
    print(f"Rendered 1:1 Satellite Top-Down Ortho -> {ortho_out}")

    # Overview Snapshot Camera
    ov_data = bpy.data.cameras.new(name=f"Overview_Cam_{BLOCK_ID}")
    ov_data.angle = math.radians(52.0)
    ov_data.clip_start = 1.0
    ov_data.clip_end = 3000.0
    ov_obj = bpy.data.objects.new(name=f"Overview_Cam_{BLOCK_ID}", object_data=ov_data)
    scene.collection.objects.link(ov_obj)

    target = Vector((458.0, 8.0, 10.0))
    ov_obj.location = (310.0, -180.0, 140.0)
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = SNAPSHOT_PATH
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Block Overview Snapshot -> {SNAPSHOT_PATH}")


# --- Main Build Orchestration ---

def main():
    print(f"Starting Iteration 2 High-Poly 3D Build for Block {BLOCK_ID} (Quai King-Edward & Montreal Science Centre)...")
    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    master_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(master_col)
    col_owned = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    master_col.children.link(col_owned)

    palette = create_upgraded_palette()

    print("Building wave-rippled 2K PBR water, stepped granite quays, Promenade lawns, vessels & parked cars...")
    build_ground_quays_and_water(dossier, palette, col_owned)

    print("Building high-poly architectural 3D models for primary owned buildings...")
    for bldg in dossier.get("osm_features", {}).get("buildings", []):
        if not bldg.get("is_primary_owner"):
            continue
        bid = bldg["id"]
        bname = bldg.get("name", "")
        print(f"  Building {bid} ('{bname}')...")

        if bid == 46866809:
            build_science_centre_46866809(bldg, palette, col_owned)
        elif bid == 46866806:
            build_o_quai_bistro_46866806(bldg, palette, col_owned)
        elif bid == 161202894:
            build_skybridge_161202894(bldg, palette, col_owned)
        elif bid == 263735643:
            build_historic_pier_shed(bldg, palette, col_owned, "North_Pier_Shed", height=10.50)
        elif bid == 263735648:
            build_historic_pier_shed(bldg, palette, col_owned, "South_Pier_Shed", height=10.50)
        elif bid == 263735642:
            build_pavilion_or_canopy(bldg, palette, col_owned, "Pier_End_Link", height=9.50, is_canopy=False)
        elif bid == 1248578233:
            build_decalade_tower_1248578233(bldg, palette, col_owned)
        elif bid == 440195626:
            build_pavilion_or_canopy(bldg, palette, col_owned, "Pier_Tip_Pavilion", height=5.50, is_canopy=False)
        elif bid == 1445521129:
            build_pavilion_or_canopy(bldg, palette, col_owned, "Entrance_Canopy", height=4.80, is_canopy=True)
        else:
            build_pavilion_or_canopy(bldg, palette, col_owned, "Structure", height=8.00, is_canopy=False)

    print("Placing Poly Haven 3D trees, streetlamps & benches...")
    scatter_quayside_props(palette, col_owned)

    print("Configuring world, HDRI lighting and rendering cameras...")
    configure_world_and_render()

    print(f"Packing 2K PBR textures and saving clean {BLEND_OUT_PATH}...")
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"Warning during pack_all: {e}")
    tmp_blend = BLEND_OUT_PATH + ".tmp.blend"
    for p in (tmp_blend, BLEND_OUT_PATH + "@"):
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

    print(f"Exporting clean USD {USDC_OUT_PATH}...")
    bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, selected_objects_only=False)

    print("Rendering Iteration 3 street view cameras, satellite ortho & overview snapshot...")
    render_cameras(dossier, iter_num=3)

    print(f"Iteration 3 build complete for {BLOCK_ID}!")


if __name__ == "__main__":
    main()
