"""
Fetch Poly Haven 2K PBR Architectural Facade Textures.
Downloads 12 distinct facade sets (Diffuse, Roughness, nor_gl) into assets/polyhaven/.
"""
import os
import json
import urllib.request
import time

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
OUT_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
os.makedirs(OUT_DIR, exist_ok=True)

TARGET_SETS = [
    "stone_brick_wall_001",
    "medieval_blocks_06",
    "red_sandstone_wall",
    "brick_wall_04",
    "yellow_brick",
    "dark_brick_wall",
    "castle_brick_02_white",
    "concrete_block_wall",
    "stone_block_wall",
    "box_profile_metal_sheet",
    "weathered_planks",
    "stone_tile_wall"
]


def download_file(url: str, dest_path: str, retries: int = 3):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
        print(f"  [EXISTS] {os.path.basename(dest_path)} ({os.path.getsize(dest_path)} bytes)")
        return True

    tmp_path = dest_path + ".tmp"
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1000:
                os.replace(tmp_path, dest_path)
                print(f"  [DOWNLOADED] {os.path.basename(dest_path)} ({os.path.getsize(dest_path)} bytes)")
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


def fetch_all():
    print(f"Fetching {len(TARGET_SETS)} Poly Haven 2K PBR texture sets to {OUT_DIR}...")
    success_count = 0

    for asset_id in TARGET_SETS:
        print(f"\nProcessing asset: {asset_id}")
        api_url = f"https://api.polyhaven.com/files/{asset_id}"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"  ERROR fetching metadata for {asset_id}: {e}")
            continue

        diff_info = data.get("Diffuse", {}).get("2k", {}).get("jpg")
        rough_info = data.get("Rough", {}).get("2k", {}).get("jpg")
        nor_info = data.get("nor_gl", {}).get("2k", {}).get("jpg")

        if not diff_info or not rough_info or not nor_info:
            print(f"  MISSING 2K JPG maps for {asset_id}: diff={bool(diff_info)}, rough={bool(rough_info)}, nor={bool(nor_info)}")
            continue

        # Standard filenames
        dest_diff = os.path.join(OUT_DIR, f"{asset_id}_Diffuse_2k.jpg")
        dest_rough = os.path.join(OUT_DIR, f"{asset_id}_Rough_2k.jpg")
        dest_nor = os.path.join(OUT_DIR, f"{asset_id}_nor_gl_2k.jpg")

        ok1 = download_file(diff_info["url"], dest_diff)
        ok2 = download_file(rough_info["url"], dest_rough)
        ok3 = download_file(nor_info["url"], dest_nor)

        # Also create aliases if remote url filename had diff/rough lowercase
        orig_diff_name = os.path.basename(diff_info["url"])
        if orig_diff_name != os.path.basename(dest_diff):
            alias_path = os.path.join(OUT_DIR, orig_diff_name)
            if not os.path.exists(alias_path) and os.path.exists(dest_diff):
                with open(dest_diff, "rb") as sf, open(alias_path, "wb") as df:
                    df.write(sf.read())

        orig_rough_name = os.path.basename(rough_info["url"])
        if orig_rough_name != os.path.basename(dest_rough):
            alias_path = os.path.join(OUT_DIR, orig_rough_name)
            if not os.path.exists(alias_path) and os.path.exists(dest_rough):
                with open(dest_rough, "rb") as sf, open(alias_path, "wb") as df:
                    df.write(sf.read())

        if ok1 and ok2 and ok3:
            success_count += 1
            print(f"  [SUCCESS] {asset_id} complete (diff, rough, nor_gl).")
        else:
            print(f"  [FAILURE] {asset_id} incomplete.")

    print(f"\nCompleted fetching Poly Haven textures: {success_count}/{len(TARGET_SETS)} sets successfully obtained.")
    return success_count


if __name__ == "__main__":
    fetch_all()
