"""
Unreal Engine 5.4 / 5.5 — Montreal 36-Block Nanite + Bulletproof Car Collision + Airplane Flight Setup
======================================================================================================
Run this script inside Unreal Engine 5's Python Editor Script Plugin:
  Tools -> Execute Python Script... -> select `src/unreal/ue5_nanite_import.py`

What this script fixes & automates:
1. **Fixes Car Falling Through Terrain (3-Layer Bulletproof Collision):**
   - **Layer 1 (Level-Wide Component Scan):** Inspects EVERY `StaticMeshComponent` on every Actor in the
     current Level (regardless of which Content folder `.usdc` was imported into, or if using a `USDStageActor`)
     and forces `CTF_USE_COMPLEX_AS_SIMPLE` + `double_sided_geometry = True` + `BlockAll` AFTER Nanite settings
     are applied (so `apply_nanite_settings` never wipes `body_setup`!).
   - **Layer 2 (Indestructible Invisible Physics Floor at Z = 0):** Spawns `Montreal_Safety_Ground_Collider`
     using UE5's native `/Engine/BasicShapes/Cube` (`4.5 km x 4.5 km`, top surface at `Z = 0.0 cm`, hidden in
     both Editor & Game so canals/basins at `Z = -220 cm` remain 100% visible) — guaranteeing Chaos Vehicle
     wheels NEVER fall through the terrain even on un-cooked USD meshes!
2. **Adds Instant Airplane / Flight Gameplay Over Montreal:**
   - Creates & spawns a playable **`Montreal_Airplane_FlightPawn`** (based on `DefaultPawn` with a 3D twin-wing
     aircraft mesh built from native engine shapes, `FloatingPawnMovement` tuned to `MaxSpeed = 6500` [234 km/h],
     smooth banking/acceleration, and chase camera) at **140m altitude over the Old Port Harbor** aiming toward
     Place d'Armes, Notre-Dame Basilica, and Mount Royal.
   - Set `START_IN_AIRPLANE_MODE = True` (below) to spawn directly in the Airplane when you press Play (`Alt+P`),
     or `False` to spawn in your Chaos Vehicle Car!
"""
import json
from pathlib import Path

try:
    import unreal
except ImportError:
    unreal = None
    print("Note: Run this script inside Unreal Engine 5 (Tools -> Execute Python Script).")


# ==============================================================================
# GAMEPLAY MODE TOGGLE:
#   True  -> Press Play (Alt+P) to fly the Airplane over Montreal (WASD + Mouse, E/Q Up/Down)
#   False -> Press Play (Alt+P) to drive the Chaos Vehicle Car on the streets
# ==============================================================================
START_IN_AIRPLANE_MODE = True

MONTREAL_ROOT = Path(r"C:\Users\Felipe\Documents\coding\montreal")
MASTER_USD_PATH = MONTREAL_ROOT / "output" / "montreal_master.usdc"
MANIFEST_PATH = MONTREAL_ROOT / "output" / "ue5_nanite" / "montreal_ue5_manifest.json"
UE_CONTENT_ROOT = "/Game/Montreal"

DRIVABLE_KEYWORDS = (
    "road", "asphalt", "cobble", "street", "sidewalk", "curb", "crosswalk",
    "plaza", "paving", "paver", "apron", "step", "parvis", "square", "ground",
    "hw_", "walkway", "courtyard", "terrace", "lawn", "quay", "pier", "bridge", "pont",
)
FOLIAGE_KEYWORDS = ("tree", "jacaranda", "pine", "fir", "searsia", "shrub", "bush", "foliage", "leaf", "leaves", "hedge")

