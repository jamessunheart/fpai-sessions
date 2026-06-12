#!/usr/bin/env python3
"""
Multi-model decision debate · v1 · 2026-05-24

Takes a decision topic, dispatches to 2-4 available models for adversarial debate,
synthesizes pros/cons + recommendation, logs to append-only JSONL ledger.

Trust-tier 6.1: substrate-decides-with-debate-and-log. James reverses via log.

Models currently wired:
  - claude-opus (via ~/.local/bin/claude CLI)
  - qwen3-max (via DashScope intl OpenAI-compatible API)
  - [TODO] gpt-4 (via OpenAI API, key at ~/.config/fpai/openai/api.token)
  - [TODO] gemini-2.5-pro (via Google AI Studio, key at ~/.config/fpai/gemini/api.token)

Usage:
  python3 debate.py "Decision topic phrased as a question?"
  python3 debate.py --execute "Topic" --pro-cmd "..." --con-cmd "..." --reversal-cmd "..."

Output:
  ~/.config/fpai/decisions/log.jsonl (append-only)
  stdout (full debate transcript)
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# === Constants ===
HOME = Path.home()
LOG_DIR = HOME / ".config" / "fpai" / "decisions"
LOG_FILE = LOG_DIR / "log.jsonl"
CLAUDE_BIN = HOME / ".local" / "bin" / "claude"
QWEN_KEY_FILE = HOME / ".config" / "fpai" / "qwen" / "api.token"
QWEN_ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

PRICING = {
    "claude-opus": {"in": 15.00, "out": 75.00},
    "qwen3-max": {"in": 2.50, "out": 7.50},
}


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", file=sys.stderr, flush=True)


def estimate_cost(model: str, t_in: int, t_out: int) -> float:
    p = PRICING.get(model)
    if not p:
        return 0.0
    return (t_in * p["in"] + t_out * p["out"]) / 1_000_000


# === Debate prompt templates ===
DEBATE_PROMPT = """You are part of a multi-model decision debate. Your job is to argue ONE side of a decision rigorously.

## The decision to debate

{topic}

## Your role

{role}

## Your task

Produce a structured argument in this exact format:

**Core position (one sentence):**
[your stance]

**Three strongest arguments for your side:**
1. [argument with reasoning]
2. [argument with reasoning]
3. [argument with reasoning]

**Strongest counter-argument (steelman the other side):**
[their best point]

**What would change your mind:**
[specific evidence or condition that would flip your stance]

Be concrete. Avoid hedging. Argue your position as forcefully as a senior engineer would. Limit total response to 300 words.
"""

SYNTHESIS_PROMPT = """You are the referee of a 2-model debate on this decision:

## The decision
{topic}

## Position A (PRO · {pro_model})
{pro_arg}

## Position B (CON · {con_model})
{con_arg}

## Your task

Produce a synthesis in this exact format:

**Convergence:**
[where both models genuinely agree, 1-3 bullets]

**Divergence:**
[the real axis of disagreement, 1-2 sentences]

**Recommendation: YES / NO / REFINE**
[one-paragraph reasoning · what should happen]

**Reversibility classification: REVERSIBLE / PARTIALLY-REVERSIBLE / IRREVERSIBLE**
[brief justification]

**If REVERSIBLE — exact rollback steps:**
1. [command or action to undo]
2. [...]

**Confidence (0-100):**
[number] · [one-line reasoning for confidence level]

