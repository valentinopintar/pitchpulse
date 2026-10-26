# Dataset generation

PitchPulse uses **100% synthetic** match data. Event types and rolling statistics use **PitchPulse naming** (not third-party provider schemas).

## Quick run

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

export PYTHONPATH=src   # omit after pip install -e .
python3 -m pitchpulse.data.generate_match --match syn-001
python3 -m pitchpulse.data.validate_events --match syn-001
```

Outputs land in `data/matches/syn-001/`:

| File | Purpose |
| --- | --- |
| `events.jsonl` | Stream of match events (ingest source) |
| `meta.json` | Teams, formations, score arc |
| `lineups.json` | Starters + bench |
| `expected_alerts.json` | Rule targets for demo (Coach / Analyst) |
| `substitution_moments.json` | Fan rewind windows + observable before/after metrics |
| `minute_snapshots.json` | Per-minute zone and team rollups for dashboards |
| `player_match_rollups.json` | Per-player PitchPulse KPIs for the match |

Authoring input: `data/storybeats/syn-001.yaml`.

## Coach vs fan data

- **Coach / Analyst** consume live `expected_alerts` + rolling `minute_snapshots` and event-derived KPIs. Alerts fire while leaks develop.
- **Fan** consume `substitution_moments`: a time window around each sub showing **observable** metric shifts (flank entries, duel success, turnover rate). No private coach-to-player instructions — only what the broadcast could infer from events.

## PitchPulse metric glossary (event + rollup)

| Name | Meaning |
| --- | --- |
| `pass_obstruction_index` | Pass difficulty (distance, pressure, line-breaking) |
| `ball_velocity_mps` | Ball speed on pass/shot/carry |
| `carrier_pressure_load` | Pressure on ball carrier (0–1) |
| `lane_threat_score` | Attacking lane value proxy |
| `duel_contact_quality` | Duel outcome strength |
| `zone_tension_index` | Short-window pressure in a pitch zone |
| `flank_strike_load` | Cross + final-third entries on a flank |
| `possession_chaos_index` | Turnovers + failed duels in midfield |
| `defensive_contact_rate` | Successful tackles/aerials vs entries against |

See `src/pitchpulse/schema/events.py` for the canonical event contract.
