"""MorningUI OLED protection. Presentation-only."""
import os
import re
import socket
import time
from pathlib import Path

from PySide6.QtCore import QObject, QEvent, QSocketNotifier, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QDialog, QWidget


class Shade(QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("MorningUIOLEDShade")
        self.level = 0
        self.opacity = 0.0  # OLED_FOCUS_V6_STAGED_DIM
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.level == 3:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 255))
        elif self.level == 2:
            painter.fillRect(self.rect(), QColor(0, 0, 0, round(255 * self.opacity)))
        painter.end()



# MORNINGUI_OPAQUE_BLACKOUT_V1
class BlackShade(QWidget):
    """Fully opaque blackout; separate from translucent dimming."""

    def __init__(self, owner):
        super().__init__(owner)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_OpaquePaintEvent,
            True
        )
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("MorningUIOpaqueBlackout")
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(
            self.rect(),
            QColor(0, 0, 0, 255)
        )
        painter.end()


class OLEDProtection(QObject):
    PAPER_COLORS = {
        "#ead6b0": "#293947",
        "#d8b985": "#1d2a37",
        "#f6e9c8": "#253542",
        "#ead3a3": "#202e3b",
        "#d4b073": "#192733",
        "#efdcaf": "#293947",
        "#ecd5a4": "#263542",
        "#e4c48b": "#202e3a",
        "#d9b06f": "#1b2935",
        "#f4e7cf": "#293b49",
        "#241a10": "#d9e2ea",
        "#5a442b": "#bccbd7",
        "#5d3d20": "#a8bac9",
        "#fff1d3": "#18232f",
        "#f6e4bd": "#202c39",
        "#ead4a8": "#1b2733",
        "#fff0d0": "#1b2733",
        "#f3e6c9": "#233341",
        "#fff0cf": "#2b3f50",
        "#24170d": "#dbe5ed",
        "#1b130c": "#dbe5ed",
        "#17100a": "#e4ebef",
        "#2d2419": "#111920",
    }

    def __init__(self, app, main_window):
        super().__init__(app)
        self.app = app
        self.main = main_window

        # OLED_FOCUS_V6_STAGED_DIM
        test = os.environ.get("MORNINGUI_OLED_TEST") == "1"
        unit = 1 if test else 60
        self.dark_at, self.shift_at = 10 * unit, 15 * unit
        self.dim_35_at, self.dim_50_at = 30 * unit, 45 * unit
        self.black_at, self.shift_interval = 90 * unit, 5 * unit
        self.dim_opacity = 0.0

        self.since = time.monotonic()
        self.level = 0
        self.shift = (0, 0)
        self.overlays = {}
        self.black_overlays = {}
        self._styles = {}
        self._popup_origins = {}
        self._remote_woke_at = -999.0
        self._swallow_key_release = False
        self._swallow_mouse_release = False

        page = getattr(main_window, "dashboard_page", None)
        self.layout = page.layout() if page is not None else None
        self.base_margins = None

        if self.layout is not None:
            m = self.layout.contentsMargins()
            self.base_margins = (
                m.left(), m.top(), m.right(), m.bottom()
            )

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.path = Path.home() / ".cache/morningui-oled-activity.sock"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.unlink(missing_ok=True)
        self.sock.bind(str(self.path))
        os.chmod(self.path, 0o600)

        self.notifier = QSocketNotifier(
            self.sock.fileno(), QSocketNotifier.Type.Read, self
        )
        self.notifier.activated.connect(self._remote_input)

        app.installEventFilter(self)
        app.aboutToQuit.connect(self._cleanup)

        self.timer = QTimer(self)
        self.timer.setInterval(250 if test else 1000)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

        print(
            "[OLED] enabled:",
            "TEST 10/15/30/45/90 seconds" if test else "10/15/30/45/90 minutes",
            flush=True
        )

    def _cleanup(self):
        self.notifier.setEnabled(False)
        self.sock.close()
        self.path.unlink(missing_ok=True)

    def _remote_input(self, *args):
        seen = False
        while True:
            try:
                if not self.sock.recv(1024):
                    break
                seen = True
            except BlockingIOError:
                break

        if seen:
            if self.level == 3:
                self._remote_woke_at = time.monotonic()
            self.reset()

    def eventFilter(self, obj, event):
        t = event.type()

        if t in (
            QEvent.Type.KeyPress,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.Wheel,
            QEvent.Type.TouchBegin,
        ):
            remote_wake = (
                t == QEvent.Type.KeyPress
                and time.monotonic() - self._remote_woke_at < 0.25
            )
            black = self.level == 3 or remote_wake

            self.reset()

            if black:
                if t == QEvent.Type.KeyPress:
                    self._swallow_key_release = True
                if t == QEvent.Type.MouseButtonPress:
                    self._swallow_mouse_release = True
                return True

        if t == QEvent.Type.KeyRelease and self._swallow_key_release:
            self._swallow_key_release = False
            return True

        if t == QEvent.Type.MouseButtonRelease and self._swallow_mouse_release:
            self._swallow_mouse_release = False
            return True

        if t in (QEvent.Type.Show, QEvent.Type.Resize):
            if isinstance(obj, QWidget) and not isinstance(obj, Shade):
                if obj is self.main or (
                    isinstance(obj, QDialog) and obj.isWindow()
                ):
                    QTimer.singleShot(0, self._update_shades)

        return False

    def reset(self):
        self.since = time.monotonic()

        if self.level or self.shift != (0, 0):
            self.level = 0
            self._restore_styles()
            self._shift_to((0, 0))
            self._update_shades()
            self._v6_sync_weather_palette()
            print("[OLED] user input: normal display restored", flush=True)

    def _tick(self):
        elapsed = time.monotonic() - self.since
        target, opacity = self._v6_stage(elapsed)
        changed = self.level != target
        dim_changed = self.dim_opacity != opacity
        previous = self.level

        self.level, self.dim_opacity = target, opacity

        if changed:
            if previous == 0 and target >= 1:
                self._apply_dark_styles()
            elif previous >= 1 and target == 0:
                self._restore_styles()

        if changed or dim_changed:
            self._update_shades()
            print(f"[OLED] stage={target} dim={opacity:.0%}", flush=True)

        if target == 2:
            self._shift_to(self._shift_at_elapsed(elapsed))
        elif target < 2 and self.shift != (0, 0):
            self._shift_to((0, 0))

        self._v6_sync_weather_palette()

    def _v6_stage(self, elapsed):
        if elapsed >= self.black_at: return 3, 0.0
        if elapsed >= self.dim_50_at: return 2, 0.50
        if elapsed >= self.dim_35_at: return 2, 0.35
        if elapsed >= self.shift_at: return 2, 0.20
        if elapsed >= self.dark_at: return 1, 0.0
        return 0, 0.0

    def _v6_sync_weather_palette(self):
        from PySide6.QtQuickWidgets import QQuickWidget
        active = self.level >= 1

        for view in self.main.findChildren(QQuickWidget):
            if view.objectName() not in (
                "MorningUIV26ContainedGPU",
                "V27CurrentHourWeatherGPU"
            ):
                continue
            try:
                obj = view.rootObject()
                if obj is not None and obj.property("oledWeatherPalette") != active:
                    obj.setProperty("oledWeatherPalette", active)
            except RuntimeError:
                pass

    def _shift_at_elapsed(self, elapsed):
        # OLED_BOUNDED_SHIFT_V2
        # One discrete position every shift_interval.
        step = max(
            0, int(
                (elapsed - self.shift_at) //
                self.shift_interval
            )
        )
        positions = (
            (12, 0),
            (-12, 0),
            (0, 0),
            (12, -4),
            (-12, -4),
            (0, 0),
        )
        return positions[step % len(positions)]

    def _shift_to(self, xy):
        # Move the complete fixed-size dashboard.
        # NEVER modify layout margins or invalidate layouts.
        from PySide6.QtCore import QPoint

        viewport = getattr(
            self.main, "dashboard_viewport", None
        )
        page = getattr(
            self.main, "dashboard_page", None
        )

        if viewport is None or page is None:
            self.shift = (0, 0)
            return

        # MORNINGUI_OLED_SHIFT_OPEN_POPUPS_V1
        # Approved popups move; unrelated dialogs still block shifting.
        movable_dialog_types = (
            "OpenNewspaperDialog", "WeatherRadarDialog",
            "MLBBoxScoreDialog", "ESPNBoxScoreDialog"
        )
        popups_open = any(
            isinstance(w, QDialog) and w.isVisible()
            and type(w).__name__ not in movable_dialog_types
            for w in self.app.allWidgets()
        )

        on_dashboard = (
            self.main.page_stack.currentWidget()
            is viewport
        )

        if popups_open or not on_dashboard:
            xy = (0, 0)

        # These five widgets define the outer dashboard
        # content boundaries. All other dashboard widgets
        # move automatically with their common parent.
        sections = [
            getattr(self.main, "date_card_container", None),
            getattr(self.main, "weather_panel", None),
            getattr(self.main, "top_row_widget", None),
            getattr(self.main, "middle_row_widget", None),
            getattr(self.main, "bottom_row_widget", None),
        ]

        valid = all(
            isinstance(w, QWidget)
            and w.width() > 0
            and w.height() > 0
            for w in sections
        )

        if valid and xy != (0, 0):
            bounds = []

            for widget in sections:
                point = widget.mapTo(page, QPoint(0, 0))
                bounds.append((
                    point.x(),
                    point.y(),
                    point.x() + widget.width(),
                    point.y() + widget.height()
                ))

            left = min(r[0] for r in bounds)
            top = min(r[1] for r in bounds)
            right = max(r[2] for r in bounds)
            bottom = max(r[3] for r in bounds)

            # Never permit content outside the viewport.
            if (left < 0 or top < 0
                    or right > viewport.width()
                    or bottom > viewport.height()):
                xy = (0, 0)
            else:
                left_space = max(0, left - 2)
                right_space = max(
                    0, viewport.width() - right - 2
                )
                up_space = max(0, top - 2)
                down_space = max(
                    0, viewport.height() - bottom - 2
                )

                dx = max(
                    -left_space,
                    min(right_space, int(xy[0]))
                )
                dy = max(
                    -up_space,
                    min(down_space, int(xy[1]))
                )

                xy = (dx, dy)
        elif not valid:
            xy = (0, 0)

        # The only geometry operation during a shift:
        # move() changes position, NEVER dimensions.
        if page.pos() != QPoint(*xy):
            page.move(*xy)

        # Move approved popups by the same bounded dashboard offset.
        # Keep the original position to prevent cumulative drift.
        movable = [
            w for w in self.app.allWidgets()
            if isinstance(w, QDialog) and w.isVisible()
            and type(w).__name__ in movable_dialog_types
            and w.parentWidget() is self.main
        ]

        for stale in tuple(self._popup_origins):
            if stale not in movable:
                self._popup_origins.pop(stale, None)

        for popup in movable:
            if popup not in self._popup_origins:
                self._popup_origins[popup] = QPoint(popup.pos())

            base = self._popup_origins[popup]
            position = QPoint(base.x() + xy[0], base.y() + xy[1])

            if popup.pos() != position:
                popup.move(position)

        if xy == self.shift:
            return

        self.shift = xy

        # Keep the existing LG remote selection outline
        # aligned with the physically moved dashboard.
        navigation = getattr(
            self.main, "_lg_dpad_navigation", None
        )
        if navigation is not None:
            try:
                identity = navigation.selected_identity
                targets = navigation._targets()
                target = navigation._by_identity(
                    targets, identity
                )

                if target is not None:
                    navigation.last_point = target.center

                    if navigation.outline.isVisible():
                        navigation.outline.setGeometry(
                            target.rect.adjusted(
                                -1, -1, 1, 1
                            )
                        )
            except Exception as error:
                print(
                    "[OLED] Focus alignment warning:",
                    error, flush=True
                )

        print(
            f"[OLED] bounded shift: x={xy[0]} "
            f"y={xy[1]}",
            flush=True
        )

    def _refresh_oled_paper_painters(self):
        modules = {
            "ui.panels.news_card",
            "ui.panels.sports_news_panel",
            "ui.panels.sports_games_panel",
            "ui.panels.weather_radar_dialog",
        }

        for widget in self.app.allWidgets():
            try:
                if type(widget).__module__ in modules:
                    widget.update()
            except RuntimeError:
                pass


    # OLED_CONTRAST_V4
    def _apply_dark_styles(self):
        from ui.newspaper_chrome import set_oled_newspaper_dark
        from ui.oled_text import set_oled_text_dark

        set_oled_newspaper_dark(True)
        set_oled_text_dark(True, self.app)

        for widget in self.app.allWidgets():
            try:
                if type(widget).__name__ == "ConnectedNewspaperSpread":
                    if not widget.property("morningui_oled_dark"):
                        widget.setProperty("morningui_oled_dark", True)
                        widget.update()
            except RuntimeError:
                pass

        self._refresh_oled_paper_painters()

    def _restore_styles(self):
        from ui.newspaper_chrome import set_oled_newspaper_dark
        from ui.oled_text import set_oled_text_dark

        set_oled_newspaper_dark(False)
        set_oled_text_dark(False, self.app)

        for widget in self.app.allWidgets():
            try:
                if type(widget).__name__ == "ConnectedNewspaperSpread":
                    if widget.property("morningui_oled_dark"):
                        widget.setProperty("morningui_oled_dark", False)
                        widget.update()
            except RuntimeError:
                pass

        self._refresh_oled_paper_painters()

    def _update_shades(self):
        visible = [self.main] + [
            w for w in self.app.topLevelWidgets()
            if isinstance(w, QDialog) and w.isVisible()
        ]

        for owner in visible:
            try:
                # MORNINGUI_OPAQUE_BLACKOUT_V1
                # Level 3 uses a dedicated opaque surface.
                # It never depends on transparent compositing.
                if self.level == 3:
                    dim = self.overlays.get(owner)
                    if dim is not None:
                        dim.hide()

                    black = self.black_overlays.get(owner)
                    if black is None:
                        black = BlackShade(owner)
                        self.black_overlays[owner] = black

                    black.setGeometry(owner.rect())
                    black.show()
                    black.raise_()

                    # Paint the solid black frame immediately,
                    # rather than waiting for queued weather
                    # animation paints to complete.
                    black.repaint()
                    continue

                # Hide opaque blackout immediately on wake.
                black = self.black_overlays.get(owner)
                if black is not None:
                    black.hide()

                # Preserve original partial-dimming behavior.
                shade = self.overlays.get(owner)

                if shade is None:
                    shade = Shade(owner)
                    self.overlays[owner] = shade

                shade.setGeometry(owner.rect())
                shade.level = self.level
                shade.opacity = self.dim_opacity

                if self.level == 2:
                    shade.show()
                    shade.raise_()
                    shade.update()
                else:
                    shade.hide()

            except RuntimeError:
                self.overlays.pop(owner, None)
                self.black_overlays.pop(owner, None)


# OLED_PALETTE_TARGETS_V11
_v11_previous_dark = OLEDProtection._apply_dark_styles
_v11_previous_wake = OLEDProtection._restore_styles

def _v11_apply_dark(self, *args, **kwargs):
    result = _v11_previous_dark(self, *args, **kwargs)
    from ui.oled_palette_targets import enable
    enable(self.app)
    return result

def _v11_restore(self, *args, **kwargs):
    from ui.oled_palette_targets import disable
    disable(self.app)
    return _v11_previous_wake(self, *args, **kwargs)

OLEDProtection._apply_dark_styles = _v11_apply_dark
OLEDProtection._restore_styles = _v11_restore
