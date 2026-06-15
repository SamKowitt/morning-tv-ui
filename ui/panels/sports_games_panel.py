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
            5 if compact else 6,
            6 if compact else 7,
            5 if compact else 6,
        )
        layout.setSpacing(5 if compact else 6)
        self.setLayout(layout)

        time_label = QLabel(time)
        time_label.setObjectName("PaperGameTime")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setFixedWidth(54 if compact else 72)
        time_label.setMinimumHeight(18 if compact else 24)
        time_font_size = 11 if compact else 14

        time_label.setStyleSheet(f"""
            QLabel#PaperGameTime {{
                color: #3b2a17;
                background: transparent;
                font-size: {time_font_size}px;
                font-weight: 1000;
                letter-spacing: 0.2px;
            }}
        """)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(1 if compact else 2)

        matchup_label = QLabel(matchup)
        matchup_label.setObjectName("PaperGameMatchup")
        matchup_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        matchup_label.setWordWrap(False)
        matchup_label.setMinimumHeight(18 if compact else 24)
        is_no_games_placeholder = str(matchup or "").strip().lower() == "no games scheduled"

        if is_no_games_placeholder:
            matchup_font_size = 10 if compact else 11
        else:
            # Compact mode is used when a league has three games displayed.
            # Make MLB-style matchup text like "MIN @ TEX" slightly smaller
            # so pitcher/detail text has more room in each game bubble.
            matchup_font_size = 12 if compact else 16

        matchup_label.setStyleSheet(f"""
            QLabel#PaperGameMatchup {{
                color: #1f160d;
                background: transparent;
                font-size: {matchup_font_size}px;
                font-weight: 1000;
                letter-spacing: 0.5px;
            }}
        """)
        info.addWidget(matchup_label, 2)

        if detail:
            info.addStretch(1)

            detail_label = AutoFitLabel(
                detail,
                min_size=4 if compact else 5,
                max_size=34 if compact else 8,
                bold=False,
                alignment=Qt.AlignLeft | Qt.AlignBottom,
                word_wrap=True,
            )
            detail_label.setObjectName("PaperGameDetail")
            detail_label.setMinimumHeight(9 if compact else 12)
            info.addWidget(detail_label, 0)

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


class EmptyGamesMessage(QWidget):
    def __init__(self, message):
        super().__init__()

        self.setObjectName("PaperLeagueColumn")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        self.setLayout(layout)

        title = AutoFitLabel(
            "NO CURRENT GAMES",
            min_size=10,
            max_size=20,
            bold=True,
            alignment=Qt.AlignCenter,
            word_wrap=False,
        )
        title.setObjectName("PaperLeagueTitle")

        body = AutoFitLabel(
            message,
            min_size=8,
            max_size=14,
            bold=True,
            alignment=Qt.AlignCenter,
            word_wrap=True,
        )
        body.setObjectName("PaperGameDetail")

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(GamesPaperDivider())
        layout.addWidget(body)
        layout.addStretch(1)


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
            "Game Times:",
            min_size=14,
            max_size=27,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
            word_wrap=False,
        )
        masthead.setObjectName("PaperMasthead")

        self.edition = AutoFitLabel(
            "Today's Games",
            min_size=6,
            max_size=10,
            bold=True,
            alignment=Qt.AlignRight | Qt.AlignVCenter,
            word_wrap=False,
        )
        self.edition.setObjectName("PaperEditionLine")

        header.addWidget(masthead, 35)
        header.addWidget(self.edition, 65)

        main.addLayout(header, 14)
        main.addWidget(GamesPaperDivider())

        self.columns = QHBoxLayout()
        self.columns.setSpacing(6)
        self.columns.setContentsMargins(0, 0, 0, 0)

        main.addLayout(self.columns, 74)

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

        self.set_loading()

    def clear_columns(self):
        while self.columns.count():
            item = self.columns.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def set_loading(self):
        self.edition.setText("Loading live schedules")
        self.clear_columns()

        self.columns.addWidget(
            EmptyGamesMessage("Checking MLB, NFL, and NBA schedules..."),
            1,
        )

    def set_error(self, message="Unable to load live games."):
        self.edition.setText("Schedule unavailable")
        self.clear_columns()

        self.columns.addWidget(
            EmptyGamesMessage(message),
            1,
        )

    def normalize_game(self, game):
        if isinstance(game, dict):
            return (
                game.get("matchup", ""),
                game.get("time", ""),
                game.get("detail", ""),
            )

        if isinstance(game, (tuple, list)):
            matchup = game[0] if len(game) > 0 else ""
            time = game[1] if len(game) > 1 else ""
            detail = game[2] if len(game) > 2 else ""
            return matchup, time, detail

        return (
            getattr(game, "matchup", ""),
            getattr(game, "time", ""),
            getattr(game, "detail", ""),
        )

    def normalize_league(self, league_data):
        if isinstance(league_data, dict):
            emoji = league_data.get("emoji", "")
            league = league_data.get("league", "")
            games = league_data.get("games", [])
        else:
            emoji = getattr(league_data, "emoji", "")
            league = getattr(league_data, "league", "")
            games = getattr(league_data, "games", [])

        normalized_games = []

        for game in games:
            matchup, time, detail = self.normalize_game(game)

            if matchup and time:
                normalized_games.append((matchup, time, detail))

        return emoji, league, normalized_games

    def update_leagues(self, leagues):
        print("SportsGamesPanel received leagues:", leagues)

        self.clear_columns()

        active_leagues = []

        for league_data in leagues or []:
            emoji, league, games = self.normalize_league(league_data)

            print(f"Normalized league {league}: {len(games)} game(s)")

            if league:
                active_leagues.append((emoji, league, games))

        if not active_leagues:
            self.edition.setText("No active leagues")
            self.columns.addWidget(
                EmptyGamesMessage("No MLB, NFL, or NBA leagues are currently in season."),
                1,
            )
            return

        league_names = " / ".join([league for _, league, _ in active_leagues])
        self.edition.setText(f"In Season: {league_names}")

        for emoji, league, games in active_leagues:
            display_games = games

            if not display_games:
                display_games = [
                    ("No games scheduled", "—", "No games found in the next 3 days")
                ]

            self.columns.addWidget(
                LeagueColumn(
                    emoji=emoji,
                    league=league,
                    games=display_games,
                ),
                1,
            )

    def update_games_data(self, leagues):
        self.update_leagues(leagues)