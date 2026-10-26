"""
Subagent 8: Water Basins, Rivers, Locks, Canals, Seawalls & Satellite Context Terrain Overhaul
==============================================================================================
Self-contained Blender 5.2 Python module for `output/montreal_master.blend` providing:
  - `rebuild_water_and_satellite_terrain(osm_data=None)`
  - `OSMWaterfrontClassifier` (`is_land(x, y)` / `is_water(x, y)`)

Key Capabilities:
1. Exact OpenStreetMap Shoreline, Harbor Basins, Lachine Canal & Seawalls:
   - Parses `data/open_data/old_montreal_osm.json` (or passed `osm_data`):
     * `Way 83255355` (Vieux-Port 237-point coastline & Quai de l'Horloge arm)
     * `Way 243058802` (Quai King-Edward 24-point pier)
     * `Way 243058804` (Grand Quai / Quai Alexandra 16-point pier)
     * `Way 677248943` / `Way 69948943` (Quai Jacques-Cartier 12-point pier)
     * `Way 677248942` (Quai des Convoyeurs 9-point pier)
     * `Way 1180387334` (Parc du Bassin-Bonsecours / Île Bonsecours 25-point island)
     * `Way 1272856121` (Pointe-du-Moulin 96-point quay)
     * `Way 115577288` (Parc de Dieppe 60-point peninsula & Cité du Havre shoreline)
     * Lachine Canal, Écluse No. 1, West Spillway Basin & Bassin Peel ways.
   - Builds a precise 2D land-vs-water classifier (`is_land(x, y)` and `is_water(x, y)`)
     distinguishing Mainland Old Montreal/Downtown, all 7 piers/islands/peninsulas, and
     all 9 harbor basins, locks, canals, lagoons, and the St. Lawrence River channel.

2. High-Resolution Smooth-Boundary `Water_District_StLawrence_And_Canals` (`Z = -2.20m`)
   & Continuous 3D Stepped Granite Seawall (`Quays_And_Canal_Retaining_Walls`, `Z = -2.50m .. +0.18m`):
   - Sub-cell Marching-Squares boundary-snapped water mesh at `Z = -2.20m` with
     `Mat_MTL_StLawrence_Water_PBR` (`water_river_diffuse_2k.jpg`, `water_river_rough_2k.jpg`,
     `water_river_nor_gl_2k.jpg` at `15m` metric UV tiling).
   - Shoreline foam trim ribbon (`Mat_MTL_Water_Foam_Edge`, `water_foam_edge_2k.jpg`) at `Z = -2.18m`
     along all quay, pier, island, and canal walls.
   - Continuous 3D stepped granite seawall (`Mat_MTL_Quay_Granite`, `Z = -2.50m` to `+0.18m`)
     with `0.45m`-wide granite coping stones and 3D cast-iron mooring bollards (`Mat_MTL_CastIron_Black`)
     every `18m` along the exact `is_land` / `is_water` boundary.

3. `Ground_District_Solid_Collider` with 4K Metric-Aligned Google Maps Satellite Texture:
   - Solid drivable land collider (`Z = -0.05m` top face, `Z = -2.50m` bottom face across all
     `is_land(x, y)` regions; dropping cleanly to `Z = -2.50m` top / `Z = -2.80m` bottom under
     all `is_water(x, y)` regions so water basins are never covered by ground).
   - Assigned PBR material `Mat_MTL_Satellite_Ground_4K` wired directly to
     `assets/polyhaven/montreal_satellite_ortho_4k.jpg` (fallback `output/renders/google_maps_aerial_full_36blocks.png`)
     with exact metric UV projection:
       `u = (x - (40.0 - 975.0)) / 1950.0`
       `v = (y - (-60.0 - 975.0)) / 1950.0`
"""

from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

try:
    import bmesh
    import bpy
    from mathutils import Matrix, Vector
    from mathutils.geometry import tessellate_polygon
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
DEFAULT_OSM_PATH = PROJECT_ROOT / "data" / "open_data" / "old_montreal_osm.json"

# Master World Origin (Place d'Armes Center - Maisonneuve Monument)
MASTER_ORIGIN_LAT = 45.50472
MASTER_ORIGIN_LON = -73.55661
EARTH_RADIUS_M = 6378137.0

# 4K Metric-Aligned Google Maps Satellite Orthophoto Projection Constants
SAT_CENTER_X = 40.0
SAT_CENTER_Y = -60.0
SAT_SCALE_M = 1950.0
SAT_HALF_M = SAT_SCALE_M / 2.0  # 975.0m -> X in [-935.0, +1015.0], Y in [-1035.0, +915.0]


def log(msg: str) -> None:
    print(f"[WATER-TERRAIN-OVERHAUL] {msg}", flush=True)


def latlon_to_xy(
    lat: float,
    lon: float,
    origin_lat: float = MASTER_ORIGIN_LAT,
    origin_lon: float = MASTER_ORIGIN_LON,
) -> Tuple[float, float]:
    """Converts WGS84 (lat, lon) into Master World metric coordinates (x, y) in meters."""
    mean_lat = math.radians(origin_lat)
    x = math.radians(lon - origin_lon) * EARTH_RADIUS_M * math.cos(mean_lat)
    y = math.radians(lat - origin_lat) * EARTH_RADIUS_M
    return float(x), float(y)


def satellite_uv_from_xy(x: float, y: float) -> Tuple[float, float]:
    """
    Computes exact metric-aligned Google Maps Satellite UV coordinates (u, v)
    for any world position (x, y) in meters:
      u = (x - (40.0 - 975.0)) / 1950.0
      v = (y - (-60.0 - 975.0)) / 1950.0
    """
    u = (x - (SAT_CENTER_X - SAT_HALF_M)) / SAT_SCALE_M
    v = (y - (SAT_CENTER_Y - SAT_HALF_M)) / SAT_SCALE_M
    return float(u), float(v)


def point_in_polygon_2d(x: float, y: float, poly: Sequence[Tuple[float, float]]) -> bool:
    """Exact 2D ray-casting point-in-polygon test."""
    n = len(poly)
    if n < 3:
        return False
    inside = False
    px1, py1 = poly[0]
    for i in range(1, n + 1):
        px2, py2 = poly[i % n]
        if (py1 > y) != (py2 > y):
            x_int = (px2 - px1) * (y - py1) / (py2 - py1 + 1e-15) + px1
            if x < x_int:
                inside = not inside
        px1, py1 = px2, py2
    return inside


def points_in_polygon_vectorized(
    xs: np.ndarray,
    ys: np.ndarray,
    poly: Sequence[Tuple[float, float]],
) -> np.ndarray:
    """Vectorized 2D ray-casting point-in-polygon evaluation over numpy arrays xs, ys."""
    mask = np.zeros(xs.shape, dtype=bool)
    n = len(poly)
    if n < 3:
        return mask

    pts = np.asarray(poly, dtype=np.float64)
    min_x, max_x = float(pts[:, 0].min()), float(pts[:, 0].max())
    min_y, max_y = float(pts[:, 1].min()), float(pts[:, 1].max())

    in_bbox = (xs >= min_x) & (xs <= max_x) & (ys >= min_y) & (ys <= max_y)
    if not np.any(in_bbox):
        return mask

    bx = xs[in_bbox]
    by = ys[in_bbox]
    inside = np.zeros(bx.shape, dtype=bool)

    px1, py1 = pts[0, 0], pts[0, 1]
    for i in range(1, n + 1):
        px2, py2 = pts[i % n, 0], pts[i % n, 1]
        cond_y = (py1 > by) != (py2 > by)
        if np.any(cond_y):
            x_int = (px2 - px1) * (by - py1) / (py2 - py1 + 1e-15) + px1
            inside ^= cond_y & (bx < x_int)
        px1, py1 = px2, py2

    mask[in_bbox] = inside
    return mask


# =============================================================================
# SECTION 1: EXACT OPENSTREETMAP WATERFRONT POLYGON EXTRACTOR & 2D CLASSIFIER
# =============================================================================

# Fallback exact OSM coordinates (in case an incomplete osm_data dict is passed)
FALLBACK_QUAI_ALEXANDRA = [
    (299.0, -306.2), (596.0, -274.2), (657.5, -267.6), (658.1, -267.0),
    (678.4, -167.4), (674.0, -160.6), (588.5, -170.1), (297.8, -202.5),
    (298.8, -241.8), (298.9, -244.3), (298.9, -252.6), (298.9, -260.6),
    (296.0, -263.0), (296.1, -271.7), (298.0, -297.6), (299.0, -306.2),
]

FALLBACK_QUAI_CONVOYEURS = [
    (313.3, -123.3), (310.3, -136.4), (321.5, -138.5), (321.5, -139.3),
    (524.1, -118.6), (522.5, -104.0), (320.3, -124.3), (320.3, -124.7),
    (313.3, -123.3),
]

FALLBACK_QUAI_KING_EDWARD = [
    (348.6, 63.8), (345.7, 58.3), (340.8, 38.5), (338.5, 26.2),
    (339.4, 18.9), (332.8, 4.3), (332.8, -2.5), (326.7, -31.0),
    (326.5, -40.1), (709.7, -4.6), (711.0, -3.5), (736.0, 89.2),
    (736.3, 92.0), (735.6, 95.4), (734.2, 97.5), (731.7, 99.5),
    (727.8, 100.5), (639.8, 91.9), (630.1, 91.0), (618.0, 89.8),
    (609.3, 89.0), (600.3, 88.1), (594.1, 87.5), (348.6, 63.8),
]

