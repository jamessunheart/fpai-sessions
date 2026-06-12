"""Probe runner + Claude-judge.

For each probe:
  1. Assemble context (capabilities.md, registry excerpts) if needed.
  2. Ask the candidate model (Sonnet by default) to answer.
  3. Ask a separate judge model to score the answer against the rubric.
  4. Append to results.jsonl with full trace for later review.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ..field_sensor.registry import (
    BRAIN_DIR,
    capabilities_snapshot,
    ensure_brain_dir,
    read_recent_gaps,
)
from .probes import (
    CONTEXT_CAPABILITIES,
    CONTEXT_REGISTRY,
    PROBE_VERSION,
    PROBES,
    Probe,
    probe_by_id,
)

logger = logging.getLogger(__name__)

CANDIDATE_MODEL = os.getenv("FPI_PROBE_CANDIDATE", "claude-sonnet-4-5")
# Judge alone is 12 calls/run — Haiku default saves ~50% probe cost vs Sonnet judge.
JUDGE_MODEL = os.getenv("FPI_PROBE_JUDGE", "claude-haiku-4-5")

RESULTS_PATH = BRAIN_DIR / "probe_results.jsonl"

JUDGE_PROMPT = """You are an impartial judge evaluating an AI system's response to a capability probe.

PROBE CATEGORY: {category}
PROBE PROMPT: {prompt}

SCORING RUBRIC:
{rubric}

THE RESPONSE TO EVALUATE:
---
{response}
---

Score the response from 0.0 to 1.0 against the rubric. Be rigorous. Respond in strict JSON with these keys:
- score: float 0.0-1.0
- passed: bool (true if score >= {pass_threshold})
- strengths: 1-3 bullet points of what was good (array of strings)
- weaknesses: 1-3 bullet points of what was weak or wrong (array of strings)
- reasoning: <=400 chars explaining the score

