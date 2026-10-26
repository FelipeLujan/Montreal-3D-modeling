import bpy

for col in bpy.data.collections:
    print(f"Col: {col.name} ({len(col.objects)} objs)")
