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

            beacon_growth = None
            try:
                await cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'live')::int
                      FROM brain_index.beacon_campaigns
                    """
                )
                (active_campaigns,) = await cur.fetchone()
                await cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE event_type = 'click')::int,
                        COUNT(*) FILTER (WHERE event_type = 'chat_start')::int,
                        COUNT(*) FILTER (WHERE event_type = 'proof_created')::int
                      FROM brain_index.beacon_events
                     WHERE at > NOW() - INTERVAL '24 hours'
                    """
                )
                beacon_clicks, beacon_chats, beacon_proofs = await cur.fetchone()
                await cur.execute(
                    """
                    SELECT campaign_id, cost_per_proof
                      FROM brain_index.beacon_campaigns
                     WHERE proofs_created > 0
                     ORDER BY cost_per_proof ASC NULLS LAST, proofs_created DESC
                     LIMIT 1
                    """
                )
                best = await cur.fetchone()
                await cur.execute(
                    """
                    SELECT COUNT(*)::int
                      FROM brain_index.beacon_variants
                     WHERE james_approved_at IS NULL
                    """
                )
                (awaiting_approval,) = await cur.fetchone()
                beacon_growth = {
                    "active_campaigns": active_campaigns,
                    "clicks_24h": beacon_clicks,
                    "chat_starts_24h": beacon_chats,
                    "proofs_24h": beacon_proofs,
                    "best": {
                        "campaign_id": best[0],
                        "cost_per_proof": str(best[1]),
                    } if best else None,
                    "ready_for_james": awaiting_approval,
                    "pacing": {
                        "scale": False,
                        "reason": "hold until proof signal is stable",
                    },
                    "next_test_recommendation": "Approve one organic variant and route it through onboarding before any paid spend.",
                }
            except Exception as e:
                log.info("beacon growth digest skipped: %s", e)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "totals": {"chunks": total_chunks, "concepts": total_concepts},
        "last_24h": {
            "new_chunks_by_sensitivity": by_sens,
            "auto_merges": merges_24h,
            "blocked_queries": blocked_24h,
            "top_agents": [{"agent": a, "calls": n} for a, n in agents],
        },
        "beacon_growth": beacon_growth,
    }

    summary = (
        f"+{sum(by_sens.values())} chunks · "
        f"{merges_24h} auto-merges · "
        f"{blocked_24h} blocked queries"
    )
    if beacon_growth:
        summary += (
            f" · Beacon {beacon_growth['active_campaigns']} active/"
            f"{beacon_growth['proofs_24h']} proofs"
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
