"""
MEMBER WALLET
==============

High-level wallet operations for members.

Provides:
- Balance checking
- Credit transfers
- Pool operations
- Transaction history
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .member_db import (
    MemberDB, get_member_db,
    Member, Wallet, Transaction, PendingGift,
    TransactionType, TransactionStatus
)

logger = logging.getLogger("aria.membership.wallet")


@dataclass
class TransferResult:
    """Result of a credit transfer."""
    success: bool
    message: str
    transaction_id: Optional[int] = None
    pending_gift_id: Optional[str] = None


class MemberWallet:
    """
    Wallet operations for a specific member.
    
    Handles:
    - Balance queries
    - Sending gifts
    - Pool opt-in/out
    - Transaction history
    """
    
    def __init__(self, member_id: str, db: MemberDB = None):
        self.member_id = member_id
        self.db = db or get_member_db()
    
    @property
    def member(self) -> Optional[Member]:
        """Get the member."""
        return self.db.get_member(self.member_id)
    
    @property
    def wallet(self) -> Optional[Wallet]:
        """Get the wallet."""
        return self.db.get_wallet(self.member_id)
    
    def get_balance(self) -> Dict[str, float]:
        """Get wallet balances."""
        wallet = self.wallet
        if not wallet:
            return {
                "available": 0,
                "pool": 0,
                "total": 0,
                "pool_share": 0
            }
        
        return {
            "available": wallet.available_credits,
            "pool": wallet.pool_credits,
            "total": wallet.total_balance,
            "pool_share": wallet.pool_share
        }
    
    def send_gift(
        self,
        to_telegram_id: int,
        to_username: Optional[str],
        amount: float,
        message: Optional[str] = None
    ) -> TransferResult:
        """
        Send a gift to another user.
        
        If recipient is a member, transfer immediately.
        If not, create a pending gift for them to claim.
        """
        wallet = self.wallet
        if not wallet:
            return TransferResult(False, "Wallet not found")
        
        if wallet.available_credits < amount:
            return TransferResult(
                False, 
                f"Insufficient balance. Available: {wallet.available_credits:.2f} UC"
            )
        
        if amount <= 0:
            return TransferResult(False, "Amount must be positive")
        
        # Check if recipient is already a member
        recipient = self.db.get_member_by_telegram(to_telegram_id)
        
        if recipient:
            # Direct transfer
            return self._transfer_to_member(recipient.id, amount, message)
        else:
            # Create pending gift
            return self._create_pending_gift(to_telegram_id, to_username, amount, message)
    
    def _transfer_to_member(
        self,
        to_member_id: str,
        amount: float,
        message: Optional[str] = None
    ) -> TransferResult:
        """Transfer credits to another member."""
        # Deduct from sender
        if not self.db.deduct_credits(self.member_id, amount):
            return TransferResult(False, "Failed to deduct credits")
        
        # Add to recipient
        if not self.db.add_credits(to_member_id, amount):
            # Rollback
            self.db.add_credits(self.member_id, amount)
            return TransferResult(False, "Failed to credit recipient")
        
        # Record transaction
        tx = Transaction(
            from_member=self.member_id,
            to_member=to_member_id,
            amount=amount,
            type=TransactionType.GIFT,
            status=TransactionStatus.COMPLETED,
            description=message or "Gift transfer",
            completed_at=datetime.now().isoformat()
        )
        tx_id = self.db.create_transaction(tx)
        
        logger.info(f"Transferred {amount} UC from {self.member_id} to {to_member_id}")
        
        return TransferResult(
            True,
            f"Successfully sent {amount:.2f} UC",
            transaction_id=tx_id
        )
    
    def _create_pending_gift(
        self,
        to_telegram_id: int,
        to_username: Optional[str],
        amount: float,
        message: Optional[str] = None
    ) -> TransferResult:
        """Create a pending gift for a non-member."""
        # Deduct from sender (hold in escrow)
        if not self.db.deduct_credits(self.member_id, amount):
            return TransferResult(False, "Failed to deduct credits")
        
        # Create pending gift
        gift = PendingGift(
            id=None,
            from_member=self.member_id,
            to_telegram_id=to_telegram_id,
            to_telegram_username=to_username,
            amount=amount,
            message=message
        )
        gift_id = self.db.create_pending_gift(gift)
        
        # Record transaction as pending
        tx = Transaction(
            from_member=self.member_id,
            to_member=None,  # Not yet a member
            amount=amount,
            type=TransactionType.GIFT,
            status=TransactionStatus.PENDING,
            description=f"Pending gift to @{to_username or to_telegram_id}",
            metadata={"pending_gift_id": gift_id}
        )
        self.db.create_transaction(tx)
        
        logger.info(f"Created pending gift {gift_id}: {amount} UC to {to_telegram_id}")
        
        return TransferResult(
            True,
            f"Gift of {amount:.2f} UC pending acceptance",
            pending_gift_id=gift_id
        )
    
    def accept_pending_gift(self, gift_id: str) -> TransferResult:
        """Accept a pending gift (called after onboarding)."""
        gift = self.db.get_pending_gift(gift_id)
        if not gift:
            return TransferResult(False, "Gift not found or expired")
        
        if gift.to_telegram_id != self.member.telegram_id:
            return TransferResult(False, "This gift is not for you")
        
        # Credit the recipient
        if not self.db.add_credits(self.member_id, gift.amount):
            return TransferResult(False, "Failed to credit your wallet")
        
        # Record completed transaction
        tx = Transaction(
            from_member=gift.from_member,
            to_member=self.member_id,
            amount=gift.amount,
            type=TransactionType.GIFT,
            status=TransactionStatus.COMPLETED,
            description=gift.message or "Gift accepted",
            completed_at=datetime.now().isoformat()
        )
        tx_id = self.db.create_transaction(tx)
        
        # Delete pending gift
        self.db.delete_pending_gift(gift_id)
        
        logger.info(f"Gift {gift_id} accepted by {self.member_id}")
        
        return TransferResult(
            True,
            f"Received {gift.amount:.2f} UC!",
            transaction_id=tx_id
        )
    
    def opt_into_pool(self, amount: Optional[float] = None) -> TransferResult:
        """Opt into the trading pool."""
        member = self.member
        if not member:
            return TransferResult(False, "Member not found")
        
        if not member.trading_agreed_at:
            return TransferResult(False, "You must agree to trading terms first")
        
        wallet = self.wallet
        if not wallet:
            return TransferResult(False, "Wallet not found")
        
        # Default to all available credits
        if amount is None:
            amount = wallet.available_credits
        
        if amount <= 0:
            return TransferResult(False, "No credits to add to pool")
        
        if amount > wallet.available_credits:
            return TransferResult(
                False,
                f"Insufficient balance. Available: {wallet.available_credits:.2f} UC"
            )
        
        # Add to pool
        if not self.db.add_to_pool(self.member_id, amount):
            return TransferResult(False, "Failed to add to pool")
        
        # Record transaction
        tx = Transaction(
            from_member=self.member_id,
            to_member=None,
            amount=amount,
            type=TransactionType.POOL_CONTRIBUTION,
            status=TransactionStatus.COMPLETED,
            description=f"Added {amount:.2f} UC to trading pool",
            completed_at=datetime.now().isoformat()
        )
        self.db.create_transaction(tx)
        
        # Get updated wallet
        wallet = self.wallet
        pool = self.db.get_pool()
        
        logger.info(f"{self.member_id} added {amount} UC to pool")
        
        return TransferResult(
            True,
            f"Added {amount:.2f} UC to pool. Your share: {wallet.pool_share:.1%} of {pool.total_credits:.2f} UC"
        )
    
    def opt_out_of_pool(self, amount: Optional[float] = None) -> TransferResult:
        """Withdraw from the trading pool."""
        wallet = self.wallet
        if not wallet:
            return TransferResult(False, "Wallet not found")
        
        # Default to all pool credits
        if amount is None:
            amount = wallet.pool_credits
        
        if amount <= 0:
            return TransferResult(False, "No credits in pool")
        
        if amount > wallet.pool_credits:
            return TransferResult(
                False,
                f"Only {wallet.pool_credits:.2f} UC in pool"
            )
        
        # Withdraw from pool
        if not self.db.withdraw_from_pool(self.member_id, amount):
            return TransferResult(False, "Failed to withdraw from pool")
        
        # Record transaction
        tx = Transaction(
            from_member=None,
            to_member=self.member_id,
            amount=amount,
            type=TransactionType.POOL_WITHDRAWAL,
            status=TransactionStatus.COMPLETED,
            description=f"Withdrew {amount:.2f} UC from trading pool",
            completed_at=datetime.now().isoformat()
        )
        self.db.create_transaction(tx)
        
        logger.info(f"{self.member_id} withdrew {amount} UC from pool")
        
        return TransferResult(
            True,
            f"Withdrew {amount:.2f} UC from pool. Now available in your wallet."
        )
    
    def get_transactions(self, limit: int = 20) -> List[Transaction]:
        """Get transaction history."""
        return self.db.get_transactions(self.member_id, limit=limit)
    
    def get_pool_returns(self, limit: int = 20) -> List[Transaction]:
        """Get pool return history."""
        all_tx = self.db.get_transactions(self.member_id, limit=100)
        return [tx for tx in all_tx if tx.type == TransactionType.POOL_RETURN][:limit]
    
    def format_balance(self) -> str:
        """Format balance for display."""
        balance = self.get_balance()
        
        lines = [
            f"💳 **Your Wallet**\n",
            f"Available: {balance['available']:.2f} UC",
        ]
        
        if balance['pool'] > 0:
            lines.append(f"In Pool: {balance['pool']:.2f} UC ({balance['pool_share']:.1%} share)")
        
        lines.append(f"**Total: {balance['total']:.2f} UC**")
        
        return "\n".join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_wallet(member_id: str) -> MemberWallet:
    """Get a wallet instance for a member."""
    return MemberWallet(member_id)


def get_wallet_by_telegram(telegram_id: int) -> Optional[MemberWallet]:
    """Get wallet by Telegram ID."""
    db = get_member_db()
    member = db.get_member_by_telegram(telegram_id)
    
    if member:
        return MemberWallet(member.id, db)
    return None








