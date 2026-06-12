#!/usr/bin/env python3
"""
Autopilot orchestrator · MVP v1 · 2026-05-24
Invokes `claude` CLI (or future Qwen adapter) for a Kai-scoped reversible task.
Tracks cost · verifies reversibility · writes A/B-schema JSON log.

Spec: ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/spec_autopilot_cron_light.md
Trust-tier: 4.1 · Reversible only.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# === Constants ===
REPO_ROOT = Path("/Users/jamessunheart/FPAI_Cockpit")
HOME = Path.home()
RUN_DIR = HOME / ".config" / "fpai" / "autopilot"
QUEUE_FILE = RUN_DIR / "queue" / "pending.json"
RUNS_DIR = RUN_DIR / "runs"
STATE_DIR = RUN_DIR / "state"

# Model pricing per 1M tokens (USD) · published rates 2026-05-24
PRICING = {
    "claude-opus-4-7": {"in": 15.00, "out": 75.00},
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00},
    "claude-haiku-4-5-20251001": {"in": 1.00, "out": 5.00},
    "qwen3.7-max": {"in": 2.50, "out": 7.50},
    "qwen3-max": {"in": 2.50, "out": 7.50},  # actual API model ID (marketing name = 3.7-max)
    "gpt-5": {"in": 5.00, "out": 20.00},
    "gemini-2.5-pro": {"in": 1.25, "out": 5.00},
}

# Task prompts inline for MVP (v2: move to queue/tasks/{slug}.md)
TASKS = {
    "audit-archive": """Read every immediate subdirectory of /Users/jamessunheart/FPAI_Cockpit/_archive/projects/.
For each subdir, examine the top-level README.md (if present) and run `git log --oneline -3 -- {subdir}` to get the 3 most recent commits.
Produce a markdown table with these columns:
  project | last_touched | apparent_purpose | recommendation (KEEP / DELETE / MERGE-INTO-X) | reasoning_one_sentence

Do not modify any files. Return ONLY the markdown table — no preamble, no closing remarks.""",

    "dep-analysis": """Walk every requirements.txt under /Users/jamessunheart/FPAI_Cockpit/SERVICES/.
