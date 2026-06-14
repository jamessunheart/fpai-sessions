"""Apply-Approved job — scan '07 · Curator Queue' for rows the user flipped
to ✅ Approved and execute the change idempotently.

Each proposal type knows how to apply itself via the Diff payload.
After successful apply we flip the row to ✅ Applied + Decided At/By.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from ..appflowy import AppFlowy
from ..db import connect

log = logging.getLogger("curator.apply")


def _load_ingest_token() -> str | None:
    token = (os.environ.get("SH_INGEST_TOKEN") or "").strip()
    if token:
        return token
    p = Path("/root/sh-brain-secrets/token-ingest.txt")
    if not p.exists():
        return None
    raw = p.read_text().strip()
    for ln in raw.splitlines():
        if ln.lower().startswith("token:"):
            return ln.split(":", 1)[1].strip()
    if raw.startswith("sh_"):
        return raw
    return None


async def _resolve_notes_by_filter(filter_text: str, limit: int = 200) -> list[str]:
    """Best-effort filter resolver. Accepts plain natural-language filters and
    tries to extract quoted/keyword terms; matches them as case-insensitive
    substrings against note_chunks.content.

    Returns deduplicated note_row_ids.
    """
    if not filter_text:
        return []
    # Cheap parse: pull quoted strings if present, else split on OR / commas.
    import re
    quoted = re.findall(r"['\"]([^'\"]{2,60})['\"]", filter_text)
    if not quoted:
        # split on OR / and / commas, keep tokens >= 3 chars
        raw = re.split(r"\s+OR\s+|\s+AND\s+|,", filter_text, flags=re.I)
        quoted = [t.strip() for t in raw if len(t.strip()) >= 3][:6]
    if not quoted:
        return []
    placeholders = " OR ".join(["content ILIKE %s"] * len(quoted))
    params = [f"%{q}%" for q in quoted]
    sql = f"""
        SELECT DISTINCT note_row_id
          FROM brain_index.note_chunks
         WHERE {placeholders}
         LIMIT {int(limit)}
    """
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return [str(r[0]) for r in await cur.fetchall()]


async def _apply_promote_tier(af: AppFlowy, notes_db_id: str, diff: dict) -> str:
    note_id = diff.get("note_row_id") or (diff.get("params") or {}).get("note_row_id")
    target = (diff.get("to") or (diff.get("params") or {}).get("to") or "public").lower()
    if not note_id:
        return "skipped: no note_row_id in diff"
    cell_value = {"public": "🟢 Public", "personal": "🟡 Personal", "private": "🔴 Private"}.get(target, "🟢 Public")
    await af.update_row(notes_db_id, note_id, {"Sensitivity": cell_value})
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE brain_index.note_chunks SET sensitivity=%s WHERE note_row_id=%s",
                (target, note_id),
            )
    return f"promoted 1 note to {target}"


async def _apply_add_tag(af: AppFlowy, notes_db_id: str, diff: dict) -> str:
    """Two shapes accepted:
        diff.tag + diff.note_ids                              (curator jobs)
        diff.params.tag + diff.params.filter (NL string)      (council)
    """
    params = diff.get("params") or {}
    tag = diff.get("tag") or params.get("tag")
    if not tag:
        return "skipped: no tag in diff"
    note_ids = diff.get("note_ids") or []
    if not note_ids and params.get("filter"):
        note_ids = await _resolve_notes_by_filter(params["filter"])
    if not note_ids:
        return f"skipped: no notes resolved for tag '{tag}'"
    applied = 0
    for nid in note_ids[:200]:  # safety cap
        try:
            row = await af.get(f"/api/workspace/{af.workspace_id}/database/{notes_db_id}/row/detail", ids=nid)
            data = row.get("data") or []
            cells = (data[0] if data else {}).get("cells") if isinstance(data, list) else (data.get("cells") or {})
            existing = (cells or {}).get("Tags") or []
            if isinstance(existing, str):
                existing = [t.strip() for t in existing.split(",") if t.strip()]
            if tag not in existing:
                await af.update_row(notes_db_id, nid, {"Tags": list({*existing, tag})})
                applied += 1
        except Exception as e:
            log.warning("add-tag skipped %s: %s", nid, e)
    return f"add-tag '{tag}' → {applied} notes"


async def _apply_create_task(af: AppFlowy, notes_db_id: str, diff: dict) -> str:
    """Create an executable task note via brain-index ingest route so it is both
    written to AppFlowy and embedded into note_chunks for future retrieval.

    Accepted diff shape:
        {
          "params": {
            "title": "...",
            "content": "...",
            "tags": ["execution", "recruiting"],
            "sensitivity": "personal|public"
          }
        }
    """
    params = diff.get("params") or {}
    title = (params.get("title") or diff.get("title") or "").strip()
    if not title:
        return "skipped: create-task missing title"
    content = (params.get("content") or diff.get("content") or "").strip()
    tags = params.get("tags") or diff.get("tags") or ["execution"]
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    sens_code = str(params.get("sensitivity") or diff.get("sensitivity") or "personal").lower()
    sens_label = "🟡 Personal" if sens_code != "public" else "🟢 Public"
    source_seed = (title + "\n" + (content or title)).strip().lower().encode("utf-8")
    source_id = f"task:{hashlib.sha1(source_seed).hexdigest()[:24]}"

    token = _load_ingest_token()
    if not token:
        return "skipped: ingest token unavailable for create-task"
    base = (os.environ.get("BRAIN_INDEX_BASE") or "http://127.0.0.1:28090").rstrip("/")
    payload = {
        "source": "council-exec",
        "source_id": source_id,
        "title": title[:200],
        "content": content or title,
        "tags": tags[:12],
        "note_type": "Task",
        "sensitivity": sens_label,
        "prefer": "local",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{base}/ingest/add_note",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json()
    created = bool(data.get("created", True))
    if not created:
        return f"create-task '{title[:40]}' already exists"
    return f"create-task '{title[:40]}' → note {str(data.get('note_row_id') or '')[:8]}"


APPLIERS = {
    "promote-tier": _apply_promote_tier,
    "demote-tier": _apply_promote_tier,
    "add-tag":     _apply_add_tag,
    "create-task": _apply_create_task,
    # link-concept / merge-concept / summarize-conversation / split-collection
    # are not yet self-applying. They will land on the queue as 🟡 Proposed,
    # then if user flips ✅ Approved we mark them ✅ Applied with a note that
    # manual application is still required (placeholder until v2).
}


async def _row_details(af: AppFlowy, db_id: str, row_id: str) -> dict:
    """Fetch a single row's cells via the /row/detail endpoint."""
    body = await af.get(
        f"/api/workspace/{af.workspace_id}/database/{db_id}/row/detail",
        ids=row_id,
    )
    data = body.get("data") or []
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return {}


