"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0024 (Iteration 2)
(Bassin Bonsecours, Île Bonsecours & La Grande Roue de Montréal)
362 Rue de la Commune Est, Montréal, QC H2Y 0B4

Iteration 2 Complete Architectural & Waterfront Remodel:
1. Bassin Bonsecours Deep Water Basin (Z = -2.20m) & Sculpted Île Bonsecours Island:
   - Eliminated the giant solid ground slab that covered the water in Iteration 1!
   - Full wave-displaced 2K PBR water basin at Z = -2.20m (wired with water_river_diffuse_2k.jpg,
     water_river_nor_gl_2k.jpg, water_river_rough_2k.jpg via build_montreal_kit.py) with procedural
     wave ripple displacement, covering H1..H3 (North basin), V1..V2 (West channel), and V7..V8 (East basin).
   - Stepped granite quay retaining walls (Z = -2.50m .. +0.16m) with projecting stone coping and cast-iron
     mooring bollards around the entire Île Bonsecours island (V3..V6, H3..H8) and outer quays.
   - Lush green park lawns (leafy_grass_Diffuse_2k.jpg, Mat_MTL_Grass_Lawn_PBR at Z = +0.195m),
     granite curbs (Z = +0.225m), and micro-stepped single-sided +Z limestone/crushed-stone walkways
     (Z = +0.245m .. +0.265m) matching every band of satellite_topdown.png.
   - Two curved pedestrian bridges connecting Île Bonsecours on the East (H3 V7..V8) and West (H6 V1..V2),
     plus the North stone quay promenade (H1) with metal mesh guardrails and pedal boats / harbor vessels in the water.
2. La Grande Roue de Montréal (60m White Structural Steel Ferris Wheel):
   - Positioned at the exact island location (V4..V5, H4..H7 in satellite_topdown.png, centered at X=621.76, Y=419.00).
   - 60m white enamel structural steel wheel with 42 glazed climate-controlled passenger gondolas,
     4 heavy A-frame support legs, hub spindle flanges, tension spokes, and boarding platform.
3. Pavillon du Bassin Bonsecours (North Bistro 1097403709), South Bistro & Ticket Pavilions (1097403706):
   - Articulated stone and glass Pavillon du Bassin Bonsecours (V3..V4, H4..H6) with dark flat roof,
     white twin-canopy court, and amphitheater seating steps on the west lawn.
   - Glazed Bistro, terrace umbrellas, and white steel entrance/ticket pavilions at the south base of the wheel (H6..H7).
   - Terrasses Bonsecours (46866826), East Pier Pavilion (1180387335), and MTL Zipline Tower (1180387340 & 1180387341 visual context)
     with red-and-white banner wrap and aerial cables.
   - Hangar 16 (46866827) historic clock-quay warehouse with weathered industrial facade, recessed bays, and north quay edge.
4. High-Poly Poly Haven 3D Trees & Street Furniture:
   - Dense high-poly Poly Haven 3D trees (jacaranda_tree), heritage streetlamps (street_lamp_01), and benches
     (modular_street_seating) placed around the island perimeter, north boardwalk, and waterfront parks.
