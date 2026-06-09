# SERVICES/aria-command/wallet/unified_view.py
"""
Unified Wallet View - Single view of all member balances.

Aggregates from:
- FP Credits Gateway (UC balance)
- Trust Index service (TRUST score)
- Aria Trading (trading P&L)
- Zend Wallet (Zend-specific balance)
- TON Wallet (USDT balance)
"""

import os
import logging
import httpx
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WalletBalance:
    """A single wallet balance."""
    source: str
    balance: float
    currency: str
    last_updated: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedWalletView:
    """Unified view of all member balances."""
    user_id: str
    
    # UC Credits
    uc_balance: float = 0.0
    uc_lifetime_credits: float = 0.0
    uc_lifetime_spent: float = 0.0
    
    # TRUST
    trust_score: int = 0
    trust_tier: str = "inactive"
    trust_quarterly_score: int = 0
    trust_eligible_for_benefits: bool = False
    
    # Trading
    trading_connected: bool = False
    trading_balance: float = 0.0
    trading_pnl_today: float = 0.0
    trading_pnl_month: float = 0.0
    trading_positions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Zend
    zend_balance: float = 0.0
    zend_unlocks: List[str] = field(default_factory=list)
    
    # TON
    ton_connected: bool = False
    ton_usdt_balance: float = 0.0
    ton_balance: float = 0.0
    
    # Meta
    fetched_at: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)


