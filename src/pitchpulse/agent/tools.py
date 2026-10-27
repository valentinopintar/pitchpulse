"""Thin tool layer — same services the studio UI uses."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from pitchpulse.api.replay_session import SESSION
from pitchpulse.api.studio_state import STUDIO
from pitchpulse.data.paths import match_dir
from pitchpulse.data.score import score_at
from pitchpulse.explain.service import EXPLAIN
from pitchpulse.explain.templates import ALERT_COPY
from pitchpulse.interpret.events_io import load_events
from pitchpulse.interpret.window import rolling_metrics
from pitchpulse.personalize.halftime import (
    _rank_underperformers,
    build_fan_live,
    build_halftime_summary,
)
from pitchpulse.personalize.viewer import ViewerProfile
from pitchpulse.render.overlay import build_overlay_packet
from pitchpulse.shortlist.service import propose_roles_for_alert
from pitchpulse.shortlist.tactics import suggest_tactical_adjustments


def get_match_clock() -> dict[str, Any]:
    st = SESSION.status()
    return {
        "match_id": st.match_id,
        "t_ms": st.t_ms,
        "match_minute": st.match_minute,
        "period": 1 if st.match_minute < 45 else 2,
        "running": st.running,
        "score": _live_score(),
    }


def _live_score() -> dict[str, Any]:
    """Scoreline at the live minute, with scorers so far (compact for models)."""
    sc = score_at(STUDIO.match_id or "syn-001", _live_minute())
    return {
        "scoreline": sc["scoreline"],
        "goals": [
            {"minute": g["minute"], "team_side": g["team_side"], "scorer": g["name"]}
            for g in sc["goals"]
        ],
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


def suggest_tactics(alert_id: str) -> dict[str, Any]:
    """On-pitch fixes (shape, roles, pressing) for an alert — no substitution needed."""
    match_id = STUDIO.match_id or "syn-001"
    minute = _live_minute()
    meta = json.loads((match_dir(match_id) / "meta.json").read_text(encoding="utf-8"))
    # Evidence from the window where the leak happened (up to now), not just the last 6 minutes.
    window = next((a for a in STUDIO._expected_alerts if a["alert_id"] == alert_id), None)
    now_ms = int(minute * 60_000)
    if window and window["t_start_ms"] <= now_ms:
        t1 = min(window["t_end_ms"], now_ms)
        rolling = rolling_metrics(
            [e for e in load_events(match_id) if window["t_start_ms"] <= e.t_ms <= t1]
        )
    else:
        rolling = SESSION.snapshot().get("rolling")
    return suggest_tactical_adjustments(
        alert_id,
        match_minute=minute,
        rolling=rolling,
        meta=meta,
        score=score_at(match_id, minute),
    )


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
    """Story cards only — the full summary (pitch, slices) is UI payload, too big for a model."""
    ht = build_halftime_summary(STUDIO.match_id or "syn-001")
    keep = ("match_id", "title", "home_team", "away_team", "experience", "cards")
    minute = _live_minute()
    out = {k: ht[k] for k in keep}
    # Never leak the final score mid-replay: report the score at the live minute.
    out["clock"] = f"{minute:.0f}'"
    out["live_score"] = _live_score()
    out["scoreline"] = out["live_score"]["scoreline"]
    if minute >= 45:
        out["halftime_score"] = ht["halftime_score"]
    return out


def _live_minute() -> float:
    st = SESSION.status()
    return float(st.match_minute) if st.loaded and st.match_minute else 90.0


def _fan_row(row: dict[str, Any]) -> dict[str, Any]:
    return {"name": row["name"], "shirt": row["shirt"], "position": row["position"],
            "fan_pct": row["fan_pct"], "reason": row["reason"]}


def get_crowd_pulse(team_side: str | None = None) -> dict[str, Any]:
    """What the stands think: crowd calls overall + the 5-minute window at the live minute."""
    ht = build_halftime_summary(STUDIO.match_id or "syn-001")
    minute = _live_minute()
    out: dict[str, Any] = {"match_minute": round(minute, 1), "scoreline": _live_score()["scoreline"]}
    for side in ("home", "away"):
        if team_side and side != team_side:
            continue
        board = ht["team_boards"][side]
        window = next(
            (s for s in board["slices"] if s["minute_start"] <= minute < s["minute_end"]),
            board["slices"][-1],
        )
        out[side] = {
            "team_name": board["team_name"],
            "crowd_calls": [
                {k: c[k] for k in ("question", "fan_pct", "data_vs_fans", "polarity", "blurb")}
                for c in board["crowd_calls"][:4]
            ],
            "right_now": {
                "window": window["label"],
                "fans_love": [_fan_row(r) for r in window["standouts"][:2]],
                "fans_worried": [_fan_row(r) for r in window["underperformers"][:2]],
            },
        }
    return out


def _find_players(query: str, lineups: dict[str, Any]) -> list[dict[str, Any]]:
    q = query.lower()
    numbers = set(re.findall(r"#\s?(\d{1,2})\b", q)) or (
        {q.strip()} if q.strip().isdigit() else set()
    )
    found = []
    for side in ("home", "away"):
        for p in lineups.get(side, {}).get("starters", []):
            shirt = str(int("".join(ch for ch in p["id"] if ch.isdigit()) or 0))
            surname = p["name"].split()[-1].lower()
            if p["id"].lower() in q or shirt in numbers or (len(surname) > 2 and surname in q):
                found.append({**p, "team_side": side})
    return found[:2]


def get_player_status(player: str) -> dict[str, Any]:
    """Fan-level status of a player (by shirt '#6', id 'A06' or surname) at the live minute."""
    match_id = STUDIO.match_id or "syn-001"
    minute = _live_minute()
    ht = build_halftime_summary(match_id)
    lineups = {
        side: {"starters": [{"id": p["player_id"], "name": p["name"], "position": p["position"]}
                            for p in ht["pitch_players"] if p["team_side"] == side]}
        for side in ("home", "away")
    }
    matches = _find_players(player or "", lineups)
    if not matches:
        return {"error": f"No player matches '{player}'. Try a shirt number like #6 or a surname."}
    live = {p["player_id"]: p for p in build_fan_live(match_id, minute)["pitch_players"]}
    players = []
    for m in matches:
        board = ht["team_boards"][m["team_side"]]
        calls = [c for c in board["crowd_calls"] if c.get("player_id") == m["id"]]
        lp = live.get(m["id"], {})
        problem = lp.get("problem") or {}
        players.append(
            {
                "name": m["name"],
                "team": board["team_name"],
                "position": m["position"],
                "stats_so_far": {
                    k: lp.get("stats", {}).get(k)
                    for k in ("touches", "pass_accuracy_pct", "losses", "duels_won",
                              "duels_lost", "shots", "goals")
                },
                "storyline": problem.get("label"),
                "crowd": [
                    {k: c[k] for k in ("question", "fan_pct", "data_vs_fans")} for c in calls
                ],
            }
        )
    return {"match_minute": round(minute, 1), "players": players}


def _data_check(s: dict[str, Any], team: dict[str, float]) -> tuple[list[str], list[str], bool]:
    """Numbers against and for a player vs outfield teammates so far, and whether one is glaring."""
    against: list[str] = []
    for_: list[str] = []
    glaring = False
    acc = s.get("pass_accuracy_pct")
    if acc is not None and team["pass_acc"]:
        if acc <= team["pass_acc"] - 8:
            against.append(f"passing {acc}% vs team {team['pass_acc']:.0f}%")
            glaring |= acc <= team["pass_acc"] - 15
        elif acc >= team["pass_acc"] + 5:
            for_.append(f"passing {acc}% vs team {team['pass_acc']:.0f}%")
    if s["touches"]:
        rate = 10 * s["losses"] / s["touches"]
        if rate >= 1.3 * team["loss_rate"] and s["losses"] >= 3:
            against.append(
                f"{s['losses']} balls lost ({rate:.1f} per 10 touches vs team {team['loss_rate']:.1f})"
            )
            glaring |= rate >= 2.5 * team["loss_rate"] and s["losses"] >= 5
    if s["duels_lost"] >= 3 and s["duels_lost"] > s["duels_won"]:
        against.append(f"duels {s['duels_won']} won / {s['duels_lost']} lost")
        glaring |= s["duels_lost"] >= 5 and s["duels_lost"] >= 3 * s["duels_won"]
    elif s["duels_won"] >= 3 and s["duels_won"] > s["duels_lost"]:
        for_.append(f"duels {s['duels_won']} won / {s['duels_lost']} lost")
    if s["goals"]:
        for_.append(f"{s['goals']} goal(s) from {s['shots']} shots")
    elif s["shots"] >= 3:
        against.append(f"{s['shots']} shots, {s['shots_on']} on target, no goal")
    return against, for_, glaring


def get_fan_verdicts(team_side: str | None = None) -> dict[str, Any]:
    """Who the stands are unhappy with right now, why, and whether the numbers back the fans."""
    match_id = STUDIO.match_id or "syn-001"
    minute = _live_minute()
    ht = build_halftime_summary(match_id)
    live = build_fan_live(match_id, minute)["pitch_players"]
    out: dict[str, Any] = {
        "match_minute": round(minute, 1),
        "scoreline": _live_score()["scoreline"],
        "method": "Each criticised player is compared with their outfield teammates so far: passing "
        "accuracy, balls lost per 10 touches, duels, finishing.",
    }
    for side in ("home", "away"):
        if team_side and side != team_side:
            continue
        players = [p for p in live if p["team_side"] == side and p["position"] != "GK"]
        active = [p for p in players if p["stats"]["touches"] >= 3]
        accs = [p["stats"]["pass_accuracy_pct"] for p in active if p["stats"]["pass_accuracy_pct"] is not None]
        touches = sum(p["stats"]["touches"] for p in active) or 1
        team = {
            "pass_acc": sum(accs) / len(accs) if accs else 0.0,
            "loss_rate": 10 * sum(p["stats"]["losses"] for p in active) / touches,
        }
        # The stands judge the whole match so far, louder on the last five minutes.
        raw = {
            p["player_id"]: {
                **p["stats"],
                "pass_accuracy": (p["stats"]["pass_accuracy_pct"] or 0) / 100
                if p["stats"]["pass_accuracy_pct"] is not None
                else None,
            }
            for p in players
        }
        starters = [{"id": p["player_id"], "name": p["name"], "position": p["position"]} for p in players]
        board = ht["team_boards"][side]
        window = next(
            (s for s in board["slices"] if s["minute_start"] <= minute < s["minute_end"]),
            board["slices"][-1],
        )
        targets: dict[str, dict[str, Any]] = {}
        for row in _rank_underperformers(raw, starters, limit=3):
            targets[row["player_id"]] = {"fan_pct": row["fan_pct"], "fans_say": row["reason"],
                                         "heard": "match so far"}
        for row in window["underperformers"][:2]:
            t = targets.setdefault(row["player_id"], {"fan_pct": row["fan_pct"],
                                                      "fans_say": row["reason"], "heard": ""})
            t["heard"] = ", ".join(filter(None, [t["heard"], f"last 5 min ({window['label']})"]))
        by_id = {p["player_id"]: p for p in players}
        verdicts = []
        checks = {pid: _data_check(p["stats"], team) for pid, p in by_id.items()}
        for pid, t in sorted(targets.items(), key=lambda kv: -kv[1]["fan_pct"]):
            p = by_id[pid]
            against, for_, glaring = checks[pid]
            if p["stats"]["touches"] < 8:
                verdict = "too early to judge"
            elif (len(against) >= 2 or glaring) and not for_:
                verdict = "backed by data"
            elif against:
                verdict = "partly backed"
            else:
                verdict = "harsh: the numbers don't support it"
            verdicts.append({
                "player": f"#{p['shirt']} {p['name']}", "position": p["position"],
                "fans_unhappy_pct": t["fan_pct"], "fans_say": t["fans_say"], "heard": t["heard"],
                "data_against": against, "data_for": for_, "verdict": verdict,
            })
        missed = max(
            (pid for pid in by_id if pid not in targets and by_id[pid]["stats"]["touches"] >= 8),
            key=lambda pid: len(checks[pid][0]) - len(checks[pid][1]),
            default=None,
        )
        team_out: dict[str, Any] = {
            "team_name": board["team_name"],
            "team_average": {"pass_accuracy_pct": round(team["pass_acc"]),
                             "balls_lost_per_10_touches": round(team["loss_rate"], 1)},
            "criticised": verdicts,
        }
        if missed and len(checks[missed][0]) >= 2:
            team_out["fans_may_be_missing"] = {
                "player": f"#{by_id[missed]['shirt']} {by_id[missed]['name']}",
                "data_against": checks[missed][0],
            }
        out[side] = team_out
    return out


TOOL_SPECS: list[dict[str, Any]] = [
    {"name": "get_match_clock", "description": "Current match clock and period"},
    {"name": "get_match_state", "description": "Rolling tactical state snapshot (coach)"},
    {"name": "list_alerts", "description": "Active coaching alert ids"},
    {"name": "explain_alert", "description": "Explain an alert for current viewer"},
    {"name": "set_viewer_profile", "description": "Set coach|fan (analyst maps to coach)"},
    {"name": "get_overlay_packet", "description": "On-screen graphic JSON for an alert"},
    {"name": "propose_roles_for_alert", "description": "Bench profiles that can stop the gap (coach)"},
    {
        "name": "suggest_tactical_adjustments",
        "description": "Fixes without a substitution: formation, role, pressing and build-up "
        "changes for an alert, with trade-offs, timing advice and evidence (coach)",
    },
    {"name": "generate_match_recap", "description": "Coach recap or fan halftime summary"},
    {"name": "get_fan_halftime", "description": "Living-room Match Day Summary (halftime)"},
    {"name": "get_crowd_pulse", "description": "What fans in the stands think, overall and right now (fan)"},
    {"name": "get_player_status", "description": "How one player is doing so far, fan-level (fan)"},
    {
        "name": "get_fan_verdicts",
        "description": "Who the fans are unhappy with right now, why, and whether the numbers "
        "back them (fan)",
    },
]


ALERT_IDS: list[str] = list(ALERT_COPY)

_ALERT_ARG = {"alert_id": {"type": "string", "enum": ALERT_IDS}}

# JSON-schema parameters for Azure OpenAI function calling (tools without args take none).
TOOL_PARAMS: dict[str, dict[str, Any]] = {
    "explain_alert": {"properties": _ALERT_ARG, "required": ["alert_id"]},
    "set_viewer_profile": {
        "properties": {
            "mode": {"type": "string", "enum": ["coach", "fan"]},
            "favorite_player_id": {"type": "string"},
        },
        "required": ["mode"],
    },
    "get_overlay_packet": {"properties": _ALERT_ARG, "required": ["alert_id"]},
    "propose_roles_for_alert": {
        "properties": {**_ALERT_ARG, "team_side": {"type": "string", "enum": ["home", "away"]}},
        "required": ["alert_id"],
    },
    "suggest_tactical_adjustments": {"properties": _ALERT_ARG, "required": ["alert_id"]},
    "get_crowd_pulse": {
        "properties": {"team_side": {"type": "string", "enum": ["home", "away"]}},
        "required": [],
    },
    "get_fan_verdicts": {
        "properties": {"team_side": {"type": "string", "enum": ["home", "away"]}},
        "required": [],
    },
    "get_player_status": {
        "properties": {
            "player": {"type": "string", "description": "Shirt like '#6', id like 'A06', or surname"}
        },
        "required": ["player"],
    },
}


def openai_tools(names: list[str]) -> list[dict[str, Any]]:
    """Function-calling definitions for the named tools."""
    specs = {t["name"]: t for t in TOOL_SPECS}
    out = []
    for name in names:
        params = TOOL_PARAMS.get(name, {"properties": {}, "required": []})
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": specs[name]["description"],
                    "parameters": {"type": "object", **params},
                },
            }
        )
    return out


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
        "suggest_tactical_adjustments": lambda: suggest_tactics(
            args.get("alert_id", "flank_overload_right")
        ),
        "get_fan_verdicts": lambda: get_fan_verdicts(args.get("team_side")),
        "generate_match_recap": generate_match_recap,
        "get_fan_halftime": get_fan_halftime,
        "get_crowd_pulse": lambda: get_crowd_pulse(args.get("team_side")),
        "get_player_status": lambda: get_player_status(str(args.get("player") or "")),
    }
    if name not in table:
        return {"error": f"Unknown tool: {name}", "available": [t["name"] for t in TOOL_SPECS]}
    return table[name]()
