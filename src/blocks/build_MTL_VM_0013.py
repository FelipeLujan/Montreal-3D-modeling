"""
Headless Builder for City Block MTL-VM-0013 (AAA Poly Haven PBR)
(Courthouse Block — Palais de Justice de Montréal, Édifice Ernest-Cormier & Old Montreal North-East)
====================================================================================================
Constructs all 48 owned buildings inside `Block_MTL-VM-0013_Owned` (including the
18-storey Modernist Palais de Justice de Montréal with its Brutalist brise-soleil podium
and civic plaza, the Beaux-Arts/Art Deco Édifice Ernest-Cormier `way 92071709` with its
monumental colonnade and grand steps, AC Hotel / SpringHill Suites colonnaded loggia,
10-storey Édifice Métropole, and the historic Rue Sainte-Thérèse & Rue Saint-Gabriel
streetscapes) and 11 neighbor context buildings inside `Block_MTL-VM-0013_Context_Proxy`.

Uses verified 2K Poly Haven PBR textures in `assets/polyhaven/` (`sandstone_blocks_05`,
`castle_brick_02_red`, `cobblestone_floor_08`, `asphalt_02`), `kloppenheim_06_puresky_2k.hdr`,
and 3D scanned assets from `assets/montreal_kit.blend`.
"""
import os
import sys
import json
import math
import bpy
import bmesh
from mathutils import Vector, Euler

