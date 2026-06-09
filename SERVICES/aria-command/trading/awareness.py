#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - TRADING AWARENESS
========================================

Market-aware operations:
- Check market conditions before risky actions
- Respect open positions
- Trade-safe mode for critical operations
"""

import os
import asyncio
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import httpx

logger = logging.getLogger("aria.trading")

# ============================================================================
# CONFIGURATION
# ============================================================================

WHALETRACK_URL = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8600")
WHALETRACK_LIVE_URL = os.getenv("WHALETRACK_LIVE_URL", "http://198.54.123.234:8601")


class MarketCondition(str, Enum):
    CALM = "calm"
    ACTIVE = "active"
    VOLATILE = "volatile"
    EXTREME = "extreme"


class TradeSafetyLevel(str, Enum):
    SAFE = "safe"           # No restrictions
    CAUTION = "caution"     # Warn before risky ops
    PROTECTED = "protected"  # Block risky ops


@dataclass
class Position:
    """An open trading position."""
    symbol: str
    side: str  # long/short
    size: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    opened_at: datetime


@dataclass
class Signal:
    """A trading signal."""
    symbol: str
    direction: str  # long/short
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    generated_at: datetime


@dataclass
class MarketContext:
    """Current market context."""
    condition: MarketCondition
    volatility: float
    positions: List[Position]
    active_signals: List[Signal]
    safety_level: TradeSafetyLevel
    
    @property
    def has_open_positions(self) -> bool:
        return len(self.positions) > 0
    
    @property
    def has_high_confidence_signals(self) -> bool:
        return any(s.confidence >= 0.75 for s in self.active_signals)
    
    @property
    def total_exposure(self) -> float:
        return sum(abs(p.size * p.current_price) for p in self.positions)


class TradingAwareness:
    """
    Trading-aware operations.
    
    Features:
    - Market condition monitoring
    - Position tracking
    - Safe operation scheduling
    - Trade-aware alerts
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._context_cache: Optional[MarketContext] = None
        self._cache_time: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=30)
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def get_market_context(self, force_refresh: bool = False) -> MarketContext:
        """
        Get current market context.
        
        Caches results for 30 seconds.
        """
        if (not force_refresh and 
            self._context_cache and 
            self._cache_time and 
            datetime.now() - self._cache_time < self._cache_duration):
            return self._context_cache
        
        # Fetch fresh data
        positions = await self._get_positions()
        signals = await self._get_active_signals()
        volatility = await self._get_volatility()
        
        # Determine market condition
        if volatility > 50:
            condition = MarketCondition.EXTREME
        elif volatility > 30:
            condition = MarketCondition.VOLATILE
        elif volatility > 15:
            condition = MarketCondition.ACTIVE
        else:
            condition = MarketCondition.CALM
        
        # Determine safety level
        if positions and any(abs(p.pnl_percent) > 5 for p in positions):
            # In a significant trade
            safety = TradeSafetyLevel.PROTECTED
        elif positions:
            safety = TradeSafetyLevel.CAUTION
        elif signals and any(s.confidence > 0.8 for s in signals):
            # High-confidence signal pending
            safety = TradeSafetyLevel.CAUTION
        else:
            safety = TradeSafetyLevel.SAFE
        
        context = MarketContext(
            condition=condition,
            volatility=volatility,
            positions=positions,
            active_signals=signals,
            safety_level=safety
        )
        
        self._context_cache = context
        self._cache_time = datetime.now()
        
        return context
    
    async def _get_positions(self) -> List[Position]:
        """Get open positions from WhaleTrack."""
        try:
            response = await self.http.get(f"{WHALETRACK_LIVE_URL}/api/positions")
            
            if response.status_code == 200:
                data = response.json()
                positions = []
                
                for p in data.get("positions", []):
                    positions.append(Position(
                        symbol=p.get("symbol", ""),
                        side=p.get("side", ""),
                        size=float(p.get("size", 0)),
                        entry_price=float(p.get("entry_price", 0)),
                        current_price=float(p.get("current_price", 0)),
                        pnl=float(p.get("pnl", 0)),
                        pnl_percent=float(p.get("pnl_percent", 0)),
                        opened_at=datetime.fromisoformat(p.get("opened_at", datetime.now().isoformat()))
                    ))
                
                return positions
        except Exception as e:
            logger.debug(f"Position fetch failed: {e}")
        
        return []
    
    async def _get_active_signals(self) -> List[Signal]:
        """Get active signals from WhaleTrack using liquidity-clarity endpoint."""
        signals = []
        
        try:
            response = await self.http.get(f"{WHALETRACK_URL}/api/liquidity-clarity")
            
            if response.status_code == 200:
                api_data = response.json()
                symbols_data = api_data.get("symbols", {})
                
                for symbol_key, data in symbols_data.items():
                    symbol = symbol_key.replace("/USDT", "")
                    action = data.get("recommended_action", "WAIT")
                    
                    # Only include if there's a clear signal
                    if action in ["LONG", "SHORT"]:
                        signals.append(Signal(
                            symbol=symbol,
                            direction="long" if action == "LONG" else "short",
                            confidence=float(data.get("clarity_score", 0)) / 100,
                            entry_price=float(data.get("price", 0)),
                            stop_loss=float(data.get("stop_loss", 0)),
                            take_profit=float(data.get("primary_target", 0)),
                            generated_at=datetime.now()
                        ))
        except Exception as e:
            logger.debug(f"Signal fetch failed: {e}")
        
        return signals
    
    async def _get_volatility(self) -> float:
        """Get market volatility estimate."""
        try:
            response = await self.http.get(f"{WHALETRACK_URL}/api/market/volatility")
            
            if response.status_code == 200:
                return float(response.json().get("volatility", 15))
        except Exception as e:
            logger.debug(f"Volatility fetch failed: {e}")
        
        return 15.0  # Default to normal
    
    async def check_operation_safety(self, operation: str) -> Dict:
        """
        Check if an operation is safe given current market conditions.
        
        Returns:
            {
                "safe": bool,
                "level": TradeSafetyLevel,
                "reason": str,
                "recommendation": str
            }
        """
        context = await self.get_market_context()
        
        # Classify operation risk
        high_risk_ops = ["restart", "deploy", "database", "shutdown"]
        medium_risk_ops = ["pip install", "git pull", "update"]
        
        is_high_risk = any(op in operation.lower() for op in high_risk_ops)
        is_medium_risk = any(op in operation.lower() for op in medium_risk_ops)
        
        # Check against market context
        if context.safety_level == TradeSafetyLevel.PROTECTED:
            if is_high_risk:
                return {
                    "safe": False,
                    "level": TradeSafetyLevel.PROTECTED,
                    "reason": f"Open position with {context.positions[0].pnl_percent:.1f}% P&L",
                    "recommendation": "Wait for position to close or use /force to override"
                }
            if is_medium_risk:
                return {
                    "safe": True,
                    "level": TradeSafetyLevel.CAUTION,
                    "reason": "Open position active",
                    "recommendation": "Proceed with caution, avoid trading service restarts"
                }
        
        if context.safety_level == TradeSafetyLevel.CAUTION:
            if is_high_risk and context.condition in [MarketCondition.VOLATILE, MarketCondition.EXTREME]:
                return {
                    "safe": False,
                    "level": TradeSafetyLevel.CAUTION,
                    "reason": f"Market is {context.condition.value}, volatility: {context.volatility:.1f}%",
                    "recommendation": "Wait for market to calm or use /force"
                }
        
        return {
            "safe": True,
            "level": context.safety_level,
            "reason": "No trading concerns",
            "recommendation": "Safe to proceed"
        }
    
    async def get_position_summary(self) -> str:
        """Get human-readable position summary."""
        context = await self.get_market_context()
        
        if not context.positions:
            return "No open positions. All clear."
        
        lines = [f"**{len(context.positions)} Open Position(s)**\n"]
        
        for p in context.positions:
            emoji = "📈" if p.pnl >= 0 else "📉"
            pnl_sign = "+" if p.pnl >= 0 else ""
            lines.append(
                f"{emoji} {p.symbol} {p.side.upper()}\n"
                f"   Entry: ${p.entry_price:.2f} → Now: ${p.current_price:.2f}\n"
                f"   P&L: {pnl_sign}${p.pnl:.2f} ({pnl_sign}{p.pnl_percent:.1f}%)"
            )
        
        total_pnl = sum(p.pnl for p in context.positions)
        lines.append(f"\n**Total P&L:** ${total_pnl:+.2f}")
        
        return "\n".join(lines)
    
    async def get_signal_summary(self) -> str:
        """Get human-readable signal summary."""
        context = await self.get_market_context()
        
        if not context.active_signals:
            return "📊 No active signals at the moment.\n\nUse `/signal SOL` for a specific asset."
        
        lines = [f"**📊 {len(context.active_signals)} Active Signal(s)**\n"]
        
        for s in context.active_signals:
            confidence_bar = "🟢" * int(s.confidence * 5) + "⚪" * (5 - int(s.confidence * 5))
            emoji = "📈" if s.direction == "long" else "📉"
            lines.append(
                f"{emoji} **{s.symbol}** → {s.direction.upper()}\n"
                f"   Clarity: {confidence_bar} ({s.confidence*100:.0f}%)\n"
                f"   Entry: ${s.entry_price:.2f} | SL: ${s.stop_loss:.2f} | TP: ${s.take_profit:.2f}"
            )
        
        return "\n".join(lines)
    
    async def get_symbol_signal(self, symbol: str) -> str:
        """Get detailed signal for a specific symbol."""
        symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        symbol_key = f"{symbol}/USDT"
        
        try:
            response = await self.http.get(f"{WHALETRACK_URL}/api/liquidity-clarity")
            
            if response.status_code == 200:
                api_data = response.json()
                
                # API returns all symbols in a "symbols" dict
                symbols_data = api_data.get("symbols", {})
                
                if symbol_key not in symbols_data:
                    available = ", ".join(s.replace("/USDT", "") for s in symbols_data.keys())
                    return f"❌ Symbol {symbol} not found.\n\nAvailable: {available}"
                
                data = symbols_data[symbol_key]
                
                action = data.get("recommended_action", "WAIT")
                clarity = data.get("clarity_score", 0)
                bias = data.get("bias", "neutral")
                bias_strength = data.get("bias_strength", 0)
                price = data.get("price", 0)
                stop = data.get("stop_loss", 0)
                target = data.get("primary_target", 0)
                rr = data.get("risk_reward", 0)
                sources = data.get("sources_online", 0)
                
                # Build response
                if action == "WAIT":
                    emoji = "⏸️"
                elif action == "LONG":
                    emoji = "📈"
                else:
                    emoji = "📉"
                
                lines = [
                    f"{emoji} **{symbol}/USDT** Signal",
                    f"",
                    f"**Action:** {action}",
                    f"**Current Price:** ${price:,.2f}",
                    f"**Clarity Score:** {clarity:.1f}%",
                    f"**Bias:** {bias.upper()} ({bias_strength:.1f}% strength)",
                    f"**Sources Online:** {sources}/3",
                    f""
                ]
                
                if action != "WAIT":
                    lines.extend([
                        f"**Entry:** ${price:,.2f}",
                        f"**Stop Loss:** ${stop:,.2f}",
                        f"**Target:** ${target:,.2f}",
                        f"**Risk/Reward:** {rr:.1f}x"
                    ])
                else:
                    lines.append(f"_Waiting for better setup..._")
                
                return "\n".join(lines)
            else:
                return f"❌ Could not fetch signals (HTTP {response.status_code})"
                
        except Exception as e:
            logger.error(f"Error getting signal for {symbol}: {e}")
            return f"❌ Error fetching {symbol} signal: {e}"
    
    async def get_market_summary(self) -> str:
        """Get human-readable market summary."""
        context = await self.get_market_context()
        
        condition_emoji = {
            MarketCondition.CALM: "😌",
            MarketCondition.ACTIVE: "📊",
            MarketCondition.VOLATILE: "⚡",
            MarketCondition.EXTREME: "🌪️"
        }
        
        safety_emoji = {
            TradeSafetyLevel.SAFE: "✅",
            TradeSafetyLevel.CAUTION: "⚠️",
            TradeSafetyLevel.PROTECTED: "🛡️"
        }
        
        lines = [
            f"{condition_emoji[context.condition]} Market: {context.condition.value.upper()}",
            f"   Volatility: {context.volatility:.1f}%",
            f"",
            f"{safety_emoji[context.safety_level]} Trade Safety: {context.safety_level.value.upper()}",
            f"   Positions: {len(context.positions)}",
            f"   Active signals: {len(context.active_signals)}"
        ]
        
        if context.total_exposure > 0:
            lines.append(f"   Total exposure: ${context.total_exposure:.2f}")
        
        return "\n".join(lines)


