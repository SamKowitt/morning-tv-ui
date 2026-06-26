import random
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QTime, QTimer, QRectF, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from services.pushover_notifier import send_pushover_notification
from ui.auto_fit_label import AutoFitLabel
from ui.newspaper_chrome import draw_stacked_newspaper_panel


class ReminderTimeDialog(QDialog):
    def __init__(self, reminder_text, parent=None):
        super().__init__(parent)

        self.reminder_text = reminder_text

        self.setObjectName("ReminderTimeDialog")
        self.setWindowTitle("Set Reminder Time")
        self.setModal(True)
        self.setFixedSize(390, 210)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        self.setLayout(layout)

        title = QLabel("SET REMINDER")
        title.setObjectName("ReminderDialogTitle")
        title.setAlignment(Qt.AlignCenter)

        event_label = QLabel(reminder_text)
        event_label.setObjectName("ReminderDialogEvent")
        event_label.setAlignment(Qt.AlignCenter)
        event_label.setWordWrap(True)

        prompt = QLabel("Select a time to receive this reminder:")
        prompt.setObjectName("ReminderDialogPrompt")
        prompt.setAlignment(Qt.AlignLeft)

        self.time_input = QTimeEdit()
        self.time_input.setObjectName("ReminderTimeInput")
        self.time_input.setDisplayFormat("h:mm AP")
        self.time_input.setTime(QTime(17, 0))
        self.time_input.setAlignment(Qt.AlignCenter)
        self.time_input.setMinimumHeight(42)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.setObjectName("ReminderDialogButtons")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(event_label)
        layout.addWidget(prompt)
        layout.addWidget(self.time_input)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog#ReminderTimeDialog {
                background: #f5ead7;
                border: 2px solid rgba(83, 59, 33, 0.35);
                border-radius: 18px;
            }

            QLabel#ReminderDialogTitle {
                color: #2d2114;
                background: transparent;
                font-size: 20px;
                font-weight: 1000;
                letter-spacing: 1px;
            }

            QLabel#ReminderDialogEvent {
                color: rgba(45, 33, 20, 0.88);
                background: transparent;
                font-size: 13px;
                font-weight: 900;
            }

            QLabel#ReminderDialogPrompt {
                color: rgba(45, 33, 20, 0.78);
                background: transparent;
                font-size: 12px;
                font-weight: 800;
            }

            QTimeEdit#ReminderTimeInput {
                color: #2d2114;
                background: rgba(255, 255, 255, 0.78);
                border: 1px solid rgba(83, 59, 33, 0.32);
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 20px;
                font-weight: 1000;
                selection-background-color: rgba(196, 139, 61, 0.35);
            }

            QTimeEdit#ReminderTimeInput::up-button,
            QTimeEdit#ReminderTimeInput::down-button {
                width: 22px;
                border: none;
                background: transparent;
            }

            QDialogButtonBox#ReminderDialogButtons QPushButton {
                color: #2d2114;
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(83, 59, 33, 0.28);
                border-radius: 10px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: 900;
                min-width: 78px;
            }

            QDialogButtonBox#ReminderDialogButtons QPushButton:hover {
                background: rgba(255, 255, 255, 0.92);
            }
        """)

    def selected_qtime(self):
        return self.time_input.time()

    def selected_time_text(self):
        return self.time_input.time().toString("h:mm AP")


class ReminderItem(QWidget):
    def __init__(self, icon, text, today=False, show_reminder_button=False):
        super().__init__()

        self.today = today
        self.reminder_text = text
        self.active_timers = []

        self.setObjectName("TodayReminderRow" if today else "UpcomingReminderRow")
        self.setAttribute(Qt.WA_StyledBackground, True)

        if today:
            self.setMinimumHeight(40)
        else:
            self.setMinimumHeight(28)

        self.setStyleSheet("""
            QWidget#TodayReminderRow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(243, 216, 157, 0.78),
                    stop: 0.70 rgba(247, 229, 188, 0.35),
                    stop: 1 rgba(247, 229, 188, 0.08)
                );
                border: none;
                border-left: 3px solid rgba(150, 96, 31, 0.78);
                border-top: 1px solid rgba(55, 42, 25, 0.44);
                border-bottom: 1px solid rgba(55, 42, 25, 0.20);
            }

            QWidget#UpcomingReminderRow {
                background: transparent;
                border: none;
                border-top: 1px solid rgba(55, 42, 25, 0.38);
            }

            QLabel#TodayReminderIcon,
            QLabel#UpcomingReminderIcon {
                background: transparent;
                color: #4c3420;
                font-size: 12px;
            }

            QLabel#ReminderMeta {
                background: transparent;
                color: #9c6424;
                font-family: "Times New Roman";
                font-size: 8px;
                font-weight: 1000;
                letter-spacing: 1.1px;
            }

            QLabel#TodayReminderText {
                background: transparent;
                color: #17100a;
                font-family: "Georgia";
                font-size: 14px;
                font-weight: 1000;
            }

            QLabel#UpcomingReminderText {
                background: transparent;
                color: #302116;
                font-family: "Georgia";
                font-size: 10px;
                font-weight: 800;
            }

            QPushButton#ReminderSendButton,
            QPushButton#UpcomingReminderSendButton {
                color: #4d351b;
                background: rgba(255, 248, 236, 0.46);
                border: 1px solid rgba(83, 59, 33, 0.50);
                border-radius: 3px;
                padding: 1px 7px;
                font-family: "Times New Roman";
                font-size: 8px;
                font-weight: 1000;
            }

            QPushButton#ReminderSendButton:hover,
            QPushButton#UpcomingReminderSendButton:hover {
                background: rgba(255, 248, 236, 0.80);
                border-color: rgba(83, 59, 33, 0.76);
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(
            7 if today else 8,
            3 if today else 2,
            8,
            3 if today else 2,
        )
        layout.setSpacing(7 if today else 6)
        self.setLayout(layout)

        icon_label = QLabel(icon)
        icon_label.setObjectName(
            "TodayReminderIcon" if today else "UpcomingReminderIcon"
        )
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedWidth(20)

        text_column = QWidget()
        text_column.setStyleSheet("background: transparent; border: none;")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_column.setLayout(text_layout)

        text_label = AutoFitLabel(
            text,
            min_size=8 if today else 7,
            max_size=15 if today else 11,
            bold=True,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
            word_wrap=False,
        )
        text_label.setObjectName(
            "TodayReminderText" if today else "UpcomingReminderText"
        )

        text_layout.addWidget(text_label, 1)

        layout.addWidget(icon_label)
        layout.addWidget(text_column, 1)

        if show_reminder_button:
            send_button = QPushButton("Set Reminder")
            send_button.setObjectName(
                "ReminderSendButton" if today else "UpcomingReminderSendButton"
            )
            send_button.setCursor(Qt.PointingHandCursor)
            send_button.setFixedSize(88 if today else 82, 21 if today else 20)
            send_button.clicked.connect(self.open_reminder_time_popup)

            layout.addWidget(send_button, 0, Qt.AlignRight | Qt.AlignVCenter)

    def open_reminder_time_popup(self):
        dialog = ReminderTimeDialog(self.reminder_text, self)

        if dialog.exec() == QDialog.Accepted:
            selected_qtime = dialog.selected_qtime()
            selected_time_text = dialog.selected_time_text()

            self.schedule_pushover_reminder(selected_qtime, selected_time_text)

    def schedule_pushover_reminder(self, selected_qtime, selected_time_text):
        now = datetime.now()

        scheduled_time = now.replace(
            hour=selected_qtime.hour(),
            minute=selected_qtime.minute(),
            second=0,
            microsecond=0,
        )

        if scheduled_time <= now:
            scheduled_time = scheduled_time + timedelta(days=1)

        delay_ms = int((scheduled_time - now).total_seconds() * 1000)

        timer = QTimer(self)
        timer.setSingleShot(True)

        def send_due_reminder():
            try:
                send_pushover_notification(
                    title=self.reminder_text,
                    message="Reminder",
                )
                print(f"Sent Pushover reminder: {self.reminder_text}")
            except Exception as error:
                print(f"Failed to send Pushover reminder: {error}")
            finally:
                if timer in self.active_timers:
                    self.active_timers.remove(timer)
                timer.deleteLater()

        timer.timeout.connect(send_due_reminder)
        timer.start(delay_ms)

        self.active_timers.append(timer)

        confirmation = QMessageBox(self)
        confirmation.setWindowTitle("Reminder Scheduled")
        confirmation.setIcon(QMessageBox.Information)
        confirmation.setText(f"Reminder scheduled for {selected_time_text}.")
        confirmation.setStyleSheet("""
            QMessageBox {
                background-color: #f5ead7;
                color: #2d2114;
                font-size: 14px;
                font-weight: 900;
            }

            QMessageBox QLabel {
                color: #2d2114;
                background: transparent;
                font-size: 14px;
                font-weight: 900;
            }

            QMessageBox QPushButton {
                background-color: #72542d;
                color: #f7f0df;
                border: 1px solid #4d351b;
                border-radius: 7px;
                padding: 5px 18px;
                font-size: 12px;
                font-weight: 900;
                min-width: 64px;
            }

            QMessageBox QPushButton:hover {
                background-color: #846236;
            }
        """)
        confirmation.exec()

        print(f"Scheduled reminder for '{self.reminder_text}' at {scheduled_time}")


