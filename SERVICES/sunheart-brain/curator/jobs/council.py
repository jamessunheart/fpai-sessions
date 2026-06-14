"""Council job — Claude × GPT debate on how to optimize Sunheart Brain.

Pipeline (one run):
    1. Pull metrics + a representative sample of recent notes/concepts
       from brain_index.
    2. Ask Claude (claude-sonnet-4) and GPT (gpt-4o-mini by default)
       independently for their top 3-5 actionable optimizations.
    3. Hand both answers back to a synthesizer model and ask it to:
         - identify common ground (where both agree → highest priority),
         - flag genuine disagreements with the strongest argument from each side,
         - rank a final 5-item action brief most valuable to the human owner.
    4. Write a single proposal row to '07 · Curator Queue' (Type='council')
       with the synthesized brief in `Proposal`, the full transcript in
       `AI Reasoning`, and the structured payload in `Diff`.

This is the most expensive job in the system; it ships ~5-15k tokens per
run on each provider. Default cadence: weekly.

Env knobs:
    CURATOR_COUNCIL_SYNTHESIZER  = "claude" | "openai"   (default "claude")
    CURATOR_COUNCIL_SAMPLE_SIZE  = int                  (default 30)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from .. import llm
from ..appflowy import AppFlowy
from ..db import connect
from .apply_approved import APPLIERS
from ..proposals import Proposal, ProposalWriter, SAFE_AUTO_APPLY

log = logging.getLogger("curator.council")


SYNTHESIZER = (os.environ.get("CURATOR_COUNCIL_SYNTHESIZER") or "claude").lower()
SAMPLE_SIZE = int(os.environ.get("CURATOR_COUNCIL_SAMPLE_SIZE") or "30")
COHERENCE_MISSION = os.environ.get(
    "SH_COHERENCE_MISSION",
    "Help James maximize coherence between ultimate intentions and daily execution.",
).strip()
AUTO_LOW_RISK = (os.environ.get("CURATOR_COUNCIL_AUTO_LOW_RISK") or "true").strip().lower() in {
    "1", "true", "yes", "on"
}
CREATE_TASK_AUTO_THRESHOLD = float(os.environ.get("CURATOR_COUNCIL_CREATE_TASK_AUTO_THRESHOLD") or "0.80")
MIN_EXEC_TASKS = int(os.environ.get("CURATOR_COUNCIL_MIN_EXEC_TASKS") or "2")


SYSTEM_PROMPT = """You are a senior knowledge-management strategist reviewing a
personal "second brain" (a self-hosted AppFlowy + pgvector store called
Sunheart Brain). The owner ingests memories from prior AI chats (Claude,
ChatGPT, Cursor), Bear notes, and PDFs/papers.

Mission anchor (do not ignore):
The mission is provided in the user prompt.

Your job: propose 3-5 concrete, high-leverage moves for this week that improve
COHERENCE: alignment between long-term intentions and day-to-day behavior.
Prioritize actions that convert insight into execution and reduce drift.
Include task/recruiting moves when supported by the snapshot data.

Each optimization MUST include:
    - title (≤8 words, action-oriented)
    - rationale (≤2 sentences, references the data)
    - effort (one of: "low", "medium", "high")
    - leverage (one of: "low", "medium", "high")
    - first_step (concrete next action the curator agent could take today)

Return ONLY a single JSON object of the form:
{"optimizations": [{"title": "...", "rationale": "...", "effort": "...",
                    "leverage": "...", "first_step": "..."}]}
"""


SYNTH_SYSTEM_PROMPT = """You are the moderator of a two-AI council. Two senior
AIs (Claude and GPT) have independently reviewed the same brain snapshot and
each produced a list of optimization proposals.

Your job, in this order:
    1. Identify the optimizations both AIs agree on (CONSENSUS) — these are
       the highest-priority items.
    2. List the optimizations only one AI proposed but you judge to be high
       leverage (UNIQUE INSIGHTS) — note which AI proposed each.
    3. Surface any direct disagreements (CONFLICTS) with the strongest case
       from each side, and your verdict.
    4. Produce the FINAL BRIEF: the top 5 actions ranked by coherence impact:
       alignment to long-term intentions × leverage × low effort.
    5. Produce ACTIONS: a list of *concrete, executable* moves the curator
       agent could perform if approved. Each must use one of these types:
            - "add-tag"               : attach a tag to notes matching a query
            - "link-concept"          : link notes to an existing concept centroid
            - "merge-concept"         : merge concept A into concept B
            - "summarize-conversation": generate summary for a conversation
            - "promote-tier"          : raise sensitivity tier (e.g. Personal→Public)
            - "split-collection"      : separate notes into a new collection by a rule
            - "create-task"           : create an executable task note in AppFlowy
            - "other"                 : non-mutating recommendation
      At least 2 ACTIONS should be "create-task" when enough detail exists.
       Only include actions you have specific enough information to define
       (e.g. you know the tag name + filter; you know the concept names).
       Skip vague aspirational items.

