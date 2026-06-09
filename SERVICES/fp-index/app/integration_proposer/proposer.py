"""Integration proposer — takes gaps, produces proposals.

Ranking: pick gaps the reflection layer already scored highly for
leverage and marked as "integrate_now" or "research_further". Skip
"watch" and "ignore". Dedupe against existing proposals by source_gap_id.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ..field_sensor.registry import capabilities_snapshot, read_recent_gaps
from .conscience import score_regenerative_alignment
from .registry import append_proposal, read_proposals

logger = logging.getLogger(__name__)

PROPOSER_VERSION = "v1.0.0-2026-04-24"
PROPOSER_MODEL = os.getenv("FPI_PROPOSER_MODEL", "claude-haiku-4-5")

ELIGIBLE_ACTIONS = {"integrate_now", "research_further"}

PROPOSAL_PROMPT = """You are the Integration Proposer for Full Potential Intelligence (FPI), a self-assembling AI.

FPI's current capabilities:
---
{capabilities}
---

A gap has been flagged by the reflection layer:
---
Gap title: {gap_title}
Event URL: {gap_url}
Event type: {gap_event_type}
Source: {gap_source}
Significance score: {gap_significance}
Leverage (as rated by reflection): {gap_leverage}
Gap closed by this event: {gap_closed}
Gap created by this event: {gap_created}
Original reasoning: {gap_reasoning}
Recommended action: {gap_action}
---

Your job: produce a CONCRETE, ACTIONABLE integration proposal that a human reviewer can approve and a system (or careful human) can execute.

Produce a proposal in strict JSON with these keys:
- title: <=80 chars — what this integration does
- one_line_summary: <=140 chars — why it matters for FPI
- capability_added: <=140 chars — specific capability this unlocks
- leverage: float 0.0-1.0 — how much this compounds FPI's other capabilities
- estimated_effort: one of "trivial" (< 1 hour), "small" (1-4 hours), "medium" (4-16 hours), "large" (> 16 hours)
- integration_plan: array of 3-7 concrete steps (strings), each specific enough to execute
- code_scaffold: string — minimal Python code stub that would begin the integration (single file, ~30-80 lines). Include imports, function signatures, and TODO markers for the hard parts. Must be valid Python.
- test_plan: array of 3-5 testable assertions the integration must satisfy before ship
- rollout_plan: array of 2-4 steps for safe rollout (canary, monitoring, rollback trigger)
- risks: array of 2-4 specific risks — failure modes, attack surfaces, cost spikes, drift possibilities
- success_metrics: array of 2-3 measurable outcomes that prove the integration worked
- affected_files: array of file paths (existing or new) this integration would touch
- requires_human: array of decisions or approvals that MUST be human-made (e.g. API key provisioning)
- pulse_hypothesis: object with keys:
    - target_metric: string — a dotted path into the pulse snapshot that this integration should move.
      Valid paths include (but are not limited to):
        * "zen_village.passes_last_7d" — new Zen Pass signups this week
        * "zen_village.passes_paid_total" — cumulative paid passes
        * "zen_village.bookings_confirmed" — confirmed stays at Zen Village
        * "zen_village.zen_pass_revenue_last_7d" — revenue from passes this week
        * "zen_village.bookings_revenue_total" — cumulative booking revenue
        * "reach.email_subscribers_total" — FPI audience size
        * "reach.email_subscribers_last_7d" — new subscribers this week
        * "reach.unique_visitors_last_7d_approx.fullpotential.ai" — site traffic
        * "reach.unique_visitors_last_7d_approx.zenvillagecr.com"
        * "system.probe_pass_rate_latest" — FPI self-capability pass rate
        * "system.probe_avg_score_latest" — FPI capability avg score
        * "system.proposals.approved" — approved-proposal throughput
    - expected_delta: float — how much the metric should move in the measurement window.
      Positive = increase, negative = decrease. Be honest and conservative.
    - measurement_window_days: int — 7, 14, 30, or 90.
    - rationale: <= 200 chars — the causal story from this integration to the metric delta.
      If you cannot tell a credible causal story, the proposal is probably not worth shipping.

Be HONEST. If the gap doesn't actually warrant integration, say so with a minimal proposal marked estimated_effort="trivial" and a one_line_summary explaining why integration should be deferred.

