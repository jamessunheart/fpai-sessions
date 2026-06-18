"""Digest job — daily brain status report. Logs to stderr and writes a row in
'07 · Curator Queue' with Type='other' for record-keeping. No LLM calls; pure
metrics so it's cheap and always runs.
"""
from __future__ import annotations

import logging
import os
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..appflowy import AppFlowy
from ..db import connect
from ..proposals import Proposal, ProposalWriter

log = logging.getLogger("curator.digest")


def horizon_signal_lines() -> list[str]:
    repo = Path(os.environ.get("FPAI_CODEX_REPO", "/opt/fpai-build/FPAI_Cockpit"))
    scanner_path = repo / "tools" / "horizon" / "scanner.py"
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("fpai_horizon_scanner", scanner_path)
        _mod = _ilu.module_from_spec(_spec) if _spec and _spec.loader else None
        if not _mod:
            return []
        _spec.loader.exec_module(_mod)
        recent_horizon_signal_lines = _mod.recent_horizon_signal_lines
    except Exception:
        return []
    ledger = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
    try:
        return recent_horizon_signal_lines(ledger)
    except Exception:
        return []


def latest_probe_rate_line() -> str:
    ledger = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
    if not ledger.exists():
        return "Rate next cycle: n/a (no probe_rate row)"
    latest: dict[str, Any] | None = None
    for raw in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if str(row.get("event") or row.get("type")) == "probe_rate":
            latest = row
    if not latest:
        return "Rate next cycle: n/a (no probe_rate row)"
    return f"Rate next cycle: {latest.get('count', 'n/a')} ({latest.get('reason', 'unknown')})"


def consciousness_observer_lines() -> list[str]:
    repo = Path(os.environ.get("FPAI_CODEX_REPO", "/opt/fpai-build/FPAI_Cockpit"))
    helper_path = repo / "tools" / "consciousness" / "loop.py"
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("fpai_consciousness_loop", helper_path)
        _mod = _ilu.module_from_spec(_spec) if _spec and _spec.loader else None
        if not _mod:
            return []
        sys.modules["fpai_consciousness_loop"] = _mod
        _spec.loader.exec_module(_mod)
        section = _mod.digest_section()
    except Exception:
        return []
    return [line for line in str(section or "").splitlines() if line.strip()]


def bandwidth_ledger_lines() -> list[str]:
    repo = Path(os.environ.get("FPAI_CODEX_REPO", "/opt/fpai-build/FPAI_Cockpit"))
    report_path = repo / "core" / "STATE" / "BANDWIDTH_LEDGER.md"
    if not report_path.exists():
        return []
    try:
        text = report_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    useful: list[str] = []
    capture = False
    for raw in text.splitlines():
        line = raw.strip()
        if line == "## Recovered This Week":
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture and line.startswith("- "):
            useful.append(line)
    return useful[:4]


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

            probe_report: dict[str, Any] = {"available": False}
            try:
                await cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE notes LIKE '%send_status=sent%')::int,
                        COUNT(*) FILTER (WHERE notes LIKE '%send_status=sent%' AND engaged IS TRUE)::int,
                        COUNT(*) FILTER (WHERE notes LIKE '%send_status=sent%' AND completed_spark IS TRUE)::int,
                        AVG(quality_score) FILTER (WHERE notes LIKE '%send_status=sent%')
                      FROM brain_index.probe_sessions
                     WHERE initiated_at > NOW() - INTERVAL '24 hours'
                    """
                )
                sent, engaged, completed_spark, avg_quality = await cur.fetchone()
                probe_report = {
                    "available": True,
                    "sent": int(sent or 0),
                    "engaged": int(engaged or 0),
                    "completed_spark": int(completed_spark or 0),
                    "avg_quality": float(avg_quality) if avg_quality is not None else None,
                    "rate_line": latest_probe_rate_line(),
                }
            except Exception as exc:
                probe_report = {"available": False, "reason": str(exc)[:160]}

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "totals": {"chunks": total_chunks, "concepts": total_concepts},
        "last_24h": {
            "new_chunks_by_sensitivity": by_sens,
            "auto_merges": merges_24h,
            "blocked_queries": blocked_24h,
            "top_agents": [{"agent": a, "calls": n} for a, n in agents],
            "probe": probe_report,
        },
    }
    scanner_flags = horizon_signal_lines()
    if scanner_flags:
        report["last_24h"]["horizon_scanner_flags"] = scanner_flags
    consciousness_lines = consciousness_observer_lines()
    if consciousness_lines:
        report["last_24h"]["consciousness_observer"] = consciousness_lines
    bandwidth_lines = bandwidth_ledger_lines()
    if bandwidth_lines:
        report["last_24h"]["bandwidth_ledger"] = bandwidth_lines

    summary = (
        f"+{sum(by_sens.values())} chunks · "
        f"{merges_24h} auto-merges · "
        f"{blocked_24h} blocked queries"
    )
    proposal_text = f"Daily digest · {summary}"
    if scanner_flags:
        proposal_text += "\n\n⚡ Scanner flagged:\n" + "\n".join(f"- {line}" for line in scanner_flags)
    if consciousness_lines:
        proposal_text += "\n\n" + "\n".join(consciousness_lines)
    if bandwidth_lines:
        proposal_text += "\n\nBandwidth Ledger\n" + "\n".join(bandwidth_lines)
    if probe_report.get("available"):
        quality = "n/a" if probe_report.get("avg_quality") is None else f"{probe_report['avg_quality']:.1f}"
        proposal_text += (
            "\n\nProbe section\n"
            f"Probes sent yesterday: {probe_report['sent']} | Engaged: {probe_report['engaged']} | "
            f"Completed Spark: {probe_report['completed_spark']} | Avg quality: {quality}\n"
            f"{probe_report['rate_line']}"
        )
    log.info("digest: %s", summary)

    async with AppFlowy() as af:
        writer = ProposalWriter(af)
        await writer.write(
            Proposal(
                proposal=proposal_text,
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
