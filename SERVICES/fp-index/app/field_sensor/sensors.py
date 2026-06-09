"""Continuous, cheap field sensors. No LLM calls here.

Each sensor returns a list of SensedEvent objects. These get passed
through the significance gate before any expensive reflection.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import sqlite3
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

import httpx

from .registry import EVENTS_DB, ensure_brain_dir

logger = logging.getLogger(__name__)

FRONTIER_HF_AUTHORS = [
    "meta-llama", "mistralai", "google", "Qwen", "deepseek-ai",
    "microsoft", "nvidia", "apple", "01-ai", "THUDM",
    "NousResearch", "stabilityai", "black-forest-labs", "anthropic",
    "openai-community", "xai-org",
]

FRONTIER_GH_ORGS = [
    "anthropics", "openai", "google-deepmind", "meta-llama",
    "mistralai", "deepseek-ai", "QwenLM", "microsoft", "huggingface",
    "langchain-ai", "run-llama", "vllm-project",
]

ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]

HTTP_TIMEOUT = 15.0
USER_AGENT = "FPI-FieldSensor/1.0 (compounding-capabilities)"


@dataclass
class SensedEvent:
    source: str
    event_type: str
    title: str
    url: str
    author: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def event_id(self) -> str:
        h = hashlib.sha256(f"{self.source}|{self.url}|{self.title}".encode()).hexdigest()
        return h[:16]

    def to_row(self) -> tuple:
        import json as _json
        return (
            self.event_id, self.source, self.event_type, self.title,
            self.url, self.author, _json.dumps(self.raw, default=str), self.fetched_at,
        )


def _init_events_db() -> None:
    ensure_brain_dir()
    with sqlite3.connect(EVENTS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                author TEXT,
                raw_json TEXT,
                fetched_at TEXT NOT NULL,
                significance_score REAL DEFAULT 0,
                gated_passed INTEGER DEFAULT 0,
                reflected INTEGER DEFAULT 0,
                reflected_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_fetched_at ON events(fetched_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_unreflected ON events(reflected) WHERE reflected = 0")
        conn.commit()


def upsert_events(events: list[SensedEvent]) -> int:
    """Insert new events; skip duplicates. Returns count of newly inserted."""
    if not events:
        return 0
    _init_events_db()
    inserted = 0
    with sqlite3.connect(EVENTS_DB) as conn:
        for ev in events:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO events "
                    "(event_id, source, event_type, title, url, author, raw_json, fetched_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ev.to_row(),
                )
                if conn.total_changes > 0:
                    inserted += 1
                    conn.commit()
            except sqlite3.Error as e:
                logger.warning(f"[FIELD] DB insert failed for {ev.event_id}: {e}")
    return inserted


def get_unreflected_events(limit: int = 50) -> list[dict[str, Any]]:
    """Fetch events that haven't been reflected on yet."""
    _init_events_db()
    with sqlite3.connect(EVENTS_DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM events WHERE reflected = 0 ORDER BY fetched_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def mark_reflected(event_id: str, significance: float, gated: bool) -> None:
    _init_events_db()
    with sqlite3.connect(EVENTS_DB) as conn:
        conn.execute(
            "UPDATE events SET reflected = 1, reflected_at = ?, significance_score = ?, gated_passed = ? "
            "WHERE event_id = ?",
            (datetime.now(timezone.utc).isoformat(), significance, 1 if gated else 0, event_id),
        )
        conn.commit()


async def _sense_hf_frontier_authors(client: httpx.AsyncClient, limit_per_author: int = 3) -> list[SensedEvent]:
    out: list[SensedEvent] = []
    for author in FRONTIER_HF_AUTHORS:
        try:
            r = await client.get(
                "https://huggingface.co/api/models",
                params={"author": author, "sort": "createdAt", "direction": -1, "limit": limit_per_author},
            )
            if r.status_code != 200:
                continue
            for m in r.json():
                model_id = m.get("modelId") or m.get("id") or ""
                if not model_id:
                    continue
                out.append(SensedEvent(
                    source="huggingface",
                    event_type="model_release",
                    title=model_id,
                    url=f"https://huggingface.co/{model_id}",
                    author=author,
                    raw={"downloads": m.get("downloads"), "likes": m.get("likes"),
                         "tags": m.get("tags", [])[:10], "pipeline_tag": m.get("pipeline_tag"),
                         "created_at": m.get("createdAt")},
                ))
        except Exception as e:
            logger.debug(f"[FIELD] HF sensor failed for {author}: {e}")
    return out


async def _sense_arxiv(client: httpx.AsyncClient, max_results: int = 20) -> list[SensedEvent]:
    out: list[SensedEvent] = []
    import feedparser
    for cat in ARXIV_CATEGORIES:
        try:
            url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
            r = await client.get(url)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.text)
            for entry in feed.entries:
                title = (entry.get("title", "") or "").replace("\n", " ").strip()
                link = entry.get("link", "")
                authors = ", ".join([a.get("name", "") for a in entry.get("authors", [])][:5])
                summary = (entry.get("summary", "") or "").replace("\n", " ")[:500]
                out.append(SensedEvent(
                    source="arxiv",
                    event_type="paper",
                    title=title,
                    url=link,
                    author=authors,
                    raw={"category": cat, "summary": summary,
                         "published": entry.get("published", "")},
                ))
        except Exception as e:
            logger.debug(f"[FIELD] arXiv sensor failed for {cat}: {e}")
    return out


