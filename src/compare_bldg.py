import bpy
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
b31_blend = PROJECT_ROOT / "output" / "blocks" / "MTL-VM-0031.blend"

# In master
m_obj = bpy.data.objects.get("Bldg_189604569_Shophouse_189604569")
print("MASTER OBJ:")
print("  loc:", m_obj.location)
print("  mat_world:", m_obj.matrix_world)
print("  mesh verts:", len(m_obj.data.vertices))
xs = [v.co.x for v in m_obj.data.vertices]
ys = [v.co.y for v in m_obj.data.vertices]
print(f"  raw co: X={min(xs):.2f}..{max(xs):.2f}, Y={min(ys):.2f}..{max(ys):.2f}")

# Load from 0031.blend
with bpy.data.libraries.load(str(b31_blend), link=False) as (df, dt):
    dt.objects = ["Bldg_189604569_Shophouse_189604569"]

src_obj = dt.objects[0]
print("0031 OBJ:")
print("  loc:", src_obj.location)
print("  mat_world:", src_obj.matrix_world)
print("  mesh verts:", len(src_obj.data.vertices))
s_xs = [v.co.x for v in src_obj.data.vertices]
s_ys = [v.co.y for v in src_obj.data.vertices]
print(f"  raw co: X={min(s_xs):.2f}..{max(s_xs):.2f}, Y={min(s_ys):.2f}..{max(s_ys):.2f}")

# Find outliers
outliers = [v for v in m_obj.data.vertices if v.co.x > -200 or v.co.y > 700 or v.co.y < 300]
print(f"MASTER has {len(outliers)} outlier vertices out of {len(m_obj.data.vertices)}")
for ov in outliers[:5]:
    print(f"  vert {ov.index}: co=({ov.co.x:.2f}, {ov.co.y:.2f}, {ov.co.z:.2f})")
