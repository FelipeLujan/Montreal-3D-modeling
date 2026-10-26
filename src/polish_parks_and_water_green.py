r"""
Color-grades Poly Haven's South African dry savannah grass textures (`leafy_grass`,
`forrest_ground_01`, `grass_path_2`, `grass_park_diffuse_2k`) to lush Montreal summer
chlorophyll green while preserving 100% of the 2K photogrammetry leaf/blade detail,
elevates the park grass lawns above pier decks/walkways, cleans sawtooth foam strips,
re-renders the Google Maps comparison views, and exports `output/montreal_master.usdc`.
"""
import os
import sys
import math

try:
    import bpy
    import bmesh
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
POLY_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
OUT_TEX_DIR = os.path.join(BASE_DIR, "output", "textures")
OUT_RENDERS = os.path.join(BASE_DIR, "output", "renders")
MASTER_BLEND = os.path.join(BASE_DIR, "output", "montreal_master.blend")
MASTER_USDC = os.path.join(BASE_DIR, "output", "montreal_master.usdc")


def color_grade_polyhaven_grass_textures():
    """Run in system Python (with PIL/numpy) to transform dry tan grass (R=151,G=131,B=89) to lush green."""
    from PIL import Image
    import numpy as np

    targets = [
        ("leafy_grass", (52.0, 128.0, 44.0)),
        ("grass_park", (52.0, 128.0, 44.0)),
        ("forrest_ground_01", (60.0, 118.0, 46.0)),
        ("grass_path_2", (66.0, 122.0, 50.0)),
    ]

    folders = [POLY_DIR, OUT_TEX_DIR]
    for root, _, files in os.walk(POLY_DIR):
        if root not in folders:
            folders.append(root)

    count = 0
    for folder in folders:
        if not os.path.exists(folder):
            continue
        for fname in os.listdir(folder):
            low = fname.lower()
            if not (low.endswith(".jpg") or low.endswith(".png")):
                continue
            if not any(k in low for k in ("diff", "col", "albedo")):
                continue
            for prefix, target_rgb in targets:
                if prefix in low:
                    fpath = os.path.join(folder, fname)
                    img = Image.open(fpath).convert("RGB")
                    arr = np.asarray(img, dtype=np.float32)
                    # Compute pixel luminance & micro-detail variation around mean
                    luma = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
                    mean_luma = max(1.0, float(luma.mean()))
                    # Relative detail factor (preserves every blade of grass, shadow, and highlight!)
                    detail = np.clip(luma / mean_luma, 0.35, 1.85)
                    # Also preserve subtle warm/cool hue variation between blades
                    warmth = (arr[:, :, 0] - arr[:, :, 1]) * 0.18
                    new_arr = np.zeros_like(arr)
                    new_arr[:, :, 0] = np.clip(target_rgb[0] * detail + warmth, 8, 245)
                    new_arr[:, :, 1] = np.clip(target_rgb[1] * detail, 18, 250)
                    new_arr[:, :, 2] = np.clip(target_rgb[2] * detail - warmth * 0.4, 6, 220)
                    out_img = Image.fromarray(new_arr.astype(np.uint8), "RGB")
                    out_img.save(fpath, quality=94)
                    count += 1
                    print(f"Color-graded {fpath} -> mean RGB {new_arr.mean(axis=(0,1)).round(1)}")
    print(f"Total grass diffuse maps color-graded to lush Montreal green: {count}")


