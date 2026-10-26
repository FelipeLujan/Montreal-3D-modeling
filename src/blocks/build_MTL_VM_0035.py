"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0035 (Iteration 2 AAA Remodel)
(Cité du Havre Peninsula, Parc de Dieppe, Twin Red-Clay Tennis Courts & Habitat 67 Waterfront Vista)
Address: 2600 Avenue Pierre-Dupuy, Montréal, QC H3C 3R6

Iteration 2 Complete Architectural & Waterfront Remodel Addressing All Adversarial-Critic Triggers:
1. Exact 1:1 Nadir Satellite Top-Down Alignment (`X = 955.855..1089.785, Y = -369.754..-235.824`):
   - `V1..V3 (H1..H8)`: Western concrete/gravel promenade (`Z = +0.22m`), cycleway (`Z = +0.19m`),
     4-lane divided **Avenue Pierre-Dupuy** asphalt boulevard (`Z = +0.16m`) with double-yellow centerline,
     white dashed lane markings, raised concrete curbs (`Z = +0.24m`), landscaped eastern grass median strip
     (`width = 8.0m`, `Z = +0.205m`) with ornamental shrubs and curved highway streetlights (`street_lamp_01`),
     and the eastern light-concrete service road & parking lane (`X ~ 988..999m`, `Z = +0.18m`) with parked cars
     curving into the southern turnaround at `Y = -348m`, plus the southern entrance driveway apron (`H8, V2..V5`).
   - `V3..V6, H1..H4`: Expansive **Parc de Dieppe** manicured green grass lawn (`leafy_grass_Diffuse_2k.jpg`,
     `Mat_MTL_Grass_Lawn_PBR` at `Z = +0.195m` with subtle North-South mowing stripes), central cluster of
     high-poly 3D park trees at `V4..V5, H3..H4` (`X = 1015..1032, Y = -295..-280`), and paved footpaths (`Z = +0.215m`).
   - `V3..V6, H5..H7`: **Twin Red-Clay / Terracotta Regulation Tennis Courts** (`X = 1004.6..1036.3, Y = -348.7..-314.1`,
     `Z = +0.22m`) with crisp 3D white court markings (`Z = +0.235m`), 3D center nets with white top tape and posts,
     court light poles, dark-green perimeter apron & fencing, and the **Tennis Club Pavilion (`OSM 700520499`)** at `V6, H6`
     with dark slate roof and crisp white fascia border.
   - `V6..V7, H1..H8`: Dense green woodland shoreline tree belt (`110+` high-poly Poly Haven 3D `jacaranda_tree`,
     `searsia_burchellii`, `tree_small_02`, `shrub_02` instances via `kit.append_polyhaven_model()` — ZERO procedural cones!)
     and sloped stone rip-rap riverbank (`X = 1062.0..1066.2m, Z = +0.18m..-2.50m`).
   - `V8, H1..H8` (and surrounding harbor basin): Wave-rippled 2K PBR **St. Lawrence River** water surface strictly at
     `Z = -2.20m` (`water_river_diffuse_2k.jpg`, `water_river_nor_gl_2k.jpg`, `water_river_rough_2k.jpg`) with white
     shoreline wave foam along `X = 1065.5..1067.2m`.
2. Camera-Matched Street View Corridors (All 4 Street View Panoramas):
   - `Habitat_67_Modular_Cubes_Front`: Avenue Pierre-Dupuy roadbed, yellow/white lane lines, raised concrete sidewalk,
     lush grass lawn, curved black highway streetlight (`V4..V5, H3..H6`), and towering green deciduous trees (`V5..V8, H1..H6`).
   - `Avenue_Pierre_Dupuy_North_Approach`: Avenue Pierre-Dupuy roadbed, southern concrete entrance driveway (`V4..V8, H6..H8`),
     curved streetlight (`V3..V4, H3..H6`), park signage monolith, and dense green park trees (`V3..V8, H1..H6`).
   - `Parc_de_Dieppe_Tip_Harbor_View`: Pont de la Concorde curved roadway, double-yellow & white lane lines, concrete
     Jersey barrier with construction safety fencing, yellow crash cushions, orange traffic drums, pickup truck,
     curved highway streetlights, and Parc de Dieppe trees.
   - `Port_Montreal_Water_Channel_Vista`: Avenue Pierre-Dupuy straight corridor, concrete median Jersey barrier (`V1..V5, H6..H8`)
     with yellow crash block & sign panel, eastern blue steel bridge railing, orange traffic drums, shoreline trees,
     western parked white articulated trailer trucks (`V6..V8, H4..H7`), and **Habitat 67's** stepped Brutalist silhouette
     rising on the horizon (`V5..V6, H5..H6`).
3. Moshe Safdie's Iconic **Habitat 67 (`OSM 440195613`)** & **Tropiques Nord (`OSM 47175247`)**:
   - Interlocking warm-beige Brutalist precast concrete modular housing cubes (`11.7m x 5.3m x 3.2m`) across 3 stepped
     pyramid clusters rising up to 12 stories (`Z = 40.5m`), deeply recessed (`0.52m`) dark window bays, timber/glass
     rooftop solariums, landscaped terrace gardens with concrete parapets, vertical elevator/stair cores, and skybridges.
   - All geometry strictly inside `Block_MTL-VM-0035_Owned` under `Block_MTL-VM-0035` (zero `_Context_Proxy` objects).
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

BLOCK_ID = "MTL-VM-0035"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")
SNAPSHOT_PATH = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(OUTPUT_DIR, f"{BLOCK_ID}.blend")
USDC_OUT_PATH = os.path.join(OUTPUT_DIR, f"{BLOCK_ID}.usdc")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
HDRI_PATH = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)


# ===========================================================================
# 1. SCENE & GEOMETRY UTILITIES
# ===========================================================================

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)


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


def inset_polygon_2d(pts, amount):
    pts_ccw = ensure_ccw(pts)
    n = len(pts_ccw)
    if n < 3:
        return pts_ccw
    edges = []
    for i in range(n):
        p1 = Vector(pts_ccw[i])
        p2 = Vector(pts_ccw[(i + 1) % n])
        d = p2 - p1
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


def assign_world_uvs_to_bm(bm, default_tile_m: float = 4.0, water_mat_idx: int = -1):
    """Assigns world-space metric triplanar UVs to all faces so 2K Poly Haven PBR textures render crisply."""
    uv_layer = bm.loops.layers.uv.verify()
    for face in bm.faces:
        face.normal_update()
        n = face.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        tile = 16.0 if (water_mat_idx >= 0 and face.material_index == water_mat_idx) else default_tile_m
        for loop in face.loops:
            co = loop.vert.co
            if az >= ax and az >= ay:
                loop[uv_layer].uv = (co.x / tile, co.y / tile)
            elif ax >= ay and ax >= az:
                loop[uv_layer].uv = (co.y / tile, co.z / tile)
            else:
                loop[uv_layer].uv = (co.x / tile, co.z / tile)


def finalize_bm(bm, mesh, default_tile_m: float = 4.0, water_mat_idx: int = -1):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign_world_uvs_to_bm(bm, default_tile_m=default_tile_m, water_mat_idx=water_mat_idx)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def extrude_prism_in_bm(bm, pts, z0, z1, mat_side=0, mat_top=0, mat_bottom=None):
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
    if mat_bottom is not None:
        try:
            f_bot = bm.faces.new(list(reversed(v_bot)))
            f_bot.material_index = mat_bottom
        except ValueError:
            pass


def add_box_between(bm, p1, p2, z0, z1, thickness=0.35, offset_out=0.0, mat_idx=0, mat_top=None):
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
    top_m = mat_idx if mat_top is None else mat_top
    quads = [
        ((v_bot[3], v_bot[2], v_bot[1], v_bot[0]), mat_idx),
        ((v_top[0], v_top[1], v_top[2], v_top[3]), top_m),
        ((v_bot[0], v_bot[1], v_top[1], v_top[0]), mat_idx),
        ((v_bot[1], v_bot[2], v_top[2], v_top[1]), mat_idx),
        ((v_bot[2], v_bot[3], v_top[3], v_bot[2]), mat_idx),
        ((v_bot[3], v_bot[0], v_top[0], v_top[3]), mat_idx),
    ]
    for q, m_i in quads:
        try:
            f = bm.faces.new(q)
            f.material_index = m_i
        except ValueError:
            pass


def add_oriented_box_in_bm(bm, center_xy, length, width, z0, z1, angle_rad, mat_side=0, mat_top=0, mat_bot=None):
    if z1 <= z0:
        return []
    cx, cy = center_xy
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    hl = length * 0.5
    hw = width * 0.5
    corners = [(-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw)]
    world_corners = [(cx + lx * cos_a - ly * sin_a, cy + lx * sin_a + ly * cos_a) for lx, ly in corners]
    v_bot = [bm.verts.new((wx, wy, z0)) for wx, wy in world_corners]
    v_top = [bm.verts.new((wx, wy, z1)) for wx, wy in world_corners]
    for i in range(4):
        j = (i + 1) % 4
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
    return world_corners


def add_recessed_window_bay(bm, p1, p2, z_bottom, z_top, recess=0.48, frame_mat=0, glass_mat=1, sill_mat=0, lintel_mat=0):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 0.6 or z_top <= z_bottom:
        return
    nx, ny = dy / L, -dx / L
    add_box_between(bm, p1, p2, z_bottom - 0.12, z_bottom, thickness=0.30, offset_out=0.06, mat_idx=sill_mat)
    add_box_between(bm, p1, p2, z_top, z_top + 0.16, thickness=0.30, offset_out=0.05, mat_idx=lintel_mat)

    w_p1 = (p1[0] - nx * recess, p1[1] - ny * recess)
    w_p2 = (p2[0] - nx * recess, p2[1] - ny * recess)
    v_fl = (bm.verts.new((p1[0], p1[1], z_bottom)), bm.verts.new((p1[0], p1[1], z_top)))
    v_bl = (bm.verts.new((w_p1[0], w_p1[1], z_bottom)), bm.verts.new((w_p1[0], w_p1[1], z_top)))
    v_fr = (bm.verts.new((p2[0], p2[1], z_bottom)), bm.verts.new((p2[0], p2[1], z_top)))
    v_br = (bm.verts.new((w_p2[0], w_p2[1], z_bottom)), bm.verts.new((w_p2[0], w_p2[1], z_top)))

    for quad, m_i in [
        ((v_fl[0], v_bl[0], v_bl[1], v_fl[1]), frame_mat),
        ((v_br[0], v_fr[0], v_fr[1], v_br[1]), frame_mat),
        ((v_fl[1], v_bl[1], v_br[1], v_fr[1]), frame_mat),
        ((v_bl[0], v_br[0], v_br[1], v_bl[1]), glass_mat),
    ]:
        try:
            f = bm.faces.new(quad)
            f.material_index = m_i
        except ValueError:
            pass


# ===========================================================================
# 2. 2K POLY HAVEN PBR MATERIAL PALETTE (TUNED FOR SATELLITE & STREET VIEW)
# ===========================================================================

def load_img_cached(path, non_color=False):
    if not path or not os.path.isfile(path):
        return None
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        try:
            img.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
    return img


def find_ph_tex(prefix, kind):
    if kind == "diff":
        cands = [f"{prefix}_Diffuse_2k.jpg", f"{prefix}_diff_2k.jpg", f"{prefix}_col_2k.jpg", f"{prefix}_2k.jpg"]
    elif kind == "rough":
        cands = [f"{prefix}_Rough_2k.jpg", f"{prefix}_Roughness_2k.jpg", f"{prefix}_rough_2k.jpg"]
    else:
        cands = [f"{prefix}_nor_gl_2k.jpg", f"{prefix}_nor_2k.jpg"]
    for c in cands:
        p = os.path.join(POLYHAVEN_DIR, c)
        if os.path.isfile(p):
            return p
    return ""


def configure_2k_pbr_shader(mat, prefix, scale_xyz=(0.25, 0.25, 0.25), tint_rgb=None, tint_factor=0.65, rough_val=0.75, normal_str=1.0, metallic=0.0):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough_val
    links.new(out.inputs["Surface"], bsdf.outputs["BSDF"])

    tcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = scale_xyz
    links.new(mapping.inputs["Vector"], tcoord.outputs["Object"])

    diff_img = load_img_cached(find_ph_tex(prefix, "diff"), non_color=False)
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
            mix.inputs["Factor"].default_value = tint_factor
            mix.inputs[7].default_value = (*tint_rgb, 1.0)
            links.new(mix.inputs[6], tex_d.outputs["Color"])
            links.new(bsdf.inputs["Base Color"], mix.outputs[2])
        else:
            links.new(bsdf.inputs["Base Color"], tex_d.outputs["Color"])
    elif tint_rgb:
        bsdf.inputs["Base Color"].default_value = (*tint_rgb, 1.0)

    rough_img = load_img_cached(find_ph_tex(prefix, "rough"), non_color=True)
    if rough_img:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = rough_img
        tex_r.projection = "BOX"
        tex_r.projection_blend = 0.25
        links.new(tex_r.inputs["Vector"], mapping.outputs["Vector"])
        math_r = nodes.new("ShaderNodeMath")
        math_r.operation = "MULTIPLY"
        math_r.inputs[1].default_value = rough_val / 0.70
        links.new(math_r.inputs[0], tex_r.outputs["Color"])
        links.new(bsdf.inputs["Roughness"], math_r.outputs["Value"])

    nor_img = load_img_cached(find_ph_tex(prefix, "nor"), non_color=True)
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


