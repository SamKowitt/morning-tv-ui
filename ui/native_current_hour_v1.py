"""Optional native current-hour card foreground for the existing layer-shell scene.

The DateCard remains authoritative: its original label widgets, clock, forecast,
solar and precipitation update logic are never replaced.  This bridge only
captures those label widgets as alpha-transparent pixels and supplies their
geometry/weather-art parameters to the independent native QML renderer.
"""
from pathlib import Path
import time

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage, QPainter, QRegion
from PySide6.QtWidgets import QLabel

from ui.weather_gpu_v26_helper import (
    _v41_mode, _v5w_mode, _v41_phase, _v6_cloud_speed_multiplier,
    V5W_FLAG,
)
from ui.weather_date_gpu_v27 import SCENE

ROOT = Path.home() / ".cache/morningui_native_hourly_v1"


class CurrentHourBridge:
    def __init__(self, controller):
        self.controller = controller
        self.document = {"show": False}
        self.version = 0
        self.signature = None
        self.next_check = 0.0
        self.native_confirmed = False
        self._gpu_suspended = False
        self._error_count = 0

    def _card(self):
        return getattr(self.controller.panel.window(), "date_card", None)

    def _gpu(self):
        card = self._card()
        return getattr(card, "_v27_current_gpu", None) if card else None

    @staticmethod
    def _is_descendant(child, ancestor):
        while child is not None:
            if child is ancestor:
                return True
            child = child.parentWidget()
        return False

    def update(self):
        now = time.monotonic()
        if now < self.next_check:
            return False
        self.next_check = now + 0.60

        card = self._card()
        gpu = self._gpu()
        if (card is None or gpu is None or not card.isVisible()
                or card.width() < 100 or card.height() < 90
                or getattr(gpu, "source_row", None) is None):
            return False

        # Source-row selection and art classification match the V27 DateCard
        # renderer. The WeatherRow's own text values stay unchanged.
        row = gpu.source_row
        try:
            mode = _v5w_mode(row)
            legacy_mode = _v41_mode(row)
            phase = _v41_phase(row)
            wind = float(_v6_cloud_speed_multiplier(row))
            pt = card.mapToGlobal(QPoint(0, 0))
            dpr = max(1.0, float(card.devicePixelRatioF()))

            labels = []
            for label in card.findChildren(QLabel):
                if self._is_descendant(label, card.background_weather_row):
                    continue
                # The ordinal suffix is a child of the number label; render
                # it once through its parent instead of duplicating it.
                if isinstance(label.parentWidget(), QLabel):
                    continue
                if not label.isVisibleTo(card) or not label.width() or not label.height():
                    continue
                pos = label.mapTo(card, QPoint(0, 0))
                font = label.font()
                pixmap = label.pixmap()
                labels.append((label, pos, (
                    label.objectName(), pos.x(), pos.y(), label.width(), label.height(),
                    label.text(), font.family(), font.pointSizeF(), font.weight(),
                    label.alignment(), label.styleSheet(),
                    pixmap.cacheKey() if pixmap is not None and not pixmap.isNull() else 0,
                )))

            # Never replace the established DateCard until its essential
            # text widgets are visible and fully laid out.
            names = {item[0].objectName() for item in labels}
            essential = {
                "DateDayWeather", "DateCurrentTimeWeather",
                "DateMonthWeather", "DateNumberWeather",
                "DateCurrentWeather",
            }
            if not essential.issubset(names):
                return False

            signature = (
                pt.x(), pt.y(), card.width(), card.height(), dpr,
                mode, legacy_mode, phase, round(wind, 4), V5W_FLAG.is_file(),
                tuple(item[2] for item in labels),
            )
            if signature == self.signature:
                return False

            # Exactly as with the nine hourly cards, draw only foreground
            # widgets onto alpha-transparent PNG; never capture old sky.
            image = QImage(
                max(1, round(card.width() * dpr)),
                max(1, round(card.height() * dpr)),
                QImage.Format.Format_ARGB32_Premultiplied,
            )
            image.setDevicePixelRatio(dpr)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            try:
                for label, pos, _key in labels:
                    painter.save()
                    # Draw widget text and nested ordinal label, but NOT
                    # any window background (which would hide QML artwork).
                    label.render(
                        painter, pos, QRegion(),
                        label.RenderFlag.DrawChildren,
                    )
                    painter.restore()
            finally:
                painter.end()

            new_version = self.version + 1
            filename = ROOT / "current_hour_foreground.png"
            tempfile = ROOT / "current_hour_foreground.new.png"
            if not image.save(str(tempfile), "PNG"):
                raise RuntimeError("Unable to write current-hour foreground PNG")
            tempfile.replace(filename)

            self.signature = signature
            self.version = new_version
            self.document = {
                "show": True,
                "x": pt.x(), "y": pt.y(),
                "w": card.width(), "h": card.height(),
                "condition": mode, "legacy_mode": legacy_mode,
                "phase": phase, "wind": wind,
                "use_v5w": V5W_FLAG.is_file(),
                "scene": SCENE.with_name("V41DateCardNative.qml").as_uri(),
                "url": filename.as_uri() + "?v=" + str(new_version),
            }
            self._error_count = 0
            print("NATIVE_CURRENT_HOUR_FRAME", self.version,
                  mode, phase, card.width(), card.height(),
                  "labels=" + str(len(labels)), flush=True)
            return True
        except Exception as exc:
            self._error_count += 1
            if self._error_count <= 4:
                print("NATIVE_CURRENT_HOUR_CAPTURE_ERROR", repr(exc), flush=True)
            return False

    def suspend_gpu(self):
        if self._gpu_suspended or not self.controller.ready or not self.document.get("show"):
            return
        gpu = self._gpu()
        if gpu is None:
            return
        gpu._mui_native_current_suspended = True
        gpu.poll.stop()
        gpu.view.hide()
        gpu.row.timer.stop()
        self._gpu_suspended = True
        self.native_confirmed = True
        print("NATIVE_CURRENT_HOUR_ACTIVE: original DateCard logic preserved", flush=True)

    def restore_gpu(self):
        if not self._gpu_suspended:
            return
        gpu = self._gpu()
        if gpu is None:
            return
        gpu._mui_native_current_suspended = False
        gpu.poll.start()
        gpu.schedule(0)
        self._gpu_suspended = False
        print("NATIVE_CURRENT_HOUR_GPU_RESTORED", flush=True)
