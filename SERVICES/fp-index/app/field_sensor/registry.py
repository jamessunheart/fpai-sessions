"""Append-only memory for the field sensor.

Every gap the system notices in itself goes here. Immutable log.
When the assembly layer comes online, this registry becomes the
prioritized build list.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BRAIN_DIR = Path(os.getenv("FPI_BRAIN_DIR", "/opt/fpai/brain"))
REGISTRY_PATH = BRAIN_DIR / "gap_registry.jsonl"
CAPABILITIES_PATH = BRAIN_DIR / "capabilities.md"
EVENTS_DB = BRAIN_DIR / "field_events.db"

DEFAULT_CAPABILITIES = """# FPI Current Capabilities

## LLM Providers
- Anthropic Claude (Sonnet, Haiku) via anthropic SDK
- OpenAI GPT (via openai SDK)
- Ollama local models (llama3, etc.) on secondary server

## Agent / Conversation
- Telegram companion (Adam) — long-running, SYSTEM_PROMPT aligned to Zen Village
- Signal router with decision engine
- Budget ledger with spend tracking

## Data Capture
- Tiered scanners (disabled 2026-04-24, scaffolding preserved)
- HuggingFace / arXiv / GitHub / OpenRouter metadata pulls
- Feedparser for RSS sources

## Storage
- SQLite (fp_index.db, fpi.db, zen_pass.db)
- Append-only JSONL logs in /opt/fpai/brain/

## Infrastructure
- FastAPI + APScheduler + systemd
- Credits Gateway (port 8765, UC ledger)
- Zen Village (port 8770, bookings + passes + Stripe)
- nginx reverse proxy + Postfix mail

## Known Gaps (seed entries — will grow via field_sensor)
- No auto-integration layer (Step 4 of self-assembly loop)
- No capability gap detection from field signals
- No sandboxed code execution for testing new integrations
- No model router that adapts to newly released models automatically
- No structured memory of past decisions + outcomes
"""


def ensure_brain_dir() -> None:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    if not CAPABILITIES_PATH.exists():
        CAPABILITIES_PATH.write_text(DEFAULT_CAPABILITIES)
        logger.info(f"[FIELD] Seeded capabilities.md at {CAPABILITIES_PATH}")
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.touch()
        logger.info(f"[FIELD] Created empty gap_registry.jsonl at {REGISTRY_PATH}")


def capabilities_snapshot() -> str:
    ensure_brain_dir()
    return CAPABILITIES_PATH.read_text()


def append_gap(entry: dict[str, Any]) -> None:
    """Append a single gap observation. Never overwrites, never deletes."""
    ensure_brain_dir()
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **entry,
    }
    with REGISTRY_PATH.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")
    logger.info(f"[FIELD] Gap logged: {entry.get('gap_summary', entry.get('event_title', '?'))[:80]}")


def read_recent_gaps(limit: int = 50) -> list[dict[str, Any]]:
    """Read the N most recent gaps. Used for dashboard + dedup."""
    ensure_brain_dir()
    if not REGISTRY_PATH.exists():
        return []
    lines = REGISTRY_PATH.read_text().strip().split("\n")
    if not lines or lines == [""]:
        return []
    recent = lines[-limit:]
    out = []
    for ln in recent:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def registry_stats() -> dict[str, Any]:
    """Summary stats for the dashboard."""
    gaps = read_recent_gaps(limit=10_000)
    return {
        "total_gaps": len(gaps),
        "latest_ts": gaps[-1]["ts"] if gaps else None,
        "recent_titles": [g.get("event_title", g.get("gap_summary", "?"))[:80] for g in gaps[-5:]],
    }
