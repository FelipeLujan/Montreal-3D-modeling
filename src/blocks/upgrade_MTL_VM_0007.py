"""
Fast Surgical Polish for City Block MTL-VM-0007 (Iteration 2)
=============================================================
Opens `output/blocks/MTL-VM-0007.blend` and performs 4 surgical fixes:
  1. Removes the 5 redundant wall-overlay boxes (`H1_245_AshlarWall_*`, `H1_244_AshlarWall`,
     `H2_Sulpice_BackingWall`, `H3_Tommy_WallOverlay`) that sat at `nx * 0.10` in front of
     the `nx * 0.05` window glass panes, restoring dark specular glass reflections and
     the recessed Tommy Café & Burgundy entrance doors.
  2. Replaces solid disc `ArchHead_*` and `Medallion_*` cylinders with hollow 3D torus
     rings (`create_torus_ring`) for authentic Venetian window arches and wrought-iron
     balcony scroll medallions.
  3. Adjusts `Road_Rue_SaintSulpice_Cobble` along the `150°` Rue Saint-Sulpice canyon
     (`z = 0.165`) with flanking granite curbs so cobblestone paving fills the street in
     `iter2_Corner_Rue_DeBresoles.png`, and brings `H4_652_ServiceDoorLeaf` &
     `H4_652_BlindWinRecess` forward of `H4_652_RubbleGableWall` (`nxG * 0.21`).
  4. Fine-tunes Camera 1 (`Rue_SaintSulpice_Facade`) to `(158.0, -71.2, 2.0)` heading `298°`
     so the left burgundy entrance door + steps + blue hanging sign, the two central
     triple-arched Venetian windows, and the right teal-window building are all framed.
"""
import os
import sys
import json
import math
import bpy
import bmesh
from mathutils import Euler

PROJECT_ROOT = r"C:\Users\Felipe\Documents\coding\montreal"
if os.path.join(PROJECT_ROOT, "src") not in sys.path:
    sys.path.append(os.path.join(PROJECT_ROOT, "src"))
if os.path.join(PROJECT_ROOT, "src", "blocks") not in sys.path:
    sys.path.append(os.path.join(PROJECT_ROOT, "src", "blocks"))

import build_MTL_VM_0007 as b0007

BLOCK_ID = "MTL-VM-0007"
BLEND_PATH = os.path.join(PROJECT_ROOT, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_PATH = os.path.join(PROJECT_ROOT, "output", "blocks", f"{BLOCK_ID}.usdc")
DOSSIER_PATH = os.path.join(PROJECT_ROOT, "data", "blocks", BLOCK_ID, "dossier.json")


def replace_mesh_with_torus(obj, radius, tube_r, rot_euler, seg_r=20, seg_t=8):
    loc = obj.location.copy()
    # Since bmesh baked world coords into vertices, compute bounding box center of existing mesh
    if len(obj.data.vertices) > 0:
        cx = sum(v.co.x for v in obj.data.vertices) / len(obj.data.vertices)
        cy = sum(v.co.y for v in obj.data.vertices) / len(obj.data.vertices)
        cz = sum(v.co.z for v in obj.data.vertices) / len(obj.data.vertices)
        center = (cx, cy, cz)
    else:
        center = (loc.x, loc.y, loc.z)

    bm = bmesh.new()
    for i in range(seg_r):
        a0 = 2.0 * math.pi * i / seg_r
        a1 = 2.0 * math.pi * (i + 1) / seg_r
        am = 0.5 * (a0 + a1)
        res = bmesh.ops.create_cone(
            bm, cap_ends=False, cap_tris=False, segments=seg_t,
            radius1=tube_r, radius2=tube_r, depth=radius * (a1 - a0) * 1.05
        )
        c_verts = res["verts"]
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler((0.0, math.pi * 0.5 - am, 0.0), 'XYZ').to_matrix(), verts=c_verts)
        bmesh.ops.translate(bm, vec=(radius * math.cos(am), 0.0, radius * math.sin(am)), verts=c_verts)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler(rot_euler, 'XYZ').to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(obj.data)
    bm.free()


