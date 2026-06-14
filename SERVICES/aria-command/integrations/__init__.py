# SERVICES/aria-command/integrations/__init__.py
"""
Cross-service integrations for Aria.
Bridges between Trading, Zend, UC, and other services.
"""

from .zend_trading_bridge import (
    ZendTradingBridge,
    get_zend_trading_bridge,
    convert_profit_to_uc,
    fund_trading_from_zend
)

__all__ = [
    "ZendTradingBridge",
    "get_zend_trading_bridge",
    "convert_profit_to_uc",
    "fund_trading_from_zend"
]