class RemindersPanel(QWidget):
    hide_requested = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("RemindersCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet("""
            QWidget#RemindersCard {
                background: transparent;
                border: none;
                border-radius: 0px;
            }

            QWidget#RemindersCard QLabel {
                background: transparent;
            }

            QLabel#RemindersTitle {
                font-family: "Rockwell";
                font-size: 20px;
                font-weight: 900;
                color: #241a10;
                letter-spacing: 1px;
                padding: 2px 0px 0px 0px;
                border: none;
            }

            QFrame#RemindersHeaderRule {
                background: rgba(55, 42, 25, 185);
                border: none;
                min-height: 1px;
                max-height: 1px;
            }

            QPushButton#RemindersHideButton {
                color: #5e3f1c;
                background: rgba(255, 248, 236, 0.52);
                border: 1px solid rgba(83, 59, 33, 0.38);
                border-radius: 5px;
                padding: 1px 7px;
                font-family: "Times New Roman";
                font-size: 9px;
                font-weight: 900;
            }

            QPushButton#RemindersHideButton:hover {
                background: rgba(255, 248, 236, 0.88);
                border-color: rgba(83, 59, 33, 0.68);
            }

            QLabel#TodayReminderGroupTitle,
            QLabel#UpcomingReminderGroupTitle {
                font-family: "Times New Roman";
                font-size: 8px;
                font-weight: 1000;
                color: #9c6424;
                letter-spacing: 1.4px;
            }

            QWidget#ReminderSpacer {
                background: transparent;
                border: none;
            }
        """)

        self.dynamic_widgets = []
        self.all_today_events = []
        self.all_upcoming_events = []

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(12, 6, 12, 6)
        self.main_layout.setSpacing(3)
        self.setLayout(self.main_layout)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title = QLabel("REMINDERS")
        title.setObjectName("RemindersTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setMinimumHeight(28)
        title.setMaximumHeight(28)

        title_row.addWidget(title, 1)

        self.hide_button = QPushButton("Hide")
        self.hide_button.setObjectName("RemindersHideButton")
        self.hide_button.setCursor(Qt.PointingHandCursor)
        self.hide_button.setFixedHeight(20)
        self.hide_button.clicked.connect(self.hide_requested.emit)

        title_row.addWidget(
            self.hide_button,
            0,
            Qt.AlignRight | Qt.AlignVCenter,
        )

        header_rule = QFrame()
        header_rule.setObjectName("RemindersHeaderRule")
        header_rule.setFixedHeight(1)

        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addLayout(title_row)
        header_layout.addWidget(header_rule)

        self.main_layout.addLayout(header_layout)

        self.today_title = QLabel("TODAY")
        self.today_title.setObjectName("TodayReminderGroupTitle")
        self.today_title.setAlignment(Qt.AlignLeft)
        self.main_layout.addWidget(self.today_title)

        self.set_calendar_error("Connect Apple Calendar in Settings")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Match NewsCard exactly: let the shared newspaper renderer own
        # the entire visible card surface and its built-in shadow/fold.
        rect = self.rect().adjusted(1, 1, -1, -1)
        draw_stacked_newspaper_panel(painter, rect, seed=44)

    def clear_dynamic_widgets(self):
        for widget in self.dynamic_widgets:
            self.main_layout.removeWidget(widget)
            widget.deleteLater()

        self.dynamic_widgets = []

    def add_dynamic_widget(self, widget, stretch=1):
        self.dynamic_widgets.append(widget)
        self.main_layout.addWidget(widget, stretch)

    def rebuild_calendar_rows(self, today_widgets, upcoming_widgets):
        self.clear_dynamic_widgets()

        for widget, stretch in today_widgets:
            self.add_dynamic_widget(widget, stretch)

        upcoming_title = QLabel("UPCOMING")
        upcoming_title.setObjectName("UpcomingReminderGroupTitle")
        upcoming_title.setAlignment(Qt.AlignLeft)
        self.add_dynamic_widget(upcoming_title, 0)

        for widget, stretch in upcoming_widgets:
            self.add_dynamic_widget(widget, stretch)

        spacer = QWidget()
        spacer.setObjectName("ReminderSpacer")
        self.add_dynamic_widget(spacer, 1)

    def event_sort_key(self, event):
        value = getattr(event, "sort_date", None)

        if value is not None:
            return value

        return datetime.max.date()

    def event_text(self, event):
        title = str(getattr(event, "title", "") or "").strip()
        when_text = str(getattr(event, "when_text", "") or "").strip()

        if when_text:
            return f"{title} - {when_text}"

        return title

    def make_event_row(self, event, today):
        return ReminderItem(
            "📅" if today else "🗓️",
            self.event_text(event),
            today=today,
            show_reminder_button=True,
        )

    def make_overflow_row(self, count, group):
        plural = "event" if count == 1 else "events"
        label = f"{count} more {plural} {group}. Click to see details."

        button = QPushButton(label)
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(34)
        button.setStyleSheet("""
            QPushButton {
                background: rgba(114, 84, 45, 0.18);
                color: #4d351b;
                border: 1px solid rgba(83, 59, 33, 0.48);
                border-radius: 4px;
                padding: 4px 8px;
                font-family: "Times New Roman";
                font-size: 13px;
                font-weight: 1000;
                text-align: left;
            }

            QPushButton:hover {
                background: rgba(114, 84, 45, 0.30);
                border-color: rgba(83, 59, 33, 0.78);
            }
        """)
        button.clicked.connect(self.open_all_events_popup)

        return button

    def make_details_empty_row(self, text):
        label = QLabel(text)
        label.setObjectName("CalendarDetailsEmptyState")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumHeight(42)
        label.setStyleSheet("""
            QLabel#CalendarDetailsEmptyState {
                background: #72542d;
                color: #ffffff;
                border: 1px solid #4d351b;
                border-radius: 4px;
                padding: 6px 10px;
                font-family: "Georgia";
                font-size: 15px;
                font-weight: 1000;
            }
        """)
        return label

    def open_all_events_popup(self):
        dialog = QDialog(self)
        dialog.setObjectName("CalendarDetailsDialog")
        dialog.setModal(True)
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setAttribute(Qt.WA_StyledBackground, True)
        dialog.resize(620, 560)
        dialog.setStyleSheet("""
            QDialog#CalendarDetailsDialog {
                background: #f5ead7;
                border: none;
                border-radius: 14px;
            }

            QLabel#CalendarDetailsTitle {
                color: #2d2114;
                background: transparent;
                font-size: 20px;
                font-weight: 1000;
                letter-spacing: 0.8px;
            }

            QLabel#CalendarDetailsSection {
                color: #7a4d18;
                background: transparent;
                font-size: 11px;
                font-weight: 1000;
                letter-spacing: 1.2px;
            }

            QScrollArea {
                background: #fff8ec;
                border: none;
            }

            QWidget#CalendarDetailsContent {
                background: #fff8ec;
                border: none;
            }

            QScrollArea::viewport {
                background: #fff8ec;
                border: none;
            }
        """)

        root = QVBoxLayout()
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)
        dialog.setLayout(root)

        title = QLabel("CALENDAR EVENT DETAILS")
        title.setObjectName("CalendarDetailsTitle")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setObjectName("CalendarDetailsContent")
        content.setStyleSheet("""
            QWidget#CalendarDetailsContent {
                background: #fff8ec;
                border: none;
            }
        """)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(6)
        content.setLayout(content_layout)

        def detail_row(event, today):
            row = self.make_event_row(event, today=today)
            row.setStyleSheet("""
                QWidget#TodayReminderRow {
                    background: #f6dda3;
                    border: 1px solid #b58a48;
                    border-radius: 5px;
                }

                QWidget#UpcomingReminderRow {
                    background: #fff8ec;
                    border: 1px solid #d2b77f;
                    border-radius: 5px;
                }

                QLabel#TodayReminderIcon,
                QLabel#UpcomingReminderIcon,
                QLabel#TodayReminderText,
                QLabel#UpcomingReminderText {
                    color: #2d2114;
                    background: transparent;
                }

                QLabel#TodayReminderText {
                    font-family: "Georgia";
                    font-size: 15px;
                    font-weight: 1000;
                }

                QLabel#UpcomingReminderText {
                    font-family: "Times New Roman";
                    font-size: 13px;
                    font-weight: 800;
                }

                QPushButton#ReminderSendButton,
                QPushButton#UpcomingReminderSendButton {
                    background: #ead3a1;
                    color: #2d2114;
                    border: 1px solid #8c6938;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-family: "Times New Roman";
                    font-size: 10px;
                    font-weight: 1000;
                }

                QPushButton#ReminderSendButton:hover,
                QPushButton#UpcomingReminderSendButton:hover {
                    background: #f6e4ba;
                }
            """)
            return row

        today_heading = QLabel("TODAY")
        today_heading.setObjectName("CalendarDetailsSection")
        content_layout.addWidget(today_heading)

        if self.all_today_events:
            for event in self.all_today_events:
                content_layout.addWidget(detail_row(event, today=True))
        else:
            content_layout.addWidget(
                self.make_details_empty_row("No Events Today")
            )

        upcoming_heading = QLabel("UPCOMING")
        upcoming_heading.setObjectName("CalendarDetailsSection")
        content_layout.addSpacing(8)
        content_layout.addWidget(upcoming_heading)

        if self.all_upcoming_events:
            for event in self.all_upcoming_events:
                content_layout.addWidget(detail_row(event, today=False))
        else:
            content_layout.addWidget(
                self.make_details_empty_row("No Upcoming Events")
            )

        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)

        close_button = QPushButton("Close")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setStyleSheet("""
            QPushButton {
                background: #d8c7a4;
                color: #2d2114;
                border: 1px solid #8c6938;
                border-radius: 7px;
                padding: 5px 18px;
                font-size: 12px;
                font-weight: 1000;
            }

            QPushButton:hover {
                background: #eadab7;
            }
        """)
        close_button.clicked.connect(dialog.accept)

        close_row.addWidget(close_button)
        close_row.addStretch(1)
        root.addLayout(close_row)

        dialog.exec()

    def update_calendar_events(self, events):
        events = list(events or [])

        self.all_today_events = sorted(
            [
                event for event in events
                if bool(getattr(event, "starts_today", False))
            ],
            key=self.event_sort_key,
        )

        self.all_upcoming_events = sorted(
            [
                event for event in events
                if not bool(getattr(event, "starts_today", False))
            ],
            key=self.event_sort_key,
        )

        today_count = len(self.all_today_events)
        upcoming_count = len(self.all_upcoming_events)

        today_widgets = []
        upcoming_widgets = []

        if today_count > 3:
            for event in self.all_today_events[:2]:
                today_widgets.append(
                    (self.make_event_row(event, today=True), 2)
                )

            today_widgets.append(
                (
                    self.make_overflow_row(
                        today_count - 2,
                        "today",
                    ),
                    2,
                )
            )

        elif today_count:
            for event in self.all_today_events:
                today_widgets.append(
                    (self.make_event_row(event, today=True), 2)
                )

        else:
            today_widgets.append(
                (
                    ReminderItem(
                        "📅",
                        "No Events Today",
                        today=True,
                        show_reminder_button=False,
                    ),
                    2,
                )
            )

        if today_count > 3:
            # The Today overflow row uses the available card space. All
            # upcoming events remain available inside the details popup.
            pass

        elif today_count == 3:
            if upcoming_count == 1:
                upcoming_widgets.append(
                    (
                        self.make_event_row(
                            self.all_upcoming_events[0],
                            today=False,
                        ),
                        1,
                    )
                )
            elif upcoming_count > 1:
                upcoming_widgets.append(
                    (
                        self.make_overflow_row(
                            upcoming_count,
                            "upcoming",
                        ),
                        1,
                    )
                )

        elif today_count == 2:
            if upcoming_count <= 2:
                for event in self.all_upcoming_events:
                    upcoming_widgets.append(
                        (self.make_event_row(event, today=False), 1)
                    )
            elif upcoming_count > 2:
                upcoming_widgets.append(
                    (
                        self.make_event_row(
                            self.all_upcoming_events[0],
                            today=False,
                        ),
                        1,
                    )
                )
                upcoming_widgets.append(
                    (
                        self.make_overflow_row(
                            upcoming_count - 1,
                            "upcoming",
                        ),
                        1,
                    )
                )

        elif today_count == 1:
            if upcoming_count <= 3:
                for event in self.all_upcoming_events:
                    upcoming_widgets.append(
                        (self.make_event_row(event, today=False), 1)
                    )
            elif upcoming_count > 3:
                for event in self.all_upcoming_events[:2]:
                    upcoming_widgets.append(
                        (self.make_event_row(event, today=False), 1)
                    )

                upcoming_widgets.append(
                    (
                        self.make_overflow_row(
                            upcoming_count - 2,
                            "upcoming",
                        ),
                        1,
                    )
                )

        else:
            if upcoming_count <= 4:
                for event in self.all_upcoming_events:
                    upcoming_widgets.append(
                        (self.make_event_row(event, today=False), 1)
                    )
            else:
                for event in self.all_upcoming_events[:3]:
                    upcoming_widgets.append(
                        (self.make_event_row(event, today=False), 1)
                    )

                upcoming_widgets.append(
                    (
                        self.make_overflow_row(
                            upcoming_count - 3,
                            "upcoming",
                        ),
                        1,
                    )
                )

        if not upcoming_widgets:
            upcoming_widgets.append(
                (
                    ReminderItem(
                        "🗓️",
                        "No Upcoming Events",
                        today=False,
                        show_reminder_button=False,
                    ),
                    1,
                )
            )

        self.rebuild_calendar_rows(today_widgets, upcoming_widgets)

    def set_calendar_error(self, message):
        self.all_today_events = []
        self.all_upcoming_events = []

        today_widgets = [
            (ReminderItem("⚠️", message, today=True), 2),
        ]

        upcoming_widgets = [
            (ReminderItem("🗓️", "Calendar events will appear here"), 1),
        ]

        self.rebuild_calendar_rows(today_widgets, upcoming_widgets)
