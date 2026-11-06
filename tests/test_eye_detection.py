import unittest

from studyguard.core.config import DetectionSettings
from studyguard.vision.eye_detector import EyeDetector, EyeState


class FakeFace:
    def __init__(self, marks):
        self._marks = marks

    def landmarks(self, frame):
        return self._marks, 0.9


def marks_for_eye(open_eye=True):
    marks = [(0.0, 0.0, 0.0)] * 500
    left = [(0.1, 0.1, 0), (0.12, 0.07 if open_eye else 0.095, 0), (0.18, 0.07 if open_eye else 0.095, 0), (0.22, 0.1, 0), (0.18, 0.13 if open_eye else 0.105, 0), (0.12, 0.13 if open_eye else 0.105, 0)]
    right = [(0.4, 0.1, 0), (0.42, 0.07 if open_eye else 0.095, 0), (0.48, 0.07 if open_eye else 0.095, 0), (0.52, 0.1, 0), (0.48, 0.13 if open_eye else 0.105, 0), (0.42, 0.13 if open_eye else 0.105, 0)]
    for i, p in zip([33, 160, 158, 133, 153, 144], left):
        marks[i] = p
    for i, p in zip([362, 385, 387, 263, 373, 380], right):
        marks[i] = p
    return marks


class EyeDetectorTests(unittest.TestCase):
    def test_eye_state_reaches_drowsy_after_threshold(self):
        detector = EyeDetector(FakeFace(marks_for_eye(open_eye=False)), DetectionSettings(eye_ear_threshold=0.21, drowsy_seconds=1.0))
        self.assertEqual(detector.process(None, 0.0).metadata["state"], EyeState.CLOSING.value)
        result = detector.process(None, 1.2)
        self.assertEqual(result.event_type, "DROWSINESS")
        self.assertEqual(result.metadata["state"], EyeState.DROWSY.value)
