"""
Independent Victory Verification Script for Montreal 3D Reconstruction
Auditor: victory_auditor_3
Mandate: Verify water nodes, Z=-2.20m, 13 Poly Haven 3D models, clearances, and canal carving.
"""
import sys
import bpy
import bmesh
from mathutils import Vector, bvhtree
import math

def run_probe():
    print("=" * 80)
    print("INDEPENDENT VICTORY AUDITOR FORENSIC PROBE")
    print("=" * 80)

    # 1. WATER MESH OBJECTS & ELEVATION
    print("\n--- 1. WATER MESH OBJECTS & ELEVATION ---")
    water_objs = [o for o in bpy.data.objects if o.type == 'MESH' and any(k in o.name.lower() for k in ['water', 'basin', 'river', 'canal'])]
    print(f"Found {len(water_objs)} water-related mesh objects:")
    for o in water_objs:
        zs = [ (o.matrix_world @ v.co).z for v in o.data.vertices ]
        min_z = min(zs) if zs else 0
        max_z = max(zs) if zs else 0
        avg_z = sum(zs)/len(zs) if zs else 0
        mats = [m.name for m in o.data.materials if m]
        print(f"  - {o.name:<45} | Z: min={min_z:.2f}, max={max_z:.2f}, avg={avg_z:.2f} | Mats: {mats}")

    # 2. WATER MATERIAL NODE GRAPH INSPECTION
    print("\n--- 2. WATER MATERIAL NODE GRAPH INSPECTION ---")
    water_mats = [m for m in bpy.data.materials if any(k in m.name.lower() for k in ['water', 'basin', 'river'])]
    print(f"Found {len(water_mats)} water materials:")
    for m in water_mats:
        print(f"  Material: {m.name} (use_nodes={m.use_nodes})")
        if m.use_nodes and m.node_tree:
            tex_nodes = [n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE']
            print(f"    ShaderNodeTexImage count: {len(tex_nodes)}")
            for tn in tex_nodes:
                img_name = tn.image.name if tn.image else "NONE"
                img_path = tn.image.filepath if tn.image else "NONE"
                print(f"      Image Node: {tn.name} -> Image: {img_name} ({img_path})")

    # 3. FACADE MATERIAL NODE GRAPH INSPECTION
    print("\n--- 3. FACADE MATERIAL NODE GRAPH INSPECTION ---")
    facade_mats = [m for m in bpy.data.materials if m.name.startswith("Mat_MTL_") and not any(k in m.name.lower() for k in ['water', 'asphalt', 'cobble', 'grass', 'roof', 'slate', 'glass', 'rust', 'curb', 'sidewalk'])]
    print(f"Found {len(facade_mats)} facade materials:")
    for m in facade_mats[:15]:
        tex_count = len([n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE']) if (m.use_nodes and m.node_tree) else 0
        images = [n.image.name for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image] if (m.use_nodes and m.node_tree) else []
        print(f"  - {m.name:<32} | TexImage nodes: {tex_count} | Images: {images}")

    # 4. POLY HAVEN 3D MODELS IN SCENE
    print("\n--- 4. POLY HAVEN 3D MODELS IN SCENE ---")
    ph_objs = [o for o in bpy.data.objects if o.type == 'MESH' and (o.name.startswith("PolyHaven_") or "polyhaven" in o.name.lower())]
    print(f"Found {len(ph_objs)} Poly Haven instanced objects:")
    ph_types = {}
    for o in ph_objs:
        parts = o.name.split("_")
        prefix = "_".join(parts[:-1]) if parts[-1].isdigit() else o.name
        ph_types[prefix] = ph_types.get(prefix, 0) + 1
    print(f"Total Unique Poly Haven Model Types: {len(ph_types)} / 13")
    for k, v in ph_types.items():
        print(f"  {k}: {v} instances")

    # Check Clearance to Buildings (True Polygon BVH)
    print("\n--- 5. PROP-TO-BUILDING CLEARANCE CHECK (Threshold: >= 1.8m) ---")
    print("Building BVH of actual vertical exterior building walls...")
    bm = bmesh.new()
    for obj in bpy.data.objects:
        if obj.type == "MESH" and not obj.hide_render:
            nl = obj.name.lower()
            if any(k in nl for k in ["bldg", "owned"]) and not any(k in nl for k in ["tree", "lamp", "prop", "ground", "quay", "street", "sidewalk", "curb", "water", "vessel", "polyhaven"]):
                me = obj.to_mesh()
                mw = obj.matrix_world
                for poly in me.polygons:
                    norm = (mw.to_3x3() @ poly.normal).normalized()
                    if abs(norm.z) < 0.3:  # vertical wall
                        v_cos = [mw @ me.vertices[vid].co for vid in poly.vertices]
                        bm.faces.new([bm.verts.new(co) for co in v_cos])
                obj.to_mesh_clear()

    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    print(f"Total building wall faces in BVH: {len(bm.faces)}")
    bvh = bvhtree.BVHTree.FromBMesh(bm)

    min_clearance = float('inf')
    clearance_violations = 0
    for o in ph_objs:
        loc = o.matrix_world.translation
        nearest_loc, normal, face_idx, dist = bvh.find_nearest(loc)
        if dist < min_clearance:
            min_clearance = dist
        if dist < 1.8:
            clearance_violations += 1
            print(f"  [CLEARANCE VIOLATION <1.8m] {o.name} at ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f}) -> dist to wall = {dist:.2f}m")
        else:
            print(f"  [OK] {o.name} at ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f}) -> dist to wall = {dist:.2f}m")

    print(f"Min Observed Prop-to-Building Clearance: {min_clearance:.2f}m")
    print(f"Total Clearance Violations (< 1.8m): {clearance_violations}")
    bm.free()

    # 6. CANAL & EMBANKMENT VERIFICATION
    print("\n--- 6. CANAL & EMBANKMENT OBJECTS ---")
    canal_objs = [o for o in bpy.data.objects if any(k in o.name.lower() for k in ['canal', 'lock', 'ecluse', 'spillway', 'quay', 'embankment'])]
    print(f"Found {len(canal_objs)} canal/lock/embankment/quay objects:")
    for o in canal_objs[:20]:
        print(f"  - {o.name:<45} | Type: {o.type} | Verts: {len(o.data.vertices) if o.type=='MESH' else 'N/A'}")

    print("\n" + "=" * 80)
    print("PROBE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_probe()
