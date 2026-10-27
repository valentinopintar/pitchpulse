# PitchPulse AI

**One intelligence engine. Two views: the bench and the living room.**

> We all love being armchair managers — PitchPulse finally puts that instinct to the test.

The platform processes on-pitch **synthetic** events and splits the same match intelligence into two experiences:

- **Coach** — live bench feed: flank/midfield leaks, explainable alerts, substitute shortlist, and a multi-agent bench team (Orchestrator → Match Analyst, Bench Scout, Storyteller on Azure OpenAI function calling, with a visible trace) while the clock runs.
- **Fan** — halftime Match Day Summary: crowd calls, storylines, an interactive pitch, and a Fan Companion chat (Crowd Pulse + Storyteller agents: what other fans think, how a player is doing) without exposing full coaching detail.
- **MCP** — every agent tool call goes through a PitchPulse MCP server (`/api/mcp`, bearer-key protected) that external clients like GitHub Copilot can use too. See [MCP](docs/MCP.md).

Built for the [Inside the Game: Developer Hackathon](https://github.com/microsoft/insidethegamehackathon) (Microsoft × Premier League).

**Tagline:** One match brain — urgent for the bench, clear for the living room.

---

## Pipeline

```text
Live synthetic events
  → positional leak detection
  → explainable coaching alerts (+ bench shortlist)
  → Fan Match Day Summary (halftime) from the same intelligence
  → dual UI tabs: Fan (insights + pitch) | Coach (analytics + pitch)
```


| Stage              | Coach tab                           | Fan tab                                         |
| ------------------ | ----------------------------------- | ----------------------------------------------- |
| Ingest / Interpret | Live event stream + rolling metrics | First-half rollups for HT cards                 |
| Explain            | Why the leak matters now            | Casual verdicts (cold start, flank, crowd call) |
| Render             | Alert rail + pitch zones            | Storyline cards + pitch pressure map            |
| Personalize        | Live bench tools + agent            | Halftime summary (separate tab in demo)         |


---

## Quickstart

**Needs:** Python ≥ 3.11, Node ≥ 18 (conda optional).

```bash
git clone https://github.com/valentinopintar/pitchpulse.git
cd pitchpulse

# Python env
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[api]"

# Demo match dataset (syn-001 ships under data/matches/; regenerate if needed)
export PYTHONPATH=src
python -m pitchpulse.data.generate_match --match syn-001

# Terminal 1 — API
PORT=8011 python -m pitchpulse.api.main

# Terminal 2 — UI
cd web && npm install && npm run dev
```

Open **[http://localhost:5173](http://localhost:5173)**

- First visit: About modal → optional Tour. Click panels for short explanations.
- **Fan** tab = halftime summary + pitch · **Coach** tab = live analytics + pitch.
- In the UI: **Load & run syn-001** to start the live stream.

### LLM is optional

Copy `.env.example` → `.env` (git-ignored, never committed) and fill **one** option:

| Option | Env vars | What you get |
| --- | --- | --- |
| **A. Azure OpenAI / Foundry** (preferred) | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` | Model-driven agent team + LLM narratives |
| **B. OpenAI API** (local testing) | `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4.1`) | Same as A via api.openai.com |
| **None** (default) | — | Rule-based agent team + template narratives |

Without a key the app and the bench chat **still work**: the same four agents run on keyword routing and the trace shows `RULES`. What you lose is free-form questions, answers in other languages (the LLM replies in the user's language), and model-written explanations. Try rule-based prompts such as “What is leaking?”, “Who can fix the flank?”, “Show halftime summary”.

### Useful API checks

```bash
curl -s http://localhost:8011/fan/halftime
curl -s 'http://localhost:8011/shortlist/flank_overload_right'
curl -s -X POST http://localhost:8011/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Show halftime summary"}'
```

More detail: [MCP](docs/MCP.md) · [DATASET](docs/DATASET.md) · [INTERPRET](docs/INTERPRET.md) · [API](docs/API.md) · [EXPLAIN](docs/EXPLAIN.md) · [STUDIO](docs/STUDIO.md) · [HACKATHON-AI](docs/HACKATHON-AI.md)

---

## Docker (single URL)

Builds the Vite UI and serves it from FastAPI: **UI `/`**, **API `/api`**, port **7860** (Hugging Face Spaces default).

```bash
docker build -t pitchpulse .
docker run --rm -p 7860:7860 pitchpulse
# open http://localhost:7860  → Load & run syn-001
```

**Hugging Face Spaces:** New Space → SDK **Docker** → link this GitHub repo (or push the Dockerfile). Public URL will look like `https://<user>-pitchpulse.hf.space`.

Local `PORT=8011` + `npm run dev` is unchanged when `web/dist` is absent (API stays at `/`).

---

## License

MIT (intended for public hackathon submission).