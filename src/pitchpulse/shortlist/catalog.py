"""Load synthetic bench / roster catalog."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from pitchpulse.data.paths import roster_path


@dataclass
class RosterPlayer:
    player_id: str
    name: str
    position: str
    team_side: str
    on_bench: bool
    aerial: float
    cross_defend: float
    defensive_duels: float
    press_resistance: float
    progressive_pass: float
    pace: float
    finishing: float
    delivery: float
    style_tags: list[str]

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "position": self.position,
            "team_side": self.team_side,
            "on_bench": self.on_bench,
            "traits": {
                "aerial": self.aerial,
                "cross_defend": self.cross_defend,
                "defensive_duels": self.defensive_duels,
                "press_resistance": self.press_resistance,
                "progressive_pass": self.progressive_pass,
                "pace": self.pace,
                "finishing": self.finishing,
                "delivery": self.delivery,
            },
            "style_tags": self.style_tags,
        }


def load_roster(path: Path | None = None) -> list[RosterPlayer]:
    csv_path = path or roster_path()
    players: list[RosterPlayer] = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            players.append(
                RosterPlayer(
                    player_id=row["player_id"],
                    name=row["name"],
                    position=row["position"],
                    team_side=row.get("team_side", "away"),
                    on_bench=str(row.get("on_bench", "1")) in ("1", "true", "True"),
                    aerial=float(row["aerial"]),
                    cross_defend=float(row["cross_defend"]),
                    defensive_duels=float(row["defensive_duels"]),
                    press_resistance=float(row["press_resistance"]),
                    progressive_pass=float(row["progressive_pass"]),
                    pace=float(row["pace"]),
                    finishing=float(row.get("finishing") or 0.45),
                    delivery=float(row.get("delivery") or row.get("progressive_pass") or 0.45),
                    style_tags=[t for t in (row.get("style_tags") or "").split(";") if t],
                )
            )
    return players
