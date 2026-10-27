"""Tactical adjustments that fix a leak without a substitution.

A substitution in the 33rd minute is a big call; most of the time the bench first changes shape,
roles or pressing triggers. Each alert maps to the team that has to react and a short playbook of
on-pitch changes (formation, role, pressing, build-up), ranked by when in the match they make sense.
"""

from __future__ import annotations

from typing import Any

# alert_id → (team that must react, rolling-metric keys that prove the problem, options)
PLAYBOOK: dict[str, dict[str, Any]] = {
    "flank_overload_right": {
        "team_side": "away",
        "evidence": ("flank_strike_load_home_right", "away_lb_duel_loss_rate", "cross_attempts"),
        "options": [
            {
                "type": "formation",
                "change": "4-2-3-1 → 4-4-1-1 out of possession",
                "how": "LW drops into a flat four-man midfield line and doubles up on the home RW "
                "with the LB; CAM becomes the second striker.",
                "tradeoff": "Less counter threat down the left; the LW spends energy defending.",
                "risk": "low",
            },
            {
                "type": "role",
                "change": "Holding six shades to the left half-space",
                "how": "The CDM covers inside the LB so the full-back can show the winger outside "
                "instead of being 1v2.",
                "tradeoff": "Opens the right half-space; the other CM must hold the centre.",
                "risk": "medium",
            },
            {
                "type": "pressing",
                "change": "Cut the supply, not the cross",
                "how": "Press the home RB and right CM before the ball reaches the winger; "
                "force play back inside where the six can win it.",
                "tradeoff": "Higher pressing load; needs the whole left side to step up together.",
                "risk": "medium",
            },
            {
                "type": "formation",
                "change": "4-2-3-1 → 5-4-1 (protect a lead)",
                "how": "Drop the CDM between the centre-backs; wing-backs go one-on-one with "
                "the wide threats.",
                "tradeoff": "Gives up territory; only if the scoreline is worth protecting.",
                "risk": "high",
            },
        ],
    },
    "chaos_press_mid": {
        "team_side": "away",
        "evidence": ("midfield_turnovers", "midfield_chaos_index"),
        "options": [
            {
                "type": "formation",
                "change": "4-2-3-1 → 4-3-3 in possession",
                "how": "CAM drops level with the two CMs to make a midfield three and give the "
                "exposed six a short passing option.",
                "tradeoff": "One fewer runner between the lines.",
                "risk": "low",
            },
            {
                "type": "build_up",
                "change": "Go around or over the press",
                "how": "Keeper and centre-backs play earlier and longer to the striker or switch "
                "to the far full-back; stop forcing passes into the pivot.",
                "tradeoff": "Lower possession share; second balls become the battle.",
                "risk": "low",
            },
            {
                "type": "role",
                "change": "Centre-backs split wide, six drops between them",
                "how": "A back three in build-up adds a free man against the home front three.",
                "tradeoff": "Full-backs push high and leave space behind on the turnover.",
                "risk": "medium",
            },
        ],
    },
    "unproductive_crosses": {
        "team_side": "home",
        "evidence": ("cross_attempts", "cross_productive", "cross_productivity_rate"),
        "options": [
            {
                "type": "instruction",
                "change": "Byline cut-backs instead of early crosses",
                "how": "The RW carries to the byline and cuts back to the penalty spot; the "
                "far-side CM arrives late into that zone.",
                "tradeoff": "Slower attacks; the defence has time to drop.",
                "risk": "low",
            },
            {
                "type": "formation",
                "change": "4-3-3 → 4-4-2 when attacking",
                "how": "The LW moves inside as a second striker so crosses meet two targets "
                "instead of one.",
                "tradeoff": "Less width on the left; the LB must overlap more.",
                "risk": "medium",
            },
            {
                "type": "role",
                "change": "Overload the right side with the RB underlapping",
                "how": "RB runs inside the winger to create a 2v1 and cross from a better angle.",
                "tradeoff": "Space behind the RB on the counter.",
                "risk": "medium",
            },
        ],
    },
    "wasteful_finishing": {
        "team_side": "home",
        "evidence": ("attacker_chances", "attacker_chances_used", "attacker_conversion_rate"),
        "options": [
            {
                "type": "instruction",
                "change": "Higher-quality shots: work it into the central box",
                "how": "No shots from wide angles or outside the area unless free; the #9 attacks "
                "the near post and the CMs crash the edge of the box for cut-backs.",
                "tradeoff": "Fewer shots in total; needs patience.",
                "risk": "low",
            },
            {
                "type": "formation",
                "change": "4-3-3 → 4-4-2 with a second runner beside the #9",
                "how": "A wide forward moves central so the striker is not the only finisher.",
                "tradeoff": "Midfield is outnumbered against a 4-2-3-1.",
                "risk": "medium",
            },
            {
                "type": "set_piece",
                "change": "Target set pieces",
                "how": "Win corners and free kicks in the final third; aerial centre-backs go up.",
                "tradeoff": "Exposed to counters while centre-backs are forward.",
                "risk": "low",
            },
        ],
    },
    "midfield_link_break": {
        "team_side": "away",
        "evidence": (
            "mid_progressive_attempts",
            "mid_progressive_complete",
            "mid_progression_rate",
        ),
        "options": [
            {
                "type": "role",
                "change": "CAM drops between the lines to receive",
                "how": "The #10 shows short in the pocket behind the home midfield instead of "
                "staying high on the last line.",
                "tradeoff": "Fewer bodies in the box when the ball does arrive.",
                "risk": "low",
            },
            {
                "type": "build_up",
                "change": "Switch play to the free full-back",
                "how": "Use diagonals to the weak side rather than forcing passes through the "
                "congested centre.",
                "tradeoff": "Slower progression; relies on full-back quality.",
                "risk": "low",
            },
            {
                "type": "formation",
                "change": "4-2-3-1 → 4-1-4-1",
                "how": "One CM pushes up beside the CAM so there are two link players between "
                "the lines.",
                "tradeoff": "A single six is exposed on the counter.",
                "risk": "medium",
            },
        ],
    },
    "shot_speed_spike": {
        "team_side": "away",
        "evidence": ("home_shots", "max_shot_strike_velocity_mps"),
        "options": [
            {
                "type": "role",
                "change": "Six screens the edge of the box",
                "how": "The CDM stays in front of the centre-backs and blocks shooting lanes "
                "instead of stepping out to press.",
                "tradeoff": "Less pressure on the ball in midfield.",
                "risk": "low",
            },
            {
                "type": "pressing",
                "change": "Mid-block: drop the line 5–10 metres",
                "how": "Deny space between the lines where the home side is shooting from.",
                "tradeoff": "Concedes territory and possession.",
                "risk": "medium",
            },
        ],
    },
    "low_defensive_contacts": {
        "team_side": "away",
        "evidence": (
            "final_third_entries_vs_away",
            "defensive_contacts_away",
            "defensive_contact_rate",
        ),
        "options": [
            {
                "type": "instruction",
                "change": "Centre-backs step into the first duel",
                "how": "Front-foot defending on balls into the striker; the far CB covers.",
                "tradeoff": "Risk of being turned if the step is late.",
                "risk": "medium",
            },
            {
                "type": "formation",
                "change": "4-2-3-1 → 4-4-2 compact mid-block",
                "how": "CAM joins the striker, two banks of four stay narrow so entries meet "
                "a body early.",
                "tradeoff": "Less pressure on the opponent's build-up.",
                "risk": "low",
            },
            {
                "type": "formation",
                "change": "Back five for the last 15 minutes",
                "how": "An extra centre-back body for every entry into the box.",
                "tradeoff": "Very little attacking threat left.",
                "risk": "high",
            },
        ],
    },
}


