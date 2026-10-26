"""
Restore `output/montreal_master.blend` from `output/montreal_master_pre_rooffix.blend` (100% intact building roofs)
and apply:
1. Park walkway, curb, and lawn de-coplanarization (`Parks_47_OSM_Crushed_Stone_And_Paved_Walkways`,
   `Parks_47_OSM_Granite_Garden_Curbs`, `Parks_47_OSM_Contoured_Lawns`) + warm limestone gravel shader.
2. Surgical, 100% NON-DESTRUCTIVE building roof fix (ZERO faces deleted):
   - Only when two LARGE upward-facing (`normal.z > 0.85`, `area > 15.0 m²`) roof caps in the same building share
     the same Z (`|z1 - z2| < 0.035m`) and concentric 2D centroids (`hypot(cx1 - cx2, cy1 - cy2) < 3.5m`),
     raise the smaller (inset) roof cap by `+0.05m`.
   - Only when a downward-facing (`normal.z < -0.85`, `area > 5.0 m²`) horizontal face is AT OR ABOVE the main roof cap
     (`z >= roof_z - 0.05m`, i.e. an upside-down parapet coping top like `z=28.62m` above `roof_z=28.50m` on `La Presse`),
     flip its normal to `+Z` and raise it by `+0.02m`. Never touch window lintels or cornice soffits below the roof!
"""
import os
import math
import shutil
import bpy
import bmesh
import mathutils
from mathutils import Vector

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(WORKSPACE, "output", "montreal_master.blend")
BACKUP_BLEND1 = os.path.join(WORKSPACE, "output", "montreal_master.blend1")
SAFE_BACKUP = os.path.join(WORKSPACE, "output", "montreal_master_pre_rooffix.blend")
TEMP_BLEND = os.path.join(WORKSPACE, "output", "montreal_master_saving_tmp.blend")
USDC_PATH = os.path.join(WORKSPACE, "output", "montreal_master.usdc")
POLYHAVEN_DIR = os.path.join(WORKSPACE, "assets", "polyhaven")
RENDERS_DIR = os.path.join(WORKSPACE, "output", "renders")


