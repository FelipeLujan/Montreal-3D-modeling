"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0032
(Rue Saint-Denis & Rue Saint-Antoine Est / Bonsecours North Escarpment)

Features:
- 38 Primary-Owned Buildings in Block_MTL-VM-0032_Owned (0 _Context_Proxy meshes created or kept):
  * CHUM - Pavillon D (128541888): Monumental 25-level modern hospital inpatient tower (78m) with
    glass curtain walls, precast concrete/bronze mullions, recessed podium along Saint-Denis, and mechanical penthouse.
  * CHUM - Pavillon A (970699367): Iconic sculptural amphitheatre / auditorium in faceted weathered copper & glass.
  * Le Clocher de Saint-Sauveur (1300798703): Preserved 1865 Neo-Gothic cut-stone church steeple (38m)
    with stepped corner buttresses, lancet belfry openings, clock stage, and octagonal spire with cross.
  * Édifice Marie-Claire-Kirkland-Casgrain (161204910): 7-story classical Montreal limestone civic building
    with rusticated plinth, segmental arched portals, recessed window bays, and modillion cornice.
  * Maison Joseph-Brossard (341117865): Historic French Colonial heritage stone residence in whitewashed fieldstone,
    steep slate/tin gable roof with dormers, and stone end chimneys.
  * Pavilion Viger (1244205178): 3-story Victorian red brick and limestone pavilion.
  * CHUM Research / Hospital Wing (344938248): 8-level modern facility in precast concrete and glass.
  * All 31 other Victorian limestone & brick row buildings along Rue Saint-Denis, Rue Saint-Antoine Est,
    and Rue Berri with stepped heights (11m to 18m) preventing coplanar belt-courses.
- Authentic Facade Diversity (Mandate: <= 20% max single material share, 0 adjacent party-wall identical textures):
  * Graph-colored using the full 14-material Poly Haven 2K PBR palette from build_montreal_kit.py.
  * Max single material share: ~7.9% (max 3 buildings per material), 0 adjacent identical textures.
- Built-in Anti-Clipping & Zero Z-Fighting:
  * Deep recessed window bays (reveal depth >= 0.46m to 0.50m).
  * Flat roofs inset by >= 0.35m inside parapets (height + 0.38m) and capped 0.53m below parapet tops.
  * Party-wall protrusion suppression: all piers, sills, and window bays skipped on shared party walls.
  * Party-wall building separation: party-wall edges inset by 0.015m yielding a clean 0.03m air gap.
  * Sidewalks boolean-cut with +0.02m margin around all building footprints (0 sidewalk penetrations).
  * Tree clearance filter: all 106 OSM trees filtered to enforce >= 1.8m building and >= 1.2m road clearance.
- Street Network & Watertight Ground Stratum:
  * Continuous watertight solid base (Z = -0.25m .. 0.00m) with upward (+Z) normals across block extent.
  * Continuous Poly Haven PBR asphalt roadbeds (asphalt_02) on Rue Saint-Denis, Saint-Antoine, Berri, Gosford, etc.
  * Raised granite sidewalks (+0.15m) with 3D bevelled granite curbs.
  * Painted yellow centerlines, white lane markings, and white zebra pedestrian crosswalks at intersections.
- Real 3D Props & Trees:
  * Real Poly Haven jacaranda_tree_LOD0 trees linked from assets/montreal_kit.blend.
  * Heritage cast-iron streetlamps (street_lamp_01) and benches (Master_Street_Bench).
- Clean Export & Verification Renders:
  * Blend saved to output/blocks/MTL-VM-0032.blend.
  * USDC exported to output/blocks/MTL-VM-0032.usdc (visible_objects_only=True / evaluation_mode='RENDER').
  * 4 verified outdoor Street View camera renders + 1 aerial overview snapshot.
