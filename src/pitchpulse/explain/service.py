"""Explain alerts for Coach / Analyst / Fan — English templates + optional Azure OpenAI."""

from __future__ import annotations

import json
from typing import Any

from pitchpulse.explain import azure_client
from pitchpulse.explain.templates import fan_substitution_copy, template_modes_for_alert
from pitchpulse.personalize.viewer import ViewerProfile


SYSTEM_PROMPT = """You are PitchPulse, a studio match-intelligence narrator for synthetic football.
Return ONLY valid JSON with this shape:
{
  "why": "...",
  "coach": "...",
  "analyst": "...",
  "fan": "..."
}
Rules:
- English only.
- Coach: actionable cues (no private locker-room speech); suggest what to change on the pitch.
- Analyst: evidence-first, use the metric names provided.
- Fan: plain language; do not invent private coach instructions.
- Keep each string under 320 characters.
- Football context only; fictional clubs/players are fine.
"""


class ExplainService:
    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    def explain_alert(
        self,
        *,
        alert_id: str,
        evidence: dict[str, Any] | None = None,
        match_minute: float | None = None,
        related_player_ids: list[str] | None = None,
        use_llm: bool = True,
    ) -> dict[str, Any]:
        cache_key = f"{alert_id}|{json.dumps(evidence or {}, sort_keys=True)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        modes = template_modes_for_alert(alert_id, evidence)
        source = "template"

        if use_llm and azure_client.llm_configured():
            user = json.dumps(
                {
                    "alert_id": alert_id,
                    "match_minute": match_minute,
                    "evidence": evidence or {},
                    "related_player_ids": related_player_ids or [],
                },
                ensure_ascii=False,
            )
            llm = azure_client.chat_json(SYSTEM_PROMPT, user)
            if llm and all(k in llm for k in ("why", "coach", "analyst", "fan")):
                modes = {
                    "why": str(llm["why"]),
                    "coach": str(llm["coach"]),
                    "analyst": str(llm["analyst"]),
                    "fan": str(llm["fan"]),
                }
                source = azure_client.provider() or "template"

        out = {
            "alert_id": alert_id,
            "match_minute": match_minute,
            "evidence": evidence or {},
            "related_player_ids": related_player_ids or [],
            "source": source,
            "azure_configured": azure_client.azure_configured(),
            "modes": {
                "coach": modes["coach"],
                "analyst": modes["analyst"],
                "fan": modes["fan"],
            },
            "why": modes["why"],
        }
        self._cache[cache_key] = out
        return out

    def for_viewer(self, explanation: dict[str, Any], viewer: ViewerProfile) -> dict[str, Any]:
        mode_key = "coach" if viewer.mode == "coach" else "fan"
        text = explanation["modes"].get(mode_key) or explanation["modes"]["coach"]
        return {
            "alert_id": explanation["alert_id"],
            "mode": viewer.mode,
            "language": "en",
            "text": text,
            "why_it_matters": explanation.get("why") or "",
            "source": explanation.get("source"),
            "favorite_player_id": viewer.favorite_player_id,
        }

    def explain_substitution(self, moment: dict[str, Any]) -> dict[str, Any]:
        return {
            "moment_id": moment.get("moment_id"),
            "addresses_alert_id": moment.get("addresses_alert_id"),
            "t_sub_ms": moment.get("t_sub_ms"),
            "player_off_id": moment.get("player_off_id"),
            "player_on_id": moment.get("player_on_id"),
            "metrics_before": moment.get("metrics_before"),
            "metrics_after": moment.get("metrics_after"),
            "narrative": fan_substitution_copy(moment),
            "source": "template",
        }


EXPLAIN = ExplainService()
