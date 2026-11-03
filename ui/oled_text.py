"""OLED contrast V4: presentation only, no geometry/data changes."""
import re
import weakref

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QPalette, QPen, QTextDocument
from PySide6.QtWidgets import (
    QApplication, QLabel, QAbstractButton, QTextEdit,
    QLineEdit, QComboBox, QAbstractSpinBox,
)

_DARK = False
_STYLES = weakref.WeakKeyDictionary()
_HTML = weakref.WeakKeyDictionary()
_PALETTES = weakref.WeakKeyDictionary()

TEXT = QColor("#ead3a3")
PAPER = "#42596b"


def _bright(c):
    return (0.2126*c.red() + 0.7152*c.green()
            + 0.0722*c.blue()) > 145


def _bg_token(m):
    value = m.group(0)
    c = QColor(value)
    return PAPER if c.isValid() and _bright(c) else value


def _bg_rgba(m):
    r, g, b = [int(m.group(i)) for i in (1, 2, 3)]
    a = m.group(4)
    if 0.2126*r + 0.7152*g + 0.0722*b <= 145:
        return m.group(0)
    return f"rgba(66,89,107,{a})"


def _dark_css(css):
    if not css:
        return css

    css = re.sub(
        r"(?<![\w-])color\s*:\s*([^;}]+)",
        lambda m: m.group(0)
        if m.group(1).strip().lower() in ("transparent", "none")
        else "color: #ead3a3",
        css, flags=re.I
    )

    def background(m):
        value = m.group(2)
        if value.strip().lower() in ("transparent", "none"):
            return m.group(0)

        value = re.sub(
            r"#[0-9a-fA-F]{6}\b", _bg_token, value
        )
        value = re.sub(
            r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,"
            r"\s*(\d+)\s*,\s*([\d.]+)\s*\)",
            _bg_rgba, value, flags=re.I
        )
        return m.group(1) + value

    return re.sub(
        r"(background(?:-color)?\s*:\s*)([^;}]+)",
        background, css, flags=re.I
    )


def _dark_html(html):
    html = re.sub(
        r"(?<![\w-])color\s*:\s*"
        r"(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|[a-zA-Z]+)",
        "color: #ead3a3", html, flags=re.I
    )
    html = re.sub(
        r"""(?<![\w-])color\s*=\s*['"]?"""
        r"""(?:#[0-9a-fA-F]{3,8}|[a-zA-Z]+)['"]?""",
        'color="#ead3a3"', html, flags=re.I
    )
    html = re.sub(
        r"(background(?:-color)?\s*:\s*)#[0-9a-fA-F]{6}",
        lambda m: m.group(1) + _bg_token(
            re.search(r"#[0-9a-fA-F]{6}", m.group(0))
        ),
        html, flags=re.I
    )
    return (
        "<style>body,p,div,td,th,h1,h2,h3,span"
        "{color:#ead3a3;}</style>" + html
    )


def oled_text_draw(painter, *args, **kwargs):
    if not _DARK:
        return painter.drawText(*args, **kwargs)

    previous = painter.pen()
    pen = QPen(previous)
    pen.setColor(TEXT)
    painter.setPen(pen)
    try:
        return painter.drawText(*args, **kwargs)
    finally:
        painter.setPen(previous)


def oled_layout_draw(layout, painter, *args, **kwargs):
    if not _DARK:
        return layout.draw(painter, *args, **kwargs)

    previous = painter.pen()
    pen = QPen(previous)
    pen.setColor(TEXT)
    painter.setPen(pen)
    try:
        return layout.draw(painter, *args, **kwargs)
    finally:
        painter.setPen(previous)


def oled_style(widget, css):
    try:
        _STYLES[widget] = css
    except TypeError:
        pass
    return widget.setStyleSheet(
        _dark_css(css) if _DARK else css
    )


def oled_html(widget, html):
    try:
        _HTML[widget] = html
    except TypeError:
        pass
    return widget.setHtml(
        _dark_html(html) if _DARK else html
    )


def _restore_resources(widget):
    try:
        doc = (
            widget.document()
            if hasattr(widget, "document")
            else widget
        )
        owner = widget if hasattr(widget, "parent") else None

        for _ in range(8):
            if owner is None:
                break

            images = getattr(
                owner, "article_image_resources", None
            )
            if isinstance(images, dict):
                for name, image in images.items():
                    doc.addResource(
                        QTextDocument.ResourceType.ImageResource,
                        QUrl(str(name)), image
                    )
                break

            owner = owner.parent()
    except (RuntimeError, AttributeError):
        pass


