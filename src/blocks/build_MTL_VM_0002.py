"""
Build script for City Block MTL-VM-0002:
Basilique Notre-Dame de Montréal & Vieux Séminaire de Saint-Sulpice Full Block (110 Rue Notre-Dame Ouest)

AAA / Matrix Awakens Photorealistic Standards:
1. Real Poly Haven 2K PBR Textures (`sandstone_blocks_05`, `castle_brick_02_red`, `cobblestone_floor_08`, `asphalt_02`)
   mapped with `projection='BOX'` (`TexCoord -> Object`) + RGB tinting, normal maps, and roughness variation.
2. Real Poly Haven 2K Outdoor HDRI (`kloppenheim_06_puresky_2k.hdr`) + warm afternoon directional sun for realistic
   glass reflections, soft shadows, and natural sky horizon.
3. Deep 3D Architectural Relief (`0.55m–3.4m` recessed Gothic lancet windows, open 3-bay vaulted West Loggia,
   multi-pane seminary casement windows, projecting stone sills, lintels, hood moldings, 3D tracery mullions & transoms,
   rusticated ground plinth, stepped cornices, octagonal buttresses with spire pinnacles, and `BEVEL` modifiers).
4. High-Poly Organic Multi-Branch Deciduous Trees (`shade_smooth()`) and ornate multi-globe cast-iron candelabra lamps.
5. Strict Georeferencing & Ownership Deduplication:
   - `Block_MTL-VM-0002`
     - `Block_MTL-VM-0002_Owned`: Basilique Notre-Dame, Vieux Séminaire de Saint-Sulpice, Forecourt Wall, Parvis & Streetscape.
     - `Block_MTL-VM-0002_Context_Proxy`: Detailed context buildings (`is_primary_owner == False`) with 3D recessed window bays.
"""

import os
import sys
import json
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
if os.path.join(BASE_DIR, "src") not in sys.path:
    sys.path.append(os.path.join(BASE_DIR, "src"))

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0002"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_BLOCKS_DIR = os.path.join(BASE_DIR, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")

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


def ensure_collection(name: str, parent=None):
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
    else:
        col = bpy.data.collections.new(name)
        if parent is not None:
            parent.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)
    return col


def load_image_safe(filepath: str, colorspace: str = "sRGB"):
    if not os.path.isfile(filepath):
        return None
    img = bpy.data.images.load(filepath, check_existing=True)
    try:
        img.colorspace_settings.name = colorspace
    except Exception:
        pass
    return img


