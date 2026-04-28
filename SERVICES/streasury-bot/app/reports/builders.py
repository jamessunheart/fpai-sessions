"""app/reports/builders.py — SQL aggregations for /report."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..db import connect


def _window(period: str) -> tuple[datetime, datetime, str]:
    now = datetime.now(timezone.utc)
    if period == "week":
        start = now - timedelta(days=7)
        return start, now, "Last 7 days"
    if period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now, f"{now.strftime('%B %Y')} (MTD)"
    if period == "ytd":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now, f"YTD {now.year}"
    if period == "30d":
        return now - timedelta(days=30), now, "Last 30 days"
    if period == "90d":
        return now - timedelta(days=90), now, "Last 90 days"
    raise ValueError(f"unknown period: {period}")


async def build_report(period: str) -> dict[str, Any]:
    start, end, label = _window(period)
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0), "
                "       COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0), "
                "       COUNT(*) "
                "FROM streasury.txn WHERE occurred_at >= %s AND occurred_at < %s",
                (start, end),
            )
            income, expense, n = await cur.fetchone()

            await cur.execute(
                "SELECT category, "
                "       COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0), "
                "       COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0) "
                "FROM streasury.txn WHERE occurred_at >= %s AND occurred_at < %s "
                "GROUP BY category ORDER BY (SUM(ABS(amount))) DESC",
                (start, end),
            )
            categories = await cur.fetchall()

            await cur.execute(
                "SELECT a.slug, COALESCE(SUM(t.amount), 0) "
                "FROM streasury.account a "
                "LEFT JOIN streasury.txn t ON t.account_id = a.id "
                "  AND t.occurred_at >= %s AND t.occurred_at < %s "
                "WHERE a.archived = FALSE "
                "GROUP BY a.slug ORDER BY a.slug",
                (start, end),
            )
            by_account = await cur.fetchall()

            await cur.execute(
                "SELECT slug, balance, currency FROM streasury.v_account_balance "
                "WHERE archived = FALSE ORDER BY balance DESC NULLS LAST"
            )
            balances = await cur.fetchall()

            await cur.execute(
                "SELECT DISTINCT ON (name) name, value, unit, occurred_at "
                "FROM streasury.kpi_point ORDER BY name, occurred_at DESC"
            )
            kpis = await cur.fetchall()

    income = float(income or 0)
    expense = float(expense or 0)
    return {
        "label": label,
        "period": period,
        "start": start,
        "end": end,
        "income": income,
        "expense": expense,
        "net": income - expense,
        "n": int(n),
        "by_category": [
            {"category": c, "income": float(i), "expense": float(e)}
            for (c, i, e) in categories
        ],
        "by_account": [
            {"slug": s, "delta": float(d)}
            for (s, d) in by_account
        ],
        "balances": [
            {"slug": s, "balance": float(b or 0), "currency": c}
            for (s, b, c) in balances
        ],
        "kpis": [
            {"name": n, "value": float(v), "unit": u, "as_of": ts}
            for (n, v, u, ts) in kpis
        ],
    }
