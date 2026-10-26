"""
Complete High-Poly Photorealistic 3D Architectural Reconstruction of Montreal Block MTL-VM-0006
("Rue Saint-Jacques Financial Canyon & Royal Bank Tower Block", 240-360 Rue Saint-Jacques)

Implements AAA Urban Photorealism Standards:
1. Real Poly Haven 2K PBR Textures (`sandstone_blocks_05`, `castle_brick_02_red`, `cobblestone_floor_08`, `asphalt_02`)
   mapped via `TexCoord -> Object -> Mapping -> ImageTexture (projection='BOX', blend=0.25)` + NormalMap + Roughness.
2. Real Poly Haven 2K Outdoor HDRI (`kloppenheim_06_puresky_2k.hdr`) for natural sky clouds, skylight, and specular glass reflections.
3. True 3D Recessed Architectural Fenestration (`0.48m` deep recessed window alcoves carved into exterior walls),
   projecting stone sills/lintels/cornices, 3D window mullions, parallax interior backing planes, and reflective glass
   (`Roughness=0.05`, `IOR=1.52`, `Metallic=0.25`).
4. Bevel modifiers (`width=0.03m, segments=2`), rusticated ground-floor stonework, smooth curved semicircular arches,
   and dense high-poly organic multi-branch trees with `shade_smooth()`.
5. Strict Ownership Deduplication:
   - 25 Primary-Owned buildings (`is_primary_owner == True`) in `Block_MTL-VM-0006_Owned`
   - 11 Context Proxy buildings (`is_primary_owner == False`) in `Block_MTL-VM-0006_Context_Proxy`
"""

import os
import sys
import json
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0006"
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
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)


def create_collection_hierarchy():
    root_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(root_col)

    owned_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    root_col.children.link(owned_col)

    proxy_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Context_Proxy")
    root_col.children.link(proxy_col)

    streets_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Streets_And_Props")
    owned_col.children.link(streets_col)

    return root_col, owned_col, proxy_col, streets_col


def load_image_safe(filepath, colorspace='sRGB'):
    if not os.path.exists(filepath):
        return None
    img = bpy.data.images.load(filepath, check_existing=True)
    try:
        img.colorspace_settings.name = colorspace
    except Exception:
        pass
    return img


def apply_polyhaven_box_pbr(mat, asset_prefix, tint_hex, scale=0.35, roughness_mult=1.0, normal_strength=1.1, metallic=0.0):
    """Upgrades a Blender material with real Poly Haven 2K Diffuse, Roughness, and Normal maps using seamless BOX projection."""
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

    diff_path = os.path.join(POLYHAVEN_DIR, f"{asset_prefix}_Diffuse_2k.jpg")
    rough_path = os.path.join(POLYHAVEN_DIR, f"{asset_prefix}_Rough_2k.jpg")
    norm_path = os.path.join(POLYHAVEN_DIR, f"{asset_prefix}_nor_gl_2k.jpg")

    rgba = kit.hex_to_rgba(tint_hex)
    mat.diffuse_color = rgba

    img_diff = load_image_safe(diff_path, 'sRGB')
    if img_diff:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = img_diff
        tex_d.projection = 'BOX'
        tex_d.projection_blend = 0.25
        links.new(tex_d.inputs["Vector"], mapping.outputs["Vector"])

        mix_col = nodes.new("ShaderNodeMix")
        mix_col.data_type = 'RGBA'
        mix_col.blend_type = 'MULTIPLY'
        mix_col.inputs["Factor"].default_value = 0.68
        mix_col.inputs[6].default_value = rgba
        links.new(mix_col.inputs[7], tex_d.outputs["Color"])
        links.new(bsdf.inputs["Base Color"], mix_col.outputs[2])
    else:
        bsdf.inputs["Base Color"].default_value = rgba

    img_rough = load_image_safe(rough_path, 'Non-Color')
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
        bsdf.inputs["Roughness"].default_value = 0.7 * roughness_mult

    img_norm = load_image_safe(norm_path, 'Non-Color')
    if img_norm:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = img_norm
        tex_n.projection = 'BOX'
        tex_n.projection_blend = 0.25
        links.new(tex_n.inputs["Vector"], mapping.outputs["Vector"])

        norm_map = nodes.new("ShaderNodeNormalMap")
        norm_map.space = 'OBJECT'
        # Use Bump + Object space blend for arbitrary BMesh faces without UV tangents:
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = min(0.35, normal_strength * 0.28)
        bump.inputs["Distance"].default_value = 0.03
        links.new(bump.inputs["Height"], tex_n.outputs["Color"])
        links.new(bsdf.inputs["Normal"], bump.outputs["Normal"])

    return mat


def enhance_materials(palette):
    """Upgrades shared Montreal palette + specialized materials with real Poly Haven 2K PBR textures & reflective architectural glass."""
    # Unify warm limestone tones across PierreGrise, WarmBuff, and Cream so there is no cold blue-grey split
    apply_polyhaven_box_pbr(palette["Mat_MTL_PierreGrise_Limestone"], "sandstone_blocks_05", "#DFD6C5", scale=0.26, roughness_mult=0.80, normal_strength=1.15)
    apply_polyhaven_box_pbr(palette["Mat_MTL_WarmBuff_Limestone"], "sandstone_blocks_05", "#E4DAC6", scale=0.25, roughness_mult=0.78, normal_strength=1.10)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Red_Sandstone"], "sandstone_blocks_05", "#B5654D", scale=0.28, roughness_mult=0.88, normal_strength=1.25)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Heritage_RedBrick"], "castle_brick_02_red", "#9E3E2E", scale=0.45, roughness_mult=0.90, normal_strength=1.35)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Cobblestone"], "cobblestone_floor_08", "#78746E", scale=0.42, roughness_mult=0.85, normal_strength=1.35)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Street_Asphalt"], "asphalt_02", "#3B3E43", scale=0.32, roughness_mult=0.90, normal_strength=1.1)
    # Concrete sidewalk slabs (warm grey concrete, not snowy cobblestone!)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Plaza_Light_Granite"], "asphalt_02", "#A8A59E", scale=0.45, roughness_mult=0.82, normal_strength=0.45)
    # Dark charcoal speckled granite for 500 Place d'Armes plaza & retaining walls
    apply_polyhaven_box_pbr(palette["Mat_MTL_Plaza_Charcoal_Granite"], "asphalt_02", "#34373B", scale=0.45, roughness_mult=0.58, normal_strength=0.65)

    palette["Mat_MTL_Cream_Limestone"] = bpy.data.materials.get("Mat_MTL_Cream_Limestone") or bpy.data.materials.new("Mat_MTL_Cream_Limestone")
    apply_polyhaven_box_pbr(palette["Mat_MTL_Cream_Limestone"], "sandstone_blocks_05", "#EAE0CE", scale=0.25, roughness_mult=0.78, normal_strength=1.15)

    palette["Mat_MTL_Bright_White_Limestone"] = bpy.data.materials.get("Mat_MTL_Bright_White_Limestone") or bpy.data.materials.new("Mat_MTL_Bright_White_Limestone")
    apply_polyhaven_box_pbr(palette["Mat_MTL_Bright_White_Limestone"], "sandstone_blocks_05", "#EFEAE0", scale=0.24, roughness_mult=0.74, normal_strength=1.0)

    palette["Mat_MTL_Warm_Beige_Sandstone"] = bpy.data.materials.get("Mat_MTL_Warm_Beige_Sandstone") or bpy.data.materials.new("Mat_MTL_Warm_Beige_Sandstone")
    apply_polyhaven_box_pbr(palette["Mat_MTL_Warm_Beige_Sandstone"], "sandstone_blocks_05", "#DCC8AA", scale=0.27, roughness_mult=0.82, normal_strength=1.20)

    palette["Mat_MTL_Polished_Black_Granite"] = bpy.data.materials.get("Mat_MTL_Polished_Black_Granite") or bpy.data.materials.new("Mat_MTL_Polished_Black_Granite")
    apply_polyhaven_box_pbr(palette["Mat_MTL_Polished_Black_Granite"], "asphalt_02", "#1E2024", scale=0.50, roughness_mult=0.24, normal_strength=0.25, metallic=0.15)

    # Reflective Architectural Glass (Roughness = 0.05, IOR = 1.52, Metallic = 0.28)
    glass_mat = palette["Mat_MTL_Window_Glass_Dark"]
    glass_mat.use_nodes = True
    gnodes = glass_mat.node_tree.nodes
    glinks = glass_mat.node_tree.links
    gnodes.clear()
    g_out = gnodes.new("ShaderNodeOutputMaterial")
    g_bsdf = gnodes.new("ShaderNodeBsdfPrincipled")
    g_bsdf.inputs["Base Color"].default_value = (0.06, 0.11, 0.15, 1.0)
    g_bsdf.inputs["Roughness"].default_value = 0.05
    g_bsdf.inputs["Metallic"].default_value = 0.28
    if "IOR" in g_bsdf.inputs:
        g_bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in g_bsdf.inputs:
        g_bsdf.inputs["Specular IOR Level"].default_value = 0.85
    glinks.new(g_out.inputs["Surface"], g_bsdf.outputs["BSDF"])

    # Warm lit office/storefront interior parallax backing plane material
    int_mat = bpy.data.materials.get("Mat_MTL_Interior_Parallax") or bpy.data.materials.new("Mat_MTL_Interior_Parallax")
    int_mat.use_nodes = True
    inodes = int_mat.node_tree.nodes
    ilinks = int_mat.node_tree.links
    inodes.clear()
    i_out = inodes.new("ShaderNodeOutputMaterial")
    i_bsdf = inodes.new("ShaderNodeBsdfPrincipled")
    tc = inodes.new("ShaderNodeTexCoord")
    noise = inodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.2
    noise.inputs["Detail"].default_value = 5.0
    ramp = inodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.14, 0.12, 0.09, 1.0)
    ramp.color_ramp.elements[1].color = (0.72, 0.58, 0.40, 1.0)
    ilinks.new(noise.inputs["Vector"], tc.outputs["Object"])
    ilinks.new(ramp.inputs["Fac"], noise.outputs["Fac"])
    ilinks.new(i_bsdf.inputs["Base Color"], ramp.outputs["Color"])
    if "Emission Color" in i_bsdf.inputs:
        ilinks.new(i_bsdf.inputs["Emission Color"], ramp.outputs["Color"])
    if "Emission Strength" in i_bsdf.inputs:
        i_bsdf.inputs["Emission Strength"].default_value = 0.55
    ilinks.new(i_out.inputs["Surface"], i_bsdf.outputs["BSDF"])
    palette["Mat_MTL_Interior_Parallax"] = int_mat

    palette["Mat_MTL_Awning_Black"] = kit.get_or_create_pbr_material("Mat_MTL_Awning_Black", "#1D1F24", roughness=0.78, bump_strength=0.06, noise_scale=45.0)
    palette["Mat_MTL_Banner_Crimson"] = kit.get_or_create_pbr_material("Mat_MTL_Banner_Crimson", "#852228", roughness=0.55, bump_strength=0.04, noise_scale=30.0)
    palette["Mat_MTL_Sign_RoyalBlue"] = kit.get_or_create_pbr_material("Mat_MTL_Sign_RoyalBlue", "#1B3B7B", roughness=0.38, metallic=0.15, bump_strength=0.03)
    palette["Mat_MTL_Storefront_Navy"] = kit.get_or_create_pbr_material("Mat_MTL_Storefront_Navy", "#223147", roughness=0.45, metallic=0.20, bump_strength=0.04)
    palette["Mat_MTL_Traffic_Cone_Orange"] = kit.get_or_create_pbr_material("Mat_MTL_Traffic_Cone_Orange", "#EC4E1A", roughness=0.42, bump_strength=0.02)
    palette["Mat_MTL_Reflective_White"] = kit.get_or_create_pbr_material("Mat_MTL_Reflective_White", "#F2F4F7", roughness=0.28, metallic=0.1, bump_strength=0.01)
    palette["Mat_MTL_Caution_Yellow"] = kit.get_or_create_pbr_material("Mat_MTL_Caution_Yellow", "#E8B81A", roughness=0.35, metallic=0.05, bump_strength=0.01)
    palette["Mat_MTL_Stake_Green"] = kit.get_or_create_pbr_material("Mat_MTL_Stake_Green", "#2E7D32", roughness=0.50, metallic=0.1, bump_strength=0.02)
    palette["Mat_MTL_Hydrant_Red"] = kit.get_or_create_pbr_material("Mat_MTL_Hydrant_Red", "#C2241E", roughness=0.35, metallic=0.35, bump_strength=0.04)
    palette["Mat_MTL_Window_Frame_Light"] = kit.get_or_create_pbr_material("Mat_MTL_Window_Frame_Light", "#E2DFD7", roughness=0.42, metallic=0.2, bump_strength=0.02)
    palette["Mat_MTL_Gold_Brass"] = kit.get_or_create_pbr_material("Mat_MTL_Gold_Brass", "#CFA43C", roughness=0.24, metallic=0.88, bump_strength=0.02)

    if "Mat_MTL_Lamp_Glow" not in bpy.data.materials:
        mat = bpy.data.materials.new("Mat_MTL_Lamp_Glow")
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (1.0, 0.94, 0.78, 1.0)
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (1.0, 0.90, 0.68, 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 4.5
        palette["Mat_MTL_Lamp_Glow"] = mat
    else:
        palette["Mat_MTL_Lamp_Glow"] = bpy.data.materials["Mat_MTL_Lamp_Glow"]

    return palette


def apply_bevel_and_smooth(obj, width=0.03, segments=2):
    """Adds a subtle architectural edge bevel so stone corners catch realistic specular highlights."""
    if not obj or obj.type != 'MESH':
        return
    bev = obj.modifiers.new(name="ArchBevel", type='BEVEL')
    bev.width = width
    bev.segments = segments
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(35.0)
    bev.harden_normals = False


def clean_polygon_pts(coords_xy):
    pts = coords_xy[:-1] if coords_xy[0] == coords_xy[-1] else list(coords_xy)
    cleaned = []
    for p in pts:
        if not cleaned or math.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > 0.25:
            cleaned.append((float(p[0]), float(p[1])))
    if len(cleaned) > 2 and math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) < 0.25:
        cleaned.pop()
    return cleaned


