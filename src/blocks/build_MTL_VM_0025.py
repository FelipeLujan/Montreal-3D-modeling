"""
Headless Blender 5.2 Reconstruction Script for Montreal Block MTL-VM-0025 (Iteration 2 - AAA Polished)
Quai de l'Horloge — Old Port Clock Tower (Tour de l'Horloge), Plage de l'Horloge Urban Beach & Bassin de l'Horloge Yacht Marina
1 Rue Quai de l'Horloge, Montréal, QC H2L 0E2

Key Improvements in Iteration 2:
1. Exact Peninsula & Basin Geometry:
   - Carves the true narrow Quai de l'Horloge peninsula flanked by the St. Lawrence River on the East
     and the Bassin de l'Horloge Yacht Marina on the West (eliminating the Iteration 1 slab that buried the marina!).
   - Restores the true East Quay Wall along (791.5, 510.0) -> (845.2, 775.7) -> (854.2, 815.9) -> (861.5, 853.1)
     and Northern Tip (808.95, 907.00).
   - Wave-rippled 2K PBR water surface at Z = -2.20m (water_river_diffuse_2k.jpg, water_river_nor_gl_2k.jpg,
     water_river_rough_2k.jpg) with stepped granite bulkheads, coping stones, timber fenders, and mooring bollards.
2. Bassin de l'Horloge Yacht Marina (Port de Plaisance):
   - Floating timber/white marina pontoons and finger piers at Z = -2.02m.
   - 15 articulated 3D white motor yachts, flybridge cruisers, sailboats with masts, and excursion boat moored in
     Bassin de l'Horloge (including the northern tip yacht visible in satellite_topdown.png and foreground yachts in
     Gare_Dalhousie_Rue_Berri_Approach).
   - Galvanized tubular steel quayside safety railings along the western mainland promenade and pier edges.
3. Plage de l'Horloge Urban Beach, Boardwalk, Shade Sail, Green Ivy Wall & 24 Sky-Blue Parasols:
   - Warm golden-cream sand beach zones at Z = +0.215m (matching camera elevation Z = 1.75m in render_block_for_critique.py).
   - Weathered timber boardwalk decking (Z = +0.255m) and stepped amphitheatre bleachers (Z = +0.26m..+3.20m) with flagpole.
   - 3.0m-high lush green ivy-covered dividing wall (Mur Végétal) with top metal balustrade along the boardwalk.
   - Overhead hyperbolic white/light-blue fabric shade sail canopy above the boardwalk camera viewpoint.
   - 24 sky-blue octagonal beach parasols (umbrellas) and sky-blue Adirondack deck chairs placed at exact satellite & SV coords.
4. Lush Green Park Lawns, Parking Lot Stall Markings & 3D Vehicles:
   - Emerald green park lawn (Mat_PH_Leafy_Grass, Z = +0.195m) on the East half of the pier + 3 terrace lawn strips at Clock Tower base.
   - Crisp white painted parking stall markings, disabled parking symbols, and diagonal zebra stripes on the West half of the pier,
     plus 3D white shuttle van and parked cars.
5. 45m Beaux-Arts Tour de l'Horloge, Quai de l'Horloge Hangar Shed, L'Héritage du Vieux-Port & Blue-Roofed Beach Kiosk:
   - Full 4-sided articulation with deeply recessed (>= 0.48m) 3D window bays, sills, lintels, mullions, and inset roofs.
   - Diverse Poly Haven 2K PBR materials (<= 20% single-material share) with world-space metric UV mapping on every mesh.
   - High-poly Poly Haven 3D trees (jacaranda_tree, searsia_burchellii, tree_small_02), streetlamps (street_lamp_01), and benches.
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

PROJECT_ROOT = r"C:\Users\Felipe\Documents\coding\montreal"
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0025"
DOSSIER_PATH = os.path.join(PROJECT_ROOT, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(PROJECT_ROOT, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_BLOCKS_DIR = os.path.join(PROJECT_ROOT, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(PROJECT_ROOT, "output", "renders")
SNAPSHOT_PATH = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
BLEND_OUT_PATH = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.blend")
USDC_OUT_PATH = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.usdc")
POLYHAVEN_DIR = os.path.join(PROJECT_ROOT, "assets", "polyhaven")
HDRI_PATH = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_BLOCKS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)


# ===========================================================================
# 1. SCENE CLEANUP & COLLECTION HIERARCHY
# ===========================================================================

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)


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


# ===========================================================================
# 2. 2D GEOMETRY & BMESH UTILITIES
# ===========================================================================

def clean_poly_pts(coords_xy):
    pts = [(float(p[0]), float(p[1])) for p in coords_xy]
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-3:
        pts = pts[:-1]
    cleaned = []
    for p in pts:
        if not cleaned or math.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > 0.05:
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
    return list(reversed(pts)) if polygon_signed_area(pts) < 0.0 else list(pts)


def polygon_centroid_2d(pts):
    if not pts:
        return (0.0, 0.0)
    n = len(pts)
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)


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
        if d.length < 1e-4:
            continue
        d.normalize()
        normal = Vector((-d.y, d.x))
        edges.append((p1, p2, normal))
    if len(edges) < 3:
        return pts_ccw
    offset_lines = [(p1 + normal * amount, p2 + normal * amount) for p1, p2, normal in edges]
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


def extrude_prism_in_bm(bm, pts, z0, z1, mat_side=0, mat_top=None, mat_bottom=None):
    pts_ccw = ensure_ccw(pts)
    if len(pts_ccw) < 3 or z1 <= z0:
        return
    v_bot = [bm.verts.new((p[0], p[1], z0)) for p in pts_ccw]
    v_top = [bm.verts.new((p[0], p[1], z1)) for p in pts_ccw]
    n = len(pts_ccw)
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


def add_top_face_in_bm(bm, pts, z, mat_idx=0):
    """Creates a single upward-facing (+Z) polygon with zero bottom/side faces to prevent coplanar Z-fighting."""
    pts_ccw = ensure_ccw(pts)
    if len(pts_ccw) < 3:
        return
    verts = [bm.verts.new((p[0], p[1], z)) for p in pts_ccw]
    try:
        f = bm.faces.new(verts)
        f.material_index = mat_idx
    except ValueError:
        pass


def add_ribbon_top_face_between(bm, p1, p2, z, width=0.20, offset_out=0.0, mat_idx=0):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    seg_len = math.hypot(dx, dy)
    if seg_len < 1e-4:
        return
    nx, ny = dy / seg_len, -dx / seg_len
    hw = width * 0.5
    ox, oy = nx * offset_out, ny * offset_out
    pts = [
        (p1[0] + ox - nx * hw, p1[1] + oy - ny * hw),
        (p2[0] + ox - nx * hw, p2[1] + oy - ny * hw),
        (p2[0] + ox + nx * hw, p2[1] + oy + ny * hw),
        (p1[0] + ox + nx * hw, p1[1] + oy + ny * hw),
    ]
    add_top_face_in_bm(bm, pts, z, mat_idx=mat_idx)


def add_box_between(bm, p1, p2, z0, z1, thickness=0.35, offset_out=0.0, mat_idx=0, cap_top=True, cap_bottom=False):
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
    if cap_bottom:
        quads.append((v_bot[3], v_bot[2], v_bot[1], v_bot[0]))
    for q in quads:
        try:
            f = bm.faces.new(q)
            f.material_index = mat_idx
        except ValueError:
            pass


def add_cylinder_in_bm(bm, center_xy, z0, z1, r_bot, r_top, n_seg=16, mat_idx=0, cap_top=True, cap_bot=False):
    cx, cy = center_xy
    if z1 <= z0 or (r_bot <= 0 and r_top <= 0):
        return
    v_bot = []
    v_top = []
    for i in range(n_seg):
        th = (i / n_seg) * 2.0 * math.pi
        v_bot.append(bm.verts.new((cx + r_bot * math.cos(th), cy + r_bot * math.sin(th), z0)))
        v_top.append(bm.verts.new((cx + r_top * math.cos(th), cy + r_top * math.sin(th), z1)))
    for i in range(n_seg):
        j = (i + 1) % n_seg
        try:
            f = bm.faces.new((v_bot[i], v_bot[j], v_top[j], v_top[i]))
            f.material_index = mat_idx
        except ValueError:
            pass
    if cap_top and r_top > 0.005:
        try:
            f_top = bm.faces.new(v_top)
            f_top.material_index = mat_idx
        except ValueError:
            pass
    if cap_bot and r_bot > 0.005:
        try:
            f_bot = bm.faces.new(list(reversed(v_bot)))
            f_bot.material_index = mat_idx
        except ValueError:
            pass


def assign_world_uvs_to_bm(bm, default_tile_m: float = 4.0, water_mat_idx: int = -1):
    """Assigns world-space triplanar metric UV coordinates to all loops in a BMesh."""
    uv_layer = bm.loops.layers.uv.verify()
    for face in bm.faces:
        face.normal_update()
        n = face.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        tile = 14.0 if (water_mat_idx >= 0 and face.material_index == water_mat_idx) else default_tile_m
        for loop in face.loops:
            co = loop.vert.co
            if az >= ax and az >= ay:
                loop[uv_layer].uv = (co.x / tile, co.y / tile)
            elif ax >= ay and ax >= az:
                loop[uv_layer].uv = (co.y / tile, co.z / tile)
            else:
                loop[uv_layer].uv = (co.x / tile, co.z / tile)


# ===========================================================================
# 3. AUTHENTIC MONTREAL 2K PBR MATERIAL PALETTE
# ===========================================================================

def setup_materials():
    pal = kit.create_montreal_material_palette()

    # 1. Tour de l'Horloge Cream-White Beaux-Arts Limestone/Concrete (2K PBR)
    mat_tower = kit.get_or_create_image_pbr_material(
        "Mat_MTL_Tower_White_Limestone", "castle_brick_02_white", fallback_hex="#EDEAE2", uv_scale=1.2, bump_strength=0.65
    )
    pal["Mat_MTL_Tower_White_Limestone"] = mat_tower

    # 2. Plage de l'Horloge Warm Golden-Cream Beach Sand (2K PBR)
    mat_sand = kit.get_or_create_image_pbr_material(
        "Mat_MTL_Beach_Sand", "sandstone_blocks_05", fallback_hex="#E6D8BC", uv_scale=2.0, bump_strength=0.35
    )
    if mat_sand.use_nodes:
        bsdf_s = next((n for n in mat_sand.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        tex_s = mat_sand.node_tree.nodes.get("TexImage_Diffuse")
        if bsdf_s and tex_s:
            mix_s = mat_sand.node_tree.nodes.new("ShaderNodeMix")
            mix_s.data_type = "RGBA"
            mix_s.blend_type = "MIX"
            mix_s.inputs["Factor"].default_value = 0.72
            mix_s.inputs[7].default_value = (0.86, 0.79, 0.64, 1.0)
            mat_sand.node_tree.links.new(tex_s.outputs["Color"], mix_s.inputs[6])
            mat_sand.node_tree.links.new(mix_s.outputs[2], bsdf_s.inputs["Base Color"])
            bsdf_s.inputs["Roughness"].default_value = 0.88
    pal["Mat_MTL_Beach_Sand"] = mat_sand

    # 3. Weathered Timber Boardwalk & Marina Floating Docks (2K PBR weathered_planks)
    pal["Mat_MTL_Floating_Dock_Wood"] = kit.get_or_create_image_pbr_material(
        "Mat_MTL_Floating_Dock_Wood", "weathered_planks", fallback_hex="#7A6855", uv_scale=1.5, bump_strength=1.10
    )

    # 4. Sky-Blue Beach Parasols, Adirondack Chairs & Beach Kiosk Roof (#3FA2E8)
    pal["Mat_MTL_Parasol_SkyBlue"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Parasol_SkyBlue", "#42A5F0", roughness=0.45, metallic=0.05, bump_strength=0.04
    )

    # 5. Shade Sail Canopy (Bright off-white / pale sky-tinted taut architectural fabric)
    pal["Mat_MTL_Shade_Sail_Fabric"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Shade_Sail_Fabric", "#DCE6EE", roughness=0.52, metallic=0.0, bump_strength=0.03
    )

    # 6. Lush Green Ivy Wall (Mur Végétal) & Grass Lawns (2K PBR leafy_grass)
    pal["Mat_MTL_Grass_Lawn_PBR"] = pal["Mat_PH_Leafy_Grass"]
    pal["Mat_MTL_Ivy_Wall_Green"] = kit.get_or_create_image_pbr_material(
        "Mat_MTL_Ivy_Wall_Green", "leafy_grass", fallback_hex="#2E5420", uv_scale=1.6, bump_strength=1.35
    )

    # 7. Yacht & Sailboat Hull White Gelcoat + Navy/Black Accent + Tinted Cabin Glass
    pal["Mat_MTL_Yacht_White_Gelcoat"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Yacht_White_Gelcoat", "#F4F6F8", roughness=0.14, metallic=0.08, bump_strength=0.01
    )
    pal["Mat_MTL_Yacht_Navy_Stripe"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Yacht_Navy_Stripe", "#162844", roughness=0.25, metallic=0.35, bump_strength=0.02
    )
    pal["Mat_MTL_Yacht_Teak_Deck"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Yacht_Teak_Deck", "#A8794C", roughness=0.55, metallic=0.0, bump_strength=0.06
    )
    pal["Mat_MTL_Bateau_Mouche_Green"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Bateau_Mouche_Green", "#2B4A2B", roughness=0.30, metallic=0.45, bump_strength=0.02
    )

    # 8. Galvanized Steel Guardrails & Parking Paint
    pal["Mat_MTL_Galvanized_Rail"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Galvanized_Rail", "#A8B0B8", roughness=0.35, metallic=0.80, bump_strength=0.02
    )
    pal["Mat_MTL_Parking_Paint_White"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Parking_Paint_White", "#EAECEF", roughness=0.60, metallic=0.0, bump_strength=0.02
    )

    # 9. Clock Tower Gilded Hands & Illuminated Ivory Dial
    pal["Mat_MTL_Gold_Leaf"] = kit.get_or_create_pbr_material(
        "Mat_MTL_Gold_Leaf", "#F2C138", roughness=0.18, metallic=0.95, bump_strength=0.01
    )
    mat_clock = bpy.data.materials.new("Mat_MTL_Clock_Illuminated")
    mat_clock.use_nodes = True
    cnodes = mat_clock.node_tree.nodes
    clinks = mat_clock.node_tree.links
    cnodes.clear()
    cout = cnodes.new("ShaderNodeOutputMaterial")
    cbsdf = cnodes.new("ShaderNodeBsdfPrincipled")
    cbsdf.inputs["Base Color"].default_value = (0.98, 0.96, 0.88, 1.0)
    cbsdf.inputs["Roughness"].default_value = 0.25
    if "Emission Color" in cbsdf.inputs:
        cbsdf.inputs["Emission Color"].default_value = (1.0, 0.96, 0.85, 1.0)
        cbsdf.inputs["Emission Strength"].default_value = 1.20
    clinks.new(cbsdf.outputs["BSDF"], cout.inputs["Surface"])
    pal["Mat_MTL_Clock_Illuminated"] = mat_clock

    return pal


# ===========================================================================
# 4. QUAI DE L'HORLOGE PENINSULA, RIVER, MARINA BASIN, LAWNS & PARKING
# ===========================================================================

def build_ground_peninsula_water_and_lawns(dossier, parent_col, pal):
    """
    Constructs the exact geometry of:
    1. Wave-rippled St. Lawrence River & Bassin de l'Horloge Marina water surface at Z = -2.20m.
    2. Narrow Quai de l'Horloge Pier peninsula (East side) & West Mainland peninsula (leaving Bassin de l'Horloge open!).
    3. Stepped granite quay bulkhead walls (Z = -2.60m..+0.16m) with coping stones (+0.16m..+0.26m),
       timber fenders, mooring bollards, and galvanized steel quayside safety railings.
    4. Lush green park lawn (Z = +0.195m) on the East side of the pier + 3 Clock Tower terrace lawn strips.
    5. Asphalt parking lot on the West side of the pier with white painted parking stalls, disabled bay markings,
       diagonal zebra stripes, and concrete sidewalks/promenades.
    """
    me = bpy.data.meshes.new(f"Quai_Horloge_Peninsula_And_Water_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"Quai_Horloge_Peninsula_And_Water_{BLOCK_ID}", me)
    parent_col.objects.link(obj)

    mats = [
        pal["Mat_PH_Worn_Asphalt"],               # 0: Pier asphalt parking & roadways
        pal["Mat_MTL_Granite_Plinth"],            # 1: Stepped granite quay bulkhead walls
        pal["Mat_PH_Concrete_Sidewalk"],          # 2: Concrete / light granite promenade & sidewalks
        pal["Mat_MTL_StLawrence_Water_PBR"],      # 3: 2K PBR River & Marina Water
        pal["Mat_MTL_Plaza_Charcoal_Granite"],    # 4: Granite coping stones & curbs
        pal["Mat_MTL_Grass_Lawn_PBR"],            # 5: 2K PBR Leafy Grass park lawns
        pal["Mat_PH_Gravel_Path"],                # 6: Crushed limestone park paths
        pal["Mat_MTL_CastIron_Black"],            # 7: Mooring bollards & railings
        pal["Mat_MTL_Galvanized_Rail"],           # 8: Tubular marina safety railings
        pal["Mat_MTL_Parking_Paint_White"],       # 9: White painted parking stall lines
        pal["Mat_MTL_Warm_Timber"],               # 10: Quay timber fenders
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # --- Part A: Wave-Displaced 2K PBR Water Surface at Z = -2.20m ---
    # Subdivided grid across (420..1050, 450..1200) so water ripples catch realistic highlights
    wx0, wx1 = 420.0, 1050.0
    wy0, wy1 = 450.0, 1200.0
    nx_w, ny_w = 48, 56
    dx_w = (wx1 - wx0) / nx_w
    dy_w = (wy1 - wy0) / ny_w

    w_verts = []
    for iy in range(ny_w + 1):
        row = []
        y = wy0 + iy * dy_w
        for ix in range(nx_w + 1):
            x = wx0 + ix * dx_w
            wave_z = -2.20 + 0.025 * math.sin(x * 0.22 + y * 0.15) * math.cos(x * 0.14 - y * 0.19)
            row.append(bm.verts.new((x, y, wave_z)))
        w_verts.append(row)

    for iy in range(ny_w):
        for ix in range(nx_w):
            f = bm.faces.new((
                w_verts[iy][ix],
                w_verts[iy][ix + 1],
                w_verts[iy + 1][ix + 1],
                w_verts[iy + 1][ix]
            ))
            f.material_index = 3
            f.smooth = True

    # Dark riverbed floor at Z = -4.80m
    riverbed_pts = [(wx0, wy0), (wx1, wy0), (wx1, wy1), (wx0, wy1)]
    add_top_face_in_bm(bm, riverbed_pts, -4.80, mat_idx=1)

    # --- Part B: Exact Quai de l'Horloge Peninsula (East Pier) ---
    # Matches satellite_topdown.png and footway 105231251 to the meter!
    clock_pier_poly = [
        (681.342, 604.598),
        (791.500, 510.000),
        (801.800, 561.500),
        (833.000, 714.900),
        (845.200, 775.734),
        (846.600, 782.765),
        (854.200, 815.900),
        (856.000, 815.600),
        (858.818, 830.699),
        (860.277, 841.831),
        (861.556, 850.392),
        (861.525, 853.108),
        (860.698, 855.457),
        (859.247, 854.934),
        (811.968, 905.651),
        (810.618, 906.820),
        (808.949, 906.998),
        (807.614, 906.297),
        (806.663, 904.682),
        (796.013, 858.496),
        (790.170, 856.381),
        (784.903, 854.488),
        (687.396, 620.829),
    ]
    extrude_prism_in_bm(bm, clock_pier_poly, -0.40, 0.160, mat_side=1, mat_top=0)

    # Stepped Granite Quay Bulkhead Walls & Coping around Clock Tower Pier
    n_cp = len(clock_pier_poly)
    for i in range(n_cp):
        p1 = clock_pier_poly[i]
        p2 = clock_pier_poly[(i + 1) % n_cp]
        if i == 0:
            continue
        add_box_between(bm, p1, p2, -2.60, 0.160, thickness=0.90, offset_out=0.0, mat_idx=1)
        add_box_between(bm, p1, p2, 0.160, 0.255, thickness=1.05, offset_out=0.05, mat_idx=4)
        add_box_between(bm, p1, p2, -1.95, -1.65, thickness=0.25, offset_out=0.45, mat_idx=10)
        # Cast-iron mooring bollards every 18m along the river & marina quays
        seg_l = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_l >= 14.0:
            n_bol = max(1, int(seg_l // 18.0))
            for b in range(n_bol):
                t = (b + 0.5) / n_bol
                bx = p1[0] + (p2[0] - p1[0]) * t
                by = p1[1] + (p2[1] - p1[1]) * t
                add_cylinder_in_bm(bm, (bx, by), 0.255, 0.72, 0.16, 0.18, n_seg=12, mat_idx=7)

    # --- Part C: West Mainland & Southern Basin Connector (Leaving Bassin de l'Horloge Open!) ---
    west_mainland_poly = [
        (450.000, 480.000),
        (791.500, 510.000),
        (681.342, 604.598),
        (580.846, 600.825),
        (577.258, 602.906),
        (615.260, 695.012),
        (732.280, 974.814),
        (741.432, 996.955),
        (774.933, 1075.057),
        (795.000, 1220.000),
        (450.000, 1220.000),
    ]
    extrude_prism_in_bm(bm, west_mainland_poly, -0.40, 0.160, mat_side=1, mat_top=0)

    # West Mainland Quay Bulkhead Wall & Galvanized Tubular Marina Safety Railing
    # (Directly in front of Gare_Dalhousie_Rue_Berri_Approach camera at [586.353, 634.432]!)
    west_basin_wall = [
        (681.342, 604.598),
        (580.846, 600.825),
        (577.258, 602.906),
        (615.260, 695.012),
        (732.280, 974.814),
        (741.432, 996.955),
        (774.933, 1075.057),
    ]
    for i in range(len(west_basin_wall) - 1):
        p1 = west_basin_wall[i]
        p2 = west_basin_wall[i + 1]
        add_box_between(bm, p1, p2, -2.60, 0.160, thickness=0.90, offset_out=0.0, mat_idx=1)
        add_box_between(bm, p1, p2, 0.160, 0.250, thickness=1.05, offset_out=0.0, mat_idx=4)
        # Concrete quayside walkway (4.8m wide inland along the West Mainland wall)
        add_box_between(bm, p1, p2, 0.160, 0.205, thickness=4.80, offset_out=-2.40, mat_idx=2)
        # Galvanized steel 3-rail tubular safety railing along the quay edge
        for rz in (0.55, 0.88, 1.20):
            add_box_between(bm, p1, p2, rz - 0.025, rz + 0.025, thickness=0.05, offset_out=-0.25, mat_idx=8)
        seg_l = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        n_posts = max(2, int(seg_l // 2.4))
        for k in range(n_posts + 1):
            t = k / float(n_posts)
            px = p1[0] + (p2[0] - p1[0]) * t
            py = p1[1] + (p2[1] - p1[1]) * t
            add_cylinder_in_bm(bm, (px, py), 0.250, 1.24, 0.035, 0.035, n_seg=8, mat_idx=8)

    # --- Part D: East Quay Concrete/Granite Promenade & Clock Tower Plaza ---
    # Wide light-granite promenade along the East side of the pier (between green lawn and East Quay Wall)
    east_promenade_poly = [
        (782.0, 512.0),
        (791.0, 510.5),
        (844.8, 775.7),
        (853.8, 815.9),
        (855.6, 815.6),
        (858.5, 830.7),
        (860.0, 841.8),
        (861.0, 850.4),
        (858.8, 854.5),
        (824.0, 847.0),
        (790.0, 838.0),
        (794.0, 822.0),
        (840.5, 813.0),
        (832.5, 775.7),
        (802.0, 630.0),
    ]
    extrude_prism_in_bm(bm, east_promenade_poly, 0.160, 0.205, mat_side=4, mat_top=2)

    # --- Part E: Lush Green Park Lawns (Mat_MTL_Grass_Lawn_PBR at Z = +0.195m) ---
    # 1. Main Quai de l'Horloge East Park Lawn (visible in satellite_topdown.png H5..H8, V3..V5
    #    and on the LEFT V1..V3 of Clock_Tower_Quayside_South_Approach!)
    main_park_lawn = [
        (778.0, 660.0),
        (806.0, 654.0),
        (832.5, 775.7),
        (840.5, 813.0),
        (814.0, 818.5),
        (804.0, 775.7),
    ]
    extrude_prism_in_bm(bm, main_park_lawn, 0.160, 0.215, mat_side=4, mat_top=5)
    # Granite perimeter curb around main park lawn
    for i in range(len(main_park_lawn)):
        p1 = main_park_lawn[i]
        p2 = main_park_lawn[(i + 1) % len(main_park_lawn)]
        add_box_between(bm, p1, p2, 0.160, 0.235, thickness=0.28, offset_out=0.0, mat_idx=4)

    # 2. Three Green Terrace Lawn Strips South & West of the Clock Tower Podium (exact satellite_topdown.png match!)
    lawn_strip_1 = [(829.8, 833.4), (846.8, 830.0), (847.3, 832.4), (830.3, 835.8)]
    lawn_strip_2 = [(828.2, 826.8), (843.2, 823.8), (844.4, 829.0), (829.4, 832.0)]
    lawn_strip_3 = [(821.2, 829.4), (825.5, 828.5), (826.2, 831.8), (821.9, 832.7)]
    for l_poly in (lawn_strip_1, lawn_strip_2, lawn_strip_3):
        extrude_prism_in_bm(bm, l_poly, 0.205, 0.250, mat_side=4, mat_top=5)
        for i in range(len(l_poly)):
            add_box_between(bm, l_poly[i], l_poly[(i + 1) % len(l_poly)], 0.205, 0.275, thickness=0.22, offset_out=0.0, mat_idx=4)

    # 3. Two Parking Lot Landscaped Tree Islands (visible in bottom-left of satellite_topdown.png)
    island_1 = [(794.2, 790.2), (797.8, 789.4), (798.5, 793.2), (794.9, 794.0)]
    island_2 = [(789.8, 778.0), (793.4, 777.2), (794.1, 781.0), (790.5, 781.8)]
    for isl in (island_1, island_2):
        extrude_prism_in_bm(bm, isl, 0.160, 0.225, mat_side=4, mat_top=5)

    # --- Part F: Crisp White Painted Parking Stall Lines & Zebra Markings (Z = +0.168m) ---
    # 4 Rows of angled parking stalls visible in satellite_topdown.png (X: 775..812, Y: 775..822)
    stall_rows = [
        # (x_start, y_start, x_end, y_end, stall_dx, stall_dy, n_stalls)
        (775.5, 776.0, 789.5, 822.0, 4.2, -1.2, 18),
        (786.0, 776.0, 798.5, 816.0, 4.2, -1.2, 16),
        (791.5, 776.0, 804.0, 816.0, 4.2, -1.2, 16),
        (802.5, 776.0, 813.0, 818.0, 4.2, -1.2, 17),
    ]
    for xs, ys, xe, ye, sdx, sdy, n_st in stall_rows:
        # Spine line
        add_ribbon_top_face_between(bm, (xs, ys), (xe, ye), 0.168, width=0.14, mat_idx=9)
        for k in range(n_st + 1):
            t = k / float(n_st)
            px = xs + (xe - xs) * t
            py = ys + (ye - ys) * t
            add_ribbon_top_face_between(bm, (px, py), (px + sdx, py + sdy), 0.168, width=0.13, mat_idx=9)

    # Diagonal zebra hatching in front of Clock_Tower_Quayside_South_Approach camera (X: 811..816, Y: 816..825)
    for k in range(8):
        zy = 816.5 + k * 1.05
        add_ribbon_top_face_between(bm, (811.5, zy), (815.5, zy + 0.6), 0.168, width=0.18, mat_idx=9)

    # Checkered crosswalk blocks at (783..788, 820..826) and (809..813, 818..824)
    for cx_b, cy_b in [(785.0, 822.5), (810.5, 820.5)]:
        for ix in range(4):
            for iy in range(5):
                if (ix + iy) % 2 == 0:
                    bx = cx_b + ix * 0.75
                    by = cy_b + iy * 0.75
                    add_top_face_in_bm(bm, [(bx, by), (bx + 0.55, by), (bx + 0.55, by + 0.55), (bx, by + 0.55)], 0.169, mat_idx=9)

    assign_world_uvs_to_bm(bm, default_tile_m=4.0, water_mat_idx=3)
    bm.to_mesh(me)
    bm.free()
    me.update()
    print("Constructed Quai de l'Horloge Peninsula, River & Marina Water, Green Park Lawns & Parking Lot.")


# ===========================================================================
# 5. PLAGE DE L'HORLOGE BEACH, BOARDWALK, BLEACHERS, IVY WALL, SHADE SAIL & PARASOLS
# ===========================================================================

def build_plage_de_l_horloge_and_parasols(parent_col, pal):
    """
    Constructs the complete Plage de l'Horloge urban beach experience:
    1. Warm golden-cream sand beaches (North triangular beach & West boardwalk beach strip) at Z = +0.215m.
    2. Weathered timber boardwalk decking (Z = +0.255m) along the west quay edge, north tip apron, and ivy wall base.
    3. Stepped amphitheatre bleachers / sun deck (Z = +0.26m..+3.20m) with central stairs and angled flagpole.
    4. 3.0m-high lush green ivy-covered dividing wall (Mur Végétal) with top metal railing along (694.3, 617.8) -> (788.9, 842.7)
       and around the Clock Tower terrace base.
    5. Hyperbolic overhead fabric shade sail canopy above Cam_SV_Plage_de_l_Horloge_Boardwalk (774.81, 824.30).
    6. 26 sky-blue octagonal beach parasols (umbrellas) and 36 sky-blue Adirondack beach chairs.
    """
    me = bpy.data.meshes.new(f"Plage_de_l_Horloge_Beach_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"Plage_de_l_Horloge_Beach_{BLOCK_ID}", me)
    parent_col.objects.link(obj)

    mats = [
        pal["Mat_MTL_Beach_Sand"],            # 0: Warm golden beach sand
        pal["Mat_MTL_Floating_Dock_Wood"],    # 1: Weathered timber boardwalk planks
        pal["Mat_PH_Concrete_Pavers"],        # 2: Stepped amphitheatre bleachers
        pal["Mat_MTL_Ivy_Wall_Green"],        # 3: Green ivy wall (Mur Végétal)
        pal["Mat_MTL_Parasol_SkyBlue"],       # 4: Sky-blue beach parasols & Adirondack chairs
        pal["Mat_MTL_Shade_Sail_Fabric"],     # 5: Overhead fabric shade sail canopy
        pal["Mat_MTL_CastIron_Black"],        # 6: Railing & umbrella poles
        pal["Mat_MTL_Galvanized_Rail"],       # 7: Flagpole & shade sail masts
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # --- 1. Northern Triangular Beach Sand (H1..H4, V2..V5 in satellite_topdown.png) ---
    north_sand_poly = [
        (802.0, 868.5),
        (826.5, 863.0),
        (827.5, 852.0),
        (856.5, 846.5),
        (858.5, 853.8),
        (812.0, 904.5),
        (808.5, 892.0),
    ]
    extrude_prism_in_bm(bm, north_sand_poly, 0.160, 0.218, mat_side=0, mat_top=0)

    # --- 2. Western Beach Strip (from Y = 620 up to Y = 855, covering Cam 2 & Cam 3!) ---
    west_sand_poly = [
        (687.6, 621.0),
        (694.3, 618.0),
        (788.9, 842.7),
        (790.2, 855.8),
        (785.0, 854.4),
    ]
    extrude_prism_in_bm(bm, west_sand_poly, 0.160, 0.218, mat_side=0, mat_top=0)

    # --- 3. Weathered Timber Boardwalk Decking (Z = +0.218m .. +0.258m) ---
    # 3a. Boardwalk running along the base of the Green Ivy Wall (visible in Plage_de_l_Horloge_Boardwalk & Road_North)
    boardwalk_ivy_base = [
        (692.2, 619.0),
        (694.3, 618.0),
        (788.9, 842.7),
        (786.8, 843.6),
    ]
    extrude_prism_in_bm(bm, boardwalk_ivy_base, 0.218, 0.258, mat_side=1, mat_top=1)

    # Rustic wooden bollard posts & draped nautical rope along the boardwalk edge
    n_bposts = 46
    for kp in range(n_bposts):
        t0 = kp / float(n_bposts)
        px0 = 692.1 + (786.7 - 692.1) * t0
        py0 = 619.0 + (843.6 - 619.0) * t0
        add_cylinder_in_bm(bm, (px0, py0), 0.22, 1.08, 0.09, 0.08, n_seg=8, mat_idx=1)
        if kp < n_bposts - 1:
            t1 = (kp + 1) / float(n_bposts)
            px1 = 692.1 + (786.7 - 692.1) * t1
            py1 = 619.0 + (843.6 - 619.0) * t1
            pmx, pmy = (px0 + px1) * 0.5, (py0 + py1) * 0.5
            add_box_between(bm, (px0, py0), (pmx, pmy), 0.78, 0.83, thickness=0.04, mat_idx=0)
            add_box_between(bm, (pmx, pmy), (px1, py1), 0.78, 0.83, thickness=0.04, mat_idx=0)

    # 3b. Wide Western Timber Deck & Northern Tip Apron (visible in satellite_topdown.png V2..V3, H1..H5)
    boardwalk_north_west = [
        (780.5, 837.5),
        (792.0, 835.0),
        (802.5, 868.5),
        (809.0, 892.0),
        (820.5, 895.5),
        (811.8, 905.2),
        (807.2, 905.0),
        (796.2, 858.5),
    ]
    extrude_prism_in_bm(bm, boardwalk_north_west, 0.218, 0.262, mat_side=1, mat_top=1)

    # --- 4. Stepped Amphitheatre Bleachers / Sun Deck (X: 792..826, Y: 834..865) ---
    n_bleacher_steps = 10
    for s in range(n_bleacher_steps):
        t = s / float(n_bleacher_steps)
        z_bot = 0.20 + s * 0.26
        z_top = z_bot + 0.26
        bx0 = 792.0 + t * 8.5
        bx1 = 826.5 - t * 1.5
        by0 = 834.0 + t * 2.0
        by1 = 865.0 - t * 15.5
        if bx1 > bx0 + 1.0 and by1 > by0 + 1.0:
            step_poly = [(bx0, by0), (bx1, by0 - 2.5), (bx1, by1 - 2.5), (bx0, by1)]
            extrude_prism_in_bm(bm, step_poly, z_bot, z_top, mat_side=2, mat_top=2)

    # Angled Flagpole Mast on the Bleachers at (817.5, 853.0)
    add_cylinder_in_bm(bm, (817.5, 853.0), 1.50, 14.50, 0.14, 0.06, n_seg=10, mat_idx=7)

    # --- 5. Lush Green Ivy Retaining Wall (Mur Végétal) & Upper Railing ---
    # Runs along (694.3, 618.0) -> (788.9, 842.7) -> (827.5, 842.0)
    ivy_wall_pts = [
        (694.3, 618.0),
        (788.9, 842.7),
        (796.5, 841.5),
        (827.5, 841.0),
    ]
    for i in range(len(ivy_wall_pts) - 1):
        p1 = ivy_wall_pts[i]
        p2 = ivy_wall_pts[i + 1]
        add_box_between(bm, p1, p2, 0.20, 2.95, thickness=0.65, offset_out=0.32, mat_idx=3)
        # Black steel handrail on top of the green ivy wall (Z = 2.95m .. 3.95m)
        add_box_between(bm, p1, p2, 3.88, 3.95, thickness=0.08, offset_out=0.15, mat_idx=6)
        add_box_between(bm, p1, p2, 3.40, 3.45, thickness=0.05, offset_out=0.15, mat_idx=6)
        seg_l = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        n_p = max(2, int(seg_l // 2.2))
        for k in range(n_p + 1):
            tk = k / float(n_p)
            px = p1[0] + (p2[0] - p1[0]) * tk
            py = p1[1] + (p2[1] - p1[1]) * tk
            add_cylinder_in_bm(bm, (px, py), 2.95, 3.95, 0.035, 0.035, n_seg=8, mat_idx=6)

    # Western beach quay edge safety railing along (687.6, 621.0) -> (785.0, 854.4)
    west_beach_edge = [(687.6, 621.0), (785.0, 854.4)]
    for rz in (0.60, 0.92, 1.22):
        add_box_between(bm, west_beach_edge[0], west_beach_edge[1], rz - 0.02, rz + 0.02, thickness=0.05, offset_out=0.15, mat_idx=7)
    for k in range(85):
        tk = k / 84.0
        px = 687.6 + (785.0 - 687.6) * tk
        py = 621.0 + (854.4 - 621.0) * tk
        add_cylinder_in_bm(bm, (px, py), 0.22, 1.25, 0.03, 0.03, n_seg=8, mat_idx=7)

    # --- 6. Overhead Hyperbolic Fabric Shade Sail Canopy above Cam_SV_Plage_de_l_Horloge_Boardwalk ---
    # Camera 2 is at (774.814, 824.298, 1.75) looking ENE (heading 65 deg, pitch +12 deg).
    # Shade sail spans (774.5..779.2, 822.2..828.0, Z = 2.75..4.45m) matching H1..H4, V1..V8!
    sail_p1 = Vector((775.2, 827.8, 4.25))  # Top-left corner
    sail_p2 = Vector((779.0, 824.7, 2.72))  # Front-center low tension point
    sail_p3 = Vector((778.0, 822.1, 4.45))  # Top-right corner
    sail_p4 = Vector((773.8, 824.5, 4.55))  # Back-west high corner
    v_s1 = bm.verts.new(sail_p1)
    v_s2 = bm.verts.new(sail_p2)
    v_s3 = bm.verts.new(sail_p3)
    v_s4 = bm.verts.new(sail_p4)
    try:
        f_sail1 = bm.faces.new((v_s1, v_s2, v_s4))
        f_sail1.material_index = 5
        f_sail2 = bm.faces.new((v_s4, v_s2, v_s3))
        f_sail2.material_index = 5
    except ValueError:
        pass
    # Steel support post for the front corner of the shade sail
    add_cylinder_in_bm(bm, (779.1, 824.6), 0.22, 2.85, 0.045, 0.045, n_seg=8, mat_idx=7)

    # --- 7. 26 Sky-Blue Octagonal Beach Parasols (Umbrellas) & Adirondack Chairs ---
    def add_beach_parasol(ux, uy, z_ground=0.22, radius=1.65):
        # Pole
        add_cylinder_in_bm(bm, (ux, uy), z_ground, z_ground + 2.35, 0.04, 0.04, n_seg=8, mat_idx=6)
        # Octagonal sky-blue umbrella canopy
        add_cylinder_in_bm(bm, (ux, uy), z_ground + 1.95, z_ground + 2.42, radius, 0.12, n_seg=8, mat_idx=4, cap_top=True, cap_bot=True)

    def add_adirondack_chair(cx, cy, z_ground=0.22, yaw_deg=0.0):
        rad = math.radians(yaw_deg)
        ca, sa = math.cos(rad), math.sin(rad)
        def cpt(lx, ly):
            return (cx + lx * ca - ly * sa, cy + lx * sa + ly * ca)
        # Seat & base
        seat_pts = [cpt(-0.38, -0.35), cpt(0.38, -0.35), cpt(0.38, 0.35), cpt(-0.38, 0.35)]
        extrude_prism_in_bm(bm, seat_pts, z_ground, z_ground + 0.42, mat_side=4, mat_top=4)
        # High slanted backrest
        back_pts = [cpt(-0.36, -0.35), cpt(0.36, -0.35), cpt(0.36, -0.18), cpt(-0.36, -0.18)]
        extrude_prism_in_bm(bm, back_pts, z_ground + 0.42, z_ground + 0.98, mat_side=4, mat_top=4)
        # Wide armrests
        for sx in (-0.38, 0.30):
            arm_pts = [cpt(sx, -0.32), cpt(sx + 0.10, -0.32), cpt(sx + 0.10, 0.38), cpt(sx, 0.38)]
            extrude_prism_in_bm(bm, arm_pts, z_ground + 0.42, z_ground + 0.58, mat_side=4, mat_top=4)

    # Exact satellite_topdown.png parasol coordinates on Northern Beach & Deck
    north_parasols = [
        (808.2, 899.5, 0.26),
        (819.5, 891.5, 0.22),
        (820.5, 886.8, 0.22),
        (806.5, 879.0, 0.22),
        (814.8, 881.5, 0.22),
        (824.5, 880.5, 0.22),
        (829.2, 878.5, 0.22),
        (811.2, 869.5, 0.22),
        (816.2, 873.5, 0.22),
        (819.5, 869.0, 0.22),
        (825.2, 871.2, 0.22),
        (833.0, 868.2, 0.22),
        (838.2, 868.0, 0.22),
        (834.0, 859.8, 0.22),
        (845.2, 854.8, 0.22),
        (849.5, 856.0, 0.22),
        (853.5, 850.0, 0.22),
    ]
    for ux, uy, uz in north_parasols:
        add_beach_parasol(ux, uy, uz, radius=1.75)
        add_adirondack_chair(ux - 1.1, uy + 0.6, uz, yaw_deg=45.0)
        add_adirondack_chair(ux + 1.1, uy - 0.6, uz, yaw_deg=45.0)

    # Row of blue lounge chairs along NE river edge (visible in satellite_topdown.png)
    for k in range(16):
        tk = k / 15.0
        lx = 814.0 + (855.0 - 814.0) * tk
        ly = 900.5 + (853.5 - 900.5) * tk
        add_adirondack_chair(lx, ly, 0.22, yaw_deg=45.0)

    # Western Beach Strip Parasols & Chairs (matching satellite_topdown.png V1, Plage_de_l_Horloge_Boardwalk & Road_North!)
    west_parasols = [
        (785.5, 842.0),
        (778.8, 830.2),  # Midground umbrella in Plage_de_l_Horloge_Boardwalk (V2..V4, H4..H6)
        (774.2, 820.5),
        (766.0, 801.0),
        (754.0, 773.0),
        (742.0, 745.0),
        (731.0, 718.0),
        (724.5, 703.0),
        (719.5, 690.5),
        (715.8, 679.8),  # Foreground umbrella in Quai_de_l_Horloge_Road_North (V4..V6, H4..H6)
        (705.0, 656.0),
        (696.0, 635.0),
    ]
    for ux, uy in west_parasols:
        add_beach_parasol(ux, uy, 0.22, radius=1.65)
        add_adirondack_chair(ux - 0.7, uy - 0.9, 0.22, yaw_deg=-65.0)
        add_adirondack_chair(ux + 0.5, uy + 0.9, 0.22, yaw_deg=-115.0)

    # Dedicated Foreground Blue Adirondack Chair in Plage_de_l_Horloge_Boardwalk (V5..V6, H6..H8)
    add_adirondack_chair(777.2, 825.0, 0.22, yaw_deg=155.0)

    assign_world_uvs_to_bm(bm, default_tile_m=3.5)
    bm.to_mesh(me)
    bm.free()
    me.update()
    print("Constructed Plage de l'Horloge Beach, Boardwalk, Bleachers, Ivy Wall, Shade Sail & 29 Sky-Blue Parasols.")


# ===========================================================================
# 6. BASSIN DE L'HORLOGE YACHT MARINA (PONTOONS & 15 3D YACHTS / BOATS)
# ===========================================================================

def build_yacht_marina_and_vessels(parent_col, pal):
    """
    Constructs the Port de Plaisance (Bassin de l'Horloge Yacht Marina) & Parked Pier Vehicles:
    1. Floating marina pontoons & finger piers at Z = -2.02m across Bassin de l'Horloge.
    2. 15 articulated 3D luxury white motor yachts, cabin cruisers, sailboats with masts, and excursion vessel
       moored in Bassin de l'Horloge (matching Gare_Dalhousie_Rue_Berri_Approach, Quai_de_l_Horloge_Road_North,
       and the top-left corner of satellite_topdown.png).
    3. 3D White Shuttle Van & Parked Cars in the Quai de l'Horloge parking lot (matching satellite_topdown.png
       and Clock_Tower_Quayside_South_Approach).
    """
    me = bpy.data.meshes.new(f"Marina_Yachts_And_Vehicles_{BLOCK_ID}_Mesh")
    obj = bpy.data.objects.new(f"Marina_Yachts_And_Vehicles_{BLOCK_ID}", me)
    parent_col.objects.link(obj)

    mats = [
        pal["Mat_MTL_Yacht_White_Gelcoat"],    # 0: Yacht hull & cabin white gelcoat
        pal["Mat_MTL_Yacht_Navy_Stripe"],      # 1: Hull waterline stripe & bimini canvas
        pal["Mat_MTL_Window_Glass_Dark"],      # 2: Tinted wrap-around cabin windshields
        pal["Mat_MTL_Yacht_Teak_Deck"],        # 3: Teak swim platform & foredeck
        pal["Mat_MTL_Floating_Dock_Wood"],     # 4: Floating marina dock pontoons
        pal["Mat_MTL_Galvanized_Rail"],        # 5: Masts, cleats, radar arches
        pal["Mat_MTL_Bateau_Mouche_Green"],    # 6: Excursion boat green frame
        pal["Mat_MTL_CastIron_Black"],         # 7: Tires & dark trim
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    def add_motor_yacht(cx, cy, yaw_deg, length=13.5, beam=3.8, has_mast=False):
        rad = math.radians(yaw_deg)
        ca, sa = math.cos(rad), math.sin(rad)
        def ypt(lx, ly):
            return (cx + lx * ca - ly * sa, cy + lx * sa + ly * ca)

        hl = length * 0.5
        hb = beam * 0.5
        # Hull footprint with pointed bow (+X local) and transom stern (-X local)
        hull_pts = [
            ypt(-hl, -hb * 0.88),
            ypt(hl * 0.35, -hb),
            ypt(hl * 0.78, -hb * 0.55),
            ypt(hl, 0.0),
            ypt(hl * 0.78, hb * 0.55),
            ypt(hl * 0.35, hb),
            ypt(-hl, hb * 0.88),
        ]
        # Waterline dark navy stripe (Z = -2.25m .. -1.95m)
        extrude_prism_in_bm(bm, hull_pts, -2.25, -1.95, mat_side=1, mat_top=None)
        # Main white freeboard hull (Z = -1.95m .. -1.10m)
        extrude_prism_in_bm(bm, hull_pts, -1.95, -1.10, mat_side=0, mat_top=3)
        # Teak swim platform at stern
        swim_pts = [
            ypt(-hl - 0.85, -hb * 0.80),
            ypt(-hl, -hb * 0.80),
            ypt(-hl, hb * 0.80),
            ypt(-hl - 0.85, hb * 0.80),
        ]
        extrude_prism_in_bm(bm, swim_pts, -2.05, -1.80, mat_side=0, mat_top=3)

        # Sleek Cabin Superstructure (Z = -1.10m .. -0.15m)
        cab_pts = [
            ypt(-hl * 0.65, -hb * 0.72),
            ypt(hl * 0.30, -hb * 0.72),
            ypt(hl * 0.48, -hb * 0.42),
            ypt(hl * 0.48, hb * 0.42),
            ypt(hl * 0.30, hb * 0.72),
            ypt(-hl * 0.65, hb * 0.72),
        ]
        extrude_prism_in_bm(bm, cab_pts, -1.10, -0.15, mat_side=0, mat_top=0)

        # Dark tinted wrap-around cabin windshield & side windows
        win_pts = inset_polygon_2d(cab_pts, -0.04)
        extrude_prism_in_bm(bm, win_pts, -0.82, -0.32, mat_side=2, mat_top=None)

        # Upper Flybridge / Radar Arch (Z = -0.15m .. +0.65m)
        arch_pts = [
            ypt(-hl * 0.45, -hb * 0.62),
            ypt(-hl * 0.10, -hb * 0.62),
            ypt(-hl * 0.10, hb * 0.62),
            ypt(-hl * 0.45, hb * 0.62),
        ]
        extrude_prism_in_bm(bm, arch_pts, -0.15, 0.55, mat_side=0, mat_top=1)

        if has_mast:
            mast_xy = ypt(hl * 0.15, 0.0)
            add_cylinder_in_bm(bm, mast_xy, -0.15, 11.5, 0.08, 0.05, n_seg=8, mat_idx=5)

    # --- 1. Floating Marina Pontoons in Bassin de l'Horloge (Z = -2.15m .. -1.92m) ---
    # Spine docks & finger piers visible in Gare_Dalhousie_Rue_Berri_Approach & Quai_de_l_Horloge_Road_North
    marina_spines = [
        ((602.0, 625.0), (665.0, 775.0), 2.4),
        ((645.0, 622.0), (725.0, 815.0), 2.4),
        ((672.0, 625.0), (768.0, 855.0), 2.2),
        ((765.0, 885.0), (784.0, 912.0), 2.5),  # Top-left corner dock in satellite_topdown.png
    ]
    for p1, p2, w in marina_spines:
        add_box_between(bm, p1, p2, -2.15, -1.92, thickness=w, offset_out=0.0, mat_idx=4)
        add_box_between(bm, p1, p2, -1.92, -1.84, thickness=w + 0.16, offset_out=0.0, mat_idx=0)

    # Finger piers branching off spines
    for k in range(8):
        tk = k / 7.0
        sx = 605.0 + (660.0 - 605.0) * tk
        sy = 632.0 + (765.0 - 632.0) * tk
        add_box_between(bm, (sx, sy), (sx + 12.0, sy - 4.5), -2.15, -1.92, thickness=1.4, offset_out=0.0, mat_idx=4)
        sx2 = 674.0 + (758.0 - 674.0) * tk
        sy2 = 635.0 + (835.0 - 635.0) * tk
        add_box_between(bm, (sx2, sy2), (sx2 - 11.0, sy2 + 4.0), -2.15, -1.92, thickness=1.4, offset_out=0.0, mat_idx=4)

    # --- 2. Moored Yachts in Bassin de l'Horloge ---
    # Yacht 1: Top-left corner of satellite_topdown.png (X = 775.2, Y = 903.5)
    add_motor_yacht(775.2, 903.5, yaw_deg=68.0, length=15.5, beam=4.4, has_mast=False)

    # Yacht 2: Prominent foreground luxury motor yacht in Gare_Dalhousie_Rue_Berri_Approach (V2..V5, H5..H6)
    add_motor_yacht(610.5, 645.2, yaw_deg=155.0, length=15.0, beam=4.2, has_mast=False)

    # Vessel 3: Glazed Green/Black Excursion Boat (Bateau-Mouche / Navark) at (626.0, 653.0) in Gare_Dalhousie view
    bm_cx, bm_cy = 626.0, 653.0
    bm_rad = math.radians(155.0)
    ca_b, sa_b = math.cos(bm_rad), math.sin(bm_rad)
    def bpt(lx, ly):
        return (bm_cx + lx * ca_b - ly * sa_b, bm_cy + lx * sa_b + ly * ca_b)
    bm_hull = [bpt(-11.0, -2.8), bpt(9.0, -2.8), bpt(12.0, 0.0), bpt(9.0, 2.8), bpt(-11.0, 2.8)]
    extrude_prism_in_bm(bm, bm_hull, -2.25, -1.05, mat_side=7, mat_top=3)
    bm_cab = [bpt(-8.5, -2.5), bpt(7.5, -2.5), bpt(7.5, 2.5), bpt(-8.5, 2.5)]
    extrude_prism_in_bm(bm, bm_cab, -1.05, 0.45, mat_side=2, mat_top=6)
    extrude_prism_in_bm(bm, inset_polygon_2d(bm_cab, -0.10), 0.35, 0.65, mat_side=6, mat_top=6)

    # Fleet of 13 additional yachts & sailboats across Bassin de l'Horloge (visible in Cam 3 & Cam 4)
    fleet_specs = [
        (598.0, 658.0, -25.0, 11.5, 3.4, True),
        (604.0, 672.0, 155.0, 12.5, 3.6, False),
        (612.0, 688.0, -25.0, 13.0, 3.8, True),
        (620.0, 705.0, 155.0, 12.0, 3.5, False),
        (630.0, 725.0, -25.0, 14.0, 4.0, True),
        (676.0, 642.0, 65.0, 12.0, 3.5, False),
        (684.0, 662.0, -115.0, 13.5, 3.8, True),
        (693.0, 684.0, 65.0, 12.5, 3.6, False),   # Visible on left of Quai_de_l_Horloge_Road_North!
        (701.0, 704.0, -115.0, 14.0, 4.0, True),  # Visible on left of Quai_de_l_Horloge_Road_North!
        (710.0, 726.0, 65.0, 13.0, 3.8, False),
        (722.0, 752.0, -115.0, 14.5, 4.1, True),
        (735.0, 782.0, 65.0, 12.5, 3.7, False),
        (748.0, 812.0, -115.0, 13.5, 3.9, True),
    ]
    for yx, yy, yyaw, ylen, ybeam, ymast in fleet_specs:
        add_motor_yacht(yx, yy, yyaw, ylen, ybeam, ymast)

    # --- 3. 3D White Shuttle Van & Parked Cars on Quai de l'Horloge Pier ---
    def add_vehicle(vx, vy, yaw_deg, length=4.6, width=1.9, height=1.55, is_van=False):
        rad = math.radians(yaw_deg)
        ca, sa = math.cos(rad), math.sin(rad)
        def vpt(lx, ly):
            return (vx + lx * ca - ly * sa, vy + lx * sa + ly * ca)
        hl, hw = length * 0.5, width * 0.5
        base_pts = [vpt(-hl, -hw), vpt(hl, -hw), vpt(hl, hw), vpt(-hl, hw)]
        extrude_prism_in_bm(bm, base_pts, 0.18, 0.45, mat_side=7, mat_top=0)
        extrude_prism_in_bm(bm, base_pts, 0.45, 0.45 + height * 0.48, mat_side=0 if is_van else 1, mat_top=0 if is_van else 1)
        cab_pts = [vpt(-hl * 0.75, -hw * 0.88), vpt(hl * (0.65 if is_van else 0.35), -hw * 0.88),
                   vpt(hl * (0.65 if is_van else 0.35), hw * 0.88), vpt(-hl * 0.75, hw * 0.88)]
        extrude_prism_in_bm(bm, cab_pts, 0.45 + height * 0.48, 0.45 + height, mat_side=2, mat_top=0 if is_van else 1)

    # White shuttle van in satellite_topdown.png at (787.5, 802.0)
    add_vehicle(787.5, 802.0, yaw_deg=-16.0, length=6.8, width=2.25, height=2.45, is_van=True)
    # White van on right edge of Clock_Tower_Quayside_South_Approach at (805.2, 821.0)
    add_vehicle(805.2, 821.0, yaw_deg=-18.0, length=5.8, width=2.15, height=2.35, is_van=True)
    # Dark sedan in satellite_topdown.png at (812.0, 806.8)
    add_vehicle(812.0, 806.8, yaw_deg=-16.0, length=4.6, width=1.88, height=1.48, is_van=False)
    # Additional parked cars along the parking rows (visible in Clock_Tower_Quayside_South_Approach)
    for px, py in [(801.5, 795.0), (798.5, 782.0), (792.0, 765.0), (788.0, 748.0)]:
        add_vehicle(px, py, yaw_deg=-16.0, length=4.5, width=1.85, height=1.48, is_van=False)

    assign_world_uvs_to_bm(bm, default_tile_m=3.5)
    bm.to_mesh(me)
    bm.free()
    me.update()
    print("Constructed Bassin de l'Horloge Marina Pontoons, 15 3D Yachts/Vessels & Parked Vehicles.")


# ===========================================================================
# 7. LANDMARK BUILDINGS: TOUR DE L'HORLOGE, PAVILIONS, HANGAR SHED & HERITAGE
# ===========================================================================

def add_recessed_window_bay(bm, p1, p2, z_bottom, z_top, recess=0.50, frame_mat=0, glass_mat=1, sill_mat=2, lintel_mat=2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 0.6 or z_top <= z_bottom:
        return
    nx, ny = dy / L, -dx / L

    add_box_between(bm, p1, p2, z_bottom - 0.12, z_bottom, thickness=0.35, offset_out=0.06, mat_idx=sill_mat)
    add_box_between(bm, p1, p2, z_top, z_top + 0.18, thickness=0.35, offset_out=0.05, mat_idx=lintel_mat)

    w_p1 = (p1[0] - nx * recess, p1[1] - ny * recess)
    w_p2 = (p2[0] - nx * recess, p2[1] - ny * recess)

    v_front_l = (bm.verts.new((p1[0], p1[1], z_bottom)), bm.verts.new((p1[0], p1[1], z_top)))
    v_back_l = (bm.verts.new((w_p1[0], w_p1[1], z_bottom)), bm.verts.new((w_p1[0], w_p1[1], z_top)))
    v_front_r = (bm.verts.new((p2[0], p2[1], z_bottom)), bm.verts.new((p2[0], p2[1], z_top)))
    v_back_r = (bm.verts.new((w_p2[0], w_p2[1], z_bottom)), bm.verts.new((w_p2[0], w_p2[1], z_top)))

    for quad, midx in [
        ((v_front_l[0], v_back_l[0], v_back_l[1], v_front_l[1]), frame_mat),
        ((v_back_r[0], v_front_r[0], v_front_r[1], v_back_r[1]), frame_mat),
        ((v_front_l[1], v_back_l[1], v_back_r[1], v_front_r[1]), frame_mat),
        ((v_back_l[0], v_back_r[0], v_back_r[1], v_back_l[1]), glass_mat),
    ]:
        try:
            f = bm.faces.new(quad)
            f.material_index = midx
        except ValueError:
            pass


def add_circular_clock_face(bm, center_xy, z_center, radius=1.85, heading_rad=0.0, mat_dial=3, mat_gold=4):
    cx, cy = center_xy
    nx = math.cos(heading_rad)
    ny = math.sin(heading_rad)
    tx, ty = -ny, nx
    n_seg = 24
    v_dial = []
    for i in range(n_seg):
        th = (i / n_seg) * 2.0 * math.pi
        px = cx + tx * math.cos(th) * radius + nx * 0.08
        py = cy + ty * math.cos(th) * radius + ny * 0.08
        pz = z_center + math.sin(th) * radius
        v_dial.append(bm.verts.new((px, py, pz)))
    try:
        f_dial = bm.faces.new(v_dial)
        f_dial.material_index = mat_dial
    except ValueError:
        pass

    hx, hy = cx + nx * 0.12, cy + ny * 0.12
    for hand_len, ang_deg in [(1.45, 0.0), (1.05, 115.0)]:
        ang = math.radians(ang_deg)
        h_top = (hx + tx * math.sin(ang) * hand_len, hy + ty * math.sin(ang) * hand_len, z_center + math.cos(ang) * hand_len)
        h_bl = (hx - tx * 0.05, hy - ty * 0.05, z_center)
        h_br = (hx + tx * 0.05, hy + ty * 0.05, z_center)
        try:
            f_h = bm.faces.new([bm.verts.new(h_bl), bm.verts.new(h_br), bm.verts.new(h_top)])
            f_h.material_index = mat_gold
        except ValueError:
            pass


def build_tour_de_l_horloge(parent_col, pal):
    """
    Constructs the 45m Beaux-Arts Sailors' Memorial Clock Tower (OSM 161206731):
    - Exact footprint & western memorial podium/ramp matching satellite_topdown.png.
    - Stepped corner buttresses, arched base portal, vertical narrow window slits,
      4 illuminated clock dials, cornice arcades, and octagonal lantern cupola.
    """
    me = bpy.data.meshes.new("Tour_de_l_Horloge_Mesh")
    obj = bpy.data.objects.new("Tour_de_l_Horloge_45m", me)
    parent_col.objects.link(obj)

    mats = [
        pal["Mat_MTL_Tower_White_Limestone"],     # 0: Cream-white Beaux-Arts stone
        pal["Mat_MTL_PierreGrise_Limestone"],      # 1: Podium & steps grey limestone
        pal["Mat_MTL_Window_Glass_Dark"],          # 2: Recessed window glass
        pal["Mat_MTL_Clock_Illuminated"],          # 3: Illuminated clock dial
        pal["Mat_MTL_Gold_Leaf"],                  # 4: Gilded clock hands & finial
        pal["Mat_MTL_Dark_Bronze_CurtainWall"],    # 5: Bronze trim
        pal["Mat_MTL_Verdigris_Copper"],           # 6: Cupola roof
        pal["Mat_MTL_CastIron_Black"],             # 7: Portal ironwork
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    cx, cy = 850.4, 836.3
    rot_rad = math.radians(-11.7)
    cos_r, sin_r = math.cos(rot_rad), math.sin(rot_rad)

    def rot_pt(lx, ly):
        return (cx + lx * cos_r - ly * sin_r, cy + lx * sin_r + ly * cos_r)

    hx, hy = 4.1, 4.0

    # Western Memorial Wall & Podium (matches OSM 161206731 coords_xy & satellite shadow!)
    podium_pts = [
        rot_pt(-hx - 18.8, -1.8),
        rot_pt(-hx - 0.05, -1.8),
        rot_pt(-hx - 0.05, 1.8),
        rot_pt(-hx - 18.8, 1.8),
    ]
    extrude_prism_in_bm(bm, podium_pts, 0.20, 4.60, mat_side=0, mat_top=1)

    # Western Podium End Pier / Buttress Turret at (829.5, 840.8) visible in satellite_topdown.png & Boardwalk SV!
    west_pier_pts = [
        rot_pt(-hx - 21.5, -2.5),
        rot_pt(-hx - 18.5, -2.5),
        rot_pt(-hx - 18.5, 2.5),
        rot_pt(-hx - 21.5, 2.5),
    ]
    extrude_prism_in_bm(bm, west_pier_pts, 0.20, 7.80, mat_side=0, mat_top=0)

    # Tower Rusticated Base (Z = 0.20m .. 8.50m)
    tower_base_pts = [rot_pt(-hx, -hy), rot_pt(hx, -hy), rot_pt(hx, hy), rot_pt(-hx, hy)]
    extrude_prism_in_bm(bm, tower_base_pts, 0.20, 8.50, mat_side=0, mat_top=None)

    add_recessed_window_bay(bm, rot_pt(-hx, 1.2), rot_pt(-hx, -1.2), 4.6, 7.8, recess=0.65, frame_mat=0, glass_mat=7, sill_mat=1, lintel_mat=0)

    cornice_base = [rot_pt(-hx - 0.35, -hy - 0.35), rot_pt(hx + 0.35, -hy - 0.35), rot_pt(hx + 0.35, hy + 0.35), rot_pt(-hx - 0.35, hy + 0.35)]
    extrude_prism_in_bm(bm, cornice_base, 8.30, 8.80, mat_side=0, mat_top=0)

    # Fluted Shaft (Z = 8.80m .. 33.0m)
    sx, sy = hx - 0.25, hy - 0.25
    shaft_pts = [rot_pt(-sx, -sy), rot_pt(sx, -sy), rot_pt(sx, sy), rot_pt(-sx, sy)]
    extrude_prism_in_bm(bm, shaft_pts, 8.80, 33.0, mat_side=0, mat_top=None)

    # Stepped Corner Buttresses
    for lx, ly, dxs, dys in [(-sx, -sy, -1, -1), (sx, -sy, 1, -1), (sx, sy, 1, 1), (-sx, sy, -1, 1)]:
        p_box = [rot_pt(lx, ly), rot_pt(lx + dxs * 0.28, ly), rot_pt(lx + dxs * 0.28, ly + dys * 1.15), rot_pt(lx, ly + dys * 1.15)]
        extrude_prism_in_bm(bm, p_box, 8.80, 32.8, mat_side=0, mat_top=0)

    for z_bot, z_tp in [(12.0, 15.2), (18.5, 21.7), (25.0, 28.2)]:
        add_recessed_window_bay(bm, rot_pt(-0.9, -sy), rot_pt(0.9, -sy), z_bot, z_tp, recess=0.52, frame_mat=0, glass_mat=2, sill_mat=1, lintel_mat=0)
        add_recessed_window_bay(bm, rot_pt(0.9, sy), rot_pt(-0.9, sy), z_bot, z_tp, recess=0.52, frame_mat=0, glass_mat=2, sill_mat=1, lintel_mat=0)
        add_recessed_window_bay(bm, rot_pt(sx, -0.9), rot_pt(sx, 0.9), z_bot, z_tp, recess=0.52, frame_mat=0, glass_mat=2, sill_mat=1, lintel_mat=0)
        add_recessed_window_bay(bm, rot_pt(-sx, 0.9), rot_pt(-sx, -0.9), z_bot, z_tp, recess=0.52, frame_mat=0, glass_mat=2, sill_mat=1, lintel_mat=0)

    cornice_top = [rot_pt(-sx - 0.65, -sy - 0.65), rot_pt(sx + 0.65, -sy - 0.65), rot_pt(sx + 0.65, sy + 0.65), rot_pt(-sx - 0.65, sy + 0.65)]
    extrude_prism_in_bm(bm, cornice_top, 32.8, 33.8, mat_side=0, mat_top=0)

    # Clock Chamber (Z = 33.8m .. 39.2m)
    cx_b, cy_b = sx - 0.15, sy - 0.15
    chamber_pts = [rot_pt(-cx_b, -cy_b), rot_pt(cx_b, -cy_b), rot_pt(cx_b, cy_b), rot_pt(-cx_b, cy_b)]
    extrude_prism_in_bm(bm, chamber_pts, 33.8, 39.2, mat_side=0, mat_top=None)

    clock_z, clock_r = 36.5, 1.85
    add_circular_clock_face(bm, rot_pt(0.0, -cy_b), clock_z, radius=clock_r, heading_rad=rot_rad - math.pi * 0.5, mat_dial=3, mat_gold=4)
    add_circular_clock_face(bm, rot_pt(0.0, cy_b), clock_z, radius=clock_r, heading_rad=rot_rad + math.pi * 0.5, mat_dial=3, mat_gold=4)
    add_circular_clock_face(bm, rot_pt(cx_b, 0.0), clock_z, radius=clock_r, heading_rad=rot_rad, mat_dial=3, mat_gold=4)
    add_circular_clock_face(bm, rot_pt(-cx_b, 0.0), clock_z, radius=clock_r, heading_rad=rot_rad + math.pi, mat_dial=3, mat_gold=4)

    c_clock = [rot_pt(-cx_b - 0.45, -cy_b - 0.45), rot_pt(cx_b + 0.45, -cy_b - 0.45), rot_pt(cx_b + 0.45, cy_b + 0.45), rot_pt(-cx_b - 0.45, cy_b + 0.45)]
    extrude_prism_in_bm(bm, c_clock, 39.0, 39.5, mat_side=0, mat_top=0)

    # Observation Loggia & Octagonal Cupola (Z = 39.5m .. 45.4m)
    ox_b, oy_b = cx_b - 0.75, cy_b - 0.75
    obs_pts = [rot_pt(-ox_b, -oy_b), rot_pt(ox_b, -oy_b), rot_pt(ox_b, oy_b), rot_pt(-ox_b, oy_b)]
    extrude_prism_in_bm(bm, obs_pts, 39.5, 42.3, mat_side=0, mat_top=0)
    add_cylinder_in_bm(bm, (cx, cy), 42.3, 44.0, 1.95, 1.95, n_seg=8, mat_idx=0)
    add_cylinder_in_bm(bm, (cx, cy), 44.0, 44.9, 2.05, 0.45, n_seg=8, mat_idx=6)
    add_cylinder_in_bm(bm, (cx, cy), 44.9, 45.5, 0.25, 0.04, n_seg=8, mat_idx=4)

    assign_world_uvs_to_bm(bm, default_tile_m=3.0)
    bm.to_mesh(me)
    bm.free()
    me.update()
    print("Constructed 45m Beaux-Arts Tour de l'Horloge & Western Podium.")


def build_other_owned_buildings(dossier, parent_col, pal):
    """
    Constructs the remaining 4 primary-owned buildings in MTL-VM-0025 with distinct Poly Haven 2K PBR materials:
    1. 794574905: Plage de l'Horloge T-Shaped Beach Kiosk / Bar Pavilion (Sky-Blue Roof matching satellite_topdown.png!)
    2. 794574909: Plage de l'Horloge White/Timber Container Pavilion
    3. 46866828: Hangar du Quai de l'Horloge (61m x 133m industrial exhibition shed with dark steel & glass bays)
    4. 46866834: L'Héritage du Vieux-Port (1000 Rue de la Commune Est, 9-story heritage brick & limestone residence)
    """
    bldgs = {b["id"]: b for b in dossier["osm_features"]["buildings"]}

    # 1. Pavilions 794574905 (Sky-Blue Roof Kiosk) & 794574909 (Container Pavilion)
    for bid, wall_m, roof_m, h in [
        (794574905, "Mat_MTL_Warm_Timber", "Mat_MTL_Parasol_SkyBlue", 4.2),
        (794574909, "Mat_MTL_Precast_Concrete", "Mat_MTL_Weathered_Metal", 4.5),
    ]:
        b = bldgs.get(bid)
        if not b:
            continue
        coords = clean_poly_pts(b["coords_xy"])
        me = bpy.data.meshes.new(f"Pavilion_{bid}_Mesh")
        obj = bpy.data.objects.new(f"Bldg_Pavilion_{bid}", me)
        parent_col.objects.link(obj)
        for mn in (wall_m, roof_m, "Mat_MTL_Window_Glass_Dark", "Mat_MTL_CastIron_Black"):
            obj.data.materials.append(pal[mn])
        bm = bmesh.new()
        extrude_prism_in_bm(bm, coords, 0.20, h, mat_side=0, mat_top=None)
        canopy_pts = inset_polygon_2d(coords, -0.35)
        extrude_prism_in_bm(bm, canopy_pts, h, h + 0.30, mat_side=1, mat_top=1)
        pts_ccw = ensure_ccw(coords)
        for i in range(len(pts_ccw)):
            p1, p2 = pts_ccw[i], pts_ccw[(i + 1) % len(pts_ccw)]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 2.8:
                add_recessed_window_bay(bm, p1, p2, 1.0, 3.3, recess=0.48, frame_mat=3, glass_mat=2, sill_mat=0, lintel_mat=1)
        assign_world_uvs_to_bm(bm, default_tile_m=3.0)
        bm.to_mesh(me)
        bm.free()
        me.update()

    # 2. Hangar du Quai de l'Horloge Exhibition Shed (OSM 46866828)
    b_shed = bldgs.get(46866828)
    if b_shed:
        coords = clean_poly_pts(b_shed["coords_xy"])
        me = bpy.data.meshes.new("Hangar_Quai_Horloge_46866828_Mesh")
        obj = bpy.data.objects.new("Bldg_Hangar_Quai_Horloge_46866828", me)
        parent_col.objects.link(obj)
        for mn in ("Mat_MTL_Weathered_Metal", "Mat_MTL_Granite_Plinth", "Mat_MTL_Window_Glass_Dark", "Mat_MTL_Dark_Bronze_CurtainWall", "Mat_MTL_Slate_Roof_Dark"):
            obj.data.materials.append(pal[mn])
        bm = bmesh.new()
        z_eaves = 10.2
        extrude_prism_in_bm(bm, coords, 0.16, z_eaves, mat_side=0, mat_top=None)
        extrude_prism_in_bm(bm, inset_polygon_2d(coords, -0.08), 0.16, 1.35, mat_side=1, mat_top=1)
        roof_in = inset_polygon_2d(coords, 0.35)
        extrude_prism_in_bm(bm, roof_in, z_eaves - 0.25, z_eaves - 0.15, mat_side=4, mat_top=4)
        mon_pts = inset_polygon_2d(coords, 4.2)
        if len(mon_pts) >= 3:
            extrude_prism_in_bm(bm, mon_pts, z_eaves - 0.15, z_eaves + 2.4, mat_side=2, mat_top=0)
        pts_ccw = ensure_ccw(coords)
        for i in range(len(pts_ccw)):
            p1, p2 = pts_ccw[i], pts_ccw[(i + 1) % len(pts_ccw)]
            seg_l = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_l >= 5.0:
                nb = max(1, int(seg_l // 4.8))
                bw = seg_l / nb
                ux, uy = (p2[0] - p1[0]) / seg_l, (p2[1] - p1[1]) / seg_l
                for b_i in range(nb):
                    bs = (p1[0] + ux * (b_i * bw + bw * 0.16), p1[1] + uy * (b_i * bw + bw * 0.16))
                    be = (p1[0] + ux * ((b_i + 1) * bw - bw * 0.16), p1[1] + uy * ((b_i + 1) * bw - bw * 0.16))
                    add_recessed_window_bay(bm, bs, be, 1.5, 5.4, recess=0.52, frame_mat=3, glass_mat=2, sill_mat=1, lintel_mat=3)
                    add_recessed_window_bay(bm, bs, be, 6.0, 9.2, recess=0.48, frame_mat=3, glass_mat=2, sill_mat=3, lintel_mat=3)
        assign_world_uvs_to_bm(bm, default_tile_m=4.0)
        bm.to_mesh(me)
        bm.free()
        me.update()

    # 3. L'Héritage du Vieux-Port (OSM 46866834 - 9-story luxury heritage brick & limestone residence)
    b_her = bldgs.get(46866834)
    if b_her:
        coords = clean_poly_pts(b_her["coords_xy"])
        me = bpy.data.meshes.new("Heritage_Vieux_Port_46866834_Mesh")
        obj = bpy.data.objects.new("Bldg_Heritage_du_Vieux_Port_46866834", me)
        parent_col.objects.link(obj)
        for mn in ("Mat_MTL_Heritage_RedBrick", "Mat_MTL_WarmBuff_Limestone", "Mat_MTL_Window_Glass_Dark", "Mat_MTL_Slate_Roof_Dark", "Mat_MTL_Victorian_Brick"):
            obj.data.materials.append(pal[mn])
        bm = bmesh.new()
        z_parapet = 32.6
        extrude_prism_in_bm(bm, coords, 0.16, z_parapet, mat_side=0, mat_top=None)
        extrude_prism_in_bm(bm, inset_polygon_2d(coords, -0.10), 0.16, 4.2, mat_side=1, mat_top=1)
        roof_in = inset_polygon_2d(coords, 0.40)
        extrude_prism_in_bm(bm, roof_in, z_parapet - 0.30, z_parapet - 0.15, mat_side=3, mat_top=3)
        pent_in = inset_polygon_2d(coords, 3.8)
        if len(pent_in) >= 3:
            extrude_prism_in_bm(bm, pent_in, z_parapet - 0.15, 35.4, mat_side=4, mat_top=3)
        pts_ccw = ensure_ccw(coords)
        for i in range(len(pts_ccw)):
            p1, p2 = pts_ccw[i], pts_ccw[(i + 1) % len(pts_ccw)]
            seg_l = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_l >= 4.5:
                nb = max(1, int(seg_l // 3.8))
                bw = seg_l / nb
                ux, uy = (p2[0] - p1[0]) / seg_l, (p2[1] - p1[1]) / seg_l
                for fl in range(8):
                    w_bot = 1.2 + fl * 3.7
                    w_top = w_bot + 2.3
                    for b_i in range(nb):
                        bs = (p1[0] + ux * (b_i * bw + bw * 0.20), p1[1] + uy * (b_i * bw + bw * 0.20))
                        be = (p1[0] + ux * ((b_i + 1) * bw - bw * 0.20), p1[1] + uy * ((b_i + 1) * bw - bw * 0.20))
                        add_recessed_window_bay(bm, bs, be, w_bot, w_top, recess=0.48, frame_mat=1, glass_mat=2, sill_mat=1, lintel_mat=1)
        assign_world_uvs_to_bm(bm, default_tile_m=3.5)
        bm.to_mesh(me)
        bm.free()
        me.update()

    print("Constructed Pavilions (Sky-Blue Kiosk & Container), Hangar du Quai de l'Horloge, and L'Héritage du Vieux-Port.")


# ===========================================================================
# 8. REAL POLY HAVEN 3D TREES, STREETLAMPS & BENCHES
# ===========================================================================

def spawn_polyhaven_trees_and_props(parent_col):
    """
    Spawns genuine high-poly Poly Haven 3D trees, streetlamps, and benches at the exact
    satellite_topdown.png and Street View coordinates!
    """
    # Exact tree coordinates on the East Green Park Lawn & Parking Islands from satellite_topdown.png
    # Plus continuation south along the green lawn so Clock_Tower_Quayside_South_Approach sees the lush canopy on the LEFT!
    tree_specs = [
        # Main Park Lawn North-West Cluster (u = 0.31..0.41, v = 0.21..0.33 in satellite_topdown.png)
        (816.0, 816.2, "jacaranda_tree", 1.15),
        (821.2, 815.0, "searsia_burchellii", 1.20),
        (819.5, 808.8, "jacaranda_tree", 1.30),
        (814.5, 804.8, "tree_small_02", 1.15),
        (823.2, 804.2, "searsia_burchellii", 1.15),
        # Main Park Lawn North-East & Mid-East Trees
        (833.5, 812.0, "jacaranda_tree", 1.05),
        (831.0, 801.0, "searsia_burchellii", 1.10),
        # Main Park Lawn Mid-West Cluster (u = 0.30..0.36, v = 0.10..0.16)
        (813.8, 795.0, "jacaranda_tree", 1.20),
        (819.2, 791.2, "searsia_burchellii", 1.15),
        (811.8, 788.8, "tree_small_02", 1.10),
        # Main Park Lawn South-East & Bottom Edge Clusters (u = 0.29..0.45, v = 0.01..0.09)
        (828.2, 788.0, "jacaranda_tree", 1.05),
        (812.2, 779.0, "searsia_burchellii", 1.20),
        (817.5, 777.0, "jacaranda_tree", 1.15),
        (826.5, 778.2, "searsia_burchellii", 1.20),
        (831.2, 776.5, "jacaranda_tree", 1.15),
        # Parking Lot Median Island Trees (exact satellite_topdown.png positions!)
        (796.0, 792.0, "tree_small_02", 0.95),
        (791.5, 779.8, "tree_small_02", 0.95),
        # Southern Continuation along the East Park Lawn (visible on LEFT V1..V3 of Clock_Tower_Quayside_South_Approach!)
        (809.5, 764.0, "jacaranda_tree", 1.20),
        (822.0, 760.0, "searsia_burchellii", 1.15),
        (805.0, 745.0, "jacaranda_tree", 1.20),
        (818.0, 740.0, "searsia_burchellii", 1.15),
        (800.0, 722.0, "jacaranda_tree", 1.15),
        (794.0, 698.0, "searsia_burchellii", 1.15),
        (788.0, 675.0, "jacaranda_tree", 1.10),
    ]

    for idx, (tx, ty, species, sc) in enumerate(tree_specs):
        rot_z = math.radians((idx * 67) % 360)
        kit.append_polyhaven_model(
            species,
            parent_col,
            f"Tree_{idx:02d}_{species}",
            location=(tx, ty, 0.21),
            rotation_z=rot_z,
            scale=sc,
        )

    # Streetlamps along the pier promenade, park edge, and West Mainland Marina promenade
    lamp_coords = [
        (814.5, 819.5), (811.0, 798.0), (806.5, 776.0), (801.5, 752.0),
        (796.5, 728.0), (841.5, 815.0), (836.5, 790.0), (831.5, 765.0),
        (593.5, 646.5), (604.0, 670.0), (614.5, 694.0),  # West Marina promenade lamps
    ]
    for idx, (lx, ly) in enumerate(lamp_coords):
        kit.append_polyhaven_model(
            "street_lamp_01",
            parent_col,
            f"StreetLamp_{idx:02d}",
            location=(lx, ly, 0.21),
            rotation_z=math.radians((idx * 90) % 360),
            scale=1.0,
        )

    # Park & Promenade Benches (modular_street_seating & painted_wooden_bench)
    bench_coords = [
        (838.5, 808.0, 12.0), (835.0, 792.0, 12.0), (831.5, 778.0, 12.0),
        (814.2, 812.0, -168.0), (810.5, 794.0, -168.0), (806.8, 776.0, -168.0),
    ]
    for idx, (bx, by, rot_deg) in enumerate(bench_coords):
        b_model = "modular_street_seating" if idx % 2 == 0 else "painted_wooden_bench"
        kit.append_polyhaven_model(
            b_model,
            parent_col,
            f"Bench_{idx:02d}_{b_model}",
            location=(bx, by, 0.21),
            rotation_z=math.radians(rot_deg),
            scale=1.0,
        )

    print(f"Spawned {len(tree_specs)} Poly Haven 3D trees, {len(lamp_coords)} streetlamps, and {len(bench_coords)} benches.")


# ===========================================================================
# 9. WORLD LIGHTING & OVERVIEW SNAPSHOT RENDER
# ===========================================================================

def setup_world_and_lighting(scene):
    scene.render.engine = "CYCLES"
    if hasattr(scene, "cycles"):
        scene.cycles.samples = 32
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.use_denoising = False

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.20

    if os.path.isfile(HDRI_PATH):
        env_tex = nodes.new("ShaderNodeTexEnvironment")
        env_tex.image = bpy.data.images.load(HDRI_PATH, check_existing=True)
        links.new(env_tex.outputs["Color"], bg.inputs["Color"])
    else:
        bg.inputs["Color"].default_value = (0.72, 0.84, 0.96, 1.0)
    links.new(bg.outputs["Background"], out.inputs["Surface"])

    sun_data = bpy.data.lights.new(name="Sun_MTL_VM_0025", type="SUN")
    sun_data.energy = 3.8
    sun_data.color = (1.0, 0.96, 0.90)
    sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name="Sun_MTL_VM_0025", object_data=sun_data)
    scene.collection.objects.link(sun_obj)
    # Sun angle casting shadow to the North-West / North as seen in satellite_topdown.png
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(-18.0), math.radians(25.0))


def render_overview_snapshot(scene, cam_col):
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100

    ov_data = bpy.data.cameras.new(name=f"Cam_Overview_{BLOCK_ID}")
    ov_data.lens_unit = "FOV"
    ov_data.angle = math.radians(62.0)
    ov_data.clip_start = 0.5
    ov_data.clip_end = 2500.0
    ov_obj = bpy.data.objects.new(name=f"Cam_Overview_{BLOCK_ID}", object_data=ov_data)
    cam_col.objects.link(ov_obj)

    ov_obj.location = (735.0, 745.0, 72.0)
    look_vec = Vector((828.0, 848.0, 14.0)) - ov_obj.location
    ov_obj.rotation_euler = look_vec.to_track_quat("-Z", "Y").to_euler()

    scene.camera = ov_obj
    scene.render.filepath = SNAPSHOT_PATH
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Overview Snapshot -> {SNAPSHOT_PATH}")
    sys.stdout.flush()


# ===========================================================================
# 10. MAIN EXECUTION PIPELINE
# ===========================================================================

def main():
    print(f"=== Starting Build for Block {BLOCK_ID} (Iteration 2) ===")
    sys.stdout.flush()
    clear_scene()

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    pal = setup_materials()

    root_col = ensure_collection(f"Block_{BLOCK_ID}")
    owned_col = ensure_collection(f"Block_{BLOCK_ID}_Owned", parent=root_col)
    cam_col = ensure_collection(f"Block_{BLOCK_ID}_Cameras", parent=root_col)

    # 1. Exact Quai de l'Horloge Peninsula, 2K PBR River & Marina Basin, Lawns & Parking Lot
    build_ground_peninsula_water_and_lawns(dossier, owned_col, pal)

    # 2. Plage de l'Horloge Urban Beach, Boardwalk, Bleachers, Ivy Wall, Shade Sail & 29 Sky-Blue Parasols
    build_plage_de_l_horloge_and_parasols(owned_col, pal)

    # 3. Bassin de l'Horloge Yacht Marina Pontoons, 15 3D Yachts/Boats & Parked Vehicles
    build_yacht_marina_and_vessels(owned_col, pal)

    # 4. 45m Beaux-Arts Tour de l'Horloge & Western Podium
    build_tour_de_l_horloge(owned_col, pal)

    # 5. Pavilions (Sky-Blue Roof Kiosk & Container), Hangar Shed & L'Héritage du Vieux-Port
    build_other_owned_buildings(dossier, owned_col, pal)

    # 6. Real Poly Haven 3D Trees, Streetlamps & Benches
    spawn_polyhaven_trees_and_props(owned_col)

    # 7. World Lighting & Overview Snapshot
    scene = bpy.context.scene
    setup_world_and_lighting(scene)
    render_overview_snapshot(scene, cam_col)

    # 8. Save Clean .blend & Export .usdc
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

    bpy.ops.wm.usd_export(filepath=USDC_OUT_PATH, check_existing=False)
    print(f"Exported clean USD to {USDC_OUT_PATH}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
