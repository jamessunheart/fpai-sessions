from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest

from app.config import Settings
from app.store import JsonlStore


@pytest.fixture
def settings(tmp_path):
    return Settings(var_dir=tmp_path, dry_run=True)


@pytest.fixture
def store(settings):
    return JsonlStore(settings.var_dir)

