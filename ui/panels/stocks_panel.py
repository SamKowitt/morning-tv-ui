from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGridLayout,
    QSizePolicy,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SparklineChart(QWidget):
    def __init__(self, values, months=None):
        super().__init__()
        self.values = values or [1, 1, 1]
        self.months = months or ["Apr", "May", "Jun"]

        self.setMinimumWidth(56)
        self.setFixedHeight(32)

    def set_values(self, values):
        self.values = values or [1, 1, 1]
        self.update()

    def paintEvent(self, event):
        if not self.values or len(self.values) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        chart_rect = self.rect().adjusted(3, 1, -3, -8)
        label_y = self.rect().bottom() - 1

        min_value = min(self.values)
        max_value = max(self.values)
        value_range = max(max_value - min_value, 1)

        points = []
        for index, value in enumerate(self.values):
            x = chart_rect.left() + (
                index / (len(self.values) - 1)
            ) * chart_rect.width()
            normalized = (value - min_value) / value_range
            y = chart_rect.bottom() - normalized * chart_rect.height()
            points.append(QPointF(x, y))

        line_color = QColor(255, 255, 255, 235)
        tick_color = QColor(255, 255, 255, 150)

        painter.setPen(QPen(line_color, 0.9))
        for index in range(len(points) - 1):
            painter.drawLine(points[index], points[index + 1])

        painter.setPen(Qt.NoPen)
        painter.setBrush(line_color)
        painter.drawEllipse(points[-1], 0.9, 0.9)

        month_font = QFont(painter.font())
        month_font.setPointSize(4)
        month_font.setBold(True)
        painter.setFont(month_font)

        positions = [
            chart_rect.left(),
            chart_rect.center().x(),
            chart_rect.right(),
        ]

        for index, month in enumerate(self.months[:3]):
            x = int(positions[index])

            painter.setPen(QPen(tick_color, 0.5))
            painter.drawLine(
                x,
                chart_rect.bottom() + 1,
                x,
                chart_rect.bottom() + 2,
            )

            painter.setPen(tick_color)
            painter.drawText(
                x - 9,
                label_y - 6,
                18,
                7,
                Qt.AlignCenter,
                month,
            )


