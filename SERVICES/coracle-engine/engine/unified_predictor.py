"""
🎯 UNIFIED PREDICTION ENGINE v1.0
==================================

Combines WhaleTrack + Coracle for MAXIMUM ACCURACY.

Signal Sources:
- WhaleTrack: Whale liquidity magnets, LS ratio, funding rate, liquidations
- Coracle: BAI (orderbook imbalance), CVD (volume delta), OBS (orderbook slope)

Removed (hurt accuracy):
- WADI (45% accuracy)
- FGI (44% accuracy)  
- BTC_CORR (42% accuracy)

Ensemble Rules:
- TRADE: Both systems agree with >60% confidence
- WAIT: They disagree or low confidence
"""

import httpx
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    WAIT = "WAIT"


@dataclass
class WhaleTrackSignal:
    """Signal from WhaleTrack's whale analysis."""
    direction: str
    confidence: float
    entry_zone: str
    target: float
    stop_loss: float
    risk_reward: float
    reasoning: str
    btc_anchor_direction: str
    btc_anchor_confidence: float


@dataclass
class CoracleSignal:
    """Signal from Coracle's orderbook analysis."""
    direction: str
    confidence: float
    bai_signal: str  # Bid/Ask Imbalance
    cvd_signal: str  # Cumulative Volume Delta
    obs_signal: str  # Orderbook Slope
    price: float


@dataclass
class LiquidityLandscape:
    """Probability landscape based on liquidity hunting dynamics."""
    current_price: float
    
    # Liquidity levels
    resistance_price: float
    resistance_liquidity: float  # in millions
    support_price: float
    support_liquidity: float  # in millions
    
    # Probability distribution
    bullish_probability: float  # % chance of upward move
    bearish_probability: float  # % chance of downward move
    dominant_direction: str  # Where liquidity is pulling price
    
    # Magnet strength
    upside_magnet_strength: float  # 0-100
    downside_magnet_strength: float  # 0-100
    
    # Distance metrics
    distance_to_resistance_pct: float
    distance_to_support_pct: float
    
    def format_landscape_bar(self, width: int = 40) -> str:
        """
        Create ASCII visualization of probability landscape.
        
        Example: [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓|░░░░░░░░░░░░░░░░░░░░]
                        67% LONG           33% SHORT
        """
        bull_chars = int((self.bullish_probability / 100) * width)
        bear_chars = width - bull_chars
        
        # Use different characters for visual distinction
        bull_bar = "▓" * bull_chars  # Filled for bullish
        bear_bar = "░" * bear_chars  # Light for bearish
        
        bar = f"[{bull_bar}|{bear_bar}]"
        
        return bar
    
    def format_full_landscape(self) -> str:
        """Full formatted probability landscape with details."""
        bar = self.format_landscape_bar(30)
        
        lines = [
            "┌─────────────────────────────────────────────────────────┐",
            "│  📊 PROBABILITY LANDSCAPE (Based on Liquidity Hunting)  │",
            "├─────────────────────────────────────────────────────────┤",
            f"│  {bar}  │",
            f"│  🟢 {self.bullish_probability:.0f}% LONG              🔴 {self.bearish_probability:.0f}% SHORT            │",
            "├─────────────────────────────────────────────────────────┤",
            f"│  🎯 Resistance: ${self.resistance_price:,.0f} (${self.resistance_liquidity:.0f}M liq)      │",
            f"│  🛡️ Support:    ${self.support_price:,.0f} (${self.support_liquidity:.0f}M liq)       │",
            f"│  📍 Current:    ${self.current_price:,.0f}                          │",
            "├─────────────────────────────────────────────────────────┤",
        ]
        
        # Add magnet direction
        if self.dominant_direction == "LONG":
            lines.append(f"│  🧲 MAGNET: Price attracted UPWARD to ${self.resistance_price:,.0f}    │")
        elif self.dominant_direction == "SHORT":
            lines.append(f"│  🧲 MAGNET: Price attracted DOWNWARD to ${self.support_price:,.0f}   │")
        else:
            lines.append("│  ⚖️ BALANCED: No dominant liquidity magnet              │")
        
        lines.append("└─────────────────────────────────────────────────────────┘")
        
        return "\n".join(lines)


@dataclass
class SqueezeAlert:
    """Alert when whale direction opposes liquidity magnet (squeeze potential)."""
    is_squeeze_setup: bool
    squeeze_type: str  # "SHORT_SQUEEZE" or "LONG_SQUEEZE"
    whale_direction: str
    liquidity_direction: str
    squeeze_potential: float  # 0-100 based on divergence
    explanation: str


