#!/usr/bin/env python3
"""
render_block_for_critique.py
============================
Headless Blender 5.2 helper that opens `output/blocks/<BLOCK_ID>.blend`, ensures
the 4 Street View cameras and the 1:1 Google Maps Satellite-matched Top-Down
Orthographic camera (`Cam_Satellite_TopDown_Ortho`) are configured from
`data/blocks/<BLOCK_ID>/dossier.json`, renders any missing or requested iteration
views (`iter<N>_<label>.png` + `iter<N>_topdown_ortho.png`), and immediately runs
`generate_overlay_bands.py` to produce the Overlay Band / Comparison Strip boards
for the `visual-critic` subagent.

Usage:
  & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b "output/blocks/MTL-VM-0021.blend" --python src/render_block_for_critique.py -- --block MTL-VM-0021 --iter 1
"""

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path
import bpy

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--block", required=True)
    p.add_argument("--iter", type=int, default=1)
    p.add_argument("--force-cameras", action="store_true")
    return p.parse_args(argv)


def enable_gpu(scene):
    scene.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons.get("cycles")
    if not prefs:
        return
    cprefs = prefs.preferences
    for backend in ("HIP", "CUDA", "OPTIX", "ONEAPI"):
        try:
            cprefs.compute_device_type = backend
            cprefs.get_devices()
            gpus = [d for d in cprefs.devices if d.type != "CPU"]
            if gpus:
                for d in cprefs.devices:
                    d.use = (d.type != "CPU")
                return
        except Exception:
            continue


def setup_world_lighting(scene):
    if not scene.world:
        scene.world = bpy.data.worlds.new("World_Critique")
    scene.world.use_nodes = True
    nt = scene.world.node_tree
    has_bg = any(n.type == "BACKGROUND" for n in nt.nodes)
    if not has_bg:
        bg = nt.nodes.new("ShaderNodeBackground")
        bg.inputs["Color"].default_value = (0.62, 0.76, 0.95, 1.0)
        bg.inputs["Strength"].default_value = 1.35
        out = nt.nodes.new("ShaderNodeOutputWorld")
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    # Ensure a sun light exists if none in scene
    has_sun = any(o.type == "LIGHT" for o in bpy.data.objects)
    if not has_sun:
        light_data = bpy.data.lights.new("Sun_Critique", type="SUN")
        light_data.energy = 3.5
        light_data.color = (1.0, 0.96, 0.88)
        sun_obj = bpy.data.objects.new("Sun_Critique", light_data)
        sun_obj.rotation_euler = (math.radians(42.0), math.radians(15.0), math.radians(-35.0))
        scene.collection.objects.link(sun_obj)


