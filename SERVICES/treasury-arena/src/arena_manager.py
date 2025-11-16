"""
Arena Manager - Orchestrates agent competition, birth, death, and capital allocation

The Arena Manager is the core evolutionary engine that:
- Spawns new agents
- Tracks agent performance
- Allocates capital dynamically
- Kills underperformers
- Mutates successful strategies
"""

import random
import logging
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np

from .agent import TreasuryAgent, DeFiYieldFarmer, TacticalTrader

logger = logging.getLogger(__name__)


class ArenaManager:
    """Manages the treasury arena and all competing agents"""

    def __init__(self, total_capital: float = 373261):
        self.total_capital = total_capital
        self.stable_reserve = total_capital * 0.437  # 43.7% stable reserve
        self.arena_capital = total_capital * 0.536  # 53.6% active management
        self.proving_capital = total_capital * 0.027  # 2.7% proving grounds

        # Agent pools
        self.simulation_agents: List[TreasuryAgent] = []
        self.proving_agents: List[TreasuryAgent] = []
        self.active_agents: List[TreasuryAgent] = []
        self.dead_agents: List[TreasuryAgent] = []

        # Strategy registry
        self.strategy_classes = {
            'DeFi-Yield-Farmer': DeFiYieldFarmer,
            'Tactical-Trader': TacticalTrader,
            # More strategies added as we build them
        }

        # Performance tracking
        self.arena_history = []

        logger.info(f"Arena initialized with ${total_capital:,.0f} total capital")

    def spawn_agent(
        self,
        strategy_type: str,
        params: Optional[Dict] = None,
        virtual_capital: float = 10000
    ) -> TreasuryAgent:
        """
        Birth a new agent into the simulation layer.

        Args:
            strategy_type: Type of strategy (e.g., "DeFi-Yield-Farmer")
            params: Strategy parameters (None = use defaults)
            virtual_capital: Starting simulated capital

        Returns:
            The newly created agent
        """
        if strategy_type not in self.strategy_classes:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

        # Create agent instance
        agent_class = self.strategy_classes[strategy_type]
        agent = agent_class(params=params, virtual_capital=virtual_capital)

        # Add to simulation layer
        self.simulation_agents.append(agent)

        logger.info(f"Agent {agent.id} spawned: {strategy_type} with ${virtual_capital:,.0f} virtual capital")

        return agent

    def mutate_agent(self, parent_agent: TreasuryAgent) -> TreasuryAgent:
        """
        Create a mutated version of a successful agent.

        Mutation: ±20% variation in all numeric parameters

        Args:
            parent_agent: Agent to mutate

        Returns:
            New mutated agent
        """
        mutated_params = {}

        for key, value in parent_agent.params.items():
            if isinstance(value, (int, float)):
                # Mutate numeric values by ±20%
                mutation_factor = random.uniform(0.8, 1.2)
                mutated_params[key] = value * mutation_factor
            else:
                # Keep non-numeric values unchanged
                mutated_params[key] = value

        # Create mutated agent
        mutated_agent = self.spawn_agent(
            strategy_type=parent_agent.strategy,
            params=mutated_params
        )

        logger.info(f"Agent {mutated_agent.id} mutated from {parent_agent.id}")

        return mutated_agent

    def rank_agents(self, agents: List[TreasuryAgent]) -> List[TreasuryAgent]:
        """
        Rank agents by fitness score.

        Args:
            agents: List of agents to rank

        Returns:
            Sorted list (highest fitness first)
        """
        # Calculate fitness for all agents
        for agent in agents:
            agent.calculate_fitness()

        # Sort by fitness (descending)
        ranked = sorted(agents, key=lambda a: a.fitness_score, reverse=True)

        # Assign ranks
        for i, agent in enumerate(ranked):
            agent.rank = i + 1

        return ranked

    def allocate_capital(self) -> Dict[str, float]:
        """
        Dynamically allocate capital to active agents based on fitness.

        Allocation tiers:
        - Elite (top 20%): 60% of capital
        - Active (middle 30%): 30% of capital
        - Challengers (bottom 50%): 10% of capital

        Returns:
            Dictionary mapping agent ID to allocated capital

        Raises:
            ValueError: If total allocation exceeds available capital
        """
        # Rank all active agents
        ranked = self.rank_agents(self.active_agents)

        if not ranked:
            logger.warning("No active agents to allocate capital")
            return {}

        # Calculate tier sizes
        total_agents = len(ranked)
        elite_count = max(1, total_agents // 5)  # Top 20%
        active_count = max(1, total_agents * 3 // 10)  # Middle 30%

        # Split agents into tiers
        elite = ranked[:elite_count]
        active = ranked[elite_count:elite_count + active_count]
        challengers = ranked[elite_count + active_count:]

        # Calculate per-agent allocations
        elite_capital_per_agent = (self.arena_capital * 0.60) / len(elite) if elite else 0
        active_capital_per_agent = (self.arena_capital * 0.30) / len(active) if active else 0
        challenger_capital_per_agent = (self.arena_capital * 0.10) / len(challengers) if challengers else 0

        # ✅ FIX: Validate total allocation BEFORE assigning to agents
        total_allocated = (
            (len(elite) * elite_capital_per_agent) +
            (len(active) * active_capital_per_agent) +
            (len(challengers) * challenger_capital_per_agent)
        )

        if total_allocated > self.arena_capital:
            raise ValueError(
                f"Capital allocation overflow: "
                f"${total_allocated:,.2f} > ${self.arena_capital:,.2f} "
                f"(attempting to allocate {total_allocated / self.arena_capital:.1%} of available capital)"
            )

        # Only allocate after validation passes
        allocations = {}

        for agent in elite:
            agent.real_capital = elite_capital_per_agent
            agent.tier = "elite"
            allocations[agent.id] = elite_capital_per_agent

        for agent in active:
            agent.real_capital = active_capital_per_agent
            agent.tier = "active"
            allocations[agent.id] = active_capital_per_agent

        for agent in challengers:
            agent.real_capital = challenger_capital_per_agent
            agent.tier = "challenger"
            allocations[agent.id] = challenger_capital_per_agent

        logger.info(
            f"Capital allocated: {len(elite)} elite (${elite_capital_per_agent:,.0f} each), "
            f"{len(active)} active (${active_capital_per_agent:,.0f} each), "
            f"{len(challengers)} challengers (${challenger_capital_per_agent:,.0f} each) "
            f"| Total: ${total_allocated:,.2f} / ${self.arena_capital:,.2f} ({total_allocated / self.arena_capital:.1%})"
        )

        return allocations

    def check_graduations(self):
        """Check if any agents are ready to graduate to next level"""

        # Simulation → Proving Grounds
        ready_for_proving = [
            agent for agent in self.simulation_agents
            if (
                agent.fitness_score > 2.0 and
                agent.sharpe_ratio() > 1.5 and
                agent.win_rate() > 0.60 and
                agent.max_drawdown() > -0.20 and
                agent.age >= 30
            )
        ]

        for agent in ready_for_proving:
            self.graduate_to_proving(agent)

        # Proving → Main Arena
        ready_for_arena = [
            agent for agent in self.proving_agents
            if (
                agent.real_capital > agent.initial_real_capital and  # Profitable
                agent.fitness_score > 2.0 and
                agent.sharpe_ratio() > 1.5 and
                agent.age >= 30 and
                agent.max_drawdown() > -0.25
            )
        ]

        for agent in ready_for_arena:
            self.graduate_to_arena(agent)

    def graduate_to_proving(self, agent: TreasuryAgent):
        """
        Graduate agent from simulation to proving grounds.

        Args:
            agent: Agent to graduate
        """
        # Remove from simulation
        self.simulation_agents.remove(agent)

        # Allocate $1K real capital
        agent.real_capital = 1000
        agent.initial_real_capital = 1000
        agent.status = "proving"

        # Add to proving grounds
        self.proving_agents.append(agent)

        logger.info(f"Agent {agent.id} graduated to proving grounds with $1,000 real capital")

    def graduate_to_arena(self, agent: TreasuryAgent):
        """
        Graduate agent from proving grounds to main arena.

        Args:
            agent: Agent to graduate
        """
        # Remove from proving
        self.proving_agents.remove(agent)

        # Allocate initial arena capital ($5K-$20K based on performance)
        performance_multiplier = min(20, max(5, agent.total_return() * 100))
        agent.real_capital = performance_multiplier * 1000
        agent.initial_real_capital = agent.real_capital
        agent.status = "active"

        # Add to main arena
        self.active_agents.append(agent)

        logger.info(f"Agent {agent.id} graduated to main arena with ${agent.real_capital:,.0f} capital")

    def kill_underperformers(self) -> List[TreasuryAgent]:
        """
        Terminate agents that fail to meet standards.

        Kill conditions:
        - Fitness < 0 for 30+ days
        - Max drawdown > 50%
        - Negative returns for 90+ days
        - Sharpe ratio < 0.5 for 60+ days
        - Age > 365 days (retirement)

        Returns:
            List of killed agents
        """
        killed = []

        # Check simulation agents
        for agent in self.simulation_agents[:]:
            if self._should_kill(agent):
                self.simulation_agents.remove(agent)
                agent.status = "dead"
                self.dead_agents.append(agent)
                killed.append(agent)
                logger.info(f"Killed simulation agent {agent.id}: fitness={agent.fitness_score:.2f}")

                # Spawn replacement
                self.spawn_agent(agent.strategy)

        # Check proving agents
        for agent in self.proving_agents[:]:
            if self._should_kill(agent):
                self.proving_agents.remove(agent)
                agent.status = "dead"
                self.dead_agents.append(agent)
                killed.append(agent)
                logger.info(f"Killed proving agent {agent.id}: fitness={agent.fitness_score:.2f}")

        # Check active agents
        for agent in self.active_agents[:]:
            if self._should_kill(agent):
                self.active_agents.remove(agent)
                agent.status = "dead"
                self.dead_agents.append(agent)
                killed.append(agent)
                logger.info(f"Killed active agent {agent.id}: fitness={agent.fitness_score:.2f}")

        return killed

    def _should_kill(self, agent: TreasuryAgent) -> bool:
        """Determine if agent should be killed"""
        return (
            # Negative fitness for 30 days
            (agent.fitness_score < 0 and agent.days_negative >= 30) or

            # Catastrophic drawdown
            (agent.max_drawdown() < -0.50) or

            # Negative returns for 90 days
            (agent.total_return() < 0 and agent.age >= 90) or

            # Low Sharpe ratio
            (agent.sharpe_ratio() < 0.5 and agent.age >= 60) or

            # Retirement age
            (agent.age > 365)
        )

    def run_evolution_cycle(self):
        """
        Run one cycle of evolution:
        1. Check graduations
        2. Allocate capital
        3. Kill underperformers
        4. Spawn new agents
        5. Mutate top performers
        """
        logger.info("Starting evolution cycle")

        # 1. Check graduations
        self.check_graduations()

        # 2. Allocate capital
        self.allocate_capital()

        # 3. Kill underperformers
        killed = self.kill_underperformers()

        # 4. Spawn new random agents (every 7 days)
        if datetime.now().day % 7 == 0:
            for _ in range(5):
                strategy = random.choice(list(self.strategy_classes.keys()))
                self.spawn_agent(strategy)

        # 5. Mutate top performers
        top_performers = self.rank_agents(self.active_agents)[:3]  # Top 3
        for agent in top_performers:
            self.mutate_agent(agent)

        logger.info(f"Evolution cycle complete: {len(killed)} agents killed, "
                   f"{len(self.active_agents)} active, "
                   f"{len(self.proving_agents)} proving, "
                   f"{len(self.simulation_agents)} simulating")

    def safe_run_evolution(self) -> tuple[bool, Optional[Exception]]:
        """
        Run evolution cycle with error isolation.

        Wraps run_evolution_cycle() in try/except to prevent system failure.

        Returns:
            Tuple of (success, error). If successful, error is None.
        """
        try:
            self.run_evolution_cycle()
            return True, None
        except Exception as e:
            logger.error(f"Evolution cycle failed: {str(e)}", exc_info=True)
            return False, e

    def get_arena_stats(self) -> Dict:
        """Get current arena statistics"""

        active_ranked = self.rank_agents(self.active_agents)

        # Calculate arena performance
        total_capital_active = sum(a.real_capital for a in self.active_agents)
        total_initial_active = sum(a.initial_real_capital for a in self.active_agents)
        arena_return = ((total_capital_active - total_initial_active) / total_initial_active) if total_initial_active > 0 else 0

        # Calculate arena Sharpe
        if self.active_agents:
            arena_sharpe = np.mean([a.sharpe_ratio() for a in self.active_agents])
        else:
            arena_sharpe = 0

        return {
            'total_capital': self.total_capital,
            'stable_reserve': self.stable_reserve,
            'arena_capital': self.arena_capital,
            'proving_capital': self.proving_capital,
            'agents_active': len(self.active_agents),
            'agents_proving': len(self.proving_agents),
            'agents_simulating': len(self.simulation_agents),
            'agents_dead': len(self.dead_agents),
            'arena_return': arena_return,
            'arena_sharpe': arena_sharpe,
            'top_performers': [a.to_dict() for a in active_ranked[:5]],
            'ready_for_proving': len([a for a in self.simulation_agents if a.fitness_score > 2.0])
        }

    def get_all_agents(self) -> List[Dict]:
        """Get all agents across all pools"""
        all_agents = (
            self.simulation_agents +
            self.proving_agents +
            self.active_agents
        )

        ranked = self.rank_agents(all_agents)

        return [a.to_dict() for a in ranked]
