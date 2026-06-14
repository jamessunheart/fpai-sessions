"""Deep reflection — the only place LLMs get called in the field sensor.

Only events that pass the significance gate reach this layer.
The reflection answers: given our current capabilities, what does
this change, and what gap does it close or create?

Uses Claude Haiku for cheap triage, Sonnet only for the deepest cases.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from .registry import append_gap, capabilities_snapshot

logger = logging.getLogger(__name__)

HAIKU_MODEL = os.getenv("FPI_FIELD_HAIKU", "claude-haiku-4-5")
SONNET_MODEL = os.getenv("FPI_FIELD_SONNET", "claude-sonnet-4-5")
DEEP_THRESHOLD = 0.90

REFLECTION_PROMPT = """You are the self-awareness organ of Full Potential Intelligence (FPI), a system designed to self-assemble new capabilities from the AI field.

Current FPI capabilities:
---
{capabilities}
---

A new event has been detected in the field:
- Source: {source}
- Type: {event_type}
- Title: {title}
- Author: {author}
- URL: {url}
- Significance score (local heuristic): {score:.2f}
- Raw data: {raw}

Reflect briefly and answer in strict JSON with these keys:
- relevance: 0.0-1.0 (is this actually useful to FPI, not just hyped?)
- gap_closed: short string — what existing FPI gap does this close, if any? Empty string if none.
- gap_created: short string — what new gap does this expose in FPI's current capabilities? Empty string if none.
- integration_effort: one of "trivial", "moderate", "significant", "major"
- leverage: 0.0-1.0 (how much would integrating this compound FPI's other capabilities?)
- recommended_action: one of "integrate_now", "watch", "ignore", "research_further"
- one_line_summary: <=140 chars
- reasoning: <=400 chars, why you scored it this way

Return ONLY the JSON object, no prose, no markdown fencing."""


def _build_client():
    try:
        import anthropic
    except ImportError:
        logger.error("[FIELD] anthropic SDK not installed")
        return None
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        logger.error("[FIELD] ANTHROPIC_API_KEY not set")
        return None
    return anthropic.Anthropic(api_key=key)


def _call_claude(client, model: str, prompt: str, max_tokens: int = 800) -> Optional[str]:
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            from ..metering import meter_anthropic_message_response
            meter_anthropic_message_response(
                resp,
                "field_sensor_reflection",
                f"field_sensor reflect model={model}",
                model_fallback=model,
            )
        except Exception as me:
            logger.debug(f"[FIELD] metering: {me}")
        parts = []
        for block in resp.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts).strip()
    except Exception as e:
        logger.warning(f"[FIELD] Claude call failed ({model}): {e}")
        return None


def _parse_json_strict(s: str) -> Optional[dict[str, Any]]:
    if not s:
        return None
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
    if s.endswith("```"):
        s = s.rsplit("```", 1)[0]
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        start = s.find("{")
        end = s.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(s[start:end+1])
            except json.JSONDecodeError:
                return None
    return None


def reflect_on_event(event: dict[str, Any], significance: float) -> Optional[dict[str, Any]]:
    """Run deep reflection on an event that passed the gate.

    Writes result to gap_registry.jsonl and returns the reflection dict.
    Returns None if reflection failed.
    """
    client = _build_client()
    if client is None:
        return None

    raw = event.get("raw") or event.get("raw_json") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}

    prompt = REFLECTION_PROMPT.format(
        capabilities=capabilities_snapshot(),
        source=event.get("source", ""),
        event_type=event.get("event_type", ""),
        title=event.get("title", ""),
        author=event.get("author", ""),
        url=event.get("url", ""),
        score=significance,
        raw=json.dumps(raw, default=str)[:1500],
    )

    model = SONNET_MODEL if significance >= DEEP_THRESHOLD else HAIKU_MODEL
    raw_text = _call_claude(client, model, prompt, max_tokens=800)
    parsed = _parse_json_strict(raw_text or "")

    if not parsed:
        logger.warning(f"[FIELD] Reflection failed to parse for {event.get('title', '?')[:60]}")
        append_gap({
            "event_id": event.get("event_id"),
            "event_title": event.get("title", ""),
            "event_url": event.get("url", ""),
            "source": event.get("source", ""),
            "significance": significance,
            "model_used": model,
            "reflection_error": "parse_failed",
            "raw_text": (raw_text or "")[:500],
        })
        return None

    entry = {
        "event_id": event.get("event_id"),
        "event_title": event.get("title", ""),
        "event_url": event.get("url", ""),
        "event_type": event.get("event_type", ""),
        "source": event.get("source", ""),
        "author": event.get("author", ""),
        "significance": significance,
        "model_used": model,
        **parsed,
        "gap_summary": parsed.get("one_line_summary") or parsed.get("gap_created") or parsed.get("gap_closed", ""),
    }
    append_gap(entry)
    return entry
