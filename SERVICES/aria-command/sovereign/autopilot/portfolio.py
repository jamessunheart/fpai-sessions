#!/usr/bin/env python3
"""
ARIA ULTRA POWER - PORTFOLIO MANAGER
=====================================

Track and manage trading portfolio:
- Position tracking across exchanges
- P&L calculation
- Exposure analysis
- Rebalancing recommendations
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.autopilot.portfolio")

WHALETRACK_LIVE_URL = "http://198.54.123.234:8601"


class PositionSide(Enum):
    """Position side."""
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    """A trading position."""
    symbol: str
    side: PositionSide
    size: float  # In units
    entry_price: float
    current_price: float
    leverage: float = 1.0
    unrealized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: float = field(default_factory=time.time)
    
    @property
    def notional_value(self) -> float:
        """Total notional value."""
        return self.size * self.current_price
    
    @property
    def margin_used(self) -> float:
        """Margin used for this position."""
        return self.notional_value / self.leverage
    
    @property
    def pnl_percent(self) -> float:
        """P&L as percentage."""
        if self.entry_price == 0:
            return 0
        if self.side == PositionSide.LONG:
            return (self.current_price - self.entry_price) / self.entry_price * 100 * self.leverage
        else:
            return (self.entry_price - self.current_price) / self.entry_price * 100 * self.leverage
    
    @property
    def is_profit(self) -> bool:
        """Is position in profit."""
        return self.unrealized_pnl > 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "size": self.size,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "leverage": self.leverage,
            "unrealized_pnl": self.unrealized_pnl,
            "pnl_percent": self.pnl_percent,
            "notional_value": self.notional_value,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
        }


@dataclass
class PortfolioState:
    """Current portfolio state."""
    total_balance: float
    available_balance: float
    total_margin_used: float
    total_unrealized_pnl: float
    positions: List[Position]
    exposure_by_asset: Dict[str, float]
    total_exposure_percent: float
    updated_at: float = field(default_factory=time.time)
    
    @property
    def equity(self) -> float:
        """Total equity including unrealized P&L."""
        return self.total_balance + self.total_unrealized_pnl
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "total_balance": self.total_balance,
            "available_balance": self.available_balance,
            "equity": self.equity,
            "total_margin_used": self.total_margin_used,
            "total_unrealized_pnl": self.total_unrealized_pnl,
            "positions": [p.to_dict() for p in self.positions],
            "exposure_by_asset": self.exposure_by_asset,
            "total_exposure_percent": self.total_exposure_percent,
        }


class PortfolioManager:
    """
    Manage trading portfolio.
    
    Features:
    - Real-time position tracking
    - P&L calculation
    - Exposure analysis
    - Position sizing
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._state: Optional[PortfolioState] = None
        self._last_update = 0
        self._update_interval = 30  # seconds
        
        logger.info("PortfolioManager initialized")
    
    async def get_state(self, force_refresh: bool = False) -> PortfolioState:
        """Get current portfolio state."""
        now = time.time()
        
        if not force_refresh and self._state and (now - self._last_update < self._update_interval):
            return self._state
        
        # Fetch from WhaleTrack Live
        try:
            response = await self.http.get(f"{WHALETRACK_LIVE_URL}/api/live/status")
            
            if response.status_code == 200:
                data = response.json()
                self._state = self._parse_state(data)
                self._last_update = now
                return self._state
        except Exception as e:
            logger.error(f"Failed to fetch portfolio: {e}")
        
        # Return empty state if failed
        if self._state is None:
            self._state = PortfolioState(
                total_balance=0,
                available_balance=0,
                total_margin_used=0,
                total_unrealized_pnl=0,
                positions=[],
                exposure_by_asset={},
                total_exposure_percent=0,
            )
        
        return self._state
    
    def _parse_state(self, data: Dict) -> PortfolioState:
        """Parse portfolio state from API response."""
        positions = []
        exposure_by_asset = {}
        total_margin = 0
        total_pnl = 0
        
        for pos_data in data.get("positions", []):
            pos = Position(
                symbol=pos_data.get("symbol", ""),
                side=PositionSide.LONG if pos_data.get("side", "").lower() == "long" else PositionSide.SHORT,
                size=pos_data.get("size", 0),
                entry_price=pos_data.get("entry_price", 0),
                current_price=pos_data.get("mark_price", pos_data.get("current_price", 0)),
                leverage=pos_data.get("leverage", 1),
                unrealized_pnl=pos_data.get("unrealized_pnl", 0),
                stop_loss=pos_data.get("stop_loss"),
                take_profit=pos_data.get("take_profit"),
            )
            positions.append(pos)
            
            # Track exposure
            asset = pos.symbol.replace("/USDT", "").replace("USDT", "")
            exposure_by_asset[asset] = exposure_by_asset.get(asset, 0) + pos.notional_value
            total_margin += pos.margin_used
            total_pnl += pos.unrealized_pnl
        
        balance = data.get("balance", data.get("total_balance", 0))
        available = data.get("available_balance", balance - total_margin)
        
        # Calculate exposure percentage
        total_exposure = sum(exposure_by_asset.values())
        exposure_pct = (total_exposure / balance * 100) if balance > 0 else 0
        
        return PortfolioState(
            total_balance=balance,
            available_balance=available,
            total_margin_used=total_margin,
            total_unrealized_pnl=total_pnl,
            positions=positions,
            exposure_by_asset=exposure_by_asset,
            total_exposure_percent=exposure_pct,
        )
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get a specific position."""
        state = await self.get_state()
        for pos in state.positions:
            if pos.symbol == symbol or pos.symbol.startswith(symbol):
                return pos
        return None
    
    def calculate_position_size(
        self,
        portfolio_percent: float,
        entry_price: float,
        leverage: float = 1.0,
    ) -> float:
        """Calculate position size based on portfolio percentage."""
        if self._state is None:
            return 0
        
        risk_amount = self._state.total_balance * (portfolio_percent / 100)
        position_value = risk_amount * leverage
        size = position_value / entry_price if entry_price > 0 else 0
        
        return size
    
    def get_rebalance_recommendations(self, target_allocations: Dict[str, float]) -> List[Dict]:
        """Get recommendations to rebalance portfolio to target allocations."""
        if self._state is None:
            return []
        
        recommendations = []
        total_equity = self._state.equity
        
        for asset, target_pct in target_allocations.items():
            current_exposure = self._state.exposure_by_asset.get(asset, 0)
            current_pct = (current_exposure / total_equity * 100) if total_equity > 0 else 0
            target_exposure = total_equity * (target_pct / 100)
            
            diff = target_exposure - current_exposure
            diff_pct = target_pct - current_pct
            
            if abs(diff_pct) > 1:  # More than 1% difference
                action = "BUY" if diff > 0 else "SELL"
                recommendations.append({
                    "asset": asset,
                    "action": action,
                    "amount_usd": abs(diff),
                    "current_percent": current_pct,
                    "target_percent": target_pct,
                    "reason": f"Rebalance {asset} from {current_pct:.1f}% to {target_pct:.1f}%",
                })
        
        return recommendations
    
    def format_portfolio(self) -> str:
        """Format portfolio for display."""
        if self._state is None:
            return "Portfolio data unavailable"
        
        state = self._state
        
        lines = [
            "💼 **Portfolio Status**",
            "",
            f"Balance: ${state.total_balance:,.2f}",
            f"Equity: ${state.equity:,.2f}",
            f"P&L: ${state.total_unrealized_pnl:+,.2f}",
            f"Exposure: {state.total_exposure_percent:.1f}%",
            "",
        ]
        
        if state.positions:
            lines.append("**Positions:**")
            for pos in state.positions:
                emoji = "🟢" if pos.is_profit else "🔴"
                side = "L" if pos.side == PositionSide.LONG else "S"
                lines.append(
                    f"{emoji} {pos.symbol} ({side} {pos.leverage}x): "
                    f"${pos.unrealized_pnl:+,.2f} ({pos.pnl_percent:+.2f}%)"
                )
        else:
            lines.append("No open positions")
        
        return "\n".join(lines)


# Singleton instance
_manager: Optional[PortfolioManager] = None


def get_portfolio_manager() -> PortfolioManager:
    """Get global PortfolioManager instance."""
    global _manager
    if _manager is None:
        _manager = PortfolioManager()
    return _manager


