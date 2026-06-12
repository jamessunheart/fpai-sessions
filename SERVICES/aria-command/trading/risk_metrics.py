#!/usr/bin/env python3
"""
📊 RISK METRICS CALCULATOR
============================

Institutional-grade risk-adjusted performance metrics.

Calculates:
- Sharpe Ratio (risk-adjusted return)
- Sortino Ratio (downside risk only)
- Maximum Drawdown and Duration
- Profit Factor and Expectancy
- Various consistency metrics
"""

import math
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("aria.trading.risk")


@dataclass
class RiskMetrics:
    """Comprehensive risk-adjusted performance metrics."""
    
    # Return metrics
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    
    # Risk metrics
    volatility_pct: float = 0.0          # Standard deviation of returns
    max_drawdown_pct: float = 0.0        # Maximum peak-to-trough decline
    max_drawdown_duration_days: int = 0  # Longest time in drawdown
    
    # Risk-adjusted metrics
    sharpe_ratio: float = 0.0            # (Return - RiskFree) / Volatility
    sortino_ratio: float = 0.0           # Return / Downside Volatility
    calmar_ratio: float = 0.0            # Annualized Return / Max Drawdown
    
    # Trade quality
    profit_factor: float = 0.0           # Gross Profit / Gross Loss
    expectancy: float = 0.0              # Avg Win * WR - Avg Loss * LR
    
    # Consistency
    win_rate: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    largest_win_pct: float = 0.0
    largest_loss_pct: float = 0.0
    consecutive_wins_max: int = 0
    consecutive_losses_max: int = 0
    
    # Meta
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    trading_days: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "returns": {
                "total_return_pct": round(self.total_return_pct, 2),
                "annualized_return_pct": round(self.annualized_return_pct, 2)
            },
            "risk": {
                "volatility_pct": round(self.volatility_pct, 2),
                "max_drawdown_pct": round(self.max_drawdown_pct, 2),
                "max_drawdown_duration_days": self.max_drawdown_duration_days
            },
            "risk_adjusted": {
                "sharpe_ratio": round(self.sharpe_ratio, 2),
                "sortino_ratio": round(self.sortino_ratio, 2),
                "calmar_ratio": round(self.calmar_ratio, 2)
            },
            "trade_quality": {
                "profit_factor": round(self.profit_factor, 2),
                "expectancy": round(self.expectancy, 2)
            },
            "consistency": {
                "win_rate": round(self.win_rate, 2),
                "avg_win_pct": round(self.avg_win_pct, 2),
                "avg_loss_pct": round(self.avg_loss_pct, 2),
                "largest_win_pct": round(self.largest_win_pct, 2),
                "largest_loss_pct": round(self.largest_loss_pct, 2),
                "consecutive_wins_max": self.consecutive_wins_max,
                "consecutive_losses_max": self.consecutive_losses_max
            },
            "summary": {
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "trading_days": self.trading_days
            },
            "interpretation": self._get_interpretation()
        }
    
    def _get_interpretation(self) -> Dict:
        """Get human-readable interpretation of metrics."""
        return {
            "sharpe": self._interpret_sharpe(),
            "overall": self._interpret_overall()
        }
    
    def _interpret_sharpe(self) -> str:
        """Interpret Sharpe ratio."""
        if self.sharpe_ratio >= 3.0:
            return "Excellent - Top tier performance"
        elif self.sharpe_ratio >= 2.0:
            return "Very Good - Strong risk-adjusted returns"
        elif self.sharpe_ratio >= 1.0:
            return "Good - Acceptable risk-adjusted returns"
        elif self.sharpe_ratio >= 0.5:
            return "Mediocre - Subpar risk-adjusted returns"
        else:
            return "Poor - Returns don't justify the risk"
    
    def _interpret_overall(self) -> str:
        """Overall performance interpretation."""
        score = 0
        
        if self.sharpe_ratio >= 1.0:
            score += 2
        elif self.sharpe_ratio >= 0.5:
            score += 1
        
        if self.win_rate >= 60:
            score += 2
        elif self.win_rate >= 50:
            score += 1
        
        if self.profit_factor >= 2.0:
            score += 2
        elif self.profit_factor >= 1.5:
            score += 1
        
        if self.max_drawdown_pct <= 10:
            score += 2
        elif self.max_drawdown_pct <= 20:
            score += 1
        
        if score >= 7:
            return "Excellent trading performance"
        elif score >= 5:
            return "Good trading performance"
        elif score >= 3:
            return "Average trading performance"
        else:
            return "Needs improvement"


