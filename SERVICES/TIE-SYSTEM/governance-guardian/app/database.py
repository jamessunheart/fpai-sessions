"""
Database models and configuration
"""

import os
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, Boolean, Text, Index
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/tie_governance"
)

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# Database Models

class GovernanceAlertDB(Base):
    """Governance alerts for threshold violations"""
    __tablename__ = "governance_alerts"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    alert_type = Column(String(20), nullable=False)  # caution|warning|critical|emergency
    holder_control = Column(DECIMAL(5, 2), nullable=False)
    message = Column(Text, nullable=False)
    action_taken = Column(String(50), nullable=False)
    resolved = Column(Boolean, nullable=False, default=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_alert_timestamp_desc', timestamp.desc()),
        Index('idx_alert_resolved', resolved),
    )


class GovernanceEventDB(Base):
    """Audit log of all governance events"""
    __tablename__ = "governance_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    event_type = Column(String(30), nullable=False, index=True)  # governance_check|threshold_crossed|pause|resume
    holder_control = Column(DECIMAL(5, 2), nullable=False)
    threshold_level = Column(String(20), nullable=False)  # excellent|good|acceptable|caution|warning|critical
    action = Column(String(50), nullable=False)  # none|alert|pause|resume
    details = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_event_timestamp_desc', timestamp.desc()),
        Index('idx_event_type', event_type),
    )


class SystemPauseDB(Base):
    """System pause/resume tracking"""
    __tablename__ = "system_pauses"

    id = Column(Integer, primary_key=True, index=True)
    paused_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    resumed_at = Column(DateTime, nullable=True)
    pause_reason = Column(Text, nullable=False)
    pause_type = Column(String(20), nullable=False)  # automatic|manual
    holder_control_at_pause = Column(DECIMAL(5, 2), nullable=False)
    resumed_by = Column(String(100), nullable=True)
    resume_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_pause_timestamp_desc', paused_at.desc()),
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
