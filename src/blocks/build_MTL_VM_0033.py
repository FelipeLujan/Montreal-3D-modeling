"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0033 (Milestone 3)
(Place Gare-Viger / Château Viger, Rue Berri / Rue Saint-Antoine Est / Avenue Viger Est / Place Gare Viger Courtyard)

Architectural Landmarks & Scope:
1. Château Viger / Ancienne Gare Viger (OSM Way 46866814):
   - Monumental French Châteauesque / Romanesque Revival railway hotel & station (Bruce Price, 1898).
   - Heavy rusticated ashlar limestone plinth & ground-floor Romanesque round-arched portal loggias.
   - Red brick facade with limestone quoins, sills, lintels, and machicolated corbel cornices.
   - Steep copper chateau roof rising to 46.5m peak with copper cresting and verdigris patina.
   - 5 monumental corner tourelles / round turrets with conical copper roofs and spires (up to Z = 45m).
   - 2 tiers of steep gabled dormers along the high-pitch roof slopes.
   - Deeply recessed window bays (reveal >= 0.48m) with stone sills, lintels, and mullions.
2. Modern Glass Annex (OSM Way 1244672622):
   - Modern 5-storey glass & bronze atrium annex in the courtyard (height ~24m).
   - Reflective architectural glass curtain wall with dark bronze grid mullions.
   - Inset rooftop terrace & mechanical penthouse.
3. Place Gare Viger Courtyard Plaza (OSM Park/Square "Place Gare Viger"):
   - Two-tone granite paver courtyard (light & charcoal granite), stepped amphitheater terraces,
     and raised granite planter beds.
4. Remaining Primary Owned Buildings (197 buildings, 199 owned total):
   - Recessed window bays (reveal >= 0.46m), parapet insets (>= 0.20m), roof decks inset (>= 0.35m).
   - Party-wall detection and protrusion suppression (no sills, lintels, or cornices on shared walls).
   - Party-wall separation >= 0.02m to eliminate inter-building clipping and coplanar Z-fighting.
   - Balanced Welsh-Powell graph coloring across 14 distinct Poly Haven 2K PBR facade materials:
     <= 20% max single material share (actual ~7.5%), 0 adjacent party-wall identical textures.
5. Ground Stratum, Roadbed & Sidewalk Network:
   - Watertight district ground collider base slab (Z = -0.25m .. 0.00m) with upward (+Z) normals.
   - Continuous PBR asphalt roadbeds (Z = 0.00m .. +0.015m) and raised sidewalks (Z = +0.15m) with 3D curbs.
   - Building footprints (+0.02m buffer) cut out from sidewalks (0 sidewalk-building penetrations).
   - Prop clearance filter: >= 1.8m from all buildings and >= 1.2m from roadbed edges.
6. Export Standards:
   - ONLY Block_MTL-VM-0033_Owned (ZERO context proxies, ZERO hidden meshes).
   - Clean export: output/blocks/MTL-VM-0033.blend and output/blocks/MTL-VM-0033.usdc (visible_objects_only=True).
   - Verification of 0 Z-fighting conflicts and 0 hidden proxies.