class RiskMetricsCalculator:
    """
    Calculates institutional-grade risk metrics.
    
    Uses daily equity curve to compute:
    - Sharpe ratio (risk-adjusted return)
    - Sortino ratio (downside risk only)
    - Maximum drawdown and duration
    - Various other metrics
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 5%)
        """
        self._risk_free_rate = risk_free_rate
    
    def calculate_metrics(
        self,
        equity_curve: List[float],
        trades: Optional[List[Dict]] = None,
        trading_days: int = 0
    ) -> RiskMetrics:
        """
        Calculate all risk metrics.
        
        Args:
            equity_curve: List of daily equity values
            trades: List of trades with P&L data
            trading_days: Number of trading days
            
        Returns:
            Complete RiskMetrics object
        """
        metrics = RiskMetrics()
        
        if len(equity_curve) < 2:
            return metrics
        
        # Calculate returns
        returns = self._calculate_returns(equity_curve)
        
        # Return metrics
        metrics.total_return_pct = self._total_return(equity_curve)
        metrics.annualized_return_pct = self._annualize_return(
            metrics.total_return_pct,
            len(equity_curve)
        )
        
        # Risk metrics
        metrics.volatility_pct = self._volatility(returns) * 100
        dd_result = self._max_drawdown(equity_curve)
        metrics.max_drawdown_pct = dd_result[0]
        metrics.max_drawdown_duration_days = dd_result[3]
        
        # Risk-adjusted metrics
        metrics.sharpe_ratio = self.calculate_sharpe_ratio(returns)
        metrics.sortino_ratio = self.calculate_sortino_ratio(returns)
        
        if metrics.max_drawdown_pct > 0:
            metrics.calmar_ratio = metrics.annualized_return_pct / metrics.max_drawdown_pct
        
        # Trade metrics
        if trades:
            self._calculate_trade_metrics(trades, metrics)
        
        metrics.trading_days = trading_days or len(equity_curve)
        
        return metrics
    
    def _calculate_returns(self, equity_curve: List[float]) -> List[float]:
        """Calculate daily percentage returns."""
        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] != 0:
                ret = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                returns.append(ret)
            else:
                returns.append(0)
        return returns
    
    def _total_return(self, equity_curve: List[float]) -> float:
        """Calculate total return percentage."""
        if len(equity_curve) < 2 or equity_curve[0] == 0:
            return 0
        return ((equity_curve[-1] - equity_curve[0]) / equity_curve[0]) * 100
    
    def _annualize_return(self, total_return_pct: float, days: int) -> float:
        """Annualize a return."""
        if days <= 0:
            return 0
        # Assume 252 trading days per year
        years = days / 252
        if years <= 0:
            return total_return_pct
        
        # Compound annual growth rate
        total_return = total_return_pct / 100 + 1
        if total_return <= 0:
            return -100
        
        cagr = (total_return ** (1 / years)) - 1
        return cagr * 100
    
    def _volatility(self, returns: List[float]) -> float:
        """Calculate volatility (standard deviation of returns)."""
        if len(returns) < 2:
            return 0
        
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        return math.sqrt(variance)
    
    def _downside_volatility(self, returns: List[float], target: float = 0) -> float:
        """Calculate downside volatility (only negative returns)."""
        downside_returns = [r for r in returns if r < target]
        
        if len(downside_returns) < 2:
            return 0
        
        mean = sum(downside_returns) / len(downside_returns)
        variance = sum((r - mean) ** 2 for r in downside_returns) / (len(downside_returns) - 1)
        return math.sqrt(variance)
    
    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe Ratio.
        
        Formula: (Mean Return - Risk Free Rate) / Std Dev of Returns
        Annualized: Sharpe * sqrt(periods_per_year)
        
        Interpretation:
        - < 1.0: Subpar
        - 1.0 - 2.0: Good
        - 2.0 - 3.0: Very good
        - > 3.0: Excellent
        """
        if len(returns) < 2:
            return 0
        
        mean_return = sum(returns) / len(returns)
        volatility = self._volatility(returns)
        
        if volatility == 0:
            return 0
        
        # Daily risk-free rate
        daily_rf = self._risk_free_rate / periods_per_year
        
        sharpe = (mean_return - daily_rf) / volatility
        
        # Annualize
        return sharpe * math.sqrt(periods_per_year)
    
    def calculate_sortino_ratio(
        self,
        returns: List[float],
        target_return: float = 0,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sortino Ratio.
        
        Like Sharpe but only penalizes downside volatility.
        Better for strategies that have occasional large gains.
        
        Formula: (Mean Return - Target) / Downside Deviation
        """
        if len(returns) < 2:
            return 0
        
        mean_return = sum(returns) / len(returns)
        downside_vol = self._downside_volatility(returns, target_return)
        
        if downside_vol == 0:
            return 0 if mean_return <= target_return else float('inf')
        
        daily_target = target_return / periods_per_year
        sortino = (mean_return - daily_target) / downside_vol
        
        # Annualize
        return sortino * math.sqrt(periods_per_year)
    
    def _max_drawdown(
        self,
        equity_curve: List[float]
    ) -> Tuple[float, int, int, int]:
        """
        Calculate maximum drawdown.
        
        Returns:
        - max_drawdown_pct: Percentage decline
        - start_index: Where drawdown started
        - end_index: Where drawdown ended
        - duration: Days in drawdown
        """
        if len(equity_curve) < 2:
            return (0.0, 0, 0, 0)
        
        peak = equity_curve[0]
        peak_idx = 0
        max_dd = 0.0
        max_dd_start = 0
        max_dd_end = 0
        
        current_dd_start = 0
        
        for i, value in enumerate(equity_curve):
            if value > peak:
                peak = value
                peak_idx = i
                current_dd_start = i
            else:
                if peak > 0:
                    dd = ((peak - value) / peak) * 100
                    if dd > max_dd:
                        max_dd = dd
                        max_dd_start = current_dd_start
                        max_dd_end = i
        
        duration = max_dd_end - max_dd_start
        
        return (max_dd, max_dd_start, max_dd_end, duration)
    
    def _calculate_trade_metrics(self, trades: List[Dict], metrics: RiskMetrics):
        """Calculate trade-level metrics."""
        if not trades:
            return
        
        wins = []
        losses = []
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        gross_profit = 0
        gross_loss = 0
        
        for trade in trades:
            pnl = trade.get("pnl", 0)
            pnl_pct = trade.get("pnl_pct", 0)
            
            if pnl > 0:
                wins.append(pnl_pct)
                gross_profit += pnl
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            elif pnl < 0:
                losses.append(abs(pnl_pct))
                gross_loss += abs(pnl)
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        metrics.total_trades = len(trades)
        metrics.winning_trades = len(wins)
        metrics.losing_trades = len(losses)
        
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
        
        if wins:
            metrics.avg_win_pct = sum(wins) / len(wins)
            metrics.largest_win_pct = max(wins)
        
        if losses:
            metrics.avg_loss_pct = sum(losses) / len(losses)
            metrics.largest_loss_pct = max(losses)
        
        metrics.consecutive_wins_max = max_consecutive_wins
        metrics.consecutive_losses_max = max_consecutive_losses
        
        # Profit factor
        if gross_loss > 0:
            metrics.profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            metrics.profit_factor = float('inf')
        
        # Expectancy: avg_win * win_rate - avg_loss * loss_rate
        win_rate_decimal = metrics.win_rate / 100
        loss_rate_decimal = 1 - win_rate_decimal
        metrics.expectancy = (
            (metrics.avg_win_pct * win_rate_decimal) -
            (metrics.avg_loss_pct * loss_rate_decimal)
        )
    
    def generate_report(self, metrics: RiskMetrics) -> str:
        """Generate formatted risk report for steward."""
        lines = [
            "📊 **RISK METRICS REPORT**",
            "=" * 40,
            "",
            "**📈 Returns**",
            f"  Total Return: {metrics.total_return_pct:+.2f}%",
            f"  Annualized Return: {metrics.annualized_return_pct:+.2f}%",
            "",
            "**⚠️ Risk**",
            f"  Volatility: {metrics.volatility_pct:.2f}%",
            f"  Max Drawdown: {metrics.max_drawdown_pct:.2f}%",
            f"  DD Duration: {metrics.max_drawdown_duration_days} days",
            "",
            "**📊 Risk-Adjusted**",
            f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f} ({metrics._interpret_sharpe()})",
            f"  Sortino Ratio: {metrics.sortino_ratio:.2f}",
            f"  Calmar Ratio: {metrics.calmar_ratio:.2f}",
            "",
            "**🎯 Trade Quality**",
            f"  Win Rate: {metrics.win_rate:.1f}%",
            f"  Profit Factor: {metrics.profit_factor:.2f}",
            f"  Expectancy: {metrics.expectancy:+.2f}%",
            "",
            "**📋 Summary**",
            f"  Trades: {metrics.total_trades} ({metrics.winning_trades}W / {metrics.losing_trades}L)",
            f"  Avg Win: {metrics.avg_win_pct:.2f}%",
            f"  Avg Loss: {metrics.avg_loss_pct:.2f}%",
            f"  Best Streak: {metrics.consecutive_wins_max} wins",
            f"  Worst Streak: {metrics.consecutive_losses_max} losses",
            "",
            "=" * 40,
            f"**{metrics._interpret_overall()}**"
        ]
        
        return "\n".join(lines)


# Singleton calculator
_calculator: Optional[RiskMetricsCalculator] = None


def get_risk_calculator() -> RiskMetricsCalculator:
    """Get or create global risk calculator."""
    global _calculator
    if _calculator is None:
        _calculator = RiskMetricsCalculator()
    return _calculator


def calculate_risk_metrics(
    equity_curve: List[float],
    trades: Optional[List[Dict]] = None
) -> RiskMetrics:
    """Calculate risk metrics from equity curve."""
    calc = get_risk_calculator()
    return calc.calculate_metrics(equity_curve, trades)


def generate_risk_report(metrics: RiskMetrics) -> str:
    """Generate formatted risk report."""
    calc = get_risk_calculator()
    return calc.generate_report(metrics)









