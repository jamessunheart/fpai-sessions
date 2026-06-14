#!/usr/bin/env python3
"""Capture Telegram `build:` messages into the Rung 4 build-intent lane.

This module is intentionally capture-only: it writes an intent file and returns.
The builder loop decides what to do next, and James keeps the merge gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

INBOX = Path(os.environ.get(
    "FPAI_TG_INBOX",
    Path.home() / ".config" / "fpai" / "tg_inbox" / "messages.jsonl",
))
CURSOR = Path(os.environ.get(
    "FPAI_BUILD_INTENT_CURSOR",
    Path.home() / ".config" / "fpai" / "tg_inbox" / "build_intent_cursor.txt",
))
INTENTS_DIR = Path(os.environ.get(
    "FPAI_BUILD_INTENTS_DIR",
    REPO_ROOT / "core" / "BUILD" / "intents",
))
TRIGGER_RE = re.compile(r"^\s*build:\s*(.+)$", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class CapturedIntent:
    update_id: int
    source_message_id: str
    slug: str
    path: Path


def capture(message: dict, intents_dir: Path | str = INTENTS_DIR) -> Path | None:
    """Write one build intent from a Telegram message, or return None.

    `message` is a decoded row from `tg_inbox/messages.jsonl`. Text and voice
    transcriptions are both expected in the `text` field, with fallbacks for
    common transcription keys. Duplicate `source_message_id` values return the
    already-written path instead of writing a second intent.
    """
    raw = _message_text(message)
    match = TRIGGER_RE.match(raw)
    if not match:
        return None
    description = _clean_description(match.group(1))
    if not description:
        return None

    target_dir = Path(intents_dir)
    source_message_id = _source_message_id(message)
    existing = _find_existing(source_message_id, target_dir)
    if existing:
        return existing

    now = _utc_now()
    intent_id = _intent_id(now)
    slug = slugify(description)
    path = target_dir / f"{intent_id}-{slug}.md"
    target_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_intent(
        intent_id=intent_id,
        slug=slug,
        source_message_id=source_message_id,
        created=now,
        raw=raw,
        description=description,
    ), encoding="utf-8")
    return path


def capture_new_messages(
    inbox: Path | str = INBOX,
    *,
    after_update_id: int | None = None,
    cursor_path: Path | str | None = CURSOR,
    intents_dir: Path | str = INTENTS_DIR,
) -> list[CapturedIntent]:
    """Scan inbox rows after a cursor/update id and capture build intents."""
    inbox_path = Path(inbox)
    if not inbox_path.exists():
        return []
    last_id = int(after_update_id if after_update_id is not None else _read_cursor(Path(cursor_path)))
    max_id = last_id
    captured: list[CapturedIntent] = []
    for message in _read_messages(inbox_path):
        update_id = int(message.get("update_id", 0) or 0)
        if update_id <= last_id:
            continue
        max_id = max(max_id, update_id)
        path = capture(message, intents_dir=intents_dir)
        if path:
            captured.append(CapturedIntent(
                update_id=update_id,
                source_message_id=_source_message_id(message),
                slug=slug_from_path(path),
                path=path,
            ))
    if cursor_path is not None and max_id > last_id:
        cursor = Path(cursor_path)
        cursor.parent.mkdir(parents=True, exist_ok=True)
        cursor.write_text(str(max_id), encoding="utf-8")
    return captured


def slugify(value: str, max_chars: int = 40) -> str:
    """Lowercase slug, max 40 chars, with whole separators cleaned up."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)[:max_chars].strip("-")
    return slug or "build-intent"


def slug_from_path(path: Path | str) -> str:
    name = Path(path).stem
    match = re.match(r"intent-\d{8}-[0-9a-f]{6}-(.+)$", name)
    return match.group(1) if match else name


def _message_text(message: dict) -> str:
    for key in ("text", "transcription", "transcript", "voice_text", "caption"):
        value = message.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _source_message_id(message: dict) -> str:
    for key in ("message_id", "source_message_id", "update_id"):
        value = message.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return "unknown"


def _clean_description(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def _intent_id(now: dt.datetime) -> str:
    return f"intent-{now:%Y%m%d}-{secrets.token_hex(3)}"


def _render_intent(
    *,
    intent_id: str,
    slug: str,
    source_message_id: str,
    created: dt.datetime,
    raw: str,
    description: str,
) -> str:
    return (
        "---\n"
        f"id: {intent_id}\n"
        f"slug: {slug}\n"
        "status: open\n"
        "source: telegram\n"
        f"source_message_id: {source_message_id}\n"
        f"created: {created.isoformat().replace('+00:00', 'Z')}\n"
        f"raw: {json.dumps(raw, ensure_ascii=False)}\n"
        "---\n\n"
        f"# {slug}\n\n"
        f"{description}\n"
    )


def _find_existing(source_message_id: str, intents_dir: Path) -> Path | None:
    if not intents_dir.exists():
        return None
    needle = f"source_message_id: {source_message_id}"
    for path in sorted(intents_dir.glob("*.md")):
        try:
            if needle in path.read_text(encoding="utf-8", errors="ignore"):
                return path
        except OSError:
            continue
    return None


def _read_cursor(cursor_path: Path | None) -> int:
    if cursor_path is None:
        return 0
    try:
        return int(cursor_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def _read_messages(inbox: Path) -> list[dict]:
    messages = []
    for line in inbox.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture Telegram build: intents.")
    parser.add_argument("--inbox", type=Path, default=INBOX)
    parser.add_argument("--cursor", type=Path, default=CURSOR)
    parser.add_argument("--intents-dir", type=Path, default=INTENTS_DIR)
    parser.add_argument("--after-update-id", type=int)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    captured = capture_new_messages(
        args.inbox,
        after_update_id=args.after_update_id,
        cursor_path=None if args.after_update_id is not None else args.cursor,
        intents_dir=args.intents_dir,
    )
    payload = [
        {
            "update_id": item.update_id,
            "source_message_id": item.source_message_id,
            "slug": item.slug,
            "path": str(item.path),
        }
        for item in captured
    ]
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"build_intent_router: captured={len(captured)}")
        for item in captured:
            print(f"  + {item.path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
