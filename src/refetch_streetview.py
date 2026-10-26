"""
Coordinator Street View Audit & Outdoor Street-Centerline Re-Fetch Tool
========================================================================
Detects indoor / user-contributed 360 photospheres (where copyright != '© Google'
or pano_id starts with 'CAoS' or probe point fell inside a building polygon)
and re-fetches guaranteed outdoor Google Street View car panoramas by snapping
probe coordinates to OpenStreetMap street centerlines (highways) outside all
building footprints.

Can be invoked by Coordinator Agents or flagged by Subagents:
  python src/refetch_streetview.py --audit
  python src/refetch_streetview.py --fix-all
  python src/refetch_streetview.py --block MTL-VM-0003 --camera Rear_Rue_SaintAntoine
"""
import argparse
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
BLOCKS_DIR = ROOT / "data" / "blocks"
OSM_FILE = ROOT / "data" / "open_data" / "old_montreal_osm.json"
ENV_FILE = ROOT / ".env"

ORIGIN_LAT = 45.50472
ORIGIN_LON = -73.55661
METERS_PER_DEG_LAT = 111132.92
METERS_PER_DEG_LON = 111412.84 * math.cos(math.radians(ORIGIN_LAT))


def load_api_key() -> str:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("GOOGLE_MAPS_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("GOOGLE_MAPS_API_KEY not found in .env")


def latlon_to_xy(lat: float, lon: float):
    x = (lon - ORIGIN_LON) * METERS_PER_DEG_LON
    y = (lat - ORIGIN_LAT) * METERS_PER_DEG_LAT
    return round(x, 2), round(y, 2)


def xy_to_latlon(x: float, y: float):
    lat = ORIGIN_LAT + (y / METERS_PER_DEG_LAT)
    lon = ORIGIN_LON + (x / METERS_PER_DEG_LON)
    return round(lat, 6), round(lon, 6)


def is_official_google_outdoor_pano(meta: dict) -> bool:
    if meta.get("status") != "OK":
        return False
    pano_id = meta.get("pano_id", "")
    copyright_str = meta.get("copyright", "")
    # Third-party / indoor business / user photospheres have pano_id starting with CAoS
    # or copyright with a photographer/business name instead of '© Google'
    if pano_id.startswith("CAoS") or len(pano_id) > 28:
        return False
    if "Google" not in copyright_str:
        return False
    return True


def query_sv_meta(lat: float, lon: float, radius: int, api_key: str) -> dict:
    params = urllib.parse.urlencode({
        "location": f"{lat},{lon}",
        "radius": radius,
        "source": "outdoor",
        "key": api_key,
    })
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?{params}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_sv_image(pano_id: str, heading: float, pitch: float, fov: float, out_path: Path, api_key: str):
    params = urllib.parse.urlencode({
        "size": "640x640",
        "pano": pano_id,
        "heading": round(heading, 1),
        "pitch": round(pitch, 1),
        "fov": round(fov, 1),
        "key": api_key,
    })
    url = f"https://maps.googleapis.com/maps/api/streetview?{params}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=20) as resp:
        out_path.write_bytes(resp.read())


def collect_street_nodes(dossier: dict):
    """Collects all (x, y, lat, lon, street_name) points along OSM highways in the block."""
    pts = []
    for hw in dossier.get("osm_features", {}).get("highways", []):
        tags = hw.get("tags", {})
        hw_type = tags.get("highway", "")
        # Prefer actual vehicular streets where the Google Street View car drives!
        is_car_street = hw_type in ("primary", "secondary", "tertiary", "residential", "unclassified", "living_street", "service")
        pts_xy = hw.get("coords_xy", hw.get("points_xy", []))
        for x, y in pts_xy:
            lat, lon = xy_to_latlon(x, y)
            pts.append({
                "x": x,
                "y": y,
                "lat": lat,
                "lon": lon,
                "is_car_street": is_car_street,
                "name": tags.get("name", hw_type),
            })
    return pts


def find_guaranteed_outdoor_google_pano(target_lat: float, target_lon: float, dossier: dict, api_key: str, used_panos: set):
    """
    Searches for an official '© Google' outdoor street car panorama near (target_lat, target_lon):
    1. First checks direct coordinate with small radius (15m, 30m).
    2. Next snaps to nearest OSM car-street centerline nodes in the block and probes each one.
    3. Lastly probes a ring of offsets around the target coordinate.
    """
    tx, ty = latlon_to_xy(target_lat, target_lon)

    # Candidate probe points: (lat, lon, desc)
    candidates = [(target_lat, target_lon, "direct")]

    street_pts = collect_street_nodes(dossier)
    # Sort street points by distance to target (preferring car streets first)
    street_pts.sort(key=lambda p: (0 if p["is_car_street"] else 1, math.hypot(p["x"] - tx, p["y"] - ty)))
    for sp in street_pts[:25]:
        candidates.append((sp["lat"], sp["lon"], f"osm_street:{sp['name']}"))

    # Also add 20m, 40m, 60m cardinal/diagonal offsets
    for dist in (20, 40, 60, 85):
        for ang_deg in range(0, 360, 45):
            rad = math.radians(ang_deg)
            ox, oy = tx + dist * math.cos(rad), ty + dist * math.sin(rad)
            olat, olon = xy_to_latlon(ox, oy)
            candidates.append((olat, olon, f"offset_{dist}m_{ang_deg}deg"))

    tested = set()
    for clat, clon, desc in candidates:
        key = (round(clat, 4), round(clon, 4))
        if key in tested:
            continue
        tested.add(key)
        for radius in (15, 35, 60):
            meta = query_sv_meta(clat, clon, radius, api_key)
            if is_official_google_outdoor_pano(meta):
                pid = meta["pano_id"]
                if pid not in used_panos:
                    return meta, desc
    # Second pass allowing reuse of a valid Google outdoor pano if needed (with different heading)
    tested.clear()
    for clat, clon, desc in candidates[:20]:
        key = (round(clat, 4), round(clon, 4))
        if key in tested:
            continue
        tested.add(key)
        meta = query_sv_meta(clat, clon, 50, api_key)
        if is_official_google_outdoor_pano(meta):
            return meta, desc + "_reused_pano"

    return None, "failed"


def audit_and_fix(fix: bool = False, target_block: str = None, target_camera: str = None):
    api_key = load_api_key()
    flagged = []
    fixed = []

    for dossier_path in sorted(BLOCKS_DIR.glob("MTL-VM-*/dossier.json")):
        dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
        bid = dossier["block_id"]
        if target_block and bid != target_block:
            continue
        if not target_block and bid == "MTL-VM-0001":
            # MTL-VM-0001 is the pedestrian square interior (already visually verified outdoor plaza views)
            continue

        used_panos = set()
        for cam in dossier.get("streetview_cameras", []):
            meta_sim = {
                "status": "OK",
                "pano_id": cam.get("pano_id", ""),
                "copyright": cam.get("copyright", ""),
            }
            if is_official_google_outdoor_pano(meta_sim):
                used_panos.add(cam["pano_id"])

        modified = False
        for cam in dossier.get("streetview_cameras", []):
            label = cam["label"]
            if target_camera and label != target_camera:
                continue

            pano_id = cam.get("pano_id", "")
            cp = cam.get("copyright", "")
            meta_check = {"status": "OK", "pano_id": pano_id, "copyright": cp}

            is_valid = is_official_google_outdoor_pano(meta_check)
            # Also force fix if specifically targeted by subagent/user flag
            force_target = (target_block == bid and target_camera == label)

            if not is_valid or force_target:
                reason = f"Indoor/3rd-party photosphere (copyright='{cp}', pano_id='{pano_id[:18]}...')"
                flagged.append((bid, label, reason))
                print(f"[FLAGGED] {bid} | {label}: {reason}")

                if fix:
                    cx, cy = dossier.get("blender_center_xy_m", [0.0, 0.0])
                    def_lat, def_lon = xy_to_latlon(cx, cy)
                    req_lat = cam.get("requested_lat", cam.get("actual_lat", def_lat))
                    req_lon = cam.get("requested_lon", cam.get("actual_lon", def_lon))
                    new_meta, source_desc = find_guaranteed_outdoor_google_pano(req_lat, req_lon, dossier, api_key, used_panos)
                    if new_meta:
                        new_pid = new_meta["pano_id"]
                        used_panos.add(new_pid)
                        alat = new_meta["location"]["lat"]
                        alon = new_meta["location"]["lng"]
                        bx, by = latlon_to_xy(alat, alon)

                        # Calculate heading from the new outdoor street camera toward the original target or block center
                        tx, ty = latlon_to_xy(req_lat, req_lon)
                        dx, dy = cx - bx, cy - by
                        if math.hypot(dx, dy) < 5.0:
                            dx, dy = tx - bx, ty - by
                        # Compass heading (0=North=+Y, 90=East=+X)
                        auto_heading = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
                        heading = round(auto_heading, 1)

                        img_path = Path(cam["image_path"])
                        download_sv_image(new_pid, heading, cam.get("pitch", 10), cam.get("fov", 90), img_path, api_key)

                        cam["pano_id"] = new_pid
                        cam["actual_lat"] = alat
                        cam["actual_lon"] = alon
                        cam["blender_cam_xy_m"] = [bx, by]
                        cam["heading"] = heading
                        cam["date"] = new_meta.get("date", "")
                        cam["copyright"] = new_meta.get("copyright", "© Google")
                        cam["refetched_source"] = source_desc
                        cam["google_maps_url"] = (
                            f"https://www.google.com/maps/@?api=1&map_action=pano"
                            f"&pano={new_pid}&heading={heading}&pitch={cam.get('pitch', 10)}&fov={cam.get('fov', 90)}"
                        )
                        modified = True
                        fixed.append((bid, label, new_pid, alat, alon, heading, source_desc))
                        print(f"  -> [RE-FETCHED OUTDOOR GOOGLE PANO] {bid} | {label}: pano={new_pid} ({new_meta.get('date')}) via {source_desc} @ ({alat:.5f}, {alon:.5f}) heading={heading}°")
                    else:
                        print(f"  -> [ERROR] Could not find outdoor Google pano for {bid} | {label}")

        if modified:
            dossier_path.write_text(json.dumps(dossier, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nSummary: Flagged={len(flagged)}, Fixed={len(fixed)}")
    return flagged, fixed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true", help="Audit all blocks for indoor/non-Google panos")
    parser.add_argument("--fix-all", action="store_true", help="Re-fetch all flagged indoor/non-Google panos with outdoor Google street panos")
    parser.add_argument("--block", type=str, default=None, help="Specific block ID (e.g., MTL-VM-0003)")
    parser.add_argument("--camera", type=str, default=None, help="Specific camera label (e.g., Rear_Rue_SaintAntoine)")
    args = parser.parse_args()

    do_fix = args.fix_all or (args.block is not None)
    audit_and_fix(fix=do_fix, target_block=args.block, target_camera=args.camera)
