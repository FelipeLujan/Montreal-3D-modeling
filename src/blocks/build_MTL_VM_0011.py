import bpy
import bmesh
import json
import math
import os
import sys

sys.path.append(r"C:\Users\Felipe\Documents\coding\montreal\src")
import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0011"
DOSSIER_PATH = rf"C:\Users\Felipe\Documents\coding\montreal\data\blocks\{BLOCK_ID}\dossier.json"
RENDERS_DIR = rf"C:\Users\Felipe\Documents\coding\montreal\data\blocks\{BLOCK_ID}\renders"
SNAPSHOT_PATH = rf"C:\Users\Felipe\Documents\coding\montreal\output\renders\{BLOCK_ID}_snapshot.png"
BLEND_PATH = rf"C:\Users\Felipe\Documents\coding\montreal\output\blocks\{BLOCK_ID}.blend"
USDC_PATH = rf"C:\Users\Felipe\Documents\coding\montreal\output\blocks\{BLOCK_ID}.usdc"
ASSETS_PATH = r"C:\Users\Felipe\Documents\coding\montreal\assets\montreal_kit.blend"
TEXTURES_DIR = r"C:\Users\Felipe\Documents\coding\montreal\assets\polyhaven"
HDRI_PATH = r"C:\Users\Felipe\Documents\coding\montreal\assets\polyhaven\kloppenheim_06_puresky_2k.hdr"

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(BLEND_PATH), exist_ok=True)


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


def link_obj(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    if col.name.endswith("_Context_Proxy"):
        obj.hide_render = True
        obj.hide_viewport = True


def make_pbr_mat(name, prefix, tint=(1.0, 1.0, 1.0), scale=0.65, roughness_mult=1.0, metallic=0.0):
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

    diff_path = os.path.join(TEXTURES_DIR, f"{prefix}_Diffuse_2k.jpg")
    rough_path = os.path.join(TEXTURES_DIR, f"{prefix}_Rough_2k.jpg")
    nor_path = os.path.join(TEXTURES_DIR, f"{prefix}_nor_gl_2k.jpg")

    if os.path.exists(diff_path):
        img_d = bpy.data.images.load(diff_path, check_existing=True)
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = img_d
        tex_d.projection = "BOX"
        tex_d.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])

        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["B"].default_value = (tint[0], tint[1], tint[2], 1.0)
        links.new(tex_d.outputs["Color"], mix.inputs["A"])
        links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1.0)

    if os.path.exists(rough_path):
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

    if os.path.exists(nor_path):
        img_n = bpy.data.images.load(nor_path, check_existing=True)
        img_n.colorspace_settings.name = "Non-Color"
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = img_n
        tex_n.projection = "BOX"
        tex_n.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nor = nodes.new("ShaderNodeNormalMap")
        nor.inputs["Strength"].default_value = 0.65
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
    pal = kit.create_montreal_material_palette()
    # Realistic fine Beaux-Arts ashlar stone scaling (0.68..0.85 instead of coarse 0.22)
    pal["limestone_cream"] = make_pbr_mat("WTC_Limestone_Cream", "sandstone_blocks_05", tint=(0.98, 0.94, 0.86), scale=0.68, roughness_mult=0.82)
    pal["limestone_gold"] = make_pbr_mat("WTC_Limestone_Gold", "sandstone_blocks_05", tint=(0.94, 0.85, 0.68), scale=0.72, roughness_mult=0.82)
    pal["limestone_grey"] = make_pbr_mat("WTC_Limestone_Grey", "sandstone_blocks_05", tint=(0.78, 0.80, 0.82), scale=0.68, roughness_mult=0.82)
    pal["granite_dark"] = make_pbr_mat("WTC_Granite_Dark", "sandstone_blocks_05", tint=(0.22, 0.22, 0.24), scale=0.75, roughness_mult=0.55)
    pal["granite_rose"] = make_pbr_mat("WTC_Granite_Rose", "sandstone_blocks_05", tint=(0.72, 0.46, 0.44), scale=0.80, roughness_mult=0.28)
    pal["brick_rose"] = make_pbr_mat("WTC_Brick_Rose", "castle_brick_02_red", tint=(0.90, 0.68, 0.56), scale=0.85, roughness_mult=0.85)
    pal["brick_red"] = make_pbr_mat("WTC_Brick_Red", "castle_brick_02_red", tint=(0.82, 0.44, 0.34), scale=0.85, roughness_mult=0.88)
    pal["sandstone_red"] = make_pbr_mat("WTC_Sandstone_Red", "sandstone_blocks_05", tint=(0.64, 0.38, 0.34), scale=0.68, roughness_mult=0.88)
    pal["asphalt_pbr"] = make_pbr_mat("WTC_Asphalt", "asphalt_02", tint=(0.24, 0.25, 0.27), scale=0.22, roughness_mult=0.85)
    pal["asphalt_patch"] = make_pbr_mat("WTC_Asphalt_Patch", "asphalt_02", tint=(0.16, 0.17, 0.19), scale=0.35, roughness_mult=0.92)
    pal["sidewalk_pbr"] = make_pbr_mat("WTC_Sidewalk", "cobblestone_floor_08", tint=(0.76, 0.77, 0.79), scale=0.42, roughness_mult=0.85)
    pal["roof_membrane"] = make_pbr_mat("WTC_Roof_Membrane", "asphalt_02", tint=(0.82, 0.80, 0.76), scale=0.25, roughness_mult=0.90)
    pal["bronze_dark"] = make_simple_mat("WTC_Bronze_Dark", (0.10, 0.10, 0.11), roughness=0.28, metallic=0.78)
    pal["cast_iron"] = make_simple_mat("WTC_Cast_Iron", (0.20, 0.21, 0.23), roughness=0.42, metallic=0.82)
    pal["tire_rubber"] = make_simple_mat("WTC_Tire_Rubber", (0.05, 0.05, 0.06), roughness=0.78, metallic=0.0)
    pal["metal_white"] = make_simple_mat("WTC_Metal_White", (0.90, 0.92, 0.94), roughness=0.24, metallic=0.65)
    pal["metal_silver"] = make_simple_mat("WTC_Metal_Silver", (0.72, 0.75, 0.78), roughness=0.20, metallic=0.88)
    pal["copper_green"] = make_simple_mat("WTC_Copper_Green", (0.32, 0.56, 0.44), roughness=0.38, metallic=0.45)
    pal["slate_dark"] = make_simple_mat("WTC_Slate_Dark", (0.15, 0.17, 0.20), roughness=0.48, metallic=0.20)
    pal["glass_dark"] = make_simple_mat("WTC_Glass_Dark", (0.05, 0.09, 0.14), roughness=0.03, metallic=0.35, ior=1.52)
    pal["glass_blue"] = make_simple_mat("WTC_Glass_Blue", (0.12, 0.30, 0.46), roughness=0.03, metallic=0.38, ior=1.52)
    pal["glass_green"] = make_simple_mat("WTC_Glass_Green", (0.10, 0.28, 0.26), roughness=0.03, metallic=0.38, ior=1.52)
    pal["glass_warm"] = make_simple_mat("WTC_Glass_Warm", (0.28, 0.22, 0.15), roughness=0.04, metallic=0.25, ior=1.52)
    pal["awning_black"] = make_simple_mat("WTC_Awning_Black", (0.05, 0.05, 0.06), roughness=0.82, metallic=0.0)
    pal["awning_grey"] = make_simple_mat("WTC_Awning_Grey", (0.52, 0.55, 0.58), roughness=0.75, metallic=0.0)
    pal["awning_burgundy"] = make_simple_mat("WTC_Awning_Burgundy", (0.44, 0.06, 0.10), roughness=0.68, metallic=0.0)
    pal["white_paint"] = make_simple_mat("WTC_White_Paint", (0.92, 0.92, 0.92), roughness=0.35, metallic=0.0)
    pal["warm_light"] = make_simple_mat("WTC_Warm_Light", (1.0, 0.88, 0.68), roughness=0.2, emission_strength=4.8)
    pal["red_light"] = make_simple_mat("WTC_Red_Light", (1.0, 0.08, 0.05), roughness=0.15, emission_strength=7.5)
    pal["car_white"] = make_simple_mat("WTC_Car_White", (0.92, 0.93, 0.95), roughness=0.14, metallic=0.35)
    pal["car_dark"] = make_simple_mat("WTC_Car_Dark", (0.10, 0.12, 0.15), roughness=0.15, metallic=0.68)
    pal["car_red"] = make_simple_mat("WTC_Car_Red", (0.68, 0.10, 0.08), roughness=0.16, metallic=0.58)
    pal["car_orange"] = make_simple_mat("WTC_Car_Orange", (0.92, 0.45, 0.08), roughness=0.22, metallic=0.20)
    pal["flag_red"] = make_simple_mat("WTC_Flag_Red", (0.82, 0.08, 0.10), roughness=0.65, metallic=0.0)
    pal["flag_blue"] = make_simple_mat("WTC_Flag_Blue", (0.08, 0.24, 0.68), roughness=0.65, metallic=0.0)
    pal["sign_green"] = make_simple_mat("WTC_Sign_Green", (0.08, 0.36, 0.20), roughness=0.40, metallic=0.10)
    pal["post_pink"] = make_simple_mat("WTC_Post_Pink", (0.78, 0.16, 0.26), roughness=0.45, metallic=0.10)
    pal["foliage_ivy"] = make_simple_mat("WTC_Foliage_Ivy", (0.14, 0.34, 0.12), roughness=0.75, metallic=0.0)
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


def inset_polygon(pts_2d, inset_m=1.4):
    """Shrinks polygon vertices inward along bisector normals by inset_m so inner cores never
    cover recessed windows or ground-floor storefronts."""
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
        # Inward normals for CCW polygon are (-dy, dx)
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


def add_prism(bm, pts_2d, z0, z1, mat_side=0, mat_top=0):
    pts = ensure_ccw(pts_2d)
    if len(pts) < 3:
        return
    v_bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    v_top = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((v_bot[i], v_bot[j], v_top[j], v_top[i]))
        f.material_index = mat_side
    f_top = bm.faces.new(v_top)
    f_top.material_index = mat_top
    f_bot = bm.faces.new(list(reversed(v_bot)))
    f_bot.material_index = mat_side


def add_cylinder(bm, cx, cy, z0, z1, r_bot, r_top=None, segs=16, mat_idx=0):
    if r_top is None:
        r_top = r_bot
    vb, vt = [], []
    for i in range(segs):
        ang = 2.0 * math.pi * i / segs
        ca, sa = math.cos(ang), math.sin(ang)
        vb.append(bm.verts.new((cx + r_bot * ca, cy + r_bot * sa, z0)))
        vt.append(bm.verts.new((cx + r_top * ca, cy + r_top * sa, z1)))
    for i in range(segs):
        j = (i + 1) % segs
        f = bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
        f.material_index = mat_idx
    ft = bm.faces.new(vt)
    ft.material_index = mat_idx
    fb = bm.faces.new(list(reversed(vb)))
    fb.material_index = mat_idx


def add_sloped_awning(bm, wx, wy, z_top, z_bot, width, proj, ux, uy, nx, ny, mat_idx):
    """Builds a smooth wedge-shaped fabric canopy with side cheeks and front valence."""
    hw = width * 0.5
    val_h = 0.22
    # 6 vertices per side: wall-top, wall-bot, front-top, front-bot
    local_pts = [
        (-hw, 0.02, z_top), (-hw, 0.02, z_bot), (-hw, proj, z_bot), (-hw, proj, z_bot - val_h),
        (hw, 0.02, z_top), (hw, 0.02, z_bot), (hw, proj, z_bot), (hw, proj, z_bot - val_h),
    ]
    v = [bm.verts.new((wx + ux * lx + nx * ly, wy + uy * lx + ny * ly, lz)) for lx, ly, lz in local_pts]
    faces = [
        (0, 4, 6, 2),  # Sloped top fabric
        (2, 6, 7, 3),  # Vertical front valence
        (0, 2, 1),     # Left triangular cheek
        (4, 5, 6),     # Right triangular cheek
    ]
    for f_idxs in faces:
        f = bm.faces.new([v[i] for i in f_idxs])
        f.material_index = mat_idx