def polygon_signed_area(pts):
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
    return 0.5 * area


def ensure_ccw(pts):
    if polygon_signed_area(pts) < 0:
        return list(reversed(pts))
    return pts


def inset_polygon_2d(pts, inset_dist):
    """Inset a 2D CCW polygon by inset_dist (positive = inward, negative = outward), clamping miter spikes on acute corners."""
    pts = ensure_ccw(pts)
    n = len(pts)
    new_pts = []
    for i in range(n):
        p_prev = Vector(pts[(i - 1) % n])
        p_curr = Vector(pts[i])
        p_next = Vector(pts[(i + 1) % n])

        v1 = (p_curr - p_prev)
        v2 = (p_next - p_curr)
        if v1.length < 1e-4 or v2.length < 1e-4:
            new_pts.append((p_curr.x, p_curr.y))
            continue
        v1.normalize()
        v2.normalize()
        n1 = Vector((-v1.y, v1.x))
        n2 = Vector((-v2.y, v2.x))
        bisector = n1 + n2
        if bisector.length < 1e-3:
            offset = n1 * inset_dist
        else:
            bisector.normalize()
            denom = max(0.55, bisector.dot(n1))
            offset = bisector * (inset_dist / denom)
            if offset.length > abs(inset_dist) * 1.65:
                offset = offset.normalized() * (abs(inset_dist) * 1.65)
        np = p_curr + offset
        new_pts.append((np.x, np.y))
    return new_pts


def add_prism_to_bm(bm, pts_2d, z0, z1, mat_side, mat_top, mat_bot=None):
    pts = ensure_ccw(pts_2d)
    if len(pts) < 3:
        return
    v_bot = [bm.verts.new((p[0], p[1], z0)) for p in pts]
    v_top = [bm.verts.new((p[0], p[1], z1)) for p in pts]
    n = len(pts)
    for i in range(n):
        f_side = bm.faces.new((v_bot[i], v_bot[(i + 1) % n], v_top[(i + 1) % n], v_top[i]))
        f_side.material_index = mat_side
    try:
        f_top = bm.faces.new(v_top)
        f_top.material_index = mat_top
        if mat_bot is not None:
            f_bot = bm.faces.new(list(reversed(v_bot)))
            f_bot.material_index = mat_bot
    except ValueError:
        pass


def add_oriented_box(bm, center_xyz, dir_xy, normal_xy, width, depth, height, mat_idx, smooth=False):
    dx, dy = dir_xy
    nx, ny = normal_xy
    cx, cy, cz = center_xyz
    hw = width * 0.5
    hd = depth * 0.5
    hh = height * 0.5

    corners_2d = [
        (cx - dx * hw - nx * hd, cy - dy * hw - ny * hd),
        (cx + dx * hw - nx * hd, cy + dy * hw - ny * hd),
        (cx + dx * hw + nx * hd, cy + dy * hw + ny * hd),
        (cx - dx * hw + nx * hd, cy - dy * hw + ny * hd),
    ]
    # Ensure 2D corners are strictly counter-clockwise in XY so side and top normals always point outward!
    if (dx * ny - dy * nx) < 0.0:
        corners_2d.reverse()

    v_bot = [bm.verts.new((x, y, cz - hh)) for x, y in corners_2d]
    v_top = [bm.verts.new((x, y, cz + hh)) for x, y in corners_2d]
    for i in range(4):
        f = bm.faces.new((v_bot[i], v_bot[(i + 1) % 4], v_top[(i + 1) % 4], v_top[i]))
        f.material_index = mat_idx
        f.smooth = smooth
    f_t = bm.faces.new(v_top)
    f_t.material_index = mat_idx
    f_t.smooth = smooth
    f_b = bm.faces.new(list(reversed(v_bot)))
    f_b.material_index = mat_idx
    f_b.smooth = smooth


def add_smooth_arch_extrusion(bm, center_xy, z_spring, z_top_spandrel, half_bay_w, dir_xy, normal_xy, radius_w, radius_h, ring_thickness, depth, mat_ring, mat_spandrel, segments=24):
    """
    Creates a smooth high-poly 24-segment radial stone arch ring (archivolt) AND seamlessly fills the
    triangular stone spandrel corners between the arch extrados and the rectangular bay top (`z_top_spandrel`),
    with outward-pointing face normals matching the surrounding piers.
    """
    dx, dy = dir_xy
    nx, ny = normal_xy
    cx, cy = center_xy

    inner_r_w = radius_w
    inner_r_h = radius_h
    outer_r_w = min(half_bay_w * 0.98, radius_w + ring_thickness)
    outer_r_h = min((z_top_spandrel - z_spring) * 0.96, radius_h + ring_thickness)

    front_inner = []
    front_outer = []
    back_inner = []
    back_outer = []
    spandrel_front_top = []
    spandrel_back_top = []

    sp_depth = depth * 0.88

    for s in range(segments + 1):
        ang = math.pi * s / segments
        cos_a = math.cos(ang)
        sin_a = math.sin(ang)

        xi = cx - cos_a * dx * inner_r_w
        yi = cy - cos_a * dy * inner_r_w
        zi = z_spring + sin_a * inner_r_h

        xo = cx - cos_a * dx * outer_r_w
        yo = cy - cos_a * dy * outer_r_w
        zo = z_spring + sin_a * outer_r_h

        u_sp = -cos_a * half_bay_w
        x_top = cx + u_sp * dx
        y_top = cy + u_sp * dy
        z_top = max(zo + 0.05, z_top_spandrel)

        front_inner.append(bm.verts.new((xi + nx * depth, yi + ny * depth, zi)))
        front_outer.append(bm.verts.new((xo + nx * depth, yo + ny * depth, zo)))
        back_inner.append(bm.verts.new((xi, yi, zi)))
        back_outer.append(bm.verts.new((xo, yo, zo)))

        spandrel_front_top.append(bm.verts.new((x_top + nx * sp_depth, y_top + ny * sp_depth, z_top)))
        spandrel_back_top.append(bm.verts.new((x_top, y_top, z_top)))

    for s in range(segments):
        # 1. Carved archivolt ring with outward-pointing normals (+normal_xy)
        f_front = bm.faces.new((front_inner[s], front_inner[s + 1], front_outer[s + 1], front_outer[s]))
        f_front.material_index = mat_ring
        f_front.smooth = True
        f_intra = bm.faces.new((back_inner[s], back_inner[s + 1], front_inner[s + 1], front_inner[s]))
        f_intra.material_index = mat_ring
        f_intra.smooth = True
        f_extra = bm.faces.new((front_outer[s], front_outer[s + 1], back_outer[s + 1], back_outer[s]))
        f_extra.material_index = mat_ring
        f_extra.smooth = True

        # 2. Seamless spandrel web filling from arch extrados up to horizontal cornice line (+normal_xy)
        f_sp_f = bm.faces.new((front_outer[s], front_outer[s + 1], spandrel_front_top[s + 1], spandrel_front_top[s]))
        f_sp_f.material_index = mat_spandrel
        f_sp_t = bm.faces.new((spandrel_front_top[s], spandrel_front_top[s + 1], spandrel_back_top[s + 1], spandrel_back_top[s]))
        f_sp_t.material_index = mat_spandrel

    # Projecting carved trapezoidal keystone at the crown of the arch
    kz = z_spring + inner_r_h + ring_thickness * 0.52
    add_oriented_box(
        bm, (cx + nx * (depth * 0.72), cy + ny * (depth * 0.72), kz),
        dir_xy, normal_xy, ring_thickness * 0.85, depth * 1.48, ring_thickness * 1.28, mat_ring
    )


def add_rooftop_superstructures(bm, pts, total_height, bldg_id, mat_stone, mat_roof, mat_copper, mat_glass, mat_frame):
    """
    Populates building rooftops with realistic mechanical penthouses, elevator bulkheads, HVAC chiller units,
    and vaulted skylights matching `satellite_topdown.png` while staying strictly inside the roof polygon.
    """
    pts_inner_roof = inset_polygon_2d(pts, 0.65)
    if len(pts_inner_roof) < 3:
        return
    add_prism_to_bm(bm, pts_inner_roof, total_height + 0.1, total_height + 0.45, mat_stone, mat_roof)

    # Use a deeply inset safe zone polygon to guarantee all rooftop equipment stays well inside L-shaped/narrow roofs
    pts_safe = inset_polygon_2d(pts, 4.2)
    if len(pts_safe) < 3:
        return
    cx = sum(p[0] for p in pts_safe) / len(pts_safe)
    cy = sum(p[1] for p in pts_safe) / len(pts_safe)
    min_x, max_x = min(p[0] for p in pts_safe), max(p[0] for p in pts_safe)
    min_y, max_y = min(p[1] for p in pts_safe), max(p[1] for p in pts_safe)
    span_x = max_x - min_x
    span_y = max_y - min_y
    if span_x < 5.0 or span_y < 5.0:
        return

    # Align along the longest building edge
    best_len = 0.0
    u_dir = (0.857, 0.515)
    for i in range(len(pts)):
        p1 = Vector(pts[i])
        p2 = Vector(pts[(i + 1) % len(pts)])
        ev = p2 - p1
        if ev.length > best_len:
            best_len = ev.length
            u_dir = (ev.x / ev.length, ev.y / ev.length)
    v_dir = (-u_dir[1], u_dir[0])

    # 1. Elevator / Mechanical Penthouse structure near center of safe roof zone
    ph_w = min(7.2, span_x * 0.35)
    ph_d = min(5.4, span_y * 0.35)
    ph_h = 3.4 if total_height > 28.0 else 2.5
    add_oriented_box(
        bm, (cx, cy, total_height + 0.45 + ph_h * 0.5),
        u_dir, v_dir, ph_w, ph_d, ph_h, mat_stone
    )
    add_oriented_box(
        bm, (cx, cy, total_height + 0.45 + ph_h + 0.15),
        u_dir, v_dir, ph_w + 0.35, ph_d + 0.35, 0.28, mat_roof
    )

    # 2. Array of 3 HVAC chiller / cooling tower units beside the penthouse
    for h_i in (-1, 0, 1):
        hx = cx + u_dir[0] * (ph_w * 0.68) + v_dir[0] * (h_i * 1.8)
        hy = cy + u_dir[1] * (ph_w * 0.68) + v_dir[1] * (h_i * 1.8)
        add_oriented_box(bm, (hx, hy, total_height + 0.45 + 0.75), u_dir, v_dir, 1.6, 1.4, 1.5, mat_frame)
        ret_f = bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=True, segments=12,
            radius1=0.48, radius2=0.45, depth=0.30,
            matrix=Matrix.Translation((hx, hy, total_height + 0.45 + 1.62))
        )
        for v in ret_f["verts"]:
            for f in v.link_faces:
                f.material_index = mat_roof
                f.smooth = True

    # 3. Vaulted Glass Atrium Skylight on large blocks
    if span_x > 16.0 and span_y > 16.0:
        sky_w = min(9.5, span_x * 0.35)
        sky_d = min(3.8, span_y * 0.24)
        sx = cx - u_dir[0] * (ph_w * 0.72)
        sy = cy - u_dir[1] * (ph_w * 0.72)
        add_oriented_box(bm, (sx, sy, total_height + 0.45 + 0.55), u_dir, v_dir, sky_w, sky_d, 1.1, mat_glass)
        add_oriented_box(bm, (sx, sy, total_height + 0.45 + 1.25), u_dir, v_dir, sky_w * 0.98, sky_d * 0.55, 0.40, mat_glass)
        for m_k in range(-2, 3):
            mx = sx + u_dir[0] * (m_k * sky_w / 5.0)
            my = sy + u_dir[1] * (m_k * sky_w / 5.0)
            add_oriented_box(bm, (mx, my, total_height + 0.45 + 0.75), u_dir, v_dir, 0.10, sky_d + 0.08, 1.35, mat_frame)


