"""Deterministic metric helpers for synthetic events."""

from __future__ import annotations

import math


def pass_obstruction_index(
    distance_m: float,
    pressure: float,
    progressive_x: float,
    into_box: bool,
) -> float:
    prog = min(1.0, max(0.0, progressive_x / 25.0))
    dist = min(1.0, distance_m / 35.0)
    box = 0.15 if into_box else 0.0
    raw = 0.35 * dist + 0.45 * pressure + 0.2 * prog + box
    return round(min(1.0, max(0.05, raw)), 3)


def lane_threat_score(x: float, y: float, end_x: float | None, end_y: float | None) -> float:
    ex = end_x if end_x is not None else x
    depth = ex / 100.0
    central = 1.0 - abs((y if end_y is None else end_y) - 50.0) / 50.0
    return round(min(1.0, 0.55 * depth + 0.45 * central), 3)


def distance_m(x1: float, y1: float, x2: float, y2: float) -> float:
    # Pitch 105m x 68m scaled to 0-100
    dx = (x2 - x1) * 1.05
    dy = (y2 - y1) * 0.68
    return round(math.hypot(dx, dy), 2)


def expected_strike_value(x: float, y: float, velocity: float) -> float:
    dist_goal = math.hypot(100 - x, 50 - y) * 1.05
    angle_factor = 1.0 - min(1.0, abs(y - 50) / 50.0) * 0.4
    vel = min(1.0, velocity / 32.0)
    raw = angle_factor * (1.0 - min(1.0, dist_goal / 40.0)) * 0.7 + vel * 0.3
    return round(min(1.0, max(0.02, raw)), 3)
