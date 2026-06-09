#!/usr/bin/env python3
"""
ARIA ULTRA POWER - STRATEGY EXECUTOR
=====================================

Trading strategy execution:
- Pre-defined strategies
- Signal + data + risk = decision
- Confidence-based execution tiers
- Backtest integration
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("aria.autopilot.strategy")


class StrategyType(Enum):
    """Types of trading strategies."""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"


class SignalStrength(Enum):
    """Signal strength levels."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WEAK_BUY = "weak_buy"
    NEUTRAL = "neutral"
    WEAK_SELL = "weak_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class StrategySignal:
    """A trading signal from a strategy."""
    strategy: str
    symbol: str
    strength: SignalStrength
    confidence: float  # 0-1
    action: str  # "LONG", "SHORT", "CLOSE", "HOLD"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    size_percent: float = 5.0  # % of portfolio
    leverage: float = 1.0
    reason: str = ""
    data: Dict = field(default_factory=dict)
    
    @property
    def requires_approval(self) -> bool:
        """Does this signal need user approval?"""
        if self.confidence >= 0.9 and self.strength in [SignalStrength.STRONG_BUY, SignalStrength.STRONG_SELL]:
            return False  # High confidence, auto-execute
        elif self.confidence >= 0.7:
            return True  # Medium confidence, quick approval
        else:
            return True  # Low confidence, needs discussion
    
    def to_dict(self) -> Dict:
        return {
            "strategy": self.strategy,
            "symbol": self.symbol,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "action": self.action,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "size_percent": self.size_percent,
            "leverage": self.leverage,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
        }


@dataclass
class TradingStrategy:
    """A trading strategy definition."""
    name: str
    strategy_type: StrategyType
    symbols: List[str]
    enabled: bool = True
    parameters: Dict = field(default_factory=dict)
    performance: Dict = field(default_factory=dict)  # Historical stats


