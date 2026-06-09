#!/usr/bin/env python3
"""
🎯 TRAILING STOP SYSTEM
========================

Manages trailing stops for open positions:
- Activates after position reaches profit threshold
- Trails behind price at configurable distance
- Updates stop orders on exchange automatically
- Locks in profits as price moves favorably

Example:
  Entry: $100
  Activation: 2% profit ($102)
  Trail: 1.5% behind high
  
  Price hits $105 → Stop at $103.43
  Price hits $110 → Stop at $108.35
  Price drops to $108.35 → STOP TRIGGERED, profit locked!
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("aria.trading.trailing")


class TrailingState(Enum):
    """State of trailing stop."""
    INACTIVE = "inactive"        # Waiting for activation
    ACTIVE = "active"            # Trailing engaged
    TRIGGERED = "triggered"      # Stop was hit
    CANCELLED = "cancelled"      # Manually cancelled


@dataclass
class TrailingStopConfig:
    """Configuration for trailing stops."""
    activation_pct: float = 2.0      # Activate after 2% profit
    trail_pct: float = 1.5           # Trail 1.5% behind high/low
    step_size: float = 0.5           # Move stop in 0.5% steps (reduce updates)
    min_profit_pct: float = 0.5      # Minimum profit to lock in when trailing
    update_interval_seconds: int = 5  # How often to check prices


@dataclass
class TrailingPosition:
    """A position being monitored for trailing stop."""
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    size: float
    
    # Trailing state
    state: TrailingState = TrailingState.INACTIVE
    high_watermark: float = 0.0       # Highest price seen (for longs)
    low_watermark: float = float('inf')  # Lowest price seen (for shorts)
    current_stop: float = 0.0         # Current stop price
    stop_order_id: Optional[str] = None
    
    # Config
    config: TrailingStopConfig = field(default_factory=TrailingStopConfig)
    
    # Timestamps
    activated_at: Optional[datetime] = None
    last_update: Optional[datetime] = None
    
    @property
    def activation_price(self) -> float:
        """Price at which trailing activates."""
        if self.side == "long":
            return self.entry_price * (1 + self.config.activation_pct / 100)
        else:
            return self.entry_price * (1 - self.config.activation_pct / 100)
    
    def should_activate(self, current_price: float) -> bool:
        """Check if trailing should activate."""
        if self.state != TrailingState.INACTIVE:
            return False
        
        if self.side == "long":
            return current_price >= self.activation_price
        else:
            return current_price <= self.activation_price
    
    def calculate_stop_price(self, reference_price: float) -> float:
        """Calculate stop price based on reference (high/low watermark)."""
        if self.side == "long":
            # Stop below the high
            return reference_price * (1 - self.config.trail_pct / 100)
        else:
            # Stop above the low
            return reference_price * (1 + self.config.trail_pct / 100)
    
    def should_update_stop(self, new_stop: float) -> bool:
        """
        Check if stop should be updated.
        Uses step_size to avoid too many updates.
        """
        if self.current_stop == 0:
            return True
        
        if self.side == "long":
            # Only update if new stop is higher by at least step_size%
            min_improvement = self.current_stop * (1 + self.config.step_size / 100)
            return new_stop >= min_improvement
        else:
            # Only update if new stop is lower by at least step_size%
            max_improvement = self.current_stop * (1 - self.config.step_size / 100)
            return new_stop <= max_improvement


class TrailingStopManager:
    """
    Manages trailing stops for multiple positions.
    
    Features:
    - Monitors price continuously
    - Updates stops on exchange when price moves favorably
    - Handles activation, trailing, and triggering
    """
    
    def __init__(self):
        from .order_manager import get_order_manager
        self.order_manager = get_order_manager()
        self._positions: Dict[str, TrailingPosition] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, symbol: str, position: TrailingPosition):
        """
        Start monitoring a position for trailing stop.
        
        Called when a new position is opened.
        """
        self._positions[symbol] = position
        logger.info(
            f"🎯 Started trailing monitor for {symbol} "
            f"(activate at {position.config.activation_pct}% profit)"
        )
        
        # Ensure the monitoring loop is running
        if not self._running:
            await self.start()
    
    async def stop_monitoring(self, symbol: str):
        """Stop monitoring a position."""
        if symbol in self._positions:
            del self._positions[symbol]
            logger.info(f"🎯 Stopped trailing monitor for {symbol}")
    
    async def start(self):
        """Start the trailing stop monitoring loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("🎯 Trailing stop manager started")
    
    async def stop(self):
        """Stop the trailing stop monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🎯 Trailing stop manager stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_all_positions()
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trailing monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _check_all_positions(self):
        """Check all positions and update trailing stops."""
        if not self._positions:
            return
        
        # Get current prices from Hyperliquid
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            if not hl.is_connected:
                return
            
            exchange_positions = hl.get_positions()
            price_map = {p["symbol"]: p["mark_price"] for p in exchange_positions}
            
        except Exception as e:
            logger.error(f"Failed to get prices: {e}")
            return
        
        # Check each trailing position
        for symbol, trailing in list(self._positions.items()):
            current_price = price_map.get(symbol)
            
            if current_price is None:
                # Position might be closed
                continue
            
            await self._process_position(trailing, current_price)
    
    async def _process_position(self, pos: TrailingPosition, current_price: float):
        """Process a single position for trailing stop."""
        
        # Update watermarks
        if pos.side == "long":
            if current_price > pos.high_watermark:
                pos.high_watermark = current_price
        else:
            if current_price < pos.low_watermark:
                pos.low_watermark = current_price
        
        # Check for activation
        if pos.state == TrailingState.INACTIVE:
            if pos.should_activate(current_price):
                await self._activate_trailing(pos, current_price)
                return
        
        # Check for stop updates
        elif pos.state == TrailingState.ACTIVE:
            await self._update_trailing(pos, current_price)
    
    async def _activate_trailing(self, pos: TrailingPosition, current_price: float):
        """Activate trailing stop for a position."""
        pos.state = TrailingState.ACTIVE
        pos.activated_at = datetime.now()
        
        # Set initial watermark
        if pos.side == "long":
            pos.high_watermark = current_price
        else:
            pos.low_watermark = current_price
        
        # Calculate initial stop
        reference = pos.high_watermark if pos.side == "long" else pos.low_watermark
        new_stop = pos.calculate_stop_price(reference)
        
        # Place or update stop order on exchange
        result = await self.order_manager.update_stop_loss(pos.symbol, new_stop)
        
        if result.success:
            pos.current_stop = new_stop
            pos.stop_order_id = result.stop_order_id
            pos.last_update = datetime.now()
            
            profit_pct = abs(current_price - pos.entry_price) / pos.entry_price * 100
            
            logger.info(
                f"✨ Trailing ACTIVATED for {pos.symbol} "
                f"(+{profit_pct:.1f}% profit, stop at ${new_stop:,.2f})"
            )
            
            # Send notification
            await self._notify_activation(pos, current_price, new_stop)
        else:
            logger.error(f"Failed to place trailing stop: {result.error}")
    
    async def _update_trailing(self, pos: TrailingPosition, current_price: float):
        """Update trailing stop if price moved favorably."""
        
        # Determine reference price (high or low watermark)
        if pos.side == "long":
            reference = pos.high_watermark
        else:
            reference = pos.low_watermark
        
        # Calculate new stop
        new_stop = pos.calculate_stop_price(reference)
        
        # Check if update needed
        if not pos.should_update_stop(new_stop):
            return
        
        # Validate new stop locks in profit
        if pos.side == "long":
            if new_stop <= pos.entry_price:
                return  # Don't update if it would be at or below entry
        else:
            if new_stop >= pos.entry_price:
                return  # Don't update if it would be at or above entry
        
        # Update stop on exchange
        result = await self.order_manager.update_stop_loss(pos.symbol, new_stop)
        
        if result.success:
            old_stop = pos.current_stop
            pos.current_stop = new_stop
            pos.stop_order_id = result.stop_order_id
            pos.last_update = datetime.now()
            
            logger.info(
                f"📈 Trailing updated for {pos.symbol}: "
                f"${old_stop:,.2f} → ${new_stop:,.2f}"
            )
    
    async def _notify_activation(self, pos: TrailingPosition, price: float, stop: float):
        """Send notification when trailing activates."""
        try:
            from telegram.bot import send_message
            
            STEWARD_CHAT_ID = int(os.getenv("STEWARD_CHAT_ID", "1759822075"))
            
            profit_pct = abs(price - pos.entry_price) / pos.entry_price * 100
            locked_profit_pct = abs(stop - pos.entry_price) / pos.entry_price * 100
            
            message = f"""🎯 **TRAILING STOP ACTIVATED**

