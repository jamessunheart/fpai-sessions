#!/usr/bin/env python3
"""Detect correction-memory loops that did not close.

The retention smoke proves one synthetic correction can be written and injected.
This probe checks the real correction ledger for recurrence: the same
bot-response -> James-correction pair appearing more than once. That is evidence
that the bot saw the correction path but repeated the failure anyway.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any


DEFAULT_CURATOR_PARENT = Path(os.environ.get("FPAI_CURATOR_PARENT", "/opt/sh-brain-src"))
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_LIMIT = int(os.environ.get("CORRECTION_LOOP_CLOSURE_LIMIT", "80"))
DEFAULT_THRESHOLD = int(os.environ.get("CORRECTION_LOOP_CLOSURE_THRESHOLD", "2"))
DEFAULT_COOLDOWN_HOURS = float(os.environ.get("CORRECTION_LOOP_CLOSURE_COOLDOWN_HOURS", "24"))
_SPACE = re.compile(r"\s+")


class ProbeUnavailable(RuntimeError):
    """Raised when the probe cannot read correction memory."""


@dataclass(frozen=True)
class CorrectionRow:
    row_id: str
    conversation_id: str
    bot_turn_id: str
    original_response: str
    james_correction: str
    captured_at: str


@dataclass(frozen=True)
class Recurrence:
    fingerprint: str
    count: int
    conversation_id: str
    first_seen: str
    latest_seen: str
    sample_original: str
    sample_correction: str


def load_curator_package(curator_parent: Path) -> ModuleType:
    package_dir = curator_parent / "curator"
    init_file = package_dir / "__init__.py"
    if not init_file.exists():
        raise ProbeUnavailable(f"curator package not found at {package_dir}")
    existing = sys.modules.get("curator")
    if existing is not None:
        existing_file = Path(str(getattr(existing, "__file__", "") or "")).resolve()
        try:
            if existing_file.is_relative_to(package_dir.resolve()):
                return existing
        except ValueError:
            pass
        for name in list(sys.modules):
            if name == "curator" or name.startswith("curator."):
                sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        "curator",
        init_file,
        submodule_search_locations=[str(package_dir)],
    )
    if not spec or not spec.loader:
        raise ProbeUnavailable(f"could not load curator package spec from {init_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["curator"] = module
    spec.loader.exec_module(module)
    return module


async def read_recent_corrections(
    *,
    curator_parent: Path = DEFAULT_CURATOR_PARENT,
    limit: int = DEFAULT_LIMIT,
    conversation_id: str | None = None,
) -> list[CorrectionRow]:
    load_curator_package(curator_parent)
    try:
        db = importlib.import_module("curator.db")
    except Exception as exc:
        raise ProbeUnavailable(f"curator.db import failed: {exc}") from exc

    clauses: list[str] = []
    params: list[Any] = []
    if conversation_id:
        clauses.append("conversation_id = %s")
        params.append(str(conversation_id))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(max(1, int(limit)))
    try:
        async with db.connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    SELECT id::text, conversation_id, COALESCE(bot_turn_id::text, ''),
                           original_response, james_correction, captured_at::text
                      FROM brain_index.corrections
                      {where}
                     ORDER BY captured_at DESC
                     LIMIT %s
                    """,
                    params,
                )
                rows = await cur.fetchall()
    except Exception as exc:
        raise ProbeUnavailable(f"corrections query failed: {exc}") from exc

    return [
        CorrectionRow(
            row_id=str(row[0] or ""),
            conversation_id=str(row[1] or ""),
            bot_turn_id=str(row[2] or ""),
            original_response=str(row[3] or ""),
            james_correction=str(row[4] or ""),
            captured_at=str(row[5] or ""),
        )
        for row in rows
    ]


def normalize_text(text: str) -> str:
    return _SPACE.sub(" ", (text or "").strip().casefold())


