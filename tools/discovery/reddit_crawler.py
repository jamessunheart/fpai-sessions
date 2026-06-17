#!/usr/bin/env python3
"""Discover Reddit users from recent public subreddit JSON feeds."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.discovery.common import DiscoveryContact, add_common_args, clean_text, disabled, extract_email, finish_cli, main_disabled, score_signal

SUBREDDITS = (
    "awakening",
    "consciousness",
    "artificial",
    "selfimprovement",
    "solopreneur",
    "Meditation",
    "AIAssistants",
    "digitalnomad",
    "CostaRica",
    "Psychonaut",
    "spirituality",
)


def fetch_json(url: str, *, urlopen: Any = urllib.request.urlopen) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "FPAI-discovery/0.1"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def discover(*, subreddits: tuple[str, ...] = SUBREDDITS, now: datetime | None = None, fetcher: Any = fetch_json) -> list[DiscoveryContact]:
    if disabled("reddit"):
        return []
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=7)
    rows: list[DiscoveryContact] = []
    for sub in subreddits:
        data = fetcher(f"https://www.reddit.com/r/{sub}/new.json?limit=25")
        for child in data.get("data", {}).get("children", []):
            item = child.get("data", {})
            author = clean_text(item.get("author"), limit=120)
            if not author or author in {"[deleted]", "AutoModerator"}:
                continue
            created = datetime.fromtimestamp(float(item.get("created_utc") or 0), tz=timezone.utc)
            if created < cutoff:
                continue
            karma = int(item.get("author_karma") or item.get("author_total_karma") or 11)
            if karma <= 10:
                continue
            title = clean_text(item.get("title"), limit=180)
            body = clean_text(item.get("selftext"), limit=200)
            topic = clean_text(f"{title} {body}", limit=420)
            email = extract_email(body)
            rows.append(
                DiscoveryContact(
                    handle=email or f"u/{author}",
                    platform="email" if email else "reddit",
                    source=f"reddit_{sub}",
                    topic_signal=topic,
                    discovery_score=score_signal(topic, content_length=len(topic)),
                    metadata={"subreddit": sub, "reddit_author": author, "permalink": item.get("permalink")},
                )
            )
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover contacts from Reddit public JSON feeds.")
    add_common_args(parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if disabled("reddit"):
        return main_disabled("reddit", json_mode=args.json)
    return finish_cli(discover(), source="reddit", args=args)


if __name__ == "__main__":
    raise SystemExit(main())
