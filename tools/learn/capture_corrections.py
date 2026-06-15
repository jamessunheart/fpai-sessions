#!/usr/bin/env python3
"""Append James correction pairs to the advisory preference dataset.

This is capture only. It does not train, score, route, deploy, or grant new
authority. The JSONL shape matches the d010 preference-pair dataset so explicit
corrections can feed the later measurement/training path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO_ROOT / "tools" / "learn" / "runs" / "preference_pairs.jsonl"


def correction_id(*, rejected: str, preferred: str, prompt: str, source: str) -> str:
    digest = hashlib.sha256(
        "\n".join([source.strip(), prompt.strip(), rejected.strip(), preferred.strip()]).encode("utf-8")
    ).hexdigest()
    return f"corr-{digest[:16]}"


def make_correction_pair(
    *,
    rejected: str,
    preferred: str,
    prompt: str = "",
    source: str = "james-correction",
    metadata: dict[str, Any] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Return one d010-compatible preference pair from an explicit correction."""
    clean_rejected = _clean_required(rejected, "rejected")
    clean_preferred = _clean_required(preferred, "preferred")
    clean_prompt = _clean(prompt) or "James corrected the bot response."
    clean_source = _clean(source) or "james-correction"
    stamp = captured_at or datetime.now(timezone.utc).isoformat()
    row_id = correction_id(
        rejected=clean_rejected,
        preferred=clean_preferred,
        prompt=clean_prompt,
        source=clean_source,
    )
    return {
        "id": row_id,
        "source": clean_source,
        "signal": "james_correction",
        "verdict": "correction",
        "prompt": clean_prompt,
        "preferred": {"text": clean_preferred},
        "rejected": {"text": clean_rejected},
        "split": "train",
        "never_train": False,
        "eval": None,
        "metadata": {
            "captured_at": stamp,
            "capture_tool": "tools/learn/capture_corrections.py",
            **(metadata or {}),
        },
    }


def append_pair(row: dict[str, Any], dataset: Path | str = DEFAULT_DATASET, *, dedupe: bool = True) -> bool:
    """Append ``row`` to ``dataset``. Return False when dedupe skipped it."""
    path = Path(dataset)
    if dedupe and path.exists() and row.get("id") in _existing_ids(path):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return True


def _existing_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("id"):
                ids.add(str(item["id"]))
    return ids


def _clean_required(value: str, field: str) -> str:
    cleaned = _clean(value)
    if not cleaned:
        raise ValueError(f"{field} is required")
    return cleaned


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append one James correction pair to preference JSONL.")
    parser.add_argument("--rejected", required=True, help="Bot response or behavior James rejected")
    parser.add_argument("--preferred", required=True, help="James's correction or preferred response")
    parser.add_argument("--prompt", default="", help="Original prompt/context for the correction")
    parser.add_argument("--source", default="james-correction", help="Correction source label")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET, help="JSONL dataset path")
    parser.add_argument("--metadata", default="{}", help="Optional JSON metadata object")
    parser.add_argument("--allow-duplicate", action="store_true", help="Append even if this correction id exists")
    parser.add_argument("--dry-run", action="store_true", help="Print the row without writing")
    args = parser.parse_args(argv)

    try:
        metadata = json.loads(args.metadata)
    except json.JSONDecodeError as exc:
        print(f"invalid --metadata JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(metadata, dict):
        print("--metadata must be a JSON object", file=sys.stderr)
        return 2

    row = make_correction_pair(
        rejected=args.rejected,
        preferred=args.preferred,
        prompt=args.prompt,
        source=args.source,
        metadata=metadata,
    )
    wrote = False if args.dry_run else append_pair(row, args.dataset, dedupe=not args.allow_duplicate)
    print(json.dumps({"id": row["id"], "dataset": str(args.dataset), "dry_run": args.dry_run, "wrote": wrote}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

