import bpy
import os

MASTER_BLEND = r"C:\Users\Felipe\Documents\coding\montreal\output\montreal_master.blend"
bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

print("=== NOTRE-DAME BASILICA & PLACE D'ARMES OBJECTS ===")
for obj in bpy.data.objects:
    if obj.type == "MESH" and not obj.hide_render:
        n = obj.name.lower()
        if any(k in n for k in ["basilica", "notre_dame", "place_d_armes", "maisoneuve", "monument"]):
            bb = [obj.matrix_world @ bpy.context.scene.cursor.location for _ in range(1)]
            from mathutils import Vector
            pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
            print(f"  {obj.name}: X=[{min(xs):.1f}..{max(xs):.1f}], Y=[{min(ys):.1f}..{max(ys):.1f}], Z=[{min(zs):.1f}..{max(zs):.1f}]")

print("\n=== V5 / V6 GROUND, PARK, WALKWAY, QUAY & SATELLITE OBJECTS ===")
for obj in bpy.data.objects:
    if obj.type == "MESH" and not obj.hide_render:
        from mathutils import Vector
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
        # Check if low Z (ground/park/street/walkway/quay) and overlaps X=100..700
        if min(zs) < 3.0 and max(zs) < 8.0 and max(xs) > 100.0 and min(xs) < 700.0:
            mats = [m.name if m else "None" for m in obj.data.materials]
            n = obj.name.lower()
            if any(k in n for k in ["park", "grass", "lawn", "walk", "path", "promenade", "quay", "ground", "ortho", "sat", "commune", "road", "sidewalk", "curb", "plaza", "turf", "green"]):
                print(f"  {obj.name} (coll={[c.name for c in obj.users_collection]}): X=[{min(xs):.1f}..{max(xs):.1f}], Y=[{min(ys):.1f}..{max(ys):.1f}], Z=[{min(zs):.2f}..{max(zs):.2f}] mats={mats}")

print("\n=== TREE / FOLIAGE MATERIALS IN SCENE ===")
for mat in bpy.data.materials:
    mn = mat.name.lower()
    if any(k in mn for k in ["leaf", "foliage", "tree", "jacaranda", "bark", "grass", "lawn", "park", "canopy", "shrub"]):
        info = []
        if mat.use_nodes and mat.node_tree:
            for nd in mat.node_tree.nodes:
                if nd.type == "TEX_IMAGE" and nd.image:
                    info.append(f"IMG:{nd.image.name}")
                elif nd.type == "BSDF_PRINCIPLED":
                    bc = nd.inputs["Base Color"].default_value
                    info.append(f"BSDF:({bc[0]:.2f},{bc[1]:.2f},{bc[2]:.2f})")
        print(f"  Mat {mat.name}: {info}")
