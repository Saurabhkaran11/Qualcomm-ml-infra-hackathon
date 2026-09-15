"""Read a JSON file, decide authorized/unauthorized, show it on the Modulino Pixels.

Usage: python3 check_auth.py <file.json>
Authorized only when the file has "status": "authorized" (case-insensitive).
Anything else (missing file, bad JSON, other status) is unauthorized.
"""
import json
import sys

from rpc_base import ArduinoBridge


def is_authorized(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"cannot read {path}: {exc}")
        return False
    return isinstance(data, dict) and str(data.get("status", "")).lower() == "authorized"


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 check_auth.py <file.json>")

    authorized = is_authorized(sys.argv[1])
    print("AUTHORIZED" if authorized else "UNAUTHORIZED")

    bridge = ArduinoBridge()
    try:
        bridge.call("set_status", int(authorized))
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