For each, identify: (1) likely-unused imports (cross-check with the service's main.py if obvious), (2) pinned-too-loose deps (e.g. plain `requests` without version bound), (3) deps that appear in only one service (potential orphans).
Produce a markdown table:
  service | issue_type | dep_name | recommendation | reasoning

Do not modify any files. Return ONLY the markdown table.""",
}


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    p = PRICING.get(model)
    if not p:
        log(f"WARN: no pricing for {model}, falling back to opus rates")
        p = PRICING["claude-opus-4-7"]
    return (tokens_in * p["in"] + tokens_out * p["out"]) / 1_000_000


def git_status_short() -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--short"],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception as e:
        log(f"WARN: git status failed: {e}")
        return ""


def load_queue() -> list:
    if not QUEUE_FILE.exists():
        return []
    with open(QUEUE_FILE) as f:
        data = json.load(f)
    return data.get("pending", [])


def pick_task(task_arg: str | None, model: str) -> dict | None:
    queue = load_queue()
    if task_arg:
        for t in queue:
            if t.get("task_slug") == task_arg:
                return t
        # Allow ad-hoc not-in-queue
        if task_arg in TASKS:
            return {"task_slug": task_arg, "task_class": "ad_hoc", "task_name": task_arg}
        return None
    # Pick first matching model preference
    for t in queue:
        if t.get("preferred_model", model) == model:
            return t
    return queue[0] if queue else None


MODEL_ALIASES = {
    "claude-opus-4-7": "opus",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5-20251001": "haiku",
}

QWEN_KEY_FILE = HOME / ".config" / "fpai" / "qwen" / "api.token"
QWEN_ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"


def _call_claude_cli(prompt: str, model: str) -> tuple[str, dict]:
    """Invoke claude CLI. Return (output_text, usage_dict)."""
    # claude CLI (Node/commander.js): --model MUST come before -p flag
    cmd = ["claude"]
    if model.startswith("claude-") or model in MODEL_ALIASES.values():
        alias = MODEL_ALIASES.get(model, model)
        cmd.extend(["--model", alias])
    cmd.extend(["-p", "--output-format", "json"])
    cmd.append(prompt)  # prompt MUST be last (REMAINDER)

    log(f"invoking: claude --model {MODEL_ALIASES.get(model, model)} -p <{len(prompt)} chars>")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return ("ERROR: claude CLI timed out after 600s", {"tokens_in": 0, "tokens_out": 0, "error": "timeout"})

    if result.returncode != 0:
        log(f"claude exit {result.returncode}: {result.stderr[:500]}")
        return (result.stderr or result.stdout, {"tokens_in": 0, "tokens_out": 0, "error": f"exit_{result.returncode}"})

    try:
        data = json.loads(result.stdout)
        output_text = data.get("result", data.get("content", result.stdout))
        usage = data.get("usage", {})
        tokens_in = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        tokens_out = usage.get("output_tokens", usage.get("completion_tokens", 0))
        return (output_text, {"tokens_in": tokens_in, "tokens_out": tokens_out})
    except (json.JSONDecodeError, KeyError):
        text = result.stdout
        return (text, {"tokens_in": len(prompt) // 4, "tokens_out": len(text) // 4})


def _call_qwen_dashscope(prompt: str, model: str) -> tuple[str, dict]:
    """Invoke Qwen via DashScope intl OpenAI-compat endpoint (curl subprocess — urllib has SSL issues on macOS)."""
    try:
        key = QWEN_KEY_FILE.read_text().strip()
    except FileNotFoundError:
        return ("", {"tokens_in": 0, "tokens_out": 0, "error": f"qwen key missing at {QWEN_KEY_FILE}"})

    # Qwen API uses "qwen3-max" as model ID (not "qwen3.7-max" — that's marketing name)
    api_model = "qwen3-max" if "qwen" in model.lower() else model
    body = json.dumps({
        "model": api_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16000,
    })
    cmd = [
        "curl", "-sS", "-X", "POST", QWEN_ENDPOINT,
        "-H", f"Authorization: Bearer {key}",
        "-H", "Content-Type: application/json",
        "-d", body,
    ]
    log(f"invoking: curl POST DashScope intl model={api_model} <{len(prompt)} chars>")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return ("ERROR: qwen curl timeout 600s", {"tokens_in": 0, "tokens_out": 0, "error": "timeout"})
    if r.returncode != 0:
        return (r.stderr, {"tokens_in": 0, "tokens_out": 0, "error": f"curl_exit_{r.returncode}"})

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return (r.stdout, {"tokens_in": 0, "tokens_out": 0, "error": "non-json-response"})

    if "error" in data:
        return ("", {"tokens_in": 0, "tokens_out": 0, "error": f"qwen API: {str(data['error'])[:200]}"})

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return ("", {"tokens_in": 0, "tokens_out": 0, "error": f"unexpected shape: {str(data)[:200]}"})

    usage = data.get("usage", {})
    return (text, {
        "tokens_in": usage.get("prompt_tokens", 0),
        "tokens_out": usage.get("completion_tokens", 0),
    })


def invoke_model(prompt: str, model: str, dry_run: bool) -> tuple[str, dict]:
    """Route to the right model adapter."""
    if dry_run:
        log(f"DRY-RUN: would invoke {model} with prompt of {len(prompt)} chars")
        return ("[DRY-RUN] no actual invocation", {"tokens_in": 0, "tokens_out": 0})
    if "qwen" in model.lower():
        return _call_qwen_dashscope(prompt, model)
    # default to Claude (including opus/sonnet/haiku aliases)
    return _call_claude_cli(prompt, model)


# Backward-compat alias
invoke_claude = invoke_model


def write_run_json(run_data: dict, run_id: str) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{run_id}.json"
    with open(path, "w") as f:
        json.dump(run_data, f, indent=2)
    return path


def write_transcript(output: str, run_id: str) -> Path:
    path = RUNS_DIR / f"{run_id}.transcript.md"
    with open(path, "w") as f:
        f.write(f"# Run {run_id}\n\n## Output\n\n{output}\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--budget-usd", type=float, default=5.00)
    ap.add_argument("--task", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reversible-only", action="store_true")
    ap.add_argument("--no-git-push", action="store_true")
    ap.add_argument("--no-identity-writes", action="store_true")
    ap.add_argument("--no-treasury", action="store_true")
    ap.add_argument("--no-publish", action="store_true")
    args = ap.parse_args()

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Snapshot pre-run state for reversibility check
    pre_status = git_status_short()

    # Pick task
    task = pick_task(args.task, args.model)
    if not task:
        log("FATAL: no task available (queue empty + no --task specified)")
        sys.exit(2)

    task_slug = task["task_slug"]
    prompt = TASKS.get(task_slug)
    if not prompt:
        log(f"FATAL: no prompt template for task_slug={task_slug}")
        sys.exit(2)

    log(f"task={task_slug} model={args.model} budget=${args.budget_usd:.2f} dry_run={args.dry_run}")

    started_at = datetime.now(timezone.utc)
    t0 = time.time()

    output, usage = invoke_claude(prompt, args.model, args.dry_run)

    duration_s = round(time.time() - t0, 1)
    ended_at = datetime.now(timezone.utc)

    tokens_in = usage.get("tokens_in", 0)
    tokens_out = usage.get("tokens_out", 0)
    cost = round(estimate_cost(args.model, tokens_in, tokens_out), 4)

    # Reversibility check
    post_status = git_status_short()
    reversibility_verified = (pre_status == post_status)
    if not reversibility_verified:
        log(f"WARN: git status diverged · pre=[{pre_status[:200]}] post=[{post_status[:200]}]")

    # Outcome
    if args.dry_run:
        outcome = "dry_run"
    elif "error" in usage:
        outcome = "model_api_error"
    elif cost > args.budget_usd:
        outcome = "aborted_budget"
    elif not reversibility_verified:
        outcome = "reversibility_check_failed"
    else:
        outcome = "success"

    # Build run JSON
    run_id = f"{args.date}_{args.model}_{task_slug}"
    run_data = {
        "schema_version": "1.0",
        "run_id": run_id,
        "date": args.date,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_s": duration_s,
        "model": args.model,
        "model_provider": (
            "anthropic" if args.model.startswith("claude-")
            else "alibaba" if "qwen" in args.model.lower()
            else "openai" if "gpt" in args.model.lower()
            else "google" if "gemini" in args.model.lower()
            else "other"
        ),
        "task_name": task.get("task_name", task_slug),
        "task_slug": task_slug,
        "task_class": task.get("task_class", "audit_inventory"),
        "task_queued_by": task.get("queued_by", "manual"),
        "task_queued_at": task.get("queued_at"),
        "cost_usd": cost,
        "cost_breakdown": {
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "input_rate_per_1m": PRICING.get(args.model, PRICING["claude-opus-4-7"])["in"],
            "output_rate_per_1m": PRICING.get(args.model, PRICING["claude-opus-4-7"])["out"],
        },
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "outcome": outcome,
        "outcome_detail": output[:500] if outcome != "success" else "",
        "reversibility_verified": reversibility_verified,
        "budget_ceiling_usd": args.budget_usd,
        "budget_breach": cost > args.budget_usd,
        "dry_run": args.dry_run,
    }

    # Write artifacts
    json_path = write_run_json(run_data, run_id)
    transcript_path = write_transcript(output, run_id)

    log(f"run complete: outcome={outcome} cost=${cost:.4f} duration={duration_s}s tokens_in={tokens_in} tokens_out={tokens_out}")
    log(f"  run JSON: {json_path}")
    log(f"  transcript: {transcript_path}")

    # Auto-disable on critical failure
    if outcome == "reversibility_check_failed" or outcome == "aborted_budget":
        disabled_flag = RUN_DIR / ".disabled"
        disabled_flag.write_text(f"auto-disabled {datetime.now(timezone.utc).isoformat()} outcome={outcome} run_id={run_id}\n")
        log(f"AUTOPILOT DISABLED · flag at {disabled_flag}")

    sys.exit(0 if outcome in ("success", "dry_run") else 1)


if __name__ == "__main__":
    main()
