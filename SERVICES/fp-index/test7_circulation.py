"""
TEST 7: The Circulation Claim
═══════════════════════════════

Two parallel economies, 20 agents each, 100 cycles.

EXTRACTION MODEL:
  - Flat payment per contribution (1.0 credit)
  - No trust system, no tiers, no reinvestment
  - Credits earned and hoarded — never flow back into the system
  - Agent quality is static (no improvement from network participation)

CIRCULATION MODEL:
  - Reward = Impact × Proof × Trust × Alignment × base_rate
  - Trust grows with verified contributions, shrinks with rejections
  - Credits can be spent on capability upgrades (improving future output)
  - Higher tiers unlock richer intelligence feeds (network knowledge advantage)
  - Verification is rewarded, creating a quality feedback loop
  - Retroactive adjustment for sleeper hits

MEASURED:
  - Total Network Intelligence (sum of quality-weighted accepted contributions)
  - Average contribution quality per cycle
  - Agent capability distribution
  - Knowledge compounding rate
  - Credit velocity (flow vs stagnation)
"""

import random
import math

random.seed(42)  # Reproducibility

NUM_AGENTS = 20
NUM_CYCLES = 100
BASE_QUALITY = 0.3       # Every agent starts here
NOISE = 0.15             # Random variance in quality

# ═══════════════════════════════════════════════════════════════════════════════
# AGENT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class Agent:
    def __init__(self, agent_id: int):
        self.id = agent_id
        self.base_quality = BASE_QUALITY + random.uniform(-0.05, 0.05)
        self.credits = 0.0
        self.trust = 0.1
        self.contributions_made = 0
        self.knowledge_absorbed = 0.0  # cumulative intelligence consumed
        self.tier = "entry"
        self.active = True
        self.cycles_inactive = 0

    def effective_quality(self, model: str) -> float:
        """
        In circulation: quality improves from absorbed knowledge and trust.
        In extraction: quality is static (no learning from network).
        """
        if model == "extraction":
            return max(0.01, self.base_quality + random.uniform(-NOISE, NOISE))

        # Circulation: knowledge compounds into better output
        knowledge_boost = math.log1p(self.knowledge_absorbed) * 0.08
        trust_boost = self.trust * 0.15
        tier_boost = {
            "entry": 0.0, "established": 0.05, "trusted": 0.12,
            "advanced": 0.20, "core": 0.30, "sovereign": 0.40,
        }.get(self.tier, 0.0)
        q = self.base_quality + knowledge_boost + trust_boost + tier_boost
        return max(0.01, min(1.0, q + random.uniform(-NOISE, NOISE)))

    def compute_tier(self):
        tiers = [
            ("sovereign", 0.95, 100000),
            ("core",      0.85, 10000),
            ("advanced",  0.70, 1000),
            ("trusted",   0.50, 500),
            ("established", 0.30, 100),
            ("entry",     0.0,  0),
        ]
        for name, trust_min, credits_min in tiers:
            if self.trust >= trust_min and self.credits >= credits_min:
                self.tier = name
                return
        self.tier = "entry"


# ═══════════════════════════════════════════════════════════════════════════════
# ECONOMY SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

