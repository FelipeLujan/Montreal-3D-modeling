import bpy
import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
sys.path.insert(0, str(PROJECT_ROOT))

from src.fasttrack_unified_solve import resolve_ground_and_plazas, resolve_roof_cornice_zfighting

print("=" * 80)
print("RUNNING FAST Z-FIGHTING RESOLUTION")
print("=" * 80)

t0 = time.time()
resolve_ground_and_plazas()
resolve_roof_cornice_zfighting()

# Save master blend atomically
master_blend = str(PROJECT_ROOT / "output" / "montreal_master.blend")
tmp_blend = master_blend + ".tmp.blend"
if os.path.exists(tmp_blend):
    try:
        os.remove(tmp_blend)
    except Exception:
        pass
bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
os.replace(tmp_blend, master_blend)
print(f"Saved master blend in {time.time() - t0:.2f}s!")
