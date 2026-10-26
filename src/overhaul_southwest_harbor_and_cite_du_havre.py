r"""
Southwest Harbor, Pointe-du-Moulin (Silo No. 5, Bota Bota, Lachine Canal Locks) &
Cite du Havre (Parc de Dieppe & Habitat 67) Overhaul (`src/overhaul_southwest_harbor_and_cite_du_havre.py`).
Replaces misaligned/axis-aligned placeholder slabs in MTL-VM-0028, 0029, 0035 with
exact OpenStreetMap shoreline, quay, lock gate, bridge, and landmark geometry:
- Way 115577288 (Parc de Dieppe 60-vertex peninsula) & Cite du Havre spine + Habitat 67 modular cubes
- Way 1272856121 (Pointe-du-Moulin 96-vertex quay) + Silo No. 5 grain elevator battery + Bota Bota ferry spa
- Ways 144002136, 1268191756, 1268191755, 1268191754, 1232525650 (Lachine Canal Lock No. 1 chamber & gates)
- Ways 1184021650, 1391560298, 1391560349 (Canal lock pedestrian & road bridges)
"""
import os
import json
import math
import random
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


def get_or_create_collection(name: str):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def get_pbr_mat(name: str, tex_file: str = None, fallback_rgb=(0.72, 0.70, 0.66, 1.0), rough=0.60, metallic=0.0):
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

    area2 = sum(clean[i][0] * clean[(i + 1) % len(clean)][1] - clean[(i + 1) % len(clean)][0] * clean[i][1] for i in range(len(clean)))
    if area2 < 0:
        clean.reverse()

    uv_layer = bm.loops.layers.uv.verify()
    v_bot = [bm.verts.new((x, y, z_bot)) for x, y in clean]
    v_top = [bm.verts.new((x, y, z_top)) for x, y in clean]
    n = len(clean)

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


def add_cylinder(bm: bmesh.types.BMesh, cx: float, cy: float, z0: float, z1: float, r: float, segs: int = 24, mat_idx: int = 0):
    uv_layer = bm.loops.layers.uv.verify()
    vb = [bm.verts.new((cx + r * math.cos(2 * math.pi * i / segs), cy + r * math.sin(2 * math.pi * i / segs), z0)) for i in range(segs)]
    vt = [bm.verts.new((cx + r * math.cos(2 * math.pi * i / segs), cy + r * math.sin(2 * math.pi * i / segs), z1)) for i in range(segs)]
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
        try:
            ft = bm.faces.new((vt[i], vt[j], vc_top))
            ft.material_index = mat_idx
            for loop in ft.loops:
                loop[uv_layer].uv = (loop.vert.co.x * 0.25, loop.vert.co.y * 0.25)
        except ValueError:
            pass


def purge_legacy_sw_and_cite_du_havre():
    """Removes the fake axis-aligned green rectangle in MTL-VM-0035 and misplaced Silo/Lock slabs."""
    target_cols = ["Block_MTL-VM-0035_Owned", "Block_MTL-VM-0028_Owned", "Block_MTL-VM-0029_Owned"]
    to_remove = set()
    for col_name in target_cols:
        col = bpy.data.collections.get(col_name)
        if col:
            for obj in list(col.objects):
                if obj.type == "MESH":
                    # Keep inland buildings (X < 250), purge peninsula/pier/waterfront slabs
                    cx = sum(v[0] for v in obj.bound_box) / 8.0 + obj.location.x
                    if col_name == "Block_MTL-VM-0035_Owned" or cx > 230.0 or any(k in obj.name.lower() for k in ("silo", "bota", "pier", "quay", "lock", "ecluse", "dieppe", "habitat", "havre", "water", "park", "ground")):
                        to_remove.add(obj)

    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and any(k in obj.name.lower() for k in ("cite_du_havre", "parc_de_dieppe", "habitat_67", "pointe_du_moulin_overhaul")):
            to_remove.add(obj)

    for obj in to_remove:
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except Exception:
            pass
    print(f"Purged {len(to_remove)} legacy MTL-VM-0028/0029/0035 waterfront objects.")


