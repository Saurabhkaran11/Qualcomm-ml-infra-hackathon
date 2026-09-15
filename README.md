# Qualcomm ML Infra Hackathon — Authorization Status Light

Arduino Uno Q reads a JSON file and shows whether it is authorized on a Modulino Pixels strip.

- `"status": "authorized"` → green (1 flash, then solid)
- anything else (other status, bad JSON, missing file) → red (3 flashes, then solid)
- blue = idle, blinking violet = Linux↔MCU bridge failed

## How it works

The Uno Q has two processors: a Linux processor (MPU) and a microcontroller (MCU). They talk through
the `arduino-router` service using MessagePack-RPC messages.

```
JSON file ──► check_auth.py (Linux/MPU) ──RPC "set_status"──► arduino-router ──► auth_status.ino (MCU) ──► Modulino Pixels
```

1. `check_auth.py` reads the JSON file and decides authorized (1) or unauthorized (0).
2. `rpc_base.py` sends the call `set_status(1 or 0)` to the router socket `/var/run/arduino-router.sock`.
3. The router forwards it to the MCU, where the sketch registered `set_status` with `Bridge.provide`.
4. The sketch sets all 8 Pixels green or red and returns the value back to Linux.

## Hardware

- Arduino UNO Q
- Arduino Modulino Pixels, plugged into the UNO Q's Qwiic connector (the library uses `Wire1` on the UNO Q)

## Layout

- `MCU/auth_status/auth_status.ino` — MCU sketch; exposes `set_status(int)` over the RPC bridge and drives the Pixels.
- `MPU/check_auth.py` — runs on the Uno Q Linux side; reads the JSON and calls `set_status`.
- `MPU/rpc_base.py` — MessagePack-RPC client for `arduino-router`, from [DerrickJ1612/snapdragon-mcp-arduino](https://github.com/DerrickJ1612/snapdragon-mcp-arduino) (MIT, see `THIRD_PARTY_NOTICES.md`).
- `MPU/samples/` — test files.

## Setup (from Windows, board on COM5)

```bash
arduino-cli core install arduino:zephyr
arduino-cli lib install Arduino_RouterBridge Arduino_Modulino
arduino-cli compile --fqbn arduino:zephyr:unoq MCU/auth_status
arduino-cli upload -p COM5 --fqbn arduino:zephyr:unoq MCU/auth_status
```

Copy `MPU/` to the board (e.g. `adb push MPU/. /home/arduino/rpc/`). The board has no pip, so copy the
`msgpack` package folder from the msgpack source tarball next to the scripts.

## Run (on the board)

```bash
cd /home/arduino/rpc
MSGPACK_PUREPYTHON=1 python3 check_auth.py samples/authorized.json
MSGPACK_PUREPYTHON=1 python3 check_auth.py samples/unauthorized.json
```

## Not yet

- Beep: no buzzer on the Uno Q or Pixels. Add a Modulino Buzzer and call `tone()` in `set_status`.
- Camera input (Snapdragon X): have it write the JSON file, then run `check_auth.py`.

## References

**Hardware docs**
- [Arduino UNO Q](https://docs.arduino.cc/hardware/uno-q/) — board overview, pinout, specs.
- [UNO Q user manual](https://docs.arduino.cc/tutorials/uno-q/user-manual/) — MPU/MCU setup, Bridge, `adb` access.
- [Modulino Pixels](https://docs.arduino.cc/hardware/modulino-pixels/) — the 8-LED RGB module used for the status light.
- [Modulino Buzzer](https://docs.arduino.cc/hardware/modulino-buzzer/) — add-on for the planned beep.

**Libraries and tools**
- [Arduino_RouterBridge](https://github.com/arduino-libraries/Arduino_RouterBridge) — MCU library; `Bridge.provide()` exposes `set_status`.
- [arduino-router](https://github.com/arduino/arduino-router) — Linux service that routes RPC calls between MPU and MCU.
- [Arduino_Modulino](https://github.com/arduino-libraries/Arduino_Modulino) — library for `ModulinoPixels` (`set`, `show`).
- [Arduino CLI docs](https://arduino.github.io/arduino-cli/latest/) — `compile`, `upload`, `lib install`.
- [msgpack (PyPI)](https://pypi.org/project/msgpack/) — Python MessagePack library used by `rpc_base.py`.
- [MessagePack-RPC spec](https://github.com/msgpack-rpc/msgpack-rpc/blob/master/spec.md) — message format (request/response/notify).

**Source code this project builds on**
- [DerrickJ1612/snapdragon-mcp-arduino](https://github.com/DerrickJ1612/snapdragon-mcp-arduino) — origin of `rpc_base.py` and the
  `rpc_hearts` example this project was modeled on (MIT, see `THIRD_PARTY_NOTICES.md`).