def build_polyhaven_box_material(
    name: str,
    diff_file: str,
    rough_file: str,
    nor_file: str,
    tint_hex: str = "#FFFFFF",
    tint_fac: float = 0.35,
    scale: float = 0.25,
    normal_strength: float = 1.15,
    roughness_bias: float = 0.0,
    metallic: float = 0.0,
):
    """
    Creates or updates a PBR material using real Poly Haven 2K Diffuse, Roughness, and Normal maps
    projected seamlessly in 3D world/object space via `projection = 'BOX'`.
    """
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
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
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(mapping.inputs["Vector"], tex_coord.outputs["Object"])

    rgba = kit.hex_to_rgba(tint_hex)
    mat.diffuse_color = rgba

    diff_img = load_image_safe(os.path.join(POLYHAVEN_DIR, diff_file), "sRGB")
    rough_img = load_image_safe(os.path.join(POLYHAVEN_DIR, rough_file), "Non-Color")
    nor_img = load_image_safe(os.path.join(POLYHAVEN_DIR, nor_file), "Non-Color")

    if diff_img:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = diff_img
        tex_d.projection = 'BOX'
        tex_d.projection_blend = 0.25
        links.new(tex_d.inputs["Vector"], mapping.outputs["Vector"])

        mix_rgb = nodes.new("ShaderNodeMix")
        mix_rgb.data_type = 'RGBA'
        mix_rgb.blend_type = 'MULTIPLY' if tint_fac > 0.5 else 'MIX'
        mix_rgb.inputs["Factor"].default_value = tint_fac
        links.new(mix_rgb.inputs[6], tex_d.outputs["Color"])
        mix_rgb.inputs[7].default_value = rgba
        links.new(bsdf.inputs["Base Color"], mix_rgb.outputs[2])
    else:
        bsdf.inputs["Base Color"].default_value = rgba

    if rough_img:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = rough_img
        tex_r.projection = 'BOX'
        tex_r.projection_blend = 0.25
        links.new(tex_r.inputs["Vector"], mapping.outputs["Vector"])

        math_r = nodes.new("ShaderNodeMath")
        math_r.operation = 'ADD'
        math_r.use_clamp = True
        math_r.inputs[1].default_value = roughness_bias
        links.new(math_r.inputs[0], tex_r.outputs["Color"])
        links.new(bsdf.inputs["Roughness"], math_r.outputs["Value"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.75

    if nor_img:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = nor_img
        tex_n.projection = 'BOX'
        tex_n.projection_blend = 0.25
        links.new(tex_n.inputs["Vector"], mapping.outputs["Vector"])

        nor_map = nodes.new("ShaderNodeNormalMap")
        nor_map.space = 'OBJECT'
        nor_map.inputs["Strength"].default_value = normal_strength
        links.new(nor_map.inputs["Color"], tex_n.outputs["Color"])
        links.new(bsdf.inputs["Normal"], nor_map.outputs["Normal"])

    return mat


def upgrade_palette_with_polyhaven(palette: dict):
    """Upgrades all Montreal kit materials with real 2K Poly Haven PBR maps and reflective architectural glass."""
    palette["Mat_MTL_PierreGrise_Limestone"] = build_polyhaven_box_material(
        "Mat_MTL_PierreGrise_Limestone",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint_hex="#9B9890",
        tint_fac=0.52,
        scale=0.22,
        normal_strength=1.10,
    )
    palette["Mat_MTL_WarmBuff_Limestone"] = build_polyhaven_box_material(
        "Mat_MTL_WarmBuff_Limestone",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint_hex="#BAAD94",
        tint_fac=0.45,
        scale=0.26,
        normal_strength=0.95,
    )
    palette["Mat_MTL_Fieldstone_Rubble"] = build_polyhaven_box_material(
        "Mat_MTL_Fieldstone_Rubble",
        "cobblestone_floor_08_Diffuse_2k.jpg",
        "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg",
        tint_hex="#7D776C",
        tint_fac=0.42,
        scale=0.35,
        normal_strength=1.40,
        roughness_bias=0.08,
    )
    palette["Mat_MTL_Heritage_RedBrick"] = build_polyhaven_box_material(
        "Mat_MTL_Heritage_RedBrick",
        "castle_brick_02_red_Diffuse_2k.jpg",
        "castle_brick_02_red_Rough_2k.jpg",
        "castle_brick_02_red_nor_gl_2k.jpg",
        tint_hex="#964234",
        tint_fac=0.25,
        scale=0.32,
        normal_strength=1.15,
    )
    palette["Mat_MTL_Red_Sandstone"] = build_polyhaven_box_material(
        "Mat_MTL_Red_Sandstone",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint_hex="#9E4E38",
        tint_fac=0.58,
        scale=0.24,
        normal_strength=1.05,
    )
    palette["Mat_MTL_Cobblestone"] = build_polyhaven_box_material(
        "Mat_MTL_Cobblestone",
        "cobblestone_floor_08_Diffuse_2k.jpg",
        "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg",
        tint_hex="#76716A",
        tint_fac=0.28,
        scale=0.32,
        normal_strength=1.25,
    )
    palette["Mat_MTL_Plaza_Light_Granite"] = build_polyhaven_box_material(
        "Mat_MTL_Plaza_Light_Granite",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint_hex="#ABA79F",
        tint_fac=0.48,
        scale=0.35,
        normal_strength=0.70,
        roughness_bias=-0.10,
    )
    palette["Mat_MTL_Plaza_Charcoal_Granite"] = build_polyhaven_box_material(
        "Mat_MTL_Plaza_Charcoal_Granite",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#5A5D62",
        tint_fac=0.35,
        scale=0.28,
        normal_strength=0.80,
    )
    palette["Mat_MTL_Street_Asphalt"] = build_polyhaven_box_material(
        "Mat_MTL_Street_Asphalt",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint_hex="#383A3E",
        tint_fac=0.25,
        scale=0.22,
        normal_strength=0.95,
    )
    palette["Mat_MTL_Slate_Roof_Dark"] = build_polyhaven_box_material(
        "Mat_MTL_Slate_Roof_Dark",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint_hex="#2E3238",
        tint_fac=0.74,
        scale=0.45,
        normal_strength=0.80,
        roughness_bias=-0.15,
    )
    # Dark Vaulted Loggia Interior Stone (deep shadowed stone for the 3-arch west portico)
    palette["Mat_MTL_Dark_Vault_Stone"] = build_polyhaven_box_material(
        "Mat_MTL_Dark_Vault_Stone",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint_hex="#3C3A36",
        tint_fac=0.72,
        scale=0.25,
        normal_strength=1.10,
    )

    # Reflective Architectural Glass (catches real HDRI sky reflections, Roughness=0.04, IOR=1.52)
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    bsdf_g = next(n for n in mat_glass.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf_g.inputs["Base Color"].default_value = (0.06, 0.11, 0.16, 1.0)
    bsdf_g.inputs["Roughness"].default_value = 0.04
    bsdf_g.inputs["Metallic"].default_value = 0.35
    if "IOR" in bsdf_g.inputs:
        bsdf_g.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in bsdf_g.inputs:
        bsdf_g.inputs["Specular IOR Level"].default_value = 0.85

    # Gothic Stained Glass (Reflective exterior + rich blue/gold/ruby internal variation)
    palette["Mat_MTL_Stained_Glass"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Stained_Glass", "#18283E", roughness=0.04, metallic=0.45, bump_strength=0.04, noise_scale=14.0
    )
    bsdf_sg = next(n for n in palette["Mat_MTL_Stained_Glass"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "IOR" in bsdf_sg.inputs:
        bsdf_sg.inputs["IOR"].default_value = 1.52

    # Gold leaf, Clock enamel, White wood muntins, Warm portal glow, Garden lawn, Spring-Summer Green Foliage
    palette["Mat_MTL_Gold_Leaf"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Gold_Leaf", "#D8B238", roughness=0.18, metallic=0.94, bump_strength=0.02
    )
    palette["Mat_MTL_Clock_Black_Enamel"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Clock_Black_Enamel", "#121417", roughness=0.15, metallic=0.55, bump_strength=0.01
    )
    palette["Mat_MTL_White_Trim"] = kit.get_or_create_pbr_material(
        "Mat_MTL_White_Trim", "#EAE6DF", roughness=0.45, metallic=0.05, bump_strength=0.03
    )
    palette["Mat_MTL_Garden_Lawn"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Garden_Lawn", "#45632D", roughness=0.82, metallic=0.0, bump_strength=0.22, noise_scale=35.0
    )
    palette["Mat_MTL_Summer_Canopy_Green"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Summer_Canopy_Green", "#3D6426", roughness=0.62, metallic=0.0, bump_strength=0.16, noise_scale=28.0
    )

    if "Mat_MTL_Portal_Warm_Glow" not in bpy.data.materials:
        mat = bpy.data.materials.new("Mat_MTL_Portal_Warm_Glow")
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (0.98, 0.78, 0.42, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.25
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (1.0, 0.78, 0.42, 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 2.5
        palette["Mat_MTL_Portal_Warm_Glow"] = mat
    else:
        palette["Mat_MTL_Portal_Warm_Glow"] = bpy.data.materials["Mat_MTL_Portal_Warm_Glow"]

    return palette


def add_bevel(obj, width=0.03, segments=2):
    if obj and obj.type == 'MESH':
        bev = obj.modifiers.new(name="ArchBevel", type='BEVEL')
        bev.width = width
        bev.segments = segments
        bev.limit_method = 'ANGLE'
        bev.angle_limit = math.radians(32.0)


def set_smooth(obj):
    if obj and obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True


def create_box(name, center, dims, rot_z, mat, col, bevel_width=0.025):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=dims, verts=bm.verts)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, 'Z'), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()

    if mat:
        obj.data.materials.append(mat)
    if bevel_width > 0.0:
        add_bevel(obj, width=bevel_width, segments=2)
    return obj


def create_cylinder(name, center, radius, depth, rot_euler, mat, col, segments=24, smooth=True):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=radius, radius2=radius, depth=depth)
    rot_mat = Euler(rot_euler, 'XYZ').to_matrix() if rot_euler else Matrix.Identity(3)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=rot_mat, verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()

    if mat:
        obj.data.materials.append(mat)
    if smooth:
        set_smooth(obj)
    return obj


def create_cone(name, center, r1, r2, depth, rot_z, mat, col, segments=12, smooth=False):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r1, radius2=r2, depth=depth)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, 'Z'), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()

    if mat:
        obj.data.materials.append(mat)
    if smooth:
        set_smooth(obj)
    else:
        add_bevel(obj, width=0.02, segments=1)
    return obj


def create_gothic_arch_recess(
    name, pos, width, height, depth, rot_z, mat_frame, mat_inner, col,
    add_tracery=True, mat_tracery=None, add_sill=True
):
    """
    Creates a 3D Gothic pointed-arch window or portal bay where:
    - In local coords before rotation (`rot_z`):
      +X = horizontal width along the wall
      +Y = OUTWARD from the wall face (so `y = +0.22` projects out in front of the wall, and `y = -depth` recesses into the wall!)
      +Z = vertical height up the wall
    This guarantees that the stone hood molding, archivolts, 3D lancet mullions, transoms, and window sills
    are 100% visible in front of the stained glass and never buried behind the wall face!
    """
    if mat_tracery is None:
        mat_tracery = mat_frame

    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)

    bm = bmesh.new()
    hw = width * 0.5
    spring_z = height * 0.64
    arch_pts = [(-hw, 0.0, 0.0), (-hw, 0.0, spring_z)]
    steps = 10
    for i in range(1, steps):
        t = i / steps
        ang = t * (math.pi * 0.5)
        px = -hw * math.cos(ang)
        pz = spring_z + (height - spring_z) * math.sin(ang)
        arch_pts.append((px, 0.0, pz))
    arch_pts.append((0.0, 0.0, height))
    for i in range(steps - 1, 0, -1):
        t = i / steps
        ang = t * (math.pi * 0.5)
        px = hw * math.cos(ang)
        pz = spring_z + (height - spring_z) * math.sin(ang)
        arch_pts.append((px, 0.0, pz))
    arch_pts.extend([(hw, 0.0, spring_z), (hw, 0.0, 0.0)])

    # Note: +Y is OUTWARD from the wall!
    # Outer projecting hood molding at y = +0.26m, inner splayed jamb ring at y = +0.06m
    v_hood_out = [bm.verts.new((p[0] * 1.12, 0.26, p[2] * 1.03)) for p in arch_pts]
    v_hood_wall = [bm.verts.new((p[0] * 1.14, 0.02, p[2] * 1.04)) for p in arch_pts]
    v_front = [bm.verts.new((p[0], 0.22, p[2])) for p in arch_pts]
    v_back = [bm.verts.new((p[0] * 0.90, 0.04, p[2] * 0.98)) for p in arch_pts]

    try:
        f_back = bm.faces.new(v_back)
        f_back.material_index = 1
    except ValueError:
        pass

    n_pts = len(arch_pts)
    for i in range(n_pts - 1):
        j = i + 1
        try:
            # Outer return of hood molding to wall
            f_hw = bm.faces.new([v_hood_wall[i], v_hood_wall[j], v_hood_out[j], v_hood_out[i]])
            f_hw.material_index = 0
            # Front face of stone hood molding
            f_hood = bm.faces.new([v_hood_out[i], v_hood_out[j], v_front[j], v_front[i]])
            f_hood.material_index = 0
            # Deep splayed stone jamb / archivolt reveal down to the glass plane
            f_side = bm.faces.new([v_front[i], v_front[j], v_back[j], v_back[i]])
            f_side.material_index = 0
        except ValueError:
            pass

    # Projecting Stone Window Sill + 2 Carved Corbel Brackets at bottom of window (at y = +0.18m)
    if add_sill:
        sill_geom = bmesh.ops.create_cube(bm, size=1.0)
        s_verts = sill_geom["verts"]
        bmesh.ops.scale(bm, vec=(width * 1.20, 0.38, 0.26), verts=s_verts)
        bmesh.ops.translate(bm, vec=(0.0, 0.16, -0.10), verts=s_verts)
        for f in bm.faces:
            if all(v in s_verts for v in f.verts):
                f.material_index = 0
        for corb_x in (-hw * 0.78, hw * 0.78):
            c_geom = bmesh.ops.create_cube(bm, size=1.0)
            c_verts = c_geom["verts"]
            bmesh.ops.scale(bm, vec=(0.28, 0.30, 0.34), verts=c_verts)
            bmesh.ops.translate(bm, vec=(corb_x, 0.14, -0.35), verts=c_verts)
            for f in bm.faces:
                if all(v in c_verts for v in f.verts):
                    f.material_index = 0

    # 3D Gothic Lancet Mullions, Transoms & Tracery IN FRONT of the glass plane (at y = +0.09m to +0.16m)
    if add_tracery and width >= 1.2:
        # 2 vertical primary mullions dividing the window into 3 lancet lights
        for m_x in (-width * 0.18, width * 0.18):
            m_geom = bmesh.ops.create_cube(bm, size=1.0)
            m_verts = m_geom["verts"]
            bmesh.ops.scale(bm, vec=(0.11, 0.12, height * 0.88), verts=m_verts)
            bmesh.ops.translate(bm, vec=(m_x, 0.10, height * 0.44), verts=m_verts)
            for f in bm.faces:
                if all(v in m_verts for v in f.verts):
                    f.material_index = 2

        # 3 horizontal transoms across the tall Gothic window (at 28%, 54%, and 74% height)
        for t_z in (height * 0.28, height * 0.54, height * 0.74):
            t_geom = bmesh.ops.create_cube(bm, size=1.0)
            t_verts = t_geom["verts"]
            w_at_z = width * (0.90 if t_z < spring_z else 0.72)
            bmesh.ops.scale(bm, vec=(w_at_z, 0.12, 0.13), verts=t_verts)
            bmesh.ops.translate(bm, vec=(0.0, 0.10, t_z), verts=t_verts)
            for f in bm.faces:
                if all(v in t_verts for v in f.verts):
                    f.material_index = 2

        # Fine secondary muntin grid bars inside each lancet
        for sub_x in (-width * 0.33, 0.0, width * 0.33):
            sm_geom = bmesh.ops.create_cube(bm, size=1.0)
            sm_verts = sm_geom["verts"]
            bmesh.ops.scale(bm, vec=(0.045, 0.08, height * 0.80), verts=sm_verts)
            bmesh.ops.translate(bm, vec=(sub_x, 0.08, height * 0.40), verts=sm_verts)
            for f in bm.faces:
                if all(v in sm_verts for v in f.verts):
                    f.material_index = 2

    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, 'Z'), verts=bm.verts)
    bmesh.ops.translate(bm, vec=pos, verts=bm.verts)

    bm.to_mesh(mesh)
    bm.free()

    obj.data.materials.append(mat_frame)
    obj.data.materials.append(mat_inner)
    obj.data.materials.append(mat_tracery)
    add_bevel(obj, width=0.015, segments=1)
    return obj