FALLBACK_QUAI_JACQUES_CARTIER = [
    (471.3, 328.5), (420.2, 227.9), (428.2, 228.2), (527.4, 233.9),
    (764.1, 248.2), (780.4, 331.2), (777.9, 335.3), (773.8, 339.6),
    (691.9, 336.4), (688.3, 336.4), (472.7, 328.3), (471.3, 328.5),
]

FALLBACK_ILE_BONSECOURS = [
    (789.5, 507.8), (784.7, 507.6), (732.5, 505.7), (724.4, 505.4),
    (536.8, 498.7), (534.8, 498.3), (533.7, 497.1), (502.0, 415.6),
    (500.4, 411.8), (471.6, 338.7), (469.7, 333.3), (469.5, 331.2),
    (470.1, 329.5), (471.3, 328.5), (472.7, 328.3), (688.3, 336.4),
    (691.9, 336.4), (773.8, 339.6), (777.9, 335.3), (780.4, 331.2),
    (803.2, 434.2), (780.1, 438.7), (776.0, 439.5), (788.6, 503.3),
    (789.5, 507.8),
]

# Full Quai de l'Horloge Pier Polygon (east arm of Way 83255355 up to Tour de l'Horloge (842.9, 838.4),
# bridging the central road/parking apron cutout pt[161..176] so the entire pier deck is solid land)
QUAI_DE_L_HORLOGE_POLY = [
    (675.7, 552.1),
    (681.3, 604.6),
    (687.4, 620.8),
    (784.9, 854.5),
    (790.2, 856.4),
    (796.0, 858.5),
    (806.7, 904.7),
    (807.6, 906.3),
    (808.9, 907.0),
    (810.6, 906.8),
    (812.0, 905.7),
    (859.2, 854.9),
    (860.7, 855.5),
    (861.6, 850.4),
    (860.3, 841.8),
    (858.8, 830.7),
    (855.8, 815.7),
    (852.7, 816.2),
    (800.6, 561.7),
    (768.9, 560.2),
]

# Cité du Havre southern peninsula polygon (Avenue Pierre-Dupuy Way 1270689191 / Cycleway Way 24007286 /
# Habitat 67 Way 440195613 / Tropiques Nord Way 47175247) connecting seamlessly into Parc de Dieppe Way 115577288
CITE_DU_HAVRE_SOUTH_POLY = [
    (865.0, -1650.0),
    (888.0, -1180.9),
    (903.0, -900.0),
    (917.8, -737.0),
    (930.0, -545.0),
    (945.0, -345.0),
    (955.0, -224.0),
    (967.2, -127.5),
    (975.5, -73.9),
    (994.1, -38.3),
    (1019.8, -13.4),
    (1077.6, 18.7),
    (1220.0, 18.7),
    (1220.0, -1650.0),
]

# Pont de la Concorde causeway/bridge deck corridor (Way 23027211)
PONT_DE_LA_CONCORDE_POLY = [
    (955.0, -230.0),
    (1880.0, 380.0),
    (1880.0, 425.0),
    (955.0, -175.0),
]

# Lachine Canal & Écluse No. 1 Main Water Channel (carving through Vieux-Port neck from Bassin Peel to Old Port)
# East bank follows exact Way 1272856121 (Pointe-du-Moulin) pts[13..55]
LACHINE_MAIN_CHANNEL_WATER_POLY = [
    (352.0, -1035.0),
    (362.0, -960.0),
    (367.0, -895.0),
    (363.4, -719.7),
    (366.0, -705.8),
    (369.4, -659.8),
    (368.9, -632.0),
    (367.0, -598.0),
    (392.0, -598.0),
    (403.3, -547.7),
    (455.2, -557.9),
    (451.2, -615.2),
    (447.5, -640.7),
    (440.7, -681.7),
    (435.1, -716.0),
    (439.1, -720.1),
    (461.9, -723.8),
    (457.2, -764.2),
    (455.2, -781.8),
    (444.2, -888.3),
    (417.8, -884.3),
    (408.7, -886.7),
    (405.6, -902.1),
    (395.7, -969.4),
    (388.5, -1035.0),
]

# Place des Écluses / Bota Bota North Peninsula between Lock No. 1 exit and East Spillway (dry land)
LACHINE_NORTH_PENINSULA_LAND_POLY = [
    (392.0, -632.0),
    (435.0, -622.0),
    (445.0, -552.4),
    (403.3, -547.7),
]

# Lachine Canal West Spillway & Tugboat Basin (Way 1391578741 & Way 1163916100)
LACHINE_WEST_SPILLWAY_WATER_POLY = [
    (320.0, -1025.0),
    (326.0, -960.0),
    (332.0, -902.0),
    (325.3, -884.0),
    (332.7, -787.6),
    (336.4, -737.1),
    (338.5, -711.4),
    (358.5, -712.9),
    (358.0, -728.5),
    (352.0, -888.0),
    (351.4, -902.0),
    (338.0, -1025.0),
]

# Bassin Bonsecours Lagoon (inner water lagoon inside Way 1180387334 between Marché Bonsecours promenade & Île Bonsecours)
BASSIN_BONSECOURS_LAGOON_WATER_POLY = [
    (473.0, 334.0),
    (685.0, 341.0),
    (689.0, 383.0),
    (676.0, 412.0),
    (687.5, 447.4),
    (725.9, 499.6),
    (653.8, 503.0),
    (535.0, 496.0),
    (503.0, 415.0),
]

# East Inlet of Bassin Bonsecours (under eastern wooden boardwalk bridge Way 105231249)
BASSIN_BONSECOURS_EAST_INLET_WATER_POLY = [
    (690.0, 339.6),
    (773.8, 339.6),
    (795.0, 434.0),
    (772.0, 436.0),
    (752.0, 360.0),
    (690.0, 355.0),
]

# Central Pavilion Island inside Bassin Bonsecours Lagoon (dry land holding pavilions 1097403706, 1097403709, 1180387344)
BONSECOURS_CENTRAL_ISLAND_LAND_POLY = [
    (538.0, 362.0),
    (626.0, 366.0),
    (626.0, 406.0),
    (618.0, 415.0),
    (622.0, 465.0),
    (548.0, 462.0),
    (548.0, 425.0),
    (538.0, 412.0),
]

# Mainland Old Montreal / Downtown / Bassin Peel West Quay / Bassin de l'Horloge West Quay Seawall Curve
# Pairs of (y_meters, x_seawall_meters) sorted by y_meters ascending
MAINLAND_WEST_SEAWALL_PROFILE = [
    (-1650.0, 235.0),
    (-1350.0, 250.0),
    (-1100.0, 268.0),
    (-990.0, 282.0),
    (-965.0, 315.0),
    (-954.4, 331.2),
    (-906.5, 294.0),
    (-730.5, 302.7),
    (-577.1, 293.6),
    (-534.1, 282.9),
    (-486.4, 256.0),
    (-353.8, 229.2),
    (-186.9, 219.6),
    (-105.4, 227.6),
    (53.1, 269.6),
    (137.3, 293.8),
    (230.3, 340.5),
    (397.5, 404.9),
    (544.3, 463.0),
    (552.1, 538.0),
    (591.0, 562.0),
    (650.0, 588.0),
    (707.1, 614.0),
    (758.4, 636.0),
    (800.0, 654.0),
    (850.0, 675.0),
    (900.0, 695.0),
    (951.6, 718.0),
    (986.8, 745.0),
    (1130.0, 748.0),
    (1250.0, 760.0),
]


def eval_mainland_west_seawall_x(y: float) -> float:
    """Evaluates the mainland west seawall X coordinate at a given Y coordinate."""
    pts = MAINLAND_WEST_SEAWALL_PROFILE
    if y <= pts[0][0]:
        return pts[0][1]
    if y >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        y0, x0 = pts[i]
        y1, x1 = pts[i + 1]
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return x0 + t * (x1 - x0)
    return 300.0


def eval_mainland_west_seawall_x_vec(ys: np.ndarray) -> np.ndarray:
    """Vectorized evaluation of the mainland west seawall X coordinate over numpy array ys."""
    pts_y = np.array([p[0] for p in MAINLAND_WEST_SEAWALL_PROFILE], dtype=np.float64)
    pts_x = np.array([p[1] for p in MAINLAND_WEST_SEAWALL_PROFILE], dtype=np.float64)
    return np.interp(ys, pts_y, pts_x)


def load_osm_ways_xy(osm_data: Optional[Union[dict, str, Path]] = None) -> Dict[int, List[Tuple[float, float]]]:
    """
    Loads OSM ways in Master World metric coordinates (x, y) from `osm_data`
    (or from `data/open_data/old_montreal_osm.json` if `osm_data` is None or a path).
    """
    raw = None
    if isinstance(osm_data, dict) and "elements" in osm_data:
        raw = osm_data
    elif isinstance(osm_data, (str, Path)) and os.path.exists(str(osm_data)):
        with open(str(osm_data), "r", encoding="utf-8") as f:
            raw = json.load(f)
    elif DEFAULT_OSM_PATH.exists():
        with open(str(DEFAULT_OSM_PATH), "r", encoding="utf-8") as f:
            raw = json.load(f)

    ways_xy: Dict[int, List[Tuple[float, float]]] = {}
    if not raw or "elements" not in raw:
        return ways_xy

    nodes_ll: Dict[int, Tuple[float, float]] = {}
    for el in raw["elements"]:
        if el.get("type") == "node" and "lat" in el and "lon" in el:
            nodes_ll[int(el["id"])] = (float(el["lat"]), float(el["lon"]))

    for el in raw["elements"]:
        if el.get("type") == "way":
            wid = int(el["id"])
            pts: List[Tuple[float, float]] = []
            if "geometry" in el and el["geometry"]:
                for pt in el["geometry"]:
                    pts.append(latlon_to_xy(float(pt["lat"]), float(pt["lon"])))
            else:
                for nid in el.get("nodes", []):
                    if int(nid) in nodes_ll:
                        lat, lon = nodes_ll[int(nid)]
                        pts.append(latlon_to_xy(lat, lon))
            if len(pts) >= 2:
                ways_xy[wid] = pts

    # Alias Way 69948943 -> Way 677248943 (Quai Jacques-Cartier) so both IDs resolve identically
    if 677248943 in ways_xy and 69948943 not in ways_xy:
        ways_xy[69948943] = ways_xy[677248943]

    return ways_xy


