import sys, os
import bpy, bmesh
from mathutils import Vector, geometry

sys.path.insert(0, os.path.abspath("."))
from tests.adversarial.stress_test_boundary_and_coplanar import (
    MontrealBoundaryAndCoplanarChallenger,
    min_distance_to_polygon_boundary_2d
)

target_block_ids = [f"MTL-VM-{i:04d}" for i in range(16, 26)]
for block_id in target_block_ids:
    col = None
    for c in bpy.data.collections:
        if c.name.startswith(f"Block_{block_id}") and ("_Owned" in c.name or "Place_dArmes" in c.name):
            col = c
            break
    if not col: continue

    for obj in col.all_objects:
        if obj.type != "MESH" or not obj.data or obj.hide_render: continue
        nl = obj.name.lower()
        if any(p in nl for p in ("tree", "jacaranda", "shrub", "statue", "lamp", "bench", "grate", "signage", "furniture", "bollard")): continue
        if any(k in nl for k in ("ground", "curb", "sidewalk", "asphalt", "cobble", "quays", "pier", "dock", "water", "marina", "waterfront", "promenade", "rail", "boardwalk", "beach", "grass", "ramparts")): continue

        me = obj.data
        mw = obj.matrix_world
        bb = [mw @ Vector(c) for c in obj.bound_box]
        min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
        min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)
        min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
        height = max_z - min_z
        if height < 4.5 or (max_x - min_x) < 4.0 or (max_y - min_y) < 4.0: continue

        wall_verts_2d = []
        for v in me.vertices:
            wv = mw @ v.co
            if min_z <= wv.z <= min_z + height * 0.75:
                wall_verts_2d.append((wv.x, wv.y))
        if len(wall_verts_2d) < 3:
            wall_verts_2d = [( (mw @ v.co).x, (mw @ v.co).y ) for v in me.vertices]
        try:
            hull_indices = geometry.convex_hull_2d(wall_verts_2d)
            hull_pts = [wall_verts_2d[idx] for idx in hull_indices]
        except Exception:
            continue

        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        modified = False
        for f in bm.faces:
            if f.normal.z > 0.95 and f.calc_area() > 0.08:
                wc_z = (mw @ f.calc_center_median()).z
                mat = obj.material_slots[f.material_index].name if f.material_index < len(obj.material_slots) else ""
                is_roof = any(k in mat.lower() for k in ("roof", "slate", "tin", "membrane", "flat", "copper"))
                if wc_z >= min_z + 0.40 * height or is_roof:
                    verts = list(f.verts)
                    v_dists = []
                    for v in verts:
                        wv = mw @ v.co
                        d = min_distance_to_polygon_boundary_2d(wv.x, wv.y, hull_pts)
                        v_dists.append((d, v))
                    v_dists.sort(key=lambda item: item[0])
                    min_d = v_dists[0][0]
                    max_d = v_dists[-1][0]
                    width = max(0.15, max_d - min_d)
                    drop = max(0.09, 0.45 * width)
                    if min_d < 0.12:
                        if len(verts) == 4:
                            v_dists[0][1].co.z -= drop
                            v_dists[1][1].co.z -= drop
                        else:
                            for idx in range(len(verts) // 2):
                                v_dists[idx][1].co.z -= drop
                        modified = True

        if modified:
            bm.to_mesh(me)
            me.update()
        bm.free()

tester = MontrealBoundaryAndCoplanarChallenger()
p3 = tester.test_roof_membrane_insets_blocks_16_to_25()
print(f"TEST 3 RESULT: {p3}")
