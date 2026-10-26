import os
import sys
import json
import math
import random
import shutil
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

sys.path.append(r"C:\Users\Felipe\Documents\coding\montreal\src")
import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0012"
BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_BLOCKS_DIR = os.path.join(BASE_DIR, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
KIT_BLEND_PATH = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_BLOCKS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def get_or_create_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        if parent is not None:
            parent.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)
    return col


def load_image_safe(filepath, colorspace="sRGB"):
    if not os.path.exists(filepath):
        return None
    img = bpy.data.images.load(filepath, check_existing=True)
    if colorspace and hasattr(img, "colorspace_settings"):
        try:
            img.colorspace_settings.name = colorspace
        except Exception:
            pass
    return img


def build_pbr_textured_material(
    name, diff_file, rough_file, norm_file, tint_hex="#FFFFFF", tint_factor=0.30,
    box_scale=0.35, roughness_mult=1.0, normal_strength=0.95, metallic=0.0,
    add_mortar_grid=False, mortar_scale=3.2, mortar_hex="#4A4742"
):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = metallic
    links.new(out.inputs["Surface"], bsdf.outputs["BSDF"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (box_scale, box_scale, box_scale)
    links.new(mapping.inputs["Vector"], tex_coord.outputs["Object"])

    img_d = load_image_safe(os.path.join(POLYHAVEN_DIR, diff_file), "sRGB") if diff_file else None
    if img_d:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = img_d
        tex_d.projection = 'BOX'
        tex_d.projection_blend = 0.25
        links.new(tex_d.inputs["Vector"], mapping.outputs["Vector"])

        mix_c = nodes.new("ShaderNodeMix")
        mix_c.data_type = 'RGBA'
        mix_c.blend_type = 'MULTIPLY' if tint_factor > 0.45 else 'MIX'
        mix_c.inputs["Factor"].default_value = tint_factor
        mix_c.inputs["B"].default_value = kit.hex_to_rgba(tint_hex)
        links.new(mix_c.inputs["A"], tex_d.outputs["Color"])
        base_col_out = mix_c.outputs["Result"]
    else:
        rgb = nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = kit.hex_to_rgba(tint_hex)
        base_col_out = rgb.outputs[0]

    if add_mortar_grid:
        brick = nodes.new("ShaderNodeTexBrick")
        brick.offset = 0.5
        brick.inputs["Scale"].default_value = mortar_scale
        brick.inputs["Mortar Size"].default_value = 0.018
        brick.inputs["Mortar Smooth"].default_value = 0.20
        brick.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
        brick.inputs["Color2"].default_value = (0.94, 0.93, 0.91, 1.0)
        brick.inputs["Mortar"].default_value = kit.hex_to_rgba(mortar_hex)
        links.new(brick.inputs["Vector"], tex_coord.outputs["Object"])

        mix_m = nodes.new("ShaderNodeMix")
        mix_m.data_type = 'RGBA'
        mix_m.blend_type = 'MULTIPLY'
        mix_m.inputs["Factor"].default_value = 0.60
        links.new(mix_m.inputs["A"], base_col_out)
        links.new(mix_m.inputs["B"], brick.outputs["Color"])
        links.new(bsdf.inputs["Base Color"], mix_m.outputs["Result"])
    else:
        links.new(bsdf.inputs["Base Color"], base_col_out)

    img_r = load_image_safe(os.path.join(POLYHAVEN_DIR, rough_file), "Non-Color") if rough_file else None
    if img_r:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = img_r
        tex_r.projection = 'BOX'
        tex_r.projection_blend = 0.25
        links.new(tex_r.inputs["Vector"], mapping.outputs["Vector"])
        math_r = nodes.new("ShaderNodeMath")
        math_r.operation = 'MULTIPLY'
        math_r.inputs[1].default_value = roughness_mult
        links.new(math_r.inputs[0], tex_r.outputs["Color"])
        links.new(bsdf.inputs["Roughness"], math_r.outputs["Value"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.6 * roughness_mult

    img_n = load_image_safe(os.path.join(POLYHAVEN_DIR, norm_file), "Non-Color") if norm_file else None
    if img_n:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = img_n
        tex_n.projection = 'BOX'
        tex_n.projection_blend = 0.25
        links.new(tex_n.inputs["Vector"], mapping.outputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal_strength
        links.new(nmap.inputs["Color"], tex_n.outputs["Color"])
        links.new(bsdf.inputs["Normal"], nmap.outputs["Normal"])

    return mat


def create_custom_materials(palette):
    palette["Mat_MTL_PierreGrise_Limestone"] = build_pbr_textured_material(
        "Mat_MTL_PierreGrise_Limestone", "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg", tint_hex="#A4A5A1", tint_factor=0.52, box_scale=0.42,
        roughness_mult=0.88, normal_strength=1.20, add_mortar_grid=True, mortar_scale=2.6, mortar_hex="#555652"
    )
    palette["Mat_MTL_WarmBuff_Limestone"] = build_pbr_textured_material(
        "Mat_MTL_WarmBuff_Limestone", "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg", tint_hex="#DFC9A4", tint_factor=0.45, box_scale=0.38,
        roughness_mult=0.82, normal_strength=1.25, add_mortar_grid=True, mortar_scale=2.4, mortar_hex="#685C49"
    )
    palette["Mat_MTL_Light_Granite_Steps"] = build_pbr_textured_material(
        "Mat_MTL_Light_Granite_Steps", "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg", tint_hex="#D2D4D0", tint_factor=0.72, box_scale=0.35,
        roughness_mult=0.68, normal_strength=0.55, add_mortar_grid=True, mortar_scale=1.25, mortar_hex="#767874"
    )
    palette["Mat_MTL_SquareVictoria_Pavers"] = build_pbr_textured_material(
        "Mat_MTL_SquareVictoria_Pavers", "cobblestone_floor_08_Diffuse_2k.jpg", "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg", tint_hex="#B4B7B3", tint_factor=0.35, box_scale=0.48,
        roughness_mult=0.80, normal_strength=1.20, add_mortar_grid=True, mortar_scale=1.8, mortar_hex="#4E504D"
    )
    palette["Mat_MTL_Dark_Honed_Granite"] = build_pbr_textured_material(
        "Mat_MTL_Dark_Honed_Granite", "rock_wall_16_diff_2k.jpg", "rock_wall_16_rough_2k.jpg",
        "rock_wall_16_nor_gl_2k.jpg", tint_hex="#33363B", tint_factor=0.68, box_scale=0.45,
        roughness_mult=0.42, normal_strength=0.75
    )
    palette["Mat_MTL_Street_Asphalt"] = build_pbr_textured_material(
        "Mat_MTL_Street_Asphalt", "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg", tint_hex="#46494E", tint_factor=0.35, box_scale=0.22,
        roughness_mult=0.88, normal_strength=1.05
    )
    palette["Mat_MTL_Heritage_RedBrick"] = build_pbr_textured_material(
        "Mat_MTL_Heritage_RedBrick", "castle_brick_02_red_Diffuse_2k.jpg", "castle_brick_02_red_Rough_2k.jpg",
        "castle_brick_02_red_nor_gl_2k.jpg", tint_hex="#9E3C2E", tint_factor=0.40, box_scale=0.48,
        roughness_mult=0.88, normal_strength=1.20, add_mortar_grid=True, mortar_scale=4.2, mortar_hex="#685A52"
    )
    palette["Mat_MTL_Slate_Roof_Dark"] = build_pbr_textured_material(
        "Mat_MTL_Slate_Roof_Dark", "rock_wall_16_diff_2k.jpg", "rock_wall_16_rough_2k.jpg",
        "rock_wall_16_nor_gl_2k.jpg", tint_hex="#23272D", tint_factor=0.75, box_scale=0.45,
        roughness_mult=0.65, normal_strength=0.90
    )
    palette["Mat_MTL_Verdigris_Copper"] = build_pbr_textured_material(
        "Mat_MTL_Verdigris_Copper", "rock_wall_16_diff_2k.jpg", "rock_wall_16_rough_2k.jpg",
        "rock_wall_16_nor_gl_2k.jpg", tint_hex="#3A6E5C", tint_factor=0.78, box_scale=0.50,
        roughness_mult=0.48, normal_strength=0.60, metallic=0.55
    )
    palette["Mat_MTL_Grass_Lawn"] = build_pbr_textured_material(
        "Mat_MTL_Grass_Lawn", "rock_wall_16_diff_2k.jpg", "rock_wall_16_rough_2k.jpg",
        "rock_wall_16_nor_gl_2k.jpg", tint_hex="#3A6E24", tint_factor=0.78, box_scale=0.55,
        roughness_mult=0.92, normal_strength=0.85
    )
    palette["Mat_MTL_Foliage_Shrub"] = build_pbr_textured_material(
        "Mat_MTL_Foliage_Shrub", "rock_wall_16_diff_2k.jpg", "rock_wall_16_rough_2k.jpg",
        "rock_wall_16_nor_gl_2k.jpg", tint_hex="#285418", tint_factor=0.82, box_scale=0.75,
        roughness_mult=0.88, normal_strength=1.15
    )
    palette["Mat_MTL_Modern_Smooth_Limestone"] = build_pbr_textured_material(
        "Mat_MTL_Modern_Smooth_Limestone", "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg", tint_hex="#9FA4A8", tint_factor=0.76, box_scale=0.35,
        roughness_mult=0.55, normal_strength=0.28, add_mortar_grid=True, mortar_scale=1.15, mortar_hex="#686C70"
    )
    palette["Mat_MTL_Window_Frame_Light"] = build_pbr_textured_material(
        "Mat_MTL_Window_Frame_Light", "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg", tint_hex="#EBE8E0", tint_factor=0.82, box_scale=0.50,
        roughness_mult=0.38, normal_strength=0.25
    )
    palette["Mat_MTL_CastIron_Black"] = build_pbr_textured_material(
        "Mat_MTL_CastIron_Black", "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg", tint_hex="#181B1F", tint_factor=0.82, box_scale=0.55,
        roughness_mult=0.38, normal_strength=0.40, metallic=0.78
    )

    for mat_name, hex_col, rough, metal, ior_val, emit_hex, emit_str in (
        ("Mat_MTL_Window_Glass_Dark", "#0F1924", 0.05, 0.22, 1.52, None, 0.0),
        ("Mat_MTL_Curtain_Glass_Blue", "#3E5D7C", 0.04, 0.35, 1.52, None, 0.0),
        ("Mat_MTL_Water_Surface", "#102430", 0.03, 0.15, 1.33, None, 0.0),
        ("Mat_MTL_Guimard_Green", "#234F3C", 0.28, 0.72, 1.50, None, 0.0),
        ("Mat_MTL_Bronze_Statue", "#354238", 0.32, 0.82, 1.50, None, 0.0),
        ("Mat_MTL_Brushed_Steel", "#C8CED4", 0.20, 0.88, 1.50, None, 0.0),
        ("Mat_MTL_Patio_Yellow", "#D8B428", 0.32, 0.10, 1.50, None, 0.0),
        ("Mat_MTL_Sign_Blue", "#184A8C", 0.35, 0.15, 1.50, None, 0.0),
        ("Mat_MTL_Sign_Red", "#9E201C", 0.35, 0.15, 1.50, None, 0.0),
        ("Mat_MTL_Auto_White", "#ECEFF2", 0.14, 0.35, 1.50, None, 0.0),
        ("Mat_MTL_Auto_Silver", "#BFC6CE", 0.15, 0.65, 1.50, None, 0.0),
        ("Mat_MTL_Auto_Charcoal", "#1C2128", 0.14, 0.55, 1.50, None, 0.0),
        ("Mat_MTL_Rubber_Tire", "#141517", 0.78, 0.02, 1.50, None, 0.0),
        ("Mat_MTL_Amber_Glow", "#FF8C1A", 0.15, 0.0, 1.50, "#FF9A28", 4.5),
    ):
        m = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
        m.use_nodes = True
        ns = m.node_tree.nodes
        ls = m.node_tree.links
        ns.clear()
        out_n = ns.new("ShaderNodeOutputMaterial")
        bsdf_n = ns.new("ShaderNodeBsdfPrincipled")
        bsdf_n.inputs["Base Color"].default_value = kit.hex_to_rgba(hex_col)
        bsdf_n.inputs["Roughness"].default_value = rough
        bsdf_n.inputs["Metallic"].default_value = metal
        if "IOR" in bsdf_n.inputs:
            bsdf_n.inputs["IOR"].default_value = ior_val
        if emit_hex and "Emission Color" in bsdf_n.inputs:
            bsdf_n.inputs["Emission Color"].default_value = kit.hex_to_rgba(emit_hex)
            bsdf_n.inputs["Emission Strength"].default_value = emit_str
        ls.new(out_n.inputs["Surface"], bsdf_n.outputs["BSDF"])
        palette[mat_name] = m

    return palette


def apply_bevel_and_smooth(obj, width=0.025, segments=2):
    if obj is None or obj.type != 'MESH':
        return
    bev = obj.modifiers.new(name="ArchBevel", type='BEVEL')
    bev.width = width
    bev.segments = segments
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(35.0)


def add_oriented_box(bm, center_xy, dir_2d, perp_2d, width, depth, z_min, z_max, mat_idx=0):
    cx, cy = center_xy
    dx, dy = dir_2d
    px, py = perp_2d
    hw, hd = width * 0.5, depth * 0.5
    corners_2d = [
        (cx - dx * hw - px * hd, cy - dy * hw - py * hd),
        (cx + dx * hw - px * hd, cy + dy * hw - py * hd),
        (cx + dx * hw + px * hd, cy + dy * hw + py * hd),
        (cx - dx * hw + px * hd, cy - dy * hw + py * hd),
    ]
    v_bot = [bm.verts.new((x, y, z_min)) for (x, y) in corners_2d]
    v_top = [bm.verts.new((x, y, z_max)) for (x, y) in corners_2d]
    faces = []
    try:
        faces.append(bm.faces.new(v_bot[::-1]))
        faces.append(bm.faces.new(v_top))
        for i in range(4):
            ni = (i + 1) % 4
            faces.append(bm.faces.new((v_bot[i], v_bot[ni], v_top[ni], v_top[i])))
    except ValueError:
        pass
    for f in faces:
        f.material_index = mat_idx
    return faces


def inset_polygon_2d(pts_2d, inset_dist=0.85):
    n = len(pts_2d)
    new_pts = []
    for i in range(n):
        p_prev = pts_2d[(i - 1) % n]
        p_curr = pts_2d[i]
        p_next = pts_2d[(i + 1) % n]
        e1 = (p_curr - p_prev).normalized()
        e2 = (p_next - p_curr).normalized()
        in1 = Vector((-e1.y, e1.x))
        in2 = Vector((-e2.y, e2.x))
        avg_in = in1 + in2
        if avg_in.length < 0.1:
            avg_in = in1
        else:
            avg_in.normalize()
        new_pts.append(p_curr + avg_in * inset_dist)
    return new_pts


def build_recessed_window_facade_along_edge(
    bm, p_start, p_end, out_dir, z_base, z_top, n_floors=4, bay_target_width=3.2,
    recess_depth=0.48, wall_mat=0, trim_mat=1, glass_mat=3, frame_mat=4,
    ground_commercial=True, add_cornice=True
):
    edge_vec = p_end - p_start
    edge_len = edge_vec.length
    if edge_len < 2.2 or z_top <= z_base + 1.5:
        return
    t_dir = edge_vec / edge_len
    n_bays = max(1, int(round(edge_len / bay_target_width)))
    bay_w = edge_len / n_bays
    pier_w = max(0.42, min(0.85, bay_w * 0.25))
    win_w = max(0.75, bay_w - pier_w)
    mid_edge = (p_start + p_end) * 0.5

    glass_plane = mid_edge - out_dir * (recess_depth * 0.55)
    add_oriented_box(bm, (glass_plane.x, glass_plane.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), edge_len - 0.15, recess_depth * 0.45, z_base + 0.2, z_top - 0.2, mat_idx=glass_mat)

    for i in range(n_bays + 1):
        u = (i / n_bays) * edge_len
        pw = pier_w * 0.65 if (i == 0 or i == n_bays) else pier_w
        u_clamped = max(pw * 0.5, min(edge_len - pw * 0.5, u))
        pier_xy = p_start + t_dir * u_clamped
        add_oriented_box(bm, (pier_xy.x, pier_xy.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), pw, recess_depth, z_base, z_top, mat_idx=wall_mat)

    floor_h = (z_top - z_base) / max(1, n_floors)
    for fl in range(n_floors):
        fz0 = z_base + fl * floor_h
        fz1 = z_base + (fl + 1) * floor_h
        sill_h = 0.52 if (fl == 0 and ground_commercial) else 0.78
        lintel_drop = 0.52 if (fl == 0 and ground_commercial) else 0.55
        wz0 = fz0 + sill_h
        wz1 = fz1 - lintel_drop

        add_oriented_box(bm, (mid_edge.x, mid_edge.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), edge_len, recess_depth, fz0, wz0, mat_idx=wall_mat)
        add_oriented_box(bm, (mid_edge.x, mid_edge.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), edge_len, recess_depth, wz1, fz1, mat_idx=wall_mat)

        if fl in (0, 1, n_floors - 2) and n_floors >= 3:
            belt_xy = mid_edge + out_dir * (recess_depth * 0.5 + 0.12)
            add_oriented_box(bm, (belt_xy.x, belt_xy.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), edge_len + 0.20, 0.28, fz1 - 0.16, fz1 + 0.16, mat_idx=trim_mat)

        for b_i in range(n_bays):
            bay_c = p_start.lerp(p_end, (b_i + 0.5) / n_bays)
            outer_face = bay_c + out_dir * (recess_depth * 0.5)
            recess_face = bay_c - out_dir * (recess_depth * 0.25)

            sill_xy = outer_face + out_dir * 0.08
            add_oriented_box(bm, (sill_xy.x, sill_xy.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), win_w + 0.20, 0.24, wz0 - 0.12, wz0 + 0.03, mat_idx=trim_mat)
            lintel_xy = outer_face + out_dir * 0.07
            add_oriented_box(bm, (lintel_xy.x, lintel_xy.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), win_w + 0.24, 0.22, wz1 - 0.02, wz1 + 0.18, mat_idx=trim_mat)
            add_oriented_box(bm, (recess_face.x, recess_face.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), 0.07, 0.14, wz0, wz1, mat_idx=frame_mat)
            tr_z = wz0 + (wz1 - wz0) * 0.62
            add_oriented_box(bm, (recess_face.x, recess_face.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), win_w, 0.14, tr_z - 0.035, tr_z + 0.035, mat_idx=frame_mat)

    if add_cornice:
        corn_xy = mid_edge + out_dir * (recess_depth * 0.5 + 0.28)
        add_oriented_box(bm, (corn_xy.x, corn_xy.y), (t_dir.x, t_dir.y), (out_dir.x, out_dir.y), edge_len + 0.45, 0.65, z_top - 0.42, z_top + 0.12, mat_idx=trim_mat)


def build_detailed_heritage_building(
    b_data, height, mat_wall, mat_trim, mat_roof, mat_window, mat_frame,
    collection, prefix="Bldg", bay_width=3.4
):
    coords = b_data["coords_xy"]
    pts_2d = [Vector((p[0], p[1])) for p in coords[:-1]]
    if len(pts_2d) < 3:
        return None
    area2 = sum(pts_2d[i].x * pts_2d[(i + 1) % len(pts_2d)].y - pts_2d[(i + 1) % len(pts_2d)].x * pts_2d[i].y for i in range(len(pts_2d)))
    if area2 < 0:
        pts_2d.reverse()

    b_id = b_data.get("id", 0)
    mesh = bpy.data.meshes.new(f"{prefix}_{b_id}_Mesh")
    obj = bpy.data.objects.new(f"{prefix}_{b_id}", mesh)
    collection.objects.link(obj)
    for m in (mat_wall, mat_trim, mat_roof, mat_window, mat_frame):
        obj.data.materials.append(m)

    bm = bmesh.new()
    inset_pts = inset_polygon_2d(pts_2d, inset_dist=0.80)
    v_bot = [bm.verts.new((p.x, p.y, 0.0)) for p in inset_pts]
    v_top = [bm.verts.new((p.x, p.y, height)) for p in inset_pts]
    try:
        bm.faces.new(v_bot[::-1]).material_index = 0
        bm.faces.new(v_top).material_index = 2
        for i in range(len(inset_pts)):
            ni = (i + 1) % len(inset_pts)
            bm.faces.new((v_bot[i], v_bot[ni], v_top[ni], v_top[i])).material_index = 0
    except ValueError:
        pass

    n_floors = max(2, int(round(height / 3.8)))
    for i in range(len(pts_2d)):
        p1 = pts_2d[i]
        p2 = pts_2d[(i + 1) % len(pts_2d)]
        edge_v = p2 - p1
        if edge_v.length < 3.0:
            continue
        out_n = Vector((edge_v.y, -edge_v.x)).normalized()
        build_recessed_window_facade_along_edge(
            bm, p1, p2, out_n, 0.0, height, n_floors=n_floors, bay_target_width=bay_width,
            recess_depth=0.45, wall_mat=0, trim_mat=1, glass_mat=3, frame_mat=4
        )

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.025, segments=2)
    return obj


def add_contoured_vehicle(bm, cx, cy, c_ang_deg, body_mat, glass_mat, tire_mat, rim_mat, style="sedan", accent_mat=None):
    """
    Builds a contoured 3D parked/street vehicle (`style='sedan'`, `'suv'`, or `'van'`) with an 8-station
    longitudinal automotive profile, dark tinted glass windows, roof ladder rack (for commercial vans),
    and 4 true cylindrical 20-segment wheels with metallic alloy hubcaps.
    """
    ang_rad = math.radians(c_ang_deg)
    cd = Vector((math.cos(ang_rad), math.sin(ang_rad)))
    cp = Vector((-cd.y, cd.x))
    center = Vector((cx, cy))

    if style == "van":
        stations = [
            (-2.55, 0.28, 0.72, 0.94, 0.88),
            (-2.42, 0.24, 1.98, 0.98, 0.90),
            (-1.20, 0.24, 2.02, 0.98, 0.90),
            (0.65,  0.24, 2.00, 0.98, 0.90),
            (1.45,  0.24, 1.15, 0.95, 0.88),
            (2.25,  0.26, 0.92, 0.90, 0.84),
            (2.45,  0.30, 0.65, 0.84, 0.78),
        ]
    elif style == "suv":
        stations = [
            (-2.22, 0.28, 0.72, 0.88, 0.82),
            (-2.05, 0.24, 1.56, 0.92, 0.78),
            (-0.55, 0.24, 1.60, 0.92, 0.78),
            (0.45,  0.24, 1.56, 0.92, 0.78),
            (1.05,  0.24, 1.02, 0.90, 0.84),
            (1.98,  0.26, 0.86, 0.88, 0.80),
            (2.20,  0.30, 0.62, 0.82, 0.76),
        ]
    else:
        stations = [
            (-2.12, 0.26, 0.66, 0.82, 0.76),
            (-1.92, 0.22, 0.90, 0.88, 0.82),
            (-1.32, 0.22, 0.94, 0.90, 0.82),
            (-0.72, 0.22, 1.42, 0.90, 0.74),
            (0.30,  0.22, 1.42, 0.90, 0.74),
            (0.95,  0.22, 0.90, 0.88, 0.82),
            (1.90,  0.24, 0.75, 0.86, 0.78),
            (2.14,  0.28, 0.56, 0.78, 0.72),
        ]

    rings = []
    for x_lon, z_bot, z_top, hw_b, hw_t in stations:
        p_mid = center + cd * x_lon
        z_belt = min(z_top - 0.04, 0.95 if style == "van" else 0.88)
        ring = [
            bm.verts.new(((p_mid - cp * hw_b).x, (p_mid - cp * hw_b).y, z_bot)),
            bm.verts.new(((p_mid - cp * (hw_b + 0.03)).x, (p_mid - cp * (hw_b + 0.03)).y, z_belt)),
            bm.verts.new(((p_mid - cp * hw_t).x, (p_mid - cp * hw_t).y, z_top)),
            bm.verts.new(((p_mid + cp * hw_t).x, (p_mid + cp * hw_t).y, z_top)),
            bm.verts.new(((p_mid + cp * (hw_b + 0.03)).x, (p_mid + cp * (hw_b + 0.03)).y, z_belt)),
            bm.verts.new(((p_mid + cp * hw_b).x, (p_mid + cp * hw_b).y, z_bot)),
        ]
        rings.append(ring)

    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        is_cabin = (i == 3) if style == "van" else ((1 <= i <= 3) if style == "suv" else (3 <= i <= 4))
        for k in range(6):
            nk = (k + 1) % 6
            try:
                f = bm.faces.new((r0[k], r1[k], r1[nk], r0[nk]))
                if is_cabin and k in (1, 3):
                    f.material_index = glass_mat
                elif style == "van" and i == 4 and k == 2:
                    f.material_index = glass_mat
                elif style != "van" and ((i == (3 if style == "suv" else 4) and k == 2) or (i == (0 if style == "suv" else 2) and k == 2)):
                    f.material_index = glass_mat
                else:
                    f.material_index = body_mat
                f.smooth = True
            except ValueError:
                pass
    try:
        bm.faces.new(rings[0][::-1]).material_index = body_mat
        bm.faces.new(rings[-1]).material_index = body_mat
    except ValueError:
        pass

    if style == "van" and accent_mat is not None:
        # Solid white commercial van details: roof ladder rack + orange ladder + side panel seam/stripe + rear bumper & red taillights!
        add_oriented_box(bm, (cx - cd.x * 0.4, cy - cd.y * 0.4), (cd.x, cd.y), (cp.x, cp.y), 2.9, 1.35, 2.02, 2.12, mat_idx=rim_mat)
        add_oriented_box(bm, (cx - cd.x * 0.4, cy - cd.y * 0.4), (cd.x, cd.y), (cp.x, cp.y), 3.1, 0.42, 2.10, 2.20, mat_idx=accent_mat)
        add_oriented_box(bm, (cx - cd.x * 0.55, cy - cd.y * 0.55), (cd.x, cd.y), (cp.x, cp.y), 2.4, 2.01, 1.28, 1.40, mat_idx=accent_mat)
        add_oriented_box(bm, (cx - cd.x * 2.52, cy - cd.y * 2.52), (cd.x, cd.y), (cp.x, cp.y), 0.18, 1.92, 0.28, 0.46, mat_idx=tire_mat)
        for ts in (-0.82, 0.82):
            tp = center - cd * 2.45 + cp * ts
            add_oriented_box(bm, (tp.x, tp.y), (cd.x, cd.y), (cp.x, cp.y), 0.12, 0.22, 0.65, 1.05, mat_idx=accent_mat)

    rot_wheel = Euler((math.radians(90.0), 0.0, ang_rad), 'XYZ').to_matrix().to_4x4()
    wx_pair = (-1.52, 1.55) if style == "van" else (-1.32, 1.34)
    wy_off = 0.90 if style == "van" else 0.84
    r_tire = 0.36 if style in ("van", "suv") else 0.33
    for wx in wx_pair:
        for side_s in (-1.0, 1.0):
            wp = center + cd * wx + cp * (side_s * wy_off)
            ret_t = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20, radius1=r_tire, radius2=r_tire, depth=0.25, matrix=Matrix.Translation((wp.x, wp.y, r_tire)) @ rot_wheel)
            for v in ret_t["verts"]:
                for f in v.link_faces:
                    f.material_index = tire_mat
                    f.smooth = True
            rp = wp + cp * (side_s * 0.04)
            ret_r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16, radius1=r_tire * 0.62, radius2=r_tire * 0.62, depth=0.21, matrix=Matrix.Translation((rp.x, rp.y, r_tire)) @ rot_wheel)
            for v in ret_r["verts"]:
                for f in v.link_faces:
                    f.material_index = rim_mat
                    f.smooth = True


def build_greenshields_104674804(b_data, palette, col_owned):
    """
    Hero Building #1 (`104674804`): Édifice Greenshields (`759 Rue Saint-Antoine Ouest`).
    10-story Beaux-Arts golden-buff cut limestone landmark in the Right Foreground of Camera 1 (`Guimard_Metro_Entrance.jpg`)
    and Camera 3 (`Square_Victoria_East_Walk.jpg`), and Right Background of Camera 2 & Camera 4.
    """
    mesh = bpy.data.meshes.new("MTL_VM_0012_Greenshields_104674804_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0012_Greenshields_104674804", mesh)
    col_owned.objects.link(obj)
    for m in [
        palette["Mat_MTL_WarmBuff_Limestone"],       # 0: Golden-buff cut limestone ashlar walls & fluted pilasters
        palette["Mat_MTL_PierreGrise_Limestone"],    # 1: Rusticated ground plinth, belt cornices & carved medallions
        palette["Mat_MTL_Slate_Roof_Dark"],          # 2: Roof & heavily bracketed dark projecting roof cornice
        palette["Mat_MTL_Window_Glass_Dark"],        # 3: Deeply recessed dark reflective window glass
        palette["Mat_MTL_CastIron_Black"],           # 4: Dark bronze tripartite window frames, mullions & modillion brackets
        palette["Mat_MTL_Guimard_Green"],            # 5: Green wayfinding parking sign panel (`P`) on sidewalk
        palette["Mat_MTL_Window_Frame_Light"],       # 6: White sign lettering & lamp globe
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()
    pts_2d = [Vector((p[0], p[1])) for p in b_data["coords_xy"][:-1]]
    area2 = sum(pts_2d[i].x * pts_2d[(i + 1) % len(pts_2d)].y - pts_2d[(i + 1) % len(pts_2d)].x * pts_2d[i].y for i in range(len(pts_2d)))
    if area2 < 0:
        pts_2d.reverse()

    z_top = 37.50
    inset_pts = inset_polygon_2d(pts_2d, inset_dist=0.88)
    v_bot = [bm.verts.new((p.x, p.y, 0.0)) for p in inset_pts]
    v_top = [bm.verts.new((p.x, p.y, z_top)) for p in inset_pts]
    try:
        bm.faces.new(v_bot[::-1]).material_index = 0
        bm.faces.new(v_top).material_index = 2
        for i in range(len(inset_pts)):
            ni = (i + 1) % len(inset_pts)
            bm.faces.new((v_bot[i], v_bot[ni], v_top[ni], v_top[i])).material_index = 0
    except ValueError:
        pass

    # Main NW Hero Facade along Rue Saint-Antoine Ouest (`p_sw = (-376.61, -329.44)` to `p_ne = (-338.35, -264.54)`)
    # and SW Facade facing Square Victoria (`p_se = (-348.59, -343.72)` to `p_sw = (-376.61, -329.44)`)
    p_sw = Vector((-376.61, -329.44))
    p_ne = Vector((-338.35, -264.54))
    p_se = Vector((-348.59, -343.72))
    p_east = Vector((-315.83, -280.40))

    for f_p1, f_p2, n_bays, has_arch_portal in (
        (p_sw, p_ne, 13, True),   # NW Facade along Rue Saint-Antoine Ouest (Camera 1 & Camera 3 Hero Right!)
        (p_se, p_sw, 7, False),   # SW Facade facing Square Victoria (Camera 2 & Camera 4 Background Right!)
        (p_ne, p_east, 6, False), # NE Facade
    ):
        f_vec = f_p2 - f_p1
        f_len = f_vec.length
        f_dir = f_vec / f_len
        out_n = Vector((-f_dir.y, f_dir.x)).normalized()
        if out_n.dot(Vector((-366.57, -287.81)) - f_p1) < 0 and has_arch_portal:
            out_n = -out_n
        elif not has_arch_portal and out_n.dot(Vector((-342.0, -305.0)) - (f_p1 + f_p2) * 0.5) > 0:
            out_n = -out_n
        in_n = -out_n
        bay_w = f_len / n_bays
        mid_f = (f_p1 + f_p2) * 0.5

        # Backing dark reflective glass plane (`in_n * 0.48m`)
        gl_c = mid_f + in_n * 0.48
        add_oriented_box(bm, (gl_c.x, gl_c.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), f_len - 0.3, 0.25, 0.4, z_top - 0.5, mat_idx=3)

        # Horizontal stone spandrel bands & projecting Beaux-Arts cornices (`z = 2.4m, 8.6m, 12.2m, 31.8m, 36.4m`)
        for sz0, sz1, m_i in ((0.0, 0.65, 1), (2.15, 2.95, 1), (7.95, 9.15, 0), (11.75, 12.55, 0), (31.40, 32.35, 1), (35.80, z_top, 0)):
            sc = mid_f + in_n * 0.22
            add_oriented_box(bm, (sc.x, sc.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), f_len, 0.48, sz0, sz1, mat_idx=m_i)
        for fl_i in range(6):
            fz = 12.55 + (fl_i + 1) * 3.88
            sc = mid_f + in_n * 0.22
            add_oriented_box(bm, (sc.x, sc.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), f_len, 0.46, fz - 0.52, fz + 0.42, mat_idx=0)

        for cz0, cz1, c_proj, c_mat in ((2.65, 2.98, 0.22, 1), (8.45, 9.05, 0.48, 1), (12.15, 12.55, 0.32, 1), (31.75, 32.35, 0.45, 1), (36.35, 37.55, 0.92, 2)):
            cc = mid_f + out_n * (c_proj * 0.5)
            add_oriented_box(bm, (cc.x, cc.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), f_len + 0.5, c_proj + 0.3, cz0, cz1, mat_idx=c_mat)

        # Heavily bracketed dark bronze/slate roof cornice modillion brackets (`z = 35.75..36.45m`, visible in Camera 1 & Camera 3!)
        n_mod = int(f_len / 0.85)
        for m_i in range(n_mod):
            mp = f_p1.lerp(f_p2, (m_i + 0.5) / n_mod) + out_n * 0.46
            add_oriented_box(bm, (mp.x, mp.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), 0.22, 0.78, 35.70, 36.42, mat_idx=4)

        # Vertical rusticated ground piers (`z = 0..9.0m`) & upper fluted limestone pilasters (`z = 9.0..36.4m`)
        for b_i in range(n_bays + 1):
            pxy = f_p1 + f_dir * (b_i * bay_w)
            add_oriented_box(bm, (pxy.x, pxy.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), 1.05, 0.58, 0.0, 9.0, mat_idx=1)
            add_oriented_box(bm, (pxy.x, pxy.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), 0.92, 0.52, 9.0, z_top, mat_idx=0)
            for rz in (0.8, 1.6, 3.2, 4.2, 5.2, 6.2, 7.2):
                rp = pxy + out_n * 0.08
                add_oriented_box(bm, (rp.x, rp.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), 1.12, 0.46, rz, rz + 0.55, mat_idx=0)

        for b_i in range(n_bays):
            b_xy = f_p1 + f_dir * ((b_i + 0.5) * bay_w)
            win_w = bay_w - 1.05

            # Ground/basement window (`z = 0.65..2.15m`)
            for m_s in (-0.32, 0.32):
                mp = b_xy + f_dir * (m_s * win_w) + in_n * 0.22
                add_oriented_box(bm, (mp.x, mp.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), 0.12, 0.22, 0.65, 2.15, mat_idx=4)

            # Double-height mezzanine bay (`z = 2.95..7.95m`): arched entrance portal at bay 4 & 8, tripartite Chicago window elsewhere!
            if has_arch_portal and b_i in (4, 8):
                # Semicircular arched stone surround (`Guimard_Metro_Entrance.jpg` Center-Right!)
                for a_i in range(11):
                    ang = math.pi * (a_i / 10.0)
                    ax = math.cos(ang) * (win_w * 0.48)
                    az = 5.65 + math.sin(ang) * 2.15
                    ap = b_xy + f_dir * ax + out_n * 0.14
                    add_oriented_box(bm, (ap.x, ap.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), 0.36, 0.42, az - 0.22, az + 0.22, mat_idx=1)
            for m_s in (-0.28, 0.28):
                mp = b_xy + f_dir * (m_s * win_w) + in_n * 0.24
                add_oriented_box(bm, (mp.x, mp.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), 0.09, 0.18, 2.95, 7.95, mat_idx=4)
            add_oriented_box(bm, (b_xy.x + in_n.x * 0.24, b_xy.y + in_n.y * 0.24), (f_dir.x, f_dir.y), (out_n.x, out_n.y), win_w, 0.18, 6.25, 6.38, mat_idx=4)

            # Upper 8 stories (`z = 9.05..35.80m`): paired/tripartite windows separated by stone center mullion + carved spandrel medallions!
            cm_p = b_xy + in_n * 0.14
            add_oriented_box(bm, (cm_p.x, cm_p.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), 0.28, 0.36, 9.05, 35.80, mat_idx=0)
            for fl_z in (14.2, 18.1, 22.0, 25.8, 29.7):
                med_p = b_xy + out_n * 0.06
                add_oriented_box(bm, (med_p.x, med_p.y), (f_dir.x, f_dir.y), (out_n.x, out_n.y), 0.52, 0.18, fl_z - 0.26, fl_z + 0.26, mat_idx=1)

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.025, segments=2)
    return obj


def build_jacques_parizeau_w_hotel_112881749(b_data, palette, col_owned):
    """
    Hero Building #2 (`112881749`): Édifice Jacques-Parizeau (CDPQ) & W Montréal Hotel (`901 Rue du Square-Victoria`).
    1. SW Wing (`W Montréal Hotel`, facing Square Victoria along `(-445.3, -290.0)` to `(-408.8, -312.0)`):
       Hero of Camera 4 (`Square_Victoria_West_Walk.jpg`)! Features 10-story smooth architectural grey limestone facade,
       dark honed granite wainscot, monumental double-height glass entrance portal (`901`) with smooth 4-bar 3D brushed-silver `"W"`
       sculpture above (`z = 8.45..11.45m`), deeply recessed ground-floor window bays, and the outdoor restaurant terrace
       with alternating yellow/gold and dark-charcoal vertical-louvered planter boxes + 3 white octagonal canvas umbrellas!
    2. NE Wing (`CDPQ Glass Curtain-Wall Tower`, `(-378.5, -218.0)`):
       Hero Left Skyscraper of Camera 1 (`Guimard_Metro_Entrance.jpg`) and Camera 3 (`Square_Victoria_East_Walk.jpg`)!
    """
    mesh = bpy.data.meshes.new("MTL_VM_0012_JacquesParizeau_W_112881749_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0012_JacquesParizeau_W_112881749", mesh)
    col_owned.objects.link(obj)
    for m in [
        palette["Mat_MTL_Modern_Smooth_Limestone"],  # 0: Large-format smooth cool-grey limestone panels of W Montréal Hotel
        palette["Mat_MTL_Dark_Honed_Granite"],       # 1: Dark honed charcoal granite wainscot & planter boxes
        palette["Mat_MTL_Slate_Roof_Dark"],          # 2: Roof & dark window frames
        palette["Mat_MTL_Window_Glass_Dark"],        # 3: Deeply recessed dark reflective window glass
        palette["Mat_MTL_Window_Frame_Light"],       # 4: Crisp white curtain-wall spandrels, penthouse & patio umbrellas
        palette["Mat_MTL_Curtain_Glass_Blue"],       # 5: Reflective blue-silver curtain-wall glass (CDPQ NE wing & W portal fins)
        palette["Mat_MTL_Brushed_Steel"],            # 6: Smooth 3D brushed-silver `"W"` sculpture & `901` stainless portal canopy
        palette["Mat_MTL_Patio_Yellow"],             # 7: Yellow/gold vertical-slat terrace planter boxes (Camera 4!)
        palette["Mat_MTL_Foliage_Shrub"],            # 8: Planter soil base
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # --- PART A: W Montréal Hotel SW Facade (`p_nw = (-445.30, -289.95)` to `p_se = (-409.50, -311.62)`, Hero of Camera 4!) ---
    # Shortened slightly at SE corner (`w_len = 41.85m`) so the parked dark SUV and east-side Édifice Greenshields are visible on the right of Camera 4!
    p_nw = Vector((-445.30, -289.95))
    p_se_orig = Vector((-397.71, -318.76))
    w_dir = (p_se_orig - p_nw).normalized()
    w_len = 41.85
    p_se = p_nw + w_dir * w_len
    sw_out = Vector((-w_dir.y, w_dir.x)).normalized()
    if sw_out.dot(Vector((-424.84, -311.67)) - p_nw) < 0:
        sw_out = -sw_out
    ne_in = -sw_out
    mid_w = (p_nw + p_se) * 0.5
    z_w_top = 36.80

    # Main W Hotel Core Box recessed 0.90m behind the SW/SE facades
    core_c = mid_w + ne_in * 12.5
    add_oriented_box(bm, (core_c.x, core_c.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), w_len - 1.5, 23.2, 0.0, z_w_top, mat_idx=0)
    add_oriented_box(bm, (core_c.x, core_c.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), w_len - 2.2, 22.4, z_w_top, z_w_top + 0.15, mat_idx=2)

    # Backing dark reflective glass plane (`ne_in * 0.55m`)
    gl_w = mid_w + ne_in * 0.55
    add_oriented_box(bm, (gl_w.x, gl_w.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), w_len - 0.4, 0.25, 0.2, z_w_top - 0.4, mat_idx=3)

    # Dark honed granite wainscot (`z = 0..1.35m`), horizontal stone spandrels & projecting belt courses
    add_oriented_box(bm, (mid_w.x + ne_in.x * 0.20, mid_w.y + ne_in.y * 0.20), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), w_len, 0.45, 0.0, 1.35, mat_idx=1)
    for sz0, sz1 in ((7.65, 9.25), (11.35, 12.45), (15.05, 16.05), (18.65, 19.75), (22.35, 23.35), (25.95, 27.05), (29.65, 30.65), (33.25, z_w_top)):
        add_oriented_box(bm, (mid_w.x + ne_in.x * 0.22, mid_w.y + ne_in.y * 0.22), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), w_len, 0.45, sz0, sz1, mat_idx=0)
    for cz0, cz1, c_proj in ((8.35, 8.75, 0.28), (11.85, 12.20, 0.24), (19.15, 19.50, 0.24), (26.45, 26.80, 0.24), (35.95, 36.85, 0.55)):
        cc = mid_w + sw_out * (c_proj * 0.5)
        add_oriented_box(bm, (cc.x, cc.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), w_len + 0.3, c_proj + 0.25, cz0, cz1, mat_idx=0)

    n_bays_w = 10
    bay_w_len = w_len / n_bays_w  # 4.185m per bay (`portal` at bays 4 & 5 -> u = 20.92m, exact same world position!)
    for b_i in range(n_bays_w + 1):
        pxy = p_nw + w_dir * (b_i * bay_w_len)
        # Skip central pier inside the double-width `901 / W` entrance portal (`b_i == 5`)
        z0_pier = 8.40 if b_i == 5 else 0.0
        pw = 1.35 if b_i in (4, 6) else 0.92
        add_oriented_box(bm, (pxy.x, pxy.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), pw, 0.52, z0_pier, z_w_top, mat_idx=0)
        if b_i < n_bays_w and b_i not in (4, 5):
            # Center window mullion on upper floors & ground floor window frames
            b_mid = p_nw + w_dir * ((b_i + 0.5) * bay_w_len) + ne_in * 0.32
            add_oriented_box(bm, (b_mid.x, b_mid.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), 0.14, 0.18, 1.35, z_w_top - 0.5, mat_idx=2)
            add_oriented_box(bm, (b_mid.x, b_mid.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), bay_w_len - 0.9, 0.22, 4.15, 4.45, mat_idx=2)

    # Monumental Double-Height `"W / 901"` Glass Entrance Portal (`bays 4 & 5`, centered at `u = 5.0 * bay_w_len = 20.92m`)!
    portal_xy = p_nw + w_dir * (5.0 * bay_w_len)
    portal_w = bay_w_len * 2.0 - 1.15
    # Stainless steel surround frame + `901` horizontal canopy (`z = 3.15..3.85m`) + glass revolving doors + blue glass side fins
    add_oriented_box(bm, (portal_xy.x + sw_out.x * 0.12, portal_xy.y + sw_out.y * 0.12), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), portal_w + 0.45, 0.35, 7.60, 8.05, mat_idx=6)
    add_oriented_box(bm, (portal_xy.x - sw_out.x * 0.15, portal_xy.y - sw_out.y * 0.15), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), portal_w, 0.55, 3.15, 3.85, mat_idx=6)
    for s_fin in (-0.46, 0.46):
        fp = portal_xy + w_dir * (s_fin * portal_w) + sw_out * 0.05
        add_oriented_box(bm, (fp.x, fp.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), 0.38, 0.45, 0.0, 7.80, mat_idx=5)
    for d_m in (-0.22, 0.0, 0.22):
        dp = portal_xy + w_dir * (d_m * portal_w) - sw_out * 0.20
        add_oriented_box(bm, (dp.x, dp.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), 0.08, 0.25, 0.0, 3.15, mat_idx=6)

    # Iconic Smooth 4-Bar 3D Brushed-Silver Metallic `"W"` Sculpture (`z = 8.45..11.45m`, ZERO stair-step voxels!)
    w_strokes = [
        (-1.68, 11.42, -0.82, 8.45),
        (-0.82, 8.45,   0.00, 10.68),
        ( 0.00, 10.68,  0.82, 8.45),
        ( 0.82, 8.45,   1.68, 11.42),
    ]
    bar_hw = 0.22
    for u0, z0, u1, z1 in w_strokes:
        du, dz = u1 - u0, z1 - z0
        blen = math.hypot(du, dz)
        nu, nz = -dz / blen * bar_hw, du / blen * bar_hw
        pts_uz = [(u0 - nu, z0 - nz), (u0 + nu, z0 + nz), (u1 + nu, z1 + nz), (u1 - nu, z1 - nz)]
        v_back = [bm.verts.new(((portal_xy + w_dir * u + sw_out * 0.22).x, (portal_xy + w_dir * u + sw_out * 0.22).y, z)) for (u, z) in pts_uz]
        v_front = [bm.verts.new(((portal_xy + w_dir * u + sw_out * 0.52).x, (portal_xy + w_dir * u + sw_out * 0.52).y, z)) for (u, z) in pts_uz]
        try:
            bm.faces.new(v_back[::-1]).material_index = 6
            bm.faces.new(v_front).material_index = 6
            for k_i in range(4):
                nk_i = (k_i + 1) % 4
                bm.faces.new((v_back[k_i], v_back[nk_i], v_front[nk_i], v_front[k_i])).material_index = 6
        except ValueError:
            pass

    # Sidewalk Cafe Terrace (`Square_Victoria_West_Walk.jpg` Center-Right Foreground: `u = 26.8m` to `39.6m`)!
    # Alternating Yellow/Gold (`mat_idx=7`) and Dark Charcoal (`mat_idx=1`) vertical-louvered planter boxes + 3 white umbrellas!
    # (Botanical leaf shrubs inside the planters are instanced from `jacaranda_tree_LOD0` in `build_square_victoria_park_and_streetscape`!)
    for p_idx in range(7):
        pu = 27.6 + p_idx * 1.82
        p_box_xy = p_nw + w_dir * pu + sw_out * 2.55
        p_mat = 7 if (p_idx % 2 == 0) else 1
        add_oriented_box(bm, (p_box_xy.x, p_box_xy.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), 1.74, 0.52, 0.15, 0.96, mat_idx=p_mat)
        # Vertical louver slats on the planter front face
        for sl_i in range(-5, 6):
            sl_p = p_box_xy + w_dir * (sl_i * 0.14) + sw_out * 0.27
            add_oriented_box(bm, (sl_p.x, sl_p.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), 0.04, 0.04, 0.18, 0.94, mat_idx=p_mat)
    for side_u in (26.8, 39.5):
        sp_xy = p_nw + w_dir * side_u + sw_out * 1.45
        add_oriented_box(bm, (sp_xy.x, sp_xy.y), (w_dir.x, w_dir.y), (sw_out.x, sw_out.y), 0.52, 2.30, 0.15, 0.96, mat_idx=7)
    for umb_u in (29.2, 33.8, 38.2):
        u_xy = p_nw + w_dir * umb_u + sw_out * 1.65
        ret_up = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=12, radius1=0.05, radius2=0.04, depth=2.65, matrix=Matrix.Translation((u_xy.x, u_xy.y, 1.48)))
        for v in ret_up["verts"]:
            for f in v.link_faces:
                f.material_index = 6
        ret_uc = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=8, radius1=2.15, radius2=0.08, depth=0.58, matrix=Matrix.Translation((u_xy.x, u_xy.y, 2.82)))
        for v in ret_uc["verts"]:
            for f in v.link_faces:
                f.material_index = 4

    # SE Facade of W Montréal along Rue Saint-Antoine Ouest (`p_se` to `p_se2`)
    p_se2 = p_se + ne_in * 24.0
    se_dir = (p_se2 - p_se).normalized()
    se_out = Vector((se_dir.y, -se_dir.x)).normalized()
    build_recessed_window_facade_along_edge(
        bm, p_se, p_se2, se_out, 0.0, z_w_top, n_floors=9, bay_target_width=3.6, recess_depth=0.50,
        wall_mat=0, trim_mat=0, glass_mat=3, frame_mat=2
    )

    # --- PART B: CDPQ 13-Story Sleek Glass Curtain-Wall Tower Wing (`(-378.5, -218.0)`, `z = 0..53.5m`, Camera 1 & Camera 3 Left Skyscraper!) ---
    cdpq_c = Vector((-378.5, -218.0))
    cdpq_dir = Vector((0.51, 0.86)).normalized()
    cdpq_out = Vector((0.86, -0.51)).normalized()  # facing SE toward Rue Saint-Antoine Ouest
    cw_w, cw_d, cw_h = 44.0, 30.0, 47.5
    add_oriented_box(bm, (cdpq_c.x, cdpq_c.y), (cdpq_dir.x, cdpq_dir.y), (cdpq_out.x, cdpq_out.y), cw_w, cw_d, 0.0, cw_h, mat_idx=5)
    # White horizontal curtain-wall spandrel bands every 3.6m (`Guimard_Metro_Entrance.jpg` Left!)
    for f_i in range(13):
        fz = 3.8 + f_i * 3.55
        add_oriented_box(bm, (cdpq_c.x, cdpq_c.y), (cdpq_dir.x, cdpq_dir.y), (cdpq_out.x, cdpq_out.y), cw_w + 0.25, cw_d + 0.25, fz, fz + 0.62, mat_idx=4)
    # Slender vertical silver mullions every 2.0m
    for u_i in range(-10, 11):
        mp1 = cdpq_c + cdpq_dir * (u_i * 2.0) + cdpq_out * (cw_d * 0.5)
        add_oriented_box(bm, (mp1.x, mp1.y), (cdpq_dir.x, cdpq_dir.y), (cdpq_out.x, cdpq_out.y), 0.14, 0.28, 0.0, cw_h, mat_idx=4)
        mp2 = cdpq_c + cdpq_out * (u_i * 1.35) - cdpq_dir * (cw_w * 0.5)
        add_oriented_box(bm, (mp2.x, mp2.y), (cdpq_out.x, cdpq_out.y), (cdpq_dir.x, cdpq_dir.y), 0.14, 0.28, 0.0, cw_h, mat_idx=4)
    # Recessed White Vertical-Ribbed Mechanical Penthouse Crown (`z = 47.5..53.8m`)!
    add_oriented_box(bm, (cdpq_c.x, cdpq_c.y), (cdpq_dir.x, cdpq_dir.y), (cdpq_out.x, cdpq_out.y), cw_w - 1.2, cw_d - 1.2, cw_h, cw_h + 6.2, mat_idx=4)
    for u_i in range(-10, 11):
        rp1 = cdpq_c + cdpq_dir * (u_i * 1.95) + cdpq_out * (cw_d * 0.5 - 0.55)
        add_oriented_box(bm, (rp1.x, rp1.y), (cdpq_dir.x, cdpq_dir.y), (cdpq_out.x, cdpq_out.y), 0.18, 0.35, cw_h, cw_h + 6.2, mat_idx=0)
        rp2 = cdpq_c + cdpq_out * (u_i * 1.30) - cdpq_dir * (cw_w * 0.5 - 0.55)
        add_oriented_box(bm, (rp2.x, rp2.y), (cdpq_out.x, cdpq_out.y), (cdpq_dir.x, cdpq_dir.y), 0.18, 0.35, cw_h, cw_h + 6.2, mat_idx=0)

    bm.to_mesh(mesh)
    bm.free()
    apply_bevel_and_smooth(obj, width=0.025, segments=2)
    return obj


