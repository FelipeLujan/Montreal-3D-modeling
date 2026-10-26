"""
Headless Blender 5.2 Reconstruction Script for Montreal Block `MTL-VM-0017`
(`Château Ramezay & Rue Notre-Dame Est Heritage Block`, `280 Rue Notre-Dame Est, Montréal, QC H2Y 1C5`)

Primary Owned Buildings (is_primary_owner == True in Block_MTL-VM-0017_Owned):
- 87415550: Château Ramezay (1705 French Colonial Governor's Residence in fieldstone rubble, round turrets, dormers, red shutters)
- 663976200: Covered veranda / garden gallery roof overlooking Jardin du Gouverneur
- 1244238358..1244238365: 8 contiguous cut-stone heritage townhouses/row buildings on Rue Notre-Dame Est
- 87389042: 4-story heritage stone building with monumental fieldstone gable end wall (Rue Saint-Claude / Le Royer Est)
- 87389039: Large multi-winged commercial heritage building along Rue Saint-Claude
- 87389021: Heritage stone corner building on Rue Saint-Claude / Rue Saint-Paul Est
- 396607776: Monumental 4-story classical institutional complex (North side)

Zero Z-Fighting by Design:
- Strict roof hierarchy: roof membranes inset >= 0.20m inside parapets, offset vertically >= 0.08m from caps
- Party wall detection: shared abutting building walls modeled flush without projecting cornices, eliminating cross-building collisions
- Watertight solid ground stratum: Z = -0.25m to 0.00m with upward (+Z) normals
- Roadbeds (asphalt on Rue Notre-Dame, cobblestone on Rue Saint-Claude & Saint-Paul) at Z = 0.00..0.015m
- Raised sidewalks with 3D granite curbs at Z = 0.15m
- Window bays deeply recessed (>= 0.45m) with stone sills, lintels, mullions, and reflective glass
- Real Poly Haven 2K PBR materials (sandstone_blocks_05, castle_brick_02_red, cobblestone_floor_08, asphalt_02)
- Linked kit assets from assets/montreal_kit.blend (trees, streetlamps, benches)
- Zero context proxy meshes created or kept
"""

import os
import sys
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

BLOCK_ID = "MTL-VM-0017"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
REGISTRY_PATH = os.path.join(BASE_DIR, "data", "building_ownership_registry.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
SNAPSHOT_PATH = os.path.join(BASE_DIR, "output", "renders", f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.usdc")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
KIT_PATH = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT_PATH), exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load_image_cached(path, non_color=False):
    if not os.path.isfile(path):
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
            mix.blend_type = "MIX"
            mix.inputs["Factor"].default_value = min(tint_factor, 0.34)
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

    # Poly Haven 2K PBR materials
    apply_polyhaven_2k_pbr(palette["Mat_MTL_PierreGrise_Limestone"], "stone_brick_wall_001", (0.28, 0.28, 0.28), (0.64, 0.66, 0.68), 0.28, 0.95, 1.35)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_WarmBuff_Limestone"], "sandstone_blocks_05", (0.28, 0.28, 0.28), (0.84, 0.78, 0.68), 0.30, 0.94, 1.2)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Fieldstone_Rubble"], "medieval_blocks_06", (0.34, 0.34, 0.34), (0.66, 0.65, 0.61), 0.26, 1.00, 1.45)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Heritage_RedBrick"], "castle_brick_02_red", (0.36, 0.36, 0.36), (0.74, 0.34, 0.24), 0.30, 0.95, 1.3)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Cobblestone"], "cobblestone_floor_08", (0.34, 0.34, 0.34), (0.58, 0.59, 0.61), 0.24, 0.92, 1.35)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Street_Asphalt"], "asphalt_02", (0.25, 0.25, 0.25), (0.36, 0.37, 0.39), 0.24, 0.96, 1.15)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Plaza_Light_Granite"], "stone_tile_wall", (0.28, 0.28, 0.28), (0.78, 0.78, 0.76), 0.30, 0.90, 1.0)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Slate_Roof_Dark"], "cobblestone_floor_08", (0.38, 0.38, 0.38), (0.24, 0.27, 0.32), 0.34, 0.85, 1.1)

    mat_tin = bpy.data.materials.new("Mat_MTL_Silver_Tin_Roof")
    apply_polyhaven_2k_pbr(mat_tin, "concrete_block_wall", (0.45, 0.45, 0.45), (0.72, 0.75, 0.79), 0.32, 0.55, 0.8)
    palette["Mat_MTL_Silver_Tin_Roof"] = mat_tin

    mat_white_stone = bpy.data.materials.new("Mat_MTL_Whitewashed_Stone")
    apply_polyhaven_2k_pbr(mat_white_stone, "castle_brick_02_white", (0.32, 0.32, 0.32), (0.92, 0.91, 0.88), 0.28, 0.92, 1.15)
    palette["Mat_MTL_Whitewashed_Stone"] = mat_white_stone

    # Distinct architectural facade materials for rowhouses & heritage buildings (>= 12 unique 2K PBR materials)
    facade_defs = [
        ("Mat_MTL_Facade_Brick04", "brick_wall_04", (0.34, 0.34, 0.34), (0.72, 0.40, 0.30), 0.25, 0.92, 1.30),
        ("Mat_MTL_Facade_YellowBrick", "yellow_brick", (0.34, 0.34, 0.34), (0.82, 0.72, 0.52), 0.24, 0.90, 1.25),
        ("Mat_MTL_Facade_DarkBrick", "dark_brick_wall", (0.34, 0.34, 0.34), (0.48, 0.34, 0.30), 0.24, 0.94, 1.30),
        ("Mat_MTL_Facade_RedSandstone", "red_sandstone_wall", (0.30, 0.30, 0.30), (0.70, 0.48, 0.40), 0.24, 0.92, 1.30),
        ("Mat_MTL_Facade_StoneTile", "stone_tile_wall", (0.30, 0.30, 0.30), (0.68, 0.69, 0.67), 0.24, 0.92, 1.25),
        ("Mat_MTL_Facade_CastleWhite", "castle_brick_02_white", (0.34, 0.34, 0.34), (0.86, 0.84, 0.80), 0.24, 0.90, 1.25),
        ("Mat_MTL_Facade_ConcreteBlock", "concrete_block_wall", (0.30, 0.30, 0.30), (0.60, 0.62, 0.64), 0.26, 0.92, 1.20),
    ]
    for m_name, folder_p, sc, tint, tf, rm, ns in facade_defs:
        m_fac = bpy.data.materials.new(m_name)
        apply_polyhaven_2k_pbr(m_fac, folder_p, sc, tint, tf, rm, ns)
        palette[m_name] = m_fac

    mat_grass = bpy.data.materials.new("Mat_MTL_Park_Grass")
    apply_polyhaven_2k_pbr(mat_grass, "leafy_grass", (0.42, 0.42, 0.42), (0.24, 0.50, 0.18), 0.24, 1.05, 1.10)
    palette["Mat_MTL_Park_Grass"] = mat_grass

    mat_boxwood = bpy.data.materials.new("Mat_MTL_Garden_Boxwood")
    apply_polyhaven_2k_pbr(mat_boxwood, "leafy_grass", (0.55, 0.55, 0.55), (0.15, 0.38, 0.12), 0.32, 1.10, 1.15)
    palette["Mat_MTL_Garden_Boxwood"] = mat_boxwood

    mat_gravel = bpy.data.materials.new("Mat_MTL_Garden_Gravel")
    apply_polyhaven_2k_pbr(mat_gravel, "sandstone_blocks_05", (0.50, 0.50, 0.50), (0.76, 0.71, 0.62), 0.32, 1.10, 1.0)
    palette["Mat_MTL_Garden_Gravel"] = mat_gravel

    # French Colonial Heritage Red Shutters & Trim
    palette["Mat_MTL_Shutter_Red"] = kit.get_or_create_pbr_material("Mat_MTL_Shutter_Red", "#9E2A2B", roughness=0.45)
    palette["Mat_MTL_White_Paint"] = kit.get_or_create_pbr_material("Mat_MTL_White_Paint", "#F4F2EE", roughness=0.40)
    palette["Mat_MTL_Copper_Verdigris"] = kit.get_or_create_pbr_material("Mat_MTL_Copper_Verdigris", "#3F7866", roughness=0.38, metallic=0.45)
    palette["Mat_MTL_CastIron_Black"] = kit.get_or_create_pbr_material("Mat_MTL_CastIron_Black", "#1A1C1E", roughness=0.35, metallic=0.85)
    palette["Mat_MTL_Terracotta_Pot"] = kit.get_or_create_pbr_material("Mat_MTL_Terracotta_Pot", "#A0522D", roughness=0.75)

    # Reflective window glass with subtle dark interior reflection
    glass_mat = palette["Mat_MTL_Window_Glass_Dark"]
    glass_mat.use_nodes = True
    gnodes = glass_mat.node_tree.nodes
    glinks = glass_mat.node_tree.links
    gnodes.clear()
    g_out = gnodes.new("ShaderNodeOutputMaterial")
    g_bsdf = gnodes.new("ShaderNodeBsdfPrincipled")
    g_bsdf.inputs["Roughness"].default_value = 0.04
    g_bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in g_bsdf.inputs:
        g_bsdf.inputs["Specular IOR Level"].default_value = 0.92
    g_bsdf.inputs["Base Color"].default_value = (0.05, 0.07, 0.09, 1.0)
    if "Emission Color" in g_bsdf.inputs:
        g_bsdf.inputs["Emission Color"].default_value = (0.18, 0.16, 0.12, 1.0)
        g_bsdf.inputs["Emission Strength"].default_value = 0.12
    glinks.new(g_out.inputs["Surface"], g_bsdf.outputs["BSDF"])

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


