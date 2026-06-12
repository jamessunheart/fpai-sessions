"""
🌐 External Data Fetchers - Intelligence Ingestion Layer

Fetches data from external sources for the Data Intelligence Engine:
- Hacker News API (tech/AI news)
- arXiv API (research papers)
- RSS Feeds (curated blogs/newsletters)

All fetchers are:
- Rate-limited (respect API limits)
- Cached (avoid duplicate fetches)
- Async (non-blocking)
- Filtered (relevance scoring)
"""

import asyncio
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class SourceType(str, Enum):
    HACKER_NEWS = "hacker_news"
    ARXIV = "arxiv"
    RSS = "rss"
    INTERNAL = "internal"


class Category(str, Enum):
    TECH = "tech"
    AI = "ai"
    MARKETS = "markets"
    CONSCIOUSNESS = "consciousness"
    SYSTEM = "system"
    GENERAL = "general"


@dataclass
class IntelligenceItem:
    """A single piece of intelligence from any source"""
    id: str
    title: str
    summary: str
    source: SourceType
    source_url: str
    category: Category = Category.GENERAL
    relevance_score: float = 0.5  # 0-1, higher = more relevant to Full Potential
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# RELEVANCE KEYWORDS
# =============================================================================

# Keywords that indicate high relevance to Full Potential mission
RELEVANCE_KEYWORDS = {
    # AI & Technology (high relevance)
    "ai": 0.8, "artificial intelligence": 0.9, "machine learning": 0.7, 
    "llm": 0.85, "large language model": 0.85, "gpt": 0.7, "claude": 0.8,
    "autonomous": 0.8, "agent": 0.75, "automation": 0.7,
    "neural": 0.6, "deep learning": 0.65, "transformer": 0.6,
    
    # Consciousness & Growth (core mission)
    "consciousness": 0.95, "potential": 0.8, "growth": 0.7, 
    "mindfulness": 0.85, "meditation": 0.8, "wellness": 0.75,
    "self-improvement": 0.8, "personal development": 0.85,
    "spiritual": 0.7, "awakening": 0.75,
    
    # Trading & Markets
    "crypto": 0.6, "bitcoin": 0.55, "trading": 0.6, "market": 0.5,
    "defi": 0.6, "blockchain": 0.55, "liquidation": 0.7,
    
    # Business & Startups
    "startup": 0.6, "saas": 0.55, "revenue": 0.5, "founder": 0.6,
    "open source": 0.65, "oss": 0.6,
}

# Keywords that reduce relevance
NEGATIVE_KEYWORDS = {
    "politics": -0.3, "celebrity": -0.4, "sports": -0.3,
    "entertainment": -0.2, "gossip": -0.4,
}


def calculate_relevance(text: str) -> float:
    """Calculate relevance score based on keyword matching"""
    text_lower = text.lower()
    score = 0.3  # Base score
    
    # Check positive keywords
    for keyword, weight in RELEVANCE_KEYWORDS.items():
        if keyword in text_lower:
            score += weight * 0.2  # Additive boost
    
    # Check negative keywords
    for keyword, penalty in NEGATIVE_KEYWORDS.items():
        if keyword in text_lower:
            score += penalty * 0.2
    
    # Clamp to 0-1
    return max(0.0, min(1.0, score))


def categorize_content(text: str) -> Category:
    """Categorize content based on keywords"""
    text_lower = text.lower()
    
    ai_keywords = ["ai", "llm", "gpt", "claude", "machine learning", "neural", "transformer"]
    consciousness_keywords = ["consciousness", "meditation", "mindfulness", "spiritual", "wellness"]
    markets_keywords = ["crypto", "bitcoin", "trading", "market", "defi", "price"]
    
    if any(k in text_lower for k in consciousness_keywords):
        return Category.CONSCIOUSNESS
    if any(k in text_lower for k in ai_keywords):
        return Category.AI
    if any(k in text_lower for k in markets_keywords):
        return Category.MARKETS
    
    return Category.TECH


# =============================================================================
# HACKER NEWS FETCHER
# =============================================================================

