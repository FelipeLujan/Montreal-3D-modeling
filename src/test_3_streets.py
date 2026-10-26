import json, unicodedata, math

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

for target in ["Côte de la Place d'Armes", 'Rue Saint-François-Xavier', 'Rue Saint-Sulpice']:
    ways = []
    for e in osm['elements']:
        if e.get('type') == 'way' and 'highway' in e.get('tags', {}):
            if norm(target) in norm(e['tags'].get('name', '')):
                pts = [latlon_to_local_xy(*nodes[nid]) for nid in e.get('nodes', []) if nid in nodes]
                if len(pts) >= 2:
                    ways.append(pts)
    all_pts = [p for w in ways for p in w]
    hw = 4.0
    verts = []
    for pts in ways:
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i+1]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            L = math.hypot(dx, dy)
            if L < 0.1: continue
            nx, ny = -dy / L, dx / L
            verts.extend([
                (p1[0] + nx * hw, p1[1] + ny * hw),
                (p2[0] + nx * hw, p2[1] + ny * hw),
                (p2[0] - nx * hw, p2[1] - ny * hw),
                (p1[0] - nx * hw, p1[1] - ny * hw),
            ])
    x1, x2 = min(v[0] for v in verts), max(v[0] for v in verts)
    y1, y2 = min(v[1] for v in verts), max(v[1] for v in verts)
    covered = sum(1 for x, y in all_pts if x1 - 4.0 <= x <= x2 + 4.0 and y1 - 4.0 <= y <= y2 + 4.0)
    print(f"{target}: {covered}/{len(all_pts)} = {covered/len(all_pts)*100:.1f}% [verts={len(verts)}]")
