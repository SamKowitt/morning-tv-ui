import time
import rp2
from machine import Pin

# Keep the lift command MOSFET inactive.
Pin(15, Pin.OUT, value=0)

# Read-only monitoring of RJ45 pin 4 through GP14.
rx_pin = Pin(14, Pin.IN)

@rp2.asm_pio(
    autopush=True,
    push_thresh=8,
    in_shiftdir=rp2.PIO.SHIFT_RIGHT,
    fifo_join=rp2.PIO.JOIN_RX,
)
def uart_receiver():
    wait(0, pin, 0)
    set(x, 7) [10]
    label("bits")
    in_(pins, 1)
    jmp(x_dec, "bits") [6]

sm = rp2.StateMachine(
    1,
    uart_receiver,
    freq=8 * 9600,
    in_base=rx_pin
)

print("VEVOR GP14 STATUS DIAGNOSTIC")
print("No lift commands will be transmitted.")
print("Initial GP14 level:", rx_pin.value())

samples = 0
high_samples = 0
low_samples = 0
changes = 0
previous = rx_pin.value()
data = bytearray()

sm.active(1)
start = time.ticks_ms()

try:
    while time.ticks_diff(time.ticks_ms(), start) < 5000:
        level = rx_pin.value()
        samples += 1

        if level:
            high_samples += 1
        else:
            low_samples += 1

        if level != previous:
            changes += 1
            previous = level

        while sm.rx_fifo():
            byte = sm.get() >> 24
            if len(data) < 2048:
                data.append(byte)
finally:
    sm.active(0)

print()
print("=== ELECTRICAL SIGNAL ===")
print("Samples:", samples)
print("HIGH samples:", high_samples)
print("LOW samples:", low_samples)
print("Detected transitions:", changes)

print()
print("=== UART DATA ===")
print("Received bytes:", len(data))
print("First 96 bytes:")
print(" ".join("%02X" % b for b in data[:96]))

frames = []
for i in range(len(data) - 5):
    if data[i] == 0x55 and data[i + 1] == 0xAA:
        frames.append(data[i:i+6])

print()
print("=== STATUS FRAMES ===")
print("Found:", len(frames))

for frame in frames[:12]:
    raw = frame[3] | (frame[4] << 8)
    height = raw / 44.0
    print(
        " ".join("%02X" % b for b in frame),
        "| Height:", round(height, 2),
        "| Status:", frame[5]
    )

print()
print("Diagnostic finished.")
