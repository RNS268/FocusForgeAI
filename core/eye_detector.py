"""Eye closure and fatigue detection using Eye Aspect Ratio (EAR).

This module is intentionally conservative: it only uses geometry from the
landmarks already detected by MediaPipe, and it distinguishes normal blinking
from prolonged eye closure.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

from core.face_detector import FaceFrameResult

# MediaPipe Face Landmarker index map for eyes.
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
LEFT_EYE_CORNER_LEFT = 153
LEFT_EYE_CORNER_RIGHT = 154

RIGHT_EYE_OUTER = 263
RIGHT_EYE_INNER = 362
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374
RIGHT_EYE_CORNER_LEFT = 387
RIGHT_EYE_CORNER_RIGHT = 388


class EyeState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PROLONGED_CLOSED = "prolonged_closed"
    UNKNOWN = "unknown"


@dataclass
class EyeMetrics:
    left_ear: float
    right_ear: float
    mean_ear: float
    left_closed: bool
    right_closed: bool
    eyes_closed: bool
    eyes_open: bool
    blink_detected: bool
    prolonged_closure: bool
    closure_duration_s: float
    blink_count: int
    drowsiness_score: float
    state: EyeState
    explanation: str


class EyeClosureDetector:
    """Tracks eye aspect ratio, blinking, and fatigue over time."""

    def __init__(
        self,
        eye_close_threshold: float = 0.22,
        eye_open_threshold: float = 0.28,
        prolonged_close_seconds: float = 1.3,
        blink_cooldown_seconds: float = 0.25,
        smoothing: float = 0.25,
    ) -> None:
        if not 0.0 < smoothing <= 1.0:
            raise ValueError("smoothing must be in (0, 1]")
        self.eye_close_threshold = eye_close_threshold
        self.eye_open_threshold = eye_open_threshold
        self.prolonged_close_seconds = prolonged_close_seconds
        self.blink_cooldown_seconds = blink_cooldown_seconds
        self.smoothing = smoothing

        self._last_time: Optional[float] = None
        self._closed_since: Optional[float] = None
        self._blink_count = 0
        self._last_blink_time: float = -1_000.0
        self._previous_closed = False
        self._smooth_ear: float = 0.0

    @property
    def blink_count(self) -> int:
        return self._blink_count

    def _ema(self, previous: float, value: float) -> float:
        if previous <= 0.0:
            return value
        return self.smoothing * value + (1.0 - self.smoothing) * previous

    @staticmethod
    def _eye_aspect_ratio(points: np.ndarray, eye_indices: tuple[int, int, int, int, int, int]) -> float:
        points = np.asarray(points, dtype=np.float64)
        if points.shape[0] <= max(eye_indices):
            return 0.0
        p1, p2, p3, p4, p5, p6 = [points[idx] for idx in eye_indices]
        vertical_1 = np.linalg.norm(p2 - p3)
        vertical_2 = np.linalg.norm(p4 - p5)
        horizontal = np.linalg.norm(p1 - p6)
        if horizontal <= 1e-6:
            return 0.0
        return (vertical_1 + vertical_2) / (2.0 * horizontal)

    def _compute_ear_for_face(self, face) -> tuple[float, float]:
        points = face.landmarks_px
        left = self._eye_aspect_ratio(
            points,
            (LEFT_EYE_OUTER, LEFT_EYE_TOP, LEFT_EYE_BOTTOM, LEFT_EYE_INNER, LEFT_EYE_CORNER_LEFT, LEFT_EYE_CORNER_RIGHT),
        )
        right = self._eye_aspect_ratio(
            points,
            (RIGHT_EYE_OUTER, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM, RIGHT_EYE_INNER, RIGHT_EYE_CORNER_LEFT, RIGHT_EYE_CORNER_RIGHT),
        )
        return left, right

    def detect(self, face_result: FaceFrameResult, now: Optional[float] = None) -> EyeMetrics:
        now = time.perf_counter() if now is None else now
        if not face_result.available:
            return EyeMetrics(
                left_ear=0.0,
                right_ear=0.0,
                mean_ear=0.0,
                left_closed=False,
                right_closed=False,
                eyes_closed=False,
                eyes_open=True,
                blink_detected=False,
                prolonged_closure=False,
                closure_duration_s=0.0,
                blink_count=self._blink_count,
                drowsiness_score=0.0,
                state=EyeState.UNKNOWN,
                explanation="Face detector unavailable; eye state cannot be estimated.",
            )

        primary = face_result.primary_face
        if primary is None:
            return EyeMetrics(
                left_ear=0.0,
                right_ear=0.0,
                mean_ear=0.0,
                left_closed=False,
                right_closed=False,
                eyes_closed=False,
                eyes_open=False,
                blink_detected=False,
                prolonged_closure=False,
                closure_duration_s=0.0,
                blink_count=self._blink_count,
                drowsiness_score=0.0,
                state=EyeState.UNKNOWN,
                explanation="No face detected; eye analysis is unavailable.",
            )

        left_ear, right_ear = self._compute_ear_for_face(primary)
        mean_ear = float((left_ear + right_ear) / 2.0)
        self._smooth_ear = self._ema(self._smooth_ear, mean_ear)
        mean_ear = self._smooth_ear

        left_closed = left_ear < self.eye_close_threshold
        right_closed = right_ear < self.eye_close_threshold
        eyes_closed = left_closed or right_closed
        eyes_open = mean_ear > self.eye_open_threshold

        closure_duration_s = 0.0
        if eyes_closed:
            if self._closed_since is None:
                self._closed_since = now
            closure_duration_s = now - self._closed_since
        else:
            self._closed_since = None

        blink_detected = False
        if self._previous_closed is False and eyes_closed and (now - self._last_blink_time) >= self.blink_cooldown_seconds:
            self._blink_count += 1
            self._last_blink_time = now
            blink_detected = True
        self._previous_closed = eyes_closed

        prolonged_closure = closure_duration_s >= self.prolonged_close_seconds
        if prolonged_closure:
            state = EyeState.PROLONGED_CLOSED
            explanation = (
                f"Eyes have been closed for {closure_duration_s:.1f}s, which suggests possible drowsiness."
            )
        elif eyes_closed:
            state = EyeState.CLOSED
            explanation = "Eyes are closed; normal blink or brief eye closure detected."
        elif eyes_open:
            state = EyeState.OPEN
            explanation = "Eyes are open and the user appears alert."
        else:
            state = EyeState.UNKNOWN
            explanation = "Eye state is uncertain because landmark quality is low."

        drowsiness_score = 0.0
        if eyes_closed:
            drowsiness_score = min(1.0, closure_duration_s / max(self.prolonged_close_seconds, 0.1))
        elif blink_detected:
            drowsiness_score = 0.3
        else:
            drowsiness_score = max(0.0, 1.0 - (mean_ear / max(self.eye_open_threshold, 1e-6)))

        return EyeMetrics(
            left_ear=float(left_ear),
            right_ear=float(right_ear),
            mean_ear=float(mean_ear),
            left_closed=bool(left_closed),
            right_closed=bool(right_closed),
            eyes_closed=bool(eyes_closed),
            eyes_open=bool(eyes_open),
            blink_detected=blink_detected,
            prolonged_closure=bool(prolonged_closure),
            closure_duration_s=float(closure_duration_s),
            blink_count=self._blink_count,
            drowsiness_score=float(drowsiness_score),
            state=state,
            explanation=explanation,
        )


def estimate_drowsiness_score(metrics: EyeMetrics) -> float:
    """Return a normalized drowsiness score in [0,1]."""
    if metrics.state == EyeState.PROLONGED_CLOSED:
        return min(1.0, metrics.closure_duration_s / 4.0)
    if metrics.state == EyeState.CLOSED:
        return 0.6
    if metrics.state == EyeState.OPEN:
        return max(0.0, 1.0 - metrics.mean_ear / 0.3)
    return 0.0
