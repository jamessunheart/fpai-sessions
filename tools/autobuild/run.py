#!/usr/bin/env python3
"""Invoke a guarded, flat-rate headless builder for one approved spec."""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


HOME = Path.home()
REPO = Path(__file__).resolve().parents[2]
HANDOFF = REPO / "docs" / "codex" / "HANDOFF.md"
COST_GUARD = HOME / ".local" / "bin" / "cost-guard"
AUTOBUILD_DISABLED = HOME / ".config" / "fpai" / "autobuild" / ".disabled"

RESERVED_WORDS = (
    "move money",
    "money movement",
    "transfer funds",
    "send outreach",
    "send message",
    "public send",
    "deploy production",
    "production deploy",
    "touch secrets",
    "secret",
    "credential",
    "delete service",
    "stop service",
    "archive service",
    "irreversible",
    "hire",
    "fire",
    "treasury",
    "doctrine",
    "offer decision",
)

SAFE_CONTEXT_HINTS = (
    "do not",
    "does not",
    "don't",
    "never",
    "forbidden",
    "files forbidden",
    "may not",
    "must not",
    "without",
    "no ",
    "rollback",
)


def rel(path: Path, repo: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def status_files(repo: Path) -> set[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    files: set[str] = set()
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.add(path.strip())
    return files


def discover_builder(choice: str) -> tuple[str, list[str]]:
    if choice in {"auto", "claude"}:
        claude = shutil.which("claude")
        if claude:
            return "claude", [
                claude,
                "--permission-mode",
                "acceptEdits",
                "--add-dir",
                str(REPO),
                "-p",
            ]
        if choice == "claude":
            raise FileNotFoundError("claude CLI not found")

    codex = shutil.which("codex")
    if codex and choice in {"auto", "codex"}:
        return "codex", [codex, "exec", "--cd", str(REPO)]
    if choice == "codex":
        raise FileNotFoundError("codex CLI not found")
    raise FileNotFoundError("no flat-rate headless builder found (wanted claude -p or codex exec)")


def build_prompt(spec: Path, metered: bool) -> str:
    metered_line = (
        "A metered builder was explicitly allowed for this invocation, but still prefer flat-rate if available."
        if metered
        else "Do not use any metered API path; use only the flat-rate local plan/CLI context."
    )
    spec_rel = rel(spec, REPO)
    return f"""Read `AGENTS.md`, then `docs/codex/README.md`, `docs/codex/AI_PROTOCOLS.md`, `docs/codex/PHONE_HANDOFF.md`, `docs/codex/HANDOFF.md`, `docs/codex/INTENT_BUILDSTREAM.md`, then the target spec `{spec_rel}`.
Work ONLY on the branch named in that spec; touch only files-allowed, never files-forbidden.
Build to the Definition of Done, run the tests, then update the 📥 lane in `docs/codex/HANDOFF.md` with: files changed · summary · tests · risks · rollback.
Do NOT merge or move money/deploy/secrets — show James the diff first.
Reserved Class work escalates instead of executing: money movement, outreach sends, production deploys, secrets, irreversible service deletion/stops, doctrine/treasury/people/offer decisions.
{metered_line}
"""


def command_for(builder: str, prompt: str) -> list[str]:
    _name, prefix = discover_builder(builder)
    return prefix + [prompt]


def reserved_hits(spec_text: str) -> list[str]:
    hits: list[str] = []
    in_forbidden = False
    for raw_line in spec_text.splitlines():
        line = raw_line.strip()
        low = line.lower()
        if re.match(r"^#+\s*files forbidden\b", low):
            in_forbidden = True
            continue
        if in_forbidden and re.match(r"^#+\s+", low):
            in_forbidden = False
        if in_forbidden or any(hint in low for hint in SAFE_CONTEXT_HINTS):
            continue
        for word in RESERVED_WORDS:
            if word in low:
                hits.append(f"{word}: {line}")
    return hits


def run_cost_guard() -> tuple[bool, str]:
    if AUTOBUILD_DISABLED.exists():
        return False, f"autobuild disabled: {AUTOBUILD_DISABLED}"
    if not COST_GUARD.exists():
        return False, f"cost-guard missing: {COST_GUARD}"
    proc = subprocess.run(
        [str(COST_GUARD), "autobuild"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    detail = (proc.stdout.strip() or proc.stderr.strip() or f"exit {proc.returncode}").strip()
    return proc.returncode == 0, detail


def handoff_summary(output: str, max_lines: int = 10) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return "builder produced no text output"
    tail = lines[-max_lines:]
    return " / ".join(tail)


def append_handoff(
    spec: Path,
    command: list[str],
    returncode: int,
    before: set[str],
    after: set[str],
    output: str,
    dry_run: bool,
) -> str:
    changed = sorted(after - before) or sorted(after)
    changed_text = ", ".join(changed) if changed else "none detected"
    status = "dry-run" if dry_run else ("done" if returncode == 0 else f"builder exited {returncode}")
    stamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d · %H:%M %Z")
    entry = f"""### {stamp} · SPEC_headless-build autobuild runner · branch `feat/headless-build`
- Status: {status}
- Files changed: {changed_text}
- Summary: invoked `{rel(spec, REPO)}` through a guarded flat-rate headless builder command; captured result for review.
- Tests: command `{shell_join(command)}`; result `{returncode}`; output tail: {handoff_summary(output)}
- Risks: headless builder output is summarized from stdout/stderr; review `git diff` before merge. Reserved Class actions remain blocked/escalated by prompt and preflight.
- Rollback: delete `tools/autobuild/`; revert this HANDOFF note.
- Questions for Ember/James: review the diff before any merge; no money/deploy/secrets action was taken.

"""
    text = HANDOFF.read_text(encoding="utf-8")
    lane = "## 📥 CODEX → EMBER"
    lane_pos = text.find(lane)
    if lane_pos == -1:
        raise RuntimeError(f"handoff lane not found in {HANDOFF}")
    first_entry = text.find("\n### ", lane_pos)
    if first_entry == -1:
        insert_at = text.find("\n## ", lane_pos + len(lane))
        if insert_at == -1:
            insert_at = len(text)
    else:
        insert_at = first_entry + 1
    HANDOFF.write_text(text[:insert_at] + entry + text[insert_at:], encoding="utf-8")
    return changed_text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a guarded flat-rate headless build from a spec.")
    ap.add_argument("--spec", type=Path, required=True, help="path to docs/codex/specs/SPEC_<x>.md")
    ap.add_argument("--builder", choices=("auto", "claude", "codex"), default="auto")
    ap.add_argument("--metered", action="store_true", help="explicitly allow a metered API path if a future builder needs one")
    ap.add_argument("--dry-run", action="store_true", help="print the command that would run; execute and write nothing")
    ap.add_argument("--no-handoff", action="store_true", help="do not append the captured result to docs/codex/HANDOFF.md")
    args = ap.parse_args(argv)

    spec = args.spec if args.spec.is_absolute() else REPO / args.spec
    if not spec.exists():
        print(f"autobuild: missing spec: {spec}", file=sys.stderr)
        return 2
    spec_text = read_text(spec)
    hits = reserved_hits(spec_text)
    if hits:
        print("autobuild: Reserved Class language found outside guardrail sections; escalate instead.")
        for hit in hits:
            print(f"- {hit}")
        return 0

    try:
        command = command_for(args.builder, build_prompt(spec, args.metered))
    except FileNotFoundError as exc:
        print(f"autobuild: {exc}", file=sys.stderr)
        return 2

    print(shell_join(command))
    if args.dry_run:
        print("autobuild: dry-run only; executed nothing and wrote nothing.")
        return 0

    allowed, guard_detail = run_cost_guard()
    if not allowed:
        print(f"autobuild: cost-guard blocked: {guard_detail}")
        return 0
    print(f"autobuild: cost-guard passed: {guard_detail or 'passed'}")

    before = status_files(REPO)
    proc = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False)
    output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    if output.strip():
        print(output.rstrip())
    after = status_files(REPO)

    if not args.no_handoff:
        changed_text = append_handoff(spec, command, proc.returncode, before, after, output, False)
        print(f"autobuild: handoff updated; changed files: {changed_text}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