Return ONLY the JSON object, no prose, no markdown fencing."""


def _build_client():
    try:
        import anthropic
    except ImportError:
        logger.error("[PROPOSER] anthropic SDK not installed")
        return None
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        logger.error("[PROPOSER] ANTHROPIC_API_KEY not set")
        return None
    return anthropic.Anthropic(api_key=key)


def _call_claude(client, model: str, prompt: str, max_tokens: int = 3000) -> Optional[str]:
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
                "integration_proposer",
                "integration proposal generation",
                model_fallback=model,
            )
        except Exception as me:
            logger.debug(f"[PROPOSER] metering: {me}")
        return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
    except Exception as e:
        logger.warning(f"[PROPOSER] Claude call failed ({model}): {e}")
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


def _gap_already_proposed(gap_id: str) -> bool:
    if not gap_id:
        return False
    status = read_proposals()
    for p in status.values():
        if p.get("gap_id") == gap_id and p.get("status") not in ("rejected", "archived"):
            return True
    return False


def rank_candidate_gaps(limit: int = 10) -> list[dict[str, Any]]:
    """Return gaps eligible for proposal, ranked by leverage × significance.

    Filters:
      - action in ELIGIBLE_ACTIONS (integrate_now / research_further)
      - relevance >= 0.5
      - not already in a live proposal
    """
    all_gaps = read_recent_gaps(limit=500)
    scored = []
    for g in all_gaps:
        action = g.get("recommended_action", "")
        if action not in ELIGIBLE_ACTIONS:
            continue
        relevance = float(g.get("relevance", 0) or 0)
        if relevance < 0.5:
            continue
        gap_id = g.get("event_id", "")
        if _gap_already_proposed(gap_id):
            continue
        leverage = float(g.get("leverage", 0) or 0)
        significance = float(g.get("significance", 0) or 0)
        rank = leverage * 0.6 + significance * 0.25 + relevance * 0.15
        scored.append({"gap": g, "rank": rank})

    scored.sort(key=lambda x: x["rank"], reverse=True)
    return [s["gap"] for s in scored[:limit]]


def generate_proposal(gap: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Generate a single proposal from a single gap. Writes to proposals.jsonl.

    Returns the full proposal dict (including conscience score) or None on failure.
    """
    client = _build_client()
    if client is None:
        return None

    prompt = PROPOSAL_PROMPT.format(
        capabilities=capabilities_snapshot(),
        gap_title=gap.get("event_title", "") or gap.get("gap_summary", ""),
        gap_url=gap.get("event_url", ""),
        gap_event_type=gap.get("event_type", ""),
        gap_source=gap.get("source", ""),
        gap_significance=gap.get("significance", 0),
        gap_leverage=gap.get("leverage", 0),
        gap_closed=gap.get("gap_closed", ""),
        gap_created=gap.get("gap_created", ""),
        gap_reasoning=(gap.get("reasoning") or "")[:500],
        gap_action=gap.get("recommended_action", ""),
    )
    raw = _call_claude(client, PROPOSER_MODEL, prompt, max_tokens=3500)
    parsed = _parse_json(raw or "")
    if not parsed:
        logger.warning(f"[PROPOSER] parse failed for gap {gap.get('event_id')}")
        return None

    proposal_id = f"prop_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    proposal = {
        "proposal_id": proposal_id,
        "proposer_version": PROPOSER_VERSION,
        "proposer_model": PROPOSER_MODEL,
        "source_gap_id": gap.get("event_id", ""),
        "source_gap_title": gap.get("event_title", ""),
        "source_gap_url": gap.get("event_url", ""),
        **parsed,
    }

    alignment = score_regenerative_alignment(proposal)
    proposal["regenerative_score"] = alignment.get("regenerative_score", 0.0)
    proposal["conscience_verdict"] = alignment.get("verdict", "mixed")
    proposal["conscience"] = alignment

    append_proposal(proposal)
    return proposal


def propose_from_top_gap() -> Optional[dict[str, Any]]:
    """Pick the single highest-ranked unproposed gap and generate a proposal.

    Called once per scheduled cycle (daily).
    """
    candidates = rank_candidate_gaps(limit=5)
    if not candidates:
        logger.info("[PROPOSER] no eligible gaps to propose on")
        return None
    top = candidates[0]
    logger.info(
        f"[PROPOSER] proposing on gap: {top.get('event_title', '')[:80]} "
        f"(leverage={top.get('leverage')}, action={top.get('recommended_action')})"
    )
    return generate_proposal(top)
