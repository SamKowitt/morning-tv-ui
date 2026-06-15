from PySide6.QtCore import QObject, QThread, Signal, Qt, QSettings, QEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from services.news_fetcher import NEWS_SOURCES, NEWS_SOURCE_OPTIONS, fetch_news_cards, get_news_source_display
from services.sports_games_fetcher import fetch_current_sports_games
from services.sports_news_fetcher import fetch_espn_sports_articles
from services.stock_fetcher import fetch_market_data
from services.weather_fetcher import fetch_weather_rows, validate_zip_code

from ui.styles import APP_STYLE
from ui.panels.date_card import DateCard
from ui.panels.weather_panel import WeatherPanel
from ui.panels.sports_news_panel import SportsNewsPanel
from ui.panels.news_card import NewsCard
from ui.panels.sports_games_panel import SportsGamesPanel
from ui.panels.stocks_panel import StocksPanel
from ui.panels.reminders_panel import RemindersPanel


class WeatherFetchWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, zip_code="44865"):
        super().__init__()
        self.zip_code = zip_code

    def run(self):
        try:
            rows = fetch_weather_rows(max_rows=9, zip_code=self.zip_code)
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
    finished = Signal(int, str, str, object, object)
    failed = Signal(int, str)

    def __init__(self, request_id, left_source_key="FOX", right_source_key="CNBC"):
        super().__init__()
        self.request_id = request_id
        self.left_source_key = left_source_key
        self.right_source_key = right_source_key

    def run(self):
        try:
            left_article, right_article = fetch_news_cards(
                left_source_key=self.left_source_key,
                right_source_key=self.right_source_key,
            )
            self.finished.emit(
                self.request_id,
                self.left_source_key,
                self.right_source_key,
                left_article,
                right_article,
            )
        except Exception as error:
            self.failed.emit(self.request_id, str(error))


class SportsGamesFetchWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            leagues = fetch_current_sports_games(max_games_per_league=3)
            self.finished.emit(leagues)
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

        self.saved_settings = QSettings("MorningTVUI", "MorningTVUI")

        self.left_news_source_key = self.load_saved_news_source(
            setting_name="left_news_source_key",
            default_value="FOX",
        )
        self.right_news_source_key = self.load_saved_news_source(
            setting_name="right_news_source_key",
            default_value="CNBC",
        )

        self.weather_zip_code = self.load_saved_weather_zip()

        self.weather_location_label = self.load_saved_weather_location_label()

        self.news_request_id = 0

        self.root = QWidget()
        self.root.setObjectName("RootWidget")
        self.setCentralWidget(self.root)

        self.page_stack = QStackedLayout()
        self.page_stack.setContentsMargins(0, 0, 0, 0)
        self.root.setLayout(self.page_stack)

        self.dashboard_page = QWidget()
        self.dashboard_page.setObjectName("DashboardPage")

        main = QHBoxLayout()
        main.setContentsMargins(
            self.outer_margin,
            self.outer_margin,
            self.outer_margin,
            self.outer_margin,
        )
        main.setSpacing(self.main_spacing)
        self.dashboard_page.setLayout(main)

        left_column = QVBoxLayout()
        left_column.setSpacing(14)
        left_column.setContentsMargins(0, 0, 0, 0)

        self.date_card = DateCard()
        self.install_date_card_location_label()

        self.weather_panel = WeatherPanel()

        left_column.addWidget(self.date_card, 22)
        left_column.addWidget(self.weather_panel, 78)

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

        self.settings_page = self.build_settings_page()
        self.page_stack.addWidget(self.dashboard_page)
        self.page_stack.addWidget(self.settings_page)
        self.page_stack.setCurrentWidget(self.dashboard_page)

        self.settings_button = QPushButton("⚙", self.root)
        self.settings_button.setObjectName("DashboardSettingsButton")
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.setFixedSize(30, 30)
        self.settings_button.clicked.connect(self.show_settings_page)

        self.apply_forced_row_heights()
        self.position_settings_button()

        self.start_news_fetch()
        self.start_sports_news_fetch()
        self.start_sports_games_fetch()
        self.start_stock_fetch()
        self.start_weather_fetch()

    def valid_news_source_keys(self):
        return {source_key for source_key, _label in NEWS_SOURCE_OPTIONS}


    def load_saved_news_source(self, setting_name, default_value):
        saved_value = self.saved_settings.value(setting_name, default_value)

        if saved_value in self.valid_news_source_keys():
            return saved_value

        return default_value

    def save_news_source_settings(self):
        self.saved_settings.setValue("left_news_source_key", self.left_news_source_key)
        self.saved_settings.setValue("right_news_source_key", self.right_news_source_key)
        self.saved_settings.sync()

        print(
            "Saved news settings -> "
            f"left: {self.left_news_source_key}, right: {self.right_news_source_key}"
        )

    def load_saved_weather_zip(self):
        saved_zip = str(self.saved_settings.value("weather_zip_code", "44865") or "44865")
        cleaned_zip = "".join(ch for ch in saved_zip if ch.isdigit())

        if len(cleaned_zip) == 5:
            return cleaned_zip

        return "44865"

    def load_saved_weather_location_label(self):
        saved_label = str(
            self.saved_settings.value("weather_location_label", "") or ""
        ).strip()

        # If we already saved a real city/state label, use it.
        if saved_label and not saved_label.isdigit():
            return saved_label

        # Otherwise resolve the saved ZIP into city/state.
        try:
            location = validate_zip_code(self.weather_zip_code)
            return self.city_name_from_weather_location(location)
        except Exception as error:
            print(f"Could not resolve saved weather ZIP location label: {error}")

        return ""

    def city_name_from_weather_location(self, location):
        label = getattr(location, "label", "") or ""
        zip_code = getattr(location, "zip_code", self.weather_zip_code)

        # Expected label format: "44865 — North Fairfield, OH"
        if "—" in label:
            return label.split("—", 1)[1].strip()

        if "-" in label:
            return label.split("-", 1)[1].strip()

        cleaned = label.replace(str(zip_code), "").strip()
        cleaned = cleaned.strip("-").strip("—").strip()

        return cleaned or ""

    def install_date_card_location_label(self):
        initial_text = self.weather_location_label or ""

        self.date_location_label = QLabel(initial_text, self.date_card)
        self.date_location_label.setObjectName("DateLocationLabel")
        self.date_location_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.date_location_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.date_location_label.show()
        self.sync_date_location_label_style()

        self.date_card.installEventFilter(self)
        self.position_date_location_label()

    def position_date_location_label(self):
        if not hasattr(self, "date_location_label"):
            return

        label_height = 18
        left_margin = 16
        bottom_margin = 2
        width = max(80, self.date_card.width() - 32)

        self.date_location_label.setGeometry(
            left_margin,
            max(0, self.date_card.height() - label_height - bottom_margin),
            width,
            label_height,
        )

        self.date_location_label.raise_()

    def set_date_card_location_label(self, location_label):
        if not hasattr(self, "date_location_label"):
            return

        text = str(location_label or "").strip()
        self.date_location_label.setText(text)
        self.position_date_location_label()

    def eventFilter(self, watched, event):
        if (
                hasattr(self, "date_card")
                and watched is self.date_card
                and event.type() == QEvent.Resize
        ):
            self.position_date_location_label()

        return super().eventFilter(watched, event)

    def save_weather_zip_setting(self):
        self.saved_settings.setValue("weather_zip_code", self.weather_zip_code)
        self.saved_settings.setValue("weather_location_label", self.weather_location_label)
        self.saved_settings.sync()

        print(
            f"Saved weather ZIP code -> {self.weather_zip_code} "
            f"({self.weather_location_label})"
        )

    def build_top_row(self):
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sports_news = SportsNewsPanel()
        self.sports_games = SportsGamesPanel()

        layout.addWidget(self.sports_news, 1)
        layout.addWidget(self.sports_games, 1)

        return layout

    def build_middle_row(self):
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        self.fox_card = NewsCard(
            headline=f"Loading latest {get_news_source_display(self.left_news_source_key)} headline...",
            source=get_news_source_display(self.left_news_source_key),
            image_label="LOADING",
            variant="fox",
        )

        self.cnbc_card = NewsCard(
            headline=f"Loading latest {get_news_source_display(self.right_news_source_key)} headline...",
            source=get_news_source_display(self.right_news_source_key),
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

    def build_settings_page(self):
        page = QWidget()
        page.setObjectName("SettingsPage")

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        page.setLayout(outer)

        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setFixedWidth(560)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(16)
        card.setLayout(card_layout)

        title = QLabel("SETTINGS")
        title.setObjectName("SettingsTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Choose the news sources for the two article cards.")
        subtitle.setObjectName("SettingsSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)

        left_label = QLabel("LEFT ARTICLE")
        left_label.setObjectName("SettingsFieldLabel")

        self.left_news_combo = QComboBox()
        self.left_news_combo.setObjectName("SettingsComboBox")

        right_label = QLabel("RIGHT ARTICLE")
        right_label.setObjectName("SettingsFieldLabel")

        self.right_news_combo = QComboBox()
        self.right_news_combo.setObjectName("SettingsComboBox")

        for source_key, label in NEWS_SOURCE_OPTIONS:
            self.left_news_combo.addItem(label, source_key)
            self.right_news_combo.addItem(label, source_key)

        self.set_combo_to_source(self.left_news_combo, self.left_news_source_key)
        self.set_combo_to_source(self.right_news_combo, self.right_news_source_key)

        weather_label = QLabel("WEATHER ZIP CODE")
        weather_label.setObjectName("SettingsFieldLabel")

        self.weather_zip_input = QLineEdit()
        self.weather_zip_input.setObjectName("SettingsLineEdit")
        self.weather_zip_input.setPlaceholderText("Enter 5-digit ZIP code")
        self.weather_zip_input.setMaxLength(5)
        self.weather_zip_input.setText(self.weather_zip_code)

        card_layout.addWidget(left_label)
        card_layout.addWidget(self.left_news_combo)
        card_layout.addWidget(right_label)
        card_layout.addWidget(self.right_news_combo)
        card_layout.addWidget(weather_label)
        card_layout.addWidget(self.weather_zip_input)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 8, 0, 0)
        button_row.setSpacing(12)

        self.settings_back_button = QPushButton("Back")

        self.settings_back_button.setObjectName("SettingsSecondaryButton")
        self.settings_back_button.setCursor(Qt.PointingHandCursor)
        self.settings_back_button.clicked.connect(self.show_dashboard_page)

        self.settings_apply_button = QPushButton("Apply")
        self.settings_apply_button.setObjectName("SettingsPrimaryButton")
        self.settings_apply_button.setCursor(Qt.PointingHandCursor)
        self.settings_apply_button.clicked.connect(self.apply_news_settings)
        settings_button_style = """
        QPushButton {
            background-color: #d8c7a4;
            color: #2d2114;
            border: 2px solid #8b6d3e;
            border-radius: 12px;
            padding: 10px 18px;
            font-size: 15px;
            font-weight: 900;
        }

        QPushButton:hover {
            background-color: #eadab7;
            color: #2d2114;
        }

        QPushButton:pressed {
            background-color: #b79b6a;
            color: #2d2114;
        }

        QPushButton:disabled {
            background-color: #d8c7a4;
            color: #2d2114;
            border: 2px solid #8b6d3e;
        }
        """

        apply_button_style = """
        QPushButton {
            background-color: #72542d;
            color: #f7f0df;
            border: 2px solid #4d351b;
            border-radius: 12px;
            padding: 10px 18px;
            font-size: 15px;
            font-weight: 900;
        }

        QPushButton:hover {
            background-color: #846236;
            color: #f7f0df;
        }

        QPushButton:pressed {
            background-color: #5c4324;
            color: #f7f0df;
        }

        QPushButton:disabled {
            background-color: #72542d;
            color: #f7f0df;
            border: 2px solid #4d351b;
        }
        """
        self.settings_back_button.setStyleSheet(settings_button_style)
        self.settings_apply_button.setStyleSheet(apply_button_style)
        button_row.addWidget(self.settings_back_button)
        button_row.addWidget(self.settings_apply_button)

        card_layout.addLayout(button_row)

        outer.addStretch(1)

        center_row = QHBoxLayout()
        center_row.setContentsMargins(0, 0, 0, 0)
        center_row.addStretch(1)
        center_row.addWidget(card)
        center_row.addStretch(1)
        outer.addLayout(center_row)

        outer.addStretch(1)

        return page

    def set_combo_to_source(self, combo, source_key):
        for index in range(combo.count()):
            if combo.itemData(index) == source_key:
                combo.setCurrentIndex(index)
                return

    def show_settings_page(self):
        self.set_combo_to_source(self.left_news_combo, self.left_news_source_key)
        self.set_combo_to_source(self.right_news_combo, self.right_news_source_key)
        self.weather_zip_input.setText(self.weather_zip_code)
        self.settings_button.hide()
        self.page_stack.setCurrentWidget(self.settings_page)

    def show_dashboard_page(self):
        self.page_stack.setCurrentWidget(self.dashboard_page)
        self.settings_button.show()
        self.position_settings_button()

    def apply_news_settings(self):
        requested_zip = "".join(
            ch for ch in self.weather_zip_input.text().strip() if ch.isdigit()
        )

        try:
            validated_location = validate_zip_code(requested_zip)
        except Exception as error:
            QMessageBox.warning(
                self,
                "Invalid ZIP Code",
                str(error),
            )
            self.weather_zip_input.setFocus()
            return

        old_weather_zip = self.weather_zip_code

        self.left_news_source_key = self.left_news_combo.currentData() or "FOX"
        self.right_news_source_key = self.right_news_combo.currentData() or "CNBC"
        self.weather_zip_code = validated_location.zip_code

        self.weather_location_label = self.city_name_from_weather_location(validated_location)
        self.set_date_card_location_label(self.weather_location_label)

        self.save_news_source_settings()
        self.save_weather_zip_setting()

        self.refresh_news_card_placeholders()
        self.show_dashboard_page()
        self.start_news_fetch()

        if self.weather_zip_code != old_weather_zip:
            self.refresh_weather_placeholders()
            self.start_weather_fetch()

    def refresh_news_card_placeholders(self):
        left_label = get_news_source_display(self.left_news_source_key)
        right_label = get_news_source_display(self.right_news_source_key)

        self.fox_card.top_source_label.setText(left_label)
        self.fox_card.image.set_source_text(left_label)
        self.fox_card.headline_label.setText(f"Loading latest {left_label} headline...")
        self.fox_card.read_label.setText("")
        self.fox_card.image.set_pixmap_from_data(b"")

        self.cnbc_card.top_source_label.setText(right_label)
        self.cnbc_card.image.set_source_text(right_label)
        self.cnbc_card.headline_label.setText(f"Loading latest {right_label} headline...")
        self.cnbc_card.read_label.setText("")
        self.cnbc_card.image.set_pixmap_from_data(b"")

    def sync_date_location_label_style(self):
        if not hasattr(self, "date_location_label"):
            return

        source_label = None

        if hasattr(self.date_card, "current_weather_label"):
            source_label = self.date_card.current_weather_label
        elif hasattr(self.date_card, "current_temp_label"):
            source_label = self.date_card.current_temp_label

        if source_label is None:
            return

        source_palette = source_label.palette()
        text_color = source_palette.color(source_label.foregroundRole()).name()

        self.date_location_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                background: transparent;
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 0.4px;
            }}
        """)

    def refresh_weather_placeholders(self):
        print(f"Refreshing weather placeholders for ZIP {self.weather_zip_code}")

        if hasattr(self.weather_panel, "update_weather_rows"):
            self.weather_panel.update_weather_rows([])

        if hasattr(self.date_card, "current_weather_label"):
            self.date_card.current_weather_label.setText("--°")

    def position_settings_button(self):
        if not hasattr(self, "settings_button"):
            return

        x = 4
        y = max(4, self.root.height() - self.settings_button.height() - 4)
        self.settings_button.move(x, y)
        self.settings_button.raise_()

    def force_clear_news_card(self, card, source_key):
        label = get_news_source_display(source_key)

        card.source = label
        card.article_url = ""

        card.top_source_label.setText(label)
        card.image.set_source_text(label)
        card.image.set_label_text("LOADING")
        card.image.set_pixmap_from_data(b"")

        card.headline_label.setText(f"Loading latest {label} headline...")
        card.read_label.setText("")
        card.page_label.setText("PAGE 1")

        card.update()
        card.repaint()

    def article_matches_selected_source(self, article, source_key):
        config = NEWS_SOURCES.get(source_key)

        if not config:
            return False

        expected_source = config["source_name"]
        expected_domain = config["allowed_domain"]

        article_title = getattr(article, "title", "") or ""
        article_source = getattr(article, "source", "") or ""
        article_link = getattr(article, "link", "") or ""
        article_image_url = getattr(article, "image_url", "") or ""

        print(
            f"Checking article for {expected_source}: "
            f"source={article_source}, link={article_link}, title={article_title}"
        )

        if article_source and article_source != expected_source:
            print(
                f"Rejecting article for {expected_source}: "
                f"article source was {article_source}"
            )
            return False

        if not article_link or expected_domain not in article_link:
            print(
                f"Rejecting article for {expected_source}: "
                f"missing or wrong-domain link: {article_link}"
            )
            return False

        allowed_image_domains = [expected_domain]

        if source_key == "CNBC":
            allowed_image_domains.extend([
                "cnbcfm.com",
                "image.cnbcfm.com",
            ])

        if source_key == "BLOOMBERG":
            allowed_image_domains.extend([
                "bwbx.io",
                "assets.bwbx.io",
                "images.bloomberg.com",
                "assets.bloomberg.com",
                "assets.bloombergmedia.com",
            ])

        if article_image_url and not any(domain in article_image_url for domain in allowed_image_domains):
            print(
                f"Removing wrong-domain image for {expected_source}: "
                f"{article_image_url}"
            )
            article.image_url = ""
            article.image_bytes = b""

        article.source = expected_source
        return True

    def reject_mismatched_news_card(self, card, source_key):
        label = get_news_source_display(source_key)

        card.top_source_label.setText(label)
        card.image.set_source_text(label)
        card.headline_label.setText(f"Unable to load latest {label} headline.")
        card.read_label.setText("")
        card.image.set_pixmap_from_data(b"")

    def start_weather_fetch(self):
        self.weather_thread = QThread()
        self.weather_worker = WeatherFetchWorker(zip_code=self.weather_zip_code)

        self.weather_worker.moveToThread(self.weather_thread)

        self.weather_thread.started.connect(self.weather_worker.run)
        self.weather_worker.finished.connect(self.on_weather_loaded)
        self.weather_worker.failed.connect(self.on_weather_failed)

        self.weather_worker.finished.connect(self.weather_thread.quit)
        self.weather_worker.failed.connect(self.weather_thread.quit)

        self.weather_thread.finished.connect(self.weather_worker.deleteLater)
        self.weather_thread.finished.connect(self.weather_thread.deleteLater)

        self.weather_thread.start()

    def on_weather_loaded(self, rows):
        print("Weather data loaded into panel.")

        if hasattr(self.weather_panel, "update_weather_rows"):
            self.weather_panel.update_weather_rows(rows)

        if rows:
            self.date_card.update_current_weather(rows[0])

            if hasattr(self.date_card, "update_low_high_from_rows"):
                self.date_card.update_low_high_from_rows(rows)

        self.sync_date_location_label_style()
        self.position_date_location_label()

    def on_weather_failed(self, message):
        print(f"Weather fetch failed: {message}")

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

    def start_sports_games_fetch(self):
        self.sports_games_thread = QThread()
        self.sports_games_worker = SportsGamesFetchWorker()
        self.sports_games_worker.moveToThread(self.sports_games_thread)

        self.sports_games_thread.started.connect(self.sports_games_worker.run)

        self.sports_games_worker.finished.connect(self.on_sports_games_loaded)
        self.sports_games_worker.failed.connect(self.on_sports_games_failed)

        self.sports_games_worker.finished.connect(self.sports_games_thread.quit)
        self.sports_games_worker.failed.connect(self.sports_games_thread.quit)

        self.sports_games_thread.finished.connect(self.sports_games_worker.deleteLater)
        self.sports_games_thread.finished.connect(self.sports_games_thread.deleteLater)

        self.sports_games_thread.start()

    def on_sports_games_loaded(self, leagues):
        print("Live sports games loaded.")

        if hasattr(self.sports_games, "update_leagues"):
            self.sports_games.update_leagues(leagues)

    def on_sports_games_failed(self, error_message):
        print(f"Sports games fetch failed: {error_message}")

        if hasattr(self.sports_games, "set_error"):
            self.sports_games.set_error("Unable to load live MLB, NFL, and NBA games.")

    def start_news_fetch(self):
        self.news_request_id += 1
        request_id = self.news_request_id

        left_source_key = self.left_news_source_key
        right_source_key = self.right_news_source_key

        print(
            f"Starting news fetch request {request_id}: "
            f"left={left_source_key}, right={right_source_key}"
        )

        self.news_thread = QThread()
        self.news_worker = NewsFetchWorker(
            request_id=request_id,
            left_source_key=left_source_key,
            right_source_key=right_source_key,
        )
        self.news_worker.moveToThread(self.news_thread)

        self.news_thread.started.connect(self.news_worker.run)

        self.news_worker.finished.connect(self.on_news_loaded)
        self.news_worker.failed.connect(self.on_news_failed)

        self.news_worker.finished.connect(self.news_thread.quit)
        self.news_worker.failed.connect(self.news_thread.quit)

        self.news_thread.finished.connect(self.news_worker.deleteLater)
        self.news_thread.finished.connect(self.news_thread.deleteLater)

        self.news_thread.start()

    def on_news_loaded(self, request_id, left_source_key, right_source_key, left_article, right_article):
        if request_id != self.news_request_id:
            print(
                f"Ignoring stale news fetch request {request_id}; "
                f"latest request is {self.news_request_id}"
            )
            return

        if left_source_key != self.left_news_source_key or right_source_key != self.right_news_source_key:
            print(
                "Ignoring news result because source settings changed while it was loading: "
                f"result left={left_source_key}, right={right_source_key}; "
                f"current left={self.left_news_source_key}, right={self.right_news_source_key}"
            )
            return

        print(
            f"Applying news fetch request {request_id}: "
            f"left={left_source_key}, right={right_source_key}"
        )

        if self.article_matches_selected_source(left_article, left_source_key):
            self.force_clear_news_card(self.fox_card, left_source_key)
            self.fox_card.update_article(left_article)
            print(f"LEFT CARD NOW SET TO: {left_article.source} | {left_article.title}")
        else:
            self.reject_mismatched_news_card(self.fox_card, left_source_key)

        if self.article_matches_selected_source(right_article, right_source_key):
            self.force_clear_news_card(self.cnbc_card, right_source_key)
            self.cnbc_card.update_article(right_article)
            print(f"RIGHT CARD NOW SET TO: {right_article.source} | {right_article.title}")
        else:
            self.reject_mismatched_news_card(self.cnbc_card, right_source_key)

    def on_news_failed(self, request_id, error_message):
        if request_id != self.news_request_id:
            print(
                f"Ignoring stale failed news fetch request {request_id}; "
                f"latest request is {self.news_request_id}"
            )
            return

        print(f"News fetch failed: {error_message}")

        left_label = get_news_source_display(self.left_news_source_key)
        right_label = get_news_source_display(self.right_news_source_key)

        self.fox_card.headline_label.setText(
            f"Unable to load latest {left_label} headline."
        )
        self.cnbc_card.headline_label.setText(
            f"Unable to load latest {right_label} headline."
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_forced_row_heights()
        self.position_settings_button()

    def apply_forced_row_heights(self):
        available_height = (
            self.height()
            - (self.outer_margin * 2)
            - (self.row_spacing * 2)
        )

        top_height = int(available_height * 0.25)
        middle_height = int(available_height * 0.50)
        bottom_height = available_height - top_height - middle_height

        self.top_row_widget.setFixedHeight(top_height)
        self.middle_row_widget.setFixedHeight(middle_height)
        self.bottom_row_widget.setFixedHeight(bottom_height)

        print(
            f"FORCED HEIGHTS -> top: {top_height}, middle: {middle_height}, bottom: {bottom_height}"
        )