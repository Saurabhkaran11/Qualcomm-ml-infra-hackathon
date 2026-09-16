"""Send one camera result to the Uno Q. This is the integration point for the detector.

Command line:
    python scripts/send_to_board.py result.json     # a file the detector wrote
    detector.py | python scripts/send_to_board.py - # or straight from stdout

From Python:
    from send_to_board import send
    send({"people": [{"id": "u1", "status": "authorized", "box": [40, 120, 90, 200]}]})

Expected input — the only fields that matter are "people" and each person's "status":

    {"people": [
        {"id": "user-001", "status": "authorized",   "box": [40, 120, 90, 200], "confidence": 0.97},
        {"id": "unknown",  "status": "unauthorized", "box": [180, 130, 95, 210], "confidence": 0.61}
    ]}

    status == "authorized" (any case) -> green LED for that person
    anything else, including "unknown" -> red LED + one beep

    box is [x, y, w, h]; its x sorts the LEDs left-to-right so they match the frame.
    Everything else is ignored, so extra fields from your detector are fine.

Prints what the board did, e.g.
    5 detected: 3 authorized, 2 denied   (over usb (4208084015))
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from board_link import connect  # noqa: E402

REMOTE_DIR = "/home/arduino/rpc"
REMOTE_FILE = "/tmp/verdict.json"


def send(result, link=None):
    """Push one result to the board and light it up. Returns the board's summary line."""
    if isinstance(result, (str, bytes)):
        result = json.loads(result)
    payload = json.dumps(result)
    if "'" in payload:  # would break the single-quoted remote shell command
        raise ValueError("single quotes are not supported in the payload")

    link = link or connect()
    if not link:
        raise RuntimeError("board not found. run: python scripts/check_link.py")

    # heredoc works the same over adb shell and ssh, so no scp/adb-push special case
    command = (
        f"cat > {REMOTE_FILE} <<'JSON'\n{payload}\nJSON\n"
        f"cd {REMOTE_DIR} && MSGPACK_PUREPYTHON=1 python3 check_auth.py {REMOTE_FILE}"
    )
    code, out = link.run(command)
    if code or not out:
        raise RuntimeError(f"board did not answer: {out}")
    return out.splitlines()[-1]


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python send_to_board.py <result.json | ->")

    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1]).read()
    link = connect()
    if not link:
        sys.exit("board not found. run: python scripts/check_link.py")

    print(f"{send(raw, link)}   (over {link.describe()})")


if __name__ == "__main__":
    main()