def extrude_lawn_poly(bm, pts_2d, z_bot, z_top, mat_idx=0, uv_scale=4.5):
    clean = []
    for p in pts_2d:
        if not clean or math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 0.05:
            clean.append((float(p[0]), float(p[1])))
    if len(clean) >= 2 and math.hypot(clean[0][0] - clean[-1][0], clean[0][1] - clean[-1][1]) < 0.05:
        clean.pop()
    if len(clean) < 3:
        return
    area2 = sum(clean[i][0] * clean[(i + 1) % len(clean)][1] - clean[(i + 1) % len(clean)][0] * clean[i][1] for i in range(len(clean)))
    if area2 < 0:
        clean.reverse()

    uv_layer = bm.loops.layers.uv.verify()
    v_bot = [bm.verts.new((x, y, z_bot)) for x, y in clean]
    v_top = [bm.verts.new((x, y, z_top)) for x, y in clean]
    n = len(clean)
    for i in range(n):
        j = (i + 1) % n
        try:
            f = bm.faces.new((v_bot[i], v_bot[j], v_top[j], v_top[i]))
            f.material_index = mat_idx
            for loop in f.loops:
                loop[uv_layer].uv = (loop.vert.co.x / uv_scale, loop.vert.co.z / uv_scale)
        except ValueError:
            pass
    loop_vecs = [Vector((x, y, 0.0)) for x, y in clean]
    for i0, i1, i2 in tessellate_polygon([loop_vecs]):
        if i0 < n and i1 < n and i2 < n and len({i0, i1, i2}) == 3:
            p0, p1, p2 = clean[i0], clean[i1], clean[i2]
            cz = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
            tri_v = (v_top[i0], v_top[i1], v_top[i2]) if cz >= 0 else (v_top[i0], v_top[i2], v_top[i1])
            try:
                f = bm.faces.new(tri_v)
                f.material_index = mat_idx
                for loop in f.loops:
                    loop[uv_layer].uv = (loop.vert.co.x / uv_scale, loop.vert.co.y / uv_scale)
            except ValueError:
                pass


