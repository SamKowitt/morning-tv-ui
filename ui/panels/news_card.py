import base64
import html as html_module
import re
import random
from urllib.parse import unquote
from PySide6.QtCore import Qt, QRectF, QUrl, QSize, QEvent, QPointF, Signal, QThread, QTimer
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QImage, QTextDocument
from PySide6.QtWidgets import QSizePolicy, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QFrame, QDialog, QTextEdit, QTextBrowser, QPushButton

from ui.auto_fit_label import AutoFitLabel
from ui.newspaper_chrome import draw_stacked_newspaper_panel
from services.article_text_fetcher import fetch_article_text_payload


class ResponsiveMiniHeadlineLabel(QLabel):
    """
    Mini-news headline with one fixed font size.

    Long titles stay the same size and end with an ellipsis.
    """

    FONT_SIZE = 14

    def __init__(self, text=""):
        super().__init__()

        self.full_title = ""
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setContentsMargins(0, 0, 0, 0)

        self.setText(text)

    def setText(self, text):
        self.full_title = " ".join(str(text or "").split())
        super().setText(self.full_title)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        font = QFont("Georgia")
        font.setPointSize(self.FONT_SIZE)
        font.setBold(True)

        painter.setFont(font)
        painter.setPen(QColor("#17100a"))

        rect = self.contentsRect()
        metrics = painter.fontMetrics()

        visible_text = metrics.elidedText(
            self.full_title,
            Qt.ElideRight,
            max(20, rect.width()),
        )

        painter.drawText(
            rect.adjusted(0, 0, 0, -3),
            Qt.AlignLeft | Qt.AlignBottom,
            visible_text,
        )
        painter.end()


class PaperRule(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setFixedHeight(1)
        self.setStyleSheet("background-color: rgba(90, 78, 63, 135); border: none;")


class NewspaperImagePanel(QWidget):
    def __init__(self, label_text="", source_text="", variant="FOX"):
        super().__init__()

        self.variant = variant
        self.label_text = label_text
        self.source_text = source_text
        self.original_pixmap = None

        self.breaking_headline = ""
        self.breaking_offset = 0
        self.breaking_timer = QTimer(self)
        self.breaking_timer.setInterval(28)
        self.breaking_timer.timeout.connect(self.advance_breaking_ticker)

        self.setObjectName("NewsPaperPhotoBox")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setMinimumHeight(150)

    def set_label_text(self, text):
        self.label_text = text
        self.update()

    def set_source_text(self, text):
        self.source_text = text
        self.update()

    def set_breaking_headline(self, text):
        self.breaking_headline = " ".join(str(text or "").split())
        self.breaking_offset = 0

        if self.breaking_headline:
            if not self.breaking_timer.isActive():
                self.breaking_timer.start()
        else:
            self.breaking_timer.stop()

        self.update()

    def advance_breaking_ticker(self):
        if not self.breaking_headline:
            self.breaking_timer.stop()
            return

        self.breaking_offset += 2

        font = QFont("Arial")
        font.setPointSize(12)
        font.setBold(True)

        metrics = QFontMetrics(font)
        ticker_text = f"   {self.breaking_headline}     •     {self.breaking_headline}     •"
        text_width = max(1, metrics.horizontalAdvance(ticker_text))

        if self.breaking_offset >= text_width:
            self.breaking_offset = 0

        self.update()

    def set_pixmap_from_data(self, data):
        if not data:
            self.original_pixmap = None
            self.update()
            return

        pixmap = QPixmap()
        loaded = pixmap.loadFromData(data)

        if loaded and not pixmap.isNull():
            self.original_pixmap = pixmap
        else:
            self.original_pixmap = None

        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Keep the headline image from getting pushed too low or too short.
        # It should always occupy at least half of the newspaper card height.
        if hasattr(self, "image") and self.image is not None:
            self.image.setMinimumHeight(max(135, int(self.height() * 0.52)))

        if hasattr(self, "headline_label") and self.headline_label is not None:
            self.headline_label.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(0, 0, 0, 0)

        path = QPainterPath()
        path.addRect(QRectF(rect))
        painter.setClipPath(path)

        if self.original_pixmap:
            target_size = QSize(
                int(rect.width() * 1.12),
                int(rect.height() * 1.12),
            )

            scaled = self.original_pixmap.scaled(
                target_size,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )

            x = int(rect.left() + (rect.width() - scaled.width()) / 2)

            # Top-align vertical cropping so faces/heads near the top of news photos
            # are preserved instead of being cut off by center-cropping.
            y = int(rect.top())

            painter.drawPixmap(x, y, scaled)

            overlay = QLinearGradient(0, 0, 0, rect.height())
            overlay.setColorAt(0.0, QColor(0, 0, 0, 8))
            overlay.setColorAt(0.65, QColor(0, 0, 0, 18))
            overlay.setColorAt(1.0, QColor(0, 0, 0, 130))
            painter.fillRect(rect, overlay)
        else:
            self.draw_fallback_art(painter, rect)

        painter.setClipping(False)

        self.draw_breaking_banner(painter, rect)

        # No drawn border here; the newspaper panel already frames the section.


    def draw_breaking_banner(self, painter, rect):
        if not self.breaking_headline:
            return

        banner_height = min(34, max(26, int(rect.height() * 0.16)))
        banner_rect = QRectF(
            rect.left(),
            rect.top(),
            rect.width(),
            banner_height,
        )

        painter.save()
        painter.setClipRect(banner_rect)

        painter.fillRect(banner_rect, QColor("#8f120f"))

        label_width = min(112, max(92, int(rect.width() * 0.23)))
        label_rect = QRectF(
            banner_rect.left(),
            banner_rect.top(),
            label_width,
            banner_rect.height(),
        )

        painter.fillRect(label_rect, QColor("#f4e7cf"))

        label_font = QFont("Arial")
        label_font.setPointSize(10)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(QColor("#7e110d"))
        painter.drawText(
            label_rect.adjusted(7, 0, -6, 0),
            Qt.AlignLeft | Qt.AlignVCenter,
            "BREAKING",
        )

        ticker_rect = QRectF(
            label_rect.right(),
            banner_rect.top(),
            banner_rect.width() - label_rect.width(),
            banner_rect.height(),
        )

        ticker_font = QFont("Arial")
        ticker_font.setPointSize(12)
        ticker_font.setBold(True)
        painter.setFont(ticker_font)
        painter.setPen(QColor("#fff7e8"))

        ticker_text = f"   {self.breaking_headline}     •     {self.breaking_headline}     •"
        text_width = painter.fontMetrics().horizontalAdvance(ticker_text)

        start_x = ticker_rect.left() - self.breaking_offset

        while start_x < ticker_rect.right():
            painter.drawText(
                QRectF(
                    start_x,
                    ticker_rect.top(),
                    text_width + 4,
                    ticker_rect.height(),
                ),
                Qt.AlignLeft | Qt.AlignVCenter,
                ticker_text,
            )
            start_x += text_width

        painter.restore()

    def draw_fallback_art(self, painter, rect):
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())

        if self.variant == "FOX":
            gradient.setColorAt(0.0, QColor("#d9c8a8"))
            gradient.setColorAt(0.55, QColor("#8e9b8e"))
            gradient.setColorAt(1.0, QColor("#7b4f43"))
        else:
            gradient.setColorAt(0.0, QColor("#d9c8a8"))
            gradient.setColorAt(0.55, QColor("#759797"))
            gradient.setColorAt(1.0, QColor("#436775"))

        painter.fillRect(rect, gradient)

        painter.setPen(QPen(QColor(255, 248, 236, 150), 2))
        center_y = rect.center().y()
        painter.drawLine(rect.left() + 60, center_y, rect.right() - 60, center_y)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 248, 236, 175))
        painter.drawEllipse(rect.center().x() - 9, center_y - 9, 18, 18)

        painter.setPen(QColor(255, 248, 236, 220))
        font = painter.font()
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.source_text)

    def draw_photo_caption(self, painter, rect):
        caption_rect = QRectF(
            rect.left() + 10,
            rect.bottom() - 30,
            rect.width() - 20,
            20,
        )

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(38, 32, 27, 170))
        painter.drawRect(caption_rect)

        painter.setPen(QColor(255, 248, 236, 235))
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)

        caption = self.label_text or "LATEST"
        painter.drawText(
            caption_rect.adjusted(8, 0, -8, 0),
            Qt.AlignLeft | Qt.AlignVCenter,
            caption,
        )