def build_beaux_arts_building(
    bldg_id, name, coords_xy, collection, palette,
    total_height, podium_height, style="beaux_arts_limestone",
    bay_width=4.2, floor_h=3.7, has_balustrade=True, has_Copper_mansard=False,
    has_storefront_awnings=False, has_black_granite_base=False, has_corner_banner=False,
    podium_arches=True, has_blue_blade_sign=False, has_iron_balconies=False
):
    """
    Builds a high-poly Montreal Beaux-Arts or Art Deco building with TRUE 0.48m recessed window bays,
    unified warm ashlar limestone materiality, smooth 24-segment radial archivolts (or rectangular bays),
    3rd-floor wrought-iron balconies, rooftop superstructures, and custom signage.
    """
    pts = ensure_ccw(clean_polygon_pts(coords_xy))
    if len(pts) < 3:
        return None

    mesh = bpy.data.meshes.new(f"Bldg_{bldg_id}_Mesh")
    obj = bpy.data.objects.new(f"Bldg_{bldg_id}_{name}" if name else f"Bldg_{bldg_id}", mesh)
    collection.objects.link(obj)

    if style == "white_beaux_arts":
        mat_wall = palette["Mat_MTL_Bright_White_Limestone"]
        mat_podium = palette["Mat_MTL_Cream_Limestone"]
        mat_trim = palette["Mat_MTL_WarmBuff_Limestone"]
        mat_frame = palette["Mat_MTL_Window_Frame_Light"]
    elif style == "cream_beaux_arts":
        mat_wall = palette["Mat_MTL_Cream_Limestone"]
        mat_podium = palette["Mat_MTL_Cream_Limestone"]
        mat_trim = palette["Mat_MTL_WarmBuff_Limestone"]
        mat_frame = palette["Mat_MTL_CastIron_Black"]
    elif style == "sandstone_heritage":
        mat_wall = palette["Mat_MTL_Warm_Beige_Sandstone"]
        mat_podium = palette["Mat_MTL_WarmBuff_Limestone"]
        mat_trim = palette["Mat_MTL_Cream_Limestone"]
        mat_frame = palette["Mat_MTL_CastIron_Black"]
    elif style == "redbrick_classical":
        mat_wall = palette["Mat_MTL_Heritage_RedBrick"]
        mat_podium = palette["Mat_MTL_WarmBuff_Limestone"]
        mat_trim = palette["Mat_MTL_Cream_Limestone"]
        mat_frame = palette["Mat_MTL_Window_Frame_Light"]
    elif style == "modern_granite_base":
        mat_wall = palette["Mat_MTL_Cream_Limestone"]
        mat_podium = palette["Mat_MTL_Polished_Black_Granite"]
        mat_trim = palette["Mat_MTL_Plaza_Charcoal_Granite"]
        mat_frame = palette["Mat_MTL_Window_Frame_Light"]
    else:
        mat_wall = palette["Mat_MTL_Cream_Limestone"]
        mat_podium = palette["Mat_MTL_WarmBuff_Limestone"]
        mat_trim = palette["Mat_MTL_PierreGrise_Limestone"]
        mat_frame = palette["Mat_MTL_CastIron_Black"]

    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_roof = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_copper = palette["Mat_MTL_Verdigris_Copper"]
    mat_awning = palette["Mat_MTL_Awning_Black"]
    mat_banner = palette["Mat_MTL_Sign_RoyalBlue"] if has_blue_blade_sign else palette["Mat_MTL_Banner_Crimson"]
    mat_granite_blk = palette["Mat_MTL_Storefront_Navy"] if has_blue_blade_sign else palette["Mat_MTL_Polished_Black_Granite"]
    mat_interior = palette["Mat_MTL_Interior_Parallax"]
    mat_white = palette["Mat_MTL_Reflective_White"]
    mat_brick = palette["Mat_MTL_Heritage_RedBrick"]

    mats = [
        mat_wall, mat_podium, mat_trim, mat_glass, mat_frame,
        mat_roof, mat_copper, mat_awning, mat_banner, mat_granite_blk, mat_interior, mat_white, mat_brick
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    recess_depth = 0.48
    pts_glass_core = inset_polygon_2d(pts, recess_depth)
    pts_parallax_core = inset_polygon_2d(pts, recess_depth + 0.35)

    # 1. Ground plinth / granite water-table base (0 to plinth_h)
    plinth_h = 1.35 if has_black_granite_base else 1.05
    plinth_mat = 9 if has_black_granite_base else 1
    pts_plinth = inset_polygon_2d(pts, -0.06)
    add_prism_to_bm(bm, pts_plinth, -0.4, plinth_h, plinth_mat, plinth_mat, plinth_mat)

    # 2. Recessed Reflective Glass Volume & Interior Parallax Core from plinth_h to total_height
    add_prism_to_bm(bm, pts_parallax_core, plinth_h, total_height - 0.5, 10, 5)
    add_prism_to_bm(bm, pts_glass_core, plinth_h, total_height - 0.3, 3, 5)

    # 3. Podium Entablature & Molded Cornice (at podium_height)
    pod_ent_mat = 9 if has_blue_blade_sign else 2
    add_prism_to_bm(bm, pts, podium_height - 0.85, podium_height + 0.35, 1, pod_ent_mat)
    pts_pod_cornice = inset_polygon_2d(pts, -0.42)
    add_prism_to_bm(bm, pts_pod_cornice, podium_height - 0.38, podium_height + 0.45, pod_ent_mat, pod_ent_mat, pod_ent_mat)

    # 4. Main Projecting Entablature, Copper Roof Cornice & Balustrade at Roofline
    add_prism_to_bm(bm, pts, total_height - 1.2, total_height, 0, 5)
    pts_cornice_low = inset_polygon_2d(pts, -0.32)
    pts_cornice_high = inset_polygon_2d(pts, -0.68)
    cornice_top_mat = 6 if has_iron_balconies else 2
    add_prism_to_bm(bm, pts_cornice_low, total_height - 0.95, total_height - 0.42, 2, 2, 2)
    add_prism_to_bm(bm, pts_cornice_high, total_height - 0.42, total_height + 0.32, cornice_top_mat, 5, cornice_top_mat)

    if has_balustrade:
        pts_parapet_out = inset_polygon_2d(pts, -0.12)
        pts_parapet_in = inset_polygon_2d(pts, 0.38)
        add_prism_to_bm(bm, pts_parapet_out, total_height + 0.32, total_height + 1.42, 2, 2)
        add_prism_to_bm(bm, pts_parapet_in, total_height + 0.32, total_height + 1.45, 5, 5)

    if has_Copper_mansard:
        pts_mansard_top = inset_polygon_2d(pts, 1.8)
        v_b = [bm.verts.new((p[0], p[1], total_height + 0.32)) for p in pts]
        v_t = [bm.verts.new((p[0], p[1], total_height + 3.9)) for p in pts_mansard_top]
        n = len(pts)
        for i in range(n):
            f = bm.faces.new((v_b[i], v_b[(i + 1) % n], v_t[(i + 1) % n], v_t[i]))
            f.material_index = 6
        try:
            ft = bm.faces.new(v_t)
            ft.material_index = 5
        except ValueError:
            pass

    # Add rooftop mechanical penthouses, HVAC units, and skylights
    add_rooftop_superstructures(bm, pts, total_height, bldg_id, mat_stone=0, mat_roof=5, mat_copper=6, mat_glass=3, mat_frame=4)

    # 5. Deep 3D Structural Wall Piers, Spandrels, Sills, Lintels, Arches & Mullions
    n = len(pts)
    for i in range(n):
        p1 = Vector(pts[i])
        p2 = Vector(pts[(i + 1) % n])
        edge_vec = p2 - p1
        edge_len = edge_vec.length
        if edge_len < 2.2:
            mid = (p1 + p2) * 0.5
            d_xy = (edge_vec.x / max(1e-4, edge_len), edge_vec.y / max(1e-4, edge_len))
            n_xy = (d_xy[1], -d_xy[0])
            add_oriented_box(
                bm, (mid.x - n_xy[0] * (recess_depth * 0.5), mid.y - n_xy[1] * (recess_depth * 0.5), total_height * 0.5),
                d_xy, n_xy, edge_len + 0.4, recess_depth + 0.12, total_height, 0
            )
            continue

        dir_xy = (edge_vec.x / edge_len, edge_vec.y / edge_len)
        normal_xy = (dir_xy[1], -dir_xy[0])

        # Special Red-Brick Party Wall on SW side of Building 339898458 facing Photo Service (339898461) on Rue Notre-Dame!
        if bldg_id == 339898458 and normal_xy[1] < -0.55:
            mid = (p1 + p2) * 0.5
            add_oriented_box(
                bm, (mid.x - normal_xy[0] * 0.15, mid.y - normal_xy[1] * 0.15, total_height * 0.5),
                dir_xy, normal_xy, edge_len + 0.2, 0.65, total_height, 12
            )
            continue

        num_bays = max(1, int(round(edge_len / bay_width)))
        actual_bay_w = edge_len / num_bays
        pier_w = actual_bay_w * 0.28
        wall_depth = recess_depth + 0.10

        # A. Full-height structural piers at bay boundaries
        for b_i in range(num_bays + 1):
            t_pier = b_i / num_bays
            px = p1.x + edge_vec.x * t_pier - normal_xy[0] * (recess_depth * 0.42)
            py = p1.y + edge_vec.y * t_pier - normal_xy[1] * (recess_depth * 0.42)
            cur_pier_w = pier_w * (1.35 if (b_i == 0 or b_i == num_bays) else 1.0)

            pod_pier_h = podium_height - plinth_h
            podium_mat = 9 if has_black_granite_base else 1
            add_oriented_box(
                bm, (px, py, plinth_h + pod_pier_h * 0.5),
                dir_xy, normal_xy, cur_pier_w, wall_depth + 0.08, pod_pier_h, podium_mat
            )
            if not has_black_granite_base:
                num_rust = int(pod_pier_h / 0.58)
                for r_i in range(num_rust):
                    rz = plinth_h + (r_i + 0.5) * 0.58
                    add_oriented_box(
                        bm, (px + normal_xy[0] * (wall_depth * 0.48), py + normal_xy[1] * (wall_depth * 0.48), rz),
                        dir_xy, normal_xy, cur_pier_w + 0.08, 0.16, 0.42, 1
                    )

            shaft_h = total_height - podium_height - 0.8
            if shaft_h > 1.5:
                add_oriented_box(
                    bm, (px, py, podium_height + 0.35 + shaft_h * 0.5),
                    dir_xy, normal_xy, cur_pier_w, wall_depth, shaft_h, 0
                )
                add_oriented_box(
                    bm, (px + normal_xy[0] * (wall_depth * 0.52), py + normal_xy[1] * (wall_depth * 0.52), podium_height + 0.35 + shaft_h * 0.5),
                    dir_xy, normal_xy, cur_pier_w * 0.55, 0.14, shaft_h - 0.4, 2
                )
                add_oriented_box(
                    bm, (px + normal_xy[0] * (wall_depth * 0.65), py + normal_xy[1] * (wall_depth * 0.65), total_height - 0.68),
                    dir_xy, normal_xy, 0.28, 0.42, 0.48, 2
                )

        # B. Per-bay spandrels, smooth radial arches (or rectangular bays), sills, lintels, balconies & mullions
        for b_i in range(num_bays):
            t_center = (b_i + 0.5) / num_bays
            bx = p1.x + edge_vec.x * t_center
            by = p1.y + edge_vec.y * t_center
            open_w = actual_bay_w - pier_w * 0.85

            # Mid-block Curtain Wall Atrium & STATIONNEMENT Garage Portal on Building 340057021 (seen in Cam 1!)
            is_curtain_atrium_bay = (bldg_id == 340057021 and num_bays >= 4 and b_i in (1, 2))

            if is_curtain_atrium_bay:
                # Recessed dark parking garage portal on ground floor with dark sign beam (`STATIONNEMENT P`)
                add_oriented_box(
                    bm, (bx + normal_xy[0] * 0.05, by + normal_xy[1] * 0.05, 3.4),
                    dir_xy, normal_xy, open_w * 0.98, 0.45, 0.85, 4
                )
                # Multi-story curtain wall mullion grid up the facade + open roofline arch at top floor
                add_smooth_arch_extrusion(
                    bm, (bx - normal_xy[0] * (recess_depth * 0.35), by - normal_xy[1] * (recess_depth * 0.35)),
                    total_height - 4.2, total_height - 0.9, open_w * 0.52,
                    dir_xy, normal_xy, open_w * 0.44, 1.8, ring_thickness=0.36, depth=recess_depth * 0.65,
                    mat_ring=2, mat_spandrel=0, segments=24
                )
            elif podium_height >= 6.5 and not has_black_granite_base and podium_arches:
                transom_z = plinth_h + (podium_height - plinth_h) * 0.50
                add_oriented_box(
                    bm, (bx - normal_xy[0] * (recess_depth * 0.35), by - normal_xy[1] * (recess_depth * 0.35), transom_z),
                    dir_xy, normal_xy, open_w + 0.2, wall_depth + 0.08, 0.48, 2
                )
                arch_r_w = open_w * 0.45
                arch_r_h = min(open_w * 0.42, podium_height - transom_z - 0.90)
                if arch_r_h > 0.45:
                    add_smooth_arch_extrusion(
                        bm, (bx - normal_xy[0] * (recess_depth * 0.42), by - normal_xy[1] * (recess_depth * 0.42)),
                        transom_z + 0.22, podium_height - 0.35, open_w * 0.52,
                        dir_xy, normal_xy, arch_r_w, arch_r_h, ring_thickness=0.38, depth=wall_depth * 0.92,
                        mat_ring=2, mat_spandrel=1, segments=24
                    )

                if has_storefront_awnings:
                    awn_z = transom_z - 0.25
                    awn_depth = 0.95
                    awn_h = 0.68
                    p_bl = (bx - dir_xy[0] * open_w * 0.48, by - dir_xy[1] * open_w * 0.48)
                    p_br = (bx + dir_xy[0] * open_w * 0.48, by + dir_xy[1] * open_w * 0.48)
                    v1 = bm.verts.new((p_bl[0], p_bl[1], awn_z + awn_h))
                    v2 = bm.verts.new((p_br[0], p_br[1], awn_z + awn_h))
                    v3 = bm.verts.new((p_br[0] + normal_xy[0] * awn_depth, p_br[1] + normal_xy[1] * awn_depth, awn_z))
                    v4 = bm.verts.new((p_bl[0] + normal_xy[0] * awn_depth, p_bl[1] + normal_xy[1] * awn_depth, awn_z))
                    v5 = bm.verts.new((p_bl[0] + normal_xy[0] * awn_depth, p_bl[1] + normal_xy[1] * awn_depth, awn_z - 0.18))
                    v6 = bm.verts.new((p_br[0] + normal_xy[0] * awn_depth, p_br[1] + normal_xy[1] * awn_depth, awn_z - 0.18))
                    for fv in [(v1, v2, v3, v4), (v4, v3, v6, v5)]:
                        f = bm.faces.new(fv)
                        f.material_index = 7
            else:
                # Rectangular limestone podium openings (e.g. Rue Notre-Dame left & right sides!)
                sp_h = 1.15
                sp_mat = 9 if (has_black_granite_base or has_blue_blade_sign) else 1
                add_oriented_box(
                    bm, (bx - normal_xy[0] * (recess_depth * 0.42), by - normal_xy[1] * (recess_depth * 0.42), podium_height - sp_h * 0.5),
                    dir_xy, normal_xy, open_w + 0.15, wall_depth, sp_h, sp_mat
                )
                if podium_height >= 6.8:
                    mid_sp_z = plinth_h + (podium_height - plinth_h) * 0.52
                    add_oriented_box(
                        bm, (bx - normal_xy[0] * (recess_depth * 0.42), by - normal_xy[1] * (recess_depth * 0.42), mid_sp_z),
                        dir_xy, normal_xy, open_w + 0.15, wall_depth, 0.85, 1
                    )

            # Recessed ground-floor storefront 3D mullions
            gx = bx - normal_xy[0] * (recess_depth - 0.06)
            gy = by - normal_xy[1] * (recess_depth - 0.06)
            gf_h = podium_height - plinth_h - 0.6
            for m_u in (-0.28, 0.0, 0.28):
                add_oriented_box(
                    bm, (gx + dir_xy[0] * (open_w * m_u), gy + dir_xy[1] * (open_w * m_u), plinth_h + gf_h * 0.5),
                    dir_xy, normal_xy, 0.07, 0.12, gf_h, 4
                )
            for m_z in (0.35, 0.68):
                add_oriented_box(
                    bm, (gx, gy, plinth_h + gf_h * m_z),
                    dir_xy, normal_xy, open_w, 0.12, 0.07, 4
                )

            # Upper shaft floors
            z_fl_bot = podium_height + 0.35
            fl_idx = 0
            while z_fl_bot + floor_h <= total_height - 0.4:
                win_bot = z_fl_bot + 0.72
                win_top = z_fl_bot + floor_h - 0.58
                win_h = win_top - win_bot
                win_mid_z = (win_bot + win_top) * 0.5

                sp_bot_h = win_bot - z_fl_bot
                add_oriented_box(
                    bm, (bx - normal_xy[0] * (recess_depth * 0.42), by - normal_xy[1] * (recess_depth * 0.42), z_fl_bot + sp_bot_h * 0.5),
                    dir_xy, normal_xy, open_w + 0.15, wall_depth, sp_bot_h, 0
                )
                sp_top_h = (z_fl_bot + floor_h) - win_top
                add_oriented_box(
                    bm, (bx - normal_xy[0] * (recess_depth * 0.42), by - normal_xy[1] * (recess_depth * 0.42), win_top + sp_top_h * 0.5),
                    dir_xy, normal_xy, open_w + 0.15, wall_depth, sp_top_h, 0
                )

                # Projecting stone window sill & lintel
                add_oriented_box(
                    bm, (bx + normal_xy[0] * 0.09, by + normal_xy[1] * 0.09, win_bot - 0.08),
                    dir_xy, normal_xy, open_w * 0.98, 0.24, 0.16, 2
                )
                add_oriented_box(
                    bm, (bx + normal_xy[0] * 0.10, by + normal_xy[1] * 0.10, win_top + 0.10),
                    dir_xy, normal_xy, open_w * 1.02, 0.26, 0.20, 2
                )

                # Wrought-iron 3rd-floor balcony balustrade with stone brackets (seen in Cam 1 & Cam 4!)
                if has_iron_balconies and fl_idx == 0 and (b_i % 2 == 1):
                    bal_x = bx + normal_xy[0] * 0.28
                    bal_y = by + normal_xy[1] * 0.28
                    add_oriented_box(bm, (bal_x, bal_y, z_fl_bot + 0.05), dir_xy, normal_xy, open_w * 1.06, 0.52, 0.18, 2)
                    add_oriented_box(bm, (bal_x + normal_xy[0] * 0.20, bal_y + normal_xy[1] * 0.20, z_fl_bot + 0.52), dir_xy, normal_xy, open_w * 1.04, 0.06, 0.78, 4)

                if actual_bay_w >= 3.4 and not is_curtain_atrium_bay:
                    add_oriented_box(
                        bm, (bx - normal_xy[0] * (recess_depth * 0.45), by - normal_xy[1] * (recess_depth * 0.45), win_mid_z),
                        dir_xy, normal_xy, 0.36, wall_depth * 0.92, win_h, 0
                    )
                    for sub_u in (-0.26, 0.26):
                        wx = gx + dir_xy[0] * (open_w * sub_u)
                        wy = gy + dir_xy[1] * (open_w * sub_u)
                        sub_w = open_w * 0.42
                        add_oriented_box(bm, (wx, wy, win_mid_z + 0.08), dir_xy, normal_xy, sub_w, 0.10, 0.07, 4)
                        add_oriented_box(bm, (wx, wy, win_mid_z), dir_xy, normal_xy, 0.06, 0.10, win_h, 4)
                else:
                    add_oriented_box(bm, (gx, gy, win_mid_z + 0.08), dir_xy, normal_xy, open_w * 0.92, 0.10, 0.07, 4)
                    add_oriented_box(bm, (gx, gy, win_mid_z), dir_xy, normal_xy, 0.06, 0.10, win_h, 4)

                fl_idx += 1
                if fl_idx % 3 == 0 and (z_fl_bot + floor_h) < total_height - 2.0:
                    add_oriented_box(
                        bm, (bx + normal_xy[0] * 0.14, by + normal_xy[1] * 0.14, z_fl_bot + floor_h),
                        dir_xy, normal_xy, actual_bay_w + 0.1, 0.32, 0.34, 2
                    )

                z_fl_bot += floor_h

        # Projecting Vertical Blade Sign (`PHOTO SERVICE` Royal Blue Blade Sign w/ White Border & Crest on Rue Notre-Dame, or Le Bogart)
        if has_blue_blade_sign and edge_len > 10.0 and normal_xy[0] < -0.2:
            ban_x = p1.x + edge_vec.x * 0.32 + normal_xy[0] * 0.68
            ban_y = p1.y + edge_vec.y * 0.32 + normal_xy[1] * 0.68
            # Main Royal Blue Blade Sign projecting 1.2m perpendicular to the wall!
            add_oriented_box(bm, (ban_x, ban_y, 7.2), dir_xy, normal_xy, 0.22, 1.18, 6.2, 8)
            # White trim border & top crest emblem on the blade sign
            add_oriented_box(bm, (ban_x, ban_y, 7.2), dir_xy, normal_xy, 0.25, 1.24, 6.32, 11)
            add_oriented_box(bm, (ban_x, ban_y, 7.2), dir_xy, normal_xy, 0.28, 1.06, 6.02, 8)
            add_oriented_box(bm, (ban_x, ban_y, 10.55), dir_xy, normal_xy, 0.30, 0.75, 0.65, 11)
            # Horizontal iron mounting brackets
            for bz in (4.6, 9.6):
                add_oriented_box(bm, (ban_x - normal_xy[0] * 0.35, ban_y - normal_xy[1] * 0.35, bz), dir_xy, normal_xy, 0.10, 0.85, 0.10, 4)
        elif has_corner_banner and edge_len > 8.0:
            ban_x = p1.x + edge_vec.x * 0.08 + normal_xy[0] * 0.25
            ban_y = p1.y + edge_vec.y * 0.08 + normal_xy[1] * 0.25
            add_oriented_box(bm, (ban_x, ban_y, 5.2), dir_xy, normal_xy, 1.35, 0.22, 4.6, 8)

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.025, segments=2)
    return obj


