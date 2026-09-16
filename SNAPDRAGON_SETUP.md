# Snapdragon X Elite — setup and integration

**Read this first if you are an AI coding agent working on the Snapdragon laptop.**

- **Goal:** make this laptop able to send camera results to an Arduino Uno Q, which shows one
  LED per detected person (green = authorized, red = not) and beeps once per refusal.
- **Your deliverable:** the detector on this laptop calls `scripts/send_to_board.py`. That is
  the entire integration — do not write RPC, MCP or serial code, it already exists.
- **Done when:** `python scripts/check_link.py` prints `CONNECTED`, and sending one of your
  detector's own results makes the board react.
- **Do not change** anything under `MCU/` or `MPU/` — that is the board's firmware and its
  Linux side, both already tested on hardware. Adapt on this side.
- **If a step fails,** stop and report the exact command and its full output. Do not work
  around it by editing the board code.

Every command is PowerShell, run from the repo root.

---

## The contract (the only thing your code must produce)

```json
{"people": [
  {"id": "user-001", "status": "authorized",   "box": [40, 120, 90, 200], "confidence": 0.97},
  {"id": "unknown",  "status": "unauthorized", "box": [180, 130, 95, 210], "confidence": 0.61}
]}
```

| Field | Required | Meaning |
|---|---|---|
| `people` | yes | one entry per detected person; `[]` means nobody, and the board goes dark |
| `status` | yes | `"authorized"` (any case) → green. **Anything else, including `"unknown"` or a missing field → red + one beep** |
| `box` | recommended | `[x, y, w, h]`; `x` sorts the LEDs left-to-right so they match the frame |
| `id`, `confidence` | no | ignored by the board, useful in logs |

Extra fields are ignored, so your detector's own output shape is fine as long as it contains
`people[].status`. Only 8 people can be shown (8 LEDs); the rest are counted in the summary.

**Fail-safe rule:** unreadable input, bad JSON and unknown people all count as refusals. Never
"fix" this by defaulting to authorized.

## Sending a result

```powershell
python scripts/send_to_board.py result.json
```
```powershell
python your_detector.py | python scripts/send_to_board.py -
```

Or in-process, which is what you most likely want:

```python
from send_to_board import send          # scripts/ must be on sys.path
send({"people": [{"id": "u1", "status": "authorized", "box": [40, 120, 90, 200]}]})
```

It prints, and returns, what the board did:

```text
UNAUTHORIZED - 5 detected: 3 authorized, 2 denied   (over usb (4208084015))
```

---

## 1. Get the code

```powershell
cd $HOME\Desktop
```
```powershell
git clone https://github.com/Saurabhkaran11/Qualcomm-ml-infra-hackathon.git
```
```powershell
cd Qualcomm-ml-infra-hackathon
```

## 2. Python (ARM64 build)

Needs Python 3.11+ **for Windows ARM64** — the native ARM build, not x64, or the NPU work later
will not run.

```powershell
python -c "import platform; print(platform.machine(), platform.python_version())"
```
Expect `ARM64` and `3.11`+. `AMD64` means the emulated build — install the ARM64 one first.

```powershell
pip install -r x_elite/requirements.txt
```

**If this laptop already has a working detection environment, install into that environment
instead, and skip step 5 entirely** — a plain `pip install onnxruntime` can shadow a QNN/NPU build.

## 3. Arduino CLI (this also provides `adb`)

```powershell
winget install ArduinoSA.CLI
```

**Close this terminal and open a new one** so PATH refreshes, then:

```powershell
cd $HOME\Desktop\Qualcomm-ml-infra-hackathon
```
```powershell
arduino-cli version
```
```powershell
arduino-cli core install arduino:zephyr
```
```powershell
arduino-cli lib install Arduino_RouterBridge Arduino_Modulino
```

`adb` lands at `%LOCALAPPDATA%\Arduino15\packages\arduino\tools\adb\32.0.0\adb.exe`. Set it once
per terminal — later blocks assume it:

```powershell
$adb = "$env:LOCALAPPDATA\Arduino15\packages\arduino\tools\adb\32.0.0\adb.exe"
```

## 4. GenieX and Qwen 3 (only if the model should drive the board)

