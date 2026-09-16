"""Is this machine connected to the Uno Q? Prints CONNECTED or NOT CONNECTED.

    python scripts/check_link.py            # auto: usb, then network
    BOARD_TARGET=net python scripts/check_link.py    # force the network path

Finds the board by itself (see board_link.py) — no IP to edit. Checks each link in the chain,
stops at the first break and names the fix. The last check is physical: the board runs a
green-then-red sequence you can see and hear.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from board_link import TARGET, connect  # noqa: E402

REMOTE = "cd /home/arduino/rpc && MSGPACK_PUREPYTHON=1 python3"


def fail(step, detail, fix):
    print(f"\n[FAIL] {step}")
    if detail:
        print(f"       {detail}")
    print(f"  fix: {fix}")
    print("\nNOT CONNECTED")
    sys.exit(1)


def main():
    print(f"looking for the board (BOARD_TARGET={TARGET})")
    link = connect(verbose=True)
    if not link:
        fail("board not found on any route", None,
             "USB: use a DATA usb-c cable and check the board is not plugged into another "
             "computer. Network: the board and this machine must be on the same Wi-Fi, with "
             "client isolation off and any VPN disabled.")
    print(f"[ok]   reached the board over {link.describe()}")

    code, out = link.run("hostname")
    if code:
        fail("cannot run commands on the board", out, "replug the board, or re-run this check")
    print(f"[ok]   board says its name is {out}")

    code, out = link.run("systemctl is-active arduino-router")
    if "active" not in out:
        fail("arduino-router not running on the board", out,
             "power-cycle the board, then re-run this check")
    print("[ok]   arduino-router is running")

    code, out = link.run(f"{REMOTE} -c \"import msgpack; print('ok')\"")
    if "ok" not in out:
        fail("board is missing the python files", out,
             "run the push/msgpack steps in SNAPDRAGON_SETUP.md step 7")
    print("[ok]   board-side python is in place")

    print("\n-- watch the board --")
    code, out = link.run(f"{REMOTE} check_auth.py samples/frame_3authorized.json")
    if "3 authorized" not in out:
        fail("the board did not answer", out,
             "flash the sketch: arduino-cli upload -p COM5 --fqbn arduino:zephyr:unoq MCU/auth_status")
    print(f"[ok]   {out.splitlines()[-1]}")
    print("       expect: 3 GREEN leds, a tick on the matrix, no sound")

    code, out = link.run(f"{REMOTE} check_auth.py samples/frame_5people.json")
    if "2 denied" not in out:
        fail("the board did not answer the second frame", out, "re-run this check")
    print(f"[ok]   {out.splitlines()[-1]}")
    print("       expect: 3 GREEN + 2 RED leds, X flashing twice, 2 beeps")

    print(f"\nCONNECTED  (over {link.describe()})")
    print("If the lights and beeps did NOT happen, the software link is fine but the")
    print("Modulino Pixels/Buzzer are not wired to the Qwiic connector.")


if __name__ == "__main__":
    main()
