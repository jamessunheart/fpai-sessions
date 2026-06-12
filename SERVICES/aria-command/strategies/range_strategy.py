#!/usr/bin/env python3
"""
RANGE TRADING STRATEGY
======================
Buys at lower band, sells at upper band.
Best for sideways/choppy markets.
"""
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("strategy.range")

@dataclass
class RangeConfig:
    """Range strategy configuration"""
    # Band detection
    lookback_hours: int = 48
    min_range_width_pct: float = 4.0    # Minimum 4% range to trade
    max_range_width_pct: float = 15.0   # Max 15% (beyond this, trend trading better)
    
    # Entry triggers  
    band_touch_pct: float = 1.5         # Within 1.5% of band = "touching"
    lower_band_rsi: float = 35.0        # RSI must be below this at lower band
    upper_band_rsi: float = 65.0        # RSI must be above this at upper band
    
    # Exits
    take_profit_target: str = "middle"  # "middle" or "opposite"
    stop_outside_band_pct: float = 1.5  # Stop 1.5% outside band
    
    # Position sizing
    position_pct: float = 30.0          # 30% of account per range trade
    
    # Confidence thresholds
    min_confidence: int = 70            # Minimum confidence to trade


class RangeStrategy:
    """
    Range/Mean Reversion Strategy
    
    Best when:
    - Market is consolidating (no clear trend)
    - Range width between 4-15%
    - Clear support and resistance levels
    
    Avoid when:
    - Strong trending market
    - Range too tight (<4%) or too wide (>15%)
    - Breaking out of established range
    """
    
    def __init__(self, config: RangeConfig = None):
        self.config = config or RangeConfig()
        self.name = "RANGE"
    
    def detect_range(self, candles: list) -> Dict:
        """Detect trading range from candles"""
        lookback = min(len(candles), self.config.lookback_hours)
        candles = candles[-lookback:]
        
        highs = [float(c["h"]) for c in candles]
        lows = [float(c["l"]) for c in candles]
        
        upper = max(highs)
        lower = min(lows)
        middle = (upper + lower) / 2
        width_pct = ((upper - lower) / middle) * 100
        
        # Check if range is tradeable
        is_valid = (
            self.config.min_range_width_pct <= width_pct <= self.config.max_range_width_pct
        )
        
        return {
            "upper": upper,
            "lower": lower, 
            "middle": middle,
            "width_pct": width_pct,
            "is_valid": is_valid,
            "reason": self._range_validity_reason(width_pct)
        }
    
    def _range_validity_reason(self, width: float) -> str:
        if width < self.config.min_range_width_pct:
            return f"Range too tight ({width:.1f}% < {self.config.min_range_width_pct}%)"
        elif width > self.config.max_range_width_pct:
            return f"Range too wide ({width:.1f}% > {self.config.max_range_width_pct}%)"
        return "Valid range"
    
    def analyze(self, price: float, rsi: float, candles: list) -> Dict:
        """
        Analyze current setup for range trading opportunity
        
        Returns:
            signal: BUY, SHORT, CLOSE_LONG, CLOSE_SHORT, or WAIT
            confidence: 0-100
            entry, stop, target prices
        """
        range_data = self.detect_range(candles)
        
        if not range_data["is_valid"]:
            return {
                "signal": "SKIP",
                "confidence": 0,
                "reason": range_data["reason"],
                "strategy": self.name
            }
        
        upper = range_data["upper"]
        lower = range_data["lower"]
        middle = range_data["middle"]
        
        # Calculate distances
        dist_to_lower = ((price - lower) / price) * 100
        dist_to_upper = ((upper - price) / price) * 100
        
        # Determine zone
        at_lower = dist_to_lower < self.config.band_touch_pct
        at_upper = dist_to_upper < self.config.band_touch_pct
        
        # Generate signal
        signal = "WAIT"
        confidence = 0
        entry = None
        stop = None
        target = None
        reason = ""
        
        if at_lower and rsi < self.config.lower_band_rsi:
            signal = "BUY"
            # Higher confidence for more oversold RSI
            confidence = min(95, 60 + int((self.config.lower_band_rsi - rsi) * 1.5))
            entry = price
            stop = lower * (1 - self.config.stop_outside_band_pct / 100)
            target = middle if self.config.take_profit_target == "middle" else upper
            reason = f"At lower band (${lower:.2f}) with oversold RSI ({rsi:.1f})"
            
        elif at_upper and rsi > self.config.upper_band_rsi:
            signal = "SHORT"
            confidence = min(95, 60 + int((rsi - self.config.upper_band_rsi) * 1.5))
            entry = price
            stop = upper * (1 + self.config.stop_outside_band_pct / 100)
            target = middle if self.config.take_profit_target == "middle" else lower
            reason = f"At upper band (${upper:.2f}) with overbought RSI ({rsi:.1f})"
            
        else:
            confidence = 20
            reason = f"Not at band edges (lower: {dist_to_lower:.1f}%, upper: {dist_to_upper:.1f}%)"
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry": entry,
            "stop": stop,
            "target": target,
            "reason": reason,
            "strategy": self.name,
            "range": range_data,
            "zone": "lower" if at_lower else ("upper" if at_upper else "middle"),
            "rsi": rsi
        }
    
    def should_exit(self, position: Dict, price: float, rsi: float, candles: list) -> Tuple[bool, str]:
        """Check if we should exit an existing range trade"""
        range_data = self.detect_range(candles)
        middle = range_data["middle"]
        
        side = position.get("side", "").lower()
        
        # Check target hit
        if side == "long":
            if price >= middle:
                return True, f"Target reached (middle: ${middle:.2f})"
            if rsi > 60:
                return True, f"RSI overbought ({rsi:.1f})"
        elif side == "short":
            if price <= middle:
                return True, f"Target reached (middle: ${middle:.2f})"
            if rsi < 40:
                return True, f"RSI oversold ({rsi:.1f})"
        
        return False, ""
    
    def get_position_size(self, account_value: float, entry: float, stop: float) -> float:
        """Calculate position size based on risk"""
        risk_pct = self.config.position_pct / 100
        risk_amount = account_value * risk_pct
        risk_per_unit = abs(entry - stop)
        
        if risk_per_unit == 0:
            return 0
        
        size = risk_amount / risk_per_unit
        return size