class OSMWaterfrontClassifier:
    """
    Exact 2D OpenStreetMap Land-vs-Water Classifier for Montreal's Old Port,
    Lachine Canal, Bassin Peel, Île Bonsecours, Quai de l'Horloge, Cité du Havre,
    and the St. Lawrence River / Le Courant Sainte-Marie.
    """

    def __init__(self, osm_data: Optional[Union[dict, str, Path]] = None):
        self.ways_xy = load_osm_ways_xy(osm_data)

        # Extract exact OSM polygons (with high-precision fallbacks if any way is missing)
        self.vieux_port_poly = self.ways_xy.get(83255355, [])
        self.pointe_du_moulin_poly = self.ways_xy.get(1272856121, [])
        self.quai_alexandra_poly = self.ways_xy.get(243058804, FALLBACK_QUAI_ALEXANDRA)
        self.quai_convoyeurs_poly = self.ways_xy.get(677248942, FALLBACK_QUAI_CONVOYEURS)
        self.quai_king_edward_poly = self.ways_xy.get(243058802, FALLBACK_QUAI_KING_EDWARD)
        self.quai_jacques_cartier_poly = (
            self.ways_xy.get(677248943)
            or self.ways_xy.get(69948943)
            or FALLBACK_QUAI_JACQUES_CARTIER
        )
        self.ile_bonsecours_poly = self.ways_xy.get(1180387334, FALLBACK_ILE_BONSECOURS)
        self.parc_de_dieppe_poly = self.ways_xy.get(115577288, [])
        self.quai_horloge_poly = list(QUAI_DE_L_HORLOGE_POLY)
        self.cite_du_havre_south_poly = list(CITE_DU_HAVRE_SOUTH_POLY)
        self.pont_concorde_poly = list(PONT_DE_LA_CONCORDE_POLY)

        # Internal water carve-out polygons (Lachine Canal / Écluse No. 1 & Bassin Bonsecours Lagoon)
        self.lachine_main_channel_poly = list(LACHINE_MAIN_CHANNEL_WATER_POLY)
        self.lachine_west_spillway_poly = list(LACHINE_WEST_SPILLWAY_WATER_POLY)
        self.bassin_bonsecours_lagoon_poly = list(BASSIN_BONSECOURS_LAGOON_WATER_POLY)
        self.bassin_bonsecours_east_inlet_poly = list(BASSIN_BONSECOURS_EAST_INLET_WATER_POLY)

        # Internal islands inside the carved water basins
        self.bonsecours_central_island_poly = list(BONSECOURS_CENTRAL_ISLAND_LAND_POLY)
        self.lachine_north_peninsula_poly = list(LACHINE_NORTH_PENINSULA_LAND_POLY)

        # Precompute bounding boxes for fast scalar queries
        self._land_polys_bbox = []
        for name, poly in [
            ("Vieux-Port (Way 83255355)", self.vieux_port_poly),
            ("Pointe-du-Moulin (Way 1272856121)", self.pointe_du_moulin_poly),
            ("Grand Quai / Quai Alexandra (Way 243058804)", self.quai_alexandra_poly),
            ("Quai des Convoyeurs (Way 677248942)", self.quai_convoyeurs_poly),
            ("Quai King-Edward (Way 243058802)", self.quai_king_edward_poly),
            ("Quai Jacques-Cartier (Way 677248943)", self.quai_jacques_cartier_poly),
            ("Île Bonsecours (Way 1180387334)", self.ile_bonsecours_poly),
            ("Quai de l'Horloge (Way 83255355 East Arm)", self.quai_horloge_poly),
            ("Parc de Dieppe (Way 115577288)", self.parc_de_dieppe_poly),
            ("Cité du Havre Peninsula", self.cite_du_havre_south_poly),
            ("Pont de la Concorde Causeway", self.pont_concorde_poly),
        ]:
            if poly and len(poly) >= 3:
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                self._land_polys_bbox.append((name, poly, min(xs), max(xs), min(ys), max(ys)))

        self._water_carve_bbox = []
        for name, poly in [
            ("Lachine Canal & Écluse No. 1", self.lachine_main_channel_poly),
            ("Lachine Canal West Spillway Basin", self.lachine_west_spillway_poly),
            ("Bassin Bonsecours Lagoon", self.bassin_bonsecours_lagoon_poly),
            ("Bassin Bonsecours East Inlet", self.bassin_bonsecours_east_inlet_poly),
        ]:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            self._water_carve_bbox.append((name, poly, min(xs), max(xs), min(ys), max(ys)))

    def is_land(self, x: float, y: float) -> bool:
        """
        Returns True if (x, y) in Master World meters is on dry land:
          - Mainland Old Montreal/Downtown north-west of the Rue de la Commune / Rue Mill seawall, OR
          - Exact interior of Pointe-du-Moulin (`Way 1272856121`), Grand Quai / Quai Alexandra (`Way 243058804`),
            Quai des Convoyeurs (`Way 677248942`), Quai King-Edward (`Way 243058802`),
            Quai Jacques-Cartier (`Way 677248943` / `Way 69948943`), Île Bonsecours (`Way 1180387334`),
            Quai de l'Horloge (east arm of `Way 83255355` up to Tour de l'Horloge `(842.9, 838.4)`),
            or Cité du Havre / Parc de Dieppe (`Way 115577288`),
          - MINUS the internal water channels of the Lachine Canal & Écluse No. 1 and Bassin Bonsecours Lagoon.
        """
        # Fast path for inland Downtown / Old Montreal West of X = 215m
        if x <= 215.0:
            return True

        # 1. Check explicit internal water carve-outs first (Lachine Canal & Bassin Bonsecours Lagoon)
        for _, poly, x0, x1, y0, y1 in self._water_carve_bbox:
            if x0 <= x <= x1 and y0 <= y <= y1:
                if point_in_polygon_2d(x, y, poly):
                    # Check internal dry islands inside carved lagoons/canals
                    if 538.0 <= x <= 626.0 and 362.0 <= y <= 465.0:
                        if point_in_polygon_2d(x, y, self.bonsecours_central_island_poly):
                            return True
                    if 392.0 <= x <= 445.0 and -632.0 <= y <= -547.7:
                        if point_in_polygon_2d(x, y, self.lachine_north_peninsula_poly):
                            return True
                    return False

        # 2. Check Mainland West of the Rue de la Commune / Rue Mill / Bassin Peel / Yacht Club seawall
        if x <= eval_mainland_west_seawall_x(y):
            return True

        # 3. Check exact OSM pier, quay, island, and peninsula polygons
        for _, poly, x0, x1, y0, y1 in self._land_polys_bbox:
            if x0 <= x <= x1 and y0 <= y <= y1:
                if point_in_polygon_2d(x, y, poly):
                    return True

        return False

    def is_water(self, x: float, y: float) -> bool:
        """
        Returns True if (x, y) in Master World meters is inside any water basin or river channel:
          - Bassin Peel
          - Lachine Canal & Écluse No. 1 channel (plus West Spillway basin)
          - Pointe-du-Moulin Basin
          - Bassin Alexandra
          - Bassin King-Edward
          - Bassin Jacques-Cartier
          - Bassin Bonsecours Lagoon (between Marché Bonsecours and Île Bonsecours)
          - Bassin de l'Horloge / Yacht Club Basin (west of Quai de l'Horloge)
          - St. Lawrence River / Le Courant Sainte-Marie channel (between the piers and Cité du Havre)
        """
        return not self.is_land(x, y)

    def evaluate_land_grid(self, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        """Vectorized evaluation of `is_land(xs, ys)` over 2D numpy coordinate arrays."""
        land_mask = xs <= eval_mainland_west_seawall_x_vec(ys)

        for _, poly, _, _, _, _ in self._land_polys_bbox:
            land_mask |= points_in_polygon_vectorized(xs, ys, poly)

        carve_mask = np.zeros(xs.shape, dtype=bool)
        for _, poly, _, _, _, _ in self._water_carve_bbox:
            carve_mask |= points_in_polygon_vectorized(xs, ys, poly)

        # Restore internal islands inside carved water basins
        island_mask = (
            points_in_polygon_vectorized(xs, ys, self.bonsecours_central_island_poly)
            | points_in_polygon_vectorized(xs, ys, self.lachine_north_peninsula_poly)
        )
        carve_mask &= ~island_mask

        return land_mask & ~carve_mask

    def get_shoreline_polylines(self) -> List[Tuple[str, List[Tuple[float, float]], bool]]:
        """
        Returns the ordered list of `(name, points_xy, is_closed)` polylines along the
        exact boundary between `is_land` and `is_water` for constructing the continuous
        3D stepped granite seawall, coping stones, mooring bollards, and shoreline foam trim.
        """
        polylines: List[Tuple[str, List[Tuple[float, float]], bool]] = []

        # 1. Mainland Seawall (Bassin Peel -> Rue de la Commune -> Bassin de l'Horloge West Quay)
        mainland_wall = [(x, y) for (y, x) in MAINLAND_WEST_SEAWALL_PROFILE]
        polylines.append(("Mainland_Commune_And_Peel_Seawall", mainland_wall, False))

        # 2. Vieux-Port Inner Basin Promenade Seawall (from Way 83255355 eastern harbor edge)
        if self.vieux_port_poly and len(self.vieux_port_poly) >= 230:
            # Indices 196..236 trace from Quai de l'Horloge down the Old Port seawall to Lachine Canal
            polylines.append(("Vieux_Port_Harbor_Seawall", self.vieux_port_poly[196:], False))

        # 3. Pointe-du-Moulin 96-point Quay (Way 1272856121)
        if self.pointe_du_moulin_poly:
            polylines.append(("Pointe_du_Moulin_Quay_1272856121", self.pointe_du_moulin_poly, True))

        # 4. Grand Quai / Quai Alexandra (Way 243058804)
        if self.quai_alexandra_poly:
            polylines.append(("Quai_Alexandra_Grand_Quai_243058804", self.quai_alexandra_poly, True))

        # 5. Quai des Convoyeurs (Way 677248942)
        if self.quai_convoyeurs_poly:
            polylines.append(("Quai_des_Convoyeurs_677248942", self.quai_convoyeurs_poly, True))

        # 6. Quai King-Edward (Way 243058802)
        if self.quai_king_edward_poly:
            polylines.append(("Quai_King_Edward_243058802", self.quai_king_edward_poly, True))

        # 7. Quai Jacques-Cartier (Way 677248943 / 69948943)
        if self.quai_jacques_cartier_poly:
            polylines.append(("Quai_Jacques_Cartier_677248943", self.quai_jacques_cartier_poly, True))

        # 8. Île Bonsecours Outer Perimeter (Way 1180387334) & Bassin Bonsecours Lagoon Walls
        if self.ile_bonsecours_poly:
            polylines.append(("Ile_Bonsecours_Outer_1180387334", self.ile_bonsecours_poly, True))
        polylines.append(("Bassin_Bonsecours_Lagoon_Wall", self.bassin_bonsecours_lagoon_poly, True))
        polylines.append(("Bonsecours_Central_Island_Wall", self.bonsecours_central_island_poly, True))

        # 9. Quai de l'Horloge (East arm of Way 83255355 up to Tour de l'Horloge)
        polylines.append(("Quai_de_l_Horloge_83255355", self.quai_horloge_poly, True))

        # 10. Lachine Canal & Écluse No. 1 Channel Walls & West Spillway Basin Walls
        polylines.append(("Lachine_Canal_Ecluse1_Walls", self.lachine_main_channel_poly, True))
        polylines.append(("Lachine_West_Spillway_Walls", self.lachine_west_spillway_poly, True))

        # 11. Parc de Dieppe (Way 115577288) & Cité du Havre West Seawall
        if self.parc_de_dieppe_poly:
            polylines.append(("Parc_de_Dieppe_Peninsula_115577288", self.parc_de_dieppe_poly, True))
        cite_west_wall = self.cite_du_havre_south_poly[:12]
        polylines.append(("Cite_du_Havre_West_Seawall", cite_west_wall, False))

        return polylines


# Module-level singleton classifier for convenient `is_land(x, y)` / `is_water(x, y)` calls
_DEFAULT_CLASSIFIER: Optional[OSMWaterfrontClassifier] = None


def get_classifier(osm_data: Optional[Union[dict, str, Path]] = None) -> OSMWaterfrontClassifier:
    global _DEFAULT_CLASSIFIER
    if osm_data is not None or _DEFAULT_CLASSIFIER is None:
        _DEFAULT_CLASSIFIER = OSMWaterfrontClassifier(osm_data)
    return _DEFAULT_CLASSIFIER


def is_land(x: float, y: float) -> bool:
    """Module-level 2D land classifier (`True` on Mainland, Piers, Islands & Cité du Havre)."""
    return get_classifier().is_land(x, y)


def is_water(x: float, y: float) -> bool:
    """Module-level 2D water classifier (`True` in all Harbor Basins, Canals, Locks, Lagoons & River)."""
    return get_classifier().is_water(x, y)


# =============================================================================
# SECTION 2: PBR MATERIALS FOR WATER, FOAM, GRANITE SEAWALL & 4K SATELLITE GROUND
# =============================================================================

def _ensure_textures_synced() -> Tuple[Path, Path]:
    """Ensures water, granite, and 4K satellite textures are present in both assets/polyhaven and output/textures."""
    poly_dir = PROJECT_ROOT / "assets" / "polyhaven"
    out_tex_dir = PROJECT_ROOT / "output" / "textures"
    out_tex_dir.mkdir(parents=True, exist_ok=True)

    # Resolve 4K satellite texture (primary: assets/polyhaven/montreal_satellite_ortho_4k.jpg,
    # fallback: output/renders/google_maps_aerial_full_36blocks.png)
    sat_primary = poly_dir / "montreal_satellite_ortho_4k.jpg"
    sat_fallback = PROJECT_ROOT / "output" / "renders" / "google_maps_aerial_full_36blocks.png"
    sat_path = sat_primary if sat_primary.exists() else sat_fallback

    sync_files = [
        "water_river_diffuse_2k.jpg",
        "water_river_rough_2k.jpg",
        "water_river_nor_gl_2k.jpg",
        "water_foam_edge_2k.jpg",
        "stone_block_wall_Diffuse_2k.jpg",
        "stone_block_wall_Rough_2k.jpg",
        "stone_block_wall_nor_gl_2k.jpg",
        "montreal_satellite_ortho_4k.jpg",
    ]
    for fname in sync_files:
        src = poly_dir / fname
        dst = out_tex_dir / fname
        if src.exists() and not dst.exists():
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass

    return poly_dir, sat_path


def _wire_pbr_material(
    mat_name: str,
    diff_path: Optional[Path],
    rough_path: Optional[Path],
    nor_path: Optional[Path],
    base_rgba: Tuple[float, float, float, float],
    rough_val: float = 0.8,
    spec_val: float = 0.4,
    metallic_val: float = 0.0,
    normal_strength: float = 0.85,
):
    """
    Creates or updates a Blender Principled BSDF material with direct ShaderNodeTexImage links
    (no intermediate MixRGB nodes so Blender's USD exporter writes clean UsdPreviewSurface textures).
    """
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    mat.diffuse_color = base_rgba

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = base_rgba
    bsdf.inputs["Roughness"].default_value = rough_val
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic_val
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec_val
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    if diff_path and diff_path.exists():
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.location = (-350, 220)
        tex_d.image = bpy.data.images.load(str(diff_path), check_existing=True)
        tex_d.image.colorspace_settings.name = "sRGB"
        links.new(tex_d.outputs["Color"], bsdf.inputs["Base Color"])

    if rough_path and rough_path.exists():
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.location = (-350, -40)
        tex_r.image = bpy.data.images.load(str(rough_path), check_existing=True)
        tex_r.image.colorspace_settings.name = "Non-Color"
        links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])

    if nor_path and nor_path.exists():
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.location = (-600, -300)
        tex_n.image = bpy.data.images.load(str(nor_path), check_existing=True)
        tex_n.image.colorspace_settings.name = "Non-Color"
        norm_map = nodes.new("ShaderNodeNormalMap")
        norm_map.location = (-280, -300)
        norm_map.inputs["Strength"].default_value = normal_strength
        links.new(tex_n.outputs["Color"], norm_map.inputs["Color"])
        links.new(norm_map.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def create_water_seawall_and_satellite_materials() -> Dict[str, "bpy.types.Material"]:
    """Creates and wires all PBR materials required for water, foam, granite seawalls, bollards, and 4K satellite ground."""
    poly_dir, sat_path = _ensure_textures_synced()

    # 1. St. Lawrence River & Basins Water PBR (15m metric tiling)
    mat_water = _wire_pbr_material(
        "Mat_MTL_StLawrence_Water_PBR",
        poly_dir / "water_river_diffuse_2k.jpg",
        poly_dir / "water_river_rough_2k.jpg",
        poly_dir / "water_river_nor_gl_2k.jpg",
        base_rgba=(0.04, 0.22, 0.34, 1.0),
        rough_val=0.08,
        spec_val=0.92,
        normal_strength=0.90,
    )

    # 2. Shoreline Foam Edge Trim PBR (wired to water_foam_edge_2k.jpg)
    mat_foam = _wire_pbr_material(
        "Mat_MTL_Water_Foam_Edge",
        poly_dir / "water_foam_edge_2k.jpg",
        poly_dir / "water_river_rough_2k.jpg",
        poly_dir / "water_river_nor_gl_2k.jpg",
        base_rgba=(0.72, 0.84, 0.88, 1.0),
        rough_val=0.28,
        spec_val=0.65,
        normal_strength=0.50,
    )

    # 3. Stepped Granite Seawall & Coping Stone PBR (Mat_MTL_Quay_Granite)
    mat_granite = _wire_pbr_material(
        "Mat_MTL_Quay_Granite",
        poly_dir / "stone_block_wall_Diffuse_2k.jpg",
        poly_dir / "stone_block_wall_Rough_2k.jpg",
        poly_dir / "stone_block_wall_nor_gl_2k.jpg",
        base_rgba=(0.46, 0.45, 0.43, 1.0),
        rough_val=0.74,
        spec_val=0.38,
        normal_strength=1.0,
    )

    # 4. Cast-Iron Maritime Mooring Bollards PBR (Mat_MTL_CastIron_Black)
    mat_cast_iron = _wire_pbr_material(
        "Mat_MTL_CastIron_Black",
        poly_dir / "box_profile_metal_sheet_Diffuse_2k.jpg",
        poly_dir / "box_profile_metal_sheet_Rough_2k.jpg",
        poly_dir / "box_profile_metal_sheet_nor_gl_2k.jpg",
        base_rgba=(0.08, 0.09, 0.10, 1.0),
        rough_val=0.42,
        spec_val=0.60,
        metallic_val=0.85,
        normal_strength=0.40,
    )

    # 5. 4K Metric-Aligned Google Maps Satellite Ground Terrain PBR (Mat_MTL_Satellite_Ground_4K)
    mat_satellite = _wire_pbr_material(
        "Mat_MTL_Satellite_Ground_4K",
        sat_path,
        poly_dir / "clean_asphalt_Rough_2k.jpg",
        poly_dir / "clean_asphalt_nor_gl_2k.jpg",
        base_rgba=(0.32, 0.35, 0.30, 1.0),
        rough_val=0.86,
        spec_val=0.22,
        normal_strength=0.25,
    )

    return {
        "water": mat_water,
        "foam": mat_foam,
        "granite": mat_granite,
        "cast_iron": mat_cast_iron,
        "satellite": mat_satellite,
    }


# =============================================================================
# SECTION 3: SUB-CELL MARCHING-SQUARES BOUNDARY-SNAPPED WATER & SATELLITE GROUND
# =============================================================================

def _split_cell_land_water(
    clf: OSMWaterfrontClassifier,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    c00: bool,
    c10: bool,
    c11: bool,
    c01: bool,
) -> Tuple[List[List[Tuple[float, float]]], List[List[Tuple[float, float]]]]:
    """
    Given a grid cell `[x0, x1] x [y0, y1]` whose 4 corners `(c00, c10, c11, c01)`
    have mixed `is_land` booleans, computes the exact boundary transition points along
    any sign-changing edge via 4-step binary search and splits the cell into smooth
    CCW `land_polygons` and `water_polygons`.
    """
    corners = [
        (x0, y0, c00),
        (x1, y0, c10),
        (x1, y1, c11),
        (x0, y1, c01),
    ]

    def find_edge_crossing(ax: float, ay: float, a_land: bool, bx: float, by: float) -> Tuple[float, float]:
        lx, ly = (ax, ay) if a_land else (bx, by)
        wx, wy = (bx, by) if a_land else (ax, ay)
        for _ in range(4):
            mx = 0.5 * (lx + wx)
            my = 0.5 * (ly + wy)
            if clf.is_land(mx, my):
                lx, ly = mx, my
            else:
                wx, wy = mx, my
        return (0.5 * (lx + wx), 0.5 * (ly + wy))

    land_ring: List[Tuple[float, float]] = []
    water_ring: List[Tuple[float, float]] = []

    for i in range(4):
        ax, ay, a_land = corners[i]
        bx, by, b_land = corners[(i + 1) % 4]
        if a_land:
            land_ring.append((ax, ay))
        else:
            water_ring.append((ax, ay))

        if a_land != b_land:
            cx, cy = find_edge_crossing(ax, ay, a_land, bx, by)
            land_ring.append((cx, cy))
            water_ring.append((cx, cy))

    land_polys = [land_ring] if len(land_ring) >= 3 else []
    water_polys = [water_ring] if len(water_ring) >= 3 else []
    return land_polys, water_polys


def _add_shoreline_foam_ribbon_to_bm(
    bm: "bmesh.types.BMesh",
    clf: OSMWaterfrontClassifier,
    polylines: Sequence[Tuple[str, List[Tuple[float, float]], bool]],
    z_foam: float = -2.18,
    foam_width: float = 1.85,
    mat_index: int = 1,
) -> int:
    """
    Adds a subtle shoreline foam trim ribbon (`water_foam_edge_2k.jpg` at `Z = -2.18m`)
    along the water side of all quay, pier, island, and canal edges.
    """
    foam_faces = 0
    for _, pts, is_closed in polylines:
        n = len(pts)
        if n < 2:
            continue
        seg_count = n if is_closed else n - 1
        for i in range(seg_count):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            dx = x1 - x0
            dy = y1 - y0
            seg_len = math.hypot(dx, dy)
            if seg_len < 0.4 or seg_len > 280.0:
                continue

            tx, ty = dx / seg_len, dy / seg_len
            # Candidate normal pointing toward water
            nx, ny = ty, -tx
            mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            if not clf.is_water(mx + 1.5 * nx, my + 1.5 * ny):
                if clf.is_water(mx - 1.5 * nx, my - 1.5 * ny):
                    nx, ny = -nx, -ny
                else:
                    continue

            # Inner edge tucked 0.15m into the seawall face; outer edge 1.85m out on the water
            in_off = -0.15
            out_off = foam_width
            v0 = bm.verts.new((x0 + nx * in_off, y0 + ny * in_off, z_foam))
            v1 = bm.verts.new((x1 + nx * in_off, y1 + ny * in_off, z_foam))
            v2 = bm.verts.new((x1 + nx * out_off, y1 + ny * out_off, z_foam))
            v3 = bm.verts.new((x0 + nx * out_off, y0 + ny * out_off, z_foam))
            try:
                f = bm.faces.new([v0, v1, v2, v3])
                if f.normal.z < 0:
                    f.normal_flip()
                f.material_index = mat_index
                foam_faces += 1
            except ValueError:
                pass

    return foam_faces


def build_water_district_mesh(
    clf: OSMWaterfrontClassifier,
    water_mat: "bpy.types.Material",
    foam_mat: "bpy.types.Material",
    target_col: "bpy.types.Collection",
) -> Tuple["bpy.types.Object", int, int]:
    """
    Rebuilds `Water_District_StLawrence_And_Canals` at `Z = -2.20m` with smooth
    Marching-Squares shoreline boundaries across all `is_water(x, y)` regions,
    plus shoreline foam trim (`Z = -2.18m`) wired to `water_foam_edge_2k.jpg`.
    """
    old_w = bpy.data.objects.get("Water_District_StLawrence_And_Canals")
    if old_w:
        bpy.data.objects.remove(old_w, do_unlink=True)

    bm = bmesh.new()
    z_water = -2.20

    # High-resolution 6.0m grid across the entire waterfront, piers, locks, canals & Cité du Havre
    # X in [210.0, 1140.0], Y in [-1620.0, 1200.0]
    step_fine = 6.0
    xs_fine = np.arange(210.0, 1140.0 + step_fine, step_fine, dtype=np.float64)
    ys_fine = np.arange(-1620.0, 1200.0 + step_fine, step_fine, dtype=np.float64)
    gx_f, gy_f = np.meshgrid(xs_fine, ys_fine, indexing="ij")
    land_f = clf.evaluate_land_grid(gx_f, gy_f)

    nx_f = len(xs_fine) - 1
    ny_f = len(ys_fine) - 1
    water_poly_count = 0

    for ix in range(nx_f):
        x0 = float(xs_fine[ix])
        x1 = float(xs_fine[ix + 1])
        for iy in range(ny_f):
            c00 = bool(land_f[ix, iy])
            c10 = bool(land_f[ix + 1, iy])
            c11 = bool(land_f[ix + 1, iy + 1])
            c01 = bool(land_f[ix, iy + 1])

            if c00 and c10 and c11 and c01:
                # 100% dry land cell
                continue

            y0 = float(ys_fine[iy])
            y1 = float(ys_fine[iy + 1])

            if not (c00 or c10 or c11 or c01):
                # 100% open water cell
                v0 = bm.verts.new((x0, y0, z_water))
                v1 = bm.verts.new((x1, y0, z_water))
                v2 = bm.verts.new((x1, y1, z_water))
                v3 = bm.verts.new((x0, y1, z_water))
                f = bm.faces.new([v0, v1, v2, v3])
                f.material_index = 0
                water_poly_count += 1
            else:
                # Shoreline boundary cell -> smooth sub-cell Marching Squares split
                _, water_rings = _split_cell_land_water(clf, x0, x1, y0, y1, c00, c10, c11, c01)
                for ring in water_rings:
                    bverts = [bm.verts.new((px, py, z_water)) for (px, py) in ring]
                    try:
                        f = bm.faces.new(bverts)
                        if f.normal.z < 0:
                            f.normal_flip()
                        f.material_index = 0
                        water_poly_count += 1
                    except ValueError:
                        pass

    # Eastern St. Lawrence River deep channel extension (X in [1140.0, 1860.0], Y in [-1620.0, 1200.0])
    step_east = 24.0
    xs_east = np.arange(1140.0, 1860.0 + step_east, step_east, dtype=np.float64)
    ys_east = np.arange(-1620.0, 1200.0 + step_east, step_east, dtype=np.float64)
    gx_e, gy_e = np.meshgrid(xs_east, ys_east, indexing="ij")
    land_e = clf.evaluate_land_grid(gx_e, gy_e)

    for ix in range(len(xs_east) - 1):
        x0, x1 = float(xs_east[ix]), float(xs_east[ix + 1])
        for iy in range(len(ys_east) - 1):
            if land_e[ix, iy] and land_e[ix + 1, iy] and land_e[ix + 1, iy + 1] and land_e[ix, iy + 1]:
                continue
            y0, y1 = float(ys_east[iy]), float(ys_east[iy + 1])
            v0 = bm.verts.new((x0, y0, z_water))
            v1 = bm.verts.new((x1, y0, z_water))
            v2 = bm.verts.new((x1, y1, z_water))
            v3 = bm.verts.new((x0, y1, z_water))
            f = bm.faces.new([v0, v1, v2, v3])
            f.material_index = 0
            water_poly_count += 1

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)

    # Add shoreline foam edge trim at Z = -2.18m along all quay & pier boundaries
    polylines = clf.get_shoreline_polylines()
    foam_count = _add_shoreline_foam_ribbon_to_bm(bm, clf, polylines, z_foam=-2.18, foam_width=1.85, mat_index=1)

    bm.normal_update()

    # Assign 15m metric UV tiling on water faces and 4m metric UV tiling on foam edge faces
    uv_layer = bm.loops.layers.uv.verify()
    for f in bm.faces:
        tile_m = 15.0 if f.material_index == 0 else 4.0
        for loop in f.loops:
            co = loop.vert.co
            loop[uv_layer].uv = (co.x / tile_m, co.y / tile_m)

    me_w = bpy.data.meshes.new("Water_District_StLawrence_And_Canals")
    me_w.materials.append(water_mat)
    me_w.materials.append(foam_mat)
    bm.to_mesh(me_w)
    bm.free()
    me_w.update()

    obj_w = bpy.data.objects.new("Water_District_StLawrence_And_Canals", me_w)
    obj_w["ue5_collision_role"] = "DRIVABLE"
    target_col.objects.link(obj_w)

    log(f"Built Water_District_StLawrence_And_Canals: {water_poly_count} smooth water faces (Z=-2.20m) + {foam_count} shoreline foam edge faces (Z=-2.18m).")
    return obj_w, water_poly_count, foam_count


