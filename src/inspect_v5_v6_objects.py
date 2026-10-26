import bpy
from mathutils import Vector

MASTER_BLEND = r"C:\Users\Felipe\Documents\coding\montreal\output\montreal_master.blend"
bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

print("=== ALL MESH OBJECTS IN OLD PORT CORRIDOR (X=120..800, Y=-450..650) WITH Z_MAX > 2.0 OR LARGE AREA ===")
for obj in sorted(bpy.data.objects, key=lambda o: o.name):
    if obj.type != "MESH" or obj.hide_render:
        continue
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)
    if xmax > 140.0 and xmin < 800.0 and ymax > -450.0 and ymin < 650.0:
        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin
        # Ignore small props/trees unless large
        if "tree" in obj.name.lower() or "shrub" in obj.name.lower() or "lamp" in obj.name.lower() or "hydrant" in obj.name.lower() or "seating" in obj.name.lower() or "planter" in obj.name.lower():
            continue
        mats = [m.name if m else "None" for m in obj.data.materials]
        colls = [c.name for c in obj.users_collection]
        print(f"  {obj.name} (coll={colls}): X=[{xmin:.1f}..{xmax:.1f}], Y=[{ymin:.1f}..{ymax:.1f}], Z=[{zmin:.2f}..{zmax:.2f}] (dx={dx:.1f}, dy={dy:.1f}, dz={dz:.1f}) mats={mats[:5]}")

print("\n=== ALL BASILICA / BLOCK 0001 & 0002 OBJECTS ===")
for obj in sorted(bpy.data.objects, key=lambda o: o.name):
    if obj.type != "MESH" or obj.hide_render:
        continue
    colls = [c.name for c in obj.users_collection]
    if any("0001" in c or "0002" in c for c in colls):
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
        if max(zs) > 15.0:
            print(f"  {obj.name} (coll={colls}): X=[{min(xs):.1f}..{max(xs):.1f}], Y=[{min(ys):.1f}..{max(ys):.1f}], Z=[{min(zs):.1f}..{max(zs):.1f}]")
