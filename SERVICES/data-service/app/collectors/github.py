"""
GitHub Collector
================
Collects trending repositories and activity from GitHub.
Focus on AI/ML repositories.
"""

import httpx
import logging
from datetime import datetime, timezone, timedelta
from typing import List

logger = logging.getLogger("collector.github")

GITHUB_API = "https://api.github.com"

# Topics to search
TOPICS = ["llm", "machine-learning", "artificial-intelligence", "langchain", "llama"]


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


async def collect_github(limit: int = 20) -> List[DataItem]:
    """
    Collect trending AI/ML repositories from GitHub.
    Uses public API (rate limited to 60 requests/hour without auth).
    """
    items = []
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "FullPotentialAI/1.0"
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            # Search for recently active AI repos
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            # Build query for AI/ML repos with recent activity
            query = "topic:machine-learning+topic:artificial-intelligence+pushed:>" + week_ago
            url = f"{GITHUB_API}/search/repositories?q={query}&sort=stars&order=desc&per_page={limit}"
            
            resp = await client.get(url)
            
            if resp.status_code != 200:
                logger.warning(f"GitHub API returned {resp.status_code}")
                # Try without date filter as fallback
                url = f"{GITHUB_API}/search/repositories?q=topic:llm&sort=stars&order=desc&per_page={limit}"
                resp = await client.get(url)
                
                if resp.status_code != 200:
                    return items
            
            data = resp.json()
            repos = data.get("items", [])
            
            for repo in repos:
                name = repo.get("full_name", "")
                description = repo.get("description", "") or ""
                stars = repo.get("stargazers_count", 0)
                forks = repo.get("forks_count", 0)
                language = repo.get("language", "Unknown")
                
                # Calculate relevance based on stars and activity
                relevance = min(1.0, 0.5 + (stars / 10000) + (forks / 5000))
                
                items.append(DataItem(
                    id=f"github_{repo.get('id', '')}",
                    title=f"⭐ {name} ({stars:,} stars)",
                    summary=description[:200] if description else f"A {language} repository",
                    source="github",
                    source_url=repo.get("html_url", ""),
                    category="tech",
                    relevance_score=relevance,
                    timestamp=repo.get("pushed_at", datetime.now(timezone.utc).isoformat()),
                    entities=[language] if language else [],
                    metadata={
                        "stars": stars,
                        "forks": forks,
                        "language": language,
                        "topics": repo.get("topics", []),
                        "open_issues": repo.get("open_issues_count", 0),
                        "owner": repo.get("owner", {}).get("login", "unknown")
                    }
                ))
            
            logger.info(f"💻 Collected {len(items)} items from GitHub")
            
    except Exception as e:
        logger.error(f"GitHub collection failed: {e}")
    
    return items











