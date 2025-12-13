"""
Reddit Collector
================
Collects top posts from relevant subreddits.
No authentication required for public subreddits.
"""

import httpx
import logging
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger("collector.reddit")

# Subreddits to monitor
SUBREDDITS = [
    "cryptocurrency",
    "Bitcoin", 
    "ethereum",
    "artificial",
    "MachineLearning",
    "LocalLLaMA"
]


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


async def collect_reddit(subreddits: List[str] = None, limit_per_sub: int = 10) -> List[DataItem]:
    """
    Collect top posts from specified subreddits.
    Uses public JSON API (no auth required).
    """
    if subreddits is None:
        subreddits = SUBREDDITS
    
    items = []
    
    headers = {
        "User-Agent": "FullPotentialAI/1.0 (Data Collection)",
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            for subreddit in subreddits:
                try:
                    # Get hot posts from subreddit
                    # Use api.reddit.com to avoid some 403 blocks
                    url = f"https://api.reddit.com/r/{subreddit}/hot?limit={limit_per_sub}"
                    resp = await client.get(url)
                    
                    if resp.status_code != 200:
                        logger.warning(f"Reddit r/{subreddit} returned {resp.status_code}")
                        continue
                    
                    data = resp.json()
                    posts = data.get("data", {}).get("children", [])
                    
                    for post_data in posts:
                        post = post_data.get("data", {})
                        
                        # Skip stickied/pinned posts
                        if post.get("stickied"):
                            continue
                        
                        title = post.get("title", "")
                        score = post.get("score", 0)
                        comments = post.get("num_comments", 0)
                        url = f"https://reddit.com{post.get('permalink', '')}"
                        
                        # Determine category
                        category = "markets" if subreddit.lower() in ["cryptocurrency", "bitcoin", "ethereum"] else "ai"
                        
                        # Calculate relevance
                        relevance = min(1.0, 0.5 + (score / 1000) + (comments / 500))
                        
                        items.append(DataItem(
                            id=f"reddit_{post.get('id', '')}",
                            title=title,
                            summary=f"r/{subreddit} | Score: {score} | Comments: {comments}",
                            source="reddit",
                            source_url=url,
                            category=category,
                            relevance_score=relevance,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            entities=[subreddit],
                            metadata={
                                "subreddit": subreddit,
                                "score": score,
                                "comments": comments,
                                "author": post.get("author", "unknown"),
                                "is_self": post.get("is_self", False)
                            }
                        ))
                        
                except Exception as e:
                    logger.debug(f"Failed to fetch r/{subreddit}: {e}")
                    continue
            
            logger.info(f"🗣️ Collected {len(items)} items from Reddit")
            
    except Exception as e:
        logger.error(f"Reddit collection failed: {e}")
    
    return items

