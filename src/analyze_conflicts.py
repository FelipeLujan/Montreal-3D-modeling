"""
src/analyze_conflicts.py
Detailed analysis of the remaining conflicts in Criterion 1 and Criterion 2.
"""
import sys
import bpy
from pathlib import Path
from collections import defaultdict
import math

# We can reuse the AuditSuite from audit_zfighting_headless
sys.path.append(r"C:\Users\Felipe\Documents\coding\montreal")
from src.audit_zfighting_headless import MontrealZFightingAuditor, EXCLUDED_OBJECT_KEYWORDS

suite = MontrealZFightingAuditor()
suite.inspect_scene_inventory()

# 1. Analyze Criterion 2: Ground
print("\n=== DETAILED ANALYSIS OF CRITERION 2 GROUND CONFLICTS ===")
t0 = bpy.context
ground_faces = []

for obj in suite.visible_mesh_objs:
    nl = obj.name.lower()
    if any(k in nl for k in EXCLUDED_OBJECT_KEYWORDS):
        continue
    me = obj.data
    mw = obj.matrix_world
    rot_3x3 = mw.to_3x3()
    mats = [m.name if m else "None" for m in me.materials]

    for p in me.polygons:
        wn = (rot_3x3 @ p.normal).normalized()
        if wn.z > 0.88 and p.area > 2.0:
            wc = mw @ p.center
            if -0.30 <= wc.z <= 0.50:
                mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                ground_faces.append((
                    obj.name, wc.z, min(xs), max(xs), min(ys), max(ys),
                    mat_name, p.index, p.area
                ))

BUCKET_DZ = 0.02
buckets = defaultdict(list)
for f in ground_faces:
    b_idx = int(math.floor(f[1] / BUCKET_DZ))
    buckets[b_idx].append(f)
for b_idx in buckets:
    buckets[b_idx].sort(key=lambda f: f[2])

ground_conflicts = {}
for b_idx, faces_a in buckets.items():
    len_a = len(faces_a)
    for i in range(len_a):
        f1 = faces_a[i]
        o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
        for j in range(i + 1, len_a):
            f2 = faces_a[j]
            if f2[2] > x1b:
                break
            if abs(z1 - f2[1]) < 0.02:
                oy = min(y1b, f2[5]) - max(y1a, f2[4])
                if oy > 0.0:
                    ox = min(x1b, f2[3]) - f2[2]
                    if ox * oy > 2.0:
                        if o1 != f2[0] or m1 != f2[6]:
                            key = (o1, m1, f2[0], f2[6], round(z1, 3), round(f2[1], 3))
                            ground_conflicts[key] = ground_conflicts.get(key, 0) + 1

    if (b_idx + 1) in buckets:
        faces_b = buckets[b_idx + 1]
        for f1 in faces_a:
            o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
            for f2 in faces_b:
                if f2[2] > x1b:
                    break
                if f2[3] < x1a:
                    continue
                if abs(z1 - f2[1]) < 0.02:
                    oy = min(y1b, f2[5]) - max(y1a, f2[4])
                    if oy > 0.0:
                        ox = min(x1b, f2[3]) - max(x1a, f2[2])
                        if ox * oy > 2.0:
                            if o1 != f2[0] or m1 != f2[6]:
                                key = (o1, m1, f2[0], f2[6], round(z1, 3), round(f2[1], 3))
                                ground_conflicts[key] = ground_conflicts.get(key, 0) + 1

print(f"Total Ground Conflict Groups: {len(ground_conflicts)}")
for k, cnt in sorted(ground_conflicts.items(), key=lambda item: -item[1]):
    print(f"  [{cnt:4d} pairs] {k[0]} [{k[1]}] (z={k[4]}) <==> {k[2]} [{k[3]}] (z={k[5]})")

# 2. Analyze Criterion 1: Roof
print("\n=== DETAILED ANALYSIS OF CRITERION 1 ROOF CONFLICTS ===")
roof_faces = []
for obj in suite.visible_mesh_objs:
    nl = obj.name.lower()
    if any(k in nl for k in EXCLUDED_OBJECT_KEYWORDS):
        continue
    me = obj.data
    mw = obj.matrix_world
    rot_3x3 = mw.to_3x3()
    mats = [m.name if m else "None" for m in me.materials]

    for p in me.polygons:
        wn = (rot_3x3 @ p.normal).normalized()
        if wn.z > 0.88 and p.area > 1.0:
            wc = mw @ p.center
            if wc.z > 3.0:
                mat_name = mats[p.material_index] if p.material_index < len(mats) else "None"
                xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                roof_faces.append((
                    obj.name, wc.z, min(xs), max(xs), min(ys), max(ys),
                    mat_name, p.index, p.area
                ))

BUCKET_DZ = 0.05
buckets = defaultdict(list)
for f in roof_faces:
    b_idx = int(math.floor(f[1] / BUCKET_DZ))
    buckets[b_idx].append(f)
for b_idx in buckets:
    buckets[b_idx].sort(key=lambda f: f[2])

roof_conflicts = {}
intra_object_conflicts = 0
inter_object_conflicts = 0

for b_idx, faces_a in buckets.items():
    len_a = len(faces_a)
    for i in range(len_a):
        f1 = faces_a[i]
        o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
        for j in range(i + 1, len_a):
            f2 = faces_a[j]
            if f2[2] > x1b:
                break
            if abs(z1 - f2[1]) < 0.05:
                oy = min(y1b, f2[5]) - max(y1a, f2[4])
                if oy > 0.0:
                    ox = min(x1b, f2[3]) - f2[2]
                    if ox * oy > 1.0:
                        if o1 != f2[0] or m1 != f2[6]:
                            key = (o1, m1, f2[0], f2[6], round(z1, 2), round(f2[1], 2))
                            roof_conflicts[key] = roof_conflicts.get(key, 0) + 1
                            if o1 == f2[0]:
                                intra_object_conflicts += 1
                            else:
                                inter_object_conflicts += 1

    if (b_idx + 1) in buckets:
        faces_b = buckets[b_idx + 1]
        for f1 in faces_a:
            o1, z1, x1a, x1b, y1a, y1b, m1 = f1[0], f1[1], f1[2], f1[3], f1[4], f1[5], f1[6]
            for f2 in faces_b:
                if f2[2] > x1b:
                    break
                if f2[3] < x1a:
                    continue
                if abs(z1 - f2[1]) < 0.05:
                    oy = min(y1b, f2[5]) - max(y1a, f2[4])
                    if oy > 0.0:
                        ox = min(x1b, f2[3]) - max(x1a, f2[2])
                        if ox * oy > 1.0:
                            if o1 != f2[0] or m1 != f2[6]:
                                key = (o1, m1, f2[0], f2[6], round(z1, 2), round(f2[1], 2))
                                roof_conflicts[key] = roof_conflicts.get(key, 0) + 1
                                if o1 == f2[0]:
                                    intra_object_conflicts += 1
                                else:
                                    inter_object_conflicts += 1

print(f"Total Roof Conflict Groups: {len(roof_conflicts)}")
print(f"Intra-object conflict pairs: {intra_object_conflicts}, Inter-object conflict pairs: {inter_object_conflicts}")

# Show top 30
for k, cnt in sorted(roof_conflicts.items(), key=lambda item: -item[1])[:35]:
    same = "SAME_OBJ" if k[0] == k[2] else "DIFF_OBJ"
    print(f"  [{cnt:4d} pairs] ({same}) {k[0]} [{k[1]}] (z={k[4]}) <==> {k[2]} [{k[3]}] (z={k[5]})")
