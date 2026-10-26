"""
Diagnose and permanently fix:
1. Black crisscross park walkways in Promenade du Vieux-Port and Champ-de-Mars
   (caused by coplanar self-intersecting ribbon segments at identical Z or duplicate walkway objects / inverted normals).
2. Black block ground/roof patches NE of Place d'Armes (between #1 Place d'Armes and #4 Place Jacques-Cartier,
   around X in [0, 240], Y in [-120, 150]).
"""
import os
import math
import bpy
import bmesh
from mathutils import Vector

WORKSPACE = r"C:\Users\Felipe\Documents\coding\montreal"
MASTER_BLEND = os.path.join(WORKSPACE, "output", "montreal_master.blend")
POLYHAVEN_DIR = os.path.join(WORKSPACE, "assets", "polyhaven")


def find_tex(prefix, suffix):
    for f in os.listdir(POLYHAVEN_DIR):
        fl = f.lower()
        if fl.startswith(prefix.lower()) and fl.endswith(suffix.lower()):
            return os.path.join(POLYHAVEN_DIR, f)
    return None


def main():
    print(f"[FIX-WALKWAYS] Opening {MASTER_BLEND}...")
    bpy.ops.wm.open_mainfile(filepath=MASTER_BLEND)

    # 1. Inspect all visible objects matching *Walkway*, *Path*, *Park*, *Promenade*, *Plaza*
    print("\n--- Step 1: Inspecting Park / Walkway Objects ---")
    for obj in list(bpy.data.objects):
        if obj.type != 'MESH' or obj.hide_render:
            continue
        nl = obj.name.lower()
        if any(k in nl for k in ("walkway", "path", "park", "promenade", "lawn", "champ", "curb")):
            mats = [m.name if m else "None" for m in obj.data.materials]
            zs = [ (obj.matrix_world @ Vector(c)).z for c in obj.bound_box ]
            print(f"  OBJ: {obj.name:48s} | verts={len(obj.data.vertices):6d} | Z=[{min(zs):.3f}, {max(zs):.3f}] | mats={mats}")

    # 2. Why did Parks_47_OSM_Crushed_Stone_And_Paved_Walkways render black?
    # Let's inspect its vertices, normals, Z values, and whether its faces self-overlap at identical Z
    # OR if it intersects with Parks_47_OSM_Contoured_Lawns (which was raised or contoured up to Z=0.35m!).
    # WAIT A SECOND! Look at Parks_47_OSM_Contoured_Lawns vs Parks_47_OSM_Crushed_Stone_And_Paved_Walkways!
    # In overhaul_water_parks_and_architecture.py:
    # Lawns had mounding: `mound = 0.22 * math.sin(...)` -> Z up to 0.08 + 0.22 = 0.30m!
    # Meanwhile Walkways were at flat Z = 0.13m (bottom at Z = 0.02m, top at Z = 0.13m) with side walls!
    # AND each walkway segment is a 3D box (top face at Z=0.13m, bottom face at Z=0.02m)!
    # When two walkway segments cross, or when adjacent segments along a polyline share an joint,
    # their top faces at Z = 0.13m and bottom faces at Z = 0.02m overlap in XY!
    # Even worse: if a walkway has both a top face and a bottom face, or if bmesh.ops.recalc_face_normals
    # on open/non-manifold ribbon boxes flipped the top face normal to -Z, Cycles renders backfacing or
    # overlapping coplanar shadow-terminator faces BLACK!
    walkway_obj = bpy.data.objects.get("Parks_47_OSM_Crushed_Stone_And_Paved_Walkways")
    if walkway_obj:
        me = walkway_obj.data
        up_faces = sum(1 for p in me.polygons if p.normal.z > 0.5)
        down_faces = sum(1 for p in me.polygons if p.normal.z < -0.5)
        side_faces = len(me.polygons) - up_faces - down_faces
        print(f"\n[WALKWAY ANALYSIS] {walkway_obj.name}: total_polys={len(me.polygons)}, up={up_faces}, down={down_faces}, side={side_faces}")

        # Let's check the material on Parks_47_OSM_Crushed_Stone_And_Paved_Walkways
        for slot in walkway_obj.material_slots:
            m = slot.material
            if m and m.use_nodes:
                print(f"  Material {m.name} nodes:")
                for n in m.node_tree.nodes:
                    if n.type == 'TEX_IMAGE':
                        img = n.image
                        print(f"    TEX_IMAGE: {img.name if img else 'None'} | path={img.filepath if img else ''} | size={img.size[:] if img else None} | packed={img.packed_file is not None if img else False}")

    # 3. Let's also check what objects exist in the dark patch NE of Place d'Armes:
    # World X in [10, 220], Y in [-100, 120]
    print("\n--- Step 2: Inspecting Objects in NE of Place d'Armes (X in [10, 220], Y in [-100, 120]) ---")
    ne_objs = []
    for obj in list(bpy.data.objects):
        if obj.type != 'MESH' or obj.hide_render:
            continue
        bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        min_x, max_x = min(v.x for v in bb), max(v.x for v in bb)
        min_y, max_y = min(v.y for v in bb), max(v.y for v in bb)
        min_z, max_z = min(v.z for v in bb), max(v.z for v in bb)
        # Check if object center or bbox is in X=[10, 220], Y=[-100, 120]
        if max_x > 15 and min_x < 210 and max_y > -90 and min_y < 110 and (max_x - min_x) < 400:
            mats = [m.name if m else "None" for m in obj.data.materials]
            ne_objs.append((obj, min_x, max_x, min_y, max_y, min_z, max_z, mats))

    for obj, x0, x1, y0, y1, z0, z1, mats in sorted(ne_objs, key=lambda t: (t[1], t[3])):
        # Check if any material has missing image, packed invalid image, or dark color
        mat_status = []
        for m in obj.data.materials:
            if not m:
                mat_status.append("NONE_MAT")
                continue
            if not m.use_nodes:
                mat_status.append(f"{m.name}(no_nodes:{m.diffuse_color[:3]})")
                continue
            bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            imgs = [n.image for n in m.node_tree.nodes if n.type == 'TEX_IMAGE']
            bad_imgs = [im.name if im else "NullImg" for im in imgs if (not im or im.size[0] == 0 or im.packed_file is not None)]
            bc = tuple(round(c, 2) for c in bsdf.inputs['Base Color'].default_value[:3]) if bsdf else ()
            met = round(bsdf.inputs['Metallic'].default_value, 2) if bsdf else 0
            mat_status.append(f"{m.name}(bc={bc},met={met},imgs={len(imgs)},bad={bad_imgs})")
        print(f"  NE_OBJ: {obj.name:42s} | X=[{x0:6.1f},{x1:6.1f}] Y=[{y0:6.1f},{y1:6.1f}] Z=[{z0:5.2f},{z1:5.2f}] | {'; '.join(mat_status[:3])}")

    # Let's check EVERY material in bpy.data.materials for packed images or size[0] == 0 or dark Base Color!
    print("\n--- Step 3: Auditing ALL Materials in Scene for Packed/Broken Images or Black Shaders ---")
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                im = n.image
                if not im or im.size[0] == 0 or im.packed_file is not None:
                    print(f"  [BAD_TEX_MAT] Material '{m.name}' has image '{im.name if im else None}' (size={im.size[:] if im else None}, packed={im.packed_file is not None if im else None}, path={im.filepath if im else None})")

if __name__ == "__main__":
    main()
