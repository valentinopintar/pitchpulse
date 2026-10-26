"""Deterministic alert rules (Coach / Analyst)."""

from __future__ import annotations

from dataclasses import dataclass, field

from pitchpulse.interpret.window import rolling_metrics
from pitchpulse.schema.events import MatchEvent


@dataclass
class FiredAlert:
    alert_id: str
    t_ms: int
    match_minute: float
    severity: str
    evidence: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class AlertRule:
    alert_id: str
    window_ms: int
    min_crosses: float = 999.0
    min_lb_duel_loss_rate: float = 999.0
    min_mid_turnovers: float = 999.0
    min_mid_chaos: float = 999.0
    min_home_shots: float = 999.0
    min_shot_velocity: float = 999.0
    max_defensive_contact_rate: float = -1.0
    min_final_third_entries: float = 999.0
    min_attacker_chances: float = 999.0
    max_attacker_conversion: float = -1.0
    min_cross_attempts: float = 999.0
    max_cross_productivity: float = -1.0
    min_mid_progressive_attempts: float = 999.0
    max_mid_progression_rate: float = -1.0

    def evaluate(self, window_events: list[MatchEvent], t_ms: int, match_minute: float) -> FiredAlert | None:
        m = rolling_metrics(window_events)
        ok = True
        if self.min_crosses < 900 and m["flank_strike_load_home_right"] < self.min_crosses:
            ok = False
        if self.min_lb_duel_loss_rate < 900 and m["away_lb_duel_loss_rate"] < self.min_lb_duel_loss_rate:
            ok = False
        if self.min_mid_turnovers < 900 and m["midfield_turnovers"] < self.min_mid_turnovers:
            ok = False
        if self.min_mid_chaos < 900 and m["midfield_chaos_index"] < self.min_mid_chaos:
            ok = False
        if self.min_home_shots < 900 and m["home_shots"] < self.min_home_shots:
            ok = False
        if self.min_shot_velocity < 900 and m["max_shot_strike_velocity_mps"] < self.min_shot_velocity:
            ok = False
        if self.max_defensive_contact_rate >= 0 and m["defensive_contact_rate"] > self.max_defensive_contact_rate:
            ok = False
        if self.min_final_third_entries < 900 and m["final_third_entries_vs_away"] < self.min_final_third_entries:
            ok = False
        if self.min_attacker_chances < 900 and m["attacker_chances"] < self.min_attacker_chances:
            ok = False
        if self.max_attacker_conversion >= 0 and m["attacker_conversion_rate"] > self.max_attacker_conversion:
            ok = False
        if self.min_cross_attempts < 900 and m["cross_attempts"] < self.min_cross_attempts:
            ok = False
        if self.max_cross_productivity >= 0 and m["cross_productivity_rate"] > self.max_cross_productivity:
            ok = False
        if self.min_mid_progressive_attempts < 900 and m["mid_progressive_attempts"] < self.min_mid_progressive_attempts:
            ok = False
        if self.max_mid_progression_rate >= 0 and m["mid_progression_rate"] > self.max_mid_progression_rate:
            ok = False
        if not ok:
            return None
        severity = "warning" if self.alert_id != "shot_speed_spike" else "info"
        return FiredAlert(
            alert_id=self.alert_id,
            t_ms=t_ms,
            match_minute=match_minute,
            severity=severity,
            evidence={k: float(v) for k, v in m.items()},
        )


DEFAULT_RULES: list[AlertRule] = [
    AlertRule(
        alert_id="flank_overload_right",
        window_ms=6 * 60 * 1000,
        min_crosses=6,
        min_lb_duel_loss_rate=0.55,
    ),
    AlertRule(
        alert_id="chaos_press_mid",
        window_ms=6 * 60 * 1000,
        min_mid_turnovers=10,
        min_mid_chaos=0.8,
    ),
    AlertRule(
        alert_id="unproductive_crosses",
        window_ms=7 * 60 * 1000,
        min_cross_attempts=4,
        max_cross_productivity=0.40,
    ),
    AlertRule(
        alert_id="midfield_link_break",
        window_ms=7 * 60 * 1000,
        min_mid_progressive_attempts=4,
        max_mid_progression_rate=0.45,
    ),
    AlertRule(
        alert_id="wasteful_finishing",
        window_ms=8 * 60 * 1000,
        min_attacker_chances=3,
        max_attacker_conversion=0.40,
    ),
    AlertRule(
        alert_id="shot_speed_spike",
        window_ms=7 * 60 * 1000,
        min_home_shots=2,
        min_shot_velocity=25.0,
    ),
    AlertRule(
        alert_id="low_defensive_contacts",
        window_ms=7 * 60 * 1000,
        min_final_third_entries=4,
        max_defensive_contact_rate=0.45,
    ),
]
