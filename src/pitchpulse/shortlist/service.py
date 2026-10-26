"""Score bench profiles against alert gaps."""

from __future__ import annotations

from typing import Any

from pitchpulse.shortlist.catalog import RosterPlayer, load_roster

# alert_id → preferred positions + trait weights
ALERT_ROLE_MAP: dict[str, dict[str, Any]] = {
    "flank_overload_right": {
        "positions": ["LB", "WB", "RB"],
        "weights": {"cross_defend": 0.4, "aerial": 0.35, "defensive_duels": 0.15, "pace": 0.1},
        "gap": "Need aerial / cross-defending full-back",
    },
    "chaos_press_mid": {
        "positions": ["CDM", "CM"],
        "weights": {"press_resistance": 0.45, "progressive_pass": 0.3, "defensive_duels": 0.25},
        "gap": "Need press-resistant pivot",
    },
    "unproductive_crosses": {
        "positions": ["RW", "LW", "WB", "CAM"],
        "weights": {"delivery": 0.5, "progressive_pass": 0.25, "pace": 0.25},
        "gap": "Need a wide creator with productive delivery",
    },
    "midfield_link_break": {
        "positions": ["CAM", "CM", "CDM"],
        "weights": {"progressive_pass": 0.5, "press_resistance": 0.3, "delivery": 0.2},
        "gap": "Need progressive midfielder to restore the supply line",
    },
    "wasteful_finishing": {
        "positions": ["ST", "CAM", "RW"],
        "weights": {"finishing": 0.55, "pace": 0.2, "delivery": 0.15, "progressive_pass": 0.1},
        "gap": "Need a clinical finisher who converts big chances",
    },
    "low_defensive_contacts": {
        "positions": ["CB"],
        "weights": {"defensive_duels": 0.45, "aerial": 0.4, "cross_defend": 0.15},
        "gap": "Need duel-winning centre-back",
    },
    "shot_speed_spike": {
        "positions": ["CB", "CDM"],
        "weights": {"defensive_duels": 0.4, "aerial": 0.3, "press_resistance": 0.3},
        "gap": "Need box protection / first-contact defender",
    },
}


def _score(player: RosterPlayer, weights: dict[str, float]) -> float:
    traits = {
        "aerial": player.aerial,
        "cross_defend": player.cross_defend,
        "defensive_duels": player.defensive_duels,
        "press_resistance": player.press_resistance,
        "progressive_pass": player.progressive_pass,
        "pace": player.pace,
        "finishing": player.finishing,
        "delivery": player.delivery,
    }
    total = 0.0
    for key, w in weights.items():
        total += traits.get(key, 0.0) * w
    return round(total, 4)


def _why(player: RosterPlayer, alert_id: str, score: float) -> str:
    if alert_id == "flank_overload_right":
        return (
            f"{player.name} fits the wide leak: cross_defend={player.cross_defend:.2f}, "
            f"aerial={player.aerial:.2f} (fit {score:.2f})."
        )
    if alert_id == "chaos_press_mid":
        return (
            f"{player.name} can settle tempo: press_resistance={player.press_resistance:.2f}, "
            f"progressive_pass={player.progressive_pass:.2f} (fit {score:.2f})."
        )
    if alert_id == "low_defensive_contacts":
        return (
            f"{player.name} raises first contacts: defensive_duels={player.defensive_duels:.2f}, "
            f"aerial={player.aerial:.2f} (fit {score:.2f})."
        )
    if alert_id == "unproductive_crosses":
        return (
            f"{player.name} upgrades delivery: delivery={player.delivery:.2f}, "
            f"pace={player.pace:.2f} (fit {score:.2f})."
        )
    if alert_id == "wasteful_finishing":
        return (
            f"{player.name} is clinical: finishing={player.finishing:.2f}, "
            f"pace={player.pace:.2f} (fit {score:.2f})."
        )
    if alert_id == "midfield_link_break":
        return (
            f"{player.name} restores supply: progressive_pass={player.progressive_pass:.2f}, "
            f"press_resistance={player.press_resistance:.2f} (fit {score:.2f})."
        )
    return f"{player.name} scored {score:.2f} against {alert_id}."


# Attack-quality gaps map to the attacking side's bench; defensive leaks to away.
ATTACK_SIDE_ALERTS = frozenset(
    {"wasteful_finishing", "unproductive_crosses"}
)


def default_team_side(alert_id: str) -> str:
    return "home" if alert_id in ATTACK_SIDE_ALERTS else "away"


def propose_roles_for_alert(
    alert_id: str,
    *,
    team_side: str | None = None,
    bench_only: bool = True,
    limit: int = 3,
) -> dict[str, Any]:
    cfg = ALERT_ROLE_MAP.get(alert_id)
    if not cfg:
        return {
            "alert_id": alert_id,
            "gap": "No role mapping for this alert",
            "candidates": [],
        }

    side = team_side or default_team_side(alert_id)
    positions = set(cfg["positions"])
    weights = cfg["weights"]
    roster = load_roster()
    scored: list[tuple[float, RosterPlayer]] = []
    for p in roster:
        if p.team_side != side:
            continue
        if bench_only and not p.on_bench:
            continue
        if p.position not in positions:
            continue
        scored.append((_score(p, weights), p))

    scored.sort(key=lambda x: x[0], reverse=True)
    candidates = []
    for score, p in scored[:limit]:
        row = p.to_dict()
        row["fit_score"] = score
        row["why"] = _why(p, alert_id, score)
        candidates.append(row)

    return {
        "alert_id": alert_id,
        "gap": cfg["gap"],
        "team_side": side,
        "preferred_positions": list(positions),
        "candidates": candidates,
    }
