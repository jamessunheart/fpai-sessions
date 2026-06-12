#!/usr/bin/env python3
"""Rung 4 builder-loop watcher.

Open build intents become generated specs, one Codex build, one review file,
and one Telegram review notification. The loop stops there; merge/reject stays
with James.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.spec import draft as spec_draft

INTENTS_DIR = REPO_ROOT / "core" / "BUILD" / "intents"
SPECS_DIR = REPO_ROOT / "core" / "BUILD" / "specs"
RESULTS_DIR = REPO_ROOT / "core" / "BUILD" / "results"
REVIEWS_DIR = REPO_ROOT / "core" / "BUILD" / "reviews"
PROOF_LOG = REPO_ROOT / "core" / "BUILD" / "PROOF_LOG.md"
RUN_CODEX = REPO_ROOT / "tools" / "build_loop" / "run_codex.sh"

Runner = Callable[[Path], subprocess.CompletedProcess[str]]
Sender = Callable[[str], tuple[bool, str]]


def watch_once(
    intents_dir: Path | str = INTENTS_DIR,
    specs_dir: Path | str = SPECS_DIR,
    reviews_dir: Path | str = REVIEWS_DIR,
    *,
    results_dir: Path | str = RESULTS_DIR,
    proof_log: Path | str = PROOF_LOG,
    dry_run: bool = False,
    runner: Runner | None = None,
    sender: Sender | None = None,
    now_fn: Callable[[], dt.datetime] | None = None,
) -> list[str]:
    """Process every `status: open` build intent once."""
    if os.environ.get("FPAI_BUILD_LOOP_DISABLE") == "1":
        return []
    intents_path = Path(intents_dir)
    specs_path = Path(specs_dir)
    reviews_path = Path(reviews_dir)
    results_path = Path(results_dir)
    proof_path = Path(proof_log)
    now = now_fn or _utc_now
    run = runner or _run_codex
    notify = sender or _send_tg
    outcomes: list[str] = []

    for intent_path in sorted(intents_path.glob("intent-*.md")) if intents_path.exists() else []:
        intent = _read_intent(intent_path)
        if intent.get("status") != "open":
            continue
        ident = intent["id"]
        slug = intent["slug"]
        spec_path = specs_path / f"{ident}-{slug}.md"
        review_path = reviews_path / f"{ident}-{slug}.review.md"
        result_path = results_path / f"{ident}.result.md"

        if dry_run:
            outcomes.append(f"would build {slug}")
            continue

        specs_path.mkdir(parents=True, exist_ok=True)
        reviews_path.mkdir(parents=True, exist_ok=True)
        results_path.mkdir(parents=True, exist_ok=True)
        _write_generated_spec(intent, spec_path)
        _update_intent(intent_path, {"status": "spec-drafted", "spec_path": _rel(spec_path)})
        _update_intent(intent_path, {"status": "building"})

        try:
            completed = run(spec_path)
            failed = completed.returncode != 0
            output = (completed.stdout or "") + (completed.stderr or "")
        except Exception as exc:  # subprocess failure is a safe terminal state.
            failed = True
            output = f"{type(exc).__name__}: {exc}"

        if failed:
            if not result_path.exists():
                result_path.write_text(_failure_result(ident, output, now()), encoding="utf-8")
            review_path.write_text(_render_review(
                intent=intent,
                result_text=result_path.read_text(encoding="utf-8", errors="ignore"),
                test_status="tests failed",
                recommendation="reject or reset after fixing the build failure",
                ran_at=now(),
            ), encoding="utf-8")
            _update_intent(intent_path, {
                "status": "build-failed",
                "review_path": _rel(review_path),
            })
            notify(f"Built `{slug}` — build failed. Merge? ⚡ Reply 'reject {ident}'.")
            outcomes.append(f"build-failed:{ident}")
            continue

        result_text = result_path.read_text(encoding="utf-8", errors="ignore") if result_path.exists() else output
        test_status = _test_status(result_text)
        review_path.write_text(_render_review(
            intent=intent,
            result_text=result_text,
            test_status=test_status,
            recommendation="merge only after James reviews the diff",
            ran_at=now(),
        ), encoding="utf-8")
        _update_intent(intent_path, {
            "status": "review-pending",
            "review_path": _rel(review_path),
        })
        _append_proof(proof_path, intent, now())
        notify(f"Built `{slug}` — {test_status}. Merge? ⚡ Reply 'merge {ident}' or 'reject {ident}'.")
        outcomes.append(f"review-pending:{ident}")
    return outcomes


def _read_intent(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    frontmatter, body = _split_frontmatter(text)
    data = _parse_frontmatter(frontmatter)
    ident = data.get("id") or _id_from_filename(path)
    slug = data.get("slug") or _slug_from_filename(path)
    description = body.split("\n", 1)[-1].strip() if body.startswith("# ") else body.strip()
    return {
        "path": str(path),
        "id": ident,
        "slug": slug,
        "status": data.get("status", "open"),
        "title": slug.replace("-", " "),
        "next": description or data.get("raw", slug),
        "stream": data.get("stream", "builder-loop"),
        "weight": data.get("weight", "rung4"),
        "notes": data.get("raw", description or slug),
        "dependency": data.get("dependency", "voice/text build intent"),
        "landing_target": data.get("landing_target", "feat/headless-build"),
    }


def _write_generated_spec(intent: dict[str, str], spec_path: Path) -> None:
    rendered = spec_draft.render_spec(intent)
    spec_path.write_text(
        "---\n"
        f"id: {intent['id']}\n"
        f"slug: {intent['slug']}\n"
        "status: drafted\n"
        "source: build_loop_watcher\n"
        f"source_intent: {_rel(Path(intent['path']))}\n"
        "---\n\n"
        f"{rendered}",
        encoding="utf-8",
    )


def _run_codex(spec_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(RUN_CODEX), "--spec", str(spec_path)],
        text=True,
        capture_output=True,
        timeout=int(os.environ.get("FPAI_BUILD_LOOP_TIMEOUT", "3600")),
        check=False,
    )


def _send_tg(message: str) -> tuple[bool, str]:
    try:
        from tools.decisions import send_tg_digest
        return send_tg_digest.send_to_telegram(message, send_tg_digest.load_creds())
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _render_review(
    *,
    intent: dict[str, str],
    result_text: str,
    test_status: str,
    recommendation: str,
    ran_at: dt.datetime,
) -> str:
    summary = _summarize_result(result_text)
    return (
        f"# Build review - {intent['slug']}\n\n"
        f"- Intent: `{intent['id']}`\n"
        f"- Status: {test_status}\n"
        f"- Ran: {ran_at.isoformat().replace('+00:00', 'Z')}\n"
        f"- Recommendation: {recommendation}\n\n"
        "## Diff Summary\n"
        f"{summary}\n\n"
        "## Tests\n"
        f"{test_status}\n\n"
        "## Risks\n"
        "- Review the generated branch diff before merge.\n"
        "- No deploy, money movement, secret access, or approval was performed by this watcher.\n\n"
        "## Merge Gate\n"
        f"James can reply `merge {intent['id']}` or `reject {intent['id']}` after review.\n"
    )


def _failure_result(ident: str, output: str, ran_at: dt.datetime) -> str:
    return (
        f"# Codex build result - {ident}\n"
        f"_ran: {ran_at.isoformat().replace('+00:00', 'Z')}_\n\n"
        "```text\n"
        f"{output.strip()}\n"
        "```\n"
    )


def _test_status(result_text: str) -> str:
    low = result_text.lower()
    if "failed" in low or "error:" in low or "exited non-zero" in low:
        return "tests failed"
    return "tests green"


def _summarize_result(result_text: str, max_lines: int = 18) -> str:
    lines = [line.rstrip() for line in result_text.splitlines() if line.strip()]
    if not lines:
        return "- Result file was empty; inspect the build worktree."
    clipped = lines[:max_lines]
    return "\n".join(f"- {line[:180]}" for line in clipped)


def _append_proof(proof_log: Path, intent: dict[str, str], now: dt.datetime) -> None:
    proof_log.parent.mkdir(parents=True, exist_ok=True)
    stamp = now.isoformat().replace("+00:00", "Z")
    proof_log.open("a", encoding="utf-8").write(
        f"- [{stamp}] · {intent['stream']} · builder loop: {intent['slug']} · "
        f"REVERSE: git branch -D build/{intent['id']}\n"
    )


def _update_intent(path: Path, updates: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    frontmatter, body = _split_frontmatter(text)
    data = _parse_frontmatter(frontmatter)
    data.update(updates)
    ordered_keys = list(dict.fromkeys([*data.keys(), *updates.keys()]))
    rendered = "---\n" + "\n".join(f"{key}: {data[key]}" for key in ordered_keys) + "\n---\n"
    path.write_text(rendered + body, encoding="utf-8")


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return "", text
    return parts[1], parts[2]


def _parse_frontmatter(frontmatter: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def _id_from_filename(path: Path) -> str:
    match = re.match(r"(intent-\d{8}-[0-9a-f]{6})-", path.stem)
    return match.group(1) if match else path.stem


def _slug_from_filename(path: Path) -> str:
    match = re.match(r"intent-\d{8}-[0-9a-f]{6}-(.+)$", path.stem)
    return match.group(1) if match else path.stem


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def _json_default(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Rung 4 build loop once.")
    parser.add_argument("--intents-dir", type=Path, default=INTENTS_DIR)
    parser.add_argument("--specs-dir", type=Path, default=SPECS_DIR)
    parser.add_argument("--reviews-dir", type=Path, default=REVIEWS_DIR)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--proof-log", type=Path, default=PROOF_LOG)
    parser.add_argument("--dry-run", action="store_true", help="print what would run; write nothing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    outcomes = watch_once(
        args.intents_dir,
        args.specs_dir,
        args.reviews_dir,
        results_dir=args.results_dir,
        proof_log=args.proof_log,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps({"outcomes": outcomes, "dry_run": args.dry_run}, default=_json_default))
    elif args.dry_run:
        print("\n".join(outcomes) if outcomes else "No open intents.")
    else:
        print(f"build_loop_watcher: processed={len(outcomes)}")
        for outcome in outcomes:
            print(f"  {outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
