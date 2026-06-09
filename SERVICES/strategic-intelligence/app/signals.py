"""
Strategic Intelligence - Signal Store
====================================

Receives external signals (from Data Service, Nerve Center digests, etc.)
and persists them so the Strategic Intelligence loop can incorporate them into
prioritization.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import settings


logger = logging.getLogger("StrategicSignals")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(kind: str, title: str, source: str, category: str) -> str:
    key = f"{kind}|{title}|{source}|{category}".encode("utf-8", errors="ignore")
    return hashlib.sha1(key).hexdigest()[:16]


class SignalStore:
    def __init__(self, max_items: int = 2000):
        self.max_items = max_items
        self.dir = settings.coordination_path / "signals"
        self.file = self.dir / "strategic_signals.json"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._signals: List[Dict[str, Any]] = []
        self._seen_ids: set[str] = set()
        self._load()

    def _load(self):
        try:
            if self.file.exists():
                self._signals = json.loads(self.file.read_text())
                for s in self._signals:
                    sid = s.get("id")
                    if sid:
                        self._seen_ids.add(sid)
        except Exception as e:
            logger.warning(f"Failed to load signals store: {e}")
            self._signals = []
            self._seen_ids = set()

    def _save(self):
        try:
            self.file.write_text(json.dumps(self._signals[-self.max_items :], indent=2))
        except Exception as e:
            logger.warning(f"Failed to persist signals store: {e}")

    def add_many(self, source: str, signals: List[Dict[str, Any]], kind: str = "signal") -> Dict[str, Any]:
        received_at = _utc_now_iso()
        stored = 0
        duplicates = 0

        for s in signals:
            title = str(s.get("title") or s.get("content") or s.get("name") or "").strip()
            if not title:
                continue
            category = str(s.get("category") or s.get("type") or "general")
            src = str(s.get("source") or source or "unknown")
            sid = str(s.get("id") or _stable_id(kind, title, src, category))

            if sid in self._seen_ids:
                duplicates += 1
                continue

            rec = {
                "id": sid,
                "kind": kind,
                "title": title,
                "category": category,
                "relevance": s.get("relevance") or s.get("relevance_score") or s.get("confidence") or 0.5,
                "source": src,
                "meta": s.get("meta") or {k: v for k, v in s.items() if k not in {"id", "title", "category", "relevance", "relevance_score", "confidence", "source"}},
                "received_at": received_at,
            }

            self._signals.append(rec)
            self._seen_ids.add(sid)
            stored += 1

        # Trim
        if len(self._signals) > self.max_items:
            self._signals = self._signals[-self.max_items :]
            self._seen_ids = {s.get("id") for s in self._signals if s.get("id")}

        if stored > 0:
            self._save()

        return {"received": len(signals), "stored": stored, "duplicates": duplicates, "kind": kind, "received_at": received_at}

    def recent(self, limit: int = 50, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        items = self._signals
        if kind:
            items = [s for s in items if s.get("kind") == kind]
        return list(reversed(items[-limit:]))

    def stats(self) -> Dict[str, Any]:
        by_kind: Dict[str, int] = {}
        by_cat: Dict[str, int] = {}
        for s in self._signals:
            by_kind[s.get("kind", "signal")] = by_kind.get(s.get("kind", "signal"), 0) + 1
            by_cat[s.get("category", "general")] = by_cat.get(s.get("category", "general"), 0) + 1
        return {
            "total": len(self._signals),
            "by_kind": by_kind,
            "by_category": by_cat,
            "storage_file": str(self.file),
        }


signal_store = SignalStore()




