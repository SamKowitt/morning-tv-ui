"""V26: Contained GPU weather rendering for MorningUI."""

import os
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication

BASE = Path(__file__).resolve().parent / "weather_gpu_v26_data"

ENABLED = (
    Path.home()
    / ".config/morningui/gpu_weather_v26_enabled"
)

ACTIVE = (
    Path.home()
    / ".cache/morningui_gpu_v26_active"
)


class _WeatherGPUState(QObject):
    def __init__(self, panel):
        super().__init__(panel)

        self.panel = panel
        self.failed = False
        self.active = False
        self.pending = False
        self.awaiting_verify = False

        self.view = QQuickWidget(panel)
        self.view.setObjectName("MorningUIV26ContainedGPU")
        self.view.setClearColor(QColor("#172c43"))

        self.view.setResizeMode(
            QQuickWidget.ResizeMode.SizeRootObjectToView
        )

        self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.view.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self.view.setSource(
            QUrl.fromLocalFile(
                str(BASE / "contained_weather.qml")
            )
        )

        if (
            self.view.rootObject() is None
            or self.view.status() == QQuickWidget.Status.Error
        ):
            raise RuntimeError(
                "V26 QML load failed: " + repr(self.view.errors())
            )

        if self.view.testAttribute(
            Qt.WidgetAttribute.WA_NativeWindow
        ):
            raise RuntimeError(
                "V26 unexpectedly created a native window"
            )

        self.view.hide()
        self.panel.installEventFilter(self)

        self.poll = QTimer(self)
        self.poll.setInterval(750)
        self.poll.timeout.connect(self.check)
        self.poll.start()

        QTimer.singleShot(700, self.check)

    def eventFilter(self, obj, event):
        if (
            obj is self.panel
            and event.type() in (
                QEvent.Type.Resize,
                QEvent.Type.Show,
            )
        ):
            self.view.setGeometry(self.panel.rect())

            if ENABLED.is_file() and not self.failed:
                self.schedule(250)

        return False

    def check(self):
        if self.failed or not ENABLED.is_file():
            self.disable()
            return

        if not self.active and not self.awaiting_verify:
            self.schedule(100)

    def schedule(self, delay=200):
        if (
            self.failed
            or not ENABLED.is_file()
            or self.pending
            or self.awaiting_verify
        ):
            return

        self.pending = True
        QTimer.singleShot(delay, self.rebuild)

    def disable(self):
        if not self.view.isHidden():
            self.view.hide()

        if self.active:
            print(
                "V26_GPU_OFF: Original weather rendering resumed",
                flush=True,
            )

        self.active = False

        try:
            ACTIVE.unlink(missing_ok=True)
        except OSError:
            pass

        for row in self.panel.row_widgets:
            if hasattr(row, "_v41_visual_phase"):
                del row._v41_visual_phase
                row.update()
            if not row.timer.isActive():
                row.timer.start(50)

    def verify(self):
        self.awaiting_verify = False

        if self.failed or not ENABLED.is_file():
            self.disable()
            return

        try:
            api = (
                self.view.quickWindow()
                .rendererInterface()
                .graphicsApi()
                .name
            )

            if api != "OpenGL":
                raise RuntimeError(
                    "GPU backend is " + api + ", not OpenGL"
                )

            if self.view.geometry() != self.panel.rect():
                raise RuntimeError(
                    "GPU view differs from panel bounds"
                )

            if self.view.testAttribute(
                Qt.WidgetAttribute.WA_NativeWindow
            ):
                raise RuntimeError(
                    "V26 became a native child window"
                )

            self.active = True

            ACTIVE.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            ACTIVE.write_text(
                f"{os.getpid()} "
                f"{self._last_card_count} "
                f"{api}\n"
            )

            print(
                f"V26_GPU_ACTIVE: "
                f"{self._last_card_count} cards, {api}",
                flush=True,
            )

        except Exception as exc:
            self.failed = True

            print(
                "V26_GPU_FAILED:",
                repr(exc),
                flush=True,
            )

            self.disable()

    def rebuild(self):
        self.pending = False

        if self.failed or not ENABLED.is_file():
            self.disable()
            return

        if (
            not self.panel.isVisible()
            or self.panel.width() < 100
        ):
            return

        try:
            rows = list(self.panel.row_widgets)

            if len(rows) != 9:
                raise RuntimeError(
                    f"Expected nine WeatherRows; found {len(rows)}"
                )

            (BASE / "assets").mkdir(
                parents=True,
                exist_ok=True,
            )

            # Temporarily hide the GPU layer while capturing
            # the underlying original WeatherRow artwork.
            self.view.hide()
            QApplication.processEvents()

            cards = []

            for i, row in enumerate(rows):
                if (
                    not row.isVisible()
                    or row.width() < 30
                    or row.height() < 30
                ):
                    continue

                image = BASE / "assets" / f"card_{i}.png"

                if not _v41_foreground_image(row, image):
                    raise RuntimeError(
                        "Cannot save " + str(image)
                    )
                # MORNINGUI_OLED_WEATHER_TAN_TEXT_V1
                oled_image = BASE / "assets" / f"card_{i}_oled_tan.png"
                if not _v41_foreground_image(row, oled_image, oled_tan=True):
                    raise RuntimeError(
                        "Cannot save OLED text " + str(oled_image)
                    )

                pos = row.mapTo(
                    self.panel,
                    row.rect().topLeft(),
                )

                condition = str(row.condition).lower()

                cards.append({
                    "x": pos.x(),
                    "y": pos.y(),
                    "w": row.width(),
                    "h": row.height(),
                    "url": (
                        image.as_uri()
                        + "?v="
                        + str(image.stat().st_mtime_ns)
                    ),
                    "oledUrl": (
                        oled_image.as_uri() + "?v="
                        + str(oled_image.stat().st_mtime_ns)
                    ),
                    "rainy": condition in ("rain", "storm"),
                    "cloudy": condition in ("cloud", "fog"),
                    "mode": _v41_mode(row),
                    "v5w_mode": _v5w_mode(row),
                    "useV5W": V5W_FLAG.is_file(),
                    "windMultiplier": _v6_cloud_speed_multiplier(getattr(row, "weather_data", None)),
                    "phase": _v41_border_phase(row),
                })

            if not cards:
                raise RuntimeError(
                    "No visible weather rows to snapshot"
                )

            self.view.rootObject().setProperty(
                "cards", cards
            )

            self.view.setGeometry(
                self.panel.rect()
            )

            # V26_ROUNDED_BORDER_CLIP
            # Clip GPU artwork inside the original curved borders.
            from PySide6.QtCore import QRectF
            from PySide6.QtGui import QPainterPath, QRegion

            _mw26_mask = QRegion()
            _mw26_count = 0

            for _mw26_row in rows:
                if (
                    not _mw26_row.isVisible()
                    or _mw26_row.width() < 30
                    or _mw26_row.height() < 30
                ):
                    continue

                _mw26_pt = _mw26_row.mapTo(
                    self.panel,
                    _mw26_row.rect().topLeft()
                )

                _mw26_curve = QPainterPath()

                # Original WeatherRow uses a 16px corner radius.
                # Inset by 2px to expose its original anti-aliased border.
                _mw26_curve.addRoundedRect(
                    QRectF(
                        _mw26_pt.x() + 2,
                        _mw26_pt.y() + 2,
                        _mw26_row.width() - 4,
                        _mw26_row.height() - 4
                    ),
                    14.0,
                    14.0
                )

                _mw26_mask = _mw26_mask.united(
                    QRegion(
                        _mw26_curve.toFillPolygon().toPolygon()
                    )
                )

                _mw26_count += 1

            if _mw26_mask.isEmpty() or _mw26_count != len(cards):
                raise RuntimeError(
                    "V26 rounded border mask validation failed"
                )

            self.view.setMask(_mw26_mask)
            self.view.show()
            self.view.raise_()

            if self.view.geometry() != self.panel.rect():
                raise RuntimeError(
                    "GPU view geometry mismatch"
                )

            # Original animation timers are no longer needed
            # while the GPU layer is displaying the artwork.
            for row in rows:
                row.timer.stop()

            self.awaiting_verify = True
            self._last_card_count = len(cards)

            QTimer.singleShot(
                1800,
                self.verify,
            )

        except Exception as exc:
            self.failed = True

            print(
                "V26_GPU_FAILED:",
                repr(exc),
                flush=True,
            )

            self.disable()


