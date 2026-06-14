#!/usr/bin/env python3
"""Tests for Telegram `build:` intent capture."""
from __future__ import annotations

import json
import re
from pathlib import Path

import tools.queue.build_intent_router as router


def test_build_prefix_writes_open_intent(tmp_path: Path):
    path = router.capture(
        {"update_id": 10, "message_id": 101, "type": "text", "text": "build: a daily digest"},
        intents_dir=tmp_path,
    )

    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert re.match(r"intent-\d{8}-[0-9a-f]{6}-a-daily-digest\.md", path.name)
    assert "status: open" in text
    assert "slug: a-daily-digest" in text
    assert "source: telegram" in text
    assert "source_message_id: 101" in text
    assert "# a-daily-digest" in text
    assert text.rstrip().endswith("a daily digest")


def test_case_insensitive_build_prefix(tmp_path: Path):
    path = router.capture(
        {"update_id": 11, "message_id": 102, "type": "text", "text": "Build: Resend email wirer"},
        intents_dir=tmp_path,
    )

    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert "slug: resend-email-wirer" in text
    assert text.rstrip().endswith("Resend email wirer")


def test_non_build_message_returns_none_and_writes_nothing(tmp_path: Path):
    path = router.capture(
        {"update_id": 12, "message_id": 103, "type": "text", "text": "hello ember"},
        intents_dir=tmp_path,
    )

    assert path is None
    assert list(tmp_path.glob("*.md")) == []


def test_duplicate_source_message_id_returns_existing_path(tmp_path: Path):
    first = router.capture(
        {"update_id": 13, "message_id": 104, "type": "text", "text": "build: first thing"},
        intents_dir=tmp_path,
    )
    second = router.capture(
        {"update_id": 14, "message_id": 104, "type": "text", "text": "build: changed thing"},
        intents_dir=tmp_path,
    )

    assert first is not None
    assert second == first
    assert len(list(tmp_path.glob("*.md"))) == 1
    assert "first thing" in first.read_text(encoding="utf-8")


def test_voice_transcription_is_captured_like_text(tmp_path: Path):
    path = router.capture(
        {"update_id": 15, "message_id": 105, "type": "voice", "text": "build: voice bridge"},
        intents_dir=tmp_path,
    )

    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert "slug: voice-bridge" in text
    assert text.rstrip().endswith("voice bridge")


def test_scan_new_messages_uses_cursor_and_returns_metadata(tmp_path: Path):
    inbox = tmp_path / "messages.jsonl"
    cursor = tmp_path / "cursor.txt"
    intents = tmp_path / "intents"
    inbox.write_text("\n".join([
        json.dumps({"update_id": 1, "message_id": 201, "text": "hello"}),
        json.dumps({"update_id": 2, "message_id": 202, "text": "build: scanned intent"}),
    ]), encoding="utf-8")

    captured = router.capture_new_messages(inbox, cursor_path=cursor, intents_dir=intents)

    assert len(captured) == 1
    assert captured[0].update_id == 2
    assert captured[0].slug == "scanned-intent"
    assert cursor.read_text(encoding="utf-8") == "2"
    assert router.capture_new_messages(inbox, cursor_path=cursor, intents_dir=intents) == []
