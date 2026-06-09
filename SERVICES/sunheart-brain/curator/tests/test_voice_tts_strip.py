"""Smoke test for the voice-out HTML-stripping helper used before TTS.

The logic is mirrored from tgbot._strip_for_tts so we can validate it without
importing the whole bot module (which pulls DB drivers etc).
"""
import re

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_TTS_MAX_CHARS = 1200


def _strip_for_tts(html_text: str) -> str:
    if not html_text:
        return ""
    cut = re.split(r"\n*<b>\s*Sources\b", html_text, maxsplit=1, flags=re.IGNORECASE)
    text = cut[0]
    text = _HTML_TAG_RE.sub("", text)
    text = (text
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#x27;", "'"))
    text = re.sub(r"^\s*[•\-\*]\s+", ". ", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > _TTS_MAX_CHARS:
        text = text[: _TTS_MAX_CHARS - 1].rstrip() + "…"
    return text


def test_basic_strip():
    sample = (
        "Burn rate is about $8.4k/month, runway 12 months [1].\n\n"
        "<b>Next moves</b>\n"
        "• Tighten village line\n"
        "• Push OneBPO close\n\n"
        "<b>Sources</b> <i>([N] in answer maps here)</i>\n"
        "<i>[1]</i> <code>core/STATE/NOW.md</code>"
    )
    out = _strip_for_tts(sample)
    assert "Sources" not in out
    assert "<b>" not in out
    assert "•" not in out
    assert "$8.4k" in out
    assert "Tighten village line" in out


def test_entity_decode():
    assert _strip_for_tts("a &amp; b &lt;c&gt;") == "a & b <c>"


def test_empty():
    assert _strip_for_tts("") == ""
    assert _strip_for_tts(None) == ""


def test_truncation():
    long = "word " * 500
    out = _strip_for_tts(long)
    assert len(out) <= _TTS_MAX_CHARS


if __name__ == "__main__":
    test_basic_strip()
    test_entity_decode()
    test_empty()
    test_truncation()
    print("OK")
