#!/usr/bin/env python3
"""Reset CORA-Operator loop to clean state. Use with caution."""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MEMORY_FILE = BASE / "memory" / "memory.json"

def reset():
    confirm = input("This will reset memory to cycle 0. Archives are preserved. Continue? (y/N): ")
    if confirm.lower() != "y":
        print("Aborted.")
        return

    memory = {
        "cycle_number": 0,
        "timestamp": None,
        "status": "initialized",
        "locked_by": None,
        "cora_directive": None,
        "operator_report": None,
        "sunheart_steering": [],
        "history": [],
    }
    MEMORY_FILE.write_text(json.dumps(memory, indent=2))
    print("✅ Memory reset to cycle 0. Archives preserved.")

if __name__ == "__main__":
    reset()
