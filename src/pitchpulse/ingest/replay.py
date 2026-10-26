"""CLI replay of synthetic match events with live alert output."""

from __future__ import annotations

import argparse
import time

from pitchpulse.data.pitch import minute_from_ms
from pitchpulse.interpret.engine import replay_alerts
from pitchpulse.interpret.events_io import load_events
from pitchpulse.interpret.state import MatchState
from pitchpulse.schema.events import EventType, MatchEvent


def _event_type(ev: MatchEvent) -> str:
    t = ev.type
    return t.value if isinstance(t, EventType) else str(t)


def run_replay(
    match_id: str,
    *,
    speed: float = 0.0,
    max_events: int | None = None,
    precompute_alerts: bool = True,
) -> int:
    events = load_events(match_id)
    if max_events:
        events = events[:max_events]

    fired_list: list = []
    if precompute_alerts:
        _, fired_list = replay_alerts(events, match_id=match_id)
    fired_list = sorted(fired_list, key=lambda a: a.t_ms)
    fire_idx = 0

    state = MatchState(match_id=match_id)
    prev_t = 0

    print(f"PitchPulse replay — {match_id} ({len(events)} events, speed={speed or 'instant'})")
    print("-" * 60)

    for event in events:
        if speed > 0 and event.t_ms > prev_t:
            time.sleep((event.t_ms - prev_t) / 1000.0 / speed)
        prev_t = event.t_ms

        while fire_idx < len(fired_list) and fired_list[fire_idx].t_ms <= event.t_ms:
            alert = fired_list[fire_idx]
            minute = minute_from_ms(alert.t_ms)
            print(
                f"[{minute:5.1f}'] ALERT {alert.alert_id} ({alert.severity}) "
                f"crosses={alert.evidence.get('flank_strike_load_home_right')} "
                f"chaos={alert.evidence.get('midfield_chaos_index')}"
            )
            fire_idx += 1

        state.apply(event)
        minute = minute_from_ms(event.t_ms)

        if _event_type(event) == EventType.SUBSTITUTION.value:
            off_id = event.meta.get("player_off") or event.opponent_id
            on_id = event.meta.get("player_on") or event.player_id
            print(f"[{minute:5.1f}'] SUB  {event.team_id}: {off_id} → {on_id}")

        if _event_type(event) == EventType.MATCH_META.value:
            print(f"[{minute:5.1f}'] META {event.outcome}")

    snap = state.snapshot()
    print("-" * 60)
    print(f"Done at {snap['match_minute']}' — alerts seen: {snap['active_alert_ids']}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay synthetic match events")
    parser.add_argument("--match", default="syn-001")
    parser.add_argument(
        "--speed",
        type=float,
        default=0.0,
        help="Real-time multiplier (0=instant, 10=10x match clock)",
    )
    parser.add_argument("--max-events", type=int, default=None)
    args = parser.parse_args()
    raise SystemExit(run_replay(args.match, speed=args.speed, max_events=args.max_events))


if __name__ == "__main__":
    main()
