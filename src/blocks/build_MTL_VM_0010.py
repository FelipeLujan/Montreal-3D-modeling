"""
Complete High-Poly Photorealistic 3D Architectural Reconstruction of Montreal Block MTL-VM-0010
("Palais des Congrès Colorful Glass Facade & Place Jean-Paul-Riopelle", 1001 Place Jean-Paul-Riopelle)

Implements AAA Urban Photorealism Standards:
1. Real Poly Haven 2K PBR Textures (`sandstone_blocks_05`, `castle_brick_02_red`, `cobblestone_floor_08`, `asphalt_02`)
   mapped via `TexCoord -> Object -> Mapping -> ImageTexture (projection='BOX', blend=0.25)` + Bump/Normal + Roughness.
2. Real Poly Haven 2K Outdoor HDRI (`kloppenheim_06_puresky_2k.hdr`) for natural sky clouds, skylight, and glass reflections.
3. Bespoke Multi-Colored Translucent Glass Curtain Wall & Sloped Atrium Gallery on Palais des Congrès (`21258128`),
   matching all 4 verified outdoor Google Street View cameras + `satellite_topdown.png` rooftop garden & white tensile pavilion.
4. Real Poly Haven 3D `jacaranda_tree_LOD0` trees from `assets/montreal_kit.blend`.
5. Strict Ownership Deduplication:
   - 162 Primary-Owned buildings (`is_primary_owner == True`) in `Block_MTL-VM-0010_Owned`
   - 3 Context Proxy buildings (`is_primary_owner == False`) in `Block_MTL-VM-0010_Context_Proxy`
"""

import os
import sys
import json
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import build_montreal_kit as kit

BLOCK_ID = "MTL-VM-0010"
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_BLOCKS_DIR = os.path.join(BASE_DIR, "output", "blocks")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(OUTPUT_BLOCKS_DIR, exist_ok=True)
os.makedirs(OUTPUT_RENDERS_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)


def create_collection_hierarchy():
    root_col = bpy.data.collections.new(f"Block_{BLOCK_ID}")
    bpy.context.scene.collection.children.link(root_col)
    owned_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
    root_col.children.link(owned_col)
    proxy_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Context_Proxy")
    root_col.children.link(proxy_col)
    streets_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Streets_And_Props")
    owned_col.children.link(streets_col)
    return root_col, owned_col, proxy_col, streets_col


def load_image_safe(filepath, colorspace='sRGB'):
    if not os.path.exists(filepath):
        return None
    img = bpy.data.images.load(filepath, check_existing=True)
    try:
        img.colorspace_settings.name = colorspace
    except Exception:
        pass
    return img


