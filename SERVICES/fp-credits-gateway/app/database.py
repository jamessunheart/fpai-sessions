"""
FP Credits Gateway - Database Layer
SQLite for development, PostgreSQL-ready for production.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, 
    ForeignKey, JSON, Enum, Index, create_engine
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, List, Any
import enum
import os
import json

# Database URL - SQLite for dev, PostgreSQL for production
DATABASE_URL = os.environ.get(
    "FP_CREDITS_DATABASE_URL",
    "sqlite+aiosqlite:///./fp_credits.db"
)

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


# ============================================================
# ENUMS
# ============================================================

class AccountType(str, enum.Enum):
    USER = "user"
    SERVICE = "service"
    EXTERNAL = "external"
    SYSTEM = "system"


class CreditType(str, enum.Enum):
    FP_CREDITS = "fp_credits"
    CORA_CREDITS = "cora_credits"
    USD = "usd"


class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    EXCHANGE = "exchange"
    PURCHASE = "purchase"
    REFUND = "refund"
    BONUS = "bonus"
    FEE = "fee"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


# ============================================================
# MODELS
# ============================================================

class Account(Base):
    """User/Service accounts with credit balances"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(255), unique=True, index=True, nullable=False)
    account_type = Column(String(50), default=AccountType.USER)
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Balances for each credit type
    balance_fp = Column(Float, default=0.0)
    balance_cora = Column(Float, default=0.0)
    balance_usd = Column(Float, default=0.0)
    
    # Pending amounts (for holds/reservations)
    pending_fp = Column(Float, default=0.0)
    pending_cora = Column(Float, default=0.0)
    pending_usd = Column(Float, default=0.0)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_activity = Column(DateTime, default=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="account")
    
    def get_balance(self, credit_type: CreditType) -> float:
        if credit_type == CreditType.FP_CREDITS:
            return self.balance_fp
        elif credit_type == CreditType.CORA_CREDITS:
            return self.balance_cora
        elif credit_type == CreditType.USD:
            return self.balance_usd
        return 0.0
    
    def set_balance(self, credit_type: CreditType, amount: float):
        if credit_type == CreditType.FP_CREDITS:
            self.balance_fp = amount
        elif credit_type == CreditType.CORA_CREDITS:
            self.balance_cora = amount
        elif credit_type == CreditType.USD:
            self.balance_usd = amount
    
    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "account_type": self.account_type,
            "display_name": self.display_name,
            "balances": {
                "fp_credits": self.balance_fp,
                "cora_credits": self.balance_cora,
                "usd": self.balance_usd
            },
            "pending": {
                "fp_credits": self.pending_fp,
                "cora_credits": self.pending_cora,
                "usd": self.pending_usd
            },
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None
        }


class Transaction(Base):
    """Immutable transaction ledger"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(64), unique=True, index=True, nullable=False)
    
    # Account reference
    account_id = Column(String(255), ForeignKey("accounts.account_id"), nullable=False)
    
    # Transaction details
    type = Column(String(50), nullable=False)
    credit_type = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)  # Positive = credit, Negative = debit
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    # Context
    reason = Column(String(500), nullable=True)
    reference_id = Column(String(255), nullable=True, index=True)
    reference_type = Column(String(50), nullable=True)
    
    # For transfers/exchanges
    counterparty_id = Column(String(255), nullable=True)
    related_transaction_id = Column(String(64), nullable=True)
    
    # Status
    status = Column(String(50), default=TransactionStatus.COMPLETED)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Source tracking
    source_service = Column(String(100), nullable=True)
    source_ip = Column(String(45), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Relationships
    account = relationship("Account", back_populates="transactions")
    
    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "type": self.type,
            "credit_type": self.credit_type,
            "amount": self.amount,
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
            "reason": self.reason,
            "reference_id": self.reference_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class APIKey(Base):
    """API keys for service authentication"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(64), unique=True, index=True, nullable=False)
    key_hash = Column(String(64), nullable=False)  # SHA-256 hash
    
    # Service info
    service_name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Permissions
    permissions = Column(JSON, default=list)  # ["read", "credit", "debit", etc.]
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=100)
    rate_limit_per_day = Column(Integer, default=10000)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)
    
    def to_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "service_name": self.service_name,
            "description": self.description,
            "permissions": self.permissions,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Webhook(Base):
    """Webhook subscriptions for balance change notifications"""
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(String(64), unique=True, index=True, nullable=False)
    
    # Target
    url = Column(String(500), nullable=False)
    secret = Column(String(64), nullable=True)  # For signature verification
    
    # Subscription
    account_id = Column(String(255), nullable=True)  # null = all accounts
    event_types = Column(JSON, default=list)  # ["credit", "debit", "transfer"]
    
    # Status
    is_active = Column(Boolean, default=True)
    failure_count = Column(Integer, default=0)
    last_triggered = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())


