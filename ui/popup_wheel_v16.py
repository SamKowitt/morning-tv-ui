"""Real QApplication wheel-event filter. Only acts while a supported popup is visible."""
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication


class PopupWheelRouterV16(QObject):
    def __init__(self, navigation):
        super().__init__(navigation)
        self.navigation = navigation
        self._popup = None
        self._wheel_unit = 0
        self._remainder = 0
        self._seen = 0
        print("MUI_POPUP_WHEEL_V16_FILTER_INSTALLED", flush=True)

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.Wheel or QApplication.closingDown():
            return False
        angle = int(event.angleDelta().y())
        pixel = int(event.pixelDelta().y()) if not angle else 0
        delta = angle or pixel
        dialog = self.navigation._article_popup()
        kind = type(dialog).__name__ if dialog is not None else "none"
        self._seen += 1
        if self._seen <= 40:
            print("MUI_WHEEL_V16_RX", "target=" + type(watched).__name__,
                  "popup=" + kind, "angle=" + str(angle),
                  "pixel=" + str(pixel), flush=True)
        if kind not in ("WeatherRadarDialog", "OpenNewspaperDialog",
                        "MLBBoxScoreDialog", "ESPNBoxScoreDialog"):
            self._popup = None
            self._remainder = 0
            return False
        if not delta:
            return True
        unit = 120 if angle else 40
        if self._popup != id(dialog) or self._wheel_unit != unit:
            self._popup = id(dialog)
            self._wheel_unit = unit
            self._remainder = 0
        if self._remainder and (self._remainder > 0) != (delta > 0):
            self._remainder = 0
        self._remainder += delta
        amount = min(16, abs(self._remainder) // unit)
        if amount:
            sign = 1 if self._remainder > 0 else -1
            self._remainder -= sign * amount * unit
            direction = -1 if delta > 0 else 1  # Wheel DOWN -> +1.
            for _ in range(amount):
                if kind == "WeatherRadarDialog":
                    if dialog.is_playing:
                        dialog.toggle_playback()
                    if dialog.pixmaps:
                        (dialog.next_frame if direction < 0
                         else dialog.previous_frame)()
                elif kind in ("MLBBoxScoreDialog", "ESPNBoxScoreDialog"):
                    for side in ("left_page", "right_page"):
                        page = getattr(dialog, side, None)
                        body = getattr(page, "body", page)
                        bar = (body.verticalScrollBar() if
                               callable(getattr(body, "verticalScrollBar", None))
                               else None)
                        if bar is not None:
                            step = max(24, int(bar.pageStep() * 0.20))
                            bar.setValue(max(bar.minimum(), min(bar.maximum(),
                                                 bar.value() + direction * step)))
                else:
                    (dialog.next_spread if direction < 0
                     else dialog.previous_spread)()
            print("MUI_WHEEL_V16_STEP", "popup=" + kind,
                  "direction=" + ("DOWN" if direction > 0 else "UP"),
                  "notches=" + str(amount), flush=True)
        # Consume sub-notch input too so one QTextEdit doesn't scroll alone.
        return True
