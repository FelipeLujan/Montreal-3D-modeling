"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0019
Chapelle Notre-Dame-de-Bon-Secours & Rue Bonsecours Block (400 Rue Saint-Paul Est)

Architecture & Features:
1. Chapelle Notre-Dame-de-Bon-Secours (400 Rue Saint-Paul Est, osm_id: 87389036):
   - Strict Coordinate Alignment along Nave Principal Axis (heading -12.5 deg, cross 77.5 deg):
     * Front NW entrance portal facing Rue Saint-Paul Est / Rue Bonsecours:
       - Classical projecting ashlar portal with fluted stone pilasters, triangular pediment,
         semicircular arch with archivolt, and arched crimson double doors (Mat_Chapel_Door_Red)
         with radial fanlight transom.
       - Stepped granite entrance stairs with cast-iron handrails.
       - Arched stone niche housing the gilded statue of Notre-Dame with Child (Mat_Gold_Gilt).
       - Circular stone rose / oculus window with decorative moldings.
       - Flanking semicircular arched stained-glass windows (2.2m wide, 6.5m high, 0.50m deep recess)
         with stone sills, archivolts, and white lattice mullions (exactly as in Street View reference).
       - Triangular stone gable rising to Z = 21.5m with apex stone cross.
       - Twin octagonal stone bell turrets rising to Z = 27.5m with copper conical caps and iron crosses.
     * Nave Walls & Slate Gabled Roof:
       - Symmetrical pitched slate roof (Mat_Dark_Slate_Roof) with verdigris copper ridge cresting
         running from front gable apex to rear apse with ZERO floating overhangs.
       - Massive exterior stone buttresses along side walls.
       - Deeply recessed (>= 0.50m) high round-arched stained-glass windows between buttresses.
     * Verdigris Copper Spire & Belfry (La Flèche de Bonsecours):
       - Square copper base transitioning to an octagonal belfry lantern with 8 arched louvered openings.
       - Stepped copper balcony and balustrade at Z = 32.0m.
       - Soaring octagonal copper needle spire rising to Z = 44.5m crowned with a gilded finial and cross.
     * Harbor-Facing Lookout Terrace & Statues:
       - Lookout terrace on southeast roof elevation facing the Old Port / St. Lawrence River.
       - Monumental gilded statue of Notre-Dame (Star of the Sea) extending open arms toward the river
         and harbor ships, flanked by stone angel statues on pedestals!
2. Marguerite Bourgeoys Museum Complex (osm_id: 87389002):
   - 4-storey rustic coursed limestone ashlar facade along Rue Bonsecours.
   - Deeply recessed sash windows (>= 0.48m reveal) with cut stone lintels, sills, and white frames.
   - Semicircular arched entrance portals, pitched slate roofs with copper dormers and stone chimneys.
3. Maison Pierre du Calvet (osm_id: 339924180):
   - 1770-1771 French colonial fieldstone residence with massive parapeted firebreak gables,
     twin stone chimneys, and 3 storeys of deeply recessed small-pane sash windows.
4. Rue Bonsecours Victorian Stone Row Buildings (osm_ids: 339924177, 339924178, 339924179, 340013662, 340013663):
   - 3 to 4 storeys of cut grey limestone facades with deeply recessed window bays (0.50m),
     arched doorways, and bracketed stone cornices.
5. All 124 Primary Owned Buildings:
   - High-poly BMesh geometry, deeply recessed (>= 0.45m) window bays, stone sills, lintels, mullions,
     and reflective dark glass.
   - Strict Z-fighting prevention: roof membranes inset >= 0.15m and vertically offset by >= 0.06m.
   - Solid watertight ground stratum (Z = -0.25m to 0.00m) with upward (+Z) normals.
   - PBR asphalt and Old Montreal granite cobblestone roadbeds, raised (+0.15m) granite sidewalks with 3D curbs.
   - Zero Context Proxy meshes created or kept! All objects linked to Block_MTL-VM-0019_Owned.