PROJECT_ROOT = r"C:\Users\Felipe\Documents\coding\montreal"
if os.path.join(PROJECT_ROOT, "src") not in sys.path:
    sys.path.append(os.path.join(PROJECT_ROOT, "src"))

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0013"
DOSSIER_PATH = os.path.join(PROJECT_ROOT, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(PROJECT_ROOT, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_BLOCKS_DIR = os.path.join(PROJECT_ROOT, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(PROJECT_ROOT, "output", "renders")
KIT_BLEND_PATH = os.path.join(PROJECT_ROOT, "assets", "montreal_kit.blend")
PH_DIR = os.path.join(PROJECT_ROOT, "assets", "polyhaven")


# ---------------------------------------------------------------------------
# 1. VERIFIED POLY HAVEN 2K PBR MATERIALS + COURSED ASHLAR MORTAR SHADERS
# ---------------------------------------------------------------------------
def build_ph_pbr_mat(name, diff_file, rough_file, nor_file, tint=(1.0, 1.0, 1.0, 1.0),
                     scale=0.28, rough_mult=1.0, normal_str=0.55, brick_grid=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    diff_path = os.path.join(PH_DIR, diff_file) if diff_file else ""
    rough_path = os.path.join(PH_DIR, rough_file) if rough_file else ""
    nor_path = os.path.join(PH_DIR, nor_file) if nor_file else ""

    base_color_out = None
    if diff_path and os.path.exists(diff_path):
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = bpy.data.images.load(diff_path, check_existing=True)
        tex_d.projection = 'BOX'
        tex_d.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])
        if tint != (1.0, 1.0, 1.0, 1.0):
            mix = nodes.new("ShaderNodeMix")
            mix.data_type = 'RGBA'
            mix.blend_type = 'MULTIPLY'
            mix.inputs["Factor"].default_value = 0.72
            mix.inputs[6].default_value = tint
            links.new(tex_d.outputs["Color"], mix.inputs[7])
            base_color_out = mix.outputs[2]
        else:
            base_color_out = tex_d.outputs["Color"]

    if brick_grid is not None:
        b_scale, b_w, b_h, mortar_col = brick_grid
        b_tex = nodes.new("ShaderNodeTexBrick")
        b_tex.offset = 0.5
        b_tex.inputs["Scale"].default_value = b_scale
        b_tex.inputs["Brick Width"].default_value = b_w
        b_tex.inputs["Row Height"].default_value = b_h
        b_tex.inputs["Mortar Size"].default_value = 0.018
        b_tex.inputs["Mortar Smooth"].default_value = 0.1
        b_tex.inputs["Color1"].default_value = tint
        b_tex.inputs["Color2"].default_value = (tint[0] * 0.90, tint[1] * 0.90, tint[2] * 0.90, 1.0)
        b_tex.inputs["Mortar"].default_value = mortar_col
        links.new(tex_coord.outputs["Object"], b_tex.inputs["Vector"])

        if base_color_out is not None:
            mix_b = nodes.new("ShaderNodeMix")
            mix_b.data_type = 'RGBA'
            mix_b.blend_type = 'MULTIPLY'
            mix_b.inputs["Factor"].default_value = 0.55
            links.new(base_color_out, mix_b.inputs[6])
            links.new(b_tex.outputs["Color"], mix_b.inputs[7])
            links.new(mix_b.outputs[2], bsdf.inputs["Base Color"])
        else:
            links.new(b_tex.outputs["Color"], bsdf.inputs["Base Color"])
    elif base_color_out is not None:
        links.new(base_color_out, bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = tint

    if rough_path and os.path.exists(rough_path):
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = bpy.data.images.load(rough_path, check_existing=True)
        tex_r.image.colorspace_settings.name = 'Non-Color'
        tex_r.projection = 'BOX'
        tex_r.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_r.inputs["Vector"])
        math_r = nodes.new("ShaderNodeMath")
        math_r.operation = 'MULTIPLY'
        math_r.inputs[1].default_value = rough_mult
        links.new(tex_r.outputs["Color"], math_r.inputs[0])
        links.new(math_r.outputs["Value"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.65

    if nor_path and os.path.exists(nor_path):
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = bpy.data.images.load(nor_path, check_existing=True)
        tex_n.image.colorspace_settings.name = 'Non-Color'
        tex_n.projection = 'BOX'
        tex_n.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal_str
        links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def create_solid_mat(name, color, roughness=0.45, metallic=0.0, ior=1.45):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = ior
    return mat


def create_block_palette():
    palette = kit.create_montreal_material_palette()

    # 1. Coursed Montreal Grey Ashlar Limestone (Édifice Ernest-Cormier & Vieux Palais de Justice)
    palette["Mat_Stone_Grey"] = build_ph_pbr_mat(
        "Mat_Stone_Grey",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint=(0.68, 0.70, 0.68, 1.0), scale=0.32, rough_mult=0.90, normal_str=0.45,
        brick_grid=(1.35, 0.90, 0.45, (0.36, 0.38, 0.36, 1.0))
    )
    # 2. Warm Buff Precast / Travertine Limestone (Palais de Justice Podium & 339882470)
    palette["Mat_Stone_Buff"] = build_ph_pbr_mat(
        "Mat_Stone_Buff",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint=(0.82, 0.78, 0.72, 1.0), scale=0.35, rough_mult=0.88, normal_str=0.42,
        brick_grid=(1.2, 1.10, 0.55, (0.48, 0.45, 0.42, 1.0))
    )
    # 3. Rugged Fieldstone Rubble Masonry (`moellons` — 626555172 Historic House & Garden Walls)
    palette["Mat_Stone_Rubble"] = build_ph_pbr_mat(
        "Mat_Stone_Rubble",
        "cobblestone_floor_08_Diffuse_2k.jpg",
        "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg",
        tint=(0.62, 0.60, 0.56, 1.0), scale=0.48, rough_mult=1.02, normal_str=1.55
    )
    # 4. Dressed Ashlar Quoin & Cornice Trim
    palette["Mat_Stone_Quoin"] = build_ph_pbr_mat(
        "Mat_Stone_Quoin",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint=(0.76, 0.75, 0.72, 1.0), scale=0.38, rough_mult=0.88, normal_str=0.40,
        brick_grid=(1.5, 0.85, 0.42, (0.42, 0.42, 0.40, 1.0))
    )
    # 5. Heritage Red Brick (AC Hotel / SpringHill Suites 610570818)
    palette["Mat_Red_Brick"] = build_ph_pbr_mat(
        "Mat_Red_Brick",
        "castle_brick_02_red_Diffuse_2k.jpg",
        "castle_brick_02_red_Rough_2k.jpg",
        "castle_brick_02_red_nor_gl_2k.jpg",
        tint=(0.68, 0.36, 0.30, 1.0), scale=0.38, rough_mult=0.95, normal_str=1.35
    )
    # 6. Warm Brown / Terracotta Brick & Spandrel (Édifice Métropole 190106260 & 161202612)
    palette["Mat_Brown_Brick"] = build_ph_pbr_mat(
        "Mat_Brown_Brick",
        "castle_brick_02_red_Diffuse_2k.jpg",
        "castle_brick_02_red_Rough_2k.jpg",
        "castle_brick_02_red_nor_gl_2k.jpg",
        tint=(0.52, 0.36, 0.26, 1.0), scale=0.35, rough_mult=0.90, normal_str=1.20
    )
    # 7. Cobblestone Crosswalk / Street & Asphalt Road
    palette["Mat_Cobble_Street"] = build_ph_pbr_mat(
        "Mat_Cobble_Street",
        "cobblestone_floor_08_Diffuse_2k.jpg",
        "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg",
        tint=(0.58, 0.56, 0.55, 1.0), scale=0.45, rough_mult=0.90, normal_str=1.45
    )
    palette["Mat_Asphalt"] = build_ph_pbr_mat(
        "Mat_Asphalt",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint=(0.36, 0.37, 0.39, 1.0), scale=0.28, rough_mult=0.92, normal_str=1.25
    )
    palette["Mat_Sidewalk"] = build_ph_pbr_mat(
        "Mat_Sidewalk",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint=(0.68, 0.67, 0.65, 1.0), scale=0.35, rough_mult=0.88, normal_str=0.85,
        brick_grid=(0.65, 1.4, 1.4, (0.34, 0.34, 0.33, 1.0))
    )
    # 8. Standing-Seam Metal / Slate Roof & Flat Bitumen Roof
    palette["Mat_Roof_Slate"] = build_ph_pbr_mat(
        "Mat_Roof_Slate",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint=(0.28, 0.32, 0.36, 1.0), scale=0.40, rough_mult=0.60, normal_str=1.10,
        brick_grid=(2.4, 0.32, 0.60, (0.14, 0.16, 0.18, 1.0))
    )
    palette["Mat_Roof_Flat"] = build_ph_pbr_mat(
        "Mat_Roof_Flat",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint=(0.32, 0.31, 0.29, 1.0), scale=0.32, rough_mult=0.95, normal_str=1.25
    )
    palette["Mat_Copper_Green"] = create_solid_mat("Mat_Copper_Green", (0.22, 0.48, 0.40, 1.0), roughness=0.38, metallic=0.65)
    palette["Mat_Glass_Dark"] = create_solid_mat("Mat_Glass_Dark", (0.02, 0.04, 0.06, 1.0), roughness=0.04, metallic=0.18, ior=1.52)
    palette["Mat_Glass_Warm"] = create_solid_mat("Mat_Glass_Warm", (0.28, 0.18, 0.10, 1.0), roughness=0.05, metallic=0.10, ior=1.52)
    palette["Mat_Frame_White"] = create_solid_mat("Mat_Frame_White", (0.88, 0.88, 0.86, 1.0), roughness=0.32)
    palette["Mat_Frame_Dark"] = create_solid_mat("Mat_Frame_Dark", (0.06, 0.07, 0.08, 1.0), roughness=0.30, metallic=0.45)
    palette["Mat_Granite_Black"] = create_solid_mat("Mat_Granite_Black", (0.08, 0.08, 0.09, 1.0), roughness=0.18, metallic=0.20)
    palette["Mat_Spandrel_Brown"] = create_solid_mat("Mat_Spandrel_Brown", (0.36, 0.25, 0.19, 1.0), roughness=0.38, metallic=0.15)
    palette["Mat_Wood_Oak"] = create_solid_mat("Mat_Wood_Oak", (0.48, 0.28, 0.12, 1.0), roughness=0.35)
    palette["Mat_Bin_Green"] = create_solid_mat("Mat_Bin_Green", (0.04, 0.18, 0.06, 1.0), roughness=0.35)
    palette["Mat_Iron_Black"] = create_solid_mat("Mat_Iron_Black", (0.03, 0.03, 0.04, 1.0), roughness=0.30, metallic=0.85)
    palette["Mat_Flag_Red"] = create_solid_mat("Mat_Flag_Red", (0.75, 0.06, 0.06, 1.0), roughness=0.55)
    palette["Mat_Sign_Blue"] = create_solid_mat("Mat_Sign_Blue", (0.10, 0.20, 0.48, 1.0), roughness=0.38)
    palette["Mat_Lawn_Green"] = create_solid_mat("Mat_Lawn_Green", (0.12, 0.26, 0.09, 1.0), roughness=0.85)
    return palette


def load_kit_assets():
    assets = {}
    if not os.path.exists(KIT_BLEND_PATH):
        return assets
    with bpy.data.libraries.load(KIT_BLEND_PATH, link=False) as (data_from, data_to):
        target_names = ["jacaranda_tree_LOD0", "street_lamp_01", "Master_Street_Bench"]
        data_to.objects = [n for n in target_names if n in data_from.objects]
    for obj in data_to.objects:
        if obj is not None:
            assets[obj.name] = obj
    return assets


# ---------------------------------------------------------------------------
# 2. GEOMETRY PRIMITIVES & ARCHITECTURAL HELPERS
# ---------------------------------------------------------------------------
def add_bevel(obj, width=0.02, segments=2):
    mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(35.0)


def create_box(name, center, size, rot_z, mat, col, bevel_w=0.015, cap_top=True, cap_bottom=True):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    if col.name.endswith("_Context_Proxy"):
        obj.hide_render = True
        obj.hide_viewport = True
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if not cap_top or not cap_bottom:
        faces_to_del = []
        for f in bm.faces:
            if not cap_top and f.normal.z > 0.8:
                faces_to_del.append(f)
            elif not cap_bottom and f.normal.z < -0.8:
                faces_to_del.append(f)
        if faces_to_del:
            bmesh.ops.delete(bm, geom=faces_to_del, context='FACES_ONLY')
    if abs(rot_z) > 1e-5:
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler((0.0, 0.0, rot_z), 'XYZ').to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        obj.data.materials.append(mat)
    if bevel_w > 0:
        add_bevel(obj, bevel_w)
    return obj


def create_cylinder(name, center, radius, depth, rot_euler, mat, col, segments=16):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    if col.name.endswith("_Context_Proxy"):
        obj.hide_render = True
        obj.hide_viewport = True
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=radius, radius2=radius, depth=depth)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler(rot_euler, 'XYZ').to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        obj.data.materials.append(mat)
    return obj


def create_extruded_polygon(name, pts_2d, z_min, z_max, mat, col, bevel_w=0.02, cap_top=True, cap_bottom=True):
    pts = list(pts_2d)
    if len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05:
        pts = pts[:-1]
    if len(pts) < 3:
        return None
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    if col.name.endswith("_Context_Proxy"):
        obj.hide_render = True
        obj.hide_viewport = True
    bm = bmesh.new()
    b_verts = [bm.verts.new((p[0], p[1], z_min)) for p in pts]
    face = bm.faces.new(b_verts)
    face.normal_update()
    if face.normal.z > 0:
        bmesh.ops.reverse_faces(bm, faces=[face])
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts_top = [v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0.0, 0.0, z_max - z_min), verts=verts_top)

    faces_to_delete = []
    if not cap_bottom or not cap_top:
        for f in bm.faces:
            avg_z = sum(v.co.z for v in f.verts) / len(f.verts)
            if not cap_bottom and avg_z <= z_min + 1e-3:
                faces_to_delete.append(f)
            elif not cap_top and avg_z >= z_max - 1e-3:
                faces_to_delete.append(f)
    if faces_to_delete:
        bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES_ONLY')

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        obj.data.materials.append(mat)
    if bevel_w > 0:
        add_bevel(obj, bevel_w)
    return obj


def compute_outward_normal(p1, p2, poly_pts):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-4:
        return (0.0, 1.0), 0.0
    nx, ny = dy / length, -dx / length
    area2 = 0.0
    n = len(poly_pts)
    for i in range(n):
        x1, y1 = poly_pts[i]
        x2, y2 = poly_pts[(i + 1) % n]
        area2 += (x1 * y2 - x2 * y1)
    if area2 < 0:
        nx, ny = -nx, -ny
    return (nx, ny), length


def add_window_bay(prefix, wx, wy, wz, w, h, rot_z, nx, ny, mat_stone, mat_frame, mat_glass, mat_iron, col,
                   arched=False, panes_x=2, balcony=False, bracketed=False):
    ux, uy = math.cos(rot_z), math.sin(rot_z)
    # Deep 0.42m architectural reveal: jambs, lintel/cornice & sill project outward to +0.26m..+0.34m while glass sits at +0.03m
    create_box(f"{prefix}_RevealTop", (wx + nx * 0.20, wy + ny * 0.20, wz + h * 0.5 + 0.11), (w + 0.34, 0.46, 0.22), rot_z, mat_stone, col)
    create_box(f"{prefix}_Sill", (wx + nx * 0.23, wy + ny * 0.23, wz - h * 0.5 - 0.09), (w + 0.40, 0.52, 0.18), rot_z, mat_stone, col)
    for s_side in (-1.0, 1.0):
        jx = wx + s_side * (w * 0.5 + 0.09) * ux + nx * 0.17
        jy = wy + s_side * (w * 0.5 + 0.09) * uy + ny * 0.17
        create_box(f"{prefix}_Jamb_{int(s_side)}", (jx, jy, wz), (0.18, 0.38, h + 0.04), rot_z, mat_stone, col)
        if bracketed:
            bx_c = wx + s_side * (w * 0.38) * ux + nx * 0.22
            by_c = wy + s_side * (w * 0.38) * uy + ny * 0.22
            create_box(f"{prefix}_Corbel_{int(s_side)}", (bx_c, by_c, wz - h * 0.5 - 0.24), (0.14, 0.32, 0.22), rot_z, mat_stone, col)

    create_box(f"{prefix}_Glass", (wx + nx * 0.03, wy + ny * 0.03, wz), (w, 0.05, h), rot_z, mat_glass, col, bevel_w=0.0)

    for m_i in range(panes_x + 1):
        frac = -0.5 + m_i / float(panes_x)
        mx = wx + frac * (w - 0.08) * ux + nx * 0.08
        my = wy + frac * (w - 0.08) * uy + ny * 0.08
        create_box(f"{prefix}_Mullion_{m_i}", (mx, my, wz), (0.065, 0.10, h), rot_z, mat_frame, col, bevel_w=0.005)
    for t_frac in (-0.48, 0.0, 0.48):
        create_box(f"{prefix}_Transom_{int(t_frac*100)}", (wx + nx * 0.08, wy + ny * 0.08, wz + t_frac * h), (w, 0.10, 0.06), rot_z, mat_frame, col, bevel_w=0.005)

    if arched:
        # Multi-segment Roman arch hood + recessed dark arched fanlight + keystone
        create_box(f"{prefix}_ArchHood1", (wx + nx * 0.22, wy + ny * 0.22, wz + h * 0.5 + 0.24), (w * 0.82, 0.44, 0.22), rot_z, mat_stone, col)
        create_box(f"{prefix}_ArchHood2", (wx + nx * 0.22, wy + ny * 0.22, wz + h * 0.5 + 0.40), (w * 0.54, 0.44, 0.20), rot_z, mat_stone, col)
        create_box(f"{prefix}_ArchGlass", (wx + nx * 0.04, wy + ny * 0.04, wz + h * 0.5 + 0.22), (w * 0.72, 0.06, 0.28), rot_z, mat_glass, col, bevel_w=0.0)
        create_box(f"{prefix}_Keystone", (wx + nx * 0.26, wy + ny * 0.26, wz + h * 0.5 + 0.44), (0.32, 0.48, 0.36), rot_z, mat_stone, col)

    if balcony and mat_iron:
        rail_z = wz - h * 0.5 + 0.48
        create_box(f"{prefix}_BalcTop", (wx + nx * 0.24, wy + ny * 0.24, rail_z + 0.42), (w + 0.06, 0.05, 0.04), rot_z, mat_iron, col, bevel_w=0.0)
        create_box(f"{prefix}_BalcBot", (wx + nx * 0.24, wy + ny * 0.24, rail_z - 0.38), (w + 0.06, 0.05, 0.04), rot_z, mat_iron, col, bevel_w=0.0)
        n_bars = max(6, int(w / 0.20))
        for b_i in range(n_bars):
            bf = -0.46 + 0.92 * (b_i / float(max(1, n_bars - 1)))
            bx = wx + bf * w * ux + nx * 0.24
            by = wy + bf * w * uy + ny * 0.24
            create_box(f"{prefix}_BalcBar_{b_i}", (bx, by, rail_z), (0.025, 0.025, 0.78), rot_z, mat_iron, col, bevel_w=0.0)


def inset_polygon_2d(pts, inset_dist):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out = []
    for p in pts:
        vx, vy = p[0] - cx, p[1] - cy
        d = math.hypot(vx, vy)
        scale = max(0.1, (d - inset_dist) / max(d, 1e-4))
        out.append([cx + vx * scale, cy + vy * scale])
    return out


# ---------------------------------------------------------------------------
# 3. LANDMARK BUILDERS: PALAIS DE JUSTICE (20919177) & ÉDIFICE ERNEST-CORMIER (92071709)
# ---------------------------------------------------------------------------
def build_palais_de_justice_and_cormier(palette, owned_col):
    mat_grey = palette["Mat_Stone_Grey"]
    mat_buff = palette["Mat_Stone_Buff"]
    mat_quoin = palette["Mat_Stone_Quoin"]
    mat_glass = palette["Mat_Glass_Dark"]
    mat_dark = palette["Mat_Frame_Dark"]
    mat_iron = palette["Mat_Iron_Black"]
    mat_copper = palette["Mat_Copper_Green"]
    mat_oak = palette["Mat_Wood_Oak"]
    mat_white = palette["Mat_Frame_White"]
    mat_flat = palette["Mat_Roof_Flat"]

    # --- A. PALAIS DE JUSTICE DE MONTRÉAL (1 Rue Notre-Dame Est, ID 20919177) ---
    podium_pts = [[61.455, 187.495], [16.735, 215.615], [-28.445, 242.665], [17.726, 319.754], [61.572, 293.494], [105.777, 261.501]]
    podium_base_inset = inset_polygon_2d(podium_pts, 1.8)
    podium_glass_inset = inset_polygon_2d(podium_pts, 0.45)

    # 1. Deeply recessed ground-floor dark colonnade core (z = 0 to 4.8m) + 3-storey Brutalist Travertine Podium
    create_extruded_polygon("PDJ_DarkColonnade_Base", podium_base_inset, 0.0, 4.8, mat_dark, owned_col, bevel_w=0.02, cap_top=False)
    create_extruded_polygon("PDJ_Podium_Slab_Lower", podium_pts, 4.6, 5.8, mat_buff, owned_col, bevel_w=0.03, cap_bottom=False, cap_top=False)
    create_extruded_polygon("PDJ_Podium_GlassCore", podium_glass_inset, 5.8, 15.2, mat_glass, owned_col, bevel_w=0.0, cap_bottom=False, cap_top=False)
    create_extruded_polygon("PDJ_Podium_Slab_Upper", podium_pts, 15.2, 16.8, mat_buff, owned_col, bevel_w=0.03, cap_bottom=False, cap_top=False)
    create_extruded_polygon("PDJ_Podium_RoofDeck", podium_glass_inset, 16.8, 17.0, mat_flat, owned_col, bevel_w=0.01, cap_bottom=False)

    # Vertical Precast Sun-Breaker Fins (`brise-soleil`) + Ground Colonnade Pillars around all 4 sides of Podium
    n_pod = len(podium_pts)
    for p_idx in range(n_pod):
        pP1, pP2 = podium_pts[p_idx], podium_pts[(p_idx + 1) % n_pod]
        (nxP, nyP), lenP = compute_outward_normal(pP1, pP2, podium_pts)
        if lenP < 8.0:
            continue
        dxP, dyP = pP2[0] - pP1[0], pP2[1] - pP1[1]
        rotP = math.atan2(dyP, dxP)
        n_fins = max(6, int(lenP / 2.3))
        for f_i in range(n_fins):
            ft = (f_i + 0.5) / float(n_fins)
            fx, fy = pP1[0] + ft * dxP, pP1[1] + ft * dyP
            create_box(f"PDJ_PodFin_{p_idx}_{f_i}", (fx - nxP * 0.12, fy - nyP * 0.12, 10.5), (0.34, 0.68, 9.6), rotP, mat_buff, owned_col)
            if f_i % 3 == 0:
                create_box(f"PDJ_ColPillar_{p_idx}_{f_i}", (fx - nxP * 0.55, fy - nyP * 0.55, 2.35), (0.88, 0.88, 4.7), rotP, mat_buff, owned_col)
                if p_idx in (0, 4, 5):
                    create_cylinder(f"PDJ_Bollard_{p_idx}_{f_i}", (fx + nxP * 2.2, fy + nyP * 2.2, 0.55), 0.16, 1.1, (0, 0, 0), mat_iron, owned_col, segments=12)

    # Charles Daudelin's 1973 Brutalist Bronze Sculpture `Allegrocube` on the Palais de Justice Main Plaza
    create_box("PDJ_Allegrocube_Pedestal", (72.0, 198.0, 0.6), (2.4, 2.4, 1.2), 0.9, mat_quoin, owned_col)
    create_box("PDJ_Allegrocube_Bronze", (72.0, 198.0, 2.6), (2.8, 2.8, 2.8), 1.5, mat_iron, owned_col, bevel_w=0.05)

    # 2. 18-Storey Modernist Palais de Justice Main Tower (ZERO Z-fighting: glass core inset by 0.55m!)
    tower_pts = [[56.0, 195.0], [2.0, 228.0], [34.0, 282.0], [88.0, 249.0]]
    tower_core_pts = inset_polygon_2d(tower_pts, 0.55)
    create_extruded_polygon("PDJ_Tower_GlassCore", tower_core_pts, 16.8, 71.5, mat_glass, owned_col, bevel_w=0.0)

    # Horizontal Precast Spandrel Bands on every floor (projecting 0.55m proud of glass core -> zero Z-fighting!)
    for fl_z in range(19, 69, 3):
        create_extruded_polygon(f"PDJ_Tower_Spandrel_{fl_z}", tower_pts, fl_z, fl_z + 1.25, mat_buff, owned_col, bevel_w=0.02)
    create_extruded_polygon("PDJ_Tower_Crown", tower_pts, 68.2, 72.5, mat_buff, owned_col, bevel_w=0.03, cap_bottom=False)
    create_extruded_polygon("PDJ_Tower_RoofDeck", tower_core_pts, 72.5, 72.8, mat_flat, owned_col, bevel_w=0.01, cap_bottom=False)

    # Vertical Precast Mullions on all 4 facades of the 18-storey Tower
    for t_idx in range(4):
        t1, t2 = tower_pts[t_idx], tower_pts[(t_idx + 1) % 4]
        (nxt, nyt), lent = compute_outward_normal(t1, t2, tower_pts)
        dxt, dyt = t2[0] - t1[0], t2[1] - t1[1]
        rott = math.atan2(dyt, dxt)
        n_tmul = max(8, int(lent / 3.6))
        for m_i in range(n_tmul + 1):
            mt = m_i / float(n_tmul)
            mx_t, my_t = t1[0] + mt * dxt, t1[1] + mt * dyt
            create_box(f"PDJ_Tower_Mullion_{t_idx}_{m_i}", (mx_t - nxt * 0.22, my_t - nyt * 0.22, 43.5), (0.32, 0.42, 53.0), rott, mat_buff, owned_col)

    # --- B. ÉDIFICE ERNEST-CORMIER / VIEUX PALAIS DE JUSTICE WING (way 92071709, 100-155 Rue Notre-Dame Est) ---
    cormier_pts = [
        [174.16, 310.27], [231.76, 275.21], [223.58, 255.66], [222.51, 256.24],
        [210.08, 229.03], [211.3, 228.41], [202.33, 209.93], [137.19, 250.55],
        [138.09, 252.32], [136.65, 253.18], [154.52, 281.18], [171.76, 309.19], [172.93, 308.48]
    ]
    cormier_attic_pts = inset_polygon_2d(cormier_pts, 1.4)
    cormier_roof_pts = inset_polygon_2d(cormier_pts, 2.2)

    create_extruded_polygon("Cormier_Plinth_Base", cormier_pts, 0.0, 1.35, mat_quoin, owned_col, bevel_w=0.02)
    create_extruded_polygon("Cormier_Main_Body", cormier_pts, 1.35, 21.5, mat_grey, owned_col, bevel_w=0.03, cap_top=False)
    create_extruded_polygon("Cormier_Parapet_Band", cormier_pts, 21.5, 22.4, mat_quoin, owned_col, bevel_w=0.03, cap_bottom=False)
    create_extruded_polygon("Cormier_Attic_Tier", cormier_attic_pts, 22.4, 25.4, mat_quoin, owned_col, bevel_w=0.03, cap_bottom=False)
    create_extruded_polygon("Cormier_Main_RoofDeck", cormier_roof_pts, 25.4, 25.7, mat_flat, owned_col, bevel_w=0.01, cap_bottom=False)

    # Stepped Art Deco Clerestory & Patinated Green Copper Dome/Cupola + Roof Pavilions (for Overview Snapshot!)
    rot_cormier = math.radians(-32.0)
    create_box("Cormier_Central_Clerestory", (184.0, 260.0, 27.2), (38.0, 20.0, 3.2), rot_cormier, mat_quoin, owned_col)
    create_box("Cormier_Copper_MainRoof", (184.0, 260.0, 29.8), (34.0, 16.5, 2.2), rot_cormier, mat_copper, owned_col)
    create_cylinder("Cormier_Octagonal_Drum", (184.0, 260.0, 31.8), 6.2, 2.8, (0, 0, 0), mat_quoin, owned_col, segments=8)
    create_cylinder("Cormier_Copper_Dome", (184.0, 260.0, 34.2), 5.8, 2.6, (0, 0, 0), mat_copper, owned_col, segments=8)
    create_cylinder("Cormier_Copper_Lantern", (184.0, 260.0, 36.2), 2.1, 2.2, (0, 0, 0), mat_copper, owned_col, segments=8)
    create_box("Cormier_Copper_Pavilion_N", (174.0, 286.0, 27.4), (8.5, 8.5, 3.8), rot_cormier, mat_copper, owned_col)
    create_box("Cormier_Copper_Pavilion_S", (196.0, 236.0, 27.4), (8.5, 8.5, 3.8), rot_cormier, mat_copper, owned_col)

    # Full 4-Sided Beaux-Arts Fenestration, Cornices, Portals & Colonnades around ALL perimeter edges of 92071709
    n_cpts = len(cormier_pts)
    for e_idx in range(n_cpts):
        c1, c2 = cormier_pts[e_idx], cormier_pts[(e_idx + 1) % n_cpts]
        (nxc, nyc), lenc = compute_outward_normal(c1, c2, cormier_pts)
        if lenc < 6.0:
            continue
        dxc, dyc = c2[0] - c1[0], c2[1] - c1[1]
        rotc = math.atan2(dyc, dxc)
        ux_c, uy_c = dxc / lenc, dyc / lenc
        mxc, myc = (c1[0] + c2[0]) * 0.5, (c1[1] + c2[1]) * 0.5

        # Continuous projecting 1st-floor rusticated band (z = 4.2m), 2nd-floor cornice (z = 8.4m), and dentil roof cornice (z = 21.3m)
        create_box(f"Cormier_E{e_idx}_Band1", (mxc + nxc * 0.22, myc + nyc * 0.22, 4.25), (lenc + 0.3, 0.44, 0.36), rotc, mat_quoin, owned_col, cap_top=False, cap_bottom=False)
        create_box(f"Cormier_E{e_idx}_MidCornice", (mxc + nxc * 0.36, myc + nyc * 0.36, 8.45), (lenc + 0.5, 0.68, 0.55), rotc, mat_quoin, owned_col, cap_top=False, cap_bottom=False)
        create_box(f"Cormier_E{e_idx}_TopCornice", (mxc + nxc * 0.48, myc + nyc * 0.48, 21.35), (lenc + 0.7, 0.88, 0.68), rotc, mat_quoin, owned_col, cap_top=False, cap_bottom=False)

        # Dentil blocks under the overhanging roof cornice
        n_dentils = max(8, int(lenc / 1.4))
        for d_i in range(n_dentils):
            dt = (d_i + 0.5) / float(n_dentils)
            dx_d, dy_d = c1[0] + dt * dxc, c1[1] + dt * dyc
            create_box(f"Cormier_E{e_idx}_Dentil_{d_i}", (dx_d + nxc * 0.38, dy_d + nyc * 0.38, 20.85), (0.45, 0.55, 0.36), rotc, mat_quoin, owned_col)

        n_bays = max(2, int(lenc / 5.0))
        for b_i in range(n_bays):
            bt = (b_i + 0.5) / float(n_bays)
            wx, wy = c1[0] + bt * dxc, c1[1] + bt * dyc

            # Vertical limestone pilaster between bays
            if b_i > 0:
                pt_pil = b_i / float(n_bays)
                px_p, py_p = c1[0] + pt_pil * dxc, c1[1] + pt_pil * dyc
                create_box(f"Cormier_E{e_idx}_Pilaster_{b_i}", (px_p + nxc * 0.14, py_p + nyc * 0.14, 14.8), (0.68, 0.30, 12.2), rotc, mat_quoin, owned_col)

            # On SE facade facing Camera 2 (`e_idx == 5`: (211.3, 228.41) -> (202.33, 209.93)), place the recessed Stone Entrance Portal + Oak Door + White Globe Wall Sconce!
            if e_idx == 5 and b_i == 1:
                create_box(f"Cormier_E{e_idx}_PortalSurround", (wx + nxc * 0.26, wy + nyc * 0.26, 2.15), (2.55, 0.54, 4.2), rotc, mat_quoin, owned_col)
                create_box(f"Cormier_E{e_idx}_PortalLint", (wx + nxc * 0.38, wy + nyc * 0.38, 4.15), (2.85, 0.72, 0.45), rotc, mat_quoin, owned_col)
                create_box(f"Cormier_E{e_idx}_DoorReveal", (wx + nxc * 0.04, wy + nyc * 0.04, 1.95), (1.85, 0.12, 3.6), rotc, mat_dark, owned_col)
                create_box(f"Cormier_E{e_idx}_OakDoor", (wx + nxc * 0.10, wy + nyc * 0.10, 1.75), (1.65, 0.12, 3.05), rotc, mat_oak, owned_col)
                create_box(f"Cormier_E{e_idx}_DoorGlass", (wx + nxc * 0.14, wy + nyc * 0.14, 1.95), (1.15, 0.08, 1.85), rotc, mat_glass, owned_col)
                create_box(f"Cormier_E{e_idx}_Step1", (wx + nxc * 0.34, wy + nyc * 0.34, 0.16), (2.45, 0.52, 0.32), rotc, mat_quoin, owned_col)
                create_box(f"Cormier_E{e_idx}_Step2", (wx + nxc * 0.52, wy + nyc * 0.52, 0.08), (2.65, 0.42, 0.16), rotc, mat_quoin, owned_col)
                # White Glass Globe Wall Sconce on Scrolled Iron Bracket next to portal (prominent in View 2!)
                for s_dir in (-1.0, 1.0):
                    lx_s = wx + s_dir * 1.65 * ux_c + nxc * 0.38
                    ly_s = wy + s_dir * 1.65 * uy_c + nyc * 0.38
                    create_box(f"Cormier_SconceBracket_{int(s_dir)}", (lx_s, ly_s, 2.85), (0.14, 0.46, 0.24), rotc, mat_iron, owned_col)
                    create_cylinder(f"Cormier_SconceGlobe_{int(s_dir)}", (lx_s + nxc * 0.18, ly_s + nyc * 0.18, 3.18), 0.26, 0.46, (0, 0, 0), mat_white, owned_col, segments=14)
            else:
                # Ground-floor recessed window with black wrought-iron vertical security grille
                add_window_bay(f"Cormier_E{e_idx}_GndWin_{b_i}", wx, wy, 2.25, 1.95, 2.45, rotc, nxc, nyc, mat_quoin, mat_dark, mat_glass, mat_iron, owned_col, panes_x=2, balcony=True)

            # 2nd floor paired mezzanine window (z = 6.1m) with bracketed sill
            add_window_bay(f"Cormier_E{e_idx}_Fl2Win_{b_i}", wx, wy, 6.15, 2.15, 2.35, rotc, nxc, nyc, mat_quoin, mat_dark, mat_glass, None, owned_col, panes_x=2, bracketed=True)
            # 3rd & 4th floor tall courtroom windows with bracketed sills & projecting pediments (z = 11.5m & z = 16.9m)
            for fl_i, fz in enumerate([11.5, 16.9]):
                add_window_bay(f"Cormier_E{e_idx}_TallWin_{b_i}_{fl_i}", wx, wy, fz, 2.10, 3.65, rotc, nxc, nyc, mat_quoin, mat_dark, mat_glass, None, owned_col, panes_x=2, bracketed=True)
            # Attic tier window (z = 23.8m)
            add_window_bay(f"Cormier_E{e_idx}_AtticWin_{b_i}", wx - nxc * 1.4, wy - nyc * 1.4, 23.8, 1.65, 1.55, rotc, nxc, nyc, mat_quoin, mat_dark, mat_glass, None, owned_col, panes_x=2)

        # Monumental Colonnade & Grand Staircase on SW Main Facade (e_idx == 6: Rue Notre-Dame Est) and NW Facade (e_idx == 9/10)
        if e_idx in (6, 9, 10) and lenc > 25.0:
            for col_i in range(8):
                ct = 0.14 + 0.72 * (col_i / 7.0)
                cx_c, cy_c = c1[0] + ct * dxc, c1[1] + ct * dyc
                create_cylinder(f"Cormier_E{e_idx}_Col_{col_i}", (cx_c + nxc * 0.55, cy_c + nyc * 0.55, 14.5), 0.58, 12.2, (0, 0, 0), mat_quoin, owned_col, segments=16)
            if e_idx == 6:
                for st_i in range(6):
                    st_d = 0.8 + st_i * 0.55
                    st_h = 1.35 - st_i * 0.20
                    create_box(f"Cormier_GrandStep_{st_i}", (mxc + nxc * st_d, myc + nyc * st_d, st_h * 0.5), (32.0, 0.65, st_h), rotc, mat_quoin, owned_col)


# ---------------------------------------------------------------------------
# 4. BESPOKE HERO FACADES FOR THE 4 STREET VIEW CAMERAS
# ---------------------------------------------------------------------------
def build_hero_facades(palette, col):
    mat_grey = palette["Mat_Stone_Grey"]
    mat_buff = palette["Mat_Stone_Buff"]
    mat_rubble = palette["Mat_Stone_Rubble"]
    mat_quoin = palette["Mat_Stone_Quoin"]
    mat_brick = palette["Mat_Red_Brick"]
    mat_brown_brick = palette["Mat_Brown_Brick"]
    mat_spandrel = palette["Mat_Spandrel_Brown"]
    mat_granite = palette["Mat_Granite_Black"]
    mat_slate = palette["Mat_Roof_Slate"]
    mat_white = palette["Mat_Frame_White"]
    mat_dark = palette["Mat_Frame_Dark"]
    mat_glass = palette["Mat_Glass_Dark"]
    mat_warm = palette["Mat_Glass_Warm"]
    mat_iron = palette["Mat_Iron_Black"]
    mat_flag = palette["Mat_Flag_Red"]
    mat_blue = palette["Mat_Sign_Blue"]
    mat_bin = palette["Mat_Bin_Green"]
    mat_lawn = palette["Mat_Lawn_Green"]
    mat_oak = palette["Mat_Wood_Oak"]

    # =========================================================================
    # HERO 1: `Rue_NotreDame_Main_Plaza.jpg` (SpringHill Suites 610570818 on Right & 339882470 on Left)
    # =========================================================================
    # Exact SW Facade of 610570818 along Rue Saint-Jean-Baptiste: (180.996, 154.220) -> (126.644, 184.948)
    pH1, pH2 = (180.996, 154.220), (126.644, 184.948)
    dxH, dyH = pH2[0] - pH1[0], pH2[1] - pH1[1]
    lenH = math.hypot(dxH, dyH)
    rotH = math.atan2(dyH, dxH)
    uxH, uyH = dxH / lenH, dyH / lenH
    # Outward SW normal pointing toward Rue Saint-Jean-Baptiste and Camera 1: (-0.492, -0.870)
    nxH, nyH = -dyH / lenH, dxH / lenH

    # 1. Deep Ground-Floor Colonnaded Loggia along SW facade (t = 0.04 to 0.72, length = 42.5m)
    mxL, myL = pH1[0] + 0.38 * dxH, pH1[1] + 0.38 * dyH
    # Continuous buff limestone entablature fascia beam above colonnade (z = 4.55m to 5.45m)
    create_box("H1_SpringHill_Entablature", (mxL + nxH * 0.28, myL + nyH * 0.28, 5.00), (43.5, 0.65, 0.92), rotH, mat_buff, col)
    create_box("H1_SpringHill_CorniceCap", (mxL + nxH * 0.36, myL + nyH * 0.36, 5.52), (44.0, 0.78, 0.22), rotH, mat_quoin, col)
    # Recessed inner loggia shadow wall & warm hotel lobby glazing behind the brick colonnade piers
    create_box("H1_SpringHill_LoggiaShadow", (mxL + nxH * 0.03, myL + nyH * 0.03, 2.30), (42.5, 0.08, 4.50), rotH, mat_dark, col, bevel_w=0.0, cap_top=False, cap_bottom=False)
    create_box("H1_SpringHill_LoggiaSoffit", (mxL + nxH * 0.16, myL + nyH * 0.16, 4.48), (42.5, 0.45, 0.14), rotH, mat_buff, col, cap_top=False, cap_bottom=False)

    # 3D Dark-Bronze `SPRINGHILL` Block Lettering on the limestone entablature in foreground of View 1 (t = 0.13 to 0.26)
    for l_idx in range(10):
        lt = 0.135 + l_idx * 0.0125
        lx_let, ly_let = pH1[0] + lt * dxH, pH1[1] + lt * dyH
        create_box(f"H1_SpringHill_Letter_{l_idx}", (lx_let + nxH * 0.63, ly_let + nyH * 0.63, 4.98), (0.48, 0.10, 0.42), rotH, mat_iron, col, bevel_w=0.005)

    # 9 Square Red-Brick Colonnade Piers with Buff Limestone Plinths & Capitals + Wrought-Iron Fence + Hanging Lanterns
    n_piers = 9
    for p_i in range(n_piers):
        pt = 0.05 + p_i * 0.082
        px, py = pH1[0] + pt * dxH, pH1[1] + pt * dyH
        create_box(f"H1_PierBase_{p_i}", (px + nxH * 0.30, py + nyH * 0.30, 0.35), (1.12, 0.68, 0.70), rotH, mat_buff, col)
        create_box(f"H1_BrickPier_{p_i}", (px + nxH * 0.28, py + nyH * 0.28, 2.35), (0.98, 0.62, 3.50), rotH, mat_brick, col)
        create_box(f"H1_PierCap_{p_i}", (px + nxH * 0.32, py + nyH * 0.32, 4.30), (1.14, 0.72, 0.48), rotH, mat_buff, col)

        # Classical wall-mounted streetlamp bracket on foreground piers
        if p_i in (1, 4):
            create_box(f"H1_PierLampArm_{p_i}", (px + nxH * 0.68, py + nyH * 0.68, 3.45), (0.10, 0.48, 0.12), rotH, mat_iron, col)
            create_cylinder(f"H1_PierLampGlobe_{p_i}", (px + nxH * 0.85, py + nyH * 0.85, 3.72), 0.18, 0.38, (0, 0, 0), mat_white, col, segments=10)

        if p_i < n_piers - 1:
            mid_t = pt + 0.041
            fx, fy = pH1[0] + mid_t * dxH, pH1[1] + mid_t * dyH
            # Recessed hotel lobby windows behind the colonnade bay
            create_box(f"H1_LobbyGlass_{p_i}", (fx + nxH * 0.07, fy + nyH * 0.07, 2.25), (3.4, 0.06, 3.2), rotH, mat_warm if p_i % 2 == 0 else mat_glass, col, bevel_w=0.0)
            for lm_i in (-1, 0, 1):
                create_box(f"H1_LobbyMul_{p_i}_{lm_i}", (fx + lm_i * 1.05 * uxH + nxH * 0.10, fy + lm_i * 1.05 * uyH + nyH * 0.10, 2.25), (0.07, 0.08, 3.2), rotH, mat_dark, col)
            # Black wrought-iron courtyard picket fence between brick piers
            create_box(f"H1_FenceTop_{p_i}", (fx + nxH * 0.30, fy + nyH * 0.30, 1.75), (4.1, 0.06, 0.05), rotH, mat_iron, col, bevel_w=0.0)
            create_box(f"H1_FenceBot_{p_i}", (fx + nxH * 0.30, fy + nyH * 0.30, 0.35), (4.1, 0.06, 0.05), rotH, mat_iron, col, bevel_w=0.0)
            for b_k in range(14):
                bt = pt + 0.008 + b_k * 0.0050
                bx_f, by_f = pH1[0] + bt * dxH, pH1[1] + bt * dyH
                create_box(f"H1_Picket_{p_i}_{b_k}", (bx_f + nxH * 0.30, by_f + nyH * 0.30, 1.05), (0.03, 0.03, 1.45), rotH, mat_iron, col, bevel_w=0.0)
            # Hanging glowing lantern inside loggia bay
            create_cylinder(f"H1_Lantern_{p_i}", (fx + nxH * 0.18, fy + nyH * 0.18, 3.85), 0.20, 0.45, (0, 0, 0), mat_white, col, segments=8)

    # Two Red-and-White Canadian Flags on angled flagpoles above the 1st-floor entablature (t = 0.24 and t = 0.30)
    for flg_i, ft in enumerate([0.24, 0.30]):
        fx, fy = pH1[0] + ft * dxH, pH1[1] + ft * dyH
        create_box(f"H1_FlagPole_{flg_i}", (fx + nxH * 0.75, fy + nyH * 0.75, 6.35), (0.06, 1.45, 0.06), rotH, mat_white, col)
        create_box(f"H1_RedFlag_{flg_i}", (fx + nxH * 1.15, fy + nyH * 1.15, 5.85), (0.08, 0.95, 1.05), rotH, mat_flag, col)

    # All 5 Upper Storeys of Recessed Casement Windows + Limestone Sills + Under-Window AC Louver Grilles on 610570818
    create_box("H1_SpringHill_TopCornice", (pH1[0] + 0.5 * dxH + nxH * 0.32, pH1[1] + 0.5 * dyH + nyH * 0.32, 21.25), (lenH + 0.4, 0.62, 0.48), rotH, mat_buff, col)
    n_hcols = 15
    for col_i in range(n_hcols):
        ct = 0.04 + 0.92 * (col_i / float(n_hcols - 1))
        wx, wy = pH1[0] + ct * dxH, pH1[1] + ct * dyH
        for fl_i, fz in enumerate([7.2, 10.4, 13.6, 16.8, 19.8]):
            add_window_bay(f"H1_610_Win_{col_i}_{fl_i}", wx, wy, fz, 2.05, 1.95, rotH, nxH, nyH, mat_buff, mat_white, mat_glass, None, col, panes_x=3)
            # Dark metal PTAC air-conditioner louver grille beneath each hotel window
            create_box(f"H1_610_ACGrille_{col_i}_{fl_i}", (wx + nxH * 0.08, wy + nyH * 0.08, fz - 1.32), (1.35, 0.14, 0.42), rotH, mat_dark, col)

    # =========================================================================
    # HERO 2: `Edifice_Ernest_Cormier_Columns.jpg` (End of Rue Sainte-Thérèse Heritage Stone House + 10-Storey Beaux-Arts Tower + Left Hedge Wall)
    # =========================================================================
    # 1. 2-Storey Heritage Fieldstone Building with Steep Slate Pitched Roof & 3 Gabled Dormers directly at the end of Rue Sainte-Thérèse
    # Visible across (216.0, 186.5) -> (188.0, 199.5), facing NE (+0.45, +0.89) toward Camera 2 at (216.2, 232.0)!
    pM1, pM2 = (215.5, 186.8), (189.5, 198.8)
    dxM, dyM = pM2[0] - pM1[0], pM2[1] - pM1[1]
    lenM = math.hypot(dxM, dyM)
    rotM = math.atan2(dyM, dxM)
    nxM, nyM = dyM / lenM, -dxM / lenM  # Outward NE normal (+0.42, +0.91) facing Camera 2!
    if nyM < 0:
        nxM, nyM = -nxM, -nyM
    mxM, myM = (pM1[0] + pM2[0]) * 0.5, (pM1[1] + pM2[1]) * 0.5

    create_box("H2_EndHouse_Body", (mxM - nxM * 4.2, myM - nyM * 4.2, 3.4), (lenM, 8.6, 6.8), rotM, mat_rubble, col)
    create_box("H2_EndHouse_Cornice", (mxM + nxM * 0.22, myM + nyM * 0.22, 6.85), (lenM + 0.4, 0.52, 0.35), rotM, mat_quoin, col)
    # Stepped/sloped dark-slate pitched roof rising from z = 6.9m to 10.8m
    for r_step in range(5):
        r_z = 7.25 + r_step * 0.72
        r_d = 8.2 - r_step * 1.35
        create_box(f"H2_EndHouse_RoofTier_{r_step}", (mxM - nxM * 4.2, myM - nyM * 4.2, r_z), (lenM + 0.2, r_d, 0.78), rotM, mat_slate, col)
    # 4 Gabled Slate Dormers with multi-pane windows facing Camera 2
    for d_i, dt in enumerate([0.18, 0.39, 0.61, 0.82]):
        dx_d, dy_d = pM1[0] + dt * dxM, pM1[1] + dt * dyM
        create_box(f"H2_EndDormer_{d_i}", (dx_d - nxM * 1.1, dy_d - nyM * 1.1, 8.35), (1.85, 2.2, 2.3), rotM, mat_slate, col)
        create_box(f"H2_EndDormerCap_{d_i}", (dx_d - nxM * 0.9, dy_d - nyM * 0.9, 9.60), (1.45, 1.45, 0.28), rotM, mat_quoin, col, cap_top=False, cap_bottom=False)
        add_window_bay(f"H2_EndDormerWin_{d_i}", dx_d - nxM * 0.05, dy_d - nyM * 0.05, 8.25, 1.25, 1.55, rotM, nxM, nyM, mat_quoin, mat_dark, mat_glass, None, col, panes_x=2)
    # 1st & 2nd floor windows + central arched wooden carriageway door on the heritage house
    for w_i, wt in enumerate([0.15, 0.32, 0.50, 0.68, 0.85]):
        wx, wy = pM1[0] + wt * dxM, pM1[1] + wt * dyM
        if w_i == 2:
            add_window_bay("H2_EndHouse_ArchDoor", wx, wy, 2.15, 2.35, 3.10, rotM, nxM, nyM, mat_quoin, mat_dark, mat_oak, None, col, arched=True, panes_x=2)
        else:
            add_window_bay(f"H2_EndHouse_GndW_{w_i}", wx, wy, 2.05, 1.55, 2.15, rotM, nxM, nyM, mat_quoin, mat_dark, mat_glass, None, col, panes_x=2)
        add_window_bay(f"H2_EndHouse_Fl2W_{w_i}", wx, wy, 5.05, 1.55, 1.95, rotM, nxM, nyM, mat_quoin, mat_dark, mat_glass, None, col, panes_x=2)

    # 2. 10-Storey Red-Brick & Buff-Limestone Beaux-Arts Tower (`Édifice La Sauvegarde / Métropole`) rising behind the pitched-roof house on the left of View 2!
    pT1, pT2 = (224.0, 174.0), (196.0, 187.0)
    dxT, dyT = pT2[0] - pT1[0], pT2[1] - pT1[1]
    lenT = math.hypot(dxT, dyT)
    rotT = math.atan2(dyT, dxT)
    nxT, nyT = dyT / lenT, -dxT / lenT
    if nyT < 0:
        nxT, nyT = -nxT, -nyT
    mxT, myT = (pT1[0] + pT2[0]) * 0.5, (pT1[1] + pT2[1]) * 0.5
    create_box("H2_BackTower_BrickBody", (mxT - nxT * 8.0, myT - nyT * 8.0, 15.0), (lenT, 16.0, 30.0), rotT, mat_brick, col)
    create_box("H2_BackTower_StoneCrown", (mxT - nxT * 8.0, myT - nyT * 8.0, 33.5), (lenT + 0.3, 16.3, 7.0), rotT, mat_buff, col)
    create_box("H2_BackTower_BeltCornice", (mxT + nxT * 0.35, myT + nyT * 0.35, 30.0), (lenT + 0.6, 0.75, 0.55), rotT, mat_quoin, col)
    create_box("H2_BackTower_TopCornice", (mxT + nxT * 0.45, myT + nyT * 0.45, 36.8), (lenT + 0.8, 0.90, 0.65), rotT, mat_quoin, col)
    for bc_i in range(7):
        bt = 0.08 + 0.84 * (bc_i / 6.0)
        wx_t, wy_t = pT1[0] + bt * dxT, pT1[1] + bt * dyT
        for fz_t in [13.5, 17.0, 20.5, 24.0, 27.5, 31.8, 34.8]:
            add_window_bay(f"H2_BackTower_Win_{bc_i}_{int(fz_t)}", wx_t, wy_t, fz_t, 1.85, 2.25, rotT, nxT, nyT, mat_quoin, mat_white, mat_glass, None, col, panes_x=2)

    # 3. Left Side of Rue Sainte-Thérèse: 1-Storey Fieldstone Boundary Wall + Lush Green Hedge + Vintage Lamp (92071740)
    pW1, pW2 = (234.18, 215.72), (218.5, 232.5)
    dxW, dyW = pW2[0] - pW1[0], pW2[1] - pW1[1]
    lenW = math.hypot(dxW, dyW)
    rotW = math.atan2(dyW, dxW)
    nxW, nyW = -dyW / lenW, dxW / lenW
    if nxW > 0:
        nxW, nyW = -nxW, -nyW
    mxW, myW = (pW1[0] + pW2[0]) * 0.5, (pW1[1] + pW2[1]) * 0.5
    create_box("H2_LeftStoneWall", (mxW - nxW * 2.2, myW - nyW * 2.2, 2.2), (lenW, 4.4, 4.4), rotW, mat_rubble, col)
    create_box("H2_LeftWallCoping", (mxW + nxW * 0.12, myW + nyW * 0.12, 4.45), (lenW + 0.2, 0.45, 0.25), rotW, mat_quoin, col)
    for lw_i, lwt in enumerate([0.22, 0.50, 0.78]):
        wx_l, wy_l = pW1[0] + lwt * dxW, pW1[1] + lwt * dyW
        add_window_bay(f"H2_LeftWallWin_{lw_i}", wx_l, wy_l, 2.15, 1.35, 1.65, rotW, nxW, nyW, mat_quoin, mat_dark, mat_glass, mat_iron, col, panes_x=2, balcony=True)
    # Dense multi-tiered green hedge along the sidewalk edge
    create_box("H2_LeftGreenHedge_Main", (mxW + nxW * 1.15, myW + nyW * 1.15, 0.65), (lenW - 1.0, 1.35, 1.25), rotW, mat_lawn, col, bevel_w=0.08)
    create_box("H2_LeftGreenHedge_Top", (mxW + nxW * 1.15, myW + nyW * 1.15, 1.35), (lenW - 2.0, 1.05, 0.55), rotW, mat_lawn, col, bevel_w=0.08)

    # =========================================================================
    # HERO 3: `Rue_SaintAntoine_North.jpg` (Corner Building 626555174 + Café Storefronts + Fluted Pilasters + Green Bins)
    # =========================================================================
    # Detail both visible street facades of 626555174:
    # Edge NE: (147.49, 231.94) -> (127.52, 244.79) and Edge NW: (127.52, 244.79) -> (116.44, 224.85)
    c626_pts = [[116.44, 224.85], [116.98, 224.52], [128.48, 217.34], [136.62, 212.58], [140.10, 219.63], [145.69, 229.03], [147.49, 231.94], [127.52, 244.79]]
    for s3_idx, (p3_1, p3_2) in enumerate([((147.49, 231.94), (127.52, 244.79)), ((127.52, 244.79), (116.44, 224.85))]):
        (nx3, ny3), len3 = compute_outward_normal(p3_1, p3_2, c626_pts)
        dx3, dy3 = p3_2[0] - p3_1[0], p3_2[1] - p3_1[1]
        rot3 = math.atan2(dy3, dx3)
        ux3, uy3 = dx3 / len3, dy3 / len3
        mx3, my3 = (p3_1[0] + p3_2[0]) * 0.5, (p3_1[1] + p3_2[1]) * 0.5

        # Coursed grey granite base plinth (z = 0 to 0.85m), projecting 1st-floor canopy cornice (z = 4.25m), and classical roof cornice (z = 16.0m)
        create_box(f"H3_626_GranitePlinth_{s3_idx}", (mx3 + nx3 * 0.16, my3 + ny3 * 0.16, 0.42), (len3 + 0.3, 0.36, 0.85), rot3, mat_granite, col)
        create_box(f"H3_626_CanopyCornice_{s3_idx}", (mx3 + nx3 * 0.38, my3 + ny3 * 0.38, 4.25), (len3 + 0.5, 0.72, 0.52), rot3, mat_quoin, col, cap_top=False, cap_bottom=False)
        create_box(f"H3_626_TopCornice_{s3_idx}", (mx3 + nx3 * 0.42, my3 + ny3 * 0.42, 16.05), (len3 + 0.6, 0.78, 0.58), rot3, mat_quoin, col, cap_top=False, cap_bottom=False)

        n_bays3 = 4
        for b3_i in range(n_bays3 + 1):
            pt_pil = b3_i / float(n_bays3)
            px3, py3 = p3_1[0] + pt_pil * dx3, p3_1[1] + pt_pil * dy3
            # Vertical fluted/channelled limestone pilasters from ground to roof
            create_box(f"H3_626_Pilaster_{s3_idx}_{b3_i}", (px3 + nx3 * 0.22, py3 + ny3 * 0.22, 8.1), (0.85, 0.42, 15.8), rot3, mat_quoin, col)
            for fl_g in (-0.22, 0.0, 0.22):
                create_box(f"H3_626_Flute_{s3_idx}_{b3_i}_{int(fl_g*100)}", (px3 + fl_g * ux3 + nx3 * 0.42, py3 + fl_g * uy3 + ny3 * 0.42, 10.1), (0.06, 0.08, 11.4), rot3, mat_grey, col, bevel_w=0.0)

        for b3_i in range(n_bays3):
            bt3 = (b3_i + 0.5) / float(n_bays3)
            wx3, wy3 = p3_1[0] + bt3 * dx3, p3_1[1] + bt3 * dy3

            # Ground-Floor Deeply Recessed Black-Framed Café/Restaurant Storefront Windows (NO flat tan stickers!)
            create_box(f"H3_626_StoreSill_{s3_idx}_{b3_i}", (wx3 + nx3 * 0.24, wy3 + ny3 * 0.24, 0.88), (3.85, 0.48, 0.16), rot3, mat_quoin, col)
            create_box(f"H3_626_StoreInterior_{s3_idx}_{b3_i}", (wx3 - nx3 * 0.15, wy3 - ny3 * 0.15, 2.35), (3.55, 0.06, 2.85), rot3, mat_warm, col, bevel_w=0.0)
            create_box(f"H3_626_StoreGlass_{s3_idx}_{b3_i}", (wx3 + nx3 * 0.04, wy3 + ny3 * 0.04, 2.35), (3.65, 0.05, 2.90), rot3, mat_glass, col, bevel_w=0.0)
            # Café menu poster inside left pane + dark metal storefront mullions & transom
            create_box(f"H3_626_StorePoster_{s3_idx}_{b3_i}", (wx3 - 0.95 * ux3 + nx3 * 0.02, wy3 - 0.95 * uy3 + ny3 * 0.02, 2.15), (0.65, 0.04, 0.95), rot3, mat_white, col)
            for m3_i in range(4):
                mf = -0.5 + m3_i / 3.0
                create_box(f"H3_626_StoreMul_{s3_idx}_{b3_i}_{m3_i}", (wx3 + mf * 3.55 * ux3 + nx3 * 0.09, wy3 + mf * 3.55 * uy3 + ny3 * 0.09, 2.35), (0.08, 0.12, 2.95), rot3, mat_dark, col)
            for tf3 in (-0.48, 0.22, 0.48):
                create_box(f"H3_626_StoreTrans_{s3_idx}_{b3_i}_{int(tf3*100)}", (wx3 + nx3 * 0.09, wy3 + ny3 * 0.09, 2.35 + tf3 * 2.90), (3.65, 0.12, 0.08), rot3, mat_dark, col)

            # Upper 3 Storeys: Wide 3-Part Black-Framed Chicago Windows (z = 6.1, 9.8, 13.5)
            for fl3_i, fz3 in enumerate([6.1, 9.8, 13.5]):
                add_window_bay(f"H3_626_ChiWin_{s3_idx}_{b3_i}_{fl3_i}", wx3, wy3, fz3, 3.35, 2.25, rot3, nx3, ny3, mat_quoin, mat_dark, mat_glass, None, col, panes_x=3)

    # Row of 6 Green Wheeled Recycling Bins along the right-hand curb of 626555174 + Cobra-Head Streetlight + STOP Sign
    for b_i in range(6):
        bt_bin = 0.12 + b_i * 0.14
        bx = 127.2 + bt_bin * (116.8 - 127.2) - 1.15
        by = 244.2 + bt_bin * (225.2 - 244.2) + 0.65
        create_box(f"H3_GreenBin_{b_i}", (bx, by, 0.68), (0.68, 0.74, 1.08), math.radians(60.0), mat_bin, col)
        create_box(f"H3_GreenBinLid_{b_i}", (bx, by, 1.25), (0.74, 0.80, 0.09), math.radians(60.0), mat_bin, col)
        create_cylinder(f"H3_BinWheel_{b_i}", (bx + 0.28, by - 0.15, 0.22), 0.14, 0.72, (0, math.radians(90.0), math.radians(60.0)), mat_iron, col, segments=10)

    # Tall Curved Streetlight Pole + Red Octagonal STOP Sign + Vertical Banner at Corner (127.8, 245.5)
    create_cylinder("H3_CornerPole", (127.8, 245.5, 4.2), 0.09, 8.2, (0, 0, 0), mat_iron, col, segments=12)
    create_box("H3_CornerArm", (127.1, 246.2, 8.1), (0.10, 2.2, 0.10), math.radians(-40.0), mat_iron, col)
    create_box("H3_CornerBanner", (127.8, 245.4, 5.2), (0.05, 0.65, 1.65), math.radians(-40.0), mat_blue, col)
    create_cylinder("H3_StopSignPost", (126.4, 244.6, 1.35), 0.04, 2.5, (0, 0, 0), mat_iron, col, segments=8)
    create_cylinder("H3_StopSignOct", (126.4, 244.6, 2.45), 0.38, 0.04, (math.radians(90.0), 0, math.radians(30.0)), mat_flag, col, segments=8)

    # =========================================================================
    # HERO 4: `Boulevard_SaintLaurent_West.jpg` (6-Storey Postmodern Office & Parking Facade on Edge 6 of 161202612)
    # =========================================================================
    # Exact NE Facade of 161202612 facing Camera 4 ([122.5, 143.5] at heading 220.4°):
    # pB1 = (118.35, 131.00) -> pB2 = (90.15, 145.27), length = 31.6m, outward normal = (+0.452, +0.892)
    pB1, pB2 = (118.35, 131.00), (90.15, 145.27)
    dxB, dyB = pB2[0] - pB1[0], pB2[1] - pB1[1]
    lenB = math.hypot(dxB, dyB)
    rotB = math.atan2(dyB, dxB)
    uxB, uyB = dxB / lenB, dyB / lenB
    nxB, nyB = -dyB / lenB, dxB / lenB  # Outward NE normal (+0.452, +0.892) facing Camera 4!
    if nyB < 0:
        nxB, nyB = -nxB, -nyB
    mxB, myB = (pB1[0] + pB2[0]) * 0.5, (pB1[1] + pB2[1]) * 0.5

    # 1. Left-side 2-storey Weathered Concrete Annex Wall (`Boulevard_SaintLaurent_West.jpg` left 25% of frame!)
    pA1, pA2 = (127.5, 126.4), (118.35, 131.00)
    mxA, myA = (pA1[0] + pA2[0]) * 0.5, (pA1[1] + pA2[1]) * 0.5
    lenA = math.hypot(pA2[0] - pA1[0], pA2[1] - pA1[1])
    create_box("H4_LeftConcreteAnnex", (mxA - nxB * 4.5, myA - nyB * 4.5, 4.6), (lenA, 9.0, 9.2), rotB, mat_grey, col)
    create_box("H4_LeftAnnexCoping", (mxA + nxB * 0.12, myA + nyB * 0.12, 9.30), (lenA + 0.2, 0.42, 0.24), rotB, mat_dark, col)
    for j_z in [2.2, 4.4, 6.6]:
        create_box(f"H4_LeftAnnexJoint_{int(j_z*10)}", (mxA + nxB * 0.05, myA + nyB * 0.05, j_z), (lenA, 0.12, 0.08), rotB, mat_quoin, col)

    # 2. Main 6-Storey Postmodern Facade on 161202612:
    # Dark Polished Charcoal Granite Base Plinth (z = 0 to 1.85m) + Heavy Projecting 3rd-Floor Moulded Cornice (z = 11.2m) + Top Roof Cornice (z = 22.3m)
    create_box("H4_612_GraniteBase", (mxB + nxB * 0.22, myB + nyB * 0.22, 0.92), (lenB + 0.3, 0.46, 1.85), rotB, mat_granite, col)
    create_box("H4_612_MidCornice_Lower", (mxB + nxB * 0.42, myB + nyB * 0.42, 10.95), (lenB + 0.6, 0.82, 0.38), rotB, mat_buff, col)
    create_box("H4_612_MidCornice_Upper", (mxB + nxB * 0.56, myB + nyB * 0.56, 11.42), (lenB + 0.8, 1.10, 0.56), rotB, mat_quoin, col)
    create_box("H4_612_TopCornice", (mxB + nxB * 0.46, myB + nyB * 0.46, 22.35), (lenB + 0.6, 0.88, 0.55), rotB, mat_quoin, col)

    # 5 Wide Channel-Rusticated Buff Precast Vertical Piers rising from z = 1.85m to 22.5m
    pier_fracs = [0.03, 0.265, 0.50, 0.735, 0.97]
    for p_idx, p_frac in enumerate(pier_fracs):
        px, py = pB1[0] + p_frac * dxB, pB1[1] + p_frac * dyB
        create_box(f"H4_612_Pier_{p_idx}", (px + nxB * 0.28, py + nyB * 0.28, 12.1), (1.45, 0.56, 20.5), rotB, mat_buff, col)
        # Horizontal rustication joints across the precast piers
        for r_z in range(3, 22, 2):
            create_box(f"H4_612_PierRust_{p_idx}_{r_z}", (px + nxB * 0.54, py + nyB * 0.54, float(r_z)), (1.48, 0.08, 0.08), rotB, mat_quoin, col, bevel_w=0.0)

    # 4 Structural Bays between the 5 Precast Piers:
    for bay_i in range(4):
        bt = (pier_fracs[bay_i] + pier_fracs[bay_i + 1]) * 0.5
        bx, by = pB1[0] + bt * dxB, pB1[1] + bt * dyB
        bay_w = (pier_fracs[bay_i + 1] - pier_fracs[bay_i]) * lenB - 1.35

        # Ground floor: Bays 0 & 1 have pedestrian glass entrance & 5-part storefront; Bays 2 & 3 have the recessed dark Parking Garage Portal!
        if bay_i in (0, 1):
            add_window_bay(f"H4_612_GndStore_{bay_i}", bx, by, 2.05, bay_w, 2.55, rotB, nxB, nyB, mat_granite, mat_dark, mat_glass, None, col, panes_x=4)
            if bay_i == 0:
                create_box("H4_612_PedDoorFrame", (bx - 1.4 * uxB + nxB * 0.18, by - 1.4 * uyB + nyB * 0.18, 1.75), (1.95, 0.36, 3.2), rotB, mat_dark, col)
        else:
            # Deeply recessed dark underground parking garage entrance portal
            create_box(f"H4_612_GarageVoid_{bay_i}", (bx + nxB * 0.03, by + nyB * 0.03, 1.75), (bay_w + 0.3, 0.12, 3.4), rotB, mat_dark, col, bevel_w=0.0)
            create_box(f"H4_612_GarageHeader_{bay_i}", (bx + nxB * 0.26, by + nyB * 0.26, 3.55), (bay_w + 0.4, 0.52, 0.45), rotB, mat_Spandrel_Brown if "mat_Spandrel_Brown" in locals() else mat_spandrel, col)

        # Floors 2 & 3 (below the heavy 3rd-floor cornice, z = 5.4 and z = 8.8)
        for fl_i, fz in enumerate([5.35, 8.65]):
            if bay_i == 2:
                # Projecting Cantilevered 3-Sided Bronze-Brown & Glass Oriel Bay Window over the parking garage entrance!
                create_box(f"H4_612_OrielSpandrel_{fl_i}", (bx + nxB * 0.68, by + nyB * 0.68, fz - 1.35), (bay_w - 0.2, 0.95, 1.05), rotB, mat_spandrel, col)
                create_box(f"H4_612_OrielGlass_{fl_i}", (bx + nxB * 0.64, by + nyB * 0.64, fz), (bay_w - 0.3, 0.85, 1.85), rotB, mat_glass, col)
                for om_i in range(5):
                    omf = -0.5 + om_i / 4.0
                    create_box(f"H4_612_OrielMul_{fl_i}_{om_i}", (bx + omf * (bay_w - 0.4) * uxB + nxB * 1.08, by + omf * (bay_w - 0.4) * uyB + nyB * 1.08, fz), (0.08, 0.10, 1.90), rotB, mat_dark, col)
            else:
                create_box(f"H4_612_SpandrelLow_{bay_i}_{fl_i}", (bx + nxB * 0.16, by + nyB * 0.16, fz - 1.38), (bay_w, 0.34, 1.02), rotB, mat_spandrel, col)
                add_window_bay(f"H4_612_RibbonLow_{bay_i}_{fl_i}", bx, by, fz, bay_w - 0.15, 1.85, rotB, nxB, nyB, mat_buff, mat_dark, mat_glass, None, col, panes_x=4)

        # Floors 4, 5 & 6 (above the heavy 3rd-floor cornice, z = 13.5, 16.9, 20.2)
        for fl_i, fz in enumerate([13.5, 16.9, 20.2]):
            create_box(f"H4_612_SpandrelHigh_{bay_i}_{fl_i}", (bx + nxB * 0.16, by + nyB * 0.16, fz - 1.38), (bay_w, 0.34, 1.02), rotB, mat_spandrel, col)
            add_window_bay(f"H4_612_RibbonHigh_{bay_i}_{fl_i}", bx, by, fz, bay_w - 0.15, 1.85, rotB, nxB, nyB, mat_buff, mat_dark, mat_glass, None, col, panes_x=4)

    # 3. Foreground Sidewalk Parking Props in View 4:
    # Black Solar Parking Pay-Station Meter on left sidewalk + Green `<- P` Sign + Blue `$20` A-Frame Sign
    px_m, py_m = pB1[0] + 0.14 * dxB + nxB * 1.45, pB1[1] + 0.14 * dyB + nyB * 1.45
    create_box("H4_ParkingKiosk_Body", (px_m, py_m, 0.95), (0.38, 0.32, 1.65), rotB, mat_iron, col)
    create_box("H4_ParkingKiosk_Cap", (px_m, py_m, 1.85), (0.44, 0.38, 0.25), rotB, mat_blue, col)

    px_s, py_s = pB1[0] + 0.50 * dxB + nxB * 0.62, pB1[1] + 0.50 * dyB + nyB * 0.62
    create_box("H4_GreenPSign_Board", (px_s, py_s, 3.15), (0.85, 0.12, 0.55), rotB, mat_bin, col)
    create_box("H4_GreenPSign_Text", (px_s + nxB * 0.07, py_s + nyB * 0.07, 3.15), (0.55, 0.04, 0.28), rotB, mat_white, col)

    px_b, py_b = pB1[0] + 0.52 * dxB + nxB * 1.25, pB1[1] + 0.52 * dyB + nyB * 1.25
    create_box("H4_Blue20Sign_Board", (px_b, py_b, 0.68), (0.68, 0.45, 1.15), rotB, mat_blue, col)
    create_box("H4_Blue20Sign_Frame", (px_b + nxB * 0.24, py_b + nyB * 0.24, 0.72), (0.52, 0.04, 0.48), rotB, mat_white, col)


# ---------------------------------------------------------------------------
# 5. PROCEDURAL BUILDING GENERATOR FOR ALL BLOCK BUILDINGS
# ---------------------------------------------------------------------------
def build_all_buildings(dossier, palette, owned_col, context_col):
    mat_grey = palette["Mat_Stone_Grey"]
    mat_buff = palette["Mat_Stone_Buff"]
    mat_rubble = palette["Mat_Stone_Rubble"]
    mat_quoin = palette["Mat_Stone_Quoin"]
    mat_brick = palette["Mat_Red_Brick"]
    mat_brown = palette["Mat_Brown_Brick"]
    mat_slate = palette["Mat_Roof_Slate"]
    mat_flat = palette["Mat_Roof_Flat"]
    mat_white = palette["Mat_Frame_White"]
    mat_dark = palette["Mat_Frame_Dark"]
    mat_glass = palette["Mat_Glass_Dark"]
    mat_warm = palette["Mat_Glass_Warm"]
    mat_iron = palette["Mat_Iron_Black"]

    bldg_specs = {
        20919179:   (5, 19.5, mat_grey, mat_dark, "flat"),        # Annexe du Vieux-Palais-de-Justice
        190106260:  (10, 38.0, mat_brown, mat_white, "flat"),     # Édifice Métropole (10-storey brown-brick tower)
        190106273:  (6, 22.5, mat_grey, mat_dark, "flat"),
        610570818:  (6, 21.5, mat_brick, mat_white, "flat"),      # AC Hotel / SpringHill Suites by Marriott
        339882470:  (7, 24.5, mat_buff, mat_dark, "flat"),        # Buff stone building on Rue Saint-Jean-Baptiste (View 1 left)
        626555174:  (4, 16.2, mat_grey, mat_dark, "flat"),        # Corner building in View 3 (`Rue_SaintAntoine_North.jpg` left!)
        161202612:  (6, 22.5, mat_buff, mat_dark, "flat"),        # Postmodern office building in View 4 (`Boulevard_SaintLaurent_West.jpg`)
        190498524:  (10, 36.0, mat_buff, mat_dark, "flat"),       # Édifice La Sauvegarde
        626555172:  (2, 6.2, mat_rubble, mat_dark, "pitched"),    # Historic pitched-roof stone house in View 2
        626555171:  (2, 6.2, mat_rubble, mat_dark, "pitched"),    # End of Rue Sainte-Thérèse heritage house
        626555169:  (2, 6.2, mat_rubble, mat_dark, "pitched"),    # End of Rue Sainte-Thérèse heritage house
        1253645843: (2, 6.2, mat_rubble, mat_dark, "pitched"),
        92071740:   (1, 4.2, mat_rubble, mat_dark, "flat"),       # Low stone building left of View 2
    }

    for bldg in dossier.get("osm_features", {}).get("buildings", []):
        bid = bldg["id"]
        if bid == 20919177:
            # Built by custom landmark builder `build_palais_de_justice_and_cormier`
            continue

        is_owned = bldg.get("is_primary_owner", False)
        target_col = owned_col if is_owned else context_col
        pts = bldg.get("coords_xy", [])
        if len(pts) < 4:
            continue
        clean_pts = pts[:-1] if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05 else pts

        if bid in bldg_specs:
            lvls, h_wall, mat_wall, mat_frm, roof_type = bldg_specs[bid]
        else:
            lvls = 4 if (bid % 2 == 0) else 3
            h_wall = lvls * 3.8
            mat_wall = mat_grey if (bid % 3 != 0) else (mat_brick if bid % 5 == 0 else mat_buff)
            mat_frm = mat_white if (bid % 2 == 0) else mat_dark
            roof_type = "pitched" if (bid % 4 == 0) else "flat"

        h_stagger = (((int(bid) * 17) % 31) - 15) * 0.12
        h_wall = round(h_wall + h_stagger, 2)

        if bid == 610570818:
            # Recess ground floor (z = 0 to 4.6m) along the SW colonnade edge so the SpringHill Suites loggia is a true 2.4m-deep recess!
            gnd_pts = []
            for px, py in clean_pts:
                if py < 186.0 and px < 182.0:
                    gnd_pts.append([px + 2.2 * 0.492, py + 2.2 * 0.870])
                else:
                    gnd_pts.append([px, py])
            create_extruded_polygon(f"Bldg_{bid}_GndRecess", gnd_pts, 0.0, 4.6, mat_dark, target_col, bevel_w=0.02, cap_top=False)
            create_extruded_polygon(f"Bldg_{bid}_UpperBody", clean_pts, 4.6, h_wall, mat_wall, target_col, bevel_w=0.02, cap_top=False)
        else:
            create_extruded_polygon(f"Bldg_{bid}_Plinth", clean_pts, 0.0, 0.95, mat_rubble if roof_type == "pitched" else mat_quoin, target_col, bevel_w=0.015)
            create_extruded_polygon(f"Bldg_{bid}_Body", clean_pts, 0.95, h_wall, mat_wall, target_col, bevel_w=0.02, cap_top=False)

        # Special 2-storey limestone crown on 10-storey Édifice Métropole (190106260)
        if bid == 190106260:
            create_extruded_polygon("Bldg_Metropole_Crown", clean_pts, 31.0, 38.2, mat_buff, target_col, bevel_w=0.03, cap_bottom=False)

        cx = sum(p[0] for p in clean_pts) / len(clean_pts)
        cy = sum(p[1] for p in clean_pts) / len(clean_pts)
        if bid == 626555172:
            # Roof is modeled in rich hero detail by H2_EndHouse_RoofTier_0..4
            create_extruded_polygon(f"Bldg_{bid}_RoofCap", clean_pts, h_wall, h_wall + 0.42, mat_quoin, target_col, bevel_w=0.02, cap_bottom=False, cap_top=False)
        else:
            create_extruded_polygon(f"Bldg_{bid}_RoofCap", clean_pts, h_wall, h_wall + 0.42, mat_quoin, target_col, bevel_w=0.02, cap_bottom=False, cap_top=(roof_type == "pitched"))
            if roof_type == "pitched":
                inner_pts = [(p[0] + (cx - p[0]) * 0.06, p[1] + (cy - p[1]) * 0.06) for p in clean_pts]
                create_extruded_polygon(f"Bldg_{bid}_PitchedRoof", inner_pts, h_wall + 0.35, h_wall + 3.4, mat_slate, target_col, bevel_w=0.03)
            else:
                deck_pts = inset_polygon_2d(clean_pts, 0.45)
                create_extruded_polygon(f"Bldg_{bid}_FlatDeck", deck_pts, h_wall + 0.42, h_wall + 0.62, mat_flat, target_col, bevel_w=0.01, cap_bottom=False)
                if is_owned and h_wall > 10.0:
                    create_box(f"Bldg_{bid}_HVAC", (cx, cy, h_wall + 1.45), (2.4, 1.2, 1.6), math.radians(32.0), mat_quoin, target_col)

        n_pts = len(clean_pts)
        for e_i in range(n_pts):
            p1 = clean_pts[e_i]
            p2 = clean_pts[(e_i + 1) % n_pts]
            (nx, ny), elen = compute_outward_normal(p1, p2, clean_pts)
            if elen < 4.5:
                continue

            # Skip custom hero edges to prevent overlap
            if bid == 610570818 and ny < -0.4:
                continue
            if bid == 161202612 and (nx > 0.3 and ny > 0.4):
                continue
            if bid == 626555174 and e_i in (6, 7):
                continue
            if bid in (626555171, 626555169, 92071740):
                continue

            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            erot = math.atan2(dy, dx)
            mx, my = (p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5

            create_box(f"Bldg_{bid}_E{e_i}_GndCornice", (mx + nx * 0.22, my + ny * 0.22, 4.10), (elen + 0.2, 0.42, 0.34), erot, mat_quoin, target_col, cap_top=False, cap_bottom=False)
            create_box(f"Bldg_{bid}_E{e_i}_TopCornice", (mx + nx * 0.28, my + ny * 0.28, h_wall - 0.15), (elen + 0.3, 0.54, 0.42), erot, mat_quoin, target_col, cap_top=False)

            if bid == 339882470:
                # Extra limestone belt courses above the 2nd floor arched windows (z = 10.1m)
                create_box(f"Bldg_{bid}_E{e_i}_Belt2", (mx + nx * 0.24, my + ny * 0.24, 10.15), (elen + 0.25, 0.46, 0.36), erot, mat_quoin, target_col, cap_top=False, cap_bottom=False)

            n_cols = max(1, int((elen - 1.4) / 3.8))
            for c_i in range(n_cols):
                t_pos = (c_i + 0.5) / float(n_cols)
                wx, wy = p1[0] + t_pos * dx, p1[1] + t_pos * dy
                if bid == 339882470:
                    # Deeply recessed dark metal basement air-intake louver vents + stone surround (NOT grey stickers!)
                    create_box(f"Bldg_{bid}_E{e_i}_LouverFrame_{c_i}", (wx + nx * 0.14, wy + ny * 0.14, 1.15), (2.55, 0.28, 1.15), erot, mat_quoin, target_col)
                    create_box(f"Bldg_{bid}_E{e_i}_LouverVoid_{c_i}", (wx + nx * 0.03, wy + ny * 0.03, 1.15), (2.25, 0.06, 0.88), erot, mat_dark, target_col, bevel_w=0.0)
                    # TWO storeys of large round-arched industrial multi-pane windows (z = 4.2m and z = 8.1m)
                    add_window_bay(f"Bldg_{bid}_E{e_i}_Arch1_{c_i}", wx, wy, 4.20, 2.55, 2.85, erot, nx, ny, mat_quoin, mat_dark, mat_glass, None, target_col, arched=True, panes_x=3)
                    add_window_bay(f"Bldg_{bid}_E{e_i}_Arch2_{c_i}", wx, wy, 8.10, 2.55, 2.85, erot, nx, ny, mat_quoin, mat_dark, mat_glass, None, target_col, arched=True, panes_x=3)
                    for fl_i, fz in enumerate([12.1, 15.6, 19.1, 22.4]):
                        add_window_bay(f"Bldg_{bid}_E{e_i}_UpW_{c_i}_{fl_i}", wx, wy, fz, 2.35, 2.15, erot, nx, ny, mat_quoin, mat_dark, mat_glass, None, target_col, panes_x=3)
                else:
                    add_window_bay(f"Bldg_{bid}_E{e_i}_Gnd_{c_i}", wx, wy, 2.25, 1.95, 2.55, erot, nx, ny, mat_quoin, mat_frm, mat_glass, None, target_col, panes_x=2)
                    for fl_i in range(1, lvls):
                        fz = 2.25 + fl_i * ((h_wall - 3.4) / float(max(1, lvls - 1)))
                        add_window_bay(f"Bldg_{bid}_E{e_i}_W_{c_i}_{fl_i}", wx, wy, fz, 1.65, 2.15, erot, nx, ny, mat_quoin, mat_frm, mat_glass, mat_iron, target_col, panes_x=2)


# ---------------------------------------------------------------------------
# 6. STREETS, SIDEWALKS, TREES & STREET FURNITURE
# ---------------------------------------------------------------------------
def build_public_realm(dossier, palette, kit_assets, col):
    mat_cobble = palette["Mat_Cobble_Street"]
    mat_asphalt = palette["Mat_Asphalt"]
    mat_sidewalk = palette["Mat_Sidewalk"]
    mat_quoin = palette["Mat_Stone_Quoin"]
    mat_white = palette["Mat_Frame_White"]

    # Base Asphalt Roadway Plane across the entire Courthouse & Old Montreal NE district (top at z = 0.00m)
    create_box("Block_Ground_Asphalt", (150.0, 200.0, -0.08), (420.0, 360.0, 0.16), 0.0, mat_asphalt, col, bevel_w=0.0)

    # Raised Jointed Concrete Sidewalks with Granite Curbs under each block sector (top at z = 0.14m)
    rot_nd = math.radians(58.0)  # Aligned with Rue Notre-Dame Est (~58 deg)
    # 1. Palais de Justice & Édifice Ernest-Cormier NW Plazas
    create_box("Sidewalk_Palais_NW", (45.0, 265.0, 0.07), (145.0, 135.0, 0.14), rot_nd, mat_sidewalk, col, bevel_w=0.01)
    create_box("Sidewalk_Cormier_NW", (184.0, 262.0, 0.07), (94.0, 56.0, 0.14), rot_nd, mat_sidewalk, col, bevel_w=0.01)

    # 2. View 2 Sidewalks along Rue Sainte-Thérèse (Right curb along Édifice Ernest-Cormier & Left curb along Hedge Wall 92071740)
    rot_st = math.radians(-116.0)
    create_box("Sidewalk_SainteTherese_Right", (208.5, 224.0, 0.07), (46.0, 3.6, 0.14), rot_st, mat_sidewalk, col, bevel_w=0.01)
    create_box("Curb_SainteTherese_Right", (210.1, 223.2, 0.08), (46.0, 0.28, 0.16), rot_st, mat_quoin, col, bevel_w=0.01)
    create_box("Sidewalk_SainteTherese_Left", (223.5, 220.0, 0.07), (42.0, 3.6, 0.14), rot_st, mat_sidewalk, col, bevel_w=0.01)
    create_box("Curb_SainteTherese_Left", (221.8, 220.8, 0.08), (42.0, 0.28, 0.16), rot_st, mat_quoin, col, bevel_w=0.01)

    # 3. View 3 Full Sidewalk & Granite Curb wrapping Corner Building 626555174 (NO floating slab!)
    sidewalk_626_pts = [[113.5, 224.0], [137.0, 209.5], [151.5, 232.5], [127.2, 248.2]]
    create_extruded_polygon("Sidewalk_Corner_626555174", sidewalk_626_pts, 0.0, 0.14, mat_sidewalk, col, bevel_w=0.015)
    curb_626_pts = inset_polygon_2d(sidewalk_626_pts, -0.25)
    create_extruded_polygon("Curb_Corner_626555174", curb_626_pts, 0.0, 0.13, mat_quoin, col, bevel_w=0.01)

    # Flush Reddish-Grey Cobblestone Crosswalk with White Stripes in Foreground of View 3 (`Rue_SaintAntoine_North.jpg`)
    rot_cw = math.radians(-32.0)
    create_box("Crosswalk_Cobble_View3", (134.5, 249.2, 0.01), (14.5, 3.8, 0.025), rot_cw, mat_cobble, col, bevel_w=0.0)
    create_box("Crosswalk_Line_N", (135.5, 250.8, 0.02), (14.5, 0.18, 0.02), rot_cw, mat_white, col, bevel_w=0.0)
    create_box("Crosswalk_Line_S", (133.5, 247.6, 0.02), (14.5, 0.18, 0.02), rot_cw, mat_white, col, bevel_w=0.0)

    # 4. View 1 Sidewalks & Asphalt Roadway along Rue Saint-Jean-Baptiste
    create_box("Sidewalk_Central_Triangle", (156.0, 194.0, 0.07), (76.0, 44.0, 0.14), math.radians(-30.0), mat_sidewalk, col, bevel_w=0.01)
    create_box("Sidewalk_South_2470", (138.0, 152.0, 0.07), (68.0, 34.0, 0.14), math.radians(-30.0), mat_sidewalk, col, bevel_w=0.01)
    p_jb1, p_jb2 = (190.0, 148.0), (110.0, 194.0)
    dx_jb, dy_jb = p_jb2[0] - p_jb1[0], p_jb2[1] - p_jb2[1]
    rot_jb = math.atan2(dy_jb, dx_jb)
    create_box("Road_SaintJeanBaptiste", (150.0, 171.0, 0.08), (92.0, 5.2, 0.14), rot_jb, mat_asphalt, col, bevel_w=0.0)
    nx_jb, ny_jb = dy_jb / math.hypot(dx_jb, dy_jb), -dx_jb / math.hypot(dx_jb, dy_jb)
    for s_side in (-1.0, 1.0):
        create_box(f"Curb_SaintJeanBaptiste_{int(s_side)}", (150.0 + s_side * nx_jb * 3.7, 171.0 + s_side * ny_jb * 3.7, 0.12), (92.0, 2.2, 0.16), rot_jb, mat_sidewalk, col, bevel_w=0.01)

    # 5. View 4 Jointed Concrete Sidewalk & Raised Granite Curb along Boulevard Saint-Laurent (in front of 161202612)
    pB1, pB2 = (128.0, 126.1), (88.0, 146.4)
    dxB, dyB = pB2[0] - pB1[0], pB2[1] - pB1[1]
    lenB = math.hypot(dxB, dyB)
    rotB = math.atan2(dyB, dxB)
    nxB, nyB = -dyB / lenB, dxB / lenB
    if nyB < 0:
        nxB, nyB = -nxB, -nyB
    mxB, myB = (pB1[0] + pB2[0]) * 0.5, (pB1[1] + pB2[1]) * 0.5
    create_box("Sidewalk_SaintLaurent_View4", (mxB + nxB * 1.6, myB + nyB * 1.6, 0.07), (lenB + 4.0, 3.2, 0.14), rotB, mat_sidewalk, col, bevel_w=0.01)
    create_box("Curb_SaintLaurent_View4", (mxB + nxB * 3.25, myB + nyB * 3.25, 0.08), (lenB + 4.0, 0.28, 0.16), rotB, mat_quoin, col, bevel_w=0.01)
    create_box("Sidewalk_East_Retail", (265.0, 215.0, 0.07), (95.0, 140.0, 0.14), math.radians(-30.0), mat_sidewalk, col, bevel_w=0.01)

    # Instantiate Poly Haven `jacaranda_tree_LOD0` 3D Trees
    tree_template = kit_assets.get("jacaranda_tree_LOD0")
    curated_trees = [
        ("PDJ_Plaza_Tree_1", 92.0, 228.0, 0.38),
        ("PDJ_Plaza_Tree_2", 78.0, 206.0, 0.42),
        ("PDJ_Plaza_Tree_3", 112.0, 268.0, 0.44),
        ("SainteTherese_Tree", 213.5, 198.5, 0.36),
        ("SaintGabriel_Tree_1", 158.0, 235.0, 0.40),
        ("SaintLaurent_Tree_1", 82.0, 155.0, 0.45),
    ]
    if tree_template:
        for i, (tname, tx, ty, ts) in enumerate(curated_trees):
            inst = tree_template.copy()
            inst.data = tree_template.data
            inst.name = f"PH_Tree_{i}_{tname}"
            col.objects.link(inst)
            inst.scale = (ts, ts, ts)
            inst.location = (tx, ty, 0.0)
            inst.rotation_euler = (0.0, 0.0, (i * 1.7) % (2.0 * math.pi))

    # Instantiate Street Lamps from `assets/montreal_kit.blend`
    lamp_template = kit_assets.get("street_lamp_01")
    lamp_coords = [
        (220.8, 225.2),  # Left sidewalk of View 2 (`Edifice_Ernest_Cormier_Columns.jpg`)
        (225.5, 214.0),
        (102.0, 242.0),
        (88.0, 220.0),
    ]
    if lamp_template:
        for l_i, (lx, ly) in enumerate(lamp_coords):
            lp = lamp_template.copy()
            lp.data = lamp_template.data
            lp.name = f"PH_StreetLamp_{l_i}"
            col.objects.link(lp)
            lp.location = (lx, ly, 0.14)
            lp.scale = (1.0, 1.0, 1.0)


# ---------------------------------------------------------------------------
# 7. WORLD HDRI LIGHTING & STREET VIEW CAMERAS
# ---------------------------------------------------------------------------
def setup_world_and_lighting(scene):
    scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 64

    world = bpy.data.worlds.get("World_MTL_VM_0013") or bpy.data.worlds.new("World_MTL_VM_0013")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.15
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    hdri_path = os.path.join(PH_DIR, "kloppenheim_06_puresky_2k.hdr")
    if os.path.exists(hdri_path):
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri_path, check_existing=True)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    else:
        bg.inputs["Color"].default_value = (0.55, 0.68, 0.88, 1.0)

    sun_data = bpy.data.lights.new(name="Sun_MTL_0013", type='SUN')
    sun_data.energy = 3.2
    sun_data.color = (1.0, 0.95, 0.86)
    sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new("Sun_MTL_0013", sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(15.0), math.radians(-135.0))


def render_cameras(scene, dossier, cam_col, iter_num=2):
    os.makedirs(RENDERS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.image_settings.file_format = 'PNG'

    # Calibrated camera positions matching the exact 90-deg Street View car framing
    cam_overrides = {
        "Rue_NotreDame_Main_Plaza": (169.2, 158.2, 2.0, 312.0, 12.0),
        "Edifice_Ernest_Cormier_Columns": (216.2, 232.0, 1.9, 223.0, 10.0),
        "Rue_SaintAntoine_North": (134.2, 253.2, 1.9, 204.0, 10.0),
        "Boulevard_SaintLaurent_West": (122.5, 143.5, 1.9, 220.4, 12.0),
    }

    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        if label in cam_overrides:
            cx, cy, cz, heading, pitch = cam_overrides[label]
        else:
            cx, cy = cam_info["blender_cam_xy_m"]
            cz = 1.8
            heading = cam_info.get("heading", cam_info.get("heading_deg", 0.0))
            pitch = cam_info.get("pitch_deg", 10.0)
        fov = cam_info.get("fov_deg", 90.0)

        cam_data = bpy.data.cameras.new(name=f"SV_Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(fov)
        cam_data.clip_start = 0.1
        cam_data.clip_end = 1000.0

        cam_obj = bpy.data.objects.new(f"SV_Cam_{label}", cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cx, cy, cz)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch), 0.0, math.radians(-heading))

        scene.camera = cam_obj
        out_file = os.path.join(RENDERS_DIR, f"iter{iter_num}_{label}.png")
        scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View Camera [{label}] -> {out_file}")

    # Overview Camera framing Palais de Justice, Édifice Ernest-Cormier, and the Old Montreal NE block
    ov_data = bpy.data.cameras.new(name=f"{BLOCK_ID}_Overview_Cam")
    ov_data.lens_unit = 'FOV'
    ov_data.angle = math.radians(65.0)
    ov_obj = bpy.data.objects.new(f"{BLOCK_ID}_Overview_Cam", ov_data)
    cam_col.objects.link(ov_obj)
    ov_obj.location = (195.0, 95.0, 125.0)
    target = Vector((115.0, 225.0, 18.0))
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
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    root_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(root_col)
    owned_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    root_col.children.link(owned_col)
    context_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Context_Proxy")
    root_col.children.link(context_col)
    context_col.hide_render = True
    context_col.hide_viewport = True
    cam_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Cameras")
    root_col.children.link(cam_col)

    palette = create_block_palette()
    kit_assets = load_kit_assets()

    build_palais_de_justice_and_cormier(palette, owned_col)
    build_all_buildings(dossier, palette, owned_col, context_col)
    build_hero_facades(palette, owned_col)
    build_public_realm(dossier, palette, kit_assets, owned_col)

    scene = bpy.context.scene
    setup_world_and_lighting(scene)
    render_cameras(scene, dossier, cam_col, iter_num=2)

    for o in context_col.all_objects:
        o.hide_render = True
        o.hide_viewport = True

    os.makedirs(OUTPUT_BLOCKS_DIR, exist_ok=True)
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
    bpy.ops.wm.usd_export(filepath=usdc_path, check_existing=False)
    print(f"Saved {blend_path} and exported {usdc_path}")


if __name__ == "__main__":
    main()

