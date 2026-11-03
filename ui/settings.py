from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QComboBox, QPushButton


class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Camera selection"))
        layout.addWidget(QComboBox())
        layout.addWidget(QCheckBox("Enable privacy mode"))
        layout.addWidget(QCheckBox("Save aggregate analytics to cloud"))
        layout.addWidget(QCheckBox("Show landmarks overlay"))
        layout.addWidget(QPushButton("Calibrate focus pose"))
        layout.addWidget(QPushButton("Reset local history"))