def update_blender_parks_and_water():
    # 1. Reload all images so Blender picks up the lush green Poly Haven grass maps
    for img in bpy.data.images:
        try:
            img.reload()
        except Exception:
            pass

    # Ensure all grass materials have vibrant green fallback + direct leafy_grass_Diffuse_2k.jpg
    leafy_path = os.path.join(POLY_DIR, "leafy_grass_Diffuse_2k.jpg")
    leafy_img = bpy.data.images.load(leafy_path, check_existing=True) if os.path.exists(leafy_path) else None
    for mat in bpy.data.materials:
        mlow = mat.name.lower()
        if any(k in mlow for k in ("grass", "lawn", "foliage", "leaf", "shrub", "greenery", "forest")):
            if mat.use_nodes and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        node.inputs["Base Color"].default_value = (0.16, 0.46, 0.14, 1.0)
                    elif node.type == "TEX_IMAGE" and leafy_img and ("grass" in mlow or "lawn" in mlow):
                        if node.image and any(d in node.image.name.lower() for d in ("diff", "col", "grass", "forrest")):
                            node.image = leafy_img

    # 2. Lift Parks_47_OSM_Contoured_Lawns by +0.035m so green grass crowns cleanly above gravel walkways
    lawns_obj = bpy.data.objects.get("Parks_47_OSM_Contoured_Lawns")
    if lawns_obj and lawns_obj.type == "MESH":
        bm = bmesh.new()
        bm.from_mesh(lawns_obj.data)
        for v in bm.verts:
            if v.co.z > 0.10:
                v.co.z += 0.038
        # Also add explicit contoured green park parterres on the Old Port Waterfront piers & islands
        # where the pier deck is wide open (Promenade du Vieux-Port, Ile Bonsecours, Quai de l'Horloge,
        # Grand Quai, Quai King-Edward, Parc des Eclusiers, and Parc de Dieppe):
        waterfront_green_lawns = [
            # Promenade du Vieux-Port linear park lawns (McGill -> King-Edward -> Jacques-Cartier -> Bonsecours)
            [(205.0, -420.0), (268.0, -420.0), (288.0, -180.0), (228.0, -180.0)],
            [(235.0, -155.0), (295.0, -155.0), (322.0, 55.0), (262.0, 55.0)],
            [(275.0, 80.0), (345.0, 80.0), (405.0, 275.0), (338.0, 275.0)],
            [(355.0, 295.0), (425.0, 295.0), (508.0, 480.0), (442.0, 480.0)],
            # Ile Bonsecours & Central Island lush green lawns
            [(548.0, 372.0), (592.0, 362.0), (618.0, 388.0), (614.0, 438.0), (578.0, 456.0), (544.0, 432.0)],
            [(672.0, 342.0), (748.0, 338.0), (788.0, 415.0), (762.0, 492.0), (695.0, 485.0), (668.0, 412.0)],
            # Quai de l'Horloge green promenade lawn strips
            [(705.0, 455.0), (755.0, 440.0), (805.0, 625.0), (758.0, 638.0)],
            [(762.0, 650.0), (808.0, 638.0), (828.0, 712.0), (785.0, 722.0)],
            # Grand Quai (Quai Alexandra) elevated green roof & eastern tip park lawn
            [(365.0, -252.0), (595.0, -232.0), (592.0, -198.0), (362.0, -218.0)],
            [(615.0, -268.0), (668.0, -262.0), (662.0, -175.0), (610.0, -180.0)],
            # Quai King-Edward eastern tip lawn
            [(675.0, 22.0), (728.0, 28.0), (722.0, 88.0), (670.0, 82.0)],
            # Parc des Eclusiers & Lachine Canal Lock No. 1 green embankments
            [(225.0, -585.0), (315.0, -565.0), (345.0, -765.0), (255.0, -785.0)],
            # Parc de Dieppe & Cite du Havre peninsula green park lawns
            [(968.0, -95.0), (1068.0, -95.0), (1076.0, 145.0), (1035.0, 325.0), (995.0, 315.0), (964.0, 120.0)],
            [(968.0, -560.0), (992.0, -560.0), (988.0, -120.0), (964.0, -120.0)],
            # Champ-de-Mars main upper & lower green lawns
            [(35.0, 325.0), (118.0, 358.0), (75.0, 468.0), (-8.0, 435.0)],
            [(45.0, 478.0), (125.0, 512.0), (92.0, 592.0), (12.0, 558.0)],
            # Square Victoria north & south green lawns
            [(-425.0, -395.0), (-368.0, -365.0), (-398.0, -305.0), (-455.0, -335.0)],
        ]
        for poly in waterfront_green_lawns:
            extrude_lawn_poly(bm, poly, 0.05, 0.235, mat_idx=0, uv_scale=4.5)

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(lawns_obj.data)
        bm.free()
        lawns_obj.data.update()
        print("Elevated Parks_47_OSM_Contoured_Lawns and added 17 prominent waterfront/park lawn parterres at Z=+0.235m.")

    # 3. Remove white sawtooth foam strips (Mat_MTL_Water_Foam_Edge faces) from Water_District_StLawrence_And_Canals
    water_obj = bpy.data.objects.get("Water_District_StLawrence_And_Canals")
    if water_obj and water_obj.type == "MESH":
        bm = bmesh.new()
        bm.from_mesh(water_obj.data)
        foam_faces = [f for f in bm.faces if f.material_index > 0 or any(v.co.z > -2.195 for v in f.verts)]
        if foam_faces:
            bmesh.ops.delete(bm, geom=foam_faces, context="FACES")
            bm.to_mesh(water_obj.data)
            water_obj.data.update()
            print(f"Removed {len(foam_faces)} sawtooth white foam faces from Water_District_StLawrence_And_Canals.")
        bm.free()

    # Save updated montreal_master.blend
    tmp_blend = os.path.join(BASE_DIR, "output", "montreal_master.tmp.blend")
    if os.path.exists(tmp_blend):
        try:
            os.remove(tmp_blend)
        except Exception:
            pass
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
    os.replace(tmp_blend, MASTER_BLEND)
    print(f"Saved updated {MASTER_BLEND}")

    # Re-render the 4 verification views
    import execute_master_overhaul
    execute_master_overhaul.render_verification_views()

    # Export USD (using Blender 5.2 supported parameters)
    print(f"Exporting USD stage to {MASTER_USDC} ...")
    bpy.ops.wm.usd_export(
        filepath=MASTER_USDC,
        check_existing=False,
        selected_objects_only=False,
        visible_objects_only=True,
        export_materials=True,
        generate_preview_surface=True,
        export_textures=True,
        export_uvmaps=True,
        export_normals=True,
        export_mesh_colors=True,
        use_instancing=False,
    )

    from pxr import Usd, UsdGeom, UsdPhysics
    stage = Usd.Stage.Open(MASTER_USDC)
    coll_count, ds_count = 0, 0
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            UsdGeom.Mesh(prim).CreateDoubleSidedAttr(True)
            ds_count += 1
            if "water" not in prim.GetName().lower():
                UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(True)
                UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr("none")
                coll_count += 1
    stage.GetRootLayer().Save()
    print(f"USD EXPORT COMPLETE: doubleSided={ds_count}, CollisionAPI={coll_count}")


if __name__ == "__main__":
    if not IN_BLENDER:
        color_grade_polyhaven_grass_textures()
    else:
        sys.path.insert(0, os.path.join(BASE_DIR, "src"))
        update_blender_parks_and_water()
