"""
Renders updated 1:1 Nadir Top-Down Orthographic aerial views of the stitched 36-block
`output/montreal_master.blend` (including all 8 remodeled Iteration 2 Old Port & Waterfront blocks),
fetches exact metric-aligned Google Maps Satellite orthophotos at matching centers and scales,
and builds:
1. Side-by-side 1:1 Nadir Top-Down Aerial Comparison Plates (with numbered landmark callouts & legend)
2. 4-Panel District-Wide Overlay-Band Comparison Boards (Real vs. 3D vs. Horizontal Bands H1..H8 vs. Vertical Sobel Strips V1..V8)
"""
import os
import sys
import math
import shutil
import urllib.request
from io import BytesIO

try:
    import bpy
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(BASE_DIR, "output", "montreal_master.blend")
OUT_RENDERS = os.path.join(BASE_DIR, "output", "renders")
SOCIAL_MEDIA_DIR = os.path.join(BASE_DIR, "social media", "media")
ARTIFACT_DIR = r"C:\Users\Felipe\.gemini\antigravity-cli\brain\46bfcc49-d0cd-4c6f-9b9e-df45a866983f"

os.makedirs(OUT_RENDERS, exist_ok=True)
os.makedirs(SOCIAL_MEDIA_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0

# 3 comprehensive Nadir Top-Down Orthographic Views covering all 36 blocks + Old Port Waterfront
VIEWS = [
    {
        "id": "full_36blocks",
        "title_left": "Google Maps Satellite — Full 36-Block District (2100m × 2100m)",
        "title_right": "Blender 5.2 Cycles Top-Down Render — All 36 Blocks (Ortho-Matched)",
        "cx": 180.0,
        "cy": -110.0,
        "scale_m": 2100.0,
        "zoom": 17,
        "blender_png": "blender_topdown_full_36blocks_v2.png",
        "gmaps_png": "google_topdown_full_36blocks_v2.png",
        "side_by_side_png": "topdown_comparison_full_36blocks.png",
        "overlay_board_png": "topdown_overlay_bands_full_36blocks.png",
    },
    {
        "id": "core_old_montreal_and_old_port",
        "title_left": "Google Maps Satellite — Old Montreal & Old Port Quays (1350m × 1350m)",
        "title_right": "Blender 5.2 Cycles Top-Down Render — Old Montreal & Old Port Quays",
        "cx": 240.0,
        "cy": 60.0,
        "scale_m": 1350.0,
        "zoom": 17,
        "blender_png": "blender_topdown_core_old_montreal_v2.png",
        "gmaps_png": "google_topdown_core_old_montreal_v2.png",
        "side_by_side_png": "topdown_comparison_core_old_montreal.png",
        "overlay_board_png": "topdown_overlay_bands_core_old_montreal.png",
    },
    {
        "id": "waterfront_harbor_and_habitat67",
        "title_left": "Google Maps Satellite — Old Port, Lachine Canal & Habitat 67 (1550m × 1550m)",
        "title_right": "Blender 5.2 Cycles Top-Down Render — Remodeled Waterfront & Habitat 67",
        "cx": 330.0,
        "cy": -180.0,
        "scale_m": 1550.0,
        "zoom": 17,
        "blender_png": "blender_topdown_waterfront_harbor_v2.png",
        "gmaps_png": "google_topdown_waterfront_harbor_v2.png",
        "side_by_side_png": "topdown_comparison_waterfront_harbor.png",
        "overlay_board_png": "topdown_overlay_bands_waterfront_harbor.png",
    },
    {
        "id": "old_port_v5_v6_closeup",
        "title_left": "Google Maps Satellite — Old Port V5/V6 Walkways, Trees & Rue de la Commune (720m × 720m)",
        "title_right": "Blender 5.2 Cycles Top-Down — Old Port V5/V6 Walkways, Vegetation & Street Overhaul",
        "cx": 355.0,
        "cy": 135.0,
        "scale_m": 720.0,
        "zoom": 18,
        "blender_png": "blender_topdown_old_port_v5_v6_v2.png",
        "gmaps_png": "google_topdown_old_port_v5_v6_v2.png",
        "side_by_side_png": "topdown_comparison_old_port_v5_v6.png",
        "overlay_board_png": "topdown_overlay_bands_old_port_v5_v6.png",
    },
]

LANDMARKS = [
    (0.0, 0.0, "Place d'Armes & Notre-Dame Basilica (Blocks 1-5)"),
    (-165.0, -75.0, "Royal Bank Tower & Rue St-Jacques (Block 6)"),
    (-365.0, 45.0, "Square Victoria & World Trade Centre (Blocks 11-12)"),
    (295.0, 215.0, "Place Jacques-Cartier & City Hall (Blocks 14, 16-17)"),
    (465.0, 325.0, "Marché Bonsecours Silver Dome (Block 18)"),
    (606.0, 447.0, "Bassin Bonsecours, Île Bonsecours & La Grande Roue (Block 24)"),
    (805.0, 515.0, "Quai de l'Horloge, Clock Tower, Beach & Marina (Block 25)"),
    (360.0, 120.0, "Quai Jacques-Cartier & Hangar 16 (Block 23)"),
    (310.0, -35.0, "Montréal Science Centre & Quai King-Edward (Block 21)"),
    (225.0, -210.0, "Grand Quai Cruise Terminal & Port Tower (Block 22)"),
    (-220.0, -490.0, "Bota Bota Ferry Spa & Silo No. 5 Elevators (Block 28)"),
    (-415.0, -600.0, "Lachine Canal Entrance Locks Écluse No. 1 (Block 29)"),
    (-570.0, -830.0, "Farine Five Roses Flour Mill & Bassin Peel (Block 36)"),
    (-245.0, 390.0, "Chinatown Paifang Gate & Palais des Congrès (Blocks 10, 31)"),
    (470.0, 620.0, "Place Gare-Viger / Château Viger (Block 33)"),
    (1065.0, -400.0, "Cité du Havre, Parc de Dieppe & Habitat 67 (Block 35)"),
]


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
    tile_size = 256 * scale
    num_tiles = 2 ** zoom
    world_size = tile_size * num_tiles
    x = (lon + 180.0) / 360.0 * world_size
    sin_lat = math.sin(math.radians(lat))
    y = (0.5 - math.log((1.0 + sin_lat) / (1.0 - sin_lat)) / (4.0 * math.pi)) * world_size
    return x, y


def render_blender_views():
    print(f"[BLENDER] Opening {MASTER_BLEND}...")
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)
    scene = bpy.context.scene

    # Hide any leftover flat satellite ground planes so only real 3D geometry renders
    for obj in bpy.data.objects:
        if "Ground_Satellite_Ortho" in obj.name:
            obj.hide_render = True
            obj.hide_viewport = True

    scene.render.engine = "CYCLES"
    scene.render.use_persistent_data = True
    scene.cycles.samples = 24
    scene.cycles.max_bounces = 2
    scene.cycles.diffuse_bounces = 1
    scene.cycles.glossy_bounces = 1
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 32
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.04
    scene.cycles.use_denoising = True
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

    cam_data = bpy.data.cameras.new("Cam_TopDown_Master")
    cam_data.type = "ORTHO"
    cam_data.clip_start = 1.0
    cam_data.clip_end = 5000.0
    cam_obj = bpy.data.objects.new("Cam_TopDown_Master", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    cam_obj.rotation_mode = "XYZ"
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)

    for v in VIEWS:
        cam_obj.location = (v["cx"], v["cy"], 1500.0)
        cam_data.ortho_scale = v["scale_m"]
        out_file = os.path.join(OUT_RENDERS, v["blender_png"])
        scene.render.filepath = out_file
        print(f"[BLENDER] Rendering {v['blender_png']} at center=({v['cx']}, {v['cy']}), scale={v['scale_m']}m...")
        bpy.ops.render.render(write_still=True)
        print(f"[BLENDER] Saved {out_file}")