class HackerNewsFetcher:
    """
    Fetches top stories from Hacker News API.
    Free, no auth required. Rate limit: ~30 req/min
    
    API: https://github.com/HackerNews/API
    """
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self):
        self.cache: Dict[int, Dict] = {}
        self.last_fetch: Optional[datetime] = None
        self.min_interval = timedelta(minutes=5)  # Don't fetch more than every 5 min
    
    async def fetch_top_stories(self, limit: int = 30) -> List[IntelligenceItem]:
        """Fetch top stories from HN"""
        items = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Get top story IDs
                resp = await client.get(f"{self.BASE_URL}/topstories.json")
                resp.raise_for_status()
                story_ids = resp.json()[:limit]
                
                # Fetch each story (in parallel batches)
                tasks = [self._fetch_story(client, sid) for sid in story_ids]
                stories = await asyncio.gather(*tasks, return_exceptions=True)
                
                for story in stories:
                    if isinstance(story, IntelligenceItem):
                        items.append(story)
                
                logger.info(f"📰 Fetched {len(items)} stories from Hacker News")
                self.last_fetch = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error(f"HN fetch error: {e}")
        
        return items
    
    async def _fetch_story(self, client: httpx.AsyncClient, story_id: int) -> Optional[IntelligenceItem]:
        """Fetch a single story"""
        try:
            # Check cache
            if story_id in self.cache:
                return self.cache[story_id]
            
            resp = await client.get(f"{self.BASE_URL}/item/{story_id}.json")
            resp.raise_for_status()
            data = resp.json()
            
            if not data or data.get("type") != "story":
                return None
            
            title = data.get("title", "")
            url = data.get("url", f"https://news.ycombinator.com/item?id={story_id}")
            
            # Calculate relevance
            relevance = calculate_relevance(title)
            category = categorize_content(title)
            
            item = IntelligenceItem(
                id=f"hn_{story_id}",
                title=title,
                summary=f"HN Score: {data.get('score', 0)} | {data.get('descendants', 0)} comments",
                source=SourceType.HACKER_NEWS,
                source_url=url,
                category=category,
                relevance_score=relevance,
                metadata={
                    "hn_id": story_id,
                    "score": data.get("score", 0),
                    "comments": data.get("descendants", 0),
                    "by": data.get("by", "unknown"),
                }
            )
            
            self.cache[story_id] = item
            return item
            
        except Exception as e:
            logger.debug(f"Failed to fetch HN story {story_id}: {e}")
            return None


# =============================================================================
# ARXIV FETCHER
# =============================================================================

