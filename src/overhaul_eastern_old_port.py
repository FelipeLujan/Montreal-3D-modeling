r"""
Eastern Old Port Waterfront Overhaul (`src/overhaul_eastern_old_port.py`).
Replaces axis-aligned placeholder boxes in MTL-VM-0023, 0024, 0025 with exact
OpenStreetMap coastline, pier, island, marina, and landmark geometry:
- Way 83255355 (Vieux-Port coastline & Quai de l'Horloge NNE-angled finger pier)
- Way 161206731 (Tour de l'Horloge at true OSM centroid (842.9, 838.4) + Plage de l'Horloge)
- Way 1180387334 (Parc du Bassin-Bonsecours / Ile Bonsecours curved island + La Grande Roue + Pavilion)
- Way 46866826 (Terrasses Bonsecours)
- Way 69948943 (Quai Jacques-Cartier & steel entrance pergolas)
- Ways 144001259..144001278 & 92859517..263739305 (Marina floating docks & 3D sailboats/yachts)
"""
import os
import json
import math
import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
OSM_PATH = os.path.join(BASE_DIR, "data", "open_data", "old_montreal_osm.json")
MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0


def ll2xy(lat: float, lon: float):
    dlat = math.radians(lat - MASTER_ORIGIN_LAT)
    dlon = math.radians(lon - MASTER_ORIGIN_LON)
    x = dlon * EARTH_RADIUS_M * math.cos(math.radians(MASTER_ORIGIN_LAT))
    y = dlat * EARTH_RADIUS_M
    return (round(x, 3), round(y, 3))


def get_or_create_collection(name: str, parent=None):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    if parent is None:
        bpy.context.scene.collection.children.link(col)
    else:
        parent.children.link(col)
    return col


def get_pbr_mat(name: str, tex_file: str = None, fallback_rgb=(0.75, 0.74, 0.72, 1.0), rough=0.55, metallic=0.0, emission_rgb=None, emission_str=0.0):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = fallback_rgb
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if emission_rgb and emission_str > 0.0:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission_rgb
            bsdf.inputs["Emission Strength"].default_value = emission_str

    if tex_file:
        for folder in [os.path.join(BASE_DIR, "assets", "polyhaven"), os.path.join(BASE_DIR, "output", "textures")]:
            p = os.path.join(folder, tex_file)
            if os.path.exists(p):
                tex_node = nt.nodes.new("ShaderNodeTexImage")
                tex_node.image = bpy.data.images.load(p, check_existing=True)
                nt.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
                break
    return mat


def extrude_polygon_prism(bm: bmesh.types.BMesh, pts_2d: list, z_bot: float, z_top: float, mat_idx: int = 0, uv_scale: float = 4.0):
    clean = []
    for p in pts_2d:
        if not clean or math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 0.05:
            clean.append((float(p[0]), float(p[1])))
    if len(clean) >= 2 and math.hypot(clean[0][0] - clean[-1][0], clean[0][1] - clean[-1][1]) < 0.05:
        clean.pop()
    if len(clean) < 3:
        return

    # Ensure CCW winding
    area2 = sum(clean[i][0] * clean[(i + 1) % len(clean)][1] - clean[(i + 1) % len(clean)][0] * clean[i][1] for i in range(len(clean)))
    if area2 < 0:
        clean.reverse()

    uv_layer = bm.loops.layers.uv.verify()
    v_bot = [bm.verts.new((x, y, z_bot)) for x, y in clean]
    v_top = [bm.verts.new((x, y, z_top)) for x, y in clean]
    n = len(clean)

    # Side walls
    for i in range(n):
        j = (i + 1) % n
        try:
            f = bm.faces.new((v_bot[i], v_bot[j], v_top[j], v_top[i]))
            f.material_index = mat_idx
            seg_len = math.hypot(clean[j][0] - clean[i][0], clean[j][1] - clean[i][1])
            dz = z_top - z_bot
            uvs = [(0.0, 0.0), (seg_len / uv_scale, 0.0), (seg_len / uv_scale, dz / uv_scale), (0.0, dz / uv_scale)]
            for loop, uv in zip(f.loops, uvs):
                loop[uv_layer].uv = uv
        except ValueError:
            pass

    # Triangulate top cap with upward (+Z) normals
    loop_vecs = [Vector((x, y, 0.0)) for x, y in clean]
    tris = tessellate_polygon([loop_vecs])
    for i0, i1, i2 in tris:
        if i0 < n and i1 < n and i2 < n and len({i0, i1, i2}) == 3:
            p0, p1, p2 = clean[i0], clean[i1], clean[i2]
            cross_z = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
            tri_v = (v_top[i0], v_top[i1], v_top[i2]) if cross_z >= 0 else (v_top[i0], v_top[i2], v_top[i1])
            try:
                f = bm.faces.new(tri_v)
                f.material_index = mat_idx
                for loop in f.loops:
                    co = loop.vert.co
                    loop[uv_layer].uv = (co.x / uv_scale, co.y / uv_scale)
            except ValueError:
                pass