def ensure_camera(name: str):
    obj = bpy.data.objects.get(name)
    if obj and obj.type == "CAMERA":
        return obj
    cam_data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def main():
    args = parse_args()
    block_id = args.block
    iteration = args.iter

    block_dir = REPO_ROOT / "data" / "blocks" / block_id
    renders_dir = block_dir / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)
    import time
    quad_sheet = block_dir / "overlay_bands" / f"iter{iteration}_{block_id}_3d_diagnostic_quad.png"
    if quad_sheet.exists() and (time.time() - quad_sheet.stat().st_mtime) < 5400:
        print(f"[SKIP] {quad_sheet.name} already rendered recently.")
        return
    dossier = json.loads((block_dir / "dossier.json").read_text(encoding="utf-8"))

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    enable_gpu(scene)
    scene.cycles.samples = 6
    scene.cycles.max_bounces = 1
    scene.cycles.diffuse_bounces = 1
    scene.cycles.glossy_bounces = 0
    scene.cycles.transmission_bounces = 1
    scene.cycles.transparent_max_bounces = 1
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.08
    scene.cycles.use_denoising = False
    scene.render.image_settings.file_format = "PNG"

    # Hide any GeoRef satellite planes or hidden proxies during render
    many_objs = len(bpy.data.objects) > 500
    for obj in bpy.data.objects:
        if "GeoRef" in obj.name or "Context_Proxy" in obj.name or "Ground_Satellite" in obj.name:
            obj.hide_render = True
        if many_objs and obj.modifiers:
            for mod in obj.modifiers:
                if mod.type in ("BEVEL", "SUBSURF"):
                    mod.show_render = False

    setup_world_lighting(scene)

    # 1. Render 4 Street View matched cameras if missing or forced
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100

    for cam_spec in dossier.get("streetview_cameras", []):
        label = cam_spec["label"]
        out_png = renders_dir / f"iter{iteration}_{label}.png"
        if out_png.exists() and not args.force_cameras:
            print(f"[SKIP] Existing camera render: {out_png.name}")
            continue

        cam_obj = ensure_camera(f"Cam_SV_{label}")
        cam_obj.data.type = "PERSP"
        cam_obj.data.lens_unit = "FOV"
        cam_obj.data.angle = math.radians(cam_spec.get("fov_deg", 90.0))
        cam_obj.data.clip_start = 0.2
        cam_obj.data.clip_end = 2500.0

        cx, cy = cam_spec["blender_cam_xy_m"]
        heading_deg = float(cam_spec.get("heading", cam_spec.get("heading_deg", 0.0)))
        pitch_deg = float(cam_spec.get("pitch_deg", 10.0))

        cam_obj.location = (cx, cy, 1.75)
        cam_obj.rotation_mode = "XYZ"
        cam_obj.rotation_euler = (
            math.radians(90.0 + pitch_deg),
            0.0,
            math.radians(-heading_deg),
        )

        scene.camera = cam_obj
        scene.render.filepath = str(out_png)
        bpy.ops.render.render(write_still=True)
        print(f"[OK] Rendered Street View camera: {out_png.name}")

    # 2. Always render the 1:1 Google Maps Satellite-Matched Top-Down Orthographic view
    sat_spec = dossier.get("satellite", {})
    sat_cx, sat_cy = sat_spec.get("center_xy_m", dossier.get("blender_center_xy_m", [0.0, 0.0]))
    sat_span = float(sat_spec.get("span_meters", 133.93))

    ortho_out = renders_dir / f"iter{iteration}_topdown_ortho.png"
    ortho_cam = ensure_camera(f"Cam_Satellite_TopDown_Ortho_{block_id}")
    ortho_cam.data.type = "ORTHO"
    ortho_cam.data.ortho_scale = sat_span
    ortho_cam.data.clip_start = 1.0
    ortho_cam.data.clip_end = 1000.0
    ortho_cam.location = (sat_cx, sat_cy, 300.0)
    ortho_cam.rotation_mode = "XYZ"
    ortho_cam.rotation_euler = (0.0, 0.0, 0.0)

    scene.camera = ortho_cam
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.filepath = str(ortho_out)
    bpy.ops.render.render(write_still=True)
    print(f"[OK] Rendered Satellite-Matched Top-Down Ortho: {ortho_out.name}")

    # 2b. Render 3D overview snapshot & 4-Angle 3D Isometric Diagnostic Views (SE, SW, NW, NE)
    snap_dir = REPO_ROOT / "output" / "renders"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_out = snap_dir / f"{block_id}_snapshot.png"
    cam_radius = max(102.0, sat_span * 0.46)
    cam_height = max(82.0, sat_span * 0.34)
    target_z = max(12.0, sat_span * 0.06)

    def aim_camera(cam_obj, loc_xyz, tgt_xyz, lens_mm=28.0):
        cam_obj.data.type = "PERSP"
        cam_obj.data.lens = lens_mm
        cam_obj.data.clip_start = 0.5
        cam_obj.data.clip_end = 5000.0
        cam_obj.location = loc_xyz
        dx = tgt_xyz[0] - loc_xyz[0]
        dy = tgt_xyz[1] - loc_xyz[1]
        dz = tgt_xyz[2] - loc_xyz[2]
        dist_xy = math.hypot(dx, dy)
        cam_obj.rotation_mode = "XYZ"
        cam_obj.rotation_euler = (
            math.radians(90.0) + math.atan2(dz, dist_xy),
            0.0,
            math.atan2(dy, dx) - math.radians(90.0),
        )

    if not snap_out.exists() or args.force_cameras:
        snap_cam = ensure_camera(f"Cam_Snapshot_{block_id}")
        aim_camera(snap_cam, (sat_cx + cam_radius, sat_cy - cam_radius * 0.88, cam_height), (sat_cx, sat_cy, target_z), lens_mm=28.0)
        scene.camera = snap_cam
        scene.render.resolution_x = 960
        scene.render.resolution_y = 540
        scene.render.filepath = str(snap_out)
        bpy.ops.render.render(write_still=True)
        print(f"[OK] Rendered 3D Overview Snapshot: {snap_out.name}")

    quad_angles = [
        ("SE_Iso", (sat_cx + cam_radius, sat_cy - cam_radius, cam_height)),
        ("SW_Iso", (sat_cx - cam_radius, sat_cy - cam_radius, cam_height)),
        ("NW_Iso", (sat_cx - cam_radius, sat_cy + cam_radius, cam_height)),
        ("NE_Iso", (sat_cx + cam_radius, sat_cy + cam_radius, cam_height)),
    ]
    for qlabel, qloc in quad_angles:
        qp = renders_dir / f"iter{iteration}_diag_{qlabel}.png"
        if not qp.exists() or args.force_cameras:
            qcam = ensure_camera(f"Cam_Diag_{qlabel}_{block_id}")
            aim_camera(qcam, qloc, (sat_cx, sat_cy, target_z), lens_mm=28.0)
            scene.camera = qcam
            scene.render.resolution_x = 640
            scene.render.resolution_y = 480
            scene.render.filepath = str(qp)
            bpy.ops.render.render(write_still=True)
            print(f"[OK] Rendered 3D Diagnostic View: {qp.name}")

    # 2c. Export automated 3D Geometry & Fenestration Forensics JSON
    ob_dir = block_dir / "overlay_bands"
    ob_dir.mkdir(parents=True, exist_ok=True)
    total_verts = 0
    total_faces = 0
    mat_names = set()
    windowless_tall_objects = []
    sidewalk_and_curb_faces = 0
    street_marking_faces = 0
    polyhaven_streetlamp_instances = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        me = obj.data
        n_polys = len(me.polygons)
        total_verts += len(me.vertices)
        total_faces += n_polys
        obj_mats = [m.name for m in me.materials if m]
        mat_names.update(obj_mats)
        oname_low = obj.name.lower()
        if "sidewalk" in oname_low or "curb" in oname_low or any("sidewalk" in m.lower() or "granite_plinth" in m.lower() for m in obj_mats):
            sidewalk_and_curb_faces += n_polys
        if "marking" in oname_low or "crosswalk" in oname_low or any("road_mark" in m.lower() for m in obj_mats):
            street_marking_faces += n_polys
        if "streetlamp" in oname_low or "street_lamp" in oname_low or "lantern" in oname_low:
            polyhaven_streetlamp_instances += 1
        zs = [(obj.matrix_world @ v.co).z for v in me.vertices] if me.vertices else [0.0]
        h_span = (max(zs) - min(zs)) if zs else 0.0
        if h_span > 8.0 and ("Bldg" in obj.name or "Building" in obj.name):
            has_glass = any("glass" in mn.lower() or "window" in mn.lower() or "glaz" in mn.lower() for mn in obj_mats)
            if not has_glass:
                windowless_tall_objects.append({"name": obj.name, "height_m": round(h_span, 2), "faces": n_polys})

    forensics = {
        "block_id": block_id,
        "iteration": iteration,
        "total_mesh_vertices": total_verts,
        "total_mesh_faces": total_faces,
        "distinct_materials_count": len(mat_names),
        "windowless_tall_buildings": windowless_tall_objects,
        "packed_images_count": sum(1 for img in bpy.data.images if img.packed_file is not None),
        "sidewalk_and_curb_faces": sidewalk_and_curb_faces,
        "street_marking_faces": street_marking_faces,
        "polyhaven_streetlamp_instances": polyhaven_streetlamp_instances,
        "street_signs_omitted": True,
    }
    (ob_dir / f"iter{iteration}_geometry_forensics.json").write_text(json.dumps(forensics, indent=2), encoding="utf-8")

    # 3. Call generate_overlay_bands.py using system Python
    cmd = ["python", str(REPO_ROOT / "src" / "generate_overlay_bands.py"), "--block", block_id, "--iter", str(iteration)]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
