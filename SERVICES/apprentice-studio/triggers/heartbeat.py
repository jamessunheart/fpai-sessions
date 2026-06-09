"""
Standalone heartbeat runner.

Useful for running cycles outside FastAPI — from a cron, manual command, or test.

Usage:
    cd SERVICES/apprentice-studio
    python triggers/heartbeat.py            # one daily cycle
    python triggers/heartbeat.py weekly     # full weekly review
"""

from __future__ import annotations

import asyncio
import logging
import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from orchestrator import get_orchestrator  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("apprentice_studio.heartbeat")


async def _run(mode: str) -> None:
    orch = get_orchestrator()
    if mode == "weekly":
        markdown = await orch.run_weekly_review()
        print(markdown)
    else:
        report = await orch.run_cycle()
        print(f"[{datetime.now().isoformat()}] cycle ran")
        print(f"summary: {report.summary}")
        if report.decisions_needed:
            print("decisions needed:")
            for d in report.decisions_needed:
                print(f"  - {d}")
        if report.blocks:
            print("blocks:")
            for b in report.blocks:
                print(f"  - {b}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    asyncio.run(_run(mode))


if __name__ == "__main__":
    main()