def install(weather_panel_class):
    if getattr(
        weather_panel_class,
        "_mw26_installed",
        False,
    ):
        return

    original_init = weather_panel_class.__init__
    original_update = weather_panel_class.update_weather_rows

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

        self._mw26_state = _WeatherGPUState(self)

    def update(self, rows):
        result = original_update(self, rows)

        state = getattr(
            self,
            "_mw26_state",
            None,
        )

        if state is not None:
            state.schedule(250)

        return result

    weather_panel_class.__init__ = init
    weather_panel_class.update_weather_rows = update
    weather_panel_class._mw26_installed = True

# MORNINGUI_GPU_FOCUS_V27

_v27_old_init = _WeatherGPUState.__init__

def _v27_init(self, panel):
    _v27_old_init(self, panel)

    self._v27_last_selection = None

    self._v27_focus_timer = QTimer(self)
    self._v27_focus_timer.setInterval(100)

    self._v27_focus_timer.timeout.connect(
        lambda: _v27_sync_focus(self)
    )

    self._v27_focus_timer.start()



# V28_IDENTITY_FOCUS_FIX
def _v27_sync_focus(state):
    """Mirror the actual LG remote selected WeatherRow identity."""

    if not state.active:
        return

    item = state.view.rootObject()
    if item is None:
        return

    from PySide6.QtCore import QObject

    root = state.panel.window()

    # RemoteNavigation is a QObject owned by the dashboard.
    controllers = [
        obj
        for obj in root.findChildren(QObject)
        if type(obj).__name__ == "RemoteNavigation"
        and hasattr(obj, "selected_identity")
    ]

    selected = -1

    if len(controllers) == 1:
        identity = controllers[0].selected_identity

        if (
            isinstance(identity, tuple)
            and len(identity) >= 2
            and identity[0] == "weather"
        ):
            for index, row in enumerate(
                state.panel.row_widgets
            ):
                if identity[1] == id(row):
                    selected = index
                    break

    else:
        if not getattr(
            state, "_v28_controller_warning", False
        ):
            print(
                "V28_FOCUS_WARNING: "
                "RemoteNavigation not uniquely found",
                flush=True,
            )

            state._v28_controller_warning = True

    if item.property("selectedIndex") != selected:
        item.setProperty("selectedIndex", selected)

        print(
            "V28_HOURLY_FOCUS_INDEX:",
            selected,
            flush=True,
        )

    state._v27_last_selection = selected