def build_royal_bank_tower_hero(bldg_data, collection, palette):
    """
    Constructs the iconic 1928 Royal Bank Tower (Édifice de la Banque Royale, 360 Rue Saint-Jacques,
    OSM ID 141608766) with deep 3D recessed window bays, smooth semicircular banking hall arches,
    fluted limestone piers, colonnaded loggia crown, corner turrets, and stepped pyramidal roof (121m).
    """
    pts = ensure_ccw(clean_polygon_pts(bldg_data["coords_xy"]))
    mesh = bpy.data.meshes.new("Hero_RoyalBankTower_360StJacques_Mesh")
    obj = bpy.data.objects.new("Hero_RoyalBankTower_360StJacques", mesh)
    collection.objects.link(obj)

    mat_stone_light = palette["Mat_MTL_Cream_Limestone"]
    mat_stone_podium = palette["Mat_MTL_WarmBuff_Limestone"]
    mat_stone_trim = palette["Mat_MTL_Cream_Limestone"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_bronze = palette["Mat_MTL_Dark_Bronze_CurtainWall"]
    mat_copper = palette["Mat_MTL_Verdigris_Copper"]
    mat_roof = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_gold = palette["Mat_MTL_Gold_Brass"]
    mat_interior = palette["Mat_MTL_Interior_Parallax"]

    for m in [mat_stone_light, mat_stone_podium, mat_stone_trim, mat_glass, mat_bronze, mat_copper, mat_roof, mat_gold, mat_interior]:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Monumental Rusticated Podium (0 to 23.5m) with 0.55m Recessed Window Core
    podium_h = 23.5
    recess_podium = 0.55
    pts_base = inset_polygon_2d(pts, -0.15)
    pts_pod_glass = inset_polygon_2d(pts, recess_podium)
    pts_pod_interior = inset_polygon_2d(pts, recess_podium + 0.40)

    add_prism_to_bm(bm, pts_base, -0.5, 2.2, 1, 1, 1)
    add_prism_to_bm(bm, pts_pod_interior, 2.2, podium_h - 0.5, 8, 2)
    add_prism_to_bm(bm, pts_pod_glass, 2.2, podium_h - 0.2, 3, 2)
    add_prism_to_bm(bm, pts, podium_h - 1.2, podium_h, 1, 2)

    pts_pod_cornice = inset_polygon_2d(pts, -0.58)
    add_prism_to_bm(bm, pts_pod_cornice, podium_h - 0.8, podium_h + 0.45, 2, 2, 2)
    pts_pod_parapet = inset_polygon_2d(pts, -0.12)
    add_prism_to_bm(bm, pts_pod_parapet, podium_h + 0.45, podium_h + 1.65, 2, 2)

    n = len(pts)
    for i in range(n):
        p1 = Vector(pts[i])
        p2 = Vector(pts[(i + 1) % n])
        edge_vec = p2 - p1
        edge_len = edge_vec.length
        if edge_len < 4.5:
            continue
        dir_xy = (edge_vec.x / edge_len, edge_vec.y / edge_len)
        normal_xy = (dir_xy[1], -dir_xy[0])
        num_bays = max(2, int(round(edge_len / 5.5)))
        bay_w = edge_len / num_bays
        pier_w = bay_w * 0.32

        for b_i in range(num_bays + 1):
            tp = b_i / num_bays
            px = p1.x + edge_vec.x * tp - normal_xy[0] * (recess_podium * 0.45)
            py = p1.y + edge_vec.y * tp - normal_xy[1] * (recess_podium * 0.45)
            add_oriented_box(bm, (px, py, 2.2 + (podium_h - 2.2) * 0.5), dir_xy, normal_xy, pier_w, recess_podium + 0.15, podium_h - 2.2, 1)
            for rz_i in range(int((podium_h - 3.0) / 0.75)):
                rz = 2.6 + rz_i * 0.75
                add_oriented_box(bm, (px + normal_xy[0] * 0.32, py + normal_xy[1] * 0.32, rz), dir_xy, normal_xy, pier_w + 0.10, 0.18, 0.52, 1)

        for b_i in range(num_bays):
            tc = (b_i + 0.5) / num_bays
            bx = p1.x + edge_vec.x * tc
            by = p1.y + edge_vec.y * tc
            open_w = bay_w - pier_w * 0.85

            add_smooth_arch_extrusion(
                bm, (bx - normal_xy[0] * (recess_podium * 0.42), by - normal_xy[1] * (recess_podium * 0.42)),
                11.5, 16.5, open_w * 0.52, dir_xy, normal_xy,
                open_w * 0.45, open_w * 0.42, ring_thickness=0.45, depth=recess_podium * 0.90,
                mat_ring=2, mat_spandrel=1, segments=24
            )
            add_oriented_box(
                bm, (bx - normal_xy[0] * (recess_podium * 0.45), by - normal_xy[1] * (recess_podium * 0.45), 19.2),
                dir_xy, normal_xy, open_w + 0.2, recess_podium + 0.12, 5.2, 1
            )
            gx = bx - normal_xy[0] * (recess_podium - 0.08)
            gy = by - normal_xy[1] * (recess_podium - 0.08)
            for m_u in (-0.25, 0.0, 0.25):
                add_oriented_box(bm, (gx + dir_xy[0] * (open_w * m_u), gy + dir_xy[1] * (open_w * m_u), 8.2), dir_xy, normal_xy, 0.09, 0.14, 11.5, 4)

    # 2. Set-back Skyscraper Tower Shaft (23.5m to 96.0m)
    cx, cy = bldg_data["centroid_xy"]
    u_dir = (0.857, 0.515)
    v_dir = (-0.515, 0.857)
    tower_w = 30.0
    tower_d = 32.0

    def make_rect_pts(cx_0, cy_0, w, d):
        hw, hd = w * 0.5, d * 0.5
        return [
            (cx_0 - u_dir[0] * hw - v_dir[0] * hd, cy_0 - u_dir[1] * hw - v_dir[1] * hd),
            (cx_0 + u_dir[0] * hw - v_dir[0] * hd, cy_0 + u_dir[1] * hw - v_dir[1] * hd),
            (cx_0 + u_dir[0] * hw + v_dir[0] * hd, cy_0 + u_dir[1] * hw + v_dir[1] * hd),
            (cx_0 - u_dir[0] * hw + v_dir[0] * hd, cy_0 - u_dir[1] * hw + v_dir[1] * hd),
        ]

    pts_tier1 = make_rect_pts(cx, cy, tower_w + 5.0, tower_d + 5.0)
    add_prism_to_bm(bm, pts_tier1, 23.5, 31.0, 0, 2)
    pts_tier1_cornice = make_rect_pts(cx, cy, tower_w + 6.2, tower_d + 6.2)
    add_prism_to_bm(bm, pts_tier1_cornice, 30.5, 31.4, 2, 2, 2)

    pts_shaft_glass = make_rect_pts(cx, cy, tower_w - 1.1, tower_d - 1.1)
    pts_shaft_interior = make_rect_pts(cx, cy, tower_w - 1.8, tower_d - 1.8)
    add_prism_to_bm(bm, pts_shaft_interior, 31.0, 95.5, 8, 2)
    add_prism_to_bm(bm, pts_shaft_glass, 31.0, 96.0, 3, 2)

    pts_shaft = make_rect_pts(cx, cy, tower_w, tower_d)
    for side_idx in range(4):
        sp1 = Vector(pts_shaft[side_idx])
        sp2 = Vector(pts_shaft[(side_idx + 1) % 4])
        s_vec = sp2 - sp1
        s_len = s_vec.length
        s_dir = (s_vec.x / s_len, s_vec.y / s_len)
        s_norm = (s_dir[1], -s_dir[0])
        num_cols = 7
        col_w = s_len / num_cols

        for c_i in range(num_cols + 1):
            px = sp1.x + s_vec.x * (c_i / num_cols) - s_norm[0] * 0.25
            py = sp1.y + s_vec.y * (c_i / num_cols) - s_norm[1] * 0.25
            pw = col_w * (0.52 if (c_i == 0 or c_i == num_cols) else 0.38)
            add_oriented_box(bm, (px, py, 63.5), s_dir, s_norm, pw, 0.68, 65.0, 0)

        for c_i in range(num_cols):
            tc = (c_i + 0.5) / num_cols
            bx = sp1.x + s_vec.x * tc - s_norm[0] * 0.45
            by = sp1.y + s_vec.y * tc - s_norm[1] * 0.45
            add_oriented_box(bm, (bx, by, 63.5), s_dir, s_norm, 0.10, 0.16, 64.0, 4)
            for z_sp in range(35, 95, 4):
                add_oriented_box(bm, (bx, by, float(z_sp)), s_dir, s_norm, col_w * 0.66, 0.26, 1.15, 4)
                add_oriented_box(bm, (bx + s_norm[0] * 0.16, by + s_norm[1] * 0.16, float(z_sp) + 0.62), s_dir, s_norm, col_w * 0.68, 0.22, 0.16, 2)

    # 3. Upper Colonnaded Loggia Crown & Corner Turrets (96.0m to 111.5m)
    pts_crown_cornice = make_rect_pts(cx, cy, tower_w + 1.8, tower_d + 1.8)
    add_prism_to_bm(bm, pts_crown_cornice, 95.5, 97.0, 2, 2, 2)

    pts_loggia = make_rect_pts(cx, cy, tower_w - 2.5, tower_d - 2.5)
    add_prism_to_bm(bm, pts_loggia, 97.0, 106.5, 0, 2)

    for corner_pt in pts_shaft:
        pts_turret = make_rect_pts(corner_pt[0], corner_pt[1], 4.2, 4.2)
        add_prism_to_bm(bm, pts_turret, 97.0, 108.0, 2, 5)
        pts_turret_cap = make_rect_pts(corner_pt[0], corner_pt[1], 2.2, 2.2)
        add_prism_to_bm(bm, pts_turret_cap, 108.0, 111.5, 5, 7)

    # 4. Stepped Pyramidal Roof & Obelisk Lantern (106.5m to 121.5m)
    steps = 6
    z_curr = 106.5
    step_h = 1.4
    for s_i in range(steps):
        frac = 1.0 - (s_i / steps) * 0.72
        pts_step = make_rect_pts(cx, cy, (tower_w - 3.0) * frac, (tower_d - 3.0) * frac)
        add_prism_to_bm(bm, pts_step, z_curr, z_curr + step_h, 5, 5)
        z_curr += step_h

    pts_lantern = make_rect_pts(cx, cy, 5.5, 5.5)
    add_prism_to_bm(bm, pts_lantern, z_curr, 118.5, 2, 5)
    pts_spire = make_rect_pts(cx, cy, 1.4, 1.4)
    add_prism_to_bm(bm, pts_spire, 118.5, 121.5, 7, 7)

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.03, segments=2)
    return obj


