"""Laptop webcam access with platform backends, threading, and reconnect."""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np

from utils.logger import get_logger
from utils.performance import FpsTracker

logger = get_logger("camera")


class CameraStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass(frozen=True)
class CameraDevice:
    index: int
    name: str
    available: bool


@dataclass
class CameraInfo:
    index: int
    width: int
    height: int
    backend: str
    status: CameraStatus
    error_message: str = ""


def _preferred_backend() -> int:
    if sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    if sys.platform.startswith("win"):
        return cv2.CAP_DSHOW
    return cv2.CAP_ANY


class CameraManager:
    """Owns a single OpenCV capture device.

    Frames are read on a background thread so later GUI work does not block.
    Video is never written to disk.
    """

    def __init__(
        self,
        device_index: int = 0,
        width: int = 640,
        height: int = 480,
        requested_fps: int = 30,
        buffer_size: int = 1,
        reconnect_attempts: int = 5,
        reconnect_delay_seconds: float = 1.5,
        fps_smoothing: float = 0.15,
    ) -> None:
        self.device_index = device_index
        self.width = width
        self.height = height
        self.requested_fps = requested_fps
        self.buffer_size = buffer_size
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay_seconds = reconnect_delay_seconds

        self._capture: Optional[cv2.VideoCapture] = None
        self._status = CameraStatus.DISCONNECTED
        self._error_message = ""
        self._backend_name = "unknown"
        self._lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._fps = FpsTracker(smoothing=fps_smoothing)
        self._actual_width = 0
        self._actual_height = 0

    @property
    def status(self) -> CameraStatus:
        return self._status

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def measured_fps(self) -> float:
        return self._fps.fps

    @property
    def frame_count(self) -> int:
        return self._fps.frame_count

    def info(self) -> CameraInfo:
        return CameraInfo(
            index=self.device_index,
            width=self._actual_width or self.width,
            height=self._actual_height or self.height,
            backend=self._backend_name,
            status=self._status,
            error_message=self._error_message,
        )

    @staticmethod
    def list_devices(max_index: int = 6) -> list[CameraDevice]:
        """Probe camera indexes. Opening a device may trigger OS permission prompts."""
        devices: list[CameraDevice] = []
        backend = _preferred_backend()
        for index in range(max_index):
            capture = cv2.VideoCapture(index, backend)
            opened = bool(capture.isOpened())
            name = f"Camera {index}"
            if opened:
                backend_name = capture.getBackendName()
                name = f"Camera {index} ({backend_name})"
            devices.append(CameraDevice(index=index, name=name, available=opened))
            capture.release()
        return devices

    def open(self) -> bool:
        """Open the configured camera. Returns True on success."""
        with self._lock:
            self._status = CameraStatus.CONNECTING
            self._error_message = ""
            self._release_unlocked()

            backend = _preferred_backend()
            capture = cv2.VideoCapture(self.device_index, backend)
            if not capture.isOpened():
                capture = cv2.VideoCapture(self.device_index, cv2.CAP_ANY)

            if not capture.isOpened():
                self._status = CameraStatus.ERROR
                self._error_message = (
                    f"Unable to open camera index {self.device_index}. "
                    "Check that the webcam is not used by another app and that "
                    "camera permission is granted (macOS: System Settings > Privacy "
                    "& Security > Camera)."
                )
                logger.error(self._error_message)
                return False

            capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.width))
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.height))
            capture.set(cv2.CAP_PROP_FPS, float(self.requested_fps))
            if self.buffer_size:
                capture.set(cv2.CAP_PROP_BUFFERSIZE, float(self.buffer_size))

            ok, frame = capture.read()
            if not ok or frame is None:
                capture.release()
                self._status = CameraStatus.ERROR
                self._error_message = (
                    "Camera opened but produced no frames. Another process may hold the device."
                )
                logger.error(self._error_message)
                return False

            self._capture = capture
            self._backend_name = capture.getBackendName()
            self._actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or frame.shape[1]
            self._actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or frame.shape[0]
            self._status = CameraStatus.CONNECTED
            self._fps.reset()
            with self._frame_lock:
                self._latest_frame = frame.copy()
            logger.info(
                "Camera %s connected via %s at %sx%s",
                self.device_index,
                self._backend_name,
                self._actual_width,
                self._actual_height,
            )
            return True

    def start(self) -> bool:
        """Open if needed and start the capture thread."""
        if self._status != CameraStatus.CONNECTED:
            if not self.open():
                return False
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, name="focusforge-camera", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Stop the capture thread and release the device."""
        self._running = False
        thread = self._thread
        if thread is not None and thread.is_alive() and threading.current_thread() is not thread:
            thread.join(timeout=2.0)
        self._thread = None
        with self._lock:
            self._release_unlocked()
            if self._status != CameraStatus.ERROR:
                self._status = CameraStatus.DISCONNECTED
        with self._frame_lock:
            self._latest_frame = None
        logger.info("Camera released")

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Return a copy of the most recent BGR frame, or None if unavailable."""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def reconnect(self) -> bool:
        """Attempt to recover after a disconnect."""
        logger.warning("Attempting camera reconnect")
        self._status = CameraStatus.RECONNECTING
        self.stop()
        for attempt in range(1, self.reconnect_attempts + 1):
            logger.info("Reconnect attempt %s/%s", attempt, self.reconnect_attempts)
            if self.open():
                return self.start()
            time.sleep(self.reconnect_delay_seconds)
        self._status = CameraStatus.ERROR
        self._error_message = "Camera reconnection failed after repeated attempts."
        logger.error(self._error_message)
        return False

    def _capture_loop(self) -> None:
        consecutive_failures = 0
        while self._running:
            with self._lock:
                capture = self._capture
            if capture is None:
                time.sleep(0.05)
                continue

            ok, frame = capture.read()
            if not ok or frame is None:
                consecutive_failures += 1
                logger.warning("Frame grab failed (%s consecutive)", consecutive_failures)
                if consecutive_failures >= 15:
                    self._status = CameraStatus.ERROR
                    self._error_message = "Camera disconnected or stopped delivering frames."
                    self._running = False
                    break
                time.sleep(0.03)
                continue

            consecutive_failures = 0
            self._fps.tick()
            with self._frame_lock:
                self._latest_frame = frame
            self._status = CameraStatus.CONNECTED

    def _release_unlocked(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "CameraManager":
        if not self.start():
            raise RuntimeError(self._error_message or "Failed to start camera")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
