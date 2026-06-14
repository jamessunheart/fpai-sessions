#!/usr/bin/env python3
"""
💰 PARTIAL PROFIT TAKING SYSTEM
================================

Manages staged profit taking:
- Multiple take-profit targets
- Partial position closes at each target
- Move stop to breakeven after first TP
- Trail remaining position

Example:
  Entry: $100, Position: 1.0
  TP1 (+3%): Close 50% at $103 → Lock in profit
  TP2 (+6%): Close 30% at $106 → More profit
  Remaining 20%: Trail to maximum
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("aria.trading.profit_taker")

STEWARD_CHAT_ID = int(os.getenv("STEWARD_CHAT_ID", "1759822075"))


class TPState(Enum):
    """State of a take-profit order."""
    PENDING = "pending"       # Not yet placed
    PLACED = "placed"         # Order on exchange
    TRIGGERED = "triggered"   # Order filled
    CANCELLED = "cancelled"   # Cancelled


@dataclass
class ProfitTakeConfig:
    """Configuration for profit taking."""
    # First target
    take_profit_1_pct: float = 3.0    # First target: +3%
    take_profit_1_size: float = 0.5   # Take 50% at first target
    
    # Second target
    take_profit_2_pct: float = 6.0    # Second target: +6%
    take_profit_2_size: float = 0.3   # Take 30% at second
    
    # Third target (optional)
    take_profit_3_pct: float = 10.0   # Third target: +10%
    take_profit_3_size: float = 0.0   # Disabled by default
    
    # Remaining trails
    # (1 - tp1_size - tp2_size - tp3_size) = 20% trails to max
    
    # Behavior
    move_stop_to_breakeven_after_tp1: bool = True
    trail_remainder: bool = True


@dataclass
class TakeProfitOrder:
    """A take-profit order."""
    level: int  # 1, 2, 3
    price: float
    size: float  # Size to close
    size_pct: float  # Percentage of original position
    state: TPState = TPState.PENDING
    order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_at: Optional[datetime] = None


@dataclass
class ProfitTakePosition:
    """A position with profit-taking orders."""
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    original_size: float
    
    # TP orders
    tp_orders: List[TakeProfitOrder] = field(default_factory=list)
    
    # Tracking
    remaining_size: float = 0.0
    total_profit_taken: float = 0.0
    stop_moved_to_breakeven: bool = False
    
    # Config
    config: ProfitTakeConfig = field(default_factory=ProfitTakeConfig)
    
    def __post_init__(self):
        self.remaining_size = self.original_size


class ProfitTaker:
    """
    Manages partial profit taking for positions.
    
    Features:
    - Places multiple TP orders at different levels
    - Closes partial position at each level
    - Moves stop to breakeven after TP1
    - Trails remaining position for maximum gain
    """
    
    def __init__(self):
        from .order_manager import get_order_manager
        self.order_manager = get_order_manager()
        self._positions: Dict[str, ProfitTakePosition] = {}
    
    async def setup_profit_targets(
        self,
        symbol: str,
        entry_price: float,
        total_size: float,
        side: str,
        config: Optional[ProfitTakeConfig] = None
    ) -> Dict[str, Any]:
        """
        Set up profit-taking orders for a position.
        
        Places:
        1. TP1: 50% at +3%
        2. TP2: 30% at +6%
        3. Remaining 20%: Trailing stop
        """
        if config is None:
            config = ProfitTakeConfig()
        
        result = {
            "success": False,
            "orders_placed": 0,
            "tp_levels": [],
            "error": None
        }
        
        try:
            # Create position tracker
            position = ProfitTakePosition(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                original_size=total_size,
                config=config
            )
            
            # Calculate TP prices and sizes
            tp_configs = [
                (1, config.take_profit_1_pct, config.take_profit_1_size),
                (2, config.take_profit_2_pct, config.take_profit_2_size),
                (3, config.take_profit_3_pct, config.take_profit_3_size),
            ]
            
            for level, pct, size_pct in tp_configs:
                if size_pct <= 0:
                    continue
                
                # Calculate TP price
                if side == "long":
                    tp_price = entry_price * (1 + pct / 100)
                else:
                    tp_price = entry_price * (1 - pct / 100)
                
                # Calculate size to close
                tp_size = total_size * size_pct
                
                tp_order = TakeProfitOrder(
                    level=level,
                    price=tp_price,
                    size=tp_size,
                    size_pct=size_pct
                )
                
                position.tp_orders.append(tp_order)
            
            # Place TP orders on exchange
            for tp_order in position.tp_orders:
                place_result = await self._place_tp_order(
                    symbol=symbol,
                    side=side,
                    size=tp_order.size,
                    tp_price=tp_order.price
                )
                
                if place_result.get("success"):
                    tp_order.state = TPState.PLACED
                    tp_order.order_id = place_result.get("order_id")
                    result["orders_placed"] += 1
                    
                    result["tp_levels"].append({
                        "level": tp_order.level,
                        "price": tp_order.price,
                        "size_pct": tp_order.size_pct * 100,
                        "profit_pct": self._calc_profit_pct(entry_price, tp_order.price, side)
                    })
                    
                    logger.info(
                        f"💰 TP{tp_order.level} placed: {tp_order.size_pct*100:.0f}% "
                        f"@ ${tp_order.price:,.2f}"
                    )
                else:
                    logger.warning(f"Failed to place TP{tp_order.level}: {place_result.get('error')}")
            
            # Store position
            self._positions[symbol] = position
            
            result["success"] = result["orders_placed"] > 0
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Failed to set up profit targets: {e}")
        
        return result
    
    async def _place_tp_order(
        self,
        symbol: str,
        side: str,  # Original position side
        size: float,
        tp_price: float
    ) -> Dict:
        """Place a take-profit order on exchange."""
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            if not hl.is_connected:
                return {"success": False, "error": "Not connected"}
            
            # TP is opposite side of position
            tp_side = "sell" if side == "long" else "buy"
            is_buy = tp_side == "buy"
            
            # Place take-profit trigger order
            result = hl._exchange.order(
                coin=symbol,
                is_buy=is_buy,
                sz=size,
                limit_px=tp_price,
                order_type={"trigger": {
                    "isMarket": True,
                    "triggerPx": str(tp_price),
                    "tpsl": "tp"
                }},
                reduce_only=True
            )
            
            if result.get("status") == "ok":
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                order_id = None
                
                if statuses:
                    status = statuses[0]
                    if "resting" in status:
                        order_id = status["resting"].get("oid")
                
                return {"success": True, "order_id": order_id}
            else:
                return {"success": False, "error": str(result)}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calc_profit_pct(self, entry: float, target: float, side: str) -> float:
        """Calculate profit percentage."""
        if side == "long":
            return (target - entry) / entry * 100
        else:
            return (entry - target) / entry * 100
    
    async def on_partial_fill(self, symbol: str, filled_price: float, filled_size: float):
        """
        Called when a TP order fills.
        
        Actions:
        1. Update position tracking
        2. Move stop-loss to breakeven after TP1
        3. Notify steward of partial profit
        """
        position = self._positions.get(symbol)
        if not position:
            return
        
        try:
            # Find which TP was filled
            for tp_order in position.tp_orders:
                if tp_order.state == TPState.PLACED:
                    # Check if this price matches
                    if abs(filled_price - tp_order.price) / tp_order.price < 0.01:
                        tp_order.state = TPState.TRIGGERED
                        tp_order.filled_price = filled_price
                        tp_order.filled_at = datetime.now()
                        
                        # Calculate profit
                        profit = self._calc_partial_profit(
                            position.entry_price,
                            filled_price,
                            filled_size,
                            position.side
                        )
                        position.total_profit_taken += profit
                        position.remaining_size -= filled_size
                        
                        logger.info(
                            f"💰 TP{tp_order.level} triggered: "
                            f"+${profit:,.2f} profit"
                        )
                        
                        # Move stop to breakeven after TP1
                        if tp_order.level == 1 and position.config.move_stop_to_breakeven_after_tp1:
                            await self._move_stop_to_breakeven(position)
                        
                        # Notify steward
                        await self._notify_partial_profit(position, tp_order, profit)
                        
                        break
                        
        except Exception as e:
            logger.error(f"Error handling TP fill: {e}")
    
    def _calc_partial_profit(
        self,
        entry: float,
        exit_price: float,
        size: float,
        side: str
    ) -> float:
        """Calculate profit from partial close."""
        if side == "long":
            return (exit_price - entry) * size
        else:
            return (entry - exit_price) * size
    
    async def _move_stop_to_breakeven(self, position: ProfitTakePosition):
        """Move stop-loss to breakeven after TP1."""
        if position.stop_moved_to_breakeven:
            return
        
        try:
            result = await self.order_manager.update_stop_loss(
                symbol=position.symbol,
                new_stop_price=position.entry_price
            )
            
            if result.success:
                position.stop_moved_to_breakeven = True
                logger.info(
                    f"🛡️ Stop moved to breakeven for {position.symbol} "
                    f"@ ${position.entry_price:,.2f}"
                )
            else:
                logger.warning(f"Failed to move stop: {result.error}")
                
        except Exception as e:
            logger.error(f"Error moving stop: {e}")
    
    async def _notify_partial_profit(
        self,
        position: ProfitTakePosition,
        tp_order: TakeProfitOrder,
        profit: float
    ):
        """Notify steward of partial profit taken."""
        try:
            from telegram.bot import send_message
            
            profit_pct = self._calc_profit_pct(
                position.entry_price,
                tp_order.filled_price,
                position.side
            )
            
            remaining_pct = (position.remaining_size / position.original_size) * 100
            
            message = f"""💰 **PARTIAL PROFIT TAKEN**