class StrategyExecutor:
    """
    Execute trading strategies.
    
    Features:
    - Multiple strategy support
    - Confidence-based execution tiers
    - Signal aggregation
    - Performance tracking
    """
    
    # Confidence tiers
    CONFIDENCE_TIERS = {
        "auto": 0.90,      # Execute automatically, notify after
        "quick": 0.70,     # Ask for quick approval
        "discuss": 0.0,    # Full discussion before action
    }
    
    def __init__(self):
        self._strategies: Dict[str, TradingStrategy] = {}
        self._signal_history: List[StrategySignal] = []
        self._pending_signals: List[StrategySignal] = []
        
        # Register default strategies
        self._register_default_strategies()
        
        logger.info("StrategyExecutor initialized")
    
    def _register_default_strategies(self):
        """Register built-in strategies."""
        # Trend Following
        self._strategies["trend_follow"] = TradingStrategy(
            name="Trend Following",
            strategy_type=StrategyType.TREND_FOLLOWING,
            symbols=["SOL", "BTC", "ETH"],
            parameters={
                "timeframe": "4h",
                "lookback_periods": 20,
                "trend_threshold": 0.3,
            }
        )
        
        # WhaleTrack Signal Strategy
        self._strategies["whaletrack"] = TradingStrategy(
            name="WhaleTrack Signals",
            strategy_type=StrategyType.MOMENTUM,
            symbols=["SOL", "BTC", "ETH", "XRP"],
            parameters={
                "min_clarity": 60,
                "min_bias_strength": 25,
            }
        )
    
    async def generate_signals(self) -> List[StrategySignal]:
        """Generate signals from all active strategies."""
        signals = []
        
        for name, strategy in self._strategies.items():
            if not strategy.enabled:
                continue
            
            try:
                strategy_signals = await self._run_strategy(strategy)
                signals.extend(strategy_signals)
            except Exception as e:
                logger.error(f"Strategy {name} error: {e}")
        
        # Sort by confidence
        signals.sort(key=lambda s: s.confidence, reverse=True)
        
        return signals
    
    async def _run_strategy(self, strategy: TradingStrategy) -> List[StrategySignal]:
        """Run a single strategy."""
        if strategy.strategy_type == StrategyType.MOMENTUM:
            return await self._run_whaletrack_strategy(strategy)
        elif strategy.strategy_type == StrategyType.TREND_FOLLOWING:
            return await self._run_trend_strategy(strategy)
        else:
            return []
    
    async def _run_whaletrack_strategy(self, strategy: TradingStrategy) -> List[StrategySignal]:
        """Run WhaleTrack-based strategy."""
        signals = []
        
        try:
            from sovereign.intel.sentiment import get_unified_sentiment
            
            us = get_unified_sentiment()
            
            for symbol in strategy.symbols:
                sentiment = await us.get_sentiment(symbol)
                
                # Check minimum requirements
                min_clarity = strategy.parameters.get("min_clarity", 60)
                min_strength = strategy.parameters.get("min_bias_strength", 25)
                
                # Get WhaleTrack source
                wt_source = next((s for s in sentiment.sources if s.name == "WhaleTrack"), None)
                if not wt_source:
                    continue
                
                clarity = wt_source.details.get("clarity", 0)
                strength = abs(wt_source.score)
                
                if clarity < min_clarity or strength < min_strength:
                    continue
                
                # Generate signal
                if sentiment.action == "STRONG_BUY":
                    strength_enum = SignalStrength.STRONG_BUY
                    action = "LONG"
                elif sentiment.action == "BUY":
                    strength_enum = SignalStrength.BUY
                    action = "LONG"
                elif sentiment.action == "STRONG_SELL":
                    strength_enum = SignalStrength.STRONG_SELL
                    action = "SHORT"
                elif sentiment.action == "SELL":
                    strength_enum = SignalStrength.SELL
                    action = "SHORT"
                else:
                    continue  # HOLD = no signal
                
                signals.append(StrategySignal(
                    strategy="WhaleTrack Signals",
                    symbol=symbol,
                    strength=strength_enum,
                    confidence=sentiment.confidence,
                    action=action,
                    entry_price=wt_source.details.get("current_price"),
                    reason=f"Combined sentiment: {sentiment.score:+.0f}, Action: {sentiment.action}",
                    data=sentiment.to_dict(),
                ))
        
        except Exception as e:
            logger.error(f"WhaleTrack strategy error: {e}")
        
        return signals
    
    async def _run_trend_strategy(self, strategy: TradingStrategy) -> List[StrategySignal]:
        """Run trend following strategy."""
        signals = []
        
        # This would analyze price trends using the lookback period
        # Simplified for now - would integrate with price history
        
        return signals
    
    def get_execution_tier(self, signal: StrategySignal) -> str:
        """Determine execution tier based on confidence."""
        if signal.confidence >= self.CONFIDENCE_TIERS["auto"]:
            return "auto"
        elif signal.confidence >= self.CONFIDENCE_TIERS["quick"]:
            return "quick"
        else:
            return "discuss"
    
    async def execute_signal(self, signal: StrategySignal, approved: bool = False) -> Dict:
        """Execute a trading signal."""
        from .risk import get_risk_engine
        from .portfolio import get_portfolio_manager
        import httpx
        
        # Check risk first
        risk_engine = get_risk_engine()
        risk = await risk_engine.assess_risk()
        
        if not risk.can_trade and not approved:
            return {
                "success": False,
                "reason": f"Risk limit exceeded: {risk.reason}",
                "risk_assessment": risk.to_dict(),
            }
        
        # Check if approval needed
        tier = self.get_execution_tier(signal)
        if tier != "auto" and not approved:
            self._pending_signals.append(signal)
            return {
                "success": False,
                "reason": f"Approval required (tier: {tier})",
                "signal": signal.to_dict(),
                "tier": tier,
            }
        
        # Execute trade
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://198.54.123.234:8601/api/live/trade",
                    json={
                        "action": "open",
                        "asset": signal.symbol,
                        "side": signal.action,
                        "size_percent": signal.size_percent,
                        "leverage": signal.leverage,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit,
                    }
                )
                
                if response.status_code == 200:
                    self._signal_history.append(signal)
                    return {
                        "success": True,
                        "message": f"Executed {signal.action} on {signal.symbol}",
                        "signal": signal.to_dict(),
                        "trade_data": response.json(),
                    }
                else:
                    return {
                        "success": False,
                        "reason": f"Trade execution failed: {response.text}",
                    }
        
        except Exception as e:
            return {
                "success": False,
                "reason": f"Execution error: {str(e)}",
            }
    
    def get_pending_signals(self) -> List[StrategySignal]:
        """Get signals pending approval."""
        return self._pending_signals.copy()
    
    def approve_signal(self, index: int) -> Optional[StrategySignal]:
        """Approve a pending signal by index."""
        if 0 <= index < len(self._pending_signals):
            return self._pending_signals.pop(index)
        return None
    
    def reject_signal(self, index: int) -> bool:
        """Reject a pending signal by index."""
        if 0 <= index < len(self._pending_signals):
            self._pending_signals.pop(index)
            return True
        return False
    
    def get_strategies(self) -> Dict[str, TradingStrategy]:
        """Get all registered strategies."""
        return self._strategies.copy()
    
    def enable_strategy(self, name: str):
        """Enable a strategy."""
        if name in self._strategies:
            self._strategies[name].enabled = True
    
    def disable_strategy(self, name: str):
        """Disable a strategy."""
        if name in self._strategies:
            self._strategies[name].enabled = False
    
    def format_signal(self, signal: StrategySignal) -> str:
        """Format signal for display."""
        emoji_map = {
            SignalStrength.STRONG_BUY: "🟢🟢",
            SignalStrength.BUY: "🟢",
            SignalStrength.WEAK_BUY: "🟢",
            SignalStrength.NEUTRAL: "⚪",
            SignalStrength.WEAK_SELL: "🔴",
            SignalStrength.SELL: "🔴",
            SignalStrength.STRONG_SELL: "🔴🔴",
        }
        
        emoji = emoji_map.get(signal.strength, "⚪")
        tier = self.get_execution_tier(signal)
        
        lines = [
            f"{emoji} **{signal.symbol} Signal**",
            "",
            f"Action: {signal.action}",
            f"Strength: {signal.strength.value}",
            f"Confidence: {signal.confidence:.0%}",
            f"Tier: {tier}",
        ]
        
        if signal.entry_price:
            lines.append(f"Entry: ${signal.entry_price:,.2f}")
        if signal.stop_loss:
            lines.append(f"Stop: ${signal.stop_loss:,.2f}")
        if signal.take_profit:
            lines.append(f"Target: ${signal.take_profit:,.2f}")
        
        lines.append(f"Size: {signal.size_percent}% of portfolio")
        
        if signal.reason:
            lines.append("")
            lines.append(f"_{signal.reason}_")
        
        return "\n".join(lines)


# Singleton instance
_executor: Optional[StrategyExecutor] = None


def get_strategy_executor() -> StrategyExecutor:
    """Get global StrategyExecutor instance."""
    global _executor
    if _executor is None:
        _executor = StrategyExecutor()
    return _executor


