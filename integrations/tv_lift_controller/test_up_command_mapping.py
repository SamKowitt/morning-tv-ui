import serial
import time

PORT = "/dev/ttyACM0"

height = None
moving = None
last_update = 0
last_display = None

with serial.Serial(PORT, 115200, timeout=0.1, write_timeout=1) as ser:

    def send(command):
        print("COMMAND:", command, flush=True)
        ser.write((command + "\n").encode())
        ser.flush()

    def monitor(seconds):
        global height, moving, last_update, last_display

        end = time.monotonic() + seconds

        while time.monotonic() < end:
            raw = ser.readline()

            if not raw:
                continue

            line = raw.decode("utf-8", "replace").strip()

            if line.startswith("STATUS "):
                try:
                    parts = line.split()
                    new_height = float(parts[1])
                    new_moving = bool(int(parts[2]))

                    height = new_height
                    moving = new_moving
                    last_update = time.monotonic()

                    display = (
                        round(height, 2),
                        moving
                    )

                    if display != last_display:
                        print(
                            "HEIGHT: {:.2f} cm | {}".format(
                                height,
                                "MOVING" if moving else "STOPPED"
                            ),
                            flush=True
                        )
                        last_display = display

                except (IndexError, ValueError):
                    pass

            elif line.startswith(("SENT", "ERROR", "WATCHDOG")):
                print("PICO:", line, flush=True)

    print("MANUAL UP COMMAND MAPPING TEST")
    print()

    monitor(1.5)

    if (
        height is None
        or moving is not False
        or not 72 <= height <= 75
        or time.monotonic() - last_update > 1
    ):
        raise SystemExit(
            "ABORT: Lift must be stationary near 73 cm."
        )

    print()
    print("Sending WAKE...")
    send("WAKE")
    monitor(0.7)

    if moving is not False:
        raise SystemExit("ABORT: Unexpected movement after WAKE.")

    print()
    print("TESTING E1 (currently named UP_RELEASE)")
    print("Maximum test duration: 1 second")

    try:
        start = time.monotonic()

        while time.monotonic() - start < 1.0:
            send("UP_RELEASE")
            monitor(0.15)

            if moving or (height is not None and height > 73.15):
                print("MOVEMENT DETECTED")
                break

            if time.monotonic() - last_update > 1:
                print("STATUS LOST - ENDING TEST")
                break

    finally:
        print()
        print("SENDING E3 (currently named DOWN_RELEASE)")

        for _ in range(3):
            try:
                send("DOWN_RELEASE")
                time.sleep(0.1)
            except Exception as exc:
                print("STOP TRANSMISSION ERROR:", exc)

    print()
    print("MONITORING STOPPING BEHAVIOR")
    monitor(4)

    print()
    print("TEST COMPLETE")
    print("FINAL HEIGHT:", height)
    print("FINAL MOVING:", moving)

    if moving is not False:
        print(
            "WARNING: Lift did not confirm STOPPED. "
            "Disconnect motor power if it continues moving."
        )
