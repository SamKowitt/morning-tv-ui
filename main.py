import os
import sys

# Match macOS point-font sizing on Raspberry Pi/Linux.
# This must be set before PySide6 is imported.
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_FONT_DPI", "72")

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import QApplication

from ui.dashboard_window import DashboardWindow


APP_FONT_FAMILY = "Times New Roman"
APP_FONT_SIZE = 12


def main():
    app = QApplication(sys.argv)

    # MORNINGUI_CURSOR_HIDDEN_WHILE_RUNNING_V1
    # Hide the pointer only within MorningUI.
    app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))

    app_font = QFont(APP_FONT_FAMILY, APP_FONT_SIZE)
    app.setFont(app_font)

    window = DashboardWindow()
    window.showFullScreen()
    # MORNINGUI_OLED_PROTECTION_V1
    try:
        from ui.oled_protection import OLEDProtection
        window._oled_protection = OLEDProtection(app, window)
    except Exception as error:
        print(f"OLED protection startup error: {error}", flush=True)

    # MORNINGUI_CEC_DPAD_NAVIGATION_V1
    # Keyboard focus map for LG CEC arrows and OK; unrelated UI remains unchanged.
    try:
        from ui.remote_navigation import install_remote_navigation
        window._lg_dpad_navigation = install_remote_navigation(window)
    except Exception as error:
        print(f"LG D-pad navigation disabled: {error}", flush=True)

    try:
        exit_code = app.exec()
    finally:
        # Restore the normal cursor during clean shutdown.
        app.restoreOverrideCursor()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()