"""Classify screen attention from head pose and approximate gaze.

This is not the full distraction matrix (Phase 6). It only interprets
pose, face count, and head motion with light smoothing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.face_detector import FaceFrameResult
from core.head_pose import HeadPose, estimate_head_pose
from utils.calibration import PoseCalibration


class AttentionState(str, Enum):
    LOOKING_AT_SCREEN = "looking_at_screen"
    LOOKING_LEFT = "looking_left"
    LOOKING_RIGHT = "looking_right"
    LOOKING_UP = "looking_up"
    LOOKING_DOWN = "looking_down"
    HEAD_TURNED_AWAY = "head_turned_away"
    NO_FACE = "no_face"
    MULTIPLE_FACES = "multiple_faces"
    UNKNOWN = "unknown"


@dataclass
class AttentionResult:
    state: AttentionState
    explanation: str
    yaw_deg: float
    pitch_deg: float
    roll_deg: float
    gaze_offset_x: float
    gaze_offset_y: float
    gaze_available: bool
    head_moving: bool
    angular_speed_deg_s: float
    pose: Optional[HeadPose]
    calibrated: bool


class AttentionDetector:
    def __init__(
        self,
        yaw_look_threshold_deg: float = 12.0,
        pitch_look_threshold_deg: float = 10.0,
        yaw_away_threshold_deg: float = 28.0,
        pitch_away_threshold_deg: float = 24.0,
        motion_threshold_deg_s: float = 40.0,
        smoothing: float = 0.25,
        invert_yaw: bool = True,
        invert_pitch: bool = False,
        gaze_yaw_gain_deg: float = 10.0,
        gaze_pitch_gain_deg: float = 8.0,
        calibration: Optional[PoseCalibration] = None,
    ) -> None:
        if not 0.0 < smoothing <= 1.0:
            raise ValueError("smoothing must be in (0, 1]")
        self.yaw_look_threshold_deg = yaw_look_threshold_deg
        self.pitch_look_threshold_deg = pitch_look_threshold_deg
        self.yaw_away_threshold_deg = yaw_away_threshold_deg
        self.pitch_away_threshold_deg = pitch_away_threshold_deg
        self.motion_threshold_deg_s = motion_threshold_deg_s
        self.smoothing = smoothing
        self.invert_yaw = invert_yaw
        self.invert_pitch = invert_pitch
        self.gaze_yaw_gain_deg = gaze_yaw_gain_deg
        self.gaze_pitch_gain_deg = gaze_pitch_gain_deg
        self.calibration = calibration or PoseCalibration()
        self._smooth_yaw: Optional[float] = None
        self._smooth_pitch: Optional[float] = None
        self._smooth_roll: Optional[float] = None
        self._last_time: Optional[float] = None
        self._last_angles: Optional[tuple[float, float, float]] = None

    def set_calibration(self, calibration: PoseCalibration) -> None:
        self.calibration = calibration

    def reset_smoothing(self) -> None:
        self._smooth_yaw = None
        self._smooth_pitch = None
        self._smooth_roll = None
        self._last_time = None
        self._last_angles = None

    def _ema(self, previous: Optional[float], value: float) -> float:
        if previous is None:
            return value
        return self.smoothing * value + (1.0 - self.smoothing) * previous

    def classify(
        self,
        face_result: FaceFrameResult,
        frame_width: int,
        frame_height: int,
        now: Optional[float] = None,
    ) -> AttentionResult:
        now = time.perf_counter() if now is None else now
        if not face_result.available:
            self.reset_smoothing()
            return AttentionResult(
                state=AttentionState.UNKNOWN,
                explanation="Face detector is unavailable, so attention cannot be estimated.",
                yaw_deg=0.0,
                pitch_deg=0.0,
                roll_deg=0.0,
                gaze_offset_x=0.0,
                gaze_offset_y=0.0,
                gaze_available=False,
                head_moving=False,
                angular_speed_deg_s=0.0,
                pose=None,
                calibrated=self.calibration.calibrated,
            )
        if face_result.face_count == 0:
            self.reset_smoothing()
            return AttentionResult(
                state=AttentionState.NO_FACE,
                explanation="No face detected in the webcam frame.",
                yaw_deg=0.0,
                pitch_deg=0.0,
                roll_deg=0.0,
                gaze_offset_x=0.0,
                gaze_offset_y=0.0,
                gaze_available=False,
                head_moving=False,
                angular_speed_deg_s=0.0,
                pose=None,
                calibrated=self.calibration.calibrated,
            )
        if face_result.face_count > 1:
            return AttentionResult(
                state=AttentionState.MULTIPLE_FACES,
                explanation=f"{face_result.face_count} faces are visible; the student cannot be identified uniquely.",
                yaw_deg=0.0,
                pitch_deg=0.0,
                roll_deg=0.0,
                gaze_offset_x=0.0,
                gaze_offset_y=0.0,
                gaze_available=False,
                head_moving=False,
                angular_speed_deg_s=0.0,
                pose=None,
                calibrated=self.calibration.calibrated,
            )

        primary = face_result.primary_face
        if primary is None:
            self.reset_smoothing()
            return AttentionResult(
                state=AttentionState.UNKNOWN,
                explanation="Face list was empty after a positive count.",
                yaw_deg=0.0,
                pitch_deg=0.0,
                roll_deg=0.0,
                gaze_offset_x=0.0,
                gaze_offset_y=0.0,
                gaze_available=False,
                head_moving=False,
                angular_speed_deg_s=0.0,
                pose=None,
                calibrated=self.calibration.calibrated,
            )

        pose = estimate_head_pose(primary, frame_width, frame_height)
        if pose is None:
            return AttentionResult(
                state=AttentionState.UNKNOWN,
                explanation="Landmarks were found but head pose could not be solved.",
                yaw_deg=0.0,
                pitch_deg=0.0,
                roll_deg=0.0,
                gaze_offset_x=0.0,
                gaze_offset_y=0.0,
                gaze_available=False,
                head_moving=False,
                angular_speed_deg_s=0.0,
                pose=None,
                calibrated=self.calibration.calibrated,
            )

        yaw, pitch, roll = self.calibration.apply_angles(pose.yaw_deg, pose.pitch_deg, pose.roll_deg)
        gaze_x, gaze_y = self.calibration.apply_gaze(pose.gaze_offset_x, pose.gaze_offset_y)
        if self.invert_yaw:
            yaw = -yaw
            gaze_x = -gaze_x
        if self.invert_pitch:
            pitch = -pitch
            gaze_y = -gaze_y

        self._smooth_yaw = self._ema(self._smooth_yaw, yaw)
        self._smooth_pitch = self._ema(self._smooth_pitch, pitch)
        self._smooth_roll = self._ema(self._smooth_roll, roll)
        yaw, pitch, roll = self._smooth_yaw, self._smooth_pitch, self._smooth_roll

        angular_speed = 0.0
        if self._last_time is not None and self._last_angles is not None:
            dt = now - self._last_time
            if dt > 1e-3:
                dyaw = yaw - self._last_angles[0]
                dpitch = pitch - self._last_angles[1]
                droll = roll - self._last_angles[2]
                angular_speed = (dyaw**2 + dpitch**2 + droll**2) ** 0.5 / dt
        self._last_time = now
        self._last_angles = (yaw, pitch, roll)
        head_moving = angular_speed >= self.motion_threshold_deg_s

        # Approximate gaze nudges the decision only; head pose remains primary.
        effective_yaw = yaw
        effective_pitch = pitch
        if pose.gaze_available:
            effective_yaw += gaze_x * self.gaze_yaw_gain_deg
            effective_pitch += gaze_y * self.gaze_pitch_gain_deg

        state, explanation = self._state_from_angles(effective_yaw, effective_pitch, pose.gaze_available)
        if head_moving and state == AttentionState.LOOKING_AT_SCREEN:
            explanation = f"{explanation} Head is moving ({angular_speed:.0f} deg/s)."

        return AttentionResult(
            state=state,
            explanation=explanation,
            yaw_deg=yaw,
            pitch_deg=pitch,
            roll_deg=roll,
            gaze_offset_x=gaze_x,
            gaze_offset_y=gaze_y,
            gaze_available=pose.gaze_available,
            head_moving=head_moving,
            angular_speed_deg_s=angular_speed,
            pose=pose,
            calibrated=self.calibration.calibrated,
        )

    def _state_from_angles(self, yaw: float, pitch: float, gaze_available: bool) -> tuple[AttentionState, str]:
        abs_yaw = abs(yaw)
        abs_pitch = abs(pitch)
        gaze_note = (
            " Approximate gaze uses iris landmarks, not dedicated eye tracking."
            if gaze_available
            else " Iris landmarks were unavailable; decision uses head pose only."
        )

        if abs_yaw >= self.yaw_away_threshold_deg or abs_pitch >= self.pitch_away_threshold_deg:
            direction = "side" if abs_yaw >= abs_pitch else "vertical"
            return (
                AttentionState.HEAD_TURNED_AWAY,
                f"Head is turned well away from the screen ({direction}; yaw={yaw:.1f}°, pitch={pitch:.1f}°).{gaze_note}",
            )
        if abs_yaw < self.yaw_look_threshold_deg and abs_pitch < self.pitch_look_threshold_deg:
            cal = "after calibration" if self.calibration.calibrated else "using default camera-forward origin"
            return (
                AttentionState.LOOKING_AT_SCREEN,
                f"Head is facing the screen {cal} (yaw={yaw:.1f}°, pitch={pitch:.1f}°).{gaze_note}",
            )
        if abs_pitch >= abs_yaw:
            if pitch < 0:
                return (
                    AttentionState.LOOKING_UP,
                    f"Head is tilted up relative to the screen (pitch={pitch:.1f}°).{gaze_note}",
                )
            return (
                AttentionState.LOOKING_DOWN,
                f"Head is tilted down relative to the screen (pitch={pitch:.1f}°).{gaze_note}",
            )
        if yaw < 0:
            return (
                AttentionState.LOOKING_LEFT,
                f"Head is turned left relative to the screen (yaw={yaw:.1f}°).{gaze_note}",
            )
        return (
            AttentionState.LOOKING_RIGHT,
            f"Head is turned right relative to the screen (yaw={yaw:.1f}°).{gaze_note}",
        )
