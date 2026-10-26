import bpy
import bmesh
from mathutils import Vector
from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")

print("=" * 80)
print("FIXING FINAL 5 GROUND CONFLICTS")
print("=" * 80)

# 1. Ground_Quays_Water_MTL-VM-0036: delete shallow water faces at Z > -1.0m
g36 = bpy.data.objects.get("Ground_Quays_Water_MTL-VM-0036")
if g36 and g36.data:
    bm = bmesh.new()
    bm.from_mesh(g36.data)
    bm.faces.ensure_lookup_table()
    mats = [m.name if m else "" for m in g36.data.materials]
    to_delete = []
    for f in bm.faces:
        mat_name = mats[f.material_index] if f.material_index < len(mats) else ""
        if "water" in mat_name.lower():
            c = f.calc_center_median()
            if c.z > -1.0:
                to_delete.append(f)
    print(f"Ground_Quays_Water_MTL-VM-0036: deleting {len(to_delete)} shallow water faces.")
    bmesh.ops.delete(bm, geom=to_delete, context="FACES")
    bm.to_mesh(g36.data)
    bm.free()
    g36.data.update()

# 2. Peninsula_Ground_Quays_Park_And_Water: lower cobblestone faces under Habitat 67 plaza
pen = bpy.data.objects.get("Peninsula_Ground_Quays_Park_And_Water")
if pen and pen.data:
    bm = bmesh.new()
    bm.from_mesh(pen.data)
    bm.faces.ensure_lookup_table()
    mats = [m.name if m else "" for m in pen.data.materials]
    lowered = 0
    for f in bm.faces:
        c = f.calc_center_median()
        # Habitat 67 footprint: X in [950..1150], Y in [-650..-450]
        if 950 <= c.x <= 1150 and -650 <= c.y <= -450:
            if 0.04 <= c.z <= 0.08:
                for v in f.verts:
                    if v.co.z > 0.04:
                        v.co.z -= 0.04
                lowered += 1
    print(f"Peninsula_Ground_Quays_Park_And_Water: lowered {lowered} faces under Habitat 67.")
    bm.to_mesh(pen.data)
    bm.free()
    pen.data.update()

# 3. Ground_District_Solid_Collider: lower faces overlapping Quays Marina MTL-VM-0023 and Plage de l'Horloge
col = bpy.data.objects.get("Ground_District_Solid_Collider")
if col and col.data:
    bm = bmesh.new()
    bm.from_mesh(col.data)
    bm.faces.ensure_lookup_table()
    lowered = 0
    for f in bm.faces:
        if f.normal.z > 0.88:
            c = f.calc_center_median()
            # Marina MTL-VM-0023: X in [340..800], Y in [50..420]
            # Plage Horloge: X in [600..750], Y in [600..900]
            in_marina = (340 <= c.x <= 800 and 50 <= c.y <= 420)
            in_plage = (600 <= c.x <= 800 and 600 <= c.y <= 950)
            if (in_marina or in_plage) and abs(c.z - (-0.12)) < 0.02:
                for v in f.verts:
                    if abs(v.co.z - (-0.12)) < 0.02:
                        v.co.z = -0.16
                lowered += 1
    print(f"Ground_District_Solid_Collider: lowered {lowered} top faces in Marina & Plage de l'Horloge.")
    bm.to_mesh(col.data)
    bm.free()
    col.data.update()

# Save master blend atomically
master_blend = str(PROJECT_ROOT / "output" / "montreal_master.blend")
tmp_blend = master_blend + ".tmp.blend"
if os.path.exists(tmp_blend):
    try:
        os.remove(tmp_blend)
    except Exception:
        pass
bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
os.replace(tmp_blend, master_blend)
print("Saved cleaned master blend.")
