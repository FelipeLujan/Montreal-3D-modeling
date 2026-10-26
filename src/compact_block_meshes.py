"""
Ultra-fast O(N) BMesh compaction of micro-meshes in a block .blend file (such as MTL-VM-0007.blend,
which had 49,584 objects) by copying vertices/faces directly in BMesh and using bpy.data.batch_remove.
"""
import bpy
import bmesh

print(f"[Compact] Inspecting: {bpy.data.filepath} (Total objects before: {len(bpy.data.objects)})", flush=True)

for col in list(bpy.data.collections):
    if not (col.name.endswith("_Owned") or col.name.endswith("_Context_Proxy")):
        continue
    mesh_objs = [o for o in list(col.all_objects) if o.type == 'MESH' and o.data is not None]
    if len(mesh_objs) <= 150:
        print(f"[Compact] Collection {col.name} has {len(mesh_objs)} meshes (already compact).", flush=True)
        continue

    print(f"[Compact] Fast BMesh merging {len(mesh_objs)} objects in {col.name}...", flush=True)
    by_mat = {}
    to_remove = []
    for o in mesh_objs:
        nl = o.name.lower()
        if any(k in nl for k in ("tree", "jacaranda", "statue", "seating", "bench")):
            continue
        mat = o.data.materials[0] if len(o.data.materials) > 0 else None
        mat_key = mat.name if mat else "__NO_MAT__"
        by_mat.setdefault((mat_key, mat), []).append(o)
        to_remove.append(o)

    for (mat_key, mat), objs in by_mat.items():
        bm = bmesh.new()
        for o in objs:
            me = o.data
            if len(me.vertices) == 0:
                continue
            v_start = len(bm.verts)
            bm.from_mesh(me)
            bm.verts.ensure_lookup_table()
            mw = o.matrix_world
            # Transform only the newly added vertices
            for idx in range(v_start, len(bm.verts)):
                bm.verts[idx].co = mw @ bm.verts[idx].co

        bm.normal_update()
        merged_me = bpy.data.meshes.new(f"{col.name}_{mat_key}_Mesh")
        bm.to_mesh(merged_me)
        bm.free()
        if mat is not None:
            merged_me.materials.append(mat)
        merged_obj = bpy.data.objects.new(f"{col.name}_{mat_key}", merged_me)
        col.objects.link(merged_obj)
        print(f"  -> Created {merged_obj.name} from {len(objs)} micro-objects ({len(merged_me.polygons)} faces)", flush=True)

    print(f"[Compact] Batch-removing {len(to_remove)} micro-objects from {col.name}...", flush=True)
    bpy.data.batch_remove(to_remove)

bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
print(f"[Compact] Total objects after compaction: {len(bpy.data.objects)}, Total meshes: {len(bpy.data.meshes)}", flush=True)
import os
orig_path = bpy.data.filepath
tmp_path = orig_path + ".compact_tmp.blend"
bpy.ops.wm.save_as_mainfile(filepath=tmp_path, copy=True)
print(f"[Compact] Saved compacted temp file: {tmp_path}", flush=True)

