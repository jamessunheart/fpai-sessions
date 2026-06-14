#!/usr/bin/env python
"""push_revenue_signal.py — daily revenue summary into the morning digest.

Reads last-24h and MTD revenue from streasury (currently just the outbounders
adapter; future adapters land here automatically), then POSTs a `metric`
signal to chief-of-staff (port 8107 on primary). Chief-of-staff includes
context-tier signals in the 9am Telegram digest.

Run via systemd timer at 08:55 UTC daily (5 min before chief-of-staff's
9am digest). Manual run for testing:

    cd /opt/streasury-bot
    .venv/bin/python -m scripts.push_revenue_signal
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

from app.db import close_pool, connect

CHIEF_OF_STAFF_URL = os.environ.get(
    "CHIEF_OF_STAFF_URL",
    "http://198.54.123.234:8107/signal",
)
TIMEOUT_SEC = float(os.environ.get("CHIEF_OF_STAFF_TIMEOUT", "10"))


async def collect_revenue() -> dict[str, Any]:
    """Pull revenue numbers from streasury.txn for the last 24h, MTD, 30d."""
    async with connect() as c:
        async with c.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    COALESCE(SUM(amount) FILTER (WHERE occurred_at >= NOW() - INTERVAL '24 hours'), 0)::float AS last_24h,
                    COALESCE(SUM(amount) FILTER (WHERE occurred_at >= DATE_TRUNC('month', NOW())), 0)::float AS mtd,
                    COALESCE(SUM(amount) FILTER (WHERE occurred_at >= NOW() - INTERVAL '30 days'), 0)::float AS trailing_30d,
                    COALESCE(SUM(amount) FILTER (WHERE occurred_at >= NOW() - INTERVAL '7 days'), 0)::float AS trailing_7d,
                    COUNT(*) FILTER (WHERE occurred_at >= NOW() - INTERVAL '24 hours') AS txn_count_24h,
                    COUNT(*) FILTER (WHERE occurred_at >= DATE_TRUNC('month', NOW())) AS txn_count_mtd
                FROM streasury.txn
                WHERE source = 'outbounders' AND amount > 0
                """
            )
            row = await cur.fetchone()
            keys = ("last_24h", "mtd", "trailing_30d", "trailing_7d", "txn_count_24h", "txn_count_mtd")
            return dict(zip(keys, row))


def render_summary(rev: dict[str, Any]) -> tuple[str, str, str]:
    """Return (title, description, urgency_hint).

    Urgency: trailing-7d revenue compared to the prior 7d window already
    available in `rev` would let us surface drops, but for v1 we keep
    everything `context`. Only flag urgent when 24h is zero AND it's a
    weekday — which here we approximate as "zero on any day" since cash
    revenue should land most days.
    """
    h24 = rev["last_24h"]
    mtd = rev["mtd"]
    d30 = rev["trailing_30d"]
    d7 = rev["trailing_7d"]
    c24 = rev["txn_count_24h"]

    title = f"💰 Outbounders revenue: ${h24:,.0f} (24h) / ${mtd:,.0f} MTD"

    description = (
        f"Last 24h: ${h24:,.2f} ({c24} txn)\n"
        f"MTD: ${mtd:,.2f}\n"
        f"Trailing 7d: ${d7:,.2f}\n"
        f"Trailing 30d: ${d30:,.2f}"
    )

    # Heuristic urgency: zero in last 24h is unusual (Outbounders bills daily-ish).
    # If the trailing 30d average suggests revenue should have arrived, flag.
    expected_per_day = d30 / 30.0
    if expected_per_day > 100 and h24 == 0:
        urgency = "important"
    else:
        urgency = "context"
    return title, description, urgency


async def push_signal(payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
        r = await client.post(CHIEF_OF_STAFF_URL, json=payload)
        r.raise_for_status()
        return r.json()


async def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    log = logging.getLogger("push_revenue_signal")

    try:
        rev = await collect_revenue()
        log.info("collected: %s", rev)
        title, description, urgency = render_summary(rev)

        payload = {
            "source": "streasury-bot",
            "type": "metric",
            "title": title,
            "description": description,
            "urgency_hint": urgency,
            "data": {
                "currency": "USD",
                "account": "outbounders",
                "last_24h": rev["last_24h"],
                "mtd": rev["mtd"],
                "trailing_7d": rev["trailing_7d"],
                "trailing_30d": rev["trailing_30d"],
                "txn_count_24h": rev["txn_count_24h"],
                "txn_count_mtd": rev["txn_count_mtd"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        result = await push_signal(payload)
        log.info("signal accepted: %s", result.get("signal_id") or result)
        return 0
    except Exception as e:
        log.exception("failed to push revenue signal: %s", e)
        return 1
    finally:
        await close_pool()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
