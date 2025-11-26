#!/usr/bin/env python3
"""
🔄 REVERSAL ENGINE

Identifies high-probability reversals after liquidity sweeps.

Reversal Conditions:
- Magnet fully swept
- Large wick rejection
- Whale velocity shifts
- Displacement breaks structure
- Candle body closes opposite direction

Reversal Signals:
- BOS (Break of Structure)
- CHoCH (Change of Character)
- Break of countertrend structure
- Imbalance fill
- Delta reversal

Reversal trades = low frequency, high precision
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class ReversalType(str, Enum):
    BOS = "break_of_structure"
    CHOCH = "change_of_character"
    SWEEP_REVERSAL = "sweep_reversal"
    IMBALANCE_FILL = "imbalance_fill"


@dataclass
class ReversalSignal:
    """Reversal opportunity"""
    reversal_price: float
    reversal_type: ReversalType
    new_direction: str  # "up" or "down"
    confidence: float  # 0-100
    reason: str
    entry_zone: float
    stop_loss: float
    target: float


class ReversalEngine:
    """
    Detects and signals reversal opportunities.
    """
    
    def __init__(self,
                 min_wick_ratio: float = 2.0,
                 structure_lookback: int = 10):
        self.min_wick_ratio = min_wick_ratio
        self.structure_lookback = structure_lookback
    
    def detect_reversal(self,
                       candles: List,
                       whale_state,
                       magnet_price: Optional[float] = None) -> Optional[ReversalSignal]:
        """
        Main reversal detection.
        
        Returns ReversalSignal or None.
        """
        if len(candles) < 5:
            return None
        
        # Check sweep reversal
        sweep_rev = self._detect_sweep_reversal(candles, magnet_price)
        if sweep_rev:
            return sweep_rev
        
        # Check BOS
        bos = self._detect_bos(candles)
        if bos:
            return bos
        
        # Check CHoCH
        choch = self._detect_choch(candles)
        if choch:
            return choch
        
        return None
    
    def _detect_sweep_reversal(self, 
                               candles: List,
                               magnet_price: Optional[float]) -> Optional[ReversalSignal]:
        """
        Detect reversal after magnet sweep.
        
        Conditions:
        - Price swept magnet
        - Large wick rejection
        - Body closes back opposite
        """
        latest = candles[-1]
        
        # Check for large wick
        has_upper_wick = latest.upper_wick > latest.body_size * self.min_wick_ratio
        has_lower_wick = latest.lower_wick > latest.body_size * self.min_wick_ratio
        
        if not (has_upper_wick or has_lower_wick):
            return None
        
        # Determine reversal direction
        if has_upper_wick and latest.close < latest.open:
            # Swept high, closed bearish = reversal down
            new_direction = "down"
            swept_price = latest.high
            entry = latest.close
            stop = latest.high * 1.005
            target = min(c.low for c in candles[-5:]) * 0.995
        
        elif has_lower_wick and latest.close > latest.open:
            # Swept low, closed bullish = reversal up
            new_direction = "up"
            swept_price = latest.low
            entry = latest.close
            stop = latest.low * 0.995
            target = max(c.high for c in candles[-5:]) * 1.005
        
        else:
            return None
        
        # Check if magnet was swept
        confidence = 75
        if magnet_price:
            if abs(swept_price - magnet_price) / magnet_price < 0.003:
                confidence = 90  # Magnet was hit = high confidence reversal
        
        return ReversalSignal(
            reversal_price=swept_price,
            reversal_type=ReversalType.SWEEP_REVERSAL,
            new_direction=new_direction,
            confidence=confidence,
            reason=f"Sweep reversal at {swept_price:.2f} with large wick rejection",
            entry_zone=entry,
            stop_loss=stop,
            target=target
        )
    
    def _detect_bos(self, candles: List) -> Optional[ReversalSignal]:
        """
        Detect Break of Structure.
        
        BOS = price breaks significant swing high/low
        """
        if len(candles) < self.structure_lookback:
            return None
        
        recent = candles[-self.structure_lookback:]
        latest = candles[-1]
        
        # Get swing high and low
        swing_high = max(c.high for c in recent[:-1])
        swing_low = min(c.low for c in recent[:-1])
        
        # Check for break up
        if latest.close > swing_high:
            return ReversalSignal(
                reversal_price=swing_high,
                reversal_type=ReversalType.BOS,
                new_direction="up",
                confidence=70,
                reason=f"BOS: Broke above {swing_high:.2f}",
                entry_zone=latest.close,
                stop_loss=swing_low,
                target=swing_high + (swing_high - swing_low)  # Same range projection
            )
        
        # Check for break down
        if latest.close < swing_low:
            return ReversalSignal(
                reversal_price=swing_low,
                reversal_type=ReversalType.BOS,
                new_direction="down",
                confidence=70,
                reason=f"BOS: Broke below {swing_low:.2f}",
                entry_zone=latest.close,
                stop_loss=swing_high,
                target=swing_low - (swing_high - swing_low)
            )
        
        return None
    
    def _detect_choch(self, candles: List) -> Optional[ReversalSignal]:
        """
        Detect Change of Character.
        
        CHoCH = shift in market behavior (e.g., from HH to LL)
        """
        if len(candles) < 6:
            return None
        
        # Get last 6 candles
        recent = candles[-6:]
        
        # Check for trend shift
        first_half = recent[:3]
        second_half = recent[3:]
        
        first_trend = self._get_trend(first_half)
        second_trend = self._get_trend(second_half)
        
        if first_trend != second_trend and first_trend != "neutral" and second_trend != "neutral":
            # Trend changed
            latest = candles[-1]
            
            if second_trend == "up":
                return ReversalSignal(
                    reversal_price=latest.close,
                    reversal_type=ReversalType.CHOCH,
                    new_direction="up",
                    confidence=65,
                    reason="Change of Character: Shift to bullish",
                    entry_zone=latest.close,
                    stop_loss=min(c.low for c in second_half) * 0.995,
                    target=max(c.high for c in recent) * 1.01
                )
            else:
                return ReversalSignal(
                    reversal_price=latest.close,
                    reversal_type=ReversalType.CHOCH,
                    new_direction="down",
                    confidence=65,
                    reason="Change of Character: Shift to bearish",
                    entry_zone=latest.close,
                    stop_loss=max(c.high for c in second_half) * 1.005,
                    target=min(c.low for c in recent) * 0.99
                )
        
        return None
    
    def _get_trend(self, candles: List) -> str:
        """Determine trend direction of candles."""
        if len(candles) < 2:
            return "neutral"
        
        closes = [c.close for c in candles]
        
        if all(closes[i] > closes[i-1] for i in range(1, len(closes))):
            return "up"
        elif all(closes[i] < closes[i-1] for i in range(1, len(closes))):
            return "down"
        else:
            return "neutral"