def _refresh_html(enabled):
    for widget, original in list(_HTML.items()):
        try:
            value = (
                _dark_html(original) if enabled else original
            )
            if hasattr(widget, "verticalScrollBar"):
                bar = widget.verticalScrollBar()
                position = bar.value()
                cursor = widget.textCursor()

                widget.setHtml(value)
                _restore_resources(widget)

                try:
                    widget.setTextCursor(cursor)
                except (RuntimeError, ValueError):
                    pass

                bar.setValue(position)
                widget.viewport().update()
            else:
                widget.setHtml(value)
                _restore_resources(widget)
        except RuntimeError:
            pass


def set_oled_text_dark(enabled, app=None):
    global _DARK

    enabled = bool(enabled)
    if enabled == _DARK:
        return

    _DARK = enabled
    app = app or QApplication.instance()

    if app is None:
        return

    for widget in app.allWidgets():
        try:
            if widget not in _STYLES:
                _STYLES[widget] = widget.styleSheet()

            original = _STYLES[widget]
            desired = (
                _dark_css(original) if enabled else original
            )

            if widget.styleSheet() != desired:
                widget.setStyleSheet(desired)

            if isinstance(widget, (
                QLabel, QAbstractButton, QTextEdit,
                QLineEdit, QComboBox, QAbstractSpinBox
            )):
                if widget not in _PALETTES:
                    _PALETTES[widget] = QPalette(
                        widget.palette()
                    )

                palette = QPalette(_PALETTES[widget])

                if enabled:
                    for role in (
                        QPalette.ColorRole.Text,
                        QPalette.ColorRole.WindowText,
                        QPalette.ColorRole.ButtonText,
                        QPalette.ColorRole.PlaceholderText,
                        QPalette.ColorRole.HighlightedText,
                    ):
                        palette.setColor(role, TEXT)

                    if isinstance(widget, QTextEdit):
                        palette.setColor(
                            QPalette.ColorRole.Base,
                            QColor(PAPER)
                        )

                widget.setPalette(palette)
        except RuntimeError:
            continue

    _refresh_html(enabled)


# OLED_BORDER_WEATHER_V5_SAFE
# Recolor borders only during OLED dark mode.
# Never alter border width, radius, geometry or normal mode.
_previous_dark_css_v5 = _dark_css

def oled_is_dark():
    return _DARK

def _dark_css(css):
    css = _previous_dark_css_v5(css)

    # OLED_INSET_LINES_V6
    # News section inner separators: tan -> subtle slate.
    css = re.sub(
        r"(?i)(background-color\s*:\s*)"
        r"rgba\(\s*90\s*,\s*78\s*,\s*63\s*,\s*135\s*\)",
        r"\g<1>rgba(69,90,105,70)",
        css
    )

    if not css:
        return css


    def recolor(match):
        declaration = match.group(1)
        value = match.group(2)

        if value.strip().lower() in ("none", "transparent"):
            return match.group(0)

        def hex_color(m):
            original = m.group(0)
            color = QColor(original)

            if not color.isValid():
                return original

            r, g, b = color.red(), color.green(), color.blue()

            # Preserve bright gold/yellow focus indicators.
            if r > g and g > 85 and b < 75:
                return original

            return "#526977"

        value = re.sub(
            r"#[0-9a-fA-F]{6}(?![0-9a-fA-F])",
            hex_color,
            value
        )

        def rgb_color(m):
            r, g, b = (int(m.group(i)) for i in (1, 2, 3))
            alpha = m.group(4)

            if r > g and g > 85 and b < 75:
                return m.group(0)

            if alpha is None:
                return "rgb(82,105,119)"

            return f"rgba(82,105,119,{alpha})"

        value = re.sub(
            r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,"
            r"\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)",
            rgb_color,
            value,
            flags=re.I
        )

        return declaration + value

    return re.sub(
        r"((?:border(?:-(?:top|right|bottom|left))?"
        r"(?:-color)?|outline(?:-color)?)\s*:\s*)"
        r"([^;}\n]+)",
        recolor,
        css,
        flags=re.I
    )