def build_skyway_bridge(bldg_data, collection, palette):
    pts = ensure_ccw(clean_polygon_pts(bldg_data["coords_xy"]))
    mesh = bpy.data.meshes.new("Bldg_1417455252_Skyway_Mesh")
    obj = bpy.data.objects.new("Bldg_1417455252_Skyway", mesh)
    collection.objects.link(obj)

    obj.data.materials.append(palette["Mat_MTL_Dark_Bronze_CurtainWall"])
    obj.data.materials.append(palette["Mat_MTL_Window_Glass_Dark"])

    bm = bmesh.new()
    add_prism_to_bm(bm, pts, 5.2, 9.0, 1, 0, 0)
    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.02, segments=2)
    return obj


def load_kit_assets():
    """Appends real Poly Haven 3D `jacaranda_tree_LOD0` and `street_lamp_01` from `assets/montreal_kit.blend`."""
    kit_path = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
    if not os.path.exists(kit_path):
        return None, None
    with bpy.data.libraries.load(kit_path, link=False) as (data_from, data_to):
        to_load = [name for name in ("jacaranda_tree_LOD0", "street_lamp_01") if name in data_from.objects]
        data_to.objects = to_load
    tree_proto = bpy.data.objects.get("jacaranda_tree_LOD0")
    lamp_proto = bpy.data.objects.get("street_lamp_01")
    return tree_proto, lamp_proto


