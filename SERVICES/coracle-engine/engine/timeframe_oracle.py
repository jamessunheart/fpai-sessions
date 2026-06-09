"""
Coracle Multi-Timeframe Oracle
================================

Different timeframes serve different purposes:

HOURLY (1h)
- Noise level: HIGH
- Use for: Entry timing, scalping
- Value: Low per prediction, high volume
- "Should I enter RIGHT NOW?"

4-HOUR (4h)
- Noise level: MEDIUM  
- Use for: Swing trading, session bias
- Value: Medium per prediction
- "What's the trend for this session?"

DAILY (24h)
- Noise level: LOW
- Use for: Position trading, daily bias
- Value: High per prediction
- "What should I be positioned for today?"

WEEKLY (7d)
- Noise level: VERY LOW
- Use for: Strategic allocation, macro view
- Value: Very high per prediction
- "What's the market bias this week?"

THE HIERARCHY:
- Weekly sets the MACRO BIAS (strongest signal)
- Daily confirms or challenges the weekly
- 4h gives the SESSION DIRECTION
- 1h is for ENTRY TIMING within the larger trend

RULE: Never trade 1h against the daily. Never trade daily against weekly.
"""

import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum

from app.config import get_settings

logger = logging.getLogger(__name__)


class Timeframe(str, Enum):
    HOURLY = "1h"
    FOUR_HOUR = "4h"
    DAILY = "24h"
    WEEKLY = "7d"


@dataclass
class TimeframePrediction:
    """Prediction for a specific timeframe."""
    timeframe: str
    symbol: str
    timestamp: str
    
    direction: str  # LONG, SHORT, NEUTRAL
    confidence: float  # 0-100
    
    # Probabilities
    long_probability: float
    short_probability: float
    neutral_probability: float
    
    # Price targets (adjusted for timeframe)
    entry: float
    stop_loss: float
    target_1: float  # Conservative
    target_2: float  # Moderate
    target_3: float  # Aggressive
    
    # Target probabilities
    target_1_probability: float
    target_2_probability: float
    target_3_probability: float
    
    # Expected move
    expected_move_pct: float
    
    # Value metrics
    expected_value: float
    grade: str
    
    # Alignment with higher timeframes
    aligned_with_higher: bool
    higher_tf_direction: Optional[str]


@dataclass
class MultiTimeframeBias:
    """Combined bias across all timeframes."""
    symbol: str
    timestamp: str
    
    # Individual timeframe directions
    hourly_direction: str
    four_hour_direction: str
    daily_direction: str
    weekly_direction: str
    
    # Confidence at each level
    hourly_confidence: float
    four_hour_confidence: float
    daily_confidence: float
    weekly_confidence: float
    
    # Overall bias (weighted by timeframe importance)
    overall_direction: str
    overall_confidence: float
    
    # Alignment score (0-100, higher = all timeframes agree)
    alignment_score: float
    
    # Actionable?
    tradeable: bool
    trade_reasoning: str


