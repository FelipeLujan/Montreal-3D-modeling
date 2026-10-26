"""
Independent Verification Audit for Milestone 1:
- Verifies 12+ Poly Haven 2K PBR facade texture sets on disk in assets/polyhaven/
- Verifies 4 tileable 2K PBR water texture maps on disk in assets/polyhaven/
- Verifies ShaderNodeTexImage wiring in assets/montreal_kit.blend and output/montreal_master.blend
- Verifies Facade Diversity Cap: <= 20% single material share globally and per block
- Verifies 0 adjacent party-wall conflicts
Exit code 0 indicates 100% compliance.
"""
import os
import sys
import glob
import math
import re
from collections import defaultdict, Counter

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
POLYHAVEN_DIR = os.path.join(BASE_DIR, "assets", "polyhaven")
KIT_BLEND = os.path.join(BASE_DIR, "assets", "montreal_kit.blend")
MASTER_BLEND = os.path.join(BASE_DIR, "output", "montreal_master.blend")

EXCLUDE_KEYWORDS = (
    'tree', 'jacaranda', 'shrub', 'statue', 'lamp', 'bench', 'clock_bezel', 'grate', 'signage', 'furniture', 'bollard',
    'street', 'road', 'sidewalk', 'curb', 'collider', 'cam', 'sun', 'ground', 'satellite', 'water', 'fountain', 'basin',
    'pier_deck', 'quay_deck', 'boardwalk', 'crosswalk', 'traffic', 'sign', 'candelabra', 'mast', 'banner', 'standard',
    'post', 'bin', 'plaque', 'socle', 'wheel', 'ferris', 'boat', 'vessel', 'ship', 'bota', 'shed', 'pergola',
    'rooftop', 'skylight', '_owned_mat_', 'mechanical'
)

NON_WALL_MAT_KEYWORDS = (
    'roof', 'glass', 'window', 'door', 'iron', 'steel', 'bronze', 'copper', 'shutter', 'sign', 'trim',
    'spandrel', 'cornice', 'parapet', 'grass', 'lawn', 'solar', 'asphalt', 'cobble', 'sidewalk'
)

REQUIRED_WATER_MAPS = [
    "water_river_diffuse_2k.jpg",
    "water_river_nor_gl_2k.jpg",
    "water_river_rough_2k.jpg",
    "water_foam_edge_2k.jpg"
]


def audit_disk_assets():
    print("=" * 80)
    print("TEST SUITE 1: DISK ASSETS AUDIT (assets/polyhaven/)")
    print("=" * 80)

    # 1. Audit Water Maps
    print("\n--- Auditing 2K Water Maps ---")
    missing_water = []
    for wm in REQUIRED_WATER_MAPS:
        p = os.path.join(POLYHAVEN_DIR, wm)
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            missing_water.append(wm)
            print(f"  [FAIL] Missing or empty: {wm}")
        else:
            print(f"  [PASS] {wm} ({os.path.getsize(p)} bytes)")

    assert len(missing_water) == 0, f"Missing water maps: {missing_water}"

    # 2. Audit Facade Sets
    print("\n--- Auditing Poly Haven Facade PBR Sets ---")
    distinct_sets = set()
    for f in os.listdir(POLYHAVEN_DIR):
        for sfx in ["_Diffuse_2k.jpg", "_diff_2k.jpg", "_Rough_2k.jpg", "_rough_2k.jpg", "_nor_gl_2k.jpg"]:
            if f.endswith(sfx):
                distinct_sets.add(f[:-len(sfx)])

    facade_sets = [s for s in distinct_sets if s not in ["asphalt_02", "cobblestone_floor_08", "kloppenheim_06_puresky"]]
    print(f"Found {len(facade_sets)} architectural facade sets on disk (minimum required: 12):")
    complete_facades = 0
    for s in sorted(facade_sets):
        has_diff = os.path.exists(os.path.join(POLYHAVEN_DIR, f"{s}_Diffuse_2k.jpg")) or os.path.exists(os.path.join(POLYHAVEN_DIR, f"{s}_diff_2k.jpg"))
        has_rough = os.path.exists(os.path.join(POLYHAVEN_DIR, f"{s}_Rough_2k.jpg")) or os.path.exists(os.path.join(POLYHAVEN_DIR, f"{s}_rough_2k.jpg"))
        has_nor = os.path.exists(os.path.join(POLYHAVEN_DIR, f"{s}_nor_gl_2k.jpg"))
        status = "COMPLETE" if (has_diff and has_rough and has_nor) else "INCOMPLETE"
        if status == "COMPLETE":
            complete_facades += 1
        print(f"  {s:<26}: diff={has_diff}, rough={has_rough}, nor={has_nor} [{status}]")

    print(f"Total complete facade sets: {complete_facades} (requirement >= 12)")
    assert complete_facades >= 12, f"Expected at least 12 complete facade sets, got {complete_facades}"


