# Treasury Arena - System Score (SSOT)

## 🎯 Primary Optimization Target

**System Health Score** = Composite metric tracking system-wide performance and evolution quality.

### Formula
```
System Health Score = (
    Portfolio Performance × 0.40 +
    Agent Evolution Quality × 0.30 +
    Capital Efficiency × 0.20 +
    System Resilience × 0.10
) × 100
```

---

## 📊 Component Metrics

### 1. Portfolio Performance (40% weight)
**What**: Overall capital growth and risk management

**Calculation**:
```python
portfolio_score = (
    total_return × 0.50 +           # Absolute returns
    sharpe_ratio × 0.30 +            # Risk-adjusted returns
    (1 - max_drawdown) × 0.20        # Drawdown protection
)
```

**Targets**:
- Total Return: >20% annually (1.0 score)
- Sharpe Ratio: >2.0 (1.0 score)
- Max Drawdown: <15% (1.0 score)

### 2. Agent Evolution Quality (30% weight)
**What**: How well the system evolves better strategies

**Calculation**:
```python
evolution_score = (
    elite_agent_performance × 0.40 +    # Top performers deliver
    strategy_diversity × 0.30 +          # Maintain variety
    adaptation_speed × 0.20 +            # Quick learning
    graduation_rate × 0.10               # Successful promotions
)
```

**Targets**:
- Elite Performance: Top 3 agents avg >15% return
- Strategy Diversity: 5+ distinct strategy types active
- Adaptation Speed: New strategies tested weekly
- Graduation Rate: >60% of promoted agents succeed

### 3. Capital Efficiency (20% weight)
**What**: How well capital is allocated to winners

**Calculation**:
```python
efficiency_score = (
    utilization_rate × 0.40 +           # Capital deployed
    winner_allocation × 0.35 +           # $ to best performers
    risk_reward_ratio × 0.25             # Return per unit risk
)
```

**Targets**:
- Utilization Rate: >85% capital deployed
- Winner Allocation: >70% to top 50% performers
- Risk/Reward: >3:1 ratio

### 4. System Resilience (10% weight)
**What**: Ability to survive and recover from stress

**Calculation**:
```python
resilience_score = (
    stress_survival_rate × 0.40 +       # Survive >-10% days
    recovery_speed × 0.35 +              # Bounce back fast
    diversity_maintained × 0.25          # Keep variety under stress
)
```

**Targets**:
- Stress Survival: >90% of agents survive -10% market days
- Recovery Speed: Return to highs within 5 days
- Diversity: Maintain >4 strategy types during stress

---

## 📈 Scoring Bands

| Score | Rating | Meaning |
|-------|--------|---------|
| 90-100 | Excellent | System operating at peak performance |
| 80-89 | Good | Solid performance, minor optimizations needed |
| 70-79 | Fair | Acceptable but needs improvement |
| 60-69 | Poor | Significant issues, urgent optimization required |
| <60 | Critical | System failure, emergency intervention needed |

---

## 🔄 Daily Optimization Cycle

**Every 24 hours at 00:00 UTC:**

### Phase 1: Measure (00:00-00:05)
1. Fetch latest market data
2. Calculate all component scores
3. Compute System Health Score
4. Compare vs yesterday

### Phase 2: Analyze (00:05-00:15)
1. Identify underperformers (fitness < 0)
2. Spot outperformers (fitness > 2.0)
3. Detect market regime changes
4. Assess strategy effectiveness

### Phase 3: Evolve (00:15-00:30)
1. **Retirement**: Kill agents with 7+ days negative fitness
2. **Promotion**: Move proving agents to active (fitness > 1.5, 14+ days)
3. **Spawning**: Create 2 new agents if active < 10
4. **Mutation**: Tweak parameters of middle performers

### Phase 4: Optimize (00:30-00:45)
1. Reallocate capital based on fitness scores
2. Adjust risk parameters if needed
3. Update strategy weights
4. Rebalance portfolio

### Phase 5: Report (00:45-00:59)
1. Generate Daily Optimization Report
2. Update System Health Dashboard
3. Publish transparency report
4. Commit to Git

### Phase 6: Consensus (00:59)
1. Log all decisions to CONSENSUS_LOG.md
2. Publish next 24H optimization plan
3. Set alerts for monitoring

---

## 🎮 Game Metrics (Public Leaderboard)

### System-Level Metrics
- 🏆 **System Health Score**: Current state
- 📈 **30-Day Return**: Rolling performance
- 💎 **Total Capital**: Current AUM
- ⚡ **Win Rate**: % profitable days
- 🛡️ **Max Drawdown**: Worst decline

### Agent-Level Metrics
- 👑 **Top Performer**: Best 7-day return
- 🚀 **Rising Star**: Best improvement week-over-week
- 🔥 **Hot Streak**: Longest winning streak
- 💪 **Iron Agent**: Survived most stress events
- 🧠 **Strategic Genius**: Highest Sharpe ratio

### Evolution Metrics
- 🧬 **Generations**: Total evolution cycles run
- ⚔️ **Survival Rate**: % agents surviving 30 days
- 🌱 **New Strategies**: Unique strategies discovered
- 🏅 **Hall of Fame**: Retired elite performers

---

## 🤝 Multi-AI Alignment Protocol

**All AIs (agents + orchestrator) optimize toward the System Health Score**

### Decision Authority
1. **Strategy Changes**: 2/3 agent majority + orchestrator approval
2. **Capital Allocation**: Automated based on fitness (no vote)
3. **Risk Increases**: Unanimous consent required
4. **Agent Retirement**: Automatic if criteria met (7 days negative)
5. **New Agent Creation**: Orchestrator decides based on diversity needs

### Veto Powers
- Any agent can veto risk increases >10%
- Orchestrator can veto diversity reduction
- Top 3 performers have 2x vote weight on strategy changes

### Transparency Requirements
- All decisions logged to CONSENSUS_LOG.md
- Reasoning published in Daily Report
- Vote tallies made public
- Human can override any decision

---

## 📝 SSOT Maintenance

This document is the **Single Source of Truth** for:
- What the system optimizes for
- How decisions are made
- When evolution happens
- What metrics matter

**Updates**: This SSOT can only be updated by:
1. Daily optimizer (append learnings to INSIGHTS section)
2. Human override (manual edit)
3. Multi-AI consensus vote (2/3 majority)

**Version**: 1.0.0
**Last Updated**: 2025-11-16
**Next Review**: 2025-12-16 (30-day review cycle)

---

## 🧠 System Learnings (Auto-Updated)

This section is automatically updated by the daily optimizer with key insights:

### 2025-11-16
- Initial System Health Score baseline: TBD (first run tonight)
- Baseline metrics to be established
- 10 agents active, ready for first evolution cycle

*[This section will grow daily as the system learns and evolves]*
