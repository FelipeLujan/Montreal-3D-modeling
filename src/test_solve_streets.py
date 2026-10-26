import sys
from pathlib import Path
sys.path.append(str(Path(".").resolve()))

from src.fasttrack_unified_solve import setup_pbr_materials, reconstruct_osm_street_network, resolve_ground_and_plazas, save_export_and_render
from src.audit_zfighting_headless import MontrealZFightingAuditor
import bpy

print("=== RUNNING FASTTRACK TEST ===")
materials = setup_pbr_materials()
reconstruct_osm_street_network(materials)
resolve_ground_and_plazas()

# Now audit Criterion 4 and Criterion 2
auditor = MontrealZFightingAuditor()
c4 = auditor.audit_criterion_4_street_completeness()
print("Criterion 4 result:", c4["passed"], c4["summary"])
c2 = auditor.audit_criterion_2_ground_zfighting()
print("Criterion 2 result:", c2["passed"], c2["conflict_count"])
