"""Daily value check Telegram prompt and reply capture."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import telegram as tg

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - Python without zoneinfo
    ZoneInfo = None  # type: ignore


log = logging.getLogger("curator.daily_value_check")

ATHENS_TZ = "Europe/Athens"
PROMPT = "Did I help you today? What would have helped more?"
SOURCE = "daily_value_check"
DEFAULT_STATE_FILE = Path(os.environ.get("DAILY_VALUE_CHECK_STATE", "/var/lib/sh-brain/daily_value_check.json"))
DEFAULT_DISABLE_FILE = Path(os.environ.get("DAILY_VALUE_CHECK_DISABLE_FILE", "/opt/fpai-build/.daily_value_check_disabled"))
DEFAULT_REQUIRED_HOUR = 20


@dataclass(frozen=True)
class CheckResult:
    status: str
    message: str
    sent: bool = False
    captured: bool = False


def athens_now() -> datetime:
    forced = os.environ.get("DAILY_VALUE_CHECK_NOW")
    if forced:
        dt = datetime.fromisoformat(forced.replace("Z", "+00:00"))
        if dt.tzinfo is None and ZoneInfo:
            dt = dt.replace(tzinfo=ZoneInfo(ATHENS_TZ))
        return dt
    if ZoneInfo:
        return datetime.now(ZoneInfo(ATHENS_TZ))
    return datetime.now(timezone.utc)


def _read_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


async def send_due_check(
    *,
    state_file: Path = DEFAULT_STATE_FILE,
    disable_file: Path = DEFAULT_DISABLE_FILE,
    required_hour: int | None = DEFAULT_REQUIRED_HOUR,
    sender=tg.send,
    now: datetime | None = None,
) -> CheckResult:
    """Send the daily prompt once per Athens date when the hour gate matches."""
    if disable_file.exists():
        return CheckResult("disabled", f"disabled by {disable_file}")

    current = now or athens_now()
    if required_hour is not None and current.hour != required_hour:
        return CheckResult("skipped_time", f"skipped at Athens hour {current.hour}; waiting for {required_hour}:00")

    day = current.date().isoformat()
    state = _read_state(state_file)
    if state.get("date") == day and state.get("status") in {"awaiting_reply", "captured"}:
        return CheckResult("skipped", f"daily value check already {state.get('status')} for {day}")

    sent = await sender(PROMPT)
    if not sent:
        return CheckResult("send_failed", "telegram send returned false")

    _write_state(
        state_file,
        {
            "date": day,
            "prompt": PROMPT,
            "sent_at": current.isoformat(),
            "status": "awaiting_reply",
            "source": SOURCE,
        },
    )
    return CheckResult("sent", f"daily value check sent for {day}", sent=True)


async def capture_reply_if_pending(
    *,
    conversation_id: str,
    james_message: str,
    state_file: Path = DEFAULT_STATE_FILE,
    disable_file: Path = DEFAULT_DISABLE_FILE,
) -> CheckResult:
    """Capture the next one-line owner reply as a daily value correction."""
    if disable_file.exists():
        return CheckResult("disabled", f"disabled by {disable_file}")

    reply = " ".join((james_message or "").split())
    if not reply or "\n" in (james_message or ""):
        return CheckResult("ignored", "daily value check reply must be one line")

    state = _read_state(state_file)
    if state.get("status") != "awaiting_reply" or not state.get("date"):
        return CheckResult("ignored", "no pending daily value check")

    await write_daily_value_correction(
        conversation_id=str(conversation_id),
        prompt=str(state.get("prompt") or PROMPT),
        reply=reply,
    )
    state.update(
        {
            "status": "captured",
            "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "conversation_id": str(conversation_id),
            "reply_preview": reply[:240],
        }
    )
    _write_state(state_file, state)
    return CheckResult("captured", "daily value check reply captured", captured=True)


async def write_daily_value_correction(*, conversation_id: str, prompt: str, reply: str) -> None:
    """Append the daily check reply to brain_index.corrections with source metadata."""
    try:
        from .db import connect

        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute("ALTER TABLE brain_index.corrections ADD COLUMN IF NOT EXISTS source TEXT")
                await cur.execute(
                    """
                    INSERT INTO brain_index.corrections
                        (conversation_id, bot_turn_id, original_response, james_correction, source)
                    VALUES (%s, NULL, %s, %s, %s)
                    """,
                    (conversation_id, prompt[:8000], reply[:8000], SOURCE),
                )
    except Exception as exc:
        log.warning("daily value correction write failed: %s", exc)
        raise


async def _amain() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--disable-file", type=Path, default=DEFAULT_DISABLE_FILE)
    parser.add_argument("--require-athens-hour", type=int, choices=range(0, 24), default=DEFAULT_REQUIRED_HOUR)
    parser.add_argument("--force", action="store_true", help="ignore the Athens hour gate")
    args = parser.parse_args()

    result = await send_due_check(
        state_file=args.state_file,
        disable_file=args.disable_file,
        required_hour=None if args.force else args.require_athens_hour,
    )
    print(result.message)
    return 0 if result.status not in {"send_failed"} else 1


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
