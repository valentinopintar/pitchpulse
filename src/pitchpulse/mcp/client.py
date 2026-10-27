"""MCP client the agents use for every tool call.

With PITCHPULSE_MCP_URL set, calls go over HTTP to the MCP server with the PITCHPULSE_MCP_KEY
bearer token. Otherwise (or if the HTTP server is unreachable) the same JSON-RPC messages are
handled in-process, so the demo never depends on networking.
"""

from __future__ import annotations

import itertools
import json
import os
import urllib.error
import urllib.request
from typing import Any

from pitchpulse.mcp import server

_ids = itertools.count(1)


class MCPClient:
    def __init__(self) -> None:
        self.url = os.environ.get("PITCHPULSE_MCP_URL", "").strip()
        if self.url == "auto":  # single container (Render, ACA): talk to our own /api/mcp
            self.url = f"http://127.0.0.1:{os.environ.get('PORT', '7860')}/api/mcp"
        self.key = server.mcp_key()
        self.transport = "mcp-http" if self.url and self.key else "mcp-inproc"
        self._initialized = False
        self.fallback_reason: str | None = None

    def _send_http(self, message: dict[str, Any]) -> dict[str, Any] | None:
        req = urllib.request.Request(
            self.url,
            data=json.dumps(message).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {self.key}",
                "MCP-Protocol-Version": server.SUPPORTED_VERSIONS[0],
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
        return json.loads(body) if body else None

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        message = {"jsonrpc": "2.0", "id": next(_ids), "method": method, "params": params or {}}
        reply: dict[str, Any] | None = None
        if self.transport == "mcp-http":
            try:
                if not self._initialized:
                    self._send_http(
                        {
                            "jsonrpc": "2.0",
                            "id": next(_ids),
                            "method": "initialize",
                            "params": {
                                "protocolVersion": server.SUPPORTED_VERSIONS[0],
                                "capabilities": {},
                                "clientInfo": {"name": "pitchpulse-agents", "version": "0.1.0"},
                            },
                        }
                    )
                    self._initialized = True
                reply = self._send_http(message)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                reason = (
                    f"HTTP {exc.code}"
                    if isinstance(exc, urllib.error.HTTPError)
                    else type(exc).__name__
                )
                self.fallback_reason = f"MCP HTTP failed ({reason}); using in-process MCP"
                self.transport = "mcp-inproc"
        if reply is None:
            reply = server.handle(message)
        if not reply or "error" in reply:
            raise RuntimeError((reply or {}).get("error", {}).get("message", "MCP error"))
        return reply["result"]

    def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        result = self._rpc("tools/call", {"name": name, "arguments": args})
        if "structuredContent" in result:
            return result["structuredContent"]
        return json.loads(result["content"][0]["text"])

    def list_tools(self) -> list[dict[str, Any]]:
        return self._rpc("tools/list")["tools"]
