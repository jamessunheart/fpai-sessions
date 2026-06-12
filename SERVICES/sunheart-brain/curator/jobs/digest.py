"""Digest job — daily brain status report. Logs to stderr and writes a row in
'07 · Curator Queue' with Type='other' for record-keeping. No LLM calls; pure
metrics so it's cheap and always runs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..appflowy import AppFlowy
from ..db import connect
from ..proposals import Proposal, ProposalWriter

log = logging.getLogger("curator.digest")


async def run(run_id: str) -> dict[str, Any]:
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT sensitivity, COUNT(*)::int
                  FROM brain_index.note_chunks
                 WHERE created_at > NOW() - INTERVAL '24 hours'
                 GROUP BY sensitivity
                """
            )
            by_sens = dict(await cur.fetchall())

            await cur.execute("SELECT COUNT(*)::int FROM brain_index.note_chunks")
            (total_chunks,) = await cur.fetchone()

            await cur.execute("SELECT COUNT(*)::int FROM brain_index.concepts")
            (total_concepts,) = await cur.fetchone()

            await cur.execute(
                """
                SELECT COUNT(*)::int FROM brain_index.merge_log
                 WHERE at > NOW() - INTERVAL '24 hours'
                """
            )
            (merges_24h,) = await cur.fetchone()

            await cur.execute(
                """
                SELECT agent, COUNT(*)::int
                  FROM brain_index.audit_log
                 WHERE at > NOW() - INTERVAL '24 hours'
                 GROUP BY agent
                 ORDER BY 2 DESC
                 LIMIT 10
                """
            )
            agents = await cur.fetchall()

            await cur.execute(
                """
                SELECT COUNT(*)::int FROM brain_index.audit_log
                 WHERE at > NOW() - INTERVAL '24 hours' AND blocked = true
                """
            )
            (blocked_24h,) = await cur.fetchone()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "totals": {"chunks": total_chunks, "concepts": total_concepts},
        "last_24h": {
            "new_chunks_by_sensitivity": by_sens,
            "auto_merges": merges_24h,
            "blocked_queries": blocked_24h,
            "top_agents": [{"agent": a, "calls": n} for a, n in agents],
        },
    }

    summary = (
        f"+{sum(by_sens.values())} chunks · "
        f"{merges_24h} auto-merges · "
        f"{blocked_24h} blocked queries"
    )
    log.info("digest: %s", summary)

    async with AppFlowy() as af:
        writer = ProposalWriter(af)
        await writer.write(
            Proposal(
                proposal=f"Daily digest · {summary}",
                type="other",
                confidence_score=1.0,
                proposed_by="digest",
                reasoning=str(report),
                diff=report,
                run_id=run_id,
                model="n/a",
                prompt_sha1="n/a",
            ),
            auto_apply=False,
        )
    return report
