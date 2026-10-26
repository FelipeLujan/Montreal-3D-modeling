#!/usr/bin/env python3
"""
build_MTL_OLY_0008.py
=====================
Builds and refines `MTL-OLY-0008` (Hochelaga Heritage District, Rue Sainte-Catherine Est,
Rue Ontario Est, Rue Moreau & Rue Davidson, `X=[-650..580], Y=[2950..3950]`) by executing
`src.build_corridor_superblock.build_superblock("MTL-OLY-0008")` followed by the bespoke
BMesh architectural & streetscape refinement in `src.blocks.refine_mtl_oly_0008`.
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
REPO_ROOT = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.build_corridor_superblock import build_superblock
from src.blocks.refine_mtl_oly_0008 import main as refine_main


if __name__ == "__main__":
    build_superblock("MTL-OLY-0008")
    refine_main()