Return ONLY a single JSON object:
{
  "consensus": [{"title": "...", "summary": "..."}],
  "unique": [{"title": "...", "from": "claude|gpt", "summary": "..."}],
  "conflicts": [{"topic": "...", "claude_view": "...", "gpt_view": "...", "verdict": "..."}],
  "final_brief": [{"rank": 1, "title": "...", "why": "...", "first_step": "..."}],
  "actions": [
    {
      "type": "create-task",
      "title": "Draft recruiting outreach list",
      "rationale": "Directly advances current intention with concrete execution steps.",
      "confidence": 0.92,
      "params": {
        "title": "Build top-20 candidate list for recruiting sprint",
        "content": "Collect top candidate sources and draft first outreach batch.",
        "tags": ["execution", "recruiting", "coherence"],
        "sensitivity": "personal"
      }
    }
  ]
}
"""


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _action_signature(action: dict[str, Any]) -> str:
    params = action.get("params") or {}
    if not isinstance(params, dict):
        params = {}
    atype = (action.get("type") or "other").lower()
    title = str(params.get("title") or action.get("title") or "")
    return f"{atype}:{_norm(title)[:140]}"


def _expand_actions_for_execution(
    actions: list[dict[str, Any]],
    final_brief: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Ensure the run yields enough concrete create-task actions."""
    result = [a for a in actions if isinstance(a, dict)]
    seen = {_action_signature(a) for a in result}
    task_count = sum(1 for a in result if (a.get("type") or "").lower() == "create-task")
    generated = 0

    for idx, item in enumerate(final_brief[:5], start=1):
        if task_count >= MIN_EXEC_TASKS:
            break
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        why = str(item.get("why") or "").strip()
        first_step = str(item.get("first_step") or "").strip()
        rank = item.get("rank", idx)
        default_step = "Define the smallest concrete next move and execute it today."
        content_lines = [
            f"Council rank: {rank}",
            f"Why: {why}" if why else "",
            f"First step: {first_step or default_step}",
        ]
        candidate = {
            "type": "create-task",
            "title": f"Execute: {title}"[:200],
            "rationale": why or "Promote council brief into immediate execution.",
            "confidence": 0.91,
            "generated_by": "council-brief-expander",
            "params": {
                "title": title[:200],
                "content": "\n".join(x for x in content_lines if x).strip(),
                "tags": ["execution", "coherence", "council"],
                "sensitivity": "personal",
            },
        }
        sig = _action_signature(candidate)
        if sig in seen:
            continue
        seen.add(sig)
        result.append(candidate)
        task_count += 1
        generated += 1
    return result, generated


async def _gather_snapshot() -> dict[str, Any]:
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*)::int FROM brain_index.note_chunks")
            (total_chunks,) = await cur.fetchone()

            await cur.execute("SELECT COUNT(*)::int FROM brain_index.concepts")
            (total_concepts,) = await cur.fetchone()

            await cur.execute(
                """
                SELECT source, sensitivity, COUNT(*)::int
                  FROM brain_index.note_chunks
                 GROUP BY source, sensitivity
                 ORDER BY 3 DESC
                """
            )
            by_source = [
                {"source": s, "sensitivity": sens, "count": n}
                for s, sens, n in await cur.fetchall()
            ]

            await cur.execute(
                """
                SELECT unnest(tags) AS tag, COUNT(*)::int AS n
                  FROM brain_index.note_chunks
                 GROUP BY 1
                 ORDER BY 2 DESC
                 LIMIT 20
                """
            )
            top_tags = [{"tag": t, "n": n} for t, n in await cur.fetchall()]

            await cur.execute(
                """
                SELECT COUNT(*)::int FROM brain_index.note_chunks
                 WHERE created_at > NOW() - INTERVAL '7 days'
                """
            )
            (chunks_7d,) = await cur.fetchone()

            await cur.execute(
                """
                SELECT content, source, sensitivity, tags
                  FROM brain_index.note_chunks
                 ORDER BY created_at DESC
                 LIMIT %s
                """,
                (SAMPLE_SIZE,),
            )
            sample = [
                {"content": (c or "")[:600], "source": s, "sensitivity": sens, "tags": tags}
                for c, s, sens, tags in await cur.fetchall()
            ]

    return {
        "totals": {"chunks": total_chunks, "concepts": total_concepts},
        "by_source": by_source,
        "top_tags": top_tags,
        "chunks_last_7d": chunks_7d,
        "sample_recent_notes": sample,
    }


