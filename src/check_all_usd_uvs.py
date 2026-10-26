import os
from pathlib import Path
from pxr import Usd, UsdGeom

usd_path = Path("output/montreal_master.usdc")
stage = Usd.Stage.Open(str(usd_path))
all_prims = list(stage.Traverse())
mesh_prims = [p for p in all_prims if p.IsA(UsdGeom.Mesh)]

print(f"Total Mesh Prims in USD: {len(mesh_prims)}")

uv_missing = []
uv_present = 0
triplanar_sampled = []

for p in mesh_prims:
    mesh_geom = UsdGeom.Mesh(p)
    primvars_api = UsdGeom.PrimvarsAPI(mesh_geom)
    st_pv = primvars_api.GetPrimvar("st") or primvars_api.GetPrimvar("UVMap")
    if st_pv and st_pv.HasValue():
        uv_present += 1
        val = st_pv.Get()
        if len(triplanar_sampled) < 5 and val and len(val) > 0:
            triplanar_sampled.append((p.GetPath().pathString, len(val), [tuple(round(x, 3) for x in v) for v in val[:4]]))
    else:
        uv_missing.append(p.GetPath().pathString)

print(f"UVs present: {uv_present} / {len(mesh_prims)}")
print(f"UVs missing: {len(uv_missing)}")
if uv_missing:
    print("Missing samples:", uv_missing[:10])

print("\nSampled UV values:")
for name, count, samples in triplanar_sampled:
    print(f"  {name} ({count} UVs): {samples}")
