#!/usr/bin/env python3
"""
ARIA ULTRA POWER - NEWS AGGREGATOR
===================================

Aggregate and analyze crypto news:
- Multiple news sources (CoinDesk, The Block, etc.)
- Market-moving event detection
- Keyword alerts
- Sentiment extraction
"""

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx
import feedparser

logger = logging.getLogger("aria.intel.news")

# API Keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")

# News Sources (RSS feeds)
NEWS_SOURCES = {
    "coindesk": {
        "name": "CoinDesk",
        "rss": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "weight": 1.0,
    },
    "cointelegraph": {
        "name": "Cointelegraph",
        "rss": "https://cointelegraph.com/rss",
        "weight": 0.9,
    },
    "theblock": {
        "name": "The Block",
        "rss": "https://www.theblock.co/rss.xml",
        "weight": 0.95,
    },
    "decrypt": {
        "name": "Decrypt",
        "rss": "https://decrypt.co/feed",
        "weight": 0.8,
    },
    "bitcoinmagazine": {
        "name": "Bitcoin Magazine",
        "rss": "https://bitcoinmagazine.com/feed",
        "weight": 0.85,
    },
}


class NewsImpact(Enum):
    """Impact level of news."""
    CRITICAL = "critical"  # Major market-moving event
    HIGH = "high"  # Significant news
    MEDIUM = "medium"  # Notable news
    LOW = "low"  # Minor news
    NOISE = "noise"  # Irrelevant


