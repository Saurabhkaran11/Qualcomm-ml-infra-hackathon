"""MCP server for the Uno Q Linux side (MPU). Speaks MCP over stdio.

Exposes two tools to an AI model:
  check_file(path)     - read a JSON file, decide authorized, show it on the Pixels
  set_light(authorized)- force the Pixels green or red

The Uno Q has no pip, so this uses only the standard library instead of the MCP SDK:
stdio transport is newline-delimited JSON-RPC, which is short enough to write out.

Run it from the AI host over adb:
    adb shell "cd /home/arduino/rpc && MSGPACK_PUREPYTHON=1 python3 mcp_server.py"
"""
import json
import sys

from check_auth import PIXELS, to_mask, verdict
from rpc_base import ArduinoBridge

PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {
        "name": "check_file",
        "description": (
            "Read a JSON camera result on the Arduino Uno Q and show it on the 8 Modulino Pixels: "
            "one LED per detected person, leftmost first, green if authorized and red if not. "
            "The buzzer beeps once per refused person and stays silent when all are cleared."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the JSON file on the board, e.g. samples/authorized.json",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "set_light",
        "description": "Set the Modulino Pixels directly: green when authorized is true, red when false.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "authorized": {"type": "boolean", "description": "true = green, false = red"}
            },
            "required": ["authorized"],
        },
    },
]


def show(people):
    """Drive the MCU. One short-lived bridge per call keeps the socket state simple."""
    bridge = ArduinoBridge()
    try:
        bridge.call("set_people", min(len(people), PIXELS), to_mask(people))
    finally:
        bridge.close()


def call_tool(name, args):
    if name == "check_file":
        path = args["path"]
        people, denied, summary = verdict(path)
        show(people)
        lights = f"{len(people) - denied} green, {denied} red" if people else "all off"
        beeps = f"{denied} beep(s)" if denied else "silent"
        return f"{path}: {summary}. Pixels {lights}, {beeps}."

    if name == "set_light":
        authorized = bool(args["authorized"])
        show([authorized])
        return f"Modulino Pixels set to {'green' if authorized else 'red'}."

    raise ValueError(f"unknown tool: {name}")


def handle(request):
    """Return a JSON-RPC result for a request, or None for a notification."""
    method = request.get("method")

    if method == "initialize":
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "unoq-auth", "version": "0.1.0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        params = request.get("params", {})
        try:
            text = call_tool(params.get("name"), params.get("arguments") or {})
            is_error = False
        except Exception as exc:  # reported to the model, not crashing the server
            text = f"error: {exc}"
            is_error = True
        return {"content": [{"type": "text", "text": text}], "isError": is_error}

    raise LookupError(method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = json.loads(line)
        if "id" not in request:  # notification, e.g. notifications/initialized
            continue

        try:
            response = {"jsonrpc": "2.0", "id": request["id"], "result": handle(request)}
        except LookupError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {"code": -32601, "message": f"method not found: {exc}"},
            }
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