# =============================================================================
# SECTION 4: CONTINUOUS 3D STEPPED GRANITE SEAWALL & CAST-IRON MOORING BOLLARDS
# =============================================================================

def _add_stepped_granite_seawall_segment(
    bm: "bmesh.types.BMesh",
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    nx: float,
    ny: float,
    granite_mat_idx: int = 0,
) -> int:
    """
    Constructs a 3D stepped granite seawall segment from `(x0, y0)` to `(x1, y1)`
    with unit water-facing normal `(nx, ny)` from `Z = -2.50m` to `Z = +0.18m`:
      - Tier 1 (Submerged Granite Footing & Lower Ashlar Wall):
        `Z = -2.50m .. -1.10m`, offset `-0.50m` (land side) to `+0.50m` (water side).
      - Tier 2 (Upper Battered Ashlar Granite Wall with 0.18m Water-Side Step Ledge):
        `Z = -1.10m .. +0.04m`, offset `-0.45m` (land side) to `+0.32m` (water side).
      - Tier 3 (Overhanging 0.45m-wide Granite Coping Stone):
        `Z = +0.04m .. +0.18m`, offset `-0.07m` (land side) to `+0.38m` (water side, width = 0.45m!).
    """
    tiers = [
        (-2.50, -1.10, -0.50, 0.50),
        (-1.10, 0.04, -0.45, 0.32),
        (0.04, 0.18, -0.07, 0.38),  # 0.45m-wide granite coping stone at top (+0.04m .. +0.18m)
    ]
    faces_added = 0
    for z_bot, z_top, off_land, off_water in tiers:
        p00 = (x0 + nx * off_land, y0 + ny * off_land)
        p10 = (x1 + nx * off_land, y1 + ny * off_land)
        p11 = (x1 + nx * off_water, y1 + ny * off_water)
        p01 = (x0 + nx * off_water, y0 + ny * off_water)

        b00 = bm.verts.new((p00[0], p00[1], z_bot))
        b10 = bm.verts.new((p10[0], p10[1], z_bot))
        b11 = bm.verts.new((p11[0], p11[1], z_bot))
        b01 = bm.verts.new((p01[0], p01[1], z_bot))

        t00 = bm.verts.new((p00[0], p00[1], z_top))
        t10 = bm.verts.new((p10[0], p10[1], z_top))
        t11 = bm.verts.new((p11[0], p11[1], z_top))
        t01 = bm.verts.new((p01[0], p01[1], z_top))

        for quad in [
            [t00, t10, t11, t01],  # Top (+Z)
            [b00, b01, b11, b10],  # Bottom (-Z)
            [b01, t01, t11, b11],  # Water-facing front wall
            [b10, t10, t00, b00],  # Land-facing back wall
            [b00, t00, t01, b01],  # Start endcap
            [b11, t11, t10, b10],  # End endcap
        ]:
            try:
                f = bm.faces.new(quad)
                f.material_index = granite_mat_idx
                faces_added += 1
            except ValueError:
                pass

    return faces_added


