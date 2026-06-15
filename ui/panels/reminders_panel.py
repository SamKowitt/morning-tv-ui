from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QTime, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from services.pushover_notifier import send_pushover_notification
from ui.auto_fit_label import AutoFitLabel


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

        layout = QHBoxLayout()
        layout.setContentsMargins(
            10 if today else 8,
            5 if today else 3,
            10 if today else 8,
            5 if today else 3,
        )
        layout.setSpacing(8 if today else 6)
        self.setLayout(layout)

        icon_label = QLabel(icon)
        icon_label.setObjectName("TodayReminderIcon" if today else "UpcomingReminderIcon")
        icon_label.setAlignment(Qt.AlignCenter)

        text_label = AutoFitLabel(
            text,
            min_size=9 if today else 7,
            max_size=18 if today else 11,
            bold=today,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
            word_wrap=False,
        )
        text_label.setObjectName("TodayReminderText" if today else "UpcomingReminderText")

        layout.addWidget(icon_label, 12 if today else 11)
        layout.addWidget(text_label, 58 if today and show_reminder_button else 86)

        if today and show_reminder_button:
            send_button = QPushButton("Send Reminder")
            send_button.setObjectName("ReminderSendButton")
            send_button.setCursor(Qt.PointingHandCursor)
            send_button.setFixedWidth(92)
            send_button.clicked.connect(self.open_reminder_time_popup)

            layout.addStretch(1)
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

        QMessageBox.information(
            self,
            "Reminder Scheduled",
            f"Reminder scheduled for {selected_time_text}.",
        )

        print(f"Scheduled reminder for '{self.reminder_text}' at {scheduled_time}")


class RemindersPanel(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("RemindersCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.dynamic_widgets = []

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(14, 7, 14, 8)
        self.main_layout.setSpacing(5)
        self.setLayout(self.main_layout)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title = QLabel("REMINDERS")
        title.setObjectName("RemindersTitle")
        title.setAlignment(Qt.AlignLeft)

        title_row.addWidget(title, 1)
        self.main_layout.addLayout(title_row)

        self.today_title = QLabel("TODAY")
        self.today_title.setObjectName("TodayReminderGroupTitle")
        self.today_title.setAlignment(Qt.AlignLeft)
        self.main_layout.addWidget(self.today_title)

        self.set_calendar_error("Connect Apple Calendar in Settings")

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

    def update_calendar_events(self, events):
        today_events = [event for event in events if getattr(event, "starts_today", False)]
        upcoming_events = [event for event in events if not getattr(event, "starts_today", False)]

        today_widgets = []
        upcoming_widgets = []

        if today_events:
            for event in today_events[:3]:
                text = f"{event.title} - {event.when_text}"
                today_widgets.append(
                    (
                        ReminderItem(
                            "📅",
                            text,
                            today=True,
                            show_reminder_button=True,
                        ),
                        2,
                    )
                )
        else:
            today_widgets.append((ReminderItem("📅", "No Apple Calendar events today", today=True), 2))

        if upcoming_events:
            for event in upcoming_events[:5]:
                text = f"{event.title} - {event.when_text}"
                upcoming_widgets.append((ReminderItem("🗓️", text), 1))
        else:
            upcoming_widgets.append((ReminderItem("🗓️", "No upcoming Apple Calendar events"), 1))

        self.rebuild_calendar_rows(today_widgets, upcoming_widgets)

    def set_calendar_error(self, message):
        today_widgets = [
            (ReminderItem("⚠️", message, today=True), 2),
        ]

        upcoming_widgets = [
            (ReminderItem("🗓️", "Apple Calendar events will appear here"), 1),
        ]

        self.rebuild_calendar_rows(today_widgets, upcoming_widgets)
