"""
Simulation results container and analysis utilities

Stores simulation outputs, calculates performance metrics, and enables comparison.
"""

import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class AgentSnapshot:
    """Single agent state snapshot at a point in time"""
    date: str
    agent_id: str
    virtual_capital: float
    fitness_score: float
    sharpe_ratio: Optional[float] = None
    status: str = "simulation"
    tier: Optional[str] = None


@dataclass
class SimulationResults:
    """
    Complete results from a simulation run.

    Contains:
    - Run metadata (dates, config, agents)
    - Daily snapshots of all agents
    - Aggregate performance metrics
    - Export/comparison utilities
    """

    run_id: str
    start_date: str
    end_date: str
    initial_agents: int
    final_agents: int
    total_spawned: int
    total_killed: int
    initial_capital: float
    final_capital: float
    config: Dict

    # Performance metrics
    total_return: float = 0.0
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    avg_daily_return: Optional[float] = None
    volatility: Optional[float] = None

    # Daily snapshots
    snapshots: List[AgentSnapshot] = None

    # Timestamps
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    def __post_init__(self):
        if self.snapshots is None:
            self.snapshots = []

        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

        # Calculate derived metrics
        self.calculate_metrics()

    def add_snapshot(self, snapshot: AgentSnapshot):
        """Add a daily agent snapshot"""
        self.snapshots.append(snapshot)

    def calculate_metrics(self):
        """Calculate aggregate performance metrics from snapshots"""
        if not self.snapshots:
            return

        # Calculate total return
        if self.initial_capital > 0:
            self.total_return = ((self.final_capital - self.initial_capital) / self.initial_capital) * 100

        # Get daily portfolio values
        daily_values = self._get_daily_portfolio_values()

        if len(daily_values) > 1:
            # Calculate daily returns
            returns = []
            for i in range(1, len(daily_values)):
                if daily_values[i-1] > 0:
                    daily_return = (daily_values[i] - daily_values[i-1]) / daily_values[i-1]
                    returns.append(daily_return)

            if returns:
                # Average daily return
                self.avg_daily_return = np.mean(returns) * 100

                # Volatility (standard deviation of returns)
                self.volatility = np.std(returns) * 100

                # Sharpe ratio (annualized)
                if self.volatility > 0:
                    self.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(365)

                # Max drawdown
                peak = daily_values[0]
                max_dd = 0
                for value in daily_values:
                    if value > peak:
                        peak = value
                    dd = ((peak - value) / peak) * 100
                    if dd > max_dd:
                        max_dd = dd
                self.max_drawdown = max_dd

        logger.info(
            f"Calculated metrics",
            run_id=self.run_id,
            total_return=f"{self.total_return:.2f}%",
            sharpe=f"{self.sharpe_ratio:.2f}" if self.sharpe_ratio else "N/A"
        )

    def _get_daily_portfolio_values(self) -> List[float]:
        """Get total portfolio value for each day"""
        daily_totals = {}

        for snapshot in self.snapshots:
            date = snapshot.date
            if date not in daily_totals:
                daily_totals[date] = 0
            daily_totals[date] += snapshot.virtual_capital

        return [daily_totals[date] for date in sorted(daily_totals.keys())]

    def get_top_agents(self, n: int = 10) -> List[AgentSnapshot]:
        """Get top N agents by final fitness score"""
        if not self.snapshots:
            return []

        # Get latest snapshot for each agent
        latest_by_agent = {}
        for snapshot in self.snapshots:
            if snapshot.agent_id not in latest_by_agent:
                latest_by_agent[snapshot.agent_id] = snapshot
            elif snapshot.date > latest_by_agent[snapshot.agent_id].date:
                latest_by_agent[snapshot.agent_id] = snapshot

        # Sort by fitness score
        sorted_agents = sorted(
            latest_by_agent.values(),
            key=lambda x: x.fitness_score,
            reverse=True
        )

        return sorted_agents[:n]

    def get_agent_history(self, agent_id: str) -> List[AgentSnapshot]:
        """Get complete history for a specific agent"""
        return [s for s in self.snapshots if s.agent_id == agent_id]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            'run_id': self.run_id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_agents': self.initial_agents,
            'final_agents': self.final_agents,
            'total_spawned': self.total_spawned,
            'total_killed': self.total_killed,
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': self.total_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'avg_daily_return': self.avg_daily_return,
            'volatility': self.volatility,
            'config': self.config,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'snapshot_count': len(self.snapshots),
            'top_agents': [asdict(a) for a in self.get_top_agents(5)]
        }

    def to_json(self, filepath: str):
        """Export results to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

        logger.info(f"Exported results to JSON", filepath=filepath)

    def save_to_database(self, db_path: str = "simulation_data.db"):
        """Save results to SQLite database"""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Insert simulation run
            cursor.execute("""
                INSERT OR REPLACE INTO simulation_runs (
                    run_id, start_date, end_date,
                    initial_agents, final_agents,
                    total_spawned, total_killed,
                    initial_capital, final_capital,
                    total_return, sharpe_ratio, max_drawdown,
                    config, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.run_id, self.start_date, self.end_date,
                self.initial_agents, self.final_agents,
                self.total_spawned, self.total_killed,
                self.initial_capital, self.final_capital,
                self.total_return, self.sharpe_ratio, self.max_drawdown,
                json.dumps(self.config), self.created_at, self.completed_at
            ))

            # Insert snapshots
            for snapshot in self.snapshots:
                cursor.execute("""
                    INSERT OR REPLACE INTO simulation_snapshots (
                        run_id, date, agent_id,
                        virtual_capital, fitness_score, sharpe_ratio,
                        status, tier
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.run_id, snapshot.date, snapshot.agent_id,
                    snapshot.virtual_capital, snapshot.fitness_score, snapshot.sharpe_ratio,
                    snapshot.status, snapshot.tier
                ))

            conn.commit()

        logger.info(f"Saved results to database", run_id=self.run_id, snapshots=len(self.snapshots))

    @classmethod
    def load_from_database(cls, run_id: str, db_path: str = "simulation_data.db") -> Optional['SimulationResults']:
        """Load results from database"""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Load run metadata
            cursor.execute("""
                SELECT run_id, start_date, end_date,
                       initial_agents, final_agents,
                       total_spawned, total_killed,
                       initial_capital, final_capital,
                       total_return, sharpe_ratio, max_drawdown,
                       config, created_at, completed_at
                FROM simulation_runs
                WHERE run_id = ?
            """, (run_id,))

            row = cursor.fetchone()
            if not row:
                logger.warning(f"Run not found", run_id=run_id)
                return None

            config = json.loads(row[12]) if row[12] else {}

            results = cls(
                run_id=row[0],
                start_date=row[1],
                end_date=row[2],
                initial_agents=row[3],
                final_agents=row[4],
                total_spawned=row[5],
                total_killed=row[6],
                initial_capital=row[7],
                final_capital=row[8],
                total_return=row[9],
                sharpe_ratio=row[10],
                max_drawdown=row[11],
                config=config,
                created_at=row[13],
                completed_at=row[14]
            )

            # Load snapshots
            cursor.execute("""
                SELECT date, agent_id, virtual_capital,
                       fitness_score, sharpe_ratio, status, tier
                FROM simulation_snapshots
                WHERE run_id = ?
                ORDER BY date, agent_id
            """, (run_id,))

            results.snapshots = [
                AgentSnapshot(
                    date=row[0],
                    agent_id=row[1],
                    virtual_capital=row[2],
                    fitness_score=row[3],
                    sharpe_ratio=row[4],
                    status=row[5],
                    tier=row[6]
                )
                for row in cursor.fetchall()
            ]

            logger.info(f"Loaded results from database", run_id=run_id, snapshots=len(results.snapshots))
            return results


def compare_runs(run_ids: List[str], db_path: str = "simulation_data.db") -> Dict:
    """
    Compare multiple simulation runs.

    Returns:
        Dict with comparison metrics
    """
    runs = []
    for run_id in run_ids:
        result = SimulationResults.load_from_database(run_id, db_path)
        if result:
            runs.append(result)

    if not runs:
        return {'error': 'No valid runs found'}

    comparison = {
        'runs': [
            {
                'run_id': r.run_id,
                'total_return': r.total_return,
                'sharpe_ratio': r.sharpe_ratio,
                'max_drawdown': r.max_drawdown,
                'final_agents': r.final_agents,
                'final_capital': r.final_capital
            }
            for r in runs
        ],
        'best_return': max(runs, key=lambda r: r.total_return).run_id,
        'best_sharpe': max(runs, key=lambda r: r.sharpe_ratio or 0).run_id,
        'lowest_drawdown': min(runs, key=lambda r: r.max_drawdown or 100).run_id
    }

    return comparison


def get_all_runs(db_path: str = "simulation_data.db") -> List[Dict]:
    """Get summary of all simulation runs"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT run_id, start_date, end_date,
                   final_agents, total_return, sharpe_ratio,
                   completed_at
            FROM simulation_runs
            ORDER BY created_at DESC
        """)

        return [
            {
                'run_id': row[0],
                'start_date': row[1],
                'end_date': row[2],
                'final_agents': row[3],
                'total_return': row[4],
                'sharpe_ratio': row[5],
                'completed_at': row[6]
            }
            for row in cursor.fetchall()
        ]