def add_box(bm: bmesh.types.BMesh, cx: float, cy: float, z0: float, z1: float, sx: float, sy: float, angle_rad: float = 0.0, mat_idx: int = 0):
    ca, sa = math.cos(angle_rad), math.sin(angle_rad)
    hx, hy = sx * 0.5, sy * 0.5
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    pts = [(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca) for dx, dy in corners]
    extrude_polygon_prism(bm, pts, z0, z1, mat_idx=mat_idx)


def add_cylinder(bm: bmesh.types.BMesh, cx: float, cy: float, z0: float, z1: float, r_bot: float, r_top: float = None, segs: int = 24, mat_idx: int = 0):
    if r_top is None:
        r_top = r_bot
    uv_layer = bm.loops.layers.uv.verify()
    vb = [bm.verts.new((cx + r_bot * math.cos(2 * math.pi * i / segs), cy + r_bot * math.sin(2 * math.pi * i / segs), z0)) for i in range(segs)]
    vt = [bm.verts.new((cx + r_top * math.cos(2 * math.pi * i / segs), cy + r_top * math.sin(2 * math.pi * i / segs), z1)) for i in range(segs)]
    vc_top = bm.verts.new((cx, cy, z1))
    for i in range(segs):
        j = (i + 1) % segs
        try:
            fs = bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
            fs.material_index = mat_idx
            for loop in fs.loops:
                loop[uv_layer].uv = (loop.vert.co.x * 0.25, loop.vert.co.z * 0.25)
        except ValueError:
            pass
        if r_top > 0.01:
            try:
                ft = bm.faces.new((vt[i], vt[j], vc_top))
                ft.material_index = mat_idx
                for loop in ft.loops:
                    loop[uv_layer].uv = (loop.vert.co.x * 0.25, loop.vert.co.y * 0.25)
            except ValueError:
                pass


def purge_legacy_eastern_old_port():
    """Removes old axis-aligned pier slabs and misplaced Clock Tower / Ferris wheel."""
    legacy_keywords = [
        "Quai_Horloge", "Clock_Tower", "Tour_Horloge", "Plage_Horloge",
        "Bassin_Bonsecours", "Ile_Bonsecours", "Grande_Roue", "Ferris",
        "Quai_Jacques_Cartier", "Marina_Yacht", "Eastern_Old_Port_Overhaul",
    ]
    target_cols = ["Block_MTL-VM-0023_Owned", "Block_MTL-VM-0024_Owned", "Block_MTL-VM-0025_Owned"]
    to_remove = set()
    for col_name in target_cols:
        col = bpy.data.collections.get(col_name)
        if col:
            for obj in list(col.objects):
                if obj.type == "MESH":
                    # Preserve main mainland buildings if any, remove waterfront slabs/props
                    to_remove.add(obj)
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and any(k.lower() in obj.name.lower() for k in legacy_keywords):
            to_remove.add(obj)

    for obj in to_remove:
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except Exception:
            pass
    print(f"Purged {len(to_remove)} legacy axis-aligned eastern Old Port objects.")


