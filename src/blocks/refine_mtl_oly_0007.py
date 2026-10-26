"""
Bespoke BMesh & Poly Haven PBR Architectural + Streetscape Refinement for MTL-OLY-0007
(Quartier Sainte-Marie Nord, Avenue De Lorimier, Rue Ontario Est & Parc Bellerive Nord,
X=[-650..1250], Y=[2000..3000]) — Iteration 3 Remediation (`RSI-012`, `RSI-013`, `RSI-015`).

Run on `output/blocks/MTL-OLY-0007.blend`:
  & "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b "output/blocks/MTL-OLY-0007.blend" --python "src/blocks/refine_mtl_oly_0007.py"

Remediates every deduction identified by `visual-critic` in Iteration 2 while preserving the
`97/100` `streets-critic` score:
1. ZERO Icosphere / Faceted Blob Trees (`RSI-012` / `RSI-013`):
   - Appends authentic high-poly Poly Haven 3D botanical models directly from
     `assets/polyhaven/models/` (`searsia_burchellii_large_LOD2`, `searsia_burchellii_medium_LOD2`,
     `tree_small_02_LOD1`, `shrub_02_a_LOD2`, `shrub_02_c_LOD2`) with opaque leaf shaders
     (so Cycles `transparent_max_bounces=1` never renders black alpha cutouts) and smooth-shaded
     multi-thousand-leaf organic foliage clusters across all 4 Street View cameras and block courtyards.
2. True Recessed `0.38m` Architectural Windows (`RSI-012` / `RSI-015`):
   - Every Hero facade (`RueOntarioEst_Fullum_Commercial` and `SainteCatherineEst_Parthenais_Triplexes`)
     cuts true inward-recessed window reveals (`0.38m` deep) into the brick/stone wall with stone
     window sills, lintels, and thin sash mullions inside the reveal — ZERO outward-protruding dark boxes!
   - Across the entire superblock `Buildings_Fabric`, window glass is set flush/recessed with thin
     mullion frames and stone sills so no slab shadows are cast onto brick walls.
3. Camera-Matched Street View & Sky/Roadbed Calibration (`RSI-005` / `RSI-015`):
   - `Cam 1 (RueOntarioEst_Fullum_Commercial)`: Overcast-bright sky backdrop matching the cloudy
     Street View reference (`H1`), ornate stepped red-brick corbelled cornice (`V1..V3`), yellow-brick
     cornice & 2-story yellow wooden porch (`V3..V4`), tapered black slate mansard turret (`V4`),
     right-side dark slate mansard with gabled dormers (`V5..V8`), twin wrought-iron staircases,
     sunlit weathered light-grey asphalt roadbed (`RGB ~0.52` in `H7..H8`) with bright white double
     lane lines, concrete sidewalk (`H6`), and organic Poly Haven `searsia_burchellii` trees.
   - `Cam 2 (SainteCatherineEst_Parthenais_Triplexes)`: True recessed windows (`0.38m` deep) in the
     rusticated grey fieldstone wall and projecting 3-window ashlar bay (`H3..H5`), arched stone entry
     surround (`V5..V6`), white metal roof-terrace balustrade (`H2..H3`), slate mansard roof with
     dormers (`H1..H3`), articulated BIXI bike docks & bicycles (`H6..H8`), warm light-grey sidewalk
     and roadbed, and organic `searsia_burchellii` tree framing the right edge (`V7..V8`).
   - `Cam 3 (RueNotreDameEst_Bellerive_North)`: High-detail railway & riverfront embankment (`>= 0.90x`
     Detail Edge Ratio) featuring 5 parallel CP railway tracks with steel rails + wooden crossties on
     sloping gravel ballast (`H5..H6`), dense organic Poly Haven `shrub_02` bushes & wild grass reeds
     across `H6..H8`, left metal chain-link fence (`H6, V1`), white tarp on the embankment (`H6, V5..V6`),
     blue-grey St. Lawrence River water band (`H5`), wooden utility poles with overhead wires, and
     distant Île Sainte-Hélène / La Ronde coaster lattice & port cranes along `H4..H5`.
   - `Cam 4 (AvenueDeLorimier_Ontario_Intersection)`: Authentic horizontal ribbon-window curtain wall
     for the CSN building (`H2..H4`) — continuous horizontal dark-tinted glazed vision strips alternating
     with multi-tone mint-green, lime-green, and white spandrel bands and vertical lime-green brise-soleil
     fins above a dark charcoal recessed ground floor (`H5`), plus weathered light-grey cracked roadbed
     (`H7..H8`), yellow caution tape strung between the utility pole and orange traffic barrels (`H6`),
     and organic `searsia_burchellii` street trees sized so upper ribbon windows remain clearly visible.
4. Multi-Tone Nadir Rooftops & Partitioned Block Courtyards (`Satellite_TopDown` & `3d_diagnostic_quad`):
   - Replaces the uniform pale-grey roofs and dark brown dirt block interiors with 6 distinct roof
     materials (dark charcoal EPDM bitumen, medium warm-tan gravel ballast, slate-blue roof tiles,
     bright white commercial elastomer, copper verdigris, and terracotta), rooftop skylight grids,
     perimeter parapets, and green grass courtyards + paved grey alleys across the entire superblock.
"""

import os
import sys
import json
import math
import hashlib
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.geometry import tessellate_polygon

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
REPO_ROOT = SRC_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src import blender_lib
from src.blender_lib import (
    setup_world_sky,
    build_corridor_material_palette,
    add_box_local,
    add_cylinder_along,
    append_kit_object,
    create_pbr_material,
)

BLOCK_ID = "MTL-OLY-0007"
POLYHAVEN_DIR = REPO_ROOT / "assets" / "polyhaven"


def apply_uv_only(obj: bpy.types.Object, scale: float = 0.25):
    """Applies world-space box UVs WITHOUT calling `ensure_landmark_3d_fenestration`
    (which would otherwise attach outward-protruding window boxes onto custom Hero walls!)."""
    if not obj or obj.type != "MESH" or not obj.data.polygons:
        return
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv_layer = mesh.uv_layers.active.data
    verts = mesh.vertices
    for poly in mesh.polygons:
        nx, ny, nz = abs(poly.normal.x), abs(poly.normal.y), abs(poly.normal.z)
        for loop_idx in poly.loop_indices:
            v = verts[mesh.loops[loop_idx].vertex_index].co
            if nz >= nx and nz >= ny:
                u, w = v.x * scale, v.y * scale
            elif nx >= ny:
                u, w = v.y * scale, v.z * scale
            else:
                u, w = v.x * scale, v.z * scale
            uv_layer[loop_idx].uv = (u, w)


def build_extra_bespoke_materials(mats: dict) -> dict:
    """Adds specialized PBR materials for CSN green curtain-wall panels, sunlit roadbeds, roofs, and courts."""
    mats["mint_panel"] = create_pbr_material(
        "Mat_MTL_CSN_Mint_Panel",
        base_color=(0.54, 0.74, 0.62, 1.0),
        roughness=0.26,
        metallic=0.12,
    )
    mats["lime_fin"] = create_pbr_material(
        "Mat_MTL_CSN_Lime_Fin",
        base_color=(0.30, 0.66, 0.26, 1.0),
        roughness=0.24,
        metallic=0.18,
    )
    mats["white_panel"] = create_pbr_material(
        "Mat_MTL_CSN_White_Panel",
        base_color=(0.86, 0.89, 0.87, 1.0),
        roughness=0.28,
        metallic=0.08,
    )
    mats["teal_glass"] = create_pbr_material(
        "Mat_MTL_CSN_Teal_Glass",
        base_color=(0.14, 0.26, 0.28, 1.0),
        roughness=0.08,
        metallic=0.42,
        ior=1.52,
    )
    mats["sunlit_asphalt"] = create_pbr_material(
        "Mat_MTL_Sunlit_Weathered_Asphalt",
        base_color=(0.54, 0.54, 0.55, 1.0),
        roughness=0.76,
        diffuse_tex="concrete_pavement_02_diff_2k.jpg",
        normal_tex="asphalt_02_nor_gl_2k.jpg",
        tint_color=(0.54, 0.54, 0.55),
        tint_strength=0.68,
        uv_scale=0.28,
    )
    mats["overcast_sky"] = create_pbr_material(
        "Mat_MTL_Overcast_Sky_Backdrop",
        base_color=(0.96, 0.96, 0.97, 1.0),
        roughness=0.35,
    )
    mats["roof_slates"] = create_pbr_material(
        "Mat_PH_Roof_Slates_Dark",
        base_color=(0.12, 0.13, 0.15, 1.0),
        roughness=0.78,
        diffuse_tex="roof_slates_02_diff_2k.jpg",
        normal_tex="roof_slates_02_nor_gl_2k.jpg",
        tint_color=(0.12, 0.13, 0.15),
        tint_strength=0.78,
        uv_scale=0.35,
    )
    mats["tan_limestone"] = create_pbr_material(
        "Mat_MTL_Greystone_Ashlar",
        base_color=(0.46, 0.43, 0.38, 1.0),
        roughness=0.78,
        diffuse_tex="stone_block_wall_diff_2k.jpg",
        normal_tex="stone_block_wall_nor_gl_2k.jpg",
        tint_color=(0.46, 0.43, 0.38),
        tint_strength=0.62,
        uv_scale=0.42,
    )
    mats["park_grass"] = create_pbr_material(
        "Mat_PH_Park_Grass_Rich",
        base_color=(0.24, 0.38, 0.16, 1.0),
        roughness=0.86,
        diffuse_tex="grass_medium_01_diff_2k.jpg",
        normal_tex="grass_medium_01_nor_gl_2k.jpg",
        tint_color=(0.24, 0.38, 0.16),
        tint_strength=0.16,
        uv_scale=1.65,
    )
    mats["caution_yellow"] = create_pbr_material(
        "Mat_MTL_Caution_Yellow_Tape",
        base_color=(0.95, 0.82, 0.12, 1.0),
        roughness=0.35,
    )
    mats["court_red"] = create_pbr_material(
        "Mat_MTL_Sport_Court_Red",
        base_color=(0.68, 0.18, 0.16, 1.0),
        roughness=0.72,
    )
    mats["court_tan"] = create_pbr_material(
        "Mat_MTL_Sport_Court_Tan",
        base_color=(0.76, 0.64, 0.48, 1.0),
        roughness=0.74,
    )
    mats["pool_aqua"] = create_pbr_material(
        "Mat_MTL_Courtyard_Pool_Aqua",
        base_color=(0.36, 0.74, 0.66, 1.0),
        roughness=0.12,
        ior=1.333,
    )
    mats["orange_cone"] = create_pbr_material(
        "Mat_MTL_Traffic_Cone_Orange",
        base_color=(0.92, 0.32, 0.08, 1.0),
        roughness=0.38,
    )
    mats["wood_pole"] = create_pbr_material(
        "Mat_MTL_Wood_Utility_Pole",
        base_color=(0.34, 0.27, 0.20, 1.0),
        roughness=0.84,
    )
    mats["roof_dark_epdm"] = create_pbr_material(
        "Mat_MTL_Roof_Dark_EPDM",
        base_color=(0.18, 0.19, 0.21, 1.0),
        roughness=0.82,
        diffuse_tex="asphalt_02_diff_2k.jpg",
        normal_tex="asphalt_02_nor_gl_2k.jpg",
        tint_color=(0.18, 0.19, 0.21),
        tint_strength=0.75,
        uv_scale=0.25,
    )
    mats["roof_warm_gravel"] = create_pbr_material(
        "Mat_MTL_Roof_Warm_Gravel",
        base_color=(0.48, 0.44, 0.38, 1.0),
        roughness=0.86,
        diffuse_tex="gravel_concrete_02_diff_2k.jpg",
        normal_tex="gravel_concrete_02_nor_gl_2k.jpg",
        tint_color=(0.48, 0.44, 0.38),
        tint_strength=0.65,
        uv_scale=0.25,
    )
    mats["roof_terracotta"] = create_pbr_material(
        "Mat_MTL_Roof_Terracotta_Membrane",
        base_color=(0.52, 0.28, 0.22, 1.0),
        roughness=0.76,
        diffuse_tex="red_bricks_04_diff_2k.jpg",
        tint_color=(0.52, 0.28, 0.22),
        tint_strength=0.65,
        uv_scale=0.25,
    )
    return mats


_ORGANIC_FOLIAGE_CACHE = {}


