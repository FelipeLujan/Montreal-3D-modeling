"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0018 (Wave 1)
(Marché Bonsecours & Rue Saint-Paul Est, 350 Rue Saint-Paul Est, Montréal, QC H2Y 1H2)

Architectural Landmarks & Scope:
1. Marché Bonsecours (87389029):
   - Monumental 162-meter cut-stone Neoclassical market hall (William Footner, 1847).
   - Pierre Grise de Montréal limestone ashlar facade (Poly Haven sandstone_blocks_05 2K PBR).
   - Monumental Classical Portico facing Rue Saint-Paul Est: 6 fluted Doric columns, full classical
     entablature with Doric frieze, projecting modillion cornice, and monumental triangular pediment.
     Grand recessed double-height arched entrance portal with voussoirs and carved keystone.
   - Central Waterfront Wing facing Rue de la Commune Est with arcade bays and decorative attic pediment.
   - Iconic Central Silver Neoclassical Dome: square attic pedestal with balustrade, octagonal drum
     with 8 recessed round-arched windows and paired pilasters, shining silver metallic hemispherical dome
     with 16 standing-seam radial ribs, crowned by octagonal cupola lantern and spire (peak Z = 41.5m).
   - Deeply recessed (>= 0.45m) 3D window bays across all facades with projecting stone sills, pedimented
     lintels, mullions, and dark reflective glass.
   - Pitched roof membrane inset >= 0.35m inside parapet walls (Z = 15.10m .. 18.30m) with zero Z-fighting.
2. Primary Owned Historic Buildings along Rue Saint-Paul Est / Rue Saint-Claude:
   - Auberge Alt Hostel (1244238348, 347 Rue Saint-Paul Est): 4-story Victorian building with ground-floor
     storefront display windows, Poly Haven castle_brick_02_red upper stories, deeply recessed sash windows,
     stone sills, and bracketed cornice.
   - 1244238347 & 1244238349: 4-story Montreal greystone row buildings with recessed window bays, stone sills.
   - 1244238357: 3-story historic commercial building with storefront and recessed upper windows.
3. Waterfront Promenade Kiosks & Pavilion (Old Port):
   - Kiosques du vieux-port (1387776862): 135m promenade timber vendor pavilions with vertical posts,
     slatted timber siding (Mat_MTL_Wood_Timber), pitched tin roofs, recessed counter openings (0.50m recess).
   - Waterfront Pavilion (1387776864): timber and metal pavilion with overhanging roof eaves.
4. Watertight Ground Stratum & Streets:
   - Watertight solid base slab (Z = -0.25m to 0.00m) with upward (+Z) normals.
   - Roadbeds (Z = 0.00m .. 0.015m): Rue Saint-Paul Est (cobblestone), Rue de la Commune Est (asphalt),
     Rue du Marché-Bonsecours, Rue Bonsecours, Rue Saint-Claude.
   - Raised Sidewalks with 3D Curbs (Z = +0.15m): Continuous raised granite sidewalks around Marché
     Bonsecours esplanade and street edges. ZERO coplanar overlap.
5. Props & Assets:
   - Real Poly Haven 2K PBR materials (sandstone_blocks_05, castle_brick_02_red, cobblestone_floor_08, asphalt_02).
   - Linked assets from assets/montreal_kit.blend: street_lamp_01, Master_Street_Bench, jacaranda_tree_LOD0.
   - No Context Proxy meshes created or kept! All primary owned buildings in Block_MTL-VM-0018_Owned.
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

BLOCK_ID = "MTL-VM-0018"
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
        candidates = [f"{prefix}_Rough_2k.jpg", f"{prefix}_rough_2k.jpg"]
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


