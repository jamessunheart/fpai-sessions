#!/usr/bin/env python3
"""
⚡ PROBABILITY SCALPER
========================

High-frequency trading based on probability, not conviction.

Philosophy:
- Many small trades > few big trades
- Quick feedback loop
- Cut losers fast, let winners run slightly
- Only hold for "sweep" setups (strong momentum)
- Build data for learning

Strategy:
- 15-minute decision cycles
- Tight stops (1-1.5%)
- Quick take profits (2-3%)
- Rotate to best opportunity constantly
- Exit if probability drops
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum

logger = logging.getLogger("aria.trading.scalper")


class TradeReason(str, Enum):
    """Why we entered/exited a trade."""
    PROBABILITY_ENTRY = "probability_entry"
    BETTER_OPPORTUNITY = "better_opportunity"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    PROBABILITY_DROP = "probability_drop"
    TIME_EXIT = "time_exit"
    SWEEP_HOLD = "sweep_hold"


@dataclass
class ScalperConfig:
    """Configuration for probability scalping."""
    
    # Position sizing
    max_position_pct: float = 0.80  # Use 80% of capital
    
    # Entry criteria
    min_confidence: float = 75.0    # Lower bar for entries
    min_risk_reward: float = 1.5    # Minimum R:R
    
    # Exit criteria - TIGHT
    stop_loss_pct: float = 1.5      # 1.5% stop (was 3%)
    take_profit_pct: float = 2.5    # 2.5% TP (was 6%)
    
    # Time-based exits
    max_hold_minutes: int = 60      # Exit after 1 hour if flat
    stale_threshold_minutes: int = 30  # Re-evaluate after 30 min
    
    # Sweep detection (hold longer)
    sweep_confidence: float = 90.0  # 90%+ = potential sweep
    sweep_strength: float = 25.0    # 25%+ bias strength = sweep
    sweep_take_profit_pct: float = 5.0  # Wider TP for sweeps
    
    # Rotation
    better_opportunity_threshold: float = 10.0  # Switch if 10%+ better signal
    
    # Risk management
    max_daily_trades: int = 20
    max_daily_loss_pct: float = 5.0  # Stop trading after 5% daily loss
    
    # Cycle timing
    decision_interval_seconds: int = 60  # Check every minute


@dataclass
class ActiveScalp:
    """An active scalping position."""
    symbol: str
    side: str
    entry_price: float
    entry_time: datetime
    size: float
    stop_loss: float
    take_profit: float
    entry_confidence: float
    entry_reason: TradeReason
    is_sweep: bool = False
    
    @property
    def age_minutes(self) -> float:
        return (datetime.now() - self.entry_time).total_seconds() / 60


@dataclass
class ScalpResult:
    """Result of a completed scalp."""
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    size: float
    pnl: float
    pnl_pct: float
    exit_reason: TradeReason
    was_sweep: bool
    entry_confidence: float
    exit_confidence: float
    hold_minutes: float


class ProbabilityScalper:
    """
    High-frequency probability-based trading.
    
    Core Loop (every minute):
    1. Get current signals for all symbols
    2. Find highest probability opportunity
    3. If in position:
       - Check if better opportunity exists → rotate
       - Check stop/TP → exit
       - Check if stale → exit
       - Check if sweep → hold with wider TP
    4. If flat:
       - Enter best opportunity if meets criteria
    5. Log everything for learning
    """
    
    def __init__(self, config: Optional[ScalperConfig] = None):
        self.config = config or ScalperConfig()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # State
        self._position: Optional[ActiveScalp] = None
        self._daily_trades: int = 0
        self._daily_pnl: float = 0.0
        self._trade_history: List[ScalpResult] = []
        self._last_reset: datetime = datetime.now()
        
        # Stats
        self._wins: int = 0
        self._losses: int = 0
        
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def win_rate(self) -> float:
        total = self._wins + self._losses
        return (self._wins / total * 100) if total > 0 else 0.0
    
    @property
    def status(self) -> Dict:
        return {
            "running": self._running,
            "mode": "probability_scalper",
            "position": self._position.symbol if self._position else None,
            "daily_trades": self._daily_trades,
            "daily_pnl": round(self._daily_pnl, 2),
            "wins": self._wins,
            "losses": self._losses,
            "win_rate": round(self.win_rate, 1),
            "config": {
                "stop_loss_pct": self.config.stop_loss_pct,
                "take_profit_pct": self.config.take_profit_pct,
                "min_confidence": self.config.min_confidence,
                "max_hold_minutes": self.config.max_hold_minutes
            }
        }
    
    async def start(self):
        """Start the scalping loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scalping_loop())
        logger.info("⚡ Probability Scalper STARTED")
        
        await self._notify("⚡ **Probability Scalper Started**\n\n"
                          f"Mode: High-frequency trading\n"
                          f"Stop Loss: {self.config.stop_loss_pct}%\n"
                          f"Take Profit: {self.config.take_profit_pct}%\n"
                          f"Max Hold: {self.config.max_hold_minutes} min\n"
                          f"Min Confidence: {self.config.min_confidence}%")
    
    async def stop(self):
        """Stop the scalping loop."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("⚡ Probability Scalper STOPPED")
        await self._notify("⚡ **Probability Scalper Stopped**\n\n"
                          f"Trades today: {self._daily_trades}\n"
                          f"Daily P&L: ${self._daily_pnl:+.2f}\n"
                          f"Win rate: {self.win_rate:.1f}%")
    
    async def _scalping_loop(self):
        """Main scalping loop."""
        while self._running:
            try:
                # Reset daily stats at midnight
                if datetime.now().date() > self._last_reset.date():
                    self._reset_daily_stats()
                
                # Check if we should stop trading
                if self._should_stop_trading():
                    await asyncio.sleep(60)
                    continue
                
                # Run decision cycle
                await self._decision_cycle()
                
            except Exception as e:
                logger.error(f"Scalping error: {e}")
            
            await asyncio.sleep(self.config.decision_interval_seconds)
    
    def _reset_daily_stats(self):
        """Reset daily statistics."""
        logger.info(f"📊 Daily reset - Trades: {self._daily_trades}, P&L: ${self._daily_pnl:+.2f}")
        self._daily_trades = 0
        self._daily_pnl = 0.0
        self._last_reset = datetime.now()
    
    def _should_stop_trading(self) -> bool:
        """Check if we should stop trading for the day."""
        if self._daily_trades >= self.config.max_daily_trades:
            logger.info("🛑 Max daily trades reached")
            return True
        
        # Check daily loss limit
        # This would need capital tracking to implement properly
        return False
    
    async def _decision_cycle(self):
        """Run one decision cycle."""
        # Get all signals
        signals = await self._get_signals()
        
        if not signals:
            return
        
        # Find best opportunity
        best = self._find_best_opportunity(signals)
        
        if self._position:
            # We're in a position - manage it
            await self._manage_position(signals, best)
        else:
            # We're flat - look for entry
            await self._look_for_entry(best)
    
    async def _get_signals(self) -> Dict:
        """Get current signals from WhaleTrack."""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get("http://198.54.123.234:8600/api/liquidity-clarity")
                
                if r.status_code == 200:
                    data = r.json()
                    return data.get("symbols", {})
        
        except Exception as e:
            logger.error(f"Failed to get signals: {e}")
        
        return {}
    
    def _find_best_opportunity(self, signals: Dict) -> Optional[Dict]:
        """Find the best trading opportunity."""
        best = None
        best_score = 0
        
        for symbol, data in signals.items():
            action = data.get("recommended_action", "WAIT")
            
            if action == "WAIT":
                continue
            
            confidence = data.get("clarity_score", 0)
            rr = data.get("risk_reward", 0)
            strength = data.get("bias_strength", 0)
            
            # Calculate opportunity score
            score = confidence + (rr * 10) + (strength * 0.5)
            
            if score > best_score:
                best_score = score
                best = {
                    "symbol": symbol.replace("/USDT", "").replace("USDT", ""),
                    "action": action,
                    "confidence": confidence,
                    "risk_reward": rr,
                    "strength": strength,
                    "price": data.get("price", 0),
                    "target": data.get("primary_target", 0),
                    "stop": data.get("stop_loss", 0),
                    "score": score
                }
        
        return best
    
    async def _manage_position(self, signals: Dict, best: Optional[Dict]):
        """Manage an existing position."""
        pos = self._position
        
        # Get current price and signal for our position
        symbol_key = f"{pos.symbol}/USDT"
        current_signal = signals.get(symbol_key, {})
        current_price = current_signal.get("price", pos.entry_price)
        current_confidence = current_signal.get("clarity_score", 0)
        
        # Calculate current P&L
        if pos.side == "long":
            pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100
        else:
            pnl_pct = (pos.entry_price - current_price) / pos.entry_price * 100
        
        # Check stop loss
        if pnl_pct <= -self.config.stop_loss_pct:
            await self._exit_position(current_price, TradeReason.STOP_LOSS, current_confidence)
            return
        
        # Check take profit
        tp_pct = self.config.sweep_take_profit_pct if pos.is_sweep else self.config.take_profit_pct
        if pnl_pct >= tp_pct:
            await self._exit_position(current_price, TradeReason.TAKE_PROFIT, current_confidence)
            return
        
        # Check if signal reversed
        current_action = current_signal.get("recommended_action", "WAIT")
        if pos.side == "long" and current_action == "SHORT":
            await self._exit_position(current_price, TradeReason.PROBABILITY_DROP, current_confidence)
            return
        if pos.side == "short" and current_action == "LONG":
            await self._exit_position(current_price, TradeReason.PROBABILITY_DROP, current_confidence)
            return
        
        # Check if stale (no movement, low confidence)
        if pos.age_minutes > self.config.stale_threshold_minutes:
            if abs(pnl_pct) < 0.5 and current_confidence < pos.entry_confidence:
                await self._exit_position(current_price, TradeReason.TIME_EXIT, current_confidence)
                return
        
        # Check max hold time (unless sweep)
        if not pos.is_sweep and pos.age_minutes > self.config.max_hold_minutes:
            await self._exit_position(current_price, TradeReason.TIME_EXIT, current_confidence)
            return
        
        # Check for better opportunity
        if best and best["symbol"] != pos.symbol:
            improvement = best["score"] - pos.entry_confidence
            
            if improvement > self.config.better_opportunity_threshold:
                # Close current and open better
                await self._exit_position(current_price, TradeReason.BETTER_OPPORTUNITY, current_confidence)
                await self._enter_position(best)
                return
        
        # Check if this is now a sweep setup
        if not pos.is_sweep:
            if current_confidence >= self.config.sweep_confidence and \
               current_signal.get("bias_strength", 0) >= self.config.sweep_strength:
                pos.is_sweep = True
                logger.info(f"🌊 Position upgraded to SWEEP - wider TP")
                await self._notify(f"🌊 **Sweep Detected**\n\n"
                                  f"{pos.symbol} showing sweep potential\n"
                                  f"Widening TP to {self.config.sweep_take_profit_pct}%")
    
    async def _look_for_entry(self, best: Optional[Dict]):
        """Look for entry opportunity."""
        if not best:
            return
        
        # Check minimum criteria
        if best["confidence"] < self.config.min_confidence:
            return
        
        if best["risk_reward"] < self.config.min_risk_reward:
            return
        
        # Check if it's a sweep setup
        is_sweep = (best["confidence"] >= self.config.sweep_confidence and 
                   best["strength"] >= self.config.sweep_strength)
        
        await self._enter_position(best, is_sweep)
    
    async def _enter_position(self, opportunity: Dict, is_sweep: bool = False):
        """Enter a new position."""
        from .resilient_client import get_resilient_client
        
        client = get_resilient_client()
        
        # Calculate position size
        balance = client.get_balance()
        position_value = balance * self.config.max_position_pct
        size = position_value / opportunity["price"]
        
        # Calculate stops
        if opportunity["action"] == "LONG":
            stop_loss = opportunity["price"] * (1 - self.config.stop_loss_pct / 100)
            take_profit = opportunity["price"] * (1 + self.config.take_profit_pct / 100)
            side = "buy"
        else:
            stop_loss = opportunity["price"] * (1 + self.config.stop_loss_pct / 100)
            take_profit = opportunity["price"] * (1 - self.config.take_profit_pct / 100)
            side = "sell"
        
        # Place order
        try:
            result = await client.place_order(
                symbol=opportunity["symbol"],
                side=side,
                size=size
            )
            
            if result.get("success"):
                self._position = ActiveScalp(
                    symbol=opportunity["symbol"],
                    side="long" if side == "buy" else "short",
                    entry_price=opportunity["price"],
                    entry_time=datetime.now(),
                    size=size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    entry_confidence=opportunity["confidence"],
                    entry_reason=TradeReason.PROBABILITY_ENTRY,
                    is_sweep=is_sweep
                )
                
                self._daily_trades += 1
                
                sweep_tag = " 🌊 SWEEP" if is_sweep else ""
                logger.info(f"📈 Entered {opportunity['symbol']} {side.upper()}{sweep_tag}")
                
                await self._notify(
                    f"📈 **SCALP ENTRY{sweep_tag}**\n\n"
                    f"Symbol: {opportunity['symbol']}\n"
                    f"Side: {side.upper()}\n"
                    f"Price: ${opportunity['price']:,.2f}\n"
                    f"Size: {size:.4f}\n"
                    f"Confidence: {opportunity['confidence']:.0f}%\n"
                    f"Stop: ${stop_loss:,.2f} (-{self.config.stop_loss_pct}%)\n"
                    f"Target: ${take_profit:,.2f} (+{self.config.take_profit_pct}%)"
                )
            else:
                logger.error(f"Entry failed: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"Entry exception: {e}")
    
    async def _exit_position(self, exit_price: float, reason: TradeReason, exit_confidence: float):
        """Exit current position."""
        from .resilient_client import get_resilient_client
        
        if not self._position:
            return
        
        pos = self._position
        client = get_resilient_client()
        
        # Calculate P&L
        if pos.side == "long":
            pnl = (exit_price - pos.entry_price) * pos.size
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price * 100
            close_side = "sell"
        else:
            pnl = (pos.entry_price - exit_price) * pos.size
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price * 100
            close_side = "buy"
        
        # Place close order
        try:
            result = await client.place_order(
                symbol=pos.symbol,
                side=close_side,
                size=pos.size,
                reduce_only=True
            )
            
            if result.get("success"):
                # Record result
                scalp_result = ScalpResult(
                    symbol=pos.symbol,
                    side=pos.side,
                    entry_price=pos.entry_price,
                    exit_price=exit_price,
                    entry_time=pos.entry_time,
                    exit_time=datetime.now(),
                    size=pos.size,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    exit_reason=reason,
                    was_sweep=pos.is_sweep,
                    entry_confidence=pos.entry_confidence,
                    exit_confidence=exit_confidence,
                    hold_minutes=pos.age_minutes
                )
                
                self._trade_history.append(scalp_result)
                self._daily_pnl += pnl
                
                if pnl > 0:
                    self._wins += 1
                else:
                    self._losses += 1
                
                # Clear position
                self._position = None
                
                emoji = "✅" if pnl > 0 else "❌"
                logger.info(f"{emoji} Exited {pos.symbol}: ${pnl:+.2f} ({pnl_pct:+.2f}%) - {reason.value}")
                
                await self._notify(
                    f"{emoji} **SCALP EXIT**\n\n"
                    f"Symbol: {pos.symbol}\n"
                    f"Reason: {reason.value.replace('_', ' ').title()}\n"
                    f"Entry: ${pos.entry_price:,.2f}\n"
                    f"Exit: ${exit_price:,.2f}\n"
                    f"P&L: **${pnl:+.2f}** ({pnl_pct:+.2f}%)\n"
                    f"Hold time: {pos.age_minutes:.0f} min\n\n"
                    f"Daily: ${self._daily_pnl:+.2f} | Win rate: {self.win_rate:.0f}%"
                )
            else:
                logger.error(f"Exit failed: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"Exit exception: {e}")
    
    async def _notify(self, message: str):
        """Send notification to steward."""
        try:
            from telegram.bot import get_bot
            
            bot = await get_bot()
            await bot.send_message(chat_id=1087024913, text=message)
        except Exception as e:
            logger.error(f"Notification failed: {e}")
    
    async def close_current_position(self) -> Dict:
        """Manually close current position."""
        if not self._position:
            return {"success": False, "error": "No position open"}
        
        signals = await self._get_signals()
        symbol_key = f"{self._position.symbol}/USDT"
        current_signal = signals.get(symbol_key, {})
        current_price = current_signal.get("price", self._position.entry_price)
        
        await self._exit_position(current_price, TradeReason.TIME_EXIT, 0)
        
        return {"success": True}
    
    def get_trade_history(self, limit: int = 20) -> List[Dict]:
        """Get recent trade history."""
        history = []
        
        for trade in self._trade_history[-limit:]:
            history.append({
                "symbol": trade.symbol,
                "side": trade.side,
                "entry": trade.entry_price,
                "exit": trade.exit_price,
                "pnl": round(trade.pnl, 2),
                "pnl_pct": round(trade.pnl_pct, 2),
                "reason": trade.exit_reason.value,
                "hold_min": round(trade.hold_minutes, 1),
                "sweep": trade.was_sweep,
                "time": trade.exit_time.isoformat()
            })
        
        return history


# Singleton
_scalper: Optional[ProbabilityScalper] = None


def get_scalper() -> ProbabilityScalper:
    """Get or create global scalper."""
    global _scalper
    if _scalper is None:
        _scalper = ProbabilityScalper()
    return _scalper


async def start_probability_scalping():
    """Start probability scalping."""
    scalper = get_scalper()
    await scalper.start()


async def stop_probability_scalping():
    """Stop probability scalping."""
    scalper = get_scalper()
    await scalper.stop()


def get_scalper_status() -> Dict:
    """Get scalper status."""
    scalper = get_scalper()
    return scalper.status









