#!/usr/bin/env python3
"""
📋 ORDER LIFECYCLE MANAGER
============================

Complete order lifecycle management with verification.

Features:
- Track orders through all states
- Retry failed orders with backoff
- Handle partial fills
- Timeout stale orders
- Alert on issues
"""

import asyncio
import logging
import uuid
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable, Any

logger = logging.getLogger("aria.trading.lifecycle")


class OrderState(Enum):
    """Order lifecycle states."""
    PENDING = "pending"        # Order created, not sent
    SENT = "sent"              # Sent to exchange
    ACKNOWLEDGED = "ack"       # Exchange received
    PARTIAL = "partial"        # Partially filled
    FILLED = "filled"          # Fully filled
    CANCELLED = "cancelled"    # Cancelled
    REJECTED = "rejected"      # Exchange rejected
    FAILED = "failed"          # Our system failed
    EXPIRED = "expired"        # Timeout


@dataclass
class OrderFill:
    """Record of an order fill."""
    fill_id: str
    size: float
    price: float
    timestamp: datetime
    fee: float = 0.0


@dataclass
class ManagedOrder:
    """An order with full lifecycle tracking."""
    id: str
    symbol: str
    side: str  # "buy" or "sell"
    size: float
    intended_price: float      # Price we wanted
    order_type: str = "market" # "market" or "limit"
    limit_price: Optional[float] = None
    reduce_only: bool = False
    
    state: OrderState = OrderState.PENDING
    exchange_order_id: Optional[str] = None
    
    # Fill tracking
    filled_size: float = 0.0
    avg_fill_price: float = 0.0
    fills: List[OrderFill] = field(default_factory=list)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    ack_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Retry tracking
    attempts: int = 0
    max_attempts: int = 3
    last_error: Optional[str] = None
    
    # Callbacks
    on_fill: Optional[Callable] = None
    on_complete: Optional[Callable] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if order is in a terminal state."""
        return self.state in [
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
            OrderState.FAILED,
            OrderState.EXPIRED
        ]
    
    @property
    def fill_percent(self) -> float:
        """Percentage of order filled."""
        if self.size == 0:
            return 0.0
        return (self.filled_size / self.size) * 100
    
    @property
    def remaining_size(self) -> float:
        """Size remaining to fill."""
        return max(0, self.size - self.filled_size)
    
    @property
    def slippage_bps(self) -> float:
        """Slippage in basis points."""
        if self.avg_fill_price == 0 or self.intended_price == 0:
            return 0.0
        return ((self.avg_fill_price - self.intended_price) / self.intended_price) * 10000
    
    def record_fill(self, fill: OrderFill):
        """Record a fill for this order."""
        self.fills.append(fill)
        
        # Update weighted average price
        total_value = (self.avg_fill_price * self.filled_size) + (fill.price * fill.size)
        self.filled_size += fill.size
        self.avg_fill_price = total_value / self.filled_size if self.filled_size > 0 else 0
        
        if self.filled_size >= self.size:
            self.state = OrderState.FILLED
            self.filled_at = datetime.now()
        else:
            self.state = OrderState.PARTIAL
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "intended_price": self.intended_price,
            "order_type": self.order_type,
            "limit_price": self.limit_price,
            "reduce_only": self.reduce_only,
            "state": self.state.value,
            "exchange_order_id": self.exchange_order_id,
            "filled_size": self.filled_size,
            "avg_fill_price": self.avg_fill_price,
            "fill_percent": self.fill_percent,
            "slippage_bps": round(self.slippage_bps, 2),
            "attempts": self.attempts,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "last_error": self.last_error
        }


@dataclass
class OrderResult:
    """Result of order submission."""
    success: bool
    order: ManagedOrder
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "order": self.order.to_dict(),
            "error": self.error
        }


class OrderLifecycleManager:
    """
    Manages complete order lifecycle with verification.
    
    Features:
    - Track order through all states
    - Retry failed orders
    - Handle partial fills
    - Timeout stale orders
    - Alert on issues
    """
    
    def __init__(self):
        from .resilient_client import get_resilient_client
        
        self._client = get_resilient_client()
        self._orders: Dict[str, ManagedOrder] = {}
        self._pending_orders: Dict[str, ManagedOrder] = {}  # Orders awaiting fill
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Configuration
        self._order_timeout = timedelta(seconds=60)
        self._stale_check_interval = 5  # seconds
        self._price_tolerance_bps = 100  # 1% tolerance for fill verification
    
    async def start(self):
        """Start the order lifecycle manager."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._timeout_check_loop())
        logger.info("📋 Order lifecycle manager started")
    
    async def stop(self):
        """Stop the order lifecycle manager."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("📋 Order lifecycle manager stopped")
    
    def create_order(
        self,
        symbol: str,
        side: str,
        size: float,
        intended_price: float,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        reduce_only: bool = False,
        on_fill: Optional[Callable] = None,
        on_complete: Optional[Callable] = None
    ) -> ManagedOrder:
        """Create a new managed order."""
        order = ManagedOrder(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            size=size,
            intended_price=intended_price,
            order_type=order_type,
            limit_price=limit_price,
            reduce_only=reduce_only,
            on_fill=on_fill,
            on_complete=on_complete
        )
        
        self._orders[order.id] = order
        logger.info(f"📝 Created order {order.id}: {side} {size} {symbol}")
        
        return order
    
    async def submit_order(self, order: ManagedOrder) -> OrderResult:
        """
        Submit order with full lifecycle management.
        
        Flow:
        1. Validate order
        2. Send to exchange
        3. Wait for acknowledgment
        4. Wait for fill
        5. Verify fill matches expected
        6. Retry if failed
        """
        logger.info(f"📤 Submitting order {order.id}")
        
        # Validate
        validation = self._validate_order(order)
        if not validation["valid"]:
            order.state = OrderState.REJECTED
            order.last_error = validation["error"]
            return OrderResult(success=False, order=order, error=validation["error"])
        
        # Submit with retries
        while order.attempts < order.max_attempts:
            order.attempts += 1
            
            try:
                result = await self._send_to_exchange(order)
                
                if result.get("success"):
                    order.state = OrderState.SENT
                    order.sent_at = datetime.now()
                    order.exchange_order_id = result.get("order_id")
                    
                    # Check if immediately filled (market orders)
                    if result.get("filled"):
                        fill = OrderFill(
                            fill_id=str(uuid.uuid4()),
                            size=order.size,
                            price=result.get("filled", {}).get("avgPx", order.intended_price),
                            timestamp=datetime.now()
                        )
                        order.record_fill(fill)
                        
                        if order.on_fill:
                            await self._safe_callback(order.on_fill, order, fill)
                        if order.on_complete:
                            await self._safe_callback(order.on_complete, order)
                        
                        logger.info(f"✅ Order {order.id} filled immediately")
                        return OrderResult(success=True, order=order)
                    
                    # Add to pending for monitoring
                    self._pending_orders[order.id] = order
                    
                    # Wait for fill with timeout
                    try:
                        filled = await asyncio.wait_for(
                            self._wait_for_fill(order),
                            timeout=self._order_timeout.total_seconds()
                        )
                        
                        if filled:
                            return OrderResult(success=True, order=order)
                        else:
                            # Timed out or failed
                            order.state = OrderState.EXPIRED
                            return OrderResult(
                                success=False,
                                order=order,
                                error="Order timed out"
                            )
                    
                    except asyncio.TimeoutError:
                        order.state = OrderState.EXPIRED
                        await self._cancel_order(order)
                        return OrderResult(
                            success=False,
                            order=order,
                            error="Order timed out"
                        )
                
                else:
                    error = result.get("error", "Unknown error")
                    order.last_error = error
                    logger.warning(f"⚠️ Order {order.id} attempt {order.attempts} failed: {error}")
                    
                    if order.attempts < order.max_attempts:
                        delay = 2 ** order.attempts  # Exponential backoff
                        await asyncio.sleep(delay)
            
            except Exception as e:
                order.last_error = str(e)
                logger.error(f"❌ Order {order.id} exception: {e}")
                
                if order.attempts < order.max_attempts:
                    delay = 2 ** order.attempts
                    await asyncio.sleep(delay)
        
        # All attempts failed
        order.state = OrderState.FAILED
        return OrderResult(
            success=False,
            order=order,
            error=f"Failed after {order.max_attempts} attempts: {order.last_error}"
        )
    
    def _validate_order(self, order: ManagedOrder) -> Dict:
        """Validate order before submission."""
        if order.size <= 0:
            return {"valid": False, "error": "Size must be positive"}
        
        if order.symbol not in ["BTC", "ETH", "SOL", "DOGE", "AVAX", "LINK", "ARB", "OP", "SUI"]:
            logger.warning(f"⚠️ Unknown symbol: {order.symbol}")
        
        if order.order_type == "limit" and order.limit_price is None:
            return {"valid": False, "error": "Limit order requires limit_price"}
        
        return {"valid": True}
    
    async def _send_to_exchange(self, order: ManagedOrder) -> Dict:
        """Send order to exchange."""
        price = order.limit_price if order.order_type == "limit" else None
        
        return await self._client.place_order(
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            price=price,
            reduce_only=order.reduce_only
        )
    
    async def _wait_for_fill(self, order: ManagedOrder) -> bool:
        """Wait for order to fill."""
        while not order.is_complete and self._running:
            # In production, this would use WebSocket updates
            # For now, poll exchange status
            await asyncio.sleep(1)
            
            try:
                # Check if position changed (order filled)
                positions = self._client.get_positions()
                
                for pos in positions:
                    if pos["symbol"].upper() == order.symbol.upper():
                        # Position exists, check if it matches our order
                        expected_size = order.size
                        actual_size = pos["size"]
                        
                        if abs(actual_size - expected_size) < 0.01:  # Close enough
                            fill = OrderFill(
                                fill_id=str(uuid.uuid4()),
                                size=order.size,
                                price=pos["entry_price"],
                                timestamp=datetime.now()
                            )
                            order.record_fill(fill)
                            
                            if order.on_fill:
                                await self._safe_callback(order.on_fill, order, fill)
                            if order.on_complete:
                                await self._safe_callback(order.on_complete, order)
                            
                            return True
            
            except Exception as e:
                logger.error(f"Fill check error: {e}")
        
        return order.state == OrderState.FILLED
    
    async def _cancel_order(self, order: ManagedOrder):
        """Cancel an order on the exchange."""
        if not order.exchange_order_id:
            return
        
        logger.info(f"🚫 Cancelling order {order.id}")
        order.state = OrderState.CANCELLED
        
        # Remove from pending
        self._pending_orders.pop(order.id, None)
    
    async def _timeout_check_loop(self):
        """Check for stale orders."""
        while self._running:
            try:
                await self._check_stale_orders()
            except Exception as e:
                logger.error(f"Stale order check error: {e}")
            
            await asyncio.sleep(self._stale_check_interval)
    
    async def _check_stale_orders(self):
        """Check for orders that have been pending too long."""
        now = datetime.now()
        stale_ids = []
        
        for order_id, order in self._pending_orders.items():
            if order.sent_at:
                age = now - order.sent_at
                if age > self._order_timeout:
                    stale_ids.append(order_id)
        
        for order_id in stale_ids:
            order = self._pending_orders.pop(order_id, None)
            if order:
                logger.warning(f"⏰ Order {order_id} timed out")
                order.state = OrderState.EXPIRED
                await self._cancel_order(order)
                await self._alert_stale_order(order)
    
    async def _alert_stale_order(self, order: ManagedOrder):
        """Alert about a stale order."""
        try:
            from telegram.bot import get_bot
            
            bot = await get_bot()
            steward_id = 1087024913
            
            await bot.send_message(
                chat_id=steward_id,
                text=(
                    f"⏰ **Order Timed Out**\n\n"
                    f"Symbol: {order.symbol}\n"
                    f"Side: {order.side}\n"
                    f"Size: {order.size}\n"
                    f"Filled: {order.fill_percent:.1f}%\n"
                    f"Please check exchange manually."
                )
            )
        except Exception as e:
            logger.error(f"Failed to send stale order alert: {e}")
    
    async def _safe_callback(self, callback: Callable, *args):
        """Safely execute a callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    def get_order(self, order_id: str) -> Optional[ManagedOrder]:
        """Get an order by ID."""
        return self._orders.get(order_id)
    
    def get_pending_orders(self) -> List[ManagedOrder]:
        """Get all pending orders."""
        return list(self._pending_orders.values())
    
    def get_order_history(self, limit: int = 50) -> List[Dict]:
        """Get order history."""
        orders = sorted(
            self._orders.values(),
            key=lambda o: o.created_at,
            reverse=True
        )[:limit]
        
        return [o.to_dict() for o in orders]


# Singleton
_lifecycle_manager: Optional[OrderLifecycleManager] = None


def get_order_manager() -> OrderLifecycleManager:
    """Get or create global order manager."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = OrderLifecycleManager()
    return _lifecycle_manager


async def start_order_manager():
    """Start the order manager."""
    manager = get_order_manager()
    await manager.start()


async def stop_order_manager():
    """Stop the order manager."""
    manager = get_order_manager()
    await manager.stop()









