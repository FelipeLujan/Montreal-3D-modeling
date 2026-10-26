import os
import bmesh
import bpy

BLEND_PATH = r"C:\Users\Felipe\Documents\coding\montreal\output\montreal_master.blend"
USDC_PATH = r"C:\Users\Felipe\Documents\coding\montreal\output\montreal_master.usdc"
POLYHAVEN_DIR = r"C:\Users\Felipe\Documents\coding\montreal\assets\polyhaven"
RENDERS_DIR = r"C:\Users\Felipe\Documents\coding\montreal\output\renders"

print(f"[FIX] Inspecting {BLEND_PATH}...")

# 1. Check what objects have vertices at X > 820, Y > 150, Z in [-2.6, 0.5] (the white sawtooth strip in the eastern river channel)
sawtooth_candidates = []
for obj in list(bpy.data.objects):
    if obj.type != 'MESH' or obj.hide_render:
        continue
    me = obj.data
    if not me or len(me.vertices) == 0:
        continue
    # Quick bbox check
    xs = [v.co.x for v in me.vertices[:min(len(me.vertices), 500)]]
    ys = [v.co.y for v in me.vertices[:min(len(me.vertices), 500)]]
    if any(x > 800 for x in xs) or "Foam" in obj.name or "Shoreline" in obj.name or "Water" in obj.name or "Wave" in obj.name:
        mats = [m.name if m else "None" for m in me.materials]
        print(f"  [Candidate East/Water Object] {obj.name}: verts={len(me.vertices)}, mats={mats}")

# Remove any dedicated Foam / Wake / Shoreline strip objects OR faces in the river channel that use foam/white material
for obj in list(bpy.data.objects):
    if obj.type != 'MESH':
        continue
    if any(k in obj.name for k in ("Foam", "Shoreline_Strip", "Wake_Strip")):
        print(f"  -> Removing foam object: {obj.name}")
        bpy.data.objects.remove(obj, do_unlink=True)
        continue
    me = obj.data
    if not me:
        continue
    # Check if any material slot is Foam
    foam_slots = [idx for idx, m in enumerate(me.materials) if m and ("Foam" in m.name or "Wake" in m.name)]
    if foam_slots or obj.name == "Water_District_StLawrence_And_Canals":
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        to_del = []
        for f in bm.faces:
            if f.material_index in foam_slots or f.material_index > 0:
                to_del.append(f)
            elif obj.name == "Water_District_StLawrence_And_Canals":
                # Also check if there are narrow sawtooth strip faces along the eastern edge (x > 850, y > 100)
                c = f.calc_center_median()
                if c.x > 850 and c.y > 100 and f.calc_area() < 600.0:
                    to_del.append(f)
        if to_del:
            bmesh.ops.delete(bm, geom=to_del, context='FACES')
            bm.to_mesh(me)
            me.update()
            print(f"  -> Deleted {len(to_del)} foam/sawtooth faces from {obj.name}")
        bm.free()
        # Keep only slot 0 on Water_District_StLawrence_And_Canals
        if obj.name == "Water_District_StLawrence_And_Canals" and len(me.materials) > 1:
            while len(me.materials) > 1:
                me.materials.pop(index=len(me.materials) - 1)

# Also check if any object at X > 850, Y > 150 has a white/bright material or sawtooth geometry
for obj in list(bpy.data.objects):
    if obj.type != 'MESH' or obj.hide_render:
        continue
    me = obj.data
    if not me or len(me.vertices) == 0:
        continue
    # Check if vertices exist in X in [850, 990], Y in [200, 950]
    east_verts = [v for v in me.vertices if v.co.x > 850 and v.co.y > 200 and -3.0 <= v.co.z <= 2.0]
    if east_verts and obj.name != "Water_District_StLawrence_And_Canals":
        mats = [m.name if m else "None" for m in me.materials]
        print(f"  [East Channel Mesh] {obj.name}: {len(east_verts)} east verts, z={[round(v.co.z,2) for v in east_verts[:5]]}, mats={mats}")
        # If this is Terrain_District_Master_Plinth or QuayWalls protruding into the eastern river channel (X > 850, Y > 150), check!
        if obj.name in ("QuayWalls_District_Granite_Embankments", "Terrain_District_Master_Plinth"):
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            # In the eastern river channel (East of Cité du Havre / Old Port, X > 830 and Y > 50, or outer boundary X > 960),
            # QuayWalls should NOT wrap around the outer water boundary at X = +975 or Y = +975!
            bad_faces = []
            for f in bm.faces:
                c = f.calc_center_median()
                # Outer water boundary is at X > 830, Y > -200 (the river channel itself!)
                if obj.name == "QuayWalls_District_Granite_Embankments":
                    if c.x > 820 or c.y < -950 or c.y > 950:
                        bad_faces.append(f)
                elif obj.name == "Terrain_District_Master_Plinth":
                    if c.x > 820 and c.y > 50 and f.normal.z > -0.5:
                        bad_faces.append(f)
            if bad_faces:
                bmesh.ops.delete(bm, geom=bad_faces, context='FACES')
                bm.to_mesh(me)
                me.update()
                print(f"  -> Removed {len(bad_faces)} outer-river-boundary faces from {obj.name}!")
            bm.free()

