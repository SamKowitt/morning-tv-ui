from PySide6.QtCore import Qt, QRectF, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QHBoxLayout, QFrame

from ui.auto_fit_label import AutoFitLabel


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
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumHeight(120)

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 10, 10)
        painter.setClipPath(path)

        if self.original_pixmap:
            scaled = self.original_pixmap.scaled(
                rect.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )

            x = int((rect.width() - scaled.width()) / 2)
            y = int((rect.height() - scaled.height()) / 2)
            painter.drawPixmap(x, y, scaled)

            overlay = QLinearGradient(0, 0, 0, rect.height())
            overlay.setColorAt(0.0, QColor(0, 0, 0, 8))
            overlay.setColorAt(0.65, QColor(0, 0, 0, 18))
            overlay.setColorAt(1.0, QColor(0, 0, 0, 130))
            painter.fillRect(rect, overlay)
        else:
            self.draw_fallback_art(painter, rect)

        painter.setClipping(False)

        painter.setPen(QPen(QColor(96, 78, 55, 130), 1))
        painter.drawPath(path)

        self.draw_photo_caption(painter, rect)

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
        painter.drawRoundedRect(caption_rect, 6, 6)

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
    def __init__(self, headline, source, image_label="", variant="fox"):
        super().__init__()

        self.variant = variant
        self.source = source
        self.image_label = image_label
        self.article_url = ""

        self.setObjectName("NewspaperNewsCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        outer = QVBoxLayout()
        outer.setContentsMargins(12, 8, 12, 10)
        outer.setSpacing(5)
        self.setLayout(outer)

        # Newspaper section title at the top
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.top_source_label = QLabel(source)
        self.top_source_label.setObjectName("OldNewsTopMasthead")
        self.top_source_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.edition_label = QLabel("Politics")
        self.edition_label.setObjectName("OldNewsEditionSmall")
        self.edition_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

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

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(12, 8, 12, 8)
        text_layout.setSpacing(4)
        self.text_panel.setLayout(text_layout)

        self.kicker_label = QLabel("TOP STORY" if variant == "fox" else "MARKETS & BUSINESS")
        self.kicker_label.setObjectName("OldNewsKicker")
        self.kicker_label.setAlignment(Qt.AlignLeft)

        self.headline_label = AutoFitLabel(
            headline,
            min_size=15,
            max_size=33,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignTop,
            word_wrap=True,
        )
        self.headline_label.setObjectName("OldNewsHeadline")
        self.headline_label.setCursor(Qt.PointingHandCursor)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(8)

        self.read_label = QLabel("READ ARTICLE")
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
        text_layout.addLayout(bottom_row)

        outer.addWidget(self.image, 54)
        outer.addWidget(self.text_panel, 46)

    def update_article(self, article):
        self.source = article.source
        self.article_url = getattr(article, "link", "") or ""

        self.top_source_label.setText(article.source)
        self.image.set_source_text(article.source)
        self.headline_label.setText(article.title)

        if article.source == "FOX NEWS":
            self.image.set_label_text("LIVE UPDATES")
            self.edition_label.setText("POLITICS")
            self.kicker_label.setText("TOP STORY")
            self.page_label.setText("PAGE 1")
        elif article.source == "CNBC":
            self.image.set_label_text("BUSINESS")
            self.edition_label.setText("BUSINESS EDITION")
            self.kicker_label.setText("BUSINESS")
            self.page_label.setText("PAGE 2")
        else:
            self.image.set_label_text("LATEST")
            self.edition_label.setText("POLITICS")
            self.kicker_label.setText("LATEST")
            self.page_label.setText("PAGE 1")

        if self.article_url:
            self.read_label.setText("READ ARTICLE")
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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.article_url:
            QDesktopServices.openUrl(QUrl(self.article_url))

        super().mousePressEvent(event)