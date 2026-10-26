#!/usr/bin/env python3
"""
generate_overlay_bands.py
=========================
Implements the Gemini 4 Argon + Google Antigravity Adversarial Visual Critique
"Overlay Bands / Comparison Strips" methodology:
  - AI Studio 3D Worlds Guide: https://aistudio.google.com/learn/building-3d-games-and-worlds-with-gemini-4-argon
  - Tiago Aragona 3D Cathedral Demo: https://www.youtube.com/watch?v=OYp5j2RihPE
    ("An agent even automatically overlaid these comparison strips against the
     reference image to get the geometry closer, iteration after iteration.")

Since this pipeline reconstructs real-world Montreal city blocks rather than
synthetic Nano Banana concept art, it uses:
  1. Real Google Street View panoramas (`data/blocks/<ID>/streetview/<label>.jpg`)
  2. Real Google Maps Satellite orthophotos (`data/blocks/<ID>/streetview/satellite_topdown.png`)
as the 2D ground-truth reference images, and overlays interleaved Horizontal &
Vertical Comparison Strips + Edge-Contour Alignment bands against the camera-matched
Blender 3D renders (`data/blocks/<ID>/renders/iter<N>_<label>.png`).

Usage:
  python src/generate_overlay_bands.py --block MTL-VM-0021 --iter 1
"""

