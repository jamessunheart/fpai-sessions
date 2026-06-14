#!/usr/bin/env python3
"""
🧪 STRATEGY TESTER
====================

High-level interface for testing trading strategies.

Features:
- Test different configurations quickly
- Grid search for optimal parameters
- Walk-forward analysis for robustness
"""

import logging
import itertools
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from .engine import BacktestEngine, BacktestConfig, BacktestResult, get_backtest_engine
from .data_manager import OHLCV

logger = logging.getLogger("aria.trading.backtest.tester")


def simple_momentum_strategy(
    symbol: str,
    candles: List[OHLCV],
    capital: float,
    config: BacktestConfig
) -> Optional[Dict]:
    """
    Simple momentum strategy for testing.
    
    Buy if price is above 20-period moving average.
    Sell if below.
    """
    if len(candles) < 20:
        return None
    
    # Get last 20 closes
    recent_closes = [c.close for c in candles[-20:]]
    ma20 = sum(recent_closes) / len(recent_closes)
    current_price = candles[-1].close
    
    # Calculate momentum
    if len(candles) >= 5:
        price_5_ago = candles[-5].close
        momentum = (current_price - price_5_ago) / price_5_ago * 100
    else:
        momentum = 0
    
    # Generate signal
    if current_price > ma20 and momentum > 0:
        confidence = min(100, 70 + abs(momentum) * 3)
        return {"action": "buy", "confidence": confidence}
    elif current_price < ma20 and momentum < 0:
        confidence = min(100, 70 + abs(momentum) * 3)
        return {"action": "sell", "confidence": confidence}
    
    return {"action": "hold", "confidence": 0}


