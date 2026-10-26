"""Rule-based agent chat with tool routing (English)."""

from __future__ import annotations

import re
from typing import Any

from pitchpulse.agent import tools


def _detect_alert_id(text: str) -> str | None:
    lower = text.lower()
    mapping = [
        ("wasteful", "wasteful_finishing"),
        ("finish", "wasteful_finishing"),
        ("chance", "wasteful_finishing"),
        ("striker", "wasteful_finishing"),
        ("delivery", "unproductive_crosses"),
        ("unproductive", "unproductive_crosses"),
        ("link", "midfield_link_break"),
        ("supply", "midfield_link_break"),
        ("progressive", "midfield_link_break"),
        ("flank", "flank_overload_right"),
        ("right", "flank_overload_right"),
        ("cross", "unproductive_crosses"),
        ("midfield", "midfield_link_break"),
        ("chaos", "chaos_press_mid"),
        ("press", "chaos_press_mid"),
        ("shot", "shot_speed_spike"),
        ("contact", "low_defensive_contacts"),
        ("defensive", "low_defensive_contacts"),
    ]
    for key, alert_id in mapping:
        if key in lower:
            return alert_id
    active = tools.list_alerts().get("active_alert_ids") or []
    if active:
        return active[0]
    return "flank_overload_right"


def agent_chat(message: str) -> dict[str, Any]:
    text = (message or "").strip()
    lower = text.lower()
    tool_calls: list[dict[str, Any]] = []

    def call(name: str, args: dict[str, Any] | None = None) -> Any:
        result = tools.dispatch(name, args)
        tool_calls.append({"tool": name, "args": args or {}, "result": result})
        return result

    if re.search(r"\b(coach|analyst|fan)\b", lower):
        mode = "coach"
        if "fan" in lower and "coach" not in lower:
            mode = "fan"
        call("set_viewer_profile", {"mode": mode, "language": "en"})

    reply_parts: list[str] = []

    if any(w in lower for w in ("clock", "minute", "time")):
        clock = call("get_match_clock")
        reply_parts.append(
            f"Match clock: {clock.get('match_minute', 0):.1f}' "
            f"(period {clock.get('period')}, running={clock.get('running')})."
        )

    if any(w in lower for w in ("state", "rolling", "metrics")):
        state = call("get_match_state")
        rolling = state.get("rolling") or {}
        reply_parts.append(
            "Rolling state — "
            f"flank crosses={rolling.get('flank_strike_load_home_right')}, "
            f"mid turnovers={rolling.get('midfield_turnovers')}, "
            f"chaos={rolling.get('midfield_chaos_index')}, "
            f"chances={rolling.get('attacker_chances')}/"
            f"used={rolling.get('attacker_chances_used')}, "
            f"cross_prod={rolling.get('cross_productivity_rate')}, "
            f"mid_prog={rolling.get('mid_progression_rate')}."
        )

    if any(w in lower for w in ("alert", "leak", "problem")):
        alerts = call("list_alerts")
        ids = alerts.get("active_alert_ids") or []
        reply_parts.append(
            "Active alerts: " + (", ".join(ids) if ids else "none yet — keep the replay running.")
        )
        if ids or "explain" in lower or "why" in lower:
            alert_id = _detect_alert_id(text)
            explained = call("explain_alert", {"alert_id": alert_id})
            pers = explained.get("personalized") or {}
            reply_parts.append(f"[{pers.get('mode')}] {pers.get('text')}")
            if pers.get("why_it_matters"):
                reply_parts.append(f"Why it matters: {pers['why_it_matters']}")

    if any(w in lower for w in ("shortlist", "bench", "who can", "fix", "profile", "sub")):
        alert_id = _detect_alert_id(text)
        shortlist = call("propose_roles_for_alert", {"alert_id": alert_id})
        reply_parts.append(f"Gap: {shortlist.get('gap')}")
        for c in shortlist.get("candidates") or []:
            reply_parts.append(
                f"- {c['name']} ({c['position']}) fit={c['fit_score']} — {c['why']}"
            )
        if not shortlist.get("candidates"):
            reply_parts.append("No bench candidates matched this gap.")

    if any(w in lower for w in ("overlay", "graphic", "screen")):
        alert_id = _detect_alert_id(text)
        overlay = call("get_overlay_packet", {"alert_id": alert_id})
        title = (overlay.get("graphic") or {}).get("title") or alert_id
        reply_parts.append(
            f"Overlay ready for {alert_id}: {title} "
            f"(zone={(overlay.get('graphic') or {}).get('zone')})."
        )

    if any(w in lower for w in ("halftime", "half-time", "living room", "armchair")):
        ht = call("get_fan_halftime")
        cards = ht.get("cards") or {}
        cold = cards.get("cold_start") or {}
        flank = cards.get("defensive_pressure") or {}
        chance = cards.get("chance_conversion") or {}
        delivery = cards.get("cross_productivity") or {}
        crowd = cards.get("crowd_call") or {}
        reply_parts.append(
            f"Halftime summary {ht.get('scoreline')} @ {ht.get('clock')}: "
            f"{cold.get('headline')} — accuracy {cold.get('passing_accuracy')}; "
            f"{flank.get('zone_label')}; "
            f"chances {chance.get('used')}/{chance.get('chances')} "
            f"({chance.get('conversion_pct')}%); "
            f"deliveries {delivery.get('productive')}/{delivery.get('attempts')} "
            f"({delivery.get('productivity_pct')}%); "
            f"crowd call {crowd.get('crowd_pct')}% / data vs fans {crowd.get('data_vs_fans')}."
        )

    if any(w in lower for w in ("recap", "summary")) and "halftime" not in lower:
        recap = call("generate_match_recap")
        if recap.get("experience") == "fan" or "cards" in recap:
            reply_parts.append("Fan living-room summary loaded (see get_fan_halftime).")
        else:
            reply_parts.append(f"Coach recap for {recap.get('mode')}:")
            for a in recap.get("alerts") or []:
                reply_parts.append(f"• {a.get('alert_id')}: {a.get('text')}")
            for s in recap.get("substitutions") or []:
                reply_parts.append(f"• Sub: {s}")

    if not reply_parts:
        call("get_match_clock")
        reply_parts.append(
            "Two views, one engine. Coach: leaks, explain, bench fix. "
            "Fan: halftime summary. Try: “What is leaking?” or “Show halftime summary.”"
        )

    from pitchpulse.api.studio_state import STUDIO

    return {
        "reply": "\n".join(reply_parts),
        "viewer": STUDIO.viewer.to_dict(),
        "tool_calls": tool_calls,
        "tools": tools.TOOL_SPECS,
    }
