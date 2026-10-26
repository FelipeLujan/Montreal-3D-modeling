"""
Generates exact metric-aligned Google Maps Satellite aerial images and matching
Blender 5.2 Cycles top-down orthographic aerial renders of output/montreal_master.blend,
plus side-by-side comparison plates.
"""
import os
import sys
import math
import urllib.request
from io import BytesIO

# Check if running inside Blender or standard Python
try:
    import bpy
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False
    from PIL import Image, ImageDraw, ImageFont

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
OUT_RENDERS = os.path.join(BASE_DIR, "output", "renders")
os.makedirs(OUT_RENDERS, exist_ok=True)

# Master World Origin (Place d'Armes Center - Maisonneuve Monument)
MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0


def load_api_key() -> str:
    env_path = os.path.join(BASE_DIR, ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("GOOGLE_MAPS_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise RuntimeError("GOOGLE_MAPS_API_KEY not found in .env")


def xy_to_latlon(x: float, y: float, origin_lat=MASTER_ORIGIN_LAT, origin_lon=MASTER_ORIGIN_LON):
    mean_lat = math.radians(origin_lat)
    lat = origin_lat + math.degrees(y / EARTH_RADIUS_M)
    lon = origin_lon + math.degrees(x / (EARTH_RADIUS_M * math.cos(mean_lat)))
    return lat, lon


def latlon_to_web_mercator_px(lat: float, lon: float, zoom: int, scale: int = 2):
    """Returns Web Mercator global pixel coordinates at given zoom and scale."""
    tile_size = 256 * scale
    num_tiles = 2 ** zoom
    world_size = tile_size * num_tiles
    x = (lon + 180.0) / 360.0 * world_size
    sin_lat = math.sin(math.radians(lat))
    y = (0.5 - math.log((1.0 + sin_lat) / (1.0 - sin_lat)) / (4.0 * math.pi)) * world_size
    return x, y


def fetch_google_maps_metric_ortho(
    center_x_m: float,
    center_y_m: float,
    ortho_scale_m: float,
    out_px: int,
    zoom: int,
    out_path: str,
    maptype: str = "satellite",
):
    """
    Downloads a grid of Google Static Maps satellite tiles and resamples them into
    an exact metric orthographic square [center_x - ortho_scale/2, center_x + ortho_scale/2]
    x [center_y - ortho_scale/2, center_y + ortho_scale/2] matching Blender's ORTHO camera.
    """
    api_key = load_api_key()
    scale = 2
    req_w, req_h = 640, 640
    # Crop bottom 24*scale px out of each staticmap call so Google watermarks at tile edges never overlap interior
    usable_half_px = 280 * scale  # 560 px half-width per tile -> 1120x1120 usable px

    half_m = ortho_scale_m / 2.0
    min_x, max_x = center_x_m - half_m, center_x_m + half_m
    min_y, max_y = center_y_m - half_m, center_y_m + half_m

    # Compute Web Mercator global pixel bounds for the 4 metric corners
    lat_nw, lon_nw = xy_to_latlon(min_x, max_y)
    lat_se, lon_se = xy_to_latlon(max_x, min_y)
    gx_min, gy_min = latlon_to_web_mercator_px(lat_nw, lon_nw, zoom, scale)
    gx_max, gy_max = latlon_to_web_mercator_px(lat_se, lon_se, zoom, scale)

    span_gx = gx_max - gx_min
    span_gy = gy_max - gy_min
    step_px = usable_half_px * 1.8  # overlap tiles slightly

    nx = max(1, int(math.ceil(span_gx / step_px)))
    ny = max(1, int(math.ceil(span_gy / step_px)))

    canvas_w = int(math.ceil(span_gx)) + 2 * req_w * scale
    canvas_h = int(math.ceil(span_gy)) + 2 * req_h * scale
    origin_gx = gx_min - req_w * scale
    origin_gy = gy_min - req_h * scale

    canvas = Image.new("RGB", (canvas_w, canvas_h), (18, 28, 38))

    print(f"Fetching Google Maps ({maptype}, zoom={zoom}) {nx}x{ny} tile grid for {ortho_scale_m}m span...")
    for ix in range(nx):
        for iy in range(ny):
            fx = (ix + 0.5) / nx
            fy = (iy + 0.5) / ny
            tx_m = min_x + fx * ortho_scale_m
            ty_m = max_y - fy * ortho_scale_m
            tlat, tlon = xy_to_latlon(tx_m, ty_m)

            url = (
                f"https://maps.googleapis.com/maps/api/staticmap"
                f"?center={tlat:.6f},{tlon:.6f}&zoom={zoom}&size={req_w}x{req_h}&scale={scale}"
                f"&maptype={maptype}&key={api_key}"
            )
            with urllib.request.urlopen(url, timeout=20) as resp:
                tile_img = Image.open(BytesIO(resp.read())).convert("RGB")

            # Crop top/bottom 30px margin to avoid repeating bottom edge logo on interior seams
            crop_margin = 28 * scale
            cropped = tile_img.crop((0, crop_margin, req_w * scale, req_h * scale - crop_margin))

            tgx, tgy = latlon_to_web_mercator_px(tlat, tlon, zoom, scale)
            paste_x = int(round(tgx - (req_w * scale) / 2 - origin_gx))
            paste_y = int(round(tgy - (req_h * scale) / 2 + crop_margin - origin_gy))
            canvas.paste(cropped, (paste_x, paste_y))

    # Extract exact bounding box [gx_min..gx_max, gy_min..gy_max] and resize to (out_px, out_px)
    box = (
        int(round(gx_min - origin_gx)),
        int(round(gy_min - origin_gy)),
        int(round(gx_max - origin_gx)),
        int(round(gy_max - origin_gy)),
    )
    ortho_img = canvas.crop(box).resize((out_px, out_px), Image.Resampling.LANCZOS)
    ortho_img.save(out_path)
    print(f"Saved metric-aligned Google Maps ortho to {out_path}")
    return ortho_img


def render_blender_ortho_views():
    """Renders the exact same two orthographic views in Blender 5.2 Cycles."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_adaptive_sampling = True
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception:
        pass

    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    cam_data = bpy.data.cameras.new("Cam_Ortho_Compare")
    cam_data.type = "ORTHO"
    cam_data.clip_start = 1.0
    cam_data.clip_end = 5000.0
    cam_obj = bpy.data.objects.new("Cam_Ortho_Compare", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Top-down looking straight down -Z, with +Y Up (North) and +X Right (East)
    cam_obj.rotation_mode = "XYZ"
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)

    views = [
        {
            "name": "blender_aerial_ortho_full_36blocks.png",
            "cx": 40.0,
            "cy": -60.0,
            "scale": 1950.0,
        },
        {
            "name": "blender_aerial_ortho_core_old_montreal.png",
            "cx": 110.0,
            "cy": 90.0,
            "scale": 1250.0,
        },
    ]

    for v in views:
        cam_obj.location = (v["cx"], v["cy"], 1200.0)
        cam_data.ortho_scale = v["scale"]
        out_file = os.path.join(OUT_RENDERS, v["name"])
        scene.render.filepath = out_file
        print(f"Rendering {v['name']} at center=({v['cx']}, {v['cy']}), ortho_scale={v['scale']}m...")
        bpy.ops.render.render(write_still=True)
        print(f"Saved {out_file}")


def build_side_by_side_plate(
    left_path: str,
    right_path: str,
    out_path: str,
    title_left: str,
    title_right: str,
    cx: float,
    cy: float,
    scale_m: float,
    landmarks: list,
):
    left_img = Image.open(left_path).convert("RGB")
    right_img = Image.open(right_path).convert("RGB")
    w, h = left_img.size

    header_h = 68
    gap = 20
    plate_w = w * 2 + gap
    plate_h = h + header_h

    plate = Image.new("RGB", (plate_w, plate_h), (15, 20, 28))
    plate.paste(left_img, (0, header_h))
    plate.paste(right_img, (w + gap, header_h))

    draw = ImageDraw.Draw(plate)
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 28)
        font_label = ImageFont.truetype("arialbd.ttf", 18)
    except Exception:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()

    draw.text((24, 18), title_left, fill=(240, 245, 255), font=font_title)
    draw.text((w + gap + 24, 18), title_right, fill=(120, 235, 175), font=font_title)

    # Draw numbered landmark callout badges at identical metric (x, y) coordinates on both views!
    half_m = scale_m / 2.0
    for idx, (lx, ly, name) in enumerate(landmarks, start=1):
        u_norm = (lx - (cx - half_m)) / scale_m
        v_norm = 1.0 - (ly - (cy - half_m)) / scale_m
        if not (0.03 <= u_norm <= 0.97 and 0.03 <= v_norm <= 0.97):
            continue
        px = int(round(u_norm * w))
        py = header_h + int(round(v_norm * h))

        for offset_x in (0, w + gap):
            bx = offset_x + px
            by = py
            r = 14
            draw.ellipse((bx - r, by - r, bx + r, by + r), fill=(230, 50, 40), outline=(255, 255, 255), width=2)
            num_str = str(idx)
            tw = 8 if len(num_str) == 1 else 14
            draw.text((bx - tw // 2, by - 9), num_str, fill=(255, 255, 255), font=font_label)

    plate.save(out_path)
    print(f"Saved side-by-side comparison plate to {out_path}")


def main():
    if IN_BLENDER:
        render_blender_ortho_views()
        return

    # Step 1: Fetch Google Maps Orthophotos
    full_gmaps = os.path.join(OUT_RENDERS, "google_maps_aerial_full_36blocks.png")
    core_gmaps = os.path.join(OUT_RENDERS, "google_maps_aerial_core_old_montreal.png")

    fetch_google_maps_metric_ortho(
        center_x_m=40.0,
        center_y_m=-60.0,
        ortho_scale_m=1950.0,
        out_px=1400,
        zoom=17,
        out_path=full_gmaps,
        maptype="satellite",
    )
    fetch_google_maps_metric_ortho(
        center_x_m=110.0,
        center_y_m=90.0,
        ortho_scale_m=1250.0,
        out_px=1400,
        zoom=18,
        out_path=core_gmaps,
        maptype="satellite",
    )

    landmarks = [
        (0.0, 0.0, "Place d'Armes & Notre-Dame Basilica"),
        (-165.0, -75.0, "Royal Bank Tower & Rue St-Jacques"),
        (-365.0, 45.0, "Square Victoria & World Trade Centre"),
        (295.0, 215.0, "Place Jacques-Cartier & City Hall"),
        (465.0, 325.0, "Marche Bonsecours & Bassin Bonsecours"),
        (805.0, 515.0, "Quai de l'Horloge (Clock Tower)"),
        (225.0, -70.0, "Grand Quai (Quai Alexandra) & Quai King-Edward"),
        (-240.0, -490.0, "Silo No. 5, Bota Bota & Pointe-du-Moulin"),
        (-425.0, -610.0, "Lachine Canal Locks (Ecluse No. 1)"),
        (-570.0, -830.0, "Farine Five Roses & Bassin Peel (Block 36)"),
        (-245.0, 390.0, "Chinatown Gate & Complexe Desjardins"),
        (470.0, 620.0, "Place Gare-Viger (Chateau Viger)"),
        (420.0, -520.0, "Cite du Havre & Habitat 67 Peninsula"),
    ]

    build_side_by_side_plate(
        left_path=full_gmaps,
        right_path=os.path.join(OUT_RENDERS, "blender_aerial_ortho_full_36blocks.png"),
        out_path=os.path.join(OUT_RENDERS, "comparison_full_36blocks_side_by_side.png"),
        title_left="Google Maps Satellite Aerial (1950m x 1950m)",
        title_right="Blender 5.2 Reconstruction (36 Blocks, Ortho-Matched)",
        cx=40.0,
        cy=-60.0,
        scale_m=1950.0,
        landmarks=landmarks,
    )

    build_side_by_side_plate(
        left_path=core_gmaps,
        right_path=os.path.join(OUT_RENDERS, "blender_aerial_ortho_core_old_montreal.png"),
        out_path=os.path.join(OUT_RENDERS, "comparison_core_old_montreal_side_by_side.png"),
        title_left="Google Maps Satellite — Old Montreal & Old Port (1250m)",
        title_right="Blender 5.2 Reconstruction — Old Montreal & Old Port",
        cx=110.0,
        cy=90.0,
        scale_m=1250.0,
        landmarks=landmarks,
    )


if __name__ == "__main__":
    main()
