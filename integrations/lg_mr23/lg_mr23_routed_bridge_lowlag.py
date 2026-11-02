import os
import select
import socket
import subprocess
import threading
import queue
import time

from evdev import UInput, ecodes as e

OWNER = os.environ["BRIDGE_OWNER"]
SOCK = os.environ["LIFT_SOCK"]
TV_IP = "192.168.86.43"

BIN = f"/home/{OWNER}/lg-webos-test-venv/bin/bscpylgtvcommand"
WORKDIR = f"/home/{OWNER}/.config/lg-webos-test"

MORNINGUI_APP = "com.webos.app.hdmi1"

BUTTONS = {
    "806100": "BLUE",
    "807200": "RED",
    "807100": "GREEN",
    "804500": "HUB",
    "804000": "UP",
    "804100": "DOWN",
    "800700": "LEFT",
    "800600": "RIGHT",
    "804400": "OK",
    "802800": "BACK",
    "807c00": "HOME",
    "800b00": "INPUT",
    "800900": "MUTE",
    "800200": "VOLUME UP",
    "800300": "VOLUME DOWN",
    "804300": "SETTINGS",
}

KEYS = {
    "UP": e.KEY_UP,
    "DOWN": e.KEY_DOWN,
    "LEFT": e.KEY_LEFT,
    "RIGHT": e.KEY_RIGHT,
    "OK": e.KEY_ENTER,
    "BACK": e.KEY_ESC,
}

TV_KEYS = {
    "UP": "UP",
    "DOWN": "DOWN",
    "LEFT": "LEFT",
    "RIGHT": "RIGHT",
    "OK": "ENTER",
    "BACK": "BACK",
    "HOME": "HOME",
    "INPUT": "__SET_HDMI1__",
    "HUB": "INPUT_HUB",
    "SETTINGS": "QMENU",
    "MUTE": "MUTE",
    "VOLUME UP": "VOLUMEUP",
    "VOLUME DOWN": "VOLUMEDOWN",
}

state_lock = threading.Lock()
state = {"app": None, "menu": None}
stopping = threading.Event()
jobs = queue.Queue(maxsize=24)


def webos(*args, timeout=10):
    return subprocess.run(
        ["runuser", "-u", OWNER, "--", BIN, TV_IP, *args],
        cwd=WORKDIR,
        capture_output=True,
        text=True,
        timeout=timeout
    )


def read_app():
    try:
        result = webos("get_current_app")
        if result.returncode != 0:
            return None

        # Ignore diagnostic messages such as "Connection attempt: 2".
        for line in reversed(result.stdout.splitlines()):
            line = line.strip()
            if line.startswith("com.webos.app."):
                return line

    except Exception as exc:
        print("App check error:", exc, flush=True)

    return None


def app_watcher():
    while not stopping.is_set():
        app = read_app()

        if app:
            with state_lock:
                previous = state["app"]

                if app != previous:
                    state["app"] = app
                    state["menu"] = None

                    route = (
                        "MORNINGUI"
                        if app == MORNINGUI_APP
                        else "LG TV"
                    )

                    print(
                        f"\nACTIVE APP: {app} -> {route}",
                        flush=True
                    )

        stopping.wait(2.0)


def tv_worker():
    while not stopping.is_set():
        try:
            name, button = jobs.get(timeout=0.2)
        except queue.Empty:
            continue

        try:
            result = webos("button", button, timeout=12)

            if result.returncode == 0:
                print("TV COMMAND SENT:", name, flush=True)
            else:
                print(
                    "TV ERROR:",
                    name,
                    (result.stderr or result.stdout)[-300:],
                    flush=True
                )
        except Exception as exc:
            print("TV ERROR:", name, exc, flush=True)
        finally:
            jobs.task_done()


def send_tv(name):
    try:
        jobs.put_nowait((name, TV_KEYS[name]))
    except queue.Full:
        print("TV command queue full", flush=True)


def send_lift(name):
    command = b"UP_SHORT" if name == "BLUE" else b"DOWN_SHORT"

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.sendto(command, SOCK)

        print("LIFT REQUEST SENT:", command.decode(), flush=True)

    except OSError as exc:
        print("LIFT ERROR:", exc, flush=True)


def get_route():
    with state_lock:
        app = state["app"]
        menu = state["menu"]

    if menu or app != MORNINGUI_APP:
        return "TV"

    return "MORNINGUI"



