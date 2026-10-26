"""
Headless Builder for City Block MTL-VM-0007 (Iteration 2 — AAA Poly Haven PBR)
(Rue Saint-Sulpice & Cours Le Royer Historic Block — 430 Rue Saint-Sulpice)
==============================================================================
Constructs all 31 owned historic buildings (Cours Le Royer 18th/19th-century
warehouse conversions, Le Sulpice Hotel, Tommy Café corner building, Rue
Saint-Sulpice Victorian mansard buildings) inside `Block_MTL-VM-0007_Owned`,
and 13 neighbor context buildings inside `Block_MTL-VM-0007_Context_Proxy`.

Iteration 2 Upgrades:
  1. All materials wired to verified 2K Poly Haven PBR textures in `assets/polyhaven/`
     (`sandstone_blocks_05`, `castle_brick_02_red`, `cobblestone_floor_08`, `asphalt_02`)
     combined with procedural coursed ashlar/slab mortar joints so zero walls, roofs,
     or sidewalks appear flat or untextured.
  2. View 1 (`Rue_SaintSulpice_Facade`): Camera stepped back to street centerline framing
     the left burgundy paneled double entrance door + fanlight + hanging blue sign +
     wall lantern, two central triple-arched Venetian ground windows with interior
     shutters, iron guard rails, basement vent wells & oval tie-rod anchors, round-arched
     2nd/3rd floor windows with keystones, and right-side paired teal arched windows.
  3. View 2 (`Cours_Le_Royer_Courtyard`): Camera stepped back to frame all 3 wide bays
     and 3.5 storeys of Le Sulpice Hotel, seamless coursed grey ashlar piers, heavy
     projecting 2nd-floor cornice, 4-pane storefront & upper windows, circular iron
     medallions inside Juliette balconies, jointed concrete sidewalk, granite curb,
     and flush cast-iron manhole cover.
  4. View 3 (`Corner_Rue_SaintPaul`): Deep glossy forest-green (`#14361D`) storefront,
     recessed double-door entrance vestibule with glass panels & transom, menu board
     (`151`), gooseneck café lamps, celadon/copper crowning roof cornice, and across
     the lane the red-brick & stone-quoin building (`339876874`).
  5. View 4 (`Corner_Rue_DeBresoles`): Rugged fieldstone rubble (`moellons`) party wall
     with recessed blind window niche & street-level metal utility door, full 6-over-6
     recessed sash windows on the 4-storey red-brick wing (no wall-buried slits),
     projecting pedimented mansard dormers, cobblestone roadway, and foreground curved
     stone planter with overhanging tree branches.
"""
import os
import sys
import json
import math
import bpy
import bmesh
from mathutils import Vector, Euler

