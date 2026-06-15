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

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 7, 14, 8)
        layout.setSpacing(5)
        self.setLayout(layout)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title = QLabel("REMINDERS")
        title.setObjectName("RemindersTitle")
        title.setAlignment(Qt.AlignLeft)

        title_row.addWidget(title, 1)

        layout.addLayout(title_row)

        today_title = QLabel("TODAY")
        today_title.setObjectName("TodayReminderGroupTitle")
        today_title.setAlignment(Qt.AlignLeft)
        layout.addWidget(today_title)

        layout.addWidget(
            ReminderItem(
                "🗑️",
                "Trash day today",
                today=True,
                show_reminder_button=True,
            ),
            2,
        )
        layout.addWidget(
            ReminderItem(
                "🎉",
                "Zara's birthday today",
                today=True,
                show_reminder_button=True,
            ),
            2,
        )

        upcoming_title = QLabel("UPCOMING")
        upcoming_title.setObjectName("UpcomingReminderGroupTitle")
        upcoming_title.setAlignment(Qt.AlignLeft)
        layout.addWidget(upcoming_title)

        layout.addWidget(ReminderItem("🎂", "Rocky's birthday in 5 days"), 1)
        layout.addWidget(ReminderItem("🩺", "Sam doctor appointment in 2 days"), 1)

        layout.addStretch(1)