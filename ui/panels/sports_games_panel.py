from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.auto_fit_label import AutoFitLabel


class GamesPaperDivider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setFixedHeight(1)
        self.setStyleSheet("background-color: rgba(90, 78, 63, 120); border: none;")


class BlankGameSlot(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("PaperGameBlankSlot")
        self.setAttribute(Qt.WA_StyledBackground, True)


class GameListing(QWidget):
    def __init__(self, matchup, time, detail="", compact=False):
        super().__init__()

        self.setObjectName("PaperGameListing")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout()
        layout.setContentsMargins(
            6 if compact else 7,
            3 if compact else 4,
            6 if compact else 7,
            3 if compact else 4,
        )
        layout.setSpacing(5 if compact else 6)
        self.setLayout(layout)

        time_label = AutoFitLabel(
            time,
            min_size=5 if compact else 6,
            max_size=7 if compact else 8,
            bold=True,
            alignment=Qt.AlignCenter,
            word_wrap=False,
        )
        time_label.setObjectName("PaperGameTime")
        time_label.setFixedWidth(46 if compact else 54)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(0 if compact else 1)

        matchup_label = AutoFitLabel(
            matchup,
            min_size=6 if compact else 7,
            max_size=11 if compact else 14,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
            word_wrap=True,
        )
        matchup_label.setObjectName("PaperGameMatchup")

        info.addWidget(matchup_label, 2)

        if detail:
            detail_label = AutoFitLabel(
                detail,
                min_size=4 if compact else 5,
                max_size=7 if compact else 8,
                bold=False,
                alignment=Qt.AlignLeft | Qt.AlignVCenter,
                word_wrap=True,
            )
            detail_label.setObjectName("PaperGameDetail")
            info.addWidget(detail_label, 1)

        layout.addWidget(time_label)
        layout.addLayout(info, 1)


class LeagueColumn(QWidget):
    def __init__(self, emoji, league, games):
        super().__init__()

        self.setObjectName("PaperLeagueColumn")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout()
        layout.setContentsMargins(7, 4, 7, 5)
        layout.setSpacing(4)
        self.setLayout(layout)

        league_row = QHBoxLayout()
        league_row.setContentsMargins(0, 0, 0, 0)
        league_row.setSpacing(4)

        emoji_label = QLabel(emoji)
        emoji_label.setObjectName("PaperLeagueEmoji")
        emoji_label.setAlignment(Qt.AlignCenter)
        emoji_label.setFixedWidth(22)

        league_label = QLabel(league)
        league_label.setObjectName("PaperLeagueTitle")
        league_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        league_row.addWidget(emoji_label)
        league_row.addWidget(league_label, 1)

        layout.addLayout(league_row)
        layout.addWidget(GamesPaperDivider())

        real_games = games[:3]
        compact = len(real_games) >= 3

        # 1 game -> show 1 game + 1 blank slot
        # 2 games -> show 2 games
        # 3 games -> show 3 compact games
        slots = real_games[:]

        while len(slots) < 2:
            slots.append(None)

        for game in slots:
            if game is None:
                layout.addWidget(BlankGameSlot(), 1)
            else:
                matchup, time, detail = game
                layout.addWidget(
                    GameListing(
                        matchup=matchup,
                        time=time,
                        detail=detail,
                        compact=compact,
                    ),
                    1,
                )


class SportsGamesPanel(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("NewspaperSportsCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        main = QVBoxLayout()
        main.setContentsMargins(12, 6, 12, 6)
        main.setSpacing(3)
        self.setLayout(main)

        header = QHBoxLayout()
        header.setSpacing(8)

        masthead = AutoFitLabel(
            "SPORTS",
            min_size=14,
            max_size=27,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
            word_wrap=False,
        )
        masthead.setObjectName("PaperMasthead")

        edition = AutoFitLabel(
            "Today's Games",
            min_size=6,
            max_size=10,
            bold=True,
            alignment=Qt.AlignRight | Qt.AlignVCenter,
            word_wrap=False,
        )
        edition.setObjectName("PaperEditionLine")

        header.addWidget(masthead, 35)
        header.addWidget(edition, 65)

        main.addLayout(header, 14)
        main.addWidget(GamesPaperDivider())

        columns = QHBoxLayout()
        columns.setSpacing(6)
        columns.setContentsMargins(0, 0, 0, 0)

        columns.addWidget(
            LeagueColumn(
                "⚾",
                "MLB",
                [
                    ("Yankees @ Mets", "7:15 PM", "Schlittler vs. Seaver")
                ],
            ),
            1,
        )

        columns.addWidget(
            LeagueColumn(
                "🏈",
                "NFL",
                [
                    ("Panthers @ Commanders", "1:05 PM", ""),
                    ("Chiefs @ Giants", "3:15 PM", ""),
                    ("Browns @ Ravens", "8:20 PM", ""),
                ],
            ),
            1,
        )

        columns.addWidget(
            LeagueColumn(
                "🏀",
                "NBA",
                [
                    ("Hornets @ Warriors", "6:30 PM", ""),
                    ("Bulls @ Spurs", "7:30 PM", ""),
                ],
            ),
            1,
        )

        main.addLayout(columns, 74)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)

        footer_left = QLabel("SCHEDULE BOARD")
        footer_left.setObjectName("PaperFooterLeft")

        footer_page = QLabel("PAGE 2")
        footer_page.setObjectName("PaperFooterPage")
        footer_page.setAlignment(Qt.AlignRight)

        footer.addWidget(footer_left, 1)
        footer.addWidget(footer_page)

        main.addWidget(GamesPaperDivider())
        main.addLayout(footer, 6)
