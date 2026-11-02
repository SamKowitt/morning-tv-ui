from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QBrush


def draw_newspaper_sheet(painter: QPainter, rect, seed: int = 1):
    draw_stacked_newspaper_panel(painter, rect, seed=seed)


def draw_stacked_newspaper_panel(painter: QPainter, rect, seed: int = 1):
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    outer = QRectF(rect).adjusted(4, 4, -3, -5)

    # Back pages only at the top/right. They stop before the bottom.
    for dx, dy, alpha in [(5.0, -3.0, 40), (2.5, -1.2, 54)]:
        back = QRectF(outer).adjusted(dx, dy, dx - 10, dy - 22)

        back_grad = QLinearGradient(back.topLeft(), back.bottomLeft())
        back_grad.setColorAt(0.0, QColor("#ead6b0"))
        back_grad.setColorAt(1.0, QColor("#d8b985"))

        painter.setBrush(back_grad)
        painter.setPen(QPen(QColor(90, 62, 31, alpha), 1))
        painter.drawRoundedRect(back, 5, 5)

        painter.setPen(QPen(QColor(110, 80, 44, 30), 1))
        painter.drawLine(
            int(back.left() + 34),
            int(back.top() + 4),
            int(back.right() - 28),
            int(back.top() + 4),
        )

    # Main page. Right side is barely inset so the fold can reach the far side.
    sheet = QRectF(outer).adjusted(0, 0, -7, -8)

    # NEWSPAPER_ROUNDED_DIRECTIONAL_SHADOW_V6
    #
    # Direction: upper left -> lower right.
    #
    # Multiple rounded silhouettes create a
    # smooth shadow that follows the actual
    # newspaper corners, unlike fillRect.
    #
    # Rendered after back pages and before
    # the main paper, so it remains visible
    # to the bottom and right.

    painter.save()
    painter.setRenderHint(
        QPainter.RenderHint.Antialiasing,
        True,
    )
    painter.setPen(Qt.PenStyle.NoPen)

    # Soft outer layers first, darker contact
    # layers last. These values preserve roughly
    # the current bottom-shadow strength.
    # Directional shadow with sufficient
    # right-side clearance to remain visible.
    # No rectangular fills or square corners.
    # NEWSPAPER_SHADOW_REFINEMENT_V9
    # Shift all shadow layers a bit farther right.
    # Darken slightly.
    # Preserve vertical offsets and rounded corners.
    # NEWSPAPER_SHADOW_REFINEMENT_V12
    # Shift +1px right, darken approximately 15%.
    # Preserve all vertical offsets.
    # NEWSPAPER_SHADOW_OFFSET_V13
    # Shift right +1px and down +1px.
    # Preserve opacity and corner curvature.
    # NEWSPAPER_SHADOW_OFFSET_V14
    # Down 1px, left 0.5px.
    # Preserve opacity, shape, and corner radius.
    shadow_layers = [
        (12.5, 12.0, 14),
        (11.5, 10.0, 20),
        (10.5, 8.0, 25),
        (9.5, 6.5, 31),
        (8.5, 5.0, 38),
        (7.5, 3.5, 46),
    ]

    for dx, dy, opacity in shadow_layers:
        shadow_shape = QPainterPath()

        # NEWSPAPER_SHADOW_CURVE_V12
        # 12px shadow curvature, reduced from 20px.
        # Does not alter the newspaper itself.
        shadow_shape.addRoundedRect(
            QRectF(sheet).translated(dx, dy),
            12.0,
            12.0,
        )

        # NEWSPAPER_GEOMETRIC_TAPER_V17
        #
        # Keep each layer's existing darkness.
        # Shift the upper shadow only 5px left.
        # Gradually return to its original position
        # at the bottom of the newspaper.
        #
        # No change to radius, vertical offsets,
        # or bottom shadow position.

        painter.save()

        painter.translate(0.0, sheet.bottom())
        painter.shear(
            5.0 / max(1.0, sheet.height()),
            0.0,
        )
        painter.translate(0.0, -sheet.bottom())

        painter.fillPath(
            shadow_shape,
            QColor(3, 7, 10, opacity),
        )

        # NEWSPAPER_CORNER_DARKEN_V19
        # Add a subtle darkening confined to the
        # bottom-right of the existing shadow.
        # No changes to shape, offset, or taper.

        from importlib import import_module
        qtgui = import_module(QColor.__module__)

        corner_rect = QRectF(sheet).translated(dx, dy)

        # NEWSPAPER_CORNER_DARKEN_V20
        # Slightly stronger, more concentrated
        # darkness at the bottom-right corner.
        # NEWSPAPER_CORNER_POSITION_V21
        # Move only the corner darkening 3px lower.
        corner_center = corner_rect.bottomRight()
        corner_center.setY(corner_center.y() + 3.0)

        corner_gradient = qtgui.QRadialGradient(
            corner_center,
            36.0,
        )

        # NEWSPAPER_CORNER_DARKNESS_V22
        # Slightly darker at the bottom-right only.
        corner_strength = max(
            2,
            round(opacity * 0.21),
        )

        corner_gradient.setColorAt(
            0.0,
            QColor(3, 7, 10, corner_strength),
        )

        corner_gradient.setColorAt(
            0.45,
            QColor(
                3, 7, 10,
                round(corner_strength * 0.45),
            ),
        )

        corner_gradient.setColorAt(
            1.0,
            QColor(3, 7, 10, 0),
        )

        painter.fillPath(
            shadow_shape,
            qtgui.QBrush(corner_gradient),
        )

        painter.restore()

    painter.restore()

    paper_grad = QLinearGradient(sheet.topLeft(), sheet.bottomRight())
    paper_grad.setColorAt(0.00, QColor("#f6e9c8"))
    paper_grad.setColorAt(0.52, QColor("#ead3a3"))
    paper_grad.setColorAt(1.00, QColor("#d4b073"))

    painter.setBrush(paper_grad)
    painter.setPen(QPen(QColor("#5d3d20"), 1))
    painter.drawRoundedRect(sheet, 6, 6)

    # Soft aged edge.
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(92, 63, 31, 55), 1))
    painter.drawRoundedRect(sheet.adjusted(2, 2, -2, -2), 5, 5)

    # Top/left highlights.
    painter.setPen(QPen(QColor(255, 248, 229, 70), 1))
    painter.drawLine(
        int(sheet.left() + 14),
        int(sheet.top() + 2),
        int(sheet.right() - 14),
        int(sheet.top() + 2),
    )
    painter.drawLine(
        int(sheet.left() + 2),
        int(sheet.top() + 12),
        int(sheet.left() + 2),
        int(sheet.bottom() - 18),
    )

    # Right-side paper thickness, ending at the fold.
    painter.setPen(QPen(QColor(59, 37, 15, 30), 2))
    painter.drawLine(
        int(sheet.right() - 2),
        int(sheet.top() + 12),
        int(sheet.right() - 2),
        int(sheet.bottom() - 18),
    )

    _draw_bottom_fold_full_width(painter, sheet)

    # NEWSPAPER_RIGHT_CONTACT_EDGE_V6
    #
    # A narrow, soft contact shadow beside the
    # existing paper edge. Rounded ends avoid
    # the squared-off appearance of the old
    # rectangular gradient.

    painter.save()
    painter.translate(-0.5, 1.0)
    painter.setRenderHint(
        QPainter.RenderHint.Antialiasing,
        True,
    )

    # NEWSPAPER_TAPERED_CONTACT_V17
    # Preserve original contact shadow darkness.

    edge_pen = QPen(
        QColor(3, 7, 10, 106),
        1.6,
    )
    edge_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

    painter.setPen(edge_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    painter.drawLine(
        int(sheet.right() + 2.8),
        int(sheet.top() + 10),
        int(sheet.right() + 5.4),
        int(sheet.bottom() - 8),
    )

    painter.restore()

    # Tiny paper grain.
    painter.setPen(QPen(QColor(72, 49, 24, 6), 1))
    w = max(1, int(sheet.width()))
    h = max(1, int(sheet.height()))
    for i in range(12):
        x = int(sheet.left() + ((i * 37 + seed * 19) % w))
        y = int(sheet.top() + ((i * 29 + seed * 11) % h))
        painter.drawPoint(x, y)

    painter.restore()


def _draw_bottom_fold_full_width(painter: QPainter, sheet: QRectF):
    """
    Smooth curved newspaper fold with rounded right corner.

    Restored version:
    - rounded-over right corner
    - no flat stacked-paper bottom
    - no harsh added page-line patch
    - warm paper color
    - lighter left side
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    left = sheet.left() + 2.0
    right = sheet.right() + 2.0
    bottom = sheet.bottom() - 0.8
    width = right - left

    fold_h = max(18.0, min(24.0, sheet.height() * 0.070))
    top = bottom - fold_h

    paper = QLinearGradient(left, 0, right, 0)
    paper.setColorAt(0.00, QColor("#efdcaf"))
    paper.setColorAt(0.25, QColor("#ecd5a4"))
    paper.setColorAt(0.60, QColor("#e4c48b"))
    paper.setColorAt(1.00, QColor("#d9b06f"))

    painter.setPen(Qt.PenStyle.NoPen)

    painter.fillRect(QRectF(left, top - 5.0, width, 8.0), paper)

    bridge = QPainterPath()
    bridge.moveTo(sheet.right() - 8.0, top - 3.5)
    bridge.lineTo(right - 2.0, top - 2.0)
    bridge.cubicTo(
        right + 1.5, top + fold_h * 0.25,
        right + 0.8, bottom - 3.0,
        right - 3.0, bottom - 0.3
    )
    bridge.lineTo(sheet.right() - 9.0, bottom + 0.2)
    bridge.cubicTo(
        sheet.right() - 5.0, bottom - 4.0,
        sheet.right() - 5.0, top + 6.0,
        sheet.right() - 8.0, top - 3.5
    )
    bridge.closeSubpath()

    painter.setBrush(paper)
    painter.drawPath(bridge)

    fold = QPainterPath()
    fold.moveTo(left, top + 2.2)

    fold.cubicTo(
        left + width * 0.18, top + 0.6,
        left + width * 0.68, top + 0.4,
        right - 58.0, top + 1.8
    )

    fold.cubicTo(
        right - 34.0, top + 1.8,
        right - 12.0, top + 5.4,
        right - 2.5, top + fold_h * 0.38
    )

    fold.cubicTo(
        right + 2.5, top + fold_h * 0.52,
        right + 1.2, bottom - 4.4,
        right - 5.4, bottom - 0.7
    )

    fold.cubicTo(
        right - 22.0, bottom + 0.7,
        right - 47.0, bottom + 0.45,
        right - 70.0, bottom - 0.15
    )

    fold.cubicTo(
        left + width * 0.70, bottom + 1.0,
        left + width * 0.26, bottom + 0.85,
        left, bottom - 0.25
    )

    fold.closeSubpath()

    painter.setBrush(paper)
    painter.drawPath(fold)

    painter.save()
    painter.setClipPath(fold)

    depth = QLinearGradient(0, top, 0, bottom)
    depth.setColorAt(0.00, QColor(255, 250, 238, 0))
    depth.setColorAt(0.24, QColor(255, 248, 234, 8))
    depth.setColorAt(0.66, QColor(255, 244, 228, 10))
    depth.setColorAt(1.00, QColor(92, 60, 20, 13))
    painter.fillRect(QRectF(left, top, width + 4.0, fold_h + 2.0), depth)

    left_lift = QLinearGradient(left, 0, left + width * 0.38, 0)
    left_lift.setColorAt(0.00, QColor(255, 247, 226, 80))
    left_lift.setColorAt(0.35, QColor(255, 245, 220, 38))
    left_lift.setColorAt(1.00, QColor(255, 245, 220, 0))
    painter.fillRect(QRectF(left, top - 1.0, width * 0.44, fold_h + 4.0), left_lift)

    round_shade = QLinearGradient(right - 54.0, top, right + 4.0, bottom)
    round_shade.setColorAt(0.00, QColor(217, 176, 108, 0))
    round_shade.setColorAt(0.40, QColor(150, 102, 40, 14))
    round_shade.setColorAt(0.70, QColor(255, 246, 226, 18))
    round_shade.setColorAt(1.00, QColor(120, 78, 26, 18))
    painter.fillRect(QRectF(right - 58.0, top - 1.0, 62.0, fold_h + 4.0), round_shade)

    shine = QPainterPath()
    shine.moveTo(left + 10.0, top + fold_h * 0.68)
    shine.cubicTo(
        left + width * 0.30, top + fold_h * 0.82,
        right - 82.0, top + fold_h * 0.77,
        right - 18.0, top + fold_h * 0.55
    )
    shine.cubicTo(
        right - 8.0, top + fold_h * 0.49,
        right - 4.0, top + fold_h * 0.55,
        right - 7.0, bottom - 2.8
    )
    painter.setPen(QPen(QColor(255, 250, 240, 22), 1.0))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(shine)

    bottom_line = QPainterPath()
    bottom_line.moveTo(left + 8.0, bottom - 0.2)
    bottom_line.cubicTo(
        left + width * 0.30, bottom + 0.45,
        right - 86.0, bottom + 0.35,
        right - 10.0, bottom - 0.20
    )
    painter.setPen(QPen(QColor(92, 60, 20, 10), 0.8))
    painter.drawPath(bottom_line)

    painter.restore()

    edge = QPainterPath()
    edge.moveTo(right - 36.0, top + 2.0)
    edge.cubicTo(
        right - 18.0, top + 3.8,
        right - 3.0, top + fold_h * 0.35,
        right - 1.2, top + fold_h * 0.55
    )
    edge.cubicTo(
        right + 0.4, top + fold_h * 0.72,
        right - 2.0, bottom - 2.0,
        right - 7.0, bottom - 0.8
    )
    painter.setPen(QPen(QColor(90, 58, 20, 12), 0.7))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(edge)

    painter.restore()

