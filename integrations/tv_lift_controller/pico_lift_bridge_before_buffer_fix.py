"""MicroPython for Raspberry Pi Pico (RP2040) + our custom RJ45 interface.

GP15: existing open-drain MOSFET gate for RJ45 pin 2 (inverted serial TX)
GP14: existing 12k/22k resistor divider for RJ45 pin 4 (serial status RX)
GP16: existing pin-2 sense line (left as input, unused here)
USB CDC: line commands from Pi 5; STATUS lines back to Pi 5.

Adapted from public 9600-8N1 VEVOR protocol and MicroPython PIO examples.
DO NOT connect RJ45 signals directly to Pico GPIO without interface PCB.
"""
import sys
import time
import select
from machine import Pin
import rp2

BAUD = 9600
TX_MOSFET_GP = 15
RX_STATUS_GP = 14
PIN2_SENSE_GP = 16
STATUS_REPORT_MS = 250
MANUAL_KEEPALIVE_MS = 1000

# MOSFET gate LOW = RJ45 pin 2 logic HIGH (idle).
Pin(TX_MOSFET_GP, Pin.OUT, value=0)
Pin(PIN2_SENSE_GP, Pin.IN, Pin.PULL_UP)
rx_pin = Pin(RX_STATUS_GP, Pin.IN)


@rp2.asm_pio(
    set_init=rp2.PIO.OUT_LOW,
    out_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_RIGHT,
)
def serial_tx_mosfet():
    # Inverted UART: GPIO HIGH turns Q1 on and pulls the RJ45 line LOW.
    pull(block)
    set(x, 7)
    set(pins, 1) [7]         # start bit (LOW on RJ45), eight PIO cycles
    label("bits")
    out(pins, 1) [6]        # inverted serial data, LSB first
    jmp(x_dec, "bits")     # eight cycles per bit
    set(pins, 0) [7]        # stop bit (HIGH on RJ45)


@rp2.asm_pio(
    autopush=True,
    push_thresh=8,
    in_shiftdir=rp2.PIO.SHIFT_RIGHT,
    fifo_join=rp2.PIO.JOIN_RX,
)
def serial_rx():
    # Sample UART at mid-bit; require a stop bit before next start.
    wait(1, pin, 0)
    wrap_target()
    wait(0, pin, 0)
    set(x, 7) [10]
    label("bits")
    in_(pins, 1)
    jmp(x_dec, "bits") [6]
    wait(1, pin, 0)
    wrap()


tx_sm = rp2.StateMachine(
    0, serial_tx_mosfet, freq=8 * BAUD,
    set_base=Pin(TX_MOSFET_GP), out_base=Pin(TX_MOSFET_GP)
)
rx_sm = rp2.StateMachine(
    1, serial_rx, freq=8 * BAUD, in_base=rx_pin
)
tx_sm.active(1)
rx_sm.active(1)

rx_buffer = bytearray()
last_height_cm = None
last_moving = None
last_type = None
last_rx_time = time.ticks_ms()
last_report_time = time.ticks_ms()
manual_direction = None
manual_keepalive_time = time.ticks_ms()


def send_op(code):
    # 55 AA + opcode 3 times. PIO TX is an electrical open drain emulation.
    packet = (0x55, 0xAA, code, code, code)
    for byte in packet:
        tx_sm.put((~byte) & 0xFF)
    # Allow the last queued UART byte to finish.
    time.sleep_ms(7)


def send_state():
    if last_height_cm is not None:
        print("STATUS {:.2f} {} {:02X}".format(
            last_height_cm, int(last_moving), last_type
        ))
    else:
        print("STATUS_UNAVAILABLE")


def drain_status():
    global last_height_cm, last_moving, last_type, last_rx_time
    # Drain FIFO frequently, including between controller commands.
    while rx_sm.rx_fifo():
        rx_buffer.append(rx_sm.get() >> 24)
    # Keep bounded; corrupted bytes get resynchronized on header.
    if len(rx_buffer) > 128:
        del rx_buffer[:-32]
    while len(rx_buffer) >= 6:
        if rx_buffer[0] != 0x55 or rx_buffer[1] != 0xAA:
            del rx_buffer[0]
            continue
        msg_type, lo, hi, flag = rx_buffer[2:6]
        height = ((hi << 8) | lo) / 44.0
        if msg_type in (0xA5, 0xA6, 0xAC, 0xAD) and flag in (0, 4) and 60 <= height <= 210:
            last_height_cm = height
            last_moving = (flag == 4)
            last_type = msg_type
            last_rx_time = time.ticks_ms()
            del rx_buffer[:6]
        else:
            del rx_buffer[0]


def handle_command(raw):
    global manual_direction, manual_keepalive_time
    cmd = raw.strip().upper()
    if not cmd:
        return
    if cmd == "STATUS":
        send_state()
        return
    if cmd == "KEEP":
        if manual_direction:
            manual_keepalive_time = time.ticks_ms()
        return
    if cmd == "WAKE":
        send_op(0xF0)
    elif cmd == "PRESET1":
        manual_direction = None
        send_op(0xD1)
    elif cmd == "PRESET2":
        manual_direction = None
        send_op(0xD2)
    elif cmd == "UP_PRESS":
        send_op(0xE3)
        manual_direction = "UP"
        manual_keepalive_time = time.ticks_ms()
    elif cmd == "UP_RELEASE":
        send_op(0xE1)
        manual_direction = None
    elif cmd == "DOWN_PRESS":
        send_op(0xE2)
        manual_direction = "DOWN"
        manual_keepalive_time = time.ticks_ms()
    elif cmd == "DOWN_RELEASE":
        send_op(0xE3)
        manual_direction = None
    elif cmd == "STOP_UP":
        # Best-effort interruption of running preset: same direction press/release.
        # Protocol does NOT document a dedicated stop opcode. Pi 5 MUST check
        # STATUS reports stopped before attempting reversal.
        manual_direction = None
        send_op(0xE3)
        time.sleep_ms(90)
        send_op(0xE1)
    elif cmd == "STOP_DOWN":
        manual_direction = None
        send_op(0xE2)
        time.sleep_ms(90)
        send_op(0xE3)
    else:
        print("ERROR UNKNOWN_COMMAND", cmd)
        return
    print("SENT", cmd)


poller = select.poll()
poller.register(sys.stdin, select.POLLIN)
print("BRIDGE_READY 9600 GP15_TX_MOSFET GP14_RX_STATUS")

while True:
    drain_status()
    now = time.ticks_ms()
    if last_height_cm is not None and time.ticks_diff(now, last_report_time) >= STATUS_REPORT_MS:
        if time.ticks_diff(now, last_rx_time) <= 1000:
            send_state()
        last_report_time = now
    if manual_direction and time.ticks_diff(now, manual_keepalive_time) > MANUAL_KEEPALIVE_MS:
        send_op(0xE1 if manual_direction == "UP" else 0xE3)
        manual_direction = None
        print("WATCHDOG_RELEASE")
    if poller.poll(0):
        line = sys.stdin.readline()
        if line:
            handle_command(line)
    time.sleep_ms(2)