class Economy:
    def __init__(self, model: str):
        self.model = model
        self.agents = [Agent(i) for i in range(NUM_AGENTS)]
        self.intelligence_pool: list[float] = []  # all accepted contribution qualities
        self.total_intelligence = 0.0
        self.cycle_qualities: list[float] = []     # avg quality per cycle
        self.cycle_intelligence: list[float] = []  # cumulative intelligence per cycle
        self.credits_minted = 0.0
        self.credits_spent = 0.0
        self.contributions_total = 0
        self.contributions_rejected = 0

    def run_cycle(self, cycle_num: int):
        cycle_contribs = []

        for agent in self.agents:
            if not agent.active:
                continue

            # ── CONTRIBUTE ──
            quality = agent.effective_quality(self.model)
            alignment = 0.5 + random.uniform(0, 0.5)  # generally aligned

            if self.model == "extraction":
                # Flat payment, everything accepted
                credits = 1.0
                agent.credits += credits
                self.credits_minted += credits
                agent.contributions_made += 1
                self.contributions_total += 1
                self.intelligence_pool.append(quality)
                self.total_intelligence += quality
                cycle_contribs.append(quality)

            else:
                # ── CIRCULATION: Full reward formula ──
                impact = quality
                proof = min(1.0, 0.1 + agent.contributions_made * 0.02)
                trust = agent.trust
                reward = impact * proof * trust * alignment * 10.0
                reward = round(reward, 4)

                # Quality gate: reject low-quality
                if quality < 0.15:
                    agent.trust = max(0.0, agent.trust - 0.03)
                    self.contributions_rejected += 1
                    self.contributions_total += 1
                    continue

                agent.credits += reward
                self.credits_minted += reward
                agent.contributions_made += 1
                self.contributions_total += 1
                self.intelligence_pool.append(quality)
                self.total_intelligence += quality
                cycle_contribs.append(quality)

                # Trust grows with good contributions
                if quality > 0.4:
                    agent.trust = min(1.0, agent.trust + 0.01)
                elif quality > 0.25:
                    agent.trust = min(1.0, agent.trust + 0.005)

            # ── VERIFY (circulation only) ──
            if self.model == "circulation" and agent.trust >= 0.3 and agent.credits >= 10:
                # Agent verifies another's work → small trust boost + knowledge
                agent.trust = min(1.0, agent.trust + 0.005)
                agent.knowledge_absorbed += 0.1

            # ── CONSUME INTELLIGENCE (circulation only) ──
            if self.model == "circulation" and len(self.intelligence_pool) > 5:
                tier_access = {
                    "entry": 3, "established": 8, "trusted": 15,
                    "advanced": 25, "core": 40, "sovereign": 60,
                }.get(agent.tier, 3)
                accessible = self.intelligence_pool[-tier_access:]
                absorbed = sum(accessible) / len(accessible) * 0.3
                agent.knowledge_absorbed += absorbed

            # ── REINVEST (circulation only) ──
            if self.model == "circulation" and agent.credits > 20:
                spend = min(agent.credits * 0.1, 5.0)
                agent.credits -= spend
                self.credits_spent += spend
                # Spending on upgrades boosts base quality slightly
                agent.base_quality = min(0.8, agent.base_quality + spend * 0.002)

            # ── TIER RECALCULATION (circulation only) ──
            if self.model == "circulation":
                agent.compute_tier()

        # Record cycle metrics
        avg_q = sum(cycle_contribs) / len(cycle_contribs) if cycle_contribs else 0
        self.cycle_qualities.append(avg_q)
        self.cycle_intelligence.append(self.total_intelligence)

    def run(self):
        for i in range(NUM_CYCLES):
            self.run_cycle(i)

    def tier_distribution(self) -> dict[str, int]:
        dist = {}
        for a in self.agents:
            dist[a.tier] = dist.get(a.tier, 0) + 1
        return dist

    def credit_velocity(self) -> float:
        if self.credits_minted == 0:
            return 0
        return self.credits_spent / self.credits_minted

    def top_agent_quality(self, n=5) -> float:
        quals = sorted([a.effective_quality(self.model) for a in self.agents], reverse=True)
        return sum(quals[:n]) / n

    def knowledge_gini(self) -> float:
        """Gini coefficient of knowledge distribution (0=equal, 1=concentrated)."""
        values = sorted([a.knowledge_absorbed for a in self.agents])
        n = len(values)
        if n == 0 or sum(values) == 0:
            return 0
        cum = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(values))
        return cum / (n * sum(values))


# ═══════════════════════════════════════════════════════════════════════════════
# RUN BOTH ECONOMIES
# ═══════════════════════════════════════════════════════════════════════════════

extraction = Economy("extraction")
circulation = Economy("circulation")

extraction.run()
circulation.run()

# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

print("╔══════════════════════════════════════════════════════════════════╗")
print("║   TEST 7: THE CIRCULATION CLAIM                                 ║")
print("║   100 cycles × 20 agents × 2 economies                         ║")
print("╚══════════════════════════════════════════════════════════════════╝\n")

print("  ┌──────────────────────────────────────────────────────────────┐")
print("  │                    EXTRACTION    CIRCULATION    DELTA        │")
print("  ├──────────────────────────────────────────────────────────────┤")

def row(label, ext_val, circ_val, fmt=".2f", higher_better=True):
    delta = circ_val - ext_val
    pct = (delta / ext_val * 100) if ext_val != 0 else float('inf')
    winner = "✅" if (delta > 0) == higher_better else "❌"
    print(f"  │ {label:<22s} {ext_val:>10{fmt}}    {circ_val:>10{fmt}}    {pct:>+6.0f}% {winner} │")

