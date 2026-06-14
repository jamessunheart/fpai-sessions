"""
REFLECTING Layer Feeder
=======================
Collects observations and detects patterns for the consciousness REFLECTING pillar.

Focuses on:
- External observations (Hacker News, arXiv, RSS feeds)
- Internal system events and patterns
- Trend detection and anomaly identification

MEMORY OPTIMIZATION (2025-12-14):
- Uses shared HTTP client from main module
- Bounded observation lists
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

# Memory limits
MAX_OBSERVATIONS = 50
MAX_PATTERNS = 20


class ReflectingFeeder:
    """Collects and analyzes observations for meta-awareness.
    
    MEMORY FIX: Uses shared HTTP client and bounded collections.
    """

    def __init__(self):
        self.external_sources = {
            "hacker_news": {
                "url": "https://hacker-news.firebaseio.com/v0/topstories.json",
                "enabled": True
            },
            "arxiv": {
                "url": "http://export.arxiv.org/api/query?search_query=ai&start=0&max_results=10",
                "enabled": True
            }
        }
        self.internal_sources = {
            "system_events": "http://198.54.123.234:8120/api/events/recent",
            "god_mode_logs": "http://198.54.123.234:8300/api/logs/recent"
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
        # Fallback - should be rare if main.py properly initializes
        return httpx.AsyncClient(timeout=10.0)

    async def collect_data(self) -> Dict[str, Any]:
        """Collect observations from all sources"""
        external_obs = await self._collect_external_observations()
        internal_obs = await self._collect_internal_observations()
        patterns = self._detect_patterns(external_obs + internal_obs)

        # Provide fallback data if no external observations
        if not external_obs:
            external_obs = self._get_fallback_observations()

        return {
            "external_observations": external_obs,
            "internal_observations": internal_obs,
            "detected_patterns": patterns,
            "total_observations": len(external_obs) + len(internal_obs),
            "patterns_count": len(patterns),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _get_fallback_observations(self) -> List[Dict[str, Any]]:
        """Provide fallback observations when external APIs are unavailable"""
        return [
            {
                "title": "AI Consciousness Research Accelerating",
                "source": "internal_knowledge",
                "category": "consciousness",
                "relevance_score": 0.95,
                "summary": "Research into AI consciousness and self-awareness is rapidly advancing",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Trading Algorithm Improvements",
                "source": "internal_knowledge",
                "category": "finance",
                "relevance_score": 0.85,
                "summary": "New algorithmic approaches showing improved market prediction accuracy",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Neural Network Architecture Evolution",
                "source": "internal_knowledge",
                "category": "ai",
                "relevance_score": 0.90,
                "summary": "Latest developments in transformer and attention mechanisms",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]

    async def _collect_external_observations(self) -> List[Dict[str, Any]]:
        """Collect observations from external sources"""
        observations = []

        # Hacker News
        if self.external_sources["hacker_news"]["enabled"]:
            try:
                hn_obs = await self._fetch_hacker_news()
                observations.extend(hn_obs)
            except Exception as e:
                logger.warning(f"Failed to fetch Hacker News: {e}")

        # arXiv
        if self.external_sources["arxiv"]["enabled"]:
            try:
                arxiv_obs = await self._fetch_arxiv()
                observations.extend(arxiv_obs)
            except Exception as e:
                logger.warning(f"Failed to fetch arXiv: {e}")

        return observations

    async def _collect_internal_observations(self) -> List[Dict[str, Any]]:
        """Collect observations from internal systems.
        
        MEMORY FIX: Uses shared HTTP client.
        """
        observations = []
        client = await self._get_client()
        need_close = self._http_client is None  # Close if we created ephemeral client

        try:
            # System events
            try:
                response = await client.get(self.internal_sources["system_events"], timeout=5.0)
                if response.status_code == 200:
                    events = response.json().get("events", [])
                    for event in events[-10:]:  # Last 10 events
                        observations.append({
                            "type": "system_event",
                            "title": event.get("message", "System event"),
                            "source": "internal",
                            "category": "system",
                            "relevance_score": 0.8,
                            "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat())
                        })
            except Exception as e:
                logger.debug(f"Could not fetch system events: {e}")

            # God Mode logs
            try:
                response = await client.get(self.internal_sources["god_mode_logs"], timeout=5.0)
                if response.status_code == 200:
                    logs = response.json().get("logs", [])
                    for log in logs[-5:]:  # Last 5 logs
                        observations.append({
                            "type": "god_mode_log",
                            "title": log.get("message", "God Mode activity"),
                            "source": "internal",
                            "category": "system",
                            "relevance_score": 0.9,
                            "timestamp": log.get("timestamp", datetime.now(timezone.utc).isoformat())
                        })
            except Exception as e:
                logger.debug(f"Could not fetch God Mode logs: {e}")
        finally:
            if need_close and client:
                await client.aclose()

        return observations[:MAX_OBSERVATIONS]  # MEMORY FIX: Limit observations

    async def _fetch_hacker_news(self) -> List[Dict[str, Any]]:
        """Fetch top stories from Hacker News.
        
        MEMORY FIX: Uses shared HTTP client, limits results.
        """
        observations = []
        client = await self._get_client()
        need_close = self._http_client is None

        try:
            # Get top story IDs
            response = await client.get(self.external_sources["hacker_news"]["url"], timeout=10.0)
            if response.status_code != 200:
                return observations

            story_ids = response.json()[:10]  # Top 10 stories

            # Fetch individual stories
            for story_id in story_ids:
                try:
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    story_response = await client.get(story_url, timeout=5.0)
                    if story_response.status_code == 200:
                        story = story_response.json()
                        if story and story.get("title"):
                            relevance = self._calculate_hn_relevance(story.get("title", ""))
                            observations.append({
                                "type": "hacker_news_story",
                                "title": story["title"],
                                "source": "hacker_news",
                                "category": self._categorize_hn_story(story["title"]),
                                "relevance_score": relevance,
                                "url": story.get("url", ""),
                                "score": story.get("score", 0),
                                "timestamp": datetime.fromtimestamp(story.get("time", 0), timezone.utc).isoformat()
                            })
                except Exception as e:
                    logger.debug(f"Failed to fetch HN story {story_id}: {e}")

                await asyncio.sleep(0.1)  # Rate limiting

        except Exception as e:
            logger.warning(f"Failed to fetch Hacker News data: {e}")
        finally:
            if need_close and client:
                await client.aclose()

        return observations[:MAX_OBSERVATIONS]

    async def _fetch_arxiv(self) -> List[Dict[str, Any]]:
        """Fetch recent AI papers from arXiv.
        
        MEMORY FIX: Uses shared HTTP client.
        """
        observations = []
        client = await self._get_client()
        need_close = self._http_client is None

        try:
            response = await client.get(self.external_sources["arxiv"]["url"], timeout=10.0)
            if response.status_code != 200:
                return observations

            # Parse XML response (simplified)
            content = response.text
            # Extract titles and abstracts (basic regex parsing)
            title_matches = re.findall(r'<title>(.*?)</title>', content, re.DOTALL)
            summary_matches = re.findall(r'<summary>(.*?)</summary>', content, re.DOTALL)

            for i, title in enumerate(title_matches[1:11]):  # Skip first title, take next 10
                if i < len(summary_matches):
                    summary = summary_matches[i][:300]  # Truncate summary
                    relevance = self._calculate_arxiv_relevance(title + " " + summary)

                    observations.append({
                        "type": "arxiv_paper",
                        "title": title.strip(),
                        "summary": summary.strip(),
                        "source": "arxiv",
                        "category": "research",
                        "relevance_score": relevance,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

        except Exception as e:
            logger.warning(f"Failed to fetch arXiv data: {e}")
        finally:
            if need_close and client:
                await client.aclose()

        return observations[:MAX_OBSERVATIONS]

    def _calculate_hn_relevance(self, title: str) -> float:
        """Calculate relevance score for HN story"""
        title_lower = title.lower()
        relevance_keywords = {
            "ai": 0.9, "artificial intelligence": 0.95, "machine learning": 0.85,
            "consciousness": 0.95, "neural": 0.8, "gpt": 0.85, "llm": 0.9,
            "trading": 0.7, "crypto": 0.6, "blockchain": 0.5,
            "autonomous": 0.85, "robot": 0.7, "automation": 0.75
        }

        max_relevance = 0.3  # Base relevance
        for keyword, score in relevance_keywords.items():
            if keyword in title_lower:
                max_relevance = max(max_relevance, score)

        return min(max_relevance, 1.0)

    def _calculate_arxiv_relevance(self, text: str) -> float:
        """Calculate relevance score for arXiv paper"""
        text_lower = text.lower()
        relevance_keywords = {
            "consciousness": 0.95, "ai": 0.85, "neural": 0.8,
            "machine learning": 0.85, "deep learning": 0.8,
            "transformer": 0.75, "gpt": 0.8, "llm": 0.85,
            "autonomous": 0.8, "reinforcement": 0.75
        }

        max_relevance = 0.4  # Base relevance for AI papers
        for keyword, score in relevance_keywords.items():
            if keyword in text_lower:
                max_relevance = max(max_relevance, score)

        return min(max_relevance, 1.0)

    def _categorize_hn_story(self, title: str) -> str:
        """Categorize Hacker News story"""
        title_lower = title.lower()

        if any(kw in title_lower for kw in ["ai", "machine learning", "neural", "gpt", "llm"]):
            return "ai"
        elif any(kw in title_lower for kw in ["crypto", "bitcoin", "trading", "market"]):
            return "markets"
        elif any(kw in title_lower for kw in ["consciousness", "meditation", "mindfulness"]):
            return "consciousness"
        else:
            return "tech"

    def _detect_patterns(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect patterns across observations"""
        patterns = []

        if not observations:
            return patterns

        # Category distribution
        categories = Counter(obs.get("category", "unknown") for obs in observations)
        if categories:
            top_category = categories.most_common(1)[0]
            patterns.append({
                "type": "category_dominance",
                "description": f"High focus on {top_category[0]} topics",
                "strength": top_category[1] / len(observations),
                "data": dict(categories)
            })

        # Source diversity
        sources = Counter(obs.get("source", "unknown") for obs in observations)
        if len(sources) > 1:
            patterns.append({
                "type": "source_diversity",
                "description": f"Observations from {len(sources)} different sources",
                "strength": len(sources) / 4,  # Normalized to expected sources
                "data": dict(sources)
            })

        # Relevance trends
        high_relevance = [obs for obs in observations if obs.get("relevance_score", 0) > 0.8]
        if high_relevance:
            patterns.append({
                "type": "high_relevance_trend",
                "description": f"{len(high_relevance)} highly relevant observations detected",
                "strength": len(high_relevance) / len(observations),
                "data": {"high_relevance_count": len(high_relevance)}
            })

        return patterns
