"""CORA Agent — Strategic intelligence layer. Reads memory, generates directive."""

import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PROMPT_FILE = BASE / "agents" / "prompts" / "cora_system.txt"
SEED_FILE = BASE / "memory" / "seed.json"


def load_system_prompt():
    return PROMPT_FILE.read_text()


def load_seed():
    return json.loads(SEED_FILE.read_text())


def build_context(memory):
    """Build the user message context for CORA from current memory state."""
    seed = load_seed()
    cycle = memory.get("cycle_number", 0) + 1

    parts = [f"CYCLE {cycle} — CORA STRATEGIC ANALYSIS\n"]

    # Seed context (always included in Phase 1 since memory is thin)
    parts.append("ECOSYSTEM CONTEXT (seed):")
    parts.append(json.dumps(seed, indent=2))
    parts.append("")

    # Last operator report
    last_report = memory.get("operator_report")
    if last_report:
        parts.append("OPERATOR'S LAST REPORT:")
        parts.append(last_report)
        parts.append("")
    else:
        parts.append("OPERATOR'S LAST REPORT: (first cycle — no prior report)")
        parts.append("")

    # Steering messages
    steering = memory.get("sunheart_steering", [])
    unabsorbed = [s for s in steering if not s.get("absorbed")]
    if unabsorbed:
        parts.append("NEW STEERING FROM SUNHEART:")
        for s in unabsorbed:
            parts.append(f"  [{s.get('timestamp', 'unknown')}] {s.get('message', '')}")
        parts.append("")

    # Recent history (last 3 cycles)
    history = memory.get("history", [])
    if history:
        parts.append("RECENT CYCLE HISTORY:")
        for h in history[-3:]:
            parts.append(f"  Cycle {h.get('cycle_number', '?')}:")
            cora_sum = h.get("cora_directive_summary", "")
            if cora_sum:
                parts.append(f"    CORA: {cora_sum[:200]}")
            op_sum = h.get("operator_report_summary", "")
            if op_sum:
                parts.append(f"    Operator: {op_sum[:200]}")
        parts.append("")

    parts.append("Generate your strategic directive for this cycle. What is the highest-leverage move right now?")

    return "\n".join(parts)


def call_cora(memory, api_key, model="claude-sonnet-4-20250514", max_tokens=4096):
    """Call Claude API as CORA and return the directive text."""
    import requests

    system_prompt = load_system_prompt()
    context = build_context(memory)

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": context}],
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise Exception(f"CORA API error {response.status_code}: {response.text[:300]}")

    data = response.json()
    text = data["content"][0]["text"]

    return text, data.get("usage", {})
