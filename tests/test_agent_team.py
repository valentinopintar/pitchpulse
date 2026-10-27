"""Multi-agent bench team: rule-based routing, Azure function-calling loop (faked), recovery."""

from __future__ import annotations

import json

import pytest

from pitchpulse.agent import team
from pitchpulse.agent.chat import agent_chat
from pitchpulse.api.main import replay_load
from pitchpulse.api.replay_session import SESSION
from pitchpulse.explain import azure_client
from pitchpulse.explain.azure_client import AzureChatError


@pytest.fixture(autouse=True)
def live_match():
    replay_load({"match_id": "syn-001"})
    SESSION.seek(40 * 60_000)


def _kinds(result, agent):
    return [t["kind"] for t in result["trace"] if t["agent"] == agent]


def test_rules_team_hands_focus_from_analyst_to_scout():
    result = agent_chat("Who can fix the flank?", engine="rules")

    assert result["engine"] == "rules"
    handoffs = [t["agent"] for t in result["trace"] if t["kind"] == "handoff"]
    assert handoffs == ["analyst", "bench_scout"]
    scout_call = next(c for c in result["tool_calls"] if c["tool"] == "propose_roles_for_alert")
    assert scout_call["agent"] == "bench_scout"
    assert scout_call["args"]["alert_id"] == result["focus_alert_id"]
    assert "Gap:" in result["reply"]


def test_rules_team_storyteller_and_help():
    story = agent_chat("Show halftime summary", engine="rules")
    assert [t["agent"] for t in story["trace"] if t["kind"] == "handoff"] == ["storyteller"]
    assert "Halftime summary" in story["reply"]

    idle = agent_chat("hello", engine="rules")
    assert "Try:" in idle["reply"]
    assert not [t for t in idle["trace"] if t["kind"] == "handoff"]


def _call(name, args, call_id):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


class FakeAzure:
    """Scripted assistant turns per agent, keyed by the start of the system prompt."""

    def __init__(self, fail_for: str | None = None):
        self.fail_for = fail_for
        self.scripts = {
            "You are the Orchestrator": [
                {"tool_calls": [_call("handoff_to_analyst", {"task": "What leaks?"}, "o1")]},
                {"tool_calls": [_call("handoff_to_bench_scout", {"task": "Fix it"}, "o2")]},
                {"content": "Desni bok curi; uvedite najboljeg beka s klupe."},
            ],
            "You are the Match Analyst": [
                {
                    "tool_calls": [
                        _call("explain_alert", {"alert_id": "flank_overload_right"}, "a1")
                    ]
                },
                {"content": "flank_overload_right is the main leak."},
            ],
            "You are the Bench Scout": [
                {
                    "tool_calls": [
                        _call("propose_roles_for_alert", {"alert_id": "flank_overload_right"}, "b1")
                    ]
                },
                {"content": "Best fit: aerial full-back."},
            ],
        }
        self.seen_context: list[str] = []

    def __call__(self, messages, tools, **_kw):
        system = messages[0]["content"]
        for prefix, script in self.scripts.items():
            if system.startswith(prefix):
                if self.fail_for and prefix.endswith(self.fail_for):
                    raise AzureChatError("HTTP 429")
                self.seen_context.append(system)
                return script.pop(0)
        raise AssertionError(f"unexpected agent prompt: {system[:40]}")


@pytest.fixture
def fake_azure(monkeypatch):
    def install(**kw):
        fake = FakeAzure(**kw)
        monkeypatch.setattr(azure_client, "azure_configured", lambda: True)
        monkeypatch.setattr(azure_client, "chat_with_tools", fake)
        return fake

    return install


def test_azure_team_orchestrates_with_shared_state(fake_azure):
    fake = fake_azure()
    result = agent_chat("Who can fix the flank?")

    assert result["engine"] == "azure_openai"
    assert result["reply"].startswith("Desni bok")
    assert result["focus_alert_id"] == "flank_overload_right"
    assert [c["agent"] for c in result["tool_calls"]] == ["analyst", "bench_scout"]
    scout_prompt = next(s for s in fake.seen_context if s.startswith("You are the Bench Scout"))
    assert "Focus alert: flank_overload_right" in scout_prompt
    assert "Match Analyst reported" in scout_prompt


def test_specialist_failure_recovers_on_rules(fake_azure):
    fake_azure(fail_for="Bench Scout")
    result = agent_chat("Who can fix the flank?")

    assert result["engine"] == "mixed"
    assert result["recovered"] is True
    assert "recovered" in _kinds(result, "bench_scout")
    scout_report = next(
        t for t in result["trace"] if t["agent"] == "bench_scout" and t["kind"] == "report"
    )
    assert scout_report["source"] == "rules"
    assert result["reply"].startswith("Desni bok")


def test_orchestrator_failure_falls_back_to_rules_team(fake_azure):
    fake_azure(fail_for="Orchestrator")
    result = agent_chat("Who can fix the flank?")

    assert result["recovered"] is True
    assert "Gap:" in result["reply"]
    assert [t["agent"] for t in result["trace"] if t["kind"] == "handoff"] == [
        "analyst",
        "bench_scout",
    ]


def test_openai_key_routes_to_openai_api(monkeypatch):
    for var in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    sent = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

    def fake_urlopen(req, timeout):
        sent.update(
            url=req.full_url, auth=req.get_header("Authorization"), body=json.loads(req.data)
        )
        return Resp()

    monkeypatch.setattr(azure_client.urllib.request, "urlopen", fake_urlopen)
    msg = azure_client.chat_with_tools([{"role": "user", "content": "hi"}], [])

    assert azure_client.provider() == "openai"
    assert msg["content"] == "ok"
    assert sent["url"] == "https://api.openai.com/v1/chat/completions"
    assert sent["auth"] == "Bearer sk-test"
    assert sent["body"]["model"] == "gpt-4.1"


def test_openai_tool_schemas_cover_every_specialist_tool():
    for spec in team.SPECIALISTS.values():
        for schema in team.tools.openai_tools(list(spec.tools)):
            assert schema["function"]["parameters"]["type"] == "object"
