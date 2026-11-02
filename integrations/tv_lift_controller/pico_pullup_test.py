from machine import Pin
import time

# Keep lift command output inactive.
Pin(15, Pin.OUT, value=0)

print("GP14 PULL-UP DIAGNOSTIC")
print("No lift movement commands will be sent.")
print()

tests = [
    ("NO PULL", None),
    ("PULL UP", Pin.PULL_UP),
    ("PULL DOWN", Pin.PULL_DOWN),
]

for name, pull in tests:
    if pull is None:
        pin = Pin(14, Pin.IN)
    else:
        pin = Pin(14, Pin.IN, pull)

    time.sleep_ms(200)

    high = 0
    low = 0
    transitions = 0
    previous = pin.value()

    start = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start) < 3000:
        value = pin.value()

        if value:
            high += 1
        else:
            low += 1

        if value != previous:
            transitions += 1
            previous = value

    print("MODE:", name)
    print("HIGH samples:", high)
    print("LOW samples:", low)
    print("Transitions:", transitions)
    print("-----------------------------")

Pin(14, Pin.IN)

print("Test complete.")
