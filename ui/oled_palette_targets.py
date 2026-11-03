# OLED_PALETTE_TARGETS_V11
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

_MARK = "/* OLED_PALETTE_TARGETS_V11 */"
_PROP = "_oled_v11_original_style"
_ACTIVE = False
_TIMER = None

_RULES = {
    "MarketTapeCard":
        "QWidget#MarketTapeCard { "
        "border:2px solid rgba(82,105,119,145); "
        "border-radius:15px; }",

    "MarketTapeIndexCard":
        "QWidget#MarketTapeIndexCard { "
        "border:1px solid rgba(82,105,119,95); "
        "border-radius:9px; }",

    "TodayReminderRow":
        "QWidget#TodayReminderRow { "
        "background:qlineargradient("
        "x1:0,y1:0,x2:1,y2:0,"
        "stop:0 #45596a,"
        "stop:0.70 #3e5162,"
        "stop:1 #364959); "
        "border:none; "
        "border-left:3px solid rgba(82,105,119,170); "
        "border-top:1px solid rgba(82,105,119,115); "
        "border-bottom:1px solid rgba(82,105,119,90); "
        "border-radius:12px; }",

    "UpcomingReminderRow":
        "QWidget#UpcomingReminderRow { "
        "background:rgba(49,66,79,90); "
        "border:none; "
        "border-top:1px solid rgba(82,105,119,110); "
        "border-radius:8px; }",

    "OldNewsHeadline":
        "QLabel#OldNewsHeadline { color:#ead3a3; }",

    "RemindersTitle":
        "QLabel#RemindersTitle { color:#ead3a3; }",

    "TodayReminderGroupTitle":
        "QLabel#TodayReminderGroupTitle { color:#ead3a3; }",

    "UpcomingReminderGroupTitle":
        "QLabel#UpcomingReminderGroupTitle { color:#ead3a3; }",

    "TodayReminderText":
        "QLabel#TodayReminderText { color:#ead3a3; }",

    "UpcomingReminderText":
        "QLabel#UpcomingReminderText { color:#ead3a3; }",

    "TodayReminderIcon":
        "QLabel#TodayReminderIcon { color:#ead3a3; }",

    "UpcomingReminderIcon":
        "QLabel#UpcomingReminderIcon { color:#ead3a3; }",

    "ReminderMeta":
        "QLabel#ReminderMeta { color:#ead3a3; }",

    "RemindersHeaderRule":
        "QFrame#RemindersHeaderRule { "
        "background:rgba(82,105,119,145); }",

    "RemindersHideButton":
        "QPushButton#RemindersHideButton { "
        "color:#ead3a3; "
        "background:rgba(53,74,88,190); "
        "border:1px solid rgba(82,105,119,130); }",

    "ReminderSendButton":
        "QPushButton#ReminderSendButton { "
        "color:#ead3a3; "
        "background:rgba(53,74,88,185); "
        "border:1px solid rgba(82,105,119,130); }",

    "UpcomingReminderSendButton":
        "QPushButton#UpcomingReminderSendButton { "
        "color:#ead3a3; "
        "background:rgba(53,74,88,185); "
        "border:1px solid rgba(82,105,119,130); }",
}


def _apply(app):
    changed = 0

    if not _ACTIVE or app is None:
        return changed

    for widget in app.allWidgets():
        try:
            rule = _RULES.get(widget.objectName())

            if not rule:
                continue

            current = widget.styleSheet()

            if _MARK in current:
                continue

            widget.setProperty(_PROP, current)
            widget.setStyleSheet(
                current + "\n" + rule + "\n" + _MARK
            )
            changed += 1

        except RuntimeError:
            pass

    return changed


def enable(app=None):
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, _morningui_oled_nav_refresh_global)
    __import__('os').environ['MORNINGUI_OLED_FOCUS_ACTIVE'] = '1'
    global _ACTIVE, _TIMER

    app = app or QApplication.instance()
    if app is None:
        return

    _ACTIVE = True
    count = _apply(app)

    print(
        f"OLED V11: directly themed {count} widgets",
        flush=True
    )

    # Catch newly created calendar rows after data refresh.
    # Existing widgets are not repeatedly restyled.
    if _TIMER is None:
        _TIMER = QTimer(app)
        _TIMER.setInterval(2000)
        _TIMER.timeout.connect(
            lambda: _apply(QApplication.instance())
        )

    if not _TIMER.isActive():
        _TIMER.start()


def disable(app=None):
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, _morningui_oled_nav_refresh_global)
    __import__('os').environ['MORNINGUI_OLED_FOCUS_ACTIVE'] = '0'
    global _ACTIVE

    _ACTIVE = False

    if _TIMER is not None:
        _TIMER.stop()

    app = app or QApplication.instance()
    if app is None:
        return

    for widget in app.allWidgets():
        try:
            original = widget.property(_PROP)

            if original is None:
                continue

            if _MARK in widget.styleSheet():
                widget.setStyleSheet(original)

            widget.setProperty(_PROP, None)

        except RuntimeError:
            pass

# MORNINGUI_OLED_NAV_BLACK_V13

# MORNINGUI_OLED_NAV_MODE_SYNC_V14
def _morningui_oled_nav_refresh_global():
    import sys

    for module in tuple(sys.modules.values()):
        fn = getattr(module, "_morningui_oled_nav_sync", None)
        if callable(fn):
            try:
                fn()
            except (RuntimeError, TypeError):
                pass

    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()

        if app is not None:
            for widget in app.allWidgets():
                if (
                    getattr(widget, "_morningui_remote_selected", False)
                    or getattr(
                        widget,
                        "_morningui_remote_games_index",
                        None
                    ) is not None
                ):
                    widget.update()
    except (RuntimeError, TypeError):
        pass
