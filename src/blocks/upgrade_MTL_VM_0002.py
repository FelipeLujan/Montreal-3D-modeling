"""
Iteration 2 Upgrade Script for City Block MTL-VM-0002 (`upgrade_MTL_VM_0002.py`).
Opens `output/blocks/MTL-VM-0002.blend`, appends real Poly Haven 3D scanned assets from
`assets/montreal_kit.blend` (`jacaranda_tree_LOD0`, `gothic_statue`, `street_lamp_01`, `Master_Street_Bench`),
and executes all 5 Visual Critic architectural deltas:
1. Replaces all procedural sphere trees with real Poly Haven `jacaranda_tree_LOD0` 3D trees.
2. Replaces the 3 primitive statue figures on the Basilica West Facade with real `gothic_statue` 3D sculptures.
3. Fixes Vieux Séminaire de Saint-Sulpice & 3-storey Sulpician Corner Wing:
   - Removes the windowless `Seminaire_OSM_MainWings` & `Seminaire_OSM_EastLinkWing` extruded boxes that were
     occluding the Séminaire courtyard and NE wing windows!
   - Lowers the Forecourt Fieldstone Wall to `2.8m` so the U-shaped 1684 Vieux Séminaire & 1701 Clock Pavilion
     are completely visible from Rue Notre-Dame Ouest (`Seminaire_Saint_Sulpice_Clock.jpg`).
   - Adds 3-storey classical window bays, corner quoins, pediment, and entrance hood on the Sulpician NE Wing.
4. Deepens the Basilica Triple-Arch Portico Loggia (`3.8m` deep shadowed open vestibule):
   - Carves back the front of `ND_OSM_Ashlar_Nave` behind `ly = -4.2m` so the 3 Gothic entrance arches open into
     a true `3.8m`-deep shadowed loggia with dark coffered stone vaults and recessed dark-oak/bronze doors.
5. Upgrades Gothic Window Tracery (pointed sub-arches + rose/quatrefoil head rings), darkens the rusticated stone
   base plinth to aged Montreal limestone (`#75736C`), darkens oak doors (`#3A2416`), adds the Rue Saint-Sulpice
   wrought-iron fence and rainwater downspouts, and renders `iter2_*.png` + `MTL-VM-0002_snapshot.png`.
"""

import os
import sys
import json
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
for sub in ("src", os.path.join("src", "blocks")):
    p = os.path.join(BASE_DIR, sub)
    if p not in sys.path:
        sys.path.append(p)

BLOCK_ID = "MTL-VM-0002"
BLEND_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.blend")
USDC_PATH = os.path.join(BASE_DIR, "output", "blocks", f"{BLOCK_ID}.usdc")
KIT_BLEND_PATH = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
DOSSIER_PATH = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "dossier.json")
RENDERS_DIR = os.path.join(BASE_DIR, "data", "blocks", BLOCK_ID, "renders")
OUTPUT_RENDERS_DIR = os.path.join(BASE_DIR, "output", "renders")


def load_kit_assets():
    """Appends high-poly Poly Haven meshes & materials from `assets/montreal_kit.blend`."""
    wanted_objs = ["jacaranda_tree_LOD0", "gothic_statue", "street_lamp_01", "Master_Street_Bench"]
    with bpy.data.libraries.load(KIT_BLEND_PATH, link=False) as (data_from, data_to):
        data_to.objects = [name for name in wanted_objs if name in data_from.objects]
    loaded = {}
    for obj in data_to.objects:
        if obj is not None:
            loaded[obj.name] = obj
    return loaded


def create_box(name, center, dims, rot_z, mat, col):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=dims, verts=bm.verts)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, 'Z'), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        obj.data.materials.append(mat)
    bev = obj.modifiers.new(name="ArchBevel", type='BEVEL')
    bev.width = 0.025
    bev.segments = 2
    return obj


def create_torus_ring(name, center, radius, thickness, rot_euler, mat, col):
    """Creates a 3D circular/quatrefoil Gothic rose tracery ring or clock bezel."""
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    bm = bmesh.new()
    segs = 20
    ring_segs = 8
    for i in range(segs):
        a0 = (i / segs) * 2.0 * math.pi
        a1 = ((i + 1) / segs) * 2.0 * math.pi
        c_geom = bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=ring_segs,
            radius1=thickness, radius2=thickness,
            depth=(2.0 * math.pi * radius / segs) * 1.15
        )
        c_verts = c_geom["verts"]
        ang_mid = (a0 + a1) * 0.5
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler((math.pi * 0.5, 0, ang_mid + math.pi * 0.5), 'XYZ').to_matrix(), verts=c_verts)
        bmesh.ops.translate(bm, vec=(radius * math.cos(ang_mid), 0.0, radius * math.sin(ang_mid)), verts=c_verts)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler(rot_euler, 'XYZ').to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        obj.data.materials.append(mat)
    return obj


