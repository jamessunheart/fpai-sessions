#!/usr/bin/env python3
"""Enforce the FPOS public/private data boundary.

The boundary is intentionally conservative. Mixed public/private conversations
are split: public-safe fragments may continue to public surfaces, while private
or sensitive context stays in the private lane.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "core" / "STATE" / "PUBLIC_PRIVATE_DATA_BOUNDARY.json"

LANE_RANK = {"public": 0, "internal": 1, "private": 2, "sensitive": 3}
BLOCKING_LANES = {"internal", "private", "sensitive"}
URL_RE = re.compile(r"https?://[^\s<>()]+")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")
LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_/-]{28,}\b")


@dataclass(frozen=True)
class BoundaryVerdict:
    lane: str
    categories: tuple[str, ...]
    reasons: tuple[str, ...]
    public_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "categories": list(self.categories),
            "reasons": list(self.reasons),
            "public_allowed": self.public_allowed,
        }


def load_policy(path: Path | str = POLICY_PATH) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid public/private boundary policy: {path}") from exc


def classify_text(text: Any, *, policy: dict[str, Any] | None = None) -> BoundaryVerdict:
    """Classify text into the highest-risk lane it matches."""
    policy = policy or load_policy()
    value = " ".join(str(text or "").split())
    if not value:
        return BoundaryVerdict("public", (), (), True)

    matched: list[tuple[str, str, str]] = []
    for category in policy.get("categories", []):
        lane = str(category.get("lane") or policy.get("default_lane") or "private")
        for pattern in category.get("patterns", []):
            if re.search(pattern, value, re.IGNORECASE):
                matched.append((lane, str(category.get("id") or "unknown"), pattern))
                break

    if not matched:
        lane = str(policy.get("default_lane") or "private")
    else:
        lane = max((item[0] for item in matched), key=lambda item: LANE_RANK.get(item, 2))
    categories = tuple(dict.fromkeys(item[1] for item in matched))
    reasons = tuple(f"{category}:{matched_lane}" for matched_lane, category, _pattern in matched)
    return BoundaryVerdict(lane, categories, reasons, lane == "public")


def sanitize_public_text(text: Any, *, policy: dict[str, Any] | None = None, escape: bool = True) -> str | None:
    """Return a public-safe fragment, or None when the fragment belongs private."""
    policy = policy or load_policy()
    clean = " ".join(str(text or "").split())
    if not clean:
        return None

    verdict = classify_text(clean, policy=policy)
    if verdict.lane == "sensitive":
        return None
    if "correction_or_private_memory" in verdict.categories:
        return None
    if any(category in verdict.categories for category in ("personal_state_or_location", "relationship_or_people", "legal_strategy")):
        return None

    clean = _generalize_internal_ids(clean)
    clean = _redact(clean)
    clean = clean[:240].strip()
    if not clean:
        return None

    post_verdict = classify_text(clean, policy=policy)
    if post_verdict.lane in {"private", "sensitive"}:
        return None
    if post_verdict.lane == "internal":
        clean = _generalize_internal_ids(clean)
        if classify_text(clean, policy=policy).lane != "public":
            return None
    return html.escape(clean, quote=True) if escape else clean


def validate_public_text(text: str, *, policy: dict[str, Any] | None = None) -> None:
    """Raise when text still contains non-public material."""
    verdict = classify_text(text, policy=policy)
    if verdict.lane != "public":
        categories = ", ".join(verdict.categories) or verdict.lane
        raise ValueError(f"public text failed boundary policy: {categories}")


def enforce_public_text(text: Any, *, policy: dict[str, Any] | None = None, escape: bool = True) -> str:
    """Sanitize and validate one public-bound string."""
    public = sanitize_public_text(text, policy=policy, escape=escape)
    if public is None:
        raise ValueError("public text belongs to private/sensitive lane")
    validate_public_text(public, policy=policy)
    return public


def route_conversation(messages: str | Iterable[Any], *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route mixed conversation fragments into public and private lanes."""
    policy = policy or load_policy()
    fragments = _fragments(messages)
    public_fragments: list[str] = []
    private_fragments: list[dict[str, Any]] = []

    for fragment in fragments:
        verdict = classify_text(fragment, policy=policy)
        public = sanitize_public_text(fragment, policy=policy, escape=False)
        if public and classify_text(public, policy=policy).lane == "public":
            public_fragments.append(public)
        if verdict.lane in BLOCKING_LANES or public is None:
            private_fragments.append({"text": fragment, "verdict": verdict.as_dict()})

    if public_fragments and private_fragments:
        route = "split"
    elif public_fragments:
        route = "public"
    else:
        route = "private"

    public_text = "\n".join(public_fragments).strip()
    if public_text:
        validate_public_text(public_text, policy=policy)
    return {
        "route": route,
        "public_text": public_text,
        "private_fragments": private_fragments,
        "public_allowed": bool(public_text),
        "private_count": len(private_fragments),
        "public_count": len(public_fragments),
    }


def _fragments(messages: str | Iterable[Any]) -> list[str]:
    if isinstance(messages, str):
        raw = messages.splitlines()
    else:
        raw = []
        for item in messages:
            if isinstance(item, dict):
                raw.append(str(item.get("content") or item.get("text") or ""))
            else:
                raw.append(str(item or ""))
    return [line.strip(" -\t") for line in raw if line and line.strip(" -\t")]


def _redact(text: str) -> str:
    text = URL_RE.sub("[private link]", text)
    text = EMAIL_RE.sub("[private contact]", text)
    text = re.sub(r"[$€£]\s?\d[\d,]*(?:\.\d+)?", "[private figure]", text)
    text = re.sub(r"\b\d[\d,]*(?:\.\d+)?\s?(?:usd|usdc|eur|gbp|sol|btc|eth)\b", "[private figure]", text, flags=re.I)
    text = re.sub(r"\b(?:0x[a-fA-F0-9]{24,}|[1-9A-HJ-NP-Za-km-z]{32,44})\b", "[private address]", text)
    text = re.sub(r"\b(?:treasury|runway|wallet|bank account|trading position|liquidation|invoice|payment routing)\b", "private resource detail", text, flags=re.I)
    text = LONG_TOKEN_RE.sub("[private token]", text)
    return text


def _generalize_internal_ids(text: str) -> str:
    text = re.sub(r"\b(?:d\d{2,}|decision[_ -]?id)\b", "the routed decision", text, flags=re.I)
    text = re.sub(r"\bSPEC_d\d+[A-Za-z0-9_-]*\b", "the routed build", text)
    text = re.sub(r"\b(?:build/SPEC_[A-Za-z0-9_-]+|codex/[A-Za-z0-9_-]+)\b", "the build branch", text)
    text = re.sub(r"\b(?:core/BUILD|docs/codex|SERVICES/|tools/)[^\s]*", "the internal build artifact", text)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify or route public/private boundary text.")
    parser.add_argument("text", nargs="?", default="", help="Text to classify or route")
    parser.add_argument("--route", action="store_true", help="Split text into public/private lanes")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args(argv)

    result: dict[str, Any]
    if args.route:
        result = route_conversation(args.text)
    else:
        result = classify_text(args.text).as_dict()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
