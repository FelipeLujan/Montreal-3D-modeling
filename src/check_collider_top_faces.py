import bpy

col = bpy.data.objects.get("Ground_District_Solid_Collider")
me = col.data
mw = col.matrix_world
rot_3x3 = mw.to_3x3()

top_faces = []
for p in me.polygons:
    wn = (rot_3x3 @ p.normal).normalized()
    wc = mw @ p.center
    if wn.z > 0.88:
        top_faces.append((p.index, wc, wn))

print(f"Total top faces: {len(top_faces)}")
for idx, c, n in top_faces:
    print(f"  Face {idx:2d}: center=({c.x:7.1f}, {c.y:7.1f}, {c.z:6.3f}), normal=({n.x:4.2f}, {n.y:4.2f}, {n.z:4.2f})")

expected_top_regions = [
    ("Waterfront Basin", -75, -465, -2.500),
    ("West Mainland Buffer", -585, 150, 0.000),
    ("East Mainland Buffer", 510, 150, 0.000),
    ("North Mainland Buffer", 0, 520, 0.000),
    ("City Core", 0, -10, -0.150),
]

for label, ex, ey, ez in expected_top_regions:
    matched = False
    for idx, c, n in top_faces:
        if abs(c.x - ex) < 100.0 and abs(c.y - ey) < 100.0 and abs(c.z - ez) < 0.10:
            matched = True
            print(f"MATCH: '{label}' matched face {idx} at ({c.x:.1f}, {c.y:.1f}, {c.z:.3f})")
            break
    if not matched:
        print(f"FAIL: '{label}' NOT matched! Expected ~({ex}, {ey}, {ez})")
