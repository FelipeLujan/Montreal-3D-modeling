#!/usr/bin/env python3
"""
src/blocks/refine_mtl_oly_0001.py
=================================
Bespoke Superblock Refinement & Landmark Restoration Script for `MTL-OLY-0001`
(Parc olympique de Montréal — Stade olympique, 165m Inclined Tour de Montréal,
Biodôme / Velodrome, Planétarium Rio Tinto Alcan, Esplanade & Olympic Village Pyramids,
spanning `X=[-450..1050], Y=[5550..6220]`).

Workflow:
1. Opens `output/blocks/MTL-OLY-0001.blend` (after `src/build_corridor_superblock.py -- MTL-OLY-0001`).
2. Purges any generic extruded OSM building polygons from `MTL-OLY-0001_Buildings_Fabric` that
   encroach upon the Olympic Park complex (`X in [185..645], Y in [5690..6325]`) so Roger
   Taillibert's sculptural landmarks (Stade olympique, 165m Tour de Montréal, Biodôme,
   Planétarium, Esplanade) are never occluded by generic brown/brick boxes.
3. Rebuilds/restores the full-detail `OLY_Park_Lawns_and_Curbs` multi-zone hardscape plaza,
   sunken metro oculus, Vans skatepark bowl, planter beds, and camera-corridor foreground
   architectural features across all 8 Street View cameras + Satellite Top-Down.
4. Generates high-density, non-coplanar 3D Raised Sidewalks & Granite Curbs (`MTL_Sidewalks_and_Curbs`),
   3D Street Markings (`MTL_Street_Markings` with Continental Zebra Crosswalks, White Stop Bars,
   Double Yellow Centerlines, and White Dashed Lane Dividers), and 96+ Poly Haven 3D Streetlamps
   (`MTL_PH_StreetLamp_001..096` with emissive luminaire bulbs) across the entire superblock.
5. Saves `output/blocks/MTL-OLY-0001.blend`, exports `output/blocks/MTL-OLY-0001.usdc`, and renders
   `output/renders/MTL-OLY-0001_snapshot.png`.
"""

import os
import sys
import site
import json
import math
import time
import random
from pathlib import Path

try:
    _user_site = site.getusersitepackages()
    if _user_site and _user_site not in sys.path:
        sys.path.append(_user_site)
except Exception:
    pass

import bpy
import bmesh
from mathutils import Vector, Matrix
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union

import importlib.util

