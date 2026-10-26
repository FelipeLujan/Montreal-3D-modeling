import json, unicodedata, math
from collections import defaultdict

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

primary_arterials = [
    'Avenue Viger', 'Rue Saint-Antoine', 'Rue Saint-Jacques',
    'Rue Notre-Dame', 'Rue Saint-Paul', 'Rue de la Commune'
]

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

# Primary centerlines with their half_widths
primary_cl = []
for pa in primary_arterials:
    w = 14.0 if "viger" in norm(pa) else 10.5
    hw = w * 0.5
    for pts in street_ways[pa]:
        for i in range(len(pts) - 1):
            primary_cl.append((pts[i], pts[i+1], hw))

def dist_to_segment(p, a, b):
    abx, aby = b[0] - a[0], b[1] - a[1]
    ab_len2 = abx * abx + aby * aby
    if ab_len2 == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1]), 0.0
    t = max(0.0, min(1.0, ((p[0] - a[0]) * abx + (p[1] - a[1]) * aby) / ab_len2))
    proj_x, proj_y = a[0] + t * abx, a[1] + t * aby
    return math.hypot(p[0] - proj_x, p[1] - proj_y), t

for s in REQUIRED_STREETS:
    is_primary = s in primary_arterials
    ways = street_ways[s]
    w = 14.0 if "viger" in norm(s) else (10.5 if is_primary else 8.0)
    hw = w * 0.5

    road_verts = []
    for pts in ways:
        for i in range(len(pts) - 1):
            p1, p2 = list(pts[i]), list(pts[i+1])
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            L = math.hypot(dx, dy)
            if L < 0.1:
                continue
            nx, ny = -dy / L, dx / L

            # If not primary, check clipping against primary arterials
            skip_seg = False
            if not is_primary:
                # Check if p1 or p2 are inside a primary arterial
                d1_min, hw_min1 = 999.0, 5.25
                d2_min, hw_min2 = 999.0, 5.25
                for pa1, pa2, pa_hw in primary_cl:
                    d1, _ = dist_to_segment(p1, pa1, pa2)
                    if d1 < d1_min:
                        d1_min, hw_min1 = d1, pa_hw
                    d2, _ = dist_to_segment(p2, pa1, pa2)
                    if d2 < d2_min:
                        d2_min, hw_min2 = d2, pa_hw

                # If both are deep inside the primary roadbed, skip
                if d1_min < hw_min1 - 0.5 and d2_min < hw_min2 - 0.5:
                    skip_seg = True
                else:
                    # Clip p1 if inside
                    if d1_min < hw_min1:
                        # move p1 towards p2 until dist >= hw_min1
                        for step in range(1, 10):
                            frac = step / 10.0
                            test_p = [p1[0] + frac * dx, p1[1] + frac * dy]
                            d_test = min(dist_to_segment(test_p, pa1, pa2)[0] for pa1, pa2, _ in primary_cl)
                            if d_test >= hw_min1 - 0.2:
                                p1 = test_p
                                break
                    # Clip p2 if inside
                    if d2_min < hw_min2:
                        for step in range(1, 10):
                            frac = step / 10.0
                            test_p = [p2[0] - frac * dx, p2[1] - frac * dy]
                            d_test = min(dist_to_segment(test_p, pa1, pa2)[0] for pa1, pa2, _ in primary_cl)
                            if d_test >= hw_min2 - 0.2:
                                p2 = test_p
                                break

            if skip_seg:
                continue

            # Quad vertices
            v0 = (p1[0] + nx * hw, p1[1] + ny * hw)
            v1 = (p2[0] + nx * hw, p2[1] + ny * hw)
            v2 = (p2[0] - nx * hw, p2[1] - ny * hw)
            v3 = (p1[0] - nx * hw, p1[1] - ny * hw)
            road_verts.extend([v0, v1, v2, v3])

    all_street_pts = [p for w_pts in ways for p in w_pts]
    if road_verts:
        rx1, rx2 = min(v[0] for v in road_verts), max(v[0] for v in road_verts)
        ry1, ry2 = min(v[1] for v in road_verts), max(v[1] for v in road_verts)
        covered = sum(1 for x, y in all_street_pts if rx1 - 4.0 <= x <= rx2 + 4.0 and ry1 - 4.0 <= y <= ry2 + 4.0)
        pct = (covered / len(all_street_pts)) * 100.0
    else:
        covered, pct = 0, 0.0
    status = "PASS" if pct >= 85.0 else "FAIL"
    print(f"{s:28s}: {status:4s} ({covered:3d}/{len(all_street_pts):3d} = {pct:5.1f}%) [verts={len(road_verts)}]")
