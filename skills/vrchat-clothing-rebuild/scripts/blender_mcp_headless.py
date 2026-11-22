"""Run the installed Blender MCP add-on inside Blender's background (headless) mode.

Usage:
    blender -b scene.blend --python blender_mcp_headless.py -- --host 127.0.0.1 --port 9876

The Blender MCP add-on normally starts its socket server from the GUI timer loop.
This launcher drains the command queue on Blender's main thread so the same MCP
server can be used when the Blender GUI is unavailable or undesired.
"""

import argparse
import socket
import sys
import threading
import time

import bpy


def parse_args():
    user_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Start Blender MCP server in headless mode.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9876, help="Bind port (default: 9876)")
    return parser.parse_args(user_args)


def main():
    args = parse_args()
    if "blender_mcp" not in bpy.context.preferences.addons:
        bpy.ops.preferences.addon_enable(module="blender_mcp")

    import blender_mcp

    server = blender_mcp.BlenderMCPServer(host=args.host, port=args.port)
    server.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.socket.bind((server.host, server.port))
    server.socket.listen(5)
    server.running = True
    server.server_thread = threading.Thread(target=server._server_loop, daemon=True)
    server.server_thread.start()
    print(f"BLENDER_MCP_HEADLESS_READY {server.host}:{server.port}", flush=True)

    try:
        while server.running:
            server._drain_command_queue()
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()


if __name__ == "__main__":
    main()
