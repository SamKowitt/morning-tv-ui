from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGridLayout,
    QSpacerItem,
    QSizePolicy,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)



class MarketTapeWiderTextColumn(QVBoxLayout):
    # MUI_MARKET_TAPE_TEXT_WIDTH_V21
    def sizeHint(self):
        hint = super().sizeHint()
        # MUI_MARKET_TAPE_CHART_LEFT_V23
        # Reserve only 5% extra instead of 20%.
        hint.setWidth((hint.width() * 21 + 19) // 20)
        return hint


# MUI_MARKET_TAPE_CHART_V22
def _mui_market_number(value):
    import math
    try:
        number = float(
            str(value).strip()
            .replace("$", "")
            .replace(",", "")
            .replace("%", "")
            .replace("−", "-")
        )
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _mui_market_percentage(price, absolute_change):
    current = _mui_market_number(price)
    delta = _mui_market_number(absolute_change)

    if current is None or delta is None:
        return None

    previous = current - delta
    if previous <= 0:
        return None

    return 100.0 * delta / previous


def _mui_market_percent_text(value):
    if value is None:
        return "—"
    return f"{value:+.2f}%"


def _mui_market_badge(label, percentage):
    label.setText(_mui_market_percent_text(percentage))
    label.setObjectName(
        "MarketTapeDown"
        if percentage is not None and percentage < 0
        else "MarketTapeUp"
    )
    label.style().unpolish(label)
    label.style().polish(label)



# MUI_MARKET_TAPE_DATAFIX_V27
# The chart endpoint and percentage represent the same period.
def _mui_market_datafix_v27(history, displayed_price):
    prices = []

    for value in (history or []):
        number = _mui_market_number(value)
        if number is None or number <= 0:
            return [1.0, 1.0, 1.0], None
        prices.append(number)

    current = _mui_market_number(displayed_price)

    # Do not represent incomplete or synthetic history
    # as a valid three-month performance chart.
    if (
        len(prices) < 50
        or current is None
        or current <= 0
        or len({round(v, 6) for v in prices}) < 3
    ):
        return [1.0, 1.0, 1.0], None

    # Join the most recent available quote to the
    # historical daily-close series.
    if abs(prices[-1] - current) > 0.000001:
        prices.append(current)

    percent = 100.0 * (current - prices[0]) / prices[0]
    return prices, percent


class SparklineChart(QWidget):
    def __init__(self, values, months=None):
        super().__init__()
        self.values = values or [1, 1, 1]
        self.months = months or ["Apr", "May", "Jun"]

        self.setMinimumWidth(56)
        # MUI_MARKET_TAPE_FULL_CHART_V17
        self.setMinimumHeight(22)
        self.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

    def set_values(self, values):
        self.values = values or [1, 1, 1]
        self.update()

    def paintEvent(self, event):
        # MUI_MARKET_TAPE_CHART_V22
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainterPath, QLinearGradient

        try:
            values = [float(v) for v in self.values]
        except (ValueError, TypeError, OverflowError):
            return

        if len(values) < 2:
            return

        w = self.width()
        h = self.height()

        if w < 36 or h < 20:
            return

        # Never draw synthetic placeholder history.
        if getattr(
            self, "_mui_market_no_history_v27", False
        ):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Very dark chart background, like the reference.
        painter.fillRect(
            self.rect(),
            QColor(20, 23, 24, 190)
        )

        # Reserve a narrow right-side gutter for values.
        # This changes the plotting width, NOT the outer
        # stock bubble dimensions.
        axis_width = 36 if w >= 110 else 31

        left_x = 2.0
        right_x = float(w - axis_width - 4)
        top_y = 3.0
        bottom_y = float(h - 9)

        if right_x - left_x < 8:
            return

        if bottom_y - top_y < 8:
            return

        # Include the previous trading close in the 1d scale.
        axis_values = list(values)
        previous_close = getattr(
            self, "_mui_intraday_previous_close_v30", None
        )
        if previous_close is not None and previous_close > 0:
            axis_values.append(float(previous_close))
        low = min(axis_values)
        high = max(axis_values)
        span = high - low

        if span <= 0:
            pad = max(abs(high) * 0.001, 0.01)
        else:
            pad = span * 0.06

        low -= pad
        high += pad
        span = high - low

        def value_y(value):
            return (
                bottom_y
                - ((value - low) / span)
                * (bottom_y - top_y)
            )

        # Faint horizontal grid and right-side labels.
        grid_color = QColor(210, 220, 220, 32)
        axis_color = QColor(232, 236, 237, 200)

        painter.setPen(QPen(grid_color, 0.55))

        for i in range(4):
            y = top_y + (
                i / 3.0
            ) * (bottom_y - top_y)

            painter.drawLine(
                QPointF(left_x, y),
                QPointF(right_x, y)
            )

        # Only two subtle vertical grid divisions.
        for i in (1, 2):
            x = left_x + (
                i / 3.0
            ) * (right_x - left_x)

            painter.drawLine(
                QPointF(x, top_y),
                QPointF(x, bottom_y)
            )

        # Numeric scale precision adapts to price range.
        interval = span / 3.0

        if interval >= 5:
            precision = 0
        elif interval >= 0.5:
            precision = 1
        elif interval >= 0.05:
            precision = 2
        else:
            precision = 3

        axis_font = QFont(painter.font())
        axis_font.setBold(True)
        axis_font.setPixelSize(
            9 if w >= 110 else 8
        )

        painter.setFont(axis_font)
        painter.setPen(axis_color)

        for i in range(4):
            level = high - i * interval

            y = top_y + (
                i / 3.0
            ) * (bottom_y - top_y)

            label = f"{level:,.{precision}f}"

            painter.drawText(
                QRectF(
                    right_x + 3,
                    y - 6,
                    w - right_x - 5,
                    12
                ),
                Qt.AlignRight | Qt.AlignVCenter,
                label
            )

        # Dotted 1d line: previous regular-session close.
        if previous_close is not None and low <= previous_close <= high:
            reference_pen = QPen(QColor(220, 225, 230, 140), 0.85)
            reference_pen.setStyle(Qt.DashLine)
            painter.setPen(reference_pen)
            baseline = value_y(previous_close)
            painter.drawLine(
                QPointF(left_x, baseline),
                QPointF(right_x, baseline),
            )

        # Match line and shading to the change badge.
        percentage = getattr(
            self, "_market_percent", None
        )

        if percentage is None:
            down = values[-1] < values[0]
        else:
            down = percentage < 0

        if down:
            line = QColor(255, 65, 57)
            shade_top = QColor(255, 65, 57, 112)
            shade_bottom = QColor(255, 65, 57, 0)
        else:
            line = QColor(56, 216, 103)
            shade_top = QColor(56, 216, 103, 105)
            shade_bottom = QColor(56, 216, 103, 0)

        points = []

        # 1d uses the fixed 9:30 AM–4:00 PM ET time axis.
        # Future trading hours remain blank.
        intraday_minutes = getattr(
            self, "_mui_intraday_minutes_v30", None
        )
        if (
            intraday_minutes is not None
            and len(intraday_minutes) != len(values)
        ):
            painter.end()
            return

        for index, value in enumerate(values):
            if intraday_minutes is None:
                fraction = index / (len(values) - 1)
            else:
                fraction = max(
                    0.0, min(
                        1.0,
                        (intraday_minutes[index] - 570.0) / 390.0
                    )
                )
            x = left_x + fraction * (right_x - left_x)

            points.append(
                QPointF(x, value_y(value))
            )

        curve = QPainterPath()
        curve.moveTo(points[0])

        for point in points[1:]:
            curve.lineTo(point)

        # Colored area fill underneath the price line.
        area = QPainterPath()
        area.moveTo(
            QPointF(points[0].x(), bottom_y)
        )
        area.lineTo(points[0])

        for point in points[1:]:
            area.lineTo(point)

        area.lineTo(
            QPointF(points[-1].x(), bottom_y)
        )
        area.closeSubpath()

        gradient = QLinearGradient(
            0.0, top_y, 0.0, bottom_y
        )
        gradient.setColorAt(0.0, shade_top)
        gradient.setColorAt(1.0, shade_bottom)

        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(area)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(
            QPen(line, 1.65)
        )
        painter.drawPath(curve)

        # Preserve the three simple bottom time markers.
        painter.setPen(
            QPen(QColor(220, 230, 230, 135), 0.7)
        )

        # MARKET_TAPE_RANGES_V29: period-specific time marks.
        mark_count = max(1, int(getattr(self, "_mui_tick_count_v29", 3)))
        for mark_index in range(mark_count):
            fraction = (mark_index / (mark_count - 1)) if mark_count > 1 else 0.5
            x = left_x + (
                fraction * (right_x - left_x)
            )

            painter.drawLine(
                QPointF(x, h - 7),
                QPointF(x, h - 2)
            )

class MarketIndex(QWidget):
    def __init__(self, name, price, history=None):
        super().__init__()

        self.setObjectName("MarketTapeIndexCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # MUI_MARKET_TAPE_GROW_INDEX_V17
        # MUI_MARKET_TAPE_TOP_HEIGHT_V23
        self.setMinimumHeight(64)
        self.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        # MUI_MARKET_TAPE_CHART_LEFT_V23
        # Keep the chart closer to its text column.
        layout.setSpacing(1)
        self.setLayout(layout)

        left = MarketTapeWiderTextColumn()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(0)

        self.name_label = QLabel(name)
        self.name_label.setObjectName("MarketTapeTicker")
        # MUI_MARKET_TAPE_TICKER_CENTER_V23
        self.name_label.setAlignment(
            Qt.AlignHCenter | Qt.AlignVCenter
        )

        self.price_label = QLabel()
        self.price_label.setObjectName("MarketTapePrice")
        # MUI_MARKET_TAPE_PRICE_CENTER_V24
        self.price_label.setAlignment(
            Qt.AlignHCenter | Qt.AlignVCenter
        )
        self.price_label.setTextFormat(Qt.RichText)
        self.price_label.setText(self.format_index_price_text(price))

        # MUI_MARKET_TAPE_V19: same three-part
        # arrangement as the four lower stock bubbles.
        self.change_value = QLabel("—")
        self.change_value.setObjectName("MarketTapeUp")
        # MUI_MARKET_TAPE_BADGE_FONT_V24
        # Widget-local font override preserves the
        # existing red/green stylesheet properties.
        self.change_value.setStyleSheet(
            "font-size: 13px;"
        )
        self.change_value.setAlignment(Qt.AlignCenter)
        # MUI_MARKET_TAPE_V20
        # Restore natural badge width; increase height only.
        # MUI_MARKET_TAPE_UPPER_BADGE_V25
        # Same 13px text and 64px width, less height.
        self.change_value.setFixedHeight(22)
        self.change_value.setSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Fixed
        )
        # MUI_MARKET_TAPE_CHART_V22
        self.change_value.setFixedWidth(64)

        left.addWidget(self.name_label)
        left.addStretch(1)
        left.addWidget(self.price_label)
        left.addStretch(1)
        left.addWidget(self.change_value, 0, Qt.AlignLeft)

        self.sparkline = SparklineChart(
            history or [1, 1, 1],
            months=["Apr", "May", "Jun"],
        )

        # The label uses its natural width.
        # The chart receives all remaining horizontal space.
        layout.addLayout(left, 0)
        layout.addWidget(self.sparkline, 1)

    def format_index_price_text(self, price):
        # MUI_MARKET_TAPE_V20: match lower stock prices.
        # MUI_MARKET_TAPE_PRICE_SIZE_V25
        price_text = str(price or "—").strip()

        if price_text in {"", "—", "-", "Loading"}:
            return price_text

        if "." not in price_text:
            return (
                f'<span style="font-size: 14px; font-weight: 1000;">'
                f'{price_text}</span>'
            )

        whole, decimals = price_text.rsplit(".", 1)

        if not decimals:
            return (
                f'<span style="font-size: 14px; font-weight: 1000;">'
                f'{whole}</span>'
            )

        return (
            f'<span style="font-size: 14px; font-weight: 1000;">'
            f'{whole}</span>'
            f'<span style="font-size: 7px; font-weight: 900;">'
            f'.{decimals}</span>'
        )

    def update_index(self, name, price, history=None):
        self.name_label.setText(name)
        self.price_label.setText(
            self.format_index_price_text(price)
        )

        # MUI_MARKET_TAPE_DATAFIX_V27
        # Percentage, chart endpoint, and color all use
        # the same approximate three-month period.
        plotted, percentage = _mui_market_datafix_v27(
            history, price
        )
        self.sparkline.set_values(plotted)
        self.sparkline._mui_market_no_history_v27 = (
            percentage is None
        )

        _mui_market_badge(
            self.change_value, percentage
        )

        self.change_value.setVisible(
            percentage is not None
        )

        self.change_value.setToolTip(
            "Approximate 3-month return through latest quote (%)"
        )

        self.sparkline._market_percent = percentage
        self.sparkline.update()


class StockTile(QWidget):
    def __init__(self, ticker, price, ah_change, history):
        super().__init__()

        self.setObjectName("MarketTapeStockTile")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # MUI_MARKET_TAPE_GROW_STOCK_V17
        self.setMinimumHeight(73)
        self.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        # MUI_MARKET_TAPE_CHART_LEFT_V23
        # Keep the chart closer to its text column.
        layout.setSpacing(1)
        self.setLayout(layout)

        left = MarketTapeWiderTextColumn()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(0)

        self.ticker_label = QLabel(ticker)
        self.ticker_label.setObjectName("MarketTapeTicker")
        # MUI_MARKET_TAPE_LOWER_FONTS_V26
        # Local font-size override; retain existing colors,
        # weight, alignment, and other ticker styling.
        self.ticker_label.setStyleSheet(
            "QLabel#MarketTapeTicker { font-size: 14px; }"
        )
        # MUI_MARKET_TAPE_TICKER_CENTER_V23
        self.ticker_label.setAlignment(
            Qt.AlignHCenter | Qt.AlignVCenter
        )

        self.price_label = QLabel()
        self.price_label.setObjectName("MarketTapePrice")
        # MUI_MARKET_TAPE_PRICE_CENTER_V24
        self.price_label.setAlignment(
            Qt.AlignHCenter | Qt.AlignVCenter
        )
        self.price_label.setTextFormat(Qt.RichText)
        self.price_label.setText(self.format_stock_price_text(price))

        self.sparkline = SparklineChart(
            history or [1, 1, 1],
            months=["Apr", "May", "Jun"],
        )

        # MUI_MARKET_TAPE_CHANGE_LEFT_V18
        # Reuse the existing numerical change badge and its
        # MarketTapeUp / MarketTapeDown stylesheet.
        # The old outer CHG box is no longer needed.
        self.ah_value = QLabel(ah_change)
        # MUI_MARKET_TAPE_BADGE_FONT_V24
        self.ah_value.setStyleSheet(
            "font-size: 13px;"
        )
        self.ah_value.setAlignment(Qt.AlignCenter)
        self.ah_value.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )
        # MUI_MARKET_TAPE_CHART_V22
        self.ah_value.setFixedWidth(64)
        # MUI_MARKET_TAPE_V20
        # Natural width, taller numerical badge.
        self.ah_value.setMinimumHeight(31)

        # MUI_MARKET_TAPE_V19: distribute ticker,
        # price, and change badge without overlap.
        left.addWidget(self.ticker_label)
        left.addStretch(1)
        left.addWidget(self.price_label)
        left.addStretch(1)
        left.addWidget(self.ah_value, 0, Qt.AlignLeft)

        # The sparkline now occupies ALL remaining width
        # through the former right-hand CHG area.
        # Existing chart margins and month dashes remain.
        layout.addLayout(left, 0)
        layout.addWidget(self.sparkline, 1)

        self.update_stock(ticker, price, ah_change, history)

    def format_stock_price_text(self, price):
        # MUI_MARKET_TAPE_PRICE_SIZE_V25
        price_text = str(price or "—").strip()

        if price_text in {"", "—", "-", "Loading"}:
            return price_text

        if "." not in price_text:
            return (
                f'<span style="font-size: 17px; font-weight: 1000;">'
                f"{price_text}</span>"
            )

        whole, decimals = price_text.rsplit(".", 1)

        return (
            f'<span style="font-size: 17px; font-weight: 1000;">'
            f"{whole}</span>"
            f'<span style="font-size: 9px; font-weight: 900;">'
            f".{decimals}</span>"
        )

    def update_stock(
        self, ticker, price, ah_change, history
    ):
        self.ticker_label.setText(ticker)
        self.price_label.setText(
            self.format_stock_price_text(price)
        )

        # MUI_MARKET_TAPE_DATAFIX_V27
        # Percentage, chart endpoint, and color all use
        # the same approximate three-month period.
        plotted, percentage = _mui_market_datafix_v27(
            history, price
        )
        self.sparkline.set_values(plotted)
        self.sparkline._mui_market_no_history_v27 = (
            percentage is None
        )

        _mui_market_badge(
            self.ah_value, percentage
        )

        self.ah_value.setToolTip(
            "Approximate 3-month return through latest quote (%)"
        )

        self.sparkline._market_percent = percentage
        self.sparkline.update()


