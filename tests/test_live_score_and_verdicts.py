"""Live scoreline, the Tactician's no-substitution playbook and fan verdicts vs data."""

from __future__ import annotations

import pytest

from pitchpulse.agent import tools
from pitchpulse.agent.chat import agent_chat
from pitchpulse.api.main import _status_dict, replay_load
from pitchpulse.api.replay_session import SESSION
from pitchpulse.data.score import score_at
from pitchpulse.mcp import server
from pitchpulse.personalize.halftime import build_fan_live
from pitchpulse.shortlist.tactics import suggest_tactical_adjustments


@pytest.fixture(autouse=True)
def live_match():
    replay_load({"match_id": "syn-001"})


@pytest.mark.parametrize(
    ("minute", "scoreline"), [(5, "0-0"), (25, "0-1"), (44, "1-1"), (60, "2-1"), (90, "2-1")]
)
def test_score_follows_the_clock(minute, scoreline):
    assert score_at("syn-001", minute)["scoreline"] == scoreline


def test_status_and_fan_live_carry_the_live_score():
    SESSION.seek(44 * 60_000)
    assert _status_dict(SESSION.status())["score"]["scoreline"] == "1-1"
    lowe = next(
        p for p in build_fan_live("syn-001", 44)["pitch_players"] if p["player_id"] == "H10"
    )
    assert lowe["stats"]["goals"] == 1
    assert tools.get_fan_halftime()["scoreline"] == "1-1"


def test_tactics_respect_minute_and_scoreline():
    meta = {"away_team": "Riverdale United", "away_formation": "4-2-3-1", "home_formation": "4-3-3"}
    level = {"home": 0, "away": 0, "scoreline": "0-0"}
    early = suggest_tactical_adjustments(
        "flank_overload_right", match_minute=33, rolling={}, meta=meta, score=level
    )
    assert early["timing"]["phase"] == "late first half"
    assert early["options"][0]["type"] != "substitution"
    assert not any("protect a lead" in o["change"] for o in early["options"])

    ahead = {"home": 0, "away": 1, "scoreline": "0-1"}
    late = suggest_tactical_adjustments(
        "flank_overload_right", match_minute=80, rolling={}, meta=meta, score=ahead
    )
    assert late["game_state"] == "leading"
    assert late["score_for_team"] == "1-0"


def test_tactics_tool_is_coach_only():
    assert "suggest_tactical_adjustments" in server.COACH_ONLY


def test_fan_verdicts_compare_fans_with_data():
    SESSION.seek(33 * 60_000)
    verdicts = tools.get_fan_verdicts()
    criticised = verdicts["home"]["criticised"] + verdicts["away"]["criticised"]
    assert criticised
    assert {c["verdict"] for c in criticised} <= {
        "backed by data",
        "partly backed",
        "harsh: the numbers don't support it",
        "too early to judge",
    }

    result = agent_chat(
        "Who is playing badly according to the fans, and do the numbers back it up?",
        engine="rules",
        audience="fan",
    )
    assert "Verdict:" in result["reply"]
    assert {c["tool"] for c in result["tool_calls"]} == {"get_fan_verdicts"}
