import serial
import time
from pathlib import Path

PORT = "/dev/ttyACM0"
START_HEIGHT = 73.00
STOP_TEST_HEIGHT = 83.00

# Confirm the corrected STOP_UP mapping is present.
firmware = Path("pico_lift_bridge.py").read_text()
section = firmware.split('elif cmd == "STOP_UP":', 1)

if len(section) != 2:
    raise SystemExit("ABORT: STOP_UP implementation not found.")

stop_code = section[1].split('elif cmd == "STOP_DOWN":', 1)[0]

if "send_op(0xE3)" not in stop_code or "send_op(0xE1)" in stop_code:
    raise SystemExit("ABORT: STOP_UP must send E3 only.")

with serial.Serial(PORT, 115200, timeout=0.2, write_timeout=1) as ser:

    last_status = None
    last_status_time = 0
    last_display = None

    def read_status():
        global last_status, last_status_time, last_display

        raw = ser.readline()
        if not raw:
            return None

        line = raw.decode("utf-8", "replace").strip()

        if line.startswith("STATUS "):
            try:
                fields = line.split()
                h = float(fields[1])
                moving = bool(int(fields[2]))
            except (ValueError, IndexError):
                return None

            if not 60 <= h <= 210:
                return None

            last_status = (h, moving)
            last_status_time = time.monotonic()

            display = (int(h), moving)
            if display != last_display:
                print(
                    "HEIGHT: {:.2f} cm | {}".format(
                        h, "MOVING" if moving else "STOPPED"
                    ),
                    flush=True
                )
                last_display = display

            return last_status

        if line.startswith(("SENT", "ERROR", "WATCHDOG")):
            print("PICO:", line, flush=True)

        return None

    def send(cmd):
        print("COMMAND:", cmd, flush=True)
        ser.write((cmd + "\n").encode())
        ser.flush()

    print("PRESET 2 STOP TEST")
    print("No reverse command will be sent.")
    print()

    # Check initial position.
    start = time.monotonic()
    while time.monotonic() - start < 2:
        read_status()

    if (
        last_status is None
        or last_status[1]
        or abs(last_status[0] - START_HEIGHT) > 1.0
    ):
        raise SystemExit(
            "ABORT: Lift must be stationary near 73 cm."
        )

    # Wake controller.
    send("WAKE")
    start = time.monotonic()

    while time.monotonic() - start < 0.7:
        state = read_status()
        if state and state[1]:
            raise SystemExit("ABORT: Unexpected movement after WAKE.")

    print()
    print("STARTING PRESET 2")
    send("PRESET2")

    # Wait until the lift reaches approximately 83 cm.
    deadline = time.monotonic() + 20

    while time.monotonic() < deadline:
        state = read_status()

        if time.monotonic() - last_status_time > 1.5:
            print("WARNING: Position feedback lost.")
            send("STOP_UP")
            raise SystemExit(
                "TEST ABORTED. Stop not confirmed. "
                "Disconnect motor power if movement is unsafe."
            )

        if state and state[1] and state[0] >= STOP_TEST_HEIGHT:
            break
    else:
        raise SystemExit(
            "ABORT: Expected upward movement was not confirmed."
        )

    print()
    print("SENDING STOP_UP DURING PRESET MOVEMENT")
    send("STOP_UP")

    print()
    print("MONITORING FOR CONFIRMED STOP")

    stopped_since = None
    stopped_height = None
    confirmed = False
    deadline = time.monotonic() + 7

    while time.monotonic() < deadline:
        state = read_status()

        if time.monotonic() - last_status_time > 1.5:
            print("WARNING: Position feedback lost.")
            break

        if state is None:
            continue

        height, moving = state

        if moving:
            stopped_since = None
            stopped_height = None
        else:
            if (
                stopped_since is None
                or abs(height - stopped_height) > 0.2
            ):
                stopped_since = time.monotonic()
                stopped_height = height
            elif time.monotonic() - stopped_since >= 1.0:
                confirmed = True
                break

    print()
    if confirmed:
        print("SUCCESS: PRESET MOVEMENT STOPPED")
        print("FINAL HEIGHT: {:.2f} cm".format(last_status[0]))
        print("FINAL STATUS: STOPPED")
    else:
        print("STOP NOT CONFIRMED")
        print("No reverse command was sent.")
        print("Lift may continue toward Preset 2.")
        print("Keep the travel path clear.")
        print("Disconnect motor power if movement is unsafe.")

    print("TEST COMPLETE")
