from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPalette, QPixmap
from PySide6.QtWidgets import QLabel, QHBoxLayout, QStackedLayout, QVBoxLayout, QWidget, QSizePolicy

from ui.auto_fit_label import AutoFitLabel
from ui.panels.weather_panel import (
    WeatherRow,
    weather_emoji_pixmap,
)



class DateCardWeatherIcon(QLabel):
    """Large DateCard weather icon rendered from shared PNG artwork."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.icon = ""
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        oled_style(self, "background: transparent;")
        self.setScaledContents(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_icon_art()

    def refresh_icon_art(self):
        pixmap = weather_emoji_pixmap(
            self.icon,
            self.width(),
            self.height(),
        )

        if pixmap.isNull():
            self.setPixmap(QPixmap())
            return

        self.setPixmap(pixmap)

    def set_icon(self, icon):
        normalized = str(icon or "").replace("\ufe0f", "").strip()
        self.icon = "" if normalized == "🌙" else str(icon or "")
        self.setVisible(bool(self.icon))
        self.refresh_icon_art()


class DateCard(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("DateCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.text_color = "#2f2a24"

        self.background_weather_row = self.create_weather_background()

        self.overlay = QWidget()
        self.overlay.setObjectName("DateCardWeatherOverlay")
        self.overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.weather_icon_overlay = DateCardWeatherIcon(
            self.overlay
        )
        self.weather_icon_overlay.hide()

        overlay_layout = QVBoxLayout()
        overlay_layout.setContentsMargins(14, 8, 12, 12)
        overlay_layout.setSpacing(0)
        self.overlay.setLayout(overlay_layout)

        self.day_label = AutoFitLabel(
            min_size=16,
            max_size=54,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignTop,
            word_wrap=False,
        )
        self.day_label.setObjectName("DateDayWeather")

        self.current_time_label = AutoFitLabel(
            min_size=16,
            max_size=54,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignTop,
            word_wrap=False,
        )
        self.current_time_label.setObjectName("DateCurrentTimeWeather")

        # Keep MON and the clock identical in size. These are deliberately
        # fixed instead of independently auto-fitted.
        self.day_label.set_auto_fit_enabled(False)
        self.current_time_label.set_auto_fit_enabled(False)

        self.day_label.setMinimumHeight(40)
        self.current_time_label.setMinimumHeight(40)

        self.bottom_widget = QWidget()
        self.bottom_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(8)
        self.bottom_widget.setLayout(bottom_row)

        date_block = QVBoxLayout()
        date_block.setContentsMargins(0, 0, 0, 0)
        date_block.setSpacing(0)

        self.month_label = AutoFitLabel(
            min_size=12,
            max_size=24,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignBottom,
            word_wrap=False,
        )
        self.month_label.setObjectName("DateMonthWeather")

        self.date_number_label = AutoFitLabel(
            min_size=34,
            max_size=104,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignTop,
            word_wrap=False,
        )
        self.date_number_label.setObjectName("DateNumberWeather")
        self.date_number_label.setTextFormat(Qt.RichText)
        self.date_number_label.set_auto_fit_enabled(False)
        self.date_number_label.setContentsMargins(10, 0, 0, 0)

        date_block.addWidget(self.month_label, 24)
        date_block.addWidget(self.date_number_label, 76)

        weather_block = QVBoxLayout()
        weather_block.setContentsMargins(0, 0, 0, 2)
        weather_block.setSpacing(0)

        self.current_weather_label = AutoFitLabel(
            "--°",
            min_size=28,
            max_size= 56,
            bold=True,
            alignment=Qt.AlignRight | Qt.AlignBottom,
            word_wrap=False,
        )
        self.current_weather_label.setObjectName("DateCurrentWeather")
        self.current_weather_label.setContentsMargins(0, 0, 20, 0)
        self.current_weather_label.set_auto_fit_enabled(False)
        self.current_weather_label.setMinimumHeight(38)
        _mui_temp_font = QFont(self.current_weather_label.font())
        _mui_temp_font.setPointSize(26)
        _mui_temp_font.setBold(True)
        self.current_weather_label.setFont(_mui_temp_font)

        self.low_high_label = AutoFitLabel(
            "H --°  L --°",
            min_size=18,
            max_size= 36,
            bold=True,
            alignment=Qt.AlignRight | Qt.AlignBottom,
            word_wrap=False,
        )
        self.low_high_label.setObjectName("DateLowHighWeather")

        self.footer_overlay = QWidget(self.overlay)
        self.footer_overlay.setAttribute(Qt.WA_StyledBackground, False)
        self.footer_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(0)
        self.footer_overlay.setLayout(footer_row)

        footer_row.addStretch(1)
        footer_row.addWidget(
            self.low_high_label,
            0,
            Qt.AlignRight | Qt.AlignBottom,
        )
        self.footer_overlay.hide()

        self.precipitation_widget = QWidget()
        self.precipitation_widget.setObjectName("DatePrecipitationWeather")

        precipitation_layout = QHBoxLayout()
        precipitation_layout.setContentsMargins(0, 0, 0, 0)
        precipitation_layout.setSpacing(1)
        self.precipitation_widget.setLayout(precipitation_layout)

        self.precipitation_emoji_label = QLabel()
        self.precipitation_emoji_label.setObjectName(
            "DatePrecipitationEmojiWeather"
        )
        self.precipitation_emoji_label.setAlignment(Qt.AlignCenter)
        self.precipitation_emoji_label.setFixedSize(18, 18)
        oled_style(self.precipitation_emoji_label, 
            "background: transparent;"
        )
        self.precipitation_emoji_label.setScaledContents(False)

        self.precipitation_detail_label = AutoFitLabel(
            "",
            min_size=13,
            max_size=26,
            bold=True,
            alignment=Qt.AlignRight | Qt.AlignVCenter,
            word_wrap=False,
        )
        self.precipitation_detail_label.setObjectName(
            "DatePrecipitationDetailWeather"
        )

        precipitation_layout.addStretch(1)
        precipitation_layout.addWidget(self.precipitation_emoji_label, 0)
        precipitation_layout.addWidget(self.precipitation_detail_label, 0)

        self.precipitation_widget.hide()

        self.solar_detail_label = AutoFitLabel(
            "",
            min_size=12,
            max_size=22,
            bold=True,
            alignment=Qt.AlignRight | Qt.AlignTop,
            word_wrap=False,
        )
        self.solar_detail_label.setObjectName("DateSolarDetailWeather")
        self.solar_detail_label.hide()

        weather_block.addStretch(1)
        weather_block.addWidget(self.current_weather_label, 0)
        weather_block.addWidget(self.precipitation_widget, 0)
        weather_block.addWidget(self.solar_detail_label, 0)
        weather_block.addStretch(1)

        bottom_row.addLayout(date_block, 64)
        bottom_row.addLayout(weather_block, 36)

        overlay_layout.addWidget(self.day_label, 1)
        overlay_layout.addWidget(self.current_time_label, 1)
        overlay_layout.addStretch(2)
        overlay_layout.addWidget(self.bottom_widget, 0)

        self.stacked = QStackedLayout()
        self.stacked.setContentsMargins(0, 0, 0, 0)
        self.stacked.setStackingMode(QStackedLayout.StackAll)
        self.setLayout(self.stacked)

        self.stacked.addWidget(self.background_weather_row)
        self.stacked.addWidget(self.overlay)

        self.stacked.setCurrentWidget(self.overlay)
        self.background_weather_row.lower()
        self.overlay.raise_()

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.refresh_clock)

        self.update_date()
        self.schedule_next_clock_refresh()
        self.set_day_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        bottom_height = max(88, int(self.height() * 0.46))
        self.bottom_widget.setFixedHeight(bottom_height)

        self.sync_day_and_time_font_sizes()
        self.apply_text_color()
        self.position_footer_overlay()
        self.position_weather_icon_overlay()
        self.overlay.raise_()
        self.weather_icon_overlay.raise_()
        self.footer_overlay.raise_()

    def position_weather_icon_overlay(self):
        if not hasattr(self, "weather_icon_overlay"):
            return

        icon_width = max(
            100,
            int(self.width() * 0.34),
        )
        icon_height = max(
            72,
            int(self.height() * 0.26),
        )

        # Draft target:
        # center at approximately 52% of the card width and
        # 66% of the card height.
        icon_x = int(self.width() * 0.35) - 14
        icon_y = int(self.height() * 0.53)

        icon_x = min(
            max(0, icon_x),
            max(0, self.width() - icon_width),
        )
        icon_y = min(
            max(0, icon_y),
            max(0, self.height() - icon_height),
        )

        self.weather_icon_overlay.setGeometry(
            icon_x,
            icon_y,
            icon_width,
            icon_height,
        )
        self.weather_icon_overlay.raise_()

    def position_footer_overlay(self):
        if not hasattr(self, "footer_overlay"):
            return

        footer_height = max(31, int(self.height() * 0.075))
        left_margin = 14
        right_margin = 12
        bottom_offset = 4

        self.footer_overlay.setGeometry(
            left_margin,
            max(0, self.height() - footer_height - bottom_offset),
            max(0, self.width() - left_margin - right_margin),
            footer_height,
        )
        self.footer_overlay.show()
        self.footer_overlay.raise_()

    def preserve_weather_background_label_geometry(self, row):
        """Keep the painted weather-icon anchor active without showing text."""
        icon_label = getattr(row, "icon_label", None)

        geometry_labels = (
            getattr(row, "hour_label", None),
            icon_label,
            getattr(row, "temp_label", None),
        )

        for label in row.findChildren(QLabel):
            if label is icon_label:
                # WeatherRow paints the emoji itself using this label's
                # geometry, so the empty anchor must remain in the layout.
                label.setText("")
                oled_style(label, "background: transparent;")
                label.show()

            elif label in geometry_labels:
                # Preserve the original WeatherRow proportions while keeping
                # its built-in hour and temperature text invisible.
                oled_style(label, 
                    "color: transparent; background: transparent;"
                )
                label.show()

            else:
                label.hide()

        if row.layout() is not None:
            row.layout().activate()

        row.updateGeometry()
        row.update()

    def create_weather_background(self):
        try:
            row = WeatherRow("--", "🌤️", "now", "clear", False)
        except TypeError:
            row = WeatherRow("--", "🌤️", "now", "clear")

        row.setObjectName("DateWeatherBackground")
        row.setAttribute(Qt.WA_StyledBackground, True)

        row.moon_x_ratio = 0.84
        row.moon_y_ratio = 0.17

        # The DateCard displays its weather emoji through a separate,
        # larger painted overlay. Prevent WeatherRow from also painting
        # its normal small hourly icon.
        row.icon = ""

        self.preserve_weather_background_label_geometry(row)

        return row

    def update_date(self):
        now = datetime.now()
        self.day_label.setText(now.strftime("%a").upper())
        self.current_time_label.setText(
            now.strftime("%-I:%M %p").lstrip("0")
        )
        self.month_label.setText(now.strftime("%B"))
        _day = now.day
        _suffix = (
            "th" if 11 <= _day % 100 <= 13
            else {1: "st", 2: "nd", 3: "rd"}.get(_day % 10, "th")
        )
        self.date_number_label.setText(
            f'<span style="font-size:38pt; font-weight:700">{_day}</span>'
            f'<sup style="font-size:16pt; font-weight:700">{_suffix}</sup>'
        )

        self.sync_day_and_time_font_sizes()
        self.apply_text_color()
        self.position_footer_overlay()
        self.overlay.raise_()

    def sync_day_and_time_font_sizes(self):
        # Match the two top lines exactly. The point size scales with the
        # card height but is never reduced because the clock text is wider.
        point_size = max(24, min(46, int(self.height() * 0.18)))

        for label in [
            self.day_label,
            self.current_time_label,
        ]:
            font = QFont(label.font())
            font.setPointSize(point_size)
            font.setBold(True)
            label.setFont(font)


    def refresh_clock(self):
        self.update_date()
        self.schedule_next_clock_refresh()

    def schedule_next_clock_refresh(self):
        now = datetime.now()
        milliseconds = (
            ((60 - now.second) * 1000)
            - int(now.microsecond / 1000)
            + 25
        )
        self.timer.start(max(250, milliseconds))

    def update_current_weather(self, row):
        display_icon = (
            "⚡️"
            if str(row.condition or "").strip().lower() == "storm"
            else row.icon
        )

        self.background_weather_row.update_weather(
            temperature=row.temperature,
            icon="",
            time_label=row.time_label or "now",
            condition=row.condition,
            is_night=row.is_night,
            moon_datetime=datetime.now().astimezone(),
        )

        self.background_weather_row.icon = ""

        self.preserve_weather_background_label_geometry(
            self.background_weather_row
        )

        self.weather_icon_overlay.set_icon(display_icon)
        self.position_weather_icon_overlay()

        self.current_weather_label.setText(f"{row.temperature}°")
        self.update_precipitation_indicator(row)
        self.update_solar_indicator(row)

        low = (
            getattr(row, "low_temperature", None)
            or getattr(row, "low_temp", None)
            or getattr(row, "daily_low", None)
            or getattr(row, "low", None)
        )

        high = (
            getattr(row, "high_temperature", None)
            or getattr(row, "high_temp", None)
            or getattr(row, "daily_high", None)
            or getattr(row, "high", None)
        )

        if low is not None and high is not None:
            self.set_low_high(low, high)

        if row.is_night:
            self.set_night_text()
        else:
            self.set_day_text()

        self.stacked.setCurrentWidget(self.overlay)
        self.background_weather_row.lower()
        self.overlay.raise_()

    def update_precipitation_indicator(self, row):
        precipitation_condition = str(
            getattr(row, "precipitation_forecast_condition", "")
            or getattr(row, "condition", "")
            or ""
        ).strip().lower()

        precipitation_emoji = {
            "rain": "💧",
            "snow": "❄️",
            "storm": "⚡️",
        }.get(precipitation_condition, "")

        try:
            precipitation_amount = float(
                getattr(row, "precipitation_amount_inches", None)
            )
        except (TypeError, ValueError):
            precipitation_amount = 0.0

        precipitation_detail_parts = []

        try:
            precipitation_probability = int(
                getattr(row, "precipitation_probability", None)
            )
        except (TypeError, ValueError):
            precipitation_probability = None

        if precipitation_amount > 0.01:
            precipitation_text = (
                f"{precipitation_amount:.2f}".rstrip("0").rstrip(".")
            )
            precipitation_detail_parts.append(f'{precipitation_text}"')

        if (
            precipitation_emoji
            and precipitation_probability is not None
        ):
            precipitation_detail_parts.append(
                f"{max(0, min(100, precipitation_probability))}%"
            )

        precipitation_detail = "  ".join(precipitation_detail_parts)

        if precipitation_emoji and precipitation_detail:
            precipitation_pixmap = weather_emoji_pixmap(
                precipitation_emoji,
                16,
                16,
            )
            self.precipitation_emoji_label.setPixmap(
                precipitation_pixmap
            )
            self.precipitation_detail_label.setText(precipitation_detail)
            self.precipitation_widget.show()
        else:
            self.precipitation_emoji_label.setPixmap(QPixmap())
            self.precipitation_detail_label.setText("")
            self.precipitation_widget.hide()

        self.apply_text_color()

    def update_solar_indicator(self, row):
        solar_event_time = str(
            getattr(row, "solar_event_time", "") or ""
        ).strip()

        solar_event_label = str(
            getattr(row, "solar_event_label", "") or ""
        ).strip().lower()

        if solar_event_time:
            if solar_event_label in {"sunrise", "sunset"}:
                self.solar_detail_label.setText(
                    f"{solar_event_time} {solar_event_label}"
                )
            else:
                self.solar_detail_label.setText(solar_event_time)

            self.solar_detail_label.show()
        else:
            self.solar_detail_label.setText("")
            self.solar_detail_label.hide()

        self.apply_text_color()

    def update_solar_indicator_from_rows(self, rows):
        for row in rows or []:
            solar_event_time = str(
                getattr(row, "solar_event_time", "") or ""
            ).strip()

            if solar_event_time:
                self.update_solar_indicator(row)
                return

        self.update_solar_indicator(None)

    def set_low_high(self, low, high):
        low_text = str(low).replace("°", "")
        high_text = str(high).replace("°", "")
        self.low_high_label.setText(f"H {high_text}°  L {low_text}°")
        self.apply_text_color()

    def update_low_high_from_rows(self, rows):
        rows = list(rows or [])

        for row in rows:
            low = (
                getattr(row, "low_temperature", None)
                or getattr(row, "low_temp", None)
                or getattr(row, "daily_low", None)
                or getattr(row, "low", None)
            )

            high = (
                getattr(row, "high_temperature", None)
                or getattr(row, "high_temp", None)
                or getattr(row, "daily_high", None)
                or getattr(row, "high", None)
            )

            if low is not None and high is not None:
                self.set_low_high(low, high)
                return

        temperatures = []

        for row in rows:
            try:
                temperatures.append(int(float(str(row.temperature).replace("°", ""))))
            except Exception:
                pass

        if not temperatures:
            self.low_high_label.setText("H --°  L --°")
            self.apply_text_color()
            return

        self.set_low_high(min(temperatures), max(temperatures))

    def force_label_color(self, label, color):
        oled_style(label, f"color: {color};")

        palette = label.palette()
        qcolor = QColor(color)
        palette.setColor(QPalette.WindowText, qcolor)
        palette.setColor(QPalette.Text, qcolor)
        palette.setColor(QPalette.ButtonText, qcolor)
        label.setPalette(palette)

    def apply_text_color(self):
        for label in [
            self.day_label,
            self.current_time_label,
            self.month_label,
            self.date_number_label,
            self.current_weather_label,
            self.low_high_label,
            self.precipitation_detail_label,
            self.solar_detail_label,
        ]:
            self.force_label_color(label, self.text_color)

    def set_night_text(self):
        self.text_color = "#ffffff"
        self.apply_text_color()

    def set_day_text(self):
        self.text_color = "#2f2a24"
        self.apply_text_color()
# OLED_CONTRAST_V4
from ui.oled_text import oled_text_draw, oled_style, oled_html, oled_layout_draw

# MORNINGUI_WEATHER_V13_START

from PySide6.QtWidgets import QLabel as _MW13Label
from PySide6.QtCore import Qt as _MW13Qt, QTimer as _MW13Timer
from PySide6.QtGui import QFont as _MW13Font, QFontMetrics as _MW13Metrics
from ui.oled_text import oled_style as _mw13_oled_style
from datetime import datetime as _MW13Datetime

_mw13_old_update_date = DateCard.update_date
_mw13_old_apply_color = DateCard.apply_text_color
_mw13_old_resize = DateCard.resizeEvent

def _mw13_position_suffix(self):
    label = getattr(self, "date_number_label", None)
    suffix = getattr(self, "_mw13_suffix", None)

    if label is None or suffix is None or label.width() < 5:
        return

    day = _MW13Datetime.now().day
    number_font = _MW13Font(label.font())
    rect = label.contentsRect()
    available = max(1, rect.width())

    # Keep the original automatically fitted number size.
    # Only reduce it when a two-digit date needs suffix space.
    for _ in range(70):
        number_metrics = _MW13Metrics(number_font)
        suffix_font = _MW13Font(number_font)

        suffix_font.setPointSize(
            max(
                10,
                max(21, min(30, round(number_font.pointSizeF() * 0.82)))
            )
        )

        suffix_metrics = _MW13Metrics(suffix_font)

        required = (
            number_metrics.horizontalAdvance(str(day))
            + 3
            + suffix_metrics.horizontalAdvance(suffix.text())
        )

        if required <= available or number_font.pointSize() <= 25:
            break

        number_font.setPointSize(number_font.pointSize() - 1)

    if number_font.pointSize() != label.font().pointSize():
        label.set_auto_fit_enabled(False)
        label.setFont(number_font)

    suffix.setFont(suffix_font)

    x = (
        rect.left()
        + number_metrics.horizontalAdvance(str(day))
        + 3
    )

    y = rect.top() + 12

    suffix.setGeometry(
        x,
        y,
        max(
            1,
            min(
                suffix_metrics.horizontalAdvance(suffix.text()) + 4,
                label.width() - x,
            )
        ),
        max(16, suffix_metrics.height() + 2),
    )

    suffix.show()
    suffix.raise_()

def _mw13_update_date(self):
    _mw13_old_update_date(self)

    label = self.date_number_label
    day = _MW13Datetime.now().day

    # Restore the original plain-number AutoFitLabel.
    label.setTextFormat(_MW13Qt.PlainText)
    label.set_auto_fit_enabled(True)
    label.setText(str(day))

    suffix = getattr(self, "_mw13_suffix", None)

    if suffix is None:
        suffix = _MW13Label(label)
        suffix.setAttribute(
            _MW13Qt.WA_TransparentForMouseEvents,
            True
        )
        suffix.setAutoFillBackground(False)
        suffix.setAlignment(
            _MW13Qt.AlignLeft | _MW13Qt.AlignTop
        )
        self._mw13_suffix = suffix

    suffix_text = (
        "th"
        if 11 <= day % 100 <= 13
        else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    )

    suffix.setText(suffix_text)

    _mw13_oled_style(
        suffix,
        f"color: {self.text_color}; background: transparent;"
    )

    _mw13_position_suffix(self)

    _MW13Timer.singleShot(
        0,
        lambda: _mw13_position_suffix(self)
    )

def _mw13_apply_text_color(self):
    _mw13_old_apply_color(self)

    label = getattr(self, "current_weather_label", None)

    if label is not None:
        # Restore the previous horizontal position.
        label.setContentsMargins(0, 0, 20, 0)

        # Actually enlarge the rendered text, not just AutoFit limits.
        label.set_auto_fit_enabled(False)
        label.setMinimumHeight(46)

        font = _MW13Font(label.font())
        font.setPointSize(32)
        font.setBold(True)
        label.setFont(font)

        _mw13_oled_style(
            label,
            f"color: {self.text_color}; "
            "font-size: 32pt; "
            "font-weight: 700; "
            "background: transparent;"
        )

    suffix = getattr(self, "_mw13_suffix", None)

    if suffix is not None:
        _mw13_oled_style(
            suffix,
            f"color: {self.text_color}; background: transparent;"
        )

def _mw13_resize(self, event):
    _mw13_old_resize(self, event)

    if hasattr(self, "_mw13_suffix"):
        _MW13Timer.singleShot(
            0,
            lambda: _mw13_position_suffix(self)
        )

DateCard.update_date = _mw13_update_date
DateCard.apply_text_color = _mw13_apply_text_color
DateCard.resizeEvent = _mw13_resize

# MORNINGUI_WEATHER_V13_END


# MORNINGUI_CURRENT_TEMP_36PT
_mw36_original_apply_text_color = DateCard.apply_text_color

def _mw36_apply_text_color(self):
    _mw36_original_apply_text_color(self)

    from PySide6.QtGui import QFont

    label = self.current_weather_label
    label.set_auto_fit_enabled(False)

    font = QFont(label.font())
    font.setPointSize(36)
    font.setBold(True)
    label.setFont(font)

    label.setMinimumHeight(max(54, label.minimumHeight()))
    label.setStyleSheet(
        f"color: {self.text_color}; "
        "background: transparent; "
        "font-size: 36pt; "
        "font-weight: 900;"
    )

DateCard.apply_text_color = _mw36_apply_text_color
