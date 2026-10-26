#!/usr/bin/env python3
"""
Entrypoint wrapper for `MTL-OLY-0005` that delegates to `refine_mtl_oly_0005.main()`.
"""
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent.parent))

from src.blocks.refine_mtl_oly_0005 import main

if __name__ == "__main__":
    main()