def _user_prompt(snapshot: dict[str, Any]) -> str:
    return (
        "Mission:\n"
        f"{COHERENCE_MISSION}\n\n"
        "Operating preferences:\n"
        "- Primary mode: coherence + goal alignment\n"
        "- Execution system: AppFlowy-first tasks\n"
        "- Recruiting: produce API-ready recruiting/freelance actions\n"
        "- Autonomy: auto low-risk actions, seek approval for risky actions\n\n"
        "Here is the current brain snapshot (stats + recent notes):\n\n"
        + json.dumps(snapshot, indent=2, default=str)[:18000]
    )


async def _ask(provider: str, system: str, user: str, max_tokens: int = 1500) -> dict:
    """Force a specific provider for one call by temporarily flipping
    the global PROVIDER variable in llm.py.
    """
    saved = llm.PROVIDER
    llm.PROVIDER = provider
    try:
        result = await llm.complete(system, user, max_tokens=max_tokens, temperature=0.3)
    finally:
        llm.PROVIDER = saved
    return {
        "provider": provider,
        "model": result.model,
        "text": result.text,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "prompt_sha1": result.prompt_sha1,
    }


async def run(run_id: str) -> dict[str, Any]:
    snapshot = await _gather_snapshot()
    user_prompt = _user_prompt(snapshot)

    log.info(
        "council snapshot: chunks=%s concepts=%s recent_7d=%s sample=%s",
        snapshot["totals"]["chunks"],
        snapshot["totals"]["concepts"],
        snapshot["chunks_last_7d"],
        len(snapshot["sample_recent_notes"]),
    )

    # 1. Round 1: each AI answers independently.
    panels: dict[str, dict] = {}
    for provider in ("anthropic", "openai"):
        try:
            panels[provider] = await _ask(provider, SYSTEM_PROMPT, user_prompt)
            log.info(
                "council[%s] model=%s tokens_in=%s tokens_out=%s",
                provider,
                panels[provider]["model"],
                panels[provider]["tokens_in"],
                panels[provider]["tokens_out"],
            )
        except Exception as e:
            log.warning("council[%s] failed: %s", provider, e)
            panels[provider] = {"provider": provider, "error": str(e)}

    valid = [p for p in panels.values() if "error" not in p]
    if not valid:
        raise RuntimeError("council: both providers failed; aborting")

    # 2. Round 2: synthesizer reads both and produces final brief.
    synth_user = (
        "CLAUDE'S RESPONSE:\n"
        + (panels.get("anthropic", {}).get("text") or "(unavailable)")
        + "\n\n---\n\nGPT'S RESPONSE:\n"
        + (panels.get("openai", {}).get("text") or "(unavailable)")
        + "\n\n---\n\nNow produce the moderator's structured JSON output."
    )
    synthesizer_provider = "anthropic" if SYNTHESIZER == "claude" else "openai"
    synth = await _ask(synthesizer_provider, SYNTH_SYSTEM_PROMPT, synth_user, max_tokens=2000)

    try:
        # Reuse the LLM result parser by faking minimal LLMResult
        parsed = json.loads(synth["text"][synth["text"].find("{") : synth["text"].rfind("}") + 1])
    except Exception as e:
        log.warning("council: synthesizer JSON parse failed (%s); using raw text", e)
        parsed = {"final_brief": [], "raw": synth["text"]}

    # Build a one-line headline for the queue row.
    final_brief = parsed.get("final_brief") or []
    if final_brief:
        headline = f"Council brief · top action: {final_brief[0].get('title', '?')}"
    else:
        headline = "Council brief"

    full_payload = {
        "snapshot_summary": {
            "totals": snapshot["totals"],
            "chunks_last_7d": snapshot["chunks_last_7d"],
            "sample_size": len(snapshot["sample_recent_notes"]),
        },
        "claude": panels.get("anthropic"),
        "gpt": panels.get("openai"),
        "synthesizer": {"model": synth["model"], "provider": synthesizer_provider},
        "result": parsed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Render a human-readable reasoning block (lands in 'AI Reasoning').
    reasoning_lines: list[str] = ["# Council brief\n"]
    for item in final_brief[:5]:
        reasoning_lines.append(
            f"**{item.get('rank', '?')}. {item.get('title', '?')}** — {item.get('why', '')}\n"
            f"   First step: {item.get('first_step', '')}\n"
        )
    if parsed.get("consensus"):
        reasoning_lines.append("\n## Consensus\n")
        for c in parsed["consensus"]:
            reasoning_lines.append(f"- {c.get('title', '?')}: {c.get('summary', '')}")
    if parsed.get("conflicts"):
        reasoning_lines.append("\n## Conflicts\n")
        for c in parsed["conflicts"]:
            reasoning_lines.append(
                f"- **{c.get('topic', '?')}**\n"
                f"  - Claude: {c.get('claude_view', '')}\n"
                f"  - GPT:    {c.get('gpt_view', '')}\n"
                f"  - Verdict: {c.get('verdict', '')}"
            )
    reasoning = "\n".join(reasoning_lines)

    raw_actions = parsed.get("actions") or []
    actions, generated_task_actions = _expand_actions_for_execution(raw_actions, final_brief)

    async with AppFlowy() as af:
        writer = ProposalWriter(af)

        # 1. Top-level brief row (informational, never auto-applied)
        await writer.write(
            Proposal(
                proposal=headline[:200],
                type="council",
                confidence_score=0.85,
                proposed_by="council",
                reasoning=reasoning,
                diff=full_payload,
                run_id=run_id,
                model=f"claude+gpt | synth={synth['model']}",
                prompt_sha1=synth.get("prompt_sha1"),
            ),
            auto_apply=False,
        )

        # 2. One row per concrete action.
        # In AUTO_LOW_RISK mode, high-confidence safe actions are applied
        # immediately via APPLIERS and recorded as ✅ Applied.
        action_rows = 0
        auto_applied_rows = 0
        _, notes_db_id = await af.find_database_id("01 · Notes")
        for a in actions:
            atype = (a.get("type") or "other").lower()
            try:
                confidence = float(a.get("confidence") or 0.7)
            except Exception:
                confidence = 0.7
            diff_payload = {
                "type": atype,
                "params": a.get("params") or {},
                "synthesizer": synth["model"],
            }
            auto_threshold = CREATE_TASK_AUTO_THRESHOLD if atype == "create-task" else 0.90
            should_auto_apply = AUTO_LOW_RISK and atype in SAFE_AUTO_APPLY and confidence >= auto_threshold
            apply_note = ""
            if should_auto_apply:
                applier = APPLIERS.get(atype)
                if applier:
                    try:
                        apply_note = await applier(af, notes_db_id, diff_payload)
                    except Exception as e:
                        log.warning("council auto-apply failed type=%s: %s", atype, e)
                        should_auto_apply = False
                        apply_note = f"auto-apply failed: {e}"
                else:
                    should_auto_apply = False
                    apply_note = f"no applier for '{atype}'"

            reasoning_text = a.get("rationale", "")
            if a.get("generated_by") == "council-brief-expander":
                reasoning_text = f"{reasoning_text}\n\nGenerated from FINAL BRIEF to drive execution.".strip()
            if apply_note:
                reasoning_text = f"{reasoning_text}\n\nAuto-apply: {apply_note}".strip()
            await writer.write(
                Proposal(
                    proposal=a.get("title", "(council action)")[:200],
                    type=atype,
                    confidence_score=confidence,
                    proposed_by="council",
                    reasoning=reasoning_text,
                    diff=diff_payload,
                    run_id=run_id,
                    model=f"claude+gpt | synth={synth['model']}",
                    prompt_sha1=synth.get("prompt_sha1"),
                ),
                auto_apply=should_auto_apply,
            )
            action_rows += 1
            if should_auto_apply:
                auto_applied_rows += 1

        # Build a richer Telegram extra: top brief items inline.
        extra_lines = []
        if final_brief:
            extra_lines.append("*Brief headlines:*")
            for item in final_brief[:3]:
                extra_lines.append(f"  {item.get('rank', '?')}. {item.get('title', '?')}")
        if generated_task_actions:
            extra_lines.append(f"*Execution tasks generated from brief:* {generated_task_actions}")
        if AUTO_LOW_RISK:
            extra_lines.append(f"*Auto-applied low-risk actions:* {auto_applied_rows}")
        await writer.notify(
            "council",
            run_id=run_id,
            extra="\n".join(extra_lines) if extra_lines else None,
        )

    return {
        "claude_ok": "error" not in panels.get("anthropic", {"error": "?"}),
        "gpt_ok":    "error" not in panels.get("openai",    {"error": "?"}),
        "consensus_count": len(parsed.get("consensus") or []),
        "unique_count":    len(parsed.get("unique") or []),
        "conflict_count":  len(parsed.get("conflicts") or []),
        "final_brief_count": len(final_brief),
        "action_rows":     action_rows,
        "auto_applied_rows": auto_applied_rows,
        "generated_task_actions": generated_task_actions,
    }
