"""GLM-5.2 client for the council Pragmatist lens.

Supports Z-AI's OpenAI-compatible API and a local OpenAI-compatible endpoint.
No key or local URL means GLM is unavailable and callers should fall back.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_MODEL = "glm-5.2"
DEFAULT_BASE_URL = "https://api.z.ai/v1"
DEFAULT_MAX_TOKENS = 1200
_last_usage: dict[str, Any] = {}


class GLMUnavailableError(RuntimeError):
    """Raised when GLM is not configured or cannot be reached."""


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _cost_usd(tokens_in: int, tokens_out: int) -> float:
    return round((tokens_in / 1_000_000 * 1.40) + (tokens_out / 1_000_000 * 4.40), 6)


def get_last_usage() -> dict[str, Any]:
    return dict(_last_usage)


def configured_max_tokens() -> int:
    return int(os.environ.get("GLM_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))


def call_glm(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL) -> str:
    api_key = os.environ.get("GLM_API_KEY")
    local_url = os.environ.get("GLM_LOCAL_URL")
    if not api_key and not local_url:
        raise GLMUnavailableError("GLM_API_KEY or GLM_LOCAL_URL is required")

    selected_model = os.environ.get("GLM_MODEL") or model
    base_url = _normalize_base_url(local_url or os.environ.get("GLM_BASE_URL") or DEFAULT_BASE_URL)
    url = base_url + "/chat/completions"
    payload = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(os.environ.get("GLM_TEMPERATURE", "0.2")),
        "max_tokens": configured_max_tokens(),
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=float(os.environ.get("GLM_TIMEOUT_SECONDS", "120"))) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GLMUnavailableError(str(exc)) from exc

    try:
        text = str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise GLMUnavailableError("GLM response did not include choices[0].message.content") from exc

    usage = data.get("usage") or {}
    tokens_in = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    tokens_out = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    _last_usage.clear()
    _last_usage.update(
        {
            "model": selected_model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": _cost_usd(tokens_in, tokens_out),
        }
    )
    return text