def add_curved_dome_awning(bm, wx, wy, z_bot, width, height, proj, ux, uy, nx, ny, mat_idx, mat_trim):
    """Builds a smooth curved barrel/dome canopy ('LE ST-JAMES') over an arched window."""
    segs = 10
    hw = width * 0.5
    ang_w = math.atan2(uy, ux)
    for i in range(segs):
        a0 = (math.pi * 0.5) * (i / segs)
        a1 = (math.pi * 0.5) * ((i + 1) / segs)
        y0, z0 = proj * math.cos(a0), z_bot + height * math.sin(a0)
        y1, z1 = proj * math.cos(a1), z_bot + height * math.sin(a1)
        pts = [
            (-hw, 0.02, z0), (hw, 0.02, z0),
            (hw, y0, z0), (-hw, y0, z0),
            (-hw, 0.02, z1), (hw, 0.02, z1),
            (hw, y1, z1), (-hw, y1, z1),
        ]
        verts = [bm.verts.new((wx + ux * lx + nx * ly, wy + uy * lx + ny * ly, lz)) for lx, ly, lz in pts]
        for f_idxs in [(3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]:
            f = bm.faces.new([verts[k] for k in f_idxs])
            f.material_index = mat_idx
    # Front dark/gold valence trim band
    add_box(bm, (wx + nx * (proj * 0.5), wy + ny * (proj * 0.5), z_bot - 0.10),
            (width + 0.04, proj, 0.20), angle_z=ang_w, mat_idx=mat_trim)


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


def build_detailed_facade_wall(bm, p1, p2, z0, z1, bay_w=3.8, floor_h=3.6,
                               mat_wall=0, mat_glass=1, mat_frame=2, mat_sill=0,
                               recess=0.50, has_ground_shop=True, has_awnings=False, mat_awning=3,
                               tripartite=False, arched_windows=False, rusticated_base_h=0.0,
                               has_top_cornice=True):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 1.8:
        add_wall_strip(bm, p1, p2, z0, z1, -0.15, 0.35, mat_idx=mat_wall)
        return
    ux, uy = dx / L, dy / L
    nx, ny = uy, -ux
    ang = math.atan2(uy, ux)

    # Recessed reflective glass backing plane across entire wall (sits at -recess, completely unobstructed!)
    add_wall_strip(bm, p1, p2, z0 + 0.05, z1 - 0.15, -recess, 0.14, mat_idx=mat_glass)

    n_bays = max(1, int(round(L / bay_w)))
    actual_bay = L / n_bays
    pier_w = min(0.92, actual_bay * 0.28)
    win_w = actual_bay - pier_w

    # Vertical piers from z0 to z1 projecting to the street face (+0.08m)
    for i in range(n_bays + 1):
        w = pier_w * (1.25 if (i == 0 or i == n_bays) else 1.0)
        s = max(w * 0.5, min(L - w * 0.5, i * actual_bay))
        px = p1[0] + ux * s + nx * (-recess * 0.5 + 0.04)
        py = p1[1] + uy * s + ny * (-recess * 0.5 + 0.04)
        add_box(bm, (px, py, 0.5 * (z0 + z1)), (w, recess + 0.20, z1 - z0), angle_z=ang, mat_idx=mat_wall)

        # Rusticated stone blocks only on the vertical piers so windows remain 100% open!
        if rusticated_base_h > 0.5:
            zh = min(z1, z0 + rusticated_base_h)
            z_cur = z0 + 0.45
            while z_cur < zh:
                add_box(bm, (p1[0] + ux * s + nx * 0.06, p1[1] + uy * s + ny * 0.06, z_cur),
                        (w + 0.08, 0.18, 0.34), angle_z=ang, mat_idx=mat_sill)
                z_cur += 0.48

    # Horizontal spandrels, sills, mullions, and ground-floor awnings
    n_floors = max(1, int(round((z1 - z0) / floor_h)))
    actual_fh = (z1 - z0) / n_floors
    for fl in range(n_floors):
        fz0 = z0 + fl * actual_fh
        fz1 = fz0 + actual_fh
        spandrel_h = actual_fh * (0.16 if (fl == 0 and has_ground_shop) else 0.30)
        has_sill = (fl > 0 or not has_ground_shop)
        # Spandrel band: omit occluded top cap when sill sits on top to prevent co-planar Z-fighting
        add_wall_strip(bm, p1, p2, fz0, fz0 + spandrel_h, -recess * 0.45, recess + 0.14,
                       mat_idx=mat_wall, cap_top=(not has_sill))
        # Projecting stone sill inset by 0.40m from wall endpoints so adjacent sills do not penetrate corner piers
        if has_sill:
            sill_p1 = (p1[0] + ux * 0.40, p1[1] + uy * 0.40)
            sill_p2 = (p2[0] - ux * 0.40, p2[1] - uy * 0.40)
            add_wall_strip(bm, sill_p1, sill_p2, fz0 + spandrel_h - 0.08, fz0 + spandrel_h + 0.06,
                           0.08, 0.24, mat_idx=mat_sill)

        win_z0 = fz0 + spandrel_h
        win_z1 = fz1 - 0.18
        win_zc = 0.5 * (win_z0 + win_z1)
        win_h = max(0.4, win_z1 - win_z0)

        for b in range(n_bays):
            sc = (b + 0.5) * actual_bay
            wx = p1[0] + ux * sc + nx * (-recess + 0.08)
            wy = p1[1] + uy * sc + ny * (-recess + 0.08)
            # Outer window frame + horizontal transom bar
            add_box(bm, (wx, wy, win_z0 + win_h * 0.60), (win_w, 0.10, 0.08), angle_z=ang, mat_idx=mat_frame)
            if tripartite and win_w > 2.0:
                for off in (-win_w * 0.22, win_w * 0.22):
                    add_box(bm, (wx + ux * off, wy + uy * off, win_zc), (0.09, 0.12, win_h), angle_z=ang, mat_idx=mat_frame)
            else:
                add_box(bm, (wx, wy, win_zc), (0.08, 0.12, win_h), angle_z=ang, mat_idx=mat_frame)

            # Smooth radial stone archivolts over arched windows
            if arched_windows and win_w > 1.4:
                r_a = win_w * 0.46
                for k in range(9):
                    a = math.pi * k / 8.0
                    ax = p1[0] + ux * (sc + math.cos(a) * r_a) + nx * 0.06
                    ay = p1[1] + uy * (sc + math.cos(a) * r_a) + ny * 0.06
                    az = win_z1 - 0.25 + math.sin(a) * (r_a * 0.55)
                    add_box(bm, (ax, ay, az), (0.34, 0.26, 0.32), angle_z=ang, mat_idx=mat_sill)

            # Smooth wedge-shaped storefront awning on ground floor
            if fl == 0 and has_awnings:
                add_sloped_awning(bm, p1[0] + ux * sc, p1[1] + uy * sc,
                                  win_z1 + 0.12, win_z1 - 0.72, win_w * 0.90, 1.15,
                                  ux, uy, nx, ny, mat_awning)

    # Top entablature / cornice: architrave without top cap + cornice top at z1 + 0.16m
    if has_top_cornice:
        add_wall_strip(bm, p1, p2, z1 - 0.55, z1, 0.16, 0.42, mat_idx=mat_sill, cap_top=False)
        add_wall_strip(bm, p1, p2, z1 - 0.22, z1 + 0.16, 0.38, 0.78, mat_idx=mat_frame)


def build_royal_bank_tower(col, coords_xy, pal):
    """360 Rue Saint-Jacques — Banque Royale du Canada (38911498):
    35m rusticated limestone podium + giant arched portal + 12-column Corinthian loggia +
    112m stepped limestone tower positioned right behind the Rue Saint-Jacques colonnade."""
    bm = bmesh.new()
    mats = [
        pal["limestone_cream"], pal["limestone_gold"], pal["glass_dark"],
        pal["bronze_dark"], pal["granite_dark"], pal["copper_green"]
    ]

    pts = ensure_ccw(coords_xy)
    core_pts = inset_polygon(pts, 1.4)
    add_prism(bm, core_pts, 0.0, 34.8 - 0.28, mat_side=0, mat_top=0)
    add_prism(bm, pts, 0.0, 1.8, mat_side=4, mat_top=4)

    # NW facade along Rue Saint-Jacques: (-231.93, -285.52) -> (-206.65, -236.38)
    p_sw = (-231.93, -285.52)
    p_ne = (-206.65, -236.38)
    dx, dy = p_ne[0] - p_sw[0], p_ne[1] - p_sw[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    ang = math.atan2(uy, ux)

    # Rusticated limestone wall face with horizontal coursing channels (z = 1.8..22.5m)
    for zi in range(28):
        z_band = 1.8 + zi * 0.74
        mx = 0.5 * (p_sw[0] + p_ne[0]) + nx * 0.12
        my = 0.5 * (p_sw[1] + p_ne[1]) + ny * 0.12
        add_box(bm, (mx, my, z_band + 0.30), (L, 0.28, 0.62), angle_z=ang, mat_idx=0, cap_top=False, cap_bottom=False)

    # Giant recessed round-arched entrance portal + flanking arched windows
    for idx_p, t_pos in enumerate([0.22, 0.50, 0.78]):
        is_main = (idx_p == 1)
        pw = 6.8 if is_main else 4.2
        ph = 14.5 if is_main else 10.5
        px = p_sw[0] + ux * (L * t_pos)
        py = p_sw[1] + uy * (L * t_pos)
        add_box(bm, (px + nx * 0.04, py + ny * 0.04, ph * 0.5), (pw, 0.55, ph), angle_z=ang, mat_idx=2)
        for side in (-1, 1):
            jx = px + ux * (side * pw * 0.52) + nx * 0.24
            jy = py + uy * (side * pw * 0.52) + ny * 0.24
            add_box(bm, (jx, jy, (ph - pw * 0.4) * 0.5), (0.95, 0.55, ph - pw * 0.4), angle_z=ang, mat_idx=1)
        r_arch = pw * 0.52
        zc_arch = ph - pw * 0.45
        for k in range(11):
            a = math.pi * k / 10.0
            ax = px + ux * (math.cos(a) * r_arch) + nx * 0.26
            ay = py + uy * (math.cos(a) * r_arch) + ny * 0.26
            az = zc_arch + math.sin(a) * r_arch
            add_box(bm, (ax, ay, az), (0.85, 0.58, 0.85), angle_z=ang, mat_idx=1)

    # Upper Corinthian colonnade loggia along NW facade (z = 22.8..32.5m)
    mx_log = 0.5 * (p_sw[0] + p_ne[0]) - nx * 0.35
    my_log = 0.5 * (p_sw[1] + p_ne[1]) - ny * 0.35
    add_box(bm, (mx_log, my_log, 27.6), (L * 0.88, 0.40, 9.6), angle_z=ang, mat_idx=2)
    for ci in range(12):
        t = 0.07 + 0.86 * (ci / 11.0)
        col_x = p_sw[0] + ux * (L * t) + nx * 0.22
        col_y = p_sw[1] + uy * (L * t) + ny * 0.22
        add_cylinder(bm, col_x, col_y, 22.8, 32.2, 0.58, 0.52, segs=14, mat_idx=1)
        add_box(bm, (col_x, col_y, 32.4), (1.35, 1.35, 0.55), angle_z=ang, mat_idx=1)
        add_box(bm, (col_x, col_y, 22.6), (1.35, 1.35, 0.50), angle_z=ang, mat_idx=1)

    # Podium classical entablature & dentil cornice (z = 32.5..35.2m)
    mx_c = 0.5 * (p_sw[0] + p_ne[0]) + nx * 0.45
    my_c = 0.5 * (p_sw[1] + p_ne[1]) + ny * 0.45
    add_box(bm, (mx_c, my_c, 33.8), (L + 1.2, 1.3, 2.4), angle_z=ang, mat_idx=1, cap_top=False)

    # NE facade along Rue Saint-Pierre: (-162.33, -267.40) -> (-206.65, -236.38)
    build_detailed_facade_wall(bm, (-162.33, -267.40), (-206.65, -236.38), 1.8, 34.8,
                               bay_w=4.4, floor_h=4.2, mat_wall=0, mat_glass=2, mat_frame=3,
                               mat_sill=1, rusticated_base_h=20.0)

    # Stepped Setback Skyscraper Tower (z = 35.0..112.0m) positioned 4.8m behind the NW colonnade
    # so it rises prominently above the colonnade in Rue_SaintJacques_South_Facades & Corner_Rue_SaintPierre
    tw_cx = 0.5 * (p_sw[0] + p_ne[0]) - nx * 16.5
    tw_cy = 0.5 * (p_sw[1] + p_ne[1]) - ny * 16.5
    tw_w, tw_d = 38.0, 26.0
    add_box(bm, (tw_cx, tw_cy, 65.5), (tw_w - 2.2, tw_d - 2.2, 61.0), angle_z=ang, mat_idx=2, cap_bottom=False)
    for side_ang, w_span, d_off in [
        (ang, tw_w, tw_d * 0.5),
        (ang + math.pi, tw_w, tw_d * 0.5),
        (ang + math.pi * 0.5, tw_d, tw_w * 0.5),
        (ang - math.pi * 0.5, tw_d, tw_w * 0.5),
    ]:
        s_ux, s_uy = math.cos(side_ang), math.sin(side_ang)
        s_nx, s_ny = -s_uy, s_ux
        p_a = (tw_cx - s_ux * (w_span * 0.5) + s_nx * d_off, tw_cy - s_uy * (w_span * 0.5) + s_ny * d_off)
        p_b = (tw_cx + s_ux * (w_span * 0.5) + s_nx * d_off, tw_cy + s_uy * (w_span * 0.5) + s_ny * d_off)
        build_detailed_facade_wall(bm, p_b, p_a, 35.2, 96.0, bay_w=3.4, floor_h=3.6,
                                   mat_wall=0, mat_glass=2, mat_frame=3, mat_sill=1,
                                   recess=0.45, has_ground_shop=False)
    add_box(bm, (tw_cx, tw_cy, 101.5), (27.0, 20.0, 11.0), angle_z=ang, mat_idx=1)
    add_box(bm, (tw_cx, tw_cy, 109.5), (19.0, 15.0, 5.0), angle_z=ang, mat_idx=5)

    mesh = bpy.data.meshes.new("Bldg_38911498_RoyalBank")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_38911498_RoyalBank", mesh)
    link_obj(obj, col)


def build_greenshields_and_wtc_north(col_owned, col_proxy, b_green, b_380, pal):
    """Builds Édifice Greenshields (104674804, Proxy, 8 stories = 27.8m) and 380 Rue Saint-Antoine Ouest
    (104674805, Owned, 8 stories = 27.8m) featured on the right side of Square_Victoria_West_Entrance.jpg."""
    mats = [
        pal["limestone_cream"], pal["limestone_gold"], pal["glass_dark"],
        pal["bronze_dark"], pal["granite_dark"], pal["warm_light"], pal["roof_membrane"]
    ]

    for b, target_col, h_top in [(b_green, col_proxy, 27.8), (b_380, col_owned, 27.8)]:
        if not b:
            continue
        bm = bmesh.new()
        pts = ensure_ccw(b["coords_xy"])
        core_pts = inset_polygon(pts, 1.4)
        add_prism(bm, core_pts, 0.0, h_top - 0.85, mat_side=2, mat_top=6)
        add_prism(bm, pts, 0.0, 1.3, mat_side=4, mat_top=4)

        n = len(pts)
        for i in range(n):
            p1, p2 = pts[i], pts[(i + 1) % n]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            L = math.hypot(dx, dy)
            mx, my = 0.5 * (p1[0] + p2[0]), 0.5 * (p1[1] + p2[1])
            if L < 5.0 or (-310.0 < mx < -288.0 and -228.0 < my < -212.0):
                add_wall_strip(bm, p1, p2, 0.0, h_top, -0.1, 0.35, mat_idx=0)
                continue

            build_detailed_facade_wall(bm, p1, p2, 1.2, h_top - 0.9, bay_w=5.0, floor_h=3.3,
                                       mat_wall=0, mat_glass=2, mat_frame=3, mat_sill=1,
                                       recess=0.52, has_ground_shop=False, tripartite=True,
                                       rusticated_base_h=6.8)
            # Moulded limestone belt courses at z=3.4m, z=7.5m, and z=23.6m
            add_wall_strip(bm, p1, p2, 3.25, 3.60, 0.22, 0.55, mat_idx=1)
            add_wall_strip(bm, p1, p2, 7.35, 7.80, 0.28, 0.65, mat_idx=1)
            add_wall_strip(bm, p1, p2, h_top - 4.2, h_top - 3.8, 0.26, 0.60, mat_idx=1)

            # Deeply overhanging dark-bronze bracketed classical roof cornice at z = 26.9..28.0m
            add_wall_strip(bm, p1, p2, h_top - 0.90, h_top + 0.18, 0.72, 1.65, mat_idx=3)
            ux, uy = dx / L, dy / L
            nx, ny = uy, -ux
            ang = math.atan2(uy, ux)
            n_brackets = int(L / 0.95)
            for k in range(n_brackets):
                s = (k + 0.5) * (L / max(1, n_brackets))
                bx = p1[0] + ux * s + nx * 0.62
                by = p1[1] + uy * s + ny * 0.62
                add_box(bm, (bx, by, h_top - 1.12), (0.24, 1.15, 0.48), angle_z=ang, mat_idx=3)

            # Prominent 2nd-floor semicircular arched window bay directly above the white van in Square_Victoria_West_Entrance.jpg
            if nx < -0.3 and ny > 0.3 and L > 14.0:
                for sc_frac in (0.32, 0.68):
                    sc = L * sc_frac
                    ax = p1[0] + ux * sc + nx * 0.18
                    ay = p1[1] + uy * sc + ny * 0.18
                    for k in range(11):
                        a = math.pi * k / 10.0
                        rx = ax + ux * (math.cos(a) * 2.15)
                        ry = ay + uy * (math.cos(a) * 2.15)
                        rz = 5.6 + math.sin(a) * 1.45
                        add_box(bm, (rx, ry, rz), (0.52, 0.48, 0.46), angle_z=ang, mat_idx=1)

        mesh = bpy.data.meshes.new(f"Bldg_{b['id']}_BeauxArts")
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(f"Bldg_{b['id']}_BeauxArts", mesh)
        link_obj(obj, target_col)


def build_hotel_intercontinental(col_owned, b_hotel, b_tower_ne, pal):
    """Builds Hôtel InterContinental (104674799) with full recessed glass window grid, open ground-floor
    glass lobby doors beneath the marquee, 4 draped flags on angled poles, mid-block chamfered tower with
    sloped mansard crown (visible in Square_Victoria_West_Entrance), and modern NE green-glass wing."""
    bm = bmesh.new()
    # 0: brick_rose, 1: granite_dark, 2: glass_dark, 3: bronze_dark, 4: limestone_cream,
    # 5: slate_dark, 6: white_paint, 7: warm_light, 8: flag_red, 9: flag_blue, 10: glass_green, 11: roof_membrane
    mats = [
        pal["brick_rose"], pal["granite_dark"], pal["glass_dark"], pal["bronze_dark"],
        pal["limestone_cream"], pal["slate_dark"], pal["white_paint"], pal["warm_light"],
        pal["flag_red"], pal["flag_blue"], pal["glass_green"], pal["roof_membrane"]
    ]

    pts = ensure_ccw(b_hotel["coords_xy"])
    # Inset inner core by 1.8m with dark reflective glass so zero outer walls block the recessed windows!
    core_pts = inset_polygon(pts, 1.8)
    add_prism(bm, core_pts, 0.0, 39.2, mat_side=2, mat_top=11)

    # Perimeter walls of 104674799 with full recessed 3-part window grids on every segment
    n = len(pts)
    for i in range(n):
        p_a, p_b = pts[i], pts[(i + 1) % n]
        seg_L = math.hypot(p_b[0] - p_a[0], p_b[1] - p_a[1])
        mx = 0.5 * (p_a[0] + p_b[0])
        my = 0.5 * (p_a[1] + p_b[1])
        if seg_L < 4.5 or (-310.0 < mx < -288.0 and -228.0 < my < -212.0):
            add_wall_strip(bm, p_a, p_b, 0.0, 39.5, -0.15, 0.45, mat_idx=0)
        else:
            build_detailed_facade_wall(bm, p_a, p_b, 0.0, 39.5, bay_w=5.2, floor_h=3.6,
                                       mat_wall=0, mat_glass=2, mat_frame=3, mat_sill=4,
                                       recess=0.58, has_ground_shop=True, tripartite=True)

    # Hero NW Entrance Facade along Rue Saint-Antoine: (-306.43, -214.47) -> (-292.79, -188.03)
    p1 = (-306.43, -214.47)
    p2 = (-292.79, -188.03)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    # Outward normal pointing NW toward Rue Saint-Antoine: (-uy, ux)
    nx, ny = -uy, ux
    ang = math.atan2(uy, ux)

    # Extra-crisp spandrel panels, triple-grooved stone lintels, and ground-floor granite portal piers on NW face
    n_bays = 6
    bay_w = L / n_bays
    for bi in range(n_bays + 1):
        s = bi * bay_w
        px = p1[0] + ux * s + nx * 0.08
        py = p1[1] + uy * s + ny * 0.08
        # Ground-floor dark polished granite pier (z = 0..4.2m)
        add_box(bm, (px, py, 2.1), (1.15, 0.68, 4.2), angle_z=ang, mat_idx=1)

    for bi in range(n_bays):
        sc = (bi + 0.5) * bay_w
        wx = p1[0] + ux * sc
        wy = p1[1] + uy * sc
        # Ground-floor recessed glass entrance doors with warm interior lobby glow strip
        add_box(bm, (wx - nx * 0.42, wy - ny * 0.42, 2.0), (bay_w - 1.1, 0.14, 3.8), angle_z=ang, mat_idx=2)
        add_box(bm, (wx - nx * 0.25, wy - ny * 0.25, 2.0), (0.10, 0.22, 3.8), angle_z=ang, mat_idx=3)
        add_box(bm, (wx - nx * 0.85, wy - ny * 0.85, 3.45), (bay_w - 1.4, 0.25, 0.22), angle_z=ang, mat_idx=7)
        for fl in range(1, 11):
            fz = 3.8 + (fl - 1) * 3.55
            # Dark charcoal metallic spandrel panel below window
            add_box(bm, (wx - nx * 0.12, wy - ny * 0.12, fz + 0.52), (bay_w - 1.05, 0.26, 0.98), angle_z=ang, mat_idx=3)
            # Grooved stone lintel above window
            add_box(bm, (wx + nx * 0.12, wy + ny * 0.12, fz + 3.38), (bay_w - 0.95, 0.36, 0.32), angle_z=ang, mat_idx=4)

    # Grand projecting black entrance marquee canopy: "HÔTEL INTERCONTINENTAL"
    can_s = L * 0.48
    can_l = 15.2
    can_w = 2.95
    can_x = p1[0] + ux * can_s + nx * (can_w * 0.5)
    can_y = p1[1] + uy * can_s + ny * (can_w * 0.5)
    add_box(bm, (can_x, can_y, 4.38), (can_l, can_w, 0.92), angle_z=ang, mat_idx=3)
    # Recessed warm soffit downlight panels under canopy
    for li in range(8):
        ls = -can_l * 0.42 + (li / 7.0) * (can_l * 0.84)
        lx = p1[0] + ux * (can_s + ls) + nx * (can_w * 0.52)
        ly = p1[1] + uy * (can_s + ls) + ny * (can_w * 0.52)
        add_box(bm, (lx, ly, 3.90), (1.15, 1.85, 0.06), angle_z=ang, mat_idx=7)

    # 3D white lettering "HÔTEL INTERCONTINENTAL" on front AND side fascia of marquee
    for li in range(20):
        ls = -can_l * 0.40 + (li / 19.0) * (can_l * 0.80)
        lx = p1[0] + ux * (can_s + ls) + nx * (can_w + 0.03)
        ly = p1[1] + uy * (can_s + ls) + ny * (can_w + 0.03)
        add_box(bm, (lx, ly, 4.35), (0.22, 0.06, 0.36), angle_z=ang, mat_idx=6)
    for si in range(9):
        sn = 0.45 + (si / 8.0) * (can_w - 0.90)
        sx_f = p1[0] + ux * (can_s - can_l * 0.5 - 0.03) + nx * sn
        sy_f = p1[1] + uy * (can_s - can_l * 0.5 - 0.03) + ny * sn
        add_box(bm, (sx_f, sy_f, 4.35), (0.06, 0.16, 0.30), angle_z=ang, mat_idx=6)

    # 4 Angled Flagpoles with Multi-Segment Draped Fabric Flags (Canada, Montreal, Quebec)
    for fi, (f_mat1, f_mat2) in enumerate([(8, 6), (3, 6), (6, 8), (9, 6)]):
        fs = can_s - 3.9 + fi * 2.6
        fx_base = p1[0] + ux * fs + nx * 0.25
        fy_base = p1[1] + uy * fs + ny * 0.25
        # Diagonal V-strut bracket + angled flagpole
        for seg in range(10):
            t = seg / 9.0
            px_s = fx_base + nx * (t * 2.45)
            py_s = fy_base + ny * (t * 2.45)
            pz_s = 4.88 + t * 3.25
            add_box(bm, (px_s, py_s, pz_s), (0.05, 0.38, 0.05), angle_z=ang, mat_idx=3)
        # Tapered wavy draped cloth flag hanging from upper half of pole
        for wseg in range(5):
            wt = wseg / 4.0
            fl_x = fx_base + nx * (1.25 + wt * 0.95) + ux * (math.sin(wt * math.pi) * 0.16)
            fl_y = fy_base + ny * (1.25 + wt * 0.95) + uy * (math.sin(wt * math.pi) * 0.16)
            fl_z = 5.65 + wt * 0.85 - (1.0 - wt) * 0.35
            m_use = f_mat2 if (wseg in (1, 2)) else f_mat1
            add_box(bm, (fl_x, fl_y, fl_z), (0.06, 0.26, 1.15 - wt * 0.35), angle_z=ang + 0.18 * math.cos(wt * 3.0), mat_idx=m_use)

    # 4 Tall White Conical/Teardrop Fiberglass Bollards under/around the canopy on the sidewalk
    for bo_s, bo_n in [(can_s - 6.8, 2.55), (can_s - 2.6, 0.85), (can_s + 2.4, 2.55), (can_s + 6.8, 0.85)]:
        bx_c = p1[0] + ux * bo_s + nx * bo_n
        by_c = p1[1] + uy * bo_s + ny * bo_n
        add_cylinder(bm, bx_c, by_c, 0.15, 2.05, 0.34, 0.06, segs=16, mat_idx=6)

    # Chamfered Postmodern Tower & Steep Mansard Turret Crown rising mid-block (-308.5, -220.5)
    # Visible rising behind the red-brick wing in Square_Victoria_West_Entrance.jpg AND in overview!
    for tcx, tcy, tz0, tz1, tr in [(-306.5, -219.5, 27.5, 68.0, 10.5), (-282.5, -206.5, 38.0, 82.0, 14.5)]:
        add_cylinder(bm, tcx, tcy, tz0, tz1, tr, tr, segs=8, mat_idx=4 if tr < 12 else 0)
        for oi in range(8):
            o_ang = 2.0 * math.pi * oi / 8.0 + math.pi / 8.0
            ox = tcx + math.cos(o_ang) * (tr - 0.85)
            oy = tcy + math.sin(o_ang) * (tr - 0.85)
            add_box(bm, (ox, oy, 0.5 * (tz0 + tz1)), (tr * 0.42, 0.45, tz1 - tz0 - 3.0), angle_z=o_ang + math.pi * 0.5, mat_idx=2)
            for z_f in range(int(tz0) + 3, int(tz1) - 2, 3):
                add_box(bm, (ox, oy, float(z_f)), (tr * 0.44, 0.55, 0.45), angle_z=o_ang + math.pi * 0.5, mat_idx=4)
        # Steeply pitched dark-slate mansard roof & pinnacle crown
        add_cylinder(bm, tcx, tcy, tz1, tz1 + 9.5, tr + 0.3, tr * 0.42, segs=8, mat_idx=5)

    # Corner cylindrical brick turret at (-287.1, -185.8)
    add_cylinder(bm, -287.1, -185.8, 0.0, 44.0, 5.2, 5.2, segs=12, mat_idx=0)
    add_cylinder(bm, -287.1, -185.8, 44.0, 50.5, 5.4, 0.4, segs=12, mat_idx=5)

    # Modern 21-story Green-Glass & Precast Office/Hotel Wing immediately NE along Rue Saint-Antoine
    p_tw1 = (-291.0, -184.8)
    p_tw2 = (-271.5, -152.5)
    tdx, tdy = p_tw2[0] - p_tw1[0], p_tw2[1] - p_tw1[1]
    tL = math.hypot(tdx, tdy)
    tux, tuy = tdx / tL, tdy / tL
    tnx, tny = -tuy, tux
    tang = math.atan2(tuy, tux)

    tw_cx = 0.5 * (p_tw1[0] + p_tw2[0]) - tnx * 13.0
    tw_cy = 0.5 * (p_tw1[1] + p_tw2[1]) - tny * 13.0
    add_box(bm, (tw_cx, tw_cy, 34.0), (tL, 26.0, 68.0), angle_z=tang, mat_idx=4)
    for ci in range(9):
        cs = (ci / 8.0) * tL
        cx_p = p_tw1[0] + tux * cs
        cy_p = p_tw1[1] + tuy * cs
        add_box(bm, (cx_p, cy_p, 4.5), (1.1, 1.2, 9.0), angle_z=tang, mat_idx=4)
    add_box(bm, (0.5 * (p_tw1[0] + p_tw2[0]), 0.5 * (p_tw1[1] + p_tw2[1]), 37.2), (tL - 2.4, 0.55, 56.5), angle_z=tang, mat_idx=10)
    sw_cx = p_tw1[0] - tnx * 13.0
    sw_cy = p_tw1[1] - tny * 13.0
    add_box(bm, (sw_cx, sw_cy, 37.2), (0.55, 23.5, 56.5), angle_z=tang, mat_idx=10)
    for fl_z in range(10, 66, 3):
        add_box(bm, (0.5 * (p_tw1[0] + p_tw2[0]), 0.5 * (p_tw1[1] + p_tw2[1]), float(fl_z)), (tL - 2.0, 0.72, 0.45), angle_z=tang, mat_idx=3)
        add_box(bm, (sw_cx, sw_cy, float(fl_z)), (0.72, 23.8, 0.45), angle_z=tang, mat_idx=3)
    add_box(bm, (tw_cx, tw_cy, 66.8), (tL + 0.8, 26.8, 2.6), angle_z=tang, mat_idx=4)

    mesh = bpy.data.meshes.new("Bldg_104674799_InterContinental")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_104674799_InterContinental", mesh)
    link_obj(obj, col_owned)


def build_wtc_atrium_and_south_wings(col_owned, buildings_by_id, pal):
    """Builds the World Trade Centre Montreal central glass skylight atrium (104674803),
    the Rue Saint-Jacques south limestone wing (104674810), the Victorian Nordheimer &
    Canada Life / Le St-James buildings (104674798, 104674802, 340058291), and copper-mansard
    SW wings (104674800, 104674801)."""
    bm = bmesh.new()
    # 0: limestone_grey, 1: limestone_gold, 2: sandstone_red, 3: glass_dark,
    # 4: glass_blue, 5: metal_white, 6: bronze_dark, 7: copper_green,
    # 8: awning_grey, 9: awning_burgundy, 10: granite_rose, 11: granite_dark,
    # 12: roof_membrane, 13: foliage_ivy
    mats = [
        pal["limestone_grey"], pal["limestone_gold"], pal["sandstone_red"], pal["glass_dark"],
        pal["glass_blue"], pal["metal_white"], pal["bronze_dark"], pal["copper_green"],
        pal["awning_grey"], pal["awning_burgundy"], pal["granite_rose"], pal["granite_dark"],
        pal["roof_membrane"], pal["foliage_ivy"]
    ]

    # 1. Central Atrium Spine (104674803) + Translucent Reflective Blue-Glass Galleria Skylight
    b_atr = buildings_by_id.get(104674803)
    if b_atr:
        add_prism(bm, b_atr["coords_xy"], 0.0, 23.5 - 0.45, mat_side=0, mat_top=12)
        p_s = (-328.0, -336.0)
        p_e = (-253.0, -205.0)
        dx, dy = p_e[0] - p_s[0], p_e[1] - p_s[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux
        ang = math.atan2(uy, ux)
        mcx, mcy = 0.5 * (p_s[0] + p_e[0]), 0.5 * (p_s[1] + p_e[1])
        # Gabled reflective blue-glass skylight gallery (no wide opaque white strip!)
        add_box(bm, (mcx, mcy, 24.8), (L, 12.2, 2.6), angle_z=ang, mat_idx=4)
        add_box(bm, (mcx, mcy, 26.5), (L, 7.6, 1.4), angle_z=ang, mat_idx=4)
        add_box(bm, (mcx, mcy, 27.3), (L, 0.30, 0.35), angle_z=ang, mat_idx=6)
        n_ribs = int(L / 2.2)
        for ri in range(n_ribs + 1):
            rs = ri * 2.2
            rx = p_s[0] + ux * rs
            ry = p_s[1] + uy * rs
            add_box(bm, (rx, ry, 25.3), (0.16, 12.6, 3.6), angle_z=ang, mat_idx=6)
            add_box(bm, (rx, ry, 26.7), (0.18, 8.0, 1.6), angle_z=ang, mat_idx=5)

        # Secondary parallel gabled skylight on SW roof + two transverse cross-skylight wings
        sw_sk_x = p_s[0] + ux * 28.0 + nx * 12.5
        sw_sk_y = p_s[1] + uy * 28.0 + ny * 12.5
        add_box(bm, (sw_sk_x, sw_sk_y, 24.6), (38.0, 7.2, 2.2), angle_z=ang, mat_idx=4)
        for sri in range(17):
            off = -17.6 + sri * 2.2
            add_box(bm, (sw_sk_x + ux * off, sw_sk_y + uy * off, 24.8), (0.15, 7.5, 2.5), angle_z=ang, mat_idx=6)

        for c_t in (0.45, 0.78):
            ccx = p_s[0] + ux * (L * c_t) + nx * 10.5
            ccy = p_s[1] + uy * (L * c_t) + ny * 10.5
            add_box(bm, (ccx, ccy, 25.0), (10.2, 22.5, 2.6), angle_z=ang, mat_idx=4)
            for cri in range(10):
                off = -10.8 + cri * 2.4
                add_box(bm, (ccx + nx * off, ccy + ny * off, 25.3), (10.5, 0.18, 3.0), angle_z=ang, mat_idx=6)

        # 4-Fan White Rooftop Cooling Tower Bank on west roof (-321.5, -267.5)
        hvac_x, hvac_y = -321.5, -267.5
        add_box(bm, (hvac_x, hvac_y, 29.6), (22.0, 7.5, 3.6), angle_z=ang, mat_idx=5)
        for fi in range(4):
            foff = -7.8 + fi * 5.2
            fx = hvac_x + ux * foff
            fy = hvac_y + uy * foff
            add_cylinder(bm, fx, fy, 31.3, 31.9, 2.1, 2.1, segs=16, mat_idx=6)
            add_cylinder(bm, fx, fy, 31.4, 32.0, 1.7, 1.7, segs=16, mat_idx=3)

    # 2. SW Wings (104674800 & 104674801) with Pitched Green-Copper Mansard Band + Flat Membrane Roof
    for cid, ch in [(104674800, 31.0), (104674801, 29.0)]:
        b_c = buildings_by_id.get(cid)
        if not b_c:
            continue
        pts = ensure_ccw(b_c["coords_xy"])
        core_pts = inset_polygon(pts, 1.4)
        add_prism(bm, core_pts, 0.0, ch - 2.2 - 0.28, mat_side=3, mat_top=12)
        # Outer green-copper mansard band (z = ch-2.2 .. ch) + inner flat membrane roof
        inner_roof = inset_polygon(pts, 5.2)
        add_prism(bm, pts, ch - 2.2, ch, mat_side=7, mat_top=7)
        add_prism(bm, inner_roof, ch - 2.1, ch + 0.35, mat_side=0, mat_top=12)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 6.0:
                build_detailed_facade_wall(bm, p1, p2, 0.0, ch - 2.2, bay_w=4.4, floor_h=3.6,
                                           mat_wall=0, mat_glass=3, mat_frame=6, mat_sill=0,
                                           recess=0.50, has_ground_shop=True, has_top_cornice=False)

    # 3. Rue Saint-Jacques Postmodern Grey Limestone South Facade (104674810)
    # Featured on the left side of Rue_SaintJacques_South_Facades.jpg
    b_810 = buildings_by_id.get(104674810)
    if b_810:
        pts = ensure_ccw(b_810["coords_xy"])
        core_pts = inset_polygon(pts, 1.5)
        add_prism(bm, core_pts, 0.0, 27.5 - 1.10, mat_side=3, mat_top=12)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            L_seg = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if L_seg >= 6.0:
                build_detailed_facade_wall(bm, p1, p2, 0.0, 27.5, bay_w=4.4, floor_h=3.8,
                                           mat_wall=0, mat_glass=3, mat_frame=6, mat_sill=0,
                                           recess=0.55, has_ground_shop=True, has_awnings=True,
                                           mat_awning=8, tripartite=True)
            else:
                add_wall_strip(bm, p1, p2, 0.0, 27.5, -0.1, 0.35, mat_idx=0)

    # 4. Nordheimer & Victorian Facades (104674798) along Rue Saint-Jacques
    b_798 = buildings_by_id.get(104674798)
    if b_798:
        pts = ensure_ccw(b_798["coords_xy"])
        core_pts = inset_polygon(pts, 1.5)
        add_prism(bm, core_pts, 0.0, 29.5 - 0.45, mat_side=3, mat_top=12)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 6.0:
                build_detailed_facade_wall(bm, p1, p2, 0.0, 29.5, bay_w=3.6, floor_h=3.8,
                                           mat_wall=2, mat_glass=3, mat_frame=6, mat_sill=1,
                                           recess=0.55, has_ground_shop=True, arched_windows=True)
            else:
                add_wall_strip(bm, p1, p2, 0.0, 29.5, -0.1, 0.35, mat_idx=2)

    # 5. Le St-James Hotel / Canada Life / Nordheimer Corner (104674802 & 340058291)
    # Featured in the right foreground of Corner_Rue_SaintPierre.jpg!
    for cid, ch in [(104674802, 31.5), (340058291, 31.5)]:
        b_v = buildings_by_id.get(cid)
        if not b_v:
            continue
        pts = ensure_ccw(b_v["coords_xy"])
        # Inset core by 1.6m with dark reflective glass so every window bay shows glass!
        core_pts = inset_polygon(pts, 1.6)
        add_prism(bm, core_pts, 0.0, ch - 0.45, mat_side=3, mat_top=12)
        add_prism(bm, pts, 0.0, 1.25, mat_side=11, mat_top=11)
        n = len(pts)
        for i in range(n):
            p1, p2 = pts[i], pts[(i + 1) % n]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 5.5:
                build_detailed_facade_wall(bm, p1, p2, 1.15, ch, bay_w=3.8, floor_h=4.1,
                                           mat_wall=1, mat_glass=3, mat_frame=6, mat_sill=1,
                                           recess=0.58, has_ground_shop=False, arched_windows=True,
                                           rusticated_base_h=5.8, has_top_cornice=False)
                add_wall_strip(bm, p1, p2, 6.2, 6.75, 0.32, 0.75, mat_idx=1)
                add_wall_strip(bm, p1, p2, 10.6, 11.05, 0.24, 0.55, mat_idx=1)
                add_wall_strip(bm, p1, p2, ch - 0.65, ch + 0.12, 0.48, 0.98, mat_idx=7)
            else:
                add_wall_strip(bm, p1, p2, 1.15, ch, -0.1, 0.35, mat_idx=1)

    # Specific Le St-James corner details on 104674802:
    # SE wall (-230.45, -241.84) -> (-222.45, -226.53)
    p_c1 = (-230.45, -241.84)
    p_c2 = (-222.45, -226.53)
    dx, dy = p_c2[0] - p_c1[0], p_c2[1] - p_c1[1]
    L_c = math.hypot(dx, dy)
    ux, uy = dx / L_c, dy / L_c
    nx, ny = uy, -ux
    ang_c = math.atan2(uy, ux)

    # 2 Smooth Curved Burgundy Dome Canopies ("LE ST-JAMES") over the ground-floor arched windows
    for s_can in (L_c * 0.61, L_c * 0.83):
        cx_a = p_c1[0] + ux * s_can
        cy_a = p_c1[1] + uy * s_can
        add_curved_dome_awning(bm, cx_a, cy_a, 3.85, 2.25, 0.95, 1.25, ux, uy, nx, ny, 9, 6)

    # Polished rose-granite cylindrical entrance columns at (-226.8, -233.5)
    for col_s in (L_c * 0.35, L_c * 0.49):
        gx = p_c1[0] + ux * col_s + nx * 0.36
        gy = p_c1[1] + uy * col_s + ny * 0.36
        add_cylinder(bm, gx, gy, 1.25, 6.1, 0.32, 0.28, segs=14, mat_idx=10)
        add_cylinder(bm, gx, gy, 6.75, 11.2, 0.28, 0.25, segs=14, mat_idx=10)

    # Ornate Black Wrought-Iron Sidewalk Railing (with top/bottom rails, dense pickets & green ivy)
    rail_len = L_c * 0.48
    rail_sc = L_c * 0.76
    rx_mid = p_c1[0] + ux * rail_sc + nx * 1.12
    ry_mid = p_c1[1] + uy * rail_sc + ny * 1.12
    for z_r in (0.22, 1.08, 1.18):
        add_box(bm, (rx_mid, ry_mid, z_r), (rail_len, 0.06, 0.05), angle_z=ang_c, mat_idx=6)
    n_pickets = 26
    for ri in range(n_pickets + 1):
        rs = L_c * 0.52 + (ri / n_pickets) * rail_len
        rx = p_c1[0] + ux * rs + nx * 1.12
        ry = p_c1[1] + uy * rs + ny * 1.12
        is_post = (ri in (0, 13, n_pickets))
        pw = 0.09 if is_post else 0.035
        ph = 1.18 if is_post else 0.96
        add_box(bm, (rx, ry, 0.15 + ph * 0.5), (pw, pw, ph), angle_z=ang_c, mat_idx=6)
    # Climbing green ivy clusters along the wrought-iron railing & rusticated stonework
    for iv_i in range(7):
        ivs = L_c * 0.56 + iv_i * 0.95
        ivx = p_c1[0] + ux * ivs + nx * 0.95
        ivy_y = p_c1[1] + uy * ivs + ny * 0.95
        add_box(bm, (ivx, ivy_y, 0.85 + (iv_i % 3) * 0.35), (0.65, 0.32, 0.75), angle_z=ang_c + iv_i * 0.3, mat_idx=13)

    mesh = bpy.data.meshes.new("Bldg_WTC_Atrium_And_South")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_WTC_Atrium_And_South", mesh)
    link_obj(obj, col_owned)


def build_sesame_victorian_building(col_owned, b_117, b_116, pal):
    """Builds the ornate 4-story Victorian Beaux-Arts limestone building (339911117 & 339911116)
    with recessed dark-glass restaurant windows, 3 distinct wedge-shaped black 'SESAME' fabric awnings,
    and arched upper glass windows in the right foreground of Rue_SaintJacques_South_Facades.jpg."""
    bm = bmesh.new()
    # 0: limestone_gold, 1: limestone_cream, 2: glass_dark, 3: bronze_dark,
    # 4: awning_black, 5: granite_dark, 6: roof_membrane, 7: warm_light, 8: car_red
    mats = [
        pal["limestone_gold"], pal["limestone_cream"], pal["glass_dark"], pal["bronze_dark"],
        pal["awning_black"], pal["granite_dark"], pal["roof_membrane"], pal["warm_light"], pal["car_red"]
    ]
    for b in (b_117, b_116):
        if not b:
            continue
        pts = ensure_ccw(b["coords_xy"])
        core_pts = inset_polygon(pts, 1.5)
        add_prism(bm, core_pts, 0.0, 20.2 - 0.42, mat_side=2, mat_top=6)

    # Detailed NW facade along Rue Saint-Jacques: (-246.90, -313.24) -> (-234.29, -290.97)
    p1 = (-246.90, -313.24)
    p2 = (-234.29, -290.97)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    # Outward normal pointing NW toward Rue Saint-Jacques: (-uy, ux)
    nx, ny = -uy, ux
    ang = math.atan2(uy, ux)

    # Recessed dark reflective glass plane across entire NW wall (sits at -0.55m, completely open!)
    add_box(bm, (0.5 * (p1[0] + p2[0]) - nx * 0.55, 0.5 * (p1[1] + p2[1]) - ny * 0.55, 10.0),
            (L - 0.4, 0.16, 19.8), angle_z=ang, mat_idx=2)

    n_bays = 6
    bay_w = L / n_bays
    for bi in range(n_bays + 1):
        s = bi * bay_w
        px = p1[0] + ux * s + nx * 0.05
        py = p1[1] + uy * s + ny * 0.05
        # Fluted limestone column/pilaster
        add_cylinder(bm, px, py, 0.0, 20.0, 0.42, 0.36, segs=14, mat_idx=0)
        add_box(bm, (px, py, 4.85), (0.92, 0.92, 0.55), angle_z=ang, mat_idx=1)

    # Spandrel bands between floors + dark bronze/wood storefront frieze at z = 4.6..5.3m
    for z_sp, m_sp in [(0.35, 5), (4.95, 3), (10.1, 0), (15.1, 0), (19.8, 1)]:
        add_box(bm, (0.5 * (p1[0] + p2[0]) - nx * 0.15, 0.5 * (p1[1] + p2[1]) - ny * 0.15, z_sp),
                (L, 0.65, 0.85 if z_sp > 0.5 else 0.70), angle_z=ang, mat_idx=m_sp, cap_top=(z_sp < 10.0))
    # Projecting cornices at z = 5.25m, 10.4m, 15.4m, and 20.1m
    for z_ent in (5.25, 10.4, 15.4, 20.1):
        add_box(bm, (0.5 * (p1[0] + p2[0]) + nx * 0.28, 0.5 * (p1[1] + p2[1]) + ny * 0.28, z_ent),
                (L + 0.4, 0.65, 0.38), angle_z=ang, mat_idx=3 if z_ent == 5.25 else 1)

    # Distinct wedge-shaped black fabric storefront awnings ("SESAME") + upper arched windows
    for bi in range(n_bays):
        sc = (bi + 0.5) * bay_w
        wx = p1[0] + ux * sc
        wy = p1[1] + uy * sc
        # Window mullions on ground & upper floors
        add_box(bm, (wx - nx * 0.42, wy - ny * 0.42, 10.0), (0.09, 0.12, 19.2), angle_z=ang, mat_idx=3)
        for z_tr in (2.6, 7.6, 12.6, 17.4):
            add_box(bm, (wx - nx * 0.42, wy - ny * 0.42, z_tr), (bay_w - 0.75, 0.12, 0.09), angle_z=ang, mat_idx=3)
        # Warm interior restaurant glow on ground floor
        add_box(bm, (wx - nx * 0.95, wy - ny * 0.95, 3.6), (bay_w - 1.1, 0.20, 0.18), angle_z=ang, mat_idx=7)

        # Smooth wedge-shaped black fabric awning with clear gap between bays
        add_sloped_awning(bm, wx, wy, 4.55, 3.35, bay_w * 0.78, 1.45, ux, uy, nx, ny, 4)
        if bi == 2:
            # Red/black "SESAME" blade sign under awning
            add_box(bm, (wx + ux * (bay_w * 0.42) + nx * 0.85, wy + uy * (bay_w * 0.42) + ny * 0.85, 3.15),
                    (0.10, 0.65, 0.38), angle_z=ang, mat_idx=8)

        # Smooth radial stone archivolts over 2nd, 3rd, and 4th floor windows
        for z_arch in (8.6, 13.6, 18.3):
            for k in range(9):
                a = math.pi * k / 8.0
                rx = wx + ux * (math.cos(a) * (bay_w * 0.36)) + nx * 0.14
                ry = wy + uy * (math.cos(a) * (bay_w * 0.36)) + ny * 0.14
                rz = z_arch + math.sin(a) * 0.78
                add_box(bm, (rx, ry, rz), (0.36, 0.36, 0.34), angle_z=ang, mat_idx=1)

    # Wrought-iron sidewalk patio railing with vertical pickets in front of ground floor
    for z_r in (0.20, 0.98):
        add_box(bm, (0.5 * (p1[0] + p2[0]) + nx * 1.45, 0.5 * (p1[1] + p2[1]) + ny * 1.45, z_r),
                (L * 0.90, 0.06, 0.05), angle_z=ang, mat_idx=3)
    for pi in range(28):
        ps = L * 0.05 + (pi / 27.0) * (L * 0.90)
        add_box(bm, (p1[0] + ux * ps + nx * 1.45, p1[1] + uy * ps + ny * 1.45, 0.58),
                (0.04, 0.04, 0.85), angle_z=ang, mat_idx=3)

    mesh = bpy.data.meshes.new("Bldg_339911117_SesameVictorian")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_339911117_SesameVictorian", mesh)
    link_obj(obj, col_owned)


def build_cdp_and_415_saint_antoine(col_owned, col_proxy, b_415, b_cdp, pal):
    """Builds 415 Rue Saint-Antoine Ouest (611333440, Owned) and the modern white-mullion glass
    curtain-wall wing of Édifice Jacques-Parizeau / CDP (112881749, Proxy) on the left of
    Square_Victoria_West_Entrance.jpg, plus the colorful Palais des Congrès corner on the far left
    of Rue_SaintAntoine_North_Wall.jpg."""
    if b_415:
        bm = bmesh.new()
        mats = [pal["brick_red"], pal["limestone_grey"], pal["glass_dark"], pal["bronze_dark"], pal["roof_membrane"]]
        pts = ensure_ccw(b_415["coords_xy"])
        core_pts = inset_polygon(pts, 1.4)
        add_prism(bm, core_pts, 0.0, 15.8, mat_side=2, mat_top=4)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 6.0:
                build_detailed_facade_wall(bm, p1, p2, 0.0, 15.8, bay_w=3.6, floor_h=3.8,
                                           mat_wall=0, mat_glass=2, mat_frame=3, mat_sill=1,
                                           recess=0.48, has_ground_shop=True)
            else:
                add_wall_strip(bm, p1, p2, 0.0, 15.8, -0.1, 0.35, mat_idx=1)
        mesh = bpy.data.meshes.new("Bldg_611333440_415StAntoine")
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(m)
        obj = bpy.data.objects.new("Bldg_611333440_415StAntoine", mesh)
        link_obj(obj, col_owned)

    bm_p = bmesh.new()
    mats_p = [
        pal["glass_green"], pal["metal_white"], pal["limestone_grey"], pal["roof_membrane"],
        make_simple_mat("Palais_Green", (0.18, 0.68, 0.32), roughness=0.05),
        make_simple_mat("Palais_Blue", (0.12, 0.42, 0.85), roughness=0.05),
        make_simple_mat("Palais_Yellow", (0.92, 0.78, 0.12), roughness=0.05),
        make_simple_mat("Palais_Magenta", (0.85, 0.14, 0.48), roughness=0.05),
    ]
    if b_cdp:
        add_prism(bm_p, b_cdp["coords_xy"], 0.0, 44.5, mat_side=0, mat_top=3)
    cw_cx, cw_cy = -362.0, -234.0
    ang_cw = math.radians(59.0)
    add_box(bm_p, (cw_cx, cw_cy, 22.5), (34.0, 26.0, 45.0), angle_z=ang_cw, mat_idx=0)
    for fl in range(12):
        fz = 3.8 + fl * 3.5
        add_box(bm_p, (cw_cx, cw_cy, fz), (34.5, 26.5, 0.85), angle_z=ang_cw, mat_idx=1)
    for mi in range(-7, 8):
        ux, uy = math.cos(ang_cw), math.sin(ang_cw)
        nx, ny = uy, -ux
        add_box(bm_p, (cw_cx + ux * (mi * 2.2) + nx * 13.1, cw_cy + uy * (mi * 2.2) + ny * 13.1, 22.5),
                (0.18, 0.35, 45.0), angle_z=ang_cw, mat_idx=1)
        add_box(bm_p, (cw_cx - ux * 17.1 + nx * (mi * 1.7), cw_cy - uy * 17.1 + ny * (mi * 1.7), 22.5),
                (0.35, 0.18, 45.0), angle_z=ang_cw, mat_idx=1)
    add_box(bm_p, (cw_cx, cw_cy, 47.8), (28.0, 21.0, 5.5), angle_z=ang_cw, mat_idx=1)

    p_pc1 = (-324.0, -184.0)
    p_pc2 = (-298.0, -142.0)
    pdx, pdy = p_pc2[0] - p_pc1[0], p_pc2[1] - p_pc1[1]
    pL = math.hypot(pdx, pdy)
    pux, puy = pdx / pL, pdy / pL
    pnx, pny = puy, -pux
    pang = math.atan2(puy, pux)
    pc_cx = 0.5 * (p_pc1[0] + p_pc2[0]) - pnx * 8.0
    pc_cy = 0.5 * (p_pc1[1] + p_pc2[1]) - pny * 8.0
    add_box(bm_p, (pc_cx, pc_cy, 9.5), (pL, 16.0, 19.0), angle_z=pang, mat_idx=2)
    add_box(bm_p, (0.5 * (p_pc1[0] + p_pc2[0]), 0.5 * (p_pc1[1] + p_pc2[1]), 5.2), (pL, 2.4, 1.4), angle_z=pang, mat_idx=2)
    for pi in range(12):
        ps = (pi + 0.5) * (pL / 12.0)
        px = p_pc1[0] + pux * ps + pnx * 0.25
        py = p_pc1[1] + puy * ps + pny * 0.25
        c_mat = 4 + (pi % 4)
        add_box(bm_p, (px, py, 12.5), (pL / 12.2, 0.35, 11.5), angle_z=pang, mat_idx=c_mat)

    mesh_p = bpy.data.meshes.new("Bldg_112881749_CDP_And_PalaisProxy")
    bm_p.to_mesh(mesh_p)
    bm_p.free()
    for m in mats_p:
        mesh_p.materials.append(m)
    obj_p = bpy.data.objects.new("Bldg_112881749_CDP_And_PalaisProxy", mesh_p)
    link_obj(obj_p, col_proxy)


def build_remaining_buildings(col_owned, col_proxy, buildings, handled_ids, pal):
    """Builds all remaining Owned and Context Proxy buildings in dossier.json with inset glass cores
    so every recessed 3D window bay displays reflective glass."""
    mats = [
        pal["limestone_cream"], pal["brick_red"], pal["limestone_grey"],
        pal["glass_dark"], pal["bronze_dark"], pal["roof_membrane"]
    ]
    bm_owned = bmesh.new()
    bm_proxy = bmesh.new()

    for b in buildings:
        bid = b["id"]
        if bid in handled_ids:
            continue
        is_owner = bool(b.get("is_primary_owner", True))
        bm = bm_owned if is_owner else bm_proxy
        tags = b.get("tags", {})
        levels_str = str(tags.get("building:levels", "6"))
        try:
            levels = max(2, int(float(levels_str)))
        except ValueError:
            levels = 6
        h = levels * 3.7
        mat_w = (bid % 3)

        pts = ensure_ccw(b["coords_xy"])
        if len(pts) < 3:
            continue
        core_pts = inset_polygon(pts, 1.3)
        add_prism(bm, core_pts, 0.0, h - 0.28, mat_side=3, mat_top=5)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 6.5:
                build_detailed_facade_wall(bm, p1, p2, 0.0, h, bay_w=4.2, floor_h=3.7,
                                           mat_wall=mat_w, mat_glass=3, mat_frame=4, mat_sill=0,
                                           recess=0.45, has_ground_shop=True)
            else:
                add_wall_strip(bm, p1, p2, 0.0, h, -0.1, 0.35, mat_idx=mat_w)

    for name, bm, target_col in [("Bldg_Remaining_Owned", bm_owned, col_owned),
                                 ("Bldg_Remaining_Proxy", bm_proxy, col_proxy)]:
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(name, mesh)
        if target_col == col_proxy:
            obj.hide_render = True
            obj.hide_viewport = True
        link_obj(obj, target_col)


def add_sculpted_tire(bm, cx, cy, cz, r_tire, width, angle_z, mat_tire, mat_rim):
    ca, sa = math.cos(angle_z), math.sin(angle_z)
    segs = 16
    for side, r, w_off, m_idx in [
        (0, r_tire, width * 0.5, mat_tire),
        (1, r_tire * 0.62, width * 0.53, mat_rim),
    ]:
        v_left, v_right = [], []
        for i in range(segs):
            a = 2.0 * math.pi * i / segs
            lx = math.cos(a) * r
            lz = math.sin(a) * r
            v_left.append(bm.verts.new((cx + lx * ca - (-w_off) * sa, cy + lx * sa + (-w_off) * ca, cz + lz)))
            v_right.append(bm.verts.new((cx + lx * ca - w_off * sa, cy + lx * sa + w_off * ca, cz + lz)))
        if side == 0:
            for i in range(segs):
                j = (i + 1) % segs
                f = bm.faces.new((v_left[i], v_left[j], v_right[j], v_right[i]))
                f.material_index = m_idx
        f1 = bm.faces.new(v_right)
        f1.material_index = m_idx
        f2 = bm.faces.new(list(reversed(v_left)))
        f2.material_index = m_idx


def add_sculpted_vehicle(bm, cx, cy, z0, heading_deg, mat_body, mat_glass, mat_tire, mat_rim, mat_light, mat_tail, is_suv=False):
    ang = math.radians(90.0 - heading_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    L = 4.65 if is_suv else 4.45
    W = 1.92 if is_suv else 1.84
    body_h = 0.68 if is_suv else 0.58
    cab_h = 0.62 if is_suv else 0.54
    z_base = z0 + 0.34

    # Sculpted 8-vertex tapered lower body with sloped hood & front/rear bumpers
    z_b0, z_b1 = z_base, z_base + body_h
    hb = W * 0.5
    local_body = [
        (-L * 0.50, -hb, z_b0), (L * 0.50, -hb, z_b0), (L * 0.50, hb, z_b0), (-L * 0.50, hb, z_b0),
        (-L * 0.47, -hb * 0.96, z_b1), (L * 0.46, -hb * 0.96, z_b1 - 0.08),
        (L * 0.46, hb * 0.96, z_b1 - 0.08), (-L * 0.47, hb * 0.96, z_b1),
    ]
    bv = [bm.verts.new((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, lz)) for lx, ly, lz in local_body]
    for f_idxs in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        f = bm.faces.new([bv[i] for i in f_idxs])
        f.material_index = mat_body

    # Front dark grille + bumpers + side mirrors
    add_box(bm, (cx + (L * 0.49) * ca, cy + (L * 0.49) * sa, z_base + body_h * 0.40),
            (0.08, W * 0.52, body_h * 0.45), angle_z=ang, mat_idx=mat_tire)
    for sy in (-hb - 0.08, hb + 0.08):
        mx = cx + (L * 0.14) * ca - sy * sa
        my = cy + (L * 0.14) * sa + sy * ca
        add_box(bm, (mx, my, z_b1 + 0.08), (0.18, 0.22, 0.12), angle_z=ang, mat_idx=mat_body)

    # Tapered 8-vertex aerodynamic greenhouse cabin
    z_cab0 = z_b1 - 0.04
    z_cab1 = z_cab0 + cab_h
    x_f_bot, x_b_bot = L * 0.22, -L * 0.38 if is_suv else -L * 0.32
    x_f_top, x_b_top = L * 0.04, -L * 0.28 if is_suv else -L * 0.18
    yb, yt = W * 0.44, W * 0.37
    local_cab = [
        (x_b_bot, -yb, z_cab0), (x_f_bot, -yb, z_cab0), (x_f_bot, yb, z_cab0), (x_b_bot, yb, z_cab0),
        (x_b_top, -yt, z_cab1), (x_f_top, -yt, z_cab1), (x_f_top, yt, z_cab1), (x_b_top, yt, z_cab1),
    ]
    cv = [bm.verts.new((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, lz)) for lx, ly, lz in local_cab]
    c_faces = [
        ((0, 3, 2, 1), mat_body), ((4, 5, 6, 7), mat_body),
        ((0, 1, 5, 4), mat_glass), ((1, 2, 6, 5), mat_glass),
        ((2, 3, 7, 6), mat_glass), ((3, 0, 4, 7), mat_glass),
    ]
    for f_idxs, m_i in c_faces:
        f = bm.faces.new([cv[i] for i in f_idxs])
        f.material_index = m_i

    # Headlights & Taillights
    for sy in (-W * 0.34, W * 0.34):
        hx, hy = cx + (L * 0.49) * ca - sy * sa, cy + (L * 0.49) * sa + sy * ca
        tx, ty = cx + (-L * 0.49) * ca - sy * sa, cy + (-L * 0.49) * sa + sy * ca
        add_box(bm, (hx, hy, z_base + body_h * 0.58), (0.08, 0.30, 0.16), angle_z=ang, mat_idx=mat_light)
        add_box(bm, (tx, ty, z_base + body_h * 0.58), (0.08, 0.32, 0.18), angle_z=ang, mat_idx=mat_tail)

    # 4 Cylindrical Tires with Dark Rubber & Alloy Rims
    for wx_off in (-L * 0.31, L * 0.31):
        for wy_off in (-W * 0.46, W * 0.46):
            wx = cx + wx_off * ca - wy_off * sa
            wy = cy + wx_off * sa + wy_off * ca
            add_sculpted_tire(bm, wx, wy, z0 + 0.34, 0.34, 0.24, ang, mat_tire, mat_rim)


def add_commercial_van(bm, cx, cy, z0, heading_deg, mat_white, mat_glass, mat_tire, mat_rim, mat_tail, mat_orange, has_ladder=True):
    """Sculpted white commercial service van ('SECUR PLUS') with rear door windows, side stripe/lettering,
    side mirrors, and detailed aluminum roof ladder rack with a 2-rail orange stepladder & rungs."""
    ang = math.radians(90.0 - heading_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    L, W = 5.45, 2.02
    z_base = z0 + 0.36

    # Main van cargo body + sloped hood/windshield
    add_box(bm, (cx - 0.35 * ca, cy - 0.35 * sa, z_base + 0.92), (L * 0.84, W, 1.84), angle_z=ang, mat_idx=mat_white)
    add_box(bm, (cx + 2.15 * ca, cy + 2.15 * sa, z_base + 0.52), (1.15, W * 0.96, 1.04), angle_z=ang, mat_idx=mat_white)
    # Sloped windshield + side cab windows + side mirrors
    add_box(bm, (cx + 1.65 * ca, cy + 1.65 * sa, z_base + 1.38), (0.75, W * 0.88, 0.68), angle_z=ang, mat_idx=mat_glass)
    add_box(bm, (cx + 1.15 * ca, cy + 1.15 * sa, z_base + 1.38), (1.05, W + 0.04, 0.62), angle_z=ang, mat_idx=mat_glass)
    for sy in (-W * 0.54, W * 0.54):
        add_box(bm, (cx + 1.45 * ca - sy * sa, cy + 1.45 * sa + sy * ca, z_base + 1.18), (0.16, 0.22, 0.24), angle_z=ang, mat_idx=mat_tire)

    # Rear double-door seam + 2 dark rear door windows + license plate + bumper + taillights
    add_box(bm, (cx - 2.65 * ca, cy - 2.65 * sa, z_base + 0.92), (0.04, 0.04, 1.75), angle_z=ang, mat_idx=mat_tire)
    for sy in (-0.44, 0.44):
        wx, wy = cx - 2.65 * ca - sy * sa, cy - 2.65 * sa + sy * ca
        add_box(bm, (wx, wy, z_base + 1.36), (0.05, 0.68, 0.56), angle_z=ang, mat_idx=mat_glass)
    add_box(bm, (cx - 2.68 * ca, cy - 2.68 * sa, z_base + 0.12), (0.24, W + 0.04, 0.24), angle_z=ang, mat_idx=mat_tire)
    for sy in (-W * 0.43, W * 0.43):
        tx, ty = cx - 2.64 * ca - sy * sa, cy - 2.64 * sa + sy * ca
        add_box(bm, (tx, ty, z_base + 0.72), (0.10, 0.20, 0.38), angle_z=ang, mat_idx=mat_tail)

    # "SECUR PLUS" orange graphic arc + dark lettering stripe on sides & rear
    if has_ladder:
        add_box(bm, (cx - 0.25 * ca, cy - 0.25 * sa, z_base + 1.22), (2.6, W + 0.03, 0.22), angle_z=ang, mat_idx=mat_orange)
        add_box(bm, (cx - 0.65 * ca, cy - 0.65 * sa, z_base + 0.96), (2.1, W + 0.03, 0.14), angle_z=ang, mat_idx=mat_tire)
        add_box(bm, (cx - 2.65 * ca, cy - 2.65 * sa, z_base + 0.82), (0.05, 1.55, 0.14), angle_z=ang, mat_idx=mat_tire)

        # Detailed Roof Ladder Rack + 2-Rail Orange Fiberglass Extension Ladder with Rungs
        z_roof = z_base + 1.90
        for rx_off in (-1.9, -0.5, 0.8):
            add_box(bm, (cx + rx_off * ca, cy + rx_off * sa, z_roof), (0.10, W * 0.98, 0.22), angle_z=ang, mat_idx=mat_rim)
        for ly_off in (-0.32, 0.32):
            lx = cx - 0.55 * ca - ly_off * sa
            ly = cy - 0.55 * sa + ly_off * ca
            add_box(bm, (lx, ly, z_roof + 0.16), (3.85, 0.08, 0.12), angle_z=ang, mat_idx=mat_orange)
        for ri in range(11):
            rx_r = -2.25 + ri * 0.34
            add_box(bm, (cx + rx_r * ca, cy + rx_r * sa, z_roof + 0.16), (0.05, 0.62, 0.05), angle_z=ang, mat_idx=mat_rim)

    # 4 Cylindrical Tires with Dark Rubber & Silver Rims
    for wx_off in (-1.68, 1.72):
        for wy_off in (-W * 0.46, W * 0.46):
            wx = cx + wx_off * ca - wy_off * sa
            wy = cy + wx_off * sa + wy_off * ca
            add_sculpted_tire(bm, wx, wy, z0 + 0.36, 0.36, 0.26, ang, mat_tire, mat_rim)


def build_streetscape_and_vehicles(col_owned, dossier, pal):
    """Builds accurate road decks, sidewalks, street markings, vehicles, streetlamps, traffic lights,
    fire hydrants, and street furniture matching all 4 Street View cameras."""
    bm = bmesh.new()
    # 0: asphalt_pbr, 1: sidewalk_pbr, 2: granite_dark, 3: white_paint,
    # 4: car_white, 5: car_dark, 6: car_red, 7: car_orange,
    # 8: glass_dark, 9: bronze_dark, 10: metal_silver, 11: red_light,
    # 12: warm_light, 13: sign_green, 14: post_pink, 15: tire_rubber,
    # 16: asphalt_patch, 17: cast_iron
    mats = [
        pal["asphalt_pbr"], pal["sidewalk_pbr"], pal["granite_dark"], pal["white_paint"],
        pal["car_white"], pal["car_dark"], pal["car_red"], pal["car_orange"],
        pal["glass_dark"], pal["bronze_dark"], pal["metal_silver"], pal["red_light"],
        pal["warm_light"], pal["sign_green"], pal["post_pink"], pal["tire_rubber"],
        pal["asphalt_patch"], pal["cast_iron"]
    ]

    # Ground asphalt plane covering block + context
    add_box(bm, (-300.0, -250.0, -0.10), (420.0, 420.0, 0.20), mat_idx=0)

    # Raised concrete sidewalks with dark granite curbs along all building perimeters
    for b in dossier["osm_features"]["buildings"]:
        pts = list(b["coords_xy"])
        if len(pts) < 3:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        sw_pts = []
        curb_pts = []
        for x, y in pts:
            dx, dy = x - cx, y - cy
            d = max(0.1, math.hypot(dx, dy))
            sw_pts.append((x + dx / d * 3.2, y + dy / d * 3.2))
            curb_pts.append((x + dx / d * 3.45, y + dy / d * 3.45))
        add_prism(bm, curb_pts, 0.0, 0.15, mat_side=2, mat_top=2)
        add_prism(bm, sw_pts, 0.0, 0.16, mat_side=1, mat_top=1)

    # 1. Camera 1 Foreground (Square_Victoria_West_Entrance: (-366.57, -287.81), heading 51.9)
    add_commercial_van(bm, -359.1, -284.7, 0.0, 31.1, 4, 8, 15, 10, 11, 7, has_ladder=True)
    add_sculpted_vehicle(bm, -346.5, -263.8, 0.0, 31.1, 5, 8, 15, 10, 12, 11, is_suv=True)
    add_sculpted_vehicle(bm, -340.5, -253.8, 0.0, 31.1, 5, 8, 15, 10, 12, 11, is_suv=False)
    add_sculpted_vehicle(bm, -350.2, -261.2, 0.0, 31.1, 5, 8, 15, 10, 12, 11, is_suv=False)
    add_commercial_van(bm, -358.8, -256.5, 0.0, 31.1, 4, 8, 15, 10, 11, 4, has_ladder=False)

    ang_ant = math.radians(90.0 - 31.1)
    add_box(bm, (-352.0, -271.0, 0.015), (38.0, 0.14, 0.01), angle_z=ang_ant, mat_idx=3)
    add_cylinder(bm, -356.4, -277.1, 0.01, 0.025, 0.35, 0.35, segs=12, mat_idx=3)
    add_cylinder(bm, -355.8, -276.1, 0.01, 0.025, 0.35, 0.35, segs=12, mat_idx=3)
    add_box(bm, (-355.3, -275.2, 0.018), (0.65, 0.65, 0.015), angle_z=ang_ant + math.pi * 0.25, mat_idx=3)

    # Prominent green/grey "P" parking sign board right behind the van on the right sidewalk (-351.8, -275.8)
    ps_x, ps_y = -351.8, -275.8
    add_cylinder(bm, ps_x, ps_y, 0.15, 3.65, 0.07, 0.07, segs=10, mat_idx=10)
    add_box(bm, (ps_x, ps_y, 3.35), (0.12, 0.95, 0.34), angle_z=ang_ant + math.pi * 0.5, mat_idx=13)
    add_box(bm, (ps_x, ps_y, 2.85), (0.12, 0.95, 0.56), angle_z=ang_ant + math.pi * 0.5, mat_idx=9)
    # Left sidewalk utility pole with curved luminaire arm & blue street sign at (-367.5, -275.0)
    lp_x, lp_y = -367.5, -275.0
    add_cylinder(bm, lp_x, lp_y, 0.15, 8.2, 0.16, 0.12, segs=12, mat_idx=9)
    for k in range(6):
        t = k / 5.0
        add_box(bm, (lp_x + t * 2.2, lp_y - t * 1.2, 6.2 + math.sin(t * 1.4) * 1.1),
                (0.08, 0.55, 0.08), angle_z=ang_ant, mat_idx=9)
    add_box(bm, (lp_x + 0.4, lp_y - 0.2, 3.2), (0.10, 1.15, 0.28), angle_z=ang_ant, mat_idx=13)
    add_cylinder(bm, lp_x + 0.6, lp_y - 0.9, 0.15, 0.85, 0.14, 0.12, segs=10, mat_idx=6)

    # 2. Camera 2 Foreground (Rue_SaintAntoine_North_Wall: (-315.01, -201.42), heading 57.4)
    add_sculpted_vehicle(bm, -301.8, -193.5, 0.0, 31.1, 5, 8, 15, 10, 12, 11, is_suv=False)
    add_sculpted_vehicle(bm, -308.5, -184.2, 0.0, 211.1, 5, 8, 15, 10, 12, 11, is_suv=True)
    add_commercial_van(bm, -298.5, -169.5, 0.0, 31.1, 4, 8, 15, 10, 11, 4, has_ladder=False)
    add_box(bm, (-304.8, -192.0, 0.015), (42.0, 0.12, 0.01), angle_z=ang_ant, mat_idx=3)
    add_box(bm, (-303.4, -192.8, 0.015), (42.0, 0.12, 0.01), angle_z=ang_ant, mat_idx=3)
    # Prominent left-curb streetlamp pole with curved arm at (-314.8, -191.2) visible in left foreground of Cam 2!
    c2_lx, c2_ly = -314.8, -191.2
    add_cylinder(bm, c2_lx, c2_ly, 0.15, 6.8, 0.16, 0.12, segs=12, mat_idx=9)
    for k in range(6):
        t = k / 5.0
        add_box(bm, (c2_lx + t * 1.9, c2_ly - t * 0.9, 5.8 + math.sin(t * 1.4) * 0.75),
                (0.08, 0.48, 0.08), angle_z=ang_ant, mat_idx=9)
    add_box(bm, (c2_lx + 0.25, c2_ly - 0.15, 3.65), (0.08, 0.95, 0.22), angle_z=ang_ant, mat_idx=3)

    # 3. Camera 3 Foreground (Rue_SaintJacques_South_Facades: (-244.15, -298.96), heading 39.2)
    add_sculpted_vehicle(bm, -240.8, -296.4, 0.0, 207.3, 5, 8, 15, 10, 12, 11, is_suv=False)
    add_commercial_van(bm, -236.2, -287.4, 0.0, 207.3, 4, 8, 15, 10, 11, 4, has_ladder=False)
    add_sculpted_vehicle(bm, -231.0, -277.5, 0.0, 207.3, 5, 8, 15, 10, 12, 11, is_suv=True)
    # Left sidewalk pink/red graphic bin at (-246.2, -288.8) + red fire hydrant at (-243.5, -283.5) + red mailbox
    ang_jac = math.radians(90.0 - 27.3)
    add_box(bm, (-246.2, -288.8, 0.62), (0.68, 0.58, 0.98), angle_z=ang_jac, mat_idx=14)
    add_box(bm, (-246.2, -288.8, 1.15), (0.72, 0.62, 0.12), angle_z=ang_jac, mat_idx=9)
    add_cylinder(bm, -243.5, -283.5, 0.15, 0.92, 0.15, 0.13, segs=10, mat_idx=6)
    add_box(bm, (-241.8, -279.8, 0.68), (0.55, 0.52, 1.05), angle_z=ang_jac, mat_idx=6)
    add_cylinder(bm, -242.5, -281.5, 0.15, 3.1, 0.05, 0.05, segs=8, mat_idx=10)
    add_box(bm, (-242.5, -281.5, 2.7), (0.08, 0.45, 0.65), angle_z=ang_jac, mat_idx=3)

    # 4. Camera 4 Foreground (Corner_Rue_SaintPierre: (-215.66, -222.45), heading 222.0)
    add_sculpted_vehicle(bm, -216.8, -234.8, 0.0, 207.3, 6, 8, 15, 10, 12, 11, is_suv=True)
    add_sculpted_vehicle(bm, -223.8, -236.5, 0.0, 207.3, 4, 8, 15, 10, 12, 11, is_suv=False)
    # Right corner traffic signal post with 3-lens signal, turn arrow sign, black Victorian heritage lantern & trash bin
    tp_x, tp_y = -220.3, -227.2
    add_cylinder(bm, tp_x, tp_y, 0.15, 5.15, 0.11, 0.09, segs=12, mat_idx=9)
    # Black 3-lens traffic signal housing (glowing red top lens + dark middle/bottom lenses)
    add_box(bm, (tp_x + 0.08, tp_y + 0.08, 2.72), (0.30, 0.30, 0.96), angle_z=ang_jac, mat_idx=9)
    add_cylinder(bm, tp_x + 0.19, tp_y + 0.19, 2.96, 3.14, 0.11, 0.11, segs=12, mat_idx=11)
    add_cylinder(bm, tp_x + 0.19, tp_y + 0.19, 2.66, 2.82, 0.10, 0.10, segs=12, mat_idx=15)
    add_cylinder(bm, tp_x + 0.19, tp_y + 0.19, 2.38, 2.54, 0.10, 0.10, segs=12, mat_idx=15)
    # White/green directional arrow sign above signal
    add_box(bm, (tp_x + 0.10, tp_y + 0.10, 3.48), (0.08, 0.46, 0.52), angle_z=ang_jac, mat_idx=3)
    add_cylinder(bm, tp_x + 0.14, tp_y + 0.14, 3.38, 3.58, 0.16, 0.16, segs=12, mat_idx=13)
    # Black Victorian heritage lantern cage on top of pole (dark base, warm inner glass, dark conical cap & ribs)
    add_cylinder(bm, tp_x, tp_y, 5.12, 5.25, 0.16, 0.24, segs=8, mat_idx=9)
    add_cylinder(bm, tp_x, tp_y, 5.25, 5.68, 0.20, 0.16, segs=8, mat_idx=8)
    add_cylinder(bm, tp_x, tp_y, 5.30, 5.62, 0.10, 0.08, segs=8, mat_idx=12)
    add_cylinder(bm, tp_x, tp_y, 5.68, 5.92, 0.26, 0.03, segs=8, mat_idx=9)
    for l_ang in (0.0, math.pi * 0.5, math.pi, math.pi * 1.5):
        add_box(bm, (tp_x + math.cos(l_ang) * 0.20, tp_y + math.sin(l_ang) * 0.20, 5.46),
                (0.03, 0.03, 0.44), angle_z=l_ang, mat_idx=9)
    # Overhead diagonal stay wire + dark wooden/metal trash bin at base
    for k in range(8):
        t = k / 7.0
        add_box(bm, (tp_x - t * 1.8, tp_y + t * 0.9, 4.9 + t * 0.65),
                (0.04, 0.35, 0.04), angle_z=ang_jac, mat_idx=9)
    add_cylinder(bm, tp_x - 0.22, tp_y - 0.18, 0.15, 0.88, 0.24, 0.22, segs=12, mat_idx=9)

    # Dark weathered asphalt utility patch + dark metallic cast-iron manhole cover + white stop-bar line
    add_box(bm, (-217.8, -226.8, 0.008), (2.4, 2.2, 0.012), angle_z=ang_jac, mat_idx=16)
    add_cylinder(bm, -217.8, -226.8, 0.012, 0.026, 0.44, 0.42, segs=20, mat_idx=10)
    add_cylinder(bm, -217.8, -226.8, 0.015, 0.030, 0.38, 0.38, segs=20, mat_idx=17)
    # White painted stop-bar / crosswalk lines in immediate foreground of Corner_Rue_SaintPierre
    add_box(bm, (-217.2, -224.2, 0.014), (0.14, 3.2, 0.01), angle_z=ang_jac, mat_idx=3)
    add_box(bm, (-216.2, -223.8, 0.014), (1.8, 0.14, 0.01), angle_z=ang_jac, mat_idx=3)

    mesh = bpy.data.meshes.new("MTL_VM_0011_Streetscape")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("MTL_VM_0011_Streetscape", mesh)
    link_obj(obj, col_owned)


def place_street_trees(col_owned, pal):
    """Loads jacaranda_tree_LOD0 from assets/montreal_kit.blend, reshapes its lower 2.65m multi-trunk
    flare into a slender single-stem urban sapling (r <= 0.085m), and scales the foreground tree behind
    the van to a realistic 3.5m young sapling matching Square_Victoria_West_Entrance.jpg."""
    if not os.path.exists(ASSETS_PATH):
        return
    with bpy.data.libraries.load(ASSETS_PATH, link=False) as (data_from, data_to):
        if "jacaranda_tree_LOD0" in data_from.objects:
            data_to.objects = ["jacaranda_tree_LOD0"]
    src_obj = bpy.data.objects.get("jacaranda_tree_LOD0")
    if src_obj is None:
        return

    sapling_mesh = src_obj.data.copy()
    sapling_mesh.name = "WTC_UrbanSapling_Mesh"
    for v in sapling_mesh.vertices:
        z = v.co.z
        if z < 2.65:
            r = math.hypot(v.co.x, v.co.y)
            if r > 0.001:
                t = max(0.0, min(1.0, (z - 1.85) / 0.80))
                max_r = 0.085 * (1.0 - t) + r * 0.32 * t
                if r > max_r:
                    s = max_r / r
                    v.co.x *= s
                    v.co.y *= s
    sapling_mesh.update()

    # Exact curb-line sapling locations & realistic young urban tree scales
    tree_spots = [
        (-354.8, -280.2, 0.28, 0.4),   # Small 3.5m sapling right behind white van in Square_Victoria_West_Entrance.jpg
        (-344.5, -262.5, 0.42, 1.8),   # Medium 5.5m sidewalk tree further down Rue Saint-Antoine
        (-336.5, -249.0, 0.45, 3.1),   # Further along Rue Saint-Antoine right sidewalk
        (-363.2, -261.8, 0.46, 2.4),   # Left sidewalk tree in front of CDP
        (-352.5, -246.5, 0.46, 0.9),   # Left sidewalk tree further down Rue Saint-Antoine
    ]

    bm_grates = bmesh.new()
    for idx, (tx, ty, sc, rot) in enumerate(tree_spots):
        t_obj = bpy.data.objects.new(f"WTC_StreetTree_{idx:02d}", sapling_mesh)
        t_obj.location = (tx, ty, 0.15)
        t_obj.scale = (sc, sc, sc * 1.05)
        t_obj.rotation_euler = (0.0, 0.0, rot)
        link_obj(t_obj, col_owned)
        add_box(bm_grates, (tx, ty, 0.165), (0.95, 0.95, 0.02), angle_z=rot, mat_idx=0)

    grate_mesh = bpy.data.meshes.new("WTC_Tree_Grates")
    bm_grates.to_mesh(grate_mesh)
    bm_grates.free()
    grate_mesh.materials.append(pal["bronze_dark"])
    grate_obj = bpy.data.objects.new("WTC_Tree_Grates", grate_mesh)
    link_obj(grate_obj, col_owned)


def setup_world_and_render(dossier, iteration=1):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.eevee.use_raytracing = True

    world = bpy.data.worlds.new("WTC_World")
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
        env_tex = wnodes.new("ShaderNodeTexEnvironment")
        env_tex.image = bpy.data.images.load(HDRI_PATH, check_existing=True)
        wlinks.new(env_tex.outputs["Color"], w_bg.inputs["Color"])
    else:
        w_bg.inputs["Color"].default_value = (0.65, 0.78, 0.95, 1.0)

    light_data = bpy.data.lights.new(name="Montreal_Sun", type="SUN")
    light_data.energy = 3.6
    light_data.color = (1.0, 0.95, 0.86)
    light_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name="Montreal_Sun", object_data=light_data)
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(18.0), math.radians(-135.0))
    bpy.context.scene.collection.objects.link(sun_obj)

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    for cam_info in dossier["streetview_cameras"]:
        label = cam_info["label"]
        cx, cy = cam_info["blender_cam_xy_m"]
        heading_deg = float(cam_info.get("heading_deg", cam_info.get("heading", 0.0)))
        pitch_deg = float(cam_info.get("pitch_deg", 10.0))

        cam_data = bpy.data.cameras.new(name=f"Cam_{label}")
        cam_data.angle = math.radians(90.0)
        cam_data.clip_start = 0.2
        cam_data.clip_end = 1500.0
        cam_obj = bpy.data.objects.new(name=f"Cam_{label}", object_data=cam_data)
        cam_obj.location = (cx, cy, 1.7)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch_deg), 0.0, math.radians(-heading_deg))
        bpy.context.scene.collection.objects.link(cam_obj)

        scene.camera = cam_obj
        out_path = os.path.join(RENDERS_DIR, f"iter{iteration}_{label}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {label} -> {out_path}")

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    ov_data = bpy.data.cameras.new(name="Cam_Overview")
    ov_data.angle = math.radians(58.0)
    ov_data.clip_end = 2500.0
    ov_obj = bpy.data.objects.new(name="Cam_Overview", object_data=ov_data)
    ov_obj.location = (-365.0, -395.0, 145.0)
    ov_obj.rotation_euler = (math.radians(46.0), 0.0, math.radians(-32.0))
    bpy.context.scene.collection.objects.link(ov_obj)
    scene.camera = ov_obj
    scene.render.filepath = SNAPSHOT_PATH
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Overview -> {SNAPSHOT_PATH}")


def main():
    iteration = 1
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if args:
            try:
                iteration = int(args[0])
            except ValueError:
                iteration = 1

    clear_scene()
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    pal = create_block_palette()
    col_master = get_or_create_collection(f"Block_{BLOCK_ID}")
    col_owned = get_or_create_collection(f"Block_{BLOCK_ID}_Owned", parent=col_master)
    col_proxy = get_or_create_collection(f"Block_{BLOCK_ID}_Context_Proxy", parent=col_master)
    col_proxy.hide_render = True
    col_proxy.hide_viewport = True

    buildings = dossier["osm_features"]["buildings"]
    b_by_id = {b["id"]: b for b in buildings}

    if 38911498 in b_by_id:
        build_royal_bank_tower(col_owned, b_by_id[38911498]["coords_xy"], pal)
    build_greenshields_and_wtc_north(col_owned, col_proxy, b_by_id.get(104674804), b_by_id.get(104674805), pal)
    if 104674799 in b_by_id:
        build_hotel_intercontinental(col_owned, b_by_id[104674799], b_by_id.get(339853972), pal)
    build_wtc_atrium_and_south_wings(col_owned, b_by_id, pal)
    build_sesame_victorian_building(col_owned, b_by_id.get(339911117), b_by_id.get(339911116), pal)
    build_cdp_and_415_saint_antoine(col_owned, col_proxy, b_by_id.get(611333440), b_by_id.get(112881749), pal)

    handled_ids = {
        38911498, 104674804, 104674805, 104674799, 339853972,
        104674803, 104674800, 104674801, 104674810, 104674798,
        104674802, 340058291, 339911117, 339911116, 611333440, 112881749
    }
    build_remaining_buildings(col_owned, col_proxy, buildings, handled_ids, pal)
    build_streetscape_and_vehicles(col_owned, dossier, pal)
    place_street_trees(col_owned, pal)

    setup_world_and_render(dossier, iteration=iteration)

    for ext in ("", "@", "1"):
        p = BLEND_PATH + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    tmp_blend = BLEND_PATH + ".tmp.blend"
    if os.path.exists(tmp_blend):
        os.remove(tmp_blend)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
    if os.path.exists(BLEND_PATH):
        try:
            os.remove(BLEND_PATH)
        except OSError:
            pass
    if os.path.exists(BLEND_PATH + "@"):
        try:
            os.remove(BLEND_PATH + "@")
        except OSError:
            pass
    os.replace(tmp_blend, BLEND_PATH)
    bpy.ops.wm.usd_export(filepath=USDC_PATH)
    print(f"Saved {BLEND_PATH} and exported {USDC_PATH}")


if __name__ == "__main__":
    main()
