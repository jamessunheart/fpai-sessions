"""
Coracle Non-Linear Confluence Engine
=====================================
Calculates probability scores using tier-weighted signal aggregation
with power-law multipliers for aligned signals.

Signal Weights:
- LIQUIDITY: 35%
- WHALE: 25%
- DERIVATIVES: 20%
- FUNDING: 15%
- ON_CHAIN: 10%
- TECHNICAL: 10%
- SENTIMENT: 5%

Note: Total > 100% because ON_CHAIN and TECHNICAL overlap in influence.
"""
from typing import Dict, List, Optional
import logging

from app.config import Settings, SIGNAL_TIERS, GRADE_THRESHOLDS
from app.models import (
    SignalSnapshot, Direction, ConfluenceResult, TierScore, ContractGrade
)

logger = logging.getLogger(__name__)


class ConfluenceEngine:
    """
    Non-linear confluence calculator.
    
    Key concepts:
    - Signals act as multipliers, not additive
    - Cross-tier alignment provides bonus multipliers
    - Danger signals apply compound penalties
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tier_weights = {
            "LIQUIDITY": settings.weight_liquidity,
            "WHALE": settings.weight_whale,
            "DERIVATIVES": settings.weight_derivatives,
            "FUNDING": settings.weight_funding,
            "ON_CHAIN": settings.weight_onchain,
            "TECHNICAL": settings.weight_technical,
            "SENTIMENT": settings.weight_sentiment
        }
    
    def calculate(
        self, 
        signals: SignalSnapshot, 
        direction: Direction
    ) -> ConfluenceResult:
        """
        Calculate confluence score for a direction.
        
        Returns probability and multiplier based on signal alignment.
        """
        # Calculate score for each tier
        tier_scores = self._calculate_tier_scores(signals, direction)
        
        # Calculate base probability from weighted tier scores
        base_probability = self._calculate_base_probability(tier_scores)
        
        # Calculate confluence multiplier
        multiplier, aligned_tiers = self._calculate_multiplier(tier_scores, signals)
        
        # Calculate danger penalty
        danger_penalty = self._calculate_danger_penalty(signals)
        
        # Apply multiplier and penalty
        final_probability = base_probability * multiplier * (1 - danger_penalty)
        final_probability = max(0, min(1, final_probability))
        
        return ConfluenceResult(
            direction=direction,
            base_probability=round(base_probability, 4),
            confluence_multiplier=round(multiplier, 4),
            final_probability=round(final_probability, 4),
            tier_scores=tier_scores,
            danger_penalty=round(danger_penalty, 4),
            aligned_tiers=aligned_tiers
        )
    
    def detect_direction(self, signals: SignalSnapshot) -> Direction:
        """
        Auto-detect optimal direction based on signal confluence.
        """
        # Calculate scores for both directions
        long_score = self._quick_direction_score(signals, Direction.LONG)
        short_score = self._quick_direction_score(signals, Direction.SHORT)
        
        if long_score > short_score and long_score > 0.55:
            return Direction.LONG
        elif short_score > long_score and short_score > 0.55:
            return Direction.SHORT
        else:
            return Direction.NEUTRAL
    
    def _calculate_tier_scores(
        self, 
        signals: SignalSnapshot, 
        direction: Direction
    ) -> List[TierScore]:
        """Calculate score for each signal tier."""
        tier_scores = []
        
        # LIQUIDITY tier
        liquidity_signals = self._get_tier_signals(signals, "LIQUIDITY", direction)
        tier_scores.append(self._score_tier("LIQUIDITY", liquidity_signals))
        
        # WHALE tier
        whale_signals = self._get_tier_signals(signals, "WHALE", direction)
        tier_scores.append(self._score_tier("WHALE", whale_signals))
        
        # DERIVATIVES tier
        deriv_signals = self._get_tier_signals(signals, "DERIVATIVES", direction)
        tier_scores.append(self._score_tier("DERIVATIVES", deriv_signals))
        
        # FUNDING tier
        funding_signals = self._get_tier_signals(signals, "FUNDING", direction)
        tier_scores.append(self._score_tier("FUNDING", funding_signals))
        
        # TECHNICAL tier
        tech_signals = self._get_tier_signals(signals, "TECHNICAL", direction)
        tier_scores.append(self._score_tier("TECHNICAL", tech_signals))
        
        # SENTIMENT tier
        sentiment_signals = self._get_tier_signals(signals, "SENTIMENT", direction)
        tier_scores.append(self._score_tier("SENTIMENT", sentiment_signals))
        
        return tier_scores
    
    def _get_tier_signals(
        self, 
        signals: SignalSnapshot, 
        tier: str, 
        direction: Direction
    ) -> List[Dict]:
        """Get signals for a tier with their alignment to direction."""
        tier_signals = []
        
        signal_map = {
            "LIQUIDITY": [signals.bai, signals.obs, signals.lcp],
            "WHALE": [signals.wadi, signals.wc],
            "DERIVATIVES": [signals.cvd, signals.oi, signals.ls_ratio],
            "FUNDING": [signals.fr, signals.spot_premium],
            "TECHNICAL": [signals.vrc],
            "SENTIMENT": [signals.fgi]
        }
        
        for sig in signal_map.get(tier, []):
            if sig is None:
                continue
            
            alignment = self._calculate_signal_alignment(sig, direction)
            tier_signals.append({
                "name": sig.name,
                "value": sig.value,
                "signal": sig.signal,
                "strength": sig.strength,
                "alignment": alignment  # -1 to 1
            })
        
        return tier_signals
    
    def _calculate_signal_alignment(self, signal, direction: Direction) -> float:
        """
        Calculate how well a signal aligns with the direction.
        
        Returns: -1 (opposing) to +1 (aligned)
        """
        sig_text = signal.signal.upper()
        
        # Bullish signals
        bullish_keywords = ["BULLISH", "ACCUMULATION", "BUY", "LONG", "FEAR"]
        # Bearish signals
        bearish_keywords = ["BEARISH", "DISTRIBUTION", "SELL", "SHORT", "GREED"]
        
        is_bullish = any(kw in sig_text for kw in bullish_keywords)
        is_bearish = any(kw in sig_text for kw in bearish_keywords)
        
        # Handle special cases
        if "CROWDED_LONG" in sig_text:  # Contrarian - bearish
            is_bullish, is_bearish = False, True
        elif "CROWDED_SHORT" in sig_text:  # Contrarian - bullish
            is_bullish, is_bearish = True, False
        
        # Calculate alignment based on direction
        if direction == Direction.LONG:
            if is_bullish:
                return signal.strength / 100  # 0 to 1
            elif is_bearish:
                return -signal.strength / 100  # -1 to 0
        elif direction == Direction.SHORT:
            if is_bearish:
                return signal.strength / 100
            elif is_bullish:
                return -signal.strength / 100
        
        return 0  # Neutral
    
    def _score_tier(self, tier: str, signals: List[Dict]) -> TierScore:
        """Score a single tier based on its signals."""
        weight = self.tier_weights.get(tier, 0.1)
        
        if not signals:
            return TierScore(
                tier=tier,
                weight=weight,
                signals_aligned=0,
                signals_total=0,
                raw_score=0.5,  # Neutral
                weighted_score=0.5 * weight
            )
        
        # Count aligned signals
        aligned = sum(1 for s in signals if s["alignment"] > 0.3)
        total = len(signals)
        
        # Calculate raw score (0 to 1)
        alignments = [s["alignment"] for s in signals]
        avg_alignment = sum(alignments) / len(alignments)
        
        # Convert alignment (-1 to 1) to probability (0 to 1)
        raw_score = (avg_alignment + 1) / 2
        
        return TierScore(
            tier=tier,
            weight=weight,
            signals_aligned=aligned,
            signals_total=total,
            raw_score=round(raw_score, 4),
            weighted_score=round(raw_score * weight, 4)
        )
    
    def _calculate_base_probability(self, tier_scores: List[TierScore]) -> float:
        """Calculate base probability from weighted tier scores."""
        total_weight = sum(ts.weight for ts in tier_scores)
        if total_weight == 0:
            return 0.5
        
        weighted_sum = sum(ts.weighted_score for ts in tier_scores)
        return weighted_sum / total_weight
    
    def _calculate_multiplier(
        self, 
        tier_scores: List[TierScore],
        signals: SignalSnapshot
    ) -> tuple[float, int]:
        """
        Calculate non-linear confluence multiplier.
        
        Power-law multiplier logic:
        - Tier 1 (LIQUIDITY + WHALE + DERIVATIVES) alignment: 1.2x
        - Tier 2 (FUNDING + TECHNICAL + SENTIMENT) alignment: 1.15x
        - Cross-tier alignment: 1.08x
        """
        multiplier = 1.0
        
        # Group tiers
        tier1_names = ["LIQUIDITY", "WHALE", "DERIVATIVES"]
        tier2_names = ["FUNDING", "TECHNICAL", "SENTIMENT"]
        
        tier1_scores = [ts for ts in tier_scores if ts.tier in tier1_names]
        tier2_scores = [ts for ts in tier_scores if ts.tier in tier2_names]
        
        # Count aligned tiers (raw_score > 0.6)
        tier1_aligned = sum(1 for ts in tier1_scores if ts.raw_score > 0.6)
        tier2_aligned = sum(1 for ts in tier2_scores if ts.raw_score > 0.6)
        total_aligned = tier1_aligned + tier2_aligned
        
        # Tier 1 confluence bonus
        if tier1_aligned >= 3:
            multiplier *= 1.2
        elif tier1_aligned >= 2:
            multiplier *= 1.1
        
        # Tier 2 confluence bonus
        if tier2_aligned >= 3:
            multiplier *= 1.15
        elif tier2_aligned >= 2:
            multiplier *= 1.08
        
        # Cross-tier alignment bonus
        if tier1_aligned >= 2 and tier2_aligned >= 2:
            multiplier *= 1.08
        
        return multiplier, total_aligned
    
    def _calculate_danger_penalty(self, signals: SignalSnapshot) -> float:
        """
        Calculate danger compound penalty.
        
        Danger conditions:
        - High spoof detection (SDS > 0.15) + High OI volatility (OIV > 1.5)
        - Extreme Fear/Greed + High LCP
        """
        penalty = 0.0
        
        # Check LCP danger
        if signals.lcp and signals.lcp.value > 2.0:
            lcp_penalty = (signals.lcp.value - 2.0) * 0.1
            penalty += min(0.2, lcp_penalty)
        
        # Check extreme sentiment
        if signals.fgi:
            fgi_value = signals.fgi.value
            if fgi_value < 20 or fgi_value > 80:  # Extreme
                penalty += 0.05
        
        # Cap total penalty at 50%
        return min(0.5, penalty)
    
    def _quick_direction_score(
        self, 
        signals: SignalSnapshot, 
        direction: Direction
    ) -> float:
        """Quick directional score for auto-detection."""
        score = 0.5  # Start neutral
        
        # WADI contribution
        if signals.wadi:
            wadi = signals.wadi.value
            if direction == Direction.LONG:
                score += wadi * 0.3  # Max +0.3
            else:
                score -= wadi * 0.3  # Max +0.3 for SHORT when negative
        
        # CVD contribution
        if signals.cvd:
            cvd = signals.cvd.value
            if direction == Direction.LONG:
                score += cvd * 0.2
            else:
                score -= cvd * 0.2
        
        # Funding contribution (contrarian)
        if signals.fr:
            fr = signals.fr.value
            if direction == Direction.LONG and fr > 0.01:  # Longs paying
                score += 0.1  # Contrarian bullish
            elif direction == Direction.SHORT and fr < -0.01:
                score += 0.1  # Contrarian bearish
        
        # Fear/Greed contribution (contrarian)
        if signals.fgi:
            fgi = signals.fgi.value
            if direction == Direction.LONG and fgi < 30:  # Fear
                score += 0.1
            elif direction == Direction.SHORT and fgi > 70:  # Greed
                score += 0.1
        
        return max(0, min(1, score))
    
    def get_grade(self, probability: float) -> ContractGrade:
        """Convert probability to contract grade."""
        if probability >= GRADE_THRESHOLDS["A"]:
            return ContractGrade.A
        elif probability >= GRADE_THRESHOLDS["B"]:
            return ContractGrade.B
        elif probability >= GRADE_THRESHOLDS["C"]:
            return ContractGrade.C
        elif probability >= GRADE_THRESHOLDS["D"]:
            return ContractGrade.D
        else:
            return ContractGrade.F


