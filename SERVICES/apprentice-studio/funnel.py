#!/usr/bin/env python3
"""
Funnel CLI shim — run from SERVICES/apprentice-studio/.

This thin wrapper lets you run:
    python funnel.py <command> ...

instead of:
    python -m funnel.cli <command> ...
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from funnel.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