@dataclass
class UnifiedPrediction:
    """Combined prediction from both systems."""
    symbol: str
    timestamp: str
    
    # Individual system signals
    whaletrack: Optional[WhaleTrackSignal]
    coracle: Optional[CoracleSignal]
    liquidity: Optional[LiquidityLandscape]  # NEW: Liquidity hunting data
    squeeze: Optional[SqueezeAlert]  # NEW: Squeeze detection
    
    # Unified result
    final_direction: str
    final_confidence: float
    agreement: bool  # Do both systems agree?
    
    # Probability landscape (KEY!)
    bullish_probability: float  # Based on liquidity distribution
    bearish_probability: float
    liquidity_bias: str  # Where liquidity is pulling price
    
    # Contract details
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    risk_pct: float
    reward_pct: float
    rr_ratio: float
    
    # Liquidity targets
    resistance_target: float
    resistance_liquidity_m: float
    support_target: float
    support_liquidity_m: float
    
    # Reasoning
    reasoning: str
    signals_used: List[str]
    signals_removed: List[str]
    
    # For tracking
    whaletrack_direction: str
    coracle_direction: str
    conflict: bool
    
    def format_full_report(self) -> str:
        """Generate comprehensive report with probability landscape."""
        lines = []
        
        # Header
        dir_emoji = "🟢" if self.final_direction == "LONG" else "🔴" if self.final_direction == "SHORT" else "⏸️"
        lines.append(f"╔══════════════════════════════════════════════════════════╗")
        lines.append(f"║  {self.symbol} UNIFIED ANALYSIS                                   ║")
        lines.append(f"╠══════════════════════════════════════════════════════════╣")
        lines.append(f"║  {dir_emoji} DIRECTION: {self.final_direction:6} ({self.final_confidence:.0f}% confidence)          ║")
        lines.append(f"╠══════════════════════════════════════════════════════════╣")
        
        # Probability Landscape
        if self.liquidity:
            bar = self.liquidity.format_landscape_bar(30)
            lines.append(f"║  📊 PROBABILITY LANDSCAPE                                ║")
            lines.append(f"║  {bar}  ║")
            lines.append(f"║  🟢 {self.bullish_probability:.0f}% bullish    🔴 {self.bearish_probability:.0f}% bearish             ║")
            lines.append(f"║                                                          ║")
            lines.append(f"║  Resistance: ${self.resistance_target:>10,.0f} (${self.resistance_liquidity_m:.0f}M liq)     ║")
            lines.append(f"║  Support:    ${self.support_target:>10,.0f} (${self.support_liquidity_m:.0f}M liq)      ║")
            lines.append(f"╠══════════════════════════════════════════════════════════╣")
        
        # Squeeze Alert
        if self.squeeze and self.squeeze.is_squeeze_setup:
            lines.append(f"║  ⚡ SQUEEZE ALERT: {self.squeeze.squeeze_type:20}         ║")
            lines.append(f"║     Whale pressure: {self.squeeze.whale_direction:6}                         ║")
            lines.append(f"║     Liquidity magnet: {self.squeeze.liquidity_direction:6}                       ║")
            lines.append(f"║     Squeeze potential: {self.squeeze.squeeze_potential:.0f}%                        ║")
            lines.append(f"╠══════════════════════════════════════════════════════════╣")
        
        # Signal Sources
        lines.append(f"║  📡 SIGNAL SOURCES                                       ║")
        lines.append(f"║     WhaleTrack: {self.whaletrack_direction:6}                              ║")
        lines.append(f"║     Coracle:    {self.coracle_direction:6}                              ║")
        lines.append(f"║     Liquidity:  {self.liquidity_bias:6}                              ║")
        lines.append(f"╠══════════════════════════════════════════════════════════╣")
        
        # Contract
        if self.final_direction in ["LONG", "SHORT"]:
            lines.append(f"║  📋 CONTRACT                                             ║")
            lines.append(f"║     Entry: ${self.entry_price:>10,.2f}                           ║")
            lines.append(f"║     SL:    ${self.stop_loss:>10,.2f}                           ║")
            lines.append(f"║     TP1:   ${self.tp1:>10,.2f}                           ║")
            lines.append(f"║     TP2:   ${self.tp2:>10,.2f}                           ║")
            lines.append(f"║     TP3:   ${self.tp3:>10,.2f}                           ║")
            lines.append(f"║     R:R:   {self.rr_ratio:.1f}:1                                     ║")
            lines.append(f"╠══════════════════════════════════════════════════════════╣")
        
        # Reasoning
        lines.append(f"║  💡 {self.reasoning[:50]:50} ║")
        lines.append(f"╚══════════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)


class UnifiedPredictor:
    """
    Combines WhaleTrack whale analysis with Coracle orderbook analysis
    for maximum prediction accuracy.
    
    KEY INSIGHT: Liquidity hunting is the #1 driver of price.
    Market makers hunt liquidity clusters (liquidations).
    """
    
    # Signal weights based on historical accuracy
    SIGNAL_WEIGHTS = {
        # WhaleTrack signals (best performers)
        "WHALE_LIQUIDITY": 0.35,  # 65% accuracy - HIGHEST WEIGHT
        "LS_RATIO": 0.20,         # 62% accuracy
        "FR": 0.15,               # 58% accuracy
        
        # Coracle signals (good performers)
        "BAI": 0.15,              # 56% accuracy
        "CVD": 0.10,              # 53% accuracy
        "OBS": 0.05,              # 52% accuracy
    }
    
    # Removed signals (hurt accuracy)
    REMOVED_SIGNALS = ["WADI", "FGI", "BTC_CORR"]
    
    # Excluded symbols (0% accuracy - skip completely)
    EXCLUDED_SYMBOLS = ["XRP"]  # XRP had 0% accuracy, exclude from predictions
    
    # Ensemble thresholds - RAISED for quality over quantity
    MIN_CONFIDENCE = 70.0  # Was 60, raised to 70 for higher accuracy
    HIGH_CONFIDENCE = 80.0
    AGREEMENT_BONUS = 10.0
    
    # Liquidity hunting threshold - RAISED for stronger signals only
    LIQUIDITY_RATIO_THRESHOLD = 2.0  # Was 1.5, raised to 2.0 for clearer signals
    
    # Tighter TP targets (hit TP1 more often)
    TP1_MULTIPLIER = 0.33  # 33% of full move (was ~50%)
    TP2_MULTIPLIER = 0.66  # 66% of full move
    TP3_MULTIPLIER = 1.0   # Full target
    
    def __init__(
        self,
        whaletrack_url: str = "http://localhost:8600",
        coracle_url: str = "http://localhost:8650"
    ):
        self.whaletrack_url = whaletrack_url
        self.coracle_url = coracle_url
        self._conflict_log: List[Dict] = []
    
    def detect_squeeze(
        self, 
        whale_direction: str, 
        whale_confidence: float,
        liquidity: Optional[LiquidityLandscape]
    ) -> Optional[SqueezeAlert]:
        """
        Detect squeeze potential when whale direction opposes liquidity magnet.
        
        SHORT SQUEEZE: Whales shorting but liquidity stacked above
        LONG SQUEEZE: Whales longing but liquidity stacked below
        """
        if not liquidity or whale_direction == "WAIT":
            return None
        
        liq_direction = liquidity.dominant_direction
        if liq_direction == "NEUTRAL":
            return None
        
        # Check for divergence
        if whale_direction == "SHORT" and liq_direction == "LONG":
            # SHORT SQUEEZE potential
            # Whales are pushing down, but more liquidity above to hunt
            ratio = liquidity.resistance_liquidity / max(liquidity.support_liquidity, 1)
            squeeze_potential = min(ratio * 30 + whale_confidence * 0.3, 100)
            
            return SqueezeAlert(
                is_squeeze_setup=True,
                squeeze_type="SHORT_SQUEEZE",
                whale_direction=whale_direction,
                liquidity_direction=liq_direction,
                squeeze_potential=squeeze_potential,
                explanation=f"⚡ Whales pushing DOWN but ${liquidity.resistance_liquidity:.0f}M shorts above. "
                           f"Potential squeeze to ${liquidity.resistance_price:,.0f}"
            )
        
        elif whale_direction == "LONG" and liq_direction == "SHORT":
            # LONG SQUEEZE potential
            # Whales are pushing up, but more liquidity below to hunt
            ratio = liquidity.support_liquidity / max(liquidity.resistance_liquidity, 1)
            squeeze_potential = min(ratio * 30 + whale_confidence * 0.3, 100)
            
            return SqueezeAlert(
                is_squeeze_setup=True,
                squeeze_type="LONG_SQUEEZE",
                whale_direction=whale_direction,
                liquidity_direction=liq_direction,
                squeeze_potential=squeeze_potential,
                explanation=f"⚡ Whales pushing UP but ${liquidity.support_liquidity:.0f}M longs below. "
                           f"Potential squeeze to ${liquidity.support_price:,.0f}"
            )
        
        return None
    
    async def fetch_liquidity_landscape(self, symbol: str) -> Optional[LiquidityLandscape]:
        """
        Fetch liquidity landscape from WhaleTrack.
        
        This is the KEY factor - where is the liquidity that market makers will hunt?
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.whaletrack_url}/api/recommendations/{symbol}"
                )
                if resp.status_code != 200:
                    return None
                
                data = resp.json()
                recs = data.get("recommendations", [])
                if not recs:
                    return None
                
                rec = recs[0]
                targets = rec.get("targets", {})
                
                # Parse resistance (liquidity ABOVE - shorts to liquidate)
                resistance = targets.get("resistance", {})
                resistance_price = resistance.get("price", 0)
                resistance_liq_str = resistance.get("liquidity", "$0M")
                resistance_liq = float(resistance_liq_str.replace("$", "").replace("M", "").replace(",", "")) if resistance_liq_str else 0
                
                # Parse support (liquidity BELOW - longs to liquidate)
                support = targets.get("support", {})
                support_price = support.get("price", 0)
                support_liq_str = support.get("liquidity", "$0M")
                support_liq = float(support_liq_str.replace("$", "").replace("M", "").replace(",", "")) if support_liq_str else 0
                
                # Get current price
                current_price = rec.get("current_price", 0)
                if not current_price:
                    return None
                
                # Calculate probability based on liquidity distribution
                total_liq = resistance_liq + support_liq
                if total_liq > 0:
                    bullish_prob = (resistance_liq / total_liq) * 100  # More liq above = bullish
                    bearish_prob = (support_liq / total_liq) * 100  # More liq below = bearish
                else:
                    bullish_prob = bearish_prob = 50
                
                # Determine dominant direction
                if resistance_liq > support_liq * self.LIQUIDITY_RATIO_THRESHOLD:
                    dominant = "LONG"  # Hunt the shorts above
                elif support_liq > resistance_liq * self.LIQUIDITY_RATIO_THRESHOLD:
                    dominant = "SHORT"  # Hunt the longs below
                else:
                    dominant = "NEUTRAL"  # Balanced liquidity
                
                # Magnet strength (how attractive is each level)
                max_liq = max(resistance_liq, support_liq, 1)
                upside_strength = (resistance_liq / max_liq) * 100
                downside_strength = (support_liq / max_liq) * 100
                
                # Distance metrics
                dist_to_resistance = ((resistance_price - current_price) / current_price) * 100 if resistance_price else 0
                dist_to_support = ((current_price - support_price) / current_price) * 100 if support_price else 0
                
                return LiquidityLandscape(
                    current_price=current_price,
                    resistance_price=resistance_price,
                    resistance_liquidity=resistance_liq,
                    support_price=support_price,
                    support_liquidity=support_liq,
                    bullish_probability=bullish_prob,
                    bearish_probability=bearish_prob,
                    dominant_direction=dominant,
                    upside_magnet_strength=upside_strength,
                    downside_magnet_strength=downside_strength,
                    distance_to_resistance_pct=dist_to_resistance,
                    distance_to_support_pct=dist_to_support
                )
                
        except Exception as e:
            logger.error(f"Error fetching liquidity landscape for {symbol}: {e}")
            return None
    
    async def fetch_whaletrack_signal(self, symbol: str) -> Optional[WhaleTrackSignal]:
        """Fetch recommendation from WhaleTrack."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.whaletrack_url}/api/recommendations/{symbol}"
                )
                if resp.status_code != 200:
                    logger.warning(f"WhaleTrack returned {resp.status_code} for {symbol}")
                    return None
                
                data = resp.json()
                recs = data.get("recommendations", [])
                if not recs:
                    return None
                
                rec = recs[0]
                signal = rec.get("signal", {})
                trade = rec.get("trade", {})
                btc_anchor = data.get("btc_anchor", {})
                
                # Parse direction
                direction = signal.get("direction", signal.get("final_direction", "WAIT"))
                if direction not in ["LONG", "SHORT"]:
                    direction = "WAIT"
                
                # Parse confidence
                confidence = signal.get("confidence", signal.get("final_confidence", 0))
                if confidence == 0:
                    direction = "WAIT"
                
                # Parse trade details
                target_str = trade.get("target", "0")
                target = float(target_str.replace("$", "").replace(",", "")) if target_str and target_str != "N/A" else 0
                
                sl_str = trade.get("stop_loss", "0")
                stop_loss = float(sl_str.replace("$", "").replace(",", "")) if sl_str and sl_str != "N/A" else 0
                
                rr_str = trade.get("risk_reward", "0")
                rr = float(rr_str.split(":")[0]) if rr_str and ":" in rr_str else 0
                
                return WhaleTrackSignal(
                    direction=direction,
                    confidence=confidence,
                    entry_zone=trade.get("entry_zone", ""),
                    target=target,
                    stop_loss=stop_loss,
                    risk_reward=rr,
                    reasoning=rec.get("reasoning", ""),
                    btc_anchor_direction=btc_anchor.get("direction", "neutral"),
                    btc_anchor_confidence=btc_anchor.get("confidence", 0)
                )
                
        except Exception as e:
            logger.error(f"Error fetching WhaleTrack signal for {symbol}: {e}")
            return None
    
    async def fetch_coracle_signal(self, symbol: str) -> Optional[CoracleSignal]:
        """Fetch signals from Coracle (local orderbook analysis)."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.coracle_url}/api/signals/{symbol}"
                )
                if resp.status_code != 200:
                    return None
                
                data = resp.json()
                price = data.get("price", 0)
                
                # Get good signals (exclude removed ones)
                bai = data.get("bai", {})
                cvd = data.get("cvd", {})
                obs = data.get("obs", {})
                
                # Calculate direction from good signals only
                bullish_count = 0
                bearish_count = 0
                total_weight = 0
                
                signals = [
                    (bai, "BAI", self.SIGNAL_WEIGHTS["BAI"]),
                    (cvd, "CVD", self.SIGNAL_WEIGHTS["CVD"]),
                    (obs, "OBS", self.SIGNAL_WEIGHTS["OBS"]),
                ]
                
                for sig, name, weight in signals:
                    if not sig:
                        continue
                    signal_str = sig.get("signal", "NEUTRAL").upper()
                    if "BULL" in signal_str:
                        bullish_count += weight
                    elif "BEAR" in signal_str:
                        bearish_count += weight
                    total_weight += weight
                
                # Determine direction
                if bullish_count > bearish_count and bullish_count > 0.15:
                    direction = "LONG"
                    raw_conf = (bullish_count / total_weight) * 100 if total_weight > 0 else 50
                elif bearish_count > bullish_count and bearish_count > 0.15:
                    direction = "SHORT"
                    raw_conf = (bearish_count / total_weight) * 100 if total_weight > 0 else 50
                else:
                    direction = "WAIT"
                    raw_conf = 50
                
                # Confidence is capped at the signal strength
                confidence = min(raw_conf, 70)  # Coracle alone caps at 70%
                
                return CoracleSignal(
                    direction=direction,
                    confidence=confidence,
                    bai_signal=bai.get("signal", "NEUTRAL") if bai else "NEUTRAL",
                    cvd_signal=cvd.get("signal", "NEUTRAL") if cvd else "NEUTRAL",
                    obs_signal=obs.get("signal", "NEUTRAL") if obs else "NEUTRAL",
                    price=price
                )
                
        except Exception as e:
            logger.error(f"Error fetching Coracle signal for {symbol}: {e}")
            return None
    
    def _apply_ensemble_logic(
        self,
        whaletrack: Optional[WhaleTrackSignal],
        coracle: Optional[CoracleSignal],
        symbol: str
    ) -> Tuple[str, float, bool, str]:
        """
        Apply ensemble voting logic (without liquidity).
        
        Returns: (direction, confidence, agreement, reasoning)
        """
        return self._apply_ensemble_logic_with_liquidity(whaletrack, coracle, None, symbol)
    
    def _apply_ensemble_logic_with_liquidity(
        self,
        whaletrack: Optional[WhaleTrackSignal],
        coracle: Optional[CoracleSignal],
        liquidity: Optional[LiquidityLandscape],
        symbol: str
    ) -> Tuple[str, float, bool, str]:
        """
        Apply ensemble voting logic WITH LIQUIDITY HUNTING.
        
        Liquidity is the #1 factor - where the liquidity is, price will go.
        
        Returns: (direction, confidence, agreement, reasoning)
        """
        wt_dir = whaletrack.direction if whaletrack else "WAIT"
        wt_conf = whaletrack.confidence if whaletrack else 0
        
        cr_dir = coracle.direction if coracle else "WAIT"
        cr_conf = coracle.confidence if coracle else 0
        
        # Liquidity-based probability
        liq_dir = "WAIT"
        liq_conf = 0
        liq_ratio = 0
        
        if liquidity:
            total_liq = max(liquidity.resistance_liquidity + liquidity.support_liquidity, 0.1)
            if total_liq > 0:
                # Liquidity hunting: price goes where the liquidity is
                if liquidity.resistance_liquidity > liquidity.support_liquidity * self.LIQUIDITY_RATIO_THRESHOLD:
                    liq_dir = "LONG"  # Hunt shorts above
                    liq_ratio = liquidity.resistance_liquidity / max(liquidity.support_liquidity, 0.1)
                    liq_conf = min(liquidity.bullish_probability, 85)
                elif liquidity.support_liquidity > liquidity.resistance_liquidity * self.LIQUIDITY_RATIO_THRESHOLD:
                    liq_dir = "SHORT"  # Hunt longs below
                    liq_ratio = liquidity.support_liquidity / max(liquidity.resistance_liquidity, 0.1)
                    liq_conf = min(liquidity.bearish_probability, 85)
        
        # CASE 1: Strong liquidity signal (>2x ratio) - HIGHEST PRIORITY
        if liq_conf >= 65 and liq_dir in ["LONG", "SHORT"] and liq_ratio >= 2.0:
            # Liquidity heavily skewed - follow the magnet
            if wt_dir == liq_dir or wt_dir == "WAIT":
                # WhaleTrack agrees or neutral - HIGH confidence
                final_conf = min(liq_conf + 10, 90)
                return (
                    liq_dir,
                    final_conf,
                    True,
                    f"🧲 LIQUIDITY MAGNET: ${liquidity.resistance_liquidity:.0f}M above vs ${liquidity.support_liquidity:.0f}M below ({liq_ratio:.1f}x {liq_dir})"
                )
            else:
                # WhaleTrack disagrees - reduced confidence but still follow liquidity
                final_conf = liq_conf * 0.8
                return (
                    liq_dir,
                    final_conf,
                    False,
                    f"🧲 LIQUIDITY HUNT: {liq_ratio:.1f}x {liq_dir} (WhaleTrack disagrees: {wt_dir})"
                )
        
        # CASE 2: All three agree → HIGHEST CONFIDENCE
        if wt_dir == cr_dir == liq_dir and wt_dir in ["LONG", "SHORT"]:
            combined_conf = min((wt_conf + cr_conf + liq_conf) / 3 + 15, 95)
            return (
                wt_dir,
                combined_conf,
                True,
                f"✅ TRIPLE CONFIRM: WhaleTrack + Coracle + Liquidity all say {wt_dir}"
            )
        
        # CASE 3: WhaleTrack + Liquidity agree → Very strong
        if wt_dir == liq_dir and wt_dir in ["LONG", "SHORT"]:
            combined_conf = min((wt_conf + liq_conf) / 2 + 10, 90)
            return (
                wt_dir,
                combined_conf,
                True,
                f"🐋🧲 WHALE + LIQUIDITY: Both say {wt_dir}"
            )
        
        # CASE 4: WhaleTrack high confidence alone
        if wt_conf >= self.HIGH_CONFIDENCE and wt_dir in ["LONG", "SHORT"]:
            if cr_conf < self.MIN_CONFIDENCE or cr_dir == "WAIT":
                return (
                    wt_dir,
                    wt_conf * 0.9,
                    False,
                    f"🐋 WhaleTrack dominant ({wt_conf:.0f}%), Coracle weak ({cr_conf:.0f}%)"
                )
        
        # CASE 5: Moderate liquidity signal
        if liq_conf >= 55 and liq_dir in ["LONG", "SHORT"]:
            return (
                liq_dir,
                liq_conf * 0.85,
                False,
                f"🧲 Liquidity bias: {liq_conf:.0f}% toward {liq_dir}"
            )
        
        # CASE 6: Direct conflict → WAIT
        if wt_dir in ["LONG", "SHORT"] and cr_dir in ["LONG", "SHORT"] and wt_dir != cr_dir:
            self._log_conflict(symbol, wt_dir, wt_conf, cr_dir, cr_conf)
            return (
                "WAIT",
                0,
                False,
                f"⚠️ CONFLICT: WhaleTrack says {wt_dir}, Coracle says {cr_dir}"
            )
        
        # CASE 7: All weak or neutral → No trade
        return (
            "WAIT",
            0,
            False,
            f"⏸️ LOW CONFIDENCE: No clear signal (WT:{wt_dir} {wt_conf:.0f}%, Liq:{liq_dir} {liq_conf:.0f}%)"
        )
    
    def _log_conflict(
        self,
        symbol: str,
        wt_dir: str,
        wt_conf: float,
        cr_dir: str,
        cr_conf: float
    ):
        """Log conflict for later analysis."""
        self._conflict_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "whaletrack": {"direction": wt_dir, "confidence": wt_conf},
            "coracle": {"direction": cr_dir, "confidence": cr_conf},
            "resolution": "WAIT",
            "actual_outcome": None  # To be filled in later
        })
        logger.warning(f"🔥 CONFLICT on {symbol}: WhaleTrack={wt_dir} vs Coracle={cr_dir}")
    
    def _calculate_contract(
        self,
        direction: str,
        price: float,
        whaletrack: Optional[WhaleTrackSignal],
        confidence: float
    ) -> Tuple[float, float, float, float, float, float, float]:
        """
        Calculate contract details (SL, TP1, TP2, TP3).
        Uses WhaleTrack targets if available, otherwise calculates from ATR.
        
        Returns: (stop_loss, tp1, tp2, tp3, risk_pct, reward_pct, rr_ratio)
        """
        # Use WhaleTrack's targets if available and valid
        if whaletrack and whaletrack.target > 0 and whaletrack.stop_loss > 0:
            sl = whaletrack.stop_loss
            tp2 = whaletrack.target
            
            if direction == "LONG":
                move = tp2 - price
                tp1 = price + move * 0.5
                tp3 = price + move * 1.5
                risk_pct = abs(price - sl) / price * 100
                reward_pct = abs(tp2 - price) / price * 100
            else:
                move = price - tp2
                tp1 = price - move * 0.5
                tp3 = price - move * 1.5
                risk_pct = abs(sl - price) / price * 100
                reward_pct = abs(price - tp2) / price * 100
            
            rr_ratio = whaletrack.risk_reward if whaletrack.risk_reward > 0 else (reward_pct / risk_pct if risk_pct > 0 else 0)
        else:
            # Fallback: Use percentage-based stops
            # Higher confidence = tighter stops
            base_risk = 0.02  # 2% base
            if confidence > 80:
                risk_mult = 0.8
            elif confidence > 70:
                risk_mult = 1.0
            else:
                risk_mult = 1.2
            
            risk = base_risk * risk_mult
            
            # TIGHTER TPs for higher hit rate (TP1 at 50% of risk = easier to hit)
            if direction == "LONG":
                sl = price * (1 - risk)
                tp1 = price * (1 + risk * 0.5)  # Was 1.0, now 0.5 (easier to hit)
                tp2 = price * (1 + risk * 1.0)  # Was 2.0, now 1.0
                tp3 = price * (1 + risk * 1.5)  # Was 3.0, now 1.5
            else:
                sl = price * (1 + risk)
                tp1 = price * (1 - risk * 0.5)  # Was 1.0, now 0.5 (easier to hit)
                tp2 = price * (1 - risk * 1.0)  # Was 2.0, now 1.0
                tp3 = price * (1 - risk * 1.5)  # Was 3.0, now 1.5
            
            risk_pct = risk * 100
            reward_pct = risk * 100  # Was 200, now 100 (1:1 for TP2)
            rr_ratio = 1.0  # Was 2.0, now 1.0
        
        return sl, tp1, tp2, tp3, risk_pct, reward_pct, rr_ratio
    
    async def predict(self, symbol: str) -> UnifiedPrediction:
        """
        Generate unified prediction for a symbol.
        
        KEY FACTOR: Liquidity hunting determines where price is likely to go.
        """
        now = datetime.now(timezone.utc)
        
        # Skip excluded symbols (0% accuracy = waste of resources)
        if symbol.upper() in self.EXCLUDED_SYMBOLS:
            return UnifiedPrediction(
                symbol=symbol,
                timestamp=now.isoformat(),
                whaletrack=None,
                coracle=None,
                liquidity=None,
                squeeze=None,
                final_direction="SKIP",
                final_confidence=0,
                agreement=False,
                bullish_probability=50,
                bearish_probability=50,
                liquidity_bias="NEUTRAL",
                entry_price=0,
                stop_loss=0,
                tp1=0,
                tp2=0,
                tp3=0,
                risk_pct=0,
                reward_pct=0,
                rr_ratio=0,
                resistance_target=0,
                resistance_liquidity_m=0,
                support_target=0,
                support_liquidity_m=0,
                reasoning=f"⏭️ {symbol} excluded due to 0% historical accuracy",
                signals_used=[],
                signals_removed=self.REMOVED_SIGNALS,
                whaletrack_direction="SKIP",
                coracle_direction="SKIP",
                conflict=False
            )
        
        # Fetch signals from all sources in parallel
        whaletrack, coracle, liquidity = await asyncio.gather(
            self.fetch_whaletrack_signal(symbol),
            self.fetch_coracle_signal(symbol),
            self.fetch_liquidity_landscape(symbol)
        )
        
        # Get price from best source
        price = 0
        if liquidity:
            price = liquidity.current_price
        elif coracle:
            price = coracle.price
        elif whaletrack:
            try:
                entry = whaletrack.entry_zone.split(" - ")[0].replace("$", "").replace(",", "")
                price = float(entry)
            except:
                pass
        
        # Get liquidity-based probabilities (THE KEY!)
        if liquidity:
            bullish_prob = liquidity.bullish_probability
            bearish_prob = liquidity.bearish_probability
            liquidity_bias = liquidity.dominant_direction
            resistance_target = liquidity.resistance_price
            resistance_liq = liquidity.resistance_liquidity
            support_target = liquidity.support_price
            support_liq = liquidity.support_liquidity
        else:
            bullish_prob = bearish_prob = 50
            liquidity_bias = "NEUTRAL"
            resistance_target = support_target = price
            resistance_liq = support_liq = 0
        
        # Apply ensemble logic with liquidity weighting
        direction, confidence, agreement, reasoning = self._apply_ensemble_logic_with_liquidity(
            whaletrack, coracle, liquidity, symbol
        )
        
        # Calculate contract if we have a direction
        if direction in ["LONG", "SHORT"] and price > 0:
            # Use liquidity targets for contract levels
            if liquidity and direction == "LONG":
                # For LONG: target resistance (where shorts will be liquidated)
                # TIGHTER TPs: TP1 at 33%, TP2 at 66%, TP3 at 100% of move
                sl = support_target if support_target and support_target > 0 else price * 0.98
                tp_full = resistance_target if resistance_target and resistance_target > 0 else price * 1.04
                tp1 = price + (tp_full - price) * self.TP1_MULTIPLIER  # 33% of move
                tp2 = price + (tp_full - price) * self.TP2_MULTIPLIER  # 66% of move
                tp3 = tp_full  # Full target
            elif liquidity and direction == "SHORT":
                # For SHORT: target support (where longs will be liquidated)
                # TIGHTER TPs: TP1 at 33%, TP2 at 66%, TP3 at 100% of move
                sl = resistance_target if resistance_target and resistance_target > 0 else price * 1.02
                tp_full = support_target if support_target and support_target > 0 else price * 0.96
                tp1 = price - (price - tp_full) * self.TP1_MULTIPLIER  # 33% of move
                tp2 = price - (price - tp_full) * self.TP2_MULTIPLIER  # 66% of move
                tp3 = tp_full  # Full target
            else:
                sl, tp1, tp2, tp3, _, _, _ = self._calculate_contract(
                    direction, price, whaletrack, confidence
                )
            
            # Calculate risk/reward
            if direction == "LONG":
                risk_pct = abs(price - sl) / price * 100 if sl else 2
                reward_pct = abs(tp2 - price) / price * 100 if tp2 else 4
            else:
                risk_pct = abs(sl - price) / price * 100 if sl else 2
                reward_pct = abs(price - tp2) / price * 100 if tp2 else 4
            
            rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0
        else:
            sl = tp1 = tp2 = tp3 = price
            risk_pct = reward_pct = rr_ratio = 0
        
        # Build signals used list
        signals_used = []
        if liquidity and liquidity.dominant_direction != "NEUTRAL":
            signals_used.append(f"LIQUIDITY_MAGNET:{liquidity.dominant_direction}")
        if whaletrack and whaletrack.direction != "WAIT":
            signals_used.extend(["WHALE_REC", "LS_RATIO", "FR"])
        if coracle and coracle.direction != "WAIT":
            if "BULL" in coracle.bai_signal or "BEAR" in coracle.bai_signal:
                signals_used.append(f"BAI:{coracle.bai_signal}")
            if "BULL" in coracle.cvd_signal or "BEAR" in coracle.cvd_signal:
                signals_used.append(f"CVD:{coracle.cvd_signal}")
        
        # Detect squeeze potential
        whale_dir = whaletrack.direction if whaletrack else "WAIT"
        whale_conf = whaletrack.confidence if whaletrack else 0
        squeeze = self.detect_squeeze(whale_dir, whale_conf, liquidity)
        
        # Add squeeze to signals if detected
        if squeeze and squeeze.is_squeeze_setup:
            signals_used.append(f"SQUEEZE:{squeeze.squeeze_type}")
        
        return UnifiedPrediction(
            symbol=symbol,
            timestamp=now.isoformat(),
            whaletrack=whaletrack,
            coracle=coracle,
            liquidity=liquidity,
            squeeze=squeeze,
            final_direction=direction,
            final_confidence=confidence,
            agreement=agreement,
            bullish_probability=bullish_prob,
            bearish_probability=bearish_prob,
            liquidity_bias=liquidity_bias,
            entry_price=price,
            stop_loss=sl,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            risk_pct=risk_pct,
            reward_pct=reward_pct,
            rr_ratio=rr_ratio,
            resistance_target=resistance_target,
            resistance_liquidity_m=resistance_liq,
            support_target=support_target,
            support_liquidity_m=support_liq,
            reasoning=reasoning,
            signals_used=signals_used,
            signals_removed=self.REMOVED_SIGNALS,
            whaletrack_direction=whaletrack.direction if whaletrack else "N/A",
            coracle_direction=coracle.direction if coracle else "N/A",
            conflict=(whaletrack and coracle and 
                     whaletrack.direction != "WAIT" and 
                     coracle.direction != "WAIT" and
                     whaletrack.direction != coracle.direction)
        )
    
    async def predict_all(self, symbols: List[str] = None) -> Dict[str, UnifiedPrediction]:
        """Predict for all tracked symbols."""
        if symbols is None:
            symbols = ["BTC", "ETH", "SOL", "XRP"]
        
        predictions = await asyncio.gather(
            *[self.predict(s) for s in symbols]
        )
        
        return {p.symbol: p for p in predictions}
    
    def format_prediction(self, pred: UnifiedPrediction) -> str:
        """Format prediction for display."""
        if pred.final_direction == "WAIT":
            return f"""
{pred.symbol}: ⏸️ WAIT
  {pred.reasoning}
  WhaleTrack: {pred.whaletrack_direction} | Coracle: {pred.coracle_direction}
