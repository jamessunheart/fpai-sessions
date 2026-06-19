"""Lightweight context router for chat synthesis.

The classifier is intentionally deterministic and local-only. Ambiguous input
falls back to ``general`` so the caller preserves the full existing context.
"""
from __future__ import annotations

import re
from typing import Literal

ContextRoute = Literal["ops", "treasury", "memory", "general"]
ContextBlock = Literal["system_state", "buildstream", "corrections", "becoming", "brain_search"]
ALL_CONTEXT_BLOCKS: tuple[ContextBlock, ...] = (
    "system_state",
    "buildstream",
    "corrections",
    "becoming",
    "brain_search",
)

_ROUTE_PATTERNS: dict[ContextRoute, tuple[str, ...]] = {
    "ops": (
        r"\bops\b",
        r"\bstatus\b",
        r"\bsystem\s+state\b",
        r"\bbuildstream\b",
        r"\bbuild\s+(queue|status|loop|registry|branch|proof|tests?)\b",
        r"\b(pending|active|running|failing|failed)\s+(builds?|specs?|services?|jobs?)\b",
        r"\b(server|service|systemd|liveness|deploy|merge|branch|registry|handoff)\b",
    ),
    "treasury": (
        r"\btreasury\b",
        r"\b(money|cash|runway|wallet|balance|budget|spend|costs?)\b",
        r"\b(finance|financial|accounting|ledger|funds?|capital)\b",
        r"\b(trading|portfolio|position|yield|token|tokens|tokenomics|solana|usdc|crypto)\b",
    ),
    "memory": (
        r"\b(memory|remember|recall|remembered|forgot|forget)\b",
        r"\b(brain|notes?|vault|obsidian|corrections?|becoming)\b",
        r"\bwhat\s+did\s+(i|you|we)\s+(say|decide|learn)\b",
        r"\bwhen\s+did\s+(i|you|we)\b",
        r"\bwho\s+is\b",
    ),
    "general": (),
}


def classify_question(text: str) -> ContextRoute:
    """Classify an incoming chat question for context routing.

    Keyword scoring keeps the hot path fast and avoids API calls. Ties and
    no-match cases route to ``general`` because that is the safest legacy path:
    all context blocks plus brain search.
    """
    normalized = " ".join((text or "").lower().split())
    if not normalized:
        return "general"

    scores: dict[ContextRoute, int] = {"ops": 0, "treasury": 0, "memory": 0, "general": 0}
    for route, patterns in _ROUTE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                scores[route] += 1

    best_route = max(("ops", "treasury", "memory"), key=lambda route: scores[route])
    best_score = scores[best_route]
    if best_score == 0:
        return "general"
    if sum(1 for route in ("ops", "treasury", "memory") if scores[route] == best_score) > 1:
        return "general"
    return best_route


def context_blocks_for_route(route: ContextRoute | str) -> tuple[ContextBlock, ...]:
    """Return context blocks to inject for a classified route."""
    if route == "ops":
        return ("system_state", "buildstream")
    if route == "treasury":
        return ("system_state", "corrections")
    return ALL_CONTEXT_BLOCKS
