"""MORNINGUI_CEC_DPAD_NAVIGATION_V9

LG TV remote navigation with explicit dashboard transitions and isolated
newspaper, boxscore and weather radar popups. Does not change the application's visual layout or styles.
The selected WeatherRow is painted by WeatherRow.paintEvent (4K cleanup V1).
"""
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QAbstractButton, QAbstractSpinBox, QLineEdit,
    QPlainTextEdit, QTextEdit, QWidget, QGraphicsColorizeEffect,
)


@dataclass
class NavTarget:
    owner: QWidget
    rect: QRect
    label: str
    identity: tuple
    kind: str
    action: object
    local_point: QPointF = None

    @property
    def center(self):
        return self.rect.center()


class SelectionOutline(QWidget):
    """Button/game focus only. Weather borders are painted by WeatherRow."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.rounding = 5.0
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 225, 46, 255), 2.3))
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(2.0, 2.0, -2.0, -2.0),
            self.rounding, self.rounding
        )
        painter.end()


class RemoteNavigation(QObject):
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.outline = SelectionOutline(root)
        self.selected_identity = None
        self.last_point = None
        self.highlighted_label = None
        self.highlighted_weather_row = None
        self.highlighted_sports_panel = None
        # MORNINGUI_FOCUS_YELLOW_V13
        self.highlighted_sports_games_panel = None
        self.highlighted_popup_button = None
        self.popup_button_original_style = None
        self.restore_request = None
        self.restore_attempts = 0
        self.show_request = None
        self.show_attempts = 0
        self.popup_return_identity = None
        self.popup_return_point = None
        self.popup_focus_dialog = None

        app = QApplication.instance()
        if app is None:
            raise RuntimeError('QApplication required before remote navigation')
        app.installEventFilter(self)

        # Keep the V3 Hide-to-restore behavior. Connected after the app slots.
        for panel_attr, kind in (('reminders', 'reminders'),
                                 ('stocks_panel', 'market')):
            panel = getattr(root, panel_attr, None)
            button = getattr(panel, 'hide_button', None)
            if isinstance(button, QAbstractButton):
                button.clicked.connect(
                    lambda _checked=False, k=kind: self._after_hide(k)
                )
        # The replacement-news header buttons emit these signals after
        # DashboardWindow's connected show_* handler has switched the stack.
        # Listening to the signals also covers mouse clicks, not just OK.
        for card_attr, signal_name, kind in (
            ('more_news_card', 'reminders_requested', 'reminders'),
            ('market_news_card', 'market_tape_requested', 'market'),
        ):
            card = getattr(root, card_attr, None)
            signal = getattr(card, signal_name, None)
            if signal is not None:
                signal.connect(lambda k=kind: self._after_show(k))
        print('LG D-pad V9: persistent directional edge focus.',
              flush=True)
        # MORNINGUI_STARTUP_CURRENT_WEATHER_V11
        self._initial_weather_retries_v11 = 0
        QTimer.singleShot(0, self._focus_initial_current_weather_v11)

    def _focus_initial_current_weather_v11(self):
        # Select the current-hour weather card automatically at startup.
        # Do not override an existing selection or an open popup.
        if self.selected_identity is not None or self.last_point is not None:
            return
        if self._article_popup() is not None:
            return

        current = self._by_identity(
            self._dashboard_targets(), ('date', 'current')
        )

        if current is not None:
            self._show(current)
            return

        # Retry briefly if the dashboard is still becoming visible.
        self._initial_weather_retries_v11 += 1
        if self._initial_weather_retries_v11 < 30:
            QTimer.singleShot(100, self._focus_initial_current_weather_v11)

    def _article_popup(self):
        # Newspaper and all three Game Times boxscore formats are QWidget
        # child dialogs. Only one popup is active at a time.
        popup_classes = ('OpenNewspaperDialog', 'ESPNBoxScoreDialog',
                         'MLBBoxScoreDialog', 'WeatherRadarDialog')
        dialogs = [w for w in self.root.findChildren(QWidget)
                   if type(w).__name__ in popup_classes and w.isVisible()]
        return dialogs[-1] if dialogs else None

    @staticmethod
    def _is_boxscore(dialog):
        return (dialog is not None and type(dialog).__name__ in
                ('MLBBoxScoreDialog', 'ESPNBoxScoreDialog'))

    @staticmethod
    def _is_radar(dialog):
        return dialog is not None and type(dialog).__name__ == 'WeatherRadarDialog'

    def _valid(self, widget):
        return (isinstance(widget, QWidget)
                and widget is not self.outline
                and widget.isVisible() and widget.isEnabled()
                and (widget is self.root or self.root.isAncestorOf(widget)))

    def _target(self, owner, local_rect, label, identity, kind,
                action=None, local_point=None):
        if not self._valid(owner):
            return None
        rect = QRectF(local_rect)
        if rect.width() < 3 or rect.height() < 3:
            return None
        root_origin = owner.mapTo(self.root, QPoint(0, 0))
        root_rect = rect.translated(root_origin.x(), root_origin.y()).toAlignedRect()
        root_rect = root_rect.intersected(self.root.rect())
        if root_rect.width() < 4 or root_rect.height() < 4:
            return None
        return NavTarget(owner, root_rect, label, identity, kind, action,
                         local_point if local_point is not None else rect.center())

    def _popup_targets(self, dialog):
        # Exclusive whitelist. Neither the newspaper body nor any controls
        # belonging to the underlying dashboard can enter this collection.
        targets = []
        if self._is_boxscore(dialog):
            # MLB stores close_button; ESPN creates a local close_button.
            button = getattr(dialog, 'close_button', None)
            if not isinstance(button, QAbstractButton):
                button = dialog.findChild(QAbstractButton,
                    'ESPNBoxScoreCloseButton')
            if isinstance(button, QAbstractButton):
                target = self._target(button, button.rect(),
                    'Boxscore CLOSE', ('popup', id(dialog), 'close'),
                    'button', action=button.click)
                if target:
                    targets.append(target)
            return targets
        if self._is_radar(dialog):
            # The radar has zoom controls, but remote navigation is restricted
            # to exactly the four requested transport controls. The CLOSE
            # button is a local variable in the real dialog, not an attribute.
            for key, attr in (('prev', 'previous_button'),
                              ('pause', 'play_button'),
                              ('next', 'next_button'),
                              ('close', 'close_button')):
                button = getattr(dialog, attr, None)
                if key == 'close' and not isinstance(button, QAbstractButton):
                    button = dialog.findChild(QAbstractButton, 'RadarCloseButton')
                if not isinstance(button, QAbstractButton):
                    continue
                target = self._target(
                    button, button.rect(), 'Radar ' + key,
                    ('popup', id(dialog), key), 'button', action=button.click,
                )
                if target:
                    targets.append(target)
            return targets
        for key, attr in (('top', 'back_to_top_button'),
                          ('prev', 'prev_button'),
                          ('close', 'close_button'),
                          ('next', 'next_button')):
            button = getattr(dialog, attr, None)
            if not isinstance(button, QAbstractButton):
                continue
            target = self._target(
                button, button.rect(), 'Newspaper ' + key,
                ('popup', id(dialog), key), 'button', action=button.click,
            )
            if target:
                targets.append(target)
        return targets

    def _dashboard_targets(self):
        targets = []
        # The large date/time/current-weather surface sits ABOVE the first
        # hourly WeatherRow. It is its own clickable card, not hour zero.
        date_card = getattr(self.root, 'date_card', None)
        if self._valid(date_card):
            t = self._target(
                date_card, date_card.rect(), 'Current weather / date / time',
                ('date', 'current'), 'date',
                action=getattr(self.root, 'open_current_weather_radar_popup', None),
            )
            if t:
                targets.append(t)

        # Exactly one selectable text label per main news card.
        for attr in ('fox_card', 'cnbc_card'):
            card = getattr(self.root, attr, None)
            if not self._valid(card):
                continue
            label = getattr(card, 'headline_label', None)
            if (self._valid(label) and str(getattr(card, 'article_url', '') or '')
                    and str(label.text() or '').strip()):
                t = self._target(
                    label, label.rect(), 'Primary headline ' + attr,
                    ('primary', attr), 'text',
                    action=lambda c=card: c.open_article_popup(),
                )
                if t:
                    targets.append(t)

        # Up to five actual secondary headline labels per replacement card.
        for attr in ('more_news_card', 'market_news_card'):
            card = getattr(self.root, attr, None)
            if not self._valid(card):
                continue
            urls = getattr(card, 'page2_widget_urls', {})
            heads = getattr(card, 'page2_widget_headlines', {})
            if not isinstance(urls, dict):
                continue
            count = 0
            for widget, url in list(urls.items()):
                if (not self._valid(widget)
                        or widget.objectName() != 'Page2HeadlineText'
                        or not str(url or '').strip()):
                    continue
                headline = str(heads.get(widget, '') or widget.text()).strip()
                if not headline or headline == 'Additional headline unavailable.':
                    continue
                t = self._target(
                    widget, widget.rect(), 'Secondary headline ' + headline[:48],
                    ('secondary', attr, id(widget)), 'text',
                    action=lambda c=card, u=str(url), h=headline:
                    c.open_article_popup(u, h),
                )
                if t:
                    targets.append(t)
                    count += 1
                if count >= 5:
                    break

        # Every WeatherRow is its own target, retaining the integrated rounded
        # selection paint from the previously successful render cleanup.
        weather = getattr(self.root, 'weather_panel', None)
        if self._valid(weather):
            for row in getattr(weather, 'row_widgets', []):
                if self._valid(row) and hasattr(row, 'clicked'):
                    t = self._target(
                        row, row.rect(), 'Hourly weather ' + str(getattr(row, 'hour', '')),
                        ('weather', id(row)), 'weather',
                        action=lambda r=row: r.clicked.emit(),
                    )
                    if t:
                        targets.append(t)

        # Existing Qt-painted ESPN and Game Times click rectangles.
        for attr, field in (('sports_news', 'click_zones'),
                            ('sports_games', 'clickable_rows')):
            panel = getattr(self.root, attr, None)
            if not self._valid(panel):
                continue
            for index, entry in enumerate(getattr(panel, field, [])):
                if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                    continue
                if not entry[1]:
                    continue
                if (field == 'clickable_rows'
                        and not entry[1].get('is_clickable', False)):
                    continue
                try:
                    rect = QRectF(entry[0])
                except (TypeError, ValueError):
                    continue
                t = self._target(
                    panel, rect, attr + ' ' + str(index + 1),
                    ('painted', attr, index),
                    'sports_text' if attr == 'sports_news' else 'button',
                    action=None,
                )
                if t:
                    targets.append(t)

        for button in self.root.findChildren(QAbstractButton):
            if not self._valid(button):
                continue
            # OpenNewspaperDialog buttons never appear in dashboard scope.
            ancestor = button.parentWidget()
            in_article = False
            while ancestor is not None:
                if type(ancestor).__name__ in (
                    'OpenNewspaperDialog', 'MLBBoxScoreDialog',
                    'ESPNBoxScoreDialog', 'WeatherRadarDialog'):
                    in_article = True
                    break
                ancestor = ancestor.parentWidget()
            if in_article:
                continue
            t = self._target(
                button, button.rect(), button.objectName() or button.text(),
                ('button', id(button)), 'button', action=button.click,
            )
            if t:
                targets.append(t)
        return targets

    def _targets(self):
        dialog = self._article_popup()
        return self._popup_targets(dialog) if dialog else self._dashboard_targets()

    def _remove_highlights(self):
        if self.highlighted_label is not None:
            try:
                self.highlighted_label.setGraphicsEffect(None)
            except RuntimeError:
                pass
        self.highlighted_label = None
        if self.highlighted_weather_row is not None:
            try:
                self.highlighted_weather_row._morningui_remote_selected = False
                self.highlighted_weather_row.update()
            except RuntimeError:
                pass
        self.highlighted_weather_row = None
        if self.highlighted_sports_panel is not None:
            try:
                self.highlighted_sports_panel._morningui_remote_sports_index = -1
                self.highlighted_sports_panel.update()
            except RuntimeError:
                pass
        self.highlighted_sports_panel = None
        if self.highlighted_sports_games_panel is not None:
            try:
                self.highlighted_sports_games_panel._morningui_remote_games_index = -1
                self.highlighted_sports_games_panel.update()
            except RuntimeError:
                pass
        self.highlighted_sports_games_panel = None
        if self.highlighted_popup_button is not None:
            try:
                self.highlighted_popup_button.setStyleSheet(
                    self.popup_button_original_style or '')
            except RuntimeError:
                pass
        self.highlighted_popup_button = None
        self.popup_button_original_style = None

    def _show(self, target):
        self._remove_highlights()
        self.selected_identity = target.identity
        self.last_point = target.center
        if target.kind == 'weather':
            self.outline.hide()
            self.highlighted_weather_row = target.owner
            target.owner._morningui_remote_selected = True
            target.owner.update()
        elif target.kind == 'sports_text':
            # The ESPN panel draws the actual letters in the selected color.
            # No rectangle/overlay is painted around any headline.
            self.outline.hide()
            self.highlighted_sports_panel = target.owner
            # Painted click-zone indices can shift when a story has no URL.
            # Resolve the actual story's position so its LETTERS, not a
            # different headline, receive the existing orange focus color.
            visual_index = target.identity[2]
            articles = getattr(target.owner, 'articles', None)
            zones = getattr(target.owner, 'click_zones', ())
            if (isinstance(articles, (list, tuple)) and articles
                    and visual_index < len(zones)):
                link = str(zones[visual_index][1] or '').strip()
                matched = next((i for i, article in enumerate(articles[:5])
                                if link and str(getattr(article, 'link', '') or '').strip() == link),
                               None)
                if matched is not None:
                    visual_index = matched
                elif not str(getattr(articles[0], 'link', '') or '').strip():
                    # No clickable lead: painted zone zero is secondary one.
                    # Retain a visible highlight even if source URLs differ.
                    visual_index = min(visual_index + 1, len(articles) - 1)
            target.owner._morningui_remote_sports_index = visual_index
            target.owner.update()
        elif target.kind == 'text':
            self.outline.hide()
            self.highlighted_label = target.owner
            effect = QGraphicsColorizeEffect(target.owner)
            effect.setColor(QColor('#705C00'))
            effect.setStrength(1.0)
            target.owner.setGraphicsEffect(effect)
        elif target.identity[:2] == ('painted', 'sports_games'):
            self.outline.hide()
            self.highlighted_sports_games_panel = target.owner
            target.owner._morningui_remote_games_index = target.identity[2]
            target.owner.update()

        elif target.identity[0] == 'popup' and isinstance(target.owner, QAbstractButton):
            self.outline.hide()
            button = target.owner
            self.highlighted_popup_button = button
            self.popup_button_original_style = button.styleSheet()
            radius = 7 if button.objectName() == 'PageTurnButton' else 5
            button.setStyleSheet(self.popup_button_original_style +
                '\nQPushButton#' + button.objectName() + ' {' +
                ' color: #A27C00; border: 3px solid #FFE12E; ' +
                f'border-radius: {radius}px; }}')

        else:
            # The DateCard itself has 20px rounded corners. All other button
            # outlines keep their established five-pixel corner radius.
            self.outline.rounding = 20.0 if target.kind == 'date' else 5.0
            self.outline.setGeometry(target.rect.adjusted(-1, -1, 1, 1))
            self.outline.raise_()
            self.outline.show()
            self.outline.update()
        print('LG focus:', target.label, flush=True)

    def _clear(self):
        self._remove_highlights()
        self.outline.hide()
        self.selected_identity = None
        self.last_point = None

    def _current(self, targets):
        for t in targets:
            if self.selected_identity == t.identity:
                return t
        if self.last_point is not None and targets:
            return min(targets, key=lambda t:
                       (t.center.x() - self.last_point.x()) ** 2 +
                       (t.center.y() - self.last_point.y()) ** 2)
        return None

    @staticmethod
    def _near_y(targets, y):
        return min(targets, key=lambda t: (abs(t.center.y() - y), t.center.x())) if targets else None

    @staticmethod
    def _by_identity(targets, identity):
        return next((t for t in targets if t.identity == identity), None)

    @staticmethod
    def _in_panel(target, panel):
        return (isinstance(panel, QWidget) and
                (target.owner is panel or panel.isAncestorOf(target.owner)))

    def _sports_story_targets(self, espn):
        """Identify the ESPN lead by its actual source link, not zone index.

        When the main story has no link, the first painted click zone is a
        secondary headline with index zero. That must NOT become the lead.
        """
        if not espn:
            return None, []
        panel = getattr(self.root, 'sports_news', None)
        articles = getattr(panel, 'articles', None)
        lead = None
        if isinstance(articles, (list, tuple)):
            if articles:
                lead_link = str(getattr(articles[0], 'link', '') or '').strip()
                zones = getattr(panel, 'click_zones', [])
                if lead_link:
                    for t in espn:
                        idx = t.identity[2]
                        if idx < len(zones) and str(zones[idx][1] or '').strip() == lead_link:
                            lead = t
                            break
        else:
            # Compatibility with the lightweight offscreen SportsArea fixture.
            # The real SportsNewsPanel always defines the articles list.
            lead = next((t for t in espn if t.identity[2] == 0), None)
        return lead, [t for t in espn if lead is None or t.identity != lead.identity]

    def _top_edge_locked(self, current, direction, targets):
        """Up at the highest clickable weather, ESPN or Game Times row stays put."""
        if direction != Qt.Key.Key_Up:
            return False
        if current.identity == ('date', 'current'):
            return True
        espn = [t for t in targets
                if t.identity[:2] == ('painted', 'sports_news')]
        if current.identity[:2] == ('painted', 'sports_news'):
            lead, secondary = self._sports_story_targets(espn)
            if lead is not None:
                return current.identity == lead.identity
            # An unclickable lead makes ALL secondary headlines the highest
            # eligible focus level, even when their painted Y values differ.
            return any(t.identity == current.identity for t in secondary)
        if current.identity[:2] == ('painted', 'sports_games'):
            games = [t for t in targets
                     if t.identity[:2] == ('painted', 'sports_games')]
            if games:
                highest = min(t.rect.top() for t in games)
                return current.rect.top() <= highest + 3
        return False

    def _horizontal_edge_locked(self, current, direction, targets):
        """Stop Left/Right at the real dashboard columns' outer edges.

        Avoid spatial jumps to unrelated rows just because another widget's
        horizontal center differs slightly. Keep within-panel traversal when
        another clickable game/control genuinely lies farther in direction.
        """
        if direction == Qt.Key.Key_Left:
            return (current.identity == ('date', 'current')
                    or current.identity[0] == 'weather'
                    or current.owner is getattr(self.root, 'settings_button', None)
                    or self._in_panel(current, getattr(self.root, 'weather_panel', None)))
        if direction != Qt.Key.Key_Right:
            return False
        if current.identity[:2] == ('painted', 'sports_games'):
            games = [t for t in targets
                     if t.identity[:2] == ('painted', 'sports_games')]
            return not any(t.center.x() > current.center.x() + 3 for t in games)
        for attr in ('cnbc_card', 'market_news_card', 'stocks_panel'):
            panel = getattr(self.root, attr, None)
            if self._in_panel(current, panel):
                return not any(self._in_panel(t, panel)
                               and t.identity != current.identity
                               and t.center.x() > current.center.x() + 3
                               for t in targets)
        return False

    def _special_dashboard_move(self, current, direction, targets):
        weather = sorted(
            [t for t in targets if t.identity[0] == 'weather'],
            key=lambda t: t.center.y(),
        )
        gear_button = getattr(self.root, 'settings_button', None)
        gear = next((t for t in targets if t.owner is gear_button), None)
        left_primary = self._by_identity(targets, ('primary', 'fox_card'))
        right_primary = self._by_identity(targets, ('primary', 'cnbc_card'))
        date_current = self._by_identity(targets, ('date', 'current'))
        espn = [t for t in targets if t.identity[:2] == ('painted', 'sports_news')]
        games = [t for t in targets if t.identity[:2] == ('painted', 'sports_games')]
        # Game Times LEFT: move to the nearest boxscore strictly to the
        # left (across league columns). Never jump to a different widget
        # before checking all visible clickable games in the panel.
        if (current.identity[:2] == ('painted', 'sports_games')
                and direction == Qt.Key.Key_Left):
            candidates = [t for t in games if t.identity != current.identity
                          and t.center.x() < current.center.x() - 3]
            if candidates:
                return min(candidates, key=lambda t: (
                    (current.center.x() - t.center.x())
                    + 1.4 * abs(current.center.y() - t.center.y()),
                    abs(current.center.y() - t.center.y()),
                ))
            # No game to the left: prefer the CLICKABLE ESPN lead.
            # If the lead is not clickable, select the visually LAST
            # secondary ESPN headline (rightmost, then bottommost).
            lead, secondary = self._sports_story_targets(espn)
            return lead or (max(secondary, key=lambda t: (
                t.center.x(), t.center.y())) if secondary else current)

        bottom_left_panels = (getattr(self.root, 'reminders', None),
                              getattr(self.root, 'more_news_card', None))
        bottom_left = [t for t in targets if any(
            self._in_panel(t, p) for p in bottom_left_panels)]

        # The date/time card is the starting point of the weather column.
        # DOWN enters the first hourly card; RIGHT enters headline sports.
        if current.identity == ('date', 'current'):
            if direction == Qt.Key.Key_Down and weather:
                return weather[0]
            if direction == Qt.Key.Key_Right:
                lead, _ = self._sports_story_targets(espn)
                return lead or self._near_y(espn, current.center.y()) or left_primary

        if current.identity[0] == 'weather':
            idx = next((i for i, w in enumerate(weather)
                        if w.identity == current.identity), -1)
            if idx >= 0:
                if direction == Qt.Key.Key_Down:
                    if idx + 1 < len(weather):
                        return weather[idx + 1]
                    return gear
                if direction == Qt.Key.Key_Up:
                    if idx > 0:
                        return weather[idx - 1]
                    return date_current
                if direction == Qt.Key.Key_Right:
                    if idx >= max(1, len(weather) - 3):
                        return self._near_y(bottom_left, current.center.y()) or left_primary
                    return left_primary

        if gear is not None and current.identity == gear.identity:
            if direction == Qt.Key.Key_Up and weather:
                return weather[-1]
            if direction == Qt.Key.Key_Right:
                return self._near_y(bottom_left, current.center.y()) or left_primary

        # LEFT from the main ESPN story returns to the large current-hour
        # DateCard, not the first (smaller) hourly WeatherRow.
        if current.identity[:2] == ('painted', 'sports_news'):
            lead, _ = self._sports_story_targets(espn)
            if (direction == Qt.Key.Key_Left and lead is not None
                    and current.identity == lead.identity):
                return date_current

        # Header controls of BOTH secondary-news panels must go to the
        # respective PRIMARY headline immediately above, never straight to
        # sports. This also works when the ordinary panels are restored.
        reminder_hide = getattr(getattr(self.root, 'reminders', None),
                                'hide_button', None)
        reminder_restore = getattr(getattr(self.root, 'more_news_card', None),
                                   'reminders_button', None)
        market_hide = getattr(getattr(self.root, 'stocks_panel', None),
                              'hide_button', None)
        market_restore = getattr(getattr(self.root, 'market_news_card', None),
                                 'market_tape_button', None)
        if direction == Qt.Key.Key_Up:
            if current.owner in (reminder_hide, reminder_restore):
                return left_primary
            if current.owner in (market_hide, market_restore):
                return right_primary

        if current.identity[:2] == ('painted', 'sports_news'):
            lead, secondary = self._sports_story_targets(espn)
            # MORNINGUI_SPORTS_LEAD_DOWN_LEFTMOST_SECONDARY_V12
            if (lead is not None and current.identity == lead.identity
                    and direction == Qt.Key.Key_Down):
                return (min(secondary, key=lambda t: (t.rect.left(), t.rect.top()))
                        if secondary else current)
            is_secondary = lead is None or current.identity != lead.identity
            if is_secondary and direction == Qt.Key.Key_Down:
                return left_primary
            if is_secondary and lead is None and direction == Qt.Key.Key_Up:
                # Secondary stories are the TOP of Sports News when the
                # headline has no valid link; never leave the selection.
                return current
            if secondary and direction == Qt.Key.Key_Right:
                rightmost = max(secondary, key=lambda t: t.center.x())
                if current.identity == rightmost.identity:
                    return self._near_y(games, current.center.y()) or right_primary

        # MORNINGUI_PRIMARY_NEWS_LEFT_TO_FIRST_HOURLY_V10
        # LEFT from the primary news headline goes to the first hourly weather card.
        if (current.identity == ('primary', 'fox_card')
                and direction == Qt.Key.Key_Left):
            return weather[0] if weather else current

        if (current.identity == ('primary', 'fox_card')
                and direction == Qt.Key.Key_Down):
            reminders = getattr(self.root, 'reminders', None)
            hide = getattr(reminders, 'hide_button', None)
            if self._valid(reminders) and self._valid(hide):
                match = next((t for t in targets if t.owner is hide), None)
                if match:
                    return match

        if (current.identity == ('primary', 'fox_card')
                and direction == Qt.Key.Key_Right):
            return right_primary
        if (current.identity == ('primary', 'cnbc_card')
                and direction == Qt.Key.Key_Left):
            return left_primary
        return None

    def _bottom_edge_locked(self, current, direction, targets):
        """Only the explicitly named lower edges stop DOWN navigation."""
        if direction != Qt.Key.Key_Down:
            return False
        if current.owner is getattr(self.root, 'settings_button', None):
            return True
        market = getattr(self.root, 'stocks_panel', None)
        if current.owner is getattr(market, 'hide_button', None):
            return True
        if current.identity[0] == 'secondary':
            card = current.identity[1]
            if card in ('more_news_card', 'market_news_card'):
                peers = [t for t in targets
                         if t.identity[:2] == ('secondary', card)]
                if peers:
                    last = max(peers, key=lambda t: (t.center.y(), t.center.x()))
                    return current.identity == last.identity
        reminders = getattr(self.root, 'reminders', None)
        if (self._in_panel(current, reminders)
                and current.owner.objectName() in
                ('ReminderSendButton', 'UpcomingReminderSendButton')):
            peers = [t for t in targets
                     if self._in_panel(t, reminders)
                     and t.owner.objectName() in
                     ('ReminderSendButton', 'UpcomingReminderSendButton')]
            if peers:
                last = max(peers, key=lambda t: (t.center.y(), t.center.x()))
                return current.identity == last.identity
        return False

    def _spatial_move(self, current, direction, targets):
        cx, cy = current.center.x(), current.center.y()
        choices = []
        for t in targets:
            if t.identity == current.identity:
                continue
            dx = t.center.x() - cx
            dy = t.center.y() - cy
            if direction == Qt.Key.Key_Right:
                along, cross = dx, abs(dy)
            elif direction == Qt.Key.Key_Left:
                along, cross = -dx, abs(dy)
            elif direction == Qt.Key.Key_Down:
                along, cross = dy, abs(dx)
            else:
                along, cross = -dy, abs(dx)
            if along > 3:
                choices.append((along + cross * 1.4, cross, t))
        return min(choices, key=lambda pair: pair[:2])[2] if choices else None

    def _popup_move(self, direction, targets):
        if not targets:
            self._clear()
            return
        current = self._by_identity(targets, self.selected_identity)
        if current is None:
            dialog = self._article_popup()
            key = 'pause' if self._is_radar(dialog) else 'next'
            preferred = self._by_identity(targets, ('popup', id(dialog), key))
            self._show(preferred or self._by_identity(
                targets, ('popup', id(dialog), 'close')) or targets[0])
            return
        if len(targets) == 1:
            return
        # Button arrangement follows the visual newspaper controls: BACK TO
        # TOP / BACK PAGE / CLOSE / TURN PAGE. D-pad never escapes this list.
        ordered = sorted(targets, key=lambda t: (t.center.x(), t.center.y()))
        i = next(i for i, t in enumerate(ordered) if t.identity == current.identity)
        if direction in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            j = min(len(ordered) - 1, i + 1)
        else:
            j = max(0, i - 1)
        if j != i:
            self._show(ordered[j])

    def move(self, direction):
        targets = self._targets()
        if not targets:
            self._clear()
            return
        if self._article_popup() is not None:
            self._popup_move(direction, targets)
            return
        current = self._current(targets)
        if current is None:
            if direction == Qt.Key.Key_Left:
                first = min(targets, key=lambda t: (t.center.x(), t.center.y()))
            elif direction == Qt.Key.Key_Down:
                first = min(targets, key=lambda t: (t.center.y(), t.center.x()))
            elif direction == Qt.Key.Key_Up:
                first = max(targets, key=lambda t: (t.center.y(), -t.center.x()))
            else:
                first = max(targets, key=lambda t: (t.center.x(), -t.center.y()))
            self._show(first)
            return
        # Do not move beyond the TOP of weather, Sports News or Game Times.
        # This runs before generic spatial navigation can escape the column.
        if self._top_edge_locked(current, direction, targets):
            self._show(current)  # refresh existing highlight; focus does not move
            return
        if self._horizontal_edge_locked(current, direction, targets):
            self._show(current)  # no wraparound or unrelated spatial fallback
            return
        # Never jump past the specific last-row controls listed by the user.
        if self._bottom_edge_locked(current, direction, targets):
            return
        # Explicit routes have precedence over spatial nearest-neighbor.
        destination = self._special_dashboard_move(current, direction, targets)
        if destination:
            self._show(destination)
            return
        # Keep weather navigation inside its column at its vertical edges.
        weather_targets = sorted(
            (t for t in targets if t.identity[0] == 'weather'),
            key=lambda t: t.center.y(),
        )
        if weather_targets and current.identity[0] == 'weather':
            if (direction == Qt.Key.Key_Up
                    and current.identity == weather_targets[0].identity
                    and self._by_identity(targets, ('date', 'current')) is None):
                return
            if (direction == Qt.Key.Key_Down
                    and current.identity == weather_targets[-1].identity):
                return
        destination = self._spatial_move(current, direction, targets)
        if destination:
            self._show(destination)
        else:
            self._show(current)  # keep the selected article/control highlighted
            print('LG focus: edge reached.', flush=True)

    def _focus_popup(self, dialog, preferred=None):
        if dialog is None or dialog is not self._article_popup():
            return
        targets = self._popup_targets(dialog)
        if not targets:
            return
        if self._is_boxscore(dialog):
            preferred = 'close'
        elif self._is_radar(dialog):
            preferred = preferred or 'pause'
        elif preferred is None:
            preferred = 'next' if getattr(dialog, 'spread_index', 0) == 0 else 'prev'
        target = self._by_identity(targets, ('popup', id(dialog), preferred))
        if target is None:
            for alternative in ('next', 'prev', 'close', 'top'):
                target = self._by_identity(targets, ('popup', id(dialog), alternative))
                if target:
                    break
        if target:
            self._show(target)

    def _restore_dashboard_focus(self):
        if self._article_popup() is not None:
            return
        # Hide-event and explicit Back/Close both request restoration.
        # The SECOND callback must not clear the focus restored by the first.
        if (self.popup_focus_dialog is None
                and self.popup_return_identity is None
                and self.popup_return_point is None):
            return
        original = self.popup_return_identity
        point = self.popup_return_point
        self.popup_focus_dialog = None
        self.popup_return_identity = None
        self.popup_return_point = None
        self._clear()
        targets = self._dashboard_targets()
        target = self._by_identity(targets, original)
        if target is None and point is not None and targets:
            target = min(targets, key=lambda t:
                         (t.center.x() - point.x()) ** 2 +
                         (t.center.y() - point.y()) ** 2)
        if target:
            self._show(target)

    def _close_popup(self, dialog):
        dialog.close()
        QTimer.singleShot(30, self._restore_dashboard_focus)

    def _after_popup_button(self, dialog, key):
        if self._article_popup() is not dialog:
            QTimer.singleShot(30, self._restore_dashboard_focus)
            return
        if self._is_radar(dialog):
            # Pause/Play, previous and next each keep their own focus.
            self._focus_popup(dialog, key)
            return
        if key == 'next':
            # Preserve TURN PAGE after each turn, until the final page.
            preferred = 'next'
        elif key == 'prev':
            preferred = 'prev'
        elif key == 'top':
            preferred = 'next'
        else:
            preferred = 'close'
        self._focus_popup(dialog, preferred)

    def activate(self):
        targets = self._targets()
        if not targets:
            self._clear()
            return
        target = self._by_identity(targets, self.selected_identity)
        if target is None:
            if self._article_popup():
                self._focus_popup(self._article_popup())
            else:
                self._show(min(targets, key=lambda t: (t.center.y(), t.center.x())))
            return
        dialog = self._article_popup()
        if dialog is not None:
            key = target.identity[2]
            if key == 'close':
                self._close_popup(dialog)
                return
            if target.action:
                target.action()
            QTimer.singleShot(0, lambda d=dialog, k=key:
                              self._after_popup_button(d, k))
            return

        if (target.identity[0] in ('primary', 'secondary', 'weather')
                or target.identity == ('date', 'current')
                or target.identity[:2] in
                (('painted', 'sports_news'), ('painted', 'sports_games'))):
            self.popup_return_identity = target.identity
            self.popup_return_point = target.center
        self.restore_request = None
        self._clear()
        if target.action is not None:
            target.action()
            return
        # Existing ESPN/Game Times hit-test logic; do not reimplement it.
        owner, point = target.owner, target.local_point
        glob = owner.mapToGlobal(point.toPoint())
        for event_type, state in (
            (QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton),
            (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton),
        ):
            event = QMouseEvent(
                event_type, point, QPointF(glob),
                Qt.MouseButton.LeftButton, state,
                Qt.KeyboardModifier.NoModifier,
            )
            QApplication.sendEvent(owner, event)

    def _after_hide(self, kind):
        self._clear()
        self.restore_request = kind
        self.restore_attempts = 0
        QTimer.singleShot(60, self._focus_restore)

    def _focus_restore(self):
        kind = self.restore_request
        if kind is None or self._article_popup() is not None:
            return
        card_attr, button_attr, hidden_attr = (
            ('more_news_card', 'reminders_button', 'session_reminders_hidden')
            if kind == 'reminders' else
            ('market_news_card', 'market_tape_button', 'session_market_tape_hidden')
        )
        card = getattr(self.root, card_attr, None)
        button = getattr(card, button_attr, None) if card is not None else None
        if (self._valid(card) and isinstance(button, QAbstractButton)
                and bool(getattr(self.root, hidden_attr, False))):
            if not button.isVisible():
                if hasattr(card, 'edition_label'):
                    card.edition_label.hide()
                button.show()
            matches = [t for t in self._targets() if t.owner is button]
            if matches:
                if self.selected_identity != matches[0].identity:
                    self._show(matches[0])
                # One-shot completion: do not steal focus repeatedly while
                # the user navigates away from the restored button.
                self.restore_request = None
                return
        self.restore_attempts += 1
        if self.restore_attempts < 45:
            QTimer.singleShot(150, self._focus_restore)
        else:
            self.restore_request = None

    def _after_show(self, kind):
        # Restore-button signals are delivered AFTER the dashboard switches
        # the stack. Defer one event loop so visibility has settled.
        self.restore_request = None
        self.show_request = kind
        self.show_attempts = 0
        self._clear()
        QTimer.singleShot(0, self._focus_shown_hide)

    def _focus_shown_hide(self):
        kind = self.show_request
        if kind not in ('reminders', 'market') or self._article_popup() is not None:
            return
        panel_attr = 'reminders' if kind == 'reminders' else 'stocks_panel'
        panel = getattr(self.root, panel_attr, None)
        button = getattr(panel, 'hide_button', None)
        if (self._valid(panel) and isinstance(button, QAbstractButton)
                and self._valid(button)):
            target = next((t for t in self._dashboard_targets()
                           if t.owner is button), None)
            if target is not None:
                self._show(target)
                self.show_request = None
                return
        self.show_attempts += 1
        if self.show_attempts < 20:
            QTimer.singleShot(75, self._focus_shown_hide)
        else:
            print('LG focus: restored panel Hide button not visible.', flush=True)
            self.show_request = None

    def eventFilter(self, watched, event):
        # Popup lifecycle: focus only popup buttons on Show, restore the
        # underlying article headline on Hide. This also works for the
        # app's normal CLOSE button and not just LG Back.
        if type(watched).__name__ in ('OpenNewspaperDialog', 'MLBBoxScoreDialog',
                                      'ESPNBoxScoreDialog', 'WeatherRadarDialog'):
            if event.type() == QEvent.Type.Show:
                self.popup_focus_dialog = watched
                QTimer.singleShot(0, lambda d=watched: self._focus_popup(d))
            elif event.type() == QEvent.Type.Hide:
                QTimer.singleShot(0, self._restore_dashboard_focus)

        if event.type() not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            return False
        key = event.key()
        managed = {Qt.Key.Key_Up, Qt.Key.Key_Down,
                   Qt.Key.Key_Left, Qt.Key.Key_Right,
                   Qt.Key.Key_Return, Qt.Key.Key_Enter,
                   Qt.Key.Key_Escape}
        if key not in managed:
            return False

        dialog = self._article_popup()
        if dialog is None:
            # Other application dialogs retain their native keyboard behavior.
            if QApplication.activeModalWidget() is not None:
                return False
            active = QApplication.activeWindow()
            if active is not None and active is not self.root:
                return False
            focus = QApplication.focusWidget()
            if isinstance(focus, (QLineEdit, QAbstractSpinBox,
                                  QTextEdit, QPlainTextEdit)):
                return False
        if event.type() == QEvent.Type.KeyRelease:
            return True
        if event.isAutoRepeat():
            return True
        if key == Qt.Key.Key_Escape:
            self.restore_request = None
            self.show_request = None
            if dialog is not None:
                self._close_popup(dialog)
            else:
                self._clear()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.activate()
        else:
            self.restore_request = None
            self.show_request = None
            self.move(key)
        return True


def install_remote_navigation(window):
    return RemoteNavigation(window)

# MORNINGUI_BOXSCORE_REMOTE_SCROLL_V2
# Isolated keyboard focus/scroll handling for MLB, NBA and NFL boxscore popups.
# Other dialog types, game fetching and dashboard navigation are unchanged.
from PySide6.QtCore import QPoint as _BSP, Qt as _BST, QEvent as _BSE
from PySide6.QtGui import QColor as _BSC, QPainter as _BSPainter, QPen as _BSPen
from PySide6.QtWidgets import (QWidget as _BSWidget, QTextEdit as _BSText,
                               QScrollBar as _BSScrollBar, QApplication as _BSApp)


class _MorningUIBoxscoreFocusFrame(_BSWidget):
    """Non-interactive outline inside the popup, never overlaid on team stats."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(_BST.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(_BST.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(_BST.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(_BST.FocusPolicy.NoFocus)
        self.scrolling = False

    def paintEvent(self, event):
        painter = _BSPainter(self)
        painter.setRenderHint(_BSPainter.RenderHint.Antialiasing, True)
        painter.setBrush(_BST.BrushStyle.NoBrush)
        color = _BSC('#FFD600') if self.scrolling else _BSC('#FFE12E')
        painter.setPen(_BSPen(color, 4.0 if self.scrolling else 2.6))
        painter.drawRoundedRect(self.rect().adjusted(3, 3, -4, -4), 4, 4)
        painter.end()


