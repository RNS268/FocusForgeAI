from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class AnalyticsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Analytics")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Focus timeline: no data yet"))
        layout.addWidget(QLabel("Distraction matrix: no data yet"))
        layout.addWidget(QLabel("Focus percentage: 0%"))
        layout.addWidget(QLabel("Distraction events: 0"))
        layout.addWidget(QLabel("Daily stats: unavailable"))
        layout.addWidget(QLabel("Weekly stats: unavailable"))