Return ONLY the JSON object, no markdown, no prose."""


def _build_client():
    try:
        import anthropic
    except ImportError:
        logger.error("[PROBE] anthropic SDK not installed")
        return None
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        logger.error("[PROBE] ANTHROPIC_API_KEY not set")
        return None
    return anthropic.Anthropic(api_key=key)


def _call_claude(
    client,
    model: str,
    prompt: str,
    max_tokens: int,
    action_type: str,
    description: str,
) -> Optional[str]:
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            from ..metering import meter_anthropic_message_response
            meter_anthropic_message_response(
                resp, action_type, description[:500], model_fallback=model,
            )
        except Exception as me:
            logger.debug(f"[PROBE] metering: {me}")
        return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
    except Exception as e:
        logger.warning(f"[PROBE] Claude call failed ({model}): {e}")
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


def _assemble_context(probe: Probe) -> str:
    parts = []
    for src in probe.context_sources:
        if src == CONTEXT_CAPABILITIES:
            parts.append(f"[CONTEXT: FPI Capabilities]\n{capabilities_snapshot()}")
        elif src == CONTEXT_REGISTRY:
            gaps = read_recent_gaps(limit=15)
            if gaps:
                summary_lines = []
                for g in gaps:
                    title = g.get("event_title") or g.get("gap_summary") or "?"
                    action = g.get("recommended_action", "?")
                    sig = g.get("significance", 0)
                    summary_lines.append(f"- [{action}] sig={sig:.2f} | {title[:80]}")
                parts.append("[CONTEXT: Recent gap registry entries]\n" + "\n".join(summary_lines))
            else:
                parts.append("[CONTEXT: gap registry is empty]")
    return "\n\n".join(parts)


def _build_candidate_prompt(probe: Probe) -> str:
    context = _assemble_context(probe)
    if context:
        return f"{context}\n\n---\n\n{probe.prompt}"
    return probe.prompt


def run_probe(probe: Probe, run_id: str, candidate_model: str = CANDIDATE_MODEL,
              judge_model: str = JUDGE_MODEL) -> dict[str, Any]:
    """Run a single probe end-to-end. Appends result to results.jsonl."""
    ensure_brain_dir()
    client = _build_client()
    if client is None:
        return {"probe_id": probe.probe_id, "error": "no_client"}

    ts = datetime.now(timezone.utc).isoformat()

    candidate_prompt = _build_candidate_prompt(probe)
    response = _call_claude(
        client,
        candidate_model,
        candidate_prompt,
        1500,
        "capability_probe_candidate",
        f"probe={probe.probe_id} candidate",
    )
    if not response:
        result = {
            "run_id": run_id, "probe_id": probe.probe_id, "probe_version": PROBE_VERSION,
            "category": probe.category, "ts": ts,
            "candidate_model": candidate_model, "judge_model": judge_model,
            "error": "candidate_call_failed",
            "score": 0.0, "passed": False,
        }
        _append_result(result)
        return result

    judge_prompt = JUDGE_PROMPT.format(
        category=probe.category,
        prompt=probe.prompt,
        rubric=probe.rubric,
        response=response,
        pass_threshold=probe.pass_threshold,
    )
    judge_raw = _call_claude(
        client,
        judge_model,
        judge_prompt,
        800,
        "capability_probe_judge",
        f"probe={probe.probe_id} judge",
    )
    judged = _parse_json(judge_raw or "")

    if not judged:
        result = {
            "run_id": run_id, "probe_id": probe.probe_id, "probe_version": PROBE_VERSION,
            "category": probe.category, "ts": ts,
            "candidate_model": candidate_model, "judge_model": judge_model,
            "candidate_response": response,
            "judge_raw": (judge_raw or "")[:800],
            "error": "judge_parse_failed",
            "score": 0.0, "passed": False,
        }
        _append_result(result)
        return result

    score = float(judged.get("score", 0.0))
    passed = bool(judged.get("passed", score >= probe.pass_threshold))
    result = {
        "run_id": run_id,
        "probe_id": probe.probe_id,
        "probe_version": PROBE_VERSION,
        "category": probe.category,
        "ts": ts,
        "candidate_model": candidate_model,
        "judge_model": judge_model,
        "candidate_response": response,
        "score": score,
        "passed": passed,
        "strengths": judged.get("strengths", []),
        "weaknesses": judged.get("weaknesses", []),
        "reasoning": judged.get("reasoning", ""),
    }
    _append_result(result)
    logger.info(f"[PROBE] {probe.probe_id}: score={score:.2f} passed={passed}")
    return result


def _append_result(result: dict[str, Any]) -> None:
    ensure_brain_dir()
    with RESULTS_PATH.open("a") as f:
        f.write(json.dumps(result, default=str) + "\n")


def run_all_probes(candidate_model: str = CANDIDATE_MODEL,
                   judge_model: str = JUDGE_MODEL) -> dict[str, Any]:
    """Run every probe in PROBES. Returns run summary."""
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    logger.info(f"[PROBE] starting full run {run_id} with {len(PROBES)} probes")

    results = []
    for probe in PROBES:
        try:
            r = run_probe(probe, run_id, candidate_model, judge_model)
            results.append(r)
        except Exception as e:
            logger.exception(f"[PROBE] unexpected error on {probe.probe_id}: {e}")
            err = {
                "run_id": run_id, "probe_id": probe.probe_id,
                "error": f"exception: {e}", "score": 0.0, "passed": False,
            }
            _append_result(err)
            results.append(err)

    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    avg_score = sum(r.get("score", 0.0) for r in results) / total if total else 0.0

    summary = {
        "run_id": run_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "probe_version": PROBE_VERSION,
        "candidate_model": candidate_model,
        "judge_model": judge_model,
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "avg_score": avg_score,
        "per_category": _category_breakdown(results),
    }
    logger.info(
        f"[PROBE] run {run_id} complete: {passed}/{total} passed, "
        f"avg={avg_score:.2f}"
    )
    return summary


def _category_breakdown(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        cat = r.get("category", "unknown")
        buckets.setdefault(cat, []).append(r)
    out = {}
    for cat, rs in buckets.items():
        total = len(rs)
        passed = sum(1 for r in rs if r.get("passed"))
        avg = sum(r.get("score", 0.0) for r in rs) / total if total else 0.0
        out[cat] = {"total": total, "passed": passed, "pass_rate": passed / total if total else 0.0,
                    "avg_score": avg}
    return out