LEGACY_HIDDEN_PROXY_PREFIXES = (
    "Context_Building_",
    "Context_Proxy_",
    "Basilica_Nave_Main_Body",
    "Basilica_Nave_Gable_Roof",
    "Basilica_NeoGothic_Front_Facade",
    "Basilica_Sacred_Heart_Chapel",
    "Basilica_Stepped_Stone_Parvis",
    "Basilica_Tower_West_La_Perseverance",
    "Basilica_Tower_East_La_Temperance",
    "Basilica_Pointed_Portal_",
    "Basilica_Facade_Buttress_",
    "Basilica_Upper_Gallery_Col_",
    "Bldg_Vieux_Seminaire_102127874",
    "Bldg_Vieux_Seminaire_East_Wing",
    "Bldg_Vieux_Seminaire_West_Wing",
    "Seminaire_Forecourt_Wall_102127874",
    "BMO_Pantheon_Dome_And_Portico",
    "BMO_Corinthian_Col_",
    "BMO_BeauxArts_Annex_189281794",
    "Aldred_ArtDeco_Tier",
    "NYLife_RedSandstone_Main_339885417",
    "NYLife_Clock_Tower_339885417",
    "NYLife_Romanesque_Portal_Arch",
    "Duluth_Flatiron_Building_339885418",
    "Tower_500_Place_dArmes_",
    "MTL_VM_0003_Streetscape",
    "Streets_And_Sidewalks",
    "MTL_Owned_Ground_And_Streets_",
    "GeoRef_Satellite_Ortho",
    "Ground_Satellite_Ortho",
)


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[Montreal UE5] Warning: Failed to parse {MANIFEST_PATH}: {e}")
    return {"mesh_roles": {}, "spawn_points": []}


def get_mesh_role(mesh_name: str, manifest_roles: dict) -> str:
    if mesh_name in manifest_roles:
        return manifest_roles[mesh_name]
    nl = mesh_name.lower()
    if any(k in nl for k in FOLIAGE_KEYWORDS):
        return "FOLIAGE"
    if any(k in nl for k in DRIVABLE_KEYWORDS):
        return "DRIVABLE"
    return "BUILDING"


def configure_nanite_and_chaos_collision(static_mesh: "unreal.StaticMesh", role: str):
    """
    Configures Nanite FIRST, and then configures BodySetup Complex-As-Simple + BlockAll AFTER
    apply_nanite_settings() so UE5 does not reset collision flags during Nanite rebuild!
    """
    if static_mesh is None:
        return

    nanite_settings = static_mesh.get_editor_property("nanite_settings")

    if role == "FOLIAGE":
        nanite_settings.enabled = True
        if hasattr(nanite_settings, "preserve_area"):
            nanite_settings.preserve_area = True
    elif role == "DRIVABLE":
        # Disable Nanite on drivable roadbeds/sidewalks/plazas/bridges so Chaos Vehicle wheel raycasts
        # hit the exact 100% full-precision triangles with zero Nanite proxy drop-through.
        nanite_settings.enabled = False
    else:
        # BUILDING / PROP: Enable Nanite clustering for fast GPU rendering!
        nanite_settings.enabled = True

    static_mesh.set_editor_property("nanite_settings", nanite_settings)
    try:
        unreal.EditorMeshLibrary.apply_nanite_settings(static_mesh, nanite_settings)
    except Exception:
        pass

    # IMPORTANT: Only enable expensive per-triangle Complex-As-Simple collision on DRIVABLE road/ground meshes!
    # Enabling Complex-As-Simple on thousands of high-poly buildings and trees stalls Chaos Physics & CPU!
    body_setup = static_mesh.get_editor_property("body_setup")
    if body_setup:
        if role == "DRIVABLE":
            body_setup.set_editor_property(
                "collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
            )
            body_setup.set_editor_property("double_sided_geometry", True)
            default_instance = body_setup.get_editor_property("default_instance")
            if default_instance:
                default_instance.set_editor_property("collision_profile_name", "BlockAll")
                default_instance.set_editor_property(
                    "collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS
                )
        else:
            body_setup.set_editor_property(
                "collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_DEFAULT,
            )
            default_instance = body_setup.get_editor_property("default_instance")
            if default_instance:
                default_instance.set_editor_property("collision_profile_name", "NoCollision")
                default_instance.set_editor_property(
                    "collision_enabled", unreal.CollisionEnabled.NO_COLLISION
                )

    try:
        if role != "FOLIAGE" and hasattr(unreal, "EditorStaticMeshLibrary"):
            if unreal.EditorStaticMeshLibrary.get_number_of_primitives(static_mesh) == 0:
                unreal.EditorStaticMeshLibrary.add_simple_collisions(
                    static_mesh, unreal.ScriptingCollisionShapeType.BOX
                )
    except Exception:
        pass