from PySide6.QtWidgets import QWidget
_WeatherGPUState.__init__ = _v27_init

# MORNINGUI_V29_OUTER_HOURLY_FOCUS
# Draw the selected card's border above the masked GPU view.

from PySide6.QtWidgets import QWidget as _V29QWidget
from PySide6.QtGui import QPainter as _V29Painter, QPen as _V29Pen
from PySide6.QtCore import QRectF as _V29RectF, QPoint as _V29Point


class _V29OuterWeatherFocus(_V29QWidget):
    def __init__(self, gpu_state):
        super().__init__(gpu_state.panel)

        self._gpu = gpu_state
        self._index = -1

        self.setObjectName("V29OuterHourlyFocus")

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_NoSystemBackground,
            True,
        )

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(gpu_state.panel.rect())
        self.hide()

        gpu_state.panel.installEventFilter(self)

        self._focus_tick = QTimer(self)
        self._focus_tick.setInterval(100)
        self._focus_tick.timeout.connect(self._sync)
        self._focus_tick.start()

    def eventFilter(self, obj, event):
        if obj is self._gpu.panel and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
        ):
            self.setGeometry(self._gpu.panel.rect())

            if self.isVisible():
                self.raise_()
                self.update()

        return False

    def _sync(self):
        gpu = self._gpu

        if not (
            gpu.active
            and ENABLED.is_file()
            and gpu.view.isVisible()
        ):
            if self.isVisible():
                self.hide()

            self._index = -1
            return

        root = gpu.view.rootObject()

        if root is None:
            return

        try:
            idx = int(root.property("selectedIndex"))
        except (TypeError, ValueError):
            idx = -1

        if idx < 0 or idx >= len(gpu.panel.row_widgets):
            idx = -1
        elif not gpu.panel.row_widgets[idx].isVisible():
            idx = -1

        if idx == -1:
            if self.isVisible():
                self.hide()

            self._index = -1
            return

        if idx != self._index or not self.isVisible():
            self._index = idx

            self.setGeometry(gpu.panel.rect())
            self.show()
            self.raise_()
            self.update()

    def paintEvent(self, event):
        idx = self._index

        if idx < 0 or idx >= len(self._gpu.panel.row_widgets):
            return

        row = self._gpu.panel.row_widgets[idx]

        if not row.isVisible():
            return

        pos = row.mapTo(
            self._gpu.panel,
            _V29Point(0, 0),
        )

        # Match the original RemoteNavigation.SelectionOutline
        # geometry, stroke width, color and corner radius.
        rect = _V29RectF(
            pos.x() - 1,
            pos.y() - 1,
            row.width() + 2,
            row.height() + 2,
        ).adjusted(
            2.0, 2.0, -2.0, -2.0
        )

        painter = _V29Painter(self)

        painter.setRenderHint(
            _V29Painter.RenderHint.Antialiasing,
            True,
        )

        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(
            _V29Pen(
                QColor(255, 236, 137, 255),
                3.2,
            )
        )

        painter.drawRoundedRect(
            rect,
            16.0,
            16.0,
        )

        painter.end()


