"""app/ai/snapshot.py — builds a current treasury snapshot for AI context.

Cheap (a handful of SQL queries). Result is a markdown blob that fits comfortably
in any model's context window. Used by /ask and /council.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..db import connect


async def build_snapshot(*, lookback_days: int = 90) -> dict[str, Any]:
    """Return a structured snapshot. Render with `format_snapshot_md`."""
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT slug, name, currency, kind, balance, txn_count, last_txn_at "
                "FROM streasury.v_account_balance WHERE archived = FALSE ORDER BY balance DESC NULLS LAST"
            )
            accounts = await cur.fetchall()

            await cur.execute(
                "SELECT slug, name, quantity, last_unit_usd, last_valued_at "
                "FROM streasury.holding ORDER BY (quantity * COALESCE(last_unit_usd, 0)) DESC NULLS LAST"
            )
            holdings = await cur.fetchall()

            await cur.execute(
                "SELECT category, "
                "       SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS income, "
                "       SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS expense, "
                "       COUNT(*) AS n "
                "FROM streasury.txn WHERE occurred_at >= %s "
                "GROUP BY category ORDER BY (income + expense) DESC LIMIT 20",
                (since,),
            )
            by_category = await cur.fetchall()

            await cur.execute(
                "SELECT date_trunc('month', occurred_at) AS month, "
                "       SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS income, "
                "       SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS expense "
                "FROM streasury.txn WHERE occurred_at >= %s "
                "GROUP BY month ORDER BY month",
                (since,),
            )
            by_month = await cur.fetchall()

            await cur.execute(
                "SELECT DISTINCT ON (name) name, value, unit, occurred_at "
                "FROM streasury.kpi_point ORDER BY name, occurred_at DESC"
            )
            kpis = await cur.fetchall()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lookback_days": lookback_days,
        "accounts": [
            {"slug": s, "name": n, "currency": c, "kind": k,
             "balance": float(b or 0), "txn_count": int(tc or 0),
             "last_txn_at": lt.isoformat() if lt else None}
            for (s, n, c, k, b, tc, lt) in accounts
        ],
        "holdings": [
            {"slug": s, "name": n, "quantity": float(q or 0),
             "last_unit_usd": float(p) if p is not None else None,
             "last_valued_at": v.isoformat() if v else None}
            for (s, n, q, p, v) in holdings
        ],
        "by_category": [
            {"category": cat, "income": float(inc or 0), "expense": float(exp or 0), "n": int(n)}
            for (cat, inc, exp, n) in by_category
        ],
        "by_month": [
            {"month": m.isoformat()[:7], "income": float(inc or 0), "expense": float(exp or 0)}
            for (m, inc, exp) in by_month
        ],
        "kpis": [
            {"name": n, "value": float(v), "unit": u, "as_of": ts.isoformat() if ts else None}
            for (n, v, u, ts) in kpis
        ],
    }


def format_snapshot_md(s: dict[str, Any]) -> str:
    """Compact markdown the AI can read. Keep under ~3 KB."""
    lines: list[str] = []
    lines.append(f"# Treasury snapshot ({s['lookback_days']}d window)")
    lines.append(f"_generated {s['generated_at']}_")

    lines.append("\n## Accounts")
    if not s["accounts"]:
        lines.append("_(none)_")
    for a in s["accounts"][:30]:
        lines.append(
            f"- **{a['slug']}** ({a['currency']}, {a['kind']}): "
            f"{a['balance']:,.2f} · {a['txn_count']} txns"
        )

    if s["holdings"]:
        lines.append("\n## Holdings")
        for h in s["holdings"][:20]:
            usd = (h["quantity"] * h["last_unit_usd"]) if h["last_unit_usd"] else None
            usd_part = f" ≈ ${usd:,.2f}" if usd is not None else ""
            lines.append(f"- **{h['slug']}**: {h['quantity']:,.6f}{usd_part}")

    if s["by_category"]:
        lines.append("\n## By category (window)")
        for c in s["by_category"][:15]:
            lines.append(
                f"- {c['category']}: +{c['income']:,.0f} / -{c['expense']:,.0f} ({c['n']})"
            )

    if s["by_month"]:
        lines.append("\n## By month (window)")
        for m in s["by_month"]:
            net = m["income"] - m["expense"]
            sign = "+" if net >= 0 else ""
            lines.append(f"- {m['month']}: in {m['income']:,.0f} / out {m['expense']:,.0f} (net {sign}{net:,.0f})")

    if s["kpis"]:
        lines.append("\n## KPIs (latest)")
        for k in s["kpis"][:25]:
            unit = f" {k['unit']}" if k["unit"] else ""
            lines.append(f"- {k['name']}: {k['value']:,.4g}{unit} ({k['as_of']})")

    return "\n".join(lines)
