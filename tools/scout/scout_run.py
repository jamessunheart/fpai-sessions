#!/usr/bin/env python3
"""World Scout activation runner.

This is the outward-eyes pipe. It is deliberately guarded: one run per day,
hard cost cap, kill switch, and all-or-nothing note writes. The existing
`tools/scout/scout.py` remains the local verdict/ranking engine.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HOME = Path.home()
DEFAULT_VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/FPOS/Full Potential OS"
DEFAULT_CONFIG = HOME / ".config" / "fpai" / "scout"
DEFAULT_PROMPT = DEFAULT_CONFIG / "prompt.md"
DEFAULT_CURSOR = DEFAULT_CONFIG / "last_run.txt"
DEFAULT_DISABLED = DEFAULT_CONFIG / ".disabled"
NEWS_REL = Path("00_MEMORY/NEWS FOR YOU.md")
GROWTH_REL = Path("00_MEMORY/AI GROWTH FEED.md")
COST_REL = Path("00_MEMORY/COST LEDGER.md")  # canonical ledger lives in 00_MEMORY — never create a root duplicate
PROOF_REL = Path("00_MEMORY/PROOF LOG.md")
COST_CAP_USD = 1.50
MIN_NEWS = 3
MIN_GROWTH = 2


@dataclasses.dataclass(frozen=True)
class ScoutResult:
    status: str
    date: str
    cost_usd: float
    wrote: list[Path]
    reason: str = ""


class ScoutRunError(RuntimeError):
    """Scout run failed before any live note write."""


def today_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def run_if_due(
    *,
    vault: Path | str = DEFAULT_VAULT,
    prompt_path: Path | str = DEFAULT_PROMPT,
    config_dir: Path | str = DEFAULT_CONFIG,
    cursor_path: Path | str = DEFAULT_CURSOR,
    disabled_path: Path | str = DEFAULT_DISABLED,
    fixture_path: Path | str | None = None,
    force: bool = False,
    dry_run: bool = False,
    today: str | None = None,
) -> ScoutResult:
    """Run the scout if not disabled and not already run today."""
    run_date = today or today_utc()
    config = Path(config_dir)
    cursor = Path(cursor_path)
    disabled = Path(disabled_path)
    vault_path = Path(vault)

    if os.environ.get("SCOUT_DISABLE") == "1" or disabled.exists():
        return ScoutResult("disabled", run_date, 0.0, [], "kill switch active")
    if not force and cursor.exists() and cursor.read_text(encoding="utf-8").strip() == run_date:
        return ScoutResult("skipped", run_date, 0.0, [], "already ran today")

    prompt = Path(prompt_path).read_text(encoding="utf-8") if Path(prompt_path).exists() else ""
    payload = load_research_payload(prompt, fixture_path=fixture_path)
    validate_payload(payload)
    cost = float(payload.get("cost_usd", 0.0))
    if cost > COST_CAP_USD:
        raise ScoutRunError(f"cost cap exceeded: ${cost:.2f} > ${COST_CAP_USD:.2f}")

    rendered = render_outputs(payload, run_date, vault_path=vault_path)
    targets = {
        vault_path / NEWS_REL: rendered["news"],
        vault_path / GROWTH_REL: rendered["growth"],
        vault_path / COST_REL: render_append(vault_path / COST_REL, cost_line(cost, run_date)),
        vault_path / PROOF_REL: render_append(vault_path / PROOF_REL, proof_line(payload, cost, run_date)),
    }
    if dry_run:
        return ScoutResult("dry-run", run_date, cost, list(targets))

    atomic_write_many(targets)
    config.mkdir(parents=True, exist_ok=True)
    cursor.write_text(run_date + "\n", encoding="utf-8")
    return ScoutResult("live", run_date, cost, list(targets))


def load_research_payload(prompt: str, *, fixture_path: Path | str | None = None) -> dict[str, Any]:
    """Load model output from a fixture or explicit command.

    `SCOUT_MODEL_CMD` is an intentionally explicit integration seam: the command
    receives the prompt on stdin and must return JSON with news/growth/cost_usd.
    If neither fixture nor command exists, fail closed instead of pretending.
    """
    fixture = fixture_path or os.environ.get("SCOUT_FIXTURE_JSON")
    if fixture:
        return json.loads(Path(fixture).read_text(encoding="utf-8"))
    command = os.environ.get("SCOUT_MODEL_CMD")
    if not command:
        raise ScoutRunError("no scout provider configured; set SCOUT_MODEL_CMD or pass --fixture")
    if not prompt.strip():
        raise ScoutRunError("missing scout prompt; expected ~/.config/fpai/scout/prompt.md or --prompt")
    completed = subprocess.run(
        command,
        input=prompt,
        text=True,
        shell=True,
        capture_output=True,
        timeout=180,
    )
    if completed.returncode != 0:
        raise ScoutRunError(completed.stderr.strip() or f"provider exited {completed.returncode}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ScoutRunError("provider returned non-JSON output") from exc


def validate_payload(payload: dict[str, Any]) -> None:
    news = payload.get("news")
    growth = payload.get("growth")
    if not isinstance(news, list) or len(news) < MIN_NEWS:
        raise ScoutRunError(f"expected at least {MIN_NEWS} news items")
    if not isinstance(growth, list) or len(growth) < MIN_GROWTH:
        raise ScoutRunError(f"expected at least {MIN_GROWTH} AI growth candidates")
    for lane, rows in (("news", news), ("growth", growth)):
        for idx, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise ScoutRunError(f"{lane} item {idx} is not an object")
            title = str(row.get("title") or row.get("name") or "").strip()
            url = str(row.get("url") or "").strip()
            if not title or not url.startswith(("http://", "https://")):
                raise ScoutRunError(f"{lane} item {idx} needs title/name and http(s) url")


def render_outputs(payload: dict[str, Any], run_date: str, *, vault_path: Path) -> dict[str, str]:
    return {
        "news": render_news(payload["news"], run_date, existing=_read_existing(vault_path / NEWS_REL)),
        "growth": render_growth(payload["growth"], run_date, existing=_read_existing(vault_path / GROWTH_REL)),
    }


def render_news(items: list[dict[str, Any]], run_date: str, *, existing: str = "") -> str:
    lines = frontmatter(existing, run_date) + [
        "# NEWS FOR YOU",
        "",
        "Generated by World Scout. Research-read only; nothing here has been sent or acted on.",
        "",
        "## Linked Items",
        "",
    ]
    for item in items:
        title = _clean(str(item.get("title", "")))
        url = str(item.get("url", "")).strip()
        why = _clean(str(item.get("why") or item.get("summary") or "review relevance"))
        lines.append(f"- [{title}]({url}) - {why}")
    lines.append("")
    return "\n".join(lines)


def render_growth(items: list[dict[str, Any]], run_date: str, *, existing: str = "") -> str:
    lines = frontmatter(existing, run_date) + [
        "# AI GROWTH FEED",
        "",
        "Generated by World Scout. Candidate adoption stays review-gated.",
        "",
        "## Proposed adoptions",
        "",
    ]
    for item in items:
        name = _clean(str(item.get("name") or item.get("title") or "Unnamed candidate"))
        url = str(item.get("url", "")).strip()
        why = _clean(str(item.get("why") or item.get("summary") or "review candidate"))
        use = _clean(str(item.get("proposed_use") or item.get("use") or "TODO(review): define use"))
        score = str(item.get("score", "TODO(review)")).strip()
        lines.extend(
            [
                f"- **{name}**",
                f"  - Source: {url}",
                f"  - Why it matters: {why}",
                f"  - Proposed use: {use}",
                f"  - Score: {score}",
            ]
        )
    lines.extend(["", "## Scanned", "", f"- {run_date} - World Scout"])
    return "\n".join(lines)


def cost_line(cost_usd: float, run_date: str) -> str:
    return f"- {run_date} - World Scout run - ${cost_usd:.2f} - cap ${COST_CAP_USD:.2f} - source: scout_run"


def proof_line(payload: dict[str, Any], cost_usd: float, run_date: str) -> str:
    return (
        f"- {run_date} - [Game] - Intent solved: World Scout outward feeds refreshed "
        f"- Unlocks next: NEWS FOR YOU + AI GROWTH FEED provide live scout input for scout_adopt.py "
        f"- Proof: {len(payload['news'])} news items, {len(payload['growth'])} growth candidates, cost ${cost_usd:.2f} "
        "- Next move: review scout feed and route adoption candidates - AI(Codex)"
    )


def render_append(path: Path, line: str) -> str:
    existing = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    if line in existing:
        return existing if existing.endswith("\n") else existing + "\n"
    return existing.rstrip() + "\n" + line + "\n"


def frontmatter(existing: str, run_date: str) -> list[str]:
    preserved: list[str] = []
    if existing.startswith("---\n"):
        lines = existing.splitlines()
        for line in lines[1:]:
            if line == "---":
                break
            key = line.split(":", 1)[0].strip().lower()
            if key not in {"status", "last_run", "source"}:
                preserved.append(line)
    return [
        "---",
        *preserved,
        f"status: live (scout pipe - last run {run_date})",
        f"last_run: {run_date}",
        "source: tools/scout/scout_run.py",
        "---",
        "",
    ]


def _read_existing(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def atomic_write_many(targets: dict[Path, str]) -> None:
    temp_paths: list[tuple[Path, Path]] = []
    try:
        for target, content in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
            tmp = Path(raw)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            temp_paths.append((target, tmp))
        for target, tmp in temp_paths:
            tmp.replace(target)
    except Exception:
        for _target, tmp in temp_paths:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the guarded World Scout pipe.")
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("FPAI_VAULT", DEFAULT_VAULT)))
    parser.add_argument("--prompt", type=Path, default=Path(os.environ.get("SCOUT_PROMPT", DEFAULT_PROMPT)))
    parser.add_argument("--config-dir", type=Path, default=Path(os.environ.get("SCOUT_CONFIG_DIR", DEFAULT_CONFIG)))
    parser.add_argument("--cursor", type=Path, default=Path(os.environ.get("SCOUT_CURSOR", DEFAULT_CURSOR)))
    parser.add_argument("--disabled", type=Path, default=Path(os.environ.get("SCOUT_DISABLED", DEFAULT_DISABLED)))
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--today", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_if_due(
            vault=args.vault,
            prompt_path=args.prompt,
            config_dir=args.config_dir,
            cursor_path=args.cursor,
            disabled_path=args.disabled,
            fixture_path=args.fixture,
            force=args.force,
            dry_run=args.dry_run,
            today=args.today,
        )
        code = 0
    except ScoutRunError as exc:
        result = ScoutResult("stalled", args.today or today_utc(), 0.0, [], str(exc))
        code = 2
    payload = {
        "status": result.status,
        "date": result.date,
        "cost_usd": result.cost_usd,
        "wrote": [str(path) for path in result.wrote],
        "reason": result.reason,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        wrote = f" wrote={len(result.wrote)}" if result.wrote else ""
        reason = f" reason={result.reason}" if result.reason else ""
        print(f"world-scout: {result.status} date={result.date} cost=${result.cost_usd:.2f}{wrote}{reason}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
