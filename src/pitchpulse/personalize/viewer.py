"""Viewer personalization state (English-only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Mode = Literal["coach", "fan"]


@dataclass
class ViewerProfile:
    mode: Mode = "coach"
    language: str = "en"
    favorite_player_id: str | None = None
    favorite_club: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> ViewerProfile:
        data = data or {}
        mode = str(data.get("mode", "coach")).lower()
        if mode == "analyst":
            mode = "coach"
        if mode not in ("coach", "fan"):
            mode = "coach"
        return cls(
            mode=mode,  # type: ignore[arg-type]
            language="en",
            favorite_player_id=data.get("favorite_player_id"),
            favorite_club=data.get("favorite_club"),
        )