_bs_original_targets = RemoteNavigation._popup_targets
_bs_original_show = RemoteNavigation._show
_bs_original_filter = RemoteNavigation.eventFilter


def _bs_targets(self, dialog):
    targets = _bs_original_targets(self, dialog)
    if not self._is_boxscore(dialog):
        return targets
    for side in ('left', 'right'):
        page = getattr(dialog, side + '_page', None)
        if not isinstance(page, _BSWidget):
            continue
        t = self._target(
            page, page.rect(), side.title() + ' team boxscore',
            ('popup', id(dialog), side), 'boxscore_team',
        )
        if t is not None:
            targets.append(t)
    return targets


def _bs_hide_frame(self):
    frame = getattr(self, '_bs_frame', None)
    if frame is not None:
        try:
            if frame.isVisible():
                frame.hide()
        except RuntimeError:
            pass


def _bs_show(self, target):
    if target.kind != 'boxscore_team':
        _bs_hide_frame(self)
    _bs_original_show(self, target)
    if target.kind != 'boxscore_team':
        return
    dialog = self._article_popup()
    if not self._is_boxscore(dialog):
        return
    side = target.identity[2]
    page = getattr(dialog, side + '_page', None)
    if page is None:
        return
    # The root overlay sits behind a raised newspaper dialog. Use a separate
    # transparent child of the dialog so the selected page stays visible.
    self.outline.hide()
    frame = getattr(self, '_bs_frame', None)
    if frame is None or getattr(self, '_bs_frame_dialog', None) is not dialog:
        frame = _MorningUIBoxscoreFocusFrame(dialog)
        self._bs_frame = frame
        self._bs_frame_dialog = dialog
    frame.setGeometry(page.mapTo(dialog, _BSP(0, 0)).x(),
                      page.mapTo(dialog, _BSP(0, 0)).y(),
                      page.width(), page.height())
    frame.scrolling = (getattr(self, '_bs_scroll_side', None) == side)
    frame.raise_()
    frame.show()
    frame.update()