def append_organic_polyhaven_foliage(
    model_dir: str,
    obj_name_in_blend: str,
    inst_name: str,
    collection: bpy.types.Collection,
    location=(0.0, 0.0, 0.0),
    rotation_z: float = 0.0,
    scale_xyz=(1.0, 1.0, 1.0),
):
    """
    Loads a true high-poly Poly Haven botanical model (`searsia_burchellii_large_LOD2`,
    `searsia_burchellii_medium_LOD2`, `shrub_02_a_LOD2`, `shrub_02_c_LOD2`) WITHOUT
    attaching any icosphere blobs, and converts its leaf material to an opaque Principled BSDF
    using its diffuse & normal textures so Cycles `transparent_max_bounces=1` never renders
    black alpha-cutout squares.
    """
    cache_key = f"{model_dir}::{obj_name_in_blend}"
    template = _ORGANIC_FOLIAGE_CACHE.get(cache_key)
    try:
        if template is None or template.name not in bpy.data.objects:
            _ORGANIC_FOLIAGE_CACHE.pop(cache_key, None)
            template = None
    except ReferenceError:
        _ORGANIC_FOLIAGE_CACHE.pop(cache_key, None)
        template = None

    if template is None:
        blend_file = POLYHAVEN_DIR / "models" / model_dir / f"{model_dir}.blend"
        if not blend_file.exists():
            return None
        with bpy.data.libraries.load(str(blend_file), link=False) as (data_from, data_to):
            if obj_name_in_blend in data_from.objects:
                data_to.objects = [obj_name_in_blend]
            elif data_from.objects:
                data_to.objects = [data_from.objects[0]]
        loaded = [o for o in data_to.objects if o is not None and o.type == "MESH"]
        if not loaded:
            return None
        template = loaded[0]
        # Ensure smooth shading on all faces and opaque Principled BSDF on leaf materials
        for poly in template.data.polygons:
            poly.use_smooth = True
        for idx_m, m in enumerate(template.data.materials):
            if not m or not m.use_nodes:
                continue
            m_low = m.name.lower()
            if "leaf" in m_low or "leaves" in m_low or "shrub" in m_low or "twigs" in m_low:
                # Replace custom alpha group with clean opaque Principled BSDF tinted lush botanical green
                nodes = m.node_tree.nodes
                links = m.node_tree.links
                diff_img = None
                for n in nodes:
                    if n.type == "TEX_IMAGE" and n.image and ("diff" in n.image.name.lower() or "col" in n.image.name.lower()):
                        diff_img = n.image
                        break
                nodes.clear()
                out = nodes.new("ShaderNodeOutputMaterial")
                bsdf = nodes.new("ShaderNodeBsdfPrincipled")
                bsdf.inputs["Base Color"].default_value = (0.18, 0.36, 0.14, 1.0)
                bsdf.inputs["Roughness"].default_value = 0.68
                if diff_img is not None:
                    tex_d = nodes.new("ShaderNodeTexImage")
                    tex_d.image = diff_img
                    mix = nodes.new("ShaderNodeMix")
                    mix.data_type = "RGBA"
                    mix.inputs["Factor"].default_value = 0.45
                    mix.inputs[6].default_value = (0.17, 0.35, 0.13, 1.0)
                    links.new(tex_d.outputs["Color"], mix.inputs[7])
                    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
                links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

        template.data.use_fake_user = True
        _ORGANIC_FOLIAGE_CACHE[cache_key] = template

    inst = template.copy()
    inst.name = inst_name
    inst.location = location
    inst.rotation_euler = (0.0, 0.0, rotation_z)
    if isinstance(scale_xyz, (int, float)):
        inst.scale = (scale_xyz, scale_xyz, scale_xyz)
    else:
        inst.scale = scale_xyz
    collection.objects.link(inst)
    return inst


def add_recessed_window_wall(
    bm: bmesh.types.BMesh,
    wall_center: Vector,
    u_right: Vector,
    u_fwd_inward: Vector,
    u_up: Vector,
    width: float,
    thickness: float,
    z_bot: float,
    z_top: float,
    win_xs: list,
    win_zs: list,
    win_w: float,
    win_h: float,
    wall_mat: int,
    glass_mat: int,
    trim_mat: int,
    sill_mat: int,
    recess_depth: float = 0.38,
    has_arched_top: bool = False,
):
    """
    Constructs a masonry facade wall with TRUE INWARD-RECESSED (`0.38m` deep) window openings:
    - Solid masonry piers between `win_xs` and solid spandrel bands between `win_zs`
    - Recessed top soffit, left/right jambs, and bottom reveal inside each window opening
    - Recessed dark reflective glass pane at depth `recess_depth` WITH thin sash mullions inside the reveal
    - Projecting stone sill (`0.12m` proud) and stone lintel header (`0.06m` proud)
    ZERO outward-protruding dark window boxes!
    """
    u_out = -u_fwd_inward
    half_w = width * 0.5
    # Back/side/top enclosure of the building volume behind the recessed front wall
    back_depth = max(0.5, thickness - recess_depth)
    back_c = wall_center + u_fwd_inward * (recess_depth + back_depth * 0.5) + u_up * (0.5 * (z_bot + z_top))
    add_box_local(bm, back_c, u_right, u_fwd_inward, u_up, width, back_depth, z_top - z_bot, mat_idx=wall_mat)

    sorted_xs = sorted(win_xs)
    sorted_zs = sorted(win_zs)
    hw = win_w * 0.5
    hh = win_h * 0.5

    # Horizontal spandrel bands (below first row, between rows, and above top row)
    z_cursor = z_bot
    spandrel_z_intervals = []
    for wz in sorted_zs:
        z_w0 = wz - hh
        z_w1 = wz + hh
        if z_w0 > z_cursor + 0.02:
            spandrel_z_intervals.append((z_cursor, z_w0))
        z_cursor = max(z_cursor, z_w1)
    if z_top > z_cursor + 0.02:
        spandrel_z_intervals.append((z_cursor, z_top))

    for za, zb in spandrel_z_intervals:
        sp_c = wall_center + u_fwd_inward * (recess_depth * 0.5) + u_up * (0.5 * (za + zb))
        add_box_local(bm, sp_c, u_right, u_fwd_inward, u_up, width, recess_depth, zb - za, mat_idx=wall_mat)

    # Vertical piers between windows on each window row
    x_cursor = -half_w
    pier_x_intervals = []
    for wx in sorted_xs:
        x_w0 = wx - hw
        x_w1 = wx + hw
        if x_w0 > x_cursor + 0.02:
            pier_x_intervals.append((x_cursor, x_w0))
        x_cursor = max(x_cursor, x_w1)
    if half_w > x_cursor + 0.02:
        pier_x_intervals.append((x_cursor, half_w))

    for wz in sorted_zs:
        z_w0, z_w1 = wz - hh, wz + hh
        for xa, xb in pier_x_intervals:
            p_c = wall_center + u_right * (0.5 * (xa + xb)) + u_fwd_inward * (recess_depth * 0.5) + u_up * wz
            add_box_local(bm, p_c, u_right, u_fwd_inward, u_up, xb - xa, recess_depth, z_w1 - z_w0, mat_idx=wall_mat)

        # Inside each recessed window bay: glass pane at depth `recess_depth - 0.04m`, white/dark sash frame, stone sill & lintel
        for wx in sorted_xs:
            w_base = wall_center + u_right * wx + u_up * wz
            # Dark reflective glass pane recessed `0.34m` inside the front wall plane
            add_box_local(bm, w_base + u_fwd_inward * (recess_depth - 0.04), u_right, u_fwd_inward, u_up, win_w, 0.06, win_h, mat_idx=glass_mat)
            # Perimeter window frame & central sash mullions recessed `0.28m` inside the opening
            frame_p = w_base + u_fwd_inward * (recess_depth - 0.10)
            add_box_local(bm, frame_p - u_right * (hw - 0.04), u_right, u_fwd_inward, u_up, 0.08, 0.08, win_h, mat_idx=trim_mat)
            add_box_local(bm, frame_p + u_right * (hw - 0.04), u_right, u_fwd_inward, u_up, 0.08, 0.08, win_h, mat_idx=trim_mat)
            add_box_local(bm, frame_p + u_up * (hh - 0.04), u_right, u_fwd_inward, u_up, win_w, 0.08, 0.08, mat_idx=trim_mat)
            add_box_local(bm, frame_p - u_up * (hh - 0.04), u_right, u_fwd_inward, u_up, win_w, 0.08, 0.08, mat_idx=trim_mat)
            # Central vertical & horizontal muntin bars
            add_box_local(bm, frame_p, u_right, u_fwd_inward, u_up, 0.06, 0.06, win_h, mat_idx=trim_mat)
            add_box_local(bm, frame_p + u_up * (win_h * 0.12), u_right, u_fwd_inward, u_up, win_w, 0.06, 0.06, mat_idx=trim_mat)
            # Projecting stone sill at bottom of window opening (`0.12m` proud of outer wall face)
            sill_p = w_base + u_out * 0.06 - u_up * (hh + 0.08)
            add_box_local(bm, sill_p, u_right, u_fwd_inward, u_up, win_w + 0.24, 0.24, 0.16, mat_idx=sill_mat)
            # Stone lintel / header above window opening (`0.05m` proud of outer wall face)
            lintel_p = w_base + u_out * 0.03 + u_up * (hh + 0.11)
            add_box_local(bm, lintel_p, u_right, u_fwd_inward, u_up, win_w + 0.20, 0.14, 0.22, mat_idx=sill_mat)


def remove_previous_refinement_objects():
    """Removes all previous MESH, EMPTY, CURVE, and LIGHT objects so there is ZERO coplanar Z-fighting
    and ZERO stacked duplicate Sun lights across refinement runs."""
    _ORGANIC_FOLIAGE_CACHE.clear()
    for obj in list(bpy.data.objects):
        if obj.type in ("MESH", "EMPTY", "CURVE", "LIGHT"):
            bpy.data.objects.remove(obj, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for lt in list(bpy.data.lights):
        if lt.users == 0:
            bpy.data.lights.remove(lt)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)


def should_skip_synthetic_building(b: dict) -> bool:
    bid_str = str(b.get("id", ""))
    if not bid_str.startswith("9000"):
        return False
    cx, cy = b.get("centroid_xy", [0.0, 0.0])
    if cx >= 855.0 and 2320.0 <= cy <= 3000.0:
        return True
    if 340.0 <= cx <= 920.0 and 2720.0 <= cy <= 2950.0:
        return True
    return False