**{position.side.upper()} {position.symbol}**
• TP Level: {tp_order.level}
• Closed: {tp_order.size_pct*100:.0f}% @ ${tp_order.filled_price:,.2f}
• Profit: **+${profit:,.2f}** (+{profit_pct:.1f}%)

**Position Status:**
• Remaining: {remaining_pct:.0f}%
• Total Profit Taken: **${position.total_profit_taken:,.2f}**
• Stop at Breakeven: {'✅' if position.stop_moved_to_breakeven else '❌'}"""
            
            await send_message(STEWARD_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Failed to notify: {e}")
    
    def get_position_status(self, symbol: str) -> Optional[Dict]:
        """Get profit-taking status for a position."""
        position = self._positions.get(symbol)
        if not position:
            return None
        
        return {
            "symbol": position.symbol,
            "side": position.side,
            "entry_price": position.entry_price,
            "original_size": position.original_size,
            "remaining_size": position.remaining_size,
            "remaining_pct": position.remaining_size / position.original_size * 100,
            "total_profit_taken": position.total_profit_taken,
            "stop_at_breakeven": position.stop_moved_to_breakeven,
            "tp_orders": [
                {
                    "level": tp.level,
                    "price": tp.price,
                    "size_pct": tp.size_pct * 100,
                    "state": tp.state.value,
                    "filled_price": tp.filled_price
                }
                for tp in position.tp_orders
            ]
        }
    
    async def cancel_profit_targets(self, symbol: str) -> bool:
        """Cancel all profit-taking orders for a position."""
        position = self._positions.get(symbol)
        if not position:
            return False
        
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            for tp_order in position.tp_orders:
                if tp_order.state == TPState.PLACED and tp_order.order_id:
                    try:
                        hl._exchange.cancel(coin=symbol, oid=int(tp_order.order_id))
                        tp_order.state = TPState.CANCELLED
                    except:
                        pass
            
            del self._positions[symbol]
            logger.info(f"🛑 Cancelled profit targets for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel profit targets: {e}")
            return False


# Singleton
_profit_taker: Optional[ProfitTaker] = None


def get_profit_taker() -> ProfitTaker:
    """Get or create global profit taker."""
    global _profit_taker
    if _profit_taker is None:
        _profit_taker = ProfitTaker()
    return _profit_taker