def create_recessed_casement_window(
    name, pos, width, height, depth, rot_z, mat_stone, mat_trim, mat_glass, col
):
    """
    Creates a 3D rectangular casement window where +Y is OUTWARD from the wall face:
    - Outer projecting stone surround (`y = +0.20m`)
    - Projecting stone sill (`y = +0.24m`) and stone lintel/keystone
    - Recessed reflective glass plane (`y = +0.04m`)
    - 3D white wooden multi-pane casement mullion/transom grid (`y = +0.09m`) clearly visible in front of glass!
    """
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)

    bm = bmesh.new()
    hw = width * 0.5
    hh = height * 0.5
    v_wall = [
        bm.verts.new((-hw - 0.16, 0.01, -hh - 0.12)),
        bm.verts.new((hw + 0.16, 0.01, -hh - 0.12)),
        bm.verts.new((hw + 0.16, 0.01, hh + 0.20)),
        bm.verts.new((-hw - 0.16, 0.01, hh + 0.20)),
    ]
    v_out = [
        bm.verts.new((-hw - 0.14, 0.18, -hh - 0.10)),
        bm.verts.new((hw + 0.14, 0.18, -hh - 0.10)),
        bm.verts.new((hw + 0.14, 0.18, hh + 0.18)),
        bm.verts.new((-hw - 0.14, 0.18, hh + 0.18)),
    ]
    v_in_f = [
        bm.verts.new((-hw, 0.18, -hh)),
        bm.verts.new((hw, 0.18, -hh)),
        bm.verts.new((hw, 0.18, hh)),
        bm.verts.new((-hw, 0.18, hh)),
    ]
    v_in_b = [
        bm.verts.new((-hw, 0.04, -hh)),
        bm.verts.new((hw, 0.04, -hh)),
        bm.verts.new((hw, 0.04, hh)),
        bm.verts.new((-hw, 0.04, hh)),
    ]

    f_glass = bm.faces.new(v_in_b)
    f_glass.material_index = 2

    for i in range(4):
        j = (i + 1) % 4
        f_side = bm.faces.new([v_wall[i], v_wall[j], v_out[j], v_out[i]])
        f_side.material_index = 0
        f_frame = bm.faces.new([v_out[i], v_out[j], v_in_f[j], v_in_f[i]])
        f_frame.material_index = 0
        f_jamb = bm.faces.new([v_in_f[i], v_in_f[j], v_in_b[j], v_in_b[i]])
        f_jamb.material_index = 0

    # Projecting Stone Sill at bottom & Keystone Lintel at top
    sill = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=(width + 0.40, 0.28, 0.18), verts=sill)
    bmesh.ops.translate(bm, vec=(0.0, 0.14, -hh - 0.09), verts=sill)
    for f in bm.faces:
        if all(v in sill for v in f.verts):
            f.material_index = 0

    lintel = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=(width + 0.36, 0.24, 0.26), verts=lintel)
    bmesh.ops.translate(bm, vec=(0.0, 0.12, hh + 0.13), verts=lintel)
    for f in bm.faces:
        if all(v in lintel for v in f.verts):
            f.material_index = 0

    # 3D White Wooden Casement Frame, Central Mullion & 3 Horizontal Transom Muntins (at y = +0.08m in front of glass!)
    for fx, fz, fw, fh in [
        (0.0, 0.0, 0.075, height),  # central vertical mullion
        (-hw * 0.5, 0.0, 0.04, height),  # left sub-muntin
        (hw * 0.5, 0.0, 0.04, height),  # right sub-muntin
        (0.0, hh * 0.35, width, 0.06),  # upper transom
        (0.0, -hh * 0.25, width, 0.05),  # lower muntin
        (-hw + 0.04, 0.0, 0.06, height),  # left sash frame
        (hw - 0.04, 0.0, 0.06, height),  # right sash frame
    ]:
        m_verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        bmesh.ops.scale(bm, vec=(fw, 0.07, fh), verts=m_verts)
        bmesh.ops.translate(bm, vec=(fx, 0.08, fz), verts=m_verts)
        for f in bm.faces:
            if all(v in m_verts for v in f.verts):
                f.material_index = 1

    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, 'Z'), verts=bm.verts)
    bmesh.ops.translate(bm, vec=pos, verts=bm.verts)

    bm.to_mesh(mesh)
    bm.free()

    obj.data.materials.append(mat_stone)
    obj.data.materials.append(mat_trim)
    obj.data.materials.append(mat_glass)
    return obj


def build_extruded_polygon(name, coords_xy, z_bottom, z_top, mat_wall, mat_roof, col, bevel_width=0.03):
    pts = coords_xy[:-1] if (len(coords_xy) > 1 and coords_xy[0] == coords_xy[-1]) else coords_xy
    if len(pts) < 3:
        return None
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)

    bm = bmesh.new()
    verts = [bm.verts.new((p[0], p[1], z_bottom)) for p in pts]
    try:
        face = bm.faces.new(verts)
    except ValueError:
        bm.free()
        return None
    face.normal_update()
    if face.normal.z < 0:
        face.normal_flip()

    ret = bmesh.ops.extrude_face_region(bm, geom=[face])
    ext_verts = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=ext_verts, vec=(0.0, 0.0, z_top - z_bottom))

    bm.to_mesh(mesh)
    bm.free()

    obj.data.materials.append(mat_wall)
    obj.data.materials.append(mat_roof)
    for poly in obj.data.polygons:
        if poly.normal.z > 0.7:
            poly.material_index = 1
        else:
            poly.material_index = 0
    if bevel_width > 0.0:
        add_bevel(obj, width=bevel_width, segments=2)
    return obj


