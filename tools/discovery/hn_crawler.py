#!/usr/bin/env python3
"""Discover Hacker News users from Algolia comments."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.discovery.common import DiscoveryContact, add_common_args, clean_text, disabled, extract_email, finish_cli, main_disabled, score_signal

QUERIES = ("personal AI", "conscious AI", "AI sovereignty", "open model", "local LLM", "full potential")


def fetch_json(url: str, *, urlopen: Any = urllib.request.urlopen) -> dict[str, Any]:
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def discover(*, queries: tuple[str, ...] = QUERIES, now: datetime | None = None, fetcher: Any = fetch_json) -> list[DiscoveryContact]:
    if disabled("hn"):
        return []
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=30)
    rows: list[DiscoveryContact] = []
    for query in queries:
        url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode({"query": query, "tags": "comment"})
        data = fetcher(url)
        for hit in data.get("hits", []):
            author = clean_text(hit.get("author"), limit=120)
            created_raw = hit.get("created_at") or ""
            try:
                created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            except ValueError:
                created = current
            if created < cutoff or not author:
                continue
            comment = clean_text(hit.get("comment_text"), limit=700)
            if len(comment) < 100:
                continue
            email = extract_email(comment)
            if not email:
                try:
                    profile = fetcher(f"https://hn.algolia.com/api/v1/users/{urllib.parse.quote(author)}")
                    email = extract_email(clean_text(profile.get("about"), limit=1000))
                except Exception:
                    email = None
            rows.append(
                DiscoveryContact(
                    handle=email or author,
                    platform="email" if email else "hn",
                    source="hn",
                    topic_signal=comment[:420],
                    discovery_score=score_signal(f"{query} {comment}", content_length=len(comment)),
                    metadata={"hn_author": author, "query": query, "object_id": hit.get("objectID")},
                )
            )
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover contacts from Hacker News Algolia comments.")
    add_common_args(parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if disabled("hn"):
        return main_disabled("hn", json_mode=args.json)
    return finish_cli(discover(), source="hn", args=args)


if __name__ == "__main__":
    raise SystemExit(main())
