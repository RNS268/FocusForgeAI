"""Optional phone detection using a locally installed YOLO model.

This module is intentionally conservative: if a compatible model is not present,
phone detection is marked unavailable instead of inventing results.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from utils.logger import get_logger

logger = get_logger("phone")


@dataclass
class PhoneDetectionResult:
    available: bool
    detected: bool
    confidence: float
    label: str
    bounding_box: Optional[tuple[int, int, int, int]]
    explanation: str


class PhoneDetector:
    """Optional object detector for phone usage detection.

    Core behavior:
    - If ultralytics is not installed, stay unavailable.
    - If no local YOLO model exists, stay unavailable.
    - Only classify labels that clearly correspond to a phone.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        confidence_threshold: float = 0.25,
    ) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.confidence_threshold = confidence_threshold
        self._model = None
        self.available = False
        self.error_message = ""
        self._load_model()

    @staticmethod
    def _label_is_phone(label: str) -> bool:
        normalized = label.lower().replace("_", " ")
        return any(token in normalized for token in ("phone", "cell phone", "mobile phone", "cellphone"))

    def _candidate_model_paths(self) -> list[Path]:
        candidates: list[Path] = []
        if self.model_path is not None:
            candidates.append(Path(self.model_path))
        root = Path(__file__).resolve().parents[1]
        candidates.extend(
            [
                root / "models" / "yolov8n.pt",
                root / "models" / "best.pt",
                root / "models" / "phone_detector.pt",
            ]
        )
        seen: set[Path] = set()
        ordered: list[Path] = []
        for path in candidates:
            resolved = path.expanduser().resolve()
            if resolved not in seen:
                seen.add(resolved)
                ordered.append(resolved)
        return ordered

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO
        except ImportError:
            self.error_message = (
                "Phone detection unavailable: ultralytics is not installed. "
                "Install it only when you want local YOLO phone detection."
            )
            logger.warning(self.error_message)
            return

        model_path = None
        for candidate in self._candidate_model_paths():
            if candidate.exists() and candidate.stat().st_size > 0:
                model_path = candidate
                break

        if model_path is None:
            self.error_message = (
                "Phone detection unavailable: no local YOLO model was found. "
                "Place a model under models/ or pass model_path=..."
            )
            logger.warning(self.error_message)
            return

        try:
            self._model = YOLO(str(model_path))
            self.available = True
            logger.info("Phone detector ready (%s)", model_path)
        except Exception as exc:  # pragma: no cover - platform-specific native failures
            self.available = False
            self.error_message = f"Phone detector failed to initialize: {exc}"
            logger.error(self.error_message)

    def detect(self, frame: np.ndarray) -> PhoneDetectionResult:
        if not self.available or self._model is None:
            return PhoneDetectionResult(
                available=False,
                detected=False,
                confidence=0.0,
                label="",
                bounding_box=None,
                explanation=self.error_message or "Phone detection is unavailable.",
            )

        if frame is None or frame.size == 0:
            return PhoneDetectionResult(
                available=True,
                detected=False,
                confidence=0.0,
                label="",
                bounding_box=None,
                explanation="Empty frame; phone detection skipped.",
            )

        try:
            results = self._model(frame, verbose=False, conf=self.confidence_threshold)
        except Exception as exc:  # pragma: no cover - native inference errors
            return PhoneDetectionResult(
                available=True,
                detected=False,
                confidence=0.0,
                label="",
                bounding_box=None,
                explanation=f"Phone inference failed: {exc}",
            )

        phone_candidates: list[tuple[str, float, tuple[int, int, int, int]]] = []
        for result in results:
            names = getattr(result, "names", {})
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                conf = float(box.conf[0]) if hasattr(box.conf, "__len__") else float(box.conf)
                cls_index = int(box.cls[0]) if hasattr(box.cls, "__len__") else int(box.cls)
                label = str(names.get(cls_index, "unknown")).strip()
                if not self._label_is_phone(label):
                    continue
                if conf < self.confidence_threshold:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                phone_candidates.append((label, conf, (x1, y1, max(0, x2 - x1), max(0, y2 - y1))))

        if not phone_candidates:
            return PhoneDetectionResult(
                available=True,
                detected=False,
                confidence=0.0,
                label="",
                bounding_box=None,
                explanation="No phone-like object was detected above the configured confidence threshold.",
            )

        label, confidence, box = max(phone_candidates, key=lambda item: item[1])
        return PhoneDetectionResult(
            available=True,
            detected=True,
            confidence=float(confidence),
            label=label,
            bounding_box=box,
            explanation=f"Phone-like object detected with confidence {confidence:.2f}.",
        )

    def draw_result(self, frame: np.ndarray, result: PhoneDetectionResult) -> None:
        if not result.available or result.bounding_box is None or not result.detected:
            return
        x, y, w, h = result.bounding_box
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(
            frame,
            f"PHONE: {result.confidence:.2f}",
            (x, max(0, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
