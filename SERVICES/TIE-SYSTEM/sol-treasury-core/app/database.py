"""
Database configuration and models
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from typing import AsyncGenerator
from datetime import datetime
import os

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/tie_treasury"
)

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


# Database Models
class TreasuryTransactionDB(Base):
    """Treasury transaction record"""
    __tablename__ = "treasury_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)  # Solana tx signature
    wallet_address = Column(String, index=True)

    type = Column(String)  # deposit or withdrawal
    amount_sol = Column(Float)

    status = Column(String)  # pending, confirmed, failed

    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

    # For deposits: TIE contract value (2x)
    tie_contract_value = Column(Float, nullable=True)

    # Solana details
    block_number = Column(Integer, nullable=True)
    slot = Column(Integer, nullable=True)


class TreasuryStateDB(Base):
    """Treasury state snapshot"""
    __tablename__ = "treasury_state"

    id = Column(Integer, primary_key=True)

    total_deposited = Column(Float)
    total_withdrawn = Column(Float)
    current_balance = Column(Float)

    treasury_ratio = Column(Float)
    holder_control_pct = Column(Float, nullable=True)

    paused = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
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