PROJECT_ROOT = r"C:\Users\Felipe\Documents\coding\montreal"
if os.path.join(PROJECT_ROOT, "src") not in sys.path:
    sys.path.append(os.path.join(PROJECT_ROOT, "src"))

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0007"
DOSSIER_PATH = os.path.join(PROJECT_ROOT, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(PROJECT_ROOT, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_BLOCKS_DIR = os.path.join(PROJECT_ROOT, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(PROJECT_ROOT, "output", "renders")
KIT_BLEND_PATH = os.path.join(PROJECT_ROOT, "assets", "montreal_kit.blend")
PH_DIR = os.path.join(PROJECT_ROOT, "assets", "polyhaven")


# ---------------------------------------------------------------------------
# 1. VERIFIED POLY HAVEN 2K PBR MATERIALS + COURSED ASHLAR MORTAR SHADERS
# ---------------------------------------------------------------------------
def build_ph_pbr_mat(name, diff_file, rough_file, nor_file, tint=(1.0, 1.0, 1.0, 1.0),
                     scale=0.28, rough_mult=1.0, normal_str=0.65, brick_grid=None):
    """
    Creates a 2K Poly Haven PBR material using `projection='BOX'` and optional
    3D coursed ashlar/slab mortar joints (`brick_grid=(scale_z, brick_w, row_h, mortar_col)`).
    """
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    diff_path = os.path.join(PH_DIR, diff_file) if diff_file else ""
    rough_path = os.path.join(PH_DIR, rough_file) if rough_file else ""
    nor_path = os.path.join(PH_DIR, nor_file) if nor_file else ""

    base_color_out = None
    if diff_path and os.path.exists(diff_path):
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = bpy.data.images.load(diff_path, check_existing=True)
        tex_d.projection = 'BOX'
        tex_d.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])
        if tint != (1.0, 1.0, 1.0, 1.0):
            mix = nodes.new("ShaderNodeMix")
            mix.data_type = 'RGBA'
            mix.blend_type = 'MULTIPLY'
            mix.inputs["Factor"].default_value = 0.72
            mix.inputs[6].default_value = tint
            links.new(tex_d.outputs["Color"], mix.inputs[7])
            base_color_out = mix.outputs[2]
        else:
            base_color_out = tex_d.outputs["Color"]

    if brick_grid is not None:
        b_scale, b_w, b_h, mortar_col = brick_grid
        b_tex = nodes.new("ShaderNodeTexBrick")
        b_tex.offset = 0.5
        b_tex.inputs["Scale"].default_value = b_scale
        b_tex.inputs["Brick Width"].default_value = b_w
        b_tex.inputs["Row Height"].default_value = b_h
        b_tex.inputs["Mortar Size"].default_value = 0.018
        b_tex.inputs["Mortar Smooth"].default_value = 0.1
        b_tex.inputs["Color1"].default_value = tint
        b_tex.inputs["Color2"].default_value = (tint[0] * 0.90, tint[1] * 0.90, tint[2] * 0.90, 1.0)
        b_tex.inputs["Mortar"].default_value = mortar_col
        links.new(tex_coord.outputs["Object"], b_tex.inputs["Vector"])

        if base_color_out is not None:
            mix_b = nodes.new("ShaderNodeMix")
            mix_b.data_type = 'RGBA'
            mix_b.blend_type = 'MULTIPLY'
            mix_b.inputs["Factor"].default_value = 0.55
            links.new(base_color_out, mix_b.inputs[6])
            links.new(b_tex.outputs["Color"], mix_b.inputs[7])
            links.new(mix_b.outputs[2], bsdf.inputs["Base Color"])
        else:
            links.new(b_tex.outputs["Color"], bsdf.inputs["Base Color"])
    elif base_color_out is not None:
        links.new(base_color_out, bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = tint

    if rough_path and os.path.exists(rough_path):
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = bpy.data.images.load(rough_path, check_existing=True)
        tex_r.image.colorspace_settings.name = 'Non-Color'
        tex_r.projection = 'BOX'
        tex_r.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_r.inputs["Vector"])
        math_r = nodes.new("ShaderNodeMath")
        math_r.operation = 'MULTIPLY'
        math_r.inputs[1].default_value = rough_mult
        links.new(tex_r.outputs["Color"], math_r.inputs[0])
        links.new(math_r.outputs["Value"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.65

    if nor_path and os.path.exists(nor_path):
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = bpy.data.images.load(nor_path, check_existing=True)
        tex_n.image.colorspace_settings.name = 'Non-Color'
        tex_n.projection = 'BOX'
        tex_n.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal_str
        links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def create_solid_mat(name, color, roughness=0.45, metallic=0.0, ior=1.45):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = ior
    return mat


def create_block_palette():
    palette = kit.create_montreal_material_palette()

    # 1. Coursed Montreal Grey Ashlar Limestone (Pierre Grise — flat-faced dressed stone with crisp mortar joints)
    palette["Mat_Stone_Grey"] = build_ph_pbr_mat(
        "Mat_Stone_Grey",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint=(0.68, 0.69, 0.67, 1.0), scale=0.32, rough_mult=0.92, normal_str=0.50,
        brick_grid=(1.4, 0.85, 0.42, (0.36, 0.37, 0.35, 1.0))
    )
    # 2. Warm Buff / Cream Dressed Limestone (Tommy Café & Victorian Trim — restrained normal map)
    palette["Mat_Stone_Buff"] = build_ph_pbr_mat(
        "Mat_Stone_Buff",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint=(0.86, 0.83, 0.77, 1.0), scale=0.35, rough_mult=0.88, normal_str=0.48,
        brick_grid=(1.3, 0.90, 0.45, (0.50, 0.48, 0.44, 1.0))
    )
    # 3. Rugged Fieldstone Rubble Masonry (`moellons` — 339877652 NW Gable Party Wall & Plinths)
    palette["Mat_Stone_Rubble"] = build_ph_pbr_mat(
        "Mat_Stone_Rubble",
        "cobblestone_floor_08_Diffuse_2k.jpg",
        "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg",
        tint=(0.66, 0.63, 0.58, 1.0), scale=0.48, rough_mult=1.02, normal_str=1.55
    )
    # 4. Dressed Ashlar Quoin & Pilaster Trim (flat-faced dressed stone, no pillow distortion)
    palette["Mat_Stone_Quoin"] = build_ph_pbr_mat(
        "Mat_Stone_Quoin",
        "sandstone_blocks_05_Diffuse_2k.jpg",
        "sandstone_blocks_05_Rough_2k.jpg",
        "sandstone_blocks_05_nor_gl_2k.jpg",
        tint=(0.76, 0.75, 0.72, 1.0), scale=0.38, rough_mult=0.88, normal_str=0.42,
        brick_grid=(1.5, 0.80, 0.42, (0.42, 0.42, 0.40, 1.0))
    )
    # 5. Heritage Red Brick (Poly Haven castle_brick_02_red)
    palette["Mat_Red_Brick"] = build_ph_pbr_mat(
        "Mat_Red_Brick",
        "castle_brick_02_red_Diffuse_2k.jpg",
        "castle_brick_02_red_Rough_2k.jpg",
        "castle_brick_02_red_nor_gl_2k.jpg",
        tint=(0.76, 0.40, 0.32, 1.0), scale=0.38, rough_mult=0.95, normal_str=1.35
    )
    # 6. Cobblestone Street & Promenade (Poly Haven cobblestone_floor_08)
    palette["Mat_Cobble_Street"] = build_ph_pbr_mat(
        "Mat_Cobble_Street",
        "cobblestone_floor_08_Diffuse_2k.jpg",
        "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg",
        tint=(0.56, 0.56, 0.58, 1.0), scale=0.45, rough_mult=0.90, normal_str=1.50
    )
    palette["Mat_Cobble_Courtyard"] = build_ph_pbr_mat(
        "Mat_Cobble_Courtyard",
        "cobblestone_floor_08_Diffuse_2k.jpg",
        "cobblestone_floor_08_Rough_2k.jpg",
        "cobblestone_floor_08_nor_gl_2k.jpg",
        tint=(0.68, 0.66, 0.64, 1.0), scale=0.40, rough_mult=0.90, normal_str=1.35
    )
    # 7. Asphalt Road & Jointed Concrete/Granite Sidewalk
    palette["Mat_Asphalt"] = build_ph_pbr_mat(
        "Mat_Asphalt",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint=(0.35, 0.36, 0.38, 1.0), scale=0.28, rough_mult=0.92, normal_str=1.25
    )
    palette["Mat_Sidewalk"] = build_ph_pbr_mat(
        "Mat_Sidewalk",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint=(0.68, 0.67, 0.65, 1.0), scale=0.35, rough_mult=0.88, normal_str=0.85,
        brick_grid=(0.65, 1.4, 1.4, (0.34, 0.34, 0.33, 1.0))
    )
    # 8. Slate Mansard & Bitumen/Gravel Flat Roofs
    palette["Mat_Roof_Slate"] = build_ph_pbr_mat(
        "Mat_Roof_Slate",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint=(0.22, 0.25, 0.29, 1.0), scale=0.40, rough_mult=0.65, normal_str=1.10,
        brick_grid=(2.2, 0.35, 0.55, (0.12, 0.14, 0.16, 1.0))
    )
    palette["Mat_Roof_Flat"] = build_ph_pbr_mat(
        "Mat_Roof_Flat",
        "asphalt_02_Diffuse_2k.jpg",
        "asphalt_02_Rough_2k.jpg",
        "asphalt_02_nor_gl_2k.jpg",
        tint=(0.32, 0.31, 0.29, 1.0), scale=0.32, rough_mult=0.95, normal_str=1.25
    )

    # Architectural Trim & Glazing Materials
    palette["Mat_Glass_Dark"] = create_solid_mat("Mat_Glass_Dark", (0.02, 0.04, 0.06, 1.0), roughness=0.04, metallic=0.15, ior=1.52)
    palette["Mat_Glass_Shutter"] = create_solid_mat("Mat_Glass_Shutter", (0.42, 0.39, 0.33, 1.0), roughness=0.06, metallic=0.08, ior=1.52)
    palette["Mat_Frame_White"] = create_solid_mat("Mat_Frame_White", (0.88, 0.88, 0.86, 1.0), roughness=0.32)
    palette["Mat_Frame_Dark"] = create_solid_mat("Mat_Frame_Dark", (0.07, 0.08, 0.09, 1.0), roughness=0.35, metallic=0.35)
    palette["Mat_Frame_Teal"] = create_solid_mat("Mat_Frame_Teal", (0.11, 0.22, 0.26, 1.0), roughness=0.32)
    palette["Mat_Frame_Green"] = create_solid_mat("Mat_Frame_Green", (0.015, 0.065, 0.025, 1.0), roughness=0.22)  # Deep glossy forest-green (#14361D)
    palette["Mat_Door_Burgundy"] = create_solid_mat("Mat_Door_Burgundy", (0.22, 0.03, 0.04, 1.0), roughness=0.28)
    palette["Mat_Cornice_Celadon"] = create_solid_mat("Mat_Cornice_Celadon", (0.28, 0.36, 0.31, 1.0), roughness=0.35, metallic=0.25)
    palette["Mat_Iron_Black"] = create_solid_mat("Mat_Iron_Black", (0.03, 0.03, 0.04, 1.0), roughness=0.30, metallic=0.85)
    palette["Mat_Sign_Blue"] = create_solid_mat("Mat_Sign_Blue", (0.14, 0.22, 0.34, 1.0), roughness=0.38)
    palette["Mat_Sign_Red"] = create_solid_mat("Mat_Sign_Red", (0.62, 0.08, 0.08, 1.0), roughness=0.35)
    palette["Mat_Lawn_Green"] = create_solid_mat("Mat_Lawn_Green", (0.14, 0.25, 0.09, 1.0), roughness=0.85)
    palette["Mat_Solar_Blue"] = create_solid_mat("Mat_Solar_Blue", (0.04, 0.10, 0.22, 1.0), roughness=0.15, metallic=0.60)
    return palette


def load_kit_assets():
    assets = {}
    if not os.path.exists(KIT_BLEND_PATH):
        return assets
    with bpy.data.libraries.load(KIT_BLEND_PATH, link=False) as (data_from, data_to):
        target_names = ["jacaranda_tree_LOD0", "street_lamp_01", "Master_Street_Bench"]
        data_to.objects = [n for n in target_names if n in data_from.objects]
    for obj in data_to.objects:
        if obj is not None:
            assets[obj.name] = obj
    return assets


# ---------------------------------------------------------------------------
# 2. GEOMETRY PRIMITIVES & HIGH-POLY ARCHITECTURAL HELPERS
# ---------------------------------------------------------------------------
def add_bevel(obj, width=0.02, segments=2):
    mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(35.0)


def create_box(name, center, size, rot_z, mat, col, bevel_w=0.015, cap_top=True, cap_bottom=True):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    if col.name.endswith("_Context_Proxy"):
        obj.hide_render = True
        obj.hide_viewport = True
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if not cap_top or not cap_bottom:
        faces_to_del = []
        for f in bm.faces:
            if not cap_top and f.normal.z > 0.8:
                faces_to_del.append(f)
            elif not cap_bottom and f.normal.z < -0.8:
                faces_to_del.append(f)
        if faces_to_del:
            bmesh.ops.delete(bm, geom=faces_to_del, context='FACES_ONLY')
    if abs(rot_z) > 1e-5:
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler((0.0, 0.0, rot_z), 'XYZ').to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        obj.data.materials.append(mat)
    if bevel_w > 0:
        add_bevel(obj, bevel_w)
    return obj


def create_cylinder(name, center, radius, depth, rot_euler, mat, col, segments=16):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    if col.name.endswith("_Context_Proxy"):
        obj.hide_render = True
        obj.hide_viewport = True
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=radius, radius2=radius, depth=depth)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler(rot_euler, 'XYZ').to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        obj.data.materials.append(mat)
    return obj


def create_extruded_polygon(name, pts_2d, z_min, z_max, mat, col, bevel_w=0.02, cap_top=True, cap_bottom=True):
    pts = list(pts_2d)
    if len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05:
        pts = pts[:-1]
    if len(pts) < 3:
        return None
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    if col.name.endswith("_Context_Proxy"):
        obj.hide_render = True
        obj.hide_viewport = True
    bm = bmesh.new()
    b_verts = [bm.verts.new((p[0], p[1], z_min)) for p in pts]
    face = bm.faces.new(b_verts)
    face.normal_update()
    if face.normal.z > 0:
        bmesh.ops.reverse_faces(bm, faces=[face])
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts_top = [v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0.0, 0.0, z_max - z_min), verts=verts_top)

    faces_to_delete = []
    if not cap_bottom or not cap_top:
        for f in bm.faces:
            avg_z = sum(v.co.z for v in f.verts) / len(f.verts)
            if not cap_bottom and avg_z <= z_min + 1e-3:
                faces_to_delete.append(f)
            elif not cap_top and avg_z >= z_max - 1e-3:
                faces_to_delete.append(f)
    if faces_to_delete:
        bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES_ONLY')

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        obj.data.materials.append(mat)
    if bevel_w > 0:
        add_bevel(obj, bevel_w)
    return obj


def compute_outward_normal(p1, p2, poly_pts):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-4:
        return (0.0, 1.0), 0.0
    nx, ny = dy / length, -dx / length
    area2 = 0.0
    n = len(poly_pts)
    for i in range(n):
        x1, y1 = poly_pts[i]
        x2, y2 = poly_pts[(i + 1) % n]
        area2 += (x1 * y2 - x2 * y1)
    if area2 < 0:
        nx, ny = -nx, -ny
    return (nx, ny), length


def add_window_bay(prefix, wx, wy, wz, w, h, rot_z, nx, ny, mat_stone, mat_frame, mat_glass, mat_iron, col,
                   arched=False, panes_x=2, balcony=False, scroll_medallions=False):
    """Creates a deeply recessed (0.42m) architectural window bay with sill, lintel/archivolt, mullions, and optional iron balcony."""
    ux, uy = math.cos(rot_z), math.sin(rot_z)
    create_box(f"{prefix}_RevealTop", (wx + nx * 0.15, wy + ny * 0.15, wz + h * 0.5 + 0.09), (w + 0.26, 0.34, 0.18), rot_z, mat_stone, col, cap_top=False, cap_bottom=False)
    create_box(f"{prefix}_Sill", (wx + nx * 0.19, wy + ny * 0.19, wz - h * 0.5 - 0.08), (w + 0.32, 0.40, 0.16), rot_z, mat_stone, col)
    for s_side in (-1.0, 1.0):
        jx = wx + s_side * (w * 0.5 + 0.07) * ux + nx * 0.12
        jy = wy + s_side * (w * 0.5 + 0.07) * uy + ny * 0.12
        create_box(f"{prefix}_Jamb_{int(s_side)}", (jx, jy, wz), (0.16, 0.28, h), rot_z, mat_stone, col)

    # Glass pane outside wall surface (at nx * 0.05) + deep frame/mullions (at nx * 0.09)
    create_box(f"{prefix}_Glass", (wx + nx * 0.05, wy + ny * 0.05, wz), (w, 0.06, h), rot_z, mat_glass, col, bevel_w=0.0)

    for m_i in range(panes_x + 1):
        frac = -0.5 + m_i / float(panes_x)
        mx = wx + frac * (w - 0.08) * ux + nx * 0.09
        my = wy + frac * (w - 0.08) * uy + ny * 0.09
        create_box(f"{prefix}_Mullion_{m_i}", (mx, my, wz), (0.065, 0.09, h), rot_z, mat_frame, col, bevel_w=0.005)
    for t_frac in (-0.48, 0.0, 0.24, 0.48):
        create_box(f"{prefix}_Transom_{int(t_frac*100)}", (wx + nx * 0.09, wy + ny * 0.09, wz + t_frac * h), (w, 0.09, 0.06), rot_z, mat_frame, col, bevel_w=0.005)

    if arched:
        # Sub-arches above each pane (Venetian / coupled arch heads) + central stone keystone
        for p_i in range(panes_x):
            pf = -0.5 + (p_i + 0.5) / float(panes_x)
            ax = wx + pf * (w - 0.10) * ux + nx * 0.10
            ay = wy + pf * (w - 0.10) * uy + ny * 0.10
            pw = (w - 0.12) / float(panes_x)
            create_cylinder(f"{prefix}_ArchHead_{p_i}", (ax, ay, wz + h * 0.34), pw * 0.46, 0.08, (math.pi * 0.5, 0.0, rot_z), mat_frame, col, segments=14)
        create_box(f"{prefix}_Keystone", (wx + nx * 0.21, wy + ny * 0.21, wz + h * 0.5 + 0.15), (0.28, 0.38, 0.32), rot_z, mat_stone, col)

    if balcony and mat_iron:
        rail_z = wz - h * 0.5 + 0.44
        bw = w * 0.85 if scroll_medallions else (w + 0.06)
        create_box(f"{prefix}_BalcTop", (wx + nx * 0.25, wy + ny * 0.25, rail_z + 0.40), (bw, 0.05, 0.04), rot_z, mat_iron, col, bevel_w=0.0)
        create_box(f"{prefix}_BalcBot", (wx + nx * 0.25, wy + ny * 0.25, rail_z - 0.36), (bw, 0.05, 0.04), rot_z, mat_iron, col, bevel_w=0.0)
        n_bars = max(5, int(bw / 0.20))
        for b_i in range(n_bars):
            bf = -0.48 + 0.96 * (b_i / float(max(1, n_bars - 1)))
            bx = wx + bf * bw * ux + nx * 0.25
            by = wy + bf * bw * uy + ny * 0.25
            create_box(f"{prefix}_BalcBar_{b_i}", (bx, by, rail_z), (0.025, 0.025, 0.76), rot_z, mat_iron, col, bevel_w=0.0)
        if scroll_medallions:
            for m_off in (-0.24, 0.24):
                mx_c = wx + m_off * bw * ux + nx * 0.26
                my_c = wy + m_off * bw * uy + ny * 0.26
                create_cylinder(f"{prefix}_Medallion_{int(m_off*100)}", (mx_c, my_c, rail_z), 0.20, 0.03, (math.pi * 0.5, 0.0, rot_z), mat_iron, col, segments=14)


# ---------------------------------------------------------------------------
# 3. BESPOKE HERO FACADES FOR THE 4 STREET VIEW CAMERAS
# ---------------------------------------------------------------------------
def build_hero_facades(dossier, palette, col):
    mat_grey = palette["Mat_Stone_Grey"]
    mat_buff = palette["Mat_Stone_Buff"]
    mat_rubble = palette["Mat_Stone_Rubble"]
    mat_quoin = palette["Mat_Stone_Quoin"]
    mat_brick = palette["Mat_Red_Brick"]
    mat_white = palette["Mat_Frame_White"]
    mat_dark = palette["Mat_Frame_Dark"]
    mat_teal = palette["Mat_Frame_Teal"]
    mat_green = palette["Mat_Frame_Green"]
    mat_burg = palette["Mat_Door_Burgundy"]
    mat_celadon = palette["Mat_Cornice_Celadon"]
    mat_glass = palette["Mat_Glass_Dark"]
    mat_shutter = palette["Mat_Glass_Shutter"]
    mat_iron = palette["Mat_Iron_Black"]
    mat_blue = palette["Mat_Sign_Blue"]
    mat_red = palette["Mat_Sign_Red"]

    # --- HERO 1: `Rue_SaintSulpice_Facade.jpg` (339877245 & 339877244 East Facades) ---
    pA1, pA2 = (149.686, -75.864), (151.371, -70.176)
    pB1, pB2 = (151.371, -70.176), (153.634, -62.283)
    for seg_i, (s1, s2, is_door_seg) in enumerate([(pA1, pA2, True), (pB1, pB2, False)]):
        dx, dy = s2[0] - s1[0], s2[1] - s1[1]
        slen = math.hypot(dx, dy)
        rot_s = math.atan2(dy, dx)
        nx, ny = dy / slen, -dx / slen
        ux, uy = dx / slen, dy / slen

        mx, my = (s1[0] + s2[0]) * 0.5, (s1[1] + s2[1]) * 0.5
        # Coursed grey ashlar facade overlay so mortar joints are 100% sharp
        create_box(f"H1_245_AshlarWall_{seg_i}", (mx + nx * 0.04, my + ny * 0.04, 7.8), (slen + 0.15, 0.12, 15.6), rot_s, mat_grey, col)
        create_box(f"H1_245_Band_{seg_i}", (mx + nx * 0.16, my + ny * 0.16, 4.15), (slen + 0.2, 0.32, 0.28), rot_s, mat_quoin, col)

        if is_door_seg:
            qx, qy = s1[0] + 0.62 * dx, s1[1] + 0.62 * dy
            create_box("H1_245_BurgDoor_Surround", (qx + nx * 0.16, qy + ny * 0.16, 2.15), (2.30, 0.34, 4.1), rot_s, mat_quoin, col)
            create_box("H1_245_BurgDoor_Panel", (qx + nx * 0.07, qy + ny * 0.07, 1.75), (1.82, 0.10, 2.95), rot_s, mat_burg, col)
            create_box("H1_245_BurgDoor_Fanlight", (qx + nx * 0.08, qy + ny * 0.08, 3.55), (1.82, 0.10, 0.65), rot_s, mat_glass, col)
            create_box("H1_245_BurgDoor_Mullion", (qx + nx * 0.11, qy + ny * 0.11, 1.75), (0.09, 0.12, 2.95), rot_s, mat_burg, col)
            for d_side in (-0.45, 0.45):
                create_box(f"H1_245_DoorGlass_{int(d_side*100)}", (qx + d_side * ux + nx * 0.10, qy + d_side * uy + ny * 0.10, 2.10), (0.55, 0.08, 1.55), rot_s, mat_glass, col)
            for st_i in range(3):
                create_box(f"H1_245_Step_{st_i}", (qx + nx * (0.28 + st_i * 0.22), qy + ny * (0.28 + st_i * 0.22), 0.12 * (3 - st_i)), (2.15, 0.28, 0.24 * (3 - st_i)), rot_s, mat_grey, col)
            # Hanging Blue Heritage Sign on Wrought-Iron Bracket + Wall Lantern + Brass Plaque
            sx, sy = qx + 1.15 * ux + nx * 0.55, qy + 1.15 * uy + ny * 0.55
            create_box("H1_245_BlueSign_Bracket", (sx, sy, 3.65), (0.06, 0.90, 0.06), rot_s, mat_iron, col)
            create_box("H1_245_BlueSign_Board", (sx, sy, 3.10), (0.06, 0.72, 0.88), rot_s, mat_blue, col)
            create_box("H1_245_MenuBox", (qx + 1.15 * ux + nx * 0.18, qy + 1.15 * uy + ny * 0.18, 1.45), (0.52, 0.12, 0.68), rot_s, mat_quoin, col)
            create_cylinder("H1_245_WallLantern", (qx + 1.05 * ux + nx * 0.35, qy + 1.05 * uy + ny * 0.35, 2.55), 0.16, 0.38, (0, 0, 0), mat_iron, col, segments=8)
            for fl_i, fz in enumerate([6.1, 9.5, 12.8]):
                add_window_bay(f"H1_245_SegA_Win_{fl_i}", qx, qy, fz, 1.65, 2.35, rot_s, nx, ny, mat_quoin, mat_white, mat_glass, mat_iron, col, arched=True, panes_x=2, balcony=True)
        else:
            for col_i, t_pos in enumerate([0.28, 0.74]):
                wx, wy = s1[0] + t_pos * dx, s1[1] + t_pos * dy
                # Recessed basement window well + stone pier divider + round brass pipe vents
                create_box(f"H1_245_BaseWin_{col_i}", (wx + nx * 0.06, wy + ny * 0.06, 0.45), (2.15, 0.08, 0.62), rot_s, mat_shutter, col)
                create_box(f"H1_245_BaseSill_{col_i}", (wx + nx * 0.22, wy + ny * 0.22, 0.85), (2.45, 0.40, 0.16), rot_s, mat_quoin, col)
                # Triple-arched Venetian ground window with warm shutter backing
                add_window_bay(f"H1_245_GndWin_{col_i}", wx, wy, 2.30, 2.25, 2.65, rot_s, nx, ny, mat_quoin, mat_white, mat_shutter, mat_iron, col, arched=True, panes_x=3, balcony=True)
                # Cast-iron oval tie-rod anchor plates at z = 4.15m & z = 7.8m
                for tz in (4.15, 7.80):
                    create_cylinder(f"H1_245_TieRod_{col_i}_{int(tz)}", (wx - 1.25 * ux + nx * 0.22, wy - 1.25 * uy + ny * 0.22, tz), 0.15, 0.06, (math.pi * 0.5, 0.0, rot_s), mat_iron, col, segments=12)
                for fl_i, fz in enumerate([6.1, 9.5, 12.8]):
                    add_window_bay(f"H1_245_SegB_Win_{col_i}_{fl_i}", wx, wy, fz, 1.55, 2.35, rot_s, nx, ny, mat_quoin, mat_white, mat_glass, mat_iron, col, arched=True, panes_x=2, balcony=True)

            create_cylinder("H1_245_Downspout", (s1[0] + 0.04 * dx + nx * 0.20, s1[1] + 0.04 * dy + ny * 0.20, 7.8), 0.055, 15.4, (0, 0, 0), mat_grey, col, segments=10)

    # 339877244 East Facade: (153.634, -62.283) -> (156.583, -53.411)
    pC1, pC2 = (153.634, -62.283), (156.583, -53.411)
    dxC, dyC = pC2[0] - pC1[0], pC2[1] - pC1[1]
    lenC = math.hypot(dxC, dyC)
    rotC = math.atan2(dyC, dxC)
    nxC, nyC = dyC / lenC, -dxC / lenC
    mxC, myC = (pC1[0] + pC2[0]) * 0.5, (pC1[1] + pC2[1]) * 0.5
    create_box("H1_244_AshlarWall", (mxC + nxC * 0.04, myC + nyC * 0.04, 7.8), (lenC + 0.15, 0.12, 15.6), rotC, mat_grey, col)
    create_box("H1_244_GndCornice", (mxC + nxC * 0.24, myC + nyC * 0.24, 3.85), (lenC + 0.2, 0.45, 0.36), rotC, mat_quoin, col, cap_top=False, cap_bottom=False)
    for col_i, t_pos in enumerate([0.24, 0.68]):
        wx, wy = pC1[0] + t_pos * dxC, pC1[1] + t_pos * dyC
        add_window_bay(f"H1_244_GndStore_{col_i}", wx, wy, 2.15, 2.55, 2.75, rotC, nxC, nyC, mat_quoin, mat_dark, mat_glass, None, col, panes_x=2)
        for fl_i, fz in enumerate([5.9, 9.4, 12.8]):
            add_window_bay(f"H1_244_TealWin_{col_i}_{fl_i}", wx, wy, fz, 1.85, 2.40, rotC, nxC, nyC, mat_quoin, mat_teal, mat_glass, None, col, arched=True, panes_x=2)
    create_cylinder("H1_ParkingPost", (153.95, -62.25, 1.35), 0.035, 2.7, (0, 0, 0), mat_iron, col, segments=8)
    create_box("H1_ParkingSign_1", (153.95, -62.25, 2.25), (0.03, 0.34, 0.65), rotC, mat_white, col, bevel_w=0.0)
    create_box("H1_ParkingSign_2", (153.92, -62.38, 1.85), (0.03, 0.28, 0.32), rotC, mat_red, col, bevel_w=0.0)

    # --- HERO 2: `Cours_Le_Royer_Courtyard.jpg` (339877593 Le Sulpice Hotel East Wing) ---
    pS1, pS2 = (145.005, -90.803), (149.686, -75.864)
    dxS, dyS = pS2[0] - pS1[0], pS2[1] - pS1[1]
    lenS = math.hypot(dxS, dyS)
    rotS = math.atan2(dyS, dxS)
    nxS, nyS = dyS / lenS, -dxS / lenS
    mxS, myS = (pS1[0] + pS2[0]) * 0.5, (pS1[1] + pS2[1]) * 0.5

    # Continuous coursed ashlar backing wall eliminating any corner geometry seam
    create_box("H2_Sulpice_BackingWall", (mxS + nxS * 0.05, myS + nyS * 0.05, 9.0), (lenS + 0.4, 0.14, 18.0), rotS, mat_grey, col)
    # Heavy projecting stone entablature above 2nd floor (z = 7.35m, 0.62m projection) & 4 wide dressed ashlar pilasters
    create_box("H2_Sulpice_MainCornice", (mxS + nxS * 0.34, myS + nyS * 0.34, 7.35), (lenS + 0.5, 0.68, 0.52), rotS, mat_quoin, col)
    create_box("H2_Sulpice_GndBand", (mxS + nxS * 0.18, myS + nyS * 0.18, 3.65), (lenS + 0.3, 0.34, 0.32), rotS, mat_quoin, col)
    for p_frac in [0.02, 0.34, 0.66, 0.98]:
        px, py = pS1[0] + p_frac * dxS, pS1[1] + p_frac * dyS
        create_box(f"H2_Sulpice_Pilaster_{int(p_frac*100)}", (px + nxS * 0.16, py + nyS * 0.16, 9.0), (0.88, 0.32, 18.0), rotS, mat_quoin, col)

    for bay_i, t_pos in enumerate([0.18, 0.50, 0.82]):
        bx, by = pS1[0] + t_pos * dxS, pS1[1] + t_pos * dyS
        add_window_bay(f"H2_Sulpice_GndWin_{bay_i}", bx, by, 1.85, 3.80, 3.05, rotS, nxS, nyS, mat_quoin, mat_white, mat_glass, None, col, panes_x=4, balcony=False)
        add_window_bay(f"H2_Sulpice_Fl2Win_{bay_i}", bx, by, 5.45, 3.70, 2.55, rotS, nxS, nyS, mat_quoin, mat_white, mat_glass, mat_iron, col, panes_x=4, balcony=True, scroll_medallions=True)
        for fl_i, fz in enumerate([9.2, 12.5, 15.8]):
            add_window_bay(f"H2_Sulpice_UpWin_{bay_i}_{fl_i}", bx, by, fz, 3.60, 2.35, rotS, nxS, nyS, mat_quoin, mat_white, mat_glass, mat_iron, col, panes_x=4, balcony=True, scroll_medallions=True)

    # Flush cast-iron manhole cover in sidewalk + storm drain grate at curb + parking sign + VALET A-frame
    create_cylinder("H2_ManholeCover", (148.55, -84.85, 0.175), 0.36, 0.015, (0, 0, 0), mat_iron, col, segments=20)
    create_box("H2_StormGrate", (149.15, -85.15, 0.16), (0.65, 0.42, 0.04), rotS, mat_iron, col)
    create_cylinder("H2_SignPost", (147.85, -83.55, 1.35), 0.035, 2.7, (0, 0, 0), mat_iron, col, segments=8)
    create_box("H2_SignBoard", (147.85, -83.55, 2.25), (0.03, 0.32, 0.55), rotS, mat_white, col, bevel_w=0.0)
    create_box("H2_Valet_AFrame", (151.45, -85.85, 0.52), (0.45, 0.45, 0.90), rotS + 0.3, mat_iron, col)

    # --- HERO 3: `Corner_Rue_SaintPaul.jpg` (339876531 Tommy Café & 339876874 Red-Brick/Stone Corner) ---
    pT1, pT2 = (128.8, -141.565), (132.405, -133.706)
    dxT, dyT = pT2[0] - pT1[0], pT2[1] - pT1[1]
    lenT = math.hypot(dxT, dyT)
    rotT = math.atan2(dyT, dxT)
    nxT, nyT = dyT / lenT, -dxT / lenT
    uxT, uyT = dxT / lenT, dyT / lenT
    mxT, myT = (pT1[0] + pT2[0]) * 0.5, (pT1[1] + pT2[1]) * 0.5

    create_box("H3_Tommy_WallOverlay", (mxT + nxT * 0.04, myT + nyT * 0.04, 6.25), (lenT + 0.2, 0.12, 12.5), rotT, mat_buff, col)
    create_box("H3_Tommy_GndCornice", (mxT + nxT * 0.22, myT + nyT * 0.22, 3.95), (lenT + 0.3, 0.40, 0.34), rotT, mat_buff, col, cap_top=False, cap_bottom=False)
    create_box("H3_Tommy_String1", (mxT + nxT * 0.14, myT + nyT * 0.14, 4.45), (lenT + 0.2, 0.26, 0.16), rotT, mat_buff, col, cap_top=False, cap_bottom=False)
    create_box("H3_Tommy_String2", (mxT + nxT * 0.14, myT + nyT * 0.14, 7.95), (lenT + 0.2, 0.26, 0.16), rotT, mat_buff, col, cap_top=False, cap_bottom=False)
    create_box("H3_Tommy_RoofCornice", (mxT + nxT * 0.32, myT + nyT * 0.32, 12.25), (lenT + 0.5, 0.58, 0.48), rotT, mat_celadon, col, cap_top=False, cap_bottom=False)

    for p_frac in [0.03, 0.38, 0.62, 0.97]:
        px, py = pT1[0] + p_frac * dxT, pT1[1] + p_frac * dyT
        create_box(f"H3_Tommy_Pilaster_{int(p_frac*100)}", (px + nxT * 0.16, py + nyT * 0.16, 2.0), (0.58, 0.30, 3.9), rotT, mat_buff, col)

    # Menu plaque (`151`) on pier left of entrance door
    px_m, py_m = pT1[0] + 0.38 * dxT, pT1[1] + 0.38 * dyT
    create_box("H3_Tommy_MenuBoard", (px_m + nxT * 0.32, py_m + nyT * 0.32, 1.50), (0.48, 0.08, 0.65), rotT, mat_white, col)

    for b_i, (t_pos, is_door) in enumerate([(0.20, False), (0.50, True), (0.80, False)]):
        wx, wy = pT1[0] + t_pos * dxT, pT1[1] + t_pos * dyT
        # Gooseneck café lamp above each bay
        create_box(f"H3_Tommy_GooseneckArm_{b_i}", (wx + nxT * 0.42, wy + nyT * 0.42, 3.72), (0.05, 0.55, 0.05), rotT, mat_iron, col)
        create_cylinder(f"H3_Tommy_GooseneckShade_{b_i}", (wx + nxT * 0.65, wy + nyT * 0.65, 3.62), 0.16, 0.14, (0, 0, 0), mat_iron, col, segments=12)

        if is_door:
            # Deeply recessed double-door entrance vestibule with forest-green wood stiles, kickpanels, and 2-pane glass transom
            create_box("H3_Tommy_DoorVestibule_Back", (wx + nxT * 0.02, wy + nyT * 0.02, 1.95), (1.65, 0.08, 3.50), rotT, mat_glass, col)
            for d_side in (-0.38, 0.38):
                dx_leaf = wx + d_side * uxT + nxT * 0.06
                dy_leaf = wy + d_side * uyT + nyT * 0.06
                create_box(f"H3_Tommy_DoorKick_{int(d_side*100)}", (dx_leaf, dy_leaf, 0.65), (0.72, 0.08, 0.75), rotT, mat_green, col)
                create_box(f"H3_Tommy_DoorTopRail_{int(d_side*100)}", (dx_leaf, dy_leaf, 2.45), (0.72, 0.08, 0.12), rotT, mat_green, col)
            for s_off in (-0.75, -0.04, 0.04, 0.75):
                create_box(f"H3_Tommy_DoorStile_{int(s_off*100)}", (wx + s_off * uxT + nxT * 0.07, wy + s_off * uyT + nyT * 0.07, 1.40), (0.08, 0.10, 2.30), rotT, mat_green, col)
            create_box("H3_Tommy_DoorTransomBar", (wx + nxT * 0.08, wy + nyT * 0.08, 2.60), (1.65, 0.12, 0.12), rotT, mat_green, col)
            create_box("H3_Tommy_Step1", (wx + nxT * 0.20, wy + nyT * 0.20, 0.12), (1.68, 0.32, 0.22), rotT, mat_grey, col)
            create_box("H3_Tommy_Step2", (wx + nxT * 0.12, wy + nyT * 0.12, 0.24), (1.68, 0.22, 0.22), rotT, mat_grey, col)
        else:
            add_window_bay(f"H3_Tommy_StoreWin_{b_i}", wx, wy, 2.20, 2.45, 2.45, rotT, nxT, nyT, mat_buff, mat_green, mat_glass, None, col, panes_x=3)
            create_box(f"H3_Tommy_BaseGrille_{b_i}", (wx + nxT * 0.10, wy + nyT * 0.10, 0.42), (1.85, 0.12, 0.38), rotT, mat_green, col)

        for fl_i, fz in enumerate([5.85, 9.35]):
            add_window_bay(f"H3_Tommy_UpWin_{b_i}_{fl_i}", wx, wy, fz, 1.35, 2.15, rotT, nxT, nyT, mat_buff, mat_dark, mat_glass, None, col, panes_x=2)

    create_box("H3_StreetSign_Red", (132.45 + nxT * 0.28, -133.65 + nyT * 0.28, 3.75), (0.08, 0.68, 0.22), rotT, mat_red, col)
    create_cylinder("H3_Tommy_Downspout", (132.35 + nxT * 0.20, -133.75 + nyT * 0.20, 6.2), 0.05, 12.2, (0, 0, 0), mat_grey, col, segments=8)

    # --- HERO 4: `Corner_Rue_DeBresoles.jpg` (339877652 Victorian Mansard + Rubble Party Wall & 339877593 Red-Brick Wing) ---
    pD1, pD2 = (120.811, -30.401), (112.393, -27.14)
    dxD, dyD = pD2[0] - pD1[0], pD2[1] - pD1[1]
    lenD = math.hypot(dxD, dyD)
    rotD = math.atan2(dyD, dxD)
    nxD, nyD = dyD / lenD, -dxD / lenD
    mxD, myD = (pD1[0] + pD2[0]) * 0.5, (pD1[1] + pD2[1]) * 0.5

    for cz, cw in [(4.1, 0.44), (7.6, 0.30), (11.0, 0.30), (14.5, 0.52)]:
        create_box(f"H4_652_Cornice_{int(cz*10)}", (mxD + nxD * (cw * 0.5), myD + nyD * (cw * 0.5), cz), (lenD + 0.3, cw, 0.34), rotD, mat_quoin, col)

    for q_i in range(26):
        qz = 0.45 + q_i * 0.54
        qw = 0.70 if q_i % 2 == 0 else 0.46
        create_box(f"H4_652_CornerQuoin_{q_i}", (112.393, -27.14, qz), (qw, qw, 0.48), rotD, mat_quoin, col)

    for col_i, t_pos in enumerate([0.20, 0.50, 0.80]):
        wx, wy = pD1[0] + t_pos * dxD, pD1[1] + t_pos * dyD
        add_window_bay(f"H4_652_Gnd_{col_i}", wx, wy, 2.25, 1.85, 2.85, rotD, nxD, nyD, mat_quoin, mat_dark, mat_glass, None, col, arched=True, panes_x=2)
        for fl_i, fz in enumerate([5.85, 9.30, 12.75]):
            add_window_bay(f"H4_652_Up_{col_i}_{fl_i}", wx, wy, fz, 1.55, 2.35, rotD, nxD, nyD, mat_quoin, mat_dark, mat_glass, mat_iron, col, arched=True, panes_x=2, balcony=(fl_i > 0))
        # Projecting Mansard Dormer Window at z = 16.0m with dark slate cheeks & pediment cap
        create_box(f"H4_652_DormerBody_{col_i}", (wx - nxD * 0.12, wy - nyD * 0.12, 16.05), (1.50, 1.15, 2.15), rotD, palette["Mat_Roof_Slate"], col)
        create_box(f"H4_652_DormerCap_{col_i}", (wx + nxD * 0.05, wy + nyD * 0.05, 17.20), (1.65, 1.25, 0.28), rotD, mat_quoin, col)
        add_window_bay(f"H4_652_DormerWin_{col_i}", wx + nxD * 0.10, wy + nyD * 0.10, 15.95, 1.18, 1.65, rotD, nxD, nyD, mat_quoin, mat_dark, mat_glass, None, col, panes_x=2)

    # NW Rubble Fieldstone Party Wall (`moellons`) on 339877652: (112.393, -27.14) -> (100.87, -46.398)
    pG1, pG2 = (112.393, -27.14), (100.87, -46.398)
    dxG, dyG = pG2[0] - pG1[0], pG2[1] - pG1[1]
    lenG = math.hypot(dxG, dyG)
    rotG = math.atan2(dyG, dxG)
    nxG, nyG = dyG / lenG, -dxG / lenG
    mxG, myG = (pG1[0] + pG2[0]) * 0.5, (pG1[1] + pG2[1]) * 0.5
    create_box("H4_652_RubbleGableWall", (mxG + nxG * 0.08, myG + nyG * 0.08, 7.25), (lenG, 0.22, 14.5), rotG, mat_rubble, col)
    create_box("H4_652_BrickUpperGable", (mxG + nxG * 0.06, myG + nyG * 0.06, 16.3), (lenG * 0.74, 0.28, 3.6), rotG, mat_brick, col)
    create_box("H4_652_BrickChimney", (pG1[0] + 0.38 * dxG + nxG * 0.06, pG1[1] + 0.38 * dyG + nyG * 0.06, 18.8), (2.4, 0.85, 2.8), rotG, mat_brick, col)
    # Recessed blind window niche in middle of rubble wall (t = 0.58, z = 6.2m) + street-level metal service door (t = 0.72, z = 1.15m)
    bx_n, by_n = pG1[0] + 0.58 * dxG, pG1[1] + 0.58 * dyG
    create_box("H4_652_BlindWinSill", (bx_n + nxG * 0.22, by_n + nyG * 0.22, 4.95), (1.55, 0.24, 0.16), rotG, mat_quoin, col)
    create_box("H4_652_BlindWinLintel", (bx_n + nxG * 0.22, by_n + nyG * 0.22, 7.45), (1.55, 0.24, 0.18), rotG, mat_quoin, col)
    create_box("H4_652_BlindWinRecess", (bx_n + nxG * 0.16, by_n + nyG * 0.16, 6.20), (1.35, 0.10, 2.35), rotG, mat_grey, col)
    dx_srv, dy_srv = pG1[0] + 0.72 * dxG, pG1[1] + 0.72 * dyG
    create_box("H4_652_ServiceDoorFrame", (dx_srv + nxG * 0.20, dy_srv + nyG * 0.20, 1.15), (1.28, 0.18, 2.30), rotG, mat_quoin, col)
    create_box("H4_652_ServiceDoorLeaf", (dx_srv + nxG * 0.16, dy_srv + nyG * 0.16, 1.10), (1.08, 0.12, 2.15), rotG, mat_dark, col)

    # Adjacent 4/5-Storey Heritage Red-Brick Wing (339877593 NW Wing: (102.68, -48.691) -> (92.093, -63.04))
    # Placed flush at nxR * (-0.06) so the recessed 6-over-6 windows at nxR * (+0.05..+0.19) sit cleanly outside the brick wall!
    pR1, pR2 = (102.68, -48.691), (92.093, -63.04)
    dxR, dyR = pR2[0] - pR1[0], pR2[1] - pR1[1]
    lenR = math.hypot(dxR, dyR)
    rotR = math.atan2(dyR, dxR)
    nxR, nyR = dyR / lenR, -dxR / lenR
    mxR, myR = (pR1[0] + pR2[0]) * 0.5, (pR1[1] + pR2[1]) * 0.5
    create_box("H4_593_RedBrickWall", (mxR - nxR * 0.06, myR - nyR * 0.06, 8.4), (lenR, 0.22, 16.8), rotR, mat_brick, col)
    for col_i, t_pos in enumerate([0.16, 0.38, 0.62, 0.84]):
        wx, wy = pR1[0] + t_pos * dxR, pR1[1] + t_pos * dyR
        for fl_i, fz in enumerate([2.2, 5.4, 8.6, 11.8, 14.9]):
            add_window_bay(f"H4_593_BrickWin_{col_i}_{fl_i}", wx, wy, fz, 1.38, 2.10, rotR, nxR, nyR, mat_quoin, mat_dark, mat_glass, None, col, panes_x=2)

    # Low Curved Stone Planter Wall, Lawn & Street Sign in Foreground Right of `Corner_Rue_DeBresoles.jpg`
    create_box("H4_GardenWall_Low", (102.5, -26.8, 0.55), (14.5, 0.55, 1.10), rotG, mat_rubble, col)
    create_box("H4_GardenWall_Cap", (102.5, -26.8, 1.18), (14.7, 0.68, 0.22), rotG, mat_quoin, col)
    create_box("H4_GardenLawn_Patch", (96.5, -31.5, 0.28), (14.0, 12.0, 0.50), rotG, palette["Mat_Lawn_Green"], col, bevel_w=0.0)
    create_cylinder("H4_DeBresoles_SignPost", (109.1, -24.8, 1.45), 0.038, 2.9, (0, 0, 0), mat_iron, col, segments=8)
    create_box("H4_DeBresoles_RedSign", (109.1, -24.8, 2.65), (0.04, 0.68, 0.22), rotD, mat_red, col, bevel_w=0.0)
    create_box("H4_DeBresoles_OneWay", (109.1, -24.8, 2.38), (0.04, 0.55, 0.20), rotD, mat_white, col, bevel_w=0.0)

    # Black Hotel Flags/Banners along Rue Saint-Sulpice on 339877243
    pF1, pF2 = (135.83, -36.479), (120.811, -30.401)
    for f_i, f_t in enumerate([0.25, 0.50, 0.75]):
        fx, fy = pF1[0] + f_t * (pF2[0] - pF1[0]), pF1[1] + f_t * (pF2[1] - pF1[1])
        create_box(f"H4_HotelBanner_{f_i}", (fx + nxD * 0.85, fy + nyD * 0.85, 5.2), (0.06, 1.25, 1.65), rotD, mat_iron, col)


# ---------------------------------------------------------------------------
# 4. PROCEDURAL HISTORIC BUILDING GENERATOR FOR ALL BLOCK BUILDINGS
# ---------------------------------------------------------------------------
def build_all_buildings(dossier, palette, owned_col, context_col):
    mat_grey = palette["Mat_Stone_Grey"]
    mat_buff = palette["Mat_Stone_Buff"]
    mat_rubble = palette["Mat_Stone_Rubble"]
    mat_quoin = palette["Mat_Stone_Quoin"]
    mat_brick = palette["Mat_Red_Brick"]
    mat_slate = palette["Mat_Roof_Slate"]
    mat_flat = palette["Mat_Roof_Flat"]
    mat_white = palette["Mat_Frame_White"]
    mat_dark = palette["Mat_Frame_Dark"]
    mat_green = palette["Mat_Frame_Green"]
    mat_glass = palette["Mat_Glass_Dark"]
    mat_iron = palette["Mat_Iron_Black"]
    mat_solar = palette["Mat_Solar_Blue"]

    buildings = list(dossier.get("osm_features", {}).get("buildings", []))
    buildings.append({
        "id": 161202161,
        "name": "Rue Saint-Sulpice East Canyon Context",
        "tags": {"building": "yes", "building:levels": "5"},
        "coords_xy": [[191.691, 50.795], [159.126, -35.166], [122.59, -20.705], [123.105, -19.381], [156.232, 64.565], [191.691, 50.795]],
        "is_primary_owner": False
    })

    bldg_specs = {
        339876531: (3, 12.5, mat_buff, mat_green, "flat"),        # Tommy Café
        339876874: (3, 12.2, mat_buff, mat_green, "pitched"),     # Corner building across narrow lane
        339876530: (4, 15.2, mat_grey, mat_dark, "pitched"),
        339876875: (4, 15.6, mat_grey, mat_white, "pitched"),
        339876876: (5, 18.2, mat_grey, mat_white, "flat"),
        339877243: (4, 15.8, mat_grey, mat_white, "mansard"),
        339877244: (4, 15.6, mat_grey, mat_dark, "flat"),
        339877245: (4, 15.5, mat_grey, mat_white, "flat"),
        339877593: (5, 18.0, mat_grey, mat_white, "flat"),
        339877652: (4, 14.6, mat_buff, mat_dark, "mansard"),
        339878563: (4, 15.8, mat_grey, mat_white, "pitched"),
        339878564: (4, 15.8, mat_grey, mat_white, "pitched"),
        339878565: (4, 15.6, mat_grey, mat_white, "pitched"),
        339878566: (4, 15.4, mat_grey, mat_white, "pitched"),
        339878567: (4, 14.8, mat_buff, mat_dark, "flat"),
        339878568: (4, 15.0, mat_grey, mat_white, "pitched"),
        339879303: (4, 15.6, mat_buff, mat_dark, "mansard"),
        87411690:  (3, 13.5, mat_buff, mat_white, "pitched"),
        161202161: (5, 18.5, mat_grey, mat_dark, "flat"),
    }

    for bldg in buildings:
        bid = bldg["id"]
        is_owned = bldg.get("is_primary_owner", False)
        target_col = owned_col if is_owned else context_col
        pts = bldg.get("coords_xy", [])
        if len(pts) < 4:
            continue
        clean_pts = pts[:-1] if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05 else pts

        lvls_tag = int(bldg.get("tags", {}).get("building:levels", 4))
        if bid in bldg_specs:
            lvls, h_wall, mat_wall, mat_frm, roof_type = bldg_specs[bid]
        else:
            lvls = max(3, min(5, lvls_tag))
            h_wall = lvls * 3.8
            mat_wall = mat_grey if (bid % 3 != 0) else mat_buff
            mat_frm = mat_white if (bid % 2 == 0) else mat_dark
            roof_type = "pitched" if (bid % 3 == 0) else "flat"

        h_stagger = (((int(bid) * 7) % 31) - 15) * 0.12
        h_wall = round(h_wall + h_stagger, 2)

        create_extruded_polygon(f"Bldg_{bid}_Plinth", clean_pts, 0.0, 0.95, mat_rubble, target_col, bevel_w=0.015)
        create_extruded_polygon(f"Bldg_{bid}_Body", clean_pts, 0.95, h_wall, mat_wall, target_col, bevel_w=0.02, cap_top=False)

        if bid == 339876874:
            p1, p2 = (133.232, -129.064), (120.609, -121.694)
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            elen = math.hypot(dx, dy)
            erot = math.atan2(dy, dx)
            nx, ny = compute_outward_normal(p1, p2, clean_pts)[0]
            mx, my = (p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5
            create_box(f"Bldg_{bid}_SWBrickOverlay", (mx + nx * 0.08, my + ny * 0.08, 7.6), (elen, 0.22, 9.2), erot, mat_brick, target_col)
            for q_i in range(22):
                qz = 0.5 + q_i * 0.52
                qw = 0.62 if q_i % 2 == 0 else 0.40
                create_box(f"Bldg_{bid}_Quoin_{q_i}", (133.232, -129.064, qz), (qw, qw, 0.45), erot, mat_quoin, target_col)

        # Roof Massing + Rooftop Mechanical Units, Skylights & Chimneys (for satellite_topdown & overview fidelity!)
        cx = sum(p[0] for p in clean_pts) / len(clean_pts)
        cy = sum(p[1] for p in clean_pts) / len(clean_pts)
        create_extruded_polygon(f"Bldg_{bid}_RoofCap", clean_pts, h_wall, h_wall + 0.38, mat_quoin, target_col, bevel_w=0.02, cap_bottom=False, cap_top=False)
        if roof_type == "mansard":
            inner_pts = [(p[0] + (cx - p[0]) * 0.05, p[1] + (cy - p[1]) * 0.05) for p in clean_pts]
            create_extruded_polygon(f"Bldg_{bid}_Mansard", inner_pts, h_wall + 0.35, h_wall + 3.6, mat_slate, target_col, bevel_w=0.03)
            top_pts = [(p[0] + (cx - p[0]) * 0.22, p[1] + (cy - p[1]) * 0.22) for p in clean_pts]
            create_extruded_polygon(f"Bldg_{bid}_MansardTop", top_pts, h_wall + 3.55, h_wall + 3.85, mat_flat, target_col, bevel_w=0.02)
        elif roof_type == "pitched":
            inner_pts = [(p[0] + (cx - p[0]) * 0.06, p[1] + (cy - p[1]) * 0.06) for p in clean_pts]
            create_extruded_polygon(f"Bldg_{bid}_PitchedRoof", inner_pts, h_wall + 0.35, h_wall + 2.8, mat_slate, target_col, bevel_w=0.03)
        else:
            create_extruded_polygon(f"Bldg_{bid}_FlatDeck", clean_pts, h_wall + 0.38, h_wall + 0.58, mat_flat, target_col, bevel_w=0.01, cap_bottom=False)
            if is_owned:
                create_box(f"Bldg_{bid}_HVAC", (cx, cy, h_wall + 1.45), (2.4, 1.2, 1.6), math.radians(-21.0), mat_quoin, target_col)
                create_box(f"Bldg_{bid}_Skylight", (cx + 2.5, cy - 1.8, h_wall + 0.95), (2.0, 1.4, 0.7), math.radians(-21.0), mat_glass, target_col)

        # Rooftop solar array visible on 339877652 in `satellite_topdown.png`
        if bid == 339877652:
            create_box("Bldg_652_SolarArray", (cx, cy, h_wall + 4.05), (6.5, 12.5, 0.25), math.radians(-30.0), mat_solar, target_col)

        n_pts = len(clean_pts)
        for e_i in range(n_pts):
            p1 = clean_pts[e_i]
            p2 = clean_pts[(e_i + 1) % n_pts]
            (nx, ny), elen = compute_outward_normal(p1, p2, clean_pts)
            if elen < 4.5:
                continue

            mx, my = (p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5
            if bid in (339877245, 339877244) and nx > 0.6:
                continue
            if bid == 339877593 and 144.0 < mx < 151.0 and -92.0 < my < -74.0:
                continue
            if bid == 339877593 and 90.0 < mx < 104.0 and -65.0 < my < -47.0:
                continue
            if bid == 339876531 and nx > 0.5:
                continue
            if bid == 339877652 and (ny > 0.5 or nx < -0.5):
                continue

            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            erot = math.atan2(dy, dx)

            create_box(f"Bldg_{bid}_E{e_i}_GndCornice", (mx + nx * 0.16, my + ny * 0.16, 3.85), (elen, 0.32, 0.28), erot, mat_quoin, target_col, cap_top=False, cap_bottom=False)
            create_box(f"Bldg_{bid}_E{e_i}_TopCornice", (mx + nx * 0.22, my + ny * 0.22, h_wall - 0.15), (elen + 0.2, 0.44, 0.34), erot, mat_quoin, target_col, cap_top=False, cap_bottom=False)

            n_cols = max(1, int((elen - 1.4) / 3.4))
            for c_i in range(n_cols):
                t_pos = (c_i + 0.5) / float(n_cols)
                wx, wy = p1[0] + t_pos * dx, p1[1] + t_pos * dy
                add_window_bay(f"Bldg_{bid}_E{e_i}_Gnd_{c_i}", wx, wy, 2.20, 1.95, 2.45, erot, nx, ny, mat_quoin, mat_frm, mat_glass, None, target_col, arched=(bid % 2 == 0), panes_x=2)
                for fl_i in range(1, lvls):
                    fz = 2.20 + fl_i * ((h_wall - 3.4) / float(max(1, lvls - 1)))
                    add_window_bay(f"Bldg_{bid}_E{e_i}_W_{c_i}_{fl_i}", wx, wy, fz, 1.45, 2.15, erot, nx, ny, mat_quoin, mat_frm, mat_glass, mat_iron, target_col, arched=(bid % 3 == 0), panes_x=2, balcony=(is_owned and fl_i == 1))


# ---------------------------------------------------------------------------
# 5. STREETS, COURS LE ROYER PROMENADE, TREES & STREET FURNITURE
# ---------------------------------------------------------------------------
def build_public_realm(dossier, palette, kit_assets, col):
    mat_cobble = palette["Mat_Cobble_Street"]
    mat_courtyard = palette["Mat_Cobble_Courtyard"]
    mat_asphalt = palette["Mat_Asphalt"]
    mat_sidewalk = palette["Mat_Sidewalk"]
    mat_iron = palette["Mat_Iron_Black"]
    mat_white = palette["Mat_Frame_White"]

    create_box("Block_Ground_Asphalt", (145.0, -90.0, -0.08), (260.0, 280.0, 0.16), 0.0, mat_asphalt, col, bevel_w=0.0)

    rot_grid = math.radians(-21.0)
    create_box("Sidewalk_West_Cluster", (122.0, -88.0, 0.07), (56.0, 128.0, 0.14), rot_grid, mat_sidewalk, col, bevel_w=0.01)
    create_box("Sidewalk_East_Cluster", (188.0, -68.0, 0.07), (58.0, 152.0, 0.14), rot_grid, mat_sidewalk, col, bevel_w=0.01)
    create_box("Sidewalk_South_Context", (130.0, -175.0, 0.07), (95.0, 62.0, 0.14), rot_grid, mat_sidewalk, col, bevel_w=0.01)

    # 1. Rue Saint-Sulpice & Rue De Brésoles Cobblestone Roadway (at z = 0.11m so cobblestone is visible in Camera 4!)
    p_ss1, p_ss2 = (98.0, -8.0), (164.0, -39.0)
    dx_ss, dy_ss = p_ss2[0] - p_ss1[0], p_ss2[1] - p_ss1[1]
    rot_ss = math.atan2(dy_ss, dx_ss)
    create_box("Road_Rue_SaintSulpice_Cobble", ((p_ss1[0] + p_ss2[0]) * 0.5, (p_ss1[1] + p_ss2[1]) * 0.5, 0.11), (math.hypot(dx_ss, dy_ss), 7.6, 0.10), rot_ss, mat_cobble, col, bevel_w=0.0)
    # Raised sidewalk along SW side of Rue Saint-Sulpice (in front of 339877652 & 339877243)
    create_box("Sidewalk_Rue_SaintSulpice_SW", (130.0, -29.5, 0.14), (62.0, 3.2, 0.18), rot_ss, mat_sidewalk, col, bevel_w=0.01)

    # 2. Cours Le Royer / Rue Saint-Dizier Cobblestone & Sidewalk Corridor
    p_clr1, p_clr2 = (161.5, -45.0), (135.5, -135.0)
    dx_c, dy_c = p_clr2[0] - p_clr1[0], p_clr2[1] - p_clr2[1]
    rot_clr = math.atan2(dy_c, dx_c)
    create_box("Promenade_Cours_Le_Royer", ((p_clr1[0] + p_clr2[0]) * 0.5, (p_clr1[1] + p_clr2[1]) * 0.5, 0.09), (math.hypot(dx_c, dy_c), 7.0, 0.08), rot_clr, mat_courtyard, col, bevel_w=0.0)

    nx_c, ny_c = dy_c / math.hypot(dx_c, dy_c), -dx_c / math.hypot(dx_c, dy_c)
    for s_sign in (-1.0, 1.0):
        create_box(f"Sidewalk_CoursLeRoyer_{int(s_sign)}", (148.5 + s_sign * nx_c * 4.8, -90.0 + s_sign * ny_c * 4.8, 0.13), (92.0, 3.2, 0.16), rot_clr, mat_sidewalk, col, bevel_w=0.01)

    for p_i, (ux, uy) in enumerate([(143.5, -108.0), (142.2, -112.5), (140.8, -117.0), (139.5, -121.5)]):
        create_cylinder(f"Patio_Pole_{p_i}", (ux, uy, 1.3), 0.04, 2.4, (0, 0, 0), mat_iron, col, segments=8)
        create_cylinder(f"Patio_Table_{p_i}", (ux, uy, 0.78), 0.55, 0.05, (0, 0, 0), mat_white, col, segments=12)
        create_cylinder(f"Patio_Umbrella_{p_i}", (ux, uy, 2.45), 1.45, 0.35, (0, 0, 0), mat_white, col, segments=8)

    # 3. Poly Haven `jacaranda_tree_LOD0` 3D Trees (including foreground right tree overhanging Camera 4!)
    tree_template = kit_assets.get("jacaranda_tree_LOD0")
    curated_trees = [
        ("DeBresoles_ForegroundCanopy", 102.8, -22.2, 0.38),  # Overhanging upper-right of Camera 4 (`Corner_Rue_DeBresoles.jpg`)
        ("DeBresoles_WestTree", 88.0, -22.5, 0.46),
        ("CoursLeRoyer_1", 146.5, -102.0, 0.40),
        ("CoursLeRoyer_2", 142.5, -115.0, 0.42),
        ("CoursLeRoyer_3", 139.0, -126.0, 0.38),
        ("PlaceRoyale_1", 141.0, -148.0, 0.45),
        ("PlaceRoyale_2", 172.0, -152.0, 0.46),
        ("SemGarden_East_1", 95.0, -105.0, 0.52),
        ("SemGarden_East_2", 85.0, -120.0, 0.50),
    ]
    if tree_template:
        for i, (tname, tx, ty, ts) in enumerate(curated_trees):
            inst = tree_template.copy()
            inst.data = tree_template.data
            inst.name = f"PH_Tree_{i}_{tname}"
            col.objects.link(inst)
            inst.scale = (ts, ts, ts)
            inst.location = (tx, ty, 0.0)
            inst.rotation_euler = (0.0, 0.0, (i * 1.9) % (2.0 * math.pi))

    # 4. Street Lamps & Benches from `assets/montreal_kit.blend`
    lamp_template = kit_assets.get("street_lamp_01")
    bench_template = kit_assets.get("Master_Street_Bench")
    lamp_coords = [
        (128.4, -140.4),  # Foreground far-left of Camera 3 (`Corner_Rue_SaintPaul.jpg`)
        (148.5, -96.0),
        (144.0, -110.0),
        (140.0, -123.0),
        (116.0, -28.0),
        (134.0, -35.0),
    ]
    for l_i, (lx, ly) in enumerate(lamp_coords):
        if lamp_template:
            lp = lamp_template.copy()
            lp.data = lamp_template.data
            lp.name = f"PH_StreetLamp_{l_i}"
            col.objects.link(lp)
            lp.location = (lx, ly, 0.14)
            lp.scale = (1.0, 1.0, 1.0)
        if bench_template and l_i in (1, 2, 3):
            bn = bench_template.copy()
            bn.data = bench_template.data
            bn.name = f"PH_Bench_{l_i}"
            col.objects.link(bn)
            bn.location = (lx + 1.2, ly - 0.8, 0.14)
            bn.rotation_euler = (0.0, 0.0, rot_clr)


# ---------------------------------------------------------------------------
# 6. WORLD HDRI LIGHTING & STREET VIEW CAMERAS
# ---------------------------------------------------------------------------
def setup_world_and_lighting(scene):
    scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 64

    world = bpy.data.worlds.get("World_MTL_VM_0007") or bpy.data.worlds.new("World_MTL_VM_0007")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.15
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    hdri_path = os.path.join(PH_DIR, "kloppenheim_06_puresky_2k.hdr")
    if os.path.exists(hdri_path):
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri_path, check_existing=True)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    else:
        bg.inputs["Color"].default_value = (0.55, 0.68, 0.88, 1.0)

    sun_data = bpy.data.lights.new(name="Sun_MTL_0007", type='SUN')
    sun_data.energy = 3.2
    sun_data.color = (1.0, 0.95, 0.86)
    sun_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new("Sun_MTL_0007", sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(15.0), math.radians(-135.0))


def render_cameras(scene, dossier, cam_col, iter_num=2):
    os.makedirs(RENDERS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.image_settings.file_format = 'PNG'

    # Calibrated camera pullbacks matching the exact 90-deg Street View car framing
    cam_overrides = {
        "Rue_SaintSulpice_Facade": (158.8, -68.9, 2.1, 294.0, 12.0),
        "Cours_Le_Royer_Courtyard": (153.8, -88.2, 2.0, 299.8, 12.0),
        "Corner_Rue_SaintPaul": (136.0, -142.5, 1.9, 320.0, 12.0),
        "Corner_Rue_DeBresoles": (106.59, -18.39, 1.8, 150.0, 10.0),
    }

    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        if label in cam_overrides:
            cx, cy, cz, heading, pitch = cam_overrides[label]
        else:
            cx, cy = cam_info["blender_cam_xy_m"]
            cz = 1.7
            heading = cam_info.get("heading", cam_info.get("heading_deg", 0.0))
            pitch = cam_info.get("pitch_deg", 10.0)
        fov = cam_info.get("fov_deg", 90.0)

        cam_data = bpy.data.cameras.new(name=f"SV_Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(fov)
        cam_data.clip_start = 0.1
        cam_data.clip_end = 1000.0

        cam_obj = bpy.data.objects.new(f"SV_Cam_{label}", cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cx, cy, cz)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch), 0.0, math.radians(-heading))

        scene.camera = cam_obj
        out_file = os.path.join(RENDERS_DIR, f"iter{iter_num}_{label}.png")
        scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View Camera [{label}] -> {out_file}")

    ov_data = bpy.data.cameras.new(name=f"{BLOCK_ID}_Overview_Cam")
    ov_data.lens_unit = 'FOV'
    ov_data.angle = math.radians(62.0)
    ov_obj = bpy.data.objects.new(f"{BLOCK_ID}_Overview_Cam", ov_data)
    cam_col.objects.link(ov_obj)
    ov_obj.location = (92.0, -172.0, 95.0)
    target = Vector((152.0, -72.0, 8.0))
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    snap_path = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
    scene.render.filepath = snap_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Block Overview Snapshot -> {snap_path}")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    root_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(root_col)
    owned_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    root_col.children.link(owned_col)
    context_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Context_Proxy")
    root_col.children.link(context_col)
    context_col.hide_render = True
    context_col.hide_viewport = True
    cam_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Cameras")
    root_col.children.link(cam_col)

    palette = create_block_palette()
    kit_assets = load_kit_assets()

    build_all_buildings(dossier, palette, owned_col, context_col)
    build_hero_facades(dossier, palette, owned_col)
    build_public_realm(dossier, palette, kit_assets, owned_col)

    scene = bpy.context.scene
    setup_world_and_lighting(scene)
    render_cameras(scene, dossier, cam_col, iter_num=2)

    os.makedirs(OUTPUT_BLOCKS_DIR, exist_ok=True)
    blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.blend")
    bpy.context.preferences.filepaths.save_version = 0
    tmp_blend = blend_path + ".tmp.blend"
    if os.path.exists(tmp_blend):
        try:
            os.remove(tmp_blend)
        except OSError:
            pass
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
    for ext in ("", "@", "@1", "1"):
        p = blend_path + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    if os.path.exists(tmp_blend):
        os.replace(tmp_blend, blend_path)
    sys.path.append(os.path.join(PROJECT_ROOT, "src", "blocks"))
    import upgrade_MTL_VM_0007
    upgrade_MTL_VM_0007.polish_block()
    proxy_col = bpy.data.collections.get(f"Block_{BLOCK_ID}_Context_Proxy")
    if proxy_col:
        proxy_col.hide_render = True
        proxy_col.hide_viewport = True
        for o in proxy_col.all_objects:
            if o is not None:
                try:
                    o.hide_render = True
                    o.hide_viewport = True
                except Exception:
                    pass
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=False)


if __name__ == "__main__":
    main()
