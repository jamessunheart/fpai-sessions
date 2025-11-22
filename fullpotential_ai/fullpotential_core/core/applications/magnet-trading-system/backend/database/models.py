"""
SQLAlchemy database models for Magnet Trading System
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Position(Base):
    """Trading positions table"""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)
    size_usd = Column(Float, nullable=False)
    leverage = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_price = Column(Float)
    target_price = Column(Float)
    magnet_tier = Column(Integer, CheckConstraint('magnet_tier BETWEEN 1 AND 4'))
    opened_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    closed_at = Column(DateTime, index=True)
    pnl = Column(Float)
    pnl_percent = Column(Float)
    closure_reason = Column(String(50))
    created_at = Column(DateTime, default=func.now())


class AccountSnapshot(Base):
    """Account state snapshots table"""
    __tablename__ = 'account_snapshots'

    id = Column(Integer, primary_key=True)
    equity = Column(Float, nullable=False)
    available_margin = Column(Float, nullable=False)
    open_positions_value = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    daily_pnl = Column(Float, nullable=False)
    leverage_used = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)


class MagnetDetection(Base):
    """Magnet detections table"""
    __tablename__ = 'magnet_detections'

    id = Column(Integer, primary_key=True)
    level = Column(Float, nullable=False)
    magnet_type = Column(String(20), nullable=False)
    strength = Column(Float, nullable=False)
    conflict = Column(Float, nullable=False)
    distance_atr = Column(Float, nullable=False)
    volatility_pressure = Column(Float, nullable=False)
    tier = Column(Integer, nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    detected_at = Column(DateTime, nullable=False, default=func.now(), index=True)


class FuseEvent(Base):
    """Survival fuse events table"""
    __tablename__ = 'fuse_events'

    id = Column(Integer, primary_key=True)
    trigger_type = Column(String(30), nullable=False)
    severity = Column(String(20), nullable=False)
    daily_loss_percent = Column(Float)
    action_taken = Column(String(100))
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)


class Investor(Base):
    """Investor accounts table"""
    __tablename__ = 'investors'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    share_percent = Column(Float, nullable=False)
    initial_investment = Column(Float, nullable=False)
    investment_date = Column(DateTime, nullable=False)
    kyc_verified = Column(Boolean, default=False)
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=func.now())


class InvestorSnapshot(Base):
    """Investor performance tracking table"""
    __tablename__ = 'investor_snapshots'

    id = Column(Integer, primary_key=True)
    investor_id = Column(Integer, ForeignKey('investors.id'), index=True)
    equity_value = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    return_percent = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)


class SystemConfig(Base):
    """System configuration table"""
    __tablename__ = 'system_config'

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=func.now())


class IdempotencyKey(Base):
    """Idempotency tracking table"""
    __tablename__ = 'idempotency_keys'

    key = Column(String(255), primary_key=True)
    response_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)
