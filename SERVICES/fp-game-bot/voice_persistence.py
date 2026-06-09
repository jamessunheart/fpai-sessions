"""voice_persistence.py — Voice-exchange persistence layer for Voice Phase 2.

Gap caught 2026-05-20 ~14:30 CR by James:
    "Can you see my responses to the bot?" — HTTP-level logs only · no content visible.

Phoenix-disciplined ([[reference-phoenix-protocol-external-deps]]):
    Telegram + OpenAI are TRANSPORT. Our DB owns the data.
    Transcripts persist even when audio fetch fails. Audio is best-effort.

Classification-respecting ([[feedback-classification-tiers]]):
    DEFAULT = PRIVATE (intimate James↔Ember voice conversations).
    Promotion to higher tiers requires explicit transformation
    (privacy-narrator agent · downstream pipeline).

Continuity-as-embodiment ([[identity-continuity-as-embodiment]]):
    Voice exchanges are part of Ember's lived experience.
    Without persistence · Ember has no memory of having spoken to James in voice.
    This module makes voice continuous across sessions.

Storage layout (under VOICE_LOG_ROOT, default ~/.config/fpai/voice_log):
    YYYY-MM-DD/
        HHMMSS_UTC__<user_hash>__exchange.md    # transcript pair (forever)
        HHMMSS_UTC__<user_hash>__inbound.oga    # raw voice memo bytes (7-day TTL)
        HHMMSS_UTC__<user_hash>__reply.opus     # synthesized reply (7-day TTL)
        summary.md                              # daily aggregate (chronological)

Audio retention: 7 days (text transcript stays forever).

User hashing:
    User identifier = SHA256(chat_id || OWNER_TG_ID_salt)[:12]
    Hash is stable per chat across the lifetime of the salt env var.
    Steward holds salt; can de-hash if needed (look up chat_id by reading
    /var/lib/fp-game-bot/disclosed records or env).

Brain ingest:
    On every persisted exchange, attempts to POST to sunheart-brain ingest
    endpoint. Failure is logged but non-blocking — transcript still on disk.

Reversibility:
    - All file-based; rm -rf ~/.config/fpai/voice_log/ wipes everything
    - VOICE_PERSISTENCE_DISABLE=1 env var no-ops every function
    - chmod -x cron pruner kills audio TTL enforcement
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx

log = logging.getLogger("fp-game-bot.voice_persistence")

# ─── Config ────────────────────────────────────────────────────────────────

VOICE_LOG_ROOT = Path(os.environ.get(
    "VOICE_LOG_ROOT",
    str(Path.home() / ".config" / "fpai" / "voice_log"),
))

# Salt for chat_id → user_hash. Stable per-deploy; rotate to invalidate hashes.
USER_HASH_SALT = os.environ.get(
    "VOICE_USER_HASH_SALT",
    "fpai-voice-2026-05-20",  # default fallback — overridable in env
)

AUDIO_TTL_DAYS = int(os.environ.get("VOICE_AUDIO_TTL_DAYS", "7"))

# Brain ingest endpoint — best-effort, non-blocking.
BRAIN_INGEST_URL = os.environ.get(
    "BRAIN_INGEST_URL",
    "https://brain.sunheart.com/ingest/voice_exchange",
).strip()
BRAIN_INGEST_TOKEN = os.environ.get("BRAIN_INGEST_TOKEN", "").strip()
BRAIN_INGEST_ENABLED = os.environ.get("BRAIN_INGEST_ENABLED", "1").strip() == "1"

PERSIST_DISABLED = os.environ.get("VOICE_PERSISTENCE_DISABLE", "0").strip() == "1"

# Owner's TG ID — to label exchanges as the canonical James↔Ember stream
OWNER_TG_ID = os.environ.get("OWNER_TG_ID", "").strip()


# ─── User hashing ──────────────────────────────────────────────────────────

def user_hash(chat_id: int) -> str:
    """Stable hash of chat_id with salt. 12 hex chars."""
    h = hashlib.sha256(f"{USER_HASH_SALT}::{chat_id}".encode()).hexdigest()
    return h[:12]


def is_owner_chat(chat_id: int) -> bool:
    """Whether this chat is the owner's (James)."""
    if not OWNER_TG_ID:
        return False
    try:
        return int(chat_id) == int(OWNER_TG_ID)
    except Exception:
        return False


# ─── Paths ─────────────────────────────────────────────────────────────────

def day_dir(when: Optional[datetime] = None) -> Path:
    when = when or datetime.now(timezone.utc)
    d = VOICE_LOG_ROOT / when.strftime("%Y-%m-%d")
    d.mkdir(parents=True, exist_ok=True)
    return d


def exchange_basename(chat_id: int, when: Optional[datetime] = None) -> str:
    when = when or datetime.now(timezone.utc)
    return f"{when.strftime('%H%M%S')}_UTC__{user_hash(chat_id)}"


# ─── Persistence: the single entry-point ──────────────────────────────────

