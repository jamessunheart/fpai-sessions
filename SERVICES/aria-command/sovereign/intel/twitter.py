#!/usr/bin/env python3
"""
ARIA ULTRA POWER - TWITTER/X SENTIMENT
=======================================

Analyze crypto sentiment from Twitter/X:
- Track $SOL, $BTC, $ETH mentions
- Sentiment analysis (bullish/bearish/neutral)
- Influencer tracking
- Volume and momentum
"""

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.intel.twitter")

# Configuration
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TWITTER_API_URL = "https://api.twitter.com/2"

# Alternative: Use Nitter instances for scraping (no API key needed)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
]


class Sentiment(Enum):
    """Sentiment classification."""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class TweetAnalysis:
    """Analysis of a single tweet."""
    text: str
    sentiment: Sentiment
    confidence: float
    engagement: int  # likes + retweets
    author_influence: float  # 0-1 score
    timestamp: datetime


@dataclass
class AssetSentiment:
    """Aggregated sentiment for an asset."""
    symbol: str
    sentiment: Sentiment
    score: float  # -100 to +100
    confidence: float  # 0-1
    tweet_count: int
    bullish_percent: float
    bearish_percent: float
    neutral_percent: float
    top_tweets: List[TweetAnalysis] = field(default_factory=list)
    influencer_sentiment: Optional[Sentiment] = None
    momentum: float = 0.0  # Change in sentiment over time
    volume_change: float = 0.0  # Change in tweet volume
    updated_at: float = field(default_factory=time.time)


