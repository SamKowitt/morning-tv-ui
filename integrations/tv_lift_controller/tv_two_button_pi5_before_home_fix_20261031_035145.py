#!/usr/bin/env python3
"""Two-button VEVOR TV lift/TV controller for Raspberry Pi 5.

Button receiver: GPIO17=UP, GPIO27=DOWN (change below if wired differently).
Pico bridge: USB serial /dev/ttyACM0, running pico_lift_bridge.py.
TV: HDMI-CEC (the Pi must be plugged into the TV's intended HDMI 1 input).

Run with --monitor to test without commanding the TV or lift.
Run with --dry-run to exercise actions without transmitting commands.

Safety: reversing preset motion requires confirmed STOPPED feedback; a
best-effort stop pulse alone is never treated as confirmation.
"""
import argparse
import asyncio
import contextlib
import logging
import os
import threading
import time

from gpiozero import DigitalInputDevice
import serial

UP_GPIO = int(os.getenv("TV_UP_GPIO", "17"))
DOWN_GPIO = int(os.getenv("TV_DOWN_GPIO", "27"))
PICO_PORT = os.getenv("TV_PICO_PORT", "/dev/ttyACM0")
LONG_HOLD_SEC = 0.80
DOUBLE_PRESS_IGNORE_SEC = 2.0
REVERSE_PAUSE_SEC = 1.5
STOP_TIMEOUT_SEC = 5.0
STATUS_TIMEOUT_SEC = 1.25
PRESET_TOLERANCE_CM = 0.6
MAX_HOLD_SEC = 45.0
WAKE_AFTER_IDLE_SEC = 18.0
WAKE_PAUSE_SEC = 0.65
PRESET_START_GUARD_SEC = 1.5  # never reverse immediately after a preset was just sent
# Set measured values from your actual programmable memory positions if known.
# If None, repeated preset commands are still safe because the lift manages endpoints.
PRESET1_HEIGHT_CM = 73.00
PRESET2_HEIGHT_CM = 140.73

log = logging.getLogger("tvcontroller")


class LiftLink:
    def __init__(self, port, loop, dry_run=False):
        self.loop = loop
        self.dry_run = dry_run
        self.ser = serial.Serial(port, baudrate=115200, timeout=0.15, write_timeout=1.0)
        self.lock = threading.Lock()
        self.height_cm = None
        self.moving = None
        self.direction = None
        self.last_status = 0.0
        self.last_lift_command = 0.0
        self.last_preset_command = 0.0
        self._reader_running = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self):
        while self._reader_running:
            try:
                line = self.ser.readline().decode(
                    "utf-8", "replace"
                ).strip()

                if not self._reader_running:
                    break

                if line:
                    try:
                        self.loop.call_soon_threadsafe(
                            self._process, line
                        )
                    except RuntimeError:
                        break

            except (
                serial.SerialException,
                OSError,
                TypeError
            ) as exc:
                if self._reader_running:
                    log.error(
                        "Pico serial disconnected: %s", exc
                    )
                break

    def _process(self, line):
        if line.startswith("STATUS "):
            fields = line.split()
            if len(fields) != 4:
                return
            try:
                height = float(fields[1]); moving = bool(int(fields[2]))
                int(fields[3], 16)
            except ValueError:
                return
            if not (60 <= height <= 210):
                return
            if self.height_cm is not None and moving:
                diff = height - self.height_cm
                if diff > 0.035:
                    self.direction = "UP"
                elif diff < -0.035:
                    self.direction = "DOWN"
            if not moving:
                self.direction = None
            changed = (self.moving != moving or self.height_cm is None or
                       abs(height - self.height_cm) >= 0.1)
            self.height_cm, self.moving = height, moving
            self.last_status = time.monotonic()
            if changed:
                log.info("Lift: %.2f cm | %s", height,
                         ("MOVING " + (self.direction or "(direction unknown)")) if moving else "STOPPED")
        elif line.startswith(("ERROR", "WATCHDOG", "BRIDGE_READY", "STATUS_UNAVAILABLE")):
            log.warning("Pico: %s", line)
        elif line.startswith("SENT"):
            log.info("Pico: %s", line)

    def fresh(self):
        return self.height_cm is not None and time.monotonic() - self.last_status < STATUS_TIMEOUT_SEC

    def send(self, command):
        if self.dry_run:
            log.info("[DRY RUN] Pico <- %s", command)
            return
        with self.lock:
            self.ser.write((command + "\n").encode("ascii"))
            self.ser.flush()
        if command != "KEEP":
            self.last_lift_command = time.monotonic()
        if command in ("PRESET1", "PRESET2"):
            self.last_preset_command = time.monotonic()

    async def action(self, command, wake=True):
        if not self.fresh():
            raise RuntimeError("No fresh position/motion data from Pico; movement blocked")
        if wake and self.moving is False:
            if self.last_lift_command == 0 or time.monotonic() - self.last_lift_command >= WAKE_AFTER_IDLE_SEC:
                self.send("WAKE")
                await asyncio.sleep(WAKE_PAUSE_SEC)
        self.send(command)

    def close(self):
        self._reader_running = False

        with contextlib.suppress(Exception):
            self.ser.cancel_read()

        if self._reader.is_alive():
            self._reader.join(timeout=1.0)

        with contextlib.suppress(Exception):
            self.ser.close()


