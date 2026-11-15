"""Native hourly animations: independent Qt layer-shell process, original WeatherRow data."""
import json
import os
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Qt, QEvent
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from ui.weather_gpu_v26_helper import (
    _v41_foreground_image, _v41_border_phase, _v5w_mode,
    _v6_cloud_speed_multiplier,
)

ROOT = Path.home() / ".cache/morningui_native_hourly_v1"
QML = Path(__file__).resolve().parent / "native_hourly_v1/Layer.qml"


class NativeHourly(QObject):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self.process = None
        self.ready = False
        self.failed = False
        self.stopping = False
        self.started_at = 0.0
        self.last_write = 0.0
        self.cards = []
        self.signature = None
        self.version = 0
        self.last_policy = None
        self.line_buffer = ""
        self._popup_early = set()
        self._popup_generation = {}
        ROOT.mkdir(parents=True, exist_ok=True)
        (ROOT / "ready").unlink(missing_ok=True)
        (ROOT / "state.json").unlink(missing_ok=True)
        self.tick = QTimer(self)
        self.tick.setInterval(130)
        self.tick.timeout.connect(self.sync)
        self.tick.start()
        # MUI_QML_NEWSPAPER_V1: native QML draws newspaper above weather.
        self._qml_news_enabled = (ROOT / "qml_news_enabled").is_file()
        self._qml_news_target = None
        self._qml_news_document = {"show": False}
        self._qml_news_focus_id = ""
        self._qml_news_revision = 0
        QApplication.instance().installEventFilter(self)
        QApplication.instance().aboutToQuit.connect(self.shutdown)
        QTimer.singleShot(0, self.sync)

    def _qml_news_prepare(self, dialog, defer_content=False):
        if not (self._qml_news_enabled and self.ready and not self.stopping
                and len(self.cards) == 9):
            return False
        if self._qml_news_target not in (None, dialog):
            return False
        self._qml_news_target = dialog
        if defer_content:
            # Wait for cached article pagination.
            # Never publish a temporary Fetching placeholder.
            self._qml_news_document = {"show": False}
            self._qml_news_revision += 1
            self._publish(force=True)
        else:
            self._qml_news_refresh(dialog)
        print("MUI_QML_NEWS_OPEN", flush=True)
        return True

    def _qml_news_focus(self):
        dialog = self._qml_news_target
        if dialog is None:
            return
        nav = getattr(self.panel.window(), "_lg_dpad_navigation", None)
        identity = getattr(nav, "selected_identity", None)
        focus = (
            str(identity[2]) if isinstance(identity, tuple)
            and len(identity) >= 3 and identity[:2] == ("popup", id(dialog))
            else ""
        )
        if focus != self._qml_news_focus_id:
            self._qml_news_focus_id = focus
            self._qml_news_document["focus"] = focus
            self._qml_news_revision += 1
            self._publish(force=True)

    def _qml_news_refresh(self, dialog):
        if self._qml_news_target is not dialog or self.stopping:
            return
        from PySide6.QtCore import QPoint
        origin = dialog.mapToGlobal(QPoint(0, 0))
        controls = []
        for key, name, label in (
            ("top", "back_to_top_button", "BACK TO TOP"),
            ("prev", "prev_button", "‹"),
            ("next", "next_button", "TURN PAGE  ›"),
            ("close", "close_button", "CLOSE"),
        ):
            button = getattr(dialog, name, None)
            if button is None or button.isHidden():
                continue
            pt = button.mapTo(dialog, QPoint(0, 0))
            controls.append({"id": key, "text": label,
                             "x": pt.x(), "y": pt.y(),
                             "w": button.width(), "h": button.height(),
                             "enabled": button.isEnabled()})

        left_index = dialog.spread_index * 2
        pages = dialog.pages
        # Keep existing Python pagination. The pixels and typography of
        # the newspaper itself are rendered by Qt Quick, not a PNG mirror.
        left = pages[left_index] if left_index < len(pages) else ""
        right = pages[left_index + 1] if left_index + 1 < len(pages) else ""
        if not pages:
            left = "<p>Fetching article text...</p>"
        for n, (name, image) in enumerate(
                getattr(dialog, "article_image_resources", {}).items()):
            png = ROOT / ("qml_news_%d_%d.png" % (id(dialog), n))
            if not png.is_file():
                image.save(str(png), "PNG")
            left = left.replace(name, png.as_uri())
            right = right.replace(name, png.as_uri())
        current = min(left_index + 2, max(1, len(pages)))
        counter = ("Pages %d-%d of %d" %
                   (left_index + 1, current, len(pages))) if pages else "Loading article..."
        self._qml_news_document = {
            "show": True, "x": origin.x(), "y": origin.y(),
            "w": dialog.width(), "h": dialog.height(),
            "source": str(dialog.source), "headline": str(dialog.headline),
            "counter": counter,
            "left_html": left, "right_html": right,
            "buttons": controls, "focus": self._qml_news_focus_id,
            "dark": bool(dialog.spread_surface.property("morningui_oled_dark")),
        }
        self._qml_news_revision += 1
        self._publish(force=True)
        print("MUI_QML_NEWS_SPREAD", dialog.spread_index, len(pages), flush=True)

    def eventFilter(self, obj, event):
        # Newspaper is genuinely drawn in this layer. Do not add it to
        # popup-hide policy, and do not schedule a weather reveal on close.
        if (type(obj).__name__ == "OpenNewspaperDialog"
                and getattr(obj, "_mui_qml_native", False)
                and self._qml_news_target is obj):
            if event.type() == QEvent.Type.Show:
                if not getattr(obj, "_mui_cached_qml_pending", False):
                    QTimer.singleShot(0, lambda d=obj: self._qml_news_refresh(d)
                                      if self._qml_news_target is d else None)
            elif event.type() in (QEvent.Type.Hide, QEvent.Type.Destroy):
                self._qml_news_target = None
                self._qml_news_document = {"show": False}
                self._qml_news_focus_id = ""
                self._qml_news_revision += 1
                self._publish(force=True)
                print("MUI_QML_NEWS_CLOSED", flush=True)
            return False

        # Hide weather on popup Show. Reveal immediately after actual Hide.
        # Do not wait for a dashboard Paint event or arbitrary timeout.
        if isinstance(obj, QWidget) and obj is not self.panel.window() and (isinstance(obj, QDialog) or obj.isWindow()):
            if isinstance(obj, QDialog) or obj.windowType() in (
                Qt.WindowType.Popup, Qt.WindowType.Tool, Qt.WindowType.ToolTip
            ):
                if event.type() == QEvent.Type.Show:
                    key = id(obj)
                    self._popup_generation[key] = self._popup_generation.get(key, 0) + 1
                    self._popup_early.add(key)
                    if type(obj).__name__ == "OpenNewspaperDialog":
                        # MUI_NEWSPAPER_OPEN_AFTER_SHOW_V1
                        # Allow the newspaper's showEvent to finish preparing
                        # its article before hiding native weather.
                        generation = self._popup_generation[key]
                        QTimer.singleShot(5, lambda key=key, generation=generation:
                            self._publish(force=True) if (
                                not self.stopping
                                and key in self._popup_early
                                and self._popup_generation.get(key) == generation
                            ) else None)
                    else:
                        self._publish(force=True)
                elif (event.type() == QEvent.Type.Close and
                      type(obj).__name__ in (
                          "OpenNewspaperDialog", "WeatherRadarDialog",
                          "MLBBoxScoreDialog", "ESPNBoxScoreDialog")):
                    # Immediately hide the popup before its closeEvent
                    # performs worker cleanup and other operations.
                    # Qt will still run the original closeEvent.
                    if obj.isVisible():
                        obj.hide()
                        print(
                            "MUI_POPUP_HIDDEN_AT_CLOSE",
                            type(obj).__name__,
                            flush=True
                        )
                elif event.type() in (QEvent.Type.Hide, QEvent.Type.Destroy):
                    key = id(obj)
                    if event.type() == QEvent.Type.Hide and type(obj).__name__ in (
                            "OpenNewspaperDialog", "WeatherRadarDialog",
                            "MLBBoxScoreDialog", "ESPNBoxScoreDialog"):
                        self._mui_lat_hide_ns = time.monotonic_ns()
                        self._mui_lat_key = key
                        print("MUI_LAT HIDE name=%s ns=%d" % (
                            type(obj).__name__, self._mui_lat_hide_ns), flush=True)
                        self._mui_sample_gui_stall(self._mui_lat_hide_ns)
                    if key in self._popup_early:
                        generation = self._popup_generation.get(key, 0)
                        if (event.type() == QEvent.Type.Hide and
                                not self.stopping and
                                type(obj).__name__ in (
                                    "OpenNewspaperDialog", "WeatherRadarDialog",
                                    "MLBBoxScoreDialog", "ESPNBoxScoreDialog")):
                            # MUI_DEFER_REVEAL_V1: keep weather hidden until
                            # the existing guarded post-hide Qt callback executes.
                            # This callback is delayed by the real repaint backlog.
                            print("MUI_WEATHER_REVEAL_PENDING", flush=True)
                        # Preserve the existing delayed safety check.
                        # MUI_NEWSPAPER_ZERO_REVEAL_V1
                        # Newspaper: next event-loop turn (0 ms).
                        # Other popups: retain their original 15 ms delay.
                        reveal_delay_ms = 1 if type(obj).__name__ == "OpenNewspaperDialog" else 15
                        QTimer.singleShot(reveal_delay_ms, lambda key=key, generation=generation:
                            self._popup_hide_finished(key, generation))
        return False

    def _mui_sample_gui_stall(self, hide_ns):
        # Diagnostic only: background thread never calls Qt.
        import collections
        import sys
        import threading

        self._mui_stall_trials = getattr(
            self, "_mui_stall_trials", 0
        ) + 1

        if self._mui_stall_trials > 4:
            return

        gui_ident = threading.get_ident()
        gui_tid = threading.get_native_id()
        trial = self._mui_stall_trials

        def sampler():
            counts = collections.Counter()
            observed = []
            first = None

            for _ in range(36):
                time.sleep(0.025)

                elapsed = (
                    time.monotonic_ns() - hide_ns
                ) / 1e6

                if first is None:
                    first = elapsed

                frame = sys._current_frames().get(gui_ident)
                chain = []

                for _ in range(4):
                    if frame is None:
                        break

                    chain.append("%s:%s:%d" % (
                        Path(frame.f_code.co_filename).name,
                        frame.f_code.co_name,
                        frame.f_lineno
                    ))

                    frame = frame.f_back

                try:
                    wchan = Path(
                        "/proc/self/task/%d/wchan" % gui_tid
                    ).read_text().strip()
                except OSError:
                    wchan = "?"

                signature = (" <= ".join(chain), wchan)
                counts[signature] += 1
                observed.append(elapsed)

                finished = getattr(
                    self, "_mui_last_callback_ns", 0
                )

                if finished >= hide_ns:
                    break

            print(
                "MUI_STALL_SUMMARY trial=%d first_sample_ms=%.1f "
                "samples=%d last_sample_ms=%.1f" % (
                    trial,
                    first or -1,
                    len(observed),
                    observed[-1] if observed else -1
                ),
                flush=True
            )

            for (stack, wchan), count in counts.most_common(6):
                print(
                    "MUI_STALL_STACK trial=%d samples=%d "
                    "wchan=%s stack=%s" % (
                        trial, count, wchan, stack
                    ),
                    flush=True
                )

        threading.Thread(
            target=sampler,
            name="mui-stall-sampler",
            daemon=True
        ).start()

    def _popup_hide_finished(self, key, generation):
        if key == getattr(self, "_mui_lat_key", None):
            self._mui_last_callback_ns = time.monotonic_ns()
            print("MUI_LAT CALLBACK elapsed_ms=%.2f" % (
                (time.monotonic_ns()-self._mui_lat_hide_ns)/1e6), flush=True)
        if self.stopping or self._popup_generation.get(key) != generation:
            return
        self._popup_generation.pop(key, None)
        self._popup_early.discard(key)
        self._publish(force=True)

    def _visible(self, closing_popup=None):
        if self._popup_early:
            return False
        panel = self.panel
        if not panel.isVisible() or len(self.cards) != 9:
            return False
        dashboard = panel.window()
        if hasattr(dashboard, "page_stack") and hasattr(dashboard, "dashboard_viewport"):
            if dashboard.page_stack.currentWidget() is not dashboard.dashboard_viewport:
                return False
        try:
            from ui import oled_palette_targets
            if getattr(oled_palette_targets, "_ACTIVE", False):
                return False
        except ImportError:
            pass
        app = QApplication.instance()
        modal = app.activeModalWidget()
        popup = app.activePopupWidget()
        if (modal is not None and modal is not closing_popup) or (
                popup is not None and popup is not closing_popup):
            return False
        for w in app.topLevelWidgets():
            if w is dashboard or w is closing_popup or not w.isVisible():
                continue
            # Newspaper, radar, scoreboards, color picker, and any other app dialog.
            if w.isWindow() and (isinstance(w, QDialog) or
                                 w.windowType() in (Qt.WindowType.Popup, Qt.WindowType.Tool, Qt.WindowType.ToolTip)):
                return False
        return True

    def _selected(self):
        root = self.panel.window()
        navigation = getattr(root, "_lg_dpad_navigation", None)
        identity = getattr(navigation, "selected_identity", None)
        if isinstance(identity, tuple) and len(identity) > 1 and identity[0] == "weather":
            for i, row in enumerate(self.panel.row_widgets):
                if identity[1] == id(row):
                    return i
        return -1

    def update_cards(self):
        panel = self.panel
        if not (panel.current_rows and panel.visible_rows and panel.isVisible()):
            return
        rows = panel.row_widgets
        if len(rows) != 9 or not all(r.isVisible() and r.width() >= 50 for r in rows):
            return
        try:
            signature = []
            data = []
            for i, row in enumerate(rows):
                mode = _v5w_mode(row)
                phase = _v41_border_phase(row)
                wind = _v6_cloud_speed_multiplier(getattr(row, "weather_data", None))
                pt = row.mapToGlobal(row.rect().topLeft())
                # Only regenerate label PNGs if the displayed data or its geometry changes.
                key = (pt.x(), pt.y(), row.width(), row.height(), mode, phase, wind,
                       row.hour_label.text(), row.temp_label.text(),
                       row.precipitation_detail_label.text(),
                       getattr(row, "solar_detail_text", ""),
                       row.hour_label.geometry().getRect(), row.temp_label.geometry().getRect(),
                       row.precipitation_detail_label.geometry().getRect())
                signature.append(key)
                png = ROOT / f"card_{i}.png"
                if (self.signature is None or self.signature[i] != key or not png.is_file()):
                    tmp = ROOT / f"card_{i}.new.png"
                    if not _v41_foreground_image(row, tmp):
                        raise RuntimeError(f"Unable to render foreground card {i}")
                    tmp.replace(png)
                data.append({"i": i, "x": pt.x(), "y": pt.y(),
                             "w": row.width(), "h": row.height(),
                             "v5w_mode": mode, "phase": phase,
                             "wind": float(wind),
                             "url": png.as_uri() + "?v=" + str(png.stat().st_mtime_ns)})
            signature = tuple(signature)
            if signature != self.signature:
                self.signature = signature
                self.cards = data
                self.version += 1
                self._publish(force=True)
                print("NATIVE_HOURLY_CARDS", len(data), rows[0].hour_label.text(), flush=True)
        except Exception as exc:
            print("NATIVE_HOURLY_CARD_ERROR", repr(exc), flush=True)
            if not self.ready:
                self._fallback()

    def _publish(self, force=False, closing_popup=None):
        if not self.cards:
            return
        show = self._visible(closing_popup=closing_popup)
        _mui_ns = getattr(self, "_mui_lat_hide_ns", 0)
        if _mui_ns and 0 <= time.monotonic_ns()-_mui_ns < 2_000_000_000:
            _mui_app = QApplication.instance()
            print("MUI_LAT POLICY elapsed_ms=%.2f show=%s pending=%d modal=%s popup=%s" % (
                (time.monotonic_ns()-_mui_ns)/1e6, show,
                len(self._popup_early), bool(_mui_app.activeModalWidget()),
                bool(_mui_app.activePopupWidget())), flush=True)
        selected = self._selected() if show else -1
        policy = (show, selected)
        now = time.monotonic()
        if not force and policy == self.last_policy and now - self.last_write < 0.65:
            return
        self.last_policy = policy
        self.last_write = now
        left = min(c["x"] for c in self.cards)
        top = min(c["y"] for c in self.cards)
        right = max(c["x"] + c["w"] for c in self.cards)
        bottom = max(c["y"] + c["h"] for c in self.cards)
        document = {"epoch_ms": int(time.time() * 1000),
                    "version": self.version, "show": show, "selected": selected,
                    "x": left, "y": top, "w": right - left, "h": bottom - top,
                    "cards": [{**c, "x": c["x"] - left, "y": c["y"] - top} for c in self.cards]}
        screen = QApplication.primaryScreen()
        geometry = (screen.geometry() if screen is not None
                    else self.panel.window().geometry())
        document["display_x"] = geometry.x()
        document["display_y"] = geometry.y()
        document["display_w"] = geometry.width()
        document["display_h"] = geometry.height()
        document["newspaper"] = self._qml_news_document
        document["newspaper_revision"] = self._qml_news_revision
        temp = ROOT / "state.tmp"
        temp.write_text(json.dumps(document, separators=(",", ":")))
        temp.replace(ROOT / "state.json")
        _mui_ns = getattr(self, "_mui_lat_hide_ns", 0)
        if _mui_ns and 0 <= time.monotonic_ns()-_mui_ns < 2_000_000_000:
            print("MUI_LAT WRITE elapsed_ms=%.2f show=%s" % (
                (time.monotonic_ns()-_mui_ns)/1e6, show), flush=True)

    def _launch(self):
        if self.process or self.failed or not self.cards:
            return
        try:
            binpath = next((p for p in subprocess.check_output(
                ["dpkg", "-L", "qmlscene-qt6"], text=True).splitlines()
                if p.endswith("/qmlscene") and os.access(p, os.X_OK)), None)
            if not binpath or not QML.is_file():
                raise RuntimeError("System Qt QML executable or layer scene unavailable")
            proc = QProcess(self)
            env = QProcessEnvironment.systemEnvironment()
            for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH", "LD_LIBRARY_PATH", "QT_SCALE_FACTOR"):
                env.remove(key)
            for key, value in {
                "LC_ALL": "C.UTF-8", "QT_QPA_PLATFORM": "wayland",
                "QT_WAYLAND_SHELL_INTEGRATION": "layer-shell",
                "QSG_RENDER_LOOP": "threaded", "QSG_RHI_BACKEND": "opengl",
                "QML_XHR_ALLOW_FILE_READ": "1",
                "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}",
                "WAYLAND_DISPLAY": "wayland-0",
            }.items():
                env.insert(key, value)
            proc.setProcessEnvironment(env)
            proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            proc.readyReadStandardOutput.connect(self._read_output)
            proc.finished.connect(lambda *_args: self._fallback())
            proc.start(binpath, ["--transparent", str(QML)])
            if not proc.waitForStarted(1800):
                raise RuntimeError("Native Qt renderer failed to start")
            self.process = proc
            self.started_at = time.monotonic()
            print("NATIVE_HOURLY_START", proc.processId(), flush=True)
        except Exception as exc:
            print("NATIVE_HOURLY_START_ERROR", repr(exc), flush=True)
            self._fallback()

    def _read_output(self):
        if not self.process:
            return
        self.line_buffer += bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        while "\n" in self.line_buffer:
            line, self.line_buffer = self.line_buffer.split("\n", 1)
            if "NATIVE_HOURLY_CARDS_READY" in line and not self.ready:
                self.ready = True
                for row in self.panel.row_widgets:
                    row.timer.stop()  # Old Python animation is now truly off.
                (ROOT / "ready").write_text(str(time.time()))
                print("NATIVE_HOURLY_ACTIVE: 9 independent Qt cards; old timers stopped", flush=True)
            elif "error" in line.lower() or "failed" in line.lower():
                print("NATIVE_HOURLY_QML:", line[-500:], flush=True)

    def sync(self):
        if self.failed or self.stopping:
            return
        if not self.cards:
            self.update_cards()
        if self.cards and self.process is None:
            self._publish(force=True)
            self._launch()
        if self.process is not None and not self.ready and time.monotonic() - self.started_at > 12:
            print("NATIVE_HOURLY_TIMEOUT: native renderer never became ready", flush=True)
            self._fallback()
            return
        if self.ready:
            self._qml_news_focus()
            self._publish()

    def _fallback(self):
        if self.stopping or self.failed:
            return
        self.failed = True
        self.ready = False
        (ROOT / "ready").unlink(missing_ok=True)
        # Native-only: do not restart old weather timers.
        self.tick.stop()
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
        print("NATIVE_HOURLY_FAILED: native-only mode, legacy disabled", flush=True)

    def shutdown(self):
        self.stopping = True
        QApplication.instance().removeEventFilter(self)
        (ROOT / "state.json").unlink(missing_ok=True)
        (ROOT / "ready").unlink(missing_ok=True)
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(800):
                self.process.kill()
                self.process.waitForFinished(300)


def install(weather_panel_class):
    if getattr(weather_panel_class, "_native_hourly_v1_installed", False):
        return
    old_init = weather_panel_class.__init__
    old_update = weather_panel_class.update_weather_rows

    def init(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        for row in self.row_widgets:
            row.timer.stop()
        self._native_hourly_v1 = NativeHourly(self)

    def update(self, rows):
        result = old_update(self, rows)
        state = getattr(self, "_native_hourly_v1", None)
        if state:
            QTimer.singleShot(100, state.update_cards)
        return result

    weather_panel_class.__init__ = init
    weather_panel_class.update_weather_rows = update
    weather_panel_class._native_hourly_v1_installed = True
