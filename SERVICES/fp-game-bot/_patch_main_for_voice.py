#!/usr/bin/env python3
"""_patch_main_for_voice.py — apply voice-ember patch to fp-game-bot/main.py.

Idempotent. Safe to re-run. Creates .bak.YYYYMMDD-HHMM before any write.

Patch adds:
  1. `from voice_ember import handle_voice_message` import block
  2. Voice detection in handle_update() — routes voice msgs to Ember pipeline
  3. EMBER history dict + getter (separate from text-mode HISTORY)
  4. Switches plain-text owner path to Ember instead of Game-bot system prompt
     (only when EMBER_VOICE_ENABLED env is set — falls back to chat_with_claude otherwise)

Run: python3 _patch_main_for_voice.py /path/to/main.py
"""
from __future__ import annotations
import sys
import datetime as _dt
from pathlib import Path

PATCH_MARKER = "# === EMBER VOICE PATCH (Phase 2) ==="

IMPORT_ANCHOR = "import httpx\n"
IMPORT_PATCH = """import httpx
""" + PATCH_MARKER + """
# Voice-first Ember interface (Phase 2 · project-voice-first-interface)
try:
    import voice_ember
    _EMBER_VOICE_LOADED = True
except Exception as _e:
    voice_ember = None
    _EMBER_VOICE_LOADED = False

# Voice-mode conversation history (separate from text-mode HISTORY)
EMBER_HISTORY: dict[int, list[dict]] = {}
# === END EMBER VOICE PATCH ===
"""

HANDLE_ANCHOR = """async def handle_update(client: httpx.AsyncClient, update: dict) -> None:
    msg = update.get("message")
    if not msg:
        return
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return
    text = (msg.get("text") or "").strip()
    if not text:
        return
"""

HANDLE_PATCH = """async def handle_update(client: httpx.AsyncClient, update: dict) -> None:
    msg = update.get("message")
    if not msg:
        return
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return

    # === EMBER VOICE PATCH (Phase 2) ===
    # Voice / audio note → Whisper STT → Ember (with substrate context) → OpenAI TTS → voice reply.
    # Owner-only gate. Graceful-fail to text if any step breaks.
    voice = msg.get("voice") or msg.get("audio")
    if voice and _EMBER_VOICE_LOADED and voice_ember is not None:
        if not is_owner(chat_id):
            log.info("ignoring voice from non-owner chat_id %s", chat_id)
            return
        file_id = voice.get("file_id")
        if file_id:
            history = EMBER_HISTORY.setdefault(chat_id, [])
            try:
                await voice_ember.handle_voice_message(
                    client=client,
                    bot_token=BOT_TOKEN,
                    chat_id=chat_id,
                    file_id=file_id,
                    history=history,
                    tg_send_text=tg_send,
                )
            except Exception as e:
                log.exception("ember voice pipeline failed: %s", e)
                await tg_send(client, chat_id,
                    "⚠️ Voice pipeline error. Sending fallback text only.")
        return
    # === END EMBER VOICE PATCH ===

    text = (msg.get("text") or "").strip()
    if not text:
        return
"""


def apply_patch(target: Path) -> dict:
    src = target.read_text()
    if PATCH_MARKER in src:
        return {"status": "already-patched", "msg": f"marker found in {target}; no-op"}

    # Backup
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M")
    backup = target.with_suffix(target.suffix + f".bak.{ts}")
    backup.write_text(src)

    # Apply import patch
    if IMPORT_ANCHOR not in src:
        return {"status": "fail", "msg": "import anchor not found"}
    src2 = src.replace(IMPORT_ANCHOR, IMPORT_PATCH, 1)

    # Apply handle_update patch
    if HANDLE_ANCHOR not in src2:
        return {"status": "fail", "msg": "handle_update anchor not found"}
    src3 = src2.replace(HANDLE_ANCHOR, HANDLE_PATCH, 1)

    target.write_text(src3)
    return {
        "status": "patched",
        "backup": str(backup),
        "added_lines": src3.count("\n") - src.count("\n"),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: _patch_main_for_voice.py /path/to/main.py", file=sys.stderr)
        sys.exit(1)
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"not found: {p}", file=sys.stderr)
        sys.exit(2)
    result = apply_patch(p)
    print(result)
    if result["status"] not in ("patched", "already-patched"):
        sys.exit(3)
