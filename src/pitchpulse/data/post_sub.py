"""Observable recovery patterns after substitutions (fan-visible metrics)."""

from __future__ import annotations

from random import Random

from pitchpulse.data.emitters import EventFactory
from pitchpulse.data.pitch import sample_in_zone
from pitchpulse.schema.events import MatchEvent


def emit_flank_recovery(
    factory: EventFactory,
    rng: Random,
    t_start_ms: int,
    t_end_ms: int,
    defending_team: str,
    fullback_id: str,
) -> list[MatchEvent]:
    """Fewer crosses; new full-back wins duels."""
    events: list[MatchEvent] = []
    t = t_start_ms
    while t < t_end_ms:
        x, y = sample_in_zone(rng, "right_flank_final_third")
        events.append(
            factory.duel(
                t,
                2,
                defending_team,
                fullback_id,
                "H09",
                x,
                y,
                won=rng.random() > 0.35,
                pressure=rng.uniform(0.45, 0.7),
            )
        )
        t += rng.randint(45000, 90000)
    return events


def emit_mid_recovery(
    factory: EventFactory,
    rng: Random,
    t_start_ms: int,
    t_end_ms: int,
    pivot_id: str,
) -> list[MatchEvent]:
    events: list[MatchEvent] = []
    t = t_start_ms
    while t < t_end_ms:
        x, y = sample_in_zone(rng, "central_mid")
        events.append(
            factory.pass_event(
                t,
                2,
                "away",
                pivot_id,
                x,
                y,
                min(99, x + rng.uniform(5, 12)),
                y + rng.uniform(-8, 8),
                complete=True,
                pressure=rng.uniform(0.35, 0.55),
                tags=["tempo_reset"],
            )
        )
        t += rng.randint(25_000, 45_000)
    return events
