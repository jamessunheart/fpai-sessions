#!/usr/bin/env python3
"""Autonomous daily value delivery.

At 9am Athens time, pick one safe AI-advanceable item from core/STATE/NOW.md,
write a dated repo artifact, commit only that artifact, and notify James.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - Python without zoneinfo
    ZoneInfo = None  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NOW = REPO_ROOT / "core" / "STATE" / "NOW.md"
DEFAULT_OUT_DIR = REPO_ROOT / "core" / "BUILD" / "daily_value"
DEFAULT_DISABLE_FILE = Path(os.environ.get("AUTONOMOUS_DAILY_DISABLE_FILE", "/opt/fpai-build/.autonomous_daily_disabled"))
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
ATHENS_TZ = "Europe/Athens"

RESERVED_RE = re.compile(
    r"\b("
    r"move money|send money|wire|trade|trading|live execution|order|stop-fix|"
    r"outreach|email|reddit|hacker news|hn|instagram|twitter|x\.com|linkedin|"
    r"send\b|invite\b|hiring?|candidate|alice|deploy|production|secret|"
    r"delete|archive|retire|stop unit|systemctl|legal|compliance|price|pricing"
    r")\b",
    re.I,
)
AI_ACTIONABLE_RE = re.compile(
    r"\b("
    r"self-standing|state|spec|analysis|draft|research|benchmark|proof|"
    r"queue|registry|reconciler|surface|handler|repair|audit|map|clarity|"
    r"reduce external|sovereignty|daily state|build loop"
    r")\b",
    re.I,
)


@dataclass(frozen=True)
class Candidate:
    source: str
    text: str
    rank: int


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    candidate: Candidate | None
    artifact: Path | None
    commit_sha: str | None
    message: str


def athens_now() -> datetime:
    forced = os.environ.get("AUTONOMOUS_DAILY_NOW")
    if forced:
        dt = datetime.fromisoformat(forced.replace("Z", "+00:00"))
        if dt.tzinfo is None and ZoneInfo:
            dt = dt.replace(tzinfo=ZoneInfo(ATHENS_TZ))
        return dt
    if ZoneInfo:
        return datetime.now(ZoneInfo(ATHENS_TZ))
    return datetime.now(timezone.utc)


def strip_md(text: str) -> str:
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"[*_>#]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -|")


def display_path(path: Path, root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^##\s+.*{re.escape(heading)}.*$", text, re.I | re.M)
    if not match:
        return ""
    tail = text[match.end() :]
    next_heading = re.search(r"^##\s+", tail, re.M)
    return tail[: next_heading.start()] if next_heading else tail


def _table_rows(section: str, source: str, start_rank: int) -> list[Candidate]:
    out: list[Candidate] = []
    rank = start_rank
    for line in section.splitlines():
        if not line.startswith("|") or "---" in line or "Goal" in line:
            continue
        cols = [strip_md(col) for col in line.strip().strip("|").split("|")]
        if len(cols) < 2 or not cols[0].isdigit():
            continue
        text = " - ".join(col for col in cols[1:] if col)
        if text:
            out.append(Candidate(source=source, text=text, rank=rank))
            rank += 1
    return out


def extract_candidates(now_text: str) -> list[Candidate]:
    candidates: list[Candidate] = []

    priority = re.search(r"^###\s+Priority:\s*(.+)$", now_text, re.I | re.M)
    if priority:
        candidates.append(Candidate("CURRENT PRIORITY", strip_md(priority.group(1)), 10))

    one_thing = _section(now_text, "CURRENT PRIORITY")
    for line in one_thing.splitlines():
        raw = line.strip()
        if raw.startswith("- ") and "—" in raw:
            candidates.append(Candidate("CURRENT PRIORITY bullets", strip_md(raw), 20 + len(candidates)))

    goals = _section(now_text, "GOALS")
    candidates.extend(_table_rows(goals, "GOALS top 3", 100))

    loop = _section(now_text, "LOOP 38")
    for line in loop.splitlines():
        raw = line.strip()
        if raw.startswith("- **"):
            candidates.append(Candidate("LOOP 38 options", strip_md(raw), 200 + len(candidates)))

    latent = _section(now_text, "OPEN QUESTIONS")
    for line in latent.splitlines():
        raw = line.strip()
        if raw.startswith("- **"):
            candidates.append(Candidate("OPEN QUESTIONS latent", strip_md(raw), 300 + len(candidates)))

    seen: set[str] = set()
    unique: list[Candidate] = []
    for candidate in sorted(candidates, key=lambda item: item.rank):
        key = candidate.text.lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def is_safe_ai_advanceable(candidate: Candidate) -> bool:
    text = candidate.text
    if RESERVED_RE.search(text):
        return False
    return bool(AI_ACTIONABLE_RE.search(text))


def pick_candidate(candidates: Iterable[Candidate]) -> Candidate | None:
    for candidate in candidates:
        if is_safe_ai_advanceable(candidate):
            return candidate
    return None


def render_artifact(candidate: Candidate, *, generated_at: datetime, now_path: Path) -> str:
    day = generated_at.date().isoformat()
    safe_text = candidate.text.rstrip(".")
    return f"""# Autonomous Daily Value — {day}

Generated: {generated_at.isoformat()}
Source: `{display_path(now_path, REPO_ROOT)}`
Selected from: {candidate.source}

## Picked Priority

{safe_text}

## Why This Is Safe To Advance Without James

- It is repo-side analysis/drafting work.
- It does not move money, send outreach, deploy production, touch secrets, stop/delete services, or decide people/doctrine/treasury.
- It leaves a reversible artifact James or Ember can ignore, edit, or route into a later spec.