def apply_polyhaven_box_pbr(mat, asset_prefix, tint_hex, scale=0.35, roughness_mult=1.0, normal_strength=1.0, metallic=0.0):
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
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(mapping.inputs["Vector"], tex_coord.outputs["Object"])

    rgba = kit.hex_to_rgba(tint_hex)
    mat.diffuse_color = rgba

    diff_path = os.path.join(POLYHAVEN_DIR, f"{asset_prefix}_Diffuse_2k.jpg")
    rough_path = os.path.join(POLYHAVEN_DIR, f"{asset_prefix}_Rough_2k.jpg")
    norm_path = os.path.join(POLYHAVEN_DIR, f"{asset_prefix}_nor_gl_2k.jpg")

    img_diff = load_image_safe(diff_path, 'sRGB')
    if img_diff:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = img_diff
        tex_d.projection = 'BOX'
        tex_d.projection_blend = 0.25
        links.new(tex_d.inputs["Vector"], mapping.outputs["Vector"])
        mix_col = nodes.new("ShaderNodeMix")
        mix_col.data_type = 'RGBA'
        mix_col.blend_type = 'MULTIPLY'
        mix_col.inputs["Factor"].default_value = 0.65
        mix_col.inputs[6].default_value = rgba
        links.new(mix_col.inputs[7], tex_d.outputs["Color"])
        links.new(bsdf.inputs["Base Color"], mix_col.outputs[2])
    else:
        bsdf.inputs["Base Color"].default_value = rgba

    img_rough = load_image_safe(rough_path, 'Non-Color')
    if img_rough:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = img_rough
        tex_r.projection = 'BOX'
        tex_r.projection_blend = 0.25
        links.new(tex_r.inputs["Vector"], mapping.outputs["Vector"])
        math_r = nodes.new("ShaderNodeMath")
        math_r.operation = 'MULTIPLY'
        math_r.inputs[1].default_value = roughness_mult
        links.new(math_r.inputs[0], tex_r.outputs["Color"])
        links.new(bsdf.inputs["Roughness"], math_r.outputs["Value"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.7 * roughness_mult

    img_norm = load_image_safe(norm_path, 'Non-Color')
    if img_norm:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = img_norm
        tex_n.projection = 'BOX'
        tex_n.projection_blend = 0.25
        links.new(tex_n.inputs["Vector"], mapping.outputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = min(0.32, normal_strength * 0.26)
        bump.inputs["Distance"].default_value = 0.03
        links.new(bump.inputs["Height"], tex_n.outputs["Color"])
        links.new(bsdf.inputs["Normal"], bump.outputs["Normal"])

    return mat


def create_glass_material(name, hex_color, roughness=0.04, metallic=0.26, emission_strength=0.18):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    rgba = kit.hex_to_rgba(hex_color)
    mat.diffuse_color = rgba
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.88
    if emission_strength > 0 and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    links.new(out.inputs["Surface"], bsdf.outputs["BSDF"])
    return mat


def enhance_materials(palette):
    apply_polyhaven_box_pbr(palette["Mat_MTL_PierreGrise_Limestone"], "sandstone_blocks_05", "#D6D1C7", scale=0.85, roughness_mult=0.80, normal_strength=0.75)
    apply_polyhaven_box_pbr(palette["Mat_MTL_WarmBuff_Limestone"], "sandstone_blocks_05", "#DDD2BE", scale=0.85, roughness_mult=0.78, normal_strength=0.75)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Heritage_RedBrick"], "castle_brick_02_red", "#9E3E2E", scale=0.55, roughness_mult=0.88, normal_strength=1.20)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Cobblestone"], "cobblestone_floor_08", "#8C8984", scale=0.65, roughness_mult=0.82, normal_strength=1.10)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Street_Asphalt"], "asphalt_02", "#3C3F45", scale=0.32, roughness_mult=0.88, normal_strength=1.05)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Plaza_Light_Granite"], "cobblestone_floor_08", "#A6A49E", scale=1.15, roughness_mult=0.76, normal_strength=0.95)
    apply_polyhaven_box_pbr(palette["Mat_MTL_Plaza_Charcoal_Granite"], "asphalt_02", "#34373C", scale=0.45, roughness_mult=0.58, normal_strength=0.60)

    # Smooth fine-grain architectural precast concrete & narrow-course limestone for Palais des Congrès
    palette["Mat_Palais_Concrete"] = bpy.data.materials.get("Mat_Palais_Concrete") or bpy.data.materials.new("Mat_Palais_Concrete")
    apply_polyhaven_box_pbr(palette["Mat_Palais_Concrete"], "sandstone_blocks_05", "#D4D0C6", scale=1.65, roughness_mult=0.80, normal_strength=0.35)

    # Brushed Silver-Grey Aluminum Mullions & Trusses
    palette["Mat_Palais_Aluminum"] = kit.get_or_create_pbr_material("Mat_Palais_Aluminum", "#B4B9C0", roughness=0.30, metallic=0.84, bump_strength=0.02)
    palette["Mat_Palais_DarkSteel"] = kit.get_or_create_pbr_material("Mat_Palais_DarkSteel", "#262A30", roughness=0.42, metallic=0.65, bump_strength=0.03)
    palette["Mat_MTL_Polished_Black_Granite"] = bpy.data.materials.get("Mat_MTL_Polished_Black_Granite") or bpy.data.materials.new("Mat_MTL_Polished_Black_Granite")
    apply_polyhaven_box_pbr(palette["Mat_MTL_Polished_Black_Granite"], "asphalt_02", "#1A1C20", scale=0.50, roughness_mult=0.22, normal_strength=0.20, metallic=0.18)

    # Iconic Palais des Congrès Multi-Colored Translucent Glass Palette
    palette["Mat_MTL_Window_Glass_Dark"] = create_glass_material("Mat_MTL_Window_Glass_Dark", "#122230", roughness=0.04, metallic=0.32, emission_strength=0.06)
    palette["Mat_Palais_Glass_Clear"] = create_glass_material("Mat_Palais_Glass_Clear", "#264860", roughness=0.04, metallic=0.30, emission_strength=0.14)
    palette["Mat_Palais_Glass_Magenta"] = create_glass_material("Mat_Palais_Glass_Magenta", "#D81B60", roughness=0.04, metallic=0.20, emission_strength=0.38)
    palette["Mat_Palais_Glass_Cyan"] = create_glass_material("Mat_Palais_Glass_Cyan", "#039BE5", roughness=0.04, metallic=0.20, emission_strength=0.34)
    palette["Mat_Palais_Glass_Emerald"] = create_glass_material("Mat_Palais_Glass_Emerald", "#43A047", roughness=0.04, metallic=0.20, emission_strength=0.32)
    palette["Mat_Palais_Glass_Yellow"] = create_glass_material("Mat_Palais_Glass_Yellow", "#FDD835", roughness=0.04, metallic=0.18, emission_strength=0.36)
    palette["Mat_Palais_Glass_Orange"] = create_glass_material("Mat_Palais_Glass_Orange", "#FB8C00", roughness=0.04, metallic=0.20, emission_strength=0.34)
    palette["Mat_Palais_Glass_Violet"] = create_glass_material("Mat_Palais_Glass_Violet", "#5E35B1", roughness=0.04, metallic=0.22, emission_strength=0.35)

    # Heritage buff brick & streetscape props
    palette["Mat_Heritage_BuffBrick"] = bpy.data.materials.get("Mat_Heritage_BuffBrick") or bpy.data.materials.new("Mat_Heritage_BuffBrick")
    apply_polyhaven_box_pbr(palette["Mat_Heritage_BuffBrick"], "castle_brick_02_red", "#C8AC78", scale=0.65, roughness_mult=0.85, normal_strength=1.10)

    palette["Mat_RoyalBlue_Accent"] = kit.get_or_create_pbr_material("Mat_RoyalBlue_Accent", "#1565C0", roughness=0.32, metallic=0.25, bump_strength=0.02)
    palette["Mat_Reflective_White"] = kit.get_or_create_pbr_material("Mat_Reflective_White", "#F4F6F8", roughness=0.25, metallic=0.10, bump_strength=0.01)
    palette["Mat_Traffic_Orange"] = kit.get_or_create_pbr_material("Mat_Traffic_Orange", "#EE5318", roughness=0.38, bump_strength=0.02)
    palette["Mat_Chinatown_Red"] = kit.get_or_create_pbr_material("Mat_Chinatown_Red", "#B71C1C", roughness=0.35, metallic=0.15, bump_strength=0.03)
    palette["Mat_Chinatown_Gold"] = kit.get_or_create_pbr_material("Mat_Chinatown_Gold", "#D4AF37", roughness=0.25, metallic=0.85, bump_strength=0.02)
    palette["Mat_Rooftop_Lawn"] = kit.get_or_create_pbr_material("Mat_Rooftop_Lawn", "#3B6E38", roughness=0.85, bump_strength=0.12, noise_scale=35.0)
    palette["Mat_Interior_Warm"] = create_glass_material("Mat_Interior_Warm", "#FFE4B5", roughness=0.35, metallic=0.0, emission_strength=0.85)
    return palette


def clean_polygon_pts(coords_xy):
    pts = coords_xy[:-1] if coords_xy[0] == coords_xy[-1] else list(coords_xy)
    cleaned = []
    for p in pts:
        if not cleaned or math.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > 0.25:
            cleaned.append((float(p[0]), float(p[1])))
    if len(cleaned) > 2 and math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) < 0.25:
        cleaned.pop()
    return cleaned


def polygon_signed_area(pts):
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
    return 0.5 * area


def ensure_ccw(pts):
    if polygon_signed_area(pts) < 0:
        return list(reversed(pts))
    return pts


def inset_polygon_2d(pts, inset_dist):
    pts = ensure_ccw(pts)
    n = len(pts)
    new_pts = []
    for i in range(n):
        p_prev = Vector(pts[(i - 1) % n])
        p_curr = Vector(pts[i])
        p_next = Vector(pts[(i + 1) % n])
        v1 = (p_curr - p_prev)
        v2 = (p_next - p_curr)
        if v1.length < 1e-4 or v2.length < 1e-4:
            new_pts.append((p_curr.x, p_curr.y))
            continue
        v1.normalize()
        v2.normalize()
        n1 = Vector((-v1.y, v1.x))
        n2 = Vector((-v2.y, v2.x))
        bisector = n1 + n2
        if bisector.length < 1e-3:
            offset = n1 * inset_dist
        else:
            bisector.normalize()
            denom = max(0.55, bisector.dot(n1))
            offset = bisector * (inset_dist / denom)
            if offset.length > abs(inset_dist) * 1.65:
                offset = offset.normalized() * (abs(inset_dist) * 1.65)
        np = p_curr + offset
        new_pts.append((np.x, np.y))
    return new_pts


def add_prism_to_bm(bm, pts_2d, z0, z1, mat_side, mat_top, mat_bot=None):
    pts = ensure_ccw(pts_2d)
    if len(pts) < 3:
        return
    v_bot = [bm.verts.new((p[0], p[1], z0)) for p in pts]
    v_top = [bm.verts.new((p[0], p[1], z1)) for p in pts]
    n = len(pts)
    for i in range(n):
        f_side = bm.faces.new((v_bot[i], v_bot[(i + 1) % n], v_top[(i + 1) % n], v_top[i]))
        f_side.material_index = mat_side
    try:
        f_top = bm.faces.new(v_top)
        f_top.material_index = mat_top
        if mat_bot is not None:
            f_bot = bm.faces.new(list(reversed(v_bot)))
            f_bot.material_index = mat_bot
    except ValueError:
        pass


def add_oriented_box(bm, center_xyz, dir_xy, normal_xy, width, depth, height, mat_idx, smooth=False):
    dx, dy = dir_xy
    nx, ny = normal_xy
    cx, cy, cz = center_xyz
    hw = width * 0.5
    hd = depth * 0.5
    hh = height * 0.5
    corners_2d = [
        (cx - dx * hw - nx * hd, cy - dy * hw - ny * hd),
        (cx + dx * hw - nx * hd, cy + dy * hw - ny * hd),
        (cx + dx * hw + nx * hd, cy + dy * hw + ny * hd),
        (cx - dx * hw + nx * hd, cy - dy * hw + ny * hd),
    ]
    if (dx * ny - dy * nx) < 0.0:
        corners_2d.reverse()
    v_bot = [bm.verts.new((x, y, cz - hh)) for x, y in corners_2d]
    v_top = [bm.verts.new((x, y, cz + hh)) for x, y in corners_2d]
    for i in range(4):
        f = bm.faces.new((v_bot[i], v_bot[(i + 1) % 4], v_top[(i + 1) % 4], v_top[i]))
        f.material_index = mat_idx
        f.smooth = smooth
    f_t = bm.faces.new(v_top)
    f_t.material_index = mat_idx
    f_t.smooth = smooth
    f_b = bm.faces.new(list(reversed(v_bot)))
    f_b.material_index = mat_idx
    f_b.smooth = smooth


def load_kit_tree():
    """
    Loads the real Poly Haven `jacaranda_tree_LOD0` 3D mesh from `assets/montreal_kit.blend` and
    reshapes its lower 2.5m multi-stem banyan flare into a slender single-stem urban street sapling trunk (`r=0.085m`)
    while preserving 100% of the upper branching crown and leaf cards!
    """
    kit_path = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
    if not os.path.exists(kit_path):
        return None
    if "jacaranda_tree_LOD0" not in bpy.data.objects:
        with bpy.data.libraries.load(kit_path, link=False) as (data_from, data_to):
            if "jacaranda_tree_LOD0" in data_from.objects:
                data_to.objects = ["jacaranda_tree_LOD0"]
    tree_proto = bpy.data.objects.get("jacaranda_tree_LOD0")
    if not tree_proto:
        return None
    tree_proto.hide_render = True
    tree_proto.hide_viewport = True

    sapling_mesh = tree_proto.data.copy()
    sapling_mesh.name = "PolyHaven_UrbanSapling_Mesh"
    for v in sapling_mesh.vertices:
        x = v.co.x * 0.42
        y = v.co.y * 0.42
        z = v.co.z * 0.54
        if z < 2.65:
            # Taper multi-trunk flare below z=2.65m into a clean single urban sapling trunk (radius ~0.085m)
            blend = max(0.0, min(1.0, (z - 1.95) / 0.70))
            r = math.hypot(x, y)
            if r > 1e-4:
                target_r = min(r, 0.085) * (1.0 - blend) + r * blend
                x = x * (target_r / r)
                y = y * (target_r / r)
        v.co.x = x
        v.co.y = y
        v.co.z = z
    sapling_mesh.update()
    return sapling_mesh


def spawn_polyhaven_trees(sapling_mesh, tree_positions, streets_col, bm_street, mat_grate):
    if not sapling_mesh:
        return
    for idx, (tx, ty, scale_h) in enumerate(tree_positions):
        add_oriented_box(bm_street, (tx, ty, 0.185), (0.85, 0.52), (-0.52, 0.85), 1.35, 1.35, 0.03, mat_grate)
        inst = bpy.data.objects.new(f"PolyHaven_Tree_{idx:03d}", sapling_mesh)
        inst.location = (tx, ty, 0.16)
        inst.rotation_euler = (0.0, 0.0, (idx * 1.9) % (2.0 * math.pi))
        inst.scale = (scale_h, scale_h, scale_h)
        inst.hide_render = False
        inst.hide_viewport = False
        streets_col.objects.link(inst)


def build_palais_des_congres(bldg, owned_col, palette):
    """
    Builds the landmark Palais des Congrès de Montréal (`21258128`, 1001 Place Jean-Paul-Riopelle):
    - Camera 1 (`Place_Riopelle_Colored_Glass`): Alternating board-formed concrete piers & double-height recessed glass bays,
      sloped glass soffit truss gallery (`z=10.5..15.5m`), upper multicolored translucent glass curtain wall (`z=15.5..21.2m`)
      with vibrant Magenta, Cyan, Emerald, Yellow, Orange, and Violet glass panels & vertical fins, royal-blue geometric entrance
      canopy at `(-342, 8)`, and elevated pedestrian skybridge across Rue de la Gauchetière (`y~72m`).
    - Camera 2 (`Avenue_Viger_North_Entrance`): Polished black granite plinth (`0..0.85m`), recessed storefront curtain wall with
      3 continuous horizontal brushed-aluminum bars (`0.85..4.2m`), projecting board-formed concrete spandrel beam (`4.2..6.8m`),
      and forward-sloping glass atrium curtain wall (`6.8..19.8m`) with dense aluminum mullion grid & interior space-frame trusses.
    - Camera 3 (`Rue_SaintAntoine_South_Facade`): Integrated 3-story historic buff-brick & dark-stone Beaux-Arts heritage facade
      (with ornate dark pedimented parapet & circular medallion crest) flanked by horizontal-ribbed concrete wings, upper clerestory
      ribbon windows, and recessed `Quai de livraison` garage portal.
    - Camera 4 (`Rue_SaintUrbain_East_Side`): Recessed ground-floor `LA POPESSA` restaurant storefront with open corner colonnade
      and cylindrical concrete column under the cantilevered concrete mid-section and upper colorful translucent glass curtain wall.
    - Rooftop (`satellite_topdown.png`): Linear glass skylight atrium, landscaped rooftop garden lawn beds, and white square tensile pavilion.
    """
    pts = clean_polygon_pts(bldg["coords_xy"])
    mesh = bpy.data.meshes.new("Bldg_21258128_Palais_des_Congres_Mesh")
    obj = bpy.data.objects.new("Bldg_21258128_Palais_des_Congres", mesh)
    owned_col.objects.link(obj)

    mats = [
        palette["Mat_Palais_Concrete"],             # 0: Board-formed architectural concrete
        palette["Mat_Palais_Aluminum"],             # 1: Brushed silver-grey aluminum mullions
        palette["Mat_Palais_DarkSteel"],            # 2: Dark charcoal steel / heritage stone trim
        palette["Mat_MTL_Polished_Black_Granite"],  # 3: Polished black granite plinth
        palette["Mat_MTL_Window_Glass_Dark"],       # 4: Dark reflective storefront glass
        palette["Mat_Palais_Glass_Clear"],          # 5: Clear-blue atrium curtain wall glass
        palette["Mat_Palais_Glass_Magenta"],        # 6: Vibrant Magenta translucent glass
        palette["Mat_Palais_Glass_Cyan"],           # 7: Cyan translucent glass
        palette["Mat_Palais_Glass_Emerald"],        # 8: Emerald green translucent glass
        palette["Mat_Palais_Glass_Yellow"],         # 9: Yellow translucent glass
        palette["Mat_Palais_Glass_Orange"],         # 10: Orange translucent glass
        palette["Mat_Palais_Glass_Violet"],         # 11: Violet translucent glass
        palette["Mat_Heritage_BuffBrick"],          # 12: Historic buff brick (Rue Saint-Antoine facade)
        palette["Mat_RoyalBlue_Accent"],            # 13: Royal blue geometric entrance canopy
        palette["Mat_Reflective_White"],            # 14: White tensile roof pavilion / signage
        palette["Mat_Rooftop_Lawn"],                # 15: Rooftop garden grass beds
        palette["Mat_Interior_Warm"],               # 16: Warm interior ceiling lights / parallax
        palette["Mat_MTL_Slate_Roof_Dark"],         # 17: Dark roof membrane
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # Main Palais footprint (excluding the NW annex across Rue de la Gauchetière so the street is open under the skybridge!)
    main_pts = [p for i, p in enumerate(pts) if not (15 <= i <= 33)]
    main_pts = ensure_ccw(main_pts)
    total_h = 21.0

    # 1. Deeply Recessed Ground-Floor Dark Glass Core (`z=0..4.5m`, inset 3.2m so `LA POPESSA` & storefronts are open!)
    #    and Upper Architectural Concrete Core (`z=4.5..20.6m`, inset 1.2m with soffit ceiling)
    pts_core_ground = inset_polygon_2d(main_pts, 3.2)
    pts_core_upper = inset_polygon_2d(main_pts, 1.2)
    add_prism_to_bm(bm, pts_core_ground, 0.0, 4.5, 4, 0, 2)
    add_prism_to_bm(bm, pts_core_upper, 4.5, total_h - 0.4, 0, 17, 0)

    # 2. West Annex across Rue de la Gauchetière + Elevated Pedestrian Skybridge (visible in Cam 1!)
    annex_pts = ensure_ccw(pts[16:34])
    if len(annex_pts) >= 3:
        add_prism_to_bm(bm, annex_pts, 0.0, 18.5, 0, 17, 2)
    sb_dir = (0.980, 0.198)
    sb_norm = (0.198, -0.980)
    add_oriented_box(bm, (-325.5, 70.5, 5.25), sb_dir, sb_norm, 29.0, 6.4, 0.55, 2)
    add_oriented_box(bm, (-325.5, 70.5, 8.10), sb_dir, sb_norm, 29.0, 5.8, 5.10, 5)
    add_oriented_box(bm, (-325.5, 70.5, 5.80), sb_dir, sb_norm, 29.0, 6.5, 0.45, 6)
    # Warm underpass ceiling lights under the skybridge (visible down the street in Cam 1!)
    for ul_i in (-3, -1, 1, 3):
        ux = -325.5 + sb_dir[0] * (ul_i * 2.8)
        uy = 70.5 + sb_dir[1] * (ul_i * 2.8)
        add_oriented_box(bm, (ux, uy, 4.92), sb_dir, sb_norm, 1.4, 1.8, 0.15, 16)
    for sb_k in range(-6, 7):
        sx = -325.5 + sb_dir[0] * (sb_k * 2.0)
        sy = 70.5 + sb_dir[1] * (sb_k * 2.0)
        add_oriented_box(bm, (sx, sy, 8.0), sb_dir, sb_norm, 0.14, 6.6, 5.6, 1)
    ret_cyl = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=24, radius1=2.6, radius2=2.6, depth=5.4, matrix=Matrix.Translation((-334.5, 66.5, 2.7)))
    for v in ret_cyl["verts"]:
        for f in v.link_faces:
            f.material_index = 0
            f.smooth = True

    # 3. Iterate around Main Palais Edges to build camera-specific architectural facades
    color_cycle = [6, 7, 8, 9, 10, 11]
    n_m = len(main_pts)
    for i in range(n_m):
        p1 = Vector(main_pts[i])
        p2 = Vector(main_pts[(i + 1) % n_m])
        ev = p2 - p1
        elen = ev.length
        if elen < 2.5:
            continue
        d_xy = (ev.x / elen, ev.y / elen)
        n_xy = (d_xy[1], -d_xy[0])
        mid = (p1 + p2) * 0.5

        # CASE A: West Facade along Place Jean-Paul-Riopelle (Cam 1: `Place_Riopelle_Colored_Glass`)
        if mid.x < -305.0 and -60.0 < mid.y < 72.0:
            nbays = max(2, int(round(elen / 6.2)))
            bw = elen / nbays
            for b_i in range(nbays):
                t0 = (b_i + 0.5) / nbays
                bx = p1.x + ev.x * t0
                by = p1.y + ev.y * t0
                c_mat = color_cycle[(i + b_i) % len(color_cycle)]

                # Alternating board-formed concrete piers & double-height recessed glass bays (z=0..11.2m)
                if b_i % 2 == 0:
                    add_oriented_box(bm, (bx - n_xy[0] * 0.20, by - n_xy[1] * 0.20, 5.6), d_xy, n_xy, bw * 0.90, 0.90, 11.2, 0)
                    # Subtle vertical formwork joint lines on concrete pier
                    for j_k in (-0.28, 0.28):
                        add_oriented_box(bm, (bx + d_xy[0] * (bw * j_k) + n_xy[0] * 0.25, by + d_xy[1] * (bw * j_k) + n_xy[1] * 0.25, 5.6), d_xy, n_xy, 0.05, 0.06, 11.0, 2)
                else:
                    add_oriented_box(bm, (bx - n_xy[0] * 0.45, by - n_xy[1] * 0.45, 0.85), d_xy, n_xy, bw * 0.96, 0.45, 1.7, 1)
                    add_oriented_box(bm, (bx - n_xy[0] * 0.55, by - n_xy[1] * 0.55, 6.3), d_xy, n_xy, bw * 0.96, 0.30, 9.5, 5)
                    add_oriented_box(bm, (bx - n_xy[0] * 0.95, by - n_xy[1] * 0.95, 6.3), d_xy, n_xy, bw * 0.88, 0.20, 8.8, 16)
                    for m_c in (-1.5, -0.5, 0.5, 1.5):
                        mx = bx + d_xy[0] * (m_c * bw * 0.24) - n_xy[0] * 0.38
                        my = by + d_xy[1] * (m_c * bw * 0.24) - n_xy[1] * 0.38
                        add_oriented_box(bm, (mx, my, 5.6), d_xy, n_xy, 0.09, 0.32, 11.2, 1)
                    for z_m in (1.7, 4.2, 6.8, 9.4):
                        add_oriented_box(bm, (bx - n_xy[0] * 0.38, by - n_xy[1] * 0.38, z_m), d_xy, n_xy, bw * 0.96, 0.30, 0.10, 1)

                # Smooth Inclined Cantilevered Glass Soffit & Upper Curtain Wall (z=11.2m sloping out to +3.3m at z=16.2m, then up to z=21.2m)
                # Build true sloped quad prism for the inclined glass soffit (eliminating horizontal steps!)
                hw_b = bw * 0.495
                p_bl = (bx - d_xy[0] * hw_b, by - d_xy[1] * hw_b)
                p_br = (bx + d_xy[0] * hw_b, by + d_xy[1] * hw_b)
                v_s0 = bm.verts.new((p_bl[0] + n_xy[0] * 0.25, p_bl[1] + n_xy[1] * 0.25, 11.2))
                v_s1 = bm.verts.new((p_br[0] + n_xy[0] * 0.25, p_br[1] + n_xy[1] * 0.25, 11.2))
                v_s2 = bm.verts.new((p_br[0] + n_xy[0] * 3.25, p_br[1] + n_xy[1] * 3.25, 15.8))
                v_s3 = bm.verts.new((p_bl[0] + n_xy[0] * 3.25, p_bl[1] + n_xy[1] * 3.25, 15.8))
                f_slop = bm.faces.new((v_s0, v_s1, v_s2, v_s3))
                f_slop.material_index = 5
                # Sloped aluminum rafters & horizontal purlins on the inclined soffit + glowing interior ceiling lights
                for r_m in (-1.5, -0.5, 0.5, 1.5):
                    rx0 = bx + d_xy[0] * (r_m * bw * 0.24) + n_xy[0] * 1.75
                    ry0 = by + d_xy[1] * (r_m * bw * 0.24) + n_xy[1] * 1.75
                    add_oriented_box(bm, (rx0, ry0, 13.5), d_xy, n_xy, 0.11, 3.1, 4.5, 1)
                for p_s in (0.25, 0.50, 0.75, 1.0):
                    add_oriented_box(bm, (bx + n_xy[0] * (0.25 + p_s * 3.0), by + n_xy[1] * (0.25 + p_s * 3.0), 11.2 + p_s * 4.6), d_xy, n_xy, bw * 0.99, 0.18, 0.14, 1)
                add_oriented_box(bm, (bx + n_xy[0] * 1.6, by + n_xy[1] * 1.6, 14.8), d_xy, n_xy, bw * 0.72, 1.4, 0.25, 16)

                # Upper Vertical Curtain Wall (z=15.8m to 21.2m at +3.25m overhang) with reflective sky-blue glass & colored fins
                ux = bx + n_xy[0] * 3.25
                uy = by + n_xy[1] * 3.25
                add_oriented_box(bm, (ux, uy, 18.5), d_xy, n_xy, bw * 0.99, 0.24, 5.4, 5)
                for sub_i in range(4):
                    sc_mat = color_cycle[(i + b_i * 4 + sub_i) % len(color_cycle)]
                    uo = (sub_i - 1.5) * (bw * 0.24)
                    px = ux + d_xy[0] * uo
                    py = uy + d_xy[1] * uo
                    add_oriented_box(bm, (px - n_xy[0] * 0.22, py - n_xy[1] * 0.22, 18.5), d_xy, n_xy, bw * 0.22, 0.12, 5.2, sc_mat)
                    add_oriented_box(bm, (px + n_xy[0] * 0.14, py + n_xy[1] * 0.14, 18.5), d_xy, n_xy, 0.09, 0.26, 5.4, 1)
                for z_u in (15.8, 17.6, 19.4, 21.2):
                    add_oriented_box(bm, (ux, uy, z_u), d_xy, n_xy, bw * 1.0, 0.36, 0.14, 1)

        # CASE B: Avenue Viger North/NW Facade (Cam 2: `Avenue_Viger_North_Entrance`)
        elif mid.y > 95.0 and mid.x < -215.0:
            nbays = max(2, int(round(elen / 2.8)))
            bw = elen / nbays
            # 1. Polished Black Granite Plinth (z=0..0.85m)
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.25, mid.y - n_xy[1] * 0.25, 0.425), d_xy, n_xy, elen, 0.55, 0.85, 3)
            # 2. Deeply Recessed Dark Storefront Glass (z=0.85..4.2m) + 3 prominent horizontal brushed-aluminum bars
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.78, mid.y - n_xy[1] * 0.78, 2.52), d_xy, n_xy, elen, 0.28, 3.35, 4)
            for z_bar in (0.92, 1.68, 2.46, 3.24):
                add_oriented_box(bm, (mid.x - n_xy[0] * 0.52, mid.y - n_xy[1] * 0.52, z_bar), d_xy, n_xy, elen, 0.26, 0.11, 1)
            # 3. Projecting Precast Concrete Spandrel Beam (z=4.2..6.8m) with deep dark soffit (`0.95m` overhang) & vertical panel joints
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.25, mid.y - n_xy[1] * 0.25, 4.18), d_xy, n_xy, elen, 1.15, 0.12, 2)
            add_oriented_box(bm, (mid.x + n_xy[0] * 0.22, mid.y + n_xy[1] * 0.22, 5.52), d_xy, n_xy, elen, 0.95, 2.58, 0)
            add_oriented_box(bm, (mid.x + n_xy[0] * 0.28, mid.y + n_xy[1] * 0.28, 6.86), d_xy, n_xy, elen, 1.08, 0.16, 1)
            for pj in range(1, max(2, int(elen / 5.6))):
                jt = pj / max(2, int(elen / 5.6))
                jx = p1.x + ev.x * jt + n_xy[0] * 0.68
                jy = p1.y + ev.y * jt + n_xy[1] * 0.68
                add_oriented_box(bm, (jx, jy, 5.52), d_xy, n_xy, 0.05, 0.08, 2.58, 2)
            # 4. Forward-Sloping Upper Glass Curtain Wall (z=6.8..19.8m) with visible interior trusses, floor slabs & warm ceiling lights!
            for r_k in range(6):
                z_row = 7.9 + r_k * 2.0
                out_shift = 0.35 + r_k * 0.25
                rx = mid.x + n_xy[0] * out_shift
                ry = mid.y + n_xy[1] * out_shift
                # Exterior reflective glass pane
                add_oriented_box(bm, (rx, ry, z_row), d_xy, n_xy, elen, 0.18, 1.98, 5)
                # Double-line horizontal aluminum mullion
                add_oriented_box(bm, (rx + n_xy[0] * 0.14, ry + n_xy[1] * 0.14, z_row + 1.0), d_xy, n_xy, elen, 0.24, 0.13, 1)
                # Visible interior concrete ceiling slab + glowing warm ceiling light strips right behind the glass (`-0.22m`)!
                add_oriented_box(bm, (rx - n_xy[0] * 0.32, ry - n_xy[1] * 0.32, z_row + 0.85), d_xy, n_xy, elen * 0.98, 0.45, 0.22, 0)
                add_oriented_box(bm, (rx - n_xy[0] * 0.22, ry - n_xy[1] * 0.22, z_row + 0.68), d_xy, n_xy, elen * 0.92, 0.28, 0.18, 16)
            for b_i in range(nbays + 1):
                tp = b_i / nbays
                mx = p1.x + ev.x * tp
                my = p1.y + ev.y * tp
                add_oriented_box(bm, (mx - n_xy[0] * 0.58, my - n_xy[1] * 0.58, 2.52), d_xy, n_xy, 0.10, 0.25, 3.35, 2)
                for r_k in range(6):
                    z_row = 7.9 + r_k * 2.0
                    out_shift = 0.48 + r_k * 0.25
                    add_oriented_box(bm, (mx + n_xy[0] * out_shift, my + n_xy[1] * out_shift, z_row), d_xy, n_xy, 0.12, 0.28, 2.05, 1)
                    # Interior vertical steel truss post visible behind each mullion
                    add_oriented_box(bm, (mx + n_xy[0] * (out_shift - 0.35), my + n_xy[1] * (out_shift - 0.35), z_row), d_xy, n_xy, 0.18, 0.22, 2.0, 2)

        # CASE C: East Corner along Rue Saint-Urbain (Cam 4: `Rue_SaintUrbain_East_Side`)
        elif mid.x > -190.0 and mid.y > 40.0:
            nbays = max(2, int(round(elen / 2.6)))
            bw = elen / nbays
            # 1. Ground-floor deeply recessed `LA POPESSA` dark-glass restaurant storefront (z=0..4.5m, inset 1.85m!)
            add_oriented_box(bm, (mid.x - n_xy[0] * 1.85, mid.y - n_xy[1] * 1.85, 0.35), d_xy, n_xy, elen * 0.98, 0.35, 0.70, 3)
            add_oriented_box(bm, (mid.x - n_xy[0] * 1.88, mid.y - n_xy[1] * 1.88, 2.45), d_xy, n_xy, elen * 0.98, 0.25, 4.10, 4)
            add_oriented_box(bm, (mid.x - n_xy[0] * 2.35, mid.y - n_xy[1] * 2.35, 2.25), d_xy, n_xy, elen * 0.92, 0.20, 3.80, 16)
            # Horizontal silver transom bar at z=3.2m + 3D white `LA POPESSA` block letters at z=3.55m
            add_oriented_box(bm, (mid.x - n_xy[0] * 1.72, mid.y - n_xy[1] * 1.72, 3.15), d_xy, n_xy, elen * 0.98, 0.18, 0.10, 1)
            for l_i in range(min(9, max(3, int(elen / 1.1)))):
                lt = 0.18 + 0.64 * (l_i / max(1, min(9, max(3, int(elen / 1.1))) - 1))
                lx = p1.x + ev.x * lt - n_xy[0] * 1.70
                ly = p1.y + ev.y * lt - n_xy[1] * 1.70
                add_oriented_box(bm, (lx, ly, 3.58), d_xy, n_xy, 0.42, 0.12, 0.48, 14)
            for b_i in range(nbays + 1):
                tp = b_i / nbays
                mx = p1.x + ev.x * tp - n_xy[0] * 1.72
                my = p1.y + ev.y * tp - n_xy[1] * 1.72
                add_oriented_box(bm, (mx, my, 2.25), d_xy, n_xy, 0.09, 0.22, 4.5, 1)
            # 2. Cantilevered Horizontal-Course Limestone/Concrete Middle Band (z=4.5..12.6m) overhanging the colonnade
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.85, mid.y - n_xy[1] * 0.85, 4.55), d_xy, n_xy, elen, 2.10, 0.18, 1)
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.25, mid.y - n_xy[1] * 0.25, 8.55), d_xy, n_xy, elen, 0.90, 8.1, 0)
            # 3. Upper Vibrant Multicolored Translucent Glass Curtain Wall (`Transparence`, z=12.6..21.5m)
            for b_i in range(nbays):
                tc = (b_i + 0.5) / nbays
                bx = p1.x + ev.x * tc
                by = p1.y + ev.y * tc
                c_mat = [8, 7, 6, 9, 10, 11][(i + b_i) % 6]
                add_oriented_box(bm, (bx - n_xy[0] * 0.12, by - n_xy[1] * 0.12, 17.05), d_xy, n_xy, bw * 0.95, 0.28, 8.9, c_mat)
                add_oriented_box(bm, (bx + n_xy[0] * 0.06, by + n_xy[1] * 0.06, 17.05), d_xy, n_xy, 0.09, 0.32, 8.9, 1)
            for z_h in (12.6, 15.5, 18.5, 21.4):
                add_oriented_box(bm, (mid.x + n_xy[0] * 0.06, mid.y + n_xy[1] * 0.06, z_h), d_xy, n_xy, elen, 0.34, 0.14, 1)

        # CASE D: South Facade along Rue Saint-Antoine Ouest (Cam 3: `Rue_SaintAntoine_South_Facade`)
        else:
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.35, mid.y - n_xy[1] * 0.35, 6.8), d_xy, n_xy, elen, 0.90, 13.6, 0)
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.45, mid.y - n_xy[1] * 0.45, 15.6), d_xy, n_xy, elen, 0.50, 4.0, 5)
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.25, mid.y - n_xy[1] * 0.25, 17.8), d_xy, n_xy, elen, 0.75, 0.45, 1)
            nbays = max(2, int(round(elen / 3.8)))
            for b_i in range(nbays + 1):
                tp = b_i / nbays
                mx = p1.x + ev.x * tp - n_xy[0] * 0.30
                my = p1.y + ev.y * tp - n_xy[1] * 0.30
                add_oriented_box(bm, (mx, my, 15.6), d_xy, n_xy, 0.12, 0.35, 4.0, 1)

    # 4. Bespoke Royal-Blue Geometric Sculpture Banner & Recessed Entrance Portal at `(-341.5, 7.5)` (Cam 1 right foreground)
    c1_dir = (0.525, 0.851)
    c1_norm = (-0.851, 0.525)
    # Folded-plate royal-blue geometric diamond/triangle sculpture with crisp white diagonal truss lines
    add_oriented_box(bm, (-342.4, 8.2, 3.8), c1_dir, c1_norm, 3.8, 1.4, 3.8, 13)
    add_oriented_box(bm, (-342.4, 8.2, 3.8), c1_dir, c1_norm, 3.9, 1.5, 0.08, 14)
    add_oriented_box(bm, (-342.4, 8.2, 3.8), c1_dir, c1_norm, 0.08, 1.5, 3.9, 14)
    # Recessed dark-glass entrance lobby (`1001 Place Jean-Paul-Riopelle`) immediately to the right of the blue sculpture
    add_oriented_box(bm, (-336.5, -1.5, 5.1), c1_dir, c1_norm, 12.0, 2.2, 0.95, 0)
    add_oriented_box(bm, (-336.5, -1.5, 2.3), c1_dir, c1_norm, 11.5, 1.8, 4.5, 4)
    add_oriented_box(bm, (-336.5, -1.5, 2.3), c1_dir, c1_norm, 9.5, 1.4, 4.2, 11)

    # 5. Bespoke Integrated 3-Story Historic Yellow-Brick `Façade intégrée`, White Historic Townhouse & `Quais de livraison` Portal (Cam 3)
    sa_dir = (0.506, 0.862)
    sa_norm = (0.862, -0.506)
    hx, hy = -218.2, -15.2
    # A. 3-Story Yellow-Brick `Façade intégrée` (9.6m wide, centered on left-center of Cam 3)
    # Ground-floor dark stone frame + 3 wide recessed glass storefront bays with white interior mullions!
    add_oriented_box(bm, (hx + sa_norm[0] * 0.45, hy + sa_norm[1] * 0.45, 4.35), sa_dir, sa_norm, 9.8, 0.85, 0.55, 2)
    add_oriented_box(bm, (hx + sa_norm[0] * 0.25, hy + sa_norm[1] * 0.25, 2.15), sa_dir, sa_norm, 9.4, 0.45, 4.1, 4)
    add_oriented_box(bm, (hx - sa_norm[0] * 0.15, hy - sa_norm[1] * 0.15, 2.15), sa_dir, sa_norm, 9.0, 0.25, 3.8, 16)
    for sf_i in (-1, 0, 1):
        sfx = hx + sa_dir[0] * (sf_i * 2.9) + sa_norm[0] * 0.38
        sfy = hy + sa_dir[1] * (sf_i * 2.9) + sa_norm[1] * 0.38
        add_oriented_box(bm, (sfx, sfy, 2.15), sa_dir, sa_norm, 0.08, 0.35, 3.9, 14)
        add_oriented_box(bm, (sfx, sfy, 3.10), sa_dir, sa_norm, 2.6, 0.35, 0.08, 14)
    # 2nd & 3rd floor warm buff brick wall (z=4.5..12.4m) with paired recessed glass windows
    add_oriented_box(bm, (hx + sa_norm[0] * 0.32, hy + sa_norm[1] * 0.32, 8.45), sa_dir, sa_norm, 9.6, 0.65, 7.9, 12)
    for w_i in (-1, 0, 1):
        wx = hx + sa_dir[0] * (w_i * 2.9) + sa_norm[0] * 0.48
        wy = hy + sa_dir[1] * (w_i * 2.9) + sa_norm[1] * 0.48
        for z_w in (6.5, 10.1):
            add_oriented_box(bm, (wx, wy, z_w), sa_dir, sa_norm, 2.0, 0.45, 2.2, 4)
            add_oriented_box(bm, (wx, wy, z_w), sa_dir, sa_norm, 0.10, 0.52, 2.2, 1)
            add_oriented_box(bm, (wx, wy, z_w - 1.15), sa_dir, sa_norm, 2.2, 0.65, 0.18, 2)
    # 4 Full-height dark charcoal pilasters + ornate cornice + 4 turret finials + central circular medallion crest!
    add_oriented_box(bm, (hx + sa_norm[0] * 0.62, hy + sa_norm[1] * 0.62, 12.75), sa_dir, sa_norm, 10.2, 1.05, 0.85, 2)
    add_oriented_box(bm, (hx + sa_norm[0] * 0.55, hy + sa_norm[1] * 0.55, 13.85), sa_dir, sa_norm, 3.0, 0.85, 1.45, 2)
    add_oriented_box(bm, (hx + sa_norm[0] * 0.68, hy + sa_norm[1] * 0.68, 13.85), sa_dir, sa_norm, 1.45, 0.95, 1.45, 1)
    for p_k in (-1.5, -0.5, 0.5, 1.5):
        px = hx + sa_dir[0] * (p_k * 2.95) + sa_norm[0] * 0.52
        py = hy + sa_dir[1] * (p_k * 2.95) + sa_norm[1] * 0.52
        add_oriented_box(bm, (px, py, 7.1), sa_dir, sa_norm, 0.52, 0.78, 14.2, 2)

    # B. Adjacent 3-Story White Historic Townhouse (`wx_a, wy_a` immediately right of the buff-brick facade)
    wx_a = hx + sa_dir[0] * 6.8 + sa_norm[0] * 0.35
    wy_a = hy + sa_dir[1] * 6.8 + sa_norm[1] * 0.35
    add_oriented_box(bm, (wx_a, wy_a, 8.2), sa_dir, sa_norm, 3.8, 0.65, 7.6, 14)
    add_oriented_box(bm, (wx_a + sa_norm[0] * 0.15, wy_a + sa_norm[1] * 0.15, 2.15), sa_dir, sa_norm, 3.4, 0.45, 4.1, 4)
    add_oriented_box(bm, (wx_a + sa_norm[0] * 0.25, wy_a + sa_norm[1] * 0.25, 4.35), sa_dir, sa_norm, 3.9, 0.75, 0.42, 2)
    for z_wa in (6.5, 10.1):
        add_oriented_box(bm, (wx_a + sa_norm[0] * 0.22, wy_a + sa_norm[1] * 0.22, z_wa), sa_dir, sa_norm, 2.4, 0.45, 2.1, 4)
        add_oriented_box(bm, (wx_a + sa_norm[0] * 0.28, wy_a + sa_norm[1] * 0.28, z_wa - 1.1), sa_dir, sa_norm, 2.6, 0.58, 0.16, 1)
    add_oriented_box(bm, (wx_a + sa_norm[0] * 0.35, wy_a + sa_norm[1] * 0.35, 12.25), sa_dir, sa_norm, 4.0, 0.85, 0.65, 2)

    # C. Recessed `Quais de livraison` Loading Tunnel Portal on the right of Cam 3 (`(-205.8, 5.8)`)
    gx, gy = -205.8, 5.8
    add_oriented_box(bm, (gx - sa_norm[0] * 1.1, gy - sa_norm[1] * 1.1, 2.4), sa_dir, sa_norm, 7.6, 3.0, 4.8, 3)
    # 2 Orange construction barriers inside the dark tunnel portal + yellow traffic light on left pier
    for ob_s in (-1.6, 1.6):
        add_oriented_box(bm, (gx + sa_dir[0] * ob_s - sa_norm[0] * 0.5, gy + sa_dir[1] * ob_s - sa_norm[1] * 0.5, 0.55), sa_dir, sa_norm, 1.5, 0.35, 0.85, 10)
    add_oriented_box(bm, (gx - sa_dir[0] * 4.4 + sa_norm[0] * 0.65, gy - sa_dir[1] * 4.4 + sa_norm[1] * 0.65, 4.6), sa_dir, sa_norm, 0.38, 0.38, 0.95, 9)

    # 6. Round Concrete Corner Pillar at `LA POPESSA` East Colonnade (`(-151.8, 96.2)`, Cam 4)
    ret_p = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=24, radius1=0.42, radius2=0.42, depth=4.5, matrix=Matrix.Translation((-151.8, 96.2, 2.25)))
    for v in ret_p["verts"]:
        for f in v.link_faces:
            f.material_index = 0
            f.smooth = True

    # 7. Detailed Rooftop Matching `satellite_topdown.png` (`MTL-VM-0010_snapshot.png`)
    r_dir = (0.515, 0.857)
    r_norm = (-0.857, 0.515)
    # A. Long continuous dark-blue photovoltaic solar panel array along entire Western roof edge (`18m x 135m`)
    add_oriented_box(bm, (-338.0, 12.0, total_h + 0.45), r_dir, r_norm, 132.0, 13.5, 0.65, 4)
    for sp_k in range(-10, 11):
        spx = -338.0 + r_dir[0] * (sp_k * 6.2)
        spy = 12.0 + r_dir[1] * (sp_k * 6.2)
        add_oriented_box(bm, (spx, spy, total_h + 0.80), r_dir, r_norm, 0.18, 13.6, 0.12, 1)
    # B. Row of 8 stepped light-grey modular roof bays adjacent to the solar array
    for mb_k in range(-4, 4):
        mbx = -324.0 + r_dir[0] * (mb_k * 14.5)
        mby = 8.0 + r_dir[1] * (mb_k * 14.5)
        add_oriented_box(bm, (mbx, mby, total_h + 0.75), r_dir, r_norm, 12.8, 14.0, 1.3, 0)
        add_oriented_box(bm, (mbx, mby, total_h + 1.45), r_dir, r_norm, 4.2, 3.2, 0.6, 1)
    # C. White square rooftop garden pavilion (`Oasis`, `24m x 24m`) + curved green garden beds (`(-258, 92)`)
    add_oriented_box(bm, (-258.0, 92.0, total_h + 0.35), r_dir, r_norm, 56.0, 38.0, 0.45, 15)
    add_oriented_box(bm, (-262.0, 88.0, total_h + 1.85), r_dir, r_norm, 24.0, 24.0, 2.8, 14)
    # D. Structural expansion-joint grid lines & mechanical penthouses across southern exhibition hall roof
    for gj_i in (-2, -1, 0, 1, 2):
        gx_j = -265.0 + r_dir[0] * (gj_i * 22.0)
        gy_j = 5.0 + r_dir[1] * (gj_i * 22.0)
        add_oriented_box(bm, (gx_j, gy_j, total_h + 0.15), r_dir, r_norm, 0.35, 95.0, 0.22, 2)
        add_oriented_box(bm, (-265.0 - r_norm[0] * (gj_i * 18.0), 5.0 - r_norm[1] * (gj_i * 18.0), total_h + 0.15), r_dir, r_norm, 110.0, 0.35, 0.22, 2)
    for m_x, m_y in [(-285.0, 35.0), (-235.0, 55.0), (-265.0, -25.0), (-220.0, 20.0)]:
        add_oriented_box(bm, (m_x, m_y, total_h + 1.6), r_dir, r_norm, 13.0, 8.5, 3.2, 0)
        add_oriented_box(bm, (m_x, m_y, total_h + 3.3), r_dir, r_norm, 8.0, 5.0, 0.6, 2)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def build_chinatown_gate(bldg, col, palette):
    """Builds an authentic Montreal Chinatown Paifang Arch Gate with red columns, gold plaques, and upturned verdigris roofs."""
    pts = clean_polygon_pts(bldg["coords_xy"])
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    mesh = bpy.data.meshes.new(f"Bldg_{bldg['id']}_Gate_Mesh")
    obj = bpy.data.objects.new(f"Bldg_{bldg['id']}_{bldg.get('name', 'Gate')}", mesh)
    col.objects.link(obj)
    for m in [palette["Mat_Chinatown_Red"], palette["Mat_Chinatown_Gold"], palette["Mat_MTL_Verdigris_Copper"], palette["Mat_MTL_PierreGrise_Limestone"]]:
        obj.data.materials.append(m)
    bm = bmesh.new()
    u_dir = (0.85, -0.52)
    v_dir = (0.52, 0.85)
    for side in (-4.8, 4.8):
        px, py = cx + u_dir[0] * side, cy + u_dir[1] * side
        add_oriented_box(bm, (px, py, 0.6), u_dir, v_dir, 1.4, 1.4, 1.2, 3)
        add_oriented_box(bm, (px, py, 5.2), u_dir, v_dir, 0.9, 0.9, 8.8, 0)
    add_oriented_box(bm, (cx, cy, 8.2), u_dir, v_dir, 11.8, 1.2, 1.6, 1)
    add_oriented_box(bm, (cx, cy, 9.8), u_dir, v_dir, 13.5, 2.6, 1.2, 2)
    add_oriented_box(bm, (cx, cy, 11.2), u_dir, v_dir, 8.5, 2.2, 1.4, 2)
    bm.to_mesh(mesh)
    bm.free()


