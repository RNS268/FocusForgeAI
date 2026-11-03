from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.attention_detector import AttentionDetector
from core.camera_manager import CameraManager
from core.distraction_engine import DistractionEngine, DistractionState
from core.eye_detector import EyeClosureDetector
from core.face_detector import FaceDetector, draw_face_overlays
from core.phone_detector import PhoneDetector
from core.status_reporter import StatusReporter
from ui.analytics import AnalyticsPage
from ui.dashboard import DashboardPage
from ui.live_monitor import LiveMonitorPage
from ui.session_history import SessionHistoryPage
from ui.settings import SettingsPage
from ui.study_timer import StudyTimerPage
from utils.logger import get_logger

ROOT = Path(__file__).resolve().parent.parent


class FocusForgeMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FocusForge AI")
        self.resize(1200, 760)
        self.logger = get_logger("ui")

        self.camera = CameraManager(device_index=0, width=640, height=480)
        self.face_detector = FaceDetector(model_path=ROOT / "models" / "face_landmarker.task")
        self.attention_detector = AttentionDetector()
        self.eye_detector = EyeClosureDetector()
        self.phone_detector = PhoneDetector(model_path=ROOT / "models" / "yolov8n.pt")
        self.distraction_engine = DistractionEngine(history_length=5)
        self.status_reporter = StatusReporter(base_url="http://127.0.0.1:8081")

        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._refresh_live_monitor)
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._publish_status)
        self._is_running = False

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        nav = QVBoxLayout()
        nav.setSpacing(8)

        pages = {
            "Dashboard": DashboardPage(),
            "Live Monitor": LiveMonitorPage(),
            "Analytics": AnalyticsPage(),
            "Study Timer": StudyTimerPage(),
            "Session History": SessionHistoryPage(),
            "Settings": SettingsPage(),
        }

        self.stack = QStackedWidget()
        for page in pages.values():
            self.stack.addWidget(page)

        self.live_page = pages["Live Monitor"]
        self.live_page.set_callbacks(self._start_camera, self._reconnect_camera)

        for index, name in enumerate(pages):
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, idx=index: self.stack.setCurrentIndex(idx))
            nav.addWidget(btn)

        root.addLayout(nav, 1)
        root.addWidget(self.stack, 5)

    def _start_camera(self) -> None:
        if self._is_running:
            return
        if not self.camera.start():
            self.logger.error(self.camera.error_message)
            self.live_page.set_status(
                "Camera status: error",
                "Face detection: unavailable",
                "Phone detection: unavailable",
                "FPS: 0.0",
                "State: UNKNOWN",
            )
            return
        self._is_running = True
        self._monitor_timer.start(33)
        self._status_timer.start(1000)
        self.logger.info("UI camera loop started")

    def _reconnect_camera(self) -> None:
        self.camera.reconnect()
        if self.camera.status.value == "connected":
            self.logger.info("UI camera reconnected")

    def _refresh_live_monitor(self) -> None:
        frame = self.camera.get_latest_frame()
        if frame is None:
            self.live_page.update_frame(None)
            return

        display = frame.copy()
        face_result = self.face_detector.detect(display)
        if self.face_detector.available:
            draw_face_overlays(display, face_result, draw_all_landmarks=True)

        attention = self.attention_detector.classify(face_result, display.shape[1], display.shape[0], time.perf_counter())
        eye_metrics = self.eye_detector.detect(face_result, time.perf_counter())
        phone_result = self.phone_detector.detect(display)
        decision = self.distraction_engine.update(
            attention.state,
            eye_metrics.state,
            phone_detected=phone_result.detected,
            phone_confidence=phone_result.confidence,
            face_count=face_result.face_count,
            explanation=attention.explanation,
        )

        if self.face_detector.available:
            face_text = f"Face detection: {face_result.face_count} face(s)"
        else:
            face_text = f"Face detection: unavailable ({self.face_detector.error_message})"

        phone_text = (
            f"Phone detection: {phone_result.label} ({phone_result.confidence:.2f})"
            if phone_result.available and phone_result.detected
            else "Phone detection: unavailable"
            if not phone_result.available
            else "Phone detection: none"
        )

        self.live_page.set_status(
            f"Camera status: {self.camera.status.value}",
            face_text,
            phone_text,
            f"FPS: {self.camera.measured_fps:.1f}",
            f"State: {decision.state.value.upper()}",
        )

        cv2.putText(
            display,
            f"Attention: {attention.state.value}",
            (10, display.shape[0] - 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            display,
            f"Eyes: {eye_metrics.state.value}",
            (10, display.shape[0] - 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 165, 255),
            1,
            cv2.LINE_AA,
        )

        self.live_page.update_frame(display)

    def _publish_status(self) -> None:
        camera_state = self.camera.status.value if hasattr(self.camera.status, "value") else "offline"
        focus_score = 0
        distraction_count = 0
        if self.distraction_engine._history:
            states = [d.state for d in self.distraction_engine._history]
            focused = sum(1 for state in states if state == DistractionState.FOCUSED)
            focus_score = int((focused / max(1, len(states))) * 100)
            distraction_count = sum(1 for state in states if state != DistractionState.FOCUSED)
        self.status_reporter.publish(
            focus_score=focus_score,
            distraction_count=distraction_count,
            session_active=self.camera.status.value == "connected",
            camera_status=camera_state,
            face_status="ready" if self.face_detector.available else "not_ready",
            phone_status="none",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FocusForgeMainWindow()
    window.show()
    sys.exit(app.exec())