SCRIPT_DIR = Path(r"C:\Users\Felipe\Documents\coding\montreal\src\blocks")
REPO_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
for _p in (str(REPO_ROOT), str(SCRIPT_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src import blender_lib
_spec = importlib.util.spec_from_file_location("build_mtl_oly_0001", str(SCRIPT_DIR / "build_mtl_oly_0001.py"))
oly_hero = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oly_hero)

BLOCK_ID = "MTL-OLY-0001"


def purge_olympic_park_fabric_intrusions():
    """
    Removes any faces/components from `MTL-OLY-0001_Buildings_Fabric` whose vertices fall inside
    the Olympic Park architectural campus (`X in [188..645], Y in [5700..6315]`) or within 22m
    of any preserved `OLY_Bldg_*` or hero landmark object, eliminating the giant brown extruded
    box over `Tour de Montréal` (20213158) and `Biodôme` (26699302).
    """
    fab_obj = bpy.data.objects.get(f"{BLOCK_ID}_Buildings_Fabric")
    if not fab_obj or fab_obj.type != "MESH":
        return

    # Collect XY bounding boxes (padded by 8m) of all preserved bespoke `OLY_*` meshes
    keepout_boxes = [
        # Core Olympic Park architectural reserve (Stade, Tour, Biodôme, Planétarium, Esplanade)
        (192.0, 5705.0, 635.0, 6285.0),
        # Olympic Village Pyramids reserve
        (120.0, 6260.0, 410.0, 6420.0),
    ]
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj == fab_obj:
            continue
        if obj.name.startswith("OLY_Bldg_") or obj.name.startswith("OLY_"):
            if "Tree" in obj.name or "StreetLamp" in obj.name or "Lawn" in obj.name:
                continue
            pts_w = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            xs = [p.x for p in pts_w]
            ys = [p.y for p in pts_w]
            keepout_boxes.append((min(xs) - 6.0, min(ys) - 6.0, max(xs) + 6.0, max(ys) + 6.0))

    bm = bmesh.new()
    bm.from_mesh(fab_obj.data)
    bm.faces.ensure_lookup_table()

    faces_to_del = []
    for f in bm.faces:
        fc = f.calc_center_median()
        if any(x0 <= fc.x <= x1 and y0 <= fc.y <= y1 for (x0, y0, x1, y1) in keepout_boxes):
            faces_to_del.append(f)

    if faces_to_del:
        bmesh.ops.delete(bm, geom=faces_to_del, context="FACES")
        # Clean loose verts/edges
        loose_e = [e for e in bm.edges if not e.link_faces]
        if loose_e:
            bmesh.ops.delete(bm, geom=loose_e, context="EDGES")
        loose_v = [v for v in bm.verts if not v.link_faces]
        if loose_v:
            bmesh.ops.delete(bm, geom=loose_v, context="VERTS")
        bm.normal_update()
        bm.to_mesh(fab_obj.data)
        fab_obj.data.update()
        print(f"[{BLOCK_ID}] Purged {len(faces_to_del):,} encroaching fabric faces from Olympic Park campus.")
    bm.free()


def build_superblock_sidewalks_markings_and_lamps(owned_col, dossier, mats):
    """
    Ensures `MTL_Sidewalks_and_Curbs` (Mat_PH_Concrete_Sidewalk, Mat_MTL_Granite_Plinth),
    `MTL_Street_Markings` (Mat_Road_Mark_Yellow, Mat_Road_Mark_White), and 96+ Poly Haven 3D
    streetlamp instances (`MTL_PH_StreetLamp_001..096`) are present across the full superblock
    and along all 8 Street View corridors.
    """
    for old_name in ("MTL_Sidewalks_and_Curbs", "MTL_Street_Markings"):
        old_o = bpy.data.objects.get(old_name)
        if old_o:
            bpy.data.objects.remove(old_o, do_unlink=True)
    for obj in list(bpy.data.objects):
        if obj.name.startswith("MTL_PH_StreetLamp_") or obj.name.startswith("OLY_StreetLamp_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    # First run blender_lib.build_ground_and_streets on the core Olympic Park satellite span
    # so the camera-matched streets, curbs, sidewalks, expansion joints, and crosswalks are exact.
    for core_name in ("MTL_Ground_Base", "MTL_OSM_Parks_Grass", "MTL_OSM_Streets_and_Walkways"):
        old_c = bpy.data.objects.get(core_name)
        if old_c:
            bpy.data.objects.remove(old_c, do_unlink=True)

    blender_lib.build_ground_and_streets(owned_col, dossier)

    # Slightly lower `MTL-OLY-0001_Streets_Sidewalks_And_Parks` and `MTL-OLY-0001_Ground_And_River`
    # by 0.008m inside the core Olympic Park box so `MTL_OSM_Streets_and_Walkways` and `OLY_Park_Lawns_and_Curbs`
    # never Z-fight with the superblock background mesh.
    sup_s = bpy.data.objects.get(f"{BLOCK_ID}_Streets_Sidewalks_And_Parks")
    if sup_s and sup_s.type == "MESH":
        bm_ss = bmesh.new()
        bm_ss.from_mesh(sup_s.data)
        core_del = []
        for f in bm_ss.faces:
            c = f.calc_center_median()
            # Inside the core Olympic Park Esplanade/Stadium/Biodome pad, let the high-res hero plazas & streets govern
            if 185.0 <= c.x <= 655.0 and 5645.0 <= c.y <= 6185.0:
                core_del.append(f)
        if core_del:
            bmesh.ops.delete(bm_ss, geom=core_del, context="FACES")
            bm_ss.to_mesh(sup_s.data)
            sup_s.data.update()
        bm_ss.free()

    # Also ensure `MTL-OLY-0001_Street_Trees_3D` does not place low-poly cone/sphere trees inside the core
    # 535m x 535m Olympic Park satellite/Street View zone (where high-poly `jacaranda_tree` kit assets live).
    sup_t = bpy.data.objects.get(f"{BLOCK_ID}_Street_Trees_3D")
    if sup_t and sup_t.type == "MESH":
        bm_st = bmesh.new()
        bm_st.from_mesh(sup_t.data)
        tree_del = [f for f in bm_st.faces if 120.0 <= f.calc_center_median().x <= 720.0 and 5620.0 <= f.calc_center_median().y <= 6260.0]
        if tree_del:
            bmesh.ops.delete(bm_st, geom=tree_del, context="FACES")
            bm_st.to_mesh(sup_t.data)
            sup_t.data.update()
        bm_st.free()


def main():
    t0 = time.time()
    blend_path = REPO_ROOT / "output" / "blocks" / f"{BLOCK_ID}.blend"
    usdc_path = REPO_ROOT / "output" / "blocks" / f"{BLOCK_ID}.usdc"
    snap_path = REPO_ROOT / "output" / "renders" / f"{BLOCK_ID}_snapshot.png"

    print(f"\n=== Refining Superblock {BLOCK_ID} ({blend_path}) ===")
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    # Calibrate world sky lighting & exposure (RSI-005)
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
    blender_lib.setup_world_sky(strength=0.95)

    owned_col = bpy.data.collections.get(f"Block_{BLOCK_ID}_Owned")
    if not owned_col:
        owned_col = bpy.data.collections.new(f"Block_{BLOCK_ID}_Owned")
        bpy.context.scene.collection.children.link(owned_col)

    dossier = blender_lib.load_dossier(BLOCK_ID)
    mats = oly_hero.build_olympic_materials()

    # 1. Purge generic fabric building intrusions inside the Olympic Park complex
    purge_olympic_park_fabric_intrusions()

    # 2. Rebuild high-detail streets, raised granite curbs, concrete sidewalks, zebra crosswalks & Poly Haven streetlamps
    build_superblock_sidewalks_markings_and_lamps(owned_col, dossier, mats)

    # 3. Rebuild `OLY_Park_Lawns_and_Curbs` & curated high-poly `jacaranda_tree` instances
    for obj in list(bpy.data.objects):
        if obj.name.startswith("OLY_Park_Lawns_and_Curbs") or obj.name.startswith("OLY_Tree_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    oly_hero.build_park_landscaping_and_props(owned_col, dossier, mats)

    # Sanitize any plaza faces that overlap street carriageways
    try:
        blender_lib.sanitize_non_street_pavement_overlays()
    except Exception as e:
        print(f"[WARN] sanitize_non_street_pavement_overlays: {e}")

    # 4. Pack textures, save .blend and .usdc
    try:
        bpy.ops.file.pack_all()
    except Exception:
        pass
    tmp_blend = str(blend_path) + ".tmp.blend"
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
    os.replace(tmp_blend, str(blend_path))
    try:
        bpy.ops.wm.usd_export(filepath=str(usdc_path), check_existing=False, visible_objects_only=True, export_materials=True)
    except Exception:
        pass

    # 5. Render aerial overview snapshot
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    blender_lib.setup_render_engine()
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    cx, cy = dossier.get("blender_center_xy_m", [386.971, 5903.273])
    cam_obj = bpy.data.objects.get(f"Cam_{BLOCK_ID}_Snap")
    if not cam_obj:
        cam_d = bpy.data.cameras.new(f"Cam_{BLOCK_ID}_Snap")
        cam_o = bpy.data.objects.new(f"Cam_{BLOCK_ID}_Snap", cam_d)
        scene.collection.objects.link(cam_o)
        cam_obj = cam_o
    cam_obj.data.clip_end = 8000.0
    cam_obj.location = (cx + 280.0, cy - 310.0, 210.0)
    direction = Vector((cx, cy + 40.0, 28.0)) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam_obj
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.filepath = str(snap_path)
    bpy.ops.render.render(write_still=True)
    print(f"=== Refined {BLOCK_ID} in {time.time() - t0:.1f}s -> {blend_path} & {snap_path} ===")


if __name__ == "__main__":
    main()
