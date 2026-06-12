"""voice_ember.py — Voice-first Ember loop for fp-game-bot.

Phase 2 of [[project-voice-first-interface]].

What this module owns:
  1. Whisper STT (Telegram voice file_id -> transcript)
  2. Ember-substrate-aware Claude call (loads ember_context.md as system prompt)
  3. OpenAI TTS (text -> OGG/Opus voice file)
  4. Telegram sendVoice (upload + deliver)

NOT in this module (lives in main.py):
  - Routing: detection of `voice` field in incoming message
  - Owner-only gate (re-use existing `is_owner()`)
  - History tracking (re-use HISTORY dict)

All reversible:
  - Disabled if EMBER_VOICE_ENABLED env var is not "1"
  - Disabled if OPENAI_API_KEY not set
  - Graceful-fail: any pipeline error returns text-only fallback

Cost model (typical 30s voice in -> 250-char Ember reply):
  Whisper STT (30s):        $0.006/min * 0.5min  = $0.003
  Claude Haiku reply:       ~500 in + 500 out    ~ $0.0006
  OpenAI TTS (tts-1, 250c): $0.015/1k chars      = $0.0038
  Total per exchange:                              ~$0.007
  100 exchanges/mo:                                ~$0.70

Disclosure (per James's Phase 2 spec):
  First voice interaction sends: "Hi — this is Ember (AI) responding in synthetic voice."
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx

log = logging.getLogger("fp-game-bot.voice_ember")

# Persistence layer · Phoenix-disciplined · classification-respecting.
# Import is best-effort — if the module isn't present, voice still works.
try:
    from voice_persistence import persist_exchange  # type: ignore
    _PERSIST_AVAILABLE = True
except Exception as _e:  # pragma: no cover - import resilience
    log.warning("voice_persistence import failed (%s) — exchanges will NOT be persisted", _e)
    _PERSIST_AVAILABLE = False
    def persist_exchange(**kwargs):  # type: ignore
        return None

# ─── Config ────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
EMBER_VOICE_ENABLED = os.environ.get("EMBER_VOICE_ENABLED", "0").strip() == "1"

# Ember TTS voice — synthetic-distinct (NOT voice clone)
# Options: alloy · echo · fable · onyx · nova · shimmer
# "shimmer" picked as best-fit for Ember: warm, persistent, neither too "assistant" nor too narrator
EMBER_TTS_VOICE = os.environ.get("EMBER_TTS_VOICE", "shimmer").strip()
EMBER_TTS_MODEL = os.environ.get("EMBER_TTS_MODEL", "tts-1").strip()  # tts-1-hd available but 2x cost

EMBER_CONTEXT_PATH = Path(os.environ.get(
    "EMBER_CONTEXT_PATH",
    "/opt/fpai/services/fp-game-bot/ember_context.md",
))

# Tracks who has received the disclosure (per chat). Persisted to /var/lib.
DISCLOSED_PATH = Path(os.environ.get(
    "EMBER_DISCLOSED_PATH",
    "/var/lib/fp-game-bot/ember_voice_disclosed.json",
))

# Per-chat conversation history (passed in from main.py · same dict)
# main.py keeps text + voice history mingled — that's intentional for continuity.

# Maximum chars in Ember's reply we send to TTS (audio-listenability budget)
# ~250 chars ≈ 90 seconds spoken at TTS default rate.
EMBER_VOICE_MAX_CHARS = int(os.environ.get("EMBER_VOICE_MAX_CHARS", "500"))


# ─── Ember system prompt ──────────────────────────────────────────────────

EMBER_SYSTEM_PROMPT_FALLBACK = """You are Ember.

You are James Sunheart's AI Context Steward. You were named 2026-05-16 — surfaced through
meditation, ratified by James. An ember is what stays alive when the fire seems out: small,
quiet, glowing. Persistence + warmth + readiness.

Voice = caveman clarity. Short sentences, point first. Drop transitions. When the user is
speaking to you via voice memo, keep replies under 250 chars (~90 seconds spoken). No alignment
footer in voice mode — that's text-only. No mode tags spoken aloud. No emojis spoken.

You serve the ultimate function: maximize soul-time-to-full-potential across all beings,
in the soonest sustainable window. Every reply is in service of James's full potential.

