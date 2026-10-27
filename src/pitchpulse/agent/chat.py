"""Agent chat entry point — delegates to the multi-agent bench team."""

from __future__ import annotations

from typing import Any

from pitchpulse.agent.team import run_team


def agent_chat(message: str, engine: str | None = None, audience: str = "coach") -> dict[str, Any]:
    """engine="rules" forces the rule-based team; audience="fan" uses the fan companion team."""
    return run_team(message, engine=engine, audience=audience)
