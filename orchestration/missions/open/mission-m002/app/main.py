"""FastAPI application entrypoint for Mission Control Dashboard."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.core.config import settings
from app.core.database import engine
from app.models import Base
from app.services.telemetry_bus import TelemetryBus


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Create tables on startup (for local dev convenience)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Close DB connection on shutdown
    await engine.dispose()


STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_application() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    application = FastAPI(
        title=settings.service_name,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.state.telemetry_bus = TelemetryBus()
    application.include_router(api_router)
    if STATIC_DIR.exists():
        application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/", include_in_schema=False)
    async def root():
        dashboard = STATIC_DIR / "dashboard.html"
        if dashboard.exists():
            return FileResponse(dashboard)
        return RedirectResponse(url="/docs")

    return application


app = create_application()

__all__ = ("app", "create_application")