def is_range_market(candles: list, lookback: int = 48) -> Tuple[bool, str]:
    """
    Determine if current market is suitable for range trading
    
    Returns (is_range_market, reason)
    """
    if len(candles) < lookback:
        return False, "Insufficient data"
    
    recent = candles[-lookback:]
    closes = [float(c["c"]) for c in recent]
    highs = [float(c["h"]) for c in recent]
    lows = [float(c["l"]) for c in recent]
    
    # Calculate range
    high = max(highs)
    low = min(lows)
    range_pct = ((high - low) / ((high + low) / 2)) * 100
    
    # Check trend strength (using linear regression slope)
    n = len(closes)
    x_mean = (n - 1) / 2
    y_mean = sum(closes) / n
    
    numerator = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    
    slope = numerator / denominator if denominator != 0 else 0
    slope_pct = (slope / y_mean) * 100 * n  # Normalize to % over period
    
    # Range market criteria:
    # - Range between 4-15%
    # - Slope relatively flat (< 8% over period)
    
    is_range = 4 <= range_pct <= 15 and abs(slope_pct) < 8
    
    if range_pct < 4:
        reason = f"Too tight ({range_pct:.1f}%)"
    elif range_pct > 15:
        reason = f"Too wide ({range_pct:.1f}%)"
    elif abs(slope_pct) >= 8:
        direction = "up" if slope_pct > 0 else "down"
        reason = f"Trending {direction} ({slope_pct:+.1f}%)"
    else:
        reason = f"Good range ({range_pct:.1f}%, slope: {slope_pct:+.1f}%)"
    
    return is_range, reason








