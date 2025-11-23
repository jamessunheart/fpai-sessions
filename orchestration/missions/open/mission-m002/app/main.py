"""FastAPI application entrypoint for Mission Control Dashboard."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import settings
from app.core.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Create tables on startup (for local dev convenience)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Close DB connection on shutdown
    await engine.dispose()


def create_application() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    application = FastAPI(
        title=settings.service_name,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.include_router(api_router)
    return application


app = create_application()

__all__ = ("app", "create_application")