class TimeframeOracle:
    """
    Multi-timeframe prediction engine.
    
    The key insight: Longer timeframes are MORE RELIABLE but SLOWER.
    We use the hierarchy to filter noise and find high-conviction setups.
    """
    
    # Timeframe weights for overall bias calculation
    TIMEFRAME_WEIGHTS = {
        Timeframe.WEEKLY: 0.40,    # Weekly is most important
        Timeframe.DAILY: 0.30,     # Daily confirms weekly
        Timeframe.FOUR_HOUR: 0.20, # 4h for session timing
        Timeframe.HOURLY: 0.10,    # Hourly for entry only
    }
    
    # Expected move multipliers (based on typical ATR)
    MOVE_MULTIPLIERS = {
        Timeframe.HOURLY: 1.0,
        Timeframe.FOUR_HOUR: 2.0,
        Timeframe.DAILY: 3.5,
        Timeframe.WEEKLY: 7.0,
    }
    
    # Minimum confidence to be tradeable
    MIN_CONFIDENCE = {
        Timeframe.HOURLY: 55,      # Lower bar for 1h
        Timeframe.FOUR_HOUR: 58,
        Timeframe.DAILY: 60,
        Timeframe.WEEKLY: 62,      # Higher bar for weekly
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = f"http://localhost:{self.settings.port}"
        
        # Cache for weekly/daily predictions (don't recalculate every hour)
        self._weekly_cache: Dict[str, TimeframePrediction] = {}
        self._daily_cache: Dict[str, TimeframePrediction] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def generate_prediction(
        self, 
        symbol: str, 
        timeframe: Timeframe,
        higher_tf_direction: Optional[str] = None
    ) -> Optional[TimeframePrediction]:
        """
        Generate a prediction for a specific timeframe.
        
        Longer timeframes use wider stops and targets.
        """
        try:
            # Get base signals
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.base_url}/api/signals/{symbol}")
                if resp.status_code != 200:
                    return None
                signals = resp.json()
            
            price = signals.get("price", 0)
            if not price:
                return None
            
            # Get volatility for this timeframe
            vrc = signals.get("vrc", {})
            base_atr = vrc.get("value", 0.02)
            
            # Scale ATR by timeframe
            timeframe_atr = base_atr * self.MOVE_MULTIPLIERS[timeframe]
            
            # Calculate direction from signals
            direction, confidence, long_prob, short_prob = self._calculate_direction(
                signals, timeframe
            )
            
            neutral_prob = max(0, 100 - long_prob - short_prob)
            
            # Check alignment with higher timeframe
            aligned = True
            if higher_tf_direction:
                if direction == "LONG" and higher_tf_direction == "SHORT":
                    aligned = False
                    confidence *= 0.7  # Penalize counter-trend
                elif direction == "SHORT" and higher_tf_direction == "LONG":
                    aligned = False
                    confidence *= 0.7
            
            # Calculate stops and targets based on timeframe
            risk_mult = {
                Timeframe.HOURLY: 1.0,
                Timeframe.FOUR_HOUR: 1.5,
                Timeframe.DAILY: 2.0,
                Timeframe.WEEKLY: 3.0,
            }[timeframe]
            
            risk_pct = timeframe_atr * risk_mult
            risk_pct = max(0.01, min(0.10, risk_pct))  # 1-10% range
            
            # Entry and stop loss
            entry = price
            if direction == "LONG":
                stop_loss = price * (1 - risk_pct)
                target_1 = price * (1 + risk_pct * 1.5)  # 1.5:1 R:R
                target_2 = price * (1 + risk_pct * 2.5)  # 2.5:1 R:R
                target_3 = price * (1 + risk_pct * 4.0)  # 4:1 R:R
            else:
                stop_loss = price * (1 + risk_pct)
                target_1 = price * (1 - risk_pct * 1.5)
                target_2 = price * (1 - risk_pct * 2.5)
                target_3 = price * (1 - risk_pct * 4.0)
            
            # Target probabilities (decay with distance)
            t1_prob = min(80, confidence * 0.85)
            t2_prob = min(60, confidence * 0.55)
            t3_prob = min(40, confidence * 0.35)
            
            # Expected move
            expected_move = timeframe_atr * (confidence / 100) * 100
            
            # Expected value
            # EV = (win_prob * avg_reward) - (lose_prob * risk)
            avg_reward = risk_pct * 2.0  # Assume hitting T1 average
            win_prob = t1_prob / 100
            ev = (win_prob * avg_reward) - ((1 - win_prob) * risk_pct)
            ev_pct = ev * 100
            
            # Grade
            if ev_pct > 2.0 and confidence > 70 and aligned:
                grade = "A"
            elif ev_pct > 1.0 and confidence > 60:
                grade = "B"
            elif ev_pct > 0.5 and confidence > 50:
                grade = "C"
            elif ev_pct > 0:
                grade = "D"
            else:
                grade = "F"
            
            return TimeframePrediction(
                timeframe=timeframe.value,
                symbol=symbol,
                timestamp=datetime.utcnow().isoformat(),
                direction=direction,
                confidence=confidence,
                long_probability=long_prob,
                short_probability=short_prob,
                neutral_probability=neutral_prob,
                entry=entry,
                stop_loss=stop_loss,
                target_1=target_1,
                target_2=target_2,
                target_3=target_3,
                target_1_probability=t1_prob,
                target_2_probability=t2_prob,
                target_3_probability=t3_prob,
                expected_move_pct=expected_move,
                expected_value=ev_pct,
                grade=grade,
                aligned_with_higher=aligned,
                higher_tf_direction=higher_tf_direction
            )
            
        except Exception as e:
            logger.error(f"Error generating {timeframe.value} prediction for {symbol}: {e}")
            return None
    
    def _calculate_direction(
        self, 
        signals: Dict, 
        timeframe: Timeframe
    ) -> tuple:
        """
        Calculate direction with timeframe-appropriate weighting.
        
        Longer timeframes weight slower signals higher (funding, on-chain).
        Shorter timeframes weight faster signals higher (order book, trades).
        """
        bullish_score = 0
        bearish_score = 0
        
        # Signal weights by timeframe
        if timeframe == Timeframe.HOURLY:
            # Fast signals matter more
            signal_weights = {
                "bai": 1.5,      # Order book - very fast
                "cvd": 1.3,      # Trade flow - fast
                "obs": 1.2,      # Order book sentiment
                "wadi": 1.0,     # Whale activity
                "fgi": 0.8,      # Sentiment - slower
                "fr": 0.7,       # Funding - slow
                "ls_ratio": 0.9, # Long/short ratio
            }
        elif timeframe == Timeframe.FOUR_HOUR:
            signal_weights = {
                "bai": 1.2,
                "cvd": 1.2,
                "obs": 1.0,
                "wadi": 1.3,
                "fgi": 1.0,
                "fr": 1.0,
                "ls_ratio": 1.1,
            }
        elif timeframe == Timeframe.DAILY:
            # Slow signals matter more
            signal_weights = {
                "bai": 0.8,
                "cvd": 0.9,
                "obs": 0.7,
                "wadi": 1.4,     # Whale activity important
                "fgi": 1.3,      # Sentiment important
                "fr": 1.4,       # Funding very important
                "ls_ratio": 1.2,
            }
        else:  # Weekly
            signal_weights = {
                "bai": 0.5,
                "cvd": 0.6,
                "obs": 0.5,
                "wadi": 1.5,
                "fgi": 1.5,
                "fr": 1.5,
                "ls_ratio": 1.3,
            }
        
        for sig_name, weight in signal_weights.items():
            sig = signals.get(sig_name)
            if not sig:
                continue
            
            signal_val = sig.get("signal", "").upper()
            strength = sig.get("strength", 50) * weight
            
            if "BULLISH" in signal_val:
                bullish_score += strength
            elif "BEARISH" in signal_val:
                bearish_score += strength
            elif signal_val == "FEAR":  # Contrarian
                bullish_score += strength * 0.6
            elif signal_val == "GREED":
                bearish_score += strength * 0.6
            elif signal_val == "LEAN_SHORT":
                bullish_score += strength * 0.4
            elif signal_val == "LEAN_LONG":
                bearish_score += strength * 0.4
        
        # Determine direction and confidence
        total = bullish_score + bearish_score
        if total > 0:
            if bullish_score > bearish_score:
                direction = "LONG"
                confidence = min(85, 50 + (bullish_score - bearish_score) / 6)
                long_prob = min(80, 50 + bullish_score / 5)
                short_prob = max(15, 50 - bullish_score / 5)
            elif bearish_score > bullish_score:
                direction = "SHORT"
                confidence = min(85, 50 + (bearish_score - bullish_score) / 6)
                short_prob = min(80, 50 + bearish_score / 5)
                long_prob = max(15, 50 - bearish_score / 5)
            else:
                direction = "NEUTRAL"
                confidence = 50
                long_prob = 40
                short_prob = 40
        else:
            direction = "NEUTRAL"
            confidence = 50
            long_prob = 40
            short_prob = 40
        
        return direction, confidence, long_prob, short_prob
    
    async def generate_multi_timeframe_bias(self, symbol: str) -> MultiTimeframeBias:
        """
        Generate bias across all timeframes and calculate overall direction.
        
        This is the KEY function - it tells us the TRUE bias by combining all timeframes.
        """
        # Generate predictions (weekly first, then cascade down)
        weekly = await self._get_or_generate_weekly(symbol)
        daily = await self._get_or_generate_daily(symbol, weekly)
        four_hour = await self.generate_prediction(
            symbol, 
            Timeframe.FOUR_HOUR, 
            daily.direction if daily else None
        )
        hourly = await self.generate_prediction(
            symbol, 
            Timeframe.HOURLY, 
            four_hour.direction if four_hour else None
        )
        
        # Extract directions and confidences
        predictions = {
            Timeframe.WEEKLY: weekly,
            Timeframe.DAILY: daily,
            Timeframe.FOUR_HOUR: four_hour,
            Timeframe.HOURLY: hourly,
        }
        
        directions = {}
        confidences = {}
        
        for tf, pred in predictions.items():
            if pred:
                directions[tf] = pred.direction
                confidences[tf] = pred.confidence
            else:
                directions[tf] = "NEUTRAL"
                confidences[tf] = 50
        
        # Calculate weighted overall bias
        long_score = 0
        short_score = 0
        neutral_score = 0
        
        for tf, weight in self.TIMEFRAME_WEIGHTS.items():
            direction = directions[tf]
            confidence = confidences[tf]
            
            if direction == "LONG":
                long_score += weight * confidence
            elif direction == "SHORT":
                short_score += weight * confidence
            else:
                neutral_score += weight * confidence
        
        # Determine overall direction
        max_score = max(long_score, short_score, neutral_score)
        if max_score == long_score:
            overall_direction = "LONG"
            overall_confidence = long_score / sum(self.TIMEFRAME_WEIGHTS.values())
        elif max_score == short_score:
            overall_direction = "SHORT"
            overall_confidence = short_score / sum(self.TIMEFRAME_WEIGHTS.values())
        else:
            overall_direction = "NEUTRAL"
            overall_confidence = neutral_score / sum(self.TIMEFRAME_WEIGHTS.values())
        
        # Calculate alignment score (how much do timeframes agree?)
        matching_count = sum(1 for d in directions.values() if d == overall_direction)
        alignment_score = (matching_count / len(directions)) * 100
        
        # Determine if tradeable
        tradeable = False
        reasoning = ""
        
        if alignment_score >= 75 and overall_confidence >= 60:
            tradeable = True
            reasoning = f"Strong alignment ({alignment_score:.0f}%) with high confidence ({overall_confidence:.0f}%)"
        elif alignment_score >= 50 and overall_confidence >= 70:
            tradeable = True
            reasoning = f"Moderate alignment with very high confidence ({overall_confidence:.0f}%)"
        elif directions[Timeframe.WEEKLY] == directions[Timeframe.DAILY] and confidences[Timeframe.WEEKLY] >= 60:
            tradeable = True
            reasoning = f"Weekly and Daily aligned {directions[Timeframe.WEEKLY]} - strong macro signal"
        else:
            if alignment_score < 50:
                reasoning = f"Low alignment ({alignment_score:.0f}%) - timeframes conflicting"
            elif overall_confidence < 55:
                reasoning = f"Low confidence ({overall_confidence:.0f}%) - wait for clearer signals"
            else:
                reasoning = "Mixed signals - no clear edge"
        
        return MultiTimeframeBias(
            symbol=symbol,
            timestamp=datetime.utcnow().isoformat(),
            hourly_direction=directions[Timeframe.HOURLY],
            four_hour_direction=directions[Timeframe.FOUR_HOUR],
            daily_direction=directions[Timeframe.DAILY],
            weekly_direction=directions[Timeframe.WEEKLY],
            hourly_confidence=confidences[Timeframe.HOURLY],
            four_hour_confidence=confidences[Timeframe.FOUR_HOUR],
            daily_confidence=confidences[Timeframe.DAILY],
            weekly_confidence=confidences[Timeframe.WEEKLY],
            overall_direction=overall_direction,
            overall_confidence=overall_confidence,
            alignment_score=alignment_score,
            tradeable=tradeable,
            trade_reasoning=reasoning
        )
    
    async def _get_or_generate_weekly(self, symbol: str) -> Optional[TimeframePrediction]:
        """Get cached weekly prediction or generate new one."""
        cache_key = f"weekly_{symbol}"
        now = datetime.utcnow()
        
        # Check cache (valid for 6 hours)
        if cache_key in self._weekly_cache:
            cache_time = self._cache_timestamps.get(cache_key)
            if cache_time and (now - cache_time) < timedelta(hours=6):
                return self._weekly_cache[cache_key]
        
        # Generate new
        pred = await self.generate_prediction(symbol, Timeframe.WEEKLY)
        if pred:
            self._weekly_cache[cache_key] = pred
            self._cache_timestamps[cache_key] = now
        
        return pred
    
    async def _get_or_generate_daily(
        self, 
        symbol: str, 
        weekly: Optional[TimeframePrediction]
    ) -> Optional[TimeframePrediction]:
        """Get cached daily prediction or generate new one."""
        cache_key = f"daily_{symbol}"
        now = datetime.utcnow()
        
        # Check cache (valid for 2 hours)
        if cache_key in self._daily_cache:
            cache_time = self._cache_timestamps.get(cache_key)
            if cache_time and (now - cache_time) < timedelta(hours=2):
                return self._daily_cache[cache_key]
        
        # Generate new
        higher_dir = weekly.direction if weekly else None
        pred = await self.generate_prediction(symbol, Timeframe.DAILY, higher_dir)
        if pred:
            self._daily_cache[cache_key] = pred
            self._cache_timestamps[cache_key] = now
        
        return pred
    
    def format_bias_report(self, biases: List[MultiTimeframeBias]) -> str:
        """Format multi-timeframe report for Telegram."""
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        
        def dir_emoji(d):
            return "🟢" if d == "LONG" else "🔴" if d == "SHORT" else "⚪"
        
        msg = f"""🔮 *CORACLE MULTI-TIMEFRAME BIAS*
📅 {ts}

*Timeframe Hierarchy:*
Weekly → Daily → 4H → 1H (entry)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        for bias in biases:
            alignment_emoji = "✅" if bias.alignment_score >= 75 else "⚠️" if bias.alignment_score >= 50 else "❌"
            tradeable_emoji = "🎯" if bias.tradeable else "⏸️"
            
            msg += f"""
