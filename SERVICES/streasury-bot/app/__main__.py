"""Entrypoint: starts the long-poll bot and a small FastAPI for health/reports."""
from __future__ import annotations

import asyncio
import logging

import uvicorn
from fastapi import FastAPI

from .config import settings
from .db import close_pool, get_pool
from .reports.builders import build_report
from .reports.formatters import render_report
from .tgbot import run_forever


def make_app() -> FastAPI:
    app = FastAPI(title="STreasury Bot", version="0.1.0")

    @app.get("/health")
    async def health() -> dict:
        try:
            await get_pool()
            return {"ok": True, "service": "streasury-bot", "version": "0.1.0"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.get("/report/{period}.txt")
    async def report_txt(period: str) -> str:
        rep = await build_report(period)
        return render_report(rep)

    @app.get("/api/revenue/summary")
    async def revenue_summary(period: str = "24h") -> dict:
        """Revenue summary for digest aggregation.

        Args:
            period: "24h", "7d", "30d", "90d" (default: "24h")

        Returns:
            {
                "period": "24h",
                "total": 540.00,
                "count": 3,
                "change_pct": 12.5,  # vs previous period
                "trailing_30d": 14838.00,
                "trailing_90d": 48019.00,
                "trailing_365d": 194545.34
            }
        """
        from datetime import datetime, timedelta, timezone
        from .db import connect
        from .config import settings

        # Map period to days
        period_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
        days = period_map.get(period, 1)

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        prev_start = start - timedelta(days=days)

        tid = settings.default_tenant_id

        async with connect() as conn:
            async with conn.cursor() as cur:
                # Current period revenue (positive amounts only)
                await cur.execute(
                    "SELECT COALESCE(SUM(amount), 0), COUNT(*) "
                    "FROM streasury.txn WHERE tenant_id = %s "
                    "AND occurred_at >= %s AND occurred_at < %s "
                    "AND amount > 0",
                    (tid, start, now),
                )
                total, count = await cur.fetchone()

                # Previous period revenue (for change %)
                await cur.execute(
                    "SELECT COALESCE(SUM(amount), 0) "
                    "FROM streasury.txn WHERE tenant_id = %s "
                    "AND occurred_at >= %s AND occurred_at < %s "
                    "AND amount > 0",
                    (tid, prev_start, start),
                )
                prev_total = (await cur.fetchone())[0]

                # Trailing 30/90/365 days
                await cur.execute(
                    "SELECT "
                    "  COALESCE(SUM(CASE WHEN occurred_at >= %s THEN amount ELSE 0 END), 0), "
                    "  COALESCE(SUM(CASE WHEN occurred_at >= %s THEN amount ELSE 0 END), 0), "
                    "  COALESCE(SUM(CASE WHEN occurred_at >= %s THEN amount ELSE 0 END), 0) "
                    "FROM streasury.txn WHERE tenant_id = %s AND amount > 0",
                    (now - timedelta(days=30), now - timedelta(days=90),
                     now - timedelta(days=365), tid),
                )
                t30, t90, t365 = await cur.fetchone()

        total = float(total or 0)
        prev_total = float(prev_total or 0)
        change_pct = ((total - prev_total) / prev_total * 100) if prev_total > 0 else 0.0

        return {
            "period": period,
            "total": round(total, 2),
            "count": int(count),
            "change_pct": round(change_pct, 1),
            "trailing_30d": round(float(t30 or 0), 2),
            "trailing_90d": round(float(t90 or 0), 2),
            "trailing_365d": round(float(t365 or 0), 2),
        }

    @app.on_event("shutdown")
    async def _close() -> None:
        await close_pool()

    return app


async def _run_all() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    log = logging.getLogger("streasury")

    app = make_app()
    config = uvicorn.Config(
        app,
        host=settings.http_host,
        port=settings.http_port,
        log_level=settings.log_level.lower(),
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    log.info("starting bot + http on %s:%s", settings.http_host, settings.http_port)
    await asyncio.gather(server.serve(), run_forever())


def main() -> int:
    try:
        asyncio.run(_run_all())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