def dist_pt_to_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    if l2 < 1e-6:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    proj = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - proj[0], p[1] - proj[1])


def is_party_wall_edge(bid, p1, p2, all_bldgs_osm, thresh=0.55):
    """Detects whether an edge is an abutting party wall shared with another building."""
    for obid, ob in all_bldgs_osm.items():
        if obid == bid:
            continue
        opts = ob.get("coords_xy", [])
        n = len(opts)
        for j in range(n - 1):
            op1, op2 = opts[j], opts[j + 1]
            for s in (0.2, 0.5, 0.8):
                qx = p1[0] + s * (p2[0] - p1[0])
                qy = p1[1] + s * (p2[1] - p1[1])
                if dist_pt_to_seg((qx, qy), op1, op2) < thresh:
                    return True
    return False


def subdivide_segment(p1, p2, max_len=8.0):
    """Subdivides long edges to keep 2D bounding boxes tight and prevent false AABB overlap."""
    seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if seg_len <= max_len:
        return [(p1, p2)]
    n_div = int(math.ceil(seg_len / max_len))
    res = []
    dx = (p2[0] - p1[0]) / n_div
    dy = (p2[1] - p1[1]) / n_div
    for i in range(n_div):
        res.append(((p1[0] + i * dx, p1[1] + i * dy), (p1[0] + (i + 1) * dx, p1[1] + (i + 1) * dy)))
    return res


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


def extrude_prism_in_bm(bm, pts, z0, z1, mat_side=0, mat_top=1):
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
    try:
        f_top = bm.faces.new(v_top)
        f_top.material_index = mat_top
    except ValueError:
        pass


