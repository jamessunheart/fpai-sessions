#!/usr/bin/env python3
"""Capture Claude Code correction turns into brain_index.corrections.

This module is intentionally non-blocking for hook use: ``main`` swallows
runtime failures and exits 0. Unit tests exercise the pure detection and DB
query/write contract without requiring live Postgres.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

MAX_FIELD_CHARS = 8000
DEFAULT_ENV_FILES = ("/etc/sh-brain/curator.env",)

# Bare words ("no", "actually", "fix") fire on relayed/quoted content and
# flooded the table with false positives — require correction PHRASES.
_EXPLICIT_CORRECTION = re.compile(
    r"\b(that's not right|that's wrong|incorrect|not what i meant|not what i asked)\b",
    re.IGNORECASE,
)
_CURATOR_EXPLICIT = re.compile(
    r"\b(you forgot|you said|you told me|you missed|you keep forgetting|"
    r"that's not|that is not|i already told you|i said)\b",
    re.IGNORECASE,
)
_NEGATION_START = re.compile(
    r"^\s*(no|nope|nah|not quite|wrong|incorrect|actually|rather|instead)\b[\s,:;-]+(.+)",
    re.IGNORECASE | re.DOTALL,
)
_NEGATION_RESTATEMENT = re.compile(
    r"\b(?:not|isn't|wasn't|aren't|weren't|don't|didn't|doesn't)\b.+"
    r"\b(?:it is|it's|its|i am|i'm|we are|we're|the answer is|actually|instead|rather)\b",
    re.IGNORECASE | re.DOTALL,
)


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ()) -> Any: ...
    def fetchone(self) -> tuple[Any, ...] | None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> Any: ...


@dataclass(frozen=True)
class CorrectionSignal:
    matched: bool
    reason: str = ""


@dataclass(frozen=True)
class CorrectionCapture:
    conversation_id: str
    original_response: str
    james_correction: str


def detect_correction_signal(text: str) -> CorrectionSignal:
    """Detect the d125 correction phrases plus the existing Telegram shapes."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return CorrectionSignal(False)
    if _EXPLICIT_CORRECTION.search(cleaned) or _CURATOR_EXPLICIT.search(cleaned):
        return CorrectionSignal(True, "explicit")
    if _NEGATION_RESTATEMENT.search(cleaned):
        return CorrectionSignal(True, "negation_restatement")
    match = _NEGATION_START.search(cleaned)
    if match and len(match.group(2).strip()) >= 8:
        return CorrectionSignal(True, "negation_prefix")
    return CorrectionSignal(False)


def prompt_from_hook_input(stdin_text: str, environ: dict[str, str] | None = None) -> str:
    """Return James's current prompt from env or Claude hook JSON stdin."""
    env = environ if environ is not None else os.environ
    prompt = env.get("CLAUDE_USER_PROMPT", "")
    if prompt:
        return prompt
    if not stdin_text.strip():
        return ""
    try:
        payload = json.loads(stdin_text)
    except json.JSONDecodeError:
        return ""
    value = payload.get("prompt", "")
    return value if isinstance(value, str) else ""


def load_db_env(env_files: tuple[str, ...] = DEFAULT_ENV_FILES) -> None:
    if os.environ.get("BRAIN_INDEX_DB_URL"):
        return
    for env_file in env_files:
        path = Path(env_file)
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def latest_claude_assistant_turn(conn: Connection) -> str:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT text
          FROM brain_index.thread
         WHERE surface = 'claude_code'
           AND role IN ('assistant', 'ember')
         ORDER BY at DESC
         LIMIT 1
        """
    )
    row = cur.fetchone()
    return str(row[0] or "") if row else ""


def write_correction(conn: Connection, capture: CorrectionCapture) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO brain_index.corrections
            (conversation_id, bot_turn_id, original_response, james_correction)
        VALUES (%s, %s, %s, %s)
        """,
        (
            capture.conversation_id,
            None,
            capture.original_response[:MAX_FIELD_CHARS],
            capture.james_correction[:MAX_FIELD_CHARS],
        ),
    )
    conn.commit()


def capture_prompt_if_correction(
    *,
    conn: Connection,
    conversation_id: str,
    james_prompt: str,
) -> CorrectionCapture | None:
    if not detect_correction_signal(james_prompt).matched:
        return None
    original_response = latest_claude_assistant_turn(conn)
    # A correction needs something to correct — unpaired writes polluted the
    # table with 200+ empty-original rows (2026-07-02 audit) and poisoned the
    # L2 dataset. No bot turn, no capture.
    if not original_response.strip():
        return None
    capture = CorrectionCapture(
        conversation_id=conversation_id or "unknown",
        original_response=original_response,
        james_correction=james_prompt,
    )
    write_correction(conn, capture)
    return capture


def _connect() -> Connection:
    import psycopg

    dsn = os.environ.get("BRAIN_INDEX_DB_URL", "")
    if not dsn:
        raise RuntimeError("BRAIN_INDEX_DB_URL missing")
    return psycopg.connect(dsn)


def main() -> int:
    try:
        stdin_text = sys.stdin.read()
        prompt = prompt_from_hook_input(stdin_text)
        if not detect_correction_signal(prompt).matched:
            return 0
        load_db_env()
        with _connect() as conn:
            capture_prompt_if_correction(
                conn=conn,
                conversation_id=os.environ.get("CLAUDE_SESSION_ID", "unknown"),
                james_prompt=prompt,
            )
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
