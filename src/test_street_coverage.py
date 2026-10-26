import json, unicodedata, math

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

osm = json.load(open('data/open_data/old_montreal_osm.json', encoding='utf-8'))
nodes = {e['id']: (e['lat'], e['lon']) for e in osm['elements'] if e.get('type') == 'node' and 'lat' in e}

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

targets = ["Côte de la Place d'Armes", 'Rue Saint-François-Xavier', 'Rue Saint-Sulpice']

for s in targets:
    ways = []
    for e in osm['elements']:
        if e.get('type') == 'way' and 'highway' in e.get('tags', {}):
            if norm(s) in norm(e['tags'].get('name', '')):
                pts = [latlon_to_local_xy(*nodes[nid]) for nid in e.get('nodes', []) if nid in nodes]
                if len(pts) >= 2:
                    ways.append(pts)
    pts = [p for w in ways for p in w]
    # If all ways are included, what are min/max X and Y?
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    # With half_w = 4.0m
    min_x, max_x = min(xs) - 4.0, max(xs) + 4.0
    min_y, max_y = min(ys) - 4.0, max(ys) + 4.0
    covered = sum(1 for x, y in pts if min_x - 4.0 <= x <= max_x + 4.0 and min_y - 4.0 <= y <= max_y + 4.0)
    pct = (covered / len(pts)) * 100.0
    print(f"{s}: All points included -> {covered}/{len(pts)} = {pct:.1f}%")
