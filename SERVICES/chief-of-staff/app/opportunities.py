"""Opportunity Portfolio view for Chief of Staff."""
from __future__ import annotations

import os
import importlib.util as _ilu
from pathlib import Path

from app.config import settings


def _repo_root() -> Path:
    return Path(os.environ.get("FPAI_REPO_ROOT", settings.COCKPIT_ROOT)).resolve()


def _ledger_path() -> Path:
    return Path(os.environ.get("FPAI_OPPORTUNITY_LEDGER", Path.home() / ".config/fpai/allocation/opportunities.json"))


def build_opportunities_view() -> dict:
    engine = _load_engine()

    return engine.ranked(engine.ensure_seeded(_ledger_path()))


def opportunities_digest_line() -> str:
    return _load_engine().digest_line(_ledger_path())


def _load_engine():
    path = _repo_root() / "tools" / "allocation" / "opportunity_engine.py"
    spec = _ilu.spec_from_file_location("fpai_opportunity_engine", path)
    mod = _ilu.module_from_spec(spec) if spec and spec.loader else None
    if not mod:
        raise RuntimeError(f"unable to load opportunity engine from {path}")
    spec.loader.exec_module(mod)
    return mod
