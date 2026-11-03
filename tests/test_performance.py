from utils.performance import FpsTracker


def test_fps_tracker_uses_real_intervals() -> None:
    tracker = FpsTracker(smoothing=1.0)
    assert tracker.tick(0.0) == 0.0
    fps = tracker.tick(0.05)
    assert abs(fps - 20.0) < 0.01
    assert tracker.frame_count == 2


def test_fps_tracker_reset() -> None:
    tracker = FpsTracker()
    tracker.tick(0.0)
    tracker.tick(0.04)
    tracker.reset()
    assert tracker.fps == 0.0
    assert tracker.frame_count == 0
