"""
Download 11 Real Poly Haven 2K PBR Texture Sets and 10 Real Poly Haven 3D Models (.blend + 2K textures)
into assets/polyhaven/ and copy textures into output/textures/.
Also overwrites grass_park_*_2k.jpg with real Poly Haven leafy_grass 2K photogrammetry maps.
"""
import os
import json
import shutil
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
MODELS_DIR = os.path.join(POLYHAVEN_DIR, "models")
OUTPUT_TEX_DIR = os.path.join(BASE_DIR, "output", "textures")

os.makedirs(POLYHAVEN_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_TEX_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Montreal3DTwin/2.0"}

TEXTURE_ASSETS = [
    "leafy_grass",           # 1. Lush photogrammetry park grass lawn
    "forrest_ground_01",     # 2. Natural woodland/park ground
    "grass_path_2",          # 3. Park grass path transition
    "concrete_pavers",       # 4. Jointed sidewalk concrete pavers
    "concrete_pavement_02",  # 5. Urban concrete sidewalk & plaza slabs
    "stone_pavers",          # 6. Cut granite plaza & promenade stone pavers
    "herringbone_pavement",  # 7. Herringbone brick/stone pedestrian promenade pavers
    "gravel_concrete_02",    # 8. Crushed granite / gravel park walkway surface
    "clean_asphalt",         # 9. Realistic medium-charcoal urban street asphalt
    "worn_asphalt",          # 10. Weathered urban street asphalt with aggregate detail
    "red_brick_pavers",      # 11. Heritage brick courtyard & sidewalk paving
]

MODEL_ASSETS = [
    "tree_small_02",         # 1. Deciduous street/park tree
    "fir_tree_01",           # 2. Conifer evergreen park tree
    "pine_tree_01",          # 3. Tall pine park tree
    "shrub_01",              # 4. Green park bush/shrub
    "shrub_02",              # 5. Landscaping hedge shrub
    "grass_medium_01",       # 6. 3D grass clump for park beds
    "painted_wooden_bench",  # 7. Classic park bench
    "planter_box_01",        # 8. Sidewalk/plaza planter box
    "fire_hydrant",          # 9. Street curb fire hydrant
    "rock_moss_set_01",      # 10. Natural park/shoreline boulders
]


def download_file(url: str, dest_path: str, force: bool = False, retries: int = 3) -> bool:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if not force and os.path.exists(dest_path) and os.path.getsize(dest_path) > 4096:
        return True

    tmp_path = dest_path + ".tmp"
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=45) as resp, open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1024:
                os.replace(tmp_path, dest_path)
                return True
        except Exception as e:
            print(f"  [RETRY {attempt}/{retries}] Failed downloading {url}: {e}")
            time.sleep(1.0)
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
    return False


def _extract_map_entry(data: dict, candidate_keys: list, res: str = "2k"):
    for key in candidate_keys:
        if key in data and res in data[key]:
            fmt_dict = data[key][res]
            if "jpg" in fmt_dict:
                return fmt_dict["jpg"]["url"], "jpg"
            if "png" in fmt_dict:
                return fmt_dict["png"]["url"], "png"
    return None, None


def _ensure_jpg(src_path: str, dest_jpg_path: str):
    if src_path.lower().endswith(".png"):
        try:
            from PIL import Image
            with Image.open(src_path) as im:
                rgb = im.convert("RGB")
                rgb.save(dest_jpg_path, "JPEG", quality=95)
            os.remove(src_path)
            return True
        except ImportError:
            shutil.move(src_path, dest_jpg_path)
            return True
    else:
        if os.path.abspath(src_path) != os.path.abspath(dest_jpg_path):
            shutil.copy2(src_path, dest_jpg_path)
        return True


def fetch_texture_set(asset_id: str) -> dict:
    api_url = f"https://api.polyhaven.com/files/{asset_id}"
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    diff_url, diff_fmt = _extract_map_entry(data, ["Diffuse", "diff", "col"], "2k")
    rough_url, rough_fmt = _extract_map_entry(data, ["Rough", "rough", "Roughness"], "2k")
    nor_url, nor_fmt = _extract_map_entry(data, ["nor_gl", "nor_dx", "Bump"], "2k")

    if not (diff_url and rough_url and nor_url):
        raise RuntimeError(f"Missing 2k maps for {asset_id}: diff={bool(diff_url)}, rough={bool(rough_url)}, nor={bool(nor_url)}")

    # Target standard paths in assets/polyhaven/
    dest_diff = os.path.join(POLYHAVEN_DIR, f"{asset_id}_Diffuse_2k.jpg")
    dest_roughness = os.path.join(POLYHAVEN_DIR, f"{asset_id}_Roughness_2k.jpg")
    dest_rough = os.path.join(POLYHAVEN_DIR, f"{asset_id}_Rough_2k.jpg")
    dest_nor = os.path.join(POLYHAVEN_DIR, f"{asset_id}_nor_gl_2k.jpg")

    # Download (with png->jpg conversion if needed)
    raw_diff = dest_diff if diff_fmt == "jpg" else dest_diff + ".png"
    raw_rough = dest_roughness if rough_fmt == "jpg" else dest_roughness + ".png"
    raw_nor = dest_nor if nor_fmt == "jpg" else dest_nor + ".png"

    ok1 = download_file(diff_url, raw_diff)
    ok2 = download_file(rough_url, raw_rough)
    ok3 = download_file(nor_url, raw_nor)
    if not (ok1 and ok2 and ok3):
        raise RuntimeError(f"Download failed for {asset_id}")

    _ensure_jpg(raw_diff, dest_diff)
    _ensure_jpg(raw_rough, dest_roughness)
    _ensure_jpg(raw_nor, dest_nor)

    # Create standard aliases in assets/polyhaven/ for compatibility with _find_polyhaven_map
    shutil.copy2(dest_roughness, dest_rough)
    alias_diff_lower = os.path.join(POLYHAVEN_DIR, f"{asset_id}_diff_2k.jpg")
    alias_rough_lower = os.path.join(POLYHAVEN_DIR, f"{asset_id}_rough_2k.jpg")
    shutil.copy2(dest_diff, alias_diff_lower)
    shutil.copy2(dest_roughness, alias_rough_lower)

    # Copy all variants to output/textures/
    for p in [dest_diff, dest_roughness, dest_rough, dest_nor, alias_diff_lower, alias_rough_lower]:
        shutil.copy2(p, os.path.join(OUTPUT_TEX_DIR, os.path.basename(p)))

    return {
        "asset_id": asset_id,
        "diffuse_kb": os.path.getsize(dest_diff) // 1024,
        "roughness_kb": os.path.getsize(dest_roughness) // 1024,
        "nor_gl_kb": os.path.getsize(dest_nor) // 1024,
    }


