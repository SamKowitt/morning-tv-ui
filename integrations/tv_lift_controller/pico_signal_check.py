from machine import Pin
import time

# Keep the lift command output inactive
Pin(15, Pin.OUT, value=0)

print("GP14 SIGNAL CHECK - AFTER REWIRING")
print("No motor commands will be sent.")

for name, pull in [
    ("NO PULL", None),
    ("PULL UP", Pin.PULL_UP),
    ("PULL DOWN", Pin.PULL_DOWN)
]:
    if pull is None:
        pin = Pin(14, Pin.IN)
    else:
        pin = Pin(14, Pin.IN, pull)

    time.sleep_ms(200)

    high = 0
    low = 0
    changes = 0
    previous = pin.value()
    start = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start) < 4000:
        current = pin.value()

        if current:
            high += 1
        else:
            low += 1

        if current != previous:
            changes += 1
            previous = current

    print()
    print(name)
    print("HIGH:", high)
    print("LOW:", low)
    print("TRANSITIONS:", changes)

Pin(14, Pin.IN, Pin.PULL_UP)
print("\nFinished.")
