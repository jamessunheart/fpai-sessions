#!/usr/bin/env python3
"""
🔄 TRADING STATE RECOVERY
==========================

Recovers trading state after service restart:
- Restores auto-trader configuration and stats
- Reconciles DB positions with exchange positions
- Re-establishes trailing stops for open positions
- Resumes auto-trading if it was enabled
- Alerts steward of recovery status

Ensures no data loss or orphaned positions.
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger("aria.trading.recovery")

STEWARD_CHAT_ID = int(os.getenv("STEWARD_CHAT_ID", "1759822075"))


@dataclass
class ReconciliationResult:
    """Result of position reconciliation."""
    matched: int = 0           # Positions matched between DB and exchange
    imported: int = 0          # Positions imported from exchange
    marked_closed: int = 0     # DB positions marked as closed
    updated: int = 0           # Positions with updated values
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class RecoveryResult:
    """Result of full recovery process."""
    success: bool
    auto_trader_restored: bool = False
    auto_trader_was_enabled: bool = False
    positions_reconciled: ReconciliationResult = None
    trailing_stops_restored: int = 0
    errors: List[str] = None
    message: str = ""
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.positions_reconciled is None:
            self.positions_reconciled = ReconciliationResult()


class TradingRecovery:
    """
    Recovers trading state after service restart.
    
    Called on startup to ensure consistent state between:
    - Local database
    - Hyperliquid exchange
    - In-memory trading state
    """
    
    def __init__(self):
        from .persistence import get_persistence
        from .order_manager import get_order_manager
        from .trailing_stop import get_trailing_manager
        
        self.persistence = get_persistence()
        self.order_manager = get_order_manager()
        self.trailing_manager = get_trailing_manager()
    
    async def recover_state(self) -> RecoveryResult:
        """
        Full recovery process.
        
        Steps:
        1. Load auto_trader_state from DB
        2. Check Hyperliquid for open positions
        3. Reconcile DB positions vs exchange positions
        4. Re-establish trailing stops for open positions
        5. Resume auto-trading if was enabled
        6. Alert steward of recovery status
        """
        result = RecoveryResult(success=False)
        
        try:
            logger.info("🔄 Starting trading state recovery...")
            
            # 1. Restore auto-trader state
            auto_state = await self._restore_auto_trader_state()
            result.auto_trader_restored = auto_state is not None
            result.auto_trader_was_enabled = auto_state.enabled if auto_state else False
            
            # 2. Reconcile positions
            result.positions_reconciled = await self._reconcile_positions()
            
            # 3. Restore trailing stops
            result.trailing_stops_restored = await self._restore_trailing_stops()
            
            # 4. Resume auto-trading if was enabled
            if result.auto_trader_was_enabled:
                await self._resume_auto_trading(auto_state)
            
            # 5. Build success message
            result.success = True
            result.message = self._build_recovery_message(result)
            
            # 6. Alert steward
            await self._notify_steward(result)
            
            logger.info(f"✅ Recovery complete: {result.message}")
            
        except Exception as e:
            result.errors.append(str(e))
            result.message = f"Recovery failed: {e}"
            logger.error(f"❌ Recovery failed: {e}")
        
        return result
    
    async def _restore_auto_trader_state(self):
        """Restore auto-trader state from database."""
        try:
            from .auto_trader import get_auto_trader
            
            # Load persisted state
            state = self.persistence.restore_auto_trader_state()
            
            if not state:
                logger.info("No previous auto-trader state found")
                return None
            
            # Apply to auto-trader
            trader = get_auto_trader()
            trader.config.max_position_usd = state.max_position_usd
            trader.config.min_confidence = state.min_confidence
            trader.config.max_daily_loss = state.max_daily_loss
            trader.config.leverage = state.leverage
            trader.config.symbols = state.symbols
            
            # Restore performance stats
            trader._total_trades = state.total_trades
            trader._winning_trades = state.winning_trades
            trader._total_pnl = state.total_pnl
            trader._consecutive_losses = state.consecutive_losses
            
            # Check if daily stats need reset
            today = datetime.now().strftime("%Y-%m-%d")
            if state.daily_reset_date != today:
                trader._daily_pnl = 0.0
            else:
                trader._daily_pnl = state.daily_pnl
            
            logger.info(
                f"📊 Restored auto-trader state: "
                f"{state.total_trades} trades, "
                f"${state.total_pnl:+,.2f} total P&L"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Failed to restore auto-trader state: {e}")
            return None
    
    async def _reconcile_positions(self) -> ReconciliationResult:
        """
        Reconcile database positions with exchange positions.
        
        Handles:
        - Position in DB but not on exchange → Mark as closed
        - Position on exchange but not in DB → Import it
        - Position values differ → Trust exchange, update DB
        """
        result = ReconciliationResult()
        
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            if not hl.is_connected:
                result.errors.append("Exchange not connected")
                return result
            
            # Get positions from both sources
            db_positions = self.persistence.get_active_trades()
            exchange_positions = hl.get_positions()
            
            db_symbols = {p.symbol.upper(): p for p in db_positions}
            exchange_symbols = {p["symbol"].upper(): p for p in exchange_positions}
            
            # Check DB positions against exchange
            for symbol, db_pos in db_symbols.items():
                if symbol in exchange_symbols:
                    # Position exists in both
                    exchange_pos = exchange_symbols[symbol]
                    result.matched += 1
                    
                    # Check if values need updating
                    if (db_pos.size != exchange_pos["size"] or 
                        db_pos.entry_price != exchange_pos["entry_price"]):
                        # Update DB with exchange values
                        db_pos.size = exchange_pos["size"]
                        db_pos.entry_price = exchange_pos["entry_price"]
                        self.persistence.save_trade(db_pos)
                        result.updated += 1
                        logger.info(f"📝 Updated {symbol} with exchange values")
                else:
                    # Position in DB but not on exchange → closed
                    self.persistence.close_trade(
                        trade_id=db_pos.id,
                        exit_price=0,  # Unknown
                        exit_reason="reconciliation_closed",
                        pnl=0,
                        pnl_percent=0
                    )
                    result.marked_closed += 1
                    logger.info(f"📝 Marked {symbol} as closed (not on exchange)")
            
            # Check for exchange positions not in DB
            for symbol, exchange_pos in exchange_symbols.items():
                if symbol not in db_symbols:
                    # Import from exchange
                    await self._import_position(exchange_pos)
                    result.imported += 1
                    logger.info(f"📥 Imported {symbol} from exchange")
            
            logger.info(
                f"🔄 Reconciliation: {result.matched} matched, "
                f"{result.imported} imported, {result.marked_closed} closed"
            )
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"Reconciliation error: {e}")
        
        return result
    
    async def _import_position(self, exchange_pos: Dict):
        """Import a position from exchange to database."""
        from .persistence import TradeRecord
        import uuid
        
        trade = TradeRecord(
            id=f"imported_{uuid.uuid4().hex[:8]}",
            symbol=exchange_pos["symbol"],
            side=exchange_pos["side"],
            entry_price=exchange_pos["entry_price"],
            entry_time=datetime.now(),  # Unknown, use now
            size=exchange_pos["size"],
            size_usd=exchange_pos["size_usd"],
            leverage=exchange_pos.get("leverage", 1.0),
            signal_source="imported",
            status="open",
            notes="Imported during recovery - entry time unknown"
        )
        
        self.persistence.save_trade(trade)
    
    async def _restore_trailing_stops(self) -> int:
        """
        Re-establish trailing stops for open positions.
        """
        restored = 0
        
        try:
            from .trailing_stop import TrailingPosition, TrailingStopConfig, TrailingState
            
            # Get active positions
            active_trades = self.persistence.get_active_trades()
            
            for trade in active_trades:
                # Create trailing position with default config
                trailing_pos = TrailingPosition(
                    symbol=trade.symbol,
                    side=trade.side,
                    entry_price=trade.entry_price,
                    size=trade.size,
                    high_watermark=trade.entry_price,
                    low_watermark=trade.entry_price,
                    state=TrailingState.INACTIVE,
                    config=TrailingStopConfig()
                )
                
                await self.trailing_manager.start_monitoring(trade.symbol, trailing_pos)
                restored += 1
            
            if restored > 0:
                await self.trailing_manager.start()
                logger.info(f"🎯 Restored {restored} trailing stop monitors")
            
        except Exception as e:
            logger.error(f"Failed to restore trailing stops: {e}")
        
        return restored
    
    async def _resume_auto_trading(self, state):
        """Resume auto-trading if it was enabled."""
        try:
            from .auto_trader import get_auto_trader
            
            trader = get_auto_trader()
            trader.config.enabled = True
            
            # Start the trading loop
            result = await trader.start()
            
            if result.get("success"):
                logger.info("🤖 Auto-trading resumed from previous state")
            else:
                logger.warning(f"Failed to resume auto-trading: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Failed to resume auto-trading: {e}")
    
    def _build_recovery_message(self, result: RecoveryResult) -> str:
        """Build human-readable recovery message."""
        parts = []
        
        if result.auto_trader_restored:
            parts.append("Auto-trader state restored")
        
        recon = result.positions_reconciled
        if recon.matched or recon.imported or recon.marked_closed:
            parts.append(
                f"Positions: {recon.matched} matched, "
                f"{recon.imported} imported, "
                f"{recon.marked_closed} closed"
            )
        
        if result.trailing_stops_restored:
            parts.append(f"{result.trailing_stops_restored} trailing stops restored")
        
        if result.auto_trader_was_enabled:
            parts.append("Auto-trading resumed")
        
        return " | ".join(parts) if parts else "No state to recover"
    
    async def _notify_steward(self, result: RecoveryResult):
        """Notify steward of recovery status."""
        try:
            from telegram.bot import send_message
            
            if not result.success:
                message = f"🔴 **TRADING RECOVERY FAILED**\n\n{result.message}"
            elif result.positions_reconciled.imported > 0 or result.auto_trader_was_enabled:
                # Only notify if something significant happened
                message = f"""🔄 **TRADING STATE RECOVERED**

{result.message}

**Current State:**
• Positions: {result.positions_reconciled.matched + result.positions_reconciled.imported}
• Auto-Trading: {'Resumed' if result.auto_trader_was_enabled else 'Off'}
• Trailing Stops: {result.trailing_stops_restored}"""
                
                await send_message(STEWARD_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Failed to notify steward: {e}")


# Singleton
_recovery: Optional[TradingRecovery] = None


def get_recovery() -> TradingRecovery:
    """Get or create global recovery instance."""
    global _recovery
    if _recovery is None:
        _recovery = TradingRecovery()
    return _recovery


async def run_recovery() -> RecoveryResult:
    """
    Run full trading state recovery.
    
    Should be called on service startup.
    """
    recovery = get_recovery()
    return await recovery.recover_state()