def build_context_or_owned_building(bldg, col, palette, cam_coords):
    """Builds a primary-owned or context-proxy building with recessed 0.45m windows, stone sills, cornices, and rooftop penthouse."""
    bid = bldg["id"]
    if bid == 21258128:
        return build_palais_des_congres(bldg, col, palette)
    if "Gate" in (bldg.get("name") or ""):
        return build_chinatown_gate(bldg, col, palette)

    pts = ensure_ccw(clean_polygon_pts(bldg["coords_xy"]))
    if len(pts) < 3:
        return None
    tags = bldg.get("tags", {})
    levels_str = tags.get("building:levels")
    try:
        levels = int(float(levels_str)) if levels_str else 4
    except ValueError:
        levels = 4
    if bid == 48808783:
        levels = 24
    elif bid == 116711271:
        levels = 12
    total_h = max(8.5, levels * 3.6)

    mesh = bpy.data.meshes.new(f"Bldg_{bid}_Mesh")
    obj = bpy.data.objects.new(f"Bldg_{bid}", mesh)
    col.objects.link(obj)

    use_brick = (bid % 3 == 0) and levels <= 6
    mat_wall = palette["Mat_MTL_Heritage_RedBrick"] if use_brick else palette["Mat_MTL_WarmBuff_Limestone"]
    mat_trim = palette["Mat_MTL_PierreGrise_Limestone"]
    mat_glass = palette["Mat_MTL_Window_Glass_Dark"]
    mat_roof = palette["Mat_MTL_Slate_Roof_Dark"]
    mat_frame = palette["Mat_Palais_DarkSteel"]
    for m in [mat_wall, mat_trim, mat_glass, mat_roof, mat_frame]:
        obj.data.materials.append(m)

    bm = bmesh.new()
    cx, cy = bldg["centroid_xy"]
    min_cam_dist = min(math.hypot(cx - cam[0], cy - cam[1]) for cam in cam_coords)

    pts_glass = inset_polygon_2d(pts, 0.45)
    add_prism_to_bm(bm, pts_glass, 0.0, total_h - 0.3, 2, 3)
    # Plinth & Cornice
    add_prism_to_bm(bm, inset_polygon_2d(pts, -0.06), -0.3, 1.1, 1, 1)
    add_prism_to_bm(bm, inset_polygon_2d(pts, -0.30), total_h - 0.7, total_h + 0.25, 1, 3, 1)

    # Recessed window bays (full detail within 185m of cameras, streamlined piers beyond 185m for fast build)
    step_f = 1 if min_cam_dist < 185.0 else 2
    n = len(pts)
    for i in range(n):
        p1 = Vector(pts[i])
        p2 = Vector(pts[(i + 1) % n])
        ev = p2 - p1
        elen = ev.length
        if elen < 2.8:
            mid = (p1 + p2) * 0.5
            d_xy = (ev.x / max(0.1, elen), ev.y / max(0.1, elen))
            n_xy = (d_xy[1], -d_xy[0])
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.22, mid.y - n_xy[1] * 0.22, total_h * 0.5), d_xy, n_xy, elen, 0.48, total_h, 0)
            continue
        d_xy = (ev.x / elen, ev.y / elen)
        n_xy = (d_xy[1], -d_xy[0])
        ncols = max(2, int(round(elen / 4.2)))
        cw = elen / ncols
        for c_i in range(0, ncols + 1, step_f):
            tp = min(1.0, c_i / ncols)
            px = p1.x + ev.x * tp - n_xy[0] * 0.22
            py = p1.y + ev.y * tp - n_xy[1] * 0.22
            add_oriented_box(bm, (px, py, total_h * 0.5), d_xy, n_xy, cw * 0.36 * step_f, 0.52, total_h, 0)
        for fl in range(1, levels, step_f):
            zf = fl * 3.6
            mid = (p1 + p2) * 0.5
            add_oriented_box(bm, (mid.x - n_xy[0] * 0.22, mid.y - n_xy[1] * 0.22, zf), d_xy, n_xy, elen, 0.50, 0.95, 0)
            add_oriented_box(bm, (mid.x + n_xy[0] * 0.06, mid.y + n_xy[1] * 0.06, zf + 0.52), d_xy, n_xy, elen, 0.16, 0.14, 1)

    # Rooftop mechanical penthouse
    pts_safe = inset_polygon_2d(pts, 3.8)
    if len(pts_safe) >= 3:
        sx = [p[0] for p in pts_safe]
        sy = [p[1] for p in pts_safe]
        if (max(sx) - min(sx)) > 5.0 and (max(sy) - min(sy)) > 5.0:
            add_oriented_box(bm, (cx, cy, total_h + 1.4), (0.85, 0.52), (-0.52, 0.85), 5.2, 4.2, 2.6, 1)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def add_sculpted_tire(bm, tx, ty, tz, d_xy, n_xy, radius, width, mat_tire, mat_rim):
    """Creates a 16-segment cylindrical rubber tire with metallic alloy hubcap oriented along the vehicle axle."""
    angle_z = math.atan2(n_xy[1], n_xy[0])
    rot_m = Matrix.Rotation(angle_z, 4, 'Z') @ Matrix.Rotation(math.pi * 0.5, 4, 'Y')
    mat_t = Matrix.Translation((tx, ty, tz)) @ rot_m
    ret_w = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=16, radius1=radius, radius2=radius, depth=width, matrix=mat_t)
    for v in ret_w["verts"]:
        for f in v.link_faces:
            f.material_index = mat_tire
            f.smooth = True
    ret_r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=12, radius1=radius * 0.62, radius2=radius * 0.62, depth=width + 0.02, matrix=mat_t)
    for v in ret_r["verts"]:
        for f in v.link_faces:
            f.material_index = mat_rim
            f.smooth = True


