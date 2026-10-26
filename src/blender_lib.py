#!/usr/bin/env python3
"""
Reusable Blender 5.2 Geospatial & Poly Haven 2K PBR Library (`src/blender_lib.py`)
Provides scene setup, Poly Haven 2K PBR shader node creation with BOX projection,
world-space box UV mapping, georeferenced ground/street/sidewalk generation,
kit asset appending (`assets/montreal_kit.blend`), and packed `.blend` + `.usdc` export.
"""

import os
import sys
import site
import json
import math
from pathlib import Path

try:
    _user_site = site.getusersitepackages()
    if _user_site and _user_site not in sys.path:
        sys.path.append(_user_site)
except Exception:
    pass

import bpy
import bmesh
import mathutils
from mathutils import Vector
from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon, Point, box
from shapely.ops import unary_union, linemerge

REPO_ROOT = Path(__file__).resolve().parent.parent
POLYHAVEN_DIR = REPO_ROOT / "assets" / "polyhaven"
KIT_BLEND_PATH = REPO_ROOT / "assets" / "montreal_kit.blend"


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


clean_scene = clear_scene


def setup_render_engine():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "HIP"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception:
        pass


def setup_world_lighting(dossier: dict = None):
    setup_world_sky(strength=0.95)


def setup_collection_hierarchy(block_id: str):
    owned_col = bpy.data.collections.new(f"Block_{block_id}_Owned")
    ctx_col = bpy.data.collections.new(f"Block_{block_id}_Context")
    bpy.context.scene.collection.children.link(owned_col)
    bpy.context.scene.collection.children.link(ctx_col)
    return owned_col, ctx_col


def setup_world_sky(strength: float = 0.95):
    scene = bpy.context.scene
    # Apply RSI-005 Photometric Calibration so concrete, grass, and brick never clip to white
    try:
        scene.view_settings.view_transform = "Filmic"
        scene.view_settings.look = "Medium High Contrast"
        scene.view_settings.exposure = -0.35
    except Exception:
        pass

    if not scene.world:
        scene.world = bpy.data.worlds.new("World_Montreal_PBR")
    scene.world.use_nodes = True
    nt = scene.world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength

    # Calibrated Montreal clear blue sky dome gradient (zenith deep sky blue -> horizon soft blue)
    tcoord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.42, 0.58, 0.82, 1.0)
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (0.18, 0.36, 0.68, 1.0)
    nt.links.new(tcoord.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # Add primary sun light + soft fill sun for crisp architectural shadows in rib crevices
    light_data = bpy.data.lights.new("Sun_Montreal", type="SUN")
    light_data.energy = 2.35
    light_data.color = (1.0, 0.96, 0.90)
    light_data.angle = math.radians(1.5)
    sun_obj = bpy.data.objects.new("Sun_Montreal", light_data)
    sun_obj.rotation_euler = (math.radians(42.0), math.radians(14.0), math.radians(-38.0))
    scene.collection.objects.link(sun_obj)

    fill_data = bpy.data.lights.new("Sun_Fill_Montreal", type="SUN")
    fill_data.energy = 0.55
    fill_data.color = (0.78, 0.86, 1.0)
    fill_data.angle = math.radians(15.0)
    fill_obj = bpy.data.objects.new("Sun_Fill_Montreal", fill_data)
    fill_obj.rotation_euler = (math.radians(55.0), math.radians(-20.0), math.radians(140.0))
    scene.collection.objects.link(fill_obj)


def load_dossier(block_id: str) -> dict:
    p = REPO_ROOT / "data" / "blocks" / block_id / "dossier.json"
    return json.loads(p.read_text(encoding="utf-8"))


_TEX_ALIAS = {
    "concrete_layers_02_": "concrete_pavement_02_",
    "plastered_stone_wall_": "castle_brick_02_white_",
    "red_brick_": "brick_wall_04_",
    "yellow_plaster_": "concrete_block_wall_",
    "stone_wall_": "cobblestone_floor_08_",
    "slate_roof_tiles_": "cobblestone_floor_08_",
    "rusty_metal_02_": "box_profile_metal_sheet_",
    "weathered_planks_": "concrete_block_wall_",
}


def _resolve_tex(path_str: str) -> str:
    if not path_str:
        return ""
    if os.path.isfile(path_str):
        return path_str
    base = os.path.basename(path_str)
    for k, v in _TEX_ALIAS.items():
        if base.startswith(k):
            base = v + base[len(k):]
            break
    variants = [
        base,
        base.replace("_diff_2k.jpg", "_Diffuse_2k.jpg"),
        base.replace("_Diffuse_2k.jpg", "_diff_2k.jpg"),
        base.replace("_rough_2k.jpg", "_Rough_2k.jpg"),
        base.replace("_Rough_2k.jpg", "_rough_2k.jpg"),
    ]
    for cand in variants:
        p_direct = POLYHAVEN_DIR / cand
        if p_direct.is_file():
            return str(p_direct)
    for root, _, files in os.walk(POLYHAVEN_DIR):
        for cand in variants:
            if cand in files:
                return os.path.join(root, cand)
    # Dynamic on-demand Poly Haven fetcher: if asset_id is requested but not yet on disk, fetch 2K maps from Poly Haven API
    for sfx in ("_diff_2k.jpg", "_Diffuse_2k.jpg", "_nor_gl_2k.jpg", "_rough_2k.jpg", "_Rough_2k.jpg"):
        if base.endswith(sfx):
            asset_id = base[: -len(sfx)]
            ensure_polyhaven_pbr_texture(asset_id, res="2k")
            for cand in variants:
                p_direct = POLYHAVEN_DIR / cand
                if p_direct.is_file():
                    return str(p_direct)
            break
    return ""


def ensure_polyhaven_pbr_texture(asset_id: str, res: str = "2k") -> dict:
    """
    Dynamically downloads 2K PBR maps (Diffuse, Roughness, Normal GL) from Poly Haven API
    into `assets/polyhaven/` if not already cached locally, so 3D modelers are never limited
    to the initial 14 textures in the kit.
    """
    import urllib.request
    import ssl

    POLYHAVEN_DIR.mkdir(parents=True, exist_ok=True)
    diff_out = POLYHAVEN_DIR / f"{asset_id}_diff_{res}.jpg"
    rough_out = POLYHAVEN_DIR / f"{asset_id}_rough_{res}.jpg"
    nor_out = POLYHAVEN_DIR / f"{asset_id}_nor_gl_{res}.jpg"

    if diff_out.is_file() and nor_out.is_file():
        return {"diffuse": str(diff_out), "rough": str(rough_out) if rough_out.is_file() else "", "normal": str(nor_out)}

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            f"https://api.polyhaven.com/files/{asset_id}",
            headers={"User-Agent": "Montreal3DTwin/2.0"},
        )
        with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
            files_json = json.loads(resp.read().decode("utf-8"))

        def _grab(keys, target_path):
            if target_path.is_file():
                return
            for k in keys:
                slot = files_json.get(k, {}).get(res, {})
                for fmt in ("jpg", "png"):
                    url = slot.get(fmt, {}).get("url")
                    if url:
                        r2 = urllib.request.Request(url, headers={"User-Agent": "Montreal3DTwin/2.0"})
                        with urllib.request.urlopen(r2, timeout=30, context=ctx) as d_resp:
                            target_path.write_bytes(d_resp.read())
                        print(f"[PolyHaven] Downloaded {target_path.name} ({asset_id})")
                        return

        _grab(["Diffuse", "col", "diff"], diff_out)
        _grab(["Rough", "rough", "Roughness"], rough_out)
        _grab(["nor_gl", "nor_dx"], nor_out)
    except Exception as e:
        print(f"[PolyHaven] Warning fetching {asset_id}: {e}")

    return {
        "diffuse": str(diff_out) if diff_out.is_file() else "",
        "rough": str(rough_out) if rough_out.is_file() else "",
        "normal": str(nor_out) if nor_out.is_file() else "",
    }


def create_pbr_material(
    name: str,
    base_color=(0.75, 0.75, 0.75, 1.0),
    roughness: float = 0.6,
    metallic: float = 0.0,
    ior: float = 1.45,
    diffuse_tex: str = "",
    normal_tex: str = "",
    rough_tex: str = "",
    tint_color=None,
    tint_strength: float = 0.5,
    uv_scale: float = 0.25,
) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (uv_scale, uv_scale, uv_scale)
    links.new(tcoord.outputs["Object"], mapping.inputs["Vector"])

    d_path = _resolve_tex(diffuse_tex)
    if d_path:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = bpy.data.images.load(d_path, check_existing=True)
        tex_d.projection = "BOX"
        tex_d.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])
        if tint_color is not None:
            mix = nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MIX"
            mix.inputs["Factor"].default_value = tint_strength
            mix.inputs[6].default_value = (tint_color[0], tint_color[1], tint_color[2], 1.0)
            links.new(tex_d.outputs["Color"], mix.inputs[7])
            links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        else:
            links.new(tex_d.outputs["Color"], bsdf.inputs["Base Color"])
    elif tint_color is not None:
        bsdf.inputs["Base Color"].default_value = (tint_color[0], tint_color[1], tint_color[2], 1.0)

    r_path = _resolve_tex(rough_tex)
    if r_path:
        tex_r = nodes.new("ShaderNodeTexImage")
        img_r = bpy.data.images.load(r_path, check_existing=True)
        try:
            img_r.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
        tex_r.image = img_r
        tex_r.projection = "BOX"
        tex_r.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_r.inputs["Vector"])
        links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])

    n_path = _resolve_tex(normal_tex)
    if n_path:
        tex_n = nodes.new("ShaderNodeTexImage")
        img_n = bpy.data.images.load(n_path, check_existing=True)
        try:
            img_n.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
        tex_n.image = img_n
        tex_n.projection = "BOX"
        tex_n.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = 1.0
        links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def ensure_landmark_3d_fenestration(obj: bpy.types.Object):
    """
    Rule RSI-010 Universal Landmark 3D Fenestration Gate:
    Inspects all large vertical quad wall faces (`height >= 5.5m`, `width >= 5.2m`) on
    custom Hero/Landmark meshes and populates them with floor-by-floor 3D dark-glass
    window panes, white frames, projecting stone sills, horizontal spandrel courses,
    and roof cornices across all exterior sides (plus 4-sided clockfaces on clocktowers).
    """
    if not obj or obj.type != "MESH" or not obj.data.polygons:
        return
    if any(tag in obj.name for tag in ("MTL_Bldg_", "Streets", "Sidewalks", "Markings", "Ground", "Water", "StreetLamp", "Tree", "Bench", "Hydrant")):
        return

    mats = obj.data.materials
    glass_idx = None
    trim_idx = None
    stone_idx = None
    skip_mat_indices = set()

    for idx_m, m in enumerate(mats):
        if not m:
            continue
        mname = m.name.lower()
        if "glass" in mname or "window" in mname:
            if glass_idx is None:
                glass_idx = idx_m
            skip_mat_indices.add(idx_m)
        elif "white" in mname or "trim" in mname:
            if trim_idx is None:
                trim_idx = idx_m
        elif any(w in mname for w in ("limestone", "podium", "sandstone", "concrete_block")):
            if stone_idx is None:
                stone_idx = idx_m
        if any(w in mname for w in ("water", "grass", "asphalt", "green_steel", "copper", "slates", "bitumen", "gravel")):
            skip_mat_indices.add(idx_m)

    if glass_idx is None:
        return
    if trim_idx is None:
        trim_idx = glass_idx
    if stone_idx is None:
        stone_idx = trim_idx

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    uz = Vector((0.0, 0.0, 1.0))

    wall_candidates = []
    for f in list(bm.faces):
        if len(f.verts) != 4 or f.material_index in skip_mat_indices:
            continue
        n = f.normal
        if abs(n.z) > 0.16 or n.length < 0.5:
            continue
        zs = [v.co.z for v in f.verts]
        z_min, z_max = min(zs), max(zs)
        dz = z_max - z_min
        if dz < 5.5 or z_min > 42.0:
            continue
        u_out = Vector((n.x, n.y, 0.0)).normalized()
        u_tan = Vector((-u_out.y, u_out.x, 0.0)).normalized()
        ts = [v.co.dot(u_tan) for v in f.verts]
        w = max(ts) - min(ts)
        if w < 5.2 or w > 135.0:
            continue
        fc = f.calc_center_median()
        wall_candidates.append((fc, u_tan, u_out, w, z_min, z_max, dz))

    for fc, u_tan, u_out, w, z_min, z_max, dz in wall_candidates:
        base_center = Vector((fc.x, fc.y, z_min))
        # Top projecting cornice band along wall
        add_box_local(bm, base_center + u_out * 0.14 + uz * (dz - 0.22), u_tan, u_out, uz, w + 0.16, 0.28, 0.34, mat_idx=stone_idx)

        # Clocktower 4-sided clock dial detection (e.g. Molson Clocktower: w ~ 11.5m, dz ~ 32m)
        if 26.0 <= dz <= 36.0 and 8.5 <= w <= 14.0:
            clk_pos = base_center + u_out * 0.16 + uz * (dz - 3.6)
            add_box_local(bm, clk_pos, u_tan, u_out, uz, 3.8, 0.22, 3.8, mat_idx=trim_idx)
            add_box_local(bm, clk_pos + u_out * 0.08, u_tan, u_out, uz, 0.22, 0.12, 1.5, mat_idx=glass_idx)
            add_box_local(bm, clk_pos + u_out * 0.08, u_tan, u_out, uz, 1.2, 0.12, 0.22, mat_idx=glass_idx)

        n_floors = max(1, min(22, int(round(dz / 3.6))))
        floor_h = (dz - 0.70) / n_floors
        n_cols = max(2, min(16, int(round(w / 3.6))))
        bay_w = w / n_cols
        win_w = min(1.95, bay_w * 0.56)
        win_h = min(1.75, floor_h * 0.54)

        for r_fl in range(n_floors):
            z_fl = 0.45 + (r_fl + 0.52) * floor_h
            # Horizontal spandrel belt course every floor on tall towers or every 2 floors on halls
            if dz >= 24.0 or (r_fl % 2 == 1):
                sp_pos = base_center + u_out * 0.08 + uz * (0.35 + r_fl * floor_h)
                add_box_local(bm, sp_pos, u_tan, u_out, uz, w + 0.08, 0.16, 0.20, mat_idx=stone_idx)
            for c_bay in range(n_cols):
                x_off = -0.5 * w + (c_bay + 0.5) * bay_w
                w_pos = base_center + u_tan * x_off + uz * z_fl
                add_box_local(bm, w_pos + u_out * 0.06, u_tan, u_out, uz, win_w + 0.22, 0.12, win_h + 0.20, mat_idx=trim_idx)
                add_box_local(bm, w_pos + u_out * 0.11, u_tan, u_out, uz, win_w, 0.08, win_h, mat_idx=glass_idx)
                add_box_local(bm, w_pos + u_out * 0.15 - uz * (win_h * 0.5 + 0.08), u_tan, u_out, uz, win_w + 0.32, 0.24, 0.14, mat_idx=stone_idx)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def apply_world_box_uv(obj: bpy.types.Object, scale: float = 0.25):
    if not obj or obj.type != "MESH" or not obj.data.polygons:
        return
    ensure_landmark_3d_fenestration(obj)
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


