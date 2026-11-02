from machine import Pin
import time

p = Pin(14, Pin.IN, Pin.PULL_UP)

previous = p.value()
changes = 0
high = 0
low = 0

print("Checking VEVOR status signal on GP14...")

start = time.ticks_ms()

while time.ticks_diff(time.ticks_ms(), start) < 4000:
    value = p.value()

    if value != previous:
        changes += 1
        previous = value

    if value:
        high += 1
    else:
        low += 1

print("SIGNAL TRANSITIONS:", changes)
print("HIGH SAMPLES:", high)
print("LOW SAMPLES:", low)
print("TEST COMPLETE")
