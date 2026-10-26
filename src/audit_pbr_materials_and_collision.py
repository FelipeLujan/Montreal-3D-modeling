import os
import sys
import bpy
import bmesh
from mathutils import Vector

print("=" * 80)
print("AUDIT: PBR MATERIALS, GROUND COLLIDER & SCENE INTEGRITY")
print("=" * 80)

# 1. PBR MATERIALS AUDIT
print("\n[SECTION 1: PBR MATERIALS AUDIT]")
target_keywords = {
    "asphalt": ["asphalt_02", "asphalt"],
    "cobblestone": ["cobblestone_floor_08", "cobble"],
    "sandstone": ["sandstone_blocks_05", "sandstone", "pierregreise", "limestone"],
    "brick": ["castle_brick_02_red", "brick"]
}

material_results = {k: [] for k in target_keywords}

for mat in bpy.data.materials:
    mat_name_lower = mat.name.lower()
    for cat, kws in target_keywords.items():
        if any(kw in mat_name_lower for kw in kws):
            material_results[cat].append(mat)

for cat, mats in material_results.items():
    print(f"\n--- Category: {cat.upper()} ({len(mats)} materials found) ---")
    for mat in mats:
        print(f"Material: '{mat.name}' (users: {mat.users})")
        if not mat.use_nodes or not mat.node_tree:
            print("  WARNING: Material does not use nodes!")
            continue
        nodes = mat.node_tree.nodes
        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not bsdf:
            print("  WARNING: No Principled BSDF node found!")
            continue
        
        # Check inputs
        base_color_link = bsdf.inputs["Base Color"].links[0] if bsdf.inputs["Base Color"].is_linked else None
        roughness_link = bsdf.inputs["Roughness"].links[0] if bsdf.inputs["Roughness"].is_linked else None
        normal_link = bsdf.inputs["Normal"].links[0] if bsdf.inputs["Normal"].is_linked else None
        
        print(f"  Base Color input: linked={base_color_link is not None}")
        if base_color_link:
            from_node = base_color_link.from_node
            print(f"    from node: {from_node.name} ({from_node.type})")
            if from_node.type == 'TEX_IMAGE' and from_node.image:
                print(f"    image: {from_node.image.name} -> {from_node.image.filepath}")
            elif from_node.type == 'MIX':
                # Check mix node inputs
                for inp in from_node.inputs:
                    if inp.is_linked:
                        sub = inp.links[0].from_node
                        img_str = f"image: {sub.image.name}" if hasattr(sub, 'image') and sub.image else ""
                        print(f"      mix input from: {sub.name} ({sub.type}) {img_str}")

        print(f"  Roughness input: linked={roughness_link is not None}")
        if roughness_link:
            from_node = roughness_link.from_node
            print(f"    from node: {from_node.name} ({from_node.type})")
            if from_node.type == 'TEX_IMAGE' and from_node.image:
                print(f"    image: {from_node.image.name} -> {from_node.image.filepath}")
            elif from_node.type == 'MATH':
                for inp in from_node.inputs:
                    if inp.is_linked:
                        sub = inp.links[0].from_node
                        img_str = f"image: {sub.image.name}" if hasattr(sub, 'image') and sub.image else ""
                        print(f"      math input from: {sub.name} ({sub.type}) {img_str}")

        print(f"  Normal input: linked={normal_link is not None}")
        if normal_link:
            from_node = normal_link.from_node
            print(f"    from node: {from_node.name} ({from_node.type})")
            if from_node.type == 'NORMAL_MAP':
                nmap_col_link = from_node.inputs["Color"].links[0] if from_node.inputs["Color"].is_linked else None
                if nmap_col_link:
                    tex_sub = nmap_col_link.from_node
                    img_str = f"image: {tex_sub.image.name} -> {tex_sub.image.filepath}" if hasattr(tex_sub, 'image') and tex_sub.image else "no image"
                    print(f"      normal map color from: {tex_sub.name} ({tex_sub.type}) [{img_str}]")

# Check all TexImage nodes across all materials for Poly Haven texture presence
print("\n--- Summary of Image Textures in Scene ---")
polyhaven_images_found = {}
for img in bpy.data.images:
    polyhaven_images_found[img.name] = {
        "filepath": img.filepath,
        "size": (img.size[0], img.size[1]),
        "users": img.users
    }
