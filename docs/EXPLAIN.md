# Explain + personalize (step 5)

Same match intelligence, dual audience modes (Coach / Fan). English only.

## Modes

| Mode | When | Content |
| --- | --- | --- |
| **Coach** | Live while leak develops | Actionable cues + gap to fill |
| **Analyst** | Live | Metric evidence / rolling window |
| **Fan** | Especially around substitutions | Observable before/after — no private coach speech |

## API

```bash
# set audience
curl -s -X POST http://localhost:8011/viewer \
  -H 'Content-Type: application/json' \
  -d '{"mode":"fan"}'

# explain an alert (templates if no Azure; LLM if .env configured)
curl -s -X POST http://localhost:8011/explain/alert \
  -H 'Content-Type: application/json' \
  -d '{"alert_id":"flank_overload_right","match_minute":17,"t_ms":1018766,"use_llm":true}'

# fan substitution rewind
curl -s http://localhost:8011/substitutions
curl -s http://localhost:8011/substitutions/sub_flank_fix

# end-of-match recap for current viewer
curl -s http://localhost:8011/recap
```

SSE `alert` messages include `personalized` + `overlay` (template, fast). Use `POST /explain/alert` with `use_llm:true` for Azure enrichment.

## Modules

- `explain/templates.py` — deterministic English copy
- `explain/azure_client.py` — optional Azure OpenAI chat JSON
- `explain/service.py` — cache + viewer slice
- `personalize/viewer.py` — mode / language / favorite player
- `render/overlay.py` — timed graphic packet
