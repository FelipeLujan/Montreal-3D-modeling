#!/usr/bin/env python3
"""
High-Poly 3D Architecture, Buckminster Fuller Geodesic Dome (Biosphère) & Island Park Modeler — Block `MTL-VM-0038`
(`Île Sainte-Hélène West Shoreline, Biosphère Geodesic Dome & Parc Jean-Drapeau Waterfront`)
"""

import os
import sys
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.blender_lib import (
    clear_scene,
    setup_world_sky,
    load_dossier,
    apply_world_box_uv,
    build_ground_and_streets,
    build_corridor_material_palette,
    build_corridor_context_buildings,
    build_corridor_foliage_and_props,
    add_box_local,
    add_cylinder_along,
    append_kit_object,
    export_block_artifacts,
)

BLOCK_ID = "MTL-VM-0038"


def build_biosphere_geodesic_dome_and_park(col: bpy.types.Collection, dossier: dict, mats: dict):
    """
    Models Buckminster Fuller's iconic Expo 67 Montreal Biosphère geodesic dome:
    - Double-layer triangulated tubular steel lattice sphere (`R_outer = 38.0m`, `H = 62.0m`, centered at `(1964.8, 1043.4, 24.0)`)
    - Multi-level interior exhibition museum pavilions with recessed curtain-wall glazing (`glass_office`), concrete floor slabs, and observation decks
    - Reflecting pools along the South/West perimeter (`water_pool` / `dark_glass`) and geometric concrete entrance plaza with space-frame canopy on the West (`X = 1922..1937, Y = 1056..1071`)
    - Chemin du Tour-de-l'Isle curved asphalt roadway, concrete curb, parking bays with parked cars, and Parc Jean-Drapeau green wayfinding totems seen in Camera 4 (`Chemin_Tour_de_l_Isle_North`)
    - Gently rolling grassy hillock & park paths seen in Camera 1 (`Biosphere_Geodesic_Dome_Front`), Camera 2 (`Ile_Sainte_Helene_West_Promenade`), and Camera 3 (`Parc_Jean_Drapeau_Metro_Plaza`).
    """
    mesh = bpy.data.meshes.new("MTL_VM_0038_Biosphere_Geodesic_Dome")
    obj = bpy.data.objects.new("MTL_VM_0038_Biosphere_Geodesic_Dome", mesh)
    col.objects.link(obj)
    for k in (
        "white_trim",           # 0: Silver-White Painted Tubular Steel Geodesic Lattice & Space Frame
        "concrete_podium",      # 1: Architectural Precast Concrete Plazas, Curbs & Interior Pavilion Slabs
        "blue_curtain_glass",   # 2: Exhibition Pavilion Curtain Wall Glazing
        "dark_metal",           # 3: Structural Mullions, Lamp Posts, Sign Posts & Dark Car Trim
        "water_river",          # 4: Reflecting Pool Water Surface & Car Windshields
        "park_grass",           # 5: Sculpted Park Hillocks & Berms
        "roof_light_gravel",    # 6: Fine Gravel Park Walkways & Plaza Pavers
        "bridge_green_steel",   # 7: Parc Jean-Drapeau Iconic Green Wayfinding Totems
        "grey_limestone",       # 8: Historic Pavillon Hélène-de-Champlain Stone Cladding & Retaining Walls
        "roof_bitumen",         # 9: Asphalt Parking Lot & Roadway Aprons
    ):
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    uz = Vector((0.0, 0.0, 1.0))
    ux = Vector((1.0, 0.0, 0.0))
    uy = Vector((0.0, 1.0, 0.0))

    # 0. Lush Parc Jean-Drapeau Island Park Lawn (`X = 1800..2035, Y = 965..1145`)
    # Covers the grey urban block slab with green park grass (`park_grass`) while leaving the asphalt parking lot & roadways slightly proud (`Z = 0.08..0.14m`)
    add_box_local(bm, Vector((1904.4, 1055.3, 0.025)), ux, uy, uz, 175.0, 175.0, 0.05, mat_idx=5)

    # 1. Buckminster Fuller Montreal Biosphère Geodesic Dome (`X = 1964.8, Y = 1043.4`)
    # True 3/4 sphere: radius R = 38.0m, sphere center at Z = 24.0m (top at Z = 62.0m, base ring at Z = 0.0m, R_base = 29.5m)
    dome_xy = Vector((1964.8, 1043.4, 0.0))
    sphere_c = Vector((1964.8, 1043.4, 24.0))
    r_outer = 38.0
    r_inner = 36.3

    # Build a high-frequency icosahedral geodesic triangulation on the sphere
    bm_ico = bmesh.new()
    bmesh.ops.create_icosphere(bm_ico, subdivisions=4, radius=1.0)

    # Extract unique edges & vertices above Z_world >= -0.2m (which corresponds to unit sphere z >= -24.0 / 38.0 = -0.6316)
    z_cutoff = -24.0 / r_outer
    edge_pairs = []
    vert_normals = []
    for v in bm_ico.verts:
        n = v.co.normalized()
        if n.z >= z_cutoff - 0.04:
            vert_normals.append(n)
    for e in bm_ico.edges:
        n0 = e.verts[0].co.normalized()
        n1 = e.verts[1].co.normalized()
        if n0.z >= z_cutoff and n1.z >= z_cutoff:
            edge_pairs.append((n0, n1))
        elif (n0.z >= z_cutoff) != (n1.z >= z_cutoff):
            # Clip strut cleanly at ground plane Z = 0
            if n0.z < n1.z:
                n0, n1 = n1, n0
            t_clip = (n0.z - z_cutoff) / max(1e-5, n0.z - n1.z)
            n_clip = n0.lerp(n1, t_clip).normalized()
            edge_pairs.append((n0, n_clip))
    bm_ico.free()

    # Outer & inner geodesic steel lattice struts + radial web truss struts at nodes
    for n0, n1 in edge_pairs:
        p0_out = sphere_c + n0 * r_outer
        p1_out = sphere_c + n1 * r_outer
        p0_out.z = max(0.0, p0_out.z)
        p1_out.z = max(0.0, p1_out.z)
        add_cylinder_along(bm, p0_out, p1_out, 0.16, 0.16, segs=6, mat_idx=0)

        p0_in = sphere_c + n0 * r_inner
        p1_in = sphere_c + n1 * r_inner
        if p0_in.z >= 0.0 and p1_in.z >= 0.0:
            add_cylinder_along(bm, p0_in, p1_in, 0.12, 0.12, segs=6, mat_idx=0)

    for n in vert_normals:
        p_out = sphere_c + n * r_outer
        p_in = sphere_c + n * r_inner
        if p_out.z >= 0.2 and p_in.z >= 0.2:
            add_cylinder_along(bm, p_in, p_out, 0.11, 0.11, segs=6, mat_idx=0)

    # Concrete perimeter foundation ring & reflecting pool basin at base of Biosphère (`satellite_topdown.png`)
    add_cylinder_along(bm, dome_xy, dome_xy + uz * 0.45, 31.5, 31.2, segs=36, mat_idx=1)
    # South-West reflecting pool (`X = 1938..1962, Y = 995..1030` visible in bottom-right of satellite_topdown.png)
    pool_c = Vector((1950.0, 1004.0, 0.0))
    add_box_local(bm, pool_c + uz * 0.12, ux, uy, uz, 22.0, 42.0, 0.24, mat_idx=1)
    add_box_local(bm, pool_c + uz * 0.26, ux, uy, uz, 20.4, 40.4, 0.06, mat_idx=4)

    # Multi-level interior exhibition museum pavilions inside the geodesic sphere
    for lvl_i, (z_fl, rad_fl, h_fl) in enumerate((
        (0.4, 24.5, 4.8),
        (5.6, 23.0, 4.6),
        (10.6, 20.5, 4.6),
        (15.6, 17.5, 4.4),
        (20.4, 13.5, 4.2),
    )):
        # Concrete floor & ceiling slab
        add_cylinder_along(bm, dome_xy + uz * (z_fl - 0.35), dome_xy + uz * z_fl, rad_fl + 0.6, rad_fl + 0.6, segs=24, mat_idx=1)
        add_cylinder_along(bm, dome_xy + uz * (z_fl + h_fl), dome_xy + uz * (z_fl + h_fl + 0.35), rad_fl + 0.6, rad_fl + 0.6, segs=24, mat_idx=1)
        # Recessed glass curtain wall cylinder & vertical steel mullions
        add_cylinder_along(bm, dome_xy + uz * z_fl, dome_xy + uz * (z_fl + h_fl), rad_fl, rad_fl, segs=24, mat_idx=2)
        for m_ang in range(0, 360, 15):
            ang_r = math.radians(m_ang)
            m_pos = dome_xy + Vector((math.cos(ang_r) * (rad_fl + 0.08), math.sin(ang_r) * (rad_fl + 0.08), 0.0))
            add_cylinder_along(bm, m_pos + uz * z_fl, m_pos + uz * (z_fl + h_fl), 0.10, 0.10, segs=6, mat_idx=3)

    # West Entrance Space-Frame Canopy (`X = 1922..1937, Y = 1056..1071` visible in satellite_topdown.png)
    canopy_c = Vector((1929.5, 1064.2, 0.0))
    add_box_local(bm, canopy_c + uz * 0.18, ux, uy, uz, 18.0, 16.0, 0.36, mat_idx=6)
    add_box_local(bm, canopy_c + uz * 4.6, ux, uy, uz, 14.5, 13.5, 0.45, mat_idx=3)
    # Diagonal space-frame roof grid on West entrance canopy
    for sx in range(-6, 7, 2):
        p_a = canopy_c + Vector((sx, -6.5, 4.9))
        p_b = canopy_c + Vector((sx, 6.5, 4.9))
        add_cylinder_along(bm, p_a, p_b, 0.09, 0.09, segs=6, mat_idx=0)
    for sy in range(-6, 7, 2):
        p_a = canopy_c + Vector((-7.0, sy, 4.9))
        p_b = canopy_c + Vector((7.0, sy, 4.9))
        add_cylinder_along(bm, p_a, p_b, 0.09, 0.09, segs=6, mat_idx=0)
    for cx_off in (-6.2, 6.2):
        for cy_off in (-5.8, 5.8):
            cp = canopy_c + Vector((cx_off, cy_off, 0.0))
            add_cylinder_along(bm, cp, cp + uz * 4.6, 0.22, 0.22, segs=8, mat_idx=3)

    # 2.Biosphère Forecourt Parking Lot & Curved Access Road (`X = 1892..1938, Y = 1045..1125` in satellite_topdown.png)
    lot_c = Vector((1904.5, 1068.0, 0.0))
    f_lot = Vector((math.sin(math.radians(38.0)), math.cos(math.radians(38.0)), 0.0)).normalized()
    r_lot = Vector((f_lot.y, -f_lot.x, 0.0)).normalized()
    add_box_local(bm, lot_c + uz * 0.06, r_lot, f_lot, uz, 18.0, 48.0, 0.12, mat_idx=9)
    # White parking stall lines
    for st_i in range(-6, 7):
        sp = lot_c - r_lot * 5.5 + f_lot * (st_i * 2.8)
        add_box_local(bm, sp + uz * 0.13, r_lot, f_lot, uz, 5.0, 0.14, 0.02, mat_idx=0)

    # 3. Camera 1 Foreground (`Biosphere_Geodesic_Dome_Front`: pos=(1930.28, 1085.995), hdg=15°)
    # Shows grassy lawn on right with an ornamental tree at ~6.5m, mounded shrub bed on left-center, parked cars on far left, paved walkway on far right
    cam1 = Vector((1930.28, 1085.995, 0.0))
    f1 = Vector((math.sin(math.radians(15.0)), math.cos(math.radians(15.0)), 0.0)).normalized()
    r1 = Vector((f1.y, -f1.x, 0.0)).normalized()
    # Paved path on right edge of Camera 1
    add_box_local(bm, cam1 + f1 * 14.0 + r1 * 8.5 + uz * 0.08, r1, f1, uz, 3.2, 24.0, 0.16, mat_idx=6)
    # Low stone & shrub rockery mound in Camera 1 left-midground (`f1 * 9.5 - r1 * 3.2`)
    mound1 = cam1 + f1 * 9.5 - r1 * 3.2
    add_box_local(bm, mound1 + uz * 0.35, r1, f1, uz, 2.2, 1.8, 0.7, mat_idx=8)
    # Parked cars on far left of Camera 1 (`f1 * 12.5 - r1 * 8.5`)
    for pc_i, pc_x in enumerate((-9.5, -6.5)):
        car_p = cam1 + f1 * (12.5 + pc_i * 1.5) + r1 * pc_x
        add_box_local(bm, car_p + uz * 0.55, r1, f1, uz, 1.85, 4.2, 0.85, mat_idx=3)
        add_box_local(bm, car_p + uz * 1.15, r1, f1, uz, 1.60, 2.2, 0.55, mat_idx=4)

    # 4. Camera 2 Foreground (`Ile_Sainte_Helene_West_Promenade`: pos=(1795.821, 999.465), hdg=290°)
    # Shows a prominent park lamppost in the left foreground (`f2 * 2.4 - r2 * 1.35`) with a round cobra/saucer luminaire at top (`Z ~ 3.6m`), and a grassy slope rising on the right under dense tall deciduous trees!
    cam2 = Vector((1795.821, 999.465, 0.0))
    f2 = Vector((math.sin(math.radians(290.0)), math.cos(math.radians(290.0)), 0.0)).normalized()
    r2 = Vector((f2.y, -f2.x, 0.0)).normalized()
    # Foreground metallic lamppost on far left of Camera 2
    lp2 = cam2 + f2 * 2.35 - r2 * 1.28
    add_cylinder_along(bm, lp2, lp2 + uz * 3.55, 0.09, 0.065, segs=12, mat_idx=0)
    # Vertical banner bracket on pole
    add_box_local(bm, lp2 + uz * 1.85 + r2 * 0.08, r2, f2, uz, 0.24, 0.06, 0.95, mat_idx=0)
    # Saucer luminaire cap at top-left of Camera 2 (`V0, H0`)
    add_cylinder_along(bm, lp2 + uz * 3.45 - r2 * 0.12, lp2 + uz * 3.68 - r2 * 0.12, 0.42, 0.18, segs=16, mat_idx=3)
    # Gently rising grassy hillside berm on right side of Camera 2 (`f2 * 14.0 + r2 * 6.0`)
    add_box_local(bm, cam2 + f2 * 15.0 + r2 * 7.5 + uz * 0.85, r2, f2, uz, 14.0, 22.0, 1.7, mat_idx=5)

    # 5. Camera 3 Foreground (`Parc_Jean_Drapeau_Metro_Plaza`: pos=(1867.934, 983.64), hdg=350°)
    # Shows gravel footpath corner at bottom-right (`f3 * 3.5 + r3 * 1.8`), grassy park lawn, and wooden picnic table on the right (`f3 * 12.5 + r3 * 4.8`)
    cam3 = Vector((1867.934, 983.64, 0.0))
    f3 = Vector((math.sin(math.radians(350.0)), math.cos(math.radians(350.0)), 0.0)).normalized()
    r3 = Vector((f3.y, -f3.x, 0.0)).normalized()
    add_box_local(bm, cam3 + f3 * 3.2 + r3 * 2.2 + uz * 0.05, r3, f3, uz, 3.6, 4.5, 0.10, mat_idx=6)
    # Wooden picnic table under trees on right of Camera 3
    pt3 = cam3 + f3 * 12.0 + r3 * 4.6
    add_box_local(bm, pt3 + uz * 0.74, r3, f3, uz, 1.4, 2.2, 0.08, mat_idx=8)
    add_box_local(bm, pt3 - r3 * 0.85 + uz * 0.44, r3, f3, uz, 0.32, 2.2, 0.06, mat_idx=8)
    add_box_local(bm, pt3 + r3 * 0.85 + uz * 0.44, r3, f3, uz, 0.32, 2.2, 0.06, mat_idx=8)

    # 6. Camera 4 Foreground (`Chemin_Tour_de_l_Isle_North`: pos=(1884.338, 1162.378), hdg=195°)
    # Shows:
    # - Biosphère geodesic dome rising on the far left (`H0`, already aligned via world coords or reinforced visual massing)
    # - Curved concrete curb & asphalt roadway (`Chemin du Tour-de-l'Isle`) on the right (`H2..H3, V2..V3`)
    # - Grass median strip with two green-and-black Parc Jean-Drapeau wayfinding totems, a stop sign post on left, a tall curved heritage lamppost in center (`H2, V1..V2`), and parked cars in the parking lot!
    cam4 = Vector((1884.338, 1162.378, 0.0))
    f4 = Vector((math.sin(math.radians(195.0)), math.cos(math.radians(195.0)), 0.0)).normalized()
    r4 = Vector((f4.y, -f4.x, 0.0)).normalized()
    # Roadway & raised concrete curb along right side of Camera 4
    add_box_local(bm, cam4 + f4 * 14.0 + r4 * 5.2 + uz * 0.06, r4, f4, uz, 7.5, 32.0, 0.12, mat_idx=9)
    add_box_local(bm, cam4 + f4 * 14.0 + r4 * 1.45 + uz * 0.14, r4, f4, uz, 0.32, 32.0, 0.28, mat_idx=1)
    # Grassy median island (`r4 * -1.2`)
    add_box_local(bm, cam4 + f4 * 11.0 - r4 * 1.2 + uz * 0.10, r4, f4, uz, 5.0, 22.0, 0.20, mat_idx=5)
    # Parking lot asphalt & white lines behind median (`f4 * 18.0 - r4 * 6.0`)
    add_box_local(bm, cam4 + f4 * 18.0 - r4 * 6.0 + uz * 0.06, r4, f4, uz, 18.0, 26.0, 0.12, mat_idx=9)
    for st4 in range(-3, 4):
        add_box_local(bm, cam4 + f4 * (14.5 + st4 * 2.6) - r4 * 4.5 + uz * 0.13, r4, f4, uz, 4.8, 0.12, 0.02, mat_idx=0)
    # Parked cars in Camera 4 lot (`H0..H2, V2`)
    for c4_x, c4_y, c4_mat in ((-7.5, 15.0, 0), (-5.0, 15.5, 3), (-2.2, 16.0, 3), (1.2, 15.0, 3)):
        cp4 = cam4 + f4 * c4_y + r4 * c4_x
        add_box_local(bm, cp4 + uz * 0.52, f4, r4, uz, 1.8, 4.1, 0.82, mat_idx=c4_mat)
        add_box_local(bm, cp4 + uz * 1.10, f4, r4, uz, 1.55, 2.1, 0.52, mat_idx=4)
    # Foreground left Parc Jean-Drapeau green-and-black wayfinding totem (`f4 * 3.4 - r4 * 2.15`)
    tot1 = cam4 + f4 * 3.4 - r4 * 2.15
    add_box_local(bm, tot1 + uz * 1.15, r4, f4, uz, 0.18, 0.24, 2.3, mat_idx=3)
    add_box_local(bm, tot1 + uz * 2.35, r4, f4, uz, 0.20, 0.28, 0.55, mat_idx=7)
    # Second green wayfinding totem & dark sign board on right of median (`f4 * 13.5 + r4 * 3.4`)
    tot2 = cam4 + f4 * 13.5 + r4 * 3.4
    add_box_local(bm, tot2 + uz * 1.15, r4, f4, uz, 0.22, 0.26, 2.3, mat_idx=7)
    add_box_local(bm, tot2 - r4 * 0.55 + uz * 1.35, r4, f4, uz, 1.1, 0.14, 1.2, mat_idx=3)
    # Tall heritage lamppost in center of Camera 4 (`f4 * 10.5 + r4 * 1.2`)
    lp4 = cam4 + f4 * 10.5 + r4 * 1.2
    add_cylinder_along(bm, lp4, lp4 + uz * 5.8, 0.11, 0.08, segs=10, mat_idx=3)
    add_cylinder_along(bm, lp4 + uz * 5.4, lp4 + uz * 5.6 - r4 * 1.1, 0.05, 0.05, segs=8, mat_idx=3)
    add_cylinder_along(bm, lp4 + uz * 5.35 - r4 * 1.1, lp4 + uz * 5.65 - r4 * 1.1, 0.22, 0.12, segs=10, mat_idx=3)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.25)


