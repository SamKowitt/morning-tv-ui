import random
from PySide6.QtCore import Qt, QRectF, QUrl, QSize, QEvent, QPointF
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QFrame

from ui.auto_fit_label import AutoFitLabel
from ui.newspaper_chrome import draw_stacked_newspaper_panel


class PaperRule(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setFixedHeight(1)
        self.setStyleSheet("background-color: rgba(90, 78, 63, 135); border: none;")


class NewspaperImagePanel(QWidget):
    def __init__(self, label_text="", source_text="", variant="fox"):
        super().__init__()

        self.variant = variant
        self.label_text = label_text
        self.source_text = source_text
        self.original_pixmap = None

        self.setObjectName("NewsPaperPhotoBox")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setMinimumHeight(150)

    def set_label_text(self, text):
        self.label_text = text
        self.update()

    def set_source_text(self, text):
        self.source_text = text
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

        # No drawn border here; the newspaper panel already frames the section.


    def draw_fallback_art(self, painter, rect):
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())

        if self.variant == "fox":
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


class NewsCard(QWidget):
    @staticmethod
    def plain_source_name(source):
        source = (source or "").strip()
        normalized = source.upper()

        if normalized == "FOX NEWS":
            return "Fox News"
        if normalized == "CNN":
            return "CNN"
        if normalized == "CNBC":
            return "CNBC"

        return source.title() if source else ""

    def __init__(self, headline, source, image_label="", variant="fox"):
        super().__init__()

        self.variant = variant
        self.source = source
        self.header_display_source = source
        self.image_label = image_label
        self.article_url = ""
        self.page2_widgets = []
        self.page2_widget_urls = {}

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
                font-size: 8px;
                font-weight: 1000;
                color: #4c3721;
                letter-spacing: 1px;
            }
        """)

        self.outer_layout = QVBoxLayout()
        outer = self.outer_layout
        outer.setContentsMargins(14, 6, 13, 6)
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

        top_row.addWidget(self.top_source_label, 1)
        top_row.addWidget(self.edition_label)

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

        self.kicker_label = QLabel("TOP STORY" if variant == "fox" else "MARKETS & BUSINESS")
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
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(8)

        self.read_label = QLabel("READ MORE  ›")
        self.read_label.setObjectName("OldNewsReadLink")
        self.read_label.setAlignment(Qt.AlignLeft)

        self.page_label = QLabel("P. 1")
        self.page_label.setObjectName("OldNewsPageNumber")
        self.page_label.setAlignment(Qt.AlignRight)

        bottom_row.addWidget(self.read_label, 1)
        bottom_row.addWidget(self.page_label)

        text_layout.addWidget(self.kicker_label)
        text_layout.addWidget(PaperRule())
        text_layout.addWidget(self.headline_label, 1)

        # Newspaper layout: headline above image, footer below image.
        outer.addWidget(self.text_panel, 17)
        outer.addWidget(self.image, 81)
        outer.addLayout(bottom_row, 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect().adjusted(1, 1, -1, -1)
        draw_stacked_newspaper_panel(painter, rect, seed=32 if self.variant == "fox" else 33)

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

    def clear_page2_widgets(self):
        for widget in getattr(self, "page2_widgets", []):
            self.text_layout.removeWidget(widget)
            widget.deleteLater()

        self.page2_widgets = []
        self.page2_widget_urls = {}

        self.image.show()
        self.headline_label.show()

    def update_article(self, article):
        self.clear_page2_widgets()
        self.outer_layout.setStretchFactor(self.text_panel, 17)
        self.outer_layout.setStretchFactor(self.image, 81)
        self.source = article.source
        self.article_url = getattr(article, "link", "") or ""

        source_name = (getattr(article, "source", "") or self.source or "").strip()
        visible_section = self.plain_source_name(source_name) or ("Fox News" if self.variant == "fox" else "CNN")

        self.header_display_source = visible_section
        self.top_source_label.setText("")
        self.image.set_source_text(visible_section)
        self.headline_label.setText(article.title)
        self.update()

        if article.source == "FOX NEWS":
            self.image.set_label_text("LIVE UPDATES")
            self.edition_label.setText("POLITICS")
            self.kicker_label.setText("TOP STORY")
            self.page_label.setText("P. 1")
        elif article.source == "CNBC":
            self.image.set_label_text("BUSINESS")
            self.edition_label.setText("BUSINESS")
            self.kicker_label.setText("BUSINESS")
            self.page_label.setText("P. 1")
        else:
            self.image.set_label_text("LATEST")
            self.edition_label.setText("POLITICS")
            self.kicker_label.setText("LATEST")
            self.page_label.setText("P. 1")

        if self.article_url:
            self.read_label.setText("READ MORE  ›")
            self.setCursor(Qt.PointingHandCursor)
            self.text_panel.setCursor(Qt.PointingHandCursor)
            self.headline_label.setCursor(Qt.PointingHandCursor)
        else:
            self.read_label.setText("")
            self.setCursor(Qt.ArrowCursor)
            self.text_panel.setCursor(Qt.ArrowCursor)
            self.headline_label.setCursor(Qt.ArrowCursor)

        if getattr(article, "image_bytes", b""):
            self.image.set_pixmap_from_data(article.image_bytes)
        else:
            self.image.set_pixmap_from_data(b"")

    def update_article_list(self, articles, page_label="PAGE 2"):
        self.clear_page2_widgets()

        articles = list(articles or [])[:4]

        self.image.set_pixmap_from_data(b"")
        self.image.hide()
        self.headline_label.hide()

        self.outer_layout.setStretchFactor(self.image, 0)
        self.outer_layout.setStretchFactor(self.text_panel, 1)

        if articles:
            self.source = articles[0].source
            source_name = (getattr(articles[0], "source", "") or self.source or "").strip()
            visible_section = self.plain_source_name(source_name) or ("Fox News" if self.variant == "fox" else "CNN")

            self.header_display_source = visible_section
            self.top_source_label.setText("")
            self.image.set_source_text(visible_section)
            self.update()

        self.article_url = ""
        self.edition_label.setText("CONTINUED")
        self.kicker_label.setText("MORE HEADLINES")
        self.page_label.setText(page_label)
        self.read_label.setText("")

        self.setCursor(Qt.ArrowCursor)
        self.text_panel.setCursor(Qt.ArrowCursor)

        # One visible page-2 container with four equal rows.
        page2_container = QWidget()
        page2_container.setObjectName("Page2Container")
        page2_container.setAttribute(Qt.WA_StyledBackground, True)
        page2_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        page2_layout = QVBoxLayout()
        page2_layout.setContentsMargins(0, 0, 0, 0)
        page2_layout.setSpacing(6)
        page2_container.setLayout(page2_layout)

        for index in range(4):
            article = articles[index] if index < len(articles) else None
            title = getattr(article, "title", "") if article else "Additional headline unavailable."
            article_url = getattr(article, "link", "") if article else ""

            row = QWidget()
            row.setObjectName("Page2HeadlineBox")
            row.setAttribute(Qt.WA_StyledBackground, True)
            row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            row_layout = QVBoxLayout()
            row_layout.setContentsMargins(10, 5, 10, 5)
            row_layout.setSpacing(2)
            row.setLayout(row_layout)

            story_label = QLabel(f"STORY {index + 1}")
            story_label.setObjectName("Page2HeadlineSection")
            story_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            title_label = AutoFitLabel(
                title,
                min_size=11,
                max_size=18,
                bold=True,
                alignment=Qt.AlignLeft | Qt.AlignVCenter,
                word_wrap=True,
            )
            title_label.setObjectName("Page2HeadlineText")

            row_layout.addWidget(story_label)
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
                QLabel#Page2HeadlineSection {
                    color: rgba(126, 81, 31, 0.90);
                    background: transparent;
                    font-family: "Times New Roman";
                    font-size: 8px;
                    font-weight: 1000;
                    letter-spacing: 1.2px;
                }
                QLabel#Page2HeadlineText {
                    color: #17100a;
                    background: transparent;
                    font-family: "Georgia";
                    font-weight: 1000;
                }
            """)

            if article_url:
                row.setCursor(Qt.PointingHandCursor)
                title_label.setCursor(Qt.PointingHandCursor)
                story_label.setCursor(Qt.PointingHandCursor)

                row.installEventFilter(self)
                title_label.installEventFilter(self)
                story_label.installEventFilter(self)

                self.page2_widget_urls[row] = article_url
                self.page2_widget_urls[title_label] = article_url
                self.page2_widget_urls[story_label] = article_url

            page2_layout.addWidget(row, 1)

        # Put the four-row container between the paper rule and the footer.
        self.text_layout.insertWidget(2, page2_container, 1)
        self.page2_widgets.append(page2_container)


    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress:
            article_url = getattr(self, "page2_widget_urls", {}).get(watched, "")

            if article_url:
                QDesktopServices.openUrl(QUrl(article_url))
                return True

        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.article_url:
            QDesktopServices.openUrl(QUrl(self.article_url))

        super().mousePressEvent(event)