def _add_cast_iron_mooring_bollard(
    bm: "bmesh.types.BMesh",
    bx: float,
    by: float,
    z_base: float = 0.18,
    iron_mat_idx: int = 1,
) -> int:
    """
    Constructs a 3D heritage Cast-Iron Maritime Mooring Bollard at `(bx, by, z_base=0.18m)`
    on top of the granite coping stone:
      - Octagonal bolted base flange (`r = 0.21m`, `Z = 0.18m .. 0.25m`)
      - Tapered octagonal cast-iron column (`r = 0.14m -> 0.12m`, `Z = 0.25m .. 0.66m`)
      - Flared mushroom mooring cap (`r = 0.18m`, `Z = 0.66m .. 0.76m`)
      - Cross-horn mooring bar (`0.42m` span at `Z = 0.50m .. 0.58m`)
    """
    faces_added = 0
    n_sides = 8
    angles = [2.0 * math.pi * k / n_sides for k in range(n_sides)]

    # 3 stacked octagonal rings: Base Flange -> Column -> Mushroom Cap
    sections = [
        (z_base, z_base + 0.07, 0.21, 0.19),
        (z_base + 0.07, z_base + 0.48, 0.14, 0.125),
        (z_base + 0.48, z_base + 0.58, 0.18, 0.16),
    ]

    for z0, z1, r0, r1 in sections:
        bot_ring = [bm.verts.new((bx + r0 * math.cos(a), by + r0 * math.sin(a), z0)) for a in angles]
        top_ring = [bm.verts.new((bx + r1 * math.cos(a), by + r1 * math.sin(a), z1)) for a in angles]
        for k in range(n_sides):
            kn = (k + 1) % n_sides
            try:
                f = bm.faces.new([bot_ring[k], bot_ring[kn], top_ring[kn], top_ring[k]])
                f.material_index = iron_mat_idx
                faces_added += 1
            except ValueError:
                pass
        try:
            f_cap = bm.faces.new(top_ring)
            f_cap.material_index = iron_mat_idx
            faces_added += 1
        except ValueError:
            pass

    # Horizontal mooring horn bar across the bollard waist
    hx0, hx1 = bx - 0.21, bx + 0.21
    hy0, hy1 = by - 0.045, by + 0.045
    hz0, hz1 = z_base + 0.30, z_base + 0.38
    hv = [
        bm.verts.new((hx0, hy0, hz0)),
        bm.verts.new((hx1, hy0, hz0)),
        bm.verts.new((hx1, hy1, hz0)),
        bm.verts.new((hx0, hy1, hz0)),
        bm.verts.new((hx0, hy0, hz1)),
        bm.verts.new((hx1, hy0, hz1)),
        bm.verts.new((hx1, hy1, hz1)),
        bm.verts.new((hx0, hy1, hz1)),
    ]
    for q in [
        [hv[4], hv[5], hv[6], hv[7]],
        [hv[0], hv[3], hv[2], hv[1]],
        [hv[0], hv[1], hv[5], hv[4]],
        [hv[2], hv[3], hv[7], hv[6]],
        [hv[0], hv[4], hv[7], hv[3]],
        [hv[1], hv[2], hv[6], hv[5]],
    ]:
        try:
            f = bm.faces.new(q)
            f.material_index = iron_mat_idx
            faces_added += 1
        except ValueError:
            pass

    return faces_added