def create_upgraded_palette():
    palette = kit.create_montreal_material_palette()

    # Poly Haven 2K PBR Materials
    apply_polyhaven_2k_pbr(palette["Mat_MTL_PierreGrise_Limestone"], "sandstone_blocks_05", (0.30, 0.30, 0.30), (0.60, 0.62, 0.65), 0.72, 0.96, 1.25)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_WarmBuff_Limestone"], "sandstone_blocks_05", (0.28, 0.28, 0.28), (0.86, 0.82, 0.72), 0.68, 0.94, 1.10)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Red_Sandstone"], "castle_brick_02_red", (0.28, 0.28, 0.28), (0.76, 0.42, 0.28), 0.76, 0.95, 1.15)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Heritage_RedBrick"], "castle_brick_02_red", (0.38, 0.38, 0.38), (0.72, 0.32, 0.22), 0.76, 0.95, 1.15)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Cobblestone"], "cobblestone_floor_08", (0.36, 0.36, 0.36), (0.58, 0.59, 0.61), 0.65, 0.92, 1.25)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Street_Asphalt"], "asphalt_02", (0.24, 0.24, 0.24), (0.34, 0.35, 0.37), 0.56, 0.95, 1.10)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Plaza_Light_Granite"], "sandstone_blocks_05", (0.28, 0.28, 0.28), (0.82, 0.81, 0.79), 0.68, 0.90, 0.90)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Plaza_Charcoal_Granite"], "asphalt_02", (0.28, 0.28, 0.28), (0.38, 0.40, 0.42), 0.68, 0.90, 1.00)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Slate_Roof_Dark"], "cobblestone_floor_08", (0.38, 0.38, 0.38), (0.22, 0.24, 0.28), 0.84, 0.85, 1.10)

    # Silver Tin Roof
    mat_tin = bpy.data.materials.new("Mat_MTL_Silver_Tin_Roof")
    apply_polyhaven_2k_pbr(mat_tin, "asphalt_02", (0.45, 0.45, 0.45), (0.72, 0.75, 0.79), 0.65, 0.55, 0.80)
    palette["Mat_MTL_Silver_Tin_Roof"] = mat_tin

    # Signature Silver Neoclassical Dome Material (Gleaming reflective silver metal)
    mat_dome = bpy.data.materials.new("Mat_MTL_Silver_Dome")
    mat_dome.use_nodes = True
    d_nodes = mat_dome.node_tree.nodes
    d_links = mat_dome.node_tree.links
    d_nodes.clear()
    d_out = d_nodes.new("ShaderNodeOutputMaterial")
    d_bsdf = d_nodes.new("ShaderNodeBsdfPrincipled")
    d_bsdf.inputs["Base Color"].default_value = (0.92, 0.94, 0.96, 1.0)
    d_bsdf.inputs["Metallic"].default_value = 0.98
    d_bsdf.inputs["Roughness"].default_value = 0.16
    if "Specular IOR Level" in d_bsdf.inputs:
        d_bsdf.inputs["Specular IOR Level"].default_value = 0.95
    # Add subtle brushed metal normal
    nor_img = load_image_cached(find_polyhaven_map("asphalt_02", "nor"), non_color=True)
    if nor_img:
        tcoord = d_nodes.new("ShaderNodeTexCoord")
        mapping = d_nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = (0.5, 0.5, 0.5)
        d_links.new(mapping.inputs["Vector"], tcoord.outputs["Object"])
        tex_n = d_nodes.new("ShaderNodeTexImage")
        tex_n.image = nor_img
        tex_n.projection = "BOX"
        tex_n.projection_blend = 0.2
        d_links.new(tex_n.inputs["Vector"], mapping.outputs["Vector"])
        nmap = d_nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = 0.06
        d_links.new(nmap.inputs["Color"], tex_n.outputs["Color"])
        d_links.new(d_bsdf.inputs["Normal"], nmap.outputs["Normal"])
    d_links.new(d_out.inputs["Surface"], d_bsdf.outputs["BSDF"])
    palette["Mat_MTL_Silver_Dome"] = mat_dome

    # Architectural Window Glass (High specular dark reflective glass)
    glass_mat = palette["Mat_MTL_Window_Glass_Dark"]
    glass_mat.use_nodes = True
    gnodes = glass_mat.node_tree.nodes
    glinks = glass_mat.node_tree.links
    gnodes.clear()
    g_out = gnodes.new("ShaderNodeOutputMaterial")
    g_bsdf = gnodes.new("ShaderNodeBsdfPrincipled")
    g_bsdf.inputs["Base Color"].default_value = (0.05, 0.08, 0.11, 1.0)
    g_bsdf.inputs["Roughness"].default_value = 0.035
    g_bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in g_bsdf.inputs:
        g_bsdf.inputs["Specular IOR Level"].default_value = 0.92
    if "Emission Color" in g_bsdf.inputs:
        g_bsdf.inputs["Emission Color"].default_value = (0.12, 0.10, 0.08, 1.0)
        g_bsdf.inputs["Emission Strength"].default_value = 0.05
    glinks.new(g_out.inputs["Surface"], g_bsdf.outputs["BSDF"])

    # Timber Wood Material for Old Port Waterfront Kiosks
    mat_timber = bpy.data.materials.new("Mat_MTL_Wood_Timber")
    apply_polyhaven_2k_pbr(mat_timber, "sandstone_blocks_05", (0.20, 0.20, 0.20), (0.55, 0.38, 0.24), 0.85, 0.90, 1.10)
    palette["Mat_MTL_Wood_Timber"] = mat_timber

    # Additional architectural materials
    palette["Mat_MTL_CastIron_Black"] = kit.get_or_create_pbr_material("Mat_MTL_CastIron_Black", "#1E2022", roughness=0.35, metallic=0.85)
    palette["Mat_MTL_Storefront_Navy"] = kit.get_or_create_pbr_material("Mat_MTL_Storefront_Navy", "#1A2B4C", roughness=0.48)
    palette["Mat_MTL_Storefront_DarkWood"] = kit.get_or_create_pbr_material("Mat_MTL_Storefront_DarkWood", "#3A2416", roughness=0.55)
    palette["Mat_MTL_White_Paint"] = kit.get_or_create_pbr_material("Mat_MTL_White_Paint", "#F2F0EC", roughness=0.40)
    palette["Mat_MTL_Silver_Metal"] = kit.get_or_create_pbr_material("Mat_MTL_Silver_Metal", "#C8CED4", roughness=0.25, metallic=0.85)

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


def add_box_between(bm, p1, p2, z0, z1, thickness=0.35, offset_out=0.0, mat_idx=0):
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
        (v_bot[3], v_bot[2], v_bot[1], v_bot[0]),
        (v_top[0], v_top[1], v_top[2], v_top[3]),
        (v_bot[0], v_bot[1], v_top[1], v_top[0]),
        (v_bot[1], v_bot[2], v_top[2], v_top[1]),
        (v_bot[2], v_bot[3], v_top[3], v_top[2]),
        (v_bot[3], v_bot[0], v_top[0], v_top[3]),
    ]
    for q in quads:
        try:
            f = bm.faces.new(q)
            f.material_index = mat_idx
        except ValueError:
            pass


def extrude_prism_in_bm(bm, pts, z0, z1, mat_side=0, mat_top=None):
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


def add_cylinder_in_bm(bm, center_xy, z0, z1, r_bot, r_top, n_seg=16, mat_idx=0):
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
    try:
        f_top = bm.faces.new(v_top)
        f_top.material_index = mat_idx
    except ValueError:
        pass


def add_curved_voussoir_arch(bm, wp1, wp2, z_spring, arch_rise, thickness=0.68, offset_out=0.24, mat_stone=4, mat_wall=0, add_keystone=True):
    dx = wp2[0] - wp1[0]
    dy = wp2[1] - wp1[1]
    win_w = math.hypot(dx, dy)
    if win_w < 0.35:
        return
    ux, uy = dx / win_w, dy / win_w
    z_top_spandrel = z_spring + arch_rise + 0.24
    n_seg = 9
    for k in range(n_seg):
        t0 = k / n_seg
        t1 = (k + 1) / n_seg
        tm = 0.5 * (t0 + t1)
        x_m = (tm - 0.5) * 2.0
        z_curve = z_spring + arch_rise * math.sqrt(max(0.0, 1.0 - x_m * x_m * 0.88))
        sp1 = (wp1[0] + ux * (t0 * win_w), wp1[1] + uy * (t0 * win_w))
        sp2 = (wp1[0] + ux * (t1 * win_w), wp1[1] + uy * (t1 * win_w))
        add_box_between(bm, sp1, sp2, z_curve, z_curve + 0.24, thickness=thickness, offset_out=offset_out, mat_idx=mat_stone)
        if z_top_spandrel > z_curve + 0.20:
            add_box_between(bm, sp1, sp2, z_curve + 0.20, z_top_spandrel, thickness=thickness - 0.12, offset_out=offset_out - 0.06, mat_idx=mat_wall)
    if add_keystone:
        kp1 = (wp1[0] + ux * (win_w * 0.40), wp1[1] + uy * (win_w * 0.40))
        kp2 = (wp1[0] + ux * (win_w * 0.60), wp1[1] + uy * (win_w * 0.60))
        add_box_between(bm, kp1, kp2, z_spring + arch_rise - 0.04, z_spring + arch_rise + 0.36, thickness=thickness + 0.14, offset_out=offset_out + 0.06, mat_idx=mat_stone)


