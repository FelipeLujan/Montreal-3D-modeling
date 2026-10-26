import os
import sys
import json
import math
import shutil
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

SRC_DIR = r"C:\Users\Felipe\Documents\coding\montreal\src"
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0008"
BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_BLOCKS_DIR = os.path.join(BASE_DIR, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
KIT_BLEND_PATH = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_BLOCKS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def get_or_create_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        if parent is None:
            bpy.context.scene.collection.children.link(col)
        else:
            parent.children.link(col)
    return col


def load_image_safe(filepath, colorspace="sRGB"):
    if not os.path.exists(filepath):
        return None
    img = bpy.data.images.load(filepath, check_existing=True)
    if colorspace and hasattr(img, "colorspace_settings"):
        try:
            img.colorspace_settings.name = colorspace
        except Exception:
            pass
    return img


def build_pbr_textured_material(
    name,
    diff_file,
    rough_file,
    norm_file,
    tint_hex="#FFFFFF",
    tint_factor=0.35,
    box_scale=0.38,
    roughness_mult=1.0,
    normal_strength=1.0,
    metallic=0.0,
    brick_overlay=None,
):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = metallic
    links.new(out.inputs["Surface"], bsdf.outputs["BSDF"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (box_scale, box_scale, box_scale)
    links.new(mapping.inputs["Vector"], tex_coord.outputs["Object"])

    img_diff = load_image_safe(os.path.join(POLYHAVEN_DIR, diff_file), "sRGB") if diff_file else None
    if img_diff:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = img_diff
        tex_d.projection = 'BOX'
        tex_d.projection_blend = 0.25
        links.new(tex_d.inputs["Vector"], mapping.outputs["Vector"])

        mix_c = nodes.new("ShaderNodeMix")
        mix_c.data_type = 'RGBA'
        mix_c.blend_type = 'MIX'
        mix_c.inputs["Factor"].default_value = tint_factor
        mix_c.inputs["B"].default_value = kit.hex_to_rgba(tint_hex)
        links.new(mix_c.inputs["A"], tex_d.outputs["Color"])
        base_col_socket = mix_c.outputs["Result"]
    else:
        rgb = nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = kit.hex_to_rgba(tint_hex)
        base_col_socket = rgb.outputs[0]

    if brick_overlay is not None:
        brick = nodes.new("ShaderNodeTexBrick")
        brick.offset = 0.5
        brick.offset_frequency = 2
        brick.squash = brick_overlay.get("squash", 1.5)
        brick.inputs["Scale"].default_value = brick_overlay.get("scale", 2.2)
        brick.inputs["Mortar Size"].default_value = brick_overlay.get("mortar_size", 0.02)
        brick.inputs["Mortar Smooth"].default_value = 0.1
        brick.inputs["Bias"].default_value = 0.0
        brick.inputs["Brick Width"].default_value = brick_overlay.get("brick_w", 0.65)
        brick.inputs["Row Height"].default_value = brick_overlay.get("row_h", 0.32)
        brick.inputs["Color1"].default_value = kit.hex_to_rgba(brick_overlay.get("c1", "#787570"))
        brick.inputs["Color2"].default_value = kit.hex_to_rgba(brick_overlay.get("c2", "#A49E95"))
        brick.inputs["Mortar"].default_value = kit.hex_to_rgba(brick_overlay.get("mortar", "#42403D"))
        links.new(brick.inputs["Vector"], tex_coord.outputs["Object"])

        mix_b = nodes.new("ShaderNodeMix")
        mix_b.data_type = 'RGBA'
        mix_b.blend_type = 'OVERLAY'
        mix_b.inputs["Factor"].default_value = brick_overlay.get("factor", 0.55)
        links.new(mix_b.inputs["A"], base_col_socket)
        links.new(mix_b.inputs["B"], brick.outputs["Color"])
        links.new(bsdf.inputs["Base Color"], mix_b.outputs["Result"])
    else:
        links.new(bsdf.inputs["Base Color"], base_col_socket)

    img_rough = load_image_safe(os.path.join(POLYHAVEN_DIR, rough_file), "Non-Color") if rough_file else None
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
        bsdf.inputs["Roughness"].default_value = 0.65 * roughness_mult

    img_norm = load_image_safe(os.path.join(POLYHAVEN_DIR, norm_file), "Non-Color") if norm_file else None
    if img_norm:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = img_norm
        tex_n.projection = 'BOX'
        tex_n.projection_blend = 0.25
        links.new(tex_n.inputs["Vector"], mapping.outputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal_strength
        links.new(nmap.inputs["Color"], tex_n.outputs["Color"])
        links.new(bsdf.inputs["Normal"], nmap.outputs["Normal"])

    return mat


def create_custom_materials(palette):
    """
    Configures all materials using the verified 2K Poly Haven texture files in `assets/polyhaven/`:
    - `sandstone_blocks_05_Diffuse_2k.jpg` / `_Rough_2k.jpg` / `_nor_gl_2k.jpg`
    - `cobblestone_floor_08_Diffuse_2k.jpg` / `_Rough_2k.jpg` / `_nor_gl_2k.jpg`
    - `castle_brick_02_red_Diffuse_2k.jpg` / `_Rough_2k.jpg` / `_nor_gl_2k.jpg`
    - `asphalt_02_Diffuse_2k.jpg` / `_Rough_2k.jpg` / `_nor_gl_2k.jpg`
    - `rock_wall_16_diff_2k.jpg` / `_rough_2k.jpg` / `_nor_gl_2k.jpg`
    """
    palette["Mat_MTL_PierreGrise_Limestone"] = build_pbr_textured_material(
        "Mat_MTL_PierreGrise_Limestone",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint_hex="#B4B1A9",
        tint_factor=0.38,
        box_scale=0.42,
        roughness_mult=0.92,
        normal_strength=1.25,
        brick_overlay={"scale": 1.6, "brick_w": 0.85, "row_h": 0.38, "mortar_size": 0.015, "c1": "#9E9B93", "c2": "#C4C1B8", "mortar": "#585651", "factor": 0.42},
    )

    palette["Mat_MTL_WarmBuff_Limestone"] = build_pbr_textured_material(
        "Mat_MTL_WarmBuff_Limestone",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint_hex="#CBBCA0",
        tint_factor=0.36,
        box_scale=0.40,
        roughness_mult=0.90,
        normal_strength=1.20,
        brick_overlay={"scale": 1.6, "brick_w": 0.85, "row_h": 0.38, "mortar_size": 0.015, "c1": "#B8A88C", "c2": "#D8C9AE", "mortar": "#665D4E", "factor": 0.40},
    )

    palette["Mat_MTL_Heritage_RedBrick"] = build_pbr_textured_material(
        "Mat_MTL_Heritage_RedBrick",
        "castle_brick_02_red_Diffuse_2k.jpg",
        "castle_brick_02_red_Rough_2k.jpg",
        "castle_brick_02_red_nor_gl_2k.jpg",
        tint_hex="#9B4234",
        tint_factor=0.25,
        box_scale=0.48,
        roughness_mult=1.0,
        normal_strength=1.25,
    )

    palette["Mat_MTL_Cobblestone_Street"] = build_pbr_textured_material(
        "Mat_MTL_Cobblestone_Street",
        "cobblestone_floor_08_Diffuse_2k.jpg",
        "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg",
        tint_hex="#8A7E78",
        tint_factor=0.28,
        box_scale=0.42,
        roughness_mult=0.88,
        normal_strength=1.45,
        brick_overlay={"scale": 4.2, "brick_w": 0.42, "row_h": 0.24, "mortar_size": 0.025, "c1": "#6E6460", "c2": "#9E8E86", "mortar": "#363230", "factor": 0.58},
    )

    palette["Mat_MTL_Street_Asphalt"] = build_pbr_textured_material(
        "Mat_MTL_Street_Asphalt",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#5A5D62",
        tint_factor=0.30,
        box_scale=0.32,
        roughness_mult=0.92,
        normal_strength=1.05,
    )

    palette["Mat_MTL_Light_Granite_Steps"] = build_pbr_textured_material(
        "Mat_MTL_Light_Granite_Steps",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#C4C0B6",
        tint_factor=0.58,
        box_scale=0.50,
        roughness_mult=0.80,
        normal_strength=0.75,
        brick_overlay={"scale": 0.9, "brick_w": 1.4, "row_h": 1.2, "mortar_size": 0.012, "c1": "#B8B4AA", "c2": "#CCC8BE", "mortar": "#62605B", "factor": 0.35},
    )

    palette["Mat_MTL_Dark_Honed_Granite"] = build_pbr_textured_material(
        "Mat_MTL_Dark_Honed_Granite",
        "rock_wall_16_diff_2k.jpg",
        "rock_wall_16_rough_2k.jpg",
        "rock_wall_16_nor_gl_2k.jpg",
        tint_hex="#36393E",
        tint_factor=0.65,
        box_scale=0.45,
        roughness_mult=0.68,
        normal_strength=0.95,
    )

    palette["Mat_MTL_Slate_Roof_Dark"] = build_pbr_textured_material(
        "Mat_MTL_Slate_Roof_Dark",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#24282E",
        tint_factor=0.68,
        box_scale=0.45,
        roughness_mult=0.65,
        normal_strength=0.85,
    )

    palette["Mat_MTL_Verdigris_Copper"] = build_pbr_textured_material(
        "Mat_MTL_Verdigris_Copper",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#4A8A72",
        tint_factor=0.78,
        box_scale=0.50,
        roughness_mult=0.55,
        normal_strength=0.55,
        metallic=0.65,
    )

    palette["Mat_MTL_Heritage_Green"] = build_pbr_textured_material(
        "Mat_MTL_Heritage_Green",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#1D3E30",
        tint_factor=0.82,
        box_scale=0.50,
        roughness_mult=0.48,
        normal_strength=0.45,
        metallic=0.18,
    )

    palette["Mat_MTL_Warm_Wood"] = build_pbr_textured_material(
        "Mat_MTL_Warm_Wood",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint_hex="#7E421E",
        tint_factor=0.78,
        box_scale=0.55,
        roughness_mult=0.52,
        normal_strength=0.50,
    )

    palette["Mat_MTL_Window_Frame_Light"] = build_pbr_textured_material(
        "Mat_MTL_Window_Frame_Light",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#EAE6DC",
        tint_factor=0.78,
        box_scale=0.50,
        roughness_mult=0.48,
        normal_strength=0.35,
    )

    palette["Mat_MTL_CastIron_Black"] = build_pbr_textured_material(
        "Mat_MTL_CastIron_Black",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#181A1D",
        tint_factor=0.82,
        box_scale=0.55,
        roughness_mult=0.42,
        normal_strength=0.45,
        metallic=0.82,
    )

    palette["Mat_MTL_Centaur_Blue"] = build_pbr_textured_material(
        "Mat_MTL_Centaur_Blue",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#1C4680",
        tint_factor=0.85,
        box_scale=0.50,
        roughness_mult=0.55,
        normal_strength=0.35,
    )

    palette["Mat_MTL_Statue_Gold"] = build_pbr_textured_material(
        "Mat_MTL_Statue_Gold",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#CFA032",
        tint_factor=0.88,
        box_scale=0.50,
        roughness_mult=0.35,
        normal_strength=0.30,
        metallic=0.85,
    )

    palette["Mat_MTL_BN_Red"] = build_pbr_textured_material(
        "Mat_MTL_BN_Red",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#94221E",
        tint_factor=0.85,
        box_scale=0.50,
        roughness_mult=0.45,
        normal_strength=0.35,
    )

    palette["Mat_MTL_Rust_Grate"] = build_pbr_textured_material(
        "Mat_MTL_Rust_Grate",
        "cobblestone_floor_08_Diffuse_2k.jpg",
        "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg",
        tint_hex="#3E322A",
        tint_factor=0.68,
        box_scale=0.65,
        roughness_mult=0.65,
        normal_strength=1.20,
        metallic=0.72,
    )

    palette["Mat_MTL_Portal_Warm_Glow"] = build_pbr_textured_material(
        "Mat_MTL_Portal_Warm_Glow",
        None,
        None,
        None,
        tint_hex="#FFE2A8",
        tint_factor=1.0,
    )
    bsdf_g = next(n for n in palette["Mat_MTL_Portal_Warm_Glow"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Emission Color" in bsdf_g.inputs:
        bsdf_g.inputs["Emission Color"].default_value = kit.hex_to_rgba("#FFD584")
        bsdf_g.inputs["Emission Strength"].default_value = 3.5

    glass = palette.get("Mat_MTL_Window_Glass_Dark")
    if glass is None:
        glass = bpy.data.materials.new("Mat_MTL_Window_Glass_Dark")
        palette["Mat_MTL_Window_Glass_Dark"] = glass
    glass.use_nodes = True
    gnodes = glass.node_tree.nodes
    glinks = glass.node_tree.links
    gnodes.clear()
    gout = gnodes.new("ShaderNodeOutputMaterial")
    gbsdf = gnodes.new("ShaderNodeBsdfPrincipled")
    gbsdf.inputs["Base Color"].default_value = kit.hex_to_rgba("#0D151E")
    gbsdf.inputs["Roughness"].default_value = 0.05
    gbsdf.inputs["Metallic"].default_value = 0.18
    if "IOR" in gbsdf.inputs:
        gbsdf.inputs["IOR"].default_value = 1.52
    glinks.new(gout.inputs["Surface"], gbsdf.outputs["BSDF"])

    # Smooth glossy automotive paint, alloy rim, tire rubber & deep portico shadow materials
    for mat_name, hex_col, rough, metal in (
        ("Mat_MTL_Auto_Paint_Charcoal", "#161B22", 0.14, 0.55),
        ("Mat_MTL_Auto_Paint_Silver", "#D4D9DF", 0.16, 0.62),
        ("Mat_MTL_Auto_Paint_Crimson", "#6E161A", 0.15, 0.48),
        ("Mat_MTL_Alloy_Rim", "#B8BFC6", 0.22, 0.88),
        ("Mat_MTL_Rubber_Tire", "#141517", 0.78, 0.02),
        ("Mat_MTL_Portico_Deep_Shadow", "#18191C", 0.85, 0.02),
    ):
        m_auto = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
        m_auto.use_nodes = True
        anodes = m_auto.node_tree.nodes
        alinks = m_auto.node_tree.links
        anodes.clear()
        aout = anodes.new("ShaderNodeOutputMaterial")
        absdf = anodes.new("ShaderNodeBsdfPrincipled")
        absdf.inputs["Base Color"].default_value = kit.hex_to_rgba(hex_col)
        absdf.inputs["Roughness"].default_value = rough
        absdf.inputs["Metallic"].default_value = metal
        alinks.new(aout.inputs["Surface"], absdf.outputs["BSDF"])
        palette[mat_name] = m_auto

    return palette


def apply_bevel_and_smooth(obj, width=0.025, segments=2):
    if obj is None or obj.type != 'MESH':
        return
    bev = obj.modifiers.new(name="ArchBevel", type='BEVEL')
    bev.width = width
    bev.segments = segments
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(35.0)


def add_oriented_box(bm, center_xy, dir_2d, perp_2d, width, depth, z_min, z_max, mat_idx=0):
    cx, cy = center_xy
    dx, dy = dir_2d
    px, py = perp_2d
    hw = width * 0.5
    hd = depth * 0.5
    corners_2d = [
        (cx - dx * hw - px * hd, cy - dy * hw - py * hd),
        (cx + dx * hw - px * hd, cy + dy * hw - py * hd),
        (cx + dx * hw + px * hd, cy + dy * hw + py * hd),
        (cx - dx * hw + px * hd, cy - dy * hw + py * hd),
    ]
    v_bot = [bm.verts.new((x, y, z_min)) for (x, y) in corners_2d]
    v_top = [bm.verts.new((x, y, z_max)) for (x, y) in corners_2d]
    faces = []
    try:
        faces.append(bm.faces.new(v_bot[::-1]))
        faces.append(bm.faces.new(v_top))
        for i in range(4):
            ni = (i + 1) % 4
            faces.append(bm.faces.new((v_bot[i], v_bot[ni], v_top[ni], v_top[i])))
    except ValueError:
        pass
    for f in faces:
        f.material_index = mat_idx
    return faces


def inset_polygon_2d(pts_2d, inset_dist=0.85):
    """Insets a CCW 2D polygon perpendicular to each edge by `inset_dist` so recessed windows are never blocked by the core box."""
    n = len(pts_2d)
    new_pts = []
    for i in range(n):
        p_prev = pts_2d[(i - 1) % n]
        p_curr = pts_2d[i]
        p_next = pts_2d[(i + 1) % n]
        e1 = (p_curr - p_prev).normalized()
        e2 = (p_next - p_curr).normalized()
        in1 = Vector((-e1.y, e1.x))
        in2 = Vector((-e2.y, e2.x))
        avg_in = in1 + in2
        if avg_in.length < 0.1:
            avg_in = in1
        else:
            avg_in.normalize()
        new_pts.append(p_curr + avg_in * inset_dist)
    return new_pts


def add_semicircular_arch_recess(
    bm, center_xy, dir_2d, out_2d, width, z_min, z_max, recess_depth=0.48,
    wall_mat=0, trim_mat=1, inner_mat=3, frame_mat=4, add_voussoirs=True
):
    hw = width * 0.5
    arch_r = hw
    spring_z = max(z_min + 0.4, z_max - arch_r)
    t_dir = Vector((dir_2d[0], dir_2d[1])).normalized()
    out_dir = Vector((out_2d[0], out_2d[1])).normalized()

    # Recessed dark glass backing
    back_c = center_xy - out_dir * (recess_depth * 0.55)
    add_oriented_box(bm, (back_c.x, back_c.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), width, recess_depth * 0.5, z_min, z_max, mat_idx=inner_mat)

    # Projecting sill & side jamb pilasters
    sill_c = center_xy + out_dir * 0.08
    add_oriented_box(bm, (sill_c.x, sill_c.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), width + 0.28, 0.26, z_min - 0.14, z_min + 0.06, mat_idx=trim_mat)
    for sx in (-1.0, 1.0):
        j_c = center_xy + t_dir * (sx * (hw + 0.12)) + out_dir * 0.05
        add_oriented_box(bm, (j_c.x, j_c.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), 0.24, 0.28, z_min, spring_z, mat_idx=trim_mat)

    # Smooth curved semicircular arch molding + spandrel fill + radiating voussoir blocks
    n_seg = 16
    prev_ring = None
    prev_sp = None
    for i in range(n_seg + 1):
        ang = math.pi * (1.0 - i / n_seg)
        cs, sn = math.cos(ang), math.sin(ang)
        x_in, z_in = cs * (hw * 0.92), spring_z + sn * (arch_r * 0.92)
        x_out, z_out = cs * (hw + 0.24), spring_z + sn * (arch_r + 0.26)

        p_inf = center_xy + t_dir * x_in + out_dir * 0.15
        p_outf = center_xy + t_dir * x_out + out_dir * 0.15
        p_outb = center_xy + t_dir * x_out - out_dir * (recess_depth * 0.85)
        p_inb = center_xy + t_dir * x_in - out_dir * (recess_depth * 0.85)

        curr_ring = [
            bm.verts.new((p_inf.x, p_inf.y, z_in)),
            bm.verts.new((p_outf.x, p_outf.y, z_out)),
            bm.verts.new((p_outb.x, p_outb.y, z_out)),
            bm.verts.new((p_inb.x, p_inb.y, z_in)),
        ]
        if prev_ring is not None:
            for k in range(4):
                nk = (k + 1) % 4
                try:
                    f = bm.faces.new((prev_ring[k], curr_ring[k], curr_ring[nk], prev_ring[nk]))
                    f.material_index = trim_mat
                    f.smooth = True
                except ValueError:
                    pass
        prev_ring = curr_ring

        z_top = z_max + 0.28
        p_sf = center_xy + t_dir * x_out + out_dir * 0.02
        p_tf = center_xy + t_dir * x_out + out_dir * 0.02
        p_tb = center_xy + t_dir * x_out - out_dir * (recess_depth * 0.88)
        p_sb = center_xy + t_dir * x_out - out_dir * (recess_depth * 0.88)
        curr_sp = [
            bm.verts.new((p_sf.x, p_sf.y, z_out)),
            bm.verts.new((p_tf.x, p_tf.y, z_top)),
            bm.verts.new((p_tb.x, p_tb.y, z_top)),
            bm.verts.new((p_sb.x, p_sb.y, z_out)),
        ]
        if prev_sp is not None:
            for k in range(4):
                nk = (k + 1) % 4
                try:
                    f = bm.faces.new((prev_sp[k], curr_sp[k], curr_sp[nk], prev_sp[nk]))
                    f.material_index = wall_mat
                except ValueError:
                    pass
        prev_sp = curr_sp

        if add_voussoirs and i % 2 == 1 and 0 < i < n_seg:
            vx = cs * (hw + 0.14)
            vz = spring_z + sn * (arch_r + 0.14)
            vp = center_xy + t_dir * vx + out_dir * 0.16
            add_oriented_box(bm, (vp.x, vp.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), 0.22, 0.14, vz - 0.12, vz + 0.12, mat_idx=trim_mat)

    # Interior arched window mullions, radial fanlight & transoms
    mul_c = center_xy - out_dir * (recess_depth * 0.32)
    for m_off in (-width * 0.22, 0.0, width * 0.22):
        mp = mul_c + t_dir * m_off
        z_top_m = spring_z + math.sqrt(max(0.0, arch_r * arch_r - m_off * m_off)) * 0.92
        add_oriented_box(bm, (mp.x, mp.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), 0.07, 0.16, z_min, z_top_m, mat_idx=frame_mat)
    for tr_z in (z_min + (spring_z - z_min) * 0.5, spring_z, spring_z + arch_r * 0.45):
        w_tr = width * 0.88 if tr_z <= spring_z else width * 0.68
        add_oriented_box(bm, (mul_c.x, mul_c.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), w_tr, 0.16, tr_z - 0.04, tr_z + 0.04, mat_idx=frame_mat)


def build_recessed_window_facade_along_edge(
    bm, p1_2d, p2_2d, out_normal_2d, z_base, z_top, n_floors, bay_target_width=2.9, recess_depth=0.45,
    wall_mat=0, trim_mat=1, glass_mat=3, frame_mat=4, ground_commercial=True
):
    edge_vec = p2_2d - p1_2d
    edge_len = edge_vec.length
    if edge_len < 1.2:
        return
    t_dir = edge_vec / edge_len
    n_dir = out_normal_2d.normalized()

    total_h = z_top - z_base
    floor_h = total_h / max(1, n_floors)
    n_bays = max(1, int(round(edge_len / bay_target_width)))
    bay_w = edge_len / n_bays
    pier_w = max(0.38, bay_w * 0.30)
    win_w = max(0.55, bay_w - pier_w)

    # Backing glass plane recessed at recess_depth * 0.65
    glass_center = (p1_2d + p2_2d) * 0.5 - n_dir * (recess_depth * 0.65)
    add_oriented_box(bm, (glass_center.x, glass_center.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), edge_len - 0.16, recess_depth * 0.45, z_base + 0.15, z_top - 0.25, mat_idx=glass_mat)

    # Vertical piers
    for b_idx in range(n_bays + 1):
        u = b_idx * bay_w
        pw = pier_w * 0.65 if b_idx in (0, n_bays) else pier_w
        u_clamped = max(pw * 0.5, min(edge_len - pw * 0.5, u))
        pc = p1_2d + t_dir * u_clamped - n_dir * (recess_depth * 0.40)
        add_oriented_box(bm, (pc.x, pc.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), pw, recess_depth, z_base, z_top, mat_idx=wall_mat)

    # Horizontal spandrels, sills, lintels & window mullions
    for f_idx in range(n_floors):
        fz0 = z_base + f_idx * floor_h
        fz1 = fz0 + floor_h
        sill_h = 0.45 if (f_idx == 0 and ground_commercial) else floor_h * 0.22
        lintel_h = floor_h * 0.18
        wz0 = fz0 + sill_h
        wz1 = fz1 - lintel_h

        sp_c = (p1_2d + p2_2d) * 0.5 - n_dir * (recess_depth * 0.40)
        add_oriented_box(bm, (sp_c.x, sp_c.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), edge_len, recess_depth, fz0, wz0, mat_idx=wall_mat)
        add_oriented_box(bm, (sp_c.x, sp_c.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), edge_len, recess_depth, wz1, fz1, mat_idx=wall_mat)

        if f_idx in (0, n_floors - 1):
            band_c = (p1_2d + p2_2d) * 0.5 + n_dir * 0.08
            add_oriented_box(bm, (band_c.x, band_c.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), edge_len + 0.16, 0.24, fz1 - 0.16, fz1 + 0.08, mat_idx=trim_mat)

        for b_idx in range(n_bays):
            bu = (b_idx + 0.5) * bay_w
            bc = p1_2d + t_dir * bu
            sill_c = bc + n_dir * 0.06
            add_oriented_box(bm, (sill_c.x, sill_c.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), win_w + 0.14, 0.22, wz0 - 0.10, wz0 + 0.04, mat_idx=trim_mat)
            lint_c = bc + n_dir * 0.06
            add_oriented_box(bm, (lint_c.x, lint_c.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), win_w + 0.18, 0.22, wz1 - 0.02, wz1 + 0.14, mat_idx=trim_mat)
            fr_c = bc - n_dir * (recess_depth * 0.35)
            add_oriented_box(bm, (fr_c.x, fr_c.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), 0.07, 0.14, wz0, wz1, mat_idx=frame_mat)
            add_oriented_box(bm, (fr_c.x, fr_c.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), win_w, 0.14, 0.5 * (wz0 + wz1) - 0.04, 0.5 * (wz0 + wz1) + 0.04, mat_idx=frame_mat)

    cornice_c = (p1_2d + p2_2d) * 0.5 + n_dir * 0.16
    add_oriented_box(bm, (cornice_c.x, cornice_c.y), (t_dir.x, t_dir.y), (n_dir.x, n_dir.y), edge_len + 0.36, 0.44, z_top - 0.32, z_top + 0.18, mat_idx=trim_mat)


def build_detailed_heritage_building(
    b_data, height, mat_wall, mat_trim, mat_roof, mat_window, mat_frame, collection, prefix="Bldg", add_mansard=False
):
    b_id = b_data["id"]
    pts_raw = b_data["coords_xy"]
    if len(pts_raw) > 1 and (Vector(pts_raw[0]) - Vector(pts_raw[-1])).length < 0.05:
        pts_raw = pts_raw[:-1]
    if len(pts_raw) < 3:
        return None

    mesh = bpy.data.meshes.new(f"{prefix}_{b_id}_Mesh")
    obj = bpy.data.objects.new(f"{prefix}_{b_id}", mesh)
    collection.objects.link(obj)
    for m in (mat_wall, mat_trim, mat_roof, mat_window, mat_frame):
        obj.data.materials.append(m)

    bm = bmesh.new()
    pts_2d = [Vector((p[0], p[1])) for p in pts_raw]
    area2 = sum(pts_2d[i].x * pts_2d[(i + 1) % len(pts_2d)].y - pts_2d[(i + 1) % len(pts_2d)].x * pts_2d[i].y for i in range(len(pts_2d)))
    if area2 < 0:
        pts_2d.reverse()

    inset_pts = inset_polygon_2d(pts_2d, inset_dist=0.80)
    v_bot = [bm.verts.new((p.x, p.y, 0.0)) for p in inset_pts]
    v_top = [bm.verts.new((p.x, p.y, height)) for p in inset_pts]
    try:
        bm.faces.new(v_bot[::-1]).material_index = 0
        bm.faces.new(v_top).material_index = 2
        for i in range(len(inset_pts)):
            ni = (i + 1) % len(inset_pts)
            bm.faces.new((v_bot[i], v_bot[ni], v_top[ni], v_top[i])).material_index = 0
    except ValueError:
        pass

    n_floors = max(2, int(round(height / 3.7)))
    for i in range(len(pts_2d)):
        p1, p2 = pts_2d[i], pts_2d[(i + 1) % len(pts_2d)]
        ev = p2 - p1
        if ev.length < 2.2:
            continue
        out_n = Vector((ev.y, -ev.x)).normalized()
        build_recessed_window_facade_along_edge(
            bm, p1, p2, out_n, 0.0, height, n_floors=n_floors, bay_target_width=2.9, recess_depth=0.45
        )

    if add_mansard:
        inset_m = inset_polygon_2d(pts_2d, inset_dist=1.35)
        vm_b = [bm.verts.new((p.x, p.y, height)) for p in pts_2d]
        vm_t = [bm.verts.new((p.x, p.y, height + 2.85)) for p in inset_m]
        try:
            bm.faces.new(vm_t).material_index = 2
            for i in range(len(pts_2d)):
                ni = (i + 1) % len(pts_2d)
                bm.faces.new((vm_b[i], vm_b[ni], vm_t[ni], vm_t[i])).material_index = 2
        except ValueError:
            pass

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.025, segments=2)
    return obj


def build_centaur_theatre_1082007381(b_data, palette, col_owned):
    """
    Hero Building #1 (`1082007381`): Centaur Theatre / Former Montreal Stock Exchange (453 Rue Saint-François-Xavier).
    Visible in Camera 3 (`Corner_SaintFrancoisXavier.jpg` Hero Right) and Camera 4 (`Rue_du_SaintSacrement.jpg` Midground Left).
    Features a 6-column Neoclassical Corinthian temple portico, 5-step limestone stylobate staircase,
    deep dark shadowed portico recess with 5 recessed bronze-and-glass entrance doorways & upper multi-pane windows,
    4 vertical Royal-Blue & Gold `CENTAUR THEATRE` fabric banners suspended between the columns,
    carved entablature with circular wreath medallions, rooftop flagpole, and 2-story North wing.
    """
    mesh = bpy.data.meshes.new("MTL_VM_0008_Centaur_Theatre_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0008_Centaur_Theatre_1082007381", mesh)
    col_owned.objects.link(obj)
    for m in [
        palette["Mat_MTL_WarmBuff_Limestone"],       # 0: Golden-buff Neoclassical cut limestone
        palette["Mat_MTL_PierreGrise_Limestone"],    # 1: Grey limestone plinth, steps & column bases
        palette["Mat_MTL_Portico_Deep_Shadow"],      # 2: Deep dark portico shadow wall & roof
        palette["Mat_MTL_Window_Glass_Dark"],        # 3: Recessed window glass
        palette["Mat_MTL_Window_Frame_Light"],       # 4: White window frames & flagpole
        palette["Mat_MTL_Centaur_Blue"],             # 5: Royal-blue Centaur Theatre banners & posters
        palette["Mat_MTL_Statue_Gold"],              # 6: Gold banner lettering & bronze plaques
        palette["Mat_MTL_CastIron_Black"],           # 7: Dark bronze entrance doors & ironwork
        palette["Mat_MTL_Warm_Wood"],                # 8: Warm wood accent
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()

    p_se = Vector((15.90, -146.20))
    p_nw = Vector((-3.60, -131.00))
    f_vec = p_nw - p_se
    f_len = f_vec.length
    f_dir = f_vec / f_len
    sw_out = Vector((-f_dir.y, f_dir.x))
    if sw_out.dot(Vector((-19.17, -163.70)) - p_se) < 0:
        sw_out = -sw_out
    ne_in = -sw_out

    z_stylobate = 1.15
    z_entab = 10.20
    z_top = 13.85

    # 1. Main Temple Building Volume set back behind the colonnade
    body_c = (p_se + p_nw) * 0.5 + ne_in * 11.8
    add_oriented_box(bm, (body_c.x, body_c.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), f_len, 17.0, 0.0, z_top, mat_idx=0)
    add_oriented_box(bm, (body_c.x, body_c.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), f_len - 1.2, 16.0, z_top, z_top + 0.35, mat_idx=2)

    # 2. Deep Shadowed Stone Portico Back-Wall (`z = z_stylobate..z_entab`, recessed 2.8m behind the columns!)
    portico_back_c = (p_se + p_nw) * 0.5 + ne_in * 2.55
    add_oriented_box(bm, (portico_back_c.x, portico_back_c.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), f_len - 5.2, 1.0, z_stylobate, z_entab, mat_idx=2)

    # Flanking solid limestone end-piers of the temple front (SE pier and NW pier)
    for side_s, pier_w in ((-1.0, 3.2), (1.0, 3.2)):
        pier_c = (p_se + p_nw) * 0.5 + f_dir * (side_s * (f_len * 0.5 - pier_w * 0.5)) + ne_in * 0.85
        add_oriented_box(bm, (pier_c.x, pier_c.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), pier_w, 2.2, 0.0, z_entab, mat_idx=0)
        add_oriented_box(bm, (pier_c.x, pier_c.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), pier_w + 0.25, 2.4, 0.0, z_stylobate, mat_idx=1)
        plq_c = pier_c + sw_out * 1.15
        if side_s < 0:
            add_oriented_box(bm, (plq_c.x, plq_c.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 0.92, 0.08, 1.8, 2.7, mat_idx=6)
        else:
            add_oriented_box(bm, (plq_c.x, plq_c.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 1.25, 0.12, 1.6, 3.2, mat_idx=7)
            add_oriented_box(bm, (plq_c.x, plq_c.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 1.05, 0.15, 1.8, 3.0, mat_idx=5)

    # 3. 5-Step Wide Limestone Stylobate Staircase across the Portico (`z = 0..1.15m`)
    stair_span = f_len - 5.4
    for s_i in range(5):
        sz1 = ((s_i + 1) / 5.0) * z_stylobate
        s_depth = 2.2 - s_i * 0.36
        sc = (p_se + p_nw) * 0.5 + sw_out * (0.25 + (4 - s_i) * 0.18)
        add_oriented_box(bm, (sc.x, sc.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), stair_span, s_depth, 0.0, sz1, mat_idx=1)

    # 4. 6 Monumental Fluted Corinthian Limestone Columns (`z = 1.15..10.2m`) + Recessed Portico Doors & Narrow Fabric Banners!
    col_span = f_len - 7.4
    for c_i in range(6):
        u_off = -col_span * 0.5 + (c_i / 5.0) * col_span
        col_xy = (p_se + p_nw) * 0.5 + f_dir * u_off + ne_in * 0.35
        add_oriented_box(bm, (col_xy.x, col_xy.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 1.28, 1.28, z_stylobate, z_stylobate + 0.45, mat_idx=1)
        ret_b = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20, radius1=0.62, radius2=0.52, depth=0.35, matrix=Matrix.Translation((col_xy.x, col_xy.y, z_stylobate + 0.62)))
        for v in ret_b["verts"]:
            for f in v.link_faces:
                f.material_index = 0
                f.smooth = True
        ret_sh = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=0.50, radius2=0.43, depth=7.65, matrix=Matrix.Translation((col_xy.x, col_xy.y, z_stylobate + 4.60)))
        for v in ret_sh["verts"]:
            for f in v.link_faces:
                f.material_index = 0
                f.smooth = True
        ret_cap = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20, radius1=0.44, radius2=0.66, depth=0.68, matrix=Matrix.Translation((col_xy.x, col_xy.y, z_entab - 0.54)))
        for v in ret_cap["verts"]:
            for f in v.link_faces:
                f.material_index = 0
                f.smooth = True
        add_oriented_box(bm, (col_xy.x, col_xy.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 1.36, 1.36, z_entab - 0.20, z_entab, mat_idx=0)

        # In each of the 5 bays between columns: build recessed dark-bronze theatrical entrance doors (`z = 1.15..4.15m`)
        # + upper multi-pane glass window (`z = 4.65..9.35m`) + slender hanging fabric theatre banner (`width = 0.78m`)!
        if c_i > 0:
            bay_u = u_off - (col_span / 10.0)
            door_p = (p_se + p_nw) * 0.5 + f_dir * bay_u + ne_in * 1.95
            add_oriented_box(bm, (door_p.x, door_p.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 1.75, 0.28, z_stylobate, 4.15, mat_idx=7)
            add_oriented_box(bm, (door_p.x + sw_out.x * 0.08, door_p.y + sw_out.y * 0.08), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 1.45, 0.22, z_stylobate + 0.25, 3.85, mat_idx=3)
            add_oriented_box(bm, (door_p.x, door_p.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 1.75, 0.28, 4.65, 9.35, mat_idx=3)
            for m_z in (4.25, 6.2, 7.8):
                add_oriented_box(bm, (door_p.x + sw_out.x * 0.12, door_p.y + sw_out.y * 0.12), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 1.85, 0.22, m_z - 0.10, m_z + 0.10, mat_idx=7)
            if 1 <= c_i <= 4:
                ban_xy = (p_se + p_nw) * 0.5 + f_dir * bay_u + ne_in * 0.78
                add_oriented_box(bm, (ban_xy.x, ban_xy.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 0.78, 0.06, 4.35, 8.65, mat_idx=5)
                add_oriented_box(bm, (ban_xy.x + sw_out.x * 0.02, ban_xy.y + sw_out.y * 0.02), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 0.62, 0.06, 5.15, 7.85, mat_idx=(6 if c_i <= 2 else 5))
                add_oriented_box(bm, (ban_xy.x, ban_xy.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 0.84, 0.10, 8.62, 8.70, mat_idx=7)
                add_oriented_box(bm, (ban_xy.x, ban_xy.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), 0.84, 0.10, 4.30, 4.38, mat_idx=7)

    # 5. Monumental Neoclassical Entablature, Dentil Cornice, Attic Frieze & Circular Medallions (`z = 10.2..13.85m`)
    ent_c = (p_se + p_nw) * 0.5 + ne_in * 0.65
    add_oriented_box(bm, (ent_c.x, ent_c.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), f_len + 0.4, 2.5, z_entab, z_top, mat_idx=0)
    for cz0, cz1, overhang in ((10.20, 10.48, 0.22), (11.35, 11.85, 0.58), (13.35, 13.85, 0.48)):
        cc = (p_se + p_nw) * 0.5 + sw_out * (0.60 + overhang * 0.5)
        add_oriented_box(bm, (cc.x, cc.y), (f_dir.x, f_dir.y), (sw_out.x, sw_out.y), f_len + 0.8, overhang + 0.4, cz0, cz1, mat_idx=1)

    rot_med = Euler((math.radians(90.0), 0.0, math.atan2(sw_out.y, sw_out.x) - math.pi * 0.5), 'XYZ').to_matrix().to_4x4()
    for side_s in (-1.0, 1.0):
        med_xy = (p_se + p_nw) * 0.5 + f_dir * (side_s * (f_len * 0.5 - 1.6)) + sw_out * 0.68
        ret_m = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20, radius1=0.68, radius2=0.62, depth=0.22, matrix=Matrix.Translation((med_xy.x, med_xy.y, 12.55)) @ rot_med)
        for v in ret_m["verts"]:
            for f in v.link_faces:
                f.material_index = 1
                f.smooth = True

    fp_xy = (p_se + p_nw) * 0.5 + ne_in * 2.5
    ret_fp = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=12, radius1=0.09, radius2=0.05, depth=10.8, matrix=Matrix.Translation((fp_xy.x, fp_xy.y, z_top + 5.4)))
    for v in ret_fp["verts"]:
        for f in v.link_faces:
            f.material_index = 4
            f.smooth = True

    # 6. North 2-Story Classical Wing (`(-3.6, -131.0)` to `(-9.8, -126.4)`, `z = 0..10.4m`) on the left of the colonnade in Camera 3!
    p_nw_far = Vector((-9.77, -126.44))
    w_vec = p_nw_far - p_nw
    w_len = w_vec.length
    w_dir = w_vec / w_len
    wing_c = (p_nw + p_nw_far) * 0.5 + ne_in * 6.8
    add_oriented_box(bm, (wing_c.x, wing_c.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), w_len + 0.4, 11.5, 0.0, 10.4, mat_idx=0)
    build_recessed_window_facade_along_edge(
        bm, p_nw, p_nw_far, sw_out, 0.0, 10.4, n_floors=2, bay_target_width=2.5, recess_depth=0.45,
        wall_mat=0, trim_mat=1, glass_mat=3, frame_mat=4, ground_commercial=True
    )

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.025, segments=2)
    return obj


def build_curb_market_1082007382(b_data, palette, col_owned):
    """
    Hero Building #2 (`1082007382`): Édifice Montreal Curb Market (`centroid [26.17, -143.55]`).
    Foreground Right Hero of Camera 4 (`Rue_du_SaintSacrement.jpg`) and Midground Right of Camera 1.
    Core wall is inset by `0.75m` so all 4 basement windows (`z = 0.25..1.22m`, with 3D vertical black iron security bars),
    all 3 first-story bronze-framed multi-pane windows (`z = 2.02..5.35m`), and all 3 second-story tall diamond/grid lattice
    windows (`z = 6.72..11.95m`) have true `0.48m` 3D depth!
    """
    mesh = bpy.data.meshes.new("MTL_VM_0008_Curb_Market_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0008_Curb_Market_1082007382", mesh)
    col_owned.objects.link(obj)
    for m in [
        palette["Mat_MTL_WarmBuff_Limestone"],       # 0: Golden-buff cut ashlar limestone
        palette["Mat_MTL_PierreGrise_Limestone"],    # 1: Grey limestone plinth, belt courses & cornice
        palette["Mat_MTL_Slate_Roof_Dark"],          # 2: Dark roof & basement shadow
        palette["Mat_MTL_Window_Glass_Dark"],        # 3: Specular dark reflective window glass
        palette["Mat_MTL_CastIron_Black"],           # 4: Dark bronze window frames, lattice muntins & iron bars
        palette["Mat_MTL_Verdigris_Copper"],         # 5: Green verdigris copper pediment cap
        palette["Mat_MTL_Warm_Wood"],                # 6: Interior warm wood glimpse
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()
    p_nw = Vector((15.90, -146.20))
    p_sw = Vector((28.40, -155.70))
    p_se = Vector((41.80, -139.70))
    p_ne = Vector((28.90, -130.00))

    sw_vec = p_sw - p_nw
    sw_len = sw_vec.length
    sw_dir = sw_vec / sw_len
    sw_out = Vector((-sw_dir.y, sw_dir.x))
    if sw_out.dot(Vector((21.81, -154.62)) - p_nw) < 0:
        sw_out = -sw_out

    z_top = 14.40
    c_xy = (p_nw + p_sw + p_se + p_ne) * 0.25
    depth_ne = (p_se - p_sw).length

    # 1. Core Building Mass INSET by 0.75m so all basement & upper window recesses are 100% open!
    add_oriented_box(bm, (c_xy.x, c_xy.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), sw_len - 1.50, depth_ne - 1.50, 0.0, z_top, mat_idx=0)

    # Backing dark glass / shadow plane for the SW facade (`-sw_out * 0.45m`)
    gl_sw = (p_nw + p_sw) * 0.5 - sw_out * 0.42
    add_oriented_box(bm, (gl_sw.x, gl_sw.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), sw_len - 0.4, 0.25, 0.20, 1.30, mat_idx=2)
    add_oriented_box(bm, (gl_sw.x, gl_sw.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), sw_len - 0.4, 0.25, 1.95, 12.20, mat_idx=3)

    # Flush horizontal wall bands on the SW facade:
    # - Plinth base below basement windows (`z = 0.0..0.28m`) and plinth lintel above basement windows (`z = 1.18..1.55m`)
    # - Spandrel band between 1st & 2nd floor windows (`z = 5.35..6.72m`) and frieze below cornice (`z = 11.95..14.40m`)
    sw_mid = (p_nw + p_sw) * 0.5 - sw_out * 0.18
    add_oriented_box(bm, (sw_mid.x, sw_mid.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), sw_len, 0.42, 0.0, 0.28, mat_idx=1)
    add_oriented_box(bm, (sw_mid.x, sw_mid.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), sw_len, 0.42, 1.18, 2.02, mat_idx=1)
    add_oriented_box(bm, (sw_mid.x, sw_mid.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), sw_len, 0.42, 5.35, 6.72, mat_idx=0)
    add_oriented_box(bm, (sw_mid.x, sw_mid.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), sw_len, 0.42, 11.95, z_top, mat_idx=0)

    # Moulded projecting limestone belt courses & dentil cornice
    for bz0, bz1, b_proj in ((1.42, 1.62, 0.14), (1.84, 2.04, 0.18), (6.52, 6.72, 0.12), (13.15, 13.55, 0.35), (13.85, 14.40, 0.58)):
        bc = (p_nw + p_sw) * 0.5 + sw_out * (b_proj * 0.5)
        add_oriented_box(bm, (bc.x, bc.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), sw_len + 0.4, b_proj + 0.2, bz0, bz1, mat_idx=1)

    # Vertical piers along the SW facade (grey limestone on plinth `z = 0..1.55m`, warm-buff ashlar above `z = 1.55..14.40m`)
    for p_u, p_w in ((0.45, 0.90), (3.55, 1.55), (7.35, 1.75), (11.35, 1.75), (14.95, 1.45)):
        pxy = p_nw + sw_dir * p_u - sw_out * 0.18
        add_oriented_box(bm, (pxy.x, pxy.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), p_w, 0.44, 0.0, 1.55, mat_idx=1)
        add_oriented_box(bm, (pxy.x, pxy.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), p_w, 0.44, 1.55, z_top, mat_idx=0)

    # Leftmost Bay (`u = 2.00m` from `p_nw`): Projecting Classical Pedimented Doorway with Verdigris Copper Roof (`z = 0.0..5.68m`)!
    door_xy = p_nw + sw_dir * 2.00
    for pil_s in (-0.92, 0.92):
        pil_p = door_xy + sw_dir * pil_s + sw_out * 0.12
        add_oriented_box(bm, (pil_p.x, pil_p.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 0.42, 0.42, 0.0, 4.92, mat_idx=1)
    add_oriented_box(bm, (door_xy.x + sw_out.x * 0.14, door_xy.y + sw_out.y * 0.14), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 2.38, 0.46, 4.45, 4.95, mat_idx=1)
    add_oriented_box(bm, (door_xy.x - sw_out.x * 0.22, door_xy.y - sw_out.y * 0.22), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 1.38, 0.35, 0.15, 4.45, mat_idx=4)
    # Pitched triangular pediment + green verdigris copper cap (`z = 4.92..5.72m`)
    ped_l = door_xy - sw_dir * 1.35
    ped_r = door_xy + sw_dir * 1.35
    v_pl_f = bm.verts.new((ped_l.x + sw_out.x * 0.42, ped_l.y + sw_out.y * 0.42, 4.92))
    v_pr_f = bm.verts.new((ped_r.x + sw_out.x * 0.42, ped_r.y + sw_out.y * 0.42, 4.92))
    v_pm_f = bm.verts.new((door_xy.x + sw_out.x * 0.42, door_xy.y + sw_out.y * 0.42, 5.72))
    v_pl_b = bm.verts.new((ped_l.x - sw_out.x * 0.10, ped_l.y - sw_out.y * 0.10, 4.92))
    v_pr_b = bm.verts.new((ped_r.x - sw_out.x * 0.10, ped_r.y - sw_out.y * 0.10, 4.92))
    v_pm_b = bm.verts.new((door_xy.x - sw_out.x * 0.10, door_xy.y - sw_out.y * 0.10, 5.72))
    try:
        bm.faces.new((v_pl_f, v_pr_f, v_pm_f)).material_index = 1
        bm.faces.new((v_pl_f, v_pm_f, v_pm_b, v_pl_b)).material_index = 5
        bm.faces.new((v_pm_f, v_pr_f, v_pr_b, v_pm_b)).material_index = 5
    except ValueError:
        pass
    # Fill wall above doorway (`z = 4.95..14.40m`) + carved circular stone wreath medallion at z=10.5m
    add_oriented_box(bm, (door_xy.x - sw_out.x * 0.18, door_xy.y - sw_out.y * 0.18), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 2.1, 0.44, 4.95, z_top, mat_idx=0)
    rot_w = Euler((math.radians(90.0), 0.0, math.atan2(sw_out.y, sw_out.x) - math.pi * 0.5), 'XYZ').to_matrix().to_4x4()
    ret_wr = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20, radius1=0.58, radius2=0.52, depth=0.22, matrix=Matrix.Translation((door_xy.x + sw_out.x * 0.08, door_xy.y + sw_out.y * 0.08, 10.45)) @ rot_w)
    for v in ret_wr["verts"]:
        for f in v.link_faces:
            f.material_index = 1
            f.smooth = True

    # 3 Main Window Bays along the SW Facade (`u = 5.45m, 9.35m, 13.25m` from `p_nw`):
    for u_off in (5.45, 9.35, 13.25):
        w_xy = p_nw + sw_dir * u_off
        # 1. Deeply recessed basement window (`z = 0.28..1.18m`) with 3D vertical black iron security bars!
        for bar_i in range(-4, 5):
            bar_p = w_xy + sw_dir * (bar_i * 0.20) - sw_out * 0.12
            add_oriented_box(bm, (bar_p.x, bar_p.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 0.04, 0.06, 0.28, 1.18, mat_idx=4)
        add_oriented_box(bm, (w_xy.x - sw_out.x * 0.12, w_xy.y - sw_out.y * 0.12), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 2.0, 0.06, 0.72, 0.77, mat_idx=4)

        # 2. 1st Story Deeply Recessed Window (`z = 2.02..5.35m`) with dark bronze frame, mullions, transom & warm interior accent
        for m_s in (-0.98, 0.0, 0.98):
            mp = w_xy + sw_dir * m_s - sw_out * 0.22
            add_oriented_box(bm, (mp.x, mp.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 0.08, 0.18, 2.02, 5.35, mat_idx=4)
        for tr_z in (2.06, 3.85, 5.30):
            add_oriented_box(bm, (w_xy.x - sw_out.x * 0.22, w_xy.y - sw_out.y * 0.22), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 2.05, 0.18, tr_z - 0.05, tr_z + 0.05, mat_idx=4)
        # Warm interior wood venetian blind / wall accent inside the window
        add_oriented_box(bm, (w_xy.x - sw_out.x * 0.52, w_xy.y - sw_out.y * 0.52), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 1.95, 0.10, 2.10, 5.25, mat_idx=6)

        # 3. 2nd Story Tall Recessed Window (`z = 6.72..11.95m`) with 3D geometric diamond/grid lattice muntin grille!
        add_oriented_box(bm, (w_xy.x + sw_out.x * 0.12, w_xy.y + sw_out.y * 0.12), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 2.25, 0.28, 6.50, 6.72, mat_idx=1)
        for m_s in (-0.75, -0.38, 0.0, 0.38, 0.75):
            mp = w_xy + sw_dir * m_s - sw_out * 0.22
            add_oriented_box(bm, (mp.x, mp.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 0.05, 0.14, 6.72, 11.95, mat_idx=4)
        for tr_z in (7.3, 7.9, 8.5, 9.1, 9.7, 10.3, 10.9, 11.5):
            add_oriented_box(bm, (w_xy.x - sw_out.x * 0.22, w_xy.y - sw_out.y * 0.22), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 2.05, 0.14, tr_z - 0.03, tr_z + 0.03, mat_idx=4)

    # 3. SE Facade along Rue Saint-Jean (`p_sw` to `p_se`, visible in Camera 1 Midground Right!)
    se_dir = (p_se - p_sw).normalized()
    se_out = Vector((se_dir.y, -se_dir.x))
    build_recessed_window_facade_along_edge(
        bm, p_sw, p_se, se_out, 0.0, z_top, n_floors=2, bay_target_width=3.4, recess_depth=0.45,
        wall_mat=0, trim_mat=1, glass_mat=3, frame_mat=4, ground_commercial=False
    )

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.025, segments=2)
    return obj


def build_modavie_corner_1082007383(b_data, palette, col_owned):
    """
    Hero Building #3 (`1082007383`): 200 Rue Saint-Paul Ouest / Modavie Corner Building (`centroid [52.38, -154.19]`).
    Hero Right Foreground of Camera 1 (`Rue_SaintPaul_Cobblestone_East.jpg`) and Background Center-Right of Camera 2.
    Core polygon is inset by `0.85m` so all ground-floor bistro windows, arched wooden double doors, and upper-floor
    windows have true `0.48m` 3D depth, solid 3D wedge canvas awnings (with triangular side valences and front drop flap),
    dark forest-green 6-pane 3D mullions, and wrought-iron juliet balcony bar grilles!
    """
    mesh = bpy.data.meshes.new("MTL_VM_0008_Modavie_1082007383_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0008_Modavie_1082007383", mesh)
    col_owned.objects.link(obj)
    for m in [
        palette["Mat_MTL_PierreGrise_Limestone"],    # 0: Coursed Montreal grey limestone walls & pilasters
        palette["Mat_MTL_WarmBuff_Limestone"],       # 1: Carved stone spandrels, cornices & keystones
        palette["Mat_MTL_Slate_Roof_Dark"],          # 2: Steep Mansard roof & solid 3D wedge bistro awnings
        palette["Mat_MTL_Window_Glass_Dark"],        # 3: Specular dark reflective window glass
        palette["Mat_MTL_Heritage_Green"],           # 4: Heritage dark forest-green window frames, mullions & dormers
        palette["Mat_MTL_Warm_Wood"],                # 5: Warm honey-oak arched double-leaf entrance doors
        palette["Mat_MTL_Window_Frame_Light"],       # 6: White painted shopfront wainscot panels
        palette["Mat_MTL_CastIron_Black"],           # 7: Wrought-iron juliet balcony bars, coach lanterns & signs
        palette["Mat_MTL_Portal_Warm_Glow"],         # 8: Warm bistro interior & coach lantern glow
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()
    pts_2d = [Vector((p[0], p[1])) for p in b_data["coords_xy"][:-1]]
    area2 = sum(pts_2d[i].x * pts_2d[(i + 1) % len(pts_2d)].y - pts_2d[(i + 1) % len(pts_2d)].x * pts_2d[i].y for i in range(len(pts_2d)))
    if area2 < 0:
        pts_2d.reverse()

    z_eave = 15.20
    z_mansard = 18.65
    centroid = sum(pts_2d, Vector((0.0, 0.0))) / len(pts_2d)

    # Inset core mass by 0.85m perpendicular to every edge so window recesses are never blocked!
    inset_pts = inset_polygon_2d(pts_2d, inset_dist=0.85)
    v_bot = [bm.verts.new((p.x, p.y, 0.0)) for p in inset_pts]
    v_top = [bm.verts.new((p.x, p.y, z_eave)) for p in inset_pts]
    try:
        bm.faces.new(v_bot[::-1]).material_index = 0
        for i in range(len(inset_pts)):
            ni = (i + 1) % len(inset_pts)
            bm.faces.new((v_bot[i], v_bot[ni], v_top[ni], v_top[i])).material_index = 0
    except ValueError:
        pass

    # Steeply pitched Mansard Roof (`z = 15.20..18.65m`)
    inset_m = inset_polygon_2d(pts_2d, inset_dist=1.45)
    vm_b = [bm.verts.new((p.x, p.y, z_eave)) for p in pts_2d]
    vm_t = [bm.verts.new((p.x, p.y, z_mansard)) for p in inset_m]
    try:
        bm.faces.new(vm_t).material_index = 2
        for i in range(len(pts_2d)):
            ni = (i + 1) % len(pts_2d)
            bm.faces.new((vm_b[i], vm_b[ni], vm_t[ni], vm_t[i])).material_index = 2
    except ValueError:
        pass

    p_corner = Vector((50.02, -172.62))
    p_nw = Vector((28.40, -155.70))
    p_ne = Vector((67.20, -146.70))

    for f_p1, f_p2, n_bays, has_pediment in (
        (p_corner, p_nw, 7, True),   # West facade along Rue Saint-Jean (Camera 1 Right Foreground Hero!)
        (p_ne, p_corner, 6, False),  # South facade along Rue Saint-Paul Ouest (Camera 2 Background!)
    ):
        ev = f_p2 - f_p1
        elen = ev.length
        t_dir = ev / elen
        out_n = Vector((t_dir.y, -t_dir.x)).normalized()
        if out_n.dot(centroid - (f_p1 + f_p2) * 0.5) > 0:
            out_n = -out_n
        bay_w = elen / n_bays

        # Continuous recessed dark glass backing plane (`-out_n * 0.42m`)
        gl_c = (f_p1 + f_p2) * 0.5 - out_n * 0.42
        add_oriented_box(bm, (gl_c.x, gl_c.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), elen - 0.3, 0.24, 0.25, z_eave - 0.2, mat_idx=3)

        # Horizontal limestone spandrel bands & projecting cornices
        for sz0, sz1 in ((3.75, 5.15), (7.65, 8.55), (11.05, 11.95), (14.35, z_eave)):
            sc = (f_p1 + f_p2) * 0.5 - out_n * 0.18
            add_oriented_box(bm, (sc.x, sc.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), elen, 0.42, sz0, sz1, mat_idx=0)
        for cz0, cz1, c_proj in ((4.35, 4.68, 0.28), (14.95, 15.35, 0.42)):
            cc = (f_p1 + f_p2) * 0.5 + out_n * (c_proj * 0.5)
            add_oriented_box(bm, (cc.x, cc.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), elen + 0.35, c_proj + 0.25, cz0, cz1, mat_idx=1)

        # Vertical rusticated ground-floor piers & upper limestone pilasters
        for b_i in range(n_bays + 1):
            pxy = f_p1 + t_dir * (b_i * bay_w)
            add_oriented_box(bm, (pxy.x, pxy.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.78, 0.52, 0.0, 4.45, mat_idx=0)
            for rz in (0.6, 1.4, 2.2, 3.0, 3.8):
                add_oriented_box(bm, (pxy.x + out_n.x * 0.06, pxy.y + out_n.y * 0.06), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.84, 0.48, rz, rz + 0.42, mat_idx=1)
            add_oriented_box(bm, (pxy.x, pxy.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.64, 0.44, 4.45, z_eave, mat_idx=0)
            if b_i in (1, 2, 4, 6):
                l_xy = pxy + out_n * 0.34
                add_oriented_box(bm, (l_xy.x, l_xy.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.16, 0.20, 2.75, 3.12, mat_idx=7)

        for b_i in range(n_bays):
            b_xy = f_p1 + t_dir * ((b_i + 0.5) * bay_w)
            win_w = bay_w - 0.80

            # Ground floor (`z = 0..4.35m`): alternate warm wood arched double doors (bays 1, 3) and bistro windows with 3D wedge awnings!
            if b_i in (1, 3):
                # Recessed warm honey-oak arched double doorway + lower kick panels + stiles + arched fanlight transom (`Rue_SaintPaul_Cobblestone_East.jpg`!)
                step_c = b_xy - out_n * 0.05
                add_oriented_box(bm, (step_c.x, step_c.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w + 0.1, 0.45, 0.0, 0.22, mat_idx=0)
                # Outer wood frame & lower solid wood kick-panel (`z = 0.22..1.05m`)
                add_oriented_box(bm, (b_xy.x - out_n.x * 0.22, b_xy.y - out_n.y * 0.22), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w, 0.18, 0.22, 1.05, mat_idx=5)
                add_oriented_box(bm, (b_xy.x - out_n.x * 0.22, b_xy.y - out_n.y * 0.22), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w, 0.18, 2.65, 2.88, mat_idx=5)
                add_oriented_box(bm, (b_xy.x - out_n.x * 0.22, b_xy.y - out_n.y * 0.22), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w, 0.18, 3.55, 3.78, mat_idx=5)
                for st_s in (-0.46, 0.0, 0.46):
                    st_p = b_xy + t_dir * (st_s * win_w) - out_n * 0.22
                    add_oriented_box(bm, (st_p.x, st_p.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.16, 0.18, 0.22, 3.75, mat_idx=5)
                # Transom vertical wood muntins (`z = 2.85..3.65m`)
                for tm_s in (-0.25, 0.25):
                    tm_p = b_xy + t_dir * (tm_s * win_w) - out_n * 0.22
                    add_oriented_box(bm, (tm_p.x, tm_p.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.06, 0.16, 2.85, 3.65, mat_idx=5)
                # Carved keystone above doorway arch
                ks_xy = b_xy + out_n * 0.14
                add_oriented_box(bm, (ks_xy.x, ks_xy.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.34, 0.26, 3.68, 4.22, mat_idx=1)
                if b_i == 3 and has_pediment:
                    sg_xy = b_xy - t_dir * (bay_w * 0.45) + out_n * 0.65
                    add_oriented_box(bm, (sg_xy.x, sg_xy.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.08, 0.78, 3.45, 4.05, mat_idx=7)
                    add_oriented_box(bm, (sg_xy.x, sg_xy.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.12, 0.55, 3.55, 3.92, mat_idx=8)
            else:
                # White painted wainscot stallboard (`z = 0.15..1.18m`) + dark-green framed bistro window + SOLID 3D WEDGE AWNING!
                w_c = b_xy - out_n * 0.06
                add_oriented_box(bm, (w_c.x, w_c.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w, 0.28, 0.0, 1.18, mat_idx=6)
                for m_s in (-0.48, 0.0, 0.48):
                    mp = b_xy + t_dir * (m_s * win_w) - out_n * 0.20
                    add_oriented_box(bm, (mp.x, mp.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.08, 0.16, 1.18, 3.65, mat_idx=4)
                add_oriented_box(bm, (b_xy.x - out_n.x * 0.16, b_xy.y - out_n.y * 0.16), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w + 0.08, 0.22, 1.14, 1.26, mat_idx=4)

                # Solid 3D Wedge Canvas Bistro Awning (`z = 3.05..3.98m`, projecting `0.95m` outward with triangular side cheeks & drop flap!)
                aw_l = b_xy - t_dir * (win_w * 0.49)
                aw_r = b_xy + t_dir * (win_w * 0.49)
                vt_l = bm.verts.new((aw_l.x + out_n.x * 0.04, aw_l.y + out_n.y * 0.04, 3.98))
                vt_r = bm.verts.new((aw_r.x + out_n.x * 0.04, aw_r.y + out_n.y * 0.04, 3.98))
                vb_l = bm.verts.new((aw_l.x + out_n.x * 0.04, aw_l.y + out_n.y * 0.04, 3.22))
                vb_r = bm.verts.new((aw_r.x + out_n.x * 0.04, aw_r.y + out_n.y * 0.04, 3.22))
                vf_l = bm.verts.new((aw_l.x + out_n.x * 0.96, aw_l.y + out_n.y * 0.96, 3.22))
                vf_r = bm.verts.new((aw_r.x + out_n.x * 0.96, aw_r.y + out_n.y * 0.96, 3.22))
                try:
                    bm.faces.new((vt_l, vt_r, vf_r, vf_l)).material_index = 2
                    bm.faces.new((vb_l, vf_l, vf_r, vb_r)).material_index = 2
                    bm.faces.new((vt_l, vf_l, vb_l)).material_index = 2
                    bm.faces.new((vt_r, vb_r, vf_r)).material_index = 2
                except ValueError:
                    pass
                # Front drop valance flap (`z = 3.02..3.24m`)
                flap_c = b_xy + out_n * 0.94
                add_oriented_box(bm, (flap_c.x, flap_c.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w * 0.98, 0.05, 3.02, 3.24, mat_idx=2)

            # Upper 3 Floors (`Floors 2, 3, 4`: `z = 5.15..7.65m`, `8.55..11.05m`, `11.95..14.35m`)
            for fz0, fz1 in ((5.15, 7.65), (8.55, 11.05), (11.95, 14.35)):
                # Heritage dark-green 6-pane window sash, frame & mullions (`Mat_MTL_Heritage_Green`, `mat_idx = 4`)
                fr_p = b_xy - out_n * 0.24
                for m_s in (-0.46, 0.0, 0.46):
                    mp = fr_p + t_dir * (m_s * win_w * 0.85)
                    add_oriented_box(bm, (mp.x, mp.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.08, 0.16, fz0, fz1, mat_idx=4)
                for tr_frac in (0.04, 0.52, 0.96):
                    tz = fz0 + (fz1 - fz0) * tr_frac
                    add_oriented_box(bm, (fr_p.x, fr_p.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w * 0.88, 0.16, tz - 0.04, tz + 0.04, mat_idx=4)
                # Projecting stone sill + carved spandrel panel below window
                sill_p = b_xy + out_n * 0.08
                add_oriented_box(bm, (sill_p.x, sill_p.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w * 0.92, 0.24, fz0 - 0.12, fz0 + 0.04, mat_idx=1)
                sp_p = b_xy - out_n * 0.06
                add_oriented_box(bm, (sp_p.x, sp_p.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w * 0.78, 0.24, fz0 - 0.68, fz0 - 0.16, mat_idx=1)
                # Wrought-iron Juliet balcony grille (`3D vertical iron bars + top/bottom rail`, NOT a solid block!)
                rl_p = b_xy + out_n * 0.06
                add_oriented_box(bm, (rl_p.x, rl_p.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), win_w * 0.82, 0.05, fz0 + 0.56, fz0 + 0.62, mat_idx=7)
                for jb_i in range(-3, 4):
                    jbp = rl_p + t_dir * (jb_i * 0.24)
                    add_oriented_box(bm, (jbp.x, jbp.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.035, 0.04, fz0 + 0.04, fz0 + 0.58, mat_idx=7)

            # Mansard Roof Gabled Dormer Window (`z = 15.35..17.45m`) on every bay (and central triangular stone pediment on bay 4!)
            if has_pediment and b_i == 4:
                ped_c = b_xy - out_n * 0.12
                add_oriented_box(bm, (ped_c.x, ped_c.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), bay_w * 0.95, 0.65, z_eave, z_eave + 2.45, mat_idx=0)
                add_oriented_box(bm, (ped_c.x + out_n.x * 0.18, ped_c.y + out_n.y * 0.18), (t_dir.x, t_dir.y), (out_n.x, out_n.y), bay_w * 1.05, 0.35, z_eave + 2.35, z_eave + 2.75, mat_idx=1)
            else:
                dm_c = b_xy - out_n * 0.45
                add_oriented_box(bm, (dm_c.x, dm_c.y), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 1.25, 0.95, z_eave + 0.15, z_eave + 2.05, mat_idx=4)
                add_oriented_box(bm, (dm_c.x + out_n.x * 0.42, dm_c.y + out_n.y * 0.42), (t_dir.x, t_dir.y), (out_n.x, out_n.y), 0.95, 0.20, z_eave + 0.30, z_eave + 1.85, mat_idx=3)

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.025, segments=2)
    return obj


def build_exchange_beaux_arts_339893930(b_data, palette, col_owned):
    """
    Hero Building #4 (`339893930`): Historic "EXCHANGE" Beaux-Arts Limestone Building (`centroid [7.96, -191.46]`).
    Hero Left Foreground of Camera 2 (`Rue_SaintPaul_Cobblestone_West.jpg` at `[22.55, -204.75]`).
    Core polygon is inset by `1.65m` so the `1.35m`-deep grand entrance vestibule at `b_i == 2` (`(19.0, -200.8)`,
    directly in the left foreground of Camera 2!) and all ground/upper windows are deeply recessed with zero core-wall bleeding!
    """
    mesh = bpy.data.meshes.new("MTL_VM_0008_Exchange_339893930_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0008_Exchange_339893930", mesh)
    col_owned.objects.link(obj)
    for m in [
        palette["Mat_MTL_PierreGrise_Limestone"],    # 0: Cut Montreal grey limestone
        palette["Mat_MTL_WarmBuff_Limestone"],       # 1: Carved brackets, voussoirs & column capitals
        palette["Mat_MTL_Slate_Roof_Dark"],          # 2: Dark roof & vestibule shadow
        palette["Mat_MTL_Window_Glass_Dark"],        # 3: Specular dark reflective window glass
        palette["Mat_MTL_Window_Frame_Light"],       # 4: Crisp white multi-pane arched window muntins
        palette["Mat_MTL_CastIron_Black"],           # 5: Black paneled entrance doors & wrought-iron balcony balusters
        palette["Mat_MTL_Portal_Warm_Glow"],         # 6: Warm glowing crystal chandelier inside vestibule
        palette["Mat_MTL_BN_Red"],                   # 7: Maroon bronze heritage plaque on pier
        palette["Mat_MTL_Light_Granite_Steps"],      # 8: Light-grey granite entrance steps
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()
    pts_2d = [Vector((p[0], p[1])) for p in b_data["coords_xy"][:-1]]
    area2 = sum(pts_2d[i].x * pts_2d[(i + 1) % len(pts_2d)].y - pts_2d[(i + 1) % len(pts_2d)].x * pts_2d[i].y for i in range(len(pts_2d)))
    if area2 < 0:
        pts_2d.reverse()

    z_top = 17.20
    # Inset core polygon by 1.65m perpendicular to every edge so the 1.35m entrance vestibule & windows are 100% open!
    inset_pts = inset_polygon_2d(pts_2d, inset_dist=1.65)
    v_bot = [bm.verts.new((p.x, p.y, 0.0)) for p in inset_pts]
    v_top = [bm.verts.new((p.x, p.y, z_top)) for p in inset_pts]
    try:
        bm.faces.new(v_bot[::-1]).material_index = 0
        bm.faces.new(v_top).material_index = 2
        for i in range(len(inset_pts)):
            ni = (i + 1) % len(inset_pts)
            bm.faces.new((v_bot[i], v_bot[ni], v_top[ni], v_top[i])).material_index = 0
    except ValueError:
        pass

    p_sw = Vector((11.50, -210.30))
    p_ne = Vector((26.50, -191.30))
    f_vec = p_ne - p_sw
    f_len = f_vec.length
    f_dir = f_vec / f_len
    se_out = Vector((f_dir.y, -f_dir.x)).normalized()
    if se_out.dot(Vector((22.55, -204.75)) - p_sw) < 0:
        se_out = -se_out
    nw_in = -se_out

    n_bays = 5
    bay_w = f_len / n_bays

    # Horizontal spandrel bands & projecting cornices
    for sz0, sz1 in ((3.95, 5.15), (9.65, 10.55), (14.15, 14.80), (16.55, z_top)):
        sc = (p_sw + p_ne) * 0.5 + nw_in * 0.25
        add_oriented_box(bm, (sc.x, sc.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), f_len, 0.50, sz0, sz1, mat_idx=0)
    for cz0, cz1, c_proj in ((4.42, 4.78, 0.34), (10.05, 10.38, 0.28), (14.35, 14.62, 0.24), (16.75, 17.30, 0.55)):
        cc = (p_sw + p_ne) * 0.5 + se_out * (c_proj * 0.5)
        add_oriented_box(bm, (cc.x, cc.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), f_len + 0.4, c_proj + 0.3, cz0, cz1, mat_idx=1)

    # Rusticated Ground-Floor Limestone Piers (`z = 0..4.55m`) with Banded Rustication Courses!
    for b_i in range(n_bays + 1):
        pxy = p_sw + f_dir * (b_i * bay_w)
        add_oriented_box(bm, (pxy.x, pxy.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 1.15, 0.65, 0.0, z_top, mat_idx=0)
        for rz in (0.45, 1.15, 1.85, 2.55, 3.25, 3.95, 5.2, 6.0, 6.8, 7.6, 8.4):
            rp = pxy + se_out * 0.10
            add_oriented_box(bm, (rp.x, rp.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 1.25, 0.52, rz, rz + 0.42, mat_idx=1)

    for b_i in range(n_bays):
        b_xy = p_sw + f_dir * ((b_i + 0.5) * bay_w)
        win_w = bay_w - 1.20

        if b_i == 2:
            # HERO PORTAL BAY (`b_i == 2` at `(19.0, -200.8)`, directly in the Left Foreground of Camera 2 `Rue_SaintPaul_Cobblestone_West.jpg`!):
            # 1. Deeply recessed vestibule (`1.35m` deep) + 3 light-grey granite entrance steps (`z = 0..0.54m`)
            for side_w in (-1.0, 1.0):
                vw = b_xy + f_dir * (side_w * (win_w * 0.5)) + nw_in * 0.68
                add_oriented_box(bm, (vw.x, vw.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 0.16, 1.35, 0.0, 4.35, mat_idx=0)
            ceil_c = b_xy + nw_in * 0.68
            add_oriented_box(bm, (ceil_c.x, ceil_c.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w, 1.35, 4.15, 4.45, mat_idx=2)
            for s_i in range(3):
                sz1 = ((s_i + 1) / 3.0) * 0.54
                sc = b_xy + nw_in * (s_i * 0.34 + 0.18)
                add_oriented_box(bm, (sc.x, sc.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w, 0.38, 0.0, sz1, mat_idx=8)
            # Black paneled double doors + sidelights + glass panes inside vestibule (`nw_in * 1.15m`)
            door_c = b_xy + nw_in * 1.15
            add_oriented_box(bm, (door_c.x, door_c.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w, 0.22, 0.54, 4.20, mat_idx=5)
            for dp_s in (-0.22, 0.22):
                d_glass = door_c + f_dir * (dp_s * win_w) + se_out * 0.06
                add_oriented_box(bm, (d_glass.x, d_glass.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w * 0.34, 0.18, 1.35, 3.65, mat_idx=3)
            # Warm Glowing Crystal Chandelier suspended inside the vestibule ceiling at z=3.55m!
            ch_xy = b_xy + nw_in * 0.55
            ret_ch = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=14, radius1=0.42, radius2=0.10, depth=0.62, matrix=Matrix.Translation((ch_xy.x, ch_xy.y, 3.55)))
            for v in ret_ch["verts"]:
                for f in v.link_faces:
                    f.material_index = 6

            # Maroon bronze heritage plaque on the rusticated pier immediately to the right of the portal (`z = 1.35..2.15m`)
            plq_xy = b_xy + f_dir * (bay_w * 0.50) + se_out * 0.38
            add_oriented_box(bm, (plq_xy.x, plq_xy.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 0.58, 0.10, 1.35, 2.15, mat_idx=7)

            # Projecting Carved Stone Balcony + Stepped Console Brackets (`z = 3.45..4.98m`)
            bal_c = b_xy + se_out * 0.48
            add_oriented_box(bm, (bal_c.x, bal_c.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), bay_w + 0.55, 1.05, 4.42, 4.98, mat_idx=1)
            for br_s in (-0.44, 0.44):
                br_p = b_xy + f_dir * (br_s * bay_w) + se_out * 0.42
                add_oriented_box(bm, (br_p.x, br_p.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 0.52, 0.72, 3.85, 4.45, mat_idx=1)
                add_oriented_box(bm, (br_p.x - se_out.x * 0.10, br_p.y - se_out.y * 0.10), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 0.46, 0.48, 3.40, 3.88, mat_idx=1)

            # Ornate Black Wrought-Iron Balcony Railing (`z = 4.98..6.12m`, built with 3D vertical iron balusters & curved rails!)
            rail_c = b_xy + se_out * 0.88
            add_oriented_box(bm, (rail_c.x, rail_c.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w + 0.35, 0.08, 6.02, 6.12, mat_idx=5)
            add_oriented_box(bm, (rail_c.x, rail_c.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w + 0.35, 0.08, 5.02, 5.10, mat_idx=5)
            for bl_i in range(-6, 7):
                bl_p = rail_c + f_dir * (bl_i * (win_w / 12.0))
                add_oriented_box(bm, (bl_p.x, bl_p.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 0.04, 0.05, 5.02, 6.08, mat_idx=5)

            # Paired Cylindrical Limestone Columns flanking the 2nd-floor arched window (`z = 4.98..10.05m`)!
            for col_s in (-0.45, 0.45):
                c_xy = b_xy + f_dir * (col_s * bay_w) + se_out * 0.56
                add_oriented_box(bm, (c_xy.x, c_xy.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 0.84, 0.84, 4.98, 5.58, mat_idx=1)
                ret_col = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=22, radius1=0.36, radius2=0.32, depth=4.15, matrix=Matrix.Translation((c_xy.x, c_xy.y, 7.62)))
                for v in ret_col["verts"]:
                    for f in v.link_faces:
                        f.material_index = 0
                        f.smooth = True
                add_oriented_box(bm, (c_xy.x, c_xy.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 0.88, 0.88, 9.68, 10.08, mat_idx=1)
        else:
            # Ground-floor large white-framed window (`z = 0.90..3.95m`) deeply recessed by `0.48m` + stone plinth below (`z = 0..0.90m`)
            pl_c = b_xy + nw_in * 0.16
            add_oriented_box(bm, (pl_c.x, pl_c.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w, 0.45, 0.0, 0.90, mat_idx=0)
            gw_c = b_xy + nw_in * 0.48
            add_oriented_box(bm, (gw_c.x, gw_c.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w, 0.25, 0.90, 3.95, mat_idx=3)
            gf_c = b_xy + nw_in * 0.22
            add_oriented_box(bm, (gf_c.x + se_out.x * 0.18, gf_c.y + se_out.y * 0.18), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w + 0.12, 0.26, 0.82, 0.96, mat_idx=4)
            add_oriented_box(bm, (gf_c.x, gf_c.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w, 0.16, 3.15, 3.25, mat_idx=4)
            for gm_s in (-0.46, 0.0, 0.46):
                gmp = gf_c + f_dir * (gm_s * win_w)
                add_oriented_box(bm, (gmp.x, gmp.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 0.08, 0.16, 0.90, 3.95, mat_idx=4)

        # 2nd Floor (`z = 5.15..9.65m`) & 3rd Floor (`z = 10.55..14.15m`): Semicircular Arched Windows with Rusticated Voussoirs & White Muntins!
        add_semicircular_arch_recess(
            bm, b_xy, (f_dir.x, f_dir.y), (se_out.x, se_out.y), width=win_w * 0.86, z_min=5.15, z_max=9.65,
            recess_depth=0.48, wall_mat=0, trim_mat=1, inner_mat=3, frame_mat=4, add_voussoirs=True
        )
        add_semicircular_arch_recess(
            bm, b_xy, (f_dir.x, f_dir.y), (se_out.x, se_out.y), width=win_w * 0.82, z_min=10.55, z_max=14.15,
            recess_depth=0.45, wall_mat=0, trim_mat=1, inner_mat=3, frame_mat=4, add_voussoirs=True
        )
        # Wrought-iron juliet balcony bars on 2nd floor windows (`b_i != 2`)
        if b_i != 2:
            jr_c = b_xy + se_out * 0.06
            add_oriented_box(bm, (jr_c.x, jr_c.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), win_w * 0.82, 0.05, 5.95, 6.02, mat_idx=5)
            for jb_i in range(-4, 5):
                jbp = jr_c + f_dir * (jb_i * 0.25)
                add_oriented_box(bm, (jbp.x, jbp.y), (f_dir.x, f_dir.y), (se_out.x, se_out.y), 0.035, 0.04, 5.15, 6.00, mat_idx=5)

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.025, segments=2)
    return obj


def build_saint_jean_west_buildings(dossier, palette, col_owned):
    """
    Hero #5: Builds `339893931`, `339893933`, and `339893934` along the West side of Rue Saint-Jean and Rue Saint-Paul Ouest,
    INCLUDING the immediate left-foreground street-canyon framing wing (`(40.2, -175.5)` to `(19.5, -159.2)`) visible on the
    left side of Camera 1 (`Rue_SaintPaul_Cobblestone_East.jpg`) with its projecting green-copper bracketed cornice,
    vertical `À LOUER / St.FX` banners, and white `P` parking regulation sign!
    """
    b_map = {b["id"]: b for b in dossier["osm_features"]["buildings"]}

    for b_id, h, add_m in ((339893931, 13.8, True), (339893933, 14.8, False), (339893934, 15.8, True)):
        b_data = b_map.get(b_id)
        if not b_data:
            continue
        obj = build_detailed_heritage_building(
            b_data,
            height=h,
            mat_wall=palette["Mat_MTL_PierreGrise_Limestone"],
            mat_trim=palette["Mat_MTL_WarmBuff_Limestone"],
            mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
            mat_window=palette["Mat_MTL_Window_Glass_Dark"],
            mat_frame=palette["Mat_MTL_Window_Frame_Light"],
            collection=col_owned,
            prefix="MTL_VM_0008_StJean",
            add_mansard=add_m,
        )
        if b_id == 339893931 and obj is not None:
            obj.data.materials.append(palette["Mat_MTL_Centaur_Blue"])      # 5: Vertical `À LOUER / St.FX` banner
            obj.data.materials.append(palette["Mat_MTL_Verdigris_Copper"])  # 6: Green copper cornice brackets
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            # Immediate Left-Foreground Canyon Wing along West Side of Rue Saint-Jean (`(40.2, -175.5)` to `(28.9, -166.8)`)
            p_se = Vector((40.20, -175.50))
            p_nw = Vector((28.90, -166.80))
            e_vec = p_nw - p_se
            e_len = e_vec.length
            e_dir = e_vec / e_len
            e_out = Vector((e_dir.y, -e_dir.x)).normalized()
            w_in = -e_out

            wing_c = (p_se + p_nw) * 0.5 + w_in * 4.5
            add_oriented_box(bm, (wing_c.x, wing_c.y), (e_dir.x, e_dir.y), (e_out.x, e_out.y), e_len - 0.8, 7.5, 0.0, 16.2, mat_idx=0)
            build_recessed_window_facade_along_edge(
                bm, p_se, p_nw, e_out, 0.0, 16.2, n_floors=4, bay_target_width=3.0, recess_depth=0.45,
                wall_mat=0, trim_mat=1, glass_mat=3, frame_mat=4, ground_commercial=True
            )
            # Projecting green verdigris copper cornice & brackets at z=15.6..16.3m (`Rue_SaintPaul_Cobblestone_East.jpg` top-left!)
            c_xy = (p_se + p_nw) * 0.5 + e_out * 0.42
            add_oriented_box(bm, (c_xy.x, c_xy.y), (e_dir.x, e_dir.y), (e_out.x, e_out.y), e_len + 0.4, 0.78, 15.6, 16.3, mat_idx=6)
            # Two vertical `À LOUER` and `St.FX` banners projecting from the left wall (`z = 4.2..9.6m`)
            for b_u, z0, z1 in ((0.22, 5.8, 9.6), (0.45, 4.0, 6.8)):
                ban_xy = p_se.lerp(p_nw, b_u) + e_out * 0.52
                add_oriented_box(bm, (ban_xy.x, ban_xy.y), (e_dir.x, e_dir.y), (e_out.x, e_out.y), 0.10, 0.82, z0, z1, mat_idx=5)
            # White `P` parking regulation sign at z=2.1..3.0m
            sgn_xy = p_se.lerp(p_nw, 0.14) + e_out * 0.22
            add_oriented_box(bm, (sgn_xy.x, sgn_xy.y), (e_dir.x, e_dir.y), (e_out.x, e_out.y), 0.38, 0.08, 2.05, 2.95, mat_idx=4)
            bm.to_mesh(obj.data)
            bm.free()


def add_contoured_parked_car(bm, cx, cy, c_ang_deg, body_mat, glass_mat, tire_mat, rim_mat, is_wagon=False):
    """
    Builds a contoured 3D parked vehicle with an 8-station longitudinal automotive silhouette
    (rounded front bumper -> sloped hood -> raked windshield -> curved cabin roof -> sloped rear window -> trunk),
    tapered greenhouse tumblehome, recessed dark tinted windshield & side windows, and 4 cylindrical 3D wheels with alloy rims.
    """
    ang_rad = math.radians(c_ang_deg)
    cd = Vector((math.cos(ang_rad), math.sin(ang_rad)))
    cp = Vector((-cd.y, cd.x))
    center = Vector((cx, cy))

    if is_wagon:
        # Station wagon / SUV longitudinal profile: (x_lon, z_bot, z_top, half_w_bot, half_w_top)
        stations = [
            (-2.18, 0.28, 0.68, 0.84, 0.78),
            (-2.02, 0.22, 0.92, 0.90, 0.84),
            (-1.65, 0.22, 1.46, 0.92, 0.76),
            (-0.45, 0.22, 1.50, 0.92, 0.76),
            (0.42,  0.22, 1.46, 0.92, 0.76),
            (0.98,  0.22, 0.94, 0.90, 0.84),
            (1.92,  0.24, 0.78, 0.88, 0.80),
            (2.16,  0.28, 0.58, 0.80, 0.74),
        ]
    else:
        # Contoured sedan longitudinal profile: (x_lon, z_bot, z_top, half_w_bot, half_w_top)
        stations = [
            (-2.15, 0.26, 0.65, 0.82, 0.76),
            (-1.95, 0.22, 0.88, 0.88, 0.82),
            (-1.35, 0.22, 0.92, 0.90, 0.82),
            (-0.75, 0.22, 1.40, 0.90, 0.74),
            (0.28,  0.22, 1.42, 0.90, 0.74),
            (0.95,  0.22, 0.90, 0.88, 0.82),
            (1.90,  0.23, 0.75, 0.86, 0.78),
            (2.15,  0.27, 0.55, 0.78, 0.72),
        ]

    rings = []
    for x_lon, z_bot, z_top, hw_b, hw_t in stations:
        p_mid = center + cd * x_lon
        z_belt = min(z_top - 0.04, 0.88)
        # 6-point cross-section ring: bottom-left, belt-left, roof-left, roof-right, belt-right, bottom-right
        p_bl = p_mid - cp * hw_b
        p_ml = p_mid - cp * (hw_b + 0.03)
        p_tl = p_mid - cp * hw_t
        p_tr = p_mid + cp * hw_t
        p_mr = p_mid + cp * (hw_b + 0.03)
        p_br = p_mid + cp * hw_b
        ring = [
            bm.verts.new((p_bl.x, p_bl.y, z_bot)),
            bm.verts.new((p_ml.x, p_ml.y, z_belt)),
            bm.verts.new((p_tl.x, p_tl.y, z_top)),
            bm.verts.new((p_tr.x, p_tr.y, z_top)),
            bm.verts.new((p_mr.x, p_mr.y, z_belt)),
            bm.verts.new((p_br.x, p_br.y, z_bot)),
        ]
        rings.append(ring)

    # Loft smooth quads between consecutive stations
    for i in range(len(rings) - 1):
        r0 = rings[i]
        r1 = rings[i + 1]
        is_cabin = (2 <= i <= 4) if is_wagon else (3 <= i <= 4)
        for k in range(6):
            nk = (k + 1) % 6
            try:
                f = bm.faces.new((r0[k], r1[k], r1[nk], r0[nk]))
                # Assign dark tinted glass to windshield, rear window & side greenhouse panels (`k in (1, 3)` during cabin stations)
                if is_cabin and k in (1, 3):
                    f.material_index = glass_mat
                elif (i == 4 and k == 2) or (i == (1 if is_wagon else 2) and k == 2):
                    f.material_index = glass_mat
                else:
                    f.material_index = body_mat
                f.smooth = True
            except ValueError:
                pass
    try:
        f_rear = bm.faces.new(rings[0][::-1])
        f_rear.material_index = body_mat
        f_front = bm.faces.new(rings[-1])
        f_front.material_index = body_mat
    except ValueError:
        pass

    # 4 True Cylindrical 3D Wheels (`segments=20`, rotated 90° around the axle) + Metallic Alloy Hubcaps!
    rot_wheel = Euler((math.radians(90.0), 0.0, ang_rad), 'XYZ').to_matrix().to_4x4()
    for wx in (-1.30, 1.32):
        for side_s in (-1.0, 1.0):
            wp = center + cd * wx + cp * (side_s * 0.84)
            ret_t = bmesh.ops.create_cone(
                bm, cap_ends=True, cap_tris=False, segments=20,
                radius1=0.33, radius2=0.33, depth=0.24,
                matrix=Matrix.Translation((wp.x, wp.y, 0.33)) @ rot_wheel
            )
            for v in ret_t["verts"]:
                for f in v.link_faces:
                    f.material_index = tire_mat
                    f.smooth = True
            rp = wp + cp * (side_s * 0.04)
            ret_r = bmesh.ops.create_cone(
                bm, cap_ends=True, cap_tris=False, segments=16,
                radius1=0.21, radius2=0.21, depth=0.20,
                matrix=Matrix.Translation((rp.x, rp.y, 0.33)) @ rot_wheel
            )
            for v in ret_r["verts"]:
                for f in v.link_faces:
                    f.material_index = rim_mat
                    f.smooth = True


def build_context_proxies_0008(dossier, palette, col_proxy):
    """
    Builds non-owned context buildings (`Block_MTL-VM-0008_Context_Proxy`) visible in the 4 Street View cameras:
    1. **500 Place d'Armes 32-Story Dark Steel-and-Glass Skyscraper Proxy (`Proxy_500_Place_dArmes_Skyline`)**:
       Positioned at `(-28.5, -72.0)` where the sightlines from Camera 1 (`Rue_SaintPaul_Cobblestone_East`),
       Camera 3 (`Corner_SaintFrancoisXavier`), and Camera 4 (`Rue_du_SaintSacrement`) all see the tower rising
       in the upper-left sky canyon with full 32-story dark reflective glass curtain wall, projecting black anodized
       structural mullions, and mechanical louver bands!
    2. **Notre-Dame Basilica Twin Gothic Towers Proxy (`Proxy_Basilica_Skyline`)**:
       Peeking above the central roofline in Camera 3 (`Corner_SaintFrancoisXavier.jpg`).
    3. **4-Story Second Empire Mansard Building + 5-Story Limestone Corner Building with Red-Brick Chimney (`Proxy_465_StFrancoisXavier_102127872`)**:
       Positioned directly across Rue du Saint-Sacrement in Camera 3 (`(-29.5, -124.8)` to `(-9.8, -126.4)`) with deeply recessed
       dark-glass windows, white muntins, dark slate Mansard roof with 6 white dormer windows, and red-brick chimney!
    4. **Dark Scaffolding-Wrapped Building + 5-Story Pale Masonry Building (`Proxy_339898460`)** + **Contoured 3D Parked Cars** in the Camera 3 foreground lot!
    """
    # 1. 32-Story Dark Steel-and-Glass 500 Place d'Armes Skyscraper Proxy (`z = 0..132.8m`)
    mesh_500 = bpy.data.meshes.new("Proxy_500_Place_dArmes_Skyline_Mesh")
    obj_500 = bpy.data.objects.new("Proxy_500_Place_dArmes_Skyline", mesh_500)
    col_proxy.objects.link(obj_500)
    for m in [
        palette["Mat_MTL_Window_Glass_Dark"],        # 0: Dark reflective bronze/charcoal curtain-wall glass
        palette["Mat_MTL_CastIron_Black"],           # 1: Projecting dark anodized aluminum mullions & spandrels
        palette["Mat_MTL_Dark_Honed_Granite"],       # 2: Mechanical louver bands & penthouse
    ]:
        obj_500.data.materials.append(m)

    bm_500 = bmesh.new()
    for tw_c, tw_w, tw_d, tw_h in (
        (Vector((-28.5, -72.0)), 32.0, 34.0, 132.8),
        (Vector((-36.5, -90.0)), 22.0, 24.0, 114.0),
    ):
        tw_dir = Vector((0.86, 0.51)).normalized()
        tw_perp = Vector((-tw_dir.y, tw_dir.x))
        # Dark reflective glass core
        add_oriented_box(bm_500, (tw_c.x, tw_c.y), (tw_dir.x, tw_dir.y), (tw_perp.x, tw_perp.y), tw_w - 0.5, tw_d - 0.5, 0.0, tw_h, mat_idx=0)
        # Recessed top mechanical penthouse
        add_oriented_box(bm_500, (tw_c.x, tw_c.y), (tw_dir.x, tw_dir.y), (tw_perp.x, tw_perp.y), tw_w - 3.2, tw_d - 3.2, tw_h - 8.0, tw_h + 3.8, mat_idx=2)
        # Horizontal spandrels every 3.75m + double-height mechanical louver bands
        n_fl = int((tw_h - 4.0) / 3.75)
        for f_i in range(n_fl):
            fz = 4.0 + f_i * 3.75
            is_mech = f_i in (1, 15, n_fl - 2)
            sh = 1.65 if is_mech else 0.55
            add_oriented_box(bm_500, (tw_c.x, tw_c.y), (tw_dir.x, tw_dir.y), (tw_perp.x, tw_perp.y), tw_w + 0.15, tw_d + 0.15, fz, fz + sh, mat_idx=(2 if is_mech else 1))
        # Projecting vertical Miesian mullions around all 4 faces every 2.0m
        n_m = int(tw_w * 0.23)
        for side_s in (-1.0, 1.0):
            for u_i in range(-n_m, n_m + 1):
                mp1 = tw_c + tw_dir * (u_i * 2.05) + tw_perp * (side_s * tw_d * 0.5)
                add_oriented_box(bm_500, (mp1.x, mp1.y), (tw_dir.x, tw_dir.y), (tw_perp.x, tw_perp.y), 0.24, 0.42, 0.0, tw_h, mat_idx=1)
                mp2 = tw_c + tw_perp * (u_i * 2.15) + tw_dir * (side_s * tw_w * 0.5)
                add_oriented_box(bm_500, (mp2.x, mp2.y), (tw_perp.x, tw_perp.y), (tw_dir.x, tw_dir.y), 0.24, 0.42, 0.0, tw_h, mat_idx=1)
    bm_500.to_mesh(mesh_500)
    bm_500.free()

    # 2. Custom High-Detail Proxy for `102127872` (Center & Center-Left of Camera 3 `Corner_SaintFrancoisXavier.jpg`!)
    mesh_465 = bpy.data.meshes.new("Proxy_465_StFrancoisXavier_102127872_Mesh")
    obj_465 = bpy.data.objects.new("Proxy_465_StFrancoisXavier_102127872", mesh_465)
    col_proxy.objects.link(obj_465)
    for m in [
        palette["Mat_MTL_PierreGrise_Limestone"],    # 0: Grey limestone facade
        palette["Mat_MTL_WarmBuff_Limestone"],       # 1: Trim & cornices
        palette["Mat_MTL_Slate_Roof_Dark"],          # 2: Dark slate Mansard roof & ground shopfront
        palette["Mat_MTL_Window_Glass_Dark"],        # 3: Deeply recessed dark reflective window glass
        palette["Mat_MTL_Window_Frame_Light"],       # 4: Crisp white window frames & mansard dormers
        palette["Mat_MTL_Heritage_RedBrick"],        # 5: Tall red-brick party-wall chimney
    ]:
        obj_465.data.materials.append(m)

    bm = bmesh.new()
    p_west = Vector((-29.5, -124.2))
    p_mid = Vector((-18.2, -125.6))
    p_east = Vector((-9.8, -126.4))
    sw_dir = (p_east - p_west).normalized()
    sw_out = Vector((-sw_dir.y, sw_dir.x)).normalized()
    if sw_out.dot(Vector((-19.17, -163.7)) - p_mid) < 0:
        sw_out = -sw_out
    ne_in = -sw_out

    # Left Mansard Wing (core box inset by 0.85m into `ne_in` so windows have full `0.48m` dark glass recess!)
    lw_len = (p_mid - p_west).length
    lw_c = (p_west + p_mid) * 0.5 + ne_in * 7.85
    add_oriented_box(bm, (lw_c.x, lw_c.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), lw_len - 0.4, 14.0, 0.0, 13.8, mat_idx=0)
    build_recessed_window_facade_along_edge(
        bm, p_west, p_mid, sw_out, 0.0, 13.8, n_floors=4, bay_target_width=2.1, recess_depth=0.48,
        wall_mat=0, trim_mat=4, glass_mat=3, frame_mat=4, ground_commercial=True
    )
    mans_c = (p_west + p_mid) * 0.5 + ne_in * 7.2
    add_oriented_box(bm, (mans_c.x, mans_c.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), lw_len - 0.2, 13.6, 13.8, 16.6, mat_idx=2)
    for d_i in range(6):
        du = (d_i + 0.5) / 6.0
        dp = p_west.lerp(p_mid, du) - sw_out * 0.12
        add_oriented_box(bm, (dp.x, dp.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 1.05, 0.65, 14.1, 15.9, mat_idx=4)
        add_oriented_box(bm, (dp.x + sw_out.x * 0.25, dp.y + sw_out.y * 0.25), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 0.76, 0.20, 14.25, 15.65, mat_idx=3)

    # Right 5-Story Wing (core box inset by 0.85m into `ne_in` so all 5 floors of windows show dark reflective glass!)
    rw_len = (p_east - p_mid).length
    rw_c = (p_mid + p_east) * 0.5 + ne_in * 7.85
    add_oriented_box(bm, (rw_c.x, rw_c.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), rw_len - 0.4, 14.0, 0.0, 17.6, mat_idx=0)
    build_recessed_window_facade_along_edge(
        bm, p_mid, p_east, sw_out, 0.0, 17.6, n_floors=5, bay_target_width=2.1, recess_depth=0.48,
        wall_mat=0, trim_mat=4, glass_mat=3, frame_mat=4, ground_commercial=True
    )
    chim_xy = p_east + ne_in * 1.8
    add_oriented_box(bm, (chim_xy.x, chim_xy.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 1.55, 2.0, 14.5, 21.4, mat_idx=5)

    # Stepped Gothic Basilica Tower Silhouette behind the Mansard Wing (`(-20.5, -102.0)`, `z = 16.0..28.5m`)
    bas_c = Vector((-20.5, -102.0))
    add_oriented_box(bm, (bas_c.x, bas_c.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 6.5, 6.5, 0.0, 27.5, mat_idx=1)
    for sp_s in (-2.8, 2.8):
        sp_p = bas_c + sw_dir * sp_s
        add_oriented_box(bm, (sp_p.x, sp_p.y), (sw_dir.x, sw_dir.y), (sw_out.x, sw_out.y), 1.1, 1.1, 25.0, 30.2, mat_idx=1)

    bm.to_mesh(mesh_465)
    bm.free()
    apply_bevel_and_smooth(obj_465, width=0.025, segments=2)

    # 3. Custom High-Detail Proxy for `339898460` (Left Midground of Camera 3 `Corner_SaintFrancoisXavier.jpg`!) + Contoured 3D Parked Vehicles!
    mesh_460 = bpy.data.meshes.new("Proxy_339898460_Mesh")
    obj_460 = bpy.data.objects.new("Proxy_339898460", mesh_460)
    col_proxy.objects.link(obj_460)
    for m in [
        palette["Mat_MTL_Slate_Roof_Dark"],          # 0: Dark charcoal scaffolding-wrapped facade
        palette["Mat_MTL_Window_Frame_Light"],       # 1: Pale masonry & white scaffolding bands
        palette["Mat_MTL_WarmBuff_Limestone"],       # 2: 2-story foreground annex wall
        palette["Mat_MTL_Window_Glass_Dark"],        # 3: Deeply recessed dark window glass & car windshields
        palette["Mat_MTL_Heritage_RedBrick"],        # 4: Rooftop brick chimney
        palette["Mat_MTL_Auto_Paint_Charcoal"],      # 5: Glossy dark charcoal automotive paint
        palette["Mat_MTL_Auto_Paint_Silver"],        # 6: Glossy silver/white SUV automotive paint
        palette["Mat_MTL_Auto_Paint_Crimson"],       # 7: Glossy crimson red sedan paint
        palette["Mat_MTL_Rubber_Tire"],              # 8: Cylindrical rubber tires
        palette["Mat_MTL_Alloy_Rim"],                # 9: Metallic alloy wheel hubcaps
    ]:
        obj_460.data.materials.append(m)

    bm2 = bmesh.new()
    # Dark scaffolding-wrapped 4.5-story block at (-34.5, -126.5) with horizontal white structural bands (`Corner_SaintFrancoisXavier.jpg` Left!)
    d_c = Vector((-34.5, -126.5))
    d_dir = Vector((0.82, 0.57)).normalized()
    d_out = Vector((0.57, -0.82)).normalized()
    add_oriented_box(bm2, (d_c.x, d_c.y), (d_dir.x, d_dir.y), (d_out.x, d_out.y), 13.5, 14.5, 0.0, 17.5, mat_idx=0)
    for hz in (4.5, 9.2, 13.8, 17.3):
        add_oriented_box(bm2, (d_c.x, d_c.y), (d_dir.x, d_dir.y), (d_out.x, d_out.y), 13.8, 14.8, hz, hz + 0.22, mat_idx=1)
    add_oriented_box(bm2, (d_c.x - 1.5, d_c.y + 1.5), (d_dir.x, d_dir.y), (d_out.x, d_out.y), 1.6, 1.6, 17.5, 20.2, mat_idx=4)

    # 5-story pale masonry building (core inset by 0.85m so all upper windows have deep dark glass!) + 2-story pale annex on far left
    l_c = Vector((-46.5, -123.5))
    add_oriented_box(bm2, (l_c.x - d_out.x * 0.85, l_c.y - d_out.y * 0.85), (d_dir.x, d_dir.y), (d_out.x, d_out.y), 14.5, 14.0, 0.0, 19.5, mat_idx=1)
    p_l1 = l_c - d_dir * 7.5 + d_out * 6.8
    p_l2 = l_c + d_dir * 7.5 + d_out * 6.8
    build_recessed_window_facade_along_edge(
        bm2, p_l1, p_l2, d_out, 7.8, 19.5, n_floors=3, bay_target_width=3.2, recess_depth=0.48,
        wall_mat=1, trim_mat=2, glass_mat=3, frame_mat=0, ground_commercial=False
    )
    an_c = Vector((-44.0, -132.0))
    add_oriented_box(bm2, (an_c.x, an_c.y), (d_dir.x, d_dir.y), (d_out.x, d_out.y), 14.5, 8.5, 0.0, 7.8, mat_idx=2)

    # 3 Contoured 3D Parked Vehicles in the Camera 3 Parking Lot (`Corner_SaintFrancoisXavier.jpg`!)
    for cx, cy, c_ang, body_mat, is_w in (
        (-15.8, -152.2, -32.0, 5, True),   # Right-foreground dark charcoal station wagon
        (-22.2, -151.8, 55.0,  6, True),   # Left-midground silver/white SUV
        (-18.2, -145.5, 55.0,  7, False),  # Midground crimson red sedan
    ):
        add_contoured_parked_car(bm2, cx, cy, c_ang, body_mat=body_mat, glass_mat=3, tire_mat=8, rim_mat=9, is_wagon=is_w)

    bm2.to_mesh(mesh_460)
    bm2.free()
    apply_bevel_and_smooth(obj_460, width=0.025, segments=2)


def load_kit_assets(palette):
    assets = {}
    if not os.path.exists(KIT_BLEND_PATH):
        return assets
    target_names = ["jacaranda_tree_LOD0", "Master_Street_Bench"]
    with bpy.data.libraries.load(KIT_BLEND_PATH, link=False) as (data_from, data_to):
        avail = set(data_from.objects)
        data_to.objects = [n for n in target_names if n in avail]
    for obj in data_to.objects:
        if obj is not None:
            assets[obj.name] = obj
    tree_obj = assets.get("jacaranda_tree_LOD0")
    if tree_obj:
        leaf_mat = bpy.data.materials.get("jacaranda_tree_leaves")
        if leaf_mat and leaf_mat.use_nodes:
            nodes = leaf_mat.node_tree.nodes
            links = leaf_mat.node_tree.links
            bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
            diff_node = next((n for n in nodes if n.type == 'TEX_IMAGE' and n.image and "diff" in n.image.name.lower()), None)
            if bsdf and diff_node:
                mix_g = nodes.new("ShaderNodeMix")
                mix_g.data_type = 'RGBA'
                mix_g.blend_type = 'MIX'
                mix_g.inputs["Factor"].default_value = 0.45
                mix_g.inputs["B"].default_value = kit.hex_to_rgba("#4A742C")
                links.new(mix_g.inputs["A"], diff_node.outputs["Color"])
                links.new(bsdf.inputs["Base Color"], mix_g.outputs["Result"])
    return assets


def build_ground_and_streetscape_0008(dossier, palette, col_owned, kit_assets):
    """
    Builds the georeferenced cobblestone streets (`Rue Saint-Paul Ouest`, `Rue du Saint-Sacrement`, `Rue Saint-Jean`),
    asphalt roadways (`Rue Saint-François-Xavier`), concrete/granite sidewalks with slab joints,
    flush cast-iron stormwater grates (`Camera 1`) & manhole covers (`Camera 1` & `Camera 2`, `z_offset = 0.008m`),
    curbed soil/mulch parking median & tall curved cobra-head streetlamp with parking/STOP signs (`Camera 3`),
    vintage black cast-iron streetlamps with hanging flower baskets (`Camera 2` & `Camera 4`),
    and instances genuine Poly Haven `jacaranda_tree_LOD0` botanical trees (with ZERO trees on Rue du Saint-Sacrement!).
    """
    mesh = bpy.data.meshes.new("MTL_VM_0008_Streetscape_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0008_Streetscape", mesh)
    col_owned.objects.link(obj)
    for m in [
        palette["Mat_MTL_Street_Asphalt"],         # 0: Roadbed 2K Poly Haven asphalt
        palette["Mat_MTL_Cobblestone_Street"],     # 1: Historic 2K Poly Haven cobblestone street (Rue St-Paul, St-Sacrement & St-Jean)
        palette["Mat_MTL_Light_Granite_Steps"],    # 2: Concrete/granite sidewalks & curbs with slab joints
        palette["Mat_MTL_CastIron_Black"],         # 3: Black cast-iron streetlamp poles, manhole covers & bollards
        palette["Mat_MTL_Window_Frame_Light"],     # 4: White parking regulation signs & lamp globes
        palette["Mat_MTL_BN_Red"],                 # 5: Red octagonal STOP sign & flower basket accents
        palette["Mat_MTL_Rust_Grate"],             # 6: Cast-iron stormwater grates & planter mulch bed
        palette["Mat_MTL_Heritage_Green"],         # 7: Heritage green street bin & planter foliage (Camera 4)
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Base Asphalt Ground Plane covering the block
    add_oriented_box(bm, (45.0, -235.0), (1.0, 0.0), (0.0, 1.0), 340.0, 360.0, -0.25, 0.0, mat_idx=0)

    # 2. Historic Cobblestone Roadways (`Rue Saint-Paul Ouest`, `Rue du Saint-Sacrement`, and `Rue Saint-Jean`)
    st_paul_dir = Vector((0.62, 0.78)).normalized()
    st_paul_perp = Vector((-st_paul_dir.y, st_paul_dir.x))
    add_oriented_box(bm, (48.0, -182.0), (st_paul_dir.x, st_paul_dir.y), (st_paul_perp.x, st_paul_perp.y), 155.0, 14.0, 0.0, 0.06, mat_idx=1)

    sac_dir = Vector((-0.78, 0.62)).normalized()
    sac_perp = Vector((-sac_dir.y, sac_dir.x))
    add_oriented_box(bm, (10.0, -148.0), (sac_dir.x, sac_dir.y), (sac_perp.x, sac_perp.y), 95.0, 11.0, 0.0, 0.06, mat_idx=1)

    sj_p1 = Vector((50.0, -172.6))
    sj_p2 = Vector((28.4, -155.7))
    sj_dir = (sj_p2 - sj_p1).normalized()
    sj_out = Vector((-sj_dir.y, sj_dir.x)).normalized()
    sj_road_c = (sj_p1 + sj_p2) * 0.5 + sj_out * 4.6
    add_oriented_box(bm, (sj_road_c.x, sj_road_c.y), (sj_dir.x, sj_dir.y), (sj_out.x, sj_out.y), 38.0, 6.2, 0.0, 0.06, mat_idx=1)

    # 3. Sidewalks & Curbs in all 4 Camera Foregrounds:
    sw_sj_e = (sj_p1 + sj_p2) * 0.5 + sj_out * 1.15
    add_oriented_box(bm, (sw_sj_e.x, sw_sj_e.y), (sj_dir.x, sj_dir.y), (sj_out.x, sj_out.y), 34.0, 2.3, 0.0, 0.14, mat_idx=2)
    sw_sj_w = (sj_p1 + sj_p2) * 0.5 + sj_out * 8.2
    add_oriented_box(bm, (sw_sj_w.x, sw_sj_w.y), (sj_dir.x, sj_dir.y), (sj_out.x, sj_out.y), 34.0, 2.4, 0.0, 0.14, mat_idx=2)

    # Foreground flush drainage grates (`z = 0.068m`) & manhole covers in Camera 1 (`[43.88, -172.11]`, heading `345.7°`)
    cam1_pos = Vector((43.88, -172.11))
    cam1_fwd = Vector((math.sin(math.radians(345.7)), math.cos(math.radians(345.7))))
    cam1_right = Vector((cam1_fwd.y, -cam1_fwd.x))
    for g_fwd, g_r, gw, gd in ((4.8, -0.85, 1.35, 0.42), (7.6, 0.55, 1.15, 0.38)):
        gp = cam1_pos + cam1_fwd * g_fwd + cam1_right * g_r
        add_oriented_box(bm, (gp.x, gp.y), (cam1_right.x, cam1_right.y), (cam1_fwd.x, cam1_fwd.y), gw, gd, 0.05, 0.068, mat_idx=6)
    for mh_f, mh_r, mh_z in ((3.8, 2.1, 0.148), (6.5, 2.4, 0.148)):
        mp = cam1_pos + cam1_fwd * mh_f + cam1_right * mh_r
        ret_mh = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20, radius1=0.32, radius2=0.32, depth=0.012, matrix=Matrix.Translation((mp.x, mp.y, mh_z)))
        for v in ret_mh["verts"]:
            for f in v.link_faces:
                f.material_index = 6

    # Camera 2 (`Rue_SaintPaul_Cobblestone_West.jpg` at `[22.55, -204.75]`) West Sidewalk + Cobblestone Roadbed + Flush Cast-Iron Manhole Cover!
    sp_p1 = Vector((11.5, -210.3))
    sp_p2 = Vector((37.1, -173.1))
    sp_w_dir = (sp_p2 - sp_p1).normalized()
    sp_w_out = Vector((sp_w_dir.y, -sp_w_dir.x)).normalized()
    # Full cobblestone roadbed directly bordering the west sidewalk curb in Camera 2 (`z = 0.0..0.06m`)!
    sp_road_c = (sp_p1 + sp_p2) * 0.5 + sp_w_out * 7.8
    add_oriented_box(bm, (sp_road_c.x, sp_road_c.y), (sp_w_dir.x, sp_w_dir.y), (sp_w_out.x, sp_w_out.y), 95.0, 12.5, 0.0, 0.06, mat_idx=1)
    sw_sp_w = (sp_p1 + sp_p2) * 0.5 + sp_w_out * 1.15
    add_oriented_box(bm, (sw_sp_w.x, sw_sp_w.y), (sp_w_dir.x, sp_w_dir.y), (sp_w_out.x, sp_w_out.y), 48.0, 2.3, 0.0, 0.14, mat_idx=2)
    curb_sp = (sp_p1 + sp_p2) * 0.5 + sp_w_out * 2.32
    add_oriented_box(bm, (curb_sp.x, curb_sp.y), (sp_w_dir.x, sp_w_dir.y), (sp_w_out.x, sp_w_out.y), 48.0, 0.22, 0.0, 0.15, mat_idx=2)
    # Flush dark cast-iron manhole cover on the cobblestone roadbed just outside the curb (`z = 0.060..0.068m`)!
    mh2_xy = Vector((22.05, -201.35))
    ret_mh2 = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=0.34, radius2=0.34, depth=0.008, matrix=Matrix.Translation((mh2_xy.x, mh2_xy.y, 0.064)))
    for v in ret_mh2["verts"]:
        for f in v.link_faces:
            f.material_index = 3

    # Heritage Black Cast-Iron Streetlamps with Hanging Flower Baskets in Camera 2 (`(25.2, -190.2)`) and Camera 4 (`(14.2, -144.4)`, `(5.8, -138.2)`, `(-1.5, -132.5)`)
    for lx, ly in ((25.2, -190.2), (14.2, -144.4), (5.8, -138.2), (-1.5, -132.5)):
        ret_lp = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16, radius1=0.15, radius2=0.065, depth=3.8, matrix=Matrix.Translation((lx, ly, 2.04)))
        for v in ret_lp["verts"]:
            for f in v.link_faces:
                f.material_index = 3
                f.smooth = True
        ret_gl = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6, radius1=0.14, radius2=0.23, depth=0.46, matrix=Matrix.Translation((lx, ly, 4.14)))
        for v in ret_gl["verts"]:
            for f in v.link_faces:
                f.material_index = 4
        ret_cap = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6, radius1=0.25, radius2=0.03, depth=0.22, matrix=Matrix.Translation((lx, ly, 4.48)))
        for v in ret_cap["verts"]:
            for f in v.link_faces:
                f.material_index = 3
        # Hanging flower basket on the streetlamp (`Rue_du_SaintSacrement.jpg`!)
        ret_fb = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.24, matrix=Matrix.Translation((lx - 0.25, ly - 0.15, 3.15)))
        for v in ret_fb["verts"]:
            for f in v.link_faces:
                f.material_index = 5

    # Camera 4 (`Rue_du_SaintSacrement.jpg`) NE Raised Concrete Sidewalk & Curb along Curb Market & Centaur Theatre + Green Bin!
    sac_p1 = Vector((28.4, -155.7))
    sac_p2 = Vector((-9.8, -126.4))
    sac_e_dir = (sac_p2 - sac_p1).normalized()
    sac_e_out = Vector((-sac_e_dir.y, sac_e_dir.x)).normalized()
    if sac_e_out.dot(Vector((21.81, -154.62)) - sac_p1) < 0:
        sac_e_out = -sac_e_out
    sw_sac = (sac_p1 + sac_p2) * 0.5 + sac_e_out * 1.15
    add_oriented_box(bm, (sw_sac.x, sw_sac.y), (sac_e_dir.x, sac_e_dir.y), (sac_e_out.x, sac_e_out.y), 52.0, 2.30, 0.0, 0.15, mat_idx=2)
    curb_sac = (sac_p1 + sac_p2) * 0.5 + sac_e_out * 2.32
    add_oriented_box(bm, (curb_sac.x, curb_sac.y), (sac_e_dir.x, sac_e_dir.y), (sac_e_out.x, sac_e_out.y), 52.0, 0.22, 0.0, 0.16, mat_idx=2)
    ret_gb = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16, radius1=0.26, radius2=0.28, depth=0.82, matrix=Matrix.Translation((11.8, -142.2, 0.55)))
    for v in ret_gb["verts"]:
        for f in v.link_faces:
            f.material_index = 7
            f.smooth = True

    # Camera 3 (`Corner_SaintFrancoisXavier.jpg` at `[-19.17, -163.70]`, heading `6.7°`):
    # Low Curbed Soil/Mulch Parking Median (`0.12m` curb around dark mulch bed `mat_idx=6`) + Curved Cobra-Head Streetlamp Pole!
    cam3_pos = Vector((-19.17, -163.70))
    cam3_fwd = Vector((math.sin(math.radians(6.7)), math.cos(math.radians(6.7))))
    cam3_right = Vector((cam3_fwd.y, -cam3_fwd.x))

    isl_c = cam3_pos + cam3_fwd * 10.5 - cam3_right * 1.8
    add_oriented_box(bm, (isl_c.x, isl_c.y), (cam3_fwd.x, cam3_fwd.y), (cam3_right.x, cam3_right.y), 11.5, 2.2, 0.0, 0.11, mat_idx=2)
    add_oriented_box(bm, (isl_c.x, isl_c.y), (cam3_fwd.x, cam3_fwd.y), (cam3_right.x, cam3_right.y), 11.1, 1.8, 0.0, 0.12, mat_idx=6)

    pole3_xy = cam3_pos + cam3_fwd * 9.8 + cam3_right * 1.75
    ret_p3 = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16, radius1=0.11, radius2=0.07, depth=7.4, matrix=Matrix.Translation((pole3_xy.x, pole3_xy.y, 3.7)))
    for v in ret_p3["verts"]:
        for f in v.link_faces:
            f.material_index = 3
            f.smooth = True
    arm_c = pole3_xy + cam3_right * 0.95
    add_oriented_box(bm, (arm_c.x, arm_c.y), (cam3_right.x, cam3_right.y), (cam3_fwd.x, cam3_fwd.y), 1.95, 0.10, 7.25, 7.38, mat_idx=3)
    lum_c = pole3_xy + cam3_right * 1.85
    add_oriented_box(bm, (lum_c.x, lum_c.y), (cam3_right.x, cam3_right.y), (cam3_fwd.x, cam3_fwd.y), 0.65, 0.28, 7.22, 7.42, mat_idx=3)
    add_oriented_box(bm, (pole3_xy.x - cam3_fwd.x * 0.12, pole3_xy.y - cam3_fwd.y * 0.12), (cam3_right.x, cam3_right.y), (cam3_fwd.x, cam3_fwd.y), 0.34, 0.05, 2.35, 3.25, mat_idx=4)
    stop_xy = cam3_pos + cam3_fwd * 22.5 + cam3_right * 5.8
    add_oriented_box(bm, (stop_xy.x, stop_xy.y), (cam3_right.x, cam3_right.y), (cam3_fwd.x, cam3_fwd.y), 0.06, 0.06, 0.0, 2.35, mat_idx=3)
    add_oriented_box(bm, (stop_xy.x, stop_xy.y), (cam3_right.x, cam3_right.y), (cam3_fwd.x, cam3_fwd.y), 0.62, 0.06, 2.15, 2.75, mat_idx=5)

    bm.to_mesh(mesh)
    bm.free()

    # Instance Genuine Poly Haven `jacaranda_tree_LOD0` Botanical Trees (ZERO trees on Rue du Saint-Sacrement!)
    tree_src = kit_assets.get("jacaranda_tree_LOD0")
    if tree_src is not None:
        rng = random.Random(8008)
        tree_coords = [(t["x"], t["y"], 0.52, 0.58) for t in dossier["osm_features"].get("trees", [])]
        tree_coords.extend([
            (-19.8, -151.2, 0.24, 0.30),  # Young deciduous tree in Camera 3 curbed median island
            (-15.5, -141.5, 0.22, 0.28),  # Second young tree in Camera 3 midground right
            (16.5, -118.0, 0.44, 0.52),   # Background foliage behind Centaur Theatre
        ])
        for idx, (tx, ty, s_xy, s_z) in enumerate(tree_coords):
            t_obj = bpy.data.objects.new(f"MTL_VM_0008_Tree_{idx}", tree_src.data)
            col_owned.objects.link(t_obj)
            t_obj.location = (tx, ty, 0.10)
            t_obj.scale = (s_xy, s_xy, s_z)
            t_obj.rotation_euler = (0.0, 0.0, rng.uniform(0.0, 2.0 * math.pi))


def setup_lighting_and_world(scene):
    scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 64
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    bg = nodes.new("ShaderNodeBackground")
    out = nodes.new("ShaderNodeOutputWorld")
    hdri_path = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")
    img_hdri = load_image_safe(hdri_path, colorspace=None)
    if img_hdri:
        env = nodes.new("ShaderNodeTexEnvironment")
        env.image = img_hdri
        tc = nodes.new("ShaderNodeTexCoord")
        map_n = nodes.new("ShaderNodeMapping")
        map_n.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(95.0))
        links.new(map_n.inputs["Vector"], tc.outputs["Generated"])
        links.new(env.inputs["Vector"], map_n.outputs["Vector"])
        links.new(bg.inputs["Color"], env.outputs["Color"])
        bg.inputs["Strength"].default_value = 1.15
    else:
        sky = nodes.new("ShaderNodeTexSky")
        links.new(bg.inputs["Color"], sky.outputs["Color"])
        bg.inputs["Strength"].default_value = 0.9

    links.new(out.inputs["Surface"], bg.outputs["Background"])

    sun_data = bpy.data.lights.new(name="MTL_Sun", type='SUN')
    sun_data.energy = 3.5
    sun_data.color = (1.0, 0.96, 0.90)
    if hasattr(sun_data, "angle"):
        sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name="MTL_Sun", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(40.0), math.radians(18.0), math.radians(135.0))


def render_cameras(dossier, col_root, iter_tag="iter3"):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100

    for cam_info in dossier["streetview_cameras"]:
        label = cam_info["label"]
        cx, cy = cam_info["blender_cam_xy_m"]
        heading = cam_info.get("heading", cam_info.get("heading_deg", 0.0))
        pitch = 10.0 if "heading" in cam_info else cam_info.get("pitch_deg", 12.0)
        fov = cam_info.get("fov_deg", 90.0)

        cam_data = bpy.data.cameras.new(name=f"Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(fov)
        cam_data.clip_start = 0.2
        cam_data.clip_end = 1000.0

        cam_obj = bpy.data.objects.new(name=f"Cam_{label}", object_data=cam_data)
        col_root.objects.link(cam_obj)
        cam_obj.location = (cx, cy, 1.7)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch), 0.0, math.radians(-heading))

        scene.camera = cam_obj
        out_path = os.path.join(RENDERS_DIR, f"{iter_tag}_{label}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        for alias_tag in ("iter1", "iter2"):
            if iter_tag != alias_tag:
                try:
                    shutil.copyfile(out_path, os.path.join(RENDERS_DIR, f"{alias_tag}_{label}.png"))
                except Exception:
                    pass
        print(f"Rendered Street View Camera ({label}, heading={heading}, pitch={pitch}) -> {out_path}")

    # Overview Camera (1280x720) framing the entire Rue Saint-Paul Ouest, Centaur Theatre, Curb Market, Modavie, Exchange & 500 Place d'Armes!
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    ov_data = bpy.data.cameras.new(name="Cam_Overview")
    ov_data.lens_unit = 'FOV'
    ov_data.angle = math.radians(72.0)
    ov_data.clip_start = 0.5
    ov_data.clip_end = 1500.0
    ov_obj = bpy.data.objects.new(name="Cam_Overview", object_data=ov_data)
    col_root.objects.link(ov_obj)
    ov_obj.location = (118.0, -248.0, 92.0)
    direction = Vector((18.0, -162.0, 14.0)) - ov_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    ov_obj.rotation_euler = rot_quat.to_euler()

    scene.camera = ov_obj
    snap_path = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
    scene.render.filepath = snap_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Overview Snapshot -> {snap_path}")


def main():
    clear_scene()
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    palette = kit.create_montreal_material_palette()
    palette = create_custom_materials(palette)
    kit_assets = load_kit_assets(palette)

    col_root = get_or_create_collection(f"Block_{BLOCK_ID}")
    col_owned = get_or_create_collection(f"Block_{BLOCK_ID}_Owned", parent=col_root)
    col_proxy = get_or_create_collection(f"Block_{BLOCK_ID}_Context_Proxy", parent=col_root)

    build_ground_and_streetscape_0008(dossier, palette, col_owned, kit_assets)
    build_saint_jean_west_buildings(dossier, palette, col_owned)

    custom_owned_ids = {1082007381, 1082007382, 1082007383, 339893930, 339893931, 339893933, 339893934}
    custom_proxy_ids = {102127872, 339898460}

    for b in dossier["osm_features"]["buildings"]:
        b_id = b["id"]
        is_owned = b.get("is_primary_owner", True)

        if is_owned:
            if b_id == 1082007381:
                build_centaur_theatre_1082007381(b, palette, col_owned)
            elif b_id == 1082007382:
                build_curb_market_1082007382(b, palette, col_owned)
            elif b_id == 1082007383:
                build_modavie_corner_1082007383(b, palette, col_owned)
            elif b_id == 339893930:
                build_exchange_beaux_arts_339893930(b, palette, col_owned)
            elif b_id in custom_owned_ids:
                continue
            else:
                h = 18.5 if b_id in (339867951, 339863191, 339876529, 340625153) else (15.5 if (b_id % 3 == 0) else 16.8)
                wall_mat = (
                    palette["Mat_MTL_Heritage_RedBrick"]
                    if (b_id % 5 == 0)
                    else (palette["Mat_MTL_PierreGrise_Limestone"] if (b_id % 2 == 0) else palette["Mat_MTL_WarmBuff_Limestone"])
                )
                build_detailed_heritage_building(
                    b,
                    height=h,
                    mat_wall=wall_mat,
                    mat_trim=palette["Mat_MTL_PierreGrise_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                    mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_Window_Frame_Light"],
                    collection=col_owned,
                    prefix="Bldg_Owned",
                    add_mansard=(b_id % 3 == 0),
                )
        else:
            if b_id in custom_proxy_ids:
                continue
            h = 17.5 if (b_id % 2 == 0) else 15.5
            wall_mat = palette["Mat_MTL_PierreGrise_Limestone"] if (b_id % 2 == 0) else palette["Mat_MTL_WarmBuff_Limestone"]
            build_detailed_heritage_building(
                b,
                height=h,
                mat_wall=wall_mat,
                mat_trim=palette["Mat_MTL_PierreGrise_Limestone"],
                mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                mat_frame=palette["Mat_MTL_Window_Frame_Light"],
                collection=col_proxy,
                prefix="Bldg_Proxy",
                add_mansard=(b_id % 4 == 0),
            )

    build_context_proxies_0008(dossier, palette, col_proxy)

    setup_lighting_and_world(bpy.context.scene)
    render_cameras(dossier, col_root, iter_tag="iter3")

    blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.blend")
    tmp_blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}_tmp.blend")
    usdc_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.usdc")
    bpy.ops.wm.usd_export(filepath=usdc_path)
    bpy.context.preferences.filepaths.save_version = 0
    for stale in (tmp_blend_path, blend_path + "@", blend_path + "1"):
        if os.path.exists(stale):
            try:
                os.remove(stale)
            except Exception:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend_path, copy=True)
    try:
        os.replace(tmp_blend_path, blend_path)
    except Exception:
        shutil.copyfile(tmp_blend_path, blend_path)
    print(f"Saved {blend_path} and exported {usdc_path}")


if __name__ == "__main__":
    main()
