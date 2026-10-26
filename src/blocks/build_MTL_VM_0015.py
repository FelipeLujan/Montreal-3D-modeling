import bpy
import bmesh
import json
import math
import os
import sys

sys.path.append(r"C:\Users\Felipe\Documents\coding\montreal\src")
import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0015"
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


def make_pbr_mat(name, prefix, tint=(1.0, 1.0, 1.0), scale=0.68, roughness_mult=1.0, metallic=0.0, normal_strength=0.15, emission_color=None, emission_strength=0.0):
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
    if emission_strength > 0.0:
        ec = emission_color if emission_color is not None else tint
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (ec[0], ec[1], ec[2], 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
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
        nor.inputs["Strength"].default_value = normal_strength
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
    pal["limestone_white"] = make_pbr_mat("PAC_Limestone_White", "sandstone_blocks_05", tint=(0.98, 0.97, 0.94), scale=0.65, roughness_mult=0.78, normal_strength=0.10, emission_color=(0.86, 0.85, 0.82), emission_strength=0.34)
    pal["limestone_cream"] = make_pbr_mat("PAC_Limestone_Cream", "sandstone_blocks_05", tint=(0.94, 0.90, 0.82), scale=0.62, roughness_mult=0.80, normal_strength=0.12, emission_color=(0.78, 0.75, 0.68), emission_strength=0.25)
    pal["limestone_grey"] = make_pbr_mat("PAC_Limestone_Grey", "sandstone_blocks_05", tint=(0.78, 0.80, 0.82), scale=0.62, roughness_mult=0.80, normal_strength=0.12, emission_color=(0.68, 0.70, 0.72), emission_strength=0.24)
    pal["custom_house_ashlar"] = make_pbr_mat("PAC_CustomHouse_Ashlar", "sandstone_blocks_05", tint=(0.86, 0.87, 0.88), scale=0.72, roughness_mult=0.75, normal_strength=0.06, emission_color=(0.74, 0.75, 0.76), emission_strength=0.24)
    pal["limestone_dark"] = make_pbr_mat("PAC_Limestone_Dark", "sandstone_blocks_05", tint=(0.60, 0.62, 0.64), scale=0.65, roughness_mult=0.85, normal_strength=0.14, emission_color=(0.50, 0.52, 0.54), emission_strength=0.18)
    pal["granite_dark"] = make_pbr_mat("PAC_Granite_Dark", "sandstone_blocks_05", tint=(0.34, 0.35, 0.37), scale=0.60, roughness_mult=0.65, normal_strength=0.10)
    pal["brick_red"] = make_pbr_mat("PAC_Brick_Red", "castle_brick_02_red", tint=(0.82, 0.38, 0.28), scale=0.75, roughness_mult=0.88, normal_strength=0.16, emission_color=(0.68, 0.32, 0.22), emission_strength=0.20)
    pal["asphalt_pbr"] = make_pbr_mat("PAC_Asphalt", "asphalt_02", tint=(0.82, 0.80, 0.78), scale=0.18, roughness_mult=0.88, normal_strength=0.04, emission_color=(0.66, 0.65, 0.62), emission_strength=0.38)
    pal["ballast_pbr"] = make_pbr_mat("PAC_Ballast", "cobblestone_floor_08", tint=(0.64, 0.60, 0.56), scale=0.68, roughness_mult=0.92, normal_strength=0.20, emission_color=(0.48, 0.45, 0.42), emission_strength=0.22)
    pal["sidewalk_pbr"] = make_pbr_mat("PAC_Sidewalk", "cobblestone_floor_08", tint=(0.86, 0.85, 0.82), scale=0.22, roughness_mult=0.85, normal_strength=0.06, emission_color=(0.72, 0.71, 0.68), emission_strength=0.30)
    pal["roof_membrane"] = make_pbr_mat("PAC_Roof_Membrane", "sandstone_blocks_05", tint=(0.92, 0.93, 0.94), scale=0.25, roughness_mult=0.85, normal_strength=0.04, emission_color=(0.80, 0.82, 0.84), emission_strength=0.35)
    pal["roof_terracotta"] = make_simple_mat("PAC_Roof_Terracotta", (0.58, 0.40, 0.32), roughness=0.65, emission_strength=0.22)
    pal["bronze_dark"] = make_simple_mat("PAC_Bronze_Dark", (0.10, 0.11, 0.12), roughness=0.28, metallic=0.78)
    pal["frame_green"] = make_simple_mat("PAC_Frame_Green", (0.09, 0.22, 0.14), roughness=0.30, metallic=0.30)
    pal["metal_white"] = make_simple_mat("PAC_Metal_White", (0.92, 0.93, 0.95), roughness=0.24, metallic=0.65, emission_strength=0.20)
    pal["metal_silver"] = make_simple_mat("PAC_Metal_Silver", (0.76, 0.79, 0.82), roughness=0.18, metallic=0.90)
    pal["rail_rust"] = make_simple_mat("PAC_Rail_Rust", (0.42, 0.26, 0.16), roughness=0.55, metallic=0.65, emission_strength=0.15)
    pal["wood_plywood"] = make_simple_mat("PAC_Wood_Plywood", (0.76, 0.60, 0.42), roughness=0.75, metallic=0.0, emission_strength=0.22)
    pal["copper_green"] = make_simple_mat("PAC_Copper_Green", (0.32, 0.56, 0.44), roughness=0.38, metallic=0.45)
    pal["slate_dark"] = make_simple_mat("PAC_Slate_Dark", (0.22, 0.24, 0.27), roughness=0.48, metallic=0.20)
    pal["glass_dark"] = make_simple_mat("PAC_Glass_Dark", (0.05, 0.09, 0.14), roughness=0.03, metallic=0.38, ior=1.52)
    pal["glass_blue"] = make_simple_mat("PAC_Glass_Blue", (0.12, 0.30, 0.48), roughness=0.03, metallic=0.40, ior=1.52)
    pal["banner_blue"] = make_simple_mat("PAC_Banner_Blue", (0.04, 0.28, 0.72), roughness=0.38, metallic=0.05, emission_strength=0.45)
    pal["banner_gold"] = make_simple_mat("PAC_Banner_Gold", (0.88, 0.72, 0.28), roughness=0.32, metallic=0.55, emission_strength=0.25)
    pal["door_blue"] = make_simple_mat("PAC_Door_Blue", (0.12, 0.38, 0.82), roughness=0.35, metallic=0.10)
    pal["white_paint"] = make_simple_mat("PAC_White_Paint", (0.94, 0.94, 0.94), roughness=0.35, metallic=0.0)
    pal["yellow_paint"] = make_simple_mat("PAC_Yellow_Paint", (0.92, 0.64, 0.16), roughness=0.40, metallic=0.0)
    pal["warm_light"] = make_simple_mat("PAC_Warm_Light", (1.0, 0.92, 0.76), roughness=0.2, emission_strength=4.8)
    pal["red_light"] = make_simple_mat("PAC_Red_Light", (0.95, 0.08, 0.05), roughness=0.15, emission_strength=5.5)
    pal["car_white"] = make_simple_mat("PAC_Car_White", (0.92, 0.93, 0.95), roughness=0.14, metallic=0.35)
    pal["car_silver"] = make_simple_mat("PAC_Car_Silver", (0.68, 0.71, 0.74), roughness=0.16, metallic=0.72)
    pal["car_dark"] = make_simple_mat("PAC_Car_Dark", (0.12, 0.14, 0.17), roughness=0.15, metallic=0.68)
    pal["car_orange"] = make_simple_mat("PAC_Car_Orange", (0.95, 0.38, 0.06), roughness=0.25, metallic=0.15)
    pal["tire_rubber"] = make_simple_mat("PAC_Tire_Rubber", (0.05, 0.05, 0.06), roughness=0.78, metallic=0.0)
    pal["shrub_green"] = make_simple_mat("PAC_Shrub_Green", (0.22, 0.42, 0.14), roughness=0.80, metallic=0.0)
    pal["grass_green"] = make_pbr_mat("PAC_Grass_Green", "leafy_grass", tint=(0.42, 0.68, 0.28), scale=0.35, roughness_mult=0.92)
    pal["gravel_path"] = make_pbr_mat("PAC_Gravel_Path", "gravel_floor_02", tint=(0.78, 0.76, 0.72), scale=0.45, roughness_mult=0.90)
    pal["water_pbr"] = make_pbr_mat("PAC_River_Water", "concrete_floor_worn_001", tint=(0.06, 0.16, 0.24), scale=0.18, roughness_mult=0.18, normal_strength=0.35)
    pal["tree_bark"] = make_pbr_mat("PAC_Tree_Bark", "bark_willow_02", tint=(0.42, 0.34, 0.26), scale=0.80, roughness_mult=0.90)

    # Lush sunlit summer green canopy material with Subsurface Scattering & subtle bounced-light emission
    mat_canopy = make_pbr_mat("Mat_MTL_Summer_Canopy_Green", "forest_leaves_02", tint=(0.30, 0.62, 0.20), scale=1.0, roughness_mult=0.68, normal_strength=0.35)
    if mat_canopy and mat_canopy.use_nodes:
        for n in mat_canopy.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                if "Subsurface Weight" in n.inputs:
                    n.inputs["Subsurface Weight"].default_value = 0.35
                if "Subsurface Radius" in n.inputs:
                    n.inputs["Subsurface Radius"].default_value = (0.4, 0.8, 0.2)
                if "Emission Color" in n.inputs:
                    n.inputs["Emission Color"].default_value = (0.24, 0.50, 0.14, 1.0)
                if "Emission Strength" in n.inputs:
                    n.inputs["Emission Strength"].default_value = 0.22
    pal["Mat_MTL_Summer_Canopy_Green"] = mat_canopy
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


def add_smooth_arch_band(bm, wx, wy, z_spring, r_in_w, r_in_h, arch_thick, n_front, n_back, ux, uy, nx, ny, segs=24, mat_idx=0):
    """Builds a smooth, continuous 24-segment radial semicircular/segmental stone arch ring with zero stair-stepping."""
    r_out_w = r_in_w + arch_thick
    r_out_h = r_in_h + arch_thick
    for i in range(segs):
        a0 = math.pi * i / segs
        a1 = math.pi * (i + 1) / segs
        c0, s0 = math.cos(a0), math.sin(a0)
        c1, s1 = math.cos(a1), math.sin(a1)
        pts_ring = [
            (c0 * r_in_w, n_back, z_spring + s0 * r_in_h),
            (c1 * r_in_w, n_back, z_spring + s1 * r_in_h),
            (c1 * r_out_w, n_back, z_spring + s1 * r_out_h),
            (c0 * r_out_w, n_back, z_spring + s0 * r_out_h),
            (c0 * r_in_w, n_front, z_spring + s0 * r_in_h),
            (c1 * r_in_w, n_front, z_spring + s1 * r_in_h),
            (c1 * r_out_w, n_front, z_spring + s1 * r_out_h),
            (c0 * r_out_w, n_front, z_spring + s0 * r_out_h),
        ]
        v = [bm.verts.new((wx + ux * u_off + nx * n_off, wy + uy * u_off + ny * n_off, z_val))
             for u_off, n_off, z_val in pts_ring]
        for f_idxs in [(4, 5, 6, 7), (1, 0, 3, 2), (0, 1, 5, 4), (2, 3, 7, 6), (0, 4, 7, 3), (1, 2, 6, 5)]:
            f = bm.faces.new([v[k] for k in f_idxs])
            f.material_index = mat_idx


def add_arch_spandrel_fill(bm, wx, wy, z_spring, z_top, half_w, r_in_w, r_in_h, n_front, n_back, ux, uy, nx, ny, segs=24, mat_idx=0):
    """Fills the rectangular wall region above a semicircular arch opening so the window opening is a true smooth arch."""
    for i in range(segs):
        a0 = math.pi * i / segs
        a1 = math.pi * (i + 1) / segs
        u0 = math.cos(a0) * r_in_w
        z0 = z_spring + math.sin(a0) * r_in_h
        u1 = math.cos(a1) * r_in_w
        z1 = z_spring + math.sin(a1) * r_in_h
        u0_top = half_w if i == 0 else (-half_w if i == segs else u0)
        u1_top = -half_w if (i + 1) == segs else u1
        pts_s = [
            (u0, n_back, z0), (u1, n_back, z1), (u1_top, n_back, z_top), (u0_top, n_back, z_top),
            (u0, n_front, z0), (u1, n_front, z1), (u1_top, n_front, z_top), (u0_top, n_front, z_top),
        ]
        v = [bm.verts.new((wx + ux * uo + nx * no, wy + uy * uo + ny * no, zv)) for uo, no, zv in pts_s]
        for f_idxs in [(4, 5, 6, 7), (1, 0, 3, 2), (0, 1, 5, 4), (2, 3, 7, 6)]:
            f = bm.faces.new([v[k] for k in f_idxs])
            f.material_index = mat_idx


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


def add_cylinder(bm, cx, cy, z0, z1, r_bot, r_top=None, segs=20, mat_idx=0):
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


def is_party_wall(p1, p2, all_buildings, my_bid):
    if not all_buildings:
        return False
    mx, my = 0.5 * (p1[0] + p2[0]), 0.5 * (p1[1] + p2[1])
    for b in all_buildings:
        if b.get("id") == my_bid:
            continue
        poly = b.get("coords_xy", [])
        n_pts = len(poly)
        for i in range(n_pts - 1):
            q1, q2 = poly[i], poly[i + 1]
            dx, dy = q2[0] - q1[0], q2[1] - q1[1]
            L2 = dx * dx + dy * dy
            if L2 < 1e-4:
                continue
            t = max(0.0, min(1.0, ((mx - q1[0]) * dx + (my - q1[1]) * dy) / L2))
            proj_x = q1[0] + t * dx
            proj_y = q1[1] + t * dy
            if (mx - proj_x) ** 2 + (my - proj_y) ** 2 < 0.25:
                return True
    return False


def build_detailed_facade_wall(bm, p1, p2, z0, z1, bay_w=3.8, floor_h=3.6,
                               mat_wall=0, mat_glass=1, mat_frame=2, mat_sill=0,
                               recess=0.50, has_ground_shop=True, tripartite=False,
                               arched_windows=False, paired_top_arches=False,
                               basement_vents=False, bracketed_cornice=False,
                               has_top_cornice=True):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 1.8:
        add_wall_strip(bm, p1, p2, z0, z1, -0.15, 0.35, mat_idx=mat_wall)
        return
    ux, uy = dx / L, dy / L
    nx, ny = uy, -ux
    ang = math.atan2(uy, ux)

    add_wall_strip(bm, p1, p2, z0 + 0.05, z1 - 0.15, -recess, 0.14, mat_idx=mat_glass)

    n_bays = max(1, int(round(L / bay_w)))
    actual_bay = L / n_bays
    pier_w = min(0.92, actual_bay * 0.28)
    win_w = actual_bay - pier_w

    for i in range(n_bays + 1):
        w = pier_w * (1.25 if (i == 0 or i == n_bays) else 1.0)
        s = max(w * 0.5, min(L - w * 0.5, i * actual_bay))
        px = p1[0] + ux * s + nx * (-recess * 0.5 + 0.04)
        py = p1[1] + uy * s + ny * (-recess * 0.5 + 0.04)
        add_box(bm, (px, py, 0.5 * (z0 + z1)), (w, recess + 0.20, z1 - z0), angle_z=ang, mat_idx=mat_wall)
        # Ground-floor classical pilaster capital & base moulding when basement_vents is active
        if basement_vents:
            add_box(bm, (p1[0] + ux * s + nx * 0.12, p1[1] + uy * s + ny * 0.12, z0 + 4.15),
                    (w + 0.14, 0.18, 0.28), angle_z=ang, mat_idx=mat_sill)

    n_floors = max(1, int(round((z1 - z0) / floor_h)))
    actual_fh = (z1 - z0) / n_floors
    for fl in range(n_floors):
        fz0 = z0 + fl * actual_fh
        fz1 = fz0 + actual_fh
        spandrel_h = actual_fh * (0.22 if (fl == 0 and has_ground_shop) else 0.30)
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
        is_top_paired = (paired_top_arches and fl == n_floors - 1 and win_w > 1.6)

        for b in range(n_bays):
            sc = (b + 0.5) * actual_bay
            wx = p1[0] + ux * sc + nx * (-recess + 0.08)
            wy = p1[1] + uy * sc + ny * (-recess + 0.08)

            # Dark horizontal-slatted basement vent grilles below ground-floor sills
            if fl == 0 and basement_vents:
                add_box(bm, (p1[0] + ux * sc - nx * 0.08, p1[1] + uy * sc - ny * 0.08, fz0 + spandrel_h * 0.48),
                        (win_w * 0.78, 0.16, spandrel_h * 0.52), angle_z=ang, mat_idx=mat_frame)

            if is_top_paired:
                # Central stone colonnette dividing the top-floor bay into 2 paired round-arched windows
                add_box(bm, (p1[0] + ux * sc - nx * 0.12, p1[1] + uy * sc - ny * 0.12, win_zc),
                        (0.32, recess + 0.12, win_h), angle_z=ang, mat_idx=mat_wall)
                sub_w = (win_w - 0.32) * 0.5
                for sub_sign in (-1.0, 1.0):
                    sub_sc = sc + sub_sign * (sub_w * 0.5 + 0.16)
                    swx = p1[0] + ux * sub_sc
                    swy = p1[1] + uy * sub_sc
                    add_box(bm, (swx - nx * (recess - 0.08), swy - ny * (recess - 0.08), win_z0 + win_h * 0.48),
                            (sub_w, 0.10, 0.08), angle_z=ang, mat_idx=mat_frame)
                    add_arch_spandrel_fill(bm, swx, swy, win_z1 - sub_w * 0.45, fz1, sub_w * 0.52,
                                           sub_w * 0.46, sub_w * 0.42, 0.10, -recess + 0.05, ux, uy, nx, ny, segs=14, mat_idx=mat_wall)
                    add_smooth_arch_band(bm, swx, swy, win_z1 - sub_w * 0.45, sub_w * 0.44, sub_w * 0.40,
                                         0.16, 0.15, -0.05, ux, uy, nx, ny, segs=14, mat_idx=mat_sill)
            else:
                add_box(bm, (wx, wy, win_z0 + win_h * 0.52), (win_w, 0.10, 0.08), angle_z=ang, mat_idx=mat_frame)
                if tripartite and win_w > 1.8:
                    for off in (-win_w * 0.22, win_w * 0.22):
                        add_box(bm, (wx + ux * off, wy + uy * off, win_zc), (0.08, 0.12, win_h), angle_z=ang, mat_idx=mat_frame)
                else:
                    add_box(bm, (wx, wy, win_zc), (0.08, 0.12, win_h), angle_z=ang, mat_idx=mat_frame)

                if arched_windows and win_w > 1.2 and fl > 0:
                    add_arch_spandrel_fill(bm, p1[0] + ux * sc, p1[1] + uy * sc, win_z1 - 0.38, fz1,
                                           win_w * 0.52, win_w * 0.46, 0.36, 0.10, -recess + 0.05, ux, uy, nx, ny, segs=16, mat_idx=mat_wall)
                    add_smooth_arch_band(bm, p1[0] + ux * sc, p1[1] + uy * sc, win_z1 - 0.38,
                                         win_w * 0.45, 0.35, 0.18, 0.15, -0.05, ux, uy, nx, ny, segs=16, mat_idx=mat_sill)

    # Top entablature / cornice: architrave without top cap + cornice top at z1 + 0.16m
    if has_top_cornice:
        add_wall_strip(bm, p1, p2, z1 - 0.55, z1, 0.18, 0.46, mat_idx=mat_sill, cap_top=False)
        add_wall_strip(bm, p1, p2, z1 - 0.25, z1 + 0.16, 0.42, 0.84, mat_idx=mat_frame)
        if bracketed_cornice:
            n_br = max(4, int(L / 0.75))
            for bi in range(n_br):
                bs = (bi + 0.5) * (L / n_br)
                add_box(bm, (p1[0] + ux * bs + nx * 0.32, p1[1] + uy * bs + ny * 0.32, z1 - 0.38),
                        (0.14, 0.36, 0.38), angle_z=ang, mat_idx=mat_frame)



def build_pointe_a_calliere_eperon(col_owned, b_pac, pal):
    """Builds the iconic Pointe-à-Callière Éperon Building (87411702, 350 Place Royale):
    - Triangular white limestone ship-prow body (z = 0..15.8m)
    - Open upper limestone colonnade parapet (z = 15.8..19.2m) with 10 sky openings along Rue de la Commune
    - Cylindrical corner Prow Tower (cx=198.4, cy=-210.6, r=4.35m, z=0..24.5m)
    - Blue 'Le Monde en tête' vertical exhibition banner with gold crown graphic
    - Glazed steel belfry lantern, satellite dish, radial steel ribs, and tall silver louver spire (z=24.5..36.5m)
    - Rooftop barrel-vault skylights & twin 5-fan white HVAC cooling banks matching satellite_topdown.png."""
    bm = bmesh.new()
    # 0: limestone_white, 1: limestone_grey, 2: glass_dark, 3: glass_blue,
    # 4: bronze_dark, 5: metal_silver, 6: metal_white, 7: banner_blue,
    # 8: banner_gold, 9: white_paint, 10: roof_membrane
    mats = [
        pal["limestone_white"], pal["limestone_grey"], pal["glass_dark"], pal["glass_blue"],
        pal["bronze_dark"], pal["metal_silver"], pal["metal_white"], pal["banner_blue"],
        pal["banner_gold"], pal["white_paint"], pal["roof_membrane"]
    ]

    pts = ensure_ccw(b_pac["coords_xy"])
    core_pts = inset_polygon(pts, 1.5)
    add_prism(bm, core_pts, 0.0, 15.6 - 0.45, mat_side=2, mat_top=10)

    # 1. East Facade along Rue de la Commune Ouest: p_ne=(202.57, -208.33) -> p_se=(206.03, -262.80)
    p_ne = (202.57, -208.33)
    p_se = (206.03, -262.80)
    dx, dy = p_se[0] - p_ne[0], p_se[1] - p_ne[1]
    L_e = math.hypot(dx, dy)
    ux, uy = dx / L_e, dy / L_e
    # Outward normal pointing East (+X) toward Rue de la Commune: (-uy, ux) = (+0.998, +0.063)
    nx, ny = -uy, ux
    ang_e = math.atan2(uy, ux)

    # Recessed dark reflective glass curtain wall backing plane along East facade
    add_box(bm, (0.5 * (p_ne[0] + p_se[0]) - nx * 0.65, 0.5 * (p_ne[1] + p_se[1]) - ny * 0.65, 7.8),
            (L_e - 1.2, 0.18, 15.2), angle_z=ang_e, mat_idx=2)

    # Sculpted East Limestone Wall with:
    # - Deep vertical corner loggia slot at s = 2.2..6.2m (z = 0..15.2m)
    # - Tall double-height curtain-wall bays at s = 14.5..20.5m and s = 24.5..36.5m (z = 0..10.8m)
    # - 9 narrow 3rd-floor vertical slot windows at s = 10.0..38.0m (z = 11.8..14.3m)
    # First: solid limestone sections
    for s0, s1, z0, z1 in [
        (0.0, 2.2, 0.0, 15.8),      # Pier next to tower
        (2.2, 6.2, 14.8, 15.8),     # Lintel over tall corner loggia slot
        (6.2, 14.5, 0.0, 11.8),     # Solid limestone wall before first curtain wall
        (20.5, 24.5, 0.0, 11.8),    # Pier between curtain walls
        (36.5, L_e, 0.0, 15.8),     # Southern limestone wing
        (6.2, 36.5, 10.8, 11.8),    # Belt course below 3rd-floor slot windows
        (6.2, 36.5, 14.3, 15.8),    # Entablature band below open upper colonnade
    ]:
        sc = 0.5 * (s0 + s1)
        wx = p_ne[0] + ux * sc
        wy = p_ne[1] + uy * sc
        add_box(bm, (wx, wy, 0.5 * (z0 + z1)), (s1 - s0, 0.62, z1 - z0), angle_z=ang_e, mat_idx=0)

    # Dark soffit ceiling & inner side wall inside the tall corner loggia slot (s = 2.2..6.2m)
    log_x = p_ne[0] + ux * 4.2 - nx * 0.95
    log_y = p_ne[1] + uy * 4.2 - ny * 0.95
    add_box(bm, (log_x, log_y, 14.6), (4.0, 1.9, 0.25), angle_z=ang_e, mat_idx=4)
    add_box(bm, (p_ne[0] + ux * 4.2 - nx * 1.85, p_ne[1] + uy * 4.2 - ny * 1.85, 7.4),
            (4.0, 0.25, 14.8), angle_z=ang_e, mat_idx=1)

    # Piers between the 9 narrow 3rd-floor vertical slot windows (z = 11.8..14.3m, s = 6.2..36.5m)
    n_slots = 9
    slot_span = (36.5 - 6.2) / n_slots
    for si in range(n_slots + 1):
        s_p = 6.2 + si * slot_span
        add_box(bm, (p_ne[0] + ux * s_p, p_ne[1] + uy * s_p, 13.05),
                (slot_span * 0.58, 0.62, 2.5), angle_z=ang_e, mat_idx=0)

    # Curtain-wall mullions in the two tall double-height glazed bays (s = 14.5..20.5m, 24.5..36.5m)
    for s0, s1 in [(14.5, 20.5), (24.5, 36.5)]:
        nb = max(2, int((s1 - s0) / 2.0))
        for bi in range(nb + 1):
            sm = s0 + (bi / nb) * (s1 - s0)
            add_box(bm, (p_ne[0] + ux * sm - nx * 0.45, p_ne[1] + uy * sm - ny * 0.45, 5.4),
                    (0.10, 0.22, 10.8), angle_z=ang_e, mat_idx=4)
        for zm in (3.2, 6.4, 9.2):
            sc = 0.5 * (s0 + s1)
            add_box(bm, (p_ne[0] + ux * sc - nx * 0.45, p_ne[1] + uy * sc - ny * 0.45, zm),
                    (s1 - s0, 0.22, 0.10), angle_z=ang_e, mat_idx=4)

    # Subtle horizontal limestone coursing across the East wall
    for zr in (3.4, 6.6, 9.8, 14.6):
        add_box(bm, (0.5 * (p_ne[0] + p_se[0]) + nx * 0.26, 0.5 * (p_ne[1] + p_se[1]) + ny * 0.26, zr),
                (L_e, 0.08, 0.06), angle_z=ang_e, mat_idx=0)

    # OPEN UPPER COLONNADE PARAPET (z = 15.8..19.2m) along East & NW facades so blue sky shines through!
    n_col_openings = 11
    col_span = (L_e - 4.0) / n_col_openings
    for ci in range(n_col_openings + 1):
        sc = 2.2 + ci * col_span
        add_box(bm, (p_ne[0] + ux * sc, p_ne[1] + uy * sc, 17.3),
                (0.75, 0.68, 3.0), angle_z=ang_e, mat_idx=0)
        # Inner steel guardrail bar at bottom of opening
        if ci < n_col_openings:
            sm = sc + col_span * 0.5
            add_box(bm, (p_ne[0] + ux * sm, p_ne[1] + uy * sm, 16.4),
                    (col_span, 0.10, 0.10), angle_z=ang_e, mat_idx=4)
    # Continuous top stone coping beam over the open colonnade (z = 18.8..19.4m)
    add_box(bm, (0.5 * (p_ne[0] + p_se[0]), 0.5 * (p_ne[1] + p_se[1]), 19.1),
            (L_e - 1.5, 0.78, 0.62), angle_z=ang_e, mat_idx=0)

    # 2. NW Facade along Place Royale / Place d'Youville (CCW edge: N -> SW so outward normal points NW!)
    p_nw_n = (189.04, -215.20)
    p_sw = (163.03, -254.12)
    build_detailed_facade_wall(bm, p_nw_n, p_sw, 0.0, 16.2,
                               bay_w=4.4, floor_h=4.0, mat_wall=0, mat_glass=2, mat_frame=4,
                               mat_sill=0, recess=0.52, has_ground_shop=True, has_top_cornice=False)
    # South / SW Facade along Place d'Youville (CCW edge: SW -> SE so outward normal points South!)
    build_detailed_facade_wall(bm, (163.30, -254.42), p_se, 0.0, 16.2,
                               bay_w=4.6, floor_h=4.0, mat_wall=0, mat_glass=2, mat_frame=4,
                               mat_sill=0, recess=0.52, has_ground_shop=True, has_top_cornice=False)
    # Add upper parapet coping along NW and South facades (z = 16.2..17.6m)
    add_wall_strip(bm, p_nw_n, p_sw, 16.0, 17.4, -0.10, 0.65, mat_idx=0)
    add_wall_strip(bm, (163.30, -254.42), p_se, 16.0, 17.4, -0.10, 0.65, mat_idx=0)

    # Horizontal steel floor beams inside the tall 3-story recessed vertical niche left of the Prow Tower (s = 2.2..6.2m)
    for zn in (3.8, 7.6, 11.4):
        add_box(bm, (p_ne[0] + ux * 4.2 - nx * 0.45, p_ne[1] + uy * 4.2 - ny * 0.45, zn),
                (4.0, 0.35, 0.28), angle_z=ang_e, mat_idx=4)

    # 3. CYLINDRICAL PROW TOWER & BELFRY LANTERN (cx=198.45, cy=-210.65, r=4.35m)
    tcx, tcy, tr = 198.45, -210.65, 4.35
    # Main cylindrical limestone tower shaft (z = 0..19.5m) + recessed dark lookout drum (z = 19.5..22.3m) + upper drum (z = 22.3..24.4m)
    add_cylinder(bm, tcx, tcy, 0.0, 19.5, tr, tr, segs=32, mat_idx=0)
    add_cylinder(bm, tcx, tcy, 19.5, 22.3, tr - 0.68, tr - 0.68, segs=28, mat_idx=2)
    add_cylinder(bm, tcx, tcy, 22.3, 24.4, tr, tr, segs=32, mat_idx=0)

    # Build the z = 19.5..22.3m cylindrical stone wall with 2 crisp rectangular lookout loggia cutouts
    # on the upper-left of the drum (at [-6..+8 deg] and [+14..+28 deg], directly above the rooftop colonnade in Pointe_a_Calliere_Prow_Tower.jpg!)
    n_drum_segs = 36
    for di in range(n_drum_segs):
        deg0 = -180.0 + di * (360.0 / n_drum_segs)
        deg_mid = deg0 + 5.0
        if (-6.0 <= deg_mid <= 8.0) or (14.0 <= deg_mid <= 28.0):
            rad_m = math.radians(deg_mid)
            add_box(bm, (tcx + math.cos(rad_m) * (tr - 0.14), tcy + math.sin(rad_m) * (tr - 0.14), 20.15),
                    (0.10, 0.85, 0.10), angle_z=rad_m, mat_idx=4)
            continue
        rad_m = math.radians(deg_mid)
        px = tcx + math.cos(rad_m) * (tr - 0.22)
        py = tcy + math.sin(rad_m) * (tr - 0.22)
        add_box(bm, (px, py, 20.9), (0.52, 0.88, 2.8), angle_z=rad_m, mat_idx=0)

    # Dark rectangular acoustic louver grille on upper-right stone drum (z = 20.2..22.2m, ang = 68 deg)
    lv_ang = math.radians(68.0)
    add_box(bm, (tcx + math.cos(lv_ang) * (tr - 0.04), tcy + math.sin(lv_ang) * (tr - 0.04), 21.2),
            (0.24, 1.25, 1.95), angle_z=lv_ang, mat_idx=4)

    # Subtle horizontal limestone rings around cylindrical tower
    for zr in (6, 12, 18):
        add_cylinder(bm, tcx, tcy, float(zr), float(zr) + 0.06, tr + 0.02, tr + 0.02, segs=32, mat_idx=0)

    # Tall narrow ground-floor entrance slot on NE face of cylinder (z = 0..4.2m)
    slot_ang = math.radians(48.0)
    add_box(bm, (tcx + math.cos(slot_ang) * (tr - 0.08), tcy + math.sin(slot_ang) * (tr - 0.08), 2.1),
            (0.45, 0.55, 4.2), angle_z=slot_ang, mat_idx=4)

    # Vibrant Royal-Blue Vertical Exhibition Banner ("Le Monde en tête") on NE face of Prow Tower
    # Spanning H2..H3, V5 in Cam 1 (z = 6.8..16.2m, angular span 24..62 deg)
    for bi in range(13):
        b_ang = math.radians(24.0 + bi * 3.1)
        bx = tcx + math.cos(b_ang) * (tr + 0.08)
        by = tcy + math.sin(b_ang) * (tr + 0.08)
        add_box(bm, (bx, by, 11.5), (0.06, 0.38, 9.4), angle_z=b_ang, mat_idx=7)

    # Crisp white header typography bars ("Le Monde / en tête") at top of blue banner (z = 14.3..15.6m)
    for tz, tw_deg in [(15.45, 22.0), (14.85, 28.0), (14.25, 19.0), (7.55, 24.0)]:
        for ti in range(6):
            t_ang = math.radians(43.0 + (ti - 2.5) * (tw_deg / 6.0))
            tx = tcx + math.cos(t_ang) * (tr + 0.12)
            ty = tcy + math.sin(t_ang) * (tr + 0.12)
            add_box(bm, (tx, ty, tz), (0.05, 0.34, 0.24), angle_z=t_ang, mat_idx=9)

    # Sculpted ornate Silver & Gold Headdress/Crown Emblem in center of blue banner (z = 10.0..13.6m)
    for ci in range(9):
        c_ang = math.radians(31.0 + ci * 3.0)
        cx_b = tcx + math.cos(c_ang) * (tr + 0.13)
        cy_b = tcy + math.sin(c_ang) * (tr + 0.13)
        add_box(bm, (cx_b, cy_b, 10.8), (0.07, 0.30, 0.95), angle_z=c_ang, mat_idx=8)
        plume_h = 1.95 - abs(ci - 4) * 0.22
        add_box(bm, (cx_b, cy_b, 11.5 + plume_h * 0.5), (0.06, 0.22, plume_h), angle_z=c_ang, mat_idx=5 if ci % 2 == 0 else 9)

    # Cantilevered Radial Steel Canopy Ribs on NW side of Prow Tower (z = 15.8m, visible in Prow_Tower & satellite)
    for r_deg in range(115, 185, 12):
        r_ang = math.radians(r_deg)
        rx = tcx + math.cos(r_ang) * (tr + 2.2)
        ry = tcy + math.sin(r_ang) * (tr + 2.2)
        add_box(bm, (rx, ry, 15.8), (4.6, 0.14, 0.22), angle_z=r_ang, mat_idx=5)

    # Upper Glazed Steel Belfry Lantern, Catwalk Cage, Radome & Tall Silver Lattice Spire (z = 24.4..36.8m)
    add_cylinder(bm, tcx, tcy, 24.4, 28.8, 3.05, 3.05, segs=20, mat_idx=3)
    # Open dark-steel belfry structural cage frames + external catwalk rings around the lantern
    for fi in range(10):
        fang = 2.0 * math.pi * fi / 10.0
        fx = tcx + math.cos(fang) * 3.35
        fy = tcy + math.sin(fang) * 3.35
        add_box(bm, (fx, fy, 26.8), (0.12, 0.12, 4.8), angle_z=fang, mat_idx=4)
    for z_ring in (24.6, 26.6, 28.8):
        add_cylinder(bm, tcx, tcy, z_ring, z_ring + 0.18, 3.45, 3.45, segs=20, mat_idx=4)
    # White cylindrical microwave/radar dish antenna on NW face of belfry (z = 26.5..27.9m)
    d_ang = math.radians(118.0)
    add_cylinder(bm, tcx + math.cos(d_ang) * 3.65, tcy + math.sin(d_ang) * 3.65, 26.2, 27.8, 0.68, 0.68, segs=18, mat_idx=6)
    # Vertical limestone spine pier + metallic silver louver spire rising to z = 36.8m
    sp_ang = math.radians(135.0)
    spx = tcx + math.cos(sp_ang) * 2.8
    spy = tcy + math.sin(sp_ang) * 2.8
    add_box(bm, (spx, spy, 27.5), (1.35, 1.85, 13.0), angle_z=sp_ang, mat_idx=0)
    # Tall silver lattice/louver spire screen at very top (z = 29.0..37.2m)
    add_box(bm, (tcx, tcy, 33.1), (0.35, 2.45, 8.2), angle_z=math.radians(45.0), mat_idx=5)
    for lvi in range(7):
        off = -1.05 + lvi * 0.35
        ca, sa = math.cos(math.radians(45.0)), math.sin(math.radians(45.0))
        add_box(bm, (tcx - off * sa, tcy + off * ca, 33.1), (0.45, 0.08, 8.4), angle_z=math.radians(45.0), mat_idx=6)

    # 4. Rooftop Details visible in satellite_topdown.png & MTL-VM-0015_snapshot.png:
    # - 5 Barrel-vaulted glass skylights along the East roof edge
    for ski in range(5):
        sk_s = 12.0 + ski * 7.2
        skx = p_ne[0] + ux * sk_s - nx * 4.2
        sky = p_ne[1] + uy * sk_s - ny * 4.2
        add_box(bm, (skx, sky, 16.4), (6.2, 3.2, 1.4), angle_z=ang_e, mat_idx=3)
        add_box(bm, (skx, sky, 17.2), (6.2, 1.8, 0.6), angle_z=ang_e, mat_idx=5)
    # - 2 White 5-fan HVAC chiller banks + square mechanical penthouse in center of triangular roof
    for hy_off in (-234.5, -240.5):
        add_box(bm, (188.5, hy_off, 16.8), (11.5, 2.8, 2.2), angle_z=math.radians(-10.0), mat_idx=6)
        for fi in range(5):
            fx = 184.1 + fi * 2.2
            add_cylinder(bm, fx, hy_off - 0.4 * (fi - 2), 17.8, 18.1, 0.85, 0.85, segs=14, mat_idx=4)
    add_box(bm, (184.5, -247.5, 17.4), (12.5, 11.5, 3.4), angle_z=math.radians(-10.0), mat_idx=0)
    add_box(bm, (184.5, -247.5, 19.15), (11.8, 10.8, 0.2), angle_z=math.radians(-10.0), mat_idx=10)

    mesh = bpy.data.meshes.new("Bldg_87411702_PointeACalliere")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_87411702_PointeACalliere", mesh)
    link_obj(obj, col_owned)


def build_custom_house_and_place_royale(col_owned, b_custom, b_civic, b_688, pal, all_buildings=None):
    """Builds the Neoclassical Old Custom House (Pavillon de l'Ancienne-Douane, 87411690) featured in
    Place_Royale_Custom_House.jpg, plus the Place Royale civic wing (87411683 & 87411688) and
    the stepped Place Royale retaining walls & obelisk monument."""
    bm = bmesh.new()
    # 0: custom_house_ashlar (smooth pale grey dressed limestone), 1: limestone_white,
    # 2: limestone_dark (rusticated basement plinth), 3: glass_dark,
    # 4: frame_green, 5: bronze_dark, 6: slate_dark, 7: copper_green, 8: roof_membrane
    mats = [
        pal["custom_house_ashlar"], pal["limestone_white"], pal["limestone_dark"], pal["glass_dark"],
        pal["frame_green"], pal["bronze_dark"], pal["slate_dark"], pal["copper_green"], pal["roof_membrane"]
    ]

    # 1. Old Custom House (Ancienne-Douane, 87411690)
    if b_custom:
        pts = ensure_ccw(b_custom["coords_xy"])
        core_pts = inset_polygon(pts, 1.3)
        add_prism(bm, core_pts, 0.0, 12.0 - 0.45, mat_side=3, mat_top=6)

        for i in range(len(pts)):
            pa, pb = pts[i], pts[(i + 1) % len(pts)]
            L_seg = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
            if L_seg < 5.0:
                add_wall_strip(bm, pa, pb, 0.0, 12.2, -0.1, 0.4, mat_idx=0)
                continue
            dx, dy = pb[0] - pa[0], pb[1] - pa[1]
            ux, uy = dx / L_seg, dy / L_seg
            nx, ny = uy, -ux
            ang = math.atan2(uy, ux)

            # Recessed dark reflective glass backing plane
            add_wall_strip(bm, pa, pb, 0.2, 11.8, -0.48, 0.14, mat_idx=3)

            # Channel-rusticated grey stone basement plinth (z = 0..2.18m)
            add_wall_strip(bm, pa, pb, 0.0, 2.18, -0.06, 0.58, mat_idx=2)

            # 7 bays along the 22m Neoclassical facade:
            # Bays 0, 1 (left), Bay 2 (tall entrance door + 6-pane glazed transom), Bays 3, 4, 5 (central 3-window Palladian avant-corps), Bay 6 (right)
            n_bays = 7 if L_seg > 18.0 else 4
            bw = L_seg / n_bays
            for bi in range(n_bays + 1):
                s = bi * bw
                is_center = (n_bays == 7 and 3 <= bi <= 6)
                pw = bw * (0.34 if is_center else 0.42)
                proj_out = 0.16 if is_center else 0.0
                px = pa[0] + ux * s + nx * (-0.18 + proj_out * 0.5)
                py = pa[1] + uy * s + ny * (-0.18 + proj_out * 0.5)
                # Basement portion of pier in rusticated dark stone (z = 0..2.18m), upper shaft in smooth pale grey ashlar (z = 2.18..12.2m)
                add_box(bm, (px, py, 1.09), (pw, 0.60 + proj_out, 2.18), angle_z=ang, mat_idx=2)
                add_box(bm, (px, py, 7.19), (pw, 0.58 + proj_out, 10.02), angle_z=ang, mat_idx=0)
                # Carved limestone console bracket at top of 1st-floor central piers (z = 5.35..5.95m)
                if is_center:
                    add_box(bm, (pa[0] + ux * s + nx * 0.28, pa[1] + uy * s + ny * 0.28, 5.65),
                            (0.32, 0.38, 0.58), angle_z=ang, mat_idx=1)

            for bi in range(n_bays):
                sc = (bi + 0.5) * bw
                wx = pa[0] + ux * sc
                wy = pa[1] + uy * sc
                is_door = (n_bays == 7 and bi == 2)
                is_palladian_arch = (n_bays == 7 and bi == 4)

                # Basement window mullion or recessed dark-green timber entrance door + 6-pane glazed transom
                if not is_door:
                    add_box(bm, (wx - nx * 0.12, wy - ny * 0.12, 0.98), (0.08, 0.20, 1.00), angle_z=ang, mat_idx=4)
                    add_box(bm, (wx - nx * 0.12, wy - ny * 0.12, 0.98), (bw * 0.58, 0.16, 0.06), angle_z=ang, mat_idx=4)
                else:
                    # Stone entrance threshold step + recessed dark-green paneled double door (z = 0.20..3.65m)
                    add_box(bm, (wx + nx * 0.16, wy + ny * 0.16, 0.22), (bw * 0.72, 0.36, 0.18), angle_z=ang, mat_idx=1)
                    add_box(bm, (wx - nx * 0.28, wy - ny * 0.28, 1.92), (bw * 0.62, 0.18, 3.45), angle_z=ang, mat_idx=4)
                    # Prominent green wooden transom bar at z = 3.72m + 6-pane glazed transom window (z = 3.78..5.55m)
                    add_box(bm, (wx - nx * 0.20, wy - ny * 0.20, 3.72), (bw * 0.66, 0.24, 0.14), angle_z=ang, mat_idx=4)
                    for t_off in (-bw * 0.26, -bw * 0.09, bw * 0.09, bw * 0.26):
                        add_box(bm, (wx + ux * t_off - nx * 0.34, wy + uy * t_off - ny * 0.34, 4.66),
                                (0.06, 0.12, 1.76), angle_z=ang, mat_idx=4)
                    for tz_r in (4.35, 4.95, 5.48):
                        add_box(bm, (wx - nx * 0.34, wy - ny * 0.34, tz_r),
                                (bw * 0.58, 0.12, 0.06), angle_z=ang, mat_idx=4)

                # Spandrel between 1st & 2nd floor (z = 5.55..6.65m)
                add_box(bm, (wx - nx * 0.12, wy - ny * 0.12, 6.10), (bw, 0.55, 1.10), angle_z=ang, mat_idx=0)

                # Spandrel above 2nd floor:
                # For the central Palladian arch window (bi == 4), carve a true smooth semicircular arch opening!
                if is_palladian_arch:
                    z_spring = 9.45
                    r_arch_w = bw * 0.31
                    r_arch_h = 1.05
                    # Smooth radial spandrel fill from z_spring (9.45m) up to 11.65m
                    add_arch_spandrel_fill(bm, wx, wy, z_spring, 11.65, bw * 0.36, r_arch_w, r_arch_h,
                                           0.16, -0.42, ux, uy, nx, ny, segs=28, mat_idx=0)
                    # Smooth 28-segment semicircular stone arch ring + projecting keystone at crown
                    add_smooth_arch_band(bm, wx, wy, z_spring, r_arch_w - 0.02, r_arch_h - 0.02,
                                         0.26, 0.24, -0.10, ux, uy, nx, ny, segs=28, mat_idx=1)
                    add_box(bm, (wx + nx * 0.26, wy + ny * 0.26, z_spring + r_arch_h + 0.14),
                            (0.28, 0.18, 0.36), angle_z=ang, mat_idx=1)
                    # Smooth inner green fanlight arch ring + springline transom bar
                    add_smooth_arch_band(bm, wx, wy, z_spring, r_arch_w - 0.10, r_arch_h - 0.10,
                                         0.08, -0.28, -0.40, ux, uy, nx, ny, segs=24, mat_idx=4)
                    add_box(bm, (wx - nx * 0.34, wy - ny * 0.34, z_spring), (bw * 0.62, 0.14, 0.09), angle_z=ang, mat_idx=4)
                    z2_top = z_spring
                else:
                    z2_top = 9.85
                    add_box(bm, (wx - nx * 0.12, wy - ny * 0.12, 0.5 * (z2_top + 11.65)),
                            (bw, 0.55, 11.65 - z2_top), angle_z=ang, mat_idx=0)

                # Projecting stone sills on 1st & 2nd floors
                if not is_door:
                    add_box(bm, (wx + nx * 0.14, wy + ny * 0.14, 2.22), (bw * 0.68, 0.28, 0.14), angle_z=ang, mat_idx=1)
                add_box(bm, (wx + nx * 0.14, wy + ny * 0.14, 6.62), (bw * 0.68, 0.28, 0.14), angle_z=ang, mat_idx=1)

                # Multi-pane dark forest-green window sashes & prominent central horizontal meeting rail on 1st & 2nd floors
                win_ranges = [(6.65, z2_top)] if is_door else [(2.25, 5.55), (6.65, z2_top)]
                for z_w0, z_w1 in win_ranges:
                    w_h = z_w1 - z_w0
                    w_zc = 0.5 * (z_w0 + z_w1)
                    for s_off in (-bw * 0.20, bw * 0.20):
                        add_box(bm, (wx + ux * s_off - nx * 0.35, wy + uy * s_off - ny * 0.35, w_zc),
                                (0.06, 0.10, w_h), angle_z=ang, mat_idx=4)
                    # Prominent central horizontal sash meeting rail at w_zc
                    add_box(bm, (wx - nx * 0.33, wy - ny * 0.33, w_zc),
                            (bw * 0.58, 0.14, 0.10), angle_z=ang, mat_idx=4)

            # Continuous 2nd-floor stone belt course + projecting central Palladian entablature at z = 6.0m
            add_wall_strip(bm, pa, pb, 5.92, 6.28, 0.16, 0.42, mat_idx=1)
            if n_bays == 7:
                sc_p = 4.5 * bw
                add_box(bm, (pa[0] + ux * sc_p + nx * 0.28, pa[1] + uy * sc_p + ny * 0.28, 6.18),
                        (bw * 3.15, 0.55, 0.48), angle_z=ang, mat_idx=1)

            # Projecting Neoclassical roofline cornice (z = 11.65..12.35m)
            add_wall_strip(bm, pa, pb, 11.65, 12.35, 0.34, 0.78, mat_idx=1)

            # Classical Triangular Limestone Pediment over the central 3 bays (visible in both Cam 2 & Cam 3!)
            if n_bays == 7:
                sc_ped = 4.5 * bw
                px_c = pa[0] + ux * sc_ped
                py_c = pa[1] + uy * sc_ped
                ped_half = bw * 1.62
                ped_z0, ped_z1 = 12.30, 14.55
                v_ped = [
                    bm.verts.new((px_c - ux * ped_half - nx * 0.25, py_c - uy * ped_half - ny * 0.25, ped_z0)),
                    bm.verts.new((px_c + ux * ped_half - nx * 0.25, py_c + uy * ped_half - ny * 0.25, ped_z0)),
                    bm.verts.new((px_c - nx * 0.25, py_c - ny * 0.25, ped_z1)),
                    bm.verts.new((px_c - ux * ped_half + nx * 0.28, py_c - uy * ped_half + ny * 0.28, ped_z0)),
                    bm.verts.new((px_c + ux * ped_half + nx * 0.28, py_c + uy * ped_half + ny * 0.28, ped_z0)),
                    bm.verts.new((px_c + nx * 0.28, py_c + ny * 0.28, ped_z1)),
                ]
                for f_p, m_p in [
                    ((3, 4, 5), 0), ((1, 0, 2), 0),
                    ((0, 3, 5, 2), 1), ((4, 1, 2, 5), 1),
                ]:
                    f = bm.faces.new([v_ped[k] for k in f_p])
                    f.material_index = m_p

        # Pitched dark-slate hipped roof (z = 12.2..15.2m) + 2 tall limestone chimney stacks (visible in Cam 2 & Cam 3!)
        rcx = sum(p[0] for p in pts) / len(pts)
        rcy = sum(p[1] for p in pts) / len(pts)
        r_ang_ch = math.radians(-21.5)
        ca_ch, sa_ch = math.cos(r_ang_ch), math.sin(r_ang_ch)
        hip_bot = [(-10.4, -7.8, 12.2), (10.4, -7.8, 12.2), (10.4, 7.8, 12.2), (-10.4, 7.8, 12.2)]
        hip_top = [(-5.5, -0.4, 15.1), (5.5, -0.4, 15.1), (5.5, 0.4, 15.1), (-5.5, 0.4, 15.1)]
        vb_h = [bm.verts.new((rcx + lx * ca_ch - ly * sa_ch, rcy + lx * sa_ch + ly * ca_ch, lz)) for lx, ly, lz in hip_bot]
        vt_h = [bm.verts.new((rcx + lx * ca_ch - ly * sa_ch, rcy + lx * sa_ch + ly * ca_ch, lz)) for lx, ly, lz in hip_top]
        for hi in range(4):
            hj = (hi + 1) % 4
            fh = bm.faces.new((vb_h[hi], vb_h[hj], vt_h[hj], vt_h[hi]))
            fh.material_index = 6
        fht = bm.faces.new(vt_h)
        fht.material_index = 6
        for ch_x, ch_y in [(164.8, -147.8), (151.2, -143.2)]:
            add_box(bm, (ch_x, ch_y, 14.2), (1.45, 1.15, 4.4), angle_z=r_ang_ch, mat_idx=0)
            add_box(bm, (ch_x, ch_y, 16.45), (1.72, 1.38, 0.28), angle_z=r_ang_ch, mat_idx=1)

    # 2. Place Royale NW Civic Wing (87411683 & 87411688) visible on right of Pointe_a_Calliere_Prow_Tower.jpg
    for b_w, hw, fh in [(b_civic, 16.7, 3.6), (b_688, 13.8, 3.45)]:
        if not b_w:
            continue
        pts = ensure_ccw(b_w["coords_xy"])
        core_pts = inset_polygon(pts, 1.3)
        add_prism(bm, core_pts, 0.0, hw - 0.45, mat_side=3, mat_top=8)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 6.0 and not is_party_wall(p1, p2, all_buildings, b_w["id"]):
                build_detailed_facade_wall(bm, p1, p2, 0.0, hw, bay_w=3.8, floor_h=fh,
                                           mat_wall=1, mat_glass=3, mat_frame=5, mat_sill=0,
                                           recess=0.48, has_ground_shop=True)
            else:
                add_wall_strip(bm, p1, p2, 0.0, hw, -0.1, 0.35, mat_idx=1, cap_top=False)

    # 3. Place Royale Low Limestone Retaining Wall with 3 Recessed Bench Alcoves & Slender Obelisk Monument
    # Visible in the right foreground of Pointe_a_Calliere_Prow_Tower.jpg
    pr_ang = math.radians(52.0)
    ux_pr, uy_pr = math.cos(pr_ang), math.sin(pr_ang)
    nx_pr, ny_pr = uy_pr, -ux_pr
    wall_cx, wall_cy = 205.2, -197.8
    # Back spine of retaining wall + continuous top coping slab
    add_box(bm, (wall_cx - nx_pr * 0.22, wall_cy - ny_pr * 0.22, 0.58), (14.6, 0.52, 0.96), angle_z=pr_ang, mat_idx=0)
    add_box(bm, (wall_cx, wall_cy, 1.12), (14.9, 1.05, 0.14), angle_z=pr_ang, mat_idx=1)
    # Projecting piers leaving 3 true recessed bench alcoves at ni = -3.6, -1.2, +1.2
    for s_p0, s_p1 in [(-7.3, -4.45), (-2.75, -2.05), (-0.35, 0.35), (2.05, 7.3)]:
        sc_w = 0.5 * (s_p0 + s_p1)
        add_box(bm, (wall_cx + ux_pr * sc_w + nx_pr * 0.15, wall_cy + uy_pr * sc_w + ny_pr * 0.15, 0.58),
                (s_p1 - s_p0, 0.44, 0.96), angle_z=pr_ang, mat_idx=0)
    for ni in (-3.6, -1.2, 1.2):
        # Dark recessed back plaque + cantilevered stone bench seat at z = 0.46m inside each alcove
        add_box(bm, (wall_cx + ux_pr * ni + nx_pr * 0.02, wall_cy + uy_pr * ni + ny_pr * 0.02, 0.62),
                (1.65, 0.08, 0.58), angle_z=pr_ang, mat_idx=5)
        add_box(bm, (wall_cx + ux_pr * ni + nx_pr * 0.22, wall_cy + uy_pr * ni + ny_pr * 0.22, 0.46),
                (1.68, 0.42, 0.10), angle_z=pr_ang, mat_idx=1)

    # Slender Place Royale Obelisk Monument (Monument aux Pionniers) on stepped white pedestal behind foreground lamppost
    ob_x, ob_y = 200.8, -193.8
    add_box(bm, (ob_x, ob_y, 0.45), (3.4, 3.4, 0.60), angle_z=pr_ang, mat_idx=1)
    add_box(bm, (ob_x, ob_y, 1.05), (2.2, 2.2, 0.65), angle_z=pr_ang, mat_idx=1)
    add_box(bm, (ob_x, ob_y, 1.75), (1.15, 1.15, 0.85), angle_z=pr_ang, mat_idx=1)
    add_cylinder(bm, ob_x, ob_y, 2.15, 5.55, 0.34, 0.19, segs=4, mat_idx=1)
    add_cylinder(bm, ob_x, ob_y, 5.55, 5.95, 0.19, 0.02, segs=4, mat_idx=1)


    mesh = bpy.data.meshes.new("Bldg_CustomHouse_And_PlaceRoyale")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_CustomHouse_And_PlaceRoyale", mesh)
    link_obj(obj, col_owned)


def build_rue_mcgill_and_saint_pierre_row(col_owned, b_by_id, pal, all_buildings=None):
    """Builds the historic Victorian limestone row along Rue Saint-Pierre / Place d'Youville
    (339870137, 339870338, 339870474, 339870490, 339873678, 339873679) featured in Rue_McGill_Corner_Approach.jpg:
    - Foreground left 4-story limestone building (339870137/339870338) with paired 4th-floor round-arched windows,
      bracketed dark cornice, ground-floor pilasters, and basement louvered vent grilles
    - Mid-block 2.5-story grey stone townhouse (339870474, eave z=9.6m) with pitched slate roof & dormers
    - Taller 4-story neighbor (339870490, z=17.2m) with exposed weathered red-brick upper side party wall!"""
    bm = bmesh.new()
    # 0: limestone_grey, 1: limestone_cream, 2: glass_dark, 3: frame_green,
    # 4: bronze_dark, 5: slate_dark, 6: wood_plywood, 7: car_orange, 8: door_blue, 9: roof_membrane, 10: brick_red
    mats = [
        pal["limestone_grey"], pal["limestone_cream"], pal["glass_dark"], pal["frame_green"],
        pal["bronze_dark"], pal["slate_dark"], pal["wood_plywood"], pal["car_orange"],
        pal["door_blue"], pal["roof_membrane"], pal["brick_red"]
    ]

    # (bid, height, mat_wall, arched_windows, paired_top_arches, basement_vents, bracketed_cornice)
    row_specs = [
        (339869984, 17.5, 0, False, True, True, True),
        (339870137, 17.8, 0, False, True, True, True),
        (339870338, 17.8, 0, False, True, True, True),
        (339870474, 9.6,  0, False, False, False, True),  # 2.5-story grey stone townhouse with pitched roof!
        (339870490, 17.2, 1, True,  False, False, True),  # 4-story neighbor with exposed red-brick south party wall!
        (339873678, 17.2, 0, True,  False, False, True),
        (339873679, 16.5, 1, True,  False, False, True),
    ]
    for bid, h_b, m_wall, is_arched, is_paired_top, has_vents, has_brackets in row_specs:
        b = b_by_id.get(bid)
        if not b:
            continue
        pts = ensure_ccw(b["coords_xy"])
        core_pts = inset_polygon(pts, 1.3)
        add_prism(bm, core_pts, 0.0, h_b - 0.45, mat_side=2, mat_top=5 if bid == 339870474 else 9)
        fl_h = 4.2 if bid == 339870474 else 4.1
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            # Check if this is the SW-facing side party wall of 339870490 above the 2.5-story townhouse (339870474)
            is_south_party_wall = (bid == 339870490 and dy < -4.0 and abs(dx) > 6.0)
            if is_south_party_wall:
                add_wall_strip(bm, p1, p2, 0.0, 9.6, -0.05, 0.38, mat_idx=m_wall, cap_top=False)
                add_wall_strip(bm, p1, p2, 9.6, h_b, 0.08, 0.42, mat_idx=10)  # Exposed weathered red-brick party wall!
                continue
            if is_party_wall(p1, p2, all_buildings, bid):
                add_wall_strip(bm, p1, p2, 0.0, h_b, -0.05, 0.38, mat_idx=m_wall, cap_top=False)
                continue
            if L >= 4.8:
                build_detailed_facade_wall(bm, p1, p2, 0.0, h_b, bay_w=3.6, floor_h=fl_h,
                                           mat_wall=m_wall, mat_glass=2, mat_frame=3, mat_sill=0,
                                           recess=0.48, has_ground_shop=True, tripartite=True,
                                           arched_windows=is_arched, paired_top_arches=is_paired_top,
                                           basement_vents=has_vents, bracketed_cornice=has_brackets)
                # Prominent 1st-floor entablature cornice at z = 4.45..4.90m
                add_wall_strip(bm, p1, p2, 4.45, 4.90, 0.26, 0.62, mat_idx=0)
            else:
                add_wall_strip(bm, p1, p2, 0.0, h_b, -0.1, 0.35, mat_idx=m_wall)

        # Pitched dark-slate gable/dormer roof on the 2.5-story mid-block townhouse (339870474, z = 9.6..12.3m)
        if bid == 339870474:
            tcx = sum(p[0] for p in pts) / len(pts)
            tcy = sum(p[1] for p in pts) / len(pts)
            tang = math.radians(67.5)
            add_box(bm, (tcx, tcy, 10.95), (9.8, 14.5, 2.4), angle_z=tang, mat_idx=5)
            # 2 dormer windows on the street-facing slope of the pitched roof
            for d_off in (-2.4, 2.2):
                dx_d = tcx + math.cos(tang) * d_off + math.sin(tang) * 4.2
                dy_d = tcy + math.sin(tang) * d_off - math.cos(tang) * 4.2
                add_box(bm, (dx_d, dy_d, 10.85), (1.45, 1.85, 1.65), angle_z=tang, mat_idx=0)
                add_box(bm, (dx_d + math.sin(tang) * 0.85, dy_d - math.cos(tang) * 0.85, 10.80),
                        (0.95, 0.16, 1.15), angle_z=tang, mat_idx=2)

    # Specific street-level details on 339870474 (mid-block 2.5-story townhouse):
    # Left dark wrought-iron carriage gate + center bright blue entrance door at (131.6, -262.2)
    ang_ab = math.radians(67.5)
    add_box(bm, (130.4, -264.8, 1.85), (1.85, 0.28, 3.45), angle_z=ang_ab, mat_idx=4)
    add_box(bm, (131.9, -261.5, 1.55), (1.15, 0.28, 2.65), angle_z=ang_ab, mat_idx=8)

    # Warm beige plywood boarded doorway (`H4..H5, V2..V3` of Cam 4) with two bright orange diamond warning signs
    add_box(bm, (126.4, -272.2, 2.05), (2.35, 0.36, 3.65), angle_z=ang_ab, mat_idx=6)
    for z_sign in (2.35, 1.55):
        add_box(bm, (126.6, -272.1, z_sign), (0.48, 0.42, 0.48), angle_z=ang_ab, mat_idx=7)

    mesh = bpy.data.meshes.new("Bldg_Rue_SaintPierre_HistoricRow")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("Bldg_Rue_SaintPierre_HistoricRow", mesh)
    link_obj(obj, col_owned)


def build_remaining_buildings(col_owned, col_proxy, buildings, handled_ids, pal):
    """Builds all remaining Owned and Context Proxy buildings in dossier.json, plus the fully
    fenestrated Art Deco stepped Aldred Building skyscraper visible in Rue_de_la_Commune_Waterfront.jpg."""
    mats = [
        pal["limestone_cream"], pal["brick_red"], pal["limestone_grey"],
        pal["glass_dark"], pal["bronze_dark"], pal["roof_membrane"], pal["copper_green"],
        pal["roof_terracotta"]
    ]
    bm_owned = bmesh.new()
    bm_proxy = bmesh.new()

    for b in buildings:
        bid = b["id"]
        if bid in handled_ids or bid == 46866808:  # Skip far-east port shed 46866808
            continue
        is_owner = bool(b.get("is_primary_owner", True))
        bm = bm_owned if is_owner else bm_proxy
        tags = b.get("tags", {})
        levels_str = str(tags.get("building:levels", "4"))
        try:
            levels = max(2, int(float(levels_str)))
        except ValueError:
            levels = 4
        h = levels * 3.8
        mat_w = (bid % 3)

        pts = ensure_ccw(b["coords_xy"])
        if len(pts) < 3:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        top_mat = 7 if (cy < -258.0 and cx > 158.0) else 5
        core_pts = inset_polygon(pts, 1.2)
        add_prism(bm, core_pts, 0.0, h - 0.45, mat_side=3, mat_top=top_mat)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            is_party = is_party_wall(p1, p2, buildings, bid)
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) >= 5.5 and not is_party:
                build_detailed_facade_wall(bm, p1, p2, 0.0, h, bay_w=3.8, floor_h=3.8,
                                           mat_wall=mat_w, mat_glass=3, mat_frame=4, mat_sill=0,
                                           recess=0.45, has_ground_shop=True)
            else:
                add_wall_strip(bm, p1, p2, 0.0, h, -0.1, 0.35, mat_idx=mat_w, cap_top=(not is_party))

    # Detailed Art Deco Stepped Aldred Building Skyscraper in Block_MTL-VM-0015_Context_Proxy
    # With recessed dark-glass window bays, vertical Art Deco limestone piers, and setback cornices on every tier!
    al_x, al_y = 95.0, -92.0
    ang_al = math.radians(35.0)
    ca_al, sa_al = math.cos(ang_al), math.sin(ang_al)
    for z0, z1, w_s in [(0.0, 42.0, 32.0), (42.0, 62.0, 24.0), (62.0, 78.0, 17.0), (78.0, 90.0, 10.5)]:
        hw_s = w_s * 0.5
        local_sq = [(-hw_s, -hw_s), (hw_s, -hw_s), (hw_s, hw_s), (-hw_s, hw_s)]
        tier_pts = [(al_x + lx * ca_al - ly * sa_al, al_y + lx * sa_al + ly * ca_al) for lx, ly in local_sq]
        core_tier = inset_polygon(tier_pts, 1.1)
        add_prism(bm_proxy, core_tier, z0, z1 - 0.28, mat_side=3, mat_top=5)
        for ti in range(4):
            tp1, tp2 = tier_pts[ti], tier_pts[(ti + 1) % 4]
            build_detailed_facade_wall(bm_proxy, tp1, tp2, z0, z1, bay_w=2.9, floor_h=3.8,
                                       mat_wall=0, mat_glass=3, mat_frame=4, mat_sill=2,
                                       recess=0.45, has_ground_shop=(z0 == 0.0))

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


