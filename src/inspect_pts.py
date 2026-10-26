import json, unicodedata, math
from collections import defaultdict

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

# Check Saint-Sulpice points
for target in ["Côte de la Place d'Armes", 'Rue Saint-François-Xavier', 'Rue Saint-Sulpice']:
    ways = []
    for e in osm['elements']:
        if e.get('type') == 'way' and 'highway' in e.get('tags', {}):
            if norm(target) in norm(e['tags'].get('name', '')):
                pts = [latlon_to_local_xy(*nodes[nid]) for nid in e.get('nodes', []) if nid in nodes]
                if len(pts) >= 2:
                    ways.append(pts)
    all_pts = [p for w in ways for p in w]
    print(f"=== {target} ({len(all_pts)} pts) ===")
    for i, p in enumerate(all_pts):
        print(f"  pt {i:2d}: ({p[0]:6.1f}, {p[1]:6.1f})")
