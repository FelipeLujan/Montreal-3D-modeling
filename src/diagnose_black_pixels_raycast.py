"""
Map every dark/black pixel cluster in `output/renders/blender_aerial_ortho_core_old_montreal.png`
directly back to World (X, Y) coordinates (since the camera is ORTHO at (120, -80, 1200) with ortho_scale=1250, 2048x2048!)
and raycast straight down in `output/montreal_master.blend` to find the EXACT objects, materials, and Z-fighting pairs!
"""
import os
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(WORKSPACE, "output", "montreal_master.blend")
CORE_RENDER = os.path.join(WORKSPACE, "output", "renders", "blender_aerial_ortho_core_old_montreal.png")


def main():
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

    # Load the rendered image to find black pixels!
    img = bpy.data.images.load(CORE_RENDER, check_existing=False)
    w, h = img.size[0], img.size[1]
    pixels = list(img.pixels)  # flat RGBA float array, bottom-to-top rows

    # Camera parameters for blender_aerial_ortho_core_old_montreal.png:
    # location = (120.0, -80.0, 1200.0), ortho_scale = 1250.0, resolution = 2048x2048
    cam_x, cam_y = 120.0, -80.0
    ortho_scale = 1250.0

    # Let's sample a grid of pixels every 8 pixels and find where RGB < 0.025 (very dark / black)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene

    black_hits = {}
    coplanar_hits = {}

    for py in range(0, h, 8):
        for px in range(0, w, 8):
            idx = (py * w + px) * 4
            r, g, b = pixels[idx], pixels[idx + 1], pixels[idx + 2]
            if r < 0.02 and g < 0.02 and b < 0.02:
                # Convert (px, py) to world (wx, wy)
                wx = cam_x + ((px + 0.5) / w - 0.5) * ortho_scale
                wy = cam_y + ((py + 0.5) / h - 0.5) * ortho_scale
                # Raycast from Z=500 down
                res, loc, norm, face_idx, obj, mat = scene.ray_cast(depsgraph, Vector((wx, wy, 500.0)), Vector((0.0, 0.0, -1.0)))
                if res and obj:
                    mname = "None"
                    if obj.type == 'MESH' and face_idx < len(obj.data.polygons):
                        mi = obj.data.polygons[face_idx].material_index
                        if mi < len(obj.data.materials) and obj.data.materials[mi]:
                            mname = obj.data.materials[mi].name
                    key = (obj.name, mname)
                    black_hits[key] = black_hits.get(key, 0) + 1

                    # Check if there is ANOTHER surface within 0.01m below loc!
                    res2, loc2, norm2, face_idx2, obj2, mat2 = scene.ray_cast(
                        depsgraph, loc + Vector((0.0, 0.0, -0.0002)), Vector((0.0, 0.0, -1.0))
                    )
                    if res2 and obj2 and abs(loc.z - loc2.z) < 0.02:
                        pair = (obj.name, obj2.name, round(loc.z, 3), round(loc2.z, 3))
                        coplanar_hits[pair] = coplanar_hits.get(pair, 0) + 1

    print("\n=== TOP OBJECTS/MATERIALS AT BLACK PIXELS (RGB < 0.02) ===")
    for (oname, mname), cnt in sorted(black_hits.items(), key=lambda x: -x[1])[:35]:
        obj = bpy.data.objects.get(oname)
        uvs = [u.name for u in obj.data.uv_layers] if (obj and obj.type == 'MESH') else []
        print(f"  {cnt:5d} hits | Obj: {oname:48s} | Mat: {mname:34s} | UVs: {uvs}")

    print("\n=== TOP COPLANAR / Z-FIGHTING PAIRS AT BLACK PIXELS (|dz| < 0.02m) ===")
    for (o1, o2, z1, z2), cnt in sorted(coplanar_hits.items(), key=lambda x: -x[1])[:30]:
        print(f"  {cnt:5d} hits | {o1:42s} (z={z1:.3f}) <-> {o2:42s} (z={z2:.3f})")


if __name__ == "__main__":
    main()
