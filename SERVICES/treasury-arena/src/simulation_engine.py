"""
Core Simulation Engine for Treasury Arena

Enables backtesting and fast-forward simulation of treasury agents with:
- Time progression (1x to 1000x speed)
- Historical market data replay
- Agent evolution cycles
- Performance tracking
- Zero capital risk
"""

import asyncio
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import structlog

from .agent import TreasuryAgent
from .arena_manager import ArenaManager
from .data_sources import SimulationDataCache, fetch_and_cache_all_data
from .simulation_results import SimulationResults, AgentSnapshot

logger = structlog.get_logger()


class SimulationEngine:
    """
    Core simulation engine for backtesting treasury strategies.
    
    Features:
    - Replay historical market conditions
    - Fast-forward time (1x to 1000x)
    - Execute agent strategies in isolation
    - Track performance metrics
    - Save/resume simulations
    """
    
    def __init__(
        self,
        db_path: str = "simulation_data.db",
        time_multiplier: float = 1.0
    ):
        self.db_path = db_path
        self.time_multiplier = time_multiplier
        self.cache = SimulationDataCache(db_path)
        
        # Current simulation state
        self.current_date: Optional[datetime] = None
        self.arena_manager: Optional[ArenaManager] = None
        self.results: Optional[SimulationResults] = None
        
        # Configuration
        self.assets = ['BTC', 'SOL', 'ETH']
        self.protocols = ['aave', 'pendle', 'curve']
        
    async def backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_agents: int = 10,
        initial_capital: float = 10000,
        evolution_frequency: int = 7,  # days
        spawn_per_cycle: int = 3,
        kill_bottom_percent: float = 0.3
    ) -> SimulationResults:
        """
        Run a complete backtest simulation.
        
        Args:
            start_date: Simulation start
            end_date: Simulation end
            initial_agents: Number of agents to spawn initially
            initial_capital: Virtual capital per agent
            evolution_frequency: Days between evolution cycles
            spawn_per_cycle: New agents spawned each cycle
            kill_bottom_percent: Fraction of agents to kill
            
        Returns:
            SimulationResults object with complete results
        """
        run_id = f"backtest-{uuid.uuid4().hex[:8]}"
        
        logger.info(
            "Starting backtest",
            run_id=run_id,
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            days=(end_date - start_date).days
        )
        
        # Ensure data is cached
        logger.info("Fetching/caching market data...")
        await fetch_and_cache_all_data(
            self.assets,
            self.protocols,
            start_date,
            end_date,
            self.db_path
        )
        
        # Initialize arena and agents
        self.arena_manager = ArenaManager(total_capital=initial_capital * initial_agents)
        
        # Spawn initial agents
        for i in range(initial_agents):
            strategy = 'DeFi-Yield-Farmer' if i % 2 == 0 else 'Tactical-Trader'
            self.arena_manager.spawn_agent(strategy, virtual_capital=initial_capital)
        
        # Initialize results
        self.results = SimulationResults(
            run_id=run_id,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            initial_agents=initial_agents,
            final_agents=initial_agents,
            total_spawned=initial_agents,
            total_killed=0,
            initial_capital=initial_capital * initial_agents,
            final_capital=0,
            config={
                'evolution_frequency': evolution_frequency,
                'spawn_per_cycle': spawn_per_cycle,
                'kill_bottom_percent': kill_bottom_percent,
                'time_multiplier': self.time_multiplier
            }
        )
        
        # Main simulation loop
        self.current_date = start_date
        days_simulated = 0
        
        while self.current_date <= end_date:
            date_str = self.current_date.strftime('%Y-%m-%d')
            
            # Get market data for this day
            market_data = self._get_market_data_for_date(date_str)
            
            # Execute all agent strategies
            await self._execute_agents_for_day(market_data)
            
            # Take snapshot of all agents
            self._take_snapshots(date_str)
            
            # Evolution cycle check
            if days_simulated % evolution_frequency == 0 and days_simulated > 0:
                self._run_evolution_cycle(spawn_per_cycle, kill_bottom_percent)
            
            # Progress to next day
            self.current_date += timedelta(days=1)
            days_simulated += 1
            
            if days_simulated % 10 == 0:
                logger.info(
                    "Simulation progress",
                    date=date_str,
                    days=days_simulated,
                    agents=len(self.arena_manager.simulation_agents)
                )
        
        # Finalize results
        self.results.final_agents = len(self.arena_manager.simulation_agents)
        self.results.final_capital = sum(a.virtual_capital for a in self.arena_manager.simulation_agents)
        self.results.completed_at = datetime.now().isoformat()
        self.results.calculate_metrics()
        
        # Save to database
        self.results.save_to_database(self.db_path)
        
        logger.info(
            "Backtest complete",
            run_id=run_id,
            total_return=f"{self.results.total_return:.2f}%",
            final_capital=self.results.final_capital
        )
        
        return self.results
    
    def _get_market_data_for_date(self, date_str: str) -> Dict:
        """Get market data for a specific date from cache"""
        market_data = {}
        
        # Get asset prices
        for asset in self.assets:
            data_points = self.cache.get_market_data(asset, date_str, date_str)
            if data_points:
                point = data_points[0]
                market_data[f"{asset}_price"] = point.price_usd
                market_data[f"{asset}_volume"] = point.volume_24h or 0
        
        # Get protocol APYs
        for protocol in self.protocols:
            data_points = self.cache.get_protocol_data(protocol, date_str, date_str)
            if data_points:
                point = data_points[0]
                market_data[f"{protocol}_apy"] = point.apy
                market_data[f"{protocol}_tvl"] = point.tvl or 0
        
        return market_data
    
    async def _execute_agents_for_day(self, market_data: Dict):
        """Execute all agent strategies for one day"""
        for agent in self.arena_manager.simulation_agents:
            # Execute strategy with error isolation
            trades, error = agent.safe_execute(market_data)
            
            if error:
                logger.warning(
                    "Agent execution failed",
                    agent_id=agent.id,
                    strategy=agent.strategy,
                    error=str(error)
                )
                # Penalize agent for crashes
                agent.virtual_capital *= 0.99  # 1% penalty
            else:
                # Process trades (simplified - just update capital based on returns)
                if trades:
                    # Placeholder: In real implementation, execute trades
                    # For now, apply small random return
                    import random
                    daily_return = random.gauss(0.001, 0.02)  # 0.1% avg, 2% std
                    agent.virtual_capital *= (1 + daily_return)
            
            # Update age
            agent.age += 1
            
            # Calculate fitness score (simplified)
            if agent.initial_virtual_capital > 0:
                returns = (agent.virtual_capital - agent.initial_virtual_capital) / agent.initial_virtual_capital
                agent.fitness_score = returns * 100  # Percentage return
    
    def _take_snapshots(self, date_str: str):
        """Take snapshot of all agents"""
        for agent in self.arena_manager.simulation_agents:
            snapshot = AgentSnapshot(
                date=date_str,
                agent_id=agent.id,
                virtual_capital=agent.virtual_capital,
                fitness_score=agent.fitness_score,
                sharpe_ratio=None,  # Would calculate from full history
                status=agent.status,
                tier=agent.tier
            )
            self.results.add_snapshot(snapshot)
    
    def _run_evolution_cycle(self, spawn_count: int, kill_percent: float):
        """Execute evolution cycle: kill worst, spawn new"""
        agents = self.arena_manager.simulation_agents
        
        if len(agents) < 3:
            return  # Too few agents to evolve
        
        # Sort by fitness
        sorted_agents = sorted(agents, key=lambda a: a.fitness_score)
        
        # Kill bottom performers
        num_to_kill = int(len(agents) * kill_percent)
        for i in range(num_to_kill):
            dead_agent = sorted_agents[i]
            agents.remove(dead_agent)
            self.arena_manager.dead_agents.append(dead_agent)
            self.results.total_killed += 1
        
        # Spawn new agents (mutated from top performers)
        top_performers = sorted_agents[-spawn_count:]
        for parent in top_performers:
            new_agent = self.arena_manager.mutate_agent(parent)
            self.results.total_spawned += 1
        
        logger.info(
            "Evolution cycle",
            killed=num_to_kill,
            spawned=spawn_count,
            total_agents=len(self.arena_manager.simulation_agents)
        )
    
    async def live_simulate(
        self,
        duration_days: int = 30,
        speed_multiplier: float = 10.0
    ):
        """
        Run a live forward simulation with real-time speed control.
        
        This would connect to live APIs for current data.
        Implementation placeholder - requires live data feeds.
        """
        logger.info("Live simulation not yet implemented - use backtest()")
        raise NotImplementedError("Live simulation requires live data feeds")


async def quick_backtest(
    days: int = 30,
    agents: int = 10
) -> SimulationResults:
    """
    Quick backtest helper for testing.
    
    Args:
        days: Number of days to simulate
        agents: Initial agent count
        
    Returns:
        SimulationResults
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    engine = SimulationEngine(time_multiplier=10.0)
    results = await engine.backtest(
        start_date=start_date,
        end_date=end_date,
        initial_agents=agents,
        initial_capital=10000
    )
    
    return results
