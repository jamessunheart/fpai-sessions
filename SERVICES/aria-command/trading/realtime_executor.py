#!/usr/bin/env python3
"""
⚡ REAL-TIME TRADE EXECUTOR
=============================

Executes trades with real-time price awareness.

Instead of:
  1. Get signal
  2. Wait 30s
  3. Execute at unknown price

Now:
  1. Get signal
  2. Wait for exact price via WebSocket
  3. Execute when price matches criteria
  4. Verify fill in real-time
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Callable
from enum import Enum

logger = logging.getLogger("aria.trading.realtime")


class ExecutionStatus(Enum):
    """Execution status."""
    PENDING = "pending"
    WAITING_PRICE = "waiting_price"
    EXECUTING = "executing"
    FILLED = "filled"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class PendingExecution:
    """A pending execution waiting for price."""
    id: str
    symbol: str
    side: str
    size: float
    max_price: float  # Max price to pay (for buys) / min to receive (for sells)
    timeout_seconds: int = 30
    
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    
    # Result
    fill_price: Optional[float] = None
    slippage_bps: Optional[float] = None
    
    # Internal
    _future: Optional[asyncio.Future] = None
    
    def should_execute(self, current_price: float) -> bool:
        """Check if current price is acceptable."""
        if self.side.lower() == "buy":
            return current_price <= self.max_price
        else:
            return current_price >= self.max_price
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "max_price": self.max_price,
            "status": self.status.value,
            "fill_price": self.fill_price,
            "slippage_bps": self.slippage_bps,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None
        }


@dataclass
class ExecutionResult:
    """Result of an execution."""
    success: bool
    execution: PendingExecution
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "execution": self.execution.to_dict(),
            "error": self.error
        }


class RealTimeExecutor:
    """
    Executes trades with real-time price awareness.
    
    Features:
    - Wait for exact price via WebSocket
    - Execute only when price matches criteria
    - Verify fill in real-time
    - Track slippage
    """
    
    def __init__(self):
        from .websocket_feed import get_websocket_feed
        from .resilient_client import get_resilient_client
        from .order_lifecycle import get_order_manager
        from .slippage_tracker import get_slippage_tracker
        
        self._ws = get_websocket_feed()
        self._client = get_resilient_client()
        self._order_manager = get_order_manager()
        self._slippage_tracker = get_slippage_tracker()
        
        self._pending: Dict[str, PendingExecution] = {}
        self._running = False
        
        # Subscribe to price updates
        self._ws.subscribe_prices(self._on_price_update)
    
    async def start(self):
        """Start the real-time executor."""
        if self._running:
            return
        
        self._running = True
        
        # Ensure WebSocket is connected
        await self._ws.connect()
        
        logger.info("⚡ Real-time executor started")
    
    async def stop(self):
        """Stop the real-time executor."""
        self._running = False
        
        # Cancel all pending executions
        for execution in list(self._pending.values()):
            execution.status = ExecutionStatus.CANCELLED
            if execution._future and not execution._future.done():
                execution._future.cancel()
        
        self._pending.clear()
        logger.info("⚡ Real-time executor stopped")
    
    async def execute_at_price(
        self,
        symbol: str,
        side: str,
        size: float,
        max_price: float,
        timeout_seconds: int = 30,
        on_fill: Optional[Callable] = None
    ) -> ExecutionResult:
        """
        Execute order when price is favorable.
        
        Waits for WebSocket price update, executes only if:
        - LONG/BUY: current_price <= max_price
        - SHORT/SELL: current_price >= max_price
        
        Args:
            symbol: Trading symbol (e.g., "SOL")
            side: "buy" or "sell"
            size: Position size
            max_price: Maximum acceptable price
            timeout_seconds: How long to wait for price
            on_fill: Callback when filled
            
        Returns:
            ExecutionResult with fill details
        """
        execution = PendingExecution(
            id=str(uuid.uuid4()),
            symbol=symbol.upper(),
            side=side.lower(),
            size=size,
            max_price=max_price,
            timeout_seconds=timeout_seconds
        )
        
        execution._future = asyncio.Future()
        execution.status = ExecutionStatus.WAITING_PRICE
        
        self._pending[execution.id] = execution
        
        logger.info(
            f"⏳ Waiting for {symbol} price <= ${max_price:,.2f} "
            f"(timeout: {timeout_seconds}s)"
        )
        
        try:
            # Check current price immediately
            current_price = self._ws.get_price(symbol)
            if current_price and execution.should_execute(current_price):
                # Price already good, execute immediately
                return await self._execute_now(execution, current_price)
            
            # Wait for favorable price
            await asyncio.wait_for(
                execution._future,
                timeout=timeout_seconds
            )
            
            if execution.status == ExecutionStatus.FILLED:
                if on_fill:
                    try:
                        await on_fill(execution)
                    except Exception as e:
                        logger.error(f"Fill callback error: {e}")
                
                return ExecutionResult(success=True, execution=execution)
            else:
                return ExecutionResult(
                    success=False,
                    execution=execution,
                    error="Execution failed"
                )
        
        except asyncio.TimeoutError:
            execution.status = ExecutionStatus.TIMEOUT
            self._pending.pop(execution.id, None)
            
            current = self._ws.get_price(symbol) or 0
            logger.warning(
                f"⏱️ Execution timeout: {symbol} price ${current:,.2f} "
                f"(wanted <= ${max_price:,.2f})"
            )
            
            return ExecutionResult(
                success=False,
                execution=execution,
                error=f"Timeout waiting for price <= ${max_price:,.2f}"
            )
        
        except asyncio.CancelledError:
            execution.status = ExecutionStatus.CANCELLED
            self._pending.pop(execution.id, None)
            
            return ExecutionResult(
                success=False,
                execution=execution,
                error="Cancelled"
            )
        
        finally:
            self._pending.pop(execution.id, None)
    
    async def execute_market(
        self,
        symbol: str,
        side: str,
        size: float,
        intended_price: Optional[float] = None
    ) -> ExecutionResult:
        """
        Execute market order immediately.
        
        Still tracks slippage if intended_price provided.
        """
        execution = PendingExecution(
            id=str(uuid.uuid4()),
            symbol=symbol.upper(),
            side=side.lower(),
            size=size,
            max_price=intended_price or 0
        )
        
        execution.status = ExecutionStatus.EXECUTING
        
        # Get current price for slippage tracking
        if intended_price is None:
            intended_price = self._ws.get_price(symbol) or 0
        
        return await self._execute_now(execution, intended_price)
    
    def _on_price_update(self, update):
        """Handle real-time price update."""
        symbol = update.symbol.upper()
        price = update.mid_price
        
        # Check pending executions
        to_execute = []
        
        for exec_id, execution in list(self._pending.items()):
            if execution.symbol == symbol and execution.should_execute(price):
                to_execute.append((execution, price))
        
        # Execute in background
        for execution, price in to_execute:
            asyncio.create_task(self._execute_now(execution, price))
    
    async def _execute_now(
        self,
        execution: PendingExecution,
        trigger_price: float
    ) -> ExecutionResult:
        """Execute the order immediately."""
        execution.status = ExecutionStatus.EXECUTING
        
        try:
            # Place order
            result = await self._client.place_order(
                symbol=execution.symbol,
                side=execution.side,
                size=execution.size
            )
            
            if result.get("success"):
                execution.status = ExecutionStatus.FILLED
                execution.executed_at = datetime.now()
                
                # Get fill price
                fill_price = result.get("filled", {}).get("avgPx")
                if fill_price:
                    execution.fill_price = float(fill_price)
                else:
                    execution.fill_price = trigger_price
                
                # Calculate slippage
                if execution.max_price > 0:
                    execution.slippage_bps = (
                        (execution.fill_price - execution.max_price) /
                        execution.max_price * 10000
                    )
                
                # Record slippage
                self._slippage_tracker.record_execution(
                    trade_id=execution.id,
                    symbol=execution.symbol,
                    side=execution.side,
                    intended_price=execution.max_price or trigger_price,
                    fill_price=execution.fill_price,
                    size=execution.size
                )
                
                logger.info(
                    f"✅ Executed {execution.symbol} {execution.side} {execution.size} "
                    f"@ ${execution.fill_price:,.2f} "
                    f"(slippage: {execution.slippage_bps:.1f} bps)"
                )
                
                # Resolve future
                if execution._future and not execution._future.done():
                    execution._future.set_result(True)
                
                return ExecutionResult(success=True, execution=execution)
            
            else:
                execution.status = ExecutionStatus.FAILED
                error = result.get("error", "Unknown error")
                
                logger.error(f"❌ Execution failed: {error}")
                
                if execution._future and not execution._future.done():
                    execution._future.set_result(False)
                
                return ExecutionResult(
                    success=False,
                    execution=execution,
                    error=error
                )
        
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            
            logger.error(f"❌ Execution exception: {e}")
            
            if execution._future and not execution._future.done():
                execution._future.set_exception(e)
            
            return ExecutionResult(
                success=False,
                execution=execution,
                error=str(e)
            )
        
        finally:
            self._pending.pop(execution.id, None)
    
    def get_pending_executions(self) -> List[Dict]:
        """Get all pending executions."""
        return [e.to_dict() for e in self._pending.values()]
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a pending execution."""
        execution = self._pending.get(execution_id)
        
        if execution:
            execution.status = ExecutionStatus.CANCELLED
            
            if execution._future and not execution._future.done():
                execution._future.cancel()
            
            self._pending.pop(execution_id, None)
            return True
        
        return False


# Singleton
_executor: Optional[RealTimeExecutor] = None


def get_realtime_executor() -> RealTimeExecutor:
    """Get or create global real-time executor."""
    global _executor
    if _executor is None:
        _executor = RealTimeExecutor()
    return _executor


async def start_realtime_executor():
    """Start the real-time executor."""
    executor = get_realtime_executor()
    await executor.start()


async def stop_realtime_executor():
    """Stop the real-time executor."""
    executor = get_realtime_executor()
    await executor.stop()