def add_sculpted_vehicle(bm, cx, cy, heading_deg, vtype, mat_body, mat_glass, mat_tire, mat_rim, mat_light):
    """Builds a sculpted 3D automobile or commercial delivery truck with sloped windshield, tapered hood, cabin glass, and round wheels."""
    rad = math.radians(heading_deg)
    dx, dy = math.sin(rad), math.cos(rad)
    nx, ny = dy, -dx
    d_xy = (dx, dy)
    n_xy = (nx, ny)

    def pt3(u_l, v_w, z_h):
        return bm.verts.new((cx + dx * u_l + nx * v_w, cy + dy * u_l + ny * v_w, z_h))

    if vtype == "truck":
        # Sculpted White Commercial Delivery Box Truck (sloped cab hood, raked windshield, side mirrors, rear box body, round tires)
        add_oriented_box(bm, (cx - dx * 1.4, cy - dy * 1.4, 2.05), d_xy, n_xy, 5.2, 2.38, 2.85, mat_body)
        add_oriented_box(bm, (cx + dx * 1.9, cy + dy * 1.9, 1.45), d_xy, n_xy, 1.45, 2.15, 1.85, mat_body)
        add_oriented_box(bm, (cx + dx * 2.1, cy + dy * 2.1, 1.75), d_xy, n_xy, 1.15, 2.18, 0.82, mat_glass)
        add_oriented_box(bm, (cx + dx * 3.05, cy + dy * 3.05, 0.92), d_xy, n_xy, 1.15, 2.08, 0.85, mat_body)
        add_oriented_box(bm, (cx + dx * 3.62, cy + dy * 3.62, 0.88), d_xy, n_xy, 0.08, 1.35, 0.48, mat_tire)
        for s_y in (-0.82, 0.82):
            add_oriented_box(bm, (cx + dx * 3.62 + nx * s_y, cy + dy * 3.62 + ny * s_y, 0.82), d_xy, n_xy, 0.08, 0.32, 0.22, mat_light)
        for wx, wy in [(-2.6, -1.08), (-2.6, 1.08), (2.5, -1.04), (2.5, 1.04)]:
            add_sculpted_tire(bm, cx + dx * wx + nx * wy, cy + dy * wx + ny * wy, 0.44, d_xy, n_xy, 0.44, 0.28, mat_tire, mat_rim)
    else:
        L = 4.65 if vtype == "suv" else 4.45
        W = 1.90 if vtype == "suv" else 1.82
        z_b = 0.28
        z_belt = 0.98 if vtype == "suv" else 0.86
        z_roof = 1.62 if vtype == "suv" else 1.42
        hw = W * 0.5
        hw_r = W * 0.41

        # Lower body hull with tapered front hood & rear bumper
        add_oriented_box(bm, (cx, cy, (z_b + z_belt) * 0.5), d_xy, n_xy, L, W, z_belt - z_b, mat_body)
        # Sculpted 8-vertex aerodynamic greenhouse cabin with raked front windshield and sloped rear window!
        u_ws_bot = L * 0.20
        u_ws_top = L * 0.04
        u_rw_top = -L * (0.38 if vtype == "suv" else 0.28)
        u_rw_bot = -L * (0.46 if vtype == "suv" else 0.42)

        b_fl = pt3(u_ws_bot, -hw * 0.94, z_belt)
        b_fr = pt3(u_ws_bot, hw * 0.94, z_belt)
        b_rr = pt3(u_rw_bot, hw * 0.94, z_belt)
        b_rl = pt3(u_rw_bot, -hw * 0.94, z_belt)
        t_fl = pt3(u_ws_top, -hw_r, z_roof)
        t_fr = pt3(u_ws_top, hw_r, z_roof)
        t_rr = pt3(u_rw_top, hw_r, z_roof)
        t_rl = pt3(u_rw_top, -hw_r, z_roof)

        for quad, m_idx in [
            ((b_fl, b_fr, t_fr, t_fl), mat_glass),  # Sloped front windshield
            ((b_fr, b_rr, t_rr, t_fr), mat_glass),  # Right side windows
            ((b_rr, b_rl, t_rl, t_rr), mat_glass),  # Sloped rear window
            ((b_rl, b_fl, t_fl, t_rl), mat_glass),  # Left side windows
            ((t_fl, t_fr, t_rr, t_rl), mat_body),   # Roof panel
        ]:
            f = bm.faces.new(quad)
            f.material_index = m_idx
            f.smooth = True

        # Front grille, headlights, and rear taillights
        add_oriented_box(bm, (cx + dx * (L * 0.50), cy + dy * (L * 0.50), z_b + 0.30), d_xy, n_xy, 0.08, W * 0.52, 0.26, mat_tire)
        for side_s in (-0.36, 0.36):
            add_oriented_box(bm, (cx + dx * (L * 0.50) + nx * (W * side_s), cy + dy * (L * 0.50) + ny * (W * side_s), z_b + 0.38), d_xy, n_xy, 0.08, 0.28, 0.16, mat_rim)
            add_oriented_box(bm, (cx - dx * (L * 0.50) + nx * (W * side_s), cy - dy * (L * 0.50) + ny * (W * side_s), z_b + 0.42), d_xy, n_xy, 0.08, 0.30, 0.16, mat_light)

        for wx, wy in [(-L * 0.31, -hw * 0.92), (-L * 0.31, hw * 0.92), (L * 0.31, -hw * 0.92), (L * 0.31, hw * 0.92)]:
            add_sculpted_tire(bm, cx + dx * wx + nx * wy, cy + dy * wx + ny * wy, 0.34, d_xy, n_xy, 0.34, 0.22, mat_tire, mat_rim)