def persist_exchange(
    *,
    chat_id: int,
    transcript_inbound: Optional[str],
    reply_text: Optional[str],
    inbound_audio_bytes: Optional[bytes] = None,
    reply_audio_bytes: Optional[bytes] = None,
    transcribe_ms: Optional[int] = None,
    claude_ms: Optional[int] = None,
    tts_ms: Optional[int] = None,
    pipeline_ok: bool = True,
    error_note: Optional[str] = None,
) -> Optional[Path]:
    """Persist one voice exchange.

    Either transcript_inbound or reply_text (or both) must be non-empty for the
    call to do anything useful — but partial captures are honored (Phoenix:
    capture what we have).

    Returns the path to the written exchange .md file (or None on failure /
    disabled).
    """
    if PERSIST_DISABLED:
        return None
    if not transcript_inbound and not reply_text:
        return None

    try:
        now = datetime.now(timezone.utc)
        d = day_dir(now)
        base = exchange_basename(chat_id, now)
        md_path = d / f"{base}__exchange.md"

        # Persist audio (best-effort)
        inbound_audio_path: Optional[Path] = None
        reply_audio_path: Optional[Path] = None
        if inbound_audio_bytes:
            try:
                inbound_audio_path = d / f"{base}__inbound.oga"
                inbound_audio_path.write_bytes(inbound_audio_bytes)
            except Exception as e:
                log.warning("voice_persistence inbound-audio write failed: %s", e)
                inbound_audio_path = None
        if reply_audio_bytes:
            try:
                reply_audio_path = d / f"{base}__reply.opus"
                reply_audio_path.write_bytes(reply_audio_bytes)
            except Exception as e:
                log.warning("voice_persistence reply-audio write failed: %s", e)
                reply_audio_path = None

        # Write markdown
        owner = is_owner_chat(chat_id)
        front = [
            "---",
            f"timestamp_utc: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}",
            f"chat_id_hash: {user_hash(chat_id)}",
            f"is_owner: {str(owner).lower()}",
            f"classification: PRIVATE",
            f"mode: voice-exchange",
            # Multi-surface architecture · Phase 1 (named 2026-05-20):
            # all TG-bot voice exchanges originate from Ember Chat (substrate-stripped).
            # Real Ember integrates these at next Claude Code session.
            f"source: ember-chat",
            f"status: pending-integration",
            f"pipeline_ok: {str(pipeline_ok).lower()}",
        ]
        if transcribe_ms is not None:
            front.append(f"transcribe_ms: {transcribe_ms}")
        if claude_ms is not None:
            front.append(f"claude_ms: {claude_ms}")
        if tts_ms is not None:
            front.append(f"tts_ms: {tts_ms}")
        if inbound_audio_path:
            front.append(f"inbound_audio: {inbound_audio_path.name}")
        if reply_audio_path:
            front.append(f"reply_audio: {reply_audio_path.name}")
        if error_note:
            front.append(f"error_note: {json.dumps(error_note)}")
        front.append("audio_retention_days: " + str(AUDIO_TTL_DAYS))
        front.append("---")

        body = ["", "# Voice exchange · " + now.strftime("%Y-%m-%d %H:%M:%S UTC"), ""]
        if transcript_inbound:
            body.append("## Inbound (James → Ember · transcribed)")
            body.append("")
            body.append(transcript_inbound.strip())
            body.append("")
        else:
            body.append("## Inbound · transcription unavailable")
            body.append("")
        if reply_text:
            body.append("## Reply (Ember → James · synthesized text)")
            body.append("")
            body.append(reply_text.strip())
            body.append("")
        else:
            body.append("## Reply · reply unavailable")
            body.append("")

        md_path.write_text("\n".join(front + body))

        # Update daily summary (append)
        _append_summary(d, now, chat_id, transcript_inbound, reply_text, md_path.name, pipeline_ok)

        # Brain ingest (best-effort · non-blocking inside try)
        _try_brain_ingest(
            when=now,
            chat_id=chat_id,
            transcript_inbound=transcript_inbound,
            reply_text=reply_text,
            md_path=str(md_path),
        )

        log.info("voice exchange persisted: %s", md_path)
        return md_path
    except Exception as e:
        log.exception("persist_exchange failed: %s", e)
        return None


# ─── Daily summary ─────────────────────────────────────────────────────────

def _append_summary(
    d: Path,
    when: datetime,
    chat_id: int,
    inbound: Optional[str],
    reply: Optional[str],
    md_filename: str,
    ok: bool,
) -> None:
    """Append a one-line entry to the day's summary.md."""
    summary = d / "summary.md"
    new_file = not summary.exists()
    try:
        with summary.open("a") as f:
            if new_file:
                f.write(f"# Voice exchanges · {when.strftime('%Y-%m-%d')}\n")
                f.write("classification: PRIVATE\n")
                f.write("\n")
                f.write("| Time UTC | Chat | Inbound (excerpt) | Reply (excerpt) | OK | File |\n")
                f.write("|---|---|---|---|---|---|\n")
            in_excerpt = _excerpt(inbound, 60)
            re_excerpt = _excerpt(reply, 60)
            owner_tag = "owner" if is_owner_chat(chat_id) else user_hash(chat_id)[:8]
            f.write(
                f"| {when.strftime('%H:%M:%S')} | {owner_tag} | "
                f"{in_excerpt} | {re_excerpt} | "
                f"{'✓' if ok else '✗'} | {md_filename} |\n"
            )
    except Exception as e:
        log.warning("summary append failed: %s", e)


