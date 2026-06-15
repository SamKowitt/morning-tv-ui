import math
import random

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPainterPath, QBrush
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from ui.auto_fit_label import AutoFitLabel


class WeatherRow(QWidget):
    def __init__(self, temp, icon, hour, condition="clear", is_night=False, is_now=False):
        super().__init__()

        self.temp = temp
        self.icon = icon
        self.hour = hour
        self.condition = condition
        self.is_night = is_night
        self.is_now = is_now
        self.phase = 0.0
        self.lightning_cooldown = random.randint(18, 48)
        self.lightning_frames_left = 0
        self.lightning_paths = []
        self.phase = 0.0

        # Independent lightning timing for each row
        self.lightning_cycle_length = random.randint(95, 125)
        self.lightning_flash_duration = random.randint(42, 48)
        self.lightning_offset = random.randint(0, self.lightning_cycle_length - 1)
        self.lightning_seed = random.randint(1000, 999999)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(48)

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(8)
        self.setLayout(layout)

        self.temp_label = AutoFitLabel(
            f"{temp}°",
            min_size=10,
            max_size=26,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
            word_wrap=False,
        )

        self.icon_label = AutoFitLabel(
            icon,
            min_size=10,
            max_size=24,
            bold=True,
            alignment=Qt.AlignCenter,
            word_wrap=False,
        )

        self.hour_label = AutoFitLabel(
            hour,
            min_size=10,
            max_size=26,
            bold=True,
            alignment=Qt.AlignRight | Qt.AlignVCenter,
            word_wrap=False,
        )

        layout.addWidget(self.hour_label, 30)
        layout.addWidget(self.icon_label, 30)
        layout.addWidget(self.temp_label, 40)

        self.apply_text_colors()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(50)

    def tick(self):
        # Smooth medium-speed rainfall
        self.phase += 1.5
        self.update()

    def apply_text_colors(self):
        if self.is_night:
            color = "#f4f1e8"
        else:
            color = "#22313b"

        font_css = f"color: {color}; background: transparent;"
        self.temp_label.setStyleSheet(font_css)
        self.icon_label.setStyleSheet(font_css)
        self.hour_label.setStyleSheet(font_css)

    def should_draw_night_art(self):
        return bool(self.is_night)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        night_art = self.should_draw_night_art()

        # Background gradient
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())

        if self.condition in ["rain", "storm"]:
            # Rain and thunderstorm use the exact same base art/colors.
            gradient.setColorAt(0.0, QColor("#6f8794"))
            gradient.setColorAt(0.5, QColor("#536c78"))
            gradient.setColorAt(1.0, QColor("#394f5b"))
            border = QColor("#9eb8c4")

        elif night_art:
            gradient.setColorAt(0.0, QColor("#0d1b2a"))
            gradient.setColorAt(1.0, QColor("#223a5e"))
            border = QColor("#5f7da0")

        elif self.condition == "cloud":
            # Rain and thunderstorm use the exact same base art/colors.
            gradient.setColorAt(0.0, QColor("#6f8794"))
            gradient.setColorAt(0.5, QColor("#536c78"))
            gradient.setColorAt(1.0, QColor("#394f5b"))
            border = QColor("#9eb8c4")

        elif self.condition == "cloud":
            gradient.setColorAt(0.0, QColor("#9fb1ba"))
            gradient.setColorAt(0.5, QColor("#8299a4"))
            gradient.setColorAt(1.0, QColor("#687f8b"))
            border = QColor("#b7c8cf")

        else:
            if self.is_now:
                gradient.setColorAt(0.0, QColor("#f9cd76"))
                gradient.setColorAt(1.0, QColor("#f2a65a"))
                border = QColor("#e2b35e")
            else:
                gradient.setColorAt(0.0, QColor("#f7d28f"))
                gradient.setColorAt(1.0, QColor("#f3bd6f"))
                border = QColor("#dec18b")

        painter.setPen(QPen(border, 2))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 16, 16)

        # Important:
        # Rain and storm always keep the existing rain animation.
        # Only non-rain rows from 12am–5am use deep night/moon art.
        if self.condition in ["rain", "storm"]:
            self.draw_rain(painter, rect)

            if self.condition == "storm":
                self.draw_lightning(painter, rect)

        elif night_art:
            self.draw_night_sky(painter, rect)

        elif self.condition == "cloud":
            self.draw_cloudy(painter, rect)

        elif self.condition == "fog":
            self.draw_cloudy(painter, rect)

        else:
            self.draw_clear(painter, rect)

        painter.end()

    def update_weather(self, temperature, icon, time_label, condition, is_night=False):
        temp_text = f"{temperature}°"

        # Force lightning storms to use lightning bolt icon everywhere.
        if condition == "storm":
            icon = "⚡"

        # Save animation/background state
        self.condition = condition
        self.is_night = is_night

        # Try common attribute names first
        temp_label = (
            getattr(self, "temperature_label", None)
            or getattr(self, "temp_label", None)
            or getattr(self, "degree_label", None)
        )

        icon_label = (
            getattr(self, "icon_label", None)
            or getattr(self, "weather_icon_label", None)
            or getattr(self, "emoji_label", None)
        )

        time_label_widget = (
            getattr(self, "time_label", None)
            or getattr(self, "hour_label", None)
            or getattr(self, "label_time", None)
        )

        labels = self.findChildren(QLabel)

        if temp_label is None:
            for label in labels:
                if "°" in label.text():
                    temp_label = label
                    break

        if icon_label is None:
            for label in labels:
                text = label.text()
                if any(symbol in text for symbol in ["☀", "🌤", "☁", "🌧", "⛈", "⚡", "🌙", "🌫", "🌨"]):
                    icon_label = label
                    break

        if time_label_widget is None:
            for label in labels:
                text = label.text().lower()
                if "am" in text or "pm" in text:
                    time_label_widget = label
                    break

        if temp_label is not None:
            temp_label.setText(temp_text)

        if icon_label is not None:
            icon_label.setText(icon)

        if time_label_widget is not None:
            time_label_widget.setText(time_label)

        # Make text readable after sunset / dark background
        if is_night:
            text_color = "#ffffff"
            muted_color = "rgba(255, 255, 255, 210)"
        else:
            text_color = "#263238"
            muted_color = "rgba(38, 50, 56, 210)"

        for label in labels:
            if label is icon_label:
                label.setStyleSheet(f"color: {text_color};")
            elif label is temp_label:
                label.setStyleSheet(f"color: {text_color}; font-weight: 900;")
            elif label is time_label_widget:
                label.setStyleSheet(f"color: {muted_color}; font-weight: 800;")
            else:
                label.setStyleSheet(f"color: {text_color};")

        self.update()

    def build_lightning_bolt(self, rect, seed_offset=0):
        w = max(1, rect.width())
        h = max(1, rect.height())

        random.seed((int(self.phase // 105) * 17) + seed_offset + w + h)

        top_y = rect.top() + 4
        bottom_y = rect.bottom() - 4

        start_x = rect.left() + random.uniform(w * 0.30, w * 0.70)

        points = [QPointF(start_x, top_y)]

        x = start_x
        y = top_y
        sideways_bias = random.uniform(-w * 0.015, w * 0.015)

        # 7–9 segments so the bolt reaches all the way down the section
        segment_count = random.randint(7, 9)

        for i in range(segment_count):
            remaining = bottom_y - y
            remaining_steps = max(1, segment_count - i)

            # Keep moving downward so it reaches the bottom
            step_y = remaining / remaining_steps
            step_y *= random.uniform(0.88, 1.12)

            # Jagged but still mostly vertical
            sideways_bias += random.uniform(-w * 0.035, w * 0.035)
            sideways_bias = max(-w * 0.09, min(w * 0.09, sideways_bias))

            x += sideways_bias + random.uniform(-w * 0.035, w * 0.035)
            x = max(rect.left() + 8, min(rect.right() - 8, x))

            y += step_y
            y = min(bottom_y, y)

            points.append(QPointF(x, y))

        # Force the bolt to end near the bottom edge
        if points[-1].y() < bottom_y - 1:
            points.append(QPointF(points[-1].x(), bottom_y))

        branches = []

        # Add 1–2 subtle branches for realism
        branch_total = random.randint(1, 2)

        if len(points) >= 5:
            valid_indices = list(range(2, len(points) - 2))
            random.shuffle(valid_indices)

            for branch_index in valid_indices[:branch_total]:
                anchor = points[branch_index]

                direction = -1 if random.random() < 0.5 else 1
                branch_length = random.randint(2, 3)

                bx = anchor.x()
                by = anchor.y()

                branch_points = [QPointF(bx, by)]

                for _ in range(branch_length):
                    bx += direction * random.uniform(w * 0.04, w * 0.09)
                    by += random.uniform(h * 0.06, h * 0.12)

                    bx = max(rect.left() + 6, min(rect.right() - 6, bx))
                    by = min(rect.bottom() - 6, by)

                    branch_points.append(QPointF(bx, by))

                branches.append(branch_points)

        return points, branches

    def draw_lightning(self, painter, rect):
        painter.save()

        w = max(1, rect.width())
        h = max(1, rect.height())

        # Each row now has its own independent timing.
        cycle_length = max(80, self.lightning_cycle_length)
        visible_length = min(self.lightning_flash_duration, cycle_length - 8)

        local_phase = self.phase + self.lightning_offset
        flash_cycle = int(local_phase) % cycle_length

        # Only draw during this row's own flash window.
        if flash_cycle > visible_length:
            painter.restore()
            return

        flash_progress = flash_cycle / max(1, visible_length)

        # Quick fade-in, hold, then fade-out.
        if flash_progress < 0.14:
            fade_strength = flash_progress / 0.14
        elif flash_progress > 0.78:
            fade_strength = max(0.0, 1.0 - ((flash_progress - 0.78) / 0.22))
        else:
            fade_strength = 1.0

        # Whole-row flash
        flash_alpha = int(34 + 46 * fade_strength)

        painter.setOpacity(0.08 + 0.05 * fade_strength)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, flash_alpha))
        painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 16, 16)

        # Stable bolt for this specific flash event on this specific row
        event_index = int(local_phase // cycle_length)
        trunk_points, branches = self.build_lightning_bolt(
            rect,
            seed_offset=self.lightning_seed + (event_index * 97),
        )

        trunk_path = QPainterPath(trunk_points[0])
        for point in trunk_points[1:]:
            trunk_path.lineTo(point)

        pulse = 0.88 + 0.12 * abs(math.sin(local_phase * 0.18))

        # Outer glow
        painter.setOpacity(0.55 * fade_strength * pulse)
        painter.setPen(
            QPen(
                QColor(255, 234, 150, 210),
                1.8,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        painter.drawPath(trunk_path)

        # Bright core
        painter.setOpacity(0.95 * fade_strength * pulse)
        painter.setPen(
            QPen(
                QColor(255, 255, 255, 245),
                0.8,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        painter.drawPath(trunk_path)

        # Small branches
        for branch_points in branches:
            if len(branch_points) < 2:
                continue

            branch_path = QPainterPath(branch_points[0])
            for point in branch_points[1:]:
                branch_path.lineTo(point)

            painter.setOpacity(0.42 * fade_strength * pulse)
            painter.setPen(
                QPen(
                    QColor(255, 235, 160, 190),
                    1.1,
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            painter.drawPath(branch_path)

            painter.setOpacity(0.85 * fade_strength * pulse)
            painter.setPen(
                QPen(
                    QColor(255, 255, 255, 230),
                    0.45,
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            painter.drawPath(branch_path)

        painter.restore()

    def draw_cloudy(self, painter, rect):
        painter.save()

        w = max(1, rect.width())
        h = max(1, rect.height())

        # Soft cloudy sky background
        sky = QLinearGradient(rect.topLeft(), rect.bottomRight())
        sky.setColorAt(0.0, QColor(112, 143, 162, 185))
        sky.setColorAt(0.45, QColor(152, 174, 184, 155))
        sky.setColorAt(1.0, QColor(205, 196, 166, 110))

        painter.setOpacity(0.58)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(sky))
        painter.drawRoundedRect(rect.adjusted(5, 5, -5, -5), 14, 14)

        # Muted hidden sun glow behind clouds
        sun_x = rect.left() + int(w * 0.78)
        sun_y = rect.top() + int(h * 0.28)
        sun_radius = max(9, min(w, h) * 0.12)

        painter.setOpacity(0.20)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 220, 130, 125))
        painter.drawEllipse(QPointF(sun_x, sun_y), sun_radius * 1.9, sun_radius * 1.9)

        painter.setOpacity(0.26)
        painter.setBrush(QColor(255, 238, 168, 150))
        painter.drawEllipse(QPointF(sun_x, sun_y), sun_radius, sun_radius)

        # Big slow cloud bank
        self.draw_cloud_bank(
            painter=painter,
            rect=rect,
            x_ratio=0.12,
            y_ratio=0.38,
            scale=0.95,
            speed=0.085,
            opacity=0.56,
            shade=QColor(235, 241, 244, 180),
            shadow=QColor(117, 139, 154, 95),
        )

        # Second layer drifting at a different speed
        self.draw_cloud_bank(
            painter=painter,
            rect=rect,
            x_ratio=0.50,
            y_ratio=0.60,
            scale=0.75,
            speed=0.055,
            opacity=0.42,
            shade=QColor(220, 229, 234, 160),
            shadow=QColor(92, 114, 132, 80),
        )

        # Thin lower haze
        haze_x = rect.left() + ((self.phase * 0.10) % (w + 90)) - 70

        painter.setOpacity(0.16)
        painter.setPen(QPen(QColor(240, 244, 245, 120), 5))
        painter.drawLine(
            QPointF(haze_x, rect.top() + h * 0.76),
            QPointF(haze_x + w * 0.85, rect.top() + h * 0.70),
        )

        painter.restore()

    def draw_cloud_bank(self, painter, rect, x_ratio, y_ratio, scale, speed, opacity, shade, shadow):
        painter.save()

        w = max(1, rect.width())
        h = max(1, rect.height())

        cloud_w = max(38, int(w * 0.54 * scale))
        cloud_h = max(18, int(h * 0.26 * scale))

        drift = (self.phase * speed) % (w + cloud_w)
        base_x = rect.left() + int(w * x_ratio)
        x = base_x + drift

        if x > rect.right() + cloud_w:
            x = rect.left() - cloud_w + (x - rect.right() - cloud_w)

        y = rect.top() + int(h * y_ratio) + math.sin(self.phase * 0.012 + x_ratio * 9) * 2

        # Cloud shadow underside
        painter.setOpacity(opacity * 0.55)
        painter.setPen(Qt.NoPen)
        painter.setBrush(shadow)

        painter.drawEllipse(QPointF(x + cloud_w * 0.18, y + cloud_h * 0.58), cloud_w * 0.28, cloud_h * 0.26)
        painter.drawEllipse(QPointF(x + cloud_w * 0.48, y + cloud_h * 0.62), cloud_w * 0.36, cloud_h * 0.26)
        painter.drawEllipse(QPointF(x + cloud_w * 0.74, y + cloud_h * 0.60), cloud_w * 0.26, cloud_h * 0.22)

        # Main cloud puffs
        painter.setOpacity(opacity)
        painter.setBrush(shade)

        painter.drawEllipse(QPointF(x + cloud_w * 0.10, y + cloud_h * 0.50), cloud_w * 0.22, cloud_h * 0.34)
        painter.drawEllipse(QPointF(x + cloud_w * 0.30, y + cloud_h * 0.28), cloud_w * 0.31, cloud_h * 0.47)
        painter.drawEllipse(QPointF(x + cloud_w * 0.55, y + cloud_h * 0.22), cloud_w * 0.34, cloud_h * 0.52)
        painter.drawEllipse(QPointF(x + cloud_w * 0.78, y + cloud_h * 0.45), cloud_w * 0.25, cloud_h * 0.36)

        # Soft highlight
        painter.setOpacity(opacity * 0.36)
        painter.setBrush(QColor(255, 255, 255, 145))
        painter.drawEllipse(QPointF(x + cloud_w * 0.42, y + cloud_h * 0.18), cloud_w * 0.22, cloud_h * 0.16)

        painter.restore()

    def draw_night_sky(self, painter, rect):
        self.draw_night(painter, rect)

    def draw_clear(self, painter, rect):
        painter.save()

        w = max(1, rect.width())
        h = max(1, rect.height())

        # Soft clear sky background
        sky = QLinearGradient(rect.topLeft(), rect.bottomRight())
        sky.setColorAt(0.0, QColor(98, 177, 225, 165))
        sky.setColorAt(0.55, QColor(151, 207, 236, 130))
        sky.setColorAt(1.0, QColor(255, 219, 142, 105))

        painter.setOpacity(0.52)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(sky))
        painter.drawRoundedRect(rect.adjusted(5, 5, -5, -5), 14, 14)

        # Fixed sun in the upper-right area
        sun_x = rect.left() + int(w * 0.82)
        sun_y = rect.top() + int(h * 0.28)
        sun_radius = max(9, min(w, h) * 0.13)

        # Sun glow
        for layer in range(4):
            radius = sun_radius + layer * 7
            alpha = max(18, 58 - layer * 11)

            painter.setOpacity(0.34)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 224, 120, alpha))
            painter.drawEllipse(QPointF(sun_x, sun_y), radius, radius)

        # Gentle rays
        painter.setOpacity(0.28)
        painter.setPen(QPen(QColor(255, 238, 164, 105), 1))

        for ray in range(12):
            angle = (ray / 12.0) * math.tau + self.phase * 0.006
            inner = sun_radius + 5
            outer = sun_radius + 14 + math.sin(self.phase * 0.030 + ray) * 2

            x1 = sun_x + math.cos(angle) * inner
            y1 = sun_y + math.sin(angle) * inner
            x2 = sun_x + math.cos(angle) * outer
            y2 = sun_y + math.sin(angle) * outer

            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Main sun
        painter.setOpacity(0.84)
        painter.setPen(QPen(QColor(255, 245, 190, 130), 1))
        painter.setBrush(QColor(255, 211, 92, 220))
        painter.drawEllipse(QPointF(sun_x, sun_y), sun_radius, sun_radius)

        # Very light shimmer
        for i in range(8):
            x = rect.left() + ((i * 41 + self.phase * 0.08) % w)
            y = rect.top() + h * (0.22 + ((i * 17) % 48) / 100)

            opacity = 0.14 + 0.16 * abs(math.sin(self.phase * 0.028 + i))

            painter.setOpacity(opacity)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 250, 210, 100))
            painter.drawEllipse(QPointF(x, y), 1.1, 1.1)

        painter.restore()

    def draw_sun(self, painter, rect):
        painter.save()
        painter.setOpacity(0.20)

        cx = rect.right() - 58
        cy = rect.center().y()
        radius = 18

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 233, 140, 180))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        painter.setPen(QPen(QColor(255, 223, 120, 170), 2))
        for i in range(12):
            angle = math.radians(i * 30 + self.phase * 2)
            x1 = cx + math.cos(angle) * (radius + 6)
            y1 = cy + math.sin(angle) * (radius + 6)
            x2 = cx + math.cos(angle) * (radius + 14)
            y2 = cy + math.sin(angle) * (radius + 14)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.restore()

    def draw_rain(self, painter, rect):
        painter.save()

        # Soft wet-glass overlay
        painter.setOpacity(0.14)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(180, 215, 230, 85))
        painter.drawRoundedRect(rect.adjusted(5, 5, -5, -5), 14, 14)

        w = max(1, rect.width())
        h = max(1, rect.height())

        # Larger loop height helps hide any repeating pattern
        loop_height = h + 120

        # Create many more small raindrops across the row
        columns = 18
        for col in range(columns):
            x_ratio = 0.04 + (col / (columns - 1)) * 0.92
            x = rect.left() + int(w * x_ratio)

            # Stagger the rows of drops
            for row in range(4):
                y_ratio = 0.08 + row * 0.24 + ((col % 3) * 0.03)

                # Smaller drops
                size = 2.2 + ((col + row) % 3) * 0.6

                # Slight opacity variation
                opacity = 0.40 + (((col * 7 + row * 5) % 5) * 0.07)

                # Slight speed variation
                speed = 0.42 + ((col + row) % 4) * 0.045

                base_y = rect.top() - 80 + int(loop_height * y_ratio)
                y = rect.top() - 80 + ((base_y + self.phase * speed) % loop_height)

                # Draw repeated copies for seamless looping
                for copy_offset in (-loop_height, 0, loop_height):
                    draw_y = y + copy_offset

                    if draw_y < rect.top() - 60 or draw_y > rect.bottom() + 60:
                        continue

                    self.draw_single_raindrop(
                        painter=painter,
                        x=x,
                        y=draw_y,
                        size=size,
                        opacity=opacity,
                    )

        # Add lots of tiny bead droplets for extra density
        tiny_columns = 14
        tiny_loop = h + 90

        for col in range(tiny_columns):
            x_ratio = 0.06 + (col / (tiny_columns - 1)) * 0.88
            x = rect.left() + int(w * x_ratio)

            for row in range(3):
                size = 1.3 + ((col + row) % 2) * 0.35
                speed = 0.30 + ((col + row) % 3) * 0.035
                y_ratio = 0.12 + row * 0.28 + ((col % 4) * 0.02)

                base_y = rect.top() - 40 + int(tiny_loop * y_ratio)
                y = rect.top() - 40 + ((base_y + self.phase * speed) % tiny_loop)

                for copy_offset in (-tiny_loop, 0, tiny_loop):
                    draw_y = y + copy_offset

                    if draw_y < rect.top() - 30 or draw_y > rect.bottom() + 30:
                        continue

                    painter.setOpacity(0.26)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(230, 245, 255, 140))
                    painter.drawEllipse(QPointF(x, draw_y), size, size * 1.45)

        painter.restore()

    def draw_single_raindrop(self, painter, x, y, size, opacity):
        painter.save()

        # Smaller subtle trail
        painter.setOpacity(opacity * 0.22)
        painter.setPen(QPen(QColor(220, 245, 255, 140), max(1, int(size * 0.22))))
        painter.drawLine(
            int(x),
            int(y - size * 2.8),
            int(x),
            int(y - size * 0.7),
        )

        # Main teardrop shape
        path = QPainterPath()
        path.moveTo(x, y - size * 1.9)

        path.cubicTo(
            x + size * 0.85,
            y - size * 0.7,
            x + size * 0.85,
            y + size * 0.55,
            x,
            y + size * 1.15,
        )

        path.cubicTo(
            x - size * 0.85,
            y + size * 0.55,
            x - size * 0.85,
            y - size * 0.7,
            x,
            y - size * 1.9,
        )

        painter.setOpacity(opacity)
        painter.setPen(QPen(QColor(235, 250, 255, 165), 1))
        painter.setBrush(QBrush(QColor(195, 230, 250, 145)))
        painter.drawPath(path)

        # Small highlight
        painter.setOpacity(opacity * 0.65)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 120))
        painter.drawEllipse(
            QPointF(x - size * 0.22, y - size * 0.58),
            size * 0.16,
            size * 0.24,
        )

        painter.restore()

    def draw_night(self, painter, rect):
        painter.save()

        w = max(1, rect.width())
        h = max(1, rect.height())

        # Deep animated night gradient
        sky = QLinearGradient(rect.topLeft(), rect.bottomRight())
        sky.setColorAt(0.0, QColor(10, 18, 42, 235))
        sky.setColorAt(0.45, QColor(22, 34, 70, 215))
        sky.setColorAt(1.0, QColor(45, 55, 88, 195))

        painter.setOpacity(0.78)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(sky))
        painter.drawRoundedRect(rect.adjusted(5, 5, -5, -5), 14, 14)

        # Subtle drifting galaxy haze
        haze_x = rect.left() + ((self.phase * 0.10) % (w + 120)) - 80
        haze_y = rect.top() + h * 0.35

        painter.setOpacity(0.12)
        painter.setPen(QPen(QColor(170, 190, 255, 90), 7))
        painter.drawLine(
            QPointF(haze_x, haze_y + 24),
            QPointF(haze_x + w * 0.85, haze_y - 12),
        )

        painter.setOpacity(0.08)
        painter.setPen(QPen(QColor(245, 230, 255, 80), 3))
        painter.drawLine(
            QPointF(haze_x + 20, haze_y + 30),
            QPointF(haze_x + w * 0.90, haze_y - 4),
        )

        # Moon placement can be customized by specific rows.
        moon_x_ratio = getattr(self, "moon_x_ratio", 0.90)
        moon_y_ratio = getattr(self, "moon_y_ratio", 0.17)

        moon_x = rect.left() + int(w * moon_x_ratio)
        moon_y = rect.top() + int(h * moon_y_ratio)
        moon_radius = max(7, min(w, h) * 0.105)

        for layer in range(4):
            radius = moon_radius + layer * 7
            alpha = max(12, 50 - layer * 10)

            painter.setOpacity(0.28)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(210, 225, 255, alpha))
            painter.drawEllipse(QPointF(moon_x, moon_y), radius, radius)

        # Main moon
        painter.setOpacity(0.86)
        painter.setPen(QPen(QColor(255, 255, 255, 140), 1))
        painter.setBrush(QColor(232, 238, 255, 225))
        painter.drawEllipse(QPointF(moon_x, moon_y), moon_radius, moon_radius)

        # Crescent cutout
        painter.setOpacity(0.92)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(18, 30, 62, 235))
        painter.drawEllipse(
            QPointF(moon_x + moon_radius * 0.42, moon_y - moon_radius * 0.10),
            moon_radius * 0.92,
            moon_radius * 0.92,
        )

        # Moon craters/highlights
        painter.setOpacity(0.22)
        painter.setBrush(QColor(180, 195, 230, 160))
        painter.drawEllipse(
            QPointF(moon_x - moon_radius * 0.22, moon_y - moon_radius * 0.18),
            moon_radius * 0.10,
            moon_radius * 0.10,
        )
        painter.drawEllipse(
            QPointF(moon_x + moon_radius * 0.08, moon_y + moon_radius * 0.24),
            moon_radius * 0.08,
            moon_radius * 0.08,
        )

        # Twinkling stars
        star_points = [
            (0.12, 0.22, 1.0),
            (0.22, 0.42, 0.7),
            (0.33, 0.24, 0.9),
            (0.48, 0.34, 0.65),
            (0.61, 0.17, 0.85),
            (0.70, 0.52, 0.55),
            (0.86, 0.45, 0.75),
            (0.17, 0.68, 0.6),
            (0.39, 0.62, 0.8),
            (0.57, 0.72, 0.62),
        ]

        for index, (x_ratio, y_ratio, size) in enumerate(star_points):
            x = rect.left() + w * x_ratio + math.sin(self.phase * 0.006 + index) * 1.4
            y = rect.top() + h * y_ratio + math.cos(self.phase * 0.005 + index) * 1.0

            twinkle = 0.32 + 0.42 * abs(math.sin(self.phase * 0.035 + index * 0.9))

            painter.setOpacity(twinkle)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(245, 248, 255, 210))
            painter.drawEllipse(QPointF(x, y), size + 0.6, size + 0.6)

            # tiny sparkle cross for a few stars
            if index % 3 == 0:
                painter.setOpacity(twinkle * 0.55)
                painter.setPen(QPen(QColor(245, 248, 255, 155), 0.7))
                painter.drawLine(QPointF(x - 3, y), QPointF(x + 3, y))
                painter.drawLine(QPointF(x, y - 3), QPointF(x, y + 3))

        # Slow drifting night clouds
        self.draw_night_cloud(
            painter,
            rect,
            x_ratio=0.15,
            y_ratio=0.64,
            scale=0.58,
            speed=0.10,
            opacity=0.22,
        )

        self.draw_night_cloud(
            painter,
            rect,
            x_ratio=0.55,
            y_ratio=0.76,
            scale=0.48,
            speed=0.075,
            opacity=0.16,
        )

        painter.restore()

    def draw_night_cloud(self, painter, rect, x_ratio, y_ratio, scale, speed, opacity):
        painter.save()

        w = max(1, rect.width())
        h = max(1, rect.height())

        cloud_w = max(28, int(w * 0.36 * scale))
        cloud_h = max(12, int(h * 0.18 * scale))

        drift = (self.phase * speed) % (w + cloud_w)
        base_x = rect.left() + int(w * x_ratio)
        x = base_x + drift

        if x > rect.right() + cloud_w:
            x = rect.left() - cloud_w + (x - rect.right() - cloud_w)

        y = rect.top() + int(h * y_ratio) + math.sin(self.phase * 0.012 + x_ratio * 7) * 2

        painter.setOpacity(opacity)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(145, 165, 205, 135))

        painter.drawEllipse(QPointF(x, y + cloud_h * 0.36), cloud_w * 0.30, cloud_h * 0.42)
        painter.drawEllipse(QPointF(x + cloud_w * 0.22, y), cloud_w * 0.34, cloud_h * 0.56)
        painter.drawEllipse(QPointF(x + cloud_w * 0.50, y + cloud_h * 0.24), cloud_w * 0.32, cloud_h * 0.46)
        painter.drawEllipse(QPointF(x + cloud_w * 0.72, y + cloud_h * 0.38), cloud_w * 0.24, cloud_h * 0.34)

        painter.setOpacity(opacity * 0.55)
        painter.setBrush(QColor(75, 88, 125, 135))
        painter.drawEllipse(QPointF(x + cloud_w * 0.40, y + cloud_h * 0.70), cloud_w * 0.42, cloud_h * 0.16)

        painter.restore()


