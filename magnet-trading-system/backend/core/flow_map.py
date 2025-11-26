#!/usr/bin/env python3
"""
🗺️ FLOW MAP ENGINE

Determines the most efficient path from whale position → magnet.

Answers one question:
➡️ Which magnet requires the least energy to reach next?

Flow determined by:
1. Last clean sweep
2. Whale direction
3. Distance to each magnet
4. Magnet probability score
5. Obstructions (support/resistance)
6. Candle velocity (fast = continuation)
"""
from dataclasses import dataclass
from typing import List, Optional
from .magnet_scanner import Magnet
from .whale_engine import WhaleState, WhaleDirection


@dataclass
class FlowPath:
    """The selected trading path"""
    selected_magnet: Magnet
    efficiency_score: float  # 0-100
    obstructions: int
    estimated_time_bars: int
    confidence: float  # 0-100


class FlowMapEngine:
    """
    Calculates the optimal path to the next magnet.
    """
    
    def __init__(self,
                 max_distance_pct: float = 5.0,  # Max 5% distance
                 obstruction_penalty: float = 15):
        self.max_distance_pct = max_distance_pct
        self.obstruction_penalty = obstruction_penalty
    
    def calculate_flow(self,
                      whale_state: WhaleState,
                      magnets: List[Magnet],
                      current_price: float,
                      support_levels: Optional[List[float]] = None,
                      resistance_levels: Optional[List[float]] = None) -> Optional[FlowPath]:
        """
        Main flow calculation.
        
        Returns the optimal FlowPath or None if no clear path.
        """
        if not magnets:
            return None
        
        if whale_state.direction == WhaleDirection.FOG:
            # No clear direction = no trade
            return None
        
        # Filter magnets by direction
        if whale_state.direction == WhaleDirection.UP:
            candidates = [m for m in magnets if m.price > current_price]
        else:
            candidates = [m for m in magnets if m.price < current_price]
        
        if not candidates:
            return None
        
        # Filter by distance
        candidates = [m for m in candidates if m.distance <= self.max_distance_pct]
        
        if not candidates:
            return None
        
        # Score each path
        paths = []
        for magnet in candidates:
            efficiency = self._calculate_efficiency(
                magnet,
                whale_state,
                current_price,
                support_levels,
                resistance_levels
            )
            
            obstructions = self._count_obstructions(
                current_price,
                magnet.price,
                support_levels,
                resistance_levels
            )
            
            # Estimate time to reach
            time_bars = self._estimate_time(magnet.distance, whale_state.velocity)
            
            # Overall confidence
            confidence = self._calculate_confidence(
                magnet,
                whale_state,
                efficiency,
                obstructions
            )
            
            paths.append(FlowPath(
                selected_magnet=magnet,
                efficiency_score=efficiency,
                obstructions=obstructions,
                estimated_time_bars=time_bars,
                confidence=confidence
            ))
        
        # Select best path
        paths.sort(key=lambda p: p.confidence, reverse=True)
        
        if not paths:
            return None

        best = paths[0]
        
        # Minimum confidence threshold
        if best.confidence < 50:
            return None
        
        return best
    
    def _calculate_efficiency(self,
                             magnet: Magnet,
                             whale_state: WhaleState,
                             current_price: float,
                             support_levels: Optional[List[float]],
                             resistance_levels: Optional[List[float]]) -> float:
        """
        Efficiency = how easy it is to reach this magnet.
        
        Factors:
        - Distance (closer = better)
        - Magnet score (higher = better)
        - Whale velocity (higher = easier to continue)
        - Obstructions (fewer = better)
        """
        score = 0
        
        # Distance component (inverse)
        # Closer magnets get higher score
        if magnet.distance < 1.0:
            score += 40
        elif magnet.distance < 2.0:
            score += 30
        elif magnet.distance < 3.0:
            score += 20
        else:
            score += 10
        
        # Magnet quality
        score += magnet.score * 0.3
        
        # Whale velocity alignment
        if whale_state.velocity > 60:
            # High velocity = continuation likely
            score += 20
        elif whale_state.velocity > 40:
            score += 10
        
        return min(score, 100)
    
    def _count_obstructions(self,
                           current_price: float,
                           target_price: float,
                           support_levels: Optional[List[float]],
                           resistance_levels: Optional[List[float]]) -> int:
        """
        Count how many support/resistance levels are between current and target.
        """
        if not support_levels and not resistance_levels:
            return 0
        
        count = 0
        
        min_price = min(current_price, target_price)
        max_price = max(current_price, target_price)
        
        if resistance_levels:
            for level in resistance_levels:
                if min_price < level < max_price:
                    count += 1
        
        if support_levels:
            for level in support_levels:
                if min_price < level < max_price:
                    count += 1
        
        return count
    
    def _estimate_time(self, distance_pct: float, velocity: float) -> int:
        """
        Estimate number of candles to reach target.
        
        Rough formula: bars = distance / (velocity / 100)
        """
        if velocity == 0:
            return 999
        
        # Base estimate
        bars = int((distance_pct / (max(velocity, 1) / 100)) * 2)
        
        return max(bars, 1)
    
    def _calculate_confidence(self,
                             magnet: Magnet,
                             whale_state: WhaleState,
                             efficiency: float,
                             obstructions: int) -> float:
        """
        Overall confidence in this path.
        
        Combines:
        - Whale confidence
        - Magnet score
        - Efficiency
        - Obstructions (penalty)
        """
        confidence = 0
        
        # Whale confidence (30%)
        confidence += whale_state.confidence * 0.3
        
        # Magnet score (30%)
        confidence += magnet.score * 0.3
        
        # Efficiency (30%)
        confidence += efficiency * 0.3
        
        # Obstruction penalty (10% per obstruction)
        confidence -= obstructions * self.obstruction_penalty
        
        return max(min(confidence, 100), 0)