**{pos.side.upper()} {pos.symbol}**
• Entry: ${pos.entry_price:,.2f}
• Current: ${price:,.2f} (+{profit_pct:.1f}%)
• Trailing Stop: **${stop:,.2f}**
• Locked Profit: **{locked_profit_pct:.1f}%**

_Stop will trail {pos.config.trail_pct}% behind price_"""
            
            await send_message(STEWARD_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def get_position_status(self, symbol: str) -> Optional[Dict]:
        """Get trailing stop status for a position."""
        pos = self._positions.get(symbol)
        
        if not pos:
            return None
        
        return {
            "symbol": pos.symbol,
            "side": pos.side,
            "state": pos.state.value,
            "entry_price": pos.entry_price,
            "activation_price": pos.activation_price,
            "high_watermark": pos.high_watermark,
            "low_watermark": pos.low_watermark,
            "current_stop": pos.current_stop,
            "activated_at": pos.activated_at.isoformat() if pos.activated_at else None,
            "config": {
                "activation_pct": pos.config.activation_pct,
                "trail_pct": pos.config.trail_pct,
                "step_size": pos.config.step_size
            }
        }
    
    def get_all_status(self) -> List[Dict]:
        """Get status of all trailing positions."""
        return [
            self.get_position_status(symbol)
            for symbol in self._positions
        ]


# Singleton
_trailing_manager: Optional[TrailingStopManager] = None


def get_trailing_manager() -> TrailingStopManager:
    """Get or create global trailing stop manager."""
    global _trailing_manager
    if _trailing_manager is None:
        _trailing_manager = TrailingStopManager()
    return _trailing_manager


async def start_trailing_for_position(
    symbol: str,
    side: str,
    entry_price: float,
    size: float,
    config: Optional[TrailingStopConfig] = None
):
    """
    Convenience function to start trailing for a new position.
    """
    manager = get_trailing_manager()
    
    position = TrailingPosition(
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        size=size,
        high_watermark=entry_price if side == "long" else float('inf'),
        low_watermark=entry_price if side == "short" else float('inf'),
        config=config or TrailingStopConfig()
    )
    
    await manager.start_monitoring(symbol, position)









