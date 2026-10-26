"""
Build Script for Montreal Block MTL-VM-0004:
Édifice Aldred (507 Place d'Armes) Art Deco Ziggurat Skyscraper,
New York Life Red Sandstone Building (511 Place d'Armes) with Clock Tower,
Édifice Duluth (501 Place d'Armes) Corner Turret Building,
Rue Saint-Sulpice & Rue De Brésoles Limestone Commercial Buildings,
and Old Montreal Contiguous Stone Buildings East of Côte de la Place d'Armes.

Photorealism & Anti-Boxiness Standards Applied:
- Real Poly Haven 2K PBR Textures (`sandstone_blocks_05`, `castle_brick_02_red`, `cobblestone_floor_08`, `asphalt_02`) with `projection='BOX'` (`Object` coordinates)
- Real Poly Haven 2K Outdoor HDRI (`kloppenheim_06_puresky_2k.hdr`) + directional sun
- Deep `0.48m+` 3D recessed window bays, projecting stone sills/lintels/keystones, 3D window mullions, rusticated ashlar courses, modillion cornices, and `BEVEL` modifiers (`width=0.03m, segments=2`)
- Reflective architectural glass (`Roughness=0.05, IOR=1.52, Metallic=0.28`) catching real HDRI sky reflections
- High-poly organic multi-branch smooth-shaded trees and ornate cast-iron streetlamps
- Exact camera alignment with the 4 official outdoor Google Street View panoramas in `dossier.json`.
"""

import os
import sys
import json
import math
import random
import bpy
import bmesh
from mathutils import Vector