def _iter_shapely_polygons(geom):
    if geom is None or geom.is_empty:
        return
    gtype = geom.geom_type
    if gtype == "Polygon":
        if geom.area >= 0.18:
            yield geom
    elif gtype in ("MultiPolygon", "GeometryCollection"):
        for sub in geom.geoms:
            yield from _iter_shapely_polygons(sub)


def _iter_shapely_lines(geom):
    if geom is None or geom.is_empty:
        return
    gtype = geom.geom_type
    if gtype == "LineString":
        if geom.length >= 0.40:
            yield geom
    elif gtype in ("MultiLineString", "GeometryCollection"):
        for sub in geom.geoms:
            yield from _iter_shapely_lines(sub)


def _densify_ring_xy(coords_xy, max_step: float = 3.2):
    pts = [(float(c[0]), float(c[1])) for c in coords_xy]
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-4:
        pts = pts[:-1]
    if len(pts) < 3:
        return []
    out = []
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        dist = math.hypot(x1 - x0, y1 - y0)
        if dist < 0.03:
            continue
        steps = max(1, int(math.ceil(dist / max_step)))
        for s in range(steps):
            t = s / float(steps)
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


def _extrude_shapely_to_bmesh(
    bm: bmesh.types.BMesh,
    geom,
    z_bot,
    z_top: float,
    mat_idx_top: int,
    mat_idx_side: int = None,
    max_step: float = 3.2,
):
    if mat_idx_side is None:
        mat_idx_side = mat_idx_top
    for poly in _iter_shapely_polygons(geom):
        p_clean = poly.simplify(0.03, preserve_topology=True).buffer(0)
        for sub_p in _iter_shapely_polygons(p_clean):
            ext_pts = _densify_ring_xy(sub_p.exterior.coords, max_step=max_step)
            if len(ext_pts) < 3:
                continue
            hole_rings = []
            for inter in sub_p.interiors:
                if Polygon(inter).area >= 0.15:
                    hr = _densify_ring_xy(inter.coords, max_step=max_step)
                    if len(hr) >= 3:
                        hole_rings.append(hr)

            all_rings = [ext_pts] + hole_rings
            loops_3d = [[Vector((x, y, z_top)) for x, y in r] for r in all_rings]
            flat_bm_verts = []
            for r in all_rings:
                for x, y in r:
                    flat_bm_verts.append(bm.verts.new(Vector((x, y, z_top))))

            try:
                tris = mathutils.geometry.tessellate_polygon(loops_3d)
            except Exception:
                tris = []

            for i0, i1, i2 in tris:
                if i0 == i1 or i1 == i2 or i2 == i0:
                    continue
                v0, v1, v2 = flat_bm_verts[i0], flat_bm_verts[i1], flat_bm_verts[i2]
                n_z = (v1.co - v0.co).cross(v2.co - v0.co).z
                if abs(n_z) < 1e-7:
                    continue
                tri_verts = (v0, v1, v2) if n_z > 0 else (v0, v2, v1)
                try:
                    f = bm.faces.new(tri_verts)
                    f.material_index = mat_idx_top
                except ValueError:
                    pass

            if z_bot is not None and z_top > z_bot:
                offset = 0
                for r in all_rings:
                    nr = len(r)
                    top_ring = flat_bm_verts[offset : offset + nr]
                    bot_ring = [bm.verts.new(Vector((x, y, z_bot))) for x, y in r]
                    offset += nr
                    for k in range(nr):
                        kn = (k + 1) % nr
                        try:
                            f_side = bm.faces.new((bot_ring[k], bot_ring[kn], top_ring[kn], top_ring[k]))
                            f_side.material_index = mat_idx_side
                        except ValueError:
                            pass


