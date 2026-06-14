from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QSizePolicy

from services.stock_fetcher import fetch_market_data
from ui.styles import APP_STYLE
from ui.panels.date_card import DateCard
from ui.panels.weather_panel import WeatherPanel
from ui.panels.sports_news_panel import SportsNewsPanel
from ui.panels.news_card import NewsCard
from ui.panels.sports_games_panel import SportsGamesPanel
from ui.panels.stocks_panel import StocksPanel
from ui.panels.reminders_panel import RemindersPanel
from services.news_fetcher import fetch_news_cards
from services.sports_news_fetcher import fetch_espn_sports_articles
from services.weather_fetcher import fetch_weather_rows

class WeatherFetchWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            rows = fetch_weather_rows(max_rows=9)
            self.finished.emit(rows)
        except Exception as error:
            self.failed.emit(str(error))

class SportsNewsFetchWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            articles = fetch_espn_sports_articles(max_articles=4)
            self.finished.emit(articles)
        except Exception as error:
            self.failed.emit(str(error))


class NewsFetchWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)

    def run(self):
        try:
            fox_article, cnbc_article = fetch_news_cards()
            self.finished.emit(fox_article, cnbc_article)
        except Exception as error:
            self.failed.emit(str(error))

class StockFetchWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            market_data = fetch_market_data()
            self.finished.emit(market_data)
        except Exception as error:
            self.failed.emit(str(error))


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        print("LOADED DASHBOARD_WINDOW: forced row container version with live news")

        self.setWindowTitle("Morning TV UI")
        self.resize(1280, 720)
        self.setStyleSheet(APP_STYLE)

        self.outer_margin = 18
        self.main_spacing = 16
        self.row_spacing = 14

        root = QWidget()
        root.setObjectName("RootWidget")
        self.setCentralWidget(root)

        main = QHBoxLayout()
        main.setContentsMargins(
            self.outer_margin,
            self.outer_margin,
            self.outer_margin,
            self.outer_margin,
        )
        main.setSpacing(self.main_spacing)
        root.setLayout(main)

        # Left column
        left_column = QVBoxLayout()
        left_column.setSpacing(14)
        left_column.setContentsMargins(0, 0, 0, 0)

        self.date_card = DateCard()
        self.weather_panel = WeatherPanel()

        left_column.addWidget(self.date_card, 22)
        left_column.addWidget(self.weather_panel, 78)

        # Right dashboard
        self.right_area = QVBoxLayout()
        self.right_area.setSpacing(self.row_spacing)
        self.right_area.setContentsMargins(0, 0, 0, 0)

        self.top_row_widget = QWidget()
        self.middle_row_widget = QWidget()
        self.bottom_row_widget = QWidget()

        for row_widget in [
            self.top_row_widget,
            self.middle_row_widget,
            self.bottom_row_widget,
        ]:
            row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.top_row_widget.setLayout(self.build_top_row())
        self.middle_row_widget.setLayout(self.build_middle_row())
        self.bottom_row_widget.setLayout(self.build_bottom_row())

        self.right_area.addWidget(self.top_row_widget)
        self.right_area.addWidget(self.middle_row_widget)
        self.right_area.addWidget(self.bottom_row_widget)

        main.addLayout(left_column, 14)
        main.addLayout(self.right_area, 86)

        self.apply_forced_row_heights()

        # Live headline fetch only. This does not affect layout.
        self.start_news_fetch()
        self.start_sports_news_fetch()
        self.start_stock_fetch()
        self.start_weather_fetch()

    def start_weather_fetch(self):
        self.weather_thread = QThread()
        self.weather_worker = WeatherFetchWorker()

        self.weather_worker.moveToThread(self.weather_thread)

        self.weather_thread.started.connect(self.weather_worker.run)
        self.weather_worker.finished.connect(self.on_weather_loaded)
        self.weather_worker.failed.connect(self.on_weather_failed)

        self.weather_worker.finished.connect(self.weather_thread.quit)
        self.weather_worker.failed.connect(self.weather_thread.quit)

        self.weather_thread.start()

    def on_weather_loaded(self, rows):
        print("Weather data loaded into panel.")

        if hasattr(self.weather_panel, "update_weather_rows"):
            self.weather_panel.update_weather_rows(rows)

        if rows and hasattr(self.date_card, "update_current_weather"):
            self.date_card.update_current_weather(rows[0])

    def on_weather_failed(self, message):
        print(f"Weather fetch failed: {message}")

    def build_top_row(self):
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sports_news = SportsNewsPanel()
        self.sports_games = SportsGamesPanel()

        layout.addWidget(self.sports_news, 1)
        layout.addWidget(self.sports_games, 1)

        return layout

    def start_stock_fetch(self):
        self.stock_thread = QThread()
        self.stock_worker = StockFetchWorker()
        self.stock_worker.moveToThread(self.stock_thread)

        self.stock_thread.started.connect(self.stock_worker.run)

        self.stock_worker.finished.connect(self.on_stock_data_loaded)
        self.stock_worker.failed.connect(self.on_stock_data_failed)

        self.stock_worker.finished.connect(self.stock_thread.quit)
        self.stock_worker.failed.connect(self.stock_thread.quit)

        self.stock_thread.finished.connect(self.stock_worker.deleteLater)
        self.stock_thread.finished.connect(self.stock_thread.deleteLater)

        self.stock_thread.start()

    def on_stock_data_loaded(self, market_data):
        self.stocks_panel.update_market_data(market_data)

    def on_stock_data_failed(self, error_message):
        print(f"Stock data fetch failed: {error_message}")

    def start_sports_news_fetch(self):
        self.sports_news_thread = QThread()
        self.sports_news_worker = SportsNewsFetchWorker()
        self.sports_news_worker.moveToThread(self.sports_news_thread)

        self.sports_news_thread.started.connect(self.sports_news_worker.run)

        self.sports_news_worker.finished.connect(self.on_sports_news_loaded)
        self.sports_news_worker.failed.connect(self.on_sports_news_failed)

        self.sports_news_worker.finished.connect(self.sports_news_thread.quit)
        self.sports_news_worker.failed.connect(self.sports_news_thread.quit)

        self.sports_news_thread.finished.connect(self.sports_news_worker.deleteLater)
        self.sports_news_thread.finished.connect(self.sports_news_thread.deleteLater)

        self.sports_news_thread.start()

    def on_sports_news_loaded(self, articles):
        self.sports_news.update_articles(articles)

    def on_sports_news_failed(self, error_message):
        print(f"ESPN sports news fetch failed: {error_message}")

    def build_middle_row(self):
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        self.fox_card = NewsCard(
            headline="Loading latest Fox News headline...",
            source="FOX NEWS",
            image_label="LOADING",
            variant="fox",
        )

        self.cnbc_card = NewsCard(
            headline="Loading latest CNBC headline...",
            source="CNBC",
            image_label="LOADING",
            variant="cnbc",
        )

        layout.addWidget(self.fox_card, 1)
        layout.addWidget(self.cnbc_card, 1)

        return layout

    def build_bottom_row(self):
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stocks_panel = StocksPanel()
        self.reminders = RemindersPanel()

        layout.addWidget(self.reminders, 1)
        layout.addWidget(self.stocks_panel, 1)

        return layout

    def start_news_fetch(self):
        self.news_thread = QThread()
        self.news_worker = NewsFetchWorker()
        self.news_worker.moveToThread(self.news_thread)

        self.news_thread.started.connect(self.news_worker.run)

        self.news_worker.finished.connect(self.on_news_loaded)
        self.news_worker.failed.connect(self.on_news_failed)

        self.news_worker.finished.connect(self.news_thread.quit)
        self.news_worker.failed.connect(self.news_thread.quit)

        self.news_thread.finished.connect(self.news_worker.deleteLater)
        self.news_thread.finished.connect(self.news_thread.deleteLater)

        self.news_thread.start()

    def on_news_loaded(self, fox_article, cnbc_article):
        self.fox_card.update_article(fox_article)
        self.cnbc_card.update_article(cnbc_article)

    def on_news_failed(self, error_message):
        print(f"News fetch failed: {error_message}")

        self.fox_card.headline_label.setText(
            "Unable to load latest Fox News headline."
        )
        self.cnbc_card.headline_label.setText(
            "Unable to load latest CNBC headline."
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_forced_row_heights()

    def apply_forced_row_heights(self):
        available_height = (
            self.height()
            - (self.outer_margin * 2)
            - (self.row_spacing * 2)
        )

        # Keep your working proportions.
        top_height = int(available_height * 0.25)
        middle_height = int(available_height * 0.50)
        bottom_height = available_height - top_height - middle_height

        self.top_row_widget.setFixedHeight(top_height)
        self.middle_row_widget.setFixedHeight(middle_height)
        self.bottom_row_widget.setFixedHeight(bottom_height)

        print(
            f"FORCED HEIGHTS -> top: {top_height}, middle: {middle_height}, bottom: {bottom_height}"
        )