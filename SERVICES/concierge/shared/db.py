"""Async SQLAlchemy engine + tenant-scoped session helper.

Every request must obtain a session via ``tenant_session(tenant_id)`` so that
``SET LOCAL app.tenant_id = <uuid>`` is applied and Postgres RLS policies
enforce tenant isolation at the DB layer.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def tenant_session(
    tenant_id: str | None, *, superuser: bool = False
) -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession bound to a connection with app.tenant_id SET LOCAL.

    Pass ``superuser=True`` only in trusted system contexts (migrations, cross-tenant
    admin work). Never from a request handler driven by a tenant-scoped token.
    """
    async with SessionLocal() as session:
        if superuser:
            await session.execute(
                text("SELECT set_config('app.is_superuser', 'true', true)")
            )
        else:
            await session.execute(
                text("SELECT set_config('app.is_superuser', 'false', true)")
            )
            if tenant_id is None:
                raise PermissionError("tenant_session requires a tenant_id unless superuser=True")
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def healthcheck() -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
