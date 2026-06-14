"""
Database configuration and models
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from typing import AsyncGenerator
from datetime import datetime
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/tie_contracts"
)

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class TIEContractDB(Base):
    """TIE contract database model"""
    __tablename__ = "tie_contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(String, unique=True, index=True)
    nft_mint = Column(String, unique=True, index=True)
    owner = Column(String, index=True)

    sol_deposited = Column(Float)
    contract_value = Column(Float)

    status = Column(String)  # held or redeemed
    voting_weight = Column(Integer)

    deposit_tx = Column(String)
    issue_date = Column(DateTime, default=datetime.utcnow)
    redeemed_date = Column(DateTime, nullable=True)

    metadata_uri = Column(String)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