def add_bixi_bicycle(bm, bx, by, sa_dir, sa_norm, mat_tire, mat_frame, mat_rim):
    """Builds a 3D BIXI bicycle silhouette with front & rear circular wheels, angled frame tubes, saddle seat, and handlebars."""
    # Bike extends perpendicular to dock line (`-sa_norm`)
    b_dir = (-sa_norm[0], -sa_norm[1])
    b_norm = (sa_dir[0], sa_dir[1])
    for w_off in (0.28, 1.25):
        wx = bx + b_dir[0] * w_off
        wy = by + b_dir[1] * w_off
        add_sculpted_tire(bm, wx, wy, 0.42, b_dir, b_norm, 0.31, 0.05, mat_tire, mat_rim)
    # Angled step-through BIXI frame tube, seat post + black saddle, and handlebar stem + grips
    add_oriented_box(bm, (bx + b_dir[0] * 0.76, by + b_dir[1] * 0.76, 0.58), b_dir, b_norm, 0.92, 0.06, 0.12, mat_frame)
    add_oriented_box(bm, (bx + b_dir[0] * 0.38, by + b_dir[1] * 0.38, 0.78), b_dir, b_norm, 0.06, 0.06, 0.58, mat_rim)
    add_oriented_box(bm, (bx + b_dir[0] * 0.38, by + b_dir[1] * 0.38, 1.06), b_dir, b_norm, 0.12, 0.56, 0.05, mat_tire)
    add_oriented_box(bm, (bx + b_dir[0] * 0.98, by + b_dir[1] * 0.98, 0.76), b_dir, b_norm, 0.06, 0.06, 0.45, mat_tire)
    add_oriented_box(bm, (bx + b_dir[0] * 1.02, by + b_dir[1] * 1.02, 0.96), b_dir, b_norm, 0.24, 0.18, 0.07, mat_tire)


