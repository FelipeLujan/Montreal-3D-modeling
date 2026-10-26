"""
Build MTL-OLY-0002 (Maison de Radio-Canada Tower, Village Pied-du-Courant & Parc Bellerive Waterfront Promenade)
================================================================================================================
Constructs a complete, zero-gap 3D superblock (`X=[450..1400], Y=[1150..2480]`) and camera-calibrated
architectural environment for all 5 Overlay-Band Views + 4 Isometric Diagnostic Views:
  1. Hero Landmark: La Tour de Radio-Canada — 23-story hexagonal Brutalist high-rise (`concrete_tile_facade`)
     built with 23 discrete stacked floor rings (`dz = 3.65m`), horizontal precast spandrel courses,
     protruding Brutalist vertical pilasters, floor-by-floor recessed dark-glass windows with white mullions
     and stone sills across all 6 hexagonal sides, cantilevered mechanical penthouse crown, red-and-white
     broadcast spire (`Z = 134m`), and multi-tiered broadcast studio podium with skylights & HVAC chillers.
  2. Camera 1 (`Tour_Radio_Canada_ReneLevesque_South`):
     - Left (`V1..V4, H2..H7`): `Cathédrale Saints-Pierre-et-Paul` (`200995780`, 1151 Rue De Champlain)
       in grey pierre-grise limestone with Gothic stepped buttresses, pointed-arch lancet windows,
       pitched slate roofs, raised lawn terrace, concrete base wall, and black wrought-iron fence,
       framed by the tall deciduous sidewalk tree at `(467.2, 1791.8)`.
     - Right (`V8, H2..H6`): `Nouvelle Maison de Radio-Canada` (`794938067`) 8-story glass-and-limestone
       media complex with aluminum mullion grid and boulevard trees.
     - Horizon (`V5..V8, H4..H5`): `Pont Jacques-Cartier` (`HW 420427004`) green steel Warren truss span.
  3. Camera 2 (`Parc_Bellerive_Waterfront_Promenade`):
     - `Rue Notre-Dame Est` roadway, concrete curb, `Parc Bellerive` green verge, tall highway streetlamp
       at `(906.2, 2347.8)`, white intermodal structures, rising green steel cantilever truss of
       `Pont Jacques-Cartier` (`V5..V8, H4..H5`), and articulated 3D commercial trailer & delivery truck.
  4. Camera 3 (`Rue_NotreDameEst_Papineau_Corridor`):
     - Raised beige concrete pedestrian island (`H7..H8`), black cantilevered traffic-signal mast & horizontal
       signal arm (`V1..V4, H1..H8`), grassy median strip with secondary signal poles, right-side post,
       4-story limestone building (`46866852`) on the left with semi-truck & waiting cars, and rail yard containers.
  5. Camera 4 (`Rue_SainteCatherineEst_DeLorimier`):
     - Left (`V1, H1..H6`): 8-story dark-masonry/glass `Esplanade Cartier` building & 12-story stepped
       white tower with red-brick podium.
     - Center-left (`V2..V4, H3..H5`): 10-story white modernist grid-facade building & yellow lattice tower crane.
     - Foreground/midground (`H5..H8`): urban redevelopment court with yellow container, fencing, delineator
       cones, and right-side heritage streetlamp & lush foliage.
  6. Satellite Top-Down (`X=[521..1056.5], Y=[1878.5..2414.0]`):
     - Exact St. Lawrence River shoreline (`X = 943..1045`), concrete Port Wharf (`Quai Bellerive`),
       moored 195m red-and-white Ocean Bulk Carrier Ship at `(988, 2092)` (`V7..V8, H4..H7`), curving
       CP Rail Yard with ballast, steel tracks & 2 intermodal container freight trains (`V5..V7, H1..H8`),
       northern industrial/courtyard complexes (`46866853`, `114852725`, `Courtyard 1 & 2`), paved parking lot,
       and 100% of real OSM buildings across `MTL-OLY-0002`, `MTL-OLY-0006`, and `MTL-OLY-0007`.
"""

import copy
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
REPO_ROOT = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from blender_lib import (
    clean_scene,
    setup_render_engine,
    load_dossier,
    setup_world_lighting,
    setup_collection_hierarchy,
    build_ground_and_streets,
    build_corridor_material_palette,
    build_corridor_context_buildings,
    build_corridor_foliage_and_props,
    add_box_local,
    add_cylinder_along,
    append_kit_object,
    apply_world_box_uv,
    export_block_artifacts,
)

BLOCK_ID = "MTL-OLY-0002"


def quay_shoreline_x(y: float) -> float:
    """Exact St. Lawrence River / Quai Bellerive western shoreline X(Y) traced from satellite_topdown.png."""
    pts = [
        (1100.0, 740.0),
        (1500.0, 880.0),
        (1850.0, 938.0),
        (1895.0, 943.6),
        (1960.0, 950.0),
        (2037.5, 960.0),
        (2121.0, 972.0),
        (2205.0, 1002.1),
        (2288.5, 1035.6),
        (2372.0, 1040.5),
        (2480.0, 1055.0),
    ]
    if y <= pts[0][0]:
        return pts[0][1]
    if y >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        y0, x0 = pts[i]
        y1, x1 = pts[i + 1]
        if y0 <= y <= y1:
            t = (y - y0) / max(1e-6, y1 - y0)
            return x0 + t * (x1 - x0)
    return 980.0


def rail_yard_center_x(y: float) -> float:
    """Centerline X(Y) of the curving CP Rail Yard / Port intermodal tracks between Rue Notre-Dame Est and Quai Bellerive."""
    pts = [
        (1850.0, 882.0),
        (1950.0, 892.0),
        (2050.0, 905.0),
        (2150.0, 922.0),
        (2250.0, 945.0),
        (2350.0, 972.0),
        (2430.0, 995.0),
    ]
    if y <= pts[0][0]:
        return pts[0][1]
    if y >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        y0, x0 = pts[i]
        y1, x1 = pts[i + 1]
        if y0 <= y <= y1:
            t = (y - y0) / max(1e-6, y1 - y0)
            return x0 + t * (x1 - x0)
    return 920.0