# Faster webOS backend. All Bluetooth and lift logic unchanged.
def tv_worker():
    proc = subprocess.Popen(
        [
            "runuser", "-u", OWNER, "--",
            f"/home/{OWNER}/lg-webos-test-venv/bin/python",
            "-u", "/home/mrkowitt/tv_lift_controller/lg_mr23/lg_mr23_webos_lowlag_worker.py"
        ],
        cwd=WORKDIR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    def reader():
        for line in proc.stdout:
            message = line.strip()

            if message.startswith("APP "):
                app = message[4:]

                with state_lock:
                    previous = state["app"]
                    if app != previous:
                        state["app"] = app
                        state["menu"] = None

                if app != previous:
                    route = (
                        "MORNINGUI"
                        if app == MORNINGUI_APP
                        else "LG TV"
                    )
                    print(
                        f"ACTIVE APP: {app} -> {route}",
                        flush=True
                    )

            elif message == "READY":
                print(
                    "Persistent webOS connection ready.",
                    flush=True
                )

            elif message.startswith("SENT "):
                print(
                    "TV COMMAND SENT:",
                    message[5:],
                    flush=True
                )

            elif message:
                print("WEBOS:", message, flush=True)

    threading.Thread(
        target=reader,
        daemon=True
    ).start()

    try:
        while not stopping.is_set():
            if proc.poll() is not None:
                print(
                    "WEBOS WORKER EXITED. TV commands unavailable.",
                    flush=True
                )
                return

            try:
                name, button = jobs.get(timeout=0.15)
            except queue.Empty:
                continue

            try:
                proc.stdin.write(button + "\n")
                proc.stdin.flush()
            except (OSError, BrokenPipeError) as exc:
                print("WEBOS SEND ERROR:", exc, flush=True)
                return
            finally:
                jobs.task_done()

    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()


def app_watcher():
    # The persistent webOS connection supplies app changes.
    return


# Identify the real TV screen before accepting remote input.
initial_app = read_app()

if not initial_app:
    initial_app = "TV_OFFLINE"
    print("TV offline; Bluetooth bridge remains active.",
          flush=True)

state["app"] = initial_app

print("=== LG MR23 ROUTED BRIDGE ===", flush=True)
print("Initial TV application:", initial_app, flush=True)
print("Initial navigation route:", get_route(), flush=True)

keyboard = UInput(
    {e.EV_KEY: list(set(KEYS.values()))},
    name="LG MR23 MorningUI Bluetooth Bridge"
)

threading.Thread(target=tv_worker, daemon=True).start()
threading.Thread(target=app_watcher, daemon=True).start()

monitor = subprocess.Popen(
    ["stdbuf", "-oL", "btmon", "-i", "hci0"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    bufsize=0
)

buffer = b""
correct_handle = False
last_code = "000000"
last_lift = {"BLUE": -1e9, "RED": -1e9}
last_green = -1e9
last_hub = -1e9

print("\nBluetooth monitoring active.")
print("D-pad routing follows the active TV application.")
print("Ctrl+C stops this test.\n", flush=True)

try:
    while True:
        if monitor.poll() is not None:
            raise RuntimeError("Bluetooth monitor stopped")

        ready, _, _ = select.select(
            [monitor.stdout], [], [], 0.25
        )

        if not ready:
            continue

        chunk = os.read(monitor.stdout.fileno(), 65536)
        if not chunk:
            raise RuntimeError("Bluetooth stream closed")

        buffer += chunk

        while b"\n" in buffer:
            raw, buffer = buffer.split(b"\n", 1)
            line = raw.decode(errors="replace")

            if "ACL Data RX:" in line:
                correct_handle = False

            elif "Handle: 0x0022" in line:
                correct_handle = True

            elif correct_handle and "Data[19]:" in line:
                try:
                    packet = bytes.fromhex(
                        line.split("Data[19]:", 1)[1].strip()
                    )
                except ValueError:
                    continue

                if len(packet) != 19:
                    continue

                code = packet[-3:].hex()

                # MR23_WHEEL_NAVIGATION_V1
                # Each wheel delta represents real scroll ticks.
                # Process BEFORE ordinary button de-duplication.
                if code.startswith("0000") and code != "000000":
                    steps = int.from_bytes(
                        packet[-1:], "big", signed=True
                    )

                    direction = "UP" if steps > 0 else "DOWN"
                    route = get_route()

                    for _ in range(abs(steps)):
                        if route == "TV":
                            send_tv(direction)
                        else:
                            key = KEYS[direction]

                            keyboard.write(e.EV_KEY, key, 1)
                            keyboard.syn()

                            keyboard.write(e.EV_KEY, key, 0)
                            keyboard.syn()

                    print(
                        f"WHEEL {direction} x{abs(steps)} -> {route}",
                        flush=True
                    )

                    continue

                if code == last_code:
                    continue

                last_code = code

                if code == "000000":
                    continue

                name = BUTTONS.get(code)
                if name is None:
                    continue

                route = get_route()
                print(f"{name} DETECTED -> {route}", flush=True)

                if name in ("BLUE", "RED"):
                    now = time.monotonic()
                    if now - last_lift[name] >= 2.0:
                        last_lift[name] = now
                        send_lift(name)

                elif name == "GREEN":
                    now = time.monotonic()
                    if now - last_green >= 1.5:
                        last_green = now
                        print("GREEN: RESTART MORNINGUI", flush=True)
                        subprocess.Popen(
                            ["runuser", "-u", OWNER, "--",
                             f"/home/{OWNER}/.local/bin/morningui-green"],
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )

                elif name == "HUB":
                    now = time.monotonic()
                    if now - last_hub >= 0.7:
                        last_hub = now
                        with state_lock:
                            state["menu"] = "HUB"
                        send_tv(name)

                elif name == "INPUT":
                    with state_lock:
                        state["menu"] = None
                    send_tv(name)

                elif name in ("HOME", "SETTINGS"):
                    with state_lock:
                        state["menu"] = name
                    send_tv(name)

                elif name in ("VOLUME UP", "VOLUME DOWN", "MUTE"):
                    send_tv(name)

                elif name == "BACK" and route == "TV":
                    send_tv("BACK")
                    with state_lock:
                        state["menu"] = None

                elif name in KEYS:
                    if route == "TV":
                        send_tv(name)
                    else:
                        key = KEYS[name]
                        keyboard.write(e.EV_KEY, key, 1)
                        keyboard.syn()
                        keyboard.write(e.EV_KEY, key, 0)
                        keyboard.syn()
                        print(
                            "MORNINGUI KEY SENT:", name,
                            flush=True
                        )

except KeyboardInterrupt:
    print("\nStopping bridge...", flush=True)

except Exception as exc:
    print("BRIDGE ERROR:", exc, flush=True)

finally:
    stopping.set()
    monitor.terminate()

    try:
        monitor.wait(timeout=3)
    except subprocess.TimeoutExpired:
        monitor.kill()
        monitor.wait()

    keyboard.close()
    print("Bridge stopped.", flush=True)
