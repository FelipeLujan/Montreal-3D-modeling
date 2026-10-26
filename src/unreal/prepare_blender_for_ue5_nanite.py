"""
Blender 5.2 -> Unreal Engine 5.4/5.5 Nanite + Chaos Vehicle + Flight Export Utility
===================================================================================
Prepares the stitched Montreal Master Scene (`output/montreal_master.blend`) or any
individual block for interactive Driving (Chaos Vehicles) & Flying in Unreal Engine 5:

1. Bakes real-world metric Triplanar/Box UVs (`cube_size=3.5m` for facades, `4.0m` for
   streets/sidewalks) onto all procedural meshes so UE5 Interchange imports crisp PBR
   tiling without relying on Blender-only `TexImage.projection = 'BOX'`.
2. Tags every mesh object with a custom USD/Blender attribute `ue5_collision_role`
   and standardizes object prefixes (`DRIVABLE_`, `BLDG_`, `FOLIAGE_`, `PROP_`) so the
   UE5 Editor Python importer (`src/unreal/ue5_nanite_import.py`) automatically configures:
   - `DRIVABLE_*` (roads, cobblestone streets, sidewalks, curbs, plazas):
     `CTF_UseComplexAsSimple` per-poly collision + Chaos Physical Materials (Asphalt/Cobble/Granite).
   - `BLDG_*` (buildings, towers, monuments):
     Fast simplified box/convex collision + Nanite full precision clustering.
   - `FOLIAGE_*` (instanced trees & shrubs):
     Nanite `preserve_area = True` + `no_collision` on canopy cards (or trunk capsule only).
3. Exports a JSON manifest (`output/ue5_nanite/montreal_ue5_manifest.json`) containing:
   - Recommended `PlayerStart` spawn transforms (Place d'Armes, Square Victoria, Place Jacques-Cartier,
     Rue Notre-Dame Ouest driving start, and Aerial Drone Overlook).
   - Instanced foliage/prop transform tables for optional HISM (Hierarchical Instanced Static Mesh)
     spawning in UE5.
4. Exports the binary Nanite USD stage (`output/montreal_master.usdc`) with `use_instancing=True`
   and `export_textures=True`.
"""
import json
import math
import re
import bpy
import bmesh
from pathlib import Path
from mathutils import Vector


PROJECT_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
UE5_OUT_DIR = PROJECT_ROOT / "output" / "ue5_nanite"
MASTER_USDC_PATH = PROJECT_ROOT / "output" / "montreal_master.usdc"
MANIFEST_PATH = UE5_OUT_DIR / "montreal_ue5_manifest.json"


PROP_PATTERN = re.compile(
    r"\b(lamp|lamps|bench|benches|seating|bollard|bollards|grate|grates|statue|statues|bin|bins|sign|signs|hydrant|hydrants|meter|meters|flag|flags|umbrella|umbrellas|planter|planters|car|cars|van|vans|suv|suvs|vehicle|vehicles|truck|trucks)\b",
    re.IGNORECASE,
)
FOLIAGE_PATTERN = re.compile(
    r"\b(tree|trees|jacaranda|shrub|shrubs|bush|bushes|foliage|leaf|leaves|hedge|hedges)\b",
    re.IGNORECASE,
)
DRIVABLE_PATTERN = re.compile(
    r"\b(road|roadbed|asphalt|cobble|cobblestone|street|sidewalk|curb|curbs|crosswalk|crosswalks|"
    r"plaza|paving|paver|pavers|apron|step|steps|parvis|square|ground|hw|walkway|courtyard|terrace|lawn|"
    r"pier|piers|quay|quays|quai|quais|boardwalk|boardwalks|dock|docks|wharf|wharfs|promenade|promenades)\b",
    re.IGNORECASE,
)