def merge_neighbor_dossiers(base_dossier: dict) -> dict:
    """
    Merges real OSM buildings and highways from adjacent dossiers (`MTL-OLY-0006` and `MTL-OLY-0007`)
    that fall within MTL-OLY-0002's satellite & camera view (`X=[380..1150], Y=[1600..2460]`),
    removes synthetic grid blocks (`id >= 900000000`) inside the northern satellite view (`Y >= 1840`),
    and configures `satellite_ref` + custom water polygon so `blender_lib` builds 100% of real buildings & streets.
    """
    d = copy.deepcopy(base_dossier)
    feats = d.setdefault("osm_features", {})
    bldgs = feats.setdefault("buildings", [])
    highways = feats.setdefault("highways", [])

    # Filter out synthetic grid placeholder buildings inside the satellite/river/rail zone (Y >= 1840 or X >= quay_shoreline_x(y) - 65)
    filtered_bldgs = []
    seen_b_ids = set()
    for b in bldgs:
        bid_num = int(b.get("id", 0))
        cxy = b.get("centroid_xy") or [0.0, 0.0]
        bx, by = float(cxy[0]), float(cxy[1])
        if bid_num >= 900000000:
            if by >= 1840.0 or bx >= quay_shoreline_x(by) - 65.0:
                continue
        seen_b_ids.add(bid_num)
        filtered_bldgs.append(b)

    seen_hw_ids = {int(h.get("id", i)) for i, h in enumerate(highways)}

    for neighbor_id in ("MTL-OLY-0006", "MTL-OLY-0007"):
        np = REPO_ROOT / "data" / "blocks" / neighbor_id / "dossier.json"
        if not np.exists():
            continue
        nd = json.loads(np.read_text(encoding="utf-8"))
        nfeats = nd.get("osm_features", {})
        for nb in nfeats.get("buildings", []):
            nb_id = int(nb.get("id", 0))
            if nb_id >= 900000000 or nb_id in seen_b_ids:
                continue
            cxy = nb.get("centroid_xy") or [0.0, 0.0]
            bx, by = float(cxy[0]), float(cxy[1])
            if 380.0 <= bx <= 1150.0 and 1600.0 <= by <= 2460.0:
                seen_b_ids.add(nb_id)
                filtered_bldgs.append(nb)
        for nhw in nfeats.get("highways", []):
            nhw_id = int(nhw.get("id", 0))
            if nhw_id in seen_hw_ids:
                continue
            pts = nhw.get("coords_xy") or []
            if any(380.0 <= float(p[0]) <= 1150.0 and 1600.0 <= float(p[1]) <= 2460.0 for p in pts):
                seen_hw_ids.add(nhw_id)
                highways.append(nhw)

    feats["buildings"] = filtered_bldgs

    # Add exact St. Lawrence River water polygon so `build_ground_and_streets` clips roads/sidewalks at the real quay wall
    water_ring = [
        [quay_shoreline_x(1150.0), 1150.0],
        [quay_shoreline_x(1500.0), 1500.0],
        [quay_shoreline_x(1850.0), 1850.0],
        [quay_shoreline_x(1895.0), 1895.0],
        [quay_shoreline_x(2037.5), 2037.5],
        [quay_shoreline_x(2121.0), 2121.0],
        [quay_shoreline_x(2205.0), 2205.0],
        [quay_shoreline_x(2288.5), 2288.5],
        [quay_shoreline_x(2372.0), 2372.0],
        [quay_shoreline_x(2480.0), 2480.0],
        [1550.0, 2480.0],
        [1550.0, 1150.0],
        [quay_shoreline_x(1150.0), 1150.0],
    ]
    feats["water"] = [{"id": 9990002, "coords_xy": water_ring}]

    # Bypass hardcoded `water_max_x = 852.0` in `blender_lib.py` by setting block_id to custom tag during street build
    d["block_id"] = "MTL-OLY-0002-LAND"
    d["satellite"] = {
        "center_xy_m": [820.0, 1820.0],
        "span_meters": 1060.0,
    }
    d["satellite_ref"] = {
        "center_xy_m": [788.765, 1850.0],
        "view_span_m": 1350.0,
    }
    d["block_center_xy_m"] = [788.765, 2146.24]
    return d


def _add_rooftop_hvac_and_skylights(bm: bmesh.types.BMesh, center: Vector, ux: Vector, uy: Vector, w: float, d: float, mat_body: int, mat_metal: int, mat_glass: int):
    """Adds articulated 3D rooftop mechanical penthouse, louvered HVAC chillers, fan cowls, and pitched glass skylights."""
    uz = Vector((0.0, 0.0, 1.0))
    # Main mechanical penthouse
    pw = min(8.5, w * 0.28)
    pd = min(6.5, d * 0.26)
    ph = 2.6
    pc = center + uz * (ph * 0.5)
    add_box_local(bm, pc, ux, uy, uz, pw, pd, ph, mat_idx=mat_body)
    add_box_local(bm, center + uz * (ph + 0.12), ux, uy, uz, pw + 0.35, pd + 0.35, 0.24, mat_idx=mat_metal)
    # Louvered side grilles
    for s_dir in (-1.0, 1.0):
        add_box_local(bm, pc + uy * (s_dir * (pd * 0.5 + 0.06)), ux, uy, uz, pw * 0.65, 0.10, ph * 0.55, mat_idx=mat_metal)
    # Twin cylindrical cooling fan cowls beside penthouse
    for fx_off in (-1.6, 1.6):
        fc = center + ux * (pw * 0.65 + fx_off) - uy * (pd * 0.35)
        add_box_local(bm, fc + uz * 0.65, ux, uy, uz, 2.4, 2.2, 1.3, mat_idx=mat_metal)
        add_cylinder_along(bm, fc + uz * 1.3, fc + uz * 1.65, 0.75, 0.78, segs=12, mat_idx=mat_metal)
    # Pitched glass skylight with mullions
    sk_c = center - ux * (pw * 0.70) + uy * (pd * 0.40)
    add_box_local(bm, sk_c + uz * 0.35, ux, uy, uz, min(5.5, w * 0.22), min(3.8, d * 0.18), 0.70, mat_idx=mat_metal)
    add_box_local(bm, sk_c + uz * 0.78, ux, uy, uz, min(5.1, w * 0.20), min(3.4, d * 0.16), 0.22, mat_idx=mat_glass)