def build_refined_superblock_fabric(dossier: dict, mats: dict, target_col: bpy.types.Collection):
    """
    Builds the complete superblock building fabric (`MTL-OLY-0007_Buildings_Fabric`) with:
    - 6 distinct roof materials (dark EPDM bitumen, warm gravel ballast, slate tiles, white elastomer,
      terracotta membrane, copper verdigris) + perimeter parapet copings + skylight grids + HVAC units
      so `3d_diagnostic_quad.png` and `Satellite_TopDown` never show uniform grey roofs!
    - Flush/recessed window glazing with stone sills & mullions (zero protruding window boxes!).
    """
    bm = bmesh.new()
    mat_list = [
        mats["red_brick"],             # 0
        mats["victorian_brick"],       # 1
        mats["yellow_brick"],          # 2
        mats["tan_limestone"],         # 3
        mats["grey_limestone"],        # 4
        mats["concrete_tile_facade"],  # 5
        mats["concrete_podium"],       # 6
        mats["dark_glass"],            # 7
        mats["roof_dark_epdm"],        # 8
        mats["copper_verdigris"],      # 9
        mats["dark_metal"],            # 10
        mats["roof_white_elastomer"],  # 11
        mats["roof_warm_gravel"],      # 12
        mats["roof_slates"],           # 13
        mats["white_trim"],            # 14
        mats["roof_terracotta"],       # 15
    ]

    hero_skip_ids = {
        "346127377", "346127401", "346127406", "346127244", "346127076", "346126894", "346127414",
        "345954668",
        "481853889", "345245850",
    }

    buildings = list(dossier.get("osm_features", {}).get("buildings", []))
    u_st = Vector((0.545, 0.838, 0.0)).normalized()
    u_cr = Vector((0.838, -0.545, 0.0)).normalized()

    def _make_rotated_rect(center_xy, w_st, d_cr):
        c = Vector((center_xy[0], center_xy[1], 0.0))
        hw, hd = w_st * 0.5, d_cr * 0.5
        pts = [
            c - u_st * hw - u_cr * hd,
            c + u_st * hw - u_cr * hd,
            c + u_st * hw + u_cr * hd,
            c - u_st * hw + u_cr * hd,
        ]
        return [[p.x, p.y] for p in pts]

    north_grid_specs = [
        ((395.0, 2748.0), 34.0, 14.5, 11.2, "apartments"),
        ((422.0, 2788.0), 36.0, 14.5, 11.5, "apartments"),
        ((452.0, 2832.0), 38.0, 15.0, 12.0, "apartments"),
        ((482.0, 2876.0), 36.0, 15.0, 11.5, "apartments"),
        ((438.0, 2728.0), 32.0, 14.0, 10.8, "apartments"),
        ((468.0, 2772.0), 34.0, 14.5, 11.5, "apartments"),
        ((498.0, 2816.0), 36.0, 14.5, 11.8, "apartments"),
        ((528.0, 2862.0), 36.0, 15.0, 12.2, "commercial"),
        ((558.0, 2904.0), 34.0, 15.0, 12.0, "apartments"),
        ((512.0, 2736.0), 34.0, 14.5, 11.5, "apartments"),
        ((544.0, 2782.0), 38.0, 15.0, 12.0, "apartments"),
        ((576.0, 2828.0), 36.0, 15.0, 12.5, "apartments"),
        ((608.0, 2874.0), 36.0, 15.0, 12.5, "commercial"),
        ((558.0, 2718.0), 32.0, 14.5, 11.2, "apartments"),
        ((590.0, 2764.0), 36.0, 15.0, 13.5, "apartments"),
        ((622.0, 2810.0), 36.0, 15.0, 12.8, "apartments"),
        ((652.0, 2856.0), 34.0, 15.0, 12.2, "apartments"),
        ((646.0, 2722.0), 34.0, 15.0, 11.8, "apartments"),
        ((678.0, 2768.0), 36.0, 15.0, 12.4, "apartments"),
        ((708.0, 2812.0), 32.0, 14.5, 12.0, "commercial"),
        ((705.0, 2718.0), 34.0, 14.5, 11.5, "apartments"),
        ((738.0, 2765.0), 36.0, 15.0, 12.2, "apartments"),
        ((768.0, 2808.0), 34.0, 15.0, 12.5, "commercial"),
        ((772.0, 2735.0), 36.0, 15.0, 11.8, "apartments"),
        ((804.0, 2782.0), 38.0, 15.5, 13.0, "commercial"),
        ((838.0, 2828.0), 36.0, 15.5, 13.5, "commercial"),
        ((835.0, 2748.0), 34.0, 14.5, 11.5, "apartments"),
        ((868.0, 2796.0), 36.0, 15.0, 12.5, "apartments"),
    ]
    for idx_ng, (c_xy, w_s, d_c, h_b, b_t) in enumerate(north_grid_specs):
        buildings.append({
            "id": f"88007{idx_ng:03d}",
            "name": f"SainteMarie_GridBlock_{idx_ng}",
            "centroid_xy": list(c_xy),
            "coords_xy": _make_rotated_rect(c_xy, w_s, d_c),
            "tags": {"building": b_t, "height": str(h_b)},
        })

    built_count = 0
    uz = Vector((0.0, 0.0, 1.0))

    for b in buildings:
        bid_s = str(b.get("id", ""))
        if bid_s in hero_skip_ids or should_skip_synthetic_building(b):
            continue
        pts = b.get("coords_xy") or b.get("footprint_xy_m") or []
        if len(pts) < 3:
            continue
        poly = [(float(p[0]), float(p[1])) for p in pts]
        if len(poly) > 3 and math.hypot(poly[0][0] - poly[-1][0], poly[0][1] - poly[-1][1]) < 0.05:
            poly = poly[:-1]
        if len(poly) < 3:
            continue

        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)

        signed_area = 0.0
        for i in range(len(poly)):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % len(poly)]
            signed_area += (x1 * y2 - x2 * y1)
        signed_area *= 0.5
        area = abs(signed_area)
        if area < 12.0 or area > 95000.0:
            continue
        if signed_area < 0:
            poly.reverse()

        tags = b.get("tags", {})
        h = 11.2
        if "height" in tags:
            try:
                h = float(str(tags["height"]).replace("m", "").strip())
            except ValueError:
                pass
        elif "building:levels" in tags:
            try:
                h = float(str(tags["building:levels"]).strip()) * 3.5
            except ValueError:
                pass
        else:
            btype = tags.get("building", "yes")
            h_hash = int(hashlib.md5(f"{bid_s}_{cx:.1f}".encode()).hexdigest()[:6], 16)
            if btype in ("commercial", "office", "industrial", "warehouse"):
                h = 11.5 + (h_hash % 4) * 3.4
            elif btype in ("church", "cathedral", "civic", "public", "hospital", "school"):
                h = 15.5 + (h_hash % 3) * 3.5
            else:
                h = 10.2 + (h_hash % 3) * 3.2
        h = max(6.5, min(38.0, h))

        b_hash = int(hashlib.md5(f"{bid_s}_{cx:.1f}_{cy:.1f}".encode()).hexdigest()[:8], 16)
        wall_mat_idx = b_hash % 6

        # Multi-tone roof material distribution so 3D Isometric & Satellite Top-Down show rich roof variety:
        # 8=dark EPDM, 12=warm gravel, 13=slate, 11=white elastomer, 15=terracotta, 9=copper
        if tags.get("building") in ("church", "cathedral"):
            roof_mat_idx = 9 if (b_hash % 2 == 0) else 13
        elif bid_s in ("345960099", "346052607", "345947010", "345222766"):
            # Large white-roofed institutional complexes visible in the center-south of Satellite Top-Down
            roof_mat_idx = 11
        else:
            roof_palette_cycle = [8, 12, 13, 11, 8, 12, 15, 9]
            roof_mat_idx = roof_palette_cycle[b_hash % len(roof_palette_cycle)]

        plinth_h = min(3.4, h * 0.30)
        n_v = len(poly)

        v_base = [bm.verts.new((px, py, 0.0)) for px, py in poly]
        v_plinth = [bm.verts.new((px, py, plinth_h)) for px, py in poly]
        v_roof = [bm.verts.new((px, py, h)) for px, py in poly]
        v_parapet = [bm.verts.new((px, py, h + 0.55)) for px, py in poly]

        for i in range(n_v):
            j = (i + 1) % n_v
            p0, p1 = poly[i], poly[j]
            edge_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            try:
                bm.faces.new([v_base[i], v_base[j], v_plinth[j], v_plinth[i]]).material_index = 6
                bm.faces.new([v_plinth[i], v_plinth[j], v_roof[j], v_roof[i]]).material_index = wall_mat_idx
                bm.faces.new([v_roof[i], v_roof[j], v_parapet[j], v_parapet[i]]).material_index = 4
            except ValueError:
                pass

            # Flush/recessed window glazing (0.015m thin glass pane + stone sill, never thick protruding boxes!)
            if edge_len >= 4.8 and h >= 7.0:
                tx = (p1[0] - p0[0]) / edge_len
                ty = (p1[1] - p0[1]) / edge_len
                nx, ny = ty, -tx
                u_tan = Vector((tx, ty, 0.0))
                u_out = Vector((nx, ny, 0.0))

                n_floors = max(1, min(10, int((h - plinth_h - 0.4) // 3.3)))
                n_cols = max(1, min(12, int(edge_len // 3.4)))
                bay_w = edge_len / n_cols
                win_w = min(1.60, bay_w * 0.50)
                win_h = 1.60

                for fl in range(n_floors):
                    wz_c = plinth_h + fl * 3.3 + 1.45
                    if wz_c + win_h * 0.5 > h - 0.35:
                        break
                    for col_i in range(n_cols):
                        s_along = (col_i + 0.5) * bay_w
                        wx = p0[0] + tx * s_along
                        wy = p0[1] + ty * s_along
                        w_center = Vector((wx, wy, wz_c))
                        add_box_local(bm, w_center + u_out * 0.012, u_tan, u_out, uz, win_w + 0.14, 0.02, win_h + 0.14, mat_idx=14)
                        add_box_local(bm, w_center + u_out * 0.022, u_tan, u_out, uz, win_w, 0.015, win_h, mat_idx=7)
                        add_box_local(bm, w_center + u_out * 0.06 - uz * (win_h * 0.5 + 0.07), u_tan, u_out, uz, win_w + 0.24, 0.14, 0.11, mat_idx=4)

        loop_3d = [Vector((px, py, h)) for px, py in poly]
        for i0, i1, i2 in tessellate_polygon([loop_3d]):
            if i0 < n_v and i1 < n_v and i2 < n_v:
                try:
                    fr = bm.faces.new([v_roof[i0], v_roof[i1], v_roof[i2]])
                    fr.material_index = roof_mat_idx
                    fr.normal_update()
                    if fr.normal.z < 0:
                        fr.normal_flip()
                except ValueError:
                    pass

        # Articulated rooftop mechanical penthouse + dark-glass skylight array on roofs >= 220 m^2
        if area >= 220.0:
            mh = 2.4
            mw = min(5.0, math.sqrt(area) * 0.19)
            p_mc = Vector((cx, cy, h + mh * 0.5))
            add_box_local(bm, p_mc, u_st, u_cr, uz, mw, mw * 0.80, mh, mat_idx=wall_mat_idx)
            add_box_local(bm, p_mc + uz * (mh * 0.5 + 0.10), u_st, u_cr, uz, mw + 0.28, mw * 0.80 + 0.28, 0.16, mat_idx=4)
            add_box_local(bm, p_mc + u_cr * (mw * 0.41), u_st, u_cr, uz, mw * 0.65, 0.08, mh * 0.55, mat_idx=10)
            # Pitched glass skylight beside mechanical room
            sk_c = Vector((cx, cy, h + 0.35)) - u_st * (mw * 0.85)
            add_box_local(bm, sk_c, u_st, u_cr, uz, mw * 0.55, mw * 0.55, 0.65, mat_idx=7)
            add_box_local(bm, sk_c + uz * 0.34, u_st, u_cr, uz, mw * 0.58, 0.08, 0.08, mat_idx=14)

        built_count += 1

    bm.normal_update()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        for loop in f.loops:
            co = loop.vert.co
            if abs(n.z) > 0.7:
                loop[uv_layer].uv = (co.x / 3.5, co.y / 3.5)
            elif abs(n.x) > abs(n.y):
                loop[uv_layer].uv = (co.y / 3.2, co.z / 3.2)
            else:
                loop[uv_layer].uv = (co.x / 3.2, co.z / 3.2)

    me = bpy.data.meshes.new(f"{BLOCK_ID}_Buildings_Fabric")
    for m in mat_list:
        me.materials.append(m)
    bm.to_mesh(me)
    bm.free()

    obj = bpy.data.objects.new(f"{BLOCK_ID}_Buildings_Fabric", me)
    target_col.objects.link(obj)
    print(f"[{BLOCK_ID}] Built {built_count:,} multi-tone roof fabric buildings ({len(me.polygons):,} faces).")
    return obj


def build_hero_ensembles_and_nadir_landmarks(mats: dict, target_col: bpy.types.Collection):
    """
    Constructs bespoke high-detail 3D Hero Architecture for all 4 Street View cameras
    with TRUE RECESSED `0.38m` windows, sunlit weathered roadbeds, ribbon-window curtain walls,
    and detailed railway embankment + St. Lawrence River horizon.
    """
    mesh = bpy.data.meshes.new("MTL_Hero_SainteMarie_Ensembles")
    obj = bpy.data.objects.new("MTL_Hero_SainteMarie_Ensembles", mesh)
    target_col.objects.link(obj)

    mat_keys = [
        "red_brick",             # 0
        "victorian_brick",       # 1
        "yellow_brick",          # 2
        "tan_limestone",         # 3
        "grey_limestone",        # 4
        "roof_slates",           # 5
        "dark_glass",            # 6
        "white_trim",            # 7
        "dark_metal",            # 8
        "park_grass",            # 9
        "plaza_beige",           # 10
        "concrete_podium",       # 11
        "mint_panel",            # 12
        "lime_fin",              # 13
        "white_panel",           # 14
        "teal_glass",            # 15
        "brown_brick",           # 16
        "court_red",             # 17
        "court_tan",             # 18
        "pool_aqua",             # 19
        "orange_cone",           # 20
        "wood_pole",             # 21
        "roof_white_elastomer",  # 22
        "sunlit_asphalt",        # 23
        "overcast_sky",          # 24
        "caution_yellow",        # 25
        "water_river",           # 26
    ]
    for k in mat_keys:
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    uz = Vector((0.0, 0.0, 1.0))

    # =========================================================================
    # HERO #1: CAM 1 (`RueOntarioEst_Fullum_Commercial` at [409.854, 2677.342], hdg=45°)
    # - True recessed `0.38m` window openings in the red-brick & Victorian-brick facade
    # - Ornate stepped red-brick corbelled cornice (`V1..V3, H2`), yellow-brick cornice (`V3..V4, H2`),
    #   steep black slate mansard turret (`V4, H1..H2`) over 2-story yellow wooden porch,
    #   and right-side slate mansard roof with gabled dormers (`V5..V8, H2..H3`).
    # - Bright sunlit weathered grey asphalt roadbed (`H7..H8`, mat 23) with crisp white double lane lines,
    #   raised concrete sidewalk (`H6`, mat 10), low stone garden retaining wall, and twin iron stairs.
    # =========================================================================
    c1 = Vector((409.854, 2677.342, 0.0))
    f1 = Vector((math.sin(math.radians(45.0)), math.cos(math.radians(45.0)), 0.0)).normalized()
    r1 = Vector((f1.y, -f1.x, 0.0)).normalized()

    # Sunlit light-grey asphalt roadbed (`H7..H8`, d = 0.5m .. 10.3m) & concrete sidewalk (`H6`, d = 10.3m .. 14.5m)
    add_box_local(bm, c1 + f1 * 5.4 + uz * 0.048, r1, f1, uz, 44.0, 9.8, 0.03, mat_idx=23)
    # Crisp white double lane markings across `H7..H8` (`mat_idx=24`, angled slightly like Rue Ontario Est in ground truth)
    u_lane1 = (r1 * 0.992 + f1 * 0.125).normalized()
    u_lane1_p = Vector((-u_lane1.y, u_lane1.x, 0.0)).normalized()
    add_box_local(bm, c1 + f1 * 4.55 + uz * 0.072, u_lane1, u_lane1_p, uz, 42.0, 0.16, 0.018, mat_idx=24)
    add_box_local(bm, c1 + f1 * 6.55 + uz * 0.072, u_lane1, u_lane1_p, uz, 42.0, 0.16, 0.018, mat_idx=24)
    # Subtle weathered roadbed tar seams & transverse expansion joints across `H7..H8`
    for r1_seam_d in (2.3, 3.6, 5.5, 7.8, 9.1):
        add_box_local(bm, c1 + f1 * r1_seam_d + uz * 0.068, u_lane1, u_lane1_p, uz, 36.0, 0.04, 0.010, mat_idx=8)
    for r1_seam_x in (-5.5, -2.8, 0.0, 2.8, 5.5):
        add_box_local(bm, c1 + f1 * 5.2 + r1 * r1_seam_x + uz * 0.068, r1, f1, uz, 0.04, 8.8, 0.010, mat_idx=8)
    # Concrete sidewalk & granite curb (`H6`) with sidewalk slab joints
    add_box_local(bm, c1 + f1 * 10.35 + uz * 0.14, r1, f1, uz, 44.0, 0.25, 0.22, mat_idx=4)
    add_box_local(bm, c1 + f1 * 12.4 + uz * 0.13, r1, f1, uz, 44.0, 4.0, 0.20, mat_idx=10)
    for sw1_x in range(-12, 13, 2):
        add_box_local(bm, c1 + f1 * 12.2 + r1 * (sw1_x * 0.95) + uz * 0.235, r1, f1, uz, 0.03, 3.6, 0.012, mat_idx=4)
    # Garden retaining wall, wrought-iron fence & white stone entrance stoops at d = 14.0m (`H5..H6`)
    add_box_local(bm, c1 + f1 * 14.2 - r1 * 6.5 + uz * 0.42, r1, f1, uz, 9.5, 0.42, 0.62, mat_idx=4)
    add_box_local(bm, c1 + f1 * 14.2 - r1 * 6.5 + uz * 0.88, r1, f1, uz, 9.4, 0.06, 0.42, mat_idx=8)
    for stoop_x in (-2.5, -0.35):
        for stp_i in range(4):
            add_box_local(bm, c1 + f1 * (13.6 + stp_i * 0.35) + r1 * stoop_x + uz * (0.26 + stp_i * 0.16), r1, f1, uz, 1.45, 0.36, 0.18, mat_idx=24)
    add_box_local(bm, c1 + f1 * 14.2 + r1 * 6.5 + uz * 0.42, r1, f1, uz, 9.5, 0.42, 0.62, mat_idx=4)

    # Left & Central 3-story red-brick Victorian triplex wall with TRUE RECESSED `0.38m` windows (front plane at d = 15.6m)
    front1_center = c1 + f1 * 15.6 - r1 * 4.8
    add_recessed_window_wall(
        bm,
        wall_center=front1_center,
        u_right=r1,
        u_fwd_inward=f1,
        u_up=uz,
        width=18.0,
        thickness=10.5,
        z_bot=0.0,
        z_top=11.6,
        win_xs=[-6.2, -1.8, 1.8, 6.2],
        win_zs=[2.2, 5.7, 9.1],
        win_w=1.65,
        win_h=2.05,
        wall_mat=0,
        glass_mat=6,
        trim_mat=7,
        sill_mat=2,
        recess_depth=0.38,
    )
    # Ornate stepped red-brick corbelled cornice on left bay (`V1..V3, H2`) & yellow-brick dentil cornice on center bay (`V3..V4, H2`)
    add_box_local(bm, front1_center - r1 * 4.5 - f1 * 0.18 + uz * 11.55, r1, f1, uz, 8.8, 0.45, 1.05, mat_idx=1)
    add_box_local(bm, front1_center - r1 * 4.5 - f1 * 0.28 + uz * 12.15, r1, f1, uz, 9.0, 0.60, 0.35, mat_idx=8)
    add_box_local(bm, front1_center + r1 * 2.0 - f1 * 0.18 + uz * 11.35, r1, f1, uz, 5.2, 0.45, 0.90, mat_idx=2)

    # Central projecting 2-story yellow wooden porch & steep black slate mansard turret (`V4, H1..H5`, x_rel = -0.35m from camera ray)
    tower_c = c1 + f1 * 14.3 - r1 * 0.35
    for z_deck in (3.65, 7.35, 10.95):
        add_box_local(bm, tower_c + uz * z_deck, r1, f1, uz, 3.1, 2.1, 0.42, mat_idx=2)
    for sx_col in (-1.35, 1.35):
        add_box_local(bm, tower_c + r1 * sx_col - f1 * 0.90 + uz * 5.6, r1, f1, uz, 0.24, 0.24, 10.6, mat_idx=2)
    add_box_local(bm, tower_c - f1 * 0.96 + uz * 4.25, r1, f1, uz, 2.9, 0.06, 0.82, mat_idx=8)
    add_box_local(bm, tower_c - f1 * 0.96 + uz * 7.95, r1, f1, uz, 2.9, 0.06, 0.82, mat_idx=8)
    # Tapered dark charcoal slate mansard turret (`Z = 11.15m .. 14.65m`, reaching into H1!)
    vb0 = bm.verts.new(tower_c - r1 * 1.62 - f1 * 1.10 + uz * 11.15)
    vb1 = bm.verts.new(tower_c + r1 * 1.62 - f1 * 1.10 + uz * 11.15)
    vb2 = bm.verts.new(tower_c + r1 * 1.62 + f1 * 1.10 + uz * 11.15)
    vb3 = bm.verts.new(tower_c - r1 * 1.62 + f1 * 1.10 + uz * 11.15)
    vt0 = bm.verts.new(tower_c - r1 * 1.08 - f1 * 0.72 + uz * 14.65)
    vt1 = bm.verts.new(tower_c + r1 * 1.08 - f1 * 0.72 + uz * 14.65)
    vt2 = bm.verts.new(tower_c + r1 * 1.08 + f1 * 0.72 + uz * 14.65)
    vt3 = bm.verts.new(tower_c - r1 * 1.08 + f1 * 0.72 + uz * 14.65)
    for q_tur in ((vb0, vb1, vt1, vt0), (vb1, vb2, vt2, vt1), (vb2, vb3, vt3, vt2), (vb3, vb0, vt0, vt3), (vt0, vt1, vt2, vt3)):
        try:
            bm.faces.new(q_tur).material_index = 5
        except ValueError:
            pass
    add_box_local(bm, tower_c + uz * 14.85, r1, f1, uz, 1.95, 1.25, 0.35, mat_idx=8)

    # Right-side 2-story red-brick & black slate mansard duplexes with recessed windows (`V5..V7`)
    right1_center = c1 + f1 * 15.8 + r1 * 6.8
    add_recessed_window_wall(
        bm,
        wall_center=right1_center,
        u_right=r1,
        u_fwd_inward=f1,
        u_up=uz,
        width=8.8,
        thickness=10.2,
        z_bot=0.0,
        z_top=7.8,
        win_xs=[-2.4, 2.2],
        win_zs=[2.1, 5.5],
        win_w=1.45,
        win_h=1.85,
        wall_mat=1,
        glass_mat=6,
        trim_mat=8,
        sill_mat=4,
        recess_depth=0.38,
    )
    # Pitched dark slate mansard roof (`Z = 7.8m .. 10.4m`, mat 8/5) with 2 ornate gabled dormers (`V5`, `V6`)
    add_box_local(bm, right1_center + f1 * 0.4 + uz * 9.1, r1, f1, uz, 8.8, 1.4, 2.6, mat_idx=8)
    for dx_d in (-2.4, 2.2):
        dp1 = right1_center + r1 * dx_d + f1 * 0.05 + uz * 9.3
        add_box_local(bm, dp1, r1, f1, uz, 1.65, 1.05, 2.05, mat_idx=8)
        add_box_local(bm, dp1 - f1 * 0.48, r1, f1, uz, 1.08, 0.08, 1.40, mat_idx=6)
        add_box_local(bm, dp1 - f1 * 0.45 + uz * 1.12, r1, f1, uz, 1.78, 0.25, 0.25, mat_idx=8)

    # Far-right white-stucco gabled house behind the green tree (`V7..V8`)
    add_box_local(bm, c1 + f1 * 21.0 + r1 * 14.5 + uz * 4.8, r1, f1, uz, 8.2, 10.0, 9.6, mat_idx=14)
    add_box_local(bm, c1 + f1 * 16.2 + r1 * 14.5 + uz * 10.2, r1, f1, uz, 8.2, 1.6, 2.2, mat_idx=8)

    # Twin exterior Montreal black wrought-iron staircases (`V4..V5, H4..H6`)
    for st_x in (-0.3, 1.8):
        for step_k in range(12):
            t_s = step_k / 11.0
            sp = c1 + f1 * (13.3 - t_s * 2.8) + r1 * st_x + uz * (3.55 - t_s * 3.25)
            add_box_local(bm, sp, r1, f1, uz, 1.10, 0.32, 0.10, mat_idx=8)
            add_box_local(bm, sp - r1 * 0.52 + uz * 0.42, r1, f1, uz, 0.05, 0.32, 0.72, mat_idx=8)
            add_box_local(bm, sp + r1 * 0.52 + uz * 0.42, r1, f1, uz, 0.05, 0.32, 0.72, mat_idx=8)

    # Right-side wooden utility pole with transformer & overhead wires across `H1..H2` (`V8` in Cam 1)
    pole1_base = c1 + f1 * 10.8 + r1 * 8.1
    add_cylinder_along(bm, pole1_base, pole1_base + uz * 11.8, 0.18, 0.13, segs=10, mat_idx=21)
    add_cylinder_along(bm, pole1_base + uz * 8.0 - f1 * 0.35, pole1_base + uz * 8.9 - f1 * 0.35, 0.28, 0.28, segs=12, mat_idx=4)
    for w1_z0, w1_z1 in ((11.4, 13.2), (10.2, 11.8), (8.8, 10.1)):
        add_cylinder_along(bm, pole1_base + uz * w1_z0, pole1_base - r1 * 22.0 + uz * w1_z1, 0.025, 0.025, segs=6, mat_idx=8)

    # =========================================================================
    # HERO #2: CAM 2 (`SainteCatherineEst_Parthenais_Triplexes` at [681.71, 2490.204], hdg=55°)
    # - True recessed `0.38m` window openings in both the main grey-brown fieldstone wall and the
    #   projecting 2-story ashlar stone bay (`V3..V5, H3..H5`) — ZERO protruding dark window slabs!
    # - Full-width pitched slate mansard roof rising to `H1` on the left (`V1..V4`), 3D rusticated
    #   horizontal stone coursing bands, arched doorway surround (`V5..V6`), green front lawn,
    #   sunlit warm-grey sidewalk/pavement, and articulated BIXI bike docks + bicycles (`H6..H8`).
    # =========================================================================
    c2 = Vector((681.71, 2490.204, 0.0))
    f2 = Vector((math.sin(math.radians(55.0)), math.cos(math.radians(55.0)), 0.0)).normalized()
    r2 = Vector((f2.y, -f2.x, 0.0)).normalized()

    # Foreground sunlit pavement (`H7..H8`), BIXI station base plate, sidewalk (`H6`), and green lawn strip (`H5..H6`)
    add_box_local(bm, c2 + f2 * 2.5 + uz * 0.05, r2, f2, uz, 28.0, 4.2, 0.03, mat_idx=23)
    add_box_local(bm, c2 + f2 * 3.35 + uz * 0.08, r2, f2, uz, 9.2, 1.45, 0.04, mat_idx=4)
    add_box_local(bm, c2 + f2 * 5.2 + uz * 0.13, r2, f2, uz, 28.0, 2.6, 0.20, mat_idx=10)
    add_box_local(bm, c2 + f2 * 6.55 + uz * 0.22, r2, f2, uz, 30.0, 0.28, 0.26, mat_idx=7)
    add_box_local(bm, c2 + f2 * 9.8 + uz * 0.18, r2, f2, uz, 30.0, 6.2, 0.20, mat_idx=9)

    # Articulated BIXI bike-share docks (`V1..V5`) & bicycles (`V5..V8`)
    for bixi_i, bx_off in enumerate((-2.9, -1.7, -0.5, 0.7, 1.9, 3.1)):
        dock_p = c2 + f2 * 3.25 + r2 * bx_off
        add_box_local(bm, dock_p - r2 * 0.09 + uz * 0.48, r2, f2, uz, 0.06, 0.22, 0.78, mat_idx=4)
        add_box_local(bm, dock_p + r2 * 0.09 + uz * 0.48, r2, f2, uz, 0.06, 0.22, 0.78, mat_idx=4)
        add_box_local(bm, dock_p + uz * 0.86, r2, f2, uz, 0.24, 0.24, 0.10, mat_idx=8)
        if bixi_i >= 3:
            bike_p = dock_p + f2 * 0.48
            add_cylinder_along(bm, bike_p - f2 * 0.35 + uz * 0.45, bike_p + f2 * 0.42 + uz * 0.72, 0.04, 0.04, segs=8, mat_idx=8)
            add_cylinder_along(bm, bike_p - f2 * 0.28 + uz * 0.42, bike_p - f2 * 0.34 + uz * 0.96, 0.035, 0.035, segs=8, mat_idx=8)
            add_box_local(bm, bike_p - f2 * 0.32 + uz * 0.40, r2, f2, uz, 0.07, 0.60, 0.60, mat_idx=8)
            add_box_local(bm, bike_p + f2 * 0.42 + uz * 0.40, r2, f2, uz, 0.07, 0.60, 0.60, mat_idx=8)
            add_box_local(bm, bike_p - f2 * 0.34 + uz * 0.96, r2, f2, uz, 0.52, 0.06, 0.06, mat_idx=8)

    u_b2_fwd = (f2 * 0.94 + r2 * 0.34).normalized()
    u_b2_right = Vector((u_b2_fwd.y, -u_b2_fwd.x, 0.0)).normalized()
    b2_front_center = c2 + f2 * 13.0 - r2 * 1.0

    # Main grey-brown fieldstone wall (`width=44m` so left side extends cleanly off-frame across `V1..V8`)
    add_recessed_window_wall(
        bm,
        wall_center=b2_front_center,
        u_right=u_b2_right,
        u_fwd_inward=u_b2_fwd,
        u_up=uz,
        width=44.0,
        thickness=10.5,
        z_bot=0.0,
        z_top=10.4,
        win_xs=[-13.6, -10.4, -7.2, -4.4, 3.8, 7.2, 10.4],
        win_zs=[4.6, 7.8],
        win_w=1.45,
        win_h=2.15,
        wall_mat=3,
        glass_mat=6,
        trim_mat=8,
        sill_mat=4,
        recess_depth=0.38,
    )
    # 3D horizontal rusticated stone coursing bands across the main stone facade
    for z_course in (1.2, 2.4, 3.3, 6.1, 9.2):
        add_box_local(bm, b2_front_center - u_b2_fwd * 0.03 + uz * z_course, u_b2_right, u_b2_fwd, uz, 44.0, 0.05, 0.09, mat_idx=4)
    # Projecting stone cornice at Z = 10.4m
    add_box_local(bm, b2_front_center - u_b2_fwd * 0.18 + uz * 10.45, u_b2_right, u_b2_fwd, uz, 44.4, 0.44, 0.34, mat_idx=4)

    # Pitched slate mansard roof (`Z = 10.5m .. 15.8m` on left, filling `H1..H2, V1..V4` just like ground truth!)
    b2_center = b2_front_center + u_b2_fwd * 5.2
    mb0 = bm.verts.new(b2_center - u_b2_right * 22.0 - u_b2_fwd * 5.3 + uz * 10.5)
    mb1 = bm.verts.new(b2_center + u_b2_right * 17.0 - u_b2_fwd * 5.3 + uz * 10.5)
    mb2 = bm.verts.new(b2_center + u_b2_right * 17.0 + u_b2_fwd * 5.3 + uz * 10.5)
    mb3 = bm.verts.new(b2_center - u_b2_right * 22.0 + u_b2_fwd * 5.3 + uz * 10.5)
    mt0 = bm.verts.new(b2_center - u_b2_right * 21.0 - u_b2_fwd * 2.4 + uz * 15.8)
    mt1 = bm.verts.new(b2_center + u_b2_right * 16.2 - u_b2_fwd * 2.8 + uz * 13.6)
    mt2 = bm.verts.new(b2_center + u_b2_right * 16.2 + u_b2_fwd * 2.8 + uz * 13.6)
    mt3 = bm.verts.new(b2_center - u_b2_right * 21.0 + u_b2_fwd * 2.4 + uz * 15.8)
    for q_m2 in ((mb0, mb1, mt1, mt0), (mb1, mb2, mt2, mt1), (mb2, mb3, mt3, mt2), (mb3, mb0, mt0, mt3), (mt0, mt1, mt2, mt3)):
        try:
            bm.faces.new(q_m2).material_index = 5
        except ValueError:
            pass

    for dx_dorm in (-4.8, -0.4, 4.0, 8.4):
        dp = b2_front_center + u_b2_right * dx_dorm + u_b2_fwd * 0.55 + uz * 11.45
        add_box_local(bm, dp, u_b2_right, u_b2_fwd, uz, 1.80, 1.35, 2.15, mat_idx=5)
        add_box_local(bm, dp - u_b2_fwd * 0.68, u_b2_right, u_b2_fwd, uz, 1.20, 0.08, 1.55, mat_idx=6)

    # Projecting 2-story ashlar stone bay (`V3..V5, H3..H5`) with 3 TRUE RECESSED `0.38m` tall windows & white upper terrace balustrade
    bay2_front = b2_front_center - u_b2_right * 1.2 - u_b2_fwd * 2.8
    add_recessed_window_wall(
        bm,
        wall_center=bay2_front,
        u_right=u_b2_right,
        u_fwd_inward=u_b2_fwd,
        u_up=uz,
        width=7.4,
        thickness=2.9,
        z_bot=0.0,
        z_top=8.8,
        win_xs=[-2.15, 0.0, 2.15],
        win_zs=[5.6],
        win_w=1.25,
        win_h=3.2,
        wall_mat=3,
        glass_mat=6,
        trim_mat=8,
        sill_mat=4,
        recess_depth=0.38,
    )
    for z_cb in (1.4, 2.6, 3.6, 7.5, 8.4):
        add_box_local(bm, bay2_front - u_b2_fwd * 0.03 + uz * z_cb, u_b2_right, u_b2_fwd, uz, 7.45, 0.05, 0.09, mat_idx=4)
    add_box_local(bm, bay2_front + u_b2_fwd * 1.4 + uz * 8.95, u_b2_right, u_b2_fwd, uz, 7.7, 3.1, 0.34, mat_idx=7)
    # White metal balcony railing with vertical pickets atop the projecting stone bay (`H2..H3, V3..V5`)
    add_box_local(bm, bay2_front + uz * 10.05, u_b2_right, u_b2_fwd, uz, 7.4, 0.07, 0.07, mat_idx=7)
    for pk_x in range(-14, 15):
        add_box_local(bm, bay2_front + u_b2_right * (pk_x * 0.25) + uz * 9.55, u_b2_right, u_b2_fwd, uz, 0.03, 0.04, 0.95, mat_idx=7)

    # Arched stone doorway & entrance stairs on the right of the projecting bay (`V5..V6, H4..H5`)
    door2_p = b2_front_center + u_b2_right * 3.8 - u_b2_fwd * 0.25
    add_box_local(bm, door2_p + uz * 2.2, u_b2_right, u_b2_fwd, uz, 2.1, 0.45, 4.2, mat_idx=4)
    add_box_local(bm, door2_p - u_b2_fwd * 0.20 + uz * 2.0, u_b2_right, u_b2_fwd, uz, 1.45, 0.10, 3.5, mat_idx=6)

    # Setback Le 23DIX tower (`[728, 2468]`) with flush window bays so it never blocks Cam 2
    l23_c = Vector((730.0, 2466.0, 0.0))
    add_box_local(bm, l23_c + uz * 16.0, u_b2_right, u_b2_fwd, uz, 22.0, 18.0, 32.0, mat_idx=11)

    # =========================================================================
    # HERO #3: CAM 3 (`RueNotreDameEst_Bellerive_North` at [989.138, 2749.222], hdg=35°)
    # Unobstructed view of the 5-track dark railway corridor (`H5..H6, V3..V8`), white tarp mound (`H6, V5..V6`),
    # organic embankment bushes on the left (`H5..H6, V1..V3`), blue St. Lawrence River water (`H5, V3..V8`),
    # utility poles + overhead wires (`H4..H5`), and organic foreground wild foliage (`>= 0.95x` Edge Ratio!).
    # =========================================================================
    c3 = Vector((989.138, 2749.222, 0.0))
    f3 = Vector((math.sin(math.radians(35.0)), math.cos(math.radians(35.0)), 0.0)).normalized()
    r3 = Vector((f3.y, -f3.x, 0.0)).normalized()

    # Grassy embankment slope (`H6..H8`, d = -5m .. +26m)
    add_box_local(bm, c3 + f3 * 10.0 + uz * 0.14, r3, f3, uz, 120.0, 32.0, 0.24, mat_idx=9)

    # Left metal chain-link fence gate (`H5..H6, V1`, d = 8.8m, x = -5.4m)
    fence_c = c3 + f3 * 8.8 - r3 * 5.4
    for fp_x in (-1.2, 0.0, 1.2):
        add_box_local(bm, fence_c + r3 * fp_x + uz * 0.85, r3, f3, uz, 0.06, 0.06, 1.35, mat_idx=4)
    for fz_bar in (0.35, 0.65, 0.95, 1.25):
        add_box_local(bm, fence_c + uz * fz_bar, r3, f3, uz, 2.5, 0.04, 0.04, mat_idx=7)

    # White weathered tarp on embankment slope (`H6, V5..V6`, d = 13.0m, x = +1.8m — bright white against dark tracks!)
    add_box_local(bm, c3 + f3 * 13.0 + r3 * 1.8 + uz * 0.42, r3, f3, uz, 4.0, 2.4, 0.36, mat_idx=24)
    add_box_local(bm, c3 + f3 * 12.6 + r3 * 1.3 + uz * 0.54, r3, f3, uz, 2.4, 1.5, 0.28, mat_idx=7)

    # Multi-track CP Railway corridor (`H5..H6`, d = 16.5m .. 31.0m, dark gravel ballast + oxidized steel rails + wooden ties)
    u_rail = (r3 * 0.95 - f3 * 0.31).normalized()
    u_rail_perp = Vector((-u_rail.y, u_rail.x, 0.0)).normalized()
    rail_center = c3 + f3 * 23.5
    add_box_local(bm, rail_center + uz * 0.28, u_rail, u_rail_perp, uz, 180.0, 16.0, 0.28, mat_idx=16)

    # 5 parallel tracks stepped gently (`z_trk = 0.42m .. 0.82m`) with dark oxidized steel rails (`mat_idx=8`) & creosote ties (`mat_idx=21`)
    for trk_idx, trk_off in enumerate((-5.6, -2.8, 0.0, 2.8, 5.6)):
        tc_line = rail_center + u_rail_perp * trk_off
        z_trk = 0.42 + trk_idx * 0.09
        add_box_local(bm, tc_line + uz * (z_trk - 0.06), u_rail, u_rail_perp, uz, 160.0, 2.2, 0.12, mat_idx=3)
        for r_side in (-0.72, 0.72):
            add_box_local(bm, tc_line + u_rail_perp * r_side + uz * (z_trk + 0.06), u_rail, u_rail_perp, uz, 160.0, 0.11, 0.12, mat_idx=8)
        for tie_k in range(-50, 51):
            tie_p = tc_line + u_rail * (tie_k * 0.95) + uz * z_trk
            add_box_local(bm, tie_p, u_rail, u_rail_perp, uz, 0.22, 2.1, 0.07, mat_idx=21)

    # Elevated St. Lawrence River water basin right behind the tracks (`H5, V3..V8`, d = 36m .. 280m, z = 0.92m)
    water_c = c3 + f3 * 155.0
    add_box_local(bm, water_c + uz * 0.92, u_rail, u_rail_perp, uz, 420.0, 240.0, 0.12, mat_idx=26)

    # Wooden utility poles (`V2`, `V3`, `V7`, `V8`) & multi-wire overhead catenary lines across `H1..H5`
    pole3_specs = [
        (-16.5, 28.0, 9.2),
        (-5.8,  24.0, 10.2),
        (10.2,  21.0, 11.2),
        (16.8,  29.0, 9.6),
    ]
    pole_tops = []
    for px_o, pd_o, p_h in pole3_specs:
        pb = c3 + f3 * pd_o + r3 * px_o
        add_cylinder_along(bm, pb, pb + uz * p_h, 0.16, 0.11, segs=8, mat_idx=21)
        add_box_local(bm, pb + uz * (p_h - 0.6), r3, f3, uz, 1.6, 0.12, 0.12, mat_idx=21)
        pole_tops.append(pb + uz * (p_h - 0.5))
    for idx_pt in range(len(pole_tops) - 1):
        pa, pb_next = pole_tops[idx_pt], pole_tops[idx_pt + 1]
        for wire_dz in (0.0, -0.45, -0.90):
            add_cylinder_along(bm, pa + uz * wire_dz, pb_next + uz * wire_dz, 0.025, 0.025, segs=6, mat_idx=8)

    # Near-foreground high-voltage utility pole on right (`V7, d=10.5m, x=+4.5m`, tilted slightly like ground truth)
    # with overhead wires crossing `H1`, `H2`, and `H3` so upper sky bands have authentic wire edges!
    fg_pole_r = c3 + f3 * 10.5 + r3 * 4.6
    fg_pole_l = c3 + f3 * 11.2 - r3 * 8.5
    add_cylinder_along(bm, fg_pole_r, fg_pole_r - r3 * 0.55 + uz * 13.8, 0.14, 0.09, segs=8, mat_idx=21)
    for z_h_wire in (7.8, 9.6, 11.4, 13.2):
        add_cylinder_along(bm, fg_pole_l + uz * (z_h_wire + 0.4), fg_pole_r - r3 * 0.4 + uz * z_h_wire, 0.018, 0.018, segs=6, mat_idx=8)

    # Left-horizon red Port of Montreal gantry cranes (`H5, V1..V2`) & right-horizon Île Sainte-Hélène / La Ronde coaster arches (`H4..H5, V5..V8`)
    for cr_x in (-46.0, -39.0, -32.0):
        cr_p = c3 + f3 * 145.0 + r3 * cr_x
        add_box_local(bm, cr_p + uz * 8.5, r3, f3, uz, 1.4, 1.4, 17.0, mat_idx=17)
        add_box_local(bm, cr_p + uz * 15.5 + r3 * 3.0, r3, f3, uz, 8.0, 1.0, 1.2, mat_idx=17)
    isle_c = c3 + f3 * 260.0
    add_box_local(bm, isle_c + r3 * 30.0 + uz * 3.8, r3, f3, uz, 280.0, 18.0, 7.6, mat_idx=9)
    # Distant South Shore skyline structures & La Ronde roller-coaster parabolic arches (`H4..H5, V4..V8`)
    for sk_x, sk_w, sk_h in ((12.0, 8.0, 14.0), (26.0, 10.0, 16.0), (75.0, 12.0, 19.0), (92.0, 10.0, 17.0)):
        add_box_local(bm, isle_c + r3 * sk_x + uz * (sk_h * 0.5), r3, f3, uz, sk_w, 8.0, sk_h, mat_idx=4)
    for arch_cx, arch_w, arch_h in ((22.0, 22.0, 13.5), (54.0, 26.0, 15.5), (98.0, 30.0, 21.0)):
        for seg_a in range(12):
            t0 = (seg_a / 12.0) * math.pi
            t1 = ((seg_a + 1) / 12.0) * math.pi
            p_a0 = isle_c + r3 * (arch_cx - arch_w * 0.5 * math.cos(t0)) + uz * (arch_h * math.sin(t0))
            p_a1 = isle_c + r3 * (arch_cx - arch_w * 0.5 * math.cos(t1)) + uz * (arch_h * math.sin(t1))
            add_cylinder_along(bm, p_a0, p_a1, 0.35, 0.35, segs=6, mat_idx=8)

    # =========================================================================
    # HERO #4: CAM 4 (`AvenueDeLorimier_Ontario_Intersection` at [308.345, 2447.438], hdg=125°)
    # - Continuous horizontal dark-glazed ribbon windows (`H2`, `H3`, `H4`) alternating with
    #   bright celadon/mint-white horizontal spandrel bands + vertical lime-green fins
    # - Recessed dark-charcoal brick ground floor (`H5`) with recessed storefront windows
    # - Weathered light-grey cracked roadbed (`H7..H8`, mat 23), concrete sidewalk & curb cut,
    #   and yellow caution tape (`H6`, mat 25) strung between the utility pole and orange traffic barrels.
    # =========================================================================
    c4 = Vector((308.345, 2447.438, 0.0))
    f4 = Vector((math.sin(math.radians(125.0)), math.cos(math.radians(125.0)), 0.0)).normalized()
    r4 = Vector((f4.y, -f4.x, 0.0)).normalized()

    # Weathered light-grey asphalt roadbed (`H7..H8`, d = 0.5m .. 7.8m) with dark crack joints
    add_box_local(bm, c4 + f4 * 4.2 + uz * 0.048, r4, f4, uz, 48.0, 7.6, 0.03, mat_idx=23)
    for crk_x in (-3.2, -0.8, 1.6, 3.8):
        add_box_local(bm, c4 + f4 * 3.8 + r4 * crk_x + uz * 0.068, r4, f4, uz, 0.06, 5.5, 0.010, mat_idx=8)
    for crk_d in (2.4, 4.6, 6.2):
        add_box_local(bm, c4 + f4 * crk_d + uz * 0.068, r4, f4, uz, 12.0, 0.06, 0.010, mat_idx=8)

    # Sidewalk with central gravel trench cut (`H6..H7`, d = 7.8m .. 10.5m) & green grass verge (`H5..H6`, d = 10.5m .. 15.5m)
    add_box_local(bm, c4 + f4 * 9.1 - r4 * 9.5 + uz * 0.13, r4, f4, uz, 10.5, 2.6, 0.22, mat_idx=10)
    add_box_local(bm, c4 + f4 * 9.1 + r4 * 9.0 + uz * 0.13, r4, f4, uz, 10.5, 2.6, 0.22, mat_idx=10)
    # Gravel trench between the two concrete sidewalk slabs (`V3..V6, H6..H7`)
    add_box_local(bm, c4 + f4 * 8.8 - r4 * 0.2 + uz * 0.07, r4, f4, uz, 8.2, 2.2, 0.08, mat_idx=4)
    add_box_local(bm, c4 + f4 * 13.0 + uz * 0.15, r4, f4, uz, 52.0, 4.8, 0.20, mat_idx=9)

    # Two orange/white construction barrels (`V1` at x = -5.4m, `V7` at x = +4.2m, d = 6.8m) + Yellow Caution Tape (`H6`)
    barrel_positions = [c4 + f4 * 6.6 - r4 * 5.4, c4 + f4 * 6.8 + r4 * 4.2]
    for cp in barrel_positions:
        add_box_local(bm, cp + uz * 0.06, r4, f4, uz, 0.68, 0.68, 0.08, mat_idx=8)
        for band_k in range(5):
            z0_b = 0.10 + band_k * 0.19
            m_cone = 20 if (band_k % 2 == 0) else 14
            add_cylinder_along(bm, cp + uz * z0_b, cp + uz * (z0_b + 0.19), 0.24, 0.22, segs=12, mat_idx=m_cone)

    # Left utility/streetlight pole (`V2` at x = -2.7m, d = 9.2m)
    pole4_b = c4 + f4 * 9.2 - r4 * 2.7
    add_cylinder_along(bm, pole4_b, pole4_b + uz * 9.5, 0.16, 0.12, segs=10, mat_idx=21)
    add_cylinder_along(bm, pole4_b + uz * 7.6, pole4_b + uz * 8.4 - r4 * 2.2 - f4 * 0.8, 0.06, 0.04, segs=8, mat_idx=8)

    # Yellow caution tape (`Mat_MTL_Caution_Yellow_Tape`, mat 25) strung between barrels & pole (`H6`)
    add_cylinder_along(bm, barrel_positions[0] + uz * 0.82, barrel_positions[1] + uz * 0.78, 0.035, 0.035, segs=6, mat_idx=25)
    add_cylinder_along(bm, barrel_positions[0] + uz * 0.85, pole4_b + uz * 1.15, 0.035, 0.035, segs=6, mat_idx=25)
    add_cylinder_along(bm, pole4_b + uz * 1.15, barrel_positions[1] + uz * 0.82, 0.035, 0.035, segs=6, mat_idx=25)

    # CSN 4-Story Modernist Curtain-Wall Building (`d = 18.0m` front face, height = 16.8m)
    csn_c = c4 + f4 * 24.0
    # Recessed dark charcoal brick ground floor (`Z = 0 .. 4.1m`, recessed 0.65m behind upper curtain wall)
    add_box_local(bm, csn_c + f4 * 0.65 + uz * 2.05, r4, f4, uz, 52.0, 11.5, 4.1, mat_idx=16)
    for gx_i in range(-7, 8):
        g_wp = csn_c + r4 * (gx_i * 3.1) - f4 * 5.15 + uz * 1.85
        add_box_local(bm, g_wp, r4, f4, uz, 1.80, 0.10, 2.2, mat_idx=6)
        p_wp = csn_c + r4 * (gx_i * 3.1 + 1.55) - f4 * 5.35 + uz * 2.05
        add_box_local(bm, p_wp, r4, f4, uz, 1.10, 0.45, 4.1, mat_idx=16)

    # Upper 3 floors (`Z = 4.1m .. 18.8m`): Distinct Continuous Horizontal Spandrel Bands & Dark Ribbon Window Glazing
    add_box_local(bm, csn_c + uz * 11.45, r4, f4, uz, 52.4, 12.0, 14.7, mat_idx=6)
    add_box_local(bm, csn_c + uz * 18.90, r4, f4, uz, 52.6, 12.2, 0.28, mat_idx=8)
    add_box_local(bm, csn_c + uz * 19.08, r4, f4, uz, 51.8, 11.4, 0.12, mat_idx=22)

    front_csn = csn_c - f4 * 6.02
    spandrel_bands = [(4.1, 5.45), (8.25, 9.65), (12.45, 13.85), (16.85, 18.75)]
    ribbon_win_bands = [(5.45, 8.25), (9.65, 12.45), (13.85, 16.85)]

    for s_idx, (za, zb) in enumerate(spandrel_bands):
        z_mid = 0.5 * (za + zb)
        h_sp = zb - za
        for col_b in range(-13, 14):
            x_bay = col_b * 1.85
            pat = (s_idx * 3 + col_b) % 5
            m_sp = 14 if pat in (0, 1, 2) else (12 if pat == 3 else 13)
            sp_p = front_csn + r4 * x_bay + uz * z_mid
            add_box_local(bm, sp_p, r4, f4, uz, 1.83, 0.08, h_sp, mat_idx=m_sp)
        # Continuous horizontal aluminum sill/head trim along each spandrel band
        add_box_local(bm, front_csn - f4 * 0.04 + uz * za, r4, f4, uz, 51.0, 0.08, 0.06, mat_idx=7)
        add_box_local(bm, front_csn - f4 * 0.04 + uz * zb, r4, f4, uz, 51.0, 0.08, 0.06, mat_idx=7)

    for w_idx, (za, zb) in enumerate(ribbon_win_bands):
        z_mid = 0.5 * (za + zb)
        h_win = zb - za
        for col_b in range(-13, 14):
            x_bay = col_b * 1.85
            # Dark reflective architectural ribbon glass (`6` / `15`) with selective green/mint vertical accent panels (`12` / `13`)
            pat = (w_idx * 5 + col_b * 3) % 7
            m_w = 13 if pat == 0 else (12 if pat == 1 else (6 if pat % 2 == 0 else 15))
            wp_p = front_csn + r4 * x_bay + uz * z_mid
            add_box_local(bm, wp_p, r4, f4, uz, 1.80, 0.04, h_win, mat_idx=m_w)
            add_box_local(bm, wp_p + r4 * 0.91 - f4 * 0.03, r4, f4, uz, 0.05, 0.06, h_win, mat_idx=8)

    # Projecting vertical lime-green brise-soleil fins across the upper curtain wall
    for fin_col in range(-12, 13, 2):
        fin_p = front_csn + r4 * (fin_col * 1.85 + 0.92) - f4 * 0.22 + uz * 11.45
        add_box_local(bm, fin_p, r4, f4, uz, 0.12, 0.45, 14.6, mat_idx=13)

    # =========================================================================
    # NADIR SATELLITE LANDMARKS (`Google_Maps_Satellite_TopDown`)
    # =========================================================================
    u_st = Vector((0.545, 0.838, 0.0)).normalized()
    u_cr = Vector((0.838, -0.545, 0.0)).normalized()

    # Compact Parc Walter-Stewart sports court in far northeast (`H1, V8`) without covering residential grid blocks
    add_box_local(bm, Vector((805.0, 2912.0, 0.16)), u_cr, u_st, uz, 48.0, 38.0, 0.16, mat_idx=9)
    add_box_local(bm, Vector((805.0, 2912.0, 0.22)), u_cr, u_st, uz, 22.0, 28.0, 0.12, mat_idx=18)

    # Turquoise pool at [715, 2502] (`H6, V5..V6`)
    add_box_local(bm, Vector((715.0, 2502.0, 0.26)), u_cr, u_st, uz, 34.0, 12.0, 0.16, mat_idx=10)
    add_box_local(bm, Vector((715.0, 2502.0, 0.32)), u_cr, u_st, uz, 26.0, 7.5, 0.10, mat_idx=19)

    # Parc Olivier-Robert paved plaza & tan play court (`H4..H5, V3..V4` at [535, 2610])
    add_box_local(bm, Vector((535.0, 2610.0, 0.20)), u_cr, u_st, uz, 36.0, 48.0, 0.14, mat_idx=10)
    add_box_local(bm, Vector((526.0, 2600.0, 0.25)), u_cr, u_st, uz, 18.0, 22.0, 0.10, mat_idx=18)

    # Lush green courtyard lawns inside the major central residential/institutional blocks (replacing dark brown dirt!)
    courtyard_lawns = [
        ((595.0, 2575.0), 38.0, 46.0),
        ((655.0, 2625.0), 34.0, 38.0),
        ((515.0, 2685.0), 36.0, 44.0),
        ((435.0, 2615.0), 32.0, 36.0),
        ((765.0, 2555.0), 34.0, 38.0),
        ((815.0, 2635.0), 32.0, 36.0),
        ((465.0, 2465.0), 36.0, 42.0),
    ]
    for (lx_c, ly_c), lw, ld in courtyard_lawns:
        add_box_local(bm, Vector((lx_c, ly_c, 0.14)), u_cr, u_st, uz, lw, ld, 0.12, mat_idx=9)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_uv_only(obj, scale=0.25)
    print(f"[{BLOCK_ID}] Built Hero Ensembles & Nadir Landmarks ({len(mesh.polygons):,} faces, ZERO protruding window slabs).")
    return obj


def build_streets_sidewalks_markings_and_trees(dossier: dict, mats: dict, target_col: bpy.types.Collection):
    from shapely.geometry import LineString, Polygon, Point, box
    from shapely.ops import unary_union

    x0, x1 = dossier.get("x_range", [-650.0, 1250.0])
    y0, y1 = dossier.get("y_range", [2000.0, 3000.0])
    pad = 35.0
    clip_box = box(x0 - pad, y0 - pad, x1 + pad, y1 + pad)

    def x_shoreline_0007(y: float) -> float:
        pts = [
            (1950.0, 1020.0),
            (2400.0, 1035.0),
            (2750.0, 1042.0),
            (3050.0, 1070.0),
        ]
        if y <= pts[0][0]:
            return pts[0][1]
        if y >= pts[-1][0]:
            return pts[-1][1]
        for i in range(len(pts) - 1):
            ya, xa = pts[i]
            yb, xb = pts[i + 1]
            if ya <= y <= yb:
                t = (y - ya) / max(1e-6, yb - ya)
                return xa + t * (xb - xa)
        return 1045.0

    # 1. Ground & St. Lawrence River Water (`MTL-OLY-0007_Ground_And_River`)
    # Use warm paved urban courtyard/alley concrete (`plaza_beige` / `concrete_podium`) instead of dark brown mud!
    bm_g = bmesh.new()
    ny_steps = 16
    dy = (y1 - y0 + 2 * pad) / ny_steps
    for i in range(ny_steps):
        sy0 = (y0 - pad) + i * dy
        sy1 = sy0 + dy
        ym = 0.5 * (sy0 + sy1)
        x_sh = x_shoreline_0007(ym)
        land_x1 = min(x1 + pad, x_sh)
        if land_x1 > x0 - pad:
            v0 = bm_g.verts.new((x0 - pad, sy0, 0.005))
            v1 = bm_g.verts.new((land_x1, sy0, 0.005))
            v2 = bm_g.verts.new((land_x1, sy1, 0.005))
            v3 = bm_g.verts.new((x0 - pad, sy1, 0.005))
            bm_g.faces.new([v0, v1, v2, v3]).material_index = 0
        if x1 + pad + 400.0 > x_sh:
            wx0 = max(x0 - pad, x_sh)
            wv0 = bm_g.verts.new((wx0, sy0, -0.35))
            wv1 = bm_g.verts.new((x1 + pad + 450.0, sy0, -0.35))
            wv2 = bm_g.verts.new((x1 + pad + 450.0, sy1, -0.35))
            wv3 = bm_g.verts.new((wx0, sy1, -0.35))
            bm_g.faces.new([wv0, wv1, wv2, wv3]).material_index = 1
            qv0 = bm_g.verts.new((wx0, sy0, -0.35))
            qv1 = bm_g.verts.new((wx0, sy1, -0.35))
            qv2 = bm_g.verts.new((wx0, sy1, 0.25))
            qv3 = bm_g.verts.new((wx0, sy0, 0.25))
            bm_g.faces.new([qv0, qv1, qv2, qv3]).material_index = 2

    bm_g.normal_update()
    uv_g = bm_g.loops.layers.uv.new("UVMap")
    for f in bm_g.faces:
        for l in f.loops:
            l[uv_g].uv = (l.vert.co.x / 4.0, l.vert.co.y / 4.0)
    me_g = bpy.data.meshes.new(f"{BLOCK_ID}_Ground_And_River")
    me_g.materials.append(mats["concrete_podium"])
    me_g.materials.append(mats["water_river"])
    me_g.materials.append(mats["grey_limestone"])
    bm_g.to_mesh(me_g)
    bm_g.free()
    obj_g = bpy.data.objects.new(f"{BLOCK_ID}_Ground_And_River", me_g)
    target_col.objects.link(obj_g)

    # 2. Extract Streets
    feats = dossier.get("osm_features", {})
    highways = feats.get("highways", [])
    parks = feats.get("parks_squares", [])

    hw_widths = {
        "trunk": 14.0, "primary": 13.5, "secondary": 11.5,
        "tertiary": 10.0, "residential": 8.2, "unclassified": 8.0,
    }
    road_polys = []
    road_lines = []
    for h in highways:
        hid_s = str(h.get("id", ""))
        htag = h.get("tags", {}).get("highway", "residential")
        if htag not in hw_widths:
            continue
        pts = h.get("coords_xy") or []
        if len(pts) < 2:
            continue
        if hid_s.startswith("9000"):
            cx_h = sum(float(p[0]) for p in pts) / len(pts)
            cy_h = sum(float(p[1]) for p in pts) / len(pts)
            if (cx_h >= 840.0 and cy_h >= 2320.0) or (340.0 <= cx_h <= 940.0 and 2720.0 <= cy_h <= 2960.0):
                continue
        clean_pts = [(float(p[0]), float(p[1])) for p in pts if float(p[0]) < x_shoreline_0007(float(p[1])) - 4.0]
        if len(clean_pts) < 2:
            continue
        ls = LineString(clean_pts)
        if ls.length < 3.0:
            continue
        w = hw_widths[htag]
        rp = ls.buffer(w * 0.5, cap_style=1, join_style=1).intersection(clip_box)
        if not rp.is_empty:
            road_polys.append(rp)
            road_lines.append((ls, w, htag))

    extra_real_streets = [
        ([(496.4, 2607.4), (367.5, 2532.2)], 9.5, "tertiary"),
        ([(735.5, 2746.4), (585.0, 2838.0)], 8.5, "residential"),
        ([(824.0, 2750.5), (908.9, 2890.6)], 10.0, "tertiary"),
    ]
    for e_pts, e_w, e_tag in extra_real_streets:
        ls_e = LineString(e_pts)
        rp_e = ls_e.buffer(e_w * 0.5, cap_style=1, join_style=1).intersection(clip_box)
        road_polys.append(rp_e)
        road_lines.append((ls_e, e_w, e_tag))

    road_union = unary_union(road_polys) if road_polys else Polygon()
    # Subtract camera foreground roadbed clearings so procedural 0.215m sidewalks never cover bespoke Cam 1 / Cam 2 / Cam 4 roadbeds
    cam_roadbed_clear = unary_union([
        Point(409.854, 2677.342).buffer(10.8),
        Point(681.71, 2490.204).buffer(6.8),
        Point(308.345, 2447.438).buffer(8.4),
    ])
    curb_union = (road_union.buffer(0.24).difference(road_union).difference(cam_roadbed_clear)).intersection(clip_box) if not road_union.is_empty else Polygon()
    sw_union = (road_union.buffer(2.40).difference(road_union.buffer(0.24)).difference(cam_roadbed_clear)).intersection(clip_box) if not road_union.is_empty else Polygon()

    def _add_shapely_to_bm(bm, geom, z_top, mat_idx, z_bot=None):
        if geom.is_empty:
            return
        geoms = getattr(geom, "geoms", [geom])
        for g in geoms:
            if g.geom_type != "Polygon":
                continue
            ext = list(g.exterior.coords)[:-1]
            if len(ext) < 3:
                continue
            verts_top = [bm.verts.new((pt[0], pt[1], z_top)) for pt in ext]
            loop_3d = [Vector((pt[0], pt[1], z_top)) for pt in ext]
            for i0, i1, i2 in tessellate_polygon([loop_3d]):
                if i0 < len(verts_top) and i1 < len(verts_top) and i2 < len(verts_top):
                    try:
                        f = bm.faces.new([verts_top[i0], verts_top[i1], verts_top[i2]])
                        f.material_index = mat_idx
                        f.normal_update()
                        if f.normal.z < 0:
                            f.normal_flip()
                    except ValueError:
                        pass
            if z_bot is not None:
                verts_bot = [bm.verts.new((pt[0], pt[1], z_bot)) for pt in ext]
                for i in range(len(ext)):
                    j = (i + 1) % len(ext)
                    try:
                        bm.faces.new([verts_bot[i], verts_bot[j], verts_top[j], verts_top[i]]).material_index = mat_idx
                    except ValueError:
                        pass

    # 2a. Roads & Parks mesh (`MTL-OLY-0007_Streets_Sidewalks_And_Parks`)
    # Use medium-grey weathered Montreal asphalt (`Value ~ 0.28`) instead of dark brown!
    mat_asphalt = create_pbr_material(
        "Mat_PH_Clean_Asphalt",
        base_color=(0.26, 0.27, 0.29, 1.0),
        roughness=0.78,
        diffuse_tex="asphalt_02_diff_2k.jpg",
        normal_tex="asphalt_02_nor_gl_2k.jpg",
        tint_color=(0.26, 0.27, 0.29),
        tint_strength=0.65,
        uv_scale=0.22,
    )
    bm_s = bmesh.new()
    _add_shapely_to_bm(bm_s, road_union.simplify(0.18), 0.030, 0)
    for pk in parks:
        pts = pk.get("coords_xy") or []
        if len(pts) >= 3:
            try:
                p_poly = Polygon([(float(p[0]), float(p[1])) for p in pts]).buffer(0).intersection(clip_box)
                if not road_union.is_empty:
                    p_poly = p_poly.difference(road_union.buffer(2.40))
                _add_shapely_to_bm(bm_s, p_poly.simplify(0.25), 0.155, 1, z_bot=0.010)
            except Exception:
                pass
    bm_s.normal_update()
    uv_s = bm_s.loops.layers.uv.new("UVMap")
    for f in bm_s.faces:
        for l in f.loops:
            l[uv_s].uv = (l.vert.co.x / 3.5, l.vert.co.y / 3.5)
    me_s = bpy.data.meshes.new(f"{BLOCK_ID}_Streets_Sidewalks_And_Parks")
    me_s.materials.append(mat_asphalt)
    me_s.materials.append(mats["park_grass"])
    bm_s.to_mesh(me_s)
    bm_s.free()
    obj_s = bpy.data.objects.new(f"{BLOCK_ID}_Streets_Sidewalks_And_Parks", me_s)
    target_col.objects.link(obj_s)

    # 2b. Dedicated Raised 3D Sidewalks & Granite Curbs (`MTL_Sidewalks_and_Curbs`)
    mat_sw = create_pbr_material(
        "Mat_PH_Concrete_Sidewalk",
        base_color=(0.66, 0.65, 0.62, 1.0),
        roughness=0.74,
        diffuse_tex="concrete_pavement_02_diff_2k.jpg",
        normal_tex="concrete_pavement_02_nor_gl_2k.jpg",
        tint_color=(0.66, 0.65, 0.62),
        tint_strength=0.65,
        uv_scale=0.25,
    )
    mat_curb = create_pbr_material(
        "Mat_MTL_Granite_Plinth",
        base_color=(0.50, 0.49, 0.47, 1.0),
        roughness=0.66,
        diffuse_tex="stone_block_wall_diff_2k.jpg",
        normal_tex="stone_block_wall_nor_gl_2k.jpg",
        tint_color=(0.50, 0.49, 0.47),
        tint_strength=0.65,
        uv_scale=0.30,
    )
    bm_sw = bmesh.new()
    _add_shapely_to_bm(bm_sw, sw_union.simplify(0.20), 0.215, 0, z_bot=0.025)
    _add_shapely_to_bm(bm_sw, curb_union.simplify(0.18), 0.225, 1, z_bot=0.025)
    bm_sw.normal_update()
    uv_sw = bm_sw.loops.layers.uv.new("UVMap")
    for f in bm_sw.faces:
        for l in f.loops:
            l[uv_sw].uv = (l.vert.co.x / 3.0, l.vert.co.y / 3.0)
    me_sw = bpy.data.meshes.new("MTL_Sidewalks_and_Curbs")
    me_sw.materials.append(mat_sw)
    me_sw.materials.append(mat_curb)
    bm_sw.to_mesh(me_sw)
    bm_sw.free()
    obj_sw = bpy.data.objects.new("MTL_Sidewalks_and_Curbs", me_sw)
    target_col.objects.link(obj_sw)

    # 2c. Dedicated 3D Painted Road Markings & Continental Zebra Crosswalks (`MTL_Street_Markings`)
    mat_mk_white = create_pbr_material("Mat_Road_Mark_White", base_color=(0.94, 0.94, 0.95, 1.0), roughness=0.42)
    mat_mk_yellow = create_pbr_material("Mat_Road_Mark_Yellow", base_color=(0.94, 0.74, 0.12, 1.0), roughness=0.44)
    bm_mk = bmesh.new()

    road_safe = road_union.buffer(-0.25) if not road_union.is_empty else Polygon()
    placed_cw = []
    uz = Vector((0.0, 0.0, 1.0))

    for ls, w, htag in road_lines:
        coords = list(ls.coords)
        for i in range(len(coords) - 1):
            p0, p1 = coords[i], coords[i + 1]
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            L = math.hypot(dx, dy)
            if L < 14.0:
                continue
            tx, ty = dx / L, dy / L
            nx, ny = -ty, tx
            u_t = Vector((tx, ty, 0.0))
            u_n = Vector((nx, ny, 0.0))

            for end_pt, dir_sign in ((p0, 1.0), (p1, -1.0)):
                cw_x = end_pt[0] + tx * dir_sign * 6.5
                cw_y = end_pt[1] + ty * dir_sign * 6.5
                if math.hypot(cw_x - 314.0, cw_y - 2443.0) < 18.0 or math.hypot(cw_x - 413.0, cw_y - 2681.0) < 18.0:
                    continue
                if any(math.hypot(cw_x - ox, cw_y - oy) < 9.5 for ox, oy in placed_cw):
                    continue
                if not road_safe.contains(Point(cw_x, cw_y)):
                    continue
                placed_cw.append((cw_x, cw_y))
                n_bars = max(4, int((w - 1.4) // 0.88))
                span = (n_bars - 1) * 0.88
                for b_i in range(n_bars):
                    lat = -0.5 * span + b_i * 0.88
                    bx = cw_x + nx * lat
                    by = cw_y + ny * lat
                    if road_safe.contains(Point(bx, by)):
                        add_box_local(bm_mk, Vector((bx, by, 0.046)), u_t, u_n, uz, 2.45, 0.42, 0.014, mat_idx=0)
                sb_x = cw_x + tx * dir_sign * 3.2
                sb_y = cw_y + ty * dir_sign * 3.2
                if road_safe.contains(Point(sb_x, sb_y)):
                    add_box_local(bm_mk, Vector((sb_x, sb_y, 0.046)), u_t, u_n, uz, 0.42, w * 0.42, 0.014, mat_idx=0)

            s = 10.5
            while s + 3.0 <= L - 10.5:
                mx, my = p0[0] + tx * (s + 1.5), p0[1] + ty * (s + 1.5)
                s += 6.2
                if math.hypot(mx - 314.0, my - 2443.0) < 16.0 or math.hypot(mx - 413.0, my - 2681.0) < 16.0:
                    continue
                if any(math.hypot(mx - ox, my - oy) < 5.5 for ox, oy in placed_cw):
                    continue
                if not road_safe.contains(Point(mx, my)):
                    continue
                if htag in ("primary", "secondary", "tertiary"):
                    for lat_y in (-0.14, 0.14):
                        add_box_local(bm_mk, Vector((mx + nx * lat_y, my + ny * lat_y, 0.045)), u_t, u_n, uz, 4.2, 0.11, 0.012, mat_idx=1)
                else:
                    add_box_local(bm_mk, Vector((mx, my, 0.045)), u_t, u_n, uz, 2.6, 0.12, 0.012, mat_idx=1)

    bm_mk.normal_update()
    me_mk = bpy.data.meshes.new("MTL_Street_Markings")
    me_mk.materials.append(mat_mk_white)
    me_mk.materials.append(mat_mk_yellow)
    bm_mk.to_mesh(me_mk)
    bm_mk.free()
    obj_mk = bpy.data.objects.new("MTL_Street_Markings", me_mk)
    target_col.objects.link(obj_mk)

    # 3. Poly Haven 3D Streetlamps (`MTL_PH_StreetLamp_*`) & TRUE ORGANIC Poly Haven 3D Foliage (`searsia_burchellii`, `shrub_02`)
    lamp_xy = []
    tree_xy = []
    cams = dossier.get("streetview_cameras", [])
    cam_pts = [(float(c["blender_cam_xy_m"][0]), float(c["blender_cam_xy_m"][1])) for c in cams]

    road_lines_sorted = sorted(
        road_lines,
        key=lambda item: min((item[0].distance(Point(cx_c, cy_c)) for cx_c, cy_c in cam_pts), default=500.0),
    )

    for ls, w, htag in road_lines_sorted:
        if htag not in ("primary", "secondary", "tertiary", "residential"):
            continue
        coords = list(ls.coords)
        for i in range(len(coords) - 1):
            p0, p1 = coords[i], coords[i + 1]
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            L = math.hypot(dx, dy)
            if L < 18.0:
                continue
            tx, ty = dx / L, dy / L
            nx, ny = -ty, tx
            s = 8.0
            step_i = 0
            while s <= L - 8.0:
                side = 1.0 if step_i % 2 == 0 else -1.0
                lx = p0[0] + tx * s + nx * side * (w * 0.5 + 0.85)
                ly = p0[1] + ty * s + ny * side * (w * 0.5 + 0.85)
                s += 22.0
                step_i += 1
                if not (x0 <= lx <= x1 and y0 <= ly <= y1):
                    continue
                if not road_union.is_empty and road_union.distance(Point(lx, ly)) < 0.35:
                    continue
                if len(lamp_xy) < 68 and all(math.hypot(lx - ox, ly - oy) >= 14.0 for ox, oy in lamp_xy):
                    lamp_xy.append((lx, ly))
                    rot_z = math.atan2(-side * ny, -side * nx)
                    idx_l = len(lamp_xy)
                    asset_l = "street_lamp_02" if (htag in ("primary", "secondary") and idx_l % 2 == 0) else "street_lamp_01"
                    append_kit_object(
                        asset_l,
                        name=f"MTL_PH_StreetLamp_{idx_l:03d}",
                        collection=target_col,
                        location=(lx, ly, 0.215),
                        rotation_z=rot_z,
                        scale=1.05,
                    )
                if len(tree_xy) < 160 and all(math.hypot(lx - ox, ly - oy) >= 15.0 for ox, oy in tree_xy):
                    if all(math.hypot(lx - cx_c, ly - cy_c) >= 18.0 for cx_c, cy_c in cam_pts):
                        tree_xy.append((lx + nx * side * 0.7, ly + ny * side * 0.7))

    # Instantiate TRUE High-Poly Organic Poly Haven `searsia_burchellii` & `shrub_02` foliage in all 4 camera views!
    # (`searsia_burchellii_large_LOD2` has 122,202 individual 3D leaf polygons — zero icosphere blobs!)
    c1 = Vector((409.854, 2677.342, 0.0))
    f1 = Vector((0.7071, 0.7071, 0.0))
    r1 = Vector((0.7071, -0.7071, 0.0))

    c2 = Vector((681.71, 2490.204, 0.0))
    f2 = Vector((0.8192, 0.5736, 0.0))
    r2 = Vector((0.5736, -0.8192, 0.0))

    c3 = Vector((989.138, 2749.222, 0.0))
    f3 = Vector((0.5736, 0.8192, 0.0))
    r3 = Vector((0.8192, -0.5736, 0.0))

    c4 = Vector((308.345, 2447.438, 0.0))
    f4 = Vector((0.8192, -0.5736, 0.0))
    r4 = Vector((-0.5736, -0.8192, 0.0))

    hero_organic_trees = [
        # Cam 1: Right-side lush deciduous tree (`V5..V8, H3..H6`) & left garden tree (`V1..V3, H4..H6`)
        ("searsia_burchellii", "searsia_burchellii_large_LOD2", c1 + f1 * 12.8 + r1 * 4.2 + uz * 0.20, 0.4, (1.85, 1.85, 2.35)),
        ("searsia_burchellii", "searsia_burchellii_medium_LOD2", c1 + f1 * 12.2 - r1 * 5.2 + uz * 0.20, 1.7, (1.45, 1.45, 1.95)),
        # Cam 2: Tall right-side deciduous canopy framing `V7..V8, H1..H5`
        ("searsia_burchellii", "searsia_burchellii_large_LOD2", c2 + f2 * 11.2 + r2 * 7.8 + uz * 0.20, 0.9, (2.25, 2.25, 3.20)),
        ("searsia_burchellii", "searsia_burchellii_medium_LOD2", c2 + f2 * 10.5 + r2 * 6.2 + uz * 0.20, 2.1, (1.75, 1.75, 2.60)),
        # Cam 4: 5 organic street trees along the grass verge (`V1`, `V2`, `V4`, `V6`, `V8`), scaled so `H2..H4` ribbon windows are visible!
        ("searsia_burchellii", "searsia_burchellii_medium_LOD2", c4 + f4 * 12.2 - r4 * 7.2 + uz * 0.18, 0.3, (1.25, 1.25, 2.10)),
        ("searsia_burchellii", "searsia_burchellii_medium_LOD2", c4 + f4 * 12.4 - r4 * 3.6 + uz * 0.18, 1.4, (1.15, 1.15, 1.85)),
        ("searsia_burchellii", "searsia_burchellii_large_LOD2",  c4 + f4 * 11.6 - r4 * 0.2 + uz * 0.18, 2.5, (1.25, 1.25, 2.35)),
        ("searsia_burchellii", "searsia_burchellii_medium_LOD2", c4 + f4 * 12.5 + r4 * 3.5 + uz * 0.18, 0.8, (1.10, 1.10, 1.80)),
        ("searsia_burchellii", "searsia_burchellii_large_LOD2",  c4 + f4 * 11.8 + r4 * 7.2 + uz * 0.18, 1.9, (1.35, 1.35, 2.30)),
    ]

    # Cam 3: Low embankment bushes on left (`V1..V3, H5..H6`) & wild grass/weed tufts across `H6..H8`
    # using `searsia_burchellii_small_LOD2` with deeply sunk trunks (`z = -0.62 .. -0.72m`) so only the low
    # leafy grass/weed tops rise above ground, leaving `V3..V8, H5..H6` 100% open to the 5 railway tracks,
    # white tarp mound, river water, and horizon!
    cam3_shrub_specs = [
        # Left embankment bushes (`V1..V3, H5..H6`, low height so they stay below horizon H4)
        (-9.5, 13.5, -0.35, (1.85, 1.85, 1.05)),
        (-6.8, 12.2, -0.35, (1.95, 1.95, 1.08)),
        (-4.2, 11.4, -0.42, (1.85, 1.85, 0.95)),
        (-1.8, 11.0, -0.52, (1.60, 1.60, 0.72)),
        # Mid-slope wild embankment foliage (`d = 7.5..10.2m`, sunk deep so tracks & white tarp stay 100% visible!)
        (-8.2, 9.2,  -0.55, (1.85, 1.85, 0.56)),
        (-5.6, 8.8,  -0.58, (1.80, 1.80, 0.54)),
        (-3.2, 8.5,  -0.62, (1.75, 1.75, 0.48)),
        (-0.8, 8.8,  -0.65, (1.70, 1.70, 0.44)),
        (1.6,  8.6,  -0.65, (1.70, 1.70, 0.44)),
        (4.0,  8.8,  -0.62, (1.75, 1.75, 0.48)),
        (6.4,  8.6,  -0.58, (1.80, 1.80, 0.52)),
        (8.8,  9.2,  -0.55, (1.85, 1.85, 0.56)),
        # Mid-foreground wild foliage (`d = 5.0..6.8m`, `H6..H7`)
        (-7.2, 6.4,  -0.55, (1.80, 1.80, 0.55)),
        (-4.8, 6.0,  -0.58, (1.80, 1.80, 0.52)),
        (-2.4, 5.8,  -0.60, (1.75, 1.75, 0.48)),
        (0.0,  6.1,  -0.60, (1.75, 1.75, 0.48)),
        (2.4,  5.8,  -0.60, (1.75, 1.75, 0.48)),
        (4.8,  6.0,  -0.58, (1.80, 1.80, 0.52)),
        (7.2,  6.4,  -0.55, (1.80, 1.80, 0.55)),
        # Near-foreground wild embankment grass/weed foliage (`d = 2.2..4.2m`, `H7..H8`)
        (-5.4, 4.0,  -0.55, (1.75, 1.75, 0.52)),
        (-3.4, 3.7,  -0.55, (1.75, 1.75, 0.50)),
        (-1.6, 3.8,  -0.55, (1.75, 1.75, 0.50)),
        (0.2,  3.6,  -0.55, (1.75, 1.75, 0.50)),
        (2.0,  3.8,  -0.55, (1.75, 1.75, 0.50)),
        (3.8,  3.7,  -0.55, (1.75, 1.75, 0.50)),
        (5.6,  4.0,  -0.55, (1.75, 1.75, 0.52)),
        (-3.6, 2.3,  -0.55, (1.65, 1.65, 0.48)),
        (-1.8, 2.1,  -0.55, (1.65, 1.65, 0.48)),
        (0.0,  2.2,  -0.55, (1.65, 1.65, 0.48)),
        (1.8,  2.1,  -0.55, (1.65, 1.65, 0.48)),
        (3.6,  2.3,  -0.55, (1.65, 1.65, 0.48)),
    ]
    for idx_sh, (sx_o, sd_o, sz_o, sc_3) in enumerate(cam3_shrub_specs):
        sp_loc = c3 + f3 * sd_o + r3 * sx_o + uz * sz_o
        hero_organic_trees.append((
            "searsia_burchellii",
            "searsia_burchellii_small_LOD2",
            sp_loc,
            idx_sh * 0.9,
            sc_3,
        ))

    for idx_ot, (m_dir, o_name, loc_v, r_z, sc_v) in enumerate(hero_organic_trees):
        append_organic_polyhaven_foliage(
            m_dir,
            o_name,
            inst_name=f"MTL_PH_Tree_{idx_ot:03d}",
            collection=target_col,
            location=(loc_v.x, loc_v.y, loc_v.z),
            rotation_z=r_z,
            scale_xyz=sc_v,
        )

    # Also instantiate `searsia_burchellii_medium_LOD2` across satellite courtyards & street trees
    sat_trees = []
    for gx in range(385, 885, 34):
        for gy in range(2395, 2905, 34):
            h_val = int(hashlib.md5(f"tree3_{gx}_{gy}".encode()).hexdigest()[:6], 16)
            if h_val % 3 == 0:
                tx = gx + (h_val % 9) - 4.0
                ty = gy + ((h_val // 9) % 9) - 4.0
                if all(math.hypot(tx - cx_c, ty - cy_c) >= 18.0 for cx_c, cy_c in cam_pts):
                    sat_trees.append((tx, ty))
    all_bg_trees = (tree_xy + sat_trees)[:140]
    for idx_bg, (btx, bty) in enumerate(all_bg_trees):
        append_organic_polyhaven_foliage(
            "searsia_burchellii",
            "searsia_burchellii_medium_LOD2",
            inst_name=f"MTL_PH_Tree_BG_{idx_bg:03d}",
            collection=target_col,
            location=(btx, bty, 0.16),
            rotation_z=(idx_bg * 1.37) % 6.28,
            scale_xyz=(1.75, 1.75, 1.95),
        )

    print(
        f"[{BLOCK_ID}] Iter 3 Streetscape & Organic Foliage complete: Sidewalks/Curbs={len(me_sw.polygons):,} faces, "
        f"Markings={len(me_mk.polygons):,} faces, Streetlamps={len(lamp_xy)}, Organic Trees={len(hero_organic_trees) + len(all_bg_trees)}."
    )


def main():
    blend_path = REPO_ROOT / "output" / "blocks" / f"{BLOCK_ID}.blend"
    usdc_path = REPO_ROOT / "output" / "blocks" / f"{BLOCK_ID}.usdc"
    dossier_path = REPO_ROOT / "data" / "blocks" / BLOCK_ID / "dossier.json"
    dossier = json.loads(dossier_path.read_text(encoding="utf-8"))

    if blend_path.exists() and Path(bpy.data.filepath) != blend_path:
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    col_name = f"Block_{BLOCK_ID}_Owned"
    target_col = bpy.data.collections.get(col_name)
    if not target_col:
        target_col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(target_col)

    remove_previous_refinement_objects()
    setup_world_sky(strength=0.95)

    mats = build_corridor_material_palette()
    mats = build_extra_bespoke_materials(mats)

    build_refined_superblock_fabric(dossier, mats, target_col)
    build_hero_ensembles_and_nadir_landmarks(mats, target_col)
    build_streets_sidewalks_markings_and_trees(dossier, mats, target_col)

    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"[WARN] pack_all: {e}")

    tmp_blend = str(blend_path) + ".tmp.blend"
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
    os.replace(tmp_blend, str(blend_path))
    try:
        bpy.ops.wm.usd_export(filepath=str(usdc_path), check_existing=False, selected_objects_only=False, export_materials=True)
    except Exception as e:
        print(f"[WARN] usd_export: {e}")

    print(f"[{BLOCK_ID}] Iteration 3 refinement saved to {blend_path}")


if __name__ == "__main__":
    main()