def fetch_google_maps_metric_ortho(
    center_x_m: float,
    center_y_m: float,
    ortho_scale_m: float,
    out_px: int,
    zoom: int,
    out_path: str,
    maptype: str = "satellite",
):
    api_key = load_api_key()
    scale = 2
    req_w, req_h = 640, 640
    usable_half_px = 280 * scale

    half_m = ortho_scale_m / 2.0
    min_x, max_x = center_x_m - half_m, center_x_m + half_m
    min_y, max_y = center_y_m - half_m, center_y_m + half_m

    lat_nw, lon_nw = xy_to_latlon(min_x, max_y)
    lat_se, lon_se = xy_to_latlon(max_x, min_y)
    gx_min, gy_min = latlon_to_web_mercator_px(lat_nw, lon_nw, zoom, scale)
    gx_max, gy_max = latlon_to_web_mercator_px(lat_se, lon_se, zoom, scale)

    span_gx = gx_max - gx_min
    span_gy = gy_max - gy_min
    step_px = usable_half_px * 1.75

    nx = max(1, int(math.ceil(span_gx / step_px)))
    ny = max(1, int(math.ceil(span_gy / step_px)))

    canvas_w = int(math.ceil(span_gx)) + 2 * req_w * scale
    canvas_h = int(math.ceil(span_gy)) + 2 * req_h * scale
    origin_gx = gx_min - req_w * scale
    origin_gy = gy_min - req_h * scale

    canvas = Image.new("RGB", (canvas_w, canvas_h), (18, 28, 38))

    print(f"[GMAPS] Fetching ({maptype}, zoom={zoom}) {nx}x{ny} tile grid for {ortho_scale_m}m span...")
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

            crop_margin = 28 * scale
            cropped = tile_img.crop((0, crop_margin, req_w * scale, req_h * scale - crop_margin))

            tgx, tgy = latlon_to_web_mercator_px(tlat, tlon, zoom, scale)
            paste_x = int(round(tgx - (req_w * scale) / 2 - origin_gx))
            paste_y = int(round(tgy - (req_h * scale) / 2 + crop_margin - origin_gy))
            canvas.paste(cropped, (paste_x, paste_y))

    box = (
        int(round(gx_min - origin_gx)),
        int(round(gy_min - origin_gy)),
        int(round(gx_max - origin_gx)),
        int(round(gy_max - origin_gy)),
    )
    ortho_img = canvas.crop(box).resize((out_px, out_px), Image.Resampling.LANCZOS)
    ortho_img.save(out_path)
    print(f"[GMAPS] Saved {out_path}")
    return ortho_img


