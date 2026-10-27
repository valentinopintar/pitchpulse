"""Multi-agent bench team: Orchestrator → Match Analyst / Bench Scout / Storyteller.

Each agent runs on Azure OpenAI function calling when configured. Agents coordinate through a
shared Blackboard (focus alert + teammates' findings). Every agent has a rule-based twin in
`rules.py`; if a model call fails mid-run, that agent recovers on its twin and the run continues.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pitchpulse.agent import rules, tools
from pitchpulse.explain import azure_client
from pitchpulse.explain.azure_client import AzureChatError
from pitchpulse.mcp.client import MCPClient
from pitchpulse.mcp.server import COACH_ONLY

MAX_TOOL_ROUNDS = 4
MAX_HANDOFFS = 4
RESULT_CHARS = 3500


@dataclass
class Blackboard:
    """Shared state for one request: what the agents found and everything they did."""

    message: str
    audience: str = "coach"
    focus_alert_id: str | None = None
    findings: dict[str, str] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    started: float = field(default_factory=time.perf_counter)
    mcp: MCPClient = field(default_factory=MCPClient)

    def log(self, agent: str, kind: str, detail: str, **extra: Any) -> None:
        self.trace.append(
            {
                "step": len(self.trace) + 1,
                "agent": agent,
                "kind": kind,
                "detail": detail,
                "ms": round((time.perf_counter() - self.started) * 1000),
                **extra,
            }
        )

    def call_tool(self, agent: str, name: str, args: dict[str, Any]) -> Any:
        if self.audience == "fan" and name in COACH_ONLY:
            result: Any = {"error": f"{name} is restricted to the coach view"}
        else:
            try:
                result = self.mcp.call_tool(name, args)
            except Exception as exc:  # a broken tool must not sink the whole team
                result = {"error": f"{type(exc).__name__}: {exc}"}
            if self.mcp.fallback_reason:
                self.log(agent, "recovered", self.mcp.fallback_reason)
                self.mcp.fallback_reason = None
        ok = not (isinstance(result, dict) and "error" in result)
        if ok and name in ("explain_alert", "propose_roles_for_alert") and args.get("alert_id"):
            self.focus_alert_id = self.focus_alert_id or args["alert_id"]
        self.tool_calls.append({"agent": agent, "tool": name, "args": args, "result": result})
        self.log(agent, "tool", name, args=args, ok=ok, via=self.mcp.transport)
        return result

    def context(self) -> str:
        lines = [f"Focus alert: {self.focus_alert_id or 'not set yet'}"]
        for agent, text in self.findings.items():
            lines.append(f"{SPECIALISTS[agent].name} reported:\n{text}")
        return "\n\n".join(lines)


@dataclass(frozen=True)
class Specialist:
    key: str
    name: str
    role: str
    tools: tuple[str, ...]
    prompt: str
    fallback: Callable[[Blackboard, str], str]


_SHARED_RULES = """
Synthetic football data only; fictional players are fine. Use your tools — never invent numbers.
Report back to the Orchestrator in English, at most 6 short lines, citing the numbers you used."""

SPECIALISTS: dict[str, Specialist] = {
    s.key: s
    for s in (
        Specialist(
            key="analyst",
            name="Match Analyst",
            role="Reads the live match: clock, rolling metrics, active alerts, and explains why a "
            "leak matters. Sets the focus alert for teammates.",
            tools=("get_match_clock", "get_match_state", "list_alerts", "explain_alert"),
            prompt="You are the Match Analyst on a football bench team. Find what is leaking right "
            "now (list_alerts), pick the single most relevant alert, explain_alert it and "
            "say why it matters at this minute." + _SHARED_RULES,
            fallback=rules.analyst,
        ),
        Specialist(
            key="bench_scout",
            name="Bench Scout",
            role="Proposes bench substitutes whose profile can close a specific tactical gap.",
            tools=("propose_roles_for_alert", "list_alerts"),
            prompt="You are the Bench Scout. Use the focus alert from shared state unless the task "
            "names another, call propose_roles_for_alert, and recommend the best fit with a "
            "one-line reason per candidate." + _SHARED_RULES,
            fallback=rules.bench_scout,
        ),
        Specialist(
            key="storyteller",
            name="Storyteller",
            role="Turns intelligence into fan-facing narratives: halftime summary, match recap, "
            "on-screen overlay graphics. Writes in any language requested.",
            tools=("get_fan_halftime", "generate_match_recap", "get_overlay_packet"),
            prompt="You are the Storyteller for a broadcast studio. Turn match intelligence into "
            "clear, warm copy for casual fans (halftime summary, recap, overlay). No private "
            "coaching instructions. If the task names a language, write the story in it."
            + _SHARED_RULES.replace("in English, ", ""),
            fallback=rules.storyteller,
        ),
        Specialist(
            key="crowd_pulse",
            name="Crowd Pulse",
            role="Fan companion: what other fans think (crowd calls, who the stands love or doubt "
            "right now) and how a given player is doing so far, at summary level.",
            tools=("get_crowd_pulse", "get_player_status", "get_match_clock"),
            prompt="You are Crowd Pulse, a friendly companion for fans watching the match. Use "
            "get_crowd_pulse for what the stands think and get_player_status for a named player "
            "(shirt '#6' or surname). Summary level only: fan percentages, simple stats, the "
            "storyline. Never give tactical instructions or substitution advice — that is the "
            "coach's private view." + _SHARED_RULES,
            fallback=rules.crowd_pulse,
        ),
    )
}

AUDIENCES: dict[str, dict[str, Any]] = {
    "coach": {
        "specialists": ("analyst", "bench_scout", "storyteller"),
        "extra_tools": ("set_viewer_profile",),
        "prompt": """You are the Orchestrator of PitchPulse, a football bench team of agents.
