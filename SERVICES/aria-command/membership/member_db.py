"""
MEMBER DATABASE
================

SQLite database for PMA members, wallets, and transactions.

Tables:
- members: PMA membership records
- wallets: Credit balances (available + pool)
- transactions: All credit movements
- trading_pool: Pool totals and stats
- pool_contributions: Individual pool contributions
- pending_gifts: Gifts awaiting acceptance
"""

import os
import sqlite3
import uuid
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
from enum import Enum

logger = logging.getLogger("aria.membership.db")

# Database location
DB_PATH = os.getenv("MEMBER_DB_PATH", "/opt/fpai/aria-command/data/members.db")


class TransactionType(str, Enum):
    """Types of transactions."""
    GIFT = "gift"
    POOL_CONTRIBUTION = "pool_contribution"
    POOL_WITHDRAWAL = "pool_withdrawal"
    POOL_RETURN = "pool_return"
    PURCHASE = "purchase"
    REWARD = "reward"
    ADMIN_CREDIT = "admin_credit"
    ADMIN_DEBIT = "admin_debit"


class TransactionStatus(str, Enum):
    """Transaction statuses."""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class Member:
    """A PMA member."""
    id: str
    telegram_id: int
    telegram_username: Optional[str] = None
    display_name: Optional[str] = None
    pma_agreed_at: Optional[str] = None
    trading_agreed_at: Optional[str] = None
    referred_by: Optional[str] = None
    is_steward: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Wallet:
    """Member wallet with balances."""
    member_id: str
    available_credits: float = 0.0
    pool_credits: float = 0.0
    pool_share: float = 0.0
    total_earned: float = 0.0
    total_spent: float = 0.0
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def total_balance(self) -> float:
        return self.available_credits + self.pool_credits


@dataclass
class Transaction:
    """A credit transaction."""
    id: Optional[int] = None
    from_member: Optional[str] = None
    to_member: Optional[str] = None
    amount: float = 0.0
    type: TransactionType = TransactionType.GIFT
    status: TransactionStatus = TransactionStatus.PENDING
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class PendingGift:
    """A gift awaiting acceptance."""
    id: str
    from_member: str
    to_telegram_id: int
    to_telegram_username: Optional[str]
    amount: float
    message: Optional[str] = None
    expires_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass 
