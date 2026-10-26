import socket
import json

payload = {
    "type": "execute",
    "strict_json": False,
    "code": """import bpy
import addon_utils

# 1. Enable blender_mcp (ahujasid MCP for Blender)
addon_utils.enable("blender_mcp", default_set=True, persistent=True)

# 2. Schedule stopping bl_ext.lab_blender_org.mcp and starting blender_mcp on timer
def _switch_mcp():
    try:
        from bl_ext.lab_blender_org.mcp import mcp_to_blender_server
        mcp_to_blender_server.stop()
    except Exception as e:
        print("Stop lab_blender_org.mcp error:", e)
    try:
        addon_utils.disable("bl_ext.lab_blender_org.mcp", default_set=True)
    except Exception as e:
        print("Disable lab_blender_org.mcp error:", e)
    try:
        bpy.ops.blendermcp.start_server()
    except Exception as e:
        print("Start blendermcp error:", e)
    try:
        bpy.ops.wm.save_userpref()
    except Exception as e:
        print("Save userpref error:", e)
    return None

bpy.app.timers.register(_switch_mcp, first_interval=0.2)
result = {"switched": True, "addons": [m.__name__ for m in addon_utils.modules() if "mcp" in m.__name__.lower()]}
"""
}

s = socket.create_connection(("127.0.0.1", 9876), timeout=5)
s.sendall(json.dumps(payload).encode("utf-8") + b"\x00")
resp = s.recv(8192)
print("Response from Blender:", resp.decode("utf-8", errors="replace"))
s.close()
