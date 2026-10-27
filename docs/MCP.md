# MCP server

PitchPulse exposes its match-intelligence tools over the **Model Context Protocol** (JSON-RPC 2.0,
Streamable HTTP with JSON responses, protocol `2025-06-18`). The same server is used by:

1. **The PitchPulse agent team.** Every tool call by the Orchestrator's specialists goes through
   the MCP client ([client.py](../src/pitchpulse/mcp/client.py)). The trace shows `via mcp-http`
   or `via mcp-inproc` on each tool step.
2. **External MCP clients** such as GitHub Copilot agent mode in VS Code or Claude Desktop, which can query the live match
   directly.

| | |
| --- | --- |
| Endpoint | `POST /api/mcp` (single container) · `POST /mcp` (API-only dev server) |
| Auth | `Authorization: Bearer $PITCHPULSE_MCP_KEY` (`X-API-Key` also accepted) |
| Methods | `initialize`, `ping`, `tools/list`, `tools/call` (notifications → `202`) |
| Tools | coach: `get_match_state`, `list_alerts`, `explain_alert`, `propose_roles_for_alert`, `suggest_tactical_adjustments`, `set_viewer_profile` · any: `get_match_clock`, `get_overlay_packet`, `generate_match_recap`, `get_fan_halftime`, `get_crowd_pulse`, `get_player_status`, `get_fan_verdicts` |

## Security

- **No key, no HTTP.** Without `PITCHPULSE_MCP_KEY` the endpoint returns `503`; agents keep working
  through the in-process transport (same JSON-RPC handler, no network).
- **Constant-time key check**, `401` with `WWW-Authenticate` on a missing or wrong token.
- **Audience scoping.** Each tool is tagged `_meta.audience`. The fan team can't call coach-only
  tools even if a model asks for them (the blackboard rejects the call before it reaches MCP).
- **Resilience.** If `PITCHPULSE_MCP_URL` is unreachable or rejects the key, the client switches
  to in-process MCP and the trace records a `recovered` step.

Keep the key in `.env` locally (git-ignored) and in your host's environment settings (Render →
Environment, Azure Container Apps → Secrets). Don't commit it.

## Agents over HTTP

```bash
PITCHPULSE_MCP_KEY=<random>                         # python -c "import secrets;print(secrets.token_urlsafe(32))"
PITCHPULSE_MCP_URL=auto                             # container / Render: http://127.0.0.1:$PORT/api/mcp
```

## Try it with curl

```bash
curl -s http://localhost:7860/api/mcp \
  -H "Authorization: Bearer $PITCHPULSE_MCP_KEY" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_crowd_pulse","arguments":{}}}'
```

## VS Code (GitHub Copilot agent mode)

`.vscode/mcp.json`. The key is prompted for once and stored by VS Code, never written to the repo:

```json
{
  "inputs": [
    { "type": "promptString", "id": "pitchpulse-key", "description": "PITCHPULSE_MCP_KEY", "password": true }
  ],
  "servers": {
    "pitchpulse": {
      "type": "http",
      "url": "http://localhost:7860/api/mcp",
      "headers": { "Authorization": "Bearer ${input:pitchpulse-key}" }
    }
  }
}
```