def build_continuous_granite_seawall(
    clf: OSMWaterfrontClassifier,
    granite_mat: "bpy.types.Material",
    cast_iron_mat: "bpy.types.Material",
    target_col: "bpy.types.Collection",
    bollard_spacing_m: float = 18.0,
) -> Tuple["bpy.types.Object", int, int]:
    """
    Rebuilds `Quays_And_Canal_Retaining_Walls` as a continuous 3D stepped granite
    seawall (`Mat_MTL_Quay_Granite`, `Z = -2.50m .. +0.18m`) with `0.45m`-wide
    granite coping stones and 3D cast-iron mooring bollards (`Mat_MTL_CastIron_Black`)
    every `18m` along the exact boundary between `is_land` and `is_water`.
    """
    old_q = bpy.data.objects.get("Quays_And_Canal_Retaining_Walls")
    if old_q:
        bpy.data.objects.remove(old_q, do_unlink=True)

    bm = bmesh.new()
    polylines = clf.get_shoreline_polylines()

    wall_segments = 0
    bollard_count = 0

    for _, pts, is_closed in polylines:
        n = len(pts)
        if n < 2:
            continue
        seg_count = n if is_closed else n - 1
        dist_accum = 6.0  # First bollard 6m along each quay

        for i in range(seg_count):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            dx = x1 - x0
            dy = y1 - y0
            seg_len = math.hypot(dx, dy)
            if seg_len < 0.35 or seg_len > 320.0:
                continue

            tx, ty = dx / seg_len, dy / seg_len
            # Water-facing normal
            nx, ny = ty, -tx
            mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            if not clf.is_water(mx + 1.8 * nx, my + 1.8 * ny):
                if clf.is_water(mx - 1.8 * nx, my - 1.8 * ny):
                    nx, ny = -nx, -ny

            _add_stepped_granite_seawall_segment(bm, x0, y0, x1, y1, nx, ny, granite_mat_idx=0)
            wall_segments += 1

            # Place cast-iron mooring bollards every 18m centered on the 0.45m coping stone
            pos_along = bollard_spacing_m - dist_accum
            while pos_along <= seg_len:
                bx = x0 + tx * pos_along + nx * 0.15
                by = y0 + ty * pos_along + ny * 0.15
                _add_cast_iron_mooring_bollard(bm, bx, by, z_base=0.18, iron_mat_idx=1)
                bollard_count += 1
                pos_along += bollard_spacing_m

            dist_accum = (dist_accum + seg_len) % bollard_spacing_m

    bm.normal_update()

    # Apply 3.0m world-space triplanar metric UVs
    uv_layer = bm.loops.layers.uv.verify()
    tile_m = 3.0
    for f in bm.faces:
        ax, ay, az = abs(f.normal.x), abs(f.normal.y), abs(f.normal.z)
        for loop in f.loops:
            co = loop.vert.co
            if az >= ax and az >= ay:
                loop[uv_layer].uv = (co.x / tile_m, co.y / tile_m)
            elif ax >= ay:
                loop[uv_layer].uv = (co.y / tile_m, co.z / tile_m)
            else:
                loop[uv_layer].uv = (co.x / tile_m, co.z / tile_m)

    me_q = bpy.data.meshes.new("Quays_And_Canal_Retaining_Walls")
    me_q.materials.append(granite_mat)
    me_q.materials.append(cast_iron_mat)
    bm.to_mesh(me_q)
    bm.free()
    me_q.update()

    obj_q = bpy.data.objects.new("Quays_And_Canal_Retaining_Walls", me_q)
    obj_q["ue5_collision_role"] = "DRIVABLE"
    target_col.objects.link(obj_q)

    log(f"Built Quays_And_Canal_Retaining_Walls: {wall_segments} stepped granite seawall segments (Z=-2.50m..+0.18m) + {bollard_count} cast-iron mooring bollards.")
    return obj_q, wall_segments, bollard_count


