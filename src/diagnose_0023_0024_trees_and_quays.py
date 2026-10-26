import bpy
from mathutils import Vector

MASTER_BLEND = r"C:\Users\Felipe\Documents\coding\montreal\output\montreal_master.blend"
bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

print("=== TREE OBJECTS & MATERIALS IN 0023, 0024, 0025 ===")
for cname in ("Block_MTL-VM-0023_Owned", "Block_MTL-VM-0024_Owned", "Block_MTL-VM-0025_Owned"):
    c = bpy.data.collections.get(cname)
    if not c:
        continue
    mats_used = set()
    tree_count = 0
    for o in c.objects:
        if o.type == "MESH" and not o.hide_render and any(k in o.name.lower() for k in ("tree", "jacaranda", "searsia", "shrub", "foliage")):
            tree_count += 1
            for m in o.data.materials:
                if m:
                    mats_used.add(m.name)
    print(f"  {cname}: {tree_count} tree meshes, materials={sorted(mats_used)}")
    for mname in sorted(mats_used):
        m = bpy.data.materials.get(mname)
        if m and m.use_nodes and m.node_tree:
            nodes_desc = []
            for nd in m.node_tree.nodes:
                if nd.type == "TEX_IMAGE":
                    nodes_desc.append(f"TEX_IMAGE({nd.image.name if nd.image else 'None'})")
                elif nd.type == "BSDF_PRINCIPLED":
                    bc = nd.inputs["Base Color"].default_value
                    nodes_desc.append(f"BSDF(bc=({bc[0]:.2f},{bc[1]:.2f},{bc[2]:.2f}))")
                else:
                    nodes_desc.append(nd.type)
            links_desc = [f"{l.from_node.type}.{l.from_socket.name}->{l.to_node.type}.{l.to_socket.name}" for l in m.node_tree.links]
            print(f"    Mat {mname}: nodes={nodes_desc} links={links_desc}")

print("\n=== OBJECTS IN 0023, 0024, 0025 WITH Z NEAR GROUND ===")
for cname in ("Block_MTL-VM-0023_Owned", "Block_MTL-VM-0024_Owned", "Block_MTL-VM-0025_Owned"):
    c = bpy.data.collections.get(cname)
    if not c:
        continue
    for o in c.objects:
        if o.type == "MESH" and not o.hide_render:
            pts = [o.matrix_world @ Vector(v) for v in o.bound_box]
            xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
            if max(xs) - min(xs) > 15.0:
                print(f"  {cname} / {o.name}: X=[{min(xs):.1f}..{max(xs):.1f}], Y=[{min(ys):.1f}..{max(ys):.1f}], Z=[{min(zs):.2f}..{max(zs):.2f}] mats={[m.name if m else None for m in o.data.materials]}")
