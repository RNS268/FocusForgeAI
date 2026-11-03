from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class SessionHistoryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Session History")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)

        layout.addWidget(QLabel("No study sessions recorded yet."))
        layout.addWidget(QPushButton("Export CSV"))