class ArticleImageWorker(QThread):
    image_ready = Signal(int, str, bytes)
    failed = Signal(int, str)

    def __init__(self, request_token, source, article_url, image_url):
        super().__init__()
        self.request_token = request_token
        self.source = str(source or "")
        self.article_url = str(article_url or "")
        self.image_url = str(image_url or "")

    def run(self):
        try:
            source_upper = self.source.upper().strip()
            image_url = self.image_url
            image_bytes = b""

            if source_upper == "NEWSMAX":
                from services.newsmax_chrome import (
                    fetch_newsmax_article_image_url,
                    fetch_newsmax_image_jpeg_bytes,
                )

                if not image_url:
                    image_url = fetch_newsmax_article_image_url(self.article_url)

                if image_url:
                    image_bytes = fetch_newsmax_image_jpeg_bytes(image_url)

            else:
                from services.news_fetcher import (
                    download_image_bytes,
                    find_page_image_url,
                )

                if not image_url:
                    image_url = find_page_image_url(self.article_url)

                if image_url:
                    image_bytes = download_image_bytes(image_url)

            if not image_bytes:
                raise RuntimeError("No usable image bytes returned")

            self.image_ready.emit(
                self.request_token,
                image_url,
                image_bytes,
            )

        except Exception as error:
            self.failed.emit(self.request_token, str(error))


class ArticleTextWorker(QThread):
    finished_payload = Signal(object)
    failed = Signal(str)

    def __init__(self, article_url):
        super().__init__()
        self.article_url = article_url

    def run(self):
        try:
            payload = fetch_article_text_payload(self.article_url)
            self.finished_payload.emit(payload)
        except Exception as error:
            self.failed.emit(str(error))


class ConnectedNewspaperSpread(QWidget):
    """
    One continuous two-page newspaper surface.
    The labels sit on top of this background, while this widget paints the
    shared paper texture, outside border, and center fold.
    """

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(1, 1, -1, -1)

        paper = QLinearGradient(rect.topLeft(), rect.bottomRight())
        paper.setColorAt(0.0, QColor("#fff1d3"))
        paper.setColorAt(0.48, QColor("#f6e4bd"))
        paper.setColorAt(0.52, QColor("#ead4a8"))
        paper.setColorAt(1.0, QColor("#fff0d0"))

        painter.setPen(QPen(QColor(75, 51, 28, 185), 1))
        painter.setBrush(paper)
        painter.drawRect(rect)

        center_x = rect.center().x()

        # Dark recessed side of the fold.
        fold_shadow = QLinearGradient(center_x - 10, 0, center_x + 4, 0)
        fold_shadow.setColorAt(0.0, QColor(75, 48, 25, 0))
        fold_shadow.setColorAt(0.55, QColor(74, 45, 22, 95))
        fold_shadow.setColorAt(1.0, QColor(74, 45, 22, 0))
        painter.fillRect(
            QRectF(center_x - 10, rect.top(), 14, rect.height()),
            fold_shadow,
        )

        # Light raised side of the fold.
        fold_highlight = QLinearGradient(center_x - 1, 0, center_x + 10, 0)
        fold_highlight.setColorAt(0.0, QColor(255, 249, 225, 0))
        fold_highlight.setColorAt(0.45, QColor(255, 249, 225, 120))
        fold_highlight.setColorAt(1.0, QColor(255, 249, 225, 0))
        painter.fillRect(
            QRectF(center_x - 1, rect.top(), 12, rect.height()),
            fold_highlight,
        )

        painter.setPen(QPen(QColor(91, 59, 31, 120), 1))
        painter.drawLine(center_x, rect.top() + 2, center_x, rect.bottom() - 2)


class BackPageButton(QPushButton):
    """Navigation button with a manually positioned back-arrow glyph."""

    def __init__(self, parent=None):
        super().__init__("", parent)

    def paintEvent(self, event):
        # Draw the normal rounded button first.
        super().paintEvent(event)

        # Then draw only the arrow, raised slightly without clipping the frame.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        arrow_font = QFont("Georgia", 28)
        arrow_font.setBold(True)

        painter.setFont(arrow_font)
        painter.setPen(QColor("#24170d"))

        arrow_rect = QRectF(
            0,
            -2,
            self.width(),
            self.height(),
        )

        painter.drawText(arrow_rect, Qt.AlignCenter, "‹")
        painter.end()


