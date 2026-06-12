"""/import — CSV upload flow.

Phase 1: accepts a CSV via Telegram document upload, runs a heuristic column
detector ("amount"/"date"/"description"/"category"), shows a 5-row preview, and
batch-inserts on confirm. Dedup hash prevents re-import double-counting.

Phase 2: PDF statement parsing (pdfplumber + AI normalizer).
"""
from __future__ import annotations

import csv
import hashlib
import io
import logging
from datetime import datetime, timezone

from dateutil import parser as dateparser

from .. import ledger, telegram
from ..db import connect

log = logging.getLogger("streasury.import")


COLUMN_HINTS = {
    "date":        ("date", "transaction date", "posted", "occurred", "time"),
    "amount":      ("amount", "value", "total", "debit", "credit"),
    "description": ("description", "merchant", "vendor", "name", "memo", "details"),
    "category":    ("category", "type", "group"),
}


def detect_columns(header: list[str]) -> dict[str, int]:
    h = [c.strip().lower() for c in header]
    out: dict[str, int] = {}
    for key, hints in COLUMN_HINTS.items():
        for i, col in enumerate(h):
            if any(hint in col for hint in hints):
                out[key] = i
                break
    return out


def parse_csv(text: str, account_slug: str, source_label: str) -> list[ledger.TxnInsert]:
    rows: list[ledger.TxnInsert] = []
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return rows
    cols = detect_columns(header)
    if "amount" not in cols or "date" not in cols:
        return rows
    desc_idx = cols.get("description")
    cat_idx = cols.get("category")

    for r in reader:
        if not r or len(r) <= max(cols.values()):
            continue
        try:
            amount = float(r[cols["amount"]].replace(",", "").replace("$", ""))
        except ValueError:
            continue
        try:
            occurred_at = dateparser.parse(r[cols["date"]])
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        vendor = (r[desc_idx].strip() if desc_idx is not None and desc_idx < len(r) else None) or None
        category = (r[cat_idx].strip().lower() if cat_idx is not None and cat_idx < len(r) and r[cat_idx] else "imported")
        rows.append(ledger.TxnInsert(
            account_slug=account_slug,
            amount=amount,
            currency="USD",
            category=category,
            vendor=vendor,
            note=None,
            occurred_at=occurred_at,
            source=f"csv:{source_label}",
        ))
    return rows


async def import_csv_bytes(filename: str, content: bytes, account_slug: str) -> dict:
    text = content.decode("utf-8", errors="replace")
    sha1 = hashlib.sha1(content).hexdigest()
    rows = parse_csv(text, account_slug, source_label=filename.replace(".csv", ""))
    if not rows:
        return {"ok": False, "reason": "Couldn't detect date/amount columns. CSV needs at least 'date' and 'amount' headers."}

    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO streasury.import_batch (tenant_id, source, filename, file_sha1, rows_seen) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (1, f"csv:{filename}", filename, sha1, len(rows)),
            )
            batch_id = int((await cur.fetchone())[0])

    inserted = 0
    skipped = 0
    for r in rows:
        r.import_batch_id = batch_id
        result = await ledger.insert_txn(r)
        if result.get("duplicate"):
            skipped += 1
        else:
            inserted += 1

    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE streasury.import_batch SET rows_inserted = %s, rows_skipped = %s WHERE id = %s",
                (inserted, skipped, batch_id),
            )

    return {
        "ok": True,
        "batch_id": batch_id,
        "rows_seen": len(rows),
        "inserted": inserted,
        "skipped": skipped,
        "filename": filename,
    }


def render_import_summary(result: dict) -> str:
    if not result.get("ok"):
        return f"⚠️ Import failed: {telegram.esc(result.get('reason', 'unknown'))}"
    return (
        f"✅ Imported <code>{telegram.esc(result['filename'])}</code>\n"
        f"  • seen: {result['rows_seen']}\n"
        f"  • inserted: <b>{result['inserted']}</b>\n"
        f"  • skipped (dupes): {result['skipped']}\n"
        f"  • batch id: {result['batch_id']}"
    )
