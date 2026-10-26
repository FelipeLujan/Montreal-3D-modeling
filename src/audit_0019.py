import bpy
import bmesh
import math

print("=== AUDITING MTL-VM-0019.BLEND FOR Z-FIGHTING ===")
mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH' and not any(k in o.name.lower() for k in ['tree', 'lamp', 'bench', 'statue'])]
print(f"Auditing {len(mesh_objs)} structural mesh objects: {[o.name for o in mesh_objs]}")

roof_polys = []
ground_polys = []

for o in mesh_objs:
    mw = o.matrix_world
    me = o.data
    for p in me.polygons:
        w_norm = mw.to_3x3() @ p.normal
        if w_norm.z > 0.88:
            w_center = mw @ p.center
            pts = [mw @ me.vertices[v].co for v in p.vertices]
            xs = [pt.x for pt in pts]
            ys = [pt.y for pt in pts]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            poly_info = {
                'obj': o.name,
                'center': w_center,
                'z': w_center.z,
                'area': p.area,
                'bbox': (min_x, max_x, min_y, max_y),
                'mat': p.material_index
            }
            if w_center.z > 3.0 and p.area > 1.0:
                roof_polys.append(poly_info)
            elif -0.30 <= w_center.z <= 0.50 and p.area > 2.0:
                ground_polys.append(poly_info)

print(f"Roof polys (>3m, >1m2): {len(roof_polys)}")
print(f"Ground polys (-0.3..0.5m, >2m2): {len(ground_polys)}")

roof_conflicts = 0
for i in range(len(roof_polys)):
    p1 = roof_polys[i]
    b1 = p1['bbox']
    for j in range(i + 1, len(roof_polys)):
        p2 = roof_polys[j]
        b2 = p2['bbox']
        if max(b1[0], b2[0]) < min(b1[1], b2[1]) and max(b1[2], b2[2]) < min(b1[3], b2[3]):
            dx = min(b1[1], b2[1]) - max(b1[0], b2[0])
            dy = min(b1[3], b2[3]) - max(b1[2], b2[2])
            overlap_area = dx * dy
            dz = abs(p1['z'] - p2['z'])
            if overlap_area > 1.0 and dz < 0.05:
                if p1['obj'] != p2['obj'] or p1['mat'] != p2['mat']:
                    print(f"  ROOF CONFLICT: {p1['obj']} vs {p2['obj']}, dz={dz:.4f}m, overlap={overlap_area:.2f}m2")
                    roof_conflicts += 1

ground_conflicts = 0
for i in range(len(ground_polys)):
    p1 = ground_polys[i]
    b1 = p1['bbox']
    for j in range(i + 1, len(ground_polys)):
        p2 = ground_polys[j]
        b2 = p2['bbox']
        if max(b1[0], b2[0]) < min(b1[1], b2[1]) and max(b1[2], b2[2]) < min(b1[3], b2[3]):
            dx = min(b1[1], b2[1]) - max(b1[0], b2[0])
            dy = min(b1[3], b2[3]) - max(b1[2], b2[2])
            overlap_area = dx * dy
            dz = abs(p1['z'] - p2['z'])
            if overlap_area > 2.0 and dz < 0.02:
                if p1['obj'] != p2['obj'] or p1['mat'] != p2['mat']:
                    print(f"  GROUND CONFLICT: {p1['obj']} vs {p2['obj']}, dz={dz:.4f}m, overlap={overlap_area:.2f}m2")
                    ground_conflicts += 1

print(f"TOTAL ROOF CONFLICTS: {roof_conflicts}")
print(f"TOTAL GROUND CONFLICTS: {ground_conflicts}")
assert roof_conflicts == 0, f"Expected 0 roof conflicts, found {roof_conflicts}"
assert ground_conflicts == 0, f"Expected 0 ground conflicts, found {ground_conflicts}"
print(">>> AUDIT PASSED: ZERO Z-FIGHTING CONFLICTS! <<<")
