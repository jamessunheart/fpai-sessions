#!/usr/bin/env python3
"""Discover Instagram public hashtag posters."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.discovery.common import DiscoveryContact, add_common_args, clean_text, disabled, extract_email, finish_cli, main_disabled, score_signal

HASHTAGS = ("fullpotential", "selfactualization", "consciousliving", "awakening", "personalgrowth")


def discover(*, hashtags: tuple[str, ...] = HASHTAGS, page_factory: Any | None = None, delay: float = 2.5) -> list[DiscoveryContact]:
    if disabled("instagram"):
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
        page = page_factory() if callable(page_factory) else page_factory
        try:
            page.goto(f"https://www.instagram.com/explore/tags/{tag}/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            anchors = page.locator("a").all()[:24]
            for anchor in anchors:
                text = clean_text(anchor.inner_text(timeout=1000), limit=500)
                href = str(anchor.get_attribute("href") or "")
                if "/p/" not in href and not text:
                    continue
                email = extract_email(text)
                username = clean_text(href.strip("/").split("/")[0], limit=120) if href.count("/") == 2 else ""
                handle = email or (f"@{username}" if username and username not in {"p", "reel"} else "")
                if not handle:
                    continue
                rows.append(
                    DiscoveryContact(
                        handle=handle,
                        platform="email" if email else "instagram",
                        source=f"instagram_#{tag}",
                        topic_signal=text[:420],
                        discovery_score=score_signal(f"{tag} {text}", content_length=len(text)),
                        metadata={"hashtag": f"#{tag}", "post_href": href},
                    )
                )
        finally:
            if hasattr(page, "close"):
                page.close()
        time.sleep(max(0.0, delay))
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover contacts from Instagram public hashtag pages.")
    add_common_args(parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if disabled("instagram"):
        return main_disabled("instagram", json_mode=args.json)
    return finish_cli(discover(), source="instagram", args=args)


if __name__ == "__main__":
    raise SystemExit(main())
