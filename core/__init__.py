"""Core detection and hardware modules."""

from core.camera_manager import CameraManager, CameraStatus
from core.face_detector import FaceDetector, FaceFrameResult

__all__ = ["CameraManager", "CameraStatus", "FaceDetector", "FaceFrameResult"]