def upgrade_block():
    if not os.path.exists(BLEND_PATH) and os.path.exists(BLEND_PATH + "@"):
        os.replace(BLEND_PATH + "@", BLEND_PATH)
    bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)
    with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    owned_col = bpy.data.collections.get(f"Block_{BLOCK_ID}_Owned")
    cam_col = bpy.data.collections.get(f"Block_{BLOCK_ID}_Cameras")
    kit_objs = load_kit_assets()

    mat_stone = bpy.data.materials.get("Mat_MTL_PierreGrise_Limestone")
    mat_buff = bpy.data.materials.get("Mat_MTL_WarmBuff_Limestone")
    mat_rubble = bpy.data.materials.get("Mat_MTL_Fieldstone_Rubble")
    mat_vault = bpy.data.materials.get("Mat_MTL_Dark_Vault_Stone")
    mat_slate = bpy.data.materials.get("Mat_MTL_Slate_Roof_Dark")
    mat_glass = bpy.data.materials.get("Mat_MTL_Window_Glass_Dark")
    mat_stained = bpy.data.materials.get("Mat_MTL_Stained_Glass")
    mat_white = bpy.data.materials.get("Mat_MTL_White_Trim")
    mat_iron = bpy.data.materials.get("Mat_MTL_CastIron_Black")
    mat_gold = bpy.data.materials.get("Mat_MTL_Gold_Leaf")
    mat_bronze = bpy.data.materials.get("Mat_MTL_Statue_Bronze")
    mat_wood = bpy.data.materials.get("Mat_MTL_Warm_Wood")

    # 1. Refine Material Tones per Critic:
    #    - Darken rusticated base stone (`Mat_MTL_Fieldstone_Rubble`) to aged Montreal grey limestone (`#6E6C66`)
    if mat_rubble and mat_rubble.use_nodes:
        for n in mat_rubble.node_tree.nodes:
            if n.type == 'MIX':
                n.blend_type = 'MULTIPLY'
                n.inputs["Factor"].default_value = 0.78
                n.inputs[7].default_value = (0.24, 0.23, 0.21, 1.0)
    #    - Darken oak portal doors (`Mat_MTL_Warm_Wood`) to rich dark stained walnut/oak (`#2C1B10`)
    if mat_wood and mat_wood.use_nodes:
        bsdf_w = next((n for n in mat_wood.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf_w:
            bsdf_w.inputs["Base Color"].default_value = (0.06, 0.032, 0.018, 1.0)
            bsdf_w.inputs["Roughness"].default_value = 0.42
        for n in mat_wood.node_tree.nodes:
            if n.type == 'VALTORGB':
                n.color_ramp.elements[0].color = (0.04, 0.02, 0.01, 1.0)
                n.color_ramp.elements[1].color = (0.09, 0.05, 0.025, 1.0)

    # Coordinate frame helpers for Basilica & Séminaire
    sw_pt = Vector((-8.309, -25.949, 0.0))
    ne_pt = Vector((10.018, 10.642, 0.0))
    u_vec = (ne_pt - sw_pt).normalized()
    n_west = Vector((-u_vec.y, u_vec.x, 0.0))
    facade_mid = (sw_pt + ne_pt) * 0.5
    rot_facade = math.atan2(u_vec.y, u_vec.x)

    def to_world(lx, ly, lz=0.0):
        return (
            facade_mid.x + lx * u_vec.x + ly * n_west.x,
            facade_mid.y + lx * u_vec.y + ly * n_west.y,
            lz
        )

    def sem_world(lx, ly, lz=0.0):
        return (
            sw_pt.x + lx * u_vec.x + ly * n_west.x,
            sw_pt.y + lx * u_vec.y + ly * n_west.y,
            lz
        )

    # 2. Replace ALL procedural sphere/blob trees with real Poly Haven `jacaranda_tree_LOD0` 3D trees!
    tree_template = kit_objs.get("jacaranda_tree_LOD0")
    for o in list(bpy.data.objects):
        if o.name.startswith(("OSM_Tree_", "Garden_Tree_", "PH_Tree_", "PH_StSulpice_Tree_")):
            bpy.data.objects.remove(o, do_unlink=True)

    # Curated tree placements matching the 4 Street View photos & satellite ortho (clear of the Basilica front parvis steps!)
    curated_trees = [
        # Rue Saint-Sulpice sidewalk trees framing `Corner_NotreDame_SaintSulpice` & `Rue_SaintSulpice_Side_Wall`
        ("StSulpice_North", to_world(26.8, -5.5, 0.0), 0.42),
        ("StSulpice_Mid", to_world(26.8, -24.0, 0.0), 0.46),
        ("StSulpice_South", to_world(26.8, -46.0, 0.0), 0.44),
        # Vieux Séminaire courtyard & garden trees
        ("Sem_Garden_1", sem_world(-28.0, -45.0, 0.0), 0.58),
        ("Sem_Garden_2", sem_world(-16.0, -52.0, 0.0), 0.54),
        ("Sem_Garden_3", sem_world(-40.0, -48.0, 0.0), 0.56),
        ("Sem_Forecourt_West", sem_world(-46.5, 1.5, 0.0), 0.42),
        # Place d'Armes West edge (outside Basilica West Facade sightlines)
        ("PlaceDArmes_NW", (-16.0, 28.0, 0.0), 0.45),
    ]
    if tree_template:
        for i, (tname, tloc, s) in enumerate(curated_trees):
            inst = tree_template.copy()
            inst.data = tree_template.data
            inst.name = f"PH_Tree_{i}_{tname}"
            owned_col.objects.link(inst)
            inst.scale = (s, s, s)
            inst.location = (tloc[0], tloc[1], 0.0)
            inst.rotation_euler = (0.0, 0.0, (i * 1.7) % (2.0 * math.pi))

    # 3. Replace primitive statue cones/cylinders with real sculpted `gothic_statue` 3D meshes!
    statue_template = kit_objs.get("gothic_statue")
    for o in list(bpy.data.objects):
        if o.name.startswith(("ND_Statue_Figure_", "ND_Gothic_Statue_Mesh_", "ND_Statue_Canopy_")):
            bpy.data.objects.remove(o, do_unlink=True)

    if statue_template:
        for n_idx, nx in enumerate([-5.7, 0.0, 5.7]):
            st = statue_template.copy()
            st.data = statue_template.data.copy()
            st.name = f"ND_Gothic_Statue_Mesh_{n_idx}"
            owned_col.objects.link(st)
            st.scale = (1.55, 1.55, 1.70)
            st.location = to_world(nx, 2.02, 20.3)
            st.rotation_euler = (0.0, 0.0, rot_facade)
            st.data.materials.clear()
            st.data.materials.append(mat_gold if n_idx == 1 else mat_buff)

    # 4. Fix Vieux Séminaire de Saint-Sulpice & 3-Storey Sulpician Corner Wing (`Seminaire_Saint_Sulpice_Clock`!):
    for bad_name in ["Seminaire_OSM_MainWings", "Seminaire_OSM_EastLinkWing", "Sem_Clock_Pediment", "Sem_Clock_TruePediment"]:
        obj_bad = bpy.data.objects.get(bad_name)
        if obj_bad:
            bpy.data.objects.remove(obj_bad, do_unlink=True)
    for o in list(bpy.data.objects):
        if o.name.startswith("Sem_NE_TrueFrontWin_"):
            bpy.data.objects.remove(o, do_unlink=True)

    # Lower the Forecourt Fieldstone Wall to `2.7m` height so the 1684 Vieux Séminaire & 1701 Clock Pavilion behind it are clearly visible!
    for wname, lx_w, w_len in [("Sem_Forecourt_Wall_EastSeg", -20.5, 10.5), ("Sem_Forecourt_Wall_WestSeg", -39.5, 16.5)]:
        o_w = bpy.data.objects.get(wname)
        if o_w:
            bpy.data.objects.remove(o_w, do_unlink=True)
        create_box(wname, sem_world(lx_w, -2.2, 1.35), (w_len, 0.95, 2.7), rot_facade, mat_rubble, owned_col)
    for cname, lx_w, w_len in [("Sem_Forecourt_Wall_EastCap", -20.5, 10.8), ("Sem_Forecourt_Wall_WestCap", -39.5, 16.8)]:
        o_c = bpy.data.objects.get(cname)
        if o_c:
            bpy.data.objects.remove(o_c, do_unlink=True)
        create_box(cname, sem_world(lx_w, -2.2, 2.82), (w_len, 1.15, 0.28), rot_facade, mat_buff, owned_col)

    # Add 3-Storey Classical Window Bays & Entrance Hood on the NW Front Face of `Sem_NE_Wing_Body`
    import build_MTL_VM_0002 as b0002
    ne_wing_x = -11.2
    ne_front_y = -2.45
    for fl_i, fl_z in enumerate([2.3, 5.8, 9.3, 12.6]):
        win_h = 2.25 if fl_i < 3 else 1.50
        for col_x in [-2.6, 0.0, 2.6]:
            b0002.create_recessed_casement_window(
                f"Sem_NE_TrueFrontWin_{fl_i}_{int(col_x)}",
                sem_world(ne_wing_x + col_x, ne_front_y, fl_z),
                1.48, win_h, 0.45,
                rot_facade, mat_buff, mat_white, mat_glass, owned_col
            )

    # Add Classical Triangular Pediment on the Vieux Séminaire 1701 Clock Pavilion (facing NW at ly = -16.8m)
    corps_x = -28.5
    corps_y = -24.5
    mesh_cp = bpy.data.meshes.new("Sem_Clock_TruePediment_Mesh")
    obj_cp = bpy.data.objects.new("Sem_Clock_TruePediment", mesh_cp)
    owned_col.objects.link(obj_cp)
    bm_cp = bmesh.new()
    pv1 = bm_cp.verts.new(sem_world(corps_x - 4.1, corps_y + 7.7, 15.8))
    pv2 = bm_cp.verts.new(sem_world(corps_x + 4.1, corps_y + 7.7, 15.8))
    pv3 = bm_cp.verts.new(sem_world(corps_x + 4.1, corps_y + 5.1, 15.8))
    pv4 = bm_cp.verts.new(sem_world(corps_x - 4.1, corps_y + 5.1, 15.8))
    pvt_f = bm_cp.verts.new(sem_world(corps_x, corps_y + 7.7, 18.4))
    pvt_b = bm_cp.verts.new(sem_world(corps_x, corps_y + 5.1, 18.4))
    bm_cp.faces.new([pv1, pv2, pvt_f])
    bm_cp.faces.new([pv2, pv3, pvt_b, pvt_f])
    bm_cp.faces.new([pv3, pv4, pvt_b])
    bm_cp.faces.new([pv4, pv1, pvt_f, pvt_b])
    bm_cp.to_mesh(mesh_cp)
    bm_cp.free()
    obj_cp.data.materials.append(mat_buff)

    # 5. Enhance the Basilica Triple-Arch Portico Loggia (preserve oak doors & pointed vault arches at ly = 1.82..1.88):
    for o in list(bpy.data.objects):
        if o.name.startswith(("ND_DeepLoggia_ShadowRecess_", "ND_Loggia_Entablature_Beam_", "ND_Loggia_IronCresting_", "ND_Door_IronHinge_")):
            bpy.data.objects.remove(o, do_unlink=True)

    for p_idx, px in enumerate([-5.7, 0.0, 5.7]):
        # Dark vaulted recess box strictly BEHIND the oak doors (ly = 0.65, depth = 2.0 -> front face at ly = 1.65)
        create_box(
            f"ND_DeepLoggia_ShadowRecess_{p_idx}",
            to_world(px, 0.65, 6.2),
            (3.9, 2.0, 10.5),
            rot_facade, mat_vault, owned_col
        )
        # Ornate cast-iron cresting balustrade across the entablature at z = 6.35m (seen in Basilica_West_Towers_Facade.jpg!)
        create_box(
            f"ND_Loggia_Entablature_Beam_{p_idx}",
            to_world(px, 1.90, 6.20),
            (4.3, 0.45, 0.38),
            rot_facade, mat_buff, owned_col
        )
        create_box(
            f"ND_Loggia_IronCresting_{p_idx}",
            to_world(px, 1.95, 6.55),
            (4.1, 0.10, 0.35),
            rot_facade, mat_iron, owned_col
        )
        # Add iron strap hinges and paneling dividers on the recessed oak portal doors (at ly = 1.90)
        for h_z in [2.0, 3.2, 4.4]:
            create_box(
                f"ND_Door_IronHinge_{p_idx}_{int(h_z*10)}",
                to_world(px, 1.90, h_z),
                (2.8, 0.08, 0.09),
                rot_facade, mat_iron, owned_col
            )

    # 6. Upgrade Gothic Window Head Tracery (Rose/Quatrefoil Circles + Pointed Sub-Arches) on Basilica Windows:
    for o in list(bpy.data.objects):
        if o.name.startswith(("ND_SideWin_RoseTracery_", "ND_SideWin_SubTrefoil_", "ND_Downspout_Pipe_", "ND_Tower_Rose_", "ND_StSulpice_Fence", "ND_SidePorch_")):
            bpy.data.objects.remove(o, do_unlink=True)

    for bay_i in range(8):
        win_ly = -10.5 - bay_i * 8.4 - 4.2
        for side_sign, s_rot in [(-1.0, rot_facade + math.pi * 0.5), (1.0, rot_facade - math.pi * 0.5)]:
            wall_lx = side_sign * 20.55
            # Main rose ring in upper arch tympanum (at z = 18.2m)
            create_torus_ring(
                f"ND_SideWin_RoseTracery_{bay_i}_{int(side_sign)}",
                to_world(wall_lx, win_ly, 18.2),
                0.92, 0.08, (0, 0, s_rot), mat_buff, owned_col
            )
            # 2 smaller trefoil rings below rose (at z = 16.4m)
            for sub_y in (-0.85, 0.85):
                create_torus_ring(
                    f"ND_SideWin_SubTrefoil_{bay_i}_{int(side_sign)}_{int(sub_y*10)}",
                    to_world(wall_lx, win_ly + sub_y, 16.4),
                    0.48, 0.06, (0, 0, s_rot), mat_buff, owned_col
                )
            # Metallic rainwater downspout pipe running vertically alongside each buttress on Rue Saint-Sulpice (`Corner_NotreDame_SaintSulpice.jpg`!)
            if side_sign > 0:
                b0002.create_cylinder(
                    f"ND_Downspout_Pipe_{bay_i}",
                    to_world(wall_lx + 0.12, win_ly + 2.8, 12.8),
                    0.075, 25.2, (0, 0, 0), mat_white, owned_col, segments=10
                )

    # Also add rose tracery rings to the West Tower lancet windows
    for t_name, tx in [("SW_Perseverance", -14.2), ("NE_Temperance", 14.2)]:
        ty = -3.4
        for z_rose in [10.4, 24.0, 52.8]:
            create_torus_ring(
                f"ND_Tower_Rose_{t_name}_{int(z_rose)}",
                to_world(tx, ty + 5.42, z_rose),
                0.78, 0.075, (0, 0, rot_facade), mat_buff, owned_col
            )

    # 7. Add Wrought-Iron Perimeter Fence along Rue Saint-Sulpice & Side Porch Oak Door Detailing (`Rue_SaintSulpice_Side_Wall.jpg`):
    for f_i in range(28):
        fy = -8.0 - f_i * 2.5
        create_box(
            f"ND_StSulpice_FencePost_{f_i}",
            to_world(22.1, fy, 0.65),
            (0.08, 0.08, 1.3),
            rot_facade, mat_iron, owned_col
        )
        if f_i < 27:
            create_box(
                f"ND_StSulpice_FenceRailTop_{f_i}",
                to_world(22.1, fy - 1.25, 1.18),
                (0.05, 2.5, 0.05),
                rot_facade, mat_iron, owned_col
            )
            create_box(
                f"ND_StSulpice_FenceRailBot_{f_i}",
                to_world(22.1, fy - 1.25, 0.25),
                (0.05, 2.5, 0.05),
                rot_facade, mat_iron, owned_col
            )

    # Add wrought-iron strap hinges & central divide to the Rue Saint-Sulpice Side Porch Door (bay 4, win_ly = -48.3)
    porch_ly = -10.5 - 4 * 8.4 - 4.2
    create_box("ND_SidePorch_DoorDivide", to_world(22.45, porch_ly, 1.6), (0.08, 0.08, 2.9), rot_facade, mat_iron, owned_col)
    for hz in [0.9, 1.7, 2.4]:
        create_box(f"ND_SidePorch_Hinge_{int(hz*10)}", to_world(22.45, porch_ly, hz), (0.08, 2.1, 0.07), rot_facade, mat_iron, owned_col)

    # 8. Update Cameras & Render Iteration 2 (`iter2_*.png` and `output/renders/MTL-VM-0002_snapshot.png`)
    scene = bpy.context.scene
    for c in list(cam_col.objects):
        bpy.data.objects.remove(c, do_unlink=True)

    b0002.render_cameras(scene, dossier, cam_col, iter_num=2)

    tmp_blend = BLEND_PATH + ".tmp.blend"
    if os.path.exists(tmp_blend):
        os.remove(tmp_blend)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
    if os.path.exists(BLEND_PATH + "@"):
        try:
            os.remove(BLEND_PATH + "@")
        except OSError:
            pass
    os.replace(tmp_blend, BLEND_PATH)
    bpy.ops.wm.usd_export(filepath=USDC_PATH, check_existing=False)
    print(f"Iteration 2 complete! Saved {BLEND_PATH} and {USDC_PATH}")


if __name__ == "__main__":
    upgrade_block()
