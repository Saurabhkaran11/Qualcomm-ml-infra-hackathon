"""Read a JSON file of camera results and show them on the Modulino Pixels (8 LEDs).

Usage: python3 check_auth.py <file.json>

Accepted shapes:
  {"people": [{"id": "a", "status": "authorized", "box": [x, y, w, h]}, ...]}   one LED per person
  {"status": "authorized"}                                                      single result, LED 0

People are sorted left-to-right by box x when boxes are present, so the LEDs match the frame.
A person is authorized only when status is "authorized" (case-insensitive); anything else —
missing file, bad JSON, unknown status — is unauthorized, so a bad input never opens the door.
"""
import json
import sys

PIXELS = 8


def read_people(path):
    """Return a list of bools, one per person, leftmost first. Empty list means nothing detected."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        # stderr: stdout is the MCP stdio channel when mcp_server.py imports this
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        return [False]  # unreadable input is a denial, not an empty frame

    if not isinstance(data, dict):
        return [False]

    people = data.get("people")
    if people is None:
        return [is_authorized_entry(data)]
    if not isinstance(people, list):
        return [False]

    def left_edge(person):
        box = person.get("box") if isinstance(person, dict) else None
        return box[0] if isinstance(box, list) and box else 0

    return [is_authorized_entry(p) for p in sorted(people, key=left_edge)]


def is_authorized_entry(person):
    return isinstance(person, dict) and str(person.get("status", "")).lower() == "authorized"


def to_mask(people):
    """Pack the first 8 results into a bitmask: bit i set = LED i green."""
    mask = 0
    for i, authorized in enumerate(people[:PIXELS]):
        if authorized:
            mask |= 1 << i
    return mask


def describe(people):
    if not people:
        return "no people detected"
    shown = people[:PIXELS]
    allowed = sum(shown)
    text = f"{len(people)} detected: {allowed} authorized, {len(shown) - allowed} unauthorized"
    if len(people) > PIXELS:
        text += f" (showing first {PIXELS} of {len(people)})"
    return text


def is_authorized(path):
    """True only when every person in the frame is authorized (and at least one was found)."""
    people = read_people(path)
    return bool(people) and all(people)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 check_auth.py <file.json>")

    people = read_people(sys.argv[1])
    print(describe(people))

    from rpc_base import ArduinoBridge  # here so the parsing above runs without msgpack

    bridge = ArduinoBridge()
    try:
        bridge.call("set_people", min(len(people), PIXELS), to_mask(people))
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