def _timing(minute: float) -> dict[str, str]:
    if minute < 30:
        return {
            "phase": "early",
            "advice": "Too early to burn a substitution: fix it on the pitch with shape and "
            "instructions first, then re-check around 30'.",
        }
    if minute < 45:
        return {
            "phase": "late first half",
            "advice": "Change the shape now; half-time is the natural moment for a substitution "
            "if the leak continues.",
        }
    if minute < 60:
        return {
            "phase": "early second half",
            "advice": "Shape change and substitution are both open; a half-time tweak should be "
            "given 10 minutes to work.",
        }
    return {
        "phase": "closing stages",
        "advice": "All options open; combine a shape change with a fresh pair of legs.",
    }


def suggest_tactical_adjustments(
    alert_id: str,
    *,
    match_minute: float,
    rolling: dict[str, Any] | None,
    meta: dict[str, Any],
    score: dict[str, Any],
) -> dict[str, Any]:
    entry = PLAYBOOK.get(alert_id)
    if not entry:
        return {"error": f"No tactical playbook for {alert_id}", "known": list(PLAYBOOK)}
    side = entry["team_side"]
    other = "away" if side == "home" else "home"
    goal_diff = score[side] - score[other]
    state = "leading" if goal_diff > 0 else "trailing" if goal_diff < 0 else "level"

    options = list(entry["options"])
    if state != "leading":
        # Parking the bus is only worth it with a lead to protect.
        options = [o for o in options if "protect a lead" not in o["change"]]
    if match_minute < 75:
        options = [o for o in options if "last 15 minutes" not in o["change"]]
    options.sort(key=lambda o: {"low": 0, "medium": 1, "high": 2}[o["risk"]])

    rolling = rolling or {}
    return {
        "alert_id": alert_id,
        "team_side": side,
        "team": meta.get(f"{side}_team", side),
        "current_formation": meta.get(f"{side}_formation"),
        "opponent_formation": meta.get(f"{other}_formation"),
        "match_minute": round(match_minute, 1),
        "scoreline": score["scoreline"],
        "score_for_team": f"{score[side]}-{score[other]}",
        "game_state": state,
        "timing": _timing(match_minute),
        "evidence": {k: rolling.get(k) for k in entry["evidence"]},
        "options": options[:3],
    }
