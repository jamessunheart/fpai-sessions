#!/usr/bin/env python3
"""Start the CORA-Operator loop as a persistent process.
Runs cycles on schedule and polls Telegram for steering between cycles."""

import sys
import time
import logging
import os
from datetime import datetime, timezone
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
            os.environ.setdefault(key.strip(), value.strip())

from spine.cycle_runner import run_cycle, load_memory, LOG_DIR
from telegram.bot import get_new_messages

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "cora-loop.log"),
    ],
)
logger = logging.getLogger("cora-loop")

SCHEDULE_HOURS = [12, 16, 20, 0, 4]  # UTC (roughly HST +10)
HEARTBEAT_CHECK_SECONDS = 300  # Check for steering every 5 min
WATCHDOG_HOURS = 8


def should_run_now(last_run_hour):
    """Check if current UTC hour is a scheduled slot we haven't run yet."""
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    if current_hour in SCHEDULE_HOURS and current_hour != last_run_hour:
        return True
    return False


def check_heartbeat_health():
    """Alert if no successful cycle in WATCHDOG_HOURS."""
    try:
        memory = load_memory()
        ts = memory.get("timestamp")
        if ts:
            last = datetime.fromisoformat(ts)
            if not last.tzinfo:
                last = last.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
            if age_hours > WATCHDOG_HOURS:
                from telegram.formatter import format_health_lost
                from telegram.bot import send_message
                send_message(format_health_lost())
                logger.warning(f"Heartbeat lost — last cycle was {age_hours:.1f} hours ago")
    except Exception as e:
        logger.warning(f"Health check error: {e}")


def main():
    logger.info("CORA-Operator Loop started")
    logger.info(f"Schedule (UTC hours): {SCHEDULE_HOURS}")

    last_run_hour = -1
    health_check_counter = 0

    while True:
        try:
            if should_run_now(last_run_hour):
                now = datetime.now(timezone.utc)
                last_run_hour = now.hour
                logger.info(f"Scheduled cycle triggered at {now.isoformat()}")
                run_cycle()

            # Poll Telegram for steering (messages get buffered, absorbed next cycle)
            health_check_counter += 1
            if health_check_counter >= 12:  # Every hour
                check_heartbeat_health()
                health_check_counter = 0

        except Exception as e:
            logger.error(f"Loop error: {e}", exc_info=True)

        time.sleep(HEARTBEAT_CHECK_SECONDS)


if __name__ == "__main__":
    main()
