#!/usr/bin/env python3
"""Read-only Telegram public group scanner."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.discovery.common import DiscoveryContact, add_common_args, clean_text, disabled, finish_cli, main_disabled, score_signal

GROUP_QUERIES = (
    "conscious community",
    "full potential",
    "awakening AI",
    "personal growth",
    "self actualization",
    "costa rica",
    "zen village",
    "digital nomad",
)


async def discover_async(*, queries: tuple[str, ...] = GROUP_QUERIES, client: Any | None = None, now: datetime | None = None) -> list[DiscoveryContact]:
    if disabled("telegram"):
        return []
    own_client = client is None
    if client is None:
        try:
            from telethon import TelegramClient  # type: ignore
        except ImportError:
            return []
        api_id = os.environ.get("TELEGRAM_API_ID")
        api_hash = os.environ.get("TELEGRAM_API_HASH")
        session = os.environ.get("TELETHON_SESSION", "fpai-discovery")
        if not api_id or not api_hash:
            return []
        client = TelegramClient(session, int(api_id), api_hash)
        await client.start()
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=7)
    rows: list[DiscoveryContact] = []
    try:
        for query in queries:
            async for dialog in client.iter_dialogs():
                name = clean_text(getattr(dialog, "name", ""), limit=160)
                if query.lower() not in name.lower():
                    continue
                async for message in client.iter_messages(dialog.entity, limit=40):
                    date = getattr(message, "date", current)
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=timezone.utc)
                    if date < cutoff:
                        continue
                    text = clean_text(getattr(message, "message", ""), limit=700)
                    if len(text) <= 50:
                        continue
                    sender = await message.get_sender()
                    username = clean_text(getattr(sender, "username", ""), limit=120)
                    if not username:
                        continue
                    rows.append(
                        DiscoveryContact(
                            handle=f"@{username}",
                            platform="telegram",
                            source=f"telegram_{name.replace(' ', '_')[:80]}",
                            topic_signal=text[:420],
                            discovery_score=score_signal(f"{query} {text}", content_length=len(text)),
                            metadata={"group": name, "query": query, "dm_enabled": os.environ.get("TELETHON_DM_ENABLED") == "1"},
                        )
                    )
    finally:
        if own_client and hasattr(client, "disconnect"):
            await client.disconnect()
    return rows


def discover(**kwargs: Any) -> list[DiscoveryContact]:
    return asyncio.run(discover_async(**kwargs))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover contacts from public Telegram groups, read-only.")
    add_common_args(parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if disabled("telegram"):
        return main_disabled("telegram", json_mode=args.json)
    return finish_cli(discover(), source="telegram", args=args)


if __name__ == "__main__":
    raise SystemExit(main())