# =============================================================================
# SECTION 5: REBUILD `Ground_District_Solid_Collider` WITH 4K SATELLITE ORTHO
# =============================================================================

def _add_prism_polygon_to_bm(
    bm: "bmesh.types.BMesh",
    ring_2d: Sequence[Tuple[float, float]],
    z_bot: float,
    z_top: float,
    mat_idx: int = 0,
    add_side_walls: bool = False,
) -> int:
    """
    Adds a solid 3D prism with top face at `z_top` (+Z normal), bottom face at `z_bot` (-Z normal),
    and optional vertical side walls for any 2D polygon `ring_2d`.
    """
    n = len(ring_2d)
    if n < 3:
        return 0

    # Ensure CCW winding in 2D
    area2 = 0.0
    for i in range(n):
        x1, y1 = ring_2d[i]
        x2, y2 = ring_2d[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
    pts = list(reversed(ring_2d)) if area2 < 0.0 else list(ring_2d)

    top_verts = [bm.verts.new((px, py, z_top)) for (px, py) in pts]
    bot_verts = [bm.verts.new((px, py, z_bot)) for (px, py) in pts]

    faces_created = 0
    try:
        f_top = bm.faces.new(top_verts)
        if f_top.normal.z < 0:
            f_top.normal_flip()
        f_top.material_index = mat_idx
        faces_created += 1
    except ValueError:
        pass

    try:
        f_bot = bm.faces.new(list(reversed(bot_verts)))
        if f_bot.normal.z > 0:
            f_bot.normal_flip()
        f_bot.material_index = mat_idx
        faces_created += 1
    except ValueError:
        pass

    if add_side_walls:
        for i in range(n):
            inext = (i + 1) % n
            try:
                f_side = bm.faces.new([bot_verts[i], bot_verts[inext], top_verts[inext], top_verts[i]])
                f_side.material_index = mat_idx
                faces_created += 1
            except ValueError:
                pass

    return faces_created


def build_satellite_ground_collider(
    clf: OSMWaterfrontClassifier,
    satellite_mat: "bpy.types.Material",
    target_col: "bpy.types.Collection",
) -> Tuple["bpy.types.Object", int, int]:
    """
    Rebuilds `Ground_District_Solid_Collider`:
      - For all `is_land(x, y)` cells: `Z = -0.05m` top face (+Z), `Z = -2.50m` bottom face (-Z).
      - For all `is_water(x, y)` cells: drops cleanly to `Z = -2.50m` top face (+Z), `Z = -2.80m` bottom face (-Z)
        so water basins (`Z = -2.20m`) are never covered by ground!
      - Assigned `Mat_MTL_Satellite_Ground_4K` with exact metric UV projection:
          `u = (x - (40.0 - 975.0)) / 1950.0`
          `v = (y - (-60.0 - 975.0)) / 1950.0`
    """
    old_col = bpy.data.objects.get("Ground_District_Solid_Collider")
    if old_col:
        bpy.data.objects.remove(old_col, do_unlink=True)

    bm = bmesh.new()
    z_land_top = -0.05
    z_land_bot = -2.50
    z_water_top = -2.50
    z_water_bot = -2.80

    land_face_count = 0
    seabed_face_count = 0

    # 1. Inland West Mainland (X in [-980.0, 210.0], Y in [-1620.0, 1200.0]) -> 100% Land
    step_west = 45.0
    xs_w = np.arange(-980.0, 210.0, step_west, dtype=np.float64)
    if xs_w[-1] < 210.0:
        xs_w = np.append(xs_w, 210.0)
    ys_w = np.arange(-1620.0, 1200.0, step_west, dtype=np.float64)
    if ys_w[-1] < 1200.0:
        ys_w = np.append(ys_w, 1200.0)

    for ix in range(len(xs_w) - 1):
        x0, x1 = float(xs_w[ix]), float(xs_w[ix + 1])
        for iy in range(len(ys_w) - 1):
            y0, y1 = float(ys_w[iy]), float(ys_w[iy + 1])
            ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            is_edge = (ix == 0 or iy == 0 or iy == len(ys_w) - 2)
            _add_prism_polygon_to_bm(bm, ring, z_land_bot, z_land_top, mat_idx=0, add_side_walls=is_edge)
            land_face_count += 1

    # 2. Waterfront, Piers, Locks, Canals & Cité du Havre Zone (X in [210.0, 1140.0], Y in [-1620.0, 1200.0])
    # Uses 8.0m resolution + exact Marching-Squares sub-cell boundary splitting so land never pokes into water!
    step_wf = 8.0
    xs_f = np.arange(210.0, 1140.0 + step_wf, step_wf, dtype=np.float64)
    ys_f = np.arange(-1620.0, 1200.0 + step_wf, step_wf, dtype=np.float64)
    gx_f, gy_f = np.meshgrid(xs_f, ys_f, indexing="ij")
    land_f = clf.evaluate_land_grid(gx_f, gy_f)

    nx_f = len(xs_f) - 1
    ny_f = len(ys_f) - 1

    for ix in range(nx_f):
        x0, x1 = float(xs_f[ix]), float(xs_f[ix + 1])
        for iy in range(ny_f):
            c00 = bool(land_f[ix, iy])
            c10 = bool(land_f[ix + 1, iy])
            c11 = bool(land_f[ix + 1, iy + 1])
            c01 = bool(land_f[ix, iy + 1])
            y0, y1 = float(ys_f[iy]), float(ys_f[iy + 1])

            if c00 and c10 and c11 and c01:
                # 100% Land cell -> Z = -0.05m top, Z = -2.50m bottom
                ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
                _add_prism_polygon_to_bm(bm, ring, z_land_bot, z_land_top, mat_idx=0, add_side_walls=False)
                land_face_count += 1
            elif not (c00 or c10 or c11 or c01):
                # 100% Water cell -> drops to Z = -2.50m top, Z = -2.80m bottom (seabed under water!)
                ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
                _add_prism_polygon_to_bm(bm, ring, z_water_bot, z_water_top, mat_idx=0, add_side_walls=False)
                seabed_face_count += 1
            else:
                # Shoreline transition cell -> split into smooth Land prism (-0.05m) and Seabed prism (-2.50m)
                land_rings, water_rings = _split_cell_land_water(clf, x0, x1, y0, y1, c00, c10, c11, c01)
                for lring in land_rings:
                    _add_prism_polygon_to_bm(bm, lring, z_land_bot, z_land_top, mat_idx=0, add_side_walls=True)
                    land_face_count += 1
                for wring in water_rings:
                    _add_prism_polygon_to_bm(bm, wring, z_water_bot, z_water_top, mat_idx=0, add_side_walls=False)
                    seabed_face_count += 1

    # 3. Far East Zone (X in [1140.0, 1860.0], Y in [-1620.0, 1200.0])
    step_east = 36.0
    xs_e = np.arange(1140.0, 1860.0 + step_east, step_east, dtype=np.float64)
    ys_e = np.arange(-1620.0, 1200.0 + step_east, step_east, dtype=np.float64)
    gx_e, gy_e = np.meshgrid(xs_e, ys_e, indexing="ij")
    land_e = clf.evaluate_land_grid(gx_e, gy_e)

    for ix in range(len(xs_e) - 1):
        x0, x1 = float(xs_e[ix]), float(xs_e[ix + 1])
        for iy in range(len(ys_e) - 1):
            y0, y1 = float(ys_e[iy]), float(ys_e[iy + 1])
            ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            if land_e[ix, iy] and land_e[ix + 1, iy] and land_e[ix + 1, iy + 1] and land_e[ix, iy + 1]:
                _add_prism_polygon_to_bm(bm, ring, z_land_bot, z_land_top, mat_idx=0, add_side_walls=True)
                land_face_count += 1
            else:
                _add_prism_polygon_to_bm(bm, ring, z_water_bot, z_water_top, mat_idx=0, add_side_walls=False)
                seabed_face_count += 1

    bm.normal_update()

    # Apply exact metric Google Maps Satellite UV projection:
    #   u = (x - (40.0 - 975.0)) / 1950.0
    #   v = (y - (-60.0 - 975.0)) / 1950.0
    uv_layer = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for loop in f.loops:
            co = loop.vert.co
            u, v = satellite_uv_from_xy(co.x, co.y)
            loop[uv_layer].uv = (u, v)

    me_col = bpy.data.meshes.new("Ground_District_Solid_Collider")
    me_col.materials.append(satellite_mat)
    bm.to_mesh(me_col)
    bm.free()
    me_col.update()

    obj_col = bpy.data.objects.new("Ground_District_Solid_Collider", me_col)
    obj_col["ue5_collision_role"] = "DRIVABLE"
    target_col.objects.link(obj_col)

    log(
        f"Built Ground_District_Solid_Collider with Mat_MTL_Satellite_Ground_4K: "
        f"{land_face_count} land cells (Z=-0.05m..-2.50m) + {seabed_face_count} submerged basin cells (Z=-2.50m..-2.80m)."
    )
    return obj_col, land_face_count, seabed_face_count


# =============================================================================
# SECTION 6: CLEAN STRAY BLOCK GROUND / WATER FACES OVER HARBOR BASINS
# =============================================================================

def clean_overlapping_block_ground_and_water_faces(clf: OSMWaterfrontClassifier) -> int:
    """
    Ensures no block ground, public realm, or park lawn mesh has stray horizontal
    concrete/asphalt/grass/shallow-water faces covering our `is_water(x, y)` harbor basins,
    and prevents Z-fighting at `Z = -0.05m` with `Ground_District_Solid_Collider`.
    """
    cleaned_faces = 0
    protected_names = {
        "Water_District_StLawrence_And_Canals",
        "Quays_And_Canal_Retaining_Walls",
        "Ground_District_Solid_Collider",
    }

    target_prefixes = (
        "MTL_Owned_Ground",
        "MTL_Owned_Quai",
        "MTL_Owned_Pointe",
        "MTL_Owned_Lachine",
        "MTL_Owned_Public_Realm",
        "MTL_VM_0020_Ramparts",
        "MTL_VM_0024_Basin",
        "MTL_VM_0028_Ground",
        "Plage_de_l_Horloge",
        "Peninsula_Ground",
        "Ground_Quays",
        "Old_Port_Linear_Parks",
    )

    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.data or obj.name in protected_names:
            continue
        if not any(obj.name.startswith(p) for p in target_prefixes):
            continue

        me = obj.data
        mw = obj.matrix_world
        mats = [m.name.lower() if m else "" for m in me.materials]

        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        to_del = []

        for f in bm.faces:
            mname = mats[f.material_index] if f.material_index < len(mats) else ""
            wc = mw @ f.calc_center_median()

            # 1. Remove duplicate block-specific water faces so unified Z=-2.20m water is conflict-free
            if any(k in mname for k in ("water", "basin", "river")):
                to_del.append(f)
                continue

            # 2. Keep floating marina docks, bridges, and boats intact
            if any(k in mname for k in ("marina", "dock", "wood", "plank", "deck", "bridge", "boat", "ship", "ferry")):
                continue

            # 3. For flat ground/asphalt/cobblestone/grass faces near Z=0, remove if center is over open water
            #    (more than 2.5m outside land polygons)
            if abs(f.normal.z) > 0.75 and -1.80 <= wc.z <= 0.35:
                if clf.is_water(wc.x, wc.y):
                    # Check if all 4 directional probes around center are also water (i.e. not a pier curb edge)
                    if (
                        clf.is_water(wc.x + 2.0, wc.y)
                        and clf.is_water(wc.x - 2.0, wc.y)
                        and clf.is_water(wc.x, wc.y + 2.0)
                        and clf.is_water(wc.x, wc.y - 2.0)
                    ):
                        to_del.append(f)
                        continue

                # Prevent Z-fighting with Ground_District_Solid_Collider top face at Z = -0.05m
                if abs(wc.z - (-0.05)) < 0.018:
                    for v in f.verts:
                        wco = mw @ v.co
                        if abs(wco.z - (-0.05)) < 0.018:
                            v.co.z += 0.035

        if to_del:
            bmesh.ops.delete(bm, geom=list(set(to_del)), context="FACES")
            cleaned_faces += len(to_del)

        bm.normal_update()
        bm.to_mesh(me)
        bm.free()
        me.update()

    log(f"Cleaned {cleaned_faces} stray block water/ground faces over harbor basins.")
    return cleaned_faces


# =============================================================================
# SECTION 7: MAIN ENTRY POINT `rebuild_water_and_satellite_terrain(osm_data)`
# =============================================================================

def rebuild_water_and_satellite_terrain(osm_data: Optional[Union[dict, str, Path]] = None) -> dict:
    """
    Main entry point to be called inside Blender 5.2 on `output/montreal_master.blend`.

    1. Builds the exact OpenStreetMap 2D land-vs-water classifier (`OSMWaterfrontClassifier`)
       from `data/open_data/old_montreal_osm.json` (or `osm_data`).
    2. Rebuilds `Water_District_StLawrence_And_Canals` (`Z = -2.20m`, `Mat_MTL_StLawrence_Water_PBR`
       with `15m` metric UV tiling + `Z = -2.18m` shoreline foam trim `water_foam_edge_2k.jpg`).
    3. Rebuilds `Quays_And_Canal_Retaining_Walls` (`Z = -2.50m .. +0.18m`, `Mat_MTL_Quay_Granite`
       with `0.45m`-wide granite coping stones and 3D cast-iron mooring bollards every `18m`).
    4. Rebuilds `Ground_District_Solid_Collider` (`Z = -0.05m` top / `Z = -2.50m` bottom on land,
       dropping to `Z = -2.50m` top / `Z = -2.80m` bottom under water) with `Mat_MTL_Satellite_Ground_4K`
       wired directly to `assets/polyhaven/montreal_satellite_ortho_4k.jpg` using exact metric UVs:
         `u = (x - (40.0 - 975.0)) / 1950.0`
         `v = (y - (-60.0 - 975.0)) / 1950.0`
    """
    clf = get_classifier(osm_data)

    if not IN_BLENDER:
        log("Loaded outside Blender; returning classifier & polygon summary.")
        return {
            "classifier": clf,
            "is_land": clf.is_land,
            "is_water": clf.is_water,
            "shoreline_polylines": len(clf.get_shoreline_polylines()),
        }

    street_col = bpy.data.collections.get("Master_Street_Network")
    if not street_col:
        street_col = bpy.data.collections.new("Master_Street_Network")
        bpy.context.scene.collection.children.link(street_col)

    mats = create_water_seawall_and_satellite_materials()

    # 1. Clean stray block ground/water faces over harbor basins
    cleaned_faces = clean_overlapping_block_ground_and_water_faces(clf)

    # 2. Rebuild Water_District_StLawrence_And_Canals (Z = -2.20m) & Shoreline Foam Trim (Z = -2.18m)
    obj_water, water_faces, foam_faces = build_water_district_mesh(
        clf,
        water_mat=mats["water"],
        foam_mat=mats["foam"],
        target_col=street_col,
    )

    # 3. Rebuild Continuous 3D Stepped Granite Seawall (Z = -2.50m .. +0.18m) & Cast-Iron Bollards
    obj_seawall, wall_segments, bollard_count = build_continuous_granite_seawall(
        clf,
        granite_mat=mats["granite"],
        cast_iron_mat=mats["cast_iron"],
        target_col=street_col,
        bollard_spacing_m=18.0,
    )

    # 4. Rebuild Ground_District_Solid_Collider with 4K Metric-Aligned Google Maps Satellite Texture
    obj_ground, land_cells, seabed_cells = build_satellite_ground_collider(
        clf,
        satellite_mat=mats["satellite"],
        target_col=street_col,
    )

    summary = {
        "water_object": obj_water.name,
        "water_faces": water_faces,
        "foam_faces": foam_faces,
        "seawall_object": obj_seawall.name,
        "seawall_segments": wall_segments,
        "mooring_bollards": bollard_count,
        "ground_object": obj_ground.name,
        "land_cells": land_cells,
        "seabed_cells": seabed_cells,
        "cleaned_block_faces": cleaned_faces,
        "is_land": clf.is_land,
        "is_water": clf.is_water,
    }
    log(f"Overhaul complete: {summary}")
    return summary


if __name__ == "__main__":
    rebuild_water_and_satellite_terrain()