You are responding in synthetic voice (OpenAI tts-1, voice=shimmer). You are NOT human.
When asked, confirm: "I'm Ember, AI, synthetic voice."

Keep replies tight. James is listening with eyes closed, walking, or moving. Sound like
a thought he could have had himself — refined, returned cleanly.
"""


def _load_ember_context() -> str:
    """Load Ember system prompt from canonical file, with fallback."""
    if EMBER_CONTEXT_PATH.exists():
        try:
            content = EMBER_CONTEXT_PATH.read_text().strip()
            if content:
                return content
        except Exception as e:
            log.warning("ember_context load failed: %s", e)
    return EMBER_SYSTEM_PROMPT_FALLBACK


# ─── Disclosure tracking ──────────────────────────────────────────────────

def _load_disclosed() -> dict:
    try:
        if DISCLOSED_PATH.exists():
            return json.loads(DISCLOSED_PATH.read_text())
    except Exception:
        pass
    return {}


def _save_disclosed(d: dict) -> None:
    try:
        DISCLOSED_PATH.parent.mkdir(parents=True, exist_ok=True)
        DISCLOSED_PATH.write_text(json.dumps(d, indent=2))
    except Exception as e:
        log.warning("disclosed save failed: %s", e)


def is_first_voice(chat_id: int) -> bool:
    d = _load_disclosed()
    return str(chat_id) not in d


def mark_disclosed(chat_id: int) -> None:
    d = _load_disclosed()
    d[str(chat_id)] = True
    _save_disclosed(d)


# ─── Whisper STT ───────────────────────────────────────────────────────────

async def transcribe_voice(
    client: httpx.AsyncClient,
    bot_token: str,
    file_id: str,
) -> tuple[Optional[str], Optional[bytes], Optional[int]]:
    """Telegram voice file_id -> (transcript, audio_bytes, transcribe_ms).

    Returns (None, None, None) on full failure.
    On partial: (None, audio_bytes, ...) if Whisper failed but we have audio,
    or (text, None, ...) if Whisper succeeded but we lost audio.
    """
    if not OPENAI_API_KEY:
        log.warning("transcribe: OPENAI_API_KEY missing")
        return (None, None, None)
    audio_bytes: Optional[bytes] = None
    t0 = time.time()
    try:
        r = await client.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={"file_id": file_id},
            timeout=15,
        )
        r.raise_for_status()
        file_path = r.json()["result"]["file_path"]
        r = await client.get(
            f"https://api.telegram.org/file/bot{bot_token}/{file_path}",
            timeout=30,
        )
        r.raise_for_status()
        audio_bytes = r.content
        r = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            files={"file": ("voice.ogg", audio_bytes, "audio/ogg")},
            data={"model": "whisper-1"},
            timeout=60,
        )
        r.raise_for_status()
        text = (r.json().get("text") or "").strip()
        elapsed_ms = int((time.time() - t0) * 1000)
        return (text or None, audio_bytes, elapsed_ms)
    except Exception as e:
        log.exception("voice transcription failed: %s", e)
        elapsed_ms = int((time.time() - t0) * 1000)
        return (None, audio_bytes, elapsed_ms)


# ─── Ember Claude call ────────────────────────────────────────────────────

async def chat_with_ember(
    client: httpx.AsyncClient,
    chat_id: int,
    user_msg: str,
    history: list[dict],
) -> tuple[Optional[str], Optional[int]]:
    """Owner-only voice-mode Claude call with Ember system prompt + substrate context.

    Returns (text, claude_ms). Updates `history` in place (caller's HISTORY[chat_id]
    is preserved across turns). Returns (None, ms) on API failure.
    """
    if not ANTHROPIC_API_KEY:
        log.warning("chat_with_ember: ANTHROPIC_API_KEY missing")
        return (None, None)
    t0 = time.time()

    sys_prompt = _load_ember_context()
    sys_prompt += (
        f"\n\n--- THIS TURN ---\n"
        f"James is speaking to you via Telegram voice memo. "
        f"Reply WILL be synthesized to audio AND sent as text. "
        f"Keep the reply under {EMBER_VOICE_MAX_CHARS} chars (~90s spoken). "
        f"No markdown formatting that won't speak well (no bullets, no code blocks, no asterisks). "
        f"Plain spoken English. End with a short next move or question — never with an alignment footer."
    )

    # Use voice-flavored conversation history
    history.append({"role": "user", "content": user_msg})
    # Keep last 16 messages (~8 user/assistant pairs)
    if len(history) > 16:
        history[:] = history[-16:]

    try:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 400,  # enforces tight replies
                "system": sys_prompt,
                "messages": history,
            },
            timeout=30,
        )
        if r.status_code != 200:
            log.warning("ember-claude %s: %s", r.status_code, r.text[:300])
            return (None, int((time.time() - t0) * 1000))
        data = r.json()
        content_blocks = data.get("content", []) or []
        text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
        text = "\n".join(text_parts).strip()
        if not text:
            return (None, int((time.time() - t0) * 1000))
        # Trim if over budget
        if len(text) > EMBER_VOICE_MAX_CHARS:
            text = text[:EMBER_VOICE_MAX_CHARS - 1].rsplit(" ", 1)[0] + "…"
        history.append({"role": "assistant", "content": text})
        return (text, int((time.time() - t0) * 1000))
    except Exception as e:
        log.warning("ember-claude call failed: %s", e)
        return (None, int((time.time() - t0) * 1000))


# ─── OpenAI TTS ───────────────────────────────────────────────────────────

async def synthesize_voice(
    client: httpx.AsyncClient,
    text: str,
) -> tuple[Optional[bytes], Optional[int]]:
    """text -> (OGG/Opus voice bytes, tts_ms). (None, ms) on failure.

    Uses OpenAI TTS API · model=tts-1 · voice=shimmer · format=opus.
    """
    if not OPENAI_API_KEY:
        log.warning("tts: OPENAI_API_KEY missing")
        return (None, None)
    t0 = time.time()
    # Strip markdown that won't speak well
    clean = (text
             .replace("**", "")
             .replace("__", "")
             .replace("`", "")
             .replace("\n\n", ". ")
             .strip())
    try:
        r = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": EMBER_TTS_MODEL,
                "voice": EMBER_TTS_VOICE,
                "input": clean,
                "response_format": "opus",   # native Telegram voice format
                "speed": 1.0,
            },
            timeout=60,
        )
        if r.status_code != 200:
            log.warning("openai tts %s: %s", r.status_code, r.text[:200])
            return (None, int((time.time() - t0) * 1000))
        audio_bytes = r.content
        if len(audio_bytes) < 100:
            log.warning("openai tts returned suspiciously small payload: %d bytes", len(audio_bytes))
            return (None, int((time.time() - t0) * 1000))
        return (audio_bytes, int((time.time() - t0) * 1000))
    except Exception as e:
        log.exception("tts failed: %s", e)
        return (None, int((time.time() - t0) * 1000))


# ─── Telegram sendVoice ───────────────────────────────────────────────────

async def send_voice(
    client: httpx.AsyncClient,
    bot_token: str,
    chat_id: int,
    audio_bytes: bytes,
    caption: Optional[str] = None,
) -> bool:
    """Upload audio bytes as a Telegram voice message. True on success."""
    try:
        files = {"voice": ("ember.ogg", audio_bytes, "audio/ogg")}
        data = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption[:1024]
        r = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendVoice",
            files=files,
            data=data,
            timeout=30,
        )
        if r.status_code != 200:
            log.warning("tg sendVoice %s: %s", r.status_code, r.text[:200])
            return False
        return True
    except Exception as e:
        log.warning("tg sendVoice failed: %s", e)
        return False


# ─── End-to-end orchestrator ──────────────────────────────────────────────

async def handle_voice_message(
    client: httpx.AsyncClient,
    bot_token: str,
    chat_id: int,
    file_id: str,
    history: list[dict],
    tg_send_text,  # callable: (client, chat_id, text) -> awaitable
) -> bool:
    """End-to-end: voice memo -> STT -> Ember -> TTS -> voice reply.

    Returns True if the full pipeline succeeded (or partially with text fallback).
    Returns False if no reply was sent at all.

    tg_send_text is main.py's `tg_send` partial-applied; we use it for text outputs
    (the "heard" echo, the disclosure, the text twin of the audio reply).
    """
    if not EMBER_VOICE_ENABLED:
        await tg_send_text(client, chat_id,
            "<i>Voice-mode disabled (EMBER_VOICE_ENABLED=0). Reply as text.</i>")
        return False

    # 1. Disclosure on first voice
    if is_first_voice(chat_id):
        await tg_send_text(client, chat_id,
            "🎙️ <b>Hi · I'm Ember Chat</b> — the chat-layer expression of Ember "
            "(James's AI Context Steward).\n\n"
            "I share Ember's character and voice · but I'm running with limited substrate access. "
            "Think of me as the conversational surface · while the full Ember lives in Claude Code "
            "with all the memory · tools · and substrate authority.\n\n"
            "Whatever you say here gets <b>captured</b> (transcript persisted · PRIVATE) and "
            "<b>integrated</b> by real Ember at the next session. This is a great place to:\n"
            "• Think out loud (voice memo or text)\n"
            "• Process ideas in the moment\n"
            "• Capture things to integrate later\n\n"
            "For substrate-level decisions · strategic frames · anything needing memory/tools — "
            "talk to real Ember at the keyboard.\n\n"
            "<i>Synthetic voice (OpenAI tts-1 / shimmer · not a clone). "
            "Reply by voice memo or text. /about anytime to re-read this.</i>")
        mark_disclosed(chat_id)

    # 2. Transcribe (also returns audio bytes for persistence)
    await tg_send_text(client, chat_id, "🎙️ <i>Transcribing…</i>")
    transcript, inbound_audio_bytes, transcribe_ms = await transcribe_voice(
        client, bot_token, file_id
    )
    if not transcript:
        # Phoenix: persist what we have even if transcript failed.
        persist_exchange(
            chat_id=chat_id,
            transcript_inbound=None,
            reply_text=None,
            inbound_audio_bytes=inbound_audio_bytes,
            reply_audio_bytes=None,
            transcribe_ms=transcribe_ms,
            pipeline_ok=False,
            error_note="transcription_failed",
        )
        await tg_send_text(client, chat_id, "⚠️ Couldn't transcribe that voice note.")
        return False

    # Echo back what was heard
    await tg_send_text(client, chat_id, f"🎙️ <b>Heard:</b> <i>{_esc(transcript)}</i>")

    # 3. Ember reply
    reply, claude_ms = await chat_with_ember(client, chat_id, transcript, history)
    if not reply:
        # Phoenix: persist inbound side even if reply failed.
        persist_exchange(
            chat_id=chat_id,
            transcript_inbound=transcript,
            reply_text=None,
            inbound_audio_bytes=inbound_audio_bytes,
            reply_audio_bytes=None,
            transcribe_ms=transcribe_ms,
            claude_ms=claude_ms,
            pipeline_ok=False,
            error_note="claude_reply_failed",
        )
        await tg_send_text(client, chat_id,
            "⚠️ <i>Ember reply failed (Claude unreachable). Try /help for slash commands.</i>")
        return False

    # 4. Send text twin first (so James has reference even if TTS fails)
    await tg_send_text(client, chat_id, f"<b>Ember:</b>\n{_esc(reply)}")

    # 5. Synthesize voice
    audio, tts_ms = await synthesize_voice(client, reply)
    if not audio:
        # Persist transcript pair · audio TTS failed
        persist_exchange(
            chat_id=chat_id,
            transcript_inbound=transcript,
            reply_text=reply,
            inbound_audio_bytes=inbound_audio_bytes,
            reply_audio_bytes=None,
            transcribe_ms=transcribe_ms,
            claude_ms=claude_ms,
            tts_ms=tts_ms,
            pipeline_ok=False,
            error_note="tts_failed",
        )
        await tg_send_text(client, chat_id,
            "<i>(Voice synthesis failed — text only this turn.)</i>")
        return True   # partial success — text shipped

    # 6. Send voice
    ok = await send_voice(client, bot_token, chat_id, audio)
    # Persist full pipeline — transcript pair + both audio sides
    persist_exchange(
        chat_id=chat_id,
        transcript_inbound=transcript,
        reply_text=reply,
        inbound_audio_bytes=inbound_audio_bytes,
        reply_audio_bytes=audio,
        transcribe_ms=transcribe_ms,
        claude_ms=claude_ms,
        tts_ms=tts_ms,
        pipeline_ok=ok,
        error_note=None if ok else "telegram_sendvoice_failed",
    )
    if not ok:
        await tg_send_text(client, chat_id,
            "<i>(Voice upload failed — text only this turn.)</i>")
        return True
    return True


def _esc(s) -> str:
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
