"""
Generates visual progression boards (Ground Truth vs. Iteration 1 vs. Iteration 2 + Overlay Bands)
and copies all key real-world vs. 3D render comparisons and snapshots into:
1. `C:/Users/Felipe/Documents/coding/montreal/social media/media/`
2. `C:/Users/Felipe/.gemini/antigravity-cli/brain/46bfcc49-d0cd-4c6f-9b9e-df45a866983f/`
"""
import os
import shutil
from PIL import Image, ImageDraw, ImageFont

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
SOCIAL_MEDIA_DIR = os.path.join(WORKSPACE, "social media", "media")
ARTIFACT_DIR = r"C:\Users\Felipe\.gemini\antigravity-cli\brain\46bfcc49-d0cd-4c6f-9b9e-df45a866983f"

os.makedirs(SOCIAL_MEDIA_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def copy_to_both(src_path: str, dest_filename: str):
    if not os.path.exists(src_path):
        print(f"  [SKIP] Missing {src_path}")
        return None
    dst_social = os.path.join(SOCIAL_MEDIA_DIR, dest_filename)
    dst_artifact = os.path.join(ARTIFACT_DIR, dest_filename)
    shutil.copy2(src_path, dst_social)
    shutil.copy2(src_path, dst_artifact)
    print(f"  [COPIED] {dest_filename}")
    return dst_social


def extract_panel(critique_board_path: str, panel_idx: int):
    """
    Extracts one of the 4 panels from a 1400x1100 overlay critique board:
    panel_idx 0 = Top-Left (Ground Truth)
    panel_idx 1 = Top-Right (Blender 3D Render)
    panel_idx 2 = Bottom-Left (Horizontal Overlay Bands H1..H8)
    panel_idx 3 = Bottom-Right (Vertical Strips V1..V8 + Sobel Edges)
    """
    img = Image.open(critique_board_path).convert("RGB")
    w, h = img.size
    # Header is ~60px; 2x2 grid occupies the rest
    top_y = int(h * 0.055)
    mid_y = top_y + (h - top_y) // 2
    mid_x = w // 2
    if panel_idx == 0:
        return img.crop((0, top_y, mid_x, mid_y))
    elif panel_idx == 1:
        return img.crop((mid_x, top_y, w, mid_y))
    elif panel_idx == 2:
        return img.crop((0, mid_y, mid_x, h))
    else:
        return img.crop((mid_x, mid_y, w, h))


def build_4step_progression_banner(
    block_id: str,
    title: str,
    iter1_score: str,
    iter2_score: str,
    iter1_board_path: str,
    iter2_board_path: str,
    out_filename: str,
):
    """
    Creates a 4-column progression banner (2560 x 720):
    [1. Real World (Google Maps / Street View)] -> [2. Iteration 1 Render (FAIL)] -> [3. Iteration 2 Render (PASS)] -> [4. Iter 2 Overlay Bands & Edges]
    """
    if not (os.path.exists(iter1_board_path) and os.path.exists(iter2_board_path)):
        print(f"  [WARN] Missing board for {block_id}: {iter1_board_path} or {iter2_board_path}")
        return

    p_real = extract_panel(iter2_board_path, 0)
    p_iter1 = extract_panel(iter1_board_path, 1)
    p_iter2 = extract_panel(iter2_board_path, 1)
    p_bands = extract_panel(iter2_board_path, 3)  # Vertical strips + Green/Magenta Sobel edges

    col_w, col_h = 620, 580
    pad = 16
    header_h = 96
    canvas_w = 4 * col_w + 5 * pad
    canvas_h = header_h + col_h + 2 * pad

    canvas = Image.new("RGB", (canvas_w, canvas_h), (15, 18, 24))
    draw = ImageDraw.Draw(canvas)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 28)
        font_sub = ImageFont.truetype("arialbd.ttf", 20)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text(
        (pad, 18),
        f"{block_id}: {title}  |  Adversarial Progression: {iter1_score} (Iter 1 FAIL)  ->  {iter2_score} (Iter 2 PASS)",
        fill=(245, 248, 255),
        font=font_title,
    )

    cols = [
        (p_real, "1. GROUND TRUTH (GOOGLE SATELLITE / STREET VIEW)", (46, 160, 67)),
        (p_iter1, f"2. ITERATION 1 BLENDER RENDER ({iter1_score} - REJECTED)", (218, 54, 51)),
        (p_iter2, f"3. ITERATION 2 BLENDER RENDER ({iter2_score} - PASSED)", (35, 134, 54)),
        (p_bands, "4. ITER 2 OVERLAY STRIPS + SOBEL EDGES (GREEN=REAL, MAGENTA=3D)", (88, 166, 255)),
    ]

    for idx, (panel_img, label, badge_rgb) in enumerate(cols):
        x0 = pad + idx * (col_w + pad)
        y0 = header_h
        # Draw badge bar
        draw.rectangle([x0, y0 - 34, x0 + col_w, y0 - 4], fill=badge_rgb)
        draw.text((x0 + 10, y0 - 30), label, fill=(255, 255, 255), font=font_sub)
        resized = panel_img.resize((col_w, col_h), Image.Resampling.LANCZOS)
        canvas.paste(resized, (x0, y0))
        draw.rectangle([x0, y0, x0 + col_w, y0 + col_h], outline=badge_rgb, width=3)

    dst_social = os.path.join(SOCIAL_MEDIA_DIR, out_filename)
    dst_artifact = os.path.join(ARTIFACT_DIR, out_filename)
    canvas.save(dst_social, quality=95)
    canvas.save(dst_artifact, quality=95)
    print(f"  [BUILT PROGRESSION BANNER] {out_filename}")


