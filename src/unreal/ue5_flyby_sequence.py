"""
Unreal Engine 5.8 — Montreal Cinematic Fly-By (Level Sequence + Movie Render Queue)
===================================================================================
Ports the Blender drone fly-over (`src/render_flyover_video.py::FLYOVER_KEYFRAMES`) to Unreal so the
36-block `montreal_master.usdc` (loaded through the `UsdStageActor` in the `vehicle` project) can be
rendered with Lumen/Nanite instead of headless Cycles.

Run INSIDE the Unreal Editor (vehicle/vehicle/vehicle.uproject):
  - via the Unreal MCP server (UE 5.8 ModelContextProtocol plugin, port 8000) by executing this file, or
  - Tools -> Execute Python Script... -> src/unreal/ue5_flyby_sequence.py

What it does:
  1. Ensures a UsdStageActor pointing at output/montreal_master.usdc exists in the current level.
  2. Builds /Game/Montreal/Cinematics/LS_Montreal_Flyby with a CineCameraActor. Camera + look-at target
     are Catmull-Rom interpolated between the Blender keyframes and baked per frame (equivalent to the
     Blender TRACK_TO constraint), converted Blender (m, right-handed) -> Unreal (cm, left-handed: Y flipped).
  3. Queues a Movie Render Queue job (PNG, 1920x1080, temporal AA) into output/renders/ue5_flyby_frames.

Run OUTSIDE Unreal (plain Python) to encode the rendered frames to MP4/GIF with ffmpeg:
  python src/unreal/ue5_flyby_sequence.py
"""
import ast
import math
import os
import shutil
import subprocess
from pathlib import Path

try:
    import unreal
except ImportError:
    unreal = None

MONTREAL_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
MASTER_USD_PATH = MONTREAL_ROOT / "output" / "montreal_master.usdc"
BLENDER_FLYOVER_SCRIPT = MONTREAL_ROOT / "src" / "render_flyover_video.py"
FRAMES_DIR = MONTREAL_ROOT / "output" / "renders" / "ue5_flyby_frames"
OUT_RENDERS = MONTREAL_ROOT / "output" / "renders"
SOCIAL_MEDIA_DIR = MONTREAL_ROOT / "social media" / "media"

SEQUENCE_DIR = "/Game/Montreal/Cinematics"
SEQUENCE_NAME = "LS_Montreal_Flyby"
CAMERA_LABEL = "Montreal_Flyby_CineCamera"
FPS = 24
RES_X, RES_Y = 1920, 1080
# Blender default camera sensor = 36 mm (horizontal fit) -> match filmback so focal lengths look identical.
SENSOR_W_MM, SENSOR_H_MM = 36.0, 36.0 * RES_Y / RES_X


