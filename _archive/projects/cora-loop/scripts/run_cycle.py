#!/usr/bin/env python3
"""Manually trigger a CORA-Operator cycle."""

import sys
import logging
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

# Load .env
env_file = BASE / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            import os
            os.environ.setdefault(key.strip(), value.strip())

from spine.cycle_runner import run_cycle, LOG_DIR

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "cycle.log"),
    ],
)

if __name__ == "__main__":
    success = run_cycle()
    if success:
        print("\n✅ Cycle completed successfully.")
    else:
        print("\n❌ Cycle failed. Check logs/cycle.log for details.")
    sys.exit(0 if success else 1)
