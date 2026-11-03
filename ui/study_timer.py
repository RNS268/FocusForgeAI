from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton


class StudyTimerPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Study Timer")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)

        layout.addWidget(QLabel("00:25:00"))

        controls = QHBoxLayout()
        controls.addWidget(QPushButton("Start"))
        controls.addWidget(QPushButton("Pause"))
        controls.addWidget(QPushButton("Resume"))
        layout.addLayout(controls)

        layout.addWidget(QLabel("Pomodoro: 25 min"))
        layout.addWidget(QLabel("Break: 5 min"))
        layout.addWidget(QLabel("Custom duration: 00:00"))
