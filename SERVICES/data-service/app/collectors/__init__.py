"""
Data Collectors Module
======================
Individual collectors for different data sources.
Each collector follows the same pattern:
- async def collect() -> List[DataItem]
- Handles its own errors gracefully
- Returns empty list on failure (never crashes)
"""

from .whaletrack import collect_whaletrack
from .hackernews import collect_hackernews
from .arxiv import collect_arxiv
from .reddit import collect_reddit
from .github import collect_github

__all__ = [
    "collect_whaletrack",
    "collect_hackernews", 
    "collect_arxiv",
    "collect_reddit",
    "collect_github"
]











