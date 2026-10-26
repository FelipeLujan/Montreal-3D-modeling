import bpy
import sys
import os
import math
from collections import defaultdict, Counter

sys.path.insert(0, "src")
from diversify_facades_master import collect_buildings, build_party_wall_graph, FACADE_PALETTE, LANDMARK_PRESETS

bldgs = collect_buildings()
adj = build_party_wall_graph(bldgs)

print(f"Total buildings: {len(bldgs)}")
print(f"Total edges: {sum(len(v) for v in adj.values()) // 2}")

# Find buildings with unusually large bounding boxes
for b in bldgs:
    dx = b['bbox'][1] - b['bbox'][0]
    dy = b['bbox'][3] - b['bbox'][2]
    if dx > 50.0 or dy > 50.0:
        print(f"HUGE DIMS: {b['name']} ({b['block']}): dx={dx:.1f}, dy={dy:.1f}, bbox={b['bbox']}")

# Find vertices far from median in those objects
for b in bldgs:
    dx = b['bbox'][1] - b['bbox'][0]
    dy = b['bbox'][3] - b['bbox'][2]
    if dx > 50.0 or dy > 50.0:
        obj = b['obj']
        xs = [v.co.x for v in obj.data.vertices]
        ys = [v.co.y for v in obj.data.vertices]
        med_x = sorted(xs)[len(xs)//2]
        med_y = sorted(ys)[len(ys)//2]
        outliers = [v for v in obj.data.vertices if abs(v.co.x - med_x) > 30.0 or abs(v.co.y - med_y) > 30.0]
        print(f"  {obj.name}: {len(outliers)} outliers out of {len(obj.data.vertices)} verts (med=({med_x:.1f}, {med_y:.1f}))")
        for ov in outliers[:5]:
            print(f"    outlier vert {ov.index}: co=({ov.co.x:.2f}, {ov.co.y:.2f}, {ov.co.z:.2f})")
