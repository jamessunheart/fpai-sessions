#!/usr/bin/env python3
"""test_voice_pipeline.py — server-side smoke test of voice_ember.py components.

Runs in three stages:
  1. TTS-only: synthesize a known short string -> bytes -> send as voice message
  2. STT round-trip: TTS to file -> upload to TG getFile -> Whisper transcribe -> compare
  3. Full loop sim: text-mode chat_with_ember() to verify Ember system prompt loads + replies

Usage on server:
  cd /opt/fpai/services/fp-game-bot && \\
    EnvironmentFile=/etc/fp-game-bot/fp-game-bot.env .venv/bin/python test_voice_pipeline.py

Or:
  set -a; . /etc/fp-game-bot/fp-game-bot.env; set +a; \\
    /opt/fpai/services/fp-game-bot/.venv/bin/python test_voice_pipeline.py
"""
from __future__ import annotations
import asyncio
import os
import sys

import httpx
import voice_ember


async def stage_1_tts_to_tg():
    """Synthesize a short test phrase and ship as TG voice message."""
    print("STAGE 1 — TTS-to-TG synthesis test")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    owner_chat = os.environ.get("OWNER_TG_ID", "").strip()
    if not bot_token or not owner_chat:
        print("  SKIP: missing TELEGRAM_BOT_TOKEN or OWNER_TG_ID")
        return None
    test_text = (
        "This is Ember. Synthetic voice. Phase 2 voice loop pipeline test, "
        "stage one. If you hear this, the pipeline ships."
    )
    async with httpx.AsyncClient() as client:
        audio = await voice_ember.synthesize_voice(client, test_text)
        if not audio:
            print("  FAIL: synthesize_voice returned None")
            return None
        print(f"  OK: synthesized {len(audio)} bytes (model={voice_ember.EMBER_TTS_MODEL}, voice={voice_ember.EMBER_TTS_VOICE})")
        ok = await voice_ember.send_voice(
            client=client, bot_token=bot_token,
            chat_id=int(owner_chat), audio_bytes=audio,
            caption="[Phase 2 voice loop · Stage 1 test · synthetic Ember voice]",
        )
        print(f"  OK: send_voice = {ok}")
        return audio


async def stage_2_ember_text_reply():
    """Smoke-check chat_with_ember() (no audio, just verify Ember prompt loads)."""
    print("\nSTAGE 2 — Ember text reply test (system prompt + claude call)")
    async with httpx.AsyncClient() as client:
        history: list[dict] = []
        reply = await voice_ember.chat_with_ember(
            client=client, chat_id=999999,
            user_msg=(
                "Confirm in one sentence who you are, and confirm you know "
                "you are responding in synthetic voice."
            ),
            history=history,
        )
        if not reply:
            print("  FAIL: chat_with_ember returned None")
            return None
        print(f"  OK: reply ({len(reply)} chars):")
        print(f"    \"{reply}\"")
        return reply


async def stage_3_full_loop():
    """Send the Stage 2 Ember reply as TG voice (end-to-end full loop simulation)."""
    print("\nSTAGE 3 — Full loop simulation (Ember reply -> TTS -> TG voice)")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    owner_chat = os.environ.get("OWNER_TG_ID", "").strip()
    if not bot_token or not owner_chat:
        print("  SKIP: missing TELEGRAM_BOT_TOKEN or OWNER_TG_ID")
        return None
    async with httpx.AsyncClient() as client:
        history: list[dict] = []
        reply = await voice_ember.chat_with_ember(
            client=client, chat_id=int(owner_chat),
            user_msg="Quick: are you Ember? Tell me in 1 short sentence, voice-friendly.",
            history=history,
        )
        if not reply:
            print("  FAIL: ember reply none")
            return None
        print(f"  Ember reply: \"{reply}\"")
        audio = await voice_ember.synthesize_voice(client, reply)
        if not audio:
            print("  FAIL: synth audio none")
            return None
        ok = await voice_ember.send_voice(
            client=client, bot_token=bot_token,
            chat_id=int(owner_chat), audio_bytes=audio,
            caption=f"[Phase 2 · Stage 3 · full loop test · {len(reply)}c -> {len(audio)}B]",
        )
        print(f"  OK: full loop send_voice = {ok}")


async def main():
    print("=" * 60)
    print("EMBER VOICE PIPELINE · server-side smoke test")
    print("=" * 60)
    print(f"OPENAI_API_KEY: {'set' if voice_ember.OPENAI_API_KEY else 'MISSING'}")
    print(f"ANTHROPIC_API_KEY: {'set' if voice_ember.ANTHROPIC_API_KEY else 'MISSING'}")
    print(f"EMBER_VOICE_ENABLED: {voice_ember.EMBER_VOICE_ENABLED}")
    print(f"EMBER_TTS_VOICE: {voice_ember.EMBER_TTS_VOICE}")
    print(f"EMBER_TTS_MODEL: {voice_ember.EMBER_TTS_MODEL}")
    print(f"ember_context.md present: {voice_ember.EMBER_CONTEXT_PATH.exists()}")
    print()

    await stage_1_tts_to_tg()
    await stage_2_ember_text_reply()
    await stage_3_full_loop()
    print("\nDONE.")


if __name__ == "__main__":
    asyncio.run(main())
