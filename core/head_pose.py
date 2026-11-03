"""Head pose and approximate gaze from facial landmarks.

Gaze is inferred from iris position inside the eye plus head orientation.
That is not clinical or infrared eye tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from core.face_detector import (
    CHIN,
    LEFT_EYE_INNER,
    LEFT_EYE_OUTER,
    LEFT_IRIS,
    NOSE_TIP,
    RIGHT_EYE_INNER,
    RIGHT_EYE_OUTER,
    RIGHT_IRIS,
    DetectedFace,
)

MOUTH_LEFT = 61
MOUTH_RIGHT = 291

# Generic adult face model in millimeters for solvePnP.
_CANONICAL_3D = np.array(
    [
        (0.0, 0.0, 0.0),  # nose tip
        (0.0, -63.6, -12.5),  # chin
        (-43.3, 32.7, -26.0),  # left eye outer
        (43.3, 32.7, -26.0),  # right eye outer
        (-28.9, -28.9, -24.1),  # mouth left
        (28.9, -28.9, -24.1),  # mouth right
    ],
    dtype=np.float64,
)

_LANDMARK_IDS = (NOSE_TIP, CHIN, LEFT_EYE_OUTER, RIGHT_EYE_OUTER, MOUTH_LEFT, MOUTH_RIGHT)


@dataclass
class HeadPose:
    yaw_deg: float
    pitch_deg: float
    roll_deg: float
    rotation_matrix: np.ndarray
    translation: Optional[np.ndarray]
    rvec: Optional[np.ndarray]
    tvec: Optional[np.ndarray]
    source: str  # "matrix", "pnp", or "hybrid"
    gaze_offset_x: float  # approximate, roughly [-1, 1], + is toward viewer's right of the face
    gaze_offset_y: float  # + is downward on the image
    gaze_available: bool
    nose_px: tuple[int, int]


def camera_intrinsics(frame_width: int, frame_height: int) -> np.ndarray:
    focal = float(max(frame_width, frame_height))
    return np.array(
        [
            [focal, 0.0, frame_width / 2.0],
            [0.0, focal, frame_height / 2.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def rotation_matrix_to_euler_degrees(rotation: np.ndarray) -> tuple[float, float, float]:
    """Convert a 3x3 rotation matrix to pitch, yaw, roll in degrees.

    Pitch: + looks down in image space after typical webcam projection.
    Yaw:   + looks toward the subject's left (camera-right) before optional invert.
    Roll:  + clockwise tilt of the head.
    """
    rotation = np.asarray(rotation, dtype=np.float64)
    if rotation.shape != (3, 3):
        raise ValueError("rotation matrix must be 3x3")
    u, _, vh = np.linalg.svd(rotation)
    rotation = u @ vh
    if np.linalg.det(rotation) < 0:
        rotation = u @ np.diag([1.0, 1.0, -1.0]) @ vh

    sy = np.sqrt(rotation[0, 0] ** 2 + rotation[1, 0] ** 2)
    if sy > 1e-6:
        pitch = np.arctan2(rotation[2, 1], rotation[2, 2])
        yaw = np.arctan2(-rotation[2, 0], sy)
        roll = np.arctan2(rotation[1, 0], rotation[0, 0])
    else:
        pitch = np.arctan2(-rotation[1, 2], rotation[1, 1])
        yaw = np.arctan2(-rotation[2, 0], sy)
        roll = 0.0
    return float(np.degrees(pitch)), float(np.degrees(yaw)), float(np.degrees(roll))


def euler_degrees_to_rotation_matrix(pitch_deg: float, yaw_deg: float, roll_deg: float) -> np.ndarray:
    """Inverse of rotation_matrix_to_euler_degrees for tests and helpers."""
    pitch = np.radians(pitch_deg)
    yaw = np.radians(yaw_deg)
    roll = np.radians(roll_deg)
    rx = np.array(
        [[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]],
        dtype=np.float64,
    )
    ry = np.array(
        [[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]],
        dtype=np.float64,
    )
    rz = np.array(
        [[np.cos(roll), -np.sin(roll), 0], [np.sin(roll), np.cos(roll), 0], [0, 0, 1]],
        dtype=np.float64,
    )
    return rz @ ry @ rx


def _matrix_from_face(face: DetectedFace) -> Optional[np.ndarray]:
    matrix = face.transformation_matrix
    if matrix is None:
        return None
    array = np.asarray(matrix, dtype=np.float64)
    if array.shape == (4, 4):
        return array[:3, :3]
    if array.shape == (3, 3):
        return array
    return None


def _pnp_from_face(face: DetectedFace, frame_width: int, frame_height: int) -> tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    if face.landmarks_px.shape[0] <= max(_LANDMARK_IDS):
        return None, None, None
    image_points = np.array([face.landmarks_px[index] for index in _LANDMARK_IDS], dtype=np.float64)
    camera = camera_intrinsics(frame_width, frame_height)
    dist = np.zeros((4, 1), dtype=np.float64)
    ok, rvec, tvec = cv2.solvePnP(
        _CANONICAL_3D,
        image_points,
        camera,
        dist,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        return None, None, None
    rotation, _ = cv2.Rodrigues(rvec)
    return rotation, rvec, tvec


def approximate_iris_gaze(face: DetectedFace) -> tuple[float, float, bool]:
    """Return (x, y) iris offset inside the eye boxes. Not precise eye tracking."""
    points = face.landmarks_px
    needed = max(LEFT_IRIS, RIGHT_IRIS, LEFT_EYE_INNER, RIGHT_EYE_INNER, LEFT_EYE_OUTER, RIGHT_EYE_OUTER)
    if points.shape[0] <= needed:
        return 0.0, 0.0, False

    def one_eye(outer_idx: int, inner_idx: int, iris_idx: int) -> Optional[tuple[float, float]]:
        outer = points[outer_idx].astype(np.float64)
        inner = points[inner_idx].astype(np.float64)
        iris = points[iris_idx].astype(np.float64)
        center = (outer + inner) / 2.0
        width = np.linalg.norm(inner - outer)
        if width < 1.0:
            return None
        height = max(width * 0.35, 1.0)
        offset = (iris - center) / np.array([width / 2.0, height / 2.0])
        return float(np.clip(offset[0], -1.5, 1.5)), float(np.clip(offset[1], -1.5, 1.5))

    left = one_eye(LEFT_EYE_OUTER, LEFT_EYE_INNER, LEFT_IRIS)
    right = one_eye(RIGHT_EYE_OUTER, RIGHT_EYE_INNER, RIGHT_IRIS)
    samples = [sample for sample in (left, right) if sample is not None]
    if not samples:
        return 0.0, 0.0, False
    xs = sum(sample[0] for sample in samples) / len(samples)
    ys = sum(sample[1] for sample in samples) / len(samples)
    return xs, ys, True


def estimate_head_pose(face: DetectedFace, frame_width: int, frame_height: int) -> Optional[HeadPose]:
    """Estimate pose. Prefer MediaPipe's facial matrix; fall back to solvePnP."""
    matrix_r = _matrix_from_face(face)
    pnp_r, rvec, tvec = _pnp_from_face(face, frame_width, frame_height)
    rotation = matrix_r if matrix_r is not None else pnp_r
    if rotation is None:
        return None

    if matrix_r is not None and pnp_r is not None:
        source = "hybrid"
    elif matrix_r is not None:
        source = "matrix"
    else:
        source = "pnp"

    pitch, yaw, roll = rotation_matrix_to_euler_degrees(rotation)
    gaze_x, gaze_y, gaze_ok = approximate_iris_gaze(face)
    if face.landmarks_px.shape[0] > NOSE_TIP:
        nose = (int(face.landmarks_px[NOSE_TIP][0]), int(face.landmarks_px[NOSE_TIP][1]))
    else:
        x, y, w, h = face.bounding_box
        nose = (x + w // 2, y + h // 2)

    translation = None
    if face.transformation_matrix is not None:
        array = np.asarray(face.transformation_matrix, dtype=np.float64)
        if array.shape == (4, 4):
            translation = array[:3, 3]

    return HeadPose(
        yaw_deg=yaw,
        pitch_deg=pitch,
        roll_deg=roll,
        rotation_matrix=rotation,
        translation=translation,
        rvec=rvec,
        tvec=tvec,
        source=source,
        gaze_offset_x=gaze_x,
        gaze_offset_y=gaze_y,
        gaze_available=gaze_ok,
        nose_px=nose,
    )


def draw_pose_axes(frame: np.ndarray, pose: HeadPose, axis_length: int = 70) -> None:
    """Draw X (red), Y (green), Z (blue) axes from the nose."""
    origin = np.array(pose.nose_px, dtype=np.int32)
    rotation = pose.rotation_matrix
    # Column vectors: camera-space axes projected onto the image.
    axes = {
        0: (0, 0, 255),  # X red
        1: (0, 255, 0),  # Y green
        2: (255, 0, 0),  # Z blue
    }
    for index, color in axes.items():
        direction = rotation[:, index]
        # Flip Y for image coordinates.
        end = origin + np.array(
            [direction[0] * axis_length, -direction[1] * axis_length],
            dtype=np.float64,
        )
        cv2.arrowedLine(
            frame,
            tuple(origin),
            (int(end[0]), int(end[1])),
            color,
            2,
            tipLength=0.2,
        )
    cv2.circle(frame, tuple(origin), 4, (255, 255, 255), -1)
