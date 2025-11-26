#!/usr/bin/env python3
"""
🧲 MAGNET SCANNER

Detects liquidity clusters and scores them 0-100%.

Magnet Types:
- Stop loss clusters
- Liquidation heatmaps
- Equal highs / equal lows
- Imbalances / FVG
- Unfilled volume gaps
- Volume nodes (HVN/LVN)
- Session extremes
- Wick vacuum zones

Scoring System:
+20% — Liquidation cluster present
+20% — Equal highs/lows (untapped)
+20% — FVG / imbalance alignment
+20% — Major volume node at level
+20% — Direction matches whale momentum
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import numpy as np


class MagnetType(str, Enum):
    LIQUIDITY = "liquidity"
    EQUAL_HIGHS = "equal_highs"
    EQUAL_LOWS = "equal_lows"
    VOLUME_NODE = "volume"
    IMBALANCE = "imbalance"
    SESSION_EXTREME = "session_extreme"
    WICK_VACUUM = "wick_vacuum"


@dataclass
class Magnet:
    """A liquidity target that attracts price"""
    price: float
    score: float  # 0-100
    type: MagnetType
    distance: float  # Distance from current price
    strength: float  # Liquidity density (0-100)
    tapped: bool = False  # Has price touched this level?
    
    def __repr__(self):
        return f"Magnet({self.type.value} @ {self.price:.2f}, score={self.score:.1f})"


@dataclass
class VolumeProfile:
    """Volume at price levels"""
    price_level: float
    volume: float
    is_high_volume_node: bool
    is_low_volume_node: bool


class MagnetScanner:
    """
    Scans market data to identify and score magnets.
    """
    
    def __init__(self,
                 equal_threshold: float = 0.001,  # 0.1% tolerance for equal levels
                 hvn_percentile: float = 80,
                 lvn_percentile: float = 20):
        self.equal_threshold = equal_threshold
        self.hvn_percentile = hvn_percentile
        self.lvn_percentile = lvn_percentile
    
    def scan(self, 
             candles: List,  # Candle objects
             current_price: float,
             whale_direction: str,
             liquidation_data: Optional[List[dict]] = None,
             volume_profile: Optional[List[VolumeProfile]] = None) -> List[Magnet]:
        """
        Main scan function.
        
        Returns list of Magnets sorted by score (highest first).
        """
        magnets = []
        
        # 1. Detect Equal Highs/Lows
        magnets.extend(self._detect_equal_levels(candles, current_price))
        
        # 2. Detect Imbalances (FVG)
        magnets.extend(self._detect_imbalances(candles, current_price))
        
        # 3. Detect Volume Nodes
        if volume_profile:
            magnets.extend(self._detect_volume_nodes(volume_profile, current_price))
        
        # 4. Detect Session Extremes
        magnets.extend(self._detect_session_extremes(candles, current_price))
        
        # 5. Detect Wick Vacuums
        magnets.extend(self._detect_wick_vacuums(candles, current_price))
        
        # 6. Add Liquidation Data (if available)
        if liquidation_data:
            magnets = self._enhance_with_liquidations(magnets, liquidation_data)
        
        # 7. Score all magnets
        for magnet in magnets:
            magnet.score = self._calculate_score(magnet, whale_direction, liquidation_data)
        
        # 8. Remove duplicates (merge close magnets)
        magnets = self._merge_close_magnets(magnets, current_price)
        
        # 9. Sort by score
        magnets.sort(key=lambda m: m.score, reverse=True)
        
        return magnets
    
    def _detect_equal_levels(self, candles: List, current_price: float) -> List[Magnet]:
        """Detect equal highs and equal lows."""
        magnets = []
        
        if len(candles) < 3:
            return magnets
        
        recent = candles[-20:]  # Look back 20 candles
        
        # Get all highs and lows
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        
        # Find equal highs
        equal_highs = self._find_equal_levels(highs)
        for price in equal_highs:
            if price > current_price:  # Only above current price
                magnets.append(Magnet(
                    price=price,
                    score=0,  # Will be scored later
                    type=MagnetType.EQUAL_HIGHS,
                    distance=abs(price - current_price) / current_price * 100,
                    strength=70,
                    tapped=False
                ))
        
        # Find equal lows
        equal_lows = self._find_equal_levels(lows)
        for price in equal_lows:
            if price < current_price:  # Only below current price
                magnets.append(Magnet(
                    price=price,
                    score=0,
                    type=MagnetType.EQUAL_LOWS,
                    distance=abs(price - current_price) / current_price * 100,
                    strength=70,
                    tapped=False
                ))
        
        return magnets
    
    def _find_equal_levels(self, levels: List[float]) -> List[float]:
        """Find levels that appear multiple times (within threshold)."""
        equal_levels = []
        
        for i, level in enumerate(levels):
            matches = sum(1 for other in levels 
                         if abs(other - level) / level <= self.equal_threshold)
            
            if matches >= 2:  # At least 2 touches
                if not any(abs(existing - level) / level <= self.equal_threshold 
                          for existing in equal_levels):
                    equal_levels.append(level)
        
        return equal_levels
    
    def _detect_imbalances(self, candles: List, current_price: float) -> List[Magnet]:
        """
        Detect Fair Value Gaps (FVG) / Imbalances.
        
        FVG = gap between candle N-2's high/low and candle N's low/high.
        """
        magnets = []
        
        if len(candles) < 3:
            return magnets
        
        recent = candles[-20:]
        
        for i in range(len(recent) - 2):
            c1 = recent[i]
            c2 = recent[i + 1]
            c3 = recent[i + 2]
            
            # Bullish FVG (gap up)
            if c3.low > c1.high:
                gap_mid = (c1.high + c3.low) / 2
                magnets.append(Magnet(
                    price=gap_mid,
                    score=0,
                    type=MagnetType.IMBALANCE,
                    distance=abs(gap_mid - current_price) / current_price * 100,
                    strength=60,
                    tapped=False
                ))
            
            # Bearish FVG (gap down)
            if c3.high < c1.low:
                gap_mid = (c1.low + c3.high) / 2
                magnets.append(Magnet(
                    price=gap_mid,
                    score=0,
                    type=MagnetType.IMBALANCE,
                    distance=abs(gap_mid - current_price) / current_price * 100,
                    strength=60,
                    tapped=False
                ))
        
        return magnets
    
    def _detect_volume_nodes(self, volume_profile: List[VolumeProfile], 
                            current_price: float) -> List[Magnet]:
        """Detect High Volume Nodes (HVN) and Low Volume Nodes (LVN)."""
        magnets = []
        
        for node in volume_profile:
            if node.is_high_volume_node:
                magnets.append(Magnet(
                    price=node.price_level,
                    score=0,
                    type=MagnetType.VOLUME_NODE,
                    distance=abs(node.price_level - current_price) / current_price * 100,
                    strength=80,
                    tapped=False
                ))
            elif node.is_low_volume_node:
                # LVN = vacuum zone (price moves fast through it)
                magnets.append(Magnet(
                    price=node.price_level,
                    score=0,
                    type=MagnetType.VOLUME_NODE,
                    distance=abs(node.price_level - current_price) / current_price * 100,
                    strength=50,
                    tapped=False
                ))
        
        return magnets
    
    def _detect_session_extremes(self, candles: List, current_price: float) -> List[Magnet]:
        """Detect session highs and lows."""
        magnets = []
        
        if len(candles) < 10:
            return magnets
        
        # Get session high and low
        session_high = max(c.high for c in candles)
        session_low = min(c.low for c in candles)
        
        if session_high > current_price:
            magnets.append(Magnet(
                price=session_high,
                score=0,
                type=MagnetType.SESSION_EXTREME,
                distance=abs(session_high - current_price) / current_price * 100,
                strength=75,
                tapped=False
            ))
        
        if session_low < current_price:
            magnets.append(Magnet(
                price=session_low,
                score=0,
                type=MagnetType.SESSION_EXTREME,
                distance=abs(session_low - current_price) / current_price * 100,
                strength=75,
                tapped=False
            ))
        
        return magnets
    
    def _detect_wick_vacuums(self, candles: List, current_price: float) -> List[Magnet]:
        """
        Detect wick vacuum zones.
        
        Wick vacuum = area with large wicks but no body closes.
        """
        magnets = []
        
        if len(candles) < 5:
            return magnets
        
        recent = candles[-10:]
        
        for c in recent:
            # Check for large wick rejection
            if c.upper_wick > c.body_size * 2:
                # Strong rejection from above = magnet above
                magnet_price = c.high
                if magnet_price > current_price:
                    magnets.append(Magnet(
                        price=magnet_price,
                        score=0,
                        type=MagnetType.WICK_VACUUM,
                        distance=abs(magnet_price - current_price) / current_price * 100,
                        strength=55,
                        tapped=False
                    ))
            
            if c.lower_wick > c.body_size * 2:
                # Strong rejection from below = magnet below
                magnet_price = c.low
                if magnet_price < current_price:
                    magnets.append(Magnet(
                        price=magnet_price,
                        score=0,
                        type=MagnetType.WICK_VACUUM,
                        distance=abs(magnet_price - current_price) / current_price * 100,
                        strength=55,
                        tapped=False
                    ))
        
        return magnets
    
    def _enhance_with_liquidations(self, magnets: List[Magnet], 
                                   liquidation_data: List[dict]) -> List[Magnet]:
        """Add liquidation cluster magnets."""
        for liq in liquidation_data:
            price = liq.get("price")
            volume = liq.get("volume", 0)
            
            magnets.append(Magnet(
                price=price,
                score=0,
                type=MagnetType.LIQUIDITY,
                distance=abs(price - liq.get("current_price", price)) / price * 100,
                strength=min(volume / 1000, 100),  # Normalize
                tapped=False
            ))
        
        return magnets
    
    def _calculate_score(self, magnet: Magnet, whale_direction: str,
                        liquidation_data: Optional[List[dict]]) -> float:
        """
        Score magnet 0-100 based on:
        +20% — Liquidation cluster present
        +20% — Equal highs/lows (untapped)
        +20% — FVG / imbalance alignment
        +20% — Major volume node at level
        +20% — Direction matches whale momentum
        """
        score = 0
        
        # Base strength
        score += magnet.strength * 0.2
        
        # Type bonuses
        if magnet.type == MagnetType.LIQUIDITY:
            score += 20
        
        if magnet.type in [MagnetType.EQUAL_HIGHS, MagnetType.EQUAL_LOWS] and not magnet.tapped:
            score += 20
        
        if magnet.type == MagnetType.IMBALANCE:
            score += 20
        
        if magnet.type == MagnetType.VOLUME_NODE and magnet.strength > 70:
            score += 20
        
        # Whale direction alignment
        if whale_direction == "up" and magnet.price > 0:
            score += 20
        elif whale_direction == "down" and magnet.price > 0:
            score += 20
        
        return min(score, 100)
    
    def _merge_close_magnets(self, magnets: List[Magnet], 
                            current_price: float) -> List[Magnet]:
        """Merge magnets that are very close to each other."""
        if len(magnets) <= 1:
            return magnets
        
        merged = []
        used = set()
        
        for i, m1 in enumerate(magnets):
            if i in used:
                continue
            
            cluster = [m1]
            
            for j, m2 in enumerate(magnets[i+1:], start=i+1):
                if j in used:
                    continue
                
                # Check if within 0.2% of each other
                if abs(m1.price - m2.price) / current_price < 0.002:
                    cluster.append(m2)
                    used.add(j)
            
            # Merge cluster into single magnet
            avg_price = np.mean([m.price for m in cluster])
            max_score = max(m.score for m in cluster)
            max_strength = max(m.strength for m in cluster)
            
            merged.append(Magnet(
                price=avg_price,
                score=max_score,
                type=cluster[0].type,
                distance=abs(avg_price - current_price) / current_price * 100,
                strength=max_strength,
                tapped=any(m.tapped for m in cluster)
            ))
        
        return merged

