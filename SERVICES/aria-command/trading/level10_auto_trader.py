"""
TRUE LEVEL 10 AUTO-TRADER
=========================
Automated trading using the research-backed TRUE LEVEL 10 strategy.

Features:
- Real-time signal detection
- Automatic trade execution
- Position management with stops/targets
- Performance tracking
- Telegram notifications
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass

from .true_level10_strategy import TrueLevel10Strategy, TrueLevel10Config, Indicators
from .hyperliquid_live import get_hyperliquid

logger = logging.getLogger(__name__)

@dataclass
class ActivePosition:
    """Track an active position"""
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    entry_time: datetime
    size: float
    stop_price: float
    target_price: float
    high_since_entry: float
    low_since_entry: float


class Level10AutoTrader:
    """
    Automated trader using TRUE LEVEL 10 strategy.
    
    Monitors markets, generates signals, executes trades,
    manages positions, and tracks performance.
    """
    
    def __init__(self, config: Optional[TrueLevel10Config] = None):
        self.config = config or TrueLevel10Config()
        self.strategy = TrueLevel10Strategy(self.config)
        self.exchange = get_hyperliquid()
        
        # State
        self.running = False
        self.positions: Dict[str, ActivePosition] = {}
        self.last_check: Dict[str, datetime] = {}
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.start_balance = 0.0
        
        # Timing
        self.check_interval_seconds = 60  # Check every minute
        
        logger.info("🎯 Level 10 Auto-Trader initialized")
    
    async def start(self):
        """Start the auto-trader"""
        if self.running:
            logger.warning("Auto-trader already running")
            return
        
        self.running = True
        
        # Get starting balance
        account = await self.exchange.get_account_state()
        if account.get("success"):
            self.start_balance = account.get("account_value", 0)
            logger.info(f"💰 Starting balance: ${self.start_balance:.2f}")
        
        # Recover any existing positions
        await self._recover_positions()
        
        # Start trading loop
        logger.info("🚀 TRUE LEVEL 10 Auto-Trader STARTED")
        await self._notify(f"🎯 TRUE LEVEL 10 Auto-Trader STARTED\n💰 Balance: ${self.start_balance:.2f}")
        
        asyncio.create_task(self._trading_loop())
    
    async def stop(self):
        """Stop the auto-trader"""
        self.running = False
        logger.info("🛑 Auto-trader stopped")
        await self._notify("🛑 TRUE LEVEL 10 Auto-Trader STOPPED")
    
    async def _trading_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                for symbol in self.config.symbols:
                    await self._check_symbol(symbol)
                    await asyncio.sleep(1)  # Small delay between symbols
                
                await asyncio.sleep(self.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(10)
    
    async def _check_symbol(self, symbol: str):
        """Check a symbol for entry/exit signals"""
        try:
            # Get candle data
            candles = await self._fetch_candles(symbol)
            if not candles or len(candles) < 50:
                return
            
            # Calculate indicators
            indicators = self.strategy.calculate_indicators(candles)
            if not indicators:
                return
            
            # Check for position management first
            if symbol in self.positions:
                await self._manage_position(symbol, indicators)
            else:
                # Check for new entry
                await self._check_entry(symbol, indicators)
                
        except Exception as e:
            logger.error(f"Error checking {symbol}: {e}")
    
    async def _fetch_candles(self, symbol: str) -> List[Dict]:
        """Fetch recent candle data"""
        try:
            # Use 4-hour candles for strategy (as backtested)
            import ccxt
            exchange = ccxt.okx()
            ohlcv = exchange.fetch_ohlcv(f"{symbol}/USDT", "4h", limit=60)
            
            return [{
                "time": datetime.fromtimestamp(c[0]/1000),
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5]
            } for c in ohlcv]
            
        except Exception as e:
            logger.error(f"Failed to fetch candles for {symbol}: {e}")
            return []
    
    async def _check_entry(self, symbol: str, indicators: Indicators):
        """Check for entry signal and execute if found"""
        # Get signal from strategy
        signal = self.strategy.get_signal(indicators)
        if not signal:
            return
        
        # Get account balance
        account = await self.exchange.get_account_state()
        if not account.get("success"):
            logger.error("Failed to get account state")
            return
        
        balance = account.get("account_value", 0)
        if balance < 50:
            logger.warning(f"Insufficient balance: ${balance:.2f}")
            return
        
        # Calculate position size
        size = self.strategy.get_position_size(balance, indicators.price)
        
        # Calculate stop and target
        if signal == "LONG":
            stop_price = indicators.price * (1 - self.config.stop_loss_pct / 100)
            target_price = indicators.price * (1 + self.config.take_profit_pct / 100)
            side = "buy"
        else:
            stop_price = indicators.price * (1 + self.config.stop_loss_pct / 100)
            target_price = indicators.price * (1 - self.config.take_profit_pct / 100)
            side = "sell"
        
        # Execute trade
        logger.info(f"🎯 Executing {signal} on {symbol} @ ${indicators.price:.2f}")
        
        result = await self.exchange.place_order(
            symbol=symbol,
            side=side,
            size=size,
            price=None,  # Market order
            reduce_only=False
        )
        
        if result.get("success"):
            # Record position
            self.positions[symbol] = ActivePosition(
                symbol=symbol,
                side="long" if signal == "LONG" else "short",
                entry_price=indicators.price,
                entry_time=datetime.now(),
                size=size,
                stop_price=stop_price,
                target_price=target_price,
                high_since_entry=indicators.price,
                low_since_entry=indicators.price
            )
            
            await self._notify(
                f"🎯 {signal} {symbol}\n"
                f"Entry: ${indicators.price:.2f}\n"
                f"Size: {size:.4f}\n"
                f"Stop: ${stop_price:.2f}\n"
                f"Target: ${target_price:.2f}\n"
                f"Regime: {indicators.regime}"
            )
            
            logger.info(f"✅ Position opened: {signal} {symbol} @ ${indicators.price:.2f}")
        else:
            logger.error(f"❌ Failed to open position: {result.get('error')}")
    
    async def _manage_position(self, symbol: str, indicators: Indicators):
        """Manage an existing position"""
        position = self.positions[symbol]
        current_price = indicators.price
        
        # Update extremes
        position.high_since_entry = max(position.high_since_entry, current_price)
        position.low_since_entry = min(position.low_since_entry, current_price)
        
        # Check exit conditions
        should_exit, reason = self.strategy.should_exit(
            entry_price=position.entry_price,
            current_price=current_price,
            side=position.side,
            entry_time=position.entry_time,
            high_since_entry=position.high_since_entry,
            low_since_entry=position.low_since_entry
        )
        
        if should_exit:
            await self._close_position(symbol, current_price, reason)
    
    async def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Calculate P&L
        if position.side == "long":
            pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
            pnl_pct *= self.config.leverage
        else:
            pnl_pct = (position.entry_price - exit_price) / position.entry_price * 100
            pnl_pct *= self.config.leverage
        
        pnl_usd = (position.size * position.entry_price) * (pnl_pct / 100)
        won = pnl_usd > 0
        
        # Execute close
        close_side = "sell" if position.side == "long" else "buy"
        result = await self.exchange.place_order(
            symbol=symbol,
            side=close_side,
            size=position.size,
            price=None,
            reduce_only=True
        )
        
        if result.get("success"):
            # Update tracking
            self.total_trades += 1
            if won:
                self.winning_trades += 1
            self.total_pnl += pnl_usd
            self.strategy.record_trade(pnl_usd, won)
            
            # Remove from active positions
            del self.positions[symbol]
            
            # Calculate stats
            win_rate = self.winning_trades / self.total_trades * 100 if self.total_trades > 0 else 0
            
            emoji = "🟢" if won else "🔴"
            await self._notify(
                f"{emoji} CLOSED {position.side.upper()} {symbol}\n"
                f"Entry: ${position.entry_price:.2f}\n"
                f"Exit: ${exit_price:.2f}\n"
                f"P&L: ${pnl_usd:+.2f} ({pnl_pct:+.1f}%)\n"
                f"Reason: {reason}\n"
                f"━━━━━━━━━━━━━\n"
                f"Total: {self.total_trades} trades | {win_rate:.0f}% WR\n"
                f"Session P&L: ${self.total_pnl:+.2f}"
            )
            
            logger.info(f"✅ Position closed: {symbol} @ ${exit_price:.2f}, P&L: ${pnl_usd:+.2f}")
        else:
            logger.error(f"❌ Failed to close position: {result.get('error')}")
    
    async def _recover_positions(self):
        """Recover existing positions from exchange"""
        try:
            positions = await self.exchange.get_positions()
            if positions.get("success") and positions.get("positions"):
                for pos in positions["positions"]:
                    symbol = pos.get("symbol", "").replace("/USDT", "").replace("USDT", "")
                    if symbol and float(pos.get("size", 0)) != 0:
                        size = abs(float(pos.get("size", 0)))
                        entry = float(pos.get("entry_price", 0))
                        side = "long" if float(pos.get("size", 0)) > 0 else "short"
                        
                        self.positions[symbol] = ActivePosition(
                            symbol=symbol,
                            side=side,
                            entry_price=entry,
                            entry_time=datetime.now() - timedelta(hours=1),  # Assume 1 hour ago
                            size=size,
                            stop_price=entry * (0.98 if side == "long" else 1.02),
                            target_price=entry * (1.015 if side == "long" else 0.985),
                            high_since_entry=entry,
                            low_since_entry=entry
                        )
                        
                        logger.info(f"📍 Recovered position: {side.upper()} {symbol} @ ${entry:.2f}")
                        
        except Exception as e:
            logger.error(f"Failed to recover positions: {e}")
    
    async def _notify(self, message: str):
        """Send Telegram notification"""
        try:
            from telegram.bot import AriaTelegramBot
            bot = AriaTelegramBot()
            steward_id = 1275066656  # James's Telegram ID
            await bot.send_message(steward_id, message)
        except Exception as e:
            logger.error(f"Notification failed: {e}")
    
    def get_status(self) -> Dict:
        """Get current auto-trader status"""
        win_rate = self.winning_trades / self.total_trades * 100 if self.total_trades > 0 else 0
        
        return {
            "running": self.running,
            "strategy": self.strategy.get_status(),
            "positions": {
                symbol: {
                    "side": pos.side,
                    "entry_price": pos.entry_price,
                    "entry_time": pos.entry_time.isoformat(),
                    "size": pos.size,
                    "stop": pos.stop_price,
                    "target": pos.target_price,
                }
                for symbol, pos in self.positions.items()
            },
            "performance": {
                "start_balance": self.start_balance,
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "win_rate": win_rate,
                "total_pnl": self.total_pnl,
            },
            "config": {
                "symbols": self.config.symbols,
                "leverage": self.config.leverage,
                "position_pct": self.config.position_pct,
                "check_interval": self.check_interval_seconds,
            }
        }


# Singleton instance
_trader_instance = None

def get_level10_trader() -> Level10AutoTrader:
    """Get the Level 10 auto-trader instance"""
    global _trader_instance
    if _trader_instance is None:
        _trader_instance = Level10AutoTrader()
    return _trader_instance


async def start_level10_trading():
    """Start the TRUE LEVEL 10 auto-trader"""
    trader = get_level10_trader()
    await trader.start()
    return trader.get_status()


async def stop_level10_trading():
    """Stop the TRUE LEVEL 10 auto-trader"""
    trader = get_level10_trader()
    await trader.stop()
    return {"success": True, "message": "Level 10 auto-trader stopped"}









