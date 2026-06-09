#!/usr/bin/env python3
"""
🤖 ARIA AUTO-TRADER - LEVEL 10 EDITION
========================================

Automated trading using the full Level 10 trading system:
- MasterTradeController for signal evaluation
- Persistence for state recovery
- Kelly criterion position sizing
- Drawdown protection
- Trailing stops
- Learning and pattern recognition
- Regime detection
- Correlation management

This is the orchestrator that ties everything together.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger("aria.trading.auto")

# Configuration
WHALETRACK_URL = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8600")
STEWARD_CHAT_ID = int(os.getenv("STEWARD_CHAT_ID", "1759822075"))


@dataclass
class AutoTraderConfig:
    """
    Configuration for auto-trading.
    
    AGGRESSIVE MODE - Probability Hunter Strategy:
    - Full balance commitment on high-confidence signals
    - Higher bar for entries (80%+ confidence)
    - Single focused position for maximum impact
    - Quick rotation to better opportunities
    """
    enabled: bool = False
    max_position_usd: float = 500.0  # Use up to full balance
    max_total_exposure: float = 500.0  # Can be all-in on one trade
    min_confidence: float = 80.0  # Only trade 80%+ signals (higher bar)
    min_risk_reward: float = 2.0  # Better R:R requirement
    max_daily_loss: float = 150.0  # Stop if lose 30% in a day
    leverage: float = 3.0  # 3x leverage for growth
    symbols: List[str] = None  # Symbols to trade (None = all)
    consecutive_loss_pause: int = 3  # Pause after 3 losses in a row
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["SOL", "BTC", "ETH"]


class AriaAutoTrader:
    """
    Automated trading agent for Aria - LEVEL 10 Edition.
    
    Uses full Level 10 trading system:
    - MasterTradeController for intelligent decisions
    - Persistence for crash recovery
    - Kelly position sizing
    - Drawdown protection
    - All advanced features
    """
    
    def __init__(self, config: Optional[AutoTraderConfig] = None):
        self.config = config or AutoTraderConfig()
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._initialized = False
        
        # Get hyperliquid connection
        from .hyperliquid_live import get_hyperliquid
        self.hl = get_hyperliquid()
        
        # Level 10 Components (lazy loaded)
        self._controller = None
        self._persistence = None
        self._drawdown = None
        self._capital = None
        self._learning = None
        self._patterns = None
        self._trailing = None
        self._time_rules = None
        
        logger.info(f"🤖 AutoTrader L10 initialized (enabled={self.config.enabled})")
    
    def _init_components(self):
        """Lazily initialize Level 10 components."""
        if self._initialized:
            return
        
        try:
            from .trade_controller import get_trade_controller
            from .persistence import get_persistence
            from .drawdown_protector import get_drawdown_protector
            from .capital_manager import get_capital_manager
            from .learning_engine import get_learning_engine
            from .pattern_learner import get_pattern_learner
            from .trailing_stop import get_trailing_manager
            from .time_rules import get_time_exit_manager
            
            self._controller = get_trade_controller()
            self._persistence = get_persistence()
            self._drawdown = get_drawdown_protector()
            self._capital = get_capital_manager()
            self._learning = get_learning_engine()
            self._patterns = get_pattern_learner()
            self._trailing = get_trailing_manager()
            self._time_rules = get_time_exit_manager()
            
            # Configure controller
            self._controller.min_confidence = self.config.min_confidence
            self._controller.min_risk_reward = self.config.min_risk_reward
            
            self._initialized = True
            logger.info("✅ Level 10 components initialized")
            
        except Exception as e:
            logger.error(f"Failed to init Level 10 components: {e}")
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def status(self) -> Dict:
        """Get current auto-trader status with Level 10 data."""
        self._init_components()
        
        positions = self.hl.get_positions() if self.hl.is_connected else []
        total_exposure = sum(p.get("size_usd", 0) for p in positions)
        
        # Get Level 10 stats
        perf_stats = {}
        drawdown_status = {}
        capital_status = {}
        
        if self._persistence:
            perf_stats = self._persistence.get_performance_stats(days=30)
        
        if self._drawdown:
            drawdown_status = self._drawdown.get_status()
        
        if self._capital:
            capital_status = self._capital.get_status()
        
        return {
            "enabled": self.config.enabled,
            "running": self._running,
            "connected": self.hl.is_connected,
            "level_10": self._initialized,
            "balance": self.hl.get_balance() if self.hl.is_connected else 0,
            "positions": len(positions),
            "total_exposure": total_exposure,
            
            # From persistence
            "total_trades": perf_stats.get("total_trades", 0),
            "win_rate": perf_stats.get("win_rate", 0),
            "total_pnl": perf_stats.get("total_pnl", 0),
            "profit_factor": perf_stats.get("profit_factor", 0),
            
            # From drawdown protector
            "drawdown_pct": drawdown_status.get("drawdown_pct", 0),
            "size_multiplier": drawdown_status.get("size_multiplier", 1.0),
            "trading_paused": drawdown_status.get("trading_paused", False),
            
            # From capital manager
            "trading_capital": capital_status.get("trading_capital", 0),
            
            "config": {
                "max_position_usd": self.config.max_position_usd,
                "min_confidence": self.config.min_confidence,
                "max_daily_loss": self.config.max_daily_loss,
                "symbols": self.config.symbols,
                "leverage": self.config.leverage
            }
        }
    
    @property
    def win_rate(self) -> float:
        """Get win rate from persistence."""
        if self._persistence:
            stats = self._persistence.get_performance_stats(days=30)
            return stats.get("win_rate", 0)
        return 0.0
    
    async def start(self) -> Dict:
        """Start auto-trading with Level 10 system."""
        if not self.hl.is_connected:
            return {"success": False, "error": "Hyperliquid not connected"}
        
        if self._running:
            return {"success": False, "error": "Already running"}
        
        # Initialize Level 10 components
        self._init_components()
        
        # Initialize controller
        if self._controller:
            await self._controller.initialize()
            self._controller.enabled = True
        
        # Start trailing stop manager
        if self._trailing:
            await self._trailing.start()
        
        # Start time rules manager
        if self._time_rules:
            await self._time_rules.start()
        
        self.config.enabled = True
        self._running = True
        
        # Save state
        if self._persistence:
            from .persistence import AutoTraderState
            state = AutoTraderState(
                enabled=True,
                running=True,
                max_position_usd=self.config.max_position_usd,
                min_confidence=self.config.min_confidence,
                max_daily_loss=self.config.max_daily_loss,
                leverage=self.config.leverage,
                symbols=self.config.symbols,
                started_at=datetime.now().isoformat()
            )
            self._persistence.save_auto_trader_state(state)
        
        # Start the monitoring loop
        self._loop_task = asyncio.create_task(self._trading_loop())
        
        # Notify
        balance = self.hl.get_balance()
        await self._notify(
            f"🚀 **LEVEL 10 AUTO-TRADER ACTIVATED**\n\n"
            f"**Account:**\n"
            f"• Balance: ${balance:,.2f}\n"
            f"• Leverage: {self.config.leverage}x\n\n"
            f"**Level 10 Systems:**\n"
            f"✅ Kelly Position Sizing\n"
            f"✅ Drawdown Protection\n"
            f"✅ Trailing Stops\n"
            f"✅ Learning Engine\n"
            f"✅ Pattern Recognition\n"
            f"✅ Trade Persistence\n\n"
            f"🎯 Hunting for high-probability trades..."
        )
        
        logger.info("🤖 Auto-trading started (Level 10)")
        return {"success": True, "status": self.status}
    
    async def stop(self) -> Dict:
        """Stop auto-trading."""
        self.config.enabled = False
        self._running = False
        
        if self._controller:
            self._controller.enabled = False
            await self._controller.shutdown()
        
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        
        # Save state
        if self._persistence:
            from .persistence import AutoTraderState
            state = self._persistence.restore_auto_trader_state()
            state.enabled = False
            state.running = False
            self._persistence.save_auto_trader_state(state)
        
        await self._notify("🛑 **Auto-Trading STOPPED**")
        
        logger.info("🛑 Auto-trading stopped")
        return {"success": True}
    
    async def emergency_stop(self) -> Dict:
        """Emergency stop - close all positions and stop trading."""
        await self.stop()
        
        # Cancel all orders first
        from .order_manager import get_order_manager
        om = get_order_manager()
        
        for symbol in self.config.symbols:
            await om.cancel_all_orders(symbol)
        
        # Close all positions
        result = await self.hl.close_all_positions()
        
        await self._notify(
            f"🚨 **EMERGENCY STOP**\n\n"
            f"Closed {result.get('closed', 0)} positions\n"
            f"Cancelled all orders\n"
            f"Auto-trading disabled"
        )
        
        return result
    
    async def _trading_loop(self):
        """Main trading loop using Level 10 system."""
        logger.info("🔄 Trading loop started (Level 10)")
        
        while self._running:
            try:
                # Check drawdown protection
                if self._drawdown and self._drawdown.should_pause_trading():
                    logger.info("Trading paused by drawdown protector")
                    await asyncio.sleep(60)
                    continue
                
                # Check capital rules
                if self._capital:
                    can_trade, reason = self._capital.can_trade()
                    if not can_trade:
                        logger.info(f"Trading paused by capital manager: {reason}")
                        await asyncio.sleep(60)
                        continue
                
                # Get current signals
                signals = await self._fetch_signals()
                
                if signals:
                    await self._process_signals_l10(signals)
                
                # Wait before next cycle
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(60)
        
        logger.info("🔄 Trading loop stopped")
    
    async def _fetch_signals(self) -> Dict:
        """Fetch current signals from WhaleTrack."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{WHALETRACK_URL}/api/liquidity-clarity")
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("symbols", {})
        except Exception as e:
            logger.error(f"Failed to fetch signals: {e}")
        return {}
    
    async def _process_signals_l10(self, signals: Dict):
        """
        Process signals using Level 10 MasterTradeController.
        
        The controller handles:
        - Confidence adjustment via learning
        - Pattern matching
        - Regime detection
        - Kelly position sizing
        - Drawdown adjustment
        - Correlation check
        """
        if not self._controller:
            return
        
        # Find the best signal
        best_signal = None
        best_score = 0
        
        for symbol, data in signals.items():
            clean_symbol = symbol.replace("/USDT", "").replace("USDT", "")
            
            if clean_symbol not in self.config.symbols:
                continue
            
            action = data.get("recommended_action", "WAIT")
            confidence = data.get("clarity_score", 0)
            rr = data.get("risk_reward", 0)
            
            if action not in ["LONG", "SHORT"]:
                continue
            
            if confidence < self.config.min_confidence:
                continue
            
            score = confidence * rr
            
            if score > best_score:
                best_score = score
                best_signal = {
                    "symbol": clean_symbol,
                    "side": "long" if action == "LONG" else "short",
                    "confidence": confidence,
                    "price": data.get("price", 0),
                    "target": data.get("primary_target"),
                    "stop": data.get("stop_loss"),
                    "risk_reward": rr,
                    "source": "signal-shark"
                }
        
        if not best_signal:
            return
        
        # Check current positions
        positions = self.hl.get_positions()
        current_position = positions[0] if positions else None
        
        if current_position:
            # Already have a position - check if we should rotate
            current_symbol = current_position["symbol"]
            current_side = current_position["side"]
            
            if current_symbol == best_signal["symbol"] and current_side == best_signal["side"]:
                return  # Already in this position
            
            # Check if new signal is significantly better
            if best_signal["confidence"] > 85:  # High bar for rotation
                await self._close_with_tracking(current_symbol, f"rotating to {best_signal['symbol']}")
            else:
                return  # Stay in current position
        
        # Use MasterTradeController to evaluate and execute
        from .trade_controller import TradingSignal, process_signal
        
        result = await process_signal(best_signal)
        
        if result.get("executed"):
            logger.info(f"✅ L10 Trade executed: {result.get('trade_id')}")
        elif result.get("decision") == "pass":
            logger.debug(f"Signal passed: {result.get('reasoning')}")
    
    async def _close_with_tracking(self, symbol: str, reason: str):
        """Close position and track using Level 10 system."""
        positions = self.hl.get_positions()
        position = next((p for p in positions if p["symbol"] == symbol), None)
        
        if not position:
            return
        
        # Get exit info
        pnl = position.get("unrealized_pnl", 0)
        pnl_pct = position.get("pnl_percent", 0)
        exit_price = position.get("mark_price", 0)
        
        # Close position
        result = await self.hl.close_position(symbol)
        
        if result.get("success"):
            # Update Level 10 systems
            if self._drawdown:
                is_win = pnl > 0
                equity = self.hl.get_balance()
                self._drawdown.record_trade_result(is_win, pnl, equity)
            
            if self._capital:
                equity = self.hl.get_balance()
                self._capital.record_profit(pnl, equity)
            
            # Find trade in persistence and close it
            if self._persistence:
                active = self._persistence.get_active_trades()
                for trade in active:
                    if trade.symbol == symbol:
                        self._persistence.close_trade(
                            trade_id=trade.id,
                            exit_price=exit_price,
                            exit_reason=reason,
                            pnl=pnl,
                            pnl_percent=pnl_pct
                        )
                        break
            
            # Feed to learning
            if self._learning:
                await self._learning.process_completed_trade(
                    symbol=symbol,
                    entry_time=datetime.now(),  # Approximate
                    pnl=pnl,
                    signal_source="signal-shark",
                    reported_confidence=80  # Approximate
                )
            
            # Notify
            emoji = "🟢" if pnl > 0 else "🔴"
            stats = self._persistence.get_performance_stats(days=30) if self._persistence else {}
            
            await self._notify(
                f"{emoji} **TRADE CLOSED**\n\n"
                f"**{position['side'].upper()} {symbol}**\n"
                f"• P&L: **${pnl:+,.2f}** ({pnl_pct:+.1f}%)\n"
                f"• Reason: {reason}\n\n"
                f"📊 **Level 10 Stats:**\n"
                f"• Win Rate: **{stats.get('win_rate', 0):.0f}%**\n"
                f"• Total P&L: **${stats.get('total_pnl', 0):+,.2f}**\n"
                f"• Drawdown: {self._drawdown.current_drawdown_pct:.1f}%" if self._drawdown else ""
            )
            
            logger.info(f"📊 Closed {symbol}: ${pnl:+,.2f}")
    
    async def _notify(self, message: str):
        """Send notification to steward."""
        try:
            from telegram.bot import send_message
            await send_message(STEWARD_CHAT_ID, message)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def get_performance_report(self) -> str:
        """Get formatted performance report with Level 10 data."""
        if not self._persistence:
            return "Level 10 system not initialized"
        
        stats = self._persistence.get_performance_stats(days=30)
        drawdown = self._drawdown.get_status() if self._drawdown else {}
        
        insights = None
        if self._learning:
            insights = self._learning.get_trading_insights()
        
        report = f"""📊 **Level 10 Trading Performance**

**Win Rate:** {stats.get('win_rate', 0):.0f}%
**Total P&L:** ${stats.get('total_pnl', 0):+,.2f}
**Profit Factor:** {stats.get('profit_factor', 0):.2f}
**Total Trades:** {stats.get('total_trades', 0)}

**Risk Status:**
• Drawdown: {drawdown.get('drawdown_pct', 0):.1f}%
• Size Multiplier: {drawdown.get('size_multiplier', 1.0):.0%}
• Trading Paused: {drawdown.get('trading_paused', False)}"""
        
        if insights and insights.recommendations:
            report += f"\n\n**AI Insights:**\n"
            for rec in insights.recommendations[:3]:
                report += f"• {rec}\n"
        
        return report


# Singleton
_auto_trader: Optional[AriaAutoTrader] = None


def get_auto_trader() -> AriaAutoTrader:
    """Get or create global auto-trader."""
    global _auto_trader
    if _auto_trader is None:
        _auto_trader = AriaAutoTrader()
    return _auto_trader


async def start_auto_trading(
    max_position: float = 100.0,
    min_confidence: float = 75.0,
    symbols: List[str] = None
) -> Dict:
    """Start auto-trading with configuration."""
    trader = get_auto_trader()
    trader.config.max_position_usd = max_position
    trader.config.min_confidence = min_confidence
    if symbols:
        trader.config.symbols = symbols
    return await trader.start()


async def stop_auto_trading() -> Dict:
    """Stop auto-trading."""
    trader = get_auto_trader()
    return await trader.stop()


async def emergency_stop() -> Dict:
    """Emergency stop - close all and disable."""
    trader = get_auto_trader()
    return await trader.emergency_stop()


def get_auto_trading_status() -> Dict:
    """Get auto-trading status."""
    trader = get_auto_trader()
    return trader.status
