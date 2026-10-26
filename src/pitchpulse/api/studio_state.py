"""Shared studio viewer + match context for explain endpoints."""

from __future__ import annotations

import json
from typing import Any

from pitchpulse.data.paths import match_dir
from pitchpulse.personalize.viewer import ViewerProfile


class StudioContext:
    def __init__(self) -> None:
        self.viewer = ViewerProfile()
        self.match_id: str | None = None
        self._expected_alerts: list[dict[str, Any]] = []
        self._subs: list[dict[str, Any]] = []

    def bind_match(self, match_id: str) -> None:
        self.match_id = match_id
        mdir = match_dir(match_id)
        alerts_path = mdir / "expected_alerts.json"
        subs_path = mdir / "substitution_moments.json"
        self._expected_alerts = (
            json.loads(alerts_path.read_text(encoding="utf-8")) if alerts_path.exists() else []
        )
        self._subs = json.loads(subs_path.read_text(encoding="utf-8")) if subs_path.exists() else []

    def related_players(self, alert_id: str) -> list[str]:
        for a in self._expected_alerts:
            if a.get("alert_id") == alert_id:
                return list(a.get("related_player_ids") or [])
        return []

    def expected_alert(self, alert_id: str) -> dict[str, Any] | None:
        for a in self._expected_alerts:
            if a.get("alert_id") == alert_id:
                return a
        return None

    def substitutions(self) -> list[dict[str, Any]]:
        return list(self._subs)

    def substitution(self, moment_id: str) -> dict[str, Any] | None:
        for s in self._subs:
            if s.get("moment_id") == moment_id:
                return s
        return None


STUDIO = StudioContext()
