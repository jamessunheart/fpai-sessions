"""
POOL MANAGER
=============

Manages the Conscious Wealth Trading Pool.

Responsibilities:
- Track pool totals and member shares
- Distribute trading returns pro-rata
- Connect to Aria's trading system for PnL
- Handle contribution and withdrawal requests
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger("aria.trading.pool")

# Configuration
OPERATIONS_FEE_PCT = float(os.getenv("POOL_OPERATIONS_FEE", "0.10"))  # 10%
WHALETRACK_URL = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8601")


@dataclass
class PoolStatus:
    """Current pool status."""
    total_credits: float
    member_count: int
    cumulative_pnl: float
    todays_pnl: float
    last_distribution: Optional[str]
    aria_balance: float  # Actual trading balance


@dataclass
class MemberPoolStatus:
    """Member's pool status."""
    pool_credits: float
    pool_share: float
    total_earned: float
    share_value: float  # Current value based on pool performance


class PoolManager:
    """
    Manages the trading pool.
    
    Key features:
    - Connects member pool to Aria's Hyperliquid trading
    - Distributes returns daily (or after each trade)
    - Tracks member shares accurately
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._last_known_balance = 0.0
        self._last_balance_check = None
        logger.info("PoolManager initialized")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def get_pool_status(self) -> PoolStatus:
        """Get current pool status."""
        from membership import get_member_db
        
        db = get_member_db()
        pool = db.get_pool()
        
        # Get Aria's actual trading balance
        aria_balance = await self._get_aria_balance()
        
        # Calculate today's PnL (if we have a previous balance)
        todays_pnl = 0.0
        if self._last_known_balance > 0 and aria_balance > 0:
            todays_pnl = aria_balance - self._last_known_balance
        
        return PoolStatus(
            total_credits=pool.total_credits,
            member_count=pool.member_count,
            cumulative_pnl=pool.cumulative_pnl,
            todays_pnl=todays_pnl,
            last_distribution=pool.last_return_distributed_at,
            aria_balance=aria_balance
        )
    
    async def get_member_status(self, member_id: str) -> MemberPoolStatus:
        """Get a member's pool status."""
        from membership import get_member_db, get_wallet
        
        db = get_member_db()
        wallet = db.get_wallet(member_id)
        pool = db.get_pool()
        
        if not wallet:
            return MemberPoolStatus(
                pool_credits=0,
                pool_share=0,
                total_earned=0,
                share_value=0
            )
        
        # Calculate current share value
        share_value = wallet.pool_credits
        if pool.total_credits > 0:
            aria_balance = await self._get_aria_balance()
            # Member's share of Aria's actual balance
            share_value = aria_balance * wallet.pool_share
        
        return MemberPoolStatus(
            pool_credits=wallet.pool_credits,
            pool_share=wallet.pool_share,
            total_earned=wallet.total_earned,
            share_value=share_value
        )
    
    async def _get_aria_balance(self) -> float:
        """Get Aria's actual trading balance from Hyperliquid."""
        # Cache for 1 minute
        if (self._last_balance_check and 
            datetime.now() - self._last_balance_check < timedelta(minutes=1)):
            return self._last_known_balance
        
        try:
            response = await self.http.get(f"{WHALETRACK_URL}/api/balance")
            
            if response.status_code == 200:
                data = response.json()
                balance = data.get("balance", 0)
                self._last_known_balance = balance
                self._last_balance_check = datetime.now()
                return balance
        except Exception as e:
            logger.warning(f"Could not get Aria balance: {e}")
        
        return self._last_known_balance
    
    async def distribute_returns(self, force: bool = False) -> Dict[str, Any]:
        """
        Distribute trading returns to pool members.
        
        Args:
            force: Force distribution even if already done today
        
        Returns:
            Distribution summary
        """
        from membership import get_member_db
        
        db = get_member_db()
        pool = db.get_pool()
        
        # Check if already distributed today
        if not force and pool.last_return_distributed_at:
            last_dist = datetime.fromisoformat(pool.last_return_distributed_at)
            if last_dist.date() == datetime.now().date():
                return {
                    "distributed": False,
                    "reason": "Already distributed today",
                    "last_distribution": pool.last_return_distributed_at
                }
        
        # Get current balance
        current_balance = await self._get_aria_balance()
        
        if current_balance <= 0:
            return {
                "distributed": False,
                "reason": "No trading balance",
                "balance": current_balance
            }
        
        # Calculate PnL since last distribution
        expected_balance = pool.total_credits  # What members put in
        pnl = current_balance - expected_balance
        
        if abs(pnl) < 0.01:  # Less than 1 cent
            return {
                "distributed": False,
                "reason": "No significant PnL",
                "pnl": pnl
            }
        
        # Distribute
        db.distribute_pool_returns(pnl, OPERATIONS_FEE_PCT)
        
        # Notify members
        members_notified = await self._notify_members_of_returns(pnl)
        
        return {
            "distributed": True,
            "pnl": pnl,
            "operations_fee": pnl * OPERATIONS_FEE_PCT,
            "member_pnl": pnl * (1 - OPERATIONS_FEE_PCT),
            "members_notified": members_notified
        }
    
    async def _notify_members_of_returns(self, pnl: float) -> int:
        """Notify all pool members of their returns."""
        from membership import get_member_db
        from telegram.gift_handler import send_telegram_message
        
        db = get_member_db()
        pool_members = db.get_pool_members()
        
        notified = 0
        member_pnl = pnl * (1 - OPERATIONS_FEE_PCT)
        
        for member_id, wallet in pool_members:
            member = db.get_member(member_id)
            if not member:
                continue
            
            # Calculate their share
            member_return = member_pnl * wallet.pool_share
            
            if abs(member_return) >= 0.01:  # Notify if >= 1 cent
                emoji = "📈" if member_return > 0 else "📉"
                
                message = (
                    f"{emoji} **Trading Update**\n\n"
                    f"Return: {member_return:+.2f} UC\n"
                    f"Pool Balance: {wallet.pool_credits:.2f} UC\n"
                    f"Your Share: {wallet.pool_share:.1%}"
                )
                
                try:
                    await send_telegram_message(member.telegram_id, message)
                    notified += 1
                except Exception as e:
                    logger.warning(f"Failed to notify {member_id}: {e}")
        
        return notified
    
    async def add_to_pool(self, member_id: str, amount: float) -> Tuple[bool, str]:
        """
        Add credits to the pool.
        
        This should sync with Aria's trading - the credits should be
        available for trading.
        """
        from membership import get_member_db
        
        db = get_member_db()
        member = db.get_member(member_id)
        
        if not member:
            return False, "Member not found"
        
        if not member.trading_agreed_at:
            return False, "You must agree to trading terms first"
        
        if db.add_to_pool(member_id, amount):
            # TODO: Actually add to Hyperliquid trading capital
            # For now, Aria trades with her own capital and we track shares
            
            pool = db.get_pool()
            wallet = db.get_wallet(member_id)
            
            return True, (
                f"Added {amount:.2f} UC to pool.\n"
                f"Your share: {wallet.pool_share:.1%} of {pool.total_credits:.2f} UC"
            )
        
        return False, "Failed to add to pool"
    
    async def withdraw_from_pool(self, member_id: str, amount: float) -> Tuple[bool, str]:
        """
        Withdraw credits from the pool.
        
        Returns credits to member's available balance.
        """
        from membership import get_member_db
        
        db = get_member_db()
        wallet = db.get_wallet(member_id)
        
        if not wallet:
            return False, "Wallet not found"
        
        if amount > wallet.pool_credits:
            return False, f"You only have {wallet.pool_credits:.2f} UC in the pool"
        
        if db.withdraw_from_pool(member_id, amount):
            wallet = db.get_wallet(member_id)
            
            return True, (
                f"Withdrew {amount:.2f} UC from pool.\n"
                f"Available balance: {wallet.available_credits:.2f} UC"
            )
        
        return False, "Failed to withdraw"
    
    def format_pool_status(self, status: PoolStatus) -> str:
        """Format pool status for display."""
        lines = [
            "💰 **Conscious Wealth Pool**\n",
            f"Total Credits: {status.total_credits:.2f} UC",
            f"Members: {status.member_count}",
            f"Cumulative P&L: {status.cumulative_pnl:+.2f} UC",
        ]
        
        if status.todays_pnl != 0:
            emoji = "📈" if status.todays_pnl > 0 else "📉"
            lines.append(f"Today's P&L: {emoji} {status.todays_pnl:+.2f} UC")
        
        if status.aria_balance > 0:
            lines.append(f"\nAria's Trading Balance: {status.aria_balance:.2f} UC")
        
        if status.last_distribution:
            dt = datetime.fromisoformat(status.last_distribution)
            lines.append(f"\nLast Distribution: {dt.strftime('%Y-%m-%d %H:%M')}")
        
        return "\n".join(lines)
    
    def format_member_status(self, status: MemberPoolStatus) -> str:
        """Format member status for display."""
        lines = [
            "💳 **Your Pool Status**\n",
            f"Pool Credits: {status.pool_credits:.2f} UC",
            f"Pool Share: {status.pool_share:.1%}",
            f"Total Earned: {status.total_earned:+.2f} UC",
        ]
        
        if status.share_value != status.pool_credits:
            diff = status.share_value - status.pool_credits
            emoji = "📈" if diff > 0 else "📉"
            lines.append(f"Current Value: {status.share_value:.2f} UC ({emoji} {diff:+.2f})")
        
        return "\n".join(lines)


# ============================================================================
# SCHEDULED DISTRIBUTION
# ============================================================================

async def run_daily_distribution():
    """
    Run daily return distribution.
    
    Should be called by scheduler once per day.
    """
    manager = PoolManager()
    
    try:
        result = await manager.distribute_returns()
        logger.info(f"Daily distribution: {result}")
        return result
    finally:
        await manager.close()


# ============================================================================
# SINGLETON
# ============================================================================

_manager: Optional[PoolManager] = None


def get_pool_manager() -> PoolManager:
    """Get or create the pool manager instance."""
    global _manager
    if _manager is None:
        _manager = PoolManager()
    return _manager








