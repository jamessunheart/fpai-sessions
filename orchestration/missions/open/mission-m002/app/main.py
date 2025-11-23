"""FastAPI application entrypoint for Mission Control Dashboard."""
from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import settings


def create_application() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    application = FastAPI(
        title=settings.service_name,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.include_router(api_router)
    return application


app = create_application()

__all__ = ("app", "create_application")

