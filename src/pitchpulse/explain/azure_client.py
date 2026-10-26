"""Optional Azure OpenAI client (Microsoft Foundry / Azure OpenAI)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def azure_configured() -> bool:
    return bool(os.environ.get("AZURE_OPENAI_ENDPOINT") and os.environ.get("AZURE_OPENAI_API_KEY"))


def _endpoint_url() -> str:
    base = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    # Supports both resource.openai.azure.com and Foundry-style hosts ending with /openai
    if base.endswith("/openai"):
        return f"{base}/deployments/{deployment}/chat/completions?api-version={api_version}"
    return f"{base}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"


def chat_json(system: str, user: str, *, temperature: float = 0.3) -> dict[str, Any] | None:
    """
    Call Azure OpenAI chat completions and parse a JSON object from the assistant message.
    Returns None if not configured or on failure (caller should fall back to templates).
    """
    if not azure_configured():
        return None

    body = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        _endpoint_url(),
        data=data,
        headers={
            "Content-Type": "application/json",
            "api-key": os.environ["AZURE_OPENAI_API_KEY"],
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    try:
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None
