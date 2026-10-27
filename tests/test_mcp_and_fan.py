"""MCP server/client and the fan companion team."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from pitchpulse.agent.chat import agent_chat
from pitchpulse.api.main import api_app, replay_load
from pitchpulse.api.replay_session import SESSION
from pitchpulse.mcp import server
from pitchpulse.mcp.client import MCPClient

KEY = "test-mcp-key"


@pytest.fixture(autouse=True)
def live_match(monkeypatch):
    monkeypatch.delenv("PITCHPULSE_MCP_URL", raising=False)
    monkeypatch.setenv("PITCHPULSE_MCP_KEY", KEY)
    replay_load({"match_id": "syn-001"})
    SESSION.seek(30 * 60_000)


def _rpc(method, params=None, msg_id=1):
    return {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}


def test_mcp_http_requires_key():
    client = TestClient(api_app)
    assert client.post("/mcp", json=_rpc("tools/list")).status_code == 401
    bad = client.post("/mcp", json=_rpc("tools/list"), headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401


def test_mcp_http_disabled_without_key(monkeypatch):
    monkeypatch.delenv("PITCHPULSE_MCP_KEY")
    resp = TestClient(api_app).post("/mcp", json=_rpc("tools/list"))
    assert resp.status_code == 503


def test_mcp_http_initialize_list_and_call():
    client = TestClient(api_app)
    auth = {"Authorization": f"Bearer {KEY}"}

    init = client.post(
        "/mcp",
        headers=auth,
        json=_rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "1"},
            },
        ),
    ).json()
    assert init["result"]["serverInfo"]["name"] == "pitchpulse-match-intel"
    assert (
        client.post(
            "/mcp", headers=auth, json={"jsonrpc": "2.0", "method": "notifications/initialized"}
        ).status_code
        == 202
    )

    listed = client.post("/mcp", headers=auth, json=_rpc("tools/list", msg_id=2)).json()
    names = {t["name"] for t in listed["result"]["tools"]}
    assert {"get_crowd_pulse", "get_player_status", "propose_roles_for_alert"} <= names

    called = client.post(
        "/mcp",
        headers=auth,
        json=_rpc("tools/call", {"name": "get_player_status", "arguments": {"player": "#6"}}, 3),
    ).json()
    result = called["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["players"]
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


def test_mcp_client_falls_back_to_inproc_when_http_unreachable(monkeypatch):
    monkeypatch.setenv("PITCHPULSE_MCP_URL", "http://127.0.0.1:9/mcp")
    client = MCPClient()
    assert client.transport == "mcp-http"
    clock = client.call_tool("get_match_clock", {})
    assert clock["match_minute"] == pytest.approx(30, abs=1)
    assert client.transport == "mcp-inproc"
    assert "MCP HTTP failed" in client.fallback_reason


def test_fan_team_answers_crowd_question_without_coach_tools():
    result = agent_chat("What do the other fans think right now?", engine="rules", audience="fan")

    assert result["audience"] == "fan"
    assert [a["key"] for a in result["agents"]] == ["orchestrator", "crowd_pulse", "storyteller"]
    used = {c["tool"] for c in result["tool_calls"]}
    assert used.isdisjoint(server.COACH_ONLY)
    assert "Crowd pulse" in result["reply"]
    assert all(t.get("via") == "mcp-inproc" for t in result["trace"] if t["kind"] == "tool")


def test_fan_team_player_status_by_shirt():
    result = agent_chat("How is #6 doing?", engine="rules", audience="fan")
    assert "touches" in result["reply"]
    assert "Gap:" not in result["reply"]


def test_fan_board_blocks_coach_tools():
    from pitchpulse.agent.team import Blackboard

    board = Blackboard(message="x", audience="fan")
    assert "error" in board.call_tool(
        "crowd_pulse", "propose_roles_for_alert", {"alert_id": "flank_overload_right"}
    )