Skip if your detector decides everything itself. Install GenieX with Qualcomm's
[Windows ARM64 instructions](https://geniex.aihub.qualcomm.com/en/run/cli/install/#windows-arm64), then:

```powershell
geniex pull qualcomm/Qwen3-4B-Instruct-2507
```
```powershell
geniex serve
```
Leave that terminal running; open a second one for everything below.

## 5. Camera dependencies (skip if you already have a runtime)

```powershell
pip install opencv-python onnxruntime
```
```powershell
python -c "import cv2; c=cv2.VideoCapture(0); print('camera ok' if c.isOpened() else 'CAMERA NOT FOUND'); c.release()"
```

---

## 6. Connect the board

### 6a. USB (do this first — it is the fallback and needs no network)

Plug the Uno Q in with a **data** USB-C cable.

```powershell
arduino-cli board list
```
Expect `Arduino UNO Q  arduino:zephyr:unoq`. Note the COM port.

### 6b. Wi-Fi (the two-device link)

**There is no IP address to configure.** The board runs mDNS and answers to:

```text
SCL-UNOQ05.local
```

`scripts/board_link.py` finds it by itself — USB first, then that name. Nothing in the repo
stores an address, so changing Wi-Fi never means editing code.

Requirements: both devices on the **same network**, **client isolation OFF** (most venue and
guest networks block device-to-device traffic), and **no VPN** on this laptop.

To join the board to a network, with it plugged into USB — **a human should run this line, so
the password is not pasted into an agent transcript**:

```powershell
& $adb shell 'ID=$(wpa_cli -i wlan0 add_network | tail -1); wpa_cli -i wlan0 set_network $ID ssid "\"YOUR_SSID\""; wpa_cli -i wlan0 set_network $ID psk "\"YOUR_PASSWORD\""; wpa_cli -i wlan0 enable_network $ID; wpa_cli -i wlan0 select_network $ID; wpa_cli -i wlan0 save_config'
```

The board remembers every network added this way and joins whichever is in range.

Which route is live right now:

```powershell
python scripts/board_link.py
```

## 7. Put the board-side files in place (once per board)

```powershell
& $adb shell mkdir -p /home/arduino/rpc/samples
```
```powershell
& $adb push MPU/check_auth.py MPU/rpc_base.py MPU/mcp_server.py /home/arduino/rpc/
```
```powershell
& $adb push MPU/samples/. /home/arduino/rpc/samples/
```

The board has no `pip`, so msgpack is copied as plain Python:

```powershell
python -m pip download msgpack==1.2.2 --no-binary :all: --no-deps -d $env:TEMP
```
```powershell
tar -xzf "$env:TEMP\msgpack-1.2.2.tar.gz" -C $env:TEMP
```
```powershell
& $adb push "$env:TEMP\msgpack-1.2.2\msgpack" /home/arduino/rpc/
```

Flash the firmware (use your COM port from 6a):

```powershell
arduino-cli compile --fqbn arduino:zephyr:unoq MCU/auth_status
```
```powershell
arduino-cli upload -p COM5 --fqbn arduino:zephyr:unoq MCU/auth_status
```

## 8. Verify — one command

```powershell
python scripts/check_link.py
```

**Watch the board while this runs.** Success:

```text
looking for the board (BOARD_TARGET=auto)
  found: usb
[ok]   reached the board over usb (4208084015)
[ok]   board says its name is SCL-UNOQ05
[ok]   arduino-router is running
[ok]   board-side python is in place

-- watch the board --
[ok]   AUTHORIZED - 3 detected: 3 authorized, 0 denied
       expect: 3 GREEN leds, a tick on the matrix, no sound
[ok]   UNAUTHORIZED - 5 detected: 3 authorized, 2 denied
       expect: 3 GREEN + 2 RED leds, X flashing twice, 2 beeps

CONNECTED  (over usb (4208084015))
```

Anything else stops at the first broken link, names the fix, and ends in `NOT CONNECTED`.

To prove the **network** link specifically, ignoring USB:

```powershell
$env:BOARD_TARGET="net"; python scripts/check_link.py; Remove-Item Env:\BOARD_TARGET
```
`CONNECTED (over ssh (SCL-UNOQ05.local))` means the two devices are talking over Wi-Fi, no
cable and no cloud.

Automated checks:

```powershell
python scripts/test_check_auth.py
```
```powershell
python scripts/test_mcp_server.py
```
Both end in `all ... checks passed`.

## 9. Send your detector's output

```powershell
python scripts/send_to_board.py MPU/samples/frame_5people.json
```
Then the same with a real result from your detector. The board reacting is the finish line.

## 10. Optional — the AI demo (needs step 4 running)

```powershell
python -m x_elite.client
```
Then type `check samples/frame_5people.json` or `turn the light red`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `arduino-cli` not recognised | Reopen the terminal after installing (PATH refresh) |
| `No boards found` | Use a **data** USB-C cable, not charge-only; replug |
| `adb: no devices/emulators found` | `& $adb kill-server` then `& $adb start-server`; check the board is not plugged into another computer |
| `board not found on any route` | USB unplugged, or the two devices are on different networks |
| Network route fails but USB works | Client isolation on the Wi-Fi, a VPN on this laptop, or different subnets |
| Pixels blink violet | Linux↔MCU bridge failed — power-cycle the board |
| `CONNECTED` but no lights or sound | Modulino Pixels/Buzzer not plugged into the Qwiic connector |
| `Timed out waiting for 'set_people'` | Firmware not running — redo the flash in step 7 |
| `platform.machine()` says AMD64 | Emulated Python — install the ARM64 build |

## Report back

1. Output of `python scripts/check_link.py`.
2. Output of the `BOARD_TARGET="net"` variant, if setting up the Wi-Fi link.
3. One real sample of the detector's JSON output.
4. Any failure: the command and its full output, verbatim.