async def _sense_github_orgs(client: httpx.AsyncClient) -> list[SensedEvent]:
    out: list[SensedEvent] = []
    for org in FRONTIER_GH_ORGS:
        try:
            r = await client.get(
                f"https://api.github.com/orgs/{org}/events",
                params={"per_page": 10},
                headers={"Accept": "application/vnd.github+json"},
            )
            if r.status_code != 200:
                continue
            for ev in r.json():
                ev_type = ev.get("type", "")
                if ev_type not in ("ReleaseEvent", "CreateEvent", "PublicEvent"):
                    continue
                repo_name = ev.get("repo", {}).get("name", "")
                payload = ev.get("payload", {})
                if ev_type == "ReleaseEvent":
                    title = f"{repo_name} release: {payload.get('release', {}).get('tag_name', '?')}"
                elif ev_type == "CreateEvent" and payload.get("ref_type") == "repository":
                    title = f"{repo_name} new repo"
                else:
                    continue
                out.append(SensedEvent(
                    source="github",
                    event_type=ev_type,
                    title=title,
                    url=f"https://github.com/{repo_name}",
                    author=org,
                    raw={"created_at": ev.get("created_at"),
                         "body": (payload.get("release") or {}).get("body", "")[:500]},
                ))
        except Exception as e:
            logger.debug(f"[FIELD] GH sensor failed for {org}: {e}")
    return out


async def _sense_openrouter(client: httpx.AsyncClient) -> list[SensedEvent]:
    out: list[SensedEvent] = []
    try:
        r = await client.get("https://openrouter.ai/api/v1/models")
        if r.status_code != 200:
            return out
        data = r.json().get("data", [])
        for m in data:
            mid = m.get("id", "")
            if not mid:
                continue
            out.append(SensedEvent(
                source="openrouter",
                event_type="model_available",
                title=mid,
                url=f"https://openrouter.ai/models/{mid}",
                author=mid.split("/")[0] if "/" in mid else "",
                raw={"context_length": m.get("context_length"),
                     "pricing": m.get("pricing"),
                     "created": m.get("created")},
            ))
    except Exception as e:
        logger.debug(f"[FIELD] OpenRouter sensor failed: {e}")
    return out


async def sense_once() -> list[SensedEvent]:
    """Run all sensors once. Returns newly-sensed events (pre-gate)."""
    all_events: list[SensedEvent] = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        results = await asyncio.gather(
            _sense_hf_frontier_authors(client),
            _sense_arxiv(client),
            _sense_github_orgs(client),
            _sense_openrouter(client),
            return_exceptions=True,
        )
    for res in results:
        if isinstance(res, list):
            all_events.extend(res)
        elif isinstance(res, Exception):
            logger.warning(f"[FIELD] sensor raised: {res}")

    inserted = upsert_events(all_events)
    logger.info(f"[FIELD] Sensed {len(all_events)} events, {inserted} new")
    return all_events