def build_side_by_side_plate(
    left_path: str,
    right_path: str,
    out_path: str,
    title_left: str,
    title_right: str,
    cx: float,
    cy: float,
    scale_m: float,
):
    left_img = Image.open(left_path).convert("RGB").resize((1400, 1400), Image.Resampling.LANCZOS)
    right_img = Image.open(right_path).convert("RGB").resize((1400, 1400), Image.Resampling.LANCZOS)
    w, h = 1400, 1400

    header_h = 74
    footer_h = 155
    gap = 20
    plate_w = w * 2 + gap
    plate_h = h + header_h + footer_h

    plate = Image.new("RGB", (plate_w, plate_h), (14, 18, 26))
    plate.paste(left_img, (0, header_h))
    plate.paste(right_img, (w + gap, header_h))

    draw = ImageDraw.Draw(plate)
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 26)
        font_badge = ImageFont.truetype("arialbd.ttf", 16)
        font_legend = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_legend = ImageFont.load_default()

    draw.text((24, 22), title_left, fill=(240, 245, 255), font=font_title)
    draw.text((w + gap + 24, 22), title_right, fill=(95, 240, 165), font=font_title)

    half_m = scale_m / 2.0
    visible_landmarks = []
    for idx, (lx, ly, name) in enumerate(LANDMARKS, start=1):
        u_norm = (lx - (cx - half_m)) / scale_m
        v_norm = 1.0 - (ly - (cy - half_m)) / scale_m
        if not (0.03 <= u_norm <= 0.97 and 0.03 <= v_norm <= 0.97):
            continue
        visible_landmarks.append((idx, name))
        px = int(round(u_norm * w))
        py = header_h + int(round(v_norm * h))

        for offset_x in (0, w + gap):
            bx = offset_x + px
            by = py
            r = 15
            draw.ellipse((bx - r, by - r, bx + r, by + r), fill=(225, 45, 35), outline=(255, 255, 255), width=2)
            num_str = str(idx)
            tw = 9 if len(num_str) == 1 else 16
            draw.text((bx - tw // 2, by - 9), num_str, fill=(255, 255, 255), font=font_badge)

    # Draw clean 4-column legend in footer
    legend_y0 = header_h + h + 14
    col_w = plate_w // 4
    for i, (idx, name) in enumerate(visible_landmarks):
        col = i % 4
        row = i // 4
        lx_pos = 24 + col * col_w
        ly_pos = legend_y0 + row * 30
        draw.ellipse((lx_pos, ly_pos + 2, lx_pos + 22, ly_pos + 24), fill=(225, 45, 35), outline=(255, 255, 255), width=1)
        draw.text((lx_pos + 6 if idx < 10 else lx_pos + 3, ly_pos + 4), str(idx), fill=(255, 255, 255), font=font_badge)
        draw.text((lx_pos + 30, ly_pos + 4), name, fill=(220, 228, 240), font=font_legend)

    plate.save(out_path)
    print(f"[PLATE] Saved side-by-side comparison to {out_path}")


def build_district_overlay_board(
    left_path: str,
    right_path: str,
    out_path: str,
    title: str,
):
    """
    Creates a 4-Panel District-Wide Top-Down Overlay-Band Board:
    1. Top-Left: Google Maps Satellite Ground Truth (with 8x8 H1..H8, V1..V8 grid)
    2. Top-Right: Blender 5.2 Cycles Top-Down Orthographic Render (with 8x8 grid)
    3. Bottom-Left: Horizontal Interleaved Overlay Bands (H1..H8 alternating REAL / 3D)
    4. Bottom-Right: Vertical Interleaved Strips (V1..V8) + Sobel Edge Alignment (Green=Real, Magenta=3D)
    """
    panel_sz = 900
    real_img = Image.open(left_path).convert("RGB").resize((panel_sz, panel_sz), Image.Resampling.LANCZOS)
    rend_img = Image.open(right_path).convert("RGB").resize((panel_sz, panel_sz), Image.Resampling.LANCZOS)

    # Panel 3: Horizontal bands H1..H8
    horiz_img = Image.new("RGB", (panel_sz, panel_sz))
    band_h = panel_sz // 8
    for b in range(8):
        y0 = b * band_h
        y1 = panel_sz if b == 7 else (b + 1) * band_h
        src = real_img if (b % 2 == 0) else rend_img
        horiz_img.paste(src.crop((0, y0, panel_sz, y1)), (0, y0))

    # Panel 4: Vertical strips V1..V8 + Green/Magenta Sobel edges
    vert_img = Image.new("RGB", (panel_sz, panel_sz))
    strip_w = panel_sz // 8
    for s in range(8):
        x0 = s * strip_w
        x1 = panel_sz if s == 7 else (s + 1) * strip_w
        src = real_img if (s % 2 == 0) else rend_img
        vert_img.paste(src.crop((x0, 0, x1, panel_sz)), (x0, 0))

    real_edges = np.array(real_img.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    rend_edges = np.array(rend_img.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    vert_arr = np.array(vert_img, dtype=np.float32) * 0.65
    vert_arr[:, :, 1] = np.clip(vert_arr[:, :, 1] + (real_edges > 38) * 150.0, 0, 255)
    vert_arr[:, :, 0] = np.clip(vert_arr[:, :, 0] + (rend_edges > 38) * 160.0, 0, 255)
    vert_arr[:, :, 2] = np.clip(vert_arr[:, :, 2] + (rend_edges > 38) * 160.0, 0, 255)
    vert_img = Image.fromarray(vert_arr.astype(np.uint8))

    try:
        font_hdr = ImageFont.truetype("arialbd.ttf", 24)
        font_sub = ImageFont.truetype("arialbd.ttf", 18)
        font_tag = ImageFont.truetype("arialbd.ttf", 14)
    except Exception:
        font_hdr = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_tag = ImageFont.load_default()

    def draw_grid(im: Image.Image, mode: str):
        d = ImageDraw.Draw(im)
        for i in range(1, 8):
            pos = i * (panel_sz // 8)
            d.line([(0, pos), (panel_sz, pos)], fill=(255, 255, 100), width=1)
            d.line([(pos, 0), (pos, panel_sz)], fill=(255, 255, 100), width=1)
        for b in range(8):
            y_mid = b * band_h + 6
            tag = f"H{b+1}" if mode == "grid" else f"H{b+1}:{'REAL' if b%2==0 else '3D'}"
            d.rectangle([4, y_mid - 2, 4 + len(tag) * 9, y_mid + 16], fill=(15, 20, 28))
            d.text((6, y_mid), tag, fill=(100, 255, 160) if b % 2 == 0 else (255, 160, 255), font=font_tag)
        for s in range(8):
            x_mid = s * strip_w + 8
            tag = f"V{s+1}" if mode == "grid" else f"V{s+1}:{'REAL' if s%2==0 else '3D'}"
            d.rectangle([x_mid - 2, 4, x_mid + len(tag) * 9, 22], fill=(15, 20, 28))
            d.text((x_mid, 6), tag, fill=(100, 255, 160) if s % 2 == 0 else (255, 160, 255), font=font_tag)

    p1 = real_img.copy()
    p2 = rend_img.copy()
    draw_grid(p1, "grid")
    draw_grid(p2, "grid")
    draw_grid(horiz_img, "horiz")
    draw_grid(vert_img, "vert")

    header_h = 68
    sub_h = 34
    pad = 14
    board_w = panel_sz * 2 + pad * 3
    board_h = header_h + (panel_sz + sub_h) * 2 + pad * 3

    board = Image.new("RGB", (board_w, board_h), (14, 18, 26))
    bd = ImageDraw.Draw(board)
    bd.text((pad, 18), title, fill=(240, 245, 255), font=font_hdr)

    panels = [
        (p1, "1. Ground-Truth Google Maps Satellite (8×8 Grid H1..H8, V1..V8)", (255, 220, 110)),
        (p2, "2. Blender 5.2 Cycles 3D Master Render (1:1 Nadir Orthographic)", (110, 245, 175)),
        (horiz_img, "3. Horizontal Interleaved Overlay Bands (H1..H8 Alternating REAL / 3D)", (130, 210, 255)),
        (vert_img, "4. Vertical Strips (V1..V8) + Sobel Edges (Green=Real, Magenta=3D)", (255, 150, 245)),
    ]

    for idx, (pim, ptitle, pcol) in enumerate(panels):
        col = idx % 2
        row = idx // 2
        x0 = pad + col * (panel_sz + pad)
        y0 = header_h + row * (panel_sz + sub_h + pad)
        bd.text((x0 + 6, y0 + 6), ptitle, fill=pcol, font=font_sub)
        board.paste(pim, (x0, y0 + sub_h))

    board.save(out_path)
    print(f"[OVERLAY] Saved 4-panel district overlay board to {out_path}")


def main():
    if IN_BLENDER:
        render_blender_views()
        return

    for v in VIEWS:
        gmaps_path = os.path.join(OUT_RENDERS, v["gmaps_png"])
        blender_path = os.path.join(OUT_RENDERS, v["blender_png"])
        side_path = os.path.join(OUT_RENDERS, v["side_by_side_png"])
        overlay_path = os.path.join(OUT_RENDERS, v["overlay_board_png"])

        if not os.path.exists(gmaps_path):
            fetch_google_maps_metric_ortho(
                center_x_m=v["cx"],
                center_y_m=v["cy"],
                ortho_scale_m=v["scale_m"],
                out_px=1400,
                zoom=v["zoom"],
                out_path=gmaps_path,
                maptype="satellite",
            )

        if os.path.exists(blender_path):
            build_side_by_side_plate(
                left_path=gmaps_path,
                right_path=blender_path,
                out_path=side_path,
                title_left=v["title_left"],
                title_right=v["title_right"],
                cx=v["cx"],
                cy=v["cy"],
                scale_m=v["scale_m"],
            )
            build_district_overlay_board(
                left_path=gmaps_path,
                right_path=blender_path,
                out_path=overlay_path,
                title=f"District Overlay-Band Comparison — {v['title_right']}",
            )

            # Copy to social media/media and artifact directory
            for src_f, dst_name in [
                (side_path, v["side_by_side_png"]),
                (overlay_path, v["overlay_board_png"]),
            ]:
                shutil.copy2(src_f, os.path.join(SOCIAL_MEDIA_DIR, dst_name))
                shutil.copy2(src_f, os.path.join(ARTIFACT_DIR, dst_name))
                print(f"[COPIED] {dst_name} -> social media/media & artifacts")

    # Also overwrite 01_comparison_full_36blocks_google_vs_blender.png and 02_comparison_core_old_montreal_google_vs_blender.png
    s1 = os.path.join(OUT_RENDERS, "topdown_comparison_full_36blocks.png")
    s2 = os.path.join(OUT_RENDERS, "topdown_comparison_core_old_montreal.png")
    if os.path.exists(s1):
        shutil.copy2(s1, os.path.join(SOCIAL_MEDIA_DIR, "01_comparison_full_36blocks_google_vs_blender.png"))
        shutil.copy2(s1, os.path.join(ARTIFACT_DIR, "01_comparison_full_36blocks_google_vs_blender.png"))
    if os.path.exists(s2):
        shutil.copy2(s2, os.path.join(SOCIAL_MEDIA_DIR, "02_comparison_core_old_montreal_google_vs_blender.png"))
        shutil.copy2(s2, os.path.join(ARTIFACT_DIR, "02_comparison_core_old_montreal_google_vs_blender.png"))


if __name__ == "__main__":
    main()
