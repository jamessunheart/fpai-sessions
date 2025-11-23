"""Database configuration and session management."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Use SQLite for local development
DATABASE_URL = "sqlite+aiosqlite:///./mission_control.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.environment == "local",
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        yield session

