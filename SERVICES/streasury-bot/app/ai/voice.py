"""app/ai/voice.py — voice note (.ogg/Opus from Telegram) → text via Whisper.

The handler then re-runs the text through ai/parse.py to get a structured
intent, just like a typed message.
"""
from __future__ import annotations

import io
import logging

import httpx

from ..config import settings

log = logging.getLogger("streasury.voice")


async def transcribe(audio_bytes: bytes, *, filename: str = "voice.ogg") -> str | None:
    if not settings.openai_api_key:
        return None
    files = {"file": (filename, io.BytesIO(audio_bytes), "audio/ogg")}
    data = {"model": settings.openai_whisper_model, "response_format": "json"}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                data=data,
                files=files,
            )
            r.raise_for_status()
            return (r.json() or {}).get("text") or None
    except Exception as e:
        log.warning("whisper failed: %s", e)
        return None
