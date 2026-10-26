"""
Audit script verifying UE5 Nanite object role classification integrity in
output/ue5_nanite/montreal_ue5_manifest.json.

Asserts:
1. role_counts['FOLIAGE'] >= 400 (genuine foliage population, no regex boundary failure).
2. 0 roadbeds, sidewalks, curbs, or buildings misclassified into FOLIAGE.
3. 0 trees, shrubs, or foliage meshes misclassified into DRIVABLE or BUILDING.
4. Roadbed_Place_Jacques_Cartier is classified as DRIVABLE (no substring collision on 'car').
5. WTC_StreetTree_00 is classified as FOLIAGE (no drivable collision on 'street').
"""
import json
import re
import sys
from pathlib import Path

MANIFEST_PATH = Path("output/ue5_nanite/montreal_ue5_manifest.json")


def audit_manifest():
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest file not found at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    role_counts = manifest.get("role_counts", {})
    mesh_roles = manifest.get("mesh_roles", {})

    print(f"=== UE5 Nanite Classification Manifest Audit ===")
    print(f"Total Meshes: {len(mesh_roles)}")
    print(f"Role Counts: {role_counts}")

    foliage_count = role_counts.get("FOLIAGE", 0)
    print(f"\n1. Foliage Population Check: {foliage_count} meshes")
    assert foliage_count >= 400, (
        f"CRITICAL DEFECT: Foliage count is {foliage_count} < 400! "
        f"Underscore regex word boundary or classification failure detected."
    )
    print(f"   PASS: Foliage count {foliage_count} >= 400.")

    # 2. Check for false foliage (roadbeds, sidewalks, curbs, buildings in FOLIAGE)
    print("\n2. False Foliage Check (roadbeds, sidewalks, curbs, buildings in FOLIAGE):")
    non_foliage_keywords = ("road", "roadbed", "sidewalk", "curb", "bldg", "building", "facade", "roof")
    foliage_pattern = re.compile(
        r"\b(tree|trees|jacaranda|shrub|shrubs|bush|bushes|foliage|leaf|leaves|hedge|hedges)\b",
        re.IGNORECASE,
    )

    false_foliage = []
    for name, role in mesh_roles.items():
        if role == "FOLIAGE":
            name_clean = re.sub(r"[^a-zA-Z0-9]", " ", re.sub(r"([a-z])([A-Z])", r"\1 \2", name)).lower()
            tokens = set(name_clean.split())
            if any(k in tokens or k in name.lower() for k in non_foliage_keywords):
                false_foliage.append(f"{name} (matched non-foliage keyword)")
            elif not foliage_pattern.search(name_clean):
                false_foliage.append(f"{name} (missing foliage keywords)")

    print(f"   False foliage count: {len(false_foliage)}")
    if false_foliage:
        for m in false_foliage[:10]:
            print(f"     FAIL: {m}")
    assert len(false_foliage) == 0, f"CRITICAL DEFECT: Found {len(false_foliage)} false foliage meshes: {false_foliage[:5]}"
    print("   PASS: 0 false foliage meshes.")

    # 3. Check for misclassified foliage (trees or shrubs in DRIVABLE or BUILDING)
    print("\n3. Misclassified Foliage Check (trees or shrubs in DRIVABLE or BUILDING):")
    tree_shrub_pattern = re.compile(
        r"\b(tree|trees|jacaranda|shrub|shrubs|bush|bushes)\b",
        re.IGNORECASE,
    )
    misclassified_drivable = []
    misclassified_building = []

    for name, role in mesh_roles.items():
        name_clean = re.sub(r"[^a-zA-Z0-9]", " ", re.sub(r"([a-z])([A-Z])", r"\1 \2", name)).lower()
        if "grate" in name_clean:
            continue
        if tree_shrub_pattern.search(name_clean):
            if role == "DRIVABLE":
                misclassified_drivable.append(name)
            elif role == "BUILDING":
                misclassified_building.append(name)

    print(f"   Trees/shrubs in DRIVABLE: {len(misclassified_drivable)}")
    if misclassified_drivable:
        for m in misclassified_drivable[:10]:
            print(f"     FAIL: {m}")
    assert len(misclassified_drivable) == 0, (
        f"CRITICAL DEFECT: Found {len(misclassified_drivable)} trees/shrubs in DRIVABLE: {misclassified_drivable[:5]}"
    )
    print("   PASS: 0 trees/shrubs in DRIVABLE.")

    print(f"   Trees/shrubs in BUILDING: {len(misclassified_building)}")
    if misclassified_building:
        for m in misclassified_building[:10]:
            print(f"     FAIL: {m}")
    assert len(misclassified_building) == 0, (
        f"CRITICAL DEFECT: Found {len(misclassified_building)} trees/shrubs in BUILDING: {misclassified_building[:5]}"
    )
    print("   PASS: 0 trees/shrubs in BUILDING.")

    # 4. Check specific sentinel objects
    print("\n4. Sentinel Object Role Checks:")
    cartier_role = mesh_roles.get("Roadbed_Place_Jacques_Cartier")
    print(f"   Roadbed_Place_Jacques_Cartier role: {cartier_role}")
    assert cartier_role == "DRIVABLE", (
        f"CRITICAL DEFECT: Roadbed_Place_Jacques_Cartier role is '{cartier_role}', expected 'DRIVABLE'!"
    )
    print("   PASS: Roadbed_Place_Jacques_Cartier is DRIVABLE.")

    wtc_tree_role = mesh_roles.get("WTC_StreetTree_00")
    print(f"   WTC_StreetTree_00 role: {wtc_tree_role}")
    assert wtc_tree_role == "FOLIAGE", (
        f"CRITICAL DEFECT: WTC_StreetTree_00 role is '{wtc_tree_role}', expected 'FOLIAGE'!"
    )
    print("   PASS: WTC_StreetTree_00 is FOLIAGE.")

    jacaranda_role = mesh_roles.get("Block_MTL-VM-0012_Owned_jacaranda_tree_branches")
    print(f"   Block_MTL-VM-0012_Owned_jacaranda_tree_branches role: {jacaranda_role}")
    assert jacaranda_role == "FOLIAGE", (
        f"CRITICAL DEFECT: Block_MTL-VM-0012_Owned_jacaranda_tree_branches role is '{jacaranda_role}', expected 'FOLIAGE'!"
    )
    print("   PASS: Block_MTL-VM-0012_Owned_jacaranda_tree_branches is FOLIAGE.")

    shrub_role = mesh_roles.get("PAC_ForegroundShrub_00")
    print(f"   PAC_ForegroundShrub_00 role: {shrub_role}")
    assert shrub_role == "FOLIAGE", (
        f"CRITICAL DEFECT: PAC_ForegroundShrub_00 role is '{shrub_role}', expected 'FOLIAGE'!"
    )
    print("   PASS: PAC_ForegroundShrub_00 is FOLIAGE.")

    print("\n=== ALL UE5 NANITE CLASSIFICATION AUDITS PASSED ===")


if __name__ == "__main__":
    audit_manifest()
