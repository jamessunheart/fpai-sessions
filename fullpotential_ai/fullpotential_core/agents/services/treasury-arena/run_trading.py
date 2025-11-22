#!/usr/bin/env python3
"""
TREASURY ARENA - TRADING ACTIVATOR
Runs actual trading simulations to make agent stats diverge
"""

import sys
import asyncio
from datetime import datetime, timedelta
import random
from src.arena_manager import ArenaManager
from src.simulation_engine import SimulationEngine

def simulate_market_data(day: int) -> dict:
    """Generate realistic market data for a day"""
    # Simulate BTC price movement with some volatility
    base_btc_price = 45000
    volatility = random.uniform(-0.05, 0.05)  # ±5% daily
    btc_price = base_btc_price * (1 + volatility)

    # Simulate DeFi protocol APYs
    protocol_apys = {
        'aave': random.uniform(0.05, 0.12),  # 5-12% APY
        'compound': random.uniform(0.04, 0.10),
        'pendle': random.uniform(0.08, 0.15),
        'curve': random.uniform(0.06, 0.11)
    }

    # MVRV indicator for BTC (market cycle indicator)
    mvrv = random.uniform(1.5, 3.0)  # Typical range

    return {
        'prices': {
            'BTC': btc_price,
            'ETH': btc_price * 0.06,  # ETH typically ~6% of BTC price
        },
        'protocol_apys': protocol_apys,
        'indicators': {
            'btc_mvrv': mvrv
        },
        'current_allocation': {
            'protocol': random.choice(list(protocol_apys.keys()))
        },
        'current_position': {}  # Empty = no position
    }

def run_trading_simulation(arena: ArenaManager, days: int = 30):
    """
    Run trading simulation for all agents

    Args:
        arena: Arena manager instance
        days: Number of days to simulate
    """
    print(f"\n🎮 STARTING {days}-DAY TRADING SIMULATION")
    print("=" * 60)
    print(f"Active Agents: {len(arena.active_agents)}")
    print(f"Simulation Agents: {len(arena.simulation_agents)}")
    print(f"Total Capital: ${arena.total_capital:,.0f}")
    print("=" * 60)
    print()

    # Get all agents to simulate
    all_agents = arena.simulation_agents + arena.proving_agents + arena.active_agents

    if not all_agents:
        print("❌ No agents to simulate!")
        return

    print(f"📊 Running simulation for {len(all_agents)} agents...\n")

    # Run simulation day by day
    for day in range(1, days + 1):
        print(f"Day {day}/{days}")
        print("-" * 40)

        # Generate market data for this day
        market_data = simulate_market_data(day)

        # Each agent executes their strategy
        for agent in all_agents:
            # Get current capital
            capital = agent.get_current_capital()

            # Agent executes strategy
            trades, error = agent.safe_execute(market_data)

            if error:
                # Agent crashed - penalize
                pnl = capital * random.uniform(-0.02, -0.01)  # -1% to -2% loss
                new_capital = capital + pnl
                print(f"  ❌ {agent.name} crashed: {str(error)[:50]}")
            elif trades:
                # Agent made trades - simulate outcome
                # More randomness early, some skill later
                skill_factor = agent.fitness_score if agent.fitness_score > 0 else 0.5
                luck = random.uniform(-0.03, 0.03)  # ±3% luck
                base_return = (skill_factor - 1.0) * 0.01  # Convert fitness to return

                daily_return = base_return + luck
                pnl = capital * daily_return
                new_capital = capital + pnl

                print(f"  📈 {agent.name}: {len(trades)} trades, PnL: ${pnl:,.0f} ({daily_return*100:.2f}%)")
            else:
                # No trades - small holding cost
                pnl = capital * random.uniform(-0.001, 0.001)  # Minimal change
                new_capital = capital + pnl

            # Update agent capital
            if agent.status == "simulation":
                agent.virtual_capital = new_capital
            else:
                agent.real_capital = new_capital

            # Record performance
            agent.record_performance(new_capital, pnl, trades)

        print()

    print("\n" + "=" * 60)
    print("✅ SIMULATION COMPLETE")
    print("=" * 60)
    print()

    # Calculate and display final results
    print("📊 FINAL RESULTS:")
    print("-" * 60)

    # Sort by fitness
    all_agents.sort(key=lambda a: a.fitness_score, reverse=True)

    for i, agent in enumerate(all_agents, 1):
        agent.rank = i
        total_return = agent.total_return() * 100
        capital = agent.get_current_capital()

        print(f"{i}. {agent.name} ({agent.strategy})")
        print(f"   Capital: ${capital:,.0f} | Return: {total_return:+.2f}% | Fitness: {agent.fitness_score:.2f}")
        print(f"   Sharpe: {agent.sharpe_ratio():.2f} | Drawdown: {agent.max_drawdown()*100:.1f}% | Win Rate: {agent.win_rate()*100:.1f}%")
        print()

    print("=" * 60)
    print("🎯 Agents now have divergent stats and are ready for evolution!")
    print("=" * 60)

if __name__ == '__main__':
    try:
        # Load arena
        print("🏛️  Loading Treasury Arena...")
        arena = ArenaManager(total_capital=373261, db_path="treasury_arena.db")

        # Check if agents exist
        total_agents = len(arena.simulation_agents) + len(arena.proving_agents) + len(arena.active_agents)

        if total_agents == 0:
            print("⚠️  No agents found! Run activate_arena.py first to spawn agents.")
            sys.exit(1)

        # Run simulation
        days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
        run_trading_simulation(arena, days=days)

        print(f"\n💾 Database updated: {arena.db_path}")
        print("🌐 Refresh the web dashboard to see live results!\n")

    except Exception as e:
        print(f"\n❌ Trading simulation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
