#!/usr/bin/env python3
"""
🔬 BACKTEST ENGINE
====================

Simulates trading strategy on historical data.

Features:
- Accurate fill simulation with slippage
- Commission modeling
- Uses same trading logic as live system
- Generates full metrics
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Tuple

from .data_manager import HistoricalDataManager, OHLCV, get_data_manager
from ..risk_metrics import RiskMetrics, RiskMetricsCalculator, get_risk_calculator

logger = logging.getLogger("aria.trading.backtest.engine")


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    symbols: List[str]
    interval: str = "15m"
    
    # Strategy parameters
    min_confidence: float = 80.0
    max_position_pct: float = 0.25
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 6.0
    
    # Simulation settings
    slippage_bps: float = 10       # Simulated slippage
    commission_bps: float = 5      # Trading fees
    
    def to_dict(self) -> Dict:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_capital": self.initial_capital,
            "symbols": self.symbols,
            "interval": self.interval,
            "min_confidence": self.min_confidence,
            "max_position_pct": self.max_position_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "slippage_bps": self.slippage_bps,
            "commission_bps": self.commission_bps
        }


@dataclass
class SimulatedPosition:
    """A simulated position during backtest."""
    symbol: str
    side: str  # "long" or "short"
    size: float
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    
    @property
    def is_long(self) -> bool:
        return self.side == "long"
    
    def get_pnl(self, current_price: float) -> float:
        """Calculate P&L at current price."""
        if self.is_long:
            return (current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - current_price) * self.size
    
    def get_pnl_pct(self, current_price: float) -> float:
        """Calculate P&L percentage."""
        position_value = self.entry_price * self.size
        if position_value == 0:
            return 0
        return (self.get_pnl(current_price) / position_value) * 100


@dataclass
class SimulatedTrade:
    """A completed trade during backtest."""
    symbol: str
    side: str
    size: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    exit_reason: str  # "stop_loss", "take_profit", "signal"
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "exit_reason": self.exit_reason
        }


@dataclass
class BacktestResult:
    """Results of a backtest run."""
    config: BacktestConfig
    
    # Performance
    final_equity: float = 0.0
    total_return_pct: float = 0.0
    risk_metrics: Optional[RiskMetrics] = None
    
    # Trades
    total_trades: int = 0
    trades: List[SimulatedTrade] = field(default_factory=list)
    
    # Equity curve
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    
    # Comparison
    buy_hold_return_pct: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "config": self.config.to_dict(),
            "final_equity": round(self.final_equity, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "risk_metrics": self.risk_metrics.to_dict() if self.risk_metrics else None,
            "total_trades": self.total_trades,
            "trades": [t.to_dict() for t in self.trades[:20]],  # First 20
            "buy_hold_return_pct": round(self.buy_hold_return_pct, 2)
        }


class BacktestEngine:
    """
    Simulates trading strategy on historical data.
    
    Features:
    - Accurate fill simulation with slippage
    - Commission modeling
    - Uses same trading logic as live system
    - Generates full metrics
    """
    
    def __init__(self):
        self._data_manager = get_data_manager()
        self._risk_calculator = get_risk_calculator()
    
    async def run_backtest(
        self,
        config: BacktestConfig,
        strategy: Optional[Callable] = None
    ) -> BacktestResult:
        """
        Run a backtest.
        
        Args:
            config: Backtest configuration
            strategy: Optional custom strategy function
                      Signature: (candles, position, capital) -> signal
                      signal: {"action": "buy"/"sell"/"hold", "confidence": 0-100}
            
        Returns:
            BacktestResult with full metrics
        """
        logger.info(f"🔬 Starting backtest: {config.start_date} to {config.end_date}")
        
        result = BacktestResult(config=config)
        
        # Fetch historical data
        all_candles: Dict[str, List[OHLCV]] = {}
        for symbol in config.symbols:
            candles = await self._data_manager.fetch_historical(
                symbol=symbol,
                interval=config.interval,
                start=config.start_date,
                end=config.end_date
            )
            all_candles[symbol] = candles
            logger.info(f"📊 Loaded {len(candles)} candles for {symbol}")
        
        if not all_candles:
            logger.error("No data available for backtest")
            return result
        
        # Initialize simulation state
        capital = config.initial_capital
        position: Optional[SimulatedPosition] = None
        trades: List[SimulatedTrade] = []
        equity_curve: List[Tuple[datetime, float]] = []
        
        # Track buy & hold for comparison
        first_prices = {s: c[0].close if c else 0 for s, c in all_candles.items()}
        
        # Get all timestamps and sort
        all_timestamps = set()
        for candles in all_candles.values():
            for c in candles:
                all_timestamps.add(c.timestamp)
        
        sorted_timestamps = sorted(all_timestamps)
        
        # Simulate through time
        for timestamp in sorted_timestamps:
            # Get current candles for each symbol
            current_candles = {}
            for symbol, candles in all_candles.items():
                for c in candles:
                    if c.timestamp == timestamp:
                        current_candles[symbol] = c
                        break
            
            if not current_candles:
                continue
            
            # Check stop loss / take profit for current position
            if position:
                candle = current_candles.get(position.symbol)
                if candle:
                    exit_price, exit_reason = self._check_exit(position, candle)
                    
                    if exit_price:
                        # Close position
                        pnl = position.get_pnl(exit_price)
                        pnl_pct = position.get_pnl_pct(exit_price)
                        
                        # Apply commission
                        commission = abs(exit_price * position.size) * (config.commission_bps / 10000)
                        pnl -= commission
                        
                        trade = SimulatedTrade(
                            symbol=position.symbol,
                            side=position.side,
                            size=position.size,
                            entry_price=position.entry_price,
                            exit_price=exit_price,
                            entry_time=position.entry_time,
                            exit_time=timestamp,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            exit_reason=exit_reason
                        )
                        trades.append(trade)
                        
                        capital += pnl
                        position = None
            
            # Generate signal if no position
            if position is None and strategy:
                for symbol, candle in current_candles.items():
                    signal = await self._generate_signal(
                        strategy, symbol, all_candles[symbol], capital, config
                    )
                    
                    if signal and signal.get("action") in ["buy", "sell"]:
                        confidence = signal.get("confidence", 0)
                        
                        if confidence >= config.min_confidence:
                            # Open position
                            position_size = (capital * config.max_position_pct) / candle.close
                            
                            # Apply slippage
                            entry_price = self._apply_slippage(
                                candle.close, 
                                signal["action"],
                                config.slippage_bps
                            )
                            
                            # Apply commission
                            commission = abs(entry_price * position_size) * (config.commission_bps / 10000)
                            capital -= commission
                            
                            # Calculate stop/take profit
                            if signal["action"] == "buy":
                                stop_loss = entry_price * (1 - config.stop_loss_pct / 100)
                                take_profit = entry_price * (1 + config.take_profit_pct / 100)
                                side = "long"
                            else:
                                stop_loss = entry_price * (1 + config.stop_loss_pct / 100)
                                take_profit = entry_price * (1 - config.take_profit_pct / 100)
                                side = "short"
                            
                            position = SimulatedPosition(
                                symbol=symbol,
                                side=side,
                                size=position_size,
                                entry_price=entry_price,
                                entry_time=timestamp,
                                stop_loss=stop_loss,
                                take_profit=take_profit
                            )
                            break
            
            # Calculate current equity
            current_equity = capital
            if position:
                candle = current_candles.get(position.symbol)
                if candle:
                    current_equity += position.get_pnl(candle.close)
            
            equity_curve.append((timestamp, current_equity))
        
        # Close any remaining position at end
        if position and all_candles.get(position.symbol):
            last_candle = all_candles[position.symbol][-1]
            pnl = position.get_pnl(last_candle.close)
            pnl_pct = position.get_pnl_pct(last_candle.close)
            
            trade = SimulatedTrade(
                symbol=position.symbol,
                side=position.side,
                size=position.size,
                entry_price=position.entry_price,
                exit_price=last_candle.close,
                entry_time=position.entry_time,
                exit_time=last_candle.timestamp,
                pnl=pnl,
                pnl_pct=pnl_pct,
                exit_reason="end_of_test"
            )
            trades.append(trade)
            capital += pnl
        
        # Calculate results
        result.final_equity = capital
        result.total_return_pct = ((capital - config.initial_capital) / config.initial_capital) * 100
        result.trades = trades
        result.total_trades = len(trades)
        result.equity_curve = equity_curve
        
        # Calculate buy & hold return
        last_prices = {}
        for s, candles in all_candles.items():
            if candles:
                last_prices[s] = candles[-1].close
        
        if first_prices and last_prices:
            bh_returns = []
            for s in first_prices:
                if first_prices[s] > 0 and s in last_prices:
                    bh_returns.append((last_prices[s] - first_prices[s]) / first_prices[s] * 100)
            if bh_returns:
                result.buy_hold_return_pct = sum(bh_returns) / len(bh_returns)
        
        # Calculate risk metrics
        equity_values = [e[1] for e in equity_curve]
        trade_dicts = [{"pnl": t.pnl, "pnl_pct": t.pnl_pct} for t in trades]
        result.risk_metrics = self._risk_calculator.calculate_metrics(equity_values, trade_dicts)
        
        logger.info(
            f"✅ Backtest complete: {result.total_trades} trades, "
            f"{result.total_return_pct:.2f}% return"
        )
        
        return result
    
    def _check_exit(
        self,
        position: SimulatedPosition,
        candle: OHLCV
    ) -> Tuple[Optional[float], str]:
        """Check if stop loss or take profit hit."""
        if position.is_long:
            # Check stop loss (price went below)
            if candle.low <= position.stop_loss:
                return position.stop_loss, "stop_loss"
            
            # Check take profit (price went above)
            if candle.high >= position.take_profit:
                return position.take_profit, "take_profit"
        else:
            # Short position
            # Check stop loss (price went above)
            if candle.high >= position.stop_loss:
                return position.stop_loss, "stop_loss"
            
            # Check take profit (price went below)
            if candle.low <= position.take_profit:
                return position.take_profit, "take_profit"
        
        return None, ""
    
    def _apply_slippage(
        self,
        price: float,
        side: str,
        slippage_bps: float
    ) -> float:
        """Apply simulated slippage."""
        slippage = price * (slippage_bps / 10000)
        
        if side == "buy":
            return price + slippage  # Pay more
        else:
            return price - slippage  # Receive less
    
    async def _generate_signal(
        self,
        strategy: Callable,
        symbol: str,
        candles: List[OHLCV],
        capital: float,
        config: BacktestConfig
    ) -> Optional[Dict]:
        """Generate trading signal from strategy."""
        try:
            import asyncio
            if asyncio.iscoroutinefunction(strategy):
                return await strategy(symbol, candles, capital, config)
            else:
                return strategy(symbol, candles, capital, config)
        except Exception as e:
            logger.error(f"Strategy error: {e}")
            return None
    
    def generate_report(self, result: BacktestResult) -> str:
        """Generate detailed backtest report."""
        lines = [
            "🔬 **BACKTEST REPORT**",
            "=" * 40,
            "",
            f"📅 Period: {result.config.start_date.date()} to {result.config.end_date.date()}",
            f"💰 Initial Capital: ${result.config.initial_capital:,.2f}",
            f"📊 Symbols: {', '.join(result.config.symbols)}",
            "",
            "**📈 Performance**",
            f"  Final Equity: ${result.final_equity:,.2f}",
            f"  Total Return: {result.total_return_pct:+.2f}%",
            f"  Buy & Hold: {result.buy_hold_return_pct:+.2f}%",
            f"  Alpha: {result.total_return_pct - result.buy_hold_return_pct:+.2f}%",
            "",
            f"**🎯 Trades**",
            f"  Total: {result.total_trades}",
        ]
        
        if result.risk_metrics:
            lines.extend([
                f"  Win Rate: {result.risk_metrics.win_rate:.1f}%",
                f"  Profit Factor: {result.risk_metrics.profit_factor:.2f}",
                "",
                "**📊 Risk Metrics**",
                f"  Sharpe Ratio: {result.risk_metrics.sharpe_ratio:.2f}",
                f"  Sortino Ratio: {result.risk_metrics.sortino_ratio:.2f}",
                f"  Max Drawdown: {result.risk_metrics.max_drawdown_pct:.2f}%",
            ])
        
        return "\n".join(lines)


# Singleton
_engine: Optional[BacktestEngine] = None


def get_backtest_engine() -> BacktestEngine:
    """Get or create global backtest engine."""
    global _engine
    if _engine is None:
        _engine = BacktestEngine()
    return _engine









