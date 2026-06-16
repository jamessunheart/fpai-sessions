"""Web search capability providers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus

import httpx


@dataclass
class SearchResult:
    title: str
    snippet: str
    url: str

    def as_dict(self) -> dict[str, str]:
        return {"title": self.title, "snippet": self.snippet, "url": self.url}


def _clean(value: Any) -> str:
    return str(value or "").strip()


async def search_web(query: str, *, limit: int = 3) -> list[dict[str, str]]:
    """Return top web results from SerpAPI when configured, else DuckDuckGo IA.

    DuckDuckGo's Instant Answer API is free and keyless but often sparse. When it
    returns no structured topics, the fallback result points to the DDG search
    page rather than pretending there are exact hits.
    """
    query = query.strip()
    if not query:
        raise ValueError("query is required")
    if os.environ.get("SERPAPI_API_KEY"):
        return await _serpapi_search(query, limit=limit)
    return await _duckduckgo_search(query, limit=limit)


async def _serpapi_search(query: str, *, limit: int) -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google",
                "q": query,
                "api_key": os.environ["SERPAPI_API_KEY"],
                "num": limit,
            },
        )
        response.raise_for_status()
    payload = response.json()
    results: list[dict[str, str]] = []
    for item in payload.get("organic_results", [])[:limit]:
        title = _clean(item.get("title"))
        url = _clean(item.get("link"))
        snippet = _clean(item.get("snippet"))
        if title and url:
            results.append(SearchResult(title, snippet, url).as_dict())
    return results


async def _duckduckgo_search(query: str, *, limit: int) -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
        )
        response.raise_for_status()
    payload = response.json()
    results: list[dict[str, str]] = []

    abstract = _clean(payload.get("AbstractText"))
    abstract_url = _clean(payload.get("AbstractURL"))
    heading = _clean(payload.get("Heading")) or query
    if abstract and abstract_url:
        results.append(SearchResult(heading, abstract, abstract_url).as_dict())

    for topic in _flatten_topics(payload.get("RelatedTopics", [])):
        if len(results) >= limit:
            break
        title = _clean(topic.get("Text"))
        url = _clean(topic.get("FirstURL"))
        if title and url:
            results.append(SearchResult(title[:140], title, url).as_dict())

    if not results:
        results.append(
            SearchResult(
                f"Search DuckDuckGo for {query}",
                "DuckDuckGo Instant Answer did not return structured results.",
                f"https://duckduckgo.com/?q={quote_plus(query)}",
            ).as_dict()
        )
    return results[:limit]


def _flatten_topics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for item in items:
        if "Topics" in item and isinstance(item["Topics"], list):
            flat.extend(_flatten_topics(item["Topics"]))
        else:
            flat.append(item)
    return flat