def load_blender_keyframes():
    """Single source of truth: parse FLYOVER_KEYFRAMES from the Blender script without importing bpy."""
    tree = ast.parse(BLENDER_FLYOVER_SCRIPT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "FLYOVER_KEYFRAMES" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError(f"FLYOVER_KEYFRAMES not found in {BLENDER_FLYOVER_SCRIPT}")


def blender_to_ue(p):
    """Blender metres (X east, Y north, Z up) -> Unreal cm (X east, Y south, Z up). Matches the USD import
    convention already used in output/ue5_nanite/montreal_ue5_manifest.json (blender_xyz_m -> ue5_xyz_cm)."""
    return (p[0] * 100.0, -p[1] * 100.0, p[2] * 100.0)


def catmull_rom(keys, frame):
    """Uniform Catmull-Rom over (frame, value-tuple) keys, clamped at the ends."""
    frames = [k[0] for k in keys]
    if frame <= frames[0]:
        return keys[0][1]
    if frame >= frames[-1]:
        return keys[-1][1]
    i = max(j for j in range(len(frames) - 1) if frames[j] <= frame)
    p0 = keys[max(i - 1, 0)][1]
    p1, p2 = keys[i][1], keys[i + 1][1]
    p3 = keys[min(i + 2, len(keys) - 1)][1]
    t = (frame - frames[i]) / float(frames[i + 1] - frames[i])
    t2, t3 = t * t, t * t * t
    return tuple(
        0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
        for a, b, c, d in zip(p0, p1, p2, p3)
    )


def bake_camera_path():
    """Returns [(seq_frame, cam_loc_cm, (pitch, yaw), lens_mm)] for every frame, yaw unwrapped."""
    kf = load_blender_keyframes()
    cam_keys = [(f, blender_to_ue(c)) for f, c, _, _ in kf]
    tgt_keys = [(f, blender_to_ue(t)) for f, _, t, _ in kf]
    lens_keys = [(f, (l,)) for f, _, _, l in kf]
    first, last = kf[0][0], kf[-1][0]

    baked, prev_yaw = [], None
    for f in range(first, last + 1):
        c = catmull_rom(cam_keys, f)
        t = catmull_rom(tgt_keys, f)
        dx, dy, dz = t[0] - c[0], t[1] - c[1], t[2] - c[2]
        yaw = math.degrees(math.atan2(dy, dx))
        pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
        if prev_yaw is not None:  # unwrap so Sequencer never spins 360 degrees between keys
            while yaw - prev_yaw > 180.0:
                yaw -= 360.0
            while yaw - prev_yaw < -180.0:
                yaw += 360.0
        prev_yaw = yaw
        baked.append((f - first, c, (pitch, yaw), catmull_rom(lens_keys, f)[0]))
    return baked


# ----------------------------------------------------------------------------------------------
# Unreal side
# ----------------------------------------------------------------------------------------------
def _actor_sub():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def ensure_usd_stage_actor():
    for actor in _actor_sub().get_all_level_actors():
        if isinstance(actor, unreal.UsdStageActor):
            unreal.log(f"[Montreal Flyby] Using existing UsdStageActor '{actor.get_actor_label()}'.")
            return actor
    stage = _actor_sub().spawn_actor_from_class(unreal.UsdStageActor, unreal.Vector(0, 0, 0))
    stage.set_actor_label("Montreal_USD_Stage")
    stage.set_editor_property("root_layer", unreal.FilePath(str(MASTER_USD_PATH).replace("\\", "/")))
    unreal.log("[Montreal Flyby] Spawned UsdStageActor -> montreal_master.usdc (first load can take minutes).")
    return stage


def _transform_channels(section):
    try:
        return list(section.get_all_channels())
    except Exception:
        return list(section.get_channels_by_type(unreal.MovieSceneScriptingDoubleChannel))


def build_level_sequence(baked):
    asset_path = f"{SEQUENCE_DIR}/{SEQUENCE_NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        unreal.EditorAssetLibrary.delete_asset(asset_path)
    seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_DIR, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    end_frame = baked[-1][0] + 1
    seq.set_display_rate(unreal.FrameRate(FPS, 1))
    seq.set_playback_start(0)
    seq.set_playback_end(end_frame)

    # Fresh CineCamera (remove stale ones from previous runs)
    for actor in _actor_sub().get_all_level_actors():
        if actor.get_actor_label() == CAMERA_LABEL:
            _actor_sub().destroy_actor(actor)
    cam = _actor_sub().spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(*baked[0][1]))
    cam.set_actor_label(CAMERA_LABEL)
    cam_comp = cam.get_cine_camera_component()
    filmback = cam_comp.get_editor_property("filmback")
    filmback.sensor_width, filmback.sensor_height = SENSOR_W_MM, SENSOR_H_MM
    cam_comp.set_editor_property("filmback", filmback)
    focus = cam_comp.get_editor_property("focus_settings")
    focus.focus_method = unreal.CameraFocusMethod.DISABLE  # aerial shot: everything sharp
    cam_comp.set_editor_property("focus_settings", focus)

    # Transform track — baked every frame
    cam_binding = seq.add_possessable(cam)
    xform_section = cam_binding.add_track(unreal.MovieScene3DTransformTrack).add_section()
    xform_section.set_range(0, end_frame)
    ch = _transform_channels(xform_section)  # Loc X,Y,Z, Rot Roll,Pitch,Yaw, Scale X,Y,Z
    linear = unreal.MovieSceneKeyInterpolation.LINEAR
    for frame, loc, (pitch, yaw), _ in baked:
        fn = unreal.FrameNumber(frame)
        for idx, val in ((0, loc[0]), (1, loc[1]), (2, loc[2]), (3, 0.0), (4, pitch), (5, yaw)):
            ch[idx].add_key(fn, val, interpolation=linear)

    # Focal length track on the CineCameraComponent
    comp_binding = seq.add_possessable(cam_comp)
    lens_track = comp_binding.add_track(unreal.MovieSceneFloatTrack)
    lens_track.set_property_name_and_path("CurrentFocalLength", "CurrentFocalLength")
    lens_section = lens_track.add_section()
    lens_section.set_range(0, end_frame)
    lens_ch = list(lens_section.get_all_channels())[0]
    for frame, _, _, lens in baked:
        lens_ch.add_key(unreal.FrameNumber(frame), lens, interpolation=linear)

    # Camera cut so MRQ renders through this camera
    cut_section = seq.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut_section.set_range(0, end_frame)
    try:
        binding_id = unreal.MovieSceneSequenceExtensions.get_portable_binding_id(seq, seq, cam_binding)
    except Exception:
        binding_id = seq.get_binding_id(cam_binding)
    cut_section.set_camera_binding_id(binding_id)

    unreal.EditorAssetLibrary.save_asset(asset_path)
    unreal.log(f"[Montreal Flyby] Built {asset_path}: {end_frame} frames @ {FPS} fps ({end_frame / FPS:.1f}s).")
    return seq


