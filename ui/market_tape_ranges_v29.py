"""Market Tape V29: cached time-window selector, no network calls on clicks."""
from datetime import datetime, timedelta, date
from calendar import monthrange
from zoneinfo import ZoneInfo
from math import isfinite
from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QHBoxLayout, QPushButton

_ET = ZoneInfo("America/New_York")
_WINDOWS = (
    ("YoY", "1 Year Trend", 12),
    ("YTD", "YTD Trend", 12),
    ("6 Mo", "6 Month Trend", 6),
    ("3 Mo", "3 Month Trend", 3),
    ("1 Mo", "1 Month Trend", 4),
    ("7d", "7 Day Trend", 7),
    ("1d", "1 Day Trend", 7),
)
_CAPTIONS = {key: caption for key, caption, n in _WINDOWS}
_MARKS = {key: n for key, caption, n in _WINDOWS}


def _months_before(day, n):
    year = day.year
    month = day.month - n
    while month <= 0:
        year -= 1
        month += 12
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def _window_for_quote(quote, period):
    now = datetime.now(_ET)
    daily = list(getattr(quote, "_mui_daily_v29", []) or [])
    intraday = list(getattr(quote, "_mui_intraday_v29", []) or [])
    current = getattr(quote, "_mui_live_v29", None)
    if period == "1d":
        # Preserve each candle's exchange-local timestamp.
        buckets = {}
        for ts, close, opening in intraday:
            clock = datetime.fromtimestamp(ts, _ET)
            minutes = clock.hour * 60 + clock.minute
            if 570 <= minutes <= 960 and clock.weekday() < 5:
                buckets.setdefault(clock.date(), []).append((ts, close, opening))
        if not buckets:
            return None, None, None, None

        day = max(buckets)
        records = sorted(buckets[day])

        # Only a completed PRIOR session can supply the baseline.
        prior = [
            (ts, close) for ts, close, unused_open in daily
            if datetime.fromtimestamp(ts, _ET).date() < day
            and close is not None and isfinite(close) and close > 0
        ]
        previous_close = max(
            prior, key=lambda row: row[0]
        )[1] if prior else None

        def minute_of(ts):
            t = datetime.fromtimestamp(ts, _ET)
            return t.hour * 60 + t.minute + t.second / 60.0

        values = [point[1] for point in records]
        minutes = [minute_of(point[0]) for point in records]

        first_open = records[0][2]
        if (
            minutes[0] <= 575
            and first_open is not None
            and isfinite(first_open)
            and first_open > 0
        ):
            values.insert(0, first_open)
            minutes.insert(0, 570.0)

        # Use the provider's actual trade time for a fresher quote.
        try:
            live_ts = int(
                getattr(quote, "_mui_live_time_v30", 0) or 0
            )
        except (TypeError, ValueError, OverflowError):
            live_ts = 0

        if (
            current is not None
            and isfinite(current)
            and current > 0
            and live_ts > records[-1][0]
        ):
            trade = datetime.fromtimestamp(live_ts, _ET)
            minute = minute_of(live_ts)
            if (
                trade.date() == day
                and 570 <= minute <= 960
                and live_ts <= now.timestamp() + 120
            ):
                if minute > minutes[-1]:
                    values.append(current)
                    minutes.append(minute)

        pct = (
            100.0 * (values[-1] - previous_close) / previous_close
            if previous_close is not None else None
        )
        return values, pct, previous_close, minutes

    if not daily:
        return None, None, None, None

    today = now.date()
    if period == "YoY":
        start = _months_before(today, 12)
    elif period == "YTD":
        start = date(today.year, 1, 1)
    elif period == "6 Mo":
        start = _months_before(today, 6)
    elif period == "3 Mo":
        start = _months_before(today, 3)
    elif period == "1 Mo":
        start = _months_before(today, 1)
    elif period == "7d":
        start = today - timedelta(days=7)
    else:
        return None, None, None, None

    values = [
        value for ts, value, unused_open in daily
        if datetime.fromtimestamp(ts, _ET).date() >= start
    ]
    if len(values) < 2:
        return None, None, None, None
    if current is not None and current > 0:
        if abs(values[-1] - current) > 1e-6:
            values.append(current)
    pct = 100.0 * (values[-1] - values[0]) / values[0]
    return values, pct, None, None