def create_ground_and_streetscape(dossier, streets_col, palette):
    mesh = bpy.data.meshes.new("Block_MTL_VM_0010_Streetscape_Mesh")
    obj = bpy.data.objects.new("Block_MTL_VM_0010_Streetscape", mesh)
    streets_col.objects.link(obj)

    mats = [
        palette["Mat_MTL_Street_Asphalt"],          # 0: Asphalt roadbed
        palette["Mat_MTL_Plaza_Light_Granite"],     # 1: Sidewalk / Place Riopelle pavers
        palette["Mat_MTL_Plaza_Charcoal_Granite"],  # 2: Granite curbs & dark SUV/sedan body
        palette["Mat_Palais_DarkSteel"],            # 3: Dark steel poles / BIXI docks / tires
        palette["Mat_Palais_Aluminum"],             # 4: Silver aluminum / alloy rims / sedan body
        palette["Mat_RoyalBlue_Accent"],            # 5: Royal blue cylinders & bike-lane bollards
        palette["Mat_Reflective_White"],            # 6: White road stencils / Jersey barriers / box truck
        palette["Mat_Traffic_Orange"],              # 7: Orange construction sign / traffic signals / taillights
        palette["Mat_MTL_Window_Glass_Dark"],       # 8: Vehicle glass / solar panel
        palette["Mat_Rooftop_Lawn"],                # 9: Planter island shrubs
    ]
    for m in mats:
        obj.data.materials.append(m)

    bm = bmesh.new()

    # 1. Asphalt Roadbed covering entire block & context
    add_oriented_box(bm, (-310.0, 220.0, -0.15), (1.0, 0.0), (0.0, 1.0), 680.0, 820.0, 0.30, 0)

    # 2. Raised Paver Sidewalks & Granite Curbs around Palais des Congrès & nearby buildings
    for b in dossier["osm_features"]["buildings"]:
        cx, cy = b["centroid_xy"]
        if cy < 220.0:
            pts = ensure_ccw(clean_polygon_pts(b["coords_xy"]))
            if b["id"] == 21258128:
                pts = ensure_ccw([p for idx, p in enumerate(pts) if not (15 <= idx <= 33)])
            if len(pts) >= 3:
                sw_off = -4.2 if b["id"] == 21258128 else -3.0
                add_prism_to_bm(bm, inset_polygon_2d(pts, sw_off - 0.25), -0.02, 0.16, 2, 2)
                add_prism_to_bm(bm, inset_polygon_2d(pts, sw_off), 0.0, 0.18, 1, 1)

    # 3. Place Jean-Paul-Riopelle Pedestrian Plaza & Low Concrete Planter Walls (`(-372, 28)`)
    p_dir = (0.525, 0.851)
    p_norm = (-0.851, 0.525)
    add_oriented_box(bm, (-374.0, 32.0, 0.09), p_dir, p_norm, 68.0, 22.0, 0.18, 1)
    add_oriented_box(bm, (-363.2, 26.5, 0.08), p_dir, p_norm, 68.0, 0.35, 0.16, 2)
    add_oriented_box(bm, (-367.5, 31.0, 0.38), p_dir, p_norm, 22.0, 0.45, 0.42, 1)

    # 4. Camera 1 (`Place_Riopelle_Colored_Glass`) Street Props: Curved Luminaire Mast, Bike Stencil, Bollards, Sculpted Sedan
    # Tapered octagonal traffic/streetlight mast at `(-355.2, 25.4)` with smooth 8-segment curved luminaire arm!
    ret_pole = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=12, radius1=0.18, radius2=0.13, depth=7.5, matrix=Matrix.Translation((-355.2, 25.4, 3.75)))
    for v in ret_pole["verts"]:
        for f in v.link_faces:
            f.material_index = 3
            f.smooth = True
    for arm_s in range(8):
        t_a = (arm_s + 0.5) / 8.0
        reach = t_a * 4.2
        z_arm = 5.4 + math.sin(t_a * math.pi * 0.55) * 1.55
        ax = -355.2 - p_norm[0] * reach
        ay = 25.4 - p_norm[1] * reach
        add_oriented_box(bm, (ax, ay, z_arm), p_dir, p_norm, 0.09, 0.58, 0.09, 3)
    # Luminaire head at tip of curved arm + traffic signal box & white sign plate
    add_oriented_box(bm, (-355.2 - p_norm[0] * 4.35, 25.4 - p_norm[1] * 4.35, 6.82), p_dir, p_norm, 0.35, 0.65, 0.12, 3)
    add_oriented_box(bm, (-354.9, 25.2, 2.55), p_dir, p_norm, 0.34, 0.34, 0.78, 3)
    add_oriented_box(bm, (-354.85, 25.15, 2.72), p_dir, p_norm, 0.22, 0.36, 0.22, 7)
    add_oriented_box(bm, (-354.8, 25.1, 3.95), p_dir, p_norm, 0.08, 0.78, 0.68, 6)
    # White painted bicycle symbol & chevron stencil in foreground bike lane (`(-355.6, 20.8)`)
    st_x, st_y = -355.4, 21.0
    for w_s in (-0.45, 0.45):
        ret_bw = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=16, radius1=0.32, radius2=0.32, depth=0.02, matrix=Matrix.Translation((st_x + p_dir[0] * w_s, st_y + p_dir[1] * w_s, 0.015)))
        for v in ret_bw["verts"]:
            for f in v.link_faces:
                f.material_index = 6
    add_oriented_box(bm, (st_x, st_y, 0.016), p_dir, p_norm, 0.95, 0.12, 0.02, 6)
    add_oriented_box(bm, (st_x + p_dir[0] * 1.25, st_y + p_dir[1] * 1.25, 0.016), p_dir, p_norm, 0.75, 0.45, 0.02, 6)
    # Blue flexible bike-lane delineator posts & white dashed lane stripes
    for k_b in range(6):
        bx = -354.5 + p_dir[0] * (k_b * 5.2)
        by = 17.5 + p_dir[1] * (k_b * 5.2)
        add_oriented_box(bm, (bx, by, 0.015), p_dir, p_norm, 1.6, 0.13, 0.02, 6)
        add_oriented_box(bm, (bx - p_norm[0] * 1.6, by - p_norm[1] * 1.6, 0.45), p_dir, p_norm, 0.09, 0.09, 0.85, 5)
    # Sculpted dark metallic Mazda sedan on Place Jean-Paul-Riopelle (`(-346.2, 24.8)`)
    add_sculpted_vehicle(bm, -346.2, 24.8, 212.0, "sedan", mat_body=2, mat_glass=8, mat_tire=3, mat_rim=4, mat_light=7)

    # 5. Camera 3 (`Rue_SaintAntoine_South_Facade`) Street Props: BIXI Station + Bikes, Dual-Solar Kiosk, Box Truck, SUV, Oval Planter
    sa_dir = (0.506, 0.862)
    sa_norm = (0.862, -0.506)
    # Blue cycle lane stripe & white buffer stripe in foreground of Cam 3
    add_oriented_box(bm, (-208.5, -16.5, 0.018), sa_dir, sa_norm, 32.0, 0.24, 0.02, 5)
    add_oriented_box(bm, (-209.2, -15.8, 0.018), sa_dir, sa_norm, 32.0, 0.16, 0.02, 6)
    # BIXI bike-share platform (`(-214.8, -15.2)`), 8 black dock bollards, 5 sculpted 3D bicycles, and dual-solar payment kiosk!
    bx_base, by_base = -214.8, -15.2
    add_oriented_box(bm, (bx_base, by_base, 0.07), sa_dir, sa_norm, 8.2, 1.85, 0.12, 1)
    for d_k in range(-4, 4):
        dx_b = bx_base + sa_dir[0] * (d_k * 0.92) + sa_norm[0] * 0.55
        dy_b = by_base + sa_dir[1] * (d_k * 0.92) + sa_norm[1] * 0.55
        add_oriented_box(bm, (dx_b, dy_b, 0.48), sa_dir, sa_norm, 0.16, 0.24, 0.82, 3)
        if d_k in (-4, -3, -1, 1, 3):
            add_bixi_bicycle(bm, dx_b, dy_b, sa_dir, sa_norm, mat_tire=3, mat_frame=7 if d_k == -3 else 4, mat_rim=4)
    # Payment kiosk at right end of BIXI dock (`(-210.8, -11.6)`) topped by TWO tilted black solar panel wings!
    kx, ky = -210.8, -11.6
    add_oriented_box(bm, (kx, ky, 1.10), sa_dir, sa_norm, 0.44, 0.36, 2.05, 3)
    add_oriented_box(bm, (kx - sa_dir[0] * 0.42, ky - sa_dir[1] * 0.42, 2.48), sa_dir, sa_norm, 0.72, 0.88, 0.08, 8)
    add_oriented_box(bm, (kx + sa_dir[0] * 0.42, ky + sa_dir[1] * 0.42, 2.56), sa_dir, sa_norm, 0.72, 0.88, 0.08, 8)
    # Raised Concrete Oval Planter Island with Green Shrubs & Parked Motorcycle on right foreground (`(-205.2, -9.2)`)
    px_i, py_i = -205.2, -9.2
    ret_pl = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=20, radius1=1.65, radius2=1.65, depth=0.28, matrix=Matrix.Translation((px_i, py_i, 0.14)))
    for v in ret_pl["verts"]:
        for f in v.link_faces:
            f.material_index = 1
    ret_sh = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=16, radius1=1.35, radius2=1.05, depth=0.65, matrix=Matrix.Translation((px_i, py_i, 0.45)))
    for v in ret_sh["verts"]:
        for f in v.link_faces:
            f.material_index = 9
            f.smooth = True
    # Sculpted White Commercial Delivery Box Truck on left street lane (`(-220.2, -23.5)`), Dark Grey SUV in center (`(-209.5, -8.5)`), Silver Sedan on right (`(-202.2, 3.8)`)
    add_sculpted_vehicle(bm, -220.2, -23.5, 31.0, "truck", mat_body=6, mat_glass=8, mat_tire=3, mat_rim=4, mat_light=7)
    add_sculpted_vehicle(bm, -209.5, -8.5, 31.0, "suv", mat_body=2, mat_glass=8, mat_tire=3, mat_rim=4, mat_light=7)
    add_sculpted_vehicle(bm, -202.2, 3.8, 31.0, "sedan", mat_body=4, mat_glass=8, mat_tire=3, mat_rim=4, mat_light=7)

    # 6. Camera 4 (`Rue_SaintUrbain_East_Side`) Street Props: 5 Royal-Blue Cylindrical Columns, White Jersey Barriers, Striped Sign Base, Lamppost
    su_dir = (-0.566, 0.824)
    su_norm = (0.824, 0.566)
    for jb_i in range(5):
        jx = -153.8 + su_dir[0] * (jb_i * 2.8) + su_norm[0] * 1.4
        jy = 99.5 + su_dir[1] * (jb_i * 2.8) + su_norm[1] * 1.4
        add_oriented_box(bm, (jx, jy, 0.48), su_dir, su_norm, 2.6, 0.52, 0.88, 6)
    for bc_i in range(5):
        bx_c = -154.6 + su_dir[0] * (bc_i * 2.3) + su_norm[0] * 3.4
        by_c = 101.2 + su_dir[1] * (bc_i * 2.3) + su_norm[1] * 3.4
        ret_bc = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=16, radius1=0.24, radius2=0.24, depth=4.8, matrix=Matrix.Translation((bx_c, by_c, 2.4)))
        for v in ret_bc["verts"]:
            for f in v.link_faces:
                f.material_index = 5
                f.smooth = True
    # Orange construction sign on 5-layer black-and-white striped square rubber base (`(-149.8, 90.8)`) + left foreground lamppost (`(-150.1, 85.8)`)
    for st_l in range(5):
        add_oriented_box(bm, (-149.8, 90.8, 0.22 + st_l * 0.08), su_dir, su_norm, 0.52, 0.52, 0.075, 3 if st_l % 2 == 0 else 6)
    add_oriented_box(bm, (-149.8, 90.8, 0.82), su_dir, su_norm, 0.06, 0.06, 0.55, 7)
    add_oriented_box(bm, (-149.8, 90.8, 1.35), su_dir, su_norm, 0.08, 0.46, 0.88, 7)
    ret_lp = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=12, radius1=0.12, radius2=0.09, depth=7.2, matrix=Matrix.Translation((-150.1, 85.8, 3.6)))
    for v in ret_lp["verts"]:
        for f in v.link_faces:
            f.material_index = 3
            f.smooth = True

    # 7. Slender Single-Stem Urban Street Saplings (`jacaranda_tree_LOD0` reshaped) Placed Strictly on Curb Line (Zero Wall Clipping!)
    sapling_mesh = load_kit_tree()
    tree_positions = [
        # Cam 1 (`Place_Riopelle_Colored_Glass` left plaza trees)
        (-361.5, 29.5, 0.95), (-356.0, 38.0, 0.90), (-350.5, 46.5, 0.88),
        # Cam 3 (`Rue_SaintAntoine_South_Facade` sidewalk curb trees — +3.2m outside the facade so ZERO branches clip the wall!)
        (-218.5, -21.8, 0.82), (-213.8, -13.8, 0.85), (-208.8, -5.2, 0.80),
        # Cam 4 (`Rue_SaintUrbain_East_Side` slender foreground sidewalk saplings in square grates)
        (-150.6, 88.8, 0.78), (-148.2, 92.8, 0.76),
    ]
    for t in dossier["osm_features"].get("trees", [])[:30]:
        if "xy" in t:
            tx_0, ty_0 = t["xy"][0], t["xy"][1]
            if ty_0 > 165.0 or tx_0 < -380.0:
                tree_positions.append((tx_0, ty_0, 0.88))
    spawn_polyhaven_trees(sapling_mesh, tree_positions, streets_col, bm, mat_grate=3)

    bm.to_mesh(mesh)
    bm.free()
    return obj


