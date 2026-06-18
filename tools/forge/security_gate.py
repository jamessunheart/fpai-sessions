#!/usr/bin/env python3
"""Sanitize frontier artifacts before they are allowed onto public surfaces."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.public_private_boundary.boundary import classify_text, sanitize_public_text

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)")
SECRET_RE = re.compile(r"\b(?:api[_-]?key|secret|token|password|credential|bearer)\b", re.I)
PRIVATE_PATH_RE = re.compile(
    r"\b(?:identity/|brain_index\.|core/STATE/PERSONAL_DNA\.md|treasury|wallet|probe_pool|probe_sessions|corrections|thread)\b",
    re.I,
)


@dataclass(frozen=True)
class GateResult:
    sanitized: str
    warnings: tuple[str, ...]
    blocked: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "sanitized": self.sanitized,
            "warnings": list(self.warnings),
            "blocked": self.blocked,
        }


def sanitize_markdown(text: str) -> GateResult:
    """Return public-safe markdown plus warnings for stripped private fragments."""
    warnings: list[str] = []
    public_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            public_lines.append("")
            continue

        reasons = _pattern_reasons(line)
        verdict = classify_text(line)
        explicit_private = bool(verdict.categories)
        if reasons or explicit_private:
            warnings.extend(reasons or [f"boundary:{verdict.lane}"])
            replacement = _redacted_line(line)
            if replacement:
                public_lines.append(replacement)
            continue
        public_lines.append(line)

    sanitized = _compact_blank_lines("\n".join(public_lines).strip() + "\n")
    post_reasons = _pattern_reasons(sanitized)
    post_verdict = classify_text(sanitized)
    blocked = bool(post_reasons) or bool(post_verdict.categories)
    warnings.extend(post_reasons)
    if post_verdict.categories:
        warnings.append(f"post_boundary:{post_verdict.lane}")
    return GateResult(sanitized=sanitized, warnings=tuple(dict.fromkeys(warnings)), blocked=blocked)


def assert_public(text: str) -> GateResult:
    result = sanitize_markdown(text)
    if result.blocked:
        raise ValueError("frontier artifact failed public security gate: " + ", ".join(result.warnings))
    return result


def _pattern_reasons(text: str) -> list[str]:
    reasons: list[str] = []
    if EMAIL_RE.search(text):
        reasons.append("email")
    if _contains_phone(text):
        reasons.append("phone")
    if SECRET_RE.search(text):
        reasons.append("secret-shaped")
    if PRIVATE_PATH_RE.search(text):
        reasons.append("private-layer")
    return reasons


def _contains_phone(text: str) -> bool:
    for match in PHONE_RE.finditer(text):
        value = match.group(0)
        digits = re.sub(r"\D", "", value)
        if len(digits) < 9:
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            continue
        return True
    return False


def _redacted_line(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("#"):
        return line
    if stripped.startswith(("- ", "* ")):
        return "- [redacted private/internal detail]"
    return None


def _compact_blank_lines(text: str) -> str:
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sanitize a markdown artifact for public release.")
    parser.add_argument("path", type=Path, help="Markdown file to sanitize")
    parser.add_argument("--out", type=Path, help="Where to write sanitized markdown")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args(argv)

    result = sanitize_markdown(args.path.read_text(encoding="utf-8", errors="replace"))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result.sanitized, encoding="utf-8")
    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    else:
        print(result.sanitized, end="")
        if result.warnings:
            print(f"\nsecurity_gate warnings: {', '.join(result.warnings)}")
    return 1 if result.blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