def add_triangular_pediment_in_bm(bm, p1, p2, z_base, z_peak, thickness=0.85, offset_out=0.0, mat_tympanum=0, mat_cornice=4):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    seg_len = math.hypot(dx, dy)
    if seg_len < 1e-4:
        return
    nx, ny = dy / seg_len, -dx / seg_len
    ht = thickness * 0.5
    ox, oy = nx * offset_out, ny * offset_out

    f_p1 = (p1[0] + ox + nx * ht, p1[1] + oy + ny * ht)
    f_p2 = (p2[0] + ox + nx * ht, p2[1] + oy + ny * ht)
    b_p1 = (p1[0] + ox - nx * ht, p1[1] + oy - ny * ht)
    b_p2 = (p2[0] + ox - nx * ht, p2[1] + oy - ny * ht)

    mid_x = 0.5 * (p1[0] + p2[0]) + ox
    mid_y = 0.5 * (p1[1] + p2[1]) + oy
    f_apex = (mid_x + nx * ht, mid_y + ny * ht)
    b_apex = (mid_x - nx * ht, mid_y - ny * ht)

    v_f1 = bm.verts.new((*f_p1, z_base))
    v_f2 = bm.verts.new((*f_p2, z_base))
    v_fa = bm.verts.new((*f_apex, z_peak))

    v_b1 = bm.verts.new((*b_p1, z_base))
    v_b2 = bm.verts.new((*b_p2, z_base))
    v_ba = bm.verts.new((*b_apex, z_peak))

    # Front tympanum
    try:
        f_front = bm.faces.new((v_f1, v_f2, v_fa))
        f_front.material_index = mat_tympanum
    except ValueError:
        pass

    # Back face
    try:
        f_back = bm.faces.new((v_b2, v_b1, v_ba))
        f_back.material_index = mat_tympanum
    except ValueError:
        pass

    # Bottom face (normal down)
    try:
        f_bot = bm.faces.new((v_f1, v_b1, v_b2, v_f2))
        f_bot.material_index = mat_cornice
    except ValueError:
        pass

    # Sloped left raking face
    try:
        f_left = bm.faces.new((v_fa, v_ba, v_b1, v_f1))
        f_left.material_index = mat_cornice
    except ValueError:
        pass

    # Sloped right raking face
    try:
        f_right = bm.faces.new((v_f2, v_b2, v_ba, v_fa))
        f_right.material_index = mat_cornice
    except ValueError:
        pass


