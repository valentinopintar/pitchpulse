"""Compile story beats into forced event patterns."""

from __future__ import annotations

from random import Random

from pitchpulse.data.emitters import EventFactory
from pitchpulse.data.pitch import ms_from_minute, sample_in_zone
from pitchpulse.schema.events import MatchEvent


def emit_beat_flank_overload(
    factory: EventFactory,
    rng: Random,
    period: int,
    t_start_ms: int,
    t_end_ms: int,
    attacking_team: str,
    crossing_player: str,
    exposed_defender: str,
    dominant_attacker: str,
) -> list[MatchEvent]:
    """Home/right-flank cross overload; away LB loses duels.

    Volume mirrors a real PL window (~6–8 crosses), not a spray every few seconds.
    """
    events: list[MatchEvent] = []
    # ~1 cross / minute; main 6' window hits alert (≥6), shorter 2H window stays lighter.
    span = max(1, t_end_ms - t_start_ms)
    minutes = span / 60_000
    if minutes >= 5.5:
        count = 6
    else:
        count = max(3, min(4, int(round(minutes))))
    for i in range(count):
        t = t_start_ms + int((i + 0.35) * span / count) + rng.randint(-2500, 2500)
        t = min(max(t, t_start_ms), t_end_ms - 1)
        x, y = sample_in_zone(rng, "right_flank_final_third")
        end_x = rng.uniform(88, 96)
        end_y = rng.uniform(40, 60)
        events.append(
            factory.cross(
                t,
                period,
                attacking_team,
                crossing_player,
                x,
                y,
                end_x,
                end_y,
                complete=rng.random() > 0.35,
                pressure=rng.uniform(0.55, 0.85),
            )
        )
        dx, dy = sample_in_zone(rng, "right_flank_final_third")
        events.append(
            factory.duel(
                t + 800,
                period,
                "away" if attacking_team == "home" else "home",
                exposed_defender,
                dominant_attacker,
                dx,
                dy,
                won=rng.random() > 0.72,
                pressure=rng.uniform(0.6, 0.9),
            )
        )
        events.append(
            factory.pressure_pulse(
                t + 1200,
                period,
                attacking_team,
                "right_flank_final_third",
                tension=rng.uniform(0.65, 0.92),
            )
        )
    return events


def emit_beat_midfield_chaos(
    factory: EventFactory,
    rng: Random,
    period: int,
    t_start_ms: int,
    t_end_ms: int,
    pressing_team: str,
    exposed_mid: str,
    presser: str,
) -> list[MatchEvent]:
    """Press storm with enough turnovers for the alert, without flooding the board."""
    events: list[MatchEvent] = []
    victim_team = "away" if pressing_team == "home" else "home"
    # Alert needs ≥10 mid turnovers and chaos ≥0.8 (≈7 lost pivot duels × 0.12).
    span = max(1, t_end_ms - t_start_ms)
    count = 11 if span >= 5 * 60_000 else 6
    # Front-load losses so the chaos index clears the threshold reliably.
    must_lose = 8 if count >= 10 else 4
    for i in range(count):
        t = t_start_ms + int((i + 0.25) * span / count) + rng.randint(-1500, 1500)
        t = min(max(t, t_start_ms), t_end_ms - 1)
        x, y = sample_in_zone(rng, "central_mid")
        won = False if i < must_lose else rng.random() > 0.55
        events.append(
            factory.duel(
                t,
                period,
                victim_team,
                exposed_mid,
                presser,
                x,
                y,
                won=won,
                pressure=rng.uniform(0.5, 0.88),
            )
        )
        # Keep x/y inside middle_third so zone_at → middle_third (counts as mid turnover).
        px = min(65.0, max(35.0, x + rng.uniform(-3, 3)))
        py = min(64.0, max(36.0, y + rng.uniform(-3, 3)))
        events.append(
            factory.possession_change(
                t + 600,
                period,
                victim_team,
                pressing_team,
                px,
                py,
            )
        )
        events.append(
            factory.pressure_pulse(
                t + 900, period, pressing_team, "central_mid", rng.uniform(0.7, 0.95)
            )
        )
    return events


