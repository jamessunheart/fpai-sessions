"""Operator Agent — Tactical execution layer. Reads CORA directive, generates report."""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PROMPT_FILE = BASE / "agents" / "prompts" / "operator_system.txt"
SEED_FILE = BASE / "memory" / "seed.json"


def load_system_prompt():
    return PROMPT_FILE.read_text()


def build_context(memory, cora_directive):
    """Build the user message context for Operator from CORA's directive."""
    seed = json.loads(SEED_FILE.read_text())
    cycle = memory.get("cycle_number", 0) + 1

    parts = [f"CYCLE {cycle} — OPERATOR TACTICAL EXECUTION\n"]

    parts.append("CORA'S DIRECTIVE FOR THIS CYCLE:")
    parts.append(cora_directive)
    parts.append("")

    # Steering (so Operator is aware)
    steering = memory.get("sunheart_steering", [])
    unabsorbed = [s for s in steering if not s.get("absorbed")]
    if unabsorbed:
        parts.append("SUNHEART STEERING (for awareness):")
        for s in unabsorbed:
            parts.append(f"  [{s.get('timestamp', 'unknown')}] {s.get('message', '')}")
        parts.append("")

    # Last operator report (continuity)
    last_report = memory.get("operator_report")
    if last_report:
        parts.append("YOUR LAST REPORT (for continuity):")
        parts.append(last_report[:1000])
        parts.append("")

    # Known priorities for reference
    parts.append("CURRENT PRIORITIES (reference):")
    for p in seed.get("priorities_ranked", []):
        parts.append(f"  {p}")
    parts.append("")

    parts.append("Break CORA's directives into concrete tasks. Execute what you can. Report status on everything. Flag what's blocked and what needs human hands.")

    return "\n".join(parts)


def call_operator(memory, cora_directive, api_key, model="claude-sonnet-4-20250514", max_tokens=4096):
    """Call Claude API as Operator and return the report text."""
    import requests

    system_prompt = load_system_prompt()
    context = build_context(memory, cora_directive)

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
        raise Exception(f"Operator API error {response.status_code}: {response.text[:300]}")

    data = response.json()
    text = data["content"][0]["text"]

    return text, data.get("usage", {})
