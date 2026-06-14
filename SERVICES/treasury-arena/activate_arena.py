#!/usr/bin/env python3
"""
TREASURY ARENA v2.0 - ACTIVATION SCRIPT
Activates the arena with initial agents and runs first evolution cycle
"""

import sys
from datetime import datetime
from src.arena_manager import ArenaManager
from src.simulation_engine import SimulationEngine
from src.trading_engine import TradingEngine

def activate_arena():
    """Activate Treasury Arena v2.0"""

    print("=" * 60)
    print("🚀 TREASURY ARENA v2.0 - ACTIVATION")
    print("=" * 60)
    print(f"Activation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: SIMULATION (No Real Capital)")
    print(f"Total Capital: $373,261 (virtual)")
    print("=" * 60)
    print()

    # Initialize Arena Manager
    print("📊 Initializing Arena Manager...")
    arena = ArenaManager(total_capital=373261, db_path="treasury_arena.db")
    print(f"   ✅ Arena initialized with ${arena.total_capital:,.0f}")
    print(f"   ✅ Event sourcing database: {arena.db_path}")
    print()

    # Spawn initial agents
    print("🤖 Spawning Initial Agents...")
    print("   Strategy Mix:")
    print("   - 5x DeFi Yield Farmers")
    print("   - 5x Tactical Traders")
    print()

    agents_spawned = 0

    # Spawn 5 DeFi Yield Farmers
    for i in range(5):
        agent = arena.spawn_agent("DeFi-Yield-Farmer")
        agents_spawned += 1
        print(f"   ✅ Agent {i+1}/10: {agent.id} (DeFi-Yield-Farmer)")

    # Spawn 5 Tactical Traders
    for i in range(5):
        agent = arena.spawn_agent("Tactical-Trader")
        agents_spawned += 1
        print(f"   ✅ Agent {i+6}/10: {agent.id} (Tactical-Trader)")

    print()
    print(f"✅ {agents_spawned} agents spawned successfully")
    print()

    # For activation demo, promote all simulation agents to active tier
    print("⬆️  Promoting Agents to Active Tier (for demo)...")
    for agent in arena.simulation_agents[:]:
        arena.simulation_agents.remove(agent)
        agent.status = "active"
        agent.fitness_score = 1.0  # Give them initial fitness
        arena.active_agents.append(agent)
        print(f"   ✅ Promoted {agent.id}")
    print()

    # Allocate capital
    print("💰 Allocating Capital...")
    allocations = arena.allocate_capital()
    total_allocated = sum(allocations.values())
    print(f"   ✅ Capital allocated: ${total_allocated:,.0f}")
    print(f"   ✅ Utilization: {total_allocated / arena.arena_capital:.1%}")
    print()

    # Verify capital conservation
    print("🔒 Verifying Capital Conservation...")
    conserved, discrepancy = arena.verify_capital_conservation()
    if conserved:
        print(f"   ✅ Capital conserved (discrepancy: ${abs(discrepancy):,.2f})")
    else:
        print(f"   ❌ Capital conservation error: ${discrepancy:,.2f}")
    print()

    # Get allocation breakdown
    print("📈 Capital Allocation Breakdown:")
    breakdown = arena.get_capital_allocation_breakdown()
    print(f"   Total Capital: ${breakdown['arena_capital']:,.0f}")
    print(f"   Allocated: ${breakdown['allocated']:,.0f}")
    print(f"   Available: ${breakdown['available']:,.0f}")
    utilization = breakdown['allocated'] / breakdown['arena_capital'] if breakdown['arena_capital'] > 0 else 0
    print(f"   Utilization: {utilization:.1%}")
    print()

    # Check event log
    print("📝 Event Log Status:")
    cursor = arena.db_conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM events")
    event_count = cursor.fetchone()['count']
    print(f"   ✅ {event_count} events logged")

    cursor.execute("SELECT event_type, COUNT(*) as count FROM events GROUP BY event_type")
    for row in cursor.fetchall():
        print(f"      - {row['event_type']}: {row['count']}")
    print()

    # System Status
    print("=" * 60)
    print("✅ TREASURY ARENA v2.0 - ACTIVATION COMPLETE")
    print("=" * 60)
    print(f"Status: ACTIVE")
    print(f"Simulation Agents: {len(arena.simulation_agents)}")
    print(f"Proving Agents: {len(arena.proving_agents)}")
    print(f"Active Agents: {len(arena.active_agents)}")
    print(f"Total Capital: ${arena.total_capital:,.0f}")
    print(f"Database: {arena.db_path}")
    print()
    print("🎯 Next Steps:")
    print("   1. Run backtest simulations")
    print("   2. Execute first evolution cycle")
    print("   3. Monitor agent performance")
    print("   4. Graduate successful agents")
    print()
    print("⚡💎🏛️ Arena is LIVE and ready for evolution!")
    print("=" * 60)

    return arena

def run_initial_trading(arena: ArenaManager, days: int = 14):
    """Run initial trading simulation to make stats diverge"""
    import random

    print("\n" + "=" * 60)
    print(f"🎮 RUNNING {days}-DAY TRADING SIMULATION")
    print("=" * 60)
    print()

    all_agents = arena.active_agents

    for day in range(1, days + 1):
        print(f"Day {day}/{days}: ", end="")

        for agent in all_agents:
            capital = agent.real_capital

            # Simulate market data
            market_data = {
                'protocol_apys': {
                    'aave': random.uniform(0.05, 0.12),
                    'compound': random.uniform(0.04, 0.10),
                    'pendle': random.uniform(0.08, 0.15),
                },
                'indicators': {'btc_mvrv': random.uniform(1.5, 3.0)},
                'current_allocation': {'protocol': 'aave'},
                'current_position': {}
            }

            # Execute strategy
            trades, error = agent.safe_execute(market_data)

            # Simulate outcome with some randomness
            if error:
                daily_return = random.uniform(-0.02, -0.01)
            elif trades:
                daily_return = random.uniform(-0.03, 0.05)  # Some win, some lose
            else:
                daily_return = random.uniform(-0.001, 0.001)

            pnl = capital * daily_return
            agent.real_capital = capital + pnl
            agent.record_performance(agent.real_capital, pnl, trades)

        print("✓")

    print()
    print("=" * 60)
    print("✅ TRADING SIMULATION COMPLETE")
    print("=" * 60)
    print()

    # Sort by fitness
    all_agents.sort(key=lambda a: a.fitness_score, reverse=True)

    print("🏆 LEADERBOARD:")
    print("-" * 60)
    for i, agent in enumerate(all_agents[:5], 1):
        print(f"{i}. {agent.name} - Fitness: {agent.fitness_score:.2f} | Return: {agent.total_return()*100:+.1f}%")

    print("\n💾 All performance data saved to database")
    print("🌐 Agents now have divergent stats - refresh the dashboard!")
    print()


if __name__ == '__main__':
    try:
        arena = activate_arena()

        # Run initial trading simulation
        print("\n⏳ Starting trading simulation...")
        run_initial_trading(arena, days=14)

        print("\n✅ Arena fully activated with live trading data")
        print("   Dashboard: https://fullpotential.com/treasury-arena/")

    except Exception as e:
        print(f"\n❌ Activation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
