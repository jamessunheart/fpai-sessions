"""FP Credits SDK - Python client for the FP Credits Gateway"""

from .fp_credits import (
    FPCredits,
    FPCreditsError,
    CreditType,
    Balance,
    Transaction,
    require_credits
)

__version__ = "1.0.0"
__all__ = [
    "FPCredits",
    "FPCreditsError", 
    "CreditType",
    "Balance",
    "Transaction",
    "require_credits"
]


