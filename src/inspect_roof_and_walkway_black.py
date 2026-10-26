import os
import bpy
from mathutils import Vector

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(WORKSPACE, "output", "montreal_master.blend")
CORE_RENDER = os.path.join(WORKSPACE, "output", "renders", "blender_aerial_ortho_core_old_montreal.png")

bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)
depsgraph = bpy.context.evaluated_depsgraph_get()
scene = bpy.context.scene

# 1. Inspect the evaluated roof faces hit by downward rays on the black buildings in MTL-VM-0003!
bmo_blds = [
    "Bldg_188991339_La_Presse",
    "Bldg_102127873_BMO_Stepped_Tower",
    "Bldg_126410862_BMO_BeauxArts_Annex",
    "Bldg_188991337_Building_188991337",
    "Bldg_188991333_Building_188991333",
    "Bldg_339884442_Building_339884442",
    "Bldg_339884443_Building_339884443",
    "Bldg_339884444_Building_339884444",
    "Bldg_339888390_Building_339888390",
]

print("=== 1. INSPECTING ROOF POLYGONS OF BLACK BUILDINGS ===")
for bname in bmo_blds:
    obj = bpy.data.objects.get(bname)
    if not obj:
        continue
    me = obj.data
    # Find polygons near max Z
    max_z = max(v.co.z for v in me.vertices)
    top_polys = [p for p in me.polygons if p.center.z > max_z - 3.0 and abs(p.normal.z) > 0.5]
    # Group by (round(center.z, 3), round(normal.z, 2), mat_name)
    summary = {}
    for p in top_polys:
        mname = me.materials[p.material_index].name if p.material_index < len(me.materials) and me.materials[p.material_index] else "None"
        uv_layer = me.uv_layers.active.data if me.uv_layers.active else None
        uv0 = tuple(round(x, 2) for x in uv_layer[p.loop_start].uv) if uv_layer else None
        k = (round(p.center.z, 3), round(p.normal.z, 2), mname, round(p.area, 1), uv0)
        summary[k] = summary.get(k, 0) + 1
    print(f"  {bname} (max_z={max_z:.2f}, modifiers={[m.name for m in obj.modifiers]}):")
    for k, cnt in sorted(summary.items(), key=lambda x: -x[0][3])[:8]:
        print(f"    cnt={cnt:3d} | z={k[0]:6.3f} | nz={k[1]:5.2f} | mat={k[2]:32s} | area={k[3]:6.1f} | uv0={k[4]}")

# 2. Check Mat_MTL_Slate_Roof_Dark and Mat_MTL_Dark_Bronze_CurtainWall shader nodes!
for mname in ["Mat_MTL_Slate_Roof_Dark", "Mat_MTL_Slate_Roof_Dark.001", "Mat_MTL_Dark_Bronze_CurtainWall", "Mat_MTL_Window_Glass_Dark"]:
    m = bpy.data.materials.get(mname)
    if not m:
        continue
    print(f"\n=== Material {mname} ===")
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE':
            im = n.image
            px = [round(x, 3) for x in im.pixels[:8]] if (im and im.size[0] > 0) else []
            print(f"  TEX_IMAGE {n.name}: img={im.name if im else None}, size={im.size[:] if im else None}, px={px}")
        elif n.type == 'BSDF_PRINCIPLED':
            print(f"  BSDF: BaseColor={list(n.inputs['Base Color'].default_value)}, Met={n.inputs['Metallic'].default_value}, Rough={n.inputs['Roughness'].default_value}")
    for l in m.node_tree.links:
        print(f"  Link: {l.from_node.name}.{l.from_socket.name} -> {l.to_node.name}.{l.to_socket.name}")

# 3. Inspect Parks_47_OSM_Crushed_Stone_And_Paved_Walkways where black pixels hit it!
img = bpy.data.images.load(CORE_RENDER, check_existing=False)
w, h = img.size[0], img.size[1]
pixels = list(img.pixels)
cam_x, cam_y, ortho_scale = 120.0, -80.0, 1250.0

walkway_samples = []
for py in range(0, h, 8):
    for px in range(0, w, 8):
        idx = (py * w + px) * 4
        r, g, b = pixels[idx], pixels[idx + 1], pixels[idx + 2]
        if r < 0.02 and g < 0.02 and b < 0.02:
            wx = cam_x + ((px + 0.5) / w - 0.5) * ortho_scale
            wy = cam_y + ((py + 0.5) / h - 0.5) * ortho_scale
            res, loc, norm, face_idx, obj, mat = scene.ray_cast(depsgraph, Vector((wx, wy, 500.0)), Vector((0.0, 0.0, -1.0)))
            if res and obj and obj.name == "Parks_47_OSM_Crushed_Stone_And_Paved_Walkways":
                # Check ALL faces of Parks_47_OSM_Crushed_Stone_And_Paved_Walkways and Parks_47_OSM_Contoured_Lawns near (wx, wy)!
                walkway_samples.append((wx, wy, loc.z, norm.z, face_idx))

print(f"\n=== 3. WALKWAY BLACK PIXEL SAMPLES (total={len(walkway_samples)}) ===")
wobj = bpy.data.objects.get("Parks_47_OSM_Crushed_Stone_And_Paved_Walkways")
lobj = bpy.data.objects.get("Parks_47_OSM_Contoured_Lawns")
for wx, wy, lz, nz, fidx in walkway_samples[:10]:
    # Count how many faces in wobj have bbox containing (wx, wy)
    w_faces = []
    for p in wobj.data.polygons:
        xs = [wobj.data.vertices[vi].co.x for vi in p.vertices]
        ys = [wobj.data.vertices[vi].co.y for vi in p.vertices]
        if min(xs) <= wx <= max(xs) and min(ys) <= wy <= max(ys):
            zs = [round(wobj.data.vertices[vi].co.z, 4) for vi in p.vertices]
            w_faces.append((p.index, round(p.normal.z, 2), zs))
    print(f"  At ({wx:6.1f}, {wy:6.1f}) hit_z={lz:.4f}, nz={nz:.2f}: wobj overlapping faces={w_faces}")
