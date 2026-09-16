"""Self-check for the JSON parsing in MPU/check_auth.py. No hardware needed.

    python scripts/test_check_auth.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "MPU"))

from check_auth import describe, read_people, to_mask  # noqa: E402


def people_of(data):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(data, f) if not isinstance(data, str) else f.write(data)
        path = f.name
    try:
        return read_people(path)
    finally:
        os.unlink(path)


def main():
    # one LED per person, sorted left-to-right by box x regardless of file order
    people = people_of(
        {
            "people": [
                {"id": "c", "status": "authorized", "box": [300, 0, 10, 10]},
                {"id": "a", "status": "unauthorized", "box": [10, 0, 10, 10]},
                {"id": "b", "status": "AUTHORIZED", "box": [150, 0, 10, 10]},
            ]
        }
    )
    assert people == [False, True, True], people
    assert to_mask(people) == 0b110, bin(to_mask(people))

    # unknown status is a denial
    assert people_of({"people": [{"status": "unknown"}]}) == [False]

    # single-result shape still works
    assert people_of({"status": "authorized"}) == [True]

    # empty frame: nothing detected, no LEDs lit
    empty = people_of({"people": []})
    assert empty == [] and to_mask(empty) == 0, empty
    assert describe(empty) == "no people detected"

    # more than 8: mask covers the first 8 only, description says so
    crowd = people_of({"people": [{"status": "authorized"} for _ in range(9)]})
    assert len(crowd) == 9 and to_mask(crowd) == 0xFF, (len(crowd), bin(to_mask(crowd)))
    assert "showing first 8 of 9" in describe(crowd), describe(crowd)

    # bad input is a denial, never an empty frame
    assert people_of("{not json") == [False]
    assert people_of([1, 2, 3]) == [False]
    assert people_of({"people": "nope"}) == [False]
    assert read_people("no/such/file.json") == [False]

    assert describe([True, False]) == "2 detected: 1 authorized, 1 unauthorized"

    print("all check_auth checks passed")


if __name__ == "__main__":
    main()
