from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsDropShadowEffect


def apply_paper_shadow(widget, blur=12, x=3, y=4):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(x, y)
    shadow.setColor(QColor(0, 0, 0, 105))
    widget.setGraphicsEffect(shadow)


def draw_paper_edge(painter, rect):
    # Soft lifted-paper edge: bright upper-left, darker lower-right.
    painter.save()

    painter.setPen(QPen(QColor(255, 248, 228, 115), 1))
    painter.drawLine(int(rect.left() + 1), int(rect.top() + 1), int(rect.right() - 2), int(rect.top() + 1))
    painter.drawLine(int(rect.left() + 1), int(rect.top() + 1), int(rect.left() + 1), int(rect.bottom() - 2))

    painter.setPen(QPen(QColor(35, 24, 14, 95), 2))
    painter.drawLine(int(rect.left() + 2), int(rect.bottom() - 1), int(rect.right() - 1), int(rect.bottom() - 1))
    painter.drawLine(int(rect.right() - 1), int(rect.top() + 2), int(rect.right() - 1), int(rect.bottom() - 1))

    # Faint inner aging line.
    inner = rect.adjusted(4, 4, -4, -4)
    painter.setPen(QPen(QColor(95, 72, 43, 45), 1))
    painter.drawRect(inner)

    painter.restore()
