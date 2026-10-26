"""
Build MTL-OLY-0004 (Marché Maisonneuve Beaux-Arts Dome, Bain Morgan & Promenade Avenue Morgan Axis)
===================================================================================================
Delegates to `src.blocks.refine_mtl_oly_0004.main()` to construct the complete superblock
`X=[350..1450], Y=[3900..5150]` with bespoke BMesh hero landmarks, 2,650+ real OSM buildings
with floor-by-floor 3D fenestration, Shapely Boolean-manifold streets/sidewalks/curbs/markings,
68 Poly Haven 3D streetlamps, and 115 high-poly Poly Haven 3D trees.
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.blocks.refine_mtl_oly_0004 import main

if __name__ == "__main__":
    main()