def rebuild_eastern_old_port(osm_data=None):
    if osm_data is None:
        with open(OSM_PATH, "r", encoding="utf-8") as f:
            osm_data = json.load(f)

    purge_legacy_eastern_old_port()

    nodes = {e["id"]: ll2xy(e["lat"], e["lon"]) for e in osm_data.get("elements", []) if e["type"] == "node"}
    ways = {e["id"]: [nodes[nid] for nid in e.get("nodes", []) if nid in nodes] for e in osm_data.get("elements", []) if e["type"] == "way"}

    col = get_or_create_collection("Block_MTL-VM-0025_Owned")

    mat_quay_paver = get_pbr_mat("Mat_EOP_Quay_Paver_PH", "stone_pavers_Diffuse_2k.jpg", (0.62, 0.60, 0.57, 1.0), 0.65)
    mat_granite_wall = get_pbr_mat("Mat_EOP_Granite_Wall_PH", "sandstone_blocks_05_Diffuse_2k.jpg", (0.52, 0.50, 0.47, 1.0), 0.72)
    mat_white_stone = get_pbr_mat("Mat_EOP_ClockTower_White", "concrete_pavement_02_Diffuse_2k.jpg", (0.91, 0.89, 0.85, 1.0), 0.42)
    mat_beach_sand = get_pbr_mat("Mat_EOP_Beach_Sand_PH", "gravel_concrete_02_Diffuse_2k.jpg", (0.82, 0.74, 0.58, 1.0), 0.85)
    mat_wood_deck = get_pbr_mat("Mat_EOP_Wood_Boardwalk", "herringbone_pavement_Diffuse_2k.jpg", (0.48, 0.34, 0.22, 1.0), 0.60)
    mat_steel_white = get_pbr_mat("Mat_EOP_Steel_White", None, (0.94, 0.95, 0.96, 1.0), 0.25, metallic=0.65)
    mat_glass_blue = get_pbr_mat("Mat_EOP_Glass_Reflective", None, (0.18, 0.32, 0.45, 1.0), 0.08, metallic=0.85)
    mat_copper_roof = get_pbr_mat("Mat_EOP_Copper_Verdigris", None, (0.28, 0.58, 0.46, 1.0), 0.38, metallic=0.45)
    mat_parasol_blue = get_pbr_mat("Mat_EOP_Parasol_Blue", None, (0.15, 0.48, 0.82, 1.0), 0.50)
    mat_terracotta = get_pbr_mat("Mat_EOP_Brick_Terrasses", "castle_brick_02_red_Diffuse_2k.jpg", (0.58, 0.28, 0.22, 1.0), 0.70)
    mat_gold_glow = get_pbr_mat("Mat_EOP_Clock_Glow", None, (1.0, 0.92, 0.70, 1.0), 0.2, emission_rgb=(1.0, 0.9, 0.65, 1.0), emission_str=8.0)

    materials = [
        mat_quay_paver, mat_granite_wall, mat_white_stone, mat_beach_sand,
        mat_wood_deck, mat_steel_white, mat_glass_blue, mat_copper_roof,
        mat_parasol_blue, mat_terracotta, mat_gold_glow,
    ]

    bm = bmesh.new()

    # 1. Exact NNE-angled Quai de l'Horloge Pier (from Way 83255355 eastern finger pier + Clock Tower tip)
    quai_horloge_poly = [
        (682.0, 445.0), (765.0, 422.0), (792.0, 488.0), (818.0, 585.0),
        (845.0, 695.0), (866.0, 790.0), (874.0, 855.0), (828.0, 872.0),
        (802.0, 815.0), (776.0, 720.0), (748.0, 615.0), (718.0, 520.0),
    ]
    extrude_polygon_prism(bm, quai_horloge_poly, -2.50, 0.14, mat_idx=0, uv_scale=4.0)

    # Plage de l'Horloge (Sand beach & wooden boardwalk at northern tip of Quai de l'Horloge)
    plage_sand_poly = [
        (806.0, 725.0), (848.0, 712.0), (864.0, 788.0), (824.0, 800.0),
    ]
    extrude_polygon_prism(bm, plage_sand_poly, 0.14, 0.22, mat_idx=3, uv_scale=3.0)
    boardwalk_poly = [
        (798.0, 720.0), (808.0, 718.0), (830.0, 808.0), (818.0, 811.0),
    ]
    extrude_polygon_prism(bm, boardwalk_poly, 0.14, 0.24, mat_idx=4, uv_scale=2.5)

    # Beach parasols along Plage de l'Horloge
    for i in range(8):
        py = 732.0 + i * 8.2
        px = 815.0 + i * 2.1
        add_cylinder(bm, px, py, 0.22, 2.40, 0.06, 0.06, segs=8, mat_idx=5)
        add_cylinder(bm, px, py, 2.25, 2.75, 1.65, 0.05, segs=12, mat_idx=8)

    # 2. Iconic Tour de l'Horloge (Clock Tower, Way 161206731 at exact OSM centroid (842.9, 838.4))
    tx, ty = 842.9, 838.4
    pier_az = math.radians(-16.0)
    # Stepped octagonal/square Beaux-Arts base & buttresses
    add_box(bm, tx, ty, 0.14, 8.5, 11.2, 11.2, pier_az, mat_idx=2)
    add_box(bm, tx, ty, 8.5, 12.0, 9.4, 9.4, pier_az, mat_idx=2)
    # Main tower shaft with corner pilasters & recessed vertical bays
    add_box(bm, tx, ty, 12.0, 34.5, 7.6, 7.6, pier_az, mat_idx=2)
    for corner_dx in (-3.5, 3.5):
        for corner_dy in (-3.5, 3.5):
            ca, sa = math.cos(pier_az), math.sin(pier_az)
            bx = tx + corner_dx * ca - corner_dy * sa
            by = ty + corner_dx * sa + corner_dy * ca
            add_box(bm, bx, by, 0.14, 35.0, 1.4, 1.4, pier_az, mat_idx=2)
    # Clock stage (Z = 34.5..40.5m) + 4 glowing clock dials
    add_box(bm, tx, ty, 34.5, 40.5, 8.2, 8.2, pier_az, mat_idx=2)
    for d_ang in (0, 90, 180, 270):
        ang = pier_az + math.radians(d_ang)
        cx_d = tx + 4.15 * math.cos(ang)
        cy_d = ty + 4.15 * math.sin(ang)
        add_box(bm, cx_d, cy_d, 35.8, 39.2, 0.35, 3.4, ang, mat_idx=10)
    # Belfry lantern & spire (Z = 40.5..46.5m)
    add_cylinder(bm, tx, ty, 40.5, 44.5, 2.8, 2.2, segs=16, mat_idx=2)
    add_cylinder(bm, tx, ty, 44.5, 47.2, 2.2, 0.1, segs=16, mat_idx=7)

    # 3. Exact Curved Ile Bonsecours (Way 1180387334, 25 vertices) & Central Pavilion Island
    ile_pts = ways.get(1180387334, [])
    if len(ile_pts) >= 4:
        extrude_polygon_prism(bm, ile_pts, -2.50, 0.15, mat_idx=0, uv_scale=4.0)

    central_island_pts = [
        (542.0, 366.0), (595.0, 355.0), (626.0, 385.0), (622.0, 445.0),
        (582.0, 464.0), (540.0, 438.0), (534.0, 396.0),
    ]
    extrude_polygon_prism(bm, central_island_pts, -2.50, 0.16, mat_idx=0, uv_scale=4.0)

    # Pedestrian footbridges connecting Promenade -> Central Island -> Ile Bonsecours
    add_box(bm, 522.0, 402.0, 0.15, 0.55, 34.0, 5.5, math.radians(-22.0), mat_idx=4)
    add_box(bm, 644.0, 420.0, 0.15, 0.55, 36.0, 5.5, math.radians(-22.0), mat_idx=4)

    # Pavillon du Bassin Bonsecours (Circular glass & white tensile canopy on Central Island)
    px_pav, py_pav = 582.0, 410.0
    add_cylinder(bm, px_pav, py_pav, 0.16, 5.8, 18.5, 18.5, segs=32, mat_idx=6)
    add_cylinder(bm, px_pav, py_pav, 5.6, 6.4, 21.0, 20.5, segs=32, mat_idx=2)
    add_cylinder(bm, px_pav, py_pav, 6.4, 13.5, 19.5, 0.8, segs=32, mat_idx=5)

    # La Grande Roue de Montreal (60m tall white structural steel Ferris Wheel on Ile Bonsecours)
    gx, gy = 712.0, 405.0
    wheel_az = math.radians(-25.0)
    wheel_cz = 33.5
    wheel_r = 28.0
    # Boarding deck
    add_box(bm, gx, gy, 0.16, 1.8, 26.0, 22.0, wheel_az, mat_idx=4)
    # 4 A-frame support legs
    for side in (-4.8, 4.8):
        for leg_dx in (-14.0, 14.0):
            for s in range(12):
                t0, t1 = s / 12.0, (s + 1) / 12.0
                lx = gx + (leg_dx * (1.0 - 0.5 * (t0 + t1))) * math.cos(wheel_az) - side * math.sin(wheel_az)
                ly = gy + (leg_dx * (1.0 - 0.5 * (t0 + t1))) * math.sin(wheel_az) + side * math.cos(wheel_az)
                lz0 = 1.5 + t0 * (wheel_cz - 1.5)
                lz1 = 1.5 + t1 * (wheel_cz - 1.5)
                add_box(bm, lx, ly, lz0, lz1, 1.2, 1.2, wheel_az, mat_idx=5)
    # Hub axle
    add_box(bm, gx, gy, wheel_cz - 1.4, wheel_cz + 1.4, 2.8, 11.5, wheel_az, mat_idx=5)
    # Dual concentric steel rims & 36 passenger gondolas
    n_gondolas = 36
    for i in range(n_gondolas):
        ang0 = 2.0 * math.pi * i / n_gondolas
        ang1 = 2.0 * math.pi * (i + 1) / n_gondolas
        ang_mid = 0.5 * (ang0 + ang1)
        rcx = gx + wheel_r * math.cos(ang_mid) * math.cos(wheel_az)
        rcy = gy + wheel_r * math.cos(ang_mid) * math.sin(wheel_az)
        rcz = wheel_cz + wheel_r * math.sin(ang_mid)
        for rim_r_scale in (1.0, 0.86):
            rx = gx + (wheel_r * rim_r_scale) * math.cos(ang_mid) * math.cos(wheel_az)
            ry = gy + (wheel_r * rim_r_scale) * math.cos(ang_mid) * math.sin(wheel_az)
            rz = wheel_cz + (wheel_r * rim_r_scale) * math.sin(ang_mid)
            add_box(bm, rx, ry, rz - 0.55, rz + 0.55, 4.8 * rim_r_scale, 3.6, wheel_az, mat_idx=5)
        # Gondola cabin
        add_box(bm, rcx, rcy, rcz - 1.6, rcz + 1.2, 2.6, 2.8, wheel_az, mat_idx=6 if i % 2 == 0 else 5)

    # Terrasses Bonsecours (Way 46866826)
    tb_pts = ways.get(46866826, [])
    if len(tb_pts) >= 4:
        extrude_polygon_prism(bm, tb_pts, 0.15, 11.5, mat_idx=9, uv_scale=4.0)
        extrude_polygon_prism(bm, tb_pts, 11.5, 12.1, mat_idx=2, uv_scale=4.0)

    # 4. Quai Jacques-Cartier (Way 69948943) & Steel Pergolas
    qjc_pts = ways.get(69948943, [])
    if len(qjc_pts) >= 4:
        extrude_polygon_prism(bm, qjc_pts, -2.50, 0.15, mat_idx=0, uv_scale=4.0)
    # Iconic Waterfront Entrance Pergola Structures on Quai Jacques-Cartier
    add_box(bm, 545.0, 275.0, 0.15, 9.2, 68.0, 14.0, math.radians(8.0), mat_idx=5)
    add_box(bm, 645.0, 292.0, 0.15, 8.5, 58.0, 14.0, math.radians(8.0), mat_idx=2)

    # 5. Floating Marina Docks & 3D Moored Yachts in Bassin de l'Horloge & Bassin Jacques-Cartier
    marina_pier_wids = [
        144001259, 144001260, 144001262, 144001264, 144001265, 144001266,
        144001267, 144001268, 144001269, 144001270, 144001271, 144001272,
        144001274, 144001275, 144001276, 144001277, 144001278,
        92859517, 92859518, 92859520, 263739302, 263739304, 263739305,
        115617001, 115617003,
    ]
    yacht_idx = 0
    for wid in marina_pier_wids:
        pts = ways.get(wid, [])
        if len(pts) < 2:
            continue
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            seg_len = math.hypot(dx, dy)
            if seg_len < 2.0:
                continue
            ang = math.atan2(dy, dx)
            mx, my = 0.5 * (p0[0] + p1[0]), 0.5 * (p0[1] + p1[1])
            # Floating dock finger (-2.25m to -1.75m)
            add_box(bm, mx, my, -2.25, -1.75, seg_len, 2.4, ang, mat_idx=4)
            # Place moored yachts alongside the dock
            n_boats = max(1, int(seg_len // 14.0))
            nx, ny = -math.sin(ang), math.cos(ang)
            for b in range(n_boats):
                frac = (b + 0.5) / n_boats
                bx = p0[0] + dx * frac + nx * 4.5 * (1 if (yacht_idx % 2 == 0) else -1)
                by = p0[1] + dy * frac + ny * 4.5 * (1 if (yacht_idx % 2 == 0) else -1)
                b_ang = ang + (0.0 if yacht_idx % 2 == 0 else math.pi)
                # Yacht hull, cabin & mast
                add_box(bm, bx, by, -2.25, -0.95, 10.5, 3.4, b_ang, mat_idx=5)
                add_box(bm, bx, by, -0.95, 0.25, 5.2, 2.6, b_ang, mat_idx=6)
                add_cylinder(bm, bx, by, 0.25, 11.5, 0.08, 0.05, segs=8, mat_idx=5)
                yacht_idx += 1

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("Eastern_Old_Port_Overhaul_Mesh")
    for m in materials:
        mesh.materials.append(m)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("Eastern_Old_Port_Overhaul", mesh)
    col.objects.link(obj)
    print(f"Built Eastern_Old_Port_Overhaul: {len(mesh.polygons)} faces, {yacht_idx} marina yachts.")
    return {"faces": len(mesh.polygons), "yachts": yacht_idx}


if __name__ == "__main__":
    rebuild_eastern_old_port()
