#!/usr/bin/env python3
"""
📐 KELLY CRITERION POSITION SIZING
===================================

Calculates optimal position size using the Kelly Criterion:
- Mathematically optimal bet sizing
- Adjusted for trading (Half Kelly)
- Considers win rate, avg win, avg loss
- Applies confidence and volatility adjustments

Kelly Formula: f* = (p * b - q) / b
Where:
- p = probability of win
- q = probability of loss (1 - p)  
- b = win/loss ratio
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger("aria.trading.position_sizer")


@dataclass
class PositionSize:
    """Calculated position size with reasoning."""
    size_usd: float              # Dollar amount to trade
    size_pct: float              # Percentage of balance
    kelly_fraction: float        # Raw Kelly fraction
    applied_fraction: float      # After safety adjustments
    max_risk_usd: float          # Maximum risk on trade
    leverage: float              # Recommended leverage
    reasoning: str               # Explanation of sizing


@dataclass
class PerformanceStats:
    """Recent trading performance statistics."""
    win_rate: float              # 0.0 to 1.0
    avg_win_pct: float           # Average winning trade %
    avg_loss_pct: float          # Average losing trade %
    total_trades: int
    recent_pnl: float            # Recent P&L
    consecutive_losses: int
    max_drawdown_pct: float


class KellyPositionSizer:
    """
    Calculates optimal position size using Kelly Criterion.
    
    Uses Half Kelly for safety - proven to be more robust
    in real trading conditions.
    """
    
    def __init__(self):
        # Safety parameters
        self.kelly_fraction_multiplier = 0.5   # Half Kelly
        self.max_position_pct = 0.25           # Never more than 25% of balance
        self.min_position_usd = 10.0           # Minimum position
        self.max_risk_per_trade_pct = 0.02     # Max 2% of account at risk
        
        # Adjustments
        self.confidence_weight = 0.3           # How much confidence affects sizing
        self.volatility_weight = 0.2           # How much volatility affects sizing
    
    def calculate_kelly_fraction(
        self,
        win_rate: float,      # e.g., 0.65 (65%)
        avg_win: float,       # e.g., 50.0 ($50 avg win)
        avg_loss: float       # e.g., 30.0 ($30 avg loss)
    ) -> float:
        """
        Calculate the Kelly fraction.
        
        Kelly Formula: f* = (p * b - q) / b
        
        Example:
        - 65% win rate, avg win $50, avg loss $30
        - b = 50/30 = 1.67
        - f* = (0.65 * 1.67 - 0.35) / 1.67 = 0.44 (44% of bankroll)
        
        We use HALF Kelly for safety = 22%
        """
        if avg_loss == 0:
            return 0.0
        
        p = win_rate
        q = 1 - win_rate
        b = avg_win / avg_loss  # Win/loss ratio
        
        # Kelly formula
        if b == 0:
            return 0.0
        
        kelly = (p * b - q) / b
        
        # Kelly can be negative (don't trade)
        if kelly <= 0:
            return 0.0
        
        return kelly
    
    def get_position_size(
        self,
        balance: float,
        symbol: str,
        confidence: float,
        recent_performance: PerformanceStats,
        stop_distance_pct: float = 2.0,  # Default 2% stop
        volatility_factor: float = 1.0   # 1.0 = normal
    ) -> PositionSize:
        """
        Calculate optimal position size considering multiple factors.
        
        Steps:
        1. Calculate Kelly fraction from recent performance
        2. Apply Half Kelly multiplier
        3. Adjust for confidence level
        4. Adjust for volatility
        5. Apply drawdown reduction
        6. Cap at maximum limits
        """
        # 1. Calculate base Kelly fraction
        if recent_performance.total_trades < 5:
            # Not enough data, use conservative default
            kelly = 0.1
            reasoning = "Conservative sizing (insufficient trade history)"
        else:
            # Convert to percentages for calculation
            avg_win = recent_performance.avg_win_pct
            avg_loss = abs(recent_performance.avg_loss_pct)
            
            if avg_loss == 0:
                avg_loss = 2.0  # Default 2% loss
            if avg_win == 0:
                avg_win = 3.0  # Default 3% win
            
            kelly = self.calculate_kelly_fraction(
                win_rate=recent_performance.win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss
            )
            reasoning = f"Kelly fraction: {kelly:.2%} based on {recent_performance.win_rate:.0%} win rate"
        
        # 2. Apply Half Kelly
        applied = kelly * self.kelly_fraction_multiplier
        reasoning += f" → Half Kelly: {applied:.2%}"
        
        # 3. Confidence adjustment
        # Higher confidence = slightly larger, lower = smaller
        confidence_adj = 1.0 + (confidence - 70) / 100 * self.confidence_weight
        confidence_adj = max(0.7, min(1.3, confidence_adj))  # ±30%
        applied *= confidence_adj
        
        # 4. Volatility adjustment
        # Higher volatility = smaller positions
        volatility_adj = 1.0 / max(0.5, volatility_factor)
        volatility_adj = max(0.5, min(1.5, volatility_adj))
        applied *= volatility_adj
        
        # 5. Drawdown reduction
        # Reduce size after consecutive losses
        if recent_performance.consecutive_losses >= 3:
            drawdown_adj = 0.5  # Half size after 3 losses
            applied *= drawdown_adj
            reasoning += f" (reduced after {recent_performance.consecutive_losses} losses)"
        elif recent_performance.consecutive_losses >= 2:
            drawdown_adj = 0.75
            applied *= drawdown_adj
        
        # 6. Apply limits
        applied = min(applied, self.max_position_pct)
        applied = max(0.01, applied)  # At least 1%
        
        # Calculate actual position size
        size_usd = balance * applied
        size_usd = max(self.min_position_usd, size_usd)
        
        # Calculate max risk
        max_risk = size_usd * stop_distance_pct / 100
        
        # Ensure risk per trade limit
        max_allowed_risk = balance * self.max_risk_per_trade_pct
        if max_risk > max_allowed_risk:
            # Reduce position to keep risk within limits
            size_usd = max_allowed_risk / (stop_distance_pct / 100)
            applied = size_usd / balance
            reasoning += f" (capped by {self.max_risk_per_trade_pct*100}% max risk rule)"
        
        # Calculate recommended leverage
        # Position / Balance gives implied leverage
        leverage = min(3.0, size_usd / (balance * 0.33))  # Max 3x
        
        return PositionSize(
            size_usd=round(size_usd, 2),
            size_pct=round(applied * 100, 2),
            kelly_fraction=round(kelly, 4),
            applied_fraction=round(applied, 4),
            max_risk_usd=round(max_risk, 2),
            leverage=round(leverage, 1),
            reasoning=reasoning
        )
    
    def get_quick_size(
        self,
        balance: float,
        win_rate: float = 0.55,
        confidence: float = 80.0
    ) -> float:
        """
        Quick position size calculation with minimal inputs.
        
        Good for simple cases.
        """
        # Simplified Kelly with assumed 1.5:1 R:R
        kelly = (win_rate * 1.5 - (1 - win_rate)) / 1.5
        kelly = max(0, kelly)
        
        # Half Kelly
        applied = kelly * 0.5
        
        # Confidence adjustment
        confidence_factor = confidence / 100
        applied *= confidence_factor
        
        # Limits
        applied = min(0.20, max(0.02, applied))
        
        return balance * applied
    
    def should_trade(
        self,
        balance: float,
        performance: PerformanceStats
    ) -> tuple[bool, str]:
        """
        Check if position sizing recommends trading at all.
        
        Returns (should_trade, reason)
        """
        # Check for negative expectancy
        if performance.total_trades >= 10:
            if performance.win_rate < 0.4:
                return False, f"Win rate too low ({performance.win_rate:.0%})"
            
            # Calculate expectancy
            avg_win = performance.avg_win_pct
            avg_loss = abs(performance.avg_loss_pct)
            expectancy = (performance.win_rate * avg_win) - ((1 - performance.win_rate) * avg_loss)
            
            if expectancy <= 0:
                return False, f"Negative expectancy ({expectancy:.2%})"
        
        # Check consecutive losses
        if performance.consecutive_losses >= 5:
            return False, f"Too many consecutive losses ({performance.consecutive_losses})"
        
        # Check drawdown
        if performance.max_drawdown_pct >= 15:
            return False, f"Drawdown too high ({performance.max_drawdown_pct:.1%})"
        
        # Check minimum balance
        min_balance = 100
        if balance < min_balance:
            return False, f"Balance too low (${balance:.2f} < ${min_balance})"
        
        return True, "OK"


# Singleton
_position_sizer: Optional[KellyPositionSizer] = None


def get_position_sizer() -> KellyPositionSizer:
    """Get or create global position sizer."""
    global _position_sizer
    if _position_sizer is None:
        _position_sizer = KellyPositionSizer()
    return _position_sizer