async def run(run_id: str) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "examined": 0,
        "applied": 0,
        "errors": 0,
        "messages": [],
    }

    async with AppFlowy() as af:
        _, queue_db_id = await af.find_database_id("07 · Curator Queue")
        _, notes_db_id = await af.find_database_id("01 · Notes")
        ids = await af.list_rows(queue_db_id, limit=500)

        for row_summary in ids:
            rid = row_summary.get("id")
            if not rid:
                continue
            try:
                detail = await _row_details(af, queue_db_id, rid)
            except Exception as e:
                log.warning("row detail fetch failed %s: %s", rid, e)
                continue
            cells = detail.get("cells") or {}
            status = (cells.get("Status") or "")
            if not status.startswith("✅ Approved"):
                continue
            stats["examined"] += 1

            ptype = str(cells.get("Type") or "").strip().lower()
            try:
                payload = json.loads(cells.get("Diff") or "{}")
                if not ptype and isinstance(payload, dict):
                    ptype = str(payload.get("proposal_type") or "").strip().lower()
                diff = payload.get("diff") if isinstance(payload, dict) and "diff" in payload else payload
                if not isinstance(diff, dict):
                    diff = {}
                if not ptype:
                    ptype = str(diff.get("type") or "").strip().lower()
            except Exception as e:
                log.error("bad diff on %s: %s", rid, e)
                stats["errors"] += 1
                continue

            applier = APPLIERS.get(ptype)
            note = ""
            if applier:
                try:
                    note = await applier(af, notes_db_id, diff)
                except Exception as e:
                    log.error("apply failed %s (%s): %s", rid, ptype, e)
                    stats["errors"] += 1
                    continue
            else:
                note = f"manual: no applier for type '{ptype}' yet"
                log.info("no applier for type %s on row %s — flagging applied", ptype, rid)

            await af.update_row(queue_db_id, rid, {
                "Status": "✅ Applied",
                "Decided At": datetime.now(timezone.utc).isoformat(),
                "Decided By": "apply-approved",
            })
            stats["applied"] += 1
            stats["messages"].append(f"{rid[:8]} {ptype}: {note}")

    return stats