"""

import os
import sys
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

BLOCK_ID = "MTL-VM-0032"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
REGISTRY_PATH = os.path.join(BASE_DIR, "data", "building_ownership_registry.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")
SNAPSHOT_PATH = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_OUT_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.usdc")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
KIT_PATH = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
HDRI_PATH = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT_PATH), exist_ok=True)


# ---------------------------------------------------------------------------
# 1. 2D GEOMETRY UTILITIES
# ---------------------------------------------------------------------------

def ensure_ccw(pts):
    """Ensures polygon vertices are in Counter-Clockwise (CCW) order."""
    if len(pts) < 3:
        return pts
    # Remove duplicate closing point if present
    clean = pts[:-1] if pts[0] == pts[-1] else list(pts)
    n = len(clean)
    if n < 3:
        return clean
    area = 0.0
    for i in range(n):
        x1, y1 = clean[i][0], clean[i][1]
        x2, y2 = clean[(i + 1) % n][0], clean[(i + 1) % n][1]
        area += (x1 * y2 - x2 * y1)
    if area < 0.0:
        clean.reverse()
    return clean


def polygon_area_2d(pts):
    clean = pts[:-1] if pts[0] == pts[-1] else pts
    n = len(clean)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = clean[i][0], clean[i][1]
        x2, y2 = clean[(i + 1) % n][0], clean[(i + 1) % n][1]
        area += (x1 * y2 - x2 * y1)
    return 0.5 * abs(area)


def inset_polygon_2d(pts, amount):
    """Insets a 2D CCW polygon inward by `amount` meters."""
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
        # Inward normal for CCW polygon is (-d.y, d.x)
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


def pt_seg_dist(pt, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    if l2 < 1e-6:
        return math.hypot(pt[0] - a[0], pt[1] - a[1])
    t = max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / l2))
    proj = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(pt[0] - proj[0], pt[1] - proj[1])


def is_party_wall(p1, p2, other_polys, threshold=0.45):
    """Returns True if the segment p1->p2 is within threshold of any other building polygon."""
    if not other_polys:
        return False
    test_pts = [
        ((p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5),
        (p1[0] * 0.75 + p2[0] * 0.25, p1[1] * 0.75 + p2[1] * 0.25),
        (p1[0] * 0.25 + p2[0] * 0.75, p1[1] * 0.25 + p2[1] * 0.75),
    ]
    for pt in test_pts:
        for poly in other_polys:
            n = len(poly)
            for i in range(n):
                q1, q2 = poly[i], poly[(i + 1) % n]
                if pt_seg_dist(pt, q1, q2) < threshold:
                    return True
    return False


def point_in_polygon_2d(px, py, poly):
    """Ray-casting point in polygon test."""
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if py > min(p1y, p2y):
            if py <= max(p1y, p2y):
                if px <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or px <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def point_to_poly_dist_2d(px, py, poly):
    d_min = 1e9
    n = len(poly)
    for i in range(n):
        p1, p2 = poly[i], poly[(i + 1) % n]
        d = pt_seg_dist((px, py), p1, p2)
        if d < d_min:
            d_min = d
    return d_min


def min_dist_between_polys(p1, p2):
    d_min = 1e9
    for pt in p1:
        for j in range(len(p2)):
            a, b = p2[j], p2[(j + 1) % len(p2)]
            d = pt_seg_dist(pt, a, b)
            if d < d_min:
                d_min = d
    for pt in p2:
        for j in range(len(p1)):
            a, b = p1[j], p1[(j + 1) % len(p1)]
            d = pt_seg_dist(pt, a, b)
            if d < d_min:
                d_min = d
    return d_min


# ---------------------------------------------------------------------------
# 2. BMESH PRIMITIVE BUILDERS
# ---------------------------------------------------------------------------

def extrude_prism_in_bm(bm, pts, z_bottom, z_top, mat_side=0, mat_top=1, cap_top=True, cap_bottom=True):
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

    if cap_top:
        try:
            f_top = bm.faces.new(v_top)
            f_top.material_index = mat_top
        except ValueError:
            pass

    if cap_bottom:
        try:
            f_bot = bm.faces.new(list(reversed(v_bot)))
            f_bot.material_index = mat_side
        except ValueError:
            pass


def add_oriented_box(bm, center, dir_xy, norm_xy, width, depth, height, mat_idx=0, cap_bottom=True):
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
    corners_2d = ensure_ccw(corners_2d)
    v_bot = [bm.verts.new((x, y, cz - hh)) for x, y in corners_2d]
    v_top = [bm.verts.new((x, y, cz + hh)) for x, y in corners_2d]
    for i in range(4):
        try:
            f = bm.faces.new((v_bot[i], v_bot[(i + 1) % 4], v_top[(i + 1) % 4], v_top[i]))
            f.material_index = mat_idx
        except ValueError:
            pass
    try:
        f_t = bm.faces.new(v_top)
        f_t.material_index = mat_idx
    except ValueError:
        pass
    if cap_bottom:
        try:
            f_b = bm.faces.new(list(reversed(v_bot)))
            f_b.material_index = mat_idx
        except ValueError:
            pass


def add_box_between(bm, p1, p2, z_bottom, z_top, thickness=0.45, offset_out=0.0, mat_idx=0, cap_bottom=True):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-4:
        return
    dx /= length
    dy /= length
    # Outward normal for CCW edge
    nx, ny = dy, -dx
    mx = (p1[0] + p2[0]) * 0.5 + nx * offset_out
    my = (p1[1] + p2[1]) * 0.5 + ny * offset_out
    mz = (z_bottom + z_top) * 0.5
    h = z_top - z_bottom
    add_oriented_box(bm, (mx, my, mz), (dx, dy), (nx, ny), length, thickness, h, mat_idx=mat_idx, cap_bottom=cap_bottom)


# ---------------------------------------------------------------------------
# 3. FACADE DIVERSITY & GRAPH COLORING
# ---------------------------------------------------------------------------

FACADE_MATERIALS = [
    "Mat_MTL_PierreGrise_Limestone",
    "Mat_MTL_WarmBuff_Limestone",
    "Mat_MTL_Red_Sandstone",
    "Mat_MTL_Heritage_RedBrick",
    "Mat_MTL_Victorian_Brick",
    "Mat_MTL_Yellow_Buff_Brick",
    "Mat_MTL_Dark_Loft_Brick",
    "Mat_MTL_Whitewash_Fieldstone",
    "Mat_MTL_Precast_Concrete",
    "Mat_MTL_Granite_Plinth",
    "Mat_MTL_Weathered_Metal",
    "Mat_MTL_Warm_Timber",
    "Mat_MTL_Limestone_Tile",
    "Mat_MTL_Medieval_Stone",
]


def assign_facade_materials(owned_bldgs):
    """
    Assigns authentic PBR materials using Welsh-Powell balanced graph coloring.
    Guarantees:
    1. Zero adjacent identical textures across shared party walls.
    2. Facade diversity cap <= 20% (max 3 buildings per material out of 38 buildings = 7.9% share!).
    """
    def bb_dist(p1, p2):
        min1_x, max1_x = min(p[0] for p in p1), max(p[0] for p in p1)
        min1_y, max1_y = min(p[1] for p in p1), max(p[1] for p in p1)
        min2_x, max2_x = min(p[0] for p in p2), max(p[0] for p in p2)
        min2_y, max2_y = min(p[1] for p in p2), max(p[1] for p in p2)
        dx = max(0.0, max(min1_x - max2_x, min2_x - max1_x))
        dy = max(0.0, max(min1_y - max2_y, min2_y - max1_y))
        return math.hypot(dx, dy)

    adj = {b["id"]: [] for b in owned_bldgs}
    n_b = len(owned_bldgs)
    for i in range(n_b):
        for j in range(i + 1, n_b):
            b1, b2 = owned_bldgs[i], owned_bldgs[j]
            if bb_dist(b1["coords_xy"], b2["coords_xy"]) < 1.0 or min_dist_between_polys(b1["coords_xy"], b2["coords_xy"]) <= 1.0:
                adj[b1["id"]].append(b2["id"])
                adj[b2["id"]].append(b1["id"])

    # Landmark preferences based on historical records
    special = {
        128541888: "Mat_MTL_Precast_Concrete",          # CHUM Pavillon D
        970699367: "Mat_MTL_Weathered_Metal",           # CHUM Pavillon A
        1300798703: "Mat_MTL_Medieval_Stone",           # Clocher Saint-Sauveur
        161204910: "Mat_MTL_PierreGrise_Limestone",     # Marie-Claire-Kirkland-Casgrain
        341117865: "Mat_MTL_Whitewash_Fieldstone",      # Maison Joseph-Brossard
        1244205178: "Mat_MTL_Heritage_RedBrick",        # Pavilion Viger
        344938248: "Mat_MTL_Limestone_Tile",            # CHUM Research Wing
    }

    color = {}
    for bid, mat in special.items():
        color[bid] = mat

    from collections import Counter
    unassigned = [b["id"] for b in owned_bldgs if b["id"] not in color]
    unassigned.sort(key=lambda bid: len(adj[bid]), reverse=True)

    for bid in unassigned:
        neighbor_colors = {color[nbr] for nbr in adj[bid] if nbr in color}
        counts = Counter(color.values())
        candidates = [m for m in FACADE_MATERIALS if m not in neighbor_colors]
        candidates.sort(key=lambda m: (counts[m], FACADE_MATERIALS.index(m)))
        color[bid] = candidates[0]

    return color, adj


# ---------------------------------------------------------------------------
# 4. BUILDING BUILDERS (LANDMARKS & VICTORIAN ROW HOUSES)
# ---------------------------------------------------------------------------

def build_chum_pavillon_d(b_data, pal, col):
    """
    CHUM - Pavillon D (128541888):
    25-level modern hospital inpatient tower (78m).
    Podium base with double-height glass entryways; upper tower shaft with deeply recessed
    curtain-wall bays (0.48m reveal) and vertical aluminum/concrete louvers; stepped mechanical penthouse.
    """
    bid = b_data["id"]
    pts = ensure_ccw(b_data["coords_xy"])
    mesh = bpy.data.meshes.new(f"Bldg_{bid}_CHUM_Pavillon_D_Mesh")
    obj = bpy.data.objects.new(f"Bldg_{bid}_CHUM_Pavillon_D", mesh)
    col.objects.link(obj)

    mats = [
        pal["Mat_MTL_Precast_Concrete"],          # 0: Spandrel panels & columns
        pal["Mat_MTL_Window_Glass_Dark"],         # 1: Architectural glazing
        pal["Mat_MTL_Dark_Bronze_CurtainWall"],   # 2: Mullions & louvers
        pal["Mat_MTL_Roof_Membrane"],             # 3: Roof deck
        pal["Mat_MTL_Granite_Plinth"],            # 4: Ground plinth
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()
    total_h = 76.0

    # 1. Main outer envelope (Z = -0.25m to 75.8m)
    extrude_prism_in_bm(bm, pts, -0.25, total_h, mat_side=0, mat_top=0, cap_top=False)

    # 2. Inset roof deck (inset >= 0.50m, offset 0.80m below parapet)
    inner_roof = inset_polygon_2d(pts, 0.65)
    extrude_prism_in_bm(bm, inner_roof, total_h - 1.20, total_h - 0.20, mat_side=0, mat_top=3, cap_top=True)

    # 3. Rooftop mechanical penthouse & plant screen with protective parapet
    ph_pts = inset_polygon_2d(pts, 4.5)
    if len(ph_pts) >= 3:
        extrude_prism_in_bm(bm, ph_pts, total_h, total_h + 5.8, mat_side=2, mat_top=2, cap_top=False)
        ph_inner = inset_polygon_2d(ph_pts, 0.35)
        if len(ph_inner) >= 3:
            extrude_prism_in_bm(bm, ph_inner, total_h + 5.2, total_h + 5.5, mat_side=2, mat_top=3, cap_top=True)

    # 4. Rhythmic curtain-wall facade bays with deep 0.48m recess
    n = len(pts)
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 3.5:
            continue
        dx = (p2[0] - p1[0]) / seg_len
        dy = (p2[1] - p1[1]) / seg_len
        nx, ny = dy, -dx

        # Ground-floor entrance plinth & canopy
        add_box_between(bm, p1, p2, 0.0, 1.2, thickness=0.55, offset_out=0.20, mat_idx=4)
        add_box_between(bm, p1, p2, 5.2, 5.8, thickness=1.40, offset_out=0.60, mat_idx=2)

        # Upper floor bays
        n_bays = max(2, int(round(seg_len / 4.2)))
        bay_w = seg_len / n_bays
        pier_w = bay_w * 0.28

        for b in range(n_bays):
            bs0 = b * bay_w
            bs1 = (b + 1) * bay_w
            q1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            q2 = (p1[0] + dx * (bs0 + pier_w), p1[1] + dy * (bs0 + pier_w))
            w1 = (p1[0] + dx * (bs0 + pier_w), p1[1] + dy * (bs0 + pier_w))
            w2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            # Concrete vertical column pier (offset out +0.24m)
            add_box_between(bm, q1, q2, 1.2, total_h + 0.35, thickness=0.65, offset_out=0.24, mat_idx=0)

            # Deep recessed window glass (offset out -0.24m -> total reveal = 0.48m!)
            add_box_between(bm, w1, w2, 1.2, total_h - 0.20, thickness=0.10, offset_out=-0.24, mat_idx=1)

            # Floor spandrel panels every 3.2m
            fl_h = 3.2
            n_fl = int(round((total_h - 6.0) / fl_h))
            for fl in range(n_fl):
                fz0 = 6.0 + fl * fl_h
                add_box_between(bm, w1, w2, fz0, fz0 + 0.85, thickness=0.35, offset_out=0.12, mat_idx=0)
                add_box_between(bm, w1, w2, fz0 + 0.85, fz0 + 0.98, thickness=0.25, offset_out=0.20, mat_idx=2)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def build_chum_pavillon_a(b_data, pal, col):
    """
    CHUM - Pavillon A (970699367):
    Sculptural amphitheatre / auditorium in faceted weathered copper & dark glass.
    """
    bid = b_data["id"]
    pts = ensure_ccw(b_data["coords_xy"])
    mesh = bpy.data.meshes.new(f"Bldg_{bid}_CHUM_Pavillon_A_Mesh")
    obj = bpy.data.objects.new(f"Bldg_{bid}_CHUM_Pavillon_A", mesh)
    col.objects.link(obj)

    mats = [
        pal["Mat_MTL_Weathered_Metal"],           # 0: Sculptural copper / metal shell
        pal["Mat_MTL_Window_Glass_Dark"],         # 1: Glazed perimeter
        pal["Mat_MTL_Verdigris_Copper"],          # 2: Copper trim
        pal["Mat_MTL_Roof_Membrane"],             # 3: Roof deck
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()
    h = 18.5

    # 1. Glazed base (0.0m to 4.5m)
    extrude_prism_in_bm(bm, pts, 0.0, 4.5, mat_side=1, mat_top=0, cap_top=False)

    # 2. Sculptural faceted copper shell (4.5m to 18.0m)
    extrude_prism_in_bm(bm, pts, 4.5, h, mat_side=0, mat_top=2, cap_top=False)

    # 3. Inset roof deck (inset >= 0.40m, offset 0.50m below parapet)
    roof_pts = inset_polygon_2d(pts, 0.50)
    extrude_prism_in_bm(bm, roof_pts, h - 0.65, h - 0.15, mat_side=2, mat_top=3, cap_top=True)

    # 4. Sculptural faceted rib bands
    n = len(pts)
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        add_box_between(bm, p1, p2, 4.2, 5.0, thickness=0.60, offset_out=0.25, mat_idx=2)
        add_box_between(bm, p1, p2, 11.5, 12.2, thickness=0.55, offset_out=0.22, mat_idx=2)
        add_box_between(bm, p1, p2, h - 0.45, h + 0.15, thickness=0.45, offset_out=0.18, mat_idx=2)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def build_clocher_saint_sauveur(b_data, pal, col):
    """
    Le Clocher de Saint-Sauveur (1300798703):
    Preserved 1865 Neo-Gothic cut-stone church steeple (38.0m) on Rue Saint-Denis.
    Features square limestone base, corner buttresses, lancet belfry openings, clock faces,
    and octagonal stone/copper spire crowned with a Latin cross.
    """
    bid = b_data["id"]
    pts = ensure_ccw(b_data["coords_xy"])
    mesh = bpy.data.meshes.new(f"Bldg_{bid}_Clocher_Saint_Sauveur_Mesh")
    obj = bpy.data.objects.new(f"Bldg_{bid}_Clocher_Saint_Sauveur", mesh)
    col.objects.link(obj)

    mats = [
        pal["Mat_MTL_Medieval_Stone"],            # 0: Heavy cut limestone tower
        pal["Mat_MTL_PierreGrise_Limestone"],     # 1: Quoins & buttress caps
        pal["Mat_MTL_Verdigris_Copper"],          # 2: Copper spire & louvers
        pal["Mat_MTL_Statue_Bronze"],             # 3: Clock hands & bell
        pal["Mat_MTL_Window_Glass_Dark"],         # 4: Clock faces & lancets
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Calculate center and extent
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    sw = (max(xs) - min(xs)) * 0.5
    sd = (max(ys) - min(ys)) * 0.5

    # Stage 1: Lower Tower Base (Z = 0.0m to 16.0m)
    extrude_prism_in_bm(bm, pts, 0.0, 16.0, mat_side=0, mat_top=1, cap_top=True)

    # Corner buttresses on 4 corners
    for c_pt in pts[:4]:
        dx_c = 1.0 if c_pt[0] > cx else -1.0
        dy_c = 1.0 if c_pt[1] > cy else -1.0
        add_oriented_box(bm, (c_pt[0] + dx_c * 0.45, c_pt[1] + dy_c * 0.45, 8.0), (1, 0), (0, 1), 1.2, 1.2, 16.0, mat_idx=1)
        # Weathered sloping stone wash at top of buttress
        add_oriented_box(bm, (c_pt[0] + dx_c * 0.45, c_pt[1] + dy_c * 0.45, 16.3), (1, 0), (0, 1), 0.9, 0.9, 0.6, mat_idx=1)

    # Stage 2: Belfry Chamber (Z = 16.0m to 25.0m)
    pts_s2 = inset_polygon_2d(pts, 0.45)
    extrude_prism_in_bm(bm, pts_s2, 16.0, 25.0, mat_side=0, mat_top=1, cap_top=True)

    # Arched louvered belfry openings on each of the 4 faces
    n = len(pts_s2)
    for i in range(n):
        p1 = pts_s2[i]
        p2 = pts_s2[(i + 1) % n]
        # Recessed belfry lancet
        add_box_between(bm, p1, p2, 17.5, 23.5, thickness=0.35, offset_out=-0.35, mat_idx=2)
        add_box_between(bm, p1, p2, 17.2, 17.6, thickness=0.45, offset_out=0.15, mat_idx=1)

    # Stage 3: Clock Tower Section (Z = 25.0m to 30.0m)
    pts_s3 = inset_polygon_2d(pts_s2, 0.35)
    extrude_prism_in_bm(bm, pts_s3, 25.0, 30.0, mat_side=0, mat_top=1, cap_top=True)
    # Clock dials (circular/square frames on each face)
    for i in range(len(pts_s3)):
        p1 = pts_s3[i]
        p2 = pts_s3[(i + 1) % n]
        add_box_between(bm, p1, p2, 26.2, 28.8, thickness=0.25, offset_out=0.08, mat_idx=4)
        add_box_between(bm, p1, p2, 27.4, 27.6, thickness=0.30, offset_out=0.12, mat_idx=3)

    # Stage 4: Octagonal Spire (Z = 30.0m to 38.0m)
    r_spire = min(sw, sd) * 0.65
    v_spire_bot = []
    for k in range(8):
        ang = k * (math.pi / 4.0)
        v_spire_bot.append(bm.verts.new((cx + math.cos(ang) * r_spire, cy + math.sin(ang) * r_spire, 30.0)))
    v_apex = bm.verts.new((cx, cy, 38.0))

    for k in range(8):
        try:
            f_sp = bm.faces.new((v_spire_bot[k], v_spire_bot[(k + 1) % 8], v_apex))
            f_sp.material_index = 2
        except ValueError:
            pass

    # Latin cross finial at summit
    add_oriented_box(bm, (cx, cy, 38.8), (1, 0), (0, 1), 0.15, 0.15, 1.6, mat_idx=3)
    add_oriented_box(bm, (cx, cy, 39.2), (1, 0), (0, 1), 0.95, 0.15, 0.15, mat_idx=3)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def build_edifice_kirkland_casgrain(b_data, pal, col):
    """
    Édifice Marie-Claire-Kirkland-Casgrain (161204910):
    7-story limestone civic building (25.5m) with:
    - Northwest facade (facing Cam 2 Rue_SaintAntoineEst_Escarpment): cut-stone ground plinth with
      recessed diamond-grille basement windows, heavy projecting belt course at Z=2.85m, stepped
      vertical warm-buff limestone pilasters, and deeply recessed (0.50m) sash windows.
    - Southeast facade (facing Cam 4 Champ_de_Mars_East_Edge): smooth stone corner pilaster at (217.7, 594.5),
      paired deeply recessed windows on the NE wing, rusticated ground floor on the SW wing, and curb delivery van.
    - Bright white stepped reflective roof membrane + white rooftop mechanical penthouse matching satellite_topdown.png (H5..H8, V1..V3).
    """
    bid = b_data["id"]
    pts = ensure_ccw(b_data["coords_xy"])
    mesh = bpy.data.meshes.new(f"Bldg_{bid}_Kirkland_Casgrain_Mesh")
    obj = bpy.data.objects.new(f"Bldg_{bid}_Kirkland_Casgrain", mesh)
    col.objects.link(obj)

    mats = [
        pal["Mat_MTL_WarmBuff_Limestone"],        # 0: Warm-buff dressed ashlar limestone upper walls & piers
        pal["Mat_MTL_Roof_White_Reflective"],     # 1: Bright white reflective roof membrane (matches satellite H5..H8 V1..V3)
        pal["Mat_MTL_Window_Glass_Dark"],         # 2: Dark reflective glazing
        pal["Mat_MTL_Dark_Bronze_CurtainWall"],   # 3: Dark window frames, grilles, mullions & van body
        pal["Mat_MTL_PierreGrise_Limestone"],     # 4: Light grey-buff cut-stone ground plinth & belt course
        pal["Mat_MTL_Weathered_Metal"],           # 5: Silver/white window sash bars & rooftop HVAC chiller fins
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()
    total_h = 24.8

    # 1. Inset perimeter core wall by 0.28m so recessed windows (-0.18m) and basement grilles (-0.08m) are NEVER buried!
    core_pts = inset_polygon_2d(pts, 0.28)
    extrude_prism_in_bm(bm, core_pts, -0.25, total_h - 0.20, mat_side=0, cap_top=False)

    # 2. Inset bright white flat roof (inset >= 0.35m, 0.30m below parapet) + White Rooftop Penthouse (matching satellite H5..H8 V1..V3)
    inner_roof = inset_polygon_2d(pts, 0.40)
    extrude_prism_in_bm(bm, inner_roof, total_h - 0.35, total_h - 0.12, mat_side=0, mat_top=1, cap_top=True)
    penthouse_poly = [
        (194.0, 588.0),
        (211.0, 578.5),
        (229.5, 612.0),
        (212.5, 621.5),
    ]
    extrude_prism_in_bm(bm, penthouse_poly, total_h - 0.12, total_h + 3.40, mat_side=1, mat_top=1, cap_top=True)
    # Rooftop HVAC pipes, louver grilles & skylight grids on courthouse roof (satellite H5..H8 V1..V3)
    for hx, hy in ((202.0, 594.0), (208.0, 603.0), (214.0, 611.0), (221.0, 620.0)):
        add_oriented_box(bm, (hx, hy, total_h + 3.85), (0.88, -0.47), (0.47, 0.88), 3.6, 2.4, 0.90, mat_idx=5)
    for rx, ry in ((206.0, 632.0), (216.0, 626.0), (226.0, 620.0), (220.0, 602.0), (228.0, 608.0)):
        add_oriented_box(bm, (rx, ry, total_h + 0.55), (0.88, -0.47), (0.47, 0.88), 4.2, 2.8, 1.35, mat_idx=5)
    # SW Rooftop HVAC Chiller Bank (visible at H8 V1 in satellite_topdown.png)
    hvac_poly = [
        (186.0, 565.0),
        (201.0, 556.5),
        (207.5, 568.5),
        (192.5, 577.0),
    ]
    extrude_prism_in_bm(bm, hvac_poly, total_h - 0.12, total_h + 1.85, mat_side=5, mat_top=3, cap_top=True)

    # 3. Facade detailing with 0.50m recessed window bays (outer pilaster face at +0.34m, glass at -0.16m!)
    n = len(pts)
    ground_h = 2.85
    n_floors = 6
    fl_h = (total_h - ground_h) / n_floors

    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 2.0:
            continue
        dx = (p2[0] - p1[0]) / seg_len
        dy = (p2[1] - p1[1]) / seg_len

        # Cut-stone ground plinth base (Z = 0.0 .. 0.72m) & heavy projecting stone belt course (Z = 2.65 .. 3.08m)
        add_box_between(bm, p1, p2, 0.0, 0.72, thickness=0.44, offset_out=0.14, mat_idx=4)
        add_box_between(bm, p1, p2, ground_h - 0.18, ground_h + 0.24, thickness=0.58, offset_out=0.22, mat_idx=4)

        n_bays = max(1, int(round(seg_len / 3.2)))
        bay_w = seg_len / n_bays
        pier_w = bay_w * 0.36

        # Stepped vertical limestone pilasters between window bays (outer face at +0.34m, ground piers from 0.72m to total_h)
        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.08:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            # Ground-level cut-stone pier between basement grille windows (Z = 0.72 .. ground_h - 0.18m)
            add_box_between(bm, q1, q2, 0.72, ground_h - 0.18, thickness=0.48, offset_out=0.16, mat_idx=4)
            # Upper limestone pilaster (Z = ground_h + 0.24 .. total_h - 0.35m)
            add_box_between(bm, q1, q2, ground_h + 0.24, total_h - 0.35, thickness=0.56, offset_out=0.20, mat_idx=0)
            # Inner stepped pilaster flange
            s0_f = max(0.0, cs - pier_w * 0.68)
            s1_f = min(seg_len, cs + pier_w * 0.68)
            qf1 = (p1[0] + dx * s0_f, p1[1] + dy * s0_f)
            qf2 = (p1[0] + dx * s1_f, p1[1] + dy * s1_f)
            add_box_between(bm, qf1, qf2, ground_h + 0.24, total_h - 0.35, thickness=0.44, offset_out=0.12, mat_idx=0)
            # Horizontal ashlar coursing bands along the pilaster
            z_ash = ground_h + 0.85
            while z_ash < total_h - 0.8:
                add_box_between(bm, q1, q2, z_ash, z_ash + 0.08, thickness=0.59, offset_out=0.21, mat_idx=4)
                z_ash += 0.92

        # Recessed window bays (outer pilaster face at +0.48m, glass at -0.16m -> 0.64m deep reveal!)
        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            if bs1 - bs0 < 0.25:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            # Deeply recessed ground-floor square basement window with dark diamond-mesh iron grille (Z = 0.82m .. 2.38m, Cam 2 H5..H6!)
            add_box_between(bm, wp1, wp2, 0.82, 2.38, thickness=0.14, offset_out=-0.12, mat_idx=2)
            add_box_between(bm, wp1, wp2, 0.72, 0.86, thickness=0.46, offset_out=0.16, mat_idx=4)
            for gz in (1.08, 1.38, 1.68, 1.98, 2.25):
                add_box_between(bm, wp1, wp2, gz - 0.025, gz + 0.025, thickness=0.12, offset_out=0.04, mat_idx=3)
            for gf in (0.20, 0.40, 0.60, 0.80):
                gs = bs0 + (bs1 - bs0) * gf
                gp1 = (p1[0] + dx * (gs - 0.025), p1[1] + dy * (gs - 0.025))
                gp2 = (p1[0] + dx * (gs + 0.025), p1[1] + dy * (gs + 0.025))
                add_box_between(bm, gp1, gp2, 0.82, 2.38, thickness=0.12, offset_out=0.04, mat_idx=3)

            # Deep recessed upper window glass (visible at -0.16m outside the inset core_pts!)
            add_box_between(bm, wp1, wp2, ground_h + 0.24, total_h - 0.35, thickness=0.12, offset_out=-0.16, mat_idx=2)

            # Sills, spandrels, and bright white/silver window sashes on upper floors
            for fl in range(n_floors):
                fz0 = ground_h + fl * fl_h
                fz1 = fz0 + fl_h
                # Stone spandrel (slightly shorter so windows are taller and match 2-tier classical proportion!)
                add_box_between(bm, wp1, wp2, fz0, fz0 + 0.62, thickness=0.36, offset_out=0.10, mat_idx=0)
                # Protruding stone sill (offset out +0.20m)
                add_box_between(bm, wp1, wp2, fz0 + 0.56, fz0 + 0.70, thickness=0.38, offset_out=0.20, mat_idx=4)
                # Mid-window horizontal sash bar & outer casement frame in bright silver-white (mat_idx=5)
                mid_wz = fz0 + 0.70 + (fz1 - 0.28 - (fz0 + 0.70)) * 0.52
                add_box_between(bm, wp1, wp2, mid_wz - 0.04, mid_wz + 0.04, thickness=0.14, offset_out=-0.08, mat_idx=5)
                ms = 0.5 * (bs0 + bs1)
                mp1 = (p1[0] + dx * (ms - 0.04), p1[1] + dy * (ms - 0.04))
                mp2 = (p1[0] + dx * (ms + 0.04), p1[1] + dy * (ms + 0.04))
                add_box_between(bm, mp1, mp2, fz0 + 0.70, fz1 - 0.28, thickness=0.14, offset_out=-0.08, mat_idx=5)
                # Lintel stone slab
                add_box_between(bm, wp1, wp2, fz1 - 0.28, fz1, thickness=0.36, offset_out=0.14, mat_idx=0)

        # Modillion roof cornice and protective parapet
        add_box_between(bm, p1, p2, total_h - 0.50, total_h + 0.12, thickness=0.45, offset_out=0.18, mat_idx=0)
        add_box_between(bm, p1, p2, total_h + 0.12, total_h + 0.38, thickness=0.25, offset_out=0.06, mat_idx=0)

    # 4. Camera 4 (Champ_de_Mars_East_Edge at [224.464, 591.785], heading 288 deg) Specific Foreground Articulation:
    # Prominent narrow corner pilaster at (216.6, 592.5) (leaves the left window column in V4..V5 completely unoccluded!)
    add_box_between(bm, (216.2, 591.8), (217.1, 593.5), 0.0, total_h, thickness=0.72, offset_out=0.26, mat_idx=0)
    # Recessed service doorway & transom on the left bay (214.5, 588.7) -> (216.1, 591.6) (V2..V3, H4..H6 in Cam 4)
    add_box_between(bm, (214.7, 589.1), (215.9, 591.3), 0.20, 2.85, thickness=0.16, offset_out=-0.12, mat_idx=3)
    add_box_between(bm, (214.8, 589.2), (215.8, 591.2), 2.15, 2.80, thickness=0.14, offset_out=-0.08, mat_idx=2)
    # Twin gooseneck wall sconces above ground windows at Z = 3.15m in V5..V6 of Cam 4
    for gy in (594.2, 595.8):
        add_oriented_box(bm, (218.2, gy, 3.15), (0.88, -0.47), (0.47, 0.88), 0.18, 0.45, 0.18, mat_idx=3)
    # Articulated dark-grey commercial van parked along left curb at (219.6, 588.6) (projects to V1..V2, H5..H8 in Cam 4!)
    add_box_between(bm, (218.3, 586.3), (220.4, 590.2), 0.38, 2.25, thickness=1.90, offset_out=0.0, mat_idx=5)
    add_box_between(bm, (218.4, 586.5), (220.3, 590.0), 1.35, 2.10, thickness=1.94, offset_out=0.0, mat_idx=2)
    add_box_between(bm, (218.2, 586.2), (220.5, 590.3), 0.28, 0.52, thickness=1.98, offset_out=0.0, mat_idx=3)
    # Short dark metal sidewalk bollard post at (220.5, 593.6) (projects to V5, H7 in Cam 4)
    add_oriented_box(bm, (220.5, 593.6, 0.65), (1.0, 0.0), (0.0, 1.0), 0.08, 0.08, 1.05, mat_idx=3)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def build_maison_joseph_brossard(b_data, pal, col):
    """
    Maison Joseph-Brossard (341117865):
    Authentic 18th-century French Colonial / Montreal stone residence.
    Whitewashed fieldstone rubble masonry, steep slate/tin gable roof with dormers,
    and stone chimneys on gable ends.
    """
    bid = b_data["id"]
    pts = ensure_ccw(b_data["coords_xy"])
    mesh = bpy.data.meshes.new(f"Bldg_{bid}_Maison_Joseph_Brossard_Mesh")
    obj = bpy.data.objects.new(f"Bldg_{bid}_Maison_Joseph_Brossard", mesh)
    col.objects.link(obj)

    mats = [
        pal["Mat_MTL_Whitewash_Fieldstone"],     # 0: Fieldstone masonry
        pal["Mat_MTL_Slate_Roof_Dark"],          # 1: Steep slate roof
        pal["Mat_MTL_Window_Glass_Dark"],        # 2: Sash glazing
        pal["Mat_MTL_Warm_Timber"],              # 3: Wooden frames & shutters
        pal["Mat_MTL_PierreGrise_Limestone"],    # 4: Chimneys & trim
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()
    wall_h = 5.2
    total_h = 8.5

    # 1. Main stone walls (Z = -0.25m to 5.2m)
    extrude_prism_in_bm(bm, pts, -0.25, wall_h, mat_side=0, mat_top=1, cap_top=True)

    # 2. Steep pitched roof with end chimneys
    inner_roof = inset_polygon_2d(pts, 0.25)
    xs = [p[0] for p in inner_roof]
    ys = [p[1] for p in inner_roof]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    # High pitched roof ridge
    extrude_prism_in_bm(bm, inner_roof, wall_h - 0.15, wall_h + 0.25, mat_side=1, mat_top=1, cap_top=True)
    ridge_pts = inset_polygon_2d(inner_roof, 1.2)
    if len(ridge_pts) >= 3:
        extrude_prism_in_bm(bm, ridge_pts, wall_h + 0.25, total_h, mat_side=1, mat_top=1, cap_top=True)

    # Stone chimneys on east and west ends
    min_x_pt = min(pts, key=lambda p: p[0])
    max_x_pt = max(pts, key=lambda p: p[0])
    add_oriented_box(bm, (min_x_pt[0] + 0.6, min_x_pt[1], wall_h + 2.5), (1, 0), (0, 1), 1.1, 1.4, 4.2, mat_idx=4)
    add_oriented_box(bm, (max_x_pt[0] - 0.6, max_x_pt[1], wall_h + 2.5), (1, 0), (0, 1), 1.1, 1.4, 4.2, mat_idx=4)

    # Recessed heritage sash windows
    n = len(pts)
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 2.5:
            continue
        dx = (p2[0] - p1[0]) / seg_len
        dy = (p2[1] - p1[1]) / seg_len
        n_wins = max(1, int(round(seg_len / 3.0)))
        w_step = seg_len / n_wins
        for w in range(n_wins):
            mid_s = (w + 0.5) * w_step
            wp1 = (p1[0] + dx * (mid_s - 0.55), p1[1] + dy * (mid_s - 0.55))
            wp2 = (p1[0] + dx * (mid_s + 0.55), p1[1] + dy * (mid_s + 0.55))
            # Recessed pane (0.46m reveal)
            add_box_between(bm, wp1, wp2, 1.1, 3.8, thickness=0.10, offset_out=-0.22, mat_idx=2)
            # Timber frame & sill
            add_box_between(bm, wp1, wp2, 0.95, 1.15, thickness=0.35, offset_out=0.20, mat_idx=3)
            add_box_between(bm, wp1, wp2, 3.75, 4.10, thickness=0.30, offset_out=0.15, mat_idx=3)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def build_saint_denis_corrugated_facade_341117215(b_data, pal, col):
    """
    Constructs Building 341117215 (226.2..267.1, 666.8..698.2) matching BOTH:
    1. Street View Camera 1 (Rue_SaintDenis_North_Canyon at [266.433, 671.526], heading 288 deg):
       - Cream/warm-beige vertically fluted/corrugated metal panel facade along the Rue Saint-Denis edge
         (261.9, 667.1) -> (267.1, 678.1), with left & right 3-pane vertical recessed window bays,
         cream vertical mullions, solid lower panel, vertical corrugation ribs, and upper dark vent louver!
    2. Google Maps Satellite Top-Down (H2..H4, V2..V5):
       - Warm tan flat roof membrane with silver rooftop HVAC duct network and red entrance canopy at (225.2, 675.2).
    """
    bid = b_data["id"]
    pts = ensure_ccw(b_data["coords_xy"])
    mesh = bpy.data.meshes.new(f"Bldg_{bid}_SaintDenis_Corrugated_Mesh")
    obj = bpy.data.objects.new(f"Bldg_{bid}_SaintDenis_Corrugated", mesh)
    col.objects.link(obj)

    mats = [
        pal["Mat_MTL_WarmBuff_Limestone"],        # 0: Cream/warm-beige corrugated metal & masonry panels
        pal["Mat_MTL_Roof_Warm_Tan"],             # 1: Warm tan roof membrane (matches satellite H2..H4 V2..V4)
        pal["Mat_MTL_Window_Glass_Dark"],         # 2: Deeply recessed reflective glass
        pal["Mat_MTL_Dark_Bronze_CurtainWall"],   # 3: Dark window frames & rectangular vent louver
        pal["Mat_MTL_Weathered_Metal"],           # 4: Silver rooftop HVAC ductwork
        pal["Mat_MTL_Awning_Red"],                # 5: Bright red entrance canopy at west corner (matches satellite H4 V2)
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()
    total_h = 10.8

    # 1. Core building mass inset by 0.28m so the deeply recessed window glass at -0.16m is NEVER occluded!
    core_pts = inset_polygon_2d(pts, 0.28)
    extrude_prism_in_bm(bm, core_pts, -0.25, total_h, mat_side=0, mat_top=0, cap_top=False)
    inner_roof = inset_polygon_2d(pts, 0.38)
    extrude_prism_in_bm(bm, inner_roof, total_h - 0.32, total_h - 0.14, mat_side=0, mat_top=1, cap_top=True)

    # Rooftop silver HVAC ducting & chiller units (visible in satellite_topdown.png H2..H4, V3..V4)
    add_box_between(bm, (244.0, 674.0), (258.5, 682.5), total_h - 0.14, total_h + 1.15, thickness=3.6, mat_idx=4)
    add_box_between(bm, (254.0, 672.0), (262.0, 686.0), total_h - 0.14, total_h + 0.95, thickness=2.8, mat_idx=4)
    for rx, ry in ((236.0, 678.0), (242.0, 684.0), (249.0, 690.0), (258.0, 692.0)):
        add_oriented_box(bm, (rx, ry, total_h + 0.45), (0.88, -0.47), (0.47, 0.88), 3.2, 2.2, 1.05, mat_idx=4)
    # Bright red square entrance canopy at west corner (visible at H3..H4, V2 in satellite_topdown.png!)
    add_box_between(bm, (223.2, 673.2), (227.5, 675.8), 3.40, 3.85, thickness=3.8, mat_idx=5)

    # 2. Exact Close-Up Articulation on the Rue Saint-Denis Edge ((261.9, 667.1) -> (267.1, 678.1))
    # Camera 1 is at (266.433, 671.526) looking WNW (heading 288 deg), hitting this edge at s ~ 6.0m!
    p1 = (261.88, 667.12)
    p2 = (267.14, 678.08)
    seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])  # ~12.15m
    dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len

    def edge_pt(s):
        return (p1[0] + dx * s, p1[1] + dy * s)

    # Horizontal spandrel bands across full width (offset_out = +0.20m):
    for sp_z0, sp_z1 in ((2.35, 3.12), (4.65, 5.45), (6.95, total_h)):
        add_box_between(bm, p1, p2, sp_z0, sp_z1, thickness=0.44, offset_out=0.16, mat_idx=0)
        n_flutes = int(seg_len / 0.16)
        for fi in range(n_flutes):
            fs0 = fi * 0.16
            add_box_between(bm, edge_pt(fs0), edge_pt(fs0 + 0.06), sp_z0, sp_z1, thickness=0.50, offset_out=0.20, mat_idx=0)

    # Solid vertical piers at Left (s=0..2.45m), Center (s=5.20..6.50m), and Right (s=9.45..seg_len):
    for pr_s0, pr_s1 in ((0.0, 2.45), (5.20, 6.50), (9.45, seg_len)):
        add_box_between(bm, edge_pt(pr_s0), edge_pt(pr_s1), 0.15, total_h, thickness=0.44, offset_out=0.16, mat_idx=0)
        # Smooth lower panel on Center & Right piers (Z = 0.15m .. 1.15m, visible in H7..H8 V3..V5 of Cam 1)
        add_box_between(bm, edge_pt(pr_s0), edge_pt(pr_s1), 0.15, 1.15, thickness=0.52, offset_out=0.22, mat_idx=0)
        # Vertical corrugation flutes on piers above Z = 1.15m
        n_pflutes = int((pr_s1 - pr_s0) / 0.16)
        for fi in range(n_pflutes):
            fs0 = pr_s0 + fi * 0.16
            add_box_between(bm, edge_pt(fs0), edge_pt(fs0 + 0.06), 1.15, total_h, thickness=0.50, offset_out=0.20, mat_idx=0)

    # Dark rectangular ventilation louver at top of Center pier (s = 5.25..5.90m, Z = 4.22m..4.58m, V4 H2 in Cam 1!)
    add_box_between(bm, edge_pt(5.25), edge_pt(5.90), 4.22, 4.58, thickness=0.54, offset_out=0.23, mat_idx=3)

    # Two 3-Pane Window Bays: Left Bay (s = 2.45..5.20m) and Right Bay (s = 6.50..9.45m)
    for wb_s0, wb_s1 in ((2.45, 5.20), (6.50, 9.45)):
        # Recessed dark reflective glass on Ground (0.22..2.35m), 2nd (3.12..4.65m), and 3rd (5.45..6.95m) floors
        # Because core_pts is inset by 0.28m, glass at offset_out = -0.14m sits 0.14m in front of core wall and 0.48m behind pier face!
        for wz0, wz1 in ((0.22, 2.35), (3.12, 4.65), (5.45, 6.95)):
            add_box_between(bm, edge_pt(wb_s0), edge_pt(wb_s1), wz0, wz1, thickness=0.10, offset_out=-0.14, mat_idx=2)
            # Projecting window sill & concrete base curb
            add_box_between(bm, edge_pt(wb_s0 - 0.05), edge_pt(wb_s1 + 0.05), wz0 - 0.08, wz0 + 0.06, thickness=0.54, offset_out=0.22, mat_idx=0)
            # Outer dark aluminum perimeter window frame + silver sash trim
            for jf in (0.03, 0.97):
                js = wb_s0 + (wb_s1 - wb_s0) * jf
                add_box_between(bm, edge_pt(js - 0.04), edge_pt(js + 0.04), wz0, wz1, thickness=0.18, offset_out=-0.04, mat_idx=4)
            # 2 Wide Cream Vertical Mullions dividing each bay into 3 vertical panes!
            for m_frac in (0.333, 0.667):
                ms = wb_s0 + (wb_s1 - wb_s0) * m_frac
                add_box_between(bm, edge_pt(ms - 0.08), edge_pt(ms + 0.08), wz0, wz1, thickness=0.42, offset_out=0.14, mat_idx=0)
                # Silver/dark inner window frame strips flanking each cream mullion
                add_box_between(bm, edge_pt(ms - 0.13), edge_pt(ms + 0.13), wz0, wz1, thickness=0.28, offset_out=0.04, mat_idx=4)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def build_berri_greystone_rowhouses(owned_bldgs, pal, col):
    """
    Constructs the historic 3-story Montreal Pierre Grise greystone rowhouses along the east side of Rue Berri
    (341114936, 341114944, 341115039, 341115198) framed directly in Street View Camera 3
    (Rue_Berri_Bonsecours_Link at [279.792, 698.867], heading 108 deg):
    - 3-story cut & rock-faced Pierre Grise limestone facades (Z = 0.0m .. 9.6m).
    - Steep dark slate mansard roofs (Z = 9.6m .. 11.8m) with pedimented dormer windows (H1..H2).
    - White multi-pane window sashes, blue-grey louvered wooden shutters & paneled entrance doors.
    - Open Montreal exterior wrought-iron staircases (escaliers extérieurs) & 2nd-floor balconies (H3..H7).
    - Front-yard stone planter wall with green shrubs & two parked sedans along the Rue Berri curb (H7..H8).
    """
    target_ids = {341114936, 341114944, 341115039, 341115198}
    row_bldgs = [b for b in owned_bldgs if b["id"] in target_ids]
    if not row_bldgs:
        return None

    mesh = bpy.data.meshes.new("Bldg_Berri_Greystone_Rowhouses_Mesh")
    obj = bpy.data.objects.new("Bldg_Berri_Greystone_Rowhouses", mesh)
    col.objects.link(obj)

    mat_shutter_blue = kit.get_or_create_pbr_material("Mat_MTL_Shutter_BlueGrey", "#5C7D96", roughness=0.45)
    mat_white_sash = kit.get_or_create_pbr_material("Mat_MTL_White_Sash_Berri", "#F0F2F4", roughness=0.32)
    mat_car_silver = kit.get_or_create_pbr_material("Mat_MTL_Car_Silver", "#C2C8D0", roughness=0.20, metallic=0.82)
    mat_car_dark = kit.get_or_create_pbr_material("Mat_MTL_Car_Charcoal", "#242C36", roughness=0.18, metallic=0.85)

    mats = [
        pal["Mat_MTL_PierreGrise_Limestone"],     # 0: Dressed Pierre Grise ashlar greystone
        pal["Mat_MTL_Medieval_Stone"],            # 1: Rock-faced rusticated greystone (right townhouse 341115039)
        pal["Mat_MTL_Slate_Roof_Dark"],           # 2: Dark slate mansard roof & dormers
        pal["Mat_MTL_Window_Glass_Dark"],         # 3: Recessed window glazing & car windshields
        pal["Mat_MTL_Dark_Bronze_CurtainWall"],   # 4: Black wrought-iron stairs, railings & bracketed cornice
        mat_shutter_blue,                         # 5: Blue-grey wooden shutters, doors & trim
        pal["Mat_MTL_Grass_Lawn_PBR"],            # 6: Front planter shrubs & ivy
        mat_car_silver,                           # 7: Left silver sedan (V1..V2, H7..H8)
        mat_car_dark,                             # 8: Center-right dark sedan (V3..V8, H7..H8)
        mat_white_sash,                           # 9: Crisp white multi-pane window sashes & dormer pediments
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    for b in row_bldgs:
        bid = b["id"]
        pts = ensure_ccw(b["coords_xy"])
        is_rusticated = (bid in (341115039, 341115198))
        wall_mat = 1 if is_rusticated else 0
        wall_h = 9.65 if is_rusticated else 9.35

        # Inset core wall by 0.26m so recessed windows (-0.14m) and sashes (-0.06m) are completely visible!
        core_pts = inset_polygon_2d(pts, 0.26)
        extrude_prism_in_bm(bm, core_pts, -0.25, wall_h, mat_side=wall_mat, mat_top=2, cap_top=True)
        # Mansard upper story / attic roof (Z = wall_h .. wall_h + 2.15m)
        mansard_top = inset_polygon_2d(pts, 0.55)
        extrude_prism_in_bm(bm, mansard_top, wall_h, wall_h + 2.15, mat_side=2, mat_top=2, cap_top=True)

        # Find the west street-facing edge along Rue Berri (min X edge)
        n = len(pts)
        west_edge = None
        min_mid_x = 1e9
        for i in range(n):
            p1, p2 = pts[i], pts[(i + 1) % n]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 4.0:
                mx = 0.5 * (p1[0] + p2[0])
                if mx < min_mid_x:
                    min_mid_x = mx
                    west_edge = (p1, p2)

        if west_edge:
            p1, p2 = west_edge
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len

            # Build the front greystone piers at Left (0..0.15), Center (0.41..0.59), Right (0.85..1.0)
            for ps0, ps1 in ((0.0, 0.15 * seg_len), (0.41 * seg_len, 0.59 * seg_len), (0.85 * seg_len, seg_len)):
                pp1 = (p1[0] + dx * ps0, p1[1] + dy * ps0)
                pp2 = (p1[0] + dx * ps1, p1[1] + dy * ps1)
                add_box_between(bm, pp1, pp2, 0.0, wall_h, thickness=0.48, offset_out=0.14, mat_idx=wall_mat)
            # Horizontal stone spandrel bands between floors
            for sz0, sz1 in ((0.0, 0.85), (2.55, 3.35), (5.45, 6.25), (8.25, wall_h)):
                add_box_between(bm, p1, p2, sz0, sz1, thickness=0.48, offset_out=0.14, mat_idx=wall_mat)

            # Dark bracketed cornice at wall_h + white dentil trim
            add_box_between(bm, p1, p2, wall_h - 0.30, wall_h + 0.14, thickness=0.68, offset_out=0.28, mat_idx=4)
            add_box_between(bm, p1, p2, wall_h - 0.42, wall_h - 0.30, thickness=0.56, offset_out=0.22, mat_idx=9)

            # 2 Window Bays across each townhouse front (0.15..0.41 and 0.59..0.85)
            for b_i, (f0, f1) in enumerate(((0.15, 0.41), (0.59, 0.85))):
                s0, s1 = seg_len * f0, seg_len * f1
                s_c = 0.5 * (s0 + s1)
                w_p1 = (p1[0] + dx * s0, p1[1] + dy * s0)
                w_p2 = (p1[0] + dx * s1, p1[1] + dy * s1)

                # 3 Floors of deeply recessed windows (pier face at +0.38m, glass at -0.12m -> 0.50m reveal!)
                for fl_idx, (fz0, fz1) in enumerate(((0.85, 2.55), (3.35, 5.45), (6.25, 8.25))):
                    add_box_between(bm, w_p1, w_p2, fz0, fz1, thickness=0.10, offset_out=-0.12, mat_idx=3)
                    # Crisp white window frame & multi-pane sash crossbars (mat_idx=9)
                    add_box_between(bm, w_p1, w_p2, 0.5 * (fz0 + fz1) - 0.04, 0.5 * (fz0 + fz1) + 0.04, thickness=0.16, offset_out=-0.04, mat_idx=9)
                    mp1 = (p1[0] + dx * (s_c - 0.04), p1[1] + dy * (s_c - 0.04))
                    mp2 = (p1[0] + dx * (s_c + 0.04), p1[1] + dy * (s_c + 0.04))
                    add_box_between(bm, mp1, mp2, fz0, fz1, thickness=0.16, offset_out=-0.04, mat_idx=9)
                    # Projecting stone sill & lintel
                    add_box_between(bm, w_p1, w_p2, fz0 - 0.14, fz0 + 0.04, thickness=0.56, offset_out=0.22, mat_idx=0)
                    add_box_between(bm, w_p1, w_p2, fz1 - 0.04, fz1 + 0.22, thickness=0.58, offset_out=0.24, mat_idx=0)
                    # Blue-grey louvered wooden shutters (persiennes) on 2nd & 3rd floors of 341114944 / 341114936
                    if not is_rusticated and fl_idx in (1, 2):
                        sh_l1 = (p1[0] + dx * (s0 - 0.36), p1[1] + dy * (s0 - 0.36))
                        sh_l2 = (p1[0] + dx * s0, p1[1] + dy * s0)
                        sh_r1 = (p1[0] + dx * s1, p1[1] + dy * s1)
                        sh_r2 = (p1[0] + dx * (s1 + 0.36), p1[1] + dy * (s1 + 0.36))
                        add_box_between(bm, sh_l1, sh_l2, fz0, fz1, thickness=0.12, offset_out=0.40, mat_idx=5)
                        add_box_between(bm, sh_r1, sh_r2, fz0, fz1, thickness=0.12, offset_out=0.40, mat_idx=5)
                    elif is_rusticated and b_i == 0 and fl_idx in (0, 1):
                        # Blue-grey paneled entrance door & arched fanlight transom
                        add_box_between(bm, w_p1, w_p2, fz0 - 0.45, fz1 - 0.35, thickness=0.14, offset_out=-0.06, mat_idx=5)
                        add_box_between(bm, w_p1, w_p2, fz1 - 0.40, fz1 - 0.28, thickness=0.22, offset_out=0.02, mat_idx=9)

                # Mansard Roof Dormer Window with Pedimented Cap & White Sash (Z = wall_h - 0.05 .. wall_h + 1.95m, H1..H2 in Cam 3!)
                add_box_between(bm, w_p1, w_p2, wall_h - 0.05, wall_h + 1.65, thickness=0.65, offset_out=0.12, mat_idx=2)
                add_box_between(bm, w_p1, w_p2, wall_h + 0.15, wall_h + 1.45, thickness=0.16, offset_out=0.42, mat_idx=3)
                add_box_between(bm, w_p1, w_p2, wall_h + 0.78, wall_h + 0.86, thickness=0.20, offset_out=0.45, mat_idx=9)
                add_box_between(bm, w_p1, w_p2, wall_h + 1.60, wall_h + 1.92, thickness=0.78, offset_out=0.24, mat_idx=9)

    # Open Wrought-Iron Exterior Staircases (Escaliers Extérieurs), Thin Balconies & Front Planter (Cam 3 H3..H7):
    # (a) Open wrought-iron stair & thin 2nd-floor balcony platform on 341114944 (V1..V4 in Cam 3)
    add_box_between(bm, (291.2, 704.0), (290.4, 702.2), 3.05, 3.18, thickness=1.25, offset_out=0.75, mat_idx=4)
    # Thin open top handrail & vertical balusters (NOT a solid block!)
    add_box_between(bm, (291.2, 704.0), (290.4, 702.2), 3.95, 4.02, thickness=0.08, offset_out=1.32, mat_idx=4)
    for st_i in range(11):
        t = st_i / 10.0
        sx = 291.4 - t * 0.75
        sy = 706.8 - t * 2.50
        sz = 0.22 + t * 2.85
        add_oriented_box(bm, (sx, sy, sz), (-0.30, -0.95), (-0.95, 0.30), 0.26, 0.92, 0.05, mat_idx=4)
        add_oriented_box(bm, (sx - 0.40, sy + 0.12, sz + 0.42), (-0.30, -0.95), (-0.95, 0.30), 0.04, 0.04, 0.84, mat_idx=4)
    # Low stone planter box with green shrubs under the stair (V2..V3, H6..H7 in Cam 3)
    add_box_between(bm, (290.8, 705.6), (290.0, 703.8), 0.15, 0.52, thickness=0.95, offset_out=0.85, mat_idx=0)
    add_box_between(bm, (290.7, 705.4), (290.1, 704.0), 0.52, 0.98, thickness=0.75, offset_out=0.85, mat_idx=6)

    # (b) Open exterior stair & thin 2nd-floor cantilevered balcony on 341115039 (V4..V6 in Cam 3)
    add_box_between(bm, (290.1, 701.6), (289.2, 699.6), 5.65, 5.78, thickness=1.15, offset_out=0.68, mat_idx=5)
    add_box_between(bm, (290.1, 701.6), (289.2, 699.6), 6.50, 6.58, thickness=0.08, offset_out=1.20, mat_idx=4)
    for st_i in range(10):
        t = st_i / 9.0
        sx = 288.2 + t * 1.35
        sy = 701.4 - t * 0.42
        sz = 0.20 + t * 2.90
        add_oriented_box(bm, (sx, sy, sz), (0.95, -0.30), (0.30, 0.95), 0.24, 0.95, 0.05, mat_idx=4)
        add_oriented_box(bm, (sx, sy + 0.44, sz + 0.42), (0.95, -0.30), (0.30, 0.95), 0.04, 0.04, 0.84, mat_idx=4)

    # (c) Two Parked Sedans along the Rue Berri Curb in Camera 3 Foreground (H6..H8, V1..V2 and V3..V8)
    # Camera 3 is at (279.792, 698.867) looking ESE (heading 108 deg, ray dir = (+0.951, -0.309)).
    # Left Silver Sedan at (283.6, 699.9) -> projects directly into V1..V2, H6..H8!
    add_oriented_box(bm, (283.6, 699.9, 0.56), (-0.42, -0.91), (0.91, -0.42), 4.1, 1.72, 0.68, mat_idx=7)
    add_oriented_box(bm, (283.7, 700.1, 1.08), (-0.42, -0.91), (0.91, -0.42), 2.1, 1.50, 0.48, mat_idx=3)
    # Center-Right Dark Charcoal Sedan at (285.0, 695.9) -> projects directly into V3..V8, H7..H8!
    add_oriented_box(bm, (285.0, 695.9, 0.55), (-0.42, -0.91), (0.91, -0.42), 4.4, 1.78, 0.68, mat_idx=8)
    add_oriented_box(bm, (285.1, 696.0, 1.08), (-0.42, -0.91), (0.91, -0.42), 2.3, 1.54, 0.48, mat_idx=3)
    # Additional street-side parked cars along Rue Saint-Denis & Rue Berri for Satellite Top-Down parity (V3, V5, V7):
    for cx_car, cy_car, m_car in (
        (235.0, 712.0, 7), (242.0, 702.0, 8), (255.0, 682.0, 7),
        (262.0, 672.0, 8), (275.0, 652.0, 7), (294.0, 678.0, 8),
        (304.0, 662.0, 7), (248.0, 646.0, 8), (232.0, 636.0, 7),
    ):
        add_oriented_box(bm, (cx_car, cy_car, 0.58), (0.50, -0.86), (0.86, 0.50), 4.2, 1.75, 0.72, mat_idx=m_car)
        add_oriented_box(bm, (cx_car, cy_car, 1.12), (0.50, -0.86), (0.86, 0.50), 2.1, 1.52, 0.48, mat_idx=3)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def build_detailed_victorian_row_building(b_data, mat_wall, other_polys, pal, col):
    """
    Constructs an authentic Victorian row building with:
    - Recessed window bays (reveal depth >= 0.46m to 0.50m).
    - Stepped heights (11m to 18m, 3 to 5 floors) ensuring zero coplanar belt-courses.
    - Satellite-matched roof colors (white reflective roof for 341114673 & 341114763, silver standing-seam roof for
      341114074, 341114273, 341114511, warm tan roof for 87394920, 341116329, 341116871, 1268191776).
    - Party-wall detection: piers, sills, and bays suppressed on shared walls.
    - Flat roof deck inset >= 0.35m inside parapet, offset 0.53m below parapet cap (zero Z-fighting).
    """
    bid = b_data["id"]
    pts = ensure_ccw(b_data["coords_xy"])
    tags = b_data.get("tags", {})
    levels_str = tags.get("building:levels")
    try:
        levels = max(3, int(float(levels_str))) if levels_str else (3 + (bid % 3))
    except ValueError:
        levels = 3 + (bid % 3)

    if bid == 87394920:
        levels = 5
    elif bid in (341114673, 341114511):
        levels = 4

    # Stepped height deterministically varied by OSM ID
    fl_h = 3.20 + ((bid % 7) * 0.08)  # 3.20m to 3.68m
    total_h = levels * fl_h

    mesh = bpy.data.meshes.new(f"Bldg_{bid}_Mesh")
    bname = b_data.get("name") or f"Row_{bid}"
    obj = bpy.data.objects.new(f"Bldg_{bid}_{bname[:20]}", mesh)
    col.objects.link(obj)

    # Select satellite-matched roof membrane material
    if bid in (341114673, 341114763, 341116158, 341116132, 341117033, 341117057):
        roof_mat = pal["Mat_MTL_Roof_White_Reflective"]
    elif bid in (341114074, 341114273, 341114511):
        roof_mat = pal["Mat_MTL_Roof_Silver_Seam"]
    elif bid in (87394920, 341116329, 341116871, 1268191776, 396642829):
        roof_mat = pal["Mat_MTL_Roof_Warm_Tan"]
    else:
        roof_mat = pal["Mat_MTL_Roof_Membrane"]

    mats = [
        mat_wall,                                 # 0: Wall material from graph coloring
        roof_mat,                                 # 1: Satellite-matched inset roof membrane
        pal["Mat_MTL_Window_Glass_Dark"],         # 2: Glazing
        pal["Mat_MTL_Dark_Bronze_CurtainWall"],   # 3: Window frames & mullions
        pal["Mat_MTL_PierreGrise_Limestone"],     # 4: Sills, lintels & cornice trim
        pal["Mat_MTL_Granite_Plinth"],            # 5: Ground plinth
        pal["Mat_MTL_Weathered_Metal"],           # 6: Rooftop mechanical units & standing-seam ribs
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Main outer envelope (Z = -0.25m to height) without uninset top cap
    extrude_prism_in_bm(bm, pts, -0.25, total_h, mat_side=0, mat_top=4, cap_top=False)

    # 2. Inset roof (inset >= 0.35m, 0.20m below parapet cap)
    inner_roof = inset_polygon_2d(pts, 0.35)
    extrude_prism_in_bm(bm, inner_roof, total_h - 0.30, total_h - 0.12, mat_side=0, mat_top=1, cap_top=True)

    # Special satellite-matched roof articulations:
    xs_r = [p[0] for p in inner_roof]
    ys_r = [p[1] for p in inner_roof]
    cx_r, cy_r = sum(xs_r) / len(xs_r), sum(ys_r) / len(ys_r)
    if bid == 341114673:
        # Central bright white hipped/stepped roof pyramid in H4..H6, V4..V6 of satellite_topdown.png!
        hip_inner = inset_polygon_2d(inner_roof, 3.8)
        if len(hip_inner) >= 3:
            extrude_prism_in_bm(bm, hip_inner, total_h - 0.12, total_h + 1.45, mat_side=1, mat_top=1, cap_top=True)
        for rx_o, ry_o in ((-5.5, -3.5), (5.5, 3.5), (-4.0, 5.0), (4.0, -5.0)):
            add_oriented_box(bm, (cx_r + rx_o, cy_r + ry_o, total_h + 0.55), (0.45, 0.89), (-0.89, 0.45), 2.4, 1.8, 0.95, mat_idx=6)
    elif bid in (341114511, 341114074, 341114273):
        # Pitched silver standing-seam metal roof with ridge line, ribs, and dormers along Rue Bonsecours (H4..H7, V6..V8)
        seam_inner = inset_polygon_2d(inner_roof, 1.8)
        if len(seam_inner) >= 3:
            extrude_prism_in_bm(bm, seam_inner, total_h - 0.12, total_h + 1.65, mat_side=1, mat_top=1, cap_top=True)
        for rib_i in range(-6, 7):
            add_oriented_box(bm, (cx_r + rib_i * 0.65, cy_r + rib_i * 1.45, total_h + 0.85), (0.91, -0.41), (0.41, 0.91), 7.5, 0.14, 1.55, mat_idx=6)
    elif polygon_area_2d(inner_roof) > 85.0:
        # Add realistic rooftop HVAC units, elevator overrides, and skylights on all flat roofs for Satellite Top-Down parity
        add_oriented_box(bm, (cx_r, cy_r, total_h + 0.65), (0.45, 0.89), (-0.89, 0.45), 3.4, 2.4, 1.25, mat_idx=6)
        add_oriented_box(bm, (cx_r + 3.2, cy_r - 2.2, total_h + 0.40), (0.45, 0.89), (-0.89, 0.45), 2.2, 1.6, 0.80, mat_idx=3)

    # 3. Facade detailing with deep recessed bays
    n = len(pts)
    ground_h = min(4.0, max(2.8, fl_h))
    n_upper = max(1, levels - 1)
    upper_fl_h = (total_h - ground_h) / n_upper

    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]

        # Party-wall suppression: skip protrusions on shared abutting walls
        if other_polys and is_party_wall(p1, p2, other_polys):
            continue

        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.5:
            continue

        dx = (p2[0] - p1[0]) / seg_len
        dy = (p2[1] - p1[1]) / seg_len

        # Plinth & belt course at ground floor
        add_box_between(bm, p1, p2, 0.0, 0.85, thickness=0.45, offset_out=0.18, mat_idx=5)
        add_box_between(bm, p1, p2, ground_h - 0.35, ground_h + 0.12, thickness=0.45, offset_out=0.18, mat_idx=4)

        n_bays = max(1, int(round(seg_len / 3.4)))
        bay_w = seg_len / n_bays
        pier_w = min(1.0, max(0.40, bay_w * 0.32))

        # Vertical piers (offset out +0.24m)
        for b in range(n_bays + 1):
            cs = b * bay_w
            s0 = max(0.0, cs - pier_w * 0.5)
            s1 = min(seg_len, cs + pier_w * 0.5)
            if s1 - s0 < 0.08:
                continue
            q1 = (p1[0] + dx * s0, p1[1] + dy * s0)
            q2 = (p1[0] + dx * s1, p1[1] + dy * s1)
            add_box_between(bm, q1, q2, 0.85, total_h - 0.35, thickness=0.68, offset_out=0.24, mat_idx=0)

        # Recessed window bays (outer pier at +0.24m, glass at -0.22m -> 0.46m reveal!)
        for b in range(n_bays):
            bs0 = b * bay_w + pier_w * 0.5
            bs1 = (b + 1) * bay_w - pier_w * 0.5
            if bs1 - bs0 < 0.28:
                continue
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)

            # Deep recessed window glass
            add_box_between(bm, wp1, wp2, 0.85, total_h - 0.35, thickness=0.10, offset_out=-0.22, mat_idx=2)
            # Central mullion
            ms = (bs0 + bs1) * 0.5
            mp1 = (p1[0] + dx * (ms - 0.04), p1[1] + dy * (ms - 0.04))
            mp2 = (p1[0] + dx * (ms + 0.04), p1[1] + dy * (ms + 0.04))
            add_box_between(bm, mp1, mp2, 0.85, total_h - 0.35, thickness=0.16, offset_out=-0.08, mat_idx=3)

            # Upper floors: sills & lintels
            for fl in range(n_upper):
                fz0 = ground_h + fl * upper_fl_h
                fz1 = fz0 + upper_fl_h
                # Spandrel
                add_box_between(bm, wp1, wp2, fz0, fz0 + 0.75, thickness=0.35, offset_out=0.16, mat_idx=0)
                # Protruding stone sill (+0.22m)
                add_box_between(bm, wp1, wp2, fz0 + 0.68, fz0 + 0.84, thickness=0.30, offset_out=0.22, mat_idx=4)
                # Lintel stone slab
                add_box_between(bm, wp1, wp2, fz1 - 0.38, fz1, thickness=0.30, offset_out=0.18, mat_idx=4)

        # Cornice & parapet
        add_box_between(bm, p1, p2, total_h - 0.45, total_h + 0.12, thickness=0.40, offset_out=0.15, mat_idx=4)
        add_box_between(bm, p1, p2, total_h + 0.12, total_h + 0.38, thickness=0.25, offset_out=0.06, mat_idx=0)

    bm.to_mesh(mesh)
    bm.free()
    return obj


# ---------------------------------------------------------------------------
# 5. STREET NETWORK, PARK LAWNS & WATERTIGHT GROUND STRATUM
# ---------------------------------------------------------------------------

def build_ground_and_streets(dossier, owned_bldgs, pal, col):
    """
    Constructs the complete street network, lush green park lawns, and watertight ground stratum:
    - Continuous watertight solid base (Z = -0.25m .. 0.00m) with upward (+Z) normals.
    - Lush green park lawns (Mat_MTL_Grass_Lawn_PBR with leafy_grass_Diffuse_2k.jpg at Z = +0.195m),
      granite curbs (Z = +0.225m), and non-coplanar crushed-stone paths (Mat_PH_Gravel_Path at Z = +0.255m).
    - Continuous Poly Haven PBR asphalt roadbeds (asphalt_02) on surface roads.
    - Raised concrete/granite sidewalks (+0.15m) with 3D bevelled granite curbs.
    - White zebra pedestrian crosswalks at street intersections.
    """
    mesh = bpy.data.meshes.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"MTL_Owned_Ground_And_Streets_{BLOCK_ID}", mesh)
    col.objects.link(obj)

    mats = [
        pal["Mat_MTL_Street_Asphalt"],          # 0: Continuous PBR asphalt
        pal["Mat_MTL_Cobblestone"],             # 1: Historic cobblestone intersections
        pal["Mat_MTL_Plaza_Light_Granite"],     # 2: Raised sidewalks (+0.15m)
        pal["Mat_MTL_PierreGrise_Limestone"],   # 3: 3D granite curbs (+0.225m)
        kit.get_or_create_pbr_material("Mat_Road_Paint_Yellow", "#E5B824", roughness=0.55),  # 4: Yellow centerline
        kit.get_or_create_pbr_material("Mat_Road_Paint_White", "#F0F0F2", roughness=0.50),   # 5: White crosswalk
        pal["Mat_MTL_Grass_Lawn_PBR"],          # 6: Lush green park lawns (leafy_grass_Diffuse_2k.jpg, Z = +0.195m)
        pal["Mat_PH_Gravel_Path"],              # 7: Crushed-stone park walkways & playground oval (Z = +0.255m)
        pal["Mat_PH_Herringbone_Pavement"],     # 8: Warm terracotta/brick courtyard terrace (Z = +0.220m)
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Watertight Solid Ground Base (Z = -0.25m .. 0.00m)
    # Covering full block extent (X: [-150, 420], Y: [500, 870])
    base_corners = [
        (-150.0, 500.0),
        (420.0, 500.0),
        (420.0, 870.0),
        (-150.0, 870.0),
    ]
    extrude_prism_in_bm(bm, base_corners, -0.25, 0.00, mat_side=0, mat_top=0, cap_top=True, cap_bottom=True)

    # 2. Lush Green Park Lawns (Z = +0.195m), Granite Curbs (Z = +0.225m), and Crushed-Stone Paths (Z = +0.255m)
    #    matching satellite_topdown.png (H1..H3 V1..V2, H4..H5 V1, H1..H4 V6..V8, H7..H8 V4..V5)
    park_lawn_polys = [
        # (a) Top-Left Park & Playground Lawn (H1..H3, V1..V2: X = 196..226, Y = 678..724)
        [(196.0, 680.0), (212.0, 678.0), (226.5, 706.0), (218.0, 723.5), (196.0, 723.5)],
        # (b) Champ-de-Mars East Edge Lawn Strip (H4..H5, V1: X = 196..204, Y = 648..662)
        [(195.5, 648.5), (204.2, 653.5), (199.5, 662.5), (195.5, 660.5)],
        # (c) East Berri-Bonsecours Courtyard Grove Lawn (H2..H4, V6..V7: X = 296..322, Y = 664..692)
        [(296.0, 664.0), (317.0, 660.0), (322.5, 686.0), (301.5, 691.5)],
        # (d) South-Center Chaussegros-de-Léry Courtyard Lawn (H7..H8, V4..V5: X = 259..274, Y = 586..606)
        [(258.5, 586.0), (266.0, 582.5), (275.5, 601.5), (268.0, 606.0)],
    ]
    for lp in park_lawn_polys:
        extrude_prism_in_bm(bm, lp, 0.00, 0.195, mat_side=3, mat_top=6, cap_top=True, cap_bottom=False)
        for i in range(len(lp)):
            add_box_between(bm, lp[i], lp[(i + 1) % len(lp)], 0.00, 0.225, thickness=0.28, mat_idx=3, cap_bottom=False)

    # Crushed-stone playground & walkway patches (Z = +0.255m, non-coplanar above Z = +0.195m lawn!)
    gravel_patches = [
        # Playground sand/gravel court in Top-Left Park (H1, V1..V2: X = 204..216, Y = 708..718)
        [(204.5, 708.5), (215.5, 707.5), (217.0, 717.5), (205.5, 718.5)],
        # Crushed-stone diagonal park path in Top-Left Park (H2, V1..V2)
        [(198.5, 686.0), (202.5, 684.5), (214.0, 708.0), (210.0, 709.5)],
    ]
    for gp in gravel_patches:
        extrude_prism_in_bm(bm, gp, 0.195, 0.255, mat_side=3, mat_top=7, cap_top=True, cap_bottom=False)
        for i in range(len(gp)):
            add_box_between(bm, gp[i], gp[(i + 1) % len(gp)], 0.195, 0.225, thickness=0.22, offset_out=0.12, mat_idx=3, cap_bottom=False)

    # Warm brick courtyard terrace behind Berri rowhouses (visible in H2..H3, V6..V7 of satellite_topdown.png: X = 302..318, Y = 688..706)
    brick_courtyard = [(301.5, 688.0), (316.5, 682.5), (322.0, 698.0), (306.5, 704.5)]
    extrude_prism_in_bm(bm, brick_courtyard, 0.00, 0.220, mat_side=3, mat_top=8, cap_top=True, cap_bottom=False)

    # 3. Roadbed Network & Sidewalks from OSM Highways (Surface only)
    highways = dossier.get("osm_features", {}).get("highways", [])
    bldg_polys = [b["coords_xy"] for b in owned_bldgs]

    for hw in highways:
        if hw.get("tags", {}).get("tunnel") == "yes":
            continue
        pts = hw.get("coords_xy", [])
        if len(pts) < 2:
            continue
        name = hw.get("name") or hw.get("tags", {}).get("name", "").lower()
        hw_type = hw.get("tags", {}).get("highway", "residential")

        is_ped = hw_type in ("footway", "pedestrian", "path", "steps")
        is_cobble = any(c in name for c in ("bonsecours", "champ-de-mars", "saint-louis", "guy-frégault"))
        road_mat = 1 if is_cobble else 0

        # Road width based on classification
        if is_ped:
            rw = 2.4
        elif "saint-denis" in name:
            rw = 14.5
        elif "saint-antoine" in name:
            rw = 16.0
        elif "berri" in name:
            rw = 13.5
        elif "notre-dame" in name:
            rw = 12.0
        elif "gosford" in name:
            rw = 14.0
        else:
            rw = 9.5

        for k in range(len(pts) - 1):
            p1 = pts[k]
            p2 = pts[k + 1]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 0.3:
                continue
            dx = (p2[0] - p1[0]) / seg_len
            dy = (p2[1] - p1[1]) / seg_len
            nx, ny = dy, -dx

            if is_ped:
                # Pedestrian pathway / sidewalk (Z = 0.00..0.15m)
                add_box_between(bm, p1, p2, 0.0, 0.15, thickness=rw, offset_out=0.0, mat_idx=2, cap_bottom=False)
            else:
                # Drivable roadbed (Z = 0.00..0.015m)
                add_box_between(bm, p1, p2, -0.01, 0.015, thickness=rw, offset_out=0.0, mat_idx=road_mat, cap_bottom=False)

                # Yellow double centerline
                if rw >= 10.0 and not is_cobble:
                    add_box_between(bm, p1, p2, 0.012, 0.018, thickness=0.22, offset_out=0.0, mat_idx=4, cap_bottom=False)

                # Raised granite sidewalks (+0.15m) and 3D granite curbs bordering roadway flanks
                sw_width = 3.2
                curb_width = 0.20
                for sgn in (-1.0, 1.0):
                    sw_offset = sgn * (rw * 0.5 + sw_width * 0.5)
                    curb_offset = sgn * (rw * 0.5 + curb_width * 0.5)

                    # Check anti-clipping: if sidewalk center is inside any building footprint (+0.02m), skip!
                    mid_sw = (
                        (p1[0] + p2[0]) * 0.5 + nx * sw_offset,
                        (p1[1] + p2[1]) * 0.5 + ny * sw_offset,
                    )
                    inside_bldg = any(point_to_poly_dist_2d(mid_sw[0], mid_sw[1], b) < 0.05 for b in bldg_polys)
                    if not inside_bldg:
                        # Raised sidewalk slab (+0.15m)
                        add_box_between(bm, p1, p2, 0.0, 0.15, thickness=sw_width, offset_out=sw_offset, mat_idx=2, cap_bottom=False)
                        # 3D bevelled curb stone (+0.16m)
                        add_box_between(bm, p1, p2, 0.0, 0.16, thickness=curb_width, offset_out=curb_offset, mat_idx=3, cap_bottom=False)

    # 4. Camera-Specific Sidewalk & Curb Foregrounds for Cam 2, Cam 3 & Cam 4:
    # Cam 2 (Rue_SaintAntoineEst_Escarpment at [199.812, 641.622], heading 115 deg):
    # Wide concrete sidewalk (Z = 0.155m) with dark expansion joint lines & granite curb (Z = 0.175m)
    add_box_between(bm, (196.0, 628.0), (212.5, 648.0), 0.0, 0.155, thickness=4.8, offset_out=-2.4, mat_idx=2, cap_bottom=False)
    add_box_between(bm, (196.0, 628.0), (212.5, 648.0), 0.0, 0.175, thickness=0.26, offset_out=-4.8, mat_idx=3, cap_bottom=False)
    # Cam 4 (Champ_de_Mars_East_Edge at [224.464, 591.785], heading 288 deg):
    # Raised granite sidewalk along the SE facade of 161204910 (Z = 0.155m) & curb (Z = 0.175m)
    add_box_between(bm, (212.0, 584.0), (228.0, 612.0), 0.0, 0.155, thickness=4.2, offset_out=2.1, mat_idx=2, cap_bottom=False)
    add_box_between(bm, (212.0, 584.0), (228.0, 612.0), 0.0, 0.175, thickness=0.25, offset_out=4.2, mat_idx=3, cap_bottom=False)

    # 5. White Zebra Crosswalks at Major Intersections (Rue Saint-Denis & Saint-Antoine)
    crosswalk_intersections = [
        (266.0, 672.0, (0.866, -0.500), (0.500, 0.866)),  # Saint-Denis & Saint-Antoine
        (280.0, 698.0, (0.866, -0.500), (0.500, 0.866)),  # Berri & Saint-Antoine
        (200.0, 642.0, (0.500, 0.866), (-0.866, 0.500)),  # Saint-Antoine & Gosford
    ]
    for ix, iy, dir_xy, norm_xy in crosswalk_intersections:
        for cw_k in range(-5, 6):
            cwx = ix + dir_xy[0] * (cw_k * 1.15)
            cwy = iy + dir_xy[1] * (cw_k * 1.15)
            add_oriented_box(bm, (cwx, cwy, 0.020), norm_xy, dir_xy, 4.8, 0.55, 0.005, mat_idx=5, cap_bottom=False)

    bm.to_mesh(mesh)
    bm.free()
    return obj


# ---------------------------------------------------------------------------
# 6. REAL POLY HAVEN 3D TREES, STREETLAMPS & BENCHES
# ---------------------------------------------------------------------------

def load_combined_polyhaven_templates():
    """
    Loads and merges jacaranda_tree (trunk + branches + summer green foliage canopy),
    street_lamp_01, and modular_street_seating from assets/polyhaven/models into single
    recentered shared Mesh data-blocks.
    """
    combined_tree_mesh = None
    ph_tree_blend = os.path.join(POLYHAVEN_DIR, "models", "jacaranda_tree", "jacaranda_tree.blend")
    if os.path.isfile(ph_tree_blend):
        with bpy.data.libraries.load(ph_tree_blend, link=False) as (df, dt):
            dt.objects = list(df.objects)
        loaded_objs = [o for o in dt.objects if o and o.type == "MESH" and o.data]
        if loaded_objs:
            raw_tree_mesh = bpy.data.meshes.new("Combined_Jacaranda_Tree_Mesh")
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


def spawn_trees_and_props(dossier, owned_bldgs, col):
    """
    Appends real Poly Haven 3D assets (jacaranda_tree with lush green foliage, street_lamp_01,
    modular_street_seating) matching both surveyed OSM trees and the dense park/courtyard canopies
    in satellite_topdown.png.
    """
    tree_mesh, lamp_mesh, bench_mesh = load_combined_polyhaven_templates()
    bldg_polys = [b["coords_xy"] for b in owned_bldgs]
    highways = dossier.get("osm_features", {}).get("highways", [])

    # 1. Exact Satellite-Matched Park & Courtyard Canopy Trees (H1..H4 V1..V2, H3..H5 V2..V3, H1..H4 V6..V8)
    satellite_trees = [
        # Top-Left Park & Playground Canopy (H1..H3, V1..V2: X = 198..225, Y = 682..722)
        (202.0, 685.0, 0.52), (208.0, 688.0, 0.56), (201.0, 695.0, 0.58),
        (209.0, 698.0, 0.55), (216.0, 696.0, 0.52), (201.5, 706.0, 0.56),
        (219.0, 704.0, 0.54), (202.0, 718.0, 0.58), (214.0, 720.0, 0.56),
        # Central Plaza Tree Cluster along Rue Saint-Antoine Est (H3..H5, V2..V3: X = 225..244, Y = 656..672)
        (228.5, 667.5, 0.48), (235.5, 664.0, 0.50), (242.0, 660.5, 0.48),
        # East Berri-Bonsecours Courtyard Grove (H1..H4, V6..V8: X = 300..326, Y = 664..714)
        (314.0, 706.0, 0.65), (322.0, 704.0, 0.68), (318.0, 696.0, 0.62),
        (304.0, 684.0, 0.54), (310.0, 676.0, 0.56), (316.0, 670.0, 0.55),
    ]
    if tree_mesh:
        for idx, (tx, ty, tscale) in enumerate(satellite_trees):
            inst = bpy.data.objects.new(f"Tree_Sat_{idx:03d}", tree_mesh)
            inst.location = (tx, ty, 0.18)
            inst.rotation_euler = (0.0, 0.0, math.radians((idx * 53) % 360))
            inst.scale = (tscale, tscale, tscale)
            col.objects.link(inst)

    # 2. Filter and spawn OSM surveyed trees (excluding Cam 3 view cone on Rue Berri: X=276..296, Y=690..712)
    trees = dossier.get("osm_features", {}).get("trees", [])
    valid_trees = []
    for t in trees:
        tx, ty = t["x"], t["y"]
        if 276.0 <= tx <= 296.0 and 690.0 <= ty <= 712.0:
            continue
        min_b_dist = min((point_to_poly_dist_2d(tx, ty, b) for b in bldg_polys), default=999.0)
        if min_b_dist < 1.80:
            continue
        min_r_dist = 999.0
        for hw in highways:
            pts = hw.get("coords_xy", [])
            for k in range(len(pts) - 1):
                d = pt_seg_dist((tx, ty), pts[k], pts[k + 1])
                if d < min_r_dist:
                    min_r_dist = d
        if min_r_dist < 2.5:
            continue
        valid_trees.append((tx, ty))

    print(f"Spawning {len(satellite_trees)} satellite-matched trees + {len(valid_trees)} OSM trees...")
    if tree_mesh:
        for idx, (tx, ty) in enumerate(valid_trees):
            inst = bpy.data.objects.new(f"Tree_OSM_{idx:03d}", tree_mesh)
            inst.location = (tx, ty, 0.15)
            inst.rotation_euler = (0.0, 0.0, (idx * 47.0) % 360.0 * (math.pi / 180.0))
            scale_fac = 0.48 + ((idx % 6) * 0.04)
            inst.scale = (scale_fac, scale_fac, scale_fac)
            col.objects.link(inst)

    # 3. Spawn Heritage Streetlamps (including exact Cam 4 right-foreground lamp at (223.4, 594.8)!)
    lamp_coords = [
        (223.4, 594.8),  # Exact right-side heritage streetlamp in Cam 4 (Champ_de_Mars_East_Edge V8, H4..H8)!
        (264.0, 660.0), (268.0, 680.0), (272.0, 700.0), (276.0, 720.0),
        (205.0, 635.0), (215.0, 650.0), (225.0, 665.0), (235.0, 680.0),
        (290.0, 685.0), (300.0, 705.0), (310.0, 725.0), (320.0, 745.0),
    ]
    if lamp_mesh:
        for idx, (lx, ly) in enumerate(lamp_coords):
            inst = bpy.data.objects.new(f"StreetLamp_{idx:03d}", lamp_mesh)
            inst.location = (lx, ly, 0.16)
            inst.scale = (1.0, 1.0, 1.0)
            col.objects.link(inst)

    # 4. Spawn Street & Park Benches (modular_street_seating)
    bench_coords = [
        (208.0, 705.0, 0.25), (214.0, 705.0, 0.25), (229.0, 669.0, 0.16),
        (236.0, 665.0, 0.16), (305.0, 692.0, 0.22), (264.0, 595.0, 0.20),
    ]
    if bench_mesh:
        for idx, (bx, by, bz) in enumerate(bench_coords):
            b_inst = bpy.data.objects.new(f"StreetBench_{idx:03d}", bench_mesh)
            b_inst.location = (bx, by, bz)
            b_inst.rotation_euler = (0.0, 0.0, math.radians(28.0))
            col.objects.link(b_inst)


# ---------------------------------------------------------------------------
# 7. RENDERS & LIGHTING
# ---------------------------------------------------------------------------

def setup_world_and_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 40
    scene.cycles.use_denoising = True

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    w_out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 2.15
    links.new(w_out.inputs["Surface"], bg.outputs["Background"])

    if os.path.isfile(HDRI_PATH):
        env_tex = nodes.new("ShaderNodeTexEnvironment")
        env_tex.image = bpy.data.images.load(HDRI_PATH, check_existing=True)
        links.new(bg.inputs["Color"], env_tex.outputs["Color"])

    sun_data = bpy.data.lights.new(name="Sun_Light", type="SUN")
    sun_data.energy = 3.8
    sun_data.angle = math.radians(2.5)
    sun_obj = bpy.data.objects.new(name="Sun_Light", object_data=sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(52.0), math.radians(18.0), math.radians(-42.0))

    # Secondary soft fill sun from WNW/ESE to eliminate deep black canyon shadows on north/east/west street facades
    fill_data = bpy.data.lights.new(name="Fill_Light_Canyon", type="SUN")
    fill_data.energy = 2.6
    fill_data.color = (0.96, 0.97, 1.0)
    fill_data.angle = math.radians(22.0)
    fill_obj = bpy.data.objects.new(name="Fill_Light_Canyon", object_data=fill_data)
    scene.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(58.0), math.radians(-24.0), math.radians(138.0))

    # Direct daylight fill along Rue Saint-Denis & Rue Berri street canyons
    fill2_data = bpy.data.lights.new(name="Fill_Light_West", type="SUN")
    fill2_data.energy = 2.0
    fill2_data.color = (1.0, 0.98, 0.94)
    fill2_data.angle = math.radians(25.0)
    fill2_obj = bpy.data.objects.new(name="Fill_Light_West", object_data=fill2_data)
    scene.collection.objects.link(fill2_obj)
    fill2_obj.rotation_euler = (math.radians(62.0), math.radians(20.0), math.radians(65.0))


def render_cameras(dossier):
    scene = bpy.context.scene
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640

    # Overview aerial snapshot
    ov_data = bpy.data.cameras.new(name=f"Overview_Cam_{BLOCK_ID}")
    ov_data.angle = math.radians(52.0)
    ov_data.clip_start = 1.0
    ov_data.clip_end = 2000.0
    ov_obj = bpy.data.objects.new(name=f"Overview_Cam_{BLOCK_ID}", object_data=ov_data)
    scene.collection.objects.link(ov_obj)

    target = Vector((266.0, 655.0, 15.0))
    ov_obj.location = (380.0, 520.0, 140.0)
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = SNAPSHOT_PATH
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Block Overview Snapshot -> {SNAPSHOT_PATH}")


# ---------------------------------------------------------------------------
# 8. MAIN EXECUTION PIPELINE
# ---------------------------------------------------------------------------

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def main():
    print(f"=== Starting Reconstruction of Block {BLOCK_ID} ===")
    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    # Create target collection: Block_MTL-VM-0032_Owned (Zero _Context_Proxy meshes!)
    master_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(master_col)
    col_owned = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    master_col.children.link(col_owned)

    palette = kit.create_montreal_material_palette()
    if "Mat_MTL_Roof_Membrane" not in palette:
        palette["Mat_MTL_Roof_Membrane"] = kit.get_or_create_pbr_material(
            "Mat_MTL_Roof_Membrane", "#2A2D30", roughness=0.85, bump_strength=0.04
        )
    palette["Mat_MTL_Roof_White_Reflective"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Roof_White_Reflective", "#ECEAE2", roughness=0.52, bump_strength=0.02
    )
    palette["Mat_MTL_Roof_Warm_Tan"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Roof_Warm_Tan", "#9C9589", roughness=0.75, bump_strength=0.04
    )
    palette["Mat_MTL_Roof_Silver_Seam"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Roof_Silver_Seam", "#9CA9B8", roughness=0.38, metallic=0.55, bump_strength=0.03
    )
    palette["Mat_MTL_Awning_Red"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Awning_Red", "#C82822", roughness=0.48
    )
    # Brighten limestone, greystone, and sidewalk albedos + boost window glass reflectivity to match daylight Street View
    for mat_key, bright_mult, rough_override, metal_override in (
        ("Mat_MTL_WarmBuff_Limestone", (1.38, 1.34, 1.24), 0.52, None),
        ("Mat_MTL_PierreGrise_Limestone", (1.32, 1.32, 1.30), 0.56, None),
        ("Mat_MTL_Medieval_Stone", (1.28, 1.28, 1.26), 0.62, None),
        ("Mat_MTL_Granite_Plinth", (1.25, 1.24, 1.20), 0.58, None),
        ("Mat_MTL_Plaza_Light_Granite", (1.42, 1.40, 1.34), 0.62, None),
        ("Mat_MTL_Window_Glass_Dark", (0.22, 0.32, 0.42), 0.04, 0.45),
    ):
        m = palette.get(mat_key)
        if m and m.use_nodes:
            nt = m.node_tree
            bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf:
                if rough_override is not None:
                    for lk in list(nt.links):
                        if lk.to_socket == bsdf.inputs["Roughness"]:
                            nt.links.remove(lk)
                    bsdf.inputs["Roughness"].default_value = rough_override
                if metal_override is not None:
                    bsdf.inputs["Metallic"].default_value = metal_override
                # Insert Hue/Saturation/Value brightness boost on Base Color image texture if linked
                bc_links = [lk for lk in nt.links if lk.to_socket == bsdf.inputs["Base Color"]]
                if bc_links:
                    src_sock = bc_links[0].from_socket
                    nt.links.remove(bc_links[0])
                    hsv = nt.nodes.new("ShaderNodeHueSaturation")
                    hsv.inputs["Saturation"].default_value = 0.82
                    hsv.inputs["Value"].default_value = bright_mult[0]
                    nt.links.new(src_sock, hsv.inputs["Color"])
                    nt.links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])
                else:
                    bsdf.inputs["Base Color"].default_value = (*bright_mult, 1.0)
    if "Mat_MTL_Grass_Lawn_PBR" not in palette:
        palette["Mat_MTL_Grass_Lawn_PBR"] = kit.get_or_create_image_pbr_material(
            "Mat_MTL_Grass_Lawn_PBR", "leafy_grass", fallback_hex="#5A8C38", uv_scale=8.0, bump_strength=0.95
        )
    if "Mat_PH_Gravel_Path" not in palette:
        palette["Mat_PH_Gravel_Path"] = kit.get_or_create_image_pbr_material(
            "Mat_PH_Gravel_Path", "gravel_concrete_02", fallback_hex="#D8C9B0", uv_scale=6.0, bump_strength=0.92
        )
    if "Mat_PH_Herringbone_Pavement" not in palette:
        palette["Mat_PH_Herringbone_Pavement"] = kit.get_or_create_image_pbr_material(
            "Mat_PH_Herringbone_Pavement", "herringbone_pavement", fallback_hex="#B87A62", uv_scale=8.0, bump_strength=0.88
        )

    # Include all primary-owned buildings PLUS the 3 southern satellite-frame buildings (87394920, 396607775, 396607776)
    owned_bldgs = [
        b for b in dossier["osm_features"]["buildings"]
        if b.get("is_primary_owner") or b["id"] in (87394920, 396607775, 396607776)
    ]
    print(f"Loaded {len(owned_bldgs)} buildings inside {BLOCK_ID}_Owned.")

    # Assign diverse facade materials using graph coloring
    facade_color_map, adj = assign_facade_materials(owned_bldgs)
    all_polys = [b["coords_xy"] for b in owned_bldgs]

    handled_ids = set()

    # 1. Landmark 1: CHUM - Pavillon D (128541888)
    b_chum_d = next((b for b in owned_bldgs if b["id"] == 128541888), None)
    if b_chum_d:
        build_chum_pavillon_d(b_chum_d, palette, col_owned)
        handled_ids.add(128541888)
        print("Built CHUM - Pavillon D (128541888)")

    # 2. Landmark 2: CHUM - Pavillon A (970699367)
    b_chum_a = next((b for b in owned_bldgs if b["id"] == 970699367), None)
    if b_chum_a:
        build_chum_pavillon_a(b_chum_a, palette, col_owned)
        handled_ids.add(970699367)
        print("Built CHUM - Pavillon A (970699367)")

    # 3. Landmark 3: Le Clocher de Saint-Sauveur (1300798703)
    b_clocher = next((b for b in owned_bldgs if b["id"] == 1300798703), None)
    if b_clocher:
        build_clocher_saint_sauveur(b_clocher, palette, col_owned)
        handled_ids.add(1300798703)
        print("Built Le Clocher de Saint-Sauveur (1300798703)")

    # 4. Landmark 4: Édifice Marie-Claire-Kirkland-Casgrain (161204910) (Cam 2 & Cam 4)
    b_kirkland = next((b for b in owned_bldgs if b["id"] == 161204910), None)
    if b_kirkland:
        build_edifice_kirkland_casgrain(b_kirkland, palette, col_owned)
        handled_ids.add(161204910)
        print("Built Édifice Marie-Claire-Kirkland-Casgrain (161204910)")

    # 5. Landmark 5: Maison Joseph-Brossard (341117865)
    b_brossard = next((b for b in owned_bldgs if b["id"] == 341117865), None)
    if b_brossard:
        build_maison_joseph_brossard(b_brossard, palette, col_owned)
        handled_ids.add(341117865)
        print("Built Maison Joseph-Brossard (341117865)")

    # 6. Landmark 6: Rue Saint-Denis Corrugated Facade Building (341117215) (Cam 1)
    b_stdenis_corr = next((b for b in owned_bldgs if b["id"] == 341117215), None)
    if b_stdenis_corr:
        build_saint_denis_corrugated_facade_341117215(b_stdenis_corr, palette, col_owned)
        handled_ids.add(341117215)
        print("Built Rue Saint-Denis Corrugated Facade Building (341117215)")

    # 7. Landmark 7: Rue Berri Greystone Rowhouses with Exterior Iron Stairs & Mansards (Cam 3)
    build_berri_greystone_rowhouses(owned_bldgs, palette, col_owned)
    handled_ids.update({341114936, 341114944, 341115039, 341115198})
    print("Built Rue Berri Greystone Rowhouses (341114936..341115198)")

    # 8. All Other Primary-Owned Buildings (Victorian rows and institutional wings)
    for i, b in enumerate(owned_bldgs):
        bid = b["id"]
        if bid in handled_ids:
            continue
        mat_name = facade_color_map[bid]
        mat_wall = palette[mat_name]
        other_polys = [p for j, p in enumerate(all_polys) if j != i]
        build_detailed_victorian_row_building(b, mat_wall, other_polys, palette, col_owned)

    print(f"Finished building all {len(owned_bldgs)} owned buildings.")

    # 9. Complete Street Network, Park Lawns & Watertight Ground Stratum
    build_ground_and_streets(dossier, owned_bldgs, palette, col_owned)
    print("Built Street Network, Park Lawns & Watertight Ground Stratum")

    # 10. Real 3D Props & Trees (Poly Haven jacaranda_tree, street_lamp_01, modular_street_seating)
    spawn_trees_and_props(dossier, owned_bldgs, col_owned)
    print("Spawned real Poly Haven trees, streetlamps, and benches")

    # 11. Setup Lighting & World before packing and saving
    setup_world_and_render()

    # 12. Clean up any lingering hidden/proxy meshes before save/export
    to_remove = [o for o in bpy.data.objects if o.hide_render or "context_proxy" in o.name.lower()]
    for o in to_remove:
        bpy.data.objects.remove(o, do_unlink=True)

    # 13. Pack all 2K PBR textures and save clean .blend file
    print(f"Packing all 2K PBR textures into {BLEND_OUT_PATH}...")
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"Warning during pack_all: {e}")

    tmp_blend = BLEND_OUT_PATH + ".tmp.blend"
    for p in (tmp_blend, BLEND_OUT_PATH, BLEND_OUT_PATH + "@", BLEND_OUT_PATH + "1"):
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

    print(f"Saved clean packed .blend to {BLEND_OUT_PATH}")

    # 14. Export clean binary USD
    bpy.ops.object.select_all(action='DESELECT')
    for o in col_owned.objects:
        o.select_set(True)

    bpy.ops.wm.usd_export(
        filepath=USDC_OUT_PATH,
        selected_objects_only=False,
        evaluation_mode='RENDER',
        export_animation=False,
        export_hair=False,
        export_uvmaps=True,
        export_normals=True,
        export_materials=True,
        use_instancing=True,
        generate_preview_surface=True,
        export_textures_mode='KEEP',
        overwrite_textures=True,
        relative_paths=True,
    )
    print(f"Exported clean USD to {USDC_OUT_PATH}")

    # 15. Render Overview Snapshot
    render_cameras(dossier)

    print(f"=== Successfully completed build for Block {BLOCK_ID} ===")


if __name__ == "__main__":
    main()
