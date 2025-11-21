"""
Treasury Agent - Autonomous trading strategy executor

Each agent represents a specific trading strategy competing for capital in the arena.
Agents track performance, calculate fitness scores, and execute strategies.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np


class TreasuryAgent:
    """Base class for all treasury agents competing in the arena"""

    def __init__(
        self,
        strategy_type: str,
        params: Dict[str, Any],
        virtual_capital: float = 10000,
        real_capital: float = 0,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        avatar: Optional[str] = None,
        personality: Optional[Dict[str, Any]] = None
    ):
        self.id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self.strategy = strategy_type
        self.params = params

        # Personality traits
        self.name = name or f"Agent-{self.id[:8]}"
        self.avatar = avatar or "🤖"
        self.personality = personality or {
            'risk_tolerance': 'moderate',
            'aggression': 'balanced',
            'description': 'A treasury agent'
        }

        # Capital tracking
        self.virtual_capital = virtual_capital
        self.initial_virtual_capital = virtual_capital
        self.real_capital = real_capital
        self.initial_real_capital = real_capital

        # Performance tracking
        self.performance_history: List[Dict] = []
        self.fitness_score = 0.0
        self.age = 0  # Days alive
        self.days_negative = 0

        # Status: simulation, proving, active, retired, dead
        self.status = "simulation"

        # Tier: None, challenger, active, elite
        self.tier = None

        # Rank among all agents
        self.rank = 0

        # Creation timestamp
        self.created_at = datetime.now()
        self.last_updated = datetime.now()

    def execute_strategy(self, market_data: Dict) -> List[Dict]:
        """
        Execute the agent's trading strategy based on market data.

        Args:
            market_data: Current market conditions (prices, volumes, indicators)

        Returns:
            List of trades to execute
        """
        # This is a base implementation - subclasses override this
        raise NotImplementedError("Subclasses must implement execute_strategy")

    def safe_execute(self, market_data: Dict) -> tuple[List[Dict], Optional[Exception]]:
        """
        Execute strategy with error isolation.

        Wraps execute_strategy() in try/except to prevent one agent crash from killing the system.

        Args:
            market_data: Market conditions

        Returns:
            Tuple of (trades, error). If successful, error is None. If failed, trades is [].
        """
        try:
            trades = self.execute_strategy(market_data)
            return trades, None
        except Exception as e:
            # Log error but don't propagate
            print(f"ERROR: Agent {self.id} ({self.strategy}) crashed: {str(e)}")
            return [], e

    def validate_capital_change(self, old_capital: float, new_capital: float) -> bool:
        """
        Validate that a capital change is legal.

        Prevents:
        - Negative capital
        - Suspiciously large increases (>10x in one period)

        Args:
            old_capital: Previous capital amount
            new_capital: Proposed new capital amount

        Returns:
            True if valid

        Raises:
            ValueError: If capital change is invalid
        """
        if new_capital < 0:
            raise ValueError(f"Capital cannot be negative: ${new_capital:,.2f}")

        if old_capital > 0 and new_capital > old_capital * 10:
            raise ValueError(
                f"Capital increase too large: ${old_capital:,.2f} → ${new_capital:,.2f} "
                f"({new_capital / old_capital:.1f}x increase exceeds 10x limit)"
            )

        return True

    def calculate_fitness(self) -> float:
        """
        Calculate multi-factor fitness score.

        Fitness = (Returns * 0.3) + (Sharpe * 0.4) - (Drawdown * 0.2) - (Volatility * 0.1) + Consistency Bonus

        Returns:
            Fitness score (higher is better, typically 0-3 range)
        """
        if len(self.performance_history) < 7:
            # Need at least 7 days of data
            return 0.0

        # Returns component (30%)
        total_return = self.total_return()
        returns_score = total_return * 0.3

        # Sharpe Ratio component (40%)
        sharpe = self.sharpe_ratio()
        sharpe_score = sharpe * 0.4

        # Max Drawdown penalty (20%)
        drawdown = abs(self.max_drawdown())
        drawdown_penalty = drawdown * 0.2

        # Volatility penalty (10%)
        volatility = self.volatility()
        volatility_penalty = volatility * 0.1

        # Consistency bonus (win rate > 65%)
        win_rate = self.win_rate()
        consistency_bonus = 0.1 if win_rate > 0.65 else 0

        # Calculate final fitness
        fitness = returns_score + sharpe_score - drawdown_penalty - volatility_penalty + consistency_bonus

        self.fitness_score = fitness
        return fitness

    def sharpe_ratio(self) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted returns).

        Returns:
            Sharpe ratio (typically -1 to 4, >1.5 is good)
        """
        if len(self.performance_history) < 2:
            return 0.0

        returns = np.array([day['pnl'] / day.get('capital', 1) for day in self.performance_history])

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe (assuming daily returns)
        sharpe = (mean_return / std_return) * np.sqrt(365)

        return sharpe

    def max_drawdown(self) -> float:
        """
        Calculate maximum peak-to-trough decline.

        Returns:
            Max drawdown as negative percentage (e.g., -0.20 = -20%)
        """
        if len(self.performance_history) < 2:
            return 0.0

        capital_curve = [day['capital'] for day in self.performance_history]
        peak = capital_curve[0]
        max_dd = 0.0

        for value in capital_curve:
            if value > peak:
                peak = value
            dd = (value - peak) / peak if peak > 0 else 0
            max_dd = min(max_dd, dd)

        return max_dd

    def volatility(self) -> float:
        """
        Calculate volatility (standard deviation of returns).

        Returns:
            Annualized volatility
        """
        if len(self.performance_history) < 2:
            return 0.0

        returns = np.array([day['pnl'] / day.get('capital', 1) for day in self.performance_history])

        # Annualized volatility
        volatility = np.std(returns) * np.sqrt(365)

        return volatility

    def win_rate(self) -> float:
        """
        Calculate percentage of profitable periods.

        Returns:
            Win rate as percentage (0.0 to 1.0)
        """
        if len(self.performance_history) == 0:
            return 0.0

        winning_days = sum(1 for day in self.performance_history if day['pnl'] > 0)

        return winning_days / len(self.performance_history)

    def total_return(self) -> float:
        """
        Calculate total return since inception.

        Returns:
            Total return as percentage (e.g., 0.25 = 25%)
        """
        if self.status == "simulation":
            if self.initial_virtual_capital == 0:
                return 0.0
            return (self.virtual_capital - self.initial_virtual_capital) / self.initial_virtual_capital
        else:
            if self.initial_real_capital == 0:
                return 0.0
            return (self.real_capital - self.initial_real_capital) / self.initial_real_capital

    def annualized_return(self) -> float:
        """
        Calculate annualized return.

        Returns:
            Annualized return as percentage
        """
        if self.age == 0:
            return 0.0

        total_return = self.total_return()
        years = self.age / 365

        if years == 0:
            return total_return

        # Compound annual growth rate
        cagr = (1 + total_return) ** (1 / years) - 1

        return cagr

    def record_performance(self, capital: float, pnl: float, trades: List[Dict]):
        """
        Record daily performance.

        Args:
            capital: Current capital after trades
            pnl: Profit/loss for the period
            trades: List of trades executed
        """
        # ✅ FIX: Calculate fitness FIRST, then record it (not before)
        new_fitness = self.calculate_fitness()

        self.performance_history.append({
            'date': datetime.now(),
            'capital': capital,
            'pnl': pnl,
            'trades': trades,
            'fitness': new_fitness  # ✅ Use newly calculated fitness
        })

        # Update days negative counter
        if pnl < 0:
            self.days_negative += 1
        else:
            self.days_negative = 0

        # Update age
        self.age += 1
        self.last_updated = datetime.now()

    def get_current_capital(self) -> float:
        """Get current capital based on status"""
        return self.real_capital if self.status in ["proving", "active"] else self.virtual_capital

    def to_dict(self) -> Dict:
        """Convert agent to dictionary for API/storage"""
        return {
            'id': self.id,
            'name': self.name,
            'avatar': self.avatar,
            'personality': self.personality,
            'strategy': self.strategy,
            'status': self.status,
            'tier': self.tier,
            'virtual_capital': self.virtual_capital,
            'real_capital': self.real_capital,
            'fitness_score': self.fitness_score,
            'sharpe_ratio': self.sharpe_ratio(),
            'max_drawdown': self.max_drawdown(),
            'win_rate': self.win_rate(),
            'total_return': self.total_return(),
            'annualized_return': self.annualized_return(),
            'volatility': self.volatility(),
            'age_days': self.age,
            'rank': self.rank,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'params': self.params
        }

    def __repr__(self):
        return f"<TreasuryAgent {self.id} ({self.strategy}) - ${self.get_current_capital():,.0f} - Fitness: {self.fitness_score:.2f}>"


