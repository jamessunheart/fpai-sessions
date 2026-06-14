#!/usr/bin/env python3
"""
⏰ TIME-BASED EXIT RULES
========================

Manages time-based position exits:
- Maximum hold time (e.g., 24 hours)
- Stall detection (no movement)
- Weekend close (avoid gaps)
- High-impact news avoidance

Exit positions based on time conditions,
not just price movements.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import calendar

logger = logging.getLogger("aria.trading.time_rules")

STEWARD_CHAT_ID = int(os.getenv("STEWARD_CHAT_ID", "1759822075"))


class TimeExitReason(Enum):
    """Reasons for time-based exit."""
    MAX_HOLD = "max_hold_exceeded"
    STALLED = "position_stalled"
    WEEKEND = "weekend_close"
    NEWS = "high_impact_news"
    MANUAL = "manual_exit"


@dataclass
class TimeRules:
    """Configuration for time-based exits."""
    # Maximum hold time
    max_hold_hours: int = 24            # Exit after 24 hours
    
    # Stall detection
    stall_threshold_pct: float = 0.5    # If < 0.5% move in stall_hours
    stall_hours: int = 4                # Time window for stall detection
    
    # Weekend handling
    weekend_close: bool = True          # Close before weekend
    weekend_close_day: int = 4          # Friday = 4
    weekend_close_hour: int = 20        # 8 PM UTC
    
    # Loss cut timing
    exit_losing_trades_faster: bool = True
    losing_trade_max_hours: int = 8     # Cut losers faster


@dataclass
class TimeExitSignal:
    """Signal to exit a position based on time."""
    symbol: str
    reason: TimeExitReason
    message: str
    urgency: str = "normal"  # normal, high, critical
    details: Dict = field(default_factory=dict)


@dataclass
class TimeTrackedPosition:
    """A position being tracked for time-based exits."""
    symbol: str
    entry_time: datetime
    entry_price: float
    side: str
    
    # Price tracking for stall detection
    price_history: List[Dict] = field(default_factory=list)
    
    # Rules
    rules: TimeRules = field(default_factory=TimeRules)
    
    @property
    def hold_hours(self) -> float:
        """Hours since entry."""
        return (datetime.now() - self.entry_time).total_seconds() / 3600
    
    def record_price(self, price: float):
        """Record price for stall detection."""
        self.price_history.append({
            "price": price,
            "time": datetime.now()
        })
        
        # Keep only last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        self.price_history = [
            p for p in self.price_history
            if p["time"] > cutoff
        ]
    
    def is_stalled(self) -> bool:
        """Check if price has stalled."""
        if len(self.price_history) < 2:
            return False
        
        # Get prices from stall window
        cutoff = datetime.now() - timedelta(hours=self.rules.stall_hours)
        recent_prices = [
            p["price"] for p in self.price_history
            if p["time"] > cutoff
        ]
        
        if len(recent_prices) < 2:
            return False
        
        # Check price range
        high = max(recent_prices)
        low = min(recent_prices)
        
        if low == 0:
            return False
        
        range_pct = (high - low) / low * 100
        
        return range_pct < self.rules.stall_threshold_pct


class TimeBasedExitManager:
    """
    Manages time-based exit rules for positions.
    
    Features:
    - Monitors all positions for time conditions
    - Generates exit signals when rules trigger
    - Handles weekend closes
    - Detects stalled positions
    """
    
    def __init__(self):
        self._positions: Dict[str, TimeTrackedPosition] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.rules = TimeRules()
    
    async def track_position(
        self,
        symbol: str,
        entry_time: datetime,
        entry_price: float,
        side: str,
        rules: Optional[TimeRules] = None
    ):
        """Start tracking a position for time-based exits."""
        position = TimeTrackedPosition(
            symbol=symbol,
            entry_time=entry_time,
            entry_price=entry_price,
            side=side,
            rules=rules or self.rules
        )
        position.record_price(entry_price)
        
        self._positions[symbol] = position
        logger.info(f"⏰ Started time tracking for {symbol}")
    
    async def stop_tracking(self, symbol: str):
        """Stop tracking a position."""
        if symbol in self._positions:
            del self._positions[symbol]
            logger.info(f"⏰ Stopped time tracking for {symbol}")
    
    async def start(self):
        """Start the time-based exit monitoring loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("⏰ Time-based exit manager started")
    
    async def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("⏰ Time-based exit manager stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                exits = await self.check_time_exits()
                
                for exit_signal in exits:
                    await self._process_exit_signal(exit_signal)
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Time monitor error: {e}")
                await asyncio.sleep(60)
    
    async def check_time_exits(self) -> List[TimeExitSignal]:
        """
        Check all positions for time-based exits.
        
        Returns list of exit signals.
        """
        exits = []
        
        if not self._positions:
            return exits
        
        # Update prices
        await self._update_prices()
        
        now = datetime.now()
        
        for symbol, position in list(self._positions.items()):
            exit_signal = self._check_position(position, now)
            if exit_signal:
                exits.append(exit_signal)
        
        return exits
    
    async def _update_prices(self):
        """Update current prices for all tracked positions."""
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            if not hl.is_connected:
                return
            
            prices = hl.get_prices()
            
            for symbol, position in self._positions.items():
                if symbol in prices:
                    position.record_price(prices[symbol])
                    
        except Exception as e:
            logger.error(f"Failed to update prices: {e}")
    
    def _check_position(
        self,
        position: TimeTrackedPosition,
        now: datetime
    ) -> Optional[TimeExitSignal]:
        """Check a single position for time-based exit."""
        
        # 1. Check max hold time
        max_hours = position.rules.max_hold_hours
        
        # Use faster exit for losing trades
        if position.rules.exit_losing_trades_faster:
            if position.price_history:
                current = position.price_history[-1]["price"]
                is_losing = (
                    (position.side == "long" and current < position.entry_price) or
                    (position.side == "short" and current > position.entry_price)
                )
                if is_losing:
                    max_hours = position.rules.losing_trade_max_hours
        
        if position.hold_hours >= max_hours:
            return TimeExitSignal(
                symbol=position.symbol,
                reason=TimeExitReason.MAX_HOLD,
                message=f"Position held for {position.hold_hours:.1f} hours (max: {max_hours}h)",
                urgency="high",
                details={"hold_hours": position.hold_hours, "max_hours": max_hours}
            )
        
        # 2. Check for stalled position
        if position.is_stalled():
            return TimeExitSignal(
                symbol=position.symbol,
                reason=TimeExitReason.STALLED,
                message=f"Position stalled (< {position.rules.stall_threshold_pct}% move in {position.rules.stall_hours}h)",
                urgency="normal",
                details={"stall_hours": position.rules.stall_hours}
            )
        
        # 3. Check for weekend close
        if position.rules.weekend_close:
            if self._should_close_for_weekend(now, position.rules):
                return TimeExitSignal(
                    symbol=position.symbol,
                    reason=TimeExitReason.WEEKEND,
                    message="Closing before weekend to avoid gap risk",
                    urgency="high",
                    details={"close_by": "Friday 8PM UTC"}
                )
        
        return None
    
    def _should_close_for_weekend(self, now: datetime, rules: TimeRules) -> bool:
        """Check if position should be closed for weekend."""
        weekday = now.weekday()  # Monday = 0, Sunday = 6
        hour = now.hour
        
        # Friday after close hour
        if weekday == rules.weekend_close_day and hour >= rules.weekend_close_hour:
            return True
        
        # Saturday or Sunday
        if weekday in [5, 6]:
            return True
        
        return False
    
    async def _process_exit_signal(self, signal: TimeExitSignal):
        """Process a time-based exit signal."""
        try:
            logger.info(
                f"⏰ Time exit triggered for {signal.symbol}: "
                f"{signal.reason.value} - {signal.message}"
            )
            
            # Notify steward
            await self._notify_time_exit(signal)
            
            # Execute the exit
            from .order_manager import get_order_manager
            order_manager = get_order_manager()
            
            result = await order_manager.close_position_market(signal.symbol)
            
            if result.get("success"):
                await self.stop_tracking(signal.symbol)
                logger.info(f"✅ Time-based exit completed for {signal.symbol}")
            else:
                logger.error(f"Failed to execute time exit: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error processing time exit: {e}")
    
    async def _notify_time_exit(self, signal: TimeExitSignal):
        """Notify steward of time-based exit."""
        try:
            from telegram.bot import send_message
            
            emoji = {
                TimeExitReason.MAX_HOLD: "⏰",
                TimeExitReason.STALLED: "😴",
                TimeExitReason.WEEKEND: "📅",
                TimeExitReason.NEWS: "📰"
            }.get(signal.reason, "⏰")
            
            message = f"""{emoji} **TIME-BASED EXIT**

**{signal.symbol}**
• Reason: {signal.reason.value.replace('_', ' ').title()}
• {signal.message}
• Urgency: {signal.urgency.upper()}

_Closing position automatically_"""
            
            await send_message(STEWARD_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Failed to notify: {e}")
    
    def should_exit_for_time(
        self,
        position: TimeTrackedPosition,
        current_time: datetime
    ) -> Optional[str]:
        """
        Check if a position should exit for time reasons.
        
        Returns exit reason or None.
        """
        signal = self._check_position(position, current_time)
        return signal.reason.value if signal else None
    
    def get_status(self) -> Dict:
        """Get status of all tracked positions."""
        return {
            "running": self._running,
            "tracked_positions": len(self._positions),
            "positions": [
                {
                    "symbol": p.symbol,
                    "entry_time": p.entry_time.isoformat(),
                    "hold_hours": round(p.hold_hours, 2),
                    "is_stalled": p.is_stalled(),
                    "max_hold_hours": p.rules.max_hold_hours
                }
                for p in self._positions.values()
            ]
        }


# Singleton
_time_exit_manager: Optional[TimeBasedExitManager] = None


def get_time_exit_manager() -> TimeBasedExitManager:
    """Get or create global time exit manager."""
    global _time_exit_manager
    if _time_exit_manager is None:
        _time_exit_manager = TimeBasedExitManager()
    return _time_exit_manager









