import os
import sys
import math
import re
from collections import defaultdict, Counter
import bpy
from mathutils import Vector

print("=" * 80)
print("INDEPENDENT AUDIT FOR MTL-VM-0026")
print("=" * 80)

# 1. Collection & Proxy Hygiene
print("\n[AUDIT 1] Collection & Proxy Hygiene")
cols = [c.name for c in bpy.data.collections]
print("Collections:", cols)
assert len(cols) == 1 and cols[0] == "Block_MTL-VM-0026_Owned", f"Unexpected collections: {cols}"

hidden_count = sum(1 for o in bpy.data.objects if o.hide_render or o.hide_viewport)
print("Hidden objects count:", hidden_count)
assert hidden_count == 0, f"Found {hidden_count} hidden objects!"

proxy_count = sum(1 for o in bpy.data.objects if "proxy" in o.name.lower() or "context" in o.name.lower())
print("Proxy objects count:", proxy_count)
assert proxy_count == 0, f"Found {proxy_count} proxy objects!"

# 2. Objects Overview
print("\n[AUDIT 2] Objects Overview")
print(f"Total objects in scene: {len(bpy.data.objects)}")
bldgs = [o for o in bpy.data.objects if o.name.startswith("MTL_Owned_") and not any(k in o.name.lower() for k in ["ground", "streetlamp", "tree", "bench", "obelisk"])]
print(f"Building objects: {len(bldgs)}")
assert len(bldgs) == 35, f"Expected 35 primary buildings, found {len(bldgs)}"

# 3. Facade Diversity
print("\n[AUDIT 3] Facade Material Diversity")
NON_WALL = ("roof", "glass", "window", "door", "iron", "steel", "bronze", "copper", "shutter", "sign", "trim", "spandrel", "cornice", "parapet", "grass", "lawn", "solar", "asphalt", "cobble", "sidewalk")
mat_per_bldg = {}
for b in bldgs:
    wall_mat = None
    for s in b.material_slots:
        if s.material and not any(k in s.material.name.lower() for k in NON_WALL):
            wall_mat = re.sub(r"\.\d{3,}$", "", s.material.name)
            break
    mat_per_bldg[b.name] = wall_mat

counts = Counter(mat_per_bldg.values())
print("Material distribution across 35 buildings:")
max_share = 0.0
for m, c in counts.most_common():
    pct = c / len(bldgs) * 100.0
    if pct > max_share:
        max_share = pct
    print(f"  {m:<32}: {c} ({pct:.1f}%)")

print(f"Max single material share: {max_share:.1f}% (cap: <= 20.0%)")
assert max_share <= 20.01, f"Material exceeded 20% cap ({max_share:.1f}%)"

# 4. Party-Wall Adjacency & Material Conflict Check
print("\n[AUDIT 4] Party-Wall Adjacency Check")
conflicts = 0
adj_pairs = 0
b_list = list(bldgs)
for i in range(len(b_list)):
    b1 = b_list[i]
    bb1 = [b1.matrix_world @ Vector(c) for c in b1.bound_box]
    for j in range(i + 1, len(b_list)):
        b2 = b_list[j]
        bb2 = [b2.matrix_world @ Vector(c) for c in b2.bound_box]
        z_overlap = min(max(v.z for v in bb1), max(v.z for v in bb2)) - max(min(v.z for v in bb1), min(v.z for v in bb2))
        if z_overlap < 1.0:
            continue
        dx = max(0.0, max(min(v.x for v in bb1) - max(v.x for v in bb2), min(v.x for v in bb2) - max(v.x for v in bb1)))
        dy = max(0.0, max(min(v.y for v in bb1) - max(v.y for v in bb2), min(v.y for v in bb2) - max(v.y for v in bb1)))
        if dx <= 0.45 and dy <= 0.45:
            adj_pairs += 1
            if mat_per_bldg[b1.name] == mat_per_bldg[b2.name]:
                conflicts += 1
                print(f"  CONFLICT: {b1.name} and {b2.name} share {mat_per_bldg[b1.name]}")

print(f"Total adjacent party-wall pairs: {adj_pairs}")
print(f"Party-wall identical texture conflicts: {conflicts}")
assert conflicts == 0, f"Found {conflicts} party-wall conflicts!"

# 5. Fast Spatial-Hash Coplanar Z-Fighting Audit (Props Excluded)
print("\n[AUDIT 5] Programmatic Coplanar Z-Fighting Audit")
grid = defaultdict(list)
cell_size = 2.0

for obj in bpy.data.objects:
    if obj.type != "MESH" or not obj.data:
        continue
    # Exclude foliage and prop objects from roof/ground audit
    if any(k in obj.name.lower() for k in ["tree", "streetlamp", "bench"]):
        continue

    mw = obj.matrix_world
    scale_xy = mw.to_scale().x * mw.to_scale().y
    for poly in obj.data.polygons:
        norm_w = (mw.to_3x3() @ poly.normal).normalized()
        if norm_w.z > 0.88:
            area_w = poly.area * scale_xy
            if area_w < 0.5:
                continue
            center_w = mw @ poly.center
            cell_x = int(math.floor(center_w.x / cell_size))
            cell_y = int(math.floor(center_w.y / cell_size))
            item = {
                "obj": obj.name,
                "z": center_w.z,
                "x": center_w.x,
                "y": center_w.y,
                "area": area_w
            }
            # Add to cell and neighbors
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    grid[(cell_x + dx, cell_y + dy)].append(item)

checked_pairs = set()
roof_conflicts = 0
ground_conflicts = 0

for cell, faces in grid.items():
    n_f = len(faces)
    if n_f < 2:
        continue
    for i in range(n_f):
        f1 = faces[i]
        for j in range(i + 1, n_f):
            f2 = faces[j]
            if f1["obj"] == f2["obj"]:
                continue
            pair_key = (min(id(f1), id(f2)), max(id(f1), id(f2)))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            dz = abs(f1["z"] - f2["z"])
            dist_xy = math.hypot(f1["x"] - f2["x"], f1["y"] - f2["y"])

            # Roof check: z > 3.0m, area > 1.0, |dz| < 0.05m, xy dist < 1.0m
            if f1["z"] > 3.0 and f2["z"] > 3.0 and f1["area"] > 1.0 and f2["area"] > 1.0:
                if dz < 0.05 and dist_xy < 1.0:
                    roof_conflicts += 1
                    print(f"  Roof Z-fight: {f1['obj']} vs {f2['obj']} (dz={dz:.3f}m, dist={dist_xy:.3f}m)")

            # Ground check: -0.30 <= z <= 0.50, area > 2.0, |dz| < 0.02m, xy dist < 1.0m
            if -0.30 <= f1["z"] <= 0.50 and -0.30 <= f2["z"] <= 0.50 and f1["area"] > 2.0 and f2["area"] > 2.0:
                if dz < 0.02 and dist_xy < 1.0:
                    ground_conflicts += 1
                    print(f"  Ground Z-fight: {f1['obj']} vs {f2['obj']} (dz={dz:.3f}m, dist={dist_xy:.3f}m)")

print(f"Checked face pairs: {len(checked_pairs)}")
print(f"Roof Z-fighting conflicts: {roof_conflicts}")
print(f"Ground Z-fighting conflicts: {ground_conflicts}")
assert roof_conflicts == 0, f"Found {roof_conflicts} roof conflicts"
assert ground_conflicts == 0, f"Found {ground_conflicts} ground conflicts"

print("\n" + "=" * 80)
print("ALL VERIFICATION AUDITS PASSED WITH ZERO CONFLICTS!")
print("=" * 80)
