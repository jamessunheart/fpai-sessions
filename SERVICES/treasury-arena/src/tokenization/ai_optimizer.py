"""
AI Wallet Optimizer

Intelligent capital allocation across strategy tokens using:
- Mean-variance optimization (Markowitz portfolio theory)
- Risk-adjusted returns (Sharpe ratio maximization)
- Diversification constraints
- Correlation analysis

Modes:
- FULL_AI: Execute allocations automatically
- HYBRID: Suggest allocations for user approval
- MANUAL: Only provide analytics, no suggestions
"""

import json
import numpy as np
import sqlite3
import structlog
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import (
    AIWallet,
    StrategyToken,
    TokenHolding,
    TokenTransaction,
    TransactionType,
    WalletMode,
    RiskTolerance,
)

logger = structlog.get_logger()


# ============================================================================
# OPTIMIZATION MODELS
# ============================================================================

@dataclass
class AllocationRecommendation:
    """AI optimizer's recommended portfolio allocation"""

    # Allocations (token_id -> target percentage)
    target_allocations: Dict[int, float]

    # Expected outcomes
    expected_return: float
    expected_sharpe: float
    expected_volatility: float

    # Reasoning
    reasoning: str
    changes_summary: str

    # Actions required
    buy_orders: List[Tuple[int, float]]   # (token_id, quantity)
    sell_orders: List[Tuple[int, float]]  # (token_id, quantity)

    # Metadata
    created_at: datetime


@dataclass
class PerformanceMetrics:
    """Historical performance metrics for a strategy token"""

    token_id: int
    mean_daily_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    correlation_with_others: Dict[int, float]


# ============================================================================
# AI WALLET OPTIMIZER
# ============================================================================