def queue_movie_render(seq):
    if not hasattr(unreal, "MoviePipelineQueueSubsystem"):
        raise RuntimeError("Movie Render Queue plugin is not enabled (add 'MovieRenderPipeline' to vehicle.uproject).")
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    mrq = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    queue = mrq.get_queue()
    queue.delete_all_jobs()
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.job_name = SEQUENCE_NAME
    job.sequence = unreal.SoftObjectPath(seq.get_path_name())
    job.map = unreal.SoftObjectPath(unreal.EditorLevelLibrary.get_editor_world().get_path_name())

    cfg = job.get_configuration()
    out = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    out.output_directory = unreal.DirectoryPath(str(FRAMES_DIR).replace("\\", "/"))
    out.output_resolution = unreal.IntPoint(RES_X, RES_Y)
    out.file_name_format = "frame_{frame_number}"
    out.zero_pad_frame_numbers = 4
    out.override_existing_output = True
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.spatial_sample_count = 1
    aa.temporal_sample_count = 8
    aa.override_anti_aliasing = True
    aa.anti_aliasing_method = unreal.AntiAliasingMethod.AAM_NONE  # TSR off; MRQ temporal samples do the AA
    aa.engine_warm_up_count = 32
    aa.render_warm_up_count = 64  # let Nanite / virtual textures / Lumen settle before frame 0
    try:
        cfg.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting).cinematic_quality_settings = True
    except Exception:
        pass

    mrq.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    unreal.log(f"[Montreal Flyby] Movie Render Queue started -> {FRAMES_DIR}")


def run_in_unreal(render=True):
    ensure_usd_stage_actor()
    seq = build_level_sequence(bake_camera_path())
    if render:
        queue_movie_render(seq)
    return seq


# ----------------------------------------------------------------------------------------------
# Plain-Python side: encode frames -> MP4 + GIF and publish to social media/media
# ----------------------------------------------------------------------------------------------
def encode_videos():
    ffmpeg = shutil.which("ffmpeg") or r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
    frames = sorted(FRAMES_DIR.glob("frame_*.png"))
    if not frames:
        raise SystemExit(f"No frames in {FRAMES_DIR} — run the Unreal side first.")
    start = int(frames[0].stem.split("_")[-1])
    pattern = str(FRAMES_DIR / "frame_%04d.png")
    mp4 = OUT_RENDERS / "montreal_ue5_flyby_1080p.mp4"
    gif = OUT_RENDERS / "montreal_ue5_flyby.gif"
    subprocess.run([ffmpeg, "-y", "-framerate", str(FPS), "-start_number", str(start), "-i", pattern,
                    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(mp4)], check=True)
    subprocess.run([ffmpeg, "-y", "-framerate", str(FPS), "-start_number", str(start), "-i", pattern,
                    "-vf", "fps=12,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                    "-loop", "0", str(gif)], check=True)
    SOCIAL_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    for f in (mp4, gif):
        shutil.copy2(f, SOCIAL_MEDIA_DIR / f.name)
        print(f"[ENCODED] {f} -> social media/media/{f.name}")


if __name__ == "__main__":
    if unreal is not None:
        run_in_unreal(render=True)
    else:
        encode_videos()