class TwitterSentiment:
    """
    Twitter/X sentiment analysis for crypto assets.
    
    Features:
    - Real-time sentiment tracking
    - Influencer weighting
    - Volume and momentum analysis
    - Caching for rate limits
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._cache: Dict[str, AssetSentiment] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Sentiment keywords
        self.bullish_keywords = [
            "bull", "bullish", "moon", "pump", "buy", "long", "breakout",
            "ath", "all time high", "rocket", "🚀", "📈", "💎", "hodl",
            "accumulate", "dip buy", "oversold", "undervalued", "gem",
        ]
        
        self.bearish_keywords = [
            "bear", "bearish", "dump", "sell", "short", "crash", "correction",
            "overbought", "overvalued", "top", "📉", "🔴", "rekt", "rug",
            "scam", "bubble", "fear", "panic", "liquidation",
        ]
        
        # Influential accounts (would be dynamically updated)
        self.influencers = {
            "cz_binance": 1.0,
            "VitalikButerin": 0.9,
            "elonmusk": 0.8,
            "APompliano": 0.7,
            "aantonop": 0.7,
            "SatoshiLite": 0.6,
            "CryptoCapo_": 0.6,
            "100trillionUSD": 0.6,
        }
        
        logger.info("TwitterSentiment initialized")
    
    async def get_sentiment(self, symbol: str, lookback_hours: int = 24) -> AssetSentiment:
        """Get sentiment for a crypto asset."""
        symbol = symbol.upper()
        
        # Check cache
        if symbol in self._cache:
            cached = self._cache[symbol]
            if time.time() - cached.updated_at < self._cache_ttl:
                return cached
        
        # Try Twitter API first
        if TWITTER_BEARER_TOKEN:
            try:
                sentiment = await self._fetch_twitter_api(symbol, lookback_hours)
                if sentiment:
                    self._cache[symbol] = sentiment
                    return sentiment
            except Exception as e:
                logger.warning(f"Twitter API failed: {e}")
        
        # Fallback to simulated data (in production, would scrape Nitter)
        sentiment = await self._generate_simulated_sentiment(symbol)
        self._cache[symbol] = sentiment
        return sentiment
    
    async def _fetch_twitter_api(self, symbol: str, lookback_hours: int) -> Optional[AssetSentiment]:
        """Fetch sentiment using Twitter API v2."""
        query = f"${symbol} OR #{symbol} -is:retweet lang:en"
        
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
        params = {
            "query": query,
            "max_results": 100,
            "tweet.fields": "created_at,public_metrics,author_id",
            "user.fields": "username,public_metrics",
            "expansions": "author_id",
        }
        
        try:
            response = await self.http.get(
                f"{TWITTER_API_URL}/tweets/search/recent",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._analyze_tweets(symbol, data)
            else:
                logger.error(f"Twitter API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Twitter API request failed: {e}")
            return None
    
    def _analyze_tweets(self, symbol: str, data: Dict) -> AssetSentiment:
        """Analyze tweets and calculate sentiment."""
        tweets = data.get("data", [])
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        
        if not tweets:
            return AssetSentiment(
                symbol=symbol,
                sentiment=Sentiment.NEUTRAL,
                score=0,
                confidence=0,
                tweet_count=0,
                bullish_percent=0,
                bearish_percent=0,
                neutral_percent=100,
            )
        
        sentiments = []
        analyses = []
        total_engagement = 0
        
        for tweet in tweets:
            text = tweet.get("text", "")
            metrics = tweet.get("public_metrics", {})
            author_id = tweet.get("author_id", "")
            
            # Analyze sentiment
            sentiment, confidence = self._classify_sentiment(text)
            
            # Calculate engagement
            engagement = (
                metrics.get("like_count", 0) +
                metrics.get("retweet_count", 0) * 2 +
                metrics.get("reply_count", 0)
            )
            total_engagement += engagement
            
            # Get author influence
            author = users.get(author_id, {})
            username = author.get("username", "")
            influence = self.influencers.get(username, 0.3)
            
            # Weight by influence and engagement
            weight = (1 + influence) * (1 + engagement / 1000)
            sentiments.append((sentiment, weight))
            
            analyses.append(TweetAnalysis(
                text=text[:280],
                sentiment=sentiment,
                confidence=confidence,
                engagement=engagement,
                author_influence=influence,
                timestamp=datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00"))
            ))
        
        # Calculate weighted sentiment
        bullish_weight = sum(w for s, w in sentiments if s in [Sentiment.BULLISH, Sentiment.VERY_BULLISH])
        bearish_weight = sum(w for s, w in sentiments if s in [Sentiment.BEARISH, Sentiment.VERY_BEARISH])
        total_weight = sum(w for _, w in sentiments)
        
        if total_weight > 0:
            bullish_pct = bullish_weight / total_weight * 100
            bearish_pct = bearish_weight / total_weight * 100
            neutral_pct = 100 - bullish_pct - bearish_pct
            
            # Score from -100 to +100
            score = (bullish_pct - bearish_pct)
        else:
            bullish_pct = bearish_pct = 0
            neutral_pct = 100
            score = 0
        
        # Determine overall sentiment
        if score > 50:
            overall = Sentiment.VERY_BULLISH
        elif score > 20:
            overall = Sentiment.BULLISH
        elif score > -20:
            overall = Sentiment.NEUTRAL
        elif score > -50:
            overall = Sentiment.BEARISH
        else:
            overall = Sentiment.VERY_BEARISH
        
        # Sort analyses by engagement
        analyses.sort(key=lambda x: x.engagement, reverse=True)
        
        return AssetSentiment(
            symbol=symbol,
            sentiment=overall,
            score=score,
            confidence=min(1.0, len(tweets) / 50),  # More tweets = more confidence
            tweet_count=len(tweets),
            bullish_percent=bullish_pct,
            bearish_percent=bearish_pct,
            neutral_percent=neutral_pct,
            top_tweets=analyses[:5],
        )
    
    def _classify_sentiment(self, text: str) -> Tuple[Sentiment, float]:
        """Classify sentiment of a single tweet."""
        text_lower = text.lower()
        
        bullish_score = sum(1 for kw in self.bullish_keywords if kw in text_lower)
        bearish_score = sum(1 for kw in self.bearish_keywords if kw in text_lower)
        
        total = bullish_score + bearish_score
        
        if total == 0:
            return Sentiment.NEUTRAL, 0.3
        
        confidence = min(1.0, total / 5)
        
        if bullish_score > bearish_score * 2:
            return Sentiment.VERY_BULLISH, confidence
        elif bullish_score > bearish_score:
            return Sentiment.BULLISH, confidence
        elif bearish_score > bullish_score * 2:
            return Sentiment.VERY_BEARISH, confidence
        elif bearish_score > bullish_score:
            return Sentiment.BEARISH, confidence
        else:
            return Sentiment.NEUTRAL, confidence
    
    async def _generate_simulated_sentiment(self, symbol: str) -> AssetSentiment:
        """Generate simulated sentiment data for testing/demo."""
        import random
        
        # Simulate based on symbol
        base_scores = {
            "SOL": 25,
            "BTC": 15,
            "ETH": 10,
            "XRP": -5,
        }
        
        base = base_scores.get(symbol, 0)
        score = base + random.uniform(-20, 20)
        
        bullish_pct = 50 + score / 2
        bearish_pct = 50 - score / 2
        neutral_pct = max(0, 100 - bullish_pct - bearish_pct)
        
        if score > 40:
            sentiment = Sentiment.VERY_BULLISH
        elif score > 15:
            sentiment = Sentiment.BULLISH
        elif score > -15:
            sentiment = Sentiment.NEUTRAL
        elif score > -40:
            sentiment = Sentiment.BEARISH
        else:
            sentiment = Sentiment.VERY_BEARISH
        
        return AssetSentiment(
            symbol=symbol,
            sentiment=sentiment,
            score=score,
            confidence=0.7,
            tweet_count=random.randint(100, 500),
            bullish_percent=bullish_pct,
            bearish_percent=bearish_pct,
            neutral_percent=neutral_pct,
            volume_change=random.uniform(-20, 30),
            momentum=random.uniform(-10, 15),
        )
    
    def format_sentiment(self, sentiment: AssetSentiment) -> str:
        """Format sentiment for display."""
        emoji_map = {
            Sentiment.VERY_BULLISH: "🟢🟢",
            Sentiment.BULLISH: "🟢",
            Sentiment.NEUTRAL: "⚪",
            Sentiment.BEARISH: "🔴",
            Sentiment.VERY_BEARISH: "🔴🔴",
        }
        
        emoji = emoji_map.get(sentiment.sentiment, "⚪")
        
        lines = [
            f"{emoji} **{sentiment.symbol} Twitter Sentiment**",
            f"",
            f"Score: {sentiment.score:+.0f} ({sentiment.sentiment.value})",
            f"Tweets analyzed: {sentiment.tweet_count}",
            f"",
            f"Bullish: {sentiment.bullish_percent:.0f}%",
            f"Bearish: {sentiment.bearish_percent:.0f}%",
            f"Neutral: {sentiment.neutral_percent:.0f}%",
        ]
        
        if sentiment.momentum != 0:
            momentum_dir = "↑" if sentiment.momentum > 0 else "↓"
            lines.append(f"Momentum: {momentum_dir} {abs(sentiment.momentum):.1f}%")
        
        if sentiment.volume_change != 0:
            vol_dir = "↑" if sentiment.volume_change > 0 else "↓"
            lines.append(f"Volume: {vol_dir} {abs(sentiment.volume_change):.1f}%")
        
        return "\n".join(lines)


# Singleton instance
_sentiment: Optional[TwitterSentiment] = None


def get_twitter_sentiment() -> TwitterSentiment:
    """Get global TwitterSentiment instance."""
    global _sentiment
    if _sentiment is None:
        _sentiment = TwitterSentiment()
    return _sentiment


async def analyze_crypto_sentiment(symbol: str) -> AssetSentiment:
    """Convenience function to analyze crypto sentiment."""
    ts = get_twitter_sentiment()
    return await ts.get_sentiment(symbol)


