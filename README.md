# PitchPulse AI

**One intelligence engine. Two views: the bench and the living room.**

> We all love being armchair managers — PitchPulse finally puts that instinct to the test.

The platform processes on-pitch **synthetic** events and splits the same match intelligence into two distinct experiences:

- **Coaches** get the raw, real-time feed. The dashboard highlights granular tactical issues while the game is unfolding: where the team is leaking, which flank is overloaded, and who is compounding minor mistakes under pressure — so staff can make immediate adjustments and see who on the bench can stop the threat.
- **Fans** get the **halftime reality check**. To protect tactical secrets and keep things accessible, viewers do not see the heavy coaching analytics. Instead they get a streamlined Match Day Summary: did a player really start that poorly, how exposed was the defence, and was the crowd right to demand a substitution?

Built for the [Inside the Game: Developer Hackathon](https://github.com/microsoft/insidethegamehackathon) (Microsoft × Premier League).

---

## Description

We all love being armchair managers, and PitchPulse finally puts that instinct to the test. The platform processes on-pitch events and splits the data into two distinct experiences tailored for the bench and the living room.

Coaches get the raw, real-time feed. The dashboard highlights granular tactical issues while the game is unfolding: where the team is leaking, which flank is overloaded, and who is compounding minor mistakes under pressure, allowing for immediate tactical adjustments.

Fans get the halftime reality check. To protect tactical secrets and keep things accessible, viewers don't see the heavy coaching analytics. Instead, they receive a streamlined, easy-to-digest summary of the first half's main storylines. It's a chance to test their eye against the data without getting bogged down in jargon: did a specific player really start that poorly, how many times was the defense actually exposed, and was the crowd right to demand a substitution?

One intelligence engine, two views: urgent, detailed problem-solving for the coaching staff, and an engaging, stripped-down tactical recap for the fans.

**Tagline:** One match brain — urgent for the bench, clear for the living room.

**Keywords:** Football Analytics · Synthetic Match Intelligence · coaching alerts · tactical pressure · positional leaks · halftime summary · armchair manager · substitute shortlist · explainable AI · Coach Fan dual view · Azure OpenAI · Conversational AI Agent

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
| Personalize | Live bench tools + agent | Halftime summary only (separate tab in demo) |

---

## Quickstart

```bash
conda activate pitchpulse
cd ~/projects/pitchpulse-ai

# dataset (if needed)
export PYTHONPATH=src   # only if not pip install -e .
python3 -m pitchpulse.data.generate_match --match syn-001
python3 -m pitchpulse.interpret.assert_demo_alerts --match syn-001

# API
PORT=8011 python -m pitchpulse.api.main

# UI (needs Node >= 18; conda: conda install -c conda-forge "nodejs>=20")
cd web && npm install && npm run dev
# http://localhost:5173  — Fan tab = HT summary + pitch; Coach tab = live analytics + pitch
# First visit: About modal → optional Tour. Click panels for short explanations.
```

Useful endpoints:

```bash
curl -s http://localhost:8011/fan/halftime
curl -s 'http://localhost:8011/shortlist/flank_overload_right'
curl -s -X POST http://localhost:8011/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Show halftime summary"}'
```

Docs: [DATASET](docs/DATASET.md) · [INTERPRET](docs/INTERPRET.md) · [API](docs/API.md) · [EXPLAIN](docs/EXPLAIN.md) · [STUDIO](docs/STUDIO.md) · [HACKATHON-AI](docs/HACKATHON-AI.md)

Optional Azure OpenAI / Foundry: copy `.env.example` → `.env` (templates work without it).

---

## Status / roadmap

1. ~~Scaffold + synthetic generator~~
2. ~~Interpret + alert rules~~
3. ~~FastAPI + SSE~~
4. ~~Explain / personalize~~
5. ~~Shortlist + agent + studio UI~~
6. ~~Dual Fan HT / Coach live alignment (this update)~~
7. Demo script + submission polish

---

## License

MIT (intended for public hackathon submission).
