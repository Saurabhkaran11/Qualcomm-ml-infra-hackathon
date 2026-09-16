# Snapdragon X Elite — setup

Run everything here **on the Snapdragon X Elite laptop**, in PowerShell. Top to bottom, one
command per block. The laptop ends up able to drive the Arduino Uno Q — over USB, and over
Wi-Fi with no cloud and no internet.

The Uno Q does not need to be plugged into this laptop for steps 1-5.

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

Install **Python 3.11 or newer, Windows ARM64** — the native ARM installer, not x64. The ARM
build matters later for running models on the NPU.

Check which one you have:

```powershell
python -c "import platform; print(platform.machine(), platform.python_version())"
```
Expect `ARM64` and `3.11`+. If it says `AMD64`, that is the emulated x64 build — install the
ARM64 one before continuing.

Then install the client dependencies:

```powershell
pip install -r x_elite/requirements.txt
```

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

`adb` now lives at `%LOCALAPPDATA%\Arduino15\packages\arduino\tools\adb\32.0.0\adb.exe`.
Save it in a variable — every later block assumes this, and it is per-terminal:

```powershell
$adb = "$env:LOCALAPPDATA\Arduino15\packages\arduino\tools\adb\32.0.0\adb.exe"
```
```powershell
& $adb version
```

## 4. GenieX and Qwen 3

Install GenieX using Qualcomm's
[Windows ARM64 instructions](https://geniex.aihub.qualcomm.com/en/run/cli/install/#windows-arm64),
then:

```powershell
geniex --help
```
```powershell
geniex pull qualcomm/Qwen3-4B-Instruct-2507
```

Start the server and **leave this terminal running** — it serves the local model API on
`127.0.0.1:18181`:

```powershell
geniex serve
```

Open a **second terminal** for everything below, and set `$adb` again there.

## 5. Camera dependencies (needed later, safe to install now)

```powershell
pip install opencv-python onnxruntime
```

Plug in the USB webcam and confirm it is seen:

```powershell
python -c "import cv2; c=cv2.VideoCapture(0); print('camera ok' if c.isOpened() else 'CAMERA NOT FOUND'); c.release()"
```

---

## 6. Connect the Uno Q

### 6a. Over USB (do this first — it is the fallback path)

Plug the Uno Q into this laptop with a **data** USB-C cable, then:

```powershell
arduino-cli board list
```
Expect a line with `Arduino UNO Q  arduino:zephyr:unoq`. Note the COM port.

```powershell
& $adb devices
```
Expect one line ending in `device`.

### 6b. Over Wi-Fi (the two-device link)

1. Turn on your **phone hotspot** (not the venue Wi-Fi) and connect this laptop to it.
2. Connect the Uno Q's Linux side to the same hotspot.
3. In the hotspot settings, make sure **client isolation** is OFF, or the devices cannot see
   each other.

Find the board's IP (with the board still on USB, this asks the board itself):

```powershell
& $adb shell "ip -4 addr show scope global | grep -oP '(?<=inet )[0-9.]+'"
```

**Send that IP address back** — the Wi-Fi link is built around it.

---

## 7. Smoke test (USB, no camera, no model)

Copies the board-side files over and runs the checks. Works whether or not GenieX is running.

```powershell
& $adb shell mkdir -p /home/arduino/rpc/samples
```
```powershell
& $adb push MPU/check_auth.py MPU/rpc_base.py MPU/mcp_server.py /home/arduino/rpc/
```
```powershell
& $adb push MPU/samples/. /home/arduino/rpc/samples/
```

The board has no `pip`, so copy msgpack across as plain Python:

```powershell
python -m pip download msgpack==1.2.2 --no-binary :all: --no-deps -d $env:TEMP
```
```powershell
tar -xzf "$env:TEMP\msgpack-1.2.2.tar.gz" -C $env:TEMP
```
```powershell
& $adb push "$env:TEMP\msgpack-1.2.2\msgpack" /home/arduino/rpc/
```

Flash the sketch:

```powershell
arduino-cli compile --fqbn arduino:zephyr:unoq MCU/auth_status
```
```powershell
arduino-cli upload -p COM5 --fqbn arduino:zephyr:unoq MCU/auth_status
```
(Use the COM port from step 6a if it is not COM5.)

### Am I connected? One command

```powershell
python scripts/check_link.py
```

It checks every link in the chain and then makes the board react, so you can see and hear the
result. **Watch the board while it runs.** Success looks like this:

```text
[ok]   adb found
[ok]   board visible to adb: 4208084015
[ok]   arduino-router is running
[ok]   board-side python is in place

-- watch the board --
[ok]   AUTHORIZED - 3 detected: 3 authorized, 0 denied
       expect: 3 GREEN leds, a tick on the matrix, no sound
[ok]   UNAUTHORIZED - 5 detected: 3 authorized, 2 denied
       expect: 3 GREEN + 2 RED leds, X flashing twice, 2 beeps

CONNECTED
```

Anything else stops at the first broken link and names the fix, ending in `NOT CONNECTED`.
**Send that output back** — it says exactly where the chain breaks.

Three levels of proof, in order of strength:

1. `CONNECTED` printed — the software chain is complete.
2. The LEDs and buzzer react — the whole system works end to end.
3. `CONNECTED` but nothing physical happened — the link is fine, but the Modulino Pixels and
   Buzzer are not plugged into the Qwiic connector.

Then the automated checks:

```powershell
python scripts/test_check_auth.py
```
```powershell
python scripts/test_mcp_server.py
```
Both should end in `all ... checks passed`.

## 8. Full AI demo (needs `geniex serve` running from step 4)

```powershell
python -m x_elite.client
```
Then type: `check samples/frame_5people.json` or `turn the light red`.

---

## If something fails

| Symptom | Fix |
|---|---|
| `arduino-cli` not recognised | Close and reopen the terminal after installing (PATH refresh) |
| `No boards found` | Use a **data** USB-C cable, not charge-only; replug and retry |
| `adb: no devices/emulators found` | `& $adb kill-server` then `& $adb start-server`; check the board is not plugged into another machine |
| Pixels blink violet | The Linux↔MCU bridge failed — replug the board and re-run |
| `Timed out waiting for 'set_people'` | The sketch is not running; redo the flash in step 7 |
| Laptop cannot reach the board over Wi-Fi | Client isolation on the hotspot; both devices must be on the same hotspot |
| `platform.machine()` says AMD64 | Emulated Python — install the ARM64 build |
| `check_link.py` says CONNECTED but nothing lights up | Modulino Pixels/Buzzer not on the Qwiic connector |

## Already have a detection pipeline?

If the camera and face detection are already working on this laptop, do **not** run the whole
file — it would install into the wrong environment or shadow a working runtime.

- **Run:** steps 1, 3, 6, 7. That proves this laptop can drive the board and changes nothing
  about your detector.
- **Skip:** step 2's `pip install` (add `mcp` to your existing environment instead) and all of
  step 5 — especially if you already have a QNN/NPU build of onnxruntime.
- **Optional:** step 4 (GenieX), needed only if Qwen is meant to call the tools.
- **Then send one sample of your detector's output.** That is the integration point: the board
  expects `{"people": [{"id", "status", "box", "confidence"}]}` and an adapter to your format
  is a small change in one function.

## Send back

1. The output of `python scripts/check_link.py`.
2. The board's **IP address** from step 6b.
3. One sample of the detector's JSON output, if there is a detection pipeline already.
4. Any error text, verbatim.
