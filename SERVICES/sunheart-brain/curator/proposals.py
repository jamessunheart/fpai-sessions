"""curator/proposals.py — write proposals to '07 · Curator Queue'.

A single helper the jobs use. Centralizes:
    - confidence bucketing
    - auto-apply policy (safe types + high confidence)
    - Diff-as-JSON serialization
    - Run ID grouping so one run's proposals are easy to review/revert
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .appflowy import AppFlowy

log = logging.getLogger("curator.proposals")


# Proposal types that are *safe* to auto-apply when confidence is High.
# Everything else requires human flip to ✅ Approved.
SAFE_AUTO_APPLY = {
    "link-concept",       # attach a note to its existing concept centroid
    "add-tag",            # attach an existing canonical tag to a note
    "summarize-conversation",  # writes Summary to 03 · Conversations
    "create-task",        # create executable task note in AppFlowy/brain
}

HIGH_THRESHOLD = 0.90
MEDIUM_THRESHOLD = 0.70


def confidence_bucket(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "🟢 High (>0.9)"
    if score >= MEDIUM_THRESHOLD:
        return "🟡 Medium (0.7-0.9)"
    return "🔴 Low (<0.7)"


@dataclass
class Proposal:
    proposal: str                        # one-line summary
    type: str                            # "merge-concept" / …
    confidence_score: float              # 0.0 – 1.0
    proposed_by: str                     # "dedup" / "cluster-tag" / …
    reasoning: str                       # AI explanation
    diff: dict[str, Any]                 # JSON payload that describes change
    target_note_ids: list[str] | None = None
    target_concept_ids: list[str] | None = None
    run_id: str | None = None
    model: str | None = None             # "claude-…"
    prompt_sha1: str | None = None


class ProposalWriter:
    def __init__(self, af: AppFlowy) -> None:
        self.af = af
        self._queue_db_id: str | None = None
        self._field_map: dict[str, str] = {}  # name → field_id
        self.pending: list[tuple[str, str]] = []  # (row_id, title) for Telegram summary

    async def _ensure_schema(self) -> None:
        if self._queue_db_id:
            return
        _, db_id = await self.af.find_database_id("07 · Curator Queue")
        self._queue_db_id = db_id
        fields = await self.af.list_fields(db_id)
        self._field_map = {f["name"]: f["id"] for f in fields}

    async def write(self, p: Proposal, *, auto_apply: bool = True) -> tuple[str, str]:
        """Write a proposal row. Returns (row_id, final_status).

        If type ∈ SAFE_AUTO_APPLY and confidence is High and auto_apply=True,
        caller is expected to have already executed the change and we mark
        Status = ✅ Applied. Otherwise Status = 🟡 Proposed.
        """
        await self._ensure_schema()
        bucket = confidence_bucket(p.confidence_score)
        applied = auto_apply and p.type in SAFE_AUTO_APPLY and bucket == "🟢 High (>0.9)"
        status = "✅ Applied" if applied else "🟡 Proposed"

        diff_payload = {
            "proposal_type": p.type,
            "model": p.model,
            "prompt_sha1": p.prompt_sha1,
            "score": p.confidence_score,
            "diff": p.diff,
        }

        cells: dict[str, Any] = {
            "Proposal": p.proposal[:200],
            "Type": p.type,
            "Status": status,
            "Confidence": bucket,
            "Proposed By": p.proposed_by,
            "AI Reasoning": (p.reasoning or "")[:4000],
            "Diff": json.dumps(diff_payload, indent=2, default=str)[:16000],
            "Run ID": p.run_id or uuid.uuid4().hex[:12],
        }
        if applied:
            cells["Decided At"] = datetime.now(timezone.utc).isoformat()
            cells["Decided By"] = "auto"
        if p.target_note_ids and "Target Notes" in self._field_map:
            cells["Target Notes"] = p.target_note_ids
        if p.target_concept_ids and "Target Concepts" in self._field_map:
            cells["Target Concepts"] = p.target_concept_ids
        cells = {k: v for k, v in cells.items() if k in self._field_map}

        row_id = await self.af.add_row(self._queue_db_id, cells)
        log.info("proposal %s  type=%s  conf=%s  status=%s  row=%s",
                 p.proposed_by, p.type, bucket, status, row_id)
        # "council" rows are informational briefs, not actionable approval items.
        if not applied and row_id and p.type != "council":
            self.pending.append((row_id, p.proposal[:200]))
        return row_id, status

    async def notify(self, job_name: str, run_id: str | None = None, extra: str | None = None) -> None:
        """Send one Telegram summary for everything written this session,
        with inline ✅ Approve / ❌ Reject buttons per pending row.
        Silently no-ops if Telegram isn't configured."""
        if not self.pending and not extra:
            return
        from . import telegram as tg
        await tg.notify_job_summary(job_name, self.pending, run_id=run_id, extra=extra)
