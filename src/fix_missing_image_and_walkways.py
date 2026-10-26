import os
import bmesh
import bpy
import mathutils

BLEND_PATH = r"C:\Users\Felipe\Documents\coding\montreal\output\montreal_master.blend"
USDC_PATH = r"C:\Users\Felipe\Documents\coding\montreal\output\montreal_master.usdc"
POLYHAVEN_DIR = r"C:\Users\Felipe\Documents\coding\montreal\assets\polyhaven"
RENDERS_DIR = r"C:\Users\Felipe\Documents\coding\montreal\output\renders"

def find_ph_file(*candidates):
    files = {f.lower(): os.path.join(POLYHAVEN_DIR, f) for f in os.listdir(POLYHAVEN_DIR)}
    for c in candidates:
        if c.lower() in files:
            return files[c.lower()]
    for k, v in files.items():
        if "diffuse" in k or "diff" in k:
            return v
    return list(files.values())[0]

FALLBACK_DIFF = find_ph_file("sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_diff_2k.jpg", "stone_tile_wall_Diffuse_2k.jpg")
FALLBACK_ROUGH = find_ph_file("sandstone_blocks_05_Rough_2k.jpg", "sandstone_blocks_05_rough_2k.jpg", "stone_tile_wall_Rough_2k.jpg")
FALLBACK_NOR = find_ph_file("sandstone_blocks_05_nor_gl_2k.jpg", "stone_tile_wall_nor_gl_2k.jpg")
COBBLE_DIFF = find_ph_file("cobblestone_floor_08_Diffuse_2k.jpg", "cobblestone_floor_08_diff_2k.jpg", "pavement_02_Diffuse_2k.jpg")
COBBLE_ROUGH = find_ph_file("cobblestone_floor_08_Rough_2k.jpg", "cobblestone_floor_08_rough_2k.jpg", "pavement_02_Rough_2k.jpg")
COBBLE_NOR = find_ph_file("cobblestone_floor_08_nor_gl_2k.jpg", "pavement_02_nor_gl_2k.jpg")

img_sand_diff = bpy.data.images.load(FALLBACK_DIFF, check_existing=False)
img_sand_diff.colorspace_settings.name = 'sRGB'
img_cobble_diff = bpy.data.images.load(COBBLE_DIFF, check_existing=False)
img_cobble_diff.colorspace_settings.name = 'sRGB'
img_cobble_rough = bpy.data.images.load(COBBLE_ROUGH, check_existing=False)
img_cobble_rough.colorspace_settings.name = 'Non-Color'
img_cobble_nor = bpy.data.images.load(COBBLE_NOR, check_existing=False)
img_cobble_nor.colorspace_settings.name = 'Non-Color'

def rebuild_stone_paver_mat(mat, use_sandstone=True):
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.78
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])

    td = nt.nodes.new("ShaderNodeTexImage")
    td.image = img_sand_diff if use_sandstone else img_cobble_diff
    nt.links.new(mp.outputs["Vector"], td.inputs["Vector"])
    nt.links.new(td.outputs["Color"], bsdf.inputs["Base Color"])

    tr = nt.nodes.new("ShaderNodeTexImage")
    tr.image = img_cobble_rough
    nt.links.new(mp.outputs["Vector"], tr.inputs["Vector"])
    nt.links.new(tr.outputs["Color"], bsdf.inputs["Roughness"])

    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = img_cobble_nor
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.55
    nt.links.new(mp.outputs["Vector"], tn.inputs["Vector"])
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])

for mname, use_sand in [("Mat_PH_Park_Path_Gravel", True), ("Mat_PH_Park_Curb_Granite", False)]:
    m = bpy.data.materials.get(mname)
    if not m:
        m = bpy.data.materials.new(mname)
    rebuild_stone_paver_mat(m, use_sandstone=use_sand)
    print(f"  -> Rebuilt '{mname}' with valid Poly Haven 2K stone/cobble PBR")

