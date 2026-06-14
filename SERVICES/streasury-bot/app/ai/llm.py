"""app/ai/llm.py — generic Claude / OpenAI completion.

Two top-level helpers:
    - claude(system, user, ...)
    - openai_chat(system, user, ...)

Plus `complete(provider, ...)` that dispatches.

All return LLMResult(text, model, tokens_in, tokens_out).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from ..config import settings

log = logging.getLogger("streasury.ai")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


@dataclass
class LLMResult:
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0


async def claude(system: str, user: str, *, max_tokens: int = 1024, temperature: float = 0.3) -> LLMResult:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        r.raise_for_status()
        data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    usage = data.get("usage") or {}
    return LLMResult(
        text=text,
        model=f"anthropic:{settings.anthropic_model}",
        tokens_in=usage.get("input_tokens", 0),
        tokens_out=usage.get("output_tokens", 0),
    )


async def openai_chat(system: str, user: str, *, max_tokens: int = 1024, temperature: float = 0.3,
                      model: str | None = None) -> LLMResult:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    model = model or settings.openai_model
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        r.raise_for_status()
        data = r.json()
    text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    usage = data.get("usage") or {}
    return LLMResult(
        text=text,
        model=f"openai:{model}",
        tokens_in=usage.get("prompt_tokens", 0),
        tokens_out=usage.get("completion_tokens", 0),
    )


async def complete(provider: str, system: str, user: str, **kwargs) -> LLMResult:
    p = (provider or "").lower()
    if p == "claude" or p == "anthropic":
        return await claude(system, user, **kwargs)
    if p == "openai" or p == "gpt":
        return await openai_chat(system, user, **kwargs)
    raise ValueError(f"unknown provider: {provider}")
