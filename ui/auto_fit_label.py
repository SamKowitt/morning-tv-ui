from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QLabel


class AutoFitLabel(QLabel):
    def __init__(
        self,
        text="",
        min_size=10,
        max_size=40,
        bold=False,
        alignment=Qt.AlignCenter,
        word_wrap=True,
        font_family=None,
    ):
        super().__init__(text)

        self.min_size = min_size
        self.max_size = max_size
        self.bold = bold
        self.fit_alignment = alignment
        self.auto_fit_enabled = True
        self.font_family = str(font_family or "").strip()

        if self.font_family:
            initial_font = QFont(self.font())
            initial_font.setFamily(self.font_family)
            self.setFont(initial_font)

        self.setAlignment(alignment)
        self.setWordWrap(word_wrap)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self.auto_fit_enabled:
            self.fit_text()

    def setText(self, text):
        super().setText(text)

        if self.auto_fit_enabled:
            self.fit_text()

    def set_auto_fit_enabled(self, enabled):
        self.auto_fit_enabled = bool(enabled)

        if self.auto_fit_enabled:
            self.fit_text()

    def best_fit_point_size(self):
        if not self.text() or self.width() <= 4 or self.height() <= 4:
            return self.min_size

        available_width = max(1, self.width() - 6)
        available_height = max(1, self.height() - 6)

        low = self.min_size
        high = self.max_size
        best = self.min_size

        while low <= high:
            mid = (low + high) // 2

            test_font = QFont(self.font())
            test_font.setPointSize(mid)
            test_font.setBold(self.bold)

            metrics = QFontMetrics(test_font)

            rect = metrics.boundingRect(
                0,
                0,
                available_width,
                available_height * 3,
                Qt.TextWordWrap | self.fit_alignment,
                self.text(),
            )

            if (
                rect.width() <= available_width
                and rect.height() <= available_height
            ):
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        return best

    def set_point_size_safely(self, point_size):
        point_size = max(
            self.min_size,
            min(self.max_size, int(point_size)),
        )

        current_font = self.font()

        if (
            current_font.pointSize() == point_size
            and current_font.bold() == self.bold
        ):
            return

        updated_font = QFont(current_font)

        if self.font_family:
            updated_font.setFamily(self.font_family)

        updated_font.setPointSize(point_size)
        updated_font.setBold(self.bold)
        self.setFont(updated_font)

    def fit_text(self):
        self.set_point_size_safely(
            self.best_fit_point_size()
        )
