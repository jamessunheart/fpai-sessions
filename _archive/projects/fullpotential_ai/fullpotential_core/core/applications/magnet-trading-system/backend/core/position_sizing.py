"""
POSITION SIZING ENGINE v1.1
Formula: Position = (Equity × Risk% × L) / Stop Distance
Complete production-ready implementation
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class AccountState:
    """Current account state"""
    equity: float
    available_margin: float
    open_positions_value: float


@dataclass
class TradeSetup:
    """Proposed trade details"""
    entry_price: float
    stop_price: float
    magnet_price: float
    magnet_tier: int  # 1-4
    leverage: float


@dataclass
class SizingConfig:
    """Risk management configuration"""
    risk_per_trade_pct: float = 1.0
    max_position_pct: float = 20.0
    max_total_exposure_pct: float = 50.0
    tier1_max_pct: float = 15.0
    tier2_max_pct: float = 10.0
    tier3_max_pct: float = 5.0
    tier4_max_pct: float = 2.0


class PositionSizer:
    """Calculates optimal position sizes with survival constraints"""

    def __init__(self, config: Optional[SizingConfig] = None):
        self.config = config or SizingConfig()

    def calculate_position_size(self, account: AccountState, trade: TradeSetup) -> dict:
        """Calculate safe position size"""
        # Calculate stop distance
        stop_distance_pct = abs(trade.entry_price - trade.stop_price) / trade.entry_price

        if stop_distance_pct == 0:
            return {'position_size': 0, 'safe_to_trade': False}

        # Risk amount
        risk_amount = account.equity * (self.config.risk_per_trade_pct / 100.0)

        # Base position: (Risk × Leverage) / Stop Distance
        base_position = (risk_amount * trade.leverage) / stop_distance_pct

        # Apply tier limits
        tier_limit = self._get_tier_limit(trade.magnet_tier)
        tier_max = account.equity * (tier_limit / 100.0)
        max_position = account.equity * (self.config.max_position_pct / 100.0)

        final_position = min(base_position, tier_max, max_position)

        # Check total exposure
        total_exposure = account.open_positions_value + final_position
        max_exposure = account.equity * (self.config.max_total_exposure_pct / 100.0)

        exposure_exceeded = total_exposure > max_exposure
        if exposure_exceeded:
            allowed_additional = max(0, max_exposure - account.open_positions_value)
            final_position = min(final_position, allowed_additional)

        # Calculate metrics
        actual_risk = (final_position * stop_distance_pct) / trade.leverage
        actual_risk_pct = (actual_risk / account.equity) * 100

        reward_distance_pct = abs(trade.magnet_price - trade.entry_price) / trade.entry_price
        potential_reward = (final_position * reward_distance_pct) / trade.leverage
        risk_reward_ratio = potential_reward / actual_risk if actual_risk > 0 else 0

        return {
            'position_size': round(final_position, 2),
            'position_pct': round((final_position / account.equity) * 100, 2),
            'actual_risk': round(actual_risk, 2),
            'actual_risk_pct': round(actual_risk_pct, 2),
            'potential_reward': round(potential_reward, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'safe_to_trade': not exposure_exceeded and final_position > 0
        }

    def _get_tier_limit(self, tier: int) -> float:
        """Get max position % for magnet tier"""
        return {
            1: self.config.tier1_max_pct,
            2: self.config.tier2_max_pct,
            3: self.config.tier3_max_pct,
            4: self.config.tier4_max_pct
        }.get(tier, self.config.tier4_max_pct)
