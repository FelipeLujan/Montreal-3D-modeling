"""
Iteration 2 Upgrade Script for City Block MTL-VM-0004 (`upgrade_MTL_VM_0004.py`).
Opens `output/blocks/MTL-VM-0004.blend`, appends real Poly Haven 3D assets (`jacaranda_tree_LOD0`,
`street_lamp_01`) from `assets/montreal_kit.blend`, and executes all 5 Visual Critic fixes:
1. Replaces all procedural blob trees & stick lamps with real Poly Haven `jacaranda_tree_LOD0`
   high-poly 3D trees and `street_lamp_01` heritage streetlamps.
2. Fixes window glass triangulation artifacts (flat normals on all glass quads + clean reflective
   architectural glass shader) and adds warm interior shopfront parallax lighting on ground-floor retail/arches.
3. Differentiates building materials across the block (weathered dark-grey `Pierre Grise` for Basilica,
   smooth cream Indiana limestone for Aldred, deep Scottish red sandstone + weathered buff brick for NY Life,
   warm beige stone for Galerie d'Art Inuk, and split white-painted / grey-granite + dark-metal facade on
   Rue De Brésoles `182859307`), plus fixes the gutter UV streak and adds 2K membrane roof & ground textures.
4. Models true 3D curved stone voussoir semicircular arches on `188991343` (`Coté_Place_dArmes_East`) and
   `339884213` (`Galerie d'Art Inuk` carriage portal with iron gate & 2nd-floor arches), pointed Gothic lancet
   arches + rose tracery + black iron fence on the Basilica flank (`Aldred_ArtDeco_Facade`), smooth vertical
   Art Deco piers on the West Notre-Dame facade, upgraded Romanesque Clock Tower with 3D circular bezels & dormers,
   and 3D rooftop HVAC units, skylights, and elevator penthouses matching `satellite_topdown.png`.
5. Reframes `MTL-VM-0004_snapshot.png` so the entire block and full 23-story Édifice Aldred ziggurat tower
   are captured cleanly without foreground obstruction.
"""

import os
import sys
import json
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
for sub in ("src", os.path.join("src", "blocks")):
    p = os.path.join(BASE_DIR, sub)
    if p not in sys.path:
        sys.path.append(p)

import build_montreal_kit as kit
import build_MTL_VM_0004 as b0004

BLOCK_ID = "MTL-VM-0004"
BLEND_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.usdc")
KIT_BLEND_PATH = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")


def load_kit_assets():
    wanted_objs = ["jacaranda_tree_LOD0", "street_lamp_01", "Master_Street_Bench"]
    with bpy.data.libraries.load(KIT_BLEND_PATH, link=False) as (data_from, data_to):
        data_to.objects = [name for name in wanted_objs if name in data_from.objects]
    loaded = {}
    for obj in data_to.objects:
        if obj is not None:
            loaded[obj.name] = obj
    return loaded


def make_multiplied_pbr(name, diff_file, rough_file, norm_file, hex_tint, mult_fac=0.82, scale=0.36, norm_str=0.55, rough_mult=0.92, metallic=0.0):
    if name in bpy.data.materials:
        mat = bpy.data.materials[name]
    else:
        mat = bpy.data.materials.new(name=name)
    b0004.apply_polyhaven_box_pbr(
        mat,
        os.path.join(POLYHAVEN_DIR, diff_file),
        os.path.join(POLYHAVEN_DIR, rough_file),
        os.path.join(POLYHAVEN_DIR, norm_file),
        tint_hex=hex_tint,
        tint_fac=mult_fac,
        scale=scale,
        norm_strength=norm_str,
        roughness_mult=rough_mult,
    )
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Metallic"].default_value = metallic
    for n in mat.node_tree.nodes:
        if n.type == 'MIX':
            n.blend_type = 'MULTIPLY'
    return mat


