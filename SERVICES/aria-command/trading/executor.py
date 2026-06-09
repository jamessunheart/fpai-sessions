#!/usr/bin/env python3
"""
ARIA TRADING EXECUTOR
=====================

Execute trades via WhaleTrack Live API.
All trades require explicit approval.

Safety Features:
- Position size limits
- Leverage limits  
- Approval required for all trades
- Emergency stop capability
"""

import os
import asyncio
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import httpx

logger = logging.getLogger("aria.trading.executor")

# ============================================================================
# CONFIGURATION
# ============================================================================

WHALETRACK_LIVE_URL = os.getenv("WHALETRACK_LIVE_URL", "http://198.54.123.234:8601")

# Safety limits
MAX_POSITION_SIZE_USD = 500  # Maximum single trade size
MAX_LEVERAGE = 5  # Maximum leverage allowed
MAX_TOTAL_EXPOSURE = 1000  # Maximum total exposure


class TradeStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeSide(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class TradeRequest:
    """A request to execute a trade."""
    id: str
    symbol: str
    side: TradeSide
    size_usd: float
    leverage: int = 1
    
    # Metadata
    reason: str = ""
    requested_by: str = "aria"
    requested_at: datetime = field(default_factory=datetime.now)
    
    # Status
    status: TradeStatus = TradeStatus.PENDING
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    
    # Result
    order_id: Optional[str] = None
    entry_price: Optional[float] = None
    error: Optional[str] = None


@dataclass
class TradeResult:
    """Result of a trade execution."""
    success: bool
    trade_id: str
    message: str
    
    # Trade details
    symbol: Optional[str] = None
    side: Optional[str] = None
    size_usd: Optional[float] = None
    entry_price: Optional[float] = None
    order_id: Optional[str] = None
    
    # Error info
    error: Optional[str] = None


class TradingExecutor:
    """
    Execute trades via WhaleTrack Live.
    
    Features:
    - Place market orders (long/short)
    - Close positions
    - Emergency stop all
    - Position monitoring
    - Safety limits enforcement
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self.pending_trades: Dict[str, TradeRequest] = {}
        self._trade_counter = 0
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    def _generate_trade_id(self) -> str:
        """Generate unique trade ID."""
        self._trade_counter += 1
        return f"ARIA-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._trade_counter:04d}"
    
    # ========================================================================
    # SAFETY CHECKS
    # ========================================================================
    
    async def check_trade_safety(self, symbol: str, size_usd: float, leverage: int) -> Dict[str, Any]:
        """
        Check if trade is within safety limits.
        
        Returns:
            {
                "safe": bool,
                "issues": List[str],
                "warnings": List[str]
            }
        """
        issues = []
        warnings = []
        
        # Check position size
        if size_usd > MAX_POSITION_SIZE_USD:
            issues.append(f"Position size ${size_usd} exceeds max ${MAX_POSITION_SIZE_USD}")
        elif size_usd > MAX_POSITION_SIZE_USD * 0.8:
            warnings.append(f"Position size is {size_usd/MAX_POSITION_SIZE_USD*100:.0f}% of max")
        
        # Check leverage
        if leverage > MAX_LEVERAGE:
            issues.append(f"Leverage {leverage}x exceeds max {MAX_LEVERAGE}x")
        elif leverage > 3:
            warnings.append(f"High leverage: {leverage}x")
        
        # Check total exposure
        current_exposure = await self._get_total_exposure()
        if current_exposure + size_usd > MAX_TOTAL_EXPOSURE:
            issues.append(f"Total exposure would be ${current_exposure + size_usd:.0f}, exceeds max ${MAX_TOTAL_EXPOSURE}")
        
        # Check if WhaleTrack is healthy
        health = await self._check_whaletrack_health()
        if not health.get("healthy"):
            issues.append("WhaleTrack Live is not healthy")
        
        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "current_exposure": current_exposure
        }
    
    async def _get_total_exposure(self) -> float:
        """Get current total exposure across all positions."""
        try:
            response = await self.http.get(f"{WHALETRACK_LIVE_URL}/api/positions")
            if response.status_code == 200:
                data = response.json()
                positions = data.get("positions", [])
                return sum(
                    abs(float(p.get("size", 0)) * float(p.get("entry_price", 0)))
                    for p in positions
                )
        except Exception as e:
            logger.error(f"Failed to get exposure: {e}")
        return 0.0
    
    async def _check_whaletrack_health(self) -> Dict:
        """Check WhaleTrack Live health."""
        try:
            response = await self.http.get(f"{WHALETRACK_LIVE_URL}/health")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        return {"healthy": False}
    
    # ========================================================================
    # TRADE EXECUTION
    # ========================================================================
    
    async def request_trade(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        leverage: int = 1,
        reason: str = ""
    ) -> TradeRequest:
        """
        Request a trade (requires approval).
        
        Args:
            symbol: Trading pair (e.g., "BTC", "ETH")
            side: "long" or "short"
            size_usd: Position size in USD
            leverage: Leverage multiplier (1-5)
            reason: Reason for the trade
        
        Returns:
            TradeRequest object with pending status
        """
        trade_id = self._generate_trade_id()
        
        trade = TradeRequest(
            id=trade_id,
            symbol=symbol.upper(),
            side=TradeSide(side.lower()),
            size_usd=size_usd,
            leverage=min(leverage, MAX_LEVERAGE),
            reason=reason
        )
        
        self.pending_trades[trade_id] = trade
        logger.info(f"Trade requested: {trade_id} - {side} {symbol} ${size_usd}")
        
        return trade
    
    async def approve_and_execute(self, trade_id: str) -> TradeResult:
        """
        Approve and execute a pending trade.
        
        Args:
            trade_id: ID of the pending trade
        
        Returns:
            TradeResult with execution details
        """
        if trade_id not in self.pending_trades:
            return TradeResult(
                success=False,
                trade_id=trade_id,
                message="Trade not found",
                error="No pending trade with this ID"
            )
        
        trade = self.pending_trades[trade_id]
        
        # Safety check
        safety = await self.check_trade_safety(
            trade.symbol, trade.size_usd, trade.leverage
        )
        
        if not safety["safe"]:
            trade.status = TradeStatus.FAILED
            trade.error = "; ".join(safety["issues"])
            return TradeResult(
                success=False,
                trade_id=trade_id,
                message="Trade failed safety checks",
                error=trade.error
            )
        
        # Execute via WhaleTrack Live
        trade.approved_at = datetime.now()
        trade.status = TradeStatus.APPROVED
        
        try:
            response = await self.http.post(
                f"{WHALETRACK_LIVE_URL}/api/trade",
                json={
                    "symbol": trade.symbol,
                    "side": trade.side.value,
                    "size_usd": trade.size_usd,
                    "leverage": trade.leverage
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                trade.status = TradeStatus.EXECUTED
                trade.executed_at = datetime.now()
                trade.order_id = data.get("trade", {}).get("order_id")
                trade.entry_price = data.get("trade", {}).get("entry_price")
                
                # Remove from pending
                del self.pending_trades[trade_id]
                
                return TradeResult(
                    success=True,
                    trade_id=trade_id,
                    message=f"Trade executed: {trade.side.value} {trade.symbol}",
                    symbol=trade.symbol,
                    side=trade.side.value,
                    size_usd=trade.size_usd,
                    entry_price=trade.entry_price,
                    order_id=trade.order_id
                )
            else:
                error_msg = response.json().get("detail", response.text)
                trade.status = TradeStatus.FAILED
                trade.error = error_msg
                
                return TradeResult(
                    success=False,
                    trade_id=trade_id,
                    message="Trade execution failed",
                    error=error_msg
                )
                
        except Exception as e:
            trade.status = TradeStatus.FAILED
            trade.error = str(e)
            logger.error(f"Trade execution failed: {e}")
            
            return TradeResult(
                success=False,
                trade_id=trade_id,
                message="Trade execution failed",
                error=str(e)
            )
    
    async def execute_trade_direct(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        leverage: int = 1
    ) -> TradeResult:
        """
        Execute a trade directly (for pre-approved trades).
        
        Use with caution - bypasses approval flow.
        """
        trade = await self.request_trade(symbol, side, size_usd, leverage)
        return await self.approve_and_execute(trade.id)
    
    async def cancel_trade(self, trade_id: str) -> bool:
        """Cancel a pending trade."""
        if trade_id in self.pending_trades:
            self.pending_trades[trade_id].status = TradeStatus.CANCELLED
            del self.pending_trades[trade_id]
            return True
        return False
    
    # ========================================================================
    # POSITION MANAGEMENT
    # ========================================================================
    
    async def get_positions(self) -> List[Dict]:
        """Get all open positions."""
        try:
            response = await self.http.get(f"{WHALETRACK_LIVE_URL}/api/positions")
            if response.status_code == 200:
                data = response.json()
                return data.get("positions", [])
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
        return []
    
    async def close_position(self, symbol: str) -> TradeResult:
        """Close a specific position."""
        try:
            # Get current position to determine side
            positions = await self.get_positions()
            position = next((p for p in positions if p.get("symbol", "").upper() == symbol.upper()), None)
            
            if not position:
                return TradeResult(
                    success=False,
                    trade_id="",
                    message=f"No open position for {symbol}",
                    error="Position not found"
                )
            
            # Close by opening opposite position
            current_side = position.get("side", "long")
            close_side = "short" if current_side == "long" else "long"
            size = abs(float(position.get("size", 0)))
            entry_price = float(position.get("entry_price", 0))
            
            response = await self.http.post(
                f"{WHALETRACK_LIVE_URL}/api/trade",
                json={
                    "symbol": symbol.upper(),
                    "side": close_side,
                    "size_usd": size * entry_price,  # Close full position
                    "leverage": 1,
                    "reduce_only": True
                }
            )
            
            if response.status_code == 200:
                return TradeResult(
                    success=True,
                    trade_id=self._generate_trade_id(),
                    message=f"Closed {symbol} position",
                    symbol=symbol
                )
            else:
                return TradeResult(
                    success=False,
                    trade_id="",
                    message="Failed to close position",
                    error=response.json().get("detail", response.text)
                )
                
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            return TradeResult(
                success=False,
                trade_id="",
                message="Failed to close position",
                error=str(e)
            )
    
    async def emergency_stop(self) -> Dict[str, Any]:
        """
        EMERGENCY: Close all positions immediately.
        
        Returns:
            {
                "success": bool,
                "closed": int,
                "errors": List[str]
            }
        """
        logger.warning("EMERGENCY STOP TRIGGERED")
        
        positions = await self.get_positions()
        closed = 0
        errors = []
        
        for pos in positions:
            symbol = pos.get("symbol", "")
            if symbol:
                result = await self.close_position(symbol)
                if result.success:
                    closed += 1
                else:
                    errors.append(f"{symbol}: {result.error}")
        
        return {
            "success": len(errors) == 0,
            "closed": closed,
            "errors": errors
        }
    
    # ========================================================================
    # ACCOUNT INFO
    # ========================================================================
    
    async def get_balance(self) -> float:
        """Get account balance."""
        try:
            response = await self.http.get(f"{WHALETRACK_LIVE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("adapter", {}).get("balance", 0)
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
        return 0.0
    
    async def get_account_summary(self) -> Dict[str, Any]:
        """Get full account summary."""
        balance = await self.get_balance()
        positions = await self.get_positions()
        exposure = await self._get_total_exposure()
        
        total_pnl = sum(float(p.get("pnl", 0)) for p in positions)
        
        return {
            "balance": balance,
            "positions": len(positions),
            "exposure": exposure,
            "total_pnl": total_pnl,
            "available": balance - exposure
        }
    
    def get_pending_trades(self) -> List[TradeRequest]:
        """Get all pending trades."""
        return list(self.pending_trades.values())


# ============================================================================
# SINGLETON
# ============================================================================

_executor: Optional[TradingExecutor] = None


def get_executor() -> TradingExecutor:
    """Get or create global trading executor."""
    global _executor
    if _executor is None:
        _executor = TradingExecutor()
    return _executor


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def open_long(symbol: str, size_usd: float, leverage: int = 1) -> TradeRequest:
    """Request a long position."""
    return await get_executor().request_trade(symbol, "long", size_usd, leverage)


async def open_short(symbol: str, size_usd: float, leverage: int = 1) -> TradeRequest:
    """Request a short position."""
    return await get_executor().request_trade(symbol, "short", size_usd, leverage)


async def close(symbol: str) -> TradeResult:
    """Close a position."""
    return await get_executor().close_position(symbol)


async def emergency_stop() -> Dict:
    """Emergency stop all trading."""
    return await get_executor().emergency_stop()


async def get_positions() -> List[Dict]:
    """Get all positions."""
    return await get_executor().get_positions()


async def get_balance() -> float:
    """Get account balance."""
    return await get_executor().get_balance()


