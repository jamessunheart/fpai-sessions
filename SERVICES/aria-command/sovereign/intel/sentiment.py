#!/usr/bin/env python3
"""
ARIA ULTRA POWER - UNIFIED SENTIMENT
=====================================

Combines all external data sources into a unified sentiment score:
- Twitter sentiment
- On-chain activity
- News sentiment
- WhaleTrack signals

Provides a single confidence-weighted score for trading decisions.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.intel.sentiment")

# WhaleTrack API
WHALETRACK_URL = "http://198.54.123.234:8600"


class SentimentLevel(Enum):
    """Overall sentiment level."""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    SLIGHTLY_BULLISH = "slightly_bullish"
    NEUTRAL = "neutral"
    SLIGHTLY_BEARISH = "slightly_bearish"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class SentimentSource:
    """Individual source sentiment."""
    name: str
    score: float  # -100 to +100
    confidence: float  # 0-1
    weight: float  # Importance weight
    details: Dict = field(default_factory=dict)


@dataclass
class SentimentScore:
    """Combined sentiment score for an asset."""
    symbol: str
    
    # Combined score
    score: float  # -100 to +100
    confidence: float  # 0-1
    level: SentimentLevel
    
    # Individual sources
    sources: List[SentimentSource]
    
    # Signals
    bullish_signals: List[str]
    bearish_signals: List[str]
    
    # Recommendation
    action: str  # "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"
    action_confidence: float
    
    # Metadata
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "score": self.score,
            "confidence": self.confidence,
            "level": self.level.value,
            "action": self.action,
            "action_confidence": self.action_confidence,
            "bullish_signals": self.bullish_signals,
            "bearish_signals": self.bearish_signals,
            "sources": [
                {
                    "name": s.name,
                    "score": s.score,
                    "confidence": s.confidence,
                }
                for s in self.sources
            ],
        }


class UnifiedSentiment:
    """
    Unified sentiment analysis combining all external data.
    
    Weights:
    - WhaleTrack: 35% (primary trading signal)
    - On-chain: 25% (fundamental)
    - Twitter: 20% (social)
    - News: 20% (news events)
    """
    
    # Source weights
    WEIGHTS = {
        "whaletrack": 0.35,
        "onchain": 0.25,
        "twitter": 0.20,
        "news": 0.20,
    }
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._cache: Dict[str, SentimentScore] = {}
        self._cache_ttl = 180  # 3 minutes
        
        logger.info("UnifiedSentiment initialized")
    
    async def get_sentiment(self, symbol: str) -> SentimentScore:
        """Get unified sentiment for an asset."""
        symbol = symbol.upper()
        
        # Check cache
        if symbol in self._cache:
            cached = self._cache[symbol]
            if time.time() - cached.updated_at < self._cache_ttl:
                return cached
        
        # Fetch from all sources in parallel
        results = await asyncio.gather(
            self._get_whaletrack_sentiment(symbol),
            self._get_onchain_sentiment(symbol),
            self._get_twitter_sentiment(symbol),
            self._get_news_sentiment(symbol),
            return_exceptions=True,
        )
        
        sources = []
        bullish_signals = []
        bearish_signals = []
        
        # Process WhaleTrack
        if isinstance(results[0], SentimentSource):
            sources.append(results[0])
            if results[0].score > 20:
                bullish_signals.append(f"WhaleTrack: {results[0].details.get('bias', 'bullish')}")
            elif results[0].score < -20:
                bearish_signals.append(f"WhaleTrack: {results[0].details.get('bias', 'bearish')}")
        
        # Process On-chain
        if isinstance(results[1], SentimentSource):
            sources.append(results[1])
            if results[1].score > 20:
                bullish_signals.append(f"On-chain: {results[1].details.get('signal', 'whale buying')}")
            elif results[1].score < -20:
                bearish_signals.append(f"On-chain: {results[1].details.get('signal', 'exchange inflow')}")
        
        # Process Twitter
        if isinstance(results[2], SentimentSource):
            sources.append(results[2])
            if results[2].score > 20:
                bullish_signals.append(f"Twitter: {results[2].details.get('tweets', 0)} bullish tweets")
            elif results[2].score < -20:
                bearish_signals.append(f"Twitter: Negative sentiment trending")
        
        # Process News
        if isinstance(results[3], SentimentSource):
            sources.append(results[3])
            if results[3].score > 20:
                bullish_signals.append(f"News: Positive coverage")
            elif results[3].score < -20:
                bearish_signals.append(f"News: Negative headlines")
        
        # Calculate combined score
        if sources:
            total_weight = sum(s.weight * s.confidence for s in sources)
            if total_weight > 0:
                combined_score = sum(s.score * s.weight * s.confidence for s in sources) / total_weight
                combined_confidence = sum(s.confidence * s.weight for s in sources) / sum(s.weight for s in sources)
            else:
                combined_score = 0
                combined_confidence = 0
        else:
            combined_score = 0
            combined_confidence = 0
        
        # Determine level
        level = self._score_to_level(combined_score)
        
        # Determine action
        action, action_confidence = self._score_to_action(combined_score, combined_confidence)
        
        sentiment = SentimentScore(
            symbol=symbol,
            score=combined_score,
            confidence=combined_confidence,
            level=level,
            sources=sources,
            bullish_signals=bullish_signals,
            bearish_signals=bearish_signals,
            action=action,
            action_confidence=action_confidence,
        )
        
        self._cache[symbol] = sentiment
        return sentiment
    
    async def _get_whaletrack_sentiment(self, symbol: str) -> SentimentSource:
        """Get sentiment from WhaleTrack."""
        try:
            response = await self.http.get(f"{WHALETRACK_URL}/api/liquidity-clarity")
            
            if response.status_code == 200:
                data = response.json()
                symbols = data.get("symbols", {})
                
                symbol_key = f"{symbol}/USDT"
                if symbol_key in symbols:
                    asset = symbols[symbol_key]
                    bias = asset.get("bias", "neutral")
                    strength = asset.get("bias_strength", 0)
                    clarity = asset.get("clarity_score", 0)
                    
                    # Convert to -100 to +100 score
                    if bias == "bullish":
                        score = strength
                    elif bias == "bearish":
                        score = -strength
                    else:
                        score = 0
                    
                    return SentimentSource(
                        name="WhaleTrack",
                        score=score,
                        confidence=clarity / 100,
                        weight=self.WEIGHTS["whaletrack"],
                        details={
                            "bias": bias,
                            "strength": strength,
                            "clarity": clarity,
                            "action": asset.get("recommended_action"),
                        }
                    )
        except Exception as e:
            logger.error(f"WhaleTrack sentiment error: {e}")
        
        return SentimentSource(
            name="WhaleTrack",
            score=0,
            confidence=0,
            weight=self.WEIGHTS["whaletrack"],
        )
    
    async def _get_onchain_sentiment(self, symbol: str) -> SentimentSource:
        """Get sentiment from on-chain data."""
        try:
            from .onchain import get_onchain_intel
            
            intel = get_onchain_intel()
            summary = await intel.get_summary(symbol)
            
            # Convert to score
            if summary.overall_sentiment == "bullish":
                score = 30 + (summary.bullish_signals - summary.bearish_signals) * 5
            elif summary.overall_sentiment == "bearish":
                score = -30 - (summary.bearish_signals - summary.bullish_signals) * 5
            else:
                score = (summary.bullish_signals - summary.bearish_signals) * 10
            
            score = max(-100, min(100, score))
            
            return SentimentSource(
                name="On-Chain",
                score=score,
                confidence=summary.confidence,
                weight=self.WEIGHTS["onchain"],
                details={
                    "signal": summary.overall_sentiment,
                    "whale_buys": summary.total_whale_buys,
                    "whale_sells": summary.total_whale_sells,
                }
            )
        except Exception as e:
            logger.error(f"On-chain sentiment error: {e}")
            return SentimentSource(
                name="On-Chain",
                score=0,
                confidence=0,
                weight=self.WEIGHTS["onchain"],
            )
    
    async def _get_twitter_sentiment(self, symbol: str) -> SentimentSource:
        """Get sentiment from Twitter."""
        try:
            from .twitter import get_twitter_sentiment
            
            ts = get_twitter_sentiment()
            sentiment = await ts.get_sentiment(symbol)
            
            return SentimentSource(
                name="Twitter",
                score=sentiment.score,
                confidence=sentiment.confidence,
                weight=self.WEIGHTS["twitter"],
                details={
                    "tweets": sentiment.tweet_count,
                    "bullish_pct": sentiment.bullish_percent,
                    "bearish_pct": sentiment.bearish_percent,
                }
            )
        except Exception as e:
            logger.error(f"Twitter sentiment error: {e}")
            return SentimentSource(
                name="Twitter",
                score=0,
                confidence=0,
                weight=self.WEIGHTS["twitter"],
            )
    
    async def _get_news_sentiment(self, symbol: str) -> SentimentSource:
        """Get sentiment from news."""
        try:
            from .news import get_news_aggregator, NewsSentiment
            
            agg = get_news_aggregator()
            summary = await agg.get_news_for_symbol(symbol)
            
            # Convert to score
            sentiment_scores = {
                NewsSentiment.VERY_POSITIVE: 60,
                NewsSentiment.POSITIVE: 30,
                NewsSentiment.NEUTRAL: 0,
                NewsSentiment.NEGATIVE: -30,
                NewsSentiment.VERY_NEGATIVE: -60,
            }
            
            base_score = sentiment_scores.get(summary.overall_sentiment, 0)
            
            # Adjust based on article counts
            if summary.positive_count > summary.negative_count:
                bonus = min(20, (summary.positive_count - summary.negative_count) * 3)
            else:
                bonus = max(-20, (summary.positive_count - summary.negative_count) * 3)
            
            score = max(-100, min(100, base_score + bonus))
            confidence = min(1.0, len(summary.articles) / 10)
            
            return SentimentSource(
                name="News",
                score=score,
                confidence=confidence,
                weight=self.WEIGHTS["news"],
                details={
                    "articles": len(summary.articles),
                    "positive": summary.positive_count,
                    "negative": summary.negative_count,
                    "market_moving": len(summary.market_moving_events),
                }
            )
        except Exception as e:
            logger.error(f"News sentiment error: {e}")
            return SentimentSource(
                name="News",
                score=0,
                confidence=0,
                weight=self.WEIGHTS["news"],
            )
    
    def _score_to_level(self, score: float) -> SentimentLevel:
        """Convert score to sentiment level."""
        if score >= 50:
            return SentimentLevel.VERY_BULLISH
        elif score >= 25:
            return SentimentLevel.BULLISH
        elif score >= 10:
            return SentimentLevel.SLIGHTLY_BULLISH
        elif score >= -10:
            return SentimentLevel.NEUTRAL
        elif score >= -25:
            return SentimentLevel.SLIGHTLY_BEARISH
        elif score >= -50:
            return SentimentLevel.BEARISH
        else:
            return SentimentLevel.VERY_BEARISH
    
    def _score_to_action(self, score: float, confidence: float) -> tuple[str, float]:
        """Convert score to trading action."""
        # Require minimum confidence
        if confidence < 0.4:
            return "HOLD", confidence
        
        # Map score to action
        if score >= 60 and confidence >= 0.7:
            return "STRONG_BUY", confidence
        elif score >= 30:
            return "BUY", confidence
        elif score >= -30:
            return "HOLD", confidence
        elif score >= -60:
            return "SELL", confidence
        else:
            if confidence >= 0.7:
                return "STRONG_SELL", confidence
            else:
                return "SELL", confidence
    
    def format_sentiment(self, sentiment: SentimentScore) -> str:
        """Format sentiment for display."""
        emoji_map = {
            SentimentLevel.VERY_BULLISH: "🟢🟢",
            SentimentLevel.BULLISH: "🟢",
            SentimentLevel.SLIGHTLY_BULLISH: "🟢",
            SentimentLevel.NEUTRAL: "⚪",
            SentimentLevel.SLIGHTLY_BEARISH: "🔴",
            SentimentLevel.BEARISH: "🔴",
            SentimentLevel.VERY_BEARISH: "🔴🔴",
        }
        
        action_emoji = {
            "STRONG_BUY": "🚀",
            "BUY": "📈",
            "HOLD": "⏸️",
            "SELL": "📉",
            "STRONG_SELL": "🔻",
        }
        
        level_emoji = emoji_map.get(sentiment.level, "⚪")
        act_emoji = action_emoji.get(sentiment.action, "⏸️")
        
        lines = [
            f"{level_emoji} **{sentiment.symbol} Combined Sentiment**",
            "",
            f"**Score:** {sentiment.score:+.0f} ({sentiment.level.value})",
            f"**Confidence:** {sentiment.confidence:.0%}",
            f"**Action:** {act_emoji} {sentiment.action} ({sentiment.action_confidence:.0%})",
            "",
            "**Sources:**",
        ]
        
        for source in sentiment.sources:
            src_emoji = "🟢" if source.score > 15 else "🔴" if source.score < -15 else "⚪"
            lines.append(f"• {source.name}: {src_emoji} {source.score:+.0f} ({source.confidence:.0%})")
        
        if sentiment.bullish_signals:
            lines.append("")
            lines.append("**🟢 Bullish Signals:**")
            for signal in sentiment.bullish_signals[:3]:
                lines.append(f"• {signal}")
        
        if sentiment.bearish_signals:
            lines.append("")
            lines.append("**🔴 Bearish Signals:**")
            for signal in sentiment.bearish_signals[:3]:
                lines.append(f"• {signal}")
        
        return "\n".join(lines)


# Singleton instance
_unified: Optional[UnifiedSentiment] = None


def get_unified_sentiment() -> UnifiedSentiment:
    """Get global UnifiedSentiment instance."""
    global _unified
    if _unified is None:
        _unified = UnifiedSentiment()
    return _unified


async def calculate_combined_sentiment(symbol: str) -> SentimentScore:
    """Convenience function to get combined sentiment."""
    us = get_unified_sentiment()
    return await us.get_sentiment(symbol)