def emit_beat_shot_spike(
    factory: EventFactory,
    rng: Random,
    period: int,
    t_start_ms: int,
    t_end_ms: int,
    team_id: str,
    shooter: str,
) -> list[MatchEvent]:
    """A short finishing flurry — keep shot counts match-realistic (2–4)."""
    events: list[MatchEvent] = []
    count = rng.randint(2, 4)
    span = max(1, t_end_ms - t_start_ms)
    for i in range(count):
        t = t_start_ms + int((i + 0.5) * span / count) + rng.randint(-2000, 2000)
        t = min(max(t, t_start_ms), t_end_ms - 1)
        x = rng.uniform(78, 92)
        y = rng.uniform(35, 65)
        vel = rng.uniform(26, 34)
        on_target = rng.random() > 0.35
        is_goal = on_target and rng.random() < 0.12
        events.append(
            factory.shot(
                t,
                period,
                team_id,
                shooter,
                x,
                y,
                on_target=on_target,
                velocity=vel,
                is_goal=is_goal,
            )
        )
    return events


def emit_beat_low_defensive_contacts(
    factory: EventFactory,
    rng: Random,
    period: int,
    t_start_ms: int,
    t_end_ms: int,
    defending_team: str,
    weak_cb: str,
    attacker: str,
) -> list[MatchEvent]:
    """Entries against with few successful defensive contacts (alert needs ≥4 entries)."""
    events: list[MatchEvent] = []
    attacking = "home" if defending_team == "away" else "away"
    span = max(1, t_end_ms - t_start_ms)
    count = rng.randint(5, 6)
    for i in range(count):
        t = t_start_ms + int((i + 0.3) * span / count) + rng.randint(-2000, 2000)
        t = min(max(t, t_start_ms), t_end_ms - 1)
        x, y = sample_in_zone(rng, "final_third")
        events.append(
            factory.pass_event(
                t,
                period,
                attacking,
                attacker,
                x - 15,
                y,
                x,
                y,
                complete=True,
                pressure=0.4,
                tags=["final_third_entry"],
            )
        )
        if rng.random() > 0.55:
            events.append(
                factory.duel(
                    t + 900,
                    period,
                    defending_team,
                    weak_cb,
                    attacker,
                    x,
                    y,
                    won=False,
                    pressure=0.55,
                )
            )
    return events


def emit_beat_unproductive_crosses(
    factory: EventFactory,
    rng: Random,
    period: int,
    t_start_ms: int,
    t_end_ms: int,
    team_id: str,
    crossing_player: str,
) -> list[MatchEvent]:
    """Wide deliveries that rarely reach a useful target (low cross productivity).

    SofaScore-scale: a busy wide player might attempt ~5 crosses in a spell, not dozens.
    """
    events: list[MatchEvent] = []
    count = 4  # alert needs ≥4; keep winger season-realistic (Cherki ~5 / match)
    span = max(1, t_end_ms - t_start_ms)
    for i in range(count):
        t = t_start_ms + int((i + 0.3) * span / count) + rng.randint(-2000, 2000)
        t = min(max(t, t_start_ms), t_end_ms - 1)
        x, y = sample_in_zone(rng, "right_flank_final_third")
        # Keep productivity clearly under the 0.40 alert threshold.
        productive = rng.random() < 0.18
        end_x = rng.uniform(88, 96) if productive else rng.uniform(70, 82)
        end_y = rng.uniform(40, 60) if productive else rng.uniform(5, 25)
        ev = factory.cross(
            t,
            period,
            team_id,
            crossing_player,
            x,
            y,
            end_x,
            end_y,
            complete=productive,
            pressure=rng.uniform(0.4, 0.75),
        )
        tag = "productive_cross" if productive else "unproductive_cross"
        ev.tags = list(dict.fromkeys([*(ev.tags or []), tag, "delivery"]))
        events.append(ev)
    return events


