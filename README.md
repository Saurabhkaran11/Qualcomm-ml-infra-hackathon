# Qualcomm ML Infra Hackathon — Authorization Status Light

Arduino Uno Q reads a JSON file and shows whether it is authorized on a Modulino Pixels strip.

- `"status": "authorized"` → green (1 flash, then solid)
- anything else (other status, bad JSON, missing file) → red (3 flashes, then solid)
- blue = idle, blinking violet = Linux↔MCU bridge failed

## Layout

- `MCU/auth_status/auth_status.ino` — MCU sketch; exposes `set_status(int)` over the RPC bridge and drives the Pixels.
- `MPU/check_auth.py` — runs on the Uno Q Linux side; reads the JSON and calls `set_status`.
- `MPU/rpc_base.py` — MessagePack-RPC client for `arduino-router`, from [DerrickJ1612/snapdragon-mcp-arduino](https://github.com/DerrickJ1612/snapdragon-mcp-arduino).
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