class WeatherPanel(QWidget):
    def __init__(self):
        super().__init__()

        from PySide6.QtWidgets import QVBoxLayout

        main = QVBoxLayout()
        main.setSpacing(12)
        main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main)

        self.row_widgets = []

        rows = [
            ("68", "☀️", "10am", "clear", False),
            ("70", "☀️", "11am", "clear", False),
            ("71", "☀️", "12pm", "clear", False),
            ("72", "☀️", "1pm", "clear", False),
            ("72", "🌤️", "2pm", "clear", False),
            ("73", "🌤️", "3pm", "clear", False),
            ("70", "🌧️", "4pm", "rain", False),
            ("67", "🌧️", "5pm", "rain", False),
            ("65", "🌧️", "6pm", "rain", False),
        ]

        for index, (temp, icon, hour, condition, is_night) in enumerate(rows):
            row_widget = WeatherRow(
                temp=temp,
                icon=icon,
                hour=hour,
                condition=condition,
                is_night=is_night,
                is_now=(index == 0),
            )

            self.row_widgets.append(row_widget)
            main.addWidget(row_widget, 1)

    def update_weather_rows(self, rows):
        weather_row_widgets = []

        if hasattr(self, "row_widgets"):
            weather_row_widgets = self.row_widgets
        else:
            # Fallback: find any child widget that has the update_weather method.
            for child in self.findChildren(QWidget):
                if hasattr(child, "update_weather"):
                    weather_row_widgets.append(child)

        if not weather_row_widgets:
            print("Weather panel update skipped: no weather row widgets found.")
            return

        for index, row in enumerate(rows):
            if index >= len(weather_row_widgets):
                break

            weather_row_widgets[index].update_weather(
                temperature=row.temperature,
                icon=row.icon,
                time_label=row.time_label,
                condition=row.condition,
                is_night=row.is_night,
            )