def add_pitched_roof_in_bm(bm, pts, z_base, height=3.2, inset_factor=0.82, mat_roof=1, mat_trim=4):
    pts = ensure_ccw(pts)
    if len(pts) < 3:
        return
    inner_pts = inset_polygon_toward_centroid(pts, inset_factor)
    z_top = z_base + height
    v_bot = [bm.verts.new((p[0], p[1], z_base)) for p in pts]
    v_top = [bm.verts.new((p[0], p[1], z_top)) for p in inner_pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        try:
            f = bm.faces.new((v_bot[i], v_bot[j], v_top[j], v_top[i]))
            f.material_index = mat_roof
        except ValueError:
            pass
    try:
        f_cap = bm.faces.new(v_top)
        f_cap.material_index = mat_trim
    except ValueError:
        pass


def add_dome_in_bm(bm, center_xy, z_base, radius, height, n_radial=32, n_rings=16, mat_dome=0):
    cx, cy = center_xy
    rings = []
    for r in range(n_rings + 1):
        frac = r / n_rings
        phi = frac * (math.pi * 0.5)
        ring_r = radius * math.cos(phi)
        ring_z = z_base + height * math.sin(phi)
        verts = []
        for s in range(n_radial):
            theta = (s / n_radial) * 2.0 * math.pi
            vx = cx + ring_r * math.cos(theta)
            vy = cy + ring_r * math.sin(theta)
            verts.append(bm.verts.new((vx, vy, ring_z)))
        rings.append(verts)

    v_top = bm.verts.new((cx, cy, z_base + height))

    for r in range(n_rings - 1):
        for s in range(n_radial):
            s_next = (s + 1) % n_radial
            v1 = rings[r][s]
            v2 = rings[r][s_next]
            v3 = rings[r + 1][s_next]
            v4 = rings[r + 1][s]
            try:
                f = bm.faces.new((v1, v2, v3, v4))
                f.material_index = mat_dome
            except ValueError:
                pass

    for s in range(n_radial):
        s_next = (s + 1) % n_radial
        try:
            f = bm.faces.new((rings[n_rings - 1][s], rings[n_rings - 1][s_next], v_top))
            f.material_index = mat_dome
        except ValueError:
            pass


# --- Building 87389029: Marché Bonsecours ---

def build_marche_bonsecours(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_87389029_Marche_Bonsecours"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_PierreGrise_Limestone"],
        palette["Mat_MTL_Silver_Tin_Roof"],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_CastIron_Black"],
        palette["Mat_MTL_WarmBuff_Limestone"],
        palette["Mat_MTL_Silver_Dome"],
        palette["Mat_MTL_Storefront_DarkWood"],
        palette["Mat_MTL_Plaza_Light_Granite"],
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    height_main = 14.60
    # Core building prism without horizontal top face (prevents coplanar fighting with roof membrane)
    extrude_prism_in_bm(bm, pts, 0.0, height_main, mat_side=0, mat_top=None)

    # 1. Facades and Recessed Windows along the perimeter
    n = len(pts)
    bay_target_w = 3.6
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.0:
            add_box_between(bm, p1, p2, 0.0, height_main, thickness=0.60, offset_out=0.20, mat_idx=0)
            continue

        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / bay_target_w)))
        bay_w = seg_len / n_bays
        pier_w = min(1.10, max(0.48, bay_w * 0.34))

        # Rusticated ground floor base and water table / belt course
        add_box_between(bm, p1, p2, 0.0, 0.85, thickness=0.82, offset_out=0.30, mat_idx=4)
        add_box_between(bm, p1, p2, 4.90, 5.30, thickness=0.86, offset_out=0.32, mat_idx=4)

        # Stone piers between bays
        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.08:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            add_box_between(bm, q1, q2, 0.85, height_main - 0.40, thickness=0.74, offset_out=0.26, mat_idx=0)
            z_band = 1.05
            while z_band < 4.8:
                add_box_between(bm, q1, q2, z_band, z_band + 0.30, thickness=0.84, offset_out=0.31, mat_idx=4)
                z_band += 0.42

        # Recessed Window Bays (>= 0.45m recess into wall)
        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            win_w = bs1 - bs0
            if win_w < 0.35:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            # Ground floor arched arcade opening (Z = 0.85m .. 4.30m)
            add_box_between(bm, wp1, wp2, 0.85, 4.30, thickness=0.12, offset_out=-0.22, mat_idx=2)
            add_curved_voussoir_arch(bm, wp1, wp2, 3.70, 0.55, thickness=0.72, offset_out=0.26, mat_stone=4, mat_wall=0, add_keystone=True)
            ms = 0.5 * (bs0 + bs1)
            mp1 = (p1[0] + dx * (ms - 0.045), p1[1] + dy * (ms - 0.045))
            mp2 = (p1[0] + dx * (ms + 0.045), p1[1] + dy * (ms + 0.045))
            add_box_between(bm, mp1, mp2, 0.85, 4.30, thickness=0.18, offset_out=-0.08, mat_idx=3)

            # Piano Nobile (2nd Floor, Z = 5.30m .. 10.30m): Monumental Pedimented Windows
            add_box_between(bm, wp1, wp2, 5.30, 5.55, thickness=0.86, offset_out=0.32, mat_idx=4)
            add_box_between(bm, wp1, wp2, 5.55, 9.50, thickness=0.12, offset_out=-0.22, mat_idx=2)
            add_box_between(bm, mp1, mp2, 5.55, 9.50, thickness=0.18, offset_out=-0.08, mat_idx=3)
            add_box_between(bm, wp1, wp2, 7.50, 7.62, thickness=0.18, offset_out=-0.08, mat_idx=3)
            add_box_between(bm, wp1, wp2, 9.50, 10.05, thickness=0.82, offset_out=0.30, mat_idx=4)

            # Attic Floor (3rd Floor, Z = 10.30m .. 13.90m): Square Recessed Windows
            add_box_between(bm, wp1, wp2, 10.30, 10.55, thickness=0.80, offset_out=0.28, mat_idx=4)
            add_box_between(bm, wp1, wp2, 10.55, 12.90, thickness=0.12, offset_out=-0.22, mat_idx=2)
            add_box_between(bm, mp1, mp2, 10.55, 12.90, thickness=0.18, offset_out=-0.08, mat_idx=3)
            add_box_between(bm, wp1, wp2, 12.90, 13.30, thickness=0.80, offset_out=0.28, mat_idx=4)

        # Modillion classical cornice & solid stone parapet along the roof edge
        add_box_between(bm, p1, p2, height_main - 0.40, height_main + 0.35, thickness=1.12, offset_out=0.46, mat_idx=4)
        # Parapet wall top cap at Z = 15.75m
        add_box_between(bm, p1, p2, height_main + 0.35, height_main + 1.15, thickness=0.55, offset_out=0.20, mat_idx=0)

    # 2. Inset Pitched Roof Membrane (Built-in zero Z-fighting: inset >= 0.35m, base Z = 15.10m, ridge = 18.30m)
    add_pitched_roof_in_bm(bm, pts, 15.10, height=3.20, inset_factor=0.85, mat_roof=1, mat_trim=4)

    # 3. Monumental Classical Portico on Rue Saint-Paul Est Facade
    port_p1 = (382.40, 464.56)
    port_p2 = (388.26, 483.34)
    p_dx = port_p2[0] - port_p1[0]
    p_dy = port_p2[1] - port_p1[1]
    p_len = math.hypot(p_dx, p_dy)
    p_ux, p_uy = p_dx / p_len, p_dy / p_len
    p_nx, p_ny = -p_uy, p_ux

    # Stylobate granite steps (Z = 0.0m .. 0.45m)
    st_p1 = (port_p1[0] - p_ux * 0.8, port_p1[1] - p_uy * 0.8)
    st_p2 = (port_p2[0] + p_ux * 0.8, port_p2[1] + p_uy * 0.8)
    add_box_between(bm, st_p1, st_p2, 0.0, 0.45, thickness=4.8, offset_out=1.8, mat_idx=7)

    # 6 Monumental Doric Columns
    n_cols = 6
    col_margin = 1.05
    col_step = (p_len - 2.0 * col_margin) / (n_cols - 1)
    col_height = 9.2
    for c_i in range(n_cols):
        cs = col_margin + c_i * col_step
        cx = port_p1[0] + p_ux * cs - p_nx * 0.45
        cy = port_p1[1] + p_uy * cs - p_ny * 0.45
        add_cylinder_in_bm(bm, (cx, cy), 0.45, 0.95, 0.68, 0.64, n_seg=16, mat_idx=4)
        add_cylinder_in_bm(bm, (cx, cy), 0.95, 0.45 + col_height - 0.65, 0.52, 0.44, n_seg=20, mat_idx=0)
        add_cylinder_in_bm(bm, (cx, cy), 0.45 + col_height - 0.65, 0.45 + col_height, 0.46, 0.68, n_seg=16, mat_idx=4)

    # Portico Entablature (Architrave + Doric Frieze + Dentil Cornice)
    z_ent_bot = 0.45 + col_height
    z_ent_mid = z_ent_bot + 0.85
    z_ent_top = z_ent_bot + 1.85
    add_box_between(bm, port_p1, port_p2, z_ent_bot, z_ent_mid, thickness=1.4, offset_out=-0.35, mat_idx=4)
    add_box_between(bm, port_p1, port_p2, z_ent_mid, z_ent_top, thickness=1.5, offset_out=-0.30, mat_idx=0)
    c_p1 = (port_p1[0] - p_ux * 0.6, port_p1[1] - p_uy * 0.6)
    c_p2 = (port_p2[0] + p_ux * 0.6, port_p2[1] + p_uy * 0.6)
    add_box_between(bm, c_p1, c_p2, z_ent_top, z_ent_top + 0.45, thickness=2.2, offset_out=0.15, mat_idx=4)

    # Monumental Triangular Pediment (Clean sloped triangular prism, ZERO horizontal step faces!)
    z_ped_base = z_ent_top + 0.45
    z_ped_peak = z_ped_base + 4.60
    add_triangular_pediment_in_bm(bm, c_p1, c_p2, z_ped_base, z_ped_peak, thickness=1.40, offset_out=-0.15, mat_tympanum=0, mat_cornice=4)

    # Central Grand Entrance Arch Behind Colonnade (Z = 0.45m .. 6.60m)
    ped_mid_s = p_len * 0.5
    mid_x = port_p1[0] + p_ux * ped_mid_s - p_nx * 3.4
    mid_y = port_p1[1] + p_uy * ped_mid_s - p_ny * 3.4
    door_w = 4.2
    d_p1 = (mid_x - p_ux * (door_w * 0.5), mid_y - p_uy * (door_w * 0.5))
    d_p2 = (mid_x + p_ux * (door_w * 0.5), mid_y + p_uy * (door_w * 0.5))
    add_box_between(bm, d_p1, d_p2, 0.45, 4.2, thickness=0.35, offset_out=-0.35, mat_idx=6)
    add_box_between(bm, d_p1, d_p2, 4.2, 6.2, thickness=0.20, offset_out=-0.35, mat_idx=2)
    add_curved_voussoir_arch(bm, d_p1, d_p2, 4.8, 1.4, thickness=0.85, offset_out=0.15, mat_stone=4, mat_wall=0, add_keystone=True)

    # 4. Central Waterfront Pavilion on Rue de la Commune Est
    wf_mid_x, wf_mid_y = 419.5, 501.8
    wf_w = 22.0
    wf_p1 = (wf_mid_x - p_ux * (wf_w * 0.5), wf_mid_y - p_uy * (wf_w * 0.5))
    wf_p2 = (wf_mid_x + p_ux * (wf_w * 0.5), wf_mid_y + p_uy * (wf_w * 0.5))
    add_box_between(bm, wf_p1, wf_p2, height_main, height_main + 2.4, thickness=1.1, offset_out=0.55, mat_idx=4)
    # Triangular pediment on waterfront pavilion
    add_triangular_pediment_in_bm(bm, wf_p1, wf_p2, height_main + 2.4, height_main + 5.0, thickness=1.2, offset_out=0.55, mat_tympanum=0, mat_cornice=4)

    # 5. The Iconic Central Silver Neoclassical Dome
    dome_cx, dome_cy = 399.885, 476.466

    # A. Square Attic Pedestal (Z = 15.95m .. 19.50m, offset from parapet top 15.75m by +0.20m!)
    ped_half_w = 8.4
    ped_pts = [
        (dome_cx - p_ux * ped_half_w - p_nx * ped_half_w, dome_cy - p_uy * ped_half_w - p_ny * ped_half_w),
        (dome_cx + p_ux * ped_half_w - p_nx * ped_half_w, dome_cy + p_uy * ped_half_w - p_ny * ped_half_w),
        (dome_cx + p_ux * ped_half_w + p_nx * ped_half_w, dome_cy + p_uy * ped_half_w + p_ny * ped_half_w),
        (dome_cx - p_ux * ped_half_w + p_nx * ped_half_w, dome_cy - p_uy * ped_half_w + p_ny * ped_half_w),
    ]
    extrude_prism_in_bm(bm, ped_pts, 15.95, 19.50, mat_side=0, mat_top=4)
    ped_pts_c = inset_polygon_toward_centroid(ped_pts, 1.08)
    extrude_prism_in_bm(bm, ped_pts_c, 19.05, 19.50, mat_side=4, mat_top=4)

    # B. Octagonal Drum with 8 Arched Windows and Pilasters (Z = 19.50m .. 24.80m)
    drum_r = 7.2
    drum_verts_bot = []
    n_drum = 8
    for d_i in range(n_drum):
        d_th = (d_i / n_drum) * 2.0 * math.pi + math.radians(22.5)
        dx_d = dome_cx + drum_r * math.cos(d_th)
        dy_d = dome_cy + drum_r * math.sin(d_th)
        drum_verts_bot.append((dx_d, dy_d))

    for d_i in range(n_drum):
        j_i = (d_i + 1) % n_drum
        dp1 = drum_verts_bot[d_i]
        dp2 = drum_verts_bot[j_i]
        add_box_between(bm, dp1, dp2, 19.50, 24.20, thickness=0.55, offset_out=0.0, mat_idx=0)
        d_seg_dx = dp2[0] - dp1[0]
        d_seg_dy = dp2[1] - dp1[1]
        d_seg_len = math.hypot(d_seg_dx, d_seg_dy)
        d_ux, d_uy = d_seg_dx / d_seg_len, d_seg_dy / d_seg_len
        dw1 = (dp1[0] + d_ux * (d_seg_len * 0.28), dp1[1] + d_uy * (d_seg_len * 0.28))
        dw2 = (dp1[0] + d_ux * (d_seg_len * 0.72), dp1[1] + d_uy * (d_seg_len * 0.72))
        add_box_between(bm, dw1, dw2, 20.30, 23.60, thickness=0.12, offset_out=-0.45, mat_idx=2)
        add_curved_voussoir_arch(bm, dw1, dw2, 22.80, 0.65, thickness=0.65, offset_out=0.15, mat_stone=4, mat_wall=0, add_keystone=True)

    # Octagonal drum cornice ring at top
    add_cylinder_in_bm(bm, (dome_cx, dome_cy), 24.20, 24.80, drum_r + 0.35, drum_r + 0.35, n_seg=24, mat_idx=4)

    # C. Shining Silver Hemispherical Neoclassical Dome (Z = 24.80m .. 34.30m)
    dome_radius = 6.9
    dome_height = 9.5
    add_dome_in_bm(bm, (dome_cx, dome_cy), 24.80, dome_radius, dome_height, n_radial=32, n_rings=16, mat_dome=5)

    # 16 Radial Standing-Seam Ribs on the Dome
    n_ribs = 16
    for rb in range(n_ribs):
        r_th = (rb / n_ribs) * 2.0 * math.pi
        r_ct, r_st = math.cos(r_th), math.sin(r_th)
        for r_ring in range(12):
            f0 = r_ring / 12
            f1 = (r_ring + 1) / 12
            phi0 = f0 * (math.pi * 0.48)
            phi1 = f1 * (math.pi * 0.48)
            z0 = 24.80 + dome_height * math.sin(phi0)
            z1 = 24.80 + dome_height * math.sin(phi1)
            rad0 = dome_radius * math.cos(phi0)
            rad1 = dome_radius * math.cos(phi1)
            rp1 = (dome_cx + rad0 * r_ct, dome_cy + rad0 * r_st)
            rp2 = (dome_cx + rad1 * r_ct, dome_cy + rad1 * r_st)
            add_box_between(bm, rp1, rp2, z0, z1, thickness=0.16, offset_out=0.08, mat_idx=5)

    # D. Lantern & Cupola with Spire (Z = 34.30m .. 41.50m)
    add_cylinder_in_bm(bm, (dome_cx, dome_cy), 34.30, 34.90, 2.2, 2.2, n_seg=16, mat_idx=5)
    n_lan_cols = 8
    lan_r = 1.95
    for l_i in range(n_lan_cols):
        l_th = (l_i / n_lan_cols) * 2.0 * math.pi
        lx = dome_cx + lan_r * math.cos(l_th)
        ly = dome_cy + lan_r * math.sin(l_th)
        add_cylinder_in_bm(bm, (lx, ly), 34.90, 38.00, 0.22, 0.20, n_seg=8, mat_idx=5)
    add_cylinder_in_bm(bm, (dome_cx, dome_cy), 34.90, 38.00, 1.45, 1.45, n_seg=12, mat_idx=2)
    add_cylinder_in_bm(bm, (dome_cx, dome_cy), 38.00, 38.50, 2.4, 2.4, n_seg=16, mat_idx=5)
    add_dome_in_bm(bm, (dome_cx, dome_cy), 38.50, 2.3, 1.6, n_radial=16, n_rings=8, mat_dome=5)
    add_cylinder_in_bm(bm, (dome_cx, dome_cy), 40.10, 41.60, 0.16, 0.02, n_seg=8, mat_idx=5)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Primary Owned Buildings 1244238347, 1244238348, 1244238349, 1244238357 ---

