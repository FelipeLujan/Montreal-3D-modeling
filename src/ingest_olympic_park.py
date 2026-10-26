"""
Ingest Montreal Olympic Park (Parc olympique de Montréal) — Block ID: MTL-OLY-0001
Georeferenced in the shared Montreal metric tangent plane (EPSG:32188 aligned),
fetching OpenStreetMap footprints (Olympic Stadium, Inclined Tower, Biodôme/Velodrome,
Esplanade, Sports Centre, StarCite, Saputo Stadium), 4 verified outdoor Google Street View
panoramas, and a 1:1 Google Maps Satellite Top-Down orthophoto covering the Olympic Park complex.
"""
import os
import sys
import json
import math
import ssl
import shutil
import urllib.request
import urllib.parse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingest_all_blocks import (
    BASE_DIR, BLOCKS_DIR, MASTER_ORIGIN_LAT, MASTER_ORIGIN_LON,
    latlon_to_local_xy, query_sv_meta, is_official_google_outdoor_pano,
    find_guaranteed_outdoor_pano, download_sv_image, api_key
)

OLYMPIC_PARK_SPEC = {
    "block_id": "MTL-OLY-0001",
    "name": "Parc olympique de Montréal — Stade olympique, Tour de Montréal (165m Inclined Tower), Biodôme & Esplanade",
    "street_address": "4141 Avenue Pierre-De Coubertin, Montréal, QC H1V 3N7",
    "lat": 45.55775,
    "lon": -73.55165,
    "bbox": "45.5535,-73.5570,45.5620,-73.5460",
    "sat_zoom": 17,  # Zoom 17 (~535m span) captures the entire Olympic Stadium + Tower + Biodôme + Esplanade in one 1280x1280 ortho!
    "archetype": "Roger Taillibert 1976 Brutalist Masterpiece: Elliptical 38-Rib Cantilevered Olympic Stadium, 165m 45°-Inclined Curved Montreal Tower with Glass Curtain-Wall Office Tiers & Suspension Cables, Scalloped Concrete-Shell Biodôme (Velodrome), Multi-Tiered Esplanade & Landscaped Plazas",
    "streetview_points": [
        {
            "label": "Tour_de_Montreal_and_Biodome_South",
            "lat": 45.55695,
            "lon": -73.54945,
            "heading": 305,
            "pitch": 18
        },
        {
            "label": "Stade_Olympique_Ribs_PierreDeCoubertin",
            "lat": 45.55605,
            "lon": -73.55135,
            "heading": 355,
            "pitch": 14
        },
        {
            "label": "Biodome_Velodrome_Facade_East",
            "lat": 45.55785,
            "lon": -73.54835,
            "heading": 245,
            "pitch": 12
        },
        {
            "label": "Esplanade_Olympique_PieIX_Approach",
            "lat": 45.55615,
            "lon": -73.55355,
            "heading": 45,
            "pitch": 14
        }
    ]
}