class TV:
    def __init__(self, disabled=False, dry_run=False):
        self.disabled = disabled
        self.dry_run = dry_run
        self.lock = asyncio.Lock()

    async def _cec(self, text):
        if self.disabled:
            log.info("TV disabled: %s", text)
            return
        if self.dry_run:
            log.info("[DRY RUN] TV CEC <- %s", text)
            return
        proc = await asyncio.create_subprocess_exec(
            "cec-client", "-s", "-d", "1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, err = await asyncio.wait_for(
                proc.communicate((text + "\n").encode()), timeout=8
            )
            if proc.returncode:
                log.error("cec-client failed (%d): %s", proc.returncode,
                          err.decode(errors="replace")[-400:])
        except BaseException:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            raise

    async def on_hdmi1(self):
        async with self.lock:
            await self._cec("on 0")
            await asyncio.sleep(0.5)  # give TV time to wake before active-source command
            await self._cec("as")

    async def off(self):
        async with self.lock:
            await self._cec("standby 0")


class Controller:
    def __init__(self, link, tv, loop, monitor_only=False):
        self.link, self.tv, self.loop = link, tv, loop
        self.monitor_only = monitor_only
        self.is_pressed = {"UP": False, "DOWN": False}
        self.press_time = {"UP": 0, "DOWN": 0}
        self.hold_tasks = {"UP": None, "DOWN": None}
        self.hold_triggered = {"UP": False, "DOWN": False}
        self.manual_active = None
        self.action_task = None
        self.action_button = None
        self.last_short = {"UP": 0, "DOWN": 0}

    def down(self, name):
        if self.is_pressed[name]:
            return
        log.info("RF %s HIGH", name)
        self.is_pressed[name] = True
        self.press_time[name] = time.monotonic()
        self.hold_triggered[name] = False
        if self.monitor_only:
            return
        other = "DOWN" if name == "UP" else "UP"
        if self.is_pressed[other]:
            log.warning("Both buttons active; no new commands")
            return
        self.hold_tasks[name] = asyncio.create_task(self._maybe_hold(name))

    def up(self, name):
        if not self.is_pressed[name]:
            return
        self.is_pressed[name] = False
        elapsed = time.monotonic() - self.press_time[name]
        log.info("RF %s LOW (%.3f s)", name, elapsed)
        if self.monitor_only:
            return
        task = self.hold_tasks[name]
        if task and not task.done():
            task.cancel()  # _maybe_hold finally always releases manual motion
        if not self.hold_triggered[name]:
            asyncio.create_task(self._queue_short(name))

    async def _wait_for_recent_preset(self):
        # A preset command can arrive before the status stream reports motion.
        # Do not issue a conflicting movement command during that gap.
        age = time.monotonic() - self.link.last_preset_command
        if 0 <= age < PRESET_START_GUARD_SEC:
            await asyncio.sleep(PRESET_START_GUARD_SEC - age)
        if not self.link.fresh():
            raise RuntimeError("Lift feedback unavailable")

    async def _maybe_hold(self, name):
        try:
            await asyncio.sleep(LONG_HOLD_SEC)
            if not self.is_pressed[name]:
                return
            self.hold_triggered[name] = True
            if self.action_task and not self.action_task.done():
                self.action_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.action_task
            await self._wait_for_recent_preset()
            if self.link.moving and self.link.direction == name:
                log.info("Already moving %s: leaving lift alone", name)
                return
            if self.link.moving:
                if self.link.direction is None:
                    raise RuntimeError("Unknown movement direction; no manual reversal")
                await self._stop_and_wait(self.link.direction)
            if self.is_pressed[name]:
                await self.link.action(name + "_PRESS")
                self.manual_active = name
                log.info("Manual %s begins", name)
            began = time.monotonic()
            while self.is_pressed[name] and self.manual_active == name:
                if not self.link.fresh():
                    raise RuntimeError("Status lost during manual move")
                if time.monotonic() - began > MAX_HOLD_SEC:
                    raise RuntimeError("Manual hold maximum duration reached")
                # GitHub implementation repeats press frames for continuous movement.
                # The Pico updates its watchdog on each repeated press.
                self.link.send(name + "_PRESS")
                await asyncio.sleep(0.20)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.error("Hold aborted: %s", exc)
        finally:
            if self.manual_active == name:
                self.link.send(name + "_RELEASE")
                self.manual_active = None
                log.info("Manual %s released", name)

    async def _queue_short(self, name):
        now = time.monotonic()
        if now - self.last_short[name] < DOUBLE_PRESS_IGNORE_SEC:
            log.info("Duplicate %s ignored", name)
            return
        if self.action_task and not self.action_task.done():
            if self.action_button == name:
                log.info("Already processing %s; repeat ignored", name)
                return
            self.action_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.action_task
        self.last_short[name] = now
        self.action_button = name
        self.action_task = asyncio.create_task(self._short_action(name))

    async def _stop_and_wait(self, moving_direction):
        if moving_direction not in ("UP", "DOWN"):
            raise RuntimeError("Direction unknown; cannot reverse")
        log.warning("Reversing: request best-effort %s STOP", moving_direction)
        self.link.send("STOP_" + moving_direction)
        started = time.monotonic()
        quiet_since = None
        while time.monotonic() - started < STOP_TIMEOUT_SEC:
            await asyncio.sleep(0.08)
            if not self.link.fresh():
                raise RuntimeError("Status lost while stopping; reversal blocked")
            if self.link.moving is False:
                if quiet_since is None:
                    quiet_since = time.monotonic()
                if time.monotonic() - quiet_since >= 0.3:
                    log.info("Confirmed stopped; waiting %.1fs", REVERSE_PAUSE_SEC)
                    await asyncio.sleep(REVERSE_PAUSE_SEC)
                    return
            else:
                quiet_since = None
        raise RuntimeError("Lift did not confirm STOP within 5s; reversal BLOCKED")

    async def _short_action(self, name):
        try:
            await self._wait_for_recent_preset()

            moving = self.link.moving
            direction = self.link.direction

            if moving and direction is None:
                await asyncio.sleep(0.3)
                if not self.link.fresh():
                    raise RuntimeError("Status lost")
                moving = self.link.moving
                direction = self.link.direction
                if moving and direction is None:
                    raise RuntimeError(
                        "Moving but direction unknown; automated action blocked"
                    )

            # Already moving in the requested direction.
            # Do not send another lift command.
            if moving and direction == name:
                log.info(
                    "Same direction already in motion; lift untouched"
                )
                if name == "UP":
                    await self.tv.on_hdmi1()
                else:
                    await self.tv.off()
                return

            # Opposite direction: stop and verify before reversing.
            if moving and direction != name:
                await self._stop_and_wait(direction)

            if not self.link.fresh() or self.link.moving:
                raise RuntimeError(
                    "Lift changed state; preset blocked"
                )

            goal = (
                PRESET2_HEIGHT_CM
                if name == "UP"
                else PRESET1_HEIGHT_CM
            )

            # START LIFT BEFORE WAITING FOR HDMI-CEC.
            if (
                goal is not None
                and abs(self.link.height_cm - goal)
                <= PRESET_TOLERANCE_CM
            ):
                log.info(
                    "Already at preset height; skip lift command"
                )
            else:
                command = (
                    "PRESET2" if name == "UP" else "PRESET1"
                )
                await self.link.action(command)
                log.info("Requested %s preset", name)

            # TV command runs after motor command is issued.
            # The lift moves while HDMI-CEC is processing.
            if name == "UP":
                await self.tv.on_hdmi1()
            else:
                await self.tv.off()

        except asyncio.CancelledError:
            log.warning(
                "%s action canceled by newer input", name
            )
            raise
        except Exception as exc:
            log.error(
                "%s action aborted: %s", name, exc
            )


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monitor", action="store_true", help="Print receiver and lift status only; no actions")
    parser.add_argument("--dry-run", action="store_true", help="Log commands but don't transmit them")
    parser.add_argument("--no-tv", action="store_true", help="Skip HDMI-CEC while testing lift")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    loop = asyncio.get_running_loop()
    link = LiftLink(PICO_PORT, loop, dry_run=args.dry_run)
    tv = TV(disabled=args.no_tv, dry_run=args.dry_run)
    controller = Controller(link, tv, loop, monitor_only=args.monitor)
    up_pin = DigitalInputDevice(UP_GPIO, pull_up=False, bounce_time=0.02)
    down_pin = DigitalInputDevice(DOWN_GPIO, pull_up=False, bounce_time=0.02)
    up_pin.when_activated = lambda: loop.call_soon_threadsafe(controller.down, "UP")
    up_pin.when_deactivated = lambda: loop.call_soon_threadsafe(controller.up, "UP")
    down_pin.when_activated = lambda: loop.call_soon_threadsafe(controller.down, "DOWN")
    down_pin.when_deactivated = lambda: loop.call_soon_threadsafe(controller.up, "DOWN")
    log.info("Controller ready: UP=GPIO%d DOWN=GPIO%d Pico=%s", UP_GPIO, DOWN_GPIO, PICO_PORT)
    log.info("Mode: %s", "MONITOR" if args.monitor else "DRY RUN" if args.dry_run else "LIVE")
    try:
        # Pico streams status automatically.
        while True:
            await asyncio.sleep(1)
            if not link.fresh():
                log.warning("No fresh Pico status; automatic movement disabled until recovered")
    finally:
        for task in list(controller.hold_tasks.values()) + [controller.action_task]:
            if task and not task.done():
                task.cancel()
        if controller.manual_active:
            link.send(controller.manual_active + "_RELEASE")
        up_pin.close(); down_pin.close(); link.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