class OpenNewspaperDialog(QDialog):
    def __init__(self, source, headline, article_url, parent=None):
        super().__init__(parent)

        self.source = source or "News"
        self.headline = headline or ""
        self.article_url = article_url or ""
        self.pages = []
        self.article_anchor_pages = {}
        self.article_image_resources = {}
        self.spread_index = 0
        self.worker = None

        self.setWindowTitle(f"{self.source} Article")
        self.setModal(False)

        # Keep this as an in-dashboard temporary overlay, not a second native Mac window.
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.resize(1120, 650)

        self.setStyleSheet("""
            QDialog {
                background-color: #2d2419;
            }

            QLabel#PopupMasthead {
                font-family: "Rockwell", "Georgia", serif;
                font-size: 27px;
                font-weight: 1000;
                color: #24170d;
                letter-spacing: 1.2px;
                background: transparent;
            }

            QLabel#PopupHeadline {
                font-family: "Georgia";
                font-size: 18px;
                font-weight: 900;
                color: #17100a;
                background: transparent;
            }

            QLabel#NewspaperPage,
            QTextEdit#NewspaperPage,
            QTextBrowser#NewspaperPage {
                background: transparent;
                color: #1b130c;
                border: none;
                border-radius: 0px;
                padding: 8px 18px;
                font-family: "American Typewriter", "Courier New", monospace;
                font-size: 21px;
                line-height: 156%;
            }

            QWidget#NewspaperFold {
                background: transparent;
                border: none;
            }

            QLabel#SpreadHeadline {
                background: transparent;
                color: #1b130c;
                font-family: "Georgia";
                font-size: 22px;
                font-weight: 1000;
                letter-spacing: -0.2px;
                padding: 0px 8px 8px 8px;
            }

            QPushButton#PageTurnButton {
                background-color: #f3e6c9;
                border: 2px solid rgba(70, 50, 28, 210);
                border-radius: 7px;
                color: #24170d;
                padding: 0px;
                min-width: 172px;
                max-width: 172px;
                min-height: 42px;
                max-height: 42px;
            }

            QPushButton#PageTurnButton:hover:enabled {
                background-color: #fff0cf;
            }

            QPushButton#PageTurnButton:disabled {
                background-color: rgba(243, 230, 201, 0.42);
                border-color: rgba(70, 50, 28, 100);
                color: rgba(36, 23, 13, 105);
            }

            QPushButton#ArticleCloseButton {
                background-color: #f3e6c9;
                border: 2px solid rgba(70, 50, 28, 210);
                border-radius: 5px;
                color: #24170d;
                font-family: "Georgia";
                font-size: 18px;
                font-weight: 1000;
                padding: 7px 18px;
                min-width: 120px;
                min-height: 34px;
            }

            QPushButton#ArticleCloseButton:hover {
                background-color: #fff0cf;
            }
        """)

        root = QVBoxLayout()
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        self.setLayout(root)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        self.masthead = QLabel(self.source)
        self.masthead.setObjectName("PopupMasthead")
        self.masthead.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.page_counter = QLabel("Loading article...")
        self.page_counter.setStyleSheet("""
            QLabel {
                color: #e8d8b6;
                font-family: "Times New Roman";
                font-size: 13px;
                font-weight: 900;
                letter-spacing: 1px;
                background: transparent;
            }
        """)
        self.page_counter.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header.addWidget(self.masthead, 1)
        header.addWidget(self.page_counter)
        root.addLayout(header)

        self.headline_label = QLabel(self.headline)
        self.headline_label.setObjectName("PopupHeadline")
        self.headline_label.setWordWrap(True)

        # The headline now appears on the newspaper paper itself,
        # rather than as dark text in the outer overlay header.
        self.headline_label.hide()

        self.spread_surface = ConnectedNewspaperSpread()
        self.spread_surface.setObjectName("ConnectedNewspaperSpread")

        spread_surface_layout = QVBoxLayout(self.spread_surface)
        spread_surface_layout.setContentsMargins(20, 14, 20, 12)
        spread_surface_layout.setSpacing(0)

        spread = QHBoxLayout()
        spread.setContentsMargins(0, 0, 0, 0)
        spread.setSpacing(0)

        # LEFT NEWSPAPER PAGE:
        # headline gets space here only, then the left article text begins.
        left_page_container = QWidget()
        left_page_layout = QVBoxLayout(left_page_container)
        left_page_layout.setContentsMargins(0, 0, 0, 0)
        left_page_layout.setSpacing(0)

        # The article headline is rendered inside Page 1's rich-text
        # content so the left browser remains full height on every spread.
        self.left_page = QTextBrowser()
        self.left_page.setObjectName("NewspaperPage")
        self.left_page.setReadOnly(True)
        self.left_page.setOpenLinks(False)
        self.left_page.setOpenExternalLinks(False)
        self.left_page.setTextInteractionFlags(
            Qt.LinksAccessibleByMouse
        )
        self.left_page.setFrameShape(QFrame.NoFrame)
        self.left_page.document().setDocumentMargin(0)
        self.left_page.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.left_page.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.left_page.setFocusPolicy(Qt.NoFocus)
        self.left_page.anchorClicked.connect(
            self.handle_article_link
        )

        left_page_layout.addWidget(self.left_page, 1)

        # RIGHT NEWSPAPER PAGE:
        # no headline space, so article text starts at the very top.
        self.right_page = QTextBrowser()
        self.right_page.setObjectName("NewspaperPage")
        self.right_page.setReadOnly(True)
        self.right_page.setOpenLinks(False)
        self.right_page.setOpenExternalLinks(False)
        self.right_page.setTextInteractionFlags(
            Qt.LinksAccessibleByMouse
        )
        self.right_page.setFrameShape(QFrame.NoFrame)
        self.right_page.document().setDocumentMargin(0)
        self.right_page.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.right_page.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.right_page.setFocusPolicy(Qt.NoFocus)
        self.right_page.anchorClicked.connect(
            self.handle_article_link
        )

        self.fold = QWidget()
        self.fold.setObjectName("NewspaperFold")
        self.fold.setFixedWidth(14)

        spread.addWidget(left_page_container, 1)
        spread.addWidget(self.fold)
        spread.addWidget(self.right_page, 1)

        spread_surface_layout.addLayout(spread, 1)

        root.addWidget(self.spread_surface, 1)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)

        self.close_button = QPushButton("CLOSE")
        self.close_button.setObjectName("ArticleCloseButton")
        self.close_button.clicked.connect(self.close)

        button_width = 172
        button_height = 42
        button_gap = 18
        holder_side_padding = 8

        self.back_to_top_button = QPushButton("BACK TO TOP")
        self.back_to_top_button.setObjectName("PageTurnButton")
        self.back_to_top_button.setFixedSize(
            button_width,
            button_height,
        )
        self.back_to_top_button.setCursor(
            Qt.PointingHandCursor
        )

        back_to_top_font = QFont("Georgia", 16)
        back_to_top_font.setBold(True)
        self.back_to_top_button.setFont(back_to_top_font)
        self.back_to_top_button.clicked.connect(
            self.return_to_first_spread
        )

        self.prev_button = BackPageButton()
        self.prev_button.setObjectName("PageTurnButton")
        self.prev_button.setFixedSize(button_width, button_height)
        self.prev_button.setCursor(Qt.PointingHandCursor)
        self.prev_button.clicked.connect(self.previous_spread)

        self.next_button = QPushButton("TURN PAGE  ›")
        self.next_button.setObjectName("PageTurnButton")
        self.next_button.setFixedSize(button_width, button_height)
        self.next_button.setCursor(Qt.PointingHandCursor)

        next_font = QFont("Georgia", 16)
        next_font.setBold(True)
        self.next_button.setFont(next_font)
        self.next_button.clicked.connect(self.next_spread)

        navigation_width = (
            (button_width * 2)
            + button_gap
            + (holder_side_padding * 2)
        )
        navigation_offset = 80

        left_balance = QWidget()
        left_balance.setFixedSize(
            navigation_width + navigation_offset,
            button_height,
        )

        left_balance_layout = QHBoxLayout(left_balance)
        left_balance_layout.setContentsMargins(
            holder_side_padding,
            0,
            0,
            0,
        )
        left_balance_layout.setSpacing(0)
        left_balance_layout.addWidget(
            self.back_to_top_button
        )
        left_balance_layout.addStretch(1)

        navigation_holder = QWidget()
        navigation_holder.setFixedSize(navigation_width, button_height)

        self.previous_button_slot = QWidget()
        self.previous_button_slot.setFixedSize(button_width, button_height)

        previous_slot_layout = QHBoxLayout(self.previous_button_slot)
        previous_slot_layout.setContentsMargins(0, 0, 0, 0)
        previous_slot_layout.setSpacing(0)
        previous_slot_layout.addWidget(self.prev_button)

        navigation_layout = QHBoxLayout(navigation_holder)
        navigation_layout.setContentsMargins(
            holder_side_padding,
            0,
            holder_side_padding,
            0,
        )
        navigation_layout.setSpacing(button_gap)
        navigation_layout.addWidget(self.previous_button_slot)
        navigation_layout.addWidget(self.next_button)

        controls.addWidget(left_balance)
        controls.addStretch(1)
        controls.addWidget(self.close_button)
        controls.addStretch(1)
        controls.addWidget(navigation_holder)
        controls.addSpacing(navigation_offset)

        root.addLayout(controls)

        self.set_loading_state()
        self.start_fetch()

    def set_loading_state(self):
        self.left_page.setPlainText("Fetching article text...")
        self.right_page.clear()
        self.back_to_top_button.hide()
        self.prev_button.hide()
        self.next_button.show()
        self.next_button.setText("TURN PAGE  ›")
        self.next_button.setEnabled(False)

    def start_fetch(self):
        self.worker = ArticleTextWorker(self.article_url)
        self.worker.finished_payload.connect(self.set_article_payload)
        self.worker.failed.connect(self.set_error)
        self.worker.start()

    def set_error(self, message):
        self.pages = self.paginate_text(
            f"Could not load article text.\n\n{message}"
        )
        self.spread_index = 0
        self.render_spread()

        worker = self.worker
        self.worker = None

        if worker:
            worker.deleteLater()

    def set_article_payload(self, payload):
        worker = self.worker
        self.worker = None

        if worker:
            worker.deleteLater()

        payload = payload or {}
        is_live = bool(payload.get("is_live"))
        updates = list(payload.get("updates") or [])
        text = str(payload.get("text", "") or "")
        self.article_image_resources = {}
        blocks = self.normalize_article_blocks(
            payload.get("blocks", []) or []
        )

        if is_live and updates:
            blocks = []

            for index, update in enumerate(updates, 1):
                blocks.append({
                    "type": "heading",
                    "text": f"LIVE UPDATE {index}",
                })
                blocks.append({
                    "type": "paragraph",
                    "text": str(update or ""),
                })

        if not blocks:
            blocks = self.plain_text_to_blocks(text)

        if not blocks:
            blocks = [{
                "type": "paragraph",
                "text": "No article text was found for this page.",
            }]

        # Put the article headline inside Page 1 rather than above the
        # browser. Every newspaper page therefore retains full height.
        headline = " ".join(
            str(self.headline or "").split()
        )

        if headline:
            blocks.insert(0, {
                "type": "article_headline",
                "text": headline,
            })

        self.pages = self.paginate_article_blocks(blocks)
        self.spread_index = 0
        self.render_spread()

    def normalize_article_blocks(self, blocks):
        allowed_types = {
            "article_headline",
            "heading",
            "paragraph",
            "list_item",
            "quote",
            "image",
        }
        normalized = []

        for raw_block in blocks:
            if not isinstance(raw_block, dict):
                continue

            block_type = str(
                raw_block.get("type", "paragraph") or "paragraph"
            ).strip().lower()
            block_text = " ".join(
                str(raw_block.get("text", "") or "").split()
            )

            if block_type not in allowed_types:
                continue

            if block_type == "image":
                image_resource = str(
                    raw_block.get("image_resource", "") or ""
                ).strip()
                image = None

                if image_resource:
                    image = self.article_image_resources.get(
                        image_resource
                    )

                if image is None:
                    encoded = str(
                        raw_block.get("image_data", "") or ""
                    ).strip()

                    if not encoded:
                        continue

                    try:
                        image_bytes = base64.b64decode(
                            encoded,
                            validate=True,
                        )
                    except Exception:
                        continue

                    image = QImage.fromData(image_bytes)

                    if image.isNull():
                        continue

                    image_resource = (
                        "article-image:"
                        f"{len(self.article_image_resources)}"
                    )
                    self.article_image_resources[
                        image_resource
                    ] = image

                normalized.append({
                    "type": "image",
                    "text": block_text,
                    "image_resource": image_resource,
                    "image_width": int(image.width()),
                    "image_height": int(image.height()),
                })
                continue

            if not block_text:
                continue

            normalized_block = {
                "type": block_type,
                "text": block_text,
            }
            block_html = str(
                raw_block.get("html", "") or ""
            ).strip()

            if block_html:
                normalized_block["html"] = block_html

            if bool(raw_block.get("continuation")):
                normalized_block["continuation"] = True

            raw_anchors = raw_block.get("anchors", []) or []

            if isinstance(raw_anchors, str):
                raw_anchors = [raw_anchors]

            anchors = []

            for raw_anchor in raw_anchors:
                anchor = self.normalize_article_anchor(raw_anchor)

                if anchor and anchor not in anchors:
                    anchors.append(anchor)

            if anchors:
                normalized_block["anchors"] = anchors

            normalized.append(normalized_block)

        return normalized

    def normalize_article_anchor(self, value):
        anchor = unquote(
            str(value or "").strip()
        ).lstrip("#").strip().lower()

        return anchor

    def handle_article_link(self, link):
        if isinstance(link, QUrl):
            link_text = link.toString(QUrl.FullyEncoded)
        else:
            link_text = str(link or "").strip()

        prefix = "article-anchor:"

        if not link_text.lower().startswith(prefix):
            return

        encoded_anchor = link_text[len(prefix):]
        anchor = self.normalize_article_anchor(
            unquote(encoded_anchor)
        )
        page_index = self.article_anchor_pages.get(anchor)

        if page_index is None:
            print(
                "Article anchor target was not found: "
                f"{anchor}"
            )
            return

        print(
            f"ARTICLE INTERNAL LINK: {anchor} -> "
            f"page {page_index + 1}"
        )

        self.spread_index = page_index // 2
        self.render_spread()

    def plain_text_to_blocks(self, text):
        text = str(text or "").strip()

        if not text:
            return []

        raw_paragraphs = [
            part.strip()
            for part in re.split(r"\n\s*\n", text)
            if part.strip()
        ]

        if len(raw_paragraphs) <= 1:
            sentences = [
                sentence.strip()
                for sentence in re.split(r"(?<=[.!?])\s+", text)
                if sentence.strip()
            ]

            raw_paragraphs = []
            paragraph = ""

            for sentence in sentences:
                candidate = f"{paragraph} {sentence}".strip()

                if len(candidate) > 520 and paragraph:
                    raw_paragraphs.append(paragraph)
                    paragraph = sentence
                else:
                    paragraph = candidate

            if paragraph:
                raw_paragraphs.append(paragraph)

        blocks = []

        for paragraph in raw_paragraphs:
            block_type = "paragraph"

            if re.match(
                r"^(?:LIVE UPDATE\s+\d+|\d+\.\s+\S)",
                paragraph,
                flags=re.IGNORECASE,
            ) and len(paragraph) <= 240:
                block_type = "heading"

            blocks.append({
                "type": block_type,
                "text": paragraph,
            })

        return blocks

    def article_block_html(self, block):
        block_type = str(
            block.get("type", "paragraph") or "paragraph"
        ).strip().lower()
        block_text = str(block.get("text", "") or "").strip()
        safe_text = html_module.escape(block_text).replace("\n", "<br>")
        inline_html = str(block.get("html", "") or "").strip()
        rendered_text = inline_html or safe_text

        if block_type == "article_headline":
            return (
                '<div style="'
                'font-family: Georgia; '
                'font-size: 22px; '
                'font-weight: 700; '
                'line-height: 122%; '
                'margin-top: 0px; '
                'margin-bottom: 8px;'
                '">'
                f"{safe_text}"
                "</div>"
                '<div style="'
                'font-size: 1px; '
                'line-height: 1px; '
                'background-color: #5a4e3f; '
                'margin-bottom: 10px;'
                '">&nbsp;</div>'
            )

        if block_type == "image":
            image_resource = html_module.escape(
                str(block.get("image_resource", "") or ""),
                quote=True,
            )
            display_width = max(
                1,
                int(block.get("display_width", 1) or 1),
            )
            display_height = max(
                1,
                int(block.get("display_height", 1) or 1),
            )
            caption_html = (
                '<div style="'
                'font-family: Georgia; '
                'font-size: 14px; '
                'font-style: italic; '
                'line-height: 132%; '
                'margin-top: 10px; '
                'text-align: left;'
                '">'
                f"{safe_text}"
                "</div>"
                if safe_text
                else ""
            )

            return (
                '<div style="'
                'text-align: center; '
                'margin: 0px;'
                '">'
                f'<img src="{image_resource}" '
                f'width="{display_width}" '
                f'height="{display_height}">'
                f"{caption_html}"
                "</div>"
                '<div style="'
                'font-size: 1px; '
                'line-height: 14px; '
                'margin: 0px; '
                'padding: 0px;'
                '">&nbsp;</div>'
            )

        if block_type == "heading":
            return (
                '<div style="'
                'font-family: Georgia; '
                'font-size: 22px; '
                'font-weight: 700; '
                'line-height: 122%; '
                'margin-top: 14px; '
                'margin-bottom: 9px;'
                '">'
                f"{rendered_text}"
                "</div>"
            )

        if block_type == "list_item":
            list_prefix = (
                ""
                if bool(block.get("continuation"))
                else "&#8226;&nbsp;&nbsp;"
            )

            return (
                '<div style="'
                "font-family: 'American Typewriter', "
                "'Courier New', monospace; "
                'font-size: 21px; '
                'line-height: 145%; '
                'margin-left: 12px; '
                'margin-bottom: 12px;'
                '">'
                f"{list_prefix}{rendered_text}"
                "</div>"
            )

        if block_type == "quote":
            return (
                '<div style="'
                "font-family: 'American Typewriter', "
                "'Courier New', monospace; "
                'font-size: 21px; '
                'font-style: italic; '
                'line-height: 145%; '
                'margin-left: 14px; '
                'margin-right: 8px; '
                'margin-bottom: 14px;'
                '">'
                f"{rendered_text}"
                "</div>"
            )

        return (
            '<div style="'
            "font-family: 'American Typewriter', "
            "'Courier New', monospace; "
            'font-size: 21px; '
            'line-height: 145%; '
            'margin-bottom: 14px;'
            '">'
            f"{rendered_text}"
            "</div>"
        )

    def article_page_html(self, blocks):
        return (
            '<div style="color: #1b130c;">'
            + "".join(
                self.article_block_html(block)
                for block in blocks
            )
            + "</div>"
        )

    def paginate_text(self, text, chars_per_page=1100):
        del chars_per_page
        return self.paginate_article_blocks(
            self.plain_text_to_blocks(text)
        )

    def paginate_article_blocks(self, blocks):
        """
        Newspaper-style structured pagination:
        - no scrolling
        - preserves headings, paragraphs, lists, and quotations
        - fills remaining page space with part of a long paragraph
        - measures the same rich text that QLabel renders
        """
        blocks = self.normalize_article_blocks(blocks)
        self.article_anchor_pages = {}

        if not blocks:
            return [self.article_page_html([])]

        # QTextBrowser.viewport() is the actual drawable text area.
        # Its dimensions already exclude the 8px vertical and 18px
        # horizontal padding applied by the NewspaperPage stylesheet.
        page_viewport_width = max(
            self.left_page.viewport().width(),
            self.right_page.viewport().width(),
        )
        page_viewport_height = max(
            self.left_page.viewport().height(),
            self.right_page.viewport().height(),
        )

        # Retain only a tiny allowance for fractional QTextDocument
        # layout rounding. The previous 46px/42px deductions removed
        # usable space a second time and ended pages one or two lines early.
        page_width = max(
            320,
            int(page_viewport_width) - 2,
        )
        page_height = max(
            320,
            int(page_viewport_height) - 2,
        )

        # Images and ordinary text now use the same real page height.
        # prepare_image_block() already reserves caption and spacing height.
        image_page_height = page_height

        def rendered_height(candidate_blocks):
            document = QTextDocument()
            document.setDocumentMargin(0)
            document.setHtml(
                self.article_page_html(candidate_blocks)
            )
            document.setTextWidth(page_width)

            return document.size().height()

        def fits(candidate_blocks):
            return (
                rendered_height(candidate_blocks)
                <= page_height
            )

        def prepare_image_block(block):
            prepared = dict(block)
            original_width = max(
                1,
                int(block.get("image_width", 1) or 1),
            )
            original_height = max(
                1,
                int(block.get("image_height", 1) or 1),
            )
            caption = str(block.get("text", "") or "").strip()

            caption_document = QTextDocument()
            caption_document.setDocumentMargin(0)
            caption_document.setHtml(
                '<div style="'
                'font-family: Georgia; '
                'font-size: 14px; '
                'font-style: italic; '
                'line-height: 132%;'
                '">'
                + html_module.escape(caption)
                + "</div>"
            )
            caption_document.setTextWidth(page_width)
            caption_height = (
                caption_document.size().height()
                if caption
                else 0
            )

            max_image_width = max(1, page_width)
            max_image_height = max(
                1,
                int(image_page_height - caption_height - 14),
            )
            fit_scale = min(
                1.0,
                max_image_width / original_width,
                max_image_height / original_height,
            )

            # Reduce the previous two-thirds display size by 25%.
            # The image now uses one-half of the proportional size
            # that would otherwise fit the dedicated page.
            display_scale = fit_scale * 0.5

            prepared["display_width"] = max(
                1,
                int(original_width * display_scale),
            )
            prepared["display_height"] = max(
                1,
                int(original_height * display_scale),
            )
            return prepared

        def text_fragment(
            block,
            words,
            continuation=False,
        ):
            fragment = {
                "type": block["type"],
                "text": " ".join(words).strip(),
            }

            if continuation:
                fragment["continuation"] = True
            else:
                anchors = list(
                    block.get("anchors", []) or []
                )

                if anchors:
                    fragment["anchors"] = anchors

            return fragment

        def largest_prefix_that_fits(
            block,
            words,
            existing_blocks,
            continuation,
        ):
            low = 1
            high = len(words)
            best = 0

            while low <= high:
                middle = (low + high) // 2

                fragment = text_fragment(
                    block,
                    words[:middle],
                    continuation=continuation,
                )

                if fits(existing_blocks + [fragment]):
                    best = middle
                    low = middle + 1
                else:
                    high = middle - 1

            return best

        page_blocks = []
        pages = []

        def flush_page():
            nonlocal page_blocks

            if page_blocks:
                page_index = len(pages)

                for page_block in page_blocks:
                    for anchor in (
                        page_block.get("anchors", []) or []
                    ):
                        normalized_anchor = (
                            self.normalize_article_anchor(anchor)
                        )

                        if normalized_anchor:
                            self.article_anchor_pages.setdefault(
                                normalized_anchor,
                                page_index,
                            )

                pages.append(
                    self.article_page_html(page_blocks)
                )
                page_blocks = []

        def add_splittable_block(block):
            nonlocal page_blocks

            remaining_words = str(
                block.get("text", "") or ""
            ).split()

            continuation = bool(
                block.get("continuation")
            )
            first_fragment = True
            has_internal_links = (
                "article-anchor:"
                in str(block.get("html", "") or "")
            )

            # Keep a compact jump menu intact so its individual links
            # remain clickable. Ordinary article paragraphs still split
            # across pages to fill available space.
            if has_internal_links:
                if not fits(page_blocks + [block]) and page_blocks:
                    flush_page()

                if fits(page_blocks + [block]):
                    page_blocks.append(block)
                    return

            while remaining_words:
                entire_fragment = text_fragment(
                    block,
                    remaining_words,
                    continuation=continuation,
                )

                # Keep the original inline formatting when the entire,
                # unsplit block fits on the current page.
                if (
                    first_fragment
                    and not continuation
                    and fits(page_blocks + [block])
                ):
                    page_blocks.append(block)
                    return

                if fits(page_blocks + [entire_fragment]):
                    page_blocks.append(entire_fragment)
                    return

                prefix_count = largest_prefix_that_fits(
                    block,
                    remaining_words,
                    page_blocks,
                    continuation=continuation,
                )

                if prefix_count <= 0:
                    if page_blocks:
                        flush_page()
                        continue

                    # Prevent an infinite loop if one unusually long
                    # word cannot fit by itself.
                    prefix_count = 1

                fragment = text_fragment(
                    block,
                    remaining_words[:prefix_count],
                    continuation=continuation,
                )

                page_blocks.append(fragment)
                remaining_words = remaining_words[
                    prefix_count:
                ]

                if remaining_words:
                    flush_page()
                    continuation = True
                    first_fragment = False

        for index, block in enumerate(blocks):
            if block["type"] == "image":
                prepared_image = prepare_image_block(block)

                # Keep the complete image-and-caption block on the
                # current page whenever it fits in the remaining space.
                # Move it to a new page only when necessary.
                if not fits(
                    page_blocks + [prepared_image]
                ):
                    flush_page()

                page_blocks.append(prepared_image)

                # Following text may continue below the image and caption.
                # The image block's 14px bottom margin matches the spacing
                # used after a normal paragraph.
                continue

            # Keep the article headline or a subsection heading with
            # at least the beginning of its following paragraph whenever
            # possible.
            if (
                block["type"] in {
                    "article_headline",
                    "heading",
                }
                and page_blocks
                and index + 1 < len(blocks)
            ):
                next_block = blocks[index + 1]
                preview_words = (
                    next_block["text"].split()[:18]
                )
                preview_block = {
                    "type": next_block["type"],
                    "text": " ".join(preview_words),
                }

                if (
                    fits(page_blocks + [block])
                    and not fits(
                        page_blocks
                        + [block, preview_block]
                    )
                ):
                    flush_page()

            if block["type"] in {
                "article_headline",
                "heading",
            }:
                if not fits(page_blocks + [block]):
                    flush_page()

                page_blocks.append(block)
                continue

            add_splittable_block(block)

        flush_page()

        return pages or [
            self.article_page_html(blocks)
        ]

    def render_spread(self):
        left_index = self.spread_index * 2
        right_index = left_index + 1

        left_text = self.pages[left_index] if left_index < len(self.pages) else ""
        right_text = self.pages[right_index] if right_index < len(self.pages) else ""

        for browser, page_html in (
            (self.left_page, left_text),
            (self.right_page, right_text),
        ):
            document = browser.document()

            for resource_name, image in (
                self.article_image_resources.items()
            ):
                document.addResource(
                    QTextDocument.ImageResource,
                    QUrl(resource_name),
                    image,
                )

            browser.setHtml(page_html)

            # Keep the displayed document geometry identical to the
            # zero-margin document used while calculating page breaks.
            document = browser.document()
            document.setDocumentMargin(0)

            # Re-register after setHtml as well so Qt can resolve the
            # custom image resource regardless of document reset order.
            for resource_name, image in (
                self.article_image_resources.items()
            ):
                document.addResource(
                    QTextDocument.ImageResource,
                    QUrl(resource_name),
                    image,
                )

        self.left_page.verticalScrollBar().setValue(0)
        self.right_page.verticalScrollBar().setValue(0)

        # Page 1's headline is already part of the paginated HTML,
        # so neither browser changes height between newspaper spreads.

        total_pages = len(self.pages)
        total_spreads = max(1, (total_pages + 1) // 2)

        left_page_num = left_index + 1
        right_page_num = min(right_index + 1, total_pages)

        self.page_counter.setText(f"Pages {left_page_num}-{right_page_num} of {total_pages}")

        has_previous = self.spread_index > 0
        has_next = right_index + 1 < total_pages

        # Keep both fixed slots in place, but hide the entire back button
        # until the user has moved beyond the first spread.
        self.back_to_top_button.setVisible(has_previous)
        self.back_to_top_button.setEnabled(has_previous)
        self.prev_button.setVisible(has_previous)
        self.prev_button.setEnabled(has_previous)

        # Articles that fit in the first two pages never show TURN PAGE.
        # Longer articles keep it visible through the final spread, where it
        # becomes greyed out because there is nowhere further to go.
        article_has_more_than_two_pages = total_pages > 2
        self.next_button.setVisible(article_has_more_than_two_pages)
        self.next_button.setEnabled(has_next)

        if has_previous:
            self.prev_button.setText("")

        self.next_button.setText("TURN PAGE  ›")


    def next_spread(self):
        total_spreads = max(1, (len(self.pages) + 1) // 2)

        if self.spread_index < total_spreads - 1:
            self.spread_index += 1
            self.render_spread()

    def previous_spread(self):
        if self.spread_index > 0:
            self.spread_index -= 1
            self.render_spread()

    def return_to_first_spread(self):
        if self.spread_index > 0:
            self.spread_index = 0
            self.render_spread()

    def closeEvent(self, event):
        if self.worker:
            self.worker.quit()
            self.worker.wait()
            self.worker = None

        super().closeEvent(event)



class NewsCard(QWidget):
    reminders_requested = Signal()
    market_tape_requested = Signal()

    @staticmethod
    def plain_source_name(source):
        source = (source or "").strip()
        normalized = source.upper()

        if normalized == "FOX NEWS":
            return "FOX News"
        if normalized == "CNN":
            return "CNN"
        if normalized == "CNBC":
            return "CNBC"

        return source.title() if source else ""

    def __init__(self, headline, source, image_label="", variant="FOX"):
        super().__init__()

        self.variant = variant
        self.source = source
        self.header_display_source = source
        self.image_label = image_label
        self.article_url = ""
        self.article_dialog = None
        self.page2_widgets = []
        self.page2_widget_urls = {}
        self.page2_widget_headlines = {}
        self.reminders_action_enabled = False
        self.reminders_action_visible = True
        self.reminders_empty_state_message = ""
        self.market_tape_action_enabled = False

        self.image_request_token = 0
        self.image_workers = set()

        self.setObjectName("NewspaperNewsCard")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet("""
            QWidget#NewspaperNewsCard {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fff5df,
                    stop:0.52 #f0e3c8,
                    stop:1 #d8c39b
                );
                border: 1px solid rgba(48, 36, 22, 210);
                border-radius: 2px;
            }

            QWidget#NewspaperNewsCard QLabel {
                background: transparent;
            }

            QWidget#NewsPaperPhotoBox {
                background-color: #d6c3a0;
                border: none;
                border-radius: 0px;
            }

            QWidget#NewsPaperStoryPanel {
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }

            QLabel#OldNewsTopMasthead {
                font-family: "Rockwell", "Rockwell Extra Bold", "Rockwell Condensed", "Georgia", serif;
                font-size: 20px;
                font-weight: 900;
                color: #241a10;
                letter-spacing: 0.8px;
                background: transparent;
            }

            QLabel#OldNewsEditionSmall {
                font-family: "Times New Roman";
                font-size: 8px;
                font-weight: 1000;
                color: #5a442b;
                letter-spacing: 1.1px;
            }

            QLabel#OldNewsKicker {
                font-family: "Times New Roman";
                font-size: 8px;
                font-weight: 1000;
                color: #9c6424;
                letter-spacing: 1.4px;
            }

            QLabel#OldNewsHeadline {
                font-family: "Georgia";
                font-size: 30px;
                font-weight: 1000;
                color: #15100b;
                letter-spacing: -0.4px;
            }

            QLabel#OldNewsReadLink,
            QLabel#OldNewsPageNumber {
                font-family: "Times New Roman";
                font-size: 7px;
                font-weight: 1000;
                color: #4c3721;
                letter-spacing: 0.5px;
            }
        """)

        self.outer_layout = QVBoxLayout()
        outer = self.outer_layout
        outer.setContentsMargins(14, 6, 13, 10)
        outer.setSpacing(0)
        self.setLayout(outer)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(5)

        self.top_source_label = QLabel(source)
        self.top_source_label.setObjectName("OldNewsTopMasthead")
        self.top_source_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.top_source_label.setStyleSheet("""
            QLabel#OldNewsTopMasthead {
                font-family: "Rockwell", "Rockwell Extra Bold", "Rockwell Condensed", "Georgia", serif;
                font-size: 20px;
                font-weight: 900;
                color: #241a10;
                letter-spacing: 0.8px;
                background: transparent;
            }
        """)
        self.top_source_label.setFixedHeight(24)

        self.edition_label = QLabel("Politics")
        self.edition_label.setObjectName("OldNewsEditionSmall")
        self.edition_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.edition_label.setFixedHeight(19)

        self.reminders_button = QPushButton("Reminders")
        self.reminders_button.setObjectName("MiniNewsRemindersButton")
        self.reminders_button.setCursor(Qt.PointingHandCursor)
        self.reminders_button.setFixedHeight(19)
        self.reminders_button.hide()
        self.reminders_button.clicked.connect(self.reminders_requested.emit)
        self.reminders_button.setStyleSheet("""
            QPushButton#MiniNewsRemindersButton {
                color: #5e3f1c;
                background: rgba(255, 248, 236, 0.52);
                border: 1px solid rgba(83, 59, 33, 0.38);
                border-radius: 5px;
                padding: 1px 7px;
                font-family: "Times New Roman";
                font-size: 9px;
                font-weight: 900;
            }

            QPushButton#MiniNewsRemindersButton:hover {
                background: rgba(255, 248, 236, 0.88);
                border-color: rgba(83, 59, 33, 0.68);
            }
        """)

        self.market_tape_button = QPushButton("Market Tape")
        self.market_tape_button.setObjectName("MiniNewsMarketTapeButton")
        self.market_tape_button.setCursor(Qt.PointingHandCursor)
        self.market_tape_button.setFixedHeight(19)
        self.market_tape_button.hide()
        self.market_tape_button.clicked.connect(self.market_tape_requested.emit)
        self.market_tape_button.setStyleSheet("""
            QPushButton#MiniNewsMarketTapeButton {
                color: #5e3f1c;
                background: rgba(255, 248, 236, 0.52);
                border: 1px solid rgba(83, 59, 33, 0.38);
                border-radius: 5px;
                padding: 1px 7px;
                font-family: "Times New Roman";
                font-size: 9px;
                font-weight: 900;
            }

            QPushButton#MiniNewsMarketTapeButton:hover {
                background: rgba(255, 248, 236, 0.88);
                border-color: rgba(83, 59, 33, 0.68);
            }
        """)

        top_row.addWidget(self.top_source_label, 1)
        top_row.addWidget(self.edition_label)
        top_row.addWidget(self.reminders_button)
        top_row.addWidget(self.market_tape_button)

        outer.addLayout(top_row)
        outer.addWidget(PaperRule())

        self.image = NewspaperImagePanel(
            label_text=image_label,
            source_text=source,
            variant=variant,
        )

        self.text_panel = QWidget()
        self.text_panel.setObjectName("NewsPaperStoryPanel")
        self.text_panel.setAttribute(Qt.WA_StyledBackground, True)
        self.text_panel.setCursor(Qt.PointingHandCursor)

        self.text_layout = QVBoxLayout()
        text_layout = self.text_layout
        text_layout.setContentsMargins(2, 0, 2, 0)
        text_layout.setSpacing(1)
        self.text_panel.setLayout(text_layout)

        self.kicker_label = QLabel("TOP STORY" if variant == "FOX" else "MARKETS & BUSINESS")
        self.kicker_label.setObjectName("OldNewsKicker")
        self.kicker_label.setAlignment(Qt.AlignLeft)

        self.headline_label = AutoFitLabel(
            headline,
            min_size=12,
            max_size=34,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignTop,
            word_wrap=True,
        )
        self.headline_label.setObjectName("OldNewsHeadline")
        self.headline_label.setCursor(Qt.PointingHandCursor)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 1, 0, 4)
        bottom_row.setSpacing(8)

        self.read_label = QLabel("")
        self.read_label.setObjectName("OldNewsReadLink")
        self.read_label.setAlignment(Qt.AlignLeft)

        self.page_label = QLabel("PAGE 1")
        self.page_label.setObjectName("OldNewsPageNumber")
        self.page_label.setAlignment(Qt.AlignRight)

        bottom_row.addWidget(self.read_label, 1)
        bottom_row.addWidget(self.page_label)

        text_layout.addWidget(self.kicker_label)
        text_layout.addWidget(PaperRule())
        text_layout.addWidget(self.headline_label, 1)

        # Newspaper layout: headline above image, footer below image.
        outer.addWidget(self.text_panel, 16)
        outer.addWidget(self.image, 72)

        # Paper gap between the bottom of the article image and the newspaper footer.
        outer.addSpacing(5)

        # Small bottom border/rule for the news article section.
        outer.addWidget(PaperRule())

        outer.addLayout(bottom_row, 4)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect().adjusted(1, 1, -1, -1)
        draw_stacked_newspaper_panel(painter, rect, seed=32 if self.variant == "FOX" else 33)

        # Draw the news-site masthead the same way Sports Desk / Game Times do:
        # fixed newspaper coordinates, not QLabel layout guessing.
        inner = rect.adjusted(17, 9, -17, -13)

        masthead_font = QFont("Rockwell", 20)
        masthead_font.setBold(True)
        masthead_font.setLetterSpacing(QFont.PercentageSpacing, 106)

        painter.setFont(masthead_font)
        painter.setPen(QColor("#241a10"))

        painter.drawText(
            QRectF(inner.left(), inner.top() - 1, inner.width() * 0.72, 24),
            Qt.AlignLeft | Qt.AlignVCenter,
            getattr(self, "header_display_source", self.source),
        )

    def set_reminders_action_enabled(self, enabled):
        self.reminders_action_enabled = bool(enabled)

        if not self.reminders_action_enabled:
            self.reminders_button.hide()
            self.edition_label.show()

    def set_reminders_action_visible(self, visible):
        self.reminders_action_visible = bool(visible)

        if self.reminders_action_enabled:
            self.reminders_button.setVisible(
                self.reminders_action_visible
            )

    def set_reminders_empty_state_message(self, message):
        self.reminders_empty_state_message = str(message or "").strip()

        if not self.reminders_action_enabled:
            return

        if self.reminders_empty_state_message:
            self.reminders_button.hide()
            self.edition_label.setText(
                self.reminders_empty_state_message
            )
            self.edition_label.setStyleSheet("""
                QLabel {
                    color: rgba(45, 33, 20, 0.92);
                    background: transparent;
                    font-family: "Times New Roman";
                    font-size: 14px;
                    font-weight: 1000;
                    font-style: italic;
                }
            """)
            self.edition_label.show()
        else:
            self.edition_label.setText("Politics")
            self.edition_label.setStyleSheet("")
            self.edition_label.setVisible(
                not self.reminders_action_visible
            )

    def set_market_tape_action_enabled(self, enabled):
        self.market_tape_action_enabled = bool(enabled)

        if not self.market_tape_action_enabled:
            self.market_tape_button.hide()
            self.edition_label.show()

    def clear_page2_widgets(self):
        self.reminders_button.hide()
        self.market_tape_button.hide()
        self.edition_label.show()

        for widget in getattr(self, "page2_widgets", []):
            self.text_layout.removeWidget(widget)
            widget.deleteLater()

        self.page2_widgets = []
        self.page2_widget_urls = {}
        self.page2_widget_headlines = {}

        self.image.show()
        self.headline_label.show()


    def start_background_image_load(self, source, article_url, image_url=""):
        article_url = str(article_url or "").strip()

        if not article_url:
            return

        self.image_request_token += 1
        token = self.image_request_token

        worker = ArticleImageWorker(
            request_token=token,
            source=source,
            article_url=article_url,
            image_url=image_url,
        )

        self.image_workers.add(worker)

        worker.image_ready.connect(self.apply_background_image)
        worker.failed.connect(self.background_image_failed)

        def cleanup():
            self.image_workers.discard(worker)
            worker.deleteLater()

        worker.finished.connect(cleanup)
        worker.start()

    def apply_background_image(self, token, image_url, image_bytes):
        if token != self.image_request_token:
            return

        if not image_bytes:
            return

        self.image.set_pixmap_from_data(image_bytes)

        print(
            f"BACKGROUND IMAGE READY: "
            f"{self.source} | {len(image_bytes)} bytes | {image_url}"
        )

    def background_image_failed(self, token, message):
        if token != self.image_request_token:
            return

        print(f"BACKGROUND IMAGE FAILED: {self.source} -> {message}")

    def update_article(self, article):
        self.clear_page2_widgets()
        self.outer_layout.setStretchFactor(self.text_panel, 16)
        self.outer_layout.setStretchFactor(self.image, 72)
        self.outer_layout.setStretch(2, 16)
        self.outer_layout.setStretch(3, 72)
        self.outer_layout.setStretch(6, 4)
        self.text_layout.setStretchFactor(self.headline_label, 1)
        self.source = article.source
        self.article_url = getattr(article, "link", "") or ""

        source_name = (getattr(article, "source", "") or self.source or "").strip()
        visible_section = self.plain_source_name(source_name) or ("FOX News" if self.variant == "FOX" else "CNN")

        self.header_display_source = visible_section
        self.top_source_label.setText("")
        self.image.set_source_text(visible_section)
        self.image.set_breaking_headline(
            getattr(article, "breaking_headline", "") or ""
        )
        self.headline_label.setText(article.title)
        self.update()

        if article.source == "FOX NEWS":
            self.image.set_label_text("LIVE UPDATES")
            self.edition_label.setText("POLITICS")
            self.kicker_label.setText("TOP STORY")
            self.page_label.setText("PAGE 1")
        elif article.source == "CNBC":
            self.image.set_label_text("BUSINESS")
            self.edition_label.setText("BUSINESS")
            self.kicker_label.setText("TOP STORY")
            self.page_label.setText("PAGE 1")
        else:
            self.image.set_label_text("LATEST")
            self.edition_label.setText("POLITICS")
            self.kicker_label.setText("LATEST")
            self.page_label.setText("PAGE 1")

        if self.article_url:
            self.read_label.setText("")
            self.setCursor(Qt.PointingHandCursor)
            self.text_panel.setCursor(Qt.PointingHandCursor)
            self.headline_label.setCursor(Qt.PointingHandCursor)
        else:
            self.read_label.setText("")
            self.setCursor(Qt.ArrowCursor)
            self.text_panel.setCursor(Qt.ArrowCursor)
            self.headline_label.setCursor(Qt.ArrowCursor)

        image_bytes = getattr(article, "image_bytes", b"") or b""
        image_url = getattr(article, "image_url", "") or ""

        if image_bytes:
            self.image.set_pixmap_from_data(image_bytes)
        else:
            self.image.set_pixmap_from_data(b"")
            self.start_background_image_load(
                source=article.source,
                article_url=self.article_url,
                image_url=image_url,
            )

    def update_article_list(self, articles, page_label="PAGE 2"):
        self.clear_page2_widgets()

        articles = list(articles or [])[:5]

        self.image.set_pixmap_from_data(b"")
        self.image.set_breaking_headline("")
        self.image.hide()
        self.headline_label.hide()

        self.outer_layout.setStretchFactor(self.image, 0)
        self.outer_layout.setStretchFactor(self.text_panel, 1)

        # Layout index 6 is the footer row. In Page 2 mode it must not
        # receive stretch; all available height belongs to the five stories.
        self.outer_layout.setStretch(2, 100)
        self.outer_layout.setStretch(3, 0)
        self.outer_layout.setStretch(6, 0)
        self.text_panel.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        # The hidden main-headline layout item was still retaining stretch
        # space. Give that space entirely to the five-story mini-news list.
        self.text_layout.setStretchFactor(self.headline_label, 0)

        if articles:
            self.source = articles[0].source
            source_name = (getattr(articles[0], "source", "") or self.source or "").strip()
            visible_section = self.plain_source_name(source_name) or ("FOX News" if self.variant == "FOX" else "CNN")

            self.header_display_source = visible_section
            self.top_source_label.setText("")
            self.image.set_source_text(visible_section)
            self.update()

        self.article_url = ""

        if self.reminders_action_enabled:
            self.market_tape_button.hide()

            if self.reminders_empty_state_message:
                self.reminders_button.hide()
                self.edition_label.setText(
                    self.reminders_empty_state_message
                )
                self.edition_label.show()
            else:
                self.edition_label.hide()
                self.reminders_button.setVisible(
                    self.reminders_action_visible
                )
        elif self.market_tape_action_enabled:
            self.edition_label.hide()
            self.reminders_button.hide()
            self.market_tape_button.show()
        else:
            self.reminders_button.hide()
            self.market_tape_button.hide()
            self.edition_label.show()
            self.edition_label.setText("CONTINUED")

        self.kicker_label.setText("MORE HEADLINES")
        self.page_label.setText(page_label)
        self.read_label.setText("")

        self.setCursor(Qt.ArrowCursor)
        self.text_panel.setCursor(Qt.ArrowCursor)

        # One visible page-2 container with five equal rows.
        page2_container = QWidget()
        page2_container.setObjectName("Page2Container")
        page2_container.setAttribute(Qt.WA_StyledBackground, True)
        page2_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        page2_layout = QVBoxLayout()
        page2_layout.setContentsMargins(0, 0, 0, 0)
        page2_layout.setSpacing(0)
        page2_container.setLayout(page2_layout)

        for index in range(5):
            article = articles[index] if index < len(articles) else None
            title = getattr(article, "title", "") if article else "Additional headline unavailable."
            article_url = getattr(article, "link", "") if article else ""

            row = QWidget()
            row.setObjectName("Page2HeadlineBox")
            row.setAttribute(Qt.WA_StyledBackground, True)
            row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            row.setMinimumHeight(0)
            row.setMaximumHeight(16777215)

            row_layout = QVBoxLayout()
            row_layout.setContentsMargins(10, 2, 10, 2)
            row_layout.setSpacing(0)
            row.setLayout(row_layout)

            title_label = ResponsiveMiniHeadlineLabel(title)
            title_label.setMinimumHeight(0)
            title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            title_label.setObjectName("Page2HeadlineText")

            row_layout.addWidget(title_label, 1)

            row.setStyleSheet("""
                QWidget#Page2HeadlineBox {
                    background: transparent;
                    border: none;
                    border-top: 1px solid rgba(55, 42, 25, 0.42);
                    border-radius: 0px;
                }
                QWidget#Page2HeadlineBox:hover {
                    background: rgba(255, 248, 236, 0.28);
                    border-top: 1px solid rgba(55, 42, 25, 0.62);
                }
                QLabel#Page2HeadlineText {
                    color: #17100a;
                    background: transparent;
                }
            """)

            if article_url:
                row.setCursor(Qt.PointingHandCursor)
                title_label.setCursor(Qt.PointingHandCursor)
                row.installEventFilter(self)
                title_label.installEventFilter(self)

                self.page2_widget_urls[row] = article_url
                self.page2_widget_urls[title_label] = article_url

                self.page2_widget_headlines[row] = title
                self.page2_widget_headlines[title_label] = title

            page2_layout.addWidget(row, 1)

        # Put the five-row container between the paper rule and the footer.
        self.text_layout.insertWidget(2, page2_container, 100)
        self.text_layout.setStretchFactor(page2_container, 100)
        self.page2_widgets.append(page2_container)


    def open_article_popup(self, article_url=None, article_headline=None):
        url = article_url or self.article_url

        if not url:
            return

        headline = (
            str(article_headline or "").strip()
            or (self.headline_label.text() if hasattr(self.headline_label, "text") else "")
        )
        source = self.plain_source_name(self.source) or self.source or "News"

        parent_window = self.window()

        self.article_dialog = OpenNewspaperDialog(
            source=source,
            headline=headline,
            article_url=url,
            parent=parent_window,
        )

        if parent_window:
            parent_rect = parent_window.rect()

            # Keep the existing wide newspaper spread shape while using nearly
            # the entire dashboard window.
            aspect_ratio = 1120 / 650
            max_width = int(parent_rect.width())
            max_height = int(parent_rect.height())

            width = max_width
            height = int(width / aspect_ratio)

            if height > max_height:
                height = max_height
                width = int(height * aspect_ratio)

            x = int((parent_rect.width() - width) / 2)
            y = int((parent_rect.height() - height) / 2)

            self.article_dialog.setGeometry(x, y, width, height)

        self.article_dialog.show()
        self.article_dialog.raise_()
        self.article_dialog.activateWindow()


    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress:
            article_url = getattr(self, "page2_widget_urls", {}).get(watched, "")
            article_headline = getattr(
                self,
                "page2_widget_headlines",
                {},
            ).get(watched, "")

            if article_url:
                self.open_article_popup(article_url, article_headline)
                return True

        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.article_url:
            self.open_article_popup(self.article_url)

        super().mousePressEvent(event)
