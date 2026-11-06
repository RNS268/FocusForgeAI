import unittest
import time
from pathlib import Path

from studyguard.analytics.focus_score import FocusScore
from studyguard.core.events import AppEvent, EventType
from studyguard.core.session import StudySession
from studyguard.database.db import Database
from studyguard.database.repository import Repository


class DatabaseTests(unittest.TestCase):
    def test_database_crud(self):
        workspace_tmp = Path(__file__).resolve().parents[1] / ".test_tmp"
        workspace_tmp.mkdir(exist_ok=True)
        db_path = workspace_tmp / f"sg_{time.time_ns()}.sqlite3"
        db = Database(db_path)
        db.initialize()
        repo = Repository(db)
        session = StudySession(started_at=1.0)
        session.id = repo.create_session(session)
        repo.add_event(session.id, AppEvent(EventType.SESSION_START, timestamp=1.0))
        session.end(now=20.0)
        repo.finish_session(session, FocusScore(95, "good"))
        self.assertEqual(len(repo.sessions()), 1)
        self.assertEqual(len(repo.recent_events()), 1)