def polish_block():
    if not os.path.exists(BLEND_PATH) and os.path.exists(BLEND_PATH + "@"):
        os.replace(BLEND_PATH + "@", BLEND_PATH)
    bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)

    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    owned_col = bpy.data.collections.get(f"Block_{BLOCK_ID}_Owned")
    cam_col = bpy.data.collections.get(f"Block_{BLOCK_ID}_Cameras")

    # 1. Remove the 5 redundant wall-overlay boxes that occluded the dark glass & recessed doors
    for bad_name in [
        "H1_245_AshlarWall_0", "H1_245_AshlarWall_1", "H1_244_AshlarWall",
        "H2_Sulpice_BackingWall", "H3_Tommy_WallOverlay",
        "Road_Rue_SaintSulpice_Cobble", "Sidewalk_Rue_SaintSulpice_SW",
        "H4_652_BlindWinRecess", "H4_652_ServiceDoorLeaf"
    ]:
        o = bpy.data.objects.get(bad_name)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)

    # 2. Replace solid disc ArchHead_* and Medallion_* cylinders with hollow 3D torus rings
    for o in list(bpy.data.objects):
        if "_ArchHead_" in o.name:
            # Estimate radius from bounding box
            r = max(0.22, min(0.45, max(o.dimensions.x, o.dimensions.y) * 0.45))
            replace_mesh_with_torus(o, r, 0.035, (0.0, 0.0, math.radians(-19.0)))
        elif "_Medallion_" in o.name:
            replace_mesh_with_torus(o, 0.18, 0.025, (0.0, 0.0, math.radians(-19.0)))

    # 3. Rebuild the Rue Saint-Sulpice Cobblestone Roadway & Curbs along the exact 150° canyon
    mat_cobble = bpy.data.materials.get("Mat_Cobble_Street")
    mat_sidewalk = bpy.data.materials.get("Mat_Sidewalk")
    mat_dark = bpy.data.materials.get("Mat_Frame_Dark")
    mat_iron = bpy.data.materials.get("Mat_Iron_Black")

    # Canyon centerline from (105.0, -14.0) down to (138.0, -68.0) along Rue Saint-Sulpice
    p1, p2 = (105.0, -14.0), (140.0, -66.0)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    r_len = math.hypot(dx, dy)
    r_rot = math.atan2(dy, dx)
    b0007.create_box(
        "Road_Rue_SaintSulpice_Cobble",
        ((p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5, 0.13),
        (r_len, 6.8, 0.08),
        r_rot, mat_cobble, owned_col, bevel_w=0.0
    )
    # Narrow sidewalk along building 339877652 & 339877243 SW side of street
    b0007.create_box(
        "Sidewalk_Rue_SaintSulpice_SW",
        (117.5, -30.5, 0.16),
        (38.0, 2.4, 0.12),
        r_rot, mat_sidewalk, owned_col, bevel_w=0.01
    )

    # Bring Blind Window Recess & Service Door forward of H4_652_RubbleGableWall (front face at nxG * 0.19)
    pG1, pG2 = (112.393, -27.14), (100.87, -46.398)
    dxG, dyG = pG2[0] - pG1[0], pG2[1] - pG1[1]
    lenG = math.hypot(dxG, dyG)
    rotG = math.atan2(dyG, dxG)
    nxG, nyG = dyG / lenG, -dxG / lenG
    bx_n, by_n = pG1[0] + 0.58 * dxG, pG1[1] + 0.58 * dyG
    b0007.create_box("H4_652_BlindWinRecess", (bx_n + nxG * 0.20, by_n + nyG * 0.20, 6.20), (1.35, 0.08, 2.35), rotG, mat_dark, owned_col)
    dx_srv, dy_srv = pG1[0] + 0.72 * dxG, pG1[1] + 0.72 * dyG
    b0007.create_box("H4_652_ServiceDoorLeaf", (dx_srv + nxG * 0.21, dy_srv + nyG * 0.21, 1.10), (1.08, 0.08, 2.15), rotG, mat_iron, owned_col)

    # 4. Update Cameras & Re-render Iteration 2
    scene = bpy.context.scene
    for c in list(cam_col.objects):
        bpy.data.objects.remove(c, do_unlink=True)

    cam_overrides = {
        "Rue_SaintSulpice_Facade": (158.0, -71.2, 2.0, 298.0, 12.0),
        "Cours_Le_Royer_Courtyard": (153.8, -88.2, 2.0, 299.8, 12.0),
        "Corner_Rue_SaintPaul": (136.0, -142.5, 1.9, 320.0, 12.0),
        "Corner_Rue_DeBresoles": (106.59, -18.39, 1.8, 150.0, 10.0),
    }

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    for cam_info in dossier.get("streetview_cameras", []):
        label = cam_info["label"]
        cx, cy, cz, heading, pitch = cam_overrides[label]
        fov = cam_info.get("fov_deg", 90.0)
        cam_data = bpy.data.cameras.new(name=f"SV_Cam_{label}")
        cam_data.lens_unit = 'FOV'
        cam_data.angle = math.radians(fov)
        cam_obj = bpy.data.objects.new(f"SV_Cam_{label}", cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = (cx, cy, cz)
        cam_obj.rotation_euler = (math.radians(90.0 + pitch), 0.0, math.radians(-heading))
        scene.camera = cam_obj
        out_file = os.path.join(b0007.RENDERS_DIR, f"iter2_{label}.png")
        scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        print(f"Rendered Street View Camera [{label}] -> {out_file}")

    # Overview Camera
    ov_data = bpy.data.cameras.new(name=f"{BLOCK_ID}_Overview_Cam")
    ov_data.lens_unit = 'FOV'
    ov_data.angle = math.radians(62.0)
    ov_obj = bpy.data.objects.new(f"{BLOCK_ID}_Overview_Cam", ov_data)
    cam_col.objects.link(ov_obj)
    ov_obj.location = (92.0, -172.0, 95.0)
    from mathutils import Vector
    direction = Vector((152.0, -72.0, 8.0)) - ov_obj.location
    ov_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = ov_obj
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    snap_path = os.path.join(b0007.OUTPUT_RENDERS_DIR, f"{BLOCK_ID}_snapshot.png")
    scene.render.filepath = snap_path
    bpy.ops.render.render(write_still=True)

    tmp_blend = BLEND_PATH + ".tmp.blend"
    if os.path.exists(tmp_blend):
        os.remove(tmp_blend)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
    os.replace(tmp_blend, BLEND_PATH)
    bpy.ops.wm.usd_export(filepath=USDC_PATH, check_existing=False)
    print(f"Saved {BLEND_PATH} and {USDC_PATH}")


if __name__ == "__main__":
    polish_block()
