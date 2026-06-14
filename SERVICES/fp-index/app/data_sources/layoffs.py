"""
Layoffs Scanner — Real-time tech layoff tracking
=================================================

Scans layoffs.fyi via HN discussions and tech news for layoff signals.
Each layoff announcement with AI/automation context is a displacement data point.
"""

import logging
import re
from datetime import datetime, timezone, timedelta

import httpx
import feedparser

from ..models.schema import IndexEntry, Dimension, SourceType, Domain, Alignment

logger = logging.getLogger("fp_index.layoffs")


def _entry_id(source: str, title: str) -> str:
    import hashlib
    return hashlib.md5(f"{source}:{title}".encode()).hexdigest()[:16]


async def scan_layoffs(client: httpx.AsyncClient) -> list[IndexEntry]:
    """Scan for layoff announcements — displacement signal."""
    entries = []

    try:
        resp = await client.get(
            "https://hn.algolia.com/api/v1/search_by_date"
            "?query=layoffs+AI+automation+headcount+reduction"
            "&tags=story"
            "&numericFilters=created_at_i>"
            + str(int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp()))
            + "&hitsPerPage=15"
        )
        if resp.status_code == 200:
            for hit in resp.json().get("hits", []):
                title = hit.get("title", "")
                if not title:
                    continue
                title_lower = title.lower()
                layoff_keywords = [
                    "layoff", "laid off", "cut jobs", "headcount",
                    "workforce reduction", "downsiz", "restructur",
                    "eliminate positions", "job cuts",
                ]
                if not any(kw in title_lower for kw in layoff_keywords):
                    continue

                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                points = hit.get("points", 0)

                ai_related = any(kw in title_lower for kw in [
                    "ai", "automat", "robot", "machine learning", "chatbot",
                ])

                impact = 0.5 + min(points / 300, 0.3)
                if ai_related:
                    impact = min(1.0, impact + 0.15)

                entries.append(IndexEntry(
                    id=_entry_id("layoff_hn", title),
                    dimension=Dimension.ACTIVITY,
                    title=f"[Layoff Signal] {title}",
                    summary=f"Layoff discussion on HN ({points} points). {'AI/automation cited.' if ai_related else ''}",
                    source="layoffs",
                    source_url=url,
                    source_type=SourceType.NEWS,
                    domains=[Domain.GENERAL],
                    alignment=Alignment.NEUTRAL,
                    impact_score=impact,
                    tags=["layoff", "displacement"] + (["ai-driven"] if ai_related else []),
                    published_at=hit.get("created_at"),
                ))
    except Exception as e:
        logger.warning(f"Layoff HN scan failed: {e}")

    tech_layoff_feeds = {
        "techcrunch_layoffs": "https://techcrunch.com/tag/layoffs/feed/",
    }
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    for source_name, feed_url in tech_layoff_feeds.items():
        try:
            resp = await client.get(feed_url)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            for item in feed.entries[:5]:
                title = item.get("title", "").strip()
                if not title:
                    continue
                published = item.get("published_parsed") or item.get("updated_parsed")
                pub_str = None
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.isoformat()
                summary = re.sub(r'<[^>]+>', '', (item.get("summary") or "")[:300]).strip()
                link = item.get("link", "")

                entries.append(IndexEntry(
                    id=_entry_id(source_name, title),
                    dimension=Dimension.ACTIVITY,
                    title=f"[Layoff Signal] {title}",
                    summary=summary,
                    source="layoffs",
                    source_url=link,
                    source_type=SourceType.NEWS,
                    domains=[Domain.GENERAL],
                    impact_score=0.55,
                    tags=["layoff", "displacement", "techcrunch"],
                    published_at=pub_str,
                ))
        except Exception as e:
            logger.warning(f"Layoff RSS scan failed for {source_name}: {e}")

    return entries
