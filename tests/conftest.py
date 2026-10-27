"""Keep tests independent of a developer's local .env (LLM keys, a running MCP server)."""

from __future__ import annotations

import pytest

_LOCAL_ENV = (
    "PITCHPULSE_MCP_URL",
    "PITCHPULSE_MCP_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
)


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    import pitchpulse.api.main  # noqa: F401  (loads .env once, so we can strip it below)

    for var in _LOCAL_ENV:
        monkeypatch.delenv(var, raising=False)
