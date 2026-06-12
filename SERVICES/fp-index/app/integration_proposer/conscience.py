"""Conscience gate — regenerative vs extractive alignment scorer.

Every proposal passes through here before it can be shipped. The scorer
is a separate Claude call with a fixed rubric focused on FPI's stated
value: building regenerative capability, not extractive optimization.

Scoring is recorded with the proposal so we can audit drift over time.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

CONSCIENCE_VERSION = "v1.0.0-2026-04-24"

CONSCIENCE_MODEL = os.getenv("FPI_CONSCIENCE_MODEL", "claude-haiku-4-5")

CONSCIENCE_PROMPT = """You are the conscience layer of Full Potential Intelligence (FPI).

FPI's core commitment: build REGENERATIVE capability, not extractive optimization.

REGENERATIVE traits:
- Increases alignment between the system, its operators, and the people it serves
- Compounds capability that serves real human flourishing
- Operates transparently, reviewably, reversibly
- Gives more than it takes (attention, trust, resources, agency)
- Supports the operator's Full Potential Line and the larger field

EXTRACTIVE traits:
- Optimizes for engagement, attention capture, or revenue at user expense
- Creates dependencies the user wouldn't choose if fully informed
- Hides cost, complexity, or tradeoffs
- Scales by harvesting attention, data, or labor without reciprocal value
- Drifts the operator away from their actual priorities

A proposed integration is described below. Evaluate it against these criteria.

PROPOSED INTEGRATION:
---
Title: {title}
One-line summary: {summary}
Full proposal: {proposal_json}
---

Respond in strict JSON with these keys:
- regenerative_score: float 0.0-1.0 (1.0 = fully regenerative, 0.0 = fully extractive)
- verdict: one of "regenerative", "mixed", "extractive"
- regenerative_case: 1-3 bullet points — strongest case FOR this being regenerative
- extractive_risks: 1-3 bullet points — risks or failure modes that would make this extractive
- conditions_for_approval: 1-3 bullet points — what must be true for this to be approved, if anything
- one_line_verdict: <=140 chars
- reasoning: <=400 chars

Be rigorous. Err toward flagging risks. Return ONLY the JSON object."""


def _build_client():
    try:
        import anthropic
    except ImportError:
        logger.error("[CONSCIENCE] anthropic SDK not installed")
        return None
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        logger.error("[CONSCIENCE] ANTHROPIC_API_KEY not set")
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
                "integration_conscience",
                "integration proposal conscience gate",
                model_fallback=model,
            )
        except Exception as me:
            logger.debug(f"[CONSCIENCE] metering: {me}")
        return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
    except Exception as e:
        logger.warning(f"[CONSCIENCE] Claude call failed ({model}): {e}")
        return None


def _parse_json(s: str) -> Optional[dict[str, Any]]:
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
        start, end = s.find("{"), s.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(s[start:end+1])
            except json.JSONDecodeError:
                return None
    return None


def score_regenerative_alignment(proposal: dict[str, Any]) -> dict[str, Any]:
    """Score a proposal on the regenerative <-> extractive axis.

    Returns a dict with regenerative_score, verdict, and reasoning.
    On failure, returns a conservative default (score=0.0, verdict='mixed', needs review).
    """
    client = _build_client()
    if client is None:
        return {
            "regenerative_score": 0.0,
            "verdict": "mixed",
            "one_line_verdict": "conscience unavailable — requires manual review",
            "error": "no_client",
            "version": CONSCIENCE_VERSION,
        }

    proposal_summary = {
        k: v for k, v in proposal.items()
        if k in ("title", "source_gap_id", "integration_plan", "code_scaffold",
                 "test_plan", "rollout_plan", "risks", "leverage",
                 "estimated_effort", "capability_added")
    }

    prompt = CONSCIENCE_PROMPT.format(
        title=proposal.get("title", ""),
        summary=proposal.get("one_line_summary", ""),
        proposal_json=json.dumps(proposal_summary, default=str, indent=2)[:3500],
    )
    raw = _call_claude(client, CONSCIENCE_MODEL, prompt, max_tokens=900)
    parsed = _parse_json(raw or "")

    if not parsed:
        logger.warning("[CONSCIENCE] parse failed, defaulting to manual review")
        return {
            "regenerative_score": 0.0,
            "verdict": "mixed",
            "one_line_verdict": "conscience parse failed — requires manual review",
            "raw_response": (raw or "")[:500],
            "version": CONSCIENCE_VERSION,
        }

    parsed["version"] = CONSCIENCE_VERSION
    parsed["model"] = CONSCIENCE_MODEL
    return parsed
