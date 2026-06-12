"""
Database models and configuration
"""

import os
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, Index
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/tie_voting"
)

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# Database Models

class VotingWeightDB(Base):
    """Voting weight tracking per wallet"""
    __tablename__ = "voting_weights"

    id = Column(Integer, primary_key=True, index=True)
    wallet = Column(String(44), unique=True, nullable=False, index=True)
    total_votes = Column(Integer, nullable=False, default=0)
    holder_votes = Column(Integer, nullable=False, default=0)  # Contracts still held (2 votes each)
    seller_votes = Column(Integer, nullable=False, default=0)  # Contracts redeemed (1 vote each)
    held_contracts = Column(Integer, nullable=False, default=0)
    redeemed_contracts = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Index for leaderboard queries
    __table_args__ = (
        Index('idx_total_votes_desc', total_votes.desc()),
    )


class VotingEventDB(Base):
    """Historical record of voting weight changes"""
    __tablename__ = "voting_events"

    id = Column(Integer, primary_key=True, index=True)
    wallet = Column(String(44), nullable=False, index=True)
    contract_id = Column(String(20), nullable=False)
    event_type = Column(String(20), nullable=False)  # "contract_minted" or "contract_redeemed"
    vote_change = Column(Integer, nullable=False)  # +2 for mint, -1 for redeem
    new_total_votes = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Index for history queries
    __table_args__ = (
        Index('idx_wallet_timestamp', wallet, timestamp.desc()),
        Index('idx_timestamp_desc', timestamp.desc()),
    )


class GovernanceSnapshotDB(Base):
    """Time-series snapshots of system-wide governance metrics"""
    __tablename__ = "governance_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    total_votes = Column(Integer, nullable=False)
    holder_votes = Column(Integer, nullable=False)
    seller_votes = Column(Integer, nullable=False)
    holder_control_percentage = Column(DECIMAL(5, 2), nullable=False)
    total_wallets = Column(Integer, nullable=False)
    holder_wallets = Column(Integer, nullable=False)
    seller_wallets = Column(Integer, nullable=False)

    __table_args__ = (
        Index('idx_snapshot_timestamp_desc', timestamp.desc()),
    )


# Database initialization

async def init_db():
    """Create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