def main():
    print(f"\n=== Building {BLOCK_ID}: Île Sainte-Hélène West Shoreline & Biosphère Geodesic Dome ===")
    clear_scene()
    setup_world_sky()
    dossier = load_dossier(BLOCK_ID)

    owned_col = bpy.data.collections.new(f"{BLOCK_ID}_Owned")
    bpy.context.scene.collection.children.link(owned_col)

    mats = build_corridor_material_palette()
    build_ground_and_streets(owned_col, dossier)
    build_biosphere_geodesic_dome_and_park(owned_col, dossier, mats)
    build_corridor_context_buildings(
        owned_col,
        dossier,
        mats,
        skip_ids={"26288030", "1254104361", "1254104362", "1254104363", "1266911675"},
    )

    # Extra trees strategically placed to match satellite_topdown.png & the 4 Street View cameras
    extra_trees = [
        # Camera 1 (`Biosphere_Geodesic_Dome_Front`: pos=(1930.28, 1085.995), hdg=15°): prominent ornamental tree on right at ~6.5m, plus background grove
        (1933.2, 1091.8, 0.85),
        (1928.5, 1102.0, 1.15),
        (1922.0, 1105.0, 1.35),
        (1916.0, 1102.0, 1.30),
        (1939.5, 1104.0, 1.10),
        # Camera 2 (`Ile_Sainte_Helene_West_Promenade`: pos=(1795.821, 999.465), hdg=290°): tall dense forest canopy across top & middle
        (1782.0, 1004.5, 1.45),
        (1778.5, 1009.0, 1.55),
        (1784.0, 1012.5, 1.50),
        (1774.0, 1002.0, 1.40),
        (1788.0, 1008.0, 1.35),
        # Camera 3 (`Parc_Jean_Drapeau_Metro_Plaza`: pos=(1867.934, 983.64), hdg=350°): prominent central tree at ~7.5m + flanking trees
        (1866.6, 991.0, 1.15),
        (1861.5, 994.5, 1.25),
        (1872.8, 993.5, 1.30),
        (1858.0, 992.0, 1.15),
        # Camera 4 (`Chemin_Tour_de_l_Isle_North`: pos=(1884.338, 1162.378), hdg=195°): tree line behind parking lot
        (1888.0, 1132.0, 1.35),
        (1878.0, 1130.0, 1.40),
        (1868.0, 1135.0, 1.35),
        (1862.0, 1145.0, 1.30),
        # West & North-West dense park woodland from satellite_topdown.png (`X = 1835..1915, Y = 990..1125`)
        (1845.0, 1000.0, 1.50),
        (1852.0, 1012.0, 1.45),
        (1842.0, 1025.0, 1.55),
        (1855.0, 1028.0, 1.45),
        (1846.0, 1042.0, 1.55),
        (1862.0, 1045.0, 1.50),
        (1872.0, 1038.0, 1.40),
        (1844.0, 1058.0, 1.55),
        (1856.0, 1065.0, 1.50),
        (1868.0, 1060.0, 1.40),
        (1845.0, 1075.0, 1.50),
        (1858.0, 1082.0, 1.45),
        (1868.0, 1088.0, 1.40),
        (1848.0, 1094.0, 1.50),
        (1862.0, 1102.0, 1.45),
        (1876.0, 1100.0, 1.40),
        (1888.0, 1108.0, 1.45),
        (1898.0, 1115.0, 1.40),
        (1912.0, 1118.0, 1.35),
        (1918.0, 1092.0, 1.30),
        (1930.0, 1020.0, 1.25),
        (1932.0, 1005.0, 1.25),
    ]
    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=65)
    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== Completed {BLOCK_ID} Build Successfully ===")


if __name__ == "__main__":
    main()
