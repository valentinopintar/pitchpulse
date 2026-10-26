"""Rolling-window metrics for alert rules."""

from __future__ import annotations

from pitchpulse.data.snapshots import _event_type, window_metrics
from pitchpulse.schema.events import EventType, MatchEvent

MID_ZONES = frozenset({"central_mid", "middle_third"})


def rolling_metrics(
    events: list[MatchEvent],
    *,
    fullback_id: str = "A03",
    pivot_id: str = "A06",
    weak_cb_id: str = "A05",
) -> dict[str, float]:
    """Metrics over the provided event slice (caller sets the time window)."""
    if not events:
        return {
            "flank_strike_load_home_right": 0.0,
            "away_lb_duel_loss_rate": 0.0,
            "midfield_turnovers": 0.0,
            "midfield_chaos_index": 0.0,
            "home_shots": 0.0,
            "max_shot_strike_velocity_mps": 0.0,
            "final_third_entries_vs_away": 0.0,
            "defensive_contacts_away": 0.0,
            "defensive_contact_rate": 0.0,
            "attacker_chances": 0.0,
            "attacker_chances_used": 0.0,
            "attacker_conversion_rate": 1.0,
            "cross_attempts": 0.0,
            "cross_productive": 0.0,
            "cross_productivity_rate": 1.0,
            "mid_progressive_attempts": 0.0,
            "mid_progressive_complete": 0.0,
            "mid_progression_rate": 1.0,
        }

    t0 = events[0].t_ms
    t1 = events[-1].t_ms
    base = window_metrics(events, t0, t1, fullback_id=fullback_id, pivot_id=pivot_id)

    home_shots = 0
    max_shot_vel = 0.0
    entries = 0
    def_contacts = 0
    cb_duels_won = 0
    cb_duels_total = 0
    attacker_chances = 0
    attacker_used = 0
    cross_attempts = 0
    cross_productive = 0
    mid_prog_attempts = 0
    mid_prog_ok = 0

    for ev in events:
        et = _event_type(ev)
        tags = set(ev.tags or [])
        if et == EventType.SHOT.value and ev.team_id == "home":
            home_shots += 1
            vel = ev.metrics.shot_strike_velocity_mps or ev.metrics.ball_velocity_mps or 0.0
            max_shot_vel = max(max_shot_vel, vel)
        if et == EventType.SHOT.value and ("big_chance" in tags or ev.player_id in ("H10", "A10")):
            attacker_chances += 1
            if ev.outcome in ("on_target", "goal") or "chance_used" in tags:
                attacker_used += 1
        if et == EventType.CROSS.value:
            cross_attempts += 1
            if "productive_cross" in tags or (
                ev.outcome == "complete" and (ev.end_x or 0) >= 84 and 25 < (ev.end_y or 50) < 75
            ):
                cross_productive += 1
        if "progressive_attempt" in tags or (
            et == EventType.PASS.value and "progressive_link" in tags and (ev.pitch_zone or "") in MID_ZONES
        ):
            mid_prog_attempts += 1
            if ev.outcome == "complete":
                mid_prog_ok += 1
        if "final_third_entry" in tags and ev.team_id == "home":
            entries += 1
        if et in (EventType.TACKLE.value, EventType.AERIAL.value) and ev.team_id == "away":
            def_contacts += 1
        if et == EventType.DUEL.value and ev.player_id == weak_cb_id:
            cb_duels_total += 1
            if ev.outcome == "won":
                cb_duels_won += 1

    contact_rate = def_contacts / entries if entries else 1.0
    conversion = attacker_used / attacker_chances if attacker_chances else 1.0
    cross_rate = cross_productive / cross_attempts if cross_attempts else 1.0
    mid_rate = mid_prog_ok / mid_prog_attempts if mid_prog_attempts else 1.0

    base.update(
        {
            "home_shots": float(home_shots),
            "max_shot_strike_velocity_mps": round(max_shot_vel, 2),
            "final_third_entries_vs_away": float(entries),
            "defensive_contacts_away": float(def_contacts),
            "defensive_contact_rate": round(contact_rate, 3),
            "weak_cb_duel_win_rate": round(cb_duels_won / cb_duels_total, 3) if cb_duels_total else 0.0,
            "attacker_chances": float(attacker_chances),
            "attacker_chances_used": float(attacker_used),
            "attacker_conversion_rate": round(conversion, 3),
            "cross_attempts": float(cross_attempts),
            "cross_productive": float(cross_productive),
            "cross_productivity_rate": round(cross_rate, 3),
            "mid_progressive_attempts": float(mid_prog_attempts),
            "mid_progressive_complete": float(mid_prog_ok),
            "mid_progression_rate": round(mid_rate, 3),
        }
    )
    return base