def setup_world_and_render(dossier, iter_num=1):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 64
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True
    scene.eevee.use_shadows = True

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    wnodes = world.node_tree.nodes
    wlinks = world.node_tree.links
    wnodes.clear()

    w_out = wnodes.new("ShaderNodeOutputWorld")
    w_bg = wnodes.new("ShaderNodeBackground")
    w_bg.inputs["Strength"].default_value = 1.15
    hdri_path = os.path.join(POLYHAVEN_DIR, "kloppenheim_06_puresky_2k.hdr")
    if os.path.exists(hdri_path):
        env_tex = wnodes.new("ShaderNodeTexEnvironment")
        env_tex.image = bpy.data.images.load(hdri_path, check_existing=True)
        wlinks.new(w_bg.inputs["Color"], env_tex.outputs["Color"])
    else:
        w_bg.inputs["Color"].default_value = (0.55, 0.68, 0.85, 1.0)
    wlinks.new(w_out.inputs["Surface"], w_bg.outputs["Background"])

    sun_data = bpy.data.lights.new(name="MTL_Sun", type='SUN')
    sun_data.energy = 3.6
    sun_data.color = (1.0, 0.95, 0.88)
    sun_data.angle = math.radians(4.5)
    sun_obj = bpy.data.objects.new(name="MTL_Sun", object_data=sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(48.0), math.radians(18.0), math.radians(-125.0))

    # Render the 4 Street View cameras (`640x640`)
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        cx, cy = cam_info["blender_cam_xy_m"]
        heading_deg = cam_info.get("heading", cam_info.get("heading_deg", 0.0))
        pitch_deg = cam_info.get("pitch_deg", 12.0)
        fov_deg = cam_info.get("fov_deg", 90.0)

        cam_data = bpy.data.cameras.new(name=f"Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(fov_deg)
        cam_data.clip_start = 0.2
        cam_data.clip_end = 1500.0
        cam_obj = bpy.data.objects.new(name=f"Cam_{label}", object_data=cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)
        cam_obj.location = (cx, cy, 1.7)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch_deg), 0.0, math.radians(-heading_deg))

        scene.camera = cam_obj
        out_png = os.path.join(RENDERS_DIR, f"iter{iter_num}_{label}.png")
        scene.render.filepath = out_png
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View camera -> {out_png} (pos=({cx}, {cy}), heading={heading_deg})")

    # Render Overview Snapshot (`1280x720`) framing Palais des Congrès & Place Jean-Paul-Riopelle
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    ov_data = bpy.data.cameras.new(name="Cam_Overview")
    ov_data.lens = 28.0
    ov_data.clip_start = 0.5
    ov_data.clip_end = 2000.0
    ov_obj = bpy.data.objects.new(name="Cam_Overview", object_data=ov_data)
    bpy.context.scene.collection.objects.link(ov_obj)
    ov_obj.location = (-455.0, -65.0, 115.0)
    look_vec = Vector((-265.0, 95.0, 12.0)) - ov_obj.location
    ov_obj.rotation_euler = look_vec.to_track_quat('-Z', 'Y').to_euler()

    scene.camera = ov_obj
    snap_path = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
    scene.render.filepath = snap_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Overview Snapshot -> {snap_path}")


