"""
Montreal drone fly-over v2 — headless Blender 5.2 Cycles with sky, clouds, cloud shadows & aerial haze.

Re-uses the camera path in `src/render_flyover_video.py::FLYOVER_KEYFRAMES` (parsed, not imported, so the
old script's side effects never run) and adds:
  1. Physical sky  — Sky Texture (MULTIPLE_SCATTERING), sun disc off, matched 1:1 to the Sun lamp direction.
  2. Cloud dome    — procedural cumulus layer projected onto a virtual cloud ceiling in the World shader,
                     drifting with the wind + slowly evolving (4D noise). Reflects in the harbour water.
  3. Cloud shadows — invisible "shadow-only" cloud deck above the city that casts soft drifting shadows.
  4. Aerial haze   — compositor depth haze (Mist pass) blended toward the horizon colour; the sky itself
                     comes from the Environment pass so clouds are never washed out.
  5. Horizon tilt  — after the Notre-Dame reveal, camera pitch is limited to MIN_PITCH_DEG so the
                     skyline + clouds are in frame instead of a straight-down rooftop view.
  6. GPU (HIP) rendering, 1080p, motion blur, OIDN denoise, resumable frame loop, ffmpeg encode.

Usage:
  blender -b --factory-startup --python src/render_flyover_sky.py -- [--preview] [--res 1920x1080]
          [--frames 360] [--samples 32] [--start N] [--end N] [--cpu]
  python src/render_flyover_sky.py --encode          # MP4 + GIF -> output/renders & social media/media
"""
import ast
import math
import os
import shutil
import subprocess
import sys
import time

try:
    import bpy
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(BASE_DIR, "output", "montreal_master.blend")
BLENDER_V1_SCRIPT = os.path.join(BASE_DIR, "src", "render_flyover_video.py")
FRAMES_DIR = os.path.join(BASE_DIR, "output", "renders", "flyover_sky_frames")
OUT_RENDERS = os.path.join(BASE_DIR, "output", "renders")
SOCIAL_MEDIA_DIR = os.path.join(BASE_DIR, "social media", "media")
FPS = 24

# --- Environment look ---------------------------------------------------------------------------
SUN_ELEVATION_DEG = 30.0      # late-afternoon
SUN_ROTATION_DEG = -100.0     # Sky-Texture convention: 0 = +Y (north), +90 = +X (east) -> sun in the west
SUN_ENERGY = 4.2
SKY_STRENGTH = 0.12           # MULTIPLE_SCATTERING radiance is physical (~10 at horizon); scale to scene exposure
CLOUD_COVERAGE = 0.68         # 0 = clear, 1 = overcast
WIND_M_PER_FRAME = (0.012, 0.005)   # cloud drift in dome-UV units per frame
CLOUD_DECK_Z = 900.0          # m, shadow-casting deck height
CLOUD_SHADOW_OPACITY = 0.55
HAZE_COLOR = (0.80, 0.87, 0.97)   # ~ horizon sky radiance after SKY_STRENGTH
HAZE_MAX = 0.72
MIST_START, MIST_DEPTH = 150.0, 1500.0
MIN_PITCH_DEG = -12.0         # applied from the 3rd keyframe on (after the hero reveal)
# Camera-position fixes (keyframe index -> Blender metres). The original keyframe 2 (-72, -15, 78) sends the
# camera straight through 500 Place d'Armes (32 floors, footprint x -106..-50 / y -66..-16): black frames 58-66
# here (39-44 in the v1 Blender render). Shifted east of the tower, still west of the Basilica (x >= -8);
# verified clear of every OSM footprint with >= 12 m margin.
CAMERA_OVERRIDES = {1: (-36.0, -8.0, 82.0)}


# Original 8 keyframes stretched across frames 1..360 (must remain invariant so frames 1..360 are 100% preserved)
BASE_KEYFRAMES_240 = [
    (1,   (-55.0,  28.0,  26.0), ( 16.0,  -24.0, 34.0), 24.0),
    (35,  (-72.0, -15.0,  78.0), ( 18.0,  -24.0, 30.0), 25.0),
    (65,  ( 65.0, -145.0, 128.0), (135.0, -35.0, 22.0), 26.0),
    (105, (420.0, -280.0, 132.0), (245.0, -105.0, 14.0), 26.0),
    (145, (555.0,  -55.0, 122.0), (335.0,   48.0, 14.0), 26.0),
    (185, (725.0,  175.0, 115.0), (495.0,  310.0, 18.0), 26.0),
    (215, (855.0,  315.0, 118.0), (610.0,  445.0, 22.0), 26.0),
    (240, (955.0,  415.0, 145.0), (560.0,  340.0, 18.0), 25.0),
]

