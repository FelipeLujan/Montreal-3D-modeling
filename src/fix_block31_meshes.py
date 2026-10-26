import bpy
from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
b31_blend = PROJECT_ROOT / "output" / "blocks" / "MTL-VM-0031.blend"

col = bpy.data.collections.get("Block_MTL-VM-0031_Owned")
if not col:
    print("Block 31 collection not found!")
    sys.exit(1)

target_names = [o.name for o in col.objects if o.type == "MESH"]
print(f"Target Block 31 mesh objects to reload: {len(target_names)}")

with bpy.data.libraries.load(str(b31_blend), link=False) as (df, dt):
    available = set(df.objects)
    to_load = [name for name in target_names if name in available]
    dt.objects = to_load

print(f"Loaded {len(dt.objects)} clean objects from {b31_blend.name}")

reloaded_count = 0
import re
for loaded_obj in dt.objects:
    if not loaded_obj:
        continue
    orig_name = re.sub(r"\.\d{3,}$", "", loaded_obj.name)
    target_obj = bpy.data.objects.get(orig_name)
    if target_obj and target_obj != loaded_obj and target_obj.type == "MESH":
        old_data = target_obj.data
        target_obj.data = loaded_obj.data
        reloaded_count += 1
        bpy.data.objects.remove(loaded_obj, do_unlink=True)
        if old_data.users == 0:
            bpy.data.meshes.remove(old_data)
    else:
        bpy.data.objects.remove(loaded_obj, do_unlink=True)

print(f"Successfully reloaded {reloaded_count} clean meshes for Block 31!")

# Now save master blend atomically
master_blend = str(PROJECT_ROOT / "output" / "montreal_master.blend")
tmp_blend = master_blend + ".tmp.blend"
if os.path.exists(tmp_blend):
    try:
        os.remove(tmp_blend)
    except Exception:
        pass
bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
os.replace(tmp_blend, master_blend)
print("Saved clean master blend.")
