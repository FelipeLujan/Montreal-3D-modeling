import os
import bpy
from mathutils import Vector

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(WORKSPACE, "output", "montreal_master.blend")
CORE_RENDER = os.path.join(WORKSPACE, "output", "renders", "blender_aerial_ortho_core_old_montreal.png")

bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

print("=== 1. CHECK HIDE_VIEWPORT vs HIDE_RENDER MISMATCHES ===")
for col in bpy.data.collections:
    if col.hide_viewport != col.hide_render:
        print(f"  Collection mismatch: {col.name} | hide_viewport={col.hide_viewport}, hide_render={col.hide_render}")

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        hv = obj.hide_get() or obj.hide_viewport
        hr = obj.hide_render
        if hv != hr:
            print(f"  Object mismatch: {obj.name:48s} | hide_viewport/get={hv}, hide_render={hr}")

print("\n=== 2. CHECK CUSTOM NORMALS, COLOR ATTRIBUTES, & OUT-OF-RANGE MAT INDICES ===")
suspect_names = [
    "Parks_47_OSM_Crushed_Stone_And_Paved_Walkways",
    "Parks_47_OSM_Granite_Garden_Curbs",
    "Parks_47_OSM_Contoured_Lawns",
    "Courtyards_District_Block_Plinths",
    "Sidewalks_District_Granite",
    "Roadbeds_District_Asphalt",
    "Bldg_188991339_La_Presse",
    "Bldg_126410862_BMO_BeauxArts_Annex",
    "Bldg_188991337_Building_188991337",
    "Bldg_102127873_BMO_Stepped_Tower",
    "Bldg_188991333_Building_188991333",
]
for name in suspect_names:
    obj = bpy.data.objects.get(name)
    if not obj or obj.type != 'MESH':
        continue
    me = obj.data
    bad_mi = sum(1 for p in me.polygons if p.material_index >= len(me.materials) or me.materials[p.material_index] is None)
    print(f"  {name:48s} | has_custom_normals={me.has_custom_normals} | bad_mat_idx_polys={bad_mi}/{len(me.polygons)} | color_attrs={[a.name for a in me.color_attributes]} | modifiers={[m.name for m in obj.modifiers]} | scale={tuple(round(s,3) for s in obj.scale)}")

print("\n=== 3. FIND WORLD (X, Y) BOUNDING BOXES OF BLACK PIXEL CLUSTERS IN CORE RENDER ===")
img = bpy.data.images.load(CORE_RENDER, check_existing=False)
w, h = img.size[0], img.size[1]
pixels = list(img.pixels)
cam_x, cam_y, ortho_scale = 120.0, -80.0, 1250.0

# Bin black pixels into 25m x 25m world grid cells to see where the black clusters are!
grid_counts = {}
for py in range(0, h, 4):
    for px in range(0, w, 4):
        idx = (py * w + px) * 4
        r, g, b = pixels[idx], pixels[idx + 1], pixels[idx + 2]
        if r < 0.02 and g < 0.02 and b < 0.02:
            wx = cam_x + ((px + 0.5) / w - 0.5) * ortho_scale
            wy = cam_y + ((py + 0.5) / h - 0.5) * ortho_scale
            gx = int(wx // 25) * 25
            gy = int(wy // 25) * 25
            grid_counts[(gx, gy)] = grid_counts.get((gx, gy), 0) + 1

print("Top 25m x 25m world cells with black pixels:")
for (gx, gy), cnt in sorted(grid_counts.items(), key=lambda x: -x[1])[:25]:
    # Find ALL visible-in-render objects whose world XY bbox overlaps [gx, gx+25] x [gy, gy+25]
    overlapping_render_objs = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        x0, x1 = min(v.x for v in bb), max(v.x for v in bb)
        y0, y1 = min(v.y for v in bb), max(v.y for v in bb)
        z0, z1 = min(v.z for v in bb), max(v.z for v in bb)
        if x1 >= gx and x0 <= gx + 25 and y1 >= gy and y0 <= gy + 25 and (x1 - x0) < 600:
            overlapping_render_objs.append(f"{obj.name}(hv={obj.hide_get() or obj.hide_viewport},Z=[{z0:.2f},{z1:.2f}])")
    print(f"  Cell X=[{gx:4d},{gx+25:4d}] Y=[{gy:4d},{gy+25:4d}] ({cnt:4d} black px): {', '.join(overlapping_render_objs[:6])}")
