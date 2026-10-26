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

Without these, `POST /explain/alert` and SSE alerts still return **template** copy (`source: "template"`). With them, explain can return `source: "azure_openai"`.

```bash
cp .env.example .env
# edit credentials
conda activate pitchpulse
PORT=8011 python -m pitchpulse.api.main
```

See [EXPLAIN.md](EXPLAIN.md) and [API.md](API.md).
