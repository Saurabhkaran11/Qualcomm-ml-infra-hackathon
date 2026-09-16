"""Self-check for MPU/check_auth.py. No hardware needed.

    python scripts/test_check_auth.py

verdict() returns (people, denied count, summary); the mask drives the LEDs and the denied
count drives the buzzer, so both have to be right.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "MPU"))

from check_auth import to_mask, verdict  # noqa: E402


def verdict_of(data):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(data) if isinstance(data, str) else json.dump(data, f)
        path = f.name
    try:
        return verdict(path)
    finally:
        os.unlink(path)


def main():
    # the demo case: 5 people, 3 cleared, 2 refused -> 3 green + 2 red, 2 beeps
    people, denied, summary = verdict_of(
        {
            "people": [
                {"id": "user-001", "status": "authorized", "box": [60, 0, 1, 1]},
                {"id": "unknown", "status": "unauthorized", "box": [180, 0, 1, 1]},
                {"id": "user-014", "status": "authorized", "box": [300, 0, 1, 1]},
                {"id": "user-022", "status": "authorized", "box": [420, 0, 1, 1]},
                {"id": "unknown", "status": "unknown", "box": [540, 0, 1, 1]},
            ]
        }
    )
    assert people == [True, False, True, True, False], people
    assert denied == 2 and summary == "5 detected: 3 authorized, 2 denied", (denied, summary)
    assert to_mask(people) == 0b01101, bin(to_mask(people))

    # sorted left-to-right regardless of file order
    shuffled, _, _ = verdict_of(
        {
            "people": [
                {"status": "authorized", "box": [300, 0, 1, 1]},
                {"status": "unauthorized", "box": [10, 0, 1, 1]},
            ]
        }
    )
    assert shuffled == [False, True], shuffled

    # all cleared -> no beeps
    assert verdict_of({"people": [{"status": "authorized"}] * 3})[1] == 0

    # single-result shape still works
    assert verdict_of({"status": "authorized"})[:2] == ([True], 0)
    assert verdict_of({"status": "denied"})[:2] == ([False], 1)

    # empty frame: nothing detected, nothing lit, nothing to announce
    empty, denied, summary = verdict_of({"people": []})
    assert (empty, denied, summary) == ([], 0, "no people detected")
    assert to_mask(empty) == 0

    # more than 8: mask covers the first 8, the summary says so
    crowd, denied, summary = verdict_of({"people": [{"status": "authorized"} for _ in range(9)]})
    assert len(crowd) == 9 and to_mask(crowd) == 0xFF, (len(crowd), bin(to_mask(crowd)))
    assert "showing first 8" in summary, summary

    # bad input is always a refusal, never a green
    for bad in ("{not json", [1, 2, 3], {"people": "nope"}, {"people": [{"id": "x"}]}):
        people, denied, _ = verdict_of(bad)
        assert people == [False] and denied == 1, (bad, people, denied)
    assert verdict("no/such/file.json")[:2] == ([False], 1)

    print("all check_auth checks passed")


if __name__ == "__main__":
    main()
