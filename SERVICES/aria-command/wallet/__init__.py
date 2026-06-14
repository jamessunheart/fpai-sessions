# SERVICES/aria-command/wallet/__init__.py
"""
Unified Wallet View for Full Potential services.
Aggregates balances from UC Credits, Zend, Trading, and TRUST.
"""

from .unified_view import (
    get_unified_wallet,
    UnifiedWalletView,
    get_unified_balance_summary
)

__all__ = [
    "get_unified_wallet",
    "UnifiedWalletView",
    "get_unified_balance_summary"
]









