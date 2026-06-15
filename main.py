import sys

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

    sys.exit(app.exec())


if __name__ == "__main__":
    main()