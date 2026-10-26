"""
Build MTL-OLY-0003 (Sucrerie Lantic Heritage Refinery, Quai Sutherland & Hochelaga Sainte-Catherine Est Corridor)
=================================================================================================================
Delegates to `src.blocks.refine_mtl_oly_0003.refine_scene()` to construct the full superblock
(`X=[550..1400], Y=[2900..3950]`), exact Satellite Nadir Zoning, Sucrerie Lantic Heritage Sugar Refinery,
Quai Sutherland Port Rail Yard, all 4 Street View camera architectural corridors, raised 3D sidewalks/curbs,
3D road markings/crosswalks, Poly Haven streetlamps, and lush 9-lobe 3D trees.
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
REPO_ROOT = SRC_DIR.parent
for p in (str(REPO_ROOT), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.blocks.refine_mtl_oly_0003 import refine_scene

if __name__ == "__main__":
    refine_scene()