class ExchangeRate(Base):
    """Historical exchange rates"""
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    from_type = Column(String(50), nullable=False)
    to_type = Column(String(50), nullable=False)
    rate = Column(Float, nullable=False)
    effective_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('ix_exchange_rate_lookup', 'from_type', 'to_type', 'effective_at'),
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create system accounts if they don't exist
    async with async_session() as session:
        from sqlalchemy import select
        
        system_accounts = [
            ("system:treasury", "FP Treasury", AccountType.SYSTEM, 1000000.0),
            ("system:fees", "Fee Collection", AccountType.SYSTEM, 0.0),
            ("system:rewards", "Rewards Pool", AccountType.SYSTEM, 100000.0),
        ]
        
        for acc_id, name, acc_type, initial_balance in system_accounts:
            result = await session.execute(
                select(Account).where(Account.account_id == acc_id)
            )
            if not result.scalar_one_or_none():
                account = Account(
                    account_id=acc_id,
                    account_type=acc_type,
                    display_name=name,
                    balance_fp=initial_balance,
                    is_active=True
                )
                session.add(account)
        
        await session.commit()


async def get_db():
    """Dependency for getting database session"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================
# REPOSITORY CLASSES
# ============================================================

class AccountRepository:
    """Repository for account operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, account_id: str) -> Optional[Account]:
        from sqlalchemy import select
        result = await self.session.execute(
            select(Account).where(Account.account_id == account_id)
        )
        return result.scalar_one_or_none()
    
    async def get_or_create(
        self, 
        account_id: str, 
        account_type: AccountType = AccountType.USER,
        display_name: str = None
    ) -> Account:
        account = await self.get_by_id(account_id)
        if not account:
            account = Account(
                account_id=account_id,
                account_type=account_type,
                display_name=display_name or account_id
            )
            self.session.add(account)
            await self.session.flush()
        return account
    
    async def update_balance(
        self, 
        account_id: str, 
        credit_type: CreditType, 
        delta: float
    ) -> Account:
        account = await self.get_or_create(account_id)
        current = account.get_balance(credit_type)
        new_balance = current + delta
        
        if new_balance < 0:
            raise ValueError(f"Insufficient balance. Has {current}, needs {abs(delta)}")
        
        account.set_balance(credit_type, new_balance)
        account.last_activity = datetime.utcnow()
        await self.session.flush()
        return account


class TransactionRepository:
    """Repository for transaction operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        account_id: str,
        transaction_type: TransactionType,
        credit_type: CreditType,
        amount: float,
        balance_before: float,
        balance_after: float,
        reason: str = None,
        reference_id: str = None,
        metadata: dict = None,
        source_service: str = None
    ) -> Transaction:
        import secrets
        
        transaction = Transaction(
            transaction_id=secrets.token_hex(16),
            account_id=account_id,
            type=transaction_type,
            credit_type=credit_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            reference_id=reference_id,
            metadata=metadata or {},
            source_service=source_service,
            status=TransactionStatus.COMPLETED
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction
    
    async def get_by_account(
        self, 
        account_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[Transaction]:
        from sqlalchemy import select
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def get_by_reference(self, reference_id: str) -> List[Transaction]:
        from sqlalchemy import select
        result = await self.session.execute(
            select(Transaction).where(Transaction.reference_id == reference_id)
        )
        return result.scalars().all()


