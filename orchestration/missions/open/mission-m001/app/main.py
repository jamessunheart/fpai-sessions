"""Autonomous Executor FastAPI app."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api import api_router
from app.core import settings
from app.core.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.service_name,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.include_router(api_router)

    @application.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/docs")

    return application


app = create_app()

__all__ = ("app", "create_app")