import argparse
import json
import os
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_font(size: int = 16, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def compute_sobel_edges(img_rgb: np.ndarray) -> np.ndarray:
    """Compute normalized gradient magnitude in [0, 1] from an HxWx3 uint8 array."""
    gray = (
        0.299 * img_rgb[:, :, 0].astype(np.float32)
        + 0.587 * img_rgb[:, :, 1].astype(np.float32)
        + 0.114 * img_rgb[:, :, 2].astype(np.float32)
    )
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = (gray[:, 2:] - gray[:, :-2]) * 0.5
    gy[1:-1, :] = (gray[2:, :] - gray[:-2, :]) * 0.5
    mag = np.sqrt(gx * gx + gy * gy)
    p98 = np.percentile(mag, 98.0)
    if p98 > 1e-5:
        mag = np.clip(mag / p98, 0.0, 1.0)
    return mag


def build_horizontal_overlay_bands(
    real_img: Image.Image,
    render_img: Image.Image,
    num_bands: int = 8,
    band_labels: list[str] | None = None,
) -> Image.Image:
    """
    Create interleaved horizontal comparison strips (Venetian-blind overlay bands)
    alternating between Ground-Truth Reference and Blender 3D Render at identical
    vertical pixel ranges.
    """
    w, h = real_img.size
    real_np = np.array(real_img.convert("RGB"))
    rend_np = np.array(render_img.convert("RGB"))
    out_np = np.zeros_like(real_np)

    band_h = h / num_bands
    for b in range(num_bands):
        y0 = int(round(b * band_h))
        y1 = int(round((b + 1) * band_h)) if b < num_bands - 1 else h
        if b % 2 == 0:
            # Even band: Ground-Truth Google Street View / Satellite (with subtle 15% 3D blend at seam)
            out_np[y0:y1, :, :] = real_np[y0:y1, :, :]
        else:
            # Odd band: Blender 3D Render
            out_np[y0:y1, :, :] = rend_np[y0:y1, :, :]

    out_img = Image.fromarray(out_np)
    draw = ImageDraw.Draw(out_img)
    font_sm = load_font(12, bold=True)

    default_labels = [
        "H1: Sky / Upper Crown",
        "H2: Roofline & Towers",
        "H3: Upper Facade Cornice",
        "H4: Mid-Facade Fenestration",
        "H5: Lower Bays / Arches",
        "H6: Ground Plinth / Canopy",
        "H7: Streetscape / Quay Edge",
        "H8: Roadbed / Water Basin",
    ]
    labels = band_labels or default_labels

    for b in range(num_bands):
        y0 = int(round(b * band_h))
        y1 = int(round((b + 1) * band_h)) if b < num_bands - 1 else h
        is_real = (b % 2 == 0)
        tag = "REAL" if is_real else "3D"
        tag_bg = (16, 124, 65) if is_real else (0, 112, 192)
        border_col = (80, 255, 150) if is_real else (80, 210, 255)

        # Draw seam line
        if b > 0:
            draw.line([(0, y0), (w, y0)], fill=(255, 230, 60), width=2)

        # Draw left indicator bar + badge
        draw.rectangle([0, y0 + 1, 6, y1 - 1], fill=border_col)
        lbl = labels[b] if b < len(labels) else f"H{b+1}"
        badge_text = f" {tag} | {lbl} "
        bbox = draw.textbbox((0, 0), badge_text, font=font_sm)
        bw = bbox[2] - bbox[0] + 6
        bh = bbox[3] - bbox[1] + 4
        draw.rectangle([10, y0 + 4, 10 + bw, y0 + 4 + bh], fill=tag_bg, outline=border_col)
        draw.text((13, y0 + 5), badge_text, fill=(255, 255, 255), font=font_sm)

    return out_img


def build_vertical_and_edge_overlay_bands(
    real_img: Image.Image,
    render_img: Image.Image,
    num_bands: int = 8,
) -> tuple[Image.Image, dict]:
    """
    Create interleaved vertical comparison strips (testing horizontal alignment of
    rooflines, cornices, window rows, and shorelines across vertical strip seams)
    combined with Sobel edge-contour alignment overlay (Green = Real, Magenta = 3D).
    Also computes quantitative band-by-band RGB & Edge alignment metrics.
    """
    w, h = real_img.size
    real_np = np.array(real_img.convert("RGB"))
    rend_np = np.array(render_img.convert("RGB"))

    edges_real = compute_sobel_edges(real_np)
    edges_rend = compute_sobel_edges(rend_np)

    out_np = np.zeros_like(real_np)
    band_w = w / num_bands

    for b in range(num_bands):
        x0 = int(round(b * band_w))
        x1 = int(round((b + 1) * band_w)) if b < num_bands - 1 else w
        if b % 2 == 0:
            # Even vertical strip: Real image with superimposed 3D Magenta edges
            slice_rgb = real_np[:, x0:x1, :].astype(np.float32)
            e_3d = edges_rend[:, x0:x1] > 0.35
            slice_rgb[e_3d, 0] = np.clip(slice_rgb[e_3d, 0] * 0.3 + 255 * 0.7, 0, 255)
            slice_rgb[e_3d, 1] = slice_rgb[e_3d, 1] * 0.3
            slice_rgb[e_3d, 2] = np.clip(slice_rgb[e_3d, 2] * 0.3 + 255 * 0.7, 0, 255)
            out_np[:, x0:x1, :] = slice_rgb.astype(np.uint8)
        else:
            # Odd vertical strip: 3D render with superimposed Real Green edges
            slice_rgb = rend_np[:, x0:x1, :].astype(np.float32)
            e_gt = edges_real[:, x0:x1] > 0.35
            slice_rgb[e_gt, 0] = slice_rgb[e_gt, 0] * 0.3
            slice_rgb[e_gt, 1] = np.clip(slice_rgb[e_gt, 1] * 0.3 + 255 * 0.7, 0, 255)
            slice_rgb[e_gt, 2] = slice_rgb[e_gt, 2] * 0.3
            out_np[:, x0:x1, :] = slice_rgb.astype(np.uint8)

    out_img = Image.fromarray(out_np)
    draw = ImageDraw.Draw(out_img)
    font_sm = load_font(12, bold=True)

    for b in range(num_bands):
        x0 = int(round(b * band_w))
        x1 = int(round((b + 1) * band_w)) if b < num_bands - 1 else w
        is_real = (b % 2 == 0)
        tag = f"V{b+1}:REAL" if is_real else f"V{b+1}:3D"
        tag_bg = (16, 124, 65) if is_real else (0, 112, 192)
        border_col = (80, 255, 150) if is_real else (80, 210, 255)

        if b > 0:
            draw.line([(x0, 0), (x0, h)], fill=(255, 230, 60), width=2)

        draw.rectangle([x0 + 1, 0, x1 - 1, 6], fill=border_col)
        draw.rectangle([x0 + 4, 10, min(x1 - 2, x0 + 68), 28], fill=tag_bg, outline=border_col)
        draw.text((x0 + 7, 12), tag, fill=(255, 255, 255), font=font_sm)

    # Also draw horizontal guide lines at 25%, 50%, 75% to check roofline/horizon continuity
    for frac, lbl in [(0.25, "25% Roof/Sky"), (0.50, "50% Horizon/Mid"), (0.75, "75% Ground/Water")]:
        yy = int(round(h * frac))
        draw.line([(0, yy), (w, yy)], fill=(255, 255, 255), width=1)

    # Compute quantitative metrics per horizontal band
    band_metrics = []
    band_h = h / num_bands
    for b in range(num_bands):
        y0 = int(round(b * band_h))
        y1 = int(round((b + 1) * band_h)) if b < num_bands - 1 else h
        r_slice = real_np[y0:y1].astype(np.float32)
        d_slice = rend_np[y0:y1].astype(np.float32)
        l1_diff = float(np.mean(np.abs(r_slice - d_slice)) / 255.0)
        edge_r = float(np.mean(edges_real[y0:y1] > 0.25))
        edge_d = float(np.mean(edges_rend[y0:y1] > 0.25))
        edge_ratio = min(edge_d / max(edge_r, 0.01), 2.0)
        band_metrics.append({
            "band": f"H{b+1}",
            "y_range_px": [y0, y1],
            "color_similarity_pct": round((1.0 - l1_diff) * 100.0, 1),
            "real_edge_density_pct": round(edge_r * 100.0, 2),
            "render_edge_density_pct": round(edge_d * 100.0, 2),
            "detail_density_ratio": round(edge_ratio, 2),
        })

    overall_color_sim = round(float(np.mean([m["color_similarity_pct"] for m in band_metrics])), 1)
    overall_detail_ratio = round(float(np.mean([m["detail_density_ratio"] for m in band_metrics])), 2)

    return out_img, {
        "overall_color_similarity_pct": overall_color_sim,
        "overall_detail_density_ratio": overall_detail_ratio,
        "horizontal_bands": band_metrics,
    }


def add_reference_grid(img: Image.Image, title_badge: str, badge_color: tuple[int, int, int]) -> Image.Image:
    """Add subtle 8x8 proportional alignment grid and corner badge to an image."""
    out = img.convert("RGB").copy()
    w, h = out.size
    draw = ImageDraw.Draw(out)
    font_md = load_font(14, bold=True)
    font_sm = load_font(11, bold=False)

    # Draw 8-band grid lines
    for i in range(1, 8):
        y = int(round(h * i / 8.0))
        x = int(round(w * i / 8.0))
        col = (255, 220, 80) if i == 4 else (180, 180, 180)
        draw.line([(0, y), (w, y)], fill=col, width=1)
        draw.line([(x, 0), (x, h)], fill=col, width=1)
        draw.text((4, y - 14), f"H{i}", fill=(255, 240, 150), font=font_sm)

    # Top title banner
    draw.rectangle([8, 8, min(w - 8, 460), 34], fill=badge_color, outline=(255, 255, 255))
    draw.text((14, 12), title_badge, fill=(255, 255, 255), font=font_md)
    return out


def create_four_panel_critique_board(
    block_id: str,
    view_label: str,
    iteration: int,
    real_path: Path,
    render_path: Path,
    out_path: Path,
    is_satellite: bool = False,
) -> dict:
    """
    Assemble the 4-Panel Adversarial Overlay-Band Critique Board (1360 x 1440):
      - Top-Left: Real Google Street View / Satellite (with 8x8 alignment grid)
      - Top-Right: Blender 3D Camera-Matched Render (with 8x8 alignment grid)
      - Bottom-Left: Horizontal Overlay Bands (8 interleaved comparison strips)
      - Bottom-Right: Vertical Overlay Bands + Edge-Contour Alignment (Real Green vs 3D Magenta edges)
    """
    panel_size = 640
    real_img = Image.open(real_path).convert("RGB").resize((panel_size, panel_size), Image.Resampling.LANCZOS)
    render_img = Image.open(render_path).convert("RGB").resize((panel_size, panel_size), Image.Resampling.LANCZOS)

    sat_labels = [
        "H1: North Edge Footprints / Streets",
        "H2: Upper-North Block Roofs & Trees",
        "H3: Mid-North Roofs / Quays / Lawns",
        "H4: Center Axis Landmarks & Plazas",
        "H5: Center-South Piers / Canals",
        "H6: Mid-South Waterfront / Basins",
        "H7: Lower-South Quays / Vessels",
        "H8: South Channel / St. Lawrence River",
    ]
    h_bands_img = build_horizontal_overlay_bands(
        real_img, render_img, num_bands=8, band_labels=sat_labels if is_satellite else None
    )
    v_bands_img, metrics = build_vertical_and_edge_overlay_bands(real_img, render_img, num_bands=8)

    p1 = add_reference_grid(
        real_img,
        f"1. GROUND TRUTH ({'GOOGLE SATELLITE' if is_satellite else 'GOOGLE STREET VIEW'}): {view_label}",
        (16, 108, 58),
    )
    p2 = add_reference_grid(
        render_img,
        f"2. BLENDER 3D RENDER (ITER {iteration}): {view_label}",
        (0, 96, 168),
    )

    # Add header bars to P3 and P4
    draw_p3 = ImageDraw.Draw(h_bands_img)
    font_md = load_font(13, bold=True)
    draw_p3.rectangle([180, 6, 634, 30], fill=(40, 40, 48), outline=(255, 230, 60))
    draw_p3.text((186, 9), "3. HORIZONTAL OVERLAY BANDS (REAL vs 3D STRIPS)", fill=(255, 240, 120), font=font_md)

    draw_p4 = ImageDraw.Draw(v_bands_img)
    draw_p4.rectangle([8, panel_size - 32, 632, panel_size - 6], fill=(40, 40, 48), outline=(255, 230, 60))
    draw_p4.text(
        (14, panel_size - 28),
        "4. VERTICAL STRIPS + EDGE OVERLAY (Green=Real Edges, Magenta=3D Edges)",
        fill=(255, 240, 120),
        font=font_md,
    )

    board_w = panel_size * 2 + 48
    board_h = panel_size * 2 + 120
    board = Image.new("RGB", (board_w, board_h), (20, 22, 28))
    bdraw = ImageDraw.Draw(board)
    font_title = load_font(18, bold=True)
    font_sub = load_font(13, bold=False)

    # Header
    bdraw.rectangle([0, 0, board_w, 76], fill=(30, 34, 44))
    bdraw.text(
        (16, 12),
        f"ADVERSARIAL CRITIQUE OVERLAY BANDS — {block_id} | {view_label} (Iteration {iteration})",
        fill=(255, 255, 255),
        font=font_title,
    )
    bdraw.text(
        (16, 42),
        f"Method: Gemini 4 Argon Comparison Strips (OYp5j2RihPE) | Color Sim: {metrics['overall_color_similarity_pct']}% | "
        f"Detail Edge Ratio (3D/Real): {metrics['overall_detail_density_ratio']}x",
        fill=(180, 220, 255),
        font=font_sub,
    )

    # Paste 4 panels
    board.paste(p1, (16, 88))
    board.paste(p2, (panel_size + 32, 88))
    board.paste(h_bands_img, (16, panel_size + 104))
    board.paste(v_bands_img, (panel_size + 32, panel_size + 104))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(out_path, format="PNG")
    metrics["view_label"] = view_label
    metrics["critique_board_path"] = str(out_path)
    return metrics


def generate_block_overlay_bands(block_id: str, iteration: int = 1) -> dict:
    block_dir = REPO_ROOT / "data" / "blocks" / block_id
    sv_dir = block_dir / "streetview"
    renders_dir = block_dir / "renders"
    bands_dir = block_dir / "overlay_bands"
    bands_dir.mkdir(parents=True, exist_ok=True)

    dossier_path = block_dir / "dossier.json"
    dossier = json.loads(dossier_path.read_text(encoding="utf-8")) if dossier_path.exists() else {}

    cameras = dossier.get("streetview_cameras", [])
    results = []
    board_images = []

    # 1. Process all 4 Street View cameras
    for cam in cameras:
        label = cam.get("label")
        if not label:
            continue
        real_jpg = sv_dir / f"{label}.jpg"
        if not real_jpg.exists():
            continue

        # Find matching render (iter<N>_<label>.png or <label>.png)
        candidates = [
            renders_dir / f"iter{iteration}_{label}.png",
            renders_dir / f"{label}.png",
            renders_dir / f"iter1_{label}.png",
        ]
        render_png = next((p for p in candidates if p.exists()), None)
        if render_png is None:
            print(f"[WARN] Missing render for {block_id}/{label} (checked {candidates[0].name})")
            continue

        out_board = bands_dir / f"iter{iteration}_{label}_overlay_critique.png"
        m = create_four_panel_critique_board(
            block_id=block_id,
            view_label=label,
            iteration=iteration,
            real_path=real_jpg,
            render_path=render_png,
            out_path=out_board,
            is_satellite=False,
        )
        results.append(m)
        board_images.append(Image.open(out_board).convert("RGB"))
        print(f"  [OK] Generated Street View Overlay Bands: {out_board.relative_to(REPO_ROOT)}")

    # 2. Process Top-Down Google Maps Satellite vs Blender Top-Down / Overview
    sat_png = sv_dir / "satellite_topdown.png"
    sat_render_candidates = [
        renders_dir / f"iter{iteration}_topdown_ortho.png",
        renders_dir / "topdown_ortho.png",
        renders_dir / "iter1_topdown_ortho.png",
        REPO_ROOT / "output" / "renders" / f"{block_id}_snapshot.png",
    ]
    sat_render = next((p for p in sat_render_candidates if p.exists()), None)
    if sat_png.exists() and sat_render is not None:
        out_sat_board = bands_dir / f"iter{iteration}_satellite_topdown_overlay_critique.png"
        m_sat = create_four_panel_critique_board(
            block_id=block_id,
            view_label="Google_Maps_Satellite_TopDown",
            iteration=iteration,
            real_path=sat_png,
            render_path=sat_render,
            out_path=out_sat_board,
            is_satellite=True,
        )
        results.append(m_sat)
        board_images.append(Image.open(out_sat_board).convert("RGB"))
        print(f"  [OK] Generated Satellite Top-Down Overlay Bands: {out_sat_board.relative_to(REPO_ROOT)}")

    # 3. Create Master Summary Strip Sheet combining all viewpoints for quick multi-angle inspection
    master_sheet_path = bands_dir / f"iter{iteration}_{block_id}_master_overlay_sheet.png"
    if board_images:
        thumb_w = 680
        thumb_h = 720
        cols = min(len(board_images), 3)
        rows = (len(board_images) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * thumb_w + 24, rows * thumb_h + 70), (16, 18, 24))
        sdraw = ImageDraw.Draw(sheet)
        ft = load_font(20, bold=True)
        sdraw.text(
            (16, 18),
            f"{block_id} — ITERATION {iteration} MASTER ADVERSARIAL OVERLAY-BAND SHEET ({len(board_images)} VIEWS)",
            fill=(255, 255, 255),
            font=ft,
        )
        for idx, bimg in enumerate(board_images):
            r = idx // cols
            c = idx % cols
            thumb = bimg.resize((thumb_w - 12, thumb_h - 12), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (12 + c * thumb_w, 60 + r * thumb_h))
        sheet.save(master_sheet_path, format="PNG")
        print(f"  [OK] Saved Master Overlay Sheet: {master_sheet_path.relative_to(REPO_ROOT)}")

    # 4. Create 4-Angle 3D Isometric Diagnostic Quad Sheet (SE, SW, NW, NE)
    quad_sheet_path = bands_dir / f"iter{iteration}_{block_id}_3d_diagnostic_quad.png"
    diag_labels = ["SE_Iso", "SW_Iso", "NW_Iso", "NE_Iso"]
    diag_imgs = []
    for dlabel in diag_labels:
        dp = renders_dir / f"iter{iteration}_diag_{dlabel}.png"
        if dp.exists():
            diag_imgs.append((dlabel, Image.open(dp).convert("RGB")))
    if diag_imgs:
        qw, qh = 640, 480
        qsheet = Image.new("RGB", (qw * 2 + 36, qh * 2 + 86), (16, 18, 24))
        qdraw = ImageDraw.Draw(qsheet)
        ft_title = load_font(18, bold=True)
        ft_sub = load_font(14, bold=True)
        forensics_p = bands_dir / f"iter{iteration}_geometry_forensics.json"
        f_info = ""
        if forensics_p.exists():
            try:
                fd = json.loads(forensics_p.read_text(encoding="utf-8"))
                f_info = f" | Verts: {fd.get('total_mesh_vertices',0):,} | Faces: {fd.get('total_mesh_faces',0):,} | Mats: {fd.get('distinct_materials_count',0)} | WindowlessTallBldgs: {len(fd.get('windowless_tall_buildings',[]))}"
            except Exception:
                pass
        qdraw.text((16, 16), f"{block_id} (ITER {iteration}) — 4-ANGLE 3D ISOMETRIC GEOMETRY DIAGNOSTIC{f_info}", fill=(255, 230, 120), font=ft_title)
        for idx, (dlabel, dimg) in enumerate(diag_imgs):
            r = idx // 2
            c = idx % 2
            x0 = 12 + c * (qw + 12)
            y0 = 54 + r * (qh + 12)
            qsheet.paste(dimg.resize((qw, qh), Image.Resampling.LANCZOS), (x0, y0))
            qdraw.rectangle([x0 + 8, y0 + 8, x0 + 210, y0 + 34], fill=(0, 0, 0))
            qdraw.text((x0 + 14, y0 + 12), f"3D VIEW: {dlabel}", fill=(120, 255, 160), font=ft_sub)
        qsheet.save(quad_sheet_path, format="PNG")
        print(f"  [OK] Saved 4-Angle 3D Diagnostic Quad Sheet: {quad_sheet_path.relative_to(REPO_ROOT)}")

    summary = {
        "block_id": block_id,
        "iteration": iteration,
        "master_overlay_sheet": str(master_sheet_path) if board_images else None,
        "diagnostic_quad_sheet": str(quad_sheet_path) if diag_imgs else None,
        "views": results,
    }
    report_json = bands_dir / f"iter{iteration}_overlay_metrics.json"
    report_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Generate Overlay Band comparison strips for Adversarial Critique.")
    parser.add_argument("--block", required=True, help="Block ID (e.g. MTL-VM-0021) or comma-separated list")
    parser.add_argument("--iter", type=int, default=1, help="Iteration number (default: 1)")
    args = parser.parse_args()

    blocks = [b.strip() for b in args.block.split(",") if b.strip()]
    for b in blocks:
        print(f"=== Generating Overlay Bands for {b} (Iteration {args.iter}) ===")
        generate_block_overlay_bands(b, args.iter)


if __name__ == "__main__":
    main()
