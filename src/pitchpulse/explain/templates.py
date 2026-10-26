"""Deterministic Coach / Analyst / Fan narratives (English)."""

from __future__ import annotations

from typing import Any

# PitchPulse alert_id → audience copy
ALERT_COPY: dict[str, dict[str, str]] = {
    "flank_overload_right": {
        "coach": (
            "Right flank is leaking. Cross load and duel losses on the away left-back "
            "are stacking. Tighten wide cover now; if it continues, prepare a full-back "
            "with stronger cross-defend and aerial traits."
        ),
        "analyst": (
            "Window signal: elevated home flank_strike_load on the right and high "
            "away_lb_duel_loss_rate. Pattern = structural overload, not a single foul."
        ),
        "fan": (
            "The home side keeps whipping balls in from the right. Watch the away left-back — "
            "they are under real pressure. A change at that position would not be a surprise."
        ),
        "why": "Control is shifting to chaos on one flank: repeated entries beat individual recovery.",
    },
    "chaos_press_mid": {
        "coach": (
            "Midfield is losing the press battle. The exposed pivot is coughing up turnovers. "
            "Cue: simplify under pressure or introduce a press-resistant six."
        ),
        "analyst": (
            "Clustered midfield_turnovers with rising midfield_chaos_index. "
            "Rhythm break is central, not wide."
        ),
        "fan": (
            "The middle of the park looks scrambled — loose balls and rushed passes. "
            "If the coach switches the holding midfielder, that is why."
        ),
        "why": "Game rhythm snaps when central duels fail under sustained pressure.",
    },
    "unproductive_crosses": {
        "coach": (
            "Wide deliveries are stacking but productivity is low — incomplete or not into the box. "
            "Either cut the source earlier or bring a wide player who can actually pick out targets."
        ),
        "analyst": (
            "Elevated cross_attempts with low cross_productivity_rate. "
            "Volume without end product — delivery quality, not just count."
        ),
        "fan": (
            "Lots of balls whipped in from the wing, but almost none are useful. "
            "Pretty crosses, poor end product."
        ),
        "why": "A cross only matters if it reaches a dangerous zone — productivity beats volume.",
    },
    "wasteful_finishing": {
        "coach": (
            "The #9 is getting big chances and not using them. Conversion is too low — "
            "cue a clinical finisher or force the shot selection to simplify."
        ),
        "analyst": (
            "attacker_chances high vs attacker_conversion_rate low "
            "(chances_used / chances). Pattern = wasteful finishing, not chance drought."
        ),
        "fan": (
            "The striker keeps getting looks and keeps missing. "
            "Chances created — not converted."
        ),
        "why": "Creating chances without converting them wastes territorial dominance.",
    },
    "midfield_link_break": {
        "coach": (
            "Progressive passes through midfield are breaking down. "
            "The supply line to the attackers is stalled — introduce a progressive CAM/CM."
        ),
        "analyst": (
            "mid_progressive_attempts up with low mid_progression_rate. "
            "Link break is central supply, not the final shot."
        ),
        "fan": (
            "The middle can't find the attackers — passes forward keep dying. "
            "That is why the front three look isolated."
        ),
        "why": "Without midfield progression, attackers starve even when space exists ahead.",
    },
    "shot_speed_spike": {
        "coach": "Shot strike velocity is spiking. Track box occupancy and keeper starting position.",
        "analyst": (
            "Home shots with high shot_strike_velocity_mps in a short window — finishing threat uptick."
        ),
        "fan": "The home attackers are hitting the ball cleaner and harder — keepers are busy.",
        "why": "Finishing quality, not just shot count, is changing the threat profile.",
    },
    "low_defensive_contacts": {
        "coach": (
            "Entries against are not meeting enough defensive contacts. "
            "Cue the back line to step into first duels earlier."
        ),
        "analyst": "Low defensive_contact_rate vs final_third_entries — soft defensive third.",
        "fan": (
            "Attackers are getting into the box too easily — the defence is not winning enough first contacts."
        ),
        "why": "Without early contacts, chaos compounds into clear chances.",
    },
}


def template_modes_for_alert(
    alert_id: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, str]:
    _ = evidence
    block = ALERT_COPY.get(alert_id)
    if not block:
        generic = f"Alert {alert_id} fired. Review rolling evidence and respond."
        return {"coach": generic, "analyst": generic, "fan": generic, "why": generic}
    return {
        "coach": block["coach"],
        "analyst": block["analyst"],
        "fan": block["fan"],
        "why": block["why"],
    }


def fan_substitution_copy(moment: dict[str, Any]) -> str:
    before = moment.get("metrics_before") or {}
    after = moment.get("metrics_after") or {}
    off_id = moment.get("player_off_id")
    on_id = moment.get("player_on_id")
    alert = moment.get("addresses_alert_id")
    return (
        f"At the substitution ({off_id} → {on_id}), the coach addressed {alert}. "
        f"Before: flank crosses {before.get('flank_strike_load_home_right')}, "
        f"mid turnovers {before.get('midfield_turnovers')}. "
        f"After: crosses {after.get('flank_strike_load_home_right')}, "
        f"mid turnovers {after.get('midfield_turnovers')}. "
        f"{moment.get('observable_outcome', '')}"
    )
