#!/usr/bin/env python3
"""Extract explicit James-stated operating protocols into durable memory files.

This script is intended to run on server 162. It reads recent Telegram turns
plus the memory repo's episodic flat files, asks Claude to extract explicit
rules/preferences/clarifications, writes new protocol Markdown files, and can
commit those files to the memory git repo.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

DEFAULT_MEMORY_REPO = Path(os.environ.get("FPAI_MEMORY_REPO", "/opt/fpai/build"))
DEFAULT_PROTOCOLS_DIR = Path(os.environ.get("FPAI_PROTOCOLS_DIR", str(DEFAULT_MEMORY_REPO / "memory" / "protocols")))
DEFAULT_EPISODIC_DIR = Path(os.environ.get("FPAI_EPISODIC_DIR", str(DEFAULT_MEMORY_REPO / "memory" / "episodic")))
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
MAX_PROMPT_CHARS = 120_000
MAX_FILE_CHARS = 4_000
MAX_FILES = 80
PROOF_PHRASES = (
    "concentrate harder not build more",
    "intent should update protocols",
    "case study first then template",
)


@dataclass(frozen=True)
class Protocol:
    slug: str
    rule: str
    source_date: str


@dataclass(frozen=True)
class ExtractionResult:
    candidates: int
    written: int
    skipped: int
    files: list[str]
    committed: bool
    dry_run: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "candidates": self.candidates,
            "written": self.written,
            "skipped": self.skipped,
            "files": self.files,
            "committed": self.committed,
            "dry_run": self.dry_run,
        }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:80].strip("-") or "protocol"


def normalize_slug(raw: str, fallback_rule: str) -> str:
    slug = slugify(raw)
    if slug == "protocol":
        slug = slugify(fallback_rule[:80])
    return slug or "protocol"


def parse_date(raw: str, *, fallback: datetime) -> str:
    value = (raw or "").strip()
    if not value:
        return fallback.date().isoformat()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc)
        return parsed.date().isoformat()
    except ValueError:
        match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        if match:
            return match.group(0)
    return fallback.date().isoformat()


def connect(dsn: str | None = None) -> Any:
    database_url = dsn or dsn_from_env()
    if not database_url:
        raise RuntimeError("missing database DSN; set BRAIN_INDEX_DB_URL, DATABASE_URL, or DB_URL")
    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise RuntimeError("psycopg is required on the 162 brain-index host") from exc
    return psycopg.connect(database_url, connect_timeout=5)


def dsn_from_env() -> str | None:
    for key in ("BRAIN_INDEX_DB_URL", "DATABASE_URL", "DB_URL"):
        value = os.environ.get(key)
        if value:
            return value
    return None


def read_tg_messages(conn: Any, *, since: datetime, limit: int = 600) -> list[dict[str, str]]:
    sql = """
        SELECT role::text, text::text, at
          FROM brain_index.tg_messages
         WHERE at >= %s
           AND private_flag IS NOT TRUE
         ORDER BY at ASC
         LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (since, limit))
        rows = cur.fetchall()
    return [
        {
            "role": str(role or ""),
            "text": str(text or ""),
            "at": stringify_time(at),
        }
        for role, text, at in rows
        if compact(str(text or ""))
    ]


def stringify_time(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value or "")


def scan_episodic_files(root: Path, *, since: datetime, max_files: int = MAX_FILES) -> list[dict[str, str]]:
    if not root.exists():
        return []
    files = []
    cutoff = since.timestamp()
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json", ".jsonl"}:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_mtime < cutoff:
            continue
        files.append((stat.st_mtime, path))
    out = []
    for _mtime, path in sorted(files, reverse=True)[:max_files]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[-MAX_FILE_CHARS:]
        except OSError:
            continue
        if compact(text):
            out.append({"path": str(path), "text": text})
    return out


def build_prompt(*, messages: list[dict[str, str]], episodic_files: list[dict[str, str]], since: datetime) -> str:
    evidence = {
        "window_start": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tg_messages": messages,
        "episodic_files": episodic_files,
    }
    body = json.dumps(evidence, ensure_ascii=False, indent=2)
    if len(body) > MAX_PROMPT_CHARS:
        body = body[-MAX_PROMPT_CHARS:]
    return (
        "Extract only explicit user-stated operating rules, preferences, and clarifications from this evidence.\n"
        "A valid item must be a durable instruction James stated or clearly corrected, not a model inference.\n"
        "Ignore ordinary facts, plans, tasks, vague vibes, and bot-authored rules unless James explicitly affirmed them.\n"
        "Output strict JSON only: [{\"slug\":\"kebab-case\", \"rule\":\"one clear rule\", \"source_date\":\"YYYY-MM-DD\"}].\n"
        "Prefer concise slugs. Preserve James's intent in plain language. Return [] if nothing qualifies.\n\n"
        "Evidence JSON:\n"
        f"{body}\n"
    )


def run_claude_prompt(prompt: str, timeout: int = 120) -> str:
    claude = shutil.which("claude")
    if not claude:
        raise RuntimeError("claude CLI not found")
    result = subprocess.run(
        [claude, "-p", prompt],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"claude exited {result.returncode}")
    return result.stdout


def parse_json_array(raw: str) -> list[Any]:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end <= start:
            raise ValueError("no JSON array found")
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, list):
        raise ValueError("expected JSON array")
    return parsed


def validate_protocols(items: Iterable[Any], *, fallback_date: datetime) -> list[Protocol]:
    out: list[Protocol] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        rule = compact(str(item.get("rule") or ""))
        if len(rule) < 8:
            continue
        slug = normalize_slug(str(item.get("slug") or ""), rule)
        if slug in seen:
            continue
        seen.add(slug)
        out.append(Protocol(slug=slug, rule=rule, source_date=parse_date(str(item.get("source_date") or ""), fallback=fallback_date)))
    return out


