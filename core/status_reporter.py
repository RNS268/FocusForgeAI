"""HTTP status reporter for the laptop-to-ESP32 bridge.

This uploader sends the live focus metrics to the local JSON status server so the
ESP32 panel can display the latest AI state without hosting any ML code itself.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any


class StatusReporter:
    """Push the current session summary to the local status API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8081") -> None:
        self.base_url = base_url.rstrip("/")

    def publish(
        self,
        *,
        focus_score: int,
        distraction_count: int,
        session_active: bool,
        camera_status: str,
        face_status: str,
        phone_status: str,
    ) -> bool:
        payload = {
            "status": "ok",
            "focus_score": max(0, min(100, int(focus_score))),
            "distraction_count": max(0, int(distraction_count)),
            "session_active": bool(session_active),
            "camera_status": str(camera_status),
            "face_status": str(face_status),
            "phone_status": str(phone_status),
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/status",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=1.5) as response:
                response.read()
            return True
        except Exception:
            return False
