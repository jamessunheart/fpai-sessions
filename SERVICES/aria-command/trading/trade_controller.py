#!/usr/bin/env python3
"""
🎛️ MASTER TRADE CONTROLLER
============================

Orchestrates all trading components into a unified system:
- Signal evaluation with intelligence enhancement
- Position sizing with multiple factors
- Order execution with proper stops
- Position management and monitoring
- Learning from completed trades

This is the brain that replaces simple auto_trader.
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger("aria.trading.controller")

STEWARD_CHAT_ID = int(os.getenv("STEWARD_CHAT_ID", "1759822075"))


@dataclass
class TradingSignal:
    """An incoming trading signal."""
    symbol: str
    side: str  # "long" or "short"
    confidence: float  # 0-100
    price: float
    target: Optional[float] = None
    stop: Optional[float] = None
    risk_reward: float = 2.0
    source: str = "signal-shark"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class TradeDecision:
    """Decision on whether and how to trade."""
    action: str  # "trade", "pass", "wait"
    symbol: str
    side: str
    
    # Sizing
    position_size_usd: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_prices: List[float] = None
    leverage: float = 1.0
    
    # Confidence and scoring
    original_confidence: float = 0.0
    adjusted_confidence: float = 0.0
    pattern_score: float = 0.0
    regime: str = "unknown"
    
    # Reasoning
    reasoning: List[str] = None
    
    def __post_init__(self):
        if self.take_profit_prices is None:
            self.take_profit_prices = []
        if self.reasoning is None:
            self.reasoning = []


class MasterTradeController:
    """
    Orchestrates all trading components.
    
    This is the Level 10 trading brain that:
    1. FILTERS signals through multiple checks
    2. ENHANCES with learned intelligence
    3. SIZES positions optimally
    4. EXECUTES with proper risk management
    5. MANAGES positions with trailing/TP
    6. LEARNS from completed trades
    """
    
    def __init__(self):
        # Core components
        from .persistence import get_persistence
        from .order_manager import get_order_manager
        from .trailing_stop import get_trailing_manager
        from .recovery import get_recovery
        
        self.persistence = get_persistence()
        self.order_manager = get_order_manager()
        self.trailing_stops = get_trailing_manager()
        self.recovery = get_recovery()
        
        # Execution components
        from .scaled_entry import get_scaled_entry_manager
        from .profit_taker import get_profit_taker
        from .time_rules import get_time_exit_manager
        
        self.scaled_entry = get_scaled_entry_manager()
        self.profit_taker = get_profit_taker()
        self.time_rules = get_time_exit_manager()
        
        # Intelligence components
        from .learning_engine import get_learning_engine
        from .regime_detector import get_regime_detector
        from .pattern_learner import get_pattern_learner, MarketConditions
        
        self.learner = get_learning_engine()
        self.regime_detector = get_regime_detector()
        self.pattern_learner = get_pattern_learner()
        
        # Money management
        from .position_sizer import get_position_sizer, PerformanceStats
        from .drawdown_protector import get_drawdown_protector
        from .capital_manager import get_capital_manager
        from .correlation_manager import get_correlation_manager, Position
        
        self.position_sizer = get_position_sizer()
        self.drawdown_protector = get_drawdown_protector()
        self.capital_manager = get_capital_manager()
        self.correlation_manager = get_correlation_manager()
        
        # Configuration
        self.min_confidence = 75.0
        self.min_risk_reward = 1.5
        self.enabled = False
        
        # State
        self._running = False
    
    async def initialize(self):
        """Initialize the controller and recover state."""
        logger.info("🎛️ Initializing Master Trade Controller...")
        
        # Run recovery
        recovery_result = await self.recovery.recover_state()
        
        if recovery_result.success:
            logger.info(f"✅ Controller initialized: {recovery_result.message}")
        else:
            logger.warning(f"⚠️ Recovery issues: {recovery_result.message}")
        
        # Start background managers
        await self.trailing_stops.start()
        await self.time_rules.start()
        
        self._running = True
    
    async def shutdown(self):
        """Graceful shutdown."""
        self._running = False
        await self.trailing_stops.stop()
        await self.time_rules.stop()
        logger.info("🎛️ Trade Controller shut down")
    
    async def evaluate_signal(self, signal: TradingSignal) -> TradeDecision:
        """
        Full signal evaluation pipeline.
        
        Steps:
        1. FILTER - Basic eligibility checks
        2. ENHANCE - Apply learned intelligence
        3. SIZE - Calculate optimal position
        4. DECIDE - Make final decision
        """
        decision = TradeDecision(
            action="pass",
            symbol=signal.symbol,
            side=signal.side,
            original_confidence=signal.confidence
        )
        
        try:
            # ====== 1. FILTER ======
            
            # Check if controller is enabled
            if not self.enabled:
                decision.reasoning.append("Controller not enabled")
                return decision
            
            # Check drawdown protection
            if self.drawdown_protector.should_pause_trading():
                decision.reasoning.append("Trading paused (drawdown protection)")
                return decision
            
            # Check capital rules
            can_trade, reason = self.capital_manager.can_trade()
            if not can_trade:
                decision.reasoning.append(f"Capital check failed: {reason}")
                return decision
            
            # Check minimum confidence
            if signal.confidence < self.min_confidence:
                decision.reasoning.append(f"Confidence too low ({signal.confidence}% < {self.min_confidence}%)")
                return decision
            
            # Check risk/reward
            if signal.risk_reward < self.min_risk_reward:
                decision.reasoning.append(f"R:R too low ({signal.risk_reward} < {self.min_risk_reward})")
                return decision
            
            decision.reasoning.append("✓ Passed filters")
            
            # ====== 2. ENHANCE ======
            
            # Detect market regime
            regime = await self.regime_detector.detect_regime(signal.symbol)
            decision.regime = regime.value
            
            regime_adj = self.regime_detector.get_regime_adjustments(regime)
            decision.reasoning.append(f"Regime: {regime.value}")
            
            # Get adjusted confidence from learning
            hour = datetime.now().hour
            adjusted_conf = self.learner.get_adjusted_confidence(
                raw_confidence=signal.confidence,
                symbol=signal.symbol,
                hour=hour,
                signal_source=signal.source
            )
            decision.adjusted_confidence = adjusted_conf
            
            if adjusted_conf < self.min_confidence:
                decision.reasoning.append(f"Adjusted confidence too low ({adjusted_conf:.1f}%)")
                return decision
            
            # Check pattern match
            from .pattern_learner import MarketConditions
            conditions = MarketConditions(
                symbol=signal.symbol,
                side=signal.side,
                hour=hour,
                day_of_week=datetime.now().weekday(),
                confidence=signal.confidence,
                regime=regime.value
            )
            
            pattern_score, matching_patterns = self.pattern_learner.get_pattern_score(conditions)
            decision.pattern_score = pattern_score
            
            if matching_patterns:
                decision.reasoning.append(f"Matches {len(matching_patterns)} winning patterns (score: {pattern_score:.0f})")
            
            # ====== 3. SIZE ======
            
            # Get performance stats
            perf_stats = self._get_performance_stats()
            
            # Get balance
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            balance = hl.get_account_value() if hl.is_connected else 0
            
            if balance <= 0:
                decision.reasoning.append("Unable to get account balance")
                return decision
            
            # Update drawdown with current balance
            self.drawdown_protector.update_equity(balance)
            
            # Calculate stop distance
            if signal.stop:
                stop_distance_pct = abs(signal.price - signal.stop) / signal.price * 100
            else:
                stop_distance_pct = 2.0  # Default 2%
            
            # Get Kelly-based position size
            from .position_sizer import PerformanceStats
            position_size = self.position_sizer.get_position_size(
                balance=balance,
                symbol=signal.symbol,
                confidence=adjusted_conf,
                recent_performance=perf_stats,
                stop_distance_pct=stop_distance_pct
            )
            
            decision.reasoning.append(f"Kelly sizing: ${position_size.size_usd:.0f} ({position_size.size_pct:.1f}%)")
            
            # Apply drawdown multiplier
            dd_multiplier = self.drawdown_protector.get_size_multiplier()
            size_after_dd = position_size.size_usd * dd_multiplier
            
            if dd_multiplier < 1.0:
                decision.reasoning.append(f"Drawdown reduction: {dd_multiplier:.0%}")
            
            # Apply regime adjustment
            size_after_regime = size_after_dd * regime_adj.position_size_multiplier
            
            # Apply correlation check
            current_positions = self._get_current_positions()
            from .correlation_manager import Position as CorrPosition
            corr_positions = [
                CorrPosition(
                    symbol=p["symbol"],
                    side=p["side"],
                    size_usd=p["size_usd"],
                    entry_price=p["entry_price"]
                )
                for p in current_positions
            ]
            
            corr_check = self.correlation_manager.check_portfolio_risk(
                current_positions=corr_positions,
                proposed_symbol=signal.symbol,
                proposed_side=signal.side,
                proposed_size=size_after_regime,
                portfolio_value=balance
            )
            
            final_size = corr_check.adjusted_size
            
            if final_size != size_after_regime:
                decision.reasoning.append(f"Correlation adj: ${size_after_regime:.0f} → ${final_size:.0f}")
            
            # Get capital manager limit
            max_from_capital = self.capital_manager.get_max_position_size()
            final_size = min(final_size, max_from_capital)
            
            decision.position_size_usd = final_size
            decision.leverage = position_size.leverage
            
            # Calculate stop and targets
            if signal.stop:
                decision.stop_loss_price = signal.stop
            else:
                # Default 2% stop
                if signal.side == "long":
                    decision.stop_loss_price = signal.price * 0.98
                else:
                    decision.stop_loss_price = signal.price * 1.02
            
            # Set take profit levels
            if signal.target:
                decision.take_profit_prices = [signal.target]
            else:
                # Default targets at 3%, 6%, 10%
                if signal.side == "long":
                    decision.take_profit_prices = [
                        signal.price * 1.03,
                        signal.price * 1.06,
                        signal.price * 1.10
                    ]
                else:
                    decision.take_profit_prices = [
                        signal.price * 0.97,
                        signal.price * 0.94,
                        signal.price * 0.90
                    ]
            
            # ====== 4. DECIDE ======
            
            # Final decision logic
            if final_size < 10:  # Minimum practical size
                decision.reasoning.append("Position size too small after adjustments")
                return decision
            
            # High pattern score can override lower confidence
            if pattern_score >= 70 and adjusted_conf >= 60:
                decision.action = "trade"
                decision.reasoning.append("Strong pattern match overrides")
            elif adjusted_conf >= self.min_confidence:
                decision.action = "trade"
                decision.reasoning.append("Confidence threshold met")
            else:
                decision.reasoning.append("Does not meet trading criteria")
            
            logger.info(
                f"🎯 Signal evaluated: {signal.symbol} {signal.side} → "
                f"{decision.action.upper()} (conf: {adjusted_conf:.0f}%, size: ${final_size:.0f})"
            )
            
        except Exception as e:
            decision.reasoning.append(f"Error: {str(e)}")
            logger.error(f"Signal evaluation error: {e}")
        
        return decision
    
    async def execute_trade(self, decision: TradeDecision) -> Dict:
        """
        Execute a trade based on decision.
        
        Steps:
        1. ENTER - Execute entry (scaled or market)
        2. PROTECT - Set stops on exchange
        3. MANAGE - Setup profit taking and trailing
        4. RECORD - Store in persistence
        5. NOTIFY - Alert steward
        """
        result = {
            "success": False,
            "trade_id": None,
            "error": None
        }
        
        if decision.action != "trade":
            result["error"] = f"Decision was {decision.action}, not trade"
            return result
        
        try:
            # Get current price
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            prices = hl.get_prices()
            current_price = prices.get(decision.symbol, 0)
            
            if current_price <= 0:
                result["error"] = "Unable to get current price"
                return result
            
            # Calculate size in asset units
            size = decision.position_size_usd / current_price
            
            # 1. Execute entry with stops
            entry_result = await self.order_manager.open_position_with_stops(
                symbol=decision.symbol,
                side=decision.side,
                size=size,
                stop_loss_price=decision.stop_loss_price,
                take_profit_price=decision.take_profit_prices[0] if decision.take_profit_prices else None
            )
            
            if not entry_result.get("success"):
                result["error"] = f"Entry failed: {entry_result.get('error')}"
                return result
            
            filled_price = entry_result.get("filled_price", current_price)
            
            # 2. Create trade record
            from .persistence import TradeRecord
            import uuid
            
            trade_id = f"trade_{uuid.uuid4().hex[:8]}"
            
            trade = TradeRecord(
                id=trade_id,
                symbol=decision.symbol,
                side=decision.side,
                entry_price=filled_price,
                entry_time=datetime.now(),
                size=size,
                size_usd=decision.position_size_usd,
                leverage=decision.leverage,
                stop_loss=decision.stop_loss_price,
                take_profit=decision.take_profit_prices[0] if decision.take_profit_prices else None,
                confidence=decision.adjusted_confidence,
                signal_source="master-controller",
                entry_order_id=entry_result.get("entry_order_id"),
                stop_order_id=entry_result.get("stop_order_id"),
                tp_order_id=entry_result.get("tp_order_id"),
                metadata={
                    "original_confidence": decision.original_confidence,
                    "pattern_score": decision.pattern_score,
                    "regime": decision.regime,
                    "reasoning": decision.reasoning
                }
            )
            
            self.persistence.save_trade(trade)
            
            # 3. Setup profit taking
            if len(decision.take_profit_prices) > 1:
                from .profit_taker import ProfitTakeConfig
                config = ProfitTakeConfig(
                    take_profit_1_pct=abs(decision.take_profit_prices[0] - filled_price) / filled_price * 100,
                    take_profit_2_pct=abs(decision.take_profit_prices[1] - filled_price) / filled_price * 100 if len(decision.take_profit_prices) > 1 else 6.0
                )
                
                await self.profit_taker.setup_profit_targets(
                    symbol=decision.symbol,
                    entry_price=filled_price,
                    total_size=size,
                    side=decision.side,
                    config=config
                )
            
            # 4. Setup trailing stop
            from .trailing_stop import start_trailing_for_position
            await start_trailing_for_position(
                symbol=decision.symbol,
                side=decision.side,
                entry_price=filled_price,
                size=size
            )
            
            # 5. Setup time-based monitoring
            from .time_rules import TimeRules
            await self.time_rules.track_position(
                symbol=decision.symbol,
                entry_time=datetime.now(),
                entry_price=filled_price,
                side=decision.side
            )
            
            result["success"] = True
            result["trade_id"] = trade_id
            
            # 6. Notify steward
            await self._notify_trade_opened(trade, decision)
            
            logger.info(f"✅ Trade executed: {trade_id} - {decision.side} {decision.symbol}")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Trade execution error: {e}")
        
        return result
    
    async def on_trade_closed(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        pnl_percent: float
    ):
        """
        Process a closed trade.
        
        Steps:
        1. RECORD - Update persistence
        2. LEARN - Feed to learning systems
        3. ADJUST - Update risk parameters
        4. NOTIFY - Alert steward
        """
        try:
            # Get trade from persistence
            trade = self.persistence.get_trade(trade_id)
            if not trade:
                logger.warning(f"Trade {trade_id} not found")
                return
            
            # 1. Update trade record
            self.persistence.close_trade(
                trade_id=trade_id,
                exit_price=exit_price,
                exit_reason=exit_reason,
                pnl=pnl,
                pnl_percent=pnl_percent
            )
            
            # Update daily stats
            is_win = pnl > 0
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            equity = hl.get_account_value() if hl.is_connected else 0
            
            self.persistence.update_daily_stats(pnl, is_win, equity)
            
            # 2. Feed to learning engine
            await self.learner.process_completed_trade(
                symbol=trade.symbol,
                entry_time=trade.entry_time,
                pnl=pnl,
                signal_source=trade.signal_source,
                reported_confidence=trade.confidence
            )
            
            # Feed to pattern learner
            await self.pattern_learner.record_trade(
                symbol=trade.symbol,
                side=trade.side,
                entry_time=trade.entry_time,
                pnl=pnl,
                pnl_percent=pnl_percent,
                confidence=trade.confidence,
                regime=trade.metadata.get("regime", "unknown")
            )
            
            # 3. Update risk parameters
            self.drawdown_protector.record_trade_result(is_win, pnl, equity)
            self.capital_manager.record_profit(pnl, equity)
            
            # 4. Stop tracking
            await self.trailing_stops.stop_monitoring(trade.symbol)
            await self.time_rules.stop_tracking(trade.symbol)
            
            # 5. Notify steward
            await self._notify_trade_closed(trade, exit_price, exit_reason, pnl, pnl_percent)
            
            logger.info(f"📊 Trade closed: {trade_id} - ${pnl:+,.2f} ({pnl_percent:+.1f}%)")
            
        except Exception as e:
            logger.error(f"Error processing closed trade: {e}")
    
    def _get_performance_stats(self):
        """Get recent performance stats for position sizing."""
        from .position_sizer import PerformanceStats
        
        stats = self.persistence.get_performance_stats(days=30)
        
        return PerformanceStats(
            win_rate=stats.get("win_rate", 50) / 100,
            avg_win_pct=stats.get("avg_win", 3),
            avg_loss_pct=stats.get("avg_loss", 2),
            total_trades=stats.get("total_trades", 0),
            recent_pnl=stats.get("total_pnl", 0),
            consecutive_losses=self.drawdown_protector._consecutive_losses,
            max_drawdown_pct=self.drawdown_protector.current_drawdown_pct
        )
    
    def _get_current_positions(self) -> List[Dict]:
        """Get current positions from exchange."""
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            return hl.get_positions() if hl.is_connected else []
        except:
            return []
    
    async def _notify_trade_opened(self, trade, decision: TradeDecision):
        """Notify steward of new trade."""
        try:
            from telegram.bot import send_message
            
            message = f"""🎯 **NEW TRADE OPENED**

