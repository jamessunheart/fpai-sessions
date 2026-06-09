#!/usr/bin/env python3
"""
Telegram voice reply · v1 · 2026-05-24

Take text, generate OGG-Opus via OpenAI TTS (Nova by default), send to
@sunheartbrain_bot via sendVoice for native voice-bubble UX.

Trust-tier 4.1 reversible · cost ~$0.015/min audio.

Usage:
  echo "text to speak" | python3 send_tg_voice.py
  python3 send_tg_voice.py --text "say this"
  python3 send_tg_voice.py --file /tmp/message.txt
  python3 send_tg_voice.py --voice onyx --text "..."   # deeper voice
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
CREDS_FILE = HOME / ".config" / "fpai" / "tg_brain" / "creds.cache"
OPENAI_KEY_FILE = HOME / ".config" / "fpai" / "openai" / "api.token"
AUDIO_OUT_DIR = HOME / ".config" / "fpai" / "tg_brain" / "outbound_audio"
OPENAI_TTS = "https://api.openai.com/v1/audio/speech"
TG_API = "https://api.telegram.org"

# Per aria-bridge/voice.py — Nova is warm/clear/direct (default for Ember).
# Other options: alloy, echo, fable, onyx, shimmer
DEFAULT_VOICE = "nova"


def load_creds() -> dict:
    creds = {}
    if not CREDS_FILE.exists():
        return creds
    for line in CREDS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        creds[k.strip()] = v.strip().strip('"').strip("'")
    return creds


def synthesize_voice(text: str, voice: str = DEFAULT_VOICE) -> Path | None:
    """Generate OGG-Opus audio via OpenAI TTS. Returns path to saved file."""
    if not OPENAI_KEY_FILE.exists():
        print(f"missing key: {OPENAI_KEY_FILE}", file=sys.stderr)
        return None
    key = OPENAI_KEY_FILE.read_text().strip()

    AUDIO_OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = AUDIO_OUT_DIR / f"ember_{voice}_{ts}.ogg"

    body = {
        "model": "tts-1",
        "voice": voice,
        "input": text,
        "response_format": "opus",  # OGG-Opus — TG-compatible voice format, no ffmpeg needed
    }

    cmd = [
        "curl", "-sS", "-X", "POST", OPENAI_TTS,
        "-H", f"Authorization: Bearer {key}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(body),
        "-o", str(out_path),
        "-w", "%{http_code}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"curl exit {r.returncode}: {r.stderr[:200]}", file=sys.stderr)
        return None
    http_code = r.stdout.strip().split("\n")[-1]
    if http_code != "200":
        print(f"OpenAI TTS HTTP {http_code}", file=sys.stderr)
        # Try to read error body if present
        if out_path.exists():
            try:
                err = out_path.read_text()
                print(f"body: {err[:300]}", file=sys.stderr)
            except Exception:
                pass
        return None

    if not out_path.exists() or out_path.stat().st_size == 0:
        return None
    return out_path


def send_voice_to_telegram(audio_path: Path, creds: dict, caption: str | None = None) -> tuple[bool, str]:
    token = creds.get("TELEGRAM_BOT_TOKEN")
    chat_id = creds.get("OWNER_TG_ID") or creds.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False, "creds missing"

    url = f"{TG_API}/bot{token}/sendVoice"
    cmd = [
        "curl", "-sS", "-X", "POST", url,
        "-F", f"chat_id={chat_id}",
        "-F", f"voice=@{audio_path}",
    ]
    if caption:
        cmd.extend(["-F", f"caption={caption}"])

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return False, f"curl exit {r.returncode}: {r.stderr[:200]}"

    try:
        data = json.loads(r.stdout)
        if not data.get("ok"):
            return False, f"TG error: {data.get('description', r.stdout[:200])}"
        return True, f"message_id={data['result']['message_id']}"
    except json.JSONDecodeError:
        return False, f"non-json: {r.stdout[:200]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="Text to speak (or pipe via stdin)")
    ap.add_argument("--file", help="Path to file containing text")
    ap.add_argument("--voice", default=DEFAULT_VOICE,
                    help="OpenAI voice: nova/alloy/echo/fable/onyx/shimmer")
    ap.add_argument("--caption", help="Optional text caption alongside the voice message")
    ap.add_argument("--save-only", action="store_true",
                    help="Generate audio but don't send")
    args = ap.parse_args()

    if args.file:
        text = Path(args.file).read_text().strip()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read().strip()

    if not text:
        print("no text supplied", file=sys.stderr)
        sys.exit(2)

    if len(text) > 4096:
        print(f"text too long ({len(text)} > 4096), truncating", file=sys.stderr)
        text = text[:4090] + "..."

    print(f"synthesizing · voice={args.voice} · {len(text)} chars", file=sys.stderr)
    audio = synthesize_voice(text, args.voice)
    if not audio:
        print("synthesis failed", file=sys.stderr)
        sys.exit(1)

    print(f"audio saved · {audio} · {audio.stat().st_size} bytes", file=sys.stderr)

    if args.save_only:
        print(audio)
        return

    creds = load_creds()
    ok, msg = send_voice_to_telegram(audio, creds, caption=args.caption)
    print(f"{'✓' if ok else '✗'} {msg}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
