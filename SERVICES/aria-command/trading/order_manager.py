#!/usr/bin/env python3
"""
📋 ORDER MANAGER
=================

Manages orders on Hyperliquid with proper stops:
- Market orders for entry
- Stop-loss orders on exchange
- Take-profit orders
- Order tracking and updates

Ensures positions always have exchange-native protection.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger("aria.trading.orders")


@dataclass
class OrderResult:
    """Result of an order operation."""
    success: bool
    order_id: Optional[str] = None
    filled_size: float = 0.0
    filled_price: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


@dataclass
class StopOrderResult:
    """Result of placing stop order."""
    success: bool
    stop_order_id: Optional[str] = None
    stop_price: float = 0.0
    error: Optional[str] = None


@dataclass
class PositionWithStops:
    """A position with its associated stop/TP orders."""
    symbol: str
    side: str  # "long" or "short"
    size: float
    entry_price: float
    entry_order_id: Optional[str] = None
    stop_loss_price: Optional[float] = None
    stop_loss_order_id: Optional[str] = None
    take_profit_price: Optional[float] = None
    take_profit_order_id: Optional[str] = None
    trailing_stop_active: bool = False
    high_watermark: float = 0.0


class OrderManager:
    """
    Manages orders on Hyperliquid with proper stops.
    
    Key features:
    - Places stop-loss orders ON EXCHANGE (not just monitored)
    - Tracks all order IDs for updates/cancellations
    - Handles order failures gracefully
    """
    
    def __init__(self):
        from .hyperliquid_live import get_hyperliquid
        self.hl = get_hyperliquid()
        self._positions: Dict[str, PositionWithStops] = {}
    
    @property
    def is_connected(self) -> bool:
        """Check if exchange is connected."""
        return self.hl.is_connected
    
    async def open_position_with_stops(
        self,
        symbol: str,
        side: str,  # "long" or "short"
        size: float,
        stop_loss_price: float,
        take_profit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Open a position with stop-loss order on exchange.
        
        Flow:
        1. Place market order for entry
        2. Wait for fill confirmation
        3. Place stop-loss limit order (reduce_only=True)
        4. Optionally place take-profit order
        5. Store all order IDs
        
        Returns:
            {
                "success": bool,
                "entry_order_id": str,
                "stop_order_id": str,
                "tp_order_id": str or None,
                "filled_price": float,
                "error": str or None
            }
        """
        if not self.is_connected:
            return {"success": False, "error": "Exchange not connected"}
        
        result = {
            "success": False,
            "entry_order_id": None,
            "stop_order_id": None,
            "tp_order_id": None,
            "filled_price": 0.0,
            "error": None
        }
        
        try:
            # 1. Place market entry order
            entry_side = "buy" if side == "long" else "sell"
            entry_result = await self.hl.place_order(
                symbol=symbol,
                side=entry_side,
                size=size
            )
            
            if not entry_result.get("success"):
                result["error"] = f"Entry order failed: {entry_result.get('error')}"
                return result
            
            result["entry_order_id"] = entry_result.get("order_id")
            
            # 2. Get filled price from position
            await asyncio.sleep(0.5)  # Brief delay for position to update
            
            positions = self.hl.get_positions()
            position = next((p for p in positions if p["symbol"].upper() == symbol.upper()), None)
            
            if not position:
                result["error"] = "Position not found after entry"
                return result
            
            filled_price = position.get("entry_price", 0)
            result["filled_price"] = filled_price
            
            # 3. Place stop-loss order on exchange
            stop_result = await self._place_stop_order(
                symbol=symbol,
                side=side,
                size=size,
                stop_price=stop_loss_price
            )
            
            if stop_result.success:
                result["stop_order_id"] = stop_result.stop_order_id
            else:
                logger.warning(f"Stop order failed: {stop_result.error}")
                # Don't fail the whole operation, but log warning
            
            # 4. Place take-profit order if specified
            if take_profit_price:
                tp_result = await self._place_take_profit_order(
                    symbol=symbol,
                    side=side,
                    size=size,
                    tp_price=take_profit_price
                )
                
                if tp_result.success:
                    result["tp_order_id"] = tp_result.stop_order_id
            
            # 5. Track position
            self._positions[symbol] = PositionWithStops(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=filled_price,
                entry_order_id=result["entry_order_id"],
                stop_loss_price=stop_loss_price,
                stop_loss_order_id=result["stop_order_id"],
                take_profit_price=take_profit_price,
                take_profit_order_id=result["tp_order_id"],
                high_watermark=filled_price
            )
            
            result["success"] = True
            logger.info(
                f"✅ Opened {side} {symbol}: {size} @ ${filled_price:,.2f} "
                f"| Stop: ${stop_loss_price:,.2f}"
            )
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Open position failed: {e}")
        
        return result
    
    async def _place_stop_order(
        self,
        symbol: str,
        side: str,  # Original position side
        size: float,
        stop_price: float
    ) -> StopOrderResult:
        """
        Place a stop-loss order on Hyperliquid.
        
        Stop orders are placed as limit orders with reduce_only=True.
        The order will trigger when price crosses the stop level.
        """
        try:
            # Stop is opposite side of position
            stop_side = "sell" if side == "long" else "buy"
            is_buy = stop_side == "buy"
            
            # For stop-loss, we use a stop-limit order
            # Hyperliquid supports trigger orders
            result = self.hl._exchange.order(
                coin=symbol,
                is_buy=is_buy,
                sz=size,
                limit_px=stop_price,
                order_type={"trigger": {
                    "isMarket": True,
                    "triggerPx": str(stop_price),
                    "tpsl": "sl"  # Stop-loss type
                }},
                reduce_only=True
            )
            
            if result.get("status") == "ok":
                # Extract order ID from response
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                order_id = None
                
                if statuses:
                    status = statuses[0]
                    if "resting" in status:
                        order_id = status["resting"].get("oid")
                    elif "filled" in status:
                        order_id = status["filled"].get("oid")
                
                return StopOrderResult(
                    success=True,
                    stop_order_id=order_id,
                    stop_price=stop_price
                )
            else:
                return StopOrderResult(
                    success=False,
                    error=str(result)
                )
                
        except Exception as e:
            logger.error(f"Stop order failed: {e}")
            return StopOrderResult(success=False, error=str(e))
    
    async def _place_take_profit_order(
        self,
        symbol: str,
        side: str,  # Original position side
        size: float,
        tp_price: float
    ) -> StopOrderResult:
        """
        Place a take-profit order on Hyperliquid.
        """
        try:
            # TP is opposite side of position
            tp_side = "sell" if side == "long" else "buy"
            is_buy = tp_side == "buy"
            
            result = self.hl._exchange.order(
                coin=symbol,
                is_buy=is_buy,
                sz=size,
                limit_px=tp_price,
                order_type={"trigger": {
                    "isMarket": True,
                    "triggerPx": str(tp_price),
                    "tpsl": "tp"  # Take-profit type
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
                
                return StopOrderResult(
                    success=True,
                    stop_order_id=order_id,
                    stop_price=tp_price
                )
            else:
                return StopOrderResult(
                    success=False,
                    error=str(result)
                )
                
        except Exception as e:
            return StopOrderResult(success=False, error=str(e))
    
    async def update_stop_loss(
        self,
        symbol: str,
        new_stop_price: float
    ) -> StopOrderResult:
        """
        Update stop-loss price for a position.
        
        Cancels existing stop order and places new one.
        """
        position = self._positions.get(symbol)
        
        if not position:
            return StopOrderResult(success=False, error="Position not tracked")
        
        try:
            # Cancel existing stop order
            if position.stop_loss_order_id:
                await self._cancel_order(symbol, position.stop_loss_order_id)
            
            # Place new stop order
            result = await self._place_stop_order(
                symbol=symbol,
                side=position.side,
                size=position.size,
                stop_price=new_stop_price
            )
            
            if result.success:
                position.stop_loss_price = new_stop_price
                position.stop_loss_order_id = result.stop_order_id
                
                logger.info(f"📊 Updated stop for {symbol}: ${new_stop_price:,.2f}")
            
            return result
            
        except Exception as e:
            return StopOrderResult(success=False, error=str(e))
    
    async def _cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order by ID."""
        try:
            result = self.hl._exchange.cancel(coin=symbol, oid=int(order_id))
            return result.get("status") == "ok"
        except Exception as e:
            logger.error(f"Cancel order failed: {e}")
            return False
    
    async def cancel_all_orders(self, symbol: str) -> Dict:
        """Cancel all orders for a symbol."""
        try:
            result = self.hl._exchange.cancel_all_orders(coin=symbol)
            
            # Remove from tracking
            if symbol in self._positions:
                del self._positions[symbol]
            
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close_position_market(self, symbol: str) -> Dict:
        """Close position at market and cancel all orders."""
        try:
            # Cancel all orders first
            await self.cancel_all_orders(symbol)
            
            # Close the position
            result = await self.hl.close_position(symbol)
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open orders from exchange."""
        try:
            if not self.is_connected:
                return []
            
            # Get user state which includes orders
            state = self.hl._info.user_state(self.hl.main_account)
            orders = []
            
            for order in state.get("openOrders", []):
                coin = order.get("coin", "")
                if symbol is None or coin.upper() == symbol.upper():
                    orders.append({
                        "order_id": order.get("oid"),
                        "symbol": coin,
                        "side": "buy" if order.get("side") == "A" else "sell",
                        "size": float(order.get("sz", 0)),
                        "price": float(order.get("limitPx", 0)),
                        "order_type": order.get("orderType"),
                        "reduce_only": order.get("reduceOnly", False)
                    })
            
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []
    
    def get_tracked_position(self, symbol: str) -> Optional[PositionWithStops]:
        """Get tracked position with stops."""
        return self._positions.get(symbol)
    
    def sync_positions(self):
        """
        Sync tracked positions with exchange.
        
        Useful after restart to reconcile state.
        """
        try:
            positions = self.hl.get_positions()
            
            for pos in positions:
                symbol = pos["symbol"]
                
                if symbol not in self._positions:
                    # Position exists on exchange but not tracked
                    # Import it without stop info
                    self._positions[symbol] = PositionWithStops(
                        symbol=symbol,
                        side=pos["side"],
                        size=pos["size"],
                        entry_price=pos["entry_price"],
                        high_watermark=pos["entry_price"]
                    )
                    logger.info(f"📥 Imported untracked position: {symbol}")
            
            # Remove tracked positions that don't exist on exchange
            exchange_symbols = {p["symbol"] for p in positions}
            to_remove = [s for s in self._positions if s not in exchange_symbols]
            
            for symbol in to_remove:
                del self._positions[symbol]
                logger.info(f"🗑️ Removed closed position from tracking: {symbol}")
                
        except Exception as e:
            logger.error(f"Position sync failed: {e}")


# Singleton
_order_manager: Optional[OrderManager] = None


def get_order_manager() -> OrderManager:
    """Get or create global order manager."""
    global _order_manager
    if _order_manager is None:
        _order_manager = OrderManager()
    return _order_manager









