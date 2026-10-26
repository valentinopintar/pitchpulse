"""Pitch zones and coordinates (0–100). Home attacks +x in period 1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ZoneBounds:
    x_min: float
    x_max: float
    y_min: float
    y_max: float


ZONES: dict[str, ZoneBounds] = {
    "defensive_third": ZoneBounds(0, 33.3, 0, 100),
    "middle_third": ZoneBounds(33.3, 66.6, 0, 100),
    "final_third": ZoneBounds(66.6, 100, 0, 100),
    "right_flank_final_third": ZoneBounds(66.6, 100, 65, 100),
    "left_flank_final_third": ZoneBounds(66.6, 100, 0, 35),
    "central_mid": ZoneBounds(33.3, 66.6, 35, 65),
}


def zone_at(x: float, y: float) -> str:
    if x >= 66.6 and y >= 65:
        return "right_flank_final_third"
    if x >= 66.6 and y <= 35:
        return "left_flank_final_third"
    if x >= 66.6:
        return "final_third"
    if x >= 33.3:
        return "middle_third" if 35 < y < 65 else "middle_third"
    return "defensive_third"


def sample_in_zone(rng, zone: str) -> tuple[float, float]:
    b = ZONES.get(zone, ZONES["middle_third"])
    x = rng.uniform(b.x_min + 2, b.x_max - 2)
    y = rng.uniform(b.y_min + 2, b.y_max - 2)
    return round(x, 1), round(y, 1)


def ms_from_minute(match_minute: float, period: int = 1) -> int:
    """Match clock minute from kickoff (0–45 first half, 45–90+ second half)."""
    _ = period  # period kept for call-site readability in storybeats
    return int(match_minute * 60 * 1000)


def minute_from_ms(t_ms: int) -> float:
    if t_ms >= 45 * 60 * 1000:
        return (t_ms - 45 * 60 * 1000) / 60000.0 + 45.0
    return t_ms / 60000.0
