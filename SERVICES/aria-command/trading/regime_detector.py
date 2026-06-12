#!/usr/bin/env python3
"""
📊 MARKET REGIME DETECTOR
==========================

Detects current market conditions for strategy adaptation:
- Trend detection (strong/weak up/down)
- Volatility classification
- Range vs trend identification

Adapts trading parameters based on regime:
- Position sizes
- Stop distances
- Entry/exit aggressiveness
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("aria.trading.regime")


class MarketRegime(Enum):
    """Market regime classification."""
    STRONG_UPTREND = "strong_uptrend"
    WEAK_UPTREND = "weak_uptrend"
    RANGING = "ranging"
    WEAK_DOWNTREND = "weak_downtrend"
    STRONG_DOWNTREND = "strong_downtrend"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class RegimeAdjustments:
    """Trading adjustments for a market regime."""
    position_size_multiplier: float = 1.0   # Adjust position size
    stop_distance_multiplier: float = 1.0   # Adjust stop distance
    confidence_threshold_adj: float = 0.0    # Adjust confidence threshold
    prefer_direction: str = "neutral"        # long, short, or neutral bias
    entry_aggression: float = 1.0           # How aggressive on entries
    exit_aggression: float = 1.0            # How aggressive on exits
    description: str = ""


@dataclass
class PriceData:
    """Price data point for analysis."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class RegimeDetector:
    """
    Detects current market regime for strategy adaptation.
    
    Uses simple price action analysis:
    - Trend direction and strength
    - Volatility level
    - Support/resistance behavior
    """
    
    # Regime adjustments configuration
    REGIME_ADJUSTMENTS = {
        MarketRegime.STRONG_UPTREND: RegimeAdjustments(
            position_size_multiplier=1.2,    # Larger positions
            stop_distance_multiplier=1.3,    # Wider stops for pullbacks
            confidence_threshold_adj=-5.0,   # Lower threshold (easier entries)
            prefer_direction="long",
            entry_aggression=1.2,
            exit_aggression=0.8,             # Less aggressive exits
            description="Strong uptrend - favor longs, wider stops"
        ),
        MarketRegime.WEAK_UPTREND: RegimeAdjustments(
            position_size_multiplier=1.0,
            stop_distance_multiplier=1.0,
            confidence_threshold_adj=0.0,
            prefer_direction="long",
            entry_aggression=1.0,
            exit_aggression=1.0,
            description="Weak uptrend - standard parameters, slight long bias"
        ),
        MarketRegime.RANGING: RegimeAdjustments(
            position_size_multiplier=0.8,    # Smaller positions
            stop_distance_multiplier=0.8,    # Tighter stops
            confidence_threshold_adj=+5.0,   # Higher threshold
            prefer_direction="neutral",
            entry_aggression=0.8,
            exit_aggression=1.2,             # More aggressive exits
            description="Ranging market - smaller positions, tighter stops"
        ),
        MarketRegime.WEAK_DOWNTREND: RegimeAdjustments(
            position_size_multiplier=1.0,
            stop_distance_multiplier=1.0,
            confidence_threshold_adj=0.0,
            prefer_direction="short",
            entry_aggression=1.0,
            exit_aggression=1.0,
            description="Weak downtrend - standard parameters, slight short bias"
        ),
        MarketRegime.STRONG_DOWNTREND: RegimeAdjustments(
            position_size_multiplier=0.8,    # Smaller positions (volatility)
            stop_distance_multiplier=1.3,    # Wider stops
            confidence_threshold_adj=-5.0,
            prefer_direction="short",
            entry_aggression=1.2,
            exit_aggression=0.8,
            description="Strong downtrend - favor shorts, wider stops"
        ),
        MarketRegime.HIGH_VOLATILITY: RegimeAdjustments(
            position_size_multiplier=0.5,    # Much smaller positions
            stop_distance_multiplier=1.5,    # Much wider stops
            confidence_threshold_adj=+10.0,  # Much higher threshold
            prefer_direction="neutral",
            entry_aggression=0.7,
            exit_aggression=1.5,             # Very aggressive exits
            description="High volatility - half positions, wider stops"
        ),
        MarketRegime.LOW_VOLATILITY: RegimeAdjustments(
            position_size_multiplier=1.1,
            stop_distance_multiplier=0.8,    # Tighter stops
            confidence_threshold_adj=-5.0,
            prefer_direction="neutral",
            entry_aggression=1.1,
            exit_aggression=0.9,
            description="Low volatility - slightly larger positions, tighter stops"
        )
    }
    
    def __init__(self):
        self._price_cache: Dict[str, List[PriceData]] = {}
        self._regime_cache: Dict[str, Dict] = {}
    
    async def detect_regime(self, symbol: str) -> MarketRegime:
        """
        Detect current market regime for a symbol.
        
        Analysis:
        1. Calculate price change over periods
        2. Calculate volatility (ATR-like)
        3. Classify based on thresholds
        """
        try:
            # Get recent price data
            prices = await self._get_recent_prices(symbol)
            
            if len(prices) < 10:
                return MarketRegime.RANGING  # Default if not enough data
            
            # 1. Calculate trend
            trend = self._calculate_trend(prices)
            
            # 2. Calculate volatility
            volatility = self._calculate_volatility(prices)
            
            # 3. Classify regime
            regime = self._classify_regime(trend, volatility)
            
            # Cache result
            self._regime_cache[symbol] = {
                "regime": regime,
                "trend": trend,
                "volatility": volatility,
                "timestamp": datetime.now()
            }
            
            logger.debug(f"📊 {symbol} regime: {regime.value} (trend={trend:.2f}, vol={volatility:.2f})")
            
            return regime
            
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return MarketRegime.RANGING
    
    async def _get_recent_prices(self, symbol: str, periods: int = 20) -> List[PriceData]:
        """Get recent price data for analysis."""
        # Use cached prices if recent enough
        if symbol in self._price_cache:
            cached = self._price_cache[symbol]
            if len(cached) >= periods:
                return cached[-periods:]
        
        # Fetch from Hyperliquid
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            if not hl.is_connected:
                return []
            
            # Get candlestick data
            candles = await self._fetch_candles(hl, symbol, periods)
            
            prices = [
                PriceData(
                    timestamp=datetime.fromtimestamp(c["timestamp"] / 1000),
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c.get("volume", 0)
                )
                for c in candles
            ]
            
            self._price_cache[symbol] = prices
            return prices
            
        except Exception as e:
            logger.error(f"Failed to get prices: {e}")
            return []
    
    async def _fetch_candles(self, hl, symbol: str, periods: int) -> List[Dict]:
        """Fetch candlestick data from exchange."""
        try:
            # Hyperliquid API for candles
            candles = hl._info.candles_snapshot(
                coin=symbol,
                interval="15m",  # 15-minute candles
                n=periods
            )
            return candles
        except Exception as e:
            # Fallback: create synthetic candles from current price
            current_price = hl.get_prices().get(symbol, 0)
            if current_price:
                return [{
                    "timestamp": datetime.now().timestamp() * 1000,
                    "open": current_price,
                    "high": current_price * 1.001,
                    "low": current_price * 0.999,
                    "close": current_price,
                    "volume": 0
                }]
            return []
    
    def _calculate_trend(self, prices: List[PriceData]) -> float:
        """
        Calculate trend strength (-1 to +1).
        
        Uses simple linear regression slope on closes.
        """
        if len(prices) < 2:
            return 0.0
        
        closes = [p.close for p in prices]
        n = len(closes)
        
        # Simple slope calculation
        x_mean = (n - 1) / 2
        y_mean = sum(closes) / n
        
        numerator = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        
        # Normalize by price level
        normalized_slope = slope / y_mean * 100  # Percentage change per period
        
        # Clamp to -1 to +1
        return max(-1.0, min(1.0, normalized_slope))
    
    def _calculate_volatility(self, prices: List[PriceData]) -> float:
        """
        Calculate volatility (ATR-like).
        
        Returns normalized volatility score (0 to 1).
        """
        if len(prices) < 2:
            return 0.5
        
        # Calculate true ranges
        true_ranges = []
        for i in range(1, len(prices)):
            high = prices[i].high
            low = prices[i].low
            prev_close = prices[i-1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        if not true_ranges:
            return 0.5
        
        # Average true range
        atr = sum(true_ranges) / len(true_ranges)
        
        # Normalize by price level
        avg_price = sum(p.close for p in prices) / len(prices)
        atr_pct = atr / avg_price * 100
        
        # Map to 0-1 scale (assuming 0.5% is low, 2% is high for 15m candles)
        normalized = (atr_pct - 0.5) / 1.5
        
        return max(0.0, min(1.0, normalized))
    
    def _classify_regime(self, trend: float, volatility: float) -> MarketRegime:
        """Classify regime based on trend and volatility."""
        
        # High volatility takes precedence
        if volatility > 0.8:
            return MarketRegime.HIGH_VOLATILITY
        
        if volatility < 0.2:
            return MarketRegime.LOW_VOLATILITY
        
        # Classify by trend
        if trend > 0.5:
            return MarketRegime.STRONG_UPTREND
        elif trend > 0.2:
            return MarketRegime.WEAK_UPTREND
        elif trend < -0.5:
            return MarketRegime.STRONG_DOWNTREND
        elif trend < -0.2:
            return MarketRegime.WEAK_DOWNTREND
        else:
            return MarketRegime.RANGING
    
    def get_regime_adjustments(self, regime: MarketRegime) -> RegimeAdjustments:
        """Get trading adjustments for a regime."""
        return self.REGIME_ADJUSTMENTS.get(regime, RegimeAdjustments())
    
    def get_cached_regime(self, symbol: str) -> Optional[Dict]:
        """Get cached regime data if recent."""
        if symbol not in self._regime_cache:
            return None
        
        cached = self._regime_cache[symbol]
        age = (datetime.now() - cached["timestamp"]).total_seconds()
        
        # Cache valid for 5 minutes
        if age < 300:
            return cached
        
        return None
    
    def get_all_regimes(self) -> Dict[str, Dict]:
        """Get all cached regime data."""
        return {
            symbol: {
                "regime": data["regime"].value,
                "trend": round(data["trend"], 3),
                "volatility": round(data["volatility"], 3),
                "age_seconds": (datetime.now() - data["timestamp"]).total_seconds()
            }
            for symbol, data in self._regime_cache.items()
        }


# Singleton
_regime_detector: Optional[RegimeDetector] = None


def get_regime_detector() -> RegimeDetector:
    """Get or create global regime detector."""
    global _regime_detector
    if _regime_detector is None:
        _regime_detector = RegimeDetector()
    return _regime_detector









