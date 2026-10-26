import bpy

print("\n--- Remaining Objects ---")
for o in bpy.data.objects:
    if 'remaining' in o.name.lower():
        print(o.name, 'colls:', [c.name for c in o.users_collection], 'hide_render:', o.hide_render)

print("\n--- Block Collections Objects ---")
for col in bpy.data.collections:
    if "Block_MTL-VM-" in col.name and "Owned" in col.name:
        for o in col.objects:
            if o.hide_render:
                continue
            if "remaining" in o.name.lower():
                print(f"Col {col.name}: {o.name}")
