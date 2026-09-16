"""Read a JSON camera result, decide authorized, show it on the Modulino Pixels and buzzer.

Usage: python3 check_auth.py <file.json>

Accepted shapes:
  {"people": [{"id": "a", "status": "authorized"}, ...]}   several people in one frame
  {"status": "authorized"}                                 single result

One LED per person, leftmost first: green if authorized, red if not. The buzzer beeps once per
refused person and stays silent when every light is green. Anything that is not exactly
"authorized" — unknown, a missing field, bad JSON, a missing file — counts as a refusal, so a
bad input never opens the door.
"""
import json
import sys

PIXELS = 8


def read_statuses(path):
    """Return a list of bools, one per person. Empty list means nothing detected."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        # stderr: stdout is the MCP stdio channel when mcp_server.py imports this
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        return [False]  # unreadable input is a refusal, not an empty frame

    if not isinstance(data, dict):
        return [False]

    people = data.get("people")
    if people is None:
        return [is_cleared(data)]
    if not isinstance(people, list):
        return [False]

    def left_edge(person):
        box = person.get("box") if isinstance(person, dict) else None
        return box[0] if isinstance(box, list) and box else 0

    # leftmost first, so the LEDs line up with where people stand in the frame
    return [is_cleared(p) for p in sorted(people, key=left_edge)]


def is_cleared(person):
    return isinstance(person, dict) and str(person.get("status", "")).lower() == "authorized"


def to_mask(people):
    """Pack the first 8 results into a bitmask: bit i set = LED i green."""
    mask = 0
    for i, cleared in enumerate(people[:PIXELS]):
        if cleared:
            mask |= 1 << i
    return mask


def verdict(path):
    """(people, denied_count, summary) for one camera result."""
    people = read_statuses(path)
    denied = people.count(False)

    if not people:
        summary = "no people detected"
    else:
        summary = f"{len(people)} detected: {len(people) - denied} authorized, {denied} denied"
        if len(people) > PIXELS:
            summary += f" (showing first {PIXELS})"
    return people, denied, summary


def is_authorized(path):
    """True only when at least one person was found and nobody was refused."""
    people, denied, _ = verdict(path)
    return bool(people) and denied == 0


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 check_auth.py <file.json>")

    people, denied, summary = verdict(sys.argv[1])
    print(f"{'AUTHORIZED' if people and not denied else 'UNAUTHORIZED'} - {summary}")

    from rpc_base import ArduinoBridge  # here so the parsing above runs without msgpack

    bridge = ArduinoBridge()
    try:
        bridge.call("set_people", min(len(people), PIXELS), to_mask(people))
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