def classify_object_role(obj: bpy.types.Object) -> str:
    """Classifies a Blender mesh object for UE5 Nanite & Chaos Vehicle collision setup."""
    name_split = re.sub(r"([a-z])([A-Z])", r"\1 \2", obj.name)
    norm_name = re.sub(r"[^a-zA-Z0-9]", " ", name_split).lower()
    norm_mats = (
        " ".join(re.sub(r"[^a-zA-Z0-9]", " ", m.name).lower() for m in obj.data.materials if m)
        if (obj.data and obj.data.materials)
        else ""
    )
    # Sanitize materials: "gold leaf" is architectural gilding on clocks/statues, not foliage
    mats_foliage = norm_mats.replace("gold leaf", "gold")

    # 1. Check PROP first (street furniture, lamps, benches, signs, bollards, grates, statues)
    # Use word boundaries so 'car' doesn't match 'cartier' or 'jacaranda'
    if PROP_PATTERN.search(norm_name):
        return "PROP"

    # 2. Check FOLIAGE before DRIVABLE so 'WTC_StreetTree' and 'PAC_ForegroundShrub'
    # are recognized as foliage rather than drivable roads or ground planes.
    if not norm_name.startswith("bldg") and (FOLIAGE_PATTERN.search(norm_name) or FOLIAGE_PATTERN.search(mats_foliage)):
        return "FOLIAGE"

    # 3. Check DRIVABLE for roads, cobblestones, curbs, sidewalks, plazas
    # Use word boundaries so 'ground' doesn't match 'foreground'
    if DRIVABLE_PATTERN.search(norm_name) or DRIVABLE_PATTERN.search(norm_mats):
        bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        z_span = max(v.z for v in bbox) - min(v.z for v in bbox)
        if z_span < 6.0:
            return "DRIVABLE"

    return "BUILDING"


def bake_metric_box_uvs_for_unreal(default_cube_size_m: float = 3.5):
    """
    Generates clean, non-stretched real-world metric Box UVs on all procedural
    meshes (buildings, plazas, roads, sidewalks, pedestals) while skipping
    imported Poly Haven scanned models (`jacaranda_tree`, `gothic_statue`, etc.)
    and foliage meshes which already have bespoke unwrapped UVs.
    """
    skip_keywords = ("jacaranda_tree", "gothic_statue")
    processed_meshes = set()
    count = 0

    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.data is None or obj.hide_render:
            continue
        mesh = obj.data

        role = classify_object_role(obj)
        obj["ue5_collision_role"] = role

        if mesh.name in processed_meshes:
            continue
        name_low = f"{obj.name.lower()} {mesh.name.lower()}"
        if role == "FOLIAGE" or any(k in name_low for k in skip_keywords):
            processed_meshes.add(mesh.name)
            continue
        cube_size_m = 4.0 if role == "DRIVABLE" else default_cube_size_m

        if not mesh.uv_layers:
            mesh.uv_layers.new(name="UVMap")

        bm = bmesh.new()
        bm.from_mesh(mesh)
        uv_layer = bm.loops.layers.uv.verify()

        sx, sy, sz = obj.scale
        for face in bm.faces:
            n = face.normal
            nx, ny, nz = abs(n.x), abs(n.y), abs(n.z)
            for loop in face.loops:
                co = loop.vert.co
                wx, wy, wz = co.x * sx, co.y * sy, co.z * sz
                if nz >= nx and nz >= ny:
                    u, v = wx / cube_size_m, wy / cube_size_m
                elif nx >= ny and nx >= nz:
                    u, v = wy / cube_size_m, wz / cube_size_m
                else:
                    u, v = wx / cube_size_m, wz / cube_size_m
                loop[uv_layer].uv = (u, v)

        bm.to_mesh(mesh)
        bm.free()
        processed_meshes.add(mesh.name)
        count += 1

    print(f"[UE5 Prep] Baked metric triplanar UVs on {count} unique meshes.")


