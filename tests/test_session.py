import unittest

from studyguard.core.events import AppEvent, EventType
from studyguard.core.session import StudySession


class SessionTests(unittest.TestCase):
    def test_session_pause_and_streak(self):
        session = StudySession(started_at=0.0, current_streak_start=0.0)
        session.pause(10.0)
        session.resume(15.0)
        self.assertEqual(session.total_paused, 5.0)
        session.add_event(AppEvent(EventType.PHONE_DETECTED, timestamp=20.0, duration=2.0))
        self.assertEqual(session.best_streak, 10.0)
        session.end(30.0)
        self.assertEqual(session.elapsed, 25.0)
