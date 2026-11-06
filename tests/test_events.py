import unittest

from studyguard.core.config import DetectionSettings
from studyguard.core.event_engine import EventEngine
from studyguard.core.events import EventBus, EventType
from studyguard.vision.results import DetectionResult


class EventEngineTests(unittest.TestCase):
    def test_event_debounce_requires_duration(self):
        bus = EventBus()
        engine = EventEngine(bus, DetectionSettings(drowsy_seconds=1.0))
        result = DetectionResult("eyes", True, 0.9, event_type="DROWSINESS")
        self.assertEqual(engine.process(result, 10.0), [])
        events = engine.process(result, 11.1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventType.DROWSINESS)
        self.assertEqual(engine.process(result, 11.2), [])


    def test_event_resets_when_signal_clears(self):
        engine = EventEngine(EventBus(), DetectionSettings(looking_away_seconds=1.0))
        away = DetectionResult("attention", True, 0.9, event_type="LOOKING_AWAY")
        clear = DetectionResult("attention", False, 0.9, event_type="LOOKING_AWAY")
        self.assertEqual(engine.process(away, 1.0), [])
        self.assertEqual(engine.process(clear, 1.3), [])
        self.assertEqual(engine.process(away, 2.0), [])
