"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0023 (Iteration 2)
(Quai Jacques-Cartier & Place Jacques-Cartier Waterfront Entrance, Montréal, QC H2Y 1J1)

Iteration 2 Complete Architectural & Waterfront Remodel:
1. Real Harbor Water Basins (Z = -2.20m) & Granite Pier Quays:
   - Carves out Bassin Bonsecours (North-East quadrant H1..H2, V3..V8) and Bassin Jacques-Cartier (South/East marina)
     so the pier peninsula footprint (Z = +0.16m) is surrounded by wave-displaced 2K PBR water at Z = -2.20m
     (wired with water_river_diffuse_2k.jpg, water_river_nor_gl_2k.jpg, water_river_rough_2k.jpg).
   - Stepped granite quay walls (Z = -2.50m .. +0.16m) with projecting coping stones, cast-iron mooring bollards,
     floating timber marina docks, moored Bateau-Mouche glass-roofed excursion vessel, and white motor yachts.
2. Hangar 16 / Pavillon Jacques-Cartier (81339554) & East Festival Village:
   - West Industrial Pavilion (Hangar 16 West Hall): Pitched corrugated silver-grey metal monitor roof, limestone/steel
     facades with deeply recessed (>= 0.45m) window bays, mullions, and western timber boardwalk terrace.
   - Central Open Structural Steel Space-Frame & Upper Timber Deck: Matches Quai_Jacques_Cartier_Pier_Center
     Street View camera (galvanized I-beams, weathered timber plank ceiling deck, skylight cutout, and corrugated
     cream/beige storage container with orange rear placard).
   - East Limestone Pavilion Wing with inset flat roof membrane and rooftop skylights.
   - Southern Quayside Truss Gallery & Masts: Tiered stone amphitheater steps, weathered concrete cylindrical caissons,
     cantilevered white steel truss catwalk, and rhythmic vertical masts along the southern quay.
   - East Festival Village: White gabled event halls, yellow canopy tent, and the iconic white conical Cirque Big-Top
     tensile pavilion (Chapiteau) + white pyramidal tensile pavilion cones.
3. Rue de la Commune Est & Place Jacques-Cartier Waterfront Entrance:
   - 5-story historic Montreal Pierre Grise limestone commercial/hotel corner block along the north side of
     Place Jacques-Cartier / Rue de la Commune Est (matching Rue_de_la_CommuneEst_Quayside H1..H6, V1..V5) with
     recessed arched windows, bracketed cornice, mansard annex with dormers, black & red cafe awnings, and barrel planters.
   - Old Port Entrance Gateway (matching Quai_Jacques_Cartier_Entrance_Pergola): Right-side timber/steel pergola (V6..V8),
     red Old Port entrance totem arch (V4..V5, H4..H5), railway crossing tracks & red/white vertical gate arms,
     white pyramidal tensile cones, flagpoles, and lush green park median lawns.
4. Lush Green Promenade du Vieux-Port Lawns, Walkways & Poly Haven 3D Assets:
   - Lush green turf lawns (leafy_grass_Diffuse_2k.jpg, Mat_MTL_Grass_Lawn_PBR at Z = +0.195m), granite curbs (Z = +0.225m),
     and limestone/cobblestone walkways (Z = +0.245m..+0.265m) with micro-stepped Z offsets (zero coplanar faces).
   - High-poly Poly Haven 3D trees (jacaranda_tree), streetlamps (street_lamp_01), and benches (modular_street_seating).
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

BLOCK_ID = "MTL-VM-0023"
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
        candidates = [f"{prefix}_Diffuse_2k.jpg", f"{prefix}_diff_2k.jpg", f"{prefix}_col_2k.jpg", f"{prefix}_2k.jpg"]
    elif map_kind == "rough":
        candidates = [f"{prefix}_Rough_2k.jpg", f"{prefix}_Roughness_2k.jpg", f"{prefix}_rough_2k.jpg"]
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


