"""Focus scoring and session productivity metrics.

The scorer interprets distraction states over time and converts them into a
focus percentage and session summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from core.distraction_engine import DistractionState


@dataclass
class FocusSummary:
    focus_percentage: float
    focused_seconds: float
    distracted_seconds: float
    distraction_events: int
    total_seconds: float
    productive_minutes: float
    average_focus_percentage: float
    explanation: str


class FocusScorer:
    """Turn a stream of distraction decisions into session metrics."""

    def __init__(self) -> None:
        self._history: list[tuple[datetime, DistractionState]] = []

    def add_state(self, timestamp: Optional[datetime], state: DistractionState) -> None:
        if timestamp is None:
            timestamp = datetime.now()
        self._history.append((timestamp, state))

    def clear(self) -> None:
        self._history.clear()

    def summarize(self, window_seconds: float = 0.0) -> FocusSummary:
        if not self._history:
            return FocusSummary(
                focus_percentage=0.0,
                focused_seconds=0.0,
                distracted_seconds=0.0,
                distraction_events=0,
                total_seconds=0.0,
                productive_minutes=0.0,
                average_focus_percentage=0.0,
                explanation="No study history available yet.",
            )

        if window_seconds > 0:
            cutoff = self._history[-1][0] - timedelta(seconds=window_seconds)
            history = [entry for entry in self._history if entry[0] >= cutoff]
        else:
            history = self._history

        if not history:
            return FocusSummary(
                focus_percentage=0.0,
                focused_seconds=0.0,
                distracted_seconds=0.0,
                distraction_events=0,
                total_seconds=0.0,
                productive_minutes=0.0,
                average_focus_percentage=0.0,
                explanation="No study history within the selected time window.",
            )

        start = history[0][0]
        end = history[-1][0]
        total_seconds = max((end - start).total_seconds(), 0.0)

        focused = 0
        distracted = 0
        events = 0
        states = [state for _, state in history]

        for state in states:
            if state == DistractionState.FOCUSED:
                focused += 1
            else:
                distracted += 1

        if states:
            events = sum(1 for state in states if state != DistractionState.FOCUSED)

        focus_percentage = (focused / len(states)) * 100.0 if states else 0.0
        focused_seconds = focused * 1.0
        distracted_seconds = distracted * 1.0
        productive_minutes = max(0.0, focused_seconds / 60.0)
        average_focus_percentage = focus_percentage

        explanation = (
            f"{focus_percentage:.1f}% of recent observations were focused; "
            f"{events} distraction events were counted."
        )

        return FocusSummary(
            focus_percentage=focus_percentage,
            focused_seconds=focused_seconds,
            distracted_seconds=distracted_seconds,
            distraction_events=events,
            total_seconds=total_seconds,
            productive_minutes=productive_minutes,
            average_focus_percentage=average_focus_percentage,
            explanation=explanation,
        )
