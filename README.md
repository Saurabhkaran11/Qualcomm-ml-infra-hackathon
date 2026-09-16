# Qualcomm ML Infra Hackathon — Authorization Status Light (MCP branch)

Arduino Uno Q reads a JSON file and shows whether it is authorized on a Modulino Pixels strip.
On this branch a local Qwen 3 model on a Snapdragon X Elite drives the board through **MCP**.

- `"status": "authorized"` → green (1 flash, then solid)
- anything else (other status, bad JSON, missing file) → red (3 flashes, then solid)
- blue = idle, blinking violet = Linux↔MCU bridge failed

## Demo in three terminals (X Elite, Uno Q on USB)

```powershell
pip install -r x_elite/requirements.txt   # once
geniex serve                              # terminal 1, keep running
python -m x_elite.client                  # terminal 2
```

Then talk to the model:

```text
you>   check samples/authorized.json
  [tool]  check_file({'path': 'samples/authorized.json'})
  [board] samples/authorized.json: AUTHORIZED. Modulino Pixels set to green.
qwen>  user-001 is authorized, the light is green.

you>   turn the light red
  [tool]  set_light({'authorized': False})
  [board] Modulino Pixels set to red.
```

Full command list, including first-time setup: `COMMANDS.md`.

## Status

| Part | Tested |
|---|---|
| MCU sketch → Modulino Pixels | ✅ on hardware |
| `check_auth.py` → RPC → MCU | ✅ on hardware |
| `mcp_server.py` (handshake, both tools, error paths) | ✅ `scripts/test_mcp_server.py`, and against the official MCP SDK client |
| `x_elite/client.py` → GenieX/Qwen 3 | ⏳ needs a Snapdragon X Elite with GenieX |

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

## AI demo over MCP

A local Qwen 3 model on a Snapdragon X Elite drives the board through MCP:

```
Qwen 3 / GenieX (X Elite) ──► x_elite/client.py ──MCP over adb stdio──► MPU/mcp_server.py (Uno Q Linux)
                                                                          └─► RPC ─► MCU ─► Pixels
```

Tools the model can call:

- `check_file(path)` — read a JSON file on the board, decide authorized, set the light.
- `set_light(authorized)` — force the Pixels green or red.

Why a hand-written server: the Uno Q has no `pip`, so `mcp_server.py` speaks MCP's stdio transport
(newline-delimited JSON-RPC) with the standard library alone — no FastMCP install on the board. It is
verified against the official MCP SDK client by `scripts/test_mcp_server.py`. See `COMMANDS.md` section 8.

Transport note: the client reaches the board with `adb shell`, so nothing is exposed on the network
and no port forwarding is needed.

**MCP vs MPU vs MCU** — easy to mix up:

| Term | Meaning | Here |
|---|---|---|
| MCP | Model Context Protocol; how the AI calls tools | `mcp_server.py` ↔ `x_elite/client.py` |
| MPU | The Uno Q's Linux processor | Runs the Python: checker + MCP server |
| MCU | The Uno Q's microcontroller | Runs the sketch, drives the Pixels |

## Hardware

- Arduino UNO Q
- Arduino Modulino Pixels, plugged into the UNO Q's Qwiic connector (the library uses `Wire1` on the UNO Q)

## Layout

- `MCU/auth_status/auth_status.ino` — MCU sketch; exposes `set_status(int)` over the RPC bridge and drives the Pixels.
- `MPU/check_auth.py` — runs on the Uno Q Linux side; reads the JSON and calls `set_status`.
- `MPU/rpc_base.py` — MessagePack-RPC client for `arduino-router`, from [DerrickJ1612/snapdragon-mcp-arduino](https://github.com/DerrickJ1612/snapdragon-mcp-arduino) (MIT, see `THIRD_PARTY_NOTICES.md`).
- `MPU/mcp_server.py` — MCP server on the Uno Q Linux side; exposes `check_file` and `set_light`.
- `MPU/samples/` — test files.
- `x_elite/client.py` — Snapdragon X Elite chat client: GenieX (Qwen 3) + the MCP tools above.
- `scripts/test_mcp_server.py` — self-check for the MCP server against the real board.

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
