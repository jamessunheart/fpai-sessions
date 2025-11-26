#!/usr/bin/env python3
"""
🚪 EXIT ENGINE

Determines optimal exit points.

Exit Types:
A. At the Magnet - Exit when price hits magnet
B. Front-run the Magnet - Exit 0.1-0.3% before magnet
C. After Sweep Snapback - Exit after violent sweep + reversal

Exit Rules:
- NEVER long into a magnet above
- NEVER short into a magnet below
- Exit before magnet unless reversal conditions present
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExitType(str, Enum):
    MAGNET_HIT = "magnet_hit"
    FRONT_RUN = "front_run"
    SWEEP_SNAPBACK = "sweep_snapback"
    STOP_LOSS = "stop_loss"


@dataclass
class ExitSignal:
    """Exit signal"""
    exit_price: float
    exit_type: ExitType
    reason: str
    confidence: float  # 0-100


class ExitEngine:
    """
    Monitors position and generates exit signals.
    """
    
    def __init__(self,
                 front_run_pct: float = 0.002):  # 0.2% front-run
        self.front_run_pct = front_run_pct
    
    def check_exit(self,
                   position_entry: float,
                   position_stop: float,
                   position_target: float,
                   current_price: float,
                   magnet_price: float,
                   is_long: bool,
                   candles: list) -> Optional[ExitSignal]:
        """
        Check if exit signal should be generated.
        
        Returns ExitSignal or None.
        """
        
        # Check stop loss
        if is_long and current_price <= position_stop:
            return ExitSignal(
                exit_price=position_stop,
                exit_type=ExitType.STOP_LOSS,
                reason="Stop loss hit",
                confidence=100
            )
        elif not is_long and current_price >= position_stop:
            return ExitSignal(
                exit_price=position_stop,
                exit_type=ExitType.STOP_LOSS,
                reason="Stop loss hit",
                confidence=100
            )
        
        # Check magnet hit
        if self._is_magnet_hit(current_price, magnet_price, is_long):
            return ExitSignal(
                exit_price=magnet_price,
                exit_type=ExitType.MAGNET_HIT,
                reason="Magnet reached",
                confidence=90
            )
        
        # Check front-run zone
        if self._is_front_run_zone(current_price, magnet_price, is_long):
            return ExitSignal(
                exit_price=current_price,
                exit_type=ExitType.FRONT_RUN,
                reason="Front-running magnet to avoid reversal",
                confidence=85
            )
        
        # Check sweep snapback
        if len(candles) >= 2:
            if self._is_sweep_snapback(candles, is_long):
                return ExitSignal(
                    exit_price=current_price,
                    exit_type=ExitType.SWEEP_SNAPBACK,
                    reason="Violent sweep detected, exiting for reversal",
                    confidence=80
                )
        
        return None
    
    def _is_magnet_hit(self, current_price: float, 
                       magnet_price: float, is_long: bool) -> bool:
        """Check if magnet has been hit."""
        
        if is_long:
            return current_price >= magnet_price
        else:
            return current_price <= magnet_price
    
    def _is_front_run_zone(self, current_price: float,
                          magnet_price: float, is_long: bool) -> bool:
        """
        Check if we're in front-run zone (0.1-0.3% before magnet).
        """
        distance_pct = abs(current_price - magnet_price) / magnet_price
        
        if distance_pct <= self.front_run_pct:
            return True
        
        return False
    
    def _is_sweep_snapback(self, candles: list, is_long: bool) -> bool:
        """
        Detect violent sweep snapback.
        
        Signs:
        - Large wick rejection
        - Price closes opposite direction
        - High volume
        """
        if len(candles) < 2:
            return False
        
        latest = candles[-1]
        
        # Check for large wick
        if is_long:
            # Check upper wick (rejection from high)
            if latest.upper_wick > latest.body_size * 2:
                # Strong rejection
                if latest.close < latest.open:
                    # Closed bearish after sweep up
                    return True
        else:
            # Check lower wick (rejection from low)
            if latest.lower_wick > latest.body_size * 2:
                # Strong rejection
                if latest.close > latest.open:
                    # Closed bullish after sweep down
                    return True
        
        return False