def build_place_victoria_19896201(b_data, palette, col_owned):
    """
    Hero Building #3 (`19896201`): Place Victoria / Tour de la Bourse (`48 stories, height = 190.0m`).
    Iconic 1964 Moretti & Nervi skyscraper at the south end of Square Victoria (`centroid [-414.7, -470.7]`),
    built with 4 monumental chamfered white precast-concrete corner mega-columns, recessed dark bronze curtain wall,
    and 3 double-height mechanical louver truss bands!
    """
    mesh = bpy.data.meshes.new("MTL_VM_0012_PlaceVictoria_19896201_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0012_PlaceVictoria_19896201", mesh)
    col_owned.objects.link(obj)
    for m in [
        palette["Mat_MTL_Window_Glass_Dark"],        # 0: Dark bronze reflective curtain wall
        palette["Mat_MTL_Window_Frame_Light"],       # 1: 4 Monumental white precast-concrete corner mega-columns
        palette["Mat_MTL_CastIron_Black"],           # 2: Dark anodized bronze mullions & spandrels
        palette["Mat_MTL_Dark_Honed_Granite"],       # 3: Double-height mechanical louver truss bands & podium
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()
    tw_c = Vector((-420.5, -476.0))
    tw_dir = Vector((0.84, -0.54)).normalized()
    tw_perp = Vector((0.54, 0.84)).normalized()
    tw_w, tw_d, tw_h = 44.0, 44.0, 190.0

    # Podium base (`z = 0..14.0m`) + Dark curtain-wall tower shaft (`z = 0..190.0m`)
    add_oriented_box(bm, (-414.7, -468.0), (tw_dir.x, tw_dir.y), (tw_perp.x, tw_perp.y), 68.0, 64.0, 0.0, 14.0, mat_idx=3)
    add_oriented_box(bm, (tw_c.x, tw_c.y), (tw_dir.x, tw_dir.y), (tw_perp.x, tw_perp.y), tw_w - 1.2, tw_d - 1.2, 0.0, tw_h, mat_idx=0)

    # 4 Monumental White Precast-Concrete Corner Mega-Columns (`z = 0..190.0m`)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            cc = tw_c + tw_dir * (sx * (tw_w * 0.5 - 1.8)) + tw_perp * (sy * (tw_d * 0.5 - 1.8))
            add_oriented_box(bm, (cc.x, cc.y), (tw_dir.x, tw_dir.y), (tw_perp.x, tw_perp.y), 4.6, 4.6, 0.0, tw_h + 1.5, mat_idx=1)

    # Horizontal spandrels & 3 signature Nervi double-height mechanical louver bands (`floors 5, 20, 36`)
    for f_i in range(48):
        fz = 4.0 + f_i * 3.85
        is_mech = f_i in (5, 20, 36, 47)
        sh = 2.45 if is_mech else 0.55
        add_oriented_box(bm, (tw_c.x, tw_c.y), (tw_dir.x, tw_dir.y), (tw_perp.x, tw_perp.y), tw_w - 0.4, tw_d - 0.4, fz, fz + sh, mat_idx=(3 if is_mech else 2))

    bm.to_mesh(mesh)
    bm.free()
    return obj


def load_kit_assets(palette):
    assets = {}
    if not os.path.exists(KIT_BLEND_PATH):
        return assets
    target_names = ["jacaranda_tree_LOD0", "gothic_statue", "Master_Street_Bench"]
    with bpy.data.libraries.load(KIT_BLEND_PATH, link=False) as (data_from, data_to):
        avail = set(data_from.objects)
        data_to.objects = [n for n in target_names if n in avail]
    for obj in data_to.objects:
        if obj is not None:
            assets[obj.name] = obj
    tree_template = assets.get("jacaranda_tree_LOD0")
    if tree_template is not None and tree_template.data is not None and len(tree_template.data.polygons) > 35000:
        bpy.context.scene.collection.objects.link(tree_template)
        bpy.context.view_layer.objects.active = tree_template
        dec = tree_template.modifiers.new(name="Decimate_Tree", type='DECIMATE')
        dec.ratio = 0.18
        bpy.ops.object.modifier_apply(modifier=dec.name)
        bpy.context.scene.collection.objects.unlink(tree_template)
    leaf_mat = bpy.data.materials.get("jacaranda_tree_leaves")
    if leaf_mat and leaf_mat.use_nodes:
        nodes = leaf_mat.node_tree.nodes
        links = leaf_mat.node_tree.links
        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        diff_node = next((n for n in nodes if n.type == 'TEX_IMAGE' and n.image and "diff" in n.image.name.lower()), None)
        if bsdf and diff_node:
            mix_g = nodes.new("ShaderNodeMix")
            mix_g.data_type = 'RGBA'
            mix_g.blend_type = 'MIX'
            mix_g.inputs["Factor"].default_value = 0.45
            mix_g.inputs["B"].default_value = kit.hex_to_rgba("#3E7024")
            links.new(mix_g.inputs["A"], diff_node.outputs["Color"])
            links.new(bsdf.inputs["Base Color"], mix_g.outputs["Result"])
    return assets


def build_square_victoria_park_and_streetscape(dossier, palette, col_owned, kit_assets):
    """
    Builds the Square Victoria civic park (`104671932` & `104671946`), Hector Guimard Art Nouveau Paris
    `METROPOLITAIN` Metro entrance (`Square-Victoria–OACI`), Queen Victoria Bronze Monument (`gothic_statue`
    atop stepped granite pedestal), 3 rectangular water fountain basins, granite flagstone walkways,
    lush green grass lawns & low shrub beds (`Queen_Victoria_Monument_South.jpg`), asphalt streets with
    white painted lane & bike-lane lines, concrete sidewalks, streetlamps, benches, and botanical trees.
    """
    mesh = bpy.data.meshes.new("MTL_VM_0012_Park_Streetscape_Mesh")
    obj = bpy.data.objects.new("MTL_VM_0012_Park_Streetscape", mesh)
    col_owned.objects.link(obj)
    for m in [
        palette["Mat_MTL_Street_Asphalt"],         # 0: Roadbed 2K Poly Haven asphalt
        palette["Mat_MTL_SquareVictoria_Pavers"],  # 1: Square Victoria variegated granite flagstones
        palette["Mat_MTL_Light_Granite_Steps"],    # 2: Concrete/granite sidewalks, curbs & pedestal steps
        palette["Mat_MTL_Grass_Lawn"],             # 3: Lush green park lawn
        palette["Mat_MTL_Foliage_Shrub"],          # 4: Low park shrub borders
        palette["Mat_MTL_Dark_Honed_Granite"],     # 5: Fountain basin coping & dark granite curb
        palette["Mat_MTL_Water_Surface"],          # 6: Specular fountain water surface
        palette["Mat_MTL_Guimard_Green"],          # 7: Hector Guimard Art Nouveau green cast-iron metro entrance & parking sign
        palette["Mat_MTL_Amber_Glow"],             # 8: Glowing amber-orange dragon-eye metro lamp globes
        palette["Mat_MTL_Sign_Red"],               # 9: Red METROPOLITAIN sign arch & fire hydrant
        palette["Mat_MTL_Window_Frame_Light"],     # 10: White road lane stripes, fountain jets & lamp globes
        palette["Mat_MTL_CastIron_Black"],         # 11: Heritage black lampposts & utility poles
        palette["Mat_MTL_Sign_Blue"],              # 12: Montreal blue street-name sign blade (Camera 1 Left)
        palette["Mat_MTL_Bronze_Statue"],          # 13: Bronze monument plaques
    ]:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Base Asphalt Roadbed Plane covering the block
    add_oriented_box(bm, (-415.0, -340.0), (1.0, 0.0), (0.0, 1.0), 460.0, 480.0, -0.25, 0.0, mat_idx=0)

    # 2. Rue Saint-Antoine Ouest Sidewalks, Curbs & White Painted Road/Bike Lane Stripes (Camera 1 & Camera 3!)
    sa_dir = Vector((math.sin(math.radians(30.8)), math.cos(math.radians(30.8)))).normalized()
    sa_right = Vector((sa_dir.y, -sa_dir.x))
    sa_center = Vector((-358.0, -275.0))
    # Right (SE) sidewalk along Édifice Greenshields (`width = 3.6m`)
    sw_sa_r = sa_center + sa_right * 8.4
    add_oriented_box(bm, (sw_sa_r.x, sw_sa_r.y), (sa_dir.x, sa_dir.y), (sa_right.x, sa_right.y), 190.0, 3.8, 0.0, 0.15, mat_idx=2)
    # Left (NW) sidewalk along 611333440 & CDPQ (`width = 3.8m`)
    sw_sa_l = sa_center - sa_right * 8.8
    add_oriented_box(bm, (sw_sa_l.x, sw_sa_l.y), (sa_dir.x, sa_dir.y), (sa_right.x, sa_right.y), 190.0, 4.0, 0.0, 0.15, mat_idx=2)
    # Continuous white bike-lane lines & dashed lane divider along Rue Saint-Antoine Ouest (`z = 0.0..0.012m`)
    for lane_off in (2.65, 4.15):
        lp = sa_center + sa_right * lane_off
        add_oriented_box(bm, (lp.x, lp.y), (sa_dir.x, sa_dir.y), (sa_right.x, sa_right.y), 175.0, 0.14, 0.0, 0.012, mat_idx=10)
    for dash_i in range(-10, 11):
        dp = sa_center + sa_dir * (dash_i * 7.5) - sa_right * 1.15
        add_oriented_box(bm, (dp.x, dp.y), (sa_dir.x, sa_dir.y), (sa_right.x, sa_right.y), 3.2, 0.14, 0.0, 0.012, mat_idx=10)

    # Left-sidewalk utility pole + cobra-head streetlamp + blue street sign + red fire hydrant in Camera 1 & Camera 3!
    pole1_l = Vector((-367.8, -267.5))
    ret_pl = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16, radius1=0.14, radius2=0.10, depth=7.8, matrix=Matrix.Translation((pole1_l.x, pole1_l.y, 3.9)))
    for v in ret_pl["verts"]:
        for f in v.link_faces:
            f.material_index = 11
            f.smooth = True
    add_oriented_box(bm, (pole1_l.x + sa_right.x * 0.45, pole1_l.y + sa_right.y * 0.45), (sa_right.x, sa_right.y), (sa_dir.x, sa_dir.y), 0.85, 0.06, 2.85, 3.12, mat_idx=12)
    add_oriented_box(bm, (pole1_l.x + sa_right.x * 1.35, pole1_l.y + sa_right.y * 1.35), (sa_right.x, sa_right.y), (sa_dir.x, sa_dir.y), 2.70, 0.10, 7.45, 7.58, mat_idx=11)
    hyd_xy = pole1_l - sa_dir * 2.2 + sa_right * 0.35
    ret_hy = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=12, radius1=0.14, radius2=0.12, depth=0.78, matrix=Matrix.Translation((hyd_xy.x, hyd_xy.y, 0.52)))
    for v in ret_hy["verts"]:
        for f in v.link_faces:
            f.material_index = 9

    # Right-sidewalk green/charcoal wayfinding parking sign (`P`) & heritage black lampposts along Édifice Greenshields!
    psign_xy = Vector((-352.2, -277.2))
    add_oriented_box(bm, (psign_xy.x, psign_xy.y), (sa_right.x, sa_right.y), (sa_dir.x, sa_dir.y), 0.08, 0.08, 0.15, 3.35, mat_idx=11)
    add_oriented_box(bm, (psign_xy.x, psign_xy.y), (sa_right.x, sa_right.y), (sa_dir.x, sa_dir.y), 0.92, 0.12, 2.15, 3.05, mat_idx=11)
    add_oriented_box(bm, (psign_xy.x, psign_xy.y), (sa_right.x, sa_right.y), (sa_dir.x, sa_dir.y), 0.92, 0.14, 3.05, 3.42, mat_idx=7)
    for lp_xy in (Vector((-357.8, -286.2)), Vector((-346.5, -267.8))):
        ret_lp = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=14, radius1=0.13, radius2=0.07, depth=4.0, matrix=Matrix.Translation((lp_xy.x, lp_xy.y, 2.15)))
        for v in ret_lp["verts"]:
            for f in v.link_faces:
                f.material_index = 11
                f.smooth = True
        ret_gl = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=8, radius1=0.14, radius2=0.22, depth=0.45, matrix=Matrix.Translation((lp_xy.x, lp_xy.y, 4.35)))
        for v in ret_gl["verts"]:
            for f in v.link_faces:
                f.material_index = 10

    # 3. Camera 4 (`Square_Victoria_West_Walk.jpg`) Wide Granite Sidewalk in front of W Montréal Hotel (`901`) + Road Lane Stripe!
    w_p1 = Vector((-445.30, -289.95))
    w_p2 = Vector((-397.71, -318.76))
    w_dir = (w_p2 - w_p1).normalized()
    w_out = Vector((-w_dir.y, w_dir.x)).normalized()
    if w_out.dot(Vector((-424.84, -311.67)) - w_p1) < 0:
        w_out = -w_out
    sw_w_hotel = (w_p1 + w_p2) * 0.5 + w_out * 2.1
    add_oriented_box(bm, (sw_w_hotel.x, sw_w_hotel.y), (w_dir.x, w_dir.y), (w_out.x, w_out.y), 62.0, 4.2, 0.0, 0.15, mat_idx=2)
    curb_w = (w_p1 + w_p2) * 0.5 + w_out * 4.25
    add_oriented_box(bm, (curb_w.x, curb_w.y), (w_dir.x, w_dir.y), (w_out.x, w_out.y), 62.0, 0.24, 0.0, 0.16, mat_idx=5)
    for d_w in (-12.0, -4.0, 4.0, 12.0):
        lw_p = (w_p1 + w_p2) * 0.5 + w_dir * d_w + w_out * 8.2
        add_oriented_box(bm, (lw_p.x, lw_p.y), (w_dir.x, w_dir.y), (w_out.x, w_out.y), 3.4, 0.14, 0.0, 0.012, mat_idx=10)

    # 4. Square Victoria Civic Park (`104671932` & `104671946`): Granite Flagstone Plaza, Lush Lawns & Shrub Borders!
    sq_dir = Vector((-0.848, 0.530)).normalized()   # SE-to-NW axis of Square Victoria (`~302°`)
    sq_perp = Vector((0.530, 0.848)).normalized()   # SW-to-NE axis across Square Victoria (`~32°`)
    # North half of Square Victoria (`(-448.0, -326.0)`) & South half (`(-366.0, -382.0)`)
    add_oriented_box(bm, (-448.0, -326.0), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), 98.0, 25.5, 0.0, 0.14, mat_idx=1)
    add_oriented_box(bm, (-364.0, -380.0), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), 86.0, 25.5, 0.0, 0.14, mat_idx=1)

    # Camera 2 (`Queen_Victoria_Monument_South.jpg` at `[-433.0, -358.75]`, heading `50.4°`) Foreground Flagstone Path & Green Lawn!
    cam2_pos = Vector((-433.00, -358.75))
    cam2_fwd = Vector((math.sin(math.radians(50.4)), math.cos(math.radians(50.4)))).normalized()
    cam2_right = Vector((cam2_fwd.y, -cam2_fwd.x))
    # Foreground granite flagstone walkway leading into the park (`fwd = 0.0..6.2m`)
    path2_c = cam2_pos + cam2_fwd * 3.2 - cam2_right * 0.2
    add_oriented_box(bm, (path2_c.x, path2_c.y), (cam2_fwd.x, cam2_fwd.y), (cam2_right.x, cam2_right.y), 7.5, 2.8, 0.0, 0.15, mat_idx=1)
    # Low soil bed borders flanking the foreground flagstone walkway (botanical leaf shrubs instanced above these beds below!)
    for sh_r, sh_f, sh_w, sh_d in ((-2.3, 2.8, 3.8, 2.2), (2.5, 3.2, 4.2, 2.4)):
        shp = cam2_pos + cam2_fwd * sh_f + cam2_right * sh_r
        add_oriented_box(bm, (shp.x, shp.y), (cam2_fwd.x, cam2_fwd.y), (cam2_right.x, cam2_right.y), sh_w, sh_d, 0.0, 0.16, mat_idx=5)
    # Lush sunlit green grass lawn panel (`fwd = 6.2..15.2m, width = 12.5m`, `z = 0.0..0.155m`)!
    lawn2_c = cam2_pos + cam2_fwd * 10.6 - cam2_right * 1.5
    add_oriented_box(bm, (lawn2_c.x, lawn2_c.y), (cam2_fwd.x, cam2_fwd.y), (cam2_right.x, cam2_right.y), 9.2, 13.0, 0.0, 0.155, mat_idx=3)
    # Granite plaza terrace beyond the lawn (`fwd = 15.2..32.0m`)
    plaza2_c = cam2_pos + cam2_fwd * 23.5 - cam2_right * 2.0
    add_oriented_box(bm, (plaza2_c.x, plaza2_c.y), (cam2_fwd.x, cam2_fwd.y), (cam2_right.x, cam2_right.y), 17.5, 22.0, 0.0, 0.145, mat_idx=1)

    # 5. Three Rectangular Dark-Granite Water Fountain Basins (`satellite_topdown.png` & `Queen_Victoria_Monument_South.jpg`)!
    for fb_xy, fb_len in (
        (Vector((-444.0, -320.5)), 22.0),  # NW Fountain Basin
        (Vector((-416.5, -342.2)), 11.5),  # Mid Fountain Basin (directly visible behind the bench in Camera 2!)
        (Vector((-384.0, -360.0)), 14.0),  # SE Fountain Basin near Queen Victoria Monument
    ):
        add_oriented_box(bm, (fb_xy.x, fb_xy.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), fb_len, 3.2, 0.14, 0.42, mat_idx=5)
        add_oriented_box(bm, (fb_xy.x, fb_xy.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), fb_len - 0.55, 2.65, 0.14, 0.36, mat_idx=6)
        n_jets = max(4, int(fb_len / 2.2))
        for j_i in range(n_jets):
            jp = fb_xy + sq_dir * ((j_i - (n_jets - 1) * 0.5) * 2.0)
            ret_j = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=8, radius1=0.12, radius2=0.04, depth=1.15, matrix=Matrix.Translation((jp.x, jp.y, 0.92)))
            for v in ret_j["verts"]:
                for f in v.link_faces:
                    f.material_index = 10

    # 6. HECTOR GUIMARD ART NOUVEAU PARIS METRO ENTRANCE (`METROPOLITAIN` at `[-425.2, -333.2]`)!
    # Open Art Nouveau green cast-iron balustrade railing with vertical pickets, cartouche shields, curved lamp stalks & glowing amber globes:
    gm_c = Vector((-425.2, -333.2))
    gm_w, gm_d = 5.2, 3.6
    # Dark stairwell opening in the plaza
    add_oriented_box(bm, (gm_c.x, gm_c.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), gm_w - 0.35, gm_d - 0.35, 0.0, 0.16, mat_idx=5)
    for side_s in (-1.0, 1.0):
        sw_p = gm_c + sq_perp * (side_s * gm_d * 0.5)
        # Granite curb base (`z = 0.14..0.46m`) + open bottom/top green cast-iron rails
        add_oriented_box(bm, (sw_p.x, sw_p.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), gm_w, 0.32, 0.14, 0.46, mat_idx=2)
        add_oriented_box(bm, (sw_p.x, sw_p.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), gm_w, 0.10, 0.50, 0.58, mat_idx=7)
        add_oriented_box(bm, (sw_p.x, sw_p.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), gm_w + 0.15, 0.16, 1.36, 1.48, mat_idx=7)
        # Open vertical Art Nouveau pickets + ornate shield medallions (`z = 0.54..1.38m`)
        for pk_i in range(15):
            u_pk = -gm_w * 0.46 + (pk_i / 14.0) * (gm_w * 0.92)
            pk_xy = sw_p + sq_dir * u_pk
            pk_w = 0.22 if (pk_i % 3 == 1) else 0.045
            pk_z0 = 0.68 if (pk_i % 3 == 1) else 0.50
            pk_z1 = 1.26 if (pk_i % 3 == 1) else 1.40
            add_oriented_box(bm, (pk_xy.x, pk_xy.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), pk_w, 0.08, pk_z0, pk_z1, mat_idx=7)
    back_p = gm_c + sq_dir * (gm_w * 0.5)
    add_oriented_box(bm, (back_p.x, back_p.y), (sq_perp.x, sq_perp.y), (sq_dir.x, sq_dir.y), gm_d, 0.32, 0.14, 0.46, mat_idx=2)
    add_oriented_box(bm, (back_p.x, back_p.y), (sq_perp.x, sq_perp.y), (sq_dir.x, sq_dir.y), gm_d, 0.10, 0.50, 0.58, mat_idx=7)
    add_oriented_box(bm, (back_p.x, back_p.y), (sq_perp.x, sq_perp.y), (sq_dir.x, sq_dir.y), gm_d + 0.12, 0.16, 1.36, 1.48, mat_idx=7)
    for pk_j in range(11):
        v_pk = -gm_d * 0.45 + (pk_j / 10.0) * (gm_d * 0.90)
        pk_xy = back_p + sq_perp * v_pk
        pk_w = 0.22 if (pk_j % 3 == 1) else 0.045
        add_oriented_box(bm, (pk_xy.x, pk_xy.y), (sq_perp.x, sq_perp.y), (sq_dir.x, sq_dir.y), pk_w, 0.08, 0.50, 1.40, mat_idx=7)

    # Front entrance arch with curved green cast-iron stalks (`z = 0.48..4.15m`), red `METROPOLITAIN` sign panel & 2 glowing amber globes!
    front_p = gm_c - sq_dir * (gm_w * 0.5)
    for side_s in (-1.0, 1.0):
        st_p = front_p + sq_perp * (side_s * (gm_d * 0.5 - 0.15))
        ret_st = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=14, radius1=0.14, radius2=0.08, depth=3.45, matrix=Matrix.Translation((st_p.x, st_p.y, 1.85)))
        for v in ret_st["verts"]:
            for f in v.link_faces:
                f.material_index = 7
                f.smooth = True
        # Curved upper floral arch arm + glowing amber-orange "dragon-eye" luminaire globe (`z = 3.55..4.05m`)
        gl_p = front_p + sq_perp * (side_s * (gm_d * 0.5 - 0.55)) - sq_dir * 0.25
        arm_p = (st_p + gl_p) * 0.5
        add_oriented_box(bm, (arm_p.x, arm_p.y), (sq_perp.x, sq_perp.y), (sq_dir.x, sq_dir.y), 0.55, 0.12, 3.45, 3.85, mat_idx=7)
        ret_gb = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.30, matrix=Matrix.Translation((gl_p.x, gl_p.y, 3.78)))
        for v in ret_gb["verts"]:
            for f in v.link_faces:
                f.material_index = 8
                f.smooth = True
    # Ornate green cast-iron header arch + red-and-white `METROPOLITAIN` sign panel (`z = 3.10..3.65m`)
    add_oriented_box(bm, (front_p.x, front_p.y), (sq_perp.x, sq_perp.y), (sq_dir.x, sq_dir.y), gm_d - 0.2, 0.14, 3.12, 3.62, mat_idx=9)
    add_oriented_box(bm, (front_p.x, front_p.y), (sq_perp.x, sq_perp.y), (sq_dir.x, sq_dir.y), gm_d + 0.1, 0.20, 3.58, 3.72, mat_idx=7)

    # 7. QUEEN VICTORIA MONUMENT PEDESTAL (`[-392.0, -366.0]`, visible in `satellite_topdown.png` & Overview Snapshot!)
    qv_c = Vector((-392.0, -366.0))
    add_oriented_box(bm, (qv_c.x, qv_c.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), 9.5, 9.5, 0.14, 0.35, mat_idx=3)
    for tier_w, z0, z1 in ((5.4, 0.14, 0.65), (4.2, 0.65, 1.25), (2.8, 1.25, 4.45), (3.2, 4.45, 4.85)):
        add_oriented_box(bm, (qv_c.x, qv_c.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), tier_w, tier_w, z0, z1, mat_idx=2)
    add_oriented_box(bm, (qv_c.x, qv_c.y), (sq_dir.x, sq_dir.y), (sq_perp.x, sq_perp.y), 2.95, 2.95, 2.15, 3.45, mat_idx=13)

    bm.to_mesh(mesh)
    bm.free()

    # Instance High-Poly `gothic_statue` atop the Queen Victoria Monument Pedestal (`[-392.0, -366.0, 4.85]`)
    statue_src = kit_assets.get("gothic_statue")
    if statue_src is not None:
        st_obj = bpy.data.objects.new("MTL_VM_0012_Queen_Victoria_Statue", statue_src.data.copy())
        col_owned.objects.link(st_obj)
        st_obj.data.materials.clear()
        st_obj.data.materials.append(palette["Mat_MTL_Bronze_Statue"])
        st_obj.location = (-392.0, -366.0, 6.45)
        st_obj.scale = (2.8, 2.8, 2.8)
        st_obj.rotation_euler = (0.0, 0.0, math.radians(-38.0))

    # Instance High-Poly `Master_Street_Bench` Park Benches (including the foreground/midground benches in Camera 2!)
    bench_src = kit_assets.get("Master_Street_Bench")
    if bench_src is not None:
        bench_coords = [
            (cam2_pos.x + cam2_fwd.x * 15.2 - cam2_right.x * 2.1, cam2_pos.y + cam2_fwd.y * 15.2 - cam2_right.y * 2.1, math.radians(40.0)),
            (cam2_pos.x + cam2_fwd.x * 18.8 - cam2_right.x * 2.4, cam2_pos.y + cam2_fwd.y * 18.8 - cam2_right.y * 2.4, math.radians(40.0)),
            (cam2_pos.x + cam2_fwd.x * 16.5 - cam2_right.x * 5.8, cam2_pos.y + cam2_fwd.y * 16.5 - cam2_right.y * 5.8, math.radians(40.0)),
            (-438.0, -325.0, math.radians(122.0)),
            (-446.0, -320.0, math.radians(122.0)),
            (-388.0, -362.0, math.radians(122.0)),
        ]
        for b_idx, (bx, by, brot) in enumerate(bench_coords):
            b_obj = bpy.data.objects.new(f"MTL_VM_0012_Bench_{b_idx}", bench_src.data)
            col_owned.objects.link(b_obj)
            b_obj.location = (bx, by, 0.56)
            b_obj.scale = (1.15, 1.15, 1.15)
            b_obj.rotation_euler = (0.0, 0.0, brot)

    # Instance Genuine Poly Haven `jacaranda_tree_LOD0` Botanical Trees & Extracted Leaf-Cluster Shrubs!
    tree_src = kit_assets.get("jacaranda_tree_LOD0")
    if tree_src is not None:
        rng = random.Random(12012)
        # 1. Create a genuine botanical leaf-cluster shrub mesh extracted from the upper leafy crown of `jacaranda_tree_LOD0`!
        shrub_mesh = bpy.data.meshes.new("MTL_VM_0012_Botanical_Shrub_Mesh")
        for m in tree_src.data.materials:
            shrub_mesh.materials.append(m)
        bm_sh = bmesh.new()
        bm_sh.from_mesh(tree_src.data)
        del_faces = [f for f in bm_sh.faces if f.material_index == 0 or f.calc_center_median().z < 3.2]
        if len(del_faces) < len(bm_sh.faces) - 20:
            bmesh.ops.delete(bm_sh, geom=del_faces, context='FACES')
        del_verts = [v for v in bm_sh.verts if len(v.link_faces) == 0]
        if del_verts:
            bmesh.ops.delete(bm_sh, geom=del_verts, context='VERTS')
        if bm_sh.verts:
            xs = [v.co.x for v in bm_sh.verts]
            ys = [v.co.y for v in bm_sh.verts]
            zs = [v.co.z for v in bm_sh.verts]
            cx_s, cy_s, z_min_s = 0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys)), min(zs)
            span_xy = max(1.0, max(max(xs) - min(xs), max(ys) - min(ys)))
            span_z = max(1.0, max(zs) - z_min_s)
            for v in bm_sh.verts:
                v.co.x = (v.co.x - cx_s) / span_xy * 1.75
                v.co.y = (v.co.y - cy_s) / span_xy * 1.75
                v.co.z = (v.co.z - z_min_s) / span_z * 0.78
        bm_sh.to_mesh(shrub_mesh)
        bm_sh.free()

        # Instance botanical leaf-cluster shrubs flanking the foreground flagstone path in Camera 2 (`Queen_Victoria_Monument_South.jpg`)
        shrub_instances = []
        for s_side in (-2.35, 2.45):
            for s_fwd in (1.6, 2.5, 3.4, 4.3):
                sp2 = cam2_pos + cam2_fwd * s_fwd + cam2_right * s_side
                shrub_instances.append((sp2.x, sp2.y, 0.14, 1.35, 1.35, 0.95))
        # Instance botanical leaf-cluster shrubs inside all 7 W Hotel sidewalk café planters in Camera 4 (`Square_Victoria_West_Walk.jpg`)
        for p_idx in range(7):
            pu = 27.6 + p_idx * 1.82
            p_box_xy = w_p1 + w_dir * pu + w_out * 2.55
            shrub_instances.append((p_box_xy.x, p_box_xy.y, 0.88, 0.95, 0.65, 0.85))
        for side_u in (26.8, 39.5):
            sp_xy = w_p1 + w_dir * side_u + w_out * 1.45
            shrub_instances.append((sp_xy.x, sp_xy.y, 0.88, 0.75, 1.15, 0.85))

        for sh_i, (sx, sy, sz, sc_x, sc_y, sc_z) in enumerate(shrub_instances):
            sh_obj = bpy.data.objects.new(f"MTL_VM_0012_Botanical_Shrub_{sh_i}", shrub_mesh)
            col_owned.objects.link(sh_obj)
            sh_obj.location = (sx, sy, sz)
            sh_obj.scale = (sc_x, sc_y, sc_z)
            sh_obj.rotation_euler = (0.0, 0.0, (sh_i * 1.37) % (2.0 * math.pi))

        # 2. Instance Full Park & Street Trees (filtering out right-sidewalk trees that clipped the white vans or blocked Édifice Greenshields!)
        tree_coords = []
        for t in dossier["osm_features"].get("trees", []):
            tx, ty = t["x"], t["y"]
            # Filter out right-hand sidewalk along Édifice Greenshields (`tx > -375.0 and -335.0 < ty < -260.0`)
            if tx > -375.0 and -335.0 < ty < -260.0:
                continue
            tree_coords.append((tx, ty, 0.54, 0.62))
        # Add 2 small ornamental street trees on the sidewalk behind the parked cars in Camera 1 & Camera 3
        tree_coords.extend([
            (-356.2, -283.8, 0.15, 0.18),
            (-349.5, -272.5, 0.16, 0.19),
        ])
        for idx, (tx, ty, s_xy, s_z) in enumerate(tree_coords):
            # Keep Camera 2 lens (`-433.0, -358.75`) clear within 5.5m so the foreground walkway is unobstructed
            if math.hypot(tx - (-433.0), ty - (-358.75)) < 5.5:
                continue
            t_obj = bpy.data.objects.new(f"MTL_VM_0012_Tree_{idx}", tree_src.data)
            col_owned.objects.link(t_obj)
            t_obj.location = (tx, ty, 0.12)
            t_obj.scale = (s_xy * rng.uniform(0.92, 1.08), s_xy * rng.uniform(0.92, 1.08), s_z * rng.uniform(0.94, 1.08))
            t_obj.rotation_euler = (0.0, 0.0, rng.uniform(0.0, 2.0 * math.pi))


