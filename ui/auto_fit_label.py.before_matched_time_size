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
    ):
        super().__init__(text)

        self.min_size = min_size
        self.max_size = max_size
        self.bold = bold
        self.fit_alignment = alignment

        self.setAlignment(alignment)
        self.setWordWrap(word_wrap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_text()

    def setText(self, text):
        super().setText(text)
        self.fit_text()

    def fit_text(self):
        if not self.text() or self.width() <= 4 or self.height() <= 4:
            return

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

            if rect.width() <= available_width and rect.height() <= available_height:
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        final_font = QFont(self.font())
        final_font.setPointSize(best)
        final_font.setBold(self.bold)
        self.setFont(final_font)