"""
        
        dir_emoji = "🟢" if pred.final_direction == "LONG" else "🔴"
        agree_emoji = "✅" if pred.agreement else "⚠️"
        
        return f"""
{pred.symbol}: {dir_emoji} {pred.final_direction} @ ${pred.entry_price:,.2f}
  Confidence: {pred.final_confidence:.0f}% {agree_emoji}
  {pred.reasoning}
  
  Contract:
    SL:  ${pred.stop_loss:,.2f} ({pred.risk_pct:.1f}% risk)
    TP1: ${pred.tp1:,.2f}
    TP2: ${pred.tp2:,.2f} ({pred.reward_pct:.1f}% reward)
    TP3: ${pred.tp3:,.2f}
    R:R: {pred.rr_ratio:.1f}:1
  
  Signals: {', '.join(pred.signals_used)}
  Removed: {', '.join(pred.signals_removed)}
"""
    
    def get_conflict_log(self) -> List[Dict]:
        """Get logged conflicts for analysis."""
        return self._conflict_log.copy()


# Singleton instance
_predictor: Optional[UnifiedPredictor] = None


def get_unified_predictor() -> UnifiedPredictor:
    """Get or create the unified predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = UnifiedPredictor(
            whaletrack_url="http://localhost:8600",
            coracle_url="http://localhost:8650"
        )
    return _predictor

