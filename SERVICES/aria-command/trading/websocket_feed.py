#!/usr/bin/env python3
"""
🔌 WEBSOCKET PRICE FEED
=========================

Real-time price and order updates via WebSocket.

Features:
- Real-time mid prices for all assets
- User order fills and events
- Order status updates
- Auto-reconnect with exponential backoff
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger("aria.trading.websocket")

# Try to import websockets
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets library not installed - WebSocket features disabled")


@dataclass
class PriceUpdate:
    """Real-time price update."""
    symbol: str
    mid_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OrderUpdate:
    """Order status update."""
    order_id: str
    status: str  # "open", "filled", "cancelled", "rejected"
    filled_size: float = 0.0
    avg_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FillEvent:
    """Trade fill event."""
    order_id: str
    symbol: str
    side: str
    size: float
    price: float
    fee: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class HyperliquidWebSocket:
    """
    Real-time price and order updates via WebSocket.
    
    Connects to Hyperliquid WebSocket for:
    - allMids: Real-time mid prices for all assets
    - userEvents: Order fills, liquidations, funding
    - orderUpdates: Order status changes
    """
    
    def __init__(self, user_address: Optional[str] = None):
        self._ws_url = "wss://api.hyperliquid.xyz/ws"
        self._user_address = user_address
        self._ws: Any = None  # WebSocket connection
        
        self._running = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        
        # Callbacks
        self._price_callbacks: List[Callable[[PriceUpdate], None]] = []
        self._order_callbacks: List[Callable[[OrderUpdate], None]] = []
        self._fill_callbacks: List[Callable[[FillEvent], None]] = []
        
        # Latest prices
        self._prices: Dict[str, float] = {}
        
        # Connection task
        self._connection_task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._ws is not None and self._running
    
    @property
    def prices(self) -> Dict[str, float]:
        """Get current price snapshot."""
        return self._prices.copy()
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        return self._prices.get(symbol.upper())
    
    async def connect(self):
        """
        Connect to Hyperliquid WebSocket.
        
        Automatically subscribes to:
        - allMids: Real-time mid prices
        - userEvents: If user address provided
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library not available")
            return False
        
        if self._running:
            return True
        
        self._running = True
        self._connection_task = asyncio.create_task(self._reconnect_loop())
        
        logger.info("🔌 Starting WebSocket connection...")
        return True
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        self._running = False
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._connection_task:
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🔌 WebSocket disconnected")
    
    async def _reconnect_loop(self):
        """Auto-reconnect with exponential backoff."""
        while self._running:
            try:
                await self._connect()
                self._reconnect_delay = 1.0  # Reset on success
                await self._message_loop()
            
            except websockets.ConnectionClosed as e:
                logger.warning(f"WebSocket closed: {e}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            
            if self._running:
                logger.info(f"⏳ Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._max_reconnect_delay
                )
    
    async def _connect(self):
        """Establish WebSocket connection."""
        self._ws = await websockets.connect(self._ws_url)
        logger.info("✅ WebSocket connected")
        
        # Subscribe to allMids
        await self._subscribe_all_mids()
        
        # Subscribe to user events if address provided
        if self._user_address:
            await self._subscribe_user_events()
    
    async def _message_loop(self):
        """Process incoming WebSocket messages."""
        async for message in self._ws:
            try:
                data = json.loads(message)
                await self._handle_message(data)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON: {message[:100]}")
            except Exception as e:
                logger.error(f"Message handling error: {e}")
    
    async def _handle_message(self, data: Dict):
        """Handle incoming WebSocket message."""
        channel = data.get("channel")
        
        if channel == "allMids":
            await self._handle_price_update(data.get("data", {}))
        
        elif channel == "userEvents":
            await self._handle_user_event(data.get("data", {}))
        
        elif channel == "orderUpdates":
            await self._handle_order_update(data.get("data", {}))
    
    async def _handle_price_update(self, data: Dict):
        """Handle allMids price update."""
        mids = data.get("mids", {})
        
        for symbol, price_str in mids.items():
            try:
                price = float(price_str)
                self._prices[symbol] = price
                
                update = PriceUpdate(symbol=symbol, mid_price=price)
                
                for callback in self._price_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(update)
                        else:
                            callback(update)
                    except Exception as e:
                        logger.error(f"Price callback error: {e}")
            
            except ValueError:
                pass
    
    async def _handle_user_event(self, data: Dict):
        """Handle user event (fills, etc)."""
        fills = data.get("fills", [])
        
        for fill in fills:
            try:
                event = FillEvent(
                    order_id=fill.get("oid", ""),
                    symbol=fill.get("coin", ""),
                    side=fill.get("side", ""),
                    size=float(fill.get("sz", 0)),
                    price=float(fill.get("px", 0)),
                    fee=float(fill.get("fee", 0)),
                    timestamp=datetime.now()
                )
                
                for callback in self._fill_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Fill callback error: {e}")
            
            except Exception as e:
                logger.error(f"Fill parsing error: {e}")
    
    async def _handle_order_update(self, data: Dict):
        """Handle order status update."""
        try:
            order = data.get("order", {})
            
            update = OrderUpdate(
                order_id=str(order.get("oid", "")),
                status=order.get("status", ""),
                filled_size=float(order.get("filledSz", 0)),
                avg_price=float(order.get("avgPx", 0)) if order.get("avgPx") else 0,
                timestamp=datetime.now()
            )
            
            for callback in self._order_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(update)
                    else:
                        callback(update)
                except Exception as e:
                    logger.error(f"Order callback error: {e}")
        
        except Exception as e:
            logger.error(f"Order update parsing error: {e}")
    
    async def _subscribe_all_mids(self):
        """Subscribe to real-time mid prices."""
        message = {
            "method": "subscribe",
            "subscription": {"type": "allMids"}
        }
        await self._ws.send(json.dumps(message))
        logger.info("📊 Subscribed to allMids")
    
    async def _subscribe_user_events(self):
        """Subscribe to user's order fills and events."""
        if not self._user_address:
            return
        
        message = {
            "method": "subscribe",
            "subscription": {
                "type": "userEvents",
                "user": self._user_address
            }
        }
        await self._ws.send(json.dumps(message))
        logger.info(f"📋 Subscribed to userEvents for {self._user_address[:10]}...")
    
    def subscribe_prices(self, callback: Callable[[PriceUpdate], None]):
        """Subscribe to real-time price updates."""
        self._price_callbacks.append(callback)
    
    def subscribe_orders(self, callback: Callable[[OrderUpdate], None]):
        """Subscribe to order status updates."""
        self._order_callbacks.append(callback)
    
    def subscribe_fills(self, callback: Callable[[FillEvent], None]):
        """Subscribe to fill events."""
        self._fill_callbacks.append(callback)
    
    def unsubscribe_prices(self, callback: Callable):
        """Unsubscribe from price updates."""
        if callback in self._price_callbacks:
            self._price_callbacks.remove(callback)
    
    def unsubscribe_orders(self, callback: Callable):
        """Unsubscribe from order updates."""
        if callback in self._order_callbacks:
            self._order_callbacks.remove(callback)
    
    def unsubscribe_fills(self, callback: Callable):
        """Unsubscribe from fill events."""
        if callback in self._fill_callbacks:
            self._fill_callbacks.remove(callback)


# Singleton
_ws_feed: Optional[HyperliquidWebSocket] = None


def get_websocket_feed(user_address: Optional[str] = None) -> HyperliquidWebSocket:
    """Get or create global WebSocket feed."""
    global _ws_feed
    if _ws_feed is None:
        # Try to get user address from credentials
        if user_address is None:
            try:
                from .hyperliquid_live import get_hyperliquid
                hl = get_hyperliquid()
                user_address = hl.main_account
            except:
                pass
        
        _ws_feed = HyperliquidWebSocket(user_address)
    return _ws_feed


async def start_websocket_feed():
    """Start the WebSocket feed."""
    feed = get_websocket_feed()
    await feed.connect()


async def stop_websocket_feed():
    """Stop the WebSocket feed."""
    feed = get_websocket_feed()
    await feed.disconnect()