class UnifiedWalletAggregator:
    """
    Aggregates wallet balances from multiple services.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        # Service URLs
        self.credits_gateway_url = os.getenv(
            "FP_CREDITS_GATEWAY_URL",
            "https://fullpotential.ai/services/credits/api"
        )
        self.trust_index_url = os.getenv(
            "TRUST_INDEX_URL",
            "http://198.54.123.234:8560"
        )
        self.zend_wallet_url = os.getenv(
            "ZEND_WALLET_URL",
            "http://198.54.123.234:8580"
        )
        self.zend_ton_url = os.getenv(
            "ZEND_TON_URL",
            "http://198.54.123.234:8583"
        )
        
        # API Keys
        self.credits_api_key = os.getenv("FP_CREDITS_API_KEY", "")
        
        self._initialized = True
        logger.info("Unified Wallet Aggregator initialized")
    
    async def get_unified_view(self, user_id: str) -> UnifiedWalletView:
        """
        Get unified wallet view for a user.
        Fetches from all available services.
        """
        view = UnifiedWalletView(user_id=user_id)
        
        # Fetch all balances in parallel
        import asyncio
        results = await asyncio.gather(
            self._fetch_uc_balance(user_id),
            self._fetch_trust_score(user_id),
            self._fetch_trading_status(user_id),
            self._fetch_zend_balance(user_id),
            self._fetch_ton_balance(user_id),
            return_exceptions=True
        )
        
        # Process UC balance
        if isinstance(results[0], dict):
            view.uc_balance = results[0].get("balance", 0)
            view.uc_lifetime_credits = results[0].get("lifetime_credits", 0)
            view.uc_lifetime_spent = results[0].get("lifetime_spent", 0)
        elif isinstance(results[0], Exception):
            view.errors.append(f"UC: {str(results[0])}")
        
        # Process TRUST score
        if isinstance(results[1], dict):
            view.trust_score = results[1].get("total_score", 0)
            view.trust_tier = results[1].get("tier", "inactive")
            view.trust_quarterly_score = results[1].get("quarterly_score", 0)
            view.trust_eligible_for_benefits = results[1].get("eligible_for_benefits", False)
        elif isinstance(results[1], Exception):
            view.errors.append(f"TRUST: {str(results[1])}")
        
        # Process Trading status
        if isinstance(results[2], dict):
            view.trading_connected = results[2].get("connected", False)
            view.trading_balance = results[2].get("balance", 0)
            view.trading_pnl_today = results[2].get("pnl_today", 0)
            view.trading_pnl_month = results[2].get("pnl_month", 0)
            view.trading_positions = results[2].get("positions", [])
        elif isinstance(results[2], Exception):
            view.errors.append(f"Trading: {str(results[2])}")
        
        # Process Zend balance
        if isinstance(results[3], dict):
            view.zend_balance = results[3].get("balance", 0)
            view.zend_unlocks = results[3].get("unlocks", [])
        elif isinstance(results[3], Exception):
            view.errors.append(f"Zend: {str(results[3])}")
        
        # Process TON balance
        if isinstance(results[4], dict):
            view.ton_connected = results[4].get("connected", False)
            view.ton_usdt_balance = results[4].get("usdt_balance", 0)
            view.ton_balance = results[4].get("ton_balance", 0)
        elif isinstance(results[4], Exception):
            view.errors.append(f"TON: {str(results[4])}")
        
        view.fetched_at = datetime.now()
        return view
    
    async def _fetch_uc_balance(self, user_id: str) -> Dict[str, Any]:
        """Fetch UC balance from Credits Gateway."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.credits_gateway_url}/balance/{user_id}",
                    headers={"Authorization": f"Bearer {self.credits_api_key}"}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.debug(f"Failed to fetch UC balance: {e}")
        
        # Fallback to local billing manager
        try:
            from billing import get_billing_manager
            manager = get_billing_manager()
            summary = manager.get_billing_summary(user_id)
            return {
                "balance": summary.get("balance", 0),
                "lifetime_credits": summary.get("lifetime_credits", 0),
                "lifetime_spent": summary.get("lifetime_spent", 0)
            }
        except Exception:
            return {"balance": 0}
    
    async def _fetch_trust_score(self, user_id: str) -> Dict[str, Any]:
        """Fetch TRUST score from Trust Index service or local tracker."""
        # Try Trust Index service
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.trust_index_url}/api/member/{user_id}"
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        
        # Fallback to local contribution tracker
        try:
            from trading.contribution_tracker import get_contribution_tracker
            tracker = get_contribution_tracker()
            return tracker.get_user_summary(user_id)
        except Exception:
            return {"total_score": 0, "tier": "inactive"}
    
    async def _fetch_trading_status(self, user_id: str) -> Dict[str, Any]:
        """Fetch trading status from Hyperliquid."""
        try:
            from trading.hyperliquid_live import get_hyperliquid_client
            client = get_hyperliquid_client()
            
            if not client or not client.connected:
                return {"connected": False}
            
            account_state = await client.get_account_state()
            
            return {
                "connected": True,
                "balance": float(account_state.get("marginSummary", {}).get("accountValue", 0)),
                "pnl_today": float(account_state.get("marginSummary", {}).get("totalUnrealizedPnl", 0)),
                "pnl_month": 0,  # Would need historical data
                "positions": account_state.get("positions", [])
            }
        except Exception as e:
            logger.debug(f"Failed to fetch trading status: {e}")
            return {"connected": False}
    
    async def _fetch_zend_balance(self, user_id: str) -> Dict[str, Any]:
        """Fetch Zend wallet balance."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.zend_wallet_url}/api/zend/wallet/{user_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "balance": data.get("balance", 0),
                        "unlocks": data.get("unlocked_experiences", [])
                    }
        except Exception:
            pass
        return {"balance": 0, "unlocks": []}
    
    async def _fetch_ton_balance(self, user_id: str) -> Dict[str, Any]:
        """Fetch TON wallet balance."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.zend_ton_url}/api/ton/wallet/{user_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "connected": data.get("connected", False),
                        "usdt_balance": data.get("usdt_balance", 0),
                        "ton_balance": data.get("ton_balance", 0)
                    }
        except Exception:
            pass
        return {"connected": False}
    
    def format_balance_message(self, view: UnifiedWalletView) -> str:
        """Format unified view as a user-friendly message."""
        lines = [
            "💰 **Your Full Potential Balance**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]
        
        # UC Credits
        lines.append(f"🪙 **UC Credits:** {view.uc_balance:,.2f} UC")
        
        # TRUST Score
        tier_emoji = {"active": "🟢", "engaged": "🟡", "inactive": "⚪"}.get(view.trust_tier, "⚪")
        lines.append(f"🤝 **TRUST Score:** {view.trust_score} ({tier_emoji} {view.trust_tier.title()})")
        if view.trust_quarterly_score < 100:
            lines.append(f"    ↳ Need {100 - view.trust_quarterly_score} more points for benefits")
        
        # Trading
        if view.trading_connected:
            pnl_emoji = "📈" if view.trading_pnl_today >= 0 else "📉"
            lines.append(f"📊 **Trading Balance:** ${view.trading_balance:,.2f}")
            lines.append(f"    {pnl_emoji} Today: ${view.trading_pnl_today:+,.2f}")
            if view.trading_positions:
                lines.append(f"    📍 Open positions: {len(view.trading_positions)}")
        else:
            lines.append("📊 **Trading:** Not connected")
        
        # Zend
        if view.zend_balance > 0:
            lines.append(f"💸 **Zend Balance:** {view.zend_balance:,.2f} UC")
        
        # TON
        if view.ton_connected:
            lines.append(f"💎 **TON Wallet:** ${view.ton_usdt_balance:,.2f} USDT")
        
        # Quick Actions
        lines.extend([
            "",
            "**Quick Actions:**",
            "• /trade - Trading dashboard",
            "• /zend - Send UC",
            "• /contribute - Earn TRUST"
        ])
        
        if view.errors:
            lines.extend([
                "",
                "⚠️ Some services unavailable"
            ])
        
        return "\n".join(lines)


# Singleton instance
_aggregator: Optional[UnifiedWalletAggregator] = None


def get_unified_wallet() -> UnifiedWalletAggregator:
    """Get the singleton wallet aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = UnifiedWalletAggregator()
    return _aggregator


async def get_unified_balance_summary(user_id: str) -> str:
    """Get formatted balance summary for a user."""
    aggregator = get_unified_wallet()
    view = await aggregator.get_unified_view(user_id)
    return aggregator.format_balance_message(view)









