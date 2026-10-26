import sys
import os
import json
import time
import math
import unicodedata
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
polyhaven_dir = PROJECT_ROOT / "assets" / "polyhaven"

print("Checking Poly Haven assets exist:")
for fn in [
    "asphalt_02_Diffuse_2k.jpg", "asphalt_02_Rough_2k.jpg", "asphalt_02_nor_gl_2k.jpg",
    "cobblestone_floor_08_Diffuse_2k.jpg", "cobblestone_floor_08_Rough_2k.jpg", "cobblestone_floor_08_nor_gl_2k.jpg",
    "sandstone_blocks_05_Diffuse_2k.jpg", "sandstone_blocks_05_Rough_2k.jpg", "sandstone_blocks_05_nor_gl_2k.jpg"
]:
    p = polyhaven_dir / fn
    print(f"  {fn}: exists={p.exists()}")