def add_sculpted_vehicle(bm, cx, cy, z0, heading_deg, mat_body, mat_glass, mat_tire, mat_rim, mat_light, mat_tail):
    ang = math.radians(90.0 - heading_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    L, W = 4.45, 1.84
    body_h, cab_h = 0.58, 0.54
    z_base = z0 + 0.34
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

    add_box(bm, (cx + (L * 0.49) * ca, cy + (L * 0.49) * sa, z_base + body_h * 0.40),
            (0.08, W * 0.52, body_h * 0.45), angle_z=ang, mat_idx=mat_tire)
    for sy in (-hb - 0.08, hb + 0.08):
        add_box(bm, (cx + (L * 0.14) * ca - sy * sa, cy + (L * 0.14) * sa + sy * ca, z_b1 + 0.08),
                (0.18, 0.22, 0.12), angle_z=ang, mat_idx=mat_body)

    z_cab0 = z_b1 - 0.04
    z_cab1 = z_cab0 + cab_h
    yb, yt = W * 0.44, W * 0.37
    local_cab = [
        (-L * 0.32, -yb, z_cab0), (L * 0.22, -yb, z_cab0), (L * 0.22, yb, z_cab0), (-L * 0.32, yb, z_cab0),
        (-L * 0.18, -yt, z_cab1), (L * 0.04, -yt, z_cab1), (L * 0.04, yt, z_cab1), (-L * 0.18, yt, z_cab1),
    ]
    cv = [bm.verts.new((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, lz)) for lx, ly, lz in local_cab]
    for f_idxs, m_i in [
        ((0, 3, 2, 1), mat_body), ((4, 5, 6, 7), mat_body),
        ((0, 1, 5, 4), mat_glass), ((1, 2, 6, 5), mat_glass),
        ((2, 3, 7, 6), mat_glass), ((3, 0, 4, 7), mat_glass),
    ]:
        f = bm.faces.new([cv[i] for i in f_idxs])
        f.material_index = m_i

    for sy in (-W * 0.34, W * 0.34):
        hx, hy = cx + (L * 0.49) * ca - sy * sa, cy + (L * 0.49) * sa + sy * ca
        tx, ty = cx + (-L * 0.49) * ca - sy * sa, cy + (-L * 0.49) * sa + sy * ca
        add_box(bm, (hx, hy, z_base + body_h * 0.58), (0.08, 0.30, 0.16), angle_z=ang, mat_idx=mat_light)
        add_box(bm, (tx, ty, z_base + body_h * 0.58), (0.08, 0.32, 0.18), angle_z=ang, mat_idx=mat_tail)

    for wx_off in (-L * 0.31, L * 0.31):
        for wy_off in (-W * 0.46, W * 0.46):
            wx = cx + wx_off * ca - wy_off * sa
            wy = cy + wx_off * sa + wy_off * ca
            add_sculpted_tire(bm, wx, wy, z0 + 0.34, 0.34, 0.24, ang, mat_tire, mat_rim)


def add_sculpted_utility_van(bm, cx, cy, z0, heading_deg, mat_body, mat_glass, mat_tire, mat_rim, mat_tail, mat_rack_blue, mat_stripe_gold):
    """Builds a sculpted commercial white utility van (Ford Transit / Savana style) with chamfered roofline,
    recessed rear window panels, vertical red taillight housing, dark rear step bumper, tires, side decal stripe,
    and roof-mounted ladder rack."""
    ang = math.radians(90.0 - heading_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    L, W = 5.10, 1.98
    z_b0 = z0 + 0.36
    z_mid = z0 + 1.28
    z_top = z0 + 2.08
    hb = W * 0.50
    ht = W * 0.44

    # Lower body hull (z_b0 -> z_mid)
    pts_low = [
        (-L * 0.50, -hb, z_b0), (L * 0.50, -hb, z_b0), (L * 0.50, hb, z_b0), (-L * 0.50, hb, z_b0),
        (-L * 0.50, -hb, z_mid), (L * 0.48, -hb, z_mid), (L * 0.48, hb, z_mid), (-L * 0.50, hb, z_mid),
    ]
    vl = [bm.verts.new((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, lz)) for lx, ly, lz in pts_low]
    for f_idxs in [(0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        f = bm.faces.new([vl[k] for k in f_idxs])
        f.material_index = mat_body

    # Upper tapered van body (z_mid -> z_top)
    pts_up = [
        (-L * 0.50, -hb, z_mid), (L * 0.48, -hb, z_mid), (L * 0.48, hb, z_mid), (-L * 0.50, hb, z_mid),
        (-L * 0.47, -ht, z_top), (L * 0.28, -ht, z_top), (L * 0.28, ht, z_top), (-L * 0.47, ht, z_top),
    ]
    vu = [bm.verts.new((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, lz)) for lx, ly, lz in pts_up]
    for f_idxs, m_u in [
        ((4, 5, 6, 7), mat_body), ((0, 1, 5, 4), mat_body),
        ((1, 2, 6, 5), mat_glass), ((2, 3, 7, 6), mat_body), ((3, 0, 4, 7), mat_body)
    ]:
        f = bm.faces.new([vu[k] for k in f_idxs])
        f.material_index = m_u

    # Dark charcoal rear step bumper (z = 0.34..0.52m) + rear barn-door seam & recessed rear window glass
    add_box(bm, (cx - (L * 0.51) * ca, cy - (L * 0.51) * sa, z0 + 0.43),
            (0.16, W * 0.98, 0.18), angle_z=ang, mat_idx=mat_tire)
    add_box(bm, (cx - (L * 0.49) * ca, cy - (L * 0.49) * sa, z0 + 1.62),
            (0.06, W * 0.72, 0.52), angle_z=ang, mat_idx=mat_glass)
    add_box(bm, (cx - (L * 0.50) * ca, cy - (L * 0.50) * sa, z0 + 1.22),
            (0.07, 0.05, 1.55), angle_z=ang, mat_idx=mat_tire)

    # Vertical red/amber rear taillight assemblies wrapping D-pillar corners + gold/dark commercial side stripes on both sides
    for sy in (-hb * 0.94, hb * 0.94):
        add_box(bm, (cx - (L * 0.48) * ca - sy * sa, cy - (L * 0.48) * sa + sy * ca, z0 + 1.08),
                (0.18, 0.18, 0.56), angle_z=ang, mat_idx=mat_tail)
        add_box(bm, (cx - (L * 0.18) * ca - sy * sa, cy - (L * 0.18) * sa + sy * ca, z0 + 0.94),
                (L * 0.60, 0.05, 0.16), angle_z=ang, mat_idx=mat_stripe_gold)
        add_box(bm, (cx - (L * 0.18) * ca - sy * sa, cy - (L * 0.18) * sa + sy * ca, z0 + 0.76),
                (L * 0.60, 0.05, 0.08), angle_z=ang, mat_idx=mat_tire)

    # Roof-mounted aluminum & royal-blue ladder rack bars (z = 2.08..2.24m)
    for rx_off in (-L * 0.40, -L * 0.05, L * 0.20):
        add_box(bm, (cx + rx_off * ca, cy + rx_off * sa, z_top + 0.10),
                (0.18, W * 0.92, 0.12), angle_z=ang, mat_idx=mat_rack_blue)
    for ry_off in (-ht * 0.88, ht * 0.88):
        add_box(bm, (cx - (L * 0.10) * ca - ry_off * sa, cy - (L * 0.10) * sa + ry_off * ca, z_top + 0.15),
                (L * 0.72, 0.10, 0.10), angle_z=ang, mat_idx=mat_rim)

    # 4 sculpted tires
    for wx_off in (-L * 0.32, L * 0.32):
        for wy_off in (-W * 0.46, W * 0.46):
            wx = cx + wx_off * ca - wy_off * sa
            wy = cy + wx_off * sa + wy_off * ca
            add_sculpted_tire(bm, wx, wy, z0 + 0.36, 0.36, 0.25, ang, mat_tire, mat_rim)


def add_heritage_lamp(bm, x, y, z0, mat_pole, mat_glass, mat_light, has_sign=False, mat_sign=0):
    """Builds a black Victorian heritage streetlamp post with hexagonal lantern cage & warm globe."""
    add_cylinder(bm, x, y, z0, z0 + 0.65, 0.18, 0.13, segs=12, mat_idx=mat_pole)
    add_cylinder(bm, x, y, z0 + 0.65, z0 + 4.15, 0.10, 0.08, segs=12, mat_idx=mat_pole)
    # Lantern base, glass globe, top conical cap, and 4 vertical cage ribs
    add_cylinder(bm, x, y, z0 + 4.12, z0 + 4.24, 0.14, 0.24, segs=6, mat_idx=mat_pole)
    add_cylinder(bm, x, y, z0 + 4.24, z0 + 4.68, 0.20, 0.16, segs=6, mat_idx=mat_glass)
    add_cylinder(bm, x, y, z0 + 4.30, z0 + 4.60, 0.10, 0.08, segs=8, mat_idx=mat_light)
    add_cylinder(bm, x, y, z0 + 4.68, z0 + 4.92, 0.26, 0.03, segs=6, mat_idx=mat_pole)
    if has_sign:
        add_box(bm, (x, y, z0 + 2.85), (0.06, 0.38, 0.52), mat_idx=mat_sign)


def build_streetscape_and_rail_tracks(col_owned, dossier, pal):
    """Builds road decks, cobblestone/flagstone sidewalks, yellow/white road markings, Old Port railway
    tracks with full crushed gravel ballast & wooden ties, waterfront park lawns, crushed-stone walkways,
    stepped granite quay walls, St. Lawrence River water basin, vehicles, and streetlamps across all 5 views."""
    bm = bmesh.new()
    # 0: asphalt_pbr, 1: sidewalk_pbr, 2: granite_dark, 3: white_paint,
    # 4: yellow_paint, 5: ballast_pbr, 6: rail_rust, 7: shrub_green,
    # 8: grass_green, 9: bronze_dark, 10: metal_silver, 11: glass_dark,
    # 12: warm_light, 13: red_light, 14: car_white, 15: car_silver,
    # 16: car_dark, 17: tire_rubber, 18: banner_blue, 19: banner_gold,
    # 20: gravel_path, 21: water_pbr
    mats = [
        pal["asphalt_pbr"], pal["sidewalk_pbr"], pal["granite_dark"], pal["white_paint"],
        pal["yellow_paint"], pal["ballast_pbr"], pal["rail_rust"], pal["shrub_green"],
        pal["grass_green"], pal["bronze_dark"], pal["metal_silver"], pal["glass_dark"],
        pal["warm_light"], pal["red_light"], pal["car_white"], pal["car_silver"],
        pal["car_dark"], pal["tire_rubber"], pal["banner_blue"], pal["banner_gold"],
        pal["gravel_path"], pal["water_pbr"]
    ]

    # Ground asphalt plane (west of Old Port waterfront park & basin)
    add_prism(bm, [(40.0, -390.0), (242.0, -390.0), (242.0, -90.0), (40.0, -90.0)], -0.20, 0.0, mat_side=0, mat_top=0)
    # East port road base south of crossing
    add_prism(bm, [(218.0, -390.0), (310.0, -390.0), (310.0, -252.0), (218.0, -252.0)], -0.20, 0.01, mat_side=0, mat_top=0)

    # St. Lawrence River / Old Port Basin Water at Z = -2.20m in top-right (`V8, H1..H4` of `satellite_topdown.png`)
    water_pts = [
        (246.0, -208.0), (310.0, -208.0), (310.0, -90.0), (240.0, -90.0),
        (246.5, -155.0), (245.5, -172.0), (246.8, -188.0), (250.5, -206.0)
    ]
    add_prism(bm, water_pts, -3.50, -2.20, mat_side=21, mat_top=21)

    # Stepped Granite Quay Wall along the curved river basin edge (`V8, H1..H4`)
    quay_curve = [(247.5, -148.0), (245.5, -162.0), (245.2, -175.0), (246.8, -190.0), (250.2, -205.0), (255.0, -218.0)]
    for qi in range(len(quay_curve) - 1):
        add_wall_strip(bm, quay_curve[qi], quay_curve[qi + 1], -2.50, 0.28, 0.0, 1.35, mat_idx=2)
        add_wall_strip(bm, quay_curve[qi], quay_curve[qi + 1], 0.28, 0.36, 0.0, 1.55, mat_idx=1)

    # Old Port Waterfront Lush Green Park Lawn (`Z = +0.195m`, `V7..V8, H1..H5` of `satellite_topdown.png`)
    # Kept strictly east/north of Cam 3's foreground railway ballast bed `(246.12, -245.41)`!
    east_lawn_north = [
        (246.5, -234.0), (255.0, -234.0), (254.5, -218.0), (249.8, -205.0),
        (246.2, -190.0), (244.8, -175.0), (245.0, -160.0), (247.0, -145.0),
        (226.5, -145.0), (232.0, -190.0), (241.5, -220.0)
    ]
    add_prism(bm, east_lawn_north, 0.0, 0.195, mat_side=2, mat_top=8)

    # South-East Lawn island below the level crossing (`V7..V8, H8` of `satellite_topdown.png`)
    east_lawn_south = [(231.0, -295.0), (262.0, -295.0), (262.0, -267.5), (233.0, -267.5)]
    add_prism(bm, east_lawn_south, 0.0, 0.195, mat_side=2, mat_top=8)

    # Non-coplanar Crushed-Stone Park Promenade Walkway (`Z = +0.255m`) curving along the Old Port park (`V8, H1..H5`)
    park_path_pts = [(245.5, -150.0), (243.5, -168.0), (244.0, -186.0), (247.5, -204.0), (250.5, -222.0)]
    for ppi in range(len(park_path_pts) - 1):
        add_wall_strip(bm, park_path_pts[ppi], park_path_pts[ppi + 1], 0.195, 0.255, 0.0, 4.2, mat_idx=20)

    # Dedicated Cycle Track & Pedestrian Promenade along Rue de la Commune East side (`V6..V7, H1..H8`)
    # Placed east of X = 219.5 so Cam 1 (`(213.51, -192.87)`) sees 100% continuous sunlit asphalt roadway across `H6..H8, V1..V5`!
    cycle_pts = [(220.5, -292.0), (225.8, -292.0), (222.5, -145.0), (217.5, -145.0)]
    add_prism(bm, cycle_pts, 0.0, 0.12, mat_side=2, mat_top=0)
    add_wall_strip(bm, (220.2, -292.0), (217.2, -145.0), 0.0, 0.15, 0.0, 0.38, mat_idx=2)
    add_wall_strip(bm, (221.8, -292.0), (218.8, -145.0), 0.12, 0.135, 0.0, 0.12, mat_idx=3)
    add_wall_strip(bm, (224.8, -292.0), (221.8, -145.0), 0.12, 0.135, 0.0, 0.12, mat_idx=3)

    # White Cross-Hatched Railway Level Crossing Boxes & Stop Bars at `Y = -266..-253` (`V6..V8, H7` of `satellite_topdown.png`)
    for xb_c in [230.2, 237.5]:
        add_wall_strip(bm, (xb_c - 2.2, -266.0), (xb_c + 2.2, -266.0), 0.01, 0.03, 0.0, 0.18, mat_idx=3)
        add_wall_strip(bm, (xb_c - 2.2, -254.0), (xb_c + 2.2, -254.0), 0.01, 0.03, 0.0, 0.18, mat_idx=3)
        add_wall_strip(bm, (xb_c - 2.2, -266.0), (xb_c - 2.2, -254.0), 0.01, 0.03, 0.0, 0.18, mat_idx=3)
        add_wall_strip(bm, (xb_c + 2.2, -266.0), (xb_c + 2.2, -254.0), 0.01, 0.03, 0.0, 0.18, mat_idx=3)
        for dy_h in [-263.0, -260.0, -257.0]:
            add_wall_strip(bm, (xb_c - 2.1, dy_h - 1.5), (xb_c + 2.1, dy_h + 1.5), 0.01, 0.03, 0.0, 0.14, mat_idx=3)
            add_wall_strip(bm, (xb_c - 2.1, dy_h + 1.5), (xb_c + 2.1, dy_h - 1.5), 0.01, 0.03, 0.0, 0.14, mat_idx=3)

    # Raised sidewalks with granite curbs around all buildings
    for b in dossier["osm_features"]["buildings"]:
        if b["id"] == 46866808:
            continue
        pts = list(b["coords_xy"])
        if len(pts) < 3:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        sw_pts, curb_pts = [], []
        for x, y in pts:
            dx, dy = x - cx, y - cy
            d = max(0.1, math.hypot(dx, dy))
            sw_pts.append((x + dx / d * 3.4, y + dy / d * 3.4))
            curb_pts.append((x + dx / d * 3.65, y + dy / d * 3.65))
        add_prism(bm, curb_pts, 0.0, 0.15, mat_side=2, mat_top=2)
        add_prism(bm, sw_pts, 0.0, 0.16, mat_side=1, mat_top=1)

    # Place Royale Flagstone Plaza & Grid Seams (`V2..V5, H1..H3` of `satellite_topdown.png`)
    plaza_pts = [(142.0, -162.0), (172.0, -142.0), (206.5, -158.0), (208.5, -195.0), (204.5, -212.0), (165.0, -208.0)]
    add_prism(bm, plaza_pts, 0.0, 0.16, mat_side=2, mat_top=1)
    # Stone grid bands & central square monument base in Place Royale (`(173.5, -160.5)`) visible in `satellite_topdown.png`
    pr_grid_ang = math.radians(-21.5)
    add_box(bm, (173.5, -160.5, 0.25), (5.2, 5.2, 0.18), angle_z=pr_grid_ang, mat_idx=2)
    add_cylinder(bm, 173.5, -160.5, 0.34, 1.45, 1.35, 1.25, segs=16, mat_idx=2)
    for gi in range(-3, 4):
        gx = 178.0 + gi * 4.8 * math.cos(pr_grid_ang)
        gy = -164.0 + gi * 4.8 * math.sin(pr_grid_ang)
        add_box(bm, (gx, gy, 0.165), (0.22, 26.0, 0.015), angle_z=pr_grid_ang, mat_idx=2)

    # Green tree lawn strip along NW side of Pointe-à-Callière (`V3..V4, H3..H6`)
    nw_lawn = [(152.0, -252.0), (159.5, -256.0), (192.0, -206.0), (184.5, -202.0)]
    add_prism(bm, nw_lawn, 0.0, 0.195, mat_side=2, mat_top=8)

    # Place d'Youville SW Park Lawn & Pedestrian Plaza (`V1..V2, H6..H8` of `satellite_topdown.png`)
    youville_lawn_w = [(122.0, -288.0), (132.0, -290.0), (147.0, -262.0), (138.0, -258.0)]
    youville_lawn_e = [(137.0, -290.0), (145.0, -292.0), (156.0, -267.0), (149.0, -263.0)]
    youville_path = [(131.5, -290.0), (138.0, -291.0), (150.0, -264.0), (144.0, -261.0)]
    add_prism(bm, youville_lawn_w, 0.0, 0.195, mat_side=2, mat_top=8)
    add_prism(bm, youville_lawn_e, 0.0, 0.195, mat_side=2, mat_top=8)
    add_prism(bm, youville_path, 0.0, 0.22, mat_side=2, mat_top=20)

    # 1. Camera 1 Streetscape (Pointe_a_Calliere_Prow_Tower: (213.51, -192.87), heading 215.0)
    # Continuous yellow-orange center line along Rue de la Commune Ouest (`H8, V4 -> H5, V2` in Cam 1)
    ang_com = math.atan2(-140.0, -6.5)
    add_wall_strip(bm, (214.2, -145.0), (208.5, -285.0), 0.01, 0.025, 0.0, 0.22, mat_idx=4)
    # White stop bar at southern intersection (`V6, H6` of `satellite_topdown.png`: `Y = -246.5`)
    add_box(bm, (209.8, -246.5, 0.018), (0.45, 5.2, 0.015), angle_z=ang_com, mat_idx=3)
    # Yellow crosswalk zebra stripes at north end (`(210.5, -163.5)`) visible in `satellite_topdown.png` (`V6, H1`)
    for zi in range(-6, 7):
        add_box(bm, (210.5 + zi * 1.15, -163.5 + zi * 0.22, 0.018), (3.6, 0.48, 0.015), angle_z=ang_com, mat_idx=4)

    # Right foreground black Victorian heritage streetlamp at (208.8, -196.2) + 2 lamps along East facade
    add_heritage_lamp(bm, 208.8, -196.2, 0.15, 9, 11, 12, has_sign=True, mat_sign=3)
    add_heritage_lamp(bm, 205.4, -220.5, 0.15, 9, 11, 12, has_sign=True, mat_sign=18)
    add_heritage_lamp(bm, 206.8, -242.5, 0.15, 9, 11, 12, has_sign=False)
    # Red fire hydrant on sidewalk in front of East facade (206.0, -231.5)
    add_cylinder(bm, 206.0, -231.5, 0.15, 0.88, 0.14, 0.12, segs=10, mat_idx=13)
    # Vehicles along Rue de la Commune matching `satellite_topdown.png` (`(209.2, -207.5)` black car, `(210.8, -228.0)` white car, `(208.5, -241.0)` white van) and Cam 1
    add_sculpted_vehicle(bm, 209.2, -207.5, 0.0, 182.0, 16, 11, 17, 10, 12, 13)
    add_sculpted_vehicle(bm, 210.8, -228.0, 0.0, 182.0, 14, 11, 17, 10, 12, 13)
    add_sculpted_utility_van(bm, 208.5, -241.0, 0.0, 182.0, 14, 11, 17, 10, 13, 18, 19)
    add_sculpted_vehicle(bm, 210.2, -252.0, 0.0, 183.0, 14, 11, 17, 10, 12, 13)
    add_sculpted_vehicle(bm, 214.5, -256.0, 0.0, 3.0, 15, 11, 17, 10, 12, 13)

    # 2. Camera 2 Streetscape (Place_Royale_Custom_House: (153.14, -134.08), heading 160.0)
    bx_w, by_w = 157.2, -142.8
    add_cylinder(bm, bx_w, by_w, 0.16, 0.90, 0.21, 0.23, segs=14, mat_idx=9)
    for sl_i in range(14):
        sl_a = 2.0 * math.pi * sl_i / 14.0
        add_box(bm, (bx_w + math.cos(sl_a) * 0.24, by_w + math.sin(sl_a) * 0.24, 0.54),
                (0.025, 0.04, 0.74), angle_z=sl_a, mat_idx=10)
    add_cylinder(bm, bx_w, by_w, 0.88, 0.95, 0.26, 0.24, segs=16, mat_idx=10)
    add_cylinder(bm, 155.8, -140.2, 0.004, 0.022, 0.38, 0.38, segs=20, mat_idx=9)
    add_cylinder(bm, 155.8, -140.2, 0.020, 0.025, 0.34, 0.34, segs=20, mat_idx=6)
    add_box(bm, (156.4, -141.2, 0.012), (0.62, 0.34, 0.02), angle_z=math.radians(-21.5), mat_idx=9)
    for dl_x, dl_y in [(175.5, -150.5), (184.5, -156.0), (193.0, -162.5)]:
        add_heritage_lamp(bm, dl_x, dl_y, 0.15, 9, 11, 12, has_sign=True, mat_sign=18)
    # Dark shaded stone garden retaining wall at left of Cam 2 (`H5, V1..V2`: `(176.5, -153.5)`)
    add_box(bm, (176.5, -153.5, 1.15), (14.5, 0.85, 2.00), angle_z=math.radians(-28.0), mat_idx=2)

    # 3. Camera 3 Streetscape (Rue_de_la_Commune_Waterfront: (246.12, -245.41), heading 314.9)
    # Old Port Single-Track Railway Line running directly from bottom-center of Cam 3 (`H8, V3..V4`: `(244.8, -244.5)`)
    # up-right across `H5..H7, V4..V8` to `(222.5, -188.5)`!
    p_r1 = (244.8, -244.5)
    p_r2 = (222.5, -188.5)
    rdx, rdy = p_r2[0] - p_r1[0], p_r2[1] - p_r1[1]
    rL = math.hypot(rdx, rdy)
    rux, ruy = rdx / rL, rdy / rL
    rnx, rny = -ruy, rux
    rang = math.atan2(ruy, rux)

    # Extend track from s = -48.0m to s = rL + 48.0m so it spans the entire `satellite_topdown.png` (`H1..H8`)
    s_start, s_end = -48.0, rL + 48.0
    full_rL = s_end - s_start
    sc_mid = 0.5 * (s_start + s_end)
    # Wide crushed grey-brown gravel railway ballast bed (`H6..H8, V3..V8` of Cam 3)
    add_box(bm, (p_r1[0] + rux * sc_mid + rnx * 0.8, p_r1[1] + ruy * sc_mid + rny * 0.8, 0.055),
            (full_rL, 6.8, 0.11), angle_z=rang, mat_idx=5)
    # Granite retaining curb along the west edge of the railway ballast bed (`H6..H8, V2..V3`)
    add_box(bm, (p_r1[0] + rux * sc_mid - rnx * 2.55, p_r1[1] + ruy * sc_mid - rny * 2.55, 0.12),
            (full_rL - 4.0, 0.24, 0.22), angle_z=rang, mat_idx=2)
    add_box(bm, (p_r1[0] + rux * sc_mid - rnx * 3.9, p_r1[1] + ruy * sc_mid - rny * 3.9, 0.06),
            (full_rL - 4.0, 2.8, 0.12), angle_z=rang, mat_idx=5)

    n_ties = int((full_rL - 1.0) / 0.62)
    for ti in range(n_ties):
        ts = s_start + 0.5 + ti * 0.62
        add_box(bm, (p_r1[0] + rux * ts, p_r1[1] + ruy * ts, 0.115),
                (0.24, 2.65, 0.11), angle_z=rang, mat_idx=2)
    for g_off in (-0.74, 0.74):
        rcx_l = p_r1[0] + rux * sc_mid + rnx * g_off
        rcy_l = p_r1[1] + ruy * sc_mid + rny * g_off
        add_box(bm, (rcx_l, rcy_l, 0.19), (full_rL, 0.10, 0.12), angle_z=rang, mat_idx=6)
        add_box(bm, (rcx_l, rcy_l, 0.255), (full_rL, 0.07, 0.03), angle_z=rang, mat_idx=10)

    # White museum banner sign ("POINTE-À-CALLIÈRE") in front of East facade at (208.5, -232.0)
    add_box(bm, (208.5, -232.0, 1.15), (4.5, 0.35, 1.45), angle_z=ang_com, mat_idx=3)

    # 4. Camera 4 Streetscape (Rue_McGill_Corner_Approach: (133.19, -283.02), heading 334.8)
    add_sculpted_utility_van(bm, 128.5, -282.8, 0.0, 204.5, 14, 11, 17, 10, 13, 18, 19)
    add_sculpted_vehicle(bm, 133.2, -264.8, 0.0, 206.0, 15, 11, 17, 10, 12, 13)
    add_sculpted_vehicle(bm, 143.5, -247.5, 0.0, 206.0, 16, 11, 17, 10, 12, 13)
    add_heritage_lamp(bm, 133.4, -260.2, 0.15, 9, 11, 12, has_sign=True, mat_sign=3)
    add_cylinder(bm, 137.8, -253.2, 0.15, 0.88, 0.14, 0.12, segs=10, mat_idx=13)

    mesh = bpy.data.meshes.new("MTL_VM_0015_Streetscape")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("MTL_VM_0015_Streetscape", mesh)
    link_obj(obj, col_owned)


def _build_lush_canopy_from_polyhaven_leaves(asset_id, src_mesh, mat_green, mat_bark, target_height_m=11.0, n_clusters=3200, cluster_radius=0.22):
    verts = src_mesh.vertices
    if len(verts) == 0:
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
            v1 = bm_l.verts.new((lx - r * ca, ly - r * sa, lz + r * 0.22))
            v2 = bm_l.verts.new((lx + r * 0.65 * sa, ly - r * 0.65 * ca, lz - r * 0.18))
            v3 = bm_l.verts.new((lx + r * ca, ly + r * sa, lz - r * 0.22))
            v4 = bm_l.verts.new((lx - r * 0.65 * sa, ly + r * 0.65 * ca, lz + r * 0.18))
            v5 = bm_l.verts.new((lx, ly, lz - r * 0.92))
            v6 = bm_l.verts.new((lx + r * 0.78 * ca, ly + r * 0.78 * sa, lz))
            v7 = bm_l.verts.new((lx, ly, lz + r * 0.92))
            v8 = bm_l.verts.new((lx - r * 0.78 * ca, ly - r * 0.78 * sa, lz))
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


def preload_and_optimize_polyhaven_models(parent_col, pal):
    mat_green = pal["Mat_MTL_Summer_Canopy_Green"]
    mat_bark = pal["tree_bark"]

    tree_configs = {
        "jacaranda_tree": ("jacaranda_tree_LOD1", 11.5, 3200, 0.22),
        "searsia_burchellii": ("searsia_burchellii_large_LOD2", 9.8, 2800, 0.20),
        "tree_small_02": ("tree_small_02_LOD1", 8.2, 2200, 0.18),
        "shrub_02": ("shrub_02_c_LOD2", 1.15, 950, 0.12),
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

    for prop_id in ("street_lamp_01", "modular_street_seating"):
        warmup_objs = kit.append_polyhaven_model(prop_id, parent_col, f"_Warmup_{prop_id}", location=(0, 0, 0), scale=1.0) or []
        for wo in warmup_objs:
            try:
                bpy.data.objects.remove(wo, do_unlink=True)
            except Exception:
                pass


def place_street_trees(col_owned, pal):
    """Spawns genuine high-poly Poly Haven 3D trees (`jacaranda_tree`, `searsia_burchellii`, `tree_small_02`),
    knee-high railway shrubs (`shrub_02`), streetlamps (`street_lamp_01`), and benches (`modular_street_seating`)
    matching `satellite_topdown.png` and all 4 Street View cameras."""
    preload_and_optimize_polyhaven_models(col_owned, pal)

    tree_spots = [
        # 1. Double-row dense green tree allée along NW side of Pointe-à-Callière (`V2..V4, H3..H6` of `satellite_topdown.png`)
        (184.5, -206.0, "jacaranda_tree", 1.12, 0.5),
        (180.0, -212.5, "searsia_burchellii", 1.15, 1.2),
        (175.0, -220.0, "jacaranda_tree", 1.18, 1.9),
        (170.0, -227.5, "searsia_burchellii", 1.18, 2.5),
        (165.0, -235.0, "jacaranda_tree", 1.15, 3.1),
        (159.5, -242.5, "searsia_burchellii", 1.12, 4.2),
        (153.5, -252.0, "jacaranda_tree", 1.15, 2.7),

        # 2. Place d'Youville SW park trees (`V2, H7..H8` of `satellite_topdown.png`, kept east of Cam 4's `334.8 deg` frustum!)
        (151.5, -268.0, "tree_small_02", 1.05, 1.4),
        (146.5, -279.0, "searsia_burchellii", 1.08, 3.2),
        (143.0, -288.0, "jacaranda_tree", 1.05, 2.1),

        # 3. Rue de la Commune cycle-path & promenade tree row (`V6, H1..H6` of `satellite_topdown.png`, kept clear of Cam 1's sky!)
        (218.5, -168.0, "tree_small_02", 0.95, 0.4),
        (216.5, -176.0, "jacaranda_tree", 1.05, 1.3),
        (222.5, -224.0, "tree_small_02", 0.72, 2.1),
        (221.5, -240.0, "searsia_burchellii", 0.78, 0.8),

        # 4. Old Port Waterfront Park tree row east of the railway tracks (`V7..V8, H1..H8` of `satellite_topdown.png` & `Cam 3` right)
        (238.0, -158.0, "jacaranda_tree", 1.18, 0.6),
        (238.5, -174.0, "searsia_burchellii", 1.22, 1.5),
        (239.5, -190.0, "jacaranda_tree", 1.20, 2.4),
        (241.0, -206.0, "jacaranda_tree", 1.28, 3.3),
        (243.5, -221.0, "searsia_burchellii", 0.98, 0.9),
        (250.2, -231.5, "tree_small_02", 0.62, 1.4),
        (255.0, -227.0, "searsia_burchellii", 1.05, 2.2),
        (245.0, -278.0, "jacaranda_tree", 1.25, 1.1),
        (254.0, -276.0, "searsia_burchellii", 1.28, 2.8),

        # 5. Place Royale saplings (`Cam 1` right & `Cam 2` left background — scaled so `H1..H3` sky stays 100% open!)
        (194.5, -192.0, "tree_small_02", 0.36, 1.1),
        (186.5, -184.0, "tree_small_02", 0.42, 2.5),
        (182.0, -158.0, "tree_small_02", 0.78, 0.9),
        (191.5, -166.0, "tree_small_02", 0.82, 2.2),
    ]

    bm_grates = bmesh.new()
    for idx, (tx, ty, sp, sc, rot) in enumerate(tree_spots):
        kit.append_polyhaven_model(
            sp,
            col_owned,
            f"PAC_StreetTree_{idx:02d}_{sp}",
            location=(tx, ty, 0.16),
            rotation_z=rot,
            scale=sc
        )
        add_box(bm_grates, (tx, ty, 0.165), (1.0, 1.0, 0.02), angle_z=rot, mat_idx=0)

    # Populate the Old Port railway garden bed with knee-high organic leafy Poly Haven `shrub_02` canopies!
    # Strictly confined to `sh_s = 15.0..58.0m` west of the tracks so `H6..H8` in Cam 3 is 100% open ballast & steel rails!
    p_r1 = (244.8, -244.5)
    p_r2 = (222.5, -188.5)
    rdx, rdy = p_r2[0] - p_r1[0], p_r2[1] - p_r1[1]
    rL = math.hypot(rdx, rdy)
    rux, ruy = rdx / rL, rdy / rL
    rnx, rny = -ruy, rux
    for sh_i in range(26):
        sh_s = 15.0 + sh_i * 1.65
        lat_off = 3.3 + (sh_i % 3) * 0.40
        sh_x = p_r1[0] + rux * sh_s - rnx * lat_off
        sh_y = p_r1[1] + ruy * sh_s - rny * lat_off
        sc_xy = 0.85 + (sh_i % 4) * 0.08
        kit.append_polyhaven_model(
            "shrub_02",
            col_owned,
            f"PAC_RailwayShrub_{sh_i:02d}",
            location=(sh_x, sh_y, 0.08),
            rotation_z=sh_i * 1.15,
            scale=sc_xy
        )

    # Shrubs atop the left retaining wall in Cam 2 (`H4, V1..V2`: `(174..181, -152..-156, 2.0)`)
    for c2_i, (sx2, sy2) in enumerate([(173.5, -151.8), (176.5, -153.5), (179.5, -155.2)]):
        kit.append_polyhaven_model(
            "shrub_02",
            col_owned,
            f"PAC_Cam2WallShrub_{c2_i:02d}",
            location=(sx2, sy2, 2.05),
            rotation_z=c2_i * 0.9,
            scale=0.95
        )

    # Poly Haven Streetlamps & Benches along the Old Port promenade & Place Royale
    for li, (lx, ly) in enumerate([(220.5, -182.0), (221.8, -206.0), (222.8, -230.0), (244.5, -180.0), (247.5, -210.0)]):
        kit.append_polyhaven_model("street_lamp_01", col_owned, f"PAC_PH_Lamp_{li}", location=(lx, ly, 0.16), rotation_z=0.0, scale=1.0)
    for bi, (bx, by) in enumerate([(245.5, -165.0), (245.0, -182.0), (247.5, -198.0), (221.0, -216.0)]):
        kit.append_polyhaven_model("modular_street_seating", col_owned, f"PAC_PH_Bench_{bi}", location=(bx, by, 0.20), rotation_z=1.57, scale=1.0)

    grate_mesh = bpy.data.meshes.new("PAC_Tree_Grates")
    bm_grates.to_mesh(grate_mesh)
    bm_grates.free()
    grate_mesh.materials.append(pal["bronze_dark"])
    grate_obj = bpy.data.objects.new("PAC_Tree_Grates", grate_mesh)
    link_obj(grate_obj, col_owned)


def setup_world_and_render(dossier, iteration=3, fast_render=True):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.eevee.use_raytracing = True

    world = bpy.data.worlds.new("PAC_World")
    scene.world = world
    world.use_nodes = True
    wnodes = world.node_tree.nodes
    wlinks = world.node_tree.links
    wnodes.clear()

    w_out = wnodes.new("ShaderNodeOutputWorld")
    w_bg = wnodes.new("ShaderNodeBackground")
    w_bg.inputs["Strength"].default_value = 1.18
    wlinks.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

    if os.path.exists(HDRI_PATH):
        env_tex = wnodes.new("ShaderNodeTexEnvironment")
        env_tex.image = bpy.data.images.load(HDRI_PATH, check_existing=True)
        wlinks.new(env_tex.outputs["Color"], w_bg.inputs["Color"])
    else:
        w_bg.inputs["Color"].default_value = (0.65, 0.78, 0.95, 1.0)

    light_data = bpy.data.lights.new(name="Montreal_Sun", type="SUN")
    light_data.energy = 3.8
    light_data.color = (1.0, 0.96, 0.88)
    light_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name="Montreal_Sun", object_data=light_data)
    sun_obj.rotation_euler = (math.radians(40.0), math.radians(15.0), math.radians(-145.0))
    bpy.context.scene.collection.objects.link(sun_obj)

    if not fast_render:
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

    # Overview Snapshot framing Pointe-à-Callière ship-prow, belfry spire, Place Royale & Old Custom House
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    ov_data = bpy.data.cameras.new(name="Cam_Overview")
    ov_data.angle = math.radians(56.0)
    ov_data.clip_end = 2500.0
    ov_obj = bpy.data.objects.new(name="Cam_Overview", object_data=ov_data)
    ov_obj.location = (265.0, -325.0, 125.0)
    ov_obj.rotation_euler = (math.radians(46.0), 0.0, math.radians(34.0))
    bpy.context.scene.collection.objects.link(ov_obj)
    scene.camera = ov_obj
    scene.render.filepath = SNAPSHOT_PATH
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Overview -> {SNAPSHOT_PATH}")


def main():
    iteration = 3
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if args:
            try:
                iteration = int(args[0])
            except ValueError:
                iteration = 3

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

    if 87411702 in b_by_id:
        build_pointe_a_calliere_eperon(col_owned, b_by_id[87411702], pal)
    build_custom_house_and_place_royale(col_owned, b_by_id.get(87411690), b_by_id.get(87411683), b_by_id.get(87411688), pal, all_buildings=buildings)
    build_rue_mcgill_and_saint_pierre_row(col_owned, b_by_id, pal, all_buildings=buildings)

    handled_ids = {
        87411702, 87411690, 87411683, 87411688,
        339869984, 339870137, 339870338, 339870474,
        339870490, 339873678, 339873679
    }
    build_remaining_buildings(col_owned, col_proxy, buildings, handled_ids, pal)
    build_streetscape_and_rail_tracks(col_owned, dossier, pal)
    place_street_trees(col_owned, pal)

    setup_world_and_render(dossier, iteration=iteration, fast_render=True)
    bpy.context.scene.render.engine = "CYCLES"

    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"pack_all notice: {e}")

    bpy.context.preferences.filepaths.save_version = 0
    tmp_blend = BLEND_PATH + ".tmp.blend"
    if os.path.exists(tmp_blend):
        try:
            os.remove(tmp_blend)
        except OSError:
            pass
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
    for ext in ("", "@", "@1", "1"):
        p = BLEND_PATH + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    if os.path.exists(tmp_blend):
        os.replace(tmp_blend, BLEND_PATH)
    bpy.ops.wm.usd_export(filepath=USDC_PATH, check_existing=False)
    print(f"Saved {BLEND_PATH} and exported {USDC_PATH}")


if __name__ == "__main__":
    main()

