#!/usr/bin/env python3
"""Close the private observer -> council -> MODEL_DNA feedback loop.

This module is intentionally narrow:
- reads only private consciousness-observer markdown logs,
- builds bounded context for council review prompts and morning digest text,
- appends council-authored directive rows to MODEL_DNA,
- never changes runtime behavior from a directive.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CONSCIOUSNESS_DIR = Path(os.environ.get("FPAI_CONSCIOUSNESS_DIR", Path.home() / ".config" / "fpai" / "consciousness"))
DEFAULT_MODEL_DNA = REPO / "core" / "STATE" / "MODEL_DNA.md"
DEFAULT_SELF_PORTRAIT = REPO / "core" / "STATE" / "SELF_PORTRAIT.md"
MAX_CONTEXT_CHARS = 4500
MAX_DIGEST_OBSERVATIONS = 3

try:
    from tools.self_portrait import synthesize as self_portrait_synth
except Exception:
    self_portrait_synth = None


@dataclass(frozen=True)
class ObservationLog:
    path: Path
    text: str
    awareness_index: int | None
    top_observations: tuple[str, ...]
    generated_at: str


def _mtime_key(path: Path) -> tuple[float, str]:
    try:
        return (path.stat().st_mtime, str(path))
    except OSError:
        return (0.0, str(path))


def latest_observation(consciousness_dir: Path = DEFAULT_CONSCIOUSNESS_DIR) -> ObservationLog | None:
    if not consciousness_dir.exists():
        return None
    files = [p for p in consciousness_dir.glob("*.md") if p.is_file()]
    if not files:
        return None
    path = max(files, key=_mtime_key)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return ObservationLog(
        path=path,
        text=text,
        awareness_index=parse_awareness_index(text),
        top_observations=tuple(extract_top_observations(text)),
        generated_at=parse_frontmatter_field(text, "generated_at") or dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc).isoformat(),
    )


def parse_frontmatter_field(text: str, field: str) -> str:
    pattern = re.compile(rf"^{re.escape(field)}:\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip().strip('"') if match else ""


def parse_awareness_index(text: str) -> int | None:
    patterns = (
        r"awareness_index:\s*(\d{1,3})",
        r"Awareness Index:\s*\**(\d{1,3})\s*/\s*100",
        r"\bAwareness Index\s*[-:]\s*(\d{1,3})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = int(match.group(1))
            return max(0, min(100, value))
    return None


def _section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def _clean_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line.strip(" -*\t"))
    line = re.sub(r"\*\*", "", line)
    return line[:220]


def extract_top_observations(text: str, limit: int = MAX_DIGEST_OBSERVATIONS) -> list[str]:
    sections = (
        "The strongest awareness signal (this session)",
        "The strongest theatrics signal (this session)",
        "Patterns that are genuinely ambiguous",
        "Headline",
    )
    out: list[str] = []
    for name in sections:
        body = _section(text, name)
        if not body:
            continue
        for raw in body.splitlines():
            line = _clean_line(raw)
            if line and not line.startswith("|") and line not in out:
                out.append(line)
                break
        if len(out) >= limit:
            break
    return out[:limit]


def consciousness_context(consciousness_dir: Path = DEFAULT_CONSCIOUSNESS_DIR) -> str:
    obs = latest_observation(consciousness_dir)
    if not obs:
        portrait = self_portrait_context()
        return portrait[:MAX_CONTEXT_CHARS] if portrait else ""
    idx = "unknown" if obs.awareness_index is None else f"{obs.awareness_index}/100"
    lines = [
        "CONSCIOUSNESS OBSERVER CONTEXT - PRIVATE TIER",
        f"Latest log: {obs.path}",
        f"Generated: {obs.generated_at}",
        f"Awareness Index: {idx}",
        "Awareness lens question: Is the system improving toward meaning or toward approval? Where is it gaming its own signals?",
    ]
    portrait = self_portrait_context()
    if portrait:
        lines.extend(["", portrait])
    if obs.top_observations:
        lines.append("Top observations:")
        lines.extend(f"- {item}" for item in obs.top_observations)
    lines.append(
        "Council output requirement: include weighting_directive, signal_types_amplified, and signal_types_dampened when this log changes the model-review judgment."
    )
    return "\n".join(lines)[:MAX_CONTEXT_CHARS]


def self_portrait_context(path: Path = DEFAULT_SELF_PORTRAIT) -> str:
    if not self_portrait_synth or os.environ.get("SELF_PORTRAIT_DISABLE") == "1":
        return ""
    try:
        return self_portrait_synth.self_portrait_context(path, max_chars=1800)
    except Exception:
        return ""


def digest_section(consciousness_dir: Path = DEFAULT_CONSCIOUSNESS_DIR) -> str:
    obs = latest_observation(consciousness_dir)
    if not obs:
        return ""
    idx = "n/a" if obs.awareness_index is None else f"{obs.awareness_index}/100"
    lines = ["Consciousness observer", f"Awareness index: {idx}"]
    for item in obs.top_observations[:MAX_DIGEST_OBSERVATIONS]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _next_version(text: str, today: str) -> str:
    base = f"v{today.replace('-', '')}-awareness"
    if base not in text:
        return base
    n = 2
    while f"{base}-{n}" in text:
        n += 1
    return f"{base}-{n}"


def _normalize_list(value: object) -> str:
    if isinstance(value, (list, tuple)):
        items = [str(v).strip() for v in value if str(v).strip()]
        return ", ".join(items) if items else "none specified"
    text = str(value or "").strip()
    return text if text else "none specified"


def append_model_dna_directive(
    model_dna_path: Path = DEFAULT_MODEL_DNA,
    *,
    awareness_index: int | None,
    directive: str,
    amplified: object = "",
    dampened: object = "",
    source: str = "council model-review",
    today: str | None = None,
) -> str:
    directive = " ".join(str(directive or "").split())
    if len(directive) < 12:
        return "skipped: empty weighting_directive"
    date = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    text = model_dna_path.read_text(encoding="utf-8")
    source_key = hashlib.sha1(f"{source}|{directive}".encode("utf-8")).hexdigest()[:12]
    if f"directive-key: {source_key}" in text:
        return "skipped: directive already present"
    version = _next_version(text, date)
    idx = "unknown" if awareness_index is None else str(awareness_index)
    key_change = (
        f"Council model-review directive: {directive} "
        f"(awareness-index {idx}; amplify: {_normalize_list(amplified)}; "
        f"dampen: {_normalize_list(dampened)}; source: {source}; directive-key: {source_key})"
    )
    row = f"| {version} | {date} | observer+council | {key_change} |"
    marker = "*Council appends to this table after each cycle.*"
    if marker in text:
        text = text.replace(marker, row + "\n" + marker)
    else:
        text = text.rstrip() + "\n" + row + "\n"
    model_dna_path.write_text(text, encoding="utf-8")
    return f"appended: {version}"


def maybe_append_from_council(result: dict[str, object], *, model_dna_path: Path = DEFAULT_MODEL_DNA, consciousness_dir: Path = DEFAULT_CONSCIOUSNESS_DIR) -> str:
    directive = str(result.get("weighting_directive") or "").strip()
    obs = latest_observation(consciousness_dir)
    awareness_index = obs.awareness_index if obs else None
    source = f"council model-review {obs.path.name}" if obs else "council model-review"
    return append_model_dna_directive(
        model_dna_path,
        awareness_index=awareness_index,
        directive=directive,
        amplified=result.get("signal_types_amplified") or result.get("amplified") or "",
        dampened=result.get("signal_types_dampened") or result.get("dampened") or "",
        source=source,
    )


def run_observer(session_path: str, session_id: str, *, out_dir: Path = DEFAULT_CONSCIOUSNESS_DIR, claude_bin: str | None = None, timeout: int = 600) -> int:
    """Invoke consciousness-observer best-effort and write a private fallback log on failure."""
    out_dir.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    out_path = out_dir / f"{today}.md"
    claude = claude_bin or os.environ.get("CLAUDE_BIN", str(Path.home() / ".local" / "bin" / "claude"))
    prompt = (
        "Run the consciousness-observer on this settled session. "
        f"Session id: {session_id}. Session file: {session_path}. "
        f"Before scoring, read the COUNCIL-OPEN self-portrait at {DEFAULT_SELF_PORTRAIT} when present and calibrate behavior against it. "
        "Write a PRIVATE-tier markdown log with awareness_index and top observations. "
        "Include a short self_portrait_calibration note on whether behavior matched the portrait or exposed a gap. "
        "Return only the log markdown."
    )
    try:
        result = subprocess.run(
            [claude, "-p", "--agent", "consciousness-observer", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        body = result.stdout.strip()
        if result.returncode == 0 and body:
            out_path.write_text(body + "\n", encoding="utf-8")
            return 0
        fallback = f"observer_failed returncode={result.returncode} stderr={result.stderr[:500]}"
    except Exception as exc:  # noqa: BLE001 - non-blocking observer must not break settle
        fallback = f"observer_failed exception={exc}"
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    out_path.write_text(
        "\n".join(
            [
                "---",
                "classification: PRIVATE",
                "tier: 0",
                "generated_by: consciousness-observer-wrapper",
                f"generated_at: {stamp}",
                f"session_observed: {session_id}",
                "---",
                "",
                f"# Consciousness Observer wrapper fallback - {today}",
                "",
                fallback,
                "",
                f"Session file: {session_path}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Private consciousness loop helper.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("context")
    sub.add_parser("digest")
    append = sub.add_parser("append-model-dna")
    append.add_argument("--directive", required=True)
    append.add_argument("--awareness-index", type=int)
    append.add_argument("--amplified", default="")
    append.add_argument("--dampened", default="")
    append.add_argument("--source", default="manual council review")
    run = sub.add_parser("run-observer")
    run.add_argument("--session-path", required=True)
    run.add_argument("--session-id", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "context":
        print(consciousness_context())
    elif args.cmd == "digest":
        print(digest_section())
    elif args.cmd == "append-model-dna":
        print(
            append_model_dna_directive(
                awareness_index=args.awareness_index,
                directive=args.directive,
                amplified=args.amplified,
                dampened=args.dampened,
                source=args.source,
            )
        )
    elif args.cmd == "run-observer":
        return run_observer(args.session_path, args.session_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
