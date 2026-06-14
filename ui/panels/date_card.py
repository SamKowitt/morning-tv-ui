from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QHBoxLayout, QStackedLayout, QVBoxLayout, QWidget, QSizePolicy

from ui.auto_fit_label import AutoFitLabel
from ui.panels.weather_panel import WeatherRow


class DateCard(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("DateCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.background_weather_row = self.create_weather_background()

        self.overlay = QWidget()
        self.overlay.setObjectName("DateCardWeatherOverlay")
        self.overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)

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

        date_block.addWidget(self.month_label, 24)
        date_block.addWidget(self.date_number_label, 76)

        self.current_weather_label = AutoFitLabel(
            "--°",
            min_size=22,
            max_size=46,
            bold=True,
            alignment=Qt.AlignRight | Qt.AlignBottom,
            word_wrap=False,
        )
        self.current_weather_label.setObjectName("DateCurrentWeather")

        bottom_row.addLayout(date_block, 64)
        bottom_row.addWidget(self.current_weather_label, 36)

        overlay_layout.addWidget(self.day_label, 0)
        overlay_layout.addStretch(1)
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

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_date)
        self.timer.start(60_000)

        self.update_date()
        self.set_day_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Keep the June / 14 / temp block anchored at the bottom.
        bottom_height = max(88, int(self.height() * 0.46))
        self.bottom_widget.setFixedHeight(bottom_height)

        self.overlay.raise_()

    def create_weather_background(self):
        try:
            row = WeatherRow("--", "🌤️", "now", "clear", False)
        except TypeError:
            row = WeatherRow("--", "🌤️", "now", "clear")

        row.setObjectName("DateWeatherBackground")
        row.setAttribute(Qt.WA_StyledBackground, True)

        row.moon_x_ratio = 0.84
        row.moon_y_ratio = 0.17

        for label in row.findChildren(QLabel):
            label.hide()

        return row

    def update_date(self):
        now = datetime.now()
        self.day_label.setText(now.strftime("%a").upper())
        self.month_label.setText(now.strftime("%B"))
        self.date_number_label.setText(now.strftime("%-d"))

        self.overlay.raise_()

    def update_current_weather(self, row):
        self.background_weather_row.update_weather(
            temperature=row.temperature,
            icon=row.icon,
            time_label=row.time_label or "now",
            condition=row.condition,
            is_night=row.is_night,
        )

        for label in self.background_weather_row.findChildren(QLabel):
            label.hide()

        self.current_weather_label.setText(f"{row.temperature}°")

        if row.is_night:
            self.set_night_text()
        else:
            self.set_day_text()

        self.stacked.setCurrentWidget(self.overlay)
        self.background_weather_row.lower()
        self.overlay.raise_()

    def set_night_text(self):
        self.day_label.setStyleSheet("color: #ffffff;")
        self.month_label.setStyleSheet("color: rgba(255, 255, 255, 225);")
        self.date_number_label.setStyleSheet("color: #ffffff;")
        self.current_weather_label.setStyleSheet("color: rgba(255, 255, 255, 230);")

    def set_day_text(self):
        self.day_label.setStyleSheet("color: #2f2a24;")
        self.month_label.setStyleSheet("color: #5f4d36;")
        self.date_number_label.setStyleSheet("color: #2f2a24;")
        self.current_weather_label.setStyleSheet("color: #4b3d2c;")