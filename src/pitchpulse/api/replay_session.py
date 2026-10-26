"""In-memory replay session (single demo match stream)."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field

from pitchpulse.interpret.engine import AlertTracker
from pitchpulse.interpret.events_io import load_events
from pitchpulse.interpret.state import MatchState
from pitchpulse.interpret.alerts import FiredAlert
from pitchpulse.schema.events import MatchEvent


@dataclass
class ReplayStatus:
    match_id: str | None = None
    loaded: bool = False
    running: bool = False
    speed: float = 0.0
    index: int = 0
    total_events: int = 0
    t_ms: int = 0
    match_minute: float = 0.0
    active_alert_ids: list[str] = field(default_factory=list)


class ReplaySession:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[MatchEvent] = []
        self._match_id: str | None = None
        self._index = 0
        self._running = False
        self._speed = 0.0
        self._state: MatchState | None = None
        self._tracker = AlertTracker()
        self._last_state_push_index = 0

    def load(self, match_id: str) -> ReplayStatus:
        with self._lock:
            self._events = load_events(match_id)
            self._match_id = match_id
            self._index = 0
            self._running = False
            self._speed = 0.0
            self._state = MatchState(match_id=match_id)
            self._tracker = AlertTracker()
            self._last_state_push_index = 0
            return self.status_unlocked()

    def status_unlocked(self) -> ReplayStatus:
        st = self._state
        return ReplayStatus(
            match_id=self._match_id,
            loaded=bool(self._events),
            running=self._running,
            speed=self._speed,
            index=self._index,
            total_events=len(self._events),
            t_ms=st.t_ms if st else 0,
            match_minute=st.match_minute if st else 0.0,
            active_alert_ids=list(st.active_alert_ids) if st else [],
        )

    def status(self) -> ReplayStatus:
        with self._lock:
            return self.status_unlocked()

    def snapshot(self) -> dict:
        with self._lock:
            if self._state is None:
                return {"error": "No match loaded"}
            return self._state.snapshot()

    def start(self, speed: float = 0.0) -> ReplayStatus:
        with self._lock:
            if not self._events:
                raise ValueError("No match loaded")
            self._running = True
            self._speed = max(0.0, float(speed))
            return self.status_unlocked()

    def pause(self) -> ReplayStatus:
        with self._lock:
            self._running = False
            return self.status_unlocked()

    def set_speed(self, speed: float) -> ReplayStatus:
        with self._lock:
            self._speed = max(0.0, float(speed))
            return self.status_unlocked()

    def seek(self, t_ms: int) -> ReplayStatus:
        with self._lock:
            if not self._events or not self._match_id:
                raise ValueError("No match loaded")
            self._index = 0
            self._state = MatchState(match_id=self._match_id)
            self._tracker = AlertTracker()
            target = max(0, int(t_ms))
            while self._index < len(self._events) and self._events[self._index].t_ms < target:
                self._tracker.on_event(self._state, self._events[self._index])
                self._index += 1
            self._last_state_push_index = self._index
            return self.status_unlocked()

    def _event_dict(self, event: MatchEvent) -> dict:
        return json.loads(event.to_json_line())

    def _alert_dict(self, alert: FiredAlert) -> dict:
        return asdict(alert)

    def next_messages(self) -> tuple[list[dict], float, bool]:
        """
        Advance one event if running and return (messages, sleep_seconds, has_more).
        Caller holds no lock during sleep.
        """
        with self._lock:
            if not self._running or not self._events or self._state is None:
                return [], 0.0, self._index < len(self._events)

            if self._index >= len(self._events):
                self._running = False
                return [{"type": "done", "payload": self.status_unlocked().__dict__}], 0.0, False

            prev_t = self._state.t_ms
            event = self._events[self._index]
            alerts = self._tracker.on_event(self._state, event)
            self._index += 1

            messages: list[dict] = [
                {"type": "event", "payload": self._event_dict(event)},
            ]
            for alert in alerts:
                messages.append({"type": "alert", "payload": self._alert_dict(alert)})

            if self._index - self._last_state_push_index >= 25 or alerts:
                messages.append(
                    {"type": "state", "payload": self._state.snapshot()},
                )
                self._last_state_push_index = self._index

            sleep_s = 0.0
            if self._speed > 0 and event.t_ms > prev_t:
                sleep_s = (event.t_ms - prev_t) / 1000.0 / self._speed

            has_more = self._index < len(self._events)
            if not has_more:
                self._running = False
                messages.append({"type": "done", "payload": self.status_unlocked().__dict__})

            return messages, sleep_s, has_more or self._running


# Single studio session for hackathon demo
SESSION = ReplaySession()
