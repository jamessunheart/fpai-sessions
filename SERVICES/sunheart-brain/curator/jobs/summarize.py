"""Summarize job — for every Conversation still at '📥 Imported', produce a
2-3 sentence Summary + suggested Topics, and auto-apply (safe op).
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from ..appflowy import AppFlowy
from ..llm import complete
from ..proposals import Proposal, ProposalWriter

log = logging.getLogger("curator.summarize")

MAX_CONVOS_PER_RUN = int(__import__("os").environ.get("CURATOR_SUMMARIZE_MAX", "30"))

SYSTEM = (
    "You summarize an AI chat conversation in 2-3 sentences. Focus on the "
    "decision, outcome, or insight — not the back-and-forth. Then list up to "
    "5 short topic tags (lowercase, hyphenated). Be dense."
)


async def run(run_id: str) -> dict[str, Any]:
    stats = {"candidates": 0, "summarized": 0, "errors": 0}

    async with AppFlowy() as af:
        writer = ProposalWriter(af)

        # Find "03 · Conversations"
        try:
            _, convo_db_id = await af.find_database_id("03 · Conversations")
            _, notes_db_id = await af.find_database_id("01 · Notes")
        except LookupError as e:
            log.warning("required db missing: %s", e)
            return stats

        rows = await af.list_rows(convo_db_id, limit=MAX_CONVOS_PER_RUN * 3)
        candidates = [r for r in rows if (r.get("cells", {}).get("Status") or "").startswith("📥")]
        stats["candidates"] = len(candidates)
        candidates = candidates[:MAX_CONVOS_PER_RUN]

        for convo in candidates:
            cells = convo.get("cells") or {}
            title = cells.get("Title") or ""
            # Pull note bodies via relation
            linked_note_ids = cells.get("Linked Notes") or []
            if not linked_note_ids:
                continue
            texts = []
            for nid in linked_note_ids[:40]:
                try:
                    note = await af.get(
                        f"/api/workspace/{af.workspace_id}/database/{notes_db_id}/row/{nid}"
                    )
                    body = ((note.get("data") or {}).get("cells") or {}).get("Content") or ""
                    texts.append(body[:2000])
                except Exception:
                    pass
            if not texts:
                continue

            user = json.dumps({"title": title, "messages": texts})
            hint = (
                'Return JSON: {"summary":"2-3 sentences","topics":["tag1","tag2"],'
                '"confidence":0.0-1.0}'
            )
            try:
                res = await complete(SYSTEM, user + "\n\n" + hint, max_tokens=400)
                d = res.parse_json()
            except Exception as e:
                log.warning("summarize failed for %s: %s", title, e)
                stats["errors"] += 1
                continue

            proposal = Proposal(
                proposal=f"Summary: {title[:100]}",
                type="summarize-conversation",
                confidence_score=float(d.get("confidence", 0.85)),
                proposed_by="summarize",
                reasoning=d.get("summary", ""),
                diff={
                    "conversation_row_id": convo.get("id"),
                    "summary": d.get("summary"),
                    "topics": d.get("topics", []),
                },
                run_id=run_id,
                model=res.model,
                prompt_sha1=res.prompt_sha1,
            )
            # Auto-apply: write Summary + Topics + flip Status to '🧠 Summarized'
            try:
                await af.update_row(convo_db_id, convo["id"], {
                    "Summary": d.get("summary", ""),
                    "Topics": d.get("topics", []),
                    "Status": "🧠 Summarized",
                })
                await writer.write(proposal, auto_apply=True)
                stats["summarized"] += 1
            except Exception as e:
                log.error("apply failed for %s: %s", title, e)
                stats["errors"] += 1

        await writer.notify("summarize", run_id=run_id)

    return stats
