"""
Ingest 8 Iconic New Old Port & Waterfront Expansion Blocks (MTL-VM-0037 through MTL-VM-0044).
Fetches OpenStreetMap footprints, 4 verified outdoor Google Street View panoramas per block,
and 1:1 Zoom-19 Google Maps Satellite Top-Down orthophotos without disturbing running blocks.
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

NEW_ICONIC_BLOCKS = [
    {
        "block_id": "MTL-VM-0037",
        "name": "Pont Victoria Approach, Windmill Point (Pointe-du-Moulin South) & Silo No. 4 Waterfront",
        "street_address": "Rue de la Riverside / Rue Mill (Pont Victoria Approach), Montréal, QC H3C 1Y4",
        "lat": 45.49380,
        "lon": -73.54950,
        "bbox": "45.4922,-73.5518,45.4950,-73.5470",
        "archetype": "Historic Steel Through-Truss Victoria Bridge Approach, Windmill Point Harbor Basin, Grain Terminal Quay & Rail Corridor",
        "streetview_points": [
            {"label": "Pont_Victoria_North_Approach", "lat": 45.49325, "lon": -73.55045, "heading": 135},
            {"label": "Rue_Mill_Windmill_Point_East", "lat": 45.49445, "lon": -73.55015, "heading": 65},
            {"label": "Riverside_Harbor_Industrial_View", "lat": 45.49395, "lon": -73.55125, "heading": 95},
            {"label": "Bassin_Windmill_South_Quay", "lat": 45.49485, "lon": -73.55085, "heading": 155}
        ]
    },
    {
        "block_id": "MTL-VM-0038",
        "name": "Île Sainte-Hélène West Shoreline, Biosphère Geodesic Dome & Parc Jean-Drapeau Waterfront",
        "street_address": "160 Chemin du Tour-de-l'isle, Montréal, QC H3C 4G8",
        "lat": 45.51420,
        "lon": -73.53220,
        "bbox": "45.5125,-73.5350,45.5160,-73.5295",
        "archetype": "Buckminster Fuller Expo 67 Steel Geodesic Dome (Biosphère), Island Park Lawns, Ferry Terminal & St. Lawrence River Vista",
        "streetview_points": [
            {"label": "Biosphere_Geodesic_Dome_Front", "lat": 45.51445, "lon": -73.53185, "heading": 15},
            {"label": "Ile_Sainte_Helene_West_Promenade", "lat": 45.51385, "lon": -73.53365, "heading": 290},
            {"label": "Parc_Jean_Drapeau_Metro_Plaza", "lat": 45.51325, "lon": -73.53265, "heading": 350},
            {"label": "Chemin_Tour_de_l_Isle_North", "lat": 45.51515, "lon": -73.53245, "heading": 195}
        ]
    },
    {
        "block_id": "MTL-VM-0039",
        "name": "Pont Jacques-Cartier Monumental Steel Cantilever Bridge & Pied-du-Courant Heritage Park",
        "street_address": "Rue Notre-Dame Est / Avenue De Lorimier (Pont Jacques-Cartier), Montréal, QC H2K 2N4",
        "lat": 45.51720,
        "lon": -73.54680,
        "bbox": "45.5155,-73.5495,45.5190,-73.5440",
        "archetype": "Iconic Green Painted Steel Cantilever Bridge Towers & Piers, Craig Pumping Station & Pied-du-Courant Heritage Esplanade",
        "streetview_points": [
            {"label": "Pont_Jacques_Cartier_Main_Span_South", "lat": 45.51685, "lon": -73.54715, "heading": 135},
            {"label": "Rue_NotreDameEst_Bridge_Underpass", "lat": 45.51645, "lon": -73.54765, "heading": 55},
            {"label": "Craig_Pumping_Station_Facade", "lat": 45.51755, "lon": -73.54635, "heading": 215},
            {"label": "Parc_Pied_du_Courant_River_View", "lat": 45.51805, "lon": -73.54585, "heading": 165}
        ]
    },
    {
        "block_id": "MTL-VM-0040",
        "name": "Ancienne Brasserie Molson Heritage Waterfront & Quai des Convoyeurs (Rue Notre-Dame Est)",
        "street_address": "1670 Rue Notre-Dame Est, Montréal, QC H2L 2R4",
        "lat": 45.51450,
        "lon": -73.54820,
        "bbox": "45.5130,-73.5505,45.5160,-73.5458",
        "archetype": "Historic 1786 Red-Brick Molson Brewery Clocktower, Stepped Industrial Riverfront Complex & St. Lawrence Quay Wall",
        "streetview_points": [
            {"label": "Molson_Brewery_Clocktower_Facade", "lat": 45.51455, "lon": -73.54855, "heading": 125},
            {"label": "Rue_NotreDameEst_Molson_Canyon", "lat": 45.51385, "lon": -73.54925, "heading": 45},
            {"label": "Molson_North_Brick_Complex", "lat": 45.51535, "lon": -73.54795, "heading": 210},
            {"label": "Quai_Horloge_East_Approach_Molson", "lat": 45.51325, "lon": -73.54985, "heading": 35}
        ]
    },
    {
        "block_id": "MTL-VM-0041",
        "name": "Griffintown Heritage Block — New City Gas Victorian Gasholder Complex & Rue Ottawa",
        "street_address": "950 Rue Ottawa, Montréal, QC H3C 1S4",
        "lat": 45.49520,
        "lon": -73.55780,
        "bbox": "45.4938,-73.5600,45.4968,-73.5555",
        "archetype": "1861 Cut-Limestone & Slate-Roof New City Gas Heritage Complex, REM Viaduct & Griffintown Brick Lofts",
        "streetview_points": [
            {"label": "New_City_Gas_Heritage_Gable", "lat": 45.49535, "lon": -73.55765, "heading": 155},
            {"label": "Rue_Ottawa_Dalhousie_Corner", "lat": 45.49565, "lon": -73.55715, "heading": 235},
            {"label": "Rue_Wellington_West_Corridor", "lat": 45.49465, "lon": -73.55825, "heading": 45},
            {"label": "Rue_Ann_Industrial_Facade", "lat": 45.49505, "lon": -73.55865, "heading": 110}
        ]
    },
    {
        "block_id": "MTL-VM-0042",
        "name": "Square Viger Redesigned Urban Agora, Édifice Jacques-Viger & Avenue Viger Est",
        "street_address": "Square Viger / 750 Avenue Viger Est, Montréal, QC H2L 2P4",
        "lat": 45.51280,
        "lon": -73.55480,
        "bbox": "45.5114,-73.5570,45.5142,-73.5528",
        "archetype": "Contemporary Landscaped Civic Park (Square Viger Pergolas, Fountains & Lawns) + Heritage Beaux-Arts Stone Facades",
        "streetview_points": [
            {"label": "Square_Viger_West_Pergola_Lawn", "lat": 45.51225, "lon": -73.55545, "heading": 65},
            {"label": "Avenue_Viger_Est_North_Border", "lat": 45.51315, "lon": -73.55515, "heading": 145},
            {"label": "Rue_SaintAntoineEst_South_Border", "lat": 45.51195, "lon": -73.55425, "heading": 325},
            {"label": "Rue_Berri_Square_Viger_East", "lat": 45.51265, "lon": -73.55355, "heading": 245}
        ]
    },
    {
        "block_id": "MTL-VM-0043",
        "name": "Place d'Youville East, Édifice des Douanes South & Rue Saint-Pierre Heritage Warehouses",
        "street_address": "225 Place d'Youville, Montréal, QC H2Y 2B2",
        "lat": 45.50195,
        "lon": -73.55440,
        "bbox": "45.5010,-73.5555,45.5028,-73.5533",
        "archetype": "Tree-Lined Place d'Youville East Esplanade, Cut-Limestone Heritage Warehouses, Obelisk & Old Port Gateway",
        "streetview_points": [
            {"label": "Place_dYouville_East_Tree_Walk", "lat": 45.50215, "lon": -73.55445, "heading": 215},
            {"label": "Edifice_des_Douanes_South_Facade", "lat": 45.50245, "lon": -73.55405, "heading": 35},
            {"label": "Rue_de_la_Commune_Youville_Corner", "lat": 45.50175, "lon": -73.55375, "heading": 305},
            {"label": "Rue_SaintPierre_Youville_Cross", "lat": 45.50145, "lon": -73.55495, "heading": 55}
        ]
    },
    {
        "block_id": "MTL-VM-0044",
        "name": "Casino de Montréal Iconic Stepped Cantilevered Pavilions & Île Notre-Dame Lagoon Waterfront",
        "street_address": "1 Avenue du Casino, Montréal, QC H3C 4W7",
        "lat": 45.50560,
        "lon": -73.52560,
        "bbox": "45.5040,-73.5282,45.5072,-73.5230",
        "archetype": "Expo 67 French & Quebec Pavilions (Casino de Montréal Stepped Louvered Rotunda & Glass Atrium) + Island Lagoon Gardens",
        "streetview_points": [
            {"label": "Casino_Montreal_Main_Rotunda_West", "lat": 45.50565, "lon": -73.52635, "heading": 95},
            {"label": "Avenue_du_Casino_Bridge_Approach", "lat": 45.50515, "lon": -73.52695, "heading": 65},
            {"label": "Pavillon_du_Quebec_South_Lagoon", "lat": 45.50465, "lon": -73.52545, "heading": 15},
            {"label": "Ile_Notre_Dame_North_Water_Garden", "lat": 45.50635, "lon": -73.52525, "heading": 185}
        ]
    }
]


def ingest_single_block(spec: dict, claimed_ids: set):
    bid = spec["block_id"]
    block_dir = os.path.join(BLOCKS_DIR, bid)
    sv_dir = os.path.join(block_dir, "streetview")
    renders_dir = os.path.join(block_dir, "renders")
    snapshots_dir = os.path.join(block_dir, "snapshots")
    os.makedirs(sv_dir, exist_ok=True)
    os.makedirs(renders_dir, exist_ok=True)
    os.makedirs(snapshots_dir, exist_ok=True)

    bbox = spec["bbox"]
    existing_dossier_path = os.path.join(block_dir, "dossier.json")
    if os.path.exists(existing_dossier_path):
        try:
            ed = json.load(open(existing_dossier_path, encoding="utf-8"))
            ebldgs = ed.get("osm_features", {}).get("buildings", [])
            if len(ebldgs) > 0:
                bcx, bcy = ed["blender_center_xy_m"]
                for b in ebldgs:
                    cx, cy = b["centroid_xy"]
                    if abs(cx - bcx) <= 75.0 and abs(cy - bcy) <= 75.0:
                        b["is_primary_owner"] = True
                        b["owner_block_id"] = bid
                json.dump(ed, open(existing_dossier_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
                owned = sum(1 for b in ebldgs if b.get("is_primary_owner"))
                print(f"[SKIP-CACHED] {bid}: {owned} owned / {len(ebldgs)} total buildings")
                return
        except Exception:
            pass

    overpass_query = f"""
    [out:json][timeout:30];
    (
      way["building"]({bbox});
      relation["building"]({bbox});
      way["leisure"="park"]({bbox});
      way["highway"]({bbox});
      node["natural"="tree"]({bbox});
      way["man_made"]({bbox});
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
                headers={"User-Agent": "Montreal3DTwin/1.0"}
            )
            with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
                osm_raw = json.loads(r.read().decode("utf-8"))
            if osm_raw and "elements" in osm_raw:
                break
        except Exception as e:
            print(f"[{bid}] Overpass warning:", e)

    if not osm_raw or not osm_raw.get("elements"):
        global_osm_path = os.path.join(BASE_DIR, "data", "open_data", "old_montreal_osm.json")
        if os.path.exists(global_osm_path):
            with open(global_osm_path, "r", encoding="utf-8") as f:
                osm_raw = json.load(f)

    elements = osm_raw.get("elements", []) if osm_raw else []
    nodes = {}
    trees = []
    for el in elements:
        if el["type"] == "node":
            x, y = latlon_to_local_xy(el["lat"], el["lon"])
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"], "x": x, "y": y, "tags": el.get("tags", {})}
            if el.get("tags", {}).get("natural") == "tree":
                trees.append({"id": el["id"], "lat": el["lat"], "lon": el["lon"], "x": x, "y": y})

    block_cx, block_cy = latlon_to_local_xy(spec["lat"], spec["lon"])
    s_lat, w_lon, n_lat, e_lon = [float(x) for x in bbox.split(",")]
    buildings = []
    highways = []
    parks = []
    car_street_nodes = []
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
            if not (s_lat <= clat <= n_lat and w_lon <= clon <= e_lon):
                continue
            cx, cy = latlon_to_local_xy(clat, clon)
            item = {
                "id": el["id"],
                "name": tags.get("name", ""),
                "tags": tags,
                "centroid_latlon": [round(clat, 6), round(clon, 6)],
                "centroid_xy": [cx, cy],
                "coords_xy": coords_xy
            }
            if "building" in tags or tags.get("man_made") in ("silo", "works", "storage_tank", "bridge", "tower"):
                in_core = (abs(cx - block_cx) <= 75.0 and abs(cy - block_cy) <= 75.0)
                is_owner = (el["id"] not in claimed_ids) or in_core
                if is_owner:
                    claimed_ids.add(el["id"])
                item["owner_block_id"] = bid if is_owner else "EXISTING"
                item["is_primary_owner"] = is_owner
                buildings.append(item)
            elif "highway" in tags:
                highways.append(item)
                for n in way_nodes:
                    car_street_nodes.append({"lat": n["lat"], "lon": n["lon"], "x": n["x"], "y": n["y"], "name": tags.get("name", "street")})
            elif tags.get("leisure") == "park":
                parks.append(item)

    existing_dossier_path = os.path.join(block_dir, "dossier.json")
    existing_sv = []
    if os.path.exists(existing_dossier_path):
        try:
            existing_sv = json.load(open(existing_dossier_path, encoding="utf-8")).get("streetview_cameras", [])
        except Exception:
            existing_sv = []

    downloaded_views = existing_sv if len(existing_sv) == 4 else []
    used_panos = set()

    for vp in ([] if len(downloaded_views) == 4 else spec["streetview_points"]):
        label = vp["label"]
        pitch = 12
        tlat, tlon = vp["lat"], vp["lon"]
        meta = query_sv_meta(tlat, tlon, radius=85)
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
        if not os.path.exists(img_path):
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

    sat_path = os.path.join(sv_dir, "satellite_topdown.png")
    if not os.path.exists(sat_path):
        sat_url = (
            f"https://maps.googleapis.com/maps/api/staticmap"
            f"?center={spec['lat']},{spec['lon']}&zoom=19&size=640x640&scale=2"
            f"&maptype=satellite&key={api_key}"
        )
        urllib.request.urlretrieve(sat_url, sat_path)
        shutil.copy2(sat_path, os.path.join(snapshots_dir, "satellite_topdown.png"))
    meters_per_px_z19 = (156543.03392 * math.cos(math.radians(spec["lat"]))) / (2 ** 19)
    sat_span_meters = round(meters_per_px_z19 * 640, 2)

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

    owned = sum(1 for b in buildings if b["is_primary_owner"])
    print(f"[OK] Ingested {bid}: {owned} owned / {len(buildings)} total buildings, {len(highways)} streets, 4 SV, 1 Sat ({sat_span_meters}m)")


def main():
    claimed_ids = set()
    for i in range(1, 37):
        ebid = f"MTL-VM-{i:04d}"
        dpath = os.path.join(BLOCKS_DIR, ebid, "dossier.json")
        if os.path.exists(dpath):
            try:
                with open(dpath, "r", encoding="utf-8") as f:
                    d = json.load(f)
                for b in d.get("osm_features", {}).get("buildings", []):
                    if b.get("is_primary_owner"):
                        claimed_ids.add(b["id"])
            except Exception:
                pass

    for spec in NEW_ICONIC_BLOCKS:
        ingest_single_block(spec, claimed_ids)


if __name__ == "__main__":
    main()
