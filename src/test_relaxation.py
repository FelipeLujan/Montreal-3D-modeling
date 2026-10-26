"""
src/test_relaxation.py
Test dynamic spatial relaxation for roof deconfliction.
"""
import bpy
import bmesh
import time
import math
from collections import defaultdict
import sys

PROJECT_ROOT = r"C:\Users\Felipe\Documents\coding\montreal"
sys.path.append(PROJECT_ROOT)
from src.audit_zfighting_headless import MontrealZFightingAuditor, EXCLUDED_OBJECT_KEYWORDS

log = lambda *args: print(*args, flush=True)

def simulate_relaxation():
    log("=== SIMULATING DYNAMIC SPATIAL RELAXATION ===")
    
    visible_mesh_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]
    roof_faces = []
    
    for obj in visible_mesh_objs:
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
                    mat_name = mats[p.material_index].lower() if p.material_index < len(mats) else ""
                    # Skip internal glass caps
                    if any(k in mat_name for k in ["glass", "vitre", "fenetre", "frame_green", "frame_dark"]):
                        continue
                    xs = [(mw @ me.vertices[vi].co).x for vi in p.vertices]
                    ys = [(mw @ me.vertices[vi].co).y for vi in p.vertices]
                    # Entry: [obj_name, current_z, min_x, max_x, min_y, max_y, mat_name, poly_index, area, total_offset]
                    roof_faces.append([
                        obj.name, wc.z, min(xs), max(xs), min(ys), max(ys), mat_name, p.index, p.area, 0.0
                    ])

    log(f"Collected {len(roof_faces)} valid candidate roof faces.")

    # Run relaxation passes
    BUCKET_DZ = 0.05
    for pass_num in range(1, 19):
        # Bucket by current Z
        buckets = defaultdict(list)
        for i, f in enumerate(roof_faces):
            b_idx = int(math.floor(f[1] / BUCKET_DZ))
            buckets[b_idx].append(i)
        for b_idx in buckets:
            buckets[b_idx].sort(key=lambda idx: roof_faces[idx][2])

        conflicts_found = 0

        def check_pair(i1, i2):
            nonlocal conflicts_found
            f1, f2 = roof_faces[i1], roof_faces[i2]
            if abs(f1[1] - f2[1]) < 0.05:
                oy = min(f1[5], f2[5]) - max(f1[4], f2[4])
                if oy > 0.0:
                    ox = min(f1[3], f2[3]) - max(f1[2], f2[2])
                    if ox * oy > 1.0:
                        if f1[0] != f2[0] or f1[6] != f2[6]:
                            conflicts_found += 1
                            # Choose which one to offset down:
                            # Roof membrane moves down first; otherwise break symmetry by id
                            is_roof1 = any(k in f1[6] for k in ["roof", "membrane", "slate", "tar", "deck"])
                            is_roof2 = any(k in f2[6] for k in ["roof", "membrane", "slate", "tar", "deck"])
                            if is_roof1 and not is_roof2:
                                target = f1
                            elif is_roof2 and not is_roof1:
                                target = f2
                            elif f1[1] <= f2[1]:
                                target = f1
                            else:
                                target = f2
                            target[1] -= 0.08
                            target[9] += 0.08

        for b_idx, face_indices in buckets.items():
            len_a = len(face_indices)
            for i in range(len_a):
                i1 = face_indices[i]
                for j in range(i + 1, len_a):
                    i2 = face_indices[j]
                    if roof_faces[i2][2] > roof_faces[i1][3]:
                        break
                    check_pair(i1, i2)
            if (b_idx + 1) in buckets:
                for i1 in face_indices:
                    for i2 in buckets[b_idx + 1]:
                        if roof_faces[i2][2] > roof_faces[i1][3]:
                            break
                        if roof_faces[i2][3] < roof_faces[i1][2]:
                            continue
                        check_pair(i1, i2)

        log(f"Pass {pass_num}: {conflicts_found} conflict pairs detected and resolved.")
        if conflicts_found == 0:
            log("Convergence reached! 0 conflicts in spatial index.")
            break

    moved_faces = [f for f in roof_faces if f[9] > 0.0]
    log(f"Total faces modified: {len(moved_faces)} out of {len(roof_faces)}.")

if __name__ == "__main__":
    simulate_relaxation()