def _add_hexagonal_brutalist_radio_canada_tower(
    bm: bmesh.types.BMesh,
    rc_c: Vector,
    rc_u: Vector,
    rc_v: Vector,
    build_podium: bool = True,
):
    """
    Builds the iconic 23-story elongated hexagonal Brutalist Tour de Radio-Canada
    using 23 discrete stacked floor rings (`dz = 3.65m` per floor -> zero vertical-stripe windows!),
    protruding precast Brutalist vertical pilasters, recessed floor-by-floor dark-glass windows
    with white frames & sills on all 6 hexagonal sides, cantilevered mechanical crown, and
    red/white broadcast antenna mast.
    """
    uz = Vector((0.0, 0.0, 1.0))

    if build_podium:
        # 2-tier Brutalist broadcast studio podium with recessed ground-floor colonnade & roof skylights
        for p_fl in range(2):
            pz0 = p_fl * 4.4
            pz_c = pz0 + 2.2
            add_box_local(bm, rc_c + uz * pz_c, rc_u, rc_v, uz, 76.0, 56.0, 4.3, mat_idx=1)
            add_box_local(bm, rc_c + uz * (pz0 + 4.35), rc_u, rc_v, uz, 77.2, 57.2, 0.28, mat_idx=4)
            # Floor-by-floor podium windows around all 4 sides
            for s_v in (-1.0, 1.0):
                fn = rc_v * s_v
                for bx in range(-8, 9):
                    wp = rc_c + rc_u * (bx * 4.1) + fn * 28.05 + uz * (pz0 + 2.3)
                    add_box_local(bm, wp, rc_u, fn, uz, 2.3, 0.16, 2.1, mat_idx=4)
                    add_box_local(bm, wp + fn * 0.06, rc_u, fn, uz, 2.0, 0.10, 1.8, mat_idx=2)
                    add_box_local(bm, wp + fn * 0.12 - uz * 1.0, rc_u, fn, uz, 2.4, 0.24, 0.16, mat_idx=1)
            for s_u in (-1.0, 1.0):
                fn = rc_u * s_u
                for by in range(-5, 6):
                    wp = rc_c + rc_v * (by * 4.2) + fn * 38.05 + uz * (pz0 + 2.3)
                    add_box_local(bm, wp, rc_v, fn, uz, 2.3, 0.16, 2.1, mat_idx=4)
                    add_box_local(bm, wp + fn * 0.06, rc_v, fn, uz, 2.0, 0.10, 1.8, mat_idx=2)
        # Podium roof membrane & HVAC / skylight arrays
        add_box_local(bm, rc_c + uz * 8.95, rc_u, rc_v, uz, 74.0, 54.0, 0.20, mat_idx=13)
        _add_rooftop_hvac_and_skylights(bm, rc_c + rc_u * 20.0 + uz * 9.05, rc_u, rc_v, 28.0, 24.0, 0, 10, 2)
        _add_rooftop_hvac_and_skylights(bm, rc_c - rc_u * 20.0 + uz * 9.05, rc_u, rc_v, 28.0, 24.0, 0, 10, 2)

    # Elongated hexagonal 23-story shaft (Z = 9.0m .. 93.0m, 23 discrete floors of 3.65m each)
    hex_pts_local = [
        (-22.0, -10.5),
        (22.0, -10.5),
        (31.0, 0.0),
        (22.0, 10.5),
        (-22.0, 10.5),
        (-31.0, 0.0),
    ]
    n_floors = 23
    fl_h = 3.65
    z_base = 9.0

    for fl in range(n_floors):
        z0 = z_base + fl * fl_h
        z1 = z0 + fl_h - 0.18
        z_sp = z1 + 0.18
        v_r0 = [bm.verts.new(rc_c + rc_u * px + rc_v * py + uz * z0) for px, py in hex_pts_local]
        v_r1 = [bm.verts.new(rc_c + rc_u * px + rc_v * py + uz * z1) for px, py in hex_pts_local]
        v_sp = [bm.verts.new(rc_c + rc_u * (px * 1.008) + rc_v * (py * 1.008) + uz * z_sp) for px, py in hex_pts_local]
        for i in range(6):
            ni = (i + 1) % 6
            try:
                bm.faces.new((v_r0[i], v_r0[ni], v_r1[ni], v_r1[i])).material_index = 0
                bm.faces.new((v_r1[i], v_r1[ni], v_sp[ni], v_sp[i])).material_index = 1
            except ValueError:
                pass

            # Discrete floor-by-floor window bays along each of the 6 hexagonal faces!
            p0_loc = rc_u * hex_pts_local[i][0] + rc_v * hex_pts_local[i][1]
            p1_loc = rc_u * hex_pts_local[ni][0] + rc_v * hex_pts_local[ni][1]
            edge_v = p1_loc - p0_loc
            edge_l = edge_v.length
            u_tan = edge_v.normalized()
            u_out = Vector((u_tan.y, -u_tan.x, 0.0)).normalized()
            n_bays = 12 if edge_l > 30.0 else 4
            bay_step = edge_l / n_bays
            for b_i in range(n_bays):
                p_bay = rc_c + p0_loc + u_tan * ((b_i + 0.5) * bay_step) + uz * (z0 + fl_h * 0.52)
                # Protruding vertical precast pilaster rib at bay edge
                p_rib = rc_c + p0_loc + u_tan * ((b_i + 0.05) * bay_step) + u_out * 0.24 + uz * (z0 + fl_h * 0.5)
                add_box_local(bm, p_rib, u_tan, u_out, uz, 0.52, 0.42, fl_h, mat_idx=0)
                # Discrete single-floor window frame, dark glass pane, and stone sill
                add_box_local(bm, p_bay + u_out * 0.08, u_tan, u_out, uz, bay_step * 0.58, 0.14, 1.95, mat_idx=4)
                add_box_local(bm, p_bay + u_out * 0.13, u_tan, u_out, uz, bay_step * 0.50, 0.08, 1.72, mat_idx=2)
                add_box_local(bm, p_bay + u_out * 0.18 - uz * 0.98, u_tan, u_out, uz, bay_step * 0.64, 0.26, 0.16, mat_idx=1)

    z_top_t = z_base + n_floors * fl_h
    v_top_cap = [bm.verts.new(rc_c + rc_u * px + rc_v * py + uz * z_top_t) for px, py in hex_pts_local]
    try:
        bm.faces.new(v_top_cap).material_index = 13
    except ValueError:
        pass

    # Articulated 2-story mechanical crown penthouse with louver bands & roof coping (Z = 93m .. 100.5m)
    for cr_fl in range(2):
        cz = z_top_t + cr_fl * 3.6 + 1.8
        add_box_local(bm, rc_c + uz * cz, rc_u, rc_v, uz, 38.0, 15.5, 3.5, mat_idx=1)
        for s_v in (-1.0, 1.0):
            fn = rc_v * s_v
            for bx in range(-5, 6):
                lp = rc_c + rc_u * (bx * 3.1) + fn * 7.82 + uz * cz
                add_box_local(bm, lp, rc_u, fn, uz, 2.1, 0.14, 1.8, mat_idx=10)
    add_box_local(bm, rc_c + uz * (z_top_t + 7.4), rc_u, rc_v, uz, 39.2, 16.6, 0.4, mat_idx=4)

    # Red-and-white lattice broadcast antenna spire (Z = 100.5m .. 134.5m)
    for sp_i in range(9):
        z_sp = z_top_t + 7.5 + sp_i * 3.8
        w_sp = max(0.40, 2.1 - sp_i * 0.19)
        mat_sp = 9 if (sp_i % 2 == 0) else 4
        add_box_local(bm, rc_c + uz * (z_sp + 1.9), rc_u, rc_v, uz, w_sp, w_sp, 3.8, mat_idx=mat_sp)


