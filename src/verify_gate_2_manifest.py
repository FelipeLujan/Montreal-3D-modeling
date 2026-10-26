import json
from pathlib import Path

manifest_path = Path("output/ue5_nanite/montreal_ue5_manifest.json")
if not manifest_path.exists():
    print("Manifest does not exist!")
    exit(1)

with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

print("CRS:", manifest.get("crs"))
print("Units:", manifest.get("units"))
role_counts = manifest.get("role_counts", {})
print("Role counts:", role_counts)

mesh_roles = manifest.get("mesh_roles", {})
print("Total mesh roles listed:", len(mesh_roles))

# Breakdown
by_role = {}
for name, role in mesh_roles.items():
    by_role.setdefault(role, []).append(name)

for role, items in by_role.items():
    print(f"Role {role}: {len(items)} items")
    print(f"  Sample {role} meshes: {items[:5]}")

print("\nSpawn points:")
for sp in manifest.get("spawn_points", []):
    print(f"  {sp['name']}: {sp['mode']} at Blender {sp['blender_xyz_m']} -> UE5 {sp['ue5_xyz_cm']}")
