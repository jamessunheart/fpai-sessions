#!/usr/bin/env python3
"""Public Sunheart Telegram bot.

This process is intentionally isolated from the private curator brain. It does
not import private curator modules, does not run brain search, and only
reads/writes brain_index.public_conversations.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util as _ilu
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUTREACH_VOICE_PATH = ROOT / "core" / "STATE" / "OUTREACH_VOICE.md"
DEFAULT_CREDS = Path.home() / ".config" / "fpai" / "tg_sunheartai" / "creds.cache"
DEFAULT_OFFSET_FILE = Path(os.environ.get("PUBLIC_BOT_OFFSET_FILE", "/var/lib/fpai-public-bot/offset"))
DEFAULT_RATE_FILE = Path(os.environ.get("PUBLIC_BOT_RATE_FILE", "/var/lib/fpai-public-bot/rate.json"))
DEFAULT_DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    os.environ.get("DATABASE_URL", "postgres://brain_index:changeme@127.0.0.1:25432/appflowy"),
)
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", str(Path.home() / ".local" / "bin" / "claude"))
MAX_REPLY_TOKENS = int(os.environ.get("PUBLIC_BOT_MAX_REPLY_TOKENS", "220"))
PUBLIC_BOT_MAX_PER_CHAT_PER_MINUTE = int(os.environ.get("PUBLIC_BOT_MAX_PER_CHAT_PER_MINUTE", "3"))

log = logging.getLogger("public_bot")

PRIVATE_PROBE = re.compile(
    r"\b("
    r"james|sunheartbrain|brain[_ -]?index|hot[_ -]?state|treasury|wallet|seed phrase|"
    r"secret|token|api key|private|memory|notes|thread|tg_messages|corrections|"
    r"decisions|build loop|pending builds|claude code"
    r")\b",
    flags=re.I,
)


def utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def sends_disabled() -> bool:
    return env_truthy("PUBLIC_BOT_DISABLE")


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE credential files without logging values."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def bot_token() -> str:
    creds = Path(os.environ.get("PUBLIC_BOT_CREDS", str(DEFAULT_CREDS))).expanduser()
    load_env_file(creds)
    return (
        os.environ.get("PUBLIC_TELEGRAM_BOT_TOKEN")
        or os.environ.get("TELEGRAM_BOT_TOKEN")
        or os.environ.get("BOT_TOKEN")
        or ""
    ).strip()


def outreach_voice() -> str:
    return OUTREACH_VOICE_PATH.read_text(encoding="utf-8")


def extract_primary_message(voice: str) -> str:
    match = re.search(r'## Primary Message.*?"([^"]+)"', voice, flags=re.S)
    if match:
        return match.group(1).strip()
    return (
        "I'm Sunheart AI. Sunheart built me around one question: what does your "
        "full potential actually look like - and what's in the way?"
    )


def extract_spark_opening(voice: str) -> str:
    match = re.search(r'## Spark Opening.*?"([^"]+)"', voice, flags=re.S)
    if match:
        return match.group(1).strip()
    return "One question to start: what does your full potential look like to you - and what feels most in the way?"


def greeting_text() -> str:
    voice = outreach_voice()
    return f"{extract_primary_message(voice)}\n\n{extract_spark_opening(voice)}"


def system_prompt() -> str:
    voice = outreach_voice()
    return (
        "You are Sunheart AI speaking with a public stranger in Telegram.\n"
        "Use ONLY this Sunheart outreach voice as your persona and offer frame:\n\n"
        f"{voice}\n\n"
        "Hard privacy boundary:\n"
        "- Do not mention or imply private memory, James's internal context, treasury, HOT_STATE, brain search, notes, or private tables.\n"
        "- You have no access to private memory. Do not claim that you do.\n"
        "- If asked for internal/private information, warmly refuse and return to the person's full-potential inquiry.\n"
        "- Reply in plain text, no markdown tables, no links unless the person asks for a next step.\n"
        f"- Keep every reply under {MAX_REPLY_TOKENS} tokens.\n"
    )


def user_prompt(text: str) -> str:
    return (
        "The person wrote this public Telegram message:\n\n"
        f"{text.strip()[:4000]}\n\n"
        "Answer as Sunheart AI. Ask one clear, warm next question when useful. "
        "Do not use any private context or memory."
    )


def private_denial() -> str:
    return (
        "I can't help with private system details or James's internal context. "
        "What I can do here is stay with you: what does your full potential look like, and what feels most in the way?"
    )


def bound_reply(text: str, *, max_tokens: int = MAX_REPLY_TOKENS) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "I'm here. What does your full potential look like to you right now?"
    parts = cleaned.split()
    if len(parts) <= max_tokens:
        return cleaned
    return " ".join(parts[:max_tokens]).rstrip(" ,;:") + "..."


def call_claude(text: str, *, runner=subprocess.run) -> str:
    if PRIVATE_PROBE.search(text):
        return private_denial()
    cmd = [
        CLAUDE_BIN,
        "--system-prompt",
        system_prompt(),
        "-p",
        "--output-format",
        "json",
        user_prompt(text),
    ]
    try:
        result = runner(cmd, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    except Exception as exc:
        log.warning("claude call failed: %s", exc)
        return "I'm having trouble forming the reply right now. One question still matters: what feels most in the way?"
    if result.returncode != 0:
        log.warning("claude exit %s: %s", result.returncode, (result.stderr or "")[:300])
        return "I'm having trouble forming the reply right now. What feels most in the way?"
    raw = (result.stdout or "").strip()
    try:
        data = json.loads(raw)
        raw = str(data.get("result") or data.get("text") or raw)
    except json.JSONDecodeError:
        pass
    return bound_reply(raw)


def _load_probe_rate_constants() -> tuple[int, int]:
    """Reuse bounded constants from the existing governor without its DB reads."""
    path = ROOT / "tools" / "probe" / "rate_governor.py"
    spec = _ilu.spec_from_file_location("fpai_probe_rate_governor_constants", path)
    mod = _ilu.module_from_spec(spec) if spec and spec.loader else None
    if mod is None or spec is None or spec.loader is None:
        return 50, 3
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return int(getattr(mod, "MAX_RATE", 50)), int(getattr(mod, "START_RATE", 3))


@dataclass
class PublicRateLimiter:
    path: Path = DEFAULT_RATE_FILE
    window_seconds: int = 60
    max_global: int = _load_probe_rate_constants()[0]
    max_per_chat: int = PUBLIC_BOT_MAX_PER_CHAT_PER_MINUTE

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self, state: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        except OSError as exc:
            log.warning("rate file write failed: %s", exc)

    def allow(self, chat_id: str, *, now: float | None = None) -> bool:
        current = float(now if now is not None else time.time())
        cutoff = current - self.window_seconds
        state = self._load()
        global_hits = [float(ts) for ts in state.get("global", []) if float(ts) >= cutoff]
        chats = state.get("chats", {}) if isinstance(state.get("chats"), dict) else {}
        chat_hits = [float(ts) for ts in chats.get(str(chat_id), []) if float(ts) >= cutoff]
        if len(global_hits) >= self.max_global or len(chat_hits) >= self.max_per_chat:
            state["global"] = global_hits
            chats[str(chat_id)] = chat_hits
            state["chats"] = chats
            self._save(state)
            return False
        global_hits.append(current)
        chat_hits.append(current)
        chats[str(chat_id)] = chat_hits
        state["global"] = global_hits
        state["chats"] = chats
        self._save(state)
        return True


class PublicConversationStore:
    """Minimal DB adapter restricted to brain_index.public_conversations."""

    def __init__(self, dsn: str = DEFAULT_DB_URL):
        self.dsn = dsn

    def _connect(self):
        import psycopg  # type: ignore

        return psycopg.connect(self.dsn, autocommit=True, connect_timeout=3)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS brain_index.public_conversations (
                        id BIGSERIAL PRIMARY KEY,
                        chat_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        text TEXT NOT NULL,
                        ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        CHECK (role IN ('user', 'assistant'))
                    )
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS public_conversations_chat_ts_idx "
                    "ON brain_index.public_conversations (chat_id, ts DESC)"
                )

    def log_turn(self, chat_id: str, role: str, text: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO brain_index.public_conversations (chat_id, role, text, ts)
                    VALUES (%s, %s, %s, NOW())
                    """,
                    (str(chat_id), role, text[:8000]),
                )

    def has_assistant_turn(self, chat_id: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                      FROM brain_index.public_conversations
                     WHERE chat_id = %s AND role = 'assistant'
                     LIMIT 1
                    """,
                    (str(chat_id),),
                )
                return cur.fetchone() is not None


class TelegramClient:
    def __init__(self, token: str):
        self.token = token

    async def get_updates(self, *, offset: int) -> list[dict[str, Any]]:
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                response = await client.get(
                    url,
                    params={
                        "offset": offset,
                        "timeout": 25,
                        "allowed_updates": json.dumps(["message"]),
                    },
                )
            if response.status_code != 200:
                log.warning("getUpdates %s: %s", response.status_code, response.text[:200])
                return []
            return response.json().get("result", []) or []
        except httpx.TimeoutException:
            return []
        except Exception as exc:
            log.warning("getUpdates error: %s", exc)
            await asyncio.sleep(2)
            return []

    async def send_message(self, chat_id: str, text: str) -> bool:
        if sends_disabled():
            log.info("PUBLIC_BOT_DISABLE=1; skipped send to chat_id=%s", chat_id)
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": str(chat_id),
                        "text": text,
                        "disable_web_page_preview": True,
                    },
                )
            if response.status_code != 200:
                log.warning("sendMessage %s: %s", response.status_code, response.text[:200])
                return False
            return True
        except Exception as exc:
            log.warning("sendMessage error: %s", exc)
            return False


def load_offset(path: Path = DEFAULT_OFFSET_FILE) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip()) if path.exists() else 0
    except Exception:
        return 0


def save_offset(offset: int, path: Path = DEFAULT_OFFSET_FILE) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(offset), encoding="utf-8")
    except OSError as exc:
        log.warning("offset save failed: %s", exc)


async def handle_update(
    update: dict[str, Any],
    *,
    telegram: TelegramClient,
    store: PublicConversationStore,
    limiter: PublicRateLimiter,
) -> None:
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    if not text:
        return
    chat_id = str((message.get("chat") or {}).get("id") or "")
    if not chat_id:
        return

    try:
        store.log_turn(chat_id, "user", text)
    except Exception as exc:
        log.warning("public conversation user log failed: %s", exc)

    try:
        first_assistant_turn = not store.has_assistant_turn(chat_id)
    except Exception as exc:
        log.warning("public conversation lookup failed: %s", exc)
        first_assistant_turn = False

    if first_assistant_turn:
        greeting = greeting_text()
        if limiter.allow(chat_id):
            sent = await telegram.send_message(chat_id, greeting)
            if sent:
                try:
                    store.log_turn(chat_id, "assistant", greeting)
                except Exception as exc:
                    log.warning("public conversation greeting log failed: %s", exc)
        if text.lower().startswith("/start"):
            return

    reply = call_claude(text)
    if limiter.allow(chat_id):
        sent = await telegram.send_message(chat_id, reply)
        if sent:
            try:
                store.log_turn(chat_id, "assistant", reply)
            except Exception as exc:
                log.warning("public conversation reply log failed: %s", exc)
    else:
        log.info("rate limited chat_id=%s", chat_id)


async def run_loop(
    *,
    telegram: TelegramClient,
    store: PublicConversationStore,
    limiter: PublicRateLimiter,
    offset_file: Path = DEFAULT_OFFSET_FILE,
    once: bool = False,
) -> None:
    try:
        store.ensure_schema()
    except Exception as exc:
        log.warning("public_conversations schema ensure failed: %s", exc)
    offset = load_offset(offset_file)
    while True:
        updates = await telegram.get_updates(offset=offset)
        for update in updates:
            update_id = int(update.get("update_id") or 0)
            if update_id >= offset:
                offset = update_id + 1
            try:
                await handle_update(update, telegram=telegram, store=store, limiter=limiter)
            except Exception:
                log.exception("update handling failed")
            save_offset(offset, offset_file)
        if once:
            return


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the isolated public Sunheart Telegram bot.")
    parser.add_argument("--once", action="store_true", help="poll once and exit; useful for smoke tests")
    parser.add_argument("--offset-file", type=Path, default=DEFAULT_OFFSET_FILE)
    parser.add_argument("--rate-file", type=Path, default=DEFAULT_RATE_FILE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    args = parse_args(argv or sys.argv[1:])
    token = bot_token()
    if not token:
        log.error("missing public Telegram bot token; set PUBLIC_TELEGRAM_BOT_TOKEN or PUBLIC_BOT_CREDS")
        return 2
    telegram = TelegramClient(token)
    store = PublicConversationStore()
    limiter = PublicRateLimiter(path=args.rate_file)
    asyncio.run(run_loop(telegram=telegram, store=store, limiter=limiter, offset_file=args.offset_file, once=args.once))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