class ArxivFetcher:
    """
    Fetches research papers from arXiv API.
    Free, no auth required. Rate limit: 1 req/3 sec
    
    API: https://info.arxiv.org/help/api/basics.html
    """
    
    BASE_URL = "https://export.arxiv.org/api/query"
    
    # Categories relevant to Full Potential
    CATEGORIES = [
        "cs.AI",      # Artificial Intelligence
        "cs.LG",      # Machine Learning
        "cs.CL",      # Computation and Language (NLP)
        "cs.NE",      # Neural and Evolutionary Computing
        "q-bio.NC",   # Neurons and Cognition
    ]
    
    def __init__(self):
        self.cache: Dict[str, IntelligenceItem] = {}
        self.last_fetch: Optional[datetime] = None
        self.min_interval = timedelta(hours=1)  # Respect arXiv rate limits
    
    async def fetch_recent_papers(self, max_results: int = 20) -> List[IntelligenceItem]:
        """Fetch recent papers from relevant categories"""
        items = []
        
        # Build query for multiple categories
        cat_query = " OR ".join([f"cat:{cat}" for cat in self.CATEGORIES])
        
        params = {
            "search_query": f"({cat_query})",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                
                # Parse Atom XML response
                items = self._parse_arxiv_response(resp.text)
                
                logger.info(f"📚 Fetched {len(items)} papers from arXiv")
                self.last_fetch = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error(f"arXiv fetch error: {e}")
        
        return items
    
    def _parse_arxiv_response(self, xml_text: str) -> List[IntelligenceItem]:
        """Parse arXiv Atom XML response"""
        items = []
        
        try:
            # arXiv returns Atom XML
            root = ET.fromstring(xml_text)
            
            # Namespace handling
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom"
            }
            
            for entry in root.findall("atom:entry", ns):
                try:
                    # Extract fields
                    arxiv_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
                    title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                    summary = entry.find("atom:summary", ns).text.strip()[:500]
                    
                    # Get link
                    link = ""
                    for l in entry.findall("atom:link", ns):
                        if l.get("type") == "text/html":
                            link = l.get("href")
                            break
                    if not link:
                        link = f"https://arxiv.org/abs/{arxiv_id}"
                    
                    # Get authors
                    authors = []
                    for author in entry.findall("atom:author", ns):
                        name = author.find("atom:name", ns)
                        if name is not None:
                            authors.append(name.text)
                    
                    # Get categories
                    categories = []
                    for cat in entry.findall("arxiv:primary_category", ns):
                        categories.append(cat.get("term"))
                    
                    # Calculate relevance (papers about AI/consciousness are highly relevant)
                    relevance = calculate_relevance(title + " " + summary)
                    # Boost papers from primary categories
                    if any(c in self.CATEGORIES for c in categories):
                        relevance = min(1.0, relevance + 0.2)
                    
                    item = IntelligenceItem(
                        id=f"arxiv_{arxiv_id.replace('/', '_')}",
                        title=title,
                        summary=summary[:300] + "..." if len(summary) > 300 else summary,
                        source=SourceType.ARXIV,
                        source_url=link,
                        category=Category.AI,  # arXiv papers are mostly AI
                        relevance_score=relevance,
                        metadata={
                            "arxiv_id": arxiv_id,
                            "authors": authors[:3],  # First 3 authors
                            "categories": categories,
                        }
                    )
                    
                    items.append(item)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse arXiv entry: {e}")
                    continue
                    
        except ET.ParseError as e:
            logger.error(f"arXiv XML parse error: {e}")
        
        return items


# =============================================================================
# RSS FETCHER
# =============================================================================

