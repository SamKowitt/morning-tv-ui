from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


from ui.newspaper_chrome import draw_stacked_newspaper_panel


class SportsGamesPanel(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("NewspaperGamesCard")
        self.setAttribute(Qt.WA_StyledBackground, False)

        self.leagues = []
        self.edition_text = "Loading live schedules"
        self.message = "Checking MLB, NFL, and NBA schedules..."

        self.setMinimumHeight(120)

    def set_loading(self):
        self.edition_text = "LOADING LIVE SCHEDULES"
        self.leagues = []
        self.message = "Checking MLB, NFL, and NBA schedules..."
        self.update()

    def set_error(self, message="Unable to load live games."):
        self.edition_text = "SCHEDULE UNAVAILABLE"
        self.leagues = []
        self.message = message
        self.update()

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

        active_leagues = []

        for league_data in leagues or []:
            emoji, league, games = self.normalize_league(league_data)
            print(f"Normalized league {league}: {len(games)} game(s)")

            if league:
                if not games:
                    games = [
                        ("No games scheduled", "—", "No games found today")
                    ]

                active_leagues.append((emoji, league, games[:3]))

        if not active_leagues:
            self.edition_text = "NO ACTIVE LEAGUES"
            self.leagues = []
            self.message = "No MLB, NFL, or NBA leagues are currently in season."
            self.update()
            return

        league_names = " / ".join([league for _, league, _ in active_leagues])
        self.edition_text = f"IN SEASON: {league_names}"
        self.leagues = active_leagues
        self.message = ""
        self.update()

    def update_games_data(self, leagues):
        self.update_leagues(leagues)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        draw_stacked_newspaper_panel(painter, rect)

        inner = rect.adjusted(17, 9, -17, -13)

        self.draw_header(painter, inner)

        top_rule_y = inner.top() + 28
        bottom_rule_y = inner.bottom() - 15

        self.draw_rule(painter, inner.left(), top_rule_y, inner.right())
        self.draw_rule(painter, inner.left(), bottom_rule_y, inner.right())

        footer_font = QFont("Times New Roman", 7)
        footer_font.setBold(True)
        painter.setFont(footer_font)
        painter.setPen(QColor("#5a442b"))
        painter.drawText(
            QRectF(inner.left(), bottom_rule_y + 2, inner.width() / 2, 12),
            Qt.AlignLeft | Qt.AlignVCenter,
            "SCHEDULE BOARD",
        )
        painter.drawText(
            QRectF(inner.center().x(), bottom_rule_y + 2, inner.width() / 2, 12),
            Qt.AlignRight | Qt.AlignVCenter,
            "PAGE 2",
        )

        body = QRectF(
            inner.left(),
            top_rule_y + 3,
            inner.width(),
            bottom_rule_y - top_rule_y - 5,
        )

        if not self.leagues:
            self.draw_empty_state(painter, body)
            return

        self.draw_leagues(painter, body)

    def draw_header(self, painter, inner):
        title_font = QFont("Rockwell", 22)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.PercentageSpacing, 106)

        painter.setFont(title_font)
        painter.setPen(QColor("#241a10"))
        painter.drawText(
            QRectF(inner.left(), inner.top() - 1, inner.width() * 0.72, 24),
            Qt.AlignLeft | Qt.AlignVCenter,
            "GAME TIMES",
        )

        edition_font = QFont("Georgia", 7)
        edition_font.setBold(True)
        edition_font.setLetterSpacing(QFont.PercentageSpacing, 108)

        painter.setFont(edition_font)
        painter.setPen(QColor("#5a442b"))
        painter.drawText(
            QRectF(inner.left() + inner.width() * 0.42, inner.top() - 1, inner.width() * 0.58, 19),
            Qt.AlignRight | Qt.AlignVCenter,
            self.edition_text.upper(),
        )

    def draw_leagues(self, painter, body):
        column_count = max(1, len(self.leagues))
        column_width = body.width() / column_count

        for index, (emoji, league, games) in enumerate(self.leagues):
            left = body.left() + index * column_width
            col = QRectF(left, body.top(), column_width, body.height())

            if index > 0:
                painter.setPen(QPen(QColor(55, 42, 25, 125), 1))
                painter.drawLine(int(col.left()), int(col.top()), int(col.left()), int(col.bottom()))

            padded = col.adjusted(7, 0, -7, 0)
            self.draw_league_column(painter, padded, emoji, league, games)

    def draw_league_column(self, painter, rect, emoji, league, games):
        heading_height = 23

        emoji_font = QFont("Arial", 15)
        painter.setFont(emoji_font)
        painter.setPen(QColor("#21170d"))
        painter.drawText(
            QRectF(rect.left(), rect.top(), 24, heading_height),
            Qt.AlignCenter,
            emoji,
        )

        league_font = QFont("Georgia", 17)
        league_font.setBold(True)
        painter.setFont(league_font)
        painter.setPen(QColor("#21170d"))
        painter.drawText(
            QRectF(rect.left() + 28, rect.top(), rect.width() - 28, heading_height),
            Qt.AlignLeft | Qt.AlignVCenter,
            league,
        )

        self.draw_rule(painter, rect.left(), rect.top() + heading_height, rect.right())

        rows_top = rect.top() + heading_height + 3
        rows_height = rect.height() - heading_height - 3
        row_count = max(2, len(games))
        row_height = rows_height / row_count

        for i in range(row_count):
            row = QRectF(
                rect.left(),
                rows_top + i * row_height,
                rect.width(),
                row_height,
            )

            if i < len(games):
                matchup, time, detail = games[i]
                self.draw_game_row(painter, row, matchup, time, detail, compact=len(games) >= 3)

            if i < row_count - 1:
                self.draw_rule(painter, row.left(), row.bottom(), row.right())

    def draw_game_row(self, painter, row, matchup, time, detail, compact=False):
        time_width = 58 if compact else 66

        time_font = QFont("Times New Roman", 10)
        time_font.setBold(True)

        painter.setFont(time_font)
        painter.setPen(QColor("#25190d"))
        painter.drawText(
            QRectF(row.left(), row.top() + 2, time_width, row.height() - 4),
            Qt.AlignLeft | Qt.AlignTop,
            time,
        )

        matchup_text = str(matchup or "").strip()
        detail_text = str(detail or "").strip()
        is_final_row = str(time or "").strip().upper() == "FINAL"
        is_multiline_score = "\n" in matchup_text or "\r" in matchup_text

        left = row.left() + time_width
        width = row.width() - time_width

        if is_final_row or is_multiline_score:
            # Final score rows are special: draw each score line manually so
            # "LAD 5 / TB 4" cannot get clipped by a tight text rectangle.
            score_lines = [line.strip() for line in matchup_text.replace("\r", "\n").split("\n") if line.strip()]
            if not score_lines:
                score_lines = [matchup_text]

            score_font = QFont("Georgia", 9 if compact else 10)
            score_font.setBold(True)
            painter.setFont(score_font)
            painter.setPen(QColor("#17100a"))

            score_top = row.top() + 1
            line_height = 11 if compact else 12

            for index, line in enumerate(score_lines[:2]):
                painter.drawText(
                    QRectF(
                        left,
                        score_top + index * line_height,
                        width,
                        line_height + 2,
                    ),
                    Qt.AlignLeft | Qt.AlignVCenter,
                    line,
                )

            if detail_text:
                detail_font = QFont("Times New Roman", 9 if compact else 10)
                detail_font.setBold(False)

                painter.setFont(detail_font)
                painter.setPen(QColor("#4f3c25"))

                detail_height = 13 if compact else 15
                detail_rect = QRectF(
                    left,
                    row.bottom() - detail_height - 1,
                    width,
                    detail_height,
                )

                painter.drawText(
                    detail_rect,
                    Qt.AlignLeft | Qt.AlignBottom,
                    detail_text,
                )

            return

        matchup_font = QFont("Georgia", 12 if compact else 14)
        matchup_font.setBold(True)

        painter.setFont(matchup_font)
        painter.setPen(QColor("#17100a"))
        painter.drawText(
            QRectF(
                left,
                row.top() + 1,
                width,
                row.height() * 0.42,
            ),
            Qt.AlignLeft | Qt.AlignVCenter,
            matchup_text,
        )

        if detail_text:
            # Bigger and lower pitcher/detail text for normal game rows.
            detail_font = QFont("Times New Roman", 9 if compact else 10)
            detail_font.setBold(False)

            painter.setFont(detail_font)
            painter.setPen(QColor("#4f3c25"))

            detail_height = 14 if compact else 16
            detail_rect = QRectF(
                left,
                row.bottom() - detail_height - 1,
                width,
                detail_height,
            )

            painter.drawText(
                detail_rect,
                Qt.AlignLeft | Qt.AlignBottom,
                detail_text,
            )

    def draw_empty_state(self, painter, rect):
        dash_font = QFont("Georgia", 28)
        dash_font.setBold(True)
        painter.setFont(dash_font)
        painter.setPen(QColor("#21170d"))
        painter.drawText(rect.adjusted(0, 4, 0, -34), Qt.AlignCenter, "—")

        title_font = QFont("Georgia", 15)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(rect.adjusted(0, 26, 0, -12), Qt.AlignCenter, "No games scheduled")

        body_font = QFont("Times New Roman", 9)
        painter.setFont(body_font)
        painter.setPen(QColor("#4f3c25"))
        painter.drawText(rect.adjusted(12, 54, -12, 0), Qt.AlignCenter | Qt.TextWordWrap, self.message)

    def draw_rule(self, painter, x1, y, x2):
        painter.setPen(QPen(QColor(55, 42, 25, 150), 1))
        painter.drawLine(int(x1), int(y), int(x2), int(y))
