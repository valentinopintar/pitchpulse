# Studio API (step 4)

FastAPI replay control with **Server-Sent Events** for live dashboard wiring.

## Install (API extras)

```bash
pip install -e ".[api]"
# or: pip install fastapi "uvicorn[standard]"
```

## Run

```bash
export PYTHONPATH=src
# default PORT from .env or 8000; override for busy hosts:
PORT=8011 python3 -m pitchpulse.api.main
# or: uvicorn pitchpulse.api.main:app --host 0.0.0.0 --port 8011
```

Open `http://localhost:8011/docs` for Swagger.

## Typical flow

```bash
# 1) Load match
curl -s -X POST http://localhost:8011/replay/load \
  -H 'Content-Type: application/json' \
  -d '{"match_id":"syn-001"}'

# 2) Start replay (speed 0 = fast-as-possible on the SSE consumer)
curl -s -X POST http://localhost:8011/replay/start \
  -H 'Content-Type: application/json' \
  -d '{"speed":120}'

# 3) Stream (separate terminal)
curl -N 'http://localhost:8011/replay/stream?speed=120'
```

Other controls:

- `POST /replay/pause`
- `POST /replay/seek` — body `{"t_ms": 3900000}` (65')
- `POST /replay/speed` — body `{"speed": 60}`
- `GET /replay/status`
- `POST /viewer` — `{"mode":"coach|fan"}` (English only)
- `POST /explain/alert` — personalized narrative + overlay
- `GET /substitutions`, `GET /substitutions/{moment_id}` — fan rewind
- `GET /recap` — end-of-match narrative for current viewer
- `GET /shortlist/{alert_id}` — bench profiles for the gap
- `GET /fan/halftime` — living-room Match Day Summary (halftime cards)
- `GET /agent/tools`, `POST /agent/chat` — conversational tools

## SSE message types

| type | payload |
| --- | --- |
| `connected` | session status |
| `event` | one `events.jsonl` record |
| `alert` | fired coaching alert + evidence |
| `state` | `MatchState.snapshot()` rolling metrics |
| `done` | replay finished |
| `stream_end` | SSE channel closed |

Example:

```json
{"type":"alert","payload":{"alert_id":"flank_overload_right","t_ms":1018766,"match_minute":16.98,"severity":"warning","evidence":{...}}}
```
