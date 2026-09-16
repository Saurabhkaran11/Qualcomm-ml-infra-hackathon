# Commands

Every command below was run on Windows (PowerShell) with the Arduino UNO Q on USB and the
Modulino Pixels on the Qwiic connector. Run them **in order**, from the repo folder:

```powershell
cd C:\Users\Jungl\Desktop\Qualcomm-ml-infra-hackathon
```

## 1. Check the board is connected

```powershell
arduino-cli version
```
```powershell
arduino-cli board list
```
Expect a line with `Arduino UNO Q  arduino:zephyr:unoq`. Note the port (here `COM5`); change it below if yours differs.

## 2. Install board support and libraries (one time)

```powershell
arduino-cli core install arduino:zephyr
```
```powershell
arduino-cli lib install Arduino_RouterBridge Arduino_Modulino
```

## 3. Compile and upload the sketch to the MCU

```powershell
arduino-cli compile --fqbn arduino:zephyr:unoq MCU/auth_status
```
```powershell
arduino-cli upload -p COM5 --fqbn arduino:zephyr:unoq MCU/auth_status
```
The Pixels turn **blue** when the sketch is running.

## 4. Copy the Python side to the board (Linux/MPU)

`adb` comes with the Arduino tools. Set its path once per terminal:

```powershell
$adb = "$env:LOCALAPPDATA\Arduino15\packages\arduino\tools\adb\32.0.0\adb.exe"
```
```powershell
& $adb devices
```
Expect one line ending in `device`.

```powershell
& $adb shell mkdir -p /home/arduino/rpc/samples
```
```powershell
& $adb push MPU/check_auth.py MPU/rpc_base.py /home/arduino/rpc/
```
```powershell
& $adb push MPU/samples/authorized.json MPU/samples/unauthorized.json /home/arduino/rpc/samples/
```

## 5. Copy msgpack to the board (one time)

The board has no `pip`, so download msgpack on the PC and copy its pure-Python package over:

```powershell
python -m pip download msgpack==1.2.2 --no-binary :all: --no-deps -d $env:TEMP
```
```powershell
tar -xzf "$env:TEMP\msgpack-1.2.2.tar.gz" -C $env:TEMP
```
```powershell
& $adb push "$env:TEMP\msgpack-1.2.2\msgpack" /home/arduino/rpc/
```

## 6. Run the authorization check

```powershell
& $adb shell "cd /home/arduino/rpc && MSGPACK_PUREPYTHON=1 python3 check_auth.py samples/authorized.json"
```
Prints `AUTHORIZED`; Pixels flash once, then stay **green**.

```powershell
& $adb shell "cd /home/arduino/rpc && MSGPACK_PUREPYTHON=1 python3 check_auth.py samples/unauthorized.json"
```
Prints `UNAUTHORIZED`; Pixels flash 3 times, then stay **red**.

## 7. Useful checks

```powershell
& $adb shell ls /home/arduino/rpc /home/arduino/rpc/samples
```
Lists the files on the board.

```powershell
& $adb shell systemctl is-active arduino-router
```
Prints `active` when the Linux↔MCU router is running.

## 8. AI demo over MCP (Snapdragon X Elite)

Push the MCP server to the board (from the PC that has the board on USB):

```powershell
& $adb push MPU/mcp_server.py /home/arduino/rpc/
```

Verify it end to end against the real hardware:

```powershell
python scripts/test_mcp_server.py
```
Prints `all MCP server checks passed`.

On the X Elite laptop (board plugged into it, `adb` available), install the client:

```powershell
pip install -r x_elite/requirements.txt
```

Start GenieX in one terminal and keep it running:

```powershell
geniex pull qualcomm/Qwen3-4B-Instruct-2507
```
```powershell
geniex serve
```

In a second terminal, start the chat client:

```powershell
python -m x_elite.client
```
Then type `check samples/authorized.json` or `turn the light red`, and the Pixels react.

## If something fails

- `arduino-cli` not recognized → close and reopen the terminal (PATH refresh after install).
- `No boards found` → replug the USB-C cable, run `arduino-cli board list` again.
- Pixels blink **violet** → the bridge failed; replug the board and re-run step 6.
- `Timed out waiting for 'set_status'` → the sketch isn't running; redo step 3.