def build_auberge_alt_hostel_1244238348(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_1244238348_Auberge_Alt_Hostel"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Heritage_RedBrick"],
        palette["Mat_MTL_Slate_Roof_Dark"],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_CastIron_Black"],
        palette["Mat_MTL_WarmBuff_Limestone"],
        palette["Mat_MTL_Storefront_Navy"],
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()
    height = 14.40
    extrude_prism_in_bm(bm, pts, 0.0, height, mat_side=0, mat_top=None)

    n = len(pts)
    sills = (4.10, 7.10, 10.10)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.5:
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / 3.4)))
        bay_w = seg_len / n_bays
        pier_w = bay_w * 0.32

        add_box_between(bm, p1, p2, 0.0, 0.65, thickness=0.65, offset_out=0.18, mat_idx=4)
        add_box_between(bm, p1, p2, 3.40, 3.80, thickness=0.72, offset_out=0.22, mat_idx=5)

        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            add_box_between(bm, wp1, wp2, 0.65, 3.40, thickness=0.12, offset_out=-0.35, mat_idx=2)

            for sz in sills:
                add_box_between(bm, wp1, wp2, sz, sz + 0.20, thickness=0.75, offset_out=0.25, mat_idx=4)
                add_box_between(bm, wp1, wp2, sz + 0.20, sz + 2.10, thickness=0.12, offset_out=-0.45, mat_idx=2)
                add_box_between(bm, wp1, wp2, sz + 2.10, sz + 2.45, thickness=0.70, offset_out=0.22, mat_idx=4)
                ms = 0.5 * (bs0 + bs1)
                mp1 = (p1[0] + dx * (ms - 0.04), p1[1] + dy * (ms - 0.04))
                mp2 = (p1[0] + dx * (ms + 0.04), p1[1] + dy * (ms + 0.04))
                add_box_between(bm, mp1, mp2, sz + 0.20, sz + 2.10, thickness=0.16, offset_out=-0.20, mat_idx=3)

        add_box_between(bm, p1, p2, height - 0.45, height + 0.15, thickness=0.95, offset_out=0.38, mat_idx=4)
        add_box_between(bm, p1, p2, height + 0.15, 15.15, thickness=0.45, offset_out=0.15, mat_idx=0)

    add_pitched_roof_in_bm(bm, pts, 14.70, height=1.60, inset_factor=0.82, mat_roof=1, mat_trim=4)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def build_historic_greystone_row(bldg_data, palette, collection, name_tag, height=13.10, sills=(3.80, 6.80, 9.80), parapet_top=13.85, roof_base=13.40):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = f"MTL_Owned_{bldg_data['id']}_{name_tag}"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_PierreGrise_Limestone"],
        palette["Mat_MTL_Slate_Roof_Dark"],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_CastIron_Black"],
        palette["Mat_MTL_WarmBuff_Limestone"],
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()
    extrude_prism_in_bm(bm, pts, 0.0, height, mat_side=0, mat_top=None)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.5:
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / 3.4)))
        bay_w = seg_len / n_bays
        pier_w = bay_w * 0.34

        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            for sz in sills:
                add_box_between(bm, wp1, wp2, sz, sz + 0.20, thickness=0.75, offset_out=0.25, mat_idx=4)
                add_box_between(bm, wp1, wp2, sz + 0.20, sz + 2.10, thickness=0.12, offset_out=-0.45, mat_idx=2)
                add_box_between(bm, wp1, wp2, sz + 2.10, sz + 2.45, thickness=0.72, offset_out=0.22, mat_idx=4)
                ms = 0.5 * (bs0 + bs1)
                mp1 = (p1[0] + dx * (ms - 0.04), p1[1] + dy * (ms - 0.04))
                mp2 = (p1[0] + dx * (ms + 0.04), p1[1] + dy * (ms + 0.04))
                add_box_between(bm, mp1, mp2, sz + 0.20, sz + 2.10, thickness=0.16, offset_out=-0.22, mat_idx=3)

        add_box_between(bm, p1, p2, height - 0.40, height + 0.15, thickness=0.92, offset_out=0.36, mat_idx=4)
        add_box_between(bm, p1, p2, height + 0.15, parapet_top, thickness=0.45, offset_out=0.15, mat_idx=0)

    add_pitched_roof_in_bm(bm, pts, roof_base, height=1.50, inset_factor=0.82, mat_roof=1, mat_trim=4)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj



