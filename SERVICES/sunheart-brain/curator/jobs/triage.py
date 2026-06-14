"""Triage job — review Personal-tier notes and propose promote/demote.

Goal: the user dumps Bear in as 🟡 Personal by default, then the curator
surfaces safe candidates for promotion to 🟢 Public (e.g. clearly-technical
notes with no PII) and flags any still-Public rows that smell sensitive.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from ..appflowy import AppFlowy
from ..db import connect
from ..llm import complete
from ..proposals import Proposal, ProposalWriter

log = logging.getLogger("curator.triage")

MAX_PER_RUN = int(os.environ.get("CURATOR_TRIAGE_MAX", "40"))

SYSTEM = (
    "You are a privacy reviewer. A note is currently 🟡 Personal. Decide if it "
    "is actually safe to make 🟢 Public (any AI can read it). Notes with "
    "passwords, credentials, medical details, personal relationships, legal "
    "matters, or anything identifying must stay Personal. Be conservative."
)


async def run(run_id: str) -> dict[str, Any]:
    stats = {"examined": 0, "promote_proposals": 0, "demote_proposals": 0, "errors": 0}

    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT note_row_id, content
                  FROM brain_index.note_chunks
                 WHERE sensitivity = 'personal'
                   AND chunk_idx = 0
                 ORDER BY created_at DESC
                 LIMIT %s
                """,
                (MAX_PER_RUN,),
            )
            rows = await cur.fetchall()

    if not rows:
        log.info("no personal-tier notes to triage")
        return stats

    async with AppFlowy() as af:
        writer = ProposalWriter(af)
        for note_id, content in rows:
            stats["examined"] += 1
            hint = 'Return JSON: {"decision":"promote|keep","confidence":0.0-1.0,"reasoning":"1-2 sentences"}'
            try:
                res = await complete(SYSTEM, f"NOTE:\n{content[:3000]}\n\n{hint}", max_tokens=200)
                d = res.parse_json()
            except Exception as e:
                log.warning("triage llm failed for %s: %s", note_id, e)
                stats["errors"] += 1
                continue
            decision = (d.get("decision") or "").lower()
            if decision != "promote":
                continue

            proposal = Proposal(
                proposal=f"Promote to Public: {content[:80]}",
                type="promote-tier",
                confidence_score=float(d.get("confidence", 0.5)),
                proposed_by="triage",
                reasoning=d.get("reasoning", ""),
                diff={"note_row_id": note_id, "from": "personal", "to": "public"},
                target_note_ids=[note_id],
                run_id=run_id,
                model=res.model,
                prompt_sha1=res.prompt_sha1,
            )
            await writer.write(proposal, auto_apply=False)  # tier changes ALWAYS need human
            stats["promote_proposals"] += 1

        await writer.notify("triage", run_id=run_id)

    return stats