def fetch_model_2k(model_id: str) -> dict:
    api_url = f"https://api.polyhaven.com/files/{model_id}"
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    blend_section = data.get("blend", {})
    res = "2k" if "2k" in blend_section else ("1k" if "1k" in blend_section else next(iter(blend_section.keys()), None))
    if not res:
        raise RuntimeError(f"No .blend section for {model_id}")

    blend_info = blend_section[res].get("blend", {})
    blend_url = blend_info.get("url")
    if not blend_url:
        raise RuntimeError(f"No .blend URL for {model_id}")

    model_dir = os.path.join(MODELS_DIR, model_id)
    os.makedirs(model_dir, exist_ok=True)
    blend_dest = os.path.join(model_dir, f"{model_id}.blend")

    # Force download of 2k .blend so any earlier 1k .blend is upgraded to 2k
    download_file(blend_url, blend_dest, force=True)

    include_map = blend_info.get("include", {})
    tex_files = []
    for rel_path, file_meta in include_map.items():
        t_url = file_meta.get("url")
        if t_url:
            t_dest = os.path.join(model_dir, rel_path.replace("/", os.sep))
            download_file(t_url, t_dest, force=False)
            tex_files.append(os.path.basename(t_dest))
            # Also copy model textures to output/textures/ so USD/external resolvers can find them if needed
            shutil.copy2(t_dest, os.path.join(OUTPUT_TEX_DIR, os.path.basename(t_dest)))

    return {
        "model_id": model_id,
        "res": res,
        "blend_kb": os.path.getsize(blend_dest) // 1024,
        "tex_count": len(tex_files),
        "textures": tex_files,
    }


def main():
    print("=" * 72)
    print("STEP 1: Downloading 11 Real Poly Haven 2K PBR Texture Sets")
    print("=" * 72)
    tex_results = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(fetch_texture_set, aid): aid for aid in TEXTURE_ASSETS}
        for fut in as_completed(futs):
            aid = futs[fut]
            res = fut.result()
            tex_results.append(res)
            print(f"  [OK] {aid:24s} | Diff: {res['diffuse_kb']:5d} KB | Rough: {res['roughness_kb']:5d} KB | NorGL: {res['nor_gl_kb']:5d} KB")

    # Overwrite grass_park_*_2k.jpg in both assets/polyhaven/ and output/textures/ with leafy_grass 2K
    leafy_diff = os.path.join(POLYHAVEN_DIR, "leafy_grass_Diffuse_2k.jpg")
    leafy_rough = os.path.join(POLYHAVEN_DIR, "leafy_grass_Roughness_2k.jpg")
    leafy_nor = os.path.join(POLYHAVEN_DIR, "leafy_grass_nor_gl_2k.jpg")

    grass_park_Mapping = [
        (leafy_diff, "grass_park_diffuse_2k.jpg"),
        (leafy_rough, "grass_park_rough_2k.jpg"),
        (leafy_nor, "grass_park_nor_gl_2k.jpg"),
    ]
    for src_f, target_name in grass_park_Mapping:
        for folder in [POLYHAVEN_DIR, OUTPUT_TEX_DIR]:
            dst_f = os.path.join(folder, target_name)
            shutil.copy2(src_f, dst_f)
    print("\n  [OK] Overwrote grass_park_diffuse_2k.jpg, grass_park_rough_2k.jpg, grass_park_nor_gl_2k.jpg")
    print("       in both assets/polyhaven/ and output/textures/ with real Poly Haven leafy_grass 2K!")

    print("\n" + "=" * 72)
    print("STEP 2: Downloading 10 Real Poly Haven 3D Models (.blend + 2K textures)")
    print("=" * 72)
    mod_results = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(fetch_model_2k, mid): mid for mid in MODEL_ASSETS}
        for fut in as_completed(futs):
            mid = futs[fut]
            res = fut.result()
            mod_results.append(res)
            print(f"  [OK] {mid:24s} ({res['res']}) | .blend: {res['blend_kb']:6d} KB | textures ({res['tex_count']}): {', '.join(res['textures'])}")

    print("\nAll Poly Haven 2K Texture Sets and 3D Models successfully downloaded!")


if __name__ == "__main__":
    main()