def render_protocol(protocol: Protocol) -> str:
    return (
        "---\n"
        "type: protocol\n"
        "source: intent-extractor\n"
        f"date: {protocol.source_date}\n"
        "---\n\n"
        f"# {protocol.slug}\n\n"
        f"{protocol.rule}\n\n"
        f"Source date: {protocol.source_date}\n"
    )


def write_protocols(protocols: list[Protocol], protocols_dir: Path, *, dry_run: bool = False) -> tuple[list[Path], int]:
    written: list[Path] = []
    skipped = 0
    for protocol in protocols:
        path = protocols_dir / f"{protocol.slug}.md"
        if path.exists():
            skipped += 1
            continue
        if not dry_run:
            protocols_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(render_protocol(protocol), encoding="utf-8")
        written.append(path)
    return written, skipped


def commit_protocols(memory_repo: Path, files: list[Path], *, message: str) -> bool:
    if not files:
        return False
    rel_files = [str(path.relative_to(memory_repo)) if path.is_relative_to(memory_repo) else str(path) for path in files]
    subprocess.run(["git", "-C", str(memory_repo), "add", *rel_files], check=True, text=True)
    result = subprocess.run(
        ["git", "-C", str(memory_repo), "commit", "-m", message],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return True
    combined = (result.stdout or "") + (result.stderr or "")
    if "nothing to commit" in combined.lower():
        return False
    raise RuntimeError(combined.strip() or f"git commit exited {result.returncode}")


def extract_protocols(
    *,
    memory_repo: Path = DEFAULT_MEMORY_REPO,
    protocols_dir: Path = DEFAULT_PROTOCOLS_DIR,
    episodic_dir: Path = DEFAULT_EPISODIC_DIR,
    days: int = 7,
    dsn: str | None = None,
    read_telegram: bool = True,
    claude_runner: Callable[[str], str] = run_claude_prompt,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    commit: bool = False,
    dry_run: bool = False,
    now: datetime | None = None,
) -> ExtractionResult:
    if os.environ.get("INTENT_PROTOCOL_EXTRACTOR_DISABLE") == "1":
        return ExtractionResult(0, 0, 0, [], False, dry_run)
    current = now or utc_now()
    since = current - timedelta(days=days)
    messages: list[dict[str, str]] = []
    if read_telegram and (dsn or dsn_from_env()):
        with connect(dsn) as conn:
            messages = read_tg_messages(conn, since=since)
    episodic_files = scan_episodic_files(episodic_dir, since=since)
    prompt = build_prompt(messages=messages, episodic_files=episodic_files, since=since)
    protocols = validate_protocols(parse_json_array(claude_runner(prompt)), fallback_date=current)
    written, skipped = write_protocols(protocols, protocols_dir, dry_run=dry_run)
    committed = False
    if commit and not dry_run:
        committed = commit_protocols(memory_repo, written, message=f"Add {len(written)} intent protocol(s)")
    result = ExtractionResult(
        candidates=len(protocols),
        written=len(written),
        skipped=skipped,
        files=[str(path) for path in written],
        committed=committed,
        dry_run=dry_run,
    )
    if not dry_run:
        log_ops(result, ops_ledger=ops_ledger)
    return result


def log_ops(result: ExtractionResult, *, ops_ledger: Path) -> None:
    row = {
        "ts": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "intent_protocol_extractor",
        "event": "succeeded",
        "detail": f"wrote {result.written} protocol files; skipped {result.skipped}",
        "cost": "$0 marginal plus Claude CLI plan usage",
        "artifact": ",".join(result.files),
        "next": "protocol files available to every memory-reading surface",
        "surface": os.environ.get("FPAI_SURFACE", "server-162"),
        **result.to_json(),
    }
    ops_ledger.parent.mkdir(parents=True, exist_ok=True)
    with ops_ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def proof_count(protocols_dir: Path, phrases: Iterable[str] = PROOF_PHRASES) -> int:
    if not protocols_dir.exists():
        return 0
    files = list(protocols_dir.glob("*.md"))
    count = 0
    for phrase in phrases:
        needle = phrase.lower()
        phrase_slug = slugify(phrase)
        found = False
        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                continue
            if needle in text or phrase_slug in path.stem:
                found = True
                break
        if found:
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract explicit James-stated protocols into memory/protocols.")
    parser.add_argument("--memory-repo", type=Path, default=DEFAULT_MEMORY_REPO)
    parser.add_argument("--protocols-dir", type=Path, default=DEFAULT_PROTOCOLS_DIR)
    parser.add_argument("--episodic-dir", type=Path, default=DEFAULT_EPISODIC_DIR)
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--skip-telegram", action="store_true", help="skip brain_index.tg_messages reads")
    parser.add_argument("--commit", action="store_true", help="git add/commit written protocol files in the memory repo")
    parser.add_argument("--dry-run", action="store_true", help="run extraction without writing files, committing, or logging ops")
    parser.add_argument("--require-proof", action="store_true", help="exit nonzero unless the three expected first-run clarifications exist")
    args = parser.parse_args(argv)

    try:
        result = extract_protocols(
            memory_repo=args.memory_repo,
            protocols_dir=args.protocols_dir,
            episodic_dir=args.episodic_dir,
            days=args.days,
            dsn=args.dsn,
            read_telegram=not args.skip_telegram,
            commit=args.commit,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2

    proof = proof_count(args.protocols_dir)
    ok = proof >= len(PROOF_PHRASES) if args.require_proof else True
    print(json.dumps({"ok": ok, "proof_count": proof, **result.to_json()}, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