def _bs_scrollbar(body):
    """Find the actual vertical QScrollBar on ESPN/MLB QTextEdit bodies."""
    if not isinstance(body, _BSText):
        return None
    bar = body.verticalScrollBar()
    if isinstance(bar, _BSScrollBar):
        return bar
    # Some Qt/PySide versions can expose the inherited vertical widget
    # as a generic QWidget. Search by actual QScrollBar class instead.
    bars = body.findChildren(_BSScrollBar)
    for candidate in bars:
        if candidate.orientation() == _BST.Orientation.Vertical:
            return candidate
    return None


def _bs_key_filter(self, watched, event):
    # Never inspect child widgets or call _article_popup() for generic Qt
    # show/hide/paint/destruction events. Doing so caused reentrant calls
    # while Qt tore down the original offscreen fixture.
    etype = event.type()
    if _BSApp.closingDown():
        return False
    if etype not in (_BSE.Type.KeyPress, _BSE.Type.KeyRelease):
        if etype == _BSE.Type.Hide and self._is_boxscore(watched):
            _bs_hide_frame(self)
            self._bs_scroll_side = None
            self._bs_frame = None
            self._bs_frame_dialog = None
            self._bs_dialog_id = None
        return _bs_original_filter(self, watched, event)

    dialog = self._article_popup()
    if not self._is_boxscore(dialog):
        return _bs_original_filter(self, watched, event)
    key = event.key()
    nav = {
        _BST.Key.Key_Up: 'up', _BST.Key.Key_Down: 'down',
        _BST.Key.Key_Left: 'left', _BST.Key.Key_Right: 'right',
        _BST.Key.Key_Return: 'ok', _BST.Key.Key_Enter: 'ok',
        _BST.Key.Key_Escape: 'back', _BST.Key.Key_Backspace: 'back',
    }
    name = nav.get(key)
    if name is None:
        return _bs_original_filter(self, watched, event)
    if event.type() == _BSE.Type.KeyRelease:
        return True

    if getattr(self, '_bs_dialog_id', None) != id(dialog):
        self._bs_dialog_id = id(dialog)
        self._bs_scroll_side = None

    # Autorepeat scrolls normally when held; it never moves focus repeatedly.
    if event.isAutoRepeat() and getattr(self, '_bs_scroll_side', None) is None:
        return True

    targets = self._popup_targets(dialog)
    current = getattr(self, 'selected_identity', None)
    def target(side):
        return self._by_identity(targets, ('popup', id(dialog), side))
    close, left, right = target('close'), target('left'), target('right')
    if close is None or left is None or right is None:
        return _bs_original_filter(self, watched, event)

    scroll_side = getattr(self, '_bs_scroll_side', None)
    if scroll_side in ('left', 'right'):
        if name == 'back':
            self._bs_scroll_side = None
            self._show(target(scroll_side))
            return True
        if name in ('up', 'down'):
            page = getattr(dialog, scroll_side + '_page')
            body = page if isinstance(page, _BSText) else getattr(page, 'body', None)
            if isinstance(body, _BSText):
                bar = _bs_scrollbar(body)
                if bar is not None:
                    step = max(24, int(bar.pageStep() * 0.20))
                    movement = -step if name == 'up' else step
                    bar.setValue(max(bar.minimum(), min(bar.maximum(), bar.value() + movement)))
                else:
                    print('LG boxscore: vertical scrollbar unavailable', flush=True)
            return True
        return True   # left/right/OK cannot exit a team's scroll mode

    if current not in (close.identity, left.identity, right.identity):
        self._show(close)
        current = close.identity
    if name == 'back':
        self._close_popup(dialog)
        return True
    if name == 'ok':
        if current == close.identity:
            self._close_popup(dialog)
        else:
            side = 'left' if current == left.identity else 'right'
            self._bs_scroll_side = side
            self._show(target(side))
            print('LG boxscore scroll:', side, flush=True)
        return True

    destination = None
    if current == close.identity:
        if name == 'up':
            destination = left
    elif current == left.identity:
        if name == 'right':
            destination = right
        elif name == 'down':
            destination = close
    elif current == right.identity:
        if name == 'left':
            destination = left
        elif name == 'down':
            destination = close
    if destination is not None:
        self._show(destination)
    return True


