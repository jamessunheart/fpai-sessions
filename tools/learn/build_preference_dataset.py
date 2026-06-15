#!/usr/bin/env python3
"""Build an advisory preference-pair dataset from existing repo signals.

Layer 1 is measurement only. This module reads local files, emits JSONL when
asked, and never trains a model or writes production state.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "tools" / "learn" / "runs" / "preference_pairs.jsonl"
DEFAULT_EVAL_PERCENT = 20

POSITIVE_OUTCOMES = {"good", "realized", "success", "passed", "better", "win", "done"}
NEGATIVE_OUTCOMES = {"meh", "regressed", "regression", "bad", "failed", "no", "worse"}
FEEDBACK_GLOBS = ("memory/feedback_*.md", "docs/**/feedback_*.md", "**/feedback_*.md")
JSON_GLOBS = ("**/brain_index*.json", "**/brain-index*.json", "**/*decision*.json", "**/*receipt*.json")
JSONL_GLOBS = ("**/brain_index*.jsonl", "**/brain-index*.jsonl", "**/*decision*.jsonl", "**/*receipt*.jsonl")
MARKDOWN_GLOBS = ("**/*DECISIONS*.md", "**/*decision*.md", "**/*RECEIPT*.md", "**/*receipt*.md")
SKIP_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__"}


@dataclasses.dataclass(frozen=True)
class PreferencePair:
    """A deterministic preferred/rejected training example."""

    pair_id: str
    source: str
    signal: str
    verdict: str
    prompt: str
    preferred: str
    rejected: str
    split: str
    never_train: bool
    metadata: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.pair_id,
            "source": self.source,
            "signal": self.signal,
            "verdict": self.verdict,
            "prompt": self.prompt,
            "preferred": {"text": self.preferred},
            "rejected": {"text": self.rejected},
            "split": self.split,
            "never_train": self.never_train,
            "eval": _eval_view(self.pair_id, self.preferred, self.rejected) if self.never_train else None,
            "metadata": self.metadata,
        }


def assemble_pairs(root: Path | str = REPO_ROOT, *, eval_percent: int = DEFAULT_EVAL_PERCENT) -> list[dict[str, Any]]:
    """Return deterministic preference pairs discovered under ``root``."""
    repo = Path(root)
    pairs: list[PreferencePair] = []
    pairs.extend(_pairs_from_json_sources(repo, eval_percent=eval_percent))
    pairs.extend(_pairs_from_feedback(repo, eval_percent=eval_percent))
    pairs.extend(_pairs_from_markdown_sources(repo, eval_percent=eval_percent))

    unique: dict[str, PreferencePair] = {}
    for pair in pairs:
        unique.setdefault(pair.pair_id, pair)
    return [pair.to_json() for pair in sorted(unique.values(), key=lambda item: item.pair_id)]


def write_jsonl(pairs: Iterable[dict[str, Any]], output: Path | str = DEFAULT_OUTPUT) -> Path:
    """Write pairs to JSONL and return the output path."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in pairs:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_no}") from exc
    return rows


