"""
SURVIVAL FUSE SYSTEM v1.1
Circuit breaker for capital protection
Complete production-ready implementation
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
import time


class FuseState(Enum):
    """Current fuse state"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    COOLDOWN = "cooldown"


class FuseTrigger(Enum):
    """Trigger types"""
    VOLATILITY_SPIKE = "volatility_spike"
    DRAWDOWN_BREACH = "drawdown_breach"
    MAGNET_CONFLICT = "magnet_conflict"
    LIQUIDITY_DRY = "liquidity_dry"
    TREND_FLIP = "trend_flip"


@dataclass
class FuseConfig:
    """Fuse configuration"""
    max_volatility: float = 2.0
    max_drawdown_pct: float = 5.0
    max_conflict_index: float = 0.8
    reduction_pct_min: float = 0.3
    reduction_pct_max: float = 0.7
    fuse_leverage: float = 1.0
    cooldown_seconds: int = 300
    halt_new_trades: bool = True
    halt_duration_seconds: int = 180


@dataclass
class MarketConditions:
    """Market state for fuse evaluation"""
    volatility_pressure: float
    account_drawdown_pct: float
    conflict_index: float
    primary_magnet_strength: float
    secondary_magnet_strength: float
    trend_aligned: bool
    liquidity_score: float


class SurvivalFuse:
    """Sacred protection system that ensures fund survival"""

    def __init__(self, config: Optional[FuseConfig] = None):
        self.config = config or FuseConfig()
        self.state = FuseState.ACTIVE
        self.triggered_at: Optional[float] = None
        self.trigger_history: List[tuple] = []

    def check_triggers(self, conditions: MarketConditions) -> dict:
        """Evaluate conditions against fuse thresholds"""
        triggers = []

        if conditions.volatility_pressure > self.config.max_volatility:
            triggers.append(FuseTrigger.VOLATILITY_SPIKE)
        if conditions.account_drawdown_pct > self.config.max_drawdown_pct:
            triggers.append(FuseTrigger.DRAWDOWN_BREACH)
        if conditions.conflict_index > self.config.max_conflict_index:
            triggers.append(FuseTrigger.MAGNET_CONFLICT)
        if conditions.secondary_magnet_strength > conditions.primary_magnet_strength:
            triggers.append(FuseTrigger.MAGNET_CONFLICT)
        if not conditions.trend_aligned:
            triggers.append(FuseTrigger.TREND_FLIP)
        if conditions.liquidity_score < 30:
            triggers.append(FuseTrigger.LIQUIDITY_DRY)

        should_trigger = len(triggers) > 0 and self.state == FuseState.ACTIVE

        if should_trigger:
            self._trigger_fuse(triggers)

        return {
            'triggered': should_trigger,
            'current_state': self.state.value,
            'triggers': [t.value for t in triggers],
            'actions': self._get_actions() if should_trigger else [],
            'time_until_reset': self._time_until_reset()
        }

    def _trigger_fuse(self, triggers: List[FuseTrigger]):
        """Activate the fuse"""
        self.state = FuseState.TRIGGERED
        self.triggered_at = time.time()
        self.trigger_history.append((time.time(), triggers))

    def _get_actions(self) -> List[str]:
        """Get mandatory actions"""
        return [
            f"Reduce position by {self.config.reduction_pct_min*100:.0f}-{self.config.reduction_pct_max*100:.0f}%",
            f"Cut leverage to {self.config.fuse_leverage}x",
            f"Halt new trades for {self.config.halt_duration_seconds}s",
            "Recalculate magnet hierarchy",
            "Reset bias to neutral"
        ]

    def _time_until_reset(self) -> Optional[int]:
        """Calculate seconds remaining until reset"""
        if self.state != FuseState.TRIGGERED or self.triggered_at is None:
            return None
        elapsed = time.time() - self.triggered_at
        remaining = max(0, self.config.cooldown_seconds - elapsed)
        if remaining == 0:
            self.state = FuseState.COOLDOWN
        return int(remaining)

    def manual_reset(self):
        """Manually reset fuse"""
        self.state = FuseState.ACTIVE
        self.triggered_at = None
