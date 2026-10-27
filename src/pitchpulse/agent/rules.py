"""Rule-based twins of each agent (English) — used without Azure and to recover from model failures."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pitchpulse.agent.team import Blackboard

VIEWER_RE = re.compile(r"\b(coach|analyst|fan)\b")

ANALYST_WORDS = (
    "clock",
    "minute",
    "time",
    "state",
    "rolling",
    "metrics",
    "alert",
    "leak",
    "problem",
    "why",
    "explain",
    "wrong",
)
SCOUT_WORDS = ("shortlist", "bench", "who can", "fix", "profile", "sub")
STORY_WORDS = (
    "overlay",
    "graphic",
    "screen",
    "halftime",
    "half-time",
    "living room",
    "armchair",
    "recap",
    "summary",
    "story",
)

HELP_TEXT = (
    "Two views, one engine. Coach: leaks, explain, bench fix. "
    "Fan: halftime summary. Try: “What is leaking?” or “Show halftime summary.”"
)


def detect_alert_id(text: str, active: list[str]) -> str:
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
    if active:
        return active[0]
    return "flank_overload_right"


def viewer_mode(lower: str) -> str | None:
    if not VIEWER_RE.search(lower):
        return None
    return "fan" if "fan" in lower and "coach" not in lower else "coach"


def _mentions(lower: str, words: tuple[str, ...]) -> bool:
    # Word-start match so "leaking" hits "leak" but "halftime" does not hit "time".
    return any(re.search(rf"\b{re.escape(w)}", lower) for w in words)


def route(lower: str) -> list[str]:
    """Which specialists to run, in order. Bench Scout always follows the Analyst's focus."""
    plan: list[str] = []
    wants_scout = _mentions(lower, SCOUT_WORDS)
    if wants_scout or _mentions(lower, ANALYST_WORDS):
        plan.append("analyst")
    if wants_scout:
        plan.append("bench_scout")
    if _mentions(lower, STORY_WORDS):
        plan.append("storyteller")
    return plan


def route_fan(lower: str) -> list[str]:
    """Fan chat: Storyteller for summaries/recaps, otherwise Crowd Pulse answers."""
    if _mentions(lower, STORY_WORDS):
        return ["storyteller"]
    return ["crowd_pulse"]


def crowd_pulse(board: Blackboard, task: str) -> str:
    status = board.call_tool("crowd_pulse", "get_player_status", {"player": task})
    if "error" not in status:
        parts = []
        for p in status["players"]:
            s = p["stats_so_far"]
            acc = (
                f"{s['pass_accuracy_pct']}% passing"
                if s.get("pass_accuracy_pct") is not None
                else "few passes"
            )
            line = (
                f"{p['name']} ({p['team']}, {p['position']}) at {status['match_minute']:.0f}': "
                f"{s['touches']} touches, {acc}, {s['losses']} balls lost, {s['goals']} goals."
            )
            if p.get("storyline"):
                line += f" Storyline: {p['storyline']}."
            for c in p["crowd"][:1]:
                line += (
                    f" Fans: “{c['question']}” {c['fan_pct']}% (data agrees: {c['data_vs_fans']})."
                )
            parts.append(line)
        return "\n".join(parts)

    pulse = board.call_tool("crowd_pulse", "get_crowd_pulse", {})
    parts = [f"Crowd pulse at {pulse.get('match_minute', 0):.0f}' ({pulse.get('scoreline')}):"]
    for side in ("home", "away"):
        team = pulse.get(side)
        if not team:
            continue
        now = team["right_now"]
        loved = ", ".join(f"#{r['shirt']} {r['name']} ({r['fan_pct']}%)" for r in now["fans_love"])
        doubt = ", ".join(
            f"#{r['shirt']} {r['name']} ({r['fan_pct']}%)" for r in now["fans_worried"]
        )
        top = team["crowd_calls"][0] if team["crowd_calls"] else None
        line = f"{team['team_name']} fans ({now['window']}): loving {loved or '—'}; worried about {doubt or '—'}."
        if top:
            line += f" Loudest call: “{top['question']}” {top['fan_pct']}%."
        parts.append(line)
    return "\n".join(parts)


