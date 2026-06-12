#!/usr/bin/env python3
"""
voice_route · v1 · 2026-05-31  ·  the heart of the Voice → Telegram path
Take an audio file (a Telegram voice note), transcribe it, and route the words into
the system the same way typing into ASK EMBER would — so James can just *speak*.

  audio (.ogg/.m4a/.mp3) → Whisper transcription → append to ASK EMBER.md (## New)
                                                  → (caller then runs `ember` to route)

This is the transport-agnostic core. The Telegram listener (separate, see spec) hands
it a downloaded voice file; this turns speech into a routed ask. Transcription via
OpenAI Whisper (OPENAI_API_KEY env) or local `whisper`/`whisper.cpp` if present.

Usage:
  voice_route.py <audio-file>            # transcribe + append to ASK EMBER
  voice_route.py <audio-file> --print    # transcribe + print only
"""
import os, sys, subprocess, argparse, datetime
from pathlib import Path

VAULT = Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
ASK = VAULT / "ASK EMBER.md"

def transcribe(audio):
    # 1) OpenAI Whisper API if key present
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        try:
            import urllib.request, json, mimetypes
            boundary = "----vr" + datetime.datetime.now().strftime("%H%M%S")
            data = []
            data.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nwhisper-1\r\n".encode())
            fn = os.path.basename(audio)
            ctype = mimetypes.guess_type(audio)[0] or "application/octet-stream"
            data.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fn}\"\r\nContent-Type: {ctype}\r\n\r\n".encode())
            data.append(open(audio, "rb").read())
            data.append(f"\r\n--{boundary}--\r\n".encode())
            body = b"".join(data)
            req = urllib.request.Request(
                "https://api.openai.com/v1/audio/transcriptions", data=body,
                headers={"Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())["text"].strip()
        except Exception as e:
            print(f"(OpenAI Whisper failed: {e}; trying local)", file=sys.stderr)
    # 2) local whisper CLI fallback
    for cmd in ("whisper", "whisper.cpp"):
        if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
            out = subprocess.run([cmd, audio, "--output_format", "txt"], capture_output=True, text=True)
            txt = Path(audio).with_suffix(".txt")
            if txt.exists():
                return txt.read_text().strip()
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--print", dest="pr", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.audio):
        print("no such file:", a.audio); sys.exit(1)
    text = transcribe(a.audio)
    if not text:
        print("transcription unavailable (set OPENAI_API_KEY or install whisper)"); sys.exit(2)
    print("📝", text)
    if a.pr:
        return
    # append into ASK EMBER under ## New (so `ember` routes it like a typed ask)
    doc = ASK.read_text(errors="ignore")
    stamp = datetime.datetime.now().strftime("%H:%M")
    line = f"- 🎙️ ({stamp}, voice) {text}"
    if "## New" in doc:
        doc = doc.replace("## New", "## New\n" + line, 1)
    else:
        doc += "\n## New\n" + line + "\n"
    ASK.write_text(doc)
    print(f"→ appended to ASK EMBER. Run `ember` to route (or it'll be caught by the loop).")

if __name__ == "__main__":
    main()