def main():
    spec = OLYMPIC_PARK_SPEC
    bid = spec["block_id"]
    block_dir = os.path.join(BLOCKS_DIR, bid)
    sv_dir = os.path.join(block_dir, "streetview")
    renders_dir = os.path.join(block_dir, "renders")
    snapshots_dir = os.path.join(block_dir, "snapshots")
    os.makedirs(sv_dir, exist_ok=True)
    os.makedirs(renders_dir, exist_ok=True)
    os.makedirs(snapshots_dir, exist_ok=True)

    bbox = spec["bbox"]
    overpass_query = f"""
    [out:json][timeout:60];
    (
      way["building"]({bbox});
      relation["building"]({bbox});
      way["leisure"]({bbox});
      relation["leisure"]({bbox});
      way["highway"]({bbox});
      way["man_made"]({bbox});
      way["tourism"]({bbox});
      node["natural"="tree"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    ctx = ssl._create_unverified_context()
    osm_raw = None
    for url in [
        "https://overpass.private.coffee/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]:
        try:
            req = urllib.request.Request(
                url,
                data=urllib.parse.urlencode({"data": overpass_query}).encode("utf-8"),
                headers={"User-Agent": "Montreal3DTwin/2.0"}
            )
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                osm_raw = json.loads(r.read().decode("utf-8"))
            if osm_raw and "elements" in osm_raw:
                print(f"[OSM] Fetched {len(osm_raw['elements'])} elements from {url}")
                break
        except Exception as e:
            print(f"[OSM] Warning from {url}: {e}")

    elements = osm_raw.get("elements", []) if osm_raw else []
    nodes = {}
    ways_by_id = {}
    trees = []
    for el in elements:
        if el["type"] == "node":
            x, y = latlon_to_local_xy(el["lat"], el["lon"])
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"], "x": x, "y": y, "tags": el.get("tags", {})}
            if el.get("tags", {}).get("natural") == "tree":
                trees.append({"id": el["id"], "lat": el["lat"], "lon": el["lon"], "x": x, "y": y})
        elif el["type"] == "way":
            ways_by_id[el["id"]] = el

    buildings = []
    highways = []
    parks = []
    car_street_nodes = []
    seen_bldg_ids = set()

    for el in elements:
        if el["type"] == "way":
            tags = el.get("tags", {})
            way_nodes = [nodes[nid] for nid in el.get("nodes", []) if nid in nodes]
            if not way_nodes:
                continue
            coords_xy = [[n["x"], n["y"]] for n in way_nodes]
            coords_ll = [[n["lat"], n["lon"]] for n in way_nodes]
            clat = sum(p[0] for p in coords_ll) / len(coords_ll)
            clon = sum(p[1] for p in coords_ll) / len(coords_ll)
            cx, cy = latlon_to_local_xy(clat, clon)
            item = {
                "id": el["id"],
                "name": tags.get("name", ""),
                "tags": tags,
                "centroid_latlon": [round(clat, 6), round(clon, 6)],
                "centroid_xy": [cx, cy],
                "coords_xy": coords_xy
            }
            if (
                "building" in tags
                or "building:part" in tags
                or tags.get("leisure") in ("stadium", "sports_centre", "pitch")
                or tags.get("man_made") in ("tower", "bridge", "works")
                or tags.get("tourism") in ("attraction", "museum", "viewpoint")
            ):
                item["owner_block_id"] = bid
                item["is_primary_owner"] = True
                buildings.append(item)
                seen_bldg_ids.add(el["id"])
            elif "highway" in tags:
                highways.append(item)
                if tags.get("highway") in ("primary", "secondary", "tertiary", "residential", "service", "unclassified"):
                    for n in way_nodes:
                        car_street_nodes.append({"lat": n["lat"], "lon": n["lon"], "x": n["x"], "y": n["y"], "name": tags.get("name", "street")})
            elif tags.get("leisure") in ("park", "garden"):
                parks.append(item)

        elif el["type"] == "relation":
            tags = el.get("tags", {})
            if "building" in tags or tags.get("leisure") in ("stadium", "sports_centre") or tags.get("tourism") in ("attraction", "museum"):
                outer_ways = [
                    ways_by_id[m["ref"]]
                    for m in el.get("members", [])
                    if m.get("type") == "way" and m.get("role") in ("outer", "") and m.get("ref") in ways_by_id
                ]
                for w in outer_ways:
                    if w["id"] in seen_bldg_ids:
                        continue
                    wn = [nodes[nid] for nid in w.get("nodes", []) if nid in nodes]
                    if len(wn) < 3:
                        continue
                    coords_xy = [[n["x"], n["y"]] for n in wn]
                    coords_ll = [[n["lat"], n["lon"]] for n in wn]
                    clat = sum(p[0] for p in coords_ll) / len(coords_ll)
                    clon = sum(p[1] for p in coords_ll) / len(coords_ll)
                    cx, cy = latlon_to_local_xy(clat, clon)
                    merged_tags = dict(tags)
                    merged_tags.update(w.get("tags", {}))
                    buildings.append({
                        "id": w["id"],
                        "relation_id": el["id"],
                        "name": merged_tags.get("name", ""),
                        "tags": merged_tags,
                        "centroid_latlon": [round(clat, 6), round(clon, 6)],
                        "centroid_xy": [cx, cy],
                        "coords_xy": coords_xy,
                        "owner_block_id": bid,
                        "is_primary_owner": True,
                    })
                    seen_bldg_ids.add(w["id"])

    block_cx, block_cy = latlon_to_local_xy(spec["lat"], spec["lon"])
    downloaded_views = []
    used_panos = set()

    for vp in spec["streetview_points"]:
        label = vp["label"]
        pitch = vp.get("pitch", 14)
        tlat, tlon = vp["lat"], vp["lon"]
        meta = query_sv_meta(tlat, tlon, radius=90)
        source_desc = "direct"
        if not is_official_google_outdoor_pano(meta) or meta.get("pano_id") in used_panos:
            new_meta, source_desc = find_guaranteed_outdoor_pano(tlat, tlon, car_street_nodes, used_panos)
            if new_meta:
                meta = new_meta
        pano_id = meta.get("pano_id", "") if meta else ""
        if pano_id:
            used_panos.add(pano_id)
        loc = meta.get("location", {}) if meta else {}
        alat = loc.get("lat", tlat)
        alon = loc.get("lng", tlon)
        cam_x, cam_y = latlon_to_local_xy(alat, alon)
        heading = round(vp["heading"], 1)
        img_path = os.path.join(sv_dir, f"{label}.jpg")
        download_sv_image(pano_id, alat, alon, heading, pitch, 90, img_path)
        shutil.copy2(img_path, os.path.join(snapshots_dir, f"{label}.jpg"))
        downloaded_views.append({
            "label": label,
            "requested_lat": tlat,
            "requested_lon": tlon,
            "actual_lat": alat,
            "actual_lon": alon,
            "blender_cam_xy_m": [cam_x, cam_y],
            "heading": heading,
            "heading_deg": heading,
            "pitch_deg": pitch,
            "fov_deg": 90,
            "pano_id": pano_id,
            "date": meta.get("date", "") if meta else "",
            "copyright": meta.get("copyright", "© Google") if meta else "© Google",
            "refetched_source": source_desc,
            "image_path": img_path,
            "google_maps_url": f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={alat:.5f},{alon:.5f}&heading={heading}&pitch={pitch}&fov=90&pano={pano_id}"
        })

    sat_zoom = spec.get("sat_zoom", 17)
    sat_path = os.path.join(sv_dir, "satellite_topdown.png")
    sat_url = (
        f"https://maps.googleapis.com/maps/api/staticmap"
        f"?center={spec['lat']},{spec['lon']}&zoom={sat_zoom}&size=640x640&scale=2"
        f"&maptype=satellite&key={api_key}"
    )
    urllib.request.urlretrieve(sat_url, sat_path)
    shutil.copy2(sat_path, os.path.join(snapshots_dir, "satellite_topdown.png"))
    meters_per_px = (156543.03392 * math.cos(math.radians(spec["lat"]))) / (2 ** sat_zoom)
    sat_span_meters = round(meters_per_px * 640, 2)

    dossier = {
        "block_id": bid,
        "name": spec["name"],
        "street_address": spec["street_address"],
        "archetype": spec["archetype"],
        "blender_center_xy_m": [block_cx, block_cy],
        "crs": {
            "projection": "Local Metric Tangent Plane (EPSG:32188 / MTM Zone 8 aligned)",
            "master_origin_wgs84": [MASTER_ORIGIN_LAT, MASTER_ORIGIN_LON],
            "block_center_wgs84": [spec["lat"], spec["lon"]],
            "block_center_xy_m": [block_cx, block_cy],
            "unit": "meters"
        },
        "satellite": {
            "image_path": sat_path,
            "zoom": sat_zoom,
            "span_meters": sat_span_meters,
            "center_xy_m": [block_cx, block_cy]
        },
        "streetview_cameras": downloaded_views,
        "osm_features": {
            "buildings": buildings,
            "highways": highways,
            "parks_squares": parks,
            "monuments": [],
            "trees": trees
        }
    }

    dossier_path = os.path.join(block_dir, "dossier.json")
    with open(dossier_path, "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)

    print(f"[OK] Ingested {bid}: {len(buildings)} buildings/structures, {len(highways)} streets, {len(parks)} parks, 4 SV, 1 Sat (zoom={sat_zoom}, span={sat_span_meters}m, center={[block_cx, block_cy]})")


if __name__ == "__main__":
    main()
