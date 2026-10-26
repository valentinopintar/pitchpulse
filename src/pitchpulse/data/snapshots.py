"""Roll minute and window metrics from event streams."""

from __future__ import annotations

from collections import defaultdict

from pitchpulse.data.pitch import minute_from_ms
from pitchpulse.schema.events import EventType, MatchEvent, SubstitutionMoment


def build_minute_snapshots(events: list[MatchEvent]) -> list[dict]:
    buckets: dict[int, dict] = defaultdict(lambda: {
        "minute": 0,
        "flank_strike_load_home_right": 0,
        "zone_tension_right_flank": 0.0,
        "possession_chaos_index_mid": 0.0,
        "turnovers_mid": 0,
        "duels_lost_away_lb": 0,
        "duels_total_away_lb": 0,
        "shots_home": 0,
        "defensive_contacts_away": 0,
        "entries_vs_away": 0,
    })

    for ev in events:
        minute = int(minute_from_ms(ev.t_ms))
        b = buckets[minute]
        b["minute"] = minute

        if _event_type(ev) == EventType.CROSS.value and ev.team_id == "home":
            b["flank_strike_load_home_right"] += 1
        if _event_type(ev) == EventType.PRESSURE.value and ev.pitch_zone == "right_flank_final_third":
            b["zone_tension_right_flank"] = max(
                b["zone_tension_right_flank"],
                ev.metrics.zone_tension_index or 0.0,
            )
        if _event_type(ev) == EventType.POSSESSION_CHANGE.value and ev.pitch_zone == "central_mid":
            b["turnovers_mid"] += 1
            b["possession_chaos_index_mid"] += 0.15
        if _event_type(ev) == EventType.DUEL.value and ev.player_id == "A03":
            b["duels_total_away_lb"] += 1
            if ev.outcome == "lost":
                b["duels_lost_away_lb"] += 1
        if _event_type(ev) == EventType.SHOT.value and ev.team_id == "home":
            b["shots_home"] += 1
        if _event_type(ev) in (EventType.TACKLE.value, EventType.AERIAL.value) and ev.team_id == "away":
            b["defensive_contacts_away"] += 1
        if "final_third_entry" in ev.tags and ev.team_id == "home":
            b["entries_vs_away"] += 1

    return [buckets[m] for m in sorted(buckets.keys())]


def _event_type(ev: MatchEvent) -> str:
    t = ev.type
    return t.value if isinstance(t, EventType) else str(t)


def window_metrics(
    events: list[MatchEvent],
    t0: int,
    t1: int,
    *,
    fullback_id: str = "A03",
    pivot_id: str = "A06",
) -> dict[str, float]:
    subset = [e for e in events if t0 <= e.t_ms <= t1]
    crosses = sum(
        1 for e in subset if _event_type(e) == EventType.CROSS.value and e.team_id == "home"
    )
    duels_lb_lost = sum(
        1
        for e in subset
        if _event_type(e) == EventType.DUEL.value
        and e.player_id == fullback_id
        and e.outcome == "lost"
    )
    duels_lb = sum(
        1 for e in subset if _event_type(e) == EventType.DUEL.value and e.player_id == fullback_id
    )
    mid_zones = {"central_mid", "middle_third"}
    turnovers_mid = sum(
        1
        for e in subset
        if _event_type(e) == EventType.POSSESSION_CHANGE.value
        and e.pitch_zone in mid_zones
    )
    chaos = sum(
        0.12
        for e in subset
        if _event_type(e) == EventType.DUEL.value
        and e.pitch_zone in mid_zones
        and e.player_id == pivot_id
        and e.outcome == "lost"
    )
    lb_duel_rate = (duels_lb_lost / duels_lb) if duels_lb else 0.0
    return {
        "flank_strike_load_home_right": float(crosses),
        "away_lb_duel_loss_rate": round(lb_duel_rate, 3),
        "midfield_turnovers": float(turnovers_mid),
        "midfield_chaos_index": round(chaos, 3),
    }


def build_player_rollups(events: list[MatchEvent]) -> list[dict]:
    stats: dict[str, dict] = defaultdict(
        lambda: {
            "player_id": "",
            "touches": 0,
            "passes_complete": 0,
            "passes_total": 0,
            "duels_won": 0,
            "duels_lost": 0,
            "crosses": 0,
            "progressive_links": 0,
            "max_ball_velocity_mps": 0.0,
            "avg_pass_obstruction_index": 0.0,
            "_pass_obs_sum": 0.0,
            "_pass_obs_n": 0,
        }
    )
    for ev in events:
        if not ev.player_id:
            continue
        s = stats[ev.player_id]
        s["player_id"] = ev.player_id
        s["touches"] += 1
        if _event_type(ev) == EventType.PASS.value:
            s["passes_total"] += 1
            if ev.outcome == "complete":
                s["passes_complete"] += 1
            if ev.metrics.pass_obstruction_index is not None:
                s["_pass_obs_sum"] += ev.metrics.pass_obstruction_index
                s["_pass_obs_n"] += 1
            if ev.end_x and ev.x and ev.end_x - ev.x > 8:
                s["progressive_links"] += 1
        if _event_type(ev) == EventType.CROSS.value:
            s["crosses"] += 1
        if _event_type(ev) == EventType.DUEL.value:
            if ev.outcome == "won":
                s["duels_won"] += 1
            else:
                s["duels_lost"] += 1
        vel = ev.metrics.ball_velocity_mps or ev.metrics.shot_strike_velocity_mps
        if vel:
            s["max_ball_velocity_mps"] = max(s["max_ball_velocity_mps"], vel)
    out = []
    for s in stats.values():
        n = s.pop("_pass_obs_n")
        s["avg_pass_obstruction_index"] = round(s.pop("_pass_obs_sum") / n, 3) if n else 0.0
        if s["passes_total"]:
            s["pass_completion_rate"] = round(s["passes_complete"] / s["passes_total"], 3)
        else:
            s["pass_completion_rate"] = 0.0
        out.append(s)
    return sorted(out, key=lambda r: r["player_id"])