class StrategyTester:
    """
    High-level interface for testing strategies.
    
    Allows testing different configurations quickly.
    """
    
    def __init__(self):
        self._engine = get_backtest_engine()
    
    async def test_configuration(
        self,
        symbols: List[str],
        min_confidence: float = 80.0,
        max_position_pct: float = 0.25,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 6.0,
        days: int = 90,
        initial_capital: float = 10000
    ) -> BacktestResult:
        """Test a specific configuration."""
        config = BacktestConfig(
            start_date=datetime.now() - timedelta(days=days),
            end_date=datetime.now(),
            initial_capital=initial_capital,
            symbols=symbols,
            min_confidence=min_confidence,
            max_position_pct=max_position_pct,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        
        return await self._engine.run_backtest(config, simple_momentum_strategy)
    
    async def optimize_parameters(
        self,
        symbols: List[str],
        param_ranges: Dict[str, List[float]],
        metric: str = "sharpe_ratio",
        days: int = 90,
        initial_capital: float = 10000
    ) -> Dict:
        """
        Grid search for optimal parameters.
        
        Args:
            symbols: Symbols to test
            param_ranges: Dict of parameter name -> list of values to test
                e.g., {"stop_loss_pct": [1, 2, 3], "take_profit_pct": [4, 6, 8]}
            metric: Metric to optimize (sharpe_ratio, total_return_pct, win_rate)
            days: Days of history to test
            initial_capital: Starting capital
            
        Returns:
            Best configuration and all results
        """
        logger.info(f"🔍 Starting parameter optimization...")
        
        # Generate all combinations
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        combinations = list(itertools.product(*param_values))
        
        logger.info(f"📊 Testing {len(combinations)} parameter combinations")
        
        results = []
        best_result = None
        best_metric_value = float('-inf')
        best_params = {}
        
        for i, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))
            
            config = BacktestConfig(
                start_date=datetime.now() - timedelta(days=days),
                end_date=datetime.now(),
                initial_capital=initial_capital,
                symbols=symbols,
                min_confidence=params.get("min_confidence", 80.0),
                max_position_pct=params.get("max_position_pct", 0.25),
                stop_loss_pct=params.get("stop_loss_pct", 2.0),
                take_profit_pct=params.get("take_profit_pct", 6.0)
            )
            
            result = await self._engine.run_backtest(config, simple_momentum_strategy)
            
            # Get metric value
            if metric == "sharpe_ratio" and result.risk_metrics:
                metric_value = result.risk_metrics.sharpe_ratio
            elif metric == "total_return_pct":
                metric_value = result.total_return_pct
            elif metric == "win_rate" and result.risk_metrics:
                metric_value = result.risk_metrics.win_rate
            elif metric == "profit_factor" and result.risk_metrics:
                metric_value = result.risk_metrics.profit_factor
            else:
                metric_value = result.total_return_pct
            
            results.append({
                "params": params,
                "metric_value": metric_value,
                "result": result.to_dict()
            })
            
            if metric_value > best_metric_value:
                best_metric_value = metric_value
                best_result = result
                best_params = params
            
            logger.info(f"  [{i+1}/{len(combinations)}] {params} -> {metric}: {metric_value:.2f}")
        
        logger.info(f"✅ Best: {best_params} -> {metric}: {best_metric_value:.2f}")
        
        return {
            "best_params": best_params,
            "best_metric_value": best_metric_value,
            "best_result": best_result.to_dict() if best_result else None,
            "all_results": results,
            "optimization_metric": metric
        }
    
    async def walk_forward_test(
        self,
        symbols: List[str],
        train_days: int = 60,
        test_days: int = 30,
        num_periods: int = 4,
        initial_capital: float = 10000
    ) -> Dict:
        """
        Walk-forward analysis for robustness.
        
        Trains on period 1, tests on period 2
        Trains on period 2, tests on period 3
        etc.
        
        Shows if strategy is overfit to specific period.
        
        Args:
            symbols: Symbols to test
            train_days: Days for training period
            test_days: Days for testing period
            num_periods: Number of walk-forward periods
            initial_capital: Starting capital
            
        Returns:
            Walk-forward results
        """
        logger.info(f"🚶 Starting walk-forward analysis with {num_periods} periods")
        
        total_days = (train_days + test_days) * num_periods
        end_date = datetime.now()
        start_date = end_date - timedelta(days=total_days)
        
        periods = []
        train_results = []
        test_results = []
        
        current_start = start_date
        
        for i in range(num_periods):
            train_start = current_start
            train_end = train_start + timedelta(days=train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=test_days)
            
            # Training phase
            train_config = BacktestConfig(
                start_date=train_start,
                end_date=train_end,
                initial_capital=initial_capital,
                symbols=symbols
            )
            train_result = await self._engine.run_backtest(train_config, simple_momentum_strategy)
            train_results.append(train_result)
            
            # Testing phase (using same parameters)
            test_config = BacktestConfig(
                start_date=test_start,
                end_date=test_end,
                initial_capital=initial_capital,
                symbols=symbols
            )
            test_result = await self._engine.run_backtest(test_config, simple_momentum_strategy)
            test_results.append(test_result)
            
            periods.append({
                "period": i + 1,
                "train": {
                    "start": train_start.isoformat(),
                    "end": train_end.isoformat(),
                    "return_pct": train_result.total_return_pct
                },
                "test": {
                    "start": test_start.isoformat(),
                    "end": test_end.isoformat(),
                    "return_pct": test_result.total_return_pct
                }
            })
            
            logger.info(
                f"  Period {i+1}: Train {train_result.total_return_pct:.2f}% "
                f"-> Test {test_result.total_return_pct:.2f}%"
            )
            
            current_start = test_end
        
        # Calculate consistency metrics
        train_returns = [r.total_return_pct for r in train_results]
        test_returns = [r.total_return_pct for r in test_results]
        
        avg_train = sum(train_returns) / len(train_returns) if train_returns else 0
        avg_test = sum(test_returns) / len(test_returns) if test_returns else 0
        
        # Correlation between train and test performance
        if len(train_returns) > 1:
            # Simple correlation calculation
            mean_train = avg_train
            mean_test = avg_test
            
            numerator = sum(
                (t - mean_train) * (s - mean_test) 
                for t, s in zip(train_returns, test_returns)
            )
            
            denom_train = sum((t - mean_train) ** 2 for t in train_returns) ** 0.5
            denom_test = sum((s - mean_test) ** 2 for s in test_returns) ** 0.5
            
            if denom_train > 0 and denom_test > 0:
                correlation = numerator / (denom_train * denom_test)
            else:
                correlation = 0
        else:
            correlation = 0
        
        # Overfit score: how much worse is test vs train?
        if avg_train > 0:
            overfit_score = (avg_train - avg_test) / avg_train * 100
        else:
            overfit_score = 0
        
        return {
            "periods": periods,
            "summary": {
                "avg_train_return": round(avg_train, 2),
                "avg_test_return": round(avg_test, 2),
                "train_test_correlation": round(correlation, 2),
                "overfit_score": round(overfit_score, 2),
                "is_robust": overfit_score < 50 and correlation > 0.3
            }
        }
    
    def generate_optimization_report(self, results: Dict) -> str:
        """Generate optimization report."""
        lines = [
            "🔍 **PARAMETER OPTIMIZATION REPORT**",
            "=" * 40,
            "",
            f"📊 Optimization Metric: {results['optimization_metric']}",
            "",
            "**🏆 Best Configuration**"
        ]
        
        for param, value in results['best_params'].items():
            lines.append(f"  {param}: {value}")
        
        lines.append(f"  {results['optimization_metric']}: {results['best_metric_value']:.2f}")
        
        return "\n".join(lines)


# Singleton
_tester: Optional[StrategyTester] = None


def get_strategy_tester() -> StrategyTester:
    """Get or create global strategy tester."""
    global _tester
    if _tester is None:
        _tester = StrategyTester()
    return _tester









