"""app/ledger.py — write/read primitives over the streasury schema.

Kept small and explicit so handlers don't reach into the DB themselves.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg

from .config import settings
from .db import connect

log = logging.getLogger("streasury.ledger")


def _tenant_id(tenant_id: int | None) -> int:
    return tenant_id if tenant_id is not None else settings.default_tenant_id


def dedup_hash(occurred_at: datetime, amount: float, vendor: str | None) -> str:
    raw = f"{occurred_at.date().isoformat()}|{round(amount, 2)}|{(vendor or '').strip().lower()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


@dataclass
class TxnInsert:
    account_slug: str
    amount: float
    category: str
    occurred_at: datetime | None = None
    currency: str = "USD"
    vendor: str | None = None
    note: str | None = None
    source: str = "manual"
    source_ref: str | None = None
    import_batch_id: int | None = None
    tenant_id: int | None = None


async def ensure_account(slug: str, *, name: str | None = None, currency: str = "USD",
                         kind: str = "cash", tenant_id: int | None = None) -> int:
    """Get or create an account by (tenant_id, slug). Returns id."""
    tid = _tenant_id(tenant_id)
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO streasury.account (tenant_id, slug, name, currency, kind) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (tenant_id, slug) DO UPDATE SET slug = EXCLUDED.slug "
                "RETURNING id",
                (tid, slug, name or slug, currency, kind),
            )
            row = await cur.fetchone()
            return int(row[0])


async def list_accounts(*, include_archived: bool = False, tenant_id: int | None = None) -> list[dict[str, Any]]:
    tid = _tenant_id(tenant_id)
    sql = (
        "SELECT slug, name, currency, kind, balance, txn_count, last_txn_at, archived "
        "FROM streasury.v_account_balance "
        "WHERE tenant_id = %s "
        + ("" if include_archived else "AND archived = FALSE ")
        + "ORDER BY balance DESC NULLS LAST"
    )
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (tid,))
            return [
                {"slug": s, "name": n, "currency": c, "kind": k,
                 "balance": float(b or 0), "txn_count": int(tc or 0),
                 "last_txn_at": lt, "archived": bool(arch)}
                for (s, n, c, k, b, tc, lt, arch) in await cur.fetchall()
            ]


async def archive_account(slug: str, archived: bool = True, *, tenant_id: int | None = None) -> bool:
    tid = _tenant_id(tenant_id)
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE streasury.account SET archived = %s WHERE tenant_id = %s AND slug = %s",
                (archived, tid, slug),
            )
            return cur.rowcount > 0


async def insert_txn(t: TxnInsert) -> dict[str, Any]:
    """Insert a transaction; respects (source,source_ref) and dedup_hash unique
    indexes. Returns inserted row info, or {'duplicate': True} if it collided.
    """
    tid = _tenant_id(t.tenant_id)
    occurred_at = t.occurred_at or datetime.now(timezone.utc)
    account_id = await ensure_account(t.account_slug, currency=t.currency, tenant_id=tid)
    # When the adapter supplies a stable source_ref, the (source, source_ref)
    # unique index is sufficient. Computing dedup_hash on top would falsely
    # collide on legitimate recurring payments (same client, same amount, same
    # day) — so skip it whenever source_ref is present. Manual / photo / voice
    # entries (which have no source_ref) still get hash-based dedup.
    dh = (
        None
        if t.source_ref or t.source == "stripe"
        else dedup_hash(occurred_at, t.amount, t.vendor)
    )

    async with connect() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(
                    "INSERT INTO streasury.txn "
                    "(tenant_id, account_id, occurred_at, amount, currency, category, vendor, note, "
                    " source, source_ref, dedup_hash, import_batch_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING id, occurred_at",
                    (tid, account_id, occurred_at, t.amount, t.currency, t.category,
                     t.vendor, t.note, t.source, t.source_ref, dh, t.import_batch_id),
                )
                row = await cur.fetchone()
                return {"id": int(row[0]), "occurred_at": row[1], "duplicate": False}
            except psycopg.errors.UniqueViolation as e:
                return {"duplicate": True, "error": str(e)}
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    return {"duplicate": True, "error": str(e)}
                raise


async def list_recent_txns(limit: int = 20, *, tenant_id: int | None = None) -> list[dict[str, Any]]:
    tid = _tenant_id(tenant_id)
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT t.id, a.slug, t.occurred_at, t.amount, t.currency, t.category, "
                "       t.vendor, t.note, t.source "
                "FROM streasury.txn t JOIN streasury.account a ON a.id = t.account_id "
                "WHERE t.tenant_id = %s "
                "ORDER BY t.occurred_at DESC LIMIT %s",
                (tid, limit),
            )
            return [
                {"id": i, "account": a, "occurred_at": ts, "amount": float(amt),
                 "currency": cur_, "category": cat, "vendor": v, "note": n, "source": src}
                for (i, a, ts, amt, cur_, cat, v, n, src) in await cur.fetchall()
            ]


async def kpi_set(name: str, value: float, unit: str | None, note: str | None,
                  *, tenant_id: int | None = None) -> int:
    tid = _tenant_id(tenant_id)
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO streasury.kpi_point (tenant_id, name, value, unit, note) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (tid, name, value, unit, note),
            )
            row = await cur.fetchone()
            return int(row[0])


async def kpi_history(name: str, limit: int = 30, *, tenant_id: int | None = None) -> list[dict[str, Any]]:
    tid = _tenant_id(tenant_id)
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT value, unit, occurred_at FROM streasury.kpi_point "
                "WHERE tenant_id = %s AND name = %s ORDER BY occurred_at DESC LIMIT %s",
                (tid, name, limit),
            )
            rows = await cur.fetchall()
    rows.reverse()
    return [
        {"value": float(v), "unit": u, "at": ts}
        for (v, u, ts) in rows
    ]


async def upsert_holding(slug: str, quantity: float, *, name: str | None = None,
                         last_unit_usd: float | None = None,
                         tenant_id: int | None = None) -> dict[str, Any]:
    tid = _tenant_id(tenant_id)
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO streasury.holding (tenant_id, slug, name, quantity, last_unit_usd, last_valued_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, now()) "
                "ON CONFLICT (tenant_id, slug) DO UPDATE SET "
                "    quantity = EXCLUDED.quantity, "
                "    last_unit_usd = COALESCE(EXCLUDED.last_unit_usd, streasury.holding.last_unit_usd), "
                "    last_valued_at = COALESCE(EXCLUDED.last_valued_at, streasury.holding.last_valued_at), "
                "    updated_at = now() "
                "RETURNING id, slug, quantity, last_unit_usd",
                (tid, slug, name or slug.upper(), quantity, last_unit_usd,
                 datetime.now(timezone.utc) if last_unit_usd is not None else None),
            )
            row = await cur.fetchone()
    return {"id": int(row[0]), "slug": row[1], "quantity": float(row[2]),
            "last_unit_usd": float(row[3]) if row[3] is not None else None}
