"""Spine Cycle Runner — the main orchestrator that runs each CORA-Operator cycle.

Follows the spec exactly:
1. Acquire cycle lock
2. Validate memory integrity
3. Absorb new Sunheart steering from Telegram
4. Run CORA
5. Validate + write CORA output
6. Run Operator
7. Validate + write Operator output
8. Send Telegram summary
9. Archive cycle, release lock
10. Log health metrics
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from agents.cora import call_cora
from agents.operator import call_operator
from spine.validator import validate_memory, validate_lock, trim_history
from telegram.bot import send_message, get_new_messages
from telegram.formatter import format_cycle_summary, format_error

MEMORY_FILE = BASE / "memory" / "memory.json"
ARCHIVE_DIR = BASE / "memory" / "archive"
LOG_DIR = BASE / "logs"

logger = logging.getLogger("spine")


def load_memory():
    return json.loads(MEMORY_FILE.read_text())


def save_memory(memory):
    MEMORY_FILE.write_text(json.dumps(memory, indent=2, default=str))


def acquire_lock(memory):
    """Acquire cycle lock. Returns False if already locked."""
    unlocked, holder = validate_lock(memory)
    if not unlocked:
        lock_time = memory.get("lock_time")
        if lock_time:
            locked_at = datetime.fromisoformat(lock_time)
            if datetime.now(timezone.utc) - locked_at > timedelta(minutes=30):
                logger.warning("Stale lock detected (>30min), force-releasing")
            else:
                return False
        else:
            return False

    memory["locked_by"] = "spine"
    memory["lock_time"] = datetime.now(timezone.utc).isoformat()
    memory["status"] = "running"
    save_memory(memory)
    return True


def release_lock(memory):
    memory["locked_by"] = None
    memory["lock_time"] = None
    save_memory(memory)


def absorb_steering(memory):
    """Get new Telegram messages and inject into memory as steering."""
    try:
        messages = get_new_messages()
    except Exception as e:
        logger.warning(f"Failed to fetch Telegram messages: {e}")
        return 0

    cycle_num = memory.get("cycle_number", 0) + 1
    count = 0
    for msg in messages:
        ts = msg.get("timestamp", 0)
        if isinstance(ts, int):
            ts = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        memory["sunheart_steering"].append({
            "timestamp": ts,
            "message": msg["message"],
            "absorbed_in_cycle": cycle_num,
            "absorbed": False,
        })
        count += 1

    return count


def archive_cycle(memory, cora_directive, operator_report):
    """Archive the completed cycle to history and to disk."""
    cycle_num = memory["cycle_number"]

    history_entry = {
        "cycle_number": cycle_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cora_directive_summary": (cora_directive or "")[:300],
        "operator_report_summary": (operator_report or "")[:300],
    }
    memory["history"].append(history_entry)

    # Save full cycle to archive file
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_file = ARCHIVE_DIR / f"cycle_{cycle_num:04d}.json"
    archive_data = {
        "cycle_number": cycle_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cora_directive": cora_directive,
        "operator_report": operator_report,
        "steering_at_time": [s for s in memory.get("sunheart_steering", []) if s.get("absorbed_in_cycle") == cycle_num],
    }
    archive_file.write_text(json.dumps(archive_data, indent=2, default=str))

    # Mark steering as absorbed
    for s in memory.get("sunheart_steering", []):
        if not s.get("absorbed"):
            s["absorbed"] = True

    trim_history(memory)


def run_cycle(is_retry=False):
    """Execute one full CORA-Operator cycle. Returns True on success."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    model = os.environ.get("CORA_MODEL", "claude-sonnet-4-20250514")

    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return False

    # Load memory
    memory = load_memory()
    cycle_num = memory.get("cycle_number", 0) + 1

    logger.info(f"=== Starting cycle {cycle_num} ===")

    # Step 1: Acquire lock
    if not acquire_lock(memory):
        logger.warning(f"Cycle {cycle_num} skipped — already locked by {memory.get('locked_by')}")
        if not is_retry:
            try:
                send_message(f"⏭️ Cycle {cycle_num} skipped — another cycle is running.")
            except Exception:
                pass
        return False

    cora_directive = None
    operator_report = None
    total_usage = {"input_tokens": 0, "output_tokens": 0}

    try:
        # Step 2: Validate memory
        validate_memory(memory)
        logger.info("Memory validated")

        # Step 3: Absorb steering
        steering_count = absorb_steering(memory)
        logger.info(f"Absorbed {steering_count} steering message(s)")

        # Step 4: Run CORA
        logger.info("Calling CORA...")
        cora_directive, cora_usage = call_cora(memory, api_key, model=model)
        total_usage["input_tokens"] += cora_usage.get("input_tokens", 0)
        total_usage["output_tokens"] += cora_usage.get("output_tokens", 0)
        logger.info(f"CORA responded ({len(cora_directive)} chars)")

        # Step 5: Write CORA to memory
        memory["cora_directive"] = cora_directive

        # Step 6: Run Operator
        logger.info("Calling Operator...")
        operator_report, op_usage = call_operator(memory, cora_directive, api_key, model=model)
        total_usage["input_tokens"] += op_usage.get("input_tokens", 0)
        total_usage["output_tokens"] += op_usage.get("output_tokens", 0)
        logger.info(f"Operator responded ({len(operator_report)} chars)")

        # Step 7: Write Operator to memory
        memory["operator_report"] = operator_report
        memory["cycle_number"] = cycle_num
        memory["timestamp"] = datetime.now(timezone.utc).isoformat()
        memory["status"] = "completed"

        # Step 8: Send Telegram
        try:
            summary = format_cycle_summary(cycle_num, cora_directive, operator_report, steering_count)
            send_message(summary)
            logger.info("Telegram summary sent")
        except Exception as e:
            logger.error(f"Telegram send failed (non-fatal): {e}")

        # Step 9: Archive cycle
        archive_cycle(memory, cora_directive, operator_report)
        logger.info(f"Cycle {cycle_num} archived")

        # Step 10: Log health
        est_cost = (total_usage["input_tokens"] * 3.0 / 1_000_000) + (total_usage["output_tokens"] * 15.0 / 1_000_000)
        logger.info(f"Cycle {cycle_num} complete — tokens: {total_usage}, est cost: ${est_cost:.4f}")

        return True

    except Exception as e:
        logger.error(f"Cycle {cycle_num} failed: {e}", exc_info=True)
        memory["status"] = "failed"

        # Send error alert
        step = "CORA" if cora_directive is None else "Operator" if operator_report is None else "post-processing"
        try:
            send_message(format_error(cycle_num, step, e))
        except Exception:
            pass

        # Retry once
        if not is_retry:
            logger.info(f"Retrying cycle {cycle_num} in 5 minutes...")
            release_lock(memory)
            save_memory(memory)
            time.sleep(300)
            return run_cycle(is_retry=True)

        return False

    finally:
        release_lock(memory)
        save_memory(memory)


if __name__ == "__main__":
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "cycle.log"),
        ],
    )
    success = run_cycle()
    sys.exit(0 if success else 1)
