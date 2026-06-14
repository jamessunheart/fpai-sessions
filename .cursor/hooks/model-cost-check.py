#!/usr/bin/env python3
"""Cursor beforeSubmitPrompt hook: nudge toward cheaper models for routine work.

Reads JSON from stdin. The hook classifies the user prompt and, when it looks
routine, returns `additional_context` recommending a model downgrade. The user
can ignore the nudge — this hook never blocks.

Fail-open: any error prints `{}` so prompts always go through.
"""
from __future__ import annotations

import json
import re
import sys


# --- Heuristics ---------------------------------------------------------------

# Strong "this needs Opus/GPT-5.4" signals: architecture, deep reasoning,
# multi-system trade-offs, long autonomous runs.
HEAVY_SIGNALS = [
    r"\barchitect(ure|ural)?\b",
    r"\btrade[- ]?off",
    r"\bdesign\s+(the\s+)?(system|approach|api|schema)",
    r"\bplan\b.*\b(refactor|migration|rewrite|overhaul)",
    r"\b(refactor|migrate|rewrite)\b.*\b(whole|entire|all|across)",
    r"\b(debug|investigate|root[- ]cause)\b.*\b(complex|tricky|race|concurren|deadlock)",
    r"\bhold\s+the\s+plot",
    r"\bautonomous\b.*\b(hours?|long|all\s+day)",
    r"\bdecide\s+between\b",
    r"\bcompare\s+(approaches?|options?|strategies)",
]

# "Cheap model is fine" signals: small targeted edits, lookups, formatting,
# single-file work, doc tweaks.
CHEAP_SIGNALS = [
    r"\b(fix|add|update|change|tweak|rename|remove|delete)\b.*\b(typo|comment|log|import|variable|name)",
    r"\bformat\b",
    r"\blint\b",
    r"\bone[- ]liner",
    r"\bsingle\s+(file|function|line)",
    r"\b(what|where|how)\s+(does|is|are)\b.*\?",  # lookup question
    r"\bshow\s+me\b",
    r"\bprint\b.*\b(status|version|config)",
    r"\brun\s+(the\s+)?(test|tests|script|deploy|backup)",
    r"\brestart\b",
    r"\bcheck\s+(status|health|logs?)",
    r"\bgrep\b|\bsearch\s+for\b",
    r"\badd\s+(a\s+)?(comment|docstring|log)",
]

# UI/frontend signals → suggest Gemini.
FRONTEND_SIGNALS = [
    r"\b(ui|ux|frontend|css|tailwind|component|tsx|jsx|react|vue|svelte)\b",
    r"\bmockup\b|\bwireframe\b|\bscreenshot\b",
    r"\bstyle\b.*\b(button|page|layout|card)",
]

# Bulk fan-out signals → suggest Codex Mini + subagents.
BULK_SIGNALS = [
    r"\b(all|every|each)\s+(file|service|module|test)",
    r"\bbulk\b",
    r"\bmass\b",
    r"\bsweep\b",
    r"\bacross\s+(the\s+)?(repo|codebase|project)",
]

# Massive context signals → suggest Grok.
HUGE_CONTEXT_SIGNALS = [
    r"\b(load|read|scan|analyze)\b.*\b(everything|whole\s+repo|all\s+logs|full\s+history)",
    r"\b\d{3,}k\s+tokens?",
    r"\b(million|1m|2m)\s+tokens?",
]


def matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def classify(prompt: str) -> tuple[str, str] | None:
    """Return (recommended_model, reason) or None if no nudge needed.

    Priority: heavy signals win (no downgrade). Otherwise pick the most specific
    cheap pathway.
    """
    if matches_any(prompt, HEAVY_SIGNALS):
        return None  # Opus is appropriate, don't nag.

    if matches_any(prompt, HUGE_CONTEXT_SIGNALS):
        return ("Grok 4.20", "loading >500k tokens — only Grok's 2M window fits comfortably")

    if matches_any(prompt, FRONTEND_SIGNALS):
        return ("Gemini 3.1 Pro", "UI/frontend work benefits from multimodal + 1M context")

    if matches_any(prompt, BULK_SIGNALS):
        return ("GPT-5.1 Codex Mini", "bulk fan-out is cheap on Codex Mini ($0.25/$2 per 1M, 4× rate limit)")

    if matches_any(prompt, CHEAP_SIGNALS):
        # Very short prompts → Composer 2; longer routine work → GPT-5.3 Codex.
        if len(prompt) < 200:
            return ("Composer 2", "this looks like a small targeted edit/lookup — Composer 2 is ~10× cheaper")
        return ("GPT-5.3 Codex", "routine multi-step coding — Codex is ~30% the cost of Opus at the same quality")

    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print("{}")
            return 0
        payload = json.loads(raw)
    except Exception:
        print("{}")
        return 0

    prompt = (
        payload.get("prompt")
        or payload.get("user_message")
        or payload.get("text")
        or ""
    )
    if not isinstance(prompt, str) or not prompt.strip():
        print("{}")
        return 0

    # Skip the nudge if the user explicitly named a model in their prompt.
    if re.search(r"\b(opus|gpt-?5|codex|composer|gemini|grok|claude)\b", prompt, re.IGNORECASE):
        print("{}")
        return 0

    result = classify(prompt)
    if result is None:
        print("{}")
        return 0

    model, reason = result
    msg = (
        f"Model check: this prompt looks routine. Suggest **{model}** "
        f"({reason}). Continue here or switch?"
    )
    out = {"agent_message": msg}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
