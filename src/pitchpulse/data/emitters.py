"""Build typed MatchEvent instances."""

from __future__ import annotations

from random import Random

from pitchpulse.data import metrics as m
from pitchpulse.data.pitch import zone_at
from pitchpulse.schema.events import EventMetrics, EventType, MatchEvent


class EventFactory:
    def __init__(self, match_id: str, rng: Random):
        self.match_id = match_id
        self.rng = rng
        self._seq = 0

    def _id(self) -> str:
        self._seq += 1
        return f"e{self._seq:07d}"

    def meta(
        self,
        t_ms: int,
        period: int,
        label: str,
        team_id: str = "match",
        **extra: object,
    ) -> MatchEvent:
        return MatchEvent(
            match_id=self.match_id,
            event_id=self._id(),
            t_ms=t_ms,
            period=period,
            type=EventType.MATCH_META,
            team_id=team_id,
            outcome=label,
            meta=dict(extra),
        )

    def pass_event(
        self,
        t_ms: int,
        period: int,
        team_id: str,
        player_id: str,
        x: float,
        y: float,
        end_x: float,
        end_y: float,
        complete: bool,
        pressure: float,
        tags: list[str] | None = None,
    ) -> MatchEvent:
        dist = m.distance_m(x, y, end_x, end_y)
        prog = end_x - x
        into_box = end_x > 84 and 25 < end_y < 75
        obs = m.pass_obstruction_index(dist, pressure, prog, into_box)
        vel = self.rng.uniform(8, 22) if complete else self.rng.uniform(6, 14)
        return MatchEvent(
            match_id=self.match_id,
            event_id=self._id(),
            t_ms=t_ms,
            period=period,
            type=EventType.PASS,
            team_id=team_id,
            player_id=player_id,
            x=x,
            y=y,
            end_x=end_x,
            end_y=end_y,
            outcome="complete" if complete else "incomplete",
            pitch_zone=zone_at(x, y),
            metrics=EventMetrics(
                pass_trajectory_m=dist,
                ball_velocity_mps=round(vel, 2),
                pass_obstruction_index=obs,
                carrier_pressure_load=round(pressure, 3),
                lane_threat_score=m.lane_threat_score(x, y, end_x, end_y),
            ),
            tags=tags or [],
        )

    def cross(
        self,
        t_ms: int,
        period: int,
        team_id: str,
        player_id: str,
        x: float,
        y: float,
        end_x: float,
        end_y: float,
        complete: bool,
        pressure: float,
    ) -> MatchEvent:
        ev = self.pass_event(
            t_ms,
            period,
            team_id,
            player_id,
            x,
            y,
            end_x,
            end_y,
            complete,
            pressure,
            tags=["cross", "flank_strike"],
        )
        ev.type = EventType.CROSS
        return ev

    def duel(
        self,
        t_ms: int,
        period: int,
        team_id: str,
        player_id: str,
        opponent_id: str,
        x: float,
        y: float,
        won: bool,
        pressure: float,
    ) -> MatchEvent:
        return MatchEvent(
            match_id=self.match_id,
            event_id=self._id(),
            t_ms=t_ms,
            period=period,
            type=EventType.DUEL,
            team_id=team_id,
            player_id=player_id,
            opponent_id=opponent_id,
            x=x,
            y=y,
            outcome="won" if won else "lost",
            pitch_zone=zone_at(x, y),
            metrics=EventMetrics(
                duel_contact_quality=round(0.85 if won else 0.25, 3),
                carrier_pressure_load=round(pressure, 3),
                zone_tension_index=round(min(1.0, pressure + 0.2), 3),
            ),
            tags=["duel"],
        )

    def pressure_pulse(
        self,
        t_ms: int,
        period: int,
        team_id: str,
        zone: str,
        tension: float,
    ) -> MatchEvent:
        x, y = 50.0, 50.0
        if "right" in zone:
            x, y = 78.0, 82.0
        elif "mid" in zone:
            x, y = 50.0, 50.0
        return MatchEvent(
            match_id=self.match_id,
            event_id=self._id(),
            t_ms=t_ms,
            period=period,
            type=EventType.PRESSURE,
            team_id=team_id,
            x=x,
            y=y,
            pitch_zone=zone,
            outcome="pulse",
            metrics=EventMetrics(zone_tension_index=round(tension, 3)),
            tags=["zone_pressure"],
        )

    def possession_change(
        self,
        t_ms: int,
        period: int,
        from_team: str,
        to_team: str,
        x: float,
        y: float,
    ) -> MatchEvent:
        return MatchEvent(
            match_id=self.match_id,
            event_id=self._id(),
            t_ms=t_ms,
            period=period,
            type=EventType.POSSESSION_CHANGE,
            team_id=to_team,
            x=x,
            y=y,
            pitch_zone=zone_at(x, y),
            outcome="turnover",
            meta={"from_team": from_team},
            tags=["turnover"],
        )

    def shot(
        self,
        t_ms: int,
        period: int,
        team_id: str,
        player_id: str,
        x: float,
        y: float,
        on_target: bool,
        velocity: float,
        is_goal: bool = False,
    ) -> MatchEvent:
        esv = m.expected_strike_value(x, y, velocity)
        if is_goal:
            outcome = "goal"
        elif on_target:
            outcome = "on_target"
        else:
            outcome = "off_target"
        return MatchEvent(
            match_id=self.match_id,
            event_id=self._id(),
            t_ms=t_ms,
            period=period,
            type=EventType.SHOT,
            team_id=team_id,
            player_id=player_id,
            x=x,
            y=y,
            outcome=outcome,
            pitch_zone=zone_at(x, y),
            metrics=EventMetrics(
                ball_velocity_mps=round(velocity, 2),
                shot_strike_velocity_mps=round(velocity, 2),
                expected_strike_value=esv,
            ),
            tags=["shot", "goal"] if is_goal else ["shot"],
        )

    def substitution(
        self,
        t_ms: int,
        period: int,
        team_id: str,
        player_off: str,
        player_on: str,
        addresses_alert: str,
    ) -> MatchEvent:
        return MatchEvent(
            match_id=self.match_id,
            event_id=self._id(),
            t_ms=t_ms,
            period=period,
            type=EventType.SUBSTITUTION,
            team_id=team_id,
            player_id=player_on,
            opponent_id=player_off,
            outcome="sub",
            meta={"player_off": player_off, "player_on": player_on, "addresses_alert": addresses_alert},
            tags=["substitution"],
        )

    def filler_pass_chain(
        self,
        t_ms: int,
        period: int,
        team_id: str,
        player_ids: list[str],
        n: int,
    ) -> list[MatchEvent]:
        events: list[MatchEvent] = []
        t = t_ms
        x, y = self.rng.uniform(35, 55), self.rng.uniform(40, 60)
        for i in range(n):
            pid = player_ids[i % len(player_ids)]
            end_x = min(99, x + self.rng.uniform(-8, 12))
            end_y = max(1, min(99, y + self.rng.uniform(-15, 15)))
            pressure = self.rng.uniform(0.15, 0.45)
            # Keep background completion high so match-long "losses" stay realistic.
            complete = self.rng.random() > 0.08
            events.append(
                self.pass_event(t, period, team_id, pid, x, y, end_x, end_y, complete, pressure)
            )
            t += self.rng.randint(800, 2200)
            x, y = end_x, end_y
        return events
