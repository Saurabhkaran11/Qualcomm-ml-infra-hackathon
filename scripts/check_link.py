"""Is this machine actually connected to the Uno Q? Prints CONNECTED or NOT CONNECTED.

    python scripts/check_link.py

Checks each link in the chain and stops at the first break, naming what to fix. The last
check is physical: the board runs a green-then-red sequence you can see and hear.
"""
import os
import subprocess
import sys

ADB = os.environ.get(
    "ADB", os.path.expandvars(r"%LOCALAPPDATA%\Arduino15\packages\arduino\tools\adb\32.0.0\adb.exe")
)
REMOTE = "cd /home/arduino/rpc && MSGPACK_PUREPYTHON=1 python3"


def run(args, timeout=60):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)


def fail(step, detail, fix):
    print(f"\n[FAIL] {step}")
    if detail:
        print(f"       {detail}")
    print(f"  fix: {fix}")
    print("\nNOT CONNECTED")
    sys.exit(1)


def main():
    if not os.path.exists(ADB):
        fail("adb not found", ADB, "install the Arduino CLI (SNAPDRAGON_SETUP.md step 3), "
                                  "or set ADB=<path to adb.exe>")
    print(f"[ok]   adb found")

    code, out = run([ADB, "devices"])
    devices = [l for l in out.splitlines()[1:] if l.strip().endswith("device")]
    if code or not devices:
        fail("no board visible to adb", out,
             "use a DATA usb-c cable (not charge-only), replug, and check the board is not "
             "plugged into another computer")
    print(f"[ok]   board visible to adb: {devices[0].split()[0]}")

    code, out = run([ADB, "shell", "systemctl is-active arduino-router"])
    if "active" not in out:
        fail("arduino-router not running on the board", out,
             "power-cycle the board, then re-run this check")
    print("[ok]   arduino-router is running")

    code, out = run([ADB, "shell", f"{REMOTE} -c \"import msgpack; print('ok')\""])
    if "ok" not in out:
        fail("board is missing the python files", out,
             "run the push/msgpack steps in SNAPDRAGON_SETUP.md step 7")
    print("[ok]   board-side python is in place")

    print("\n-- watch the board --")
    code, out = run([ADB, "shell", f"{REMOTE} check_auth.py samples/frame_3authorized.json"], 90)
    if "3 authorized" not in out:
        fail("the board did not answer", out,
             "flash the sketch: arduino-cli upload -p COM5 --fqbn arduino:zephyr:unoq MCU/auth_status")
    print(f"[ok]   {out.splitlines()[-1]}")
    print("       expect: 3 GREEN leds, a tick on the matrix, no sound")

    code, out = run([ADB, "shell", f"{REMOTE} check_auth.py samples/frame_5people.json"], 90)
    if "2 denied" not in out:
        fail("the board did not answer the second frame", out, "re-run this check")
    print(f"[ok]   {out.splitlines()[-1]}")
    print("       expect: 3 GREEN + 2 RED leds, X flashing twice, 2 beeps")

    print("\nCONNECTED")
    print("If the lights and beeps did NOT happen, the software link is fine but the")
    print("Modulino Pixels/Buzzer are not wired to the Qwiic connector.")


if __name__ == "__main__":
    main()
