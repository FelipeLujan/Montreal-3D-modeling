"""
Download a rich variety of Poly Haven 3D Tree & Street Light models (.blend + textures)
into assets/polyhaven/models/<asset_id>/ and pack them into assets/montreal_kit.blend.
"""
import os
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
MODELS_DIR = os.path.join(BASE_DIR, "assets", "polyhaven", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

TARGET_MODELS = [
    # Tree & Foliage Variety (6 distinct species)
    "jacaranda_tree",
    "pine_tree_01",
    "fir_tree_01",
    "tree_small_02",
    "searsia_burchellii",
    "shrub_01",
    "shrub_02",
    # Street Lights & Urban Furniture (5 distinct models)
    "street_lamp_01",
    "street_lamp_02",
    "Lantern_01",
    "modular_electricity_poles",
    "modular_street_seating",
    "fire_hydrant",
]

HEADERS = {"User-Agent": "Montreal3DTwin/1.0"}


def download_file(url: str, dest: str):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 1024:
        return dest
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def fetch_polyhaven_model(asset_id: str):
    api_url = f"https://api.polyhaven.com/files/{asset_id}"
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))

    blend_section = data.get("blend", {})
    # Prefer 1k or 2k resolution for fast instancing with crisp textures
    res = "1k" if "1k" in blend_section else ("2k" if "2k" in blend_section else next(iter(blend_section.keys()), None))
    if not res:
        return f"[SKIP] {asset_id}: no .blend section"

    blend_info = blend_section[res].get("blend", {})
    blend_url = blend_info.get("url")
    if not blend_url:
        return f"[SKIP] {asset_id}: no .blend url"

    asset_dir = os.path.join(MODELS_DIR, asset_id)
    os.makedirs(asset_dir, exist_ok=True)
    blend_dest = os.path.join(asset_dir, f"{asset_id}.blend")
    download_file(blend_url, blend_dest)

    include_map = blend_info.get("include", {})
    tex_count = 0
    for rel_path, file_meta in include_map.items():
        t_url = file_meta.get("url")
        if t_url:
            t_dest = os.path.join(asset_dir, rel_path.replace("/", os.sep))
            download_file(t_url, t_dest)
            tex_count += 1

    return f"[OK] {asset_id} ({res}): {os.path.getsize(blend_dest)//1024} KB + {tex_count} textures"


def main():
    print(f"Downloading {len(TARGET_MODELS)} Poly Haven 3D Tree & Street Light models...")
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(fetch_polyhaven_model, m): m for m in TARGET_MODELS}
        for fut in as_completed(futs):
            m = futs[fut]
            try:
                print(" ", fut.result())
            except Exception as e:
                print(f"  [ERR] {m}: {e}")


if __name__ == "__main__":
    main()