def build_context_proxies_0012(dossier, palette, col_proxy):
    """
    Builds non-owned context buildings (`Block_MTL-VM-0012_Context_Proxy`) and contoured 3D street vehicles:
    1. `611333440` (`415 Rue Saint-Antoine Ouest`): 4-story red-brick & grey-limestone corner building in Left Foreground of Camera 1 & Camera 3!
    2. `104674800`: 11-story commercial building east of Édifice Greenshields.
    3. `Proxy_StAntoine_East_Canyon`: 8-story heritage red-brick building + 22-story pale-stone tower with dark slate Château/Mansard crown
       directly NE of Édifice Greenshields along Rue Saint-Antoine Ouest (Center-Left Background of Camera 1 & Camera 3!).
    4. Contoured 3D Commercial Vans, Sedans & SUVs in all 4 Cameras!
    """
    b_map = {b["id"]: b for b in dossier["osm_features"]["buildings"]}

    # 1. `611333440` (4-story Red-Brick & Grey-Limestone Corner Building on Left of Camera 1 & Camera 3!)
    b_611 = b_map.get(611333440)
    if b_611:
        build_detailed_heritage_building(
            b_611, height=15.5,
            mat_wall=palette["Mat_MTL_Heritage_RedBrick"],
            mat_trim=palette["Mat_MTL_PierreGrise_Limestone"],
            mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
            mat_window=palette["Mat_MTL_Window_Glass_Dark"],
            mat_frame=palette["Mat_MTL_Window_Frame_Light"],
            collection=col_proxy, prefix="Proxy_415_StAntoine"
        )

    # 2. `104674800` (11-story commercial building)
    b_104 = b_map.get(104674800)
    if b_104:
        build_detailed_heritage_building(
            b_104, height=40.0,
            mat_wall=palette["Mat_MTL_WarmBuff_Limestone"],
            mat_trim=palette["Mat_MTL_PierreGrise_Limestone"],
            mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
            mat_window=palette["Mat_MTL_Window_Glass_Dark"],
            mat_frame=palette["Mat_MTL_Window_Frame_Light"],
            collection=col_proxy, prefix="Proxy_Commercial"
        )

    # 3. Rue Saint-Antoine East Continuation Canyon + Contoured 3D Street Vehicles!
    mesh_ctx = bpy.data.meshes.new("Proxy_StAntoine_Canyon_And_Vehicles_Mesh")
    obj_ctx = bpy.data.objects.new("Proxy_StAntoine_Canyon_And_Vehicles", mesh_ctx)
    col_proxy.objects.link(obj_ctx)
    for m in [
        palette["Mat_MTL_Heritage_RedBrick"],        # 0: 8-story heritage red-brick building
        palette["Mat_MTL_WarmBuff_Limestone"],       # 1: 22-story pale-stone tower & trim
        palette["Mat_MTL_Slate_Roof_Dark"],          # 2: Pitched Château/Mansard crown & dark roofs
        palette["Mat_MTL_Window_Glass_Dark"],        # 3: Recessed window glass & vehicle windshields
        palette["Mat_MTL_Window_Frame_Light"],       # 4: White window frames
        palette["Mat_MTL_Auto_White"],               # 5: White commercial vans & white sedan
        palette["Mat_MTL_Auto_Silver"],              # 6: Silver sedan & alloy wheel hubcaps
        palette["Mat_MTL_Auto_Charcoal"],            # 7: Dark charcoal SUV / pickup / sedan
        palette["Mat_MTL_Rubber_Tire"],              # 8: Cylindrical rubber tires
        palette["Mat_MTL_Sign_Red"],                 # 9: Van taillights & ladder accent
    ]:
        obj_ctx.data.materials.append(m)

    bm = bmesh.new()
    sa_dir = Vector((math.sin(math.radians(30.8)), math.cos(math.radians(30.8)))).normalized()
    sa_out = Vector((-sa_dir.y, sa_dir.x)).normalized()  # pointing NW toward Rue Saint-Antoine Ouest
    sa_in = -sa_out

    # 8-story heritage red-brick building (`(-336.0, -260.5)` to `(-318.0, -230.2)`, `z = 0..30.5m`)
    p_rb1 = Vector((-336.0, -260.5))
    p_rb2 = Vector((-318.0, -230.2))
    rb_c = (p_rb1 + p_rb2) * 0.5 + sa_in * 11.5
    add_oriented_box(bm, (rb_c.x, rb_c.y), (sa_dir.x, sa_dir.y), (sa_out.x, sa_out.y), 34.0, 21.5, 0.0, 30.5, mat_idx=0)
    build_recessed_window_facade_along_edge(bm, p_rb1, p_rb2, sa_out, 0.0, 30.5, n_floors=8, bay_target_width=3.2, recess_depth=0.48, wall_mat=0, trim_mat=1, glass_mat=3, frame_mat=4)

    # 22-story pale-stone tower (`(-317.5, -229.5)` to `(-296.0, -193.5)`, `z = 0..72.0m`) + Pitched Dark Slate Château Crown (`z = 72.0..79.5m`)!
    p_ch1 = Vector((-317.5, -229.5))
    p_ch2 = Vector((-296.0, -193.5))
    ch_c = (p_ch1 + p_ch2) * 0.5 + sa_in * 13.0
    add_oriented_box(bm, (ch_c.x, ch_c.y), (sa_dir.x, sa_dir.y), (sa_out.x, sa_out.y), 40.5, 24.5, 0.0, 72.0, mat_idx=1)
    build_recessed_window_facade_along_edge(bm, p_ch1, p_ch2, sa_out, 0.0, 72.0, n_floors=18, bay_target_width=3.4, recess_depth=0.48, wall_mat=1, trim_mat=4, glass_mat=3, frame_mat=4)
    add_oriented_box(bm, (ch_c.x, ch_c.y), (sa_dir.x, sa_dir.y), (sa_out.x, sa_out.y), 36.5, 20.5, 72.0, 79.5, mat_idx=2)

    # 4. Contoured 3D Vehicles across all 4 Street View Cameras:
    for vx, vy, v_ang, b_mat, v_style in (
        (-360.8, -287.2, 59.2, 5, "van"),    # Cam 1 right-foreground white `SECUR PLUS` van with ladder rack
        (-371.2, -304.8, 59.2, 5, "van"),    # Cam 3 right-foreground white van
        (-366.8, -297.4, 59.2, 6, "sedan"),  # Cam 3 right-midground silver sedan
        (-363.2, -291.4, 59.2, 5, "sedan"),  # Cam 3 right-midground white sedan
        (-352.5, -273.5, 59.2, 7, "suv"),    # Cam 1 right-midground dark pickup/SUV
        (-354.5, -267.8, 59.2, 7, "sedan"),  # Cam 1 & Cam 3 center-lane dark sedan
        (-378.2, -296.5, 59.2, 6, "sedan"),  # Cam 3 left-curb silver sedan
        # - Camera 2 (`Queen_Victoria_Monument_South.jpg`): White compact service van on right (`fwd=17.2m, right=+4.2m`)
        (-417.0, -351.0, -32.0, 5, "van"),
        # - Camera 4 (`Square_Victoria_West_Walk.jpg`): Dark charcoal pickup/SUV parked right of the yellow/charcoal patio (`(-409.5, -313.8)`)
        (-409.5, -313.8, 148.0, 7, "suv"),
    ):
        add_contoured_vehicle(bm, vx, vy, v_ang, body_mat=b_mat, glass_mat=3, tire_mat=8, rim_mat=6, style=v_style, accent_mat=9)

    bm.to_mesh(mesh_ctx)
    bm.free()
    apply_bevel_and_smooth(obj_ctx, width=0.025, segments=2)


