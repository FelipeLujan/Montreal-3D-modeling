import bpy
import sys
sys.path.insert(0, "src")
from diversify_facades_master import collect_buildings, build_party_wall_graph

bldgs = collect_buildings()
adj = build_party_wall_graph(bldgs)

# Inspect the 14 conflict pairs
conflicts = []
for i in range(len(bldgs)):
    for j in adj[i]:
        if i < j and bldgs[i]['obj'].material_slots[bldgs[i]['slot_idx']].material.name == bldgs[j]['obj'].material_slots[bldgs[j]['slot_idx']].material.name:
            conflicts.append((bldgs[i], bldgs[j]))

print(f"Total conflicts: {len(conflicts)}")
for b1, b2 in conflicts:
    mat = b1['obj'].material_slots[b1['slot_idx']].material.name
    dx = max(0.0, max(b1['bbox'][0] - b2['bbox'][1], b2['bbox'][0] - b1['bbox'][1]))
    dy = max(0.0, max(b1['bbox'][2] - b2['bbox'][3], b2['bbox'][2] - b1['bbox'][3]))
    d1x = b1['bbox'][1] - b1['bbox'][0]
    d1y = b1['bbox'][3] - b1['bbox'][2]
    d2x = b2['bbox'][1] - b2['bbox'][0]
    d2y = b2['bbox'][3] - b2['bbox'][2]
    print(f"CONFLICT: '{b1['name']}' ({b1['block']}) [size {d1x:.1f}x{d1y:.1f}] vs '{b2['name']}' ({b2['block']}) [size {d2x:.1f}x{d2y:.1f}] -> mat '{mat}', dx={dx:.3f}, dy={dy:.3f}")
