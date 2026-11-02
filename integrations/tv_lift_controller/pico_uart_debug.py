from machine import Pin
import rp2
import time

# Keep the lift command MOSFET inactive.
Pin(15, Pin.OUT, value=0)

rx_pin = Pin(14, Pin.IN, Pin.PULL_UP)

@rp2.asm_pio(
    autopush=True,
    push_thresh=8,
    in_shiftdir=rp2.PIO.SHIFT_RIGHT,
    fifo_join=rp2.PIO.JOIN_RX,
)
def uart_rx():
    wait(0, pin, 0)
    set(x, 7) [10]
    label("bitloop")
    in_(pins, 1)
    jmp(x_dec, "bitloop") [6]

sm = rp2.StateMachine(
    1,
    uart_rx,
    freq=8 * 9600,
    in_base=rx_pin
)

print("Reading GP14 UART at 9600 baud for 6 seconds...")
print("No motor commands will be sent.")

sm.active(1)

data = bytearray()
total = 0
start = time.ticks_ms()

while time.ticks_diff(time.ticks_ms(), start) < 6000:
    while sm.rx_fifo():
        value = (sm.get() >> 24) & 0xFF
        total += 1
        if len(data) < 512:
            data.append(value)

sm.active(0)

print()
print("TOTAL BYTES RECEIVED:", total)
print("BYTES SAVED:", len(data))

print()
print("RAW HEX DATA:")
for i in range(0, min(len(data), 192), 16):
    print(" ".join("{:02X}".format(b) for b in data[i:i+16]))

print()
print("FRAME SEARCH:")
found = 0

for i in range(len(data) - 5):
    if data[i] == 0x55 and data[i+1] == 0xAA:
        frame = data[i:i+6]
        msg_type = frame[2]
        raw_height = frame[3] | (frame[4] << 8)
        height = raw_height / 44.0

        print(
            "FRAME:",
            " ".join("{:02X}".format(b) for b in frame),
            "TYPE:", "{:02X}".format(msg_type),
            "HEIGHT:", round(height, 2),
            "STATUS:", "{:02X}".format(frame[5])
        )
        found += 1

        if found >= 15:
            break

print("FRAMES FOUND:", found)
print("DIAGNOSTIC COMPLETE")