class StocksPanel(QWidget):
    hide_requested = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("MarketTapeCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        oled_style(self, """
            QWidget#MarketTapeCard {
                margin-bottom: 9px;
            }
        """)

        self.index_widgets = []
        self.stock_widgets = []

        main = QVBoxLayout()
        main.setContentsMargins(10, 4, 10, 6)
        main.setSpacing(2)
        self.setLayout(main)

        header = QHBoxLayout()
        header.setSpacing(6)


        title = QLabel("MARKET TAPE")
        title.setObjectName("MarketTapeTitle")
        title.setAlignment(Qt.AlignLeft)

        # MUI_MARKET_TAPE_HEADER_V23
        # Larger trend label beside the title.
        self.subtitle = QLabel("3 Month Trend")
        self.subtitle.setObjectName("MarketTapeTrendV23")
        self.subtitle.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )
        oled_style(self.subtitle, """
            QLabel#MarketTapeTrendV23 {
                color: #d9c98f;
                font-size: 12px;
                font-weight: 900;
            }
        """)

        self.hide_button = QPushButton("Hide")
        self.hide_button.setObjectName("MarketTapeHideButton")
        self.hide_button.setCursor(Qt.PointingHandCursor)
        self.hide_button.setMinimumHeight(21)
        self.hide_button.setMinimumWidth(52)
        self.hide_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.hide_button.clicked.connect(self.hide_requested.emit)
        oled_style(self.hide_button, """
            QPushButton#MarketTapeHideButton {
                color: #f7f0df;
                background: rgba(20, 35, 52, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.42);
                border-radius: 5px;
                padding: 1px 7px;
                font-family: "Times New Roman";
                font-size: 11px;
                font-weight: 900;
            }

            QPushButton#MarketTapeHideButton:hover {
                background: rgba(20, 35, 52, 0.95);
                border-color: rgba(255, 255, 255, 0.78);
            }
        """)

        # MUI_MARKET_TAPE_HEADER_V23
        header.addWidget(title)
        header.addWidget(self.subtitle)
        # MARKET_TAPE_RANGES_V29: add buttons without resizing cards.
        from ui.market_tape_ranges_v29 import add_range_buttons_v29
        add_range_buttons_v29(self, header)
        header.addStretch(1)
        header.addWidget(self.hide_button)

        main.addLayout(header)

        index_row = QHBoxLayout()
        index_row.setSpacing(4)

        for name, price, history in [
            ("S&P", "Loading", [1, 1, 1]),
            ("DOW", "Loading", [1, 1, 1]),
            ("NAS", "Loading", [1, 1, 1]),
        ]:
            widget = MarketIndex(name, price, history)
            self.index_widgets.append(widget)
            index_row.addWidget(widget, 1)

        # Market indices fill the first chart row.
        main.addLayout(index_row, 1)


        stock_grid = QGridLayout()
        stock_grid.setHorizontalSpacing(5)
        stock_grid.setVerticalSpacing(1)
        stock_grid.setContentsMargins(0, 0, 0, 0)
        # MUI_MARKET_TAPE_V20: slightly shorter
        # lower tiles, preserving their top positions.
        stock_grid.setRowMinimumHeight(0, 73)
        stock_grid.setRowMinimumHeight(1, 73)
        stock_grid.setRowStretch(0, 19)
        stock_grid.setRowStretch(1, 19)
        stock_grid.setRowStretch(2, 2)
        stock_grid.addItem(
            QSpacerItem(
                0, 0,
                QSizePolicy.Minimum,
                QSizePolicy.Expanding,
            ),
            2, 0, 1, 2,
        )

        for index, stock in enumerate([
            ("VRT", "Loading", "—", [1, 1, 1]),
            ("SPCX", "Loading", "—", [1, 1, 1]),
            ("FITB", "Loading", "—", [1, 1, 1]),
            ("AMZN", "Loading", "—", [1, 1, 1]),
        ]):
            row = index // 2
            col = index % 2

            widget = StockTile(*stock)
            self.stock_widgets.append(widget)
            stock_grid.addWidget(widget, row, col)

        # Four stock bubbles fill the remaining two rows.
        # MUI_MARKET_TAPE_V19: 1:3 upper/lower
        # height allocation; minimum sizes prevent clipping.
        main.addLayout(stock_grid, 3)

    def update_market_data(self, market_data):
        for index, quote in enumerate(market_data.indexes):
            if index >= len(self.index_widgets):
                break

            self.index_widgets[index].update_index(
                name=quote.name,
                price=quote.price,
                history=quote.history,
            )

        for index, quote in enumerate(market_data.stocks):
            if index >= len(self.stock_widgets):
                break

            self.stock_widgets[index].update_stock(
                ticker=quote.ticker,
                price=quote.price,
                ah_change=quote.ah_change,
                history=quote.history,
            )

        # MARKET_TAPE_RANGES_V29: reuse the fetched multi-range dataset.
        from ui.market_tape_ranges_v29 import render_market_ranges_v29
        render_market_ranges_v29(self, market_data)

# OLED_CONTRAST_V4
from ui.oled_text import oled_text_draw, oled_style, oled_html, oled_layout_draw