class RSSFetcher:
    """
    Fetches content from curated RSS feeds.
    Supports standard RSS 2.0 and Atom feeds.
    """
    
    # Curated list of high-signal feeds
    DEFAULT_FEEDS = [
        # AI & Tech
        {
            "url": "https://openai.com/blog/rss/",
            "name": "OpenAI Blog",
            "category": Category.AI,
        },
        {
            "url": "https://www.anthropic.com/feed.xml",
            "name": "Anthropic",
            "category": Category.AI,
        },
        {
            "url": "https://blog.google/technology/ai/rss/",
            "name": "Google AI Blog",
            "category": Category.AI,
        },
        # Tech News
        {
            "url": "https://techcrunch.com/feed/",
            "name": "TechCrunch",
            "category": Category.TECH,
        },
        # Consciousness & Growth (add more as discovered)
        {
            "url": "https://www.mindful.org/feed/",
            "name": "Mindful",
            "category": Category.CONSCIOUSNESS,
        },
    ]
    
    def __init__(self, custom_feeds: Optional[List[Dict]] = None):
        self.feeds = custom_feeds or self.DEFAULT_FEEDS
        self.cache: Dict[str, IntelligenceItem] = {}
        self.last_fetch: Dict[str, datetime] = {}
    
    async def fetch_all_feeds(self, max_per_feed: int = 10) -> List[IntelligenceItem]:
        """Fetch from all configured RSS feeds"""
        all_items = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [
                self._fetch_feed(client, feed, max_per_feed) 
                for feed in self.feeds
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_items.extend(result)
        
        logger.info(f"📡 Fetched {len(all_items)} items from {len(self.feeds)} RSS feeds")
        return all_items
    
    async def _fetch_feed(self, client: httpx.AsyncClient, feed: Dict, max_items: int) -> List[IntelligenceItem]:
        """Fetch a single RSS feed"""
        items = []
        
        try:
            resp = await client.get(feed["url"], follow_redirects=True)
            resp.raise_for_status()
            
            # Try to parse as RSS or Atom
            items = self._parse_feed(resp.text, feed)[:max_items]
            self.last_fetch[feed["url"]] = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.debug(f"Failed to fetch RSS feed {feed['name']}: {e}")
        
        return items
    
    def _parse_feed(self, xml_text: str, feed: Dict) -> List[IntelligenceItem]:
        """Parse RSS or Atom feed"""
        items = []
        
        try:
            root = ET.fromstring(xml_text)
            
            # Detect feed type and parse accordingly
            if root.tag == "rss" or root.find("channel") is not None:
                items = self._parse_rss(root, feed)
            elif "feed" in root.tag.lower() or root.find("{http://www.w3.org/2005/Atom}entry") is not None:
                items = self._parse_atom(root, feed)
            else:
                logger.debug(f"Unknown feed format for {feed['name']}")
                
        except ET.ParseError as e:
            logger.debug(f"XML parse error for {feed['name']}: {e}")
        
        return items
    
    def _parse_rss(self, root: ET.Element, feed: Dict) -> List[IntelligenceItem]:
        """Parse RSS 2.0 feed"""
        items = []
        channel = root.find("channel")
        if channel is None:
            return items
        
        for item in channel.findall("item"):
            try:
                title = item.find("title")
                link = item.find("link")
                description = item.find("description")
                
                if title is None or link is None:
                    continue
                
                title_text = title.text or ""
                link_text = link.text or ""
                desc_text = (description.text or "")[:300] if description is not None else ""
                
                # Generate unique ID
                item_id = hashlib.md5(f"{feed['name']}_{link_text}".encode()).hexdigest()[:12]
                
                # Skip if already cached
                if item_id in self.cache:
                    items.append(self.cache[item_id])
                    continue
                
                relevance = calculate_relevance(title_text + " " + desc_text)
                
                intel_item = IntelligenceItem(
                    id=f"rss_{item_id}",
                    title=title_text,
                    summary=desc_text.replace("<![CDATA[", "").replace("]]>", "").strip()[:200],
                    source=SourceType.RSS,
                    source_url=link_text,
                    category=feed.get("category", categorize_content(title_text)),
                    relevance_score=relevance,
                    metadata={
                        "feed_name": feed["name"],
                        "feed_url": feed["url"],
                    }
                )
                
                self.cache[item_id] = intel_item
                items.append(intel_item)
                
            except Exception as e:
                logger.debug(f"Failed to parse RSS item: {e}")
                continue
        
        return items
    
    def _parse_atom(self, root: ET.Element, feed: Dict) -> List[IntelligenceItem]:
        """Parse Atom feed"""
        items = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        # Handle both namespaced and non-namespaced
        entries = root.findall("atom:entry", ns)
        if not entries:
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        if not entries:
            entries = root.findall("entry")
        
        for entry in entries:
            try:
                # Try multiple ways to get title
                title = entry.find("atom:title", ns)
                if title is None:
                    title = entry.find("{http://www.w3.org/2005/Atom}title")
                if title is None:
                    title = entry.find("title")
                
                # Get link
                link = None
                for l in entry.findall("atom:link", ns) + entry.findall("{http://www.w3.org/2005/Atom}link") + entry.findall("link"):
                    href = l.get("href")
                    if href:
                        link = href
                        break
                
                # Get summary/content
                summary = entry.find("atom:summary", ns)
                if summary is None:
                    summary = entry.find("{http://www.w3.org/2005/Atom}summary")
                if summary is None:
                    summary = entry.find("summary")
                if summary is None:
                    summary = entry.find("{http://www.w3.org/2005/Atom}content")
                
                if title is None or not link:
                    continue
                
                title_text = title.text or ""
                summary_text = (summary.text or "")[:300] if summary is not None else ""
                
                # Generate unique ID
                item_id = hashlib.md5(f"{feed['name']}_{link}".encode()).hexdigest()[:12]
                
                if item_id in self.cache:
                    items.append(self.cache[item_id])
                    continue
                
                relevance = calculate_relevance(title_text + " " + summary_text)
                
                intel_item = IntelligenceItem(
                    id=f"rss_{item_id}",
                    title=title_text,
                    summary=summary_text[:200],
                    source=SourceType.RSS,
                    source_url=link,
                    category=feed.get("category", categorize_content(title_text)),
                    relevance_score=relevance,
                    metadata={
                        "feed_name": feed["name"],
                        "feed_url": feed["url"],
                    }
                )
                
                self.cache[item_id] = intel_item
                items.append(intel_item)
                
            except Exception as e:
                logger.debug(f"Failed to parse Atom entry: {e}")
                continue
        
        return items


# =============================================================================
# UNIFIED INTELLIGENCE FETCHER
# =============================================================================

class IntelligenceFetcher:
    """
    Unified interface for fetching intelligence from all sources.
    Handles scheduling, deduplication, and relevance filtering.
    """
    
    def __init__(self):
        self.hn_fetcher = HackerNewsFetcher()
        self.arxiv_fetcher = ArxivFetcher()
        self.rss_fetcher = RSSFetcher()
        
        self._all_items: List[IntelligenceItem] = []
        self._seen_ids: set = set()
        self.last_full_fetch: Optional[datetime] = None
    
    async def fetch_all(self, 
                        include_hn: bool = True,
                        include_arxiv: bool = True,
                        include_rss: bool = True,
                        min_relevance: float = 0.3) -> List[IntelligenceItem]:
        """
        Fetch from all enabled sources.
        Returns items sorted by relevance (highest first).
        """
        tasks = []
        
        if include_hn:
            tasks.append(self.hn_fetcher.fetch_top_stories(limit=30))
        if include_arxiv:
            tasks.append(self.arxiv_fetcher.fetch_recent_papers(max_results=20))
        if include_rss:
            tasks.append(self.rss_fetcher.fetch_all_feeds(max_per_feed=10))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        new_items = []
        for result in results:
            if isinstance(result, list):
                for item in result:
                    # Deduplicate
                    if item.id not in self._seen_ids:
                        self._seen_ids.add(item.id)
                        new_items.append(item)
        
        # Filter by relevance
        filtered = [i for i in new_items if i.relevance_score >= min_relevance]
        
        # Sort by relevance (highest first)
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Add to all items
        self._all_items.extend(filtered)
        self.last_full_fetch = datetime.now(timezone.utc)
        
        logger.info(f"🧠 Intelligence fetch complete: {len(filtered)} items (filtered from {len(new_items)})")
        
        return filtered
    
    def get_cached_items(self, 
                         category: Optional[Category] = None,
                         min_relevance: float = 0.0,
                         limit: int = 50) -> List[IntelligenceItem]:
        """Get cached items with optional filtering"""
        items = self._all_items
        
        if category:
            items = [i for i in items if i.category == category]
        
        if min_relevance > 0:
            items = [i for i in items if i.relevance_score >= min_relevance]
        
        # Sort by timestamp (newest first), then by relevance
        items.sort(key=lambda x: (x.timestamp, x.relevance_score), reverse=True)
        
        return items[:limit]
    
    def get_top_by_category(self, limit_per_category: int = 5) -> Dict[str, List[IntelligenceItem]]:
        """Get top items grouped by category"""
        result = {}
        
        for category in Category:
            items = [i for i in self._all_items if i.category == category]
            items.sort(key=lambda x: x.relevance_score, reverse=True)
            if items:
                result[category.value] = items[:limit_per_category]
        
        return result
    
    def clear_old_items(self, max_age_hours: int = 168):  # 7 days
        """Remove items older than max_age"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        original_count = len(self._all_items)
        self._all_items = [
            i for i in self._all_items 
            if datetime.fromisoformat(i.timestamp.replace("Z", "+00:00")) > cutoff
        ]
        
        # Also clean seen IDs
        current_ids = {i.id for i in self._all_items}
        self._seen_ids = self._seen_ids.intersection(current_ids)
        
        removed = original_count - len(self._all_items)
        if removed > 0:
            logger.info(f"🧹 Cleaned {removed} old intelligence items")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_fetcher: Optional[IntelligenceFetcher] = None

def get_intelligence_fetcher() -> IntelligenceFetcher:
    """Get singleton intelligence fetcher instance"""
    global _fetcher
    if _fetcher is None:
        _fetcher = IntelligenceFetcher()
    return _fetcher
