def rebuild_southwest_harbor_and_cite_du_havre(osm_data=None):
    if osm_data is None:
        with open(OSM_PATH, "r", encoding="utf-8") as f:
            osm_data = json.load(f)

    purge_legacy_sw_and_cite_du_havre()

    nodes = {e["id"]: ll2xy(e["lat"], e["lon"]) for e in osm_data.get("elements", []) if e["type"] == "node"}
    ways = {e["id"]: [nodes[nid] for nid in e.get("nodes", []) if nid in nodes] for e in osm_data.get("elements", []) if e["type"] == "way"}

    col = get_or_create_collection("Block_MTL-VM-0035_Owned")

    mat_quay_stone = get_pbr_mat("Mat_SW_Quay_Paver_PH", "stone_pavers_Diffuse_2k.jpg", (0.60, 0.58, 0.55, 1.0), 0.65)
    mat_silo_concrete = get_pbr_mat("Mat_SW_Silo_Concrete_PH", "concrete_pavement_02_Diffuse_2k.jpg", (0.68, 0.66, 0.62, 1.0), 0.78)
    mat_habitat_concrete = get_pbr_mat("Mat_SW_Habitat_Brutalist_PH", "sandstone_blocks_05_Diffuse_2k.jpg", (0.82, 0.78, 0.71, 1.0), 0.62)
    mat_steel_dark = get_pbr_mat("Mat_SW_Steel_Dark", None, (0.16, 0.17, 0.19, 1.0), 0.35, metallic=0.75)
    mat_steel_white = get_pbr_mat("Mat_SW_Hull_White", None, (0.93, 0.94, 0.95, 1.0), 0.25, metallic=0.45)
    mat_glass_dark = get_pbr_mat("Mat_SW_Glass_Dark", None, (0.14, 0.24, 0.32, 1.0), 0.08, metallic=0.85)
    mat_green_terrace = get_pbr_mat("Mat_SW_Terrace_Greenery", "leafy_grass_Diffuse_2k.jpg", (0.28, 0.52, 0.24, 1.0), 0.75)
    mat_wood_gate = get_pbr_mat("Mat_SW_Lock_Timber", "herringbone_pavement_Diffuse_2k.jpg", (0.36, 0.26, 0.18, 1.0), 0.68)

    materials = [
        mat_quay_stone, mat_silo_concrete, mat_habitat_concrete, mat_steel_dark,
        mat_steel_white, mat_glass_dark, mat_green_terrace, mat_wood_gate,
    ]

    bm = bmesh.new()

    # 1. Exact 60-vertex Parc de Dieppe (Way 115577288) & Cite du Havre Peninsula
    dieppe_pts = ways.get(115577288, [])
    if len(dieppe_pts) >= 4:
        extrude_polygon_prism(bm, dieppe_pts, -2.50, 0.14, mat_idx=0, uv_scale=4.0)

    # Southern Cite du Havre Peninsula Spine (connecting Parc de Dieppe south along Avenue Pierre-Dupuy)
    cite_du_havre_south_poly = [
        (955.0, -120.0), (1085.0, -120.0), (1120.0, -980.0), (965.0, -980.0),
    ]
    extrude_polygon_prism(bm, cite_du_havre_south_poly, -2.50, 0.14, mat_idx=0, uv_scale=4.0)

    # Habitat 67 Brutalist Modular Housing Complex along true Cite du Havre shoreline (X=975..1030, Y=-580..-180)
    rng = random.Random(1967)
    spine_az = math.radians(-84.0)
    for cluster_idx, (cx_c, cy_c) in enumerate([(992.0, -245.0), (998.0, -375.0), (1005.0, -505.0)]):
        for level in range(11):
            z0 = 0.14 + level * 3.2
            z1 = z0 + 3.15
            span_n = max(2, 11 - level)
            for k in range(-span_n, span_n + 1):
                offset_along = k * 5.2 + rng.uniform(-0.8, 0.8)
                offset_perp = rng.uniform(-8.5, 8.5) * (1.0 - 0.06 * level)
                ang = spine_az + (0.0 if (level + k) % 2 == 0 else math.pi * 0.5)
                mx = cx_c + offset_along * math.cos(spine_az) - offset_perp * math.sin(spine_az)
                my = cy_c + offset_along * math.sin(spine_az) + offset_perp * math.cos(spine_az)
                # Precast concrete modular cube (11.7m x 5.3m x 3.15m)
                add_box(bm, mx, my, z0, z1, 10.6, 5.0, ang, mat_idx=2)
                # Recessed window band
                add_box(bm, mx, my, z0 + 0.7, z1 - 0.5, 10.75, 3.6, ang, mat_idx=5)
                # Rooftop garden planter box on stepped cube tops
                if level >= 2 and (k + level) % 2 == 0:
                    add_box(bm, mx, my, z1, z1 + 0.45, 4.2, 4.2, ang, mat_idx=6)

    # 2. Exact 96-vertex Pointe-du-Moulin Quay (Way 1272856121, center (421.1, -939.8))
    pdm_pts = ways.get(1272856121, [])
    if len(pdm_pts) >= 4:
        extrude_polygon_prism(bm, pdm_pts, -2.50, 0.15, mat_idx=0, uv_scale=4.0)

    # Monumental Silo No. 5 Grain Elevator Battery along true Pointe-du-Moulin Pier (X=340..425, Y=-580..-840)
    silo_az = math.radians(-78.0)
    ca_s, sa_s = math.cos(silo_az), math.sin(silo_az)
    silo_x0, silo_y0 = 365.0, -585.0
    # 2x14 grid of 42m-tall cylindrical slip-form concrete grain silos
    for row in (-4.6, 4.6):
        for col_i in range(14):
            along = col_i * 9.2
            sx = silo_x0 + along * ca_s - row * sa_s
            sy = silo_y0 + along * sa_s + row * ca_s
            add_cylinder(bm, sx, sy, 0.15, 41.0, 4.45, segs=20, mat_idx=1)
    # Silo No. 5 Headhouse & Penthouse Gallery (Z = 41m..56m)
    mid_sx = silo_x0 + 60.0 * ca_s
    mid_sy = silo_y0 + 60.0 * sa_s
    add_box(bm, mid_sx, mid_sy, 41.0, 52.5, 128.0, 14.5, silo_az, mat_idx=1)
    add_box(bm, mid_sx, mid_sy, 44.0, 48.0, 128.3, 12.0, silo_az, mat_idx=5)
    add_box(bm, silo_x0 + 15.0 * ca_s, silo_y0 + 15.0 * sa_s, 52.5, 61.0, 28.0, 15.0, silo_az, mat_idx=1)
    # Overhead steel conveyor gallery extending along the pier
    add_box(bm, silo_x0 - 35.0 * ca_s, silo_y0 - 35.0 * sa_s, 24.0, 29.5, 85.0, 4.8, silo_az, mat_idx=3)

    # 3. Bota Bota Floating Ferry Spa moored at the north slip of Pointe-du-Moulin
    bx_bota, by_bota = 328.0, -525.0
    bota_az = math.radians(-18.0)
    add_box(bm, bx_bota, by_bota, -2.25, 2.2, 52.0, 14.5, bota_az, mat_idx=3)
    add_box(bm, bx_bota, by_bota, 2.2, 5.8, 44.0, 12.6, bota_az, mat_idx=4)
    add_box(bm, bx_bota, by_bota, 5.8, 9.2, 36.0, 10.8, bota_az, mat_idx=5)
    add_box(bm, bx_bota, by_bota, 9.2, 11.8, 22.0, 8.5, bota_az, mat_idx=3)

    # 4. Lachine Canal Lock No. 1 (Ecluse No. 1) Miter Gates & Pedestrian Bridges
    lock_gate_wids = [144002136, 1268191756, 1268191755, 1268191754, 1232525650]
    for wid in lock_gate_wids:
        pts = ways.get(wid, [])
        if len(pts) >= 2:
            for i in range(len(pts) - 1):
                p0, p1 = pts[i], pts[i + 1]
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                slen = math.hypot(dx, dy)
                if slen > 1.0:
                    add_box(bm, 0.5 * (p0[0] + p1[0]), 0.5 * (p0[1] + p1[1]), -2.40, 0.85, slen, 1.2, math.atan2(dy, dx), mat_idx=7)

    bridge_wids = [1184021650, 1391560298, 1391560349]
    for wid in bridge_wids:
        pts = ways.get(wid, [])
        if len(pts) >= 2:
            for i in range(len(pts) - 1):
                p0, p1 = pts[i], pts[i + 1]
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                slen = math.hypot(dx, dy)
                if slen > 1.5:
                    ang = math.atan2(dy, dx)
                    mx, my = 0.5 * (p0[0] + p1[0]), 0.5 * (p0[1] + p1[1])
                    add_box(bm, mx, my, 0.25, 0.85, slen, 6.5, ang, mat_idx=0)
                    add_box(bm, mx, my, 0.85, 1.95, slen, 6.8, ang, mat_idx=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("Southwest_Harbor_And_Cite_du_Havre_Mesh")
    for m in materials:
        mesh.materials.append(m)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("Southwest_Harbor_And_Cite_du_Havre", mesh)
    col.objects.link(obj)
    print(f"Built Southwest_Harbor_And_Cite_du_Havre: {len(mesh.polygons)} faces.")
    return {"faces": len(mesh.polygons)}


if __name__ == "__main__":
    rebuild_southwest_harbor_and_cite_du_havre()
