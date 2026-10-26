import os
import math
from pathlib import Path

def audit_uv_unwrapping():
    import bpy
    import bmesh

    print("=" * 70)
    print("AUDITING UV UNWRAPPING IN BLENDER MASTER SCENE")
    print("=" * 70)

    visible_mesh_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.data and not o.hide_render]
    total_visible = len(visible_mesh_objs)
    print(f"Total visible mesh objects: {total_visible}")

    no_uv_objs = []
    skipped_assets = []
    cube_size_deviations = []
    
    skip_keywords = ("jacaranda", "statue", "street_lamp", "seating", "bench_ph", "master_street_bench")

    checked_meshes = set()
    total_checked = 0

    for obj in visible_mesh_objs:
        mesh = obj.data
        if mesh.name in checked_meshes:
            continue
        checked_meshes.add(mesh.name)

        name_low = f"{obj.name.lower()} {mesh.name.lower()}"
        if any(k in name_low for k in skip_keywords):
            skipped_assets.append(obj.name)
            continue

        if not mesh.uv_layers:
            no_uv_objs.append(obj.name)
            continue

        total_checked += 1
        uv_layer_name = mesh.uv_layers.active.name

        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm_uv = bm.loops.layers.uv.get(uv_layer_name) or bm.loops.layers.uv.verify()

        role = obj.get("ue5_collision_role", "UNKNOWN")

        face_scales = []
        for face in bm.faces[:15]:
            if face.calc_area() < 0.01:
                continue
            if len(face.verts) < 2:
                continue
            v0, v1 = face.verts[0], face.verts[1]
            world_d3d = ((obj.matrix_world @ v0.co) - (obj.matrix_world @ v1.co)).length
            
            l0 = [l for l in face.loops if l.vert == v0][0]
            l1 = [l for l in face.loops if l.vert == v1][0]
            uv0 = l0[bm_uv].uv
            uv1 = l1[bm_uv].uv
            duv = math.hypot(uv0.x - uv1.x, uv0.y - uv1.y)

            if duv > 1e-4 and world_d3d > 1e-4:
                eff_tile_size = world_d3d / duv
                face_scales.append(eff_tile_size)

        bm.free()

        if face_scales:
            avg_tile = sum(face_scales) / len(face_scales)
            diff_35 = abs(avg_tile - 3.5)
            diff_40 = abs(avg_tile - 4.0)
            if diff_35 > 0.8 and diff_40 > 0.8:
                cube_size_deviations.append((obj.name, role, round(avg_tile, 2)))

    print(f"Total unique procedural meshes checked: {total_checked}")
    print(f"Objects skipped as pre-unwrapped assets: {len(skipped_assets)}")
    print(f"Objects missing UVs: {len(no_uv_objs)}")
    if no_uv_objs:
        print(f"  Sample missing UVs: {no_uv_objs[:10]}")
    print(f"Meshes with UV scale deviation from 3.5m/4.0m: {len(cube_size_deviations)}")
    if cube_size_deviations:
        print(f"  Sample deviations: {cube_size_deviations[:15]}")


def audit_usd_file():
    from pxr import Usd, UsdGeom
    usd_path = Path("output/montreal_master.usdc")
    print("\n" + "=" * 70)
    print("AUDITING USD STAGE (output/montreal_master.usdc)")
    print("=" * 70)

    if not usd_path.exists():
        print(f"ERROR: USD file does not exist at {usd_path}")
        return

    file_size_mb = usd_path.stat().st_size / (1024 * 1024)
    print(f"USD File size: {file_size_mb:.2f} MB ({usd_path.stat().st_size} bytes)")

    stage = Usd.Stage.Open(str(usd_path))
    if not stage:
        print("ERROR: Failed to open USD stage!")
        return

    print("USD Stage opened successfully.")
    pseudo_root = stage.GetPseudoRoot()
    all_prims = list(stage.Traverse())
    mesh_prims = [p for p in all_prims if p.IsA(UsdGeom.Mesh)]
    xform_prims = [p for p in all_prims if p.IsA(UsdGeom.Xform)]

    print(f"Total Prims in USD Stage: {len(all_prims)}")
    print(f"Total UsdGeom.Mesh Prims: {len(mesh_prims)}")
    print(f"Total UsdGeom.Xform Prims: {len(xform_prims)}")

    # Check UV primvars on UsdGeom.Mesh
    uv_present_count = 0
    uv_missing = []
    for p in mesh_prims[:200]: # Sample 200 meshes
        mesh_geom = UsdGeom.Mesh(p)
        primvars_api = UsdGeom.PrimvarsAPI(mesh_geom)
        st_pv = primvars_api.GetPrimvar("st") or primvars_api.GetPrimvar("UVMap")
        if st_pv and st_pv.HasValue():
            uv_present_count += 1
        else:
            uv_missing.append(p.GetPath().pathString)

    print(f"Sampled 200 Mesh Prims: {uv_present_count} have UV primvars (st/UVMap), {len(uv_missing)} missing.")
    if uv_missing:
        print(f"  Sample missing UV primvars: {uv_missing[:5]}")

if __name__ == "__main__":
    audit_uv_unwrapping()
    audit_usd_file()
