"""Digest job — daily brain status report. Logs to stderr and writes a row in
'07 · Curator Queue' with Type='other' for record-keeping. No LLM calls; pure
metrics so it's cheap and always runs.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..appflowy import AppFlowy
from ..db import connect
from ..proposals import Proposal, ProposalWriter

log = logging.getLogger("curator.digest")

DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))


def smoke_health_summary(*, ops_ledger: Path = DEFAULT_OPS_LEDGER, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    rows: list[dict[str, Any]] = []
    spec_gaps: list[dict[str, Any]] = []
    if not ops_ledger.exists():
        return {
            "status": "unknown",
            "summary": "smoke tests have not written to ops_ledger",
            "runs": 0,
            "warnings": 0,
            "failures": 0,
            "details": [],
            "spec_compliance_gaps": [],
        }
    for line in ops_ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        try:
            ts = datetime.strptime(row.get("ts", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if ts < cutoff:
            continue
        if row.get("loop") == "smoke_test" and row.get("event") == "smoke_test":
            rows.append(row)
        if row.get("loop") == "spec_checker" and row.get("event") == "spec_gap":
            spec_gaps.append(row)
    warnings = sum(int(r.get("warnings") or 0) for r in rows)
    failures = sum(int(r.get("failures") or 0) for r in rows)
    details = [str(r.get("detail", "")) for r in rows if r.get("status") == "FAIL" or int(r.get("failures") or 0) > 0]
    skipped = rows and rows[-1].get("status") == "SKIP"
    if failures:
        icon = "🔴"
        summary = f"{icon} {failures} failures: {'; '.join(details[:3])}"
        status = "fail"
    elif skipped:
        summary = "🟡 smoke tests skipped by kill switch"
        status = "skip"
    elif warnings:
        icon = "🟡"
        summary = f"{icon} {warnings} warnings"
        status = "warn"
    elif rows:
        icon = "🟢"
        summary = f"{icon} All 7 checks passed"
        status = "pass"
    else:
        summary = "🟡 no smoke test runs in last 24h"
        status = "warn"
    return {
        "status": status,
        "summary": summary,
        "runs": len(rows),
        "warnings": warnings,
        "failures": failures,
        "details": details[:5],
        "spec_compliance_gaps": spec_gaps[:10],
    }


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
        "system_health": smoke_health_summary(),
    }

    summary = (
        f"+{sum(by_sens.values())} chunks · "
        f"{merges_24h} auto-merges · "
        f"{blocked_24h} blocked queries · "
        f"SYSTEM HEALTH: {report['system_health']['summary']}"
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
