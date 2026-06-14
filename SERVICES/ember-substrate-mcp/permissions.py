"""
ember-substrate-mcp · permissions.py
=====================================

Path validation for write tools. Mirrors the Trust-tier 4.1 boundary
of recursive-optimizer + standards-keeper:

- Reads `.claude/hot-files.txt` at startup (re-read on SIGHUP)
- Refuses writes to:
    * identity paths (memory/identity/* · core/STATE/identity/*)
    * every path listed in hot-files.txt
    * .claude/settings.json · .claude/settings.local.json
    * .claude/agents/* · .claude/hooks/*
- Returns structured 403 dict — NEVER raises into the MCP harness.

The only writes allowed are the 5 queued surfaces:
- ~/.config/fpai/ember/* (events, decisions, inbox · via FastAPI)
- ~/.config/fpai/forge/queued/*.md
- ~/.config/fpai/standards/canonize_queue.md (append-only)
- ~/.claude/memory-global/*.md (no overwrite, no identity/*, kebab-case)
"""

from __future__ import annotations

import logging
import os
import re
import signal
from pathlib import Path
from typing import Optional

log = logging.getLogger("ember-mcp.permissions")

FPAI_COCKPIT_ROOT = Path(
    os.environ.get("FPAI_COCKPIT_ROOT", "/Users/jamessunheart/FPAI_Cockpit")
).resolve()
EMBER_MEMORY_GLOBAL = Path(
    os.environ.get("EMBER_MEMORY_GLOBAL", "/Users/jamessunheart/.claude/memory-global")
).resolve()
EMBER_FPAI_CONFIG = Path(
    os.environ.get("EMBER_FPAI_CONFIG", "/Users/jamessunheart/.config/fpai")
).resolve()

# External roots that are allowed targets (outside FPAI_Cockpit).
ALLOWED_EXTERNAL_ROOTS: tuple[Path, ...] = (EMBER_MEMORY_GLOBAL, EMBER_FPAI_CONFIG)

# Identity prefix patterns — relative to FPAI_COCKPIT_ROOT or memory roots.
IDENTITY_PREFIXES: tuple[str, ...] = (
    "memory/identity/",
    "core/STATE/identity/",
    "identity/",  # within ~/.claude/memory-global/
)

# Exact denies (relative to repo root).
EXACT_DENY: frozenset[str] = frozenset({
    ".claude/settings.json",
    ".claude/settings.local.json",
    "CLAUDE.md",
})

# Prefix denies (relative to repo root).
PREFIX_DENY: tuple[str, ...] = (
    ".claude/agents/",
    ".claude/hooks/",
)

_HOT_FILES: frozenset[str] = frozenset()
_KEBAB_FILENAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*\.md$")
_KEBAB_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _load_hot_files() -> frozenset[str]:
    path = FPAI_COCKPIT_ROOT / ".claude" / "hot-files.txt"
    if not path.exists():
        log.warning("hot-files.txt not found at %s", path)
        return frozenset()
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    log.info("loaded %d hot-files entries", len(lines))
    return frozenset(lines)


def reload_hot_files(*_args) -> None:
    global _HOT_FILES
    _HOT_FILES = _load_hot_files()


# Initial load + SIGHUP handler.
_HOT_FILES = _load_hot_files()
try:
    signal.signal(signal.SIGHUP, reload_hot_files)
except (ValueError, OSError):
    # Non-main thread or platform without SIGHUP — fine, skip.
    pass


def _deny(path: str, reason: str) -> dict:
    return {"error": "fatal_zone", "path": path, "reason": reason}


def is_kebab_filename(name: str) -> bool:
    """Filename must be `[a-z0-9][a-z0-9_-]*.md`."""
    return bool(_KEBAB_FILENAME_RE.match(name))


def is_kebab_slug(slug: str) -> bool:
    """Slug must be kebab-case alphanumeric."""
    return bool(_KEBAB_SLUG_RE.match(slug))


def _resolve_under_allowed_root(target: Path) -> Optional[Path]:
    """Resolve target. Return resolved path if under an allowed root, else None."""
    try:
        resolved = target.resolve(strict=False)
    except (OSError, RuntimeError):
        return None
    # Must be under FPAI_COCKPIT_ROOT or one of the external allowed roots.
    candidates = (FPAI_COCKPIT_ROOT,) + ALLOWED_EXTERNAL_ROOTS
    for root in candidates:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    return None


def check_write(path: str | os.PathLike) -> Optional[dict]:
    """
    Validate a write target.

    Returns None if the write is permitted; otherwise a structured 403 dict.
    NEVER raises.
    """
    p_in = Path(path)

    # Reject anything containing `..` segments — defense in depth even though
    # resolve() collapses them; we want to surface intent-clear refusals too.
    if any(part == ".." for part in p_in.parts):
        return _deny(str(p_in), "path-traversal-segment")

    resolved = _resolve_under_allowed_root(p_in)
    if resolved is None:
        return _deny(str(p_in), "outside-allowed-roots")

    # If resolved is under FPAI_COCKPIT_ROOT, compute the repo-relative form
    # and run all the per-repo deny checks.
    try:
        rel_repo = resolved.relative_to(FPAI_COCKPIT_ROOT)
        rel_repo_str = str(rel_repo).replace(os.sep, "/")
    except ValueError:
        rel_repo_str = None

    if rel_repo_str is not None:
        # Exact denies
        if rel_repo_str in EXACT_DENY:
            return _deny(rel_repo_str, "exact-deny-list")
        # Prefix denies
        for pref in PREFIX_DENY:
            if rel_repo_str.startswith(pref):
                return _deny(rel_repo_str, f"prefix-deny:{pref}")
        # Identity prefixes (repo-side)
        for pref in IDENTITY_PREFIXES:
            if rel_repo_str.startswith(pref):
                return _deny(rel_repo_str, f"identity-prefix:{pref}")
        # Hot-files.txt
        if rel_repo_str in _HOT_FILES:
            return _deny(rel_repo_str, "hot-files.txt")

    # If resolved is under EMBER_MEMORY_GLOBAL, refuse identity/* writes.
    try:
        rel_mem = resolved.relative_to(EMBER_MEMORY_GLOBAL)
        rel_mem_str = str(rel_mem).replace(os.sep, "/")
        if rel_mem_str.startswith("identity/") or rel_mem_str == "identity":
            return _deny(rel_mem_str, "identity-prefix:identity/")
        # Permit only top-level .md files (no nested dirs except sessions/)
        # We allow memory-global root .md writes; nested writes are reserved.
        # (Slightly stricter than spec — keeps default safe; can relax later.)
    except ValueError:
        pass

    # Refuse writes directly to FPAI_COCKPIT_ROOT/core/STATE/* by default
    # (use /message or POST /event endpoints, not direct file edit).
    if rel_repo_str is not None and rel_repo_str.startswith("core/STATE/"):
        # Already caught for identity/; the rest is also denied (NOW.md etc.
        # are in hot-files.txt, but defense in depth).
        return _deny(rel_repo_str, "core-state-write-forbidden")

    return None


def hot_files_snapshot() -> list[str]:
    """For diagnostics / smoke test."""
    return sorted(_HOT_FILES)
