"""
Shared Procedural & Image-Textured Montreal Asset & Material Library Generator (`build_montreal_kit.py`).
Can be imported directly inside any Blender script (`import build_montreal_kit as kit`)
OR run standalone (`blender -b -P src/build_montreal_kit.py`) to build `assets/montreal_kit.blend`.
"""
import os
import math
import random
import bpy
import bmesh

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
POLYHAVEN_DIR = os.path.join(ASSETS_DIR, "polyhaven")
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(POLYHAVEN_DIR, exist_ok=True)
KIT_BLEND_PATH = os.path.join(ASSETS_DIR, "montreal_kit.blend")


def hex_to_rgba(hex_str: str, alpha: float = 1.0):
    h = hex_str.lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    # Convert sRGB to linear approximation for Principled BSDF
    return (r ** 2.2, g ** 2.2, b ** 2.2, alpha)


def _find_polyhaven_map(asset_id: str, map_types: list):
    """Finds texture map on disk matching asset_id and map_types (e.g. ['Diffuse_2k', 'diff_2k'])."""
    for mtype in map_types:
        for ext in [".jpg", ".png", ".jpeg"]:
            cand = os.path.join(POLYHAVEN_DIR, f"{asset_id}_{mtype}{ext}")
            if os.path.exists(cand):
                return cand
    return None


def get_or_load_image(filepath: str, colorspace: str = "sRGB"):
    """Loads or retrieves cached Blender image with proper colorspace."""
    norm_path = os.path.normpath(filepath)
    fname = os.path.basename(norm_path)
    for img in bpy.data.images:
        if img.filepath and os.path.normpath(bpy.path.abspath(img.filepath)) == norm_path:
            return img
        if img.name == fname:
            return img
    img = bpy.data.images.load(norm_path)
    if colorspace and hasattr(img, "colorspace_settings"):
        img.colorspace_settings.name = colorspace
    return img


