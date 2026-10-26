import os
import json

usdc_path = r'output/montreal_master.usdc'
manifest_path = r'output/ue5_nanite/montreal_ue5_manifest.json'

print('=== USDC FILE CHECK ===')
if os.path.exists(usdc_path):
    size = os.path.getsize(usdc_path)
    print(f'USDC exists: {usdc_path}')
    print(f'USDC size: {size} bytes ({size / (1024**3):.2f} GB)')
    with open(usdc_path, 'rb') as f:
        header = f.read(16)
        print(f'USDC binary header: {header}')
else:
    print(f'ERROR: {usdc_path} does not exist!')

print('\n=== MANIFEST CHECK ===')
if os.path.exists(manifest_path):
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print('CRS:', data.get('crs'))
    print('Units:', data.get('units'))
    role_counts = data.get('role_counts', {})
    print('Role counts:', role_counts)
    mesh_roles = data.get('mesh_roles', {})
    print('Total tagged meshes:', len(mesh_roles))
    
    # Verify breakdown
    actual_counts = {}
    for m, r in mesh_roles.items():
        actual_counts[r] = actual_counts.get(r, 0) + 1
    print('Actual counts from mesh_roles:', actual_counts)
    assert actual_counts == role_counts, 'Mismatch between role_counts and mesh_roles!'
    
    # Check spawn points
    spawn_points = data.get('spawn_points', [])
    print(f'Total spawn points: {len(spawn_points)}')
    for i, sp in enumerate(spawn_points, 1):
        name = sp.get('name')
        mode = sp.get('mode')
        b_xyz = sp.get('blender_xyz_m')
        u_xyz = sp.get('ue5_xyz_cm')
        yaw = sp.get('ue5_yaw_deg')
        print(f"  {i}. {name}: mode={mode}, blender_xyz={b_xyz}, ue5_xyz={u_xyz}, yaw={yaw}")
else:
    print(f'ERROR: {manifest_path} does not exist!')
