"""
Diagnoses:
1. Roof Z-fighting (gray roof vs brick/stone wall top caps or cornice slabs)
2. Ground-level Z-fighting (overlapping ground/asphalt/sidewalk/plaza slabs at Z ~ -0.05..0.25m)
3. Missing street network / sidewalks / curbs across the 15-block Master Scene
"""
import bpy
from mathutils import Vector

print("=== Diagnosing Roofs, Ground Z-Fighting & Street Network in montreal_master.blend ===", flush=True)

master_col = bpy.data.collections.get("Montreal_Master_World")
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.data]
print(f"Total mesh objects in scene: {len(mesh_objs)} (Visible: {sum(1 for o in mesh_objs if not o.hide_render)})", flush=True)

# 1. Inspect all ground-level objects (min_z < 0.5 and max_z < 2.0)
print("\n--- 1. GROUND / STREET / SIDEWALK / PLAZA OBJECTS ---", flush=True)
ground_objs = []
for o in mesh_objs:
    bbox = [o.matrix_world @ Vector(corner) for corner in o.bound_box]
    min_x = min(v.x for v in bbox)
    max_x = max(v.x for v in bbox)
    min_y = min(v.y for v in bbox)
    max_y = max(v.y for v in bbox)
    min_z = min(v.z for v in bbox)
    max_z = max(v.z for v in bbox)
    if max_z < 2.5 and (max_x - min_x > 10.0 or max_y - min_y > 10.0):
        mats = [m.name if m else "None" for m in o.data.materials]
        ground_objs.append((o.name, o.hide_viewport, o.hide_render, round(min_z, 3), round(max_z, 3),
                            round(min_x, 1), round(max_x, 1), round(min_y, 1), round(max_y, 1), len(o.data.polygons), mats[:4]))

for g in sorted(ground_objs, key=lambda x: x[0]):
    print(f"  GROUND: {g[0]:48s} | hide_vp={str(g[1]):5s} hide_rnd={str(g[2]):5s} | Z=[{g[3]:6.3f}, {g[4]:6.3f}] | XY=[{g[5]}..{g[6]}, {g[7]}..{g[8]}] | faces={g[9]:5d} | mats={g[10]}", flush=True)

# 2. Check Roof Z-fighting (upward faces with z > 4.0m)
print("\n--- 2. ROOF Z-FIGHTING (Upward faces z > 4.0m) ---", flush=True)
all_up_faces = []
for obj in mesh_objs:
    if obj.hide_render:
        continue
    nl = obj.name.lower()
    if any(k in nl for k in ("tree", "jacaranda", "shrub", "statue", "lamp", "bench")):
        continue
    me = obj.data
    mw = obj.matrix_world
    mats = [m.name if m else "None" for m in me.materials]
    for p in me.polygons:
        if p.normal.z > 0.88 and p.area > 3.0:
            wc = mw @ p.center
            if wc.z > 4.0:
                mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                all_up_faces.append((obj.name, wc.z, min(xs), max(xs), min(ys), max(ys), mat_name, p.index, p.area))

print(f"Collected {len(all_up_faces)} upward roof polygons (z > 4.0m, area > 3.0m2).", flush=True)

roof_conflicts_by_pair = {}
for i in range(len(all_up_faces)):
    o1, z1, x1a, x1b, y1a, y1b, m1, idx1, a1 = all_up_faces[i]
    for j in range(i + 1, len(all_up_faces)):
        o2, z2, x2a, x2b, y2a, y2b, m2, idx2, a2 = all_up_faces[j]
        if abs(z1 - z2) < 0.08:
            ox = max(0.0, min(x1b, x2b) - max(x1a, x2a))
            oy = max(0.0, min(y1b, y2b) - max(y1a, y2a))
            if ox * oy > 3.0 and (o1 != o2 or m1 != m2):
                key = (o1, m1, o2, m2, round(z1, 2), round(z2, 2))
                roof_conflicts_by_pair[key] = roof_conflicts_by_pair.get(key, 0) + 1

print(f"Found {len(roof_conflicts_by_pair)} distinct roof Z-fighting groups:", flush=True)
for k, cnt in sorted(roof_conflicts_by_pair.items(), key=lambda x: -x[1])[:60]:
    print(f"  ROOF CONFLICT ({cnt:3d} faces): {k[0]} [{k[1]}] (z={k[4]}) <-> {k[2]} [{k[3]}] (z={k[5]})", flush=True)

# 3. Check Ground Z-fighting (upward faces with -0.25 <= z <= 0.45 and area > 5.0m2)
print("\n--- 3. GROUND Z-FIGHTING (Upward faces -0.25 <= z <= 0.45m) ---", flush=True)
ground_up_faces = []
for obj in mesh_objs:
    if obj.hide_render:
        continue
    nl = obj.name.lower()
    if any(k in nl for k in ("tree", "jacaranda", "shrub", "statue", "lamp", "bench")):
        continue
    me = obj.data
    mw = obj.matrix_world
    mats = [m.name if m else "None" for m in me.materials]
    for p in me.polygons:
        if p.normal.z > 0.88 and p.area > 6.0:
            wc = mw @ p.center
            if -0.25 <= wc.z <= 0.45:
                mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                ground_up_faces.append((obj.name, wc.z, min(xs), max(xs), min(ys), max(ys), mat_name, p.index, p.area))

print(f"Collected {len(ground_up_faces)} upward ground polygons (-0.25..0.45m, area > 6.0m2).", flush=True)
ground_conflicts = {}
for i in range(len(ground_up_faces)):
    o1, z1, x1a, x1b, y1a, y1b, m1, idx1, a1 = ground_up_faces[i]
    for j in range(i + 1, len(ground_up_faces)):
        o2, z2, x2a, x2b, y2a, y2b, m2, idx2, a2 = ground_up_faces[j]
        if abs(z1 - z2) < 0.04:
            ox = max(0.0, min(x1b, x2b) - max(x1a, x2a))
            oy = max(0.0, min(y1b, y2b) - max(y1a, y2a))
            if ox * oy > 10.0 and (o1 != o2 or m1 != m2):
                key = (o1, m1, o2, m2, round(z1, 3), round(z2, 3))
                ground_conflicts[key] = ground_conflicts.get(key, 0) + 1

for k, cnt in sorted(ground_conflicts.items(), key=lambda x: -x[1])[:60]:
    print(f"  GROUND CONFLICT ({cnt:3d} faces): {k[0]} [{k[1]}] (z={k[4]}) <-> {k[2]} [{k[3]}] (z={k[5]})", flush=True)
