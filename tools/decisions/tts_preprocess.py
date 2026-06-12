#!/usr/bin/env python3
"""
TTS preprocessor · v1 · 2026-05-24

Cleans text before passing to OpenAI TTS so Nova reads it naturally instead
of literally pronouncing dollar amounts, abbreviations, URLs, code blocks.

Usage:
  from tts_preprocess import preprocess
  clean = preprocess(raw_text)
  # then pass clean to OpenAI /audio/speech

Or via CLI:
  echo "She made $94K last quarter at 12% APY" | python3 tts_preprocess.py
  → "She made ninety-four thousand dollars last quarter at twelve percent annual yield"

Trade-offs: aggressive cleanup may lose precision (94.5K → "ninety-four thousand"
not "ninety-four and a half thousand"). For voice that's fine — the text version
in the same TG thread carries the exact number.
"""

import re
import sys


# Common abbreviations that Nova butchers
ABBREVIATIONS = {
    r"\bvs\.\B": "versus",
    r"\bvs\b": "versus",
    r"\be\.g\.\B": "for example",
    r"\bi\.e\.\B": "that is",
    r"\betc\.\B": "et cetera",
    r"\bAPY\b": "annual yield",
    r"\bAPR\b": "annual rate",
    r"\bAUM\b": "assets under management",
    r"\bTVL\b": "total value locked",
    r"\bDeFi\b": "defi",
    r"\bUSDC\b": "U S D C",
    r"\bUSDT\b": "U S D T",
    r"\bsUSDC\b": "S U S D C",
    r"\bsyUSDC\b": "S Y U S D C",
    r"\bPT\b": "P T",
    r"\bWBTC\b": "W B T C",
    r"\bcbBTC\b": "C B B T C",
    r"\bwstETH\b": "W S T E T H",
    r"\bJitoSOL\b": "jito sol",
    r"\bsUSDe\b": "S U S D E",
    r"\beUSDe\b": "E U S D E",
    r"\beETH\b": "E E T H",
    r"\bMetaMorpho\b": "meta morfo",
    r"\bMorpho\b": "morfo",
    r"\bPendle\b": "pendle",
    r"\bGauntlet\b": "gauntlet",
    r"\bERC-4626\b": "vault standard",
    r"\bERC-20\b": "token standard",
    r"\bTG\b": "telegram",
    r"\bAI\b": "A I",
    r"\bCLI\b": "command line",
    r"\bAPI\b": "A P I",
    r"\bUX\b": "user experience",
    r"\bLP\b": "L P",
    r"\bLPs\b": "L Ps",
    r"\bHL\b": "hyperliquid",
    r"\bSOL\b": "sol",
    r"\bBTC\b": "bitcoin",
    r"\bETH\b": "ethereum",
    r"\bXRP\b": "X R P",
    r"\bP&L\b": "P and L",
    r"\bP/E\b": "P E",
    r"\bROI\b": "R O I",
    r"\bUSD\b": "U S D",
    r"\bUTC\b": "U T C",
    r"\bCR\b": "Costa Rica",
    r"\bTOS\b": "terms of service",
}


def _expand_dollar_amount(match: re.Match) -> str:
    """Convert $X.XK / $XM / $X / $X.XX into spoken form."""
    raw = match.group(0)
    sign = "negative " if raw.startswith("-$") or raw.startswith("$-") else ""
    # extract the numeric and suffix
    m = re.match(r"-?\$?-?(\d+(?:[.,]\d+)?)\s*([KkMmBb])?", raw)
    if not m:
        return raw
    num_s, suffix = m.group(1), m.group(2)
    num_s = num_s.replace(",", "")
    try:
        num = float(num_s)
    except ValueError:
        return raw

    if suffix:
        suffix = suffix.lower()
        multiplier_word = {"k": "thousand", "m": "million", "b": "billion"}[suffix]
        if num.is_integer():
            return f"{sign}{int(num):d} {multiplier_word} dollars"
        # 94.5K → "ninety-four point five thousand"
        return f"{sign}{num:g} {multiplier_word} dollars"

    # No suffix: $X or $X.XX
    if num.is_integer():
        return f"{sign}{int(num):d} dollars"
    # Has decimals — likely cents
    whole = int(num)
    cents = round((num - whole) * 100)
    if cents == 0:
        return f"{sign}{whole} dollars"
    return f"{sign}{whole} dollars and {cents} cents"


def _expand_percent(match: re.Match) -> str:
    raw = match.group(0)
    m = re.match(r"(-?\d+(?:\.\d+)?)\s*%", raw)
    if not m:
        return raw
    num_s = m.group(1)
    return f"{num_s} percent"


def _expand_decimal_small(match: re.Match) -> str:
    """0.0024 → 'zero point zero zero two four' is bad; instead 'a fraction of a cent'."""
    raw = match.group(0).strip()
    # for now, just leave it — Nova handles 0.X reasonably
    return raw


def _strip_urls(text: str) -> str:
    # http(s) URLs
    text = re.sub(r"https?://\S+", "", text)
    # bare domains like fullpotential.ai/bottleneck
    text = re.sub(r"\b\w+\.(com|ai|io|xyz|app|finance|org|net|co|me)(/\S*)?", "", text)
    return text


def _strip_code_blocks(text: str) -> str:
    # backtick-wrapped code (single and triple)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`\n]+`", "", text)
    # absolute paths starting with /
    text = re.sub(r"/[A-Za-z][\w/.\-]+", "a file path", text)
    # home paths
    text = re.sub(r"~/[\w/.\-]+", "a file path", text)
    # 0x hex strings (addresses)
    text = re.sub(r"\b0x[a-fA-F0-9]{6,}\b", "an address", text)
    return text


def _strip_html(text: str) -> str:
    # <b>, <code>, <i>, etc. tags
    text = re.sub(r"<[^>]+>", "", text)
    return text


def _smooth_punctuation(text: str) -> str:
    # em-dash and en-dash → comma
    text = text.replace("—", ", ")
    text = text.replace("–", ", ")
    # smart quotes → straight
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    # ellipsis
    text = text.replace("…", "...")
    # tilde → "approximately"
    text = re.sub(r"~(?=\d)", "approximately ", text)
    # arrow → "to"
    text = text.replace("→", " to ")
    text = text.replace("←", " from ")
    # ampersand
    text = re.sub(r"\s&\s", " and ", text)
    return text


def _collapse_whitespace(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def preprocess(text: str) -> str:
    """Main entry — clean text for TTS synthesis."""
    if not text:
        return ""

    # 1. Strip code blocks, URLs, HTML (before number substitution which could match these)
    text = _strip_code_blocks(text)
    text = _strip_html(text)
    text = _strip_urls(text)

    # 2. Smooth punctuation
    text = _smooth_punctuation(text)

    # 3. Expand $ amounts (must come before abbreviation expansion in case any abbreviation is X-letter codes)
    # Match: $94K, $1.5M, $0.50, $-22.22, -$5, $94, $1,500
    text = re.sub(
        r"-?\$-?\d+(?:[.,]\d+)?(?:\s*[KkMmBb])?",
        _expand_dollar_amount,
        text,
    )

    # 4. Expand percents
    text = re.sub(r"-?\d+(?:\.\d+)?\s*%", _expand_percent, text)

    # 5. Expand abbreviations
    for pattern, replacement in ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text)

    # 6. Whitespace normalize
    text = _collapse_whitespace(text)

    return text


if __name__ == "__main__":
    raw = sys.stdin.read()
    print(preprocess(raw))