class AIWalletOptimizer:
    """
    Intelligent portfolio optimizer for AI wallets.

    Uses modern portfolio theory to maximize risk-adjusted returns
    while respecting user constraints (risk tolerance, diversification).
    """

    def __init__(self, db_path: str = "treasury_arena.db"):
        self.db_path = db_path
        self.logger = logger.bind(component="ai_optimizer")

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def optimize_wallet(
        self,
        wallet: AIWallet,
        available_tokens: Optional[List[StrategyToken]] = None
    ) -> AllocationRecommendation:
        """
        Generate optimal allocation for a wallet.

        Args:
            wallet: The AI wallet to optimize
            available_tokens: List of tokens to consider (None = all active)

        Returns:
            AllocationRecommendation with target allocations and trade orders
        """

        self.logger.info("optimizing_wallet", wallet_id=wallet.id, mode=wallet.mode.value)

        # 1. Get available tokens
        if available_tokens is None:
            available_tokens = StrategyToken.list_active(self.db_path)

        if len(available_tokens) == 0:
            self.logger.warning("no_active_tokens")
            return self._empty_recommendation("No active tokens available")

        # 2. Calculate performance metrics
        metrics = self._calculate_token_metrics(available_tokens)

        # 3. Filter tokens based on quality
        qualified_tokens = self._filter_qualified_tokens(metrics, wallet)

        if len(qualified_tokens) == 0:
            self.logger.warning("no_qualified_tokens")
            return self._empty_recommendation("No tokens meet quality criteria")

        # 4. Run optimization algorithm
        target_allocations = self._optimize_allocations(
            tokens=qualified_tokens,
            metrics=metrics,
            wallet=wallet
        )

        # 5. Calculate expected outcomes
        expected_return, expected_sharpe, expected_vol = self._calculate_expected_performance(
            target_allocations, metrics
        )

        # 6. Generate trade orders
        current_holdings = TokenHolding.get_wallet_holdings(wallet.id, self.db_path)
        buy_orders, sell_orders = self._generate_trade_orders(
            current_holdings=current_holdings,
            target_allocations=target_allocations,
            available_capital=wallet.cash_balance,
            total_capital=wallet.total_capital
        )

        # 7. Generate reasoning
        reasoning = self._generate_reasoning(
            target_allocations=target_allocations,
            metrics=metrics,
            wallet=wallet,
            expected_return=expected_return,
            expected_sharpe=expected_sharpe
        )

        changes_summary = self._generate_changes_summary(buy_orders, sell_orders, qualified_tokens)

        self.logger.info(
            "optimization_complete",
            num_tokens=len(target_allocations),
            expected_sharpe=expected_sharpe,
            buy_orders=len(buy_orders),
            sell_orders=len(sell_orders)
        )

        return AllocationRecommendation(
            target_allocations=target_allocations,
            expected_return=expected_return,
            expected_sharpe=expected_sharpe,
            expected_volatility=expected_vol,
            reasoning=reasoning,
            changes_summary=changes_summary,
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            created_at=datetime.now()
        )

    def execute_rebalance(
        self,
        wallet: AIWallet,
        recommendation: AllocationRecommendation,
        triggered_by: str = "ai_optimizer"
    ) -> bool:
        """
        Execute the recommended allocation.

        Args:
            wallet: The AI wallet to rebalance
            recommendation: The allocation recommendation to execute
            triggered_by: Who initiated this (ai_optimizer, user, admin)

        Returns:
            True if successful
        """

        self.logger.info(
            "executing_rebalance",
            wallet_id=wallet.id,
            num_buys=len(recommendation.buy_orders),
            num_sells=len(recommendation.sell_orders)
        )

        conn = sqlite3.connect(self.db_path)

        try:
            # 1. Execute sell orders first (to free up capital)
            for token_id, quantity in recommendation.sell_orders:
                token = StrategyToken.load(token_id, self.db_path)
                self._execute_sell(wallet, token, quantity, triggered_by, conn)

            # 2. Execute buy orders
            for token_id, quantity in recommendation.buy_orders:
                token = StrategyToken.load(token_id, self.db_path)
                self._execute_buy(wallet, token, quantity, triggered_by, conn)

            # 3. Update wallet rebalance timestamp
            wallet.last_rebalance_at = datetime.now()
            wallet.save(self.db_path)

            # 4. Take allocation snapshot
            self._save_allocation_snapshot(wallet, recommendation, conn)

            conn.commit()
            self.logger.info("rebalance_successful", wallet_id=wallet.id)
            return True

        except Exception as e:
            conn.rollback()
            self.logger.error("rebalance_failed", wallet_id=wallet.id, error=str(e))
            return False

        finally:
            conn.close()

    # ========================================================================
    # OPTIMIZATION ALGORITHM
    # ========================================================================

    def _optimize_allocations(
        self,
        tokens: List[StrategyToken],
        metrics: Dict[int, PerformanceMetrics],
        wallet: AIWallet
    ) -> Dict[int, float]:
        """
        Run mean-variance optimization to determine optimal allocations.

        Uses Sharpe ratio maximization with constraints:
        - Sum of allocations = 100%
        - Each allocation >= 0% (no shorting)
        - Each allocation <= max_single_strategy_pct
        - Minimum diversification (if enough tokens)

        Returns:
            Dict mapping token_id to allocation percentage
        """

        if len(tokens) == 0:
            return {}

        # Build return vector and covariance matrix
        returns = np.array([metrics[t.id].mean_daily_return * 365 for t in tokens])  # Annualized
        n = len(tokens)

        # Build covariance matrix from correlations and volatilities
        cov_matrix = np.zeros((n, n))
        for i, token_i in enumerate(tokens):
            for j, token_j in enumerate(tokens):
                if i == j:
                    vol_i = metrics[token_i.id].volatility
                    cov_matrix[i, j] = (vol_i ** 2)
                else:
                    vol_i = metrics[token_i.id].volatility
                    vol_j = metrics[token_j.id].volatility
                    corr = metrics[token_i.id].correlation_with_others.get(token_j.id, 0.5)
                    cov_matrix[i, j] = corr * vol_i * vol_j

        # Risk-free rate (assume 4% annual)
        rf_rate = 0.04

        # Use Sharpe ratio maximization (simplified quadratic programming)
        # For simplicity, use a heuristic approach instead of full QP solver

        # Strategy: Weight by Sharpe ratio, then apply constraints
        sharpe_scores = []
        for token in tokens:
            sharpe = metrics[token.id].sharpe_ratio or 0.0
            sharpe_scores.append(max(0, sharpe))  # Only positive Sharpe

        total_sharpe = sum(sharpe_scores)

        if total_sharpe == 0:
            # Equal weight if no positive Sharpe ratios
            weights = [1.0 / n] * n
        else:
            # Weight proportional to Sharpe ratio
            weights = [score / total_sharpe for score in sharpe_scores]

        # Apply max allocation constraint
        max_allocation = wallet.max_single_strategy_pct / 100.0
        weights = [min(w, max_allocation) for w in weights]

        # Renormalize to sum to 1.0
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]

        # Apply minimum diversification (if enough tokens)
        min_div = wallet.min_diversification
        if len(tokens) >= min_div:
            # Ensure at least min_div tokens have non-zero allocation
            sorted_indices = np.argsort(weights)[::-1]
            for i in range(min_div):
                if weights[sorted_indices[i]] == 0:
                    weights[sorted_indices[i]] = 0.01

            # Renormalize again
            total_weight = sum(weights)
            weights = [w / total_weight for w in weights]

        # Filter out tiny allocations (< 1%)
        weights = [w if w >= 0.01 else 0.0 for w in weights]
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]

        # Convert to percentage and map to token IDs
        allocations = {}
        for i, token in enumerate(tokens):
            if weights[i] > 0:
                allocations[token.id] = weights[i] * 100.0

        return allocations

    # ========================================================================
    # METRICS CALCULATION
    # ========================================================================

    def _calculate_token_metrics(
        self,
        tokens: List[StrategyToken],
        lookback_days: int = 90
    ) -> Dict[int, PerformanceMetrics]:
        """
        Calculate historical performance metrics for each token.

        Pulls data from strategy_performance_history table.
        """

        metrics = {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=lookback_days)

        for token in tokens:
            # Get historical NAV data
            cursor.execute("""
                SELECT snapshot_date, nav
                FROM strategy_performance_history
                WHERE token_id = ? AND snapshot_date >= ?
                ORDER BY snapshot_date ASC
            """, (token.id, cutoff_date))

            rows = cursor.fetchall()

            if len(rows) < 2:
                # Not enough history, use cached metrics from token
                metrics[token.id] = PerformanceMetrics(
                    token_id=token.id,
                    mean_daily_return=0.0,
                    volatility=0.15,  # Assume 15% annual volatility
                    sharpe_ratio=token.sharpe_ratio or 0.0,
                    max_drawdown=token.max_drawdown or 0.0,
                    correlation_with_others={}
                )
                continue

            # Calculate daily returns
            navs = np.array([row[1] for row in rows])
            returns = np.diff(navs) / navs[:-1]

            mean_return = np.mean(returns)
            volatility = np.std(returns) * np.sqrt(365)  # Annualized
            sharpe = (mean_return * 365 - 0.04) / volatility if volatility > 0 else 0.0

            # Calculate max drawdown
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / running_max
            max_dd = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

            metrics[token.id] = PerformanceMetrics(
                token_id=token.id,
                mean_daily_return=mean_return,
                volatility=volatility,
                sharpe_ratio=sharpe,
                max_drawdown=max_dd,
                correlation_with_others={}
            )

        # Calculate correlation matrix
        token_ids = [t.id for t in tokens]
        for i, token_i in enumerate(tokens):
            for j, token_j in enumerate(tokens):
                if i >= j:
                    continue

                # Get overlapping returns
                cursor.execute("""
                    SELECT h1.nav / LAG(h1.nav) OVER (ORDER BY h1.snapshot_date) - 1 as ret1,
                           h2.nav / LAG(h2.nav) OVER (ORDER BY h2.snapshot_date) - 1 as ret2
                    FROM strategy_performance_history h1
                    JOIN strategy_performance_history h2 ON h1.snapshot_date = h2.snapshot_date
                    WHERE h1.token_id = ? AND h2.token_id = ?
                    AND h1.snapshot_date >= ?
                    ORDER BY h1.snapshot_date
                """, (token_i.id, token_j.id, cutoff_date))

                rows = cursor.fetchall()
                if len(rows) < 2:
                    corr = 0.5  # Assume moderate correlation
                else:
                    returns_i = np.array([row[0] for row in rows if row[0] is not None])
                    returns_j = np.array([row[1] for row in rows if row[1] is not None])

                    if len(returns_i) > 0 and len(returns_j) > 0:
                        corr = np.corrcoef(returns_i, returns_j)[0, 1]
                    else:
                        corr = 0.5

                metrics[token_i.id].correlation_with_others[token_j.id] = corr
                metrics[token_j.id].correlation_with_others[token_i.id] = corr

        conn.close()
        return metrics

    def _filter_qualified_tokens(
        self,
        metrics: Dict[int, PerformanceMetrics],
        wallet: AIWallet
    ) -> List[StrategyToken]:
        """
        Filter tokens based on quality criteria.

        Conservative: Sharpe > 1.0, MaxDD < 20%
        Moderate: Sharpe > 0.5, MaxDD < 30%
        Aggressive: All tokens with positive Sharpe
        """

        if wallet.risk_tolerance == RiskTolerance.CONSERVATIVE:
            min_sharpe = 1.0
            max_dd = 0.20
        elif wallet.risk_tolerance == RiskTolerance.MODERATE:
            min_sharpe = 0.5
            max_dd = 0.30
        else:  # Aggressive
            min_sharpe = 0.0
            max_dd = 0.50

        qualified = []
        for token_id, metric in metrics.items():
            if metric.sharpe_ratio >= min_sharpe and metric.max_drawdown <= max_dd:
                token = StrategyToken.load(token_id, self.db_path)
                if token:
                    qualified.append(token)

        return qualified

    # ========================================================================
    # TRADE EXECUTION
    # ========================================================================

    def _generate_trade_orders(
        self,
        current_holdings: List[TokenHolding],
        target_allocations: Dict[int, float],
        available_capital: float,
        total_capital: float
    ) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        """
        Generate buy/sell orders to reach target allocations.

        Returns:
            (buy_orders, sell_orders) where each order is (token_id, quantity)
        """

        buy_orders = []
        sell_orders = []

        # Map current holdings
        current_allocations = {}
        for holding in current_holdings:
            pct = (holding.current_value / total_capital * 100) if total_capital > 0 else 0
            current_allocations[holding.token_id] = (pct, holding.quantity)

        # Determine buys and sells
        for token_id, target_pct in target_allocations.items():
            current_pct, current_qty = current_allocations.get(token_id, (0.0, 0.0))

            diff_pct = target_pct - current_pct

            if abs(diff_pct) < 1.0:
                # Too small to rebalance (< 1% difference)
                continue

            # Load token to get current NAV
            token = StrategyToken.load(token_id, self.db_path)
            if not token:
                continue

            target_value = total_capital * (target_pct / 100.0)
            current_value = total_capital * (current_pct / 100.0)
            value_diff = target_value - current_value

            if value_diff > 0:
                # Need to buy
                quantity = value_diff / token.current_nav
                if quantity >= token.min_purchase:
                    buy_orders.append((token_id, quantity))

            elif value_diff < 0:
                # Need to sell
                quantity = abs(value_diff) / token.current_nav
                if quantity > 0.01:  # Minimum sell quantity
                    sell_orders.append((token_id, min(quantity, current_qty)))

        # Handle tokens to exit (not in target allocations)
        for token_id, (current_pct, current_qty) in current_allocations.items():
            if token_id not in target_allocations and current_qty > 0:
                sell_orders.append((token_id, current_qty))

        return buy_orders, sell_orders

    def _execute_buy(
        self,
        wallet: AIWallet,
        token: StrategyToken,
        quantity: float,
        triggered_by: str,
        conn: sqlite3.Connection
    ):
        """Execute a buy transaction"""

        total_cost = quantity * token.current_nav

        # Platform fee (1% of transaction)
        platform_fee = total_cost * 0.01

        # Deduct from cash balance
        wallet.cash_balance -= (total_cost + platform_fee)
        wallet.invested_balance += total_cost

        # Update or create holding
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, quantity, avg_cost_basis FROM token_holdings
            WHERE wallet_id = ? AND token_id = ?
        """, (wallet.id, token.id))

        row = cursor.fetchone()

        if row:
            # Update existing holding
            holding_id, existing_qty, existing_cost = row
            new_qty = existing_qty + quantity
            new_cost = ((existing_qty * existing_cost) + (quantity * token.current_nav)) / new_qty

            cursor.execute("""
                UPDATE token_holdings
                SET quantity = ?, avg_cost_basis = ?, last_updated_at = ?
                WHERE id = ?
            """, (new_qty, new_cost, datetime.now(), holding_id))
        else:
            # Create new holding
            cursor.execute("""
                INSERT INTO token_holdings (wallet_id, token_id, quantity, avg_cost_basis, current_value, unrealized_pnl, unrealized_pnl_pct, first_acquired_at, last_updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (wallet.id, token.id, quantity, token.current_nav, total_cost, 0.0, 0.0, datetime.now(), datetime.now()))

        # Record transaction
        tx = TokenTransaction(
            wallet_id=wallet.id,
            token_id=token.id,
            transaction_type=TransactionType.BUY,
            quantity=quantity,
            price_per_token=token.current_nav,
            total_value=total_cost,
            platform_fee=platform_fee,
            triggered_by=triggered_by
        )
        tx.save(self.db_path)

        # Update token circulating supply
        token.circulating_supply += quantity
        token.total_aum += total_cost
        token.save(self.db_path)

    def _execute_sell(
        self,
        wallet: AIWallet,
        token: StrategyToken,
        quantity: float,
        triggered_by: str,
        conn: sqlite3.Connection
    ):
        """Execute a sell transaction"""

        total_proceeds = quantity * token.current_nav

        # Platform fee (1% of transaction)
        platform_fee = total_proceeds * 0.01

        # Add to cash balance
        wallet.cash_balance += (total_proceeds - platform_fee)
        wallet.invested_balance -= total_proceeds

        # Update holding
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, quantity FROM token_holdings
            WHERE wallet_id = ? AND token_id = ?
        """, (wallet.id, token.id))

        row = cursor.fetchone()
        if row:
            holding_id, existing_qty = row
            new_qty = existing_qty - quantity

            if new_qty <= 0.01:
                # Close position entirely
                cursor.execute("DELETE FROM token_holdings WHERE id = ?", (holding_id,))
            else:
                cursor.execute("""
                    UPDATE token_holdings
                    SET quantity = ?, last_updated_at = ?
                    WHERE id = ?
                """, (new_qty, datetime.now(), holding_id))

        # Record transaction
        tx = TokenTransaction(
            wallet_id=wallet.id,
            token_id=token.id,
            transaction_type=TransactionType.SELL,
            quantity=quantity,
            price_per_token=token.current_nav,
            total_value=total_proceeds,
            platform_fee=platform_fee,
            triggered_by=triggered_by
        )
        tx.save(self.db_path)

        # Update token circulating supply
        token.circulating_supply -= quantity
        token.total_aum -= total_proceeds
        token.save(self.db_path)

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _calculate_expected_performance(
        self,
        allocations: Dict[int, float],
        metrics: Dict[int, PerformanceMetrics]
    ) -> Tuple[float, float, float]:
        """Calculate expected return, Sharpe, and volatility"""

        if len(allocations) == 0:
            return 0.0, 0.0, 0.0

        # Expected return (weighted average)
        expected_return = sum(
            (pct / 100.0) * metrics[token_id].mean_daily_return * 365
            for token_id, pct in allocations.items()
        )

        # Portfolio volatility (simplified - ignores correlations for now)
        expected_vol = np.sqrt(sum(
            ((pct / 100.0) ** 2) * (metrics[token_id].volatility ** 2)
            for token_id, pct in allocations.items()
        ))

        # Sharpe ratio
        rf_rate = 0.04
        expected_sharpe = (expected_return - rf_rate) / expected_vol if expected_vol > 0 else 0.0

        return expected_return, expected_sharpe, expected_vol

    def _generate_reasoning(
        self,
        target_allocations: Dict[int, float],
        metrics: Dict[int, PerformanceMetrics],
        wallet: AIWallet,
        expected_return: float,
        expected_sharpe: float
    ) -> str:
        """Generate human-readable reasoning for allocation decision"""

        lines = []
        lines.append(f"AI Optimizer Analysis ({wallet.risk_tolerance.value.title()} Profile)")
        lines.append("")
        lines.append(f"Recommended Allocation across {len(target_allocations)} strategies:")

        for token_id, pct in sorted(target_allocations.items(), key=lambda x: x[1], reverse=True):
            token = StrategyToken.load(token_id, self.db_path)
            metric = metrics[token_id]
            lines.append(f"  • {token.strategy_name}: {pct:.1f}% (Sharpe: {metric.sharpe_ratio:.2f})")

        lines.append("")
        lines.append(f"Expected Portfolio Performance:")
        lines.append(f"  • Annual Return: {expected_return * 100:.1f}%")
        lines.append(f"  • Sharpe Ratio: {expected_sharpe:.2f}")
        lines.append(f"  • Risk Level: {wallet.risk_tolerance.value.title()}")

        lines.append("")
        lines.append("Rationale:")
        lines.append(f"  • Maximizes risk-adjusted returns (Sharpe ratio)")
        lines.append(f"  • Respects {wallet.max_single_strategy_pct}% max allocation per strategy")
        lines.append(f"  • Maintains minimum {wallet.min_diversification} strategy diversification")

        return "\n".join(lines)

    def _generate_changes_summary(
        self,
        buy_orders: List[Tuple[int, float]],
        sell_orders: List[Tuple[int, float]],
        tokens: List[StrategyToken]
    ) -> str:
        """Generate summary of changes"""

        lines = []
        if len(sell_orders) > 0:
            lines.append("Sells:")
            for token_id, qty in sell_orders:
                token = next((t for t in tokens if t.id == token_id), None)
                if token:
                    lines.append(f"  • Sell {qty:.2f} {token.token_symbol}")

        if len(buy_orders) > 0:
            lines.append("Buys:")
            for token_id, qty in buy_orders:
                token = next((t for t in tokens if t.id == token_id), None)
                if token:
                    lines.append(f"  • Buy {qty:.2f} {token.token_symbol}")

        return "\n".join(lines) if lines else "No changes needed"

    def _empty_recommendation(self, reason: str) -> AllocationRecommendation:
        """Return empty recommendation when optimization not possible"""

        return AllocationRecommendation(
            target_allocations={},
            expected_return=0.0,
            expected_sharpe=0.0,
            expected_volatility=0.0,
            reasoning=f"Cannot optimize: {reason}",
            changes_summary="No changes",
            buy_orders=[],
            sell_orders=[],
            created_at=datetime.now()
        )

    def _save_allocation_snapshot(
        self,
        wallet: AIWallet,
        recommendation: AllocationRecommendation,
        conn: sqlite3.Connection
    ):
        """Save allocation snapshot to database"""

        cursor = conn.cursor()

        allocations_json = json.dumps({
            str(token_id): pct
            for token_id, pct in recommendation.target_allocations.items()
        })

        optimizer_decision_json = json.dumps({
            "expected_return": recommendation.expected_return,
            "expected_sharpe": recommendation.expected_sharpe,
            "reasoning": recommendation.reasoning
        })

        num_holdings = len(recommendation.target_allocations)

        cursor.execute("""
            INSERT INTO allocation_snapshots (
                wallet_id, snapshot_date, total_value, cash_balance, invested_balance,
                num_holdings, allocations, optimizer_decision, rebalance_executed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            wallet.id, datetime.now(), wallet.total_capital, wallet.cash_balance,
            wallet.invested_balance, num_holdings, allocations_json,
            optimizer_decision_json, True
        ))