def stable_split(pair_id: str, *, eval_percent: int = DEFAULT_EVAL_PERCENT) -> tuple[str, bool]:
    """Return a frozen train/eval split from a pair id hash."""
    if not 0 <= eval_percent <= 100:
        raise ValueError("eval_percent must be between 0 and 100")
    bucket = int(hashlib.sha256(pair_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    is_eval = bucket < eval_percent
    return ("eval" if is_eval else "train", is_eval)


def _pairs_from_json_sources(repo: Path, *, eval_percent: int) -> list[PreferencePair]:
    pairs: list[PreferencePair] = []
    for path in _glob_many(repo, JSON_GLOBS):
        data = _read_json(path)
        if data is None:
            continue
        for idx, item in enumerate(_decision_items(data)):
            pair = _pair_from_mapping(path, idx, item, eval_percent=eval_percent)
            if pair:
                pairs.append(pair)
    for path in _glob_many(repo, JSONL_GLOBS):
        for idx, item in enumerate(_read_jsonl(path)):
            pair = _pair_from_mapping(path, idx, item, eval_percent=eval_percent)
            if pair:
                pairs.append(pair)
    return pairs


def _pairs_from_feedback(repo: Path, *, eval_percent: int) -> list[PreferencePair]:
    pairs: list[PreferencePair] = []
    for path in _glob_many(repo, FEEDBACK_GLOBS):
        text = path.read_text(encoding="utf-8", errors="ignore")
        blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
        for idx, block in enumerate(blocks):
            preferred = _field(block, "preferred") or _field(block, "correction") or _field(block, "instead")
            rejected = _field(block, "rejected") or _field(block, "original") or _field(block, "mistake")
            prompt = _field(block, "prompt") or _field(block, "context") or path.stem
            if preferred and rejected:
                pairs.append(
                    _make_pair(
                        source=path,
                        signal="feedback",
                        verdict="correction",
                        prompt=prompt,
                        preferred=preferred,
                        rejected=rejected,
                        eval_percent=eval_percent,
                        metadata={"block": idx},
                    )
                )
    return pairs


def _pairs_from_markdown_sources(repo: Path, *, eval_percent: int) -> list[PreferencePair]:
    pairs: list[PreferencePair] = []
    for path in _glob_many(repo, MARKDOWN_GLOBS):
        text = path.read_text(encoding="utf-8", errors="ignore")
        blocks = [block.strip() for block in re.split(r"\n(?=###? |\|)", text) if block.strip()]
        for idx, block in enumerate(blocks):
            preferred = _field(block, "preferred") or _field(block, "receipt") or _field(block, "proof")
            rejected = _field(block, "rejected") or _field(block, "decision") or _field(block, "claim")
            verdict = (_field(block, "verdict") or _field(block, "outcome") or "").lower()
            if preferred and rejected and (not verdict or verdict in POSITIVE_OUTCOMES | NEGATIVE_OUTCOMES):
                pairs.append(
                    _make_pair(
                        source=path,
                        signal="decision_receipt",
                        verdict=verdict or "receipt",
                        prompt=_field(block, "prompt") or _heading(block) or path.stem,
                        preferred=preferred,
                        rejected=rejected,
                        eval_percent=eval_percent,
                        metadata={"block": idx},
                    )
                )
    return pairs


def _pair_from_mapping(path: Path, idx: int, item: dict[str, Any], *, eval_percent: int) -> PreferencePair | None:
    outcome = str(_first(item, "outcome", "verdict", "merge_outcome", "result", "status") or "").strip().lower()
    if outcome and outcome not in POSITIVE_OUTCOMES | NEGATIVE_OUTCOMES:
        return None

    prompt = str(_first(item, "prompt", "question", "intent", "context", "id") or path.stem).strip()
    preferred = _first(item, "preferred", "accepted", "receipt", "proof", "better", "correction")
    rejected = _first(item, "rejected", "reverted", "regressed", "bad", "claim", "original")

    if not preferred and outcome in POSITIVE_OUTCOMES:
        preferred = _first(item, "decision", "summary", "answer", "action")
    if not rejected and outcome in POSITIVE_OUTCOMES:
        rejected = _first(item, "alternative", "before", "previous", "risk")
    if not preferred and outcome in NEGATIVE_OUTCOMES:
        preferred = _first(item, "correction", "receipt", "lesson", "desired", "fix")
    if not rejected and outcome in NEGATIVE_OUTCOMES:
        rejected = _first(item, "decision", "summary", "answer", "action")

    if not preferred or not rejected:
        return None

    return _make_pair(
        source=path,
        signal="merge_outcome" if "brain" in path.name.lower() else "decision_receipt",
        verdict=outcome or "explicit_pair",
        prompt=prompt,
        preferred=str(preferred),
        rejected=str(rejected),
        eval_percent=eval_percent,
        metadata={"index": idx},
    )


def _make_pair(
    *,
    source: Path,
    signal: str,
    verdict: str,
    prompt: str,
    preferred: str,
    rejected: str,
    eval_percent: int,
    metadata: dict[str, Any],
) -> PreferencePair:
    clean_preferred = _clean(preferred)
    clean_rejected = _clean(rejected)
    clean_prompt = _clean(prompt)
    pair_id = _pair_id(str(source), signal, verdict, clean_prompt, clean_preferred, clean_rejected)
    split, never_train = stable_split(pair_id, eval_percent=eval_percent)
    return PreferencePair(
        pair_id=pair_id,
        source=str(source),
        signal=signal,
        verdict=verdict,
        prompt=clean_prompt,
        preferred=clean_preferred,
        rejected=clean_rejected,
        split=split,
        never_train=never_train,
        metadata=metadata,
    )


def _eval_view(pair_id: str, preferred: str, rejected: str) -> dict[str, str]:
    preferred_is_a = int(hashlib.sha256((pair_id + ":order").encode("utf-8")).hexdigest()[:2], 16) % 2 == 0
    if preferred_is_a:
        return {"A": preferred, "B": rejected, "label": "A"}
    return {"A": rejected, "B": preferred, "label": "B"}


def _pair_id(*parts: str) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"pref-{digest[:16]}"


def _decision_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("decisions", "brain_index.decisions", "items", "rows", "receipts"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return [data]


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _glob_many(root: Path, patterns: Iterable[str]) -> list[Path]:
    paths: dict[str, Path] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() and not _skip_path(path):
                paths[str(path)] = path
    return [paths[key] for key in sorted(paths)]


def _skip_path(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def _field(text: str, label: str) -> str:
    pattern = re.compile(rf"^\s*(?:[-*]\s*)?(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*:\s*(?P<value>.+)$", re.I | re.M)
    match = pattern.search(text)
    return _clean(match.group("value")) if match else ""


def _heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("#"):
            return _clean(line.lstrip("# "))
    return ""


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an advisory preference-pair JSONL dataset.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repository/data root to scan")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="JSONL output path")
    parser.add_argument("--eval-percent", type=int, default=DEFAULT_EVAL_PERCENT, help="Frozen held-out percentage")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing JSONL")
    args = parser.parse_args(argv)

    pairs = assemble_pairs(args.root, eval_percent=args.eval_percent)
    eval_count = sum(1 for row in pairs if row["never_train"])
    if not args.dry_run:
        write_jsonl(pairs, args.output)
    print(json.dumps({"pairs": len(pairs), "eval": eval_count, "output": str(args.output), "dry_run": args.dry_run}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