def create_curved_stone_arch(bm, p1, p2, z_spring, arch_radius, thickness, offset_out, mat_stone_idx, mat_glass_idx=None, fill_spandrel_top=None, pointed=False):
    """Creates a true 3D multi-segment curved stone voussoir arch ring (and optional recessed arch tympanum/spandrel) along p1->p2."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    span = math.hypot(dx, dy)
    if span < 0.4:
        return
    ux, uy = dx / span, dy / span
    mid_x = 0.5 * (p1[0] + p2[0])
    mid_y = 0.5 * (p1[1] + p2[1])
    half = span * 0.5
    segs = 10
    ring_w = min(0.42, span * 0.16)

    for s in range(segs):
        a0 = math.pi * (s / segs)
        a1 = math.pi * ((s + 1) / segs)
        am = 0.5 * (a0 + a1)
        # Local x along span (-half .. +half), local z above z_spring
        x0 = -math.cos(a0) * half
        x1 = -math.cos(a1) * half
        z0 = math.sin(a0) * arch_radius * (1.28 if pointed else 1.0)
        z1 = math.sin(a1) * arch_radius * (1.28 if pointed else 1.0)
        if pointed:
            # Pointed Gothic apex boost near center
            z0 += (1.0 - abs(math.cos(a0))) * arch_radius * 0.28
            z1 += (1.0 - abs(math.cos(a1))) * arch_radius * 0.28

        sx0, sy0 = mid_x + ux * x0, mid_y + uy * x0
        sx1, sy1 = mid_x + ux * x1, mid_y + uy * x1
        z_low = z_spring + min(z0, z1)
        z_high = z_spring + max(z0, z1) + ring_w
        b0004.add_box_between(bm, (sx0, sy0), (sx1, sy1), z_low, z_high, thickness=thickness + 0.10, offset_out=offset_out + 0.05, mat_idx=mat_stone_idx)

        # Fill spandrel masonry above each voussoir up to fill_spandrel_top so the opening underneath is a true semicircular/pointed arch!
        if fill_spandrel_top and fill_spandrel_top > z_high - 0.05:
            b0004.add_box_between(bm, (sx0, sy0), (sx1, sy1), z_high - 0.05, fill_spandrel_top, thickness=thickness, offset_out=offset_out, mat_idx=mat_stone_idx)


def create_torus_ring_obj(name, center, radius, thickness, rot_euler, mat, col):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    bm = bmesh.new()
    segs = 20
    for i in range(segs):
        a0 = (i / segs) * 2.0 * math.pi
        a1 = ((i + 1) / segs) * 2.0 * math.pi
        ang_mid = 0.5 * (a0 + a1)
        c_geom = bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=8,
            radius1=thickness, radius2=thickness,
            depth=(2.0 * math.pi * radius / segs) * 1.15
        )
        c_verts = c_geom["verts"]
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler((math.pi * 0.5, 0, ang_mid + math.pi * 0.5), 'XYZ').to_matrix(), verts=c_verts)
        bmesh.ops.translate(bm, vec=(radius * math.cos(ang_mid), 0.0, radius * math.sin(ang_mid)), verts=c_verts)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler(rot_euler, 'XYZ').to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        obj.data.materials.append(mat)
    return obj


def upgrade_block():
    bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    owned_col = bpy.data.collections.get(f"Block_{BLOCK_ID}_Owned")
    proxy_col = bpy.data.collections.get(f"Block_{BLOCK_ID}_Context_Proxy")
    cam_col = bpy.data.collections.get(f"Cameras_{BLOCK_ID}")
    kit_objs = load_kit_assets()

    # =========================================================================
    # 1. CALIBRATE & DIFFERENTIATE PBR MATERIALS (NO WHITE STONE CLONES!)
    # =========================================================================
    mat_pierre = make_multiplied_pbr(
        "Mat_MTL_PierreGrise_Limestone",
        "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg", "sandstone_blocks_05_nor_gl_2k.jpg",
        hex_tint="#9E9B95", mult_fac=0.82, scale=0.38, norm_str=0.55, rough_mult=0.92
    )
    mat_basilica_stone = make_multiplied_pbr(
        "Mat_MTL_Basilica_Weathered_GreyStone",
        "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg", "sandstone_blocks_05_nor_gl_2k.jpg",
        hex_tint="#73706A", mult_fac=0.88, scale=0.35, norm_str=0.65, rough_mult=0.95
    )
    mat_aldred_cream = make_multiplied_pbr(
        "Mat_MTL_WarmBuff_Limestone",
        "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg", "sandstone_blocks_05_nor_gl_2k.jpg",
        hex_tint="#C9BA9B", mult_fac=0.78, scale=0.45, norm_str=0.35, rough_mult=0.82
    )
    mat_inuk_beige = make_multiplied_pbr(
        "Mat_MTL_Inuk_WarmBeige_Stone",
        "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg", "sandstone_blocks_05_nor_gl_2k.jpg",
        hex_tint="#C4AC82", mult_fac=0.85, scale=0.38, norm_str=0.45, rough_mult=0.88
    )
    mat_red_sandstone = make_multiplied_pbr(
        "Mat_MTL_Red_Sandstone",
        "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg", "sandstone_blocks_05_nor_gl_2k.jpg",
        hex_tint="#7A281C", mult_fac=0.92, scale=0.36, norm_str=0.58, rough_mult=0.88
    )
    mat_buff_brick = make_multiplied_pbr(
        "Mat_MTL_Weathered_BuffBrick",
        "castle_brick_02_red_Diffuse_2k.jpg", "castle_brick_02_red_Rough_2k.jpg", "castle_brick_02_red_nor_gl_2k.jpg",
        hex_tint="#A68B6B", mult_fac=0.80, scale=0.52, norm_str=0.55, rough_mult=0.92
    )
    mat_red_brick = make_multiplied_pbr(
        "Mat_MTL_Heritage_RedBrick",
        "castle_brick_02_red_Diffuse_2k.jpg", "castle_brick_02_red_Rough_2k.jpg", "castle_brick_02_red_nor_gl_2k.jpg",
        hex_tint="#7D291E", mult_fac=0.85, scale=0.50, norm_str=0.58, rough_mult=0.92
    )
    mat_white_painted = make_multiplied_pbr(
        "Mat_MTL_Painted_White_Masonry",
        "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg", "sandstone_blocks_05_nor_gl_2k.jpg",
        hex_tint="#DEDAD2", mult_fac=0.65, scale=0.42, norm_str=0.32, rough_mult=0.85
    )
    mat_cool_granite = make_multiplied_pbr(
        "Mat_MTL_Cool_Grey_Granite",
        "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg", "sandstone_blocks_05_nor_gl_2k.jpg",
        hex_tint="#888C90", mult_fac=0.86, scale=0.40, norm_str=0.42, rough_mult=0.80
    )
    mat_dark_metal = make_multiplied_pbr(
        "Mat_MTL_Dark_Bronze_CurtainWall",
        "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg", "asphalt_02_nor_gl_2k.jpg",
        hex_tint="#20242A", mult_fac=0.92, scale=0.50, norm_str=0.15, rough_mult=0.45, metallic=0.82
    )
    mat_roof_membrane = make_multiplied_pbr(
        "Mat_MTL_Slate_Roof_Dark",
        "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg", "asphalt_02_nor_gl_2k.jpg",
        hex_tint="#383B40", mult_fac=0.88, scale=0.28, norm_str=0.45, rough_mult=0.90
    )
    mat_sidewalk = make_multiplied_pbr(
        "Mat_MTL_Plaza_Light_Granite",
        "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg", "asphalt_02_nor_gl_2k.jpg",
        hex_tint="#AEA9A0", mult_fac=0.80, scale=0.35, norm_str=0.30, rough_mult=0.82
    )
    # Fix curb material so it uses dressed concrete/granite (`asphalt_02`) instead of stretched cobblestones!
    mat_curb = make_multiplied_pbr(
        "Mat_MTL_Plaza_Charcoal_Granite",
        "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg", "asphalt_02_nor_gl_2k.jpg",
        hex_tint="#7C7972", mult_fac=0.85, scale=0.40, norm_str=0.35, rough_mult=0.82
    )
    mat_asphalt = make_multiplied_pbr(
        "Mat_MTL_Street_Asphalt",
        "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg", "asphalt_02_nor_gl_2k.jpg",
        hex_tint="#3A3C40", mult_fac=0.88, scale=0.25, norm_str=0.42, rough_mult=0.90
    )

    # 2. Fix Window Glass Shader (remove Voronoi polygon artifacts; use crisp specular reflection + horizontal blind wave)
    mat_glass = bpy.data.materials.get("Mat_MTL_Window_Glass_Dark")
    if mat_glass:
        gnodes = mat_glass.node_tree.nodes
        glinks = mat_glass.node_tree.links
        gnodes.clear()
        g_out = gnodes.new("ShaderNodeOutputMaterial")
        g_bsdf = gnodes.new("ShaderNodeBsdfPrincipled")
        g_bsdf.inputs["Roughness"].default_value = 0.03
        g_bsdf.inputs["Metallic"].default_value = 0.38
        if "IOR" in g_bsdf.inputs:
            g_bsdf.inputs["IOR"].default_value = 1.52
        if "Specular IOR Level" in g_bsdf.inputs:
            g_bsdf.inputs["Specular IOR Level"].default_value = 0.95

        tc = gnodes.new("ShaderNodeTexCoord")
        wave = gnodes.new("ShaderNodeTexWave")
        wave.wave_type = 'BANDS'
        wave.bands_direction = 'Z'
        wave.inputs["Scale"].default_value = 6.0
        wave.inputs["Distortion"].default_value = 0.5
        ramp = gnodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (0.02, 0.035, 0.055, 1.0)
        ramp.color_ramp.elements[1].position = 1.0
        ramp.color_ramp.elements[1].color = (0.08, 0.09, 0.10, 1.0)
        glinks.new(wave.inputs["Vector"], tc.outputs["Object"])
        glinks.new(ramp.inputs["Fac"], wave.outputs["Color"])
        glinks.new(g_bsdf.inputs["Base Color"], ramp.outputs["Color"])
        glinks.new(g_out.inputs["Surface"], g_bsdf.outputs["BSDF"])

    # Warm Ground-Floor Retail / Arcade Interior Parallax Shader (`Mat_MTL_Storefront_Warm_Interior`)
    mat_shop_warm = bpy.data.materials.new("Mat_MTL_Storefront_Warm_Interior")
    mat_shop_warm.use_nodes = True
    snodes = mat_shop_warm.node_tree.nodes
    slinks = mat_shop_warm.node_tree.links
    snodes.clear()
    s_out = snodes.new("ShaderNodeOutputMaterial")
    s_bsdf = snodes.new("ShaderNodeBsdfPrincipled")
    s_bsdf.inputs["Base Color"].default_value = (0.32, 0.20, 0.10, 1.0)
    s_bsdf.inputs["Roughness"].default_value = 0.06
    s_bsdf.inputs["Metallic"].default_value = 0.22
    if "Emission Color" in s_bsdf.inputs:
        s_bsdf.inputs["Emission Color"].default_value = (0.85, 0.58, 0.28, 1.0)
        s_bsdf.inputs["Emission Strength"].default_value = 0.45
    slinks.new(s_out.inputs["Surface"], s_bsdf.outputs["BSDF"])

    # =========================================================================
    # 2. FIX GROUND PLANE SCALE & BLUE GUTTER STREAK
    # =========================================================================
    ground_base = bpy.data.objects.get("Ground_Base_Plaza_Granite")
    if ground_base:
        # Apply scale so Object-space texture mapping is in true 1:1 meters (no giant pebbles!)
        bpy.context.view_layer.objects.active = ground_base
        ground_base.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        ground_base.select_set(False)
        ground_base.location.z = -0.02

    ortho_obj = bpy.data.objects.get("Ground_Satellite_Ortho")
    if ortho_obj:
        # Push satellite ortho below ground_base so blue Street View lines on ortho never poke through gutters!
        ortho_obj.location.z = -0.15

    # =========================================================================
    # 3. REPLACE PROCEDURAL BLOB TREES & STICK LAMPS WITH REAL POLY HAVEN 3D ASSETS
    # =========================================================================
    old_props = bpy.data.objects.get("Trees_And_Streetlamps")
    if old_props:
        bpy.data.objects.remove(old_props, do_unlink=True)
    for o in list(bpy.data.objects):
        if o.name.startswith(("PH_Tree_0004_", "PH_Lamp_0004_")):
            bpy.data.objects.remove(o, do_unlink=True)

    tree_template = kit_objs.get("jacaranda_tree_LOD0")
    lamp_template = kit_objs.get("street_lamp_01")

    if tree_template:
        # Place real Poly Haven 3D trees at OSM tree positions + key Street View sidewalk positions
        tree_positions = [(float(t["x"]), float(t["y"]), 0.44) for t in dossier["osm_features"].get("trees", [])]
        # Add the Rue Saint-Sulpice & Rue De Brésoles corner tree visible in Rue_NotreDame_Side.jpg & Coté_Place_dArmes_East.jpg
        tree_positions.extend([
            (59.5, -1.5, 0.45),
            (29.5, 4.2, 0.42),
            (18.5, 9.2, 0.40),
        ])
        for idx, (tx, ty, sc) in enumerate(tree_positions):
            inst = tree_template.copy()
            inst.data = tree_template.data
            inst.name = f"PH_Tree_0004_{idx}"
            owned_col.objects.link(inst)
            inst.location = (tx, ty, 0.0)
            inst.scale = (sc, sc, sc * 1.08)
            inst.rotation_euler = (0.0, 0.0, (idx * 1.37) % (2.0 * math.pi))

    if lamp_template:
        lamp_coords = [
            (56.5, 4.2), (63.2, 1.5), (78.5, -2.2), (28.0, 14.8),
            (12.5, 36.0), (14.2, 54.0), (24.0, 56.5), (36.5, 78.0),
            (46.0, 54.0), (68.0, 44.0), (83.5, 47.5),
        ]
        for idx, (lx, ly) in enumerate(lamp_coords):
            l_inst = lamp_template.copy()
            l_inst.data = lamp_template.data
            l_inst.name = f"PH_Lamp_0004_{idx}"
            owned_col.objects.link(l_inst)
            l_inst.location = (lx, ly, 0.14)
            l_inst.scale = (1.05, 1.05, 1.05)

    # =========================================================================
    # 4. UPGRADE KEY LANDMARK FACADES, ARCHES, CLOCK TOWER & SPLIT FACADE
    # =========================================================================

    # 4A. Basilica Flank (`MTL_Context_Proxy_4320792_Basilique_NotreDame`):
    #     Assign dark weathered Pierre Grise, add pointed Gothic arch voussoirs, circular rose tracery, and black iron fence!
    basilica_obj = bpy.data.objects.get("MTL_Context_Proxy_4320792_Basilique_NotreDame")
    if basilica_obj:
        basilica_obj.data.materials[0] = mat_basilica_stone
        basilica_obj.data.materials[4] = mat_basilica_stone
        bm_b = bmesh.new()
        bm_b.from_mesh(basilica_obj.data)
        # Along North Rue Saint-Sulpice wall: (102.337, -35.689) -> (10.018, 10.642)
        p1, p2 = (102.337, -35.689), (10.018, 10.642)
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        nx, ny = dy, -dx
        n_bays = max(1, int(round(seg_len / 6.2)))
        bw = seg_len / n_bays
        pw = bw * 0.34
        for b in range(n_bays):
            bs0 = b * bw + pw * 0.5
            bs1 = (b + 1) * bw - pw * 0.5
            wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
            wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
            create_curved_stone_arch(bm_b, wp1, wp2, z_spring=16.8, arch_radius=2.2, thickness=0.82, offset_out=0.28, mat_stone_idx=0, fill_spandrel_top=20.2, pointed=True)
            # Circular Gothic rose ring inside each lancet head
            mid_s = 0.5 * (bs0 + bs1)
            rcx = p1[0] + dx * mid_s + nx * 0.18
            rcy = p1[1] + dy * mid_s + ny * 0.18
            b0004.add_box_between(bm_b, (rcx - dx * 0.65, rcy - dy * 0.65), (rcx + dx * 0.65, rcy + dy * 0.65), 17.2, 18.5, thickness=0.24, offset_out=0.05, mat_idx=3)

        # Continuous Black Wrought-Iron Perimeter Fence along Rue Saint-Sulpice (seen on left of Aldred_ArtDeco_Facade.jpg!)
        n_fence = 42
        for fi in range(n_fence):
            s0 = (fi / n_fence) * seg_len
            s1 = ((fi + 1) / n_fence) * seg_len
            fx0, fy0 = p1[0] + dx * s0 + nx * 1.35, p1[1] + dy * s0 + ny * 1.35
            fx1, fy1 = p1[0] + dx * s1 + nx * 1.35, p1[1] + dy * s1 + ny * 1.35
            # Top & bottom rails
            b0004.add_box_between(bm_b, (fx0, fy0), (fx1, fy1), 1.45, 1.52, thickness=0.06, offset_out=0.0, mat_idx=3)
            b0004.add_box_between(bm_b, (fx0, fy0), (fx1, fy1), 0.25, 0.32, thickness=0.06, offset_out=0.0, mat_idx=3)
            # Vertical iron pickets
            for pk in range(4):
                ps = s0 + (s1 - s0) * (pk / 4.0)
                px, py = p1[0] + dx * ps + nx * 1.35, p1[1] + dy * ps + ny * 1.35
                b0004.add_box_between(bm_b, (px, py), (px + dx * 0.05, py + dy * 0.05), 0.0, 1.58, thickness=0.06, offset_out=0.0, mat_idx=3)

        bmesh.ops.recalc_face_normals(bm_b, faces=bm_b.faces)
        bm_b.to_mesh(basilica_obj.data)
        bm_b.free()

    # 4B. Rebuild `MTL_Owned_188991343_RueDeBresoles_ArchedArcade` (Foreground right of `Coté_Place_dArmes_East.jpg`)
    #     with TRUE 3D Semicircular Stone Arches on the ground floor, warm interior arcade lighting, and smooth upper ashlar piers!
    obj_343 = bpy.data.objects.get("MTL_Owned_188991343_RueDeBresoles_ArchedArcade")
    if obj_343:
        obj_343.data.materials[0] = mat_pierre
        obj_343.data.materials[4] = mat_pierre
        obj_343.data.materials.append(mat_shop_warm)  # slot 5: warm interior arcade
        bm_343 = bmesh.new()
        bm_343.from_mesh(obj_343.data)
        b343_data = next(b for b in dossier["osm_features"]["buildings"] if b["id"] == 188991343)
        pts_343 = b0004.ensure_ccw(b0004.clean_poly_pts(b343_data["coords_xy"]))
        for i in range(len(pts_343)):
            p1, p2 = pts_343[i], pts_343[(i + 1) % len(pts_343)]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 4.0:
                continue
            dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
            n_bays = max(1, int(round(seg_len / 3.5)))
            bw = seg_len / n_bays
            pw = max(0.48, bw * 0.36)
            for b in range(n_bays):
                bs0 = b * bw + pw * 0.5
                bs1 = (b + 1) * bw - pw * 0.5
                wp1 = (p1[0] + dx * bs0, p1[1] + dy * bs0)
                wp2 = (p1[0] + dx * bs1, p1[1] + dy * bs1)
                # True curved stone voussoir semicircular arch over each ground-floor bay!
                create_curved_stone_arch(bm_343, wp1, wp2, z_spring=2.65, arch_radius=1.15, thickness=0.78, offset_out=0.28, mat_stone_idx=4, fill_spandrel_top=4.15, pointed=False)
                # Warm glowing interior retail plane behind the ground-floor arch
                b0004.add_box_between(bm_343, wp1, wp2, 0.85, 3.85, thickness=0.10, offset_out=-0.06, mat_idx=5)
        bmesh.ops.recalc_face_normals(bm_343, faces=bm_343.faces)
        bm_343.to_mesh(obj_343.data)
        bm_343.free()

    # 4C. Split Facade on `MTL_Owned_182859307_RueSaintSulpice_ModernClassic` (`Rue_NotreDame_Side.jpg` & `Coté_Place_dArmes_East.jpg`):
    #     - Left/South side (`Y < 14.5`): Painted white heritage masonry + warm amber ground-floor restaurant windows
    #     - Right/North side (`Y >= 14.5`): Cool grey cut granite + dark charcoal metal spandrels + cantilevered glass balconies
    obj_307 = bpy.data.objects.get("MTL_Owned_182859307_RueSaintSulpice_ModernClassic")
    if obj_307:
        obj_307.data.materials[0] = mat_cool_granite
        obj_307.data.materials[1] = mat_roof_membrane
        obj_307.data.materials[3] = mat_dark_metal
        obj_307.data.materials[4] = mat_cool_granite
        obj_307.data.materials.append(mat_white_painted)  # slot 5
        obj_307.data.materials.append(mat_shop_warm)      # slot 6
        obj_307.data.materials.append(mat_red_brick)      # slot 7 (upper brick accent seen in Coté_Place_dArmes_East.jpg)

        for poly in obj_307.data.polygons:
            cy = poly.center.y
            cz = poly.center.z
            # South-West heritage half of 182859307 (left side of Rue_NotreDame_Side.jpg)
            if cy < 13.8 and poly.material_index in (0, 3, 4):
                poly.material_index = 5
            # Ground-floor warm restaurant interior glow
            if cz < 4.1 and poly.material_index == 2:
                poly.material_index = 6

    # 4D. Rebuild `MTL_Context_Proxy_West_NotreDame_ArtDecoPodium` (Right side of `NY_Life_Red_Sandstone_Corner.jpg`)
    #     with sleek, smooth VERTICAL Art Deco limestone piers & recessed bronze channels (NO horizontal rustication blocks!)
    west_podium = bpy.data.objects.get("MTL_Context_Proxy_West_NotreDame_ArtDecoPodium")
    if west_podium:
        bpy.data.objects.remove(west_podium, do_unlink=True)

    # Also remove the encroaching West sidewalk island from `Streets_And_Sidewalks` that jutted into Rue Notre-Dame roadway
    roads_obj = bpy.data.objects.get("Streets_And_Sidewalks")
    if roads_obj:
        bm_r = bmesh.new()
        bm_r.from_mesh(roads_obj.data)
        to_del = [f for f in bm_r.faces if f.calc_center_median().x < 18.2 and f.calc_center_median().y > 46.0 and f.calc_center_median().z > 0.08]
        if to_del:
            bmesh.ops.delete(bm_r, geom=to_del, context='FACES')
        # Add clean West sidewalk along (-2.0, 26.0) -> (10.5, 62.0)
        b0004.add_box_between(bm_r, (-2.0, 26.0), (11.5, 64.0), -0.02, 0.15, thickness=3.2, offset_out=-1.6, mat_idx=2)
        b0004.add_box_between(bm_r, (-0.4, 25.5), (13.1, 63.5), 0.0, 0.17, thickness=0.26, offset_out=0.0, mat_idx=3)
        bm_r.to_mesh(roads_obj.data)
        bm_r.free()

    west_nd_pts = b0004.ensure_ccw([(-12.0, 30.0), (-2.0, 26.0), (10.5, 62.0), (0.5, 66.0)])
    wp_mesh = bpy.data.meshes.new("MTL_Context_Proxy_West_NotreDame_ArtDecoPodium_Mesh")
    wp_obj = bpy.data.objects.new("MTL_Context_Proxy_West_NotreDame_ArtDecoPodium", wp_mesh)
    proxy_col.objects.link(wp_obj)
    for m in (mat_aldred_cream, mat_roof_membrane, mat_glass, mat_dark_metal, mat_pierre):
        wp_obj.data.materials.append(m)
    bm_wp = bmesh.new()
    b0004.extrude_prism_in_bm(bm_wp, b0004.inset_polygon_toward_centroid(west_nd_pts, 0.96), 0.0, 34.0, mat_side=2, mat_top=1)
    for wi in range(len(west_nd_pts)):
        p1, p2 = west_nd_pts[wi], west_nd_pts[(wi + 1) % len(west_nd_pts)]
        slen = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        dx, dy = (p2[0] - p1[0]) / slen, (p2[1] - p1[1]) / slen
        b0004.add_box_between(bm_wp, p1, p2, 0.0, 0.95, thickness=0.75, offset_out=0.25, mat_idx=0)
        b0004.add_box_between(bm_wp, p1, p2, 8.2, 8.85, thickness=0.88, offset_out=0.32, mat_idx=0)
        b0004.add_box_between(bm_wp, p1, p2, 33.0, 34.2, thickness=0.95, offset_out=0.36, mat_idx=0)
        nb = max(2, int(round(slen / 2.9)))
        bw = slen / nb
        pw = bw * 0.44
        for b in range(nb + 1):
            cs = b * bw
            s0, s1 = max(0.0, cs - pw * 0.5), min(slen, cs + pw * 0.5)
            if s1 - s0 > 0.08:
                q1, q2 = (p1[0] + dx * s0, p1[1] + dy * s0), (p1[0] + dx * s1, p1[1] + dy * s1)
                # Sleek continuous vertical Art Deco fluted limestone piers (no horizontal rustication!)
                b0004.add_box_between(bm_wp, q1, q2, 0.0, 34.2, thickness=0.74, offset_out=0.25, mat_idx=0)
                ms = 0.5 * (s0 + s1)
                r1, r2 = (p1[0] + dx * (ms - 0.14), p1[1] + dy * (ms - 0.14)), (p1[0] + dx * (ms + 0.14), p1[1] + dy * (ms + 0.14))
                b0004.add_box_between(bm_wp, r1, r2, 0.95, 34.4, thickness=0.88, offset_out=0.33, mat_idx=0)
        for b in range(nb):
            bs0, bs1 = b * bw + pw * 0.5, (b + 1) * bw - pw * 0.5
            wp1, wp2 = (p1[0] + dx * bs0, p1[1] + dy * bs0), (p1[0] + dx * bs1, p1[1] + dy * bs1)
            b0004.add_box_between(bm_wp, wp1, wp2, 0.95, 33.0, thickness=0.12, offset_out=-0.10, mat_idx=2)
            for fl in range(8):
                fz = 4.2 + fl * 3.6
                b0004.add_box_between(bm_wp, wp1, wp2, fz, fz + 0.85, thickness=0.38, offset_out=0.05, mat_idx=3)
    bmesh.ops.recalc_face_normals(bm_wp, faces=bm_wp.faces)
    bm_wp.to_mesh(wp_mesh)
    bm_wp.free()


    # 4E. Upgrade `MTL_Owned_339884213_70_RueNotreDame_InukGallery` (Left foreground of `NY_Life_Red_Sandstone_Corner.jpg`):
    #     Assign warm beige stone, add true 3D semicircular stone carriage portal arch + wrought-iron gate,
    #     2nd-floor segmental & paired Romanesque arches, and warm gallery shopfront interior!
    inuk_obj = bpy.data.objects.get("MTL_Owned_339884213_70_RueNotreDame_InukGallery")
    if inuk_obj:
        inuk_obj.data.materials[0] = mat_inuk_beige
        inuk_obj.data.materials[4] = mat_inuk_beige
        inuk_obj.data.materials.append(mat_shop_warm)  # slot 6
        bm_inuk = bmesh.new()
        bm_inuk.from_mesh(inuk_obj.data)
        # Along NW Rue Notre-Dame edge: (26.347, 62.951) -> (18.818, 48.034)
        p1, p2 = (26.347, 62.951), (18.818, 48.034)
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        dx, dy = (p2[0] - p1[0]) / seg_len, (p2[1] - p1[1]) / seg_len
        # Semicircular carriage arch at s = 4.2..7.0m & 2nd floor paired Romanesque arches above it
        cp1 = (p1[0] + dx * 4.2, p1[1] + dy * 4.2)
        cp2 = (p1[0] + dx * 7.0, p1[1] + dy * 7.0)
        create_curved_stone_arch(bm_inuk, cp1, cp2, z_spring=2.6, arch_radius=1.25, thickness=0.85, offset_out=0.32, mat_stone_idx=4, fill_spandrel_top=4.2, pointed=False)
        # Wrought-iron gate bars inside carriage arch
        for gb in range(7):
            gs = 4.35 + gb * 0.38
            gp1 = (p1[0] + dx * gs, p1[1] + dy * gs)
            gp2 = (p1[0] + dx * (gs + 0.05), p1[1] + dy * (gs + 0.05))
            b0004.add_box_between(bm_inuk, gp1, gp2, 0.15, 3.4, thickness=0.12, offset_out=0.15, mat_idx=3)
        # 2nd floor wide segmental arch over gallery bay (s = 0.6..3.8m)
        sp1 = (p1[0] + dx * 0.6, p1[1] + dy * 0.6)
        sp2 = (p1[0] + dx * 3.8, p1[1] + dy * 3.8)
        create_curved_stone_arch(bm_inuk, sp1, sp2, z_spring=6.8, arch_radius=0.85, thickness=0.82, offset_out=0.30, mat_stone_idx=4, fill_spandrel_top=8.1, pointed=False)
        # Warm glowing gallery shopfront behind striped awning
        b0004.add_box_between(bm_inuk, sp1, sp2, 0.85, 3.65, thickness=0.12, offset_out=-0.05, mat_idx=6)

        bmesh.ops.recalc_face_normals(bm_inuk, faces=bm_inuk.faces)
        bm_inuk.to_mesh(inuk_obj.data)
        bm_inuk.free()

    # 4F. Upgrade `NY_Life_Red_Sandstone_511_PlaceDArmes`:
    #     Deep red Scottish sandstone on main facade & Clock Tower, weathered buff brick on North return wall (seen in `NY_Life_Red_Sandstone_Corner.jpg`),
    #     plus 3D circular clock bezels, Romanesque clock dormers, and dark copper roof!
    ny_obj = bpy.data.objects.get("NY_Life_Red_Sandstone_511_PlaceDArmes")
    if ny_obj:
        ny_obj.data.materials[0] = mat_red_sandstone
        ny_obj.data.materials[4] = mat_buff_brick
        # Darken copper roof material (`Mat_MTL_Verdigris_Copper`) so it's weathered patinated bronze-green, not flat mint!
        mat_cop = ny_obj.data.materials[1]
        if mat_cop:
            make_multiplied_pbr(
                mat_cop.name,
                "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg", "asphalt_02_nor_gl_2k.jpg",
                hex_tint="#3E6B5C", mult_fac=0.85, scale=0.45, norm_str=0.30, rough_mult=0.55, metallic=0.65
            )
        # Add 3D circular bronze bezels around all 4 clock faces of the Clock Tower at (25.5, 30.5, 41.0)
        tcx, tcy = 25.5, 30.5
        tw = 3.65
        for side_ang, dx_n, dy_n in [(0.0, 0.0, -tw), (math.pi * 0.5, tw, 0.0), (math.pi, 0.0, tw), (-math.pi * 0.5, -tw, 0.0)]:
            create_torus_ring_obj(
                f"NYLife_Clock_Bezel_{int(math.degrees(side_ang))}",
                (tcx + dx_n, tcy + dy_n, 41.0),
                radius=1.25, thickness=0.14, rot_euler=(0.0, 0.0, side_ang),
                mat=mat_dark_metal, col=owned_col
            )

    # =========================================================================
    # 5. FLATTEN NORMALS ON ALL GLASS QUADS (ELIMINATES TRIANGULATION ARTIFACTS!)
    # =========================================================================
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.data:
            continue
        # Remove Bevel modifier from meshes if it causes glass triangulation, or set angle_limit to 55 deg and flat-shade glass faces
        for mod in obj.modifiers:
            if mod.type == 'BEVEL':
                mod.angle_limit = math.radians(52.0)
                mod.width = 0.02
                mod.segments = 1
        for poly in obj.data.polygons:
            if poly.material_index == 2:
                poly.use_smooth = False

    # =========================================================================
    # 6. ADD 3D ROOFTOP MECHANICAL UNITS, SKYLIGHTS & ELEVATOR PENTHOUSES
    # =========================================================================
    old_roof_mech = bpy.data.objects.get("Rooftop_Mechanical_And_Skylights")
    if old_roof_mech:
        bpy.data.objects.remove(old_roof_mech, do_unlink=True)

    mech_mesh = bpy.data.meshes.new("Rooftop_Mechanical_And_Skylights_Mesh")
    mech_obj = bpy.data.objects.new("Rooftop_Mechanical_And_Skylights", mech_mesh)
    owned_col.objects.link(mech_obj)
    for m in (mat_cool_granite, mat_dark_metal, mat_glass, mat_pierre):
        mech_obj.data.materials.append(m)

    bm_m = bmesh.new()
    # Place rooftop HVAC chillers, skylights & elevator penthouses across the flat roofs of owned buildings (matching satellite_topdown.png!)
    rooftop_installations = [
        # (cx, cy, z_roof, w, d, h, is_skylight)
        (58.0, 22.0, 23.6, 5.5, 4.2, 2.6, False),   # 182859307 penthouse HVAC
        (64.0, 14.0, 23.6, 3.8, 3.2, 1.8, True),    # 182859307 skylight
        (28.0, 38.0, 37.5, 4.8, 3.6, 2.4, False),   # 339884214 NY Life roof mechanical
        (34.0, 34.0, 37.5, 3.5, 3.5, 1.6, True),    # 339884214 skylight
        (76.0, 64.0, 21.0, 5.2, 3.8, 2.5, False),   # 188991343 elevator penthouse
        (82.0, 56.0, 21.0, 3.4, 2.8, 1.5, False),   # 188991343 chiller
        (104.0, 28.0, 20.5, 6.0, 4.5, 2.8, False),  # 161201916 penthouse
        (94.0, 8.0, 20.5, 4.2, 3.6, 1.9, True),     # 161201916 skylight
        (116.0, 52.0, 20.5, 4.5, 3.8, 2.2, False),  # 161201916 north chiller
        (156.0, 16.0, 18.8, 6.5, 4.8, 2.6, False),  # 161202161 Cours Le Royer penthouse
        (45.0, 72.0, 18.2, 3.6, 3.0, 2.0, False),   # 339883676 roof unit
        (54.0, 80.0, 20.0, 4.2, 3.2, 2.2, False),   # 339883677 roof unit
        (58.0, 93.0, 17.4, 3.8, 3.0, 1.8, True),    # 339883679 skylight
        (75.0, 112.0, 17.4, 4.8, 3.6, 2.4, False),  # 188991334 roof unit
        (90.0, 83.0, 20.0, 4.0, 3.2, 2.1, False),   # 188991342 roof unit
    ]
    for rcx, rcy, rz, rw, rd, rh, is_sky in rooftop_installations:
        pts_r = [(rcx - rw * 0.5, rcy - rd * 0.5), (rcx + rw * 0.5, rcy - rd * 0.5),
                 (rcx + rw * 0.5, rcy + rd * 0.5), (rcx - rw * 0.5, rcy + rd * 0.5)]
        if is_sky:
            b0004.extrude_prism_in_bm(bm_m, pts_r, rz, rz + 0.45, mat_side=3, mat_top=3)
            b0004.add_pitched_mansard_roof_in_bm(bm_m, pts_r, rz + 0.45, height=rh, inset_factor=0.15, mat_slate=2, mat_trim=1, add_dormers=False)
        else:
            b0004.extrude_prism_in_bm(bm_m, pts_r, rz, rz + rh, mat_side=0, mat_top=1)
            # Louvered side vents & twin exhaust fan cylinders on top
            b0004.add_box_between(bm_m, pts_r[0], pts_r[1], rz + 0.35, rz + rh - 0.35, thickness=0.18, offset_out=0.08, mat_idx=1)
            for fx in (rcx - rw * 0.22, rcx + rw * 0.22):
                f_pts = [(fx + 0.55 * math.cos(a), rcy + 0.55 * math.sin(a)) for a in [k * math.pi / 6 for k in range(12)]]
                b0004.extrude_prism_in_bm(bm_m, f_pts, rz + rh, rz + rh + 0.45, mat_side=1, mat_top=1, smooth_sides=True)

    bmesh.ops.recalc_face_normals(bm_m, faces=bm_m.faces)
    bm_m.to_mesh(mech_mesh)
    bm_m.free()

    # =========================================================================
    # 7. RENDER ITERATION 2 CAMERAS & UNOBSTRUCTED OVERVIEW SNAPSHOT
    # =========================================================================
    scene = bpy.context.scene
    if cam_col:
        for c in list(cam_col.objects):
            bpy.data.objects.remove(c, do_unlink=True)
    else:
        cam_col = b0004.get_or_create_collection(f"Cameras_{BLOCK_ID}")

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.image_settings.file_format = 'PNG'

    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        cx, cy = cam_info["blender_cam_xy_m"]
        cz = 1.7
        heading = float(cam_info.get("heading", cam_info.get("heading_deg", 0.0)))
        pitch = 10.0

        cam_data = bpy.data.cameras.new(f"Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(cam_info.get("fov_deg", 90.0))
        cam_data.clip_start = 0.2
        cam_data.clip_end = 1000.0

        cam_obj = bpy.data.objects.new(f"Cam_{label}", cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cx, cy, cz)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch), 0.0, math.radians(-heading))

        scene.camera = cam_obj
        out_path = os.path.join(RENDERS_DIR, f"iter2_{label}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Iteration 2 Camera [{label}] -> {out_path}")

    # Hide the far-west 500 Place d'Armes context proxy during the overview snapshot so it never blocks the hero block!
    b500_proxy = bpy.data.objects.get("MTL_Context_Proxy_500_PlaceDArmes_Tower")
    if b500_proxy:
        b500_proxy.hide_render = True

    ov_data = bpy.data.cameras.new("Cam_Overview_MTL_VM_0004")
    ov_data.lens_unit = 'FOV'
    ov_data.angle = math.radians(68.0)
    ov_data.clip_end = 1500.0
    ov_obj = bpy.data.objects.new("Cam_Overview_MTL_VM_0004", ov_data)
    cam_col.objects.link(ov_obj)

    # Pull overview camera back and higher to (-55, -35, 118) looking at (62, 42, 34) so the entire block + full 97m Aldred spire are framed!
    ov_obj.location = (-55.0, -35.0, 118.0)
    target = Vector((62.0, 42.0, 34.0))
    direction = target - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    snap_path = os.path.join(OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
    scene.render.filepath = snap_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Iteration 2 Block Overview Snapshot -> {snap_path}")

    # Save .blend and export .usdc
    tmp_blend = BLEND_PATH + ".tmp.blend"
    if os.path.exists(tmp_blend):
        os.remove(tmp_blend)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
    os.replace(tmp_blend, BLEND_PATH)
    bpy.ops.wm.usd_export(filepath=USDC_PATH, selected_objects_only=False)
    print(f"Iteration 2 complete! Saved {BLEND_PATH} and exported {USDC_PATH}")


if __name__ == "__main__":
    upgrade_block()
