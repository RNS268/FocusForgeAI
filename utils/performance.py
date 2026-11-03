"""Measured performance helpers. FPS is never a hardcoded constant."""

from __future__ import annotations

import time


class FpsTracker:
    """Exponential moving average of frames per second from real timestamps."""

    def __init__(self, smoothing: float = 0.15) -> None:
        if not 0.0 < smoothing <= 1.0:
            raise ValueError("smoothing must be in (0, 1]")
        self._smoothing = smoothing
        self._last_time: float | None = None
        self._fps: float = 0.0
        self._frame_count: int = 0

    def tick(self, now: float | None = None) -> float:
        """Record one processed frame and return the current measured FPS."""
        current = time.perf_counter() if now is None else now
        self._frame_count += 1
        if self._last_time is None:
            self._last_time = current
            return 0.0

        delta = current - self._last_time
        self._last_time = current
        if delta <= 0:
            return self._fps

        instant = 1.0 / delta
        if self._fps <= 0:
            self._fps = instant
        else:
            self._fps = (self._smoothing * instant) + ((1.0 - self._smoothing) * self._fps)
        return self._fps

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def reset(self) -> None:
        self._last_time = None
        self._fps = 0.0
        self._frame_count = 0
