import json, unicodedata, math
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

# Existing roadbed in blend
import bpy
obj = bpy.data.objects.get('Roadbed_Rue_Saint_François_Xavier')
bb = [obj.matrix_world @ v.co for v in obj.data.vertices]
x1, x2 = min(v.x for v in bb), max(v.x for v in bb)
y1, y2 = min(v.y for v in bb), max(v.y for v in bb)
print(f"Existing Roadbed_Rue_Saint_François_Xavier bbox: X=[{x1:.1f}, {x2:.1f}], Y=[{y1:.1f}, {y2:.1f}]")

# Check all OSM ways for Rue Saint-Francois-Xavier
for e in osm['elements']:
    if e.get('type') == 'way' and 'highway' in e.get('tags', {}):
        if 'saint-francois-xavier' in norm(e['tags'].get('name', '')):
            pts = [latlon_to_local_xy(*nodes[nid]) for nid in e.get('nodes', []) if nid in nodes]
            inside = sum(1 for x, y in pts if x1 - 4.0 <= x <= x2 + 4.0 and y1 - 4.0 <= y <= y2 + 4.0)
            print(f"Way {e['id']} (highway={e['tags'].get('highway')}, {len(pts)} pts): covered {inside}/{len(pts)}")
            for i, p in enumerate(pts):
                if not (x1 - 4.0 <= p[0] <= x2 + 4.0 and y1 - 4.0 <= p[1] <= y2 + 4.0):
                    print(f"   UNCOVERED pt {i}: ({p[0]:.1f}, {p[1]:.1f})")
