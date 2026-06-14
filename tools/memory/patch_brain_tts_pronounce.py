#!/usr/bin/env python3
"""Patch v7 — proper pronunciation for Ember's voice replies.

James 2026-06-14: "Ember should use proper pronunciation etc." Her text bubbles
are warm-lowercase (right for reading), but _strip_for_tts only removed HTML —
no pronunciation pass — so the spoken version stumbled on symbols, emoji,
abbreviations, and lowercase prosody.

_strip_for_tts feeds ONLY the voice synthesis, so this pass keeps the on-screen
text warm-lowercase while the SPOKEN version gets: emoji dropped, symbols spoken
as words, abbreviations expanded, and sentence casing restored for natural prosody.

Safety: anchors match-once-or-abort, backup, compile-check, auto-revert.
"""
import shutil, py_compile, sys, time
P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()
edits = []

# E1 — add the pronunciation helper just before _strip_for_tts
HELPER = '''def _tts_pronounce(text: str) -> str:
    """Make text sound right when spoken (the on-screen bubble stays as written;
    only the voice gets this): drop emoji, speak symbols as words, expand common
    abbreviations, and restore sentence casing for natural prosody."""
    if not text:
        return text
    # Drop emoji / pictographs / arrows — TTS reads them aloud as names.
    text = re.sub("[\\U0001F000-\\U0001FAFF\\U00002600-\\U000027BF"
                  "\\U0001F1E6-\\U0001F1FF\\u2190-\\u21FF\\u2B00-\\u2BFF]", "", text)
    # Symbols -> spoken words.
    text = text.replace("&", " and ")
    text = re.sub(r"\\s*[\\u2014\\u2013\\u00b7\\u2022]\\s*", ", ", text)
    text = re.sub(r"(?<=\\d)\\s*%", " percent", text)
    text = re.sub(r"\\$\\s*(\\d)", r"\\1 dollars", text)
    text = re.sub(r"(?<=\\w)/(?=\\w)", " ", text)
    # Common abbreviations.
    for pat, repl in ((r"\\be\\.g\\.", "for example"), (r"\\bi\\.e\\.", "that is"),
                      (r"\\bw/\\b", "with"), (r"\\betc\\.?", "and so on"),
                      (r"\\bvs\\.?", "versus"), (r"\\baka\\b", "also known as")):
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    # Prosody: standalone 'i' -> 'I', capitalize sentence starts.
    text = re.sub(r"\\bi\\b", "I", text)
    text = re.sub(r"(^|[.!?]\\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return re.sub(r"\\s+", " ", text).strip()


def _strip_for_tts(html_text: str) -> str:'''
edits.append(("def _strip_for_tts(html_text: str) -> str:", HELPER))

# E2 — run the pronunciation pass before the length trim
edits.append((
    '    text = re.sub(r"\\s+", " ", text).strip()\n    if len(text) > _TTS_MAX_CHARS:',
    '    text = re.sub(r"\\s+", " ", text).strip()\n    text = _tts_pronounce(text)\n    if len(text) > _TTS_MAX_CHARS:',
))

for a, b in edits:
    n = src.count(a)
    if n != 1:
        print(f"ABORT: anchor matched {n}x (need 1): {a[:60]!r}")
        sys.exit(1)
    src = src.replace(a, b)

bak = P + ".bak-tts-v7-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak)
open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"OK — {len(edits)} edits applied, file compiles. Backup: {bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak, P)
    print(f"REVERTED — syntax error: {e}")
    sys.exit(1)