def _select(panel, period):
    panel._mui_range_v29 = period
    settings = QSettings("MorningTVUI", "MorningTVUI")
    settings.setValue("market_tape_observation_window", period)
    settings.sync()
    panel.subtitle.setText(_CAPTIONS[period])
    for key, button in panel._mui_range_buttons_v29.items():
        button.setChecked(key == period)
    if getattr(panel, "_mui_range_data_v29", None) is not None:
        _apply(panel)


def add_range_buttons_v29(panel, header):
    settings = QSettings("MorningTVUI", "MorningTVUI")
    selected = str(settings.value("market_tape_observation_window", "3 Mo"))
    if selected not in _CAPTIONS:
        selected = "3 Mo"
    panel._mui_range_v29 = selected
    panel._mui_range_data_v29 = None
    panel._mui_range_buttons_v29 = {}
    panel.subtitle.setText(_CAPTIONS[selected])
    buttons = QHBoxLayout()
    buttons.setContentsMargins(0, 0, 0, 0)
    buttons.setSpacing(5)
    for key, caption, n in _WINDOWS:
        button = QPushButton(key, panel)
        button.setCheckable(True)
        button.setChecked(key == selected)
        button.setFixedHeight(17)
        button.setFixedWidth(31 if len(key) >= 3 else 24)
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setStyleSheet('''
            QPushButton {
                background: rgba(18, 35, 39, 0.62);
                color: #d8d2ba;
                border: 1px solid rgba(225, 217, 174, 0.37);
                border-radius: 3px;
                font-family: "Times New Roman";
                font-size: 8px;
                font-weight: 900;
                padding: 0px;
            }
            QPushButton:checked {
                background: rgba(169, 142, 51, 0.38);
                color: #fff4c7;
                border-color: #dec16b;
            }
        ''')
        button.clicked.connect(lambda checked=False, k=key: _select(panel, k))
        panel._mui_range_buttons_v29[key] = button
        buttons.addWidget(button)
    panel._mui_range_header_v29 = buttons
    # MUI_MARKET_TAPE_NAV_V30: balance the header free space on both sides.
    header.addStretch(1)
    header.addLayout(buttons)
    # MUI_MARKET_TAPE_BUTTONS_LEFT_V31: place 3 Mo near panel center.
    header.addStretch(5)


def render_market_ranges_v29(panel, data):
    panel._mui_range_data_v29 = data
    _apply(panel)


def _apply(panel):
    data = panel._mui_range_data_v29
    if data is None:
        return
    period = panel._mui_range_v29
    panel.subtitle.setText(_CAPTIONS[period])
    marks = _MARKS[period]
    if period == "YTD":
        marks = datetime.now(_ET).month
    from ui.panels.stocks_panel import _mui_market_badge

    entries = [
        (widget, quote, widget.change_value)
        for widget, quote in zip(panel.index_widgets, data.indexes)
    ] + [
        (widget, quote, widget.ah_value)
        for widget, quote in zip(panel.stock_widgets, data.stocks)
    ]
    for widget, quote, badge in entries:
        values, percentage, previous_close, intraday_minutes = _window_for_quote(quote, period)
        chart = widget.sparkline
        valid = values is not None and len(values) >= 2
        chart._mui_tick_count_v29 = marks
        chart._mui_intraday_previous_close_v30 = previous_close if valid and period == "1d" else None
        chart._mui_intraday_minutes_v30 = intraday_minutes if valid and period == "1d" else None
        chart._market_percent = percentage if valid else None
        chart._mui_market_no_history_v27 = not valid
        if valid:
            chart.set_values(values)
        else:
            chart.set_values([1, 1, 1])
        _mui_market_badge(badge, percentage if valid else None)
        badge.setVisible(True)
        badge.setToolTip(f"{_CAPTIONS[period]} return" if valid else "No verified observations for this period")
        chart.update()
