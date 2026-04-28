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
