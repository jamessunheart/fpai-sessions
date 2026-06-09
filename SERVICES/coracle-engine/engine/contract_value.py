"""
Coracle Contract Value Mathematics
===================================

This module calculates the expected value and "edge" of Coracle contracts.

CORE CONCEPT:
If Coracle predicts with better-than-random accuracy, every contract has positive
expected value. The value compounds as accuracy improves.

KEY FORMULAS:

1. EXPECTED VALUE (EV)
   EV = (Win_Prob × Reward) - (Loss_Prob × Risk)
   
   Example: 60% win chance, 2:1 R:R
   EV = (0.60 × 2) - (0.40 × 1) = +0.80 per unit

2. EDGE (vs random chance)
   Edge = Coracle_Accuracy - Baseline_Accuracy
   
   Example: Coracle 60%, Random 50%
   Edge = 10%

3. CONTRACT VALUE
   Value = EV × Position_Size × Accuracy_Multiplier
   
   Where Accuracy_Multiplier grows as Coracle proves itself

4. KELLY CRITERION (optimal position sizing)
   f* = (p(R+1) - 1) / R
   
   Example: 60% win, 2:1 R:R
   f* = (0.60 × 3 - 1) / 2 = 0.40 (40% of bankroll)

5. COMPOUND VALUE OVER TIME
   Total_Value = Σ(EV_i × Size_i) for all trades
   
   If you have edge, this grows exponentially with Kelly sizing.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
import math


@dataclass
class ContractValueMetrics:
    """Complete value analysis for a Coracle contract."""
    
    # Basic EV calculations
    ev_tp1: float  # Expected value targeting TP1
    ev_tp2: float  # Expected value targeting TP2
    ev_tp3: float  # Expected value targeting TP3
    ev_blended: float  # Blended EV using optimal exit strategy
    
    # Edge metrics
    edge_vs_random: float  # How much better than 50/50
    edge_vs_market: float  # How much better than market baseline
    
    # Kelly sizing
    kelly_fraction: float  # Optimal position size as % of bankroll
    kelly_half: float  # Half-Kelly (safer)
    
    # Value creation
    contract_value: float  # $ value created per $100 risked
    value_per_trade: float  # Average $ value per trade
    
    # Risk metrics
    sharpe_estimate: float  # Risk-adjusted return estimate
    max_drawdown_risk: float  # Probability of 50% drawdown
    
    # Confidence
    value_confidence: float  # How confident we are in this value (0-100%)


class ContractValueCalculator:
    """
    Calculate the mathematical value of Coracle contracts.
    
    The core insight: If our predictions are better than random,
    every contract we suggest has positive expected value.
    """
    
    def __init__(self, historical_accuracy: float = 0.55):
        """
        Args:
            historical_accuracy: Coracle's proven accuracy (0.5 = random, 0.6 = 60% accurate)
        """
        self.historical_accuracy = historical_accuracy
        self.baseline_accuracy = 0.50  # Random chance
        
    def calculate_ev(
        self, 
        win_probability: float, 
        reward_risk_ratio: float
    ) -> float:
        """
        Calculate expected value of a trade.
        
        Args:
            win_probability: Chance of winning (0-1)
            reward_risk_ratio: How much you win vs how much you risk (e.g., 2.0 = 2:1)
        
        Returns:
            EV per unit risked (positive = profitable)
        
        Example:
            60% chance to win 2x what you risk:
            EV = (0.60 × 2) - (0.40 × 1) = +0.80
            
            For every $1 risked, you expect to make $0.80
        """
        loss_probability = 1 - win_probability
        ev = (win_probability * reward_risk_ratio) - (loss_probability * 1)
        return ev
    
    def calculate_kelly(
        self, 
        win_probability: float, 
        reward_risk_ratio: float
    ) -> float:
        """
        Calculate Kelly Criterion - optimal position size.
        
        Formula: f* = (p(R+1) - 1) / R
        
        Where:
            p = win probability
            R = reward/risk ratio
            f* = fraction of bankroll to bet
        
        Returns:
            Optimal fraction of bankroll (0.0 to 1.0)
            Returns 0 if edge is negative (don't bet!)
        """
        p = win_probability
        R = reward_risk_ratio
        
        kelly = (p * (R + 1) - 1) / R
        
        # Don't bet if negative edge
        return max(0, kelly)
    
    def calculate_edge(self, coracle_accuracy: float) -> float:
        """
        Calculate edge vs random chance.
        
        Edge = (Coracle_Accuracy - 0.5) × 2
        
        This normalizes to:
        - 0% = same as random
        - 100% = perfect prediction
        - 20% = 60% accuracy (10% better than random, doubled)
        """
        return (coracle_accuracy - self.baseline_accuracy) * 2
    
    def calculate_contract_value(
        self,
        direction_probability: float,
        tp1_probability: float,
        tp2_probability: float,
        tp3_probability: float,
        risk_percent: float,
        position_size_usd: float = 100
    ) -> ContractValueMetrics:
        """
        Calculate complete value metrics for a Coracle contract.
        
        Args:
            direction_probability: Chance direction is correct (0-1)
            tp1_probability: Chance of hitting TP1 (0-1)
            tp2_probability: Chance of hitting TP2 (0-1)
            tp3_probability: Chance of hitting TP3 (0-1)
            risk_percent: Stop loss distance as decimal (e.g., 0.03 = 3%)
            position_size_usd: Position size in dollars
        
        Returns:
            ContractValueMetrics with all calculations
        """
        # Convert percentages if needed
        if direction_probability > 1:
            direction_probability /= 100
        if tp1_probability > 1:
            tp1_probability /= 100
        if tp2_probability > 1:
            tp2_probability /= 100
        if tp3_probability > 1:
            tp3_probability /= 100
        if risk_percent > 1:
            risk_percent /= 100
        
        # R:R ratios
        rr1 = 1.0  # TP1 is 1:1
        rr2 = 2.0  # TP2 is 2:1
        rr3 = 3.0  # TP3 is 3:1
        
        # Calculate EV for each target
        ev_tp1 = self.calculate_ev(tp1_probability, rr1)
        ev_tp2 = self.calculate_ev(tp2_probability, rr2)
        ev_tp3 = self.calculate_ev(tp3_probability, rr3)
        
        # Blended EV using optimal strategy:
        # Take 50% at TP1, 30% at TP2, 20% at TP3
        ev_blended = (ev_tp1 * 0.5) + (ev_tp2 * 0.3) + (ev_tp3 * 0.2)
        
        # Edge calculations
        edge_vs_random = self.calculate_edge(direction_probability)
        edge_vs_market = edge_vs_random * self.historical_accuracy / 0.55  # Scale by track record
        
        # Kelly sizing (use TP2 as primary target)
        kelly = self.calculate_kelly(tp2_probability, rr2)
        kelly_half = kelly / 2  # Safer sizing
        
        # Contract value creation
        # Value = EV × Position × (1 + Edge_Bonus)
        edge_bonus = max(0, edge_vs_random)  # Bonus for having edge
        risk_usd = position_size_usd * risk_percent
        
        contract_value = ev_blended * (1 + edge_bonus) * 100  # Per $100 risked
        value_per_trade = ev_blended * risk_usd
        
        # Risk metrics
        # Sharpe-like ratio: EV / standard deviation
        # Approximate std dev for binary outcome
        win_prob_avg = (tp1_probability + tp2_probability + tp3_probability) / 3
        variance = win_prob_avg * (1 - win_prob_avg)
        std_dev = math.sqrt(variance) if variance > 0 else 0.5
        sharpe_estimate = ev_blended / std_dev if std_dev > 0 else 0
        
        # Max drawdown risk (simplified)
        # Probability of losing 5 in a row (rough 50% drawdown proxy)
        loss_prob = 1 - win_prob_avg
        max_dd_risk = loss_prob ** 5  # 5 consecutive losses
        
        # Value confidence
        # Higher accuracy track record = higher confidence
        accuracy_factor = self.historical_accuracy / 0.55  # Baseline 55%
        probability_factor = direction_probability / 0.6  # Baseline 60%
        value_confidence = min(100, accuracy_factor * probability_factor * 80)
        
        return ContractValueMetrics(
            ev_tp1=ev_tp1,
            ev_tp2=ev_tp2,
            ev_tp3=ev_tp3,
            ev_blended=ev_blended,
            edge_vs_random=edge_vs_random,
            edge_vs_market=edge_vs_market,
            kelly_fraction=kelly,
            kelly_half=kelly_half,
            contract_value=contract_value,
            value_per_trade=value_per_trade,
            sharpe_estimate=sharpe_estimate,
            max_drawdown_risk=max_dd_risk,
            value_confidence=value_confidence
        )
    
    def explain_value_creation(
        self,
        metrics: ContractValueMetrics,
        position_size: float = 1000
    ) -> str:
        """
        Generate human-readable explanation of contract value.
        """
        risk_amount = position_size * 0.03  # Assume 3% risk
        
        explanation = f"""
╔══════════════════════════════════════════════════════════════╗
║           CORACLE CONTRACT VALUE BREAKDOWN                  ║
╠══════════════════════════════════════════════════════════════╣

📊 EXPECTED VALUE (per $1 risked):
├─ TP1 (1:1 R:R): ${metrics.ev_tp1:+.3f}
├─ TP2 (2:1 R:R): ${metrics.ev_tp2:+.3f}  
├─ TP3 (3:1 R:R): ${metrics.ev_tp3:+.3f}
└─ Blended:       ${metrics.ev_blended:+.3f}

💡 WHAT THIS MEANS:
   For every $1 you risk, you expect to make ${metrics.ev_blended:+.2f}
   On a ${position_size:,.0f} position with 3% risk (${risk_amount:.0f}):
   → Expected profit per trade: ${metrics.ev_blended * risk_amount:+.2f}

📈 EDGE (vs random chance):
├─ vs 50/50:  {metrics.edge_vs_random*100:+.1f}%
└─ vs market: {metrics.edge_vs_market*100:+.1f}%

🎯 OPTIMAL POSITION SIZING (Kelly Criterion):
├─ Full Kelly:  {metrics.kelly_fraction*100:.1f}% of bankroll
└─ Half Kelly:  {metrics.kelly_half*100:.1f}% of bankroll (recommended)

💰 VALUE CREATION:
├─ Per $100 risked: ${metrics.contract_value:.2f} expected value
└─ Per trade:       ${metrics.value_per_trade:.2f}

⚠️ RISK METRICS:
├─ Sharpe estimate:    {metrics.sharpe_estimate:.2f}
└─ 5-loss streak risk: {metrics.max_drawdown_risk*100:.1f}%

🔮 VALUE CONFIDENCE: {metrics.value_confidence:.0f}%

╠══════════════════════════════════════════════════════════════╣
║ THE MATH:                                                    ║
║                                                              ║
║ EV = (Win% × Reward) - (Loss% × Risk)                       ║
║                                                              ║
║ If Coracle is 60% accurate (vs 50% random):                 ║
║ → Every trade has +10% edge                                  ║
║ → Over 100 trades: +10 wins × $2 reward = +$20 value        ║
║                                                              ║
║ VALUE COMPOUNDS AS ACCURACY IMPROVES                         ║
╚══════════════════════════════════════════════════════════════╝
"""
        return explanation


def calculate_total_coracle_value(
    contracts: List[Dict],
    historical_accuracy: float = 0.55,
    avg_position_size: float = 1000
) -> Dict:
    """
    Calculate total value created by Coracle over multiple contracts.
    
    Returns:
        Dict with total value metrics
    """
    calculator = ContractValueCalculator(historical_accuracy)
    
    total_ev = 0
    total_value = 0
    contracts_analyzed = 0
    
    for contract in contracts:
        metrics = calculator.calculate_contract_value(
            direction_probability=contract.get("direction_probability", 55),
            tp1_probability=contract.get("tp1_probability", 50),
            tp2_probability=contract.get("tp2_probability", 35),
            tp3_probability=contract.get("tp3_probability", 20),
            risk_percent=contract.get("risk_percent", 3),
            position_size_usd=avg_position_size
        )
        
        total_ev += metrics.ev_blended
        total_value += metrics.value_per_trade
        contracts_analyzed += 1
    
    return {
        "contracts_analyzed": contracts_analyzed,
        "average_ev_per_trade": total_ev / contracts_analyzed if contracts_analyzed > 0 else 0,
        "total_expected_value": total_value,
        "value_if_accuracy_maintained": total_value * (historical_accuracy / 0.55),
        "projected_annual_value": total_value * 365 * 24,  # Assuming hourly contracts
    }


# Quick reference formulas
FORMULAS = """
═══════════════════════════════════════════════════════════════
                CORACLE VALUE CREATION FORMULAS
═══════════════════════════════════════════════════════════════

1. EXPECTED VALUE (EV)
   ────────────────────
   EV = (p × R) - ((1-p) × 1)
   
   Where:
   • p = probability of winning
   • R = reward/risk ratio
   • 1 = risk (normalized)
   
   Example: 60% chance, 2:1 R:R
   EV = (0.60 × 2) - (0.40 × 1) = +0.80


2. EDGE
   ────────────────────
   Edge = (Accuracy - 0.50) × 2
   
   Example: 60% accuracy
   Edge = (0.60 - 0.50) × 2 = 20%


3. KELLY CRITERION
   ────────────────────
   f* = (p(R+1) - 1) / R
   
   Example: 60% win, 2:1 R:R
   f* = (0.60 × 3 - 1) / 2 = 0.40 (40%)


4. CONTRACT VALUE
   ────────────────────
   Value = EV × Risk_Amount × (1 + Edge)
   
   Example: EV=0.10, Risk=$30, Edge=20%
   Value = 0.10 × 30 × 1.20 = $3.60 per trade


5. COMPOUND GROWTH (with Kelly)
   ────────────────────
   Bankroll_n = Bankroll_0 × (1 + f × EV)^n
   
   Where n = number of trades


6. BREAK-EVEN ACCURACY
   ────────────────────
   p_breakeven = 1 / (1 + R)
   
   For 2:1 R:R: p = 1/3 = 33.3%
   (You only need 33% accuracy to break even!)


7. INFORMATION RATIO (Quality of Edge)
   ────────────────────
   IR = (Accuracy - Baseline) / σ(Predictions)
   
   Higher IR = more reliable edge

═══════════════════════════════════════════════════════════════
"""


if __name__ == "__main__":
    # Example usage
    calc = ContractValueCalculator(historical_accuracy=0.58)
    
    # Calculate value for a sample contract
    metrics = calc.calculate_contract_value(
        direction_probability=61,  # 61% confident in direction
        tp1_probability=62,        # 62% chance to hit TP1
        tp2_probability=40,        # 40% chance to hit TP2
        tp3_probability=26,        # 26% chance to hit TP3
        risk_percent=5.1,          # 5.1% stop loss
        position_size_usd=1000     # $1000 position
    )
    
    print(calc.explain_value_creation(metrics, position_size=1000))
    print(FORMULAS)