# Example strategy implementations

class DeFiYieldFarmer(TreasuryAgent):
    """DeFi yield farming strategy - hunts stable yields"""

    def __init__(self, params: Optional[Dict] = None, **kwargs):
        default_params = {
            'target_apy': 0.08,  # 8% minimum APY
            'rebalance_threshold': 0.02,  # Rebalance if APY difference > 2%
            'protocols': ['aave', 'pendle', 'curve'],
            'max_protocol_allocation': 0.4  # Max 40% in single protocol
        }
        params = {**default_params, **(params or {})}
        super().__init__(strategy_type="DeFi-Yield-Farmer", params=params, **kwargs)

    def execute_strategy(self, market_data: Dict) -> List[Dict]:
        """Execute DeFi yield farming strategy"""
        trades = []

        # Get current APYs for all protocols
        protocol_apys = market_data.get('protocol_apys', {})

        # Find highest APY protocol
        best_protocol = max(protocol_apys.items(), key=lambda x: x[1]) if protocol_apys else (None, 0)

        # Check if rebalance needed
        current_protocol = market_data.get('current_allocation', {}).get('protocol')
        current_apy = protocol_apys.get(current_protocol, 0)

        if best_protocol[0] and (best_protocol[1] - current_apy) > self.params['rebalance_threshold']:
            # Rebalance to best protocol
            trades.append({
                'action': 'rebalance',
                'from_protocol': current_protocol,
                'to_protocol': best_protocol[0],
                'amount': self.get_current_capital(),
                'expected_apy': best_protocol[1]
            })

        return trades


