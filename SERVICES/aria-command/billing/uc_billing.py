"""
UC Credit Billing Manager
Handles subscription billing and performance fees for Aria Trading Services.
"""

import os
import sqlite3
import logging
import httpx
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Commons Reserve allocation (30% of all trading fees)
# Per TOKENS_STRATEGY.md and REVENUE_FLOW_INTEGRATION.md
COMMONS_ALLOCATION_PCT = 0.30


class SubscriptionPlan(Enum):
    """Available subscription plans."""
    STEWARD_MONTHLY = "steward_monthly"  # 100 UC/month
    TRUSTEE_PERFORMANCE = "trustee_performance"  # 10% of gains


@dataclass
class BillingTransaction:
    """A billing transaction record."""
    id: int
    user_id: str
    transaction_type: str  # subscription, performance_fee, credit_add, refund
    amount: float
    description: str
    balance_before: float
    balance_after: float
    reference_id: Optional[str]
    created_at: datetime


class UCBillingManager:
    """
    Manages UC credit billing for Aria Trading Services.
    Integrates with FP Credits Gateway for balance management.
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
            "BILLING_DB_PATH",
            "/opt/fpai/aria-command/data/billing.db"
        ))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # FP Credits Gateway configuration
        self.gateway_url = os.getenv(
            "FP_CREDITS_GATEWAY_URL",
            "https://fullpotential.ai/services/credits/api"
        )
        self.gateway_api_key = os.getenv("FP_CREDITS_API_KEY", "")
        
        # Pricing
        self.steward_monthly_fee = float(os.getenv("STEWARD_MONTHLY_FEE", "100"))
        self.trustee_performance_fee = float(os.getenv("TRUSTEE_PERFORMANCE_FEE", "0.10"))
        
        # Commons Reserve allocation
        self.commons_allocation = COMMONS_ALLOCATION_PCT
        self.commons_ledger_account = "system:commons"
        
        self._init_db()
        self._initialized = True
        logger.info("UC Billing Manager initialized")
    
    def _init_db(self):
        """Initialize the billing database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS balances (
                    user_id TEXT PRIMARY KEY,
                    balance REAL DEFAULT 0,
                    lifetime_credits REAL DEFAULT 0,
                    lifetime_spent REAL DEFAULT 0,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    balance_before REAL,
                    balance_after REAL,
                    reference_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES balances(user_id)
                );
                
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    started_at TEXT,
                    next_billing_date TEXT,
                    last_billed_at TEXT,
                    cancelled_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES balances(user_id)
                );
                
                CREATE TABLE IF NOT EXISTS performance_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    period_start TEXT,
                    period_end TEXT,
                    starting_value REAL,
                    ending_value REAL,
                    gain_amount REAL,
                    fee_amount REAL,
                    fee_charged INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES balances(user_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
                CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
                
                CREATE TABLE IF NOT EXISTS commons_contributions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    fee_type TEXT NOT NULL,
                    fee_amount REAL NOT NULL,
                    commons_amount REAL NOT NULL,
                    synced_to_gateway INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
    
    def get_balance(self, user_id: str) -> float:
        """Get user's UC credit balance."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT balance FROM balances WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            return row[0] if row else 0.0
    
    def _update_balance(
        self,
        user_id: str,
        amount: float,
        transaction_type: str,
        description: str,
        reference_id: Optional[str] = None
    ) -> bool:
        """
        Update user balance and record transaction.
        Positive amount = add credits, negative = deduct.
        """
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Get current balance (create if doesn't exist)
            row = conn.execute(
                "SELECT balance FROM balances WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if row:
                current_balance = row[0]
            else:
                current_balance = 0.0
                conn.execute(
                    "INSERT INTO balances (user_id, balance, last_updated) VALUES (?, 0, ?)",
                    (user_id, now)
                )
            
            new_balance = current_balance + amount
            
            # Check for sufficient balance on deductions
            if amount < 0 and new_balance < 0:
                logger.warning(f"Insufficient balance for user {user_id}: {current_balance} + {amount}")
                return False
            
            # Update balance
            conn.execute("""
                UPDATE balances 
                SET balance = ?, 
                    lifetime_credits = lifetime_credits + ?,
                    lifetime_spent = lifetime_spent + ?,
                    last_updated = ?
                WHERE user_id = ?
            """, (
                new_balance,
                max(0, amount),  # Only positive for credits
                max(0, -amount),  # Only positive for spending
                now,
                user_id
            ))
            
            # Record transaction
            conn.execute("""
                INSERT INTO transactions 
                (user_id, transaction_type, amount, description, balance_before, balance_after, reference_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, transaction_type, amount, description, current_balance, new_balance, reference_id, now))
            
            logger.info(f"Balance updated for {user_id}: {current_balance} -> {new_balance} ({transaction_type})")
            return True
    
    def add_credits(
        self,
        user_id: str,
        amount: float,
        description: str = "Credit purchase",
        reference_id: Optional[str] = None
    ) -> bool:
        """Add UC credits to user's account."""
        return self._update_balance(
            user_id, amount, "credit_add", description, reference_id
        )
    
    async def _contribute_to_commons(
        self, 
        user_id: str, 
        fee_type: str,
        fee_amount: float
    ) -> Dict[str, Any]:
        """
        Contribute portion of fee to Commons Reserve.
        30% of all trading fees flow to Commons per TOKENS_STRATEGY.md.
        """
        commons_amount = fee_amount * self.commons_allocation
        
        # Record locally
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO commons_contributions 
                (user_id, fee_type, fee_amount, commons_amount, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, fee_type, fee_amount, commons_amount, datetime.now().isoformat()))
        
        # Try to sync to Credits Gateway
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.gateway_url}/commons/credit",
                    headers={"Authorization": f"Bearer {self.gateway_api_key}"},
                    json={
                        "amount": commons_amount,
                        "source": f"trading_{fee_type}",
                        "user_id": user_id,
                        "metadata": {
                            "fee_type": fee_type,
                            "original_fee": fee_amount,
                            "allocation_pct": self.commons_allocation
                        }
                    }
                )
                
                if response.status_code == 200:
                    # Mark as synced
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("""
                            UPDATE commons_contributions 
                            SET synced_to_gateway = 1 
                            WHERE user_id = ? AND created_at = (
                                SELECT MAX(created_at) FROM commons_contributions WHERE user_id = ?
                            )
                        """, (user_id, user_id))
                    
                    logger.info(f"Commons contribution: {commons_amount:.2f} UC from {fee_type} fee ({user_id})")
                    return {"success": True, "amount": commons_amount, "synced": True}
                    
        except Exception as e:
            logger.warning(f"Failed to sync commons contribution to gateway: {e}")
        
        # Still successful locally even if gateway sync fails
        return {"success": True, "amount": commons_amount, "synced": False}
    
    def charge_subscription(self, user_id: str) -> Dict[str, Any]:
        """
        Charge monthly subscription fee (Tier 1 Steward).
        Returns result of charge attempt.
        """
        amount = -self.steward_monthly_fee
        
        success = self._update_balance(
            user_id,
            amount,
            "subscription",
            f"Monthly Steward subscription ({self.steward_monthly_fee} UC)"
        )
        
        if success:
            # Update subscription record
            now = datetime.now()
            next_billing = now + timedelta(days=30)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE subscriptions 
                    SET last_billed_at = ?, next_billing_date = ?
                    WHERE user_id = ? AND plan = 'steward_monthly' AND status = 'active'
                """, (now.isoformat(), next_billing.isoformat(), user_id))
            
            # Contribute to Commons Reserve (30% of fee)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._contribute_to_commons(
                        user_id, "subscription", self.steward_monthly_fee
                    ))
                else:
                    loop.run_until_complete(self._contribute_to_commons(
                        user_id, "subscription", self.steward_monthly_fee
                    ))
            except Exception as e:
                logger.warning(f"Failed to schedule commons contribution: {e}")
            
            return {
                "success": True,
                "amount": self.steward_monthly_fee,
                "commons_contribution": self.steward_monthly_fee * self.commons_allocation,
                "next_billing": next_billing.isoformat()
            }
        
        return {
            "success": False,
            "error": "Insufficient UC balance",
            "required": self.steward_monthly_fee,
            "balance": self.get_balance(user_id)
        }
    
    def charge_performance_fee(
        self,
        user_id: str,
        gain_amount: float,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Charge performance fee (Tier 2 Trustee).
        Only charges on positive gains.
        30% of fee goes to Commons Reserve.
        """
        if gain_amount <= 0:
            return {
                "success": True,
                "fee": 0,
                "message": "No gains, no fee"
            }
        
        fee_amount = gain_amount * self.trustee_performance_fee
        
        # Record performance period
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO performance_tracking 
                (user_id, period_start, period_end, gain_amount, fee_amount, fee_charged)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (user_id, period_start.isoformat(), period_end.isoformat(), gain_amount, fee_amount))
        
        # Deduct fee
        success = self._update_balance(
            user_id,
            -fee_amount,
            "performance_fee",
            f"Performance fee ({self.trustee_performance_fee*100:.0f}% of ${gain_amount:.2f} gain)"
        )
        
        if success:
            # Contribute to Commons Reserve (30% of fee)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._contribute_to_commons(
                        user_id, "performance", fee_amount
                    ))
                else:
                    loop.run_until_complete(self._contribute_to_commons(
                        user_id, "performance", fee_amount
                    ))
            except Exception as e:
                logger.warning(f"Failed to schedule commons contribution: {e}")
            
            return {
                "success": True,
                "gain": gain_amount,
                "fee_rate": self.trustee_performance_fee,
                "fee_amount": fee_amount,
                "commons_contribution": fee_amount * self.commons_allocation
            }
        
        return {
            "success": False,
            "error": "Insufficient UC balance for fee",
            "fee_due": fee_amount
        }
    
    def create_subscription(
        self,
        user_id: str,
        plan: SubscriptionPlan
    ) -> Dict[str, Any]:
        """Create a new subscription for a user."""
        now = datetime.now()
        next_billing = now + timedelta(days=30) if plan == SubscriptionPlan.STEWARD_MONTHLY else None
        
        with sqlite3.connect(self.db_path) as conn:
            # Check for existing subscription
            existing = conn.execute(
                "SELECT id FROM subscriptions WHERE user_id = ? AND plan = ? AND status = 'active'",
                (user_id, plan.value)
            ).fetchone()
            
            if existing:
                return {"success": False, "error": "Subscription already exists"}
            
            conn.execute("""
                INSERT INTO subscriptions (user_id, plan, status, started_at, next_billing_date)
                VALUES (?, ?, 'active', ?, ?)
            """, (user_id, plan.value, now.isoformat(), next_billing.isoformat() if next_billing else None))
        
        # Charge first month for Steward
        if plan == SubscriptionPlan.STEWARD_MONTHLY:
            charge_result = self.charge_subscription(user_id)
            if not charge_result["success"]:
                # Cancel subscription if can't pay
                self.cancel_subscription(user_id, plan)
                return {
                    "success": False,
                    "error": "Insufficient balance for first month",
                    "required": self.steward_monthly_fee
                }
        
        logger.info(f"Created subscription for {user_id}: {plan.value}")
        return {
            "success": True,
            "plan": plan.value,
            "started_at": now.isoformat(),
            "next_billing": next_billing.isoformat() if next_billing else None
        }
    
    def cancel_subscription(
        self,
        user_id: str,
        plan: SubscriptionPlan
    ) -> bool:
        """Cancel a subscription."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                UPDATE subscriptions 
                SET status = 'cancelled', cancelled_at = ?
                WHERE user_id = ? AND plan = ? AND status = 'active'
            """, (now, user_id, plan.value))
            
            if result.rowcount > 0:
                logger.info(f"Cancelled subscription for {user_id}: {plan.value}")
                return True
        return False
    
    def get_subscription_status(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all subscriptions for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM subscriptions WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_transactions(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[BillingTransaction]:
        """Get transaction history for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            
            return [
                BillingTransaction(
                    id=row["id"],
                    user_id=row["user_id"],
                    transaction_type=row["transaction_type"],
                    amount=row["amount"],
                    description=row["description"],
                    balance_before=row["balance_before"],
                    balance_after=row["balance_after"],
                    reference_id=row["reference_id"],
                    created_at=datetime.fromisoformat(row["created_at"])
                )
                for row in rows
            ]
    
    def get_billing_summary(self, user_id: str) -> Dict[str, Any]:
        """Get billing summary for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Balance info
            balance_row = conn.execute(
                "SELECT * FROM balances WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            # Active subscriptions
            subs = conn.execute(
                "SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active'",
                (user_id,)
            ).fetchall()
            
            # Recent transactions
            transactions = conn.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,)).fetchall()
            
            return {
                "user_id": user_id,
                "balance": balance_row["balance"] if balance_row else 0,
                "lifetime_credits": balance_row["lifetime_credits"] if balance_row else 0,
                "lifetime_spent": balance_row["lifetime_spent"] if balance_row else 0,
                "active_subscriptions": [dict(row) for row in subs],
                "recent_transactions": [dict(row) for row in transactions]
            }
    
    async def process_due_subscriptions(self) -> Dict[str, Any]:
        """Process all subscriptions that are due for billing."""
        now = datetime.now()
        results = {"processed": 0, "success": 0, "failed": 0, "details": []}
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Find due subscriptions
            due_subs = conn.execute("""
                SELECT * FROM subscriptions 
                WHERE status = 'active' 
                AND plan = 'steward_monthly'
                AND next_billing_date <= ?
            """, (now.isoformat(),)).fetchall()
            
            for sub in due_subs:
                results["processed"] += 1
                user_id = sub["user_id"]
                
                charge_result = self.charge_subscription(user_id)
                
                if charge_result["success"]:
                    results["success"] += 1
                    results["details"].append({
                        "user_id": user_id,
                        "status": "success",
                        "amount": charge_result["amount"]
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "user_id": user_id,
                        "status": "failed",
                        "error": charge_result["error"]
                    })
                    
                    # Optionally suspend trading for failed payments
                    # self._handle_failed_payment(user_id)
        
        logger.info(f"Processed subscriptions: {results['processed']} total, {results['success']} success, {results['failed']} failed")
        return results
    
    async def sync_with_gateway(self, user_id: str) -> Dict[str, Any]:
        """
        Sync local balance with FP Credits Gateway.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.gateway_url}/balance/{user_id}",
                    headers={"Authorization": f"Bearer {self.gateway_api_key}"}
                )
                
                if response.status_code == 200:
                    gateway_balance = response.json().get("balance", 0)
                    
                    # Update local balance
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("""
                            INSERT INTO balances (user_id, balance, last_updated)
                            VALUES (?, ?, ?)
                            ON CONFLICT(user_id) DO UPDATE SET
                                balance = excluded.balance,
                                last_updated = excluded.last_updated
                        """, (user_id, gateway_balance, datetime.now().isoformat()))
                    
                    return {
                        "success": True,
                        "balance": gateway_balance
                    }
                
                return {
                    "success": False,
                    "error": f"Gateway returned {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Failed to sync with gateway: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_billing_manager: Optional[UCBillingManager] = None


def get_billing_manager() -> UCBillingManager:
    """Get the singleton billing manager instance."""
    global _billing_manager
    if _billing_manager is None:
        _billing_manager = UCBillingManager()
    return _billing_manager


def charge_subscription(user_id: str) -> Dict[str, Any]:
    """Charge monthly subscription fee."""
    return get_billing_manager().charge_subscription(user_id)


def charge_performance_fee(
    user_id: str,
    gain_amount: float,
    period_start: datetime,
    period_end: datetime
) -> Dict[str, Any]:
    """Charge performance fee."""
    return get_billing_manager().charge_performance_fee(
        user_id, gain_amount, period_start, period_end
    )


def get_user_balance(user_id: str) -> float:
    """Get user's UC balance."""
    return get_billing_manager().get_balance(user_id)


def add_credits(user_id: str, amount: float, description: str = "Credit purchase") -> bool:
    """Add credits to user's account."""
    return get_billing_manager().add_credits(user_id, amount, description)


async def get_commons_contribution_summary() -> Dict[str, Any]:
    """Get summary of Commons Reserve contributions from trading."""
    manager = get_billing_manager()
    
    with sqlite3.connect(manager.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Total contributions
        total = conn.execute("""
            SELECT 
                SUM(commons_amount) as total_contributed,
                COUNT(*) as total_contributions,
                SUM(CASE WHEN synced_to_gateway = 1 THEN commons_amount ELSE 0 END) as synced_amount,
                SUM(CASE WHEN synced_to_gateway = 0 THEN commons_amount ELSE 0 END) as pending_sync
            FROM commons_contributions
        """).fetchone()
        
        # By fee type
        by_type = conn.execute("""
            SELECT 
                fee_type,
                SUM(commons_amount) as amount,
                COUNT(*) as count
            FROM commons_contributions
            GROUP BY fee_type
        """).fetchall()
        
        # Recent contributions
        recent = conn.execute("""
            SELECT * FROM commons_contributions
            ORDER BY created_at DESC
            LIMIT 10
        """).fetchall()
        
        return {
            "total_contributed": total["total_contributed"] or 0,
            "total_contributions": total["total_contributions"] or 0,
            "synced_to_gateway": total["synced_amount"] or 0,
            "pending_sync": total["pending_sync"] or 0,
            "by_type": [dict(row) for row in by_type],
            "recent": [dict(row) for row in recent]
        }

