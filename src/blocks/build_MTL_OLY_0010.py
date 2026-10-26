#!/usr/bin/env python3
"""
Build MTL-OLY-0010 (Le Village olympique — Twin 19-Story Stepped Brutalist Pyramids,
Rue Sherbrooke Est, Boulevard Viau, Stade Saputo & Parc Maisonneuve)
====================================================================================
Entry-point wrapper that builds the superblock fabric and executes `refine_mtl_oly_0010.py`.
"""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
REPO_ROOT = SRC_DIR.parent
for p in (str(SCRIPT_DIR), str(SRC_DIR), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from build_corridor_superblock import build_superblock
from refine_mtl_oly_0010 import refine_superblock


def main():
    blend_out = REPO_ROOT / "output" / "blocks" / "MTL-OLY-0010.blend"
    if not blend_out.exists():
        build_superblock("MTL-OLY-0010")
    refine_superblock()


if __name__ == "__main__":
    main()
