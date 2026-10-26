"""
Upgrade Streets, Sidewalks, Curbs, Proper Crossing Markings, Poly Haven Streetlamps,
and Lush Green Tree Canopies across Montreal 3D Blocks (`MTL-VM-*` and `MTL-OLY-*`).

Usage inside Blender:
  blender.exe -b -P src/upgrade_all_block_streets.py -- --blocks MTL-VM-0002 MTL-VM-0003 ...
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import site
for _sp in ([site.getusersitepackages()] if isinstance(site.getusersitepackages(), str) else list(site.getusersitepackages())):
    if _sp and _sp not in sys.path:
        sys.path.append(_sp)

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

import src.blender_lib as blender_lib


def _is_water_or_pier_object(obj_name: str, mat_names: list[str]) -> bool:
    low = obj_name.lower()
    water_kw = ("water", "river", "fleuve", "basin", "bassin", "canal", "pond", "pool", "fountain", "lake", "harbour", "port_water")
    if any(k in low for k in water_kw):
        return True
    for mn in mat_names:
        mlow = mn.lower()
        if any(k in mlow for k in water_kw):
            return True
    return False


def _is_tree_object(obj_name: str, mesh_name: str = "") -> bool:
    low = obj_name.lower()
    mlow = mesh_name.lower()
    if "street" in low or "lamp" in low or "lantern" in low:
        return False
    return any(k in low or k in mlow for k in ("tree", "sapling", "jacaranda", "searsia"))


def _is_street_or_ground_object(obj_name: str) -> bool:
    low = obj_name.lower()
    if _is_tree_object(obj_name):
        return False
    exclude_kw = (
        "lamp",
        "light",
        "lantern",
        "bldg",
        "building",
        "hero",
        "basilica",
        "tower",
        "palais",
        "bmo",
        "aldred",
        "market",
        "museum",
        "hall",
        "station",
        "chapel",
        "bridge",
        "pont",
        "biosphere",
        "habitat",
        "casino",
        "silo",
        "hangar",
        "pavilion",
        "monument",
        "statue",
        "vehicle",
        "sedan",
        "truck",
        "suv",
        "bixi",
    )
    if any(k in low for k in exclude_kw):
        return False
    street_kw = (
        "ground",
        "street",
        "sidewalk",
        "curb",
        "road",
        "asphalt",
        "pavement",
        "marking",
        "crosswalk",
        "walkway",
        "footway",
        "cobble",
        "plaza",
        "park_paths",
        "osm_parks",
    )
    return any(k in low for k in street_kw)


def _upgrade_legacy_trees_and_prune_road_trees(road_union, owned_col):
    """Ensure all legacy tree meshes have compact 6.5m lush green 3D foliage and never sit on street pavement."""
    road_guard = road_union.buffer(-0.08) if (road_union is not None and not road_union.is_empty) else Polygon()

    # 1. Remove any legacy tree or lamp object sitting inside the asphalt roadway
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            continue
        low = obj.name.lower()
        if _is_tree_object(obj.name, obj.data.name if obj.data else "") or ("lamp" in low and not obj.name.startswith("MTL_PH_StreetLamp")):
            ox, oy = float(obj.location.x), float(obj.location.y)
            if abs(ox) > 0.01 or abs(oy) > 0.01:
                if not road_guard.is_empty and road_guard.contains(Point(ox, oy)):
                    bpy.data.objects.remove(obj, do_unlink=True)
                    continue

    # 2. Sanitize and attach 9-lobe lush green 3D canopy to every legacy tree mesh data-block
    mat_leaf = bpy.data.materials.get("Mat_PH_Tree_Canopy_Lush_Green")
    if mat_leaf is None:
        mat_leaf = blender_lib.create_pbr_material(
            "Mat_PH_Tree_Canopy_Lush_Green",
            base_color=(0.16, 0.36, 0.12, 1.0),
            roughness=0.82,
            diffuse_tex=str(blender_lib.POLYHAVEN_DIR / "leafy_grass_diff_2k.jpg"),
            normal_tex=str(blender_lib.POLYHAVEN_DIR / "leafy_grass_nor_gl_2k.jpg"),
            tint_color=(0.16, 0.36, 0.12),
            tint_strength=0.68,
            uv_scale=0.35,
        )
    upgraded_meshes = set()

    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.data:
            continue
        if not _is_tree_object(obj.name, obj.data.name):
            continue
        if obj.data.name in upgraded_meshes:
            continue
        upgraded_meshes.add(obj.data.name)

        # Find or append `Mat_PH_Tree_Canopy_Lush_Green` slot
        leaf_idx = None
        for idx_m, m in enumerate(obj.data.materials):
            if m and m.name == "Mat_PH_Tree_Canopy_Lush_Green":
                leaf_idx = idx_m
                break
        if leaf_idx is None:
            leaf_idx = len(obj.data.materials)
            obj.data.materials.append(mat_leaf)

        bm_t = bmesh.new()
        bm_t.from_mesh(obj.data)
        bm_t.faces.ensure_lookup_table()
        # Remove any previous oversized canopy faces using `leaf_idx`
        old_canopy_faces = [f for f in bm_t.faces if f.material_index == leaf_idx]
        if old_canopy_faces:
            bmesh.ops.delete(bm_t, geom=old_canopy_faces, context="FACES")

        # Rule RSI-010: Strip stray floating twigs (`R > 2.4m` or `Z > 6.2m` or `Z < -0.25m`)
        bm_t.verts.ensure_lookup_table()
        bad_verts = [
            v for v in bm_t.verts
            if math.hypot(v.co.x, v.co.y) > 2.4 or v.co.z > 6.2 or v.co.z < -0.25
        ]
        if bad_verts and len(bad_verts) < len(bm_t.verts):
            bmesh.ops.delete(bm_t, geom=bad_verts, context="VERTS")

        lobe_specs = [
            (0.0, 0.0, 5.2, 2.05),
            (1.05, 0.42, 4.5, 1.60),
            (-1.02, 0.50, 4.6, 1.65),
            (0.42, -1.05, 4.4, 1.60),
            (-0.60, -0.98, 4.7, 1.55),
            (0.78, 0.78, 5.8, 1.45),
            (-0.78, -0.70, 5.9, 1.50),
            (0.0, 0.88, 3.8, 1.40),
            (0.0, -0.78, 6.3, 1.38),
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
                    f_l.smooth = True
        bmesh.ops.recalc_face_normals(bm_t, faces=bm_t.faces)
        bm_t.to_mesh(obj.data)
        obj.data.update()
        bm_t.free()
        print(f"[UPGRADE] Sanitized & attached 9-lobe green 3D canopy to tree mesh '{obj.data.name}'")


def upgrade_single_block_in_place(block_id: str) -> bool:
    blend_path = REPO_ROOT / "output" / "blocks" / f"{block_id}.blend"
    dossier_path = REPO_ROOT / "data" / "blocks" / block_id / "dossier.json"
    if not blend_path.exists() or not dossier_path.exists():
        print(f"[ERROR] Missing blend or dossier for {block_id}")
        return False

    print(f"\n=======================================================")
    print(f"[UPGRADE] Opening {blend_path} for street/sidewalk/crosswalk upgrade")
    print(f"=======================================================")
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    blender_lib._KIT_CACHE.clear()
    dossier = json.loads(dossier_path.read_text(encoding="utf-8"))

    # Unhide any `Block_<BLOCK_ID>_Context_Proxy` collection so context buildings on the block render instead of leaving empty holes
    for col in bpy.data.collections:
        if "context_proxy" in col.name.lower() or "block_" in col.name.lower():
            col.hide_render = False
            col.hide_viewport = False

    owned_col = bpy.data.collections.get(f"Block_{block_id}_Owned")
    if owned_col is None:
        for col in bpy.data.collections:
            if "owned" in col.name.lower():
                owned_col = col
                break
    if owned_col is None:
        owned_col = bpy.data.collections.new(f"Block_{block_id}_Owned")
        bpy.context.scene.collection.children.link(owned_col)

    # 1. Remove previous `blender_lib` street objects & broken lamp templates if present
    remove_exact_prefixes = (
        "MTL_Ground_Base",
        "MTL_OSM_Streets_and_Walkways",
        "MTL_Sidewalks_and_Curbs",
        "MTL_Street_Markings",
        "MTL_Park_Paths",
        "MTL_OSM_Parks_Grass",
        "MTL_PH_StreetLamp",
        "street_lamp_01",
        "street_lamp_02",
    )
    for obj in list(bpy.data.objects):
        if any(obj.name.startswith(pfx) for pfx in remove_exact_prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)

    # 2. Build fresh Boolean-manifold Ground, Streets, Parallel Exterior Curbs & Sidewalks,
    #    Continental Zebra Crosswalks + Stop Bars + Trimmed Centerlines, and Poly Haven Streetlamps!
    blender_lib.build_ground_and_streets(owned_col, dossier)
    road_union = blender_lib._LAST_ROAD_UNION
    ground_clip_box = blender_lib._LAST_GROUND_CLIP_BOX

    # 3. Clean legacy ground/street/sidewalk meshes & trim any overlapping sidewalk/plaza slabs
    new_street_objs = {
        "MTL_Ground_Base",
        "MTL_OSM_Streets_and_Walkways",
        "MTL_Sidewalks_and_Curbs",
        "MTL_Street_Markings",
        "MTL_Park_Paths",
        "MTL_OSM_Parks_Grass",
    }
    road_guard = road_union.buffer(-0.04) if (road_union is not None and not road_union.is_empty) else Polygon()

    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.data:
            continue
        if obj.name in new_street_objs or obj.name.startswith("MTL_PH_StreetLamp"):
            continue
        mat_names = [m.name for m in obj.data.materials if m]
        if _is_water_or_pier_object(obj.name, mat_names):
            continue

        is_street_obj = _is_street_or_ground_object(obj.name)
        if not is_street_obj:
            continue

        mw = obj.matrix_world
        bbox_w = [mw @ Vector(corner) for corner in obj.bound_box]
        z_min = min(v.z for v in bbox_w)
        z_max = max(v.z for v in bbox_w)

        # If the entire object is a flat ground/street/sidewalk mesh (`z_max <= 0.42m`), delete it completely
        if z_max <= 0.42 and z_min >= -2.5:
            print(f"[UPGRADE] Removing legacy flat street/ground object: {obj.name} (z=[{z_min:.2f}, {z_max:.2f}])")
            bpy.data.objects.remove(obj, do_unlink=True)
            continue

        # If the object is a combined legacy streetscape mesh (containing both ground/sidewalks AND tall props)
        if z_min <= 0.45:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            to_delete = []
            for f in bm.faces:
                verts_w = [mw @ v.co for v in f.verts]
                fz_min = min(v.z for v in verts_w)
                fz_max = max(v.z for v in verts_w)
                cx_f = sum(v.x for v in verts_w) / len(verts_w)
                cy_f = sum(v.y for v in verts_w) / len(verts_w)

                # Remove ALL old ground/asphalt/sidewalk/curb/marking/plaza faces (`fz_max <= 0.40m`)
                # so the new Boolean-manifold streets, sidewalks, curbs, and crosswalks are 100% clean!
                if fz_max <= 0.40 and fz_min >= -2.5:
                    to_delete.append(f)
                    continue

                # Remove any stray ground/street face far outside `ground_clip_box`
                if ground_clip_box is not None and fz_max <= 0.60:
                    if not ground_clip_box.buffer(8.0).contains(Point(cx_f, cy_f)):
                        to_delete.append(f)

            if to_delete:
                bmesh.ops.delete(bm, geom=to_delete, context="FACES")
                bm.to_mesh(obj.data)
                obj.data.update()
                print(f"[UPGRADE] Stripped {len(to_delete)} legacy ground/pavement-overlay faces from {obj.name}")
            bm.free()

            if len(obj.data.polygons) == 0:
                bpy.data.objects.remove(obj, do_unlink=True)

    # 4. Upgrade legacy trees with 9-lobe green 3D canopy and prune any tree/lamp on the road
    _upgrade_legacy_trees_and_prune_road_trees(road_union, owned_col)

    # 4b. Expand `MTL_Ground_Base` if any visible building extends beyond its default footprint
    obj_g = bpy.data.objects.get("MTL_Ground_Base")
    if obj_g is not None and obj_g.type == "MESH" and obj_g.data and len(obj_g.data.vertices) == 4:
        g_xs = [v.co.x for v in obj_g.data.vertices]
        g_ys = [v.co.y for v in obj_g.data.vertices]
        min_gx, max_gx = min(g_xs), max(g_xs)
        min_gy, max_gy = min(g_ys), max(g_ys)
        for bo in bpy.data.objects:
            if bo.type == "MESH" and not bo.hide_render and bo.name != "MTL_Ground_Base":
                mat_ns = [m.name for m in bo.data.materials if m]
                if _is_water_or_pier_object(bo.name, mat_ns):
                    continue
                mw = bo.matrix_world
                for corner in bo.bound_box:
                    wc = mw @ Vector(corner)
                    if abs(wc.x) < 2500.0 and abs(wc.y) < 2500.0:
                        min_gx = min(min_gx, wc.x - 14.0)
                        max_gx = max(max_gx, wc.x + 14.0)
                        min_gy = min(min_gy, wc.y - 14.0)
                        max_gy = max(max_gy, wc.y + 14.0)
        obj_g.data.vertices[0].co.x, obj_g.data.vertices[0].co.y = min_gx, min_gy
        obj_g.data.vertices[1].co.x, obj_g.data.vertices[1].co.y = max_gx, min_gy
        obj_g.data.vertices[2].co.x, obj_g.data.vertices[2].co.y = max_gx, max_gy
        obj_g.data.vertices[3].co.x, obj_g.data.vertices[3].co.y = min_gx, max_gy
        obj_g.data.update()

    # 5. Pack textures and save `.blend` and `.usdc`
    blender_lib.export_block_artifacts(block_id, owned_col)
    return True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", nargs="+", required=True, help="Block IDs to upgrade")
    args = parser.parse_args(argv)

    for bid in args.blocks:
        upgrade_single_block_in_place(bid)


if __name__ == "__main__":
    main()
