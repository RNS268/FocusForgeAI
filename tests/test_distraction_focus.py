from datetime import datetime, timedelta

from core.distraction_engine import DistractionEngine, DistractionState
from core.attention_detector import AttentionState
from core.eye_detector import EyeState
from core.focus_scorer import FocusScorer


def test_distraction_engine_prefers_focus_when_screen_attention_is_stable() -> None:
    engine = DistractionEngine(history_length=3)
    decision = engine.update(AttentionState.LOOKING_AT_SCREEN, EyeState.OPEN, face_count=1)
    assert decision.state == DistractionState.FOCUSED


def test_distraction_engine_flags_phone_detection() -> None:
    engine = DistractionEngine(history_length=2)
    decision = engine.update(AttentionState.LOOKING_AT_SCREEN, EyeState.OPEN, phone_detected=True, phone_confidence=0.9, face_count=1)
    assert decision.state == DistractionState.PHONE_DETECTED


def test_focus_scorer_aggregates_recent_history() -> None:
    scorer = FocusScorer()
    now = datetime.now()
    scorer.add_state(now, DistractionState.FOCUSED)
    scorer.add_state(now + timedelta(seconds=1), DistractionState.FOCUSED)
    scorer.add_state(now + timedelta(seconds=2), DistractionState.LOOKING_AWAY)
    summary = scorer.summarize()
    assert summary.focus_percentage >= 0.0
    assert summary.distraction_events >= 1
