"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0022 (Iteration 2)
Quai Alexandra & Grand Quai du Port de Montréal (Cruise Terminal, Promenade d'Iberville & Observation Tower)
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

BLOCK_ID = "MTL-VM-0022"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
SNAPSHOT_PATH = os.path.join(BASE_DIR, "output", "renders", f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.usdc")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT_PATH), exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def assign_world_uvs(bm, scale=0.25):
    uv_layer = bm.loops.layers.uv.verify()
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.normal_update()
        nx, ny, nz = abs(f.normal.x), abs(f.normal.y), abs(f.normal.z)
        for loop in f.loops:
            co = loop.vert.co
            if nz >= nx and nz >= ny:
                loop[uv_layer].uv = (co.x * scale, co.y * scale)
            elif nx >= ny:
                loop[uv_layer].uv = (co.y * scale, co.z * scale)
            else:
                loop[uv_layer].uv = (co.x * scale, co.z * scale)


def create_upgraded_palette():
    palette = kit.create_montreal_material_palette()

    # Lush green lawn PBR (leafy_grass_Diffuse_2k.jpg)
    mat_lawn = kit.get_or_create_image_pbr_material(
        "Mat_MTL_Grass_Lawn_PBR", "leafy_grass", fallback_hex="#46692B", uv_scale=1.0, bump_strength=0.85
    )
    palette["Mat_MTL_Grass_Lawn_PBR"] = mat_lawn
    palette["Mat_MTL_Green_Roof_Lawn"] = mat_lawn

    # 2K PBR Water (water_river_diffuse_2k.jpg, water_river_nor_gl_2k.jpg, water_river_rough_2k.jpg)
    mat_water = kit.get_or_create_water_pbr_material("Mat_MTL_StLawrence_Water_PBR", uv_scale=0.35)
    palette["Mat_MTL_Water_Basin"] = mat_water

    # Warm Cedar Timber Boardwalk (weathered_planks 2K PBR)
    mat_wood = kit.get_or_create_image_pbr_material(
        "Mat_MTL_Wood_Decking", "weathered_planks", fallback_hex="#8F633E", uv_scale=1.2, bump_strength=1.0
    )
    palette["Mat_MTL_Wood_Decking"] = mat_wood

    # Terminal Pre-patinated Architectural Cladding Panels (crisp bright architectural white/light-grey)
    palette["Mat_MTL_Terminal_White_Panels"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Terminal_White_Panels", "#E6EAEF", roughness=0.32, metallic=0.10, bump_strength=0.03, noise_scale=30.0
    )

    # Light Silver-Grey Flat Roof Membrane (matching Satellite TopDown roofs)
    palette["Mat_MTL_Light_Roof_Deck"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Light_Roof_Deck", "#D2D7DC", roughness=0.55, metallic=0.05, bump_strength=0.04, noise_scale=24.0
    )

    # Golden-Bronze Cantilevered Lattice Cage for Port of Montreal Observation Tower
    palette["Mat_MTL_Tower_Gold_Cage"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Tower_Gold_Cage", "#D49B35", roughness=0.22, metallic=0.88, bump_strength=0.02
    )

    # Sleek Blue-Grey Reflective Tower Glass Curtain Wall
    mat_tg = kit.get_or_create_pbr_material(
        "Mat_MTL_Tower_Glass", "#1B3248", roughness=0.04, metallic=0.45, bump_strength=0.0
    )
    palette["Mat_MTL_Tower_Glass"] = mat_tg

    # Dark Reflective Storefront Glass
    palette["Mat_MTL_Window_Glass_Dark"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Window_Glass_Dark", "#121E2B", roughness=0.05, metallic=0.35, bump_strength=0.0
    )

    # White Structural Steel & Cruise Ship Superstructure
    palette["Mat_MTL_White_Steel"] = kit.get_or_create_pbr_material(
        "Mat_MTL_White_Steel", "#EDF0F2", roughness=0.25, metallic=0.65, bump_strength=0.01
    )
    palette["Mat_MTL_Ship_Navy_Hull"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Ship_Navy_Hull", "#13294B", roughness=0.32, metallic=0.40, bump_strength=0.02
    )
    palette["Mat_MTL_Crosswalk_White"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Crosswalk_White", "#EAECEF", roughness=0.75, metallic=0.0, bump_strength=0.04
    )

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


def add_top_face_in_bm(bm, pts, z, mat_idx=0):
    pts = ensure_ccw(pts)
    if len(pts) < 3:
        return
    verts = [bm.verts.new((p[0], p[1], z)) for p in pts]
    try:
        f = bm.faces.new(verts)
        f.material_index = mat_idx
    except ValueError:
        pass


def add_box_between(bm, p1, p2, z0, z1, thickness=0.35, offset_out=0.0, mat_idx=0, cap_top=True):
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
        (v_bot[0], v_bot[1], v_top[1], v_top[0]),
        (v_bot[1], v_bot[2], v_top[2], v_top[1]),
        (v_bot[2], v_bot[3], v_top[3], v_top[2]),
        (v_bot[3], v_bot[0], v_top[0], v_top[3]),
    ]
    if cap_top:
        quads.append((v_top[0], v_top[1], v_top[2], v_top[3]))
    for q in quads:
        try:
            f = bm.faces.new(q)
            f.material_index = mat_idx
        except ValueError:
            pass


def extrude_prism_in_bm(bm, pts, z0, z1, mat_side=0, mat_top=None):
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


def add_cylinder_in_bm(bm, center_xy, z0, z1, r_bot, r_top, n_seg=12, mat_idx=0):
    cx, cy = center_xy
    if z1 <= z0 or r_bot <= 0:
        return
    v_bot, v_top = [], []
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
    try:
        f_top = bm.faces.new(v_top)
        f_top.material_index = mat_idx
    except ValueError:
        pass


def finalize_bm_to_mesh(bm, mesh, scale_uv=0.25):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign_world_uvs(bm, scale=scale_uv)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False


# --- 1. Terminal 3 (46866808) + Stepped Wooden Promenade d'Iberville & Rooftop Lawn ---

def build_terminal_3_46866808(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_46866808_Terminal_3"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Terminal_White_Panels"],   # 0: Pre-patinated light architectural panels
        palette["Mat_MTL_Wood_Decking"],            # 1: Cedar boardwalk / stepped amphitheater
        palette["Mat_MTL_Window_Glass_Dark"],       # 2: Recessed dark curtain-wall glazing
        palette["Mat_MTL_Grass_Lawn_PBR"],          # 3: Lush green rooftop lawn
        palette["Mat_MTL_Dark_Bronze_CurtainWall"], # 4: Dark anodized aluminum mullions & canopies
        palette["Mat_MTL_Light_Roof_Deck"],         # 5: Light silver-grey roof deck (west headhouse)
        palette["Mat_MTL_PierreGrise_Limestone"],   # 6: Warm grey limestone trim
        palette["Mat_MTL_Slate_Roof_Dark"],         # 7: Dark slate roof cap
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Exact 2-story height matching Grand_Quai_Tower_South (H4/H5 seam = 6.15m)
    h_main = 6.15
    extrude_prism_in_bm(bm, pts, 0.0, h_main, mat_side=0, mat_top=None)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 2.0:
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len

        # Ground floor deeply recessed (>= 0.50m) dark-framed glass curtain-wall storefront (Z = 0.15m..3.35m)
        add_box_between(bm, p1, p2, 0.15, 3.35, thickness=0.14, offset_out=-0.52, mat_idx=2, cap_top=False)
        # Projecting dark anodized aluminum entrance canopy & transom (Z = 3.25m..3.50m)
        add_box_between(bm, p1, p2, 3.25, 3.50, thickness=0.95, offset_out=0.28, mat_idx=4)
        # Upper story horizontal pre-patinated concrete/zinc cladding bands (Z = 3.50m..6.15m)
        add_box_between(bm, p1, p2, 3.50, 4.75, thickness=0.45, offset_out=0.06, mat_idx=0)
        add_box_between(bm, p1, p2, 4.75, 4.88, thickness=0.52, offset_out=0.10, mat_idx=4)
        add_box_between(bm, p1, p2, 4.88, h_main, thickness=0.45, offset_out=0.06, mat_idx=0)

        # Dark anodized vertical mullions every 2.8m along storefront
        n_mull = max(1, int(round(seg_len / 2.8)))
        for c in range(n_mull + 1):
            pos = min(seg_len, c * (seg_len / n_mull))
            mp1 = (p1[0] + dx * max(0.0, pos - 0.12), p1[1] + dy * max(0.0, pos - 0.12))
            mp2 = (p1[0] + dx * min(seg_len, pos + 0.12), p1[1] + dy * min(seg_len, pos + 0.12))
            add_box_between(bm, mp1, mp2, 0.0, 3.35, thickness=0.42, offset_out=0.05, mat_idx=4, cap_top=False)

        # Upper story recessed windows on western headhouse (X < 335, visible in Promenade_du_Grand_Quai_Roof V5..V7)
        if 0.5 * (p1[0] + p2[0]) < 340.0 and seg_len > 6.0:
            n_win = max(2, int(round(seg_len / 3.8)))
            bw = seg_len / n_win
            for w_idx in range(n_win):
                s0 = (w_idx + 0.22) * bw
                s1 = (w_idx + 0.78) * bw
                wp1 = (p1[0] + dx * s0, p1[1] + dy * s0)
                wp2 = (p1[0] + dx * s1, p1[1] + dy * s1)
                add_box_between(bm, wp1, wp2, 4.05, 5.45, thickness=0.16, offset_out=-0.48, mat_idx=2)

    # Rooftop glass safety balustrade & dark rail posts (Z = 6.15m..7.00m)
    roof_pts = inset_polygon_toward_centroid(pts, 0.96)
    for i in range(len(roof_pts)):
        rp1, rp2 = roof_pts[i], roof_pts[(i + 1) % len(roof_pts)]
        add_box_between(bm, rp1, rp2, h_main, h_main + 0.82, thickness=0.08, offset_out=0.0, mat_idx=2)
        add_box_between(bm, rp1, rp2, h_main + 0.82, h_main + 0.90, thickness=0.14, offset_out=0.0, mat_idx=4)

    # 1) Western Headhouse Roof Deck (X = 300.5..327.8, Y = -296.5..-267.0) -> Light silver-grey roof matching Satellite V5..V6, H5..H7
    west_roof = [
        (301.8, -296.2),
        (327.5, -293.6),
        (327.5, -267.2),
        (300.2, -270.0),
    ]
    extrude_prism_in_bm(bm, west_roof, h_main - 0.25, h_main + 0.12, mat_side=6, mat_top=5)

    # Subtle dark hipped/pitched pavilion cap on the northwest corner for Promenade_du_Grand_Quai_Roof (V5..V7, H4)
    nw_pav = [
        (301.5, -278.5),
        (326.5, -276.0),
        (326.5, -267.5),
        (300.8, -270.2),
    ]
    extrude_prism_in_bm(bm, nw_pav, h_main + 0.12, h_main + 1.15, mat_side=6, mat_top=7)

    # 2) Stepped Wooden Promenade d'Iberville Boardwalk & Monumental Amphitheater Stairs along North Edge (Y = -267.2..-258.5)
    # Monumental wooden steps descending toward western plaza (X = 300..314)
    for step_i in range(10):
        sx0 = 300.0 + step_i * 1.4
        sx1 = sx0 + 1.45
        sz = 1.20 + step_i * 0.50
        step_poly = [
            (sx0, -267.0),
            (sx1, -266.8),
            (sx1, -258.8),
            (sx0, -259.0),
        ]
        extrude_prism_in_bm(bm, step_poly, sz - 0.45, sz, mat_side=1, mat_top=1)

    # Warm cedar timber boardwalk deck running East along H5 (X = 314..566)
    boardwalk_poly = [
        (314.0, -267.2),
        (566.0, -241.0),
        (565.5, -247.5),
        (314.0, -258.8),
    ]
    extrude_prism_in_bm(bm, boardwalk_poly, h_main - 0.10, h_main + 0.16, mat_side=1, mat_top=1)

    # Warm timber-slatted ramp along the north face of Terminal 3 (visible in Grand_Quai_Tower_South V1..V3, H5..H6)
    ramp_poly = [
        (368.0, -260.8),
        (428.0, -254.5),
        (428.0, -252.2),
        (368.0, -258.5),
    ]
    extrude_prism_in_bm(bm, ramp_poly, 0.20, 4.20, mat_side=1, mat_top=1)

    # 3) Eastern Rooftop Concrete Walkway & Lush Green Rooftop Lawn (X = 327.8..482.0) matching Satellite V7..V8, H5..H7
    east_walkway = [
        (327.6, -293.8),
        (482.0, -277.8),
        (480.0, -256.5),
        (327.6, -267.2),
    ]
    extrude_prism_in_bm(bm, east_walkway, h_main - 0.20, h_main + 0.08, mat_side=5, mat_top=5)

    # Lush green rooftop lawn (X = 331.2..476.0, Y = -290.8..-269.2) at Z = h_main + 0.22m
    rooftop_lawn = [
        (331.2, -290.6),
        (476.0, -275.6),
        (474.5, -259.5),
        (331.2, -269.5),
    ]
    extrude_prism_in_bm(bm, rooftop_lawn, h_main + 0.08, h_main + 0.24, mat_side=1, mat_top=3)

    # Sunken glass skylight atrium in rooftop lawn (X = 333.5..337.2, Y = -284.5..-275.0)
    skylight_frame = [
        (333.2, -284.8),
        (337.4, -284.4),
        (337.0, -274.8),
        (332.8, -275.2),
    ]
    extrude_prism_in_bm(bm, skylight_frame, h_main + 0.24, h_main + 0.52, mat_side=5, mat_top=2)

    # Rooftop stone seating patio (X = 345.0..360.0, Y = -285.5..-280.0)
    rooftop_patio = [
        (345.0, -285.5),
        (360.0, -284.0),
        (359.5, -279.5),
        (344.5, -281.0),
    ]
    extrude_prism_in_bm(bm, rooftop_patio, h_main + 0.24, h_main + 0.30, mat_side=5, mat_top=5)

    finalize_bm_to_mesh(bm, mesh, scale_uv=0.22)
    return obj


# --- 2. Stationnement Grand Quai / Hangar 4 (46866807) ---

def build_stationnement_grand_quai_46866807(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_46866807_Stationnement_Grand_Quai"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Terminal_White_Panels"],   # 0: White horizontal louver/composite cladding
        palette["Mat_MTL_Light_Roof_Deck"],         # 1: Light silver-grey roof deck (matches Satellite TopDown)
        palette["Mat_MTL_Window_Glass_Dark"],       # 2: Dark glass vestibule & parking portal shadow
        palette["Mat_MTL_Dark_Bronze_CurtainWall"], # 3: Dark anodized mullions & canopy soffit
        palette["Mat_MTL_White_Steel"],             # 4: Structural steel columns & diagonal V-struts
        palette["Mat_MTL_Wood_Decking"],            # 5: Warm timber-slatted ramp
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Exact 2-story height matching Grand_Quai_Terminal_Plaza (H3/H4 seam = 8.15m)
    h_main = 8.15
    h_mid_bot = 3.65
    h_mid_top = 5.85

    # Core recessed dark interior volume (provides dark depth behind glass vestibule, parking portal & open upper deck)
    core_pts = inset_polygon_toward_centroid(pts, 0.96)
    extrude_prism_in_bm(bm, core_pts, 0.0, h_main - 0.35, mat_side=2, mat_top=None)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 2.0:
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len

        # 1) Ground floor (Z = 0.0m..3.65m): Glass lobby on west bays + dark parking portal on east bays
        # Central white architectural pier at X ~ 344..348 (V4/V5 in Grand_Quai_Terminal_Plaza)
        add_box_between(bm, p1, p2, 0.0, 0.25, thickness=0.55, offset_out=0.05, mat_idx=0)
        # Vertical curtain-wall mullions every 1.8m on the ground level (Z = 0.25m..3.65m)
        n_mull = max(2, int(round(seg_len / 1.8)))
        for m_idx in range(n_mull + 1):
            m_pos = min(seg_len, m_idx * (seg_len / n_mull))
            mp1 = (p1[0] + dx * max(0.0, m_pos - 0.06), p1[1] + dy * max(0.0, m_pos - 0.06))
            mp2 = (p1[0] + dx * min(seg_len, m_pos + 0.06), p1[1] + dy * min(seg_len, m_pos + 0.06))
            add_box_between(bm, mp1, mp2, 0.25, h_mid_bot, thickness=0.28, offset_out=0.02, mat_idx=3)
        # Horizontal transoms across ground level storefront
        for z_tr in (1.35, 2.55):
            add_box_between(bm, p1, p2, z_tr, z_tr + 0.08, thickness=0.26, offset_out=0.02, mat_idx=3)

        n_cols = max(2, int(round(seg_len / 4.2)))
        for c in range(n_cols + 1):
            pos = min(seg_len, c * (seg_len / n_cols))
            cp1 = (p1[0] + dx * max(0.0, pos - 0.22), p1[1] + dy * max(0.0, pos - 0.22))
            cp2 = (p1[0] + dx * min(seg_len, pos + 0.22), p1[1] + dy * min(seg_len, pos + 0.22))
            # Wide solid white pier near X = 345
            cx_col = 0.5 * (cp1[0] + cp2[0])
            if 343.0 <= cx_col <= 348.5:
                wp1 = (p1[0] + dx * max(0.0, pos - 1.6), p1[1] + dy * max(0.0, pos - 1.6))
                wp2 = (p1[0] + dx * min(seg_len, pos + 1.6), p1[1] + dy * min(seg_len, pos + 1.6))
                add_box_between(bm, wp1, wp2, 0.0, h_mid_top, thickness=0.65, offset_out=0.12, mat_idx=0)
            else:
                add_box_between(bm, cp1, cp2, 0.0, h_main - 0.25, thickness=0.38, offset_out=0.04, mat_idx=4)

        # 2) Mid-Facade White Horizontal Louver Cladding Band (Z = 3.65m..5.85m, H4/H5)
        add_box_between(bm, p1, p2, h_mid_bot, h_mid_top, thickness=0.62, offset_out=0.10, mat_idx=0)
        add_box_between(bm, p1, p2, h_mid_bot - 0.12, h_mid_bot + 0.06, thickness=0.72, offset_out=0.14, mat_idx=3)
        add_box_between(bm, p1, p2, h_mid_top - 0.08, h_mid_top + 0.08, thickness=0.72, offset_out=0.14, mat_idx=3)
        # Horizontal 3D louver blades every 0.28m across the mid-facade band (Z = 3.65m..5.85m)
        z_louver = h_mid_bot + 0.18
        louver_idx = 0
        while z_louver < h_mid_top - 0.12:
            l_mat = 3 if (louver_idx % 2 == 0) else 4
            add_box_between(bm, p1, p2, z_louver, z_louver + 0.07, thickness=0.76, offset_out=0.18, mat_idx=l_mat)
            z_louver += 0.28
            louver_idx += 1

        # 3) Upper Open-Air Covered Deck & Steel-Truss Roof Canopy (Z = 5.85m..8.15m, H3/H4)
        # Diagonal steel V-struts every 4.2m in the upper open deck (Z = 5.85m..7.75m)
        for c in range(n_cols):
            s0 = c * (seg_len / n_cols)
            s1 = (c + 1) * (seg_len / n_cols)
            sm = 0.5 * (s0 + s1)
            for step_v in range(4):
                f0 = step_v / 4.0
                f1 = (step_v + 1) / 4.0
                # Left arm of V-strut (bottom-center sm -> top-left s0)
                va1 = (p1[0] + dx * (sm + (s0 - sm) * f0), p1[1] + dy * (sm + (s0 - sm) * f0))
                va2 = (p1[0] + dx * (sm + (s0 - sm) * f1), p1[1] + dy * (sm + (s0 - sm) * f1))
                # Right arm of V-strut (bottom-center sm -> top-right s1)
                vb1 = (p1[0] + dx * (sm + (s1 - sm) * f0), p1[1] + dy * (sm + (s1 - sm) * f0))
                vb2 = (p1[0] + dx * (sm + (s1 - sm) * f1), p1[1] + dy * (sm + (s1 - sm) * f1))
                zv0 = h_mid_top + f0 * (7.75 - h_mid_top)
                zv1 = h_mid_top + f1 * (7.75 - h_mid_top)
                add_box_between(bm, va1, va2, zv0, zv1, thickness=0.22, offset_out=0.06, mat_idx=4)
                add_box_between(bm, vb1, vb2, zv0, zv1, thickness=0.22, offset_out=0.06, mat_idx=4)
        # Safety guardrail at Z = 6.55m & intermediate rails
        add_box_between(bm, p1, p2, h_mid_top + 0.65, h_mid_top + 0.78, thickness=0.16, offset_out=0.05, mat_idx=4)
        add_box_between(bm, p1, p2, h_mid_top + 0.35, h_mid_top + 0.43, thickness=0.12, offset_out=0.05, mat_idx=3)
        # Overhanging roof canopy fascia (Z = 7.75m..8.15m) with dark soffit (Z = 7.55m..7.75m)
        add_box_between(bm, p1, p2, h_main - 0.60, h_main - 0.40, thickness=0.85, offset_out=0.15, mat_idx=3)
        add_box_between(bm, p1, p2, h_main - 0.40, h_main, thickness=0.92, offset_out=0.22, mat_idx=0)

    # Full flat light silver-grey roof deck (Z = 7.85m..8.08m) matching Satellite TopDown V7..V8, H1..H3
    roof_pts = inset_polygon_toward_centroid(pts, 0.985)
    extrude_prism_in_bm(bm, roof_pts, h_main - 0.30, h_main - 0.06, mat_side=1, mat_top=1)

    # Warm timber-slatted ramp & boardwalk terrace on the West end (X = 324..333, Y = -236..-220)
    west_ramp = [
        (324.0, -236.2),
        (333.0, -235.5),
        (331.0, -218.0),
        (324.0, -219.0),
    ]
    extrude_prism_in_bm(bm, west_ramp, 0.20, 4.20, mat_side=5, mat_top=5)
    # Dark glass & steel pavilion above the west ramp (Z = 4.20m..6.80m)
    west_pav = [
        (325.0, -235.8),
        (332.5, -234.8),
        (331.0, -222.0),
        (325.0, -223.0),
    ]
    extrude_prism_in_bm(bm, west_pav, 4.20, 6.80, mat_side=2, mat_top=1)

    finalize_bm_to_mesh(bm, mesh, scale_uv=0.22)
    return obj


# --- 3. Gare Maritime Iberville (677248941) ---

def build_gare_maritime_iberville_677248941(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_677248941_Gare_Maritime_Iberville"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Terminal_White_Panels"],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_Dark_Bronze_CurtainWall"],
        palette["Mat_MTL_Wood_Decking"],
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()
    h_main = 7.50
    extrude_prism_in_bm(bm, pts, 0.0, h_main, mat_side=0, mat_top=None)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.5:
            continue
        add_box_between(bm, p1, p2, 0.0, 0.65, thickness=0.60, offset_out=0.12, mat_idx=0)
        add_box_between(bm, p1, p2, 0.65, h_main - 0.65, thickness=0.14, offset_out=-0.50, mat_idx=1)
        add_box_between(bm, p1, p2, h_main - 0.65, h_main, thickness=0.65, offset_out=0.15, mat_idx=2)

    roof_pts = inset_polygon_toward_centroid(pts, 0.94)
    extrude_prism_in_bm(bm, roof_pts, h_main - 0.30, h_main - 0.05, mat_side=3, mat_top=3)

    finalize_bm_to_mesh(bm, mesh, scale_uv=0.25)
    return obj


# --- 4. Iconic 65m Port of Montreal Observation Tower (Tour du Port de Montréal) ---

def _add_tower_geometry(bm, cx, cy, tower_h=65.0):
    # Materials: 0=Concrete, 1=Tower_Glass, 2=Gold_Cage, 3=White_Steel, 4=Wood_Decking
    # Sleek Blue-Grey Reflective Glass Shaft (Z = 0.0m..50.0m)
    cw = 4.6
    shaft_pts = [
        (cx - cw, cy - cw),
        (cx + cw, cy - cw),
        (cx + cw, cy + cw),
        (cx - cw, cy + cw),
    ]
    extrude_prism_in_bm(bm, shaft_pts, 0.0, 50.0, mat_side=1, mat_top=0)

    # Internal Spiral Golden Staircase & Central Concrete Core
    add_cylinder_in_bm(bm, (cx, cy), 0.0, 52.0, r_bot=1.8, r_top=1.8, n_seg=12, mat_idx=0)
    for z_step in range(2, 48, 2):
        ang0 = math.radians(z_step * 28.0)
        ang1 = math.radians((z_step + 2) * 28.0)
        sp1 = (cx + 3.4 * math.cos(ang0), cy + 3.4 * math.sin(ang0))
        sp2 = (cx + 3.4 * math.cos(ang1), cy + 3.4 * math.sin(ang1))
        add_box_between(bm, sp1, sp2, float(z_step), float(z_step) + 1.4, thickness=0.85, offset_out=0.0, mat_idx=2)

    # Horizontal dark curtain-wall mullions every 4.0m
    for z_m in range(4, 50, 4):
        for k in range(4):
            p1, p2 = shaft_pts[k], shaft_pts[(k + 1) % 4]
            add_box_between(bm, p1, p2, float(z_m), float(z_m) + 0.25, thickness=0.35, offset_out=0.08, mat_idx=3)

    # Signature Cantilevered Golden-Bronze Diagonal Lattice Observation Cage at Crown (Z = 47.5m..62.5m)
    ow = 7.8
    od = 6.8
    cage_pts = [
        (cx - ow, cy - od),
        (cx + ow + 3.2, cy - od),
        (cx + ow + 3.2, cy + od),
        (cx - ow, cy + od),
    ]
    # Glass observation enclosure inside the golden cage
    inner_obs = inset_polygon_toward_centroid(cage_pts, 0.88)
    extrude_prism_in_bm(bm, inner_obs, 48.0, 60.5, mat_side=1, mat_top=0)

    # Golden-bronze horizontal ring beams & vertical/diagonal lattice struts
    for z_ring in (47.5, 51.5, 55.5, 59.5, 62.5):
        for k in range(4):
            p1, p2 = cage_pts[k], cage_pts[(k + 1) % 4]
            add_box_between(bm, p1, p2, z_ring, z_ring + 0.65, thickness=0.65, offset_out=0.0, mat_idx=2)

    for k in range(4):
        p1, p2 = cage_pts[k], cage_pts[(k + 1) % 4]
        seg_l = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        dx, dy = (p2[0] - p1[0]) / seg_l, (p2[1] - p1[1]) / seg_l
        n_diag = 5
        for d_i in range(n_diag + 1):
            pos = (d_i / n_diag) * seg_l
            dp1 = (p1[0] + dx * max(0.0, pos - 0.35), p1[1] + dy * max(0.0, pos - 0.35))
            dp2 = (p1[0] + dx * min(seg_l, pos + 0.35), p1[1] + dy * min(seg_l, pos + 0.35))
            add_box_between(bm, dp1, dp2, 47.5, 62.5, thickness=0.55, offset_out=0.05, mat_idx=2)

    # Navigation spire (Z = 62.5m..65.0m)
    add_cylinder_in_bm(bm, (cx, cy), 62.5, tower_h, r_bot=0.55, r_top=0.12, n_seg=10, mat_idx=2)


def build_port_observation_tower_995326034(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_995326034_Tour_Port_De_Montreal"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Precast_Concrete"],   # 0
        palette["Mat_MTL_Tower_Glass"],        # 1
        palette["Mat_MTL_Tower_Gold_Cage"],    # 2
        palette["Mat_MTL_White_Steel"],        # 3
        palette["Mat_MTL_Wood_Decking"],       # 4
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Base terrace at OSM footprint (579.4, -262.1)
    extrude_prism_in_bm(bm, pts, 0.0, 4.20, mat_side=0, mat_top=4)

    # 2. Single Iconic 65m Port of Montreal Observation Tower positioned at (445.0, -257.5)
    #    so it aligns at V1..V2, H2..H5 in Grand_Quai_Tower_South AND appears as a single landmark tower in Overview_Cam!
    _add_tower_geometry(bm, 445.0, -257.5, tower_h=65.0)

    finalize_bm_to_mesh(bm, mesh, scale_uv=0.20)
    return obj


# --- 5. Quai Alexandra Entrance Pavilion (300595274) ---

def build_entrance_pavilion_300595274(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None

    name = "MTL_Owned_300595274_Entrance_Pavilion"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_PierreGrise_Limestone"], # 0: Warm grey stone side wings
        palette["Mat_MTL_Window_Glass_Dark"],      # 1: Recessed glazing
        palette["Mat_MTL_Verdigris_Copper"],       # 2: Patinated green copper center roof (matches Satellite V2, H1/H2)
        palette["Mat_MTL_Light_Roof_Deck"],        # 3: Light grey stone side roofs
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()
    h_main = 4.20
    extrude_prism_in_bm(bm, pts, 0.20, h_main, mat_side=0, mat_top=None)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 2.0:
            add_box_between(bm, p1, p2, 0.80, 3.40, thickness=0.14, offset_out=-0.46, mat_idx=1)

    # Side wing flat stone roofs
    roof_pts = inset_polygon_toward_centroid(pts, 0.94)
    extrude_prism_in_bm(bm, roof_pts, h_main - 0.20, h_main + 0.08, mat_side=0, mat_top=3)

    # Central green patinated copper roof cap matching Satellite TopDown (X = 261.4..267.5, Y = -214.3..-206.1)
    copper_roof = [
        (261.4, -214.2),
        (267.5, -213.6),
        (266.8, -206.2),
        (261.2, -206.8),
    ]
    extrude_prism_in_bm(bm, copper_roof, h_main + 0.08, h_main + 0.45, mat_side=2, mat_top=2)

    finalize_bm_to_mesh(bm, mesh, scale_uv=0.25)
    return obj


# --- 6. Moored Multi-Deck Ocean Cruise Liner (Grand Quai South/West Berth) ---

def build_moored_cruise_ship(palette, collection):
    name = "MTL_Owned_Grand_Quai_Moored_Cruise_Liner"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    materials = [
        palette["Mat_MTL_Ship_Navy_Hull"],          # 0: Deep navy lower hull
        palette["Mat_MTL_White_Steel"],             # 1: Crisp white cruise ship superstructure
        palette["Mat_MTL_Window_Glass_Dark"],       # 2: Continuous dark bridge & cabin window ribbons
        palette["Mat_MTL_Tower_Gold_Cage"],         # 3: Gold livery stripe & lifeboats
        palette["Mat_MTL_Wood_Decking"],            # 4: Teak lido deck
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Moored along the South Berth of Grand Quai at X = 362.5..535.0, Y = -326.0..-296.0
    # (Starts at X = 362.5 so Satellite TopDown X <= 361.09 keeps open dark water in H7..H8,
    #  while Grand_Quai_Tower_South sees the ship hull & decks in V7..V8 and Overview_Cam sees the full liner!)
    hull_pts = [
        (362.5, -310.0),  # Pointed bow tip
        (382.0, -324.0),
        (525.0, -310.0),
        (534.0, -304.0),
        (532.0, -292.0),
        (520.0, -286.0),
        (380.0, -300.0),
    ]
    extrude_prism_in_bm(bm, hull_pts, -2.20, 4.50, mat_side=0, mat_top=1)
    # White upper hull & gold sheer stripe (Z = 4.50m..9.20m)
    extrude_prism_in_bm(bm, hull_pts, 4.50, 5.20, mat_side=3, mat_top=None)
    extrude_prism_in_bm(bm, hull_pts, 5.20, 9.20, mat_side=1, mat_top=4)

    # 5 Tiered Passenger Balcony Decks (Z = 9.20m..25.50m)
    for d_idx in range(5):
        z0 = 9.20 + d_idx * 3.20
        z1 = z0 + 3.20
        inset_f = 0.92 - d_idx * 0.04
        deck_pts = inset_polygon_toward_centroid(hull_pts, inset_f)
        # Cabin glass band + white balcony rail fascia
        extrude_prism_in_bm(bm, deck_pts, z0, z0 + 2.10, mat_side=2, mat_top=None)
        extrude_prism_in_bm(bm, deck_pts, z0 + 2.10, z1, mat_side=1, mat_top=4)

    # Navigation Bridge & Forward Observation Lounge (streamlined within hull beam)
    bridge_pts = [
        (382.0, -315.5),
        (402.0, -313.5),
        (400.5, -299.5),
        (380.5, -301.5),
    ]
    extrude_prism_in_bm(bm, bridge_pts, 25.20, 28.40, mat_side=2, mat_top=1)

    # Signature Raked Cruise Ship Funnel (X = 455, Y = -305, Z = 25.2m..35.5m)
    add_cylinder_in_bm(bm, (455.0, -305.0), 25.20, 34.00, r_bot=4.8, r_top=3.6, n_seg=16, mat_idx=1)
    add_cylinder_in_bm(bm, (455.0, -305.0), 34.00, 35.80, r_bot=3.6, r_top=3.2, n_seg=16, mat_idx=0)

    finalize_bm_to_mesh(bm, mesh, scale_uv=0.20)
    return obj


# --- 7. Canada Customs (87415541), Habitat 67 (440195613) & Historic Port Buildings ---

def build_canada_customs_87415541(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None
    name = "MTL_Owned_87415541_Douane"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    materials = [
        palette["Mat_MTL_PierreGrise_Limestone"],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_Dark_Bronze_CurtainWall"],
        palette["Mat_MTL_Light_Roof_Deck"],
    ]
    for m in materials:
        obj.data.materials.append(m)
    bm = bmesh.new()
    h_main = 26.0
    extrude_prism_in_bm(bm, pts, 0.0, h_main, mat_side=0, mat_top=None)
    for i in range(len(pts)):
        p1, p2 = pts[i], pts[(i + 1) % len(pts)]
        if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 3.0:
            for fl in range(6):
                zs = 2.0 + fl * 3.8
                add_box_between(bm, p1, p2, zs, zs + 2.0, thickness=0.14, offset_out=-0.48, mat_idx=1)
    roof_pts = inset_polygon_toward_centroid(pts, 0.92)
    extrude_prism_in_bm(bm, roof_pts, h_main - 0.35, h_main - 0.10, mat_side=3, mat_top=3)
    finalize_bm_to_mesh(bm, mesh, scale_uv=0.25)
    return obj


def build_habitat_67_440195613(bldg_data, palette, collection):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None
    name = "MTL_Owned_440195613_Habitat_67"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    materials = [
        palette["Mat_MTL_Precast_Concrete"],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_Grass_Lawn_PBR"],
    ]
    for m in materials:
        obj.data.materials.append(m)
    bm = bmesh.new()
    extrude_prism_in_bm(bm, pts, 0.0, 7.0, mat_side=0, mat_top=None)
    for factor, z0, z1 in [(0.90, 7.0, 14.0), (0.78, 14.0, 22.0), (0.64, 22.0, 30.0), (0.48, 30.0, 37.0)]:
        t_pts = inset_polygon_toward_centroid(pts, factor)
        extrude_prism_in_bm(bm, t_pts, z0, z1, mat_side=0, mat_top=2)
    finalize_bm_to_mesh(bm, mesh, scale_uv=0.25)
    return obj


def build_historic_port_building(bldg_data, palette, collection, prefix, height=11.5, n_floors=3, mat_wall_key="Mat_MTL_Heritage_RedBrick"):
    pts = ensure_ccw(clean_poly_pts(bldg_data["coords_xy"]))
    if len(pts) < 3:
        return None
    bid = bldg_data["id"]
    name = f"MTL_Owned_{bid}_{prefix}"
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    materials = [
        palette[mat_wall_key],
        palette["Mat_MTL_Window_Glass_Dark"],
        palette["Mat_MTL_PierreGrise_Limestone"],
        palette["Mat_MTL_Slate_Roof_Dark"],
    ]
    for m in materials:
        obj.data.materials.append(m)
    bm = bmesh.new()
    extrude_prism_in_bm(bm, pts, 0.0, height, mat_side=0, mat_top=None)
    floor_h = height / max(1, n_floors)
    for i in range(len(pts)):
        p1, p2 = pts[i], pts[(i + 1) % len(pts)]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 2.2:
            continue
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        n_bays = max(1, int(round(seg_len / 3.5)))
        bay_w = seg_len / n_bays
        for b in range(n_bays):
            s0 = (b + 0.22) * bay_w
            s1 = (b + 0.78) * bay_w
            wp1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            wp2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            for fl in range(n_floors):
                zs = 0.8 + fl * floor_h + 0.35
                zh = min(height - 0.45, zs + floor_h * 0.55)
                if zh > zs:
                    add_box_between(bm, wp1, wp2, zs, zh, thickness=0.12, offset_out=-0.46, mat_idx=1)
    roof_pts = inset_polygon_toward_centroid(pts, 0.90)
    extrude_prism_in_bm(bm, roof_pts, height - 0.30, height - 0.08, mat_side=3, mat_top=3)
    finalize_bm_to_mesh(bm, mesh, scale_uv=0.25)
    return obj


# --- 8. Watertight Ground, Satellite-Matched Lawns, Crosswalks, Quays & 2K PBR Water ---

def build_ground_quays_and_streets(dossier, palette, collection_owned):
    mesh = bpy.data.meshes.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}", mesh)
    collection_owned.objects.link(obj)

    materials = [
        palette["Mat_MTL_Plaza_Light_Granite"],     # 0: Light cream/beige granite pier promenade
        palette["Mat_MTL_Street_Asphalt"],          # 1: Clean asphalt roadways
        palette["Mat_MTL_Granite_Plinth"],          # 2: Stepped granite quay retaining walls
        palette["Mat_MTL_Water_Basin"],             # 3: 2K PBR St. Lawrence River & harbor water
        palette["Mat_MTL_Grass_Lawn_PBR"],          # 4: 2K PBR Leafy Grass park & pier lawns
        palette["Mat_PH_Gravel_Path"],              # 5: Crushed-stone / gravel paths & railway bed
        palette["Mat_PH_Red_Brick_Pavers"],         # 6: Terracotta brick pavilion plaza
        palette["Mat_MTL_Crosswalk_White"],         # 7: White zebra crosswalk markings
        palette["Mat_MTL_CastIron_Black"],          # 8: Cast-iron mooring bollards & park fences
        palette["Mat_MTL_Wood_Decking"],            # 9: Wooden tourist signboard & planter trim
        palette["Mat_MTL_Forrest_Mulch"] if "Mat_MTL_Forrest_Mulch" in palette else palette["Mat_PH_Forest_Ground"], # 10: Mulch planter beds
    ]
    for m in materials:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Strict non-overlapping Z hierarchy (Zero coplanar faces in Cycles!):
    # Z = -2.20m : Subdivided wave-displaced 2K PBR water basin
    # Z = -0.30..0.00m : Base asphalt roadway stratum
    # Z = +0.025m : Pier light-granite promenade apron (X > 294.5)
    # Z = +0.045m : Central pier asphalt roadway & entrance intersection
    # Z = +0.065m : White zebra crosswalk stripes
    # Z = +0.160m : Raised granite sidewalks & curbs
    # Z = +0.195m : Lush green park lawns (Place des Commencements & North Park)
    # Z = +0.225m : Mulch planter beds & railway ballast
    # Z = +0.245m : Single-sided +Z crushed-stone / gravel park paths

    # 1. Wave-Displaced 2K PBR Water Surface (Z = -2.20m) covering North, South & East Basins
    water_patches = [
        # South Basin (Bassin Alexandra, Y = -430..-304.5)
        (298.0, 720.0, -430.0, -304.5, 24, 10),
        # North Basin (Y = -199.5..-80.0)
        (296.0, 720.0, -199.5, -80.0, 24, 10),
        # East River Channel (X = 658..760)
        (658.0, 760.0, -304.5, -199.5, 8, 8),
        # Small North Park Canal Basin (visible in Satellite TopDown V2, H1: X = 258.5..265.8, Y = -205.5..-185.0)
        (258.5, 265.8, -205.5, -185.0, 4, 6),
    ]
    for wx0, wx1, wy0, wy1, nx_sub, ny_sub in water_patches:
        dx = (wx1 - wx0) / nx_sub
        dy = (wy1 - wy0) / ny_sub
        for ix in range(nx_sub):
            for iy in range(ny_sub):
                x0, x1 = wx0 + ix * dx, wx0 + (ix + 1) * dx
                y0, y1 = wy0 + iy * dy, wy0 + (iy + 1) * dy
                pts_w = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
                verts_w = []
                for px, py in pts_w:
                    wz = -2.20 + 0.06 * math.sin(px * 0.35 + py * 0.25) + 0.04 * math.cos(px * 0.70 - py * 0.50)
                    verts_w.append(bm.verts.new((px, py, wz)))
                try:
                    fw = bm.faces.new(verts_w)
                    fw.material_index = 3
                except ValueError:
                    pass

    # 2. Base Asphalt Roadway Stratum (Z = -0.30m..0.00m) covering Western Streets & Intersection
    west_road_base = [
        (160.0, -340.0),
        (305.0, -340.0),
        (305.0, -130.0),
        (160.0, -130.0),
    ]
    extrude_prism_in_bm(bm, west_road_base, -0.30, 0.00, mat_side=1, mat_top=1)

    # Southern Port & Habitat 67 Ground Strata
    extrude_prism_in_bm(bm, [(40.0, -610.0), (310.0, -610.0), (310.0, -380.0), (40.0, -380.0)], -0.30, 0.00, mat_side=1, mat_top=1)
    extrude_prism_in_bm(bm, [(940.0, -700.0), (1070.0, -700.0), (1070.0, -380.0), (940.0, -380.0)], -0.30, 0.00, mat_side=0, mat_top=0)

    # 3. Light Cream/Beige Granite Pier Promenade Apron (Z = -0.25m..+0.025m)
    quai_pier_pts = [
        (294.5, -304.8),
        (595.99, -273.76),
        (657.47, -267.15),
        (678.36, -167.10),
        (673.96, -160.34),
        (588.45, -169.85),
        (294.5, -199.8),
    ]
    extrude_prism_in_bm(bm, quai_pier_pts, -0.25, 0.025, mat_side=2, mat_top=0)

    # 4. Central Pier Asphalt Roadway & Entrance Plaza (Z = +0.025m..+0.048m)
    # Covers both Grand_Quai_Terminal_Plaza (355, -247.7), Grand_Quai_Tower_South (346.6, -248.8),
    # and Promenade_du_Grand_Quai_Roof (261.9, -247.6) so foreground H6..H8 is clean asphalt!
    pier_roadway_pts = [
        (246.0, -266.5),
        (305.0, -266.5),
        (585.0, -238.5),
        (583.0, -220.0),
        (328.0, -236.5),
        (246.0, -243.5),
    ]
    extrude_prism_in_bm(bm, pier_roadway_pts, 0.01, 0.048, mat_side=1, mat_top=1)
    # Concrete expansion joint strips in the foreground plaza/roadway (X = 330..385, Y = -255..-236, Z = 0.052m)
    for jx in range(330, 386, 3):
        add_box_between(bm, (float(jx), -255.0), (float(jx) - 1.5, -236.0), 0.048, 0.054, thickness=0.05, offset_out=0.0, mat_idx=0)
    for jy in range(-255, -235, 3):
        add_box_between(bm, (330.0, float(jy)), (385.0, float(jy) + 5.2), 0.048, 0.054, thickness=0.05, offset_out=0.0, mat_idx=0)

    # 5. Stepped Granite Quay Retaining Walls (Z = -2.50m..+0.16m) & Mooring Bollards
    quay_edges = [
        ((296.0, -330.0), (296.0, -304.8)),
        ((296.0, -304.8), (595.99, -273.76)),
        ((595.99, -273.76), (657.47, -267.15)),
        ((657.47, -267.15), (678.36, -167.10)),
        ((678.36, -167.10), (588.45, -169.85)),
        ((588.45, -169.85), (296.0, -199.8)),
        ((296.0, -199.8), (296.0, -140.0)),
    ]
    for p1, p2 in quay_edges:
        add_box_between(bm, p1, p2, -2.50, 0.025, thickness=0.90, offset_out=0.45, mat_idx=2)
        add_box_between(bm, p1, p2, 0.025, 0.165, thickness=0.65, offset_out=0.32, mat_idx=0)
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        seg_len = math.hypot(dx, dy)
        n_bol = max(1, int(round(seg_len / 22.0)))
        for b in range(n_bol + 1):
            pos = min(seg_len, b * (seg_len / n_bol))
            bx = p1[0] + (dx / seg_len) * pos
            by = p1[1] + (dy / seg_len) * pos
            add_cylinder_in_bm(bm, (bx, by), 0.165, 0.78, r_bot=0.26, r_top=0.32, n_seg=10, mat_idx=8)

    # Floating pontoon fender at South Quay (visible in Satellite TopDown V7, H7: X = 339..344, Y = -307..-305)
    extrude_prism_in_bm(bm, [(338.8, -307.2), (344.2, -306.8), (344.0, -304.8), (338.6, -305.2)], -2.15, -1.65, mat_side=1, mat_top=1)

    # 6. Satellite-Matched Lush Green Park Lawns (Z = +0.195m, Mat_MTL_Grass_Lawn_PBR)
    # 6a. Place des Commencements South Park Lawn (V2..V4, H5..H8: X = 247.0..285.5, Y = -326.0..-266.8)
    south_park_lawn = [
        (247.0, -326.0),
        (285.5, -326.0),
        (276.5, -266.8),
        (247.0, -266.8),
    ]
    extrude_prism_in_bm(bm, south_park_lawn, 0.01, 0.195, mat_side=0, mat_top=4)

    # 6b. North Park Lawn (V2..V3, H1..H4: X = 247.0..277.0, Y = -243.2..-150.0)
    north_park_lawn = [
        (247.0, -243.2),
        (276.8, -243.2),
        (282.0, -150.0),
        (247.0, -150.0),
    ]
    extrude_prism_in_bm(bm, north_park_lawn, 0.01, 0.195, mat_side=0, mat_top=4)

    # 6c. West Grass Verges along Rue de la Commune Bikeway (V1: X = 234.5..238.5)
    extrude_prism_in_bm(bm, [(234.5, -326.0), (238.5, -326.0), (238.5, -266.8), (234.5, -266.8)], 0.01, 0.195, mat_side=0, mat_top=4)
    extrude_prism_in_bm(bm, [(234.5, -243.2), (238.5, -243.2), (238.5, -150.0), (234.5, -150.0)], 0.01, 0.195, mat_side=0, mat_top=4)

    # 6d. Pier Entrance Triangular Garden Lawn (V5..V6, H1..H2: X = 301.0..326.5, Y = -226.0..-205.5)
    pier_north_lawn = [
        (301.0, -218.0),
        (312.5, -226.5),
        (326.5, -216.0),
        (325.5, -205.5),
        (301.0, -208.0),
    ]
    extrude_prism_in_bm(bm, pier_north_lawn, 0.025, 0.195, mat_side=0, mat_top=4)

    # 6e. Pier Roadway Median & Flanking Planter Strips (strictly X = 301..335 matching Satellite TopDown)
    # North roadway lawn strip along Hangar 4 base (Y = -238.2..-236.2)
    extrude_prism_in_bm(bm, [(301.0, -238.2), (335.0, -235.2), (335.0, -233.5), (301.0, -236.2)], 0.048, 0.195, mat_side=0, mat_top=4)
    # South roadway planter strip along Terminal 3 (X = 301..335, Y = -258.8..-256.5)
    extrude_prism_in_bm(bm, [(301.0, -258.8), (335.0, -255.8), (335.0, -254.0), (301.0, -256.8)], 0.048, 0.195, mat_side=0, mat_top=4)

    # 7. Railway Corridor Ballast & Tracks (V1..V2: X = 238.5..247.0, Y = -326.0..-150.0, Z = +0.08m)
    extrude_prism_in_bm(bm, [(238.5, -326.0), (247.0, -326.0), (247.0, -150.0), (238.5, -150.0)], 0.01, 0.08, mat_side=5, mat_top=5)
    for rx in (240.2, 241.6, 243.8, 245.2):
        add_box_between(bm, (rx, -326.0), (rx, -150.0), 0.08, 0.14, thickness=0.14, offset_out=0.0, mat_idx=8)

    # 8. Terracotta Red-Brick Pavilion Plaza (V2..V3, H1..H2: X = 256.5..277.0, Y = -216.5..-202.5, Z = +0.215m)
    brick_plaza = [
        (256.5, -216.5),
        (277.0, -216.5),
        (277.0, -202.5),
        (256.5, -202.5),
    ]
    extrude_prism_in_bm(bm, brick_plaza, 0.195, 0.215, mat_side=6, mat_top=6)

    # Two parallel trimmed green hedges in North Park (X = 259.5..261.8 and 265.2..267.5, Y = -240.0..-216.8)
    extrude_prism_in_bm(bm, [(259.5, -240.0), (261.8, -240.0), (261.8, -216.8), (259.5, -216.8)], 0.195, 1.25, mat_side=4, mat_top=4)
    extrude_prism_in_bm(bm, [(265.2, -240.0), (267.5, -240.0), (267.5, -216.8), (265.2, -216.8)], 0.195, 1.25, mat_side=4, mat_top=4)

    # 9. Single-Sided +Z Crushed-Stone / Limestone Park Walkways (Z = +0.245m..0.255m, zero coplanar faces)
    north_path = [
        (250.5, -243.0),
        (254.5, -243.0),
        (255.5, -185.0),
        (251.5, -185.0),
    ]
    add_top_face_in_bm(bm, north_path, 0.245, mat_idx=5)

    south_path = [
        (257.0, -326.0),
        (261.0, -326.0),
        (271.5, -267.0),
        (267.5, -267.0),
    ]
    add_top_face_in_bm(bm, south_path, 0.250, mat_idx=5)

    # 10. Crisp White Zebra Crosswalk Stripes at Central Intersection (V3..V4, H4..H5, Z = +0.065m)
    # N-S Crosswalk across Entrance Road (X = 273.0..276.8, Y = -265.5..-244.5)
    for cw_i in range(11):
        cy0 = -265.0 + cw_i * 1.85
        cy1 = cy0 + 0.95
        add_top_face_in_bm(bm, [(273.0, cy0), (276.8, cy0), (276.8, cy1), (273.0, cy1)], 0.065, mat_idx=7)
    # E-W Crosswalk North (X = 277.5..293.5, Y = -246.2..-243.2)
    for cw_i in range(8):
        cx0 = 278.0 + cw_i * 1.95
        cx1 = cx0 + 1.00
        add_top_face_in_bm(bm, [(cx0, -246.2), (cx1, -246.2), (cx1, -243.2), (cx0, -243.2)], 0.068, mat_idx=7)
    # Diagonal Crosswalk South (X = 277.0..293.0, Y = -267.5..-261.5)
    for cw_i in range(8):
        cx0 = 277.5 + cw_i * 1.95
        cx1 = cx0 + 1.00
        cy_base = -267.5 + cw_i * 0.65
        add_top_face_in_bm(bm, [(cx0, cy_base), (cx1, cy_base + 0.3), (cx1, cy_base + 3.1), (cx0, cy_base + 2.8)], 0.070, mat_idx=7)
    # White Railway Level Crossing Boxes (V1: X = 236.5..247.2, Y = -265.5..-245.5)
    add_top_face_in_bm(bm, [(236.5, -265.5), (241.2, -265.5), (241.2, -245.5), (236.5, -245.5)], 0.088, mat_idx=7)
    add_top_face_in_bm(bm, [(242.5, -265.5), (247.2, -265.5), (247.2, -245.5), (242.5, -245.5)], 0.088, mat_idx=7)

    # 11. Camera-Specific Foreground Details for Street View Alignment:
    # A) Promenade_du_Grand_Quai_Roof (cam = 261.92, -247.61, heading 105°):
    #    Left foreground concrete sidewalk & grassy curb (V1..V3, H6..H8) + Wooden Tourist Map Signboard (V1, H5..H6)
    prom_left_curb = [
        (262.5, -246.2),
        (275.5, -249.2),
        (276.5, -243.2),
        (262.5, -242.0),
    ]
    extrude_prism_in_bm(bm, prom_left_curb, 0.048, 0.165, mat_side=0, mat_top=0)
    prom_left_grass = [
        (263.5, -245.6),
        (272.5, -247.5),
        (273.5, -243.5),
        (263.5, -242.5),
    ]
    extrude_prism_in_bm(bm, prom_left_grass, 0.165, 0.215, mat_side=0, mat_top=4)
    # Wooden Tourist Map Signboard at (267.5, -245.2).. (269.0, -246.2) -> V1, H5..H6
    add_box_between(bm, (267.5, -245.2), (269.0, -246.2), 0.215, 1.35, thickness=0.18, offset_out=0.0, mat_idx=9)
    add_box_between(bm, (267.3, -245.0), (269.2, -246.4), 1.35, 1.50, thickness=0.36, offset_out=0.0, mat_idx=9)

    # B) Rue_de_la_Commune_Alexandra_Entrance (cam = 212.54, -162.74, heading 123.2°):
    #    Foreground granite sidewalk & curb (H6..H8), two waste bins at V3..V4 (220.4, -165.6),
    #    low black park fence & brown mulch shrub bed in H5..H6 (X = 218..234, Y = -176..-162)
    commune_sidewalk = [
        (205.0, -182.0),
        (225.0, -172.0),
        (222.0, -152.0),
        (205.0, -155.0),
    ]
    extrude_prism_in_bm(bm, commune_sidewalk, 0.00, 0.165, mat_side=0, mat_top=0)
    # Two wooden/cast-iron waste bins next to the V3 lamp post at (220.3, -165.5) and (220.8, -166.1)
    add_cylinder_in_bm(bm, (220.3, -165.5), 0.165, 1.05, r_bot=0.28, r_top=0.30, n_seg=10, mat_idx=9)
    add_cylinder_in_bm(bm, (220.8, -166.1), 0.165, 1.05, r_bot=0.28, r_top=0.30, n_seg=10, mat_idx=8)
    # Mulch planter bed & low black ornamental fence behind sidewalk (V1..V6, H5..H6)
    mulch_bed = [
        (221.5, -175.0),
        (234.0, -172.0),
        (232.0, -158.0),
        (220.5, -161.0),
    ]
    extrude_prism_in_bm(bm, mulch_bed, 0.01, 0.225, mat_side=0, mat_top=10)
    add_box_between(bm, (220.5, -161.0), (221.5, -175.0), 0.225, 0.92, thickness=0.08, offset_out=0.0, mat_idx=8)

    # C) Grand_Quai_Tower_South (cam = 346.62, -248.83, heading 132.7°):
    #    Tall tapered modern light pole & blue port banner at V2/V3 (X = 364.8, Y = -255.1)
    add_cylinder_in_bm(bm, (364.8, -255.1), 0.195, 10.50, r_bot=0.18, r_top=0.09, n_seg=10, mat_idx=0)
    add_box_between(bm, (364.5, -255.1), (365.4, -255.1), 2.80, 5.40, thickness=0.12, offset_out=0.0, mat_idx=3)

    finalize_bm_to_mesh(bm, mesh, scale_uv=0.25)
    return obj


# --- 9. High-Poly Poly Haven 3D Trees, Streetlamps & Benches ---

def scatter_pier_props(collection_owned):
    # 1. Heritage Streetlamps (street_lamp_01)
    #    - Exact V3 alignment in Rue_de_la_Commune_Alexandra_Entrance: (219.8, -164.8, 0.165)
    lamp_specs = [
        ((219.8, -164.8, 0.165), 1.05),
        ((254.0, -210.0, 0.215), 1.0),
        ((274.0, -242.0, 0.165), 1.0),
        ((312.0, -236.5, 0.195), 0.95),
        ((338.0, -268.0, 6.35), 0.90),
        ((365.0, -266.0, 6.35), 0.90),
    ]
    for idx, (loc, sc) in enumerate(lamp_specs):
        kit.append_polyhaven_model("street_lamp_01", collection_owned, f"MTL_Lamp_{idx}", location=loc, rotation_z=0.5, scale=sc)

    # 2. Street Benches & Modular Seating (modular_street_seating)
    bench_locs = [
        (226.0, -168.0, 0.165),
        (268.0, -212.0, 0.215),
        (335.0, -272.0, 6.35),
        (350.0, -282.0, 6.45),
        (370.0, -270.0, 6.35),
    ]
    for idx, loc in enumerate(bench_locs):
        kit.append_polyhaven_model("modular_street_seating", collection_owned, f"MTL_Bench_{idx}", location=loc, rotation_z=0.3, scale=1.0)

    # 3. High-Poly Poly Haven Trees (jacaranda_tree) positioned to match:
    #    - Satellite TopDown (Place des Commencements South Grove V2..V3, H5..H8 & North Park V2..V3, H1..H3)
    #    - Promenade_du_Grand_Quai_Roof (Right-side trees V6..V8, H4..H5; zero trees blocking sky in V1..V3!)
    #    - Rue_de_la_Commune_Alexandra_Entrance (Mid-distance park trees in H4..H5, V2..V8)
    tree_specs = [
        # Place des Commencements South Park Grove (V2..V3, H5..H8 in Satellite TopDown)
        ((254.0, -274.0, 0.195), 1.15),
        ((264.0, -272.0, 0.195), 1.20),
        ((273.5, -270.0, 0.195), 1.05),
        ((251.0, -286.0, 0.195), 1.25),
        ((262.5, -287.0, 0.195), 1.30),
        ((273.0, -285.0, 0.195), 1.15),
        ((255.0, -298.0, 0.195), 1.20),
        ((264.0, -300.0, 0.195), 1.20),
        ((252.0, -312.0, 0.195), 1.15),
        ((262.0, -318.0, 0.195), 1.15),
        ((280.0, -319.0, 0.195), 1.05),
        # North Park Trees (V1..V3, H1..H3 in Satellite TopDown)
        ((240.0, -203.0, 0.195), 1.05),
        ((273.5, -198.5, 0.195), 1.10),
        ((248.5, -220.0, 0.195), 1.05),
        ((246.0, -231.5, 0.195), 1.00),
        ((270.5, -225.0, 0.195), 1.05),
        # Pier South Roadway Tree (V6, H4 in Satellite TopDown & Promenade_du_Grand_Quai_Roof V6..V8, H4..H5)
        ((325.0, -256.8, 0.195), 0.78),
        ((296.0, -267.5, 0.195), 0.55),
        # Rue_de_la_Commune_Alexandra_Entrance park background trees (H4..H5)
        ((242.0, -168.0, 0.195), 0.80),
        ((238.0, -182.0, 0.195), 0.80),
        ((224.5, -179.5, 0.195), 0.52),
    ]
    for idx, (loc, sc) in enumerate(tree_specs):
        rot = float((idx * 67) % 360) * (math.pi / 180.0)
        kit.append_polyhaven_model("jacaranda_tree", collection_owned, f"MTL_Tree_{idx}", location=loc, rotation_z=rot, scale=sc)


# --- 10. World Lighting & Camera Rendering ---

def configure_world_and_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16

    world = bpy.data.worlds.new(name=f"MTL_World_{BLOCK_ID}")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.15
    links.new(out.inputs["Surface"], bg.outputs["Background"])

    # Mix HDRI sky with clear azure-blue sky tint so H1..H3 matches bright Google Street View skies
    hdri_path = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")
    if os.path.isfile(hdri_path):
        env = nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri_path, check_existing=True)
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MIX"
        mix.inputs["Factor"].default_value = 0.42
        mix.inputs[7].default_value = (0.36, 0.58, 0.88, 1.0)
        links.new(mix.inputs[6], env.outputs["Color"])
        links.new(bg.inputs["Color"], mix.outputs[2])
    else:
        bg.inputs["Color"].default_value = (0.42, 0.64, 0.92, 1.0)

    # Sun direction casting shadows to the West-Northwest matching Satellite TopDown
    sun_data = bpy.data.lights.new(name=f"MTL_Sun_{BLOCK_ID}", type="SUN")
    sun_data.energy = 4.2
    sun_data.color = (1.0, 0.97, 0.90)
    sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name=f"MTL_Sun_{BLOCK_ID}", object_data=sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(38.0), math.radians(8.0), math.radians(-115.0))


def render_cameras(dossier, iter_num=2):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640

    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        cx, cy = cam_info["blender_cam_xy_m"]
        heading_deg = float(cam_info.get("heading", cam_info.get("heading_deg", 0.0)))
        pitch_deg = float(cam_info.get("pitch_deg", 10.0))
        fov_deg = float(cam_info.get("fov_deg", 90.0))

        cam_data = bpy.data.cameras.new(name=f"Cam_SV_{label}")
        cam_data.angle = math.radians(fov_deg)
        cam_data.clip_start = 0.20
        cam_data.clip_end = 2500.0
        cam_obj = bpy.data.objects.new(name=f"Cam_SV_{label}", object_data=cam_data)
        scene.collection.objects.link(cam_obj)
        cam_obj.location = (cx, cy, 1.75)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch_deg), 0.0, math.radians(-heading_deg))

        scene.camera = cam_obj
        out_file = os.path.join(RENDERS_DIR, f"iter{iter_num}_{label}.png")
        scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)

    # 1:1 Google Maps Satellite-Matched Top-Down Orthographic Camera
    sat_spec = dossier.get("satellite", {})
    sat_cx, sat_cy = sat_spec.get("center_xy_m", dossier.get("blender_center_xy_m", [294.129, -257.148]))
    sat_span = float(sat_spec.get("span_meters", 133.93))
    ortho_data = bpy.data.cameras.new(name=f"Cam_Satellite_TopDown_Ortho_{BLOCK_ID}")
    ortho_data.type = "ORTHO"
    ortho_data.ortho_scale = sat_span
    ortho_data.clip_start = 1.0
    ortho_data.clip_end = 1000.0
    ortho_obj = bpy.data.objects.new(name=f"Cam_Satellite_TopDown_Ortho_{BLOCK_ID}", object_data=ortho_data)
    scene.collection.objects.link(ortho_obj)
    ortho_obj.location = (sat_cx, sat_cy, 300.0)
    ortho_obj.rotation_euler = (0.0, 0.0, 0.0)
    scene.camera = ortho_obj
    scene.render.filepath = os.path.join(RENDERS_DIR, f"iter{iter_num}_topdown_ortho.png")
    bpy.ops.render.render(write_still=True)

    # Overview Snapshot Camera
    ov_data = bpy.data.cameras.new(name=f"Overview_Cam_{BLOCK_ID}")
    ov_data.angle = math.radians(52.0)
    ov_data.clip_start = 1.0
    ov_data.clip_end = 3000.0
    ov_obj = bpy.data.objects.new(name=f"Overview_Cam_{BLOCK_ID}", object_data=ov_data)
    scene.collection.objects.link(ov_obj)
    target = Vector((420.0, -255.0, 15.0))
    ov_obj.location = (210.0, -400.0, 115.0)
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = SNAPSHOT_PATH
    bpy.ops.render.render(write_still=True)


