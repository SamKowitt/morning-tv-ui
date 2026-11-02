import serial
import time

PORT = "/dev/ttyACM0"
PRESET1 = 73.00

with serial.Serial(PORT, 115200, timeout=0.15, write_timeout=1) as ser:

    height = None
    moving = None
    last_status_time = 0
    last_printed = None

    def read_status():
        global height, moving, last_status_time, last_printed

        raw = ser.readline()
        if not raw:
            return None

        line = raw.decode("utf-8", "replace").strip()

        if line.startswith("STATUS "):
            try:
                parts = line.split()
                h = float(parts[1])
                m = bool(int(parts[2]))
            except (IndexError, ValueError):
                return None

            if not 60 <= h <= 210:
                return None

            height = h
            moving = m
            last_status_time = time.monotonic()

            displayed = (round(h, 1), m)

            if displayed != last_printed:
                print(
                    "HEIGHT: {:.2f} cm | {}".format(
                        h, "MOVING" if m else "STOPPED"
                    ),
                    flush=True
                )
                last_printed = displayed

            return h, m

        if line.startswith(("SENT", "ERROR", "WATCHDOG")):
            print("PICO:", line, flush=True)

        return None

    def send(command):
        print("COMMAND:", command, flush=True)
        ser.write((command + "\n").encode())
        ser.flush()

    def fresh():
        return time.monotonic() - last_status_time < 1.5

    print("AUTOMATIC DOWNWARD PRESET STOP TEST")
    print("No UP or reversal command will be sent.")
    print()

    # Establish stationary starting position.
    start = time.monotonic()

    while time.monotonic() - start < 2:
        read_status()

    if (
        height is None
        or moving is not False
        or not 80 <= height <= 90
        or not fresh()
    ):
        raise SystemExit(
            "ABORT: Lift must be stationary around 83 cm."
        )

    starting_height = height
    stop_threshold = starting_height - 4.0

    print()
    print("START HEIGHT: {:.2f} cm".format(starting_height))
    print("STOP THRESHOLD: {:.2f} cm".format(stop_threshold))
    print()

    send("WAKE")

    start = time.monotonic()
    while time.monotonic() - start < 0.7:
        read_status()

        if moving is True:
            raise SystemExit(
                "ABORT: Unexpected movement after WAKE."
            )

    if not fresh():
        raise SystemExit("ABORT: Status feedback unavailable.")

    print()
    print("STARTING PRESET 1")
    send("PRESET1")

    stop_sent = False
    deadline = time.monotonic() + 15

    try:
        while time.monotonic() < deadline:
            state = read_status()

            if not fresh():
                print("WARNING: STATUS FEEDBACK LOST")
                break

            if state is None:
                continue

            h, m = state

            if m and h <= stop_threshold:
                print()
                print("TARGET REACHED - SENDING STOP_DOWN")
                send("STOP_DOWN")
                stop_sent = True
                break

            if not m and h <= PRESET1 + 0.5:
                break

    except KeyboardInterrupt:
        print("\nINTERRUPTED")
        if not stop_sent:
            send("STOP_DOWN")
        raise SystemExit(
            "Stop not confirmed. Disconnect motor power "
            "if movement is unsafe."
        )

    if not stop_sent:
        print("WARNING: Test threshold not reached.")
        print("Attempting best-effort STOP_DOWN.")
        send("STOP_DOWN")

    print()
    print("MONITORING STOPPING BEHAVIOR")

    stopped_since = None
    stopped_height = None
    confirmed = False
    deadline = time.monotonic() + 9

    while time.monotonic() < deadline:
        state = read_status()

        if not fresh():
            print("WARNING: STATUS FEEDBACK LOST")
            break

        if state is None:
            continue

        h, m = state

        if m:
            stopped_since = None
            stopped_height = None
        else:
            if (
                stopped_since is None
                or abs(h - stopped_height) > 0.2
            ):
                stopped_since = time.monotonic()
                stopped_height = h

            elif time.monotonic() - stopped_since >= 1.0:
                confirmed = True
                break

    print()
    print("========== FINAL RESULT ==========")

    if height is not None:
        print("FINAL HEIGHT: {:.2f} cm".format(height))

    print("FINAL MOVING:", moving)

    if (
        stop_sent
        and confirmed
        and height is not None
        and height > PRESET1 + 1.5
    ):
        print("SUCCESS: STOP_DOWN STOPPED PRESET MOVEMENT")
    else:
        print("STOP_DOWN NOT VERIFIED")
        print("No reversal command was sent.")
        print("If still moving, keep the path clear.")
        print("Disconnect motor power if movement is unsafe.")

    print("==================================")
