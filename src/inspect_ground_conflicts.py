import bpy
import sys
sys.path.insert(0, ".")
from src.audit_zfighting_headless import MontrealZFightingAuditor

auditor = MontrealZFightingAuditor()
auditor.verbose = True
auditor.inspect_scene_inventory()
res = auditor.audit_ground_street_sidewalk_zfighting()