def get_or_create_image_pbr_material(name: str, asset_id: str, fallback_hex: str = "#9E988D", uv_scale: float = 1.0, bump_strength: float = 1.0):
    """
    Creates a full 2K PBR material using Poly Haven image textures (Base Color, Roughness, Normal Map).
    Compatible with EEVEE, Cycles, and USD Preview Surface export.
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    diff_path = _find_polyhaven_map(asset_id, ["Diffuse_2k", "diff_2k", "col_2k"])
    rough_path = _find_polyhaven_map(asset_id, ["Roughness_2k", "Rough_2k", "rough_2k"])
    nor_path = _find_polyhaven_map(asset_id, ["nor_gl_2k", "nor_2k", "normal_2k"])

    # If any texture map is missing, fallback to procedural PBR
    if not (diff_path and rough_path and nor_path):
        return get_or_create_pbr_material(name, fallback_hex)

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    rgba = hex_to_rgba(fallback_hex)
    mat.diffuse_color = rgba

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output node
    out_node = nodes.new("ShaderNodeOutputMaterial")
    out_node.location = (400, 0)

    # Principled BSDF
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    links.new(out_node.inputs["Surface"], bsdf.outputs["BSDF"])

    # TexCoord & Mapping
    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-700, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-500, 0)
    mapping.inputs["Scale"].default_value = (uv_scale, uv_scale, uv_scale)
    links.new(mapping.inputs["Vector"], tex_coord.outputs["UV"])

    # Base Color Texture
    diff_img = get_or_load_image(diff_path, "sRGB")
    tex_diff = nodes.new("ShaderNodeTexImage")
    tex_diff.name = "TexImage_Diffuse"
    tex_diff.location = (-250, 150)
    tex_diff.image = diff_img
    links.new(tex_diff.inputs["Vector"], mapping.outputs["Vector"])
    links.new(bsdf.inputs["Base Color"], tex_diff.outputs["Color"])

    # Roughness Texture
    rough_img = get_or_load_image(rough_path, "Non-Color")
    tex_rough = nodes.new("ShaderNodeTexImage")
    tex_rough.name = "TexImage_Roughness"
    tex_rough.location = (-250, -50)
    tex_rough.image = rough_img
    links.new(tex_rough.inputs["Vector"], mapping.outputs["Vector"])
    links.new(bsdf.inputs["Roughness"], tex_rough.outputs["Color"])

    # Normal Map Texture + Normal Map Node
    nor_img = get_or_load_image(nor_path, "Non-Color")
    tex_nor = nodes.new("ShaderNodeTexImage")
    tex_nor.name = "TexImage_Normal"
    tex_nor.location = (-250, -250)
    tex_nor.image = nor_img

    nmap = nodes.new("ShaderNodeNormalMap")
    nmap.location = (-50, -250)
    nmap.inputs["Strength"].default_value = bump_strength
    links.new(tex_nor.inputs["Vector"], mapping.outputs["Vector"])
    links.new(nmap.inputs["Color"], tex_nor.outputs["Color"])
    links.new(bsdf.inputs["Normal"], nmap.outputs["Normal"])

    return mat


def get_or_create_water_pbr_material(name: str = "Mat_MTL_StLawrence_Water_PBR", uv_scale: float = 1.0):
    """
    Creates the dedicated 2K PBR Water material for the St. Lawrence River, harbor basins, and canal.
    Uses synthesized 2K water maps: diffuse, normal (nor_gl), micro-roughness, and Worley foam.
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    diff_path = os.path.join(POLYHAVEN_DIR, "water_river_diffuse_2k.jpg")
    rough_path = os.path.join(POLYHAVEN_DIR, "water_river_rough_2k.jpg")
    nor_path = os.path.join(POLYHAVEN_DIR, "water_river_nor_gl_2k.jpg")
    foam_path = os.path.join(POLYHAVEN_DIR, "water_foam_edge_2k.jpg")

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = (0.05, 0.18, 0.25, 1.0)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node = nodes.new("ShaderNodeOutputMaterial")
    out_node.location = (450, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (150, 0)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 1.333
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.15
    elif "Transmission" in bsdf.inputs:
        bsdf.inputs["Transmission"].default_value = 0.15
    links.new(out_node.inputs["Surface"], bsdf.outputs["BSDF"])

    # TexCoord & Mapping
    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-750, 0)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-550, 0)
    mapping.inputs["Scale"].default_value = (uv_scale, uv_scale, uv_scale)
    links.new(mapping.inputs["Vector"], tex_coord.outputs["UV"])

    # Diffuse Base Color
    if os.path.exists(diff_path):
        diff_img = get_or_load_image(diff_path, "sRGB")
        tex_diff = nodes.new("ShaderNodeTexImage")
        tex_diff.name = "TexImage_Water_Diffuse"
        tex_diff.location = (-250, 200)
        tex_diff.image = diff_img
        links.new(tex_diff.inputs["Vector"], mapping.outputs["Vector"])
        links.new(bsdf.inputs["Base Color"], tex_diff.outputs["Color"])

    # Micro-Roughness
    if os.path.exists(rough_path):
        rough_img = get_or_load_image(rough_path, "Non-Color")
        tex_rough = nodes.new("ShaderNodeTexImage")
        tex_rough.name = "TexImage_Water_Roughness"
        tex_rough.location = (-250, 0)
        tex_rough.image = rough_img
        links.new(tex_rough.inputs["Vector"], mapping.outputs["Vector"])
        links.new(bsdf.inputs["Roughness"], tex_rough.outputs["Color"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.08

    # Normal Map
    if os.path.exists(nor_path):
        nor_img = get_or_load_image(nor_path, "Non-Color")
        tex_nor = nodes.new("ShaderNodeTexImage")
        tex_nor.name = "TexImage_Water_Normal"
        tex_nor.location = (-250, -200)
        tex_nor.image = nor_img
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.location = (-50, -200)
        nmap.inputs["Strength"].default_value = 1.0
        links.new(tex_nor.inputs["Vector"], mapping.outputs["Vector"])
        links.new(nmap.inputs["Color"], tex_nor.outputs["Color"])
        links.new(bsdf.inputs["Normal"], nmap.outputs["Normal"])

    # Foam edge mask (kept available in node graph for water shader mixers)
    if os.path.exists(foam_path):
        foam_img = get_or_load_image(foam_path, "Non-Color")
        tex_foam = nodes.new("ShaderNodeTexImage")
        tex_foam.name = "TexImage_Water_Foam"
        tex_foam.location = (-250, -400)
        tex_foam.image = foam_img
        links.new(tex_foam.inputs["Vector"], mapping.outputs["Vector"])

    return mat


def get_or_create_pbr_material(name: str, hex_color: str, roughness: float = 0.7, metallic: float = 0.0, bump_strength: float = 0.08, noise_scale: float = 18.0):
    """Fallback procedural PBR material for auxiliary elements without image sets."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    rgba = hex_to_rgba(hex_color)
    mat.diffuse_color = rgba

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic

    if bump_strength > 0.0:
        tex_coord = nodes.new("ShaderNodeTexCoord")
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = noise_scale
        noise.inputs["Detail"].default_value = 6.0
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.02

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (rgba[0] * 0.86, rgba[1] * 0.86, rgba[2] * 0.86, 1.0)
        ramp.color_ramp.elements[1].color = (min(1.0, rgba[0] * 1.12), min(1.0, rgba[1] * 1.12), min(1.0, rgba[2] * 1.12), 1.0)

        links.new(noise.inputs["Vector"], tex_coord.outputs["Object"])
        links.new(ramp.inputs["Fac"], noise.outputs["Fac"])
        links.new(bsdf.inputs["Base Color"], ramp.outputs["Color"])
        links.new(bump.inputs["Height"], noise.outputs["Fac"])
        links.new(bsdf.inputs["Normal"], bump.outputs["Normal"])

    return mat


def create_montreal_material_palette():
    """
    Creates and returns a comprehensive dictionary of authentic Montreal architectural materials,
    including 14 distinct Poly Haven 2K PBR facade materials, 2K PBR water, asphalt, cobblestone,
    and heritage architectural accents.
    """
    palette = {
        # --- 14 Distinct Poly Haven 2K PBR Architectural Facade Materials ---
        "Mat_MTL_PierreGrise_Limestone": get_or_create_image_pbr_material("Mat_MTL_PierreGrise_Limestone", "stone_brick_wall_001", fallback_hex="#B5B0A6"),
        "Mat_MTL_WarmBuff_Limestone": get_or_create_image_pbr_material("Mat_MTL_WarmBuff_Limestone", "sandstone_blocks_05", fallback_hex="#C4B9A5"),
        "Mat_MTL_Red_Sandstone": get_or_create_image_pbr_material("Mat_MTL_Red_Sandstone", "red_sandstone_wall", fallback_hex="#9E523B"),
        "Mat_MTL_Heritage_RedBrick": get_or_create_image_pbr_material("Mat_MTL_Heritage_RedBrick", "castle_brick_02_red", fallback_hex="#8E3B2E"),
        "Mat_MTL_Victorian_Brick": get_or_create_image_pbr_material("Mat_MTL_Victorian_Brick", "brick_wall_04", fallback_hex="#994D3F"),
        "Mat_MTL_Yellow_Buff_Brick": get_or_create_image_pbr_material("Mat_MTL_Yellow_Buff_Brick", "yellow_brick", fallback_hex="#C2AC75"),
        "Mat_MTL_Dark_Loft_Brick": get_or_create_image_pbr_material("Mat_MTL_Dark_Loft_Brick", "dark_brick_wall", fallback_hex="#4A3B35"),
        "Mat_MTL_Whitewash_Fieldstone": get_or_create_image_pbr_material("Mat_MTL_Whitewash_Fieldstone", "castle_brick_02_white", fallback_hex="#D9D5CD"),
        "Mat_MTL_Precast_Concrete": get_or_create_image_pbr_material("Mat_MTL_Precast_Concrete", "concrete_block_wall", fallback_hex="#8A8C8C"),
        "Mat_MTL_Granite_Plinth": get_or_create_image_pbr_material("Mat_MTL_Granite_Plinth", "stone_block_wall", fallback_hex="#6E6A63"),
        "Mat_MTL_Weathered_Metal": get_or_create_image_pbr_material("Mat_MTL_Weathered_Metal", "box_profile_metal_sheet", fallback_hex="#6B7275"),
        "Mat_MTL_Warm_Timber": get_or_create_image_pbr_material("Mat_MTL_Warm_Timber", "weathered_planks", fallback_hex="#8C5832"),
        "Mat_MTL_Limestone_Tile": get_or_create_image_pbr_material("Mat_MTL_Limestone_Tile", "stone_tile_wall", fallback_hex="#B8B2A7"),
        "Mat_MTL_Medieval_Stone": get_or_create_image_pbr_material("Mat_MTL_Medieval_Stone", "medieval_blocks_06", fallback_hex="#7F7B72"),

        # --- Dedicated 2K PBR Water Material ---
        "Mat_MTL_StLawrence_Water_PBR": get_or_create_water_pbr_material("Mat_MTL_StLawrence_Water_PBR"),

        # --- Street, Sidewalk, Park & Ground PBR Materials (Poly Haven 2K Photogrammetry) ---
        "Mat_PH_Leafy_Grass": get_or_create_image_pbr_material("Mat_PH_Leafy_Grass", "leafy_grass", fallback_hex="#4A6B2F"),
        "Mat_PH_Forest_Ground": get_or_create_image_pbr_material("Mat_PH_Forest_Ground", "forrest_ground_01", fallback_hex="#5A4D3B"),
        "Mat_PH_Grass_Path": get_or_create_image_pbr_material("Mat_PH_Grass_Path", "grass_path_2", fallback_hex="#5B6339"),
        "Mat_PH_Concrete_Pavers": get_or_create_image_pbr_material("Mat_PH_Concrete_Pavers", "concrete_pavers", fallback_hex="#9E9B95"),
        "Mat_PH_Concrete_Sidewalk": get_or_create_image_pbr_material("Mat_PH_Concrete_Sidewalk", "concrete_pavement_02", fallback_hex="#A6A39E"),
        "Mat_PH_Stone_Pavers": get_or_create_image_pbr_material("Mat_PH_Stone_Pavers", "stone_pavers", fallback_hex="#7A7772"),
        "Mat_PH_Herringbone_Pavement": get_or_create_image_pbr_material("Mat_PH_Herringbone_Pavement", "herringbone_pavement", fallback_hex="#8A6E5D"),
        "Mat_PH_Gravel_Path": get_or_create_image_pbr_material("Mat_PH_Gravel_Path", "gravel_concrete_02", fallback_hex="#8C877E"),
        "Mat_PH_Clean_Asphalt": get_or_create_image_pbr_material("Mat_PH_Clean_Asphalt", "clean_asphalt", fallback_hex="#333538"),
        "Mat_PH_Worn_Asphalt": get_or_create_image_pbr_material("Mat_PH_Worn_Asphalt", "worn_asphalt", fallback_hex="#3D3F42"),
        "Mat_PH_Red_Brick_Pavers": get_or_create_image_pbr_material("Mat_PH_Red_Brick_Pavers", "red_brick_pavers", fallback_hex="#8E4337"),

        # --- Legacy Street, Sidewalk & Ground PBR Materials (upgraded to Poly Haven 2K) ---
        "Mat_MTL_Street_Asphalt": get_or_create_image_pbr_material("Mat_MTL_Street_Asphalt", "clean_asphalt", fallback_hex="#333538"),
        "Mat_MTL_Cobblestone": get_or_create_image_pbr_material("Mat_MTL_Cobblestone", "cobblestone_floor_08", fallback_hex="#686560"),
        "Mat_MTL_Fieldstone_Rubble": get_or_create_image_pbr_material("Mat_MTL_Fieldstone_Rubble", "gravel_concrete_02", fallback_hex="#8C877E"),
        "Mat_MTL_Plaza_Charcoal_Granite": get_or_create_image_pbr_material("Mat_MTL_Plaza_Charcoal_Granite", "stone_pavers", fallback_hex="#5E6165"),
        "Mat_MTL_Plaza_Light_Granite": get_or_create_image_pbr_material("Mat_MTL_Plaza_Light_Granite", "concrete_pavers", fallback_hex="#B8B5AE"),

        # --- Heritage Metals, Glazing & Architectural Details ---
        "Mat_MTL_Verdigris_Copper": get_or_create_pbr_material("Mat_MTL_Verdigris_Copper", "#5B8C7A", roughness=0.45, metallic=0.65, bump_strength=0.05, noise_scale=25.0),
        "Mat_MTL_Dark_Bronze_CurtainWall": get_or_create_pbr_material("Mat_MTL_Dark_Bronze_CurtainWall", "#242629", roughness=0.25, metallic=0.85, bump_strength=0.02),
        "Mat_MTL_Window_Glass_Dark": get_or_create_pbr_material("Mat_MTL_Window_Glass_Dark", "#1C2833", roughness=0.12, metallic=0.35, bump_strength=0.0),
        "Mat_MTL_CastIron_Black": get_or_create_pbr_material("Mat_MTL_CastIron_Black", "#1D1F21", roughness=0.38, metallic=0.80, bump_strength=0.04),
        "Mat_MTL_Statue_Bronze": get_or_create_pbr_material("Mat_MTL_Statue_Bronze", "#2F3833", roughness=0.35, metallic=0.75, bump_strength=0.05),
        "Mat_MTL_Slate_Roof_Dark": get_or_create_pbr_material("Mat_MTL_Slate_Roof_Dark", "#3A3D42", roughness=0.65, bump_strength=0.08),

        # --- Foliage & Organic Accent Materials ---
        "Mat_MTL_Tree_Bark": get_or_create_pbr_material("Mat_MTL_Tree_Bark", "#4A3C31", roughness=0.90, bump_strength=0.20, noise_scale=15.0),
        "Mat_MTL_Autumn_Gold": get_or_create_pbr_material("Mat_MTL_Autumn_Gold", "#C89B28", roughness=0.65, bump_strength=0.12, noise_scale=25.0),
        "Mat_MTL_Autumn_Amber": get_or_create_pbr_material("Mat_MTL_Autumn_Amber", "#B5651E", roughness=0.65, bump_strength=0.12, noise_scale=25.0),
        "Mat_MTL_Autumn_OliveGreen": get_or_create_pbr_material("Mat_MTL_Autumn_OliveGreen", "#5A782E", roughness=0.65, bump_strength=0.12, noise_scale=25.0),
        "Mat_MTL_Warm_Wood": get_or_create_pbr_material("Mat_MTL_Warm_Wood", "#8C5832", roughness=0.62, bump_strength=0.08, noise_scale=20.0),
    }
    return palette


def build_extruded_building_from_osm(name: str, coords_xy: list, height: float, mat_wall, mat_roof, mat_window, collection, floor_height: float = 3.8, add_cornice: bool = True, roof_type: str = "flat"):
    """
    Constructs a georeferenced 3D architectural building mesh from an OSM polygon footprint (`coords_xy`),
    complete with recessed window bays, ground-floor plinth, and cornice/roof.
    """
    if len(coords_xy) < 3:
        return None

    # Remove duplicate closing point if present
    pts = coords_xy[:-1] if coords_xy[0] == coords_xy[-1] else coords_xy
    if len(pts) < 3:
        return None

    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    bm = bmesh.new()
    verts_bottom = [bm.verts.new((p[0], p[1], 0.0)) for p in pts]
    try:
        face_bottom = bm.faces.new(verts_bottom)
    except ValueError:
        bm.free()
        return None

    # Ensure upward normal before extrusion
    face_bottom.normal_update()
    if face_bottom.normal.z < 0:
        face_bottom.normal_flip()

    # Extrude main volume
    ret = bmesh.ops.extrude_face_region(bm, geom=[face_bottom])
    extruded_verts = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=extruded_verts, vec=(0.0, 0.0, height))

    bm.to_mesh(mesh)
    bm.free()

    obj.data.materials.append(mat_wall)
    obj.data.materials.append(mat_roof)
    obj.data.materials.append(mat_window)

    # Assign roof material to top faces
    for poly in obj.data.polygons:
        if poly.normal.z > 0.8:
            poly.material_index = 1
        else:
            poly.material_index = 0

    return obj


POLYHAVEN_MODELS_DIR = os.path.join(POLYHAVEN_DIR, "models")

POLYHAVEN_TREE_MODELS = [
    "jacaranda_tree",
    "tree_small_02",
    "searsia_burchellii",
    "pine_tree_01",
    "fir_tree_01",
    "shrub_01",
    "shrub_02",
    "grass_medium_01",
]

POLYHAVEN_STREET_LIGHT_MODELS = [
    "street_lamp_01",
    "street_lamp_02",
    "Lantern_01",
    "modular_electricity_poles",
]

POLYHAVEN_PARK_PROP_MODELS = [
    "painted_wooden_bench",
    "planter_box_01",
    "fire_hydrant",
    "rock_moss_set_01",
    "modular_street_seating",
]

_APPENDED_MODEL_TEMPLATES = {}


def append_polyhaven_model(asset_id: str, collection, instance_name: str, location=(0.0, 0.0, 0.0), rotation_z: float = 0.0, scale: float = 1.0):
    """
    Appends a Poly Haven 3D model from assets/polyhaven/models/<asset_id>/<asset_id>.blend once,
    caches its mesh data, and creates a linked-mesh instance at the requested location/rotation/scale.
    """
    blend_path = os.path.join(POLYHAVEN_MODELS_DIR, asset_id, f"{asset_id}.blend")
    if not os.path.isfile(blend_path):
        return None

    if asset_id not in _APPENDED_MODEL_TEMPLATES:
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            data_to.objects = list(data_from.objects)
        mesh_objs = [o for o in data_to.objects if o is not None and o.type == "MESH"]
        if not mesh_objs:
            return None
        cached_parts = []
        for o in mesh_objs:
            cached_parts.append({
                "mesh": o.data,
                "loc": (o.location.x, o.location.y, o.location.z),
                "rot": (o.rotation_euler.x, o.rotation_euler.y, o.rotation_euler.z),
                "scale": (o.scale.x, o.scale.y, o.scale.z)
            })
            if o.data:
                o.data.use_fake_user = True
            try:
                bpy.data.objects.remove(o, do_unlink=True)
            except Exception:
                pass
        _APPENDED_MODEL_TEMPLATES[asset_id] = cached_parts

    template_parts = _APPENDED_MODEL_TEMPLATES[asset_id]
    created = []
    for idx, tmpl in enumerate(template_parts):
        inst = bpy.data.objects.new(f"{instance_name}_{idx}", tmpl["mesh"])
        collection.objects.link(inst)
        inst.location = (
            location[0] + tmpl["loc"][0] * scale,
            location[1] + tmpl["loc"][1] * scale,
            location[2] + tmpl["loc"][2] * scale,
        )
        inst.rotation_euler = (
            tmpl["rot"][0],
            tmpl["rot"][1],
            tmpl["rot"][2] + rotation_z,
        )
        inst.scale = (
            tmpl["scale"][0] * scale,
            tmpl["scale"][1] * scale,
            tmpl["scale"][2] * scale,
        )
        created.append(inst)
    return created


if __name__ == "__main__":
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    palette = create_montreal_material_palette()
    for m in palette.values():
        m.use_fake_user = True
    bpy.ops.wm.save_as_mainfile(filepath=KIT_BLEND_PATH)
    print(f"Saved Montreal Material & Asset Kit ({len(palette)} materials) -> {KIT_BLEND_PATH}")

