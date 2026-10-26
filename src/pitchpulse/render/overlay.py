"""Machine-readable on-screen graphic packets (English)."""

from __future__ import annotations

from typing import Any


ZONE_BY_ALERT = {
    "flank_overload_right": "right_flank_final_third",
    "chaos_press_mid": "central_mid",
    "unproductive_crosses": "right_flank_final_third",
    "midfield_link_break": "central_mid",
    "wasteful_finishing": "final_third",
    "shot_speed_spike": "final_third",
    "low_defensive_contacts": "defensive_third",
}

TITLE_BY_ALERT = {
    "flank_overload_right": "Right flank overload",
    "chaos_press_mid": "Midfield press chaos",
    "unproductive_crosses": "Unproductive deliveries",
    "midfield_link_break": "Midfield link break",
    "wasteful_finishing": "Wasteful finishing",
    "shot_speed_spike": "Shot speed spike",
    "low_defensive_contacts": "Low defensive contacts",
}


def build_overlay_packet(
    *,
    alert_id: str,
    t_ms: int,
    explanation: dict[str, Any],
    severity: str = "warning",
) -> dict[str, Any]:
    modes = explanation.get("modes") or {}
    return {
        "t_ms": t_ms,
        "alert_id": alert_id,
        "severity": severity,
        "graphic": {
            "type": "zone_highlight",
            "zone": ZONE_BY_ALERT.get(alert_id, "middle_third"),
            "title": TITLE_BY_ALERT.get(alert_id, alert_id),
            "subtitle": explanation.get("why") or "",
        },
        "modes": {
            "coach": modes.get("coach", ""),
            "analyst": modes.get("analyst", ""),
            "fan": modes.get("fan", ""),
        },
        "source": explanation.get("source"),
    }