def spawn_polyhaven_trees(tree_proto, tree_positions, streets_col, bm_props, mat_grate, mat_stake):
    """Instances the real Poly Haven `jacaranda_tree_LOD0` 3D tree model with cast-iron sidewalk grates and green tree stakes."""
    if not tree_proto:
        return
    # Ensure smooth shading on the Poly Haven tree mesh
    for poly in tree_proto.data.polygons:
        poly.use_smooth = True

    # Measure native height of tree_proto so we scale it to realistic urban sapling/street tree height (4.8m - 6.2m)
    bbox_z = [v[2] for v in tree_proto.bound_box]
    native_h = max(0.5, max(bbox_z) - min(bbox_z))

    for idx, (tx, ty) in enumerate(tree_positions):
        # Cast-iron tree grate on sidewalk
        add_oriented_box(bm_props, (tx, ty, 0.19), (1.0, 0.0), (0.0, 1.0), 1.45, 1.45, 0.03, mat_grate)
        # Two vertical green tree stakes on either side of the sapling (matching Royal_Bank_Tower_Portal.jpg!)
        for s_off in (-0.38, 0.38):
            add_oriented_box(
                bm_props, (tx + s_off * 0.85, ty + s_off * 0.52, 0.95),
                (0.85, 0.52), (-0.52, 0.85), 0.045, 0.045, 1.55, mat_stake
            )

        target_h = 5.0 if idx < 6 else (4.8 + (idx % 4) * 0.45)
        sc = target_h / native_h
        inst = bpy.data.objects.new(f"MTL_Tree_{idx:03d}", tree_proto.data)
        streets_col.objects.link(inst)
        inst.location = (tx, ty, 0.18 - min(bbox_z) * sc)
        inst.scale = (sc * 0.88, sc * 0.88, sc)
        inst.rotation_euler = (0.0, 0.0, (idx * 1.37) % (2.0 * math.pi))


def add_smooth_heritage_lamp(bm, lx, ly, mat_iron, mat_glow):
    ret_base = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=True, segments=14,
        radius1=0.22, radius2=0.14, depth=0.95,
        matrix=Matrix.Translation((lx, ly, 0.60))
    )
    for v in ret_base["verts"]:
        for f in v.link_faces:
            f.material_index = mat_iron
            f.smooth = True

    ret_post = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=True, segments=12,
        radius1=0.09, radius2=0.06, depth=4.1,
        matrix=Matrix.Translation((lx, ly, 3.0))
    )
    for v in ret_post["verts"]:
        for f in v.link_faces:
            f.material_index = mat_iron
            f.smooth = True

    ret_globe = bmesh.ops.create_icosphere(
        bm, subdivisions=3, radius=0.26,
        matrix=Matrix.Translation((lx, ly, 5.15)) @ Matrix.Scale(1.25, 4, (0, 0, 1))
    )
    for v in ret_globe["verts"]:
        for f in v.link_faces:
            f.material_index = mat_glow
            f.smooth = True

    ret_cap = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=True, segments=12,
        radius1=0.28, radius2=0.02, depth=0.24,
        matrix=Matrix.Translation((lx, ly, 5.52))
    )
    for v in ret_cap["verts"]:
        for f in v.link_faces:
            f.material_index = mat_iron
            f.smooth = True


def add_sculpted_parked_vehicle(bm, vx, vy, heading_deg, vtype, mat_body, mat_glass, mat_tire, mat_chrome, mat_light):
    """Adds a smooth-shaded sculpted 3D parked vehicle (SUV, sedan, or GMC utility van) with wheels, cabin, windshield, and bumpers."""
    rad = math.radians(heading_deg)
    d_xy = (math.sin(rad), math.cos(rad))
    n_xy = (d_xy[1], -d_xy[0])

    length = 4.9 if vtype == "van" else 4.55
    width = 1.92
    lower_h = 0.88 if vtype == "van" else 0.72
    cabin_h = 0.82 if vtype == "van" else 0.56
    cabin_l = length * (0.72 if vtype == "van" else 0.56)

    # 4 Wheels
    for wx_s in (-0.33, 0.33):
        for wy_s in (-0.46, 0.46):
            wx = vx + d_xy[0] * (length * wx_s) + n_xy[0] * (width * wy_s)
            wy = vy + d_xy[1] * (length * wx_s) + n_xy[1] * (width * wy_s)
            add_oriented_box(bm, (wx, wy, 0.34), d_xy, n_xy, 0.68, 0.24, 0.68, mat_tire, smooth=True)
            add_oriented_box(bm, (wx + n_xy[0] * (0.04 if wy_s > 0 else -0.04), wy + n_xy[1] * (0.04 if wy_s > 0 else -0.04), 0.34), d_xy, n_xy, 0.40, 0.25, 0.40, mat_chrome, smooth=True)

    # Lower chassis body
    add_oriented_box(bm, (vx, vy, 0.34 + lower_h * 0.5), d_xy, n_xy, length, width, lower_h, mat_body, smooth=True)
    # Bumpers & grille
    add_oriented_box(bm, (vx + d_xy[0] * (length * 0.51), vy + d_xy[1] * (length * 0.51), 0.42), d_xy, n_xy, 0.18, width * 0.96, 0.28, mat_tire, smooth=True)
    add_oriented_box(bm, (vx - d_xy[0] * (length * 0.51), vy - d_xy[1] * (length * 0.51), 0.42), d_xy, n_xy, 0.18, width * 0.96, 0.28, mat_tire, smooth=True)
    # Headlights / Taillights
    for s_side in (-0.36, 0.36):
        hx = vx + d_xy[0] * (length * 0.50) + n_xy[0] * (width * s_side)
        hy = vy + d_xy[1] * (length * 0.50) + n_xy[1] * (width * s_side)
        add_oriented_box(bm, (hx, hy, 0.68), d_xy, n_xy, 0.08, 0.32, 0.18, mat_light)

    # Upper glazed cabin greenhouse
    cab_offset = -0.22 if vtype != "van" else -0.15
    cx_cab = vx + d_xy[0] * cab_offset
    cy_cab = vy + d_xy[1] * cab_offset
    cz_cab = 0.34 + lower_h + cabin_h * 0.48
    add_oriented_box(bm, (cx_cab, cy_cab, cz_cab), d_xy, n_xy, cabin_l, width * 0.86, cabin_h, mat_glass, smooth=True)
    # Roof cap
    add_oriented_box(bm, (cx_cab, cy_cab, cz_cab + cabin_h * 0.50), d_xy, n_xy, cabin_l * 0.92, width * 0.84, 0.09, mat_body, smooth=True)
    if vtype == "van":
        # Ladder rack on top of white GMC utility van (matching Corner_Rue_SaintPierre.jpg!)
        add_oriented_box(bm, (cx_cab, cy_cab, cz_cab + cabin_h * 0.5 + 0.16), d_xy, n_xy, cabin_l * 0.88, width * 0.78, 0.10, mat_chrome)