def main():
    iter_num = 1
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if args:
            iter_num = int(args[0])

    clear_scene()
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    root_col, owned_col, proxy_col, streets_col = create_collection_hierarchy()
    palette = kit.create_montreal_material_palette()
    enhance_materials(palette)

    cam_coords = [c["blender_cam_xy_m"] for c in dossier.get("streetview_cameras", [])]
    owned_count = 0
    proxy_count = 0
    for b in dossier["osm_features"]["buildings"]:
        if b.get("is_primary_owner", True):
            build_context_or_owned_building(b, owned_col, palette, cam_coords)
            owned_count += 1
        else:
            build_context_or_owned_building(b, proxy_col, palette, cam_coords)
            proxy_count += 1

    create_ground_and_streetscape(dossier, streets_col, palette)
    print(f"Built {owned_count} Owned buildings and {proxy_count} Context Proxy buildings.")

    setup_world_and_render(dossier, iter_num=iter_num)

    blend_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.blend")
    usdc_path = os.path.join(OUTPUT_BLOCKS_DIR, f"{BLOCK_ID}.usdc")
    for p_rm in (blend_path, blend_path + "@", blend_path + "1"):
        if os.path.exists(p_rm):
            try:
                os.remove(p_rm)
            except OSError:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=False)
    bpy.ops.wm.usd_export(filepath=usdc_path, selected_objects_only=False)
    print(f"Saved {blend_path} and exported {usdc_path}")


if __name__ == "__main__":
    main()

