#!/usr/bin/env python3
"""
🚪 ENTRY ENGINE

Determines optimal entry zones and types.

Entry Types:
1. Momentum Entry - Enter with the whale after displacement
2. Retrace Entry - Enter on pullback into FVG/breaker
3. Reversal Entry - Enter after liquidity sweep (highest RR)

Only enter when:
- Whale direction is clear
- Magnet target is high probability
- Path is unobstructed
- Distance-to-target offers enough room
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from .flow_map import FlowPath
from .whale_engine import WhaleState, WhaleDirection


class EntryType(str, Enum):
    MOMENTUM = "momentum"
    RETRACE = "retrace"
    REVERSAL = "reversal"


@dataclass
class EntrySignal:
    """Entry signal with all details"""
    entry_price: float
    stop_loss: float
    target_price: float
    entry_type: EntryType
    size_multiplier: float  # Position size adjustment
    confidence: float  # 0-100
    reason: str
    
    @property
    def risk_reward(self) -> float:
        """Calculate R:R ratio"""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.target_price - self.entry_price)
        
        if risk == 0:
            return 0
        
        return reward / risk


class EntryEngine:
    """
    Generates entry signals based on whale state and flow path.
    """
    
    def __init__(self,
                 min_rr: float = 2.0,
                 min_distance_pct: float = 0.5):
        self.min_rr = min_rr
        self.min_distance_pct = min_distance_pct
    
    def generate_signal(self,
                       whale_state: WhaleState,
                       flow_path: FlowPath,
                       current_price: float,
                       candles: list) -> Optional[EntrySignal]:
        """
        Main entry signal generation.
        
        Returns EntrySignal or None if no valid entry.
        """
        if not flow_path:
            return None
        
        magnet = flow_path.selected_magnet
        
        # Check minimum distance
        if magnet.distance < self.min_distance_pct:
            return None
        
        # Determine entry type
        if self._is_reversal_setup(whale_state, candles):
            return self._generate_reversal_entry(
                whale_state, magnet, current_price, candles
            )
        
        elif self._is_retrace_setup(whale_state, candles, current_price):
            return self._generate_retrace_entry(
                whale_state, magnet, current_price, candles
            )
        
        elif self._is_momentum_setup(whale_state, flow_path):
            return self._generate_momentum_entry(
                whale_state, magnet, current_price, candles
            )
        
        return None
    
    def _is_momentum_setup(self, whale_state: WhaleState, flow_path: FlowPath) -> bool:
        """
        Momentum entry valid when:
        - High velocity
        - Just broke out
        - Magnet is close but not too close
        """
        if whale_state.velocity < 50:
            return False
        
        if flow_path.selected_magnet.distance > 3.0:
            return False
        
        if whale_state.confidence < 60:
            return False
        
        return True
    
    def _is_retrace_setup(self, whale_state: WhaleState, 
                         candles: list, current_price: float) -> bool:
        """
        Retrace entry valid when:
        - Recent strong move
        - Now pulling back
        - Into key level (FVG, breaker, etc.)
        """
        if len(candles) < 3:
            return False
        
        # Check for pullback
        recent = candles[-3:]
        
        if whale_state.direction == WhaleDirection.UP:
            # Looking for pullback in uptrend
            if recent[-1].close < recent[-2].close:
                return True
        else:
            # Looking for pullback in downtrend
            if recent[-1].close > recent[-2].close:
                return True
        
        return False
    
    def _is_reversal_setup(self, whale_state: WhaleState, candles: list) -> bool:
        """
        Reversal entry valid when:
        - Liquidity sweep occurred
        - Velocity stalls
        - Displacement flips
        """
        if whale_state.sweep_direction == "none":
            return False
        
        # Check velocity stall
        if whale_state.velocity > 50:
            return False
        
        return True
    
    def _generate_momentum_entry(self,
                                whale_state: WhaleState,
                                magnet,
                                current_price: float,
                                candles: list) -> Optional[EntrySignal]:
        """Generate momentum entry signal."""
        
        # Entry = current price
        entry = current_price
        
        # Stop = recent swing low/high
        if whale_state.direction == WhaleDirection.UP:
            stop = min(c.low for c in candles[-5:])
        else:
            stop = max(c.high for c in candles[-5:])
        
        # Target = magnet (with 0.2% front-run)
        target = magnet.price * 0.998 if whale_state.direction == WhaleDirection.UP else magnet.price * 1.002
        
        signal = EntrySignal(
            entry_price=entry,
            stop_loss=stop,
            target_price=target,
            entry_type=EntryType.MOMENTUM,
            size_multiplier=2.0,  # Aggressive
            confidence=whale_state.confidence * 0.8,
            reason=f"Momentum with {whale_state.direction.value} whale toward {magnet.type.value}"
        )
        
        if signal.risk_reward < self.min_rr:
            return None
        
        return signal
    
    def _generate_retrace_entry(self,
                               whale_state: WhaleState,
                               magnet,
                               current_price: float,
                               candles: list) -> Optional[EntrySignal]:
        """Generate retrace entry signal."""
        
        # Entry = on pullback into zone
        # Use 50% retracement as entry
        if whale_state.direction == WhaleDirection.UP:
            recent_high = max(c.high for c in candles[-5:])
            recent_low = min(c.low for c in candles[-10:-5])
            entry = (recent_high + recent_low) / 2
            stop = recent_low * 0.995
        else:
            recent_low = min(c.low for c in candles[-5:])
            recent_high = max(c.high for c in candles[-10:-5])
            entry = (recent_high + recent_low) / 2
            stop = recent_high * 1.005
        
        target = magnet.price * 0.998 if whale_state.direction == WhaleDirection.UP else magnet.price * 1.002
        
        signal = EntrySignal(
            entry_price=entry,
            stop_loss=stop,
            target_price=target,
            entry_type=EntryType.RETRACE,
            size_multiplier=1.5,
            confidence=whale_state.confidence * 0.7,
            reason=f"Retrace entry into {whale_state.direction.value} trend"
        )
        
        if signal.risk_reward < self.min_rr:
            return None
        
        return signal
    
    def _generate_reversal_entry(self,
                                whale_state: WhaleState,
                                magnet,
                                current_price: float,
                                candles: list) -> Optional[EntrySignal]:
        """Generate reversal entry signal (highest RR)."""
        
        # Entry = after sweep
        entry = current_price
        
        # Stop = beyond the sweep
        if whale_state.sweep_direction == "down":
            # Swept below, going up
            stop = whale_state.last_sweep_price * 0.995 if whale_state.last_sweep_price else current_price * 0.99
            direction_up = True
        else:
            # Swept above, going down
            stop = whale_state.last_sweep_price * 1.005 if whale_state.last_sweep_price else current_price * 1.01
            direction_up = False
        
        target = magnet.price * 0.998 if direction_up else magnet.price * 1.002
        
        signal = EntrySignal(
            entry_price=entry,
            stop_loss=stop,
            target_price=target,
            entry_type=EntryType.REVERSAL,
            size_multiplier=1.0,
            confidence=60,  # Reversal = lower frequency
            reason=f"Reversal after {whale_state.sweep_direction.value} sweep"
        )
        
        if signal.risk_reward < self.min_rr:
            return None
        
        return signal

