#!/usr/bin/env python3
"""Discover Twitter/X users from public hashtag search pages."""
from __future__ import annotations

import argparse
import random
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.discovery.common import DiscoveryContact, PRIMARY_SIGNALS, add_common_args, clean_text, disabled, extract_email, finish_cli, main_disabled, score_signal

USER_AGENTS = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Safari/605.1.15",
)


def discover(*, hashtags: tuple[str, ...] = PRIMARY_SIGNALS, page_factory: Any | None = None, delay: float = 2.5) -> list[DiscoveryContact]:
    if disabled("twitter"):
        return []
    if page_factory is None:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            return []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                return discover(hashtags=hashtags, page_factory=browser.new_page, delay=delay)
            finally:
                browser.close()
    rows: list[DiscoveryContact] = []
    for tag in hashtags:
        page = page_factory(user_agent=random.choice(USER_AGENTS)) if callable(page_factory) else page_factory
        url = "https://twitter.com/search?" + urllib.parse.urlencode({"q": f"#{tag}", "f": "live"})
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            tweets = page.locator("article").all()[:12]
            for article in tweets:
                text = clean_text(article.inner_text(timeout=1000), limit=800)
                if not text:
                    continue
                handle = next((part for part in text.split() if part.startswith("@") and len(part) > 1), "")
                email = extract_email(text)
                if not handle and not email:
                    continue
                rows.append(
                    DiscoveryContact(
                        handle=email or handle,
                        platform="email" if email else "twitter",
                        source=f"twitter_#{tag}",
                        topic_signal=text[:420],
                        discovery_score=score_signal(f"{tag} {text}", content_length=len(text)),
                        metadata={"hashtag": f"#{tag}", "bio_snippet": text[:160]},
                    )
                )
        finally:
            if hasattr(page, "close"):
                page.close()
        time.sleep(max(0.0, delay))
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover contacts from Twitter/X public hashtag search.")
    add_common_args(parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if disabled("twitter"):
        return main_disabled("twitter", json_mode=args.json)
    return finish_cli(discover(), source="twitter", args=args)


if __name__ == "__main__":
    raise SystemExit(main())
