#!/usr/bin/env python3
"""
Treasury Arena - Daily Optimizer
Runs autonomous evolution cycle every 24 hours

This is the heart of the self-optimizing system.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import json

from src.arena_manager import ArenaManager
from src.live_data import get_live_market_data

# Directories
REPORTS_DIR = Path("DAILY_REPORTS")
REPORTS_DIR.mkdir(exist_ok=True)

CONSENSUS_LOG = Path("CONSENSUS_LOG.md")


class SystemHealthCalculator:
    """Calculates the System Health Score"""

    def __init__(self, arena: ArenaManager):
        self.arena = arena

    def calculate(self) -> dict:
        """Calculate full System Health Score with all components"""

        # Component 1: Portfolio Performance (40%)
        portfolio_score = self._calculate_portfolio_performance()

        # Component 2: Agent Evolution Quality (30%)
        evolution_score = self._calculate_evolution_quality()

        # Component 3: Capital Efficiency (20%)
        efficiency_score = self._calculate_capital_efficiency()

        # Component 4: System Resilience (10%)
        resilience_score = self._calculate_resilience()

        # Weighted composite
        system_health = (
            portfolio_score * 0.40 +
            evolution_score * 0.30 +
            efficiency_score * 0.20 +
            resilience_score * 0.10
        ) * 100

        return {
            'system_health_score': system_health,
            'components': {
                'portfolio_performance': portfolio_score,
                'evolution_quality': evolution_score,
                'capital_efficiency': efficiency_score,
                'system_resilience': resilience_score
            },
            'rating': self._get_rating(system_health),
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_portfolio_performance(self) -> float:
        """Portfolio Performance = returns + sharpe + drawdown protection"""
        all_agents = self.arena.active_agents + self.arena.proving_agents

        if not all_agents:
            return 0.5  # Neutral score

        # Total return across all agents
        total_return = sum(a.total_return() for a in all_agents) / len(all_agents)
        total_return_score = min(total_return / 0.20, 1.0)  # 20% = perfect

        # Sharpe ratio (simplified - using win rate as proxy)
        avg_win_rate = sum(a.win_rate() for a in all_agents) / len(all_agents)
        sharpe_score = avg_win_rate  # Win rate is good sharpe proxy

        # Drawdown protection (estimate from fitness scores)
        positive_fitness_pct = len([a for a in all_agents if a.fitness_score > 0]) / len(all_agents)
        drawdown_score = positive_fitness_pct

        return (
            total_return_score * 0.50 +
            sharpe_score * 0.30 +
            drawdown_score * 0.20
        )

    def _calculate_evolution_quality(self) -> float:
        """Evolution Quality = elite performance + diversity + adaptation"""
        all_agents = self.arena.active_agents

        if len(all_agents) < 3:
            return 0.5

        # Elite performance (top 3 agents)
        top_3 = sorted(all_agents, key=lambda a: a.fitness_score, reverse=True)[:3]
        elite_avg_return = sum(a.total_return() for a in top_3) / 3
        elite_score = min(elite_avg_return / 0.15, 1.0)  # 15% = perfect

        # Strategy diversity
        strategies = set(a.strategy for a in all_agents)
        diversity_score = min(len(strategies) / 5.0, 1.0)  # 5 types = perfect

        # Adaptation (agents with improving fitness)
        improving = len([a for a in all_agents if len(a.performance_history) > 1 and
                        a.fitness_score > 0])
        adaptation_score = improving / len(all_agents)

        # Graduation rate (proving agents that made it to active)
        graduation_score = 0.6  # Default (will improve with real data)

        return (
            elite_score * 0.40 +
            diversity_score * 0.30 +
            adaptation_score * 0.20 +
            graduation_score * 0.10
        )

    def _calculate_capital_efficiency(self) -> float:
        """Capital Efficiency = utilization + winner allocation + risk/reward"""
        breakdown = self.arena.get_capital_allocation_breakdown()

        # Utilization rate
        utilization = breakdown['allocated'] / breakdown['arena_capital'] if breakdown['arena_capital'] > 0 else 0
        utilization_score = min(utilization / 0.85, 1.0)  # 85% = perfect

        # Winner allocation (% of capital to top 50% performers)
        all_agents = self.arena.active_agents
        if all_agents:
            sorted_agents = sorted(all_agents, key=lambda a: a.fitness_score, reverse=True)
            top_half = sorted_agents[:len(sorted_agents)//2]
            top_half_capital = sum(a.real_capital for a in top_half)
            total_capital = sum(a.real_capital for a in all_agents)
            winner_allocation = top_half_capital / total_capital if total_capital > 0 else 0
            winner_score = min(winner_allocation / 0.70, 1.0)  # 70% = perfect
        else:
            winner_score = 0.5

        # Risk/reward (avg fitness score is proxy)
        avg_fitness = sum(a.fitness_score for a in all_agents) / len(all_agents) if all_agents else 0
        risk_reward_score = min(max(avg_fitness, 0) / 2.0, 1.0)  # Fitness 2.0 = perfect

        return (
            utilization_score * 0.40 +
            winner_score * 0.35 +
            risk_reward_score * 0.25
        )

    def _calculate_resilience(self) -> float:
        """Resilience = stress survival + recovery + diversity"""
        all_agents = self.arena.active_agents

        if not all_agents:
            return 0.5

        # Stress survival (agents still above 50% of starting capital)
        survivors = len([a for a in all_agents if a.real_capital > a.virtual_capital * 0.5])
        survival_score = survivors / len(all_agents)

        # Recovery speed (agents with positive recent performance)
        recent_winners = len([a for a in all_agents if a.fitness_score > 0])
        recovery_score = recent_winners / len(all_agents)

        # Diversity maintained (strategy types)
        strategies = set(a.strategy for a in all_agents)
        diversity_score = min(len(strategies) / 4.0, 1.0)  # 4 types minimum

        return (
            survival_score * 0.40 +
            recovery_score * 0.35 +
            diversity_score * 0.25
        )

    def _get_rating(self, score: float) -> str:
        """Convert score to rating"""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 70:
            return "Fair"
        elif score >= 60:
            return "Poor"
        else:
            return "Critical"


class DailyOptimizer:
    """Executes the daily optimization cycle"""

    def __init__(self, arena: ArenaManager):
        self.arena = arena
        self.calculator = SystemHealthCalculator(arena)
        self.report_data = {}

    def run_optimization_cycle(self):
        """Execute full daily optimization"""
        print("=" * 70)
        print("🚀 TREASURY ARENA - DAILY OPTIMIZATION CYCLE")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()

        # Phase 1: Measure
        print("📊 Phase 1: MEASURE")
        health_data = self._measure()
        print(f"   System Health Score: {health_data['system_health_score']:.1f}/100 ({health_data['rating']})")
        print()

        # Phase 2: Analyze
        print("🔍 Phase 2: ANALYZE")
        analysis = self._analyze()
        print(f"   Underperformers: {len(analysis['underperformers'])}")
        print(f"   Outperformers: {len(analysis['outperformers'])}")
        print(f"   Strategy diversity: {analysis['strategy_diversity']}/10")
        print()

        # Phase 3: Evolve
        print("🧬 Phase 3: EVOLVE")
        evolution = self._evolve(analysis)
        print(f"   Retired: {len(evolution['retired'])} agents")
        print(f"   Promoted: {len(evolution['promoted'])} agents")
        print(f"   Spawned: {len(evolution['spawned'])} agents")
        print()

        # Phase 4: Optimize
        print("⚡ Phase 4: OPTIMIZE")
        optimization = self._optimize()
        print(f"   Capital reallocated: ${optimization['reallocated']:,.0f}")
        print(f"   New utilization: {optimization['utilization']:.1%}")
        print()

        # Phase 5: Report
        print("📝 Phase 5: REPORT")
        report_path = self._generate_report(health_data, analysis, evolution, optimization)
        print(f"   Report saved: {report_path}")
        print()

        # Phase 6: Consensus
        print("🤝 Phase 6: CONSENSUS")
        self._log_consensus(health_data, evolution)
        print("   Decisions logged to CONSENSUS_LOG.md")
        print()

        print("=" * 70)
        print("✅ OPTIMIZATION CYCLE COMPLETE")
        print("=" * 70)

        return health_data

    def _measure(self) -> dict:
        """Phase 1: Measure system health"""
        health_data = self.calculator.calculate()
        self.report_data['health'] = health_data
        return health_data

    def _analyze(self) -> dict:
        """Phase 2: Analyze agent performance"""
        all_agents = self.arena.active_agents + self.arena.proving_agents

        underperformers = [a for a in all_agents if a.fitness_score < 0 and
                          len(a.performance_history) >= 7]
        outperformers = [a for a in all_agents if a.fitness_score > 2.0 and
                        len(a.performance_history) >= 14]

        strategies = set(a.strategy for a in all_agents)
        strategy_diversity = len(strategies) * 2  # Scale to 10

        analysis = {
            'underperformers': underperformers,
            'outperformers': outperformers,
            'strategy_diversity': strategy_diversity,
            'total_agents': len(all_agents)
        }

        self.report_data['analysis'] = analysis
        return analysis

    def _evolve(self, analysis: dict) -> dict:
        """Phase 3: Evolve agents (retire/promote/spawn)"""
        retired = []
        promoted = []
        spawned = []

        # Retire underperformers (7+ days negative fitness)
        for agent in analysis['underperformers']:
            self.arena.active_agents = [a for a in self.arena.active_agents if a.id != agent.id]
            self.arena.proving_agents = [a for a in self.arena.proving_agents if a.id != agent.id]
            retired.append({
                'name': agent.name,
                'fitness': agent.fitness_score,
                'return': agent.total_return(),
                'reason': f"Negative fitness for {len(agent.performance_history)} days"
            })

        # Promote outperformers from proving to active
        for agent in analysis['outperformers']:
            if agent in self.arena.proving_agents:
                self.arena.proving_agents.remove(agent)
                agent.status = "active"
                self.arena.active_agents.append(agent)
                promoted.append({
                    'name': agent.name,
                    'fitness': agent.fitness_score,
                    'return': agent.total_return()
                })

        # Spawn new agents if we're below target
        while len(self.arena.active_agents) < 10:
            # Alternate between strategy types
            strategy_type = "DeFi-Yield-Farmer" if len(spawned) % 2 == 0 else "Tactical-Trader"
            new_agent = self.arena.spawn_agent(strategy_type)
            spawned.append({
                'name': new_agent.name,
                'strategy': strategy_type
            })

        evolution = {
            'retired': retired,
            'promoted': promoted,
            'spawned': spawned
        }

        self.report_data['evolution'] = evolution
        return evolution

    def _optimize(self) -> dict:
        """Phase 4: Optimize capital allocation"""
        # Reallocate capital based on current fitness
        allocations = self.arena.allocate_capital()

        breakdown = self.arena.get_capital_allocation_breakdown()

        optimization = {
            'reallocated': breakdown['allocated'],
            'utilization': breakdown['allocated'] / breakdown['arena_capital'] if breakdown['arena_capital'] > 0 else 0,
            'agent_count': len(self.arena.active_agents)
        }

        self.report_data['optimization'] = optimization
        return optimization

    def _generate_report(self, health_data, analysis, evolution, optimization) -> Path:
        """Phase 5: Generate daily optimization report"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        report_path = REPORTS_DIR / f"{date_str}.md"

        report = f"""# Daily System Optimization Report - {date_str}

## System Health Score: {health_data['system_health_score']:.1f}/100 ({health_data['rating']})

### Component Scores
- **Portfolio Performance**: {health_data['components']['portfolio_performance']:.2f} (40% weight)
- **Evolution Quality**: {health_data['components']['evolution_quality']:.2f} (30% weight)
- **Capital Efficiency**: {health_data['components']['capital_efficiency']:.2f} (20% weight)
- **System Resilience**: {health_data['components']['system_resilience']:.2f} (10% weight)

---

## What the System Learned Today

### Market Observations
"""

        # Add market data
        try:
            market_data = get_live_market_data()
            report += f"- BTC Price: ${market_data['prices']['BTC']:,.0f}\n"
            report += f"- Aave APY: {market_data['protocol_apys']['aave']*100:.2f}%\n"
            report += f"- Pendle APY: {market_data['protocol_apys']['pendle']*100:.2f}%\n"
            report += f"- MVRV Ratio: {market_data['indicators']['btc_mvrv']:.2f}\n"
        except:
            report += "- Market data unavailable\n"

        report += f"\n### System Insights\n"
        report += f"- Active Agents: {len(self.arena.active_agents)}\n"
        report += f"- Strategy Diversity: {analysis['strategy_diversity']}/10\n"
        report += f"- Capital Utilization: {optimization['utilization']:.1%}\n"

        report += f"\n---\n\n## Agents Evolved\n\n"

        if evolution['retired']:
            report += f"### 🔴 Retired ({len(evolution['retired'])})\n"
            for r in evolution['retired']:
                report += f"- **{r['name']}**: Fitness {r['fitness']:.2f}, Return {r['return']*100:+.1f}% - {r['reason']}\n"

        if evolution['promoted']:
            report += f"\n### 🟢 Promoted ({len(evolution['promoted'])})\n"
            for p in evolution['promoted']:
                report += f"- **{p['name']}**: Fitness {p['fitness']:.2f}, Return {p['return']*100:+.1f}%\n"

        if evolution['spawned']:
            report += f"\n### 🆕 Spawned ({len(evolution['spawned'])})\n"
            for s in evolution['spawned']:
                report += f"- **{s['name']}** ({s['strategy']})\n"

        report += f"\n---\n\n## System Improvements\n\n"
        report += f"1. Reallocated ${optimization['reallocated']:,.0f} across {optimization['agent_count']} agents\n"
        report += f"2. Capital utilization: {optimization['utilization']:.1%}\n"
        report += f"3. Maintained strategy diversity: {analysis['strategy_diversity']}/10\n"

        report += f"\n---\n\n## Performance vs Benchmarks\n\n"

        # Calculate system-wide metrics
        all_agents = self.arena.active_agents
        if all_agents:
            avg_return = sum(a.total_return() for a in all_agents) / len(all_agents)
            report += f"- System Avg Return: {avg_return*100:+.2f}%\n"
            report += f"- Top Agent Return: {max(a.total_return() for a in all_agents)*100:+.2f}%\n"
            report += f"- Avg Win Rate: {sum(a.win_rate() for a in all_agents) / len(all_agents)*100:.1f}%\n"

        report += f"\n---\n\n## Next 24H Optimization Plan\n\n"
        report += f"1. Monitor {len(analysis['underperformers'])} agents on probation\n"
        report += f"2. Continue testing {len(evolution['spawned'])} new agents\n"
        report += f"3. Track market conditions for regime changes\n"
        report += f"4. Evaluate capital allocation efficiency\n"

        report += f"\n---\n\n*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"
        report += f"*System Version: 2.0 | Optimization Cycle: Daily*\n"

        # Write report
        report_path.write_text(report)

        return report_path

    def _log_consensus(self, health_data, evolution):
        """Phase 6: Log consensus decisions"""
        log_entry = f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        log_entry += f"**System Health Score**: {health_data['system_health_score']:.1f}/100\n\n"
        log_entry += f"**Decisions Made**:\n"
        log_entry += f"- Retired {len(evolution['retired'])} underperforming agents\n"
        log_entry += f"- Promoted {len(evolution['promoted'])} successful agents\n"
        log_entry += f"- Spawned {len(evolution['spawned'])} new agents\n\n"
        log_entry += f"**Consensus**: Autonomous execution (no votes required for routine evolution)\n\n"
        log_entry += "---\n"

        # Append to consensus log
        if CONSENSUS_LOG.exists():
            current = CONSENSUS_LOG.read_text()
            CONSENSUS_LOG.write_text(current + log_entry)
        else:
            header = "# Treasury Arena - Consensus Log\n\nAll system decisions logged here.\n\n---\n"
            CONSENSUS_LOG.write_text(header + log_entry)


