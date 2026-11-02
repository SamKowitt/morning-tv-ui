import os
import sys

# Match macOS point-font sizing on Raspberry Pi/Linux.
# This must be set before PySide6 is imported.
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_FONT_DPI", "72")

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui.dashboard_window import DashboardWindow


APP_FONT_FAMILY = "Times New Roman"
APP_FONT_SIZE = 12


def main():
    app = QApplication(sys.argv)

    app_font = QFont(APP_FONT_FAMILY, APP_FONT_SIZE)
    app.setFont(app_font)

    window = DashboardWindow()
    window.showFullScreen()

    # MORNINGUI_CEC_DPAD_NAVIGATION_V1
    # Keyboard focus map for LG CEC arrows and OK; unrelated UI remains unchanged.
    try:
        from ui.remote_navigation import install_remote_navigation
        window._lg_dpad_navigation = install_remote_navigation(window)
    except Exception as error:
        print(f"LG D-pad navigation disabled: {error}", flush=True)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()