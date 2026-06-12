"""curator/llm.py — thin LLM client for the curator.

Provider preference (configurable via CURATOR_LLM_PROVIDER):
    1. ``openai``    — OPENAI_API_KEY  (default if set)
    2. ``anthropic`` — ANTHROPIC_API_KEY
    3. ``ollama``    — local fallback

Set ``CURATOR_LLM_PROVIDER=anthropic`` to force Claude when both keys exist.

All calls return a dict with `text` plus bookkeeping fields so we can record
the exact model + prompt hash on every proposal (auditability).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger("curator.llm")


ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("CURATOR_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("CURATOR_OPENAI_MODEL", "gpt-4o-mini")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("CURATOR_OLLAMA_MODEL", "llama3.1:8b")

PROVIDER = (os.environ.get("CURATOR_LLM_PROVIDER") or "").lower().strip()


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_sha1: str
    tokens_in: int
    tokens_out: int

    def parse_json(self) -> Any:
        """Extract the first JSON object in the response.
        Models sometimes wrap JSON in prose or fenced blocks; this is lenient.
        """
        t = self.text.strip()
        if t.startswith("```"):
            t = t.split("```", 2)[1]
            if t.startswith("json"):
                t = t[4:]
            t = t.rsplit("```", 1)[0]
        start = t.find("{")
        end = t.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"no JSON object in response: {self.text[:200]}")
        return json.loads(t[start : end + 1])


async def complete(
    system: str,
    user: str,
    *,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    force_json: bool = True,
) -> LLMResult:
    """Single-shot completion. Returns LLMResult(text, model, …)."""
    prompt_hash = hashlib.sha1((system + "\n" + user).encode()).hexdigest()
    if force_json:
        user = user + "\n\nReturn ONLY a single JSON object. No prose."

    chosen = PROVIDER
    if not chosen:
        if OPENAI_KEY:
            chosen = "openai"
        elif ANTHROPIC_KEY:
            chosen = "anthropic"
        else:
            chosen = "ollama"

    if chosen == "openai" and OPENAI_KEY:
        return await _openai(system, user, max_tokens, temperature, prompt_hash)
    if chosen == "anthropic" and ANTHROPIC_KEY:
        return await _anthropic(system, user, max_tokens, temperature, prompt_hash)
    return await _ollama(system, user, max_tokens, temperature, prompt_hash)


async def _openai(system: str, user: str, max_tokens: int, temperature: float, prompt_hash: str) -> LLMResult:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_KEY}",
                "content-type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
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
    choice = (data.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content", "") or ""
    usage = data.get("usage") or {}
    return LLMResult(
        text=text,
        model=f"openai:{OPENAI_MODEL}",
        prompt_sha1=prompt_hash,
        tokens_in=usage.get("prompt_tokens", 0),
        tokens_out=usage.get("completion_tokens", 0),
    )


async def _anthropic(system: str, user: str, max_tokens: int, temperature: float, prompt_hash: str) -> LLMResult:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        r.raise_for_status()
        data = r.json()
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    usage = data.get("usage") or {}
    return LLMResult(
        text=text,
        model=ANTHROPIC_MODEL,
        prompt_sha1=prompt_hash,
        tokens_in=usage.get("input_tokens", 0),
        tokens_out=usage.get("output_tokens", 0),
    )


async def _ollama(system: str, user: str, max_tokens: int, temperature: float, prompt_hash: str) -> LLMResult:
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            f"{OLLAMA_BASE}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        r.raise_for_status()
        data = r.json()
    text = (data.get("message") or {}).get("content", "")
    return LLMResult(
        text=text,
        model=f"ollama:{OLLAMA_MODEL}",
        prompt_sha1=prompt_hash,
        tokens_in=data.get("prompt_eval_count", 0),
        tokens_out=data.get("eval_count", 0),
    )