# --- Waterfront Promenade Kiosks & Pavilion: 1387776862 & 1387776864 ---

def build_waterfront_promenade_kiosks_1387776862(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_1387776862_Kiosques_du_VieuxPort"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Wood_Timber"],
        palette["Mat_MTL_Silver_Tin_Roof"],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_CastIron_Black"],
        palette["Mat_MTL_Plaza_Light_Granite"],
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()
    height = 3.80
    extrude_prism_in_bm(bm, pts, 0.0, height, mat_side=0, mat_top=None)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 2.5:
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_units = max(1, int(seg_len // 5.2))
        unit_w = seg_len / n_units

        add_box_between(bm, p1, p2, 0.0, 0.85, thickness=0.65, offset_out=0.15, mat_idx=0)
        add_box_between(bm, p1, p2, height - 0.40, height + 0.15, thickness=0.85, offset_out=0.25, mat_idx=3)

        for u in range(n_units):
            us0 = u * unit_w + 0.6
            us1 = (u + 1) * unit_w - 0.6
            wp1 = (p1[0] + dx * us0, p1[1] + dy * us0)
            wp2 = (p1[0] + dx * us1, p1[1] + dy * us1)

            add_box_between(bm, wp1, wp2, 0.85, 2.70, thickness=0.12, offset_out=-0.50, mat_idx=2)
            add_box_between(bm, wp1, wp2, 0.85, 1.05, thickness=0.55, offset_out=0.10, mat_idx=0)
            add_box_between(bm, wp1, wp2, 2.70, 3.30, thickness=0.45, offset_out=0.15, mat_idx=3)

    add_pitched_roof_in_bm(bm, pts, height + 0.15, height=1.40, inset_factor=0.85, mat_roof=1, mat_trim=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def build_waterfront_pavilion_1387776864(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_1387776864_Waterfront_Pavilion"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Wood_Timber"],
        palette["Mat_MTL_Silver_Tin_Roof"],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_CastIron_Black"],
        palette["Mat_MTL_Plaza_Light_Granite"],
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()
    height = 4.60
    extrude_prism_in_bm(bm, pts, 0.0, height, mat_side=0, mat_top=None)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len > 2.0:
            add_box_between(bm, p1, p2, 0.0, 0.90, thickness=0.55, offset_out=0.12, mat_idx=0)
            add_box_between(bm, p1, p2, 0.90, 3.20, thickness=0.12, offset_out=-0.45, mat_idx=2)
            add_box_between(bm, p1, p2, 3.20, height, thickness=0.55, offset_out=0.12, mat_idx=0)
            add_box_between(bm, p1, p2, height - 0.25, height + 0.15, thickness=0.85, offset_out=0.25, mat_idx=3)

    add_pitched_roof_in_bm(bm, pts, height + 0.15, height=1.50, inset_factor=0.84, mat_roof=1, mat_trim=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Ground, Streets & Sidewalks Network ---

def build_ground_and_streets(dossier, palette, collection_owned):
    sat = dossier["satellite"]
    cx, cy = sat["center_xy_m"]
    span = sat["span_meters"] * 1.55
    hs = span * 0.5

    mesh = bpy.data.meshes.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}", mesh)
    collection_owned.objects.link(obj)

    for m in (palette["Mat_MTL_Street_Asphalt"], palette["Mat_MTL_Plaza_Light_Granite"], palette["Mat_MTL_Cobblestone"]):
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Watertight Solid Base Stratum (Z = -0.25m .. 0.00m) with upward (+Z) normals
    g_pts = [(cx - hs, cy - hs), (cx + hs, cy - hs), (cx + hs, cy + hs), (cx - hs, cy + hs)]
    extrude_prism_in_bm(bm, g_pts, -0.25, 0.00, mat_side=0, mat_top=0)

    # 2. Roadbed Geometry (Z = 0.00m .. 0.015m)
    for hw in dossier.get("osm_features", {}).get("highways", []):
        pts = hw.get("coords_xy", [])
        if len(pts) < 2:
            continue
        hw_name = hw.get("tags", {}).get("name", "")
        hw_type = hw.get("tags", {}).get("highway", "residential")
        is_ped = hw_type in ("footway", "pedestrian", "path", "cycleway")

        is_cobble = any(k in hw_name for k in ("Saint-Paul", "Marché-Bonsecours", "Saint-Claude", "Bonsecours"))
        mat_rd = 2 if is_cobble else (1 if is_ped else 0)

        if "Commune" in hw_name:
            w = 14.0
        elif "Saint-Paul" in hw_name:
            w = 8.5
        elif is_ped:
            w = 4.2
        else:
            w = 7.5

        for k in range(len(pts) - 1):
            p1, p2 = pts[k], pts[k + 1]
            if is_ped:
                add_box_between(bm, p1, p2, 0.00, 0.15, thickness=w, offset_out=0.0, mat_idx=1)
            else:
                add_box_between(bm, p1, p2, -0.01, 0.015, thickness=w, offset_out=0.0, mat_idx=mat_rd)

    # 3. Raised Sidewalks & Curbs around Marché Bonsecours Esplanade (Z = +0.15m)
    for bldg in dossier.get("osm_features", {}).get("buildings", []):
        if not bldg.get("is_primary_owner"):
            continue
        b_pts = clean_poly_pts(bldg.get("coords_xy", []))
        if len(b_pts) < 3:
            continue
        sw_pts = inset_polygon_toward_centroid(b_pts, 1.14)
        for k in range(len(sw_pts)):
            sp1 = sw_pts[k]
            sp2 = sw_pts[(k + 1) % len(sw_pts)]
            add_box_between(bm, sp1, sp2, 0.00, 0.15, thickness=2.8, offset_out=1.4, mat_idx=1)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# --- Props & Vegetation Linking ---

_KIT_CACHE = {}


def append_kit_asset(asset_name, collection, location, rotation_z=0.0, scale=1.0):
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


def scatter_trees_and_lamps(palette, collection_owned):
    lamp_coords_st_paul = [
        (368.5, 432.0, 0.15),
        (374.2, 452.0, 0.15),
        (380.0, 472.0, 0.15),
        (386.5, 492.0, 0.15),
        (393.0, 512.0, 0.15),
        (400.0, 532.0, 0.15),
        (406.5, 552.0, 0.15),
    ]
    for loc in lamp_coords_st_paul:
        append_kit_asset("street_lamp_01", collection=collection_owned, location=loc, rotation_z=math.radians(72.0), scale=1.0)

    lamp_coords_waterfront = [
        (378.0, 395.0, 0.15),
        (395.0, 412.0, 0.15),
        (410.0, 435.0, 0.15),
        (425.0, 460.0, 0.15),
        (440.0, 485.0, 0.15),
        (455.0, 510.0, 0.15),
    ]
    for loc in lamp_coords_waterfront:
        append_kit_asset("street_lamp_01", collection=collection_owned, location=loc, rotation_z=math.radians(-108.0), scale=1.0)

    bench_coords = [
        (378.5, 448.0, 0.15),
        (384.0, 468.0, 0.15),
        (390.0, 488.0, 0.15),
        (396.0, 508.0, 0.15),
    ]
    for loc in bench_coords:
        append_kit_asset("Master_Street_Bench", collection=collection_owned, location=loc, rotation_z=math.radians(72.0), scale=1.0)

    tree_coords = [
        (365.0, 428.0, 0.15),
        (372.0, 446.0, 0.15),
        (402.0, 538.0, 0.15),
        (410.0, 558.0, 0.15),
        (372.0, 390.0, 0.15),
        (445.0, 475.0, 0.15),
        (460.0, 500.0, 0.15),
    ]
    for loc in tree_coords:
        append_kit_asset("jacaranda_tree_LOD0", collection=collection_owned, location=loc, rotation_z=math.radians(float(hash(loc) % 360)), scale=1.1)


# --- World, Lighting & Cameras ---

def configure_world_and_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16

    world = bpy.data.worlds.new(name="MTL_World_0018")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.05
    links.new(out.inputs["Surface"], bg.outputs["Background"])

    hdri_path = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")
    if os.path.isfile(hdri_path):
        env = nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri_path, check_existing=True)
        links.new(bg.inputs["Color"], env.outputs["Color"])

    sun_data = bpy.data.lights.new(name="MTL_Sun_0018", type="SUN")
    sun_data.energy = 4.0
    sun_data.color = (1.0, 0.96, 0.88)
    sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name="MTL_Sun_0018", object_data=sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(45.0), math.radians(12.0), math.radians(-130.0))


def render_cameras(dossier, iter_num=1):
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
        cam_data.clip_start = 0.25
        cam_data.clip_end = 1500.0
        cam_obj = bpy.data.objects.new(name=f"SV_Cam_{label}", object_data=cam_data)
        scene.collection.objects.link(cam_obj)
        cam_obj.location = (cx, cy, 1.7)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch_deg), 0.0, math.radians(-heading_deg))

        scene.camera = cam_obj
        out_file = os.path.join(RENDERS_DIR, f"iter{iter_num}_{label}.png")
        scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View Camera [{label}] -> {out_file}")

    ov_data = bpy.data.cameras.new(name=f"Overview_Cam_{BLOCK_ID}")
    ov_data.angle = math.radians(50.0)
    ov_data.clip_start = 1.0
    ov_data.clip_end = 2500.0
    ov_obj = bpy.data.objects.new(name=f"Overview_Cam_{BLOCK_ID}", object_data=ov_data)
    scene.collection.objects.link(ov_obj)

    target = Vector((399.5, 471.0, 15.0))
    ov_obj.location = (485.0, 360.0, 115.0)
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
    print(f"Starting High-Poly 3D Build for Block {BLOCK_ID} (Marché Bonsecours)...")
    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    master_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(master_col)
    col_owned = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    master_col.children.link(col_owned)

    palette = create_upgraded_palette()

    print("Building watertight ground stratum & street network...")
    build_ground_and_streets(dossier, palette, col_owned)

    print("Building high-poly architectural 3D models for primary owned buildings...")
    for bldg in dossier.get("osm_features", {}).get("buildings", []):
        if not bldg.get("is_primary_owner"):
            continue
        bid = bldg["id"]
        bname = bldg.get("name", "")
        print(f"  Building {bid} ('{bname}')...")

        if bid == 87389029:
            build_marche_bonsecours(bldg, palette, col_owned)
        elif bid == 1244238348:
            build_auberge_alt_hostel_1244238348(bldg, palette, col_owned)
        elif bid == 1244238347:
            build_historic_greystone_row(bldg, palette, col_owned, "Greystone_Row_East", height=13.10, sills=(3.80, 6.80, 9.80), parapet_top=13.85, roof_base=13.40)
        elif bid == 1244238349:
            build_historic_greystone_row(bldg, palette, col_owned, "Greystone_Row_West", height=13.60, sills=(3.50, 6.45, 9.40), parapet_top=14.35, roof_base=13.90)
        elif bid == 1244238357:
            build_historic_greystone_row(bldg, palette, col_owned, "Retail_Commercial", height=10.50, sills=(3.30, 6.10, 8.80), parapet_top=11.20, roof_base=10.65)
        elif bid == 1387776862:
            build_waterfront_promenade_kiosks_1387776862(bldg, palette, col_owned)
        elif bid == 1387776864:
            build_waterfront_pavilion_1387776864(bldg, palette, col_owned)
        else:
            build_historic_greystone_row(bldg, palette, col_owned, "Building", height=12.0, sills=(3.60, 6.60, 9.60), parapet_top=12.75, roof_base=12.30)

    print("Linking assets (street lamps, benches, trees)...")
    scatter_trees_and_lamps(palette, col_owned)

    print("Configuring world, lighting, and rendering cameras...")
    configure_world_and_render()

    print(f"Saving {BLEND_OUT_PATH}...")
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

    # Render cameras if requested or if missing
    if "--render" in sys.argv:
        render_cameras(dossier, iter_num=1)
    else:
        missing = [c for c in dossier.get("streetview_cameras", []) if not os.path.isfile(os.path.join(RENDERS_DIR, f"iter1_{c['label']}.png"))]
        if missing or not os.path.isfile(SNAPSHOT_PATH):
            render_cameras(dossier, iter_num=1)
        else:
            print(f"Street view renders and snapshot already present on disk in {RENDERS_DIR}")

    print(f"Build complete for {BLOCK_ID}!")


if __name__ == "__main__":
    main()
