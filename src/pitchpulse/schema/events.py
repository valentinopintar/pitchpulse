"""Canonical synthetic event contract (PitchPulse naming)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    PASS = "pass"
    CARRY = "carry"
    SHOT = "shot"
    TACKLE = "tackle"
    INTERCEPTION = "interception"
    AERIAL = "aerial"
    FOUL = "foul"
    CARD = "card"
    CROSS = "cross"
    DUEL = "duel"
    POSSESSION_CHANGE = "possession_change"
    PRESSURE = "pressure"
    SUBSTITUTION = "substitution"
    SPEED_BURST = "speed_burst"
    MATCH_META = "match_meta"


@dataclass
class EventMetrics:
    pass_trajectory_m: float | None = None
    ball_velocity_mps: float | None = None
    pass_obstruction_index: float | None = None
    carrier_pressure_load: float | None = None
    lane_threat_score: float | None = None
    duel_contact_quality: float | None = None
    zone_tension_index: float | None = None
    shot_strike_velocity_mps: float | None = None
    expected_strike_value: float | None = None


@dataclass
class MatchEvent:
    match_id: str
    event_id: str
    t_ms: int
    period: int
    type: EventType | str
    team_id: str
    player_id: str | None = None
    opponent_id: str | None = None
    x: float | None = None
    y: float | None = None
    end_x: float | None = None
    end_y: float | None = None
    outcome: str | None = None
    pitch_zone: str | None = None
    metrics: EventMetrics = field(default_factory=EventMetrics)
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_json_line(self) -> str:
        payload = asdict(self)
        if isinstance(self.type, EventType):
            payload["type"] = self.type.value
        return json.dumps(payload, separators=(",", ":"))

    @classmethod
    def from_json_line(cls, line: str) -> MatchEvent:
        raw = json.loads(line)
        metrics_raw = raw.pop("metrics", {}) or {}
        ev_type = raw.get("type")
        if isinstance(ev_type, str):
            try:
                raw["type"] = EventType(ev_type)
            except ValueError:
                raw["type"] = ev_type
        return cls(metrics=EventMetrics(**metrics_raw), **raw)


@dataclass
class ExpectedAlert:
    alert_id: str
    t_start_ms: int
    t_peak_ms: int
    t_end_ms: int
    storyline: str
    leak_summary: str
    coach_gap: str
    audience_primary: list[str] = field(default_factory=lambda: ["coach", "analyst"])
    related_player_ids: list[str] = field(default_factory=list)


@dataclass
class SubstitutionMoment:
    moment_id: str
    t_sub_ms: int
    team_id: str
    player_off_id: str
    player_on_id: str
    addresses_alert_id: str
    fan_window_start_ms: int
    fan_window_end_ms: int
    narrative_hook: str
    metrics_before: dict[str, float]
    metrics_after: dict[str, float]
    observable_outcome: str
