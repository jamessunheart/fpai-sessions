"""Significance gate — fast, local, no LLM calls.

99% of sensed events should fail this gate. The gate IS the attention
filter. Without it we recreate the scanner-noise problem.

The gate is versioned and editable. When the retrospective review runs
(monthly), it proposes new heuristics based on which events led to
useful gaps vs which were noise.
"""
from __future__ import annotations

import re
from typing import Any

GATE_VERSION = "v1.0.0-2026-04-24"

FRONTIER_LABS = {
    "meta-llama", "meta", "mistralai", "mistral",
    "google", "google-deepmind", "deepmind",
    "qwen", "qwenlm", "deepseek-ai", "deepseek",
    "microsoft", "nvidia", "apple", "01-ai",
    "anthropic", "anthropics", "openai", "openai-community",
    "xai-org", "xai", "stabilityai", "black-forest-labs",
    "huggingface",
}

CAPABILITY_KEYWORDS = {
    "multimodal", "vision", "reasoning", "agent", "tool-use",
    "function-calling", "long-context", "mixture-of-experts", "moe",
    "instruction-tuned", "reward-model", "rlhf", "dpo",
    "code-generation", "sota", "state-of-the-art", "benchmark",
    "text-to-image", "text-to-video", "text-to-speech", "speech-to-text",
    "embedding", "retrieval", "rag", "self-play", "self-improve",
    "planning", "memory", "context-compression",
}

BENCHMARK_KEYWORDS = {
    "mmlu", "hellaswag", "humaneval", "mbpp", "swe-bench",
    "arc-agi", "gpqa", "math", "gsm8k", "bigbench",
    "arena", "lmsys", "chatbot-arena", "livebench",
}

AGENT_FRAMEWORK_KEYWORDS = {
    "agent framework", "multi-agent", "autogpt", "crewai",
    "langgraph", "autogen", "agentic",
}

NEGATIVE_SIGNALS = {
    "draft", "wip", "test-", "debug-", "fork of",
    "experimental-scratch", "placeholder",
}


def _contains_any(text: str, keywords: set[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def significance_score(event: dict[str, Any]) -> float:
    """Return 0.0–1.0 score. Higher = more worth reflecting on.

    event is either a SensedEvent-as-dict or a row from events table.
    """
    title = str(event.get("title", "")).lower()
    author = str(event.get("author", "")).lower()
    source = str(event.get("source", "")).lower()
    event_type = str(event.get("event_type", ""))

    raw = event.get("raw") or event.get("raw_json") or {}
    if isinstance(raw, str):
        import json as _json
        try:
            raw = _json.loads(raw)
        except Exception:
            raw = {}

    summary = str(raw.get("summary", "")).lower()
    body = str(raw.get("body", "")).lower()
    tags = raw.get("tags", []) or []
    if isinstance(tags, list):
        tag_text = " ".join(str(t).lower() for t in tags)
    else:
        tag_text = ""

    combined = f"{title} {summary} {body} {tag_text}"

    score = 0.0

    if any(lab in author for lab in FRONTIER_LABS):
        score += 0.35
    if any(lab in title for lab in FRONTIER_LABS):
        score += 0.15

    if _contains_any(combined, CAPABILITY_KEYWORDS):
        score += 0.25
    if _contains_any(combined, BENCHMARK_KEYWORDS):
        score += 0.20
    if _contains_any(combined, AGENT_FRAMEWORK_KEYWORDS):
        score += 0.20

    if event_type == "model_release":
        likes = raw.get("likes") or 0
        downloads = raw.get("downloads") or 0
        try:
            if int(likes) >= 100:
                score += 0.15
            if int(downloads) >= 10_000:
                score += 0.15
        except (TypeError, ValueError):
            pass

    if event_type == "ReleaseEvent":
        score += 0.15

    if event_type == "paper":
        if re.search(r"\b(gpt-?[4-9]|claude-?[3-9]|llama-?[3-9]|gemini|o[1-9]-|grok)", combined):
            score += 0.25
        if len(summary) > 200:
            score += 0.05

    if source == "openrouter" and event_type == "model_available":
        pricing = raw.get("pricing") or {}
        try:
            prompt_price = float(pricing.get("prompt", 1))
            if prompt_price < 0.000001:
                score += 0.10
        except (TypeError, ValueError):
            pass

    if _contains_any(combined, NEGATIVE_SIGNALS):
        score -= 0.30

    return max(0.0, min(1.0, score))


SIGNIFICANCE_THRESHOLD = 0.70


def passes_gate(event: dict[str, Any], threshold: float = SIGNIFICANCE_THRESHOLD) -> tuple[bool, float]:
    s = significance_score(event)
    return (s >= threshold, s)