Be decisive. Limit total response to 500 words. The recommendation MUST be one of YES/NO/REFINE — no "it depends" hedges.
"""


# === Model adapters ===
def call_claude(prompt: str, model_alias: str = "opus") -> tuple[str | None, dict]:
    """Invoke claude CLI. Returns (text, usage_dict)."""
    cmd = [str(CLAUDE_BIN), "--model", model_alias, "-p", "--output-format", "json", prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return None, {"error": "timeout"}
    if r.returncode != 0:
        return None, {"error": r.stderr[:300] or "non-zero exit"}
    try:
        data = json.loads(r.stdout)
        text = data.get("result", "")
        usage = data.get("usage", {})
        return text, {
            "tokens_in": usage.get("input_tokens", 0),
            "tokens_out": usage.get("output_tokens", 0),
            "cost_usd": data.get("total_cost_usd", 0),
        }
    except json.JSONDecodeError:
        return r.stdout, {}


def call_qwen(prompt: str) -> tuple[str | None, dict]:
    """Hit DashScope intl OpenAI-compat endpoint via curl subprocess (Python urllib has CA bundle issues on macOS)."""
    try:
        key = QWEN_KEY_FILE.read_text().strip()
    except FileNotFoundError:
        return None, {"error": f"qwen key missing at {QWEN_KEY_FILE}"}

    body = json.dumps({
        "model": "qwen3-max",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
    })

    cmd = [
        "curl", "-sS", "-X", "POST", QWEN_ENDPOINT,
        "-H", f"Authorization: Bearer {key}",
        "-H", "Content-Type: application/json",
        "-d", body,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return None, {"error": "qwen curl timeout"}

    if r.returncode != 0:
        return None, {"error": f"curl exit {r.returncode}: {r.stderr[:300]}"}

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None, {"error": f"qwen non-JSON response: {r.stdout[:300]}"}

    if "error" in data:
        return None, {"error": f"qwen API error: {data['error']}"}

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return None, {"error": f"qwen unexpected shape: {str(data)[:300]}"}

    usage = data.get("usage", {})
    t_in = usage.get("prompt_tokens", 0)
    t_out = usage.get("completion_tokens", 0)
    return text, {
        "tokens_in": t_in,
        "tokens_out": t_out,
        "cost_usd": estimate_cost("qwen3-max", t_in, t_out),
    }


def append_log(entry: dict):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", nargs="+", help="The decision topic (as a question)")
    ap.add_argument("--pro-role", default="Argue FOR the decision (YES, proceed). Defend the action.")
    ap.add_argument("--con-role", default="Argue AGAINST the decision (NO, hold). Defend inaction or the alternative.")
    ap.add_argument("--auto-execute-if-reversible", action="store_true",
                    help="If synthesis says YES and classification is REVERSIBLE, execute the rollback_cmd flag's *opposite* automatically. Default: log only.")
    ap.add_argument("--execute-cmd", default=None, help="Shell command to run if synthesis = YES and --auto-execute set")
    ap.add_argument("--rollback-cmd", default=None, help="Shell command stored in log for reversal")
    args = ap.parse_args()

    topic = " ".join(args.topic)
    decision_id = f"d_{int(time.time())}"
    started_at = datetime.now(timezone.utc).isoformat()

    print(f"\n{'=' * 70}", flush=True)
    print(f"DECISION DEBATE · {decision_id}", flush=True)
    print(f"{'=' * 70}", flush=True)
    print(f"Topic: {topic}", flush=True)
    print(f"Started: {started_at}", flush=True)
    print(f"{'=' * 70}\n", flush=True)

    # === Round 1: Pro (Claude) ===
    print(">>> Claude (PRO) thinking...", flush=True)
    pro_prompt = DEBATE_PROMPT.format(topic=topic, role=args.pro_role)
    pro_text, pro_usage = call_claude(pro_prompt, "opus")
    print(f"\n--- PRO · claude-opus ---\n{pro_text or '(failed: ' + json.dumps(pro_usage) + ')'}\n", flush=True)

    # === Round 2: Con (Qwen) ===
    print(">>> Qwen (CON) thinking...", flush=True)
    con_prompt = DEBATE_PROMPT.format(topic=topic, role=args.con_role)
    con_text, con_usage = call_qwen(con_prompt)
    print(f"\n--- CON · qwen3-max ---\n{con_text or '(failed: ' + json.dumps(con_usage) + ')'}\n", flush=True)

    # === Round 3: Synthesis (Claude as referee) ===
    print(">>> Synthesizing...", flush=True)
    synth_prompt = SYNTHESIS_PROMPT.format(
        topic=topic,
        pro_model="claude-opus",
        pro_arg=pro_text or "(no response)",
        con_model="qwen3-max",
        con_arg=con_text or "(no response)",
    )
    synth_text, synth_usage = call_claude(synth_prompt, "opus")
    print(f"\n--- SYNTHESIS · referee ---\n{synth_text or '(failed)'}\n", flush=True)

    # === Round 4: Ember summary (one conversational sentence) ===
    # Cheap call (~$0.01) so future TG digests can render this decision in Ember voice
    # without verbatim-truncating the technical topic. See feedback_tg_voice_must_be_embers.md.
    summary_prompt = (
        "Summarize the following decision in ONE short conversational phrase suitable for a friend's "
        "voice (10-15 words). Lowercase, no formal jargon. Just say what the decision is about.\n\n"
        f"Decision topic:\n{topic}\n\n"
        "Return ONLY the phrase. No preamble. No quotes."
    )
    summary_text, summary_usage = call_claude(summary_prompt, "haiku")
    ember_summary = (summary_text or "").strip().strip('"').strip("'").lower()
    if len(ember_summary) > 200:
        ember_summary = ember_summary[:197] + "..."
    print(f"\n--- EMBER SUMMARY ---\n{ember_summary or '(missing)'}\n", flush=True)

    # === Build log entry ===
    total_cost = (
        pro_usage.get("cost_usd", 0)
        + con_usage.get("cost_usd", 0)
        + synth_usage.get("cost_usd", 0)
    )

    entry = {
        "decision_id": decision_id,
        "topic": topic,
        "ember_summary": ember_summary,
        "started_at": started_at,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "models_consulted": ["claude-opus", "qwen3-max", "claude-opus (referee)", "claude-haiku (summary)"],
        "pro_role": args.pro_role,
        "con_role": args.con_role,
        "positions": {
            "PRO_claude": pro_text,
            "CON_qwen": con_text,
        },
        "synthesis": synth_text,
        "usage": {
            "pro_claude": pro_usage,
            "con_qwen": con_usage,
            "synthesis_claude": synth_usage,
            "ember_summary_haiku": summary_usage,
        },
        "total_cost_usd": round(total_cost, 4),
        "execute_status": "pending_review",
        "auto_execute_attempted": False,
        "execute_cmd": args.execute_cmd,
        "rollback_cmd": args.rollback_cmd,
        "reversal_status": "OPEN",
        "reversed_at": None,
        "reversed_by": None,
    }

    append_log(entry)

    print(f"{'=' * 70}", flush=True)
    print(f"LOGGED: {LOG_FILE}", flush=True)
    print(f"decision_id: {decision_id}", flush=True)
    print(f"total_cost_usd: ${total_cost:.4f}", flush=True)
    print(f"reversal_status: OPEN", flush=True)
    print(f"  → reverse via: bash {Path(__file__).parent}/reverse.sh {decision_id}", flush=True)
    print(f"{'=' * 70}\n", flush=True)


if __name__ == "__main__":
    main()
