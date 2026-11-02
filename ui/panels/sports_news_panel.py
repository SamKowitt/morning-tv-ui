from PySide6.QtGui import QTextLayout, QTextOption
from PySide6.QtCore import QPointF
import sys

from PySide6.QtCore import QRectF, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontMetrics, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


from ui.newspaper_chrome import draw_stacked_newspaper_panel
from ui.panels.news_card import OpenNewspaperDialog
from services.article_text_fetcher import prefetch_article_text_payload


class SportsNewsPanel(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("NewspaperSportsCard")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setCursor(Qt.PointingHandCursor)

        self.articles = []
        self.click_zones = []
        self.article_dialog = None
        self.live_logo_pixmaps = {}

        self.setMinimumHeight(120)

    def update_articles(self, articles):
        self.articles = list(articles or [])[:5]
        self.cache_live_lead_logos()

        # Start article-text requests in background immediately after the
        # Sports Desk receives new stories. The popup will use the cache when
        # the user clicks a story.
        for article in self.articles:
            link = str(getattr(article, "link", "") or "").strip()

            # ESPN game modules point to game/video pages, not
            # editorial articles. Do not scrape active or final games
            # as newspaper article text.
            if (
                link
                and not bool(
                    getattr(
                        article,
                        "is_game_lead",
                        False,
                    )
                )
            ):
                prefetch_article_text_payload(link)

        self.update()

    def cache_live_lead_logos(self):
        self.live_logo_pixmaps = {}

        if not self.articles:
            return

        lead = self.articles[0]

        if not bool(
            getattr(lead, "is_game_lead", False)
        ):
            return

        for side in ("away", "home"):
            image_bytes = getattr(
                lead,
                f"{side}_logo_bytes",
                b"",
            ) or b""

            if not image_bytes:
                continue

            pixmap = QPixmap()

            if (
                pixmap.loadFromData(image_bytes)
                and not pixmap.isNull()
            ):
                self.live_logo_pixmaps[side] = pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        draw_stacked_newspaper_panel(painter, rect)

        inner = rect.adjusted(17, 9, -17, -13)
        self.click_zones = []

        self.draw_header(painter, inner)

        top_rule_y = inner.top() + 24
        footer_rule_y = inner.bottom() - 15

        self.draw_rule(painter, inner.left(), top_rule_y, inner.right())
        self.draw_rule(painter, inner.left(), footer_rule_y, inner.right())

        footer_font = QFont("Times New Roman", 7)
        footer_font.setBold(True)
        painter.setFont(footer_font)
        painter.setPen(QColor("#5a442b"))

        painter.drawText(
            QRectF(inner.left(), footer_rule_y + 2, inner.width() / 2, 12),
            Qt.AlignLeft | Qt.AlignVCenter,
            "SPORTS ESPN",
        )
        painter.drawText(
            QRectF(inner.center().x(), footer_rule_y + 2, inner.width() / 2, 12),
            Qt.AlignRight | Qt.AlignVCenter,
            "PAGE 1",
        )

        body = QRectF(
            inner.left(),
            top_rule_y + 2,
            inner.width(),
            footer_rule_y - top_rule_y - 3,
        )

        self.draw_body(painter, body)

    def draw_header(self, painter, inner):
        title_font = QFont("Rockwell", 22)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.PercentageSpacing, 106)

        painter.setFont(title_font)
        painter.setPen(QColor("#241a10"))
        painter.drawText(
            QRectF(inner.left(), inner.top() + 2, inner.width() * 0.72, 23),
            Qt.AlignLeft | Qt.AlignVCenter,
            "ESPN",
        )

        page_font = QFont("Georgia", 8)
        page_font.setBold(True)
        page_font.setLetterSpacing(QFont.PercentageSpacing, 108)

        painter.setFont(page_font)
        painter.setPen(QColor("#5a442b"))
        painter.drawText(
            QRectF(inner.left() + inner.width() * 0.72, inner.top() + 2, inner.width() * 0.28, 18),
            Qt.AlignRight | Qt.AlignVCenter,
            "P. 1",
        )

    def draw_body(self, painter, body):
        if not self.articles:
            self.draw_loading(painter, body)
            return

        lead = self.articles[0]
        small_articles = self.articles[1:5]

        lead_rect = QRectF(
            body.left(),
            body.top(),
            body.width(),
            body.height() * 0.56,
        )

        lower_top = lead_rect.bottom() + 5
        lower_rect = QRectF(
            body.left(),
            lower_top,
            body.width(),
            body.bottom() - lower_top,
        )

        self.draw_lead_story(painter, lead_rect, lead)
        self.draw_rule(painter, body.left(), lead_rect.bottom() + 2, body.right())
        self.draw_small_stories(painter, lower_rect, small_articles)

    def draw_loading(self, painter, rect):
        kicker_font = QFont("Times New Roman", 9)
        kicker_font.setBold(True)

        painter.setFont(kicker_font)
        painter.setPen(QColor("#9c6424"))
        painter.drawText(
            QRectF(rect.left(), rect.top(), rect.width(), 16),
            Qt.AlignLeft | Qt.AlignVCenter,
            "TOP STORIES",
        )

        headline_font = QFont("Georgia", 22)
        headline_font.setBold(True)

        painter.setFont(headline_font)
        painter.setPen(QColor("#17100a"))
        painter.drawText(
            rect.adjusted(0, 16, 0, 0),
            Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
            "Loading latest sports headlines...",
        )

    def draw_lead_story(self, painter, rect, article):
        kicker_font = QFont("Times New Roman", 9)
        kicker_font.setBold(True)

        painter.setFont(kicker_font)
        painter.setPen(QColor("#9c6424"))
        painter.drawText(
            QRectF(rect.left(), rect.top(), rect.width(), 15),
            Qt.AlignLeft | Qt.AlignVCenter,
            "TOP STORIES",
        )

        is_game_lead = bool(
            getattr(article, "is_game_lead", False)
            and getattr(article, "away_team", "")
            and getattr(article, "away_score", "")
            and getattr(article, "home_team", "")
            and getattr(article, "home_score", "")
            and getattr(article, "game_status", "")
        )

        if is_game_lead:
            self.draw_live_game_lead(
                painter,
                rect,
                article,
            )
            return

        # Ordinary ESPN editorial leads keep the existing headline-only
        # presentation.
        headline_font = QFont("Georgia", 22)
        headline_font.setBold(True)

        painter.setFont(headline_font)
        # MORNINGUI_CEC_SPORTS_TEXT_V6: tint only selected headline glyphs.
        painter.setPen(QColor(
            "#705C00" if getattr(self, "_morningui_remote_sports_index", -1) == 0
            else "#15100b"
        ))

        headline_rect = QRectF(
            rect.left(),
            rect.top() + 17,
            rect.width(),
            rect.height() - 17,
        )

        self.draw_two_line_lead_headline(
            painter,
            headline_rect,
            self.clean_title(getattr(article, "title", "")),
            headline_font,
        )

        self.add_click_zone(
            headline_rect,
            getattr(article, "link", ""),
            self.clean_title(getattr(article, "title", "")),
        )

    def draw_live_game_lead(
        self,
        painter,
        rect,
        article,
    ):
        content_top = rect.top() + 17
        available_height = max(
            52.0,
            rect.bottom() - content_top,
        )

        scoreboard_height = max(
            38.0,
            min(
                50.0,
                available_height * 0.43,
            ),
        )
        # Use most of the lead-story width so both complete team
        # names can fit beside their records, logos, and scores.
        scoreboard_width = max(
            520.0,
            min(
                760.0,
                rect.width() * 0.84,
            ),
        )
        scoreboard_width = min(
            scoreboard_width,
            rect.width(),
        )

        scoreboard_rect = QRectF(
            rect.center().x()
            - scoreboard_width / 2,
            content_top,
            scoreboard_width,
            scoreboard_height,
        )

        self.draw_live_scoreboard(
            painter,
            scoreboard_rect,
            article,
        )

        headline = self.clean_title(
            getattr(article, "title", "")
        )

        # Display the live-game headline alongside TOP STORIES.
        # The scoreboard and all section dimensions are unchanged.
        caption_left = rect.left() + 76
        caption_rect = QRectF(
            caption_left,
            rect.top(),
            max(1.0, rect.right() - caption_left),
            18,
        )

        caption_font = QFont("Georgia", 11)
        caption_font.setBold(True)

        metrics = QFontMetrics(caption_font)

        while (
            caption_font.pointSize() > 7
            and metrics.height() > caption_rect.height() - 1
        ):
            caption_font.setPointSize(
                caption_font.pointSize() - 1
            )
            metrics = QFontMetrics(caption_font)

        visible_headline = metrics.elidedText(
            headline,
            Qt.ElideRight,
            max(1, int(caption_rect.width())),
        )

        painter.save()
        painter.setClipRect(caption_rect)
        painter.setFont(caption_font)
        painter.setPen(QColor("#15100b"))
        painter.drawText(
            caption_rect,
            Qt.AlignLeft | Qt.AlignVCenter,
            visible_headline,
        )
        painter.restore()

        self.add_click_zone(
            QRectF(
                rect.left(),
                content_top,
                rect.width(),
                rect.bottom() - content_top,
            ),
            getattr(article, "link", ""),
            headline,
            open_external=True,
        )

    def draw_game_lead_headline(
        self,
        painter,
        rect,
        title,
    ):
        """
        Draw only live/final game-lead headlines within their exact area.

        Ordinary ESPN editorial leads continue using the existing fixed
        two-line headline renderer without any behavior change.
        """
        painter.save()

        try:
            # This is the hard boundary that prevents the headline from
            # entering the divider or the four smaller article columns.
            painter.setClipRect(rect)
            painter.setPen(QColor(
                "#705C00" if getattr(self, "_morningui_remote_sports_index", -1) == 0
                else "#15100b"
            ))

            text = " ".join(
                str(title or "").split()
            )

            if not text:
                return

            available_width = max(
                20,
                int(rect.width()),
            )
            available_height = max(
                1,
                int(rect.height()),
            )
            words = text.split()

            def wrapped_lines(metrics, max_lines):
                raw_lines = []
                current = ""
                word_index = 0

                while word_index < len(words):
                    word = words[word_index]
                    candidate = (
                        f"{current} {word}".strip()
                    )

                    if (
                        not current
                        or metrics.horizontalAdvance(
                            candidate
                        ) <= available_width
                    ):
                        current = candidate
                        word_index += 1
                        continue

                    raw_lines.append(current)
                    current = ""

                    if len(raw_lines) >= max_lines:
                        break

                if (
                    current
                    and len(raw_lines) < max_lines
                ):
                    raw_lines.append(current)

                complete = (
                    word_index >= len(words)
                    and all(
                        metrics.horizontalAdvance(line)
                        <= available_width
                        for line in raw_lines
                    )
                )

                rendered_lines = [
                    metrics.elidedText(
                        line,
                        Qt.ElideRight,
                        available_width,
                    )
                    for line in raw_lines[:max_lines]
                ]

                if not complete:
                    if not rendered_lines:
                        rendered_lines = [
                            metrics.elidedText(
                                text,
                                Qt.ElideRight,
                                available_width,
                            )
                        ]
                    else:
                        remaining = " ".join(
                            words[word_index:]
                        )
                        combined = (
                            f"{rendered_lines[-1]} "
                            f"{remaining}"
                        ).strip()
                        rendered_lines[-1] = (
                            metrics.elidedText(
                                combined,
                                Qt.ElideRight,
                                available_width,
                            )
                        )

                return (
                    rendered_lines[:max_lines],
                    complete,
                )

            selected = None
            fallback = None

            # Preserve the normal 22-point appearance whenever it fits.
            # Reduce only game-lead headlines and only as much as needed.
            for point_size in range(22, 13, -1):
                font = QFont(
                    "Georgia",
                    point_size,
                )
                font.setBold(True)
                metrics = QFontMetrics(font)
                line_height = max(
                    1,
                    metrics.lineSpacing(),
                )
                max_lines = max(
                    1,
                    min(
                        2,
                        available_height // line_height,
                    ),
                )

                lines, complete = wrapped_lines(
                    metrics,
                    max_lines,
                )
                candidate = (
                    font,
                    line_height,
                    lines,
                )
                fallback = candidate

                if complete:
                    selected = candidate
                    break

            if selected is None:
                selected = fallback

            if selected is None:
                return

            font, line_height, lines = selected
            painter.setFont(font)

            for row, line in enumerate(lines):
                line_top = (
                    rect.top()
                    + row * line_height
                )
                remaining_height = (
                    rect.bottom() - line_top
                )

                if remaining_height <= 0:
                    break

                painter.drawText(
                    QRectF(
                        rect.left(),
                        line_top,
                        rect.width(),
                        min(
                            float(line_height),
                            remaining_height,
                        ),
                    ),
                    Qt.AlignLeft | Qt.AlignTop,
                    line,
                )

        finally:
            painter.restore()

    def draw_live_scoreboard(
        self,
        painter,
        rect,
        article,
    ):
        painter.save()
        painter.setRenderHint(
            QPainter.SmoothPixmapTransform,
            True,
        )

        # Draw the live-game information directly on the newspaper
        # surface. Do not place a separate box, fill, or border behind it.

        center_width = max(
            72.0,
            min(
                96.0,
                rect.width() * 0.20,
            ),
        )
        side_width = (
            rect.width() - center_width
        ) / 2
        left_side = QRectF(
            rect.left(),
            rect.top(),
            side_width,
            rect.height(),
        )
        center = QRectF(
            left_side.right(),
            rect.top(),
            center_width,
            rect.height(),
        )
        right_side = QRectF(
            center.right(),
            rect.top(),
            side_width,
            rect.height(),
        )

        self.draw_scoreboard_team(
            painter,
            left_side,
            team_name=str(
                getattr(
                    article,
                    "away_team",
                    "",
                )
                or ""
            ),
            record=str(
                getattr(
                    article,
                    "away_record",
                    "",
                )
                or ""
            ),
            score=str(
                getattr(
                    article,
                    "away_score",
                    "",
                )
                or ""
            ),
            logo=self.live_logo_pixmaps.get(
                "away"
            ),
            team_on_outer_side=True,
        )

        self.draw_scoreboard_team(
            painter,
            right_side,
            team_name=str(
                getattr(
                    article,
                    "home_team",
                    "",
                )
                or ""
            ),
            record=str(
                getattr(
                    article,
                    "home_record",
                    "",
                )
                or ""
            ),
            score=str(
                getattr(
                    article,
                    "home_score",
                    "",
                )
                or ""
            ),
            logo=self.live_logo_pixmaps.get(
                "home"
            ),
            team_on_outer_side=False,
        )

        # Show only the game status in the center. Active games use
        # red; completed games use the normal newspaper text color.
        status_font = QFont("Arial")
        status_font.setPointSizeF(13.5)
        status_font.setBold(True)
        painter.setFont(status_font)

        game_state = str(
            getattr(
                article,
                "game_state",
                "",
            )
            or ""
        ).strip().lower()

        painter.setPen(
            QColor(
                "#d11616"
                if game_state == "in"
                else "#4a4339"
            )
        )
        # ESPN_LIVE_STATUS_150_PERCENT_V8
        # Display the game clock and period
        # on ONE LINE separated by a space.
        # Never insert newline characters.

        status_text = str(
            getattr(article, "game_status", "")
            or ""
        ).strip()

        # Fix literal backslash-n sequences
        # left by the previous update.
        status_text = status_text.replace(
            chr(92) + "n",
            " "
        )

        # Also handle actual line breaks.
        status_text = status_text.replace(
            chr(10),
            " "
        ).replace(
            chr(13),
            " "
        )

        # Replace time/period separators
        # with ordinary spaces.
        status_text = (
            status_text
            .replace(" - ", " ")
            .replace(" – ", " ")
            .replace(" — ", " ")
        )

        # Remove duplicate whitespace.
        status_text = " ".join(
            status_text.split()
        )

        # Preserve the existing game-status
        # positioning and available space.
        status_rect = QRectF(
            center.left() - 15,
            center.top() - 8,
            center.width() + 30,
            center.height() + 16,
        )

        painter.drawText(
            status_rect,
            Qt.AlignCenter,
            status_text,
        )

        painter.restore()

    def draw_scoreboard_team(
        self,
        painter,
        rect,
        team_name,
        record,
        score,
        logo,
        team_on_outer_side,
    ):
        # ESPN_TEAM_NAMES_V4
        # Use the available width and explicitly draw
        # multiword team names on two lines.

        painter.save()

        padding = 3.0
        gap = 3.0

        logo_size = min(
            30.0,
            max(22.0, rect.height() - 7.0),
        )

        score_width = min(
            44.0,
            max(35.0, rect.width() * 0.22),
        )

        name_width = max(
            1.0,
            rect.width()
            - 2 * padding
            - 2 * gap
            - logo_size
            - score_width,
        )

        if team_on_outer_side:
            name_rect = QRectF(
                rect.left() + padding,
                rect.top(),
                name_width,
                rect.height(),
            )

            logo_rect = QRectF(
                name_rect.right() + gap,
                rect.center().y() - logo_size / 2,
                logo_size,
                logo_size,
            )

            score_rect = QRectF(
                logo_rect.right() + gap,
                rect.top(),
                score_width,
                rect.height(),
            )

            alignment = Qt.AlignRight

        else:
            score_rect = QRectF(
                rect.left() + padding,
                rect.top(),
                score_width,
                rect.height(),
            )

            logo_rect = QRectF(
                score_rect.right() + gap,
                rect.center().y() - logo_size / 2,
                logo_size,
                logo_size,
            )

            name_rect = QRectF(
                logo_rect.right() + gap,
                rect.top(),
                name_width,
                rect.height(),
            )

            alignment = Qt.AlignLeft

        # Draw score.
        score_font = QFont("Arial", 24)
        score_font.setBold(True)

        painter.setFont(score_font)
        painter.setPen(QColor("#171717"))

        painter.drawText(
            score_rect,
            Qt.AlignCenter,
            str(score),
        )

        # Draw team logo.
        if logo is not None and not logo.isNull():
            scaled_logo = logo.scaled(
                int(logo_rect.width()),
                int(logo_rect.height()),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

            painter.drawPixmap(
                int(
                    logo_rect.center().x()
                    - scaled_logo.width() / 2
                ),
                int(
                    logo_rect.center().y()
                    - scaled_logo.height() / 2
                ),
                scaled_logo,
            )

        else:
            fallback_font = QFont("Arial", 8)
            fallback_font.setBold(True)

            painter.setFont(fallback_font)
            painter.setPen(QColor("#4a4339"))

            painter.drawText(
                logo_rect,
                Qt.AlignCenter,
                self.team_abbreviation(team_name),
            )

        # Explicitly split multiword names into
        # two lines, choosing the largest font that
        # fits horizontally AND vertically.

        full_name = " ".join(
            str(team_name or "").split()
        )

        words = full_name.split()
        available_width = max(
            1,
            int(name_rect.width()) - 2,
        )

        available_height = max(
            1,
            int(name_rect.height()) - 2,
        )

        chosen_font = None
        chosen_lines = None

        for size in range(14, 5, -1):
            font = QFont("Arial", size)
            font.setBold(True)

            metrics = QFontMetrics(font)

            if len(words) >= 2:
                if (
                    metrics.lineSpacing() * 2
                    > available_height
                ):
                    continue

                candidates = []

                for split in range(1, len(words)):
                    first = " ".join(words[:split])
                    second = " ".join(words[split:])

                    w1 = metrics.horizontalAdvance(first)
                    w2 = metrics.horizontalAdvance(second)

                    if (
                        w1 <= available_width
                        and w2 <= available_width
                    ):
                        candidates.append(
                            (
                                max(w1, w2),
                                abs(w1 - w2),
                                [first, second],
                            )
                        )

                if candidates:
                    chosen_font = font
                    chosen_lines = min(candidates)[2]
                    break

            else:
                if (
                    metrics.horizontalAdvance(full_name)
                    <= available_width
                    and metrics.lineSpacing()
                    <= available_height
                ):
                    chosen_font = font
                    chosen_lines = [full_name]
                    break

        if chosen_font is None:
            chosen_font = QFont("Arial", 6)
            chosen_font.setBold(True)

            metrics = QFontMetrics(chosen_font)

            if len(words) >= 2:
                splits = []

                for split in range(1, len(words)):
                    first = " ".join(words[:split])
                    second = " ".join(words[split:])

                    splits.append(
                        (
                            max(
                                metrics.horizontalAdvance(first),
                                metrics.horizontalAdvance(second),
                            ),
                            [first, second],
                        )
                    )

                chosen_lines = min(splits)[1]
            else:
                chosen_lines = [full_name]

        # ESPN_LIVE_TEAM_125_PERCENT_V8
        # Start with 150% of the original selected
        # font size. Reduce only if a complete line
        # would otherwise be cut off.
        #
        # Allow the team-name text a little more
        # vertical room without moving or resizing
        # the scoreboard, scores, or logos.

        base_size = chosen_font.pointSizeF()
        target_size = base_size * 1.25

        expanded_name_rect = name_rect.adjusted(
            0, -8, 0, 8
        )

        for step in range(20, -1, -1):
            candidate_size = (
                base_size
                + (target_size - base_size)
                * step / 20.0
            )

            test_font = QFont(chosen_font)
            test_font.setPointSizeF(candidate_size)

            test_metrics = QFontMetrics(test_font)

            fits_height = (
                test_metrics.lineSpacing()
                * len(chosen_lines)
                <= expanded_name_rect.height()
            )

            fits_width = all(
                test_metrics.horizontalAdvance(line)
                <= available_width
                for line in chosen_lines
            )

            if fits_height and fits_width:
                chosen_font = test_font
                break

        name_rect = expanded_name_rect

        metrics = QFontMetrics(chosen_font)
        line_height = metrics.lineSpacing()

        total_height = (
            line_height * len(chosen_lines)
        )

        start_y = (
            name_rect.center().y()
            - total_height / 2
        )

        painter.setClipRect(name_rect)
        painter.setFont(chosen_font)
        painter.setPen(QColor("#202020"))

        for i, line in enumerate(chosen_lines):
            display_line = metrics.elidedText(
                line,
                Qt.ElideRight,
                available_width,
            )

            line_rect = QRectF(
                name_rect.left(),
                start_y + i * line_height,
                name_rect.width(),
                line_height,
            )

            painter.drawText(
                line_rect,
                alignment | Qt.AlignVCenter,
                display_line,
            )

        painter.restore()

    def team_abbreviation(self, team_name):
        words = [
            word
            for word in str(
                team_name or ""
            ).split()
            if word
        ]

        if not words:
            return ""

        if len(words) == 1:
            return words[0][:3].upper()

        return "".join(
            word[0]
            for word in words[-3:]
        ).upper()

    def draw_two_line_lead_headline(self, painter, rect, title, font):
        """
        Draw a lead headline at the supplied font size across up to two
        full-width rows. Only overflow after row two receives an ellipsis.
        """
        painter.save()
        painter.setFont(font)

        metrics = QFontMetrics(font)
        available_width = max(20, int(rect.width()))
        line_height = metrics.lineSpacing()

        words = str(title or "").split()
        if not words:
            painter.restore()
            return

        lines = []
        current = ""
        next_word_index = 0

        for index, word in enumerate(words):
            candidate = f"{current} {word}".strip()

            if not current or metrics.horizontalAdvance(candidate) <= available_width:
                current = candidate
                next_word_index = index + 1
                continue

            lines.append(current)
            current = word
            next_word_index = index + 1

            if len(lines) == 2:
                break

        if len(lines) < 2 and current:
            lines.append(current)

        # Everything not placed in line 1 or line 2 belongs at the end
        # of line 2, where Qt may add one final ellipsis.
        consumed = len(" ".join(lines).split())
        remaining = words[consumed:]

        if remaining and lines:
            line_two = f"{lines[-1]} {' '.join(remaining)}".strip()
            lines[-1] = metrics.elidedText(
                line_two,
                Qt.ElideRight,
                available_width,
            )

        for row, line in enumerate(lines[:2]):
            painter.drawText(
                QRectF(
                    rect.left(),
                    rect.top() + row * line_height,
                    rect.width(),
                    line_height,
                ),
                Qt.AlignLeft | Qt.AlignTop,
                line,
            )

        painter.restore()

    def draw_small_stories(self, painter, rect, articles):
        # ESPN_SECONDARY_EXPANDED_V3
        # No repeated ESPN category headings.
        # Use 60 original headline characters plus ...
        # Maximize font size using available card height.
        # Preserve all article and panel dimensions.

        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QTextLayout, QTextOption

        count = 4
        column_width = rect.width() / count

        for index in range(count):
            left = rect.left() + index * column_width

            col = QRectF(
                left,
                rect.top(),
                column_width,
                rect.height(),
            )

            # Preserve existing column separators.
            if index > 0:
                painter.setPen(
                    QPen(QColor(55, 42, 25, 115), 1)
                )
                painter.drawLine(
                    int(col.left()),
                    int(col.top() + 2),
                    int(col.left()),
                    int(col.bottom() - 2),
                )

            padded = col.adjusted(
                7 if index > 0 else 0,
                0,
                -7,
                0,
            )

            if index >= len(articles):
                continue

            article = articles[index]

            full_title = " ".join(
                self.clean_title(
                    getattr(article, "title", "")
                ).split()
            )

            # MORNINGUI_ESPN_SECONDARY_FIXED_10_5_V2
            # Fixed font size; shorten text instead of shrinking.
            headline_rect = padded.adjusted(0, 0, 0, -9)
            width = max(1.0, headline_rect.width() - 2)
            height = max(1.0, headline_rect.height() - 1)

            option = QTextOption()
            option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

            font = QFont("Georgia")
            font.setPointSizeF(10.5)
            font.setBold(True)
            font.setStretch(100)

            def layout_for(text):
                candidate_layout = QTextLayout(
                    text, font, painter.device()
                )
                candidate_layout.setTextOption(option)
                candidate_layout.beginLayout()

                y = 0.0
                while True:
                    line = candidate_layout.createLine()
                    if not line.isValid():
                        break
                    line.setLineWidth(width)
                    line.setPosition(QPointF(0, y))
                    y += line.height()

                candidate_layout.endLayout()
                return candidate_layout, y <= height

            chosen_layout, fits = layout_for(full_title)

            if not fits:
                low, high = 0, len(full_title)

                while low < high:
                    mid = (low + high + 1) // 2
                    candidate = full_title[:mid].rstrip() + "..."
                    _, fits = layout_for(candidate)

                    if fits:
                        low = mid
                    else:
                        high = mid - 1

                shortened = full_title[:low].rstrip() + "..."
                chosen_layout, fits = layout_for(shortened)

                if not fits:
                    chosen_layout, _ = layout_for("...")

            painter.save()
            painter.setClipRect(headline_rect)
            painter.setPen(QColor(
                "#705C00" if getattr(self, "_morningui_remote_sports_index", -1) == index + 1
                else "#21180f"
            ))

            chosen_layout.draw(
                painter,
                QPointF(
                    headline_rect.left(),
                    headline_rect.top(),
                ),
            )

            painter.restore()

            # Preserve the article page number.
            page_font = QFont("Times New Roman", 7)
            page_font.setBold(True)

            painter.setFont(page_font)
            painter.setPen(QColor("#5a442b"))

            painter.drawText(
                QRectF(
                    padded.left(),
                    padded.bottom() - 9,
                    padded.width(),
                    9,
                ),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"P. {index + 1}",
            )

            # Preserve the full clickable article.
            self.add_click_zone(
                padded,
                getattr(article, "link", ""),
                full_title,
            )

    def add_click_zone(
        self,
        rect,
        link,
        headline="",
        open_external=False,
    ):
        if link:
            self.click_zones.append(
                (
                    QRectF(rect),
                    str(link or ""),
                    str(headline or ""),
                    bool(open_external),
                )
            )

    def open_article_popup(self, article_url, article_headline):
        article_url = str(article_url or "").strip()

        if not article_url:
            return

        parent_window = self.window()

        self.article_dialog = OpenNewspaperDialog(
            source="ESPN",
            headline=str(article_headline or "").strip() or "ESPN",
            article_url=article_url,
            parent=parent_window,
        )

        if parent_window:
            parent_rect = parent_window.rect()

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            position = event.position()

            for (
                rect,
                link,
                headline,
                open_external,
            ) in self.click_zones:
                if not rect.contains(position):
                    continue

                if open_external:
                    QDesktopServices.openUrl(
                        QUrl(link)
                    )
                else:
                    self.open_article_popup(
                        link,
                        headline,
                    )

                return

        super().mousePressEvent(event)

    def draw_rule(self, painter, x1, y, x2):
        painter.setPen(QPen(QColor(55, 42, 25, 150), 1))
        painter.drawLine(int(x1), int(y), int(x2), int(y))

    def clean_title(self, title):
        text = str(title or "").strip()

        if not text:
            return "Story unavailable"

        return text