def setup_lighting_and_world(scene):
    scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 64
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    bg = nodes.new("ShaderNodeBackground")
    out = nodes.new("ShaderNodeOutputWorld")
    hdri_path = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")
    img_hdri = load_image_safe(hdri_path, colorspace=None)
    if img_hdri:
        env = nodes.new("ShaderNodeTexEnvironment")
        env.image = img_hdri
        tc = nodes.new("ShaderNodeTexCoord")
        map_n = nodes.new("ShaderNodeMapping")
        map_n.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(115.0))
        links.new(map_n.inputs["Vector"], tc.outputs["Generated"])
        links.new(env.inputs["Vector"], map_n.outputs["Vector"])
        links.new(bg.inputs["Color"], env.outputs["Color"])
        bg.inputs["Strength"].default_value = 1.15
    else:
        sky = nodes.new("ShaderNodeTexSky")
        links.new(bg.inputs["Color"], sky.outputs["Color"])
        bg.inputs["Strength"].default_value = 0.9

    links.new(out.inputs["Surface"], bg.outputs["Background"])

    sun_data = bpy.data.lights.new(name="MTL_Sun", type='SUN')
    sun_data.energy = 3.6
    sun_data.color = (1.0, 0.96, 0.90)
    if hasattr(sun_data, "angle"):
        sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new(name="MTL_Sun", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(38.0), math.radians(16.0), math.radians(140.0))


