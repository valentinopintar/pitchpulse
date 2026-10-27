# Hackathon AI / LLM guidance

## Do you bring your own OpenAI?

**Official rules do not ship a shared ChatGPT key.** You are expected to use **your own Microsoft Azure / Foundry access** (or other Microsoft AI services) for the LLM layer.

PitchPulse supports:

1. **Azure OpenAI / Microsoft Foundry** (preferred for judging) — set env vars in `.env`
2. **Template narratives** (always on) — Coach / Fan English copy without any cloud key so demos never break

Personal **OpenAI.com** API keys can work technically if you adapt the client, but the hackathon scoring emphasizes **Microsoft platform** (Foundry, Agent Framework, Azure AI Services, Fabric, ACA/AKS, GitHub Copilot, etc.). Prefer Azure OpenAI via your Azure subscription.

## What judges look for (from Official Rules)

- Innovative use of the **Microsoft AI platform**
- Category prizes include **Best Use of Microsoft Foundry**, Multi-Agent, Azure Cloud Native
- Stage-one viability: project should reasonably apply featured Microsoft technologies
- You must use **synthetic** football data (PitchPulse generator already does)

They do **not** redistribute real Premier League match data or a free OpenAI sandbox key in the rules text — you provision Azure yourself (free trial / student / sponsor credits if available).

## PitchPulse wiring

| Env | Purpose |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Resource endpoint |
| `AZURE_OPENAI_API_KEY` | API key |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | API version |

For local testing you can instead set `OPENAI_API_KEY` (+ optional `OPENAI_MODEL`, default `gpt-4.1`); Azure wins when both are set.

Without these, `POST /explain/alert` and SSE alerts still return **template** copy (`source: "template"`). With them, explain can return `source: "azure_openai"`.

```bash
cp .env.example .env
# edit credentials
conda activate pitchpulse
PORT=8011 python -m pitchpulse.api.main
```

See [EXPLAIN.md](EXPLAIN.md) and [API.md](API.md).

## Multi-agent bench team

`POST /agent/chat` runs a team of agents ([team.py](../src/pitchpulse/agent/team.py)):

| Agent | Role | Tools |
| --- | --- | --- |
| **Orchestrator** | Routes the question with `handoff_to_*` tools, writes the final answer in the user's language | handoffs, `set_viewer_profile` |
| **Match Analyst** | What is leaking and why it matters now; sets the focus alert | `get_match_clock`, `get_match_state`, `list_alerts`, `explain_alert` |
| **Tactician** | Fixes the leak on the pitch without a substitution — formation, role, pressing, build-up — weighed against the minute and the scoreline | `suggest_tactical_adjustments`, `get_match_clock` |
| **Bench Scout** | Substitutes whose profile closes the focus gap | `propose_roles_for_alert`, `list_alerts` |
| **Storyteller** | Fan halftime summary, recap, overlay copy (any language) | `get_fan_halftime`, `generate_match_recap`, `get_overlay_packet` |
| **Crowd Pulse** (fan team) | What other fans think, how a player is doing, and whether the fans' criticism is backed by the numbers — summary level | `get_crowd_pulse`, `get_player_status`, `get_fan_verdicts`, `get_match_clock` |

A substitution in the 33rd minute is a big call, so a "who can fix it?" question gets both the Tactician's on-pitch change and the Bench Scout's shortlist; "without a sub" skips the Scout.

Two audiences share the agents: the **coach team** (Analyst, Tactician, Bench Scout, Storyteller) and the **fan team** (Crowd Pulse, Storyteller; `"audience": "fan"`), which can't reach coach-only tools. All tool calls go through the [MCP server](MCP.md).

- **Shared state** — a per-request blackboard holds the focus alert and each agent's report; every specialist sees teammates' findings in its prompt.
- **Function calling** — each agent is an Azure OpenAI tool loop (`chat_with_tools`) limited to its own tools.
- **Recovery** — every agent has a rule-based twin ([rules.py](../src/pitchpulse/agent/rules.py)). If a model call fails, that agent finishes on rules and the run continues (`engine: "mixed"`, `recovered: true`). Without Azure the whole team runs on rules.
- **Trace** — the response carries `trace` (handoffs, tool calls, reports, recoveries with timings); the Coach tab shows it under each answer. Send `"engine": "rules"` to force the rule-based team.