# ============================================================================
# TRADE-SAFE MODE DECORATOR
# ============================================================================

def trade_safe(func):
    """Decorator to check trading safety before executing."""
    async def wrapper(*args, **kwargs):
        awareness = get_awareness()
        
        # Get operation description
        operation = kwargs.get("operation", func.__name__)
        
        safety = await awareness.check_operation_safety(operation)
        
        if not safety["safe"]:
            return {
                "blocked": True,
                "reason": safety["reason"],
                "recommendation": safety["recommendation"]
            }
        
        return await func(*args, **kwargs)
    
    return wrapper


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_awareness: Optional[TradingAwareness] = None


def get_awareness() -> TradingAwareness:
    """Get or create global trading awareness."""
    global _awareness
    if _awareness is None:
        _awareness = TradingAwareness()
    return _awareness


async def check_trading_safety(operation: str) -> Dict:
    """Check if operation is safe for trading."""
    return await get_awareness().check_operation_safety(operation)


async def get_positions() -> str:
    """Get position summary."""
    return await get_awareness().get_position_summary()


async def get_signals() -> str:
    """Get signal summary."""
    return await get_awareness().get_signal_summary()


async def get_signal(symbol: str) -> str:
    """Get signal for a specific symbol."""
    return await get_awareness().get_symbol_signal(symbol)


async def get_market() -> str:
    """Get market summary."""
    return await get_awareness().get_market_summary()