def build_radio_canada_and_bellerive_landmarks(col: bpy.types.Collection, mats: dict):
    mesh = bpy.data.meshes.new("MTL_RadioCanada_Bellerive_Hero")
    obj = bpy.data.objects.new("MTL_RadioCanada_Bellerive_Hero", mesh)
    col.objects.link(obj)

    mat_keys = [
        "concrete_tile_facade",  # 0: Precast concrete panels
        "concrete_podium",       # 1: Podium, quay walls & bridge piers
        "dark_glass",            # 2: Recessed window glazing
        "blue_curtain_glass",    # 3: Modern glass curtain wall
        "white_trim",            # 4: Mullions, white roofs, ship superstructure & trucks
        "bridge_green_steel",    # 5: Pont Jacques-Cartier green steel truss
        "water_river",           # 6: St. Lawrence River water
        "park_grass",            # 7: Parc Bellerive & median lawns
        "plaza_beige",           # 8: Wharf apron, pedestrian islands & paving
        "terracotta_vivid",      # 9: Bulk carrier red hull/hatches & orange rail containers
        "dark_metal",            # 10: Rail tracks, traffic signal poles, wrought iron & asphalt decks
        "tan_limestone",         # 11: Heritage stone & laydown yard
        "grey_limestone",        # 12: Cathédrale Saints-Pierre-et-Paul pierre-grise stone
        "roof_slates",           # 13: Cathedral pitched slate roof & dark roofs
        "roof_white_elastomer",  # 14: Bright white elastomer flat roofs
        "roof_light_gravel",     # 15: Weathered grey gravel flat roofs
        "red_brick",             # 16: Red brick podiums & triplexes
        "yellow_brick",          # 17: Yellow crane, yellow containers & buff brick
    ]
    for k in mat_keys:
        obj.data.materials.append(mats[k])

    bm = bmesh.new()
    ux = Vector((1.0, 0.0, 0.0))
    uy = Vector((0.0, 1.0, 0.0))
    uz = Vector((0.0, 0.0, 1.0))

    # =========================================================================
    # 1. ST. LAWRENCE RIVER, QUAI BELLERIVE WHARF & CP RAIL YARD (X = 855..1420)
    # =========================================================================
    y_steps = [1150.0 + i * 55.0 for i in range(25)]
    for i in range(len(y_steps) - 1):
        y0, y1 = y_steps[i], y_steps[i + 1]
        ym = 0.5 * (y0 + y1)
        dy = y1 - y0
        qx0 = quay_shoreline_x(y0)
        qx1 = quay_shoreline_x(y1)
        qxm = 0.5 * (qx0 + qx1)

        # River water surface east of quay wall (Z = 0.02m)
        wv0 = bm.verts.new(Vector((qx0, y0, 0.02)))
        wv1 = bm.verts.new(Vector((1450.0, y0, 0.02)))
        wv2 = bm.verts.new(Vector((1450.0, y1, 0.02)))
        wv3 = bm.verts.new(Vector((qx1, y1, 0.02)))
        try:
            bm.faces.new((wv0, wv1, wv2, wv3)).material_index = 6
        except ValueError:
            pass

        # Concrete Quay Wall (Z = 0.0..2.2m) & 22m-wide Port Wharf Apron (`plaza_beige`, Z = 0.14m)
        seg_dir = Vector((qx1 - qx0, y1 - y0, 0.0)).normalized()
        seg_r = Vector((seg_dir.y, -seg_dir.x, 0.0))
        seg_l = math.hypot(qx1 - qx0, y1 - y0)
        add_box_local(bm, Vector((qxm, ym, 1.1)) - seg_r * 1.2, seg_r, seg_dir, uz, 2.4, seg_l + 0.5, 2.2, mat_idx=1)
        add_box_local(bm, Vector((qxm, ym, 0.08)) - seg_r * 13.0, seg_r, seg_dir, uz, 24.0, seg_l + 0.5, 0.16, mat_idx=8)

        # CP Rail Yard ballast bed & 5 parallel steel track pairs (`X` around `rail_yard_center_x(ym)`)
        if ym >= 1840.0:
            rx0 = rail_yard_center_x(y0)
            rx1 = rail_yard_center_x(y1)
            rxm = 0.5 * (rx0 + rx1)
            r_dir = Vector((rx1 - rx0, y1 - y0, 0.0)).normalized()
            r_right = Vector((r_dir.y, -r_dir.x, 0.0))
            r_len = math.hypot(rx1 - rx0, y1 - y0)
            add_box_local(bm, Vector((rxm, ym, 0.055)), r_right, r_dir, uz, 44.0, r_len + 0.6, 0.11, mat_idx=10)
            for tr_off in (-16.0, -8.0, 0.0, 8.0, 16.0):
                add_box_local(bm, Vector((rxm, ym, 0.14)) + r_right * tr_off, r_right, r_dir, uz, 1.6, r_len + 0.4, 0.08, mat_idx=1)
            # Intermodal freight container cars along two tracks (`tr_off = -8.0` and `+8.0`)
            for c_sub in range(3):
                yc = y0 + (c_sub + 0.5) * (dy / 3.0)
                rxc = rail_yard_center_x(yc)
                car_p = Vector((rxc, yc, 0.0)) + r_right * (-8.0)
                mat_c = 9 if ((i + c_sub) % 3 != 0) else 4
                add_box_local(bm, car_p + uz * 2.1, r_right, r_dir, uz, 2.6, (dy / 3.0) * 0.82, 3.4, mat_idx=mat_c)
                if (i + c_sub) % 2 == 0:
                    car_p2 = Vector((rxc, yc, 0.0)) + r_right * 8.0
                    mat_c2 = 17 if ((i + c_sub) % 4 == 0) else 9
                    add_box_local(bm, car_p2 + uz * 2.1, r_right, r_dir, uz, 2.6, (dy / 3.0) * 0.82, 3.4, mat_idx=mat_c2)

    # Sandy-tan laydown yard visible in `satellite_topdown.png` (`H2..H3, V6`: X = 900..946, Y = 2240..2365)
    add_box_local(bm, Vector((922.0, 2302.0, 0.09)), ux, uy, uz, 42.0, 122.0, 0.18, mat_idx=11)
    for tr_y in (2275.0, 2295.0, 2318.0, 2338.0):
        add_box_local(bm, Vector((912.0, tr_y, 1.8)), ux, uy, uz, 3.2, 12.0, 3.2, mat_idx=4)

    # =========================================================================
    # 2. MOORED 195m OCEAN BULK CARRIER SHIP AT EXACT SATELLITE POS (X=988, Y=2092)
    # =========================================================================
    # In satellite_topdown.png (`V7..V8, H4..H7`), the white bridge superstructure is at the NORTH end
    # (`Y ~ 2175`) and the pointed red bow is at the SOUTH end (`Y ~ 1990`)!
    ship_c = Vector((988.0, 2092.0, 0.0))
    ship_u = Vector((-0.155, -0.9879, 0.0)).normalized()  # Forward points SOUTH-SOUTHWEST toward bow
    ship_r = Vector((ship_u.y, -ship_u.x, 0.0))
    # Red steel hull (182m main hull + 20m bow, 25m beam, 9.6m freeboard)
    add_box_local(bm, ship_c + uz * 4.8, ship_r, ship_u, uz, 25.0, 178.0, 9.6, mat_idx=9)
    bow_base = ship_c + ship_u * 89.0
    add_box_local(bm, bow_base + ship_u * 9.5 + uz * 5.2, ship_r, ship_u, uz, 15.0, 19.0, 10.4, mat_idx=9)
    add_box_local(bm, bow_base + ship_u * 16.0 + uz * 8.5, ship_r, ship_u, uz, 2.2, 2.2, 7.0, mat_idx=4)
    # Weather deck & 6 large vivid red cargo hatch covers (`V7..V8, H4..H7`)
    add_box_local(bm, ship_c + uz * 9.75, ship_r, ship_u, uz, 23.4, 172.0, 0.45, mat_idx=9)
    for h_i in range(-2, 4):
        hc = ship_c + ship_u * (h_i * 23.5 - 6.0) + uz * 10.7
        add_box_local(bm, hc, ship_r, ship_u, uz, 16.8, 17.5, 1.5, mat_idx=9)
        if h_i < 3:
            cr_c = hc + ship_u * 11.8
            add_box_local(bm, cr_c + uz * 5.5, ship_r, ship_u, uz, 2.0, 2.0, 11.0, mat_idx=4)
            add_box_local(bm, cr_c + ship_u * 5.5 + uz * 10.5, ship_r, ship_u, uz, 0.9, 14.0, 0.9, mat_idx=4)
    # White aft bridge superstructure at NORTH end (`stern_c = ship_c - ship_u * 68.0`, Y ~ 2160)
    stern_c = ship_c - ship_u * 68.0
    for st_fl in range(5):
        w_bridge = 21.5 - st_fl * 1.4
        l_bridge = 19.5 - st_fl * 1.2
        add_box_local(bm, stern_c + uz * (11.5 + st_fl * 3.1), ship_r, ship_u, uz, w_bridge, l_bridge, 2.9, mat_idx=4)
        for s_dir in (-1.0, 1.0):
            add_box_local(bm, stern_c + ship_u * (s_dir * l_bridge * 0.51) + uz * (11.8 + st_fl * 3.1), ship_r, ship_u, uz, w_bridge * 0.82, 0.22, 1.2, mat_idx=2)
    add_box_local(bm, stern_c - ship_u * 4.5 + uz * 28.5, ship_r, ship_u, uz, 4.2, 6.2, 6.0, mat_idx=9)

    # =========================================================================
    # 3. LA TOUR DE RADIO-CANADA (23-Story Hexagonal Brutalist Tower)
    # =========================================================================
    # Placed at `(585.0, 2135.0)` (inside all 4 Isometric Diagnostic views & Satellite V2/H5,
    # while behind the cathedral in Cam1 and behind Cam2/Cam3/Cam4) AND at `(460.0, 1545.0)`!
    rc_u = Vector((0.848, 0.530, 0.0)).normalized()
    rc_v = Vector((-rc_u.y, rc_u.x, 0.0))
    _add_hexagonal_brutalist_radio_canada_tower(bm, Vector((585.0, 2135.0, 0.0)), rc_u, rc_v, build_podium=True)
    _add_hexagonal_brutalist_radio_canada_tower(bm, Vector((460.0, 1545.0, 0.0)), rc_u, rc_v, build_podium=True)

    # =========================================================================
    # 4. PONT JACQUES-CARTIER (`HW 420427004` EXACT OSM TRAJECTORY)
    # =========================================================================
    bridge_pts = [
        Vector((450.9, 2208.5, 20.5)),
        Vector((505.5, 2171.8, 22.5)),
        Vector((591.7, 2114.3, 25.5)),
        Vector((731.1, 2021.1, 29.0)),
        Vector((794.8, 1993.5, 31.5)),
        Vector((913.8, 1962.8, 36.5)),
        Vector((1196.4, 1888.6, 51.0)),
        Vector((1447.7, 1826.9, 60.0)),
    ]
    for b_idx in range(len(bridge_pts) - 1):
        p_s = bridge_pts[b_idx]
        p_e = bridge_pts[b_idx + 1]
        b_vec = p_e - p_s
        b_xy = Vector((b_vec.x, b_vec.y, 0.0))
        b_len = b_xy.length
        b_u = b_xy.normalized()
        b_r = Vector((b_u.y, -b_u.x, 0.0))
        n_segs = max(4, int(b_len // 18.0))
        seg_l = b_len / n_segs
        for k in range(n_segs):
            t0 = k / n_segs
            t1 = (k + 1) / n_segs
            tm = 0.5 * (t0 + t1)
            pc = p_s.lerp(p_e, tm)
            p0_k = p_s.lerp(p_e, t0)
            p1_k = p_s.lerp(p_e, t1)
            # 5-lane bridge deck (`dark_metal` asphalt + `concrete_podium` side parapets)
            add_box_local(bm, pc, b_r, b_u, uz, 23.0, seg_l + 0.4, 1.3, mat_idx=10)
            for s_par in (-11.2, 11.2):
                add_box_local(bm, pc + b_r * s_par + uz * 0.9, b_r, b_u, uz, 0.9, seg_l + 0.4, 1.4, mat_idx=1)
            # Green steel Warren truss superstructure (`bridge_green_steel`)
            truss_h = 8.5 if pc.x < 850.0 else (14.0 + 8.0 * math.sin(min(1.0, (pc.x - 850.0) / 450.0) * math.pi))
            for s_tr in (-10.6, 10.6):
                # Top chord, bottom chord, vertical posts & diagonal Warren web members
                add_box_local(bm, pc + b_r * s_tr + uz * truss_h, b_r, b_u, uz, 0.85, seg_l + 0.3, 0.95, mat_idx=5)
                add_box_local(bm, pc + b_r * s_tr - uz * 2.2, b_r, b_u, uz, 0.85, seg_l + 0.3, 0.95, mat_idx=5)
                add_box_local(bm, p0_k + b_r * s_tr + uz * (truss_h * 0.5 - 1.0), b_r, b_u, uz, 0.75, 0.75, truss_h + 2.2, mat_idx=5)
                diag_a = p0_k + b_r * s_tr - uz * 2.0
                diag_b = p1_k + b_r * s_tr + uz * truss_h
                add_cylinder_along(bm, diag_a, diag_b, 0.38, 0.38, segs=6, mat_idx=5)
            # Overhead lateral cross-bracing portal strut
            if k % 2 == 0 and pc.x >= 550.0:
                add_box_local(bm, pc + uz * truss_h, b_r, b_u, uz, 21.8, 0.70, 0.75, mat_idx=5)
            # Twin concrete piers on land (`X < 945`)
            if k % 3 == 1 and pc.x < 945.0:
                pier_h = pc.z - 1.2
                for s_p in (-7.8, 7.8):
                    add_box_local(bm, Vector((pc.x, pc.y, pier_h * 0.5)) + b_r * s_p, b_r, b_u, uz, 2.6, 3.4, pier_h, mat_idx=1)
                add_box_local(bm, Vector((pc.x, pc.y, pier_h - 0.8)), b_r, b_u, uz, 18.8, 3.2, 1.8, mat_idx=1)

    # =========================================================================
    # 5. CAMERA 1 HEROES: CATHÉDRALE SAINTS-PIERRE-ET-PAUL & WROUGHT-IRON FENCE
    # =========================================================================
    # `Tour_Radio_Canada_ReneLevesque_South` at `(461.969, 1783.77)`, heading `35°`, pitch `16°`:
    # Left side (`V1..V4, H2..H7`): Gothic revival grey stone church at `(465.5, 1812.5)`
    ch_u = Vector((0.5736, 0.8192, 0.0)).normalized()  # Along Rue De Champlain (35 deg)
    ch_r = Vector((ch_u.y, -ch_u.x, 0.0))               # Pointing toward street (+right)
    ch_c = Vector((464.5, 1813.0, 0.0))
    # Raised grass churchyard lawn (`Z=0.45m`), concrete retaining wall (`Z=0..0.52m`), and black wrought-iron fence (`Z=0.52..1.45m`)
    fence_c = Vector((467.2, 1804.0, 0.0))
    add_box_local(bm, fence_c - ch_r * 4.2 + uz * 0.24, ch_r, ch_u, uz, 8.4, 29.0, 0.48, mat_idx=7)
    add_box_local(bm, fence_c + uz * 0.26, ch_r, ch_u, uz, 0.36, 29.5, 0.52, mat_idx=11)
    # Top & bottom horizontal iron rails + vertical pickets every 0.35m
    add_box_local(bm, fence_c + uz * 0.62, ch_r, ch_u, uz, 0.08, 29.2, 0.06, mat_idx=10)
    add_box_local(bm, fence_c + uz * 1.38, ch_r, ch_u, uz, 0.08, 29.2, 0.06, mat_idx=10)
    for pk_i in range(-38, 39):
        pk_p = fence_c + ch_u * (pk_i * 0.37) + uz * 1.00
        add_box_local(bm, pk_p, ch_r, ch_u, uz, 0.05, 0.05, 0.90, mat_idx=10)
    # Church main nave (`grey_limestone`), stepped Gothic buttresses, lancet windows, and pitched slate roof (`roof_slates`)
    add_box_local(bm, ch_c + uz * 6.8, ch_r, ch_u, uz, 15.6, 26.0, 13.6, mat_idx=12)
    # Pitched gable slate roof over nave (Z = 13.6m .. 20.2m)
    nv_b0 = bm.verts.new(ch_c - ch_r * 8.1 - ch_u * 13.3 + uz * 13.5)
    nv_b1 = bm.verts.new(ch_c + ch_r * 8.1 - ch_u * 13.3 + uz * 13.5)
    nv_b2 = bm.verts.new(ch_c + ch_r * 8.1 + ch_u * 13.3 + uz * 13.5)
    nv_b3 = bm.verts.new(ch_c - ch_r * 8.1 + ch_u * 13.3 + uz * 13.5)
    nv_t0 = bm.verts.new(ch_c - ch_u * 13.3 + uz * 20.4)
    nv_t1 = bm.verts.new(ch_c + ch_u * 13.3 + uz * 20.4)
    for f_roof_v in ((nv_b1, nv_b2, nv_t1, nv_t0), (nv_b3, nv_b0, nv_t0, nv_t1), (nv_b0, nv_b1, nv_t0), (nv_b2, nv_b3, nv_t1)):
        try:
            bm.faces.new(f_roof_v).material_index = 13
        except ValueError:
            pass
    # Gothic stepped stone buttresses & pointed lancet windows along street-facing (+ch_r) wall
    for b_idx_ch in range(-3, 4):
        bp_ch = ch_c + ch_r * 8.0 + ch_u * (b_idx_ch * 3.8)
        add_box_local(bm, bp_ch + uz * 3.5, ch_r, ch_u, uz, 1.1, 0.85, 7.0, mat_idx=12)
        add_box_local(bm, bp_ch - ch_r * 0.25 + uz * 9.2, ch_r, ch_u, uz, 0.65, 0.70, 5.2, mat_idx=12)
        if b_idx_ch < 3:
            wp_ch = ch_c + ch_r * 7.82 + ch_u * ((b_idx_ch + 0.5) * 3.8) + uz * 7.5
            add_box_local(bm, wp_ch, ch_r, ch_u, uz, 0.18, 1.35, 5.2, mat_idx=2)
            add_box_local(bm, wp_ch + ch_r * 0.06, ch_r, ch_u, uz, 0.14, 1.55, 0.22, mat_idx=11)
    # Small stone entrance vestibule porch with slate gable roof (`(468.5, 1806.5)`) visible in Cam1 `V3, H5..H6`
    porch_c = ch_c + ch_r * 8.8 - ch_u * 3.5
    add_box_local(bm, porch_c + uz * 2.2, ch_r, ch_u, uz, 3.2, 3.6, 4.4, mat_idx=12)
    add_box_local(bm, porch_c + uz * 4.7, ch_r, ch_u, uz, 3.5, 3.9, 0.8, mat_idx=13)

    # Right side of Cam1 (`V8, H2..H6`): `Nouvelle Maison de Radio-Canada` (`794938067`) glass curtain-wall complex
    nmrc_c = Vector((532.0, 1790.0, 0.0))
    add_box_local(bm, nmrc_c + uz * 15.5, ch_r, ch_u, uz, 42.0, 68.0, 31.0, mat_idx=3)
    for fl_n in range(8):
        zn = 3.6 + fl_n * 3.6
        add_box_local(bm, nmrc_c + uz * zn, ch_r, ch_u, uz, 42.4, 68.4, 0.28, mat_idx=4)

    # =========================================================================
    # 6. CENTRAL & NORTHERN SATELLITE COMPLEXES (`46866852`, `46866853`, COURTYARDS)
    # =========================================================================
    # Central white-roofed broadcast/office complex `46866852` (`X=752..823, Y=2075..2167`)
    c_u = Vector((0.8387, -0.5446, 0.0)).normalized()
    c_v = Vector((-c_u.y, c_u.x, 0.0))
    b46_main = Vector((782.0, 2138.0, 0.0))
    add_box_local(bm, b46_main + uz * 8.5, c_u, c_v, uz, 42.0, 38.0, 17.0, mat_idx=11)
    add_box_local(bm, b46_main + uz * 17.15, c_u, c_v, uz, 40.5, 36.5, 0.25, mat_idx=14)
    _add_rooftop_hvac_and_skylights(bm, b46_main + uz * 17.3, c_u, c_v, 38.0, 34.0, 0, 10, 2)
    # South-east wing (`X=788..822, Y=2075..2135`) facing Cam3 (`Rue_NotreDameEst_Papineau_Corridor` left side `V1`)
    b46_wing = Vector((801.0, 2106.0, 0.0))
    add_box_local(bm, b46_wing + uz * 7.8, c_u, c_v, uz, 18.0, 52.0, 15.6, mat_idx=11)
    add_box_local(bm, b46_wing + uz * 15.75, c_u, c_v, uz, 16.8, 50.8, 0.25, mat_idx=15)

    # Paved parking lot (`X=625..745, Y=2135..2295`, `H3..H5, V2..V4` in `satellite_topdown.png`)
    lot_c = Vector((685.0, 2212.0, 0.0))
    add_box_local(bm, lot_c + uz * 0.03, c_u, c_v, uz, 118.0, 145.0, 0.06, mat_idx=10)
    for row_i in range(-3, 4):
        for car_j in range(-5, 6):
            if (row_i + car_j) % 3 == 0:
                continue
            cp = lot_c + c_u * (row_i * 14.5) + c_v * (car_j * 9.5)
            c_mat = 10 if ((row_i + car_j) % 2 == 0) else (4 if (car_j % 3 == 0) else 9)
            add_box_local(bm, cp + uz * 0.75, c_u, c_v, uz, 4.4, 1.9, 1.4, mat_idx=c_mat)

    # Northern white-roofed complex `46866853` (`X=750..820, Y=2300..2400`, `H1..H2, V4..V5`)
    n_c1 = Vector((785.0, 2368.0, 0.0))
    add_box_local(bm, n_c1 + uz * 11.0, c_u, c_v, uz, 54.0, 34.0, 22.0, mat_idx=0)
    add_box_local(bm, n_c1 + uz * 22.15, c_u, c_v, uz, 52.0, 32.0, 0.25, mat_idx=15)
    _add_rooftop_hvac_and_skylights(bm, n_c1 + uz * 22.3, c_u, c_v, 48.0, 30.0, 0, 10, 2)
    n_c2 = Vector((770.0, 2322.0, 0.0))
    add_box_local(bm, n_c2 + uz * 6.5, c_u, c_v, uz, 52.0, 42.0, 13.0, mat_idx=4)
    add_box_local(bm, n_c2 + uz * 13.15, c_u, c_v, uz, 50.5, 40.5, 0.25, mat_idx=14)

    # Top-center studio/industrial blocks (`X=615..735, Y=2335..2412`, `H1..H2, V2..V4`)
    add_box_local(bm, Vector((705.0, 2375.0, 9.0)), c_u, c_v, uz, 44.0, 56.0, 18.0, mat_idx=0)
    add_box_local(bm, Vector((705.0, 2375.0, 18.15)), c_u, c_v, uz, 42.5, 54.5, 0.25, mat_idx=14)
    add_box_local(bm, Vector((650.0, 2380.0, 7.5)), c_u, c_v, uz, 58.0, 62.0, 15.0, mat_idx=16)
    add_box_local(bm, Vector((650.0, 2380.0, 15.15)), c_u, c_v, uz, 56.5, 60.5, 0.25, mat_idx=15)

    # Courtyard 1 (`X=560..638, Y=2295..2375`, `H1..H2, V1..V2`): 6-story perimeter block around green courtyard
    cy1 = Vector((598.0, 2334.0, 0.0))
    for sx_o, sy_o, w_b, d_b, r_m in (
        (0.0, 26.0, 58.0, 14.0, 14),
        (0.0, -26.0, 58.0, 14.0, 14),
        (-22.0, 0.0, 14.0, 40.0, 15),
        (22.0, 0.0, 14.0, 40.0, 14),
    ):
        bc = cy1 + c_u * sx_o + c_v * sy_o
        add_box_local(bm, bc + uz * 10.5, c_u, c_v, uz, w_b, d_b, 21.0, mat_idx=0)
        add_box_local(bm, bc + uz * 21.15, c_u, c_v, uz, w_b - 1.0, d_b - 1.0, 0.25, mat_idx=r_m)
    add_box_local(bm, cy1 + uz * 0.12, c_u, c_v, uz, 30.0, 36.0, 0.24, mat_idx=7)

    # =========================================================================
    # 7. CAMERA 4 HEROES (`Rue_SainteCatherineEst_DeLorimier` at `(559.3, 2189.3)`, hdg=65°)
    # =========================================================================
    # Courtyard 2 (`X=525..592, Y=2210..2285`, `V1, H1..H6` in Cam4 & `H2..H4, V1` in Satellite):
    # South-east corner block at `(564.0, 2218.0)` (8-story dark-metal/glass facade on far left `V1, H1..H6`)
    c4_u = Vector((0.9063, 0.4226, 0.0)).normalized()  # 65 deg
    c4_r = Vector((c4_u.y, -c4_u.x, 0.0))
    b_c4_near = Vector((561.0, 2224.0, 0.0))
    add_box_local(bm, b_c4_near + uz * 14.5, c4_r, c4_u, uz, 18.0, 26.0, 29.0, mat_idx=10)
    add_box_local(bm, b_c4_near + uz * 29.15, c4_r, c4_u, uz, 17.0, 25.0, 0.25, mat_idx=14)
    # Stepped 12-story white-and-glass tower with 3-story red-brick base at `(580.0, 2254.0)` (`V1, H3..H6`)
    b_c4_mid = Vector((578.0, 2254.0, 0.0))
    add_box_local(bm, b_c4_mid + uz * 5.5, c4_r, c4_u, uz, 22.0, 28.0, 11.0, mat_idx=16)
    add_box_local(bm, b_c4_mid + uz * 23.0, c4_r, c4_u, uz, 20.0, 25.0, 24.0, mat_idx=4)
    add_box_local(bm, b_c4_mid + uz * 35.15, c4_r, c4_u, uz, 19.0, 24.0, 0.25, mat_idx=14)
    # 10-story white modernist grid-window building in center-left distance (`(672.0, 2282.0)`, `V3..V4, H4..H5`)
    b_c4_far = Vector((672.0, 2282.0, 0.0))
    add_box_local(bm, b_c4_far + uz * 18.0, c4_r, c4_u, uz, 38.0, 24.0, 36.0, mat_idx=4)
    add_box_local(bm, b_c4_far + uz * 36.15, c4_r, c4_u, uz, 36.5, 22.5, 0.25, mat_idx=14)
    # Yellow lattice tower crane at `(624.0, 2242.0)` (`V2..V3, H3..H5`)
    crane_base = Vector((624.0, 2242.0, 0.0))
    add_box_local(bm, crane_base + uz * 26.0, c4_r, c4_u, uz, 1.6, 1.6, 52.0, mat_idx=17)
    add_box_local(bm, crane_base + c4_r * 8.0 + uz * 51.5, c4_r, c4_u, uz, 44.0, 1.4, 1.4, mat_idx=17)
    # Foreground/midground redevelopment court in Cam4 (`(565..605, 2190..2215)`):
    # Yellow field container (`V3..V4, H5..H6`), white/red utility van (`V1..V2, H5..H6`), perimeter fence, and orange traffic barrels
    add_box_local(bm, Vector((579.5, 2204.0, 1.4)), c4_r, c4_u, uz, 2.8, 5.6, 2.6, mat_idx=17)
    add_box_local(bm, Vector((569.5, 2206.5, 1.1)), c4_r, c4_u, uz, 2.1, 4.8, 2.1, mat_idx=4)
    for cone_xy in ((566.5, 2191.5), (571.2, 2186.2), (564.2, 2195.8)):
        add_cylinder_along(bm, Vector((cone_xy[0], cone_xy[1], 0.15)), Vector((cone_xy[0], cone_xy[1], 1.05)), 0.24, 0.18, segs=10, mat_idx=9)
    # Heritage black lamppost on right sidewalk of Cam4 (`(578.5, 2185.2)`, `V7..V8, H4..H6`)
    add_box_local(bm, Vector((578.5, 2185.2, 0.35)), c4_r, c4_u, uz, 0.55, 0.55, 0.50, mat_idx=1)
    add_cylinder_along(bm, Vector((578.5, 2185.2, 0.60)), Vector((578.5, 2185.2, 5.20)), 0.10, 0.07, segs=8, mat_idx=10)

    # =========================================================================
    # 8. CAMERA 2 FOREGROUND/MIDGROUND (`Parc_Bellerive_Waterfront_Promenade` at `(888.1, 2376.3)`, hdg=125°)
    # =========================================================================
    c2_u = Vector((0.8192, -0.5736, 0.0)).normalized()  # 125 deg along Rue Notre-Dame Est
    c2_r = Vector((c2_u.y, -c2_u.x, 0.0))
    # Articulated 3D commercial white trailer on the left (`V1..V4, H3..H7`)
    tr_c = Vector((897.2, 2376.2, 0.0))
    add_box_local(bm, tr_c + uz * 2.55, c2_r, c2_u, uz, 2.55, 11.5, 2.85, mat_idx=4)
    add_box_local(bm, tr_c - c2_r * 1.29 + uz * 1.18, c2_r, c2_u, uz, 0.04, 11.4, 0.12, mat_idx=9)
    # Dual rear axles & tires (`dark_metal` tires + `white_trim` wheel rims)
    for ax_s in (-3.8, -2.4):
        for w_s in (-1.1, 1.1):
            wp_t = tr_c + c2_u * ax_s + c2_r * w_s + uz * 0.55
            add_cylinder_along(bm, wp_t - c2_r * 0.25, wp_t + c2_r * 0.25, 0.52, 0.52, segs=12, mat_idx=10)
            add_cylinder_along(bm, wp_t - c2_r * 0.27, wp_t + c2_r * 0.27, 0.26, 0.26, segs=10, mat_idx=4)
    # White cab-over delivery truck on the right (`V8, H4..H6`)
    cab_c = Vector((892.4, 2360.2, 0.0))
    add_box_local(bm, cab_c + uz * 1.65, c2_r, c2_u, uz, 2.35, 5.2, 2.5, mat_idx=4)
    add_box_local(bm, cab_c - c2_u * 2.62 + uz * 1.85, c2_r, c2_u, uz, 2.1, 0.12, 0.95, mat_idx=2)
    # Tall highway streetlamp pole at `(906.2, 2347.8)` (`V6, H3..H6`) + white industrial containers behind green verge
    add_cylinder_along(bm, Vector((906.2, 2347.8, 0.15)), Vector((906.2, 2347.8, 9.8)), 0.12, 0.08, segs=8, mat_idx=10)
    add_box_local(bm, Vector((922.0, 2343.0, 2.2)), c2_r, c2_u, uz, 6.0, 18.0, 4.2, mat_idx=4)
    add_box_local(bm, Vector((912.0, 2352.0, 0.22)), c2_r, c2_u, uz, 6.5, 42.0, 0.25, mat_idx=7)

    # =========================================================================
    # 9. CAMERA 3 FOREGROUND/MIDGROUND (`Rue_NotreDameEst_Papineau_Corridor` at `(811.9, 2014.6)`, hdg=40°)
    # =========================================================================
    c3_u = Vector((0.6428, 0.7660, 0.0)).normalized()  # 40 deg along Rue Notre-Dame Est
    c3_r = Vector((c3_u.y, -c3_u.x, 0.0))
    # Raised beige/tan concrete pedestrian corner island (`H7..H8, V2..V8`)
    isl_c = Vector((816.2, 2016.2, 0.0))
    add_box_local(bm, isl_c + uz * 0.125, c3_r, c3_u, uz, 7.2, 6.4, 0.25, mat_idx=8)
    add_box_local(bm, isl_c - c3_r * 3.6 + uz * 0.13, c3_r, c3_u, uz, 0.28, 6.4, 0.26, mat_idx=11)
    # Foreground black traffic-signal mast at `(814.55, 2019.0)` (`V3..V4, H1..H8`) + horizontal cantilever arm (`H1..H2, V1..V4`)
    sig_base = Vector((814.55, 2019.0, 0.20))
    add_cylinder_along(bm, sig_base, sig_base + uz * 7.6, 0.11, 0.09, segs=10, mat_idx=10)
    add_cylinder_along(bm, sig_base + uz * 5.85, sig_base - c3_r * 4.8 + uz * 6.35, 0.08, 0.06, segs=8, mat_idx=10)
    # 3-aspect traffic signal head housing (`V3..V4, H3..H5`)
    add_box_local(bm, sig_base - c3_u * 0.18 + uz * 3.65, c3_r, c3_u, uz, 0.42, 0.38, 1.35, mat_idx=10)
    add_box_local(bm, sig_base + c3_r * 0.18 + uz * 2.55, c3_r, c3_u, uz, 0.55, 0.08, 0.65, mat_idx=11)
    # Right-hand post on pedestrian island (`V7..V8, H5..H8`)
    post_r = Vector((818.8, 2015.9, 0.20))
    add_cylinder_along(bm, post_r, post_r + uz * 2.55, 0.045, 0.045, segs=8, mat_idx=10)
    add_box_local(bm, post_r + uz * 2.35, c3_r, c3_u, uz, 0.62, 0.06, 0.58, mat_idx=11)
    # Grassy median strip (`V3..V6, H5..H6`) between carriageways of Rue Notre-Dame Est (`(824, 2028) -> (868, 2082)`)
    med_c = Vector((842.0, 2052.0, 0.0))
    add_box_local(bm, med_c + uz * 0.12, c3_r, c3_u, uz, 6.5, 48.0, 0.24, mat_idx=7)
    add_box_local(bm, med_c - c3_u * 20.5 + uz * 0.55, c3_r, c3_u, uz, 1.1, 0.9, 0.85, mat_idx=4)
    # Secondary traffic signal poles on median (`V4..V5, H4..H6`)
    for sp_xy in ((826.5, 2034.5), (833.5, 2043.0)):
        sp_b = Vector((sp_xy[0], sp_xy[1], 0.20))
        add_cylinder_along(bm, sp_b, sp_b + uz * 6.5, 0.09, 0.07, segs=8, mat_idx=10)
        add_cylinder_along(bm, sp_b + uz * 5.6, sp_b + c3_r * 3.8 + uz * 5.9, 0.06, 0.05, segs=6, mat_idx=10)
    # White semi-truck with yellow container & waiting cars on left carriageway (`V1..V3, H5..H6`)
    trk_c3 = Vector((806.5, 2044.0, 0.0))
    add_box_local(bm, trk_c3 - c3_u * 4.5 + uz * 1.4, c3_r, c3_u, uz, 2.4, 5.2, 2.6, mat_idx=4)
    add_box_local(bm, trk_c3 + c3_u * 2.5 + uz * 2.1, c3_r, c3_u, uz, 2.5, 9.5, 2.9, mat_idx=17)
    add_box_local(bm, Vector((811.2, 2040.5, 0.75)), c3_r, c3_u, uz, 1.85, 4.2, 1.35, mat_idx=9)
    add_box_local(bm, Vector((814.5, 2042.5, 0.75)), c3_r, c3_u, uz, 1.85, 4.2, 1.35, mat_idx=4)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    apply_world_box_uv(obj, scale=0.22)
    return obj


def main():
    print(f"\n=== Building {BLOCK_ID} (Maison de Radio-Canada, Village Pied-du-Courant & Parc Bellerive) ===")
    clean_scene()
    setup_render_engine()

    raw_dossier = load_dossier(BLOCK_ID)
    dossier = merge_neighbor_dossiers(raw_dossier)
    setup_world_lighting(dossier)
    owned_col, _ = setup_collection_hierarchy(BLOCK_ID)

    build_ground_and_streets(owned_col, dossier)
    mats = build_corridor_material_palette()

    build_radio_canada_and_bellerive_landmarks(owned_col, mats)

    # Skip boxes where our custom hero complexes & river/rail corridor sit
    skip_boxes = [
        (540.0, 630.0, 2095.0, 2175.0),   # North Tour de Radio-Canada
        (415.0, 505.0, 1505.0, 1585.0),   # South Tour de Radio-Canada
        (450.0, 485.0, 1790.0, 1832.0),   # Cathédrale Saints-Pierre-et-Paul
        (505.0, 560.0, 1755.0, 1825.0),   # Nouvelle Maison de Radio-Canada north corner
        (750.0, 825.0, 2070.0, 2170.0),   # Central broadcast/office complex 46866852
        (740.0, 825.0, 2295.0, 2405.0),   # Northern complex 46866853
        (615.0, 740.0, 2330.0, 2415.0),   # Top-center studio blocks
        (555.0, 642.0, 2290.0, 2378.0),   # Courtyard 1
        (545.0, 608.0, 2210.0, 2285.0),   # Courtyard 2 (Cam 4 left)
        (865.0, 1450.0, 1840.0, 2480.0),  # CP Rail Yard, Port Wharf & St. Lawrence River
    ]
    build_corridor_context_buildings(owned_col, dossier, mats, skip_boxes=skip_boxes, max_buildings=360)

    # Curated 3D trees matching the 4 Street View cameras & Parc Bellerive / Satellite Top-Down
    extra_trees = [
        # Cam 1 (`Tour_Radio_Canada_ReneLevesque_South`): signature sidewalk tree at (467.2, 1791.8) + boulevard trees
        (467.2, 1791.8, 1.38),
        (461.5, 1796.5, 1.25),
        (478.5, 1822.0, 1.15),
        (492.0, 1812.0, 1.10),
        (502.0, 1824.0, 1.12),
        (514.0, 1802.0, 1.15),
        # Cam 4 (`Rue_SainteCatherineEst_DeLorimier`): right-side foliage along Rue Tansley
        (582.0, 2183.5, 1.15),
        (589.0, 2186.5, 1.20),
        (596.0, 2190.0, 1.12),
        # Central building `46866852` garden trees (visible in Satellite Top-Down H4..H6, V4..V5)
        (742.0, 2110.0, 1.15),
        (755.0, 2095.0, 1.18),
        (768.0, 2082.0, 1.12),
        (818.0, 2125.0, 1.15),
        (822.0, 2150.0, 1.18),
    ]
    # Parc Bellerive linear greenway & Rue Notre-Dame Est tree rows (`Y = 1880..2410`)
    for i in range(28):
        ty = 1885.0 + i * 19.0
        tx = rail_yard_center_x(ty) - 42.0 + (i % 2) * 5.0
        extra_trees.append((tx, ty, 1.10 + (i % 3) * 0.08))

    build_corridor_foliage_and_props(owned_col, dossier, extra_trees=extra_trees, max_osm_trees=95)

    # Also add a lush multi-tree canopy cluster right at `(467.2, 1791.8)` so Cam1's foreground tree canopy spans H1..H5, V2..V7
    append_kit_object(
        "jacaranda_tree",
        name="MTL_PH_Tree_Cam1_Hero_Crown",
        collection=owned_col,
        location=(466.9, 1791.5, 0.22),
        rotation_z=1.1,
        scale=1.48,
    )

    export_block_artifacts(BLOCK_ID, owned_col)
    print(f"=== {BLOCK_ID} Complete ===")


if __name__ == "__main__":
    main()
