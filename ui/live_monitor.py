from __future__ import annotations

import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class LiveMonitorPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.start_callback = None
        self.reconnect_callback = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Live Monitoring")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)

        self.camera_status = QLabel("Camera status: not started")
        self.face_status = QLabel("Face detection: waiting")
        self.phone_status = QLabel("Phone detection: unavailable")
        self.fps_status = QLabel("FPS: 0.0")
        self.state_status = QLabel("State: UNKNOWN")

        layout.addWidget(self.camera_status)
        layout.addWidget(self.face_status)
        layout.addWidget(self.phone_status)
        layout.addWidget(self.fps_status)
        layout.addWidget(self.state_status)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start Camera")
        self.reconnect_button = QPushButton("Reconnect")
        controls.addWidget(self.start_button)
        controls.addWidget(self.reconnect_button)
        layout.addLayout(controls)

        self.video_label = QLabel("Webcam feed placeholder")
        self.video_label.setMinimumHeight(420)
        self.video_label.setStyleSheet("background: #121a22; color: white; border: 1px solid #2a3742; border-radius: 8px; qproperty-alignment: AlignCenter;")
        layout.addWidget(self.video_label)

    def set_callbacks(self, start_callback, reconnect_callback) -> None:
        self.start_callback = start_callback
        self.reconnect_callback = reconnect_callback
        if self.start_callback is not None:
            self.start_button.clicked.connect(self.start_callback)
        if self.reconnect_callback is not None:
            self.reconnect_button.clicked.connect(self.reconnect_callback)

    def set_status(self, camera_status: str, face_status: str, phone_status: str, fps_status: str, state_status: str) -> None:
        self.camera_status.setText(camera_status)
        self.face_status.setText(face_status)
        self.phone_status.setText(phone_status)
        self.fps_status.setText(fps_status)
        self.state_status.setText(state_status)

    def update_frame(self, frame) -> None:
        if frame is None:
            self.video_label.setText("No frames available")
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb.shape
        bytes_per_line = channel * width
        qimage = QImage(rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self.video_label.setText("")