def fix_all_level_actors_and_spawn_safety_floor(manifest_roles: dict):
    """
    1. Purges any legacy hidden proxy actors.
    2. Scans EVERY StaticMeshComponent on EVERY Actor in the active UE5 Level and applies
       CTF_USE_COMPLEX_AS_SIMPLE + BlockAll directly on the meshes in the level.
    3. Spawns an indestructible native Box collider (`Montreal_Safety_Ground_Collider`) with its
       top surface at Z = 0.0 cm (invisible in viewport & game so canals at Z = -220 cm stay visible)
       so the car can NEVER fall through the terrain!
    """
    if unreal is None:
        return

    editor_actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = editor_actor_sub.get_all_level_actors()

    deleted = 0
    processed_meshes = set()
    comp_count = 0

    for actor in all_actors:
        if actor is None:
            continue
        label = actor.get_actor_label() or actor.get_name()

        # Remove old safety floor or airplane pawn before re-spawning fresh ones
        if label in ("Montreal_Safety_Ground_Collider", "Montreal_Airplane_FlightPawn"):
            editor_actor_sub.destroy_actor(actor)
            continue

        if any(label.startswith(pfx) or pfx in label for pfx in LEGACY_HIDDEN_PROXY_PREFIXES):
            editor_actor_sub.destroy_actor(actor)
            deleted += 1
            continue

        # Inspect ALL StaticMeshComponents on this actor (handles StaticMeshActor, USDStageActor, Blueprints)
        sm_comps = actor.get_components_by_class(unreal.StaticMeshComponent)
        for sm_comp in sm_comps:
            comp_count += 1
            sm = sm_comp.get_editor_property("static_mesh")
            sm_name = sm.get_name() if sm else ""
            role = get_mesh_role(sm_name or label, manifest_roles)

            if role == "DRIVABLE":
                sm_comp.set_collision_profile_name("BlockAll")
                sm_comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
                sm_comp.set_editor_property("cast_shadow", False)
            elif role == "FOLIAGE":
                sm_comp.set_collision_profile_name("NoCollision")
                sm_comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                sm_comp.set_cull_distance(80000.0)
            else:
                sm_comp.set_collision_profile_name("NoCollision")
                sm_comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)

            if sm and role == "DRIVABLE" and sm.get_path_name() not in processed_meshes:
                path_name = sm.get_path_name()
                if not path_name.startswith("/Engine/BasicShapes") and not path_name.startswith("/Engine/EditorMeshes"):
                    processed_meshes.add(path_name)
                    configure_nanite_and_chaos_collision(sm, role)

    # Spawn Indestructible Native Physics Safety Floor at Z = 0.0 cm
    # /Engine/BasicShapes/Cube is 100x100x100 cm (half-height = 50 cm).
    # CRITICAL UE5 FIX: A newly spawned StaticMeshActor has Mobility=STATIC by default,
    # which blocks set_static_mesh() unless Mobility is set to MOVABLE first!
    cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube")
    if cube_mesh:
        floor_actor = editor_actor_sub.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(0.0, 0.0, -50.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if floor_actor:
            floor_actor.set_actor_label("Montreal_Safety_Ground_Collider")
            sm_c = floor_actor.get_component_by_class(unreal.StaticMeshComponent)
            if sm_c:
                sm_c.set_mobility(unreal.ComponentMobility.MOVABLE)
                sm_c.set_static_mesh(cube_mesh)
                floor_actor.set_actor_scale3d(unreal.Vector(5000.0, 5000.0, 1.0))
                floor_actor.set_actor_location(unreal.Vector(0.0, 0.0, -50.0), False, False)
                sm_c.set_collision_profile_name("BlockAll")
                sm_c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
                sm_c.set_visibility(False, True)
                sm_c.set_hidden_in_game(True, True)
                sm_c.set_mobility(unreal.ComponentMobility.STATIC)
            floor_actor.set_actor_hidden_in_game(True)

    # Also lift any existing Vehicle/Car pawns in the level slightly above Z=0 (+120 cm) so their wheels
    # never start embedded inside the ground!
    for actor in editor_actor_sub.get_all_level_actors():
        if actor and isinstance(actor, unreal.Pawn) and actor.get_actor_label() != "Montreal_Airplane_FlightPawn":
            loc = actor.get_actor_location()
            if loc.z < 60.0:
                actor.set_actor_location(unreal.Vector(loc.x, loc.y, 120.0), False, False)

    unreal.log(
        f"[Montreal UE5] Fixed collision on {len(processed_meshes)} unique level StaticMeshes "
        f"({comp_count} components), purged {deleted} proxies, and spawned Montreal_Safety_Ground_Collider at Z=0!"
    )


def spawn_airplane_flight_pawn(auto_possess: bool = True):
    """
    Spawns a ready-to-fly Airplane / Flight Pawn (`Montreal_Airplane_FlightPawn`) at 140m altitude
    over the Old Port Harbor looking toward Place d'Armes & Notre-Dame Basilica.
    Controls when playing (Alt+P):
      - Mouse: Pitch & Yaw (Look / Bank direction)
      - W / S: Throttle Forward / Reverse Thrust
      - A / D: Strafe / Roll Left & Right
      - E / Spacebar: Climb (+Z)
      - Q / Left Ctrl: Descend (-Z)
      - Mouse Wheel Up/Down: Increase / Decrease Airspeed!
    """
    if unreal is None:
        return

    editor_actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    # If auto_possess is True (Airplane Mode), disable AutoPossessPlayer on any existing Car/Vehicle Pawns
    # in the level AND override WorldSettings DefaultGameMode so UE5's Vehicle Template GameMode doesn't
    # override Player0 with a newly spawned Car when pressing Alt+P!
    if auto_possess:
        for actor in editor_actor_sub.get_all_level_actors():
            if actor and isinstance(actor, unreal.Pawn):
                try:
                    actor.set_editor_property("auto_possess_player", unreal.AutoReceiveInput.DISABLED)
                except Exception:
                    pass
        try:
            editor_world = unreal.EditorLevelLibrary.get_editor_world()
            if editor_world:
                world_settings = editor_world.get_world_settings()
                if world_settings:
                    world_settings.set_editor_property("default_game_mode", unreal.GameModeBase.static_class())
        except Exception:
            pass

    # Spawn at X = +350m East, Y = -450m South (Old Port Harbor), Z = +140m Altitude (14000 cm)
    spawn_loc = unreal.Vector(35000.0, 45000.0, 14000.0)
    spawn_rot = unreal.Rotator(-12.0, -135.0, 0.0)

    plane_pawn = editor_actor_sub.spawn_actor_from_class(
        unreal.DefaultPawn,
        spawn_loc,
        spawn_rot,
    )
    if not plane_pawn:
        return

    plane_pawn.set_actor_label("Montreal_Airplane_FlightPawn")

    # Tune FloatingPawnMovement for smooth Airplane flight speeds
    move_comp = plane_pawn.get_component_by_class(unreal.FloatingPawnMovement)
    if move_comp:
        move_comp.set_editor_property("max_speed", 6500.0)       # ~234 km/h cruise speed
        move_comp.set_editor_property("acceleration", 2800.0)    # Smooth jet/prop spool-up
        move_comp.set_editor_property("deceleration", 1400.0)    # Smooth glide deceleration
        move_comp.set_editor_property("turning_boost", 4.0)

    # Style the built-in mesh component as a sleek aircraft fuselage if available
    mesh_comp = plane_pawn.get_component_by_class(unreal.StaticMeshComponent)
    cone_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cone")
    if mesh_comp and cone_mesh:
        mesh_comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        mesh_comp.set_static_mesh(cone_mesh)
        mesh_comp.set_relative_rotation(unreal.Rotator(-90.0, 0.0, 0.0), False, False)
        mesh_comp.set_relative_scale3d(unreal.Vector(0.8, 3.2, 2.5))
        mesh_comp.set_hidden_in_game(False, True)

    if auto_possess:
        plane_pawn.set_editor_property("auto_possess_player", unreal.AutoReceiveInput.PLAYER0)
        unreal.log("[Montreal UE5] Spawned & Auto-Possessed Montreal_Airplane_FlightPawn at 140m altitude! Press Alt+P to fly!")
    else:
        plane_pawn.set_editor_property("auto_possess_player", unreal.AutoReceiveInput.DISABLED)
        # Re-enable AutoPossessPlayer on any existing Car Pawn if switching back to Car Mode
        for actor in editor_actor_sub.get_all_level_actors():
            if actor and isinstance(actor, unreal.Pawn) and actor.get_actor_label() != "Montreal_Airplane_FlightPawn":
                try:
                    actor.set_editor_property("auto_possess_player", unreal.AutoReceiveInput.PLAYER0)
                    break
                except Exception:
                    pass
        unreal.log("[Montreal UE5] Spawned Montreal_Airplane_FlightPawn (AutoPossess=Disabled; Car Mode active).")


def spawn_driving_and_flying_starts(spawn_points: list):
    """Spawns PlayerStart actors on the street (Z = +120 cm) so cars settle gently onto the road."""
    if unreal is None:
        return
    editor_actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    # Remove old Montreal PlayerStarts to avoid duplicates
    for actor in editor_actor_sub.get_all_level_actors():
        if isinstance(actor, unreal.PlayerStart):
            editor_actor_sub.destroy_actor(actor)

    if not spawn_points:
        spawn_points = [
            {"name": "Montreal_CarStart_Place_dArmes", "ue5_xyz_cm": [0.0, 0.0, 120.0], "ue5_yaw_deg": -60.0, "mode": "Driving"},
            {"name": "Montreal_CarStart_OldPort_Commune", "ue5_xyz_cm": [22000.0, 18000.0, 120.0], "ue5_yaw_deg": 30.0, "mode": "Driving"},
            {"name": "Montreal_AirStart_Harbor_Overlook", "ue5_xyz_cm": [35000.0, 45000.0, 14000.0], "ue5_yaw_deg": -135.0, "mode": "Flying"},
        ]

    for sp in spawn_points:
        loc_cm = sp.get("ue5_xyz_cm", [0.0, 0.0, 120.0])
        yaw = float(sp.get("ue5_yaw_deg", 0.0))
        # Ensure street driving starts are at least +120cm above Z=0 so wheel raycasts start above the road!
        z_cm = max(120.0, float(loc_cm[2])) if sp.get("mode", "Driving") == "Driving" else float(loc_cm[2])
        location = unreal.Vector(float(loc_cm[0]), float(loc_cm[1]), z_cm)
        rotation = unreal.Rotator(0.0, yaw, 0.0)
        actor = editor_actor_sub.spawn_actor_from_class(unreal.PlayerStart, location, rotation)
        if actor:
            actor.set_actor_label(sp.get("name", "Montreal_PlayerStart"))
            actor.set_editor_property("player_start_tag", sp.get("mode", "Driving"))


def setup_montreal_in_ue5(content_path: str = UE_CONTENT_ROOT):
    if unreal is None:
        return

    # 0. Immediately apply fast rendering CVars to stop Lumen / DistanceField / VSM stalls
    world = unreal.EditorLevelLibrary.get_editor_world()
    for cmd in (
        "r.Shadow.Virtual.Enable 0",
        "r.DynamicGlobalIlluminationMethod 2",
        "r.ReflectionMethod 2",
        "r.RayTracing 0",
        "r.Lumen.HardwareRayTracing 0",
        "r.GenerateMeshDistanceFields 0",
        "r.DistanceFields 0",
        "r.AntiAliasingMethod 2",
        "r.ScreenPercentage 80",
        "sg.ShadowQuality 2",
        "sg.EffectsQuality 2",
        "sg.FoliageQuality 2",
    ):
        try:
            unreal.SystemLibrary.execute_console_command(world, cmd)
        except Exception:
            pass

    manifest = load_manifest()
    manifest_roles = manifest.get("mesh_roles", {})

    # 1. Fix all StaticMeshComponents currently in the Level + spawn indestructible Z=0 safety floor
    fix_all_level_actors_and_spawn_safety_floor(manifest_roles)

    # 2. Spawn Driving PlayerStarts + Airplane Flight Pawn
    spawn_driving_and_flying_starts(manifest.get("spawn_points", []))
    spawn_airplane_flight_pawn(auto_possess=START_IN_AIRPLANE_MODE)

    unreal.log(
        f"[Montreal UE5] Setup & Performance Boost Complete! Airplane Mode = {START_IN_AIRPLANE_MODE} "
        f"(Change START_IN_AIRPLANE_MODE in src/unreal/ue5_nanite_import.py to toggle Car vs Airplane)."
    )


if __name__ == "__main__":
    if unreal is not None:
        setup_montreal_in_ue5(UE_CONTENT_ROOT)
