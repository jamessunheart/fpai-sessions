"""
FP Credits Gateway - Persistence Layer
Provides persistent storage for the CreditStore using SQLite.

This module wraps the in-memory CreditStore to automatically save/load
data from the database, ensuring data survives service restarts.
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import (
    async_session, init_db, engine, Base,
    Account, Transaction, Expense, ManualAsset, AuditBlock,
    ExpenseRepository, ManualAssetRepository, AuditBlockRepository
)

logger = logging.getLogger("fp-credits-persistence")


class PersistenceManager:
    """
    Manages persistence operations for the CreditStore.
    
    Design:
    - Load all data from DB on startup
    - Write-through: every mutation is immediately persisted
    - Graceful fallback: if DB fails, log warning and continue in-memory
    """
    
    def __init__(self):
        self._initialized = False
        self._db_available = False
    
    async def initialize(self) -> bool:
        """Initialize the database and return True if successful."""
        try:
            await init_db()
            self._db_available = True
            self._initialized = True
            logger.info("✅ Persistence layer initialized (SQLite)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize persistence: {e}")
            self._db_available = False
            return False
    
    @asynccontextmanager
    async def get_session(self):
        """Get a database session with automatic cleanup."""
        if not self._db_available:
            yield None
            return
        
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error: {e}")
                raise
    
    # =========================================================
    # EXPENSE OPERATIONS
    # =========================================================
    
    async def save_expense(self, expense: dict) -> bool:
        """Save an expense to the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return False
                
                repo = ExpenseRepository(session)
                await repo.create(
                    expense_id=expense.get("id", f"exp_{datetime.utcnow().timestamp()}"),
                    category=expense["category"],
                    amount_usd=expense["amount_usd"],
                    description=expense.get("description"),
                    source=expense.get("source"),
                    expense_date=datetime.fromisoformat(expense["timestamp"]) if expense.get("timestamp") else None
                )
                return True
        except Exception as e:
            logger.error(f"Failed to save expense: {e}")
            return False
    
    async def load_expenses(self) -> List[dict]:
        """Load all expenses from the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return []
                
                repo = ExpenseRepository(session)
                expenses = await repo.get_all()
                return [e.to_dict() for e in expenses]
        except Exception as e:
            logger.error(f"Failed to load expenses: {e}")
            return []
    
    # =========================================================
    # MANUAL ASSET OPERATIONS
    # =========================================================
    
    async def save_manual_asset(self, asset_id: str, asset: dict) -> bool:
        """Save or update a manual asset in the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return False
                
                repo = ManualAssetRepository(session)
                await repo.upsert(
                    asset_id=asset_id,
                    asset_type=asset["type"],
                    symbol=asset["symbol"],
                    amount=asset["amount"],
                    location=asset.get("location")
                )
                return True
        except Exception as e:
            logger.error(f"Failed to save manual asset: {e}")
            return False
    
    async def load_manual_assets(self) -> Dict[str, dict]:
        """Load all manual assets from the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return {}
                
                repo = ManualAssetRepository(session)
                assets = await repo.get_all()
                return {a.asset_id: a.to_dict() for a in assets}
        except Exception as e:
            logger.error(f"Failed to load manual assets: {e}")
            return {}
    
    # =========================================================
    # AUDIT BLOCK OPERATIONS
    # =========================================================
    
    async def save_audit_block(self, block: dict) -> bool:
        """Save an audit block to the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return False
                
                repo = AuditBlockRepository(session)
                await repo.create(
                    block_id=block.get("block_id", f"blk_{datetime.utcnow().timestamp()}"),
                    prev_hash=block["prev_hash"],
                    block_hash=block["block_hash"],
                    event_type=block["event_type"],
                    event_data=block.get("data", {})
                )
                return True
        except Exception as e:
            logger.error(f"Failed to save audit block: {e}")
            return False
    
    async def load_audit_blocks(self, limit: int = 100) -> List[dict]:
        """Load recent audit blocks from the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return []
                
                repo = AuditBlockRepository(session)
                blocks = await repo.get_latest(limit)
                # Reverse to get chronological order
                return [b.to_dict() for b in reversed(blocks)]
        except Exception as e:
            logger.error(f"Failed to load audit blocks: {e}")
            return []
    
    async def get_last_block_hash(self) -> str:
        """Get the hash of the last audit block."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return "GENESIS_BLOCK"
                
                repo = AuditBlockRepository(session)
                return await repo.get_last_hash()
        except Exception as e:
            logger.error(f"Failed to get last block hash: {e}")
            return "GENESIS_BLOCK"
    
    # =========================================================
    # ACCOUNT OPERATIONS
    # =========================================================
    
    async def save_account(self, account_id: str, account_data: dict) -> bool:
        """Save or update an account in the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return False
                
                result = await session.execute(
                    select(Account).where(Account.account_id == account_id)
                )
                db_account = result.scalar_one_or_none()
                
                if db_account:
                    # Update existing
                    db_account.display_name = account_data.get("display_name")
                    db_account.email = account_data.get("email")
                    db_account.balance_fp = account_data.get("balances", {}).get("fp_credits", 0.0)
                    db_account.balance_cora = account_data.get("balances", {}).get("cora", 0.0)
                    db_account.balance_usd = account_data.get("balances", {}).get("usd", 0.0)
                    db_account.is_active = account_data.get("is_active", True)
                    db_account.extra_data = account_data.get("metadata", {})
                else:
                    # Create new
                    db_account = Account(
                        account_id=account_id,
                        account_type=account_data.get("account_type", "user"),
                        display_name=account_data.get("display_name"),
                        email=account_data.get("email"),
                        balance_fp=account_data.get("balances", {}).get("fp_credits", 0.0),
                        balance_cora=account_data.get("balances", {}).get("cora", 0.0),
                        balance_usd=account_data.get("balances", {}).get("usd", 0.0),
                        is_active=account_data.get("is_active", True),
                        metadata=account_data.get("metadata", {})
                    )
                    session.add(db_account)
                
                return True
        except Exception as e:
            logger.error(f"Failed to save account {account_id}: {e}")
            return False
    
    async def load_accounts(self) -> Dict[str, dict]:
        """Load all accounts from the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return {}
                
                result = await session.execute(select(Account))
                accounts = result.scalars().all()
                
                loaded = {}
                for acc in accounts:
                    loaded[acc.account_id] = {
                        "account_id": acc.account_id,
                        "account_type": acc.account_type,
                        "display_name": acc.display_name,
                        "email": acc.email,
                        "balances": {
                            "fp_credits": acc.balance_fp or 0.0,
                            "cora": acc.balance_cora or 0.0,
                            "usd": acc.balance_usd or 0.0
                        },
                        "is_active": acc.is_active,
                        "metadata": acc.extra_data or {},
                        "created_at": acc.created_at.isoformat() if acc.created_at else None,
                        "last_activity": acc.last_activity.isoformat() if acc.last_activity else None
                    }
                
                return loaded
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")
            return {}
    
    # =========================================================
    # TRANSACTION OPERATIONS
    # =========================================================
    
    async def save_transaction(self, tx: dict) -> bool:
        """Save a transaction to the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return False
                
                db_tx = Transaction(
                    transaction_id=tx["transaction_id"],
                    account_id=tx["account_id"],
                    type=tx["type"],
                    credit_type=tx["credit_type"],
                    amount=tx["amount"],
                    balance_before=tx["balance_before"],
                    balance_after=tx["balance_after"],
                    reason=tx.get("reason"),
                    reference_id=tx.get("reference_id"),
                    counterparty_id=tx.get("counterparty"),
                    status=tx.get("status", "completed"),
                    extra_data=tx.get("metadata", {}),
                    source_service=tx.get("source_service")
                )
                session.add(db_tx)
                return True
        except Exception as e:
            logger.error(f"Failed to save transaction: {e}")
            return False
    
    async def load_transactions(self, limit: int = 1000) -> List[dict]:
        """Load recent transactions from the database."""
        try:
            async with self.get_session() as session:
                if session is None:
                    return []
                
                result = await session.execute(
                    select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)
                )
                transactions = result.scalars().all()
                return [tx.to_dict() for tx in reversed(transactions)]
        except Exception as e:
            logger.error(f"Failed to load transactions: {e}")
            return []


# Global persistence manager instance
_persistence: Optional[PersistenceManager] = None


def get_persistence() -> PersistenceManager:
    """Get the global persistence manager instance."""
    global _persistence
    if _persistence is None:
        _persistence = PersistenceManager()
    return _persistence


async def init_persistence() -> PersistenceManager:
    """Initialize and return the persistence manager."""
    pm = get_persistence()
    await pm.initialize()
    return pm

