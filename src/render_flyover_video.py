"""
Generates a cinematic drone fly-over animation in Blender 5.2 (`BLENDER_EEVEE`)
across `output/montreal_master.blend`, showcasing:
1. Place d'Armes & Basilique Notre-Dame de Montréal (Twin Neo-Gothic Towers, Nave & Vieux Séminaire)
2. Old Montreal Historic Core & Marché Bonsecours (Silver Neoclassical Dome)
3. Old Port Waterfront Quays:
   - Grand Quai du Port de Montréal & 65m Observation Tower (`MTL-VM-0022`)
   - Montréal Science Centre & Quai King-Edward (`MTL-VM-0021`)
   - Quai Jacques-Cartier, Hangar 16 & Bateau-Mouche (`MTL-VM-0023`)
   - Bassin Bonsecours, Île Bonsecours & 60m La Grande Roue Ferris Wheel (`MTL-VM-0024`)
   - Quai de l'Horloge (45m Sailors' Memorial Clock Tower, Urban Beach & Yacht Marina, `MTL-VM-0025`)
"""
import os
import sys
import math
import subprocess
import shutil

try:
    import bpy
    import mathutils
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(BASE_DIR, "output", "montreal_master.blend")
FRAMES_DIR = os.path.join(BASE_DIR, "output", "renders", "flyover_frames")
OUT_RENDERS = os.path.join(BASE_DIR, "output", "renders")
SOCIAL_MEDIA_DIR = os.path.join(BASE_DIR, "social media", "media")
ARTIFACT_DIR = r"C:\Users\Felipe\.gemini\antigravity-cli\brain\46bfcc49-d0cd-4c6f-9b9e-df45a866983f"

os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(OUT_RENDERS, exist_ok=True)
os.makedirs(SOCIAL_MEDIA_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)


# Keyframes: (frame, cam_loc, target_loc, lens_mm)
FLYOVER_KEYFRAMES = [
    # Act I: Place d'Armes & Notre-Dame Basilica Full-Height Unobstructed Hero Reveal & Rise
    (1,   (-55.0,   28.0,  26.0), ( 16.0,  -24.0, 34.0), 24.0),
    (35,  (-36.0,   -8.0,  82.0), ( 18.0,  -24.0, 30.0), 25.0),
    (65,  ( 65.0, -145.0, 128.0), (135.0,  -35.0, 22.0), 26.0),
    # Act II: Grand Quai Tower, Montréal Science Centre, Rue de la Commune & Promenade du Vieux-Port (V5/V6)
    (105, (420.0, -280.0, 132.0), (245.0, -105.0, 14.0), 26.0),
    (145, (555.0,  -55.0, 122.0), (335.0,   48.0, 14.0), 26.0),
    # Act III: Marché Bonsecours, Quai Jacques-Cartier, Bassin Bonsecours & La Grande Roue Ferris Wheel
    (185, (725.0,  175.0, 115.0), (495.0,  310.0, 18.0), 26.0),
    (215, (855.0,  315.0, 118.0), (610.0,  445.0, 22.0), 26.0),
    # Act IV: Bassin de l'Horloge Marina, Plage de l'Horloge & 45m Sailors' Memorial Clock Tower
    (250, (945.0,  585.0, 102.0), (805.0,  745.0, 22.0), 25.0),
    (280, (960.0,  810.0,  86.0), (842.9,  838.4, 26.0), 25.0),
    # Act V: Sweep South over St. Lawrence Harbour -> Parc de Dieppe Peninsula & Habitat 67 Modular Cubes
    (315, (1120.0, -180.0, 118.0), (985.0, -345.0, 18.0), 25.0),
    # Act VI: Pointe-du-Moulin Pier, Silo No. 5 Grain Elevators, Bota Bota Spa & Lachine Canal Locks
    (345, (560.0, -720.0, 110.0), (365.0, -585.0, 24.0), 25.0),
    (370, (245.0, -580.0, 115.0), (210.0, -320.0, 18.0), 25.0),
    # Act VII: Grand Finale Panoramic Vista over Pointe-à-Callière, Grand Quai & Full Old Port Skyline
    (390, (215.0, -340.0, 136.0), (320.0,   60.0, 20.0), 24.0),
]