def main():
    """Run daily optimization"""
    try:
        print("\n🏛️  Loading Treasury Arena...\n")
        arena = ArenaManager(total_capital=373261, db_path="treasury_arena.db")

        # Auto-spawn agents if none exist (same as web app)
        if len(arena.active_agents) == 0:
            print("📝 No active agents found. Auto-spawning initial agents...\n")

            # Spawn 10 agents (5 DeFi, 5 Tactical)
            for i in range(5):
                agent = arena.spawn_agent("DeFi-Yield-Farmer")
                print(f"   ✅ Spawned {agent.id} (DeFi-Yield-Farmer)")

            for i in range(5):
                agent = arena.spawn_agent("Tactical-Trader")
                print(f"   ✅ Spawned {agent.id} (Tactical-Trader)")

            # Promote all to active tier
            for agent in arena.simulation_agents[:]:
                arena.simulation_agents.remove(agent)
                agent.status = "active"
                agent.fitness_score = 1.0
                arena.active_agents.append(agent)

            # Allocate capital
            arena.allocate_capital()

            print(f"\n✅ {len(arena.active_agents)} agents activated and ready\n")

        optimizer = DailyOptimizer(arena)
        health_data = optimizer.run_optimization_cycle()

        print(f"\n✅ Optimization complete!")
        print(f"📊 System Health Score: {health_data['system_health_score']:.1f}/100")
        print(f"🌐 View dashboard: https://fullpotential.com/treasury-arena/\n")

        return 0

    except Exception as e:
        print(f"\n❌ Optimization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