*{bias.symbol}* {dir_emoji(bias.overall_direction)} {bias.overall_direction}

┌ 📅 Weekly:  {dir_emoji(bias.weekly_direction)} {bias.weekly_direction} ({bias.weekly_confidence:.0f}%)
├ 📊 Daily:   {dir_emoji(bias.daily_direction)} {bias.daily_direction} ({bias.daily_confidence:.0f}%)
├ ⏰ 4H:      {dir_emoji(bias.four_hour_direction)} {bias.four_hour_direction} ({bias.four_hour_confidence:.0f}%)
└ ⚡ 1H:      {dir_emoji(bias.hourly_direction)} {bias.hourly_direction} ({bias.hourly_confidence:.0f}%)

{alignment_emoji} Alignment: *{bias.alignment_score:.0f}%*
{tradeable_emoji} {bias.trade_reasoning}

"""
        
        # Summary
        tradeable_count = sum(1 for b in biases if b.tradeable)
        long_count = sum(1 for b in biases if b.overall_direction == "LONG")
        short_count = sum(1 for b in biases if b.overall_direction == "SHORT")
        
        msg += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*Summary:*
• Tradeable setups: {tradeable_count}/{len(biases)}
• Market bias: {"🟢 BULLISH" if long_count > short_count else "🔴 BEARISH" if short_count > long_count else "⚪ MIXED"}

_Higher timeframes = stronger signals_
_Trade WITH the weekly, not against it_
"""
        return msg


# Singleton
_timeframe_oracle: Optional[TimeframeOracle] = None


def get_timeframe_oracle() -> TimeframeOracle:
    """Get or create the oracle instance."""
    global _timeframe_oracle
    if _timeframe_oracle is None:
        _timeframe_oracle = TimeframeOracle()
    return _timeframe_oracle


