"""Background possession noise between story beats.

Calibrated to SofaScore / PL team volumes (~350–500 passes per side).
Reference: Man City 482 / Arsenal 335 (Etihad, Apr 2026).
"""

from __future__ import annotations

from random import Random

from pitchpulse.data.emitters import EventFactory
from pitchpulse.schema.events import MatchEvent


def fill_gaps(
    factory: EventFactory,
    rng: Random,
    period: int,
    t_cursor_ms: int,
    t_until_ms: int,
    home_players: list[str],
    away_players: list[str],
) -> tuple[list[MatchEvent], int]:
    """Possession chains dense enough for PL totals, sparse enough to stay realistic."""
    events: list[MatchEvent] = []
    t = t_cursor_ms
    team = "home" if rng.random() > 0.5 else "away"
    touch_bias: dict[str, int] = {}
    # Slight home bias — home story beats burn clock with few open-play passes.
    home_weight = 0.53

    while t < t_until_ms - 5000:
        pool = home_players if team == "home" else away_players
        if not pool:
            break
        outfield = [p for p in pool if not str(p).endswith("01")]
        keepers = [p for p in pool if str(p).endswith("01")]
        base = outfield or pool

        ranked = sorted(base, key=lambda pid: (touch_bias.get(pid, 0), rng.random()))
        n_actors = min(len(ranked), rng.randint(2, min(4, len(ranked))))
        actors = ranked[:n_actors]
        # GK build-outs ~1 in 6 — keepers stay involved without leading the pass table.
        if keepers and rng.random() < 0.16:
            actors = [keepers[0], *actors[: max(1, n_actors - 1)]]

        n_passes = rng.randint(3, 5)
        chunk = factory.filler_pass_chain(t, period, team, actors, n_passes)
        events.extend(chunk)
        for pid in actors:
            touch_bias[pid] = touch_bias.get(pid, 0) + 1

        if chunk and rng.random() > 0.68:
            defender = actors[rng.randint(0, len(actors) - 1)]
            opp_pool = away_players if team == "home" else home_players
            if opp_pool:
                opp = opp_pool[rng.randint(0, len(opp_pool) - 1)]
                last = chunk[-1]
                events.append(
                    factory.duel(
                        last.t_ms + 400,
                        period,
                        team,
                        defender,
                        opp,
                        last.end_x or last.x or 50.0,
                        last.end_y or last.y or 50.0,
                        won=rng.random() > 0.45,
                        pressure=rng.uniform(0.3, 0.7),
                    )
                )
        if chunk:
            # ~4–10s gaps → team pass totals land near 350–480.
            t = chunk[-1].t_ms + rng.randint(4_000, 10_000)
        else:
            t += 8_000
        # Pick next possession side with mild home bias.
        team = "home" if rng.random() < home_weight else "away"
    return events, t
