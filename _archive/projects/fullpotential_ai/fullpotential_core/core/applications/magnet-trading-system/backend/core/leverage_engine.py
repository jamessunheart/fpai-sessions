"""
MAGNET-AWARE LEVERAGE ENGINE v1.1
Formula: L = (D × S) / (1 + C + V)
Complete production-ready implementation
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class MagnetState:
    """Input state for leverage calculation"""
    primary_magnet_price: float
    current_price: float
    magnet_strength: float          # S: 0-100 score
    conflict_index: float           # C: 0-1+ (competing magnets)
    volatility_pressure: float      # V: 0-1+ (market stress)
    atr: float                      # Average True Range


@dataclass
class LeverageConfig:
    """Configuration bounds for leverage"""
    min_leverage: float = 1.0
    max_leverage: float = 2.5
    high_tension_max: float = 3.0
    high_tension_threshold: float = 0.15
    min_magnet_strength: float = 60.0


class LeverageEngine:
    """
    Core engine for calculating safe, dynamic leverage.
    Ensures the fund survives by scaling risk with opportunity.
    """

    def __init__(self, config: Optional[LeverageConfig] = None):
        self.config = config or LeverageConfig()

    def calculate_distance(self, state: MagnetState) -> float:
        """Calculate normalized distance: D = |Current - Magnet| / ATR"""
        raw_distance = abs(state.current_price - state.primary_magnet_price)
        return raw_distance / state.atr if state.atr > 0 else 0

    def calculate_leverage(self, state: MagnetState) -> dict:
        """
        Calculate optimal leverage: L = (D × S) / (1 + C + V)
        Returns: dict with leverage, components, and reasoning
        """
        D = self.calculate_distance(state)
        S = state.magnet_strength / 100.0
        C = state.conflict_index
        V = state.volatility_pressure

        # Core formula
        raw_leverage = (D * S) / (1 + C + V)
        leverage = np.clip(raw_leverage, self.config.min_leverage, self.config.max_leverage)

        # High-tension override (perfect setup)
        total_friction = C + V
        is_high_tension = (
            total_friction < self.config.high_tension_threshold and
            state.magnet_strength >= self.config.min_magnet_strength
        )

        if is_high_tension:
            leverage = min(leverage * 1.2, self.config.high_tension_max)

        return {
            'leverage': round(leverage, 2),
            'components': {
                'distance': round(D, 2),
                'strength': round(S, 2),
                'conflict': round(C, 2),
                'volatility': round(V, 2)
            },
            'raw_leverage': round(raw_leverage, 2),
            'is_high_tension': is_high_tension,
            'reasoning': self._generate_reasoning(D, S, C, V, is_high_tension)
        }

    def _generate_reasoning(self, D, S, C, V, is_high_tension) -> str:
        """Generate human-readable reasoning"""
        reasons = []
        if D > 3: reasons.append("High tension (far from magnet)")
        if S > 0.75: reasons.append("Strong magnet")
        if C > 0.5: reasons.append("High conflict")
        if V > 1.5: reasons.append("High volatility")
        if is_high_tension: reasons.append("PERFECT SETUP")
        return " | ".join(reasons) or "Normal conditions"
