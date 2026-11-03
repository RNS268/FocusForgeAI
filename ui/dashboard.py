from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame


class DashboardPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)

        cards = QFrame()
        cards_layout = QVBoxLayout(cards)
        cards_layout.addWidget(QLabel("Current focus score: 0%"))
        cards_layout.addWidget(QLabel("Current state: focused"))
        cards_layout.addWidget(QLabel("Study duration: 00:00:00"))
        cards_layout.addWidget(QLabel("Focused time: 00:00:00"))
        cards_layout.addWidget(QLabel("Distracted time: 00:00:00"))
        cards_layout.addWidget(QLabel("Recent activity: idle"))
        layout.addWidget(cards)
