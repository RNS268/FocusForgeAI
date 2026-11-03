from core.camera_manager import CameraManager, CameraStatus
from utils.performance import FpsTracker


def test_camera_manager_starts_disconnected() -> None:
    manager = CameraManager()
    assert manager.status == CameraStatus.DISCONNECTED
    assert manager.get_latest_frame() is None
    assert manager.measured_fps == 0.0


def test_camera_info_before_open() -> None:
    manager = CameraManager(device_index=2, width=320, height=240)
    info = manager.info()
    assert info.index == 2
    assert info.status == CameraStatus.DISCONNECTED
    assert info.error_message == ""


def test_fps_tracker_rejects_invalid_smoothing() -> None:
    try:
        FpsTracker(smoothing=0.0)
        assert False, "expected ValueError"
    except ValueError:
        pass