def render_cameras(dossier, col_root, iter_tag="iter2"):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100

    for cam_info in dossier["streetview_cameras"]:
        label = cam_info["label"]
        cx, cy = cam_info["blender_cam_xy_m"]
        heading = cam_info.get("heading", cam_info.get("heading_deg", 0.0))
        pitch = 10.0 if "heading" in cam_info else cam_info.get("pitch_deg", 12.0)
        fov = cam_info.get("fov_deg", 90.0)

        cam_data = bpy.data.cameras.new(name=f"Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(fov)
        cam_data.clip_start = 0.2
        cam_data.clip_end = 1200.0

        cam_obj = bpy.data.objects.new(name=f"Cam_{label}", object_data=cam_data)
        col_root.objects.link(cam_obj)
        cam_obj.location = (cx, cy, 1.7)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch), 0.0, math.radians(-heading))

        scene.camera = cam_obj
        out_path = os.path.join(RENDERS_DIR, f"{iter_tag}_{label}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        if iter_tag != "iter1":
            try:
                shutil.copyfile(out_path, os.path.join(RENDERS_DIR, f"iter1_{label}.png"))
            except Exception:
                pass
        print(f"Rendered Street View Camera ({label}, heading={heading}, pitch={pitch}) -> {out_path}")

    # Overview Camera (1280x720) framing full 190m Tour de la Bourse, Square Victoria, Guimard Metro Entrance, Queen Victoria Statue, W Hotel & Greenshields!
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    ov_data = bpy.data.cameras.new(name="Cam_Overview")
    ov_data.lens_unit = 'FOV'
    ov_data.angle = math.radians(76.0)
    ov_data.clip_start = 0.5
    ov_data.clip_end = 2500.0
    ov_obj = bpy.data.objects.new(name="Cam_Overview", object_data=ov_data)
    col_root.objects.link(ov_obj)
    ov_obj.location = (-545.0, -225.0, 165.0)
    direction = Vector((-405.0, -385.0, 48.0)) - ov_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    ov_obj.rotation_euler = rot_quat.to_euler()

    scene.camera = ov_obj
    snap_path = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
    scene.render.filepath = snap_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Overview Snapshot -> {snap_path}")


def main():
    clear_scene()
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    palette = kit.create_montreal_material_palette()
    palette = create_custom_materials(palette)
    kit_assets = load_kit_assets(palette)

    col_root = get_or_create_collection(f"Block_{BLOCK_ID}")
    col_owned = get_or_create_collection(f"Block_{BLOCK_ID}_Owned", parent=col_root)
    col_proxy = get_or_create_collection(f"Block_{BLOCK_ID}_Context_Proxy", parent=col_root)

    build_square_victoria_park_and_streetscape(dossier, palette, col_owned, kit_assets)

    # Skip underground/park metro polygons (`38911515`, `1411142485`) so Square Victoria Park is open and unobstructed
    custom_owned_ids = {104674804, 112881749, 19896201, 38911515, 1411142485}
    custom_proxy_ids = {611333440, 104674800, 38911515, 1411142485}

    for b in dossier["osm_features"]["buildings"]:
        b_id = b["id"]
        is_owned = b.get("is_primary_owner", True)
        levels = float(b.get("tags", {}).get("building:levels", 5))
        h_tag = b.get("tags", {}).get("height")
        h = float(h_tag) if h_tag else max(14.0, levels * 3.8)
        if b_id == 112862480:
            h = 56.0  # La Maison de l'OACI (15 stories)

        if is_owned:
            if b_id == 104674804:
                build_greenshields_104674804(b, palette, col_owned)
            elif b_id == 112881749:
                build_jacques_parizeau_w_hotel_112881749(b, palette, col_owned)
            elif b_id == 19896201:
                build_place_victoria_19896201(b, palette, col_owned)
            elif b_id in custom_owned_ids:
                continue
            else:
                wall_mat = (
                    palette["Mat_MTL_Heritage_RedBrick"]
                    if (b_id % 5 == 0)
                    else (palette["Mat_MTL_PierreGrise_Limestone"] if (b_id % 2 == 0) else palette["Mat_MTL_WarmBuff_Limestone"])
                )
                build_detailed_heritage_building(
                    b, height=h, mat_wall=wall_mat, mat_trim=palette["Mat_MTL_PierreGrise_Limestone"],
                    mat_roof=palette["Mat_MTL_Slate_Roof_Dark"], mat_window=palette["Mat_MTL_Window_Glass_Dark"],
                    mat_frame=palette["Mat_MTL_Window_Frame_Light"], collection=col_owned, prefix="Bldg_Owned"
                )
        else:
            if b_id in custom_proxy_ids:
                continue
            build_detailed_heritage_building(
                b, height=h, mat_wall=palette["Mat_MTL_PierreGrise_Limestone"],
                mat_trim=palette["Mat_MTL_WarmBuff_Limestone"], mat_roof=palette["Mat_MTL_Slate_Roof_Dark"],
                mat_window=palette["Mat_MTL_Window_Glass_Dark"], mat_frame=palette["Mat_MTL_Window_Frame_Light"],
                collection=col_proxy, prefix="Bldg_Proxy"
            )

    build_context_proxies_0012(dossier, palette, col_proxy)

    setup_lighting_and_world(bpy.context.scene)
    render_cameras(dossier, col_root, iter_tag="iter2")

    blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.blend")
    tmp_blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}_tmp.blend")
    usdc_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.usdc")
    bpy.ops.wm.usd_export(filepath=usdc_path)
    bpy.context.preferences.filepaths.save_version = 0
    for stale in (tmp_blend_path, blend_path + "@", blend_path + "1"):
        if os.path.exists(stale):
            try:
                os.remove(stale)
            except Exception:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend_path, copy=True)
    try:
        os.replace(tmp_blend_path, blend_path)
    except Exception:
        shutil.copyfile(tmp_blend_path, blend_path)
    print(f"Saved {blend_path} and exported {usdc_path}")


if __name__ == "__main__":
    main()

