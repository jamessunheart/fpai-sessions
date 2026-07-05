"""Capability-created view for Chief of Staff."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from app.config import settings


def _repo_root() -> Path:
    return Path(os.environ.get("FPAI_REPO_ROOT", settings.COCKPIT_ROOT)).resolve()


def _ledger_path() -> Path:
    return Path(os.environ.get("FPAI_CAPABILITY_LEDGER", Path.home() / ".config/fpai/allocation/ledger.jsonl"))


def build_capability_view() -> dict:
    repo = _repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from tools.allocation.capability_ledger import capability_view

    return capability_view(_ledger_path())


def capability_digest_line() -> str:
    repo = _repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from tools.allocation.capability_ledger import format_summary, period_summary

    return format_summary(period_summary(_ledger_path(), days=1))
