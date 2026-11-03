"""Local face detection and facial landmarks via MediaPipe Face Landmarker.

Frames are processed in memory. This module does not write images or video.
If MediaPipe or the local .task model is missing, detection is marked
unavailable instead of inventing faces.
"""

from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from utils.logger import get_logger

logger = get_logger("face")

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
except ImportError:  # pragma: no cover - exercised when the extra is not installed
    mp = None
    mp_python = None
    mp_vision = None

# Official MediaPipe Face Landmarker (float16). Downloaded once into models/.
FACE_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)
DEFAULT_MODEL_NAME = "face_landmarker.task"

# Subset of the 478-point Face Mesh used by later pose / EAR work.
NOSE_TIP = 1
CHIN = 152
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
RIGHT_EYE_OUTER = 263
RIGHT_EYE_INNER = 362
LEFT_IRIS = 468
RIGHT_IRIS = 473


@dataclass
class DetectedFace:
    """One face in pixel and normalized coordinates."""

    landmarks_norm: np.ndarray  # (N, 3) x,y,z in [0,1] image space for x,y
    landmarks_px: np.ndarray  # (N, 2) integer pixel x,y
    score: float
    bounding_box: tuple[int, int, int, int]  # x, y, w, h
    transformation_matrix: Optional[np.ndarray] = None


@dataclass
class FaceFrameResult:
    faces: list[DetectedFace] = field(default_factory=list)
    inference_ms: float = 0.0
    available: bool = False
    error_message: str = ""

    @property
    def face_count(self) -> int:
        return len(self.faces)

    @property
    def primary_face(self) -> Optional[DetectedFace]:
        if not self.faces:
            return None
        return max(self.faces, key=lambda face: face.score)


def default_model_path(project_root: Path) -> Path:
    return project_root / "models" / DEFAULT_MODEL_NAME