# Extended Old Port tour (frames 361..540) showcasing the rest of the Montreal Old Port
EXTENDED_SKY_KEYFRAMES = [
    # Act IV-A: Bassin de l'Horloge Yacht Marina, Plage de l'Horloge & 45m Sailors' Memorial Clock Tower
    (400, (965.0,  650.0,  96.0), (815.0,  810.0, 26.0), 25.0),
    # Act IV-B: Orbit Clock Tower & Plage de l'Horloge looking SSW down the Old Port & Harbour
    (435, (935.0,  895.0,  88.0), (760.0,  520.0, 18.0), 25.0),
    # Act V: Sweep South across Harbour -> Parc de Dieppe Peninsula & Habitat 67 Brutalist Modular Cubes
    (475, (1135.0, -140.0, 108.0), (820.0, -380.0, 18.0), 24.0),
    # Act VI: Pointe-du-Moulin Pier, Silo No. 5 Grain Elevators, Bota Bota Spa & Lachine Canal Locks
    (510, (620.0, -730.0, 102.0), (340.0, -480.0, 22.0), 25.0),
    # Act VII: Grand Finale Hero Vista over Pointe-à-Callière, Grand Quai & Full Old Port Skyline
    (540, (265.0, -520.0, 124.0), (380.0,   80.0, 22.0), 24.0),
    # Act VIII: Pont Jacques-Cartier Cantilever Bridge, Molson Heritage Waterfront & Biosphère Geodesic Dome
    (565, (1180.0,  920.0, 145.0), (765.0, 1389.0, 48.0), 25.0),
    # Act IX: Maison de Radio-Canada Tower, Sucrerie Lantic Refinery & Marché Maisonneuve / Avenue Morgan Corridor
    (590, (1120.0, 2950.0, 175.0), (828.0, 4540.0, 35.0), 25.0),
    # Act X: Château Dufresne Beaux-Arts Museum, Boulevard Pie-IX & Southern Reveal of Stade Olympique + 165m Inclined Tower
    (620, ( 160.0, 5260.0, 135.0), (370.0, 5960.0, 72.0), 25.0),
    # Act XI-A: Hero Orbit East of Stade Olympique, 165m Inclined Tour de Montréal & Biodôme Velodrome
    (655, ( 740.0, 5780.0, 148.0), (355.0, 6080.0, 68.0), 25.0),
    # Act XI-B: Close Hero Showcase of the Twin 19-Story Stepped Olympic Village Pyramids (Le Village olympique)
    (690, ( 510.0, 6110.0, 118.0), (255.0, 6335.0, 36.0), 25.0),
    # Act XII: Grand Olympic Complex Panoramic Finale — Twin Olympic Village Pyramids + 165m Tower + Stade Olympique + Biodôme
    (720, (-110.0, 6480.0, 165.0), (385.0, 5980.0, 58.0), 24.0),
]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    opts = {"preview": False, "res": (1920, 1080), "frames": 720, "samples": 16, "start": None, "end": None,
            "cpu": False, "encode": False, "out": FRAMES_DIR, "overwrite": False, "upgrade_streets": True,
            "save_master": False, "cloud_shadows": False, "motion_blur": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--preview": opts["preview"] = True
        elif a == "--cpu": opts["cpu"] = True
        elif a == "--encode": opts["encode"] = True
        elif a == "--overwrite": opts["overwrite"] = True
        elif a == "--no-upgrade-streets": opts["upgrade_streets"] = False
        elif a == "--save-master": opts["save_master"] = True
        elif a == "--cloud-shadows": opts["cloud_shadows"] = True
        elif a == "--motion-blur": opts["motion_blur"] = True
        elif a == "--res": w, h = argv[i + 1].lower().split("x"); opts["res"] = (int(w), int(h)); i += 1
        elif a in ("--frames", "--samples", "--start", "--end"): opts[a[2:]] = int(argv[i + 1]); i += 1
        elif a == "--out": opts["out"] = argv[i + 1]; i += 1
        elif a == "--only": opts["only"] = [int(x) for x in argv[i + 1].split(",")]; i += 1
        i += 1
    return opts


def _apply_horizon_tilt(cam, tgt):
    tgt = list(tgt)
    dist = math.hypot(tgt[0] - cam[0], tgt[1] - cam[1])
    min_dz = dist * math.tan(math.radians(MIN_PITCH_DEG))
    if tgt[2] - cam[2] < min_dz:
        tgt[2] = cam[2] + min_dz
    return tuple(tgt)


def load_keyframes(total_frames):
    base_span = 360
    src_last = BASE_KEYFRAMES_240[-1][0]
    out = []
    for idx, (f, cam, tgt, lens) in enumerate(BASE_KEYFRAMES_240):
        nf = 1 + round((f - 1) * (base_span - 1) / (src_last - 1))
        cam = CAMERA_OVERRIDES.get(idx, cam)
        if idx >= 2:
            tgt = _apply_horizon_tilt(cam, tgt)
        out.append((nf, cam, tuple(tgt), lens))
    if total_frames > base_span:
        for nf, cam, tgt, lens in EXTENDED_SKY_KEYFRAMES:
            if nf <= total_frames:
                out.append((nf, cam, _apply_horizon_tilt(cam, tgt), lens))
    return out


# =================================================================================================
# Blender side
# =================================================================================================
def sun_vector():
    el, rot = math.radians(SUN_ELEVATION_DEG), math.radians(SUN_ROTATION_DEG)
    return (math.sin(rot) * math.cos(el), math.cos(rot) * math.cos(el), math.sin(el))


def setup_gpu(scene, force_cpu=False):
    if force_cpu:
        scene.cycles.device = "CPU"
        return "CPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("HIP", "OPTIX", "CUDA", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == backend]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type == backend
                scene.cycles.device = "GPU"
                return f"{backend}: {', '.join(d.name for d in gpus)}"
        except Exception:
            continue
    scene.cycles.device = "CPU"
    return "CPU (no GPU backend)"


def setup_sun(scene):
    for o in [o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN"]:
        o.hide_render = True  # replace legacy suns so there is exactly one, matched to the sky
    sun_data = bpy.data.lights.new("Flyover_Sky_Sun", type="SUN")
    sun_data.energy = SUN_ENERGY
    sun_data.color = (1.0, 0.93, 0.82)
    sun_data.angle = math.radians(0.6)
    sun = bpy.data.objects.new("Flyover_Sky_Sun", sun_data)
    scene.collection.objects.link(sun)
    # Lamp shines along local -Z: rot=(90-el, 0, 180-skyRot) puts it exactly at the Sky-Texture sun.
    sun.rotation_euler = (math.radians(90.0 - SUN_ELEVATION_DEG), 0.0, math.radians(180.0 - SUN_ROTATION_DEG))


def _mix_rgba(nt, fac, a, b):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    rgba_in = [s for s in m.inputs if s.type == "RGBA"]
    for sock, val in ((m.inputs[0], fac), (rgba_in[0], a), (rgba_in[1], b)):
        if isinstance(val, bpy.types.NodeSocket):
            nt.links.new(val, sock)
        else:
            sock.default_value = val
    return [s for s in m.outputs if s.type == "RGBA"][0]


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for sock, val in ((n.inputs[0], a), (n.inputs[1], b)):
        if val is None:
            continue
        if isinstance(val, bpy.types.NodeSocket):
            nt.links.new(val, sock)
        else:
            sock.default_value = val
    return n.outputs[0]


def _map_range(nt, val, fmin, fmax, tmin=0.0, tmax=1.0, smooth=True):
    n = nt.nodes.new("ShaderNodeMapRange")
    n.interpolation_type = "SMOOTHSTEP" if smooth else "LINEAR"
    nt.links.new(val, n.inputs[0])
    n.inputs[1].default_value, n.inputs[2].default_value = fmin, fmax
    n.inputs[3].default_value, n.inputs[4].default_value = tmin, tmax
    return n.outputs[0]


def _cloud_noise(nt, vec_socket, scale, w_socket, detail=8.0):
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nz.inputs["Roughness"].default_value = 0.58
    nt.links.new(vec_socket, nz.inputs["Vector"])
    nt.links.new(w_socket, nz.inputs["W"])
    return nz.outputs["Fac"]


def _animated_wind(nt, total_frames, name, animate=True):
    """Mapping node whose Location is keyframed for linear wind drift; Value node keyed for evolution.
    Anchored at f=1 and f=360 with LINEAR extrapolation so frames 1..360 match existing renders bit-for-bit."""
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.name = name
    evo = nt.nodes.new("ShaderNodeValue")
    evo.outputs[0].default_value = 0.0
    if not animate:
        return mp, evo.outputs[0]
    loc = mp.inputs["Location"]
    base_span = 360
    scale_end = (total_frames - 1) / (base_span - 1)
    for f, k in ((1, 0.0), (total_frames, scale_end)):
        loc.default_value = (WIND_M_PER_FRAME[0] * base_span * k, WIND_M_PER_FRAME[1] * base_span * k, 0.0)
        loc.keyframe_insert("default_value", frame=f)
    for f, v in ((1, 0.0), (total_frames, 0.35 * scale_end)):
        evo.outputs[0].default_value = v
        evo.outputs[0].keyframe_insert("default_value", frame=f)
    for fc in _fcurves(nt):
        fc.extrapolation = "LINEAR"
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return mp, evo.outputs[0]


def _fcurves(idb):
    """F-curves of an ID for both legacy actions and Blender 4.4+/5.x slotted (layered) actions."""
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


def setup_world(scene, total_frames):
    world = bpy.data.worlds.new("Flyover_Sky_World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(bg.outputs[0], out.inputs["Surface"])

    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False                       # the Sun lamp provides the direct light (noise-free)
    sky.sun_elevation = math.radians(SUN_ELEVATION_DEG)
    sky.sun_rotation = math.radians(SUN_ROTATION_DEG)
    sky.altitude = 120.0
    sky.air_density, sky.aerosol_density = 1.0, 1.6   # a touch of summer haze
    sky_scaled = nt.nodes.new("ShaderNodeVectorMath"); sky_scaled.operation = "SCALE"
    nt.links.new(sky.outputs["Color"], sky_scaled.inputs[0]); sky_scaled.inputs["Scale"].default_value = SKY_STRENGTH

    # Direction -> cloud-ceiling UV  (uv = d.xy / (d.z + 0.06))
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    inv = _math(nt, "DIVIDE", 1.0, _math(nt, "ADD", sep.outputs["Z"], 0.06))
    uv = nt.nodes.new("ShaderNodeVectorMath"); uv.operation = "SCALE"
    nt.links.new(tc.outputs["Generated"], uv.inputs[0]); nt.links.new(inv, uv.inputs["Scale"])
    wind, evo = _animated_wind(nt, total_frames, "Cloud_Wind", animate=False)
    nt.links.new(uv.outputs[0], wind.inputs["Vector"])

    shape = _cloud_noise(nt, wind.outputs[0], 0.6, evo)
    lo = 0.62 - 0.22 * CLOUD_COVERAGE
    density = _map_range(nt, shape, lo, lo + 0.10)
    horizon_fade = _map_range(nt, sep.outputs["Z"], 0.0, 0.09)
    mask = _math(nt, "MULTIPLY", density, horizon_fade, clamp=True)
    mask = _math(nt, "MULTIPLY", mask, 0.95)

    # Self-shadowing: sample density again shifted toward the sun -> darker cloud bases
    sv = sun_vector()
    shifted = nt.nodes.new("ShaderNodeVectorMath"); shifted.operation = "ADD"
    nt.links.new(wind.outputs[0], shifted.inputs[0]); shifted.inputs[1].default_value = (sv[0] * 0.12, sv[1] * 0.12, 0.0)
    shade = _map_range(nt, _cloud_noise(nt, shifted.outputs[0], 0.6, evo), lo, lo + 0.25)
    lit = _math(nt, "SUBTRACT", 1.0, shade, clamp=True)
    cloud_col = _mix_rgba(nt, lit, (0.62, 0.66, 0.74, 1.0), (1.55, 1.48, 1.38, 1.0))
    sky_final = _mix_rgba(nt, mask, sky_scaled.outputs[0], cloud_col)
    nt.links.new(sky_final, bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0

    world.mist_settings.start = MIST_START
    world.mist_settings.depth = MIST_DEPTH
    world.mist_settings.falloff = "QUADRATIC"


def setup_cloud_shadows(scene, total_frames):
    """Invisible deck that only blocks Sun shadow rays -> soft drifting cloud shadows on the city."""
    size = 9000.0
    sv = sun_vector()
    cx, cy = 450.0 + sv[0] / sv[2] * CLOUD_DECK_Z, 100.0 + sv[1] / sv[2] * CLOUD_DECK_Z
    bpy.ops.mesh.primitive_plane_add(size=size, location=(cx, cy, CLOUD_DECK_Z))
    deck = bpy.context.active_object
    deck.name = "Flyover_Cloud_Shadow_Deck"
    deck.visible_camera = deck.visible_diffuse = deck.visible_glossy = False
    deck.visible_transmission = deck.visible_volume_scatter = False
    deck.visible_shadow = True

    mat = bpy.data.materials.new("Flyover_Cloud_Shadow_Mat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    scl = nt.nodes.new("ShaderNodeVectorMath"); scl.operation = "SCALE"
    nt.links.new(tc.outputs["Object"], scl.inputs[0]); scl.inputs["Scale"].default_value = 1.0 / 900.0
    wind, evo = _animated_wind(nt, total_frames, "Shadow_Wind", animate=False)
    nt.links.new(scl.outputs[0], wind.inputs["Vector"])
    lo = 0.62 - 0.22 * CLOUD_COVERAGE
    dens = _map_range(nt, _cloud_noise(nt, wind.outputs[0], 1.4, evo, detail=4.0), lo, lo + 0.2)  # soft shadows: fewer octaves = cheaper shadow rays
    opacity = _math(nt, "MULTIPLY", dens, CLOUD_SHADOW_OPACITY, clamp=True)
    mix = nt.nodes.new("ShaderNodeMixShader")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    hold = nt.nodes.new("ShaderNodeBsdfDiffuse"); hold.inputs["Color"].default_value = (0, 0, 0, 1)
    nt.links.new(opacity, mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(hold.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    deck.data.materials.append(mat)


def setup_compositor(scene):
    vl = scene.view_layers[0]
    vl.use_pass_mist = True
    vl.use_pass_environment = True
    scene.render.film_transparent = True   # Alpha separates geometry (hazed) from sky (Env pass, unhazed)

    ng = bpy.data.node_groups.new("Flyover_Haze_Compositor", "CompositorNodeTree")
    ng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.scene = scene
    gout = ng.nodes.new("NodeGroupOutput")

    def rl_out(*names):  # pass socket names differ across Blender versions ("Env" vs "Environment")
        for s in rl.outputs:
            if s.name in names or s.identifier in names:
                return s
        raise KeyError(f"Render Layers output {names} not found: {[s.name for s in rl.outputs]}")

    haze_fac = _math(ng, "MULTIPLY", rl_out("Mist"), HAZE_MAX, clamp=True)
    hazed = _mix_rgba(ng, haze_fac, rl_out("Image"), (*HAZE_COLOR, 1.0))
    final = _mix_rgba(ng, rl_out("Alpha"), rl_out("Env", "Environment", "Emit Environment"), hazed)
    if os.environ.get("FLYOVER_DEBUG_PASS"):  # e.g. FLYOVER_DEBUG_PASS=Mist -> write that pass instead
        final = rl_out(os.environ["FLYOVER_DEBUG_PASS"])
    ng.links.new(final, gout.inputs[0])
    scene.compositing_node_group = ng
    scene.render.use_compositing = True
    # The GPU compositor needs an OpenGL draw context, which crashes (GPU_fence_signal) in headless/RDP
    # sessions — the CPU compositor is plenty fast for 3 mix nodes.
    scene.render.compositor_device = "CPU"


def setup_camera(scene, keyframes):
    tgt = bpy.data.objects.new("Flyover_Target", None)
    scene.collection.objects.link(tgt)
    cam_data = bpy.data.cameras.new("Flyover_Cam")
    cam_data.clip_start, cam_data.clip_end = 0.8, 10000.0
    cam = bpy.data.objects.new("Flyover_Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    tr = cam.constraints.new(type="TRACK_TO")
    tr.target, tr.track_axis, tr.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    for f, c, t, lens in keyframes:
        cam.location = c; cam.keyframe_insert("location", frame=f)
        tgt.location = t; tgt.keyframe_insert("location", frame=f)
        cam_data.lens = lens; cam_data.keyframe_insert("lens", frame=f)
    for idb in (cam, tgt, cam_data):
        for fc in _fcurves(idb):
            for kp in fc.keyframe_points:
                kp.interpolation, kp.handle_left_type, kp.handle_right_type = "BEZIER", "AUTO_CLAMPED", "AUTO_CLAMPED"
            fc.update()
            for kp in fc.keyframe_points:
                if abs(kp.co.x - 360.0) < 0.5 or abs(kp.co.x - 540.0) < 0.5:
                    kp.handle_left_type = "FREE"
                    kp.handle_right_type = "FREE"
                    kp.handle_left.y = kp.co.y
                    kp.handle_right.y = kp.co.y
            fc.update()


def build_olympic_village_pyramids(target_col):
    """
    Constructs the iconic 1976 Montreal Olympic Village Twin 19-Story Stepped Brutalist Pyramids
    (Le Village olympique, designed by Roger D'Astous & Luc Durand, 5199 Rue Sherbrooke Est)
    just NNW of Stade Olympique at (185.0, 6310.0) and (335.0, 6360.0).
    """
    import bmesh
    from mathutils import Vector

    def _make_mat(name, rgba, rough=0.55, metal=0.0):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgba
            bsdf.inputs["Roughness"].default_value = rough
            bsdf.inputs["Metallic"].default_value = metal
        return m

    mat_conc = _make_mat("Mat_OLY_Village_Brutalist_Concrete", (0.79, 0.71, 0.58, 1.0), rough=0.64, metal=0.0)
    mat_glass = _make_mat("Mat_OLY_Village_Bronze_Glazing", (0.14, 0.16, 0.19, 1.0), rough=0.14, metal=0.35)
    mat_lawn = bpy.data.materials.get("Mat_PH_Park_Lawn_Lush") or _make_mat("Mat_OLY_Village_Terrace_Greenery", (0.16, 0.36, 0.14, 1.0), rough=0.78)
    mat_plaza = _make_mat("Mat_OLY_Village_Esplanade_Stone", (0.64, 0.61, 0.56, 1.0), rough=0.58)
    mat_trim = _make_mat("Mat_OLY_Village_Buff_Fins", (0.84, 0.77, 0.65, 1.0), rough=0.58, metal=0.0)

    bm = bmesh.new()
    # Lush Olympic Village Parkland Lawn connecting to MTL-OLY-0001 (X: 60..460, Y: 6180..6500)
    v0 = bm.verts.new((60.0, 6180.0, 0.04))
    v1 = bm.verts.new((460.0, 6180.0, 0.04))
    v2 = bm.verts.new((460.0, 6500.0, 0.04))
    v3 = bm.verts.new((60.0, 6500.0, 0.04))
    f_plz = bm.faces.new([v0, v1, v2, v3])
    f_plz.material_index = 2  # Lush green Olympic parkland lawn

    def _add_box(cx, cy, z0, z1, length, width, angle_rad, mat_idx):
        ca, sa = math.cos(angle_rad), math.sin(angle_rad)
        hl, hw = length * 0.5, width * 0.5
        corners_local = [(-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw)]
        bot, top = [], []
        for lx, ly in corners_local:
            wx = cx + lx * ca - ly * sa
            wy = cy + lx * sa + ly * ca
            bot.append(bm.verts.new((wx, wy, z0)))
            top.append(bm.verts.new((wx, wy, z1)))
        faces = [
            [top[0], top[1], top[2], top[3]],
            [bot[0], bot[1], top[1], top[0]],
            [bot[1], bot[2], top[2], top[1]],
            [bot[2], bot[3], top[3], top[2]],
            [bot[3], bot[0], top[0], top[3]],
        ]
        for fv in faces:
            try:
                f = bm.faces.new(fv)
                f.material_index = mat_idx
            except ValueError:
                pass

    # Build Twin 19-Story Stepped Semi-Pyramids (West Pyramid & East Pyramid)
    pyramids = [
        ("West", 185.0, 6310.0, math.radians(-18.0)),
        ("East", 335.0, 6360.0, math.radians(14.0)),
    ]
    n_floors = 19
    floor_h = 3.30
    for label, px, py, base_ang in pyramids:
        # Forecourt stone plaza pad beneath each pyramid core
        _add_box(px, py, 0.02, 0.12, 92.0, 82.0, base_ang, 3)
        # Central vertical Brutalist concrete elevator/stair core tower + pyramidal skylight atrium podium
        _add_box(px, py, 0.0, n_floors * floor_h + 6.5, 22.0, 18.0, base_ang, 4)
        _add_box(px, py, 0.0, 7.6, 44.0, 34.0, base_ang, 0)
        for sk_tier in range(4):
            sk_w = 18.0 - sk_tier * 3.8
            sk_z = 7.6 + sk_tier * 1.15
            _add_box(px, py, sk_z, sk_z + 1.15, sk_w, sk_w, base_ang, 1)
        # Three flared stepped wings per pyramid (0, +115 deg, -115 deg)
        for wing_deg in (0.0, 115.0, -115.0):
            wang = base_ang + math.radians(wing_deg)
            dx, dy = math.cos(wang), math.sin(wang)
            px_perp, py_perp = -dy, dx
            for fl in range(n_floors):
                z0 = fl * floor_h
                z1 = z0 + floor_h
                wing_len = max(14.0, 78.0 - fl * 3.25)
                wing_w = max(13.5, 20.0 - fl * 0.22)
                wcx = px + dx * (wing_len * 0.5 + 4.0)
                wcy = py + dy * (wing_len * 0.5 + 4.0)
                # Concrete floor slab & cantilevered balcony parapet (lower 1.35m of tier)
                _add_box(wcx, wcy, z0, z0 + 1.35, wing_len, wing_w, wang, 0)
                # Recessed bronze residential glazing band (middle 1.65m of tier)
                _add_box(wcx, wcy, z0 + 1.35, z1 - 0.30, max(10.0, wing_len - 1.2), wing_w - 1.4, wang, 1)
                # Upper concrete overhang slab
                _add_box(wcx, wcy, z1 - 0.30, z1, wing_len, wing_w, wang, 4)
                # Continuous green balcony planter troughs along both flanks & stepped nose
                for side_s in (-1.0, 1.0):
                    flk_x = wcx + px_perp * (side_s * (wing_w * 0.5 - 0.45))
                    flk_y = wcy + py_perp * (side_s * (wing_w * 0.5 - 0.45))
                    _add_box(flk_x, flk_y, z0 + 1.35, z0 + 1.62, wing_len - 0.8, 0.85, wang, 2)
                step_x = px + dx * (wing_len + 2.4)
                step_y = py + dy * (wing_len + 2.4)
                _add_box(step_x, step_y, z0 + 1.35, z0 + 1.65, 2.8, wing_w - 0.8, wang, 2)
                # Vertical precast party-wall fin dividers every 4.2m along the stepped tier
                n_bays = max(2, int(wing_len // 4.2))
                for b_i in range(1, n_bays):
                    s_bay = -wing_len * 0.5 + b_i * (wing_len / n_bays)
                    bx = wcx + dx * s_bay
                    by = wcy + dy * s_bay
                    _add_box(bx, by, z0 + 1.35, z1 - 0.25, 0.28, wing_w - 0.3, wang, 4)

    bm.normal_update()
    me = bpy.data.meshes.new("OLY_Village_Olympique_Pyramids")
    me.materials.append(mat_conc)
    me.materials.append(mat_glass)
    me.materials.append(mat_lawn)
    me.materials.append(mat_plaza)
    me.materials.append(mat_trim)
    bm.to_mesh(me)
    bm.free()

    obj = bpy.data.objects.new("OLY_Village_Olympique_Pyramids", me)
    target_col.objects.link(obj)
    print(f"[SKY-FLYOVER] Built Twin 19-Story Olympic Village Stepped Pyramids ({len(me.polygons):,} faces).", flush=True)


def append_expansion_and_olympic_blocks(scene):
    """
    Appends all 18 expansion & Olympic Corridor/Park blocks (MTL-VM-0037..0044 and MTL-OLY-0001..0010)
    into the Master Scene so the flyby camera showcases Pont Jacques-Cartier, Biosphère,
    the full continuous Olympic Corridor, Stade Olympique, 165m Inclined Tower, Biodôme, and Olympic Village.
    """
    from mathutils import Vector
    master_col = bpy.data.collections.get("Montreal_Master_World") or scene.collection
    expansion_ids = [f"MTL-VM-{i:04d}" for i in range(37, 45)] + [f"MTL-OLY-{i:04d}" for i in range(1, 11)]
    appended_total = 0
    for bid in expansion_ids:
        col_name = f"Block_{bid}_Stitched"
        if col_name in bpy.data.collections:
            continue
        blend_path = os.path.join(BASE_DIR, "output", "blocks", f"{bid}.blend")
        if not os.path.exists(blend_path):
            continue
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            data_to.objects = [
                name for name in data_from.objects
                if not any(k in name for k in (
                    "Cam_", "Camera", "Sun", "Light", "_Context_Proxy",
                    "Ground_Satellite_Ortho", "tree_small_02_trunk", "OLY_Village_Olympique_Pyramids"
                ))
            ]
        bcol = bpy.data.collections.new(col_name)
        master_col.children.link(bcol)
        cnt = 0
        for obj in data_to.objects:
            if obj is None or obj.type != "MESH" or not obj.data:
                continue
            if obj.hide_render:
                continue
            # Filter out any unlinked template meshes left near world origin (0,0,0) in MTL-OLY-* blocks
            if bid.startswith("MTL-OLY-"):
                ys_world = [obj.location.y + corner[1] for corner in obj.bound_box]
                if max(ys_world) < 700.0 and abs(obj.location.x) < 20.0 and abs(obj.location.y) < 20.0:
                    continue
            bcol.objects.link(obj)
            cnt += 1
        appended_total += cnt
        print(f"[SKY-FLYOVER] Appended {bid} ({cnt} mesh objects).", flush=True)

    # Clean up overlapping river ground planes & duplicate northern pyramids in MTL-OLY-* blocks
    import bmesh
    for bid in [f"MTL-OLY-{i:04d}" for i in range(1, 11)]:
        col = bpy.data.collections.get(f"Block_{bid}_Stitched")
        if not col:
            continue
        for obj in list(col.objects):
            if obj.type != "MESH" or not obj.data:
                continue
            # 1. Remove 1-face MTL_Ground_Base slabs in waterfront blocks MTL-OLY-0001, 0002, 0003, 0010
            #    that extend over the St. Lawrence River or duplicate Olympic parkland
            if obj.name.startswith("MTL_Ground_Base") and bid in ("MTL-OLY-0001", "MTL-OLY-0002", "MTL-OLY-0003", "MTL-OLY-0010"):
                obj.hide_render = obj.hide_viewport = True
                continue
            # 2. Trim any non-water ground faces in *_Ground_And_River that poke east of the river shoreline (X > 1015, Y < 3850)
            if "Ground_And_River" in obj.name and bid in ("MTL-OLY-0002", "MTL-OLY-0003", "MTL-OLY-0007"):
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                to_del = []
                for f in bm.faces:
                    c = f.calc_center_median()
                    mat_name = obj.data.materials[f.material_index].name if f.material_index < len(obj.data.materials) and obj.data.materials[f.material_index] else ""
                    if "Water" not in mat_name and "water" not in mat_name and c.x > 965.0 and c.y < 3850.0:
                        to_del.append(f)
                if to_del:
                    bmesh.ops.delete(bm, geom=to_del, context="FACES")
                    bm.to_mesh(obj.data)
                    obj.data.update()
                bm.free()
            # 3. Strip duplicate northern pyramids (Y > 6815, Z > 9.0) from MTL_Olympic_Village_And_Saputo_Hero
            #    while preserving Stade Saputo, Hôtel Universel, commercial podiums & parks
            if obj.name.startswith("MTL_Olympic_Village_And_Saputo_Hero"):
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                to_del = [f for f in bm.faces if f.calc_center_median().y > 6815.0 and f.calc_center_median().z > 9.0]
                if to_del:
                    bmesh.ops.delete(bm, geom=to_del, context="FACES")
                    bm.to_mesh(obj.data)
                    obj.data.update()
                bm.free()

    build_olympic_village_pyramids(master_col)
    return appended_total


def deduplicate_images_and_heavy_meshes():
    """
    Eliminates duplicate packed PBR textures (.001, .002, ...) and duplicate high-poly prop/tree
    meshes across the 54 stitched city blocks so Cycles GPU BVH & texture tables fit comfortably
    inside the 12 GB Radeon RX 6750 XT without altering a single rendered pixel.
    """
    import re
    # 1. Deduplicate bpy.data.images by canonical base name (stripping .001, .002 suffixes)
    canon_imgs = {}
    img_remap = {}
    for img in list(bpy.data.images):
        base = re.sub(r"\.\d{3,}$", "", img.name)
        key = (base, tuple(img.size))
        if key not in canon_imgs:
            canon_imgs[key] = img
        else:
            img_remap[img] = canon_imgs[key]

    remapped_nodes = 0
    for mat in bpy.data.materials:
        if not mat or not mat.use_nodes or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image in img_remap:
                node.image = img_remap[node.image]
                remapped_nodes += 1

    removed_imgs = 0
    for dup_img in list(img_remap.keys()):
        if dup_img.users == 0:
            bpy.data.images.remove(dup_img)
            removed_imgs += 1

    # 2. Deduplicate identical high-poly prop/tree meshes (> 10,000 vertices) across objects
    canon_meshes = {}
    mesh_remap = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data:
            continue
        me = obj.data
        nv, np = len(me.vertices), len(me.polygons)
        if nv < 10000:
            continue
        v0 = me.vertices[0].co
        vmid = me.vertices[nv // 2].co
        vlast = me.vertices[-1].co
        sig = (
            nv,
            np,
            round(v0.x, 3), round(v0.y, 3), round(v0.z, 3),
            round(vmid.x, 3), round(vmid.y, 3), round(vmid.z, 3),
            round(vlast.x, 3), round(vlast.y, 3), round(vlast.z, 3),
        )
        if sig not in canon_meshes:
            canon_meshes[sig] = me
        elif canon_meshes[sig] != me:
            mesh_remap[me] = canon_meshes[sig]
            obj.data = canon_meshes[sig]

    removed_meshes = 0
    for dup_me in list(set(mesh_remap.keys())):
        if dup_me.users == 0:
            bpy.data.meshes.remove(dup_me)
            removed_meshes += 1

    tot_verts = sum(len(m.vertices) for m in bpy.data.meshes)
    print(
        f"[SKY-FLYOVER] Deduplicated {removed_imgs} packed images ({len(bpy.data.images)} remain) "
        f"& {removed_meshes} heavy meshes ({len(bpy.data.meshes)} meshes, {tot_verts:,} unique verts remain).",
        flush=True,
    )


def setup_scene(opts):
    print(f"[SKY-FLYOVER] Opening {MASTER_BLEND} ...", flush=True)
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)
    scene = bpy.context.scene
    total = opts["frames"]
    for obj in bpy.data.objects:
        if "Ground_Satellite_Ortho" in obj.name or "_Context_Proxy" in obj.name:
            obj.hide_render = obj.hide_viewport = True

    append_expansion_and_olympic_blocks(scene)
    deduplicate_images_and_heavy_meshes()

    if opts.get("upgrade_streets", True):
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        from src.overhaul_streets_and_sidewalks import rebuild_streets_and_sidewalks
        rebuild_streets_and_sidewalks()

    # Prune stray jacaranda_tree twig vertices (R > 2.4m or Z > 6.2m) and disable unapplied BEVEL/SUBSURF modifiers
    import bmesh
    pruned_meshes = 0
    for me in list(bpy.data.meshes):
        if me and "jacaranda" in me.name.lower() and len(me.vertices) > 500:
            bm = bmesh.new()
            bm.from_mesh(me)
            bad_v = [v for v in bm.verts if math.hypot(v.co.x, v.co.y) > 2.4 or v.co.z > 6.2 or v.co.z < -0.25]
            if bad_v and len(bad_v) < len(bm.verts) - 20:
                bmesh.ops.delete(bm, geom=bad_v, context="VERTS")
                bm.to_mesh(me)
                me.update()
                pruned_meshes += 1
            bm.free()
    disabled_mods = 0
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.modifiers:
            for mod in obj.modifiers:
                if mod.type in ("BEVEL", "SUBSURF") and mod.show_render:
                    mod.show_render = False
                    disabled_mods += 1
    print(f"[SKY-FLYOVER] Pruned {pruned_meshes} tree meshes, disabled {disabled_mods} render modifiers.", flush=True)

    if opts.get("save_master"):
        tmp_blend = MASTER_BLEND + ".tmp.blend"
        print(f"[SKY-FLYOVER] Saving upgraded Master Scene to {MASTER_BLEND} ...", flush=True)
        bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
        os.replace(tmp_blend, MASTER_BLEND)
        print(f"[SKY-FLYOVER] Saved {MASTER_BLEND} ({os.path.getsize(MASTER_BLEND):,} bytes).", flush=True)

    scene.render.engine = "CYCLES"
    print("[SKY-FLYOVER] Device:", setup_gpu(scene, opts["cpu"]), flush=True)
    c = scene.cycles
    c.samples = opts["samples"]
    c.use_adaptive_sampling, c.adaptive_threshold = True, 0.05
    c.use_denoising = True
    try:
        c.denoiser = "OPENIMAGEDENOISE"
        c.denoising_use_gpu = True
    except Exception:
        pass
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 2, 1, 1
    c.transmission_bounces, c.transparent_max_bounces = 4, 16
    scene.render.use_persistent_data = True
    # VRAM: the full-res texture set (~11.4 GB) saturates the 12 GB RX 6750 XT and spills to host memory over
    # PCIe, starving the GPU. A 2K cap is visually lossless at 1080p aerial distances.
    scene.render.use_simplify = True
    c.texture_limit_render = os.environ.get("FLYOVER_TEX_LIMIT", "1024")
    scene.render.use_motion_blur = bool(opts.get("motion_blur")) and not os.environ.get("FLYOVER_NO_MB")
    scene.render.motion_blur_shutter = 0.15
    scene.render.resolution_x, scene.render.resolution_y = opts["res"]
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, total
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    setup_sun(scene)
    setup_world(scene, total)
    if opts.get("cloud_shadows"):
        setup_cloud_shadows(scene, total)
    setup_compositor(scene)
    setup_camera(scene, load_keyframes(total))
    return scene


def render_frames(scene, opts):
    os.makedirs(opts["out"], exist_ok=True)
    total = opts["frames"]
    if opts["preview"]:
        frames = opts.get("only") or [360, 400, 435, 475, 510, 540]
        prefix = "preview_"
    else:
        frames = opts.get("only") or list(range(opts["start"] or 1, (opts["end"] or total) + 1))
        prefix = "frame_"
    t0 = time.time()
    done = 0
    if os.environ.get("FLYOVER_PROFILE"):  # timestamped Cycles status lines -> shows where each frame's time goes
        last = {"txt": None}

        def _stats(txt):
            key = txt.split("|")[-1].strip()[:60]
            if key != last["txt"]:
                last["txt"] = key
                print(f"  [PROFILE {time.time():.2f}] {key}", flush=True)
                if key.startswith("Finished"):
                    print(f"  [PROFILE-STATS] {txt}", flush=True)
        bpy.app.handlers.render_stats.append(_stats)
    for f in frames:
        out_f = os.path.join(opts["out"], f"{prefix}{f:04d}.png")
        if not opts["preview"] and not opts.get("overwrite") and os.path.exists(out_f) and os.path.getsize(out_f) > 100_000:
            continue  # resumable
        ft = time.time()
        scene.frame_set(f)
        scene.render.filepath = out_f
        t_set = time.time() - ft
        bpy.ops.render.render(write_still=True)
        done += 1
        eta = (time.time() - t0) / done * (len(frames) - frames.index(f) - 1)
        print(f"[SKY-FLYOVER] frame {f}/{total} {time.time() - ft:.1f}s (frame_set {t_set:.1f}s)  "
              f"ETA {eta / 60:.1f} min", flush=True)


# =================================================================================================
# Encode side (plain Python)
# =================================================================================================
def qa_frames(opts):
    """Refuse to encode if frames are missing or (near-)black — e.g. the camera clipping inside a building."""
    total = opts["frames"]
    missing = [f for f in range(1, total + 1) if not os.path.exists(os.path.join(opts["out"], f"frame_{f:04d}.png"))]
    if missing:
        raise SystemExit(f"[QA] {len(missing)} frames missing (first: {missing[:10]}) — render still running?")
    try:
        from PIL import Image, ImageStat
    except ImportError:
        print("[QA] Pillow not installed — skipping black-frame check")
        return
    dark = []
    for f in range(1, total + 1):
        im = Image.open(os.path.join(opts["out"], f"frame_{f:04d}.png")).convert("L").resize((96, 54))
        if ImageStat.Stat(im).mean[0] < 15:
            dark.append(f)
    if dark:
        raise SystemExit(f"[QA] {len(dark)} near-black frames: {dark} — camera inside geometry?")
    print(f"[QA] {total} frames present, none black.")


def encode_videos(opts):
    qa_frames(opts)
    ffmpeg = shutil.which("ffmpeg") or r"C:\ProgramData\chocolatey\bin\ffmpeg.EXE"
    pattern = os.path.join(opts["out"], "frame_%04d.png")
    flyover_mp4 = os.path.join(OUT_RENDERS, "flyover.mp4")
    mp4 = os.path.join(OUT_RENDERS, "montreal_sky_flyover_1080p.mp4")
    olympic_mp4 = os.path.join(OUT_RENDERS, "olympic_village_flyover.mp4")
    vert = os.path.join(OUT_RENDERS, "montreal_sky_flyover_vertical_1080x1920.mp4")
    gif = os.path.join(OUT_RENDERS, "montreal_sky_flyover.gif")
    base = [ffmpeg, "-y", "-framerate", str(FPS), "-start_number", "1", "-i", pattern, "-frames:v", str(opts["frames"])]
    subprocess.run(base + ["-vf", "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", mp4], check=True)
    shutil.copy2(mp4, flyover_mp4)
    if opts["frames"] >= 720:
        oly_base = [ffmpeg, "-y", "-framerate", str(FPS), "-start_number", "541", "-i", pattern, "-frames:v", "180"]
        subprocess.run(oly_base + ["-vf", "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                                   "-movflags", "+faststart", olympic_mp4], check=True)
    # 9:16 centre crop for Shorts / Reels / TikTok
    subprocess.run(base + ["-vf", "crop=ih*9/16:ih,scale=1080:1920:flags=lanczos", "-c:v", "libx264",
                           "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", vert],
                   check=True)
    subprocess.run(base + ["-vf", "fps=12,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                           "-loop", "0", gif], check=True)
    os.makedirs(SOCIAL_MEDIA_DIR, exist_ok=True)
    to_copy = [flyover_mp4, mp4, vert, gif] + ([olympic_mp4] if os.path.exists(olympic_mp4) else [])
    for f in to_copy:
        shutil.copy2(f, os.path.join(SOCIAL_MEDIA_DIR, os.path.basename(f)))
        print(f"[ENCODED] {f} -> social media/media/")


if __name__ == "__main__":
    o = parse_args()
    if IN_BLENDER and not o["encode"]:
        render_frames(setup_scene(o), o)
        if not o["preview"] and not o.get("only") and o.get("end") is None:
            encode_videos(o)
    else:
        encode_videos(o)