class TradingPool:
    """Trading pool totals."""
    total_credits: float = 0.0
    member_count: int = 0
    cumulative_pnl: float = 0.0
    last_return_distributed_at: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class MemberDB:
    """
    SQLite database for membership system.
    
    Handles:
    - Member registration and lookup
    - Wallet management
    - Transaction recording
    - Trading pool tracking
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db_directory()
        self._init_db()
        logger.info(f"MemberDB initialized at {self.db_path}")
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Members table
                CREATE TABLE IF NOT EXISTS members (
                    id TEXT PRIMARY KEY,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    telegram_username TEXT,
                    display_name TEXT,
                    pma_agreed_at TEXT,
                    trading_agreed_at TEXT,
                    referred_by TEXT,
                    is_steward BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (referred_by) REFERENCES members(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_members_telegram ON members(telegram_id);
                CREATE INDEX IF NOT EXISTS idx_members_username ON members(telegram_username);
                
                -- Wallets table
                CREATE TABLE IF NOT EXISTS wallets (
                    member_id TEXT PRIMARY KEY,
                    available_credits REAL DEFAULT 0,
                    pool_credits REAL DEFAULT 0,
                    pool_share REAL DEFAULT 0,
                    total_earned REAL DEFAULT 0,
                    total_spent REAL DEFAULT 0,
                    updated_at TEXT,
                    FOREIGN KEY (member_id) REFERENCES members(id)
                );
                
                -- Transactions table
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_member TEXT,
                    to_member TEXT,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    description TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (from_member) REFERENCES members(id),
                    FOREIGN KEY (to_member) REFERENCES members(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_tx_from ON transactions(from_member);
                CREATE INDEX IF NOT EXISTS idx_tx_to ON transactions(to_member);
                CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions(status);
                
                -- Trading pool table
                CREATE TABLE IF NOT EXISTS trading_pool (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_credits REAL DEFAULT 0,
                    member_count INTEGER DEFAULT 0,
                    cumulative_pnl REAL DEFAULT 0,
                    last_return_distributed_at TEXT,
                    updated_at TEXT
                );
                
                -- Initialize pool row if not exists
                INSERT OR IGNORE INTO trading_pool (id, total_credits, member_count, cumulative_pnl, updated_at)
                VALUES (1, 0, 0, 0, datetime('now'));
                
                -- Pool contributions
                CREATE TABLE IF NOT EXISTS pool_contributions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    share_at_contribution REAL,
                    action TEXT DEFAULT 'add',  -- add or withdraw
                    contributed_at TEXT NOT NULL,
                    FOREIGN KEY (member_id) REFERENCES members(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_contrib_member ON pool_contributions(member_id);
                
                -- Pending gifts (awaiting acceptance)
                CREATE TABLE IF NOT EXISTS pending_gifts (
                    id TEXT PRIMARY KEY,
                    from_member TEXT NOT NULL,
                    to_telegram_id INTEGER NOT NULL,
                    to_telegram_username TEXT,
                    amount REAL NOT NULL,
                    message TEXT,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (from_member) REFERENCES members(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_gift_to ON pending_gifts(to_telegram_id);
            """)
            logger.info("Member database schema initialized")
    
    # ========================================================================
    # MEMBER OPERATIONS
    # ========================================================================
    
    def create_member(self, member: Member) -> str:
        """Create a new member. Returns member ID."""
        if not member.id:
            member.id = str(uuid.uuid4())
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO members 
                (id, telegram_id, telegram_username, display_name, pma_agreed_at,
                 trading_agreed_at, referred_by, is_steward, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                member.id,
                member.telegram_id,
                member.telegram_username,
                member.display_name,
                member.pma_agreed_at,
                member.trading_agreed_at,
                member.referred_by,
                member.is_steward,
                member.created_at
            ))
            
            # Create wallet for member
            conn.execute("""
                INSERT INTO wallets (member_id, updated_at)
                VALUES (?, ?)
            """, (member.id, datetime.now().isoformat()))
            
            logger.info(f"Created member {member.id} (telegram: {member.telegram_id})")
        
        return member.id
    
    def get_member(self, member_id: str) -> Optional[Member]:
        """Get member by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM members WHERE id = ?",
                (member_id,)
            ).fetchone()
            
            return self._row_to_member(row) if row else None
    
    def get_member_by_telegram(self, telegram_id: int) -> Optional[Member]:
        """Get member by Telegram ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM members WHERE telegram_id = ?",
                (telegram_id,)
            ).fetchone()
            
            return self._row_to_member(row) if row else None
    
    def get_member_by_username(self, username: str) -> Optional[Member]:
        """Get member by Telegram username."""
        # Remove @ if present
        username = username.lstrip("@")
        
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM members WHERE LOWER(telegram_username) = LOWER(?)",
                (username,)
            ).fetchone()
            
            return self._row_to_member(row) if row else None
    
    def update_member(self, member_id: str, **updates) -> bool:
        """Update member fields."""
        if not updates:
            return False
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [member_id]
        
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE members SET {set_clause} WHERE id = ?",
                values
            )
            return True
    
    def agree_to_pma(self, member_id: str) -> bool:
        """Record PMA agreement."""
        return self.update_member(member_id, pma_agreed_at=datetime.now().isoformat())
    
    def agree_to_trading(self, member_id: str) -> bool:
        """Record trading agreement."""
        return self.update_member(member_id, trading_agreed_at=datetime.now().isoformat())
    
    def _row_to_member(self, row: sqlite3.Row) -> Member:
        """Convert database row to Member."""
        return Member(
            id=row["id"],
            telegram_id=row["telegram_id"],
            telegram_username=row["telegram_username"],
            display_name=row["display_name"],
            pma_agreed_at=row["pma_agreed_at"],
            trading_agreed_at=row["trading_agreed_at"],
            referred_by=row["referred_by"],
            is_steward=bool(row["is_steward"]),
            created_at=row["created_at"]
        )
    
    # ========================================================================
    # WALLET OPERATIONS
    # ========================================================================
    
    def get_wallet(self, member_id: str) -> Optional[Wallet]:
        """Get member wallet."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM wallets WHERE member_id = ?",
                (member_id,)
            ).fetchone()
            
            return self._row_to_wallet(row) if row else None
    
    def update_wallet(self, member_id: str, **updates) -> bool:
        """Update wallet fields."""
        updates["updated_at"] = datetime.now().isoformat()
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [member_id]
        
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE wallets SET {set_clause} WHERE member_id = ?",
                values
            )
            return True
    
    def add_credits(self, member_id: str, amount: float, to_pool: bool = False) -> bool:
        """Add credits to member wallet."""
        wallet = self.get_wallet(member_id)
        if not wallet:
            return False
        
        if to_pool:
            new_pool = wallet.pool_credits + amount
            return self.update_wallet(member_id, pool_credits=new_pool)
        else:
            new_available = wallet.available_credits + amount
            return self.update_wallet(member_id, available_credits=new_available)
    
    def deduct_credits(self, member_id: str, amount: float, from_pool: bool = False) -> bool:
        """Deduct credits from member wallet."""
        wallet = self.get_wallet(member_id)
        if not wallet:
            return False
        
        if from_pool:
            if wallet.pool_credits < amount:
                return False
            new_pool = wallet.pool_credits - amount
            return self.update_wallet(member_id, pool_credits=new_pool)
        else:
            if wallet.available_credits < amount:
                return False
            new_available = wallet.available_credits - amount
            return self.update_wallet(member_id, available_credits=new_available)
    
    def _row_to_wallet(self, row: sqlite3.Row) -> Wallet:
        """Convert database row to Wallet."""
        return Wallet(
            member_id=row["member_id"],
            available_credits=row["available_credits"] or 0,
            pool_credits=row["pool_credits"] or 0,
            pool_share=row["pool_share"] or 0,
            total_earned=row["total_earned"] or 0,
            total_spent=row["total_spent"] or 0,
            updated_at=row["updated_at"]
        )
    
    # ========================================================================
    # TRANSACTION OPERATIONS
    # ========================================================================
    
    def create_transaction(self, tx: Transaction) -> int:
        """Create a transaction. Returns transaction ID."""
        import json
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO transactions 
                (from_member, to_member, amount, type, status, description, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx.from_member,
                tx.to_member,
                tx.amount,
                tx.type.value if isinstance(tx.type, TransactionType) else tx.type,
                tx.status.value if isinstance(tx.status, TransactionStatus) else tx.status,
                tx.description,
                json.dumps(tx.metadata),
                tx.created_at
            ))
            return cursor.lastrowid
    
    def complete_transaction(self, tx_id: int) -> bool:
        """Mark transaction as completed."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE transactions SET 
                    status = ?,
                    completed_at = ?
                WHERE id = ?
            """, (TransactionStatus.COMPLETED.value, datetime.now().isoformat(), tx_id))
            return True
    
    def cancel_transaction(self, tx_id: int) -> bool:
        """Cancel a transaction."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE transactions SET status = ? WHERE id = ?",
                (TransactionStatus.CANCELLED.value, tx_id)
            )
            return True
    
    def get_transactions(self, member_id: str, limit: int = 50) -> List[Transaction]:
        """Get transactions for a member."""
        import json
        
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM transactions 
                WHERE from_member = ? OR to_member = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (member_id, member_id, limit)).fetchall()
            
            return [self._row_to_transaction(row) for row in rows]
    
    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        """Convert database row to Transaction."""
        import json
        return Transaction(
            id=row["id"],
            from_member=row["from_member"],
            to_member=row["to_member"],
            amount=row["amount"],
            type=TransactionType(row["type"]),
            status=TransactionStatus(row["status"]),
            description=row["description"],
            metadata=json.loads(row["metadata"] or "{}"),
            created_at=row["created_at"],
            completed_at=row["completed_at"]
        )
    
    # ========================================================================
    # PENDING GIFT OPERATIONS
    # ========================================================================
    
    def create_pending_gift(self, gift: PendingGift) -> str:
        """Create a pending gift. Returns gift ID."""
        if not gift.id:
            gift.id = str(uuid.uuid4())
        
        if not gift.expires_at:
            gift.expires_at = (datetime.now() + timedelta(days=7)).isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO pending_gifts 
                (id, from_member, to_telegram_id, to_telegram_username, amount, message, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gift.id,
                gift.from_member,
                gift.to_telegram_id,
                gift.to_telegram_username,
                gift.amount,
                gift.message,
                gift.expires_at,
                gift.created_at
            ))
            
            logger.info(f"Created pending gift {gift.id}: {gift.amount} UC to {gift.to_telegram_id}")
        
        return gift.id
    
    def get_pending_gift(self, gift_id: str) -> Optional[PendingGift]:
        """Get pending gift by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM pending_gifts WHERE id = ?",
                (gift_id,)
            ).fetchone()
            
            return self._row_to_gift(row) if row else None
    
    def get_pending_gifts_for_user(self, telegram_id: int) -> List[PendingGift]:
        """Get all pending gifts for a Telegram user."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM pending_gifts 
                WHERE to_telegram_id = ? AND expires_at > datetime('now')
                ORDER BY created_at DESC
            """, (telegram_id,)).fetchall()
            
            return [self._row_to_gift(row) for row in rows]
    
    def delete_pending_gift(self, gift_id: str) -> bool:
        """Delete a pending gift (after acceptance or expiry)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM pending_gifts WHERE id = ?", (gift_id,))
            return True
    
    def _row_to_gift(self, row: sqlite3.Row) -> PendingGift:
        """Convert database row to PendingGift."""
        return PendingGift(
            id=row["id"],
            from_member=row["from_member"],
            to_telegram_id=row["to_telegram_id"],
            to_telegram_username=row["to_telegram_username"],
            amount=row["amount"],
            message=row["message"],
            expires_at=row["expires_at"],
            created_at=row["created_at"]
        )
    
    # ========================================================================
    # TRADING POOL OPERATIONS
    # ========================================================================
    
    def get_pool(self) -> TradingPool:
        """Get trading pool info."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM trading_pool WHERE id = 1").fetchone()
            
            return TradingPool(
                total_credits=row["total_credits"] or 0,
                member_count=row["member_count"] or 0,
                cumulative_pnl=row["cumulative_pnl"] or 0,
                last_return_distributed_at=row["last_return_distributed_at"],
                updated_at=row["updated_at"]
            )
    
    def update_pool(self, **updates) -> bool:
        """Update pool totals."""
        updates["updated_at"] = datetime.now().isoformat()
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values())
        
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE trading_pool SET {set_clause} WHERE id = 1",
                values
            )
            return True
    
    def add_to_pool(self, member_id: str, amount: float) -> bool:
        """Add credits to pool and recalculate shares."""
        wallet = self.get_wallet(member_id)
        if not wallet or wallet.available_credits < amount:
            return False
        
        pool = self.get_pool()
        
        with self._get_connection() as conn:
            # Move credits from available to pool
            new_available = wallet.available_credits - amount
            new_pool_credits = wallet.pool_credits + amount
            
            conn.execute("""
                UPDATE wallets SET 
                    available_credits = ?,
                    pool_credits = ?,
                    updated_at = ?
                WHERE member_id = ?
            """, (new_available, new_pool_credits, datetime.now().isoformat(), member_id))
            
            # Update pool totals
            new_total = pool.total_credits + amount
            new_member_count = pool.member_count
            if wallet.pool_credits == 0:  # New pool member
                new_member_count += 1
            
            conn.execute("""
                UPDATE trading_pool SET 
                    total_credits = ?,
                    member_count = ?,
                    updated_at = ?
                WHERE id = 1
            """, (new_total, new_member_count, datetime.now().isoformat()))
            
            # Record contribution
            conn.execute("""
                INSERT INTO pool_contributions 
                (member_id, amount, share_at_contribution, action, contributed_at)
                VALUES (?, ?, ?, 'add', ?)
            """, (member_id, amount, new_pool_credits / new_total if new_total > 0 else 0, 
                  datetime.now().isoformat()))
        
        # Recalculate all shares
        self._recalculate_pool_shares()
        
        logger.info(f"Added {amount} UC to pool from {member_id}")
        return True
    
    def withdraw_from_pool(self, member_id: str, amount: float) -> bool:
        """Withdraw credits from pool."""
        wallet = self.get_wallet(member_id)
        if not wallet or wallet.pool_credits < amount:
            return False
        
        pool = self.get_pool()
        
        with self._get_connection() as conn:
            # Move credits from pool to available
            new_pool_credits = wallet.pool_credits - amount
            new_available = wallet.available_credits + amount
            
            conn.execute("""
                UPDATE wallets SET 
                    available_credits = ?,
                    pool_credits = ?,
                    updated_at = ?
                WHERE member_id = ?
            """, (new_available, new_pool_credits, datetime.now().isoformat(), member_id))
            
            # Update pool totals
            new_total = pool.total_credits - amount
            new_member_count = pool.member_count
            if new_pool_credits == 0:  # No longer in pool
                new_member_count -= 1
            
            conn.execute("""
                UPDATE trading_pool SET 
                    total_credits = ?,
                    member_count = ?,
                    updated_at = ?
                WHERE id = 1
            """, (new_total, max(0, new_member_count), datetime.now().isoformat()))
            
            # Record withdrawal
            conn.execute("""
                INSERT INTO pool_contributions 
                (member_id, amount, share_at_contribution, action, contributed_at)
                VALUES (?, ?, ?, 'withdraw', ?)
            """, (member_id, amount, new_pool_credits / new_total if new_total > 0 else 0,
                  datetime.now().isoformat()))
        
        # Recalculate all shares
        self._recalculate_pool_shares()
        
        logger.info(f"Withdrew {amount} UC from pool for {member_id}")
        return True
    
    def _recalculate_pool_shares(self):
        """Recalculate pool shares for all members."""
        pool = self.get_pool()
        total = pool.total_credits
        
        if total <= 0:
            return
        
        with self._get_connection() as conn:
            # Get all wallets with pool credits
            rows = conn.execute(
                "SELECT member_id, pool_credits FROM wallets WHERE pool_credits > 0"
            ).fetchall()
            
            for row in rows:
                share = row["pool_credits"] / total
                conn.execute(
                    "UPDATE wallets SET pool_share = ? WHERE member_id = ?",
                    (share, row["member_id"])
                )
    
    def get_pool_members(self) -> List[Tuple[str, Wallet]]:
        """Get all members in the pool with their wallets."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT m.*, w.* FROM members m
                JOIN wallets w ON m.id = w.member_id
                WHERE w.pool_credits > 0
                ORDER BY w.pool_credits DESC
            """).fetchall()
            
            result = []
            for row in rows:
                member = self._row_to_member(row)
                wallet = self._row_to_wallet(row)
                result.append((member.id, wallet))
            
            return result
    
    def distribute_pool_returns(self, pnl: float, operations_fee_pct: float = 0.10):
        """Distribute PnL to pool members pro-rata."""
        pool = self.get_pool()
        
        if pool.total_credits <= 0 or pnl == 0:
            return
        
        # Calculate distributions
        operations_fee = pnl * operations_fee_pct
        member_pnl = pnl - operations_fee
        
        pool_members = self.get_pool_members()
        
        with self._get_connection() as conn:
            for member_id, wallet in pool_members:
                # Pro-rata share of PnL
                member_return = member_pnl * wallet.pool_share
                
                # Update pool credits (can be negative if losing)
                new_pool_credits = max(0, wallet.pool_credits + member_return)
                
                conn.execute("""
                    UPDATE wallets SET 
                        pool_credits = ?,
                        total_earned = total_earned + ?,
                        updated_at = ?
                    WHERE member_id = ?
                """, (new_pool_credits, max(0, member_return), 
                      datetime.now().isoformat(), member_id))
                
                # Record transaction
                conn.execute("""
                    INSERT INTO transactions 
                    (from_member, to_member, amount, type, status, description, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    None,  # from pool
                    member_id,
                    member_return,
                    TransactionType.POOL_RETURN.value,
                    TransactionStatus.COMPLETED.value,
                    f"Pool return: {member_return:+.2f} UC ({wallet.pool_share:.1%} share)",
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            # Update pool totals
            new_total = max(0, pool.total_credits + member_pnl)
            conn.execute("""
                UPDATE trading_pool SET 
                    total_credits = ?,
                    cumulative_pnl = cumulative_pnl + ?,
                    last_return_distributed_at = ?,
                    updated_at = ?
                WHERE id = 1
            """, (new_total, pnl, datetime.now().isoformat(), datetime.now().isoformat()))
        
        # Recalculate shares
        self._recalculate_pool_shares()
        
        logger.info(f"Distributed {pnl} PnL to {len(pool_members)} pool members")
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get membership statistics."""
        with self._get_connection() as conn:
            member_count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
            pma_count = conn.execute(
                "SELECT COUNT(*) FROM members WHERE pma_agreed_at IS NOT NULL"
            ).fetchone()[0]
            trading_count = conn.execute(
                "SELECT COUNT(*) FROM members WHERE trading_agreed_at IS NOT NULL"
            ).fetchone()[0]
            
            total_credits = conn.execute(
                "SELECT SUM(available_credits + pool_credits) FROM wallets"
            ).fetchone()[0] or 0
            
            pool = self.get_pool()
            
            return {
                "total_members": member_count,
                "pma_members": pma_count,
                "trading_members": trading_count,
                "total_credits_in_system": total_credits,
                "pool": {
                    "total_credits": pool.total_credits,
                    "member_count": pool.member_count,
                    "cumulative_pnl": pool.cumulative_pnl
                }
            }


# ============================================================================
# SINGLETON
# ============================================================================

_db: Optional[MemberDB] = None


def get_member_db() -> MemberDB:
    """Get or create the member database instance."""
    global _db
    if _db is None:
        _db = MemberDB()
    return _db








