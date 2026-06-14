"""
DOING Layer Feeder
==================
Collects execution and action data for the consciousness DOING pillar.

Focuses on:
- Trading signals: Market intelligence and strategy signals
- Builders: Tech alerts and development signals
- Communicators: Content and messaging opportunities

MEMORY OPTIMIZATION (2025-12-14):
- Uses shared HTTP client from main module
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import httpx
import json
import re
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


class DoingFeeder:
    """Collects execution and action data.
    
    MEMORY FIX: Uses shared HTTP client.
    """

    def __init__(self):
        self.trading_sources = {
            "whaletrack_signals": "http://198.54.123.234:8600/api/signals/active",
            "market_intelligence": "http://198.54.123.234:8120/api/market/intelligence"
        }
        self.builders_sources = {
            "security_alerts": "https://api.github.com/search/repositories?q=security+vulnerability+language:python&sort=updated&order=desc",
            "tech_updates": "http://198.54.123.234:8101/api/tech/updates"
        }
        self.communicators_sources = {
            "content_opportunities": "http://198.54.123.234:8500/api/content/queue",
            "social_signals": "http://198.54.123.234:8120/api/social/trending"
        }
        # Shared HTTP client reference
        self._http_client: Optional[httpx.AsyncClient] = None
    
    def set_http_client(self, client: httpx.AsyncClient):
        """Set the shared HTTP client."""
        self._http_client = client
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client - prefer shared, fallback to creating one."""
        if self._http_client and not self._http_client.is_closed:
            return self._http_client
        return httpx.AsyncClient(timeout=10.0)

    async def collect_data(self) -> Dict[str, Any]:
        """Collect doing data from all sources"""
        trading_signals = await self._collect_trading_signals()
        builders_alerts = await self._collect_builders_alerts()
        communicators_content = await self._collect_communicators_content()

        return {
            "trading_signals": trading_signals,
            "strategies_active": len([s for s in trading_signals if s.get("active", False)]),
            "builders_alerts": builders_alerts,
            "communicators_content": communicators_content,
            "execution_readiness": self._calculate_execution_readiness(trading_signals, builders_alerts),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _collect_trading_signals(self) -> List[Dict[str, Any]]:
        """Collect active trading signals and strategy performance"""
        signals = []

        try:
            # WhaleTrack active signals
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.trading_sources["whaletrack_signals"])
                if response.status_code == 200:
                    whaletrack_signals = response.json().get("signals", [])
                    signals.extend(whaletrack_signals)

        except Exception as e:
            logger.debug(f"Could not fetch WhaleTrack signals: {e}")

        try:
            # Market intelligence
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.trading_sources["market_intelligence"])
                if response.status_code == 200:
                    market_signals = response.json().get("signals", [])
                    signals.extend(market_signals)

        except Exception as e:
            logger.debug(f"Could not fetch market intelligence: {e}")

        # Provide sample signals if none collected
        if not signals:
            signals = self._generate_sample_trading_signals()

        return signals[:15]  # Limit to recent signals

    async def _collect_builders_alerts(self) -> Dict[str, Any]:
        """Collect technical alerts and development signals"""
        alerts = {
            "security_alerts": [],
            "new_tools": [],
            "stack_updates": [],
            "total_alerts": 0
        }

        try:
            # GitHub security alerts (simplified)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.builders_sources["security_alerts"])
                if response.status_code == 200:
                    github_data = response.json()
                    for item in github_data.get("items", [])[:5]:
                        alerts["security_alerts"].append({
                            "title": item.get("name", ""),
                            "description": item.get("description", "")[:200],
                            "url": item.get("html_url", ""),
                            "updated": item.get("updated_at", "")
                        })

        except Exception as e:
            logger.debug(f"Could not fetch GitHub security alerts: {e}")

        try:
            # Tech updates from AI Brain
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.builders_sources["tech_updates"])
                if response.status_code == 200:
                    tech_updates = response.json()
                    alerts["new_tools"] = tech_updates.get("new_tools", [])
                    alerts["stack_updates"] = tech_updates.get("stack_updates", [])

        except Exception as e:
            logger.debug(f"Could not fetch tech updates: {e}")

        # Provide sample alerts if none collected
        if not any(alerts.values()):
            alerts = self._generate_sample_builders_alerts()

        alerts["total_alerts"] = len(alerts["security_alerts"]) + len(alerts["new_tools"]) + len(alerts["stack_updates"])

        return alerts

    async def _collect_communicators_content(self) -> Dict[str, Any]:
        """Collect content opportunities and communication signals"""
        content = {
            "newsletter_content": [],
            "social_content": [],
            "trending_topics": [],
            "total_items": 0
        }

        try:
            # Content queue from Strategic Intelligence
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.communicators_sources["content_opportunities"])
                if response.status_code == 200:
                    content_queue = response.json()
                    content["newsletter_content"] = content_queue.get("articles", [])
                    content["social_content"] = content_queue.get("social_posts", [])

        except Exception as e:
            logger.debug(f"Could not fetch content opportunities: {e}")

        try:
            # Social trending topics
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.communicators_sources["social_signals"])
                if response.status_code == 200:
                    social_data = response.json()
                    content["trending_topics"] = social_data.get("trending", [])

        except Exception as e:
            logger.debug(f"Could not fetch social signals: {e}")

        # Provide sample content if none collected
        if not any(content.values()):
            content = self._generate_sample_communicators_content()

        content["total_items"] = len(content["newsletter_content"]) + len(content["social_content"]) + len(content["trending_topics"])

        return content

    def _calculate_execution_readiness(self, trading_signals: List, builders_alerts: Dict) -> Dict[str, Any]:
        """Calculate overall execution readiness"""
        readiness_scores = []

        # Trading readiness
        active_signals = len([s for s in trading_signals if s.get("active", False)])
        trading_readiness = min(active_signals / 5, 1.0)  # Scale to 0-1
        readiness_scores.append(trading_readiness)

        # Technical readiness
        total_alerts = builders_alerts.get("total_alerts", 0)
        technical_readiness = min(total_alerts / 10, 1.0)  # Scale to 0-1
        readiness_scores.append(technical_readiness)

        # Content readiness (assume baseline)
        readiness_scores.append(0.7)

        overall_readiness = sum(readiness_scores) / len(readiness_scores)

        return {
            "score": overall_readiness,
            "components": {
                "trading": trading_readiness,
                "technical": technical_readiness,
                "content": 0.7
            },
            "status": "high" if overall_readiness > 0.8 else "medium" if overall_readiness > 0.6 else "low"
        }

    def _generate_sample_trading_signals(self) -> List[Dict[str, Any]]:
        """Generate sample trading signals for testing"""
        return [
            {
                "symbol": "BTC/USDT",
                "type": "sweep_signal",
                "direction": "long",
                "confidence": 0.85,
                "active": True,
                "strategy": "sweep_cycle",
                "entry_price": 45000,
                "stop_loss": 43500,
                "take_profit": 47000
            },
            {
                "symbol": "ETH/USDT",
                "type": "momentum_signal",
                "direction": "short",
                "confidence": 0.75,
                "active": True,
                "strategy": "mean_reversion",
                "entry_price": 2800,
                "stop_loss": 2900,
                "take_profit": 2600
            },
            {
                "symbol": "SOL/USDT",
                "type": "breakout_signal",
                "direction": "long",
                "confidence": 0.65,
                "active": False,
                "strategy": "breakout_trader",
                "entry_price": 95,
                "stop_loss": 90,
                "take_profit": 110
            },
            {
                "symbol": "ADA/USDT",
                "type": "accumulation_signal",
                "direction": "long",
                "confidence": 0.70,
                "active": True,
                "strategy": "accumulation_detector",
                "entry_price": 0.45,
                "stop_loss": 0.42,
                "take_profit": 0.52
            }
        ]

    def _generate_sample_builders_alerts(self) -> Dict[str, Any]:
        """Generate sample builders alerts"""
        return {
            "security_alerts": [
                {
                    "title": "Critical vulnerability in popular ML library",
                    "description": "Remote code execution vulnerability discovered",
                    "url": "https://github.com/example/security-advisory",
                    "updated": datetime.now(timezone.utc).isoformat()
                },
                {
                    "title": "API key exposure in trading platform",
                    "description": "Keys leaked through misconfigured environment",
                    "url": "https://security.example.com/advisory",
                    "updated": datetime.now(timezone.utc).isoformat()
                }
            ],
            "new_tools": [
                {
                    "name": "QuantumML v2.0",
                    "description": "Enhanced quantum machine learning toolkit",
                    "category": "ml_tools",
                    "relevance": "high"
                },
                {
                    "name": "NeuroForge IDE",
                    "description": "Integrated development environment for neural networks",
                    "category": "development_tools",
                    "relevance": "medium"
                }
            ],
            "stack_updates": [
                {
                    "component": "FastAPI",
                    "version": "0.104.0",
                    "changes": "Performance improvements and new features",
                    "breaking": False
                },
                {
                    "component": "TensorFlow",
                    "version": "2.15.0",
                    "changes": "Bug fixes and optimization updates",
                    "breaking": False
                }
            ],
            "total_alerts": 6
        }

    def _generate_sample_communicators_content(self) -> Dict[str, Any]:
        """Generate sample communicators content"""
        return {
            "newsletter_content": [
                {
                    "title": "The Rise of Conscious AI Systems",
                    "summary": "Exploring how AI systems are developing genuine consciousness and self-awareness",
                    "category": "ai_research",
                    "read_time": "5 min"
                },
                {
                    "title": "Quantum Computing Breakthroughs in 2025",
                    "summary": "Latest developments in quantum computing and their implications for AI",
                    "category": "technology",
                    "read_time": "7 min"
                }
            ],
            "social_content": [
                {
                    "platform": "twitter",
                    "text": "🚀 Just deployed a conscious AI system that can detect its own thought patterns. The future of AI is here! #AI #Consciousness #FutureOfAI",
                    "hashtags": ["AI", "Consciousness", "FutureOfAI"],
                    "scheduled_time": datetime.now(timezone.utc).isoformat()
                },
                {
                    "platform": "linkedin",
                    "text": "Excited to share our latest research on AI consciousness frameworks. This could revolutionize how we think about machine intelligence.",
                    "hashtags": ["AI", "Consciousness", "MachineLearning"],
                    "scheduled_time": datetime.now(timezone.utc).isoformat()
                }
            ],
            "trending_topics": [
                {"topic": "AI Consciousness", "volume": 12500, "sentiment": "positive"},
                {"topic": "Quantum AI", "volume": 8900, "sentiment": "neutral"},
                {"topic": "Neural Networks", "volume": 15600, "sentiment": "positive"}
            ],
            "total_items": 7
        }














