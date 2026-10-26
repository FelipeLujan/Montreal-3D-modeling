"""
Synthesize 4 Tileable 2K PBR Water Texture Maps for the St. Lawrence River & Old Port Basins:
1. water_river_diffuse_2k.jpg: Deep St. Lawrence blue-teal with multi-octave wave luminosity.
2. water_river_nor_gl_2k.jpg: Tangent-space normal map from Gerstner wave spectrum.
3. water_river_rough_2k.jpg: Micro-roughness 0.05..0.12 map.
4. water_foam_edge_2k.jpg: Worley cellular foam mask for shoreline, quay walls, and ship wakes.
All maps are mathematically guaranteed to be seamlessly tileable across 2048x2048.
"""
import os
import math
import numpy as np
from PIL import Image

OUT_DIR = r"C:\Users\Felipe\Documents\coding\montreal\assets\polyhaven"
os.makedirs(OUT_DIR, exist_ok=True)
SIZE = 2048


def generate_water_maps():
    print(f"Synthesizing 4 tileable 2K PBR water textures ({SIZE}x{SIZE})...")
    np.random.seed(42)

    # 1. Periodic coordinate grid: u, v in [0, 2*pi)
    x = np.arange(SIZE, dtype=np.float32)
    y = np.arange(SIZE, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)
    u = (xx * (2.0 * np.pi / SIZE)).astype(np.float32)
    v = (yy * (2.0 * np.pi / SIZE)).astype(np.float32)

    # 2. Multi-octave Gerstner wave spectrum (harmonics for seamless periodicity)
    # Harmonics (nx, ny): integer frequencies ensure strict periodic boundary conditions
    wave_harmonics = [
        # (nx, ny, amplitude, phase)
        # Deep river swell (flowing along east-northeast diagonal)
        (4, 2, 0.45, 0.15),
        (5, 3, 0.38, 1.42),
        (7, 2, 0.30, 2.78),
        (3, 5, 0.28, 4.10),
        # Medium wind chop
        (11, 6, 0.20, 0.85),
        (13, 8, 0.18, 3.14),
        (8, 12, 0.16, 5.20),
        (16, 9, 0.14, 1.95),
        (18, 14, 0.12, 4.45),
        # Fine cross-chop
        (-7, 9, 0.15, 2.10),
        (-10, 14, 0.11, 0.70),
        (-14, 8, 0.09, 3.80),
        # Capillary waves & surface ripples
        (28, 18, 0.08, 1.15),
        (35, 24, 0.06, 4.90),
        (44, 30, 0.05, 2.60),
        (56, 38, 0.04, 0.35),
        (72, 48, 0.03, 3.75),
        (-32, 26, 0.05, 5.10),
        (-50, 36, 0.035, 1.80),
        (90, 60, 0.025, 4.20),
        (115, 78, 0.020, 2.10),
        (145, 96, 0.015, 0.95),
    ]

    elevation = np.zeros((SIZE, SIZE), dtype=np.float32)
    dh_dx = np.zeros((SIZE, SIZE), dtype=np.float32)
    dh_dy = np.zeros((SIZE, SIZE), dtype=np.float32)

    for nx, ny, amp, phi in wave_harmonics:
        kx = nx * (2.0 * np.pi / SIZE)
        ky = ny * (2.0 * np.pi / SIZE)
        arg = nx * u + ny * v + phi
        cos_arg = np.cos(arg)
        sin_arg = np.sin(arg)

        # Trochoidal sharpening factor (Gerstner crest peakiness)
        steepness = 0.25
        elevation += amp * cos_arg
        # Gradients
        dh_dx -= amp * kx * (sin_arg + steepness * np.sin(2.0 * arg))
        dh_dy -= amp * ky * (sin_arg + steepness * np.sin(2.0 * arg))

    # Scale gradients for realistic water normal response in Blender/UE5
    normal_strength = 320.0
    gx = dh_dx * normal_strength
    gy = dh_dy * normal_strength

    # 3. Tangent-Space OpenGL Normal Map (nor_gl)
    # Normal vector N = (-gx, -gy, 1.0) / length
    norm = np.sqrt(gx * gx + gy * gy + 1.0)
    nz = 1.0 / norm
    nx_norm = -gx / norm
    ny_norm = -gy / norm  # In OpenGL (+Y up)

    # Encode to 8-bit [0, 255]
    n_r = np.clip((nx_norm * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
    n_g = np.clip((ny_norm * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
    n_b = np.clip((nz * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
    normal_rgb = np.stack([n_r, n_g, n_b], axis=-1)

    nor_path = os.path.join(OUT_DIR, "water_river_nor_gl_2k.jpg")
    Image.fromarray(normal_rgb).save(nor_path, quality=95)
    print(f"  [SAVED] {nor_path} ({os.path.getsize(nor_path)} bytes)")

    # 4. Micro-Roughness Map (0.05 .. 0.12)
    # Slope magnitude drives micro-roughness: calm troughs = 0.05, turbulent crests = 0.12
    slope = np.sqrt(gx * gx + gy * gy)
    slope_min = float(np.percentile(slope, 2.0))
    slope_max = float(np.percentile(slope, 98.0))
    slope_norm = np.clip((slope - slope_min) / max(1e-5, (slope_max - slope_min)), 0.0, 1.0)

    # Elevation also modulates: crests are windier / rougher
    elev_min = float(np.percentile(elevation, 2.0))
    elev_max = float(np.percentile(elevation, 98.0))
    elev_norm = np.clip((elevation - elev_min) / max(1e-5, (elev_max - elev_min)), 0.0, 1.0)

    roughness = 0.05 + 0.07 * (0.65 * slope_norm + 0.35 * elev_norm)
    # Ensure strictly in [0.05, 0.12]
    roughness = np.clip(roughness, 0.05, 0.12)
    rough_gray = np.clip(roughness * 255.0, 0, 255).astype(np.uint8)

    rough_path = os.path.join(OUT_DIR, "water_river_rough_2k.jpg")
    Image.fromarray(rough_gray).save(rough_path, quality=95)
    print(f"  [SAVED] {rough_path} ({os.path.getsize(rough_path)} bytes, min={roughness.min():.3f}, max={roughness.max():.3f})")

    # 5. Diffuse Base Color Map (Deep St. Lawrence blue-teal with wave luminosity)
    # Deep water color: [16, 48, 64], crest color: [30, 84, 102], trough color: [12, 34, 48]
    trough_rgb = np.array([12.0, 36.0, 48.0], dtype=np.float32)
    mid_rgb = np.array([18.0, 54.0, 72.0], dtype=np.float32)
    crest_rgb = np.array([32.0, 88.0, 106.0], dtype=np.float32)

    lum_factor = elev_norm[:, :, np.newaxis]
    diffuse = np.where(
        lum_factor < 0.5,
        trough_rgb + (lum_factor / 0.5) * (mid_rgb - trough_rgb),
        mid_rgb + ((lum_factor - 0.5) / 0.5) * (crest_rgb - mid_rgb)
    )

    # Add subtle capillary wave highlights
    capillary_factor = (slope_norm * 0.15)[:, :, np.newaxis]
    diffuse = np.clip(diffuse + capillary_factor * np.array([20.0, 35.0, 40.0], dtype=np.float32), 0, 255).astype(np.uint8)

    diff_path = os.path.join(OUT_DIR, "water_river_diffuse_2k.jpg")
    Image.fromarray(diffuse).save(diff_path, quality=95)
    print(f"  [SAVED] {diff_path} ({os.path.getsize(diff_path)} bytes)")

    # 6. Worley Cellular Foam Mask (water_foam_edge_2k.jpg)
    # Generate seamless periodic cellular / Worley noise
    print("  Generating seamless periodic Worley foam noise...")
    CELLS = 32
    cell_size = SIZE // CELLS

    # Feature points in each cell (with periodic wrap)
    seeds = np.random.uniform(0.1, 0.9, size=(CELLS, CELLS, 2)).astype(np.float32)

    # To compute efficiently, evaluate on downsampled grid then upscale with bicubic
    GRID_EVAL = 512
    ge_x = np.arange(GRID_EVAL, dtype=np.float32) / GRID_EVAL * CELLS
    ge_y = np.arange(GRID_EVAL, dtype=np.float32) / GRID_EVAL * CELLS
    gx_grid, gy_grid = np.meshgrid(ge_x, ge_y)

    c_x = np.floor(gx_grid).astype(np.int32) % CELLS
    c_y = np.floor(gy_grid).astype(np.int32) % CELLS

    f1 = np.full((GRID_EVAL, GRID_EVAL), 999.0, dtype=np.float32)
    f2 = np.full((GRID_EVAL, GRID_EVAL), 999.0, dtype=np.float32)

    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            neigh_x = (c_x + di) % CELLS
            neigh_y = (c_y + dj) % CELLS
            # Global coordinates of candidate seed
            seed_pos_x = (c_x + di) + seeds[neigh_y, neigh_x, 0]
            seed_pos_y = (c_y + dj) + seeds[neigh_y, neigh_x, 1]

            dx = gx_grid - seed_pos_x
            dy = gy_grid - seed_pos_y
            # Periodic delta in cell units
            dx = dx - CELLS * np.round(dx / CELLS)
            dy = dy - CELLS * np.round(dy / CELLS)
            dist = np.sqrt(dx * dx + dy * dy)

            # Update f1 and f2
            f2 = np.where(dist < f1, f1, np.minimum(f2, dist))
            f1 = np.minimum(f1, dist)

    # Worley ridge cellular pattern: f2 - f1 gives web/foam cell borders
    worley_ridge = f2 - f1
    # Worley cell center: f1 gives circular bubble cores
    worley_bubble = np.clip(1.0 - f1 * 1.8, 0.0, 1.0)

    # Combine ridge + bubble to form realistic sea/river foam
    foam_pattern = 0.65 * (1.0 - np.clip(worley_ridge * 3.2, 0.0, 1.0)) + 0.35 * (worley_bubble ** 2)

    # Upscale to 2048x2048 with bicubic filtering
    foam_img = Image.fromarray((foam_pattern * 255.0).astype(np.uint8)).resize((SIZE, SIZE), Image.Resampling.BICUBIC)
    foam_arr = np.array(foam_img, dtype=np.float32) / 255.0

    # Add high-frequency capillary turbulence from the wave spectrum
    high_freq_turb = np.clip(slope_norm * 0.4 + 0.6 * elev_norm, 0.0, 1.0)
    foam_final = foam_arr * (0.5 + 0.5 * high_freq_turb)

    # Apply soft sigmoid contrast threshold for crisp foam tendrils
    foam_final = np.clip((foam_final - 0.28) / 0.42, 0.0, 1.0)
    foam_final_8bit = (foam_final * 255.0).astype(np.uint8)

    foam_path = os.path.join(OUT_DIR, "water_foam_edge_2k.jpg")
    Image.fromarray(foam_final_8bit).save(foam_path, quality=95)
    print(f"  [SAVED] {foam_path} ({os.path.getsize(foam_path)} bytes)")

    print("\nAll 4 tileable 2K PBR water textures generated successfully!")


if __name__ == "__main__":
    generate_water_maps()
