import bpy

# Inspect objects in Block 31 collection in montreal_master.blend
col = bpy.data.collections.get("Block_MTL-VM-0031_Owned")
print("Block 31 objects count:", len(col.objects))
for obj in list(col.objects):
    if "189604569" in obj.name or "223785374" in obj.name or "345141612" in obj.name:
        print(f"Object: {obj.name}, verts: {len(obj.data.vertices)}")
        xs = [v.co.x for v in obj.data.vertices]
        ys = [v.co.y for v in obj.data.vertices]
        print(f"  X span: {min(xs):.1f} .. {max(xs):.1f} (range: {max(xs)-min(xs):.1f})")
        print(f"  Y span: {min(ys):.1f} .. {max(ys):.1f} (range: {max(ys)-min(ys):.1f})")
