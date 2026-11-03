from core.attention_detector import AttentionDetector, AttentionState
from utils.calibration import PoseCalibration


def test_attention_detector_faces_screen_when_angles_are_small() -> None:
    detector = AttentionDetector()
    state, explanation = detector._state_from_angles(0.0, 0.0, False)
    assert state == AttentionState.LOOKING_AT_SCREEN
    assert "screen" in explanation.lower()


def test_attention_detector_detects_head_turn_away() -> None:
    detector = AttentionDetector()
    state, explanation = detector._state_from_angles(40.0, 2.0, False)
    assert state == AttentionState.HEAD_TURNED_AWAY
    assert "away" in explanation.lower()


def test_calibration_offsets_apply_correctly() -> None:
    calibration = PoseCalibration(yaw_offset_deg=5.0, pitch_offset_deg=3.0, gaze_offset_x=0.2, gaze_offset_y=-0.1)
    yaw, pitch, roll = calibration.apply_angles(15.0, 8.0, 0.0)
    gaze_x, gaze_y = calibration.apply_gaze(0.8, -0.5)
    assert abs(yaw - 10.0) < 1e-9
    assert abs(pitch - 5.0) < 1e-9
    assert abs(roll - 0.0) < 1e-9
    assert abs(gaze_x - 0.6) < 1e-9
    assert abs(gaze_y + 0.4) < 1e-9