def main():
    print(f"Starting Iteration 2 High-Poly 3D Build for Block {BLOCK_ID}...")
    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    master_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(master_col)
    col_owned = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    master_col.children.link(col_owned)

    palette = create_upgraded_palette()

    build_ground_quays_and_streets(dossier, palette, col_owned)
    build_moored_cruise_ship(palette, col_owned)

    # Diverse facade material cycle for secondary historic/port buildings
    wall_cycle = [
        "Mat_MTL_Heritage_RedBrick",
        "Mat_MTL_PierreGrise_Limestone",
        "Mat_MTL_WarmBuff_Limestone",
        "Mat_MTL_Victorian_Brick",
        "Mat_MTL_Yellow_Buff_Brick",
        "Mat_MTL_Red_Sandstone",
        "Mat_MTL_Dark_Loft_Brick",
    ]
    sec_idx = 0

    for bldg in dossier.get("osm_features", {}).get("buildings", []):
        if not bldg.get("is_primary_owner"):
            continue
        bid = bldg["id"]
        if bid == 46866808:
            build_terminal_3_46866808(bldg, palette, col_owned)
        elif bid == 46866807:
            build_stationnement_grand_quai_46866807(bldg, palette, col_owned)
        elif bid == 677248941:
            build_gare_maritime_iberville_677248941(bldg, palette, col_owned)
        elif bid == 995326034:
            build_port_observation_tower_995326034(bldg, palette, col_owned)
        elif bid == 300595274:
            build_entrance_pavilion_300595274(bldg, palette, col_owned)
        elif bid == 87415541:
            build_canada_customs_87415541(bldg, palette, col_owned)
        elif bid == 440195613:
            build_habitat_67_440195613(bldg, palette, col_owned)
        else:
            w_key = wall_cycle[sec_idx % len(wall_cycle)]
            sec_idx += 1
            build_historic_port_building(bldg, palette, col_owned, f"PortBldg_{sec_idx}", height=11.0, n_floors=3, mat_wall_key=w_key)

    scatter_pier_props(col_owned)
    configure_world_and_render()

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

    if os.path.exists(USDC_OUT_PATH):
        try:
            os.remove(USDC_OUT_PATH)
        except Exception:
            pass
    bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, selected_objects_only=False)
    render_cameras(dossier, iter_num=3)
    print(f"Iteration 3 build complete for {BLOCK_ID}!")


if __name__ == "__main__":
    main()