def deconflict_horizontal_mesh(obj, base_z, stagger_step=0.0015, uv_scale=0.25):
    """
    Remove side/bottom/duplicate faces from a ground/walkway/curb/lawn mesh,
    keep only clean upward-facing (+Z) top faces, deduplicate exact XY centroids,
    and stagger overlapping XY faces so NO TWO TRIANGLES are ever coplanar in Cycles.
    """
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()

    to_del = []
    for f in bm.faces:
        min_vz = min(v.co.z for v in f.verts)
        if abs(f.normal.z) < 0.85 or min_vz < 0.05 or f.calc_area() < 1e-4:
            to_del.append(f)
    if to_del:
        bmesh.ops.delete(bm, geom=to_del, context='FACES')

    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()

    seen_centroids = {}
    dup_faces = []
    for f in bm.faces:
        c = f.calc_center_median()
        key = (round(c.x * 25.0), round(c.y * 25.0))
        if key in seen_centroids:
            dup_faces.append(f)
        else:
            seen_centroids[key] = f
    if dup_faces:
        bmesh.ops.delete(bm, geom=dup_faces, context='FACES')

    loose_verts = [v for v in bm.verts if not v.link_faces]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context='VERTS')

    bm.faces.ensure_lookup_table()
    bmesh.ops.split_edges(bm, edges=bm.edges)
    bm.faces.ensure_lookup_table()

    cell_map = {}
    face_bboxes = []
    for idx, f in enumerate(bm.faces):
        xs = [v.co.x for v in f.verts]
        ys = [v.co.y for v in f.verts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        face_bboxes.append((x0, x1, y0, y1))
        gx0, gx1 = int(x0 // 4.0), int(x1 // 4.0)
        gy0, gy1 = int(y0 // 4.0), int(y1 // 4.0)
        for gx in range(gx0, gx1 + 1):
            for gy in range(gy0, gy1 + 1):
                cell_map.setdefault((gx, gy), []).append(idx)

    face_level = [0] * len(bm.faces)
    for idx, f in enumerate(bm.faces):
        x0, x1, y0, y1 = face_bboxes[idx]
        gx0, gx1 = int(x0 // 4.0), int(x1 // 4.0)
        gy0, gy1 = int(y0 // 4.0), int(y1 // 4.0)
        used_levels = set()
        for gx in range(gx0, gx1 + 1):
            for gy in range(gy0, gy1 + 1):
                for other_idx in cell_map.get((gx, gy), ()):
                    if other_idx < idx:
                        ox0, ox1, oy0, oy1 = face_bboxes[other_idx]
                        if ox1 > x0 + 1e-3 and ox0 < x1 - 1e-3 and oy1 > y0 + 1e-3 and oy0 < y1 - 1e-3:
                            used_levels.add(face_level[other_idx])
        lvl = 0
        while lvl in used_levels:
            lvl += 1
        face_level[idx] = lvl

    max_lvl = max(face_level) if face_level else 0
    for idx, f in enumerate(bm.faces):
        z_val = base_z + face_level[idx] * stagger_step
        for v in f.verts:
            v.co.z = z_val

    uv_layer = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for loop in f.loops:
            co = obj.matrix_world @ loop.vert.co
            loop[uv_layer].uv = (co.x * uv_scale, co.y * uv_scale)

    bm.to_mesh(me)
    me.update()
    bm.free()
    print(f"  [DECONFLICT-GROUND] {obj.name}: removed {len(to_del)} non-top + {len(dup_faces)} duplicate faces, colored {len(face_level)} faces across {max_lvl+1} Z-levels (base_z={base_z:.3f}m)")


def fix_building_roof_coplanarity_surgical():
    """
    Surgical, 100% NON-DESTRUCTIVE roof fix (ZERO faces deleted):
    - Only targets buildings where two LARGE upward-facing roof polygons (area > 12 m^2, normal.z > 0.85)
      at z > 3.0m share the same Z (|dz| < 0.035m) and concentric 2D centroids (< 3.5m).
    - Also flips upside-down top parapet coping faces (normal.z < -0.85, area > 4.0 m^2) that sit AT OR ABOVE
      the main roof cap (z >= main_roof_z - 0.05m), and pushes internal ceiling slabs (area > 40 m^2, normal.z < -0.85,
      within 0.6m below main_roof_z) down by -0.08m.
    """
    fixed_blds = 0
    total_offset_faces = 0
    total_flipped_parapets = 0

    for obj in list(bpy.data.objects):
        if obj.type != 'MESH' or obj.hide_render:
            continue
        me = obj.data
        if not me or len(me.polygons) == 0:
            continue
        nl = obj.name.lower()
        if any(k in nl for k in ("water", "park", "roadbed", "sidewalk", "courtyard", "terrain", "ground", "quay", "tree", "lamp", "seating", "hydrant", "planter", "statue", "monument", "fountain", "bench")):
            continue

        zs = [v.co.z for v in me.vertices]
        max_z = max(zs)
        if max_z < 3.5:
            continue

        # Quick check on me.polygons before creating BMesh
        large_up = [p for p in me.polygons if p.center.z > 3.0 and p.normal.z > 0.85 and p.area > 12.0]
        if len(large_up) < 2:
            continue

        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()

        up_faces = []
        down_faces = []
        for f in bm.faces:
            c = f.calc_center_median()
            if c.z > 3.0:
                a = f.calc_area()
                if f.normal.z > 0.85 and a > 12.0:
                    up_faces.append((f, c.x, c.y, c.z, a))
                elif f.normal.z < -0.85 and a > 4.0:
                    down_faces.append((f, c.x, c.y, c.z, a))

        up_faces.sort(key=lambda x: -x[4])  # largest area first
        faces_to_raise = {}
        faces_to_lower = {}
        concentric_roof_zs = []

        n_up = len(up_faces)
        for i in range(n_up):
            fi, cxi, cyi, zi, ai = up_faces[i]
            for j in range(i + 1, n_up):
                fj, cxj, cyj, zj, aj = up_faces[j]
                if abs(zi - zj) < 0.035 and math.hypot(cxi - cxj, cyi - cyj) < 3.5 and aj > 0.50 * ai:
                    # True concentric duplicate roof cap (like La Presse 2851.9m^2 and 2768.8m^2 at z=28.500m)!
                    faces_to_raise[fj] = faces_to_raise.get(fj, 0.0) + 0.06
                    concentric_roof_zs.append(zi)

        if concentric_roof_zs:
            min_roof_z = min(concentric_roof_zs)
            for fd, cxd, cyd, zd, ad in down_faces:
                if zd >= min_roof_z - 0.05:
                    # Upside-down parapet coping face above the roof!
                    fd.normal_flip()
                    faces_to_raise[fd] = faces_to_raise.get(fd, 0.0) + 0.03
                    total_flipped_parapets += 1
                elif min_roof_z - 0.60 <= zd < min_roof_z - 0.05 and ad > 40.0:
                    # Internal ceiling slab right under the roof
                    faces_to_lower[fd] = -0.08

        if faces_to_raise or faces_to_lower:
            target_faces = list(set(faces_to_raise.keys()) | set(faces_to_lower.keys()))
            boundary_edges = set()
            for f in target_faces:
                for e in f.edges:
                    boundary_edges.add(e)
            if boundary_edges:
                bmesh.ops.split_edges(bm, edges=list(boundary_edges))
            for f, dz in faces_to_raise.items():
                if f.is_valid:
                    for v in f.verts:
                        v.co.z += dz
                    total_offset_faces += 1
            for f, dz in faces_to_lower.items():
                if f.is_valid:
                    for v in f.verts:
                        v.co.z += dz
                    total_offset_faces += 1

            bm.to_mesh(me)
            me.update()
            fixed_blds += 1
            print(f"    -> Fixed concentric roof on {obj.name}: raised {len(faces_to_raise)} faces, lowered {len(faces_to_lower)} faces")
        bm.free()

    print(f"  [ROOF-FIX-SURGICAL] Fixed {fixed_blds} buildings (offset {total_offset_faces} concentric roof faces, flipped {total_flipped_parapets} inverted parapet faces, 0 faces deleted!)")


def main():
    # Remove any leftover @ lock file
    at_file = MASTER_BLEND + "@"
    if os.path.exists(at_file):
        try:
            os.remove(at_file)
        except OSError:
            pass

    if not os.path.exists(SAFE_BACKUP) and os.path.exists(BACKUP_BLEND1):
        print(f"[RESTORE] Saving safe copy of {BACKUP_BLEND1} -> {SAFE_BACKUP}")
        shutil.copy2(BACKUP_BLEND1, SAFE_BACKUP)
    if os.path.exists(SAFE_BACKUP):
        print(f"[RESTORE] Restoring clean {SAFE_BACKUP} -> {MASTER_BLEND}")
        shutil.copy2(SAFE_BACKUP, MASTER_BLEND)

    print(f"[FIX-ALL] Opening {MASTER_BLEND}...")
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

    # 1. Fix parks lawns, granite curbs, and walkways so there are ZERO coplanar faces
    lawn_obj = bpy.data.objects.get("Parks_47_OSM_Contoured_Lawns")
    if lawn_obj:
        deconflict_horizontal_mesh(lawn_obj, base_z=0.195, stagger_step=0.0015, uv_scale=0.25)

    curb_obj = bpy.data.objects.get("Parks_47_OSM_Granite_Garden_Curbs")
    if curb_obj:
        deconflict_horizontal_mesh(curb_obj, base_z=0.225, stagger_step=0.0012, uv_scale=0.35)

    walkway_obj = bpy.data.objects.get("Parks_47_OSM_Crushed_Stone_And_Paved_Walkways")
    if walkway_obj:
        deconflict_horizontal_mesh(walkway_obj, base_z=0.245, stagger_step=0.0015, uv_scale=0.30)

    # Ensure Mat_PH_Park_Path_Gravel has warm, bright crushed limestone gravel appearance
    gravel_mat = bpy.data.materials.get("Mat_PH_Park_Path_Gravel")
    if gravel_mat:
        nt = gravel_mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Roughness"].default_value = 0.82
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.25
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

        tex_coord = nt.nodes.new("ShaderNodeTexCoord")
        tex_diff = nt.nodes.new("ShaderNodeTexImage")
        diff_path = os.path.join(POLYHAVEN_DIR, "sandstone_blocks_05_Diffuse_2k.jpg")
        img_diff = bpy.data.images.load(diff_path, check_existing=False)
        img_diff.colorspace_settings.name = 'sRGB'
        tex_diff.image = img_diff
        nt.links.new(tex_coord.outputs["UV"], tex_diff.inputs["Vector"])

        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        mix.blend_type = 'MIX'
        mix.inputs["Factor"].default_value = 0.35
        mix.inputs["B"].default_value = (0.78, 0.74, 0.66, 1.0)
        nt.links.new(tex_diff.outputs["Color"], mix.inputs["A"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])

    # 2. Apply surgical, 100% non-destructive roof de-coplanarization
    fix_building_roof_coplanarity_surgical()

    # 3. Slightly brighten Mat_MTL_Slate_Roof_Dark so slate roofs read as crisp charcoal-grey slate
    slate_mat = bpy.data.materials.get("Mat_MTL_Slate_Roof_Dark")
    if slate_mat:
        for n in slate_mat.node_tree.nodes:
            if n.type == 'MIX' and n.data_type == 'RGBA':
                n.inputs["B"].default_value = (0.28, 0.30, 0.33, 1.0)
                n.inputs["Factor"].default_value = 0.55

    # Save via TEMP_BLEND and atomic os.replace to avoid Windows @ file lock error
    if os.path.exists(TEMP_BLEND):
        os.remove(TEMP_BLEND)
    bpy.ops.wm.save_as_mainfile(filepath=TEMP_BLEND, copy=True)
    os.replace(TEMP_BLEND, MASTER_BLEND)
    print(f"[FIX-ALL] Saved {MASTER_BLEND}")

    # 4. Render all 4 verification views
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True

    cam_data = bpy.data.cameras.new("Cam_Verify_Ortho")
    cam_obj = bpy.data.objects.new("Cam_Verify_Ortho", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # A. Orthographic Full 36-Block Aerial
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 1950.0
    cam_data.clip_start = 1.0
    cam_data.clip_end = 5000.0
    cam_obj.location = (0.0, 0.0, 1200.0)
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)
    scene.render.resolution_x = 2048
    scene.render.resolution_y = 2048
    scene.render.filepath = os.path.join(RENDERS_DIR, "blender_aerial_ortho_full_36blocks.png")
    bpy.ops.render.render(write_still=True)

    # B. Orthographic Core Old Montreal & Old Port
    cam_data.ortho_scale = 1250.0
    cam_obj.location = (120.0, -80.0, 1200.0)
    scene.render.filepath = os.path.join(RENDERS_DIR, "blender_aerial_ortho_core_old_montreal.png")
    bpy.ops.render.render(write_still=True)

    # C. Perspective Old Port & Waterfront Parks
    cam_data.type = 'PERSP'
    cam_data.lens = 26.0
    cam_obj.location = (250.0, -780.0, 360.0)
    direction = mathutils.Vector((60.0, -20.0, 0.0)) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.filepath = os.path.join(RENDERS_DIR, "old_port_water_and_parks_verified.png")
    bpy.ops.render.render(write_still=True)

    # D. Master 36-Block Overview Snapshot
    cam_data.lens = 24.0
    cam_obj.location = (150.0, -1350.0, 780.0)
    direction = mathutils.Vector((20.0, 40.0, 0.0)) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(RENDERS_DIR, "montreal_master_snapshot.png")
    bpy.ops.render.render(write_still=True)

    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.cameras.remove(cam_data, do_unlink=True)

    # 5. Export USD (.usdc)
    print(f"[USD] Exporting {USDC_PATH}...")
    bpy.ops.wm.usd_export(
        filepath=USDC_PATH,
        check_existing=False,
        selected_objects_only=False,
        export_materials=True,
        generate_preview_surface=True,
        evaluation_mode='RENDER',
    )
    print("[FIX-ALL] Done!")


if __name__ == "__main__":
    main()