class NewsSentiment(Enum):
    """Sentiment of news."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class NewsArticle:
    """A news article."""
    title: str
    summary: str
    url: str
    source: str
    published: datetime
    symbols: List[str]  # Related crypto symbols
    sentiment: NewsSentiment
    impact: NewsImpact
    keywords: List[str]
    
    @property
    def age_hours(self) -> float:
        """Hours since publication."""
        return (datetime.now() - self.published).total_seconds() / 3600


@dataclass
class NewsSummary:
    """Summary of news for an asset."""
    symbol: str
    articles: List[NewsArticle]
    positive_count: int
    negative_count: int
    neutral_count: int
    overall_sentiment: NewsSentiment
    top_headlines: List[str]
    market_moving_events: List[NewsArticle]
    updated_at: float = field(default_factory=time.time)


class NewsAggregator:
    """
    Crypto news aggregation and analysis.
    
    Features:
    - Multi-source aggregation
    - Sentiment analysis
    - Impact classification
    - Market-moving event detection
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._cache: Dict[str, NewsSummary] = {}
        self._cache_ttl = 300  # 5 minutes
        self._all_articles: List[NewsArticle] = []
        self._last_fetch = 0
        self._fetch_interval = 600  # 10 minutes
        
        # Impact keywords
        self.high_impact_keywords = [
            "sec", "regulation", "ban", "approval", "etf", "hack", "exploit",
            "partnership", "adoption", "billion", "million", "crash", "surge",
            "lawsuit", "investigation", "breaking", "emergency",
        ]
        
        self.positive_keywords = [
            "bullish", "surge", "rally", "adoption", "partnership", "approval",
            "growth", "record", "ath", "breakthrough", "milestone", "launch",
            "upgrade", "integration", "institutional",
        ]
        
        self.negative_keywords = [
            "bearish", "crash", "dump", "hack", "exploit", "ban", "lawsuit",
            "investigation", "fraud", "scam", "fail", "collapse", "warning",
            "risk", "concern", "delay", "reject",
        ]
        
        # Asset keywords
        self.asset_keywords = {
            "BTC": ["bitcoin", "btc", "satoshi", "lightning"],
            "ETH": ["ethereum", "eth", "vitalik", "erc20", "defi"],
            "SOL": ["solana", "sol", "phantom", "serum"],
            "XRP": ["ripple", "xrp", "sec lawsuit"],
        }
        
        logger.info("NewsAggregator initialized")
    
    async def fetch_all_news(self) -> List[NewsArticle]:
        """Fetch news from all sources."""
        current_time = time.time()
        
        # Check if we need to fetch
        if current_time - self._last_fetch < self._fetch_interval:
            return self._all_articles
        
        articles = []
        
        # Fetch from RSS feeds
        for source_id, source in NEWS_SOURCES.items():
            try:
                source_articles = await self._fetch_rss(source_id, source)
                articles.extend(source_articles)
            except Exception as e:
                logger.warning(f"Failed to fetch {source_id}: {e}")
        
        # Fetch from CryptoPanic if available
        if CRYPTOPANIC_API_KEY:
            try:
                panic_articles = await self._fetch_cryptopanic()
                articles.extend(panic_articles)
            except Exception as e:
                logger.warning(f"Failed to fetch CryptoPanic: {e}")
        
        # Sort by recency
        articles.sort(key=lambda a: a.published, reverse=True)
        
        # Keep last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        articles = [a for a in articles if a.published > cutoff]
        
        self._all_articles = articles[:100]  # Keep top 100
        self._last_fetch = current_time
        
        logger.info(f"Fetched {len(self._all_articles)} news articles")
        return self._all_articles
    
    async def _fetch_rss(self, source_id: str, source: Dict) -> List[NewsArticle]:
        """Fetch and parse RSS feed."""
        try:
            response = await self.http.get(source["rss"])
            if response.status_code != 200:
                return []
            
            feed = feedparser.parse(response.text)
            articles = []
            
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))[:500]
                url = entry.get("link", "")
                
                # Parse published date
                published = None
                if "published_parsed" in entry and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif "updated_parsed" in entry and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                else:
                    published = datetime.now()
                
                # Analyze article
                symbols = self._extract_symbols(title + " " + summary)
                sentiment = self._analyze_sentiment(title + " " + summary)
                impact = self._classify_impact(title + " " + summary)
                keywords = self._extract_keywords(title + " " + summary)
                
                articles.append(NewsArticle(
                    title=title,
                    summary=summary,
                    url=url,
                    source=source["name"],
                    published=published,
                    symbols=symbols,
                    sentiment=sentiment,
                    impact=impact,
                    keywords=keywords,
                ))
            
            return articles
        except Exception as e:
            logger.error(f"RSS fetch error for {source_id}: {e}")
            return []
    
    async def _fetch_cryptopanic(self) -> List[NewsArticle]:
        """Fetch from CryptoPanic API."""
        try:
            url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&public=true"
            response = await self.http.get(url)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            articles = []
            
            for post in data.get("results", [])[:20]:
                title = post.get("title", "")
                url = post.get("url", "")
                published = datetime.fromisoformat(post.get("created_at", "").replace("Z", "+00:00"))
                
                # CryptoPanic provides sentiment
                votes = post.get("votes", {})
                pos = votes.get("positive", 0)
                neg = votes.get("negative", 0)
                
                if pos > neg * 2:
                    sentiment = NewsSentiment.VERY_POSITIVE
                elif pos > neg:
                    sentiment = NewsSentiment.POSITIVE
                elif neg > pos * 2:
                    sentiment = NewsSentiment.VERY_NEGATIVE
                elif neg > pos:
                    sentiment = NewsSentiment.NEGATIVE
                else:
                    sentiment = NewsSentiment.NEUTRAL
                
                # Get symbols
                currencies = post.get("currencies", [])
                symbols = [c.get("code", "").upper() for c in currencies]
                
                articles.append(NewsArticle(
                    title=title,
                    summary="",
                    url=url,
                    source="CryptoPanic",
                    published=published,
                    symbols=symbols,
                    sentiment=sentiment,
                    impact=self._classify_impact(title),
                    keywords=self._extract_keywords(title),
                ))
            
            return articles
        except Exception as e:
            logger.error(f"CryptoPanic fetch error: {e}")
            return []
    
    async def get_news_for_symbol(self, symbol: str, hours: int = 24) -> NewsSummary:
        """Get news summary for a specific asset."""
        symbol = symbol.upper()
        
        # Check cache
        cache_key = f"{symbol}_{hours}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached.updated_at < self._cache_ttl:
                return cached
        
        # Fetch latest news
        all_articles = await self.fetch_all_news()
        
        # Filter for symbol
        cutoff = datetime.now() - timedelta(hours=hours)
        relevant = [
            a for a in all_articles
            if symbol in a.symbols or symbol.lower() in a.title.lower()
            and a.published > cutoff
        ]
        
        if not relevant:
            # Try broader search
            symbol_keywords = self.asset_keywords.get(symbol, [symbol.lower()])
            relevant = [
                a for a in all_articles
                if any(kw in (a.title + a.summary).lower() for kw in symbol_keywords)
                and a.published > cutoff
            ]
        
        # Count sentiments
        positive = sum(1 for a in relevant if a.sentiment in [NewsSentiment.POSITIVE, NewsSentiment.VERY_POSITIVE])
        negative = sum(1 for a in relevant if a.sentiment in [NewsSentiment.NEGATIVE, NewsSentiment.VERY_NEGATIVE])
        neutral = len(relevant) - positive - negative
        
        # Overall sentiment
        if positive > negative * 1.5:
            overall = NewsSentiment.POSITIVE if positive < negative * 2.5 else NewsSentiment.VERY_POSITIVE
        elif negative > positive * 1.5:
            overall = NewsSentiment.NEGATIVE if negative < positive * 2.5 else NewsSentiment.VERY_NEGATIVE
        else:
            overall = NewsSentiment.NEUTRAL
        
        # Get market-moving events
        market_moving = [a for a in relevant if a.impact in [NewsImpact.CRITICAL, NewsImpact.HIGH]]
        
        summary = NewsSummary(
            symbol=symbol,
            articles=relevant,
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            overall_sentiment=overall,
            top_headlines=[a.title for a in relevant[:5]],
            market_moving_events=market_moving,
        )
        
        self._cache[cache_key] = summary
        return summary
    
    def _extract_symbols(self, text: str) -> List[str]:
        """Extract crypto symbols from text."""
        symbols = []
        text_lower = text.lower()
        
        for symbol, keywords in self.asset_keywords.items():
            if any(kw in text_lower for kw in keywords):
                symbols.append(symbol)
        
        # Also look for $SYMBOL patterns
        dollar_symbols = re.findall(r'\$([A-Z]{2,5})\b', text)
        symbols.extend(dollar_symbols)
        
        return list(set(symbols))
    
    def _analyze_sentiment(self, text: str) -> NewsSentiment:
        """Analyze sentiment of text."""
        text_lower = text.lower()
        
        positive_score = sum(1 for kw in self.positive_keywords if kw in text_lower)
        negative_score = sum(1 for kw in self.negative_keywords if kw in text_lower)
        
        if positive_score > negative_score * 2:
            return NewsSentiment.VERY_POSITIVE
        elif positive_score > negative_score:
            return NewsSentiment.POSITIVE
        elif negative_score > positive_score * 2:
            return NewsSentiment.VERY_NEGATIVE
        elif negative_score > positive_score:
            return NewsSentiment.NEGATIVE
        else:
            return NewsSentiment.NEUTRAL
    
    def _classify_impact(self, text: str) -> NewsImpact:
        """Classify impact level of news."""
        text_lower = text.lower()
        
        high_impact_count = sum(1 for kw in self.high_impact_keywords if kw in text_lower)
        
        if high_impact_count >= 3:
            return NewsImpact.CRITICAL
        elif high_impact_count >= 2:
            return NewsImpact.HIGH
        elif high_impact_count >= 1:
            return NewsImpact.MEDIUM
        elif len(text) > 50:
            return NewsImpact.LOW
        else:
            return NewsImpact.NOISE
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        text_lower = text.lower()
        keywords = []
        
        all_keywords = self.high_impact_keywords + self.positive_keywords + self.negative_keywords
        for kw in all_keywords:
            if kw in text_lower:
                keywords.append(kw)
        
        return keywords[:10]
    
    def format_summary(self, summary: NewsSummary) -> str:
        """Format news summary for display."""
        emoji_map = {
            NewsSentiment.VERY_POSITIVE: "🟢🟢",
            NewsSentiment.POSITIVE: "🟢",
            NewsSentiment.NEUTRAL: "⚪",
            NewsSentiment.NEGATIVE: "🔴",
            NewsSentiment.VERY_NEGATIVE: "🔴🔴",
        }
        
        emoji = emoji_map.get(summary.overall_sentiment, "⚪")
        
        lines = [
            f"{emoji} **{summary.symbol} News Summary**",
            "",
            f"Sentiment: {summary.overall_sentiment.value}",
            f"Articles: {len(summary.articles)} (24h)",
            f"• Positive: {summary.positive_count}",
            f"• Negative: {summary.negative_count}",
            f"• Neutral: {summary.neutral_count}",
        ]
        
        if summary.market_moving_events:
            lines.append("")
            lines.append("**⚡ Market-Moving:**")
            for event in summary.market_moving_events[:3]:
                age = f"({event.age_hours:.0f}h ago)"
                lines.append(f"• {event.title[:60]}... {age}")
        
        if summary.top_headlines:
            lines.append("")
            lines.append("**Recent Headlines:**")
            for headline in summary.top_headlines[:3]:
                lines.append(f"• {headline[:70]}...")
        
        return "\n".join(lines)


# Singleton instance
_aggregator: Optional[NewsAggregator] = None


def get_news_aggregator() -> NewsAggregator:
    """Get global NewsAggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = NewsAggregator()
    return _aggregator


async def get_crypto_news(symbol: str, hours: int = 24) -> NewsSummary:
    """Convenience function to get news for a symbol."""
    agg = get_news_aggregator()
    return await agg.get_news_for_symbol(symbol, hours)