"""

import os
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import math
import shutil
import bpy
import bmesh
from mathutils import Vector, Matrix

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0024"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")
SNAPSHOT_PATH = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.usdc")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
MONTREAL_KIT_PATH = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
HDRI_PATH = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT_PATH), exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


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


def make_box_pbr_mat(name, prefix, tint=(1.0, 1.0, 1.0), scale=0.35, roughness_mult=1.0, metallic=0.0, normal_strength=0.75, tint_factor=0.65):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = metallic
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    diff_path = kit._find_polyhaven_map(prefix, ["Diffuse_2k", "diff_2k", "col_2k"])
    rough_path = kit._find_polyhaven_map(prefix, ["Roughness_2k", "Rough_2k", "rough_2k"])
    nor_path = kit._find_polyhaven_map(prefix, ["nor_gl_2k", "nor_2k", "normal_2k"])

    if diff_path and os.path.exists(diff_path):
        img_d = kit.get_or_load_image(diff_path, "sRGB")
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = img_d
        tex_d.projection = "BOX"
        tex_d.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])

        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = tint_factor
        mix.inputs["B"].default_value = (tint[0], tint[1], tint[2], 1.0)
        links.new(tex_d.outputs["Color"], mix.inputs["A"])
        links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1.0)

    if rough_path and os.path.exists(rough_path):
        img_r = kit.get_or_load_image(rough_path, "Non-Color")
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = img_r
        tex_r.projection = "BOX"
        tex_r.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_r.inputs["Vector"])
        math_r = nodes.new("ShaderNodeMath")
        math_r.operation = "MULTIPLY"
        math_r.inputs[1].default_value = roughness_mult
        links.new(tex_r.outputs["Color"], math_r.inputs[0])
        links.new(math_r.outputs["Value"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.65 * roughness_mult

    if nor_path and os.path.exists(nor_path):
        img_n = kit.get_or_load_image(nor_path, "Non-Color")
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = img_n
        tex_n.projection = "BOX"
        tex_n.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nor = nodes.new("ShaderNodeNormalMap")
        nor.inputs["Strength"].default_value = normal_strength
        links.new(tex_n.outputs["Color"], nor.inputs["Color"])
        links.new(nor.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def create_palette():
    pal = kit.create_montreal_material_palette()

    # 1. Dedicated 2K PBR Water Material for Bassin Bonsecours (deep blue-slate water matching satellite_topdown.png)
    mat_water = kit.get_or_create_water_pbr_material("Mat_MTL_Bassin_Bonsecours_Water_PBR", uv_scale=18.0)
    # Enhance with object-space box mapping + deep slate-navy tint matching Google Satellite & Street View
    wnodes = mat_water.node_tree.nodes
    wlinks = mat_water.node_tree.links
    bsdf_w = next((n for n in wnodes if n.type == "BSDF_PRINCIPLED"), None)
    tcoord_w = next((n for n in wnodes if n.type == "TEX_COORD"), None)
    mapping_w = next((n for n in wnodes if n.type == "MAPPING"), None)
    if bsdf_w and tcoord_w and mapping_w:
        mapping_w.inputs["Scale"].default_value = (0.08, 0.08, 0.08)
        wlinks.new(mapping_w.inputs["Vector"], tcoord_w.outputs["Object"])
        tex_d = wnodes.get("TexImage_Water_Diffuse")
        if tex_d:
            tex_d.projection = "BOX"
            mix_w = wnodes.new("ShaderNodeMix")
            mix_w.data_type = "RGBA"
            mix_w.blend_type = "MULTIPLY"
            mix_w.inputs["Factor"].default_value = 0.78
            mix_w.inputs["B"].default_value = (0.14, 0.24, 0.36, 1.0)
            wlinks.new(mix_w.inputs["A"], tex_d.outputs["Color"])
            wlinks.new(bsdf_w.inputs["Base Color"], mix_w.outputs["Result"])
        else:
            bsdf_w.inputs["Base Color"].default_value = (0.08, 0.16, 0.26, 1.0)
        bsdf_w.inputs["Roughness"].default_value = 0.09
        if "Specular IOR Level" in bsdf_w.inputs:
            bsdf_w.inputs["Specular IOR Level"].default_value = 0.90
        # Add subtle procedural wave bump on top of 2K normal map
        noise_w = wnodes.new("ShaderNodeTexNoise")
        noise_w.inputs["Scale"].default_value = 1.6
        noise_w.inputs["Detail"].default_value = 5.0
        noise_w.inputs["Roughness"].default_value = 0.45
        bump_w = wnodes.new("ShaderNodeBump")
        bump_w.inputs["Strength"].default_value = 0.14
        bump_w.inputs["Distance"].default_value = 0.08
        wlinks.new(noise_w.inputs["Vector"], tcoord_w.outputs["Object"])
        wlinks.new(bump_w.inputs["Height"], noise_w.outputs["Fac"])
        nmap_w = next((n for n in wnodes if n.type == "NORMAL_MAP"), None)
        if nmap_w:
            wlinks.new(bump_w.inputs["Normal"], nmap_w.outputs["Normal"])
        wlinks.new(bsdf_w.inputs["Normal"], bump_w.outputs["Normal"])
    pal["water_basin"] = mat_water

    # 2. Lush Green Park Lawn PBR (leafy_grass_Diffuse_2k.jpg at Z = +0.195m)
    mat_grass = make_box_pbr_mat(
        "Mat_MTL_Grass_Lawn_PBR",
        "leafy_grass",
        tint=(0.38, 0.60, 0.24),
        scale=0.22,
        roughness_mult=0.95,
        normal_strength=0.65,
        tint_factor=0.65,
    )
    pal["grass_lawn"] = mat_grass
    pal["park_lawn"] = mat_grass

    # 3. Island Limestone & Crushed-Stone Walkways (high brightness/contrast warm cream limestone & tan gravel matching satellite_topdown.png H4..H7, V3..V6)
    pal["walkway_limestone"] = make_box_pbr_mat(
        "Mat_MTL_Walkway_Limestone_PBR",
        "concrete_pavers",
        tint=(1.32, 1.28, 1.20),
        scale=0.35,
        roughness_mult=0.78,
        normal_strength=0.55,
        tint_factor=0.65,
    )
    pal["walkway_gravel"] = make_box_pbr_mat(
        "Mat_MTL_Walkway_Gravel_PBR",
        "gravel_concrete_02",
        tint=(1.36, 1.26, 1.08),
        scale=0.30,
        roughness_mult=0.80,
        normal_strength=0.65,
        tint_factor=0.68,
    )
    pal["island_plaza"] = make_box_pbr_mat(
        "Mat_MTL_Island_Plaza_PBR",
        "concrete_pavement_02",
        tint=(1.26, 1.23, 1.18),
        scale=0.28,
        roughness_mult=0.80,
        normal_strength=0.50,
        tint_factor=0.62,
    )
    pal["wheel_apron"] = make_box_pbr_mat(
        "Mat_MTL_Wheel_Apron_PBR",
        "worn_asphalt",
        tint=(0.68, 0.67, 0.66),
        scale=0.25,
        roughness_mult=0.90,
        normal_strength=0.55,
        tint_factor=0.65,
    )

    # 4. Stepped Granite Quay Walls & Curbs
    pal["quay_granite"] = make_box_pbr_mat(
        "Mat_MTL_Quay_Granite_PBR",
        "stone_block_wall",
        tint=(0.68, 0.67, 0.64),
        scale=0.32,
        roughness_mult=0.88,
        normal_strength=0.85,
        tint_factor=0.60,
    )
    pal["granite_curb"] = make_box_pbr_mat(
        "Mat_MTL_Granite_Curb_PBR",
        "sandstone_blocks_05",
        tint=(0.78, 0.77, 0.74),
        scale=0.45,
        roughness_mult=0.82,
        normal_strength=0.60,
        tint_factor=0.55,
    )

    # 5. Architectural Facade Materials (diverse Poly Haven 2K PBR)
    pal["sandstone_pbr"] = make_box_pbr_mat(
        "PBR_Sandstone_Blocks",
        "sandstone_blocks_05",
        tint=(0.86, 0.84, 0.79),
        scale=0.38,
        roughness_mult=0.85,
        normal_strength=0.65,
        tint_factor=0.60,
    )
    pal["weathered_hangar_wall"] = make_box_pbr_mat(
        "PBR_Weathered_Hangar_Wall",
        "castle_brick_02_white",
        tint=(0.76, 0.77, 0.78),
        scale=0.35,
        roughness_mult=0.90,
        normal_strength=0.75,
        tint_factor=0.65,
    )
    pal["brick_pbr"] = make_box_pbr_mat(
        "PBR_Castle_Brick",
        "castle_brick_02_red",
        tint=(0.82, 0.48, 0.42),
        scale=0.40,
        roughness_mult=0.85,
        normal_strength=0.70,
        tint_factor=0.65,
    )
    pal["cobble_pbr"] = make_box_pbr_mat(
        "PBR_Cobblestone",
        "cobblestone_floor_08",
        tint=(0.74, 0.73, 0.71),
        scale=0.36,
        roughness_mult=0.85,
        normal_strength=0.75,
        tint_factor=0.65,
    )
    pal["asphalt_pbr"] = make_box_pbr_mat(
        "PBR_Asphalt_Road",
        "asphalt_02",
        tint=(0.48, 0.49, 0.51),
        scale=0.30,
        roughness_mult=0.90,
        normal_strength=0.55,
        tint_factor=0.70,
    )
    pal["tin_roof_pbr"] = make_box_pbr_mat(
        "PBR_Tin_Roof",
        "box_profile_metal_sheet",
        tint=(0.56, 0.58, 0.60),
        scale=0.35,
        roughness_mult=0.65,
        metallic=0.45,
        normal_strength=0.50,
        tint_factor=0.70,
    )
    pal["roof_dark_pbr"] = make_box_pbr_mat(
        "PBR_Dark_Flat_Roof",
        "worn_asphalt",
        tint=(0.34, 0.35, 0.38),
        scale=0.30,
        roughness_mult=0.92,
        normal_strength=0.50,
        tint_factor=0.80,
    )
    pal["timber_wood"] = make_box_pbr_mat(
        "Mat_MTL_Wood_Timber",
        "weathered_planks",
        tint=(0.74, 0.64, 0.50),
        scale=0.40,
        roughness_mult=0.88,
        normal_strength=0.70,
        tint_factor=0.65,
    )

    # 6. Pristine White Enamel Structural Steel (La Grande Roue, white canopies, bridges)
    mat_white_steel = bpy.data.materials.new("Mat_MTL_White_Steel")
    mat_white_steel.use_nodes = True
    ws_nodes = mat_white_steel.node_tree.nodes
    ws_links = mat_white_steel.node_tree.links
    ws_nodes.clear()
    ws_out = ws_nodes.new("ShaderNodeOutputMaterial")
    ws_bsdf = ws_nodes.new("ShaderNodeBsdfPrincipled")
    ws_bsdf.inputs["Base Color"].default_value = (0.95, 0.96, 0.97, 1.0)
    ws_bsdf.inputs["Metallic"].default_value = 0.18
    ws_bsdf.inputs["Roughness"].default_value = 0.22
    if "Specular IOR Level" in ws_bsdf.inputs:
        ws_bsdf.inputs["Specular IOR Level"].default_value = 0.85
    ws_links.new(ws_out.inputs["Surface"], ws_bsdf.outputs["BSDF"])
    pal["white_steel"] = mat_white_steel

    # 7. Panoramic Architectural Glass
    mat_glass = bpy.data.materials.new("Mat_MTL_Window_Glass_Dark")
    mat_glass.use_nodes = True
    gl_nodes = mat_glass.node_tree.nodes
    gl_links = mat_glass.node_tree.links
    gl_nodes.clear()
    gl_out = gl_nodes.new("ShaderNodeOutputMaterial")
    gl_bsdf = gl_nodes.new("ShaderNodeBsdfPrincipled")
    gl_bsdf.inputs["Base Color"].default_value = (0.06, 0.11, 0.16, 1.0)
    gl_bsdf.inputs["Roughness"].default_value = 0.05
    gl_bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in gl_bsdf.inputs:
        gl_bsdf.inputs["Specular IOR Level"].default_value = 0.95
    gl_links.new(gl_out.inputs["Surface"], gl_bsdf.outputs["BSDF"])
    pal["glass_dark"] = mat_glass

    # 8. Accent Materials (Zipline red banner, blue ticket booths, cast iron)
    pal["zipline_red"] = kit.get_or_create_pbr_material("Mat_MTL_Zipline_Red", "#B8332A", roughness=0.55)
    pal["kiosk_blue"] = kit.get_or_create_pbr_material("Mat_MTL_Kiosk_Blue", "#1B5E91", roughness=0.35, metallic=0.20)
    pal["cast_iron"] = pal["Mat_MTL_CastIron_Black"]
    pal["roof_slate"] = pal["roof_dark_pbr"]

    return pal


def ensure_ccw(pts):
    pts = [Vector((p[0], p[1])) for p in pts]
    if len(pts) > 1 and (pts[0] - pts[-1]).length < 1e-4:
        pts = pts[:-1]
    if len(pts) < 3:
        return [(p.x, p.y) for p in pts]
    area2 = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))
    if area2 < 0:
        pts.reverse()
    return [(p.x, p.y) for p in pts]


def inset_polygon_2d(pts, amount):
    pts_ccw = ensure_ccw(pts)
    n = len(pts_ccw)
    if n < 3:
        return pts_ccw
    edges = []
    for i in range(n):
        p1 = Vector(pts_ccw[i])
        p2 = Vector(pts_ccw[(i + 1) % n])
        d = (p2 - p1)
        length = d.length
        if length < 1e-4:
            continue
        d.normalize()
        normal = Vector((-d.y, d.x))
        edges.append((p1, p2, normal))
    if len(edges) < 3:
        return pts_ccw
    offset_lines = []
    for p1, p2, normal in edges:
        op1 = p1 + normal * amount
        op2 = p2 + normal * amount
        offset_lines.append((op1, op2))
    new_pts = []
    m = len(offset_lines)
    for i in range(m):
        p1, p2 = offset_lines[i]
        p3, p4 = offset_lines[(i + 1) % m]
        d1 = p2 - p1
        d2 = p4 - p3
        denom = d1.x * d2.y - d1.y * d2.x
        if abs(denom) < 1e-6:
            new_pts.append((p2.x, p2.y))
        else:
            t = ((p3.x - p1.x) * d2.y - (p3.y - p1.y) * d2.x) / denom
            ip = p1 + d1 * max(-2.0, min(3.0, t))
            new_pts.append((ip.x, ip.y))
    return new_pts


def add_top_face_to_bm(bm, pts, z_top, mat_top=0):
    """Adds a single-sided upward (+Z) polygon face so Cycles never renders coplanar black undersides."""
    if len(pts) < 3:
        return None
    pts_ccw = ensure_ccw(pts)
    verts = [bm.verts.new((p[0], p[1], z_top)) for p in pts_ccw]
    try:
        f = bm.faces.new(verts)
        f.material_index = mat_top
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
        return f
    except ValueError:
        return None


def add_prism_to_bm(bm, pts, z_bottom, z_top, mat_side=0, mat_top=1, mat_bottom=None):
    if len(pts) < 3:
        return
    pts_ccw = ensure_ccw(pts)
    n = len(pts_ccw)
    v_bot = [bm.verts.new((p[0], p[1], z_bottom)) for p in pts_ccw]
    v_top = [bm.verts.new((p[0], p[1], z_top)) for p in pts_ccw]
    for i in range(n):
        v1 = v_bot[i]
        v2 = v_bot[(i + 1) % n]
        v3 = v_top[(i + 1) % n]
        v4 = v_top[i]
        try:
            f = bm.faces.new((v1, v2, v3, v4))
            f.material_index = mat_side
        except ValueError:
            pass
    if mat_top is not None:
        try:
            f_top = bm.faces.new(v_top)
            f_top.material_index = mat_top
        except ValueError:
            pass
    if mat_bottom is not None:
        try:
            f_bot = bm.faces.new(list(reversed(v_bot)))
            f_bot.material_index = mat_bottom
        except ValueError:
            pass


def add_polyline_ribbon_top_face(bm, pts, width, z_top, mat_idx=0):
    """Creates single-sided +Z ribbon quads along a 2D polyline at z_top (no bottom face to avoid Cycles coplanar shadowing)."""
    if len(pts) < 2:
        return
    hw = width * 0.5
    n = len(pts)
    left_pts = []
    right_pts = []
    for i in range(n):
        p = Vector((pts[i][0], pts[i][1]))
        if i == 0:
            tangent = (Vector((pts[1][0], pts[1][1])) - p).normalized()
        elif i == n - 1:
            tangent = (p - Vector((pts[i - 1][0], pts[i - 1][1]))).normalized()
        else:
            t1 = (p - Vector((pts[i - 1][0], pts[i - 1][1]))).normalized()
            t2 = (Vector((pts[i + 1][0], pts[i + 1][1])) - p).normalized()
            tangent = (t1 + t2)
            if tangent.length < 1e-4:
                tangent = t1
            else:
                tangent.normalize()
        normal = Vector((-tangent.y, tangent.x))
        left_pts.append(p + normal * hw)
        right_pts.append(p - normal * hw)

    v_left = [bm.verts.new((p.x, p.y, z_top)) for p in left_pts]
    v_right = [bm.verts.new((p.x, p.y, z_top)) for p in right_pts]
    for i in range(n - 1):
        try:
            f = bm.faces.new((v_right[i], v_right[i + 1], v_left[i + 1], v_left[i]))
            f.material_index = mat_idx
            f.normal_update()
            if f.normal.z < 0:
                f.normal_flip()
        except ValueError:
            pass


def add_oriented_box(bm, center, dir_xy, norm_xy, width, depth, height, mat_idx=0, smooth=False, include_bottom=False):
    cx, cy, cz = center
    dx, dy = dir_xy
    nx, ny = norm_xy
    hw = width * 0.5
    hd = depth * 0.5
    hh = height * 0.5
    corners_2d = [
        (cx - dx * hw - nx * hd, cy - dy * hw - ny * hd),
        (cx + dx * hw - nx * hd, cy + dy * hw - ny * hd),
        (cx + dx * hw + nx * hd, cy + dy * hw + ny * hd),
        (cx - dx * hw + nx * hd, cy - dy * hw + ny * hd),
    ]
    if (dx * ny - dy * nx) < 0.0:
        corners_2d.reverse()
    v_bot = [bm.verts.new((x, y, cz - hh)) for x, y in corners_2d]
    v_top = [bm.verts.new((x, y, cz + hh)) for x, y in corners_2d]
    for i in range(4):
        try:
            f = bm.faces.new((v_bot[i], v_bot[(i + 1) % 4], v_top[(i + 1) % 4], v_top[i]))
            f.material_index = mat_idx
            f.smooth = smooth
        except ValueError:
            pass
    try:
        f_t = bm.faces.new(v_top)
        f_t.material_index = mat_idx
        f_t.smooth = smooth
    except ValueError:
        pass
    if include_bottom:
        try:
            f_b = bm.faces.new(list(reversed(v_bot)))
            f_b.material_index = mat_idx
            f_b.smooth = smooth
        except ValueError:
            pass


def add_cylinder_to_bm(bm, p1, p2, radius, segments=8, mat_idx=0, smooth=True, cap_ends=True):
    p1 = Vector(p1)
    p2 = Vector(p2)
    axis = p2 - p1
    length = axis.length
    if length < 1e-5:
        return []
    v_axis = axis.normalized()
    if abs(v_axis.z) < 0.9:
        ref = Vector((0.0, 0.0, 1.0))
    else:
        ref = Vector((1.0, 0.0, 0.0))
    u = v_axis.cross(ref).normalized()
    v = v_axis.cross(u).normalized()

    ring1 = []
    ring2 = []
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        ca = math.cos(angle) * radius
        sa = math.sin(angle) * radius
        offset = u * ca + v * sa
        v1 = bm.verts.new(p1 + offset)
        v2 = bm.verts.new(p2 + offset)
        ring1.append(v1)
        ring2.append(v2)

    faces = []
    for i in range(segments):
        ni = (i + 1) % segments
        try:
            f = bm.faces.new((ring1[i], ring1[ni], ring2[ni], ring2[i]))
            f.material_index = mat_idx
            f.smooth = smooth
            faces.append(f)
        except ValueError:
            pass

    if cap_ends:
        try:
            f_bot = bm.faces.new(list(reversed(ring1)))
            f_bot.material_index = mat_idx
            f_bot.smooth = smooth
            faces.append(f_bot)
        except ValueError:
            pass
        try:
            f_top = bm.faces.new(ring2)
            f_top.material_index = mat_idx
            f_top.smooth = smooth
            faces.append(f_top)
        except ValueError:
            pass
    return faces


# ------------------------------------------------------------------------------------------------
# 1. Bassin Bonsecours Water Basin (Z = -2.20m), Sculpted Île Bonsecours Island & Bridges
# ------------------------------------------------------------------------------------------------

def build_basin_and_ile_bonsecours(col, pal):
    """
    Constructs:
    1. Subdivided wave-displaced 2K PBR water basin at Z = -2.20m covering the entire Bassin Bonsecours
       (H1..H3 North of island, V1..V2 West channel, V7..V8 East basin).
    2. Sculpted Île Bonsecours Island (V3..V6, H3..H8) with stepped granite embankment walls
       (Z = -2.50m .. +0.16m), coping stones, mooring bollards, lush green grass lawns (Z = +0.195m),
       granite curbs (Z = +0.225m), and micro-stepped limestone/gravel walkways (Z = +0.245m .. +0.265m).
    3. Curved East Pedestrian Bridge (H3 V7..V8) and West Pedestrian Bridge + Plaza (H6 V1..V2).
    4. North Stone Quay Promenade (H1) with metal mesh guardrails, plus pedal boats / harbor vessels in the basin.
    """
    # --- A. Dedicated Subdivided Wave-Displaced Water Mesh (Z = -2.20m) ---
    water_mesh = bpy.data.meshes.new("MTL_VM_0024_BassinBonsecours_Water_Mesh")
    water_obj = bpy.data.objects.new("MTL_VM_0024_BassinBonsecours_Water", water_mesh)
    col.objects.link(water_obj)
    water_obj.data.materials.append(pal["water_basin"])

    bm_w = bmesh.new()
    # Create a fine grid over X: 465..805, Y: 325..510 at Z = -2.20m with gentle wave displacement
    nx_steps = 68
    ny_steps = 40
    x_min, x_max = 468.0, 800.0
    y_min, y_max = 328.0, 507.0
    dx = (x_max - x_min) / nx_steps
    dy = (y_max - y_min) / ny_steps

    grid_verts = []
    for iy in range(ny_steps + 1):
        row = []
        y = y_min + iy * dy
        for ix in range(nx_steps + 1):
            x = x_min + ix * dx
            # Subtle 3D wave displacement around Z = -2.20m
            wave_z = -2.20 + 0.035 * math.sin(x * 0.22 + y * 0.15) * math.cos(y * 0.28 - x * 0.12)
            v = bm_w.verts.new((x, y, wave_z))
            row.append(v)
        grid_verts.append(row)

    uv_layer = bm_w.loops.layers.uv.new("UVMap")
    for iy in range(ny_steps):
        for ix in range(nx_steps):
            v1 = grid_verts[iy][ix]
            v2 = grid_verts[iy][ix + 1]
            v3 = grid_verts[iy + 1][ix + 1]
            v4 = grid_verts[iy + 1][ix]
            try:
                f = bm_w.faces.new((v1, v2, v3, v4))
                f.material_index = 0
                f.smooth = True
                for loop in f.loops:
                    co = loop.vert.co
                    loop[uv_layer].uv = ((co.x - x_min) / 40.0, (co.y - y_min) / 40.0)
            except ValueError:
                pass

    bm_w.to_mesh(water_mesh)
    bm_w.free()

    # --- B. Sculpted Île Bonsecours Island, Stepped Quay Walls, Lawns, Walkways & Bridges ---
    isl_mesh = bpy.data.meshes.new("MTL_VM_0024_IleBonsecours_Mesh")
    isl_obj = bpy.data.objects.new("MTL_VM_0024_IleBonsecours", isl_mesh)
    col.objects.link(isl_obj)

    mats = [
        pal["quay_granite"],       # 0: Stepped stone embankment walls (Z = -2.50m .. +0.16m)
        pal["granite_curb"],       # 1: Coping stones & granite curbs (Z = +0.225m)
        pal["grass_lawn"],         # 2: Lush green grass lawns (Z = +0.195m)
        pal["island_plaza"],       # 3: Island limestone plaza & west bridge deck (Z = +0.245m)
        pal["walkway_limestone"],  # 4: Curved limestone walkways (Z = +0.250m)
        pal["walkway_gravel"],     # 5: Crushed-stone / tan gravel paths (Z = +0.255m)
        pal["wheel_apron"],        # 6: Wheel service apron & eastern drive (Z = +0.240m)
        pal["timber_wood"],        # 7: Curved boardwalk & bridge decking (Z = +0.260m)
        pal["white_steel"],        # 8: White amphitheater & bridge structure
        pal["cast_iron"],          # 9: Mooring bollards & railings
    ]
    for m in mats:
        isl_obj.data.materials.append(m)

    bm = bmesh.new()

    # Exact Île Bonsecours Island Perimeter matching satellite_topdown.png (V3..V6, H3..H8)
    island_poly = [
        (643.0, 363.1),
        (559.4, 359.7),
        (555.0, 360.8),
        (550.2, 365.1),
        (548.8, 370.5),
        (551.0, 378.5),
        (563.5, 408.8),
        (555.8, 408.7),
        (555.4, 423.4),
        (569.1, 423.8),
        (588.1, 472.3),
        (639.6, 474.6),
    ]
    island_poly = ensure_ccw(island_poly)

    # 1. Stepped Stone Embankment Retaining Wall around Île Bonsecours (Z = -2.50m .. +0.16m)
    # Lower submerged/waterline step (Z = -2.50m .. -1.10m, outset 0.35m)
    isl_step_low = inset_polygon_2d(island_poly, -0.35)
    add_prism_to_bm(bm, isl_step_low, -2.50, -1.10, mat_side=0, mat_top=0, mat_bottom=None)
    # Upper embankment wall (Z = -1.10m .. +0.16m)
    add_prism_to_bm(bm, island_poly, -1.10, 0.16, mat_side=0, mat_top=0, mat_bottom=None)

    # Projecting Granite Coping Ring around Island Perimeter (Z = +0.16m .. +0.225m)
    isl_inner_curb = inset_polygon_2d(island_poly, 0.65)
    n_isl = len(island_poly)
    for i in range(n_isl):
        ni = (i + 1) % n_isl
        quad_curb = [island_poly[i], island_poly[ni], isl_inner_curb[ni], isl_inner_curb[i]]
        add_prism_to_bm(bm, quad_curb, 0.16, 0.225, mat_side=1, mat_top=1, mat_bottom=None)

    # Cast-iron mooring bollards every 14m along island stone quay edge
    for i in range(n_isl):
        p1 = Vector(island_poly[i])
        p2 = Vector(island_poly[(i + 1) % n_isl])
        seg_len = (p2 - p1).length
        if seg_len >= 10.0:
            num_b = max(1, int(seg_len / 14.0))
            for k in range(num_b):
                bp = p1.lerp(p2, (k + 0.5) / num_b)
                add_cylinder_to_bm(bm, (bp.x, bp.y, 0.225), (bp.x, bp.y, 0.68), 0.14, segments=8, mat_idx=9, smooth=True)
                add_cylinder_to_bm(bm, (bp.x, bp.y, 0.60), (bp.x, bp.y, 0.72), 0.18, segments=8, mat_idx=9, smooth=True)

    # 2. Lush Green Grass Lawn Base covering Île Bonsecours (Z = +0.195m, single-sided +Z top face)
    isl_lawn_poly = inset_polygon_2d(island_poly, 0.55)
    add_top_face_to_bm(bm, isl_lawn_poly, 0.195, mat_top=2)

    # 3. Sculpted Island Plazas, Aprons & Curved Limestone/Gravel Walkways (micro-stepped Z = +0.240m .. +0.265m)
    # A. Wheel & East Service Apron (V5..V6, H4..H8 in satellite_topdown.png: X=598..638.5, Y=370..464)
    wheel_apron_poly = [
        (596.0, 382.0),
        (638.2, 382.0),
        (636.8, 456.0),
        (596.0, 456.0),
    ]
    add_top_face_to_bm(bm, wheel_apron_poly, 0.240, mat_top=6)

    # B. West Central Limestone Plaza & Terrace Court (V3..V5, H5..H7: X=568..612, Y=384..434)
    west_plaza_poly = [
        (569.0, 405.0),
        (606.0, 403.0),
        (606.0, 434.0),
        (572.5, 431.0),
        (568.5, 422.5),
    ]
    add_top_face_to_bm(bm, west_plaza_poly, 0.245, mat_top=3)

    # C. South Plaza around South Entrance Pavilion (V4..V5, H7..H8: X=584..632, Y=366..388)
    south_plaza_poly = [
        (584.0, 366.5),
        (635.0, 368.0),
        (635.0, 385.5),
        (584.0, 385.5),
    ]
    add_top_face_to_bm(bm, south_plaza_poly, 0.246, mat_top=3)

    # D. Curved North-West Diagonal Limestone Walkway (V3..V4, H3..H6: from West Bridge Plaza up to North Tip)
    nw_walkway_pts = [
        (573.2, 416.6),
        (579.0, 431.0),
        (585.5, 447.0),
        (592.2, 463.0),
        (596.5, 466.0),
        (618.7, 466.7),
        (634.0, 466.9),
    ]
    add_polyline_ribbon_top_face(bm, nw_walkway_pts, width=5.4, z_top=0.250, mat_idx=4)

    # E. North-East Oval Gravel Parterre & West Crushed-Stone Parterres (Z = +0.255m, H3..H6, V3..V6)
    ne_oval_poly = [
        (614.0, 456.5),
        (634.5, 456.0),
        (635.5, 463.5),
        (615.0, 464.5),
    ]
    add_top_face_to_bm(bm, ne_oval_poly, 0.255, mat_top=5)
    # Granite curb border around the oval parterre
    add_prism_to_bm(bm, ne_oval_poly, 0.195, 0.225, mat_side=1, mat_top=None, mat_bottom=None)

    # West Lawn Sculpted Crushed-Stone Parterre Strip (visible in H5..H6, V3 of satellite_topdown.png)
    west_gravel_parterre = [
        (563.5, 386.0),
        (576.5, 386.5),
        (582.5, 404.0),
        (571.0, 404.5),
    ]
    add_top_face_to_bm(bm, west_gravel_parterre, 0.255, mat_top=5)
    add_prism_to_bm(bm, west_gravel_parterre, 0.195, 0.225, mat_side=1, mat_top=None, mat_bottom=None)

    # F. South-West Curved Perimeter Walkway (H6..H8, V3..V4, Z = +0.250m)
    sw_walkway_pts = [
        (573.2, 416.6),
        (565.0, 396.0),
        (558.0, 376.0),
        (559.5, 369.5),
        (585.0, 369.2),
    ]
    add_polyline_ribbon_top_face(bm, sw_walkway_pts, width=4.8, z_top=0.250, mat_idx=4)

    # F2. Floating Timber Pedal-Boat Dock Fingers along North-West Cove of Île Bonsecours (X = 548..568, Y = 424..446)
    # Main floating timber spine dock parallel to NW island shoreline
    add_oriented_box(bm, (565.8, 434.8, 0.04), (0.36, 0.93), (-0.93, 0.36), 22.0, 2.2, 0.32, mat_idx=7, include_bottom=True)
    # Gangway bridge from NW island quay edge onto the floating pedal-boat dock
    add_oriented_box(bm, (568.2, 425.2, 0.18), (1.0, 0.0), (0.0, 1.0), 4.5, 1.6, 0.20, mat_idx=8, include_bottom=True)
    # 5 Floating Timber Pedal-Boat Dock Fingers projecting West into the NW cove (X = 548..568, Y = 424..446)
    for fy_idx, fy_dock in enumerate([425.5, 430.0, 434.5, 439.0, 443.5]):
        fx_end = 563.5 + fy_idx * 1.4
        fx_start = 549.0 + fy_idx * 1.0
        f_mid_x = 0.5 * (fx_start + fx_end)
        f_len = fx_end - fx_start
        add_oriented_box(bm, (f_mid_x, fy_dock, 0.04), (1.0, 0.0), (0.0, 1.0), f_len, 1.65, 0.30, mat_idx=7, include_bottom=True)
        # Steel mooring pilings at outer & inner ends of each dock finger
        add_cylinder_to_bm(bm, (fx_start + 0.5, fy_dock, -2.40), (fx_start + 0.5, fy_dock, 0.85), 0.12, segments=8, mat_idx=9)
        add_cylinder_to_bm(bm, (fx_end - 0.4, fy_dock, -2.40), (fx_end - 0.4, fy_dock, 0.85), 0.12, segments=8, mat_idx=9)
        # Moored white pedal boats in the slips between fingers
        if fy_idx < 4:
            pb_x = f_mid_x - 1.2
            pb_y = fy_dock + 2.25
            add_oriented_box(bm, (pb_x, pb_y, -2.06), (1.0, 0.0), (0.0, 1.0), 3.4, 1.75, 0.30, mat_idx=8, include_bottom=True)
            add_oriented_box(bm, (pb_x - 0.2, pb_y, -1.62), (1.0, 0.0), (0.0, 1.0), 1.8, 1.50, 0.10, mat_idx=8, include_bottom=True)

    # G. Circular White Amphitheater / Sun-Dial Seating Feature in West Lawn (H5, V4: X=587.0, Y=427.5)
    amph_cx, amph_cy = 587.0, 427.5
    for step_i, (r_out, z_h) in enumerate([(4.6, 0.32), (3.6, 0.52), (2.6, 0.72)]):
        ring_pts = []
        for a_i in range(16):
            ang = math.radians(-30.0 + 240.0 * a_i / 15.0)
            ring_pts.append((amph_cx + r_out * math.cos(ang), amph_cy + r_out * math.sin(ang)))
        add_polyline_ribbon_top_face(bm, ring_pts, width=0.85, z_top=z_h, mat_idx=8)
        for p in ring_pts[::3]:
            add_cylinder_to_bm(bm, (p[0], p[1], 0.20), (p[0], p[1], z_h), 0.12, segments=6, mat_idx=8)

    # 4. West Pedestrian Bridge & Pier Approach (H6, V1..V3 in satellite_topdown.png)
    # Wide rectangular stone/concrete pier abutment on West side of island (X=555.5..573.5, Y=408.7..423.8)
    west_pier_abutment = [
        (555.8, 408.7),
        (572.0, 409.2),
        (572.0, 423.8),
        (555.4, 423.4),
    ]
    add_top_face_to_bm(bm, west_pier_abutment, 0.248, mat_top=3)
    # Tan landscaped planter beds flanking the west pier approach (visible in H6 V2)
    for py_bed in [411.2, 421.2]:
        add_oriented_box(bm, (563.5, py_bed, 0.26), (1.0, 0.0), (0.0, 1.0), 14.0, 3.2, 0.12, mat_idx=5)

    # Narrow West Pedestrian Bridge spanning West channel (X=518.0..556.0, Y=415.0..417.5)
    wb_p1 = Vector((501.0, 414.2, 0.30))
    wb_p2 = Vector((556.5, 416.2, 0.30))
    wb_dir = (wb_p2 - wb_p1).normalized()
    wb_norm = Vector((-wb_dir.y, wb_dir.x, 0.0))
    wb_len = (wb_p2 - wb_p1).length
    add_oriented_box(bm, (wb_p1 + wb_p2) * 0.5, (wb_dir.x, wb_dir.y), (wb_norm.x, wb_norm.y), wb_len, 4.4, 0.28, mat_idx=3, include_bottom=True)
    # Bridge guardrails (+1.10m) and support piers into water
    for side in [-2.05, 2.05]:
        add_oriented_box(bm, (wb_p1 + wb_p2) * 0.5 + wb_norm * side + Vector((0, 0, 0.65)), (wb_dir.x, wb_dir.y), (wb_norm.x, wb_norm.y), wb_len, 0.10, 1.05, mat_idx=9)
    for k in range(1, 5):
        p_pier = wb_p1.lerp(wb_p2, k / 5.0)
        add_oriented_box(bm, (p_pier.x, p_pier.y, -1.10), (wb_dir.x, wb_dir.y), (wb_norm.x, wb_norm.y), 1.4, 4.8, 2.60, mat_idx=0)

    # 5. Curved East Pedestrian Bridge (H3..H4, V7..V8 in satellite_topdown.png)
    # Sweeping curved bridge from NE corner of Île Bonsecours (X=638.5, Y=467.2) across East water basin to East Quay (X=682.5, Y=455.5)
    east_bridge_pts = [
        (638.0, 467.1),
        (648.0, 467.8),
        (657.0, 467.5),
        (665.5, 465.8),
        (673.5, 462.2),
        (681.5, 456.2),
    ]
    for i in range(len(east_bridge_pts) - 1):
        ep1 = Vector((east_bridge_pts[i][0], east_bridge_pts[i][1], 0.32))
        ep2 = Vector((east_bridge_pts[i + 1][0], east_bridge_pts[i + 1][1], 0.32))
        e_vec = (ep2 - ep1).normalized()
        e_norm = Vector((-e_vec.y, e_vec.x, 0.0))
        e_len = (ep2 - ep1).length + 0.35
        # Light limestone/timber bridge deck
        add_oriented_box(bm, (ep1 + ep2) * 0.5, (e_vec.x, e_vec.y), (e_norm.x, e_norm.y), e_len, 5.2, 0.30, mat_idx=4, include_bottom=True)
        # Outer white structural steel arch/fascia ribs
        for side in [-2.5, 2.5]:
            add_oriented_box(bm, (ep1 + ep2) * 0.5 + e_norm * side, (e_vec.x, e_vec.y), (e_norm.x, e_norm.y), e_len, 0.25, 0.45, mat_idx=8, include_bottom=True)
            add_oriented_box(bm, (ep1 + ep2) * 0.5 + e_norm * side + Vector((0, 0, 0.68)), (e_vec.x, e_vec.y), (e_norm.x, e_norm.y), e_len, 0.10, 1.05, mat_idx=9)
        # Support pilings in the water
        mid_p = (ep1 + ep2) * 0.5
        for side in [-1.8, 1.8]:
            sp = mid_p + e_norm * side
            add_cylinder_to_bm(bm, (sp.x, sp.y, -2.50), (sp.x, sp.y, 0.30), 0.22, segments=8, mat_idx=0)

    # Small north dock spur on the curved East bridge (visible at H3 V8 in satellite_topdown.png: X=662.5, Y=467.5..472.5)
    add_oriented_box(bm, (662.2, 470.2, 0.30), (0.0, 1.0), (1.0, 0.0), 5.5, 2.4, 0.25, mat_idx=7, include_bottom=True)

    # 6. North Stone Quay Promenade (H1 across V1..V8 in satellite_topdown.png: Y = 497.5 .. 508.5)
    # Plus Camera 2 (Bassin_Bonsecours_North_Boardwalk at X=530.66, Y=492.04, heading 150 deg looking SSE) foreground quay edge!
    north_quay_edge = [
        (500.0, 412.0),
        (529.2, 488.5),
        (534.5, 497.2),
        (537.5, 498.7),
        (724.4, 505.4),
        (788.5, 507.6),
    ]
    for i in range(len(north_quay_edge) - 1):
        nq1 = Vector((north_quay_edge[i][0], north_quay_edge[i][1], 0.0))
        nq2 = Vector((north_quay_edge[i + 1][0], north_quay_edge[i + 1][1], 0.0))
        nq_vec = (nq2 - nq1).normalized()
        nq_norm = Vector((-nq_vec.y, nq_vec.x, 0.0))  # Points North/West onto land
        nq_len = (nq2 - nq1).length
        mid_q = (nq1 + nq2) * 0.5
        # Granite retaining wall Z = -2.50m .. +0.18m
        w_center = mid_q + nq_norm * 0.60
        add_oriented_box(bm, (w_center.x, w_center.y, -1.16), (nq_vec.x, nq_vec.y), (nq_norm.x, nq_norm.y), nq_len, 1.20, 2.68, mat_idx=0)
        # Wide granite coping stone Z = +0.18m .. +0.26m
        c_center = mid_q + nq_norm * 0.65
        add_oriented_box(bm, (c_center.x, c_center.y, 0.22), (nq_vec.x, nq_vec.y), (nq_norm.x, nq_norm.y), nq_len, 1.40, 0.08, mat_idx=1)

        # Ornate Metal Waterfront Guardrail with Wire-Mesh Panels & Stanchions every 2.0m (Cam 2 foreground H5..H8 V1..V8!)
        r_center = mid_q + nq_norm * 0.25
        # Top, mid, and bottom horizontal rail bars
        add_oriented_box(bm, (r_center.x, r_center.y, 1.18), (nq_vec.x, nq_vec.y), (nq_norm.x, nq_norm.y), nq_len, 0.07, 0.06, mat_idx=9)
        add_oriented_box(bm, (r_center.x, r_center.y, 0.96), (nq_vec.x, nq_vec.y), (nq_norm.x, nq_norm.y), nq_len, 0.04, 0.04, mat_idx=9)
        add_oriented_box(bm, (r_center.x, r_center.y, 0.34), (nq_vec.x, nq_vec.y), (nq_norm.x, nq_norm.y), nq_len, 0.05, 0.05, mat_idx=9)
        # Vertical wire-mesh pickets every 0.35m for rich edge detail in Cam 2 foreground
        num_pickets = max(4, int(nq_len / 0.35))
        for pk_i in range(num_pickets + 1):
            pk_p = nq1.lerp(nq2, pk_i / num_pickets) + nq_norm * 0.25
            add_oriented_box(bm, (pk_p.x, pk_p.y, 0.65), (nq_vec.x, nq_vec.y), (nq_norm.x, nq_norm.y), 0.018, 0.018, 0.62, mat_idx=9)
        num_posts = max(2, int(nq_len / 2.0))
        for p_idx in range(num_posts + 1):
            pp = nq1.lerp(nq2, p_idx / num_posts) + nq_norm * 0.25
            add_oriented_box(bm, (pp.x, pp.y, 0.72), (nq_vec.x, nq_vec.y), (nq_norm.x, nq_norm.y), 0.10, 0.10, 1.00, mat_idx=9)

    # Wide light-stone / paver North Quay Promenade along south side of Hangar 16 (H1: Y = 498.5 .. 508.5)
    north_prom_poly = [
        (528.0, 498.2),
        (735.0, 505.5),
        (735.0, 514.5),
        (528.0, 507.2),
    ]
    add_top_face_to_bm(bm, north_prom_poly, 0.240, mat_top=4)

    # Green lawn strip at North-East corner of H1 (V7..V8 in satellite_topdown.png: X=654..720, Y=508..522)
    ne_quay_lawn = [
        (654.2, 508.2),
        (718.0, 510.5),
        (718.0, 524.0),
        (654.2, 522.0),
    ]
    add_top_face_to_bm(bm, ne_quay_lawn, 0.252, mat_top=2)

    # 7. East Shore & Terrasses Bonsecours Peninsula (X = 660..795, Y = 335..505)
    east_peninsula_poly = [
        (658.0, 363.5),
        (761.7, 367.4),
        (773.7, 425.5),
        (788.5, 503.3),
        (728.4, 500.1),
        (682.7, 464.2),
        (675.8, 457.8),
        (685.7, 442.9),
        (689.8, 428.3),
        (690.4, 419.0),
        (688.4, 403.3),
        (681.9, 388.4),
        (672.0, 377.7),
        (659.6, 373.2),
    ]
    east_peninsula_poly = ensure_ccw(east_peninsula_poly)
    add_prism_to_bm(bm, east_peninsula_poly, -2.50, 0.16, mat_side=0, mat_top=0, mat_bottom=None)
    add_top_face_to_bm(bm, inset_polygon_2d(east_peninsula_poly, 0.45), 0.195, mat_top=2)
    # East shore curved walkway
    east_walk_pts = [
        (681.5, 456.2),
        (687.5, 447.4),
        (692.7, 430.9),
        (693.8, 417.8),
        (693.2, 405.8),
        (689.8, 393.5),
        (683.3, 381.9),
        (659.3, 370.1),
    ]
    add_polyline_ribbon_top_face(bm, east_walk_pts, width=4.5, z_top=0.250, mat_idx=4)

    # South-East Bridge connecting Island to East Shore (X=638.5..659.3, Y=370.2)
    add_oriented_box(bm, (648.9, 370.3, 0.30), (1.0, 0.0), (0.0, 1.0), 21.5, 4.2, 0.28, mat_idx=7, include_bottom=True)

    # 8. Harbor Vessels / Pedal Boats in Bassin Bonsecours (for realistic waterfront reflections & edges)
    boat_coords = [
        (560.0, 482.0, 25.0),
        (595.0, 486.0, -15.0),
        (635.0, 485.0, 10.0),
        (662.0, 435.0, 80.0),
        (535.0, 445.0, -70.0),
    ]
    for bx, by, brot in boat_coords:
        ang = math.radians(brot)
        b_dir = (math.cos(ang), math.sin(ang))
        b_norm = (-math.sin(ang), math.cos(ang))
        # White catamaran pontoons & canopy
        add_oriented_box(bm, (bx, by, -2.08), b_dir, b_norm, 3.8, 2.1, 0.32, mat_idx=8, include_bottom=True)
        add_oriented_box(bm, (bx - b_dir[0] * 0.3, by - b_dir[1] * 0.3, -1.55), b_dir, b_norm, 2.2, 1.8, 0.12, mat_idx=8, include_bottom=True)

    bm.to_mesh(isl_mesh)
    bm.free()
    print("Constructed Bassin Bonsecours 2K PBR Water (Z = -2.20m) & Sculpted Île Bonsecours Island")
    return water_obj, isl_obj


# ------------------------------------------------------------------------------------------------
# 2. La Grande Roue de Montréal (60m White Steel Ferris Wheel at V4..V5, H4..H7)
# ------------------------------------------------------------------------------------------------

def build_la_grande_roue(col, pal):
    """
    Constructs high-detail 60m white structural steel La Grande Roue de Montréal
    at its exact island coordinates (X=621.76, Y=419.00, spanning V4..V5, H4..H7 in satellite_topdown.png):
    - 42 glazed climate-controlled passenger gondolas
    - 4 heavy white tubular steel A-frame support legs + cross-bracing
    - Dual parallel circular rim trusses with dense Warren lacing, hub spindle flanges, and tension spokes
    """
    mesh = bpy.data.meshes.new("MTL_VM_0024_LaGrandeRoue_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0024_LaGrandeRoue", mesh)
    col.objects.link(obj)

    mats = [
        pal["white_steel"],     # 0: Pristine white enamel structural steel
        pal["glass_dark"],      # 1: Panoramic tinted reflective observation glass
        pal["sandstone_pbr"],   # 2: Concrete foundation pedestals and boarding deck
        pal["cast_iron"],       # 3: Axle bearings and turnstiles
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    cx, cy = 621.76, 419.00
    angle_deg = -2.10
    ang_rad = math.radians(angle_deg)
    tx = math.sin(ang_rad)
    ty = math.cos(ang_rad)
    v_tangent = Vector((tx, ty, 0.0))  # North-South rotation plane
    v_axle = Vector((math.cos(ang_rad), -math.sin(ang_rad), 0.0))  # East-West axle
    v_up = Vector((0.0, 0.0, 1.0))

    hub_z = 32.50
    center_hub = Vector((cx, cy, hub_z))

    # 1. Concrete Foundation Pedestals (Z = 0.20m .. 1.40m)
    for px_off in [-5.2, 5.2]:
        for py_off in [-17.0, 17.0]:
            ped_pos = center_hub + v_axle * px_off + v_tangent * py_off
            ped_pos.z = 0.80
            add_oriented_box(bm, ped_pos, (v_tangent.x, v_tangent.y), (v_axle.x, v_axle.y), 3.4, 3.4, 1.25, mat_idx=2)

    # 2. Four Massive White Tubular Steel A-Frame Support Legs + West Tension Stays (visible in satellite_topdown.png!)
    leg_rad = 0.65
    for side, px_top, px_bot in [(-1, -3.4, -5.2), (1, 3.4, 5.2)]:
        p_top = center_hub + v_axle * px_top
        for py_bot in [-17.0, 17.0]:
            p_bot = center_hub + v_axle * px_bot + v_tangent * py_bot
            p_bot.z = 1.35
            add_cylinder_to_bm(bm, p_bot, p_top, leg_rad, segments=12, mat_idx=0, smooth=True)

    # Prominent angled white steel A-frame stay struts extending West into the plaza (visible at H4..H7 V4..V5 in satellite_topdown.png!)
    for py_stay in [-22.5, 19.5]:
        p_stay_bot = Vector((cx - 19.5, cy + py_stay, 0.35))
        p_stay_top = center_hub - v_axle * 3.6
        add_cylinder_to_bm(bm, p_stay_bot, p_stay_top, 0.55, segments=12, mat_idx=0, smooth=True)
        # Anchor block
        add_oriented_box(bm, (p_stay_bot.x, p_stay_bot.y, 0.65), (1.0, 0.0), (0.0, 1.0), 2.8, 2.8, 0.90, mat_idx=2)

    # Tie beams and cross-bracing between legs
    for z_beam in [12.0, 22.0]:
        fac = 1.0 - z_beam / 32.5
        for side_x in [-1.0, 1.0]:
            xb = side_x * (3.4 + 1.8 * fac)
            p_s = center_hub + v_axle * xb - v_tangent * (17.0 * fac)
            p_s.z = z_beam
            p_n = center_hub + v_axle * xb + v_tangent * (17.0 * fac)
            p_n.z = z_beam
            add_cylinder_to_bm(bm, p_s, p_n, 0.36, segments=8, mat_idx=0, smooth=True)

    # 3. Central Hub / Spindle Axle & Flanges
    add_cylinder_to_bm(bm, center_hub - v_axle * 4.0, center_hub + v_axle * 4.0, 1.25, segments=16, mat_idx=0, smooth=True)
    for px_flange in [-2.4, 2.4]:
        add_cylinder_to_bm(
            bm,
            center_hub + v_axle * (px_flange - 0.25),
            center_hub + v_axle * (px_flange + 0.25),
            2.45,
            segments=16,
            mat_idx=0,
            smooth=True,
        )

    # 4. Dual Outer and Inner Wheel Rim Trusses (42 Node Segments)
    num_rim_nodes = 42
    r_outer = 28.2
    r_inner = 25.4
    r_mid = 18.2

    wheel_nodes_w_out, wheel_nodes_e_out = [], []
    wheel_nodes_w_in, wheel_nodes_e_in = [], []
    wheel_nodes_w_mid, wheel_nodes_e_mid = [], []

    for i in range(num_rim_nodes):
        theta = 2.0 * math.pi * i / num_rim_nodes
        v_rad = v_tangent * math.sin(theta) + v_up * math.cos(theta)
        wheel_nodes_w_out.append(center_hub - v_axle * 1.45 + v_rad * r_outer)
        wheel_nodes_w_in.append(center_hub - v_axle * 1.45 + v_rad * r_inner)
        wheel_nodes_w_mid.append(center_hub - v_axle * 1.45 + v_rad * r_mid)

        wheel_nodes_e_out.append(center_hub + v_axle * 1.45 + v_rad * r_outer)
        wheel_nodes_e_in.append(center_hub + v_axle * 1.45 + v_rad * r_inner)
        wheel_nodes_e_mid.append(center_hub + v_axle * 1.45 + v_rad * r_mid)

    rim_pipe_rad = 0.22
    brace_rad = 0.12
    for i in range(num_rim_nodes):
        ni = (i + 1) % num_rim_nodes
        add_cylinder_to_bm(bm, wheel_nodes_w_out[i], wheel_nodes_w_out[ni], rim_pipe_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_e_out[i], wheel_nodes_e_out[ni], rim_pipe_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_w_in[i], wheel_nodes_w_in[ni], rim_pipe_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_e_in[i], wheel_nodes_e_in[ni], rim_pipe_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_w_mid[i], wheel_nodes_w_mid[ni], brace_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_e_mid[i], wheel_nodes_e_mid[ni], brace_rad, segments=6, mat_idx=0, smooth=True)

        # Radial & Warren truss diagonal lacing
        add_cylinder_to_bm(bm, wheel_nodes_w_in[i], wheel_nodes_w_out[i], brace_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_e_in[i], wheel_nodes_e_out[i], brace_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_w_in[i], wheel_nodes_w_out[ni], brace_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_e_in[i], wheel_nodes_e_out[ni], brace_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_w_out[i], wheel_nodes_e_out[i], brace_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_w_in[i], wheel_nodes_e_in[i], brace_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, wheel_nodes_w_out[i], wheel_nodes_e_in[ni], brace_rad * 0.85, segments=6, mat_idx=0, smooth=True)

    # 5. Radial Tension Spokes (42 pairs)
    spoke_rad = 0.09
    for s_idx in range(num_rim_nodes):
        s_theta = 2.0 * math.pi * s_idx / num_rim_nodes
        v_s_rad = v_tangent * math.sin(s_theta) + v_up * math.cos(s_theta)
        p_flange_w = center_hub - v_axle * 2.40 + v_s_rad * 2.10
        p_flange_e = center_hub + v_axle * 2.40 + v_s_rad * 2.10
        add_cylinder_to_bm(bm, p_flange_w, wheel_nodes_w_in[s_idx], spoke_rad, segments=6, mat_idx=0, smooth=True)
        add_cylinder_to_bm(bm, p_flange_e, wheel_nodes_e_in[s_idx], spoke_rad, segments=6, mat_idx=0, smooth=True)

    # 6. 42 Climate-Controlled Glazed Passenger Gondolas
    for g_idx in range(num_rim_nodes):
        p_pivot = (wheel_nodes_w_out[g_idx] + wheel_nodes_e_out[g_idx]) * 0.5
        p_gondola_roof = p_pivot - Vector((0.0, 0.0, 1.35))
        add_cylinder_to_bm(bm, p_pivot, p_gondola_roof, 0.09, segments=6, mat_idx=0, smooth=True)

        p_cabin_center = p_gondola_roof - Vector((0.0, 0.0, 1.05))
        p_floor = p_cabin_center - Vector((0.0, 0.0, 0.82))
        add_oriented_box(bm, (p_floor.x, p_floor.y, p_floor.z), (v_tangent.x, v_tangent.y), (v_axle.x, v_axle.y), 2.30, 1.95, 0.45, mat_idx=0, smooth=True, include_bottom=True)
        add_oriented_box(bm, (p_cabin_center.x, p_cabin_center.y, p_cabin_center.z), (v_tangent.x, v_tangent.y), (v_axle.x, v_axle.y), 2.20, 1.85, 1.25, mat_idx=1, smooth=False, include_bottom=True)
        p_roof = p_cabin_center + Vector((0.0, 0.0, 0.82))
        add_oriented_box(bm, (p_roof.x, p_roof.y, p_roof.z), (v_tangent.x, v_tangent.y), (v_axle.x, v_axle.y), 2.30, 1.95, 0.45, mat_idx=0, smooth=True, include_bottom=True)

    # 7. Boarding Platform & Queue Canopy at Wheel Base
    add_oriented_box(bm, (cx, cy, 0.85), (v_tangent.x, v_tangent.y), (v_axle.x, v_axle.y), 26.0, 10.5, 1.25, mat_idx=2)

    bm.to_mesh(mesh)
    bm.free()
    print("Constructed La Grande Roue de Montréal (60m Structural Steel Observation Wheel)")
    return obj


# ------------------------------------------------------------------------------------------------
# 3. Pavillon du Bassin Bonsecours (1097403709) & South Bistro / Ticket Pavilions (1097403706)
# ------------------------------------------------------------------------------------------------

def build_island_pavilions(dossier, col, pal):
    """
    Constructs the buildings on Île Bonsecours matching satellite_topdown.png (V3..V5, H4..H8):
    1. Pavillon du Bassin Bonsecours (North Pavilion, H4..H5, V4..V5: X=592..618, Y=432..448.5)
       with dark charcoal flat roof (matching satellite H4..H5 V4) + twin white square canopies at (605, 426).
    2. South Bistro & Ticketing Pavilions (1097403706, H6..H8, V4..V5: X=586..626.6, Y=382.5..403.8)
       with white flat roofs, glazed curtain walls, and patio umbrellas on the west terrace.
    3. Ticket Kiosk (1180387344).
    """
    mesh = bpy.data.meshes.new("MTL_VM_0024_IslandPavilions_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0024_IslandPavilions", mesh)
    col.objects.link(obj)

    mats = [
        pal["sandstone_pbr"],   # 0: Limestone/concrete walls & plinth
        pal["roof_dark_pbr"],   # 1: Dark flat roof membrane (Pavillon du Bassin Bonsecours H4..H5)
        pal["white_steel"],     # 2: White roofs, canopies & mullions (South Bistro & canopies)
        pal["glass_dark"],      # 3: Recessed panoramic glass curtain walls
        pal["timber_wood"],     # 4: Timber accents & patio furniture
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Pavillon du Bassin Bonsecours (North Building 1097403709, H4..H5 V4..V5 in satellite_topdown.png)
    # In satellite_topdown.png, the dark L-shaped roof spans X=584.0..618.5, Y=432.0..448.5
    north_coords = [
        (617.8, 448.5),
        (618.0, 440.5),
        (614.6, 432.1),
        (600.2, 431.9),
        (600.0, 438.4),
        (584.2, 438.0),
        (584.0, 448.1),
    ]
    add_prism_to_bm(bm, north_coords, 0.24, 0.72, mat_side=0, mat_top=0, mat_bottom=None)
    # Deepened window bay recess (>= 0.52m recess behind outer piers & parapet)
    north_inset = inset_polygon_2d(north_coords, 0.54)
    add_prism_to_bm(bm, north_inset, 0.72, 5.40, mat_side=3, mat_top=1, mat_bottom=None)
    # Articulated stone corner piers and projecting vertical aluminum curtain-wall mullions every 2.2m
    n_nc = len(north_coords)
    for i in range(n_nc):
        p1 = Vector(north_coords[i])
        p2 = Vector(north_coords[(i + 1) % n_nc])
        add_oriented_box(bm, (p1.x, p1.y, 3.06), (1.0, 0.0), (0.0, 1.0), 0.58, 0.58, 4.68, mat_idx=0)
        seg_vec = p2 - p1
        seg_len = seg_vec.length
        if seg_len >= 2.2:
            s_dir = (seg_vec.x / seg_len, seg_vec.y / seg_len)
            s_norm = (-s_dir[1], s_dir[0])
            # Horizontal projecting aluminum transom bar at Z = 3.25m & window sill at Z = 0.72m
            mid_e = (p1 + p2) * 0.5
            add_oriented_box(bm, (mid_e.x, mid_e.y, 3.25), s_dir, s_norm, seg_len, 0.52, 0.14, mat_idx=2)
            add_oriented_box(bm, (mid_e.x, mid_e.y, 0.74), s_dir, s_norm, seg_len, 0.56, 0.12, mat_idx=0)
            num_mul = max(1, int(seg_len / 2.2))
            for m_i in range(1, num_mul):
                mp = p1.lerp(p2, m_i / num_mul)
                add_oriented_box(bm, (mp.x, mp.y, 3.06), s_dir, s_norm, 0.14, 0.52, 4.68, mat_idx=2)
    # Parapet wall (Z = 5.40m .. 5.85m, ring only) and Dark Flat Roof (Z = 5.88m, inset 0.30m) matching H4..H5 V4!
    add_prism_to_bm(bm, north_coords, 5.40, 5.85, mat_side=0, mat_top=1, mat_bottom=None)
    north_roof = inset_polygon_2d(north_coords, 0.30)
    add_top_face_to_bm(bm, north_roof, 5.88, mat_top=1)
    # Rooftop HVAC Units & Skylight Curbs on Pavillon du Bassin Bonsecours (1097403709)
    for hx_c, hy_c, hw_x, hw_y, hh_z, h_mat in [
        (591.5, 443.2, 3.2, 2.4, 0.68, 2),
        (606.5, 443.5, 3.6, 2.6, 0.75, 2),
        (608.0, 436.2, 2.8, 2.2, 0.55, 3),
    ]:
        add_oriented_box(bm, (hx_c, hy_c, 5.88 + hh_z * 0.5), (1.0, 0.0), (0.0, 1.0), hw_x, hw_y, hh_z, mat_idx=h_mat, include_bottom=True)
        add_oriented_box(bm, (hx_c, hy_c, 5.96), (1.0, 0.0), (0.0, 1.0), hw_x + 0.3, hw_y + 0.3, 0.16, mat_idx=0)

    # Twin White Square Canopies immediately south of Pavillon du Bassin Bonsecours (visible at H5 V4..V5: X=601..613, Y=421..429)
    for cx_can in [602.5, 609.5]:
        add_oriented_box(bm, (cx_can, 425.2, 4.30), (1.0, 0.0), (0.0, 1.0), 6.4, 7.2, 0.28, mat_idx=2, include_bottom=True)
        for dx in [-2.8, 2.8]:
            for dy in [-3.2, 3.2]:
                add_cylinder_to_bm(bm, (cx_can + dx, 425.2 + dy, 0.24), (cx_can + dx, 425.2 + dy, 4.25), 0.12, segments=6, mat_idx=2)

    # 2. South Entrance, Bistro & Ticketing Pavilions (1097403706, H6..H8 V4..V5 in satellite_topdown.png)
    # Bright white roofs in L-shape: West wing (X=586.3..599.6, Y=382.6..403.8) and South-East wing (X=599.6..626.6, Y=385.1..397.4)
    bldg_south = next((b for b in dossier["osm_features"]["buildings"] if b["id"] == 1097403706), None)
    if bldg_south:
        south_coords = bldg_south["coords_xy"]
        add_prism_to_bm(bm, south_coords, 0.24, 0.68, mat_side=0, mat_top=0, mat_bottom=None)
        # Deepened window bay recess (>= 0.52m recess behind outer piers & roof overhang)
        south_inset = inset_polygon_2d(south_coords, 0.54)
        add_prism_to_bm(bm, south_inset, 0.68, 5.50, mat_side=3, mat_top=2, mat_bottom=None)
        n_sc = len(south_coords)
        for i in range(n_sc):
            p1 = Vector(south_coords[i])
            p2 = Vector(south_coords[(i + 1) % n_sc])
            add_cylinder_to_bm(bm, (p1.x, p1.y, 0.68), (p1.x, p1.y, 5.50), 0.18, segments=8, mat_idx=2)
            seg_vec = p2 - p1
            seg_len = seg_vec.length
            if seg_len >= 2.2:
                s_dir = (seg_vec.x / seg_len, seg_vec.y / seg_len)
                s_norm = (-s_dir[1], s_dir[0])
                mid_e = (p1 + p2) * 0.5
                add_oriented_box(bm, (mid_e.x, mid_e.y, 3.30), s_dir, s_norm, seg_len, 0.52, 0.14, mat_idx=2)
                num_mul = max(1, int(seg_len / 2.2))
                for m_i in range(1, num_mul):
                    mp = p1.lerp(p2, m_i / num_mul)
                    add_oriented_box(bm, (mp.x, mp.y, 3.09), s_dir, s_norm, 0.14, 0.52, 4.82, mat_idx=2)
        # Bright White Parapet & Roof Canopy (Z = 5.50m .. 5.95m) matching satellite_topdown.png H7 V4..V5
        add_prism_to_bm(bm, south_coords, 5.50, 5.95, mat_side=2, mat_top=2, mat_bottom=None)
        # Rooftop HVAC Units & Skylight Curbs on South Bistro Pavilion (1097403706, visible at H7 V4 in satellite_topdown.png!)
        for sx_c, sy_c, sw_x, sw_y, sh_z in [
            (592.5, 396.2, 2.6, 2.2, 0.65),
            (592.8, 389.5, 2.4, 2.0, 0.60),
            (612.0, 391.2, 3.4, 2.2, 0.65),
        ]:
            add_oriented_box(bm, (sx_c, sy_c, 5.95 + sh_z * 0.5), (1.0, 0.0), (0.0, 1.0), sw_x, sw_y, sh_z, mat_idx=0, include_bottom=True)
            add_oriented_box(bm, (sx_c, sy_c, 6.02), (1.0, 0.0), (0.0, 1.0), sw_x + 0.25, sw_y + 0.25, 0.14, mat_idx=2)

    # White Patio Umbrellas in the Bistro Courtyard (visible at H6..H7 V4 in satellite_topdown.png: X=588..596, Y=405..416)
    umbrella_coords = [
        (589.5, 407.5),
        (594.0, 408.5),
        (589.5, 413.0),
        (594.2, 414.0),
    ]
    for ux, uy in umbrella_coords:
        add_cylinder_to_bm(bm, (ux, uy, 0.25), (ux, uy, 3.10), 0.08, segments=6, mat_idx=2)
        add_cylinder_to_bm(bm, (ux, uy, 2.85), (ux, uy, 3.25), 1.85, segments=8, mat_idx=2)
        add_oriented_box(bm, (ux, uy, 0.65), (1.0, 0.0), (0.0, 1.0), 1.4, 1.4, 0.75, mat_idx=4)

    bm.to_mesh(mesh)
    bm.free()
    print("Constructed Pavillon du Bassin Bonsecours & South Bistro Pavilions on Île Bonsecours")
    return obj


# ------------------------------------------------------------------------------------------------
# 4. Hangar 16 (46866827), Terrasses Bonsecours (46866826) & Zipline Towers
# ------------------------------------------------------------------------------------------------

def build_hangar_16(bldg, col, pal):
    """
    Constructs Hangar 16 (46866827) matching BOTH satellite_topdown.png (H1, V2..V7) AND
    Street View Camera 1 (Grande_Roue_Southwest_Waterfront) & Camera 4 (Ile_Bonsecours_Pavilion_Approach):
    - Weathered pale grey-white industrial masonry/concrete facade (matching real Street View H4..H5)
    - Flat/low-slope dark industrial roof with parapet, rhythmic structural pilasters, recessed dark industrial windows,
      and blue ticket kiosks at the southwest corner!
    """
    coords = bldg.get("coords_xy", [])
    if len(coords) < 3:
        return None

    mesh = bpy.data.meshes.new("MTL_VM_0024_Hangar16_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0024_Hangar16", mesh)
    col.objects.link(obj)

    mats = [
        pal["quay_granite"],          # 0: Stone/concrete base plinth
        pal["weathered_hangar_wall"], # 1: Weathered pale grey industrial facade (matches Street View & Satellite H1)
        pal["roof_dark_pbr"],         # 2: Dark industrial flat roof membrane (matches Satellite H1)
        pal["glass_dark"],            # 3: Deeply recessed industrial window bays
        pal["cast_iron"],             # 4: Structural steel pilasters, cornice & doors
        pal["kiosk_blue"],            # 5: Blue ticket kiosks outside Hangar 16 (matches Cam 1 & Cam 4)
        pal["zipline_red"],           # 6: Red café umbrellas along south terrace (visible in Satellite H1 V3)
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    min_x = min(p[0] for p in coords)
    max_x = max(p[0] for p in coords)
    min_y = min(p[1] for p in coords)
    max_y = max(p[1] for p in coords)

    # 1. Foundation Plinth (Z = 0.00m .. 0.90m)
    add_prism_to_bm(bm, coords, 0.00, 0.90, mat_side=0, mat_top=0, mat_bottom=None)

    # 2. Main Weathered Grey Industrial Warehouse Body (Z = 0.90m .. 7.80m)
    inset_body = inset_polygon_2d(coords, 0.25)
    add_prism_to_bm(bm, inset_body, 0.90, 7.80, mat_side=1, mat_top=1, mat_bottom=None)

    # 3. Structural Parapet & Dark Industrial Flat Roof (Z = 7.80m .. 8.35m, roof inset at Z = 8.22m)
    # Matches the flat grey roof in satellite_topdown.png H1 AND the horizontal roofline in Cam 1 so La Grande Roue crown rises above it!
    add_prism_to_bm(bm, coords, 7.80, 8.35, mat_side=1, mat_top=4, mat_bottom=None)
    roof_inset = inset_polygon_2d(coords, 0.45)
    add_top_face_to_bm(bm, roof_inset, 8.22, mat_top=2)

    # 4. Rhythmic Vertical Pilasters, Recessed Industrial Loading Bay Doors, Exterior Steel Lintels & Bollards
    #    along North, South, and West Facades of Hangar 16 (46866827)
    for wx in range(int(min_x + 6), int(max_x - 4), 6):
        # Pilasters (projecting 0.52m outside the recessed bays)
        add_oriented_box(bm, (wx - 3.0, min_y + 0.18, 4.35), (1.0, 0.0), (0.0, 1.0), 0.52, 0.55, 6.90, mat_idx=1)
        add_oriented_box(bm, (wx - 3.0, max_y - 0.18, 4.35), (1.0, 0.0), (0.0, 1.0), 0.52, 0.55, 6.90, mat_idx=1)
        # Upper industrial clerestory window bays (recessed >= 0.48m)
        add_oriented_box(bm, (wx, min_y + 0.52, 5.90), (1.0, 0.0), (0.0, 1.0), 3.2, 0.18, 1.8, mat_idx=3)
        add_oriented_box(bm, (wx, max_y - 0.52, 5.90), (1.0, 0.0), (0.0, 1.0), 3.2, 0.18, 1.8, mat_idx=3)
        # Exterior projecting steel lintels above upper & lower bays (Z = 6.88m and Z = 3.92m)
        add_oriented_box(bm, (wx, min_y + 0.08, 6.88), (1.0, 0.0), (0.0, 1.0), 3.6, 0.42, 0.22, mat_idx=4, include_bottom=True)
        add_oriented_box(bm, (wx, min_y + 0.08, 3.92), (1.0, 0.0), (0.0, 1.0), 3.8, 0.48, 0.26, mat_idx=4, include_bottom=True)
        add_oriented_box(bm, (wx, max_y - 0.08, 6.88), (1.0, 0.0), (0.0, 1.0), 3.6, 0.42, 0.22, mat_idx=4, include_bottom=True)
        add_oriented_box(bm, (wx, max_y - 0.08, 3.92), (1.0, 0.0), (0.0, 1.0), 3.8, 0.48, 0.26, mat_idx=4, include_bottom=True)
        # Recessed Ground-Floor Industrial Loading Bay Doors along South & North Facades (0.55m recess, Z = 0.90m .. 3.80m)
        add_oriented_box(bm, (wx, min_y + 0.55, 2.35), (1.0, 0.0), (0.0, 1.0), 3.4, 0.16, 2.90, mat_idx=4)
        add_oriented_box(bm, (wx, max_y - 0.55, 2.35), (1.0, 0.0), (0.0, 1.0), 3.4, 0.16, 2.90, mat_idx=3)
        # Jamb reveal frames & horizontal sectional loading door ribs on South facade
        for jx_off in (-1.75, 1.75):
            add_oriented_box(bm, (wx + jx_off, min_y + 0.26, 2.35), (1.0, 0.0), (0.0, 1.0), 0.18, 0.55, 2.90, mat_idx=0)
        for rz_door in (1.45, 2.05, 2.65, 3.25):
            add_oriented_box(bm, (wx, min_y + 0.44, rz_door), (1.0, 0.0), (0.0, 1.0), 3.3, 0.10, 0.08, mat_idx=0)
        # Protective Bollards along South Facade of Hangar 16
        if wx % 12 == 0:
            add_cylinder_to_bm(bm, (wx - 1.6, min_y - 0.65, 0.20), (wx - 1.6, min_y - 0.65, 1.05), 0.13, segments=8, mat_idx=4)
            add_cylinder_to_bm(bm, (wx + 1.6, min_y - 0.65, 0.20), (wx + 1.6, min_y - 0.65, 1.05), 0.13, segments=8, mat_idx=4)

    # West Facade of Hangar 16 (prominently framed in Cam 1 Grande_Roue_Southwest_Waterfront H4..H6, V1..V5!):
    # Recessed Ground-Floor Industrial Loading Bay Doors, Projecting Steel Loading Canopy, Exterior Lintels, Guardrails & Bollards
    for wy in range(int(min_y + 4), int(max_y - 3), 5):
        # Vertical structural pilaster along West facade
        add_oriented_box(bm, (min_x + 0.16, wy - 2.5, 4.35), (0.0, 1.0), (1.0, 0.0), 0.48, 0.52, 6.90, mat_idx=1)
        # Upper recessed industrial window + projecting exterior steel lintel (Z = 5.90m, lintel at Z = 6.88m)
        add_oriented_box(bm, (min_x + 0.52, wy, 5.90), (0.0, 1.0), (1.0, 0.0), 2.6, 0.16, 1.75, mat_idx=3)
        add_oriented_box(bm, (min_x + 0.06, wy, 6.88), (0.0, 1.0), (1.0, 0.0), 3.0, 0.42, 0.22, mat_idx=4, include_bottom=True)
        # Deeply Recessed (0.58m) Ground-Floor Industrial Loading Bay Door + Heavy Exterior Steel Lintel (Z = 0.90m .. 3.75m)
        add_oriented_box(bm, (min_x + 0.58, wy, 2.32), (0.0, 1.0), (1.0, 0.0), 3.1, 0.16, 2.85, mat_idx=4)
        add_oriented_box(bm, (min_x + 0.04, wy, 3.88), (0.0, 1.0), (1.0, 0.0), 3.5, 0.52, 0.28, mat_idx=4, include_bottom=True)
        for jy_off in (-1.60, 1.60):
            add_oriented_box(bm, (min_x + 0.26, wy + jy_off, 2.32), (0.0, 1.0), (1.0, 0.0), 0.18, 0.58, 2.85, mat_idx=0)
        for rz_door in (1.45, 2.05, 2.65, 3.25):
            add_oriented_box(bm, (min_x + 0.46, wy, rz_door), (0.0, 1.0), (1.0, 0.0), 3.0, 0.10, 0.08, mat_idx=0)

    # Projecting West Loading Dock Overhang Canopy, Raised Concrete Dock Ramp & Guardrail (Cam 1 V1..V3, H5..H6)
    west_canopy_y0 = min_y + 12.0
    west_canopy_y1 = max_y - 2.0
    wc_mid_y = 0.5 * (west_canopy_y0 + west_canopy_y1)
    wc_len = west_canopy_y1 - west_canopy_y0
    # Overhanging industrial steel canopy at Z = 4.05m
    add_oriented_box(bm, (min_x - 1.35, wc_mid_y, 4.05), (0.0, 1.0), (1.0, 0.0), wc_len, 2.80, 0.26, mat_idx=1, include_bottom=True)
    add_oriented_box(bm, (min_x - 2.65, wc_mid_y, 4.05), (0.0, 1.0), (1.0, 0.0), wc_len + 0.2, 0.22, 0.34, mat_idx=4, include_bottom=True)
    # Raised concrete loading dock platform (Z = 0.02m .. 0.90m) & dark steel pipe handrail (Z = 0.90m .. 1.80m)
    add_oriented_box(bm, (min_x - 1.25, wc_mid_y, 0.46), (0.0, 1.0), (1.0, 0.0), wc_len, 2.60, 0.88, mat_idx=0)
    add_oriented_box(bm, (min_x - 2.45, wc_mid_y, 1.75), (0.0, 1.0), (1.0, 0.0), wc_len, 0.08, 0.07, mat_idx=4)
    add_oriented_box(bm, (min_x - 2.45, wc_mid_y, 1.32), (0.0, 1.0), (1.0, 0.0), wc_len, 0.06, 0.06, mat_idx=4)
    for col_y in [west_canopy_y0 + 1.0, wc_mid_y, west_canopy_y1 - 1.0]:
        add_cylinder_to_bm(bm, (min_x - 2.45, col_y, 0.90), (min_x - 2.45, col_y, 4.00), 0.12, segments=8, mat_idx=4)

    # Row of Protective Bollards & Red Security Block along West & Southwest Entrance of Hangar 16 (Cam 1 H5..H6, V1..V8)
    for bol_x, bol_y in [
        (min_x - 3.2, min_y + 4.0),
        (min_x - 3.2, min_y + 8.5),
        (min_x - 3.2, min_y + 13.0),
        (min_x - 1.5, min_y - 1.2),
        (min_x + 2.5, min_y - 1.2),
        (537.5, 536.2),
        (539.8, 536.2),
        (544.8, 536.0),
        (547.2, 535.8),
        (549.6, 535.6),
    ]:
        add_cylinder_to_bm(bm, (bol_x, bol_y, 0.02), (bol_x, bol_y, 0.92), 0.24, segments=10, mat_idx=0)
        add_cylinder_to_bm(bm, (bol_x, bol_y, 0.92), (bol_x, bol_y, 1.02), 0.26, segments=10, mat_idx=4)
    # Red concrete vehicle barrier block visible in Cam 1 V6, H6
    add_oriented_box(bm, (542.4, 536.2, 0.48), (1.0, 0.0), (0.0, 1.0), 1.45, 0.85, 0.92, mat_idx=6, include_bottom=True)

    # Red patio umbrellas along South Terrace recess of Hangar 16 (visible in satellite_topdown.png H1 V2..V3)
    for rx in [565.5, 570.0, 574.5]:
        add_cylinder_to_bm(bm, (rx, 505.8, 1.20), (rx, 505.8, 3.40), 1.65, segments=8, mat_idx=6)

    # Blue Ticket Booths at West Entrance (Cam 1: X=544.5, Y=536.5) and East Approach (Cam 4: X=668..672, Y=548)
    for kx, ky in [(544.2, 537.5), (667.5, 548.5), (671.5, 548.2)]:
        add_oriented_box(bm, (kx, ky, 1.45), (1.0, 0.0), (0.0, 1.0), 2.4, 2.4, 2.60, mat_idx=5, include_bottom=True)
        add_oriented_box(bm, (kx, ky, 1.55), (1.0, 0.0), (0.0, 1.0), 2.5, 2.5, 1.20, mat_idx=3)

    bm.to_mesh(mesh)
    bm.free()
    print("Constructed Hangar 16 (46866827)")
    return obj


def build_terrasses_and_zipline(dossier, col, pal):
    """
    Constructs:
    - Terrasses Bonsecours (46866826)
    - East Zipline Tower (1180387340) & West Zipline Tower (at X=501.7, Y=497.8, visible in Cam 1 & Cam 3 with red/purple banner wrap!)
    - East Pier Pavilion (1180387335)
    """
    mesh = bpy.data.meshes.new("MTL_VM_0024_TerrassesAndZipline_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0024_TerrassesAndZipline", mesh)
    col.objects.link(obj)

    mats = [
        pal["sandstone_pbr"],   # 0: Limestone/concrete walls
        pal["timber_wood"],     # 1: Timber pergolas & decks
        pal["glass_dark"],      # 2: Panoramic glass
        pal["white_steel"],     # 3: Steel tower frame
        pal["zipline_red"],     # 4: Zipline tower red/magenta banner wrap (visible in Cam 1 & Cam 3!)
        pal["cast_iron"],       # 5: Cables & railings
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Terrasses Bonsecours (46866826)
    bldg_tb = next((b for b in dossier["osm_features"]["buildings"] if b["id"] == 46866826), None)
    if bldg_tb:
        coords = bldg_tb["coords_xy"]
        add_prism_to_bm(bm, coords, 0.20, 0.90, mat_side=0, mat_top=0, mat_bottom=None)
        inset_l1 = inset_polygon_2d(coords, 0.35)
        add_prism_to_bm(bm, inset_l1, 0.90, 4.80, mat_side=0, mat_top=1, mat_bottom=None)
        rail_pts = inset_polygon_2d(inset_l1, 0.20)
        add_prism_to_bm(bm, rail_pts, 4.80, 5.90, mat_side=2, mat_top=2, mat_bottom=None)
        cx, cy = bldg_tb.get("centroid_xy", [713.67, 420.79])
        for px in [cx - 8.0, cx - 2.5, cx + 3.0, cx + 8.5]:
            for py in [cy - 6.0, cy, cy + 6.0]:
                add_cylinder_to_bm(bm, (px, py, 4.80), (px, py, 7.90), 0.15, segments=6, mat_idx=1)
            add_cylinder_to_bm(bm, (px, cy - 7.0, 7.90), (px, cy + 7.0, 7.90), 0.14, segments=6, mat_idx=1)

    # 2. East Zipline Tower (1180387340 at X=767.88, Y=491.17) & West Zipline Tower (at X=501.69, Y=497.83)
    # Note: West Zipline Tower is prominently visible in Cam 1 (H3..H5 V7..V8) and Cam 3 (H3..H5 V3) wrapped in red/magenta banner!
    for t_cx, t_cy, t_h, has_banner in [(767.88, 491.17, 25.0, False), (501.69, 497.83, 28.5, True)]:
        hw = 3.1
        # Base pedestals
        add_oriented_box(bm, (t_cx, t_cy, 0.60), (1.0, 0.0), (0.0, 1.0), hw * 2.1, hw * 2.1, 1.20, mat_idx=0)
        # 4 corner steel columns
        for dx in [-hw, hw]:
            for dy in [-hw, hw]:
                add_cylinder_to_bm(bm, (t_cx + dx, t_cy + dy, 1.20), (t_cx + dx * 0.85, t_cy + dy * 0.85, t_h), 0.24, segments=8, mat_idx=3)
        # Horizontal struts & decks
        for zh in [6.0, 12.0, 18.0, t_h - 1.5]:
            add_oriented_box(bm, (t_cx, t_cy, zh), (1.0, 0.0), (0.0, 1.0), hw * 1.9, hw * 1.9, 0.25, mat_idx=1)
        if has_banner:
            # Red/magenta branded mesh banner wrap around mid-upper tower (matches Cam 1 & Cam 3 ground truth!)
            add_oriented_box(bm, (t_cx, t_cy, t_h * 0.56), (1.0, 0.0), (0.0, 1.0), hw * 1.82, hw * 1.82, t_h * 0.68, mat_idx=4)

    # Aerial zipline cables across the basin
    add_cylinder_to_bm(bm, (501.7, 497.8, 27.5), (767.9, 491.2, 23.5), 0.03, segments=4, mat_idx=5)

    # 3. East Pier Pavilion (1180387335)
    bldg_ep = next((b for b in dossier["osm_features"]["buildings"] if b["id"] == 1180387335), None)
    if bldg_ep:
        add_prism_to_bm(bm, bldg_ep["coords_xy"], 0.20, 4.40, mat_side=3, mat_top=3, mat_bottom=None)

    bm.to_mesh(mesh)
    bm.free()
    print("Constructed Terrasses Bonsecours & Zipline Towers")
    return obj


# ------------------------------------------------------------------------------------------------
# 5. Mainland Streets, Promenades & Foregrounds (NO Ground Slab Under Bassin Bonsecours!)
# ------------------------------------------------------------------------------------------------

def build_mainland_streets_and_promenades(dossier, col, pal):
    """
    Constructs ONLY the mainland streets, sidewalks, crosswalks, and west promenade outside the water basin:
    - North of Y = 507.0m (Rue du Quai-de-l'Horloge, Hangar 16 apron, Cam 1 & Cam 4 foregrounds)
    - West of the basin outer wall (Promenade du Vieux-Port, Rue de la Commune Est, Cam 2 & Cam 3 foregrounds)
    - South of Y = 330.0m (South outer quay wall)
    Zero geometry overlaps Bassin Bonsecours water (Z = -2.20m)!
    """
    mesh = bpy.data.meshes.new("MTL_VM_0024_StreetNetwork_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0024_StreetNetwork", mesh)
    col.objects.link(obj)

    mats = [
        pal["asphalt_pbr"],       # 0: Asphalt roadbed
        pal["granite_curb"],      # 1: Granite sidewalks, curbs & retaining walls
        pal["cobble_pbr"],        # 2: Cobblestone / paver pedestrian promenade
        pal["grass_lawn"],        # 3: Mainland park lawns (Cam 4 & Cam 3 foregrounds)
        pal["walkway_gravel"],    # 4: Crushed-stone tree parterre (Cam 3 foreground)
        kit.get_or_create_pbr_material("Mat_Road_Paint_White", "#EAECEF", roughness=0.50),  # 5: White crosswalk stripes
        pal["cast_iron"],         # 6: Guardrails & bollards
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. North Mainland Base (North of Bassin Bonsecours: X=440..820, Y=505.5..610, Z = -0.25m .. +0.02m)
    north_land_poly = [
        (440.0, 505.5),
        (820.0, 507.5),
        (820.0, 610.0),
        (440.0, 610.0),
    ]
    add_prism_to_bm(bm, north_land_poly, -0.25, 0.02, mat_side=0, mat_top=0, mat_bottom=0)

    # 2. West Mainland Promenade Base (West of Bassin Bonsecours wall: X=440..534, Y=325..506, Z = -0.25m .. +0.16m)
    west_land_poly = [
        (440.0, 325.0),
        (471.5, 328.5),
        (500.5, 412.0),
        (534.5, 498.5),
        (534.5, 506.0),
        (440.0, 506.0),
    ]
    add_prism_to_bm(bm, west_land_poly, -0.25, 0.16, mat_side=1, mat_top=2, mat_bottom=0)

    # 3. Camera 1 Foreground (Grande_Roue_Southwest_Waterfront at X=538.0, Y=558.0, heading 171.8 deg looking South):
    # Cobblestone sidewalk on the right (west), white zebra crosswalk stripes across Rue du Quai-de-l'Horloge,
    # and road leading south toward the water basin & La Grande Roue!
    # West cobblestone apron in Cam 1 foreground (X=515..538.5, Y=535..565)
    add_oriented_box(bm, (528.0, 548.0, 0.10), (0.0, 1.0), (1.0, 0.0), 26.0, 18.0, 0.16, mat_idx=2)
    # Zebra crosswalk stripes directly in front of Cam 1 (X=536..545, Y=544..552)
    for cw_i in range(6):
        add_oriented_box(bm, (536.2 + cw_i * 1.45, 548.2, 0.035), (0.0, 1.0), (1.0, 0.0), 4.6, 0.65, 0.015, mat_idx=5)

    # 4. Camera 3 Foreground (Rue_de_la_CommuneEst_Basin_View at X=466.24, Y=557.16, heading 171.1 deg looking South):
    # Stepped granite planter / retaining walls & gravel tree parterre in the center-left foreground (X=460..485, Y=515..548)
    parterre_poly = [
        (463.5, 515.0),
        (478.0, 515.0),
        (474.5, 546.5),
        (463.5, 546.5),
    ]
    add_prism_to_bm(bm, parterre_poly, 0.02, 0.58, mat_side=1, mat_top=4, mat_bottom=None)
    # Inner stepped concrete wall edge
    add_oriented_box(bm, (470.5, 546.5, 0.42), (1.0, 0.0), (0.0, 1.0), 14.0, 0.45, 0.80, mat_idx=1)
    add_oriented_box(bm, (476.2, 530.0, 0.48), (0.0, 1.0), (1.0, 0.0), 32.0, 0.45, 0.90, mat_idx=1)

    # 5. Camera 4 Foreground (Ile_Bonsecours_Pavilion_Approach at X=683.57, Y=561.91, heading 195.5 deg looking SSW):
    # Curved granite curb & green grass lawn on the left (east, X=665..705, Y=525..556) and paved walkway
    cam4_lawn_poly = [
        (672.0, 520.0),
        (715.0, 520.0),
        (715.0, 554.0),
        (676.0, 554.0),
    ]
    add_prism_to_bm(bm, cam4_lawn_poly, 0.02, 0.22, mat_side=1, mat_top=3, mat_bottom=None)
    # Curved granite curb in Cam 4 bottom-left foreground (X=682..695, Y=550..557)
    add_oriented_box(bm, (688.0, 553.8, 0.14), (0.98, -0.18), (0.18, 0.98), 14.0, 8.0, 0.24, mat_idx=3)
    add_oriented_box(bm, (688.0, 557.8, 0.15), (0.98, -0.18), (0.18, 0.98), 14.2, 0.35, 0.26, mat_idx=1)

    bm.to_mesh(mesh)
    bm.free()
    print("Constructed Mainland Streets, Promenades & Camera Foregrounds (Zero overlap with Bassin Bonsecours)")
    return obj


# ------------------------------------------------------------------------------------------------
# 6. High-Poly Poly Haven 3D Trees, Streetlamps & Benches
# ------------------------------------------------------------------------------------------------

def spawn_trees_and_props(dossier, col, pal):
    """
    Appends real high-poly Poly Haven 3D trees (jacaranda_tree_LOD0), streetlamps (street_lamp_01),
    and benches (Master_Street_Bench / modular_street_seating) from assets/montreal_kit.blend,
    matching the dense canopy crowns around Île Bonsecours (H3..H8 in satellite_topdown.png) and Street View cameras.
    """
    # Load and merge all mesh parts (trunks + decimated lush foliage canopy) from jacaranda_tree.blend into a single fast mesh!
    combined_tree_mesh = None
    ph_tree_blend = os.path.join(POLYHAVEN_DIR, "models", "jacaranda_tree", "jacaranda_tree.blend")
    if os.path.exists(ph_tree_blend):
        with bpy.data.libraries.load(ph_tree_blend, link=False) as (df, dt):
            dt.objects = list(df.objects)
        loaded_objs = [o for o in dt.objects if o and o.type == "MESH" and o.data]
        if loaded_objs:
            combined_tree_mesh = bpy.data.meshes.new("Combined_Jacaranda_Tree_Mesh")
            bm_tree = bmesh.new()
            mat_list = []
            for o in loaded_objs:
                m = o.data
                mat_remap = {}
                for mi, mat in enumerate(m.materials):
                    if mat not in mat_list:
                        mat_list.append(mat)
                    mat_remap[mi] = mat_list.index(mat)
                bm_part = bmesh.new()
                bm_part.from_mesh(m)
                bmesh.ops.transform(bm_part, matrix=o.matrix_local, verts=bm_part.verts)
                # Decimate ultra-dense leaf card meshes (> 5000 faces) to 18% so 120 trees export to USD in < 2 seconds while keeping full lush canopy volume!
                if len(bm_part.faces) > 5000:
                    faces_to_del = [f for idx_f, f in enumerate(bm_part.faces) if (idx_f % 5) != 0]
                    bmesh.ops.delete(bm_part, geom=faces_to_del, context='FACES')
                for f in bm_part.faces:
                    f.material_index = mat_remap.get(f.material_index, 0)
                tmp_m = bpy.data.meshes.new("TmpPart")
                bm_part.to_mesh(tmp_m)
                bm_part.free()
                bm_tree.from_mesh(tmp_m)
                bpy.data.meshes.remove(tmp_m)
            bm_tree.to_mesh(combined_tree_mesh)
            bm_tree.free()
            for mat in mat_list:
                combined_tree_mesh.materials.append(mat)
        for o in dt.objects:
            if o:
                bpy.data.objects.remove(o, do_unlink=True)

    lamp_mesh = None
    ph_lamp_blend = os.path.join(POLYHAVEN_DIR, "models", "street_lamp_01", "street_lamp_01.blend")
    if os.path.exists(ph_lamp_blend):
        with bpy.data.libraries.load(ph_lamp_blend, link=False) as (df, dt):
            dt.objects = list(df.objects)
        for o in dt.objects:
            if o and o.type == "MESH" and o.data:
                lamp_mesh = o.data
                bpy.data.objects.remove(o, do_unlink=True)
                break

    bench_mesh = None
    ph_bench_blend = os.path.join(POLYHAVEN_DIR, "models", "modular_street_seating", "modular_street_seating.blend")
    if os.path.exists(ph_bench_blend):
        with bpy.data.libraries.load(ph_bench_blend, link=False) as (df, dt):
            dt.objects = list(df.objects)
        for o in dt.objects:
            if o and o.type == "MESH" and o.data:
                bench_mesh = o.data
                bpy.data.objects.remove(o, do_unlink=True)
                break

    # Ensure tree leaf materials are lush summer green matching satellite_topdown.png and Street View
    if combined_tree_mesh:
        for mat in combined_tree_mesh.materials:
            if mat and mat.use_nodes:
                for n in mat.node_tree.nodes:
                    if n.type == "BSDF_PRINCIPLED":
                        if "leaf" in mat.name.lower() or "leaves" in mat.name.lower() or "foliage" in mat.name.lower() or "twig" in mat.name.lower():
                            n.inputs["Base Color"].default_value = (0.14, 0.38, 0.09, 1.0)
                            if "Alpha" in n.inputs:
                                n.inputs["Alpha"].default_value = 1.0

    # 1. Spawn Surveyed OSM Trees + Supplemental Satellite-Matched Crown Trees on Île Bonsecours & Foregrounds
    raw_trees = list(dossier.get("osm_features", {}).get("trees", []))
    # Exclude trees inside the Pavillon du Bassin Bonsecours roof & west plaza footprint (X: 575..626, Y: 405..458)
    trees = [
        t for t in raw_trees
        if not (575.0 <= t.get("x", 0.0) <= 626.0 and 405.0 <= t.get("y", 0.0) <= 458.0)
    ]

    supplemental_trees = [
        # Île Bonsecours North Perimeter Rim (H3, V3..V6 in satellite_topdown.png)
        {"x": 588.0, "y": 469.5, "scale": 0.62},
        {"x": 598.5, "y": 470.5, "scale": 0.65},
        {"x": 609.0, "y": 470.8, "scale": 0.62},
        {"x": 620.0, "y": 471.0, "scale": 0.60},
        {"x": 629.5, "y": 471.2, "scale": 0.65},
        {"x": 636.8, "y": 471.5, "scale": 0.68},
        {"x": 636.5, "y": 456.0, "scale": 0.60},
        {"x": 636.5, "y": 442.0, "scale": 0.60},
        # Île Bonsecours West Edge & South-West Grove (H4..H8, V2..V3 in satellite_topdown.png)
        {"x": 574.0, "y": 442.0, "scale": 0.58},
        {"x": 569.0, "y": 426.0, "scale": 0.56},
        {"x": 556.0, "y": 392.0, "scale": 0.65},
        {"x": 555.0, "y": 378.0, "scale": 0.65},
        # Camera 3 Foreground Tree Allee (Rue_de_la_CommuneEst_Basin_View H1..H6, V5..V8)
        {"x": 465.2, "y": 542.0, "scale": 0.95},
        {"x": 464.5, "y": 532.0, "scale": 0.90},
        {"x": 463.8, "y": 522.0, "scale": 0.85},
        {"x": 463.0, "y": 512.0, "scale": 0.85},
        {"x": 486.0, "y": 515.0, "scale": 0.80},
        {"x": 496.0, "y": 506.0, "scale": 0.80},
        {"x": 518.0, "y": 520.0, "scale": 0.80},
        # Camera 4 Foreground Tall Trees (Ile_Bonsecours_Pavilion_Approach H1..H5, V3..V8)
        {"x": 676.0, "y": 546.0, "scale": 1.05},
        {"x": 669.0, "y": 542.0, "scale": 1.00},
        {"x": 679.5, "y": 536.0, "scale": 0.95},
        {"x": 688.0, "y": 528.0, "scale": 0.85},
        {"x": 698.0, "y": 525.0, "scale": 0.85},
    ]

    if combined_tree_mesh:
        all_trees = trees + supplemental_trees
        print(f"Spawning {len(all_trees)} high-poly Poly Haven 3D trees (1 combined mesh per tree)...")
        for idx, t in enumerate(all_trees):
            tx = t.get("x")
            ty = t.get("y")
            if tx is None or ty is None:
                continue
            base_s = t.get("scale", 0.56 + ((idx % 5) * 0.03))
            rot_z = math.radians((idx * 53) % 360)
            t_obj = bpy.data.objects.new(f"Tree_{idx}", combined_tree_mesh)
            col.objects.link(t_obj)
            t_obj.scale = (base_s, base_s, base_s * (0.95 + ((idx % 5) * 0.03)))
            t_obj.rotation_euler = (0.0, 0.0, rot_z)
            t_obj.location = (tx, ty, 0.22)

    # 2. Spawn Heritage Streetlamps along Island Perimeter & Quays
    if lamp_mesh:
        lamp_coords = [
            (532.0, 495.0, 0.24, 65.0),
            (555.0, 500.0, 0.24, 0.0),
            (585.0, 501.0, 0.24, 0.0),
            (615.0, 502.0, 0.24, 0.0),
            (645.0, 503.0, 0.24, 0.0),
            (575.0, 418.0, 0.25, 0.0),
            (590.0, 464.0, 0.25, 0.0),
            (620.0, 466.0, 0.25, 0.0),
            (636.0, 445.0, 0.25, 90.0),
            (636.0, 410.0, 0.25, 90.0),
            (672.0, 549.0, 0.22, 180.0),
            (462.0, 535.0, 0.20, 90.0),
        ]
        for l_idx, (lx, ly, lz, lrot) in enumerate(lamp_coords):
            l_obj = bpy.data.objects.new(f"Lamp_{l_idx}", lamp_mesh)
            col.objects.link(l_obj)
            l_obj.location = (lx, ly, lz)
            l_obj.rotation_euler = (0.0, 0.0, math.radians(lrot))

    # 3. Spawn Waterfront Park Benches along Île Bonsecours & North Boardwalk
    if bench_mesh:
        bench_coords = [
            (582.0, 448.0, 0.25, -25.0),
            (598.0, 466.5, 0.25, 0.0),
            (615.0, 466.8, 0.25, 0.0),
            (637.0, 430.0, 0.25, 90.0),
            (637.0, 405.0, 0.25, 90.0),
            (565.0, 408.0, 0.25, 180.0),
            (468.5, 536.0, 0.58, 0.0),
        ]
        for b_idx, (bx, by, bz, brot) in enumerate(bench_coords):
            b_obj = bpy.data.objects.new(f"Bench_{b_idx}", bench_mesh)
            col.objects.link(b_obj)
            b_obj.location = (bx, by, bz)
            b_obj.rotation_euler = (0.0, 0.0, math.radians(brot))


# ------------------------------------------------------------------------------------------------
# 7. World Lighting, Cameras & Snapshot Render
# ------------------------------------------------------------------------------------------------

def setup_world_and_render(dossier, iter_num=2):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = False

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    wnodes = world.node_tree.nodes
    wlinks = world.node_tree.links
    wnodes.clear()

    w_out = wnodes.new("ShaderNodeOutputWorld")
    w_bg = wnodes.new("ShaderNodeBackground")
    w_bg.inputs["Strength"].default_value = 1.15

    if os.path.exists(HDRI_PATH):
        env_tex = wnodes.new("ShaderNodeTexEnvironment")
        env_tex.image = bpy.data.images.load(HDRI_PATH, check_existing=True)
        wlinks.new(w_bg.inputs["Color"], env_tex.outputs["Color"])
    else:
        w_bg.inputs["Color"].default_value = (0.52, 0.68, 0.88, 1.0)
    wlinks.new(w_out.inputs["Surface"], w_bg.outputs["Background"])

    sun_data = bpy.data.lights.new(name="MTL_Sun", type='SUN')
    sun_data.energy = 3.8
    sun_data.color = (1.0, 0.96, 0.90)
    sun_data.angle = math.radians(4.5)
    sun_obj = bpy.data.objects.new(name="MTL_Sun", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    # Match sun azimuth/elevation casting wheel shadow WNW as seen in satellite_topdown.png
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(18.0), math.radians(-115.0))

    # Render Overview Snapshot (1280x720) framing Bassin Bonsecours, Île Bonsecours & La Grande Roue
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    ov_data = bpy.data.cameras.new(name="Cam_Overview")
    ov_data.lens = 28.0
    ov_data.clip_start = 0.5
    ov_data.clip_end = 2000.0
    ov_obj = bpy.data.objects.new(name="Cam_Overview", object_data=ov_data)
    bpy.context.scene.collection.objects.link(ov_obj)
    ov_obj.location = (520.0, 495.0, 58.0)
    look_vec = Vector((615.0, 425.0, 18.0)) - ov_obj.location
    ov_obj.rotation_euler = look_vec.to_track_quat('-Z', 'Y').to_euler()

    scene.camera = ov_obj
    scene.render.filepath = SNAPSHOT_PATH
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Overview Snapshot -> {SNAPSHOT_PATH}")
    sys.stdout.flush()


def main():
    iter_num = 2
    skip_render = False
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if args:
            if "--skip-render" in args:
                skip_render = True
            for a in args:
                if a.isdigit():
                    iter_num = int(a)

    print(f"=== Starting Build for Block {BLOCK_ID} (Iteration {iter_num}) ===")
    sys.stdout.flush()
    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    # Hierarchical collection structure: Block_MTL-VM-0024 -> Block_MTL-VM-0024_Owned
    root_col = get_or_create_collection(f"Block_{BLOCK_ID}")
    owned_col = get_or_create_collection(f"Block_{BLOCK_ID}_Owned", parent=root_col)
    pal = create_palette()

    # 1. Bassin Bonsecours Deep Water Basin (Z = -2.20m) & Sculpted Île Bonsecours Island
    build_basin_and_ile_bonsecours(owned_col, pal)
    sys.stdout.flush()

    # 2. La Grande Roue de Montréal (60m White Structural Steel Ferris Wheel)
    build_la_grande_roue(owned_col, pal)
    sys.stdout.flush()

    # 3. Pavillon du Bassin Bonsecours, Twin Canopies & South Bistro / Ticket Pavilions
    build_island_pavilions(dossier, owned_col, pal)
    sys.stdout.flush()

    # 4. Hangar 16, Terrasses Bonsecours & Zipline Towers
    bldg_hangar = next((b for b in dossier["osm_features"]["buildings"] if b["id"] == 46866827), None)
    if bldg_hangar:
        build_hangar_16(bldg_hangar, owned_col, pal)
    build_terrasses_and_zipline(dossier, owned_col, pal)
    sys.stdout.flush()

    # 5. Mainland Streets, Promenades & Foregrounds (Zero overlap with water basin!)
    build_mainland_streets_and_promenades(dossier, owned_col, pal)
    sys.stdout.flush()

    # 6. High-Poly Poly Haven 3D Trees, Streetlamps & Benches
    spawn_trees_and_props(dossier, owned_col, pal)
    sys.stdout.flush()

    # 7. Save Clean .blend and Export USD before rendering
    tmp_blend = BLEND_OUT_PATH + ".tmp.blend"
    for p in (tmp_blend, tmp_blend + "@", tmp_blend + "1", BLEND_OUT_PATH, BLEND_OUT_PATH + "@", BLEND_OUT_PATH + "1", BLEND_OUT_PATH + "2"):
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"Warning during pack_all: {e}")
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
    try:
        shutil.move(tmp_blend, BLEND_OUT_PATH)
    except Exception:
        shutil.copyfile(tmp_blend, BLEND_OUT_PATH)
        try:
            os.remove(tmp_blend)
        except Exception:
            pass

    print(f"Saved clean .blend to {BLEND_OUT_PATH}")
    bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, check_existing=False)
    print(f"Exported clean USD to {USDC_OUT_PATH}")
    sys.stdout.flush()

    # 8. Setup Lighting & Render Snapshot
    if not skip_render:
        setup_world_and_render(dossier, iter_num=iter_num)
        try:
            bpy.ops.file.pack_all()
        except Exception:
            pass
        bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT_PATH, copy=True)

    print(f"=== Successfully completed Iteration {iter_num} build for {BLOCK_ID} ===")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
