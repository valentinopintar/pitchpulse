"""Live scoreline from the goal timeline in meta.json (`goals: [{minute, team_side, player_id, …}]`)."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pitchpulse.data.paths import match_dir


@lru_cache(maxsize=8)
def _meta(match_id: str) -> dict[str, Any]:
    path = match_dir(match_id) / "meta.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def goals(match_id: str) -> list[dict[str, Any]]:
    return sorted(_meta(match_id).get("goals") or [], key=lambda g: float(g["minute"]))


def goals_until(match_id: str, minute: float) -> list[dict[str, Any]]:
    return [g for g in goals(match_id) if float(g["minute"]) <= minute]


def score_at(match_id: str | None, minute: float) -> dict[str, Any]:
    """Score at `minute`. Matches without a goal timeline fall back to the final score."""
    if not match_id:
        return {"home": 0, "away": 0, "scoreline": "0-0", "goals": [], "last_goal": None}
    meta = _meta(match_id)
    if "goals" not in meta:
        final = meta.get("final_score") or "0-0"
        home, _, away = final.partition("-")
        return {
            "home": int(home or 0),
            "away": int(away or 0),
            "scoreline": final,
            "goals": [],
            "last_goal": None,
        }
    so_far = goals_until(match_id, minute)
    home = sum(1 for g in so_far if g["team_side"] == "home")
    away = len(so_far) - home
    return {
        "home": home,
        "away": away,
        "scoreline": f"{home}-{away}",
        "goals": so_far,
        "last_goal": so_far[-1] if so_far else None,
    }
