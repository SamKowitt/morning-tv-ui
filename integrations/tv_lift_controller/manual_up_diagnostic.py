import serial
import time

PORT = "/dev/ttyACM0"
last_height = None
last_moving = None

with serial.Serial(PORT, 115200, timeout=0.1, write_timeout=1) as ser:

    def read_status(seconds):
        global last_height, last_moving
        end = time.monotonic() + seconds

        while time.monotonic() < end:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", "replace").strip()

            if line.startswith("STATUS "):
                parts = line.split()
                try:
                    height = float(parts[1])
                    moving = bool(int(parts[2]))
                    last_height = height
                    last_moving = moving
                    print("LIFT: {:.2f} cm | {}".format(
                        height, "MOVING" if moving else "STOPPED"
                    ))
                except (ValueError, IndexError):
                    print("PICO:", line)

            elif line.startswith(("SENT", "ERROR", "WATCHDOG")):
                print("PICO:", line)

    def send(command):
        print("SENDING:", command)
        ser.write((command + "\n").encode())
        ser.flush()

    print("MANUAL UP DIAGNOSTIC")
    print("Checking current height...")
    read_status(2)

    if last_height is None or last_moving is not False:
        raise SystemExit("ABORT: No confirmed stationary feedback")

    if not 75 <= last_height < 139:
        raise SystemExit("ABORT: Height outside safe test range")

    print("\nPreparing controller...")
    send("WAKE")
    read_status(0.7)

    send("UP_RELEASE")
    read_status(0.4)

    print("\nTesting manual UP for up to 1.5 seconds...")

    try:
        start = time.monotonic()

        while time.monotonic() - start < 1.5:
            send("UP_PRESS")
            read_status(0.2)

            if last_height is not None and last_height >= 140:
                print("Height limit reached; ending test.")
                break

    finally:
        print("\nRELEASING UP")
        send("UP_RELEASE")

    print("\nChecking final position and stopping status...")
    read_status(2.5)

    print("\nTEST COMPLETE")
    print("Final height:", last_height)
    print("Final moving:", last_moving)