RemoteNavigation._popup_targets = _bs_targets
RemoteNavigation._show = _bs_show
RemoteNavigation.eventFilter = _bs_key_filter

# MORNINGUI_DPAD_ROUTE_CORRECTIONS_V13
# Three precise dashboard-only transitions; popup and other routes are unchanged.
_morningui_v13_previous_special = RemoteNavigation._special_dashboard_move


def _morningui_v13_special_dashboard_move(self, current, direction, targets):
    from PySide6.QtCore import Qt as _NavQt

    if current is None or not targets:
        return _morningui_v13_previous_special(self, current, direction, targets)

    # ESPN's CLICKABLE lead -> first clickable Game Times boxscore;
    # if none is available, use the clickable primary headline in the
    # right-hand news column (not a secondary ESPN story).
    if (direction == _NavQt.Key.Key_Right and
            current.identity[:2] == ('painted', 'sports_news')):
        sports = [t for t in targets
                  if t.identity[:2] == ('painted', 'sports_news')]
        lead, _ = self._sports_story_targets(sports)
        if lead is not None and current.identity == lead.identity:
            games = [t for t in targets
                     if t.identity[:2] == ('painted', 'sports_games')]
            if games:
                # The index is the visible row's position in clickable_rows;
                # select the first actually clickable boxscore.
                return min(games, key=lambda t: (t.identity[2],
                                                 t.center.y(), t.center.x()))
            right_news = self._by_identity(targets, ('primary', 'cnbc_card'))
            return right_news or current

    # Primary LEFT news headline -> far-left clickable secondary ESPN
    # headline, never the ESPN primary lead.
    if (direction == _NavQt.Key.Key_Up and
            current.identity == ('primary', 'fox_card')):
        sports = [t for t in targets
                  if t.identity[:2] == ('painted', 'sports_news')]
        _, secondary = self._sports_story_targets(sports)
        return (min(secondary, key=lambda t: (t.center.x(), t.center.y()))
                if secondary else current)

    # Reminders HIDE and its replacement REMINDERS button -> third from
    # bottom of the clickable hourly-weather list (not Set Reminder).
    if direction == _NavQt.Key.Key_Left:
        reminders = getattr(self.root, 'reminders', None)
        replacement = getattr(self.root, 'more_news_card', None)
        hide = getattr(reminders, 'hide_button', None)
        restore = getattr(replacement, 'reminders_button', None)
        if ((hide is not None and current.owner is hide) or
                (restore is not None and current.owner is restore)):
            hourly = sorted(
                (t for t in targets if t.identity[0] == 'weather'),
                key=lambda t: (t.center.y(), t.center.x()),
            )
            return hourly[-3] if len(hourly) >= 3 else current

    return _morningui_v13_previous_special(self, current, direction, targets)


RemoteNavigation._special_dashboard_move = _morningui_v13_special_dashboard_move

# MORNINGUI_DPAD_RIGHT_NEWS_UP_V14
# Top clickable right-hand secondary-news headline: UP selects the
# right-hand PRIMARY news headline, not the Market Tape control.
# No other dashboard routes or popup behaviors are altered.
_morningui_v14_previous_special = RemoteNavigation._special_dashboard_move


def _morningui_v14_special_dashboard_move(self, current, direction, targets):
    if (current is not None and direction == Qt.Key.Key_Up
            and current.identity[:2] == ('secondary', 'market_news_card')):
        # Work from actual clickable targets. If an earlier article is not
        # available, the first remaining clickable headline becomes 'top'.
        secondary = [t for t in targets
                     if t.identity[:2] == ('secondary', 'market_news_card')]
        if secondary:
            first = min(secondary, key=lambda t: (t.center.y(), t.center.x()))
            if current.identity == first.identity:
                primary = self._by_identity(targets, ('primary', 'cnbc_card'))
                return primary or current
    return _morningui_v14_previous_special(self, current, direction, targets)


RemoteNavigation._special_dashboard_move = _morningui_v14_special_dashboard_move
