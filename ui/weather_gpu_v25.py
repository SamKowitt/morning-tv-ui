"""Experimental single-QQuickView embedded GPU weather rows for MorningUI.

Runs only when ~/.cache/morningui_gpu_v25_enabled exists.
Stores snapshots on disk only when data/layout/focus changes; no per-frame Python work.
"""
from pathlib import Path
from time import monotonic
import os

from PySide6.QtCore import QObject, QEvent, QTimer, QUrl, Qt, Slot
from PySide6.QtGui import QColor
from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QWidget

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'weather_gpu_assets_v25'
MODE_FILE = Path.home() / '.config/morningui/gpu_weather_v25_enabled'
FLAG = Path.home() / '.cache/morningui_gpu_v25_active'
SNAPS = Path.home() / '.cache/morningui_gpu_v25_snapshots'


class _Bridge(QObject):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel

    @Slot(int)
    def choose(self, index):
        self.panel.emit_selected_hour(index)


class _Observer(QObject):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel

    def eventFilter(self, obj, event):
        if event.type() in (
            QEvent.Type.StyleChange,
            QEvent.Type.DynamicPropertyChange,
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
        ):
            self.panel._gpu25_dirty = True
        return False


def _fail(panel, why):
    print('MORNINGUI_GPU_V25_ERROR:', why, flush=True)
    try:
        panel._gpu25_container.hide()
    except (AttributeError, RuntimeError):
        pass
    for row in panel.row_widgets:
        if row.isVisible() and not row.timer.isActive():
            row.timer.start(50)
    panel._gpu25_active = False
    try:
        FLAG.unlink(missing_ok=True)
    except OSError:
        pass
    panel._gpu25_last_error = str(why)
    # Avoid repeatedly rebuilding a failed native child window.
    panel._gpu25_disabled = True


def _ensure_view(panel):
    if getattr(panel, '_gpu25_view', None) is not None:
        return True
    try:
        view = QQuickView()
        view.setColor(QColor('#172c43'))
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.setFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        bridge = _Bridge(panel)
        view.rootContext().setContextProperty('gpuBridge', bridge)
        view.setSource(QUrl.fromLocalFile(str(ROOT / 'weather_gpu_v25.qml')))
        if view.status() == QQuickView.Status.Error:
            raise RuntimeError('; '.join(x.toString() for x in view.errors()))
        container = QWidget.createWindowContainer(view, panel)
        container.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        container.setGeometry(panel.rect())
        panel._gpu25_view = view
        panel._gpu25_bridge = bridge
        panel._gpu25_container = container
        view.show()
        return True
    except Exception as exc:
        _fail(panel, 'QQuickView installation: ' + repr(exc))
        return False


def _render_rows(panel):
    if not getattr(panel, '_gpu25_active', False):
        return
    if panel.width() < 40 or panel.height() < 60:
        return

    SNAPS.mkdir(parents=True, exist_ok=True)
    items = []
    token = str(os.getpid()) + '_' + str(int(monotonic() * 1000))
    new_files = []
    for i, row in enumerate(panel.row_widgets):
        if not row.isVisible() or row.width() < 20 or row.height() < 20:
            continue
        # The original QWidget provides accurate text, forecast details, moon
        # phase, borders, padding and the current weather art, once per update.
        pic = row.grab()
        path = SNAPS / f'live_{i}_{token}.png'
        if not pic.save(str(path), 'PNG'):
            raise RuntimeError('Could not save ' + str(path))
        new_files.append(path)
        pos = row.mapTo(panel, row.rect().topLeft())
        items.append({
            'image': path.as_uri(),
            'x': pos.x(), 'y': pos.y(),
            'w': row.width(), 'h': row.height(),
            'index': i,
            'condition': str(getattr(row, 'condition', '')).lower(),
            'night': bool(getattr(row, 'is_night', False)),
        })

    if len(items) < 1:
        raise RuntimeError('No visible weather cards to display')

    obj = panel._gpu25_view.rootObject()
    if obj is None:
        raise RuntimeError('Missing QML root object')
    obj.setProperty('cards', items)
    panel._gpu25_container.setGeometry(panel.rect())
    panel._gpu25_container.raise_()
    panel._gpu25_container.show()
    panel._gpu25_dirty = False

    # Delete obsolete image files only if this is still the newest snapshot.
    panel._gpu25_latest = token
    QTimer.singleShot(2500, lambda: _delete_old(panel, token))
    backend = panel._gpu25_view.rendererInterface().graphicsApi().name
    if backend not in ('OpenGL', 'Vulkan'):
        raise RuntimeError('GPU backend not verified: ' + backend)
    print('MORNINGUI_GPU_V25_ACTIVE:', os.getpid(),
          len(items), 'hourly rows; backend', backend, flush=True)
    FLAG.write_text(f'{os.getpid()} {len(items)}\n')


def _delete_old(panel, keep):
    if getattr(panel, '_gpu25_latest', None) != keep:
        return
    for path in SNAPS.glob('live_*.png'):
        if keep not in path.name:
            try:
                path.unlink()
            except OSError:
                pass


def _sync(panel):
    if getattr(panel, '_gpu25_disabled', False):
        return
    desired = MODE_FILE.exists()
    active = getattr(panel, '_gpu25_active', False)
    if not desired:
        if active:
            panel._gpu25_container.hide()
            for row in panel.row_widgets:
                if row.isVisible() and not row.timer.isActive():
                    row.timer.start(50)
            panel._gpu25_active = False
            for row in panel.row_widgets:
                row.update()
            panel.update()
            FLAG.unlink(missing_ok=True)
            print('MORNINGUI_GPU_V25: original renderer restored live', flush=True)
        return
    if not active:
        if not _ensure_view(panel):
            return
        panel._gpu25_active = True
        panel._gpu25_dirty = True
        for row in panel.row_widgets:
            row.timer.stop()
    if getattr(panel, '_gpu25_dirty', False):
        try:
            _render_rows(panel)
        except Exception as exc:
            _fail(panel, repr(exc))
    elif panel._gpu25_container.geometry() != panel.rect():
        panel._gpu25_container.setGeometry(panel.rect())
        panel._gpu25_dirty = True


def install(WeatherPanel):
    old_init = WeatherPanel.__init__
    old_update = WeatherPanel.update_weather_rows

    def new_init(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        self._gpu25_active = False
        self._gpu25_disabled = False
        self._gpu25_dirty = True
        self._gpu25_view = None
        self._gpu25_observer = _Observer(self)
        for row in self.row_widgets:
            row.installEventFilter(self._gpu25_observer)
        self._gpu25_check = QTimer(self)
        self._gpu25_check.setInterval(750)
        self._gpu25_check.timeout.connect(lambda: _sync(self))
        self._gpu25_check.start()
        QTimer.singleShot(900, lambda: _sync(self))

    def new_update(self, *args, **kwargs):
        result = old_update(self, *args, **kwargs)
        self._gpu25_dirty = True
        if self._gpu25_active:
            for row in self.row_widgets:
                row.timer.stop()
            QTimer.singleShot(400, lambda: _sync(self))
        return result

    WeatherPanel.__init__ = new_init
    WeatherPanel.update_weather_rows = new_update