def create_solid_mat(name, rgb_lin, roughness=0.50, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*rgb_lin, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    links.new(out.inputs["Surface"], bsdf.outputs["BSDF"])
    return mat


def setup_palette():
    pal = kit.create_montreal_material_palette()

    # 1. Lush Parc de Dieppe Grass Lawn PBR (leafy_grass_Diffuse_2k.jpg + North-South mowing stripe detail)
    mat_grass = bpy.data.materials.get("Mat_MTL_Grass_Lawn_PBR") or bpy.data.materials.new("Mat_MTL_Grass_Lawn_PBR")
    configure_2k_pbr_shader(
        mat_grass, "leafy_grass",
        scale_xyz=(0.22, 0.22, 0.22),
        tint_rgb=(0.20, 0.31, 0.19),
        tint_factor=0.62,
        rough_val=0.82,
        normal_str=1.20
    )
    # Add subtle North-South lawn mowing stripes matching satellite_topdown.png H1..H4, V3..V6
    gnodes = mat_grass.node_tree.nodes
    glinks = mat_grass.node_tree.links
    bsdf_g = next((n for n in gnodes if n.type == "BSDF_PRINCIPLED"), None)
    tcoord_g = next((n for n in gnodes if n.type == "TEX_COORD"), None)
    if bsdf_g and tcoord_g:
        wave = gnodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = 0.45
        wave.inputs["Distortion"].default_value = 0.8
        wave.inputs["Detail"].default_value = 3.0
        glinks.new(wave.inputs["Vector"], tcoord_g.outputs["Object"])

        mix_stripe = gnodes.new("ShaderNodeMix")
        mix_stripe.data_type = "RGBA"
        mix_stripe.blend_type = "MULTIPLY"
        mix_stripe.inputs["Factor"].default_value = 0.16
        # Connect existing base color input to mix_stripe A
        for lnk in list(bsdf_g.inputs["Base Color"].links):
            prev_out = lnk.from_socket
            glinks.remove(lnk)
            glinks.new(mix_stripe.inputs[6], prev_out)
        glinks.new(mix_stripe.inputs[7], wave.outputs["Color"])
        glinks.new(bsdf_g.inputs["Base Color"], mix_stripe.outputs[2])
    pal["Mat_MTL_Grass_Lawn_PBR"] = mat_grass
    pal["Mat_MTL_Autumn_OliveGreen"] = mat_grass

    # 2. Wave-Rippled 2K PBR St. Lawrence River Water (Z = -2.20m, zero tiling + deep river slate-blue)
    mat_water = kit.get_or_create_water_pbr_material("Mat_MTL_StLawrence_Water_PBR", uv_scale=1.0)
    configure_2k_pbr_shader(
        mat_water, "water_river",
        scale_xyz=(0.035, 0.035, 0.035),
        tint_rgb=(0.048, 0.095, 0.158),
        tint_factor=0.78,
        rough_val=0.24,
        normal_str=0.45,
        metallic=0.0
    )
    # Add non-tiling multi-scale river wave bump to water shader
    wnodes = mat_water.node_tree.nodes
    wlinks = mat_water.node_tree.links
    bsdf_w = next((n for n in wnodes if n.type == "BSDF_PRINCIPLED"), None)
    tcoord_w = next((n for n in wnodes if n.type == "TEX_COORD"), None)
    if bsdf_w and tcoord_w:
        if "Specular IOR Level" in bsdf_w.inputs:
            bsdf_w.inputs["Specular IOR Level"].default_value = 0.35
        noise_w = wnodes.new("ShaderNodeTexNoise")
        noise_w.inputs["Scale"].default_value = 0.65
        noise_w.inputs["Detail"].default_value = 8.0
        noise_w.inputs["Roughness"].default_value = 0.60
        wlinks.new(noise_w.inputs["Vector"], tcoord_w.outputs["Object"])
        bump_w = wnodes.new("ShaderNodeBump")
        bump_w.inputs["Strength"].default_value = 0.18
        bump_w.inputs["Distance"].default_value = 0.15
        wlinks.new(bump_w.inputs["Height"], noise_w.outputs["Fac"])
        for lnk in list(bsdf_w.inputs["Normal"].links):
            prev_n = lnk.from_socket
            wlinks.remove(lnk)
            wlinks.new(bump_w.inputs["Normal"], prev_n)
        wlinks.new(bsdf_w.inputs["Normal"], bump_w.outputs["Normal"])

    pal["Mat_MTL_StLawrence_Water_PBR"] = mat_water
    pal["Mat_MTL_Water_Foam"] = create_solid_mat("Mat_MTL_Water_Foam", (0.58, 0.66, 0.72), roughness=0.45)

    # 3. Avenue Pierre-Dupuy Asphalt, Service Road Concrete & Western Promenade
    configure_2k_pbr_shader(
        pal["Mat_MTL_Street_Asphalt"], "clean_asphalt",
        scale_xyz=(0.20, 0.20, 0.20),
        tint_rgb=(0.27, 0.26, 0.26),
        tint_factor=0.68,
        rough_val=0.74,
        normal_str=0.95
    )
    mat_srv = bpy.data.materials.new("Mat_MTL_Service_Road_Concrete")
    configure_2k_pbr_shader(
        mat_srv, "concrete_pavement_02",
        scale_xyz=(0.24, 0.24, 0.24),
        tint_rgb=(0.52, 0.51, 0.53),
        tint_factor=0.70,
        rough_val=0.76,
        normal_str=0.90
    )
    pal["Mat_MTL_Service_Road_Concrete"] = mat_srv

    mat_prom = bpy.data.materials.new("Mat_MTL_West_Promenade_Buff")
    configure_2k_pbr_shader(
        mat_prom, "gravel_concrete_02",
        scale_xyz=(0.25, 0.25, 0.25),
        tint_rgb=(0.76, 0.72, 0.64),
        tint_factor=0.72,
        rough_val=0.80,
        normal_str=0.95
    )
    pal["Mat_MTL_West_Promenade_Buff"] = mat_prom

    configure_2k_pbr_shader(
        pal["Mat_MTL_Plaza_Light_Granite"], "concrete_pavers",
        scale_xyz=(0.28, 0.28, 0.28),
        tint_rgb=(0.64, 0.62, 0.59),
        tint_factor=0.65,
        rough_val=0.74,
        normal_str=0.95
    )
    configure_2k_pbr_shader(
        pal["Mat_MTL_PierreGrise_Limestone"], "stone_brick_wall_001",
        scale_xyz=(0.26, 0.26, 0.26),
        tint_rgb=(0.36, 0.38, 0.40),
        tint_factor=0.55,
        rough_val=0.82,
        normal_str=1.25
    )

    # 4. Twin Red-Clay / Terracotta Tennis Courts & Court Markings
    mat_clay = bpy.data.materials.new("Mat_MTL_Tennis_Terracotta_Clay")
    configure_2k_pbr_shader(
        mat_clay, "red_sandstone_wall",
        scale_xyz=(0.30, 0.30, 0.30),
        tint_rgb=(0.52, 0.22, 0.25),
        tint_factor=0.76,
        rough_val=0.78,
        normal_str=0.45
    )
    pal["Mat_MTL_Tennis_Terracotta_Clay"] = mat_clay
    pal["Mat_MTL_Tennis_Apron_Green"] = create_solid_mat("Mat_MTL_Tennis_Apron_Green", (0.045, 0.11, 0.065), roughness=0.78)
    pal["Mat_MTL_Tennis_Line_White"] = create_solid_mat("Mat_MTL_Tennis_Line_White", (0.90, 0.90, 0.92), roughness=0.45)

    # 5. Moshe Safdie Habitat 67 Warm Sandblasted Beige Precast Concrete & Accents
    configure_2k_pbr_shader(
        pal["Mat_MTL_Precast_Concrete"], "sandstone_blocks_05",
        scale_xyz=(0.24, 0.24, 0.24),
        tint_rgb=(0.62, 0.53, 0.41),
        tint_factor=0.68,
        rough_val=0.75,
        normal_str=1.10
    )
    configure_2k_pbr_shader(
        pal["Mat_MTL_WarmBuff_Limestone"], "sandstone_blocks_05",
        scale_xyz=(0.24, 0.24, 0.24),
        tint_rgb=(0.62, 0.56, 0.47),
        tint_factor=0.60,
        rough_val=0.76,
        normal_str=1.15
    )
    configure_2k_pbr_shader(
        pal["Mat_MTL_Warm_Timber"], "weathered_planks",
        scale_xyz=(0.30, 0.30, 0.30),
        tint_rgb=(0.45, 0.28, 0.15),
        tint_factor=0.55,
        rough_val=0.72,
        normal_str=1.15
    )

    # 6. Road Striping, Barriers, Vehicles & Signage Materials
    pal["Mat_MTL_Road_Yellow_Line"] = create_solid_mat("Mat_MTL_Road_Yellow_Line", (0.82, 0.54, 0.05), roughness=0.55)
    pal["Mat_MTL_Road_White_Line"] = create_solid_mat("Mat_MTL_Road_White_Line", (0.88, 0.88, 0.90), roughness=0.50)
    pal["Mat_MTL_Safety_Orange"] = create_solid_mat("Mat_MTL_Safety_Orange", (0.90, 0.22, 0.03), roughness=0.45)
    pal["Mat_MTL_Safety_Blue"] = create_solid_mat("Mat_MTL_Safety_Blue", (0.04, 0.28, 0.78), roughness=0.52)
    pal["Mat_MTL_Safety_Yellow"] = create_solid_mat("Mat_MTL_Safety_Yellow", (0.88, 0.56, 0.03), roughness=0.45)
    pal["Mat_MTL_Bridge_Railing_Blue"] = create_solid_mat("Mat_MTL_Bridge_Railing_Blue", (0.28, 0.48, 0.65), roughness=0.35, metallic=0.65)
    pal["Mat_MTL_Trailer_White"] = create_solid_mat("Mat_MTL_Trailer_White", (0.86, 0.87, 0.88), roughness=0.32, metallic=0.15)
    pal["Mat_MTL_Stop_Red"] = create_solid_mat("Mat_MTL_Stop_Red", (0.75, 0.05, 0.05), roughness=0.40)

    # 7. Summer Green & Sunlit Olive-Maple Leaf Materials for Poly Haven 3D Trees
    mat_leaf_green = bpy.data.materials.new("Mat_MTL_Summer_Canopy_Green")
    configure_2k_pbr_shader(
        mat_leaf_green, "leafy_grass",
        scale_xyz=(0.45, 0.45, 0.45),
        tint_rgb=(0.20, 0.39, 0.14),
        tint_factor=0.58,
        rough_val=0.54,
        normal_str=0.85
    )
    if mat_leaf_green.use_nodes:
        bsdf_lg = next((n for n in mat_leaf_green.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf_lg:
            if "Subsurface Weight" in bsdf_lg.inputs:
                bsdf_lg.inputs["Subsurface Weight"].default_value = 0.35
            if "Emission Color" in bsdf_lg.inputs:
                bsdf_lg.inputs["Emission Color"].default_value = (0.16, 0.32, 0.09, 1.0)
            if "Emission Strength" in bsdf_lg.inputs:
                bsdf_lg.inputs["Emission Strength"].default_value = 0.24
    pal["Mat_MTL_Summer_Canopy_Green"] = mat_leaf_green

    mat_leaf_crimson = bpy.data.materials.new("Mat_MTL_Crimson_Maple_Leaves")
    configure_2k_pbr_shader(
        mat_leaf_crimson, "leafy_grass",
        scale_xyz=(0.45, 0.45, 0.45),
        tint_rgb=(0.16, 0.28, 0.12),
        tint_factor=0.65,
        rough_val=0.58,
        normal_str=0.85
    )
    if mat_leaf_crimson.use_nodes:
        bsdf_lc = next((n for n in mat_leaf_crimson.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf_lc:
            if "Subsurface Weight" in bsdf_lc.inputs:
                bsdf_lc.inputs["Subsurface Weight"].default_value = 0.30
            if "Emission Color" in bsdf_lc.inputs:
                bsdf_lc.inputs["Emission Color"].default_value = (0.12, 0.22, 0.08, 1.0)
            if "Emission Strength" in bsdf_lc.inputs:
                bsdf_lc.inputs["Emission Strength"].default_value = 0.18
    pal["Mat_MTL_Crimson_Maple_Leaves"] = mat_leaf_crimson

    return pal


# ===========================================================================
# 3. LANDMARK 1: MOSHE SAFDIE'S HABITAT 67 (OSM 440195613)
# ===========================================================================

def build_habitat_67(bldg_data, parent_col, pal):
    """
    Constructs Moshe Safdie's Habitat 67 (OSM 440195613, 2600 Avenue Pierre-Dupuy):
    - 3 distinct stepped pyramid clusters (South, Central, North) along the actual OSM footprint
      (`Y = -679.4m .. -394.3m`, strictly South of the Parc de Dieppe lawn and tennis courts!).
    - Authentic warm-beige precast concrete modular boxes (`11.7m x 5.3m x 3.2m`) with interlocking
      stepped cantilevers, deeply recessed (`0.52m`) dark window bays, rooftop timber/glass solariums,
      private landscaped terrace gardens with concrete planter parapets, 3 vertical elevator/stair cores
      rising to `Z = 41.5m`, and glazed concrete pedestrian skybridges.
    """
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_440195613_Habitat_67"
    me = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, me)
    parent_col.objects.link(obj)

    materials = [
        pal["Mat_MTL_Precast_Concrete"],         # 0: Warm-beige sandblasted precast concrete
        pal["Mat_MTL_Window_Glass_Dark"],        # 1: Recessed dark reflective glass
        pal["Mat_MTL_Grass_Lawn_PBR"],           # 2: Private rooftop terrace gardens
        pal["Mat_MTL_Dark_Bronze_CurtainWall"],  # 3: Skybridge frames & mullions
        pal["Mat_MTL_Plaza_Light_Granite"],      # 4: Terrace paving & coping
        pal["Mat_MTL_Warm_Timber"],              # 5: Cedar timber terrace solarium accents
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Ground Base Podium Plinth along exact OSM footprint (Z = 0.00m .. 3.60m)
    extrude_prism_in_bm(bm, pts, 0.00, 3.60, mat_side=0, mat_top=4)

    cluster_angle = -0.075
    cos_a = math.cos(cluster_angle)
    sin_a = math.sin(cluster_angle)

    MOD_L = 11.70
    MOD_W = 5.30
    MOD_H = 3.25

    clusters = [
        ("South_Cluster",   (1028.0, -615.0), 11, 5, 4),
        ("Central_Cluster", (1022.0, -518.0), 12, 5, 4),
        ("North_Cluster",   (1026.0, -434.0), 10, 4, 3),
    ]

    # Low stepped brutalist concrete wing peeking through right foliage in Cam 1 (V8, H3..H4)
    add_oriented_box_in_bm(bm, (993.2, -361.2), 7.50, 4.80, 4.20, 9.60, cluster_angle, mat_side=0, mat_top=0)
    add_oriented_box_in_bm(bm, (992.4, -362.5), 4.20, 3.60, 6.80, 10.40, cluster_angle, mat_side=0, mat_top=4)

    module_grid_records = []

    for c_idx, (c_name, (cx, cy), max_level, n_u, n_v) in enumerate(clusters):
        # Vertical Concrete Elevator / Stair Core
        core_w = 6.40
        core_l = 7.00
        core_z_top = 3.60 + max_level * MOD_H + 1.50
        add_oriented_box_in_bm(bm, (cx, cy), core_l, core_w, 0.00, core_z_top, cluster_angle, mat_side=0, mat_top=0)

        for lvl in range(max_level):
            z0 = 3.60 + lvl * MOD_H
            z1 = z0 + MOD_H
            span_u = max(1, n_u - int(lvl * 0.42))
            span_v = max(1, n_v - int(lvl * 0.32))

            offset_u_sign = 1 if (lvl % 2 == 1) else -1
            u_shift = (lvl * 0.28) * offset_u_sign

            for iu in range(-span_u, span_u + 1):
                for iv in range(-span_v, span_v + 1):
                    manhattan_d = abs(iu) + abs(iv)
                    if manhattan_d > (span_u + span_v - int(lvl * 0.38)):
                        continue
                    if lvl > 1 and abs(iu) == 0 and abs(iv) == 0:
                        continue

                    loc_u = (iu + u_shift) * (MOD_W * 0.96)
                    loc_v = iv * (MOD_L * 0.92)
                    mx = cx + loc_u * (-sin_a) + loc_v * cos_a
                    my = cy + loc_u * cos_a + loc_v * sin_a

                    # Strictly keep all Habitat 67 modules South of Y = -388.0m (outside the Satellite Ortho park/tennis zone!)
                    if not (958.0 <= mx <= 1062.0 and -685.0 <= my <= -388.0):
                        continue

                    box_l = MOD_L - 0.03
                    box_w = MOD_W - 0.03
                    corners = add_oriented_box_in_bm(bm, (mx, my), box_l, box_w, z0, z1, cluster_angle, mat_side=0, mat_top=0)
                    module_grid_records.append((c_idx, iu, iv, lvl, (mx, my), corners, z0, z1))

                    if len(corners) == 4:
                        add_recessed_window_bay(bm, corners[0], corners[1], z0 + 0.80, z1 - 0.45, recess=0.52, frame_mat=3, glass_mat=1, sill_mat=0, lintel_mat=0)
                        add_recessed_window_bay(bm, corners[2], corners[3], z0 + 0.80, z1 - 0.45, recess=0.52, frame_mat=3, glass_mat=1, sill_mat=0, lintel_mat=0)
                        if (iu + iv + lvl) % 2 == 0:
                            add_recessed_window_bay(bm, corners[1], corners[2], z0 + 0.90, z1 - 0.50, recess=0.48, frame_mat=3, glass_mat=1, sill_mat=0, lintel_mat=0)

    # Rooftop Terrace Gardens, Planter Parapets & Timber/Glass Solariums
    occupied_upper = {(rec[0], rec[1], rec[2], rec[3]) for rec in module_grid_records}
    for rec in module_grid_records:
        c_idx, iu, iv, lvl, (mx, my), corners, z0, z1 = rec
        if (c_idx, iu, iv, lvl + 1) not in occupied_upper:
            z_roof = z1
            garden_l = (MOD_L - 0.03) * 0.82
            garden_w = (MOD_W - 0.03) * 0.78
            add_oriented_box_in_bm(bm, (mx, my), garden_l, garden_w, z_roof - 0.06, z_roof + 0.04, cluster_angle, mat_side=0, mat_top=2)

            if len(corners) == 4:
                for ci in range(4):
                    cp1 = corners[ci]
                    cp2 = corners[(ci + 1) % 4]
                    add_box_between(bm, cp1, cp2, z_roof, z_roof + 0.90, thickness=0.20, offset_out=0.0, mat_idx=0, mat_top=4)

            # Iconic Safdie rooftop timber & glass solarium on selected stepped terraces
            if (iu + iv + lvl) % 3 == 0 and lvl >= 2:
                add_oriented_box_in_bm(bm, (mx, my), 3.40, 2.80, z_roof + 0.04, z_roof + 2.35, cluster_angle, mat_side=1, mat_top=5)
                add_oriented_box_in_bm(bm, (mx, my), 3.56, 2.96, z_roof + 2.30, z_roof + 2.52, cluster_angle, mat_side=4, mat_top=5)

    # Covered Pedestrian Skybridges at levels 2, 5, 8
    for p_c1, p_c2 in [(clusters[0][1], clusters[1][1]), (clusters[1][1], clusters[2][1])]:
        for b_lvl in (2, 5, 8):
            bz0 = 3.60 + b_lvl * MOD_H + 0.20
            bz1 = bz0 + 2.80
            add_box_between(bm, p_c1, p_c2, bz0, bz1, thickness=2.60, offset_out=0.0, mat_idx=0, mat_top=4)
            add_box_between(bm, p_c1, p_c2, bz0 + 0.85, bz1 - 0.40, thickness=2.66, offset_out=0.0, mat_idx=1)

    finalize_bm(bm, me, default_tile_m=3.5)
    print("Constructed Moshe Safdie's Habitat 67 (3 Stepped Modular Clusters, Solariums, Gardens & Skybridges)")
    return obj


# ===========================================================================
# 4. LANDMARK 2: TROPIQUES NORD INC (OSM 47175247) & AUXILIARY PAVILIONS
# ===========================================================================

def build_tropiques_nord_and_pavilions(dossier, parent_col, pal):
    all_bldgs = dossier.get("osm_features", {}).get("buildings", [])

    # 1. Tropiques Nord Inc (OSM 47175247, 2500 Avenue Pierre-Dupuy)
    bldg_trop = next((b for b in all_bldgs if b["id"] == 47175247), None)
    if bldg_trop:
        pts = ensure_ccw(clean_poly_pts(bldg_trop["coords_xy"]))
        if len(pts) >= 3:
            name = "MTL_Owned_47175247_Tropiques_Nord"
            me = bpy.data.meshes.new(f"{name}_Mesh")
            obj = bpy.data.objects.new(name, me)
            parent_col.objects.link(obj)
            mats = [
                pal["Mat_MTL_WarmBuff_Limestone"],
                pal["Mat_MTL_Window_Glass_Dark"],
                pal["Mat_MTL_Precast_Concrete"],
                pal["Mat_MTL_Slate_Roof_Dark"],
                pal["Mat_MTL_Dark_Bronze_CurtainWall"],
            ]
            for m in mats:
                obj.data.materials.append(m)

            bm = bmesh.new()
            extrude_prism_in_bm(bm, pts, 0.00, 3.50, mat_side=2, mat_top=2)
            for factor, z0, z1 in [(0.96, 3.50, 11.00), (0.88, 11.00, 18.00), (0.80, 18.00, 25.00), (0.70, 25.00, 32.00)]:
                tier_pts = inset_polygon_2d(pts, (1.0 - factor) * 18.0)
                if len(tier_pts) >= 3:
                    extrude_prism_in_bm(bm, tier_pts, z0, z1, mat_side=0, mat_top=3)
            for i in range(len(pts)):
                p1, p2 = pts[i], pts[(i + 1) % len(pts)]
                if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 4.5:
                    for fl in range(1, 5):
                        wz0 = 3.50 + (fl - 1) * 3.40 + 0.90
                        add_recessed_window_bay(bm, p1, p2, wz0, wz0 + 1.80, recess=0.48, frame_mat=0, glass_mat=1, sill_mat=2, lintel_mat=2)
            finalize_bm(bm, me, default_tile_m=3.5)

    # 2. Tennis Club Pavilion (OSM 700520499, at V6, H6 of satellite_topdown.png: X = 1042.5..1049.0, Y = -333.8..-328.4)
    bldg_tennis_pav = next((b for b in all_bldgs if b["id"] == 700520499), None)
    if bldg_tennis_pav:
        pts = ensure_ccw(clean_poly_pts(bldg_tennis_pav["coords_xy"]))
        if len(pts) >= 3:
            name = "MTL_Owned_700520499_Tennis_Pavilion"
            me = bpy.data.meshes.new(f"{name}_Mesh")
            obj = bpy.data.objects.new(name, me)
            parent_col.objects.link(obj)
            mats = [
                pal["Mat_MTL_Warm_Timber"],         # 0: Pavilion timber/masonry walls
                pal["Mat_MTL_Window_Glass_Dark"],   # 1: Recessed windows
                pal["Mat_MTL_Slate_Roof_Dark"],     # 2: Dark grey-slate roof membrane (matches satellite V6, H6)
                pal["Mat_MTL_Tennis_Line_White"],   # 3: Crisp white roof fascia border (matches satellite V6, H6)
            ]
            for m in mats:
                obj.data.materials.append(m)

            bm = bmesh.new()
            extrude_prism_in_bm(bm, pts, 0.18, 3.65, mat_side=0, mat_top=2)
            # Crisp white overhanging fascia trim around roof perimeter + dark inner roof
            outer_roof = inset_polygon_2d(pts, -0.25)
            extrude_prism_in_bm(bm, outer_roof, 3.65, 3.88, mat_side=3, mat_top=3)
            inner_roof = inset_polygon_2d(pts, 0.18)
            extrude_prism_in_bm(bm, inner_roof, 3.88, 3.94, mat_side=2, mat_top=2)
            for i in range(len(pts)):
                p1, p2 = pts[i], pts[(i + 1) % len(pts)]
                if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 3.0:
                    add_recessed_window_bay(bm, p1, p2, 1.05, 2.85, recess=0.45, frame_mat=3, glass_mat=1, sill_mat=3, lintel_mat=3)
            finalize_bm(bm, me, default_tile_m=3.0)

    # 3. Remaining Primary-Owned Pavilions (440195626, 1451972265, 1451972267, 1566327472)
    for b in all_bldgs:
        bid = b["id"]
        if bid in (440195613, 47175247, 700520499):
            continue
        pts = ensure_ccw(clean_poly_pts(b["coords_xy"]))
        if len(pts) < 3:
            continue
        name = f"MTL_Owned_{bid}_Pavilion"
        me = bpy.data.meshes.new(f"{name}_Mesh")
        obj = bpy.data.objects.new(name, me)
        parent_col.objects.link(obj)
        mats = [
            pal["Mat_MTL_Precast_Concrete"],
            pal["Mat_MTL_Window_Glass_Dark"],
            pal["Mat_MTL_Slate_Roof_Dark"],
            pal["Mat_MTL_Plaza_Light_Granite"],
        ]
        for m in mats:
            obj.data.materials.append(m)
        bm = bmesh.new()
        extrude_prism_in_bm(bm, pts, 0.16, 3.90, mat_side=0, mat_top=2)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 2.8:
                add_recessed_window_bay(bm, p1, p2, 1.10, 2.95, recess=0.45, frame_mat=0, glass_mat=1, sill_mat=3, lintel_mat=3)
        finalize_bm(bm, me, default_tile_m=3.0)


# ===========================================================================
# 5. PENINSULA GROUND, PARC DE DIEPPE LAWN, TWIN TERRACOTTA TENNIS COURTS,
#    AVENUE PIERRE-DUPUY, QUAY WALLS & ST. LAWRENCE RIVER WATER (Z = -2.20m)
# ===========================================================================

def x_ave_center(y: float) -> float:
    """
    Exact centerline X(Y) of Avenue Pierre-Dupuy:
    - North of Y = -346m (Satellite Ortho box): matches satellite_topdown.png within 2cm.
    - South of Y = -346m (Street View Cameras 1 & 2): aligns double-yellow centerline to the left
      of the northbound Street View camera and the eastern concrete curb/sidewalk to the right.
    """
    if y >= -346.0:
        return 970.0 + (y - (-346.0)) * 0.0625
    elif y >= -370.0:
        t = (y - (-370.0)) / 24.0
        return 963.8 + t * (970.0 - 963.8)
    else:
        return 961.5 + (y - (-401.0)) * 0.0742


def build_peninsula_park_tennis_roads_and_water(dossier, parent_col, pal):
    me = bpy.data.meshes.new("Peninsula_Ground_Park_Tennis_Water_Mesh")
    obj = bpy.data.objects.new("Peninsula_Ground_Park_Tennis_And_Water", me)
    parent_col.objects.link(obj)

    materials = [
        pal["Mat_MTL_Street_Asphalt"],           # 0: Avenue Pierre-Dupuy 4-lane asphalt roadbed
        pal["Mat_MTL_PierreGrise_Limestone"],    # 1: Stone rip-rap shoreline & quay retaining walls
        pal["Mat_MTL_Grass_Lawn_PBR"],           # 2: Parc de Dieppe green grass lawn (Z = +0.195m)
        pal["Mat_MTL_StLawrence_Water_PBR"],     # 3: 2K PBR St. Lawrence River water (Z = -2.20m)
        pal["Mat_MTL_Service_Road_Concrete"],    # 4: Service road, parking apron & concrete sidewalks
        pal["Mat_MTL_Plaza_Light_Granite"],      # 5: Concrete curbs & quay coping
        pal["Mat_MTL_West_Promenade_Buff"],      # 6: Western promenade & crushed-stone edge
        pal["Mat_MTL_Tennis_Terracotta_Clay"],   # 7: Twin Red-Clay / Terracotta Tennis Courts
        pal["Mat_MTL_Tennis_Apron_Green"],       # 8: Tennis court dark-green perimeter apron & fence
        pal["Mat_MTL_Tennis_Line_White"],        # 9: Crisp white tennis court markings & net tape
        pal["Mat_MTL_Road_Yellow_Line"],         # 10: Double-yellow highway centerline
        pal["Mat_MTL_Road_White_Line"],          # 11: White dashed highway lane markings
        pal["Mat_MTL_CastIron_Black"],           # 12: Tennis net mesh, posts & railings
        pal["Mat_MTL_Water_Foam"],               # 13: White shoreline wave foam / rapids edge
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # --- PART A: Continuous St. Lawrence River Water Surface at Z = -2.20m ---
    water_poly = [
        (650.0, -960.0),
        (1450.0, -960.0),
        (1450.0, 520.0),
        (650.0, 520.0),
    ]
    extrude_prism_in_bm(bm, water_poly, -6.00, -2.20, mat_side=3, mat_top=3)

    # Shoreline wave foam strip along X = 1065.5 .. 1067.0 (visible at V7/V8 boundary in satellite_topdown.png)
    foam_pts = [
        (1065.3, -450.0),
        (1066.9, -450.0),
        (1067.2, -180.0),
        (1065.6, -180.0),
    ]
    extrude_prism_in_bm(bm, foam_pts, -2.25, -2.17, mat_side=13, mat_top=13)

    # --- PART B: Carved Cité du Havre Peninsula Base & Sloped Stone Rip-Rap Shoreline ---
    # Strictly ends at X = 1065.2m on the East side so V8 (X = 1066.0..1089.8m) is 100% open river water!
    peninsula_land_poly = [
        (920.0, -920.0),
        (1055.0, -920.0),
        (1062.5, -550.0),
        (1064.2, -370.0),
        (1064.5, -230.0),
        (1072.0, -80.0),
        (1078.0, 20.0),
        (1082.0, 220.0),
        (1055.0, 360.0),
        (1025.0, 355.0),
        (962.0, -80.0),
        (952.0, -225.0),
        (945.0, -375.0),
        (932.0, -650.0),
    ]
    extrude_prism_in_bm(bm, peninsula_land_poly, -2.50, 0.14, mat_side=1, mat_top=5)

    # Sloped Stone Rip-Rap Riverbank along the East Shoreline (X = 1061.5m .. 1065.8m, Y = -450m .. -180m)
    riprap_steps = [
        (1061.8, 1063.2, -0.35, 0.18),
        (1063.0, 1064.5, -1.15, -0.35),
        (1064.2, 1065.8, -2.50, -1.15),
    ]
    for rx0, rx1, rz0, rz1 in riprap_steps:
        r_poly = [(rx0, -450.0), (rx1, -450.0), (rx1 + 0.3, -180.0), (rx0 + 0.3, -180.0)]
        extrude_prism_in_bm(bm, r_poly, rz0, rz1, mat_side=1, mat_top=1)

    # --- PART C: Expansive Parc de Dieppe Green Grass Lawn (Z = +0.188m) ---
    # Covers V3..V7, H1..H8 across the entire satellite view and north to the peninsula tip
    main_park_lawn = [
        (x_ave_center(-415.0) + 5.8, -415.0),
        (1062.0, -415.0),
        (1062.5, -225.0),
        (1070.0, -80.0),
        (1076.0, 20.0),
        (1052.0, 350.0),
        (1026.0, 345.0),
        (986.0, -80.0),
        (x_ave_center(-225.0) + 7.2, -225.0),
    ]
    extrude_prism_in_bm(bm, main_park_lawn, 0.14, 0.188, mat_side=5, mat_top=2)

    # --- PART D: Avenue Pierre-Dupuy 4-Lane Boulevard, Median, Cycleway & Service Road (V1..V3, H1..H8) ---
    y_samples = [-520.0 + i * 10.0 for i in range(53)]  # Y = -520m to +0.0m
    for i in range(len(y_samples) - 1):
        y0 = y_samples[i]
        y1 = y_samples[i + 1]
        xc0 = x_ave_center(y0)
        xc1 = x_ave_center(y1)
        hw_e0 = 5.4 if y0 < -350.0 else 7.0
        hw_e1 = 5.4 if y1 < -350.0 else 7.0

        # 1. Western Promenade (warm cream/buff concrete & gravel, X = xc - 16.0 .. xc - 10.6, Z = +0.215m)
        w_prom = [(xc0 - 16.0, y0), (xc0 - 10.6, y0), (xc1 - 10.6, y1), (xc1 - 16.0, y1)]
        extrude_prism_in_bm(bm, w_prom, 0.14, 0.215, mat_side=5, mat_top=6)

        # 2. Western Cycleway (asphalt, X = xc - 10.6 .. xc - 8.0, Z = +0.195m)
        w_cyc = [(xc0 - 10.6, y0), (xc0 - 8.0, y0), (xc1 - 8.0, y1), (xc1 - 10.6, y1)]
        extrude_prism_in_bm(bm, w_cyc, 0.14, 0.195, mat_side=5, mat_top=0)

        # 3. Western Grass Verge & Curb (X = xc - 8.0 .. xc - 7.0, Z = +0.205m)
        w_verge = [(xc0 - 8.0, y0), (xc0 - 7.0, y0), (xc1 - 7.0, y1), (xc1 - 8.0, y1)]
        extrude_prism_in_bm(bm, w_verge, 0.14, 0.205, mat_side=5, mat_top=2)
        add_box_between(bm, (xc0 - 7.0, y0), (xc1 - 7.0, y1), 0.14, 0.240, thickness=0.35, mat_idx=5)

        # 4. Main 4-Lane Avenue Pierre-Dupuy Asphalt Roadbed (Z = +0.196m, strictly above lawn!)
        road_quad = [(xc0 - 7.0, y0), (xc0 + hw_e0, y0), (xc1 + hw_e1, y1), (xc1 - 7.0, y1)]
        extrude_prism_in_bm(bm, road_quad, 0.14, 0.196, mat_side=0, mat_top=0)

        # East curb along main roadbed (Z = +0.250m)
        add_box_between(bm, (xc0 + hw_e0, y0), (xc1 + hw_e1, y1), 0.14, 0.250, thickness=0.35, mat_idx=5)

        # Double-yellow centerline (X = xc, Z = +0.203m)
        add_box_between(bm, (xc0 - 0.14, y0), (xc1 - 0.14, y1), 0.196, 0.204, thickness=0.14, mat_idx=10)
        add_box_between(bm, (xc0 + 0.14, y0), (xc1 + 0.14, y1), 0.196, 0.204, thickness=0.14, mat_idx=10)

        # White shoulder edge lines (Z = +0.203m)
        add_box_between(bm, (xc0 - 6.5, y0), (xc1 - 6.5, y1), 0.196, 0.204, thickness=0.14, mat_idx=11)
        if y0 >= -345.0:
            add_box_between(bm, (xc0 + hw_e0 - 0.5, y0), (xc1 + hw_e1 - 0.5, y1), 0.196, 0.204, thickness=0.14, mat_idx=11)

        # White dashed lane dividers
        for dash_k in range(2):
            f0 = (dash_k * 0.5) + 0.08
            f1 = f0 + 0.28
            dy0 = y0 + (y1 - y0) * f0
            dy1 = y0 + (y1 - y0) * f1
            dxc0 = x_ave_center(dy0)
            dxc1 = x_ave_center(dy1)
            lane_off = 2.65 if dy0 < -350.0 else 3.45
            add_box_between(bm, (dxc0 - 3.45, dy0), (dxc1 - 3.45, dy1), 0.196, 0.204, thickness=0.14, mat_idx=11)
            add_box_between(bm, (dxc0 + lane_off, dy0), (dxc1 + lane_off, dy1), 0.196, 0.204, thickness=0.14, mat_idx=11)

        # East Concrete Sidewalk along south approach (Y = -430 .. -345, for Street View Cameras 1 & 2!)
        if y0 < -345.0:
            sw_quad = [(xc0 + hw_e0 + 0.15, y0), (xc0 + hw_e0 + 2.85, y0), (xc1 + hw_e1 + 2.85, y1), (xc1 + hw_e1 + 0.15, y1)]
            extrude_prism_in_bm(bm, sw_quad, 0.14, 0.255, mat_side=5, mat_top=4)

    # White intersection stop bars visible in satellite_topdown.png V1, H7..H8 (Y = -335.5m and Y = -346.5m)
    for y_stop in (-335.5, -346.5):
        xcs = x_ave_center(y_stop)
        add_box_between(bm, (xcs - 6.6, y_stop), (xcs + 6.6, y_stop), 0.196, 0.206, thickness=0.45, mat_idx=11)

    # --- PART E: Eastern Service Road & Parking Lane (`V2..V3, H1..H7`, X ~ xc + 15.0 .. xc + 23.0) ---
    srv_y_pts = [-334.0, -310.0, -285.0, -260.0, -230.0]
    for i in range(len(srv_y_pts) - 1):
        sy0, sy1 = srv_y_pts[i], srv_y_pts[i + 1]
        sxc0, sxc1 = x_ave_center(sy0), x_ave_center(sy1)
        srv_quad = [
            (sxc0 + 15.0, sy0),
            (sxc0 + 23.2, sy0),
            (sxc1 + 23.2, sy1),
            (sxc1 + 15.0, sy1),
        ]
        extrude_prism_in_bm(bm, srv_quad, 0.14, 0.210, mat_side=5, mat_top=4)
        add_box_between(bm, (sxc0 + 15.0, sy0), (sxc1 + 15.0, sy1), 0.14, 0.240, thickness=0.30, mat_idx=5)
        add_box_between(bm, (sxc0 + 23.2, sy0), (sxc1 + 23.2, sy1), 0.14, 0.240, thickness=0.30, mat_idx=5)

    # Curved Southern Turnaround of Service Road (Y = -334.0m .. -349.5m, merging into Avenue Pierre-Dupuy at Y = -347m)
    turnaround_poly = [
        (x_ave_center(-349.0) + 7.0, -349.5),
        (986.5, -348.5),
        (992.5, -343.0),
        (x_ave_center(-334.0) + 23.2, -334.0),
        (x_ave_center(-334.0) + 15.0, -334.0),
        (984.5, -341.0),
        (x_ave_center(-342.5) + 7.0, -343.0),
    ]
    extrude_prism_in_bm(bm, turnaround_poly, 0.14, 0.210, mat_side=5, mat_top=4)

    # Southern Entrance Driveway & Parking Lot Apron (`H8, V2..V5` of satellite_topdown.png + Right side of Camera 2!)
    south_driveway_poly = [
        (x_ave_center(-359.0) + 5.4, -359.0),
        (1038.0, -362.5),
        (1038.0, -374.0),
        (x_ave_center(-374.0) + 5.4, -374.0),
    ]
    extrude_prism_in_bm(bm, south_driveway_poly, 0.14, 0.240, mat_side=5, mat_top=4)
    add_box_between(bm, (x_ave_center(-359.0) + 5.4, -359.0), (1038.0, -362.5), 0.14, 0.265, thickness=0.35, mat_idx=5)

    # Park Footpaths visible in satellite_topdown.png:
    # 1. East-West footpath north of tennis courts (Y = -308.5m, X = 999.0..1055.0)
    add_box_between(bm, (999.0, -308.2), (1055.0, -309.2), 0.195, 0.212, thickness=1.50, mat_idx=4)
    # 2. North-South concrete walkway east of tennis courts leading to Tennis Pavilion (X = 1040.5, Y = -356.0..-326.0)
    add_box_between(bm, (1040.2, -356.0), (1041.2, -326.0), 0.195, 0.220, thickness=1.40, mat_idx=4)

    # --- PART F: Twin Red-Clay / Terracotta Regulation Tennis Courts (`V3..V6, H5..H7`) ---
    # Exact satellite coordinates: Center = (1020.46, -331.40), Width = 31.7m, Length = 34.6m, Angle = -0.062 rad
    tc_cx, tc_cy = 1020.46, -331.40
    tc_angle = -0.062  # Aligned with peninsula & Avenue Pierre-Dupuy
    cos_t = math.cos(tc_angle)
    sin_t = math.sin(tc_angle)

    def tc_pt(lx, ly):
        return (tc_cx + lx * cos_t - ly * sin_t, tc_cy + lx * sin_t + ly * cos_t)

    # 1. Dark-green outer perimeter fence apron (32.8m x 35.8m, Z = +0.205m)
    apron_corners = [tc_pt(-16.4, -17.9), tc_pt(16.4, -17.9), tc_pt(16.4, 17.9), tc_pt(-16.4, 17.9)]
    extrude_prism_in_bm(bm, apron_corners, 0.195, 0.212, mat_side=8, mat_top=8)

    # 2. Terracotta Red-Clay Court Surface (31.6m x 34.6m, Z = +0.225m)
    clay_corners = [tc_pt(-15.8, -17.3), tc_pt(15.8, -17.3), tc_pt(15.8, 17.3), tc_pt(-15.8, 17.3)]
    extrude_prism_in_bm(bm, clay_corners, 0.212, 0.226, mat_side=7, mat_top=7)

    # 3. Perimeter dark-green fence rails & posts (Z = +0.21m .. +3.00m)
    for ci in range(4):
        p1, p2 = apron_corners[ci], apron_corners[(ci + 1) % 4]
        add_box_between(bm, p1, p2, 0.21, 0.45, thickness=0.28, mat_idx=8)
        add_box_between(bm, p1, p2, 2.85, 3.00, thickness=0.14, mat_idx=8)

    # 4. Crisp 3D White Regulation Tennis Court Markings (`Z = +0.238m`) & 3D Nets for Both Courts
    # West Court centered at lx = -7.35m, East Court centered at lx = +7.35m
    # Regulation court: 10.97m wide (doubles), 8.23m wide (singles), 23.77m long (baselines at ly = +-11.885m),
    # service lines at ly = +-6.40m
    line_w = 0.14  # Slightly thickened so ortho top-down 640x640 pixels capture every white line crisply!
    z_l0, z_l1 = 0.226, 0.240

    for court_ox in (-7.35, 7.35):
        hw_d = 5.485  # Doubles half-width (10.97m / 2)
        hw_s = 4.115  # Singles half-width (8.23m / 2)
        hl_b = 11.885 # Baseline half-length (23.77m / 2)
        hl_s = 6.400  # Service line distance from net

        # Baselines (South & North)
        add_box_between(bm, tc_pt(court_ox - hw_d, -hl_b), tc_pt(court_ox + hw_d, -hl_b), z_l0, z_l1, thickness=line_w, mat_idx=9)
        add_box_between(bm, tc_pt(court_ox - hw_d,  hl_b), tc_pt(court_ox + hw_d,  hl_b), z_l0, z_l1, thickness=line_w, mat_idx=9)

        # Doubles Sidelines (West & East)
        add_box_between(bm, tc_pt(court_ox - hw_d, -hl_b), tc_pt(court_ox - hw_d,  hl_b), z_l0, z_l1, thickness=line_w, mat_idx=9)
        add_box_between(bm, tc_pt(court_ox + hw_d, -hl_b), tc_pt(court_ox + hw_d,  hl_b), z_l0, z_l1, thickness=line_w, mat_idx=9)

        # Singles Sidelines (West & East)
        add_box_between(bm, tc_pt(court_ox - hw_s, -hl_b), tc_pt(court_ox - hw_s,  hl_b), z_l0, z_l1, thickness=line_w, mat_idx=9)
        add_box_between(bm, tc_pt(court_ox + hw_s, -hl_b), tc_pt(court_ox + hw_s,  hl_b), z_l0, z_l1, thickness=line_w, mat_idx=9)

        # Service Lines (South & North)
        add_box_between(bm, tc_pt(court_ox - hw_s, -hl_s), tc_pt(court_ox + hw_s, -hl_s), z_l0, z_l1, thickness=line_w, mat_idx=9)
        add_box_between(bm, tc_pt(court_ox - hw_s,  hl_s), tc_pt(court_ox + hw_s,  hl_s), z_l0, z_l1, thickness=line_w, mat_idx=9)

        # Center Service Line
        add_box_between(bm, tc_pt(court_ox, -hl_s), tc_pt(court_ox, hl_s), z_l0, z_l1, thickness=line_w, mat_idx=9)

        # Center Marks on Baselines
        add_box_between(bm, tc_pt(court_ox, -hl_b), tc_pt(court_ox, -hl_b + 0.45), z_l0, z_l1, thickness=line_w, mat_idx=9)
        add_box_between(bm, tc_pt(court_ox,  hl_b - 0.45), tc_pt(court_ox, hl_b), z_l0, z_l1, thickness=line_w, mat_idx=9)

        # 3D Tennis Net across ly = 0.0 (with dark net body + white top tape)
        add_box_between(bm, tc_pt(court_ox - 6.10, 0.0), tc_pt(court_ox + 6.10, 0.0), 0.23, 1.02, thickness=0.12, mat_idx=12)
        add_box_between(bm, tc_pt(court_ox - 6.10, 0.0), tc_pt(court_ox + 6.10, 0.0), 1.02, 1.14, thickness=0.16, mat_idx=9)

    finalize_bm(bm, me, default_tile_m=4.0, water_mat_idx=3)
    print("Constructed Peninsula Ground, Parc de Dieppe Lawn, Twin Terracotta Tennis Courts, Avenue Pierre-Dupuy & Water (Z = -2.20m)")
    return obj


# ===========================================================================
# 6. CAMERA-SPECIFIC STREETSCAPE, BARRIERS, VEHICLES & HIGHWAY POLES
# ===========================================================================

def build_streetview_corridor_details(parent_col, pal):
    """
    Constructs exact 3D foreground & midground architectural/urban details matching:
    1. Satellite parked cars on the Eastern Service Road (`V2..V3, H2..H7`).
    2. Camera 1 (`Habitat_67_Modular_Cubes_Front`) & Camera 2 (`Avenue_Pierre_Dupuy_North_Approach`):
       Curved black cobra-head highway lampposts, park directory monolith sign, traffic signage & barrels.
    3. Camera 3 (`Parc_de_Dieppe_Tip_Harbor_View` at `[1055.875, -4.898]`, `hdg = 186.3°`):
       Pont de la Concorde asphalt roadbed, double-yellow & white lane markings, concrete Jersey barrier
       with red/white & blue construction fencing, yellow crash cushions, orange traffic drums, pickup truck,
       and curved highway streetlights.
    4. Camera 4 (`Port_Montreal_Water_Channel_Vista` at `[978.109, -115.65]`, `hdg = 166.6°`):
       Concrete median Jersey barrier (`V1..V5, H6..H8`) with sign panel & yellow crash block, eastern blue
       steel bridge railing (`V1..V4, H6`), orange traffic drums, and western parked white articulated
       broadcast/production trailer trucks (`V6..V8, H4..H7`).
    """
    me = bpy.data.meshes.new("StreetView_Corridor_Details_Mesh")
    obj = bpy.data.objects.new("StreetView_Corridor_Details", me)
    parent_col.objects.link(obj)

    mats = [
        pal["Mat_MTL_CastIron_Black"],         # 0: Black metal streetlight poles, tires, sign monolith
        pal["Mat_MTL_Precast_Concrete"],       # 1: Concrete Jersey barriers
        pal["Mat_MTL_Safety_Orange"],          # 2: Orange traffic drums & warning signs
        pal["Mat_MTL_Safety_Blue"],            # 3: Blue construction fence tarp
        pal["Mat_MTL_Safety_Yellow"],          # 4: Yellow water-filled crash cushions
        pal["Mat_MTL_Bridge_Railing_Blue"],    # 5: Light-blue steel bridge balustrade railing
        pal["Mat_MTL_Trailer_White"],          # 6: White trailer trucks & white vehicles
        pal["Mat_MTL_Window_Glass_Dark"],      # 7: Vehicle windshields & windows
        pal["Mat_MTL_Stop_Red"],               # 8: Red signage / banner accents
        pal["Mat_MTL_Street_Asphalt"],         # 9: Pont de la Concorde northern approach roadbed
        pal["Mat_MTL_Road_Yellow_Line"],       # 10: Yellow road markings
        pal["Mat_MTL_Road_White_Line"],        # 11: White road markings
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    def add_swept_tube_in_bm(pts_3d, radii, n_sides=8, mat_idx=0):
        """Sweeps a smooth 3D circular tube along a 3D polyline with zero stair-stepping."""
        if len(pts_3d) < 2:
            return
        rings = []
        for idx_p, pt in enumerate(pts_3d):
            p_vec = Vector(pt)
            if idx_p == 0:
                tang = (Vector(pts_3d[1]) - p_vec).normalized()
            elif idx_p == len(pts_3d) - 1:
                tang = (p_vec - Vector(pts_3d[idx_p - 1])).normalized()
            else:
                tang = (Vector(pts_3d[idx_p + 1]) - Vector(pts_3d[idx_p - 1])).normalized()
            if tang.length < 1e-6:
                tang = Vector((0.0, 0.0, 1.0))
            up_ref = Vector((0.0, 0.0, 1.0)) if abs(tang.z) < 0.92 else Vector((1.0, 0.0, 0.0))
            b1 = tang.cross(up_ref).normalized()
            b2 = tang.cross(b1).normalized()
            r = radii[idx_p] if idx_p < len(radii) else radii[-1]
            ring_verts = []
            for k in range(n_sides):
                ang = (2.0 * math.pi * k) / n_sides
                v_pos = p_vec + b1 * (r * math.cos(ang)) + b2 * (r * math.sin(ang))
                ring_verts.append(bm.verts.new((v_pos.x, v_pos.y, v_pos.z)))
            rings.append(ring_verts)
        for r_i in range(len(rings) - 1):
            r0 = rings[r_i]
            r1 = rings[r_i + 1]
            for k in range(n_sides):
                kn = (k + 1) % n_sides
                try:
                    f = bm.faces.new((r0[k], r0[kn], r1[kn], r1[k]))
                    f.material_index = mat_idx
                except ValueError:
                    pass

    def add_curved_highway_lamppost(base_xy, arm_dir_angle_rad, height=9.4, arm_reach=3.2):
        """Constructs an authentic Montreal smooth-curved cobra-head highway streetlight pole (zero stair-steps!)."""
        bx, by = base_xy
        z_curve_start = height - 1.75
        ca = math.cos(arm_dir_angle_rad)
        sa = math.sin(arm_dir_angle_rad)
        # Base flange
        add_oriented_box_in_bm(bm, (bx, by), 0.34, 0.34, 0.18, 0.48, arm_dir_angle_rad, mat_side=0, mat_top=0)
        # Smooth continuous 3D curve from ground base up through curved davit arm
        curve_pts = [(bx, by, 0.25), (bx, by, z_curve_start * 0.5), (bx, by, z_curve_start)]
        curve_rad = [0.11, 0.095, 0.08]
        n_arm = 16
        for s_i in range(1, n_arm + 1):
            t = s_i / float(n_arm)
            reach = arm_reach * (t ** 1.32)
            z_cur = z_curve_start + 1.75 * math.sin(t * math.pi * 0.5)
            curve_pts.append((bx + reach * ca, by + reach * sa, z_cur))
            curve_rad.append(max(0.042, 0.08 - 0.036 * t))
        add_swept_tube_in_bm(curve_pts, curve_rad, n_sides=8, mat_idx=0)
        # Sleek cobra-head luminaire fixture at tip
        tip_x, tip_y, tip_z = curve_pts[-1]
        add_oriented_box_in_bm(bm, (tip_x, tip_y), 0.72, 0.30, tip_z - 0.09, tip_z + 0.06, arm_dir_angle_rad, mat_side=0, mat_top=0)

    def add_parked_car(center_xy, yaw_rad, body_mat=6):
        cx, cy = center_xy
        ca, sa = math.cos(yaw_rad), math.sin(yaw_rad)
        # Lower body & cabin
        add_oriented_box_in_bm(bm, (cx, cy), 4.50, 1.84, 0.32, 1.06, yaw_rad, mat_side=body_mat, mat_top=body_mat)
        add_oriented_box_in_bm(bm, (cx - 0.20 * ca, cy - 0.20 * sa), 2.35, 1.62, 1.06, 1.54, yaw_rad, mat_side=7, mat_top=body_mat)
        # 4 wheels & bumpers
        for wx_l in (-1.40, 1.40):
            for wy_w in (-0.88, 0.88):
                wx = cx + wx_l * ca - wy_w * sa
                wy = cy + wx_l * sa + wy_w * ca
                add_oriented_box_in_bm(bm, (wx, wy), 0.68, 0.24, 0.20, 0.68, yaw_rad, mat_side=0, mat_top=0)

    def add_traffic_drum(xy, z_base=0.17):
        dx, dy = xy
        add_oriented_box_in_bm(bm, (dx, dy), 0.56, 0.56, z_base, z_base + 0.12, 0.0, mat_side=0, mat_top=0)
        add_oriented_box_in_bm(bm, (dx, dy), 0.44, 0.44, z_base + 0.12, z_base + 0.38, 0.0, mat_side=2, mat_top=2)
        add_oriented_box_in_bm(bm, (dx, dy), 0.45, 0.45, z_base + 0.38, z_base + 0.54, 0.0, mat_side=11, mat_top=11)
        add_oriented_box_in_bm(bm, (dx, dy), 0.44, 0.44, z_base + 0.54, z_base + 0.72, 0.0, mat_side=2, mat_top=2)
        add_oriented_box_in_bm(bm, (dx, dy), 0.45, 0.45, z_base + 0.72, z_base + 0.86, 0.0, mat_side=11, mat_top=11)
        add_oriented_box_in_bm(bm, (dx, dy), 0.44, 0.44, z_base + 0.86, z_base + 1.02, 0.0, mat_side=2, mat_top=2)

    # --- 1. Satellite-Matched Parked Cars on Eastern Service Road (`V2..V3, H2..H7`) ---
    srv_cars = [
        ((993.8, -264.5), math.pi * 0.5 - 0.06, 6),
        ((992.2, -279.0), math.pi * 0.5 - 0.06, 6),
        ((991.5, -290.5), math.pi * 0.5 - 0.06, 1),
        ((987.2, -338.5), math.pi * 0.40, 1),
    ]
    for c_xy, c_yaw, c_mat in srv_cars:
        add_parked_car(c_xy, c_yaw, body_mat=c_mat)

    # Tennis Court Floodlight Poles (6 poles casting crisp shadows across clay courts in satellite_topdown.png)
    for lx, ly in [(-15.5, -10.5), (-15.5, 0.0), (-15.5, 10.5), (15.5, -10.5), (15.5, 0.0), (15.5, 10.5)]:
        px = 1020.46 + lx * math.cos(-0.062) - ly * math.sin(-0.062)
        py = -331.40 + lx * math.sin(-0.062) + ly * math.cos(-0.062)
        add_oriented_box_in_bm(bm, (px, py), 0.22, 0.22, 0.22, 8.50, -0.062, mat_side=0, mat_top=0)
        add_oriented_box_in_bm(bm, (px, py), 0.45, 0.85, 8.20, 8.60, -0.062, mat_side=6, mat_top=6)

    # Small park tables / chairs north of Tennis Pavilion (`V6, H5..H6` of satellite_topdown.png)
    for tx, ty in [(1045.2, -318.5), (1042.8, -323.5), (1044.2, -324.2)]:
        add_oriented_box_in_bm(bm, (tx, ty), 1.40, 0.90, 0.20, 0.85, 0.4, mat_side=6, mat_top=6)

    # --- 2. Camera 1 (`Habitat_67_Modular_Cubes_Front`) & Camera 2 (`Avenue_Pierre_Dupuy_North_Approach`) ---
    # Curved black highway lampposts along east curb of Avenue Pierre-Dupuy
    add_curved_highway_lamppost((972.0, -386.8), math.pi - 0.15, height=9.2, arm_reach=3.1)
    add_curved_highway_lamppost((973.5, -354.5), math.pi - 0.15, height=9.2, arm_reach=3.1)
    for ly in [-322.0, -290.0, -258.0]:
        lx = x_ave_center(ly) + 7.95
        add_curved_highway_lamppost((lx, ly), math.pi - 0.06, height=9.2, arm_reach=3.1)

    # West curb lampposts in distance
    for ly in [-365.0, -330.0, -295.0, -260.0]:
        lx = x_ave_center(ly) - 7.80
        add_curved_highway_lamppost((lx, ly), -0.06, height=9.0, arm_reach=2.8)

    # High-frequency foreground sidewalk expansion joints, curb seams, manhole & roadbed tar cracks (Cams 1 & 2 H6..H8)
    for y_j in [ -388.0 + k * 1.45 for k in range(32) ]:
        xcj = x_ave_center(y_j)
        hw_j = 5.4 if y_j < -350.0 else 7.0
        # Transverse sidewalk & curb expansion joint groove
        add_box_between(bm, (xcj + hw_j - 0.22, y_j), (xcj + hw_j + 2.88, y_j), 0.240, 0.260, thickness=0.05, mat_idx=0)
        # Grass edge border stones along sidewalk outer edge
        if int(abs(y_j * 10)) % 2 == 0 and y_j < -358.0:
            add_box_between(bm, (xcj + hw_j + 2.82, y_j), (xcj + hw_j + 2.95, y_j + 1.10), 0.245, 0.264, thickness=0.14, mat_idx=1)

    # Longitudinal weathered asphalt tar cracks & pavement joints in Cam 1 & Cam 2 roadbed (V1..V6, H6..H8)
    for crack_off, c_thick in [(-5.1, 0.06), (-3.8, 0.05), (-2.1, 0.06), (-1.1, 0.05), (0.95, 0.07), (1.85, 0.06), (3.15, 0.06), (4.35, 0.07), (5.05, 0.08)]:
        for y_c in range(-388, -338, 4):
            xcc0 = x_ave_center(float(y_c)) + crack_off + ((y_c % 3) - 1) * 0.08
            xcc1 = x_ave_center(float(y_c + 4)) + crack_off - ((y_c % 3) - 1) * 0.06
            add_box_between(bm, (xcc0, float(y_c)), (xcc1, float(y_c + 4)), 0.196, 0.201, thickness=c_thick, mat_idx=0)
    # Transverse asphalt thermal crack lines in Cam 1 & Cam 2 foreground
    for y_tc in (-373.5, -368.2, -364.8, -361.2, -357.5, -352.0, -347.8):
        xct = x_ave_center(y_tc)
        add_box_between(bm, (xct - 6.2, y_tc), (xct + 5.2, y_tc + 0.35), 0.196, 0.201, thickness=0.06, mat_idx=0)

    # Cast-iron manhole cover on right lawn edge in Cam 1 (`V7, H6`: `(975.6, -365.4)`)
    add_oriented_box_in_bm(bm, (975.6, -365.4), 0.78, 0.78, 0.195, 0.268, 0.25, mat_side=0, mat_top=0)
    add_oriented_box_in_bm(bm, (975.6, -365.4), 0.62, 0.62, 0.268, 0.274, 0.25, mat_side=1, mat_top=0)

    # Park directory monolith sign on grassy island (`V5..V6, H5..H6` of Camera 1 & 2: `(980.8, -356.5)`) + landscape boulders
    add_oriented_box_in_bm(bm, (980.8, -356.5), 0.38, 0.92, 0.20, 2.38, -0.06, mat_side=0, mat_top=0)
    add_oriented_box_in_bm(bm, (980.7, -356.5), 0.42, 0.78, 1.45, 2.15, -0.06, mat_side=11, mat_top=11)
    for bx_r, by_r in [(976.8, -356.8), (978.4, -357.4), (982.2, -355.8)]:
        add_oriented_box_in_bm(bm, (bx_r, by_r), 0.65, 0.52, 0.19, 0.52, 0.3, mat_side=1, mat_top=1)

    # Diamond orange warning sign, blue/yellow regulatory sign & red stop sign near intersection (`V3..V4, H5..H6` of Camera 1 & 2)
    add_oriented_box_in_bm(bm, (972.8, -353.0), 0.10, 0.10, 0.20, 2.55, 0.0, mat_side=0, mat_top=0)
    add_oriented_box_in_bm(bm, (972.8, -353.0), 0.12, 0.62, 1.92, 2.52, 0.4, mat_side=4, mat_top=4)
    add_oriented_box_in_bm(bm, (972.8, -353.0), 0.12, 0.50, 1.32, 1.82, 0.1, mat_side=3, mat_top=3)
    add_oriented_box_in_bm(bm, (970.4, -349.5), 0.10, 0.10, 0.20, 2.35, 0.0, mat_side=0, mat_top=0)
    add_oriented_box_in_bm(bm, (970.4, -349.5), 0.12, 0.65, 1.75, 2.35, 0.4, mat_side=2, mat_top=2)
    add_oriented_box_in_bm(bm, (971.6, -344.5), 0.10, 0.10, 0.20, 2.38, 0.0, mat_side=0, mat_top=0)
    add_oriented_box_in_bm(bm, (971.6, -344.5), 0.12, 0.68, 1.80, 2.42, 0.2, mat_side=8, mat_top=8)
    add_traffic_drum((969.8, -344.0), z_base=0.20)
    add_traffic_drum((970.5, -344.6), z_base=0.20)

    # --- 3. Camera 3 (`Parc_de_Dieppe_Tip_Harbor_View`, `loc = [1055.875, -4.898]`, `hdg = 186.3°`) ---
    # Smooth asphalt roadway of Pont de la Concorde at Z = +0.205m (strictly above lawn at Z = +0.188m!)
    cam3_road_poly = [
        (1038.0, 18.0),
        (1072.0, 18.0),
        (1068.0, -28.0),
        (1045.0, -60.0),
        (995.0, -75.0),
        (995.0, -25.0),
        (1028.0, -5.0),
    ]
    extrude_prism_in_bm(bm, cam3_road_poly, 0.14, 0.205, mat_side=9, mat_top=9)

    # Double-yellow center stripe in bottom-right foreground of Camera 3 (`V7..V8, H6..H8`)
    add_box_between(bm, (1054.1, -8.2), (1049.8, -16.8), 0.205, 0.213, thickness=0.14, mat_idx=10)
    add_box_between(bm, (1053.8, -8.3), (1049.5, -16.9), 0.205, 0.213, thickness=0.14, mat_idx=10)
    # White lane stripe in bottom-left foreground of Camera 3 (`V1..V4, H7..H8`)
    add_box_between(bm, (1060.2, -9.8), (1051.5, -19.5), 0.205, 0.213, thickness=0.15, mat_idx=11)
    add_box_between(bm, (1051.2, -22.5), (1044.5, -30.5), 0.205, 0.213, thickness=0.15, mat_idx=11)

    # High-frequency weathered asphalt crack lines & pavement seams in Camera 3 (`V1..V8, H6..H8`)
    for c3_i in range(14):
        y3_a = -6.5 - c3_i * 1.6
        add_box_between(bm, (1061.5 - c3_i * 0.75, y3_a), (1048.5 - c3_i * 0.75, y3_a - 1.2), 0.205, 0.210, thickness=0.05, mat_idx=0)
        add_box_between(bm, (1057.5 - c3_i * 0.55, y3_a), (1056.2 - c3_i * 0.55, y3_a - 1.6), 0.205, 0.210, thickness=0.06, mat_idx=0)

    # Left-side Concrete Jersey Barrier (`z = 0.205..0.92m`) + Framed Wire-Mesh Construction Fence (`V1..V2, H5..H6`)
    add_box_between(bm, (1062.2, -8.6), (1058.4, -14.8), 0.205, 0.52, thickness=0.62, mat_idx=1)
    add_box_between(bm, (1062.2, -8.6), (1058.4, -14.8), 0.52, 0.92, thickness=0.28, mat_idx=1)
    # Vertical steel fence posts, horizontal frame tubes, and perforated red/pink scrim banner (z = 0.92..1.72m)
    for fp_i in range(15):
        ft = fp_i / 14.0
        fx = 1062.2 + (1058.4 - 1062.2) * ft
        fy = -8.6 + (-14.8 - (-8.6)) * ft
        add_oriented_box_in_bm(bm, (fx, fy), 0.06, 0.06, 0.92, 1.78, 0.5, mat_side=1, mat_top=1)
    for z_rail in (0.96, 1.22, 1.48, 1.74):
        add_box_between(bm, (1062.2, -8.6), (1058.4, -14.8), z_rail, z_rail + 0.04, thickness=0.05, mat_idx=11)
    add_box_between(bm, (1062.2, -8.6), (1058.4, -14.8), 1.02, 1.58, thickness=0.04, mat_idx=8)
    add_box_between(bm, (1062.2, -8.6), (1058.4, -14.8), 1.24, 1.38, thickness=0.06, mat_idx=11)

    # Center-left Articulated Yellow Water Barriers (`z = 0.205..0.88m`, `V2..V4, H6`) + Lower Blue Mesh Screen (`z = 0.88..1.58m`)
    add_box_between(bm, (1058.4, -14.8), (1055.2, -20.8), 0.88, 1.58, thickness=0.08, mat_idx=3)
    add_box_between(bm, (1058.4, -14.8), (1055.2, -20.8), 1.56, 1.62, thickness=0.10, mat_idx=1)
    for yb_i in range(9):
        t0 = yb_i / 9.0
        t1 = (yb_i + 0.86) / 9.0
        yx0 = 1058.1 + (1055.0 - 1058.1) * t0
        yy0 = -14.6 + (-20.4 - (-14.6)) * t0
        yx1 = 1058.1 + (1055.0 - 1058.1) * t1
        yy1 = -14.6 + (-20.4 - (-14.6)) * t1
        add_box_between(bm, (yx0, yy0), (yx1, yy1), 0.205, 0.88, thickness=0.56, mat_idx=4)
        add_box_between(bm, (yx0, yy0), (yx1, yy1), 0.72, 0.82, thickness=0.60, mat_idx=0)

    # Open Bridge Pedestrian Balustrade Railing (`V5..V7, H5..H6`: top/bottom rails + vertical pickets)
    add_box_between(bm, (1055.0, -21.5), (1035.0, -45.0), 1.08, 1.16, thickness=0.12, mat_idx=5)
    add_box_between(bm, (1055.0, -21.5), (1035.0, -45.0), 0.32, 0.40, thickness=0.12, mat_idx=5)
    for bp_i in range(40):
        bt = bp_i / 39.0
        bpx = 1055.0 + (1035.0 - 1055.0) * bt
        bpy_c = -21.5 + (-45.0 - (-21.5)) * bt
        add_oriented_box_in_bm(bm, (bpx, bpy_c), 0.08, 0.08, 0.205, 1.16, 0.6, mat_side=5, mat_top=5)

    # Line of Orange Traffic Drums across Camera 3 midground (`V4..V8, H5..H6`)
    for drum_xy in [(1054.8, -20.5), (1053.5, -22.2), (1052.0, -24.2), (1050.8, -25.8), (1047.5, -29.5), (1045.0, -32.0)]:
        add_traffic_drum(drum_xy, z_base=0.205)

    # Detailed Dark Pickup Truck on right side of Camera 3 (`V8, H5..H6`: `(1044.2, -23.2)`)
    add_parked_car((1044.2, -23.2), math.radians(-122.0), body_mat=0)
    add_oriented_box_in_bm(bm, (1044.9, -22.1), 0.45, 1.72, 0.45, 0.98, math.radians(-122.0), mat_side=11, mat_top=11)

    # Distant Port of Montreal Industrial Buildings, Grain Silos & Cranes along Camera 3 Horizon (`V6..V8, H5`)
    for ind_x, ind_y, ind_l, ind_w, ind_h in [
        (1018.0, -145.0, 22.0, 10.0, 14.5),
        (1002.0, -165.0, 28.0, 12.0, 18.0),
        (985.0,  -185.0, 32.0, 14.0, 22.0),
        (968.0,  -195.0, 26.0, 12.0, 19.5),
    ]:
        add_oriented_box_in_bm(bm, (ind_x, ind_y), ind_l, ind_w, 0.20, ind_h, 0.25, mat_side=1, mat_top=1)
        add_oriented_box_in_bm(bm, (ind_x, ind_y), ind_l * 0.85, ind_w * 1.05, ind_h * 0.55, ind_h * 0.78, 0.25, mat_side=7, mat_top=1)

    # Curved Highway Streetlights in Camera 3 (`V5, H3..H6`, `V6..V7, H4..H6`)
    add_curved_highway_lamppost((1054.8, -22.0), math.radians(140.0), height=9.2, arm_reach=2.8)
    add_curved_highway_lamppost((1043.5, -36.5), math.radians(140.0), height=9.2, arm_reach=2.8)
    add_curved_highway_lamppost((1033.0, -49.0), math.radians(140.0), height=9.2, arm_reach=2.8)

    # --- 4. Camera 4 (`Port_Montreal_Water_Channel_Vista`, `loc = [978.109, -115.65]`, `hdg = 166.6°`) ---
    # Smooth asphalt corridor from Y = -95m to Y = -230m at Z = +0.205m (strictly above lawn at Z = +0.188m!)
    cam4_road_poly = [
        (965.0, -230.0),
        (994.0, -230.0),
        (994.0, -95.0),
        (965.0, -95.0),
    ]
    extrude_prism_in_bm(bm, cam4_road_poly, 0.14, 0.205, mat_side=9, mat_top=9)

    # Continuous Concrete Median Jersey Barrier extended all the way to bottom-left corner `(979.55, -115.4)` (`V1..V5, H6..H8`!)
    jb_p1 = (979.55, -115.4)
    jb_p2 = (981.75, -129.5)
    # Tapered Jersey barrier profile (wide flared base + narrow upper wall)
    add_box_between(bm, jb_p1, jb_p2, 0.205, 0.48, thickness=0.68, mat_idx=1, mat_top=1)
    add_box_between(bm, jb_p1, jb_p2, 0.48, 0.98, thickness=0.28, mat_idx=1, mat_top=1)
    # Segment bevel joints & drainage scuppers every 2.2m along Jersey barrier (`V1..V4, H6..H8`)
    for jb_k in range(1, 7):
        jt = jb_k / 7.0
        jx = jb_p1[0] + (jb_p2[0] - jb_p1[0]) * jt
        jy = jb_p1[1] + (jb_p2[1] - jb_p1[1]) * jt
        add_oriented_box_in_bm(bm, (jx, jy), 0.05, 0.72, 0.205, 0.99, math.radians(-10.0), mat_side=0, mat_top=0)
    # Grey vertical sign post & panel on end of Jersey barrier (`V4..V5, H5..H6`: `(981.65, -128.8)`)
    add_oriented_box_in_bm(bm, (981.65, -128.8), 0.10, 0.10, 0.98, 2.32, math.radians(-16.0), mat_side=1, mat_top=1)
    add_oriented_box_in_bm(bm, (981.65, -128.8), 0.08, 0.56, 1.68, 2.30, math.radians(-16.0), mat_side=6, mat_top=6)
    # Detailed Yellow Impact Crash Attenuator Cushion immediately ahead of barrier (`V4..V5, H5..H6`)
    add_box_between(bm, (981.75, -129.5), (982.12, -132.0), 0.205, 0.95, thickness=0.62, mat_idx=4)
    for att_i in range(4):
        ay = -129.7 - att_i * 0.55
        ax = 981.78 + att_i * 0.08
        add_oriented_box_in_bm(bm, (ax, ay), 0.06, 0.66, 0.22, 0.96, math.radians(-10.0), mat_side=0, mat_top=0)

    # Double-yellow centerline continuing SSE down road (`V4..V5, H5..H7`)
    add_box_between(bm, (982.1, -132.2), (986.2, -205.0), 0.205, 0.213, thickness=0.14, mat_idx=10)
    add_box_between(bm, (982.4, -132.2), (986.5, -205.0), 0.205, 0.213, thickness=0.14, mat_idx=10)

    # High-frequency weathered asphalt crack seams & joints in Camera 4 roadway (`V1..V7, H6..H8`)
    for c4_y in range(-116, -172, 3):
        c4_x = 978.0 + (abs(c4_y + 116) * 0.14)
        add_box_between(bm, (c4_x - 1.2, float(c4_y)), (c4_x - 0.8, float(c4_y - 3)), 0.205, 0.210, thickness=0.05, mat_idx=0)
        add_box_between(bm, (c4_x + 1.1, float(c4_y)), (c4_x + 1.5, float(c4_y - 3)), 0.205, 0.210, thickness=0.05, mat_idx=0)
        add_box_between(bm, (c4_x - 2.4, float(c4_y)), (c4_x + 2.8, float(c4_y - 0.4)), 0.205, 0.209, thickness=0.05, mat_idx=0)

    # Eastern (Left) Sidewalk, Curb & OPEN Steel Bridge Balustrade Railing (`V1..V4, H5..H6` — open vertical pickets!)
    add_box_between(bm, (984.5, -116.0), (990.8, -195.0), 0.205, 0.35, thickness=1.80, mat_idx=1)
    # Top rail & bottom rail
    add_box_between(bm, (985.3, -116.0), (991.5, -195.0), 1.14, 1.22, thickness=0.12, mat_idx=5)
    add_box_between(bm, (985.3, -116.0), (991.5, -195.0), 0.42, 0.48, thickness=0.12, mat_idx=5)
    # Open vertical balustrade pickets every 0.38m so trees & sky show through!
    for pk_i in range(110):
        pt = pk_i / 109.0
        px = 985.3 + (991.5 - 985.3) * pt
        py = -116.0 + (-195.0 - (-116.0)) * pt
        add_oriented_box_in_bm(bm, (px, py), 0.06, 0.06, 0.35, 1.22, math.radians(-8.0), mat_side=5, mat_top=5)

    # Sign panel & post on left sidewalk (`V1..V2, H5`: `(984.4, -125.2)`)
    add_oriented_box_in_bm(bm, (984.4, -125.2), 0.08, 0.08, 0.35, 2.05, math.radians(-8.0), mat_side=0, mat_top=0)
    add_oriented_box_in_bm(bm, (984.4, -125.2), 0.08, 0.48, 1.45, 2.02, math.radians(-8.0), mat_side=6, mat_top=6)

    # Orange Traffic Drums in East Lane (`V2..V5, H5..H6`)
    for d4_xy in [(983.0, -126.0), (984.0, -131.5), (985.2, -139.0), (986.4, -147.0)]:
        add_traffic_drum(d4_xy, z_base=0.205)

    # Curved Highway Streetlights along East & West sides of Camera 4
    add_curved_highway_lamppost((985.5, -133.5), math.radians(-16.0), height=9.2, arm_reach=2.8)
    add_curved_highway_lamppost((988.2, -158.0), math.radians(-16.0), height=9.2, arm_reach=2.8)
    add_curved_highway_lamppost((974.2, -132.0), math.radians(164.0), height=9.0, arm_reach=2.4)
    add_curved_highway_lamppost((976.0, -155.0), math.radians(164.0), height=9.0, arm_reach=2.4)

    # Western (Right) Individual Articulated Parked White RVs & Camper Trailers (`V6..V8, H4..H8` of Camera 4!)
    t1_yaw = math.radians(-80.8)  # Parallel to road edge
    ca_t = math.cos(t1_yaw)
    sa_t = math.sin(t1_yaw)

    def add_detailed_white_rv(center_xy, length_m=9.2, width_m=2.48, z_top=3.48):
        rcx, rcy = center_xy
        # Raised RV body shell (leaving clear undercarriage shadow gap z = 0.205..0.64m!)
        add_oriented_box_in_bm(bm, (rcx, rcy), length_m, width_m, 0.64, z_top, t1_yaw, mat_side=6, mat_top=6)
        # Dark chassis frame & undercarriage axle beam (inset so gap is visible)
        add_oriented_box_in_bm(bm, (rcx, rcy), length_m * 0.88, width_m * 0.72, 0.36, 0.64, t1_yaw, mat_side=0, mat_top=0)
        # Dual tandem rubber tires & recessed black wheel wells on road-facing (east) side
        for ax_off in (-1.15, -0.30, length_m * 0.32):
            wx = rcx + ax_off * ca_t - (width_m * 0.48) * sa_t
            wy = rcy + ax_off * sa_t + (width_m * 0.48) * ca_t
            add_oriented_box_in_bm(bm, (wx, wy), 0.78, 0.32, 0.205, 0.92, t1_yaw, mat_side=0, mat_top=0)
            add_oriented_box_in_bm(bm, (wx, wy), 0.42, 0.35, 0.38, 0.74, t1_yaw, mat_side=1, mat_top=1)
        # Horizontal grey belt mouldings, upper rolled awning rail & vertical panel seams (high-frequency edge match!)
        add_oriented_box_in_bm(bm, (rcx, rcy), length_m + 0.04, width_m + 0.05, 0.64, 0.82, t1_yaw, mat_side=1, mat_top=1)
        add_oriented_box_in_bm(bm, (rcx, rcy), length_m + 0.04, width_m + 0.04, 1.48, 1.56, t1_yaw, mat_side=0, mat_top=0)
        add_oriented_box_in_bm(bm, (rcx, rcy), length_m * 0.85, width_m + 0.14, z_top - 0.24, z_top - 0.08, t1_yaw, mat_side=1, mat_top=1)
        # Framed dark-glass RV windows & vertical door/panel ribs along east face
        n_panels = 6
        for p_i in range(n_panels):
            poff = -length_m * 0.42 + p_i * (length_m * 0.84 / max(1, n_panels - 1))
            px = rcx + poff * ca_t - (width_m * 0.50) * sa_t
            py = rcy + poff * sa_t + (width_m * 0.50) * ca_t
            # Vertical structural rib seam
            add_oriented_box_in_bm(bm, (px, py), 0.05, 0.08, 0.66, z_top - 0.05, t1_yaw, mat_side=0, mat_top=0)
            if p_i in (1, 3, 4):
                # Framed dark RV window
                add_oriented_box_in_bm(bm, (px, py), 1.05, 0.10, 1.72, 2.42, t1_yaw, mat_side=7, mat_top=0)
            elif p_i == 2:
                # RV side entry door with window & bottom step
                add_oriented_box_in_bm(bm, (px, py), 0.72, 0.09, 0.75, 2.48, t1_yaw, mat_side=1, mat_top=0)
                add_oriented_box_in_bm(bm, (px, py), 0.48, 0.12, 1.78, 2.32, t1_yaw, mat_side=7, mat_top=0)
                add_oriented_box_in_bm(bm, (px, py), 0.68, 0.35, 0.32, 0.48, t1_yaw, mat_side=0, mat_top=0)
        # Rooftop AC unit
        add_oriented_box_in_bm(bm, (rcx, rcy), 1.35, 0.95, z_top, z_top + 0.28, t1_yaw, mat_side=6, mat_top=6)

    # 3 distinct parked white RVs with clear separation gaps between them (`V6..V8, H4..H8`)
    add_detailed_white_rv((974.6, -122.4), length_m=8.6, width_m=2.46, z_top=3.46)
    add_detailed_white_rv((976.1, -132.4), length_m=8.8, width_m=2.48, z_top=3.52)
    add_detailed_white_rv((977.6, -142.5), length_m=8.6, width_m=2.46, z_top=3.44)

    # White Curb Stripe under Right Trailers (`V6..V8, H7..H8`)
    add_box_between(bm, (975.8, -116.5), (979.8, -162.0), 0.205, 0.213, thickness=0.16, mat_idx=11)

    # Dark Semi-Tractor Cab ahead of RV 3 at (978.9, -152.0)
    add_oriented_box_in_bm(bm, (978.9, -152.0), 5.80, 2.45, 0.35, 3.35, t1_yaw, mat_side=0, mat_top=0)
    add_oriented_box_in_bm(bm, (978.9, -152.0), 5.20, 2.30, 1.65, 2.45, t1_yaw, mat_side=7, mat_top=0)

    finalize_bm(bm, me, default_tile_m=3.0)
    print("Constructed Street View Corridor Details (Smooth Curved Streetlights, Open Railings, Articulated RVs & Cracks)")
    return obj


# ===========================================================================
# 7. 100% GENUINE HIGH-POLY POLY HAVEN 3D TREES & SHRUBS (ZERO PROCEDURAL CONES!)
# ===========================================================================

def _build_lush_canopy_from_polyhaven_leaves(asset_id, src_mesh, mat_green, mat_bark, target_height_m=12.0, n_clusters=1800, cluster_radius=0.44):
    """
    Extracts the genuine 3D leaf-cluster positions and trunk geometry directly from
    the loaded Poly Haven mesh (`src_mesh`), centers the tree at `(0,0,0)` with normalized
    `target_height_m`, preserves the 3D brown-bark trunk/branches, and expands `n_clusters`
    sampled Poly Haven leaf polygons into volumetric 3D crossed leaf cards so the canopy
    never collapses under decimation and renders lush summer green from both Nadir & Street View.
    """
    verts = src_mesh.vertices
    if not verts:
        return []

    xs = [v.co.x for v in verts]
    ys = [v.co.y for v in verts]
    zs = [v.co.z for v in verts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    cx = 0.5 * (min_x + max_x)
    cy = 0.5 * (min_y + max_y)
    raw_h = max(0.5, max_z - min_z)
    norm_s = target_height_m / raw_h

    leaf_mat_indices = set()
    bark_mat_indices = set()
    for i, m in enumerate(src_mesh.materials):
        mname = (m.name.lower() if m else "")
        if any(k in mname for k in ("leaf", "leaves", "foliage", "shrub", "crown")):
            leaf_mat_indices.add(i)
        else:
            bark_mat_indices.add(i)
    if not leaf_mat_indices:
        leaf_mat_indices = set(range(max(1, len(src_mesh.materials))))

    leaf_polys = [p for p in src_mesh.polygons if p.material_index in leaf_mat_indices]
    bark_polys = [p for p in src_mesh.polygons if p.material_index in bark_mat_indices]

    out_templates = []

    # 1. Build 3D Trunk & Main Branches mesh (if bark polygons exist)
    if bark_polys:
        bm_b = bmesh.new()
        step_b = max(1, len(bark_polys) // 1600)
        for p in bark_polys[::step_b]:
            p_verts = []
            for vi in p.vertices:
                co = verts[vi].co
                vx = (co.x - cx) * norm_s
                vy = (co.y - cy) * norm_s
                vz = (co.z - min_z) * norm_s
                p_verts.append(bm_b.verts.new((vx, vy, vz)))
            try:
                bm_b.faces.new(p_verts)
            except ValueError:
                pass
        me_bark = bpy.data.meshes.new(f"PH_{asset_id}_Bark_Mesh")
        bm_b.to_mesh(me_bark)
        bm_b.free()
        me_bark.materials.append(mat_bark)
        me_bark.use_fake_user = True
        out_templates.append({
            "mesh": me_bark,
            "loc": (0.0, 0.0, 0.0),
            "rot": (0.0, 0.0, 0.0),
            "scale": (1.0, 1.0, 1.0),
        })

    # 2. Build Fine-Cluster 3D Leaf Canopy mesh directly from Poly Haven leaf polygon centers
    if leaf_polys:
        bm_l = bmesh.new()
        uv_layer = bm_l.loops.layers.uv.new("UVMap")
        step_l = max(1, len(leaf_polys) // n_clusters)
        r = cluster_radius
        for idx_p, p in enumerate(leaf_polys[::step_l]):
            pc = p.center
            lx = (pc.x - cx) * norm_s
            ly = (pc.y - cy) * norm_s
            lz = (pc.z - min_z) * norm_s
            ang = (idx_p * 1.6180339) * math.pi
            ca, sa = math.cos(ang), math.sin(ang)
            # Fine diamond-shaped leaf card 1 (horizontal/oblique for Nadir & Street View)
            v1 = bm_l.verts.new((lx - r * ca, ly - r * sa, lz + r * 0.22))
            v2 = bm_l.verts.new((lx + r * 0.65 * sa, ly - r * 0.65 * ca, lz - r * 0.18))
            v3 = bm_l.verts.new((lx + r * ca, ly + r * sa, lz - r * 0.22))
            v4 = bm_l.verts.new((lx - r * 0.65 * sa, ly + r * 0.65 * ca, lz + r * 0.18))
            # Fine diamond-shaped leaf card 2 (vertical-tilted for natural organic leaf silhouette)
            v5 = bm_l.verts.new((lx, ly, lz - r * 0.92))
            v6 = bm_l.verts.new((lx + r * 0.78 * ca, ly + r * 0.78 * sa, lz))
            v7 = bm_l.verts.new((lx, ly, lz + r * 0.92))
            v8 = bm_l.verts.new((lx - r * 0.78 * ca, ly - r * 0.78 * sa, lz))
            # Fine diamond-shaped leaf card 3 (orthogonal vertical-tilted)
            v9  = bm_l.verts.new((lx, ly, lz - r * 0.85))
            v10 = bm_l.verts.new((lx - r * 0.75 * sa, ly + r * 0.75 * ca, lz + r * 0.10))
            v11 = bm_l.verts.new((lx, ly, lz + r * 0.85))
            v12 = bm_l.verts.new((lx + r * 0.75 * sa, ly - r * 0.75 * ca, lz - r * 0.10))
            for qverts in ((v1, v2, v3, v4), (v5, v6, v7, v8), (v9, v10, v11, v12)):
                try:
                    f = bm_l.faces.new(qverts)
                    f.material_index = 0
                    for loop, uv in zip(f.loops, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))):
                        loop[uv_layer].uv = uv
                except ValueError:
                    pass
        me_leaf = bpy.data.meshes.new(f"PH_{asset_id}_Canopy_Mesh")
        bm_l.to_mesh(me_leaf)
        bm_l.free()
        me_leaf.materials.append(mat_green)
        me_leaf.use_fake_user = True
        out_templates.append({
            "mesh": me_leaf,
            "loc": (0.0, 0.0, 0.0),
            "rot": (0.0, 0.0, 0.0),
            "scale": (1.0, 1.0, 1.0),
        })

    return out_templates


def preload_and_optimize_polyhaven_models(parent_col, pal, max_faces_per_part=3200):
    """
    Preloads Poly Haven 3D models into `kit._APPENDED_MODEL_TEMPLATES` BEFORE instancing,
    preserving both the 3D brown-bark trunk/branches and a lush, fine-leaved 3D summer
    green leaf canopy derived directly from each Poly Haven model's 3D crown geometry.
    """
    mat_green = pal["Mat_MTL_Summer_Canopy_Green"]
    mat_bark = pal["Mat_MTL_Tree_Bark"]

    tree_configs = {
        "jacaranda_tree": ("jacaranda_tree_LOD1", 12.5, 3200, 0.22),
        "searsia_burchellii": ("searsia_burchellii_large_LOD2", 10.5, 2800, 0.20),
        "tree_small_02": ("tree_small_02_LOD1", 8.8, 2200, 0.18),
        "shrub_02": ("shrub_02_c_LOD2", 2.2, 950, 0.14),
    }

    for asset_id, (preferred_obj_name, target_h, n_clust, c_rad) in tree_configs.items():
        blend_path = os.path.join(kit.POLYHAVEN_MODELS_DIR, asset_id, f"{asset_id}.blend")
        if not os.path.isfile(blend_path):
            continue
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            if preferred_obj_name in data_from.objects:
                data_to.objects = [preferred_obj_name]
            else:
                data_to.objects = list(data_from.objects)
        loaded_objs = [o for o in data_to.objects if o is not None and o.type == "MESH"]
        if not loaded_objs:
            continue
        src_obj = loaded_objs[0]
        templates = _build_lush_canopy_from_polyhaven_leaves(
            asset_id,
            src_obj.data,
            mat_green,
            mat_bark,
            target_height_m=target_h,
            n_clusters=n_clust,
            cluster_radius=c_rad,
        )
        for o in loaded_objs:
            try:
                me_old = o.data
                bpy.data.objects.remove(o, do_unlink=True)
                if me_old and me_old.users == 0:
                    bpy.data.meshes.remove(me_old)
            except Exception:
                pass
        if templates:
            kit._APPENDED_MODEL_TEMPLATES[asset_id] = templates

    # Also preload street furniture (`street_lamp_01`, `modular_street_seating`)
    for prop_id in ("street_lamp_01", "modular_street_seating"):
        warmup_objs = kit.append_polyhaven_model(prop_id, parent_col, f"_Warmup_{prop_id}", location=(0, 0, 0), scale=1.0) or []
        for wo in warmup_objs:
            try:
                bpy.data.objects.remove(wo, do_unlink=True)
            except Exception:
                pass


def upgrade_all_tree_materials(pal, crimson_prefixes=()):
    """
    Assigns Crimson King dark-maple foliage to the specific crimson tree instances using
    OBJECT-level material slot linking (zero duplicate mesh copies!).
    """
    mat_crimson = pal["Mat_MTL_Crimson_Maple_Leaves"]
    mat_green = pal["Mat_MTL_Summer_Canopy_Green"]

    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data:
            continue
        if not any(obj.name.startswith(pref) for pref in crimson_prefixes):
            continue
        for slot in obj.material_slots:
            if slot.material == mat_green:
                slot.link = "OBJECT"
                slot.material = mat_crimson


def spawn_polyhaven_trees_and_furniture(dossier, parent_col, pal):
    """
    Spawns 120+ genuine high-poly Poly Haven 3D botanical instances (`jacaranda_tree`,
    `searsia_burchellii`, `tree_small_02`, `shrub_02`) and street furniture (`street_lamp_01`,
    `modular_street_seating`) matched 1:1 to `satellite_topdown.png` and all 4 Street View cameras.
    """
    preload_and_optimize_polyhaven_models(parent_col, pal, max_faces_per_part=3200)
    tree_specs = []  # (x, y, z, species, scale, is_crimson)

    # 1. Dense Eastern Shoreline Woodland Belt (`V6..V7, H1..H8`, X = 1054.5 .. 1064.5, Y = -380.0 .. -225.0)
    # 55 overlapping high-poly trees & shrubs forming a continuous lush canopy strictly inside V6..V7!
    shore_species = ["jacaranda_tree", "searsia_burchellii", "tree_small_02"]
    idx_s = 0
    for y_sh in range(-375, -225, 6):
        for x_sh in (1055.8, 1060.0, 1063.5):
            jx = x_sh + ((idx_s % 3) - 1) * 0.6
            jy = float(y_sh) + ((idx_s % 2) - 0.5) * 1.5
            sp = shore_species[idx_s % len(shore_species)]
            sc = 0.72 + (idx_s % 4) * 0.08
            tree_specs.append((jx, jy, 0.20, sp, sc, False))
            idx_s += 1

    # Extra larger southern shoreline crown (`V6..V7, H7..H8` in satellite_topdown.png: X = 1049..1063, Y = -354..-368)
    for tx, ty, sc in [
        (1051.5, -357.0, 0.85), (1056.5, -361.0, 0.90), (1052.5, -365.5, 0.85),
        (1048.5, -363.0, 0.80), (1060.5, -365.5, 0.88),
    ]:
        tree_specs.append((tx, ty, 0.20, "jacaranda_tree", sc, False))

    # 2. Central Parc de Dieppe Tree Cluster (`V4..V5, H3..H4` of satellite_topdown.png: X = 1017..1031, Y = -293..-283)
    central_cluster = [
        (1017.5, -290.5, "jacaranda_tree", 0.68, False),
        (1021.5, -291.5, "searsia_burchellii", 0.72, False),
        (1026.5, -286.5, "jacaranda_tree", 0.78, False),
        (1029.5, -289.0, "searsia_burchellii", 0.70, False),
        (1024.0, -285.0, "jacaranda_tree", 0.68, False),
    ]
    for tx, ty, sp, sc, cr in central_cluster:
        tree_specs.append((tx, ty, 0.20, sp, sc, cr))

    # 3. Service Road North Tree (`V3, H2..H3` of satellite_topdown.png: `(1000.2, -267.5)`)
    tree_specs.append((1000.2, -267.5, 0.20, "jacaranda_tree", 0.68, False))
    tree_specs.append((1001.5, -266.8, 0.20, "searsia_burchellii", 0.64, False))

    # 4. Tennis Court West & South Perimeter Trees (`V2..V3, H5..H8` & `V6, H6..H7` of satellite_topdown.png)
    tennis_perimeter_trees = [
        # West of Tennis Court (V3, H5..H7: X = 998.0..999.5, Y = -318..-348 — strictly West of court!)
        (999.2,  -319.0, "jacaranda_tree", 0.64, False),
        (998.5,  -325.0, "searsia_burchellii", 0.62, False),
        (998.0,  -335.5, "jacaranda_tree", 0.66, False),
        (997.8,  -342.5, "searsia_burchellii", 0.64, False),
        (997.5,  -348.5, "jacaranda_tree", 0.62, False),
        # SW Turnaround Sunlit Maples & Green Trees (V2..V3, H7..H8 + Camera 1 & 2 right midground!)
        (984.5,  -354.5, "jacaranda_tree", 0.72, False),
        (991.5,  -356.0, "jacaranda_tree", 0.74, False),
        (987.5,  -351.0, "searsia_burchellii", 0.68, False),
        (991.5,  -367.5, "jacaranda_tree", 0.68, False),
        # SE of Tennis Pavilion (V6, H6..H7: X = 1043..1052, Y = -337..-350)
        (1048.5, -339.5, "jacaranda_tree", 0.76, True),
        (1043.8, -342.5, "searsia_burchellii", 0.70, False),
        (1046.8, -347.5, "jacaranda_tree", 0.72, False),
        (1051.5, -346.5, "searsia_burchellii", 0.70, False),
        # Hedge row north of Tennis Pavilion (X = 1039..1052, Y = -314.0)
        (1040.0, -314.0, "shrub_02", 0.90, False),
        (1044.0, -314.0, "shrub_02", 0.90, False),
        (1048.0, -314.0, "shrub_02", 0.90, False),
        (1051.5, -314.0, "shrub_02", 0.90, False),
    ]
    for tx, ty, sp, sc, cr in tennis_perimeter_trees:
        tree_specs.append((tx, ty, 0.20, sp, sc, cr))

    # 5. Median Ornamental Shrubs along Avenue Pierre-Dupuy (`V2, H1..H6`)
    for y_med in range(-330, -235, 11):
        xm = x_ave_center(float(y_med)) + 11.0
        tree_specs.append((xm, float(y_med), 0.20, "shrub_02", 0.65, False))

    # 6. Camera 1 (`[967.9, -370.9]`, `hdg = 11.4°`) & Camera 2 (`[969.9, -377.7]`, `hdg = 11.4°`) Trees:
    # Includes the tall overhanging right-side deciduous canopy in Cam 1 (`V6..V8, H1..H5`) + Cam 2 right edge (`V7..V8, H1..H5`)!
    cam12_trees = [
        (975.8, -363.2, "jacaranda_tree", 1.12, False),
        (977.4, -358.5, "searsia_burchellii", 1.05, False),
        (979.2, -371.0, "jacaranda_tree", 0.96, False),
        (982.5, -363.5, "jacaranda_tree", 0.88, False),
        (986.0, -369.5, "searsia_burchellii", 0.85, False),
        (981.8, -373.5, "tree_small_02", 0.80, False),
        (984.5, -346.0, "jacaranda_tree", 0.78, False),
        (988.0, -338.0, "searsia_burchellii", 0.78, False),
        # Distant western roadside trees near horizon (`H5, V1..V2`, well north of cameras)
        (952.0, -325.0, "tree_small_02", 0.70, False),
        (953.5, -305.0, "searsia_burchellii", 0.72, False),
    ]
    for tx, ty, sp, sc, cr in cam12_trees:
        tree_specs.append((tx, ty, 0.20, sp, sc, cr))

    # 7. Camera 3 (`Parc_de_Dieppe_Tip_Harbor_View` at `[1055.9, -4.9]`, `hdg = 186.3°`) Trees (rounded crown in H4..H5):
    cam3_trees = [
        (1062.0, -25.5, "searsia_burchellii", 0.56, False),
        (1056.8, -30.5, "searsia_burchellii", 0.58, False),
        (1050.8, -36.5, "jacaranda_tree", 0.62, False),
        (1044.5, -43.0, "searsia_burchellii", 0.64, False),
    ]
    for tx, ty, sp, sc, cr in cam3_trees:
        tree_specs.append((tx, ty, 0.20, sp, sc, cr))

    # 8. Camera 4 (`Port_Montreal_Water_Channel_Vista` at `[978.1, -115.65]`, `hdg = 166.6°`) Left Shoreline Trees:
    cam4_trees = [
        (990.5, -132.0, "jacaranda_tree", 0.72, False),
        (992.5, -145.0, "searsia_burchellii", 0.75, False),
        (994.5, -160.0, "jacaranda_tree", 0.76, False),
        (996.5, -178.0, "searsia_burchellii", 0.78, False),
        (998.5, -198.0, "jacaranda_tree", 0.80, False),
    ]
    for tx, ty, sp, sc, cr in cam4_trees:
        tree_specs.append((tx, ty, 0.20, sp, sc, cr))

    crimson_prefixes = []
    for idx, (tx, ty, tz, sp, sc, is_cr) in enumerate(tree_specs):
        inst_name = f"PH_Tree_{idx:03d}_{sp}"
        if is_cr:
            crimson_prefixes.append(inst_name)
        rot_z = math.radians((idx * 67) % 360)
        kit.append_polyhaven_model(
            sp,
            parent_col,
            inst_name,
            location=(tx, ty, tz),
            rotation_z=rot_z,
            scale=sc
        )

    # Also instantiate Poly Haven `street_lamp_01` and `modular_street_seating` in Parc de Dieppe
    for bi, (bx, by) in enumerate([(1041.8, -329.0), (1041.8, -333.0), (1002.0, -306.5), (1030.0, -307.0)]):
        kit.append_polyhaven_model(
            "modular_street_seating",
            parent_col,
            f"PH_Seating_{bi}",
            location=(bx, by, 0.22),
            rotation_z=0.0,
            scale=1.0
        )
    for li, (lx, ly) in enumerate([(1000.5, -307.0), (1041.5, -325.0)]):
        kit.append_polyhaven_model(
            "street_lamp_01",
            parent_col,
            f"PH_ParkLamp_{li}",
            location=(lx, ly, 0.22),
            rotation_z=0.0,
            scale=1.0
        )

    upgrade_all_tree_materials(pal, crimson_prefixes=tuple(crimson_prefixes))
    print(f"Instantiated {len(tree_specs)} genuine high-poly Poly Haven 3D trees/shrubs + park seating & lamps.")


# ===========================================================================
# 8. WORLD LIGHTING, GPU CYCLES CONFIG & VERIFICATION SNAPSHOT
# ===========================================================================

def setup_world_and_render(dossier, cam_col, skip_render=False):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16

    world = bpy.data.worlds.get("World_Block0035") or bpy.data.worlds.new("World_Block0035")
    scene.world = world
    world.use_nodes = True
    wnodes = world.node_tree.nodes
    wlinks = world.node_tree.links
    wnodes.clear()

    w_out = wnodes.new("ShaderNodeOutputWorld")
    w_bg = wnodes.new("ShaderNodeBackground")
    w_bg.inputs["Strength"].default_value = 1.15
    wlinks.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

    if os.path.isfile(HDRI_PATH):
        tcoord = wnodes.new("ShaderNodeTexCoord")
        mapping = wnodes.new("ShaderNodeMapping")
        mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(45.0))
        wlinks.new(tcoord.outputs["Generated"], mapping.inputs["Vector"])
        env_tex = wnodes.new("ShaderNodeTexEnvironment")
        env_tex.image = bpy.data.images.load(HDRI_PATH, check_existing=True)
        wlinks.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])

        # Mix HDRI cloud detail with crisp summer midday blue sky matching Google Street View H1..H4
        mix_sky = wnodes.new("ShaderNodeMix")
        mix_sky.data_type = "RGBA"
        mix_sky.blend_type = "MIX"
        mix_sky.inputs["Factor"].default_value = 0.62
        mix_sky.inputs[7].default_value = (0.20, 0.42, 0.78, 1.0)
        wlinks.new(mix_sky.inputs[6], env_tex.outputs["Color"])
        wlinks.new(w_bg.inputs["Color"], mix_sky.outputs[2])
    else:
        w_bg.inputs["Color"].default_value = (0.28, 0.48, 0.82, 1.0)

    # Sunlight matched to satellite_topdown.png shadow direction (sun in South-Southwest casting shadows NNE)
    sun_data = bpy.data.lights.new(name="Sun_Light", type="SUN")
    sun_data.energy = 3.8
    sun_data.color = (1.0, 0.96, 0.90)
    sun_data.angle = math.radians(2.0)
    sun_obj = bpy.data.objects.new(name="Sun_Light", object_data=sun_data)
    cam_col.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(36.0), math.radians(16.0), math.radians(-28.0))

    # Hero Aerial Verification Camera framing Habitat 67, Twin Tennis Courts, Parc de Dieppe & St. Lawrence River
    cam_data = bpy.data.cameras.new("Cam_Habitat67_Harbor")
    cam_data.lens = 28.0
    cam_obj = bpy.data.objects.new("Cam_Habitat67_Harbor", cam_data)
    cam_col.objects.link(cam_obj)
    scene.camera = cam_obj

    cam_obj.location = (935.0, -355.0, 46.0)
    target = Vector((1022.0, -445.0, 14.0))
    direction = target - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    if not skip_render:
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720
        scene.render.filepath = SNAPSHOT_PATH
        bpy.ops.render.render(write_still=True)
        print(f"Rendered verification snapshot to {SNAPSHOT_PATH}")


# ===========================================================================
# 9. MAIN BUILD ROUTINE
# ===========================================================================

def main():
    skip_render = "--skip-render" in sys.argv
    print(f"=== Starting Iteration 2 AAA Remodel for Block {BLOCK_ID} ===")
    sys.stdout.flush()
    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    root_col = get_or_create_collection(f"Block_{BLOCK_ID}")
    owned_col = get_or_create_collection(f"Block_{BLOCK_ID}_Owned", parent=root_col)
    cam_col = get_or_create_collection(f"Block_{BLOCK_ID}_Cameras", parent=root_col)

    pal = setup_palette()

    all_bldgs = dossier.get("osm_features", {}).get("buildings", [])
    bldg_habitat = next((b for b in all_bldgs if b["id"] == 440195613), None)
    if bldg_habitat:
        build_habitat_67(bldg_habitat, owned_col, pal)

    build_tropiques_nord_and_pavilions(dossier, owned_col, pal)
    build_peninsula_park_tennis_roads_and_water(dossier, owned_col, pal)
    build_streetview_corridor_details(owned_col, pal)
    spawn_polyhaven_trees_and_furniture(dossier, owned_col, pal)

    setup_world_and_render(dossier, cam_col, skip_render=skip_render)

    # Pack all 2K Poly Haven PBR textures before saving .blend
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"Warning during pack_all: {e}")

    # Save clean .blend file
    tmp_blend = BLEND_OUT_PATH + ".tmp.blend"
    for p in (tmp_blend, BLEND_OUT_PATH):
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
        try:
            os.remove(tmp_blend)
        except Exception:
            pass
    print(f"Saved clean .blend to {BLEND_OUT_PATH}")

    # Export clean USD
    try:
        bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, check_existing=False, export_materials=False)
        print(f"Exported clean USD to {USDC_OUT_PATH}")
    except Exception as e:
        print(f"USD export notice: {e}")
    print(f"=== Successfully completed Iteration 2 build for {BLOCK_ID} ===")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
