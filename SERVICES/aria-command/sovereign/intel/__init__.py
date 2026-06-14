#!/usr/bin/env python3
"""
ARIA ULTRA POWER - EXTERNAL INTELLIGENCE
=========================================

External data sources for enhanced trading signals:
- Twitter/X sentiment analysis
- On-chain whale tracking
- News aggregation
- Unified sentiment scoring
"""

from .twitter import (
    TwitterSentiment,
    get_twitter_sentiment,
    analyze_crypto_sentiment,
)

from .onchain import (
    OnChainIntel,
    get_onchain_intel,
    get_whale_movements,
    get_exchange_flows,
)

from .news import (
    NewsAggregator,
    get_news_aggregator,
    get_crypto_news,
)

from .sentiment import (
    UnifiedSentiment,
    get_unified_sentiment,
    calculate_combined_sentiment,
    SentimentScore,
)

__all__ = [
    # Twitter
    "TwitterSentiment",
    "get_twitter_sentiment",
    "analyze_crypto_sentiment",
    # On-chain
    "OnChainIntel",
    "get_onchain_intel",
    "get_whale_movements",
    "get_exchange_flows",
    # News
    "NewsAggregator",
    "get_news_aggregator",
    "get_crypto_news",
    # Unified
    "UnifiedSentiment",
    "get_unified_sentiment",
    "calculate_combined_sentiment",
    "SentimentScore",
]


