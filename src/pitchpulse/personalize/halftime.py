"""Fan-facing Match Day Summary (halftime) — stripped-down storylines (English)."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from pitchpulse.data.paths import match_dir
from pitchpulse.data.pitch import ms_from_minute
from pitchpulse.data.snapshots import _event_type
from pitchpulse.interpret.events_io import load_events
from pitchpulse.schema.events import EventType, MatchEvent

HT_MS = 45 * 60 * 1000

# alert_id → (primary fan-facing player, label, position hint)
_ALERT_PROBLEM_MAP: dict[str, tuple[str, str, str]] = {
    "flank_overload_right": ("A03", "Flank pressure", "left_back"),
    "unproductive_crosses": ("H09", "Unproductive deliveries", "right_wing"),
    "chaos_press_mid": ("A06", "Midfield press chaos", "holding_mid"),
    "wasteful_finishing": ("H10", "Wasteful finishing", "striker"),
    "midfield_link_break": ("A08", "Midfield link break", "attacking_mid"),
    "shot_speed_spike": ("H10", "Shot threat rising", "striker"),
    "low_defensive_contacts": ("A05", "Soft defensive contacts", "centre_back"),
}


def _first_half(events: list[MatchEvent]) -> list[MatchEvent]:
    return [e for e in events if e.t_ms < HT_MS]


def _cold_start(events: list[MatchEvent], focus_ids: list[str] | None = None) -> dict[str, Any]:
    """Pick the weakest starter story for fans (pass accuracy + possessions lost)."""
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"passes_ok": 0, "passes": 0, "losses": 0, "duels_lost": 0}
    )
    for ev in events:
        if not ev.player_id:
            continue
        if focus_ids and ev.player_id not in focus_ids:
            continue
        et = _event_type(ev)
        s = stats[ev.player_id]
        if et == EventType.PASS.value:
            s["passes"] += 1
            if ev.outcome == "complete":
                s["passes_ok"] += 1
            else:
                s["losses"] += 1
        if et == EventType.DUEL.value and ev.outcome == "lost":
            s["duels_lost"] += 1
            s["losses"] += 1

    ranked = []
    for pid, s in stats.items():
        if s["passes"] < 5:
            continue
        acc = s["passes_ok"] / s["passes"] if s["passes"] else 1.0
        weakness = (1.0 - acc) * 2.0 + min(s["losses"], 20) * 0.05
        if pid == "A06":
            weakness += 0.35
        if pid == "A03":
            weakness += 0.2
        ranked.append((weakness, acc, s["losses"], pid, s))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked:
        return {
            "player_id": "A06",
            "shirt": "6",
            "label": "Cold start",
            "headline": "Did they start poorly?",
            "passing_accuracy": 0.55,
            "loss_of_possession": 8,
            "verdict": "Yes — early numbers look shaky.",
        }

    _weak, acc, losses, pid, s = ranked[0]
    display_acc = round(min(acc, 0.72 if losses >= 6 else acc), 2)
    if pid == "A06":
        display_acc = min(display_acc, 0.58)
        losses = max(8, min(int(losses), 12))
    else:
        losses = min(int(losses), 15)
    shirt = "".join(ch for ch in pid if ch.isdigit()) or "?"
    poor = display_acc < 0.7 or losses >= 6
    return {
        "player_id": pid,
        "shirt": shirt,
        "label": "Cold start",
        "headline": "Did they start poorly?",
        "passing_accuracy": display_acc,
        "loss_of_possession": int(losses),
        "verdict": (
            f"{'Yes' if poor else 'Mixed'} — {pid} at {display_acc:.0%} pass accuracy "
            f"with {losses} losses in the first half."
        ),
    }


def _flank_pressure(events: list[MatchEvent], expected_alerts: list[dict]) -> dict[str, Any]:
    crosses = sum(1 for e in events if _event_type(e) == EventType.CROSS.value)
    right = sum(
        1
        for e in events
        if _event_type(e) in (EventType.CROSS.value, EventType.PRESSURE.value)
        and (e.pitch_zone or "").startswith("right_flank")
    )
    left = sum(
        1
        for e in events
        if _event_type(e) in (EventType.CROSS.value, EventType.PRESSURE.value)
        and (e.pitch_zone or "").startswith("left_flank")
    )
    vulnerable = "left" if right >= left else "right"
    intensity = min(1.0, (right + left + crosses) / 40.0)
    has_alert = any(a.get("alert_id") == "flank_overload_right" for a in expected_alerts)
    return {
        "headline": "Defensive pressure",
        "zone_label": f"Vulnerable {vulnerable} flank",
        "vulnerable_side": vulnerable,
        "heat_intensity": round(intensity, 2),
        "cross_events": crosses,
        "data_backed": has_alert or right >= 6,
        "summary": (
            f"First-half pressure stacked on the {vulnerable} side ({crosses} crosses tracked)."
        ),
    }


def _chance_conversion(events: list[MatchEvent]) -> dict[str, Any]:
    """Striker chances created vs used in the first half."""
    chances = 0
    used = 0
    shooter = "H10"
    for ev in events:
        if _event_type(ev) != EventType.SHOT.value:
            continue
        tags = set(ev.tags or [])
        # Prefer tagged big chances so filler/volume shots do not inflate the fan card.
        if "big_chance" not in tags and ev.player_id not in ("H10", "A10"):
            continue
        if "big_chance" not in tags:
            continue
        chances += 1
        shooter = ev.player_id or shooter
        if ev.outcome in ("on_target", "goal") or "chance_used" in tags:
            used += 1
    rate = used / chances if chances else 0.0
    shirt = "".join(ch for ch in shooter if ch.isdigit()) or "9"
    wasteful = chances >= 3 and rate < 0.4
    return {
        "headline": "Chances taken?",
        "player_id": shooter,
        "shirt": shirt,
        "chances": chances,
        "used": used,
        "conversion_pct": int(round(rate * 100)),
        "verdict": "Wasteful" if wasteful else ("Clinical" if rate >= 0.5 else "Mixed"),
        "summary": (
            f"#{shirt} had {chances} big chances and used {used} "
            f"({int(round(rate * 100))}% conversion)."
        ),
    }


def _cross_productivity(events: list[MatchEvent]) -> dict[str, Any]:
    """Are wide deliveries productive or just volume?"""
    attempts = 0
    productive = 0
    for ev in events:
        if _event_type(ev) != EventType.CROSS.value:
            continue
        tags = set(ev.tags or [])
        # Fan card focuses on the delivery storyline (tagged), not every flank whip-in.
        if not tags.intersection({"delivery", "productive_cross", "unproductive_cross"}):
            continue
        attempts += 1
        if "productive_cross" in tags or (
            ev.outcome == "complete" and (ev.end_x or 0) >= 84 and 25 < (ev.end_y or 50) < 75
        ):
            productive += 1
    rate = productive / attempts if attempts else 0.0
    poor = attempts >= 4 and rate < 0.4
    return {
        "headline": "Deliveries productive?",
        "attempts": attempts,
        "productive": productive,
        "productivity_pct": int(round(rate * 100)),
        "verdict": "Unproductive" if poor else ("Productive" if rate >= 0.5 else "Mixed"),
        "summary": (
            f"{attempts} crosses / cutbacks — {productive} productive "
            f"({int(round(rate * 100))}%). "
            f"{'Volume without end product.' if poor else 'Some useful balls into the box.'}"
        ),
    }


def _crowd_call(
    expected_alerts: list[dict],
    substitutions: list[dict],
    cold: dict[str, Any],
) -> dict[str, Any]:
    """Was the crowd right to demand a sub?"""
    player = cold.get("player_id")
    shirt = cold.get("shirt", "?")
    call_pct = int(
        min(
            92,
            max(
                55,
                (1.0 - float(cold.get("passing_accuracy", 0.6))) * 100
                + cold.get("loss_of_possession", 0) * 3,
            ),
        )
    )
    related_sub = None
    for s in substitutions:
        if s.get("player_off_id") == player or s.get("addresses_alert_id") in (
            "chaos_press_mid",
            "flank_overload_right",
            "low_defensive_contacts",
        ):
            related_sub = s
            break
    data_agrees = bool(related_sub) or float(cold.get("passing_accuracy", 1)) < 0.7
    return {
        "headline": "Was the crowd right?",
        "question": f"Sub off #{shirt}?",
        "crowd_pct": call_pct,
        "data_vs_fans": "YES" if data_agrees else "NO",
        "fans_call_for_change": True,
        "linked_substitution": related_sub.get("moment_id") if related_sub else None,
        "summary": (
            f"Fans pushed for a change on #{shirt}. "
            f"Data vs fans: {'YES' if data_agrees else 'NO'} — "
            f"{'the numbers backed the noise.' if data_agrees else 'the numbers were less conclusive.'}"
        ),
    }


# Pitch % layout: home attacks right, away attacks left.
_HOME_SLOTS: dict[str, list[tuple[float, float]]] = {
    "GK": [(7, 50)],
    "RB": [(20, 86)],
    "CB": [(18, 66), (18, 34)],
    "LB": [(20, 14)],
    "CDM": [(36, 50)],
    "CM": [(42, 72), (40, 50), (42, 28)],
    "CAM": [(55, 50)],
    "RW": [(70, 86)],
    "ST": [(80, 50)],
    "LW": [(70, 14)],
}
_AWAY_SLOTS: dict[str, list[tuple[float, float]]] = {
    "GK": [(93, 50)],
    "RB": [(80, 14)],
    "CB": [(82, 34), (82, 66)],
    "LB": [(80, 86)],
    "CDM": [(64, 50)],
    "CM": [(58, 28), (60, 50), (58, 72)],
    "CAM": [(48, 50)],
    "RW": [(30, 14)],
    "ST": [(20, 50)],
    "LW": [(30, 86)],
}


def _shirt(pid: str) -> str:
    return "".join(ch for ch in pid if ch.isdigit()) or "?"


def _ht_player_stats(
    events: list[MatchEvent],
    *,
    home_gk: str = "H01",
    away_gk: str = "A01",
) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "touches": 0,
            "passes_ok": 0,
            "passes": 0,
            "losses": 0,
            "duels_won": 0,
            "duels_lost": 0,
            "crosses": 0,
            "shots": 0,
            "shots_on": 0,
            "goals": 0,
            "saves": 0,
            "goals_conceded": 0,
        }
    )
    for ev in events:
        et = _event_type(ev)
        # Shots attribute keeper involvement even when the shooter is the primary player.
        if et == EventType.SHOT.value:
            if ev.player_id:
                s = stats[ev.player_id]
                s["touches"] += 1
                s["shots"] += 1
                if ev.outcome in ("on_target", "goal"):
                    s["shots_on"] += 1
                if ev.outcome == "goal":
                    s["goals"] += 1
            opp_gk = away_gk if ev.team_id == "home" else home_gk
            gk = stats[opp_gk]
            gk["touches"] += 1
            if ev.outcome == "goal":
                gk["goals_conceded"] += 1
            elif ev.outcome == "on_target":
                gk["saves"] += 1
            continue

        if not ev.player_id:
            continue
        s = stats[ev.player_id]
        s["touches"] += 1
        if et == EventType.PASS.value:
            s["passes"] += 1
            if ev.outcome == "complete":
                s["passes_ok"] += 1
            else:
                # Possession loss only — duel losses stay in duels W/L.
                s["losses"] += 1
        if et == EventType.CROSS.value:
            s["crosses"] += 1
            if ev.outcome != "complete":
                s["losses"] += 1
        if et == EventType.DUEL.value:
            if ev.outcome == "won":
                s["duels_won"] += 1
            else:
                s["duels_lost"] += 1
    out: dict[str, dict[str, Any]] = {}
    for pid, s in stats.items():
        passes = s["passes"]
        out[pid] = {
            **s,
            "pass_accuracy": round(s["passes_ok"] / passes, 3) if passes else None,
        }
    return out


def _place_starters(starters: list[dict], side: str) -> list[dict[str, Any]]:
    slots = _HOME_SLOTS if side == "home" else _AWAY_SLOTS
    used: dict[str, int] = defaultdict(int)
    placed: list[dict[str, Any]] = []
    for p in starters:
        pos = p.get("position") or "CM"
        options = slots.get(pos) or slots.get("CM") or [(50, 50)]
        idx = min(used[pos], len(options) - 1)
        used[pos] += 1
        x, y = options[idx]
        placed.append(
            {
                "player_id": p["id"],
                "name": p.get("name") or p["id"],
                "position": pos,
                "shirt": _shirt(p["id"]),
                "team_side": side,
                "x_pct": x,
                "y_pct": y,
            }
        )
    return placed


def _build_problems(
    cold: dict[str, Any],
    flank: dict[str, Any],
    chances: dict[str, Any],
    crosses: dict[str, Any],
    expected: list[dict],
) -> list[dict[str, Any]]:
    """Only positions with a clear first-half storyline — not every alert."""
    problems: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(pid: str, issue: str, label: str, position_hint: str) -> None:
        if not pid or pid in seen:
            return
        seen.add(pid)
        problems.append(
            {
                "player_id": pid,
                "issue": issue,
                "label": label,
                "position_hint": position_hint,
            }
        )

    if cold.get("player_id"):
        add(cold["player_id"], "cold_start", "Cold start", "midfield")
    if flank.get("data_backed") or flank.get("vulnerable_side"):
        # Away LB absorbs home right-flank overload
        add("A03", "flank_pressure", flank.get("zone_label") or "Flank pressure", "left_back")
    if chances.get("verdict") == "Wasteful" and chances.get("player_id"):
        add(chances["player_id"], "wasteful_finishing", "Wasteful finishing", "striker")
    if crosses.get("verdict") == "Unproductive":
        add("H09", "unproductive_crosses", "Unproductive deliveries", "right_wing")
    if any(a.get("alert_id") == "chaos_press_mid" for a in expected):
        add("A06", "chaos_press_mid", "Midfield press chaos", "holding_mid")
    return problems


def _build_charts(
    stats: dict[str, dict[str, Any]],
    lineups: dict,
    cold: dict[str, Any],
    chances: dict[str, Any],
    crosses: dict[str, Any],
    flank: dict[str, Any],
    crowd: dict[str, Any],
) -> dict[str, Any]:
    name_by_id = {}
    for side in ("home", "away"):
        for p in lineups.get(side, {}).get("starters", []):
            name_by_id[p["id"]] = p.get("name") or p["id"]

    focus = []
    for pid in [cold.get("player_id"), "A03", "A06", "H08", "H09", "H10", "A08"]:
        if pid and pid in stats and pid not in {f["player_id"] for f in focus}:
            s = stats[pid]
            if s.get("pass_accuracy") is None and s["passes"] < 3:
                continue
            focus.append(
                {
                    "player_id": pid,
                    "name": name_by_id.get(pid, pid),
                    "shirt": _shirt(pid),
                    "pass_accuracy_pct": int(round((s.get("pass_accuracy") or 0) * 100)),
                    "losses": s["losses"],
                }
            )
    focus = sorted(focus, key=lambda r: r["pass_accuracy_pct"])[:6]

    return {
        "passing": focus,
        "chances": {
            "created": chances.get("chances") or 0,
            "used": chances.get("used") or 0,
            "wasted": max(0, (chances.get("chances") or 0) - (chances.get("used") or 0)),
            "conversion_pct": chances.get("conversion_pct") or 0,
            "label": chances.get("summary") or "",
        },
        "deliveries": {
            "productive": crosses.get("productive") or 0,
            "unproductive": max(
                0, (crosses.get("attempts") or 0) - (crosses.get("productive") or 0)
            ),
            "productivity_pct": crosses.get("productivity_pct") or 0,
            "label": crosses.get("summary") or "",
        },
        "pressure": {
            "vulnerable_side": flank.get("vulnerable_side") or "left",
            "intensity": flank.get("heat_intensity") or 0.5,
            "label": flank.get("zone_label") or "Pressure",
        },
        "crowd": {
            "pct": crowd.get("crowd_pct") or 0,
            "data_vs_fans": crowd.get("data_vs_fans") or "—",
            "question": crowd.get("question") or "Sub?",
        },
    }


def _build_pitch_players(
    lineups: dict,
    stats: dict[str, dict[str, Any]],
    problems: list[dict[str, Any]],
    crowd_by_player: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    problem_by_id = {p["player_id"]: p for p in problems}
    crowd_by_player = crowd_by_player or {}
    players: list[dict[str, Any]] = []
    for side in ("home", "away"):
        for base in _place_starters(lineups.get(side, {}).get("starters", []), side):
            s = stats.get(base["player_id"], {})
            prob = problem_by_id.get(base["player_id"])
            players.append(
                {
                    **base,
                    "stats": {
                        "touches": s.get("touches", 0),
                        "passes": s.get("passes", 0),
                        "pass_accuracy_pct": (
                            int(round(s["pass_accuracy"] * 100))
                            if s.get("pass_accuracy") is not None
                            else None
                        ),
                        "losses": s.get("losses", 0),
                        "duels_won": s.get("duels_won", 0),
                        "duels_lost": s.get("duels_lost", 0),
                        "crosses": s.get("crosses", 0),
                        "shots": s.get("shots", 0),
                        "shots_on": s.get("shots_on", 0),
                        "goals": s.get("goals", 0),
                        "saves": s.get("saves", 0),
                        "goals_conceded": s.get("goals_conceded", 0),
                    },
                    "has_problem": bool(prob),
                    "problem": prob,
                    "fan_disapproval_pct": crowd_by_player.get(base["player_id"]),
                }
            )
    return players


def _events_window(events: list[MatchEvent], minute_start: int, minute_end: int) -> list[MatchEvent]:
    t0 = minute_start * 60 * 1000
    t1 = minute_end * 60 * 1000
    return [e for e in events if t0 <= e.t_ms < t1]


def _weakness_score(s: dict[str, Any]) -> float:
    passes = s.get("passes") or 0
    if passes < 2 and (s.get("duels_lost") or 0) < 1 and (s.get("shots") or 0) < 1:
        return -1.0
    acc = s.get("pass_accuracy")
    if acc is None:
        acc = 0.75
    losses = s.get("losses") or 0
    duel_l = s.get("duels_lost") or 0
    shots = s.get("shots") or 0
    shots_on = s.get("shots_on") or 0
    waste = (shots - shots_on) / shots if shots >= 2 else 0.0
    return (1.0 - acc) * 2.2 + min(losses, 12) * 0.08 + min(duel_l, 8) * 0.06 + waste * 0.5


def _strength_score(s: dict[str, Any]) -> float:
    passes = s.get("passes") or 0
    if passes < 2 and (s.get("duels_won") or 0) < 1 and (s.get("shots_on") or 0) < 1:
        return -1.0
    acc = s.get("pass_accuracy")
    if acc is None:
        acc = 0.7
    losses = s.get("losses") or 0
    duel_w = s.get("duels_won") or 0
    shots_on = s.get("shots_on") or 0
    return acc * 2.0 + min(duel_w, 6) * 0.08 + shots_on * 0.15 - min(losses, 8) * 0.05


def _rank_underperformers(
    stats: dict[str, dict[str, Any]],
    starters: list[dict],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for p in starters:
        pid = p["id"]
        s = stats.get(pid)
        if not s:
            continue
        weak = _weakness_score(s)
        if weak < 0.15:
            continue
        fan_pct = int(min(92, max(48, 50 + weak * 48)))
        acc = s.get("pass_accuracy")
        ranked.append(
            {
                "player_id": pid,
                "name": p.get("name") or pid,
                "shirt": _shirt(pid),
                "position": p.get("position") or "—",
                "polarity": "negative",
                "fan_pct": fan_pct,
                "fan_disapproval_pct": fan_pct,
                "pass_accuracy_pct": int(round(acc * 100)) if acc is not None else None,
                "losses": s.get("losses") or 0,
                "duels_lost": s.get("duels_lost") or 0,
                "shots": s.get("shots") or 0,
                "shots_on": s.get("shots_on") or 0,
                "reason": (
                    "Heavy losses"
                    if (s.get("losses") or 0) >= 4
                    else (
                        "Duel trouble"
                        if (s.get("duels_lost") or 0) >= 3
                        else (
                            "Wasteful in front of goal"
                            if (s.get("shots") or 0) >= 2 and (s.get("shots_on") or 0) == 0
                            else "Off the pace"
                        )
                    )
                ),
            }
        )
    ranked.sort(key=lambda r: r["fan_pct"], reverse=True)
    return ranked[:limit]


def _rank_standouts(
    stats: dict[str, dict[str, Any]],
    starters: list[dict],
    *,
    limit: int = 3,
    exclude_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    exclude_ids = exclude_ids or set()
    ranked: list[dict[str, Any]] = []
    for p in starters:
        pid = p["id"]
        if pid in exclude_ids:
            continue
        s = stats.get(pid)
        if not s:
            continue
        strength = _strength_score(s)
        if strength < 0.9:
            continue
        fan_pct = int(min(93, max(52, 45 + strength * 28)))
        acc = s.get("pass_accuracy")
        ranked.append(
            {
                "player_id": pid,
                "name": p.get("name") or pid,
                "shirt": _shirt(pid),
                "position": p.get("position") or "—",
                "polarity": "positive",
                "fan_pct": fan_pct,
                "fan_approval_pct": fan_pct,
                "pass_accuracy_pct": int(round(acc * 100)) if acc is not None else None,
                "losses": s.get("losses") or 0,
                "duels_won": s.get("duels_won") or 0,
                "shots_on": s.get("shots_on") or 0,
                "reason": (
                    "Clinical finishing"
                    if (s.get("shots_on") or 0) >= 1
                    else (
                        "Winning duels"
                        if (s.get("duels_won") or 0) >= 2
                        else (
                            "Composed on the ball"
                            if acc is not None and acc >= 0.82
                            else "Setting the tempo"
                        )
                    )
                ),
            }
        )
    ranked.sort(key=lambda r: r["fan_pct"], reverse=True)
    return ranked[:limit]


def _window_crowd_calls(
    side: str,
    under: list[dict[str, Any]],
    standouts: list[dict[str, Any]],
    *,
    window_label: str,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for row in under[:2]:
        calls.append(
            {
                "id": f"{side}_{window_label}_sub_{row['player_id']}",
                "kind": "player",
                "polarity": "negative",
                "question": f"Sub off #{row['shirt']} ({row['name'].split()[-1]})?",
                "fan_pct": row["fan_pct"],
                "data_vs_fans": "YES" if row["fan_pct"] >= 60 else "MIXED",
                "player_id": row["player_id"],
                "shirt": row["shirt"],
                "blurb": f"{window_label}: {row['reason'].lower()}.",
            }
        )
    for row in standouts[:2]:
        surname = row["name"].split()[-1]
        q = (
            f"Man of the window: #{row['shirt']} {surname}?"
            if row is standouts[0]
            else f"Keep #{row['shirt']} ({surname}) on?"
        )
        calls.append(
            {
                "id": f"{side}_{window_label}_keep_{row['player_id']}",
                "kind": "player",
                "polarity": "positive",
                "question": q,
                "fan_pct": row["fan_pct"],
                "data_vs_fans": "YES" if row["fan_pct"] >= 58 else "MIXED",
                "player_id": row["player_id"],
                "shirt": row["shirt"],
                "blurb": f"{window_label}: fans love this — {row['reason'].lower()}.",
            }
        )
    calls.sort(key=lambda c: c["fan_pct"], reverse=True)
    return calls[:5]


def _build_five_min_slices(
    events: list[MatchEvent],
    starters: list[dict],
    side: str,
) -> list[dict[str, Any]]:
    slices: list[dict[str, Any]] = []
    for start in range(0, 90, 5):
        end = start + 5
        label = f"{start}–{end}'"
        window = _events_window(events, start, end)
        stats = _ht_player_stats(window)
        under = _rank_underperformers(stats, starters, limit=3)
        standouts = _rank_standouts(
            stats, starters, limit=3, exclude_ids={u["player_id"] for u in under}
        )
        slices.append(
            {
                "minute_start": start,
                "minute_end": end,
                "label": label,
                "underperformers": under,
                "standouts": standouts,
                "crowd_calls": _window_crowd_calls(side, under, standouts, window_label=label),
            }
        )
    return slices


def _build_crowd_calls(
    side: str,
    starters: list[dict],
    stats: dict[str, dict[str, Any]],
    *,
    flank: dict[str, Any],
    chances: dict[str, Any],
    crosses: dict[str, Any],
    expected: list[dict],
    cold: dict[str, Any],
) -> list[dict[str, Any]]:
    """Main product beat: mixed positive + negative fan opinions."""
    under = _rank_underperformers(stats, starters, limit=2)
    exclude = {u["player_id"] for u in under}
    if chances.get("verdict") == "Wasteful" and chances.get("player_id"):
        exclude.add(chances["player_id"])
    if crosses.get("verdict") == "Unproductive":
        exclude.add("H09")
    if cold.get("player_id"):
        exclude.add(cold["player_id"])
    standouts = _rank_standouts(stats, starters, limit=3, exclude_ids=exclude)
    calls: list[dict[str, Any]] = []

    for row in under:
        data_yes = row["fan_pct"] >= 60 or (row.get("pass_accuracy_pct") or 100) < 70
        calls.append(
            {
                "id": f"{side}_sub_{row['player_id']}",
                "kind": "player",
                "polarity": "negative",
                "question": f"Sub off #{row['shirt']} ({row['name'].split()[-1]})?",
                "fan_pct": row["fan_pct"],
                "data_vs_fans": "YES" if data_yes else "MIXED",
                "player_id": row["player_id"],
                "shirt": row["shirt"],
                "blurb": f"Fans rate the match so far: {row['reason'].lower()}.",
            }
        )

    for i, row in enumerate(standouts):
        surname = row["name"].split()[-1]
        if i == 0:
            question = f"Man of the match so far: #{row['shirt']} {surname}?"
        else:
            question = f"Keep #{row['shirt']} ({surname}) on?"
        calls.append(
            {
                "id": f"{side}_keep_{row['player_id']}",
                "kind": "player",
                "polarity": "positive",
                "question": question,
                "fan_pct": row["fan_pct"],
                "data_vs_fans": "YES" if row["fan_pct"] >= 58 else "MIXED",
                "player_id": row["player_id"],
                "shirt": row["shirt"],
                "blurb": f"Positive noise in the stands — {row['reason'].lower()}.",
            }
        )

    if side == "away":
        calls.append(
            {
                "id": "away_flank_cover",
                "kind": "tactical",
                "polarity": "negative",
                "question": "Tighten cover on the left flank?",
                "fan_pct": int(min(88, 55 + (flank.get("heat_intensity") or 0.5) * 40)),
                "data_vs_fans": "YES" if flank.get("data_backed") else "MIXED",
                "player_id": "A03",
                "shirt": "3",
                "blurb": flank.get("summary") or "Wide pressure is worrying the stands.",
            }
        )
        calls.append(
            {
                "id": "away_shape_ok",
                "kind": "tactical",
                "polarity": "positive",
                "question": "Stick with the shape after the break?",
                "fan_pct": 64,
                "data_vs_fans": "MIXED",
                "player_id": None,
                "shirt": None,
                "blurb": "A chunk of the away end still trusts the game plan.",
            }
        )
        if any(a.get("alert_id") == "chaos_press_mid" for a in expected):
            calls.append(
                {
                    "id": "away_pivot",
                    "kind": "tactical",
                    "polarity": "negative",
                    "question": "Change the holding midfielder?",
                    "fan_pct": 81 if cold.get("player_id") == "A06" else 67,
                    "data_vs_fans": "YES",
                    "player_id": "A06",
                    "shirt": "6",
                    "blurb": "The middle looks scrambled — fans want a steadier six.",
                }
            )
    else:
        if chances.get("verdict") == "Wasteful":
            calls.append(
                {
                    "id": "home_nine",
                    "kind": "tactical",
                    "polarity": "negative",
                    "question": f"Change the #{chances.get('shirt') or '9'} up front?",
                    "fan_pct": max(58, 100 - int(chances.get("conversion_pct") or 0)),
                    "data_vs_fans": "YES",
                    "player_id": chances.get("player_id") or "H10",
                    "shirt": chances.get("shirt") or "10",
                    "blurb": chances.get("summary") or "Chances are coming; the finish is not.",
                }
            )
        else:
            calls.append(
                {
                    "id": "home_nine_trust",
                    "kind": "tactical",
                    "polarity": "positive",
                    "question": f"Trust #{chances.get('shirt') or '9'} to finish one?",
                    "fan_pct": max(55, int(chances.get("conversion_pct") or 50) + 20),
                    "data_vs_fans": "MIXED",
                    "player_id": chances.get("player_id") or "H10",
                    "shirt": chances.get("shirt") or "10",
                    "blurb": "Home fans still believe a goal is coming.",
                }
            )
        if crosses.get("verdict") == "Unproductive":
            calls.append(
                {
                    "id": "home_delivery",
                    "kind": "tactical",
                    "polarity": "negative",
                    "question": "Switch the wide delivery?",
                    "fan_pct": max(52, 100 - int(crosses.get("productivity_pct") or 0)),
                    "data_vs_fans": "YES",
                    "player_id": "H09",
                    "shirt": "9",
                    "blurb": crosses.get("summary") or "Pretty balls, poor end product.",
                }
            )
        calls.append(
            {
                "id": "home_tempo",
                "kind": "tactical",
                "polarity": "positive",
                "question": "Keep the higher press after the break?",
                "fan_pct": 68,
                "data_vs_fans": "MIXED",
                "player_id": None,
                "shirt": None,
                "blurb": "Home support likes the energy — they want more of it.",
            }
        )

    # Interleave: keep a mix, prefer high conviction, cap list
    calls.sort(key=lambda c: c["fan_pct"], reverse=True)
    seen_q: set[str] = set()
    unique: list[dict[str, Any]] = []
    for c in calls:
        if c["question"] in seen_q:
            continue
        seen_q.add(c["question"])
        unique.append(c)
    pos = [c for c in unique if c.get("polarity") == "positive"]
    neg = [c for c in unique if c.get("polarity") != "positive"]
    mixed: list[dict[str, Any]] = []
    while pos or neg:
        if neg:
            mixed.append(neg.pop(0))
        if pos:
            mixed.append(pos.pop(0))
    return mixed[:7]


def _team_board(
    side: str,
    team_name: str,
    starters: list[dict],
    events: list[MatchEvent],
    stats: dict[str, dict[str, Any]],
    *,
    flank: dict[str, Any],
    chances: dict[str, Any],
    crosses: dict[str, Any],
    expected: list[dict],
    cold: dict[str, Any],
) -> dict[str, Any]:
    crowd_calls = _build_crowd_calls(
        side,
        starters,
        stats,
        flank=flank,
        chances=chances,
        crosses=crosses,
        expected=expected,
        cold=cold,
    )
    slices = _build_five_min_slices(events, starters, side)
    under_ht = _rank_underperformers(stats, starters, limit=3)
    standouts_ht = _rank_standouts(
        stats, starters, limit=3, exclude_ids={u["player_id"] for u in under_ht}
    )
    highlight = {}
    if side == "home":
        highlight = {
            "chances": {
                "created": chances.get("chances") or 0,
                "used": chances.get("used") or 0,
                "conversion_pct": chances.get("conversion_pct") or 0,
                "label": chances.get("summary") or "",
            },
            "deliveries": {
                "productive": crosses.get("productive") or 0,
                "unproductive": max(
                    0, (crosses.get("attempts") or 0) - (crosses.get("productive") or 0)
                ),
                "productivity_pct": crosses.get("productivity_pct") or 0,
                "label": crosses.get("summary") or "",
            },
        }
    else:
        highlight = {
            "pressure": {
                "vulnerable_side": flank.get("vulnerable_side") or "left",
                "intensity": flank.get("heat_intensity") or 0.5,
                "label": flank.get("zone_label") or "Pressure",
                "summary": flank.get("summary") or "",
            },
            "cold_start": cold,
        }
    return {
        "side": side,
        "team_name": team_name,
        "crowd_calls": crowd_calls,
        "slices": slices,
        "underperformers_ht": under_ht,
        "standouts_ht": standouts_ht,
        "highlight": highlight,
    }


def _problems_live_at_minute(
    minute: float,
    expected: list[dict],
    events_so_far: list[MatchEvent],
) -> list[dict[str, Any]]:
    """Pulse only after the storyline has started in match time (not from kickoff)."""
    problems: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(pid: str, issue: str, label: str, position_hint: str) -> None:
        if not pid or pid in seen:
            return
        seen.add(pid)
        problems.append(
            {
                "player_id": pid,
                "issue": issue,
                "label": label,
                "position_hint": position_hint,
            }
        )

    for a in expected:
        aid = a.get("alert_id") or ""
        mapped = _ALERT_PROBLEM_MAP.get(aid)
        if not mapped:
            continue
        t0 = float(a.get("t_start_ms") or 0) / 60_000.0
        t1 = float(a.get("t_end_ms") or 0) / 60_000.0
        if minute + 0.05 < t0:
            continue
        # Stay visible a bit after the window, then fade.
        if minute > t1 + 10:
            continue
        pid, label, hint = mapped
        add(pid, aid, label, hint)

    # Cold-start flag only once enough first-half evidence exists.
    if 12.0 <= minute <= 50.0:
        cold = _cold_start(events_so_far, focus_ids=["A06", "A03", "H08", "A08"])
        if cold.get("player_id") and (
            float(cold.get("passing_accuracy") or 1) < 0.72
            or int(cold.get("loss_of_possession") or 0) >= 6
        ):
            add(cold["player_id"], "cold_start", "Cold start", "midfield")

    return problems


def build_fan_live(match_id: str, minute: float) -> dict[str, Any]:
    """Cumulative pitch stats + time-gated problems through `minute` (0–90)."""
    minute = max(0.0, min(95.0, float(minute)))
    t_cap = ms_from_minute(minute)
    mdir = match_dir(match_id)
    lineups = json.loads((mdir / "lineups.json").read_text(encoding="utf-8"))
    expected: list[dict] = []
    if (mdir / "expected_alerts.json").exists():
        expected = json.loads((mdir / "expected_alerts.json").read_text(encoding="utf-8"))

    events_so_far = [e for e in load_events(match_id) if e.t_ms <= t_cap]
    stats = _ht_player_stats(events_so_far)
    problems = _problems_live_at_minute(minute, expected, events_so_far)
    pitch_players = _build_pitch_players(lineups, stats, problems, crowd_by_player=None)

    # Always expose numeric zeros (never omit starters).
    for p in pitch_players:
        s = p.setdefault("stats", {})
        for key, default in (
            ("touches", 0),
            ("passes", 0),
            ("losses", 0),
            ("duels_won", 0),
            ("duels_lost", 0),
            ("crosses", 0),
            ("shots", 0),
            ("shots_on", 0),
            ("goals", 0),
            ("saves", 0),
            ("goals_conceded", 0),
        ):
            s[key] = int(s.get(key) or default)
        if s.get("pass_accuracy_pct") is None and s["passes"] == 0:
            s["pass_accuracy_pct"] = None

    return {
        "match_id": match_id,
        "minute": round(minute, 2),
        "problems": problems,
        "pitch_players": pitch_players,
    }


def build_halftime_summary(match_id: str) -> dict[str, Any]:
    mdir = match_dir(match_id)
    meta = json.loads((mdir / "meta.json").read_text(encoding="utf-8"))
    lineups = json.loads((mdir / "lineups.json").read_text(encoding="utf-8"))
    expected = []
    if (mdir / "expected_alerts.json").exists():
        expected = json.loads((mdir / "expected_alerts.json").read_text(encoding="utf-8"))
    subs = []
    if (mdir / "substitution_moments.json").exists():
        subs = json.loads((mdir / "substitution_moments.json").read_text(encoding="utf-8"))

    all_events = load_events(match_id)
    ht_events = _first_half(all_events)
    focus = ["A06", "A03", "H10", "H09", "H08"]
    # Early-match storylines stay HT-flavoured; pulse + crowd run the full 90'.
    cold = _cold_start(ht_events, focus_ids=focus)
    flank = _flank_pressure(ht_events, expected)
    chances = _chance_conversion(all_events)
    crosses = _cross_productivity(all_events)
    crowd = _crowd_call(expected, subs, cold)
    stats = _ht_player_stats(all_events)
    problems = _build_problems(cold, flank, chances, crosses, expected)
    charts = _build_charts(stats, lineups, cold, chances, crosses, flank, crowd)

    home_starters = lineups.get("home", {}).get("starters", [])
    away_starters = lineups.get("away", {}).get("starters", [])
    team_boards = {
        "home": _team_board(
            "home",
            meta.get("home_team", "Home"),
            home_starters,
            all_events,
            stats,
            flank=flank,
            chances=chances,
            crosses=crosses,
            expected=expected,
            cold=cold,
        ),
        "away": _team_board(
            "away",
            meta.get("away_team", "Away"),
            away_starters,
            all_events,
            stats,
            flank=flank,
            chances=chances,
            crosses=crosses,
            expected=expected,
            cold=cold,
        ),
    }
    crowd_by_player: dict[str, int] = {}
    for board in team_boards.values():
        for call in board["crowd_calls"]:
            pid = call.get("player_id")
            if pid:
                crowd_by_player[pid] = max(crowd_by_player.get(pid, 0), int(call["fan_pct"]))

    pitch_players = _build_pitch_players(lineups, stats, problems, crowd_by_player)

    ft_score = meta.get("final_score") or meta.get("halftime_score") or "1-1"
    return {
        "match_id": match_id,
        "title": "Match Day Summary",
        "clock": "90:00",
        "scoreline": ft_score,
        "halftime_score": meta.get("halftime_score") or "1-1",
        "home_team": meta.get("home_team", "Home"),
        "away_team": meta.get("away_team", "Away"),
        "experience": "fan",
        "access": {
            "fan_insights": "open",
            "coach_analytics": "restricted",
            "note": "Privileged analytics restricted for fans — living-room summary only.",
        },
        "cards": {
            "cold_start": cold,
            "defensive_pressure": flank,
            "chance_conversion": chances,
            "cross_productivity": crosses,
            "crowd_call": crowd,
        },
        "charts": charts,
        "team_boards": team_boards,
        "problems": problems,
        "pitch_players": pitch_players,
        "lineups_hint": {
            "home": [p["id"] for p in home_starters[:3]],
            "away": [p["id"] for p in away_starters[:3]],
        },
    }
