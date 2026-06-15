from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.auto_fit_label import AutoFitLabel


class NewspaperDivider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setFixedHeight(1)
        self.setStyleSheet("background-color: rgba(90, 78, 63, 120); border: none;")


class CompactPaperStory(QWidget):
    def __init__(self, headline, kicker="", featured=False, link=""):
        super().__init__()

        self.article_url = link
        self.featured = featured

        self.setObjectName("PaperFeaturedStory" if featured else "PaperStory")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout()

        if featured:
            layout.setContentsMargins(9, 5, 9, 5)
            layout.setSpacing(2)
        else:
            layout.setContentsMargins(7, 3, 7, 3)
            layout.setSpacing(1)

        self.setLayout(layout)

        self.kicker_label = QLabel(kicker)
        self.kicker_label.setObjectName("PaperKickerFeatured" if featured else "PaperKicker")
        self.kicker_label.setAlignment(Qt.AlignLeft)
        self.kicker_label.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.kicker_label)

        self.headline_label = AutoFitLabel(
            headline,
            min_size=10 if featured else 6,
            max_size=22 if featured else 10,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
            word_wrap=True,
        )
        self.headline_label.setObjectName("PaperHeadlineFeatured" if featured else "PaperHeadline")
        self.headline_label.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.headline_label, 1)

    def update_story(self, headline, kicker="ESPN", link=""):
        self.article_url = link or ""

        self.kicker_label.setText(kicker or "ESPN")
        self.headline_label.setText(headline)

        if self.article_url:
            self.setCursor(Qt.PointingHandCursor)
            self.kicker_label.setCursor(Qt.PointingHandCursor)
            self.headline_label.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self.kicker_label.setCursor(Qt.ArrowCursor)
            self.headline_label.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.article_url:
            QDesktopServices.openUrl(QUrl(self.article_url))

        super().mousePressEvent(event)


class SportsNewsPanel(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("NewspaperSportsCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.story_widgets = []

        main = QVBoxLayout()
        main.setContentsMargins(12, 6, 12, 6)
        main.setSpacing(3)
        self.setLayout(main)

        header = QHBoxLayout()
        header.setSpacing(8)

        masthead = AutoFitLabel(
            "ESPN",
            min_size=14,
            max_size=27,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
            word_wrap=False,
        )
        masthead.setObjectName("PaperMasthead")

        edition = AutoFitLabel(
            "Top ESPN Stories",
            min_size=6,
            max_size=10,
            bold=True,
            alignment=Qt.AlignRight | Qt.AlignVCenter,
            word_wrap=False,
        )
        edition.setObjectName("PaperEditionLine")

        header.addWidget(masthead, 35)
        header.addWidget(edition, 65)

        main.addLayout(header, 13)
        main.addWidget(NewspaperDivider())

        lead_story = CompactPaperStory(
            "Loading latest ESPN sports headline...",
            kicker="LEAD STORY",
            featured=True,
        )
        self.story_widgets.append(lead_story)
        main.addWidget(lead_story, 28)

        lower_row = QHBoxLayout()
        lower_row.setSpacing(6)
        lower_row.setContentsMargins(0, 0, 0, 0)

        for _ in range(3):
            story = CompactPaperStory(
                "Loading ESPN sports story...",
                kicker="ESPN",
            )
            self.story_widgets.append(story)
            lower_row.addWidget(story, 1)

        main.addLayout(lower_row, 37)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)

        footer_left = QLabel("SPORTS DESK")
        footer_left.setObjectName("PaperFooterLeft")

        footer_page = QLabel("PAGE 1")
        footer_page.setObjectName("PaperFooterPage")
        footer_page.setAlignment(Qt.AlignRight)

        footer.addWidget(footer_left, 1)
        footer.addWidget(footer_page)

        main.addWidget(NewspaperDivider())
        main.addLayout(footer, 6)

    def update_articles(self, articles):
        for index, story_widget in enumerate(self.story_widgets):
            if index >= len(articles):
                story_widget.update_story("", "ESPN", "")
                continue

            article = articles[index]

            if index == 0:
                kicker = "LEAD STORY"
            else:
                kicker = article.category or "ESPN"

            story_widget.update_story(
                headline=article.title,
                kicker=kicker,
                link=article.link,
            )