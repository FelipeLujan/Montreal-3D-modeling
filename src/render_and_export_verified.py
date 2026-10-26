"""
Complete the rename of `montreal_master_saving_tmp.blend@` -> `montreal_master.blend`
(which finished writing all 3,073,221,928 bytes after the surgical non-destructive roof & park walkway fix),
render the 4 verification views, and export `output/montreal_master.usdc`.
"""
import os
import time
import bpy
import mathutils

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(WORKSPACE, "output", "montreal_master.blend")
SAVED_AT_BLEND = os.path.join(WORKSPACE, "output", "montreal_master_saving_tmp.blend@")
SAFE_BACKUP = os.path.join(WORKSPACE, "output", "montreal_master_pre_rooffix.blend")
USDC_PATH = os.path.join(WORKSPACE, "output", "montreal_master.usdc")
RENDERS_DIR = os.path.join(WORKSPACE, "output", "renders")


def main():
    if os.path.exists(SAVED_AT_BLEND) and os.path.getsize(SAVED_AT_BLEND) > 3_000_000_000:
        print(f"[RENAME] Moving completed {SAVED_AT_BLEND} ({os.path.getsize(SAVED_AT_BLEND):,} bytes) -> {MASTER_BLEND}")
        time.sleep(0.5)
        os.replace(SAVED_AT_BLEND, MASTER_BLEND)
    if os.path.exists(SAFE_BACKUP):
        try:
            os.remove(SAFE_BACKUP)
        except OSError:
            pass

    print(f"[RENDER] Opening {MASTER_BLEND}...")
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True

    cam_data = bpy.data.cameras.new("Cam_Verify_Ortho")
    cam_obj = bpy.data.objects.new("Cam_Verify_Ortho", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # A. Orthographic Core Old Montreal & Old Port (render first for fast visual check!)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 1250.0
    cam_data.clip_start = 1.0
    cam_data.clip_end = 5000.0
    cam_obj.location = (120.0, -80.0, 1200.0)
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)
    scene.render.resolution_x = 2048
    scene.render.resolution_y = 2048
    scene.render.filepath = os.path.join(RENDERS_DIR, "blender_aerial_ortho_core_old_montreal.png")
    bpy.ops.render.render(write_still=True)

    # B. Orthographic Full 36-Block Aerial
    cam_data.ortho_scale = 1950.0
    cam_obj.location = (0.0, 0.0, 1200.0)
    scene.render.filepath = os.path.join(RENDERS_DIR, "blender_aerial_ortho_full_36blocks.png")
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
    print("[RENDER] All 4 renders and USD export complete!")


if __name__ == "__main__":
    main()