for iname, info in polyhaven_images_found.items():
    print(f"Image '{iname}': filepath='{info['filepath']}', size={info['size']}, users={info['users']}")

# 2. GROUND SOLID COLLIDER AUDIT
print("\n[SECTION 2: GROUND DISTRICT SOLID COLLIDER AUDIT]")
collider_obj = bpy.data.objects.get("Ground_District_Solid_Collider")
if not collider_obj:
    print("CRITICAL: 'Ground_District_Solid_Collider' NOT FOUND in bpy.data.objects!")
    # Look for any collider objects
    colliders = [o.name for o in bpy.data.objects if "collider" in o.name.lower() or "ground" in o.name.lower()]
    print(f"Alternative candidates with 'collider' or 'ground': {colliders}")
else:
    print(f"Found '{collider_obj.name}' (type: {collider_obj.type}, visible: {not collider_obj.hide_viewport}, render: {not collider_obj.hide_render})")
    mesh = collider_obj.data
    print(f"  Vertices: {len(mesh.vertices)}, Polygons: {len(mesh.polygons)}, Edges: {len(mesh.edges)}")
    
    # Check bounding box
    bbox_corners = [collider_obj.matrix_world @ Vector(corner) for corner in collider_obj.bound_box]
    xs = [v.x for v in bbox_corners]
    ys = [v.y for v in bbox_corners]
    zs = [v.z for v in bbox_corners]
    print(f"  World Bounding Box: X=[{min(xs):.2f}, {max(xs):.2f}], Y=[{min(ys):.2f}, {max(ys):.2f}], Z=[{min(zs):.2f}, {max(zs):.2f}]")
    
    # Check Z distribution of vertices
    vert_zs = [(collider_obj.matrix_world @ v.co).z for v in mesh.vertices]
    print(f"  Vertex Z min: {min(vert_zs):.3f}m, max: {max(vert_zs):.3f}m")
    
    # Check polygon normals
    upward_faces = 0
    downward_faces = 0
    vertical_faces = 0
    retaining_wall_faces = 0
    retaining_wall_z_mins = []
    
    for poly in mesh.polygons:
        # compute world normal
        w_norm = (collider_obj.matrix_world.to_3x3() @ poly.normal).normalized()
        face_center = collider_obj.matrix_world @ poly.center
        poly_verts_z = [(collider_obj.matrix_world @ mesh.vertices[v].co).z for v in poly.vertices]
        
        if w_norm.z > 0.7:
            upward_faces += 1
        elif w_norm.z < -0.7:
            downward_faces += 1
        else:
            vertical_faces += 1
            if min(poly_verts_z) < -0.5:
                retaining_wall_faces += 1
                retaining_wall_z_mins.append(min(poly_verts_z))
                
    print(f"  Polygon Face Analysis:")
    print(f"    Upward (+Z) faces: {upward_faces}")
    print(f"    Downward (-Z) faces: {downward_faces}")
    print(f"    Vertical / side wall faces: {vertical_faces}")
    print(f"    Retaining wall faces (Z < -0.5m): {retaining_wall_faces}")
    if retaining_wall_z_mins:
        print(f"    Retaining wall lowest Z: {min(retaining_wall_z_mins):.3f}m")

    # Check manifold / solidity using bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
    boundary_edges = [e for e in bm.edges if e.is_boundary]
    print(f"  Solid Geometry Check: Non-manifold edges: {len(non_manifold_edges)}, Boundary (open) edges: {len(boundary_edges)}")
    bm.free()

# 3. QUAYS AND WATERFRONT CHECK
print("\n[SECTION 3: QUAYS AND WATERFRONT OBJECTS]")
quay_objs = [o for o in bpy.data.objects if any(k in o.name.lower() for k in ["quay", "water", "marina", "basin", "port"])]
print(f"Found {len(quay_objs)} quay/waterfront objects:")
for q in quay_objs[:15]:
    zs = [(q.matrix_world @ v.co).z for v in q.data.vertices] if q.type == 'MESH' and len(q.data.vertices) > 0 else [0]
    print(f"  '{q.name}': verts={len(q.data.vertices) if q.type=='MESH' else 0}, Z=[{min(zs):.2f}, {max(zs):.2f}]")

print("\nAUDIT FINISHED")