TOTAL_FRAMES = FLYOVER_KEYFRAMES[-1][0]


def setup_gpu(scene):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("HIP", "OPTIX", "CUDA", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == backend]
            if gpus:
                for d in prefs.devices:
                    d.use = (d.type == backend)
                scene.cycles.device = "GPU"
                return f"{backend}: {', '.join(d.name for d in gpus)}"
        except Exception:
            continue
    scene.cycles.device = "CPU"
    return "CPU (no GPU backend found)"


def _fcurves(idb):
    act = idb.animation_data.action if getattr(idb, "animation_data", None) else None
    if act is None:
        return []
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    return out


def setup_flyover_scene(preview_only: bool = False):
    print(f"[FLYOVER] Opening {MASTER_BLEND}...")
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)
    scene = bpy.context.scene

    # Hide any flat satellite ortho helper planes
    for obj in bpy.data.objects:
        if "Ground_Satellite_Ortho" in obj.name or "_Context_Proxy" in obj.name:
            obj.hide_render = True
            obj.hide_viewport = True

    # Ensure crisp golden-hour sun & sky lighting for EEVEE
    sun_objs = [o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN"]
    if not sun_objs:
        sun_data = bpy.data.lights.new("Flyover_Golden_Sun", type="SUN")
        sun_data.energy = 4.2
        sun_data.color = (1.0, 0.95, 0.86)
        sun_obj = bpy.data.objects.new("Flyover_Golden_Sun", sun_data)
        scene.collection.objects.link(sun_obj)
        sun_obj.rotation_euler = (math.radians(48.0), math.radians(18.0), math.radians(-125.0))
    else:
        for s in sun_objs:
            s.data.energy = min(max(s.data.energy, 3.5), 5.0)

    # Configure World background if needed
    if not scene.world:
        scene.world = bpy.data.worlds.new("Flyover_World")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.48, 0.67, 0.88, 1.0)
        bg_node.inputs[1].default_value = 1.15

    # Configure CYCLES with GPU & persistent data for fast multi-frame animation in headless mode
    scene.render.engine = "CYCLES"
    gpu_info = setup_gpu(scene)
    print(f"[FLYOVER] Render Device: {gpu_info}", flush=True)
    scene.render.use_persistent_data = True
    scene.render.use_simplify = True
    scene.cycles.texture_limit_render = "2048"
    scene.cycles.samples = 16
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.05
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        scene.cycles.denoising_use_gpu = True
    except Exception:
        pass
    scene.cycles.max_bounces = 2
    scene.cycles.diffuse_bounces = 1
    scene.cycles.glossy_bounces = 1
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 32

    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    scene.render.image_settings.file_format = "PNG"

    # Create animated Camera + Look-At Target Empty
    target_empty = bpy.data.objects.new("Flyover_Target", None)
    scene.collection.objects.link(target_empty)

    cam_data = bpy.data.cameras.new("Flyover_Cam")
    cam_data.type = "PERSP"
    cam_data.clip_start = 0.8
    cam_data.clip_end = 5500.0
    cam_obj = bpy.data.objects.new("Flyover_Cam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    track = cam_obj.constraints.new(type="TRACK_TO")
    track.target = target_empty
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    # Insert keyframes
    for frame, cam_loc, tgt_loc, lens in FLYOVER_KEYFRAMES:
        scene.frame_set(frame)
        cam_obj.location = cam_loc
        cam_obj.keyframe_insert(data_path="location", frame=frame)
        target_empty.location = tgt_loc
        target_empty.keyframe_insert(data_path="location", frame=frame)
        cam_data.lens = lens
        cam_data.keyframe_insert(data_path="lens", frame=frame)

    # Set smooth Bezier interpolation on all F-curves (Blender 4.4+/5.x slotted action compatible)
    for obj in (cam_obj, target_empty, cam_data):
        for fc in _fcurves(obj):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"

    if preview_only:
        test_frames = [140, 185, 215, 250, 280, 315, 345, 370, 390]
        for f in test_frames:
            scene.frame_set(f)
            out_f = os.path.join(FRAMES_DIR, f"preview_{f:04d}.png")
            if os.path.exists(out_f):
                try:
                    os.remove(out_f)
                except Exception:
                    pass
            scene.render.filepath = out_f
            print(f"[FLYOVER] Rendering preview frame {f} -> {out_f}...", flush=True)
            bpy.ops.render.render(write_still=True)
        return

    # Render full animation (resuming valid frames, fixing frames 15..60 around keyframe 35, and rendering 140..390)
    force_all = "--force-all" in sys.argv
    fix_window = set(range(15, 61))
    for f in range(1, TOTAL_FRAMES + 1):
        out_f = os.path.join(FRAMES_DIR, f"frame_{f:04d}.png")
        if not force_all and f <= 139 and f not in fix_window and os.path.exists(out_f) and os.path.getsize(out_f) > 250000:
            continue
        if os.path.exists(out_f):
            try:
                os.remove(out_f)
            except Exception:
                pass
        scene.frame_set(f)
        scene.render.filepath = out_f
        print(f"[FLYOVER] Rendering frame {f}/{TOTAL_FRAMES}...", flush=True)
        bpy.ops.render.render(write_still=True)


def encode_videos():
    ffmpeg_exe = shutil.which("ffmpeg") or r"C:\ProgramData\chocolatey\bin\ffmpeg.EXE"
    input_pattern = os.path.join(FRAMES_DIR, "frame_%04d.png")

    flyover_mp4 = os.path.join(OUT_RENDERS, "flyover.mp4")
    mp4_path = os.path.join(OUT_RENDERS, "montreal_notre_dame_to_old_port_flyover.mp4")
    mp4_1080p_path = os.path.join(OUT_RENDERS, "old_montreal_flyover_1080p.mp4")
    gif_path = os.path.join(OUT_RENDERS, "montreal_notre_dame_to_old_port_flyover.gif")
    gif_1080p_path = os.path.join(OUT_RENDERS, "old_montreal_flyover_1080p.gif")

    # 1. Encode high-bitrate H.264 MP4 (@ 24fps)
    cmd_mp4 = [
        ffmpeg_exe, "-y",
        "-framerate", "24",
        "-i", input_pattern,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "17",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        mp4_path,
    ]
    print("[FFMPEG] Encoding MP4:", " ".join(cmd_mp4))
    subprocess.run(cmd_mp4, check=True)
    shutil.copy2(mp4_path, flyover_mp4)
    shutil.copy2(mp4_path, mp4_1080p_path)

    # 2. Encode animated GIF (for universal Markdown / GitHub / Medium preview)
    cmd_gif = [
        ffmpeg_exe, "-y",
        "-framerate", "24",
        "-i", input_pattern,
        "-vf", "fps=12,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        "-loop", "0",
        gif_path,
    ]
    print("[FFMPEG] Encoding GIF:", " ".join(cmd_gif))
    subprocess.run(cmd_gif, check=True)
    shutil.copy2(gif_path, gif_1080p_path)

    # Copy MP4 and GIF to social media/media and artifact directory
    for src_f in (flyover_mp4, mp4_path, mp4_1080p_path, gif_path, gif_1080p_path):
        fname = os.path.basename(src_f)
        shutil.copy2(src_f, os.path.join(SOCIAL_MEDIA_DIR, fname))
        if os.path.exists(ARTIFACT_DIR):
            shutil.copy2(src_f, os.path.join(ARTIFACT_DIR, fname))
        print(f"[COPIED] {fname} -> social media/media & artifacts")


if __name__ == "__main__":
    if IN_BLENDER:
        preview = "--preview" in sys.argv
        setup_flyover_scene(preview_only=preview)
        if not preview:
            encode_videos()
    else:
        encode_videos()
