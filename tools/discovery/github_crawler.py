#!/usr/bin/env python3
"""Discover public GitHub users from topic searches."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.discovery.common import DiscoveryContact, add_common_args, clean_text, disabled, extract_email, finish_cli, main_disabled, score_signal

TOPICS = ("personal-ai", "llm-agents", "consciousness", "wellbeing", "self-hosted-ai", "open-model")


def fetch_json(url: str, *, urlopen: Any = urllib.request.urlopen) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "FPAI-discovery/0.1"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def public_email_for_repo(repo: dict[str, Any], *, fetcher: Any) -> str | None:
    owner = repo.get("owner") or {}
    login = clean_text(owner.get("login"), limit=120)
    try:
        profile_url = owner.get("url") or f"https://api.github.com/users/{urllib.parse.quote(login)}"
        profile = fetcher(profile_url)
        email = extract_email(str(profile.get("email") or "") + " " + str(profile.get("bio") or ""))
        if email:
            return email
    except Exception:
        pass
    full_name = clean_text(repo.get("full_name"), limit=220)
    if not full_name:
        return None
    try:
        commits = fetcher(f"https://api.github.com/repos/{full_name}/commits?per_page=5")
        if isinstance(commits, list):
            for commit in commits:
                email = extract_email(str(((commit.get("commit") or {}).get("author") or {}).get("email") or ""))
                if email and not email.endswith("@users.noreply.github.com"):
                    return email
    except Exception:
        pass
    return None


def discover(*, topics: tuple[str, ...] = TOPICS, fetcher: Any = fetch_json) -> list[DiscoveryContact]:
    if disabled("github"):
        return []
    rows: list[DiscoveryContact] = []
    for topic in topics:
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": f"topic:{topic}", "per_page": "25"})
        data = fetcher(url)
        for repo in data.get("items", []):
            owner = repo.get("owner") or {}
            login = clean_text(owner.get("login"), limit=120)
            if not login:
                continue
            description = clean_text(repo.get("description"), limit=360)
            email = extract_email(description) or public_email_for_repo(repo, fetcher=fetcher)
            handle = email or login
            rows.append(
                DiscoveryContact(
                    handle=handle,
                    platform="email" if email else "github",
                    source=f"github_{topic}",
                    topic_signal=description or clean_text(repo.get("full_name"), limit=220),
                    discovery_score=score_signal(f"{topic} {description}", content_length=len(description)),
                    metadata={"github_login": login, "repo": repo.get("full_name"), "repo_url": repo.get("html_url"), "topic": topic},
                )
            )
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover contacts from GitHub public topic search.")
    add_common_args(parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if disabled("github"):
        return main_disabled("github", json_mode=args.json)
    return finish_cli(discover(), source="github", args=args)


if __name__ == "__main__":
    raise SystemExit(main())
