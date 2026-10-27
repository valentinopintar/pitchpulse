"""Minimal MCP server (JSON-RPC 2.0, Streamable HTTP with JSON responses).

Exposes the same match-intelligence tools the agents and the studio UI use. Served at
`POST /mcp` (`/api/mcp` in the single-container build) and guarded by PITCHPULSE_MCP_KEY.
"""

from __future__ import annotations

import hmac
import json
import os
from typing import Any

from pitchpulse.agent import tools

SERVER_INFO = {"name": "pitchpulse-match-intel", "version": "0.1.0"}
SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
INSTRUCTIONS = (
    "Synthetic football match intelligence. Coach tools expose tactical alerts and bench "
    "shortlists; fan tools (get_crowd_pulse, get_player_status, get_fan_halftime) are "
    "summary-level and safe for audiences."
)

# Tools that must never be handed to fan-facing agents.
COACH_ONLY = {
    "get_match_state",
    "list_alerts",
    "explain_alert",
    "propose_roles_for_alert",
    "suggest_tactical_adjustments",
    "set_viewer_profile",
}


def mcp_key() -> str:
    return os.environ.get("PITCHPULSE_MCP_KEY", "").strip()


def authorized(header_value: str | None) -> bool:
    """Bearer-token check; constant-time compare. No key configured → HTTP MCP is disabled."""
    key = mcp_key()
    if not key or not header_value:
        return False
    token = header_value.removeprefix("Bearer ").strip()
    return hmac.compare_digest(token.encode(), key.encode())


def list_tools() -> list[dict[str, Any]]:
    out = []
    for schema in tools.openai_tools([t["name"] for t in tools.TOOL_SPECS]):
        fn = schema["function"]
        out.append(
            {
                "name": fn["name"],
                "description": fn["description"],
                "inputSchema": fn["parameters"],
                "annotations": {"readOnlyHint": fn["name"] != "set_viewer_profile"},
                "_meta": {"audience": "coach" if fn["name"] in COACH_ONLY else "any"},
            }
        )
    return out


def _call_tool(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    known = {t["name"] for t in tools.TOOL_SPECS}
    if name not in known:
        raise _RpcError(-32602, f"Unknown tool: {name}")
    try:
        result = tools.dispatch(name, params.get("arguments") or {})
    except Exception as exc:  # report tool failures as MCP tool errors, not transport errors
        result = {"error": f"{type(exc).__name__}: {exc}"}
    is_error = isinstance(result, dict) and "error" in result
    out: dict[str, Any] = {
        "content": [{"type": "text", "text": json.dumps(result, default=str, ensure_ascii=False)}],
        "isError": is_error,
    }
    if isinstance(result, dict):
        out["structuredContent"] = json.loads(json.dumps(result, default=str))
    return out


class _RpcError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC message. Returns None for notifications."""
    msg_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if msg_id is None:
        return None
    try:
        if method == "initialize":
            requested = params.get("protocolVersion")
            result: dict[str, Any] = {
                "protocolVersion": requested
                if requested in SUPPORTED_VERSIONS
                else SUPPORTED_VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS,
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": list_tools()}
        elif method == "tools/call":
            result = _call_tool(params)
        else:
            raise _RpcError(-32601, f"Method not found: {method}")
    except _RpcError as exc:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": exc.code, "message": str(exc)}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}
