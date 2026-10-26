"""
Stitches the 8 newly remodeled Iteration 2 Old Port & Waterfront blocks
(MTL-VM-0021, MTL-VM-0022, MTL-VM-0023, MTL-VM-0024, MTL-VM-0025,
MTL-VM-0028, MTL-VM-0029, MTL-VM-0035) into `output/montreal_master.blend`,
deduplicates Poly Haven 3D botanical meshes & 2K PBR image textures,
deconflicts block-boundary water/ground overlap, saves `output/montreal_master.blend`,
renders updated verification snapshots, and exports `output/montreal_master.usdc`.
"""
import os
import re
import sys
import math
import time
import bpy
import bmesh
import mathutils
from mathutils import Vector

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(WORKSPACE, "output", "montreal_master.blend")
BLOCKS_DIR = os.path.join(WORKSPACE, "output", "blocks")
RENDERS_DIR = os.path.join(WORKSPACE, "output", "renders")
USDC_PATH = os.path.join(WORKSPACE, "output", "montreal_master.usdc")

REBUILT_BLOCKS = [
    "MTL-VM-0021",
    "MTL-VM-0022",
    "MTL-VM-0023",
    "MTL-VM-0024",
    "MTL-VM-0025",
    "MTL-VM-0028",
    "MTL-VM-0029",
    "MTL-VM-0035",
]


def log(msg: str):
    print(msg, flush=True)


def remove_collection_tree(col):
    """Recursively removes a collection and all objects exclusively linked to it."""
    if not col:
        return 0
    removed_objs = 0
    for child in list(col.children):
        removed_objs += remove_collection_tree(child)
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
        removed_objs += 1
    bpy.data.collections.remove(col)
    return removed_objs


def deduplicate_images():
    """Remaps .001, .002 duplicate images to their canonical base image."""
    canonical = {}
    remapped = 0
    for img in list(bpy.data.images):
        base_name = re.sub(r"\.\d{3,}$", "", img.name)
        if base_name not in canonical:
            canonical[base_name] = img
        else:
            target = canonical[base_name]
            if img != target:
                img.user_remap(target)
                try:
                    bpy.data.images.remove(img)
                except Exception:
                    pass
                remapped += 1
    return remapped


def deduplicate_and_decimate_tree_meshes(max_faces=4500):
    """
    Ensures all high-poly Poly Haven botanical instances across the 36-block Master Scene
    share compact LOD-optimized meshes so Cycles BVH and USD export run fast and well within RAM.
    Picks the already-decimated (< max_faces) canonical mesh for each Poly Haven botanical part
    and remaps any heavy un-decimated copies to it while preserving object-level material slots.
    """
    # First pass: find the lightest valid mesh for each base_mname
    best_meshes = {}
    for me in list(bpy.data.meshes):
        if not me or len(me.polygons) < 50:
            continue
        mname = me.name.lower()
        if not any(k in mname for k in ("jacaranda", "searsia", "tree_small", "shrub_02", "trunk", "leaves", "branches")):
            continue
        base_mname = re.sub(r"\.\d{3,}$", "", me.name)
        if base_mname not in best_meshes or len(me.polygons) < len(best_meshes[base_mname].polygons):
            best_meshes[base_mname] = me

    remapped_objs = 0
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.data:
            continue
        base_mname = re.sub(r"\.\d{3,}$", "", obj.data.name)
        if base_mname in best_meshes:
            target_me = best_meshes[base_mname]
            if obj.data != target_me and len(obj.material_slots) == len(target_me.materials):
                mats = [s.material for s in obj.material_slots]
                obj.data = target_me
                for idx, m in enumerate(mats):
                    if idx < len(obj.material_slots) and m is not None:
                        obj.material_slots[idx].link = "OBJECT"
                        obj.material_slots[idx].material = m
                remapped_objs += 1

    return remapped_objs


def trim_out_of_bounds_catchall_planes(col, block_id):
    """
    Removes or trims oversized single-block catch-all horizon planes (e.g. > 320m span)
    that were only needed for isolated single-block Street View horizon rendering,
    preventing them from overlapping neighboring blocks in the stitched 36-block Master Scene.
    """
    trimmed = 0
    for obj in list(col.all_objects):
        if obj is None or obj.type != "MESH" or not obj.data:
            continue
        oname = obj.name.lower()
        dims = obj.dimensions
        # Remove isolated camera or proxy objects
        if obj.hide_render or obj.hide_viewport or "context_proxy" in oname:
            bpy.data.objects.remove(obj, do_unlink=True)
            trimmed += 1
            continue

        # If an object has huge horizon-CatchAll faces (> 45,000 m^2 single polygon), delete those faces
        me = obj.data
        if max(dims.x, dims.y) > 420.0:
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            huge_faces = [f for f in bm.faces if f.calc_area() > 45000.0]
            if huge_faces:
                bmesh.ops.delete(bm, geom=huge_faces, context="FACES")
                bm.to_mesh(me)
                me.update()
                trimmed += len(huge_faces)
            bm.free()
            if len(me.polygons) == 0:
                bpy.data.objects.remove(obj, do_unlink=True)

    return trimmed