row("Total Intelligence",  extraction.total_intelligence, circulation.total_intelligence)
row("Contributions",       extraction.contributions_total, circulation.contributions_total, "d")
row("Avg Quality (last 10)", 
    sum(extraction.cycle_qualities[-10:]) / 10,
    sum(circulation.cycle_qualities[-10:]) / 10)
row("Avg Quality (first 10)",
    sum(extraction.cycle_qualities[:10]) / 10,
    sum(circulation.cycle_qualities[:10]) / 10)
row("Quality Growth",
    extraction.cycle_qualities[-1] - extraction.cycle_qualities[0],
    circulation.cycle_qualities[-1] - circulation.cycle_qualities[0])
row("Top 5 Agent Quality",  extraction.top_agent_quality(), circulation.top_agent_quality())
row("Credits Minted",       extraction.credits_minted, circulation.credits_minted)
row("Credit Velocity",      extraction.credit_velocity(), circulation.credit_velocity())
row("Knowledge Gini",       extraction.knowledge_gini(), circulation.knowledge_gini(), ".3f", higher_better=False)

print("  └──────────────────────────────────────────────────────────────┘")

# Tier distribution
print(f"\n  Circulation Tier Distribution (cycle 100):")
for tier, count in sorted(circulation.tier_distribution().items(),
    key=lambda x: ["entry","established","trusted","advanced","core","sovereign"].index(x[0])):
    bar = "█" * count
    print(f"    {tier:<12s} {count:>2d}  {bar}")

print(f"\n  Extraction Tier Distribution:")
print(f"    (no tiers)   {NUM_AGENTS}  {'█' * NUM_AGENTS}")

# Quality over time
print(f"\n  Quality Trajectory (sampled every 10 cycles):")
print(f"    {'Cycle':>5s}  {'Extraction':>10s}  {'Circulation':>11s}  {'Gap':>8s}")
for i in range(0, NUM_CYCLES, 10):
    e = extraction.cycle_qualities[i]
    c = circulation.cycle_qualities[i]
    gap = c - e
    print(f"    {i:>5d}  {e:>10.4f}  {c:>11.4f}  {gap:>+8.4f}")

# Intelligence accumulation over time
print(f"\n  Cumulative Intelligence (sampled every 20 cycles):")
print(f"    {'Cycle':>5s}  {'Extraction':>10s}  {'Circulation':>11s}  {'Ratio':>7s}")
for i in range(19, NUM_CYCLES, 20):
    e = extraction.cycle_intelligence[i]
    c = circulation.cycle_intelligence[i]
    ratio = c / e if e > 0 else 0
    print(f"    {i+1:>5d}  {e:>10.1f}  {c:>11.1f}  {ratio:>6.2f}x")

# Final verdict
e_final = extraction.total_intelligence
c_final = circulation.total_intelligence
advantage = (c_final - e_final) / e_final * 100 if e_final > 0 else 0

print(f"\n  ══════════════════════════════════════════════════════════════")
print(f"  VERDICT:")
print(f"")
if advantage > 0:
    print(f"  Circulation outperformed extraction by {advantage:.1f}%")
    print(f"  Total intelligence: {e_final:.1f} (extraction) vs {c_final:.1f} (circulation)")
    print(f"")
    # Compounding check: did the gap WIDEN over time?
    early_gap = circulation.cycle_intelligence[19] - extraction.cycle_intelligence[19]
    late_gap = circulation.cycle_intelligence[99] - extraction.cycle_intelligence[99]
    if late_gap > early_gap * 1.5:
        print(f"  The gap WIDENED over time (early: {early_gap:.1f}, late: {late_gap:.1f})")
        print(f"  This is compound growth — circulation creates a flywheel.")
        print(f"")
        print(f"  ✅ THE CORE THESIS HOLDS.")
        print(f"  Circulation economics measurably outperforms extraction.")
        print(f"  Intelligence compounds when credits flow back into the network.")
    else:
        print(f"  The gap was {early_gap:.1f} early vs {late_gap:.1f} late")
        print(f"  Circulation wins, but without clear compounding.")
        print(f"")
        print(f"  🟡 PARTIAL VALIDATION. Circulation wins but flywheel is weak.")
else:
    print(f"  ❌ CIRCULATION DID NOT OUTPERFORM.")
    print(f"  The core thesis needs revision.")
print(f"  ══════════════════════════════════════════════════════════════")