def build_ground_and_streets(col: bpy.types.Collection, dossier: dict):
    sat = dossier.get("satellite", {})
    cx, cy = sat.get("center_xy_m", dossier.get("blender_center_xy_m", [0.0, 0.0]))
    cx, cy = float(cx), float(cy)
    span = float(sat.get("span_meters", 280.0))
    half = span * 0.68

    mat_asphalt = create_pbr_material(
        "Mat_MTL_Base_Asphalt",
        base_color=(0.17, 0.17, 0.19, 1.0),
        roughness=0.84,
        diffuse_tex=str(POLYHAVEN_DIR / "textures" / "asphalt_02" / "asphalt_02_diff_2k.jpg"),
        normal_tex=str(POLYHAVEN_DIR / "textures" / "asphalt_02" / "asphalt_02_nor_gl_2k.jpg"),
        tint_color=(0.17, 0.17, 0.19),
        tint_strength=0.72,
        uv_scale=0.18,
    )
    mat_paving = create_pbr_material(
        "Mat_MTL_Concrete_Sidewalk",
        base_color=(0.56, 0.54, 0.50, 1.0),
        roughness=0.78,
        diffuse_tex=str(POLYHAVEN_DIR / "textures" / "concrete_layers_02" / "concrete_layers_02_diff_2k.jpg"),
        normal_tex=str(POLYHAVEN_DIR / "textures" / "concrete_layers_02" / "concrete_layers_02_nor_gl_2k.jpg"),
        tint_color=(0.56, 0.54, 0.50),
        tint_strength=0.62,
        uv_scale=0.22,
    )
    mat_park_grass = create_pbr_material(
        "Mat_MTL_Park_Ground_Grass",
        base_color=(0.19, 0.35, 0.14, 1.0),
        roughness=0.88,
        diffuse_tex=str(POLYHAVEN_DIR / "textures" / "leafy_grass" / "leafy_grass_diff_2k.jpg"),
        normal_tex=str(POLYHAVEN_DIR / "textures" / "leafy_grass" / "leafy_grass_nor_gl_2k.jpg"),
        tint_color=(0.19, 0.35, 0.14),
        tint_strength=0.62,
        uv_scale=0.20,
    )

    # 1. Base Ground Slab (Z = 0.0m — urban ground base strictly bounding the block)
    mesh_g = bpy.data.meshes.new("MTL_Ground_Base")
    obj_g = bpy.data.objects.new("MTL_Ground_Base", mesh_g)
    col.objects.link(obj_g)
    obj_g.data.materials.append(mat_paving)
    bm_g = bmesh.new()
    v0 = bm_g.verts.new(Vector((cx - half, cy - half, 0.0)))
    v1 = bm_g.verts.new(Vector((cx + half, cy - half, 0.0)))
    v2 = bm_g.verts.new(Vector((cx + half, cy + half, 0.0)))
    v3 = bm_g.verts.new(Vector((cx - half, cy + half, 0.0)))
    bm_g.faces.new((v0, v1, v2, v3))
    bm_g.to_mesh(mesh_g)
    bm_g.free()
    apply_world_box_uv(obj_g, scale=0.18)

    ground_clip_box = box(cx - half + 0.35, cy - half + 0.35, cx + half - 0.35, cy + half - 0.35)

    # Build water keepout union
    block_id_str = str(dossier.get("block_id", ""))
    water_max_x_map = {
        "MTL-OLY-0002": 852.0,
        "MTL-OLY-0003": 1038.0,
        "MTL-VM-0040": 725.0,
        "MTL-VM-0039": 822.0,
    }
    water_max_x = water_max_x_map.get(block_id_str, 999999.0)
    water_polys = []
    if water_max_x < 999999.0:
        water_polys.append(box(water_max_x, cy - half * 3.0, cx + half * 5.0, cy + half * 3.0))
    for w_feat in dossier.get("osm_features", {}).get("water", []) + dossier.get("osm_features", {}).get("waterways", []):
        w_pts = w_feat.get("coords_xy", [])
        if len(w_pts) >= 3:
            try:
                wp = Polygon([(float(p[0]), float(p[1])) for p in w_pts]).buffer(0)
                if not wp.is_empty and wp.area >= 5.0:
                    water_polys.append(wp)
            except Exception:
                pass
    water_union = unary_union(water_polys) if water_polys else Polygon()

    # Build building keepout union so sidewalks/curbs/parks never slice through building footprints
    bldg_polys = []
    raw_bldgs = dossier.get("osm_features", {}).get("buildings", []) or dossier.get("buildings", [])
    for b_item in raw_bldgs:
        b_pts = b_item.get("coords_xy") or b_item.get("footprint_xy") or []
        if len(b_pts) >= 3:
            try:
                bp = Polygon([(float(p[0]), float(p[1])) for p in b_pts]).buffer(0)
                if not bp.is_empty and 4.0 <= bp.area <= 90000.0:
                    bldg_polys.append(bp)
            except Exception:
                pass
    # Also include any already-instantiated 3D building meshes in bpy.data.objects
    for existing_o in bpy.data.objects:
        if existing_o.type == "MESH" and not existing_o.hide_render:
            oname = existing_o.name
            if any(k in oname for k in ("Bldg", "Building", "Hero", "Landmark", "Tower", "Basilica", "BMO", "Aldred", "Hotel", "Palais", "Chateau", "Marche", "Casino", "Biosphere", "Molson", "Lantic", "Viger")):
                if not any(skip_k in oname for skip_k in ("Bridge", "Pont", "Viaduct", "Pergola", "Canopy")):
                    vs_w = [existing_o.matrix_world @ v.co for v in existing_o.data.vertices]
                    if vs_w:
                        z_min = min(v.z for v in vs_w)
                        z_max = max(v.z for v in vs_w)
                        if z_max - z_min >= 3.8 and z_min <= 2.5:
                            low_vs = [(v.x, v.y) for v in vs_w if v.z <= z_min + 3.5]
                            if len(low_vs) >= 4:
                                try:
                                    hull = MultiPoint_hull = Polygon(low_vs).convex_hull if len(low_vs) < 25 else None
                                except Exception:
                                    pass
    building_union = unary_union(bldg_polys).buffer(0.08) if bldg_polys else Polygon()

    # 2. Extract & Classify True Street Centerlines from OSM Highways (Strictly Omitting Footway/Crossing Spaghetti!)
    highways = dossier.get("osm_features", {}).get("highways", [])
    street_records = []
    walkway_lines = []

    for idx_h, hw in enumerate(highways):
        pts = hw.get("coords_xy", [])
        if len(pts) < 2:
            continue
        hw_tags = hw.get("tags", {})
        if (
            hw_tags.get("bridge") in ("yes", "viaduct", "cantilever")
            or hw_tags.get("tunnel") in ("yes", "building_passage")
            or hw_tags.get("route") == "ferry"
            or hw_tags.get("indoor") == "yes"
        ):
            continue
        htype = str(hw_tags.get("highway", "residential")).lower()
        footway_sub = str(hw_tags.get("footway", "")).lower()
        service_sub = str(hw_tags.get("service", "")).lower()
        hw_name = str(hw_tags.get("name", "")).strip()

        # STRICT RULE: Never turn OSM `footway=sidewalk` or `footway=crossing` or `steps`/`cycleway`/`path` into street/sidewalk strips!
        if htype in ("footway", "path", "steps", "corridor", "cycleway", "bridleway", "track", "proposed", "construction", "platform", "elevator"):
            continue
        if footway_sub in ("sidewalk", "crossing", "access_aisle", "traffic_island"):
            continue
        if htype == "service" and service_sub in ("parking_aisle", "driveway", "alley", "drive-through", "emergency_access", "yard", "spur", "siding"):
            continue

        clean_xy = []
        for p in pts:
            x, y = float(p[0]), float(p[1])
            if not clean_xy or math.hypot(x - clean_xy[-1][0], y - clean_xy[-1][1]) >= 0.25:
                clean_xy.append((x, y))
        if len(clean_xy) < 2:
            continue

        try:
            line = LineString(clean_xy).intersection(ground_clip_box)
            if not water_union.is_empty:
                line = line.difference(water_union)
        except Exception:
            continue

        for sub_line in _iter_shapely_lines(line):
            if sub_line.length < 1.5:
                continue
            if htype == "pedestrian":
                # Named pedestrian streets (e.g. Place Jacques-Cartier) get paved plaza carriageway without yellow road markings
                if hw_name:
                    walkway_lines.append((sub_line, 4.2))
                continue
            if htype == "service":
                street_records.append({
                    "line": sub_line,
                    "half_w": 3.0,
                    "sw_w": 0.0,
                    "is_arterial": False,
                    "is_collector": False,
                    "is_service": True,
                    "name": hw_name or f"service_{idx_h}",
                })
            elif htype in ("primary", "secondary", "trunk", "primary_link", "secondary_link", "trunk_link"):
                street_records.append({
                    "line": sub_line,
                    "half_w": 5.6,
                    "sw_w": 2.2,
                    "is_arterial": True,
                    "is_collector": False,
                    "is_service": False,
                    "name": hw_name or f"arterial_{idx_h}",
                })
            elif htype in ("tertiary", "tertiary_link"):
                street_records.append({
                    "line": sub_line,
                    "half_w": 4.5,
                    "sw_w": 2.0,
                    "is_arterial": False,
                    "is_collector": True,
                    "is_service": False,
                    "name": hw_name or f"collector_{idx_h}",
                })
            elif htype in ("residential", "unclassified", "living_street", "road"):
                street_records.append({
                    "line": sub_line,
                    "half_w": 3.8,
                    "sw_w": 1.8,
                    "is_arterial": False,
                    "is_collector": False,
                    "is_service": False,
                    "name": hw_name or f"local_{idx_h}",
                })

    # Fallback: if a waterfront/park block has zero vehicular OSM streets inside `ground_clip_box`, synthesize clean perimeter/camera streets
    if not street_records:
        cams_fb = dossier.get("streetview_cameras", [])
        cam_xy_fb = [(float(c["blender_cam_xy_m"][0]), float(c["blender_cam_xy_m"][1]), float(c.get("heading_deg", 0.0))) for c in cams_fb if "blender_cam_xy_m" in c]
        for idx_c, (cx_c, cy_c, hdg_c) in enumerate(cam_xy_fb[:2]):
            rad_c = math.radians(hdg_c)
            dx_c, dy_c = math.sin(rad_c), math.cos(rad_c)
            p_a = (cx_c - dx_c * 45.0, cy_c - dy_c * 45.0)
            p_b = (cx_c + dx_c * 65.0, cy_c + dy_c * 65.0)
            l_fb = LineString([p_a, p_b]).intersection(ground_clip_box)
            if not water_union.is_empty:
                l_fb = l_fb.difference(water_union)
            for sl in _iter_shapely_lines(l_fb):
                street_records.append({
                    "line": sl,
                    "half_w": 4.2,
                    "sw_w": 2.0,
                    "is_arterial": idx_c == 0,
                    "is_collector": True,
                    "is_service": False,
                    "name": f"cam_corridor_{idx_c}",
                })

    # Merge connected street segments by street name + properties so continuous streets are single LineStrings
    grouped_by_name = {}
    for rec in street_records:
        key = (rec["name"], rec["half_w"], rec["sw_w"], rec["is_arterial"], rec["is_collector"], rec["is_service"])
        grouped_by_name.setdefault(key, []).append(rec["line"])

    merged_streets = []
    for (name, half_w, sw_w, is_art, is_coll, is_serv), lines_list in grouped_by_name.items():
        try:
            m_geom = linemerge(unary_union(lines_list))
        except Exception:
            m_geom = unary_union(lines_list)
        for sl in _iter_shapely_lines(m_geom):
            if sl.length >= 2.0:
                merged_streets.append({
                    "line": sl,
                    "half_w": half_w,
                    "sw_w": sw_w,
                    "is_arterial": is_art,
                    "is_collector": is_coll,
                    "is_service": is_serv,
                    "name": name,
                })

    # 3. Compute True Street Intersections & Parallel Offset Shells (`road_union`, `curb_union`, `sidewalk_union`)
    curb_w = 0.22
    sw_default_w = 2.0
    road_buffers_unclipped = []
    non_service_zone_buffers = []

    for st in merged_streets:
        ln = st["line"]
        hw = st["half_w"]
        sw = st["sw_w"]
        # Extend endpoints that touch the outer ground_clip_box boundary slightly so sidewalks/curbs don't wrap across road exits
        coords_l = list(ln.coords)
        if len(coords_l) >= 2:
            p0_x, p0_y = coords_l[0]
            p1_x, p1_y = coords_l[1]
            v0_x, v0_y = p0_x - p1_x, p0_y - p1_y
            v0_len = math.hypot(v0_x, v0_y)
            if v0_len > 1e-4 and ground_clip_box.exterior.distance(Point(p0_x, p0_y)) < 1.2:
                coords_l[0] = (p0_x + (v0_x / v0_len) * 5.0, p0_y + (v0_y / v0_len) * 5.0)
            pm_x, pm_y = coords_l[-1]
            pn_x, pn_y = coords_l[-2]
            vm_x, vm_y = pm_x - pn_x, pm_y - pn_y
            vm_len = math.hypot(vm_x, vm_y)
            if vm_len > 1e-4 and ground_clip_box.exterior.distance(Point(pm_x, pm_y)) < 1.2:
                coords_l[-1] = (pm_x + (vm_x / vm_len) * 5.0, pm_y + (vm_y / vm_len) * 5.0)
            ln_ext = LineString(coords_l)
        else:
            ln_ext = ln

        road_buffers_unclipped.append(ln_ext.buffer(hw, cap_style="flat", join_style="round", quad_segs=8))
        if sw > 0.0 and not st["is_service"]:
            non_service_zone_buffers.append(ln_ext.buffer(hw + curb_w + sw + 0.8, cap_style="flat", join_style="round", quad_segs=8))

    def _line_dir_at(ln: LineString, pt: Point):
        d_proj = ln.project(pt)
        d0 = max(0.0, d_proj - 1.5)
        d1 = min(ln.length, d_proj + 1.5)
        if d1 - d0 < 0.2:
            p0, p1 = ln.coords[0], ln.coords[-1]
        else:
            p0 = ln.interpolate(d0).coords[0]
            p1 = ln.interpolate(d1).coords[0]
        vx, vy = p1[0] - p0[0], p1[1] - p0[1]
        vlen = math.hypot(vx, vy)
        return (vx / vlen, vy / vlen) if vlen > 1e-5 else (1.0, 0.0)

    # Smooth concave intersection corners with morphological closing (.buffer(0.85).buffer(-0.85))
    # Do NOT subtract building_union from road_union so overhead viaducts/skybridges never punch holes in street asphalt!
    road_unclipped = unary_union(road_buffers_unclipped).buffer(0.85, join_style="round").buffer(-0.85, join_style="round") if road_buffers_unclipped else Polygon()
    road_union = road_unclipped.intersection(ground_clip_box) if not road_unclipped.is_empty else Polygon()
    if not water_union.is_empty and not road_union.is_empty:
        road_union = road_union.difference(water_union)

    global _LAST_ROAD_UNION, _LAST_GROUND_CLIP_BOX
    _LAST_ROAD_UNION = road_union
    _LAST_GROUND_CLIP_BOX = ground_clip_box

    # CRITICAL GUARANTEE: `curb_union` and `sidewalk_union` are parallel offset shells OUTSIDE `road_unclipped`!
    # Therefore it is 100% impossible for any sidewalk or curb to ever overlay or cross any street pavement!
    non_service_zone = unary_union(non_service_zone_buffers) if non_service_zone_buffers else Polygon()
    curb_outer_unclipped = road_unclipped.buffer(curb_w, join_style="round", quad_segs=8) if not road_unclipped.is_empty else Polygon()
    sw_outer_unclipped = road_unclipped.buffer(curb_w + sw_default_w, join_style="round", quad_segs=8) if not road_unclipped.is_empty else Polygon()

    curb_union = curb_outer_unclipped.difference(road_unclipped.buffer(0.015)).intersection(ground_clip_box) if not curb_outer_unclipped.is_empty else Polygon()
    if not non_service_zone.is_empty and not curb_union.is_empty:
        curb_union = curb_union.intersection(non_service_zone)
    if not water_union.is_empty and not curb_union.is_empty:
        curb_union = curb_union.difference(water_union)
    if not building_union.is_empty and not curb_union.is_empty:
        curb_union = curb_union.difference(building_union)

    sidewalk_union = sw_outer_unclipped.difference(curb_outer_unclipped.buffer(0.01)).intersection(ground_clip_box) if not sw_outer_unclipped.is_empty else Polygon()
    if not non_service_zone.is_empty and not sidewalk_union.is_empty:
        sidewalk_union = sidewalk_union.intersection(non_service_zone)
    if not water_union.is_empty and not sidewalk_union.is_empty:
        sidewalk_union = sidewalk_union.difference(water_union)
    if not building_union.is_empty and not sidewalk_union.is_empty:
        sidewalk_union = sidewalk_union.difference(building_union)

    road_keepout = road_union.buffer(0.03) if not road_union.is_empty else Polygon()
    curb_raw = curb_outer_unclipped.intersection(ground_clip_box) if not curb_outer_unclipped.is_empty else Polygon()
    sw_raw = sw_outer_unclipped.intersection(ground_clip_box) if not sw_outer_unclipped.is_empty else Polygon()
    dossier["_road_union"] = road_union

    # 4. Build Non-Overlapping Park Grass Polygons (`MTL_OSM_Parks_Grass`, clipped against streets, sidewalks & buildings)
    parks = dossier.get("osm_features", {}).get("parks_squares", [])
    if parks:
        park_polys = []
        for pk in parks:
            pts = pk.get("coords_xy", [])
            if len(pts) < 3:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if (max(xs) - min(xs)) > 480.0:
                continue
            try:
                pp = Polygon([(float(p[0]), float(p[1])) for p in pts]).buffer(0)
                if not pp.is_empty and pp.area >= 4.0:
                    park_polys.append(pp)
            except Exception:
                pass
        if park_polys:
            park_union = unary_union(park_polys).intersection(ground_clip_box)
            street_and_sw_keepout = sw_raw.union(curb_raw).union(road_keepout)
            if not street_and_sw_keepout.is_empty:
                park_union = park_union.difference(street_and_sw_keepout)
            if not water_union.is_empty:
                park_union = park_union.difference(water_union)
            if not building_union.is_empty:
                park_union = park_union.difference(building_union)
            if not park_union.is_empty:
                mesh_p = bpy.data.meshes.new("MTL_OSM_Parks_Grass")
                obj_p = bpy.data.objects.new("MTL_OSM_Parks_Grass", mesh_p)
                col.objects.link(obj_p)
                obj_p.data.materials.append(mat_park_grass)
                bm_p = bmesh.new()
                _extrude_shapely_to_bmesh(bm_p, park_union, z_bot=None, z_top=0.045, mat_idx_top=0, max_step=4.0)
                bmesh.ops.recalc_face_normals(bm_p, faces=bm_p.faces)
                bm_p.to_mesh(mesh_p)
                bm_p.free()
                apply_world_box_uv(obj_p, scale=0.20)

    # 5. Build 3D Street Pavement (`MTL_OSM_Streets_and_Walkways`), 3D Sidewalks & Curbs (`MTL_Sidewalks_and_Curbs`), and 3D Markings (`MTL_Street_Markings`)
    mat_sidewalk = create_pbr_material(
        "Mat_PH_Concrete_Sidewalk",
        base_color=(0.64, 0.62, 0.58, 1.0),
        roughness=0.76,
        diffuse_tex=str(POLYHAVEN_DIR / "concrete_pavement_02_diff_2k.jpg"),
        normal_tex=str(POLYHAVEN_DIR / "concrete_pavement_02_nor_gl_2k.jpg"),
        tint_color=(0.64, 0.62, 0.58),
        tint_strength=0.58,
        uv_scale=0.25,
    )
    mat_curb_granite = create_pbr_material(
        "Mat_MTL_Granite_Plinth",
        base_color=(0.45, 0.43, 0.40, 1.0),
        roughness=0.68,
        diffuse_tex=str(POLYHAVEN_DIR / "stone_block_wall_diff_2k.jpg"),
        normal_tex=str(POLYHAVEN_DIR / "stone_block_wall_nor_gl_2k.jpg"),
        tint_color=(0.45, 0.43, 0.40),
        tint_strength=0.60,
        uv_scale=0.30,
    )
    mat_joint_dark = create_pbr_material(
        "Mat_MTL_Sidewalk_Joint_Dark",
        base_color=(0.22, 0.22, 0.23, 1.0),
        roughness=0.85,
    )
    mat_mark_yellow = create_pbr_material(
        "Mat_Road_Mark_Yellow",
        base_color=(0.92, 0.72, 0.10, 1.0),
        roughness=0.48,
    )
    mat_mark_white = create_pbr_material(
        "Mat_Road_Mark_White",
        base_color=(0.92, 0.93, 0.94, 1.0),
        roughness=0.46,
    )

    mesh_s = bpy.data.meshes.new("MTL_OSM_Streets_and_Walkways")
    obj_s = bpy.data.objects.new("MTL_OSM_Streets_and_Walkways", mesh_s)
    col.objects.link(obj_s)
    obj_s.data.materials.append(mat_asphalt)
    obj_s.data.materials.append(mat_paving)
    bm_s = bmesh.new()

    if not road_union.is_empty:
        _extrude_shapely_to_bmesh(bm_s, road_union, z_bot=0.005, z_top=0.036, mat_idx_top=0, mat_idx_side=0, max_step=3.5)

    if walkway_lines:
        wk_union = unary_union([wl.buffer(ww, cap_style="flat", join_style="round") for wl, ww in walkway_lines])
        wk_union = wk_union.difference(sw_raw.union(curb_raw).union(road_keepout)).intersection(ground_clip_box)
        if not water_union.is_empty:
            wk_union = wk_union.difference(water_union)
        if not building_union.is_empty:
            wk_union = wk_union.difference(building_union)
        if not wk_union.is_empty:
            _extrude_shapely_to_bmesh(bm_s, wk_union, z_bot=0.010, z_top=0.085, mat_idx_top=1, mat_idx_side=1, max_step=3.5)

    mesh_sw = bpy.data.meshes.new("MTL_Sidewalks_and_Curbs")
    obj_sw = bpy.data.objects.new("MTL_Sidewalks_and_Curbs", mesh_sw)
    col.objects.link(obj_sw)
    obj_sw.data.materials.append(mat_sidewalk)
    obj_sw.data.materials.append(mat_curb_granite)
    obj_sw.data.materials.append(mat_joint_dark)
    bm_sw = bmesh.new()

    if not curb_union.is_empty:
        _extrude_shapely_to_bmesh(bm_sw, curb_union, z_bot=0.025, z_top=0.225, mat_idx_top=1, mat_idx_side=1, max_step=1.6)
    if not sidewalk_union.is_empty:
        _extrude_shapely_to_bmesh(bm_sw, sidewalk_union, z_bot=0.025, z_top=0.215, mat_idx_top=0, mat_idx_side=0, max_step=1.8)

    mesh_mk = bpy.data.meshes.new("MTL_Street_Markings")
    obj_mk = bpy.data.objects.new("MTL_Street_Markings", mesh_mk)
    col.objects.link(obj_mk)
    obj_mk.data.materials.append(mat_mark_yellow)
    obj_mk.data.materials.append(mat_mark_white)
    bm_mk = bmesh.new()

    uz = Vector((0.0, 0.0, 1.0))

    def _add_strip_box(bm, p_start: Vector, p_end: Vector, half_w_strip: float, z_bot: float, z_top: float, mat_idx: int):
        seg_v = p_end - p_start
        seg_v.z = 0.0
        if seg_v.length < 0.12:
            return
        lat_v = uz.cross(seg_v.normalized()) * half_w_strip
        b0 = Vector((p_start.x, p_start.y, z_bot)) - lat_v
        b1 = Vector((p_end.x, p_end.y, z_bot)) - lat_v
        b2 = Vector((p_end.x, p_end.y, z_bot)) + lat_v
        b3 = Vector((p_start.x, p_start.y, z_bot)) + lat_v
        t0 = Vector((p_start.x, p_start.y, z_top)) - lat_v
        t1 = Vector((p_end.x, p_end.y, z_top)) - lat_v
        t2 = Vector((p_end.x, p_end.y, z_top)) + lat_v
        t3 = Vector((p_start.x, p_start.y, z_top)) + lat_v
        vb = [bm.verts.new(p) for p in (b0, b1, b2, b3)]
        vt = [bm.verts.new(p) for p in (t0, t1, t2, t3)]
        for q in (
            (vt[0], vt[1], vt[2], vt[3]),
            (vb[0], vb[1], vt[1], vt[0]),
            (vb[1], vb[2], vt[2], vt[1]),
            (vb[2], vb[3], vt[3], vt[2]),
            (vb[3], vb[0], vt[0], vt[3]),
        ):
            try:
                f = bm.faces.new(q)
                f.material_index = mat_idx
            except ValueError:
                pass

    # Add transverse sidewalk expansion joints strictly inside `sidewalk_union`
    sw_safe = sidewalk_union.buffer(-0.06) if not sidewalk_union.is_empty else Polygon()
    for st in merged_streets:
        if st["is_service"] or st["sw_w"] <= 0.0:
            continue
        ln = st["line"]
        hw = st["half_w"]
        sw = st["sw_w"]
        d_j = 3.0
        while d_j < ln.length - 1.5:
            pt_c = ln.interpolate(d_j)
            pt_n = ln.interpolate(min(ln.length, d_j + 0.25))
            tx, ty = pt_n.x - pt_c.x, pt_n.y - pt_c.y
            tlen = math.hypot(tx, ty)
            if tlen > 1e-4:
                tx, ty = tx / tlen, ty / tlen
                rx, ry = -ty, tx
                for side_s in (-1.0, 1.0):
                    r_inner = hw + curb_w + 0.08
                    r_outer = hw + curb_w + sw - 0.08
                    pa_xy = (pt_c.x + side_s * rx * r_inner, pt_c.y + side_s * ry * r_inner)
                    pb_xy = (pt_c.x + side_s * rx * r_outer, pt_c.y + side_s * ry * r_outer)
                    j_line = LineString([pa_xy, pb_xy])
                    if not sw_safe.is_empty and sw_safe.contains(j_line):
                        _add_strip_box(
                            bm_sw,
                            Vector((pa_xy[0], pa_xy[1], 0.0)),
                            Vector((pb_xy[0], pb_xy[1], 0.0)),
                            0.028,
                            0.215,
                            0.221,
                            mat_idx=2,
                        )
            d_j += 4.2

    # 6. Proper Crossing Markings (Continental Zebra Crosswalks + Stop Bars) & Intersection-Trimmed Centerlines
    z_mk_bot = 0.036
    z_mk_top = 0.048
    road_safe = road_union.buffer(-0.08) if not road_union.is_empty else Polygon()
    inner_clip_box = ground_clip_box.buffer(-3.0)
    placed_crosswalk_boxes = []
    crosswalk_exclusion_polys = []

    def _place_intersection_crosswalk(p_edge_xy, f_in_xy, half_w_st: float, cross_guard_poly, is_start_end: bool):
        fx, fy = f_in_xy
        rx, ry = -fy, fx
        cw_dist = 2.05
        cx_cw = p_edge_xy[0] + fx * cw_dist
        cy_cw = p_edge_xy[1] + fy * cw_dist
        pt_cw = Point(cx_cw, cy_cw)
        if not inner_clip_box.contains(pt_cw):
            return False

        bar_len = 2.35
        bar_half = bar_len * 0.5
        cw_footprint = LineString([
            (cx_cw - rx * (half_w_st - 0.30), cy_cw - ry * (half_w_st - 0.30)),
            (cx_cw + rx * (half_w_st - 0.30), cy_cw + ry * (half_w_st - 0.30)),
        ]).buffer(bar_half + 0.35, cap_style="flat")

        if any(cw_footprint.intersects(existing_box) for existing_box in placed_crosswalk_boxes):
            return False

        # Verify each crosswalk bar sits strictly inside `road_safe` (and outside the crossing street's interior)
        valid_bars = []
        n_bars = int((half_w_st * 1.80) // 0.90)
        for b_i in range(-n_bars, n_bars + 1):
            lat_off = b_i * 0.90
            if abs(lat_off) > half_w_st - 0.42:
                continue
            bx = cx_cw + rx * lat_off
            by = cy_cw + ry * lat_off
            p_a = (bx - fx * bar_half, by - fy * bar_half)
            p_b = (bx + fx * bar_half, by + fy * bar_half)
            bar_line = LineString([p_a, p_b]).buffer(0.225, cap_style="flat")
            if not road_safe.is_empty and road_safe.contains(bar_line):
                if cross_guard_poly is None or cross_guard_poly.is_empty or not cross_guard_poly.buffer(-0.10).intersects(bar_line):
                    valid_bars.append((p_a, p_b))

        if len(valid_bars) < 3:
            return False

        placed_crosswalk_boxes.append(cw_footprint)
        cw_zone = LineString([
            (p_edge_xy[0], p_edge_xy[1]),
            (p_edge_xy[0] + fx * 4.85, p_edge_xy[1] + fy * 4.85),
        ]).buffer(half_w_st + 0.4, cap_style="flat")
        crosswalk_exclusion_polys.append(cw_zone)

        # Render the parallel Continental Zebra Crosswalk bars (2.35m long x 0.45m wide, crisp white)
        for p_a, p_b in valid_bars:
            _add_strip_box(
                bm_mk,
                Vector((p_a[0], p_a[1], 0.0)),
                Vector((p_b[0], p_b[1], 0.0)),
                0.225,
                z_mk_bot,
                z_mk_top + 0.003,
                mat_idx=1,
            )

        # Render White Stop Bar at d = 4.35m across the approaching right-hand lane
        stop_d = 4.35
        sx_c = p_edge_xy[0] + fx * stop_d
        sy_c = p_edge_xy[1] + fy * stop_d
        # Approaching traffic travels in `-f_in_xy`, so its right-hand side is `+r` (since `(-f) x uz = (-fy, fx) = r`)
        pa_s = (sx_c + rx * 0.25, sy_c + ry * 0.25)
        pb_s = (sx_c + rx * (half_w_st - 0.38), sy_c + ry * (half_w_st - 0.38))
        s_seg = LineString([pa_s, pb_s]).intersection(road_safe)
        for sl_s in _iter_shapely_lines(s_seg):
            if sl_s.length >= 1.3:
                c0, c1 = sl_s.coords[0], sl_s.coords[-1]
                _add_strip_box(
                    bm_mk,
                    Vector((c0[0], c0[1], 0.0)),
                    Vector((c1[0], c1[1], 0.0)),
                    0.21,
                    z_mk_bot,
                    z_mk_top + 0.003,
                    mat_idx=1,
                )
        return True

    # Process each street against all crossing streets
    lamp_candidates = []
    for i, st in enumerate(merged_streets):
        if st["is_service"]:
            continue
        ln = st["line"]
        hw = st["half_w"]
        sw = st["sw_w"]
        is_art = st["is_arterial"]
        is_coll = st["is_collector"]

        # Build union of all other streets that cross or meet `st` at an angle
        cross_buffers = []
        for j, other in enumerate(merged_streets):
            if i == j or other["is_service"]:
                continue
            lo = other["line"]
            if ln.distance(lo) > max(hw, other["half_w"]) + 1.0:
                continue
            inter_test = ln.intersection(lo.buffer(other["half_w"] + 0.8))
            if inter_test.is_empty:
                continue
            da = _line_dir_at(ln, inter_test.centroid)
            db = _line_dir_at(lo, inter_test.centroid)
            dot_ab = abs(da[0] * db[0] + da[1] * db[1])
            if dot_ab < 0.94 or (st["name"] != other["name"] and dot_ab < 0.965):
                cross_buffers.append(lo.buffer(other["half_w"] + 0.15, cap_style="flat", join_style="round"))

        cross_union = unary_union(cross_buffers) if cross_buffers else Polygon()
        trimmed_pieces = ln.difference(cross_union) if not cross_union.is_empty else ln

        for piece in _iter_shapely_lines(trimmed_pieces):
            plen = piece.length
            if plen < 5.0:
                continue

            # Check start endpoint (s = 0) and end endpoint (s = plen) for intersection approaches
            p_start_pt = Point(piece.coords[0])
            p_end_pt = Point(piece.coords[-1])
            trim_start = 0.8
            trim_end = 0.8

            if not cross_union.is_empty and cross_union.distance(p_start_pt) < 0.45 and plen >= 8.0:
                p0_c = piece.coords[0]
                p1_c = piece.interpolate(min(plen, 2.5)).coords[0]
                vx, vy = p1_c[0] - p0_c[0], p1_c[1] - p0_c[1]
                vlen = math.hypot(vx, vy)
                if vlen > 1e-4:
                    _place_intersection_crosswalk(p0_c, (vx / vlen, vy / vlen), hw, cross_union, True)
                    trim_start = 4.85

            if not cross_union.is_empty and cross_union.distance(p_end_pt) < 0.45 and plen >= 8.0:
                p0_c = piece.coords[-1]
                p1_c = piece.interpolate(max(0.0, plen - 2.5)).coords[0]
                vx, vy = p1_c[0] - p0_c[0], p1_c[1] - p0_c[1]
                vlen = math.hypot(vx, vy)
                if vlen > 1e-4:
                    _place_intersection_crosswalk(p0_c, (vx / vlen, vy / vlen), hw, cross_union, False)
                    trim_end = 4.85

            # If a long street has no cross-street inside the block, place a mid-block / camera pedestrian crossing so every block has crisp crosswalks
            if cross_union.is_empty and plen >= 24.0:
                mid_s = plen * 0.5
                p0_c = piece.interpolate(mid_s).coords[0]
                p1_c = piece.interpolate(min(plen, mid_s + 2.5)).coords[0]
                vx, vy = p1_c[0] - p0_c[0], p1_c[1] - p0_c[1]
                vlen = math.hypot(vx, vy)
                if vlen > 1e-4:
                    _place_intersection_crosswalk(p0_c, (vx / vlen, vy / vlen), hw, None, True)

            # Generate Centerlines & Lane Dividers along `[trim_start, plen - trim_end]`
            if plen - trim_end - trim_start >= 3.0:
                cw_keepout = unary_union(crosswalk_exclusion_polys) if crosswalk_exclusion_polys else Polygon()
                d_step = 0.0
                if is_art or is_coll:
                    # Continuous double yellow centerline (broken into 3m segments and checked against cw_keepout)
                    d_cur = trim_start
                    while d_cur + 0.8 < plen - trim_end:
                        d_next = min(plen - trim_end, d_cur + 3.0)
                        pa_c = piece.interpolate(d_cur)
                        pb_c = piece.interpolate(d_next)
                        mid_pt = piece.interpolate(0.5 * (d_cur + d_next))
                        if (cw_keepout.is_empty or not cw_keepout.contains(mid_pt)) and road_safe.contains(mid_pt):
                            vx, vy = pb_c.x - pa_c.x, pb_c.y - pa_c.y
                            vlen = math.hypot(vx, vy)
                            if vlen > 0.2:
                                rx, ry = -vy / vlen, vx / vlen
                                for dy_c in (-0.14, 0.14):
                                    _add_strip_box(
                                        bm_mk,
                                        Vector((pa_c.x + rx * dy_c, pa_c.y + ry * dy_c, 0.0)),
                                        Vector((pb_c.x + rx * dy_c, pb_c.y + ry * dy_c, 0.0)),
                                        0.055,
                                        z_mk_bot,
                                        z_mk_top,
                                        mat_idx=0,
                                    )
                        d_cur = d_next

                    # White dashed lane dividers on arterial streets (`hw >= 5.2m`)
                    if is_art:
                        d_cur = trim_start + 1.2
                        while d_cur + 2.6 < plen - trim_end - 1.0:
                            pa_c = piece.interpolate(d_cur)
                            pb_c = piece.interpolate(d_cur + 2.6)
                            mid_pt = piece.interpolate(d_cur + 1.3)
                            if (cw_keepout.is_empty or not cw_keepout.contains(mid_pt)) and road_safe.contains(mid_pt):
                                vx, vy = pb_c.x - pa_c.x, pb_c.y - pa_c.y
                                vlen = math.hypot(vx, vy)
                                if vlen > 0.2:
                                    rx, ry = -vy / vlen, vx / vlen
                                    for lane_s in (-2.85, 2.85):
                                        p_l0 = (pa_c.x + rx * lane_s, pa_c.y + ry * lane_s)
                                        p_l1 = (pb_c.x + rx * lane_s, pb_c.y + ry * lane_s)
                                        if road_safe.contains(Point(p_l0)) and road_safe.contains(Point(p_l1)):
                                            _add_strip_box(
                                                bm_mk,
                                                Vector((p_l0[0], p_l0[1], 0.0)),
                                                Vector((p_l1[0], p_l1[1], 0.0)),
                                                0.055,
                                                z_mk_bot,
                                                z_mk_top,
                                                mat_idx=1,
                                            )
                            d_cur += 5.8
                else:
                    # Dashed yellow centerline on residential/local streets
                    d_cur = trim_start + 0.8
                    while d_cur + 2.4 < plen - trim_end - 0.8:
                        pa_c = piece.interpolate(d_cur)
                        pb_c = piece.interpolate(d_cur + 2.4)
                        mid_pt = piece.interpolate(d_cur + 1.2)
                        if (cw_keepout.is_empty or not cw_keepout.contains(mid_pt)) and road_safe.contains(mid_pt):
                            _add_strip_box(
                                bm_mk,
                                Vector((pa_c.x, pa_c.y, 0.0)),
                                Vector((pb_c.x, pb_c.y, 0.0)),
                                0.058,
                                z_mk_bot,
                                z_mk_top,
                                mat_idx=0,
                            )
                        d_cur += 5.2

            # Collect Poly Haven Streetlamp positions strictly on `sidewalk_union` (never on roadways or inside buildings!)
            d_lamp = 4.5
            while d_lamp < plen - 3.5:
                pt_l = piece.interpolate(d_lamp)
                pt_ln = piece.interpolate(min(plen, d_lamp + 0.5))
                vx, vy = pt_ln.x - pt_l.x, pt_ln.y - pt_l.y
                vlen = math.hypot(vx, vy)
                if vlen > 1e-4:
                    rx, ry = -vy / vlen, vx / vlen
                    for side_l in (-1.0, 1.0):
                        lx = pt_l.x + side_l * rx * (hw + curb_w + 0.50)
                        ly = pt_l.y + side_l * ry * (hw + curb_w + 0.50)
                        l_pt = Point(lx, ly)
                        if (
                            ground_clip_box.buffer(-1.5).contains(l_pt)
                            and not road_union.buffer(0.25).contains(l_pt)
                            and (building_union.is_empty or not building_union.buffer(0.35).contains(l_pt))
                        ):
                            rot_z = math.atan2(-side_l * ry, -side_l * rx)
                            lamp_candidates.append((lx, ly, rot_z, is_art))
                d_lamp += 16.0

    for bm_tmp, mesh_tmp, obj_tmp in (
        (bm_s, mesh_s, obj_s),
        (bm_sw, mesh_sw, obj_sw),
        (bm_mk, mesh_mk, obj_mk),
    ):
        bmesh.ops.recalc_face_normals(bm_tmp, faces=bm_tmp.faces)
        bm_tmp.to_mesh(mesh_tmp)
        bm_tmp.free()
        apply_world_box_uv(obj_tmp, scale=0.22)

    # 7. Instantiate Poly Haven Streetlamps (`street_lamp_01` & `street_lamp_02`) with spatial deduplication
    placed_lamps = []
    min_lamp_dist = 10.5
    max_lamps = 96
    cams_l = dossier.get("streetview_cameras", [])
    cam_pts_l = [(float(c["blender_cam_xy_m"][0]), float(c["blender_cam_xy_m"][1])) for c in cams_l if "blender_cam_xy_m" in c]
    lamp_candidates.sort(
        key=lambda item: min((math.hypot(item[0] - cx_c, item[1] - cy_c) for cx_c, cy_c in cam_pts_l), default=300.0)
    )
    for lx, ly, lrot, is_art in lamp_candidates:
        if len(placed_lamps) >= max_lamps:
            break
        if any(math.hypot(lx - px, ly - py) < min_lamp_dist for px, py in placed_lamps):
            continue
        placed_lamps.append((lx, ly))
        lamp_idx = len(placed_lamps)
        asset_name = "street_lamp_02" if (is_art and lamp_idx % 2 == 0) else "street_lamp_01"
        append_kit_object(
            asset_name,
            name=f"MTL_PH_StreetLamp_{lamp_idx:03d}",
            collection=col,
            location=(lx, ly, 0.215),
            rotation_z=lrot,
            scale=1.08 if is_art else 1.0,
        )


_KIT_CACHE = {}


def append_kit_object(
    asset_prefix: str,
    name: str,
    collection: bpy.types.Collection,
    location=(0.0, 0.0, 0.0),
    rotation_z: float = 0.0,
    scale: float = 1.0,
):
    cached_t = _KIT_CACHE.get(asset_prefix)
    try:
        if cached_t is None or cached_t.name not in bpy.data.objects:
            _KIT_CACHE.pop(asset_prefix, None)
    except ReferenceError:
        _KIT_CACHE.pop(asset_prefix, None)

    if asset_prefix not in _KIT_CACHE:
        found_obj = None
        # 1. Check direct Poly Haven 3D model directory (`assets/polyhaven/models/<asset_prefix>/<asset_prefix>.blend`)
        ph_model_blend = POLYHAVEN_DIR / "models" / asset_prefix / f"{asset_prefix}.blend"
        if ph_model_blend.exists():
            with bpy.data.libraries.load(str(ph_model_blend), link=False) as (data_from, data_to):
                data_to.objects = list(data_from.objects)
            mesh_objs = [o for o in data_to.objects if o is not None and o.type == "MESH"]
            if mesh_objs:
                found_obj = mesh_objs[0]
                for extra_o in mesh_objs[1:]:
                    try:
                        bpy.data.objects.remove(extra_o, do_unlink=True)
                    except Exception:
                        pass

                # Add warm emissive luminaire bulb inside Poly Haven streetlamps for atmospheric/night/golden-hour renders
                if "lamp" in asset_prefix.lower() or "lantern" in asset_prefix.lower():
                    mat_bulb = bpy.data.materials.get("Mat_PH_StreetLamp_Bulb_Glow")
                    if mat_bulb is None:
                        mat_bulb = bpy.data.materials.new("Mat_PH_StreetLamp_Bulb_Glow")
                        mat_bulb.use_nodes = True
                        bsdf_b = next((n for n in mat_bulb.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                        if bsdf_b:
                            bsdf_b.inputs["Base Color"].default_value = (1.0, 0.90, 0.72, 1.0)
                            if "Emission Color" in bsdf_b.inputs:
                                bsdf_b.inputs["Emission Color"].default_value = (1.0, 0.88, 0.65, 1.0)
                            if "Emission Strength" in bsdf_b.inputs:
                                bsdf_b.inputs["Emission Strength"].default_value = 14.0
                    bm_l = bmesh.new()
                    bm_l.from_mesh(found_obj.data)
                    zs = [v.co.z for v in bm_l.verts] if bm_l.verts else [0.0, 4.2]
                    top_z = max(zs)
                    bulb_idx = len(found_obj.data.materials)
                    found_obj.data.materials.append(mat_bulb)
                    ret_b = bmesh.ops.create_icosphere(bm_l, subdivisions=2, radius=0.16)
                    for v_b in ret_b.get("verts", []):
                        v_b.co.z += max(3.2, top_z - 0.25)
                        for f_b in v_b.link_faces:
                            f_b.material_index = bulb_idx
                    bm_l.to_mesh(found_obj.data)
                    bm_l.free()

        # 2. Fallback to `assets/montreal_kit.blend`
        if found_obj is None and KIT_BLEND_PATH.exists():
            with bpy.data.libraries.load(str(KIT_BLEND_PATH), link=False) as (data_from, data_to):
                matches = [o for o in data_from.objects if asset_prefix.lower() in o.lower()]
                if matches:
                    data_to.objects = [matches[0]]
            for o in data_to.objects:
                if o is not None:
                    found_obj = o
                    break

        # Rule RSI-010: Whole-Canopy Tree Sanitization & Lush 9-Lobe 3D Summer Foliage Crown (applies to BOTH Step 1 & Step 2 trees, NEVER streetlamps!)
        ap_low = asset_prefix.lower()
        is_tree_asset = any(tk in ap_low for tk in ("tree", "jacaranda", "searsia", "sapling")) and "street" not in ap_low and "lamp" not in ap_low
        if found_obj is not None and found_obj.type == "MESH" and is_tree_asset:
            mat_leaf = bpy.data.materials.get("Mat_PH_Tree_Canopy_Lush_Green")
            if mat_leaf is None:
                mat_leaf = create_pbr_material(
                    "Mat_PH_Tree_Canopy_Lush_Green",
                    base_color=(0.16, 0.36, 0.12, 1.0),
                    roughness=0.82,
                    diffuse_tex=str(POLYHAVEN_DIR / "leafy_grass_diff_2k.jpg"),
                    normal_tex=str(POLYHAVEN_DIR / "leafy_grass_nor_gl_2k.jpg"),
                    tint_color=(0.16, 0.36, 0.12),
                    tint_strength=0.68,
                    uv_scale=0.35,
                )
            bm_t = bmesh.new()
            bm_t.from_mesh(found_obj.data)
            bad_verts = [
                v for v in bm_t.verts
                if math.hypot(v.co.x, v.co.y) > 2.4 or v.co.z > 6.2 or v.co.z < -0.25
            ]
            if bad_verts:
                bmesh.ops.delete(bm_t, geom=bad_verts, context="VERTS")
            leaf_idx = len(found_obj.data.materials)
            found_obj.data.materials.append(mat_leaf)
            lobe_specs = [
                (0.0, 0.0, 5.4, 2.25),
                (1.15, 0.45, 4.6, 1.75),
                (-1.10, 0.55, 4.7, 1.80),
                (0.45, -1.15, 4.5, 1.75),
                (-0.65, -1.05, 4.8, 1.70),
                (0.85, 0.85, 6.0, 1.60),
                (-0.85, -0.75, 6.1, 1.65),
                (0.0, 0.95, 3.8, 1.55),
                (0.0, -0.85, 6.6, 1.50),
            ]
            for lx_o, ly_o, lz_o, lr_o in lobe_specs:
                ret_l = bmesh.ops.create_icosphere(bm_t, subdivisions=2, radius=lr_o)
                for v_l in ret_l.get("verts", []):
                    v_l.co.z *= 0.82
                    ripple = 1.0 + 0.08 * math.sin(v_l.co.x * 3.1 + v_l.co.y * 2.7)
                    v_l.co.x = v_l.co.x * ripple + lx_o
                    v_l.co.y = v_l.co.y * ripple + ly_o
                    v_l.co.z += lz_o
                    for f_l in v_l.link_faces:
                        f_l.material_index = leaf_idx
            bmesh.ops.recalc_face_normals(bm_t, faces=bm_t.faces)
            bm_t.to_mesh(found_obj.data)
            bm_t.free()

        if found_obj is not None and found_obj.data:
            found_obj.data.use_fake_user = True
        _KIT_CACHE[asset_prefix] = found_obj

    template = _KIT_CACHE.get(asset_prefix)
    if template is not None:
        inst = template.copy()
        inst.name = name
        inst.location = location
        inst.rotation_euler = (0.0, 0.0, rotation_z)
        inst.scale = (scale, scale, scale)
        collection.objects.link(inst)
        return inst
    return None


_LAST_ROAD_UNION = None
_LAST_GROUND_CLIP_BOX = None


def sanitize_non_street_pavement_overlays():
    """Remove any custom hero/plaza ground-level horizontal slab faces that accidentally overlay street pavement,
    and remove any context building that extends outside MTL_Ground_Base."""
    global _LAST_ROAD_UNION, _LAST_GROUND_CLIP_BOX
    if _LAST_GROUND_CLIP_BOX is not None and not _LAST_GROUND_CLIP_BOX.is_empty:
        inner_ground = _LAST_GROUND_CLIP_BOX.buffer(-0.5)
        for obj in list(bpy.data.objects):
            if obj.type == "MESH" and obj.name.startswith("MTL_Context_Bldg"):
                mw = obj.matrix_world
                bbox_w = [mw @ Vector(corner) for corner in obj.bound_box]
                if any(not inner_ground.contains(Point(v.x, v.y)) for v in bbox_w):
                    bpy.data.objects.remove(obj, do_unlink=True)

    if _LAST_ROAD_UNION is None or _LAST_ROAD_UNION.is_empty:
        return
    road_guard = _LAST_ROAD_UNION.buffer(-0.10)
    if road_guard.is_empty:
        return

    skip_prefixes = (
        "MTL_Ground_Base",
        "MTL_OSM_Streets_and_Walkways",
        "MTL_Sidewalks_and_Curbs",
        "MTL_Street_Markings",
        "MTL_Park_Paths",
        "MTL_Water_",
        "MTL_PH_StreetLamp",
        "street_lamp",
        "MTL_Tree",
        "Tree_",
        "jacaranda",
        "MTL_Hedge",
        "MTL_Fountain",
        "MTL_Context_Bldg",
        "Bldg_",
        "SV_Cam",
        "Sat_Cam",
    )
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.data:
            continue
        if any(obj.name.startswith(pfx) for pfx in skip_prefixes):
            continue
        # Check if object bounding box intersects ground-level road elevation [0.01m, 0.42m]
        mw = obj.matrix_world
        bbox_w = [mw @ Vector(corner) for corner in obj.bound_box]
        z_min = min(v.z for v in bbox_w)
        z_max = max(v.z for v in bbox_w)
        if z_min > 0.45 or z_max < 0.01:
            continue

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        to_delete = []
        for f in bm.faces:
            verts_w = [mw @ v.co for v in f.verts]
            fz_min = min(v.z for v in verts_w)
            fz_max = max(v.z for v in verts_w)
            # Only delete low horizontal/near-horizontal ground-level slab/courtyard/sidewalk faces between Z=0.01m and Z=0.38m that overlap road pavement
            if fz_max <= 0.38 and fz_min >= -0.05 and (fz_max - fz_min) <= 0.40:
                cx_f = sum(v.x for v in verts_w) / len(verts_w)
                cy_f = sum(v.y for v in verts_w) / len(verts_w)
                if road_guard.contains(Point(cx_f, cy_f)) or any(road_guard.contains(Point(v.x, v.y)) for v in verts_w):
                    to_delete.append(f)
        if to_delete:
            bmesh.ops.delete(bm, geom=to_delete, context="FACES")
            bm.to_mesh(obj.data)
            obj.data.update()
            print(f"[SANITIZE] Trimmed {len(to_delete)} pavement-overlaying slab faces from {obj.name}")
        bm.free()


def export_block_artifacts(block_id: str, owned_col: bpy.types.Collection):
    try:
        sanitize_non_street_pavement_overlays()
    except Exception as e:
        print(f"[WARN] sanitize_non_street_pavement_overlays warning: {e}")

    out_dir = REPO_ROOT / "output" / "blocks"
    out_dir.mkdir(parents=True, exist_ok=True)
    blend_path = out_dir / f"{block_id}.blend"
    usdc_path = out_dir / f"{block_id}.usdc"

    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"[WARN] pack_all warning: {e}")

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[EXPORT] Saved packed .blend: {blend_path}")

    try:
        bpy.ops.wm.usd_export(
            filepath=str(usdc_path),
            selected_objects_only=False,
            export_materials=True,
        )
        print(f"[EXPORT] Saved .usdc: {usdc_path}")
    except Exception as e:
        print(f"[WARN] USD export warning: {e}")


# ==============================================================================
# EXPANDED 26-MATERIAL POLY HAVEN 2K PBR PALETTE & PARAMETRIC 3D BUILDING ENGINE
# ==============================================================================

def add_box_local(
    bm: bmesh.types.BMesh,
    center: Vector,
    ux: Vector,
    uy: Vector,
    uz: Vector,
    sx: float,
    sy: float,
    sz: float,
    mat_idx: int = 0,
):
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    corners = [
        center - ux * hx - uy * hy - uz * hz,
        center + ux * hx - uy * hy - uz * hz,
        center + ux * hx + uy * hy - uz * hz,
        center - ux * hx + uy * hy - uz * hz,
        center - ux * hx - uy * hy + uz * hz,
        center + ux * hx - uy * hy + uz * hz,
        center + ux * hx + uy * hy + uz * hz,
        center - ux * hx + uy * hy + uz * hz,
    ]
    v = [bm.verts.new(c) for c in corners]
    faces = [
        (v[0], v[3], v[2], v[1]),
        (v[4], v[5], v[6], v[7]),
        (v[0], v[1], v[5], v[4]),
        (v[1], v[2], v[6], v[5]),
        (v[2], v[3], v[7], v[6]),
        (v[3], v[0], v[4], v[7]),
    ]
    for f_verts in faces:
        try:
            f = bm.faces.new(f_verts)
            f.material_index = mat_idx
        except ValueError:
            pass


def add_cylinder_along(
    bm: bmesh.types.BMesh,
    p0: Vector,
    p1: Vector,
    r0: float,
    r1: float,
    segs: int = 12,
    mat_idx: int = 0,
    cap_ends: bool = True,
):
    axis = p1 - p0
    if axis.length < 1e-4:
        return
    w = axis.normalized()
    ref = Vector((0.0, 0.0, 1.0)) if abs(w.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = w.cross(ref).normalized()
    v = w.cross(u).normalized()
    ring0 = []
    ring1 = []
    for k in range(segs):
        ang = 2.0 * math.pi * k / segs
        d = u * math.cos(ang) + v * math.sin(ang)
        ring0.append(bm.verts.new(p0 + d * r0))
        ring1.append(bm.verts.new(p1 + d * r1))
    for k in range(segs):
        nk = (k + 1) % segs
        try:
            f = bm.faces.new((ring0[k], ring0[nk], ring1[nk], ring1[k]))
            f.material_index = mat_idx
        except ValueError:
            pass
    if cap_ends:
        try:
            fb = bm.faces.new(list(reversed(ring0)))
            fb.material_index = mat_idx
            ft = bm.faces.new(ring1)
            ft.material_index = mat_idx
        except ValueError:
            pass


def build_corridor_material_palette() -> dict:
    """
    Builds a 28-material Poly Haven 2K PBR palette combining our core Montreal kit
    with the newly imported Poly Haven textures (`concrete_tile_facade`, `sandstone_blocks_04`,
    `red_bricks_04`, `roof_slates_03`, `factory_wall`, `concrete_brick_wall_001`,
    `sandstone_brick_wall_01`, `grey_roof_01`, `brick_pavement_03`, etc.).
    """
    return {
        "red_brick": create_pbr_material(
            "Mat_PH_Red_Bricks_04",
            base_color=(0.56, 0.25, 0.19, 1.0),
            roughness=0.78,
            diffuse_tex=str(POLYHAVEN_DIR / "red_bricks_04_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "red_bricks_04_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "red_bricks_04_rough_2k.jpg"),
            tint_color=(0.56, 0.25, 0.19),
            tint_strength=0.35,
            uv_scale=0.30,
        ),
        "victorian_brick": create_pbr_material(
            "Mat_PH_Brick_Wall_04",
            base_color=(0.52, 0.27, 0.21, 1.0),
            roughness=0.80,
            diffuse_tex=str(POLYHAVEN_DIR / "brick_wall_04_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "brick_wall_04_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "brick_wall_04_rough_2k.jpg"),
            tint_color=(0.52, 0.27, 0.21),
            tint_strength=0.38,
            uv_scale=0.28,
        ),
        "brown_brick": create_pbr_material(
            "Mat_PH_Dark_Loft_Brick",
            base_color=(0.38, 0.29, 0.24, 1.0),
            roughness=0.80,
            diffuse_tex=str(POLYHAVEN_DIR / "dark_brick_wall_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "dark_brick_wall_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "dark_brick_wall_rough_2k.jpg"),
            tint_color=(0.38, 0.29, 0.24),
            tint_strength=0.42,
            uv_scale=0.28,
        ),
        "yellow_brick": create_pbr_material(
            "Mat_PH_Yellow_Buff_Brick",
            base_color=(0.72, 0.63, 0.45, 1.0),
            roughness=0.76,
            diffuse_tex=str(POLYHAVEN_DIR / "yellow_brick_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "yellow_brick_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "yellow_brick_rough_2k.jpg"),
            tint_color=(0.72, 0.63, 0.45),
            tint_strength=0.40,
            uv_scale=0.28,
        ),
        "sandstone_brick": create_pbr_material(
            "Mat_PH_Sandstone_Brick_01",
            base_color=(0.62, 0.34, 0.26, 1.0),
            roughness=0.78,
            diffuse_tex=str(POLYHAVEN_DIR / "sandstone_brick_wall_01_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "sandstone_brick_wall_01_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "sandstone_brick_wall_01_rough_2k.jpg"),
            tint_color=(0.62, 0.34, 0.26),
            tint_strength=0.35,
            uv_scale=0.28,
        ),
        "tan_limestone": create_pbr_material(
            "Mat_PH_Sandstone_Blocks_04",
            base_color=(0.76, 0.71, 0.62, 1.0),
            roughness=0.72,
            diffuse_tex=str(POLYHAVEN_DIR / "sandstone_blocks_04_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "sandstone_blocks_04_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "sandstone_blocks_04_rough_2k.jpg"),
            tint_color=(0.76, 0.71, 0.62),
            tint_strength=0.42,
            uv_scale=0.24,
        ),
        "grey_limestone": create_pbr_material(
            "Mat_PH_PierreGrise_Limestone",
            base_color=(0.62, 0.61, 0.58, 1.0),
            roughness=0.72,
            diffuse_tex=str(POLYHAVEN_DIR / "stone_brick_wall_001_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "stone_brick_wall_001_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "stone_brick_wall_001_rough_2k.jpg"),
            tint_color=(0.62, 0.61, 0.58),
            tint_strength=0.48,
            uv_scale=0.25,
        ),
        "concrete_tile_facade": create_pbr_material(
            "Mat_PH_Concrete_Tile_Facade",
            base_color=(0.68, 0.67, 0.64, 1.0),
            roughness=0.68,
            diffuse_tex=str(POLYHAVEN_DIR / "concrete_tile_facade_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "concrete_tile_facade_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "concrete_tile_facade_rough_2k.jpg"),
            tint_color=(0.68, 0.67, 0.64),
            tint_strength=0.40,
            uv_scale=0.26,
        ),
        "concrete_brick_wall": create_pbr_material(
            "Mat_PH_Concrete_Brick_Wall_001",
            base_color=(0.71, 0.68, 0.62, 1.0),
            roughness=0.74,
            diffuse_tex=str(POLYHAVEN_DIR / "concrete_brick_wall_001_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "concrete_brick_wall_001_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "concrete_brick_wall_001_rough_2k.jpg"),
            tint_color=(0.71, 0.68, 0.62),
            tint_strength=0.38,
            uv_scale=0.26,
        ),
        "factory_corrugated": create_pbr_material(
            "Mat_PH_Factory_Corrugated_Wall",
            base_color=(0.32, 0.44, 0.36, 1.0),
            roughness=0.52,
            metallic=0.45,
            diffuse_tex=str(POLYHAVEN_DIR / "factory_wall_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "factory_wall_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "factory_wall_rough_2k.jpg"),
            tint_color=(0.32, 0.44, 0.36),
            tint_strength=0.35,
            uv_scale=0.28,
        ),
        "bridge_green_steel": create_pbr_material(
            "Mat_MTL_JacquesCartier_Green_Steel",
            base_color=(0.22, 0.42, 0.33, 1.0),
            roughness=0.44,
            metallic=0.68,
            diffuse_tex=str(POLYHAVEN_DIR / "factory_wall_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "factory_wall_nor_gl_2k.jpg"),
            tint_color=(0.22, 0.42, 0.33),
            tint_strength=0.72,
            uv_scale=0.30,
        ),
        "cream_stucco": create_pbr_material(
            "Mat_PH_Cream_Fieldstone",
            base_color=(0.82, 0.79, 0.73, 1.0),
            roughness=0.74,
            diffuse_tex=str(POLYHAVEN_DIR / "castle_brick_02_white_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "castle_brick_02_white_nor_gl_2k.jpg"),
            tint_color=(0.82, 0.79, 0.73),
            tint_strength=0.55,
            uv_scale=0.25,
        ),
        "concrete_podium": create_pbr_material(
            "Mat_PH_Brutalist_Concrete",
            base_color=(0.64, 0.63, 0.60, 1.0),
            roughness=0.76,
            diffuse_tex=str(POLYHAVEN_DIR / "concrete_block_wall_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "concrete_block_wall_nor_gl_2k.jpg"),
            tint_color=(0.64, 0.63, 0.60),
            tint_strength=0.55,
            uv_scale=0.24,
        ),
        "brick_pavement": create_pbr_material(
            "Mat_PH_Brick_Pavement_03",
            base_color=(0.56, 0.48, 0.44, 1.0),
            roughness=0.78,
            diffuse_tex=str(POLYHAVEN_DIR / "brick_pavement_03_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "brick_pavement_03_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "brick_pavement_03_rough_2k.jpg"),
            tint_color=(0.56, 0.48, 0.44),
            tint_strength=0.35,
            uv_scale=0.28,
        ),
        "plaza_beige": create_pbr_material(
            "Mat_PH_Plaza_Concrete_Pavers",
            base_color=(0.74, 0.71, 0.65, 1.0),
            roughness=0.74,
            diffuse_tex=str(POLYHAVEN_DIR / "concrete_pavers_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "concrete_pavers_nor_gl_2k.jpg"),
            tint_color=(0.74, 0.71, 0.65),
            tint_strength=0.55,
            uv_scale=0.24,
        ),
        "park_grass": create_pbr_material(
            "Mat_PH_Lush_Park_Grass",
            base_color=(0.22, 0.39, 0.16, 1.0),
            roughness=0.86,
            diffuse_tex=str(POLYHAVEN_DIR / "leafy_grass_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "leafy_grass_nor_gl_2k.jpg"),
            tint_color=(0.22, 0.39, 0.16),
            tint_strength=0.55,
            uv_scale=0.22,
        ),
        "water_river": create_pbr_material(
            "Mat_PH_StLawrence_River_Water",
            base_color=(0.07, 0.19, 0.26, 1.0),
            roughness=0.14,
            ior=1.333,
            diffuse_tex=str(POLYHAVEN_DIR / "water_river_diffuse_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "water_river_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "water_river_rough_2k.jpg"),
            tint_color=(0.07, 0.19, 0.26),
            tint_strength=0.45,
            uv_scale=0.08,
        ),
        "dark_glass": create_pbr_material(
            "Mat_MTL_CurtainWall_Glass",
            base_color=(0.08, 0.13, 0.18, 1.0),
            roughness=0.10,
            metallic=0.25,
            ior=1.52,
        ),
        "blue_glass": create_pbr_material(
            "Mat_MTL_Modern_Blue_Glass",
            base_color=(0.14, 0.26, 0.38, 1.0),
            roughness=0.08,
            metallic=0.32,
            ior=1.52,
        ),
        "white_trim": create_pbr_material(
            "Mat_MTL_White_Precast_Trim",
            base_color=(0.86, 0.85, 0.82, 1.0),
            roughness=0.52,
        ),
        "dark_metal": create_pbr_material(
            "Mat_MTL_Anodized_Dark_Metal",
            base_color=(0.16, 0.17, 0.19, 1.0),
            roughness=0.38,
            metallic=0.78,
        ),
        "copper_verdigris": create_pbr_material(
            "Mat_MTL_Copper_Dome_Verdigris",
            base_color=(0.28, 0.54, 0.45, 1.0),
            roughness=0.42,
            metallic=0.65,
            diffuse_tex=str(POLYHAVEN_DIR / "box_profile_metal_sheet_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "box_profile_metal_sheet_nor_gl_2k.jpg"),
            tint_color=(0.28, 0.54, 0.45),
            tint_strength=0.72,
            uv_scale=0.30,
        ),
        "roof_slates": create_pbr_material(
            "Mat_PH_Roof_Slates_03",
            base_color=(0.28, 0.30, 0.33, 1.0),
            roughness=0.68,
            diffuse_tex=str(POLYHAVEN_DIR / "roof_slates_03_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "roof_slates_03_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "roof_slates_03_rough_2k.jpg"),
            tint_color=(0.28, 0.30, 0.33),
            tint_strength=0.32,
            uv_scale=0.30,
        ),
        "roof_grey_tiles": create_pbr_material(
            "Mat_PH_Grey_Roof_01",
            base_color=(0.35, 0.36, 0.38, 1.0),
            roughness=0.62,
            diffuse_tex=str(POLYHAVEN_DIR / "grey_roof_01_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "grey_roof_01_nor_gl_2k.jpg"),
            rough_tex=str(POLYHAVEN_DIR / "grey_roof_01_rough_2k.jpg"),
            tint_color=(0.35, 0.36, 0.38),
            tint_strength=0.32,
            uv_scale=0.25,
        ),
        "roof_light_gravel": create_pbr_material(
            "Mat_PH_Roof_Light_Gravel",
            base_color=(0.68, 0.66, 0.62, 1.0),
            roughness=0.86,
            diffuse_tex=str(POLYHAVEN_DIR / "gravel_concrete_02_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "gravel_concrete_02_nor_gl_2k.jpg"),
            tint_color=(0.68, 0.66, 0.62),
            tint_strength=0.52,
            uv_scale=0.22,
        ),
        "roof_white_elastomer": create_pbr_material(
            "Mat_PH_Roof_White_Elastomer",
            base_color=(0.82, 0.81, 0.78, 1.0),
            roughness=0.72,
            diffuse_tex=str(POLYHAVEN_DIR / "concrete_pavement_02_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "concrete_pavement_02_nor_gl_2k.jpg"),
            tint_color=(0.82, 0.81, 0.78),
            tint_strength=0.65,
            uv_scale=0.22,
        ),
        "roof_bitumen": create_pbr_material(
            "Mat_PH_Roof_Dark_Bitumen",
            base_color=(0.26, 0.26, 0.28, 1.0),
            roughness=0.84,
            diffuse_tex=str(POLYHAVEN_DIR / "asphalt_02_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "asphalt_02_nor_gl_2k.jpg"),
            tint_color=(0.26, 0.26, 0.28),
            tint_strength=0.62,
            uv_scale=0.22,
        ),
        "terracotta_vivid": create_pbr_material(
            "Mat_MTL_Terracotta_Red_Steel",
            base_color=(0.76, 0.24, 0.16, 1.0),
            roughness=0.48,
            metallic=0.35,
            diffuse_tex=str(POLYHAVEN_DIR / "box_profile_metal_sheet_diff_2k.jpg"),
            normal_tex=str(POLYHAVEN_DIR / "box_profile_metal_sheet_nor_gl_2k.jpg"),
            tint_color=(0.78, 0.22, 0.15),
            tint_strength=0.78,
            uv_scale=0.28,
        ),
        "blue_curtain_glass": create_pbr_material(
            "Mat_MTL_Blue_Curtain_Glass",
            base_color=(0.14, 0.28, 0.42, 1.0),
            roughness=0.10,
            metallic=0.72,
        ),
    }


def build_corridor_context_buildings(
    col: bpy.types.Collection,
    dossier: dict,
    mats: dict,
    skip_ids: set = None,
    skip_boxes: list = None,
    max_buildings: int = 240,
) -> int:
    """
    Constructs all OSM buildings in `dossier` (except those in `skip_ids` or `skip_boxes`)
    within the satellite bounding box, with true floor-by-floor 3D fenestration
    (`windowless_tall_buildings == 0`), rusticated ground floors, stone sills/lintels,
    cantilevered balconies, and diversified Poly Haven 2K PBR facades & roofs.
    """
    if skip_ids is None:
        skip_ids = set()
    if skip_boxes is None:
        skip_boxes = []

    palette_combos = [
        ("red_brick", "cream_stucco", "tan_limestone"),
        ("victorian_brick", "tan_limestone", "grey_limestone"),
        ("brown_brick", "tan_limestone", "grey_limestone"),
        ("sandstone_brick", "cream_stucco", "tan_limestone"),
        ("yellow_brick", "tan_limestone", "grey_limestone"),
        ("tan_limestone", "concrete_brick_wall", "grey_limestone"),
        ("grey_limestone", "white_trim", "concrete_podium"),
        ("concrete_tile_facade", "white_trim", "concrete_podium"),
        ("concrete_brick_wall", "red_brick", "grey_limestone"),
    ]
    roof_keys = ["roof_slates", "roof_grey_tiles", "roof_light_gravel", "roof_white_elastomer", "roof_bitumen"]

    sat = dossier.get("satellite_ref", {})
    center_xy = sat.get("center_xy_m") or dossier.get("block_center_xy_m") or [0.0, 0.0]
    sat_cx, sat_cy = float(center_xy[0]), float(center_xy[1])
    sat_half = float(sat.get("view_span_m", 460.0)) * 0.49

    cams = dossier.get("streetview_cameras", [])
    cam_pts = [(float(c["blender_cam_xy_m"][0]), float(c["blender_cam_xy_m"][1])) for c in cams if "blender_cam_xy_m" in c]

    raw_buildings = dossier.get("osm_features", {}).get("buildings", [])
    candidates = []
    for idx_raw, bldg in enumerate(raw_buildings):
        oid = str(bldg.get("id", idx_raw))
        if oid in skip_ids:
            continue
        pts_xy = bldg.get("coords_xy", [])
        if len(pts_xy) < 3:
            continue
        bx = sum(float(p[0]) for p in pts_xy) / len(pts_xy)
        by = sum(float(p[1]) for p in pts_xy) / len(pts_xy)
        min_cam_d = min((math.hypot(bx - cx_c, by - cy_c) for cx_c, cy_c in cam_pts), default=200.0)
        # Rule RSI-010: Keep context buildings at least 11.5m clear of every Street View camera origin
        too_close_cam = any(
            math.hypot(float(p[0]) - cx_c, float(p[1]) - cy_c) < 11.5
            for p in pts_xy
            for cx_c, cy_c in cam_pts
        )
        if too_close_cam or min_cam_d < 13.0:
            continue
        in_sat_b = (abs(bx - sat_cx) <= sat_half and abs(by - sat_cy) <= sat_half)
        if not in_sat_b:
            continue
        if any(abs(float(p[0]) - sat_cx) > sat_half * 1.03 or abs(float(p[1]) - sat_cy) > sat_half * 1.03 for p in pts_xy):
            continue
        if any(xmin <= bx <= xmax and ymin <= by <= ymax for (xmin, xmax, ymin, ymax) in skip_boxes):
            continue
        # Prioritize buildings close to Street View cameras or with larger footprints
        near_cam = 1 if min_cam_d < 120.0 else 0
        xs = [float(p[0]) for p in pts_xy]
        ys = [float(p[1]) for p in pts_xy]
        approx_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        candidates.append(((near_cam, approx_area), idx_raw, bldg))

    if len(candidates) > max_buildings:
        candidates.sort(key=lambda item: item[0], reverse=True)
        candidates = candidates[:max_buildings]

    built_count = 0
    uz = Vector((0.0, 0.0, 1.0))

    for _, idx, bldg in candidates:
        oid = str(bldg.get("id", idx))
        pts_xy = bldg.get("coords_xy", [])

        verts_2d = []
        for p in pts_xy:
            v = Vector((float(p[0]), float(p[1]), 0.0))
            if not verts_2d or (v - verts_2d[-1]).length > 0.25:
                verts_2d.append(v)
        if len(verts_2d) > 1 and (verts_2d[0] - verts_2d[-1]).length < 0.25:
            verts_2d.pop()
        if len(verts_2d) < 3:
            continue

        cx = sum(v.x for v in verts_2d) / len(verts_2d)
        cy = sum(v.y for v in verts_2d) / len(verts_2d)
        if any(xmin <= cx <= xmax and ymin <= cy <= ymax for (xmin, xmax, ymin, ymax) in skip_boxes):
            continue

        signed_area = 0.0
        m = len(verts_2d)
        for i in range(m):
            p0, p1 = verts_2d[i], verts_2d[(i + 1) % m]
            signed_area += p0.x * p1.y - p1.x * p0.y
        area = abs(signed_area) * 0.5
        if area < 10.0 or area > 38000.0:
            continue
        if signed_area < 0:
            verts_2d.reverse()

        tags = bldg.get("tags", {})
        levels_str = str(tags.get("building:levels", "")).split("-")[0].strip()
        try:
            levels = int(float(levels_str))
        except ValueError:
            levels = 0
        if levels <= 0:
            if area > 1400.0:
                levels = 4
            elif area > 200.0:
                levels = 3
            elif area > 50.0:
                levels = 2
            else:
                levels = 1
        levels = min(levels, 12)
        height = max(4.2, levels * 3.45 + 0.8)

        wall_key, accent_key, base_key = palette_combos[idx % len(palette_combos)]
        if tags.get("building") in ("industrial", "warehouse"):
            wall_key = "factory_corrugated" if (idx % 2 == 0) else "sandstone_brick"
        pitched_roof = tags.get("roof:shape") in ("hipped", "gabled") or (levels == 2 and idx % 5 == 0)
        roof_key = "roof_slates" if pitched_roof else roof_keys[idx % len(roof_keys)]

        mesh = bpy.data.meshes.new(f"MTL_Bldg_{oid}_{idx}")
        obj = bpy.data.objects.new(f"MTL_Bldg_{oid}_{idx}", mesh)
        col.objects.link(obj)
        for k in (wall_key, base_key, accent_key, "dark_glass", "white_trim", roof_key, "dark_metal"):
            obj.data.materials.append(mats[k])

        bm = bmesh.new()
        z_base_band = min(3.2, height * 0.28)
        parapet_h = 0.52 if not pitched_roof else 0.24

        r_bot = [bm.verts.new(Vector((v.x, v.y, 0.0))) for v in verts_2d]
        r_base = [bm.verts.new(Vector((v.x, v.y, z_base_band))) for v in verts_2d]
        r_top = [bm.verts.new(Vector((v.x, v.y, height))) for v in verts_2d]
        r_par = [bm.verts.new(Vector((v.x, v.y, height + parapet_h))) for v in verts_2d]
        r_in = [
            bm.verts.new(Vector((cx + (v.x - cx) * 0.94, cy + (v.y - cy) * 0.94, height + 0.08)))
            for v in verts_2d
        ]

        for i in range(m):
            ni = (i + 1) % m
            try:
                bm.faces.new((r_bot[i], r_bot[ni], r_base[ni], r_base[i])).material_index = 1
                bm.faces.new((r_base[i], r_base[ni], r_top[ni], r_top[i])).material_index = 0
                bm.faces.new((r_top[i], r_top[ni], r_par[ni], r_par[i])).material_index = 1
                bm.faces.new((r_par[i], r_par[ni], r_in[ni], r_in[i])).material_index = 1
            except ValueError:
                pass

        if pitched_roof and height >= 6.5:
            apex_z = height + min(3.6, max(2.0, math.sqrt(area) * 0.15))
            v_apex = bm.verts.new(Vector((cx, cy, apex_z)))
            for i in range(m):
                ni = (i + 1) % m
                try:
                    bm.faces.new((r_in[i], r_in[ni], v_apex)).material_index = 5
                except ValueError:
                    pass
        else:
            try:
                bm.faces.new(r_in).material_index = 5
            except ValueError:
                pass
            if area > 130.0 and height >= 6.8:
                p_c = Vector((cx, cy, height + 0.08))
                ux_r = Vector((1.0, 0.0, 0.0))
                uy_r = Vector((0.0, 1.0, 0.0))
                add_box_local(bm, p_c + uz * 1.05, ux_r, uy_r, uz, 3.6, 3.0, 2.1, mat_idx=0)
                add_box_local(bm, p_c + uz * 2.18, ux_r, uy_r, uz, 3.9, 3.3, 0.20, mat_idx=1)
                add_box_local(bm, p_c + uy_r * 1.55 + uz * 1.05, ux_r, uy_r, uz, 2.4, 0.16, 1.3, mat_idx=6)

        # Floor-by-floor 3D fenestration on exterior walls
        n_floors = max(1, min(8, int(round(height / 3.45))))
        floor_h = (height - 0.65) / n_floors
        for i in range(m):
            ni = (i + 1) % m
            p0, p1 = verts_2d[i], verts_2d[ni]
            edge_vec = p1 - p0
            edge_len = edge_vec.length
            if edge_len < 2.8:
                continue
            u_tan = edge_vec.normalized()
            u_out = Vector((u_tan.y, -u_tan.x, 0.0)).normalized()

            add_box_local(bm, p0.lerp(p1, 0.5) + u_out * 0.11 + uz * (height - 0.18), u_tan, u_out, uz, edge_len + 0.12, 0.24, 0.30, mat_idx=1)

            n_cols = max(1, min(10, int(edge_len / 3.4)))
            bay_w = edge_len / n_cols
            win_w = min(1.80, bay_w * 0.54)
            win_h = min(1.60, floor_h * 0.50)

            for r_fl in range(n_floors):
                z_fl_center = 0.45 + (r_fl + 0.52) * floor_h
                for c_bay in range(n_cols):
                    t_bay = (c_bay + 0.5) / n_cols
                    w_pos = p0.lerp(p1, t_bay) + uz * z_fl_center
                    add_box_local(bm, w_pos + u_out * 0.05, u_tan, u_out, uz, win_w + 0.20, 0.12, win_h + 0.18, mat_idx=4)
                    add_box_local(bm, w_pos + u_out * 0.10, u_tan, u_out, uz, win_w, 0.07, win_h, mat_idx=3)
                    add_box_local(bm, w_pos + u_out * 0.14 - uz * (win_h * 0.5 + 0.07), u_tan, u_out, uz, win_w + 0.30, 0.22, 0.12, mat_idx=1)
                    if n_floors >= 3 and r_fl >= 1 and (c_bay % 3 == 1) and edge_len > 9.5 and idx % 2 == 0:
                        bal_c = w_pos + u_out * 0.65 - uz * (win_h * 0.5 + 0.07)
                        add_box_local(bm, bal_c, u_tan, u_out, uz, win_w + 0.65, 1.15, 0.14, mat_idx=1)
                        add_box_local(bm, bal_c + u_out * 0.50 + uz * 0.48, u_tan, u_out, uz, win_w + 0.65, 0.05, 0.85, mat_idx=6)

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        apply_world_box_uv(obj, scale=0.25)
        built_count += 1

    print(f"[OK] Built {built_count} corridor context buildings with 3D fenestration.")
    return built_count


def build_corridor_foliage_and_props(
    col: bpy.types.Collection,
    dossier: dict,
    extra_trees: list = None,
    max_osm_trees: int = 85,
):
    """
    Instantiates Poly Haven 3D botanical trees (`jacaranda_tree`, `tree_small_02`, `searsia_burchellii`),
    shrubs (`shrub_01`, `shrub_02`), benches (`modular_street_seating`, `painted_wooden_bench`),
    and fire hydrants (`fire_hydrant`) while avoiding camera center rays.
    """
    import random

    rng = random.Random(2026)
    cams = dossier.get("streetview_cameras", [])
    cam_keepers = [Vector((float(c["blender_cam_xy_m"][0]), float(c["blender_cam_xy_m"][1]), 0.0)) for c in cams if "blender_cam_xy_m" in c]

    tree_positions = []
    if extra_trees:
        tree_positions.extend(extra_trees)

    sat = dossier.get("satellite", {}) or dossier.get("satellite_ref", {})
    center_xy = sat.get("center_xy_m") or dossier.get("blender_center_xy_m") or dossier.get("block_center_xy_m") or [0.0, 0.0]
    sat_cx, sat_cy = float(center_xy[0]), float(center_xy[1])
    sat_span = float(sat.get("span_meters") or sat.get("view_span_m") or 280.0)
    tree_max_half = sat_span * 0.62

    osm_trees = dossier.get("osm_features", {}).get("trees", [])
    step_t = max(1, len(osm_trees) // max_osm_trees) if osm_trees else 1
    for idx_t, t in enumerate(osm_trees[::step_t]):
        xy = t.get("xy") or [t.get("x", 0.0), t.get("y", 0.0)]
        tx, ty = float(xy[0]), float(xy[1])
        if abs(tx - sat_cx) > tree_max_half or abs(ty - sat_cy) > tree_max_half:
            continue
        tp = Vector((tx, ty, 0.0))
        if any((tp - ck).length < 18.0 for ck in cam_keepers):
            continue
        tree_positions.append((tx, ty, 0.95 + (idx_t % 4) * 0.14))

    tree_species = ["jacaranda_tree", "tree_small_02", "searsia_burchellii"]
    for idx_t, (tx, ty, sc) in enumerate(tree_positions[:120]):
        sp = tree_species[idx_t % len(tree_species)]
        append_kit_object(
            sp,
            name=f"MTL_PH_Tree_{idx_t:03d}",
            collection=col,
            location=(tx, ty, 0.16),
            rotation_z=rng.uniform(0.0, math.pi * 2.0),
            scale=sc,
        )

    # Add street seating & fire hydrants near camera sidewalks (offset to sides so center view is clear)
    for idx_c, c in enumerate(cams):
        if "blender_cam_xy_m" not in c:
            continue
        cx_c, cy_c = float(c["blender_cam_xy_m"][0]), float(c["blender_cam_xy_m"][1])
        hdg = math.radians(float(c.get("heading_deg", 0.0)))
        fwd = Vector((math.sin(hdg), math.cos(hdg), 0.0))
        right = Vector((fwd.y, -fwd.x, 0.0))
        bp = Vector((cx_c, cy_c, 0.0)) + fwd * 14.5 + right * 4.8
        append_kit_object(
            "modular_street_seating" if idx_c % 2 == 0 else "painted_wooden_bench",
            name=f"MTL_PH_Bench_{idx_c:02d}",
            collection=col,
            location=(bp.x, bp.y, 0.22),
            rotation_z=-hdg,
            scale=1.0,
        )
        hp = Vector((cx_c, cy_c, 0.0)) + fwd * 11.0 - right * 4.6
        append_kit_object(
            "fire_hydrant",
            name=f"MTL_PH_Hydrant_{idx_c:02d}",
            collection=col,
            location=(hp.x, hp.y, 0.22),
            rotation_z=hdg,
            scale=1.0,
        )

