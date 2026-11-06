"""V27: GPU current-hour weather background, original live text."""

import os
from pathlib import Path

from PySide6.QtCore import (
    QObject, QEvent, Qt, QTimer, QUrl, QRectF
)
from PySide6.QtGui import QColor, QPainterPath, QRegion
from PySide6.QtWidgets import QApplication
from PySide6.QtQuickWidgets import QQuickWidget

ASSETS = (
    Path(__file__).resolve().parent
    / "weather_gpu_v26_data/assets"
)

SCENE = (
    Path(__file__).resolve().parent
    / "weather_gpu_v26_data/contained_weather.qml"
)

FLAG = Path.home() / ".config/morningui/gpu_date_v27_enabled"
ACTIVE = Path.home() / ".cache/morningui_gpu_date_v27_active"


class _CurrentWeatherGPU(QObject):
    def __init__(self, card):
        super().__init__(card)

        self.card = card
        self.row = card.background_weather_row
        self.failed = False
        self.pending = False
        self.active = False

        self.view = QQuickWidget(self.row)
        self.view.setObjectName("V27CurrentHourWeatherGPU")
        self.view.setResizeMode(
            QQuickWidget.ResizeMode.SizeRootObjectToView
        )
        self.view.setClearColor(QColor(0, 0, 0, 0))
        self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.view.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self.view.setSource(QUrl.fromLocalFile(str(SCENE)))

        if (
            self.view.rootObject() is None
            or self.view.status() == QQuickWidget.Status.Error
        ):
            raise RuntimeError(
                "Current-hour GPU QML failed: "
                + repr(self.view.errors())
            )

        if self.view.testAttribute(
            Qt.WidgetAttribute.WA_NativeWindow
        ):
            raise RuntimeError(
                "Unexpected native current-hour GPU window"
            )

        self.view.hide()

        self.row.installEventFilter(self)
        self.card.installEventFilter(self)

        self.poll = QTimer(self)
        self.poll.setInterval(800)
        self.poll.timeout.connect(self.check)
        self.poll.start()

        QTimer.singleShot(900, self.check)

    def eventFilter(self, obj, event):
        if (
            obj in (self.card, self.row)
            and event.type() in (
                QEvent.Type.Resize,
                QEvent.Type.Show,
            )
        ):
            self.view.setGeometry(self.row.rect())
            self.schedule(250)

        return False

    def schedule(self, delay=200):
        if self.failed or not FLAG.is_file() or self.pending:
            return

        self.pending = True
        QTimer.singleShot(delay, self.rebuild)

    def disable(self):
        self.view.hide()
        self.active = False
        ACTIVE.unlink(missing_ok=True)

        if not self.row.timer.isActive():
            self.row.timer.start(50)

    def check(self):
        if self.failed or not FLAG.is_file():
            self.disable()
        elif not self.active:
            self.schedule(120)

    def rebuild(self):
        self.pending = False

        if self.failed or not FLAG.is_file():
            self.disable()
            return

        if (
            not self.card.isVisible()
            or self.row.width() < 100
            or self.row.height() < 60
        ):
            return

        try:
            # Snapshot original artwork without the GPU layer.
            self.view.hide()
            QApplication.processEvents()

            image = ASSETS / "v27_current_weather.png"
            image.parent.mkdir(parents=True, exist_ok=True)

            if not self.row.grab().save(str(image), "PNG"):
                raise RuntimeError(
                    "Could not snapshot current weather artwork"
                )

            w = self.row.width()
            h = self.row.height()
            condition = str(self.row.condition).lower()

            self.view.rootObject().setProperty("cards", [{
                "x": 0,
                "y": 0,
                "w": w,
                "h": h,
                "url": (
                    image.as_uri()
                    + "?v="
                    + str(image.stat().st_mtime_ns)
                ),
                "rainy": condition in ("rain", "storm"),
                "cloudy": condition in ("cloud", "fog"),
            }])

            self.view.setGeometry(self.row.rect())

            path = QPainterPath()
            path.addRoundedRect(
                QRectF(2, 2, w - 4, h - 4),
                14,
                14,
            )

            self.view.setMask(
                QRegion(path.toFillPolygon().toPolygon())
            )

            self.view.show()
            self.view.raise_()

            # Preserve the original live clock and text.
            self.card.overlay.raise_()

            if (
                self.view.geometry() != self.row.rect()
                or self.view.testAttribute(
                    Qt.WidgetAttribute.WA_NativeWindow
                )
            ):
                raise RuntimeError(
                    "Current-hour GPU containment failed"
                )

            api = (
                self.view.quickWindow()
                .rendererInterface()
                .graphicsApi()
                .name
            )

            if api != "OpenGL":
                raise RuntimeError(
                    "Current-hour renderer is not OpenGL: " + api
                )

            # Stop only the weather-art animation timer.
            # DateCard's own clock timer remains untouched.
            self.row.timer.stop()
            self.active = True

            ACTIVE.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            ACTIVE.write_text(
                f"{os.getpid()} {w}x{h} {api}\n"
            )

            print(
                "V27_CURRENT_HOUR_GPU_ACTIVE",
                w,
                h,
                api,
                flush=True,
            )

        except Exception as exc:
            self.failed = True

            print(
                "V27_CURRENT_HOUR_GPU_FAILED:",
                repr(exc),
                flush=True,
            )

            self.disable()


def install(cls):
    if getattr(cls, "_v27_current_gpu_installed", False):
        return

    original_init = cls.__init__
    original_update = cls.update_current_weather

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._v27_current_gpu = _CurrentWeatherGPU(self)

    def update_current_weather(self, row):
        result = original_update(self, row)

        gpu = getattr(self, "_v27_current_gpu", None)

        if gpu is not None:
            gpu.schedule(300)

        return result

    cls.__init__ = init
    cls.update_current_weather = update_current_weather
    cls._v27_current_gpu_installed = True