# 2. Diagnose & Fix why Parks_47_OSM_Contoured_Lawns rendered black!
park_lawn_names = [
    "Parks_47_OSM_Contoured_Lawns",
    "Parc_Dieppe_Lawn",
    "Lock1_Park_Green_West",
    "Lock1_Park_Green_East",
    "Bonsecours_Island_Green",
    "QuaiHorloge_Green_Lawn",
]

# Load a fresh, unpacked sRGB image for leafy_grass_Diffuse_2k.jpg
grass_diff_path = os.path.join(POLYHAVEN_DIR, "leafy_grass_Diffuse_2k.jpg")
grass_nor_path = os.path.join(POLYHAVEN_DIR, "leafy_grass_nor_gl_2k.jpg")
grass_rough_path = os.path.join(POLYHAVEN_DIR, "leafy_grass_rough_2k.jpg")

# Remove any corrupted/packed image instances of leafy_grass so Blender reads fresh from disk
for img in list(bpy.data.images):
    if "leafy_grass" in img.name.lower() or (img.filepath and "leafy_grass" in img.filepath.lower()):
        print(f"  -> Purging old image data-block: {img.name} (packed={img.packed_file is not None})")
        bpy.data.images.remove(img)

img_grass_diff = bpy.data.images.load(grass_diff_path, check_existing=False)
img_grass_diff.colorspace_settings.name = 'sRGB'
img_grass_nor = bpy.data.images.load(grass_nor_path, check_existing=False)
img_grass_nor.colorspace_settings.name = 'Non-Color'
img_grass_rough = bpy.data.images.load(grass_rough_path, check_existing=False)
img_grass_rough.colorspace_settings.name = 'Non-Color'

print(f"  -> Loaded fresh grass diffuse: size={img_grass_diff.size[:]}, colorspace={img_grass_diff.colorspace_settings.name}")

def rebuild_grass_material(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.82
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.22
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Use Object/Generated coordinates fallback if UV is missing or zero, OR UVMap if valid
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    # If we use Object coordinates scaled by 0.20 (1 repeat every 5m), it works whether UVs exist or not!
    # Wait: for USD export (generate_preview_surface=True), USD exporter expects UVMap connected or standard TexImage!
    # So let's make sure EVERY grass mesh has valid world-space UVs AND connect UV -> TexImage!
    tex_diff = nt.nodes.new("ShaderNodeTexImage")
    tex_diff.image = img_grass_diff
    nt.links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], tex_diff.inputs["Vector"])
    nt.links.new(tex_diff.outputs["Color"], bsdf.inputs["Base Color"])

    tex_rough = nt.nodes.new("ShaderNodeTexImage")
    tex_rough.image = img_grass_rough
    nt.links.new(mapping.outputs["Vector"], tex_rough.inputs["Vector"])
    nt.links.new(tex_rough.outputs["Color"], bsdf.inputs["Roughness"])

    tex_nor = nt.nodes.new("ShaderNodeTexImage")
    tex_nor.image = img_grass_nor
    nor_map = nt.nodes.new("ShaderNodeNormalMap")
    nor_map.inputs["Strength"].default_value = 0.65
    nt.links.new(mapping.outputs["Vector"], tex_nor.inputs["Vector"])
    nt.links.new(tex_nor.outputs["Color"], nor_map.inputs["Color"])
    nt.links.new(nor_map.outputs["Normal"], bsdf.inputs["Normal"])

