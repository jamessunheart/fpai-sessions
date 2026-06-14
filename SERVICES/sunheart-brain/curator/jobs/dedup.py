"""Dedup job — find near-duplicate note pairs and propose merges.

Ranges:
    >0.95  → auto-link (handled by brain-index dedup endpoint, not here)
    0.85–0.95 → curator proposes merge-concept / link-concept with AI reasoning
    <0.85  → ignored

We pull the top N unseen pairs from brain-index and have the LLM decide:
    - "link"   (notes express the same concept; attach to existing centroid)
    - "merge"  (two concepts are actually one; combine them)
    - "skip"   (they're genuinely different)

Output: one queue row per pair. High-confidence "link" is auto-applied.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from ..appflowy import AppFlowy
from ..db import connect
from ..llm import complete
from ..proposals import Proposal, ProposalWriter

log = logging.getLogger("curator.dedup")

MAX_PAIRS_PER_RUN = int(__import__("os").environ.get("CURATOR_DEDUP_MAX_PAIRS", "25"))

SYSTEM = (
    "You are a brain-curator. You compare two note excerpts and decide if they "
    "express the SAME concept, related-but-different concepts, or unrelated. "
    "Be decisive. Favor 'link' when two notes are clearly talking about the "
    "same underlying idea even if phrased differently. Only 'merge' two "
    "existing concepts if they are truly synonyms."
)


async def _find_candidate_pairs(conn, limit: int) -> list[tuple[dict, dict, float]]:
    """Return pairs of (a, b, cosine) with score in [0.85, 0.95)."""
    async with conn.cursor() as cur:
        await cur.execute(
            """
            WITH pairs AS (
              SELECT a.id AS a_id, b.id AS b_id,
                     a.note_row_id AS a_note, b.note_row_id AS b_note,
                     a.content AS a_content, b.content AS b_content,
                     a.concept_id AS a_concept, b.concept_id AS b_concept,
                     1 - (a.embedding <=> b.embedding) AS score
                FROM brain_index.note_chunks a
                JOIN brain_index.note_chunks b
                  ON a.id < b.id
                 AND a.sensitivity = 'public'
                 AND b.sensitivity = 'public'
                 AND (a.embedding <=> b.embedding) < 0.15
                 AND (a.embedding <=> b.embedding) > 0.05
               LIMIT %s
            )
            SELECT * FROM pairs
             WHERE a_note <> b_note
            """,
            (limit * 4,),  # oversample then dedupe by note pair below
        )
        seen_note_pairs = set()
        out: list[tuple[dict, dict, float]] = []
        for row in await cur.fetchall():
            a_id, b_id, a_note, b_note, a_content, b_content, a_concept, b_concept, score = row
            key = tuple(sorted([a_note, b_note]))
            if key in seen_note_pairs:
                continue
            seen_note_pairs.add(key)
            out.append((
                {"chunk_id": str(a_id), "note_id": a_note, "content": a_content, "concept_id": a_concept},
                {"chunk_id": str(b_id), "note_id": b_note, "content": b_content, "concept_id": b_concept},
                float(score),
            ))
            if len(out) >= limit:
                break
        return out


async def run(run_id: str) -> dict[str, Any]:
    stats = {"pairs_examined": 0, "proposals_written": 0, "auto_applied": 0, "errors": 0}

    async with connect() as conn:
        pairs = await _find_candidate_pairs(conn, MAX_PAIRS_PER_RUN)

    if not pairs:
        log.info("no near-duplicate pairs in 0.85–0.95 band")
        return stats

    log.info("examining %d near-duplicate pairs", len(pairs))
    async with AppFlowy() as af:
        writer = ProposalWriter(af)

        for a, b, cosine in pairs:
            stats["pairs_examined"] += 1
            user = json.dumps({
                "score": cosine,
                "note_a": {"id": a["note_id"], "text": a["content"][:1500]},
                "note_b": {"id": b["note_id"], "text": b["content"][:1500]},
            })
            schema_hint = (
                'Return JSON: {"decision":"link|merge|skip","confidence":0.0-1.0,'
                '"concept_name":"short canonical name","reasoning":"1-3 sentences"}'
            )
            try:
                res = await complete(SYSTEM, user + "\n\n" + schema_hint)
                decision = res.parse_json()
            except Exception as e:
                log.warning("llm decision failed: %s", e)
                stats["errors"] += 1
                continue

            kind = decision.get("decision", "skip").lower()
            if kind == "skip":
                continue

            ptype = "link-concept" if kind == "link" else "merge-concept"
            proposal = Proposal(
                proposal=(decision.get("concept_name") or f"{ptype} at cosine={cosine:.2f}")[:150],
                type=ptype,
                confidence_score=float(decision.get("confidence", 0.0)) * cosine,
                proposed_by="dedup",
                reasoning=(decision.get("reasoning") or "") + f"\n\ncosine={cosine:.3f}",
                diff={
                    "note_a_id": a["note_id"],
                    "note_b_id": b["note_id"],
                    "cosine": cosine,
                    "llm_decision": decision,
                    "existing_concept_a": a["concept_id"],
                    "existing_concept_b": b["concept_id"],
                },
                target_note_ids=[a["note_id"], b["note_id"]],
                run_id=run_id,
                model=res.model,
                prompt_sha1=res.prompt_sha1,
            )
            _, status = await writer.write(proposal, auto_apply=True)
            stats["proposals_written"] += 1
            if status == "✅ Applied":
                stats["auto_applied"] += 1

        await writer.notify("dedup", run_id=run_id)

    return stats
