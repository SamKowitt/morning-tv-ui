from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen


def draw_newspaper_sheet(painter: QPainter, rect, seed: int = 1):
    draw_stacked_newspaper_panel(painter, rect, seed=seed)


def draw_stacked_newspaper_panel(painter: QPainter, rect, seed: int = 1):
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    outer = QRectF(rect).adjusted(4, 4, -6, -6)

    # drop shadow
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 34))
    painter.drawRoundedRect(outer.adjusted(6, 7, 10, 10), 6, 6)

    # back sheets (only top/right visible, not bottom)
    back_specs = [
        (5.0, -3.0, 40),
        (2.5, -1.5, 55),
    ]
    for dx, dy, alpha in back_specs:
        back = QRectF(outer).adjusted(dx, dy, dx - 10, dy - 20)

        g = QLinearGradient(back.topLeft(), back.bottomLeft())
        g.setColorAt(0.0, QColor("#ead7b3"))
        g.setColorAt(1.0, QColor("#d6b983"))

        painter.setBrush(g)
        painter.setPen(QPen(QColor(96, 67, 34, alpha), 1))
        painter.drawRoundedRect(back, 5, 5)

        painter.setPen(QPen(QColor(120, 88, 49, 32), 1))
        painter.drawLine(
            int(back.left() + 28),
            int(back.top() + 4),
            int(back.right() - 22),
            int(back.top() + 4),
        )

    # front sheet
    sheet = QRectF(outer).adjusted(0, 0, -10, -8)

    paper = QLinearGradient(sheet.topLeft(), sheet.bottomRight())
    paper.setColorAt(0.00, QColor("#f5e7c3"))
    paper.setColorAt(0.55, QColor("#e7cf9c"))
    paper.setColorAt(1.00, QColor("#d6b06e"))

    painter.setBrush(paper)
    painter.setPen(QPen(QColor("#5b3c1d"), 1))
    painter.drawRoundedRect(sheet, 6, 6)

    # inner edge / aged border
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(88, 61, 29, 55), 1))
    painter.drawRoundedRect(sheet.adjusted(2, 2, -2, -2), 5, 5)

    # top and left soft highlight
    painter.setPen(QPen(QColor(255, 248, 230, 70), 1))
    painter.drawLine(
        int(sheet.left() + 12),
        int(sheet.top() + 2),
        int(sheet.right() - 12),
        int(sheet.top() + 2),
    )
    painter.drawLine(
        int(sheet.left() + 2),
        int(sheet.top() + 10),
        int(sheet.left() + 2),
        int(sheet.bottom() - 18),
    )

    # right thickness line
    painter.setPen(QPen(QColor(67, 45, 22, 36), 2))
    painter.drawLine(
        int(sheet.right() - 2),
        int(sheet.top() + 12),
        int(sheet.right() - 2),
        int(sheet.bottom() - 14),
    )

    _draw_bottom_fold_only(painter, sheet)
    painter.restore()


def _draw_bottom_fold_only(painter: QPainter, sheet: QRectF):
    """
    Full-width newspaper fold:
    - runs across the entire bottom
    - reaches the FAR RIGHT EDGE
    - no center cylinder / no floating knob
    - subtle right-corner turnover only
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    left = sheet.left() + 8
    right = sheet.right() - 1.0   # IMPORTANT: far right edge
    top = sheet.bottom() - 11.0
    bottom = sheet.bottom() - 1.5
    span = right - left

    # shadow below fold
    shadow = QPainterPath()
    shadow.moveTo(left + 10, bottom - 1)
    shadow.cubicTo(
        left + span * 0.28, bottom + 2.8,
        left + span * 0.72, bottom + 2.8,
        right - 4, bottom - 1
    )
    shadow.lineTo(right - 4, bottom + 3)
    shadow.cubicTo(
        left + span * 0.72, bottom + 5.0,
        left + span * 0.28, bottom + 5.0,
        left + 8, bottom + 3
    )
    shadow.closeSubpath()

    sg = QLinearGradient(left, top, left, bottom + 6)
    sg.setColorAt(0.0, QColor(0, 0, 0, 0))
    sg.setColorAt(0.7, QColor(40, 23, 8, 24))
    sg.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(sg)
    painter.drawPath(shadow)

    # full-width fold band
    fold = QPainterPath()
    fold.moveTo(left, top + 2.2)
    fold.cubicTo(
        left + span * 0.22, top + 0.2,
        left + span * 0.78, top + 0.2,
        right, top + 2.0
    )
    fold.lineTo(right, bottom - 0.8)
    fold.cubicTo(
        left + span * 0.78, bottom + 0.9,
        left + span * 0.22, bottom + 0.9,
        left + 2, bottom - 0.6
    )
    fold.closeSubpath()

    fg = QLinearGradient(left, top, left, bottom)
    fg.setColorAt(0.00, QColor("#eed7a8"))
    fg.setColorAt(0.28, QColor("#d6a35f"))
    fg.setColorAt(0.60, QColor("#c88f46"))
    fg.setColorAt(1.00, QColor("#f1d9a6"))

    painter.setPen(QPen(QColor(109, 71, 31, 58), 1))
    painter.setBrush(fg)
    painter.drawPath(fold)

    # crease line across full width
    crease = QPainterPath()
    crease.moveTo(left + 6, top + 2.1)
    crease.cubicTo(
        left + span * 0.25, top + 0.4,
        left + span * 0.75, top + 0.4,
        right - 1, top + 2.0
    )
    painter.setPen(QPen(QColor(100, 64, 28, 70), 1))
    painter.drawPath(crease)

    # underside line
    underside = QPainterPath()
    underside.moveTo(left + 10, bottom - 0.8)
    underside.cubicTo(
        left + span * 0.30, bottom + 0.8,
        left + span * 0.70, bottom + 0.8,
        right - 2, bottom - 0.6
    )
    painter.setPen(QPen(QColor(72, 43, 16, 40), 1))
    painter.drawPath(underside)

    # subtle turnover at the FAR RIGHT CORNER ONLY
    curl = QPainterPath()
    curl.moveTo(right - 82, top + 1.0)
    curl.cubicTo(
        right - 52, top + 0.6,
        right - 22, top + 1.2,
        right, top + 3.2
    )
    curl.cubicTo(
        right + 0.4, top + 6.0,
        right - 2.0, bottom - 0.8,
        right - 18, bottom - 0.2
    )
    curl.cubicTo(
        right - 34, bottom + 0.8,
        right - 56, bottom - 1.5,
        right - 82, bottom - 4.2
    )

    cg = QLinearGradient(right - 82, top, right, bottom)
    cg.setColorAt(0.00, QColor(255, 247, 224, 0))
    cg.setColorAt(0.55, QColor(255, 245, 214, 145))
    cg.setColorAt(0.85, QColor(244, 220, 176, 185))
    cg.setColorAt(1.00, QColor(214, 173, 104, 120))

    painter.setPen(QPen(QColor(128, 83, 38, 52), 1))
    painter.setBrush(cg)
    painter.drawPath(curl)

    # little inner return line so it reads as a fold, not a cylinder
    return_line = QPainterPath()
    return_line.moveTo(right - 58, top + 2.1)
    return_line.cubicTo(
        right - 34, top + 1.6,
        right - 12, top + 3.0,
        right - 9, bottom - 0.7
    )
    painter.setPen(QPen(QColor(255, 248, 225, 100), 1))
    painter.drawPath(return_line)

    painter.restore()
