import os
import json
import math
import urllib.request
import urllib.parse

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"

# Load API Key from .env
env_path = os.path.join(BASE_DIR, ".env")
api_key = ""
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("GOOGLE_MAPS_API_KEY="):
            api_key = line.strip().split("=", 1)[1]

if not api_key:
    raise RuntimeError("GOOGLE_MAPS_API_KEY not found in .env")

# Master World Origin (Place d'Armes Center - Maisonneuve Monument)
MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0


def latlon_to_local_xy(lat: float, lon: float, origin_lat=MASTER_ORIGIN_LAT, origin_lon=MASTER_ORIGIN_LON):
    """Equirectangular local tangent plane projection in meters (X=East, Y=North)."""
    dlat = math.radians(lat - origin_lat)
    dlon = math.radians(lon - origin_lon)
    mean_lat = math.radians(origin_lat)
    x = dlon * EARTH_RADIUS_M * math.cos(mean_lat)
    y = dlat * EARTH_RADIUS_M
    return round(x, 3), round(y, 3)


block_id = "MTL-VM-0001"
block_dir = os.path.join(BASE_DIR, "data", "blocks", block_id)
sv_dir = os.path.join(block_dir, "streetview")
os.makedirs(sv_dir, exist_ok=True)

viewpoints = [
    {"label": "Center_South_to_Basilica", "lat": 45.50485, "lon": -73.55675, "heading": 140, "pitch": 12},
    {"label": "North_to_BMO_Dome", "lat": 45.50485, "lon": -73.55675, "heading": 325, "pitch": 10},
    {"label": "East_to_Aldred_Tower", "lat": 45.50485, "lon": -73.55675, "heading": 65, "pitch": 18},
    {"label": "West_to_500_Place_dArmes", "lat": 45.50455, "lon": -73.55695, "heading": 245, "pitch": 15},
]

downloaded_views = []
for vp in viewpoints:
    # 1. Fetch exact Street View metadata (outdoor only!)
    meta_url = (
        f"https://maps.googleapis.com/maps/api/streetview/metadata"
        f"?location={vp['lat']},{vp['lon']}&source=outdoor&key={api_key}"
    )
    with urllib.request.urlopen(meta_url) as r:
        meta = json.loads(r.read().decode("utf-8"))

    actual_lat = meta.get("location", {}).get("lat", vp["lat"])
    actual_lon = meta.get("location", {}).get("lng", vp["lon"])
    cam_x, cam_y = latlon_to_local_xy(actual_lat, actual_lon)

    # 2. Fetch 640x640 Street View Static image (outdoor only!)
    img_url = (
        f"https://maps.googleapis.com/maps/api/streetview"
        f"?size=640x640&location={actual_lat},{actual_lon}"
        f"&heading={vp['heading']}&pitch={vp['pitch']}&fov=90&source=outdoor&key={api_key}"
    )
    img_path = os.path.join(sv_dir, f"{vp['label']}.jpg")
    urllib.request.urlretrieve(img_url, img_path)

    downloaded_views.append({
        "label": vp["label"],
        "requested_lat": vp["lat"],
        "requested_lon": vp["lon"],
        "actual_lat": actual_lat,
        "actual_lon": actual_lon,
        "blender_cam_xy_m": [cam_x, cam_y],
        "heading_deg": vp["heading"],
        "pitch_deg": vp["pitch"],
        "fov_deg": 90,
        "pano_id": meta.get("pano_id"),
        "date": meta.get("date"),
        "image_path": img_path
    })
    print(f"Downloaded Street View: {vp['label']} -> ({cam_x}m, {cam_y}m) at {img_path}")

# 3. Fetch Top-Down Satellite Static Map (Zoom 19, 640x640, scale=2 -> 1280x1280)
sat_url = (
    f"https://maps.googleapis.com/maps/api/staticmap"
    f"?center={MASTER_ORIGIN_LAT},{MASTER_ORIGIN_LON}&zoom=19&size=640x640&scale=2"
    f"&maptype=satellite&key={api_key}"
)
sat_path = os.path.join(sv_dir, "satellite_topdown.png")
urllib.request.urlretrieve(sat_url, sat_path)
print(f"Downloaded Satellite Top-Down -> {sat_path}")

