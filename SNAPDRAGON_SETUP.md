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

**There is no IP address to configure.** The board runs mDNS, so it is reachable by name:

```text
SCL-UNOQ05.local
```

That name keeps working when the IP changes, when you switch Wi-Fi, or on a phone hotspot.
`scripts/board_link.py` finds the board on its own: USB first, then the mDNS name. Nothing in
the project stores an address.

What you do need:

1. This laptop and the board on the **same Wi-Fi network**.
2. **Client isolation OFF** on that network — most venue and guest networks block devices from
   seeing each other, and that cannot be fixed from our side. A phone hotspot you control avoids it.
3. **No VPN running** on this laptop — VPNs capture local traffic too.

To join the board to a network, plug it into USB and run (substituting your own details —
type the password yourself, do not paste it into chat):

```powershell
& $adb shell 'ID=$(wpa_cli -i wlan0 add_network | tail -1); wpa_cli -i wlan0 set_network $ID ssid "\"YOUR_SSID\""; wpa_cli -i wlan0 set_network $ID psk "\"YOUR_PASSWORD\""; wpa_cli -i wlan0 enable_network $ID; wpa_cli -i wlan0 select_network $ID; wpa_cli -i wlan0 save_config'
```

The board remembers every network you add and joins whichever is in range, so adding your
hotspot once makes it work at the venue and anywhere else.

Check which route is live at any time:

```powershell
python scripts/board_link.py
```
```powershell
$env:BOARD_TARGET="net"; python scripts/board_link.py; Remove-Item Env:\BOARD_TARGET
```
The second forces the network path, ignoring USB — that is how you prove the Wi-Fi link works.

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

Anything else stops at the first broken link and names the fix, ending in `NOT CONNECTED`.
**Send that output back** — it says exactly where the chain breaks.

To prove the **network** link specifically (ignores USB entirely):

```powershell
$env:BOARD_TARGET="net"; python scripts/check_link.py; Remove-Item Env:\BOARD_TARGET
```
A `CONNECTED (over ssh (SCL-UNOQ05.local))` line means the two devices are talking over Wi-Fi
with no cable and no cloud.

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
2. The output of the `BOARD_TARGET="net"` variant, if you are setting up the Wi-Fi link.
3. One sample of the detector's JSON output, if there is a detection pipeline already.
4. Any error text, verbatim.
