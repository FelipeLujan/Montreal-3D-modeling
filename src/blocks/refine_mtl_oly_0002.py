"""
Bespoke BMesh Refinement Script for MTL-OLY-0002 (`src/blocks/refine_mtl_oly_0002.py`)
======================================================================================
Executes the full bespoke BMesh refinement pass for `MTL-OLY-0002` (Maison de Radio-Canada
23-story hexagonal Brutalist tower, broadcast podium, Cathédrale Saints-Pierre-et-Paul,
Nouvelle Maison de Radio-Canada, Pont Jacques-Cartier green steel Warren truss span,
Parc Bellerive riverfront promenade, CP Rail Yard & intermodal container freight trains,
Quai Bellerive wharf, moored 195m ocean bulk carrier ship, and 100% continuous building/street
coverage across `X=[450..1400], Y=[1150..2480]`).
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_MTL_OLY_0002 import main

if __name__ == "__main__":
    main()