# Calculate exact meter coverage of Zoom 19 at lat 45.50472 for 640px (at scale 1 base)
# Ground resolution at zoom Z: (156543.03392 * cos(lat)) / (2^Z) meters per pixel (at 256px tile base)
meters_per_px_z19 = (156543.03392 * math.cos(math.radians(MASTER_ORIGIN_LAT))) / (2 ** 19)
sat_span_meters = round(meters_per_px_z19 * 640, 2)
print(f"Satellite ground span (640 base px at Z19): {sat_span_meters}m x {sat_span_meters}m")

# 4. Query OpenStreetMap Overpass API for Place d'Armes & immediate perimeter (bbox around Place d'Armes)
bbox = "45.5038,-73.5578,45.5056,-73.5554"
overpass_query = f"""
[out:json][timeout:25];
(
  way["building"]({bbox});
  relation["building"]({bbox});
  way["leisure"="park"]({bbox});
  way["place"="square"]({bbox});
  way["highway"]({bbox});
  node["historic"="monument"]({bbox});
  way["historic"="monument"]({bbox});
  node["natural"="tree"]({bbox});
);
out body;
>;
out skel qt;
"""
overpass_url = "https://overpass-api.de/api/interpreter"
req = urllib.request.Request(
    overpass_url,
    data=urllib.parse.urlencode({"data": overpass_query}).encode("utf-8"),
    headers={"User-Agent": "Montreal3DTwin/1.0", "Accept": "application/json"}
)
osm_features = {"buildings": [], "highways": [], "parks_squares": [], "monuments": [], "trees": []}
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        osm_raw = json.loads(r.read().decode("utf-8"))
    nodes = {}
    for el in osm_raw.get("elements", []):
        if el["type"] == "node":
            x, y = latlon_to_local_xy(el["lat"], el["lon"])
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"], "x": x, "y": y, "tags": el.get("tags", {})}
            tags = el.get("tags", {})
            if tags.get("historic") == "monument" or "Maisonneuve" in tags.get("name", ""):
                osm_features["monuments"].append({"id": el["id"], "x": x, "y": y, "tags": tags})
            if tags.get("natural") == "tree":
                osm_features["trees"].append({"id": el["id"], "x": x, "y": y})

    for el in osm_raw.get("elements", []):
        if el["type"] == "way":
            tags = el.get("tags", {})
            coords = [
                [nodes[nid]["x"], nodes[nid]["y"]]
                for nid in el.get("nodes", [])
                if nid in nodes
            ]
            if not coords:
                continue
            item = {"id": el["id"], "name": tags.get("name", ""), "tags": tags, "coords_xy": coords}
            if "building" in tags:
                osm_features["buildings"].append(item)
            elif "highway" in tags:
                osm_features["highways"].append(item)
            elif tags.get("leisure") == "park" or tags.get("place") == "square" or "Place d'Armes" in tags.get("name", ""):
                osm_features["parks_squares"].append(item)
            elif tags.get("historic") == "monument":
                osm_features["monuments"].append(item)
    print(
        f"OSM Overpass parsed: {len(osm_features['buildings'])} buildings, "
        f"{len(osm_features['highways'])} street segments, "
        f"{len(osm_features['parks_squares'])} squares/parks, "
        f"{len(osm_features['monuments'])} monuments, "
        f"{len(osm_features['trees'])} trees"
    )
except Exception as e:
    print("Overpass warning:", e)

dossier = {
    "block_id": block_id,
    "name": "Place d'Armes (Park in front of Notre-Dame Basilica)",
    "crs": {
        "projection": "Local Metric Tangent Plane (EPSG:32188 / MTM Zone 8 aligned)",
        "master_origin_wgs84": [MASTER_ORIGIN_LAT, MASTER_ORIGIN_LON],
        "block_offset_m": [0.0, 0.0, 0.0],
        "unit": "meters"
    },
    "satellite": {
        "image_path": sat_path,
        "span_meters": sat_span_meters
    },
    "streetview_cameras": downloaded_views,
    "osm_features": osm_features
}

dossier_path = os.path.join(block_dir, "dossier.json")
with open(dossier_path, "w", encoding="utf-8") as f:
    json.dump(dossier, f, indent=2, ensure_ascii=False)
print(f"Saved block dossier -> {dossier_path}")
