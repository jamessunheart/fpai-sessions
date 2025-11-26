#!/usr/bin/env python3
"""
🐋 WHALE POSITION ENGINE

Determines whale intention: UP, DOWN, or FOG (indecision)

Logic:
- Analyzes last sweep direction
- Displacement strength
- Candle velocity
- Orderflow pressure
- Liquidity taken/not taken
- Structure (HH/HL vs LH/LL)
- Wick aggression
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import numpy as np


class WhaleDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FOG = "fog"


class SweepDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    NONE = "none"


@dataclass
class Candle:
    """OHLCV candle"""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def range(self) -> float:
        return self.high - self.low


@dataclass
class WhaleState:
    """Current whale position and intention"""
    direction: WhaleDirection
    velocity: float  # 0-100
    displacement_score: float  # 0-100
    sweep_direction: SweepDirection
    confidence: float  # 0-100
    last_sweep_price: Optional[float] = None


class WhalePositionEngine:
    """
    Analyzes market data to determine whale position.
    
    Output: WhaleState with direction and confidence
    """
    
    def __init__(self, 
                 velocity_window: int = 5,
                 displacement_threshold: float = 0.3,
                 fog_threshold: float = 40):
        self.velocity_window = velocity_window
        self.displacement_threshold = displacement_threshold
        self.fog_threshold = fog_threshold
    
    def analyze(self, candles: List[Candle]) -> WhaleState:
        """
        Main analysis function.
        
        Returns WhaleState with direction, velocity, and confidence.
        """
        if len(candles) < self.velocity_window:
            return WhaleState(
                direction=WhaleDirection.FOG,
                velocity=0,
                displacement_score=0,
                sweep_direction=SweepDirection.NONE,
                confidence=0
            )
        
        # Calculate components
        velocity = self._calculate_velocity(candles)
        displacement = self._calculate_displacement(candles)
        sweep_dir = self._detect_sweep(candles)
        structure = self._analyze_structure(candles)
        wick_aggression = self._calculate_wick_aggression(candles)
        
        # Combine signals
        up_score = 0
        down_score = 0
        
        # Displacement
        if displacement > self.displacement_threshold:
            latest = candles[-1]
            if latest.is_bullish:
                up_score += 30
            else:
                down_score += 30
        
        # Velocity
        if velocity > 60:
            # High velocity = continuation
            if candles[-1].is_bullish:
                up_score += 20
            else:
                down_score += 20
        
        # Sweep
        if sweep_dir == SweepDirection.DOWN:
            # Swept below = going up
            up_score += 25
        elif sweep_dir == SweepDirection.UP:
            # Swept above = going down
            down_score += 25
        
        # Structure
        if structure == "HH":
            up_score += 15
        elif structure == "LL":
            down_score += 15
        
        # Wick aggression
        if wick_aggression > 50:
            # Strong rejection
            if candles[-1].lower_wick > candles[-1].upper_wick:
                up_score += 10
            else:
                down_score += 10
        
        # Determine direction
        confidence = abs(up_score - down_score)
        
        if confidence < self.fog_threshold:
            direction = WhaleDirection.FOG
        elif up_score > down_score:
            direction = WhaleDirection.UP
        else:
            direction = WhaleDirection.DOWN
        
        return WhaleState(
            direction=direction,
            velocity=velocity,
            displacement_score=displacement * 100,
            sweep_direction=sweep_dir,
            confidence=min(confidence, 100),
            last_sweep_price=self._get_last_sweep_price(candles, sweep_dir)
        )
    
    def _calculate_velocity(self, candles: List[Candle]) -> float:
        """
        Velocity = rate of change in displacement.
        0-100 scale.
        """
        recent = candles[-self.velocity_window:]
        
        # Calculate average body size vs range
        body_ratios = [c.body_size / c.range if c.range > 0 else 0 for c in recent]
        avg_ratio = np.mean(body_ratios)
        
        # Calculate price movement speed
        price_change = abs(recent[-1].close - recent[0].open)
        avg_range = np.mean([c.range for c in recent])
        
        if avg_range == 0:
            return 0
        
        velocity_raw = (price_change / avg_range) * avg_ratio * 100
        
        return min(velocity_raw, 100)
    
    def _calculate_displacement(self, candles: List[Candle]) -> float:
        """
        Displacement = strong directional move with volume.
        Returns 0-1 score.
        """
        recent = candles[-3:]
        
        # Check for consecutive strong bodies
        strong_bodies = sum(1 for c in recent if c.body_size / c.range > 0.6)
        
        if strong_bodies >= 2:
            # Strong displacement
            return 0.8
        elif strong_bodies == 1:
            return 0.4
        else:
            return 0.1
    
    def _detect_sweep(self, candles: List[Candle]) -> SweepDirection:
        """
        Detect if recent candles swept liquidity above or below.
        
        Sweep = wick extends beyond previous structure then closes back.
        """
        if len(candles) < 5:
            return SweepDirection.NONE
        
        recent = candles[-5:]
        latest = recent[-1]
        
        # Get recent high/low
        recent_high = max(c.high for c in recent[:-1])
        recent_low = min(c.low for c in recent[:-1])
        
        # Check for sweep above
        if latest.high > recent_high and latest.close < recent_high:
            # Swept above and closed back = bearish sweep
            return SweepDirection.UP
        
        # Check for sweep below
        if latest.low < recent_low and latest.close > recent_low:
            # Swept below and closed back = bullish sweep
            return SweepDirection.DOWN
        
        return SweepDirection.NONE
    
    def _analyze_structure(self, candles: List[Candle]) -> str:
        """
        Analyze market structure: HH (higher highs), LL (lower lows), or CHOP.
        """
        if len(candles) < 3:
            return "CHOP"
        
        recent = candles[-3:]
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        
        if highs[-1] > highs[-2] > highs[-3]:
            return "HH"
        elif lows[-1] < lows[-2] < lows[-3]:
            return "LL"
        else:
            return "CHOP"
    
    def _calculate_wick_aggression(self, candles: List[Candle]) -> float:
        """
        Wick aggression = rejection strength.
        0-100 scale.
        """
        latest = candles[-1]
        
        total_wick = latest.upper_wick + latest.lower_wick
        if latest.range == 0:
            return 0
        
        wick_ratio = total_wick / latest.range
        
        return wick_ratio * 100
    
    def _get_last_sweep_price(self, candles: List[Candle], 
                              sweep_dir: SweepDirection) -> Optional[float]:
        """Get the price level that was swept."""
        if sweep_dir == SweepDirection.NONE:
            return None
        
        if len(candles) < 2:
            return None
        
        if sweep_dir == SweepDirection.UP:
            return candles[-1].high
        else:
            return candles[-1].low

