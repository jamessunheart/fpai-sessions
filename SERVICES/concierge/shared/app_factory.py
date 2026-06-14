"""Shared FastAPI app factory — health, request id, structured logging."""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

from .config import settings
from .db import healthcheck
from .logging import configure_logging, get_logger


def create_app(service_name: str, *, version: str = "0.1.0") -> FastAPI:
    configure_logging()
    log = get_logger(service_name)

    app = FastAPI(title=f"concierge.{service_name}", version=version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.env == "development" else [],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logger(request: Request, call_next):
        rid = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        start = time.monotonic()
        response = await call_next(request)
        elapsed = (time.monotonic() - start) * 1000.0
        response.headers["X-Request-Id"] = rid
        log.info(
            "request",
            service=service_name,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            ms=round(elapsed, 2),
            request_id=rid,
        )
        return response

    @app.get("/health")
    async def _health() -> dict:
        db_ok = await healthcheck()
        return {"service": service_name, "ok": db_ok, "env": settings.env}

    @app.get("/ready")
    async def _ready() -> dict:
        db_ok = await healthcheck()
        return {"ready": db_ok}

    return app