_v29_old_weather_init = _WeatherGPUState.__init__
_v29_old_weather_rebuild = _WeatherGPUState.rebuild


def _v29_weather_init(self, panel):
    _v29_old_weather_init(self, panel)
    self._v29_outer_focus = _V29OuterWeatherFocus(self)


def _v29_weather_rebuild(self):
    result = _v29_old_weather_rebuild(self)

    # Keep the original-style border above the GPU view,
    # including after weather-data refreshes.
    overlay = getattr(self, "_v29_outer_focus", None)

    if overlay is not None:
        QTimer.singleShot(0, overlay.raise_)
        QTimer.singleShot(0, overlay._sync)

    return result


_WeatherGPUState.__init__ = _v29_weather_init
_WeatherGPUState.rebuild = _v29_weather_rebuild



# MORNINGUI_V41_HOURLY_GPU_RELEASE
# Transparent foreground capture; no old painted sky.
def _v41_foreground_image(row, filename, oled_tan=False):  # MORNINGUI_OLED_WEATHER_TAN_TEXT_V1
    """Draw only foreground text onto an alpha-transparent image."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QImage, QPainter, QFont, QColor

    dpr = max(1.0, float(row.devicePixelRatioF()))
    w = max(1, row.width())
    h = max(1, row.height())

    img = QImage(
        round(w * dpr),
        round(h * dpr),
        QImage.Format.Format_ARGB32_Premultiplied
    )
    img.setDevicePixelRatio(dpr)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)

    dark = (
        _v41_phase(row) == "night"
        or str(getattr(row, "condition", "")).lower()
        in ("rain", "storm")
    )

    try:
        painter.setRenderHint(
            QPainter.RenderHint.TextAntialiasing, True
        )

        for name in (
            "hour_label",
            "temp_label",
            "precipitation_detail_label"
        ):
            label = getattr(row, name, None)

            if (
                label is None
                or not label.isVisibleTo(row)
                or label.width() <= 0
                or label.height() <= 0
            ):
                continue

            value = str(label.text() or "")
            if not value:
                continue

            # Preserve the label's current fitted font.
            painter.save()
            painter.setFont(QFont(label.font()))

            if oled_tan and name in ("hour_label", "temp_label"):
                color = QColor("#ead3a3")
            elif dark:
                color = QColor(255, 255, 255, 255)
            elif name == "hour_label":
                color = QColor(38, 50, 56, 210)
            else:
                color = QColor(38, 50, 56, 255)

            painter.setPen(color)

            # Existing widget geometry and alignment.
            point = label.mapTo(row, QPoint(0, 0))
            rect = label.contentsRect().translated(point)

            # This paints glyphs ONLY; it cannot paint
            # the old QLabel background rectangles.
            painter.drawText(
                rect,
                label.alignment(),
                value
            )
            painter.restore()

        # Sunrise/sunset is drawn directly by WeatherRow.
        solar = str(
            getattr(row, "solar_detail_text", "") or ""
        ).strip()

        if solar:
            _precip, rect = row.detail_text_layout()

            if rect.isValid():
                painter.save()

                font = QFont("Times New Roman")
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)

                painter.setPen(
                    QColor(255, 255, 255, 225)
                    if dark
                    else QColor(31, 45, 54, 235)
                )

                painter.drawText(
                    rect,
                    Qt.AlignmentFlag.AlignLeft |
                    Qt.AlignmentFlag.AlignVCenter,
                    solar
                )
                painter.restore()

    finally:
        painter.end()

    return img.save(str(filename), "PNG")

def _v41_mode(row):
    data = getattr(row, "weather_data", None)

    fields = (
        "detailed_forecast",
        "short_forecast",
        "forecast_text",
        "description",
        "forecast"
    )

    desc = " ".join(
        str(getattr(data, k, "") or "")
        for k in fields
    ).lower()

    basic = str(
        getattr(row, "condition", "clear") or "clear"
    ).lower()

    try:
        code = int(getattr(data, "weather_code", None))
    except (TypeError, ValueError):
        code = None

    import re

    if (
        code in (95, 96, 97, 99)
        or re.search(r"thunder|lightning|t.storm", desc)
        or basic == "storm"
    ):
        return "storm"

    if (
        code in (75, 86)
        or re.search(r"heavy snow|blizzard", desc)
    ):
        return "heavysnow"

    if (
        code in (71, 73, 77, 85, 56, 57, 66, 67)
        or re.search(
            r"snow|flurr|sleet|freezing rain|ice pellets",
            desc
        )
        or basic == "snow"
    ):
        return "snow"

    if (
        code in (45, 48)
        or re.search(r"fog|mist|haze|smoke", desc)
        or basic == "fog"
    ):
        return "fog"

    if (
        code in (65, 82)
        or re.search(
            r"heavy rain|torrential rain|downpour",
            desc
        )
    ):
        return "heavyrain"

    if (
        code in (51, 53, 55, 61, 80)
        or re.search(
            r"drizzle|sprinkl|light rain|chance.*rain",
            desc
        )
    ):
        return "lightrain"

    if (
        code in (63, 81)
        or re.search(r"rain|showers", desc)
        or basic == "rain"
    ):
        return "rain"

    if (
        code == 2
        or re.search(
            r"partly cloud|partly sunny|mostly clear",
            desc
        )
    ):
        return "partly"

    if (
        code == 3
        or re.search(
            r"mostly cloudy|overcast|cloudy|clouds",
            desc
        )
    ):
        return "cloudy"

    if (
        code in (0, 1)
        or re.search(r"clear|sunny|fair", desc)
        or basic == "clear"
    ):
        return "clear"

    return "cloudy" if basic == "cloud" else "clear"



# MORNINGUI_V5W_CONDITION_ADAPTER
V5W_FLAG = Path.home() / ".config/morningui/weather_v5w_enabled"

def _v5w_mode(row):
    import re

    data = getattr(row, "weather_data", None)

    desc = " ".join(
        str(getattr(data, k, "") or "")
        for k in (
            "detailed_forecast",
            "short_forecast",
            "forecast_text",
            "description"
        )
    ).lower()

    basic = str(
        getattr(row, "condition", "") or ""
    ).lower()

    try:
        code = int(getattr(data, "weather_code", None))
    except (ValueError, TypeError):
        code = None

    legacy = _v41_mode(row)

    if (
        basic == "cloud"
        and getattr(
            data, "precipitation_forecast_condition", ""
        ) in ("rain", "snow", "storm")
    ):
        return "cloudy"

    if (
        code in (95, 96, 99)
        or re.search(r"thunder|lightning|t[.-]?storms?", desc)
        or basic == "storm"
    ):
        return "thunderstorms"

    if re.search(r"\bhail\b", desc):
        return "hail"

    if (
        code in (56, 57, 66, 67)
        or re.search(
            r"wintry mix|wintery mix|mixed precip|"
            r"rain.{0,25}snow|snow.{0,25}rain|"
            r"sleet|freezing rain|ice pellets",
            desc
        )
    ):
        return "wintry_mix"

    if (
        code in (75, 86)
        or re.search(
            r"heavy snow|blizzard|snow squall", desc
        )
    ):
        return "heavy_snow"

    if (
        code in (71, 85)
        or re.search(
            r"flurr|light snow|snow flake|snow showers?",
            desc
        )
    ):
        return "flurries"

    if code in (73, 77) or legacy == "snow":
        return "snow"

    if legacy == "fog":
        return "fog"

    if code in (65, 82) or legacy == "heavyrain":
        return "heavy_rain"

    if (
        code in (51, 53, 55, 61, 80)
        or legacy == "lightrain"
    ):
        return "light_rain"

    if legacy == "rain":
        return "rain"

    if (
        code == 1
        or re.search(r"mostly clear|mainly clear", desc)
    ):
        return "mostly_clear"

    if legacy == "partly":
        return "partly_cloudy"

    if legacy == "cloudy":
        return "cloudy"

    return "clear_sky"

def _v41_phase(row):
    """Choose hourly artwork from forecast sunrise/sunset events."""
    from datetime import datetime, timedelta
    import re

    # MORNINGUI_SOLAR_ROW_PHASE_V2
    # Direct forecast: current DateCard.
    # Wrapped forecast: hourly WeatherRow.
    forecast = getattr(row, "weather_data", None)

    if forecast is None:
        forecast = row

    saved_phase = getattr(
        forecast, "_v41_solar_phase", None
    )

    if saved_phase in ("dawn", "day", "dusk", "night"):
        return saved_phase

    data = getattr(row, "weather_data", None)

    def start_of(forecast):
        raw = str(
            getattr(forecast, "forecast_start", "") or ""
        ).strip()
        try:
            return datetime.fromisoformat(
                raw.replace("Z", "+00:00")
            )
        except (TypeError, ValueError):
            return None

    target = start_of(data)
    owner = (
        row.parentWidget()
        if hasattr(row, "parentWidget") else None
    )

    for _ in range(6):
        if owner is None or hasattr(owner, "current_rows"):
            break
        owner = (
            owner.parentWidget()
            if hasattr(owner, "parentWidget") else None
        )

    forecasts = list(
        getattr(owner, "current_rows", []) or []
    )
    if data is not None:
        forecasts.append(data)

    events = set()

    for forecast in forecasts:
        label = str(
            getattr(forecast, "solar_event_label", "")
            or ""
        ).strip().lower()

        if label not in ("sunrise", "sunset"):
            continue

        raw_time = str(
            getattr(forecast, "solar_event_time", "")
            or ""
        ).strip().lower()

        match = re.fullmatch(
            r"(\d{1,2}):(\d{2})\s*([ap]m)?",
            raw_time
        )

        hour_start = start_of(forecast)

        if match is None or hour_start is None:
            continue

        hour = int(match.group(1))
        minute = int(match.group(2))
        meridiem = match.group(3)

        if meridiem:
            if not 1 <= hour <= 12:
                continue
            hour = hour % 12 + (
                12 if meridiem == "pm" else 0
            )

        if not (
            0 <= hour <= 23
            and 0 <= minute <= 59
        ):
            continue

        when = hour_start.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0
        )

        events.add((when, label))

    if target is not None and events:
        ordered = sorted(events)
        hour_end = target + timedelta(hours=1)

        # Keep dawn/dusk for the event's hour.
        within = [
            (moment, kind)
            for moment, kind in ordered
            if target <= moment < hour_end
        ]

        if within:
            return (
                "dawn"
                if within[0][1] == "sunrise"
                else "dusk"
            )

        before = [
            (moment, kind)
            for moment, kind in ordered
            if moment <= target
        ]

        if before:
            return (
                "day"
                if before[-1][1] == "sunrise"
                else "night"
            )

        after = [
            (moment, kind)
            for moment, kind in ordered
            if moment > target
        ]

        if after:
            return (
                "night"
                if after[0][1] == "sunrise"
                else "day"
            )

    # Fallback only when solar-event data is unavailable.
    return (
        "night"
        if bool(getattr(row, "is_night", False))
        else "day"
    )


# V41: use one phase for GPU artwork and QWidget border.
def _v41_border_phase(row):
    phase = _v41_phase(row)
    if getattr(row, "_v41_visual_phase", None) != phase:
        row._v41_visual_phase = phase
        row.update()
    return phase


# MORNINGUI_WIND_CLOUD_BANDS_V1
# Cloud speed from the source forecast hour, not gust speed.
def _v6_cloud_speed_multiplier(forecast):
    import math
    import re

    raw = getattr(forecast, "wind_speed", None)

    if raw is None or isinstance(raw, bool):
        return 1.0

    if isinstance(raw, (int, float)):
        mph = float(raw)
    else:
        text = str(raw).strip().lower()

        if text in ("calm", "calm winds"):
            mph = 0.0
        else:
            text = re.split(
                r"\bgust(?:s|ing)?\b", text, maxsplit=1
            )[0]

            numbers = re.findall(r"\d+(?:\.\d+)?", text)

            if not numbers:
                return 1.0

            mph = float(numbers[0])

            if len(numbers) >= 2 and re.search(r"\bto\b|[-–]", text):
                mph = (mph + float(numbers[1])) / 2.0

            if "km/h" in text or "kmh" in text:
                mph /= 1.609344
            elif "mph" not in text and not text.replace(
                ".", "", 1
            ).isdigit():
                return 1.0

    if not math.isfinite(mph) or mph < 0:
        return 1.0

    rounded = int(math.floor(mph + 0.5))

    bands = (
        (5, 0.50), (9, 0.75), (20, 1.00),
        (25, 1.40), (30, 1.65), (36, 1.90),
        (45, 2.15), (56, 2.35), (72, 2.60),
    )

    for upper, factor in bands:
        if rounded <= upper:
            return factor

    return 3.00
