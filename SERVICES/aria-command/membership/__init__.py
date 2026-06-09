"""
MEMBERSHIP SYSTEM
==================

Member management for the Conscious Wealth Fellowship (PMA).

Components:
- MemberDB: SQLite database for members, wallets, transactions
- MemberWallet: Wallet operations (balance, transfers, pool allocation)
- Onboarding: PMA agreement acceptance flow
"""

from .member_db import (
    MemberDB, get_member_db,
    Member, Wallet, Transaction, PendingGift, TradingPool,
    TransactionType, TransactionStatus
)
from .member_wallet import MemberWallet, get_wallet, get_wallet_by_telegram
from .onboarding import MemberOnboarding, get_onboarding
from .claim_links import ClaimLink, ClaimLinkManager, get_claim_manager

__all__ = [
    "MemberDB",
    "get_member_db",
    "Member",
    "Wallet",
    "Transaction",
    "PendingGift",
    "TradingPool",
    "TransactionType",
    "TransactionStatus",
    "MemberWallet", 
    "get_wallet",
    "get_wallet_by_telegram",
    "MemberOnboarding",
    "get_onboarding",
    "ClaimLink",
    "ClaimLinkManager",
    "get_claim_manager",
]
