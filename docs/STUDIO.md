# Studio — dual experience (demo tabs)

PitchPulse is **one engine, two product views**. In the demo UI, **Fan** and **Coach** tabs simulate separate audiences (fans never see the coach workspace; coaches never see the fan summary as their primary screen).

| Tab | Left | Right |
| --- | --- | --- |
| **Fan** | Home \| Away boards — **crowd calls** (hero), **90'** 5-min pulse (0–5'…85–90'), highlights | Full-width interactive pitch — click players; pulse = problems |
| **Coach** | Coach Analytics — live alerts, shortlist, agent | Pitch tactical zones |

There is **no** blurred “restricted” overlay in the demo. Switching tabs is the access simulation.

## About + guided tour

- **About** (header) — short product explainer for judges; opens on first visit.
- **Tour** — Next / Back / Skip walkthrough (load → Fan cards → pitch → Coach → alerts → shortlist → agent).
- **Click-to-explain** — click Fan cards, pitch, coach panels for a short “what is this?” popup (disabled while the tour is active).

## Run

```bash
PORT=8011 python -m pitchpulse.api.main
cd web && npm install && npm run dev
```

Open `http://localhost:5173` → **Load & run syn-001** → toggle **Fan** / **Coach**.

## Fan HT API

```bash
curl -s http://localhost:8011/fan/halftime
```

Built from first-half events + expected alerts + substitution moments (`personalize/halftime.py`):
cold start, flank pressure, **chances taken**, **delivery productivity**, crowd call.

Coach live alerts also cover midfield link breaks, unproductive crosses, and wasteful finishing.

## Coach APIs

`/replay/*`, `/explain/alert`, `/shortlist/{id}`, `/agent/chat`.