def analyst(board: Blackboard, task: str) -> str:
    lower = task.lower()
    parts: list[str] = []

    if any(w in lower for w in ("clock", "minute", "time")):
        clock = board.call_tool("analyst", "get_match_clock", {})
        parts.append(
            f"Match clock: {clock.get('match_minute', 0):.1f}' "
            f"(period {clock.get('period')}, running={clock.get('running')})."
        )

    if any(w in lower for w in ("state", "rolling", "metrics")):
        state = board.call_tool("analyst", "get_match_state", {})
        rolling = state.get("rolling") or {}
        parts.append(
            "Rolling state — "
            f"flank crosses={rolling.get('flank_strike_load_home_right')}, "
            f"mid turnovers={rolling.get('midfield_turnovers')}, "
            f"chaos={rolling.get('midfield_chaos_index')}, "
            f"chances={rolling.get('attacker_chances')}/"
            f"used={rolling.get('attacker_chances_used')}, "
            f"cross_prod={rolling.get('cross_productivity_rate')}, "
            f"mid_prog={rolling.get('mid_progression_rate')}."
        )

    alerts = board.call_tool("analyst", "list_alerts", {})
    ids = alerts.get("active_alert_ids") or []
    parts.append(
        "Active alerts: " + (", ".join(ids) if ids else "none yet — keep the replay running.")
    )
    alert_id = detect_alert_id(task, ids)
    if ids or "explain" in lower or "why" in lower or any(w in lower for w in SCOUT_WORDS):
        explained = board.call_tool("analyst", "explain_alert", {"alert_id": alert_id})
        pers = explained.get("personalized") or {}
        parts.append(f"[{pers.get('mode')}] {pers.get('text')}")
        if pers.get("why_it_matters"):
            parts.append(f"Why it matters: {pers['why_it_matters']}")
    board.focus_alert_id = board.focus_alert_id or alert_id
    return "\n".join(parts)


def bench_scout(board: Blackboard, task: str) -> str:
    alert_id = board.focus_alert_id or detect_alert_id(task, [])
    shortlist = board.call_tool("bench_scout", "propose_roles_for_alert", {"alert_id": alert_id})
    parts = [f"Gap: {shortlist.get('gap')}"]
    for c in shortlist.get("candidates") or []:
        parts.append(f"- {c['name']} ({c['position']}) fit={c['fit_score']} — {c['why']}")
    if not shortlist.get("candidates"):
        parts.append("No bench candidates matched this gap.")
    return "\n".join(parts)


def storyteller(board: Blackboard, task: str) -> str:
    lower = task.lower()
    parts: list[str] = []

    if any(w in lower for w in ("overlay", "graphic", "screen")):
        alert_id = board.focus_alert_id or detect_alert_id(task, [])
        overlay = board.call_tool("storyteller", "get_overlay_packet", {"alert_id": alert_id})
        graphic = overlay.get("graphic") or {}
        parts.append(
            f"Overlay ready for {alert_id}: {graphic.get('title') or alert_id} "
            f"(zone={graphic.get('zone')})."
        )

    if any(w in lower for w in ("recap", "summary")) and "halftime" not in lower:
        recap = board.call_tool("storyteller", "generate_match_recap", {})
        if recap.get("experience") == "fan" or "cards" in recap:
            parts.append("Fan living-room summary loaded (see get_fan_halftime).")
        else:
            parts.append(f"Coach recap for {recap.get('mode')}:")
            for a in recap.get("alerts") or []:
                parts.append(f"• {a.get('alert_id')}: {a.get('text')}")
            for s in recap.get("substitutions") or []:
                parts.append(f"• Sub: {s}")

    if not parts or any(w in lower for w in ("halftime", "half-time", "living room", "armchair")):
        ht = board.call_tool("storyteller", "get_fan_halftime", {})
        cards = ht.get("cards") or {}
        cold = cards.get("cold_start") or {}
        flank = cards.get("defensive_pressure") or {}
        chance = cards.get("chance_conversion") or {}
        delivery = cards.get("cross_productivity") or {}
        crowd = cards.get("crowd_call") or {}
        parts.append(
            f"Halftime summary {ht.get('scoreline')} @ {ht.get('clock')}: "
            f"{cold.get('headline')} — accuracy {cold.get('passing_accuracy')}; "
            f"{flank.get('zone_label')}; "
            f"chances {chance.get('used')}/{chance.get('chances')} "
            f"({chance.get('conversion_pct')}%); "
            f"deliveries {delivery.get('productive')}/{delivery.get('attempts')} "
            f"({delivery.get('productivity_pct')}%); "
            f"crowd call {crowd.get('crowd_pct')}% / data vs fans {crowd.get('data_vs_fans')}."
        )
    return "\n".join(parts)
