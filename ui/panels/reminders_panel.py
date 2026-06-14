from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.auto_fit_label import AutoFitLabel


class ReminderItem(QWidget):
    def __init__(self, icon, text, today=False):
        super().__init__()

        self.today = today
        self.setObjectName("TodayReminderRow" if today else "UpcomingReminderRow")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout()
        layout.setContentsMargins(10 if today else 8, 5 if today else 3, 10 if today else 8, 5 if today else 3)
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

        layout.addWidget(icon_label, 14 if today else 11)
        layout.addWidget(text_label, 86 if today else 89)


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

        count_badge = QLabel("2 TODAY")
        count_badge.setObjectName("ReminderTodayBadge")
        count_badge.setAlignment(Qt.AlignCenter)
        count_badge.setFixedWidth(74)

        title_row.addWidget(title, 1)
        title_row.addWidget(count_badge)

        layout.addLayout(title_row)

        today_title = QLabel("TODAY")
        today_title.setObjectName("TodayReminderGroupTitle")
        today_title.setAlignment(Qt.AlignLeft)
        layout.addWidget(today_title)

        layout.addWidget(ReminderItem("🗑️", "Trash day today", today=True), 2)
        layout.addWidget(ReminderItem("🎉", "Zara's birthday today", today=True), 2)

        upcoming_title = QLabel("UPCOMING")
        upcoming_title.setObjectName("UpcomingReminderGroupTitle")
        upcoming_title.setAlignment(Qt.AlignLeft)
        layout.addWidget(upcoming_title)

        layout.addWidget(ReminderItem("🎂", "Rocky's birthday in 5 days"), 1)
        layout.addWidget(ReminderItem("🩺", "Sam doctor appointment in 2 days"), 1)

        layout.addStretch(1)