**{trade.side.upper()} {trade.symbol}**
• Entry: ${trade.entry_price:,.2f}
• Size: ${trade.size_usd:,.0f}
• Leverage: {trade.leverage:.1f}x

**Risk Management:**
• Stop Loss: ${trade.stop_loss:,.2f}
• Take Profit: ${trade.take_profit:,.2f}

**Intelligence:**
• Confidence: {decision.adjusted_confidence:.0f}%
• Pattern Score: {decision.pattern_score:.0f}
• Regime: {decision.regime}

_Trailing stop will activate at +2% profit_"""
            
            await send_message(STEWARD_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Failed to notify: {e}")
    
    async def _notify_trade_closed(self, trade, exit_price, reason, pnl, pnl_pct):
        """Notify steward of closed trade."""
        try:
            from telegram.bot import send_message
            
            emoji = "🟢" if pnl > 0 else "🔴"
            
            message = f"""{emoji} **TRADE CLOSED**

**{trade.side.upper()} {trade.symbol}**
• Entry: ${trade.entry_price:,.2f}
• Exit: ${exit_price:,.2f}
• Reason: {reason}

**Result:**
• P&L: **${pnl:+,.2f}** ({pnl_pct:+.1f}%)

**Insights:**
• Win rate: {self._get_performance_stats().win_rate*100:.0f}%"""
            
            await send_message(STEWARD_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Failed to notify: {e}")
    
    def get_status(self) -> Dict:
        """Get controller status."""
        return {
            "enabled": self.enabled,
            "running": self._running,
            "min_confidence": self.min_confidence,
            "min_risk_reward": self.min_risk_reward,
            "drawdown": self.drawdown_protector.get_status(),
            "capital": self.capital_manager.get_status(),
            "learning_insights": self.learner.get_trading_insights().__dict__,
            "active_positions": len(self._get_current_positions()),
            "performance": self.persistence.get_performance_stats(days=30)
        }


# Singleton
_controller: Optional[MasterTradeController] = None


def get_trade_controller() -> MasterTradeController:
    """Get or create global trade controller."""
    global _controller
    if _controller is None:
        _controller = MasterTradeController()
    return _controller


async def process_signal(signal_data: Dict) -> Dict:
    """
    Process an incoming signal through the full pipeline.
    
    This is the main entry point for trading signals.
    """
    controller = get_trade_controller()
    
    signal = TradingSignal(
        symbol=signal_data.get("symbol", ""),
        side=signal_data.get("side", signal_data.get("action", "").lower()),
        confidence=signal_data.get("confidence", 0),
        price=signal_data.get("price", 0),
        target=signal_data.get("target"),
        stop=signal_data.get("stop"),
        risk_reward=signal_data.get("risk_reward", 2.0),
        source=signal_data.get("source", "signal-shark")
    )
    
    # Evaluate
    decision = await controller.evaluate_signal(signal)
    
    # Execute if decision is to trade
    if decision.action == "trade":
        result = await controller.execute_trade(decision)
        return {
            "decision": "trade",
            "executed": result.get("success"),
            "trade_id": result.get("trade_id"),
            "error": result.get("error"),
            "details": {
                "size_usd": decision.position_size_usd,
                "confidence": decision.adjusted_confidence,
                "reasoning": decision.reasoning
            }
        }
    
    return {
        "decision": decision.action,
        "executed": False,
        "reasoning": decision.reasoning
    }