def download_face_landmarker_model(destination: Path, timeout_seconds: int = 60) -> Path:
    """Fetch the Face Landmarker model if it is not already on disk."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 1000:
        logger.info("Face Landmarker model already present at %s", destination)
        return destination

    logger.info("Downloading Face Landmarker model to %s", destination)
    tmp_path = destination.with_suffix(".task.partial")
    try:
        with urllib.request.urlopen(FACE_LANDMARKER_URL, timeout=timeout_seconds) as response:
            data = response.read()
        if len(data) < 1000:
            raise RuntimeError("Downloaded Face Landmarker model is unexpectedly small.")
        tmp_path.write_bytes(data)
        tmp_path.replace(destination)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
    logger.info("Saved Face Landmarker model (%s bytes)", destination.stat().st_size)
    return destination


def landmarks_to_pixels(landmarks_norm: np.ndarray, width: int, height: int) -> np.ndarray:
    """Convert MediaPipe normalized x,y to integer pixel coordinates."""
    if landmarks_norm.size == 0:
        return np.zeros((0, 2), dtype=np.int32)
    xs = np.clip(np.round(landmarks_norm[:, 0] * width), 0, max(width - 1, 0))
    ys = np.clip(np.round(landmarks_norm[:, 1] * height), 0, max(height - 1, 0))
    return np.stack([xs, ys], axis=1).astype(np.int32)


def bounding_box_from_pixels(points: np.ndarray) -> tuple[int, int, int, int]:
    if points.size == 0:
        return (0, 0, 0, 0)
    x_min = int(points[:, 0].min())
    y_min = int(points[:, 1].min())
    x_max = int(points[:, 0].max())
    y_max = int(points[:, 1].max())
    return (x_min, y_min, x_max - x_min, y_max - y_min)


class FaceDetector:
    """Runs MediaPipe Face Landmarker in VIDEO mode on BGR OpenCV frames."""

    def __init__(
        self,
        model_path: Path,
        max_faces: int = 2,
        min_detection_confidence: float = 0.5,
        min_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        output_transformation_matrices: bool = True,
    ) -> None:
        self.model_path = Path(model_path)
        self.max_faces = max_faces
        self.min_detection_confidence = min_detection_confidence
        self.min_presence_confidence = min_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.output_transformation_matrices = output_transformation_matrices
        self._landmarker = None
        self._last_timestamp_ms = -1
        self._start = time.perf_counter()
        self._error_message = ""
        self._available = False
        self._open()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def error_message(self) -> str:
        return self._error_message

    def _open(self) -> None:
        if mp is None or mp_python is None or mp_vision is None:
            self._error_message = (
                "MediaPipe is not installed. Run: pip install -r requirements.txt"
            )
            logger.warning(self._error_message)
            return
        if not self.model_path.exists():
            self._error_message = (
                f"Face Landmarker model not found at {self.model_path}. "
                "Run: python main.py --download-models"
            )
            logger.warning(self._error_message)
            return
        try:
            options = mp_vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=mp_vision.RunningMode.VIDEO,
                num_faces=self.max_faces,
                min_face_detection_confidence=self.min_detection_confidence,
                min_face_presence_confidence=self.min_presence_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=self.output_transformation_matrices,
            )
            self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
            self._available = True
            logger.info("Face Landmarker ready (%s)", self.model_path)
        except Exception as exc:  # MediaPipe raises various native errors
            self._error_message = f"Failed to load Face Landmarker: {exc}"
            logger.error(self._error_message)
            self._landmarker = None
            self._available = False

    def detect(self, bgr_frame: np.ndarray) -> FaceFrameResult:
        if not self._available or self._landmarker is None:
            return FaceFrameResult(available=False, error_message=self._error_message)
        if bgr_frame is None or bgr_frame.size == 0:
            return FaceFrameResult(available=True, error_message="Empty frame")

        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        height, width = rgb.shape[:2]
        timestamp_ms = int((time.perf_counter() - self._start) * 1000)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        started = time.perf_counter()
        try:
            raw = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        except Exception as exc:
            message = f"Face Landmarker inference failed: {exc}"
            logger.error(message)
            return FaceFrameResult(available=True, error_message=message)
        inference_ms = (time.perf_counter() - started) * 1000.0

        faces: list[DetectedFace] = []
        landmarks_list = raw.face_landmarks or []
        matrices = raw.facial_transformation_matrixes or []
        for index, landmark_list in enumerate(landmarks_list):
            coords = np.array(
                [[lm.x, lm.y, lm.z] for lm in landmark_list],
                dtype=np.float32,
            )
            pixels = landmarks_to_pixels(coords, width, height)
            matrix = None
            if index < len(matrices):
                matrix = np.array(matrices[index], dtype=np.float32)
            faces.append(
                DetectedFace(
                    landmarks_norm=coords,
                    landmarks_px=pixels,
                    score=1.0,
                    bounding_box=bounding_box_from_pixels(pixels),
                    transformation_matrix=matrix,
                )
            )
        return FaceFrameResult(faces=faces, inference_ms=inference_ms, available=True)

    def close(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None
        self._available = False
        logger.info("Face Landmarker released")

    def __enter__(self) -> "FaceDetector":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def draw_face_overlays(frame: np.ndarray, result: FaceFrameResult, draw_all_landmarks: bool = True) -> None:
    """Draw bounding boxes and landmarks onto a BGR frame (in place)."""
    if not result.available:
        return
    for face in result.faces:
        x, y, w, h = face.bounding_box
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 255), 1)
        if draw_all_landmarks:
            for px, py in face.landmarks_px:
                cv2.circle(frame, (int(px), int(py)), 1, (0, 255, 255), -1)
        for key_index, color in (
            (NOSE_TIP, (0, 255, 0)),
            (LEFT_EYE_OUTER, (255, 0, 0)),
            (RIGHT_EYE_OUTER, (255, 0, 0)),
            (CHIN, (255, 255, 0)),
        ):
            if key_index < len(face.landmarks_px):
                point = face.landmarks_px[key_index]
                cv2.circle(frame, (int(point[0]), int(point[1])), 3, color, -1)
