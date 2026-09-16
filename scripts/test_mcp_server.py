"""Self-check for MPU/mcp_server.py: drives it over adb the same way the AI client does.

Run from the repo root on the machine with the board attached:
    python scripts/test_mcp_server.py

Asserts the MCP handshake, the tool list, and both tools against the real hardware.
"""
import json
import os
import subprocess
import sys

ADB = os.environ.get(
    "ADB", os.path.expandvars(r"%LOCALAPPDATA%\Arduino15\packages\arduino\tools\adb\32.0.0\adb.exe")
)
REMOTE = "cd /home/arduino/rpc && MSGPACK_PUREPYTHON=1 python3 mcp_server.py"


def main():
    proc = subprocess.Popen(
        [ADB, "shell", REMOTE],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    def rpc(msgid, method, params=None):
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": msgid, "method": method, "params": params or {}}) + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    try:
        init = rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
        assert init["result"]["serverInfo"]["name"] == "unoq-auth", init

        tools = {t["name"] for t in rpc(2, "tools/list")["result"]["tools"]}
        assert tools == {"check_file", "set_light"}, tools

        ok = rpc(3, "tools/call", {"name": "check_file", "arguments": {"path": "samples/authorized.json"}})
        text = ok["result"]["content"][0]["text"]
        assert not ok["result"]["isError"] and "Pixels 1 green, 0 red, silent" in text, ok

        five = rpc(4, "tools/call", {"name": "check_file", "arguments": {"path": "samples/frame_5people.json"}})
        text = five["result"]["content"][0]["text"]
        assert "3 authorized, 2 denied" in text and "Pixels 3 green, 2 red, 2 beep(s)" in text, five

        bad = rpc(5, "tools/call", {"name": "check_file", "arguments": {"path": "samples/nope.json"}})
        assert "Pixels 0 green, 1 red, 1 beep(s)" in bad["result"]["content"][0]["text"], bad

        red = rpc(6, "tools/call", {"name": "set_light", "arguments": {"authorized": False}})
        assert "red" in red["result"]["content"][0]["text"], red

        unknown = rpc(7, "tools/call", {"name": "nope", "arguments": {}})
        assert unknown["result"]["isError"], unknown

        missing = rpc(8, "does/not/exist")
        assert missing["error"]["code"] == -32601, missing
    finally:
        proc.stdin.close()
        proc.terminate()

    print("all MCP server checks passed")


if __name__ == "__main__":
    sys.exit(main())
