"""Screen-looking pose calibration stored locally as JSON. No images are saved."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger("calibration")


@dataclass
class PoseCalibration:
    yaw_offset_deg: float = 0.0
    pitch_offset_deg: float = 0.0
    roll_offset_deg: float = 0.0
    gaze_offset_x: float = 0.0
    gaze_offset_y: float = 0.0
    sample_count: int = 0
    calibrated: bool = False

    def apply_angles(self, yaw_deg: float, pitch_deg: float, roll_deg: float) -> tuple[float, float, float]:
        return (
            yaw_deg - self.yaw_offset_deg,
            pitch_deg - self.pitch_offset_deg,
            roll_deg - self.roll_offset_deg,
        )

    def apply_gaze(self, gaze_x: float, gaze_y: float) -> tuple[float, float]:
        return gaze_x - self.gaze_offset_x, gaze_y - self.gaze_offset_y


class CalibrationCollector:
    """Average pose samples while the user looks at the screen."""

    def __init__(self, needed_samples: int = 20) -> None:
        self.needed_samples = needed_samples
        self._yaw: list[float] = []
        self._pitch: list[float] = []
        self._roll: list[float] = []
        self._gx: list[float] = []
        self._gy: list[float] = []
        self.collecting = False

    def start(self) -> None:
        self.collecting = True
        self._yaw.clear()
        self._pitch.clear()
        self._roll.clear()
        self._gx.clear()
        self._gy.clear()

    def add(
        self,
        yaw_deg: float,
        pitch_deg: float,
        roll_deg: float,
        gaze_x: float = 0.0,
        gaze_y: float = 0.0,
    ) -> Optional[PoseCalibration]:
        if not self.collecting:
            return None
        self._yaw.append(yaw_deg)
        self._pitch.append(pitch_deg)
        self._roll.append(roll_deg)
        self._gx.append(gaze_x)
        self._gy.append(gaze_y)
        if len(self._yaw) >= self.needed_samples:
            return self.finish()
        return None

    @property
    def progress(self) -> tuple[int, int]:
        return len(self._yaw), self.needed_samples

    def finish(self) -> PoseCalibration:
        self.collecting = False
        if not self._yaw:
            return PoseCalibration()
        calibration = PoseCalibration(
            yaw_offset_deg=float(sum(self._yaw) / len(self._yaw)),
            pitch_offset_deg=float(sum(self._pitch) / len(self._pitch)),
            roll_offset_deg=float(sum(self._roll) / len(self._roll)),
            gaze_offset_x=float(sum(self._gx) / len(self._gx)),
            gaze_offset_y=float(sum(self._gy) / len(self._gy)),
            sample_count=len(self._yaw),
            calibrated=True,
        )
        logger.info(
            "Calibration complete: yaw=%.1f pitch=%.1f samples=%s",
            calibration.yaw_offset_deg,
            calibration.pitch_offset_deg,
            calibration.sample_count,
        )
        return calibration


def load_calibration(path: Path) -> PoseCalibration:
    if not path.exists():
        return PoseCalibration()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PoseCalibration(
            yaw_offset_deg=float(data.get("yaw_offset_deg", 0.0)),
            pitch_offset_deg=float(data.get("pitch_offset_deg", 0.0)),
            roll_offset_deg=float(data.get("roll_offset_deg", 0.0)),
            gaze_offset_x=float(data.get("gaze_offset_x", 0.0)),
            gaze_offset_y=float(data.get("gaze_offset_y", 0.0)),
            sample_count=int(data.get("sample_count", 0)),
            calibrated=bool(data.get("calibrated", False)),
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("Could not read calibration file %s: %s", path, exc)
        return PoseCalibration()


def save_calibration(path: Path, calibration: PoseCalibration) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(calibration), indent=2), encoding="utf-8")
    logger.info("Wrote calibration to %s", path)
