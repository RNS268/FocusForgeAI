from pathlib import Path

import numpy as np
import pytest

from core.face_detector import (
    FaceDetector,
    bounding_box_from_pixels,
    landmarks_to_pixels,
)


def test_landmarks_to_pixels_scales_and_clips() -> None:
    norms = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.5, 0.25, 0.0]], dtype=np.float32)
    pixels = landmarks_to_pixels(norms, width=100, height=40)
    assert pixels.tolist() == [[0, 0], [99, 39], [50, 10]]


def test_landmarks_to_pixels_empty() -> None:
    pixels = landmarks_to_pixels(np.zeros((0, 3), dtype=np.float32), 64, 64)
    assert pixels.shape == (0, 2)


def test_bounding_box_from_pixels() -> None:
    points = np.array([[10, 20], [40, 80], [15, 25]], dtype=np.int32)
    assert bounding_box_from_pixels(points) == (10, 20, 30, 60)


def test_missing_model_is_unavailable(tmp_path: Path) -> None:
    detector = FaceDetector(model_path=tmp_path / "missing.task")
    assert detector.available is False
    assert detector.error_message
    blank = np.zeros((48, 64, 3), dtype=np.uint8)
    result = detector.detect(blank)
    assert result.available is False
    assert result.face_count == 0
    detector.close()


def test_blank_frame_has_no_faces() -> None:
    root = Path(__file__).resolve().parents[1]
    model_path = root / "models" / "face_landmarker.task"
    detector = FaceDetector(model_path=model_path)
    if not detector.available:
        pytest.skip(detector.error_message)
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    result = detector.detect(blank)
    detector.close()
    assert result.available is True
    assert result.face_count == 0
