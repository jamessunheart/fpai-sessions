"""
Hacker News Collector
=====================
Collects top stories from Hacker News.
Focus on AI, tech, startups, and programming.
"""

import httpx
import logging
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger("collector.hackernews")

HN_API = "https://hacker-news.firebaseio.com/v0"

# Keywords for categorization
CATEGORIES = {
    "ai": ["ai", "artificial intelligence", "machine learning", "llm", "gpt", "claude", "neural", "deep learning", "transformer", "openai", "anthropic"],
    "markets": ["crypto", "bitcoin", "ethereum", "defi", "trading", "finance", "yield", "btc", "eth"],
    "tech": ["startup", "saas", "api", "developer", "programming", "software", "rust", "python", "javascript"],
    "research": ["paper", "study", "research", "arxiv", "phd"]
}


class DataItem:
    """Simple data item structure"""
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")
        self.title = kwargs.get("title", "")
        self.summary = kwargs.get("summary")
        self.source = kwargs.get("source", "")
        self.source_url = kwargs.get("source_url")
        self.category = kwargs.get("category", "general")
        self.relevance_score = kwargs.get("relevance_score", 0.5)
        self.timestamp = kwargs.get("timestamp", datetime.now(timezone.utc).isoformat())
        self.entities = kwargs.get("entities", [])
        self.metadata = kwargs.get("metadata", {})
    
    def dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "source_url": self.source_url,
            "category": self.category,
            "relevance_score": self.relevance_score,
            "timestamp": self.timestamp,
            "entities": self.entities,
            "metadata": self.metadata
        }


def categorize(text: str) -> str:
    """Categorize text based on keywords"""
    text_lower = text.lower()
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category
    return "tech"  # Default for HN


async def collect_hackernews(limit: int = 30) -> List[DataItem]:
    """
    Collect top stories from Hacker News.
    
    Focus on:
    - AI and ML news
    - Crypto/trading news
    - Tech startups
    - Programming
    """
    items = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get top story IDs
            resp = await client.get(f"{HN_API}/topstories.json")
            if resp.status_code != 200:
                logger.warning(f"HN API returned {resp.status_code}")
                return items
            
            story_ids = resp.json()[:limit]
            
            # Fetch each story
            for story_id in story_ids:
                try:
                    resp = await client.get(f"{HN_API}/item/{story_id}.json")
                    if resp.status_code != 200:
                        continue
                    
                    story = resp.json()
                    if not story or story.get("type") != "story":
                        continue
                    
                    title = story.get("title", "")
                    url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                    score = story.get("score", 0)
                    comments = story.get("descendants", 0)
                    
                    # Categorize
                    category = categorize(title)
                    
                    # Calculate relevance (higher score = more relevant)
                    # AI/markets content gets bonus
                    base_relevance = min(1.0, score / 500)
                    if category in ["ai", "markets"]:
                        base_relevance = min(1.0, base_relevance + 0.2)
                    
                    items.append(DataItem(
                        id=f"hn_{story_id}",
                        title=title,
                        summary=f"Score: {score} | Comments: {comments}",
                        source="hacker_news",
                        source_url=url,
                        category=category,
                        relevance_score=base_relevance,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        entities=extract_entities(title),
                        metadata={
                            "score": score,
                            "comments": comments,
                            "hn_id": story_id,
                            "by": story.get("by", "unknown")
                        }
                    ))
                    
                except Exception as e:
                    logger.debug(f"Failed to fetch story {story_id}: {e}")
                    continue
            
            logger.info(f"📰 Collected {len(items)} items from Hacker News")
            
    except Exception as e:
        logger.error(f"HN collection failed: {e}")
    
    return items


def extract_entities(text: str) -> List[str]:
    """Extract company/product names from title"""
    entities = []
    
    # Known entities to look for
    known = ["OpenAI", "Anthropic", "Google", "Meta", "Microsoft", "Apple", 
             "Bitcoin", "Ethereum", "Solana", "Claude", "GPT", "Llama",
             "Python", "Rust", "JavaScript", "React", "AWS", "Azure"]
    
    for entity in known:
        if entity.lower() in text.lower():
            entities.append(entity)
    
    return entities











