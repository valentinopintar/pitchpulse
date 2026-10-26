"""Thin tool layer — same services the studio UI uses."""

from __future__ import annotations

from typing import Any, Callable

from pitchpulse.api.replay_session import SESSION
from pitchpulse.api.studio_state import STUDIO
from pitchpulse.explain.service import EXPLAIN
from pitchpulse.personalize.viewer import ViewerProfile
from pitchpulse.render.overlay import build_overlay_packet
from pitchpulse.personalize.halftime import build_halftime_summary
from pitchpulse.shortlist.service import propose_roles_for_alert


def get_match_clock() -> dict[str, Any]:
    st = SESSION.status()
    return {
        "match_id": st.match_id,
        "t_ms": st.t_ms,
        "match_minute": st.match_minute,
        "period": 1 if st.match_minute < 45 else 2,
        "running": st.running,
    }


def get_match_state() -> dict[str, Any]:
    return SESSION.snapshot()


def list_alerts() -> dict[str, Any]:
    st = SESSION.status()
    return {
        "active_alert_ids": st.active_alert_ids,
        "match_minute": st.match_minute,
    }


def explain_alert(alert_id: str, use_llm: bool = False) -> dict[str, Any]:
    st = SESSION.status()
    explanation = EXPLAIN.explain_alert(
        alert_id=alert_id,
        evidence={},
        match_minute=st.match_minute,
        related_player_ids=STUDIO.related_players(alert_id),
        use_llm=use_llm,
    )
    return {
        "explanation": explanation,
        "personalized": EXPLAIN.for_viewer(explanation, STUDIO.viewer),
    }


def set_viewer_profile(
    mode: str = "coach",
    language: str = "en",
    favorite_player_id: str | None = None,
) -> dict[str, Any]:
    _ = language  # English-only product
    STUDIO.viewer = ViewerProfile.from_dict(
        {
            "mode": mode,
            "language": "en",
            "favorite_player_id": favorite_player_id,
        }
    )
    return STUDIO.viewer.to_dict()


def get_overlay_packet(alert_id: str) -> dict[str, Any]:
    st = SESSION.status()
    explanation = EXPLAIN.explain_alert(
        alert_id=alert_id,
        evidence={},
        match_minute=st.match_minute,
        related_player_ids=STUDIO.related_players(alert_id),
        use_llm=False,
    )
    return build_overlay_packet(
        alert_id=alert_id,
        t_ms=st.t_ms,
        explanation=explanation,
    )


def propose_roles(alert_id: str, team_side: str | None = None) -> dict[str, Any]:
    return propose_roles_for_alert(alert_id, team_side=team_side, bench_only=True, limit=3)


def generate_match_recap() -> dict[str, Any]:
    if not STUDIO.match_id:
        return {"error": "No match loaded"}
    if STUDIO.viewer.mode == "fan":
        return get_fan_halftime()
    alerts = []
    for a in STUDIO._expected_alerts:
        exp = EXPLAIN.explain_alert(
            alert_id=a["alert_id"],
            evidence={},
            match_minute=(a.get("t_peak_ms") or 0) / 60000.0,
            related_player_ids=a.get("related_player_ids"),
            use_llm=False,
        )
        alerts.append(EXPLAIN.for_viewer(exp, STUDIO.viewer))
    subs = STUDIO.substitutions()
    return {
        "match_id": STUDIO.match_id,
        "mode": STUDIO.viewer.mode,
        "language": "en",
        "alerts": alerts,
        "substitutions": [EXPLAIN.explain_substitution(s)["narrative"] for s in subs],
    }


def get_fan_halftime() -> dict[str, Any]:
    match_id = STUDIO.match_id or "syn-001"
    return build_halftime_summary(match_id)


TOOL_SPECS: list[dict[str, Any]] = [
    {"name": "get_match_clock", "description": "Current match clock and period"},
    {"name": "get_match_state", "description": "Rolling tactical state snapshot (coach)"},
    {"name": "list_alerts", "description": "Active coaching alert ids"},
    {"name": "explain_alert", "description": "Explain an alert for current viewer"},
    {"name": "set_viewer_profile", "description": "Set coach|fan (analyst maps to coach)"},
    {"name": "get_overlay_packet", "description": "On-screen graphic JSON for an alert"},
    {"name": "propose_roles_for_alert", "description": "Bench profiles that can stop the gap (coach)"},
    {"name": "generate_match_recap", "description": "Coach recap or fan halftime summary"},
    {"name": "get_fan_halftime", "description": "Living-room Match Day Summary (halftime)"},
]


def dispatch(name: str, args: dict[str, Any] | None = None) -> Any:
    args = args or {}
    table: dict[str, Callable[..., Any]] = {
        "get_match_clock": get_match_clock,
        "get_match_state": get_match_state,
        "list_alerts": list_alerts,
        "explain_alert": lambda: explain_alert(args.get("alert_id", "flank_overload_right"), args.get("use_llm", False)),
        "set_viewer_profile": lambda: set_viewer_profile(
            args.get("mode", "coach"),
            args.get("language", "en"),
            args.get("favorite_player_id"),
        ),
        "get_overlay_packet": lambda: get_overlay_packet(args.get("alert_id", "flank_overload_right")),
        "propose_roles_for_alert": lambda: propose_roles(
            args.get("alert_id", "flank_overload_right"),
            args.get("team_side"),
        ),
        "generate_match_recap": generate_match_recap,
        "get_fan_halftime": get_fan_halftime,
    }
    if name not in table:
        return {"error": f"Unknown tool: {name}", "available": [t["name"] for t in TOOL_SPECS]}
    return table[name]()
