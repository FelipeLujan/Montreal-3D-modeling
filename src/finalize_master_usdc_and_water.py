"""
Deduplicates all heavy (> 4,000 poly) botanical meshes in `output/montreal_master.blend`
by remapping them to the already-decimated (< 3,500 poly) botanical meshes from Block 35,
saves `output/montreal_master.blend`, and exports `output/montreal_master.usdc`.
"""
import os
import re
import time
import bpy

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(WORKSPACE, "output", "montreal_master.blend")
USDC_PATH = os.path.join(WORKSPACE, "output", "montreal_master.usdc")


def get_botanical_key(name: str):
    n = name.lower()
    for prefix in ("jakaranda", "jacaranda", "searsia", "tree_small", "shrub_02"):
        if prefix in n:
            if "trunk" in n or "bark" in n or "stem" in n:
                return f"{prefix}_trunk"
            elif "branch" in n or "twig" in n:
                return f"{prefix}_branch"
            else:
                return f"{prefix}_leaves"
    return None


def main():
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

    # Find the lightest valid mesh (100 <= polys <= 4500) for each botanical key
    light_meshes = {}
    for me in list(bpy.data.meshes):
        if not me or len(me.polygons) < 50:
            continue
        bkey = get_botanical_key(me.name)
        if not bkey:
            continue
        if bkey not in light_meshes or len(me.polygons) < len(light_meshes[bkey].polygons):
            light_meshes[bkey] = me

    for k, m in light_meshes.items():
        print(f"  [CANONICAL BOTANICAL] {k} -> {m.name} ({len(m.polygons)} polys)")

    swapped = 0
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.data:
            continue
        bkey = get_botanical_key(obj.data.name) or get_botanical_key(obj.name)
        if bkey and bkey in light_meshes:
            target_me = light_meshes[bkey]
            if obj.data != target_me and len(obj.data.polygons) > len(target_me.polygons):
                mats = [s.material for s in obj.material_slots]
                obj.data = target_me
                for idx, m in enumerate(mats):
                    if idx < len(obj.material_slots) and m is not None:
                        obj.material_slots[idx].link = "OBJECT"
                        obj.material_slots[idx].material = m
                swapped += 1

    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    print(f"[TREES] Swapped {swapped} heavy botanical instances to lightweight LOD meshes.")

    # Save updated montreal_master.blend
    tmp_blend = MASTER_BLEND + ".tmp.blend"
    if os.path.exists(tmp_blend):
        try:
            os.remove(tmp_blend)
        except OSError:
            pass
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
    time.sleep(0.5)
    os.replace(tmp_blend, MASTER_BLEND)
    print(f"[SAVED] {MASTER_BLEND} ({os.path.getsize(MASTER_BLEND):,} bytes)")

    # Export USD (.usdc)
    print(f"[USD] Exporting {USDC_PATH}...")
    bpy.ops.wm.usd_export(
        filepath=USDC_PATH,
        check_existing=False,
        selected_objects_only=False,
        export_materials=False,
        use_instancing=True,
        evaluation_mode="RENDER",
    )
    print(f"[USD COMPLETE] {USDC_PATH} ({os.path.getsize(USDC_PATH):,} bytes)")


if __name__ == "__main__":
    main()
