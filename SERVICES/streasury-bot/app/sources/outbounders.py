"""app/sources/outbounders.py — Outbounders.com revenue adapter.

Pulls main_invoice rows from the Outbounders MariaDB into streasury.txn so
revenue from the call-center business shows up alongside everything else in
/balance and /report.

Connection details come from env (OUTBOUNDERS_DB_*) rather than
source_connection.secret because the credential is provisioned at the OS level
(streasury.env, mode 600). The source_connection row carries config like
{"since": "..."} for incremental sync.

Each main_invoice row → one streasury.txn:
    source        = 'outbounders'
    source_ref    = invoice_id
    occurred_at   = date_created
    amount        = grand_total (positive)
    category      = 'revenue'
    vendor        = client name (joined from main_users)
    account_slug  = 'outbounders'
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import pymysql

from ..db import connect as pg_connect
from ..ledger import TxnInsert, ensure_account, insert_txn
from .base import Adapter, SourceConnection, SyncResult, register

log = logging.getLogger("streasury.sources.outbounders")


def _open_outbounders_conn() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=os.environ["OUTBOUNDERS_DB_HOST"],
        port=int(os.environ.get("OUTBOUNDERS_DB_PORT", "3306")),
        user=os.environ["OUTBOUNDERS_DB_USER"],
        password=os.environ["OUTBOUNDERS_DB_PASS"],
        database=os.environ.get("OUTBOUNDERS_DB_NAME", "obapp_outbounders"),
        charset="utf8mb4",
        connect_timeout=10,
        read_timeout=30,
    )


def _fetch_invoices(since: datetime | None) -> list[tuple[Any, ...]]:
    """Synchronous fetch (pymysql is sync). Run in a thread via run_in_executor.

    Only paid invoices flow into the ledger as revenue — `date_paid` is the
    cash-flow event we want to track. Unpaid invoices stay invisible to
    streasury until they actually get paid. This keeps /balance honest.

    Returns rows of (iid, invoice_id, date_paid, grand_total, client_name).
    `iid` is the int primary key — used as source_ref for uniqueness because
    `invoice_id` (varchar) is a date-style code that recurs across rows.
    """
    conn = _open_outbounders_conn()
    try:
        with conn.cursor() as cur:
            sql = (
                "SELECT i.iid, i.invoice_id, i.date_paid, i.grand_total, "
                "       TRIM(CONCAT(COALESCE(u.firstname,''), ' ', COALESCE(u.lastname,''))) AS client_name "
                "FROM main_invoice i "
                "LEFT JOIN main_users u ON i.client_id = u.user_id "
                # paid='P' is the active "paid" status (266 in last 12mo, all carry
                # date_paid + a stripe/paypal/coinbase ref). 'Y' is a legacy code
                # (pre-2015 era). 'N'=unpaid, 'C'=cancelled.
                "WHERE i.grand_total > 0 "
                "  AND i.paid IN ('P','Y') "
                "  AND i.date_paid > '1970-01-02'"
            )
            args: tuple = ()
            if since is not None:
                sql += " AND i.date_paid >= %s"
                args = (since.replace(tzinfo=None),)
            sql += " ORDER BY i.date_paid"
            cur.execute(sql, args)
            return list(cur.fetchall())
    finally:
        conn.close()


class OutbounderAdapter(Adapter):
    kind = "outbounders"

    async def sync(self, conn: SourceConnection) -> SyncResult:
        # Read incremental cursor from config; missing == full backfill.
        since: datetime | None = None
        since_str = conn.config.get("since")
        if since_str:
            try:
                since = datetime.fromisoformat(since_str)
                if since.tzinfo is None:
                    since = since.replace(tzinfo=timezone.utc)
            except Exception:
                log.warning("outbounders[%s]: bad config['since']=%r — full backfill", conn.label, since_str)

        # Make sure the account exists before inserting txns referencing it.
        await ensure_account(
            "outbounders",
            name="Outbounders.com",
            currency="USD",
            kind="revenue",
            tenant_id=conn.tenant_id,
        )

        loop = asyncio.get_running_loop()
        rows = await loop.run_in_executor(None, _fetch_invoices, since)

        result = SyncResult()
        max_dt = since or datetime(2000, 1, 1, tzinfo=timezone.utc)

        for iid, invoice_id, date_paid, grand_total, client_name in rows:
            result.seen += 1

            # MariaDB returns naive datetimes; the Outbounders cPanel box stores in
            # server-local time which the system reports as UTC. Normalize.
            occurred_at = date_paid
            if occurred_at is not None and occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)

            res = await insert_txn(TxnInsert(
                account_slug="outbounders",
                amount=float(grand_total),
                category="revenue",
                occurred_at=occurred_at,
                currency="USD",
                vendor=(client_name or "").strip() or None,
                note=f"Outbounders invoice {invoice_id} (iid={iid})",
                source=self.kind,
                source_ref=str(iid),  # iid is the int PK, guaranteed unique
                tenant_id=conn.tenant_id,
            ))

            if res.get("duplicate"):
                result.skipped += 1
            else:
                result.inserted += 1

            if occurred_at and occurred_at > max_dt:
                max_dt = occurred_at

        # Advance the cursor with a 1-day overlap to catch back-dated invoices.
        # Unique index on (tenant_id, source, source_ref) guarantees no double-counting.
        if rows:
            new_since = (max_dt - timedelta(days=1)).isoformat()
            async with pg_connect() as pg:
                async with pg.cursor() as cur:
                    await cur.execute(
                        "UPDATE streasury.source_connection "
                        "SET config = jsonb_set(config, '{since}', to_jsonb(%s::text)) "
                        "WHERE id = %s",
                        (new_since, conn.id),
                    )

        log.info(
            "outbounders[%s] seen=%d inserted=%d skipped=%d new_since=%s",
            conn.label, result.seen, result.inserted, result.skipped,
            (max_dt - timedelta(days=1)).isoformat() if rows else None,
        )
        return result


register(OutbounderAdapter())
