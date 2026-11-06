import unittest

from studyguard.analytics.focus_score import FocusScoreCalculator
from studyguard.core.events import AppEvent, EventType


class FocusScoreTests(unittest.TestCase):
    def test_focus_score_penalizes_distractions(self):
        events = [
            AppEvent(EventType.PHONE_DETECTED, timestamp=1, duration=12, confidence=0.9),
            AppEvent(EventType.LOOKING_AWAY, timestamp=2, duration=5, confidence=0.8),
        ]
        score = FocusScoreCalculator().calculate(events, focused_seconds=500, total_seconds=600)
        self.assertTrue(0 <= score.score < 100)
        self.assertTrue("distraction" in score.explanation.lower() or "session" in score.explanation.lower())