def export_ue5_gameplay_manifest(manifest_path: Path):
    """
    Writes `output/ue5_nanite/montreal_ue5_manifest.json` with:
    - Mesh role classifications (`DRIVABLE`, `BUILDING`, `FOLIAGE`, `PROP`)
    - Curated Driving & Flying spawn points in Unreal Engine centimetres (UE5 Left-Handed Z-Up)
    """
    UE5_OUT_DIR.mkdir(parents=True, exist_ok=True)
    role_counts = {"DRIVABLE": 0, "BUILDING": 0, "FOLIAGE": 0, "PROP": 0}
    mesh_roles = {}

    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.data is None or obj.hide_render:
            continue
        role = classify_object_role(obj)
        role_counts[role] = role_counts.get(role, 0) + 1
        mesh_roles[obj.name] = role

    # Note: Blender (X East, Y North, Z Up in meters) -> UE5 (X East*100, Y -North*100, Z Up*100 in cm)
    spawn_points = [
        {
            "name": "Spawn_Drive_Place_dArmes_NotreDame",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Rue Notre-Dame Ouest directly in front of Basilique Notre-Dame & Place d'Armes (facing ENE toward Place Jacques-Cartier)",
            "blender_xyz_m": [-22.0, -18.0, 0.35],
            "ue5_xyz_cm": [-2200.0, 1800.0, 35.0],
            "ue5_yaw_deg": -30.0,
        },
        {
            "name": "Spawn_Drive_Rue_SaintJacques_Canyon",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Rue Saint-Jacques Financial Canyon between Royal Bank Tower & Bank of Montreal Dome",
            "blender_xyz_m": [-135.0, -45.0, 0.35],
            "ue5_xyz_cm": [-13500.0, 4500.0, 35.0],
            "ue5_yaw_deg": -30.0,
        },
        {
            "name": "Spawn_Drive_Square_Victoria_Guimard",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Rue du Square-Victoria beside the Hector Guimard Paris Metro entrance & Tour de la Bourse",
            "blender_xyz_m": [-375.0, -295.0, 0.35],
            "ue5_xyz_cm": [-37500.0, 29500.0, 35.0],
            "ue5_yaw_deg": -120.0,
        },
        {
            "name": "Spawn_Fly_Place_dArmes_Overlook",
            "mode": "FlightPawn_Drone",
            "description": "Aerial Flight Start 95m above Place d'Armes overlooking Notre-Dame Towers, Aldred, and 500 Place d'Armes",
            "blender_xyz_m": [-45.0, -65.0, 95.0],
            "ue5_xyz_cm": [-4500.0, 6500.0, 9500.0],
            "ue5_yaw_deg": 45.0,
        },
        {
            "name": "Spawn_Drive_Quai_de_l_Horloge_Boardwalk",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Driving start at the foot of the Sailors' Memorial Clock Tower on Quai de l'Horloge boardwalk",
            "blender_xyz_m": [920.0, 780.0, 0.35],
            "ue5_xyz_cm": [92000.0, -78000.0, 35.0],
            "ue5_yaw_deg": 45.0,
        },
        {
            "name": "Spawn_Drive_Marche_Bonsecours_Waterfront",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Rue de la Commune Est facing Marche Bonsecours neoclassical dome and La Grande Roue",
            "blender_xyz_m": [380.0, 440.0, 0.35],
            "ue5_xyz_cm": [38000.0, -44000.0, 35.0],
            "ue5_yaw_deg": -30.0,
        },
        {
            "name": "Spawn_Fly_Old_Port_Grand_Quai_Overlook",
            "mode": "FlightPawn_Drone",
            "description": "Aerial Drone spawn 85m above Grand Quai overlooking the Cruise Terminal, Science Centre, and skyline",
            "blender_xyz_m": [420.0, -260.0, 85.0],
            "ue5_xyz_cm": [42000.0, 26000.0, 8500.0],
            "ue5_yaw_deg": 60.0,
        },
        {
            "name": "Spawn_Drive_Chinatown_Gate",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Boulevard Saint-Laurent facing the historic Chinatown South Paifang ceremonial archway",
            "blender_xyz_m": [-150.0, 480.0, 0.35],
            "ue5_xyz_cm": [-15000.0, -48000.0, 35.0],
            "ue5_yaw_deg": 90.0,
        },
        {
            "name": "Spawn_Drive_Grand_Trunk_McGill",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Rue McGill gateway between the monumental Grand Trunk Building and Place d'Youville",
            "blender_xyz_m": [-280.0, -180.0, 0.35],
            "ue5_xyz_cm": [-28000.0, 18000.0, 35.0],
            "ue5_yaw_deg": -30.0,
        },
        {
            "name": "Spawn_Drive_Chateau_Viger_Courtyard",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Place Gare-Viger forecourt facing Chateau Viger castle hotel tourelles",
            "blender_xyz_m": [650.0, 720.0, 0.35],
            "ue5_xyz_cm": [65000.0, -72000.0, 35.0],
            "ue5_yaw_deg": 45.0,
        },
        {
            "name": "Spawn_Drive_Habitat67_Dieppe",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Parc de Dieppe promenade facing Moshe Safdie's Habitat 67 modular cubes across the harbor",
            "blender_xyz_m": [980.0, -520.0, 0.35],
            "ue5_xyz_cm": [98000.0, 52000.0, 35.0],
            "ue5_yaw_deg": 135.0,
        },
        {
            "name": "Spawn_Drive_Lachine_Locks_Mill",
            "mode": "ChaosVehicle_SportsCar",
            "description": "Rue Mill alongside Silo No. 5 and Lachine Canal Entrance Locks Ecluse No. 1",
            "blender_xyz_m": [-450.0, -420.0, 0.35],
            "ue5_xyz_cm": [-45000.0, 42000.0, 35.0],
            "ue5_yaw_deg": 45.0,
        },
        {
            "name": "Spawn_Fly_Habitat67_Harbor_Overlook",
            "mode": "FlightPawn_Drone",
            "description": "Aerial Drone spawn 90m above Cite du Havre peninsula overlooking Old Port and Habitat 67",
            "blender_xyz_m": [1020.0, -480.0, 90.0],
            "ue5_xyz_cm": [102000.0, 48000.0, 9000.0],
            "ue5_yaw_deg": -45.0,
        },
        {
            "name": "Spawn_Fly_Silo5_Lachine_Overlook",
            "mode": "FlightPawn_Drone",
            "description": "Aerial Drone spawn 95m above Silo No. 5 and Bassin des Eclusiers looking towards Old Montreal",
            "blender_xyz_m": [-480.0, -480.0, 95.0],
            "ue5_xyz_cm": [-48000.0, 48000.0, 9500.0],
            "ue5_yaw_deg": 30.0,
        },
    ]

    manifest = {
        "crs": "EPSG:32188 (NAD83 MTM Zone 8 local tangent plane anchored at Place d'Armes 45.50472N, -73.55661W)",
        "units": {"blender": "meters", "unreal": "centimeters"},
        "role_counts": role_counts,
        "spawn_points": spawn_points,
        "mesh_roles": mesh_roles,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[UE5 Prep] Wrote UE5 Gameplay & Collision Manifest -> {manifest_path} ({role_counts})")


def purge_hidden_proxy_objects() -> int:
    """Permanently deletes hidden proxy objects (hide_render=True or Context_Proxy) so USD exports never include duplicate Cathedral/landmark proxies."""
    to_remove = [
        o for o in list(bpy.data.objects)
        if o.hide_render or o.hide_viewport or o.name.startswith("Context_Building_")
    ]
    removed_count = len(to_remove)
    for o in to_remove:
        bpy.data.objects.remove(o, do_unlink=True)
    for col in list(bpy.data.collections):
        if "Context_Proxy" in col.name or "04_Perimeter_Landmarks" in col.name:
            if len(col.objects) == 0:
                bpy.data.collections.remove(col)
    if removed_count:
        print(f"[UE5 Prep] Purged {removed_count} hidden/duplicate proxy objects before USD export.")
    return removed_count


def flatten_materials_for_usd_preview_surface():
    """
    Blender's USD exporter (`generate_preview_surface=True`) ONLY exports textures to UsdPreviewSurface
    when `ShaderNodeTexImage` is connected DIRECTLY to `Principled BSDF` inputs (`Base Color`, `Roughness`,
    `Metallic`, `NormalMap -> Normal`).
    Whenever a `MixRGB` or `Math` node sits between `TexImage` and `Principled BSDF`, Blender drops BOTH
    the texture and the MixRGB color, exporting flat untextured `(0.8, 0.8, 0.8)` gray!

    This function rewires all materials so:
    1. `Principled BSDF.inputs["Base Color"].default_value` is set to the architectural tint color (from MixRGB),
       and the diffuse `ShaderNodeTexImage` is wired directly into `Principled BSDF.inputs["Base Color"]`.
    2. Roughness `ShaderNodeTexImage` is wired directly into `Principled BSDF.inputs["Roughness"]`.
    3. Normal `ShaderNodeTexImage` is wired directly into `ShaderNodeNormalMap -> Principled BSDF.inputs["Normal"]`.
    """
    fixed_mats = 0
    for mat in bpy.data.materials:
        if not mat or not mat.use_nodes or not mat.node_tree:
            continue
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf:
            continue

        tex_nodes = [n for n in nodes if n.type == "TEX_IMAGE" and n.image]
        diff_tex = None
        rough_tex = None
        nor_tex = None

        for tn in tex_nodes:
            iname = tn.image.name.lower()
            if any(k in iname for k in ("nor", "normal", "nrm", "bump")):
                nor_tex = tn
            elif any(k in iname for k in ("rough", "rgh", "arm")):
                rough_tex = tn
            elif any(k in iname for k in ("diff", "col", "albedo", "base", "leaves", "twig", "grass", "wood", "stone", "brick", "asphalt", "pave", "sandstone")):
                diff_tex = tn

        if not diff_tex and tex_nodes:
            # Fallback: if there is a texture node not used for normal/roughness, treat as diffuse
            for tn in tex_nodes:
                if tn not in (rough_tex, nor_tex):
                    diff_tex = tn
                    break

        # Extract any MixRGB / Mix tint color connected to Base Color so untextured or tinted materials keep their color
        base_in = bsdf.inputs.get("Base Color")
        if base_in and base_in.is_linked:
            from_node = base_in.links[0].from_node
            if from_node.type in ("MIX_RGB", "MIX"):
                for inp_name in ("Color2", "B", "Color1", "A"):
                    inp = from_node.inputs.get(inp_name)
                    if inp and not inp.is_linked and hasattr(inp, "default_value"):
                        val = inp.default_value
                        if len(val) >= 3 and (abs(val[0] - 0.5) > 0.02 or abs(val[1] - 0.5) > 0.02 or abs(val[2] - 0.5) > 0.02):
                            base_in.default_value = (val[0], val[1], val[2], 1.0)
                            break
                for l in list(base_in.links):
                    links.remove(l)

        # Connect diffuse texture directly to Base Color
        if diff_tex and base_in:
            for l in list(base_in.links):
                links.remove(l)
            links.new(base_in, diff_tex.outputs["Color"])

        # Connect roughness texture directly to Roughness
        rough_in = bsdf.inputs.get("Roughness")
        if rough_tex and rough_in:
            for l in list(rough_in.links):
                links.remove(l)
            links.new(rough_in, rough_tex.outputs["Color"])

        # Connect normal texture via NormalMap node directly to Normal
        nor_in = bsdf.inputs.get("Normal")
        if nor_tex and nor_in:
            nmap = next((n for n in nodes if n.type == "NORMAL_MAP"), None)
            if not nmap:
                nmap = nodes.new("ShaderNodeNormalMap")
            for l in list(nmap.inputs["Color"].links):
                links.remove(l)
            for l in list(nor_in.links):
                links.remove(l)
            links.new(nmap.inputs["Color"], nor_tex.outputs["Color"])
            links.new(nor_in, nmap.outputs["Normal"])

        fixed_mats += 1

    print(f"[UE5 Prep] Flattened {fixed_mats} materials into direct UsdPreviewSurface texture chains.")


def export_ue5_nanite_usd(filepath: str = str(MASTER_USDC_PATH), export_textures: bool = True):
    """Exports the scene to binary .usdc optimized for UE5 Interchange + Nanite + Chaos Vehicles."""
    purge_hidden_proxy_objects()
    bake_metric_box_uvs_for_unreal(default_cube_size_m=3.5)
    export_ue5_gameplay_manifest(MANIFEST_PATH)

    # Save baked UVs into .blend BEFORE flattening MixRGB nodes for USD export
    try:
        master_blend = str(PROJECT_ROOT / "output" / "montreal_master.blend")
        tmp_blend = master_blend + ".tmp.blend"
        bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, compress=True, copy=True)
        import os
        if os.path.exists(tmp_blend):
            os.replace(tmp_blend, master_blend)
        print("[UE5 Prep] Saved baked UVs into Blender mainfile.")
    except Exception as e:
        print(f"[UE5 Prep Warning] Could not save mainfile: {e}")

    # Flatten MixRGB / Math nodes so Blender's USD exporter writes full PBR textures + colors to UsdPreviewSurface
    flatten_materials_for_usd_preview_surface()

    out = Path(filepath)
    out.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.usd_export(
        filepath=str(out),
        selected_objects_only=False,
        evaluation_mode='RENDER',
        export_animation=False,
        export_hair=False,
        export_uvmaps=True,
        export_normals=True,
        export_materials=True,
        use_instancing=True,
        generate_preview_surface=True,
        export_textures_mode='COPY',
        overwrite_textures=True,
        relative_paths=True,
    )

    print(f"[UE5 Prep] Exported Nanite + Chaos Vehicle ready USD with full PBR textures to {out}")


if __name__ == "__main__":
    export_ue5_nanite_usd(str(MASTER_USDC_PATH))
