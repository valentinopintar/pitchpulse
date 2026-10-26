# Interpret layer (step 3)

Turns `events.jsonl` into rolling **match state** and deterministic **coaching alerts**.

## Commands

```bash
export PYTHONPATH=src   # omit after pip install -e .

python3 -m pitchpulse.interpret.assert_demo_alerts --match syn-001
python3 -m pitchpulse.ingest.replay --match syn-001          # instant
python3 -m pitchpulse.ingest.replay --match syn-001 --speed 60   # ~60x clock
```

After dataset generation, `./scripts/generate_dataset.sh` also runs assert.

## Modules

| Module | Role |
| --- | --- |
| `interpret/state.py` | `MatchState` — event buffer, rolling snapshot |
| `interpret/window.py` | PitchPulse metrics over a time slice |
| `interpret/alerts.py` | Threshold rules → `FiredAlert` |
| `interpret/engine.py` | Full replay + cooldown per alert id |
| `interpret/assert_demo_alerts.py` | Match fires to `expected_alerts.json` |

## Alert rules (defaults)

- **flank_overload_right** — 6 min window: ≥6 home crosses + away LB duel loss rate ≥0.55  
- **chaos_press_mid** — ≥10 midfield turnovers + chaos index ≥0.8  
- **shot_speed_spike** — ≥2 home shots, max strike velocity ≥25 m/s  
- **low_defensive_contacts** — ≥4 final-third entries vs away, defensive contact rate ≤0.45  

Next: FastAPI SSE exposing the same engine (step 4).
