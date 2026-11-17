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
    "805600": "REMINDERS HIDE",  # MUI_LG_HIDE_V35
    "805c00": "MARKET TAPE HIDE",
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
state = {"app": None, "menu": None, "webos_ready": False, "confirmed_at": 0.0, "worker_activity": 0.0}
_route_checks = {}
_route_checks_lock = threading.Lock()
_last_nav_time = 0.0
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
    # Never route to an unverified or stale application.
    with state_lock:
        if not state["webos_ready"] or time.monotonic() - state["confirmed_at"] > 8:
            return "UNKNOWN"
        app = state["app"]
        menu = state["menu"]
    if app in (None, "TV_OFFLINE", "UNKNOWN"):
        return "UNKNOWN"
    return "TV" if menu or app != MORNINGUI_APP else "MORNINGUI"


def checked_route():
    global _last_nav_time
    now = time.monotonic()
    if now - _last_nav_time > 15:
        token = str(time.monotonic_ns())
        event = threading.Event()
        with _route_checks_lock:
            _route_checks[token] = event
        try:
            jobs.put_nowait(("ROUTE_CHECK", "__CHECK_APP__ " + token))
        except queue.Full:
            with _route_checks_lock:
                _route_checks.pop(token, None)
            return "UNKNOWN"
        received = event.wait(4.5)
        with _route_checks_lock:
            _route_checks.pop(token, None)
        if not received:
            print("WEBOS ROUTE CHECK TIMED OUT; navigation withheld", flush=True)
            return "UNKNOWN"
    _last_nav_time = time.monotonic()
    return get_route()



# Faster webOS backend. All Bluetooth and lift logic unchanged.
def _mr23_webos_worker_once():
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

    with state_lock:
        state["worker_activity"] = time.monotonic()

    def reader():
        for line in proc.stdout:
            with state_lock:
                state["worker_activity"] = time.monotonic()
            message = line.strip()

            if message.startswith(("APP ", "STATE ")):
                app = message.split(" ", 1)[1]
                with state_lock:
                    previous = state["app"]
                    state["app"] = app
                    state["confirmed_at"] = time.monotonic()
                    if app != previous:
                        state["menu"] = None
                if app != previous:
                    route = "MORNINGUI" if app == MORNINGUI_APP else "LG TV"
                    print(f"ACTIVE APP: {app} -> {route}", flush=True)

            elif message == "READY":
                with state_lock:
                    state["webos_ready"] = True
                print("Persistent webOS connection ready.", flush=True)

            elif message == "OFFLINE":
                with state_lock:
                    state["webos_ready"] = False
                    state["app"] = "TV_OFFLINE"
                    state["menu"] = None
                    state["confirmed_at"] = 0.0
                print("WEBOS OFFLINE - automatic reconnect active", flush=True)

            elif message.startswith("CHECK_OK "):
                token = message.split(" ", 1)[1]
                with _route_checks_lock:
                    event = _route_checks.get(token)
                if event is not None:
                    event.set()

            elif message.startswith("CHECK_FAIL "):
                print("WEBOS route verification failed", flush=True)

            elif message.startswith("SENT "):
                print(
                    "TV COMMAND SENT:",
                    message[5:],
                    flush=True
                )

            elif message:
                print("WEBOS:", message, flush=True)

        # Any worker exit invalidates all cached routing information.
        with state_lock:
            state["webos_ready"] = False
            state["confirmed_at"] = 0.0

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

            with state_lock:
                silent_for = time.monotonic() - state["worker_activity"]
            if silent_for > 45:
                print("WEBOS WORKER SILENT >45s - RESTARTING", flush=True)
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



# MR23_WEBOS_RECOVERY_V1
# Supervise the actual webOS subprocess.
# Recreate it ONLY when it exits or fails.
def tv_worker():
    while not stopping.is_set():
        try:
            _mr23_webos_worker_once()
        except Exception as exc:
            print(
                "WEBOS SESSION FAILED:",
                repr(exc),
                flush=True
            )

        if not stopping.is_set():
            print(
                "WEBOS SESSION LOST - RECONNECTING",
                flush=True
            )
            stopping.wait(2.0)


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
                # MORNINGUI_OLED_PROTECTION_V1
                # Send user activity only; do not alter command routing.
                if code != "000000":
                    try:
                        with socket.socket(
                            socket.AF_UNIX, socket.SOCK_DGRAM
                        ) as oled_s:
                            oled_s.sendto(
                                b"1",
                                f"/home/{OWNER}/.cache/morningui-oled-activity.sock"
                            )
                    except OSError:
                        pass

                # MR23_WHEEL_NAVIGATION_V1
                # Each wheel delta represents real scroll ticks.
                # Process BEFORE ordinary button de-duplication.
                if code.startswith("0000") and code != "000000":
                    steps = int.from_bytes(
                        packet[-1:], "big", signed=True
                    )

                    direction = "UP" if steps > 0 else "DOWN"
                    route = checked_route()

                    for _ in range(abs(steps)):
                        if route == "TV":
                            send_tv(direction)
                        elif route == "MORNINGUI":
                            # MUI_LG_WHEEL_V17: distinguish wheel from D-pad.
                            # Use a dedicated user-owned UNIX datagram socket.
                            # If UI is not listening, preserve legacy arrows.
                            try:
                                with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as wheel_socket:
                                    wheel_socket.sendto(
                                        b"U" if direction == "UP" else b"D",
                                        f"/home/{OWNER}/.cache/morningui-lg-wheel-v17.sock"
                                    )
                            except OSError as wheel_error:
                                print("MUI_LG_WHEEL_V17_FALLBACK", wheel_error, flush=True)
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

                route = (
                    checked_route()
                    if name in KEYS or name in (
                        "REMINDERS HIDE", "MARKET TAPE HIDE"
                    )
                    else get_route()
                )
                print(f"{name} DETECTED -> {route}", flush=True)

                # MUI_LG_HIDE_V35: route only when MorningUI is active.
                if name in ("REMINDERS HIDE", "MARKET TAPE HIDE"):
                    if route == "MORNINGUI":
                        token = (
                            b"R" if name == "REMINDERS HIDE"
                            else b"M"
                        )
                        try:
                            with socket.socket(
                                socket.AF_UNIX, socket.SOCK_DGRAM
                            ) as hide_socket:
                                hide_socket.sendto(
                                    token,
                                    f"/home/{OWNER}/.cache/morningui-lg-wheel-v17.sock"
                                )
                            print(
                                "MUI_LG_HIDE_V35_SENT",
                                name, flush=True
                            )
                        except OSError as exc:
                            print(
                                "MUI_LG_HIDE_V35_SEND_ERROR",
                                name, repr(exc), flush=True
                            )
                    else:
                        print(
                            "MUI_LG_HIDE_V35_IGNORED",
                            name, "route=" + str(route),
                            flush=True
                        )

                elif name in ("BLUE", "RED"):
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
                    elif route == "MORNINGUI":
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
