from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.auto_fit_label import AutoFitLabel


class ReminderItem(QWidget):
    def __init__(self, icon, text, today=False, show_reminder_button=False):
        super().__init__()

        self.today = today
        self.reminder_text = text
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
            send_button.clicked.connect(self.send_reminder)

            layout.addStretch(1)
            layout.addWidget(send_button, 0, Qt.AlignRight | Qt.AlignVCenter)

    def send_reminder(self):
        print(f"Send Reminder clicked for: {self.reminder_text}")


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
                text = f"{event.when_text}  •  {event.title}"
                today_widgets.append((ReminderItem("📅", text, today=True), 2))
        else:
            today_widgets.append((ReminderItem("📅", "No Apple Calendar events today", today=True), 2))

        if upcoming_events:
            for event in upcoming_events[:5]:
                text = f"{event.when_text}  •  {event.title}"
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