def build_detailed_context_building(name, coords_xy, height, mat_wall, mat_trim, mat_roof, mat_glass, col, floor_h=3.8):
    pts = coords_xy[:-1] if (len(coords_xy) > 1 and coords_xy[0] == coords_xy[-1]) else coords_xy
    if len(pts) < 3:
        return None

    build_extruded_polygon(f"{name}_Plinth", pts, 0.0, 4.2, mat_trim, mat_roof, col, bevel_width=0.03)
    build_extruded_polygon(f"{name}_Body", pts, 4.2, height, mat_wall, mat_roof, col, bevel_width=0.03)
    build_extruded_polygon(f"{name}_Cornice", pts, height - 0.6, height + 0.45, mat_trim, mat_roof, col, bevel_width=0.03)

    n_pts = len(pts)
    n_floors = max(1, min(12, int((height - 5.0) / floor_h)))
    cx = sum(p[0] for p in pts) / n_pts
    cy = sum(p[1] for p in pts) / n_pts

    for i in range(n_pts):
        p1 = pts[i]
        p2 = pts[(i + 1) % n_pts]
        mx, my = (p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5
        if math.hypot(mx, my) > 120.0:
            continue
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        edge_len = math.hypot(dx, dy)
        if edge_len < 5.5:
            continue
        # Outward normal (nx, ny) away from polygon centroid
        nx, ny = -dy / edge_len, dx / edge_len
        if (mx + nx - cx) ** 2 + (my + ny - cy) ** 2 < (mx - nx - cx) ** 2 + (my - ny - cy) ** 2:
            nx, ny = -nx, -ny
        # Rotation angle so local +Y aligns with (nx, ny): since R(ang)*(0,1) = (-sin(ang), cos(ang)), ang = atan2(-nx, ny)
        ang = math.atan2(-nx, ny)

        n_bays = max(1, min(8, int(edge_len / 4.2)))
        for b_i in range(n_bays):
            t = (b_i + 0.5) / n_bays
            bx = p1[0] + dx * t
            by = p1[1] + dy * t
            create_recessed_casement_window(
                f"{name}_GFWin_{i}_{b_i}",
                (bx, by, 2.2),
                2.2, 2.6, 0.35,
                ang, mat_trim, mat_trim, mat_glass, col
            )
            fl_step = 2 if n_floors > 7 else 1
            for fl in range(0, n_floors, fl_step):
                wz = 6.2 + fl * floor_h
                if wz + 1.5 < height - 0.8:
                    create_recessed_casement_window(
                        f"{name}_Win_{i}_{b_i}_{fl}",
                        (bx, by, wz),
                        1.55, 2.15, 0.35,
                        ang, mat_trim, mat_trim, mat_glass, col
                    )


def build_basilica_notre_dame(bldg_osm, palette, col):
    """
    Constructs the full Basilique Notre-Dame de Montréal with deep open West Loggia arches
    (no solid box blocking the triple Gothic portico!), 3D lancet tracery, twin 69m towers,
    and side buttresses along Rue Saint-Sulpice.
    """
    mat_stone = palette["Mat_MTL_PierreGrise_Limestone"]
    mat_buff = palette["Mat_MTL_WarmBuff_Limestone"]
    mat_rubble = palette["Mat_MTL_Fieldstone_Rubble"]
    mat_vault = palette["Mat_MTL_Dark_Vault_Stone"]
    mat_slate = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_glass = palette["Mat_MTL_Stained_Glass"]
    mat_gold = palette["Mat_MTL_Gold_Leaf"]
    mat_bronze = palette["Mat_MTL_Statue_Bronze"]
    mat_iron = palette["Mat_MTL_CastIron_Black"]
    mat_copper = palette["Mat_MTL_Verdigris_Copper"]
    mat_clock = palette["Mat_MTL_Clock_Black_Enamel"]
    mat_wood = palette["Mat_MTL_Warm_Wood"]

    coords = bldg_osm["coords_xy"]

    sw_pt = Vector((-8.309, -25.949, 0.0))
    ne_pt = Vector((10.018, 10.642, 0.0))
    u_vec = (ne_pt - sw_pt).normalized()
    v_vec = Vector((u_vec.y, -u_vec.x, 0.0))
    n_west = -v_vec

    facade_mid = (sw_pt + ne_pt) * 0.5
    rot_facade = math.atan2(u_vec.y, u_vec.x)

    def to_world(lx, ly, lz=0.0):
        return (
            facade_mid.x + lx * u_vec.x + ly * n_west.x,
            facade_mid.y + lx * u_vec.y + ly * n_west.y,
            lz
        )

    # 1. Stepped Granite Parvis Stairway (6 steps + cast-iron handrails)
    for s in range(6):
        step_h = 0.20 * (s + 1)
        step_d = 5.2 - s * 0.72
        create_box(
            f"ND_Parvis_Step_{s}",
            to_world(0.0, step_d * 0.5 + 0.4, step_h * 0.5),
            (43.0 - s * 0.35, step_d, step_h),
            rot_facade,
            palette["Mat_MTL_Plaza_Light_Granite"],
            col,
            bevel_width=0.02
        )
    for rx in [-12.5, -6.2, 0.0, 6.2, 12.5]:
        create_box(f"ND_Stair_Rail_{int(rx)}", to_world(rx, 3.2, 1.15), (0.08, 3.6, 0.85), rot_facade, mat_iron, col, bevel_width=0.01)

    # 2. Exact OSM Footprint (recessed slightly at the front loggia by starting full Nave behind ly = -4.0m
    #    while keeping the full OSM polygon for the main body behind the West Loggia!)
    build_extruded_polygon("ND_OSM_Rubble_Plinth", coords, 0.0, 2.65, mat_rubble, mat_slate, col, bevel_width=0.03)
    build_extruded_polygon("ND_OSM_Plinth_Ledge", coords, 2.65, 3.05, mat_buff, mat_slate, col, bevel_width=0.03)
    build_extruded_polygon("ND_OSM_Ashlar_Nave", coords, 3.05, 25.5, mat_stone, mat_slate, col, bevel_width=0.03)

    for idx, (bz, bh) in enumerate([(11.2, 0.50), (24.6, 0.65), (25.35, 0.90)]):
        build_extruded_polygon(f"ND_OSM_BeltCourse_{idx}", coords, bz - bh * 0.5, bz + bh * 0.5, mat_buff, mat_slate, col, bevel_width=0.025)

    # 3. Vaulted Pitched Slate Roof over the 78m Nave & Choir
    mesh_roof = bpy.data.meshes.new("ND_Nave_Pitched_Roof_Mesh")
    obj_roof = bpy.data.objects.new("ND_Nave_Pitched_Roof", mesh_roof)
    col.objects.link(obj_roof)
    bm_r = bmesh.new()
    nave_hw = 17.6
    y0, y1 = -4.5, -81.5
    z_eave = 25.5
    z_ridge = 39.2
    v_sw_b = bm_r.verts.new(to_world(-nave_hw, y0, z_eave))
    v_se_b = bm_r.verts.new(to_world(-nave_hw, y1, z_eave))
    v_ne_b = bm_r.verts.new(to_world(nave_hw, y1, z_eave))
    v_nw_b = bm_r.verts.new(to_world(nave_hw, y0, z_eave))
    v_w_top = bm_r.verts.new(to_world(0.0, y0, z_ridge))
    v_e_top = bm_r.verts.new(to_world(0.0, y1, z_ridge))

    bm_r.faces.new([v_sw_b, v_se_b, v_e_top, v_w_top])
    bm_r.faces.new([v_se_b, v_ne_b, v_e_top])
    bm_r.faces.new([v_ne_b, v_nw_b, v_w_top, v_e_top])
    bm_r.faces.new([v_nw_b, v_sw_b, v_w_top])
    bm_r.faces.new([v_sw_b, v_nw_b, v_ne_b, v_se_b])
    bm_r.to_mesh(mesh_roof)
    bm_r.free()
    obj_roof.data.materials.append(mat_slate)
    add_bevel(obj_roof, width=0.03, segments=2)

    create_box("ND_Roof_Copper_Ridge", to_world(0.0, -43.0, z_ridge + 0.35), (0.65, 77.0, 0.75), rot_facade, mat_copper, col)
    create_cone("ND_East_Fleche_Base", to_world(0.0, -76.0, z_ridge + 2.8), 1.4, 1.1, 5.5, rot_facade, mat_copper, col, segments=8)
    create_cone("ND_East_Fleche_Spire", to_world(0.0, -76.0, z_ridge + 9.5), 1.1, 0.05, 8.5, rot_facade, mat_copper, col, segments=8)

    for sky_ly in [-24.0, -43.0, -61.0]:
        for side_sign in [-1.0, 1.0]:
            create_box(
                f"ND_Roof_Skylight_{int(abs(sky_ly))}_{int(side_sign)}",
                to_world(side_sign * 6.2, sky_ly, 34.4),
                (5.2, 8.5, 0.9),
                rot_facade,
                mat_glass,
                col
            )

    # Mid-Nave Cross-Gable Pediment & Twin Turrets (visible in Rue_SaintSulpice_Side_Wall.jpg)
    for side_sign, s_rot in [(-1.0, rot_facade + math.pi * 0.5), (1.0, rot_facade - math.pi * 0.5)]:
        gx = side_sign * 17.5
        gy = -41.6
        create_box(f"ND_MidNave_GableWall_{int(side_sign)}", to_world(gx, gy, 28.0), (2.2, 10.2, 6.2), rot_facade, mat_stone, col)
        create_cone(f"ND_MidNave_GablePeak_{int(side_sign)}", to_world(gx, gy, 32.8), 5.2, 0.2, 4.2, rot_facade + math.pi * 0.25, mat_buff, col, segments=4)
        for ty_off in (-4.8, 4.8):
            create_cylinder(f"ND_MidNave_Turret_{int(side_sign)}_{int(ty_off)}", to_world(gx + side_sign * 0.5, gy + ty_off, 29.8), 0.95, 7.5, (0, 0, rot_facade), mat_buff, col, segments=8)
            create_cone(f"ND_MidNave_TurretCap_{int(side_sign)}_{int(ty_off)}", to_world(gx + side_sign * 0.5, gy + ty_off, 34.8), 1.05, 0.08, 2.8, rot_facade, mat_buff, col, segments=8)

    # 4. West Front Central Screen Facade (Projecting forward to ly = +1.8m so the 3 Portico Arches recess deeply from +1.8m back to 0.0m!)
    # Upper screen wall above the loggia arches (z=14.5m to 34.8m, ly from -2.5m to +1.8m)
    create_box("ND_West_Upper_Screen", to_world(0.0, -0.35, 24.65), (18.4, 4.3, 20.3), rot_facade, mat_stone, col)

    # 4 Deeply Projecting Stone Loggia Piers at ground level (z=0.0 to 15.0m, ly from 0.0 to +1.9m) framing the 3 open Gothic Portals!
    for pier_i, pier_x in enumerate([-8.5, -2.85, 2.85, 8.5]):
        create_box(f"ND_West_Loggia_Pier_{pier_i}", to_world(pier_x, 0.95, 7.5), (1.45, 2.1, 15.0), rot_facade, mat_stone, col)
        # Engaged Octagonal Buttress Pilasters rising from z=0 to 36.8m on the front face of each pier (ly = +2.05m)
        create_cylinder(
            f"ND_West_Screen_Pilaster_{pier_i}",
            to_world(pier_x, 2.05, 18.2),
            0.52, 34.4, (0, 0, rot_facade),
            mat_buff, col, segments=8, smooth=False
        )
        create_cone(
            f"ND_West_Screen_PilPin_{pier_i}",
            to_world(pier_x, 2.05, 36.9),
            0.58, 0.06, 3.2,
            rot_facade, mat_buff, col, segments=8
        )

    # Molded Horizontal Cornices on West Screen (at ly = +2.0m)
    create_box("ND_West_Lower_Cornice", to_world(0.0, 1.85, 14.8), (19.2, 1.15, 0.95), rot_facade, mat_buff, col)
    create_box("ND_West_Upper_Cornice", to_world(0.0, 1.90, 33.2), (19.2, 1.25, 0.95), rot_facade, mat_buff, col)

    # Crenellated Gothic Battlements (Merlons) + Central Cross at top of West Screen (z=34.5m to 36.4m)
    for m_idx in range(9):
        mx = -7.6 + m_idx * 1.9
        create_box(f"ND_Battlement_Merlon_{m_idx}", to_world(mx, 1.65, 35.4), (1.15, 0.95, 1.75), rot_facade, mat_stone, col)
        create_box(f"ND_Battlement_Cap_{m_idx}", to_world(mx, 1.65, 36.4), (1.32, 1.12, 0.26), rot_facade, mat_buff, col)

    create_box("ND_Center_Cross_V", to_world(0.0, 1.65, 38.3), (0.38, 0.38, 3.9), rot_facade, mat_iron, col)
    create_box("ND_Center_Cross_H", to_world(0.0, 1.65, 39.0), (1.90, 0.35, 0.35), rot_facade, mat_iron, col)

    # Triple Pointed-Arch Entrance Loggia (Ground Level, lx = -5.7, 0.0, +5.7)
    # Placed at ly = +1.75m with dark vaulted stone recess, bronze/wood inner doors, and upper Gothic windows!
    for p_idx, px in enumerate([-5.7, 0.0, 5.7]):
        arch_h = 13.5 if p_idx == 1 else 12.8
        arch_w = 4.5 if p_idx == 1 else 4.1
        # Outer stone pointed arch & dark vaulted recess (`mat_vault`)
        create_gothic_arch_recess(
            f"ND_West_Loggia_Arch_{p_idx}",
            to_world(px, 1.75, 1.1),
            arch_w, arch_h, 1.8,
            rot_facade, mat_buff, mat_vault, col, add_tracery=False, add_sill=False
        )
        # Inner wooden/bronze portal doors & upper loggia Gothic tracery windows inside the dark vaulted recess!
        create_gothic_arch_recess(
            f"ND_West_Inner_Door_{p_idx}",
            to_world(px, 1.82, 1.15),
            arch_w * 0.72, 5.4, 0.5,
            rot_facade, mat_bronze, mat_wood, col, add_tracery=True, mat_tracery=mat_bronze, add_sill=False
        )
        create_gothic_arch_recess(
            f"ND_West_Loggia_UpperWindow_{p_idx}",
            to_world(px, 1.82, 7.0),
            arch_w * 0.70, 5.2, 0.5,
            rot_facade, mat_buff, mat_glass, col, add_tracery=True, mat_tracery=mat_iron
        )

    # 3 Sculpted Gothic Statue Niches on Upper West Screen (z=16.2m to 29.8m, at ly = +1.80m!)
    for n_idx, nx in enumerate([-5.7, 0.0, 5.7]):
        niche_h = 12.4 if n_idx == 1 else 11.5
        create_gothic_arch_recess(
            f"ND_Statue_Niche_{n_idx}",
            to_world(nx, 1.80, 16.4),
            4.1, niche_h, 1.2,
            rot_facade, mat_buff, mat_vault, col, add_tracery=True, mat_tracery=mat_buff
        )
        create_box(f"ND_Statue_Pedestal_{n_idx}", to_world(nx, 2.05, 18.8), (1.15, 0.85, 3.2), rot_facade, mat_buff, col)
        create_cylinder(
            f"ND_Statue_Figure_{n_idx}",
            to_world(nx, 2.10, 21.8),
            0.48, 2.9, (0, 0, rot_facade),
            mat_gold if n_idx == 1 else mat_buff, col, segments=16
        )
        create_cone(f"ND_Statue_Canopy_{n_idx}", to_world(nx, 2.10, 24.5), 0.78, 0.1, 1.9, rot_facade, mat_buff, col, segments=8)

    # 5. Twin 69m Gothic Revival West Towers:
    #    - SW Tower ("La Persévérance"): centered at lx = -14.2, ly = -3.4 (front face at ly = +1.9m!)
    #    - NE Tower ("La Tempérance"): centered at lx = +14.2, ly = -3.4 (front face at ly = +1.9m!)
    for t_name, tx in [("SW_Perseverance", -14.2), ("NE_Temperance", 14.2)]:
        ty = -3.4
        tiers = [
            (0.0, 14.8, 10.6, 10.6),
            (14.8, 28.5, 10.2, 10.2),
            (28.5, 42.0, 9.8, 9.8),
            (42.0, 58.5, 9.4, 9.4),
        ]
        for tier_i, (z0, z1, w_x, w_y) in enumerate(tiers):
            create_box(
                f"ND_Tower_{t_name}_Tier_{tier_i}",
                to_world(tx, ty, (z0 + z1) * 0.5),
                (w_x, w_y, z1 - z0),
                rot_facade,
                mat_stone,
                col
            )
            create_box(
                f"ND_Tower_{t_name}_Cornice_{tier_i}",
                to_world(tx, ty, z1),
                (w_x + 0.75, w_y + 0.75, 0.80),
                rot_facade,
                mat_buff,
                col
            )

        # 4 Octagonal Corner Buttresses on each Tower extending from z=0 to 69.2m
        for bx_s in [-1.0, 1.0]:
            for by_s in [-1.0, 1.0]:
                b_lx = tx + bx_s * 4.95
                b_ly = ty + by_s * 4.95
                create_cylinder(
                    f"ND_Tower_{t_name}_Buttress_{int(bx_s)}_{int(by_s)}",
                    to_world(b_lx, b_ly, 29.75),
                    1.08, 59.5, (0, 0, rot_facade),
                    mat_buff, col, segments=8, smooth=False
                )
                for gz in [14.8, 28.5, 42.0, 58.5]:
                    create_box(
                        f"ND_Tower_{t_name}_ButtCap_{int(bx_s)}_{int(by_s)}_{int(gz)}",
                        to_world(b_lx, b_ly, gz),
                        (2.40, 2.40, 0.70),
                        rot_facade,
                        mat_buff,
                        col
                    )
                create_cone(
                    f"ND_Tower_{t_name}_Pinnacle_{int(bx_s)}_{int(by_s)}",
                    to_world(b_lx, b_ly, 64.35),
                    1.08, 0.08, 9.7,
                    rot_facade,
                    mat_buff, col, segments=8
                )

        # Crenellated Parapet & Intermediate Pinnacles at top of Tower (z=58.5 to 63.5m)
        for fx, fy in [(0.0, 4.7), (0.0, -4.7), (-4.7, 0.0), (4.7, 0.0)]:
            create_box(
                f"ND_Tower_{t_name}_Parapet_{int(fx)}_{int(fy)}",
                to_world(tx + fx, ty + fy, 59.8),
                (7.8 if fx == 0 else 0.75, 0.75 if fx == 0 else 7.8, 2.5),
                rot_facade,
                mat_stone, col
            )
            create_cone(
                f"ND_Tower_{t_name}_MidPin_{int(fx)}_{int(fy)}",
                to_world(tx + fx, ty + fy, 62.5),
                0.58, 0.06, 4.4,
                rot_facade,
                mat_buff, col, segments=8
            )

        # Tower Lancet Windows & Clock Faces on Front & Side faces (with outward +Y normal!)
        for side_i, (sx, sy, s_rot) in enumerate([
            (0.0, 5.30, rot_facade),  # Front (NW, outward +Y is n_west)
            (-5.30, 0.0, rot_facade + math.pi * 0.5),  # SW side (outward +Y is -u_vec)
            (5.30, 0.0, rot_facade - math.pi * 0.5),  # NE side (outward +Y is +u_vec)
        ]):
            if side_i == 0 or (t_name == "NE_Temperance" and side_i == 2) or (t_name == "SW_Perseverance" and side_i == 1):
                create_gothic_arch_recess(
                    f"ND_Tower_{t_name}_Lancet_T0_{side_i}",
                    to_world(tx + sx, ty + sy, 3.2),
                    3.2, 9.4, 0.65,
                    s_rot, mat_buff, mat_glass, col, add_tracery=True, mat_tracery=mat_iron
                )
            create_gothic_arch_recess(
                f"ND_Tower_{t_name}_Lancet_T1_{side_i}",
                to_world(tx + sx * 0.96, ty + sy * 0.96, 16.5),
                3.1, 9.8, 0.65,
                s_rot, mat_buff, mat_glass, col, add_tracery=True, mat_tracery=mat_iron
            )
            create_gothic_arch_recess(
                f"ND_Tower_{t_name}_Lancet_T2_{side_i}",
                to_world(tx + sx * 0.93, ty + sy * 0.93, 29.5),
                2.9, 7.2, 0.65,
                s_rot, mat_buff, mat_iron, col, add_tracery=True, mat_tracery=mat_buff
            )
            c_pos = to_world(tx + sx * 0.94, ty + sy * 0.94, 38.9)
            create_cylinder(
                f"ND_Tower_{t_name}_ClockRing_{side_i}",
                c_pos, 1.85, 0.38,
                (math.pi * 0.5, 0.0, s_rot),
                mat_buff, col, segments=24
            )
            create_cylinder(
                f"ND_Tower_{t_name}_ClockDial_{side_i}",
                to_world(tx + sx * 0.96, ty + sy * 0.96, 38.9), 1.48, 0.28,
                (math.pi * 0.5, 0.0, s_rot),
                mat_clock, col, segments=24
            )
            create_box(
                f"ND_Tower_{t_name}_ClockHand_{side_i}",
                to_world(tx + sx * 0.98, ty + sy * 0.98, 39.2),
                (0.18, 0.18, 1.15),
                s_rot, mat_gold, col
            )

        # Tier 3 (z=43.5m): Grand Gothic Belfry Openings on all 4 sides of the upper tower
        for side_i, (sx, sy, s_rot) in enumerate([
            (0.0, 4.70, rot_facade),
            (0.0, -4.70, rot_facade + math.pi),
            (-4.70, 0.0, rot_facade + math.pi * 0.5),
            (4.70, 0.0, rot_facade - math.pi * 0.5),
        ]):
            create_gothic_arch_recess(
                f"ND_Tower_{t_name}_Belfry_{side_i}",
                to_world(tx + sx, ty + sy, 43.6),
                4.2, 12.2, 0.85,
                s_rot, mat_buff, mat_iron, col, add_tracery=True, mat_tracery=mat_buff
            )

    # 6. Side Aisle Buttresses, Pinnacles, Tall Gothic Tracery Windows & Gabled Side Entrance Porch
    #    Wait: What is the exact lx of the Basilica NE wall along Rue Saint-Sulpice?
    #    Let's check OSM coords: NE corner is (10.018, 10.642), SE corner is (102.337, -35.689).
    #    In `to_world(lx, ly)`, `ne_pt` is at `lx = +20.49m`!
    #    Aha! Earlier we placed the side buttresses and windows at `wall_lx = +17.8m`, which was 2.7m INSIDE the `ND_OSM_Ashlar_Nave` polygon (`lx = +20.49m`)!
    #    That's why the side windows and buttresses along Rue Saint-Sulpice were hidden inside the `ND_OSM_Ashlar_Nave` wall in Cameras 3 and 4!
    #    Let's place the NE side buttresses and windows right on the true outer wall surface at `wall_lx = +20.48m` (NE side) and `wall_lx = -20.48m` (SW side)!
    for bay_i in range(9):
        bay_ly = -10.5 - bay_i * 8.4
        for side_sign, s_rot in [(-1.0, rot_facade + math.pi * 0.5), (1.0, rot_facade - math.pi * 0.5)]:
            wall_lx = side_sign * 20.45
            # Stepped Stone Buttress Pier projecting OUTWARD from `wall_lx` (`20.45m` to `21.65m`)!
            create_box(
                f"ND_Nave_Buttress_Lower_{bay_i}_{int(side_sign)}",
                to_world(wall_lx + side_sign * 0.65, bay_ly, 6.5),
                (1.6, 1.35, 13.0),
                rot_facade,
                mat_stone, col
            )
            create_box(
                f"ND_Nave_Buttress_Upper_{bay_i}_{int(side_sign)}",
                to_world(wall_lx + side_sign * 0.50, bay_ly, 19.2),
                (1.3, 1.20, 12.6),
                rot_facade,
                mat_stone, col
            )
            for bz_wrap in [2.85, 13.0, 24.8]:
                create_box(
                    f"ND_Nave_ButtWrap_{bay_i}_{int(side_sign)}_{int(bz_wrap)}",
                    to_world(wall_lx + side_sign * 0.65, bay_ly, bz_wrap),
                    (1.95, 1.65, 0.45),
                    rot_facade,
                    mat_buff, col
                )
            # Octagonal Pinnacle rising above the cornice line (z=25.5 to 30.2m)
            create_cylinder(
                f"ND_Nave_ButtPinShaft_{bay_i}_{int(side_sign)}",
                to_world(wall_lx + side_sign * 0.50, bay_ly, 26.8),
                0.62, 2.6, (0, 0, rot_facade),
                mat_buff, col, segments=8, smooth=False
            )
            create_cone(
                f"ND_Nave_ButtPinSpire_{bay_i}_{int(side_sign)}",
                to_world(wall_lx + side_sign * 0.50, bay_ly, 29.4),
                0.68, 0.08, 2.8,
                rot_facade,
                mat_buff, col, segments=8
            )

            # Tall Pointed-Arch Stained Glass Window with 3-Lancet Tracery between buttresses (z=5.2m to 21.6m)
            if bay_i < 8:
                win_ly = bay_ly - 4.2
                create_gothic_arch_recess(
                    f"ND_Nave_SideWindow_{bay_i}_{int(side_sign)}",
                    to_world(wall_lx, win_ly, 5.2),
                    3.9, 16.2, 0.65,
                    s_rot, mat_buff, mat_glass, col,
                    add_tracery=True, mat_tracery=mat_iron, add_sill=True
                )
                # Gabled Stone Side Entrance Porch along Rue Saint-Sulpice (at bay 5, right in front of Camera 4!)
                if side_sign > 0 and bay_i in (4, 5):
                    if bay_i == 4:
                        create_box(
                            "ND_RueStSulpice_SidePorch",
                            to_world(wall_lx + 0.95, win_ly, 1.8),
                            (2.0, 5.2, 3.6),
                            rot_facade, mat_rubble, col
                        )
                        create_cone(
                            "ND_RueStSulpice_SidePorch_Gable",
                            to_world(wall_lx + 1.0, win_ly, 4.3),
                            3.4, 0.15, 1.8,
                            rot_facade + math.pi * 0.25, mat_slate, col, segments=4
                        )
                        create_gothic_arch_recess(
                            "ND_RueStSulpice_SidePorch_Door",
                            to_world(wall_lx + 1.92, win_ly, 0.2),
                            2.4, 3.1, 0.5,
                            s_rot, mat_buff, mat_wood, col, add_tracery=False, add_sill=False
                        )
                else:
                    # Arched crypt window with iron grille in the fieldstone basement plinth
                    create_gothic_arch_recess(
                        f"ND_Crypt_Win_{bay_i}_{int(side_sign)}",
                        to_world(wall_lx, win_ly, 0.65),
                        1.35, 1.55, 0.45,
                        s_rot, mat_buff, mat_iron, col, add_tracery=True, mat_tracery=mat_iron, add_sill=False
                    )

    # Iron Snow-Guard Railings along the Basilica Roof Eaves (at lx = +/-20.4m)
    for side_sign in (-1.0, 1.0):
        create_box(
            f"ND_Roof_SnowGuard_{int(side_sign)}",
            to_world(side_sign * 20.35, -43.0, 26.05),
            (0.15, 74.0, 0.65),
            rot_facade, mat_iron, col, bevel_width=0.01
        )

    # 7. Chapelle du Sacré-Cœur & Sacristy Eastern Extension
    create_box("ND_SacredHeart_Chapel_Roof", to_world(2.5, -88.5, 21.5), (26.0, 18.5, 5.5), rot_facade, mat_copper, col)
    for sk_i in [-5.0, 0.0, 5.0]:
        create_box(f"ND_SacredHeart_Skylight_{int(sk_i)}", to_world(sk_i + 2.5, -88.5, 24.5), (2.2, 15.0, 0.8), rot_facade, mat_glass, col)

    # 8. Octagonal Baptistery/Chapel at SW side of Basilica
    create_cylinder("ND_SW_Octagonal_Chapel", to_world(-22.2, -16.5, 5.5), 4.6, 11.0, (0, 0, rot_facade), mat_stone, col, segments=8, smooth=False)
    create_cone("ND_SW_Octagonal_Roof", to_world(-22.2, -16.5, 12.8), 4.9, 0.15, 3.6, rot_facade, mat_copper, col, segments=8)


def build_seminaire_saint_sulpice(seminaire_osm, link_osm, palette, col):
    """
    Constructs the Vieux Séminaire de Saint-Sulpice (1684-1687) & Forecourt Wall with deep 3D architectural relief
    matching `Seminaire_Saint_Sulpice_Clock.jpg` and `Center_South_to_Basilica.jpg`.
    """
    mat_rubble = palette["Mat_MTL_Fieldstone_Rubble"]
    mat_quoin = palette["Mat_MTL_PierreGrise_Limestone"]
    mat_buff = palette["Mat_MTL_WarmBuff_Limestone"]
    mat_slate = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_white = palette["Mat_MTL_White_Trim"]
    mat_gold = palette["Mat_MTL_Gold_Leaf"]
    mat_clock = palette["Mat_MTL_Clock_Black_Enamel"]
    mat_wood = palette["Mat_MTL_Warm_Wood"]
    mat_copper = palette["Mat_MTL_Verdigris_Copper"]
    mat_iron = palette["Mat_MTL_CastIron_Black"]

    sw_pt = Vector((-8.309, -25.949, 0.0))
    ne_pt = Vector((10.018, 10.642, 0.0))
    u_vec = (ne_pt - sw_pt).normalized()
    n_west = Vector((-u_vec.y, u_vec.x, 0.0))
    rot_nd = math.atan2(u_vec.y, u_vec.x)
    sem_orig = sw_pt

    def sem_world(lx, ly, lz=0.0):
        return (
            sem_orig.x + lx * u_vec.x + ly * n_west.x,
            sem_orig.y + lx * u_vec.y + ly * n_west.y,
            lz
        )

    if seminaire_osm:
        build_extruded_polygon("Seminaire_OSM_MainWings", seminaire_osm["coords_xy"], 0.0, 12.8, mat_rubble, mat_slate, col)
    if link_osm:
        build_extruded_polygon("Seminaire_OSM_EastLinkWing", link_osm["coords_xy"], 0.0, 11.5, mat_rubble, mat_slate, col)

    # 1. Twin-Arch Gothic Stone Gatehouse between Basilica SW Tower and Séminaire NE Wing
    create_box("Sem_Gatehouse_Wall", sem_world(-3.4, -2.5, 4.4), (6.8, 1.8, 8.8), rot_nd, mat_quoin, col)
    for g_idx, gx in enumerate([-1.8, -5.0]):
        create_gothic_arch_recess(
            f"Sem_Gatehouse_Arch_{g_idx}",
            sem_world(gx, -1.6, 0.4),
            2.5, 5.6, 1.2,
            rot_nd, mat_buff, mat_wood, col, add_tracery=True, mat_tracery=mat_iron, add_sill=False
        )
    for cm_i in range(4):
        create_box(f"Sem_Gate_Merlon_{cm_i}", sem_world(-1.2 - cm_i * 1.5, -1.8, 9.2), (0.85, 0.8, 0.9), rot_nd, mat_quoin, col)

    # 2. NE Gable-Ended Seminary Wing (prominently visible on the right of `Seminaire_Saint_Sulpice_Clock.jpg`!)
    ne_wing_x = -11.2
    ne_wing_y = -13.5
    create_box("Sem_NE_Wing_Body", sem_world(ne_wing_x, ne_wing_y, 7.2), (9.4, 22.0, 14.4), rot_nd, mat_quoin, col)
    for bz in [3.8, 11.2, 14.5]:
        create_box(f"Sem_NE_Wing_Belt_{int(bz)}", sem_world(ne_wing_x, ne_wing_y, bz), (9.85, 22.4, 0.45), rot_nd, mat_buff, col)

    mesh_nep = bpy.data.meshes.new("Sem_NE_Wing_Roof_Mesh")
    obj_nep = bpy.data.objects.new("Sem_NE_Wing_Roof", mesh_nep)
    col.objects.link(obj_nep)
    bm_nep = bmesh.new()
    v1 = bm_nep.verts.new(sem_world(ne_wing_x - 4.9, ne_wing_y + 11.3, 14.7))
    v2 = bm_nep.verts.new(sem_world(ne_wing_x + 4.9, ne_wing_y + 11.3, 14.7))
    v3 = bm_nep.verts.new(sem_world(ne_wing_x + 4.9, ne_wing_y - 11.3, 14.7))
    v4 = bm_nep.verts.new(sem_world(ne_wing_x - 4.9, ne_wing_y - 11.3, 14.7))
    vt_f = bm_nep.verts.new(sem_world(ne_wing_x, ne_wing_y + 11.3, 18.2))
    vt_b = bm_nep.verts.new(sem_world(ne_wing_x, ne_wing_y - 11.3, 18.2))
    bm_nep.faces.new([v1, v2, vt_f])
    bm_nep.faces.new([v2, v3, vt_b, vt_f])
    bm_nep.faces.new([v3, v4, vt_b])
    bm_nep.faces.new([v4, v1, vt_f, vt_b])
    bm_nep.to_mesh(mesh_nep)
    bm_nep.free()
    obj_nep.data.materials.append(mat_slate)
    add_bevel(obj_nep, width=0.03, segments=2)

    create_box("Sem_NE_Pediment_Base", sem_world(ne_wing_x, ne_wing_y + 11.15, 14.65), (10.2, 0.85, 0.55), rot_nd, mat_buff, col)

    # Alternating Dressed Limestone Corner Quoins on NE Wing corners
    for qz_i in range(14):
        qz = 0.5 + qz_i * 1.0
        q_w = 0.90 if (qz_i % 2 == 0) else 0.55
        for q_side in [-1.0, 1.0]:
            create_box(
                f"Sem_NE_Quoin_{qz_i}_{int(q_side)}",
                sem_world(ne_wing_x + q_side * (4.7 - q_w * 0.4), ne_wing_y + 11.0, qz),
                (q_w, 0.70, 0.84),
                rot_nd, mat_buff, col
            )

    # 3D Multi-Pane Casement Windows on NE Wing Front (NW, ly = ne_wing_y + 11.0) & Courtyard (SW, lx = ne_wing_x - 4.7)
    for fl_i, fl_z in enumerate([2.3, 5.8, 9.3, 12.6]):
        win_h = 2.25 if fl_i < 3 else 1.55
        for col_x in [-2.4, 2.4]:
            create_recessed_casement_window(
                f"Sem_NE_FrontWin_{fl_i}_{int(col_x)}",
                sem_world(ne_wing_x + col_x, ne_wing_y + 11.0, fl_z),
                1.55, win_h, 0.45,
                rot_nd, mat_buff, mat_white, mat_glass, col
            )
        for wy_off in [7.5, 3.0, -1.5, -6.0]:
            create_recessed_casement_window(
                f"Sem_NE_SideWin_{fl_i}_{int(wy_off)}",
                sem_world(ne_wing_x - 4.7, ne_wing_y + wy_off, fl_z),
                1.45, win_h, 0.45,
                rot_nd + math.pi * 0.5, mat_buff, mat_white, mat_glass, col
            )

    # 3. Historic Fieldstone Forecourt Wall & Cut-Stone Gate Piers along Rue Notre-Dame Ouest
    create_box("Sem_Forecourt_Wall_EastSeg", sem_world(-20.5, -2.2, 1.85), (10.5, 0.95, 3.7), rot_nd, mat_rubble, col)
    create_box("Sem_Forecourt_Wall_EastCap", sem_world(-20.5, -2.2, 3.85), (10.8, 1.15, 0.35), rot_nd, mat_buff, col)

    create_box("Sem_Forecourt_Wall_WestSeg", sem_world(-39.5, -2.2, 1.85), (16.5, 0.95, 3.7), rot_nd, mat_rubble, col)
    create_box("Sem_Forecourt_Wall_WestCap", sem_world(-39.5, -2.2, 3.85), (16.8, 1.15, 0.35), rot_nd, mat_buff, col)

    for p_side in [-2.3, 2.3]:
        px = -28.5 + p_side
        create_box(f"Sem_Forecourt_GatePier_{int(p_side)}", sem_world(px, -2.1, 2.15), (1.15, 1.35, 4.3), rot_nd, mat_buff, col)
        create_box(f"Sem_Forecourt_GatePierCap_{int(p_side)}", sem_world(px, -2.1, 4.45), (1.40, 1.60, 0.38), rot_nd, mat_quoin, col)

    create_box("Sem_Forecourt_Paving", sem_world(-28.5, -12.5, 0.10), (34.0, 20.5, 0.20), rot_nd, palette["Mat_MTL_Plaza_Light_Granite"], col)

    # 4. Main Central Corps-de-Logis & Famous 1701 Clock Pavilion
    corps_x = -28.5
    corps_y = -24.5
    create_box("Sem_Main_CorpsDeLogis", sem_world(corps_x, corps_y, 7.0), (34.0, 12.5, 14.0), rot_nd, mat_rubble, col)
    for bz in [4.0, 11.2, 14.1]:
        create_box(f"Sem_Corps_Belt_{int(bz)}", sem_world(corps_x, corps_y, bz), (34.5, 12.9, 0.42), rot_nd, mat_buff, col)

    mesh_cr = bpy.data.meshes.new("Sem_Main_Roof_Mesh")
    obj_cr = bpy.data.objects.new("Sem_Main_Roof", mesh_cr)
    col.objects.link(obj_cr)
    bm_cr = bmesh.new()
    cw_h = 17.2
    cd_h = 6.4
    rv1 = bm_cr.verts.new(sem_world(corps_x - cw_h, corps_y + cd_h, 14.0))
    rv2 = bm_cr.verts.new(sem_world(corps_x + cw_h, corps_y + cd_h, 14.0))
    rv3 = bm_cr.verts.new(sem_world(corps_x + cw_h, corps_y - cd_h, 14.0))
    rv4 = bm_cr.verts.new(sem_world(corps_x - cw_h, corps_y - cd_h, 14.0))
    rt1 = bm_cr.verts.new(sem_world(corps_x - cw_h + 2.0, corps_y, 19.6))
    rt2 = bm_cr.verts.new(sem_world(corps_x + cw_h - 2.0, corps_y, 19.6))
    bm_cr.faces.new([rv1, rv2, rt2, rt1])
    bm_cr.faces.new([rv2, rv3, rt2])
    bm_cr.faces.new([rv3, rv4, rt1, rt2])
    bm_cr.faces.new([rv4, rv1, rt1])
    bm_cr.to_mesh(mesh_cr)
    bm_cr.free()
    obj_cr.data.materials.append(mat_slate)
    add_bevel(obj_cr, width=0.03, segments=2)

    for ch_x in [-19.5, -37.5]:
        create_box(f"Sem_Chimney_{int(ch_x)}", sem_world(ch_x, corps_y, 20.2), (1.4, 2.2, 4.4), rot_nd, mat_quoin, col)

    create_box("Sem_Clock_Pavilion", sem_world(corps_x, corps_y + 6.4, 8.0), (7.8, 2.4, 16.0), rot_nd, mat_quoin, col)
    create_cone("Sem_Clock_Pediment", sem_world(corps_x, corps_y + 6.5, 17.2), 4.8, 0.2, 2.9, rot_nd + math.pi * 0.25, mat_buff, col, segments=4)
    create_cylinder(
        "Sem_1701_Clock_Face",
        sem_world(corps_x, corps_y + 7.65, 14.2),
        1.30, 0.28,
        (math.pi * 0.5, 0.0, rot_nd),
        mat_clock, col, segments=24
    )
    create_cylinder(
        "Sem_1701_Clock_Rim",
        sem_world(corps_x, corps_y + 7.60, 14.2),
        1.48, 0.24,
        (math.pi * 0.5, 0.0, rot_nd),
        mat_gold, col, segments=24
    )
    create_cylinder("Sem_Belfry_Lantern", sem_world(corps_x, corps_y, 20.8), 1.15, 3.4, (0, 0, rot_nd), mat_white, col, segments=8)
    create_cone("Sem_Belfry_Spire", sem_world(corps_x, corps_y, 23.8), 1.30, 0.05, 3.6, rot_nd, mat_copper, col, segments=8)

    # 3D Recessed Multi-Pane Casement Windows across the Main Corps-de-Logis (7 bays x 3 floors)
    for b_i in range(-3, 4):
        wx = corps_x + b_i * 4.2
        for fl_z in [2.6, 6.4, 10.2]:
            if b_i == 0 and fl_z < 4.0:
                create_gothic_arch_recess("Sem_Main_Door", sem_world(wx, corps_y + 7.6, 0.4), 2.3, 3.8, 0.85, rot_nd, mat_buff, mat_wood, col, add_tracery=True, mat_tracery=mat_wood, add_sill=False)
                create_cone("Sem_Door_Canopy", sem_world(wx, corps_y + 8.3, 4.4), 2.2, 0.15, 1.2, rot_nd + math.pi * 0.25, mat_slate, col, segments=4)
                continue
            wy = (corps_y + 7.6) if b_i == 0 else (corps_y + 6.25)
            create_recessed_casement_window(
                f"Sem_Corps_Win_{b_i}_{int(fl_z)}",
                sem_world(wx, wy, fl_z),
                1.50, 2.25, 0.45,
                rot_nd, mat_buff, mat_white, mat_glass, col
            )

    # 5. South-West Wing of Séminaire
    sw_wing_x = -44.2
    sw_wing_y = -13.5
    create_box("Sem_SW_Wing_Body", sem_world(sw_wing_x, sw_wing_y, 7.0), (9.0, 22.0, 14.0), rot_nd, mat_rubble, col)
    create_cone("Sem_SW_Wing_Roof", sem_world(sw_wing_x, sw_wing_y, 16.0), 11.5, 0.5, 4.2, rot_nd + math.pi * 0.25, mat_slate, col, segments=4)
    for fl_z in [2.6, 6.4, 10.2]:
        for wy_off in [7.0, 2.0, -3.0]:
            create_recessed_casement_window(
                f"Sem_SW_SideWin_{int(fl_z)}_{int(wy_off)}",
                sem_world(sw_wing_x + 4.5, sw_wing_y + wy_off, fl_z),
                1.45, 2.15, 0.45,
                rot_nd - math.pi * 0.5, mat_buff, mat_white, mat_glass, col
            )

    # 6. Formal Classical Seminary Garden
    create_box("Sem_South_Garden_Lawn", (5.0, -70.0, 0.04), (82.0, 52.0, 0.08), rot_nd, palette["Mat_MTL_Garden_Lawn"], col, bevel_width=0.0)
    create_cylinder("Sem_Garden_Parterre_Ring", (-33.837, -69.204, 0.12), 4.2, 0.24, (0, 0, 0), palette["Mat_MTL_Plaza_Light_Granite"], col, segments=24)
    create_cylinder("Sem_Garden_Parterre_Center", (-33.837, -69.204, 0.35), 1.8, 0.5, (0, 0, 0), mat_quoin, col, segments=16)


def create_street_lamp(name, x, y, palette, col, multi_globe=False):
    mat_iron = palette["Mat_MTL_CastIron_Black"]
    mat_glow = palette["Mat_MTL_Portal_Warm_Glow"]

    create_cylinder(f"{name}_Plinth", (x, y, 0.25), 0.38, 0.5, (0, 0, 0), palette["Mat_MTL_Plaza_Light_Granite"], col, segments=12)
    create_cylinder(f"{name}_Base", (x, y, 0.85), 0.24, 0.9, (0, 0, 0), mat_iron, col, segments=16)
    create_cylinder(f"{name}_Pole", (x, y, 2.75), 0.095, 3.8, (0, 0, 0), mat_iron, col, segments=12)

    if multi_globe:
        create_box(f"{name}_CrossArm1", (x, y, 4.45), (1.45, 0.12, 0.12), 0.0, mat_iron, col, bevel_width=0.01)
        create_box(f"{name}_CrossArm2", (x, y, 4.45), (0.12, 1.45, 0.12), 0.0, mat_iron, col, bevel_width=0.01)
        for gx, gy, gz in [(0, 0, 4.95), (-0.64, 0, 4.72), (0.64, 0, 4.72), (0, -0.64, 4.72), (0, 0.64, 4.72)]:
            create_cylinder(f"{name}_LanternFrame_{gx}_{gy}", (x + gx, y + gy, gz - 0.22), 0.18, 0.12, (0, 0, 0), mat_iron, col, segments=8)
            create_cylinder(f"{name}_Globe_{gx}_{gy}", (x + gx, y + gy, gz), 0.22, 0.45, (0, 0, 0), mat_glow, col, segments=12)
            create_cone(f"{name}_Crown_{gx}_{gy}", (x + gx, y + gy, gz + 0.30), 0.24, 0.03, 0.20, 0.0, mat_iron, col, segments=8)
    else:
        create_cylinder(f"{name}_Lantern", (x, y, 4.75), 0.24, 0.55, (0, 0, 0), mat_glow, col, segments=8)
        create_cone(f"{name}_Cap", (x, y, 5.12), 0.30, 0.04, 0.26, 0.0, mat_iron, col, segments=8)


def create_tree(name, x, y, palette, col, scale=1.0, seed=0):
    """
    Creates a high-poly, organic multi-branch deciduous tree (`subdivisions=3`, `shade_smooth()`,
    natural green & olive-gold foliage canopy with fine leaf-cluster articulation).
    """
    rng = random.Random(seed)
    mat_bark = palette["Mat_MTL_Tree_Bark"]
    foliage_mats = [
        palette["Mat_MTL_Summer_Canopy_Green"],
        palette["Mat_MTL_Autumn_OliveGreen"],
        palette["Mat_MTL_Summer_Canopy_Green"],
        palette["Mat_MTL_Autumn_Gold"],
    ]
    mat_leaf = foliage_mats[seed % len(foliage_mats)]

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)

    bm = bmesh.new()

    trunk_h = 3.6 * scale
    t_geom = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=14, radius1=0.26 * scale, radius2=0.14 * scale, depth=trunk_h)
    bmesh.ops.translate(bm, vec=(0.0, 0.0, trunk_h * 0.5), verts=t_geom["verts"])

    branch_specs = [
        (0.42, 0.22, 0.40, 0.15, 2.5),
        (-0.38, 0.28, -0.35, 0.22, 2.4),
        (0.15, -0.45, 0.12, -0.40, 2.3),
        (-0.22, -0.32, -0.25, -0.30, 2.2),
    ]
    for bx, by, rx, ry, bh in branch_specs:
        b_geom = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=10, radius1=0.12 * scale, radius2=0.05 * scale, depth=bh * scale)
        b_verts = b_geom["verts"]
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler((rx, ry, 0.0), 'XYZ').to_matrix(), verts=b_verts)
        bmesh.ops.translate(bm, vec=(bx * scale, by * scale, trunk_h + 0.5 * scale), verts=b_verts)

    for f in bm.faces:
        f.material_index = 0

    # 18 smaller, airy, organic leaf sub-clusters so the architecture behind street trees remains visible!
    for c_i in range(18):
        ang = c_i * 2.39996  # golden angle
        rad_dist = (0.35 + 1.45 * math.sqrt(c_i / 18.0)) * scale
        cx = rad_dist * math.cos(ang)
        cy = rad_dist * math.sin(ang)
        cz = trunk_h + (1.3 + 2.2 * ((c_i % 5) / 4.0)) * scale
        crad = rng.uniform(0.75, 1.15) * scale

        c_geom = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=crad)
        c_verts = c_geom["verts"]
        for v in c_verts:
            v.co.z *= 0.75
            n_val = math.sin(v.co.x * 4.2 + c_i) * math.cos(v.co.y * 3.8) * 0.18 * scale
            v.co.x += n_val
            v.co.y += n_val
        bmesh.ops.translate(bm, vec=(cx, cy, cz), verts=c_verts)
        for f in bm.faces:
            if all(v in c_verts for v in f.verts):
                f.material_index = 1

    bmesh.ops.translate(bm, vec=(x, y, 0.0), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()

    obj.data.materials.append(mat_bark)
    obj.data.materials.append(mat_leaf)
    set_smooth(obj)
    return obj


def build_streets_and_public_realm(dossier, palette, col):
    mat_cobble = palette["Mat_MTL_Cobblestone"]
    mat_granite_dark = palette["Mat_MTL_Plaza_Charcoal_Granite"]
    mat_granite_light = palette["Mat_MTL_Plaza_Light_Granite"]
    mat_asphalt = palette["Mat_MTL_Street_Asphalt"]
    mat_iron = palette["Mat_MTL_CastIron_Black"]

    create_box("MTL_VM_0002_Ground_Plane", (40.0, -35.0, -0.15), (260.0, 240.0, 0.30), 0.0, mat_cobble, col, bevel_width=0.0)

    for hw in dossier.get("osm_features", {}).get("highways", []):
        pts = hw.get("coords_xy", [])
        if len(pts) < 2:
            continue
        tags = hw.get("tags", {})
        hw_type = tags.get("highway", "")
        surface = tags.get("surface", "")

        if hw_type in ("footway", "pedestrian", "steps"):
            width = 3.6 if hw_type != "pedestrian" else 11.0
            z_top = 0.12 if hw_type != "pedestrian" else 0.05
            mat = mat_granite_light if surface == "paving_stones" else mat_granite_dark
        else:
            width = 8.8
            z_top = 0.04
            mat = mat_cobble if surface == "sett" else mat_asphalt

        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            seg_len = math.hypot(dx, dy)
            if seg_len < 0.3:
                continue
            ang = math.atan2(dy, dx)
            mx, my = (p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5
            create_box(
                f"HW_{hw['id']}_{i}",
                (mx, my, z_top * 0.5),
                (seg_len + 0.4, width, z_top),
                ang, mat, col, bevel_width=0.015
            )

    sw_pt = Vector((-8.309, -25.949, 0.0))
    ne_pt = Vector((10.018, 10.642, 0.0))
    u_vec = (ne_pt - sw_pt).normalized()
    n_west = Vector((-u_vec.y, u_vec.x, 0.0))
    facade_mid = (sw_pt + ne_pt) * 0.5

    def to_world(lx, ly):
        return (
            facade_mid.x + lx * u_vec.x + ly * n_west.x,
            facade_mid.y + lx * u_vec.y + ly * n_west.y
        )

    for lx_lamp in [-11.5, -4.2, 4.2, 11.5]:
        lx_w, ly_w = to_world(lx_lamp, 3.8)
        create_street_lamp(f"ND_Parvis_Candelabrum_{int(lx_lamp)}", lx_w, ly_w, palette, col, multi_globe=True)

    for b_i in range(-6, 7):
        bx_w, by_w = to_world(b_i * 4.8, 9.5)
        create_cylinder(f"ND_Bollard_{b_i}", (bx_w, by_w, 0.52), 0.16, 1.05, (0, 0, 0), mat_iron, col, segments=16)

    lamp_coords = [
        (16.0, 9.5), (34.0, 2.0), (52.0, -5.5), (70.0, -12.5), (88.0, -20.0),
        (-16.0, -28.0), (-26.0, -34.0), (-36.0, -40.0)
    ]
    for l_i, (lx, ly) in enumerate(lamp_coords):
        create_street_lamp(f"StreetLamp_{l_i}", lx, ly, palette, col, multi_globe=False)

    # OSM Street Trees (keep clear of immediate camera lenses so they frame rather than block the gothic windows)
    cam_positions = [sv["blender_cam_xy_m"] for sv in dossier.get("streetview_cameras", [])]
    for t_i, t in enumerate(dossier.get("osm_features", {}).get("trees", [])):
        tx, ty = t["x"], t["y"]
        # Offset slightly if directly in front of a Street View camera lens (< 10m)
        too_close = any(math.hypot(tx - cx, ty - cy) < 9.5 for cx, cy in cam_positions)
        scale_t = 0.72 if too_close else 0.95
        create_tree(f"OSM_Tree_{t['id']}", tx, ty, palette, col, scale=scale_t, seed=t_i)

    garden_tree_coords = [
        (5.0, -56.0), (14.0, -62.0), (24.0, -66.0), (35.0, -72.0), (46.0, -76.0),
        (-6.0, -68.0), (-16.0, -74.0), (-22.0, -88.0), (8.0, -82.0), (22.0, -86.0),
        (38.0, -88.0), (-38.0, -84.0)
    ]
    for g_i, (gx, gy) in enumerate(garden_tree_coords):
        create_tree(f"Garden_Tree_{g_i}", gx, gy, palette, col, scale=1.15, seed=100 + g_i)


def build_context_proxies(dossier, palette, context_col):
    mat_stone = palette["Mat_MTL_PierreGrise_Limestone"]
    mat_buff = palette["Mat_MTL_WarmBuff_Limestone"]
    mat_brick = palette["Mat_MTL_Heritage_RedBrick"]
    mat_sandstone = palette["Mat_MTL_Red_Sandstone"]
    mat_slate = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]

    for bldg in dossier.get("osm_features", {}).get("buildings", []):
        if bldg.get("is_primary_owner", False):
            continue
        bid = bldg["id"]
        if bid == 102127874:
            continue

        name = bldg.get("name", "") or f"Context_Bldg_{bid}"
        tags = bldg.get("tags", {})
        levels = int(tags.get("building:levels", 5))
        height = float(tags.get("height", levels * 4.0))

        if "Aldred" in name or bid == 102127875:
            pts = bldg["coords_xy"]
            build_detailed_context_building(f"Proxy_{bid}_Aldred_Base", pts, 36.0, mat_buff, mat_stone, mat_slate, mat_glass, context_col, floor_h=4.0)
            cx, cy = bldg["centroid_xy"]
            pts_mid = [[cx + (p[0] - cx) * 0.72, cy + (p[1] - cy) * 0.72] for p in pts]
            pts_top = [[cx + (p[0] - cx) * 0.48, cy + (p[1] - cy) * 0.48] for p in pts]
            build_detailed_context_building(f"Proxy_{bid}_Aldred_Mid", pts_mid, 62.0, mat_buff, mat_stone, mat_slate, mat_glass, context_col, floor_h=4.2)
            build_detailed_context_building(f"Proxy_{bid}_Aldred_Top", pts_top, 86.0, mat_buff, mat_stone, mat_slate, mat_glass, context_col, floor_h=4.2)
            continue
        elif bid == 339885417:
            height = 34.0
            mat_w, mat_t = mat_stone, mat_buff
        elif bid in (182859304, 182859305, 182859306, 182859307):
            height = 38.0 if bid == 182859305 else 26.0
            mat_w = mat_sandstone if bid == 182859305 else mat_stone
            mat_t = mat_buff
        elif bid == 161201916:
            height = 22.0
            mat_w, mat_t = mat_stone, mat_buff
        else:
            height = max(15.0, height)
            mat_w = mat_brick if (bid % 2 == 0) else mat_stone
            mat_t = mat_buff

        build_detailed_context_building(
            name=f"Proxy_{bid}",
            coords_xy=bldg["coords_xy"],
            height=height,
            mat_wall=mat_w,
            mat_trim=mat_t,
            mat_roof=mat_slate,
            mat_glass=mat_glass,
            col=context_col
        )


def setup_world_and_lighting(scene):
    scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 64
    if hasattr(scene.eevee, "use_gtao"):
        scene.eevee.use_gtao = True
    if hasattr(scene.eevee, "use_ssr"):
        scene.eevee.use_ssr = True

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    bg = nodes.new("ShaderNodeBackground")
    hdri_path = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")
    if os.path.isfile(hdri_path):
        env_tex = nodes.new("ShaderNodeTexEnvironment")
        env_tex.image = bpy.data.images.load(hdri_path, check_existing=True)
        links.new(bg.inputs["Color"], env_tex.outputs["Color"])
        bg.inputs["Strength"].default_value = 1.15
    else:
        sky = nodes.new("ShaderNodeTexSky")
        sky.sky_type = 'HOSEK_WILKIE'
        links.new(bg.inputs["Color"], sky.outputs["Color"])
        bg.inputs["Strength"].default_value = 1.10

    out = nodes.new("ShaderNodeOutputWorld")
    links.new(out.inputs["Surface"], bg.outputs["Background"])

    sun_data = bpy.data.lights.new(name="MTL_Sun_Key", type='SUN')
    sun_data.energy = 3.6
    sun_data.color = (1.0, 0.95, 0.86)
    sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name="MTL_Sun_Key", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(44.0), math.radians(16.0), math.radians(-130.0))

    fill_data = bpy.data.lights.new(name="MTL_Sky_Fill", type='SUN')
    fill_data.energy = 1.10
    fill_data.color = (0.84, 0.91, 1.0)
    fill_data.angle = math.radians(18.0)
    fill_obj = bpy.data.objects.new(name="MTL_Sky_Fill", object_data=fill_data)
    bpy.context.scene.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(55.0), math.radians(-15.0), math.radians(45.0))