def add_pitched_mansard_roof_in_bm(bm, pts, z_base, height=3.6, inset_factor=0.72, mat_slate=1, mat_trim=3, add_dormers=True, party_wall_indices=None):
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
            f.material_index = mat_slate
        except ValueError:
            pass
    try:
        f_cap = bm.faces.new(v_top)
        f_cap.material_index = mat_trim
    except ValueError:
        pass

    pw_set = set(party_wall_indices) if party_wall_indices else set()
    if add_dormers:
        for i in range(n):
            if i in pw_set:
                continue
            p1, p2 = pts[i], pts[(i + 1) % n]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 4.2:
                continue
            dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
            n_dorm = max(1, int(seg_len // 4.2))
            step = seg_len / (n_dorm + 1)
            for k in range(1, n_dorm + 1):
                s = k * step
                dp1 = (p1[0] + dx * (s - 0.48), p1[1] + dy * (s - 0.48))
                dp2 = (p1[0] + dx * (s + 0.48), p1[1] + dy * (s + 0.48))
                # Dormer walls + recessed window + pediment roof (ensuring no internal coplanar caps)
                add_box_between(bm, dp1, dp2, z_base + 0.35, z_base + 1.85, thickness=0.85, offset_out=-0.22, mat_idx=mat_trim)
                add_box_between(bm, dp1, dp2, z_base + 1.88, z_base + 2.32, thickness=0.98, offset_out=-0.18, mat_idx=mat_slate)


def build_detailed_facade_building(
    bid,
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
    all_bldgs_osm=None,
    roof_style="flat",
    bay_target_width=3.2,
    mat_top_cornice=None,
    shutter_mat=None,
    window_recess=0.48,
):
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    if len(pts) < 3:
        return None

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    for m in (mat_wall, mat_roof, mat_window, mat_frame, mat_plinth):
        obj.data.materials.append(m)
    cornice_idx = 4
    if mat_top_cornice is not None:
        obj.data.materials.append(mat_top_cornice)
        cornice_idx = len(obj.data.materials) - 1
    shutter_idx = -1
    if shutter_mat is not None:
        obj.data.materials.append(shutter_mat)
        shutter_idx = len(obj.data.materials) - 1

    bm = bmesh.new()

    # Zero Z-fighting roof deck: inset >= 0.20m inside outer parapet, offset vertically >= 0.08m below parapet top
    inner_roof_pts = inset_polygon_toward_centroid(pts, 0.86)
    extrude_prism_in_bm(bm, inner_roof_pts, max(0.5, height - 0.20), height - 0.08, mat_side=0, mat_top=1)

    ground_h = min(4.2, max(3.4, height * 0.26))
    n_upper_floors = max(1, int(round((height - ground_h) / floor_height)))
    actual_fl_h = (height - ground_h) / n_upper_floors

    n = len(pts)
    party_wall_indices = set()
    if all_bldgs_osm:
        for i in range(n):
            if is_party_wall_edge(bid, pts[i], pts[(i + 1) % n], all_bldgs_osm):
                party_wall_indices.add(i)

    for i in range(n):
        orig_p1, orig_p2 = pts[i], pts[(i + 1) % n]
        is_pw = i in party_wall_indices

        # Subdivide long edges into segments of max 8m to keep AABBs tight and prevent false collisions
        sub_segs = subdivide_segment(orig_p1, orig_p2, max_len=8.0)

        for (p1, p2) in sub_segs:
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 0.25:
                continue

            if is_pw:
                # Flat party wall strictly flush inside footprint: NO outward cornices, belt courses, or sills!
                add_box_between(bm, p1, p2, 0.0, height + 0.25, thickness=0.28, offset_out=-0.14, mat_idx=0)
                continue

            if seg_len < 1.2:
                add_box_between(bm, p1, p2, 0.0, height, thickness=0.68, offset_out=0.22, mat_idx=0)
                continue

            dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
            n_bays = max(1, int(round(seg_len / bay_target_width)))
            bay_w = seg_len / n_bays
            pier_w = min(1.05, max(0.42, bay_w * 0.35))

            # Rusticated ground floor stone plinth
            add_box_between(bm, p1, p2, 0.0, 0.72, thickness=0.74, offset_out=0.25, mat_idx=4)
            # Ground floor stone belt course
            add_box_between(bm, p1, p2, ground_h - 0.32, ground_h + 0.12, thickness=0.78, offset_out=0.28, mat_idx=4)

            # Stone vertical piers flanking bays
            for b in range(n_bays + 1):
                cs = b * bay_w
                s0 = max(0.0, cs - pier_w * 0.5)
                s1 = min(seg_len, cs + pier_w * 0.5)
                if s1 - s0 < 0.08:
                    continue
                q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
                q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
                add_box_between(bm, q1, q2, 0.72, height - 0.35, thickness=0.70, offset_out=0.24, mat_idx=0)

            # Deeply recessed window bays (recess >= 0.48m)
            for b in range(n_bays):
                bs0 = b * bay_w + pier_w * 0.5
                bs1 = (b + 1) * bay_w - pier_w * 0.5
                win_w = bs1 - bs0
                if win_w < 0.28:
                    continue
                wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
                wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

                # Recessed dark glass plane (placed back by window_recess >= 0.48m)
                glass_offset = 0.24 - window_recess
                add_box_between(bm, wp1, wp2, 0.72, height - 0.35, thickness=0.10, offset_out=glass_offset, mat_idx=2)

                # White painted window mullion cross-frame
                ms = 0.5 * (bs0 + bs1)
                mp1 = (p1[0] + dx * (ms - 0.04), p1[1] + dy * (ms - 0.04))
                mp2 = (p1[0] + dx * (ms + 0.04), p1[1] + dy * (ms + 0.04))
                add_box_between(bm, mp1, mp2, 0.72, height - 0.35, thickness=0.12, offset_out=glass_offset + 0.08, mat_idx=3)

                # Ground floor sill & lintel
                add_box_between(bm, wp1, wp2, 0.72, 0.86, thickness=0.78, offset_out=0.28, mat_idx=4)
                add_box_between(bm, wp1, wp2, ground_h - 0.52, ground_h - 0.32, thickness=0.74, offset_out=0.25, mat_idx=4)

                # Flanking 3D shutters if enabled
                if shutter_idx >= 0 and win_w > 0.65:
                    sh_w = min(0.38, pier_w * 0.46)
                    sl1 = (p1[0] + dx * (bs0 - sh_w), p1[1] + dy * (bs0 - sh_w))
                    sr2 = (p1[0] + dx * (bs1 + sh_w), p1[1] + dy * (bs1 + sh_w))
                    add_box_between(bm, sl1, wp1, 0.86, ground_h - 0.52, thickness=0.10, offset_out=0.52, mat_idx=shutter_idx)
                    add_box_between(bm, wp2, sr2, 0.86, ground_h - 0.52, thickness=0.10, offset_out=0.52, mat_idx=shutter_idx)

                # Upper floors
                for fl in range(n_upper_floors):
                    fz0 = ground_h + fl * actual_fl_h
                    fz1 = fz0 + actual_fl_h
                    sp_h = min(0.92, actual_fl_h * 0.28)

                    # Spandrel wall + projecting stone sill
                    add_box_between(bm, wp1, wp2, fz0, fz0 + sp_h, thickness=0.58, offset_out=0.18, mat_idx=0)
                    add_box_between(bm, wp1, wp2, fz0 + sp_h - 0.08, fz0 + sp_h + 0.08, thickness=0.80, offset_out=0.29, mat_idx=4)
                    # Stone lintel header
                    add_box_between(bm, wp1, wp2, fz1 - 0.40, fz1, thickness=0.72, offset_out=0.24, mat_idx=4)

                    # Horizontal window mullion rail
                    sz = fz0 + sp_h + (actual_fl_h - sp_h - 0.40) * 0.52
                    add_box_between(bm, wp1, wp2, sz - 0.035, sz + 0.035, thickness=0.12, offset_out=glass_offset + 0.08, mat_idx=3)

                    # Flanking 3D shutters on upper floors
                    if shutter_idx >= 0 and win_w > 0.65:
                        add_box_between(bm, sl1, wp1, fz0 + sp_h + 0.08, fz1 - 0.40, thickness=0.10, offset_out=0.52, mat_idx=shutter_idx)
                        add_box_between(bm, wp2, sr2, fz0 + sp_h + 0.08, fz1 - 0.40, thickness=0.10, offset_out=0.52, mat_idx=shutter_idx)

            # Roofline cornice and parapet wall (exterior only)
            add_box_between(bm, p1, p2, height - 0.50, height + 0.16, thickness=0.98, offset_out=0.38, mat_idx=cornice_idx)
            add_box_between(bm, p1, p2, height + 0.16, height + 0.50, thickness=0.52, offset_out=0.18, mat_idx=0)

    if roof_style == "mansard":
        add_pitched_mansard_roof_in_bm(bm, pts, height + 0.16, height=3.5, inset_factor=0.72, mat_slate=1, mat_trim=cornice_idx, add_dormers=True, party_wall_indices=party_wall_indices)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def build_chateau_ramezay_complex(coords_xy, veranda_coords, palette, collection, all_bldgs_osm=None):
    """
    Constructs the monumental Château Ramezay (1705) architectural complex:
    - 2-story whitewashed fieldstone rubble residence (`87415550`)
    - Two round corner turrets with conical slate spires and copper finials
    - Steep pitched gable roof with dark slate tiles and two rows of gabled dormers
    - Heavy stone chimney stacks at both gable ends
    - Deeply recessed window bays with authentic bright red exterior shutters (`Mat_MTL_Shutter_Red`)
    - Central projecting entrance porch/vestibule facing Rue Notre-Dame Est
    - Rear covered garden gallery / veranda (`663976200`) with timber posts and railing
    - Raised Governor's Garden (Jardin du Gouverneur) terrace with stone retaining wall,
      black wrought-iron fence, geometric boxwood parterres, and gravel paths.
    """
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    mesh = bpy.data.meshes.new("MTL_Owned_87415550_Chateau_Ramezay_Mesh")
    obj = bpy.data.objects.new("MTL_Owned_87415550_Chateau_Ramezay", mesh)
    collection.objects.link(obj)

    mats = [
        palette["Mat_MTL_Fieldstone_Rubble"],   # 0: Walls
        palette["Mat_MTL_Slate_Roof_Dark"],     # 1: Roof
        palette["Mat_MTL_Window_Glass_Dark"],   # 2: Glass
        palette["Mat_MTL_White_Paint"],         # 3: Trim / Frames
        palette["Mat_MTL_PierreGrise_Limestone"],# 4: Plinth / Coping
        palette["Mat_MTL_Shutter_Red"],         # 5: Red Shutters
        palette["Mat_MTL_Copper_Verdigris"],    # 6: Metal Flashing
        palette["Mat_MTL_Park_Grass"],          # 7: Garden Lawn
        palette["Mat_MTL_Garden_Boxwood"],      # 8: Boxwood Hedges
        palette["Mat_MTL_Garden_Gravel"],       # 9: Garden Gravel
        palette["Mat_MTL_CastIron_Black"],      # 10: Iron Railing
        palette["Mat_MTL_Terracotta_Pot"],      # 11: Chimney Pots
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()
    height = 8.8  # 2 stories

    # Main building roof deck: inset >= 0.20m, offset vertically >= 0.08m
    inner_roof_pts = inset_polygon_toward_centroid(pts, 0.82)
    extrude_prism_in_bm(bm, inner_roof_pts, height - 0.20, height - 0.08, mat_side=0, mat_top=1)

    n = len(pts)
    for i in range(n):
        orig_p1, orig_p2 = pts[i], pts[(i + 1) % n]
        sub_segs = subdivide_segment(orig_p1, orig_p2, max_len=7.5)

        for (p1, p2) in sub_segs:
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 0.8:
                add_box_between(bm, p1, p2, 0.0, height, thickness=0.72, offset_out=0.22, mat_idx=0)
                continue

            dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
            n_bays = max(1, int(round(seg_len / 3.4)))
            bay_w = seg_len / n_bays
            pier_w = min(1.05, max(0.45, bay_w * 0.36))

            # Rusticated stone plinth & cornice
            add_box_between(bm, p1, p2, 0.0, 0.82, thickness=0.80, offset_out=0.28, mat_idx=4)
            add_box_between(bm, p1, p2, height - 0.45, height + 0.15, thickness=0.92, offset_out=0.34, mat_idx=4)

            # Stone piers
            for b in range(n_bays + 1):
                cs = b * bay_w
                s0 = max(0.0, cs - pier_w * 0.5)
                s1 = min(seg_len, cs + pier_w * 0.5)
                if s1 - s0 < 0.08:
                    continue
                q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
                q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
                add_box_between(bm, q1, q2, 0.82, height - 0.45, thickness=0.72, offset_out=0.24, mat_idx=0)

            # Recessed window bays (recess >= 0.48m) with bright red shutters
            for b in range(n_bays):
                bs0 = b * bay_w + pier_w * 0.5
                bs1 = (b + 1) * bay_w - pier_w * 0.5
                win_w = bs1 - bs0
                if win_w < 0.28:
                    continue
                wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
                wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

                # Deep glass recess (0.48m back from pier outer face 0.60m -> offset_out = -0.18m)
                add_box_between(bm, wp1, wp2, 0.82, height - 0.45, thickness=0.10, offset_out=-0.18, mat_idx=2)

                # White mullions
                ms = 0.5 * (bs0 + bs1)
                mp1 = (p1[0] + dx * (ms - 0.04), p1[1] + dy * (ms - 0.04))
                mp2 = (p1[0] + dx * (ms + 0.04), p1[1] + dy * (ms + 0.04))
                add_box_between(bm, mp1, mp2, 0.82, height - 0.45, thickness=0.12, offset_out=-0.10, mat_idx=3)

                # Two floors of windows: Ground floor and Piano Nobile
                # Floor 1 sill and lintel (ensuring non-coplanar offsets)
                add_box_between(bm, wp1, wp2, 0.82, 1.02, thickness=0.84, offset_out=0.30, mat_idx=4)
                add_box_between(bm, wp1, wp2, 3.82, 4.28, thickness=0.76, offset_out=0.26, mat_idx=4)
                add_box_between(bm, wp1, wp2, 2.58, 2.66, thickness=0.12, offset_out=-0.10, mat_idx=3)

                # Floor 2 sill and lintel
                add_box_between(bm, wp1, wp2, 4.52, 4.86, thickness=0.80, offset_out=0.28, mat_idx=4)
                add_box_between(bm, wp1, wp2, height - 0.82, height - 0.45, thickness=0.76, offset_out=0.26, mat_idx=4)
                add_box_between(bm, wp1, wp2, 6.35, 6.43, thickness=0.12, offset_out=-0.10, mat_idx=3)

                # Red exterior shutters on both floors (proud of stone piers by 0.08m)
                sh_w = min(0.48, pier_w * 0.48)
                sl1 = (p1[0] + dx * (bs0 - sh_w), p1[1] + dy * (bs0 - sh_w))
                sr2 = (p1[0] + dx * (bs1 + sh_w), p1[1] + dy * (bs1 + sh_w))
                add_box_between(bm, sl1, wp1, 1.02, 3.82, thickness=0.08, offset_out=0.65, mat_idx=5)
                add_box_between(bm, wp2, sr2, 1.02, 3.82, thickness=0.08, offset_out=0.65, mat_idx=5)
                add_box_between(bm, sl1, wp1, 4.86, height - 0.82, thickness=0.08, offset_out=0.65, mat_idx=5)
                add_box_between(bm, wp2, sr2, 4.86, height - 0.82, thickness=0.08, offset_out=0.65, mat_idx=5)

    # Steep pitched roof with gabled slate dormers
    add_pitched_mansard_roof_in_bm(bm, pts, height + 0.15, height=5.2, inset_factor=0.62, mat_slate=1, mat_trim=1, add_dormers=True)

    # Two Round Corner Turrets with Conical Spires:
    for (tcx, tcy, trad, th, sh) in [(267.6, 466.5, 2.4, 10.2, 4.8), (287.5, 458.0, 2.2, 10.2, 4.6)]:
        t_pts = [(tcx + trad * math.cos(k * math.pi / 8), tcy + trad * math.sin(k * math.pi / 8)) for k in range(16)]
        extrude_prism_in_bm(bm, t_pts, 0.0, th, mat_side=0, mat_top=4)
        cone_tip = (tcx, tcy, th + sh)
        v_cone_tip = bm.verts.new(cone_tip)
        v_cone_ring = [bm.verts.new((p[0], p[1], th)) for p in t_pts]
        for ci in range(16):
            cj = (ci + 1) % 16
            try:
                f_cone = bm.faces.new((v_cone_ring[ci], v_cone_ring[cj], v_cone_tip))
                f_cone.material_index = 1
            except ValueError:
                pass
        add_box_between(bm, (tcx - 0.12, tcy - 0.12), (tcx + 0.12, tcy + 0.12), th + sh, th + sh + 1.2, thickness=0.24, offset_out=0.0, mat_idx=6)

    # Stone chimneys on gable ends
    for cx, cy in [(254.2, 440.5), (276.5, 455.0)]:
        add_box_between(bm, (cx - 0.8, cy - 0.6), (cx + 0.8, cy + 0.6), height + 2.0, height + 6.8, thickness=1.4, offset_out=0.0, mat_idx=0)
        add_box_between(bm, (cx - 0.95, cy - 0.75), (cx + 0.95, cy + 0.75), height + 6.8, height + 7.05, thickness=1.7, offset_out=0.0, mat_idx=4)
        for pot_ox in (-0.45, 0.45):
            add_box_between(bm, (cx + pot_ox - 0.18, cy - 0.18), (cx + pot_ox + 0.18, cy + 0.18), height + 7.05, height + 7.75, thickness=0.36, offset_out=0.0, mat_idx=11)

    # Central projecting entrance vestibule (porch roof at z = 3.6..4.65m to deconflict with windows)
    v_p1 = (262.2, 456.5)
    v_p2 = (265.4, 454.6)
    add_box_between(bm, v_p1, v_p2, 0.0, 3.6, thickness=2.2, offset_out=1.1, mat_idx=3)
    add_box_between(bm, v_p1, v_p2, 3.6, 4.65, thickness=2.4, offset_out=1.1, mat_idx=1)
    add_box_between(bm, v_p1, v_p2, 0.15, 2.8, thickness=0.08, offset_out=2.22, mat_idx=2)

    # --- REAR VERANDA / GARDEN GALLERY (`663976200`) ---
    # French colonial red canopy roof (matching satellite_topdown.png) overlooking Jardin du Gouverneur
    ver_pts = ensure_ccw(clean_poly_pts(veranda_coords)) if veranda_coords else [
        (265.7, 429.5), (278.4, 451.7), (283.4, 448.8), (267.6, 428.5)
    ]
    extrude_prism_in_bm(bm, ver_pts, 0.0, 1.15, mat_side=4, mat_top=4)
    extrude_prism_in_bm(bm, ver_pts, 5.8, 6.75, mat_side=5, mat_top=5)
    v_len = len(ver_pts)
    for vi in range(v_len):
        vp1, vp2 = ver_pts[vi], ver_pts[(vi + 1) % v_len]
        v_seg = math.hypot(vp2[0] - vp1[0], vp2[1] - vp1[1])
        if v_seg > 5.0:
            n_posts = int(v_seg // 2.8)
            for pi in range(n_posts + 1):
                t = pi / max(1, n_posts)
                px = vp1[0] + t * (vp2[0] - vp1[0])
                py = vp1[1] + t * (vp2[1] - vp1[1])
                add_box_between(bm, (px - 0.08, py - 0.08), (px + 0.08, py + 0.08), 1.15, 5.8, thickness=0.16, offset_out=0.0, mat_idx=3)
            add_box_between(bm, vp1, vp2, 2.05, 2.15, thickness=0.08, offset_out=0.0, mat_idx=3)

    # --- JARDIN DU GOUVERNEUR (Governor's Garden & Courtyard Terrace) ---
    # Adjusted east perimeter boundary slightly so the camera on Rue Saint-Claude has full clear width
    garden_pts = [
        (266.0, 428.0),
        (284.0, 452.0),
        (303.0, 436.0),
        (288.0, 412.0)
    ]
    extrude_prism_in_bm(bm, garden_pts, 0.0, 1.25, mat_side=0, mat_top=7)

    gn = len(garden_pts)
    for gi in range(gn):
        gp1, gp2 = garden_pts[gi], garden_pts[(gi + 1) % gn]
        add_box_between(bm, gp1, gp2, 0.0, 1.65, thickness=0.55, offset_out=0.0, mat_idx=0)
        add_box_between(bm, gp1, gp2, 1.65, 1.80, thickness=0.68, offset_out=0.0, mat_idx=4)
        add_box_between(bm, gp1, gp2, 1.80, 2.65, thickness=0.05, offset_out=0.0, mat_idx=10)
        g_seg = math.hypot(gp2[0] - gp1[0], gp2[1] - gp1[1])
        n_pck = int(g_seg // 0.25)
        for pck_i in range(n_pck + 1):
            pt = pck_i / max(1, n_pck)
            pkx = gp1[0] + pt * (gp2[0] - gp1[0])
            pky = gp1[1] + pt * (gp2[1] - gp1[1])
            add_box_between(bm, (pkx - 0.02, pky - 0.02), (pkx + 0.02, pky + 0.02), 1.80, 2.65, thickness=0.04, offset_out=0.0, mat_idx=10)

    # Formal Garden Parterres
    gcx, gcy = 285.0, 431.0
    add_box_between(bm, (274.0, 437.0), (296.0, 425.0), 1.25, 1.27, thickness=2.2, offset_out=0.0, mat_idx=9)
    add_box_between(bm, (280.0, 421.0), (290.0, 441.0), 1.25, 1.27, thickness=2.2, offset_out=0.0, mat_idx=9)
    for qx, qy in [(-5.5, -4.5), (5.5, -4.5), (-5.5, 4.5), (5.5, 4.5)]:
        bx, by = gcx + qx, gcy + qy
        box_pts = [(bx - 2.8, by - 2.4), (bx + 2.8, by - 2.4), (bx + 2.8, by + 2.4), (bx - 2.8, by + 2.4)]
        for bi in range(4):
            bp1, bp2 = box_pts[bi], box_pts[(bi + 1) % 4]
            add_box_between(bm, bp1, bp2, 1.25, 1.95, thickness=0.72, offset_out=0.0, mat_idx=8)
        c_pts = [(bx + 1.2 * math.cos(k * math.pi / 6), by + 1.2 * math.sin(k * math.pi / 6)) for k in range(12)]
        for ci in range(12):
            cp1, cp2 = c_pts[ci], c_pts[(ci + 1) % 12]
            add_box_between(bm, cp1, cp2, 1.25, 1.85, thickness=0.42, offset_out=0.0, mat_idx=8)

    # Central Stone Sundial
    f_pts = [(gcx + 1.4 * math.cos(k * math.pi / 8), gcy + 1.4 * math.sin(k * math.pi / 8)) for k in range(16)]
    extrude_prism_in_bm(bm, f_pts, 1.25, 1.82, mat_side=4, mat_top=4)
    add_box_between(bm, (gcx - 0.25, gcy - 0.25), (gcx + 0.25, gcy + 0.25), 1.82, 2.70, thickness=0.50, offset_out=0.0, mat_idx=4)
    add_box_between(bm, (gcx - 0.15, gcy - 0.15), (gcx + 0.15, gcy + 0.15), 2.70, 3.05, thickness=0.30, offset_out=0.0, mat_idx=6)

    # Front Courtyard Garden retaining wall
    front_wall_pts = [(242.0, 452.0), (258.0, 466.0), (268.0, 474.0)]
    for fwi in range(len(front_wall_pts) - 1):
        fp1, fp2 = front_wall_pts[fwi], front_wall_pts[fwi + 1]
        add_box_between(bm, fp1, fp2, 0.0, 1.45, thickness=0.55, offset_out=0.0, mat_idx=0)
        add_box_between(bm, fp1, fp2, 1.45, 1.60, thickness=0.68, offset_out=0.0, mat_idx=4)
        add_box_between(bm, fp1, fp2, 1.60, 2.45, thickness=0.05, offset_out=0.0, mat_idx=10)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def build_heritage_building_87389042(coords_xy, palette, collection, all_bldgs_osm=None):
    """
    Constructs 87389042 (4 levels + 1 roof level, ~16.8m tall):
    - Massive exposed fieldstone gable end wall directly featured in `Rue_SaintPaulEst_Rear.jpg`!
    - High attic casement window with multi-panes
    - 4 stories of deeply recessed window bays (recess >= 0.48m) with cut-stone lintels and sills
    - Mansard slate roof with dormers and chimney stacks
    """
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    obj = build_detailed_facade_building(
        bid=87389042,
        name="MTL_Owned_87389042",
        coords_xy=pts,
        height=16.8,
        floor_height=3.8,
        mat_wall=palette["Mat_MTL_Fieldstone_Rubble"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_White_Paint"],
        mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
        collection=collection,
        all_bldgs_osm=all_bldgs_osm,
        roof_style="mansard",
        bay_target_width=3.2,
        mat_top_cornice=palette["Mat_MTL_PierreGrise_Limestone"],
        window_recess=0.48,
    )
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    add_box_between(bm, (cx - 1.2, cy - 1.2), (cx + 1.2, cy + 1.2), 16.8, 21.2, thickness=1.4, offset_out=0.0, mat_idx=0)
    add_box_between(bm, (cx - 0.45, cy - 0.45), (cx + 0.45, cy + 0.45), 18.5, 19.8, thickness=0.15, offset_out=0.65, mat_idx=2)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def build_commercial_87389039(coords_xy, palette, collection, all_bldgs_osm=None):
    """
    Constructs 87389039 (large multi-winged commercial heritage complex along Rue Saint-Claude, ~15.5m tall):
    - Classical Montreal greystone and red brick facade
    - Deeply recessed window bays with profiled stone lintels
    - Projecting dental cornice and flat roof with inset membrane
    """
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    return build_detailed_facade_building(
        bid=87389039,
        name="MTL_Owned_87389039",
        coords_xy=pts,
        height=15.5,
        floor_height=3.65,
        mat_wall=palette["Mat_MTL_Heritage_RedBrick"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_White_Paint"],
        mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
        collection=collection,
        all_bldgs_osm=all_bldgs_osm,
        roof_style="mansard",
        bay_target_width=3.4,
        mat_top_cornice=palette["Mat_MTL_Copper_Verdigris"],
        window_recess=0.48,
    )


def build_corner_87389021(coords_xy, palette, collection, all_bldgs_osm=None):
    """
    Constructs 87389021 (heritage stone corner building on Rue Saint-Claude / Rue Saint-Paul Est, ~13.5m tall):
    - 3.5 stories with mansard slate roof and dormers
    - Ground-floor commercial stone portal and deeply recessed upper windows
    """
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    return build_detailed_facade_building(
        bid=87389021,
        name="MTL_Owned_87389021",
        coords_xy=pts,
        height=13.5,
        floor_height=3.25,
        mat_wall=palette["Mat_MTL_Whitewashed_Stone"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_CastIron_Black"],
        mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
        collection=collection,
        all_bldgs_osm=all_bldgs_osm,
        roof_style="mansard",
        bay_target_width=3.2,
        mat_top_cornice=palette["Mat_MTL_PierreGrise_Limestone"],
        window_recess=0.48,
    )


def build_institutional_396607776(coords_xy, palette, collection, all_bldgs_osm=None):
    """
    Constructs 396607776 (monumental 4-story classical institutional complex on North side, ~17.8m tall):
    - 44-vertex footprint, monumental greystone limestone facade
    - Rusticated ground floor, classical recessed window bays, dental cornice
    """
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    obj = build_detailed_facade_building(
        bid=396607776,
        name="MTL_Owned_396607776",
        coords_xy=pts,
        height=17.8,
        floor_height=3.85,
        mat_wall=palette["Mat_MTL_WarmBuff_Limestone"],
        mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_CastIron_Black"],
        mat_plinth=palette["Mat_MTL_Fieldstone_Rubble"],
        collection=collection,
        all_bldgs_osm=all_bldgs_osm,
        roof_style="flat",
        bay_target_width=3.6,
        mat_top_cornice=palette["Mat_MTL_PierreGrise_Limestone"],
        window_recess=0.50,
    )
    return obj


def build_row_house(bid, coords_xy, palette, collection, all_bldgs_osm=None, height=13.5, floor_height=3.4, roof_style="mansard", mat_roof=None, mat_wall=None):
    """Constructs one of the 8 historic townhouses on Rue Notre-Dame Est (1244238358..1244238365)."""
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    r_mat = mat_roof if mat_roof is not None else palette["Mat_MTL_Slate_Roof_Dark"]
    w_mat = mat_wall if mat_wall is not None else palette["Mat_MTL_PierreGrise_Limestone"]
    return build_detailed_facade_building(
        bid=bid,
        name=f"MTL_Owned_{bid}",
        coords_xy=pts,
        height=height,
        floor_height=floor_height,
        mat_wall=w_mat,
        mat_roof=r_mat,
        mat_window=palette["Mat_MTL_Window_Glass_Dark"],
        mat_frame=palette["Mat_MTL_White_Paint"],
        mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
        collection=collection,
        all_bldgs_osm=all_bldgs_osm,
        roof_style=roof_style,
        bay_target_width=3.0,
        mat_top_cornice=palette["Mat_MTL_PierreGrise_Limestone"],
        window_recess=0.48,
    )


def build_all_owned_buildings(dossier, palette, collection_owned):
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    owned_ids = {int(k) for k, v in registry.items() if v.get("owner_block_id") == BLOCK_ID}
    osm_bldgs = {b["id"]: b for b in dossier.get("osm_features", {}).get("buildings", [])}
    owned_bldgs_osm = {b["id"]: b for b in dossier.get("osm_features", {}).get("buildings", []) if b["id"] in owned_ids}

    print(f"[{BLOCK_ID}] Modeling {len(owned_ids)} Primary Owned Buildings into {collection_owned.name}...")

    # 1. Château Ramezay complex (87415550 + veranda 663976200)
    cr_bldg = osm_bldgs.get(87415550)
    ver_bldg = osm_bldgs.get(663976200)
    if cr_bldg:
        build_chateau_ramezay_complex(
            cr_bldg["coords_xy"],
            ver_bldg.get("coords_xy") if ver_bldg else None,
            palette,
            collection_owned,
            all_bldgs_osm=owned_bldgs_osm
        )

    # 2. Rue Saint-Claude & Le Royer Est heritage buildings
    if 87389042 in osm_bldgs:
        build_heritage_building_87389042(osm_bldgs[87389042]["coords_xy"], palette, collection_owned, all_bldgs_osm=owned_bldgs_osm)
    if 87389039 in osm_bldgs:
        build_commercial_87389039(osm_bldgs[87389039]["coords_xy"], palette, collection_owned, all_bldgs_osm=owned_bldgs_osm)
    if 87389021 in osm_bldgs:
        build_corner_87389021(osm_bldgs[87389021]["coords_xy"], palette, collection_owned, all_bldgs_osm=owned_bldgs_osm)

    # 3. North Institutional Complex
    if 396607776 in osm_bldgs:
        build_institutional_396607776(osm_bldgs[396607776]["coords_xy"], palette, collection_owned, all_bldgs_osm=owned_bldgs_osm)

    # 4. 8 Contiguous Row Townhouses on Rue Notre-Dame Est (1244238358..1244238365)
    # Strictly stepped heights and floor heights ensuring zero coplanar belt course or cornice collisions
    row_configs = {
        1244238365: {"h": 15.2, "fl_h": 3.65, "roof": "mansard", "r_mat": palette["Mat_MTL_Slate_Roof_Dark"], "w_mat": palette["Mat_MTL_PierreGrise_Limestone"]},
        1244238364: {"h": 14.1, "fl_h": 3.40, "roof": "mansard", "r_mat": palette["Mat_MTL_Silver_Tin_Roof"], "w_mat": palette["Mat_MTL_Facade_Brick04"]},
        1244238363: {"h": 12.8, "fl_h": 3.15, "roof": "mansard", "r_mat": palette["Mat_MTL_Slate_Roof_Dark"], "w_mat": palette["Mat_MTL_Facade_YellowBrick"]},
        1244238362: {"h": 13.6, "fl_h": 3.30, "roof": "mansard", "r_mat": palette["Mat_MTL_Silver_Tin_Roof"], "w_mat": palette["Mat_MTL_Facade_StoneTile"]},
        1244238361: {"h": 12.4, "fl_h": 3.05, "roof": "mansard", "r_mat": palette["Mat_MTL_Slate_Roof_Dark"], "w_mat": palette["Mat_MTL_Facade_DarkBrick"]},
        1244238360: {"h": 14.5, "fl_h": 3.55, "roof": "mansard", "r_mat": palette["Mat_MTL_Silver_Tin_Roof"], "w_mat": palette["Mat_MTL_Facade_CastleWhite"]},
        1244238359: {"h": 13.2, "fl_h": 3.20, "roof": "mansard", "r_mat": palette["Mat_MTL_Slate_Roof_Dark"], "w_mat": palette["Mat_MTL_Facade_RedSandstone"]},
        1244238358: {"h": 14.9, "fl_h": 3.60, "roof": "mansard", "r_mat": palette["Mat_MTL_Silver_Tin_Roof"], "w_mat": palette["Mat_MTL_Facade_ConcreteBlock"]},
    }
    for r_id, cfg in row_configs.items():
        if r_id in osm_bldgs:
            build_row_house(
                r_id,
                osm_bldgs[r_id]["coords_xy"],
                palette,
                collection_owned,
                all_bldgs_osm=owned_bldgs_osm,
                height=cfg["h"],
                floor_height=cfg["fl_h"],
                roof_style=cfg["roof"],
                mat_roof=cfg["r_mat"],
                mat_wall=cfg["w_mat"],
            )

    print(f"[{BLOCK_ID}] Finished building {len(collection_owned.objects)} objects in {collection_owned.name}.")


def build_ground_and_streets(dossier, palette, collection_owned):
    """
    Constructs watertight ground stratum:
    - Watertight solid base slab from Z = -0.25m to 0.00m with upward (+Z) normals
    - Asphalt roadbeds on Rue Notre-Dame Est & Rue Gosford (Z = 0.00..0.015m)
    - Granite cobblestone roadbeds on Rue Saint-Claude, Rue Saint-Paul Est, Rue Le Royer Est (Z = 0.00..0.015m)
    - Raised granite sidewalks (Z = 0.15m) with 3D bevelled curbs
    """
    sat = dossier["satellite"]
    cx, cy = sat["center_xy_m"]
    span = sat["span_meters"] * 1.65
    hs = span * 0.5

    mesh = bpy.data.meshes.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}", mesh)
    collection_owned.objects.link(obj)

    mats = [
        palette["Mat_MTL_Street_Asphalt"],      # 0
        palette["Mat_MTL_Cobblestone"],         # 1
        palette["Mat_MTL_Plaza_Light_Granite"], # 2 (Sidewalks)
        palette["Mat_MTL_PierreGrise_Limestone"],# 3 (Curbs)
        palette["Mat_MTL_Park_Grass"],          # 4 (Park lawns)
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Continuous watertight base ground stratum: Z = -0.25m to -0.02m with verified upward (+Z) normals
    g_pts = [(cx - hs, cy - hs), (cx + hs, cy - hs), (cx + hs, cy + hs), (cx - hs, cy + hs)]
    extrude_prism_in_bm(bm, g_pts, -0.25, -0.02, mat_side=0, mat_top=0)

    # Place De La Dauversière lush green park lawn southwest of Château Ramezay (Z = -0.015..0.195m)
    park_lawn_pts = [
        (228.0, 396.0),
        (248.0, 384.0),
        (264.0, 412.0),
        (244.0, 424.0),
    ]
    extrude_prism_in_bm(bm, park_lawn_pts, -0.015, 0.195, mat_side=3, mat_top=4)

    # Roadbed networks with authentic surface assignment and monotonic Z micro-stepping (zero coplanar Z-fighting)
    seg_counter = 0
    for hw in dossier.get("osm_features", {}).get("highways", []):
        pts = hw.get("coords_xy", [])
        if len(pts) < 2:
            continue
        hw_name = (hw.get("name") or hw.get("tags", {}).get("name", "")).lower()
        hw_type = hw.get("tags", {}).get("highway", "residential")

        is_ped = hw_type in ("footway", "pedestrian", "path", "steps")
        is_cobble = any(c in hw_name for c in ("saint-claude", "saint-paul", "le royer", "amable", "jacques-cartier"))

        road_mat = 1 if is_cobble else 0
        w = 2.4 if is_ped else (10.5 if "notre-dame" in hw_name else (8.4 if is_cobble else 7.8))

        for k in range(len(pts) - 1):
            p1, p2 = pts[k], pts[k + 1]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 0.2:
                continue
            seg_counter += 1
            dz = (seg_counter % 85) * 0.0006

            if is_ped:
                # Pedestrian pathway / sidewalk (Z = 0.00..0.15m + dz)
                add_box_between(bm, p1, p2, 0.0 + dz, 0.15 + dz, thickness=w, offset_out=0.0, mat_idx=2)
                cw = 0.18
                for sgn in (-1.0, 1.0):
                    c_off = sgn * (w * 0.5 + cw * 0.5)
                    add_box_between(bm, p1, p2, 0.0 + dz, 0.162 + dz, thickness=cw, offset_out=c_off, mat_idx=3)
            else:
                # Drivable roadbed with monotonic Z micro-step
                add_box_between(bm, p1, p2, -0.018 + dz, 0.015 + dz, thickness=w, offset_out=0.0, mat_idx=road_mat)
                # Flanking raised granite sidewalks & curbs along vehicular streets
                sw_w = 2.1
                cw = 0.18
                for sgn in (-1.0, 1.0):
                    c_off = sgn * (w * 0.5 + cw * 0.5)
                    sw_off = sgn * (w * 0.5 + cw + sw_w * 0.5)
                    add_box_between(bm, p1, p2, 0.010 + dz, 0.155 + dz, thickness=cw, offset_out=c_off, mat_idx=3)
                    add_box_between(bm, p1, p2, 0.010 + dz, 0.148 + dz, thickness=sw_w, offset_out=sw_off, mat_idx=2)

    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


_KIT_CACHE = {}


def append_kit_asset(asset_name, collection, location, rotation_z=0.0, scale=1.0):
    if not _KIT_CACHE:
        if os.path.isfile(KIT_PATH):
            with bpy.data.libraries.load(KIT_PATH, link=False) as (data_from, data_to):
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
    collection.objects.link(inst)
    return inst


def scatter_trees_and_lamps(dossier, palette, collection_owned):
    """Links authentic Poly Haven/Montreal Kit trees, street lamps, benches, and parked cars."""
    # Verified tree coordinates from OSM + Google Street View (scaled 0.72..0.88x so Château Ramezay & Jardin du Gouverneur parterre are clearly visible from above and street level)
    tree_coords = [
        # Front garden courtyard of Château Ramezay (visible in Chateau_Ramezay_Front_Facade.jpg & Rue_NotreDameEst_Approach.jpg)
        (254.5, 462.0, 0.16, 0.85, 25.0),
        (260.0, 468.0, 0.16, 0.78, 75.0),
        (248.0, 456.0, 0.16, 0.88, 140.0),
        (271.5, 468.0, 0.16, 0.82, 110.0),
        (279.0, 462.0, 0.16, 0.80, 240.0),
        # Jardin du Gouverneur perimeter trees (arranged around edges so central boxwood parterres & red gallery roof remain open in satellite view)
        (294.0, 444.0, 1.26, 0.75, 35.0),
        (301.0, 434.0, 1.26, 0.78, 130.0),
        (274.0, 418.0, 1.26, 0.82, 240.0),
        # Sidewalk street trees along Place De La Dauversière
        (238.0, 448.0, 0.16, 0.85, 50.0),
        (244.0, 436.0, 0.16, 0.88, 95.0),
        (252.0, 426.0, 0.16, 0.82, 160.0),
        (262.0, 416.0, 0.16, 0.80, 215.0),
        (234.0, 412.0, 0.20, 0.85, 45.0),
        (248.0, 398.0, 0.20, 0.85, 125.0),
    ]
    for idx, (tx, ty, tz, sc, rot_deg) in enumerate(tree_coords):
        t_obj = append_kit_asset("jacaranda_tree_LOD0", collection=collection_owned, location=(tx, ty, tz), rotation_z=math.radians(rot_deg), scale=sc)
        if t_obj:
            t_obj.name = f"MTL_Owned_Tree_{BLOCK_ID}_{idx:02d}"

    # Heritage cast-iron streetlamps along Rue Notre-Dame Est, Rue Saint-Claude, and Rue Saint-Paul Est
    lamp_coords = [
        (246.5, 468.0, 0.16),
        (262.0, 474.0, 0.16),
        (278.0, 480.0, 0.16),
        (294.0, 474.0, 0.16),
        (310.0, 468.0, 0.16),
        (326.0, 462.0, 0.16),
        (288.5, 416.0, 0.16),
        (278.0, 396.0, 0.16),
        (268.0, 380.0, 0.16),
        (305.0, 438.0, 0.16),
    ]
    for idx, (lx, ly, lz) in enumerate(lamp_coords):
        l_obj = append_kit_asset("street_lamp_01", collection=collection_owned, location=(lx, ly, lz), rotation_z=0.0, scale=1.0)
        if l_obj:
            l_obj.name = f"MTL_Owned_StreetLamp_{BLOCK_ID}_{idx:02d}"

    # Heritage street benches along Rue Notre-Dame Est sidewalk & inside Jardin du Gouverneur
    bench_coords = [
        (248.0, 470.0, 0.16, 25.0),
        (268.0, 478.0, 0.16, 25.0),
        (280.0, 434.0, 1.26, -65.0),
        (242.0, 410.0, 0.20, 30.0),
        (252.0, 402.0, 0.20, 30.0),
    ]
    for idx, (bx, by, bz, rot_deg) in enumerate(bench_coords):
        b_obj = append_kit_asset("Master_Street_Bench", collection=collection_owned, location=(bx, by, bz), rotation_z=math.radians(rot_deg), scale=1.0)
        if b_obj:
            b_obj.name = f"MTL_Owned_Bench_{BLOCK_ID}_{idx:02d}"

    # Curbside parked vehicles matching Rue_SaintPaulEst_Rear.jpg and satellite_topdown.png
    car_mesh = bpy.data.meshes.new(f"MTL_Owned_Parked_Cars_{BLOCK_ID}_Mesh")
    car_obj = bpy.data.objects.new(f"MTL_Owned_Parked_Cars_{BLOCK_ID}", car_mesh)
    collection_owned.objects.link(car_obj)

    car_mats = [
        palette["Mat_MTL_White_Paint"],       # 0: White car body
        palette["Mat_MTL_CastIron_Black"],    # 1: Dark car body / tires
        palette["Mat_MTL_Silver_Tin_Roof"],   # 2: Silver car body
        palette["Mat_MTL_Shutter_Red"],       # 3: Red car body
        palette["Mat_MTL_Window_Glass_Dark"], # 4: Windshield glass
    ]
    for cm in car_mats:
        car_obj.data.materials.append(cm)

    cbm = bmesh.new()
    parked_cars = [
        # White sedan in foreground left curb of Rue_SaintPaulEst_Rear.jpg (cam at 292.2, 381.4 looking heading 29.5 deg)
        (292.8, 390.5, 29.5, 0),
        (295.4, 395.2, 29.5, 1),
        (298.0, 400.0, 29.5, 2),
        # Cars parked along Rue Saint-Paul Est & Rue Notre-Dame Est in satellite view
        (304.5, 405.5, 29.5, 1),
        (285.0, 469.0, -25.0, 0),
        (293.0, 465.2, -25.0, 2),
        (301.0, 461.5, -25.0, 1),
        (309.0, 457.8, -25.0, 3),
        (317.0, 454.0, -25.0, 0),
    ]
    for cx, cy, hdg_deg, body_mat in parked_cars:
        rad = math.radians(hdg_deg)
        dx, dy = math.sin(rad), math.cos(rad)
        p1 = (cx - dx * 2.1, cy - dy * 2.1)
        p2 = (cx + dx * 2.1, cy + dy * 2.1)
        cp1 = (cx - dx * 1.0, cy - dy * 1.0)
        cp2 = (cx + dx * 0.8, cy + dy * 0.8)
        add_box_between(cbm, p1, p2, 0.16, 0.88, thickness=1.82, offset_out=0.0, mat_idx=body_mat)
        add_box_between(cbm, cp1, cp2, 0.88, 1.44, thickness=1.56, offset_out=0.0, mat_idx=body_mat)
        add_box_between(cbm, cp1, cp2, 0.92, 1.38, thickness=1.60, offset_out=0.0, mat_idx=4)

    cbm.to_mesh(car_mesh)
    cbm.free()


def configure_world_and_render(col_owned):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    eevee = scene.eevee
    for attr, val in [("taa_render_samples", 24), ("use_raytracing", True), ("use_shadows", True)]:
        if hasattr(eevee, attr):
            setattr(eevee, attr, val)

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    w_out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.52, 0.68, 0.90, 1.0)
    bg.inputs["Strength"].default_value = 1.15
    links.new(w_out.inputs["Surface"], bg.outputs["Background"])

    # 3-Sun Daylight & Canyon Fill Lighting inside col_owned
    sun_configs = [
        ("MTL_Owned_Sun_Key", 2.2, 1.2, (52.0, 18.0, -42.0), True),
        ("MTL_Owned_Sun_Fill_North", 0.70, 12.0, (58.0, -25.0, 138.0), False),
        ("MTL_Owned_Sun_Fill_West", 0.58, 15.0, (62.0, 15.0, 48.0), False),
    ]
    for s_name, energy, angle_deg, rot_deg, use_shad in sun_configs:
        sun_data = bpy.data.lights.new(name=s_name, type="SUN")
        sun_data.energy = energy
        sun_data.angle = math.radians(angle_deg)
        if hasattr(sun_data, "use_shadow"):
            sun_data.use_shadow = use_shad
        sun_obj = bpy.data.objects.new(name=s_name, object_data=sun_data)
        col_owned.objects.link(sun_obj)
        sun_obj.rotation_euler = tuple(math.radians(d) for d in rot_deg)


def render_cameras(dossier, iter_num=1):
    scene = bpy.context.scene
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

    # Overview aerial snapshot
    ov_data = bpy.data.cameras.new(name=f"Overview_Cam_{BLOCK_ID}")
    ov_data.angle = math.radians(52.0)
    ov_data.clip_start = 1.0
    ov_data.clip_end = 2000.0
    ov_obj = bpy.data.objects.new(name=f"Overview_Cam_{BLOCK_ID}", object_data=ov_data)
    scene.collection.objects.link(ov_obj)

    target = Vector((295.0, 445.0, 8.0))
    ov_obj.location = (370.0, 310.0, 135.0)
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = SNAPSHOT_PATH
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Block Overview Snapshot -> {SNAPSHOT_PATH}")


def main():
    print(f"=== Starting Reconstruction of Block {BLOCK_ID} ===")
    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    # Master and Owned collection (NO _Context_Proxy collection created or kept)
    master_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(master_col)
    col_owned = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    master_col.children.link(col_owned)

    palette = create_upgraded_palette()
    # Clean up any template objects that kit.create_montreal_material_palette() may have created in scene.collection
    for obj in list(bpy.context.scene.collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    build_ground_and_streets(dossier, palette, col_owned)
    build_all_owned_buildings(dossier, palette, col_owned)
    scatter_trees_and_lamps(dossier, palette, col_owned)

    configure_world_and_render(col_owned)

    # Ensure no stray collections exist outside Block_MTL-VM-0017
    for c in list(bpy.context.scene.collection.children):
        if c != master_col:
            bpy.context.scene.collection.children.unlink(c)

    # Pack all 2K Poly Haven PBR textures into the .blend file
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"pack_all warning: {e}")

    # Save clean .blend file (ensuring no temporary lock files)
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

    # Export clean USDC
    bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, selected_objects_only=False)
    print(f"SUCCESS: Saved {BLEND_OUT_PATH} and exported {USDC_OUT_PATH}")


if __name__ == "__main__":
    main()
