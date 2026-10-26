import sys
from pathlib import Path
import json, unicodedata, math
from collections import defaultdict
import bpy
from mathutils import Vector

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
osm = json.load(open(PROJECT_ROOT / 'data/open_data/old_montreal_osm.json', encoding='utf-8'))
nodes = {e['id']: (e['lat'], e['lon']) for e in osm['elements'] if e.get('type') == 'node' and 'lat' in e}

MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0

def latlon_to_local_xy(lat, lon):
    dlat = math.radians(lat - MASTER_ORIGIN_LAT)
    dlon = math.radians(lon - MASTER_ORIGIN_LON)
    mean_lat = math.radians(MASTER_ORIGIN_LAT)
    return dlon * EARTH_RADIUS_M * math.cos(mean_lat), dlat * EARTH_RADIUS_M

# Collect building bboxes exactly as challenger_fast_probe.py does
visible_meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]
bldg_objs = [
    o for o in visible_meshes
    if not any(k in o.name.lower() for k in ("street", "road", "curb", "sidewalk", "asphalt", "cobble", "plaza", "tree", "lamp", "bench", "grate", "sign"))
]
bldg_bboxes = []
for b in bldg_objs:
    bb = [b.matrix_world @ Vector(c) for c in b.bound_box]
    min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
    min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)
    min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
    if max_z > 3.0 and (max_x - min_x) > 3.0 and (max_y - min_y) > 3.0:
        bldg_bboxes.append((b.name, min_x, max_x, min_y, max_y))

print(f"Collected {len(bldg_bboxes)} building bounding boxes.")

# Also collect 2D polygon footprints from dossiers
dossier_bldg_polys = []
for d_dir in (PROJECT_ROOT / "data" / "blocks").iterdir():
    d_file = d_dir / "dossier.json"
    if d_file.exists():
        d = json.load(open(d_file, encoding='utf-8'))
        for b in d.get("osm_features", {}).get("buildings", []):
            coords = b.get("coords_xy", [])
            if len(coords) >= 3:
                dossier_bldg_polys.append(coords)

print(f"Collected {len(dossier_bldg_polys)} building polygon footprints from dossiers.")

def point_in_bbox(x, y, margin=0.3):
    for _, bx1, bx2, by1, by2 in bldg_bboxes:
        if bx1 + margin <= x <= bx2 - margin and by1 + margin <= y <= by2 - margin:
            return True
    return False

def point_in_poly(x, y, poly):
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

# Test current sidewalk in blend
cur_sw = bpy.data.objects.get("District_Sidewalks_Raised")
penetrated = set()
if cur_sw:
    mw = cur_sw.matrix_world
    for p in cur_sw.data.polygons:
        wc = mw @ p.center
        for bname, bx1, bx2, by1, by2 in bldg_bboxes:
            if bx1 + 0.5 <= wc.x <= bx2 - 0.5 and by1 + 0.5 <= wc.y <= by2 - 0.5:
                penetrated.add(bname)
print(f"Current blend penetrations: {len(penetrated)}")