## Delivered Value

The useful next move is to reduce ambiguity around this priority before asking for more attention. Today, the system converts the priority into a concrete working brief:

- Current intent: {safe_text}
- AI-doable slice: identify the nearest proof, surface, or build-loop artifact that can move this forward without James.
- Human gate preserved: any public send, financial choice, production deploy, service stop/delete, or people decision remains blocked until James/Ember explicitly routes it.

## Next AI-Only Actions

1. Compare the next related build or state artifact against this priority.
2. Draft a narrow spec only if it can produce proof, revenue, clarity, or ease inside 30 days.
3. Log the proof path before building so tomorrow's run can continue from evidence instead of memory.

## Rollback

Delete this file or revert the commit. To stop future daily runs, create `/opt/fpai-build/.autonomous_daily_disabled`.
"""


def write_ops_ledger(path: Path, result: DeliveryResult) -> None:
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "autonomous_daily_value",
        "event": result.status,
        "detail": result.message,
        "cost": "$0",
        "artifact": str(result.artifact or ""),
        "commit": result.commit_sha or "",
        "surface": "auto-loop",
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")
    except OSError:
        pass


def run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo_root), *args], text=True, capture_output=True, check=False)


def commit_artifact(repo_root: Path, artifact: Path) -> str | None:
    rel = str(artifact.relative_to(repo_root))
    status = run_git(repo_root, ["status", "--porcelain", "--", rel])
    if status.returncode == 0 and not status.stdout.strip():
        return None
    run_git(repo_root, ["add", "--", rel])
    commit = run_git(
        repo_root,
        [
            "-c",
            "user.email=ember@fpai",
            "-c",
            "user.name=Ember",
            "commit",
            "-q",
            "-m",
            f"build: autonomous daily value {artifact.stem}",
            "--",
            rel,
        ],
    )
    if commit.returncode != 0:
        raise RuntimeError(commit.stderr.strip() or "git commit failed")
    sha = run_git(repo_root, ["rev-parse", "--short", "HEAD"])
    return sha.stdout.strip() if sha.returncode == 0 else None


def notify(repo_root: Path, message: str) -> None:
    script = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    subprocess.run([str(script), message], text=True, capture_output=True, check=False)


def deliver(
    *,
    repo_root: Path = REPO_ROOT,
    now_path: Path = DEFAULT_NOW,
    out_dir: Path = DEFAULT_OUT_DIR,
    disable_file: Path = DEFAULT_DISABLE_FILE,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    commit: bool = True,
    send_notify: bool = True,
    force: bool = False,
    require_athens_hour: int | None = None,
) -> DeliveryResult:
    if disable_file.exists():
        result = DeliveryResult("disabled", None, None, None, f"disabled by {disable_file}")
        write_ops_ledger(ops_ledger, result)
        return result

    generated_at = athens_now()
    if require_athens_hour is not None and generated_at.hour != require_athens_hour:
        result = DeliveryResult(
            "skipped_time",
            None,
            None,
            None,
            f"skipped at Athens hour {generated_at.hour}; waiting for {require_athens_hour}:00",
        )
        write_ops_ledger(ops_ledger, result)
        return result

    day = generated_at.date().isoformat()
    artifact = out_dir / f"{day}.md"
    if artifact.exists() and not force:
        result = DeliveryResult("skipped", None, artifact, None, f"daily value already exists for {day}: {artifact}")
        write_ops_ledger(ops_ledger, result)
        return result

    now_text = now_path.read_text(encoding="utf-8", errors="replace")
    candidates = extract_candidates(now_text)
    candidate = pick_candidate(candidates)
    if not candidate:
        result = DeliveryResult("no_candidate", None, None, None, "no safe AI-advanceable NOW.md priority found")
        write_ops_ledger(ops_ledger, result)
        if send_notify:
            notify(repo_root, "Autonomous daily value: no safe AI-advanceable NOW.md priority found.")
        return result

    out_dir.mkdir(parents=True, exist_ok=True)
    artifact.write_text(render_artifact(candidate, generated_at=generated_at, now_path=now_path), encoding="utf-8")

    commit_sha = None
    status = "written"
    if commit:
        commit_sha = commit_artifact(repo_root, artifact)
        status = "committed" if commit_sha else "unchanged"

    artifact_display = display_path(artifact, repo_root)
    message = f"Autonomous daily value delivered: {candidate.text} -> {artifact_display}"
    result = DeliveryResult(status, candidate, artifact, commit_sha, message)
    write_ops_ledger(ops_ledger, result)
    if send_notify:
        sha_part = f" commit {commit_sha}" if commit_sha else ""
        notify(repo_root, f"Autonomous daily value delivered{sha_part}: {candidate.text}<br><code>{artifact_display}</code>")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--now", type=Path, default=DEFAULT_NOW)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--disable-file", type=Path, default=DEFAULT_DISABLE_FILE)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--no-notify", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--require-athens-hour", type=int, choices=range(0, 24), metavar="HOUR")
    args = parser.parse_args()

    try:
        result = deliver(
            repo_root=args.repo_root,
            now_path=args.now,
            out_dir=args.out_dir,
            disable_file=args.disable_file,
            ops_ledger=args.ops_ledger,
            commit=not args.no_commit,
            send_notify=not args.no_notify,
            force=args.force,
            require_athens_hour=args.require_athens_hour,
        )
    except Exception as exc:
        print(f"autonomous daily value failed: {exc}")
        return 1

    print(result.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