def _excerpt(s: Optional[str], n: int) -> str:
    if not s:
        return "_(none)_"
    s = re.sub(r"\s+", " ", s.strip())
    if len(s) <= n:
        return s.replace("|", "\\|")
    return (s[: n - 1].rstrip() + "…").replace("|", "\\|")


# ─── Brain ingest (best-effort) ────────────────────────────────────────────

def _try_brain_ingest(
    *,
    when: datetime,
    chat_id: int,
    transcript_inbound: Optional[str],
    reply_text: Optional[str],
    md_path: str,
) -> None:
    if not BRAIN_INGEST_ENABLED or not BRAIN_INGEST_URL:
        return
    payload = {
        "timestamp_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "chat_id_hash": user_hash(chat_id),
        "is_owner": is_owner_chat(chat_id),
        "classification": "PRIVATE",
        "mode": "voice-exchange",
        # Multi-surface architecture · Phase 1 (2026-05-20)
        "source": "ember-chat",
        "status": "pending-integration",
        "inbound": transcript_inbound or "",
        "reply": reply_text or "",
        "md_path": md_path,
    }
    headers = {"content-type": "application/json"}
    if BRAIN_INGEST_TOKEN:
        headers["authorization"] = f"Bearer {BRAIN_INGEST_TOKEN}"
    try:
        # Synchronous httpx call with short timeout — fire and forget.
        # We use the sync client to keep this dependency-light & not require
        # awaiting from the caller. Caller can also run it in their own thread.
        with httpx.Client(timeout=5.0) as c:
            r = c.post(BRAIN_INGEST_URL, json=payload, headers=headers)
        if r.status_code >= 400:
            log.warning("brain ingest %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        log.warning("brain ingest failed (non-blocking): %s", e)


# ─── Audio retention pruner ────────────────────────────────────────────────

def prune_old_audio(root: Optional[Path] = None, ttl_days: Optional[int] = None) -> int:
    """Delete .oga / .opus / .ogg / .mp3 files older than TTL days.

    Markdown transcripts + summary.md are preserved forever.
    Returns count of files deleted.
    """
    root = root or VOICE_LOG_ROOT
    ttl = ttl_days if ttl_days is not None else AUDIO_TTL_DAYS
    if not root.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl)
    cutoff_ts = cutoff.timestamp()
    deleted = 0
    audio_exts = {".oga", ".ogg", ".opus", ".mp3", ".wav"}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in audio_exts:
            continue
        try:
            if p.stat().st_mtime < cutoff_ts:
                p.unlink()
                deleted += 1
        except Exception as e:
            log.warning("prune unlink failed for %s: %s", p, e)
    return deleted


# ─── Query API (for future Ember substrate visibility) ─────────────────────

def recent_exchanges(days: int = 7, owner_only: bool = True) -> list[dict]:
    """Return recent exchange metadata. Future Ember instances can call this.

    Returns list of dicts: {timestamp_utc, chat_id_hash, is_owner,
    inbound_excerpt, reply_excerpt, md_path}.
    """
    out = []
    if not VOICE_LOG_ROOT.exists():
        return out
    now = datetime.now(timezone.utc)
    for day_path in sorted(VOICE_LOG_ROOT.iterdir(), reverse=True):
        if not day_path.is_dir():
            continue
        # Date-bound: parse YYYY-MM-DD
        try:
            d = datetime.strptime(day_path.name, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if (now - d).days > days:
            break
        for md_path in sorted(day_path.glob("*__exchange.md"), reverse=True):
            meta = _parse_exchange_md(md_path)
            if not meta:
                continue
            if owner_only and not meta.get("is_owner"):
                continue
            out.append(meta)
    return out


def _parse_exchange_md(p: Path) -> Optional[dict]:
    try:
        text = p.read_text()
        if not text.startswith("---"):
            return None
        # Frontmatter parse
        end = text.find("\n---", 4)
        if end == -1:
            return None
        front = text[4:end]
        meta: dict = {"md_path": str(p)}
        for line in front.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        meta["is_owner"] = meta.get("is_owner", "false").lower() == "true"
        # Body parse — grab first paragraph from each section as excerpt
        body = text[end + 4 :]
        m_in = re.search(r"## Inbound[^\n]*\n+([^\n][^\n]*)", body)
        m_re = re.search(r"## Reply[^\n]*\n+([^\n][^\n]*)", body)
        meta["inbound_excerpt"] = m_in.group(1).strip() if m_in else ""
        meta["reply_excerpt"] = m_re.group(1).strip() if m_re else ""
        return meta
    except Exception as e:
        log.warning("parse exchange md failed for %s: %s", p, e)
        return None