# Rebuild all grass/lawn/foliage materials
for mat in bpy.data.materials:
    ml = mat.name.lower()
    if any(k in ml for k in ("grass", "lawn", "park_turf", "turf", "dieppe_lawn")):
        print(f"  -> Rebuilding grass material: {mat.name}")
        rebuild_grass_material(mat)

# Ensure Mat_MTL_Grass_Lawn_PBR exists
grass_mat = bpy.data.materials.get("Mat_MTL_Grass_Lawn_PBR")
if not grass_mat:
    grass_mat = bpy.data.materials.new("Mat_MTL_Grass_Lawn_PBR")
    rebuild_grass_material(grass_mat)

# Now inspect Parks_47_OSM_Contoured_Lawns and all park lawn objects:
# Check why Parks_47_OSM_Contoured_Lawns was black:
# Could it be intersecting/underneath Terrain_District_Master_Plinth or Courtyards_District_Block_Plinths or having -Z normals or missing UVs?
for obj in bpy.data.objects:
    if obj.type != 'MESH' or obj.hide_render:
        continue
    if obj.name in park_lawn_names or "Lawn" in obj.name or "Park_Green" in obj.name or "Grass" in obj.name:
        me = obj.data
        print(f"  [Park Mesh] {obj.name}: verts={len(me.vertices)}, faces={len(me.polygons)}, uv_layers={[u.name for u in me.uv_layers]}, mats={[m.name if m else None for m in me.materials]}")
        # Ensure grass_mat is assigned to all faces
        if len(me.materials) == 0:
            me.materials.append(grass_mat)
        else:
            for idx in range(len(me.materials)):
                me.materials[idx] = grass_mat
        for p in me.polygons:
            p.material_index = 0

        # Fix normals to point +Z and generate clean world-space UVs (1 tile per 4.0m)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            if f.normal.z < 0:
                f.normal_flip()
            # Ensure top faces of Parks_47_OSM_Contoured_Lawns are at Z >= +0.22m so they sit cleanly above all block plinths (+0.16m) and sidewalks (+0.15m)!
        if obj.name == "Parks_47_OSM_Contoured_Lawns":
            for v in bm.verts:
                if v.co.z > 0.02:
                    v.co.z = max(v.co.z, 0.22)
        uv_layer = bm.loops.layers.uv.verify()
        for f in bm.faces:
            for loop in f.loops:
                co = obj.matrix_world @ loop.vert.co
                loop[uv_layer].uv = (co.x * 0.25, co.y * 0.25)
        bm.to_mesh(me)
        me.update()
        bm.free()
        print(f"    -> Fixed +Z normals, Z elevation (>=0.22m), world UVs, and assigned Mat_MTL_Grass_Lawn_PBR on {obj.name}")

# Also elevate Parks_47_OSM_Crushed_Stone_And_Paved_Walkways and Parks_47_OSM_Granite_Perimeter_Curbs slightly so they sit at +0.23m..+0.25m above the +0.22m lawn
for wname, target_z in [("Parks_47_OSM_Crushed_Stone_And_Paved_Walkways", 0.235), ("Parks_47_OSM_Granite_Perimeter_Curbs", 0.26)]:
    wobj = bpy.data.objects.get(wname)
    if wobj and wobj.type == 'MESH':
        bm = bmesh.new()
        bm.from_mesh(wobj.data)
        for v in bm.verts:
            if v.co.z > 0.05:
                v.co.z = max(v.co.z, target_z)
        bm.to_mesh(wobj.data)
        wobj.data.update()
        bm.free()
        print(f"    -> Elevated {wname} top vertices to {target_z}m")

# Also check if any object is overlapping Parks_47_OSM_Contoured_Lawns from above!
# Let's check what objects exist at Place d'Youville, Champ-de-Mars, Square Victoria, Bassin Bonsecours
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print(f"[FIX] Saved updated {BLEND_PATH}")

# 3. Render the 4 verification views to verify green parks and clean eastern river channel
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True

# A. Orthographic Full 36-Block Aerial
cam_data = bpy.data.cameras.new("Cam_Verify_Ortho")
cam_obj = bpy.data.objects.new("Cam_Verify_Ortho", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

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
import mathutils
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

# 4. Export USD (.usdc) with Blender 5.2 supported parameters
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