"""

import os
import sys
import json
import math
import bpy
import bmesh
from mathutils import Vector

BLOCK_ID = "MTL-VM-0019"
BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
REGISTRY_PATH = os.path.join(BASE_DIR, "data", "building_ownership_registry.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
SNAPSHOT_PATH = os.path.join(BASE_DIR, "output", "renders", f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
MONTREAL_KIT_PATH = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
HDRI_PATH = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT_PATH), exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0


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


def link_obj(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


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


def make_pbr_mat(name, prefix, tint=(1.0, 1.0, 1.0), scale=0.68, roughness_mult=1.0, metallic=0.0, normal_strength=0.60):
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

    diff_path = find_polyhaven_map(prefix, "diff")
    rough_path = find_polyhaven_map(prefix, "rough")
    nor_path = find_polyhaven_map(prefix, "nor")

    if diff_path:
        img_d = bpy.data.images.load(diff_path, check_existing=True)
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = img_d
        tex_d.projection = "BOX"
        tex_d.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])

        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MIX"
        mix.inputs["Factor"].default_value = 0.28
        mix.inputs["B"].default_value = (tint[0], tint[1], tint[2], 1.0)
        links.new(tex_d.outputs["Color"], mix.inputs["A"])
        links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1.0)

    if rough_path:
        img_r = bpy.data.images.load(rough_path, check_existing=True)
        img_r.colorspace_settings.name = "Non-Color"
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
        bsdf.inputs["Roughness"].default_value = 0.55 * roughness_mult

    if nor_path:
        img_n = bpy.data.images.load(nor_path, check_existing=True)
        img_n.colorspace_settings.name = "Non-Color"
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


def make_simple_mat(name, color, roughness=0.4, metallic=0.0, ior=1.45, emission_strength=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    if emission_strength > 0.0:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (color[0], color[1], color[2], 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def create_block_palette():
    pal = {}
    # Real Poly Haven 2K PBR materials (>= 12 distinct facade and street textures)
    pal["limestone_ashlar_white"] = make_pbr_mat(
        "Mat_Limestone_Ashlar_White", "castle_brick_02_white",
        tint=(0.94, 0.93, 0.89), scale=0.42, roughness_mult=0.82, normal_strength=0.95
    )
    pal["limestone_ashlar_grey"] = make_pbr_mat(
        "Mat_Limestone_Ashlar_Grey", "stone_brick_wall_001",
        tint=(0.74, 0.76, 0.78), scale=0.38, roughness_mult=0.85, normal_strength=1.15
    )
    pal["limestone_ashlar_warm"] = make_pbr_mat(
        "Mat_Limestone_Ashlar_Warm", "sandstone_blocks_05",
        tint=(0.86, 0.82, 0.74), scale=0.38, roughness_mult=0.86, normal_strength=1.05
    )
    pal["limestone_rustic_buff"] = make_pbr_mat(
        "Mat_Limestone_Rustic_Buff", "medieval_blocks_06",
        tint=(0.72, 0.70, 0.66), scale=0.40, roughness_mult=0.92, normal_strength=1.25
    )
    pal["granite_curb"] = make_pbr_mat(
        "Mat_Granite_Curb", "concrete_block_wall",
        tint=(0.56, 0.58, 0.60), scale=0.45, roughness_mult=0.78, normal_strength=0.90
    )
    pal["brick_heritage_red"] = make_pbr_mat(
        "Mat_Brick_Heritage_Red", "castle_brick_02_red",
        tint=(0.78, 0.36, 0.26), scale=0.42, roughness_mult=0.88, normal_strength=1.15
    )
    pal["brick_brown"] = make_pbr_mat(
        "Mat_Brick_Brown", "brick_wall_04",
        tint=(0.64, 0.44, 0.36), scale=0.42, roughness_mult=0.88, normal_strength=1.15
    )
    pal["brick_yellow"] = make_pbr_mat(
        "Mat_Brick_Yellow", "yellow_brick",
        tint=(0.84, 0.74, 0.54), scale=0.42, roughness_mult=0.88, normal_strength=1.10
    )
    pal["brick_dark"] = make_pbr_mat(
        "Mat_Brick_Dark", "dark_brick_wall",
        tint=(0.48, 0.36, 0.32), scale=0.42, roughness_mult=0.90, normal_strength=1.15
    )
    pal["sandstone_red"] = make_pbr_mat(
        "Mat_Sandstone_Red", "red_sandstone_wall",
        tint=(0.74, 0.50, 0.42), scale=0.38, roughness_mult=0.88, normal_strength=1.15
    )
    pal["stone_tile_facade"] = make_pbr_mat(
        "Mat_Stone_Tile_Facade", "stone_tile_wall",
        tint=(0.70, 0.71, 0.69), scale=0.38, roughness_mult=0.88, normal_strength=1.10
    )
    pal["cobblestone_street"] = make_pbr_mat(
        "Mat_Cobblestone_Street", "cobblestone_floor_08",
        tint=(0.56, 0.57, 0.59), scale=0.36, roughness_mult=0.85, normal_strength=1.20
    )
    pal["sidewalk_flagstone"] = make_pbr_mat(
        "Mat_Sidewalk_Flagstone", "stone_tile_wall",
        tint=(0.78, 0.78, 0.76), scale=0.34, roughness_mult=0.80, normal_strength=0.85
    )
    pal["street_asphalt"] = make_pbr_mat(
        "Mat_Street_Asphalt", "asphalt_02",
        tint=(0.34, 0.35, 0.37), scale=0.25, roughness_mult=0.88, normal_strength=0.95
    )
    pal["roof_membrane"] = make_pbr_mat(
        "Mat_Roof_Membrane", "concrete_block_wall",
        tint=(0.62, 0.63, 0.65), scale=0.32, roughness_mult=0.90, normal_strength=0.75
    )
    pal["park_grass"] = make_pbr_mat(
        "Mat_Park_Grass", "leafy_grass",
        tint=(0.24, 0.50, 0.18), scale=0.42, roughness_mult=1.05, normal_strength=1.10
    )
    pal["crushed_stone_path"] = make_pbr_mat(
        "Mat_Crushed_Stone_Path", "sandstone_blocks_05",
        tint=(0.76, 0.72, 0.64), scale=0.45, roughness_mult=0.95, normal_strength=0.90
    )

    # Architectural shaders: Verdigris copper, slate, reflective glass, gold gilt
    pal["copper_verdigris"] = make_simple_mat(
        "Mat_Verdigris_Copper", (0.32, 0.58, 0.48), roughness=0.42, metallic=0.68
    )
    pal["dark_slate_roof"] = make_simple_mat(
        "Mat_Dark_Slate_Roof", (0.18, 0.20, 0.23), roughness=0.55, metallic=0.15
    )
    pal["window_glass"] = make_simple_mat(
        "Mat_Window_Glass_Reflective", (0.06, 0.09, 0.14), roughness=0.03, metallic=0.38, ior=1.52
    )
    pal["window_mullion_dark"] = make_simple_mat(
        "Mat_Window_Mullion_Dark", (0.12, 0.13, 0.14), roughness=0.35, metallic=0.30
    )
    pal["window_mullion_white"] = make_simple_mat(
        "Mat_Window_Mullion_White", (0.92, 0.92, 0.92), roughness=0.30, metallic=0.05
    )
    pal["chapel_door_red"] = make_simple_mat(
        "Mat_Chapel_Door_Red", (0.55, 0.12, 0.10), roughness=0.32, metallic=0.08
    )
    pal["gold_gilt"] = make_simple_mat(
        "Mat_Gold_Gilt", (0.95, 0.78, 0.22), roughness=0.18, metallic=0.90
    )
    pal["stone_angel_marble"] = make_simple_mat(
        "Mat_Stone_Angel_Marble", (0.86, 0.85, 0.82), roughness=0.52, metallic=0.05
    )
    pal["cast_iron_black"] = make_simple_mat(
        "Mat_Cast_Iron_Black", (0.08, 0.08, 0.09), roughness=0.36, metallic=0.82
    )
    pal["white_paint"] = make_simple_mat(
        "Mat_White_Road_Paint", (0.94, 0.94, 0.94), roughness=0.35, metallic=0.0
    )
    pal["yellow_paint"] = make_simple_mat(
        "Mat_Yellow_Road_Paint", (0.92, 0.65, 0.14), roughness=0.40, metallic=0.0
    )
    pal["warm_lamp_glow"] = make_simple_mat(
        "Mat_Warm_Lamp_Glow", (1.0, 0.92, 0.74), roughness=0.20, emission_strength=4.5
    )
    return pal


def ensure_ccw(pts_2d):
    pts = list(pts_2d)
    if len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.02:
        pts = pts[:-1]
    area = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        area += (x1 * y2 - x2 * y1)
    if area < 0:
        pts.reverse()
    return pts


def inset_polygon(pts_2d, inset_m=1.2):
    pts = ensure_ccw(pts_2d)
    n = len(pts)
    if n < 3:
        return pts
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    out = []
    for i in range(n):
        p_prev = pts[(i - 1) % n]
        p_cur = pts[i]
        p_next = pts[(i + 1) % n]
        dx1, dy1 = p_cur[0] - p_prev[0], p_cur[1] - p_prev[1]
        dx2, dy2 = p_next[0] - p_cur[0], p_next[1] - p_cur[1]
        L1 = max(0.01, math.hypot(dx1, dy1))
        L2 = max(0.01, math.hypot(dx2, dy2))
        in1x, in1y = -dy1 / L1, dx1 / L1
        in2x, in2y = -dy2 / L2, dx2 / L2
        bx, by = in1x + in2x, in1y + in2y
        bL = math.hypot(bx, by)
        if bL > 0.05:
            bx /= bL
            by /= bL
        else:
            vx, vy = cx - p_cur[0], cy - p_cur[1]
            vL = max(0.01, math.hypot(vx, vy))
            bx, by = vx / vL, vy / vL
        out.append((p_cur[0] + bx * inset_m, p_cur[1] + by * inset_m))
    return out


def add_box(bm, center, size, angle_z=0.0, mat_idx=0, cap_top=True, cap_bottom=True):
    sx, sy, sz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    cx, cy, cz = center
    ca, sa = math.cos(angle_z), math.sin(angle_z)
    local_pts = [
        (-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
        (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz),
    ]
    verts = []
    for lx, ly, lz in local_pts:
        wx = cx + lx * ca - ly * sa
        wy = cy + lx * sa + ly * ca
        wz = cz + lz
        verts.append(bm.verts.new((wx, wy, wz)))
    faces = [
        (0, 1, 5, 4), (1, 2, 6, 5),
        (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    if cap_bottom:
        faces.append((0, 3, 2, 1))
    if cap_top:
        faces.append((4, 5, 6, 7))
    for f in faces:
        face = bm.faces.new([verts[i] for i in f])
        face.material_index = mat_idx


def add_prism(bm, pts_2d, z0, z1, mat_side=0, mat_top=0, cap_bottom=True):
    pts = ensure_ccw(pts_2d)
    n = len(pts)
    if n < 3:
        return
    vb = [bm.verts.new((x, y, z0)) for x, y in pts]
    vt = [bm.verts.new((x, y, z1)) for x, y in pts]
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
        f.material_index = mat_side
    ft = bm.faces.new(vt)
    ft.material_index = mat_top
    if cap_bottom:
        fb = bm.faces.new(list(reversed(vb)))
        fb.material_index = mat_side


def add_cylinder(bm, cx, cy, z0, z1, r_bot, r_top=None, segs=16, mat_idx=0):
    if r_top is None:
        r_top = r_bot
    vb, vt = [], []
    for i in range(segs):
        ang = 2.0 * math.pi * i / segs
        ca, sa = math.cos(ang), math.sin(ang)
        vb.append(bm.verts.new((cx + ca * r_bot, cy + sa * r_bot, z0)))
        vt.append(bm.verts.new((cx + ca * r_top, cy + sa * r_top, z1)))
    for i in range(segs):
        j = (i + 1) % segs
        f = bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
        f.material_index = mat_idx
    ft = bm.faces.new(vt)
    ft.material_index = mat_idx
    fb = bm.faces.new(list(reversed(vb)))
    fb.material_index = mat_idx


def add_cone(bm, cx, cy, z0, z1, radius, segs=16, mat_idx=0):
    vb = []
    for i in range(segs):
        ang = 2.0 * math.pi * i / segs
        ca, sa = math.cos(ang), math.sin(ang)
        vb.append(bm.verts.new((cx + ca * radius, cy + sa * radius, z0)))
    v_apex = bm.verts.new((cx, cy, z1))
    for i in range(segs):
        j = (i + 1) % segs
        f = bm.faces.new((vb[i], vb[j], v_apex))
        f.material_index = mat_idx
    fb = bm.faces.new(list(reversed(vb)))
    fb.material_index = mat_idx


def add_wall_strip(bm, p1, p2, z0, z1, offset_out, thickness, mat_idx=0, cap_top=True, cap_bottom=True):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 0.05:
        return
    ux, uy = dx / L, dy / L
    nx, ny = uy, -ux
    mx = 0.5 * (p1[0] + p2[0]) + nx * offset_out
    my = 0.5 * (p1[1] + p2[1]) + ny * offset_out
    ang = math.atan2(uy, ux)
    add_box(bm, (mx, my, 0.5 * (z0 + z1)), (L, thickness, z1 - z0), angle_z=ang, mat_idx=mat_idx,
            cap_top=cap_top, cap_bottom=cap_bottom)


def add_smooth_arch_band(bm, wx, wy, z_spring, r_in_w, r_in_h, arch_thick, n_front, n_back, ux, uy, nx, ny, segs=16, mat_idx=0):
    r_out_w = r_in_w + arch_thick
    r_out_h = r_in_h + arch_thick
    for i in range(segs):
        a0 = math.pi * i / segs
        a1 = math.pi * (i + 1) / segs
        c0, s0 = math.cos(a0), math.sin(a0)
        c1, s1 = math.cos(a1), math.sin(a1)
        pts_ring = [
            (c0 * r_in_w, n_back, z_spring + s0 * r_in_h),
            (c1 * r_in_w, n_back, z_spring + s1 * r_in_h),
            (c1 * r_out_w, n_back, z_spring + s1 * r_out_h),
            (c0 * r_out_w, n_back, z_spring + s0 * r_out_h),
            (c0 * r_in_w, n_front, z_spring + s0 * r_in_h),
            (c1 * r_in_w, n_front, z_spring + s1 * r_in_h),
            (c1 * r_out_w, n_front, z_spring + s1 * r_out_h),
            (c0 * r_out_w, n_front, z_spring + s0 * r_out_h),
        ]
        v = [bm.verts.new((wx + ux * u_off + nx * n_off, wy + uy * u_off + ny * n_off, z_val))
             for u_off, n_off, z_val in pts_ring]
        for f_idxs in [(4, 5, 6, 7), (1, 0, 3, 2), (0, 1, 5, 4), (2, 3, 7, 6), (0, 4, 7, 3), (1, 2, 6, 5)]:
            f = bm.faces.new([v[k] for k in f_idxs])
            f.material_index = mat_idx


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


def build_detailed_facade_wall(bm, p1, p2, z0, z1, bay_w=3.4, floor_h=3.5,
                               mat_wall=0, mat_glass=1, mat_frame=2, mat_sill=0,
                               recess=0.50, has_ground_shop=True, arched_windows=False,
                               bracketed_cornice=True, has_top_cornice=True):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 1.8:
        add_wall_strip(bm, p1, p2, z0, z1, -0.15, 0.35, mat_idx=mat_wall, cap_top=False, cap_bottom=False)
        return
    ux, uy = dx / L, dy / L
    nx, ny = uy, -ux
    ang = math.atan2(uy, ux)

    # Glass backing plane recessed by 0.50m (cap_top=False, cap_bottom=False to prevent roof coplanar fight)
    add_wall_strip(bm, p1, p2, z0 + 0.05, z1 - 0.15, -recess, 0.12, mat_idx=mat_glass, cap_top=False, cap_bottom=False)

    n_bays = max(1, int(round(L / bay_w)))
    actual_bay = L / n_bays
    pier_w = min(0.85, actual_bay * 0.26)
    win_w = actual_bay - pier_w

    # Vertical stone piers between window bays (capped by top cornice, omit intermediate top/bottom caps)
    for i in range(n_bays + 1):
        w = pier_w * (1.25 if (i == 0 or i == n_bays) else 1.0)
        s = max(w * 0.5, min(L - w * 0.5, i * actual_bay))
        px = p1[0] + ux * s + nx * (-recess * 0.5 + 0.04)
        py = p1[1] + uy * s + ny * (-recess * 0.5 + 0.04)
        add_box(bm, (px, py, 0.5 * (z0 + z1)), (w, recess + 0.20, z1 - z0), angle_z=ang, mat_idx=mat_wall,
                cap_top=False, cap_bottom=False)

    # Floor spandrels, stone sills, lintels, and mullions
    n_floors = max(1, int(round((z1 - z0) / floor_h)))
    actual_fh = (z1 - z0) / n_floors
    for fl in range(n_floors):
        fz0 = z0 + fl * actual_fh
        fz1 = fz0 + actual_fh
        spandrel_h = actual_fh * 0.24

        # Spandrel wall band (omit caps to prevent coplanar fighting)
        add_wall_strip(bm, p1, p2, fz0, fz0 + spandrel_h, -recess * 0.45, recess + 0.14,
                       mat_idx=mat_wall, cap_top=False, cap_bottom=False)

        # Projecting stone sill
        sill_p1 = (p1[0] + ux * 0.35, p1[1] + uy * 0.35)
        sill_p2 = (p2[0] - ux * 0.35, p2[1] - uy * 0.35)
        add_wall_strip(bm, sill_p1, sill_p2, fz0 + spandrel_h - 0.08, fz0 + spandrel_h + 0.06,
                       0.08, 0.24, mat_idx=mat_sill, cap_top=True, cap_bottom=True)

        win_z0 = fz0 + spandrel_h
        win_z1 = fz1 - 0.18
        win_zc = 0.5 * (win_z0 + win_z1)
        win_h = max(0.4, win_z1 - win_z0)

        # Horizontal transom & vertical mullions
        for b in range(n_bays):
            sc = (b + 0.5) * actual_bay
            wx = p1[0] + ux * sc + nx * (-recess + 0.08)
            wy = p1[1] + uy * sc + ny * (-recess + 0.08)
            add_box(bm, (wx, wy, win_z0 + win_h * 0.52), (win_w, 0.09, 0.08), angle_z=ang, mat_idx=mat_frame,
                    cap_top=False, cap_bottom=False)
            add_box(bm, (wx, wy, win_zc), (0.08, 0.10, win_h), angle_z=ang, mat_idx=mat_frame,
                    cap_top=False, cap_bottom=False)

            # Arch bands for upper floor heritage windows
            if arched_windows and win_w > 1.2 and fl > 0:
                add_smooth_arch_band(bm, p1[0] + ux * sc, p1[1] + uy * sc, win_z1 - 0.35,
                                     win_w * 0.45, 0.32, 0.16, 0.12, -0.05, ux, uy, nx, ny, segs=14, mat_idx=mat_sill)

    # Top entablature & projecting bracketed stone cornice
    if has_top_cornice:
        add_wall_strip(bm, p1, p2, z1 - 0.50, z1, 0.16, 0.44, mat_idx=mat_sill, cap_top=False, cap_bottom=False)
        add_wall_strip(bm, p1, p2, z1 - 0.20, z1 + 0.16, 0.38, 0.80, mat_idx=mat_frame, cap_top=True, cap_bottom=False)
        if bracketed_cornice:
            n_br = max(3, int(L / 0.85))
            for bi in range(n_br):
                bs = (bi + 0.5) * (L / n_br)
                add_box(bm, (p1[0] + ux * bs + nx * 0.28, p1[1] + uy * bs + ny * 0.28, z1 - 0.35),
                        (0.12, 0.32, 0.34), angle_z=ang, mat_idx=mat_frame, cap_top=False, cap_bottom=False)


def build_chapelle_bonsecours(col_owned, b_chapel, pal):
    """
    Constructs high-poly architectural model of Chapelle Notre-Dame-de-Bon-Secours (400 Rue Saint-Paul Est)
    with rigorous alignment along the primary nave axis:
    - Nave Axis Vector: (ax, ay) = (0.9763, -0.2163) at angle -12.5 deg.
    - Cross Axis Vector: (px, py) = (0.2163, 0.9763) at angle 77.5 deg.
    - Outward Normal of Front Facade: (fnx, fny) = (-0.9763, 0.2163) facing Rue Saint-Paul Est.
    """
    mats = [
        pal["limestone_ashlar_white"],  # 0
        pal["limestone_ashlar_grey"],   # 1
        pal["copper_verdigris"],        # 2
        pal["dark_slate_roof"],         # 3
        pal["window_glass"],            # 4
        pal["window_mullion_white"],    # 5
        pal["chapel_door_red"],         # 6
        pal["gold_gilt"],               # 7
        pal["stone_angel_marble"],      # 8
        pal["cast_iron_black"],         # 9
        pal["granite_curb"]             # 10
    ]
    bm = bmesh.new()

    # Canonical coordinate points for the chapel geometry
    fx_mid, fy_mid = 413.45, 572.30  # Front facade center
    ax, ay = 0.9763, -0.2163          # Nave longitudinal unit vector (front -> rear)
    px, py = 0.2163, 0.9763           # Nave cross unit vector (right -> left looking from front)
    fnx, fny = -ax, -ay               # Outward normal of front facade
    ang_nave = math.atan2(ay, ax)     # -12.5 deg
    ang_cross = math.atan2(py, px)    # 77.5 deg
    wall_h = 15.0                     # Nave wall height
    L_nave = 36.5                     # Length of nave
    hw_nave = 7.6                     # Half-width of nave

    # 1. Nave Base Volume & Buttresses
    # Solid stone core
    pts_core = [
        (fx_mid - px * hw_nave, fy_mid - py * hw_nave),
        (fx_mid - px * hw_nave + ax * L_nave, fy_mid - py * hw_nave + ay * L_nave),
        (fx_mid + px * hw_nave + ax * L_nave, fy_mid + py * hw_nave + ay * L_nave),
        (fx_mid + px * hw_nave, fy_mid + py * hw_nave)
    ]
    add_prism(bm, pts_core, 0.0, wall_h - 0.15, mat_side=0, mat_top=3)

    # Side walls with stone buttresses and tall arched stained-glass windows
    n_side_bays = 7
    bay_len = L_nave / n_side_bays
    for side_sign in (-1.0, 1.0):
        side_nx = px * side_sign
        side_ny = py * side_sign
        ang_side = ang_nave if side_sign < 0 else (ang_nave + math.pi)

        # Exterior wall strip (omit top cap because roof slopes meet wall top at Z=15.1m)
        p_start = (fx_mid + side_nx * hw_nave, fy_mid + side_ny * hw_nave)
        p_end = (p_start[0] + ax * L_nave, p_start[1] + ay * L_nave)
        add_wall_strip(bm, p_start, p_end, 0.0, wall_h, 0.15, 0.40, mat_idx=0, cap_top=False, cap_bottom=False)

        # Buttresses and arched windows (buttresses only on exterior south facade, side_sign < 0)
        for b in range(n_side_bays):
            # Buttress pier (exterior south wall only)
            if side_sign < 0:
                bs_x = p_start[0] + ax * (b * bay_len) + side_nx * 0.45
                bs_y = p_start[1] + ay * (b * bay_len) + side_ny * 0.45
                add_box(bm, (bs_x, bs_y, wall_h * 0.5), (0.75, 0.70, wall_h), angle_z=ang_side, mat_idx=0, cap_top=False, cap_bottom=False)
                # Weathering cap
                add_box(bm, (bs_x, bs_y, wall_h + 0.15), (0.85, 0.80, 0.30), angle_z=ang_side, mat_idx=0)

            # Deeply recessed arched window (recess = 0.50m)
            ws_x = p_start[0] + ax * ((b + 0.5) * bay_len)
            ws_y = p_start[1] + ay * ((b + 0.5) * bay_len)
            win_w = 2.1
            win_z0 = 4.2
            win_z1 = 11.8
            win_h = win_z1 - win_z0

            # Reflective glass recessed by 0.50m
            add_box(bm, (ws_x - side_nx * 0.50, ws_y - side_ny * 0.50, 0.5 * (win_z0 + win_z1)),
                    (win_w, 0.10, win_h), angle_z=ang_side, mat_idx=4)
            # Stone sill
            add_box(bm, (ws_x + side_nx * 0.08, ws_y + side_ny * 0.08, win_z0 - 0.08),
                    (win_w + 0.30, 0.35, 0.18), angle_z=ang_side, mat_idx=0)
            # White mullions
            add_box(bm, (ws_x - side_nx * 0.45, ws_y - side_ny * 0.45, 0.5 * (win_z0 + win_z1)),
                    (0.08, 0.10, win_h), angle_z=ang_side, mat_idx=5)
            add_box(bm, (ws_x - side_nx * 0.45, ws_y - side_ny * 0.45, win_z0 + win_h * 0.52),
                    (win_w, 0.10, 0.08), angle_z=ang_side, mat_idx=5)
            # Arch archivolt
            add_smooth_arch_band(bm, ws_x, ws_y, win_z1 - win_w * 0.48, win_w * 0.46, win_w * 0.44,
                                 0.22, 0.15, -0.30, ax, ay, side_nx, side_ny, segs=16, mat_idx=0)

    # 2. Pitched Slate Nave Roof (Z = 15.0m to Ridge Z = 21.5m)
    # Ridge runs along the nave axis from front gable apex to rear apse
    ridge_start = (fx_mid, fy_mid, 21.5)
    ridge_end = (fx_mid + ax * L_nave, fy_mid + ay * L_nave, 21.5)

    # Left & right roof slope planes
    for side_sign in (-1.0, 1.0):
        eave_start = (fx_mid + px * (side_sign * hw_nave), fy_mid + py * (side_sign * hw_nave), 15.1)
        eave_end = (eave_start[0] + ax * L_nave, eave_start[1] + ay * L_nave, 15.1)

        v_r0 = bm.verts.new(ridge_start)
        v_r1 = bm.verts.new(ridge_end)
        v_e1 = bm.verts.new(eave_end)
        v_e0 = bm.verts.new(eave_start)

        rf = bm.faces.new((v_r0, v_r1, v_e1, v_e0) if side_sign < 0 else (v_r0, v_e0, v_e1, v_r1))
        rf.material_index = 3

    # Verdigris copper ridge capping
    rc_mid = (0.5 * (ridge_start[0] + ridge_end[0]), 0.5 * (ridge_start[1] + ridge_end[1]), 21.6)
    add_box(bm, rc_mid, (L_nave + 0.4, 0.28, 0.20), angle_z=ang_nave, mat_idx=2)

    # 3. Front NW Entrance Facade (Rue Saint-Paul Est / Rue Bonsecours)
    # Front triangular stone gable rising to Z = 21.5m
    v_gable_top = bm.verts.new((fx_mid, fy_mid, 21.5))
    v_gable_left = bm.verts.new((fx_mid + px * hw_nave, fy_mid + py * hw_nave, 15.0))
    v_gable_right = bm.verts.new((fx_mid - px * hw_nave, fy_mid - py * hw_nave, 15.0))
    gf = bm.faces.new((v_gable_top, v_gable_right, v_gable_left))
    gf.material_index = 0

    # Segmented Front Facade Wall: Open bays for windows & central entrance doorway
    # A. Right corner pier (s = -7.6m to -6.2m)
    add_box(bm, (fx_mid + px * (-6.9), fy_mid + py * (-6.9), 7.5), (1.4, 0.45, 15.0), angle_z=ang_cross, mat_idx=0)
    # B. Left corner pier (s = 6.2m to 7.6m)
    add_box(bm, (fx_mid + px * 6.9, fy_mid + py * 6.9, 7.5), (1.4, 0.45, 15.0), angle_z=ang_cross, mat_idx=0)

    # C. Window Bays (Right: s = -5.0m, Left: s = +5.0m)
    for win_s in (-1.0, 1.0):
        fw_x = fx_mid + px * (win_s * 5.0)
        fw_y = fy_mid + py * (win_s * 5.0)
        fwin_w = 2.4
        fwin_z0 = 4.2
        fwin_z1 = 10.8
        fwin_h = fwin_z1 - fwin_z0

        # Stone wall below window (Z = 0.0m to 4.2m)
        add_box(bm, (fw_x, fw_y, 2.1), (fwin_w, 0.45, 4.2), angle_z=ang_cross, mat_idx=0)
        # Stone wall above window (Z = 10.8m to 15.0m)
        add_box(bm, (fw_x, fw_y, 12.9), (fwin_w, 0.45, 4.2), angle_z=ang_cross, mat_idx=0)

        # Reflective glass backing recessed by 0.50m (recess >= 0.45m mandatory)
        add_box(bm, (fw_x - fnx * 0.50, fw_y - fny * 0.50, 0.5 * (fwin_z0 + fwin_z1)),
                (fwin_w - 0.20, 0.10, fwin_h), angle_z=ang_cross, mat_idx=4)
        # Projecting stone sill at Z = 4.2m
        add_box(bm, (fw_x + fnx * 0.08, fw_y + fny * 0.08, fwin_z0 - 0.08),
                (fwin_w + 0.35, 0.38, 0.18), angle_z=ang_cross, mat_idx=0)
        # White timber sash mullions & transoms
        add_box(bm, (fw_x - fnx * 0.45, fw_y - fny * 0.45, 0.5 * (fwin_z0 + fwin_z1)),
                (0.08, 0.10, fwin_h), angle_z=ang_cross, mat_idx=5)
        add_box(bm, (fw_x - fnx * 0.45, fw_y - fny * 0.45, fwin_z0 + fwin_h * 0.52),
                (fwin_w - 0.20, 0.10, 0.08), angle_z=ang_cross, mat_idx=5)
        # Semicircular stone arch archivolt framing window opening
        add_smooth_arch_band(bm, fw_x, fw_y, fwin_z1 - (fwin_w - 0.20) * 0.48, (fwin_w - 0.20) * 0.46, (fwin_w - 0.20) * 0.44,
                             0.24, 0.15, -0.30, px, py, fnx, fny, segs=16, mat_idx=0)

    # D. Central Bay (s = -3.8m to +3.8m)
    # Flanking stone walls next to doorway (s = -2.7m and s = +2.7m)
    add_box(bm, (fx_mid - px * 2.7, fy_mid - py * 2.7, 4.0), (2.2, 0.45, 8.0), angle_z=ang_cross, mat_idx=0)
    add_box(bm, (fx_mid + px * 2.7, fy_mid + py * 2.7, 4.0), (2.2, 0.45, 8.0), angle_z=ang_cross, mat_idx=0)
    # Stone wall above entrance portal (Z = 7.8m to 15.0m)
    add_box(bm, (fx_mid, fy_mid, 11.4), (7.6, 0.45, 7.2), angle_z=ang_cross, mat_idx=0)

    # Projecting Classical Entrance Portico (projecting outward along fnx, fny)
    portico_proj = 1.35
    # Left portico pilaster
    add_box(bm, (fx_mid + px * 2.2 + fnx * (portico_proj * 0.5), fy_mid + py * 2.2 + fny * (portico_proj * 0.5), 3.4),
            (1.2, portico_proj, 6.8), angle_z=ang_cross, mat_idx=0)
    # Right portico pilaster
    add_box(bm, (fx_mid - px * 2.2 + fnx * (portico_proj * 0.5), fy_mid - py * 2.2 + fny * (portico_proj * 0.5), 3.4),
            (1.2, portico_proj, 6.8), angle_z=ang_cross, mat_idx=0)
    # Top entablature spanning pilasters (Z = 4.8m to 6.8m)
    add_box(bm, (fx_mid + fnx * (portico_proj * 0.5), fy_mid + fny * (portico_proj * 0.5), 5.8),
            (5.6, portico_proj, 2.0), angle_z=ang_cross, mat_idx=0)

    # Stepped granite entrance stairs (3 steps leading outward along fnx, fny)
    for st_i in range(3):
        st_z = st_i * 0.16
        st_w = 6.0 - st_i * 0.35
        st_d = 2.4 - st_i * 0.45
        st_x = fx_mid + fnx * (portico_proj + 0.35 + st_i * 0.35)
        st_y = fy_mid + fny * (portico_proj + 0.35 + st_i * 0.35)
        add_box(bm, (st_x, st_y, st_z + 0.08), (st_w, st_d, 0.16), angle_z=ang_cross, mat_idx=10)

    # Grand Arched Doorway with Rich Crimson Double Doors (Mat_Chapel_Door_Red)
    door_x = fx_mid + fnx * 0.10
    door_y = fy_mid + fny * 0.10
    add_box(bm, (door_x, door_y, 1.9), (2.8, 0.15, 3.8), angle_z=ang_cross, mat_idx=6)
    # White radial fanlight transom above door (Z = 3.8m to 4.8m)
    add_box(bm, (door_x, door_y, 4.3), (2.8, 0.12, 1.0), angle_z=ang_cross, mat_idx=4)
    for fa_i in range(5):
        fa_ang = math.pi * (fa_i + 1) / 6.0
        fa_dx = math.cos(fa_ang) * 1.1
        fa_dz = math.sin(fa_ang) * 0.45
        add_box(bm, (door_x + px * fa_dx, door_y + py * fa_dx, 3.8 + fa_dz),
                (0.06, 0.14, 0.9), angle_z=ang_cross, mat_idx=5)
    # Semicircular archivolt framing portal arch
    add_smooth_arch_band(bm, fx_mid + fnx * portico_proj, fy_mid + fny * portico_proj, 3.8, 1.45, 1.0,
                         0.28, 0.15, -portico_proj, px, py, fnx, fny, segs=16, mat_idx=0)

    # Classical Triangular Pediment at Z = 6.8m to 8.2m
    ped_x = fx_mid + fnx * (portico_proj * 0.5)
    ped_y = fy_mid + fny * (portico_proj * 0.5)
    add_box(bm, (ped_x, ped_y, 7.0), (6.0, portico_proj, 0.42), angle_z=ang_cross, mat_idx=0)
    for ra_s in (-1.0, 1.0):
        rax = ped_x + px * (ra_s * 1.5)
        ray = ped_y + py * (ra_s * 1.5)
        add_box(bm, (rax, ray, 7.6), (3.4, 0.38, 0.26), angle_z=ang_cross + ra_s * 0.28, mat_idx=0)

    # Arched stone niche housing the golden statue of Notre-Dame with Child (Mat_Gold_Gilt)
    niche_x = fx_mid + fnx * 0.25
    niche_y = fy_mid + fny * 0.25
    add_box(bm, (niche_x, niche_y, 9.4), (1.8, 0.65, 2.6), angle_z=ang_cross, mat_idx=0)
    add_smooth_arch_band(bm, niche_x, niche_y, 10.4, 0.85, 0.85, 0.20, 0.18, -0.35, px, py, fnx, fny, segs=16, mat_idx=0)
    # Sculpted Golden Statue of Notre-Dame in niche
    add_cylinder(bm, niche_x + fnx * 0.15, niche_y + fny * 0.15, 8.4, 10.2, 0.35, 0.22, segs=12, mat_idx=7)
    add_cylinder(bm, niche_x + fnx * 0.15, niche_y + fny * 0.15, 10.2, 10.7, 0.16, 0.14, segs=10, mat_idx=7)
    add_cylinder(bm, niche_x + fnx * 0.28, niche_y + fny * 0.28, 9.2, 9.9, 0.14, 0.10, segs=8, mat_idx=7)

    # Circular stone rose / oculus window at Z = 13.8m
    oc_x = fx_mid + fnx * 0.20
    oc_y = fy_mid + fny * 0.20
    add_cylinder(bm, oc_x, oc_y, 13.8, 13.9, 1.25, segs=24, mat_idx=4)
    add_cylinder(bm, oc_x, oc_y, 13.7, 14.0, 1.45, 1.45, segs=24, mat_idx=0)

    # Apex stone cross at Z = 21.8m
    add_box(bm, (fx_mid, fy_mid, 22.3), (0.35, 0.35, 1.8), angle_z=ang_cross, mat_idx=0)
    add_box(bm, (fx_mid, fy_mid, 22.6), (1.2, 0.25, 0.30), angle_z=ang_cross, mat_idx=0)

    # Flanking octagonal bell turrets on front corners (left & right)
    for t_sign in (-1.0, 1.0):
        tx = fx_mid + px * (t_sign * 8.0)
        ty = fy_mid + py * (t_sign * 8.0)
        # Stone tower shaft rising to Z = 23.5m
        add_cylinder(bm, tx, ty, 14.0, 23.5, 1.35, 1.30, segs=8, mat_idx=0)
        # Arched belfry openings
        for open_ang in (0.0, math.pi * 0.5, math.pi, math.pi * 1.5):
            ox = tx + math.cos(open_ang) * 1.15
            oy = ty + math.sin(open_ang) * 1.15
            add_box(bm, (ox, oy, 21.5), (0.55, 0.55, 2.2), angle_z=open_ang, mat_idx=9)
        # Copper conical cap and cross
        add_cone(bm, tx, ty, 23.5, 27.2, 1.55, segs=8, mat_idx=2)
        add_box(bm, (tx, ty, 27.8), (0.15, 0.15, 1.2), mat_idx=9)
        add_box(bm, (tx, ty, 28.0), (0.75, 0.12, 0.15), mat_idx=9)

    # 4. Soaring Verdigris Copper Spire & Belfry (Flèche de Bonsecours)
    # Located on the ridge at X = fx_mid + ax * 23.0, Y = fy_mid + ay * 23.0
    sx = fx_mid + ax * 23.0
    sy = fy_mid + ay * 23.0
    # Square base transitioning from roof (Z = 20.0m to 23.5m)
    add_box(bm, (sx, sy, 21.8), (5.0, 5.0, 3.8), angle_z=ang_nave, mat_idx=2)
    # Octagonal belfry plinth (Z = 23.5m to 25.0m)
    add_cylinder(bm, sx, sy, 23.5, 25.0, 2.7, 2.5, segs=8, mat_idx=2)
    # Octagonal louvered lantern belfry (Z = 25.0m to 32.0m)
    add_cylinder(bm, sx, sy, 25.0, 32.0, 2.3, 2.1, segs=8, mat_idx=2)
    for li in range(8):
        lang = 2.0 * math.pi * li / 8.0
        lx = sx + math.cos(lang) * 2.05
        ly = sy + math.sin(lang) * 2.05
        add_box(bm, (lx, ly, 28.5), (0.85, 0.25, 4.2), angle_z=lang, mat_idx=9)
    # Stepped copper balcony & balustrade at Z = 32.0m
    add_cylinder(bm, sx, sy, 32.0, 32.4, 2.65, 2.65, segs=8, mat_idx=2)
    add_cylinder(bm, sx, sy, 32.4, 33.2, 2.60, 2.60, segs=8, mat_idx=9)
    # Octagonal tapering needle spire (Z = 33.2m to 44.5m)
    add_cylinder(bm, sx, sy, 33.2, 44.5, 2.25, 0.25, segs=8, mat_idx=2)
    # Finial ball & gilded cross at apex
    add_cylinder(bm, sx, sy, 44.5, 45.3, 0.45, 0.45, segs=8, mat_idx=7)
    add_box(bm, (sx, sy, 46.2), (0.16, 0.16, 2.2), mat_idx=7)
    add_box(bm, (sx, sy, 46.5), (1.4, 0.12, 0.16), mat_idx=7)

    # 5. Harbor-Facing Statues & Lookout Terrace (Facing Old Port / St. Lawrence River to SE)
    hx = fx_mid + ax * 32.5
    hy = fy_mid + ay * 32.5
    add_box(bm, (hx, hy, 16.5), (4.5, 4.5, 3.0), angle_z=ang_nave, mat_idx=0)
    add_box(bm, (hx, hy, 18.2), (4.8, 4.8, 0.4), angle_z=ang_nave, mat_idx=0)
    add_box(bm, (hx, hy, 18.8), (4.6, 4.6, 0.8), angle_z=ang_nave, mat_idx=9)

    # Monumental Gilded Statue of Notre-Dame (Star of the Sea) facing the harbor with open arms
    add_cylinder(bm, hx, hy, 18.4, 21.0, 0.42, 0.28, segs=12, mat_idx=7)
    add_cylinder(bm, hx, hy, 21.0, 21.6, 0.18, 0.16, segs=10, mat_idx=7)
    # Outstretched blessing arms facing the harbor (heading ~135 deg)
    arm_ang = math.radians(135.0)
    add_box(bm, (hx, hy, 20.3), (1.6, 0.25, 0.35), angle_z=arm_ang + math.pi * 0.5, mat_idx=7)

    # Flanking stone angel statues on pedestals
    for a_sign in (-1.0, 1.0):
        ax_pos = hx + px * (a_sign * 1.6)
        ay_pos = hy + py * (a_sign * 1.6)
        add_box(bm, (ax_pos, ay_pos, 18.6), (0.6, 0.6, 0.8), angle_z=ang_nave, mat_idx=0)
        add_cylinder(bm, ax_pos, ay_pos, 19.0, 20.4, 0.22, 0.16, segs=8, mat_idx=8)

    mesh = bpy.data.meshes.new("Bldg_Chapelle_Bonsecours_Owned_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_Chapelle_Bonsecours_Owned", mesh)
    link_obj(obj, col_owned)


def build_marguerite_bourgeoys_museum(col_owned, b_museum, pal, all_bldgs=None):
    """
    Constructs the Marguerite Bourgeoys Museum complex (osm_id: 87389002),
    a 4-storey rustic coursed ashlar limestone heritage convent building on Rue Bonsecours.
    """
    mats = [
        pal["limestone_rustic_buff"],  # 0
        pal["limestone_ashlar_grey"],   # 1
        pal["dark_slate_roof"],         # 2
        pal["roof_membrane"],           # 3
        pal["window_glass"],            # 4
        pal["window_mullion_white"],    # 5
        pal["copper_verdigris"],        # 6
        pal["cast_iron_black"]          # 7
    ]
    bm = bmesh.new()
    pts = ensure_ccw(b_museum["coords_xy"])
    wall_h = 14.5

    # Core volume inset by 0.35m to guarantee zero Z-fighting with parapets
    core_pts = inset_polygon(pts, 0.35)
    add_prism(bm, core_pts, 0.0, wall_h - 0.25, mat_side=0, mat_top=3)

    # Detailed exterior facade bays with deeply recessed sash windows (>= 0.48m)
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]
        L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if L < 0.2:
            continue
        is_party = is_party_wall(p1, p2, all_bldgs, b_museum["id"])
        if L >= 3.6 and not is_party:
            build_detailed_facade_wall(bm, p1, p2, 0.0, wall_h, bay_w=3.4, floor_h=3.5,
                                       mat_wall=0, mat_glass=4, mat_frame=5, mat_sill=1,
                                       recess=0.48, has_ground_shop=False, arched_windows=True,
                                       bracketed_cornice=True)
        else:
            add_wall_strip(bm, p1, p2, 0.0, wall_h, -0.10, 0.35, mat_idx=0, cap_top=False, cap_bottom=False)

    # Pitched roof mansards & copper dormers along top floor
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    for p in pts[::3]:
        dx, dy = p[0] - cx, p[1] - cy
        dist = math.hypot(dx, dy)
        if dist > 3.0:
            nx, ny = dx / dist, dy / dist
            d_ang = math.atan2(ny, nx)
            add_box(bm, (p[0] - nx * 0.8, p[1] - ny * 0.8, wall_h + 1.2),
                    (1.4, 1.8, 1.6), angle_z=d_ang, mat_idx=6)
            add_box(bm, (p[0] - nx * 0.15, p[1] - ny * 0.15, wall_h + 1.2),
                    (0.9, 0.15, 1.1), angle_z=d_ang, mat_idx=4)

    mesh = bpy.data.meshes.new("Bldg_Marguerite_Bourgeoys_Owned_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_Marguerite_Bourgeoys_Owned", mesh)
    link_obj(obj, col_owned)


def build_pierre_du_calvet(col_owned, b_calvet, pal, all_bldgs=None):
    """
    Constructs Maison Pierre du Calvet (osm_id: 339924180),
    the iconic 1770 French colonial fieldstone residence on Rue Bonsecours with massive firebreak gables,
    twin chimneys, and small rectangular sash windows.
    """
    mats = [
        pal["limestone_rustic_buff"],  # 0
        pal["limestone_ashlar_grey"],   # 1
        pal["dark_slate_roof"],         # 2
        pal["roof_membrane"],           # 3
        pal["window_glass"],            # 4
        pal["window_mullion_dark"],     # 5
        pal["brick_heritage_red"]       # 6
    ]
    bm = bmesh.new()
    pts = ensure_ccw(b_calvet["coords_xy"])
    wall_h = 10.8

    # Core volume inset
    core_pts = inset_polygon(pts, 0.35)
    add_prism(bm, core_pts, 0.0, wall_h - 0.25, mat_side=0, mat_top=3)

    # Deeply recessed small-pane sash windows (recess = 0.50m)
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]
        L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if L < 0.2:
            continue
        is_party = is_party_wall(p1, p2, all_bldgs, b_calvet["id"])
        if L >= 3.5 and not is_party:
            build_detailed_facade_wall(bm, p1, p2, 0.0, wall_h, bay_w=2.8, floor_h=3.4,
                                       mat_wall=0, mat_glass=4, mat_frame=5, mat_sill=1,
                                       recess=0.50, has_ground_shop=False, arched_windows=False,
                                       bracketed_cornice=False)
        else:
            add_wall_strip(bm, p1, p2, 0.0, wall_h, -0.10, 0.35, mat_idx=0, cap_top=False, cap_bottom=False)

    # Parapeted firebreak end gables rising above roofline to Z = 13.5m with twin stone chimneys
    for p in [pts[0], pts[len(pts) // 2]]:
        add_box(bm, (p[0], p[1], wall_h + 1.2), (3.6, 0.8, 2.4), mat_idx=0)
        # Chimney stacks
        add_box(bm, (p[0] + 0.9, p[1], wall_h + 3.2), (0.7, 0.7, 1.8), mat_idx=6)
        add_box(bm, (p[0] - 0.9, p[1], wall_h + 3.2), (0.7, 0.7, 1.8), mat_idx=6)

    mesh = bpy.data.meshes.new("Bldg_Pierre_du_Calvet_Owned_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_Pierre_du_Calvet_Owned", mesh)
    link_obj(obj, col_owned)


def build_all_remaining_owned_buildings(col_owned, dossier, registry, handled_ids, pal):
    """
    Constructs high-poly architectural models for all primary owned buildings in Block MTL-VM-0019
    where is_primary_owner == True in data/building_ownership_registry.json.
    Ensures zero Z-fighting:
    - Roof membranes inset >= 0.15m and vertically offset by >= 0.06m.
    - Deeply recessed (>= 0.45m) window bays with sills, lintels, and mullions.
    """
    mats = [
        pal["limestone_ashlar_white"],  # 0
        pal["limestone_ashlar_grey"],   # 1
        pal["limestone_ashlar_warm"],   # 2
        pal["brick_heritage_red"],      # 3
        pal["brick_brown"],             # 4
        pal["brick_yellow"],            # 5
        pal["brick_dark"],              # 6
        pal["sandstone_red"],           # 7
        pal["stone_tile_facade"],       # 8
        pal["window_glass"],            # 9
        pal["window_mullion_dark"],     # 10
        pal["roof_membrane"],           # 11
        pal["dark_slate_roof"],         # 12
        pal["granite_curb"]             # 13
    ]
    bm = bmesh.new()
    all_bldgs = dossier["osm_features"]["buildings"]

    for b in all_bldgs:
        bid = b["id"]
        bid_str = str(bid)
        # Check ownership registry
        owner = registry.get(bid_str, {}).get("owner_block_id")
        if owner != BLOCK_ID:
            continue
        if bid in handled_ids:
            continue

        pts = ensure_ccw(b.get("coords_xy", []))
        if len(pts) < 3:
            continue

        tags = b.get("tags", {})
        levels_str = str(tags.get("building:levels", "4"))
        try:
            levels = max(2, int(float(levels_str)))
        except ValueError:
            levels = 3 if ("historic" in tags or bid % 2 == 0) else 4
        # Add subtle height variation per building ID so adjacent roofs/cornices never Z-fight
        h = levels * 3.8 + (bid % 7) * 0.18

        # Deterministic material selection across 9 distinct 2K PBR facade materials
        wall_mat_idx = (bid * 3 + 1) % 9

        # Core interior volume inset by 0.35m (guarantees roof membrane is inset >= 0.15m)
        core_pts = inset_polygon(pts, 0.35)
        # Top roof membrane vertically offset by -0.20m below parapet wall top (guarantees |dz| >= 0.06m)
        add_prism(bm, core_pts, 0.0, h - 0.20, mat_side=wall_mat_idx, mat_top=11)

        # Exterior facades
        for i in range(len(pts)):
            p1 = pts[i]
            p2 = pts[(i + 1) % len(pts)]
            L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if L < 0.2:
                continue

            is_party = is_party_wall(p1, p2, all_bldgs, bid)
            if L >= 3.2 and not is_party:
                build_detailed_facade_wall(
                    bm, p1, p2, 0.0, h, bay_w=3.4, floor_h=3.8,
                    mat_wall=wall_mat_idx, mat_glass=9, mat_frame=10, mat_sill=1,
                    recess=0.48, has_ground_shop=(levels >= 3),
                    arched_windows=(levels >= 4 and wall_mat_idx < 3),
                    bracketed_cornice=True
                )
            else:
                # Party wall or narrow return wall (omit top cap to prevent coplanar fighting)
                add_wall_strip(bm, p1, p2, 0.0, h, -0.10, 0.35, mat_idx=wall_mat_idx, cap_top=False, cap_bottom=False)

    mesh = bpy.data.meshes.new("Bldg_MTL_VM_0019_Remaining_Owned_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_MTL_VM_0019_Remaining_Owned", mesh)
    link_obj(obj, col_owned)


def build_streetscape_and_ground(col_owned, dossier, registry, pal):
    """
    Constructs watertight solid ground stratum (Z = -0.25m to -0.02m) with upward (+Z) normals,
    continuous roadbeds (asphalt and Old Montreal granite cobblestone for Rue Saint-Paul and Rue Bonsecours),
    lush green promenade lawns (Z = +0.195m), crushed-stone pathways (Z = +0.255m),
    and micro-stepped raised (+0.15m) granite sidewalks with 3D curbs bordering all buildings.
    """
    mats = [
        pal["street_asphalt"],      # 0
        pal["cobblestone_street"],  # 1
        pal["sidewalk_flagstone"],  # 2
        pal["granite_curb"],        # 3
        pal["white_paint"],         # 4
        pal["yellow_paint"],        # 5
        pal["cast_iron_black"],     # 6
        pal["park_grass"],          # 7
        pal["crushed_stone_path"]   # 8
    ]
    bm = bmesh.new()

    # 1. Watertight Solid Ground Base Stratum (Z = -0.25m to -0.02m)
    # Covering full block bounds [X: 270.0 .. 610.0, Y: 480.0 .. 1060.0]
    add_box(bm, (440.0, 770.0, -0.135), (340.0, 580.0, 0.23), mat_idx=0)

    # 2. Historic Cobblestone & Asphalt Street Sections (micro-stepped Z to prevent coplanar intersection)
    # Rue Saint-Paul Est along front of Chapelle Bonsecours (X: 380..490, Y: 545..575)
    ang_stpaul = math.radians(-16.0)
    add_box(bm, (435.0, 560.0, 0.008), (125.0, 11.5, 0.026), angle_z=ang_stpaul, mat_idx=1)

    # Rue Bonsecours historic canyon running north-south (X: 405..422, Y: 560..680)
    ang_bonsecours = math.radians(72.0)
    add_box(bm, (410.0, 620.0, 0.014), (125.0, 9.5, 0.028), angle_z=ang_bonsecours, mat_idx=1)

    # Rue de la Commune Est / Rue du Quai-de-l'Horloge arterial avenue along east edge
    ang_commune = math.radians(72.0)
    add_box(bm, (466.0, 585.0, 0.005), (160.0, 16.0, 0.022), angle_z=ang_commune, mat_idx=0)

    # Lush green park promenade lawns (Z = +0.195m) & crushed-stone walkways (Z = +0.255m) along east waterfront border
    promenade_lawn_pts = [
        (472.0, 495.0),
        (492.0, 490.0),
        (518.0, 610.0),
        (496.0, 615.0)
    ]
    add_prism(bm, promenade_lawn_pts, -0.01, 0.195, mat_side=3, mat_top=7)
    promenade_path_pts = [
        (465.0, 496.0),
        (473.0, 494.0),
        (497.0, 614.0),
        (489.0, 616.0)
    ]
    add_prism(bm, promenade_path_pts, 0.01, 0.255, mat_side=3, mat_top=8)

    # 3. Continuous Raised Granite Sidewalks (+0.15m) with 3D Curbs and Monotonic Z Micro-Stepping
    all_bldgs = dossier["osm_features"]["buildings"]
    sw_idx = 0
    for b in all_bldgs:
        bid_str = str(b["id"])
        if registry.get(bid_str, {}).get("owner_block_id") != BLOCK_ID:
            continue
        pts = list(b.get("coords_xy", []))
        if len(pts) < 3:
            continue
        sw_idx += 1
        dz = (sw_idx % 85) * 0.0005
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)

        sw_pts, curb_pts = [], []
        for x, y in pts:
            dx, dy = x - cx, y - cy
            d = max(0.1, math.hypot(dx, dy))
            sw_pts.append((x + dx / d * 3.1, y + dy / d * 3.1))
            curb_pts.append((x + dx / d * 3.35, y + dy / d * 3.35))

        # 3D Granite curb stone (non-coplanar micro-stepped Z)
        add_prism(bm, curb_pts, 0.015 + dz, 0.148 + dz, mat_side=3, mat_top=3)
        # Raised flagstone sidewalk slab (strictly above curb top by 0.008m so top caps never coplanar-fight)
        add_prism(bm, sw_pts, 0.020 + dz, 0.156 + dz, mat_side=2, mat_top=2)

    # 4. White Crosswalk Stripes & Yellow Lane Markings at intersections
    for ci in range(-4, 5):
        add_box(bm, (412.0 + ci * 0.9, 568.0, 0.032), (0.45, 3.8, 0.008), angle_z=ang_stpaul, mat_idx=4)
        add_box(bm, (460.0 + ci * 0.9, 555.0, 0.032), (0.45, 3.8, 0.008), angle_z=ang_stpaul, mat_idx=4)

    # 5. Flush Cast-Iron Manhole Covers & Drainage Grates
    add_cylinder(bm, 415.5, 574.0, 0.025, 0.035, 0.38, 0.38, segs=16, mat_idx=6)
    add_cylinder(bm, 440.0, 558.0, 0.025, 0.035, 0.38, 0.38, segs=16, mat_idx=6)

    mesh = bpy.data.meshes.new("MTL_VM_0019_Streetscape_And_Ground_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("MTL_VM_0019_Streetscape_And_Ground", mesh)
    link_obj(obj, col_owned)


_KIT_CACHE = {}


def append_kit_asset(asset_name, col_owned, location, rotation_z=0.0, scale=1.0):
    if not _KIT_CACHE:
        if os.path.isfile(MONTREAL_KIT_PATH):
            with bpy.data.libraries.load(MONTREAL_KIT_PATH, link=False) as (data_from, data_to):
                want = [n for n in ("jacaranda_tree_LOD0", "street_lamp_01", "Master_Street_Bench", "gothic_statue") if n in data_from.objects]
                data_to.objects = want
            for o in data_to.objects:
                if o is not None:
                    _KIT_CACHE[o.name] = o

        fallback_blend = os.path.join(BASE_DIR, "output", "blocks", "MTL-VM-0016.blend")
        if os.path.isfile(fallback_blend):
            with bpy.data.libraries.load(fallback_blend, link=False) as (data_from, data_to):
                rename_map = {}
                for obj_name in data_from.objects:
                    if "Tree" in obj_name and "jacaranda_tree_LOD0" not in _KIT_CACHE and "jacaranda_tree_LOD0" not in rename_map.values():
                        data_to.objects.append(obj_name)
                        rename_map[obj_name] = "jacaranda_tree_LOD0"
                    elif "StreetLamp" in obj_name and "street_lamp_01" not in _KIT_CACHE and "street_lamp_01" not in rename_map.values():
                        data_to.objects.append(obj_name)
                        rename_map[obj_name] = "street_lamp_01"
                    elif "Bench" in obj_name and "Master_Street_Bench" not in _KIT_CACHE and "Master_Street_Bench" not in rename_map.values():
                        data_to.objects.append(obj_name)
                        rename_map[obj_name] = "Master_Street_Bench"
            for o in data_to.objects:
                if o is not None:
                    canonical = rename_map.get(o.name, o.name)
                    _KIT_CACHE[canonical] = o

    src = _KIT_CACHE.get(asset_name)
    if src is None:
        return None
    inst = src.copy()
    inst.location = location
    inst.rotation_euler = (0.0, 0.0, rotation_z)
    inst.scale = (scale, scale, scale)
    link_obj(inst, col_owned)
    return inst


def place_street_furniture_and_trees(col_owned, pal):
    """
    Links high-poly props (street_lamp_01, Master_Street_Bench, jacaranda_tree_LOD0)
    along Rue Saint-Paul Est, Rue Bonsecours, and the Quai-de-l'Horloge promenade, plus curb-parked vehicles.
    """
    # Streetlamp locations along Rue Saint-Paul Est and Rue Bonsecours
    lamp_locs = [
        (409.2, 578.5, 0.16, 140.0),
        (411.5, 565.0, 0.16, 135.0),
        (414.8, 595.0, 0.16, 75.0),
        (418.2, 615.0, 0.16, 75.0),
        (421.5, 635.0, 0.16, 75.0),
        (438.0, 553.0, 0.16, -16.0),
        (455.0, 549.0, 0.16, -16.0),
        (464.5, 545.0, 0.25, -16.0),
        (460.0, 528.0, 0.25, -16.0),
    ]
    for idx, (lx, ly, lz, rot_deg) in enumerate(lamp_locs):
        lamp = append_kit_asset("street_lamp_01", col_owned, (lx, ly, lz), math.radians(rot_deg), 1.0)
        if lamp:
            lamp.name = f"MTL_VM_0019_StreetLamp_{idx:02d}"

    # Street benches in chapel forecourt & promenade
    bench_locs = [
        (411.0, 571.0, 0.16, 140.0),
        (436.5, 551.5, 0.16, -16.0),
        (452.0, 547.0, 0.16, -16.0),
        (467.5, 544.5, 0.26, 72.0),
        (464.5, 532.0, 0.26, 72.0),
    ]
    for idx, (bx, by, bz, rot_deg) in enumerate(bench_locs):
        bench = append_kit_asset("Master_Street_Bench", col_owned, (bx, by, bz), math.radians(rot_deg), 1.0)
        if bench:
            bench.name = f"MTL_VM_0019_Bench_{idx:02d}"

    # Trees along Rue Saint-Paul sidewalk & Quai-de-l'Horloge promenade (seen in Rue_SaintPaulEst_East_Approach.jpg)
    tree_locs = [
        (465.5, 546.0, 0.25, 0.85, 25.0),
        (463.0, 536.0, 0.25, 0.88, 80.0),
        (460.5, 526.0, 0.25, 0.82, 145.0),
        (458.0, 516.0, 0.25, 0.85, 210.0),
        (455.5, 506.0, 0.25, 0.85, 275.0),
        (476.0, 542.0, 0.20, 0.85, 45.0),
        (473.5, 530.0, 0.20, 0.88, 115.0),
        (471.0, 518.0, 0.20, 0.85, 190.0),
        (448.0, 532.0, 0.16, 0.78, 60.0),
        (386.0, 610.0, 0.16, 0.85, 130.0),
    ]
    for idx, (tx, ty, tz, scale, rot_deg) in enumerate(tree_locs):
        tree = append_kit_asset("jacaranda_tree_LOD0", col_owned, (tx, ty, tz), math.radians(rot_deg), scale)
        if tree:
            tree.name = f"MTL_VM_0019_Tree_{idx:02d}"

    # Curbside parked vehicles matching Rue_Bonsecours_South_Canyon.jpg and satellite_topdown.png
    car_mats = [
        pal["cast_iron_black"],   # 0: Dark sedan
        pal["white_paint"],       # 1: White sedan
        pal["granite_curb"],      # 2: Silver sedan
        pal["chapel_door_red"],   # 3: Red car
        pal["window_glass"],      # 4: Cabin glass
    ]
    cbm = bmesh.new()
    parked_cars = [
        # Cars along west curb of Rue Bonsecours (visible in Rue_Bonsecours_South_Canyon.jpg)
        (411.2, 608.0, 72.0, 0),
        (409.5, 601.5, 72.0, 2),
        (407.8, 595.0, 72.0, 1),
        # Cars along Rue Saint-Paul Est & parking lane in satellite_topdown.png
        (454.0, 538.0, 72.0, 0),
        (451.5, 528.0, 72.0, 1),
        (422.0, 618.0, 72.0, 2),
        (424.0, 626.0, 72.0, 3),
    ]
    for cx, cy, ang_deg, b_mat in parked_cars:
        rad = math.radians(ang_deg)
        add_box(cbm, (cx, cy, 0.52), (4.2, 1.82, 0.72), angle_z=rad, mat_idx=b_mat)
        add_box(cbm, (cx, cy, 1.12), (2.2, 1.56, 0.52), angle_z=rad, mat_idx=b_mat)
        add_box(cbm, (cx, cy, 1.12), (2.26, 1.60, 0.44), angle_z=rad, mat_idx=4)

    car_mesh = bpy.data.meshes.new("MTL_VM_0019_Parked_Cars_Mesh")
    cbm.to_mesh(car_mesh)
    cbm.free()
    for cm in car_mats:
        car_mesh.materials.append(cm)
    car_obj = bpy.data.objects.new("MTL_VM_0019_Parked_Cars", car_mesh)
    link_obj(car_obj, col_owned)


def setup_lighting_and_render(col_owned):
    """
    Configures bright daylight sky and 3-sun canyon fill lighting inside col_owned.
    """
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"

    world = bpy.data.worlds.new("MTL_VM_0019_World")
    scene.world = world
    world.use_nodes = True
    wnodes = world.node_tree.nodes
    wlinks = world.node_tree.links
    wnodes.clear()

    w_out = wnodes.new("ShaderNodeOutputWorld")
    w_bg = wnodes.new("ShaderNodeBackground")
    w_bg.inputs["Color"].default_value = (0.52, 0.68, 0.90, 1.0)
    w_bg.inputs["Strength"].default_value = 1.15
    wlinks.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

    # 3-Sun Daylight & Canyon Fill Lighting linked into col_owned
    sun_configs = [
        ("MTL_Owned_Sun_Key", 2.2, 1.2, (48.0, 15.0, -42.0), True),
        ("MTL_Owned_Sun_Fill_North", 0.70, 12.0, (55.0, -20.0, 138.0), False),
        ("MTL_Owned_Sun_Fill_West", 0.58, 15.0, (60.0, 15.0, 48.0), False),
    ]
    for s_name, energy, angle_deg, rot_deg, use_shad in sun_configs:
        sun_data = bpy.data.lights.new(name=s_name, type="SUN")
        sun_data.energy = energy
        sun_data.angle = math.radians(angle_deg)
        if hasattr(sun_data, "use_shadow"):
            sun_data.use_shadow = use_shad
        sun_obj = bpy.data.objects.new(name=s_name, object_data=sun_data)
        sun_obj.rotation_euler = tuple(math.radians(d) for d in rot_deg)
        link_obj(sun_obj, col_owned)


def main():
    skip_render = False
    if "--no-render" in sys.argv:
        skip_render = True

    print(f"Starting Montreal Block {BLOCK_ID} 3D reconstruction...")
    clear_scene()

    # Load dossier and ownership registry
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    # Create hierarchical master and owned collections
    master_col = get_or_create_collection(f"Block_{BLOCK_ID}")
    col_owned = get_or_create_collection(f"Block_{BLOCK_ID}_Owned", parent=master_col)
    pal = create_block_palette()

    handled_ids = set()
    all_bldgs = dossier["osm_features"]["buildings"]

    # 1. Chapelle Notre-Dame-de-Bon-Secours (osm_id: 87389036)
    b_chapel = next((b for b in all_bldgs if b["id"] == 87389036), None)
    if b_chapel:
        print("Constructing Chapelle Notre-Dame-de-Bon-Secours...")
        build_chapelle_bonsecours(col_owned, b_chapel, pal)
        handled_ids.add(87389036)

    # 2. Marguerite Bourgeoys Museum Complex (osm_id: 87389002)
    b_museum = next((b for b in all_bldgs if b["id"] == 87389002), None)
    if b_museum:
        print("Constructing Marguerite Bourgeoys Museum Complex...")
        build_marguerite_bourgeoys_museum(col_owned, b_museum, pal, all_bldgs=all_bldgs)
        handled_ids.add(87389002)

    # 3. Maison Pierre du Calvet (osm_id: 339924180)
    b_calvet = next((b for b in all_bldgs if b["id"] == 339924180), None)
    if b_calvet:
        print("Constructing Maison Pierre du Calvet...")
        build_pierre_du_calvet(col_owned, b_calvet, pal, all_bldgs=all_bldgs)
        handled_ids.add(339924180)

    # 4. All Remaining Primary Owned Buildings (121 buildings)
    print("Constructing remaining primary owned buildings...")
    build_all_remaining_owned_buildings(col_owned, dossier, registry, handled_ids, pal)

    # 5. Watertight Ground Stratum, Streetscape, Sidewalks & Curbs
    print("Constructing ground stratum, cobblestone roadbeds, and granite curbs...")
    build_streetscape_and_ground(col_owned, dossier, registry, pal)

    # 6. Street Furniture & Trees
    print("Linking props, heritage streetlamps, and trees...")
    place_street_furniture_and_trees(col_owned, pal)

    # 7. Lighting
    print("Configuring daylight sky and 3-sun canyon fill lighting...")
    setup_lighting_and_render(col_owned)

    # Ensure no stray collections or objects exist outside Block_MTL-VM-0019
    for c in list(bpy.context.scene.collection.children):
        if c != master_col:
            bpy.context.scene.collection.children.unlink(c)
    for o in list(bpy.context.scene.collection.objects):
        bpy.context.scene.collection.objects.unlink(o)

    # Pack all 2K Poly Haven PBR textures into the .blend file
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"pack_all warning: {e}")

    # 8. Save Clean .blend File
    import shutil
    tmp_blend = BLEND_OUT_PATH + ".tmp.blend"
    for p in (tmp_blend, BLEND_OUT_PATH + "@", BLEND_OUT_PATH + "1", BLEND_OUT_PATH + "2"):
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
    print(f"Successfully generated and saved {BLOCK_ID} -> {BLEND_OUT_PATH}")


if __name__ == "__main__":
    main()
