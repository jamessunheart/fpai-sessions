#!/usr/bin/env python3
"""
📊 SCALED ENTRY SYSTEM
=======================

Manages scaled entries into positions:
- Split orders into multiple entries (default: 40/35/25)
- Wait for confirmation between entries
- Stop adding if price reverses
- Better average entry price
- Reduces slippage on larger positions

Example:
  Total position: $400
  Entry 1: $160 (40%) at market
  Wait for confirmation...
  Entry 2: $140 (35%) at limit
  Wait for confirmation...
  Entry 3: $100 (25%) at limit
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("aria.trading.scaled_entry")


class ScaledEntryState(Enum):
    """State of scaled entry."""
    PENDING = "pending"           # Not started
    IN_PROGRESS = "in_progress"   # Scaling in
    COMPLETED = "completed"       # All entries filled
    PARTIAL = "partial"           # Stopped with partial fill
    FAILED = "failed"             # Failed to enter
    CANCELLED = "cancelled"       # Manually cancelled


@dataclass
class ScaleConfig:
    """Configuration for scaled entries."""
    num_entries: int = 3                  # Number of entries
    entry_spacing_pct: float = 0.5        # Price spacing between entries (%)
    confirmation_bars: int = 2            # Candles to wait between entries
    confirmation_seconds: int = 60        # Seconds between entries
    size_distribution: List[float] = field(
        default_factory=lambda: [0.4, 0.35, 0.25]  # 40/35/25 split
    )
    
    # Risk management
    abort_on_reversal_pct: float = 1.0    # Abort if price reverses by this %
    use_limit_orders: bool = True         # Use limits after first entry
    limit_offset_pct: float = 0.1         # Offset from current price for limits


@dataclass
class ScaledEntryResult:
    """Result of a scaled entry operation."""
    success: bool
    state: ScaledEntryState
    
    # Entry details
    total_size: float = 0.0
    filled_size: float = 0.0
    avg_entry_price: float = 0.0
    num_entries_completed: int = 0
    
    # Order IDs
    entry_order_ids: List[str] = field(default_factory=list)
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error info
    error: Optional[str] = None
    abort_reason: Optional[str] = None


@dataclass
class ScaledEntryPosition:
    """Tracks a position being scaled into."""
    symbol: str
    side: str  # "long" or "short"
    total_size: float
    config: ScaleConfig
    
    # State
    state: ScaledEntryState = ScaledEntryState.PENDING
    current_entry: int = 0
    
    # Fills
    fills: List[Dict] = field(default_factory=list)  # {size, price, time}
    
    # Tracking
    initial_price: float = 0.0
    best_price: float = 0.0    # Best price seen during scaling
    worst_price: float = 0.0   # Worst price seen
    
    # Timing
    started_at: Optional[datetime] = None
    last_entry_at: Optional[datetime] = None
    
    @property
    def filled_size(self) -> float:
        """Total size filled so far."""
        return sum(f["size"] for f in self.fills)
    
    @property
    def avg_entry_price(self) -> float:
        """Volume-weighted average entry price."""
        if not self.fills:
            return 0.0
        
        total_value = sum(f["size"] * f["price"] for f in self.fills)
        total_size = self.filled_size
        
        return total_value / total_size if total_size > 0 else 0.0
    
    @property
    def remaining_size(self) -> float:
        """Size remaining to fill."""
        return self.total_size - self.filled_size
    
    def get_next_entry_size(self) -> float:
        """Get size for next entry."""
        if self.current_entry >= len(self.config.size_distribution):
            return 0.0
        
        return self.total_size * self.config.size_distribution[self.current_entry]
    
    def should_abort(self, current_price: float) -> bool:
        """Check if scaling should abort due to reversal."""
        if not self.initial_price:
            return False
        
        reversal_pct = self.config.abort_on_reversal_pct
        
        if self.side == "long":
            # Abort if price drops too much from initial
            threshold = self.initial_price * (1 - reversal_pct / 100)
            return current_price < threshold
        else:
            # Abort if price rises too much from initial
            threshold = self.initial_price * (1 + reversal_pct / 100)
            return current_price > threshold


class ScaledEntryManager:
    """
    Manages scaled entries into positions.
    
    Features:
    - Splits large orders into smaller pieces
    - Uses market for first entry, limits for rest
    - Waits for confirmation between entries
    - Aborts if price reverses
    """
    
    def __init__(self):
        from .order_manager import get_order_manager
        self.order_manager = get_order_manager()
        self._active_entries: Dict[str, ScaledEntryPosition] = {}
    
    async def execute_scaled_entry(
        self,
        symbol: str,
        side: str,
        total_size: float,
        config: Optional[ScaleConfig] = None
    ) -> ScaledEntryResult:
        """
        Execute a scaled entry into a position.
        
        Instead of market buying full size:
        1. Entry 1: 40% at market (immediate)
        2. Wait for confirmation
        3. Entry 2: 35% at market or limit
        4. Wait for confirmation
        5. Entry 3: 25% at limit
        
        If price reverses, stop adding and keep partial.
        """
        if config is None:
            config = ScaleConfig()
        
        result = ScaledEntryResult(
            success=False,
            state=ScaledEntryState.PENDING,
            total_size=total_size,
            started_at=datetime.now()
        )
        
        # Create position tracker
        position = ScaledEntryPosition(
            symbol=symbol,
            side=side,
            total_size=total_size,
            config=config,
            started_at=datetime.now()
        )
        
        self._active_entries[symbol] = position
        
        try:
            # Get current price
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            if not hl.is_connected:
                result.error = "Exchange not connected"
                result.state = ScaledEntryState.FAILED
                return result
            
            # Get current price
            current_price = await self._get_current_price(hl, symbol)
            position.initial_price = current_price
            position.state = ScaledEntryState.IN_PROGRESS
            
            logger.info(
                f"📊 Starting scaled entry: {side} {symbol} "
                f"| Total: {total_size} | Entries: {config.num_entries}"
            )
            
            # Execute entries
            for entry_num in range(config.num_entries):
                position.current_entry = entry_num
                
                # Check for abort condition
                current_price = await self._get_current_price(hl, symbol)
                if position.should_abort(current_price):
                    position.state = ScaledEntryState.PARTIAL
                    result.abort_reason = f"Price reversed beyond {config.abort_on_reversal_pct}%"
                    logger.warning(f"⚠️ Aborting scale: {result.abort_reason}")
                    break
                
                # Calculate entry size
                entry_size = position.get_next_entry_size()
                if entry_size <= 0:
                    break
                
                # Execute entry
                use_limit = config.use_limit_orders and entry_num > 0
                
                entry_result = await self._execute_single_entry(
                    symbol=symbol,
                    side=side,
                    size=entry_size,
                    use_limit=use_limit,
                    current_price=current_price,
                    config=config
                )
                
                if entry_result.get("success"):
                    fill = {
                        "size": entry_result["filled_size"],
                        "price": entry_result["filled_price"],
                        "time": datetime.now()
                    }
                    position.fills.append(fill)
                    result.entry_order_ids.append(entry_result.get("order_id", ""))
                    position.last_entry_at = datetime.now()
                    
                    logger.info(
                        f"✅ Entry {entry_num + 1}/{config.num_entries}: "
                        f"{entry_size:.4f} @ ${entry_result['filled_price']:,.2f}"
                    )
                else:
                    logger.warning(f"Entry {entry_num + 1} failed: {entry_result.get('error')}")
                    # Continue with partial position
                
                # Wait between entries (except last)
                if entry_num < config.num_entries - 1:
                    await asyncio.sleep(config.confirmation_seconds)
            
            # Finalize result
            result.filled_size = position.filled_size
            result.avg_entry_price = position.avg_entry_price
            result.num_entries_completed = len(position.fills)
            result.completed_at = datetime.now()
            
            if position.filled_size > 0:
                result.success = True
                if position.filled_size >= total_size * 0.95:  # 95% filled = complete
                    result.state = ScaledEntryState.COMPLETED
                    position.state = ScaledEntryState.COMPLETED
                else:
                    result.state = ScaledEntryState.PARTIAL
                    position.state = ScaledEntryState.PARTIAL
            else:
                result.state = ScaledEntryState.FAILED
                position.state = ScaledEntryState.FAILED
            
            logger.info(
                f"📊 Scaled entry complete: {position.filled_size:.4f}/{total_size:.4f} "
                f"@ avg ${position.avg_entry_price:,.2f}"
            )
            
        except Exception as e:
            result.error = str(e)
            result.state = ScaledEntryState.FAILED
            logger.error(f"Scaled entry error: {e}")
        
        finally:
            # Clean up
            if symbol in self._active_entries:
                del self._active_entries[symbol]
        
        return result
    
    async def _get_current_price(self, hl, symbol: str) -> float:
        """Get current price for symbol."""
        try:
            prices = hl.get_prices()
            return prices.get(symbol, 0.0)
        except:
            return 0.0
    
    async def _execute_single_entry(
        self,
        symbol: str,
        side: str,
        size: float,
        use_limit: bool,
        current_price: float,
        config: ScaleConfig
    ) -> Dict:
        """Execute a single entry order."""
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            order_side = "buy" if side == "long" else "sell"
            
            if use_limit:
                # Calculate limit price with offset
                offset = current_price * config.limit_offset_pct / 100
                if side == "long":
                    limit_price = current_price + offset  # Slightly above for fills
                else:
                    limit_price = current_price - offset
                
                # Place limit order
                result = await hl.place_order(
                    symbol=symbol,
                    side=order_side,
                    size=size,
                    price=limit_price
                )
            else:
                # Market order
                result = await hl.place_order(
                    symbol=symbol,
                    side=order_side,
                    size=size
                )
            
            if result.get("success"):
                # Get fill info
                await asyncio.sleep(0.5)  # Wait for fill
                positions = hl.get_positions()
                pos = next((p for p in positions if p["symbol"] == symbol), None)
                
                return {
                    "success": True,
                    "order_id": result.get("order_id"),
                    "filled_size": size,
                    "filled_price": pos["entry_price"] if pos else current_price
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error")
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_active_entries(self) -> Dict[str, ScaledEntryPosition]:
        """Get all active scaling entries."""
        return self._active_entries.copy()
    
    async def cancel_entry(self, symbol: str) -> bool:
        """Cancel an in-progress scaled entry."""
        if symbol not in self._active_entries:
            return False
        
        position = self._active_entries[symbol]
        position.state = ScaledEntryState.CANCELLED
        
        # Cancel any pending limit orders
        await self.order_manager.cancel_all_orders(symbol)
        
        del self._active_entries[symbol]
        logger.info(f"🛑 Cancelled scaled entry for {symbol}")
        
        return True


# Singleton
_scaled_entry_manager: Optional[ScaledEntryManager] = None


def get_scaled_entry_manager() -> ScaledEntryManager:
    """Get or create global scaled entry manager."""
    global _scaled_entry_manager
    if _scaled_entry_manager is None:
        _scaled_entry_manager = ScaledEntryManager()
    return _scaled_entry_manager









