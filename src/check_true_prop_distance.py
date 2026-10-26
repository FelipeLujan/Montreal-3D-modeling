"""
Detailed polygon-level distance probe for Poly Haven props
Auditor: victory_auditor_3
"""
import bpy
import bmesh
from mathutils import Vector, bvhtree
import math

def check_true_polygon_distance():
    print("Building BVH of actual vertical exterior building walls...")
    bm = bmesh.new()

    # Collect only actual building wall faces (not ground, not street, not roof)
    for obj in bpy.data.objects:
        if obj.type == "MESH" and not obj.hide_render:
            nl = obj.name.lower()
            if any(k in nl for k in ["bldg", "owned"]) and not any(k in nl for k in ["tree", "lamp", "prop", "ground", "quay", "street", "sidewalk", "curb", "water", "vessel", "polyhaven"]):
                me = obj.to_mesh()
                mw = obj.matrix_world
                for poly in me.polygons:
                    # check if vertical face (wall)
                    norm = (mw.to_3x3() @ poly.normal).normalized()
                    if abs(norm.z) < 0.3: # vertical wall
                        v_cos = [mw @ me.vertices[vid].co for vid in poly.vertices]
                        bm.faces.new([bm.verts.new(co) for co in v_cos])
                obj.to_mesh_clear()

    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    print(f"Total building wall faces in BVH: {len(bm.faces)}")
    bvh = bvhtree.BVHTree.FromBMesh(bm)

    ph_objs = [o for o in bpy.data.objects if o.type == 'MESH' and (o.name.startswith("PolyHaven_") or "polyhaven" in o.name.lower())]
    print(f"\nChecking true 3D distance from {len(ph_objs)} Poly Haven props to building walls:")
    
    violations = []
    distances = []
    for o in ph_objs:
        loc = o.matrix_world.translation
        # find nearest point on building wall BVH
        nearest_loc, normal, face_idx, dist = bvh.find_nearest(loc)
        distances.append(dist)
        if dist < 1.8:
            violations.append((o.name, loc, dist))
            print(f"  [VIOLATION <1.8m] {o.name} at ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f}) -> dist to wall = {dist:.2f}m")
        else:
            print(f"  [OK] {o.name} at ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f}) -> dist to wall = {dist:.2f}m")

    print("\n" + "=" * 60)
    print(f"Min true distance to building wall: {min(distances):.2f}m")
    print(f"Total props with dist < 1.8m: {len(violations)} / {len(ph_objs)}")
    print("=" * 60)
    bm.free()

if __name__ == "__main__":
    check_true_polygon_distance()