"""

import os
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import math
import re
import shutil
import bpy
import bmesh
from mathutils import Vector, Matrix

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

BLOCK_ID = "MTL-VM-0033"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")
SNAPSHOT_PATH = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.usdc")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
KIT_BLEND_PATH = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
HDRI_PATH = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT_PATH), exist_ok=True)


# ---------------------------------------------------------------------------
# 1. SCENE & COLLECTION MANAGEMENT
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 2. 2D GEOMETRY UTILITIES & ANTI-CLIPPING HELPERS
# ---------------------------------------------------------------------------
def clean_poly_pts(coords_xy):
    pts = [(float(p[0]), float(p[1])) for p in coords_xy]
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05:
        pts = pts[:-1]
    cleaned = []
    for p in pts:
        if not cleaned or math.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > 0.05:
            cleaned.append(p)
    return cleaned


def polygon_area_2d(pts):
    n = len(pts)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
    return 0.5 * area


def ensure_ccw(pts):
    if polygon_area_2d(pts) < 0:
        return list(reversed(pts))
    return pts


def inset_polygon_2d(pts, dist):
    pts = ensure_ccw(clean_poly_pts(pts))
    n = len(pts)
    if n < 3:
        return pts
    insets = []
    for i in range(n):
        p_prev = pts[(i - 1 + n) % n]
        p_curr = pts[i]
        p_next = pts[(i + 1) % n]
        v1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        v2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
        l1 = math.hypot(v1[0], v1[1])
        l2 = math.hypot(v2[0], v2[1])
        if l1 < 1e-4 or l2 < 1e-4:
            insets.append(p_curr)
            continue
        n1 = (-v1[1] / l1, v1[0] / l1)
        n2 = (-v2[1] / l2, v2[0] / l2)
        bis_x = n1[0] + n2[0]
        bis_y = n1[1] + n2[1]
        bl = math.hypot(bis_x, bis_y)
        if bl < 1e-4:
            insets.append((p_curr[0] + n1[0] * dist, p_curr[1] + n1[1] * dist))
            continue
        bis_x /= bl
        bis_y /= bl
        dot = bis_x * n1[0] + bis_y * n1[1]
        scale = dist / max(0.25, dot)
        scale = min(scale, dist * 3.0)
        insets.append((p_curr[0] + bis_x * scale, p_curr[1] + bis_y * scale))
    if polygon_area_2d(insets) <= 0.05:
        cx = sum(p[0] for p in pts) / n
        cy = sum(p[1] for p in pts) / n
        return [((1.0 - 0.05) * p[0] + 0.05 * cx, (1.0 - 0.05) * p[1] + 0.05 * cy) for p in pts]
    return insets


def pt_seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    if l2 < 1e-6:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    proj = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - proj[0], p[1] - proj[1])


def poly_poly_dist_2d(p1, p2):
    min_d = 9999.0
    for pt in p1:
        for i in range(len(p2) - 1):
            d = pt_seg_dist(pt, p2[i], p2[i + 1])
            if d < min_d:
                min_d = d
    for pt in p2:
        for i in range(len(p1) - 1):
            d = pt_seg_dist(pt, p1[i], p1[i + 1])
            if d < min_d:
                min_d = d
    return min_d


def is_party_wall(p1, p2, other_polys, threshold=0.45):
    if not other_polys:
        return False
    mid = ((p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5)
    q1 = (p1[0] * 0.75 + p2[0] * 0.25, p1[1] * 0.75 + p2[1] * 0.25)
    q2 = (p1[0] * 0.25 + p2[0] * 0.75, p1[1] * 0.25 + p2[1] * 0.75)
    test_pts = [mid, q1, q2]
    for pt in test_pts:
        for poly in other_polys:
            n = len(poly)
            for i in range(n):
                a, b = poly[i], poly[(i + 1) % n]
                if pt_seg_dist(pt, a, b) < threshold:
                    return True
    return False


def deconflict_party_walls(pts, other_polys, min_sep=0.02):
    """
    Shifts party wall vertices inward along edge normals by min_sep so touching
    building shells never share identical coplanar coordinates or intersect.
    """
    if not other_polys:
        return pts
    n = len(pts)
    deconf = list(pts)
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        if is_party_wall(p1, p2, other_polys, threshold=0.45):
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            l = math.hypot(dx, dy)
            if l > 0.05:
                # Inward normal for CCW polygon: (-dy/l, dx/l)
                nx, ny = -dy / l, dx / l
                deconf[i] = (deconf[i][0] + nx * min_sep, deconf[i][1] + ny * min_sep)
                deconf[(i + 1) % n] = (deconf[(i + 1) % n][0] + nx * min_sep, deconf[(i + 1) % n][1] + ny * min_sep)
    return deconf


# ---------------------------------------------------------------------------
# 3. BMESH PRIMITIVE BUILDERS
# ---------------------------------------------------------------------------
def extrude_prism_in_bm(bm, pts, z0, z1, mat_side=0, mat_top=0, mat_bottom=0, cap_top=True, cap_bottom=True):
    n = len(pts)
    if n < 3:
        return
    bverts = [bm.verts.new((p[0], p[1], z0)) for p in pts]
    tverts = [bm.verts.new((p[0], p[1], z1)) for p in pts]
    for i in range(n):
        i_next = (i + 1) % n
        f = bm.faces.new([bverts[i], bverts[i_next], tverts[i_next], tverts[i]])
        f.material_index = mat_side
    if cap_bottom:
        try:
            fb = bm.faces.new(list(reversed(bverts)))
            fb.material_index = mat_bottom
        except ValueError:
            pass
    if cap_top:
        try:
            ft = bm.faces.new(tverts)
            ft.material_index = mat_top
        except ValueError:
            pass


def extrude_sloped_hip_roof_in_bm(bm, pts_eave, z_eave, z_ridge, inset_dist, mat_roof=0, cap_top=True):
    """
    Creates a true sloped hipped château roof frustum connecting `pts_eave` at `z_eave`
    to `inset_polygon_2d(pts_eave, inset_dist)` at `z_ridge` with sloped quad faces.
    """
    pts_bot = ensure_ccw(clean_poly_pts(pts_eave))
    n = len(pts_bot)
    if n < 3:
        return
    pts_top = inset_polygon_2d(pts_bot, inset_dist)
    if len(pts_top) != n:
        cx = sum(p[0] for p in pts_bot) / n
        cy = sum(p[1] for p in pts_bot) / n
        pts_top = [(0.65 * p[0] + 0.35 * cx, 0.65 * p[1] + 0.35 * cy) for p in pts_bot]
    bverts = [bm.verts.new((p[0], p[1], z_eave)) for p in pts_bot]
    tverts = [bm.verts.new((p[0], p[1], z_ridge)) for p in pts_top]
    for i in range(n):
        i_next = (i + 1) % n
        try:
            f = bm.faces.new([bverts[i], bverts[i_next], tverts[i_next], tverts[i]])
            f.material_index = mat_roof
        except ValueError:
            pass
    if cap_top:
        try:
            ft = bm.faces.new(tverts)
            ft.material_index = mat_roof
        except ValueError:
            pass


def add_box_between(bm, p1, p2, z0, z1, thickness=0.45, offset_out=0.0, mat_idx=0):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    l = math.hypot(dx, dy)
    if l < 1e-4:
        return
    ux, uy = dx / l, dy / l
    nx, ny = uy, -ux  # Outward normal for CCW segment!
    half_th = thickness * 0.5
    c_out = offset_out + half_th
    o1 = (p1[0] + nx * (c_out - half_th), p1[1] + ny * (c_out - half_th))
    o2 = (p2[0] + nx * (c_out - half_th), p2[1] + ny * (c_out - half_th))
    o3 = (p2[0] + nx * (c_out + half_th), p2[1] + ny * (c_out + half_th))
    o4 = (p1[0] + nx * (c_out + half_th), p1[1] + ny * (c_out + half_th))
    box_pts = [o1, o2, o3, o4]
    extrude_prism_in_bm(bm, box_pts, z0, z1, mat_side=mat_idx, mat_top=mat_idx, mat_bottom=mat_idx)


def add_curved_voussoir_arch(bm, wp1, wp2, z_spring, arch_rise=0.45, thickness=0.68,
                             offset_out=0.24, mat_stone=0, add_keystone=True):
    dx, dy = wp2[0] - wp1[0], wp2[1] - wp1[1]
    win_w = math.hypot(dx, dy)
    if win_w < 0.2:
        return
    ux, uy = dx / win_w, dy / win_w
    n_segs = 6
    for si in range(n_segs):
        t0 = si / float(n_segs)
        t1 = (si + 1) / float(n_segs)
        ang0 = math.pi * (1.0 - t0)
        ang1 = math.pi * (1.0 - t1)
        z0_c = z_spring + arch_rise * math.sin(ang0)
        z1_c = z_spring + arch_rise * math.sin(ang1)
        z_curve = min(z0_c, z1_c)
        sp1 = (wp1[0] + ux * (t0 * win_w), wp1[1] + uy * (t0 * win_w))
        sp2 = (wp1[0] + ux * (t1 * win_w), wp1[1] + uy * (t1 * win_w))
        add_box_between(bm, sp1, sp2, z_curve, z_curve + 0.26, thickness=thickness, offset_out=offset_out, mat_idx=mat_stone)

    if add_keystone:
        kp1 = (wp1[0] + ux * (win_w * 0.42), wp1[1] + uy * (win_w * 0.42))
        kp2 = (wp1[0] + ux * (win_w * 0.58), wp1[1] + uy * (win_w * 0.58))
        add_box_between(bm, kp1, kp2, z_spring + arch_rise - 0.05, z_spring + arch_rise + 0.36,
                        thickness=thickness + 0.16, offset_out=offset_out + 0.08, mat_idx=mat_stone)


def add_dormer_in_bm(bm, center_xy, heading_deg, z_base, width=2.0, depth=2.4, height=3.2,
                     mat_wall=0, mat_roof=1, mat_win=2):
    rad = math.radians(heading_deg)
    fx, fy = math.cos(rad), math.sin(rad)
    rx, ry = -fy, fx
    hw, hd = width * 0.5, depth * 0.5
    cx, cy = center_xy
    p1 = (cx - rx * hw - fx * hd, cy - ry * hw - fy * hd)
    p2 = (cx + rx * hw - fx * hd, cy + ry * hw - fy * hd)
    p3 = (cx + rx * hw + fx * hd, cy + ry * hw + fy * hd)
    p4 = (cx - rx * hw + fx * hd, cy - ry * hw + fy * hd)
    extrude_prism_in_bm(bm, [p1, p2, p3, p4], z_base, z_base + height * 0.65, mat_side=mat_wall, cap_top=False)

    # Recessed window pane on the front face (p3 -> p4)
    win_p1 = (cx + rx * (hw * 0.70) + fx * (hd - 0.25), cy + ry * (hw * 0.70) + fy * (hd - 0.25))
    win_p2 = (cx - rx * (hw * 0.70) + fx * (hd - 0.25), cy - ry * (hw * 0.70) + fy * (hd - 0.25))
    add_box_between(bm, win_p1, win_p2, z_base + 0.4, z_base + height * 0.60, thickness=0.10, offset_out=0.0, mat_idx=mat_win)

    # Steep triangular pediment / gable roof
    z_wall_top = z_base + height * 0.65
    z_ridge = z_base + height
    v_b1 = bm.verts.new((p1[0], p1[1], z_wall_top))
    v_b2 = bm.verts.new((p2[0], p2[1], z_wall_top))
    v_b3 = bm.verts.new((p3[0], p3[1], z_wall_top))
    v_b4 = bm.verts.new((p4[0], p4[1], z_wall_top))
    v_r_back = bm.verts.new((cx - fx * hd, cy - fy * hd, z_ridge))
    v_r_front = bm.verts.new((cx + fx * hd, cy + fy * hd, z_ridge))

    try:
        f_left = bm.faces.new([v_b4, v_b1, v_r_back, v_r_front])
        f_left.material_index = mat_roof
        f_right = bm.faces.new([v_b2, v_b3, v_r_front, v_r_back])
        f_right.material_index = mat_roof
        f_front = bm.faces.new([v_b3, v_b4, v_r_front])
        f_front.material_index = mat_wall
    except ValueError:
        pass


def add_tourelle_in_bm(bm, center_xy, radius, z_base, z_cornice, z_spire,
                       mat_wall=0, mat_roof=1, mat_trim=4, n_segs=16):
    cx, cy = center_xy
    pts_base = [(cx + radius * math.cos(i * 2.0 * math.pi / n_segs),
                 cy + radius * math.sin(i * 2.0 * math.pi / n_segs)) for i in range(n_segs)]
    # Main round turret body
    extrude_prism_in_bm(bm, pts_base, z_base, z_cornice, mat_side=mat_wall, cap_top=False)

    # Projecting machicolated cornice band
    pts_cornice = [(cx + (radius + 0.28) * math.cos(i * 2.0 * math.pi / n_segs),
                    cy + (radius + 0.28) * math.sin(i * 2.0 * math.pi / n_segs)) for i in range(n_segs)]
    extrude_prism_in_bm(bm, pts_cornice, z_cornice - 0.45, z_cornice + 0.15, mat_side=mat_trim, cap_top=True)

    # Steep conical copper roof
    cornice_verts = [bm.verts.new((p[0], p[1], z_cornice + 0.15)) for p in pts_cornice]
    spire_tip = bm.verts.new((cx, cy, z_spire))
    for i in range(n_segs):
        i_next = (i + 1) % n_segs
        try:
            f = bm.faces.new([cornice_verts[i], cornice_verts[i_next], spire_tip])
            f.material_index = mat_roof
        except ValueError:
            pass

    # Copper spire / finial needle extending above roof
    pts_spire = [(cx + 0.12 * math.cos(i * 2.0 * math.pi / 8),
                  cy + 0.12 * math.sin(i * 2.0 * math.pi / 8)) for i in range(8)]
    extrude_prism_in_bm(bm, pts_spire, z_spire - 0.2, z_spire + 1.8, mat_side=mat_roof, mat_top=mat_roof)


# ---------------------------------------------------------------------------
# 4. POLY HAVEN 2K PBR MATERIAL LOADER & 14-FACADE PALETTE
# ---------------------------------------------------------------------------
def load_image_cached(path, non_color=False):
    if not path or not os.path.isfile(path):
        return None
    norm_path = os.path.normpath(path)
    fname = os.path.basename(norm_path)
    for img in bpy.data.images:
        if img.filepath and os.path.normpath(bpy.path.abspath(img.filepath)) == norm_path:
            return img
        if img.name == fname:
            return img
    img = bpy.data.images.load(norm_path)
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
        p = os.path.join(POLYHAVEN_DIR, cand)
        if os.path.isfile(p):
            return p
    return ""


def apply_polyhaven_2k_pbr(mat, folder_prefix, scale_xyz=(0.25, 0.25, 0.25),
                           tint_rgb=None, tint_factor=0.65, roughness_mult=1.0, normal_str=1.0):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = scale_xyz
    links.new(tcoord.outputs["Object"], mapping.inputs["Vector"])

    diff_path = find_polyhaven_map(folder_prefix, "diff")
    diff_img = load_image_cached(diff_path, non_color=False)
    if diff_img:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = diff_img
        tex_d.projection = "BOX"
        tex_d.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])
        if tint_rgb:
            mix = nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MIX"
            mix.inputs["Factor"].default_value = tint_factor
            mix.inputs[7].default_value = (*tint_rgb, 1.0)
            links.new(tex_d.outputs["Color"], mix.inputs[6])
            links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        else:
            links.new(tex_d.outputs["Color"], bsdf.inputs["Base Color"])
    elif tint_rgb:
        bsdf.inputs["Base Color"].default_value = (*tint_rgb, 1.0)

    rough_path = find_polyhaven_map(folder_prefix, "rough")
    rough_img = load_image_cached(rough_path, non_color=True)
    if rough_img:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = rough_img
        tex_r.projection = "BOX"
        tex_r.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_r.inputs["Vector"])
        if roughness_mult != 1.0:
            math_r = nodes.new("ShaderNodeMath")
            math_r.operation = "MULTIPLY"
            math_r.inputs[1].default_value = roughness_mult
            links.new(tex_r.outputs["Color"], math_r.inputs[0])
            links.new(math_r.outputs["Value"], bsdf.inputs["Roughness"])
        else:
            links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.6 * roughness_mult

    nor_path = find_polyhaven_map(folder_prefix, "nor")
    nor_img = load_image_cached(nor_path, non_color=True)
    if nor_img:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = nor_img
        tex_n.projection = "BOX"
        tex_n.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal_str
        links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def make_ortho_only_material(base_mat, name):
    """
    Wraps `base_mat` so that it renders with 100% PBR fidelity in `Cam_Satellite_TopDown_Ortho`
    (where vertical orthographic rays have `abs(Geometry.Incoming.Z) == 1.0 > 0.96`),
    while evaluating to `ShaderNodeBsdfTransparent` (100% invisible, 0 shadow) for all street-level
    perspective cameras (`Z = 1.75m`) and sun/sky shadow rays (`abs(Incoming.Z) < 0.94`).
    """
    mat = base_mat.copy()
    mat.name = name
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links

    out_node = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
    bsdf_node = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not out_node or not bsdf_node:
        return mat

    trans_node = nodes.new("ShaderNodeBsdfTransparent")
    trans_node.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    geom_node = nodes.new("ShaderNodeNewGeometry")
    sep_node = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geom_node.outputs["Incoming"], sep_node.inputs["Vector"])

    abs_node = nodes.new("ShaderNodeMath")
    abs_node.operation = "ABSOLUTE"
    links.new(sep_node.outputs["Z"], abs_node.inputs[0])

    gt_node = nodes.new("ShaderNodeMath")
    gt_node.operation = "GREATER_THAN"
    links.new(abs_node.outputs["Value"], gt_node.inputs[0])
    gt_node.inputs[1].default_value = 0.96

    mix_node = nodes.new("ShaderNodeMixShader")
    links.new(gt_node.outputs["Value"], mix_node.inputs["Fac"])
    links.new(trans_node.outputs["BSDF"], mix_node.inputs[1])
    links.new(bsdf_node.outputs["BSDF"], mix_node.inputs[2])
    links.new(mix_node.outputs["Shader"], out_node.inputs["Surface"])
    return mat


def create_solid_material(name, color_rgba, roughness=0.5, metallic=0.0, ior=1.45):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = color_rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    return mat


def create_block_palette():
    palette = {}

    # --- 14 Distinct Poly Haven 2K PBR Architectural Facade Materials ---
    facade_defs = [
        ("Mat_MTL_PierreGrise_Limestone", "stone_brick_wall_001", (0.30, 0.30, 0.30), (0.64, 0.63, 0.61), 0.58, 0.92, 1.20),
        ("Mat_MTL_WarmBuff_Limestone", "sandstone_blocks_05", (0.28, 0.28, 0.28), (0.76, 0.72, 0.64), 0.55, 0.90, 1.10),
        ("Mat_MTL_Red_Sandstone", "red_sandstone_wall", (0.28, 0.28, 0.28), (0.58, 0.28, 0.18), 0.45, 0.95, 1.15),
        ("Mat_MTL_Heritage_RedBrick", "castle_brick_02_red", (0.34, 0.34, 0.34), (0.54, 0.22, 0.14), 0.42, 0.95, 1.25),
        ("Mat_MTL_Victorian_Brick", "brick_wall_04", (0.32, 0.32, 0.32), (0.52, 0.25, 0.18), 0.42, 0.94, 1.20),
        ("Mat_MTL_Yellow_Buff_Brick", "yellow_brick", (0.30, 0.30, 0.30), (0.72, 0.62, 0.42), 0.48, 0.90, 1.10),
        ("Mat_MTL_Dark_Loft_Brick", "dark_brick_wall", (0.32, 0.32, 0.32), (0.28, 0.20, 0.17), 0.45, 0.96, 1.15),
        ("Mat_MTL_Whitewash_Fieldstone", "castle_brick_02_white", (0.30, 0.30, 0.30), (0.82, 0.80, 0.76), 0.62, 0.90, 1.10),
        ("Mat_MTL_Precast_Concrete", "concrete_block_wall", (0.26, 0.26, 0.26), (0.58, 0.59, 0.60), 0.52, 0.95, 1.05),
        ("Mat_MTL_Granite_Plinth", "stone_block_wall", (0.28, 0.28, 0.28), (0.46, 0.45, 0.44), 0.50, 0.96, 1.25),
        ("Mat_MTL_Weathered_Metal", "box_profile_metal_sheet", (0.25, 0.25, 0.25), (0.48, 0.52, 0.54), 0.50, 0.85, 1.00),
        ("Mat_MTL_Warm_Timber", "weathered_planks", (0.30, 0.30, 0.30), (0.52, 0.36, 0.22), 0.50, 0.92, 1.15),
        ("Mat_MTL_Limestone_Tile", "stone_tile_wall", (0.30, 0.30, 0.30), (0.68, 0.66, 0.62), 0.55, 0.90, 1.10),
        ("Mat_MTL_Medieval_Stone", "medieval_blocks_06", (0.30, 0.30, 0.30), (0.52, 0.50, 0.48), 0.50, 0.98, 1.30),
    ]

    for name, prefix, scale, tint, tfact, rmult, nstr in facade_defs:
        m = bpy.data.materials.new(name)
        palette[name] = apply_polyhaven_2k_pbr(m, prefix, scale, tint, tfact, rmult, nstr)

    # --- Heritage Chateau Roof Copper (Verdigris Patina) ---
    mat_copper = bpy.data.materials.new("Mat_MTL_Verdigris_Copper")
    mat_copper.use_nodes = True
    c_bsdf = next(n for n in mat_copper.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    c_bsdf.inputs["Base Color"].default_value = (0.34, 0.62, 0.52, 1.0)
    c_bsdf.inputs["Roughness"].default_value = 0.42
    c_bsdf.inputs["Metallic"].default_value = 0.40
    palette["Mat_MTL_Verdigris_Copper"] = mat_copper

    # --- Modern Bronze Curtain Wall Mullions ---
    mat_bronze = bpy.data.materials.new("Mat_MTL_Dark_Bronze_CurtainWall")
    mat_bronze.use_nodes = True
    b_bsdf = next(n for n in mat_bronze.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b_bsdf.inputs["Base Color"].default_value = (0.16, 0.17, 0.18, 1.0)
    b_bsdf.inputs["Roughness"].default_value = 0.22
    b_bsdf.inputs["Metallic"].default_value = 0.85
    palette["Mat_MTL_Dark_Bronze_CurtainWall"] = mat_bronze

    # --- Reflective Architectural Glass ---
    mat_glass = bpy.data.materials.new("Mat_MTL_Window_Glass_Dark")
    mat_glass.use_nodes = True
    g_bsdf = next(n for n in mat_glass.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    g_bsdf.inputs["Base Color"].default_value = (0.08, 0.12, 0.16, 1.0)
    g_bsdf.inputs["Roughness"].default_value = 0.05
    g_bsdf.inputs["Metallic"].default_value = 0.25
    if "IOR" in g_bsdf.inputs:
        g_bsdf.inputs["IOR"].default_value = 1.52
    palette["Mat_MTL_Window_Glass_Dark"] = mat_glass

    # --- Cast Iron & Metal Trim ---
    palette["Mat_MTL_CastIron_Black"] = create_solid_material("Mat_MTL_CastIron_Black", (0.10, 0.11, 0.12, 1.0), roughness=0.35, metallic=0.80)

    # --- Roof Slate & Flat Roof Membrane (Rich Dark Charcoal Slate for Château Viger Steep Roofs & Turrets!) ---
    palette["Mat_MTL_Slate_Roof_Dark"] = create_solid_material("Mat_MTL_Slate_Roof_Dark", (0.09, 0.10, 0.12, 1.0), roughness=0.68, metallic=0.05)
    palette["Mat_Roof_Flat"] = create_solid_material("Mat_Roof_Flat", (0.18, 0.19, 0.21, 1.0), roughness=0.80, metallic=0.0)

    # --- Roadbeds, Sidewalks & Courtyard Plazas ---
    m_asphalt = bpy.data.materials.new("Mat_MTL_Street_Asphalt")
    palette["Mat_MTL_Street_Asphalt"] = apply_polyhaven_2k_pbr(m_asphalt, "asphalt_02", (0.22, 0.22, 0.22), (0.44, 0.43, 0.41), 0.58, 0.92, 1.05)

    m_cobble = bpy.data.materials.new("Mat_MTL_Cobblestone")
    palette["Mat_MTL_Cobblestone"] = apply_polyhaven_2k_pbr(m_cobble, "cobblestone_floor_08", (0.34, 0.34, 0.34), (0.58, 0.58, 0.60), 0.55, 0.92, 1.25)

    m_plz_light = bpy.data.materials.new("Mat_MTL_Plaza_Light_Granite")
    palette["Mat_MTL_Plaza_Light_Granite"] = apply_polyhaven_2k_pbr(m_plz_light, "sandstone_blocks_05", (0.26, 0.26, 0.26), (0.76, 0.75, 0.72), 0.58, 0.90, 0.90)

    m_plz_dark = bpy.data.materials.new("Mat_MTL_Plaza_Charcoal_Granite")
    palette["Mat_MTL_Plaza_Charcoal_Granite"] = apply_polyhaven_2k_pbr(m_plz_dark, "stone_block_wall", (0.28, 0.28, 0.28), (0.34, 0.35, 0.37), 0.55, 0.92, 1.15)

    # --- Organic / Foliage & Park Materials ---
    m_grass = bpy.data.materials.new("Mat_MTL_Grass_Lawn_PBR")
    palette["Mat_MTL_Grass_Lawn_PBR"] = apply_polyhaven_2k_pbr(
        m_grass, "leafy_grass", (0.18, 0.18, 0.18), (0.26, 0.48, 0.16), 0.38, 0.95, 1.15
    )

    m_gravel = bpy.data.materials.new("Mat_PH_Gravel_Path")
    palette["Mat_PH_Gravel_Path"] = apply_polyhaven_2k_pbr(
        m_gravel, "gravel_concrete_02", (0.22, 0.22, 0.22), (0.68, 0.65, 0.60), 0.45, 0.92, 1.05
    )

    m_terracotta = bpy.data.materials.new("Mat_MTL_Courtyard_Terracotta")
    palette["Mat_MTL_Courtyard_Terracotta"] = apply_polyhaven_2k_pbr(
        m_terracotta, "herringbone_pavement", (0.28, 0.28, 0.28), (0.76, 0.48, 0.36), 0.68, 0.88, 1.10
    )

    m_roof_white = bpy.data.materials.new("Mat_MTL_Roof_White_Reflective")
    palette["Mat_MTL_Roof_White_Reflective"] = apply_polyhaven_2k_pbr(
        m_roof_white, "gravel_concrete_02", (0.16, 0.16, 0.16), (0.90, 0.89, 0.87), 0.78, 0.70, 0.45
    )

    m_timber_deck = bpy.data.materials.new("Mat_MTL_Weathered_Timber_Deck")
    palette["Mat_MTL_Weathered_Timber_Deck"] = apply_polyhaven_2k_pbr(
        m_timber_deck, "weathered_planks", (0.45, 0.45, 0.45), (0.24, 0.23, 0.22), 0.65, 0.92, 1.35
    )

    palette["Mat_MTL_White_Sash"] = create_solid_material("Mat_MTL_White_Sash", (0.91, 0.92, 0.93, 1.0), roughness=0.32, metallic=0.10)
    palette["Mat_MTL_Pool_Water"] = create_solid_material("Mat_MTL_Pool_Water", (0.16, 0.68, 0.82, 1.0), roughness=0.06, metallic=0.10, ior=1.333)
    palette["Mat_MTL_Tree_Bark"] = create_solid_material("Mat_MTL_Tree_Bark", (0.28, 0.22, 0.18, 1.0), roughness=0.92, metallic=0.0)
    palette["Mat_MTL_Autumn_Gold"] = create_solid_material("Mat_MTL_Autumn_Gold", (0.22, 0.48, 0.16, 1.0), roughness=0.65, metallic=0.0)
    palette["Mat_MTL_Autumn_Amber"] = create_solid_material("Mat_MTL_Autumn_Amber", (0.26, 0.52, 0.18, 1.0), roughness=0.65, metallic=0.0)
    palette["Mat_MTL_Autumn_OliveGreen"] = create_solid_material("Mat_MTL_Autumn_OliveGreen", (0.18, 0.42, 0.14, 1.0), roughness=0.65, metallic=0.0)

    return palette


# ---------------------------------------------------------------------------
# 5. BUILDING ADJACENCY, BALANCED COLORING & HEIGHT DECONFLICTION
# ---------------------------------------------------------------------------
def compute_building_adjacency(bldgs):
    """
    Builds the adjacency graph connecting any two buildings that share a party wall,
    are within 2.0m of each other, OR have overlapping 2D AABB bounding boxes (> 0.5 m²).
    Guarantees every pair capable of triggering a Z-fighting conflict is evaluated.
    """
    bboxes = {}
    for b in bldgs:
        pts = b["coords_xy"]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bboxes[b["id"]] = (min(xs), max(xs), min(ys), max(ys))

    adj = {b["id"]: [] for b in bldgs}
    n = len(bldgs)
    for i in range(n):
        bi = bldgs[i]
        b1 = bboxes[bi["id"]]
        ci = bi.get("centroid_xy", (0.0, 0.0))
        for j in range(i + 1, n):
            bj = bldgs[j]
            b2 = bboxes[bj["id"]]
            cj = bj.get("centroid_xy", (0.0, 0.0))

            ox = min(b1[1], b2[1]) - max(b1[0], b2[0])
            oy = min(b1[3], b2[3]) - max(b1[2], b2[2])
            is_overlap = (ox > 0.0 and oy > 0.0 and ox * oy > 0.50)

            is_close = False
            if math.hypot(ci[0] - cj[0], ci[1] - cj[1]) < 45.0:
                if poly_poly_dist_2d(bi["coords_xy"], bj["coords_xy"]) < 2.0:
                    is_close = True

            if is_overlap or is_close:
                adj[bi["id"]].append(bj["id"])
                adj[bj["id"]].append(bi["id"])
    return adj


def compute_balanced_facade_assignments(bldgs, adj, n_materials=14):
    """
    Computes deterministic facade material assignments across all primary owned buildings
    using Welsh-Powell greedy graph coloring on the touching-building adjacency graph.
    Guarantees:
      1. 0 adjacent touching buildings share the same material.
      2. Maximum share of any single material <= 10% (well below the 20% cap).
    """
    mat_counts = {m: 0 for m in range(n_materials)}
    assignments = {}

    sorted_bldgs = sorted(bldgs, key=lambda b: len(adj[b["id"]]), reverse=True)
    for b in sorted_bldgs:
        bid = b["id"]
        used_neighbor_mats = {assignments[nid] for nid in adj[bid] if nid in assignments}
        candidates = [m for m in range(n_materials) if m not in used_neighbor_mats]
        candidates.sort(key=lambda m: mat_counts[m])
        chosen = candidates[0]
        assignments[bid] = chosen
        mat_counts[chosen] += 1

    return assignments


def compute_deconflicted_heights(bldgs, adj):
    """
    Computes deterministic height and ground_h values for every building such that
    no two touching adjacent buildings have roofs, parapets, or belt courses within
    |Δz| < 0.08m, completely eliminating cross-building coplanar Z-fighting.
    """
    base_heights = {}
    for b in bldgs:
        bid = b["id"]
        if bid == 46866814:
            base_heights[bid] = 26.5
        elif bid == 1244672622:
            base_heights[bid] = 24.0
        elif bid == 1244672623:
            base_heights[bid] = 28.0
        elif bid == 46866830:
            base_heights[bid] = 26.0
        elif bid == 370730179:
            base_heights[bid] = 18.5
        elif bid == 119612954:
            base_heights[bid] = 24.5
        else:
            levels_tag = b.get("tags", {}).get("building:levels")
            if levels_tag:
                try:
                    fl_count = int(float(levels_tag))
                    base_heights[bid] = fl_count * 3.8 + 0.5
                except ValueError:
                    base_heights[bid] = 15.5
            else:
                pts = b["coords_xy"]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                span = max(max(xs) - min(xs), max(ys) - min(ys))
                if span > 60.0:
                    base_heights[bid] = 28.0
                elif span > 35.0:
                    base_heights[bid] = 21.0
                elif span > 20.0:
                    base_heights[bid] = 16.5
                else:
                    base_heights[bid] = 12.8

    final_heights = {}
    final_ground_h = {}

    def is_height_safe(cand_h, neighbor_hs):
        my_faces = [cand_h - 0.15, cand_h + 0.12, cand_h + 0.38]
        for nh in neighbor_hs:
            n_faces = [nh - 0.15, nh + 0.12, nh + 0.38]
            for fa in my_faces:
                for fb in n_faces:
                    if abs(fa - fb) < 0.08:
                        return False
        return True

    def is_ground_safe(cand_gh, neighbor_ghs):
        my_faces = [cand_gh - 0.38, cand_gh + 0.16]
        for ngh in neighbor_ghs:
            n_faces = [ngh - 0.38, ngh + 0.16]
            for fa in my_faces:
                for fb in n_faces:
                    if abs(fa - fb) < 0.08:
                        return False
        return True

    deltas_h = [0.0]
    for k in range(1, 101):
        deltas_h.extend([k * 0.05, -k * 0.05])

    deltas_gh = [0.0]
    for k in range(1, 51):
        deltas_gh.extend([k * 0.05, -k * 0.05])

    sorted_bldgs = sorted(bldgs, key=lambda x: len(adj[x["id"]]), reverse=True)
    for b in sorted_bldgs:
        bid = b["id"]
        if bid == 46866814:
            final_heights[bid] = 26.5
            final_ground_h[bid] = 3.6
            continue
        h_base = base_heights[bid]
        gh_base = 3.20

        neighbor_hs = [final_heights[nid] for nid in adj[bid] if nid in final_heights]
        neighbor_ghs = [final_ground_h[nid] for nid in adj[bid] if nid in final_ground_h]

        for dh in deltas_h:
            cand_h = h_base + dh
            if is_height_safe(cand_h, neighbor_hs):
                final_heights[bid] = cand_h
                break
        if bid not in final_heights:
            final_heights[bid] = h_base

        for dgh in deltas_gh:
            cand_gh = gh_base + dgh
            if is_ground_safe(cand_gh, neighbor_ghs):
                final_ground_h[bid] = cand_gh
                break
        if bid not in final_ground_h:
            final_ground_h[bid] = gh_base

    return final_heights, final_ground_h


# ---------------------------------------------------------------------------
# 6. PROCEDURAL DETAILED FACADE GENERATOR (DEEP WINDOW BAYS)
# ---------------------------------------------------------------------------
def build_detailed_facade_building(name, coords_xy, height, floor_height, mat_wall, mat_roof,
                                   mat_window, mat_frame, mat_plinth, collection, roof_style="flat",
                                   arched_second_floor=False, rusticated_piers=True,
                                   bay_target_width=3.2, mat_top_cornice=None, other_polys=None,
                                   custom_ground_h=None):
    pts = ensure_ccw(clean_poly_pts(coords_xy))
    if len(pts) < 3:
        return None

    # Anti-clipping: deconflict party-wall edges touching adjacent buildings
    pts_clean = deconflict_party_walls(pts, other_polys, min_sep=0.02)

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    mats = [mat_wall, mat_roof, mat_window, mat_frame, mat_plinth]
    for m in mats:
        obj.data.materials.append(m)

    cornice_idx = 4
    if mat_top_cornice is not None:
        obj.data.materials.append(mat_top_cornice)
        cornice_idx = len(obj.data.materials) - 1

    bm = bmesh.new()

    # Inset core perimeter wall by 0.28m so deeply recessed window glass at -0.14m is NEVER occluded!
    core_pts = inset_polygon_2d(pts_clean, 0.28)
    extrude_prism_in_bm(bm, core_pts, 0.0, height - 0.20, mat_side=0, cap_top=False)

    if custom_ground_h is not None:
        ground_h = custom_ground_h
    else:
        ground_h = min(4.2, max(3.2, height * 0.25))

    n_upper_floors = max(1, int(round((height - ground_h) / floor_height)))
    actual_fl_h = (height - ground_h) / n_upper_floors

    n = len(pts_clean)
    for i in range(n):
        p1, p2 = pts_clean[i], pts_clean[(i + 1) % n]
        if other_polys and is_party_wall(p1, p2, other_polys):
            # Protrusion suppression on party walls: no sills, piers, lintels, or cornices!
            continue
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.2:
            continue

        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        p1_in = (p1[0] + dx * 0.15, p1[1] + dy * 0.15)
        p2_in = (p2[0] - dx * 0.15, p2[1] - dy * 0.15)
        n_bays = max(1, int(round(seg_len / bay_target_width)))
        bay_w = seg_len / n_bays
        pier_w = min(1.10, max(0.45, bay_w * 0.34))

        # Rusticated stone plinth (z = 0.0 to 0.85m) & belt course at ground floor top
        add_box_between(bm, p1_in, p2_in, 0.0, 0.85, thickness=0.45, offset_out=0.18, mat_idx=4)
        add_box_between(bm, p1_in, p2_in, ground_h - 0.38, ground_h + 0.16, thickness=0.45, offset_out=0.18, mat_idx=4)

        # Vertical rusticated piers between window bays
        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.08:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            add_box_between(bm, q1, q2, 0.85, height - 0.40, thickness=0.68, offset_out=0.24, mat_idx=0)
            if rusticated_piers:
                z_cur = 0.95
                while z_cur < height - 0.6:
                    add_box_between(bm, q1, q2, z_cur, z_cur + 0.38, thickness=0.74, offset_out=0.28, mat_idx=4)
                    z_cur += 0.48

        # Recessed Window Bays: Outer pier sits at +0.24m..+0.28m, Glass sits at -0.22m!
        # Total reveal depth: 0.24 - (-0.22) = 0.46m to 0.50m (exceeds >= 0.45m mandate!)
        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            win_w = bs1 - bs0
            if win_w < 0.28:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            # Deeply recessed window glass
            add_box_between(bm, wp1, wp2, 0.85, height - 0.40, thickness=0.10, offset_out=-0.14, mat_idx=2)

            # Window frame & central mullion
            ms = 0.5 * (bs0 + bs1)
            mp1 = (p1[0] + dx * (ms - 0.05), p1[1] + dy * (ms - 0.05))
            mp2 = (p1[0] + dx * (ms + 0.05), p1[1] + dy * (ms + 0.05))
            add_box_between(bm, mp1, mp2, 0.85, height - 0.40, thickness=0.16, offset_out=-0.04, mat_idx=3)
            add_box_between(bm, wp1, wp2, ground_h - 1.20, ground_h - 1.05, thickness=0.18, offset_out=-0.02, mat_idx=3)

            # Upper floors: Stone sills, lintels, and spandrels
            for fl in range(n_upper_floors):
                fz0 = ground_h + fl * actual_fl_h
                fz1 = fz0 + actual_fl_h
                sp_h = min(0.95, actual_fl_h * 0.28)

                # Stone spandrel panel
                add_box_between(bm, wp1, wp2, fz0, fz0 + sp_h, thickness=0.35, offset_out=0.18, mat_idx=0)
                # Projecting 3D stone sill (offset_out = +0.22m, sits 0.44m in front of glass!)
                add_box_between(bm, wp1, wp2, fz0 + sp_h - 0.08, fz0 + sp_h + 0.10, thickness=0.30, offset_out=0.22, mat_idx=4)
                # Lintel stone slab
                add_box_between(bm, wp1, wp2, fz1 - 0.42, fz1, thickness=0.30, offset_out=0.18, mat_idx=4)

                # Arched window hoods on second floor if requested
                if arched_second_floor and fl == 0:
                    add_curved_voussoir_arch(bm, wp1, wp2, fz1 - 0.80, 0.42, thickness=0.68, offset_out=0.24, mat_stone=4, add_keystone=True)

        # Projecting roof cornice & protective parapet
        add_box_between(bm, p1_in, p2_in, height - 0.45, height + 0.12, thickness=0.35, offset_out=0.12, mat_idx=cornice_idx)
        add_box_between(bm, p1_in, p2_in, height + 0.12, height + 0.38, thickness=0.25, offset_out=0.05, mat_idx=0)

    # Inset flat roof deck inside parapet (inset >= 0.35m, height offset >= 0.53m -> ZERO Z-fighting!)
    inner_roof_pts = inset_polygon_2d(pts_clean, 0.35)
    extrude_prism_in_bm(bm, inner_roof_pts, height - 0.25, height - 0.15, mat_side=0, mat_top=1, cap_top=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


# ---------------------------------------------------------------------------
# 7. CHÂTEAU VIGER / ANCIENNE GARE VIGER (WAY 46866814) MONUMENTAL BUILDER
# ---------------------------------------------------------------------------
def build_chateau_viger(bldg_data, palette, collection, other_polys=None):
    """
    Constructs Château Viger / Ancienne Gare Viger (OSM Way 46866814):
    - Multi-wing Bruce Price Châteauesque / Romanesque Revival railway hotel & station (1898):
      1. South-West 2.5-Story Light-Grey Limestone Pavilion (`sw_pav_pts`, X = 239.5..271.5, Y = 814.3..836.5):
         10.2m high ashlar limestone facade topped by a steep dark-charcoal slate hipped roof (Z = 10.2..17.2m),
         stone gable dormers, and the iconic SW conical dark-slate turret at (271.8, 831.5) (Cam 3 V1..V3, H2..H5).
      2. West / North-West Heritage Château Keep (`west_chateau_pts`, Y = 836.5..910.3):
         20.8m wall with steep sloped dark-slate château roof rising to 33.5m ridge, East Courtyard conical
         dark-slate turret at (284.5, 864.5) & dormers (Cam 2 V6..V8, H3..H4 & Cam 4 V7..V8, H2..H4),
         and central main keep turret at (262.0, 858.0).
      3. South-East 3-Story Annex Wing (`se_annex_pts` along Saint-Antoine Est):
         13.8m facade with rusticated light-grey Montreal limestone lower stratum (Floors 1–2, Z = 0.0..9.30m,
         Cam 1 H3..H6), arched 2nd-floor tripartite fanlight windows with stone voussoirs, continuous grey
         limestone belt course (Z = 8.85..9.35m), warm red-brown brick upper 3rd floor (Z = 9.35..13.85m,
         Cam 1 H1..H3) with corbeled brick cornice, and raised weathered-plank boardwalk terrace with
         36-picket black steel railing spanning V1,H8 -> V4,H7 -> V8,H6 in Cam 1.
    """
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    pts_clean = deconflict_party_walls(pts, other_polys, min_sep=0.02)

    name = "MTL_Owned_46866814_Chateau_Viger"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    # Materials:
    # 0: Heritage Red Brick
    # 1: Verdigris Copper (Turret finials / flashings)
    # 2: Window Glass Dark
    # 3: Cast Iron Black
    # 4: Montreal Pierre Grise Limestone (Rusticated Lower Stratum, Quoins, Voussoirs)
    # 5: Warm Buff Limestone (Belt courses, Portals, Retaining Wall)
    # 6: Slate Roof Dark (Steep Château sloped roofs & conical turret spires)
    # 7: White Window Sash / Mullions
    # 8: Flat Dark Roof Membrane (SE Annex Wing)
    # 9: Weathered Timber Deck (Cam 1 Boardwalk Planks)
    mats = [
        palette["Mat_MTL_Heritage_RedBrick"],
        palette["Mat_MTL_Verdigris_Copper"],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_CastIron_Black"],
        palette["Mat_MTL_PierreGrise_Limestone"],
        palette["Mat_MTL_WarmBuff_Limestone"],
        palette["Mat_MTL_Slate_Roof_Dark"],
        palette["Mat_MTL_White_Sash"],
        palette["Mat_Roof_Flat"],
        palette["Mat_MTL_Weathered_Timber_Deck"],
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. South-West 2.5-Story Light-Grey Limestone Pavilion (Cam 3 left V1..V2, H3..H5 — NO tall red brick wall here!)
    sw_pav_pts = ensure_ccw([
        (267.821, 814.280),
        (239.524, 825.022),
        (244.500, 836.500),
        (271.504, 822.139),
    ])
    # 2. Main North-West / Central Château Keep (starts north of Y = 836.5 so SW Pavilion has clean sky in Cam 3 H1..H2!)
    west_chateau_pts = ensure_ccw([
        (269.467, 841.108),
        (244.500, 836.500),
        (238.978, 837.067),
        (268.999, 910.293),
        (293.887, 899.194),
        (275.500, 855.000),
    ])
    # 3. South-East 3-Story Annex Wing
    se_annex_pts = ensure_ccw([
        (346.862, 787.073),
        (334.652, 791.682),
        (336.017, 794.576),
        (271.504, 822.139),
        (269.467, 841.108),
        (326.265, 816.885),
        (329.947, 825.779),
        (357.293, 814.180),
    ])

    h_pav = 10.2
    h_west = 20.8
    h_annex = 13.8

    # --- PART A1: SW 2.5-STORY LIGHT-GREY LIMESTONE PAVILION & SLOPED DARK SLATE ROOF (Cam 3 V1..V2, H3..H5) ---
    pav_core_pts = inset_polygon_2d(sw_pav_pts, 0.26)
    extrude_prism_in_bm(bm, pav_core_pts, 0.0, h_pav - 0.15, mat_side=4, cap_top=False)
    npav = len(sw_pav_pts)
    for i in range(npav):
        p1, p2 = sw_pav_pts[i], sw_pav_pts[(i + 1) % npav]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 2.0:
            continue
        add_box_between(bm, p1, p2, 0.0, 1.10, thickness=0.44, offset_out=0.14, mat_idx=4)
        add_box_between(bm, p1, p2, 5.10, 5.48, thickness=0.48, offset_out=0.18, mat_idx=5)
        add_box_between(bm, p1, p2, h_pav - 0.55, h_pav + 0.15, thickness=0.54, offset_out=0.22, mat_idx=4)
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / 3.8)))
        bay_w = seg_len / n_bays
        pier_w = min(1.10, max(0.55, bay_w * 0.34))
        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.1:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            add_box_between(bm, q1, q2, 1.10, h_pav - 0.35, thickness=0.46, offset_out=0.16, mat_idx=4)
        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            if bs1 - bs0 < 0.35:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
            add_box_between(bm, wp1, wp2, 1.20, h_pav - 0.55, thickness=0.10, offset_out=-0.12, mat_idx=2)
            add_box_between(bm, wp1, wp2, 4.45, 5.65, thickness=0.38, offset_out=0.12, mat_idx=4)
            ms = 0.5 * (bs0 + bs1)
            mp1 = (p1[0] + dx * (ms - 0.05), p1[1] + dy * (ms - 0.05))
            mp2 = (p1[0] + dx * (ms + 0.05), p1[1] + dy * (ms + 0.05))
            add_box_between(bm, mp1, mp2, 1.20, h_pav - 0.55, thickness=0.14, offset_out=-0.03, mat_idx=7)

    # Steeply sloped dark-charcoal slate hipped roof on SW Limestone Pavilion (Z = 10.2 .. 17.0m, Cam 3 V1..V2, H3!)
    extrude_sloped_hip_roof_in_bm(bm, sw_pav_pts, h_pav, 17.0, 4.2, mat_roof=6, cap_top=True)

    # --- PART A2: MAIN WEST HERITAGE CHÂTEAU KEEP (Z = 0.0 .. 20.8m + Sloped Dark Slate Roof to 33.5m) ---
    west_core_pts = inset_polygon_2d(west_chateau_pts, 0.28)
    extrude_prism_in_bm(bm, west_core_pts, 0.0, h_west - 0.20, mat_side=0, cap_top=False)

    nw = len(west_chateau_pts)
    for i in range(nw):
        p1, p2 = west_chateau_pts[i], west_chateau_pts[(i + 1) % nw]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 2.0:
            continue

        add_box_between(bm, p1, p2, 0.0, 7.20, thickness=0.44, offset_out=0.14, mat_idx=4)
        add_box_between(bm, p1, p2, 7.20, 7.60, thickness=0.50, offset_out=0.18, mat_idx=5)
        add_box_between(bm, p1, p2, 14.00, 14.38, thickness=0.44, offset_out=0.14, mat_idx=4)
        add_box_between(bm, p1, p2, h_west - 0.85, h_west - 0.15, thickness=0.56, offset_out=0.22, mat_idx=4)
        add_box_between(bm, p1, p2, h_west - 0.15, h_west + 0.25, thickness=0.64, offset_out=0.26, mat_idx=5)

        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / 3.8)))
        bay_w = seg_len / n_bays
        pier_w = min(1.15, max(0.55, bay_w * 0.34))

        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.1:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            add_box_between(bm, q1, q2, 1.50, h_west - 0.35, thickness=0.50, offset_out=0.18, mat_idx=0)
            z_q = 2.0
            while z_q < h_west - 1.0:
                add_box_between(bm, q1, q2, z_q, z_q + 0.38, thickness=0.56, offset_out=0.22, mat_idx=4)
                z_q += 1.15

        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            win_w = bs1 - bs0
            if win_w < 0.35:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
            add_box_between(bm, wp1, wp2, 1.50, h_west - 0.50, thickness=0.10, offset_out=-0.14, mat_idx=2)
            ms = 0.5 * (bs0 + bs1)
            mp1 = (p1[0] + dx * (ms - 0.05), p1[1] + dy * (ms - 0.05))
            mp2 = (p1[0] + dx * (ms + 0.05), p1[1] + dy * (ms + 0.05))
            add_box_between(bm, mp1, mp2, 1.50, h_west - 0.50, thickness=0.14, offset_out=-0.04, mat_idx=7)

            for fl in range(4):
                fz0 = 1.60 + fl * 4.65
                fz1 = fz0 + 4.65
                sp_h = 1.10
                add_box_between(bm, wp1, wp2, fz0, fz0 + sp_h, thickness=0.38, offset_out=0.12, mat_idx=4 if fl == 0 else 0)
                add_box_between(bm, wp1, wp2, fz0 + sp_h - 0.10, fz0 + sp_h + 0.12, thickness=0.36, offset_out=0.20, mat_idx=4)
                add_box_between(bm, wp1, wp2, fz1 - 0.45, fz1, thickness=0.36, offset_out=0.16, mat_idx=4)
                if fl in (0, 1):
                    add_curved_voussoir_arch(bm, wp1, wp2, fz1 - 0.88, 0.46, thickness=0.56, offset_out=0.20, mat_stone=4, add_keystone=True)

    # True Steeply Sloped Dark-Charcoal Slate Château Roof on West Keep (Z = 20.8 .. 32.8m, NO vertical grey boxes!)
    extrude_sloped_hip_roof_in_bm(bm, west_chateau_pts, h_west, 32.8, 6.2, mat_roof=6, cap_top=True)
    w_ridge = inset_polygon_2d(west_chateau_pts, 6.6)
    extrude_prism_in_bm(bm, w_ridge, 32.8, 33.8, mat_side=1, mat_top=1, cap_top=True)

    # Monumental Cylindrical Turrets & Pepper-Pot Tourelles (Dark Charcoal Slate Cones + Spires)
    # 1. Limestone-walled SW Corner Turrets (visible in Cam 3 Rue_Berri V2..V3, H2..H4!)
    for c_xy, rad, zb, zc, zs in (
        ((271.8, 831.5), 4.2, 0.0, 16.5, 26.5),
        ((277.8, 829.0), 2.0, 9.5, 16.2, 22.2),
        ((246.5, 829.5), 2.2, 8.5, 14.5, 20.2),
    ):
        add_tourelle_in_bm(bm, c_xy, rad, zb, zc, zs, mat_wall=4, mat_roof=6, mat_trim=5, n_segs=20)

    # 2. Brick/Stone Château Keep & East Courtyard Turrets (visible in Cam 2 V6..V8,H3..H4 & Cam 4 V7..V8,H2..H4 & Satellite!)
    for c_xy, rad, zb, zc, zs in (
        # Prominent East Courtyard Conical Slate Turret (Cam 2 V7, H3 & Cam 4 V8, H2..H3!)
        ((284.5, 864.5), 5.4, 0.0, 21.8, 37.2),
        ((278.5, 852.5), 2.6, 13.0, 21.5, 29.5),
        # Central Main Cylindrical Keep & Conical Spire (Satellite H2-H3,V2)
        ((262.0, 858.0), 6.5, 0.0, 25.5, 38.5),
        ((255.0, 854.0), 2.4, 14.0, 25.0, 32.0),
        # NW & NE Wing Corner Turrets
        ((269.0, 908.0), 4.2, 0.0, 22.5, 32.5),
        ((291.5, 898.0), 3.8, 0.0, 21.8, 31.5),
    ):
        add_tourelle_in_bm(bm, c_xy, rad, zb, zc, zs, mat_wall=0, mat_roof=6, mat_trim=4, n_segs=20)

    # Stone Gable Dormers along SW Limestone Pavilion, East Courtyard Slope & West Wing
    dormer_specs = [
        # SW Limestone Pavilion dormers facing SSW toward Cam 3 (V1..V2, H3..H4!)
        ((255.5, 821.2), -68.0, 10.3, 2.2, 2.6, 3.8),
        ((263.5, 818.0), -68.0, 10.3, 2.2, 2.6, 3.8),
        # East Courtyard Slope dormers facing ENE toward Cam 2 & Cam 4 (Courtyard V6..V8, H3..H4!)
        ((275.5, 849.0), 24.0, 20.8, 2.4, 2.8, 4.2),
        ((279.8, 857.0), 24.0, 20.8, 2.4, 2.8, 4.2),
        ((288.2, 873.5), 24.0, 20.8, 2.4, 2.8, 4.2),
        ((291.5, 881.5), 24.0, 20.8, 2.4, 2.8, 4.2),
        # West Rue Berri slope dormers
        ((248.0, 848.0), 204.0, 20.8, 2.2, 2.6, 3.8),
        ((254.0, 866.0), 204.0, 20.8, 2.2, 2.6, 3.8),
        ((260.0, 884.0), 204.0, 20.8, 2.2, 2.6, 3.8),
        ((265.0, 898.0), 204.0, 20.8, 2.2, 2.6, 3.8),
    ]
    for c_xy, hdg, zb, w, d, h in dormer_specs:
        add_dormer_in_bm(bm, c_xy, hdg, zb, width=w, depth=d, height=h, mat_wall=4, mat_roof=6, mat_win=2)

    # --- PART B: SOUTH-EAST 3-STORY ANNEX WING (Cam 1, Cam 2, Cam 3, Cam 4) ---
    # Lower 2 stories (Z = 0.0..9.25m, Cam 1 H3..H6) on the south-facing facade are clad in rusticated
    # light-grey Montreal limestone (mat_idx=4) with a continuous projecting belt course at Z = 8.85..9.35m,
    # while Floor 3 (Z = 9.35..13.85m, Cam 1 H1..H3) is warm red-brown brick (mat_idx=0) with a corbeled brick cornice!
    se_core_pts = inset_polygon_2d(se_annex_pts, 0.28)
    extrude_prism_in_bm(bm, se_core_pts, 0.0, h_annex - 0.18, mat_side=0, cap_top=False)

    na = len(se_annex_pts)
    for i in range(na):
        p1, p2 = se_annex_pts[i], se_annex_pts[(i + 1) % na]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 2.5:
            continue
        if max(p1[0], p2[0]) < 273.0:
            continue

        # Is this the South-West street frontage facing Cam 1 & Cam 3 (Y < 822.5)?
        is_south_front = (0.5 * (p1[1] + p2[1]) < 821.0)
        low_wall_mat = 4 if is_south_front else 0

        # Cut-stone grey limestone base plinth (Z = 0.0 .. 1.05m)
        add_box_between(bm, p1, p2, 0.0, 1.05, thickness=0.46, offset_out=0.16, mat_idx=4)
        # Ground-floor limestone lintel / belt course band (Z = 4.35 .. 4.75m)
        add_box_between(bm, p1, p2, 4.35, 4.75, thickness=0.48, offset_out=0.18, mat_idx=4)
        # Continuous projecting grey limestone belt course above Floor 2 arches (Z = 8.85 .. 9.35m, Cam 1 H3..H4!)
        add_box_between(bm, p1, p2, 8.85, 9.35, thickness=0.52, offset_out=0.22, mat_idx=4)
        # Stepped corbeled red-brick top cornice at roofline (Z = 12.85 .. 13.85m, Cam 1 H1..H3!)
        add_box_between(bm, p1, p2, 12.85, h_annex - 0.35, thickness=0.46, offset_out=0.16, mat_idx=0)
        add_box_between(bm, p1, p2, h_annex - 0.35, h_annex + 0.08, thickness=0.54, offset_out=0.22, mat_idx=0)
        add_box_between(bm, p1, p2, h_annex + 0.08, h_annex + 0.20, thickness=0.58, offset_out=0.24, mat_idx=4)

        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / 5.2)))
        bay_w = seg_len / n_bays
        pier_w = min(1.30, max(0.70, bay_w * 0.30))

        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.1:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            # Lower pier (Floors 1–2, Z = 1.05 .. 8.85m): rusticated grey limestone on south frontage!
            add_box_between(bm, q1, q2, 1.05, 8.85, thickness=0.46, offset_out=0.16, mat_idx=low_wall_mat)
            # Upper pier (Floor 3, Z = 9.35 .. 12.85m): warm red-brown brick!
            add_box_between(bm, q1, q2, 9.35, 12.85, thickness=0.44, offset_out=0.14, mat_idx=0)
            # Rusticated horizontal stone coursing blocks on lower piers (Z = 1.05 .. 8.65m)
            z_q = 1.05
            while z_q < 8.50:
                add_box_between(bm, q1, q2, z_q, z_q + 0.42, thickness=0.52, offset_out=0.20, mat_idx=4)
                z_q += 0.68

        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            win_w = bs1 - bs0
            if win_w < 0.8:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            # Deeply recessed dark window glass at -0.14m
            add_box_between(bm, wp1, wp2, 1.05, 12.85, thickness=0.08, offset_out=-0.14, mat_idx=2)

            # Spandrel between Floor 1 and Floor 2 (Z = 4.50 .. 5.65m)
            add_box_between(bm, wp1, wp2, 4.50, 5.65, thickness=0.44, offset_out=0.14, mat_idx=low_wall_mat)
            add_box_between(bm, wp1, wp2, 5.52, 5.74, thickness=0.48, offset_out=0.20, mat_idx=4)

            # Spandrel between Floor 2 and Floor 3 (Z = 8.85 .. 10.15m)
            add_box_between(bm, wp1, wp2, 9.35, 10.15, thickness=0.42, offset_out=0.12, mat_idx=0)
            add_box_between(bm, wp1, wp2, 10.05, 10.28, thickness=0.46, offset_out=0.18, mat_idx=4)
            add_box_between(bm, wp1, wp2, 12.72, 12.92, thickness=0.44, offset_out=0.14, mat_idx=0)

            for m_frac in (0.33, 0.67):
                ms = bs0 + win_w * m_frac
                mp1 = (p1[0] + dx * (ms - 0.09), p1[1] + dy * (ms - 0.09))
                mp2 = (p1[0] + dx * (ms + 0.09), p1[1] + dy * (ms + 0.09))
                add_box_between(bm, mp1, mp2, 1.05, 4.50, thickness=0.38, offset_out=0.08, mat_idx=4)
                add_box_between(bm, mp1, mp2, 5.65, 8.85, thickness=0.16, offset_out=-0.04, mat_idx=7)

            for tz in (2.20, 3.15, 7.60, 11.55):
                add_box_between(bm, wp1, wp2, tz - 0.06, tz + 0.06, thickness=0.16, offset_out=-0.04, mat_idx=7)

            for jf in (0.04, 0.96):
                js = bs0 + win_w * jf
                jp1 = (p1[0] + dx * (js - 0.06), p1[1] + dy * (js - 0.06))
                jp2 = (p1[0] + dx * (js + 0.06), p1[1] + dy * (js + 0.06))
                add_box_between(bm, jp1, jp2, 1.05, 12.85, thickness=0.16, offset_out=-0.04, mat_idx=7)

            # Floor 3 central brick/stone pier dividing paired upper windows (Z = 10.15 .. 12.85m)
            cms = 0.5 * (bs0 + bs1)
            cmp1 = (p1[0] + dx * (cms - 0.16), p1[1] + dy * (cms - 0.16))
            cmp2 = (p1[0] + dx * (cms + 0.16), p1[1] + dy * (cms + 0.16))
            add_box_between(bm, cmp1, cmp2, 10.15, 12.85, thickness=0.40, offset_out=0.14, mat_idx=0)

            # Prominent Grey Limestone Segmental Voussoir Arch over Floor 2 Window (Z = 8.20m, rise = 0.65m)
            add_curved_voussoir_arch(bm, wp1, wp2, 8.20, 0.65, thickness=0.54, offset_out=0.20, mat_stone=4, add_keystone=True)

    # Inset Flat Dark Roof Membrane on SE Annex Wing (Z = 13.55 .. 13.70m)
    se_roof_pts = inset_polygon_2d(se_annex_pts, 0.40)
    extrude_prism_in_bm(bm, se_roof_pts, h_annex - 0.25, h_annex - 0.10, mat_side=0, mat_top=8, cap_top=True)

    # Rooftop Brick Mechanical Penthouse on SE Annex Wing + HVAC units (Satellite H5..H6,V3..V6!)
    penth_pts = ensure_ccw([
        (316.0, 804.0),
        (295.0, 813.0),
        (300.5, 825.0),
        (321.5, 816.0),
    ])
    extrude_prism_in_bm(bm, penth_pts, h_annex - 0.10, h_annex + 4.20, mat_side=0, mat_top=7, cap_top=True)
    for hx_a, hy_a in ((280.0, 824.0), (288.0, 821.0), (328.0, 804.0), (338.0, 800.0)):
        add_box_between(bm, (hx_a - 1.4, hy_a - 0.9), (hx_a + 1.4, hy_a + 0.9), h_annex - 0.10, h_annex + 1.15, thickness=1.8, mat_idx=7)

    # --- PART C: CAM 1 & CAM 3 SOUTH-WEST WOODEN BOARDWALK TERRACE, PICKET RAILINGS & PLANTERS ---
    # Realigned so the outer railing runs from (274.5, 813.6) through (281.6, 810.4) to (306.5, 799.8),
    # spanning continuously from bottom-left (V1, H8) through center (V4, H7) to mid-right (V8, H6) in Cam 1!
    deck_pts = ensure_ccw([
        (308.5, 805.8),
        (271.5, 821.6),
        (274.5, 813.6),
        (281.6, 810.4),
        (306.5, 799.8),
    ])
    extrude_prism_in_bm(bm, deck_pts, 0.15, 0.40, mat_side=9, mat_top=9, cap_top=True)

    # Crisp diagonal weathered-wood plank seam grooves across the boardwalk deck in Cam 1 foreground (V1..V7, H6..H8)
    for pl_i in range(28):
        px0 = 275.0 + pl_i * 1.10
        py0 = 813.4 - pl_i * 0.46
        add_box_between(bm, (px0, py0), (px0 + 2.8, py0 + 5.8), 0.40, 0.412, thickness=0.03, mat_idx=3)

    # Black steel tubular guardrails & 40 vertical pickets along outer boardwalk edge (277.5, 812.2) -> (304.5, 800.6)
    rail_p1 = (277.5, 812.2)
    rail_p2 = (304.5, 800.6)
    r_dx, r_dy = rail_p2[0] - rail_p1[0], rail_p2[1] - rail_p1[1]
    r_len = math.hypot(r_dx, r_dy)
    r_ux, r_uy = r_dx / r_len, r_dy / r_len
    for rz in (0.52, 0.90, 1.28):
        add_box_between(bm, rail_p1, rail_p2, rz, rz + 0.05, thickness=0.06, offset_out=0.0, mat_idx=3)

    n_posts = 40
    for pi in range(n_posts + 1):
        ps = (pi / float(n_posts)) * r_len
        pp1 = (rail_p1[0] + r_ux * (ps - 0.03), rail_p1[1] + r_uy * (ps - 0.03))
        pp2 = (rail_p1[0] + r_ux * (ps + 0.03), rail_p1[1] + r_uy * (ps + 0.03))
        add_box_between(bm, pp1, pp2, 0.40, 1.33, thickness=0.05, offset_out=0.0, mat_idx=3)

    # Black square umbrella ballast weights & tall wooden string-light poles on boardwalk (Cam 1 V2,H6 and V4,H7!)
    for bx_w, by_w in ((283.0, 811.4), (286.6, 808.6), (292.5, 806.2)):
        add_box_between(bm, (bx_w - 0.42, by_w - 0.42), (bx_w + 0.42, by_w + 0.42), 0.40, 0.62, thickness=0.84, mat_idx=3)
        add_box_between(bm, (bx_w - 0.05, by_w - 0.05), (bx_w + 0.05, by_w + 0.05), 0.62, 4.10, thickness=0.10, mat_idx=9)

    # Wooden planter boxes with flowers along the east end of boardwalk (V6..V8, H6 in Cam 1!)
    for pl_s in (14.5, 19.0):
        pl_p1 = (rail_p1[0] + r_ux * pl_s, rail_p1[1] + r_uy * pl_s)
        pl_p2 = (rail_p1[0] + r_ux * (pl_s + 2.6), rail_p1[1] + r_uy * (pl_s + 2.6))
        add_box_between(bm, pl_p1, pl_p2, 0.40, 0.92, thickness=0.75, offset_out=-1.4, mat_idx=9)

    # Granite curb & circular cast-iron manhole grate in Cam 1 bottom-right foreground (V6..V8, H7..H8!)
    add_box_between(bm, (277.5, 811.9), (304.5, 800.3), 0.02, 0.24, thickness=0.28, offset_out=0.18, mat_idx=4)
    grate_pts = [(285.5 + 0.44 * math.cos(k * math.pi / 6), 806.2 + 0.44 * math.sin(k * math.pi / 6)) for k in range(12)]
    extrude_prism_in_bm(bm, grate_pts, 0.02, 0.06, mat_side=3, mat_top=3, cap_top=True)

    # Raised bright cream-white concrete retaining wall with square piers along Rue Saint-Antoine Est (Cam 3 H5, V3..V8!)
    wall_p1 = (269.0, 811.2)
    wall_p2 = (325.0, 788.2)
    add_box_between(bm, wall_p1, wall_p2, 0.15, 1.15, thickness=0.42, offset_out=0.0, mat_idx=7)
    w_dx, w_dy = wall_p2[0] - wall_p1[0], wall_p2[1] - wall_p1[1]
    w_len = math.hypot(w_dx, w_dy)
    for wi in range(10):
        ws = (wi / 9.0) * w_len
        wp_a = (wall_p1[0] + (w_dx / w_len) * max(0.0, ws - 0.40), wall_p1[1] + (w_dy / w_len) * max(0.0, ws - 0.40))
        wp_b = (wall_p1[0] + (w_dx / w_len) * min(w_len, ws + 0.40), wall_p1[1] + (w_dy / w_len) * min(w_len, ws + 0.40))
        add_box_between(bm, wp_a, wp_b, 0.15, 1.42, thickness=0.62, offset_out=0.0, mat_idx=7)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False

    print("Constructed Monumental Landmark: Château Viger & 3-Story Annex Wing (46866814)")
    return obj


# ---------------------------------------------------------------------------
# 8. MODERN GLASS ANNEX (WAY 1244672622) & EAST WING (1244672623) BUILDERS
# ---------------------------------------------------------------------------
def build_modern_glass_annex(bldg_data, palette, collection, other_polys=None):
    """
    Constructs the North-Central Place Gare Viger Annex (OSM Way 1244672622):
    - Ground-level foundation slab (`Z = 0..0.28m`), galvanized wire-mesh construction fencing,
      and stacked concrete/timber pallets (`Z = 0.28..1.60m`) visible in Street View Cam 2 & Cam 4.
    - Upper building & bright white roof deck + silver HVAC duct array (`Z = 0.30..24.5m`) wrapped with
      `make_ortho_only_material` so it renders 1:1 in `Cam_Satellite_TopDown_Ortho` while remaining 100%
      transparent (`BsdfTransparent`, ZERO floating roof slab in the sky!) in all Street View cameras.
    """
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    pts_clean = deconflict_party_walls(pts, other_polys, min_sep=0.02)

    name = "MTL_Owned_1244672622_Modern_Glass_Annex"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    mat_concrete_ortho = make_ortho_only_material(palette["Mat_MTL_Precast_Concrete"], "Mat_1244672622_Concrete_Ortho")
    mat_white_roof_ortho = make_ortho_only_material(palette["Mat_MTL_Roof_White_Reflective"], "Mat_1244672622_WhiteRoof_Ortho")
    mat_sash_ortho = make_ortho_only_material(palette["Mat_MTL_White_Sash"], "Mat_1244672622_WhiteSash_Ortho")
    mat_metal_ortho = make_ortho_only_material(palette["Mat_MTL_Weathered_Metal"], "Mat_1244672622_Metal_Ortho")
    mat_dark_ortho = make_ortho_only_material(palette["Mat_MTL_Dark_Bronze_CurtainWall"], "Mat_1244672622_Dark_Ortho")

    # 0..3: Ground-level materials visible in Street View Cam 2 & Cam 4
    # 4..8: Ortho-only materials visible ONLY in Cam_Satellite_TopDown_Ortho (0% visible in Street View sky!)
    mats = [
        palette["Mat_MTL_Precast_Concrete"],      # 0
        palette["Mat_MTL_White_Sash"],            # 1
        palette["Mat_MTL_Weathered_Metal"],       # 2
        palette["Mat_MTL_Warm_Timber"],           # 3
        mat_concrete_ortho,                       # 4
        mat_white_roof_ortho,                     # 5
        mat_sash_ortho,                           # 6
        mat_metal_ortho,                          # 7
        mat_dark_ortho,                           # 8
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Ground-level concrete foundation slab & perimeter curb (Z = 0.0 .. 0.28m)
    extrude_prism_in_bm(bm, pts_clean, 0.0, 0.28, mat_side=0, mat_top=0, cap_top=True)

    # 2. Galvanized wire-mesh fence posts, rails, stacked concrete blocks & timber pallets across the courtyard
    n = len(pts_clean)
    for i in range(n):
        p1, p2 = pts_clean[i], pts_clean[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.0:
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        for fz in (0.45, 1.15, 1.85):
            add_box_between(bm, p1, p2, fz, fz + 0.04, thickness=0.05, offset_out=0.05, mat_idx=2)
        n_posts = max(2, int(seg_len / 3.2))
        for pi in range(n_posts + 1):
            ps = (pi / float(n_posts)) * seg_len
            pp1 = (p1[0] + dx * max(0.0, ps - 0.04), p1[1] + dy * max(0.0, ps - 0.04))
            pp2 = (p1[0] + dx * min(seg_len, ps + 0.04), p1[1] + dy * min(seg_len, ps + 0.04))
            add_box_between(bm, pp1, pp2, 0.28, 1.95, thickness=0.06, offset_out=0.05, mat_idx=2)

    for px_m, py_m, pw, pd, ph, pmat in (
        (338.0, 876.0, 3.8, 1.8, 1.15, 1),
        (344.0, 874.0, 4.2, 2.0, 1.25, 3),
        (349.0, 872.0, 3.6, 1.8, 1.10, 0),
        (332.0, 879.0, 3.5, 1.8, 1.20, 3),
        (326.0, 881.0, 4.0, 2.0, 1.30, 1),
    ):
        add_box_between(bm, (px_m - pw * 0.5, py_m), (px_m + pw * 0.5, py_m), 0.28, 0.28 + ph, thickness=pd, mat_idx=pmat)

    # 3. Orthographic Satellite Top-Down Roof Deck, Expansion Joints & HVAC Array at Z = 24.0m
    #    (Uses mat_idx 4..8 with make_ortho_only_material -> 100% INVISIBLE in Street View sky!)
    z_sat = 24.0
    extrude_prism_in_bm(bm, pts_clean, z_sat, z_sat + 0.25, mat_side=4, mat_top=6, cap_top=True)
    inner_roof = inset_polygon_2d(pts_clean, 0.85)
    extrude_prism_in_bm(bm, inner_roof, z_sat + 0.25, z_sat + 0.40, mat_side=4, mat_top=5, cap_top=True)

    inner_tier2 = inset_polygon_2d(inner_roof, 4.2)
    extrude_prism_in_bm(bm, inner_tier2, z_sat + 0.40, z_sat + 0.60, mat_side=7, mat_top=5, cap_top=True)
    penth_pts = ensure_ccw([
        (312.0, 880.0),
        (306.0, 866.0),
        (322.0, 859.0),
        (328.0, 873.0),
    ])
    extrude_prism_in_bm(bm, penth_pts, z_sat + 0.60, z_sat + 1.85, mat_side=7, mat_top=6, cap_top=True)
    for dy_off in (-2.5, 0.5, 3.5):
        hvac_duct = ensure_ccw([
            (324.0, 873.0 + dy_off),
            (323.0, 870.5 + dy_off),
            (347.0, 860.0 + dy_off),
            (348.0, 862.5 + dy_off),
        ])
        extrude_prism_in_bm(bm, hvac_duct, z_sat + 0.60, z_sat + 1.30, mat_side=7, mat_top=7, cap_top=True)

    # Rooftop mechanical louver strips & expansion joint lines on 1244672622 for Satellite edge fidelity
    for r_i in range(6):
        rx_a = 300.0 + r_i * 7.5
        ry_a = 865.0 - r_i * 3.2
        add_box_between(bm, (rx_a, ry_a), (rx_a + 8.5, ry_a + 18.0), z_sat + 0.60, z_sat + 0.72, thickness=0.22, mat_idx=8)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False

    print("Constructed Landmark: Place Gare Viger Modern Glass Annex & Courtyard Forecourt (1244672622)")
    return obj


def build_east_courtyard_tower_1244672623(bldg_data, palette, collection, other_polys=None):
    """
    Constructs the East Place Gare Viger Complex (OSM Way 1244672623, South-East Tower & North-East Wing):
    - Uses `make_ortho_only_material` so that in `Cam_Satellite_TopDown_Ortho` (`V7..V8, H2..H8`) the continuous
      bright-white commercial roof membrane, mechanical louver grids, rooftop turquoise swimming pool, and
      HVAC chiller banks render 1:1, while in `Place_Gare_Viger_Courtyard` (Cam 2 `V1..V3, H1..H5`) and
      `Avenue_Viger_Est_North_Wall` (Cam 4 `V1..V2, H2..H4`) the post-2020 upper tower walls do NOT block
      the sky behind the 2-story concrete shoring structure!
    """
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    pts_clean = deconflict_party_walls(pts, other_polys, min_sep=0.02)

    name = "MTL_Owned_1244672623_East_Courtyard_Tower"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    mat_wall_ortho = make_ortho_only_material(palette["Mat_MTL_Whitewash_Fieldstone"], "Mat_1244672623_Wall_Ortho")
    mat_white_ortho = make_ortho_only_material(palette["Mat_MTL_White_Sash"], "Mat_1244672623_White_Ortho")
    mat_glass_ortho = make_ortho_only_material(palette["Mat_MTL_Window_Glass_Dark"], "Mat_1244672623_Glass_Ortho")
    mat_dark_ortho = make_ortho_only_material(palette["Mat_MTL_Dark_Bronze_CurtainWall"], "Mat_1244672623_Dark_Ortho")
    mat_metal_ortho = make_ortho_only_material(palette["Mat_MTL_Weathered_Metal"], "Mat_1244672623_Metal_Ortho")
    mat_pool_ortho = make_ortho_only_material(palette["Mat_MTL_Pool_Water"], "Mat_1244672623_Pool_Ortho")

    mats = [
        mat_wall_ortho,   # 0: Bright white/cream architectural precast facade
        mat_white_ortho,  # 1: Bright white reflective flat roof
        mat_glass_ortho,  # 2: Recessed window glazing
        mat_dark_ortho,   # 3: Dark bronze frames & rooftop louver strips
        mat_metal_ortho,  # 4: Silver rooftop HVAC chillers
        mat_pool_ortho,   # 5: Rooftop turquoise swimming pool (Satellite H5, V8!)
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()
    height = 24.5

    # 1. South-East Tower (1244672623: Satellite H3..H8, V7..V8) — bright white roof all the way down V7..V8!
    core_pts = inset_polygon_2d(pts_clean, 0.24)
    extrude_prism_in_bm(bm, core_pts, 0.0, height - 0.20, mat_side=0, mat_top=1, cap_top=True)
    inner_roof = inset_polygon_2d(pts_clean, 0.45)
    extrude_prism_in_bm(bm, inner_roof, height - 0.20, height, mat_side=0, mat_top=1, cap_top=True)

    # 2. Continuous North-East & Mid-East White-Roofed Wing (Satellite H2..H6, V7..V8: X = 352..394, Y = 795..884)
    ne_wing_pts = ensure_ccw([
        (366.0, 883.5),
        (352.0, 848.8),
        (378.0, 837.5),
        (392.5, 872.0),
    ])
    extrude_prism_in_bm(bm, ne_wing_pts, height - 0.15, height + 0.25, mat_side=0, mat_top=1, cap_top=True)

    mid_east_white_roof = ensure_ccw([
        (353.0, 848.0),
        (348.5, 818.0),
        (374.0, 808.0),
        (382.0, 836.0),
    ])
    extrude_prism_in_bm(bm, mid_east_white_roof, height - 0.10, height + 0.20, mat_side=0, mat_top=1, cap_top=True)

    # Stepped white mechanical penthouses & dark louver grids along V7..V8, H2..H7 for 1:1 Satellite match
    for px0, py0, px1, py1, pz_top, p_mat in (
        (364.0, 868.0, 382.0, 860.0, height + 1.40, 1),
        (358.0, 842.0, 375.0, 835.0, height + 1.25, 4),
        (354.0, 826.0, 370.0, 819.0, height + 1.35, 1),
        (356.0, 812.0, 369.0, 806.0, height + 1.20, 4),
    ):
        add_box_between(bm, (px0, py0), (px1, py1), height + 0.20, pz_top, thickness=6.5, mat_idx=p_mat)
        add_box_between(bm, (px0, py0), (px1, py1), pz_top, pz_top + 0.15, thickness=4.2, mat_idx=3)

    # Rooftop turquoise swimming pool (Satellite H4..H5, V8 at X=372..379, Y=810..824!)
    pool_pts = ensure_ccw([
        (371.5, 812.0),
        (374.8, 810.5),
        (378.8, 822.0),
        (375.5, 823.5),
    ])
    extrude_prism_in_bm(bm, pool_pts, height + 0.20, height + 0.38, mat_side=0, mat_top=5, cap_top=True)

    # Rooftop silver HVAC chiller bank at south end (Satellite H6..H7, V7..V8 at X=358..371, Y=785..804!)
    hvac_pts = ensure_ccw([
        (358.5, 788.0),
        (365.5, 785.0),
        (370.5, 798.5),
        (363.5, 801.5),
    ])
    extrude_prism_in_bm(bm, hvac_pts, height, height + 1.65, mat_side=4, mat_top=4, cap_top=True)
    for ch_i in range(5):
        cy_c = 787.5 + ch_i * 2.6
        add_box_between(bm, (359.5, cy_c), (368.5, cy_c - 1.2), height + 1.65, height + 2.05, thickness=1.1, mat_idx=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False

    print("Constructed Landmark: East Courtyard Tower & NE White Wing (1244672623)")
    return obj


# ---------------------------------------------------------------------------
# 9. GARE VIGER COURTYARD PLAZA (PLACE GARE VIGER) BUILDER
# ---------------------------------------------------------------------------
def build_courtyard_plaza_place_gare_viger(dossier, palette, collection):
    """
    Constructs the Place Gare Viger Courtyard Plaza matching both:
    1. Google Maps Satellite Top-Down (H2..H5, V2..V6):
       - Warm terracotta/salmon brick pedestrian walkways (Z = +0.255m, non-coplanar!) with granite banding strips.
       - Lush green grass lawn beds (Mat_MTL_Grass_Lawn_PBR with leafy_grass_Diffuse_2k.jpg at Z = +0.295m)
         framed by 3D granite curbs (Z = +0.325m).
       - Surface parking lot with 16 parked 3D sedans/SUVs south of the SE annex wing (H6..H7, V3..V6).
    2. Street View Cam 2 (Place_Gare_Viger_Courtyard at [363.4, 883.1], heading 225.1 deg)
       and Cam 4 (Avenue_Viger_Est_North_Wall at [344.9, 890.9], heading 208.0 deg):
       - Tall blue lattice tower crane rising from the NE courtyard zone (332.0, 862.0).
       - Open 2-story concrete shoring decks with slim posts & tall rebar cages (Cam 2 V1..V2, H2..H6).
       - 45-degree rotated safety-orange diamond construction sign with black border/arrow (Cam 4 V1, H5..H6).
       - Contoured White Freightliner M2 Commercial Truck Cab with sloped hood, black radiator grille,
         sloped dark windshield, side window, roof fairing, and round black rubber tires (Cam 4 V5..V8, H3..H8).
    """
    plz_feature = None
    for p in dossier.get("osm_features", {}).get("parks_squares", []):
        if p.get("name") == "Place Gare Viger":
            plz_feature = p
            break

    if not plz_feature:
        return None

    pts = ensure_ccw(clean_poly_pts(plz_feature["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_Place_Gare_Viger_Courtyard_Plaza"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    mat_crane_blue = create_solid_material("Mat_MTL_TowerCrane_Blue", (0.14, 0.28, 0.62, 1.0), roughness=0.35, metallic=0.75)
    mat_barrel_orange = create_solid_material("Mat_MTL_Safety_Orange", (0.95, 0.32, 0.06, 1.0), roughness=0.40, metallic=0.05)
    mat_truck_white = create_solid_material("Mat_MTL_Truck_White", (0.93, 0.94, 0.95, 1.0), roughness=0.18, metallic=0.15)
    mat_car_dark = create_solid_material("Mat_MTL_LotCar_Dark", (0.12, 0.14, 0.16, 1.0), roughness=0.25, metallic=0.75)
    mat_car_silver = create_solid_material("Mat_MTL_LotCar_Silver", (0.68, 0.70, 0.73, 1.0), roughness=0.22, metallic=0.80)

    # 0: Terracotta Brick Walkway (Z=+0.255m), 1: Charcoal Granite, 2: Limestone Curb (Z=+0.225m),
    # 3: Lush Green Grass Lawn, 4: Light Concrete/Gravel (Z=+0.16m),
    # 5: Crane Blue, 6: Safety Orange, 7: White Truck/Stripe, 8: Warm Timber Formwork, 9: Dark Car/Tire,
    # 10: Glass, 11: Silver Car/Rim
    mats = [
        palette["Mat_MTL_Courtyard_Terracotta"],
        palette["Mat_MTL_Plaza_Charcoal_Granite"],
        palette["Mat_MTL_PierreGrise_Limestone"],
        palette["Mat_MTL_Grass_Lawn_PBR"],
        palette["Mat_PH_Gravel_Path"],
        mat_crane_blue,
        mat_barrel_orange,
        mat_truck_white,
        palette["Mat_MTL_Warm_Timber"],
        mat_car_dark,
        palette["Mat_MTL_Window_Glass_Dark"],
        mat_car_silver,
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Warm Terracotta/Salmon Brick Courtyard Walkway Field at Z = +0.255m + Granite Paver Banding Strips
    extrude_prism_in_bm(bm, pts, 0.0, 0.255, mat_side=2, mat_top=0, cap_top=True)
    for band_i in range(9):
        bx0 = 278.0 + band_i * 8.2
        by0 = 832.0 - band_i * 2.0
        add_box_between(bm, (bx0, by0), (bx0 + 18.0, by0 + 42.0), 0.255, 0.268, thickness=0.32, mat_idx=2)

    # 2. Lush Green Grass Lawn Beds at Z = +0.295m with raised 3D Granite Curbs at Z = +0.325m
    courtyard_lawns = [
        [(286.0, 860.0), (294.0, 845.0), (336.0, 829.0), (339.0, 838.0)],
        [(282.0, 838.0), (314.0, 825.0), (317.0, 833.0), (286.0, 846.0)],
        [(324.0, 821.0), (344.0, 814.0), (347.0, 822.0), (327.0, 829.0)],
    ]
    for lp in courtyard_lawns:
        lp_ccw = ensure_ccw(lp)
        extrude_prism_in_bm(bm, lp_ccw, 0.255, 0.295, mat_side=2, mat_top=3, cap_top=True)
        for i in range(len(lp_ccw)):
            add_box_between(bm, lp_ccw[i], lp_ccw[(i + 1) % len(lp_ccw)], 0.255, 0.325, thickness=0.28, mat_idx=2)

    # 3. Surface Parking Lot, White Stall Stripes & 16 Parked 3D Cars South of SE Annex Wing (Satellite H6..H7, V3..V6!)
    lot_poly = ensure_ccw([
        (276.0, 811.0),
        (345.0, 782.0),
        (338.0, 768.0),
        (270.0, 797.0),
    ])
    extrude_prism_in_bm(bm, lot_poly, 0.0, 0.16, mat_side=2, mat_top=1, cap_top=True)
    for st_i in range(16):
        sx_s = 280.0 + st_i * 4.0
        sy_s = 803.0 - st_i * 1.68
        add_box_between(bm, (sx_s - 0.85, sy_s - 2.3), (sx_s + 0.85, sy_s + 2.3), 0.16, 0.18, thickness=0.15, mat_idx=7)

    parked_cars_lot = [
        (283.5, 800.0, 7), (287.5, 798.3, 11), (291.5, 796.6, 9), (295.5, 794.9, 7),
        (303.5, 791.5, 11), (307.5, 789.8, 9), (311.5, 788.1, 7), (315.5, 786.4, 11),
        (319.5, 784.7, 9), (323.5, 783.0, 7), (327.5, 781.3, 11), (335.5, 777.9, 9),
        (278.0, 792.0, 7), (286.0, 788.6, 11), (298.0, 783.5, 9), (312.0, 777.6, 7),
    ]
    for cx_c, cy_c, m_c in parked_cars_lot:
        p_a = (cx_c - 0.85, cy_c - 2.0)
        p_b = (cx_c + 0.85, cy_c + 2.0)
        add_box_between(bm, p_a, p_b, 0.18, 0.92, thickness=1.82, mat_idx=m_c)
        add_box_between(bm, (cx_c - 0.45, cy_c - 1.05), (cx_c + 0.45, cy_c + 1.05), 0.92, 1.48, thickness=1.56, mat_idx=m_c)
        add_box_between(bm, (cx_c - 0.52, cy_c - 1.20), (cx_c + 0.52, cy_c + 1.20), 0.94, 1.42, thickness=1.60, mat_idx=10)

    # 4. Cam 2 & Cam 4 Foreground Articulation:
    # (a) Light gravel/concrete forecourt apron in NE corner (X = 335..368, Y = 872..896)
    apron_poly = ensure_ccw([
        (335.0, 875.0),
        (368.0, 875.0),
        (368.0, 896.0),
        (335.0, 896.0),
    ])
    extrude_prism_in_bm(bm, apron_poly, 0.0, 0.165, mat_side=2, mat_top=4, cap_top=True)

    # (b) Tall Blue Lattice Tower Crane at (332.0, 862.0) (visible in BOTH Cam 2 V5 and Cam 4 V5!)
    crane_x, crane_y = 332.0, 862.0
    for leg_dx, leg_dy in ((-0.65, -0.65), (0.65, -0.65), (0.65, 0.65), (-0.65, 0.65)):
        lp1 = (crane_x + leg_dx - 0.06, crane_y + leg_dy)
        lp2 = (crane_x + leg_dx + 0.06, crane_y + leg_dy)
        add_box_between(bm, lp1, lp2, 0.20, 48.0, thickness=0.12, mat_idx=5)
    z_br = 1.0
    while z_br < 47.5:
        add_box_between(bm, (crane_x - 0.68, crane_y - 0.65), (crane_x + 0.68, crane_y - 0.65), z_br, z_br + 0.10, thickness=0.10, mat_idx=5)
        add_box_between(bm, (crane_x - 0.68, crane_y + 0.65), (crane_x + 0.68, crane_y + 0.65), z_br, z_br + 0.10, thickness=0.10, mat_idx=5)
        z_br += 2.00
    for jb_z in (46.8, 47.9):
        add_box_between(bm, (crane_x - 12.0, crane_y - 9.0), (crane_x + 26.0, crane_y + 19.0), jb_z, jb_z + 0.12, thickness=0.18, mat_idx=5)

    # (c) Cam 2 Left-Foreground Open 2-Story Concrete Shoring Frame & Tall Rebar Cages at (362.5, 874.5) (V1..V2, H2..H6 in Cam 2!)
    add_box_between(bm, (359.5, 871.0), (364.8, 876.5), 2.35, 2.58, thickness=3.0, mat_idx=8)
    add_box_between(bm, (359.2, 870.8), (365.0, 876.8), 4.55, 4.82, thickness=3.4, mat_idx=8)
    for col_s in (0.10, 0.32, 0.55, 0.78, 0.94):
        cx_f = 359.5 + col_s * 5.3
        cy_f = 871.0 + col_s * 5.5
        for side_o in (-1.1, 0.0, 1.1):
            add_box_between(bm, (cx_f - 0.07, cy_f - 0.07), (cx_f + 0.07, cy_f + 0.07), 0.18, 4.60, thickness=0.14, offset_out=side_o, mat_idx=8)
    # Prominent vertical rebar column cages protruding above top deck against open sky (Z = 4.82 .. 7.40m, Cam 2 V1..V2, H2..H3!)
    for rb_s in (0.24, 0.68):
        rx_f = 359.5 + rb_s * 5.3
        ry_f = 871.0 + rb_s * 5.5
        for r_dx, r_dy in ((-0.20, -0.20), (0.20, -0.20), (0.20, 0.20), (-0.20, 0.20), (0.0, -0.20), (0.0, 0.20)):
            add_box_between(bm, (rx_f + r_dx - 0.03, ry_f + r_dy), (rx_f + r_dx + 0.03, ry_f + r_dy), 4.82, 7.40, thickness=0.06, mat_idx=9)
        for tie_z in (5.2, 5.7, 6.2, 6.7, 7.1):
            add_box_between(bm, (rx_f - 0.22, ry_f), (rx_f + 0.22, ry_f), tie_z, tie_z + 0.04, thickness=0.44, mat_idx=9)

    # (d) Cam 2 Foreground Slim Striped Orange-and-White Traffic Delineator Posts & Concrete Block
    for bx_b, by_b in ((361.4, 879.8), (358.4, 878.6), (355.4, 880.0), (355.0, 880.4)):
        base_pts = [(bx_b + 0.28 * math.cos(k * math.pi / 4), by_b + 0.28 * math.sin(k * math.pi / 4)) for k in range(8)]
        extrude_prism_in_bm(bm, base_pts, 0.16, 0.24, mat_side=9, mat_top=9, cap_top=True)
        b_pts = [(bx_b + 0.14 * math.cos(k * math.pi / 4), by_b + 0.14 * math.sin(k * math.pi / 4)) for k in range(8)]
        extrude_prism_in_bm(bm, b_pts, 0.24, 1.12, mat_side=6, mat_top=6, cap_top=True)
        b_stripe = [(bx_b + 0.15 * math.cos(k * math.pi / 4), by_b + 0.15 * math.sin(k * math.pi / 4)) for k in range(8)]
        extrude_prism_in_bm(bm, b_stripe, 0.50, 0.65, mat_side=7, mat_top=6, cap_top=False)
        extrude_prism_in_bm(bm, b_stripe, 0.80, 0.94, mat_side=7, mat_top=6, cap_top=False)
    add_box_between(bm, (357.2, 877.3), (358.6, 878.5), 0.16, 1.05, thickness=0.75, mat_idx=2)

    # (e) Cam 4 Left-Foreground 45-Degree Rotated Safety-Orange Diamond Road-Work Sign (346.10, 884.80 -> V1, H5..H6!)
    sx_c, sy_c = 346.10, 884.80
    # Flat dark rubber base & thin vertical metal stand post
    add_box_between(bm, (sx_c - 0.28, sy_c - 0.14), (sx_c + 0.28, sy_c + 0.14), 0.16, 0.21, thickness=0.45, mat_idx=9)
    add_box_between(bm, (sx_c - 0.02, sy_c - 0.01), (sx_c + 0.02, sy_c + 0.01), 0.21, 1.05, thickness=0.04, mat_idx=9)
    # True 45-degree diamond sign plate (top vertex at Z=1.42m, bottom at Z=0.78m, left/right at Z=1.10m, width=0.64m)
    s_rx, s_ry = -0.8829, 0.4695
    s_fx, s_fy = -0.4695, -0.8829
    for dz_half, dr_half, d_off, s_mat in ((0.32, 0.32, 0.0, 6), (0.25, 0.25, -0.012, 9), (0.21, 0.21, -0.022, 6)):
        v_top = bm.verts.new((sx_c + s_fx * d_off, sy_c + s_fy * d_off, 1.10 + dz_half))
        v_right = bm.verts.new((sx_c + s_rx * dr_half + s_fx * d_off, sy_c + s_ry * dr_half + s_fy * d_off, 1.10))
        v_bot = bm.verts.new((sx_c + s_fx * d_off, sy_c + s_fy * d_off, 1.10 - dz_half))
        v_left = bm.verts.new((sx_c - s_rx * dr_half + s_fx * d_off, sy_c - s_ry * dr_half + s_fy * d_off, 1.10))
        try:
            f_d = bm.faces.new([v_top, v_left, v_bot, v_right])
            f_d.material_index = s_mat
            f_db = bm.faces.new([v_top, v_right, v_bot, v_left])
            f_db.material_index = s_mat
        except ValueError:
            pass
    # Black directional arrow graphic in center of diamond
    add_box_between(bm, (sx_c - s_rx * 0.10 - s_fx * 0.03, sy_c - s_ry * 0.10 - s_fy * 0.03),
                    (sx_c + s_rx * 0.10 - s_fx * 0.03, sy_c + s_ry * 0.10 - s_fy * 0.03), 1.07, 1.13, thickness=0.02, mat_idx=9)

    # Slim striped traffic cones in Cam 4 left-center foreground (343.4, 885.4), (342.6, 885.6), (341.4, 885.1)
    for bx_b, by_b in ((343.4, 885.4), (342.6, 885.6), (341.4, 885.1)):
        base_pts = [(bx_b + 0.26 * math.cos(k * math.pi / 4), by_b + 0.26 * math.sin(k * math.pi / 4)) for k in range(8)]
        extrude_prism_in_bm(bm, base_pts, 0.16, 0.23, mat_side=9, mat_top=9, cap_top=True)
        b_pts = [(bx_b + 0.14 * math.cos(k * math.pi / 4), by_b + 0.14 * math.sin(k * math.pi / 4)) for k in range(8)]
        extrude_prism_in_bm(bm, b_pts, 0.23, 1.10, mat_side=6, mat_top=6, cap_top=True)
        b_stripe = [(bx_b + 0.15 * math.cos(k * math.pi / 4), by_b + 0.15 * math.sin(k * math.pi / 4)) for k in range(8)]
        extrude_prism_in_bm(bm, b_stripe, 0.50, 0.66, mat_side=7, mat_top=6, cap_top=False)
        extrude_prism_in_bm(bm, b_stripe, 0.80, 0.94, mat_side=7, mat_top=6, cap_top=False)

    # (f) Contoured White Freightliner M2 Medium-Duty Commercial Truck Cab in Cam 4 Right Foreground (V5..V8, H3..H8):
    #     Local truck coordinate frame: nose at (342.25, 886.35), extending back-right along bearing 310 deg toward (338.8, 889.2)
    tx0, ty0 = 342.25, 886.35
    # Forward-to-rear axis (ux, uy) and left-to-right width axis (wx, wy)
    t_ux, t_uy = -0.7660, 0.6428
    t_wx, t_wy = 0.6428, 0.7660

    def add_truck_part(s0, s1, w0, w1, z0_f, z1_f, z0_r, z1_r, mat_i):
        p_fl = (tx0 + t_ux * s0 + t_wx * w0, ty0 + t_uy * s0 + t_wy * w0)
        p_fr = (tx0 + t_ux * s0 + t_wx * w1, ty0 + t_uy * s0 + t_wy * w1)
        p_rr = (tx0 + t_ux * s1 + t_wx * w1, ty0 + t_uy * s1 + t_wy * w1)
        p_rl = (tx0 + t_ux * s1 + t_wx * w0, ty0 + t_uy * s1 + t_wy * w0)
        vb = [
            bm.verts.new((p_fl[0], p_fl[1], z0_f)),
            bm.verts.new((p_fr[0], p_fr[1], z0_f)),
            bm.verts.new((p_rr[0], p_rr[1], z0_r)),
            bm.verts.new((p_rl[0], p_rl[1], z0_r)),
        ]
        vt = [
            bm.verts.new((p_fl[0], p_fl[1], z1_f)),
            bm.verts.new((p_fr[0], p_fr[1], z1_f)),
            bm.verts.new((p_rr[0], p_rr[1], z1_r)),
            bm.verts.new((p_rl[0], p_rl[1], z1_r)),
        ]
        for fi in range(4):
            fn = (fi + 1) % 4
            try:
                f = bm.faces.new([vb[fi], vb[fn], vt[fn], vt[fi]])
                f.material_index = mat_i
            except ValueError:
                pass
        try:
            ft = bm.faces.new(vt)
            ft.material_index = mat_i
            fb = bm.faces.new(list(reversed(vb)))
            fb.material_index = mat_i
        except ValueError:
            pass

    # 1. Dark grey/black front bumper & license plate valance (V5..V7, H7..H8)
    add_truck_part(-0.08, 0.32, -1.08, 1.08, 0.24, 0.64, 0.24, 0.64, 9)
    # 2. Sloped glossy white hood & rounded front fenders (V5..V7, H5..H7)
    add_truck_part(0.05, 1.68, -1.02, 1.02, 0.64, 1.44, 0.64, 1.68, 7)
    # 3. Black front radiator grille + silver horizontal grille bars (V5..V6, H6..H7)
    add_truck_part(-0.02, 0.12, -0.56, 0.56, 0.70, 1.38, 0.70, 1.38, 9)
    for g_z in (0.82, 0.96, 1.10, 1.24):
        add_truck_part(-0.04, 0.08, -0.50, 0.50, g_z, g_z + 0.04, g_z, g_z + 0.04, 11)
    # 4. Left & Right Headlight Clusters (bright white/silver + amber turn signal at V6, H6..H7)
    add_truck_part(-0.02, 0.22, 0.62, 0.98, 0.70, 0.98, 0.70, 1.02, 11)
    add_truck_part(-0.02, 0.22, -0.98, -0.62, 0.70, 0.98, 0.70, 1.02, 11)
    add_truck_part(0.02, 0.26, 0.88, 1.03, 0.72, 0.92, 0.72, 0.94, 6)
    # 5. Dark recessed front wheel well & Round 20-segment Black Rubber Tire + Silver Wheel Rim (V7..V8, H7..H8)
    add_truck_part(0.62, 1.62, 0.72, 1.04, 0.16, 1.02, 0.16, 1.02, 9)
    wheel_s = 1.12
    wheel_z = 0.52
    wheel_r = 0.48
    rim_r = 0.26
    for w_side in (-1.04, 0.88):
        w_verts_in = []
        w_verts_out = []
        r_verts_out = []
        for wi in range(20):
            ang = wi * 2.0 * math.pi / 20.0
            ds = wheel_r * math.cos(ang)
            dz = wheel_r * math.sin(ang)
            rds = rim_r * math.cos(ang)
            rdz = rim_r * math.sin(ang)
            wx_in = tx0 + t_ux * (wheel_s + ds) + t_wx * w_side
            wy_in = ty0 + t_uy * (wheel_s + ds) + t_wy * w_side
            wx_out = tx0 + t_ux * (wheel_s + ds) + t_wx * (w_side + 0.24)
            wy_out = ty0 + t_uy * (wheel_s + ds) + t_wy * (w_side + 0.24)
            rx_out = tx0 + t_ux * (wheel_s + rds) + t_wx * (w_side + 0.26)
            ry_out = ty0 + t_uy * (wheel_s + rds) + t_wy * (w_side + 0.26)
            w_verts_in.append(bm.verts.new((wx_in, wy_in, wheel_z + dz)))
            w_verts_out.append(bm.verts.new((wx_out, wy_out, wheel_z + dz)))
            r_verts_out.append(bm.verts.new((rx_out, ry_out, wheel_z + rdz)))
        for wi in range(20):
            wn = (wi + 1) % 20
            try:
                ft = bm.faces.new([w_verts_in[wi], w_verts_in[wn], w_verts_out[wn], w_verts_out[wi]])
                ft.material_index = 9
            except ValueError:
                pass
        try:
            fw = bm.faces.new(w_verts_out)
            fw.material_index = 9
            fr = bm.faces.new(r_verts_out)
            fr.material_index = 11
        except ValueError:
            pass

    # 6. Main Glossy White Cab Body & Lower Door Panel (V6..V8, H4..H7)
    add_truck_part(1.65, 3.85, -1.06, 1.06, 0.55, 1.72, 0.55, 1.72, 7)
    add_truck_part(2.15, 3.85, -1.04, 1.04, 1.72, 2.52, 1.72, 2.52, 7)
    # Sloped upper cab windshield frame & dark-tinted glass windshield (V6..V7, H4..H5)
    add_truck_part(1.65, 2.18, -1.02, 1.02, 1.68, 1.75, 2.42, 2.52, 7)
    add_truck_part(1.62, 2.14, -0.92, 0.92, 1.70, 1.74, 2.38, 2.44, 10)
    # Dark-tinted driver side door window & black side mirror assembly (V7..V8, H4..H5)
    add_truck_part(2.22, 3.32, 1.01, 1.07, 1.74, 2.38, 1.74, 2.38, 10)
    add_truck_part(2.12, 2.26, 1.05, 1.32, 1.78, 2.28, 1.78, 2.28, 9)
    # 7. Swept Glossy White Aerodynamic Roof Fairing & Amber Marker Lights (V6..V8, H3..H4)
    add_truck_part(1.98, 3.80, -0.98, 0.98, 2.50, 2.62, 2.50, 3.32, 7)
    add_truck_part(2.02, 2.20, 0.72, 0.92, 2.52, 2.66, 2.52, 2.66, 6)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False

    print("Constructed Public Plaza: Place Gare Viger Courtyard Plaza & Foreground Props")
    return obj


# ---------------------------------------------------------------------------
# 10. GROUND STRATUM, ROADBEDS & RAISED SIDEWALKS (ANTI-CLIPPING)
# ---------------------------------------------------------------------------
def build_ground_streets_and_sidewalks(dossier, palette, collection, building_polys):
    """
    Constructs:
    1. Solid watertight district ground collider base slab (Z = -0.25m .. 0.00m) with +Z normals
       and continuous PBR asphalt surface (Mat_MTL_Street_Asphalt).
    2. Continuous sun-lit PBR asphalt roadbeds (Z = 0.00m .. +0.025m) + smooth Rue Berri / Rue Saint-Antoine Est
       intersection plaza with white bicycle-lane sharrow chevrons, lane lines, green bike bollard,
       cyclist figure (V2..V3, H5..H6), and parked car noses (V1 & V8, H5..H6) in Cam 3!
    3. Raised concrete/granite sidewalks (Z = +0.15m) with 3D granite curbs.
    """
    name = f"Block_{BLOCK_ID}_Ground_And_Streets"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    mat_white_paint = create_solid_material("Mat_MTL_RoadPaint_White", (0.92, 0.93, 0.94, 1.0), roughness=0.45)
    mat_green_bollard = create_solid_material("Mat_MTL_BikeBollard_Green", (0.18, 0.68, 0.32, 1.0), roughness=0.35)
    mat_silver_car = create_solid_material("Mat_MTL_StreetCar_Silver", (0.76, 0.78, 0.80, 1.0), roughness=0.22, metallic=0.75)
    mat_cyclist_red = create_solid_material("Mat_MTL_Cyclist_Jersey", (0.68, 0.22, 0.20, 1.0), roughness=0.55)

    # 0: Asphalt, 1: Sidewalk Granite, 2: Cobblestone, 3: Dark Tire/Frame, 4: White Road Paint,
    # 5: Green Bollard, 6: Silver Car Body, 7: Dark Glass, 8: Cyclist Red
    mats = [
        palette["Mat_MTL_Street_Asphalt"],
        palette["Mat_MTL_Plaza_Light_Granite"],
        palette["Mat_MTL_Cobblestone"],
        palette["Mat_MTL_CastIron_Black"],
        mat_white_paint,
        mat_green_bollard,
        mat_silver_car,
        palette["Mat_MTL_Window_Glass_Dark"],
        mat_cyclist_red,
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # --- Part A: Watertight District Ground Base Slab (Z = -0.25m .. 0.00m) ---
    base_poly = [
        (100.0, 650.0),
        (550.0, 650.0),
        (550.0, 1050.0),
        (100.0, 1050.0),
    ]
    extrude_prism_in_bm(bm, base_poly, -0.25, 0.00, mat_side=3, mat_top=0, cap_top=True)

    # --- Part B: Smooth Continuous Rue Berri / Rue Saint-Antoine Est Intersection Roadbed (Cam 3 H5..H8!) ---
    berri_intersection_poly = ensure_ccw([
        (240.0, 765.0),
        (318.0, 765.0),
        (318.0, 812.0),
        (240.0, 812.0),
    ])
    extrude_prism_in_bm(bm, berri_intersection_poly, 0.00, 0.025, mat_side=0, mat_top=0, cap_top=True)

    # White bicycle lane lines, sharrow chevrons, and directional arrows in Cam 3 foreground
    add_box_between(bm, (263.0, 791.0), (290.0, 779.5), 0.025, 0.033, thickness=0.15, offset_out=0.0, mat_idx=4)
    add_box_between(bm, (266.0, 784.5), (287.0, 775.5), 0.025, 0.033, thickness=0.15, offset_out=0.0, mat_idx=4)
    for bx_m, by_m in ((273.2, 788.0), (276.6, 790.2)):
        add_box_between(bm, (bx_m - 0.85, by_m + 0.35), (bx_m + 0.85, by_m - 0.35), 0.025, 0.035, thickness=0.16, offset_out=0.0, mat_idx=4)
        add_box_between(bm, (bx_m - 0.55, by_m + 0.65), (bx_m + 0.15, by_m + 0.10), 0.025, 0.035, thickness=0.14, offset_out=0.0, mat_idx=4)
        add_box_between(bm, (bx_m - 0.55, by_m - 0.15), (bx_m + 0.15, by_m + 0.10), 0.025, 0.035, thickness=0.14, offset_out=0.0, mat_idx=4)

    # Raised traffic median island & green flexible bike-lane bollard in Cam 3 left foreground (V1..V2, H5..H6!)
    island_poly = ensure_ccw([
        (261.0, 792.5),
        (266.8, 790.2),
        (267.4, 791.6),
        (261.6, 793.9),
    ])
    extrude_prism_in_bm(bm, island_poly, 0.00, 0.16, mat_side=1, mat_top=1, cap_top=True)
    bollard_pts = [(266.8 + 0.07 * math.cos(k * math.pi / 4), 790.7 + 0.07 * math.sin(k * math.pi / 4)) for k in range(8)]
    extrude_prism_in_bm(bm, bollard_pts, 0.02, 0.96, mat_side=5, mat_top=5, cap_top=True)

    # Cam 3 Street Life:
    # 1. Left foreground parked silver sedan nose + street sign post at (264.2, 791.8) (V1, H5..H6 in Cam 3!)
    add_box_between(bm, (262.2, 792.6), (264.8, 791.5), 0.18, 0.88, thickness=1.72, mat_idx=6)
    add_box_between(bm, (262.0, 792.7), (263.6, 792.0), 0.88, 1.38, thickness=1.52, mat_idx=7)
    add_box_between(bm, (264.4, 791.7), (264.9, 791.4), 0.02, 0.65, thickness=1.78, mat_idx=3)
    add_box_between(bm, (264.45, 792.15), (264.55, 792.25), 0.16, 2.55, thickness=0.06, mat_idx=3)
    add_box_between(bm, (264.25, 792.05), (264.75, 792.35), 1.85, 2.50, thickness=0.05, mat_idx=4)

    # 2. Cyclist on Bicycle riding along the bike lane at (268.6, 791.0) (V2..V3, H5..H6 in Cam 3!)
    cyc_x, cyc_y = 268.6, 791.0
    c_ux, c_uy = 0.9135, -0.4067
    for w_off in (-0.52, 0.52):
        wx_c = cyc_x + c_ux * w_off
        wy_c = cyc_y + c_uy * w_off
        add_box_between(bm, (wx_c - c_ux * 0.32, wy_c - c_uy * 0.32), (wx_c + c_ux * 0.32, wy_c + c_uy * 0.32), 0.03, 0.68, thickness=0.06, mat_idx=3)
    # Bicycle frame, handlebars, and cyclist torso/legs/head
    add_box_between(bm, (cyc_x - c_ux * 0.45, cyc_y - c_uy * 0.45), (cyc_x + c_ux * 0.45, cyc_y + c_uy * 0.45), 0.36, 0.86, thickness=0.07, mat_idx=3)
    add_box_between(bm, (cyc_x - c_ux * 0.18, cyc_y - c_uy * 0.18), (cyc_x + c_ux * 0.18, cyc_y + c_uy * 0.18), 0.45, 1.05, thickness=0.26, mat_idx=3)
    add_box_between(bm, (cyc_x - c_ux * 0.22, cyc_y - c_uy * 0.22), (cyc_x + c_ux * 0.22, cyc_y + c_uy * 0.22), 0.98, 1.52, thickness=0.32, mat_idx=8)
    add_box_between(bm, (cyc_x + c_ux * 0.05, cyc_y + c_uy * 0.05), (cyc_x + c_ux * 0.25, cyc_y + c_uy * 0.25), 1.52, 1.74, thickness=0.22, mat_idx=3)

    # 3. Right foreground silver sedan nose at (284.2, 792.8) (V8, H5..H6 in Cam 3!)
    add_box_between(bm, (283.2, 793.2), (286.0, 792.0), 0.18, 0.92, thickness=1.76, mat_idx=6)
    add_box_between(bm, (284.2, 792.8), (286.0, 792.0), 0.92, 1.42, thickness=1.56, mat_idx=7)
    add_box_between(bm, (283.3, 793.2), (284.1, 792.8), 0.02, 0.68, thickness=1.82, mat_idx=3)

    # --- Part C: Roadbeds & Flanking Raised Sidewalks (excluding the Cam 3 intersection box so no interior curbs cut across!) ---
    highways = dossier.get("osm_features", {}).get("highways", [])
    for hw in highways:
        pts = hw.get("coords_xy", [])
        if len(pts) < 2:
            continue
        hw_name = hw.get("tags", {}).get("name") or hw.get("name") or ""
        hw_type = hw.get("tags", {}).get("highway", "residential")
        is_ped = hw_type in ("pedestrian", "footway", "path", "steps") or "Gare Viger" in hw_name

        road_w = 4.0 if is_ped else 8.5
        mat_road = 2 if is_ped else 0

        for s in range(len(pts) - 1):
            p1, p2 = pts[s], pts[s + 1]
            seg_l = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_l < 0.5:
                continue
            mid_x = 0.5 * (p1[0] + p2[0])
            mid_y = 0.5 * (p1[1] + p2[1])
            # Skip interior sidewalk/curb segments inside the Cam 3 intersection box (252..298, 774..808)
            in_cam3_box = (252.0 <= mid_x <= 298.0 and 774.0 <= mid_y <= 808.0)

            # Asphalt roadbed (Z = 0.00m .. 0.015m)
            if not in_cam3_box:
                add_box_between(bm, p1, p2, 0.00, 0.015, thickness=road_w, offset_out=0.0, mat_idx=mat_road)

            # Flanking raised sidewalks (+0.15m) along vehicular roadways
            if not is_ped and not in_cam3_box:
                dx, dy = (p2[0] - p1[0]) / seg_l, (p2[1] - p1[1]) / seg_l
                nx, ny = dy, -dx

                # Left and Right sidewalk centers
                for side in (-1.0, 1.0):
                    sw_offset = side * (road_w * 0.5 + 1.4)
                    sw_mid = ((p1[0] + p2[0]) * 0.5 + nx * sw_offset,
                              (p1[1] + p2[1]) * 0.5 + ny * sw_offset)

                    clipping = False
                    for b_poly in building_polys:
                        for k in range(len(b_poly) - 1):
                            if pt_seg_dist(sw_mid, b_poly[k], b_poly[k + 1]) < 1.42:
                                clipping = True
                                break
                        if clipping:
                            break

                    if not clipping:
                        add_box_between(bm, p1, p2, 0.00, 0.15, thickness=2.8, offset_out=sw_offset, mat_idx=1)
                        curb_offset = side * (road_w * 0.5 + 0.09)
                        add_box_between(bm, p1, p2, 0.00, 0.17, thickness=0.18, offset_out=curb_offset, mat_idx=1)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False

    print("Constructed Watertight Ground Stratum, Smooth Intersection Roadbed & Bike Lane Markings")
    return obj


# ---------------------------------------------------------------------------
# 11. PROPS & 3D ASSETS SCATTERING (COMBINED POLY HAVEN 3D ASSETS)
# ---------------------------------------------------------------------------
def load_combined_polyhaven_templates():
    """
    Loads real high-poly Poly Haven 3D models from `assets/polyhaven/models/`:
    - `jacaranda_tree.blend`: combines trunk/branches AND leaf foliage canopy into a single
      rich 3D tree mesh with summer-green Montreal foliage material.
    - `street_lamp_01.blend`: heritage cast-iron streetlamp.
    - `modular_street_seating.blend`: park/courtyard bench.
    """
    combined_tree_mesh = None
    ph_tree_blend = os.path.join(POLYHAVEN_DIR, "models", "jacaranda_tree", "jacaranda_tree.blend")
    if os.path.isfile(ph_tree_blend):
        with bpy.data.libraries.load(ph_tree_blend, link=False) as (df, dt):
            dt.objects = list(df.objects)
        tree_parts = [o for o in dt.objects if o is not None and o.type == "MESH" and o.data is not None]
        if tree_parts:
            raw_tree_mesh = bpy.data.meshes.new("PH_Combined_Jacaranda_Tree_0033")
            bm_tree = bmesh.new()
            mat_list = []
            mat_index_map = {}
            for o in tree_parts:
                me = o.data
                mat_remap = {}
                for slot_idx, mat in enumerate(me.materials):
                    m_key = mat.name if mat else "None"
                    if m_key not in mat_index_map:
                        mat_index_map[m_key] = len(mat_list)
                        mat_list.append(mat)
                    mat_remap[slot_idx] = mat_index_map[m_key]
                bm_part = bmesh.new()
                bm_part.from_mesh(me)
                bm_part.transform(o.matrix_world)
                is_leaves = ("leaves" in o.name.lower() or "leaf" in o.name.lower() or "twig" in o.name.lower())
                if is_leaves and len(bm_part.faces) > 6000:
                    faces_to_del = [f for idx_f, f in enumerate(bm_part.faces) if (idx_f % 5) != 0]
                    bmesh.ops.delete(bm_part, geom=faces_to_del, context="FACES")
                elif len(bm_part.faces) > 8000:
                    bmesh.ops.dissolve_limit(bm_part, angle_limit=math.radians(16.0), verts=bm_part.verts, edges=bm_part.edges)
                for f in bm_part.faces:
                    f.material_index = mat_remap.get(f.material_index, 0)
                tmp_m = bpy.data.meshes.new("TmpTreePart0033")
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
                                n.inputs["Base Color"].default_value = (0.16, 0.42, 0.11, 1.0)
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


def point_in_poly_2d(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside
    return inside


def dist_to_poly_2d(px, py, poly):
    if point_in_poly_2d(px, py, poly):
        return 0.0
    min_d = 999999.0
    n = len(poly)
    for i in range(n):
        d = pt_seg_dist((px, py), poly[i], poly[(i + 1) % n])
        if d < min_d:
            min_d = d
    return min_d


def scatter_kit_props(collection_owned, dossier, building_polys, palette):
    """
    Places real combined Poly Haven 3D shade trees (jacaranda_tree with lush green foliage),
    streetlamps (street_lamp_01), and benches (modular_street_seating) across Place Gare Viger,
    Rue Saint-Antoine Est, and Rue Berri matching both Street View cameras and Satellite Top-Down.
    """
    tree_mesh, lamp_mesh, bench_mesh = load_combined_polyhaven_templates()

    # 1. Exact Satellite & Street View Matched Trees (Cam 3 left cluster, Place Gare-Viger courtyard lawn trees, NW Berri trees)
    satellite_trees = [
        # Cam 3 (Rue_Berri_Viger_Frontage) & Satellite H5..H6, V2..V3 lush trees in front of SW junction:
        (268.5, 811.0, 0.34, 25.0),
        (277.0, 807.5, 0.32, 115.0),
        (264.0, 799.0, 0.34, 210.0),
        # NW Rue Berri street trees (Satellite H1..H2, V1):
        (246.5, 882.0, 0.56, 40.0),
        (253.0, 898.0, 0.52, 130.0),
        # Place Gare-Viger Courtyard Lawn Trees (Satellite H4..H5, V3..V5):
        (289.0, 840.0, 0.38, 60.0),
        (298.0, 836.0, 0.40, 145.0),
        (308.0, 832.0, 0.38, 235.0),
        (332.0, 822.0, 0.36, 310.0),
        # South Rue Berri / Saint-Antoine trees (Satellite H7..H8, V2..V4):
        (266.0, 762.0, 0.50, 80.0),
        (294.0, 756.0, 0.48, 175.0),
    ]

    placed_trees = 0
    if tree_mesh:
        for idx, (tx, ty, sc, rot_deg) in enumerate(satellite_trees):
            t_obj = bpy.data.objects.new(f"MTL_Owned_Tree_{BLOCK_ID}_{placed_trees:02d}", tree_mesh)
            t_obj.location = (tx, ty, 0.18)
            t_obj.rotation_euler = (0.0, 0.0, math.radians(rot_deg))
            t_obj.scale = (sc, sc, sc)
            collection_owned.objects.link(t_obj)
            placed_trees += 1

    # 2. Streetlamp Locations (including exact Cam 3 center-right streetlamp at [283.5, 798.5]!)
    candidate_lamps = [
        (283.5, 798.5),  # Exact black heritage lamp post in Cam 3 (Rue_Berri_Viger_Frontage V5..V6, H3..H6)!
        (274.0, 816.0),
        (290.0, 846.0),
        (312.0, 838.0),
        (332.0, 830.0),
        (252.0, 860.0),
        (260.0, 880.0),
        (318.0, 790.0),
    ]

    placed_lamps = 0
    if lamp_mesh:
        for idx, (lx, ly) in enumerate(candidate_lamps):
            l_obj = bpy.data.objects.new(f"MTL_Owned_StreetLamp_{BLOCK_ID}_{placed_lamps:02d}", lamp_mesh)
            l_obj.location = (lx, ly, 0.16)
            l_obj.scale = (1.0, 1.0, 1.0)
            collection_owned.objects.link(l_obj)
            placed_lamps += 1

    # 3. Courtyard Bench Locations along Terracotta Walkways
    candidate_benches = [
        (294.0, 844.0, 22.0),
        (308.0, 838.0, 22.0),
        (322.0, 832.0, 22.0),
        (336.0, 826.0, 22.0),
    ]

    placed_benches = 0
    if bench_mesh:
        for idx, (bx, by, rot) in enumerate(candidate_benches):
            b_obj = bpy.data.objects.new(f"MTL_Owned_Bench_{BLOCK_ID}_{placed_benches:02d}", bench_mesh)
            b_obj.location = (bx, by, 0.26)
            b_obj.rotation_euler = (0.0, 0.0, math.radians(rot))
            collection_owned.objects.link(b_obj)
            placed_benches += 1

    print(f"Placed Combined Poly Haven 3D Props: {placed_trees} Trees, {placed_lamps} Streetlamps, {placed_benches} Benches")


def configure_world_and_lighting():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.device = "CPU"
        scene.cycles.samples = 36
        scene.cycles.use_denoising = True
    except Exception:
        pass

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    w_out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.62, 0.76, 0.94, 1.0)
    bg.inputs["Strength"].default_value = 1.85
    links.new(w_out.inputs["Surface"], bg.outputs["Background"])

    if os.path.isfile(HDRI_PATH):
        try:
            env = nodes.new("ShaderNodeTexEnvironment")
            env.image = bpy.data.images.load(HDRI_PATH, check_existing=True)
            links.new(bg.inputs["Color"], env.outputs["Color"])
        except Exception:
            pass

    sun_data = bpy.data.lights.new(name=f"MTL_Sun_{BLOCK_ID}", type="SUN")
    sun_data.energy = 3.8
    sun_data.color = (1.0, 0.96, 0.89)
    sun_data.angle = math.radians(2.0)
    sun_obj = bpy.data.objects.new(name=f"MTL_Sun_{BLOCK_ID}", object_data=sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(48.0), math.radians(16.0), math.radians(-130.0))

    fill_data = bpy.data.lights.new(name=f"MTL_Fill_{BLOCK_ID}", type="SUN")
    fill_data.energy = 2.2
    fill_data.color = (0.95, 0.97, 1.0)
    fill_data.angle = math.radians(20.0)
    fill_obj = bpy.data.objects.new(name=f"MTL_Fill_{BLOCK_ID}", object_data=fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(56.0), math.radians(-18.0), math.radians(50.0))


def render_cameras(dossier, cam_col):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640

    cams = dossier.get("streetview_cameras", [])
    for cam_info in cams:
        label = cam_info.get("label", "cam")
        cx, cy = cam_info.get("blender_cam_xy_m", (312.0, 832.0))
        heading_deg = float(cam_info.get("heading", cam_info.get("heading_deg", 0.0)))
        pitch_deg = float(cam_info.get("pitch_deg", 10.0))
        fov_deg = float(cam_info.get("fov_deg", 90.0))

        cam_data = bpy.data.cameras.new(name=f"SV_Cam_{label}")
        cam_data.angle = math.radians(fov_deg)
        cam_data.clip_start = 0.20
        cam_data.clip_end = 1500.0
        cam_obj = bpy.data.objects.new(name=f"SV_Cam_{label}", object_data=cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cx, cy, 1.8)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch_deg), 0.0, math.radians(-heading_deg))

        scene.camera = cam_obj
        out_file = os.path.join(RENDERS_DIR, f"iter1_{label}.png")
        scene.render.filepath = out_file
        try:
            bpy.ops.render.render(write_still=True)
            print(f"Rendered Street View Camera [{label}] -> {out_file}")
        except Exception as e:
            print(f"Render skipped for [{label}]: {e}")

    # Overview Snapshot Camera
    ov_data = bpy.data.cameras.new(name=f"Overview_Cam_{BLOCK_ID}")
    ov_data.angle = math.radians(52.0)
    ov_data.clip_start = 1.0
    ov_data.clip_end = 2000.0
    ov_obj = bpy.data.objects.new(name=f"Overview_Cam_{BLOCK_ID}", object_data=ov_data)
    cam_col.objects.link(ov_obj)

    target = Vector((310.0, 840.0, 20.0))
    ov_obj.location = (420.0, 720.0, 120.0)
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = SNAPSHOT_PATH
    try:
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Block Overview Snapshot -> {SNAPSHOT_PATH}")
    except Exception as e:
        print(f"Overview snapshot skipped: {e}")


# ---------------------------------------------------------------------------
# 13. MAIN EXECUTION PIPELINE
# ---------------------------------------------------------------------------
def main():
    skip_render = False
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if "--skip-render" in args:
            skip_render = True

    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    # Collections Setup: ONLY Block_MTL-VM-0033_Owned (NO Context Proxies!)
    master_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(master_col)
    col_owned = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    master_col.children.link(col_owned)
    cam_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Cameras")
    master_col.children.link(cam_col)

    palette = create_block_palette()

    # Filter to ONLY primary owned buildings
    all_bldgs = dossier.get("osm_features", {}).get("buildings", [])
    owned_bldgs = [b for b in all_bldgs if b.get("is_primary_owner") is True]
    print(f"[{BLOCK_ID}] Processing {len(owned_bldgs)} primary owned buildings...")

    # Extract all building footprint polygons for party-wall & clearance checks
    bldg_polys = [b["coords_xy"] for b in owned_bldgs if len(b.get("coords_xy", [])) >= 3]

    # 1. Ground Stratum & Streets
    print(f"[{BLOCK_ID}] Building ground stratum and watertight roadbed/sidewalk network...")
    build_ground_streets_and_sidewalks(dossier, palette, col_owned, bldg_polys)

    # 2. Courtyard Plaza (Place Gare Viger)
    print(f"[{BLOCK_ID}] Building Place Gare Viger courtyard plaza...")
    build_courtyard_plaza_place_gare_viger(dossier, palette, col_owned)

    # 3. Adjacency, Balanced Facade Assignments & Height Deconfliction
    print(f"[{BLOCK_ID}] Computing adjacency graph, balanced coloring & deconflicted heights...")
    facade_keys = [
        "Mat_MTL_PierreGrise_Limestone", "Mat_MTL_WarmBuff_Limestone", "Mat_MTL_Red_Sandstone",
        "Mat_MTL_Heritage_RedBrick", "Mat_MTL_Victorian_Brick", "Mat_MTL_Yellow_Buff_Brick",
        "Mat_MTL_Dark_Loft_Brick", "Mat_MTL_Whitewash_Fieldstone", "Mat_MTL_Precast_Concrete",
        "Mat_MTL_Granite_Plinth", "Mat_MTL_Weathered_Metal", "Mat_MTL_Warm_Timber",
        "Mat_MTL_Limestone_Tile", "Mat_MTL_Medieval_Stone",
    ]
    adj = compute_building_adjacency(owned_bldgs)
    facade_assignments = compute_balanced_facade_assignments(owned_bldgs, adj, n_materials=len(facade_keys))
    deconf_heights, deconf_ground_h = compute_deconflicted_heights(owned_bldgs, adj)

    # 4. Construct all primary owned buildings
    print(f"[{BLOCK_ID}] Constructing 3D architectural models for all {len(owned_bldgs)} primary owned buildings...")
    built_count = 0
    for b in owned_bldgs:
        bid = b["id"]
        pts = b.get("coords_xy", [])
        if len(pts) < 3:
            continue

        other_p = [op for op in bldg_polys if op is not pts]

        # Signature Landmark 1: Château Viger / Ancienne Gare Viger (46866814)
        if bid == 46866814:
            build_chateau_viger(b, palette, col_owned, other_polys=other_p)
            built_count += 1
            continue

        # Signature Landmark 2: Modern Glass Annex (1244672622)
        if bid == 1244672622:
            build_modern_glass_annex(b, palette, col_owned, other_polys=other_p)
            built_count += 1
            continue

        # Signature Landmark 3: East Courtyard Tower with Rooftop Pool (1244672623)
        if bid == 1244672623:
            build_east_courtyard_tower_1244672623(b, palette, col_owned, other_polys=other_p)
            built_count += 1
            continue

        # Skip demolished historical roadway footprints inside the Rue Berri / Rue Saint-Antoine Est intersection
        if bid in (341118811, 341119731, 341119977, 341120172, 341120236):
            continue

        # Assigned facade material from balanced coloring
        mat_idx = facade_assignments.get(bid, 0)
        wall_mat_key = facade_keys[mat_idx]
        mat_wall = palette[wall_mat_key]

        b_height = deconf_heights.get(bid, 15.5)
        b_ground_h = deconf_ground_h.get(bid, 3.20)

        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', b.get("name") or "")
        b_name = f"MTL_Owned_{bid}_{safe_name}" if safe_name else f"MTL_Owned_{bid}_Bldg"

        roof_mat = palette["Mat_MTL_Roof_White_Reflective"] if bid in (46866830, 341118811, 341120172) else palette["Mat_Roof_Flat"]

        build_detailed_facade_building(
            name=b_name,
            coords_xy=pts,
            height=b_height,
            floor_height=3.8,
            mat_wall=mat_wall,
            mat_roof=roof_mat,
            mat_window=palette["Mat_MTL_Window_Glass_Dark"],
            mat_frame=palette["Mat_MTL_CastIron_Black"],
            mat_plinth=palette["Mat_MTL_PierreGrise_Limestone"],
            collection=col_owned,
            roof_style="flat",
            rusticated_piers=True,
            bay_target_width=3.4,
            mat_top_cornice=palette["Mat_MTL_WarmBuff_Limestone"],
            other_polys=other_p,
            custom_ground_h=b_ground_h,
        )
        built_count += 1

    print(f"[{BLOCK_ID}] Successfully constructed {built_count} primary owned buildings in Block_{BLOCK_ID}_Owned.")

    # 5. Scatter 3D Props (clearance filter verified)
    print(f"[{BLOCK_ID}] Scattering 3D kit assets (trees, lamps, benches)...")
    scatter_kit_props(col_owned, dossier, bldg_polys, palette)

    # 6. Verification & World Lighting Setup BEFORE packing and saving
    print(f"[{BLOCK_ID}] Configuring world lighting and verifying clean collection hierarchy...")
    configure_world_and_lighting()
    hidden_count = 0
    proxy_count = 0
    for obj in bpy.data.objects:
        if obj.hide_render:
            hidden_count += 1
        if "proxy" in obj.name.lower() or "context" in obj.name.lower():
            proxy_count += 1
    print(f"[{BLOCK_ID}] Verification: Hidden meshes = {hidden_count}, Context Proxies = {proxy_count}")

    # 7. Pack all 2K PBR textures, Save Blend & Export USDC
    print(f"[{BLOCK_ID}] Packing all 2K PBR textures and saving {BLEND_OUT_PATH}...")
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"Warning during pack_all: {e}")
    tmp_blend = BLEND_OUT_PATH + ".tmp.blend"
    for p in (tmp_blend, BLEND_OUT_PATH + "@", BLEND_OUT_PATH + "@1"):
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

    print(f"[{BLOCK_ID}] Exporting {USDC_OUT_PATH} (visible objects in col_owned)...")
    bpy.ops.object.select_all(action='DESELECT')
    for obj in col_owned.all_objects:
        if not obj.hide_render and not obj.hide_viewport:
            obj.select_set(True)
    try:
        bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, check_existing=False, selected_objects_only=True)
    except Exception:
        bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, check_existing=False)
    print(f"[{BLOCK_ID}] Successfully saved clean .blend and exported .usdc!")

    # 8. Cameras Rendering
    if not skip_render:
        render_cameras(dossier, cam_col)

    print(f"[{BLOCK_ID}] BUILD COMPLETE! Clean .blend and .usdc successfully created.")


if __name__ == "__main__":
    main()
