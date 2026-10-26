import bpy
import os

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(WORKSPACE, "output", "montreal_master.blend")
bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

target_mats = [
    "Mat_PH_Park_Path_Gravel",
    "Mat_PH_Park_Curb_Granite",
    "Mat_MTL_Sidewalk_Pavers_PH",
    "Mat_MTL_Street_Asphalt_PH",
    "Mat_MTL_Plaza_Pavers_PH",
    "Mat_MTL_Cobblestone_PH",
    "Mat_MTL_Curb_Granite_PH",
]

for mname in target_mats:
    m = bpy.data.materials.get(mname)
    print(f"\n=== Material: {mname} (exists={m is not None}) ===")
    if not m:
        continue
    for n in m.node_tree.nodes:
        print(f"  Node: {n.name} ({n.type})")
        if n.type == 'TEX_IMAGE':
            im = n.image
            print(f"    -> Image: {im.name if im else None}, filepath={im.filepath if im else None}, size={im.size[:] if im else None}, has_data={im.has_data if im else None}, colorspace={im.colorspace_settings.name if im else None}")
            if im and im.size[0] > 0:
                # sample first 4 pixels
                px = list(im.pixels[:16])
                print(f"    -> Pixel sample: {[round(x, 3) for x in px[:8]]}")
        elif n.type == 'BSDF_PRINCIPLED':
            for inp_name in ("Base Color", "Metallic", "Roughness", "IOR", "Alpha"):
                if inp_name in n.inputs:
                    inp = n.inputs[inp_name]
                    val = list(inp.default_value) if hasattr(inp.default_value, "__iter__") else inp.default_value
                    links = [(l.from_node.name, l.from_socket.name) for l in inp.links]
                    print(f"    -> Input {inp_name}: default={val}, links={links}")
    for l in m.node_tree.links:
        print(f"  Link: {l.from_node.name}.{l.from_socket.name} -> {l.to_node.name}.{l.to_socket.name}")

# Also inspect Parks_47_OSM_Crushed_Stone_And_Paved_Walkways UVs and normals and face Zs!
wobj = bpy.data.objects.get("Parks_47_OSM_Crushed_Stone_And_Paved_Walkways")
if wobj:
    me = wobj.data
    uv_layer = me.uv_layers.active.data if me.uv_layers.active else None
    sample_uvs = [tuple(round(x, 3) for x in uv_layer[i].uv) for i in range(min(10, len(uv_layer)))] if uv_layer else []
    print(f"\n=== Walkway Object: {wobj.name} ===")
    print(f"  Sample UVs: {sample_uvs}")
    print(f"  Sample Normals: {[tuple(round(x, 3) for x in p.normal) for p in me.polygons[:8]]}")
    print(f"  Sample Poly Zs: {[round(p.center.z, 4) for p in me.polygons[:15]]}")

# Also inspect Bldg_188991339_La_Presse and Courtyards_District_Block_Plinths
for oname in ["Bldg_188991339_La_Presse", "Bldg_126410862_BMO_BeauxArts_Annex", "Bldg_188991337_Building_188991337", "Courtyards_District_Block_Plinths", "Sidewalks_District_Granite", "Roadbeds_District_Asphalt"]:
    obj = bpy.data.objects.get(oname)
    if obj:
        me = obj.data
        uv_layer = me.uv_layers.active.data if me.uv_layers.active else None
        sample_uvs = [tuple(round(x, 3) for x in uv_layer[i].uv) for i in range(min(6, len(uv_layer)))] if uv_layer else []
        mats = [m.name if m else "None" for m in me.materials]
        up = sum(1 for p in me.polygons if p.normal.z > 0.5)
        down = sum(1 for p in me.polygons if p.normal.z < -0.5)
        print(f"\n=== Object: {oname} | mats={mats} | up={up}, down={down} | sample_uvs={sample_uvs} ===")