def main():
    print("=== 1. Copying District-Wide Aerial & Comparison Renders ===")
    copy_to_both(
        os.path.join(ARTIFACT_DIR, "comparison_full_36blocks_overhauled.png"),
        "01_comparison_full_36blocks_google_vs_blender.png",
    )
    copy_to_both(
        os.path.join(ARTIFACT_DIR, "comparison_core_old_montreal_overhauled.png"),
        "02_comparison_core_old_montreal_google_vs_blender.png",
    )
    copy_to_both(
        os.path.join(WORKSPACE, "output", "renders", "montreal_master_snapshot.png"),
        "03_montreal_master_36blocks_snapshot.png",
    )
    copy_to_both(
        os.path.join(WORKSPACE, "output", "renders", "old_port_water_and_parks_verified.png"),
        "04_old_port_waterfront_and_parks_verified.png",
    )

    print("=== 2. Building 4-Column Progression Banners (Real vs. Iter 1 vs. Iter 2 vs. Overlay Bands) ===")
    progression_specs = [
        (
            "MTL-VM-0021",
            "Montreal Science Centre & Quai King-Edward",
            "48/100",
            "92/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0021", "overlay_bands", "iter1_Science_Centre_South_Promenade_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0021", "overlay_bands", "iter2_Science_Centre_South_Promenade_overlay_critique.png"),
            "prog_MTL_VM_0021_science_centre.png",
        ),
        (
            "MTL-VM-0022",
            "Grand Quai Cruise Terminal & Port Observation Tower",
            "62/100",
            "93/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0022", "overlay_bands", "iter1_Grand_Quai_Tower_South_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0022", "overlay_bands", "iter2_Grand_Quai_Tower_South_overlay_critique.png"),
            "prog_MTL_VM_0022_grand_quai.png",
        ),
        (
            "MTL-VM-0023",
            "Quai Jacques-Cartier, Hangar 16 & Harbor Basins",
            "55/100",
            "94/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0023", "overlay_bands", "iter1_satellite_topdown_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0023", "overlay_bands", "iter2_satellite_topdown_overlay_critique.png"),
            "prog_MTL_VM_0023_quai_jacques_cartier.png",
        ),
        (
            "MTL-VM-0024",
            "Bassin Bonsecours, Ile Bonsecours & La Grande Roue (60m Ferris Wheel)",
            "52/100",
            "95/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0024", "overlay_bands", "iter1_satellite_topdown_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0024", "overlay_bands", "iter2_satellite_topdown_overlay_critique.png"),
            "prog_MTL_VM_0024_bassin_bonsecours_grande_roue.png",
        ),
        (
            "MTL-VM-0025",
            "Quai de l'Horloge, Clock Tower, Urban Beach & Yacht Marina",
            "44/100",
            "92/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0025", "overlay_bands", "iter1_satellite_topdown_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0025", "overlay_bands", "iter2_satellite_topdown_overlay_critique.png"),
            "prog_MTL_VM_0025_clock_tower_pier.png",
        ),
        (
            "MTL-VM-0028",
            "Bota Bota Floating Ferry Spa & Silo No. 5 Grain Elevators",
            "38/100",
            "92/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0028", "overlay_bands", "iter1_satellite_topdown_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0028", "overlay_bands", "iter2_satellite_topdown_overlay_critique.png"),
            "prog_MTL_VM_0028_bota_bota_silo5.png",
        ),
        (
            "MTL-VM-0029",
            "Lachine Canal Entrance Locks (Ecluse No. 1) & Spillway Park",
            "35/100",
            "92/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0029", "overlay_bands", "iter1_satellite_topdown_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0029", "overlay_bands", "iter2_satellite_topdown_overlay_critique.png"),
            "prog_MTL_VM_0029_lachine_canal_locks.png",
        ),
        (
            "MTL-VM-0035",
            "Cite du Havre Peninsula, Parc de Dieppe Tennis Courts & Habitat 67",
            "40/100",
            "94/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0035", "overlay_bands", "iter1_satellite_topdown_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0035", "overlay_bands", "iter2_satellite_topdown_overlay_critique.png"),
            "prog_MTL_VM_0035_habitat67_satellite.png",
        ),
        (
            "MTL-VM-0029",
            "Street View: Lachine Canal Lock #1 (Cone Trees vs. Poly Haven 3D Trees)",
            "35/100",
            "92/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0029", "overlay_bands", "iter1_Ecluse_No1_Lock_Gate_West_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0029", "overlay_bands", "iter2_Ecluse_No1_Lock_Gate_West_overlay_critique.png"),
            "prog_MTL_VM_0029_streetview_lock_gate.png",
        ),
        (
            "MTL-VM-0024",
            "Street View: La Grande Roue de Montreal & Bassin Bonsecours Waterfront",
            "52/100",
            "95/100",
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0024", "overlay_bands", "iter1_Grande_Roue_Southwest_Waterfront_overlay_critique.png"),
            os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0024", "overlay_bands", "iter2_Grande_Roue_Southwest_Waterfront_overlay_critique.png"),
            "prog_MTL_VM_0024_streetview_grande_roue.png",
        ),
    ]

    for spec in progression_specs:
        build_4step_progression_banner(*spec)

    copy_to_both(
        os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0035", "overlay_bands", "iter2_Habitat_67_Modular_Cubes_Front_overlay_critique.png"),
        "iter2_MTL_VM_0035_Habitat_67_StreetView_critique.png",
    )
    copy_to_both(
        os.path.join(WORKSPACE, "data", "blocks", "MTL-VM-0035", "overlay_bands", "iter2_Avenue_Pierre_Dupuy_North_Approach_overlay_critique.png"),
        "iter2_MTL_VM_0035_Avenue_Pierre_Dupuy_StreetView_critique.png",
    )

    print("=== 3. Copying Master Overlay Sheets & Block Verification Renders ===")
    for bid in ["MTL-VM-0021", "MTL-VM-0022", "MTL-VM-0023", "MTL-VM-0024", "MTL-VM-0025", "MTL-VM-0028", "MTL-VM-0029", "MTL-VM-0035"]:
        copy_to_both(
            os.path.join(WORKSPACE, "data", "blocks", bid, "overlay_bands", f"iter1_{bid}_master_overlay_sheet.png"),
            f"iter1_{bid}_master_overlay_sheet.png",
        )
        copy_to_both(
            os.path.join(WORKSPACE, "data", "blocks", bid, "overlay_bands", f"iter2_{bid}_master_overlay_sheet.png"),
            f"iter2_{bid}_master_overlay_sheet.png",
        )
        copy_to_both(
            os.path.join(WORKSPACE, "output", "renders", f"{bid}_snapshot.png"),
            f"{bid}_iter2_snapshot.png",
        )

    # Also copy iconic historic block snapshots (Notre-Dame Basilica, Place d'Armes, Royal Bank, Marché Bonsecours, Five Roses)
    for bid in ["MTL-VM-0001", "MTL-VM-0002", "MTL-VM-0004", "MTL-VM-0006", "MTL-VM-0018", "MTL-VM-0031", "MTL-VM-0033", "MTL-VM-0036"]:
        copy_to_both(
            os.path.join(WORKSPACE, "output", "renders", f"{bid}_snapshot.png"),
            f"{bid}_snapshot.png",
        )

    print("=== Done building all social media comparison assets! ===")


if __name__ == "__main__":
    main()
