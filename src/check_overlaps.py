import json, unicodedata, math
from collections import defaultdict
import sys
sys.path.append('src')

osm = json.load(open('data/open_data/old_montreal_osm.json', encoding='utf-8'))
nodes = {e['id']: (e['lat'], e['lon']) for e in osm['elements'] if e.get('type') == 'node' and 'lat' in e}

MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0

def latlon_to_local_xy(lat, lon):
    dlat = math.radians(lat - MASTER_ORIGIN_LAT)
    dlon = math.radians(lon - MASTER_ORIGIN_LON)
    mean_lat = math.radians(MASTER_ORIGIN_LAT)
    return dlon * EARTH_RADIUS_M * math.cos(mean_lat), dlat * EARTH_RADIUS_M

def norm(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t.lower()) if unicodedata.category(c) != 'Mn')

REQUIRED_STREETS = [
    "Rue Notre-Dame",
    "Rue Saint-Jacques",
    "Rue Saint-Antoine",
    "Rue Saint-Paul",
    "Rue de la Commune",
    "Rue McGill",
    "Rue Saint-Pierre",
    "Rue Saint-François-Xavier",
    "Rue Saint-Sulpice",
    "Côte de la Place d'Armes",
    "Place Jacques-Cartier",
    "Square Victoria",
    "Avenue Viger"
]

elements = osm.get("elements", [])
street_ways = defaultdict(list)
for e in elements:
    if e.get("type") == "way" and "tags" in e and "highway" in e["tags"]:
        name = e["tags"].get("name", "")
        norm_name = norm(name)
        for s in REQUIRED_STREETS:
            if norm(s) in norm_name:
                pts = [latlon_to_local_xy(*nodes[nid]) for nid in e.get("nodes", []) if nid in nodes]
                if len(pts) >= 2:
                    street_ways[s].append(pts)

primary_arterials = [
    'Avenue Viger', 'Rue Saint-Antoine', 'Rue Saint-Jacques',
    'Rue Notre-Dame', 'Rue Saint-Paul', 'Rue de la Commune'
]

# Generate all faces without any skip
all_road_faces = []
for s in REQUIRED_STREETS:
    ways = street_ways[s]
    w = 14.0 if "viger" in norm(s) else (10.5 if s in primary_arterials else 8.0)
    hw = w * 0.5
    for pts in ways:
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i+1]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            L = math.hypot(dx, dy)
            if L < 0.1: continue
            nx, ny = -dy / L, dx / L
            xs = [p1[0] + nx * hw, p2[0] + nx * hw, p2[0] - nx * hw, p1[0] - nx * hw]
            ys = [p1[1] + ny * hw, p2[1] + ny * hw, p2[1] - ny * hw, p1[1] - ny * hw]
            all_road_faces.append((s, min(xs), max(xs), min(ys), max(ys)))

# Check overlaps between different street roadbeds
overlap_count = 0
for i in range(len(all_road_faces)):
    s1, x1a, x1b, y1a, y1b = all_road_faces[i]
    for j in range(i + 1, len(all_road_faces)):
        s2, x2a, x2b, y2a, y2b = all_road_faces[j]
        if s1 == s2: continue
        ox = min(x1b, x2b) - max(x1a, x2a)
        if ox > 0:
            oy = min(y1b, y2b) - max(y1a, y2a)
            if oy > 0 and ox * oy > 2.0:
                overlap_count += 1
                if overlap_count <= 5:
                    print(f"Overlap between {s1} and {s2}: area={ox*oy:.2f} m²")

print(f"Total roadbed-roadbed face overlaps (> 2.0 m²): {overlap_count}")
