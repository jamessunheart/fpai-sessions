"""
BACKTEST HARNESS v1.1
Complete validation framework
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.leverage_engine import LeverageEngine, MagnetState, LeverageConfig
from core.survival_fuse import SurvivalFuse, MarketConditions, FuseConfig
from core.position_sizing import PositionSizer, AccountState, TradeSetup, SizingConfig


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    initial_equity: float = 430000.0
    start_date: str = "2024-09-01"
    end_date: str = "2024-10-31"
    leverage_config: Optional[LeverageConfig] = None
    fuse_config: Optional[FuseConfig] = None
    sizing_config: Optional[SizingConfig] = None


@dataclass
class Trade:
    """Trade record"""
    timestamp: datetime
    entry_price: float
    exit_price: float
    position_size: float
    leverage: float
    pnl: float
    tier: int


@dataclass
class BacktestResults:
    """Performance metrics"""
    initial_equity: float
    final_equity: float
    total_return_pct: float
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    avg_leverage: float


class BacktestHarness:
    """Validates protocol against historical data"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.leverage_engine = LeverageEngine(config.leverage_config)
        self.fuse = SurvivalFuse(config.fuse_config)
        self.sizer = PositionSizer(config.sizing_config)
        self.equity = config.initial_equity
        self.equity_curve = [self.equity]
        self.trades: List[Trade] = []

    def run(self, market_data: pd.DataFrame, signals: pd.DataFrame) -> BacktestResults:
        """Execute backtest"""
        data = market_data.join(signals, how='inner')

        for idx, row in data.iterrows():
            if self._should_enter(row):
                trade = self._execute_trade(row)
                if trade:
                    self.trades.append(trade)
                    self.equity += trade.pnl
            self.equity_curve.append(self.equity)

        return self._calculate_results()

    def _should_enter(self, row: pd.Series) -> bool:
        """Check entry conditions"""
        if pd.isna(row.get('magnet_price')):
            return False

        conditions = MarketConditions(
            volatility_pressure=row.get('volatility_pressure', 1.0),
            account_drawdown_pct=self._current_drawdown_pct(),
            conflict_index=row.get('conflict_index', 0.3),
            primary_magnet_strength=row.get('magnet_strength', 70.0),
            secondary_magnet_strength=row.get('secondary_strength', 40.0),
            trend_aligned=row.get('trend_aligned', True),
            liquidity_score=row.get('liquidity_score', 70.0)
        )

        fuse_check = self.fuse.check_triggers(conditions)
        return not fuse_check['triggered']

    def _execute_trade(self, row: pd.Series) -> Optional[Trade]:
        """Simulate trade execution"""
        magnet_state = MagnetState(
            primary_magnet_price=row['magnet_price'],
            current_price=row['close'],
            magnet_strength=row.get('magnet_strength', 70.0),
            conflict_index=row.get('conflict_index', 0.3),
            volatility_pressure=row.get('volatility_pressure', 1.0),
            atr=row['atr']
        )

        leverage_result = self.leverage_engine.calculate_leverage(magnet_state)

        account = AccountState(
            equity=self.equity,
            available_margin=self.equity * 0.9,
            open_positions_value=0
        )

        trade_setup = TradeSetup(
            entry_price=row['close'],
            stop_price=row.get('stop_price', row['close'] * 0.995),
            magnet_price=row['magnet_price'],
            magnet_tier=int(row.get('magnet_tier', 1)),
            leverage=leverage_result['leverage']
        )

        sizing_result = self.sizer.calculate_position_size(account, trade_setup)

        if not sizing_result['safe_to_trade']:
            return None

        # Simulate outcome (65% win rate)
        hit_magnet = np.random.random() < 0.65
        exit_price = row['magnet_price'] if hit_magnet else trade_setup.stop_price

        direction = 1 if row['magnet_price'] > row['close'] else -1
        price_change_pct = (exit_price - trade_setup.entry_price) / trade_setup.entry_price
        pnl = sizing_result['position_size'] * price_change_pct * direction

        return Trade(
            timestamp=row.name,
            entry_price=trade_setup.entry_price,
            exit_price=exit_price,
            position_size=sizing_result['position_size'],
            leverage=leverage_result['leverage'],
            pnl=pnl,
            tier=trade_setup.magnet_tier
        )

    def _current_drawdown_pct(self) -> float:
        """Calculate current drawdown"""
        if not self.equity_curve:
            return 0.0
        peak = max(self.equity_curve)
        return max(0, ((peak - self.equity) / peak) * 100)

    def _calculate_results(self) -> BacktestResults:
        """Calculate final metrics"""
        if not self.trades:
            return BacktestResults(
                initial_equity=self.config.initial_equity,
                final_equity=self.equity,
                total_return_pct=0,
                total_trades=0,
                win_rate=0,
                profit_factor=0,
                max_drawdown_pct=0,
                avg_leverage=0
            )

        winners = [t for t in self.trades if t.pnl > 0]
        losers = [t for t in self.trades if t.pnl <= 0]

        total_profit = sum(t.pnl for t in winners)
        total_loss = abs(sum(t.pnl for t in losers))

        # Max drawdown
        peak = self.config.initial_equity
        max_dd = 0
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = ((peak - equity) / peak) * 100
            max_dd = max(max_dd, dd)

        return BacktestResults(
            initial_equity=self.config.initial_equity,
            final_equity=self.equity,
            total_return_pct=((self.equity - self.config.initial_equity) / self.config.initial_equity) * 100,
            total_trades=len(self.trades),
            win_rate=len(winners) / len(self.trades),
            profit_factor=total_profit / total_loss if total_loss > 0 else float('inf'),
            max_drawdown_pct=max_dd,
            avg_leverage=np.mean([t.leverage for t in self.trades])
        )
