#!/usr/bin/env python3
"""
ARIA ASCENSION - TRADE EXECUTOR
===============================

Execute approved trading strategies:
- Strict risk limits (max position size, daily loss limit)
- Real-time P&L tracking
- Approval workflow for trades
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.revenue.trade")

# ============================================================================
# CONFIGURATION
# ============================================================================

WHALETRACK_LIVE_URL = os.getenv("WHALETRACK_LIVE_URL", "http://198.54.123.234:8601")

# Risk limits
MAX_POSITION_SIZE_PCT = float(os.getenv("MAX_POSITION_SIZE_PCT", "0.20"))  # 20% of equity
MAX_SINGLE_TRADE_PCT = float(os.getenv("MAX_SINGLE_TRADE_PCT", "0.10"))    # 10% per trade
DAILY_LOSS_LIMIT_PCT = float(os.getenv("DAILY_LOSS_LIMIT_PCT", "0.05"))    # 5% daily loss limit
MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", "3"))                         # Max 3x leverage

# Auto-execution threshold
AUTO_EXECUTE_CONFIDENCE = float(os.getenv("AUTO_EXECUTE_CONFIDENCE", "0.95"))


class TradeStatus(str, Enum):
    """Status of a trade."""
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeDirection(str, Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"
    CLOSE = "close"


@dataclass
class TradeRequest:
    """A trade request."""
    id: str
    symbol: str
    direction: TradeDirection
    size_pct: float  # Size as % of equity
    leverage: int
    
    # Risk parameters
    stop_loss_pct: float = None
    take_profit_pct: float = None
    
    # Status
    status: TradeStatus = TradeStatus.PENDING
    confidence: float = 0.0
    reason: str = ""
    
    # Results
    entry_price: float = None
    filled_size: float = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    approved_at: datetime = None
    executed_at: datetime = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "size_pct": self.size_pct,
            "leverage": self.leverage,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "status": self.status.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "entry_price": self.entry_price,
            "filled_size": self.filled_size,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class RiskCheck:
    """Result of a risk check."""
    passed: bool
    checks: Dict[str, bool]
    reasons: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "reasons": self.reasons
        }


# ============================================================================
# TRADE EXECUTOR
# ============================================================================

class TradeExecutor:
    """
    Executes trades with strict risk management.
    """
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.pending_trades: Dict[str, TradeRequest] = {}
        self._approval_callback: Optional[callable] = None
        
        # Daily tracking
        self._daily_pnl: float = 0
        self._daily_reset_date: datetime = datetime.now().date()
        
        logger.info(f"Trade Executor initialized. Max leverage: {MAX_LEVERAGE}x, Max position: {MAX_POSITION_SIZE_PCT*100}%")
    
    def set_approval_callback(self, callback: callable):
        """Set callback for requesting trade approvals."""
        self._approval_callback = callback
    
    # ========================================================================
    # RISK CHECKS
    # ========================================================================
    
    async def check_risk(self, trade: TradeRequest) -> RiskCheck:
        """
        Perform risk checks on a trade.
        """
        checks = {}
        reasons = []
        
        # Get current state
        balance = await self._get_balance()
        positions = await self._get_positions()
        
        # Check 1: Position size limit
        checks["position_size"] = trade.size_pct <= MAX_SINGLE_TRADE_PCT
        if not checks["position_size"]:
            reasons.append(f"Size {trade.size_pct*100}% exceeds max {MAX_SINGLE_TRADE_PCT*100}%")
        
        # Check 2: Leverage limit
        checks["leverage"] = trade.leverage <= MAX_LEVERAGE
        if not checks["leverage"]:
            reasons.append(f"Leverage {trade.leverage}x exceeds max {MAX_LEVERAGE}x")
        
        # Check 3: Total exposure limit
        current_exposure = sum(p.get("size", 0) for p in positions)
        new_exposure = balance.get("equity", 0) * trade.size_pct
        total_exposure_pct = (current_exposure + new_exposure) / max(balance.get("equity", 1), 1)
        
        checks["total_exposure"] = total_exposure_pct <= MAX_POSITION_SIZE_PCT
        if not checks["total_exposure"]:
            reasons.append(f"Total exposure {total_exposure_pct*100:.1f}% would exceed {MAX_POSITION_SIZE_PCT*100}%")
        
        # Check 4: Daily loss limit
        self._check_daily_reset()
        checks["daily_loss"] = self._daily_pnl > -(balance.get("equity", 0) * DAILY_LOSS_LIMIT_PCT)
        if not checks["daily_loss"]:
            reasons.append(f"Daily loss limit ({DAILY_LOSS_LIMIT_PCT*100}%) reached")
        
        # Check 5: Has stop loss
        checks["has_stop_loss"] = trade.stop_loss_pct is not None
        if not checks["has_stop_loss"]:
            reasons.append("No stop loss defined")
        
        passed = all(checks.values())
        
        return RiskCheck(passed=passed, checks=checks, reasons=reasons)
    
    # ========================================================================
    # TRADE MANAGEMENT
    # ========================================================================
    
    async def request_trade(
        self,
        symbol: str,
        direction: TradeDirection,
        size_pct: float,
        leverage: int = 1,
        stop_loss_pct: float = None,
        take_profit_pct: float = None,
        confidence: float = 0.0,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Request a trade.
        
        Workflow:
        1. Create trade request
        2. Run risk checks
        3. If high confidence + passes risk → can auto-execute
        4. Otherwise → requires approval
        """
        trade = TradeRequest(
            id=f"trade-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            symbol=symbol,
            direction=direction,
            size_pct=size_pct,
            leverage=leverage,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            confidence=confidence,
            reason=reason
        )
        
        # Run risk checks
        risk = await self.check_risk(trade)
        
        if not risk.passed:
            trade.status = TradeStatus.REJECTED
            return {
                "status": "rejected",
                "trade_id": trade.id,
                "reasons": risk.reasons,
                "risk_check": risk.to_dict()
            }
        
        # Check if can auto-execute
        can_auto = (
            confidence >= AUTO_EXECUTE_CONFIDENCE and
            trade.stop_loss_pct is not None and
            trade.size_pct <= MAX_SINGLE_TRADE_PCT * 0.5  # Extra conservative for auto
        )
        
        if can_auto:
            # Auto-execute
            return await self._execute_trade(trade)
        
        # Requires approval
        self.pending_trades[trade.id] = trade
        
        if self._approval_callback:
            await self._approval_callback({
                "type": "trade",
                "trade": trade.to_dict(),
                "risk_check": risk.to_dict()
            })
        
        return {
            "status": "pending_approval",
            "trade_id": trade.id,
            "trade": trade.to_dict(),
            "risk_check": risk.to_dict(),
            "message": f"{direction.value.upper()} {symbol} requires approval"
        }
    
    async def approve_trade(self, trade_id: str) -> Dict[str, Any]:
        """Approve and execute a pending trade."""
        if trade_id not in self.pending_trades:
            return {"status": "error", "message": "Trade not found"}
        
        trade = self.pending_trades[trade_id]
        
        if trade.status != TradeStatus.PENDING:
            return {"status": "error", "message": f"Trade in invalid state: {trade.status.value}"}
        
        # Re-check risk (market may have changed)
        risk = await self.check_risk(trade)
        if not risk.passed:
            trade.status = TradeStatus.REJECTED
            del self.pending_trades[trade_id]
            return {
                "status": "rejected",
                "message": "Risk check failed on re-evaluation",
                "reasons": risk.reasons
            }
        
        trade.status = TradeStatus.APPROVED
        trade.approved_at = datetime.now()
        
        # Execute
        result = await self._execute_trade(trade)
        
        if result.get("status") == "filled":
            del self.pending_trades[trade_id]
        
        return result
    
    async def reject_trade(self, trade_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a pending trade."""
        if trade_id not in self.pending_trades:
            return {"status": "error", "message": "Trade not found"}
        
        trade = self.pending_trades[trade_id]
        trade.status = TradeStatus.REJECTED
        
        del self.pending_trades[trade_id]
        
        return {"status": "rejected", "trade_id": trade_id, "reason": reason}
    
    async def _execute_trade(self, trade: TradeRequest) -> Dict[str, Any]:
        """Execute a trade via WhaleTrack Live."""
        trade.status = TradeStatus.EXECUTING
        
        try:
            # Build payload for WhaleTrack Live
            payload = {
                "symbol": trade.symbol,
                "side": trade.direction.value,
                "size_percent": trade.size_pct * 100,
                "leverage": trade.leverage
            }
            
            if trade.stop_loss_pct:
                payload["stop_loss_percent"] = trade.stop_loss_pct * 100
            if trade.take_profit_pct:
                payload["take_profit_percent"] = trade.take_profit_pct * 100
            
            response = await self.http_client.post(
                f"{WHALETRACK_LIVE_URL}/api/live/trade",
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                
                trade.status = TradeStatus.FILLED
                trade.executed_at = datetime.now()
                trade.entry_price = data.get("entry_price")
                trade.filled_size = data.get("filled_size")
                
                logger.info(f"Trade executed: {trade.id} - {trade.direction.value} {trade.symbol}")
                
                return {
                    "status": "filled",
                    "trade": trade.to_dict(),
                    "execution": data
                }
            else:
                trade.status = TradeStatus.FAILED
                error = response.json() if response.headers.get("content-type") == "application/json" else response.text
                return {
                    "status": "failed",
                    "trade_id": trade.id,
                    "error": error
                }
        
        except Exception as e:
            trade.status = TradeStatus.FAILED
            logger.error(f"Trade execution error: {e}")
            return {
                "status": "failed",
                "trade_id": trade.id,
                "error": str(e)
            }
    
    # ========================================================================
    # POSITION MANAGEMENT
    # ========================================================================
    
    async def get_positions(self) -> Dict[str, Any]:
        """Get current positions."""
        positions = await self._get_positions()
        return {
            "status": "success",
            "positions": positions,
            "count": len(positions)
        }
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close a position."""
        return await self.request_trade(
            symbol=symbol,
            direction=TradeDirection.CLOSE,
            size_pct=1.0,  # Close full position
            reason="Manual close request"
        )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _get_balance(self) -> Dict[str, Any]:
        """Get account balance."""
        try:
            response = await self.http_client.get(
                f"{WHALETRACK_LIVE_URL}/api/live/balance"
            )
            if response.status_code == 200:
                return response.json()
            return {"equity": 0, "balance": 0}
        except:
            return {"equity": 0, "balance": 0}
    
    async def _get_positions(self) -> List[Dict]:
        """Get current positions."""
        try:
            response = await self.http_client.get(
                f"{WHALETRACK_LIVE_URL}/api/live/positions"
            )
            if response.status_code == 200:
                return response.json().get("positions", [])
            return []
        except:
            return []
    
    def _check_daily_reset(self):
        """Reset daily P&L if new day."""
        today = datetime.now().date()
        if today > self._daily_reset_date:
            self._daily_pnl = 0
            self._daily_reset_date = today
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L tracking."""
        self._check_daily_reset()
        self._daily_pnl += pnl
    
    # ========================================================================
    # PENDING TRADES
    # ========================================================================
    
    def get_pending_trades(self) -> List[Dict]:
        """Get all pending trades."""
        return [t.to_dict() for t in self.pending_trades.values()]


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_executor: Optional[TradeExecutor] = None


def get_trade_executor() -> TradeExecutor:
    """Get global trade executor."""
    global _executor
    if _executor is None:
        _executor = TradeExecutor()
    return _executor


async def execute_trade(
    symbol: str,
    direction: str,
    size_pct: float,
    **kwargs
) -> Dict:
    """Execute a trade."""
    dir_enum = TradeDirection(direction.lower())
    return await get_trade_executor().request_trade(
        symbol=symbol,
        direction=dir_enum,
        size_pct=size_pct,
        **kwargs
    )


async def get_position_status() -> Dict:
    """Get position status."""
    return await get_trade_executor().get_positions()


