# PitchPulse AI

**One intelligence engine. Two views: the bench and the living room.**

> We all love being armchair managers — PitchPulse finally puts that instinct to the test.

The platform processes on-pitch **synthetic** events and splits the same match intelligence into two experiences:

- **Coach** — live bench feed: flank/midfield leaks, explainable alerts, substitute shortlist, and a conversational agent while the clock runs.
- **Fan** — halftime Match Day Summary: crowd calls, storylines, and an interactive pitch without exposing full coaching detail.

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

| Stage | Coach tab | Fan tab |
| --- | --- | --- |
| Ingest / Interpret | Live event stream + rolling metrics | First-half rollups for HT cards |
| Explain | Why the leak matters now | Casual verdicts (cold start, flank, crowd call) |
| Render | Alert rail + pitch zones | Storyline cards + pitch pressure map |
| Personalize | Live bench tools + agent | Halftime summary (separate tab in demo) |

---

## Quickstart

**Needs:** Python ≥ 3.11, Node ≥ 18 (conda optional).

```bash
git clone https://bitbucket.org/piworkspace/pitchpulse.git
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

Open **http://localhost:5173**

- First visit: About modal → optional Tour. Click panels for short explanations.
- **Fan** tab = halftime summary + pitch · **Coach** tab = live analytics + pitch.
- In the UI: **Load & run syn-001** to start the live stream.

Optional Azure OpenAI / Foundry: copy `.env.example` → `.env` (templates work without it).

### Useful API checks

```bash
curl -s http://localhost:8011/fan/halftime
curl -s 'http://localhost:8011/shortlist/flank_overload_right'
curl -s -X POST http://localhost:8011/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Show halftime summary"}'
```

More detail: [DATASET](docs/DATASET.md) · [INTERPRET](docs/INTERPRET.md) · [API](docs/API.md) · [EXPLAIN](docs/EXPLAIN.md) · [STUDIO](docs/STUDIO.md) · [HACKATHON-AI](docs/HACKATHON-AI.md)

---

## License

MIT (intended for public hackathon submission).
