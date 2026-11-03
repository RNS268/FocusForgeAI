"""Distraction classification engine with temporal smoothing and state transitions.

This phase combines the camera-derived attention state, eye state, and optional
phone detection into a final high-level distraction state. It intentionally
avoids flipping state on a single bad frame.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.attention_detector import AttentionState
from core.eye_detector import EyeState


class DistractionState(str, Enum):
    FOCUSED = "focused"
    LOOKING_AWAY = "looking_away"
    PHONE_DETECTED = "phone_detected"
    EYES_CLOSED = "eyes_closed"
    NO_FACE = "no_face"
    MULTIPLE_FACES = "multiple_faces"
    POSSIBLE_DROWSINESS = "possible_drowsiness"
    UNKNOWN = "unknown"


@dataclass
class DistractionDecision:
    state: DistractionState
    confidence: float
    explanation: str
    evidence: dict


class DistractionEngine:
    """Smooths noisy per-frame signals into a consistent attention state."""

    def __init__(
        self,
        history_length: int = 8,
        lookaway_weight: float = 0.6,
        eye_close_weight: float = 0.8,
        phone_weight: float = 0.9,
        drowsiness_weight: float = 0.7,
    ) -> None:
        self.history_length = max(1, history_length)
        self.lookaway_weight = lookaway_weight
        self.eye_close_weight = eye_close_weight
        self.phone_weight = phone_weight
        self.drowsiness_weight = drowsiness_weight
        self._history: deque[DistractionDecision] = deque(maxlen=self.history_length)

    def reset(self) -> None:
        self._history.clear()

    def update(
        self,
        attention_state: AttentionState,
        eye_state: EyeState,
        phone_detected: bool = False,
        phone_confidence: float = 0.0,
        face_count: int = 1,
        explanation: str = "",
    ) -> DistractionDecision:
        evidence = {
            "attention_state": attention_state,
            "eye_state": eye_state,
            "phone_detected": phone_detected,
            "phone_confidence": phone_confidence,
            "face_count": face_count,
        }

        if face_count == 0:
            state = DistractionState.NO_FACE
            confidence = 0.95
            explanation = explanation or "No face was detected in the current frame."
        elif face_count > 1:
            state = DistractionState.MULTIPLE_FACES
            confidence = 0.9
            explanation = explanation or "Multiple faces are visible, so the study target is ambiguous."
        elif phone_detected:
            state = DistractionState.PHONE_DETECTED
            confidence = min(0.99, max(0.5, phone_confidence))
            explanation = explanation or "A phone-like object was detected near the user."
        elif eye_state == EyeState.PROLONGED_CLOSED:
            state = DistractionState.POSSIBLE_DROWSINESS
            confidence = 0.88
            explanation = explanation or "Eyes have been closed for an extended period."
        elif eye_state == EyeState.CLOSED:
            state = DistractionState.EYES_CLOSED
            confidence = 0.8
            explanation = explanation or "Eyes are closed for a short period; blinking or temporary fatigue is possible."
        elif attention_state in {AttentionState.LOOKING_LEFT, AttentionState.LOOKING_RIGHT, AttentionState.LOOKING_UP, AttentionState.LOOKING_DOWN, AttentionState.HEAD_TURNED_AWAY}:
            state = DistractionState.LOOKING_AWAY
            confidence = 0.75
            explanation = explanation or "The student is visually oriented away from the screen."
        elif attention_state == AttentionState.LOOKING_AT_SCREEN:
            state = DistractionState.FOCUSED
            confidence = 0.8
            explanation = explanation or "The student is facing the screen and appears engaged."
        else:
            state = DistractionState.UNKNOWN
            confidence = 0.5
            explanation = explanation or "Unable to classify attention reliably from the current signals."

        decision = DistractionDecision(state=state, confidence=confidence, explanation=explanation, evidence=evidence)
        self._history.append(decision)
        return self._smoothed_state()

    def _smoothed_state(self) -> DistractionDecision:
        if not self._history:
            return DistractionDecision(
                state=DistractionState.UNKNOWN,
                confidence=0.0,
                explanation="No decisions yet.",
                evidence={},
            )

        counts = {item.state: 0 for item in self._history}
        for item in self._history:
            counts[item.state] += 1
        best_state, _ = max(counts.items(), key=lambda item: item[1])

        majority = counts[best_state] / len(self._history)
        latest = self._history[-1]
        if majority >= 0.6:
            return DistractionDecision(
                state=best_state,
                confidence=max(latest.confidence, min(0.99, majority)),
                explanation=f"Temporal smoothing: {best_state.value} has been the dominant recent state ({majority:.0%} of recent frames).",
                evidence=latest.evidence,
            )

        return latest

    def current_state(self) -> Optional[DistractionDecision]:
        if not self._history:
            return None
        return self._history[-1]