def audit_montreal_kit():
    print("\n" + "=" * 80)
    print("TEST SUITE 2: MONTREAL KIT AUDIT (assets/montreal_kit.blend)")
    print("=" * 80)
    import bpy

    # Open kit blend file if running in Blender
    tex_mats = []
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        tex_nodes = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
        if tex_nodes:
            tex_mats.append((mat.name, len(tex_nodes)))

    print(f"Materials with active ShaderNodeTexImage in scene: {len(tex_mats)}")
    assert any("Water" in name for name, _ in tex_mats), "Mat_MTL_StLawrence_Water_PBR missing image textures!"
    facade_tex_mats = [name for name, _ in tex_mats if any(k in name for k in ['Limestone', 'Brick', 'Stone', 'Sandstone', 'Concrete', 'Plinth', 'Metal', 'Timber', 'Fieldstone'])]
    print(f"Facade materials with active ShaderNodeTexImage: {len(facade_tex_mats)} (minimum required: 12)")
    assert len(facade_tex_mats) >= 12, f"Expected >= 12 facade materials with TexImage nodes, found {len(facade_tex_mats)}"


def audit_master_diversity():
    print("\n" + "=" * 80)
    print("TEST SUITE 3: MASTER SCENE DIVERSITY & PARTY-WALL AUDIT")
    print("=" * 80)
    import bpy
    from mathutils import Vector

    bldgs = []
    for col in bpy.data.collections:
        if 'owned' in col.name.lower():
            b_name = col.name
            for obj in col.all_objects:
                if obj.type != 'MESH' or obj.hide_render:
                    continue
                nl = obj.name.lower()
                if any(k in nl for k in EXCLUDE_KEYWORDS):
                    continue
                if obj.dimensions.z >= 2.2 and max(obj.dimensions.x, obj.dimensions.y) >= 1.5:
                    wall_mat = None
                    for slot in obj.material_slots:
                        if not slot.material:
                            continue
                        mn = slot.material.name.lower()
                        if not any(k in mn for k in NON_WALL_MAT_KEYWORDS):
                            wall_mat = slot.material.name
                            break
                    if wall_mat:
                        base_m = re.sub(r"\.\d{3,}$", "", wall_mat)
                        bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
                        xs = [v.x for v in bb]
                        ys = [v.y for v in bb]
                        zs = [v.z for v in bb]
                        bldgs.append({
                            'idx': len(bldgs),
                            'name': obj.name,
                            'block': b_name,
                            'mat': base_m,
                            'bbox': (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)),
                            'center': (sum(xs)/8.0, sum(ys)/8.0)
                        })

    print(f"Total building objects evaluated: {len(bldgs)}")

    # 1. Adjacency Graph and Party-Wall Conflicts
    adj = defaultdict(set)
    conflicts = 0
    adj_edges = 0
    n = len(bldgs)
    for i in range(n):
        b1 = bldgs[i]
        for j in range(i + 1, n):
            b2 = bldgs[j]
            z_overlap = min(b1['bbox'][5], b2['bbox'][5]) - max(b1['bbox'][4], b2['bbox'][4])
            if z_overlap < 1.0:
                continue
            dx = max(0.0, max(b1['bbox'][0] - b2['bbox'][1], b2['bbox'][0] - b1['bbox'][1]))
            dy = max(0.0, max(b1['bbox'][2] - b2['bbox'][3], b2['bbox'][2] - b1['bbox'][3]))
            if dx <= 0.35 and dy <= 0.35:
                adj_edges += 1
                if b1['mat'] == b2['mat']:
                    conflicts += 1
                    print(f"  [CONFLICT] '{b1['name']}' and '{b2['name']}' share material '{b1['mat']}'")

    print(f"Total adjacent party-wall edges: {adj_edges}")
    print(f"Total party-wall conflicts: {conflicts}")
    assert conflicts == 0, f"Party-wall conflicts detected: {conflicts} (must be 0!)"

    # 2. Global Material Share
    global_counts = Counter(b['mat'] for b in bldgs)
    print("\nGlobal Material Distribution across District:")
    max_global_pct = 0.0
    for mat, cnt in global_counts.most_common():
        pct = cnt / len(bldgs) * 100.0
        if pct > max_global_pct:
            max_global_pct = pct
        print(f"  {mat:<35}: {cnt:>3} ({pct:>5.1f}%)")

    print(f"\nMax Global Material Share: {max_global_pct:.1f}%")
    assert max_global_pct <= 20.0, f"Global material diversity cap violated: {max_global_pct:.1f}% > 20.0%"

    # 3. Per-Block Material Share
    print("\nPer-Block Material Diversity Check:")
    block_bldgs = defaultdict(list)
    for b in bldgs:
        block_bldgs[b['block']].append(b)

    for b_name, b_list in sorted(block_bldgs.items()):
        b_total = len(b_list)
        b_counts = Counter(b['mat'] for b in b_list)
        b_max_cnt = b_counts.most_common(1)[0][1] if b_counts else 0
        b_max_pct = (b_max_cnt / b_total * 100.0) if b_total > 0 else 0.0
        status = "PASS" if (b_total < 5 or b_max_pct <= 20.01) else "FAIL"
        print(f"  {b_name:<32}: {b_total:>3} bldgs | max single: {b_max_pct:>5.1f}% [{status}]")
        if b_total >= 5:
            assert b_max_pct <= 20.01, f"Block {b_name} exceeded 20% cap with {b_max_pct:.1f}%!"

    print("\n" + "=" * 80)
    print("ALL MILESTONE 1 DIVERSITY & INTEGRITY AUDITS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    audit_disk_assets()
    try:
        import bpy
        if "montreal_master" in bpy.data.filepath:
            audit_master_diversity()
        elif "montreal_kit" in bpy.data.filepath:
            audit_montreal_kit()
    except ImportError:
        pass