# Fix UVs and normals on Parks_47_OSM_Crushed_Stone_And_Paved_Walkways and Parks_47_OSM_Granite_Perimeter_Curbs
for wname, mat_name in [
    ("Parks_47_OSM_Crushed_Stone_And_Paved_Walkways", "Mat_PH_Park_Path_Gravel"),
    ("Parks_47_OSM_Granite_Perimeter_Curbs", "Mat_PH_Park_Curb_Granite"),
]:
    wobj = bpy.data.objects.get(wname)
    if wobj and wobj.type == 'MESH':
        me = wobj.data
        target_mat = bpy.data.materials.get(mat_name)
        me.materials.clear()
        me.materials.append(target_mat)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            f.material_index = 0
            if f.normal.z < 0:
                f.normal_flip()
        uv_layer = bm.loops.layers.uv.verify()
        for f in bm.faces:
            for loop in f.loops:
                co = wobj.matrix_world @ loop.vert.co
                loop[uv_layer].uv = (co.x * 0.25, co.y * 0.25)
        bm.to_mesh(me)
        me.update()
        bm.free()
        print(f"  -> Fixed +Z normals, world UVs, and material '{mat_name}' on {wname}")

# Also fix any empty TEX_IMAGE node across all materials without unpacking existing images
for mat in bpy.data.materials:
    if not mat.node_tree:
        continue
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            if node.image is None or (node.image.packed_file is None and not node.image.filepath):
                print(f"  [EMPTY TEX_IMAGE] in '{mat.name}' -> assigning sandstone_blocks_05_Diffuse_2k.jpg")
                node.image = img_sand_diff

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print(f"[SAVE] Saved {BLEND_PATH}")

# Render the 4 views
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True

cam_data = bpy.data.cameras.new("Cam_Verify_Ortho")
cam_obj = bpy.data.objects.new("Cam_Verify_Ortho", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

# A. Orthographic Full 36-Block Aerial
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 1950.0
cam_data.clip_start = 1.0
cam_data.clip_end = 5000.0
cam_obj.location = (0.0, 0.0, 1200.0)
cam_obj.rotation_euler = (0.0, 0.0, 0.0)
scene.render.resolution_x = 2048
scene.render.resolution_y = 2048
scene.render.filepath = os.path.join(RENDERS_DIR, "blender_aerial_ortho_full_36blocks.png")
bpy.ops.render.render(write_still=True)

# B. Orthographic Core Old Montreal & Old Port
cam_data.ortho_scale = 1250.0
cam_obj.location = (120.0, -80.0, 1200.0)
scene.render.filepath = os.path.join(RENDERS_DIR, "blender_aerial_ortho_core_old_montreal.png")
bpy.ops.render.render(write_still=True)

# C. Perspective Old Port & Waterfront Parks
cam_data.type = 'PERSP'
cam_data.lens = 26.0
cam_obj.location = (250.0, -780.0, 360.0)
direction = mathutils.Vector((60.0, -20.0, 0.0)) - cam_obj.location
cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.filepath = os.path.join(RENDERS_DIR, "old_port_water_and_parks_verified.png")
bpy.ops.render.render(write_still=True)

# D. Master 36-Block Overview Snapshot
cam_data.lens = 24.0
cam_obj.location = (150.0, -1350.0, 780.0)
direction = mathutils.Vector((20.0, 40.0, 0.0)) - cam_obj.location
cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = os.path.join(RENDERS_DIR, "montreal_master_snapshot.png")
bpy.ops.render.render(write_still=True)

bpy.data.objects.remove(cam_obj, do_unlink=True)
bpy.data.cameras.remove(cam_data, do_unlink=True)

# Export USD (.usdc)
print(f"[USD] Exporting {USDC_PATH}...")
bpy.ops.wm.usd_export(
    filepath=USDC_PATH,
    check_existing=False,
    selected_objects_only=False,
    export_materials=True,
    generate_preview_surface=True,
    evaluation_mode='RENDER',
)
print(f"[USD] Exported {USDC_PATH} ({os.path.getsize(USDC_PATH)/(1024*1024):.1f} MB)")
