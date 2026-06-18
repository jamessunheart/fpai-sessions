#!/usr/bin/env python3
"""Shared helpers for bounded hot-memory scanner outputs."""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_HOT_DIR = Path(os.environ.get("FPAI_HOT_MEMORY_DIR", "~/.config/fpai/hot_memory")).expanduser()
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
MAX_FACT_TEXT = 240
SECRET_RE = re.compile(r"(secret|token|password|passwd|api[_-]?key|private[_-]?key|credential)", re.I)
PRIVATE_RE = re.compile(r"(health|family|relationship|legal name|address|phone|wallet|seed phrase)", re.I)


@dataclasses.dataclass(frozen=True)
class HotFact:
    text: str
    source: str
    date: str
    weight: int = 5
    category: str = "general"

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_stamp(value: dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_date(path: Path) -> str:
    try:
        return utc_stamp(dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc))
    except OSError:
        return utc_stamp()


def clean_text(value: str, *, max_chars: int = MAX_FACT_TEXT) -> str:
    text = " ".join(str(value).replace("\x00", " ").split())
    text = text.replace("\u2192", "->").replace("\u00b7", "-").replace("\u2014", "-").replace("\u2013", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", lambda m: m.group(0).lower(), text)
    if len(text) > max_chars:
        text = text[: max(0, max_chars - 3)].rstrip() + "..."
    return text


def is_public_safe(value: str) -> bool:
    text = str(value)
    return bool(text.strip()) and not SECRET_RE.search(text) and not PRIVATE_RE.search(text)


def fact(text: str, source: str, date: str, *, weight: int = 5, category: str = "general") -> HotFact | None:
    if not is_public_safe(text):
        return None
    return HotFact(clean_text(text), clean_text(source, max_chars=160), date, int(weight), category)


def compact_facts(items: Iterable[HotFact | None], *, limit: int = 12) -> list[HotFact]:
    seen: set[str] = set()
    facts: list[HotFact] = []
    for item in items:
        if not item:
            continue
        key = re.sub(r"\W+", " ", item.text.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        facts.append(item)
    facts.sort(key=lambda row: (-row.weight, row.category, row.text))
    return facts[:limit]


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def read_jsonl_tail(path: Path, *, limit: int = 100) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def facts_hash(facts: Iterable[HotFact], pruned: Iterable[str] = ()) -> str:
    payload = {
        "facts": [item.to_json() for item in facts],
        "pruned": list(pruned),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def scanner_path(domain: str, hot_dir: Path = DEFAULT_HOT_DIR) -> Path:
    return hot_dir / f"scanner_{domain}.json"


def write_scan(
    domain: str,
    facts: list[HotFact],
    *,
    hot_dir: Path = DEFAULT_HOT_DIR,
    pruned: list[str] | None = None,
    now: dt.datetime | None = None,
    error: str = "",
) -> dict[str, Any]:
    hot_dir.mkdir(parents=True, exist_ok=True)
    path = scanner_path(domain, hot_dir)
    previous = read_json(path)
    pruned = pruned or []
    digest = facts_hash(facts, pruned)
    payload = {
        "schema": "hot-memory-scanner.v1",
        "domain": domain,
        "generated_at": utc_stamp(now),
        "changed": digest != previous.get("facts_hash"),
        "facts_hash": digest,
        "facts": [item.to_json() for item in facts],
        "pruned": [clean_text(item, max_chars=200) for item in pruned if is_public_safe(item)],
    }
    if error:
        payload["error"] = clean_text(error, max_chars=240)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def load_scans(hot_dir: Path = DEFAULT_HOT_DIR) -> list[dict[str, Any]]:
    scans: list[dict[str, Any]] = []
    for path in sorted(hot_dir.glob("scanner_*.json")):
        data = read_json(path)
        if data:
            scans.append(data)
    return scans
