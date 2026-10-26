"""Replay events and fire coaching alerts."""

from __future__ import annotations

from dataclasses import dataclass, field

from pitchpulse.data.pitch import minute_from_ms
from pitchpulse.interpret.alerts import DEFAULT_RULES, AlertRule, FiredAlert
from pitchpulse.interpret.state import MatchState
from pitchpulse.schema.events import EventType, MatchEvent


def _event_type(ev: MatchEvent) -> str:
    t = ev.type
    return t.value if isinstance(t, EventType) else str(t)


@dataclass
class AlertTracker:
    """Incremental alert evaluation while streaming events."""

    rules: list[AlertRule] = field(default_factory=lambda: list(DEFAULT_RULES))
    cooldown_ms: int = 4 * 60 * 1000
    last_fire: dict[str, int] = field(default_factory=dict)

    def on_event(self, state: MatchState, event: MatchEvent) -> list[FiredAlert]:
        fired: list[FiredAlert] = []
        if _event_type(event) == EventType.MATCH_META.value:
            state.apply(event)
            return fired

        state.apply(event)
        t_ms = event.t_ms
        minute = minute_from_ms(t_ms)

        for rule in self.rules:
            last = self.last_fire.get(rule.alert_id, -10**12)
            if t_ms - last < self.cooldown_ms:
                continue
            window_events = state.window_events(rule.window_ms)
            alert = rule.evaluate(window_events, t_ms, minute)
            if alert is None:
                continue
            fired.append(alert)
            self.last_fire[rule.alert_id] = t_ms
            if rule.alert_id not in state.active_alert_ids:
                state.active_alert_ids.append(rule.alert_id)
        return fired


def replay_alerts(
    events: list[MatchEvent],
    *,
    match_id: str = "syn-001",
    rules: list[AlertRule] | None = None,
    cooldown_ms: int = 4 * 60 * 1000,
) -> tuple[MatchState, list[FiredAlert]]:
    """Walk the event stream; emit each alert_id at most once per cooldown window."""
    tracker = AlertTracker(rules=rules or list(DEFAULT_RULES), cooldown_ms=cooldown_ms)
    state = MatchState(match_id=match_id)
    fired: list[FiredAlert] = []

    for event in events:
        fired.extend(tracker.on_event(state, event))

    return state, fired