# Import shared Montreal Material & Asset Kit
SRC_DIR = r"C:\Users\Felipe\Documents\coding\montreal\src"
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)
import build_montreal_kit as kit

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
BLOCK_ID = "MTL-VM-0004"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_BLOCKS_DIR = os.path.join(BASE_DIR, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_BLOCKS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def get_or_create_collection(name, parent=None):
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
    else:
        col = bpy.data.collections.new(name)
        if parent is None:
            bpy.context.scene.collection.children.link(col)
        else:
            parent.children.link(col)
    return col


def load_image_cached(path, non_color=False):
    if not os.path.exists(path):
        return None
    fname = os.path.basename(path)
    if fname in bpy.data.images:
        img = bpy.data.images[fname]
    else:
        img = bpy.data.images.load(path)
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    return img


def apply_polyhaven_box_pbr(mat, diff_path, rough_path, norm_path, tint_hex="#FFFFFF", tint_fac=0.35, scale=0.32, norm_strength=0.55, roughness_mult=1.0):
    """Upgrades a Blender material with real 2K Poly Haven Diffuse, Roughness, and Normal maps using seamless Object BOX projection."""
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(out.inputs["Surface"], bsdf.outputs["BSDF"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(mapping.inputs["Vector"], tex_coord.outputs["Object"])

    img_diff = load_image_cached(diff_path, non_color=False)
    if img_diff:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = img_diff
        tex_d.projection = 'BOX'
        tex_d.projection_blend = 0.25
        links.new(tex_d.inputs["Vector"], mapping.outputs["Vector"])

        mix = nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY' if tint_fac > 0.5 else 'MIX'
        mix.inputs["Factor"].default_value = tint_fac
        rgba = kit.hex_to_rgba(tint_hex)
        links.new(mix.inputs[6], tex_d.outputs["Color"])
        mix.inputs[7].default_value = rgba
        links.new(bsdf.inputs["Base Color"], mix.outputs[2])
    else:
        bsdf.inputs["Base Color"].default_value = kit.hex_to_rgba(tint_hex)

    img_rough = load_image_cached(rough_path, non_color=True)
    if img_rough:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = img_rough
        tex_r.projection = 'BOX'
        tex_r.projection_blend = 0.25
        links.new(tex_r.inputs["Vector"], mapping.outputs["Vector"])
        math_r = nodes.new("ShaderNodeMath")
        math_r.operation = 'MULTIPLY'
        math_r.inputs[1].default_value = roughness_mult
        links.new(math_r.inputs[0], tex_r.outputs["Color"])
        links.new(bsdf.inputs["Roughness"], math_r.outputs["Value"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.75

    img_norm = load_image_cached(norm_path, non_color=True)
    if img_norm:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = img_norm
        tex_n.projection = 'BOX'
        tex_n.projection_blend = 0.25
        links.new(tex_n.inputs["Vector"], mapping.outputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.space = 'OBJECT'
        nmap.inputs["Strength"].default_value = norm_strength
        links.new(nmap.inputs["Color"], tex_n.outputs["Color"])
        links.new(bsdf.inputs["Normal"], nmap.outputs["Normal"])

    return mat


def upgrade_palette_with_polyhaven_2k(palette):
    """Applies real 2K Poly Haven PBR maps and reflective architectural glass to the shared Montreal material palette."""
    sand_d = os.path.join(POLYHAVEN_DIR, "sandstone_blocks_05_Diffuse_2k.jpg")
    sand_r = os.path.join(POLYHAVEN_DIR, "sandstone_blocks_05_Rough_2k.jpg")
    sand_n = os.path.join(POLYHAVEN_DIR, "sandstone_blocks_05_nor_gl_2k.jpg")

    brick_d = os.path.join(POLYHAVEN_DIR, "castle_brick_02_red_Diffuse_2k.jpg")
    brick_r = os.path.join(POLYHAVEN_DIR, "castle_brick_02_red_Rough_2k.jpg")
    brick_n = os.path.join(POLYHAVEN_DIR, "castle_brick_02_red_nor_gl_2k.jpg")

    cobble_d = os.path.join(POLYHAVEN_DIR, "cobblestone_floor_08_Diffuse_2k.jpg")
    cobble_r = os.path.join(POLYHAVEN_DIR, "cobblestone_floor_08_Rough_2k.jpg")
    cobble_n = os.path.join(POLYHAVEN_DIR, "cobblestone_floor_08_nor_gl_2k.jpg")

    asph_d = os.path.join(POLYHAVEN_DIR, "asphalt_02_Diffuse_2k.jpg")
    asph_r = os.path.join(POLYHAVEN_DIR, "asphalt_02_Rough_2k.jpg")
    asph_n = os.path.join(POLYHAVEN_DIR, "asphalt_02_nor_gl_2k.jpg")

    apply_polyhaven_box_pbr(
        palette["Mat_MTL_PierreGrise_Limestone"],
        sand_d, sand_r, sand_n,
        tint_hex="#B5B2AC", tint_fac=0.45, scale=0.36, norm_strength=0.45, roughness_mult=0.92
    )
    apply_polyhaven_box_pbr(
        palette["Mat_MTL_WarmBuff_Limestone"],
        sand_d, sand_r, sand_n,
        tint_hex="#D2C4AA", tint_fac=0.42, scale=0.34, norm_strength=0.42, roughness_mult=0.88
    )
    apply_polyhaven_box_pbr(
        palette["Mat_MTL_Fieldstone_Rubble"],
        sand_d, sand_r, sand_n,
        tint_hex="#9C978E", tint_fac=0.45, scale=0.40, norm_strength=0.52, roughness_mult=0.95
    )
    apply_polyhaven_box_pbr(
        palette["Mat_MTL_Red_Sandstone"],
        sand_d, sand_r, sand_n,
        tint_hex="#A44A32", tint_fac=0.58, scale=0.35, norm_strength=0.50, roughness_mult=0.90
    )
    apply_polyhaven_box_pbr(
        palette["Mat_MTL_Heritage_RedBrick"],
        brick_d, brick_r, brick_n,
        tint_hex="#8F392B", tint_fac=0.35, scale=0.48, norm_strength=0.50, roughness_mult=0.95
    )
    apply_polyhaven_box_pbr(
        palette["Mat_MTL_Cobblestone"],
        cobble_d, cobble_r, cobble_n,
        tint_hex="#7A7670", tint_fac=0.28, scale=0.45, norm_strength=0.55, roughness_mult=0.86
    )
    apply_polyhaven_box_pbr(
        palette["Mat_MTL_Plaza_Light_Granite"],
        asph_d, asph_r, asph_n,
        tint_hex="#C6C2B9", tint_fac=0.65, scale=0.40, norm_strength=0.25, roughness_mult=0.78
    )
    apply_polyhaven_box_pbr(
        palette["Mat_MTL_Plaza_Charcoal_Granite"],
        cobble_d, cobble_r, cobble_n,
        tint_hex="#5A5D62", tint_fac=0.55, scale=0.50, norm_strength=0.35, roughness_mult=0.80
    )
    apply_polyhaven_box_pbr(
        palette["Mat_MTL_Street_Asphalt"],
        asph_d, asph_r, asph_n,
        tint_hex="#3E4045", tint_fac=0.32, scale=0.30, norm_strength=0.40, roughness_mult=0.90
    )

    # Reflective Architectural Window Glass (Roughness=0.05, IOR=1.52, Metallic=0.28)
    glass_mat = palette["Mat_MTL_Window_Glass_Dark"]
    glass_mat.use_nodes = True
    gnodes = glass_mat.node_tree.nodes
    glinks = glass_mat.node_tree.links
    gnodes.clear()
    g_out = gnodes.new("ShaderNodeOutputMaterial")
    g_bsdf = gnodes.new("ShaderNodeBsdfPrincipled")
    g_bsdf.inputs["Roughness"].default_value = 0.05
    g_bsdf.inputs["Metallic"].default_value = 0.28
    if "IOR" in g_bsdf.inputs:
        g_bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in g_bsdf.inputs:
        g_bsdf.inputs["Specular IOR Level"].default_value = 0.88

    tc = gnodes.new("ShaderNodeTexCoord")
    vor = gnodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 0.45
    ramp = gnodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.04, 0.07, 0.11, 1.0)
    ramp.color_ramp.elements[1].position = 0.80
    ramp.color_ramp.elements[1].color = (0.28, 0.22, 0.15, 1.0)
    glinks.new(vor.inputs["Vector"], tc.outputs["Object"])
    glinks.new(ramp.inputs["Fac"], vor.outputs["Color"])
    glinks.new(g_bsdf.inputs["Base Color"], ramp.outputs["Color"])
    glinks.new(g_out.inputs["Surface"], g_bsdf.outputs["BSDF"])

    # Custom Heritage Forest Green Wood Frame & Striped Awning materials (for 70 Rue Notre-Dame in NY_Life_Red_Sandstone_Corner.jpg)
    palette["Mat_MTL_Heritage_GreenFrame"] = kit.get_or_create_pbr_material("Mat_MTL_Heritage_GreenFrame", "#24472E", roughness=0.42, bump_strength=0.04)
    palette["Mat_MTL_Awning_Red"] = kit.get_or_create_pbr_material("Mat_MTL_Awning_Red", "#B8332A", roughness=0.75, bump_strength=0.08)


def clean_poly_pts(coords_xy):
    pts = [(float(p[0]), float(p[1])) for p in coords_xy]
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05:
        pts = pts[:-1]
    cleaned = []
    for p in pts:
        if not cleaned or math.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > 0.15:
            cleaned.append(p)
    if len(cleaned) > 2 and math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) < 0.15:
        cleaned.pop()
    return cleaned


def signed_area_2d(pts):
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
    return 0.5 * area


def ensure_ccw(pts):
    if signed_area_2d(pts) < 0:
        return list(reversed(pts))
    return pts


def inset_polygon_toward_centroid(pts, factor):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return [(cx + (p[0] - cx) * factor, cy + (p[1] - cy) * factor) for p in pts]


def add_bevel_modifier(obj, width=0.03, segments=2):
    bev = obj.modifiers.new(name="Arch_Bevel", type='BEVEL')
    bev.width = width
    bev.segments = segments
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(35.0)
    if hasattr(bev, "harden_normals"):
        bev.harden_normals = False


def add_box_between(bm, p1, p2, z_min, z_max, thickness, offset_out=0.0, mat_idx=0, cap_top=True, cap_bottom=True):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-4 or z_max <= z_min:
        return
    ux, uy = dx / length, dy / length
    nx, ny = uy, -ux  # Outward normal for CCW polygon

    ox1 = p1[0] + nx * (offset_out - thickness * 0.5)
    oy1 = p1[1] + ny * (offset_out - thickness * 0.5)
    ox2 = p2[0] + nx * (offset_out - thickness * 0.5)
    oy2 = p2[1] + ny * (offset_out - thickness * 0.5)

    ix1 = p1[0] + nx * (offset_out + thickness * 0.5)
    iy1 = p1[1] + ny * (offset_out + thickness * 0.5)
    ix2 = p2[0] + nx * (offset_out + thickness * 0.5)
    iy2 = p2[1] + ny * (offset_out + thickness * 0.5)

    v0 = bm.verts.new((ox1, oy1, z_min))
    v1 = bm.verts.new((ox2, oy2, z_min))
    v2 = bm.verts.new((ix2, iy2, z_min))
    v3 = bm.verts.new((ix1, iy1, z_min))
    v4 = bm.verts.new((ox1, oy1, z_max))
    v5 = bm.verts.new((ox2, oy2, z_max))
    v6 = bm.verts.new((ix2, iy2, z_max))
    v7 = bm.verts.new((ix1, iy1, z_max))

    faces = [
        (v0, v4, v5, v1),
        (v1, v5, v6, v2),
        (v2, v6, v7, v3),
        (v3, v7, v4, v0),
    ]
    if cap_bottom:
        faces.append((v0, v1, v2, v3))
    if cap_top:
        faces.append((v7, v6, v5, v4))
    for fv in faces:
        try:
            f = bm.faces.new(fv)
            f.material_index = mat_idx
        except ValueError:
            pass


def extrude_prism_in_bm(bm, pts_2d, z_min, z_max, mat_side=0, mat_top=1, smooth_sides=False):
    pts = ensure_ccw(pts_2d)
    if len(pts) < 3 or z_max <= z_min:
        return
    bottom_verts = [bm.verts.new((p[0], p[1], z_min)) for p in pts]
    top_verts = [bm.verts.new((p[0], p[1], z_max)) for p in pts]
    n = len(pts)
    try:
        fb = bm.faces.new(list(reversed(bottom_verts)))
        fb.material_index = mat_side
    except ValueError:
        pass
    try:
        ft = bm.faces.new(top_verts)
        ft.material_index = mat_top
    except ValueError:
        pass
    for i in range(n):
        v0 = bottom_verts[i]
        v1 = bottom_verts[(i + 1) % n]
        v2 = top_verts[(i + 1) % n]
        v3 = top_verts[i]
        try:
            fs = bm.faces.new((v0, v1, v2, v3))
            fs.material_index = mat_side
            fs.smooth = smooth_sides
        except ValueError:
            pass


def add_pitched_mansard_roof_in_bm(bm, pts_2d, z_base, height, inset_factor=0.82, mat_slate=1, mat_trim=4, add_dormers=True):
    pts = ensure_ccw(pts_2d)
    if len(pts) < 3:
        return
    top_pts = inset_polygon_toward_centroid(pts, inset_factor)
    z_top = z_base + height

    b_verts = [bm.verts.new((p[0], p[1], z_base)) for p in pts]
    t_verts = [bm.verts.new((p[0], p[1], z_top)) for p in top_pts]
    n = len(pts)
    for i in range(n):
        try:
            f = bm.faces.new((b_verts[i], b_verts[(i + 1) % n], t_verts[(i + 1) % n], t_verts[i]))
            f.material_index = mat_slate
        except ValueError:
            pass
    try:
        ft = bm.faces.new(t_verts)
        ft.material_index = mat_slate
    except ValueError:
        pass

    if add_dormers:
        for i in range(n):
            p1, p2 = pts[i], pts[(i + 1) % n]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 6.0:
                continue
            num_dormers = max(2, int(seg_len // 3.8))
            dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
            nx, ny = dy, -dx
            for d_idx in range(num_dormers):
                t_frac = (d_idx + 0.5) / num_dormers
                cx = p1[0] + (p2[0] - p1[0]) * t_frac - nx * 0.22
                cy = p1[1] + (p2[1] - p1[1]) * t_frac - ny * 0.22
                w = 1.30
                q1 = (cx - dx * w * 0.5, cy - dy * w * 0.5)
                q2 = (cx + dx * w * 0.5, cy + dy * w * 0.5)
                add_box_between(bm, q1, q2, z_base + 0.30, z_base + height * 0.78, thickness=1.20, offset_out=0.25, mat_idx=mat_trim)
                g1 = (cx - dx * 0.44, cy - dy * 0.44)
                g2 = (cx + dx * 0.44, cy + dy * 0.44)
                add_box_between(bm, g1, g2, z_base + 0.46, z_base + height * 0.70, thickness=0.14, offset_out=0.72, mat_idx=2)
                m1 = (cx - dx * 0.04, cy - dy * 0.04)
                m2 = (cx + dx * 0.04, cy + dy * 0.04)
                add_box_between(bm, m1, m2, z_base + 0.46, z_base + height * 0.70, thickness=0.18, offset_out=0.78, mat_idx=3)
                add_box_between(bm, (cx - dx * 0.76, cy - dy * 0.76), (cx + dx * 0.76, cy + dy * 0.76),
                                z_base + height * 0.75, z_base + height * 0.88, thickness=1.35, offset_out=0.30, mat_idx=mat_trim)
                add_box_between(bm, (cx - dx * 0.45, cy - dy * 0.45), (cx + dx * 0.45, cy + dy * 0.45),
                                z_base + height * 0.88, z_base + height * 0.98, thickness=1.30, offset_out=0.28, mat_idx=mat_trim)


def is_party_wall(p1, p2, all_buildings, my_bid):
    if not all_buildings:
        return False
    mx, my = 0.5 * (p1[0] + p2[0]), 0.5 * (p1[1] + p2[1])
    for b in all_buildings:
        if b.get("id") == my_bid:
            continue
        poly = b.get("coords_xy", [])
        n_pts = len(poly)
        for i in range(n_pts - 1):
            q1, q2 = poly[i], poly[i + 1]
            dx, dy = q2[0] - q1[0], q2[1] - q1[1]
            L2 = dx * dx + dy * dy
            if L2 < 1e-4:
                continue
            t = max(0.0, min(1.0, ((mx - q1[0]) * dx + (my - q1[1]) * dy) / L2))
            proj_x = q1[0] + t * dx
            proj_y = q1[1] + t * dy
            if (mx - proj_x) ** 2 + (my - proj_y) ** 2 < 0.25:
                return True
    return False


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
    white_shop_muntins=False,
    modern_glass_bays=False,
    arched_ground_arcade=False,
    bay_target_width=3.2,
    has_rooftop_penthouse=False,
    all_buildings=None,
    my_bid=None,
):
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    if len(pts) < 3:
        return None

    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if collection.name.endswith("_Context_Proxy"):
        obj.hide_render = True
        obj.hide_viewport = True

    for m in (mat_wall, mat_roof, mat_window, mat_frame, mat_plinth):
        obj.data.materials.append(m)

    bm = bmesh.new()

    core_pts = inset_polygon_toward_centroid(pts, 0.965)
    extrude_prism_in_bm(bm, core_pts, 0.0, height - 0.28, mat_side=2, mat_top=1)

    ground_h = min(4.3, height * 0.35)
    plinth_h = 0.76
    n_Edges = len(pts)

    for i in range(n_Edges):
        p1 = pts[i]
        p2 = pts[(i + 1) % n_Edges]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if is_party_wall(p1, p2, all_buildings, my_bid):
            add_box_between(bm, p1, p2, 0.0, height, thickness=0.65, offset_out=0.18, mat_idx=0, cap_top=False, cap_bottom=False)
            continue
        if seg_len < 1.2:
            add_box_between(bm, p1, p2, 0.0, height, thickness=0.65, offset_out=0.18, mat_idx=0, cap_top=False, cap_bottom=False)
            continue

        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len

        add_box_between(bm, p1, p2, 0.0, plinth_h, thickness=0.68, offset_out=0.22, mat_idx=4, cap_bottom=False)
        add_box_between(bm, p1, p2, plinth_h, plinth_h + 0.10, thickness=0.74, offset_out=0.26, mat_idx=4, cap_top=False, cap_bottom=False)

        add_box_between(bm, p1, p2, ground_h - 0.42, ground_h - 0.12, thickness=0.72, offset_out=0.25, mat_idx=4, cap_top=False, cap_bottom=False)
        add_box_between(bm, p1, p2, ground_h - 0.12, ground_h + 0.16, thickness=0.88, offset_out=0.34, mat_idx=4, cap_bottom=False, cap_top=False)

        n_bays = max(1, int(round(seg_len / bay_target_width)))
        bay_w = seg_len / n_bays
        pier_w = max(0.48, bay_w * (0.24 if modern_glass_bays else 0.36))

        for b in range(n_bays + 1):
            center_s = b * bay_w
            s_start = max(0.0, center_s - pier_w * 0.5)
            s_end = min(seg_len, center_s + pier_w * 0.5)
            if s_end - s_start > 0.08:
                q1 = (p1[0] + dx * s_start, p1[1] + dy * s_start)
                q2 = (p1[0] + dx * s_end, p1[1] + dy * s_end)
                z_cur = plinth_h + 0.10
                while z_cur < ground_h - 0.44:
                    z_next = min(ground_h - 0.42, z_cur + 0.42)
                    add_box_between(bm, q1, q2, z_cur, z_next, thickness=0.74, offset_out=0.26, mat_idx=4)
                    z_cur += 0.48
                cap_q1 = (p1[0] + dx * max(0.0, s_start - 0.06), p1[1] + dy * max(0.0, s_start - 0.06))
                cap_q2 = (p1[0] + dx * min(seg_len, s_end + 0.06), p1[1] + dy * min(seg_len, s_end + 0.06))
                add_box_between(bm, cap_q1, cap_q2, ground_h - 0.58, ground_h - 0.42, thickness=0.80, offset_out=0.29, mat_idx=4)

                # Upper story vertical stone pier (with rusticated corner quoins if arched_ground_arcade)
                add_box_between(bm, q1, q2, ground_h + 0.16, height - 0.55, thickness=0.68, offset_out=0.22, mat_idx=0, cap_top=False, cap_bottom=False)
                if arched_ground_arcade and (b == 0 or b == n_bays):
                    qz = ground_h + 0.30
                    while qz < height - 0.80:
                        add_box_between(bm, q1, q2, qz, qz + 0.38, thickness=0.78, offset_out=0.28, mat_idx=4, cap_top=False, cap_bottom=False)
                        qz += 0.68

        num_upper_floors = max(1, int(round((height - ground_h - 0.5) / floor_height)))
        actual_fh = (height - ground_h - 0.55) / num_upper_floors

        for b in range(n_bays):
            b_s0 = b * bay_w + pier_w * 0.5
            b_s1 = (b + 1) * bay_w - pier_w * 0.5
            if b_s1 - b_s0 < 0.35:
                continue
            w_p1 = (p1[0] + dx * b_s0, p1[1] + dy * b_s0)
            w_p2 = (p1[0] + dx * b_s1, p1[1] + dy * b_s1)

            add_box_between(bm, w_p1, w_p2, plinth_h, height - 0.55, thickness=0.12, offset_out=-0.12, mat_idx=2)

            if arched_ground_arcade:
                # Stepped stone round-arch spandrels & keystone at top of ground-floor opening (matching 188991343 in Coté_Place_dArmes_East.jpg!)
                bw_open = b_s1 - b_s0
                # Left & right arch haunches
                h1_p2 = (p1[0] + dx * (b_s0 + bw_open * 0.25), p1[1] + dy * (b_s0 + bw_open * 0.25))
                h2_p1 = (p1[0] + dx * (b_s1 - bw_open * 0.25), p1[1] + dy * (b_s1 - bw_open * 0.25))
                add_box_between(bm, w_p1, h1_p2, ground_h - 1.15, ground_h - 0.42, thickness=0.72, offset_out=0.25, mat_idx=4, cap_top=False, cap_bottom=False)
                add_box_between(bm, h2_p1, w_p2, ground_h - 1.15, ground_h - 0.42, thickness=0.72, offset_out=0.25, mat_idx=4, cap_top=False, cap_bottom=False)
                # Arch keystone
                mid_s = 0.5 * (b_s0 + b_s1)
                ak1 = (p1[0] + dx * (mid_s - 0.18), p1[1] + dy * (mid_s - 0.18))
                ak2 = (p1[0] + dx * (mid_s + 0.18), p1[1] + dy * (mid_s + 0.18))
                add_box_between(bm, ak1, ak2, ground_h - 0.72, ground_h - 0.18, thickness=0.84, offset_out=0.32, mat_idx=4, cap_top=False, cap_bottom=False)

            g_s0 = b * bay_w + bay_w * 0.26
            g_s1 = b * bay_w + bay_w * 0.74
            if g_s1 - g_s0 > 0.3:
                gp1 = (p1[0] + dx * g_s0, p1[1] + dy * g_s0)
                gp2 = (p1[0] + dx * g_s1, p1[1] + dy * g_s1)
                add_box_between(bm, gp1, gp2, 0.14, plinth_h - 0.14, thickness=0.18, offset_out=0.52, mat_idx=3, cap_top=False, cap_bottom=False)

            add_box_between(bm, w_p1, w_p2, plinth_h, plinth_h + 0.14, thickness=0.76, offset_out=0.28, mat_idx=4, cap_top=False, cap_bottom=False)
            add_box_between(bm, w_p1, w_p2, plinth_h + 0.14, plinth_h + 0.24, thickness=0.24, offset_out=0.05, mat_idx=3, cap_top=False, cap_bottom=False)
            add_box_between(bm, w_p1, w_p2, ground_h - 0.54, ground_h - 0.42, thickness=0.24, offset_out=0.05, mat_idx=3, cap_top=False, cap_bottom=False)

            if white_shop_muntins:
                for mh in range(1, 3):
                    mz = plinth_h + 0.20 + (ground_h - 0.62 - plinth_h) * (mh / 3.0)
                    add_box_between(bm, w_p1, w_p2, mz - 0.035, mz + 0.035, thickness=0.14, offset_out=0.02, mat_idx=4, cap_top=False, cap_bottom=False)
                for mv in range(1, 4):
                    ms = b_s0 + (b_s1 - b_s0) * (mv / 4.0)
                    mp1 = (p1[0] + dx * (ms - 0.035), p1[1] + dy * (ms - 0.035))
                    mp2 = (p1[0] + dx * (ms + 0.035), p1[1] + dy * (ms + 0.035))
                    add_box_between(bm, mp1, mp2, plinth_h + 0.20, ground_h - 0.42, thickness=0.14, offset_out=0.02, mat_idx=4, cap_top=False, cap_bottom=False)
            else:
                tz = ground_h - 1.10
                add_box_between(bm, w_p1, w_p2, tz - 0.05, tz + 0.05, thickness=0.20, offset_out=0.04, mat_idx=3, cap_top=False, cap_bottom=False)
                ms = 0.5 * (b_s0 + b_s1)
                mp1 = (p1[0] + dx * (ms - 0.045), p1[1] + dy * (ms - 0.045))
                mp2 = (p1[0] + dx * (ms + 0.045), p1[1] + dy * (ms + 0.045))
                add_box_between(bm, mp1, mp2, plinth_h + 0.14, ground_h - 0.42, thickness=0.18, offset_out=0.04, mat_idx=3, cap_top=False, cap_bottom=False)

            for fl in range(num_upper_floors):
                fz0 = ground_h + 0.16 + fl * actual_fh
                fz1 = fz0 + actual_fh
                win_z0 = fz0 + (0.48 if modern_glass_bays else 0.70)
                win_z1 = fz1 - (0.38 if modern_glass_bays else 0.50)

                spandrel_mat = 3 if modern_glass_bays else 0
                add_box_between(bm, w_p1, w_p2, fz0, win_z0, thickness=0.60, offset_out=0.18, mat_idx=spandrel_mat, cap_top=False, cap_bottom=False)

                sill_p1 = (p1[0] + dx * (b_s0 - 0.08), p1[1] + dy * (b_s0 - 0.08))
                sill_p2 = (p1[0] + dx * (b_s1 + 0.08), p1[1] + dy * (b_s1 + 0.08))
                add_box_between(bm, sill_p1, sill_p2, win_z0 - 0.15, win_z0 + 0.02, thickness=0.82, offset_out=0.31, mat_idx=4)

                add_box_between(bm, w_p1, w_p2, win_z1, fz1, thickness=0.64, offset_out=0.20, mat_idx=spandrel_mat, cap_top=False, cap_bottom=False)
                add_box_between(bm, sill_p1, sill_p2, win_z1, win_z1 + 0.18, thickness=0.78, offset_out=0.29, mat_idx=4)
                mid_s = 0.5 * (b_s0 + b_s1)
                kp1 = (p1[0] + dx * (mid_s - 0.16), p1[1] + dy * (mid_s - 0.16))
                kp2 = (p1[0] + dx * (mid_s + 0.16), p1[1] + dy * (mid_s + 0.16))
                add_box_between(bm, kp1, kp2, win_z1 - 0.04, win_z1 + 0.28, thickness=0.84, offset_out=0.33, mat_idx=4)

                add_box_between(bm, w_p1, w_p2, win_z0, win_z0 + 0.07, thickness=0.18, offset_out=0.0, mat_idx=3, cap_top=False, cap_bottom=False)
                add_box_between(bm, w_p1, w_p2, win_z1 - 0.07, win_z1, thickness=0.18, offset_out=0.0, mat_idx=3, cap_top=False, cap_bottom=False)

                if arched_ground_arcade:
                    # 3-part vertical mullions (matching 188991343 in Coté_Place_dArmes_East.jpg)
                    for mf in (0.33, 0.67):
                        ms_i = b_s0 + (b_s1 - b_s0) * mf
                        vp1 = (p1[0] + dx * (ms_i - 0.04), p1[1] + dy * (ms_i - 0.04))
                        vp2 = (p1[0] + dx * (ms_i + 0.04), p1[1] + dy * (ms_i + 0.04))
                        add_box_between(bm, vp1, vp2, win_z0, win_z1, thickness=0.18, offset_out=0.0, mat_idx=3, cap_top=False, cap_bottom=False)
                else:
                    vp1 = (p1[0] + dx * (mid_s - 0.045), p1[1] + dy * (mid_s - 0.045))
                    vp2 = (p1[0] + dx * (mid_s + 0.045), p1[1] + dy * (mid_s + 0.045))
                    add_box_between(bm, vp1, vp2, win_z0, win_z1, thickness=0.18, offset_out=0.0, mat_idx=3, cap_top=False, cap_bottom=False)

                for sh in (0.35, 0.68):
                    sz = win_z0 + (win_z1 - win_z0) * sh
                    add_box_between(bm, w_p1, w_p2, sz - 0.03, sz + 0.03, thickness=0.15, offset_out=0.0, mat_idx=3, cap_top=False, cap_bottom=False)

                if modern_glass_bays and (b % 2 == 1):
                    # Glass Juliet balcony on alternating bays (matching 182859307 in Rue_NotreDame_Side.jpg!)
                    jb_s0 = b_s0 + (b_s1 - b_s0) * 0.12
                    jb_s1 = b_s0 + (b_s1 - b_s0) * 0.88
                    jp1 = (p1[0] + dx * jb_s0, p1[1] + dy * jb_s0)
                    jp2 = (p1[0] + dx * jb_s1, p1[1] + dy * jb_s1)
                    add_box_between(bm, jp1, jp2, win_z0, win_z0 + 1.05, thickness=0.06, offset_out=0.38, mat_idx=2)
                    add_box_between(bm, jp1, jp2, win_z0 + 1.02, win_z0 + 1.08, thickness=0.10, offset_out=0.38, mat_idx=3)

        add_box_between(bm, p1, p2, height - 0.65, height - 0.30, thickness=0.80, offset_out=0.30, mat_idx=4, cap_top=False, cap_bottom=False)
        add_box_between(bm, p1, p2, height - 0.30, height + 0.18, thickness=1.12, offset_out=0.46, mat_idx=4, cap_bottom=False)

        n_dentils = int(seg_len / 0.60)
        for d in range(n_dentils):
            ds0 = d * 0.60 + 0.14
            ds1 = ds0 + 0.24
            if ds1 < seg_len:
                dp1 = (p1[0] + dx * ds0, p1[1] + dy * ds0)
                dp2 = (p1[0] + dx * ds1, p1[1] + dy * ds1)
                add_box_between(bm, dp1, dp2, height - 0.85, height - 0.60, thickness=0.76, offset_out=0.28, mat_idx=4)

    if roof_style == "mansard":
        add_pitched_mansard_roof_in_bm(bm, pts, height + 0.18, height=3.3, inset_factor=0.82, mat_slate=1, mat_trim=4, add_dormers=True)
    elif has_rooftop_penthouse:
        ph_pts = inset_polygon_toward_centroid(pts, 0.68)
        extrude_prism_in_bm(bm, ph_pts, height + 0.18, height + 3.5, mat_side=0, mat_top=1)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    add_bevel_modifier(obj, width=0.025, segments=2)
    return obj


def build_basilique_notre_dame_context(coords_xy, palette, collection):
    """
    Constructs a high-detail Gothic Revival architectural backdrop for Basilique Notre-Dame (4320792)
    in `Block_MTL-VM-0004_Context_Proxy` because its north flank along Rue Saint-Sulpice is prominently
    visible in `Aldred_ArtDeco_Facade.jpg`, `Rue_NotreDame_Side.jpg`, and `Coté_Place_dArmes_East.jpg`!
    Features:
    - Cut Pierre Grise ashlar masonry walls (23.5m) + steep pitched dark slate Basilica roof (23.5..33.0m)
    - Stepped Gothic stone buttresses every 6.2m topped by octagonal spirelet pinnacles (23.5..29.2m)
    - Deeply recessed 12m-tall Gothic pointed-arch stained glass windows with stone tracery mullions
    - Twin 65m Western Bell Towers facing Place d'Armes
    """
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    mesh = bpy.data.meshes.new("MTL_Context_Proxy_4320792_Basilique_NotreDame_Mesh")
    obj = bpy.data.objects.new("MTL_Context_Proxy_4320792_Basilique_NotreDame", mesh)
    collection.objects.link(obj)
    obj.hide_render = True
    obj.hide_viewport = True

    mat_stone = palette["Mat_MTL_PierreGrise_Limestone"]
    mat_slate = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_iron = palette["Mat_MTL_CastIron_Black"]
    mat_trim = palette["Mat_MTL_Fieldstone_Rubble"]

    for m in (mat_stone, mat_slate, mat_glass, mat_iron, mat_trim):
        obj.data.materials.append(m)

    bm = bmesh.new()
    wall_h = 23.5

    # Inner dark stained-glass core
    core_pts = inset_polygon_toward_centroid(pts, 0.96)
    extrude_prism_in_bm(bm, core_pts, 0.0, wall_h, mat_side=2, mat_top=1)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 3.0:
            add_box_between(bm, p1, p2, 0.0, wall_h, thickness=0.80, offset_out=0.25, mat_idx=0)
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        nx, ny = dy, -dx

        # Rusticated stone base (0..3.8m) & cornice (22.5..23.8m)
        add_box_between(bm, p1, p2, 0.0, 3.8, thickness=0.90, offset_out=0.32, mat_idx=4)
        add_box_between(bm, p1, p2, 3.8, 4.2, thickness=1.05, offset_out=0.40, mat_idx=0)
        add_box_between(bm, p1, p2, wall_h - 1.1, wall_h + 0.25, thickness=1.15, offset_out=0.45, mat_idx=0)

        n_bays = max(1, int(round(seg_len / 6.2)))
        bw = seg_len / n_bays
        pier_w = bw * 0.34

        for b in range(n_bays + 1):
            cs = b * bw
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 > 0.15:
                q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
                q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
                # Main wall pier
                add_box_between(bm, q1, q2, 3.8, wall_h - 1.1, thickness=0.82, offset_out=0.28, mat_idx=0)

                # Stepped Gothic Buttress + Octagonal Spirelet Pinnacle (matching Rue_NotreDame_Side.jpg & Aldred_ArtDeco_Facade.jpg!)
                bcx = p1[0] + dx * cs + nx * 0.58
                bcy = p1[1] + dy * cs + ny * 0.58
                but_q1 = (p1[0] + dx * max(0.0, cs - 0.55), p1[1] + dy * max(0.0, cs - 0.55))
                but_q2 = (p1[0] + dx * min(seg_len, cs + 0.55), p1[1] + dy * min(seg_len, cs + 0.55))
                add_box_between(bm, but_q1, but_q2, 0.0, 12.5, thickness=1.10, offset_out=0.55, mat_idx=0)
                add_box_between(bm, but_q1, but_q2, 12.5, wall_h + 0.4, thickness=0.85, offset_out=0.42, mat_idx=0)
                # Octagonal pinnacle shaft & spirelet cone (23.8..29.2m)
                pin_pts = [(bcx + 0.48 * math.cos(a), bcy + 0.48 * math.sin(a)) for a in [k * math.pi / 4 for k in range(8)]]
                extrude_prism_in_bm(bm, pin_pts, wall_h + 0.2, wall_h + 3.2, mat_side=0, mat_top=0)
                add_pitched_mansard_roof_in_bm(bm, pin_pts, wall_h + 3.2, height=2.6, inset_factor=0.08, mat_slate=0, mat_trim=0, add_dormers=False)

        for b in range(n_bays):
            bs0 = b * bw + pier_w * 0.5
            bs1 = (b + 1) * bw - pier_w * 0.5
            if bs1 - bs0 < 0.5:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
            add_box_between(bm, wp1, wp2, 4.2, wall_h - 1.1, thickness=0.14, offset_out=-0.12, mat_idx=2)
            # Wall spandrel below window (4.2..7.2m) & above pointed arch (19.8..22.4m)
            add_box_between(bm, wp1, wp2, 4.2, 7.2, thickness=0.72, offset_out=0.22, mat_idx=0)
            add_box_between(bm, wp1, wp2, 7.0, 7.35, thickness=0.95, offset_out=0.35, mat_idx=0)
            add_box_between(bm, wp1, wp2, 19.8, wall_h - 1.1, thickness=0.76, offset_out=0.24, mat_idx=0)
            # Pointed Gothic arch haunches at top of window (17.2..19.8m)
            w_open = bs1 - bs0
            hp1 = (p1[0] + dx * (bs0 + w_open * 0.28), p1[1] + dy * (bs0 + w_open * 0.28))
            hp2 = (p1[0] + dx * (bs1 - w_open * 0.28), p1[1] + dy * (bs1 - w_open * 0.28))
            add_box_between(bm, wp1, hp1, 17.2, 19.8, thickness=0.74, offset_out=0.23, mat_idx=0)
            add_box_between(bm, hp2, wp2, 17.2, 19.8, thickness=0.74, offset_out=0.23, mat_idx=0)
            # Gothic window tracery mullions (3 vertical bars + 3 horizontal transoms)
            for mf in (0.25, 0.50, 0.75):
                ms = bs0 + w_open * mf
                mp1 = (p1[0] + dx * (ms - 0.05), p1[1] + dy * (ms - 0.05))
                mp2 = (p1[0] + dx * (ms + 0.05), p1[1] + dy * (ms + 0.05))
                add_box_between(bm, mp1, mp2, 7.2, 19.8, thickness=0.22, offset_out=0.02, mat_idx=3)
            for tz in (10.2, 13.5, 16.8):
                add_box_between(bm, wp1, wp2, tz - 0.05, tz + 0.05, thickness=0.20, offset_out=0.02, mat_idx=3)

    # Steep Pitched Basilica Slate Roof (23.5..33.0m)
    add_pitched_mansard_roof_in_bm(bm, pts, wall_h + 0.2, height=9.5, inset_factor=0.35, mat_slate=1, mat_trim=0, add_dormers=False)

    # Twin Western Bell Towers at Place d'Armes end: (3.5, 3.0) and (-4.5, -20.5)
    for tcx, tcy in [(4.2, 3.8), (-4.2, -20.2)]:
        r = 4.8
        t_pts = [(tcx - r, tcy - r), (tcx + r, tcy - r), (tcx + r, tcy + r), (tcx - r, tcy + r)]
        extrude_prism_in_bm(bm, t_pts, 0.0, 62.0, mat_side=0, mat_top=1)
        for ti in range(4):
            tp1, tp2 = t_pts[ti], t_pts[(ti + 1) % 4]
            add_box_between(bm, tp1, tp2, 42.0, 43.0, thickness=0.95, offset_out=0.35, mat_idx=0)
            add_box_between(bm, tp1, tp2, 60.8, 62.2, thickness=1.10, offset_out=0.42, mat_idx=0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    add_bevel_modifier(obj, width=0.03, segments=2)
    return obj


def build_notredame_west_context_backdrops(palette, proxy_col):
    """
    Builds the immediate architectural context across Rue Notre-Dame Ouest & Place d'Armes
    (`Block_MTL-VM-0004_Context_Proxy`) visible in `NY_Life_Red_Sandstone_Corner.jpg` and `Aldred_ArtDeco_Facade.jpg`:
    1. The monumental stepped Indiana limestone colonnade on the West side of Rue Notre-Dame Ouest
       (`X = -14..+6, Y = 24..64`, right side of `NY_Life_Red_Sandstone_Corner.jpg`)
    2. The 32-story dark bronze & glass Miesian tower (`500 Place d'Armes`, `X = -24..-4, Y = -24..+12`)
       visible in the center-right background of `NY_Life_Red_Sandstone_Corner.jpg`
    3. The 8-story classical white/grey limestone building (`X = -38..-12, Y = -18..+18`) visible at the end
       of Rue Saint-Sulpice in the center background of `Aldred_ArtDeco_Facade.jpg`!
    """
    # 1. West side of Rue Notre-Dame Ouest (Stepped Art Deco limestone facade on right of NY_Life_Red_Sandstone_Corner.jpg)
    west_nd_pts = [(-8.0, 26.0), (2.5, 22.0), (14.5, 58.0), (2.0, 63.0)]
    build_detailed_facade_building(
        name="MTL_Context_Proxy_West_NotreDame_ArtDecoPodium",
        coords_xy=west_nd_pts,
        height=32.0,
        floor_height=4.2,
        mat_wall=palette["Mat_MTL_PierreGrise_Limestone"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_Dark_Bronze_CurtainWall"],
        mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
        collection=proxy_col,
        roof_style="cornice_flat",
        modern_glass_bays=False,
        bay_target_width=2.8,
        has_rooftop_penthouse=True,
    )

    # 2. 500 Place d'Armes dark bronze & glass tower in background of NY_Life_Red_Sandstone_Corner.jpg
    b500_pts = [(-22.0, -28.0), (-4.0, -34.0), (2.0, -8.0), (-16.0, -2.0)]
    build_detailed_facade_building(
        name="MTL_Context_Proxy_500_PlaceDArmes_Tower",
        coords_xy=b500_pts,
        height=78.0,
        floor_height=3.8,
        mat_wall=palette["Mat_MTL_Dark_Bronze_CurtainWall"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_Dark_Bronze_CurtainWall"],
        mat_plinth=palette["Mat_MTL_Plaza_Charcoal_Granite"],
        collection=proxy_col,
        roof_style="cornice_flat",
        modern_glass_bays=True,
        bay_target_width=2.6,
    )

    # 3. Classical 8-story white/grey limestone building at end of Rue Saint-Sulpice in Aldred_ArtDeco_Facade.jpg
    west_pa_pts = [(-38.0, -14.0), (-16.0, -22.0), (-8.0, 8.0), (-30.0, 16.0)]
    build_detailed_facade_building(
        name="MTL_Context_Proxy_PlaceDArmes_West_Classical",
        coords_xy=west_pa_pts,
        height=26.5,
        floor_height=3.6,
        mat_wall=palette["Mat_MTL_PierreGrise_Limestone"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_CastIron_Black"],
        mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
        collection=proxy_col,
        roof_style="cornice_flat",
        bay_target_width=3.2,
    )


def build_edifice_aldred_and_70_notredame(coords_xy, palette, collection):
    """
    Constructs footprint 339884213:
    1. Along the West Rue Notre-Dame Ouest frontage (`(18.8, 48.0) -> (26.3, 63.0)`):
       The 3.5-story Warm Buff Cut-Limestone heritage building (`70 Rue Notre-Dame Ouest`, *"Galerie d'Art Inuk"*)
       seen in the immediate left foreground of `NY_Life_Red_Sandstone_Corner.jpg`, complete with:
       - Forest-green ground-floor storefront (`#24472E`) + red-and-green striped 3D canvas awning
       - Rusticated stone carriage arch with wrought-iron gate
       - Segmental & twin round-arched 2nd-floor windows + multi-pane green 3rd-floor windows
    2. Rising from the setback eastern core of `339884213`:
       The 23-story Stepped Art Deco Indiana Limestone Ziggurat Tower (`Édifice Aldred`, 86m + flagpole)!
    """
    pts = ensure_ccw(clean_poly_pts(coords_xy))

    # Part A: 3.5-story heritage frontage on Rue Notre-Dame Ouest (visible in NY_Life_Red_Sandstone_Corner.jpg!)
    front_obj = build_detailed_facade_building(
        name="MTL_Owned_339884213_70_RueNotreDame_InukGallery",
        coords_xy=pts,
        height=14.8,
        floor_height=3.8,
        mat_wall=palette["Mat_MTL_WarmBuff_Limestone"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_Heritage_GreenFrame"],
        mat_plinth=palette["Mat_MTL_WarmBuff_Limestone"],
        collection=collection,
        roof_style="cornice_flat",
        white_shop_muntins=False,
        modern_glass_bays=False,
        arched_ground_arcade=True,
        bay_target_width=3.6,
    )

    # Add the signature Red & Green Striped Awning + Hanging Banner on the NW Rue Notre-Dame facade (around X=23.2, Y=56.8)
    bm_a = bmesh.new()
    bm_a.from_mesh(front_obj.data)
    front_obj.data.materials.append(palette["Mat_MTL_Awning_Red"])  # slot 5
    # Edge from (26.347, 62.951) to (18.818, 48.034)
    p1 = (25.2, 60.7)
    p2 = (22.2, 54.7)
    # Sloped 3D striped awning projecting out over sidewalk
    for stripe_i in range(6):
        t0 = stripe_i / 6.0
        t1 = (stripe_i + 1) / 6.0
        sp1 = (p1[0] + (p2[0] - p1[0]) * t0, p1[1] + (p2[1] - p1[1]) * t0)
        sp2 = (p1[0] + (p2[0] - p1[0]) * t1, p1[1] + (p2[1] - p1[1]) * t1)
        m_idx = 5 if (stripe_i % 2 == 0) else 3
        add_box_between(bm_a, sp1, sp2, 3.35, 3.95, thickness=0.95, offset_out=0.62, mat_idx=m_idx)
    bmesh.ops.recalc_face_normals(bm_a, faces=bm_a.faces)
    bm_a.to_mesh(front_obj.data)
    bm_a.free()

    # Part B: 23-story Édifice Aldred Stepped Art Deco Ziggurat Tower rising on the setback eastern core of 339884213
    tower_base_pts = inset_polygon_toward_centroid(pts, 0.72)
    # Shift slightly East-Southeast so the 3.5-story Rue Notre-Dame street wall is clean in front
    tower_base_pts = [(p[0] + 6.5, p[1] - 2.5) for p in tower_base_pts]

    mesh = bpy.data.meshes.new("Edifice_Aldred_507_PlaceDArmes_Mesh")
    obj = bpy.data.objects.new("Edifice_Aldred_507_PlaceDArmes", mesh)
    collection.objects.link(obj)

    mat_limestone = palette["Mat_MTL_WarmBuff_Limestone"]
    mat_trim = palette["Mat_MTL_PierreGrise_Limestone"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_bronze = palette["Mat_MTL_Dark_Bronze_CurtainWall"]
    mat_roof = palette["Mat_MTL_Slate_Roof_Dark"]

    for m in (mat_limestone, mat_roof, mat_glass, mat_bronze, mat_trim):
        obj.data.materials.append(m)

    bm = bmesh.new()
    tiers = [
        (1.00, 14.5, 34.0, 2.6),
        (0.80, 34.0, 50.5, 2.4),
        (0.62, 50.5, 63.0, 2.2),
        (0.46, 63.0, 76.0, 2.0),
        (0.30, 76.0, 86.5, 1.8),
    ]

    for t_idx, (scale, z0, z1, bay_w) in enumerate(tiers):
        t_pts = inset_polygon_toward_centroid(tower_base_pts, scale)
        core_pts = inset_polygon_toward_centroid(t_pts, 0.95)
        extrude_prism_in_bm(bm, core_pts, z0, z1 - 0.28, mat_side=2, mat_top=1)

        n = len(t_pts)
        for i in range(n):
            p1, p2 = t_pts[i], t_pts[(i + 1) % n]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 1.2:
                add_box_between(bm, p1, p2, z0, z1, thickness=0.65, offset_out=0.20, mat_idx=0)
                continue
            dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
            n_bays = max(2, int(round(seg_len / bay_w)))
            actual_bw = seg_len / n_bays
            pier_w = actual_bw * 0.42

            for b in range(n_bays + 1):
                cs = b * actual_bw
                s0 = max(0.0, cs - pier_w * 0.5)
                s1 = min(seg_len, cs + pier_w * 0.5)
                if s1 - s0 > 0.08:
                    q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
                    q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
                    add_box_between(bm, q1, q2, z0, z1 + 0.75, thickness=0.72, offset_out=0.25, mat_idx=0)
                    ms = 0.5 * (s0 + s1)
                    r1 = (p1[0] + dx * (ms - 0.11), p1[1] + dy * (ms - 0.11))
                    r2 = (p1[0] + dx * (ms + 0.11), p1[1] + dy * (ms + 0.11))
                    add_box_between(bm, r1, r2, z0, z1 + 1.0, thickness=0.86, offset_out=0.32, mat_idx=4)

            fl_h = 3.6
            n_fl = max(1, int(round((z1 - z0) / fl_h)))
            step_z = (z1 - z0) / n_fl
            for b in range(n_bays):
                bs0 = b * actual_bw + pier_w * 0.5
                bs1 = (b + 1) * actual_bw - pier_w * 0.5
                if bs1 - bs0 < 0.22:
                    continue
                wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
                wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
                add_box_between(bm, wp1, wp2, z0, z1, thickness=0.12, offset_out=-0.12, mat_idx=2)
                for fl in range(n_fl):
                    fz = z0 + fl * step_z
                    add_box_between(bm, wp1, wp2, fz, fz + 0.88, thickness=0.42, offset_out=0.06, mat_idx=3)
                    add_box_between(bm, wp1, wp2, fz + 0.82, fz + 0.96, thickness=0.58, offset_out=0.14, mat_idx=4)

            add_box_between(bm, p1, p2, z1 - 0.90, z1 + 0.35, thickness=0.84, offset_out=0.30, mat_idx=4)
            add_box_between(bm, p1, p2, z1 + 0.35, z1 + 0.80, thickness=0.56, offset_out=0.18, mat_idx=0)

    cx = sum(p[0] for p in tower_base_pts) / len(tower_base_pts)
    cy = sum(p[1] for p in tower_base_pts) / len(tower_base_pts)
    spire_pts = [(cx - 1.3, cy - 1.3), (cx + 1.3, cy - 1.3), (cx + 1.3, cy + 1.3), (cx - 1.3, cy + 1.3)]
    extrude_prism_in_bm(bm, spire_pts, 86.5, 90.0, mat_side=4, mat_top=4)
    mast_pts = [(cx - 0.18, cy - 0.18), (cx + 0.18, cy - 0.18), (cx + 0.18, cy + 0.18), (cx - 0.18, cy + 0.18)]
    extrude_prism_in_bm(bm, mast_pts, 90.0, 97.0, mat_side=3, mat_top=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    add_bevel_modifier(obj, width=0.03, segments=2)
    return obj


def build_ny_life_red_sandstone_building(coords_xy, palette, collection):
    """
    Constructs the historic New York Life Building (511 Place d'Armes, 1888) on footprint 339884214
    rising 37.5m (10 stories, matching the tall tower on the left of `NY_Life_Red_Sandstone_Corner.jpg`
    and right of `Aldred_ArtDeco_Facade.jpg`), with rich Red Scottish Sandstone & Warm Buff masonry,
    Romanesque recessed window bays, belt courses, dentiled cornice, and the signature Clock Tower.
    """
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    mesh = bpy.data.meshes.new("NY_Life_Red_Sandstone_511_PlaceDArmes_Mesh")
    obj = bpy.data.objects.new("NY_Life_Red_Sandstone_511_PlaceDArmes", mesh)
    collection.objects.link(obj)

    mat_red = palette["Mat_MTL_Red_Sandstone"]
    mat_buff = palette["Mat_MTL_WarmBuff_Limestone"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_iron = palette["Mat_MTL_CastIron_Black"]
    mat_copper = palette["Mat_MTL_Verdigris_Copper"]
    mat_clock_face = kit.get_or_create_pbr_material("Mat_MTL_ClockFace_Ivory", "#F2EBDC", roughness=0.35, bump_strength=0.02)

    for m in (mat_red, mat_copper, mat_glass, mat_iron, mat_buff, mat_clock_face):
        obj.data.materials.append(m)

    bm = bmesh.new()
    height = 37.5
    core_pts = inset_polygon_toward_centroid(pts, 0.96)
    extrude_prism_in_bm(bm, core_pts, 0.0, height - 0.28, mat_side=2, mat_top=1)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.5:
            add_box_between(bm, p1, p2, 0.0, height, thickness=0.65, offset_out=0.20, mat_idx=0)
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len

        add_box_between(bm, p1, p2, 0.0, 1.1, thickness=0.78, offset_out=0.28, mat_idx=0)
        add_box_between(bm, p1, p2, 4.1, 4.6, thickness=0.76, offset_out=0.26, mat_idx=0)
        add_box_between(bm, p1, p2, 8.0, 8.7, thickness=0.88, offset_out=0.34, mat_idx=4)
        add_box_between(bm, p1, p2, 28.0, 28.7, thickness=0.92, offset_out=0.36, mat_idx=4)
        add_box_between(bm, p1, p2, height - 1.2, height - 0.4, thickness=0.95, offset_out=0.38, mat_idx=4)
        add_box_between(bm, p1, p2, height - 0.4, height + 0.42, thickness=1.25, offset_out=0.50, mat_idx=0)
        add_box_between(bm, p1, p2, height + 0.42, height + 1.35, thickness=0.58, offset_out=0.22, mat_idx=0)

        n_bays = max(1, int(round(seg_len / 3.1)))
        bw = seg_len / n_bays
        pw = bw * 0.36
        for b in range(n_bays + 1):
            cs = b * bw
            s0 = max(0.0, cs - pw * 0.5)
            s1 = min(seg_len, cs + pw * 0.5)
            if s1 - s0 > 0.08:
                q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
                q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
                add_box_between(bm, q1, q2, 0.0, height - 0.4, thickness=0.74, offset_out=0.26, mat_idx=0)

        for b in range(n_bays):
            bs0 = b * bw + pw * 0.5
            bs1 = (b + 1) * bw - pw * 0.5
            if bs1 - bs0 < 0.3:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
            add_box_between(bm, wp1, wp2, 1.1, height - 0.4, thickness=0.12, offset_out=-0.12, mat_idx=2)
            mid_s = 0.5 * (bs0 + bs1)
            mp1 = (p1[0] + dx * (mid_s - 0.045), p1[1] + dy * (mid_s - 0.045))
            mp2 = (p1[0] + dx * (mid_s + 0.045), p1[1] + dy * (mid_s + 0.045))
            add_box_between(bm, mp1, mp2, 1.1, height - 0.4, thickness=0.18, offset_out=0.0, mat_idx=3)

            for fl in range(9):
                fz0 = fl * 4.05
                fz1 = fz0 + 4.05
                add_box_between(bm, wp1, wp2, fz0, fz0 + 0.88, thickness=0.58, offset_out=0.16, mat_idx=0)
                add_box_between(bm, wp1, wp2, fz0 + 0.78, fz0 + 0.96, thickness=0.82, offset_out=0.31, mat_idx=4)
                add_box_between(bm, wp1, wp2, fz1 - 0.60, fz1, thickness=0.72, offset_out=0.24, mat_idx=0)
                sz = fz0 + 2.25
                add_box_between(bm, wp1, wp2, sz - 0.035, sz + 0.035, thickness=0.16, offset_out=0.0, mat_idx=3)

    # Signature Square Clock Tower at (25.5, 30.5) so it is visible both from Rue Saint-Sulpice (Aldred_ArtDeco_Facade.jpg) & Place d'Armes!
    tcx, tcy = 25.5, 30.5
    tw = 3.5
    tower_pts = [
        (tcx - tw, tcy - tw),
        (tcx + tw, tcy - tw),
        (tcx + tw, tcy + tw),
        (tcx - tw, tcy + tw),
    ]
    extrude_prism_in_bm(bm, tower_pts, 0.0, 45.5, mat_side=0, mat_top=0)

    for ti in range(4):
        tp1, tp2 = tower_pts[ti], tower_pts[(ti + 1) % 4]
        add_box_between(bm, tp1, tp2, 37.8, 38.5, thickness=0.85, offset_out=0.32, mat_idx=0)
        add_box_between(bm, tp1, tp2, 44.0, 44.9, thickness=0.98, offset_out=0.38, mat_idx=0)
        tdx, tdy = (tp2[0] - tp1[0]) / (2 * tw), (tp2[1] - tp1[1]) / (2 * tw)
        c1a, c1b = tp1, (tp1[0] + tdx * 1.25, tp1[1] + tdy * 1.25)
        c2a, c2b = (tp2[0] - tdx * 1.25, tp2[1] - tdy * 1.25), tp2
        add_box_between(bm, c1a, c1b, 38.5, 44.0, thickness=0.75, offset_out=0.26, mat_idx=0)
        add_box_between(bm, c2a, c2b, 38.5, 44.0, thickness=0.75, offset_out=0.26, mat_idx=0)
        cf1 = (tp1[0] + tdx * (tw - 1.15), tp1[1] + tdy * (tw - 1.15))
        cf2 = (tp1[0] + tdx * (tw + 1.15), tp1[1] + tdy * (tw + 1.15))
        add_box_between(bm, cf1, cf2, 39.8, 42.2, thickness=0.35, offset_out=0.20, mat_idx=5)
        ch1 = (tp1[0] + tdx * (tw - 0.12), tp1[1] + tdy * (tw - 0.12))
        ch2 = (tp1[0] + tdx * (tw + 0.12), tp1[1] + tdy * (tw + 0.12))
        add_box_between(bm, ch1, ch2, 40.8, 41.9, thickness=0.40, offset_out=0.28, mat_idx=3)
        add_box_between(bm, cf1, (tp1[0] + tdx * tw, tp1[1] + tdy * tw), 40.9, 41.1, thickness=0.40, offset_out=0.28, mat_idx=3)

    add_pitched_mansard_roof_in_bm(bm, tower_pts, 45.5, height=4.8, inset_factor=0.10, mat_slate=1, mat_trim=0, add_dormers=False)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    add_bevel_modifier(obj, width=0.03, segments=2)
    return obj


def build_edifice_duluth_corner(coords_xy, palette, collection):
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    obj = build_detailed_facade_building(
        name="Edifice_Duluth_501_PlaceDArmes",
        coords_xy=pts,
        height=24.5,
        floor_height=3.7,
        mat_wall=palette["Mat_MTL_WarmBuff_Limestone"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_CastIron_Black"],
        mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
        collection=collection,
        roof_style="cornice_flat",
        white_shop_muntins=False,
        modern_glass_bays=False,
        arched_ground_arcade=True,
        bay_target_width=3.0,
    )
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    tcx, tcy = 10.8, 26.2
    r = 3.6
    ang = math.radians(-22.0)
    ca, sa = math.cos(ang), math.sin(ang)
    local_sq = [(-r, -r), (r, -r), (r, r), (-r, r)]
    turret_pts = [(tcx + x * ca - y * sa, tcy + x * sa + y * ca) for x, y in local_sq]
    extrude_prism_in_bm(bm, turret_pts, 0.0, 29.5, mat_side=0, mat_top=1)
    for ti in range(4):
        tp1, tp2 = turret_pts[ti], turret_pts[(ti + 1) % 4]
        add_box_between(bm, tp1, tp2, 28.6, 29.6, thickness=0.85, offset_out=0.32, mat_idx=4)
    add_pitched_mansard_roof_in_bm(bm, turret_pts, 29.6, height=4.0, inset_factor=0.16, mat_slate=1, mat_trim=4, add_dormers=False)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def add_streetfront_props_and_signage(palette, collection):
    """
    Adds street-level props across Rue Saint-Sulpice, Rue De Brésoles, and Rue Notre-Dame:
    - Hanging boutique signage & wrought-iron brackets
    - Octagonal red STOP sign at Rue De Brésoles & Rue Saint-Sulpice (`(62.8, 2.2)` in `Rue_NotreDame_Side.jpg`!)
    - Cast-iron bollards & street-side planters/bins along Rue De Brésoles (`Coté_Place_dArmes_East.jpg`)
    """
    mesh = bpy.data.meshes.new("Streetfront_Props_And_Signage_Mesh")
    obj = bpy.data.objects.new("Streetfront_Props_And_Signage", mesh)
    collection.objects.link(obj)

    mat_iron = palette["Mat_MTL_CastIron_Black"]
    mat_wood = palette["Mat_MTL_Warm_Wood"]
    mat_stone = palette["Mat_MTL_PierreGrise_Limestone"]
    mat_gold = palette["Mat_MTL_Autumn_Gold"]
    mat_red = palette["Mat_MTL_Awning_Red"]
    for m in (mat_iron, mat_wood, mat_stone, mat_gold, mat_red):
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Hanging boutique sign at (42.8, 10.1, 3.65)
    sx, sy = 42.8, 10.1
    nx, ny = -0.38, -0.92
    add_box_between(bm, (sx, sy), (sx + nx * 1.25, sy + ny * 1.25), 3.82, 3.90, thickness=0.08, offset_out=0.0, mat_idx=0)
    add_box_between(bm, (sx + nx * 0.30, sy + ny * 0.30), (sx + nx * 1.18, sy + ny * 1.18), 3.28, 3.76, thickness=0.10, offset_out=0.0, mat_idx=1)

    # 2. Red STOP sign post at corner of Rue Saint-Sulpice & Rue De Brésoles (visible on left of Rue_NotreDame_Side.jpg!)
    stx, sty = 61.8, 3.2
    post_pts = [(stx + 0.04 * math.cos(a), sty + 0.04 * math.sin(a)) for a in [k * math.pi / 4 for k in range(8)]]
    extrude_prism_in_bm(bm, post_pts, 0.12, 2.35, mat_side=0, mat_top=0)
    add_box_between(bm, (stx - 0.05, sty - 0.32), (stx + 0.05, sty + 0.32), 1.85, 2.48, thickness=0.06, offset_out=0.0, mat_idx=4)

    # 3. Cast-iron heritage bollards along Rue Saint-Sulpice & Rue De Brésoles curbs
    bollard_coords = [
        (64.5, 1.8), (67.2, 8.8), (70.0, 16.0), (73.5, 25.0),
        (52.0, 6.2), (44.0, 9.4), (36.0, 12.5), (28.0, 15.6)
    ]
    for bx, by in bollard_coords:
        b_pts = [(bx + 0.11 * math.cos(a), by + 0.11 * math.sin(a)) for a in [k * math.pi / 6 for k in range(12)]]
        extrude_prism_in_bm(bm, b_pts, 0.12, 0.98, mat_side=0, mat_top=0, smooth_sides=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    add_bevel_modifier(obj, width=0.015, segments=2)
    return obj


def build_streets_sidewalks_and_curbs(dossier, palette, collection):
    sat_info = dossier.get("satellite", {})
    sat_cx, sat_cy = sat_info.get("center_xy_m", [67.096, 25.603])
    sat_span = sat_info.get("span_meters", 133.93) * 2.5
    sat_img_path = sat_info.get("image_path", "")

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(sat_cx, sat_cy, -0.06))
    ground_obj = bpy.context.active_object
    ground_obj.name = "Ground_Base_Plaza_Granite"
    ground_obj.scale = (sat_span, sat_span, 1.0)
    for col in list(ground_obj.users_collection):
        col.objects.unlink(ground_obj)
    collection.objects.link(ground_obj)
    ground_obj.data.materials.append(palette["Mat_MTL_Street_Asphalt"])

    true_span = sat_info.get("span_meters", 133.93)
    if os.path.exists(sat_img_path):
        bpy.ops.mesh.primitive_plane_add(size=true_span, location=(sat_cx, sat_cy, -0.03))
        ortho_obj = bpy.context.active_object
        ortho_obj.name = "Ground_Satellite_Ortho"
        for col in list(ortho_obj.users_collection):
            col.objects.unlink(ortho_obj)
        collection.objects.link(ortho_obj)

        mat_sat = bpy.data.materials.new("Mat_MTL_Satellite_Ortho")
        mat_sat.use_nodes = True
        nodes = mat_sat.node_tree.nodes
        links = mat_sat.node_tree.links
        bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Roughness"].default_value = 0.88
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(sat_img_path)
        links.new(bsdf.inputs["Base Color"], tex.outputs["Color"])
        ortho_obj.data.materials.append(mat_sat)

    road_mesh = bpy.data.meshes.new("Streets_And_Sidewalks_Mesh")
    road_obj = bpy.data.objects.new("Streets_And_Sidewalks", road_mesh)
    collection.objects.link(road_obj)

    mat_cobble = palette["Mat_MTL_Cobblestone"]
    mat_asphalt = palette["Mat_MTL_Street_Asphalt"]
    mat_sidewalk = palette["Mat_MTL_Plaza_Light_Granite"]
    mat_curb = palette["Mat_MTL_Plaza_Charcoal_Granite"]
    for m in (mat_cobble, mat_asphalt, mat_sidewalk, mat_curb):
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
            width = 2.6
            z_top = 0.14
            mat_i = 2
        elif "Saint-Sulpice" in name or surface in ("sett", "paving_stones") or hw_type == "pedestrian":
            width = 8.2
            z_top = 0.02
            mat_i = 0
        else:
            width = 9.2
            z_top = 0.02
            mat_i = 1

        for j in range(len(pts) - 1):
            p1, p2 = pts[j], pts[j + 1]
            add_box_between(bm, p1, p2, -0.02, z_top, thickness=width, offset_out=0.0, mat_idx=mat_i)

    sw_blocks = [
        # SW Sub-block sidewalk apron
        [(4.2, 24.5), (24.5, 13.5), (65.5, -1.8), (79.0, 34.5), (56.5, 52.0), (24.5, 64.5), (11.5, 38.5)],
        # Middle Sub-block sidewalk apron (East of Côte de la Place d'Armes / West of Rue De Brésoles)
        [(24.5, 62.5), (57.5, 46.5), (79.5, 39.5), (94.0, 75.5), (108.5, 114.5), (62.5, 131.5)],
        # East Sub-block sidewalk apron (East of Rue De Brésoles)
        [(76.5, -3.5), (108.5, -16.5), (141.5, 72.5), (110.5, 84.5)],
        # Far-East Sub-block (161202161 along Rue Le Royer)
        [(120.5, -22.5), (161.5, -38.0), (195.0, 52.0), (154.5, 67.5)],
        # South Sidewalk along Basilique Notre-Dame on Rue Saint-Sulpice (visible on left of Aldred_ArtDeco_Facade.jpg!)
        [(6.0, 15.0), (62.0, -7.5), (58.0, -16.0), (2.0, 6.0)],
        # West Sidewalk along Rue Notre-Dame Ouest (visible on right of NY_Life_Red_Sandstone_Corner.jpg!)
        [(-8.0, 24.0), (4.5, 20.0), (18.0, 60.0), (6.0, 65.0)],
    ]
    for sb_pts in sw_blocks:
        ccw_sb = ensure_ccw(sb_pts)
        extrude_prism_in_bm(bm, ccw_sb, -0.02, 0.15, mat_side=3, mat_top=2)
        for k in range(len(ccw_sb)):
            q1, q2 = ccw_sb[k], ccw_sb[(k + 1) % len(ccw_sb)]
            add_box_between(bm, q1, q2, 0.0, 0.17, thickness=0.28, offset_out=0.0, mat_idx=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(road_mesh)
    bm.free()
    add_bevel_modifier(road_obj, width=0.02, segments=2)
    return road_obj


def add_highpoly_organic_foliage_cluster(bm, center_vec, rx, ry, rz, mat_idx):
    """Creates a subdivided, organically displaced smooth-shaded leaf cluster."""
    ret = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    verts = ret["verts"]
    for v in verts:
        n_val = 1.0 + 0.18 * math.sin(v.co.x * 5.2 + v.co.y * 4.1) * math.cos(v.co.z * 6.3)
        v.co.x = center_vec.x + v.co.x * rx * n_val
        v.co.y = center_vec.y + v.co.y * ry * n_val
        v.co.z = center_vec.z + v.co.z * rz * n_val

    for f in bm.faces:
        if all(v in verts for v in f.verts):
            f.material_index = mat_idx
            f.smooth = True


def build_trees_and_streetlamps(dossier, palette, collection):
    prop_mesh = bpy.data.meshes.new("Trees_And_Streetlamps_Mesh")
    prop_obj = bpy.data.objects.new("Trees_And_Streetlamps", prop_mesh)
    collection.objects.link(prop_obj)

    mat_bark = palette["Mat_MTL_Tree_Bark"]
    mat_gold = palette["Mat_MTL_Autumn_Gold"]
    mat_amber = palette["Mat_MTL_Autumn_Amber"]
    mat_green = palette["Mat_MTL_Autumn_OliveGreen"]
    mat_iron = palette["Mat_MTL_CastIron_Black"]
    mat_lamp_glow = kit.get_or_create_pbr_material("Mat_MTL_Lamp_WarmGlow", "#FFF3D1", roughness=0.12)
    bsdf = next(n for n in mat_lamp_glow.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (1.0, 0.88, 0.62, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 4.0

    for m in (mat_bark, mat_gold, mat_amber, mat_green, mat_iron, mat_lamp_glow):
        prop_obj.data.materials.append(m)

    bm = bmesh.new()
    rng = random.Random(4004)

    for t in dossier["osm_features"].get("trees", []):
        tx, ty = float(t["x"]), float(t["y"])
        trunk_h = rng.uniform(3.2, 4.2)
        crown_r = rng.uniform(2.0, 2.8)
        leaf_mat_idx = rng.choice([1, 2, 3])

        t_pts = [(tx + 0.18 * math.cos(a), ty + 0.18 * math.sin(a)) for a in [k * math.pi / 8 for k in range(16)]]
        extrude_prism_in_bm(bm, t_pts, 0.0, trunk_h + 1.0, mat_side=0, mat_top=0, smooth_sides=True)

        add_highpoly_organic_foliage_cluster(
            bm, Vector((tx, ty, trunk_h + 2.2)), crown_r * 0.90, crown_r * 0.90, crown_r * 0.78, leaf_mat_idx
        )
        for b_i in range(4):
            b_ang = b_i * (math.pi * 0.5) + rng.uniform(-0.25, 0.25)
            bx = tx + math.cos(b_ang) * crown_r * 0.52
            by = ty + math.sin(b_ang) * crown_r * 0.52
            bz = trunk_h + 1.45 + rng.uniform(-0.2, 0.35)
            add_highpoly_organic_foliage_cluster(
                bm, Vector((bx, by, bz)), crown_r * 0.62, crown_r * 0.62, crown_r * 0.54, leaf_mat_idx
            )

    lamp_coords = [
        (56.5, 4.2), (63.2, 1.5), (78.5, -2.2), (28.0, 14.8),
        (12.5, 36.0), (14.2, 54.0), (24.0, 56.5), (36.5, 78.0),
        (46.0, 54.0), (68.0, 44.0), (85.0, 46.0),
    ]
    for lx, ly in lamp_coords:
        base_pts = [(lx + 0.18 * math.cos(a), ly + 0.18 * math.sin(a)) for a in [k * math.pi / 8 for k in range(16)]]
        plinth_pts = [(lx + 0.12 * math.cos(a), ly + 0.12 * math.sin(a)) for a in [k * math.pi / 8 for k in range(16)]]
        post_pts = [(lx + 0.065 * math.cos(a), ly + 0.065 * math.sin(a)) for a in [k * math.pi / 8 for k in range(16)]]
        extrude_prism_in_bm(bm, base_pts, 0.12, 0.65, mat_side=4, mat_top=4, smooth_sides=True)
        extrude_prism_in_bm(bm, plinth_pts, 0.65, 1.25, mat_side=4, mat_top=4, smooth_sides=True)
        extrude_prism_in_bm(bm, post_pts, 1.25, 4.25, mat_side=4, mat_top=4, smooth_sides=True)
        add_box_between(bm, (lx - 0.38, ly), (lx + 0.38, ly), 3.95, 4.04, thickness=0.07, offset_out=0.0, mat_idx=4)
        for gx in (lx - 0.34, lx + 0.34):
            add_highpoly_organic_foliage_cluster(bm, Vector((gx, ly, 4.22)), 0.18, 0.18, 0.22, 5)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(prop_mesh)
    bm.free()
    return prop_obj


def setup_world_and_lighting():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 64
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True

    world = bpy.data.worlds.new("World_MTL_VM_0004") if not scene.world else scene.world
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
    else:
        sky = nodes.new("ShaderNodeTexSky")
        sky.sky_type = 'HOSEK_WILKIE'
        links.new(bg.inputs["Color"], sky.outputs["Color"])

    sun_data = bpy.data.lights.new(name="Sun_MTL_VM_0004", type='SUN')
    sun_data.energy = 3.8
    sun_data.color = (1.0, 0.96, 0.89)
    sun_data.angle = math.radians(1.2)
    sun_obj = bpy.data.objects.new(name="Sun_MTL_VM_0004", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(12.0), math.radians(-145.0))


def render_cameras(dossier, iter_num=1):
    scene = bpy.context.scene
    cam_col = get_or_create_collection("Cameras_MTL-VM-0004")

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.image_settings.file_format = 'PNG'

    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        cx, cy = cam_info["blender_cam_xy_m"]
        cz = 1.7
        # Use the exact Google Street View `heading` from the updated dossier.json (`255.1`, `195.7`, `257.2`, `238.7`)
        heading = float(cam_info.get("heading", cam_info.get("heading_deg", 0.0)))
        pitch = 10.0

        cam_data = bpy.data.cameras.new(f"Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(cam_info.get("fov_deg", 90.0))
        cam_data.clip_start = 0.2
        cam_data.clip_end = 1000.0

        cam_obj = bpy.data.objects.new(f"Cam_{label}", cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cx, cy, cz)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch), 0.0, math.radians(-heading))

        scene.camera = cam_obj
        out_path = os.path.join(RENDERS_DIR, f"iter{iter_num}_{label}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View Camera [{label}] -> {out_path}")

    ov_data = bpy.data.cameras.new("Cam_Overview_MTL_VM_0004")
    ov_data.lens_unit = 'FOV'
    ov_data.angle = math.radians(62.0)
    ov_data.clip_end = 1500.0
    ov_obj = bpy.data.objects.new("Cam_Overview_MTL_VM_0004", ov_data)
    cam_col.objects.link(ov_obj)

    ov_obj.location = (-36.0, -18.0, 92.0)
    target = Vector((68.0, 44.0, 22.0))
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

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

    palette = kit.create_montreal_material_palette()
    upgrade_palette_with_polyhaven_2k(palette)

    master_col = get_or_create_collection(f"Block_{BLOCK_ID}")
    owned_col = get_or_create_collection(f"Block_{BLOCK_ID}_Owned", parent=master_col)
    proxy_col = get_or_create_collection(f"Block_{BLOCK_ID}_Context_Proxy", parent=master_col)
    proxy_col.hide_render = True
    proxy_col.hide_viewport = True

    build_streets_sidewalks_and_curbs(dossier, palette, owned_col)

    owned_count = 0
    proxy_count = 0

    buildings = dossier["osm_features"]["buildings"]
    for b in buildings:
        bid = b["id"]
        coords = b["coords_xy"]
        is_owned = bool(b.get("is_primary_owner", False))

        if is_owned:
            owned_count += 1
            if bid == 339884213:
                build_edifice_aldred_and_70_notredame(coords, palette, owned_col)
            elif bid == 339884214:
                build_ny_life_red_sandstone_building(coords, palette, owned_col)
            elif bid == 182859305:
                build_edifice_duluth_corner(coords, palette, owned_col)
            elif bid in (182859304, 182859306):
                # 5-story classic cut-stone Rue Saint-Sulpice buildings (visible on right of Aldred_ArtDeco_Facade.jpg!)
                h_sulpice = 19.8 if bid == 182859304 else 20.6
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_RueSaintSulpice_Heritage",
                    coords_xy=coords,
                    height=h_sulpice,
                    floor_height=3.7,
                    mat_wall=palette["Mat_MTL_PierreGrise_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=owned_col,
                    roof_style="cornice_flat",
                    white_shop_muntins=True,
                    modern_glass_bays=False,
                    bay_target_width=3.2,
                    all_buildings=buildings,
                    my_bid=bid,
                )
            elif bid == 182859307:
                # 6-story modern-classic stone-pier & glass-bay building in Rue_NotreDame_Side.jpg & Coté_Place_dArmes_East.jpg!
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_RueSaintSulpice_ModernClassic",
                    coords_xy=coords,
                    height=23.6,
                    floor_height=3.8,
                    mat_wall=palette["Mat_MTL_PierreGrise_Limestone"],
                    mat_roof=palette["Mat_MTL_Plaza_Light_Granite"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_Dark_Bronze_CurtainWall"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=owned_col,
                    roof_style="cornice_flat",
                    white_shop_muntins=False,
                    modern_glass_bays=True,
                    bay_target_width=3.4,
                    has_rooftop_penthouse=True,
                    all_buildings=buildings,
                    my_bid=bid,
                )
            elif bid == 188991343:
                # 5-story Pierre Grise building with arched ground-floor stone arcade & corner quoins in Coté_Place_dArmes_East.jpg!
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_RueDeBresoles_ArchedArcade",
                    coords_xy=coords,
                    height=21.0,
                    floor_height=3.9,
                    mat_wall=palette["Mat_MTL_PierreGrise_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=owned_col,
                    roof_style="cornice_flat",
                    white_shop_muntins=False,
                    modern_glass_bays=False,
                    arched_ground_arcade=True,
                    bay_target_width=3.5,
                    all_buildings=buildings,
                    my_bid=bid,
                )
            elif bid in (161201916, 161202161):
                h = 19.4 if bid == 161201916 else 18.8
                w_mat = palette["Mat_MTL_PierreGrise_Limestone"] if bid == 161201916 else palette["Mat_MTL_WarmBuff_Limestone"]
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}_CoursLeRoyer",
                    coords_xy=coords,
                    height=h,
                    floor_height=3.7,
                    mat_wall=w_mat,
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=owned_col,
                    roof_style="cornice_flat",
                    white_shop_muntins=False,
                    modern_glass_bays=False,
                    arched_ground_arcade=True,
                    bay_target_width=3.2,
                    has_rooftop_penthouse=True,
                    all_buildings=buildings,
                    my_bid=bid,
                )
            else:
                b_hash = int(bid) % 5
                b_stagger = (((int(bid) * 5) % 32) - 16) * 0.24
                height = 19.0 + b_stagger
                fh = 3.55 + ((int(bid) * 11) % 13) * 0.05
                wall_mats = [
                    palette["Mat_MTL_PierreGrise_Limestone"],
                    palette["Mat_MTL_WarmBuff_Limestone"],
                    palette["Mat_MTL_Heritage_RedBrick"],
                    palette["Mat_MTL_PierreGrise_Limestone"],
                    palette["Mat_MTL_Red_Sandstone"],
                ]
                r_style = "mansard" if b_hash in (1, 3) else "cornice_flat"
                build_detailed_facade_building(
                    name=f"MTL_Owned_{bid}",
                    coords_xy=coords,
                    height=height,
                    floor_height=fh,
                    mat_wall=wall_mats[b_hash],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=owned_col,
                    roof_style=r_style,
                    white_shop_muntins=(b_hash == 0),
                    modern_glass_bays=False,
                    bay_target_width=3.1,
                    all_buildings=buildings,
                    my_bid=bid,
                )
        else:
            proxy_count += 1
            if bid == 4320792:
                # High-detail Gothic context proxy for Basilique Notre-Dame
                build_basilique_notre_dame_context(coords, palette, proxy_col)
            else:
                build_detailed_facade_building(
                    name=f"MTL_Context_Proxy_{bid}",
                    coords_xy=coords,
                    height=16.5,
                    floor_height=3.8,
                    mat_wall=palette["Mat_MTL_Fieldstone_Rubble"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_CastIron_Black"],
                    mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
                    collection=proxy_col,
                    roof_style="cornice_flat",
                    bay_target_width=3.5,
                    all_buildings=buildings,
                    my_bid=bid,
                )

    build_notredame_west_context_backdrops(palette, proxy_col)
    add_streetfront_props_and_signage(palette, owned_col)
    build_trees_and_streetlamps(dossier, palette, owned_col)

    print(f"Built {owned_count} Owned buildings in Block_{BLOCK_ID}_Owned and {proxy_count} Context Proxy buildings in Block_{BLOCK_ID}_Context_Proxy.")

    setup_world_and_lighting()
    render_cameras(dossier, iter_num=1)

    blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.blend")
    usdc_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.usdc")
    bpy.context.preferences.filepaths.save_version = 0
    tmp_blend = blend_path + ".tmp.blend"
    if os.path.exists(tmp_blend):
        try:
            os.remove(tmp_blend)
        except OSError:
            pass
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
    for ext in ("", "@", "@1", "1"):
        p = blend_path + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    if os.path.exists(tmp_blend):
        os.replace(tmp_blend, blend_path)
    bpy.ops.wm.usd_export(filepath=usdc_path, selected_objects_only=False)
    print(f"Saved {blend_path} and exported {usdc_path}")

    # Run Iteration 2 AAA upgrade pass (Poly Haven 3D trees/lamps, 3D stepped stone arches, flat glass normals, distinct PBR facade materials)
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import upgrade_MTL_VM_0004
    upgrade_MTL_VM_0004.upgrade_block()


if __name__ == "__main__":
    main()

