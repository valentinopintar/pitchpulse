"""Live match state updated event-by-event."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from pitchpulse.data.pitch import minute_from_ms
from pitchpulse.interpret.window import rolling_metrics
from pitchpulse.schema.events import EventType, MatchEvent


def _event_type(ev: MatchEvent) -> str:
    t = ev.type
    return t.value if isinstance(t, EventType) else str(t)


@dataclass
class MatchState:
    """Rolling state for replay / future SSE stream."""

    match_id: str
    t_ms: int = 0
    match_minute: float = 0.0
    period: int = 1
    events_seen: int = 0
    home_passes_complete: int = 0
    home_passes_total: int = 0
    active_alert_ids: list[str] = field(default_factory=list)
    _buffer: deque[MatchEvent] = field(default_factory=deque, repr=False)
    _max_buffer_ms: int = field(default=8 * 60 * 1000, repr=False)

    def apply(self, event: MatchEvent) -> None:
        self.t_ms = event.t_ms
        self.match_minute = minute_from_ms(event.t_ms)
        self.period = event.period
        self.events_seen += 1

        self._buffer.append(event)
        self._prune_buffer()

        et = _event_type(event)
        if et == EventType.PASS.value and event.team_id == "home":
            self.home_passes_total += 1
            if event.outcome == "complete":
                self.home_passes_complete += 1

    def _prune_buffer(self) -> None:
        cutoff = self.t_ms - self._max_buffer_ms
        while self._buffer and self._buffer[0].t_ms < cutoff:
            self._buffer.popleft()

    def window_events(self, window_ms: int) -> list[MatchEvent]:
        cutoff = self.t_ms - window_ms
        return [e for e in self._buffer if e.t_ms >= cutoff]

    def snapshot(self, window_ms: int = 6 * 60 * 1000) -> dict:
        window = self.window_events(window_ms)
        metrics = rolling_metrics(window)
        pass_rate = (
            round(self.home_passes_complete / self.home_passes_total, 3)
            if self.home_passes_total
            else 0.0
        )
        return {
            "match_id": self.match_id,
            "t_ms": self.t_ms,
            "match_minute": round(self.match_minute, 2),
            "period": self.period,
            "events_seen": self.events_seen,
            "home_pass_completion_rate": pass_rate,
            "active_alert_ids": list(self.active_alert_ids),
            "rolling": metrics,
        }
