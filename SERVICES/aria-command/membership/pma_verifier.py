"""
PMA Membership Verification
Verifies Cora Nation PMA membership and trading eligibility for Aria services.
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MembershipStatus(Enum):
    """PMA Membership status levels."""
    ACTIVE = "active"
    PENDING = "pending"  # Signed but awaiting processing
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class MembershipTier(Enum):
    """Aria Trading Service tiers."""
    NONE = "none"  # Not signed up for trading
    STEWARD = "steward"  # Tier 1: Connected account
    TRUSTEE = "trustee"  # Tier 2: Pooled fund


@dataclass
class MemberProfile:
    """Member profile with membership and trading status."""
    user_id: str
    telegram_id: Optional[str]
    email: Optional[str]
    name: Optional[str]
    
    # PMA Status
    pma_status: MembershipStatus
    pma_joined_date: Optional[datetime]
    pma_expires_date: Optional[datetime]
    
    # Trading Status
    trading_tier: MembershipTier
    trading_addendum_signed: bool
    risk_disclosures_signed: bool
    pool_agreement_signed: bool  # Only for Tier 2
    
    # UC Balance
    uc_balance: float
    
    # Trading Activity
    trading_enabled: bool
    trading_started_date: Optional[datetime]
    last_trade_date: Optional[datetime]
    
    def is_eligible_for_trading(self) -> bool:
        """Check if member is eligible to use Aria Trading Services."""
        return (
            self.pma_status == MembershipStatus.ACTIVE and
            self.trading_addendum_signed and
            self.risk_disclosures_signed and
            (self.trading_tier == MembershipTier.STEWARD or 
             (self.trading_tier == MembershipTier.TRUSTEE and self.pool_agreement_signed))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "telegram_id": self.telegram_id,
            "email": self.email,
            "name": self.name,
            "pma_status": self.pma_status.value,
            "pma_joined_date": self.pma_joined_date.isoformat() if self.pma_joined_date else None,
            "pma_expires_date": self.pma_expires_date.isoformat() if self.pma_expires_date else None,
            "trading_tier": self.trading_tier.value,
            "trading_addendum_signed": self.trading_addendum_signed,
            "risk_disclosures_signed": self.risk_disclosures_signed,
            "pool_agreement_signed": self.pool_agreement_signed,
            "uc_balance": self.uc_balance,
            "trading_enabled": self.trading_enabled,
            "trading_started_date": self.trading_started_date.isoformat() if self.trading_started_date else None,
            "last_trade_date": self.last_trade_date.isoformat() if self.last_trade_date else None,
            "is_eligible": self.is_eligible_for_trading(),
        }


class PMAMembershipVerifier:
    """
    Verifies and manages PMA membership for Aria Trading Services.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.db_path = Path(os.getenv(
            "MEMBERSHIP_DB_PATH",
            "/opt/fpai/aria-command/data/membership.db"
        ))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._initialized = True
        logger.info("PMA Membership Verifier initialized")
    
    def _init_db(self):
        """Initialize the membership database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS members (
                    user_id TEXT PRIMARY KEY,
                    telegram_id TEXT UNIQUE,
                    email TEXT,
                    name TEXT,
                    pma_status TEXT DEFAULT 'unknown',
                    pma_joined_date TEXT,
                    pma_expires_date TEXT,
                    trading_tier TEXT DEFAULT 'none',
                    trading_addendum_signed INTEGER DEFAULT 0,
                    risk_disclosures_signed INTEGER DEFAULT 0,
                    pool_agreement_signed INTEGER DEFAULT 0,
                    uc_balance REAL DEFAULT 0,
                    trading_enabled INTEGER DEFAULT 0,
                    trading_started_date TEXT,
                    last_trade_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS document_signatures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    document_version TEXT NOT NULL,
                    signed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    signature_data TEXT,
                    FOREIGN KEY (user_id) REFERENCES members(user_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_members_telegram ON members(telegram_id);
                CREATE INDEX IF NOT EXISTS idx_signatures_user ON document_signatures(user_id);
            """)
    
    def get_member_by_telegram(self, telegram_id: str) -> Optional[MemberProfile]:
        """Get member profile by Telegram ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM members WHERE telegram_id = ?",
                (str(telegram_id),)
            ).fetchone()
            
            if row:
                return self._row_to_profile(row)
        return None
    
    def get_member_by_id(self, user_id: str) -> Optional[MemberProfile]:
        """Get member profile by user ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM members WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if row:
                return self._row_to_profile(row)
        return None
    
    def _row_to_profile(self, row: sqlite3.Row) -> MemberProfile:
        """Convert database row to MemberProfile."""
        return MemberProfile(
            user_id=row["user_id"],
            telegram_id=row["telegram_id"],
            email=row["email"],
            name=row["name"],
            pma_status=MembershipStatus(row["pma_status"]),
            pma_joined_date=datetime.fromisoformat(row["pma_joined_date"]) if row["pma_joined_date"] else None,
            pma_expires_date=datetime.fromisoformat(row["pma_expires_date"]) if row["pma_expires_date"] else None,
            trading_tier=MembershipTier(row["trading_tier"]),
            trading_addendum_signed=bool(row["trading_addendum_signed"]),
            risk_disclosures_signed=bool(row["risk_disclosures_signed"]),
            pool_agreement_signed=bool(row["pool_agreement_signed"]),
            uc_balance=row["uc_balance"] or 0,
            trading_enabled=bool(row["trading_enabled"]),
            trading_started_date=datetime.fromisoformat(row["trading_started_date"]) if row["trading_started_date"] else None,
            last_trade_date=datetime.fromisoformat(row["last_trade_date"]) if row["last_trade_date"] else None,
        )
    
    def register_member(
        self,
        telegram_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None
    ) -> MemberProfile:
        """Register a new member or update existing."""
        import uuid
        
        existing = self.get_member_by_telegram(telegram_id)
        if existing:
            return existing
        
        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO members (user_id, telegram_id, email, name, pma_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """, (user_id, str(telegram_id), email, name, now, now))
        
        logger.info(f"Registered new member: {user_id} (Telegram: {telegram_id})")
        return self.get_member_by_id(user_id)
    
    def activate_pma_membership(self, user_id: str, duration_days: int = 365) -> bool:
        """Activate PMA membership for a user."""
        now = datetime.now()
        expires = now + timedelta(days=duration_days)
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                UPDATE members 
                SET pma_status = 'active', 
                    pma_joined_date = ?,
                    pma_expires_date = ?,
                    updated_at = ?
                WHERE user_id = ?
            """, (now.isoformat(), expires.isoformat(), now.isoformat(), user_id))
            
            if result.rowcount > 0:
                logger.info(f"Activated PMA membership for user: {user_id}")
                return True
        return False
    
    def sign_document(
        self,
        user_id: str,
        document_type: str,
        document_version: str = "1.0.0",
        ip_address: Optional[str] = None,
        signature_data: Optional[str] = None
    ) -> bool:
        """Record a document signature."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Record signature
            conn.execute("""
                INSERT INTO document_signatures 
                (user_id, document_type, document_version, signed_at, ip_address, signature_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, document_type, document_version, now, ip_address, signature_data))
            
            # Update member flags
            if document_type == "trading_addendum":
                conn.execute(
                    "UPDATE members SET trading_addendum_signed = 1, updated_at = ? WHERE user_id = ?",
                    (now, user_id)
                )
            elif document_type == "risk_disclosures":
                conn.execute(
                    "UPDATE members SET risk_disclosures_signed = 1, updated_at = ? WHERE user_id = ?",
                    (now, user_id)
                )
            elif document_type == "pool_agreement":
                conn.execute(
                    "UPDATE members SET pool_agreement_signed = 1, updated_at = ? WHERE user_id = ?",
                    (now, user_id)
                )
            
            logger.info(f"Recorded signature for user {user_id}: {document_type}")
            return True
    
    def set_trading_tier(self, user_id: str, tier: MembershipTier) -> bool:
        """Set member's trading tier."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                UPDATE members 
                SET trading_tier = ?, updated_at = ?
                WHERE user_id = ?
            """, (tier.value, now, user_id))
            
            if result.rowcount > 0:
                logger.info(f"Set trading tier for user {user_id}: {tier.value}")
                return True
        return False
    
    def enable_trading(self, user_id: str) -> bool:
        """Enable trading for a member."""
        member = self.get_member_by_id(user_id)
        if not member:
            return False
        
        if not member.is_eligible_for_trading():
            logger.warning(f"User {user_id} not eligible for trading")
            return False
        
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE members 
                SET trading_enabled = 1, trading_started_date = ?, updated_at = ?
                WHERE user_id = ?
            """, (now, now, user_id))
            
            logger.info(f"Enabled trading for user: {user_id}")
            return True
    
    def disable_trading(self, user_id: str) -> bool:
        """Disable trading for a member."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                UPDATE members 
                SET trading_enabled = 0, updated_at = ?
                WHERE user_id = ?
            """, (now, user_id))
            
            if result.rowcount > 0:
                logger.info(f"Disabled trading for user: {user_id}")
                return True
        return False
    
    def update_uc_balance(self, user_id: str, new_balance: float) -> bool:
        """Update member's UC credit balance."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                UPDATE members 
                SET uc_balance = ?, updated_at = ?
                WHERE user_id = ?
            """, (new_balance, now, user_id))
            
            return result.rowcount > 0
    
    def record_trade(self, user_id: str) -> bool:
        """Record that a trade was made (updates last_trade_date)."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                UPDATE members 
                SET last_trade_date = ?, updated_at = ?
                WHERE user_id = ?
            """, (now, now, user_id))
            
            return result.rowcount > 0
    
    def get_all_active_traders(self) -> List[MemberProfile]:
        """Get all members with trading enabled."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM members WHERE trading_enabled = 1"
            ).fetchall()
            
            return [self._row_to_profile(row) for row in rows]
    
    def get_tier_members(self, tier: MembershipTier) -> List[MemberProfile]:
        """Get all members in a specific tier."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM members WHERE trading_tier = ?",
                (tier.value,)
            ).fetchall()
            
            return [self._row_to_profile(row) for row in rows]
    
    def check_eligibility(self, telegram_id: str) -> Dict[str, Any]:
        """
        Check trading eligibility for a Telegram user.
        Returns detailed status of what's needed.
        """
        member = self.get_member_by_telegram(telegram_id)
        
        if not member:
            return {
                "eligible": False,
                "registered": False,
                "message": "Not registered. Please join Cora Nation PMA first.",
                "next_steps": ["Register for PMA membership", "Sign trading documents"]
            }
        
        issues = []
        next_steps = []
        
        if member.pma_status != MembershipStatus.ACTIVE:
            issues.append(f"PMA membership status: {member.pma_status.value}")
            next_steps.append("Activate PMA membership")
        
        if not member.trading_addendum_signed:
            issues.append("Trading addendum not signed")
            next_steps.append("Sign Trading Services Addendum")
        
        if not member.risk_disclosures_signed:
            issues.append("Risk disclosures not signed")
            next_steps.append("Sign Risk Disclosures")
        
        if member.trading_tier == MembershipTier.TRUSTEE and not member.pool_agreement_signed:
            issues.append("Pool agreement not signed")
            next_steps.append("Sign Fellowship Pool Agreement")
        
        if member.trading_tier == MembershipTier.NONE:
            issues.append("No trading tier selected")
            next_steps.append("Select Steward or Trustee tier")
        
        eligible = len(issues) == 0
        
        return {
            "eligible": eligible,
            "registered": True,
            "user_id": member.user_id,
            "pma_status": member.pma_status.value,
            "trading_tier": member.trading_tier.value,
            "trading_enabled": member.trading_enabled,
            "uc_balance": member.uc_balance,
            "issues": issues,
            "next_steps": next_steps,
            "message": "Eligible for trading!" if eligible else f"Not eligible: {', '.join(issues)}"
        }


# Singleton instance
_verifier: Optional[PMAMembershipVerifier] = None


def get_verifier() -> PMAMembershipVerifier:
    """Get the singleton verifier instance."""
    global _verifier
    if _verifier is None:
        _verifier = PMAMembershipVerifier()
    return _verifier


def verify_member(telegram_id: str) -> Dict[str, Any]:
    """Verify a member's trading eligibility."""
    return get_verifier().check_eligibility(telegram_id)


def get_member_profile(telegram_id: str) -> Optional[MemberProfile]:
    """Get a member's profile."""
    return get_verifier().get_member_by_telegram(telegram_id)


def check_trading_eligibility(telegram_id: str) -> bool:
    """Quick check if member is eligible for trading."""
    result = verify_member(telegram_id)
    return result.get("eligible", False)