def emit_beat_wasteful_finishing(
    factory: EventFactory,
    rng: Random,
    period: int,
    t_start_ms: int,
    t_end_ms: int,
    team_id: str,
    shooter: str,
) -> list[MatchEvent]:
    """Attacker gets a handful of big chances but converts poorly (3–5 shots)."""
    events: list[MatchEvent] = []
    count = rng.randint(3, 5)
    span = max(1, t_end_ms - t_start_ms)
    for i in range(count):
        t = t_start_ms + int((i + 0.4) * span / count) + rng.randint(-3000, 3000)
        t = min(max(t, t_start_ms), t_end_ms - 1)
        x = rng.uniform(80, 92)
        y = rng.uniform(32, 68)
        used = rng.random() < 0.25
        vel = rng.uniform(18, 28)
        ev = factory.shot(
            t,
            period,
            team_id,
            shooter,
            x,
            y,
            on_target=used,
            velocity=vel,
            is_goal=False,
        )
        tags = ["shot", "big_chance"]
        if used:
            tags.append("chance_used")
        else:
            tags.append("chance_wasted")
        ev.tags = tags
        events.append(ev)
    return events


def emit_beat_midfield_link_break(
    factory: EventFactory,
    rng: Random,
    period: int,
    t_start_ms: int,
    t_end_ms: int,
    team_id: str,
    passer: str,
) -> list[MatchEvent]:
    """Midfield progressive passes stall — a few failed supplies, not a turnover storm."""
    events: list[MatchEvent] = []
    count = rng.randint(6, 8)
    span = max(1, t_end_ms - t_start_ms)
    for i in range(count):
        # Front-load attempts so the alert fires inside the expected window.
        t = t_start_ms + int((i + 0.15) * span / (count + 1))
        x, y = sample_in_zone(rng, "central_mid")
        complete = rng.random() < 0.34
        end_x = min(95, x + rng.uniform(12, 28))
        end_y = y + rng.uniform(-18, 18)
        events.append(
            factory.pass_event(
                t,
                period,
                team_id,
                passer,
                x,
                y,
                end_x,
                end_y,
                complete=complete,
                pressure=rng.uniform(0.55, 0.9),
                tags=["progressive_attempt", "progressive_link", "midfield_supply"],
            )
        )
        events.append(
            factory.pressure_pulse(
                t + 400,
                period,
                "home" if team_id == "away" else "away",
                "central_mid",
                rng.uniform(0.65, 0.9),
            )
        )
    return events


def emit_beat_player_focus(
    factory: EventFactory,
    rng: Random,
    period: int,
    t_start_ms: int,
    t_end_ms: int,
    team_id: str,
    player_id: str,
) -> list[MatchEvent]:
    """A short spotlight spell — a handful of progressive links, not a 100-pass burst."""
    events: list[MatchEvent] = []
    count = rng.randint(5, 7)
    span = max(1, t_end_ms - t_start_ms)
    x, y = 55.0, 50.0
    for i in range(count):
        t = t_start_ms + int((i + 0.4) * span / count) + rng.randint(-1500, 1500)
        t = min(max(t, t_start_ms), t_end_ms - 1)
        end_x = min(95, x + rng.uniform(8, 18))
        end_y = y + rng.uniform(-12, 12)
        events.append(
            factory.pass_event(
                t,
                period,
                team_id,
                player_id,
                x,
                y,
                end_x,
                end_y,
                complete=rng.random() > 0.12,
                pressure=rng.uniform(0.3, 0.55),
                tags=["progressive_link", "player_focus"],
            )
        )
        x, y = end_x, end_y
    return events


def beat_window_ms(beat: dict, period: int = 1) -> tuple[int, int]:
    start = ms_from_minute(float(beat["minute_start"]), period)
    end = ms_from_minute(float(beat["minute_end"]), period)
    return start, end