Delegate with the handoff_to_* tools; never answer match questions from your own knowledge.
- What is leaking / why / metrics / clock → Match Analyst.
- Who can fix it / substitutes → Match Analyst first (it sets the focus alert), then Bench Scout.
- Halftime summary / recap / overlay / fan story → Storyteller.
- "coach" or "fan" view switch → set_viewer_profile.
Give each specialist a precise task. When you have their reports, write the final answer for the
user: concise, concrete, in the same language the user wrote in.""",
    },
    "fan": {
        "specialists": ("crowd_pulse", "storyteller"),
        "extra_tools": (),
        "prompt": """You are the Orchestrator of PitchPulse's fan companion, talking to a casual fan.
Delegate with the handoff_to_* tools; never answer match questions from your own knowledge.
- What other fans think / a player's form right now / man of the match → Crowd Pulse.
- Halftime summary / recap / the story of the match → Storyteller.
Keep it light and short (max 4 sentences), no tactical jargon, no coaching or substitution advice.
Answer in the same language the user wrote in.""",
    },
}


def _clip(result: Any) -> str:
    text = json.dumps(result, default=str, ensure_ascii=False)
    return text if len(text) <= RESULT_CHARS else text[:RESULT_CHARS] + "…(truncated)"


def _args(call: dict[str, Any]) -> dict[str, Any]:
    try:
        args = json.loads(call["function"].get("arguments") or "{}")
    except json.JSONDecodeError:
        return {}
    return args if isinstance(args, dict) else {}


def _llm_specialist(spec: Specialist, board: Blackboard, task: str) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": f"{spec.prompt}\n\nShared state:\n{board.context()}"},
        {"role": "user", "content": task},
    ]
    schemas = tools.openai_tools(list(spec.tools))
    for _ in range(MAX_TOOL_ROUNDS):
        msg = azure_client.chat_with_tools(messages, schemas)
        calls = msg.get("tool_calls") or []
        if not calls:
            return (msg.get("content") or "").strip()
        messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": calls})
        for call in calls:
            name = call["function"]["name"]
            if name in spec.tools:
                result = board.call_tool(spec.key, name, _args(call))
            else:
                result = {"error": f"{name} is not one of your tools"}
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": _clip(result)})
    raise AzureChatError("tool loop did not converge")


def run_specialist(key: str, board: Blackboard, task: str, *, use_llm: bool) -> str:
    spec = SPECIALISTS[key]
    board.log(key, "handoff", task)
    text = ""
    source = "rules"
    if use_llm:
        try:
            text = _llm_specialist(spec, board, task)
            source = "llm"
        except AzureChatError as exc:
            board.log(key, "recovered", f"Model call failed ({exc}); {spec.name} switched to rules")
    if not text:
        text = spec.fallback(board, task)
        source = "rules"
    board.findings[key] = text
    board.log(key, "report", text, source=source)
    return text


def _handoff_tools(keys: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": f"handoff_to_{spec.key}",
                "description": f"{spec.name}: {spec.role}",
                "parameters": {
                    "type": "object",
                    "properties": {"task": {"type": "string", "description": "What to do"}},
                    "required": ["task"],
                },
            },
        }
        for spec in (SPECIALISTS[k] for k in keys)
    ]


def _orchestrate_llm(board: Blackboard) -> str:
    setup = AUDIENCES[board.audience]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": setup["prompt"]},
        {"role": "user", "content": board.message},
    ]
    schemas = _handoff_tools(setup["specialists"]) + tools.openai_tools(list(setup["extra_tools"]))
    handoffs = 0
    for _ in range(MAX_HANDOFFS + 2):
        msg = azure_client.chat_with_tools(messages, schemas)
        calls = msg.get("tool_calls") or []
        if not calls:
            return (msg.get("content") or "").strip()
        messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": calls})
        for call in calls:
            name, args = call["function"]["name"], _args(call)
            key = name.removeprefix("handoff_to_")
            if name in setup["extra_tools"]:
                result: Any = board.call_tool("orchestrator", name, args)
            elif key in setup["specialists"] and handoffs < MAX_HANDOFFS:
                handoffs += 1
                task = str(args.get("task") or board.message)
                report = run_specialist(key, board, task, use_llm=True)
                result = {"agent": SPECIALISTS[key].name, "report": report}
            else:
                result = {"error": "Handoff budget used up — write the final answer now."}
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": _clip(result)})
    raise AzureChatError("orchestrator did not converge")


def _orchestrate_rules(board: Blackboard) -> str:
    lower = board.message.lower()
    if board.audience == "fan":
        plan = rules.route_fan(lower)
    else:
        mode = rules.viewer_mode(lower)
        if mode:
            board.call_tool("orchestrator", "set_viewer_profile", {"mode": mode})
        plan = rules.route(lower)
    if not plan and not board.findings:
        return rules.HELP_TEXT
    board.log("orchestrator", "plan", " → ".join(SPECIALISTS[k].name for k in plan) or "(reuse)")
    for key in plan:
        if key not in board.findings:
            run_specialist(key, board, board.message, use_llm=False)
    return "\n".join(board.findings.values())


def run_team(message: str, *, engine: str | None = None, audience: str = "coach") -> dict[str, Any]:
    from pitchpulse.api.studio_state import STUDIO

    audience = audience if audience in AUDIENCES else "coach"
    board = Blackboard(message=(message or "").strip(), audience=audience)
    llm = azure_client.provider()
    use_llm = engine != "rules" and llm is not None
    board.log(
        "orchestrator",
        "start",
        f"{audience} team · {llm or 'rule-based'} routing · tools via {board.mcp.transport}",
    )

    reply = ""
    if use_llm:
        try:
            reply = _orchestrate_llm(board)
        except AzureChatError as exc:
            board.log(
                "orchestrator", "recovered", f"Model call failed ({exc}); finishing with rules"
            )
    if not reply:
        reply = _orchestrate_rules(board)
    board.log("orchestrator", "final", f"{len(reply)} chars")

    sources = {t["source"] for t in board.trace if t["kind"] == "report"}
    recovered = any(t["kind"] == "recovered" for t in board.trace)
    if use_llm and not recovered and sources <= {"llm"}:
        engine_used = llm
    elif not use_llm:
        engine_used = "rules"
    else:
        engine_used = "mixed"

    return {
        "reply": reply,
        "engine": engine_used,
        "recovered": recovered,
        "audience": audience,
        "tool_transport": board.mcp.transport,
        "focus_alert_id": board.focus_alert_id,
        "agents": [{"key": "orchestrator", "name": "Orchestrator"}]
        + [
            {"key": k, "name": SPECIALISTS[k].name, "tools": list(SPECIALISTS[k].tools)}
            for k in AUDIENCES[audience]["specialists"]
        ],
        "trace": board.trace,
        "tool_calls": board.tool_calls,
        "viewer": STUDIO.viewer.to_dict(),
        "tools": tools.TOOL_SPECS,
    }
