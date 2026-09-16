"""Find the Uno Q and return a way to run commands on it — USB, mDNS name, or explicit host.

Nothing else in the project should hardcode an IP. Import from here:

    from board_link import connect
    link = connect()                 # auto: usb, then mdns, then BOARD_HOST
    print(link.describe())           # e.g. "usb (4208084015)"
    code, out = link.run("hostname")
    argv = link.shell_argv(REMOTE)   # for MCP stdio / subprocess

Order matters: USB first because it needs no network at all, so it keeps working when the
Wi-Fi changes, the venue blocks device-to-device traffic, or there is no network.

Environment overrides:
    BOARD_TARGET  auto (default) | usb | net
    BOARD_HOST    hostname or IP to try after mDNS (default: none)
    BOARD_MDNS    mDNS name (default: SCL-UNOQ05.local)
    BOARD_USER    ssh user (default: arduino)
    ADB           path to adb.exe
"""
import os
import shutil
import socket
import subprocess

MDNS = os.environ.get("BOARD_MDNS", "SCL-UNOQ05.local")
USER = os.environ.get("BOARD_USER", "arduino")
TARGET = os.environ.get("BOARD_TARGET", "auto").lower()
EXTRA_HOST = os.environ.get("BOARD_HOST")

ADB = os.environ.get("ADB") or os.path.expandvars(
    r"%LOCALAPPDATA%\Arduino15\packages\arduino\tools\adb\32.0.0\adb.exe"
)


class BoardLink:
    """One way of reaching the board. `shell_argv(cmd)` is the argv that runs cmd there."""

    def __init__(self, kind, detail, prefix):
        self.kind = kind        # "usb" or "ssh"
        self.detail = detail    # serial number or host
        self._prefix = prefix

    def describe(self):
        return f"{self.kind} ({self.detail})"

    def shell_argv(self, command):
        return self._prefix + [command]

    def run(self, command, timeout=90):
        try:
            p = subprocess.run(self.shell_argv(command), capture_output=True, text=True,
                               timeout=timeout)
            return p.returncode, (p.stdout + p.stderr).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            return 1, str(exc)


def _usb_link():
    if not os.path.exists(ADB):
        return None
    try:
        p = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    serials = [l.split()[0] for l in p.stdout.splitlines()[1:] if l.strip().endswith("device")]
    if not serials:
        return None
    return BoardLink("usb", serials[0], [ADB, "shell"])


def _ssh_link(host, port=22, timeout=3):
    """Only returns a link if the host resolves and port 22 actually accepts a connection."""
    if not shutil.which("ssh"):
        return None
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError:
        return None
    return BoardLink("ssh", host,
                     ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
                      "-o", "ConnectTimeout=5", f"{USER}@{host}"])


def candidates():
    """Every route worth trying, in order, as (label, factory) pairs."""
    routes = []
    if TARGET in ("auto", "usb"):
        routes.append(("usb", _usb_link))
    if TARGET in ("auto", "net"):
        routes.append((f"mdns {MDNS}", lambda: _ssh_link(MDNS)))
        if EXTRA_HOST:
            routes.append((f"host {EXTRA_HOST}", lambda: _ssh_link(EXTRA_HOST)))
    return routes


def connect(verbose=False):
    """First route that works, or None. Never raises."""
    for label, factory in candidates():
        link = factory()
        if verbose:
            print(f"  {'found' if link else 'no  '}: {label}")
        if link:
            return link
    return None


if __name__ == "__main__":
    print(f"looking for the board (BOARD_TARGET={TARGET})")
    link = connect(verbose=True)
    if not link:
        raise SystemExit("\nboard not found on any route")
    code, out = link.run("hostname")
    print(f"\nconnected via {link.describe()} -> {out}")