def render_cameras(scene, dossier, cam_col, iter_num=1):
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100

    for sv in dossier.get("streetview_cameras", []):
        label = sv["label"]
        cam_x, cam_y = sv["blender_cam_xy_m"]
        cam_z = 1.7
        heading_deg = sv.get("heading_deg", sv.get("heading", 180.0))
        pitch_deg = sv.get("pitch_deg", sv.get("pitch", 12.0))

        cam_data = bpy.data.cameras.new(name=f"Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(sv.get("fov_deg", 90.0))
        cam_data.clip_start = 0.2
        cam_data.clip_end = 1000.0

        cam_obj = bpy.data.objects.new(name=f"Cam_{label}", object_data=cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cam_x, cam_y, cam_z)
        cam_obj.rotation_euler = (
            math.radians(90.0 + pitch_deg),
            0.0,
            math.radians(-heading_deg)
        )

        scene.camera = cam_obj
        out_path = os.path.join(RENDERS_DIR, f"iter{iter_num}_{label}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View Camera [{label}] -> {out_path}")

    ov_data = bpy.data.cameras.new(name="Cam_Overview_MTL_VM_0002")
    ov_data.lens_unit = 'FOV'
    ov_data.angle = math.radians(65.0)
    ov_data.clip_start = 0.5
    ov_data.clip_end = 1500.0
    ov_obj = bpy.data.objects.new(name="Cam_Overview_MTL_VM_0002", object_data=ov_data)
    cam_col.objects.link(ov_obj)

    ov_obj.location = (-58.0, 32.0, 58.0)
    target = Vector((8.0, -28.0, 18.0))
    direction = target - ov_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    ov_obj.rotation_euler = rot_quat.to_euler()

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
    palette = upgrade_palette_with_polyhaven(palette)

    root_col = ensure_collection(f"Block_{BLOCK_ID}")
    owned_col = ensure_collection(f"Block_{BLOCK_ID}_Owned", parent=root_col)
    context_col = ensure_collection(f"Block_{BLOCK_ID}_Context_Proxy", parent=root_col)
    cam_col = ensure_collection(f"Block_{BLOCK_ID}_Cameras", parent=root_col)

    basilica_osm = None
    seminaire_osm = None
    link_osm = None
    for bldg in dossier.get("osm_features", {}).get("buildings", []):
        if bldg["id"] == 4320792:
            basilica_osm = bldg
        elif bldg["id"] == 102127874:
            seminaire_osm = bldg
        elif bldg["id"] == 126410863:
            link_osm = bldg

    if basilica_osm:
        build_basilica_notre_dame(basilica_osm, palette, owned_col)
    build_seminaire_saint_sulpice(seminaire_osm, link_osm, palette, owned_col)
    build_streets_and_public_realm(dossier, palette, owned_col)
    build_context_proxies(dossier, palette, context_col)

    scene = bpy.context.scene
    setup_world_and_lighting(scene)
    render_cameras(scene, dossier, cam_col, iter_num=1)

    blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.blend")
    usdc_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.usdc")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    sys.path.append(os.path.join(PROJECT_ROOT, "src", "blocks"))
    import upgrade_MTL_VM_0002
    upgrade_MTL_VM_0002.upgrade_block()


if __name__ == "__main__":
    main()