def correction_fingerprint(row: CorrectionRow) -> str:
    payload = "\n".join(
        [
            normalize_text(row.conversation_id),
            normalize_text(row.original_response),
            normalize_text(row.james_correction),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def find_recurrences(
    rows: list[CorrectionRow],
    *,
    threshold: int = DEFAULT_THRESHOLD,
) -> list[Recurrence]:
    grouped: dict[str, list[CorrectionRow]] = {}
    for row in rows:
        if not normalize_text(row.original_response) or not normalize_text(row.james_correction):
            continue
        grouped.setdefault(correction_fingerprint(row), []).append(row)

    recurrences: list[Recurrence] = []
    for fingerprint, items in grouped.items():
        if len(items) < threshold:
            continue
        ordered = sorted(items, key=lambda item: item.captured_at or "")
        latest = ordered[-1]
        recurrences.append(
            Recurrence(
                fingerprint=fingerprint,
                count=len(items),
                conversation_id=latest.conversation_id,
                first_seen=ordered[0].captured_at,
                latest_seen=latest.captured_at,
                sample_original=latest.original_response,
                sample_correction=latest.james_correction,
            )
        )
    return sorted(recurrences, key=lambda item: (item.count, item.latest_seen), reverse=True)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _parse_utc(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def alert_recently_sent(
    *,
    ops_ledger: Path,
    fingerprint: str,
    now: datetime,
    cooldown_hours: float = DEFAULT_COOLDOWN_HOURS,
) -> bool:
    cutoff = now - timedelta(hours=max(0.0, cooldown_hours))
    for row in reversed(read_jsonl(ops_ledger)):
        if row.get("loop") != "correction-loop":
            continue
        if row.get("event") != "correction-loop:fail":
            continue
        if str(row.get("fingerprint") or "") != fingerprint:
            continue
        ts = _parse_utc(str(row.get("ts") or ""))
        if ts is None or ts >= cutoff:
            return True
    return False


async def run_probe(
    *,
    curator_parent: Path = DEFAULT_CURATOR_PARENT,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    limit: int = DEFAULT_LIMIT,
    threshold: int = DEFAULT_THRESHOLD,
    cooldown_hours: float = DEFAULT_COOLDOWN_HOURS,
    conversation_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    rows = await read_recent_corrections(
        curator_parent=curator_parent,
        limit=limit,
        conversation_id=conversation_id,
    )
    recurrences = find_recurrences(rows, threshold=threshold)
    if not recurrences:
        return {
            "status": "pass",
            "checked": len(rows),
            "threshold": threshold,
            "recurrences": [],
            "alert_recommended": False,
        }

    top = recurrences[0]
    already_alerted = alert_recently_sent(
        ops_ledger=ops_ledger,
        fingerprint=top.fingerprint,
        now=current,
        cooldown_hours=cooldown_hours,
    )
    return {
        "status": "fail",
        "checked": len(rows),
        "threshold": threshold,
        "recurrences": [recurrence_to_dict(item) for item in recurrences[:5]],
        "fingerprint": top.fingerprint,
        "count": top.count,
        "conversation_id": top.conversation_id,
        "alert_recommended": not already_alerted,
        "cooldown_hours": cooldown_hours,
    }


def recurrence_to_dict(item: Recurrence) -> dict[str, Any]:
    return {
        "fingerprint": item.fingerprint,
        "count": item.count,
        "conversation_id": item.conversation_id,
        "first_seen": item.first_seen,
        "latest_seen": item.latest_seen,
        "sample_original": item.sample_original[:280],
        "sample_correction": item.sample_correction[:280],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curator-parent", type=Path, default=DEFAULT_CURATOR_PARENT)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--cooldown-hours", type=float, default=DEFAULT_COOLDOWN_HOURS)
    parser.add_argument("--conversation-id", default=None)
    parser.add_argument("--spec-id", default="")
    parser.add_argument("--decision-id", default="")
    parser.add_argument("--branch", default="")
    return parser.parse_args(argv)


async def async_main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        result = await run_probe(
            curator_parent=args.curator_parent,
            ops_ledger=args.ops_ledger,
            limit=args.limit,
            threshold=args.threshold,
            cooldown_hours=args.cooldown_hours,
            conversation_id=args.conversation_id,
        )
    except ProbeUnavailable as exc:
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "error": str(exc),
                    "spec_id": args.spec_id,
                    "decision_id": args.decision_id,
                    "branch": args.branch,
                },
                sort_keys=True,
            )
        )
        return 2
    result.update(
        {"spec_id": args.spec_id, "decision_id": args.decision_id, "branch": args.branch}
    )
    print(json.dumps(result, sort_keys=True))
    return 1 if result.get("status") == "fail" else 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(async_main(list(sys.argv[1:] if argv is None else argv)))


if __name__ == "__main__":
    raise SystemExit(main())