class MarketIndex(QWidget):
    def __init__(self, name, price, history=None):
        super().__init__()

        self.setObjectName("MarketTapeIndexCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(48)

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(4)
        self.setLayout(layout)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(0)

        self.name_label = QLabel(name)
        self.name_label.setObjectName("MarketTapeIndexName")
        self.name_label.setAlignment(Qt.AlignLeft)

        self.price_label = QLabel()
        self.price_label.setObjectName("MarketTapeIndexPrice")
        self.price_label.setAlignment(Qt.AlignLeft)
        self.price_label.setTextFormat(Qt.RichText)
        self.price_label.setText(self.format_index_price_text(price))

        left.addWidget(self.name_label)
        left.addWidget(self.price_label)

        self.sparkline = SparklineChart(
            history or [1, 1, 1],
            months=["Apr", "May", "Jun"],
        )

        layout.addLayout(left, 43)
        layout.addWidget(self.sparkline, 57)

    def format_index_price_text(self, price):
        price_text = str(price or "—")

        if "." not in price_text:
            return price_text

        whole, decimals = price_text.rsplit(".", 1)
        return (
            f"{whole}"
            f'<span style="font-size: 7px; font-weight: 900;">.{decimals}</span>'
        )

    def update_index(self, name, price, history=None):
        self.name_label.setText(name)
        self.price_label.setText(self.format_index_price_text(price))
        self.sparkline.set_values(history or [1, 1, 1])


class StockTile(QWidget):
    def __init__(self, ticker, price, ah_change, history):
        super().__init__()

        self.setObjectName("MarketTapeStockTile")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(65)

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(4)
        self.setLayout(layout)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(0)

        self.ticker_label = QLabel(ticker)
        self.ticker_label.setObjectName("MarketTapeTicker")
        self.ticker_label.setAlignment(Qt.AlignLeft)

        self.price_label = QLabel()
        self.price_label.setObjectName("MarketTapePrice")
        self.price_label.setAlignment(Qt.AlignLeft)
        self.price_label.setTextFormat(Qt.RichText)
        self.price_label.setText(self.format_stock_price_text(price))

        left.addWidget(self.ticker_label)
        left.addWidget(self.price_label)

        self.sparkline = SparklineChart(
            history or [1, 1, 1],
            months=["Apr", "May", "Jun"],
        )

        self.ah_box = QWidget()
        self.ah_box.setObjectName("MarketTapeAHBox")
        self.ah_box.setAttribute(Qt.WA_StyledBackground, True)
        self.ah_box.setFixedSize(46, 49)

        ah_layout = QVBoxLayout()
        ah_layout.setContentsMargins(2, 1, 2, 1)
        ah_layout.setSpacing(0)
        self.ah_box.setLayout(ah_layout)

        self.ah_title = QLabel("CHG")
        self.ah_title.setObjectName("MarketTapeAHLabel")
        self.ah_title.setAlignment(Qt.AlignCenter)

        self.ah_value = QLabel(ah_change)
        self.ah_value.setAlignment(Qt.AlignCenter)

        ah_layout.addWidget(self.ah_title)
        ah_layout.addWidget(self.ah_value)

        layout.addLayout(left, 33)
        layout.addWidget(self.sparkline, 48)
        layout.addWidget(self.ah_box, 19)

        self.update_stock(ticker, price, ah_change, history)

    def format_stock_price_text(self, price):
        price_text = str(price or "—").strip()

        if price_text in {"", "—", "-", "Loading"}:
            return price_text

        if "." not in price_text:
            return (
                f'<span style="font-size: 14px; font-weight: 1000;">'
                f"{price_text}</span>"
            )

        whole, decimals = price_text.rsplit(".", 1)

        return (
            f'<span style="font-size: 14px; font-weight: 1000;">'
            f"{whole}</span>"
            f'<span style="font-size: 7px; font-weight: 900;">'
            f".{decimals}</span>"
        )

    def update_stock(self, ticker, price, ah_change, history):
        self.ticker_label.setText(ticker)
        self.price_label.setText(self.format_stock_price_text(price))
        self.sparkline.set_values(history or [1, 1, 1])

        if str(ah_change).startswith("-"):
            self.ah_value.setObjectName("MarketTapeDown")
        else:
            self.ah_value.setObjectName("MarketTapeUp")

        self.ah_value.setText(str(ah_change))
        self.ah_value.style().unpolish(self.ah_value)
        self.ah_value.style().polish(self.ah_value)


class StocksPanel(QWidget):
    hide_requested = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("MarketTapeCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet("""
            QWidget#MarketTapeCard {
                margin-bottom: 9px;
            }
        """)

        self.index_widgets = []
        self.stock_widgets = []

        main = QVBoxLayout()
        main.setContentsMargins(10, 5, 10, 10)
        main.setSpacing(4)
        self.setLayout(main)

        header = QHBoxLayout()
        header.setSpacing(6)

        title_block = QVBoxLayout()
        title_block.setSpacing(0)

        title = QLabel("MARKET TAPE")
        title.setObjectName("MarketTapeTitle")
        title.setAlignment(Qt.AlignLeft)

        self.subtitle = QLabel("Latest Price  •  3 Month Trend")
        self.subtitle.setObjectName("MarketTapeSubtitle")
        self.subtitle.setAlignment(Qt.AlignLeft)

        title_block.addWidget(title)
        title_block.addWidget(self.subtitle)

        self.hide_button = QPushButton("Hide")
        self.hide_button.setObjectName("MarketTapeHideButton")
        self.hide_button.setCursor(Qt.PointingHandCursor)
        self.hide_button.setFixedHeight(18)
        self.hide_button.clicked.connect(self.hide_requested.emit)
        self.hide_button.setStyleSheet("""
            QPushButton#MarketTapeHideButton {
                color: #f7f0df;
                background: rgba(20, 35, 52, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.42);
                border-radius: 5px;
                padding: 1px 7px;
                font-family: "Times New Roman";
                font-size: 8px;
                font-weight: 900;
            }

            QPushButton#MarketTapeHideButton:hover {
                background: rgba(20, 35, 52, 0.95);
                border-color: rgba(255, 255, 255, 0.78);
            }
        """)

        header.addLayout(title_block, 1)
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

        main.addLayout(index_row)

        divider = QLabel("FAVORITES")
        divider.setObjectName("MarketTapeSectionLabel")
        divider.setAlignment(Qt.AlignLeft)
        main.addWidget(divider)

        stock_grid = QGridLayout()
        stock_grid.setHorizontalSpacing(5)
        stock_grid.setVerticalSpacing(3)
        stock_grid.setContentsMargins(0, 0, 0, 0)
        stock_grid.setRowMinimumHeight(0, 65)
        stock_grid.setRowMinimumHeight(1, 65)

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

        main.addLayout(stock_grid)
        main.addStretch(1)

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