class TacticalTrader(TreasuryAgent):
    """Cycle-aware BTC/SOL trading based on MVRV and indicators"""

    def __init__(self, params: Optional[Dict] = None, **kwargs):
        default_params = {
            'mvrv_buy_threshold': 2.0,  # Buy when MVRV < 2.0
            'mvrv_sell_threshold': 3.5,  # Sell when MVRV > 3.5
            'position_size': 0.25,  # 25% of capital per trade
            'max_leverage': 2.0,  # Max 2x leverage
            'assets': ['BTC', 'SOL']
        }
        params = {**default_params, **(params or {})}
        super().__init__(strategy_type="Tactical-Trader", params=params, **kwargs)

    def execute_strategy(self, market_data: Dict) -> List[Dict]:
        """Execute tactical trading strategy"""
        trades = []

        # Get MVRV for BTC
        mvrv = market_data.get('indicators', {}).get('btc_mvrv', 2.5)

        current_position = market_data.get('current_position', {})

        # Buy signal: MVRV < 2.0 and not in position
        if mvrv < self.params['mvrv_buy_threshold'] and not current_position:
            position_size = self.get_current_capital() * self.params['position_size']
            trades.append({
                'action': 'buy',
                'asset': 'BTC',
                'amount': position_size,
                'leverage': self.params['max_leverage'],
                'reason': f'MVRV {mvrv:.2f} < {self.params["mvrv_buy_threshold"]}'
            })

        # Sell signal: MVRV > 3.5 and in position
        elif mvrv > self.params['mvrv_sell_threshold'] and current_position:
            trades.append({
                'action': 'sell',
                'asset': 'BTC',
                'amount': current_position.get('amount', 0),
                'reason': f'MVRV {mvrv:.2f} > {self.params["mvrv_sell_threshold"]}'
            })

        return trades
