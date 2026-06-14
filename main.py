import sys

from PySide6.QtWidgets import QApplication

from ui.dashboard_window import DashboardWindow


def main():
    app = QApplication(sys.argv)

    window = DashboardWindow()
    window.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()