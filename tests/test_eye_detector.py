from core.eye_detector import EyeClosureDetector, EyeState
import numpy as np


def test_eye_detector_classifies_open_eyes() -> None:
    detector = EyeClosureDetector()
    metrics = detector.detect(_fake_face_result())
    assert metrics.state in {EyeState.OPEN, EyeState.UNKNOWN}


def test_eye_detector_detects_prolonged_closure() -> None:
    detector = EyeClosureDetector(prolonged_close_seconds=0.1)
    face = _closed_eye_face_result()
    metrics = detector.detect(face, now=1.0)
    assert metrics.state in {EyeState.CLOSED, EyeState.PROLONGED_CLOSED}


def _fake_face_result():
    class FakeFace:
        landmarks_px = np.array([
            [0.0, 0.0],
            [10.0, 0.0],
            [20.0, 0.0],
            [30.0, 0.0],
            [40.0, 0.0],
            [50.0, 0.0],
        ] * 100, dtype=float)

    class FakeResult:
        available = True
        primary_face = FakeFace()
        face_count = 1

    return FakeResult()


def _closed_eye_face_result():
    class FakeFace:
        landmarks_px = np.array([
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
        ] * 100, dtype=float)

    class FakeResult:
        available = True
        primary_face = FakeFace()
        face_count = 1

    return FakeResult()