def apply_polyhaven_2k_pbr(mat, folder_prefix, scale_xyz=(0.25, 0.25, 0.25), tint_rgb=None, tint_factor=0.60, roughness_mult=1.0, normal_str=1.0, metallic=0.0):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = metallic
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
            mix.inputs["Factor"].default_value = min(0.85, tint_factor)
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
        if abs(roughness_mult - 1.0) > 1e-3:
            math_r = nodes.new("ShaderNodeMath")
            math_r.operation = "MULTIPLY"
            math_r.inputs[1].default_value = roughness_mult
            links.new(math_r.inputs[0], tex_r.outputs["Color"])
            links.new(bsdf.inputs["Roughness"], math_r.outputs["Value"])
        else:
            links.new(bsdf.inputs["Roughness"], tex_r.outputs["Color"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.65 * roughness_mult

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


def create_solid_pbr(name, rgb, roughness=0.45, metallic=0.0, coat=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if coat > 0.0 and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
    links.new(out.inputs["Surface"], bsdf.outputs["BSDF"])
    return mat


def create_palette():
    palette = kit.create_montreal_material_palette()

    # Diverse Poly Haven 2K PBR Facade & Ground Materials (BOX + UV compatible)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_PierreGrise_Limestone"], "stone_brick_wall_001", (0.28, 0.28, 0.28), (0.64, 0.65, 0.67), 0.55, 0.92, 1.25)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_WarmBuff_Limestone"], "sandstone_blocks_05", (0.26, 0.26, 0.26), (0.85, 0.81, 0.74), 0.55, 0.90, 1.15)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Cobblestone"], "cobblestone_floor_08", (0.68, 0.68, 0.68), (0.76, 0.75, 0.72), 0.55, 1.18, 1.20)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Street_Asphalt"], "clean_asphalt", (0.24, 0.24, 0.24), (0.38, 0.39, 0.41), 0.50, 0.92, 1.00)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Plaza_Light_Granite"], "concrete_pavers", (0.36, 0.36, 0.36), (0.84, 0.82, 0.78), 0.50, 1.05, 0.95)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Plaza_Charcoal_Granite"], "stone_pavers", (0.42, 0.42, 0.42), (0.58, 0.59, 0.60), 0.50, 1.05, 1.05)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Weathered_Metal"], "box_profile_metal_sheet", (0.35, 0.35, 0.35), (0.76, 0.78, 0.81), 0.80, 1.05, 1.10, metallic=0.60)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Warm_Timber"], "weathered_planks", (0.38, 0.38, 0.38), (0.68, 0.52, 0.36), 0.50, 1.08, 1.15)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Precast_Concrete"], "concrete_block_wall", (0.28, 0.28, 0.28), (0.76, 0.75, 0.72), 0.50, 0.98, 1.10)
    apply_polyhaven_2k_pbr(palette["Mat_MTL_Granite_Plinth"], "stone_block_wall", (0.26, 0.26, 0.26), (0.55, 0.54, 0.52), 0.55, 0.92, 1.30)
    apply_polyhaven_2k_pbr(palette["Mat_PH_Herringbone_Pavement"], "herringbone_pavement", (0.55, 0.55, 0.55), (0.76, 0.58, 0.50), 0.48, 1.02, 1.15)
    apply_polyhaven_2k_pbr(palette["Mat_PH_Gravel_Path"], "gravel_concrete_02", (0.30, 0.30, 0.30), (0.82, 0.79, 0.73), 0.45, 1.02, 1.05)

    # Lush Green Park Lawn PBR (leafy_grass_Diffuse_2k.jpg)
    mat_grass = bpy.data.materials.get("Mat_MTL_Grass_Lawn_PBR") or bpy.data.materials.new("Mat_MTL_Grass_Lawn_PBR")
    apply_polyhaven_2k_pbr(mat_grass, "leafy_grass", (0.22, 0.22, 0.22), (0.28, 0.50, 0.18), 0.45, 0.90, 1.15)
    palette["Mat_MTL_Grass_Lawn_PBR"] = mat_grass

    # Wave-Displaced 2K PBR Water (water_river_diffuse_2k.jpg, water_river_nor_gl_2k.jpg, water_river_rough_2k.jpg)
    mat_water = kit.get_or_create_water_pbr_material("Mat_MTL_StLawrence_Water_PBR", uv_scale=1.0)
    # Enhance water shader so both UV and Object coordinates produce crisp ripples and deep harbor teal-blue reflections
    wnodes = mat_water.node_tree.nodes
    wlinks = mat_water.node_tree.links
    bsdf_w = next((n for n in wnodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf_w:
        bsdf_w.inputs["Roughness"].default_value = 0.05
        bsdf_w.inputs["IOR"].default_value = 1.333
        if "Specular IOR Level" in bsdf_w.inputs:
            bsdf_w.inputs["Specular IOR Level"].default_value = 0.95
        if "Transmission Weight" in bsdf_w.inputs:
            bsdf_w.inputs["Transmission Weight"].default_value = 0.05
    palette["Mat_MTL_Water_StLawrence"] = mat_water
    palette["Mat_MTL_StLawrence_Water_PBR"] = mat_water

    # Corrugated Industrial Silver Roof (Hangar 16)
    mat_tin = bpy.data.materials.new("Mat_MTL_Silver_Tin_Roof")
    apply_polyhaven_2k_pbr(mat_tin, "box_profile_metal_sheet", (0.40, 0.40, 0.40), (0.78, 0.80, 0.83), 0.88, 1.15, 1.15, metallic=0.45)
    palette["Mat_MTL_Silver_Tin_Roof"] = mat_tin

    # Roof Flat Membrane
    mat_roof = bpy.data.materials.new("Mat_MTL_Roof_Membrane")
    apply_polyhaven_2k_pbr(mat_roof, "worn_asphalt", (0.35, 0.35, 0.35), (0.42, 0.43, 0.45), 0.65, 0.92, 0.90)
    palette["Mat_MTL_Roof_Membrane"] = mat_roof

    # High Specular Dark Reflective Architectural Glass
    glass_mat = palette["Mat_MTL_Window_Glass_Dark"]
    glass_mat.use_nodes = True
    gnodes = glass_mat.node_tree.nodes
    glinks = glass_mat.node_tree.links
    gnodes.clear()
    g_out = gnodes.new("ShaderNodeOutputMaterial")
    g_bsdf = gnodes.new("ShaderNodeBsdfPrincipled")
    g_bsdf.inputs["Base Color"].default_value = (0.04, 0.08, 0.12, 1.0)
    g_bsdf.inputs["Roughness"].default_value = 0.04
    g_bsdf.inputs["Metallic"].default_value = 0.25
    g_bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in g_bsdf.inputs:
        g_bsdf.inputs["Specular IOR Level"].default_value = 0.95
    glinks.new(g_out.inputs["Surface"], g_bsdf.outputs["BSDF"])

    # Warm Cedar / Weathered Timber
    palette["Mat_MTL_Wood_Timber"] = palette["Mat_MTL_Warm_Timber"]

    # Heavy Stone Retaining Wall & Coping for Quays
    mat_quay_wall = bpy.data.materials.new("Mat_MTL_Quay_Retaining_Wall")
    apply_polyhaven_2k_pbr(mat_quay_wall, "medieval_blocks_06", (0.28, 0.28, 0.28), (0.46, 0.48, 0.49), 0.60, 0.92, 1.40)
    palette["Mat_MTL_Quay_Retaining_Wall"] = mat_quay_wall

    mat_coping = bpy.data.materials.new("Mat_MTL_Quayside_Concrete")
    apply_polyhaven_2k_pbr(mat_coping, "concrete_pavement_02", (0.35, 0.35, 0.35), (0.85, 0.82, 0.77), 0.60, 1.22, 0.95)
    palette["Mat_MTL_Quayside_Concrete"] = mat_coping

    mat_dock = bpy.data.materials.new("Mat_MTL_Marina_Dock")
    apply_polyhaven_2k_pbr(mat_dock, "weathered_planks", (0.28, 0.28, 0.28), (0.58, 0.46, 0.34), 0.65, 0.88, 1.15)
    palette["Mat_MTL_Marina_Dock"] = mat_dock

    # Specialized Accent Materials for Street View Landmarks
    palette["Mat_MTL_CastIron_Black"] = create_solid_pbr("Mat_MTL_CastIron_Black", (0.10, 0.11, 0.12), roughness=0.35, metallic=0.85)
    palette["Mat_MTL_Silver_Metal"] = create_solid_pbr("Mat_MTL_Silver_Metal", (0.68, 0.71, 0.74), roughness=0.28, metallic=0.85)
    palette["Mat_MTL_White_Steel"] = create_solid_pbr("Mat_MTL_White_Steel", (0.93, 0.94, 0.95), roughness=0.22, metallic=0.15, coat=0.4)
    palette["Mat_MTL_Tensile_White"] = create_solid_pbr("Mat_MTL_Tensile_White", (0.95, 0.95, 0.93), roughness=0.38, metallic=0.0)
    palette["Mat_MTL_Marina_Blue_Tent"] = create_solid_pbr("Mat_MTL_Marina_Blue_Tent", (0.08, 0.24, 0.62), roughness=0.52, metallic=0.0)
    palette["Mat_MTL_Awning_Red"] = create_solid_pbr("Mat_MTL_Awning_Red", (0.72, 0.10, 0.10), roughness=0.48, metallic=0.0)
    palette["Mat_MTL_Container_Beige"] = create_solid_pbr("Mat_MTL_Container_Beige", (0.82, 0.77, 0.66), roughness=0.48, metallic=0.25)
    palette["Mat_MTL_Warning_Orange"] = create_solid_pbr("Mat_MTL_Warning_Orange", (0.92, 0.58, 0.08), roughness=0.40, metallic=0.10)
    palette["Mat_MTL_Canopy_Yellow"] = create_solid_pbr("Mat_MTL_Canopy_Yellow", (0.88, 0.68, 0.26), roughness=0.45, metallic=0.0)

    return palette


# --- Geometry & BMesh Helpers ---

def assign_planar_uvs(bm, scale=0.15):
    uv_layer = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        for loop in f.loops:
            co = loop.vert.co
            if abs(n.z) > 0.65:
                loop[uv_layer].uv = (co.x * scale, co.y * scale)
            elif abs(n.x) > abs(n.y):
                loop[uv_layer].uv = (co.y * scale, co.z * scale)
            else:
                loop[uv_layer].uv = (co.x * scale, co.z * scale)


def finalize_bm_to_mesh(bm, mesh, uv_scale=0.15, smooth=False):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign_planar_uvs(bm, scale=uv_scale)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = smooth


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


def add_box_between(bm, p1, p2, z0, z1, thickness=0.35, offset_out=0.0, mat_idx=0, cap_bottom=False):
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
    vb = [bm.verts.new((*pt, z0)) for pt in c]
    vt = [bm.verts.new((*pt, z1)) for pt in c]
    for i in range(4):
        j = (i + 1) % 4
        try:
            f = bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
            f.material_index = mat_idx
        except ValueError:
            pass
    try:
        f_top = bm.faces.new(vt)
        f_top.material_index = mat_idx
    except ValueError:
        pass
    if cap_bottom:
        try:
            f_bot = bm.faces.new(list(reversed(vb)))
            f_bot.material_index = mat_idx
        except ValueError:
            pass


def add_strut_3d(bm, p1_xyz, p2_xyz, radius=0.08, n_seg=8, mat_idx=0):
    v1 = Vector(p1_xyz)
    v2 = Vector(p2_xyz)
    axis = v2 - v1
    length = axis.length
    if length < 1e-4:
        return
    z_dir = axis.normalized()
    ref = Vector((0.0, 0.0, 1.0)) if abs(z_dir.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u_dir = z_dir.cross(ref).normalized()
    v_dir = z_dir.cross(u_dir).normalized()
    r1 = []
    r2 = []
    for i in range(n_seg):
        ang = (i / n_seg) * 2.0 * math.pi
        off = (u_dir * math.cos(ang) + v_dir * math.sin(ang)) * radius
        r1.append(bm.verts.new(v1 + off))
        r2.append(bm.verts.new(v2 + off))
    for i in range(n_seg):
        j = (i + 1) % n_seg
        try:
            f = bm.faces.new((r1[i], r1[j], r2[j], r2[i]))
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


def add_cylinder_in_bm(bm, center_xy, z0, z1, r_bot, r_top, n_seg=16, mat_idx=0, cap_top=True):
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
    if cap_top and r_top > 1e-3:
        try:
            f_top = bm.faces.new(v_top)
            f_top.material_index = mat_idx
        except ValueError:
            pass


def add_conical_tent_in_bm(bm, center_xy, r_base, z_base, z_eave, z_peak, n_seg=24, mat_wall=0, mat_roof=0, mat_pole=1):
    cx, cy = center_xy
    # Cylindrical fabric skirt wall
    add_cylinder_in_bm(bm, center_xy, z_base, z_eave, r_base, r_base, n_seg=n_seg, mat_idx=mat_wall, cap_top=False)
    # Conical Catenary Roof (3 concentric rings for authentic tensile curve)
    rings = [
        (r_base * 1.02, z_eave),
        (r_base * 0.62, z_eave + (z_peak - z_eave) * 0.32),
        (r_base * 0.25, z_eave + (z_peak - z_eave) * 0.68),
        (0.18, z_peak),
    ]
    ring_verts = []
    for rad, rz in rings:
        rv = []
        for i in range(n_seg):
            th = (i / n_seg) * 2.0 * math.pi
            rv.append(bm.verts.new((cx + rad * math.cos(th), cy + rad * math.sin(th), rz)))
        ring_verts.append(rv)
    for r_i in range(len(ring_verts) - 1):
        r_a = ring_verts[r_i]
        r_b = ring_verts[r_i + 1]
        for i in range(n_seg):
            j = (i + 1) % n_seg
            try:
                f = bm.faces.new((r_a[i], r_a[j], r_b[j], r_b[i]))
                f.material_index = mat_roof
            except ValueError:
                pass
    # Center mast finial
    add_cylinder_in_bm(bm, center_xy, z_peak - 0.5, z_peak + 1.8, 0.14, 0.06, n_seg=8, mat_idx=mat_pole)


def add_pyramidal_canopy_in_bm(bm, p_min, p_max, z_base, z_eave, z_peak, mat_roof=0, mat_pole=1):
    x0, y0 = p_min
    x1, y1 = p_max
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    # 4 corner poles
    for px, py in corners:
        add_cylinder_in_bm(bm, (px, py), z_base, z_eave, 0.06, 0.06, n_seg=8, mat_idx=mat_pole)
    # Eave valance skirt
    for i in range(4):
        add_box_between(bm, corners[i], corners[(i + 1) % 4], z_eave - 0.32, z_eave, thickness=0.06, mat_idx=mat_roof)
    # 4 triangular roof slopes
    v_eave = [bm.verts.new((px, py, z_eave)) for px, py in corners]
    v_apex = bm.verts.new((cx, cy, z_peak))
    for i in range(4):
        j = (i + 1) % 4
        try:
            f = bm.faces.new((v_eave[i], v_eave[j], v_apex))
            f.material_index = mat_roof
        except ValueError:
            pass


def add_pitched_shed_in_bm(bm, x0, y0, x1, y1, z_base, z_eave, z_ridge, ridge_along_x=True, mat_wall=0, mat_roof=1):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    extrude_prism_in_bm(bm, pts, z_base, z_eave, mat_side=mat_wall, mat_top=None)
    if ridge_along_x:
        ym = 0.5 * (y0 + y1)
        v_sw = bm.verts.new((x0, y0, z_eave))
        v_se = bm.verts.new((x1, y0, z_eave))
        v_ne = bm.verts.new((x1, y1, z_eave))
        v_nw = bm.verts.new((x0, y1, z_eave))
        v_rw = bm.verts.new((x0, ym, z_ridge))
        v_re = bm.verts.new((x1, ym, z_ridge))
        for verts, m_i in [
            ((v_sw, v_se, v_re, v_rw), mat_roof),
            ((v_ne, v_nw, v_rw, v_re), mat_roof),
            ((v_nw, v_sw, v_rw), mat_wall),
            ((v_se, v_ne, v_re), mat_wall),
        ]:
            try:
                f = bm.faces.new(verts)
                f.material_index = m_i
            except ValueError:
                pass
    else:
        xm = 0.5 * (x0 + x1)
        v_sw = bm.verts.new((x0, y0, z_eave))
        v_se = bm.verts.new((x1, y0, z_eave))
        v_ne = bm.verts.new((x1, y1, z_eave))
        v_nw = bm.verts.new((x0, y1, z_eave))
        v_rs = bm.verts.new((xm, y0, z_ridge))
        v_rn = bm.verts.new((xm, y1, z_ridge))
        for verts, m_i in [
            ((v_sw, v_rs, v_rn, v_nw), mat_roof),
            ((v_se, v_ne, v_rn, v_rs), mat_roof),
            ((v_sw, v_se, v_rs), mat_wall),
            ((v_ne, v_nw, v_rn), mat_wall),
        ]:
            try:
                f = bm.faces.new(verts)
                f.material_index = m_i
            except ValueError:
                pass


# ==============================================================================
# 1. WATERFRONTS, WAVE-DISPLACED HARBOR BASINS, MARINA DOCKS & VESSELS
# ==============================================================================

def build_waterfront_quays_and_marina(palette, collection):
    name = f"MTL_Owned_Quays_And_Marina_{BLOCK_ID}"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Quay_Retaining_Wall"],    # 0: Stepped stone quay retaining wall
        palette["Mat_MTL_Quayside_Concrete"],      # 1: Concrete quay coping & lower apron
        palette["Mat_MTL_StLawrence_Water_PBR"],   # 2: Wave-displaced 2K PBR water (Z = -2.20m)
        palette["Mat_MTL_Marina_Dock"],            # 3: Floating timber marina docks
        palette["Mat_MTL_CastIron_Black"],         # 4: Mooring bollards & railings
        palette["Mat_MTL_Wood_Timber"],            # 5: Timber boardwalks & picnic tables
        palette["Mat_MTL_White_Steel"],            # 6: White vessel hulls & marina railings
        palette["Mat_MTL_Window_Glass_Dark"],      # 7: Bateau-Mouche glass roof & yacht cabins
        palette["Mat_MTL_Marina_Blue_Tent"],       # 8: Blue marina ticket kiosk canopies
        palette["Mat_MTL_Tensile_White"],          # 9: White dockside tents & freezer chests
        palette["Mat_MTL_Warning_Orange"],         # 10: Lifebuoy ring safety straps
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Subdivided Wave-Displaced 2K PBR Water Surface (Z = -2.20m)
    # Covers Bassin Bonsecours (North-East: X = 466..620, Y = 327..450)
    # and Bassin Jacques-Cartier (South & East: X = 320..640, Y = 100..228)
    water_patches = [
        # Bassin Bonsecours (visible in satellite_topdown H1..H2, V3..V8)
        (466.0, 327.0, 620.0, 440.0, 28, 20),
        # Bassin Jacques-Cartier main marina basin (South & South-East)
        (340.0, 110.0, 620.0, 226.5, 36, 18),
        # Marina channel under southern pier apron (H7..H8, V5..V8)
        (450.0, 221.0, 580.0, 231.0, 24, 6),
    ]
    for wx0, wy0, wx1, wy1, nx_sub, ny_sub in water_patches:
        dx = (wx1 - wx0) / nx_sub
        dy = (wy1 - wy0) / ny_sub
        grid_v = []
        for iy in range(ny_sub + 1):
            row_v = []
            y = wy0 + iy * dy
            for ix in range(nx_sub + 1):
                x = wx0 + ix * dx
                # Subtle 3D harmonic wave displacement around Z = -2.20m
                zw = -2.20 + 0.035 * math.sin(x * 0.45 + y * 0.30) + 0.020 * math.cos(x * 0.85 - y * 0.65)
                row_v.append(bm.verts.new((x, y, zw)))
            grid_v.append(row_v)
        for iy in range(ny_sub):
            for ix in range(nx_sub):
                try:
                    f = bm.faces.new((grid_v[iy][ix], grid_v[iy][ix + 1], grid_v[iy + 1][ix + 1], grid_v[iy + 1][ix]))
                    f.material_index = 2
                except ValueError:
                    pass

    # 2. Bassin Bonsecours Stepped Granite Quay Wall (North-East H1..H2, V3..V8)
    # Exact curve from satellite_topdown.png: (478.0, 356.0) -> rounded corner at (467.8, 331.5) -> East to (570.0, 331.5)
    bonsecours_quay_pts = [
        (478.5, 356.0),
        (472.5, 342.5),
        (468.2, 333.5),
        (468.0, 330.5),
        (470.2, 328.6),
        (474.5, 328.2),
        (515.0, 329.5),
        (565.0, 331.2),
    ]
    for i in range(len(bonsecours_quay_pts) - 1):
        p1, p2 = bonsecours_quay_pts[i], bonsecours_quay_pts[i + 1]
        # Lower stepped granite wall (Z = -2.50m .. -0.80m)
        add_box_between(bm, p1, p2, -2.50, -0.80, thickness=1.30, offset_out=0.0, mat_idx=0)
        # Upper stepped granite wall (Z = -0.80m .. +0.16m)
        add_box_between(bm, p1, p2, -0.80, 0.16, thickness=1.05, offset_out=0.0, mat_idx=0)
        # Light granite coping stone cap (Z = +0.16m .. +0.26m)
        add_box_between(bm, p1, p2, 0.16, 0.26, thickness=1.25, offset_out=0.0, mat_idx=1)

        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len >= 8.0:
            n_bol = max(1, int(seg_len // 12.0))
            for b_i in range(1, n_bol + 1):
                t = b_i / (n_bol + 1)
                bx = p1[0] + (p2[0] - p1[0]) * t
                by = p1[1] + (p2[1] - p1[1]) * t - 0.55
                add_cylinder_in_bm(bm, (bx, by), 0.26, 0.78, 0.16, 0.14, n_seg=10, mat_idx=4)
                add_cylinder_in_bm(bm, (bx, by), 0.78, 0.86, 0.20, 0.18, n_seg=10, mat_idx=4)

    # 3. Southern Quayside Wall & Lower Marina Apron (H7..H8, V1..V8)
    # Upper quayside edge along Y = 228.5 .. 232.0
    south_upper_quay = [
        (420.0, 227.8),
        (465.0, 229.6),
        (515.0, 231.5),
        (565.0, 233.5),
    ]
    for i in range(len(south_upper_quay) - 1):
        p1, p2 = south_upper_quay[i], south_upper_quay[i + 1]
        add_box_between(bm, p1, p2, -2.50, 0.16, thickness=1.10, offset_out=0.0, mat_idx=0)
        add_box_between(bm, p1, p2, 0.16, 0.25, thickness=1.30, offset_out=0.0, mat_idx=1)

    # Lower Marina Dock Promenade Apron (Y = 220.0 .. 228.8, X = 420.0 .. 560.0)
    # Note: SV_Cam_Bassin_Jacques_Cartier_Marina is at (448.091, 223.145, 1.75) looking NE (heading 45 deg)!
    apron_pts = [
        (420.0, 219.8),
        (558.0, 222.5),
        (558.0, 229.5),
        (420.0, 228.2),
    ]
    extrude_prism_in_bm(bm, apron_pts, -2.40, 0.00, mat_side=0, mat_top=1)
    # Two parallel light concrete utility/drainage strips visible on the right of Bassin_Jacques_Cartier_Marina.jpg
    add_box_between(bm, (445.0, 221.0), (510.0, 228.5), 0.00, 0.015, thickness=0.22, offset_out=0.0, mat_idx=6)
    add_box_between(bm, (445.4, 220.6), (510.4, 228.1), 0.00, 0.015, thickness=0.22, offset_out=0.0, mat_idx=6)

    # Row of dark floating dock cubes along East Marina slot (visible in satellite_topdown H7..H8, V6..V8)
    for fi in range(9):
        fx = 508.0 + fi * 5.2
        fy = 226.8 + fi * 0.15
        add_box_between(bm, (fx, fy), (fx + 3.8, fy + 0.1), -0.40, 0.08, thickness=3.4, mat_idx=4)

    # 4. Elements directly framed in SV_Cam_Bassin_Jacques_Cartier_Marina ([448.091, 223.145], heading 45 deg):
    # (a) Two White Dockside Freezer/Storage Chests in lower-left foreground (H6..H8, V1..V3)
    add_box_between(bm, (448.8, 225.4), (449.7, 226.2), 0.00, 0.92, thickness=0.75, mat_idx=9)
    add_box_between(bm, (449.9, 226.4), (451.7, 227.9), 0.00, 0.90, thickness=0.80, mat_idx=9)

    # (b) White Metal Quayside Safety Railing along left edge of marina apron (H5..H6, V2..V6)
    rail_p1 = (447.5, 225.2)
    rail_p2 = (482.0, 253.5)
    add_box_between(bm, rail_p1, rail_p2, 0.98, 1.05, thickness=0.06, mat_idx=6)
    add_box_between(bm, rail_p1, rail_p2, 0.52, 0.58, thickness=0.05, mat_idx=6)
    n_rposts = 16
    for rpi in range(n_rposts + 1):
        t = rpi / n_rposts
        rx = rail_p1[0] + (rail_p2[0] - rail_p1[0]) * t
        ry = rail_p1[1] + (rail_p2[1] - rail_p1[1]) * t
        add_cylinder_in_bm(bm, (rx, ry), 0.00, 1.05, 0.04, 0.04, n_seg=8, mat_idx=6)

    # White Lifebuoy Rings mounted along the quayside safety railing & Dockside Timber Cleats (H5..H7, V4..V8)
    r_dx, r_dy = rail_p2[0] - rail_p1[0], rail_p2[1] - rail_p1[1]
    r_len = math.hypot(r_dx, r_dy)
    r_ux, r_uy = r_dx / r_len, r_dy / r_len
    r_nx, r_ny = r_uy, -r_ux
    for lb_t in (0.14, 0.28, 0.42, 0.56, 0.70, 0.84):
        lbx = rail_p1[0] + r_dx * lb_t + r_nx * 0.08
        lby = rail_p1[1] + r_dy * lb_t + r_ny * 0.08
        lbz = 0.76
        n_lb_seg = 12
        r_ring = 0.34
        for s_i in range(n_lb_seg):
            a0 = (s_i / n_lb_seg) * 2.0 * math.pi
            a1 = ((s_i + 1) / n_lb_seg) * 2.0 * math.pi
            p_a = (lbx + r_ux * r_ring * math.cos(a0), lby + r_uy * r_ring * math.cos(a0), lbz + r_ring * math.sin(a0))
            p_b = (lbx + r_ux * r_ring * math.cos(a1), lby + r_uy * r_ring * math.cos(a1), lbz + r_ring * math.sin(a1))
            m_lb = 10 if (s_i % 3 == 0) else 6
            add_strut_3d(bm, p_a, p_b, radius=0.065, n_seg=6, mat_idx=m_lb)

    # Dockside Timber Mooring Cleats along the marina apron & finger pier edge (H5..H7, V5..V8)
    for cl_i in range(12):
        ct = cl_i / 11.0
        clx = 450.5 + ct * 38.0
        cly = 222.0 + ct * 28.5
        # Timber bollard post + horizontal horn cleat bar
        add_box_between(bm, (clx - 0.16, cly - 0.12), (clx + 0.16, cly + 0.12), 0.00, 0.38, thickness=0.24, mat_idx=5)
        add_box_between(bm, (clx - 0.36, cly - 0.26), (clx + 0.36, cly + 0.26), 0.32, 0.44, thickness=0.14, mat_idx=5)
        add_cylinder_in_bm(bm, (clx, cly), 0.44, 0.50, 0.10, 0.08, n_seg=8, mat_idx=4)

    # (c) Two Blue Peaked Marina Ticket Kiosk Tents (Chapiteaux Bleus) & Picnic Tables (H4..H7, V3..V6)
    # Foreground-midground blue tent (centered in V3..V6, H4..H6 of Bassin_Jacques_Cartier_Marina)
    add_pyramidal_canopy_in_bm(bm, (451.8, 227.4), (455.6, 231.2), 0.00, 2.15, 3.15, mat_roof=8, mat_pole=6)
    # Picnic tables under first blue tent
    for tb_off in (-0.65, 0.65):
        tcx, tcy = 453.7 + tb_off * 0.7, 229.3 + tb_off * 0.7
        # Table top
        add_box_between(bm, (tcx - 0.9, tcy - 0.7), (tcx + 0.9, tcy + 0.7), 0.72, 0.78, thickness=0.85, mat_idx=5)
        # Bench seats
        add_box_between(bm, (tcx - 0.9, tcy - 0.7), (tcx + 0.9, tcy + 0.7), 0.42, 0.47, thickness=0.30, offset_out=0.68, mat_idx=5)
        add_box_between(bm, (tcx - 0.9, tcy - 0.7), (tcx + 0.9, tcy + 0.7), 0.42, 0.47, thickness=0.30, offset_out=-0.68, mat_idx=5)

    # Second blue marina tent further down the quay (H5..H6, V6..V7)
    add_pyramidal_canopy_in_bm(bm, (466.0, 239.0), (470.2, 243.2), 0.00, 2.20, 3.25, mat_roof=8, mat_pole=6)

    # Additional blue & white marina tents visible along bottom edge H8 of satellite_topdown.png (kept clear of Camera 4 foreground right!)
    add_pyramidal_canopy_in_bm(bm, (438.0, 219.5), (443.5, 222.5), 0.00, 2.20, 3.20, mat_roof=8, mat_pole=6)
    add_pyramidal_canopy_in_bm(bm, (471.0, 221.8), (477.0, 224.8), 0.00, 2.20, 3.20, mat_roof=8, mat_pole=6)
    add_box_between(bm, (511.0, 221.8), (523.5, 222.2), 0.00, 2.80, thickness=3.8, mat_idx=9)
    add_box_between(bm, (535.0, 222.5), (541.5, 222.8), 0.00, 2.80, thickness=3.6, mat_idx=9)

    # 5. Moored Bateau-Mouche Glass-Roofed Excursion Vessel & White Motor Yachts
    # Helper to build an articulated white motor yacht / excursion boat in BMesh
    def add_motor_yacht(center_xy, heading_rad, length=14.0, beam=4.2, is_bateau_mouche=False):
        ycx, ycy = center_xy
        ux, uy = math.cos(heading_rad), math.sin(heading_rad)
        nx, ny = -uy, ux

        def to_world(lx, ly):
            return (ycx + ux * lx + nx * ly, ycy + uy * lx + ny * ly)

        hl = length * 0.5
        hb = beam * 0.5
        hull_pts = [
            to_world(-hl, -hb * 0.85),
            to_world(hl * 0.55, -hb),
            to_world(hl, 0.0),
            to_world(hl * 0.55, hb),
            to_world(-hl, hb * 0.85),
        ]
        # White hull rising from water Z = -2.25m to deck Z = -0.95m (or +0.45m for dockside visibility)
        z_wl = -2.25
        z_deck = 0.35 if not is_bateau_mouche else 0.55
        extrude_prism_in_bm(bm, hull_pts, z_wl, z_deck, mat_side=6, mat_top=5)

        if is_bateau_mouche:
            # Iconic glass-vaulted panoramic cabin of Le Bateau-Mouche
            cab_p1 = to_world(-hl * 0.78, 0.0)
            cab_p2 = to_world(hl * 0.62, 0.0)
            add_box_between(bm, cab_p1, cab_p2, z_deck, z_deck + 1.85, thickness=beam * 0.82, mat_idx=7)
            # White steel arch ribs along the panoramic glass cabin
            for ri in range(9):
                rt = -0.75 + ri * (1.35 / 8.0)
                rp1 = to_world(hl * rt, -hb * 0.43)
                rp2 = to_world(hl * rt, hb * 0.43)
                add_box_between(bm, rp1, rp2, z_deck, z_deck + 1.92, thickness=0.18, mat_idx=6)
            # Upper sun-deck canopy at stern
            st_p1 = to_world(-hl * 0.92, 0.0)
            st_p2 = to_world(-hl * 0.45, 0.0)
            add_box_between(bm, st_p1, st_p2, z_deck + 1.85, z_deck + 2.10, thickness=beam * 0.78, mat_idx=6)
        else:
            # Main saloon cabin with dark tinted wrap-around windows
            cab_p1 = to_world(-hl * 0.45, 0.0)
            cab_p2 = to_world(hl * 0.35, 0.0)
            add_box_between(bm, cab_p1, cab_p2, z_deck, z_deck + 1.15, thickness=beam * 0.72, mat_idx=7)
            add_box_between(bm, cab_p1, cab_p2, z_deck + 1.15, z_deck + 1.38, thickness=beam * 0.76, mat_idx=6)
            # Flybridge & radar arch
            fb_p1 = to_world(-hl * 0.25, 0.0)
            fb_p2 = to_world(hl * 0.10, 0.0)
            add_box_between(bm, fb_p1, fb_p2, z_deck + 1.38, z_deck + 2.15, thickness=beam * 0.48, mat_idx=6)
            # Tall White Mast, Spreader Yardarm & Rigging Stays (visible in Bassin_Jacques_Cartier_Marina H5..H7, V5..V8)
            mast_xy = to_world(hl * 0.05, 0.0)
            z_mast_top = z_deck + 7.40
            add_cylinder_in_bm(bm, mast_xy, z_deck + 1.38, z_mast_top, 0.065, 0.038, n_seg=8, mat_idx=6)
            # Horizontal spreader yardarm at mid-mast
            sp_port = to_world(hl * 0.05, -hb * 0.68)
            sp_stbd = to_world(hl * 0.05, hb * 0.68)
            add_strut_3d(bm, (*sp_port, z_deck + 4.50), (*sp_stbd, z_deck + 4.50), radius=0.032, n_seg=6, mat_idx=6)
            # Fore-stay, back-stay, and port/starboard shrouds
            bow_pt = to_world(hl * 0.92, 0.0)
            stern_pt = to_world(-hl * 0.88, 0.0)
            port_chain = to_world(hl * 0.02, -hb * 0.82)
            stbd_chain = to_world(hl * 0.02, hb * 0.82)
            for anchor_xy in (bow_pt, stern_pt, port_chain, stbd_chain):
                add_strut_3d(bm, (*anchor_xy, z_deck + 0.25), (*mast_xy, z_mast_top - 0.35), radius=0.024, n_seg=6, mat_idx=6)

    # Moored Bateau-Mouche & Motor Yachts in Bassin Jacques-Cartier (visible in Bassin_Jacques_Cartier_Marina V5..V8, H5..H7 & Satellite H8)
    add_motor_yacht((495.0, 214.0), math.radians(4.0), length=30.0, beam=6.4, is_bateau_mouche=True)
    add_motor_yacht((460.2, 217.2), math.radians(36.0), length=12.0, beam=3.7, is_bateau_mouche=False)
    add_motor_yacht((466.5, 221.8), math.radians(38.0), length=12.5, beam=3.8, is_bateau_mouche=False)
    add_motor_yacht((472.5, 225.8), math.radians(40.0), length=13.0, beam=3.9, is_bateau_mouche=False)
    add_motor_yacht((478.0, 229.5), math.radians(42.0), length=13.5, beam=4.0, is_bateau_mouche=False)
    add_motor_yacht((489.0, 236.5), math.radians(42.0), length=11.5, beam=3.6, is_bateau_mouche=False)
    add_motor_yacht((532.0, 214.5), math.radians(3.0), length=16.0, beam=4.4, is_bateau_mouche=False)

    # Floating Marina Finger Piers in Bassin Jacques-Cartier
    add_box_between(bm, (458.0, 220.5), (495.0, 240.0), -2.25, 0.15, thickness=1.8, mat_idx=3)

    finalize_bm_to_mesh(bm, mesh, uv_scale=0.12)
    return obj


# ==============================================================================
# 2. HANGAR 16 / PAVILLON JACQUES-CARTIER & EAST FESTIVAL VILLAGE
# ==============================================================================

def build_pavillon_jacques_cartier_and_hangar16(palette, collection):
    """
    Builds the complete Quai Jacques-Cartier Pavilion & Hangar 16 complex (H5..H7, V1..V8)
    and East Festival Village (H2..H7, V6..V8) matching satellite_topdown.png and
     Street View cameras SV_Cam_Quai_Jacques_Cartier_Pier_Center & SV_Cam_Bassin_Jacques_Cartier_Marina.
    """
    name = "MTL_Owned_81339554_Pavillon_Jacques_Cartier_Hangar16"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_PierreGrise_Limestone"],  # 0: Limestone walls & piers
        palette["Mat_MTL_Silver_Tin_Roof"],        # 1: Corrugated silver-grey metal roof (Hangar 16)
        palette["Mat_MTL_Window_Glass_Dark"],      # 2: Deeply recessed reflective glass
        palette["Mat_MTL_CastIron_Black"],         # 3: Dark structural steel & mullions
        palette["Mat_MTL_WarmBuff_Limestone"],     # 4: Stone plinths, sills, coping
        palette["Mat_MTL_Wood_Timber"],            # 5: Weathered timber boardwalk & upper deck planks
        palette["Mat_MTL_Silver_Metal"],           # 6: Galvanized steel I-beams & H-columns
        palette["Mat_MTL_White_Steel"],            # 7: White structural steel space-frame & catwalk
        palette["Mat_MTL_Container_Beige"],        # 8: Cream/beige corrugated shipping container
        palette["Mat_MTL_Warning_Orange"],         # 9: Orange rear placard on container
        palette["Mat_MTL_Roof_Membrane"],          # 10: Inset flat roof membrane
        palette["Mat_MTL_Tensile_White"],          # 11: White Cirque Big-Top Chapiteau & event tents
        palette["Mat_MTL_Canopy_Yellow"],          # 12: Warm ochre/yellow festival canopy
        palette["Mat_MTL_Precast_Concrete"],       # 13: Weathered concrete cylindrical caissons
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # --------------------------------------------------------------------------
    # A. HANGAR 16 / PAVILLON WEST HALL (X = 442.8..473.2, Y = 238.5..267.8, V2..V3, H5..H7)
    # Large pitched-roof industrial steel & limestone pavilion visible in satellite_topdown.png
    # --------------------------------------------------------------------------
    hx0, hy0, hx1, hy1 = 442.8, 238.5, 473.2, 267.8
    z_base = 0.16
    z_eave = 7.40
    z_ridge = 8.95

    # Core walls & low-slope industrial gable roof with standing-seam ribs
    add_pitched_shed_in_bm(bm, hx0, hy0, hx1, hy1, z_base, z_eave, z_ridge, ridge_along_x=False, mat_wall=0, mat_roof=1)

    # Standing-seam roof purlin ribs visible in satellite_topdown.png running North-South (along Y)
    for rx_i in range(28):
        rx = hx0 + 0.5 + rx_i * ((hx1 - hx0 - 1.0) / 27.0)
        t_roof = 1.0 - abs((rx - 0.5 * (hx0 + hx1)) / (0.5 * (hx1 - hx0)))
        rz = z_eave + (z_ridge - z_eave) * t_roof
        add_box_between(bm, (rx, hy0 - 0.2), (rx, hy1 + 0.2), rz - 0.04, rz + 0.08, thickness=0.14, mat_idx=6)

    # Articulated facades on Hangar 16 West Hall (0.50m recessed industrial window bays)
    w_corners = [(hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)]
    for i in range(4):
        p1, p2 = w_corners[i], w_corners[(i + 1) % 4]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(3, int(seg_len // 4.2))
        bay_w = seg_len / n_bays
        pier_w = 0.75

        # Plinth & Cornice
        add_box_between(bm, p1, p2, z_base, z_base + 0.95, thickness=0.80, offset_out=0.25, mat_idx=4)
        add_box_between(bm, p1, p2, z_eave - 0.35, z_eave + 0.10, thickness=0.90, offset_out=0.30, mat_idx=6)

        for b in range(n_bays + 1):
            s0 = max(0.0, b * bay_w - pier_w * 0.5)
            s1 = min(seg_len, b * bay_w + pier_w * 0.5)
            if s1 > s0 + 0.05:
                q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
                q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
                add_box_between(bm, q1, q2, z_base + 0.95, z_eave - 0.35, thickness=0.72, offset_out=0.22, mat_idx=0)

        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            if bs1 - bs0 < 0.4:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
            # Ground & clerestory recessed glass (0.50m recess behind outer piers)
            add_box_between(bm, wp1, wp2, z_base + 1.15, 4.10, thickness=0.10, offset_out=-0.28, mat_idx=2)
            add_box_between(bm, wp1, wp2, 4.10, 4.45, thickness=0.82, offset_out=0.26, mat_idx=4)
            add_box_between(bm, wp1, wp2, 4.45, z_eave - 0.50, thickness=0.10, offset_out=-0.28, mat_idx=2)

    # --------------------------------------------------------------------------
    # B. WEST TIMBER BOARDWALK TERRACE (X = 429.5..442.8, Y = 239.5..256.5, V1..V2, H6..H7)
    # --------------------------------------------------------------------------
    deck_pts = [(429.5, 239.5), (442.8, 239.5), (442.8, 256.5), (429.5, 256.5)]
    extrude_prism_in_bm(bm, deck_pts, 0.16, 0.36, mat_side=3, mat_top=5)
    add_box_between(bm, (429.5, 239.5), (429.5, 256.5), 0.36, 1.25, thickness=0.12, mat_idx=3)
    add_box_between(bm, (429.5, 256.5), (442.8, 256.5), 0.36, 1.25, thickness=0.12, mat_idx=3)

    # --------------------------------------------------------------------------
    # C. CENTRAL OPEN STEEL-TRUSS PERGOLA GRID & PIER CENTER CAMERA STRUCTURE
    # (X = 473.2..501.2, Y = 239.5..267.8, V3..V5, H5..H7)
    # Specifically engineered so SV_Cam_Quai_Jacques_Cartier_Pier_Center at
    # (497.368, 248.266, 1.75) looking SW (heading 235 deg, pitch +12 deg)
    # sees the exact galvanized steel I-beams, timber plank ceiling deck,
    # skylight opening, left steel column, and cream corrugated container!
    # --------------------------------------------------------------------------
    # 1. Open white/silver structural steel space-frame grid visible from top-down satellite (X = 473.2..501.2, Y = 240.0..267.5)
    grid_x = [473.4, 478.0, 482.6, 487.2, 491.8, 496.4, 501.0]
    grid_y = [240.2, 245.5, 250.8, 256.1, 261.4, 267.2]
    z_grid_top = 6.80
    for gx in grid_x:
        for gy in grid_y:
            # Skip column right on top of camera (497.368, 248.266)
            if math.hypot(gx - 497.37, gy - 248.27) < 2.2:
                continue
            add_cylinder_in_bm(bm, (gx, gy), 0.16, z_grid_top, 0.16, 0.16, n_seg=8, mat_idx=7)
    # Longitudinal & transverse white steel roof girders casting grid shadows in satellite_topdown.png
    for gx in grid_x:
        add_box_between(bm, (gx, grid_y[0]), (gx, grid_y[-1]), z_grid_top - 0.30, z_grid_top, thickness=0.26, mat_idx=7)
    for gy in grid_y:
        add_box_between(bm, (grid_x[0], gy), (grid_x[-1], gy), z_grid_top - 0.28, z_grid_top + 0.02, thickness=0.26, mat_idx=7)
    # Secondary purlins on northern half of central grid (Y = 256..267)
    for py_sub in (257.8, 259.6, 263.2, 265.0):
        add_box_between(bm, (grid_x[0], py_sub), (grid_x[-1], py_sub), z_grid_top - 0.18, z_grid_top, thickness=0.14, mat_idx=7)

    # 2. Exact Foreground Structure for SV_Cam_Quai_Jacques_Cartier_Pier_Center ([497.368, 248.266, 1.75], heading = 235 deg):
    # Camera forward unit vector: (-0.81915, -0.57358) (SW)
    # Camera right unit vector:   (-0.57358, +0.81915) (NW)
    # Camera left unit vector:    (+0.57358, -0.81915) (SE)
    cam3_x, cam3_y = 497.368, 248.266
    f_ux, f_uy = -math.sin(math.radians(235.0)), math.cos(math.radians(235.0))  # (+0.81915, -0.57358)? Wait!
    # Wait: let's verify Blender's camera forward vector for rotation_euler = (radians(90+pitch), 0, radians(-heading))!
    # In Blender: at rot_z = 0, rot_x = 90 deg, local -Z points along World +Y = (0, 1, 0), and local +X (Right) points along World +X = (1, 0, 0).
    # When rotated by rot_z = -heading_deg around World Z:
    # World Forward = (sin(heading_deg), cos(heading_deg))!
    # World Right   = (cos(heading_deg), -sin(heading_deg))!
    # For heading = 235 deg:
    # sin(235 deg) = -0.81915, cos(235 deg) = -0.57358!
    # So Forward = (-0.81915, -0.57358) (South-West), and Right = (-0.57358, +0.81915) (North-West), Left = (+0.57358, -0.81915) (South-East)!
    fw_x, fw_y = math.sin(math.radians(235.0)), math.cos(math.radians(235.0))
    rt_x, rt_y = math.cos(math.radians(235.0)), -math.sin(math.radians(235.0))

    def c3_pt(fwd_m, right_m):
        return (cam3_x + fw_x * fwd_m + rt_x * right_m, cam3_y + fw_y * fwd_m + rt_y * right_m)

    # (a) Overhead Timber Plank Deck (Z = 3.55m .. 3.68m) covering the upper frame (H1..H4, V1..V8)
    # with an open skylight cutout on the upper-left (fwd = 1.2..2.8m, right = -1.6..-0.3m)
    deck_main_pts = [c3_pt(-1.0, -0.35), c3_pt(6.5, -0.35), c3_pt(6.5, 4.5), c3_pt(-1.0, 4.5)]
    extrude_prism_in_bm(bm, deck_main_pts, 3.58, 3.70, mat_side=5, mat_top=5, mat_bot=5)
    deck_left_far = [c3_pt(2.8, -3.5), c3_pt(6.5, -3.5), c3_pt(6.5, -0.35), c3_pt(2.8, -0.35)]
    extrude_prism_in_bm(bm, deck_left_far, 3.58, 3.70, mat_side=5, mat_top=5, mat_bot=5)

    # Galvanized steel joists running diagonally under the timber deck (spaced every 0.55m)
    for j_i in range(-2, 12):
        jf = j_i * 0.55
        jp1 = c3_pt(jf, -3.2 if jf > 2.6 else -0.35)
        jp2 = c3_pt(jf + 0.3, 4.2)
        add_box_between(bm, jp1, jp2, 3.40, 3.58, thickness=0.10, mat_idx=6, cap_bottom=True)

    # Heavy galvanized primary steel I-beam girders framing the skylight and supporting the joists
    add_box_between(bm, c3_pt(-0.8, -0.35), c3_pt(6.5, -0.35), 3.22, 3.58, thickness=0.22, mat_idx=6, cap_bottom=True)
    add_box_between(bm, c3_pt(2.7, -3.2), c3_pt(2.7, 3.8), 3.22, 3.58, thickness=0.22, mat_idx=6, cap_bottom=True)
    add_box_between(bm, c3_pt(0.8, -2.5), c3_pt(2.7, -0.35), 3.25, 3.58, thickness=0.20, mat_idx=6, cap_bottom=True)

    # Upper deck skylight steel guardrail (visible in H1, V2..V4 of Quai_Jacques_Cartier_Pier_Center.jpg)
    add_box_between(bm, c3_pt(1.0, -0.35), c3_pt(2.7, -0.35), 3.70, 4.65, thickness=0.08, mat_idx=6)
    add_box_between(bm, c3_pt(1.0, -1.6), c3_pt(2.7, -1.6), 3.70, 4.65, thickness=0.08, mat_idx=6)

    # (b) Left Galvanized Steel H-Column (H2..H7, V1..V2) at fwd = 2.65m, right = -1.75m
    col_left_xy = c3_pt(2.65, -1.75)
    add_box_between(bm, c3_pt(2.53, -1.75), c3_pt(2.77, -1.75), 0.16, 3.58, thickness=0.24, mat_idx=6)

    # Low galvanized steel curb beam along the floor in front of the container (H7..H8, V1..V5)
    add_box_between(bm, c3_pt(2.55, -1.65), c3_pt(1.35, 1.45), 0.18, 0.42, thickness=0.24, mat_idx=6)

    # (c) Cream/Beige Corrugated Steel Shipping Container (H3..H8, V2..V8)
    # Angled from (fwd=2.65m, right=-1.45m) to (fwd=1.40m, right=+1.65m)
    # NOTE: Because cont_p1 -> cont_p2 goes Left-to-Right in camera space, the CW normal (nx, ny)
    # points TOWARD the camera (-fwd). Therefore offset_out = -1.20 extrudes the container body
    # AWAY from the camera (+fwd), keeping the front face at cont_p1 -> cont_p2!
    cont_p1 = c3_pt(2.65, -1.45)
    cont_p2 = c3_pt(1.40, 1.65)
    add_box_between(bm, cont_p1, cont_p2, 0.32, 2.86, thickness=2.35, offset_out=-1.20, mat_idx=8, cap_bottom=True)
    # Top corner rail & vertical corrugation ribs on the container face facing Camera 3
    add_box_between(bm, cont_p1, cont_p2, 2.74, 2.88, thickness=0.12, offset_out=0.02, mat_idx=8, cap_bottom=True)
    n_ribs = 22
    for rb_i in range(n_ribs + 1):
        rt = rb_i / n_ribs
        rx = cont_p1[0] + (cont_p2[0] - cont_p1[0]) * rt
        ry = cont_p1[1] + (cont_p2[1] - cont_p1[1]) * rt
        rx2 = cont_p1[0] + (cont_p2[0] - cont_p1[0]) * min(1.0, rt + 0.022)
        ry2 = cont_p1[1] + (cont_p2[1] - cont_p1[1]) * min(1.0, rt + 0.022)
        add_box_between(bm, (rx, ry), (rx2, ry2), 0.36, 2.74, thickness=0.07, offset_out=0.02, mat_idx=8)

    # Orange-Yellow "REAR" warning placard on the lower-right of the container (H7, V7..V8)
    plac_p1 = (cont_p1[0] + (cont_p2[0] - cont_p1[0]) * 0.74, cont_p1[1] + (cont_p2[1] - cont_p1[1]) * 0.74)
    plac_p2 = (cont_p1[0] + (cont_p2[0] - cont_p1[0]) * 0.90, cont_p1[1] + (cont_p2[1] - cont_p1[1]) * 0.90)
    add_box_between(bm, plac_p1, plac_p2, 0.55, 0.88, thickness=0.06, offset_out=0.04, mat_idx=9)
    # Dark vertical container door bar & stenciled code strip on right (V6..V7, H4..H7)
    bar_p1 = (cont_p1[0] + (cont_p2[0] - cont_p1[0]) * 0.67, cont_p1[1] + (cont_p2[1] - cont_p1[1]) * 0.67)
    bar_p2 = (cont_p1[0] + (cont_p2[0] - cont_p1[0]) * 0.69, cont_p1[1] + (cont_p2[1] - cont_p1[1]) * 0.69)
    add_box_between(bm, bar_p1, bar_p2, 0.50, 2.25, thickness=0.06, offset_out=0.04, mat_idx=3)

    # --------------------------------------------------------------------------
    # D. EAST FLAT-ROOFED PAVILION WING (X = 500.5..520.5, Y = 260.0..268.2, V5..V6, H5..H6)
    # --------------------------------------------------------------------------
    ew_pts = [(500.5, 260.0), (520.5, 260.8), (520.2, 268.4), (500.2, 267.6)]
    extrude_prism_in_bm(bm, ew_pts, 0.16, 6.80, mat_side=0, mat_top=None)
    for i in range(4):
        add_box_between(bm, ew_pts[i], ew_pts[(i + 1) % 4], 6.80, 7.35, thickness=0.45, offset_out=0.10, mat_idx=4)
    ew_inner = inset_polygon_toward_centroid(ew_pts, 0.90)
    extrude_prism_in_bm(bm, ew_inner, 6.60, 6.72, mat_side=10, mat_top=10)
    # Rooftop skylight boxes visible in satellite_topdown.png
    add_box_between(bm, (504.0, 264.0), (506.2, 264.1), 6.72, 7.45, thickness=1.8, mat_idx=6)
    add_box_between(bm, (513.5, 264.4), (515.8, 264.5), 6.72, 7.45, thickness=1.8, mat_idx=6)

    # --------------------------------------------------------------------------
    # E. SOUTHERN QUAYSIDE CONCOURSE: TIERED AMPHITHEATER STEPS, CONCRETE CAISSONS,
    #    CANTILEVERED WHITE STEEL CATWALK GALLERY & MASTS (X = 425..558, Y = 235..242)
    #    Framed in SV_Cam_Bassin_Jacques_Cartier_Marina (H1..H5, V1..V6) and Satellite (H6..H7, V1..V8)
    # --------------------------------------------------------------------------
    # 1. Weathered concrete cylindrical caissons & tiered stone amphitheater steps along the marina quay wall
    # Starting at (445.5, 229.0) and running NE along the quayside so Camera 4 sees them on the left (V1..V5, H3..H6)
    caisson_p1 = (444.0, 228.5)
    caisson_p2 = (486.0, 261.0)
    n_caissons = 11
    for ci in range(n_caissons):
        ct = ci / (n_caissons - 1)
        cx = caisson_p1[0] + (caisson_p2[0] - caisson_p1[0]) * ct
        cy = caisson_p1[1] + (caisson_p2[1] - caisson_p1[1]) * ct
        add_cylinder_in_bm(bm, (cx, cy), 0.00, 4.20, 1.45, 1.45, n_seg=14, mat_idx=13)

    # Tiered stone amphitheater steps on the lower left (H4..H6, V1..V3)
    for st_i in range(5):
        st_z0 = st_i * 0.48
        st_z1 = (st_i + 1) * 0.48
        st_off = st_i * 0.55
        add_box_between(bm, (445.0 - st_off * 0.6, 227.5 + st_off * 0.6), (456.0 - st_off * 0.6, 236.5 + st_off * 0.6), st_z0, st_z1, thickness=0.65, mat_idx=4)

    # Cantilevered White Structural Steel Truss Catwalk Gallery (Z = 3.60m .. 4.95m)
    cat_p1 = (443.5, 226.8)
    cat_p2 = (490.0, 263.0)
    # Floor & top chords of catwalk
    add_box_between(bm, cat_p1, cat_p2, 3.55, 3.75, thickness=2.10, mat_idx=5, cap_bottom=True)
    add_box_between(bm, cat_p1, cat_p2, 3.50, 3.78, thickness=0.18, offset_out=1.05, mat_idx=7, cap_bottom=True)
    add_box_between(bm, cat_p1, cat_p2, 3.50, 3.78, thickness=0.18, offset_out=-1.05, mat_idx=7, cap_bottom=True)
    add_box_between(bm, cat_p1, cat_p2, 4.65, 4.82, thickness=0.16, offset_out=1.05, mat_idx=7, cap_bottom=True)
    add_box_between(bm, cat_p1, cat_p2, 4.65, 4.82, thickness=0.16, offset_out=-1.05, mat_idx=7, cap_bottom=True)
    # Upper overhanging canopy roof above catwalk (Z = 5.65m .. 5.90m)
    add_box_between(bm, cat_p1, cat_p2, 5.65, 5.90, thickness=2.60, mat_idx=6, cap_bottom=True)

    # Diagonal Warren truss posts & vertical masts along the catwalk (H1..H4, V1..V6)
    n_truss = 18
    for ti in range(n_truss):
        tt0 = ti / n_truss
        tt1 = (ti + 1) / n_truss
        tx0 = cat_p1[0] + (cat_p2[0] - cat_p1[0]) * tt0
        ty0 = cat_p1[1] + (cat_p2[1] - cat_p1[1]) * tt0
        tx1 = cat_p1[0] + (cat_p2[0] - cat_p1[0]) * tt1
        ty1 = cat_p1[1] + (cat_p2[1] - cat_p1[1]) * tt1
        # Vertical truss post & tall mast (rising to Z = 8.4m)
        add_cylinder_in_bm(bm, (tx0, ty0), 3.55, 8.40, 0.09, 0.06, n_seg=8, mat_idx=7)
        # Diagonal truss web member
        add_strut_3d(bm, (tx0, ty0, 3.60), (tx1, ty1, 4.75), radius=0.06, n_seg=6, mat_idx=7)
        # Diagonal knee brace from caisson up to catwalk
        if ti % 2 == 0:
            add_strut_3d(bm, (tx0 - 0.6, ty0 + 0.6, 2.10), (tx0 + 0.5, ty0 - 0.5, 3.60), radius=0.09, n_seg=6, mat_idx=7)

    # 2. Southern Promenade Overhead Truss Gallery & Diagonal V-Masts along Y = 237..243 (visible across H6..H7, V1..V8 of Satellite)
    south_gal_p1 = (424.0, 236.5)
    south_gal_p2 = (558.0, 243.5)
    add_box_between(bm, south_gal_p1, south_gal_p2, 4.20, 4.55, thickness=2.40, mat_idx=7)
    n_smasts = 22
    for smi in range(n_smasts + 1):
        st = smi / n_smasts
        sx = south_gal_p1[0] + (south_gal_p2[0] - south_gal_p1[0]) * st
        sy = south_gal_p1[1] + (south_gal_p2[1] - south_gal_p1[1]) * st
        add_cylinder_in_bm(bm, (sx, sy), 0.16, 8.80, 0.14, 0.08, n_seg=8, mat_idx=3)
        # Diagonal V-struts casting V-shadows on the southern promenade in satellite_topdown.png
        add_strut_3d(bm, (sx, sy - 1.2, 4.30), (sx - 2.2, sy + 2.5, 8.20), radius=0.07, n_seg=6, mat_idx=3)
        add_strut_3d(bm, (sx, sy - 1.2, 4.30), (sx + 2.2, sy + 2.5, 8.20), radius=0.07, n_seg=6, mat_idx=3)

    # --------------------------------------------------------------------------
    # F. EAST FESTIVAL VILLAGE & CIRQUE BIG-TOP CHAPITEAU (V6..V8, H2..H7, X = 520..558)
    # --------------------------------------------------------------------------
    # 1. Multi-bay white gabled event hall (X = 530.5..548.8, Y = 298.0..318.5, V7..V8, H3)
    for bay_y0, bay_y1 in ((298.0, 304.8), (304.8, 311.6), (311.6, 318.5)):
        add_pitched_shed_in_bm(bm, 530.5, bay_y0, 548.8, bay_y1, 0.20, 4.60, 6.10, ridge_along_x=True, mat_wall=11, mat_roof=11)
    # White auxiliary event tent (X = 520.2..526.4, Y = 298.5..312.0, V6..V7, H3)
    add_pitched_shed_in_bm(bm, 520.2, 298.5, 526.4, 312.0, 0.20, 4.20, 5.40, ridge_along_x=False, mat_wall=11, mat_roof=11)
    # East perimeter white tents (X = 552.0..558.5, Y = 299.0..322.0, V8, H3)
    add_pitched_shed_in_bm(bm, 552.0, 299.0, 558.5, 322.0, 0.20, 4.50, 5.80, ridge_along_x=False, mat_wall=11, mat_roof=11)
    # Warm ochre-yellow canopy tent (X = 531.0..545.8, Y = 290.0..298.0, V7..V8, H4)
    add_pitched_shed_in_bm(bm, 531.0, 290.0, 545.8, 298.0, 0.20, 3.80, 4.90, ridge_along_x=True, mat_wall=12, mat_roof=12)

    # 2. Iconic White Circular Cirque Big-Top Tent (Chapiteau) at (550.8, 261.5), R = 10.6m (V7..V8, H5..H6)
    add_conical_tent_in_bm(bm, (550.8, 261.5), r_base=10.6, z_base=0.20, z_eave=4.20, z_peak=12.40, n_seg=28, mat_wall=11, mat_roof=11, mat_pole=7)
    # White rectangular entry vestibule tent connected to Chapiteau (X = 536.2..543.5, Y = 258.0..265.2, V7, H6)
    add_pyramidal_canopy_in_bm(bm, (536.2, 258.0), (543.5, 265.2), 0.20, 3.40, 5.20, mat_roof=11, mat_pole=7)
    extrude_prism_in_bm(bm, [(536.2, 258.0), (543.5, 258.0), (543.5, 265.2), (536.2, 265.2)], 0.20, 3.40, mat_side=11, mat_top=None)

    finalize_bm_to_mesh(bm, mesh, uv_scale=0.14)
    return obj


# ==============================================================================
# 3. FOUR CENTRAL-NORTH PERGOLA PAVILIONS & NORTH-WEST KIOSQUES DU VIEUX-PORT
# ==============================================================================

def build_pier_pergolas_and_kiosks(dossier, palette, collection):
    name = f"MTL_Owned_Pier_Pergolas_And_Kiosks_{BLOCK_ID}"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Silver_Metal"],           # 0: Galvanized steel pergola frames
        palette["Mat_MTL_Wood_Timber"],            # 1: Timber rafters & kiosk siding
        palette["Mat_MTL_PierreGrise_Limestone"],  # 2: Stone bases
        palette["Mat_MTL_Tensile_White"],          # 3: White modular kiosk roofs/walls
        palette["Mat_MTL_Window_Glass_Dark"],      # 4: Kiosk display glass
        palette["Mat_MTL_CastIron_Black"],         # 5: Trim & frames
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Four Open Steel/Timber Pergola Frames in Central-North Square (H2..H3, V3..V5 of satellite_topdown.png)
    pergola_boxes = [
        (468.2, 315.2, 474.5, 323.8),  # NW Pergola
        (493.2, 315.5, 499.5, 324.0),  # NE Pergola
        (468.2, 298.5, 474.5, 307.2),  # SW Pergola
        (493.2, 298.8, 499.5, 307.5),  # SE Pergola
    ]
    for x0, y0, x1, y1 in pergola_boxes:
        z_top = 4.60
        for px in (x0, x1):
            for py in (y0, 0.5 * (y0 + y1), y1):
                add_cylinder_in_bm(bm, (px, py), 0.20, 0.65, 0.22, 0.20, n_seg=10, mat_idx=2)
                add_cylinder_in_bm(bm, (px, py), 0.65, z_top, 0.12, 0.12, n_seg=10, mat_idx=0)
        # Perimeter steel beams
        add_box_between(bm, (x0, y0), (x0, y1), z_top - 0.25, z_top, thickness=0.22, mat_idx=0)
        add_box_between(bm, (x1, y0), (x1, y1), z_top - 0.25, z_top, thickness=0.22, mat_idx=0)
        # Cross rafters casting crisp horizontal stripe shadows in satellite_topdown.png
        n_raf = 7
        for ri in range(n_raf + 1):
            ry = y0 + ri * ((y1 - y0) / n_raf)
            add_box_between(bm, (x0 - 0.4, ry), (x1 + 0.4, ry), z_top, z_top + 0.20, thickness=0.16, mat_idx=1)
        # Wooden Picnic Tables under each of the 4 Central-North Pergolas (resting on Z = +0.255m walkway)
        tcx = 0.5 * (x0 + x1)
        for tcy in (y0 + 2.4, y1 - 2.4):
            # Table top (Z = 0.96m .. 1.02m)
            add_box_between(bm, (tcx - 1.15, tcy), (tcx + 1.15, tcy), 0.96, 1.02, thickness=0.90, mat_idx=1, cap_bottom=True)
            # Bench seats (Z = 0.66m .. 0.71m)
            add_box_between(bm, (tcx - 1.15, tcy), (tcx + 1.15, tcy), 0.66, 0.71, thickness=0.32, offset_out=0.72, mat_idx=1, cap_bottom=True)
            add_box_between(bm, (tcx - 1.15, tcy), (tcx + 1.15, tcy), 0.66, 0.71, thickness=0.32, offset_out=-0.72, mat_idx=1, cap_bottom=True)
            # Steel A-frame table legs
            for lx_off in (-0.85, 0.85):
                add_box_between(bm, (tcx + lx_off, tcy - 0.72), (tcx + lx_off, tcy + 0.72), 0.255, 0.96, thickness=0.08, mat_idx=5)

    # 2. North-West Kiosques du Vieux-Port (H1, V1..V2 of satellite_topdown.png: X = 432..455, Y = 335..354)
    kiosk_footprints = [
        # West pair
        [(434.0, 342.5), (438.5, 341.2), (440.8, 349.0), (436.3, 350.3)],
        [(438.8, 341.0), (443.2, 339.7), (445.5, 347.5), (441.1, 348.8)],
        # East pair
        [(444.2, 342.5), (449.0, 341.0), (451.8, 350.5), (447.0, 352.0)],
        [(445.0, 336.0), (449.2, 334.5), (451.5, 340.5), (447.3, 342.0)],
    ]
    for k_pts in kiosk_footprints:
        extrude_prism_in_bm(bm, k_pts, 0.20, 3.60, mat_side=3, mat_top=None)
        for i in range(4):
            add_box_between(bm, k_pts[i], k_pts[(i + 1) % 4], 3.45, 3.85, thickness=0.35, offset_out=0.08, mat_idx=0)
            add_box_between(bm, k_pts[i], k_pts[(i + 1) % 4], 1.05, 2.65, thickness=0.08, offset_out=-0.25, mat_idx=4)
        k_inner = inset_polygon_toward_centroid(k_pts, 0.85)
        extrude_prism_in_bm(bm, k_inner, 3.50, 3.68, mat_side=3, mat_top=3)

    # 3. Primary Owned Building 1387776863 (Promenade Kiosk at X=459.1, Y=368.3)
    for bldg in dossier.get("osm_features", {}).get("buildings", []):
        if bldg.get("id") == 1387776863:
            pts = ensure_ccw(clean_poly_pts(bldg["coords_xy"]))
            extrude_prism_in_bm(bm, pts, 0.16, 3.80, mat_side=1, mat_top=None)
            for i in range(len(pts)):
                p1, p2 = pts[i], pts[(i + 1) % len(pts)]
                add_box_between(bm, p1, p2, 0.16, 0.55, thickness=0.50, offset_out=0.12, mat_idx=2)
                add_box_between(bm, p1, p2, 1.10, 2.65, thickness=0.08, offset_out=-0.25, mat_idx=4)
                add_box_between(bm, p1, p2, 3.55, 3.95, thickness=0.55, offset_out=0.15, mat_idx=5)
            inner_k = inset_polygon_toward_centroid(pts, 0.86)
            extrude_prism_in_bm(bm, inner_k, 3.65, 3.82, mat_side=0, mat_top=0)

    finalize_bm_to_mesh(bm, mesh, uv_scale=0.15)
    return obj


# ==============================================================================
# 4. PLACE JACQUES-CARTIER & RUE DE LA COMMUNE EST HERITAGE LIMESTONE BLOCK
#    (Framed in SV_Cam_Rue_de_la_CommuneEst_Quayside [323.726, 336.45], heading 88.8 deg)
# ==============================================================================

def build_place_jacques_cartier_heritage_block(palette, collection):
    """
    Constructs the monumental 4-to-5 story Montreal Pierre Grise limestone commercial/hotel
    building block on the north side of Place Jacques-Cartier / Rue de la Commune Est
    (H1..H6, V1..V5 of Rue_de_la_CommuneEst_Quayside.jpg), complete with:
    - Deeply recessed (0.50m) window bays across all 4 stories (arched 4th-story windows).
    - Rusticated stone corner pilasters, belt courses, and heavy bracketed modillion cornice.
    - 3-story pitched-roof mansard annex with dormers on the west flank (V1, H2..H6).
    - Ground-floor black restaurant awning (V2..V3, H5) and red cafe awning (V4..V5, H5).
    - Potted evergreen shrubs in wooden barrels along the Place Jacques-Cartier pedestrian ramp.
    """
    name = f"MTL_Owned_Place_Jacques_Cartier_Heritage_{BLOCK_ID}"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_PierreGrise_Limestone"],  # 0: Pierre Grise cut-stone ashlar
        palette["Mat_MTL_WarmBuff_Limestone"],     # 1: Dressed stone quoins, sills & belt courses
        palette["Mat_MTL_Window_Glass_Dark"],      # 2: Deeply recessed reflective glass
        palette["Mat_MTL_CastIron_Black"],         # 3: Bracketed cornice, window mullions, black awning
        palette["Mat_MTL_Awning_Red"],             # 4: Red restaurant/cafe awning (V4..V5, H5)
        palette["Mat_MTL_Slate_Roof_Dark"],        # 5: Mansard roof & inset roof cap
        palette["Mat_MTL_Wood_Timber"],            # 6: Barrel planters
        palette["Mat_MTL_Grass_Lawn_PBR"],         # 7: Conical evergreen topiary in barrels
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Main 4-story Pierre Grise Limestone Corner Building
    # Central corner pilaster at (335.0, 340.0) is closest to Camera 2 ([323.726, 336.45], heading 88.8 deg),
    # aligning at V3/V4 boundary (u = 0.36) and peaking at H1/H2 (Z = 10.65m)!
    # Left facade recedes WNW to (328.2, 347.5) so its roofline slopes DOWN to the left (H2/H3 at V1/V2)!
    # Right facade recedes ENE to (360.0, 341.2) so its roofline slopes DOWN to the right (H4 at V5/V6)!
    bldg_pts = [
        (328.2, 347.5),  # 0: SW-West corner (V1/V2 boundary)
        (335.0, 340.0),  # 1: Prominent central corner pilaster (V3/V4 boundary)
        (360.0, 341.2),  # 2: SE corner facing Rue de la Commune Est (V5/V6 boundary)
        (360.0, 355.5),  # 3: NE back corner
        (329.5, 356.5),  # 4: NW back corner
    ]
    z_base = 0.15
    z_top = 10.55

    extrude_prism_in_bm(bm, bldg_pts, z_base, z_top, mat_side=0, mat_top=None)
    inner_roof = inset_polygon_toward_centroid(bldg_pts, 0.90)
    extrude_prism_in_bm(bm, inner_roof, z_top - 0.30, z_top - 0.12, mat_side=5, mat_top=5)

    # Facade articulation on Front Left (0 -> 1) and Front Right (1 -> 2)
    front_edges = [
        (bldg_pts[0], bldg_pts[1], 4, "left_face"),
        (bldg_pts[1], bldg_pts[2], 7, "right_face"),
    ]
    floor_levels = [
        (0.15, 2.95),   # Ground floor storefront
        (3.10, 5.45),   # 2nd floor
        (5.60, 7.90),   # 3rd floor
        (8.05, 10.10),  # 4th floor (arched top windows)
    ]

    for p1, p2, n_bays, face_tag in front_edges:
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        bay_w = seg_len / n_bays
        pier_w = bay_w * 0.30

        # Stone plinth & horizontal floor belt courses
        add_box_between(bm, p1, p2, z_base, 0.85, thickness=0.78, offset_out=0.24, mat_idx=1)
        for fz in (2.98, 5.48, 7.93):
            add_box_between(bm, p1, p2, fz, fz + 0.18, thickness=0.82, offset_out=0.28, mat_idx=1)

        # Monumental dark bracketed cornice at roofline (Z = 10.15m .. 10.75m)
        add_box_between(bm, p1, p2, 10.15, 10.45, thickness=0.95, offset_out=0.35, mat_idx=3, cap_bottom=True)
        add_box_between(bm, p1, p2, 10.45, 10.75, thickness=1.25, offset_out=0.50, mat_idx=3, cap_bottom=True)
        # Decorative cornice corbel brackets every 1.1m
        n_brack = int(seg_len // 1.1)
        for bi in range(n_brack + 1):
            bs = (bi / max(1, n_brack)) * seg_len
            bp1 = (p1[0] + dx * max(0.0, bs - 0.10), p1[1] + dy * max(0.0, bs - 0.10))
            bp2 = (p1[0] + dx * min(seg_len, bs + 0.10), p1[1] + dy * min(seg_len, bs + 0.10))
            add_box_between(bm, bp1, bp2, 9.85, 10.45, thickness=1.05, offset_out=0.40, mat_idx=3, cap_bottom=True)

        # Vertical rusticated limestone piers between window bays
        for b in range(n_bays + 1):
            s0 = max(0.0, b * bay_w - pier_w * 0.5)
            s1 = min(seg_len, b * bay_w + pier_w * 0.5)
            if s1 - s0 > 0.06:
                q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
                q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
                add_box_between(bm, q1, q2, 0.85, 10.15, thickness=0.76, offset_out=0.24, mat_idx=0)

        # Deeply recessed window bays (0.50m recess) on all 4 floors
        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
            ms = 0.5 * (bs0 + bs1)
            mp1 = (p1[0] + dx * (ms - 0.05), p1[1] + dy * (ms - 0.05))
            mp2 = (p1[0] + dx * (ms + 0.05), p1[1] + dy * (ms + 0.05))

            for fl_idx, (fz0, fz1) in enumerate(floor_levels):
                # Sill
                add_box_between(bm, wp1, wp2, fz0, fz0 + 0.15, thickness=0.84, offset_out=0.28, mat_idx=1)
                # Recessed reflective glass (recess = 0.50m relative to outer pier face)
                add_box_between(bm, wp1, wp2, fz0 + 0.15, fz1 - 0.16, thickness=0.10, offset_out=-0.26, mat_idx=2)
                # Center vertical mullion & horizontal transom bar
                add_box_between(bm, mp1, mp2, fz0 + 0.15, fz1 - 0.16, thickness=0.18, offset_out=-0.12, mat_idx=3)
                tz = fz0 + 0.58 * (fz1 - fz0)
                add_box_between(bm, wp1, wp2, tz - 0.05, tz + 0.05, thickness=0.18, offset_out=-0.12, mat_idx=3)
                # Lintel / arch hood
                add_box_between(bm, wp1, wp2, fz1 - 0.16, fz1, thickness=0.84, offset_out=0.28, mat_idx=0 if fl_idx < 3 else 1)

        # Ground-Floor Restaurant Awnings matching Rue_de_la_CommuneEst_Quayside.jpg:
        if face_tag == "left_face":
            # Black Pizzeria Awning spanning bays 1..3 on left face (V2..V3, H5)
            aw_p1 = (p1[0] + dx * (bay_w * 0.8), p1[1] + dy * (bay_w * 0.8))
            aw_p2 = (p1[0] + dx * (bay_w * 3.85), p1[1] + dy * (bay_w * 3.85))
            add_box_between(bm, aw_p1, aw_p2, 2.65, 3.10, thickness=1.45, offset_out=0.65, mat_idx=3, cap_bottom=True)
        elif face_tag == "right_face":
            # Bright Red Cafe Awning spanning first 3 bays on right face (V4..V5, H5)
            aw_p1 = (p1[0] + dx * (bay_w * 0.12), p1[1] + dy * (bay_w * 0.12))
            aw_p2 = (p1[0] + dx * (bay_w * 3.10), p1[1] + dy * (bay_w * 3.10))
            add_box_between(bm, aw_p1, aw_p2, 2.65, 3.12, thickness=1.55, offset_out=0.70, mat_idx=4, cap_bottom=True)

    # West 3-Story Mansard-Roof Annex with Dormer Windows (V1, H2..H6)
    annex_pts = [
        (323.5, 353.0),
        (328.2, 347.5),
        (329.5, 356.5),
        (324.8, 360.2),
    ]
    extrude_prism_in_bm(bm, annex_pts, z_base, 7.60, mat_side=0, mat_top=None)
    add_box_between(bm, annex_pts[0], annex_pts[1], 7.45, 7.80, thickness=0.90, offset_out=0.30, mat_idx=3, cap_bottom=True)
    # Mansard roof slope & 2 dormers
    annex_inner = inset_polygon_toward_centroid(annex_pts, 0.80)
    extrude_prism_in_bm(bm, annex_inner, 7.60, 9.35, mat_side=5, mat_top=5)
    for dt in (0.30, 0.72):
        dx_d = annex_pts[0][0] + (annex_pts[1][0] - annex_pts[0][0]) * dt
        dy_d = annex_pts[0][1] + (annex_pts[1][1] - annex_pts[0][1]) * dt
        add_box_between(bm, (dx_d - 0.5, dy_d + 0.2), (dx_d + 0.5, dy_d - 0.2), 7.75, 9.15, thickness=1.1, offset_out=0.1, mat_idx=5)

    # Potted Conical Evergreen Shrubs in Wooden Barrels along Place Jacques-Cartier (V4..V8, H5..H6)
    barrel_locs = [
        (336.4, 337.0),  # Prominent foreground barrel at V4/V5, H5..H6
        (343.5, 336.6),  # Second barrel down the ramp (V5, H5..H6)
        (350.5, 336.3),  # Third barrel (V6, H5..H6)
        (348.5, 330.8),  # Right-side barrel across pedestrian way (V7, H5..H6)
    ]
    for bx, by in barrel_locs:
        add_cylinder_in_bm(bm, (bx, by), 0.15, 0.78, 0.42, 0.46, n_seg=12, mat_idx=6)
        add_cylinder_in_bm(bm, (bx, by), 0.75, 2.35, 0.52, 0.08, n_seg=12, mat_idx=7)

    # Street sign post on left sidewalk (V2, H5..H7)
    add_cylinder_in_bm(bm, (329.8, 339.4), 0.15, 2.55, 0.04, 0.04, n_seg=8, mat_idx=3)
    add_cylinder_in_bm(bm, (329.8, 339.4), 2.15, 2.55, 0.24, 0.24, n_seg=10, mat_idx=1)

    finalize_bm_to_mesh(bm, mesh, uv_scale=0.16)
    return obj


# ==============================================================================
# 5. OLD PORT ENTRANCE GATEWAY, RAILWAY CROSSING, RED TOTEM & TENSILE CONES
#    (Framed in SV_Cam_Quai_Jacques_Cartier_Entrance_Pergola [377.48, 278.899], heading 52.8 deg)
# ==============================================================================

def build_old_port_entrance_pergolas(palette, collection):
    """
    Constructs the complete Old Port Waterfront Entrance at the foot of Place Jacques-Cartier:
    1. Right-side timber & black steel pergola colonnade (V6..V8, H2..H6).
    2. Railway crossing signal masts with tall red-and-white striped vertical gate arms (V3..V5, H2..H6),
       dual flashing red lights, yellow concrete crash block, and steel railway tracks.
    3. Red Old Port Entrance Totem Portal Arch ("Vieux-Port" red/white portal at V4..V5, H4..H5) + 4 white flagpoles.
    4. White pyramidal tensile pavilion cones across the entrance esplanade (V5..V7, H4..H5).
    """
    name = f"MTL_Owned_Entrance_Pergolas_{BLOCK_ID}"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Wood_Timber"],            # 0: Heavy timber pergola beams
        palette["Mat_MTL_CastIron_Black"],         # 1: Structural black steel columns & railway signal housings
        palette["Mat_MTL_PierreGrise_Limestone"],  # 2: Stone pedestal bases
        palette["Mat_MTL_Awning_Red"],             # 3: Red Old Port entrance totem & red gate stripes
        palette["Mat_MTL_White_Steel"],            # 4: White flagpoles, white gate stripes & signage
        palette["Mat_MTL_Tensile_White"],          # 5: White pyramidal tensile pavilion cones
        palette["Mat_MTL_Canopy_Yellow"],          # 6: Yellow concrete crash block
        palette["Mat_MTL_Silver_Metal"],           # 7: Galvanized signal masts & railway rails
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Right-Side Timber & Black Steel Entrance Pergola (V6..V8, H2..H6)
    # Shifted slightly south-east of camera (377.48, 278.899) so it frames V6..V8 without blocking V1..V5!
    p_start = (380.2, 274.2)
    p_end = (408.0, 294.5)
    g_dx = p_end[0] - p_start[0]
    g_dy = p_end[1] - p_start[1]
    g_len = math.hypot(g_dx, g_dy)
    g_ux, g_uy = g_dx / g_len, g_dy / g_len
    g_nx, g_ny = -g_uy, g_ux  # Points NW toward camera axis

    n_bays = 6
    bay_step = g_len / n_bays
    beam_height = 4.20

    for bi in range(n_bays + 1):
        bx = p_start[0] + g_ux * (bi * bay_step)
        by = p_start[1] + g_uy * (bi * bay_step)
        post_left = (bx + g_nx * 1.4, by + g_ny * 1.4)
        post_right = (bx - g_nx * 2.8, by - g_ny * 2.8)
        for p_loc in (post_left, post_right):
            add_cylinder_in_bm(bm, p_loc, 0.16, 0.55, 0.28, 0.24, n_seg=10, mat_idx=2)
            add_cylinder_in_bm(bm, p_loc, 0.55, beam_height, 0.13, 0.13, n_seg=10, mat_idx=1)
        add_box_between(bm, post_left, post_right, beam_height, beam_height + 0.30, thickness=0.24, mat_idx=0, cap_bottom=True)

    # Longitudinal stringers & overhead rafters
    for side_off in (1.4, -2.8):
        s_p1 = (p_start[0] + g_nx * side_off, p_start[1] + g_ny * side_off)
        s_p2 = (p_end[0] + g_nx * side_off, p_end[1] + g_ny * side_off)
        add_box_between(bm, s_p1, s_p2, beam_height + 0.30, beam_height + 0.55, thickness=0.22, mat_idx=0, cap_bottom=True)

    n_purlins = 24
    for pi in range(n_purlins + 1):
        t = pi / n_purlins
        px = p_start[0] + g_dx * t
        py = p_start[1] + g_dy * t
        r_p1 = (px + g_nx * 1.8, py + g_ny * 1.8)
        r_p2 = (px - g_nx * 3.2, py - g_ny * 3.2)
        add_box_between(bm, r_p1, r_p2, beam_height + 0.55, beam_height + 0.72, thickness=0.11, mat_idx=0, cap_bottom=True)

    # 2. Railway Crossing Tracks, Yellow Bumper Block & Vertical Striped Gate Arms (V3..V5, H2..H6)
    # Steel railway rails crossing diagonally in front of Camera 1 ((377.48, 278.899), heading 52.8 deg)
    trk_p1 = (368.0, 294.5)
    trk_p2 = (402.0, 271.5)
    add_box_between(bm, trk_p1, trk_p2, 0.16, 0.21, thickness=0.12, offset_out=-0.72, mat_idx=7)
    add_box_between(bm, trk_p1, trk_p2, 0.16, 0.21, thickness=0.12, offset_out=0.72, mat_idx=7)

    # Yellow concrete crash block at base of signal mast (V3..V4, H6: (382.2, 285.0))
    add_box_between(bm, (381.6, 284.7), (382.8, 285.5), 0.16, 0.92, thickness=0.85, mat_idx=6)

    # Primary Railway Crossing Signal Mast at (383.2, 284.8) (projects to V4, H2..H6)
    mast1_xy = (383.2, 284.8)
    add_cylinder_in_bm(bm, mast1_xy, 0.16, 4.40, 0.11, 0.09, n_seg=10, mat_idx=7)
    # Control box & dual black flashing light hoods at Z = 2.6m .. 3.4m
    add_box_between(bm, (382.9, 284.6), (383.5, 285.0), 1.25, 2.05, thickness=0.45, mat_idx=7)
    add_box_between(bm, (382.6, 285.2), (383.8, 284.4), 3.05, 3.45, thickness=0.35, mat_idx=1, cap_bottom=True)
    add_box_between(bm, (382.7, 285.1), (383.7, 284.5), 2.35, 2.68, thickness=0.32, mat_idx=1, cap_bottom=True)
    # Tall Vertical Red-and-White Striped Gate Arm rising from Z = 1.8m to Z = 7.6m (H2..H5, V4)
    for seg_i in range(10):
        sz0 = 1.80 + seg_i * 0.58
        sz1 = sz0 + 0.58
        m_stripe = 3 if (seg_i % 2 == 0) else 4
        add_box_between(bm, (383.25, 284.65), (383.42, 284.52), sz0, sz1, thickness=0.14, mat_idx=m_stripe)

    # Secondary Railway Crossing Mast & Vertical Gate Arm at (390.8, 288.2) (V5, H3..H5)
    mast2_xy = (390.8, 288.2)
    add_cylinder_in_bm(bm, mast2_xy, 0.16, 4.00, 0.09, 0.08, n_seg=8, mat_idx=7)
    for seg_i in range(9):
        sz0 = 1.80 + seg_i * 0.55
        sz1 = sz0 + 0.55
        m_stripe = 3 if (seg_i % 2 == 0) else 4
        add_box_between(bm, (390.75, 288.15), (390.92, 288.05), sz0, sz1, thickness=0.13, mat_idx=m_stripe)

    # 3. Red Old Port Entrance Totem Portal Arch ("Vieux-Port" Red/White Gateway at V4..V5, H4..H5)
    # Located at (394.5..399.5, 291.0..294.5)
    totem_p1 = (394.2, 294.2)
    totem_p2 = (398.5, 290.8)
    # Left & Right Red Totem Columns (Z = 0.20m .. 4.90m)
    add_box_between(bm, totem_p1, (395.2, 293.4), 0.20, 4.90, thickness=0.85, mat_idx=3)
    add_box_between(bm, (397.5, 291.6), totem_p2, 0.20, 4.90, thickness=0.85, mat_idx=3)
    # Overhead Red/White Signboard Arch Beam (Z = 3.85m .. 4.90m)
    add_box_between(bm, totem_p1, totem_p2, 3.85, 4.90, thickness=0.90, mat_idx=3, cap_bottom=True)
    add_box_between(bm, (394.8, 293.7), (397.9, 291.3), 4.05, 4.65, thickness=0.96, mat_idx=4)

    # 4 Tall White Flagpoles with Flags just right of the Red Totem (V5..V6, H3..H5)
    for fp_i in range(4):
        fpx = 398.8 + fp_i * 1.45
        fpy = 290.2 - fp_i * 0.85
        add_cylinder_in_bm(bm, (fpx, fpy), 0.20, 8.80, 0.08, 0.05, n_seg=8, mat_idx=4)
        # Flag banner near top of pole
        add_box_between(bm, (fpx, fpy), (fpx + 0.95, fpy - 0.55), 7.20, 8.50, thickness=0.06, mat_idx=3 if fp_i % 2 == 0 else 4)

    # 5. White Pyramidal Tensile Pavilion Cones along the Entrance Esplanade (X = 412..435, Y = 295..318)
    for cone_xy in ((414.0, 298.5), (424.0, 306.0), (434.0, 313.5)):
        cx_c, cy_c = cone_xy
        add_pyramidal_canopy_in_bm(bm, (cx_c - 3.2, cy_c - 3.2), (cx_c + 3.2, cy_c + 3.2), 0.20, 2.80, 5.20, mat_roof=5, mat_pole=4)

    # 6. Iconic White Tubular Steel Old Port Entrance Pergola Arches & Quayside Bollards
    #    along South Side of Rue de la Commune Est (X = 345..415, Y = 324..332)
    #    Framed directly in SV_Cam_Rue_de_la_CommuneEst_Quayside (H4..H6, V6..V8)!
    n_arch_bays = 10
    arch_x0, arch_x1 = 346.0, 414.0
    arch_y_south, arch_y_north = 324.8, 330.8
    arch_step = (arch_x1 - arch_x0) / n_arch_bays
    for ai in range(n_arch_bays + 1):
        ax = arch_x0 + ai * arch_step
        p_south = (ax, arch_y_south)
        p_north = (ax, arch_y_north)
        # Stone plinth bases + white tubular steel columns
        for p_col in (p_south, p_north):
            add_cylinder_in_bm(bm, p_col, 0.16, 0.62, 0.22, 0.19, n_seg=10, mat_idx=2)
            add_cylinder_in_bm(bm, p_col, 0.62, 4.10, 0.11, 0.11, n_seg=10, mat_idx=4)
        # Segmented White Tubular Steel Pergola Arch spanning Y = 324.8 .. 330.8 (rising to Z = 4.85m)
        n_arc_seg = 6
        for s_i in range(n_arc_seg):
            t0 = s_i / n_arc_seg
            t1 = (s_i + 1) / n_arc_seg
            ay0 = arch_y_south + (arch_y_north - arch_y_south) * t0
            ay1 = arch_y_south + (arch_y_north - arch_y_south) * t1
            az0 = 4.10 + 0.78 * math.sin(t0 * math.pi)
            az1 = 4.10 + 0.78 * math.sin(t1 * math.pi)
            add_strut_3d(bm, (ax, ay0, az0), (ax, ay1, az1), radius=0.09, n_seg=8, mat_idx=4)
        # Horizontal white steel tie chord & tall Old Port mast finial (matching V6..V8 skyline in Cam 2!)
        add_strut_3d(bm, (ax, arch_y_south, 4.05), (ax, arch_y_north, 4.05), radius=0.065, n_seg=8, mat_idx=4)
        add_cylinder_in_bm(bm, (ax, 0.5 * (arch_y_south + arch_y_north)), 4.10, 7.60, 0.06, 0.035, n_seg=8, mat_idx=4)

    # Longitudinal white tubular steel purlins & side beams connecting the pergola arches (X = 346..414)
    for py_off, pz_off in ((arch_y_south, 4.10), (arch_y_north, 4.10), (326.3, 4.65), (327.8, 4.88), (329.3, 4.65)):
        add_strut_3d(bm, (arch_x0, py_off, pz_off), (arch_x1, py_off, pz_off), radius=0.075, n_seg=8, mat_idx=4)

    # Quayside Cast-Iron Pedestrian Bollards & Low Rail along South Side of Rue de la Commune Est (X = 345..415, Y = 331.8)
    for b_idx in range(20):
        bx_bol = 345.5 + b_idx * 3.6
        by_bol = 331.8
        add_cylinder_in_bm(bm, (bx_bol, by_bol), 0.18, 1.02, 0.11, 0.09, n_seg=10, mat_idx=1)
        add_cylinder_in_bm(bm, (bx_bol, by_bol), 1.02, 1.12, 0.14, 0.10, n_seg=10, mat_idx=1)
    add_box_between(bm, (345.5, 331.4), (414.0, 331.4), 0.55, 0.62, thickness=0.06, mat_idx=1)
    add_box_between(bm, (345.5, 331.4), (414.0, 331.4), 0.88, 0.95, thickness=0.06, mat_idx=1)

    finalize_bm_to_mesh(bm, mesh, uv_scale=0.15)
    return obj


# ==============================================================================
# 6. LUSH GREEN PROMENADE DU VIEUX-PORT LAWNS, WALKWAYS, CURBS & STREETS
#    (Micro-Stepped Z Hierarchy -> Zero Coplanar Z-Fighting!)
# ==============================================================================

def build_ground_and_streets(dossier, palette, collection_owned):
    mesh = bpy.data.meshes.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}", mesh)
    collection_owned.objects.link(obj)

    materials = [
        palette["Mat_MTL_Plaza_Light_Granite"],    # 0: Warm light limestone/concrete pier plaza (Z = +0.16m)
        palette["Mat_MTL_Cobblestone"],            # 1: Granite sett cobblestone streets & bands (Z = +0.205m)
        palette["Mat_MTL_Street_Asphalt"],         # 2: Charcoal asphalt roadbeds & east service court (Z = +0.20m)
        palette["Mat_MTL_Grass_Lawn_PBR"],         # 3: Lush green park turf lawns (leafy_grass 2K, Z = +0.195m)
        palette["Mat_MTL_Granite_Plinth"],         # 4: Granite curbs (Z = +0.225m)
        palette["Mat_PH_Gravel_Path"],             # 5: Warm crushed limestone/gravel walkways (Z = +0.245m)
        palette["Mat_PH_Herringbone_Pavement"],    # 6: Reddish-buff brick pavers at Place Jacques-Cartier (Z = +0.215m)
        palette["Mat_MTL_Plaza_Charcoal_Granite"], # 7: Dark granite paving bands (Z = +0.210m)
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. CARVED PIER PENINSULA & OLD PORT MAINLAND BASE (Z = -0.25m .. +0.16m)
    # Single unified non-overlapping polygon (strictly excluding Bassin Bonsecours X > 468, Y > 329
    # and Bassin Jacques-Cartier Y < 228) -> ZERO coplanar overlap anywhere on the pier!
    unified_pier_and_mainland_poly = [
        (280.0, 228.0),
        (465.0, 229.5),
        (565.0, 233.5),
        (565.0, 331.2),
        (515.0, 329.5),
        (474.5, 328.2),
        (470.2, 328.6),
        (468.0, 330.5),
        (468.2, 333.5),
        (472.5, 342.5),
        (478.0, 356.0),
        (460.0, 460.0),
        (280.0, 460.0),
    ]
    extrude_prism_in_bm(bm, unified_pier_and_mainland_poly, -0.25, 0.16, mat_side=4, mat_top=0)

    # 2. LUSH GREEN PARK LAWNS (Mat_MTL_Grass_Lawn_PBR at Z = +0.195m) & GRANITE CURBS (Z = +0.225m)
    lawn_polygons = [
        # (a) North-West Promenade du Vieux-Port Tree Bosque Lawn (tucked in V1 so V2 shows paved promenade)
        [(421.0, 290.0), (431.5, 294.0), (435.5, 332.0), (432.0, 355.0), (421.0, 355.0)],
        # (b) North-West Kiosk Courtyard Turf (H1, V1..V2 of satellite_topdown.png: green patch at X=438..447, Y=348..355)
        [(437.5, 347.5), (446.5, 346.5), (448.0, 354.5), (438.5, 354.8)],
        # (c) Entrance Park Median Lawn (visible in Quai_Jacques_Cartier_Entrance_Pergola V2..V5, H5..H6)
        [(378.5, 286.5), (392.0, 290.0), (416.0, 328.0), (398.0, 334.0)],
        # (d) Expanded Central-North Pergola Square North Tree Lawn Strip (H2..H3, V3..V5)
        [(474.6, 315.8), (493.1, 316.1), (493.1, 323.6), (474.6, 323.2)],
        # (e) Expanded Central-North Pergola Square South Tree Lawn Strip (H3, V3..V5)
        [(474.6, 299.0), (493.1, 299.3), (493.1, 307.2), (474.6, 306.8)],
        # (f) Expanded Center Axis Tree Planter Bed 1 (H4, V3..V5: X = 474.6..495.5, Y = 289.2..294.5)
        [(474.6, 289.2), (495.5, 289.6), (495.5, 294.5), (474.6, 294.2)],
        # (g) Center-West Tree Planter Bed 2 north of Hangar 16 (H5, V2..V3: X = 443.5..466.5, Y = 275.5..280.4)
        [(443.5, 275.5), (466.5, 276.0), (466.5, 280.4), (443.5, 279.8)],
        # (h) Central Esplanade South Tree Lawn Strip (H4..H5, V3..V5: X = 474.6..495.5, Y = 275.8..280.4)
        [(474.6, 275.8), (495.5, 276.2), (495.5, 280.4), (474.6, 280.0)],
        # (i) East Pergola Flanking Lawn Strip (H2..H3, V5: X = 499.8..505.5, Y = 315.8..323.5)
        [(499.8, 315.8), (505.5, 316.0), (505.5, 323.5), (499.8, 323.2)],
    ]
    for l_pts in lawn_polygons:
        extrude_prism_in_bm(bm, l_pts, 0.16, 0.195, mat_side=4, mat_top=3)
        for i in range(len(l_pts)):
            add_box_between(bm, l_pts[i], l_pts[(i + 1) % len(l_pts)], 0.16, 0.225, thickness=0.28, mat_idx=4)

    # 3. CRUSHED-STONE / LIMESTONE WALKWAYS & ESPLANADE BANDS (Z = +0.205m .. +0.255m, micro-stepped)
    # (a) Transverse Cobblestone Esplanade Band across H4..H5 (Y = 280.6..288.8, X = 423..526, Z = +0.205m)
    esp_band = [(423.0, 280.6), (526.0, 281.5), (526.0, 288.8), (423.0, 287.5)]
    extrude_prism_in_bm(bm, esp_band, 0.16, 0.205, mat_side=4, mat_top=1)

    # (b) Expanded Crushed-Stone Walkways (Mat_PH_Gravel_Path at Z = +0.255m) with Granite Curbs (Z = +0.225m)
    #     Non-overlapping strips framing the Central-North Pergolas & Esplanade Lawns in H3..H5, V3..V5!
    gravel_walkway_strips = [
        # West Pergola Colonnade Crushed-Stone Walkway (under NW & SW Pergolas)
        [(467.5, 289.2), (474.4, 289.2), (474.4, 324.5), (467.5, 324.5)],
        # East Pergola Colonnade Crushed-Stone Walkway (under NE & SE Pergolas)
        [(493.3, 289.5), (499.6, 289.5), (499.6, 324.8), (493.3, 324.8)],
        # Central E-W Promenade Strip between North & South Pergola Lawns (H3, V3..V5)
        [(474.4, 307.4), (493.3, 307.6), (493.3, 315.6), (474.4, 315.4)],
        # South-Central E-W Crushed-Stone Strip between South Pergola Lawn & Center Axis Lawn (H3..H4, V3..V5)
        [(474.4, 294.7), (493.3, 294.9), (493.3, 298.8), (474.4, 298.6)],
        # Lower-Central E-W Crushed-Stone Parterre Path north of Hangar 16 Steel Grid (H5, V3..V5)
        [(467.5, 269.2), (501.2, 269.8), (501.2, 275.4), (467.5, 274.8)],
    ]
    for gw_pts in gravel_walkway_strips:
        extrude_prism_in_bm(bm, gw_pts, 0.16, 0.255, mat_side=4, mat_top=5)
        for i in range(len(gw_pts)):
            add_box_between(bm, gw_pts[i], gw_pts[(i + 1) % len(gw_pts)], 0.16, 0.225, thickness=0.26, offset_out=0.14, mat_idx=4)

    # (c) Central Pier Cobblestone Floor under Open Steel Frame (X = 473.2..501.2, Y = 239.5..267.8, Z = +0.178m)
    pier_center_cobble = [(473.2, 239.5), (501.2, 240.5), (501.2, 267.8), (473.2, 267.0)]
    extrude_prism_in_bm(bm, pier_center_cobble, 0.16, 0.178, mat_side=4, mat_top=1)

    # (d) East Festival Village Dark Charcoal Asphalt Service Court (V7..V8, H4..H5: X = 528.5..558.0, Y = 271.5..290.0, Z = +0.198m)
    east_asphalt = [(528.5, 271.5), (558.0, 272.0), (558.0, 290.0), (528.5, 289.5)]
    extrude_prism_in_bm(bm, east_asphalt, 0.16, 0.198, mat_side=4, mat_top=2)

    # 4. CAMERA-SPECIFIC FOREGROUND PAVING FOR STREET VIEW CAMERAS 1 & 2:
    # (a) Camera 1 (Quai_Jacques_Cartier_Entrance_Pergola at [377.48, 278.899], heading 52.8 deg):
    # Left sidewalk in light granite pavers (Z = +0.235m), center-bottom fan cobbles (Z = +0.215m), right roadbed (Z = +0.190m)
    cam1_left_granite = [(370.0, 276.0), (381.5, 285.0), (376.5, 290.0), (366.0, 281.0)]
    extrude_prism_in_bm(bm, cam1_left_granite, 0.16, 0.235, mat_side=4, mat_top=0)
    cam1_cobble = [(374.0, 273.0), (408.0, 282.0), (402.0, 295.0), (370.0, 280.0)]
    extrude_prism_in_bm(bm, cam1_cobble, 0.16, 0.208, mat_side=4, mat_top=1)

    # (b) Camera 2 (Rue_de_la_CommuneEst_Quayside at [323.726, 336.45], heading 88.8 deg):
    # Foreground left reddish-brown brick herringbone paving (V1..V4, H7..H8, Z = +0.228m)
    cam2_brick = [(318.0, 333.5), (333.5, 334.0), (333.5, 343.0), (318.0, 345.0)]
    extrude_prism_in_bm(bm, cam2_brick, 0.16, 0.228, mat_side=4, mat_top=6)
    # Place Jacques-Cartier sloped granite sett plaza with light granite linear bands (V4..V8, H6..H8, Z = +0.212m)
    cam2_sett = [(333.5, 324.0), (364.0, 324.0), (364.0, 339.2), (333.5, 339.2)]
    extrude_prism_in_bm(bm, cam2_sett, 0.16, 0.212, mat_side=4, mat_top=7)
    # Light granite decorative banding strips running East down Place Jacques-Cartier (visible in V5..V7, H6..H8)
    add_box_between(bm, (334.0, 335.4), (362.0, 334.2), 0.212, 0.222, thickness=0.45, mat_idx=0)
    add_box_between(bm, (334.0, 332.2), (362.0, 331.0), 0.212, 0.222, thickness=0.45, mat_idx=0)
    # Raised granite sidewalk along heritage building base (Z = +0.245m)
    add_box_between(bm, (324.0, 343.2), (334.2, 338.8), 0.16, 0.248, thickness=2.6, offset_out=1.1, mat_idx=0)
    add_box_between(bm, (334.2, 338.8), (358.0, 337.0), 0.16, 0.248, thickness=2.6, offset_out=1.1, mat_idx=0)

    # 5. Surveyed OSM Roadbeds along Rue de la Commune Est & Rue Saint-Paul Est (clipped away from water basins)
    for hw in dossier.get("osm_features", {}).get("highways", []):
        pts = hw.get("coords_xy", [])
        if len(pts) < 2:
            continue
        hw_name = hw.get("tags", {}).get("name", "")
        if not any(k in hw_name for k in ("Commune", "Saint-Paul", "Marché")):
            continue
        w = 11.0 if "Commune" in hw_name else 7.5
        mat_rd = 2 if "Commune" in hw_name else 1
        z_rd = 0.188 if "Commune" in hw_name else 0.192
        for k in range(len(pts) - 1):
            p1, p2 = pts[k], pts[k + 1]
            if p1[0] > 460.0 or p2[0] > 460.0:
                continue
            add_box_between(bm, p1, p2, 0.16, z_rd, thickness=w, offset_out=0.0, mat_idx=mat_rd)

    finalize_bm_to_mesh(bm, mesh, uv_scale=0.18)
    return obj


# ==============================================================================
# 7. REAL POLY HAVEN 3D TREES, STREETLAMPS & MODULAR SEATING
# ==============================================================================

def load_combined_polyhaven_Templates():
    """
    Loads and merges jacaranda_tree, street_lamp_01, and modular_street_seating from
    assets/polyhaven/models into single recentered, memory-safe shared Mesh data-blocks.
    """
    combined_tree_mesh = None
    ph_tree_blend = os.path.join(POLYHAVEN_DIR, "models", "jacaranda_tree", "jacaranda_tree.blend")
    if os.path.isfile(ph_tree_blend):
        with bpy.data.libraries.load(ph_tree_blend, link=False) as (df, dt):
            dt.objects = list(df.objects)
        loaded_objs = [o for o in dt.objects if o and o.type == "MESH" and o.data]
        if loaded_objs:
            raw_tree_mesh = bpy.data.meshes.new("Raw_Jacaranda_Tree_Mesh")
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
                is_leaf_part = any("leaf" in (mat.name.lower() if mat else "") or "leaves" in (mat.name.lower() if mat else "") or "twig" in (mat.name.lower() if mat else "") for mat in m.materials) or ("leaves" in o.name.lower() or "twigs" in o.name.lower())
                if is_leaf_part and len(bm_part.faces) > 3000:
                    faces_to_del = [f for idx_f, f in enumerate(bm_part.faces) if (idx_f % 5) != 0]
                    bmesh.ops.delete(bm_part, geom=faces_to_del, context="FACES")
                elif len(bm_part.faces) > 8000:
                    bmesh.ops.dissolve_limit(bm_part, angle_limit=math.radians(16.0), verts=bm_part.verts, edges=bm_part.edges)
                for f in bm_part.faces:
                    f.material_index = mat_remap.get(f.material_index, 0)
                tmp_m = bpy.data.meshes.new("TmpTreePart")
                bm_part.to_mesh(tmp_m)
                bm_part.free()
                bm_tree.from_mesh(tmp_m)
                bpy.data.meshes.remove(tmp_m)

            bm_tree.to_mesh(raw_tree_mesh)
            bm_tree.free()
            for mat in mat_list:
                if mat and mat.use_nodes:
                    mname = mat.name.lower()
                    for n in mat.node_tree.nodes:
                        if n.type == "BSDF_PRINCIPLED":
                            if any(k in mname for k in ("leaf", "leaves", "foliage", "twig", "jacaranda")):
                                n.inputs["Base Color"].default_value = (0.15, 0.38, 0.10, 1.0)
                raw_tree_mesh.materials.append(mat)
            raw_tree_mesh.use_fake_user = True
            combined_tree_mesh = raw_tree_mesh

        for o in dt.objects:
            if o:
                try:
                    bpy.data.objects.remove(o, do_unlink=True)
                except Exception:
                    pass

    lamp_mesh = None
    ph_lamp_blend = os.path.join(POLYHAVEN_DIR, "models", "street_lamp_01", "street_lamp_01.blend")
    if os.path.isfile(ph_lamp_blend):
        with bpy.data.libraries.load(ph_lamp_blend, link=False) as (df, dt):
            dt.objects = list(df.objects)
        for o in dt.objects:
            if o and o.type == "MESH" and o.data and lamp_mesh is None:
                lamp_mesh = o.data
                lamp_mesh.use_fake_user = True
            if o:
                try:
                    bpy.data.objects.remove(o, do_unlink=True)
                except Exception:
                    pass

    bench_mesh = None
    ph_bench_blend = os.path.join(POLYHAVEN_DIR, "models", "modular_street_seating", "modular_street_seating.blend")
    if os.path.isfile(ph_bench_blend):
        with bpy.data.libraries.load(ph_bench_blend, link=False) as (df, dt):
            dt.objects = list(df.objects)
        for o in dt.objects:
            if o and o.type == "MESH" and o.data and bench_mesh is None:
                bench_mesh = o.data
                bench_mesh.use_fake_user = True
            if o:
                try:
                    bpy.data.objects.remove(o, do_unlink=True)
                except Exception:
                    pass

    return combined_tree_mesh, lamp_mesh, bench_mesh


def scatter_trees_and_props(dossier, palette, collection_owned):
    tree_mesh, lamp_mesh, bench_mesh = load_combined_polyhaven_Templates()

    # 1. Exact Satellite-Matched Trees inside the Pier Plaza & Promenade (H1..H5, V1..V5 of satellite_topdown.png)
    # Using realistic 0.42..0.58 scale factors (6.5m..9.0m crown diameter matching satellite_topdown.png!)
    satellite_pier_trees = [
        # Central-North Pergola Square North Row (H2, V3..V5)
        (476.5, 320.2, 0.46), (480.8, 320.8, 0.48), (488.2, 320.0, 0.46),
        (489.2, 315.8, 0.44), (500.2, 320.8, 0.48), (502.5, 318.8, 0.44),
        # Central-North Pergola Square South Row (H3, V3..V5)
        (475.8, 304.2, 0.48), (479.8, 303.2, 0.50), (483.5, 304.8, 0.46),
        (488.8, 304.2, 0.48), (491.2, 301.2, 0.45),
        # Center Axis Row of 3 Trees (H4, V4..V5: Y = 291.5)
        (480.8, 291.5, 0.38), (485.8, 291.8, 0.40), (490.8, 291.2, 0.38),
        # Center Tree Cluster (H5, V4..V5: (486.8, 279.2))
        (486.2, 279.5, 0.42), (488.2, 278.2, 0.38),
        # West Row of 5 Trees north of Hangar 16 West Hall (H5, V2..V3: Y = 278.0)
        (446.2, 277.6, 0.38), (450.2, 278.0, 0.40), (454.2, 278.4, 0.40),
        (458.2, 278.4, 0.38), (462.2, 278.0, 0.38),
        # Tree inside Central Steel Grid (H5/H6, V3/V4: (476.5, 260.2))
        (476.5, 260.2, 0.42),
        # North-West Promenade du Vieux-Port Dense Tree Canopy (H1..H4, V1..V2)
        (424.0, 293.0, 0.52), (424.5, 303.0, 0.54), (429.5, 304.5, 0.48),
        (424.0, 314.0, 0.55), (430.0, 317.0, 0.52), (434.5, 321.0, 0.50),
        (425.0, 326.0, 0.56), (430.5, 328.5, 0.52), (435.5, 329.5, 0.48),
        (425.5, 338.0, 0.55), (430.0, 344.0, 0.52), (426.0, 350.0, 0.55),
        # Entrance Camera 1 (Quai_Jacques_Cartier_Entrance_Pergola) Background Trees (V1..V6, H4..H5)
        (388.0, 296.0, 0.48), (393.0, 302.0, 0.52), (401.0, 305.0, 0.50),
        (408.0, 310.0, 0.52), (373.0, 292.0, 0.48), (368.0, 298.0, 0.50),
        # Camera 2 (Rue_de_la_CommuneEst_Quayside) Right-Side Street Trees (V6..V8, H4..H5)
        (362.0, 327.0, 0.46), (372.0, 328.0, 0.48), (382.0, 329.0, 0.48), (394.0, 330.0, 0.50),
    ]
    if tree_mesh:
        for idx, (tx, ty, tscale) in enumerate(satellite_pier_trees):
            yaw = math.radians((idx * 53) % 360)
            t_obj = bpy.data.objects.new(f"Tree_Pier_{idx}", tree_mesh)
            collection_owned.objects.link(t_obj)
            t_obj.location = (tx, ty, 0.20)
            t_obj.rotation_euler = (0.0, 0.0, yaw)
            t_obj.scale = (tscale, tscale, tscale)

    # 2. Surveyed OSM Trees (filtered to exclude water basins, central pier duplicates, and camera foreground cones)
    trees = dossier.get("osm_features", {}).get("trees", [])
    kept_osm = 0
    if tree_mesh:
        for idx, t in enumerate(trees):
            tx, ty = t.get("x"), t.get("y")
            if tx is None or ty is None:
                continue
            # Skip if inside Bassin Bonsecours or Bassin Jacques-Cartier or already covered by satellite_pier_trees
            if (tx > 465.0 and ty > 326.0) or ty < 228.0 or (420.0 <= tx <= 510.0 and 255.0 <= ty <= 355.0):
                continue
            # Skip if blocking Camera 1 or Camera 2 line of sight
            if math.hypot(tx - 377.5, ty - 278.9) < 11.0 or math.hypot(tx - 323.7, ty - 336.5) < 14.0:
                continue
            if tx > 555.0 and ty > 355.0:
                continue
            rnd_yaw = math.radians(float((t.get("id", idx) * 17) % 360))
            rnd_scale = 0.42 + float((t.get("id", idx) * 13) % 14) / 100.0
            t_obj = bpy.data.objects.new(f"Tree_OSM_{idx}", tree_mesh)
            collection_owned.objects.link(t_obj)
            t_obj.location = (tx, ty, 0.20)
            t_obj.rotation_euler = (0.0, 0.0, rnd_yaw)
            t_obj.scale = (rnd_scale, rnd_scale, rnd_scale)
            kept_osm += 1
    print(f"Linked {len(satellite_pier_trees)} satellite-matched pier trees + {kept_osm} OSM trees.")

    # 3. Heritage Cast-Iron Streetlamps (street_lamp_01) & Benches (modular_street_seating)
    lamp_coords = [
        (340.0, 335.0, 0.22), (348.0, 331.8, 0.22), (355.0, 334.0, 0.22),
        (362.0, 331.2, 0.22), (376.0, 330.8, 0.22), (390.0, 330.5, 0.22),
        (404.0, 330.2, 0.22), (375.0, 286.0, 0.22),
        (435.0, 284.0, 0.20), (455.0, 284.5, 0.20), (475.0, 285.0, 0.20),
        (495.0, 285.5, 0.20), (515.0, 286.0, 0.20), (475.0, 326.5, 0.20),
        (495.0, 327.2, 0.20), (515.0, 328.0, 0.20),
    ]
    if lamp_mesh:
        for i, loc in enumerate(lamp_coords):
            l_obj = bpy.data.objects.new(f"StreetLamp_{i}", lamp_mesh)
            collection_owned.objects.link(l_obj)
            l_obj.location = loc
            l_obj.rotation_euler = (0.0, 0.0, math.radians(45.0))

    bench_coords = [
        (445.0, 281.5, 0.20), (460.0, 281.8, 0.20), (482.0, 295.0, 0.20),
        (488.0, 295.0, 0.20), (480.0, 312.0, 0.20), (490.0, 312.0, 0.20),
        (450.0, 233.0, 0.20), (470.0, 234.0, 0.20), (490.0, 235.0, 0.20),
    ]
    if bench_mesh:
        for i, loc in enumerate(bench_coords):
            b_obj = bpy.data.objects.new(f"StreetBench_{i}", bench_mesh)
            collection_owned.objects.link(b_obj)
            b_obj.location = loc
            b_obj.rotation_euler = (0.0, 0.0, math.radians(2.0))


# ==============================================================================
# 8. WORLD, LIGHTING & CAMERA RENDERS
# ==============================================================================

def configure_world_and_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 18
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
    wlinks.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

    if os.path.exists(HDRI_PATH):
        tcoord = wnodes.new("ShaderNodeTexCoord")
        mapping = wnodes.new("ShaderNodeMapping")
        mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(110.0))
        wlinks.new(tcoord.outputs["Generated"], mapping.inputs["Vector"])
        tex_env = wnodes.new("ShaderNodeTexEnvironment")
        tex_env.image = bpy.data.images.load(HDRI_PATH, check_existing=True)
        wlinks.new(mapping.outputs["Vector"], tex_env.inputs["Vector"])
        wlinks.new(tex_env.outputs["Color"], w_bg.inputs["Color"])
    else:
        w_bg.inputs["Color"].default_value = (0.65, 0.75, 0.88, 1.0)

    sun_data = bpy.data.lights.new(name="Sun_Key", type="SUN")
    sun_data.energy = 3.8
    sun_data.color = (1.0, 0.96, 0.88)
    sun_obj = bpy.data.objects.new(name="Sun_Key", object_data=sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.location = (490.0, 287.0, 150.0)
    # Match afternoon sun direction in satellite_topdown.png (casting shadows slightly North-West / North-East)
    sun_obj.rotation_euler = (math.radians(38.0), math.radians(14.0), math.radians(-25.0))

    # Daylight Skylight Bounce Light for SV_Cam_Quai_Jacques_Cartier_Pier_Center under the upper timber deck
    fill_data = bpy.data.lights.new(name="Pier_Center_Skylight_Fill", type="POINT")
    fill_data.energy = 1200.0
    fill_data.color = (0.98, 0.97, 0.95)
    fill_data.shadow_soft_size = 1.8
    fill_obj = bpy.data.objects.new(name="Pier_Center_Skylight_Fill", object_data=fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.location = (497.1, 248.0, 2.85)


def render_overview_snapshot():
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"

    ov_data = bpy.data.cameras.new(name=f"Overview_Cam_{BLOCK_ID}")
    ov_data.angle = math.radians(52.0)
    ov_data.clip_start = 1.0
    ov_data.clip_end = 2500.0
    ov_obj = bpy.data.objects.new(name=f"Overview_Cam_{BLOCK_ID}", object_data=ov_data)
    scene.collection.objects.link(ov_obj)

    target = Vector((485.0, 285.0, 6.0))
    ov_obj.location = (415.0, 175.0, 88.0)
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = SNAPSHOT_PATH
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Block Overview Snapshot -> {SNAPSHOT_PATH}")


def main():
    print(f"Starting High-Poly 3D Build for Block {BLOCK_ID} (Iteration 2 Remodel)...")
    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    master_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(master_col)
    col_owned = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    master_col.children.link(col_owned)

    palette = create_palette()

    print("1. Building carved pier ground stratum, lush green park lawns, curbs & walkways...")
    build_ground_and_streets(dossier, palette, col_owned)

    print("2. Building wave-displaced 2K PBR harbor basins, granite quays, marina docks & Bateau-Mouche/yachts...")
    build_waterfront_quays_and_marina(palette, col_owned)

    print("3. Building Hangar 16, Pavillon Jacques-Cartier, central steel canopy & East Festival Village...")
    build_pavillon_jacques_cartier_and_hangar16(palette, col_owned)

    print("4. Building Central-North pergola square pavilions & North-West Kiosques du Vieux-Port...")
    build_pier_pergolas_and_kiosks(dossier, palette, col_owned)

    print("5. Building Place Jacques-Cartier / Rue de la Commune Est 5-story Pierre Grise heritage block...")
    build_place_jacques_cartier_heritage_block(palette, col_owned)

    print("6. Building Old Port Entrance pergola, railway crossing gates, red totem sign & tensile cones...")
    build_old_port_entrance_pergolas(palette, col_owned)

    print("7. Linking Poly Haven 3D trees, streetlamps, and benches...")
    scatter_trees_and_props(dossier, palette, col_owned)

    print("8. Configuring world, lighting, saving .blend & USD, and rendering overview snapshot...")
    configure_world_and_render()

    print(f"Packing all 2K PBR textures and saving {BLEND_OUT_PATH}...")
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
    bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, selected_objects_only=False, use_instancing=True)

    render_overview_snapshot()
    print(f"Build complete for {BLOCK_ID} (Iteration 3)!")


if __name__ == "__main__":
    main()
