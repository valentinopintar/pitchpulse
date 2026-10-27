"""Optional LLM client: Azure OpenAI / Microsoft Foundry (preferred), or OpenAI API for local tests."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def azure_configured() -> bool:
    return bool(os.environ.get("AZURE_OPENAI_ENDPOINT") and os.environ.get("AZURE_OPENAI_API_KEY"))


def openai_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def provider() -> str | None:
    """"azure_openai" wins over "openai" when both are set; None means templates/rules only."""
    if azure_configured():
        return "azure_openai"
    if openai_configured():
        return "openai"
    return None


def llm_configured() -> bool:
    return provider() is not None


def _azure_url() -> str:
    base = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    # Supports both resource.openai.azure.com and Foundry-style hosts ending with /openai
    if base.endswith("/openai"):
        return f"{base}/deployments/{deployment}/chat/completions?api-version={api_version}"
    return f"{base}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"


def _post(body: dict[str, Any], timeout: float) -> dict[str, Any]:
    """POST a chat-completions body to the configured provider and return the parsed payload."""
    if provider() == "azure_openai":
        url = _azure_url()
        headers = {"api-key": os.environ["AZURE_OPENAI_API_KEY"]}
    else:
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
        body = {"model": os.environ.get("OPENAI_MODEL", "gpt-4.1"), **body}
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class AzureChatError(RuntimeError):
    """Raised by chat_with_tools so agents can record the failure and recover."""


def chat_with_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    temperature: float = 0.2,
    timeout: float = 25,
) -> dict[str, Any]:
    """
    One chat-completions turn with function calling.
    Returns the assistant message (may contain `tool_calls`). Raises AzureChatError on failure.
    """
    if not llm_configured():
        raise AzureChatError("No LLM configured")

    body: dict[str, Any] = {"messages": messages, "temperature": temperature}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    try:
        return _post(body, timeout)["choices"][0]["message"]
    except urllib.error.HTTPError as exc:
        raise AzureChatError(f"HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as exc:
        raise AzureChatError(type(exc).__name__) from exc


def chat_json(system: str, user: str, *, temperature: float = 0.3) -> dict[str, Any] | None:
    """
    Call chat completions and parse a JSON object from the assistant message.
    Returns None if not configured or on failure (caller should fall back to templates).
    """
    if not llm_configured():
        return None

    body = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    try:
        payload = _post(body, 45)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    try:
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None