def create_ground_and_streets(dossier, streets_col, palette):
    """Creates PBR-textured asphalt roadbed, concrete sidewalks with granite curbs, Poly Haven 3D trees, lamps, cones, caution tape, road markings, and parked vehicles."""
    mesh = bpy.data.meshes.new("Block_MTL_VM_0006_Streetscape_Mesh")
    obj = bpy.data.objects.new("Block_MTL_VM_0006_Streetscape", mesh)
    streets_col.objects.link(obj)

    mat_asphalt = palette["Mat_MTL_Street_Asphalt"]
    mat_cobble = palette["Mat_MTL_Cobblestone"]
    mat_sidewalk = palette["Mat_MTL_Plaza_Light_Granite"]
    mat_curb = palette["Mat_MTL_Plaza_Charcoal_Granite"]
    mat_iron = palette["Mat_MTL_CastIron_Black"]
    mat_glow = palette["Mat_MTL_Lamp_Glow"]
    mat_bark = palette["Mat_MTL_Tree_Bark"]
    mat_stake = palette["Mat_MTL_Stake_Green"]
    mat_caution = palette["Mat_MTL_Caution_Yellow"]
    mat_cone = palette["Mat_MTL_Traffic_Cone_Orange"]
    mat_white = palette["Mat_MTL_Reflective_White"]
    mat_hydrant = palette["Mat_MTL_Hydrant_Red"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_navy = palette["Mat_MTL_Storefront_Navy"]

    for m in [
        mat_asphalt, mat_cobble, mat_sidewalk, mat_curb, mat_iron,
        mat_glow, mat_bark, mat_stake, mat_caution, mat_cone,
        mat_white, mat_hydrant, mat_glass, mat_navy
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Base Asphalt Roadbed
    cx, cy = dossier["crs"]["block_center_xy_m"]
    add_oriented_box(bm, (cx, cy, -0.15), (1.0, 0.0), (0.0, 1.0), 340.0, 340.0, 0.30, 0)

    # 2. Raised Concrete Sidewalk Beds & Granite Curbs around every building footprint
    for b in dossier["osm_features"]["buildings"]:
        pts = ensure_ccw(clean_polygon_pts(b["coords_xy"]))
        if len(pts) < 3:
            continue
        bid = str(b.get("id", ""))
        sw_mat = 3 if bid in ("102127876", "126410859") else 2
        pts_sw = inset_polygon_2d(pts, -3.5)
        pts_curb = inset_polygon_2d(pts, -3.75)
        add_prism_to_bm(bm, pts_curb, -0.02, 0.16, 3, 3)
        add_prism_to_bm(bm, pts_sw, 0.0, 0.18, sw_mat, sw_mat)

    # 3. Highway segments, crosswalks, and white dashed parking lane markings
    for hw in dossier["osm_features"].get("highways", []):
        pts_hw = hw.get("coords_xy", [])
        tags = hw.get("tags", {})
        hw_type = tags.get("highway", "")
        if len(pts_hw) < 2:
            continue
        for k in range(len(pts_hw) - 1):
            p1 = Vector(pts_hw[k])
            p2 = Vector(pts_hw[k + 1])
            seg = p2 - p1
            slen = seg.length
            if slen < 0.5:
                continue
            d_xy = (seg.x / slen, seg.y / slen)
            n_xy = (-d_xy[1], d_xy[0])
            mid = (p1 + p2) * 0.5
            if hw_type == "footway" and tags.get("footway") == "crossing":
                num_stripes = max(2, int(slen / 1.2))
                for s_i in range(num_stripes):
                    st = (s_i + 0.5) / num_stripes
                    sx = p1.x + seg.x * st
                    sy = p1.y + seg.y * st
                    add_oriented_box(bm, (sx, sy, 0.015), d_xy, n_xy, 0.45, 2.4, 0.02, 10)
            elif tags.get("surface") == "sett":
                add_oriented_box(bm, (mid.x, mid.y, 0.008), d_xy, n_xy, slen, 7.5, 0.02, 1)

    # White dashed parking bay markings along Rue Notre-Dame Ouest (Camera 3) & Rue Saint-Jacques (Camera 1 & 4)
    nd_dir = (0.539, 0.842)
    nd_norm = (0.842, -0.539)
    for d_step in range(4, 58, 6):
        for lane_off in (-2.0, 2.0):
            lx = -91.06 + nd_dir[0] * d_step + nd_norm[0] * lane_off
            ly = -142.53 + nd_dir[1] * d_step + nd_norm[1] * lane_off
            add_oriented_box(bm, (lx, ly, 0.015), nd_dir, nd_norm, 2.6, 0.13, 0.02, 10)
            # Perpendicular T-tick at end of parking stall
            add_oriented_box(bm, (lx + nd_dir[0] * 1.3, ly + nd_dir[1] * 1.3, 0.015), nd_dir, nd_norm, 0.13, 0.65, 0.02, 10)

    sj_dir = (0.786, 0.618)
    sj_norm = (0.618, -0.786)
    for d_step in range(5, 65, 7):
        lx = -161.12 + sj_dir[0] * d_step + sj_norm[0] * 1.8
        ly = -126.80 + sj_dir[1] * d_step + sj_norm[1] * 1.8
        add_oriented_box(bm, (lx, ly, 0.015), sj_dir, sj_norm, 0.9, 0.14, 0.02, 10)
        add_oriented_box(bm, (lx + sj_dir[0] * 0.45, ly + sj_dir[1] * 0.45, 0.015), sj_dir, sj_norm, 0.14, 0.65, 0.02, 10)

    # 4. Real Poly Haven 3D `jacaranda_tree_LOD0` Street Trees (Replaces all procedural sphere blobs!)
    tree_proto, _ = load_kit_assets()
    tree_positions = [
        (-155.8, -133.2), (-149.5, -122.0), (-141.0, -108.0), (-132.5, -93.0),
        (-125.0, -144.0), (-138.0, -152.0), (-188.0, -155.0)
    ]
    tree_positions.extend([(t["xy"][0], t["xy"][1]) for t in dossier["osm_features"].get("trees", []) if "xy" in t])
    spawn_polyhaven_trees(tree_proto, tree_positions, streets_col, bm, mat_grate=4, mat_stake=7)

    # 5. Smooth Heritage Street Lamps (Removed the misplaced lamp at (-106.5, -52.0) in front of 500 Place d'Armes!)
    lamp_coords = [
        (-159.2, -139.5), (-152.0, -125.0), (-143.0, -110.0), (-133.5, -94.0),
        (-124.0, -78.0), (-115.0, -64.0),
        (-115.5, -138.0), (-128.0, -146.0), (-142.0, -155.0),
        (-192.0, -161.0), (-185.0, -148.0), (-177.0, -133.0),
    ]
    for lx, ly in lamp_coords:
        add_smooth_heritage_lamp(bm, lx, ly, mat_iron=4, mat_glow=5)

    # 6. Montreal Construction Barrels with Green/Black Bases, Triple Reflective Stripes, Steel Road Plate & Yellow Caution Tape
    cone_right_cluster = [
        (-170.2, -152.5), (-169.4, -151.4), (-168.6, -150.3), (-167.8, -149.2),
        (-171.2, -153.2), (-170.5, -154.0), (-169.6, -153.1),
    ]
    cone_left_cluster = [
        (-176.2, -147.5), (-175.0, -145.6), (-173.8, -143.7),
        (-156.4, -132.6), (-158.5, -137.2), (-163.5, -120.5), (-161.2, -116.8),
    ]
    # Steel trench plate under the right-hand cone cluster in Camera 4
    add_oriented_box(bm, (-169.6, -152.0, 0.19), sj_dir, sj_norm, 3.8, 2.2, 0.04, 6)

    for cx_0, cy_0 in (cone_right_cluster + cone_left_cluster):
        # Black rubber base + green lower collar (matching Corner_Rue_SaintPierre.jpg!)
        add_oriented_box(bm, (cx_0, cy_0, 0.20), (1.0, 0.0), (0.0, 1.0), 0.46, 0.46, 0.05, 4)
        ret_gr = bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=True, segments=16,
            radius1=0.18, radius2=0.16, depth=0.22,
            matrix=Matrix.Translation((cx_0, cy_0, 0.32))
        )
        for v in ret_gr["verts"]:
            for f in v.link_faces:
                f.material_index = 7
                f.smooth = True
        ret_c = bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=True, segments=16,
            radius1=0.155, radius2=0.115, depth=0.72,
            matrix=Matrix.Translation((cx_0, cy_0, 0.68))
        )
        for v in ret_c["verts"]:
            for f in v.link_faces:
                f.material_index = 9
                f.smooth = True
        for b_z, r_b in [(0.55, 0.152), (0.78, 0.138)]:
            ret_band = bmesh.ops.create_cone(
                bm, cap_ends=True, cap_tris=True, segments=16,
                radius1=r_b, radius2=r_b - 0.01, depth=0.13,
                matrix=Matrix.Translation((cx_0, cy_0, b_z))
            )
            for v in ret_band["verts"]:
                for f in v.link_faces:
                    f.material_index = 10
                    f.smooth = True

    # Yellow caution tape ribbons linking the construction barrels in Camera 4
    tape_pts = [(-171.2, -153.2), (-170.5, -154.0), (-169.6, -153.1), (-167.8, -149.2), (-170.2, -152.5)]
    for t_i in range(len(tape_pts) - 1):
        pa = Vector(tape_pts[t_i])
        pb = Vector(tape_pts[t_i + 1])
        seg = pb - pa
        slen = seg.length
        if slen > 0.1:
            td = (seg.x / slen, seg.y / slen)
            tn = (-td[1], td[0])
            mid = (pa + pb) * 0.5
            add_oriented_box(bm, (mid.x, mid.y, 0.76), td, tn, slen, 0.02, 0.07, 8)

    # 7. Sculpted Parked Vehicles along Rue Notre-Dame Ouest (Cam 3) and Rue Saint-Jacques (Cam 4 & Cam 1)
    # Cam 3 (`Rue_NotreDame_South_Side` at (-91.06, -142.53) heading 32.6 deg): parked SUVs/sedans along left & right curbs
    add_sculpted_parked_vehicle(bm, -88.2, -132.8, 32.6, "suv", mat_body=3, mat_glass=12, mat_tire=4, mat_chrome=10, mat_light=11)
    add_sculpted_parked_vehicle(bm, -84.5, -127.0, 32.6, "suv", mat_body=4, mat_glass=12, mat_tire=4, mat_chrome=10, mat_light=11)
    add_sculpted_parked_vehicle(bm, -82.2, -133.5, 32.6, "suv", mat_body=13, mat_glass=12, mat_tire=4, mat_chrome=10, mat_light=11)
    add_sculpted_parked_vehicle(bm, -76.0, -123.8, 32.6, "van", mat_body=10, mat_glass=12, mat_tire=4, mat_chrome=10, mat_light=11)
    # Cam 4 (`Corner_Rue_SaintPierre` at (-175.04, -153.77) heading 48.7 deg): white GMC utility van on right curb + dark parked SUV on left curb
    add_sculpted_parked_vehicle(bm, -162.8, -145.2, 228.7, "van", mat_body=10, mat_glass=12, mat_tire=4, mat_chrome=10, mat_light=9)
    add_sculpted_parked_vehicle(bm, -172.0, -141.5, 48.7, "suv", mat_body=13, mat_glass=12, mat_tire=4, mat_chrome=10, mat_light=10)
    # Cam 1 (`Royal_Bank_Tower_Portal` at (-161.12, -126.80) heading 51.8 deg): parked car down the canyon
    add_sculpted_parked_vehicle(bm, -143.5, -114.2, 231.8, "suv", mat_body=3, mat_glass=12, mat_tire=4, mat_chrome=10, mat_light=10)

    # 8. Stepped Dark Charcoal Granite Plaza Retaining Walls with Honed Capstones & Louver Vents (`SaintJacques_East_Canyon`)
    for step_i, (sx, sy, sw, sd, sh) in enumerate([
        (-102.5, -54.0, 18.0, 0.65, 0.88),
        (-99.5, -51.5, 16.0, 0.65, 1.38),
        (-96.0, -49.0, 14.0, 0.65, 1.88),
    ]):
        # Dark charcoal granite wall body & honed dark granite capstone lip
        add_oriented_box(bm, (sx, sy, sh * 0.5), (0.85, 0.52), (-0.52, 0.85), sw, sd, sh, 3)
        add_oriented_box(bm, (sx, sy, sh + 0.05), (0.85, 0.52), (-0.52, 0.85), sw + 0.12, sd + 0.12, 0.10, 3)
        # Dark recessed louver intake grille on middle wall
        if step_i == 1:
            add_oriented_box(bm, (sx - 0.2, sy + 0.1, 0.48), (0.85, 0.52), (-0.52, 0.85), 3.6, 0.72, 0.36, 4)

    hx, hy = -118.2, -66.5
    ret_h = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=True, segments=14,
        radius1=0.15, radius2=0.14, depth=0.82,
        matrix=Matrix.Translation((hx, hy, 0.55))
    )
    for v in ret_h["verts"]:
        for f in v.link_faces:
            f.material_index = 11
            f.smooth = True

    bm.to_mesh(mesh)
    bm.free()
    return obj


def build_500_place_darmes_proxy(b102, b126, proxy_col, palette):
    """
    Builds the iconic 32-story 500 Place d'Armes (Banque Canadienne Nationale Tower, ID 102127876)
    and its cantilevered dark bronze fluted podium (ID 126410859) matching `SaintJacques_East_Canyon.jpg`:
    - Floor-by-floor horizontal spandrel beams and center vertical mullions from ground floor up.
    - Dark recessed granite colonnade under the cantilevered bronze box with structural pillars,
      dark matte bronze/charcoal soffit ceiling, recessed lobby glazing, metal railings, and garage clearance signage.
    """
    pts_tower = ensure_ccw(clean_polygon_pts(b102["coords_xy"]))
    mesh_t = bpy.data.meshes.new("Proxy_102127876_500PlaceDArmes_Mesh")
    obj_t = bpy.data.objects.new("Proxy_102127876_500PlaceDArmes", mesh_t)
    proxy_col.objects.link(obj_t)

    mat_stone = palette["Mat_MTL_PierreGrise_Limestone"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_bronze = palette["Mat_MTL_Dark_Bronze_CurtainWall"]
    mat_roof = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_int = palette["Mat_MTL_Interior_Parallax"]
    mat_white = palette["Mat_MTL_Reflective_White"]
    mat_soffit = palette["Mat_MTL_Awning_Black"]
    for m in [mat_stone, mat_glass, mat_bronze, mat_roof, mat_int, mat_white]:
        obj_t.data.materials.append(m)

    bm = bmesh.new()
    total_h = 126.0
    pts_glass = inset_polygon_2d(pts_tower, 0.52)
    pts_int = inset_polygon_2d(pts_tower, 0.90)
    add_prism_to_bm(bm, pts_int, 0.0, total_h - 1.0, 4, 3)
    add_prism_to_bm(bm, pts_glass, 0.0, total_h - 0.5, 1, 3)

    n = len(pts_tower)
    for i in range(n):
        p1 = Vector(pts_tower[i])
        p2 = Vector(pts_tower[(i + 1) % n])
        ev = p2 - p1
        elen = ev.length
        if elen < 3.0:
            continue
        d_xy = (ev.x / elen, ev.y / elen)
        n_xy = (d_xy[1], -d_xy[0])
        ncols = max(2, int(round(elen / 3.4)))
        cw = elen / ncols
        for c_i in range(ncols + 1):
            tp = c_i / ncols
            px = p1.x + ev.x * tp - n_xy[0] * 0.22
            py = p1.y + ev.y * tp - n_xy[1] * 0.22
            pw = cw * (0.48 if (c_i == 0 or c_i == ncols) else 0.34)
            add_oriented_box(bm, (px, py, total_h * 0.5), d_xy, n_xy, pw, 0.62, total_h, 0)
        for c_i in range(ncols):
            tc = (c_i + 0.5) / ncols
            bx = p1.x + ev.x * tc - n_xy[0] * 0.42
            by = p1.y + ev.y * tc - n_xy[1] * 0.42
            # Center vertical bronze mullion dividing each window bay from ground floor to top!
            add_oriented_box(bm, (bx, by, total_h * 0.5), d_xy, n_xy, 0.08, 0.16, total_h - 1.0, 2)
            # Floor-by-floor spandrel beams starting at z = 4.0m (no 3-story unbroken glass strips!)
            for z_fl in range(4, int(total_h) - 2, 4):
                sp_h = 0.65 if z_fl < 12 else 1.08
                add_oriented_box(bm, (bx, by, float(z_fl)), d_xy, n_xy, cw * 0.72, 0.26, sp_h, 2)
                # Subtle horizontal interior office ceiling/Mullion bars on lower floors
                if z_fl <= 16:
                    add_oriented_box(bm, (bx, by, float(z_fl) - 1.8), d_xy, n_xy, cw * 0.70, 0.14, 0.08, 0)

    bm.to_mesh(mesh_t)
    bm.free()
    apply_bevel_and_smooth(obj_t, width=0.03, segments=2)

    # 2. Cantilevered Dark Bronze Fluted Podium Box (ID 126410859) in foreground of Cam 2!
    if b126:
        pts_pod = ensure_ccw(clean_polygon_pts(b126["coords_xy"]))
        mesh_p = bpy.data.meshes.new("Proxy_126410859_BronzePodium_Mesh")
        obj_p = bpy.data.objects.new("Proxy_126410859_BronzePodium", mesh_p)
        proxy_col.objects.link(obj_p)
        for m in [mat_bronze, mat_glass, mat_stone, mat_white, mat_soffit]:
            obj_p.data.materials.append(m)

        bm_p = bmesh.new()
        # Deeply recessed dark lobby core (inset 3.2m) & dark charcoal structural piers under the overhang (0 to 5.2m)
        pts_recess = inset_polygon_2d(pts_pod, 3.2)
        add_prism_to_bm(bm_p, pts_recess, 0.0, 5.2, 4, 4, 4)

        # Cantilevered bronze box (5.2m to 15.8m) with dark matte soffit (mat_bot=4)!
        add_prism_to_bm(bm_p, pts_pod, 5.2, 15.8, 0, 4, 4)

        # Structural dark granite columns, metal railings, and garage clearance sign under the overhang
        np_len = len(pts_pod)
        for i in range(np_len):
            p1 = Vector(pts_pod[i])
            p2 = Vector(pts_pod[(i + 1) % np_len])
            ev = p2 - p1
            elen = ev.length
            if elen < 2.0:
                continue
            d_xy = (ev.x / elen, ev.y / elen)
            n_xy = (d_xy[1], -d_xy[0])

            # Structural dark granite columns set 1.2m inside the overhang edge
            ncol_p = max(2, int(elen / 5.5))
            for kp in range(ncol_p + 1):
                tp = kp / ncol_p
                cx_p = p1.x + ev.x * tp - n_xy[0] * 1.35
                cy_p = p1.y + ev.y * tp - n_xy[1] * 1.35
                add_oriented_box(bm_p, (cx_p, cy_p, 2.6), d_xy, n_xy, 0.85, 0.85, 5.2, 4)

            # Metal picket railing & white clearance warning bar along the underpass ramp
            mid_p = (p1 + p2) * 0.5
            add_oriented_box(bm_p, (mid_p.x - n_xy[0] * 0.8, mid_p.y - n_xy[1] * 0.8, 0.95), d_xy, n_xy, elen * 0.75, 0.08, 0.90, 4)
            add_oriented_box(bm_p, (mid_p.x - n_xy[0] * 1.35, mid_p.y - n_xy[1] * 1.35, 2.35), d_xy, n_xy, min(4.2, elen * 0.45), 0.15, 0.38, 3)

            # Vertical bronze architectural fins along exterior of cantilevered box
            nfins = max(3, int(elen / 0.72))
            for f_i in range(nfins):
                tf = (f_i + 0.5) / nfins
                fx = p1.x + ev.x * tf + n_xy[0] * 0.14
                fy = p1.y + ev.y * tf + n_xy[1] * 0.14
                add_oriented_box(bm_p, (fx, fy, 10.55), d_xy, n_xy, 0.18, 0.32, 10.4, 0)

        bm_p.to_mesh(mesh_p)
        bm_p.free()
        apply_bevel_and_smooth(obj_p, width=0.02, segments=2)


def setup_world_and_lighting():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    world = bpy.data.worlds.get("Montreal_World") or bpy.data.worlds.new("Montreal_World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.10
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(out.inputs["Surface"], bg.outputs["Background"])

    hdri_path = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")
    if os.path.exists(hdri_path):
        env_tex = nodes.new("ShaderNodeTexEnvironment")
        env_tex.image = bpy.data.images.load(hdri_path, check_existing=True)
        links.new(bg.inputs["Color"], env_tex.outputs["Color"])
    else:
        sky = nodes.new("ShaderNodeTexSky")
        sky.sky_type = 'HOSEK_WILKIE'
        links.new(bg.inputs["Color"], sky.outputs["Color"])

    sun_data = bpy.data.lights.new(name="MTL_Sun_Key", type='SUN')
    sun_data.energy = 3.8
    sun_data.color = (1.0, 0.94, 0.84)
    sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name="MTL_Sun_Key", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(46.0), math.radians(14.0), math.radians(142.0))

    fill_data = bpy.data.lights.new(name="MTL_Canyon_Fill", type='SUN')
    fill_data.energy = 1.30
    fill_data.color = (0.86, 0.92, 1.0)
    fill_obj = bpy.data.objects.new(name="MTL_Canyon_Fill", object_data=fill_data)
    bpy.context.scene.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(62.0), math.radians(-18.0), math.radians(-38.0))