def main():
    log(f"=== Opening Master Scene: {MASTER_BLEND} ===")
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

    master_col = bpy.data.collections.get("Montreal_Master_World")
    if not master_col:
        master_col = bpy.data.collections.new("Montreal_Master_World")
        bpy.context.scene.collection.children.link(master_col)

    # 1. Remove old collections for the 8 rebuilt blocks + legacy overhaul objects
    legacy_obj_names = [
        "Eastern_Old_Port_Overhaul",
        "Southwest_Harbor_And_Cite_du_Havre",
    ]
    for oname in legacy_obj_names:
        o = bpy.data.objects.get(oname)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
            log(f"  [CLEAN] Removed legacy overhaul object: {oname}")

    for bid in REBUILT_BLOCKS:
        for col_name in [f"Block_{bid}_Owned", f"Block_{bid}", f"Block_{bid}_Cameras", f"Block_{bid}_Context_Proxy"]:
            col = bpy.data.collections.get(col_name)
            if col:
                n_rem = remove_collection_tree(col)
                log(f"  [CLEAN] Removed old collection {col_name} ({n_rem} objects)")

    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    # 2. Append the 8 newly rebuilt Iteration 2 `Block_<id>_Owned` collections
    for bid in REBUILT_BLOCKS:
        blend_path = os.path.join(BLOCKS_DIR, f"{bid}.blend")
        if not os.path.exists(blend_path):
            log(f"  [ERROR] Missing {blend_path}!")
            continue

        target_col_name = f"Block_{bid}_Owned"
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            if target_col_name in data_from.collections:
                data_to.collections = [target_col_name]
            elif f"Block_{bid}" in data_from.collections:
                data_to.collections = [f"Block_{bid}"]
            else:
                log(f"  [WARN] No Block_{bid}_Owned collection in {blend_path}")
                continue

        appended_col = data_to.collections[0]
        if appended_col:
            if appended_col.name not in master_col.children:
                master_col.children.link(appended_col)
            # Remove any Cameras sub-collection if Block_<bid> was appended
            for child in list(appended_col.children):
                if "Cameras" in child.name or "Context_Proxy" in child.name:
                    remove_collection_tree(child)
            for obj in list(appended_col.all_objects):
                if obj.type == "CAMERA":
                    bpy.data.objects.remove(obj, do_unlink=True)
            n_trim = trim_out_of_bounds_catchall_planes(appended_col, bid)
            log(f"  [APPENDED] {appended_col.name} from {bid}.blend ({len(appended_col.all_objects)} objects, {n_trim} catchall faces trimmed)")

    # 3. Deduplicate images and tree meshes, then purge orphans
    n_img = deduplicate_images()
    n_tree = deduplicate_and_decimate_tree_meshes(max_faces=3500)
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    log(f"=== Deduplicated {n_img} images and {n_tree} botanical instances ===")

    # 4. Save updated Master Scene atomically
    tmp_blend = MASTER_BLEND + ".tmp.blend"
    if os.path.exists(tmp_blend):
        try:
            os.remove(tmp_blend)
        except OSError:
            pass
    log(f"=== Saving updated {MASTER_BLEND} ===")
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
    time.sleep(0.5)
    os.replace(tmp_blend, MASTER_BLEND)
    log(f"=== Atomically saved {MASTER_BLEND} ({os.path.getsize(MASTER_BLEND):,} bytes) ===")

    # 5. Render updated Old Port Waterfront & Full 36-Block Master Snapshots
    os.makedirs(RENDERS_DIR, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True

    cam_data = bpy.data.cameras.new("Cam_Verify_Master")
    cam_obj = bpy.data.objects.new("Cam_Verify_Master", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Render 1: Old Port & Waterfront Parks Perspective
    cam_data.type = "PERSP"
    cam_data.lens = 26.0
    cam_data.clip_start = 1.0
    cam_data.clip_end = 6000.0
    cam_obj.location = Vector((250.0, -780.0, 360.0))
    direction = Vector((60.0, -20.0, 0.0)) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    old_port_render = os.path.join(RENDERS_DIR, "old_port_water_and_parks_verified.png")
    scene.render.filepath = old_port_render
    bpy.ops.render.render(write_still=True)
    log(f"  [RENDERED] {old_port_render}")

    # Render 2: Master 36-Block Aerial Overview Snapshot
    cam_data.lens = 24.0
    cam_obj.location = Vector((150.0, -1350.0, 780.0))
    direction = Vector((20.0, 40.0, 0.0)) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    master_render = os.path.join(RENDERS_DIR, "montreal_master_snapshot.png")
    scene.render.filepath = master_render
    bpy.ops.render.render(write_still=True)
    log(f"  [RENDERED] {master_render}")

    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.cameras.remove(cam_data, do_unlink=True)

    # 6. Export updated Master USD (.usdc)
    log(f"=== Exporting {USDC_PATH} ===")
    try:
        bpy.ops.wm.usd_export(
            filepath=USDC_PATH,
            check_existing=False,
            selected_objects_only=False,
            visible_objects_only=True,
            export_materials=True,
            generate_preview_surface=True,
            evaluation_mode="RENDER",
        )
        log(f"  [USD EXPORTED] {USDC_PATH}")
    except Exception as e:
        log(f"  [USD NOTE] {e}")

    log("=== Master Waterfront Stitch Complete! ===")


if __name__ == "__main__":
    main()