def render_cameras(dossier, iteration=1):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'

    cam_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Cameras")
    bpy.context.scene.collection.children.link(cam_col)

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100

    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        cam_x, cam_y = cam_info["blender_cam_xy_m"]
        heading_deg = float(cam_info.get("heading", cam_info.get("heading_deg", 0.0)))
        pitch_deg = float(cam_info.get("pitch_deg", 10.0))
        fov_deg = float(cam_info.get("fov_deg", 90.0))

        cam_data = bpy.data.cameras.new(name=f"Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(fov_deg)
        cam_data.clip_start = 0.25
        cam_data.clip_end = 1000.0

        cam_obj = bpy.data.objects.new(name=f"Cam_{label}", object_data=cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cam_x, cam_y, 1.7)
        cam_obj.rotation_euler = (
            math.radians(90.0 + pitch_deg),
            0.0,
            math.radians(-heading_deg)
        )

        scene.camera = cam_obj
        out_path = os.path.join(RENDERS_DIR, f"iter{iteration}_{label}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View camera -> {out_path} (pos=({cam_x}, {cam_y}), heading={heading_deg})")

    # Overview Camera (1280x720) — framed to showcase the entire Rue Saint-Jacques canyon AND the full 121m Royal Bank Tower crown!
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    ov_data = bpy.data.cameras.new(name="Cam_Overview")
    ov_data.lens_unit = 'FOV'
    ov_data.angle = math.radians(68.0)
    ov_data.clip_start = 0.5
    ov_data.clip_end = 1500.0
    ov_obj = bpy.data.objects.new(name="Cam_Overview", object_data=ov_data)
    cam_col.objects.link(ov_obj)

    ov_obj.location = (-32.0, -225.0, 148.0)
    target = Vector((-162.0, -78.0, 52.0))
    direction = target - ov_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    ov_obj.rotation_euler = rot_quat.to_euler()

    scene.camera = ov_obj
    snapshot_path = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
    scene.render.filepath = snapshot_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Overview Snapshot -> {snapshot_path}")


def main():
    clear_scene()
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    palette = kit.create_montreal_material_palette()
    palette = enhance_materials(palette)

    root_col, owned_col, proxy_col, streets_col = create_collection_hierarchy()

    # Tuple format: (total_h, podium_h, style, has_balustrade, has_mansard, has_awnings, has_blk_granite, has_banner, podium_arches, has_blue_blade, has_balconies)
    bldg_configs = {
        141608769: (68.0, 12.0, "sandstone_heritage", False, False, False, False, False, True, False, False),
        339888388: (50.0, 10.5, "cream_beaux_arts", True, False, False, False, False, True, False, False),
        340057019: (26.0, 8.5, "cream_beaux_arts", True, True, False, False, False, True, False, True),
        340057020: (38.0, 9.2, "cream_beaux_arts", True, False, True, False, False, True, False, True),
        340057021: (36.0, 9.0, "cream_beaux_arts", True, False, True, False, False, True, False, False),
        340057022: (32.0, 8.2, "cream_beaux_arts", True, False, False, True, False, False, False, False),
        340057023: (42.0, 8.5, "modern_granite_base", False, False, False, True, True, False, False, False),
        340057024: (24.0, 7.2, "sandstone_heritage", True, False, False, False, False, False, False, False),
        340057025: (22.0, 6.8, "redbrick_classical", True, False, False, False, False, False, False, False),
        340057026: (23.0, 7.0, "cream_beaux_arts", True, False, False, False, False, False, False, False),
        340057027: (26.0, 7.5, "white_beaux_arts", True, False, False, False, False, False, False, False),
        340057028: (25.0, 7.2, "white_beaux_arts", True, False, False, False, False, False, False, False),
        340057029: (28.0, 7.8, "white_beaux_arts", True, False, False, False, False, False, False, False),
        340057030: (22.0, 7.0, "cream_beaux_arts", True, False, False, False, False, False, False, False),
        340058292: (28.0, 11.5, "sandstone_heritage", True, False, False, False, False, True, False, False),
        340058293: (26.0, 8.5, "cream_beaux_arts", True, False, True, False, False, True, False, True),
        340058294: (25.0, 8.0, "white_beaux_arts", True, False, False, False, False, True, False, False),
        340058295: (27.0, 8.2, "sandstone_heritage", True, False, False, False, False, True, False, False),
        340058296: (30.0, 8.8, "cream_beaux_arts", True, False, False, False, False, True, False, False),
        340058297: (32.0, 9.0, "white_beaux_arts", True, False, False, False, False, True, False, False),
        340058298: (46.0, 11.0, "white_beaux_arts", True, False, False, False, False, True, False, False),
        340058299: (38.0, 10.0, "cream_beaux_arts", True, False, False, False, False, True, False, False),
        1237390984: (24.0, 7.5, "sandstone_heritage", True, False, False, False, False, True, False, False),
    }

    owned_count = 0
    proxy_count = 0
    b102 = next((b for b in dossier["osm_features"]["buildings"] if int(b["id"]) == 102127876), None)
    b126 = next((b for b in dossier["osm_features"]["buildings"] if int(b["id"]) == 126410859), None)
    if b102:
        build_500_place_darmes_proxy(b102, b126, proxy_col, palette)
        proxy_count += (2 if b126 else 1)

    for b in dossier["osm_features"]["buildings"]:
        bid = int(b["id"])
        if bid in (102127876, 126410859):
            continue
        bname = b.get("name", "")
        is_owned = bool(b.get("is_primary_owner", False))
        target_col = owned_col if is_owned else proxy_col

        if is_owned:
            owned_count += 1
            if bid == 141608766:
                build_royal_bank_tower_hero(b, target_col, palette)
            elif bid == 1417455252:
                build_skyway_bridge(b, target_col, palette)
            else:
                cfg = bldg_configs.get(bid, (28.0, 8.0, "cream_beaux_arts", True, False, False, False, False, True, False, False))
                build_beaux_arts_building(
                    bid, bname, b["coords_xy"], target_col, palette,
                    total_height=cfg[0], podium_height=cfg[1], style=cfg[2],
                    has_balustrade=cfg[3], has_Copper_mansard=cfg[4],
                    has_storefront_awnings=cfg[5], has_black_granite_base=cfg[6],
                    has_corner_banner=cfg[7], podium_arches=cfg[8],
                    has_blue_blade_sign=cfg[9], has_iron_balconies=cfg[10]
                )
        else:
            proxy_count += 1
            levels = int(b.get("tags", {}).get("building:levels", 4))
            # Create the authentic 3-story Photo Service foreground building stepping up to the 5-story ornate neighbor w/ red-brick party wall!
            if bid in (339898461, 339898462):
                h_proxy = 11.8
                pod_h = 4.6
                is_photo_service = (bid == 339898461)
                build_beaux_arts_building(
                    bid, f"Proxy_{bname}" if bname else "Proxy", b["coords_xy"], target_col, palette,
                    total_height=h_proxy, podium_height=pod_h, style="cream_beaux_arts",
                    has_balustrade=False, podium_arches=False, has_blue_blade_sign=is_photo_service
                )
            elif bid == 339898458:
                build_beaux_arts_building(
                    bid, f"Proxy_{bname}" if bname else "Proxy", b["coords_xy"], target_col, palette,
                    total_height=19.2, podium_height=5.2, style="sandstone_heritage",
                    has_balustrade=True, podium_arches=False
                )
            else:
                h_proxy = max(18.0, levels * 3.8)
                build_beaux_arts_building(
                    bid, f"Proxy_{bname}" if bname else "Proxy", b["coords_xy"], target_col, palette,
                    total_height=h_proxy, podium_height=min(8.5, h_proxy * 0.35), style="cream_beaux_arts",
                    has_balustrade=True, podium_arches=False
                )

    print(f"Built {owned_count} Owned buildings and {proxy_count} Context Proxy buildings.")

    create_ground_and_streets(dossier, streets_col, palette)
    setup_world_and_lighting()

    iteration = 2
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        if idx + 1 < len(sys.argv):
            try:
                iteration = int(sys.argv[idx + 1])
            except ValueError:
                pass

    render_cameras(dossier, iteration=iteration)

    blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.blend")
    usdc_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.usdc")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.wm.usd_export(filepath=usdc_path)
    print(f"Saved {blend_path} and exported {usdc_path}")


if __name__ == "__main__":
    main()
