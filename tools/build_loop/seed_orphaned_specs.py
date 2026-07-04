#!/usr/bin/env python3
"""Seed decision rows for SPEC files that have no matching decision.

The server build loop is decision-driven. This helper keeps repo-local specs
visible by creating an answered `needs_build=true` decision row when a
`core/BUILD/specs/SPEC_dNNN*.md` file exists without a `brain_index.decisions`
row whose id is `dNNN`.

Named specs (`SPEC_foo.md`) are renamed to a DB-allocated `SPEC_dNNN_foo.md`
before they are allowed into the loop. The decisions DB owns the dNNN namespace;
file-side numbering is only honored for files that already carry a dNNN id.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPECS_DIR = REPO_ROOT / "core" / "BUILD" / "specs"
DEFAULT_RESULTS_DIR = REPO_ROOT / "core" / "BUILD" / "results"
DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
)
SPEC_RE = re.compile(r"^SPEC_(d\d{3,})(?:_|-|$)")


@dataclasses.dataclass(frozen=True)
class SpecCandidate:
    decision_id: str
    spec_id: str
    path: Path
    question: str
    answer: str
    build_spec: str
    proof_expected: str
    rename_from: Path | None = None


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_spec(path: Path) -> SpecCandidate | None:
    match = SPEC_RE.match(path.stem)
    if not match:
        return None
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return None
    decision_id = match.group(1)
    first_heading = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("# ")), "")
    question = first_heading or path.stem
    proof_expected = _field_from_context(text, "Proof expected") or (
        f"brain_index.decisions contains answered needs_build row `{decision_id}` "
        f"for orphan spec `{path.name}`."
    )
    return SpecCandidate(
        decision_id=decision_id,
        spec_id=path.stem,
        path=path,
        question=question,
        answer=f"auto-seeded from orphaned spec file `{path.name}` at {utc_now()}",
        build_spec=text + "\n",
        proof_expected=proof_expected,
    )


def parse_named_spec(path: Path, decision_id: str) -> SpecCandidate | None:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return None
    slug = slug_from_named_spec(path)
    target = path.with_name(f"SPEC_{decision_id}_{slug}.md")
    first_heading = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("# ")), "")
    question = first_heading or path.stem
    proof_expected = _field_from_context(text, "Proof expected") or (
        f"brain_index.decisions contains answered needs_build row `{decision_id}` "
        f"for named spec `{target.name}`."
    )
    return SpecCandidate(
        decision_id=decision_id,
        spec_id=target.stem,
        path=target,
        question=question,
        answer=f"auto-seeded from named spec file `{path.name}` at {utc_now()}",
        build_spec=text + "\n",
        proof_expected=proof_expected,
        rename_from=path,
    )


def slug_from_named_spec(path: Path) -> str:
    stem = path.stem
    raw = stem[len("SPEC_") :] if stem.startswith("SPEC_") else stem
    slug = re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-").lower()
    return slug or "named-spec"


def _field_from_context(text: str, label: str) -> str:
    prefix = f"- {label}:"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return ""


def discover_specs(
    specs_dir: Path,
    results_dir: Path,
    *,
    existing_ids: set[str] | None = None,
) -> list[SpecCandidate]:
    existing = existing_ids or set()
    candidates: list[SpecCandidate] = []
    if not specs_dir.exists():
        return candidates
    for path in sorted(specs_dir.glob("SPEC_d*.md")):
        candidate = parse_spec(path)
        if candidate is None:
            continue
        if candidate.decision_id in existing:
            continue
        if (results_dir / f"{candidate.spec_id}.result.md").exists():
            continue
        candidates.append(candidate)
    return candidates


def discover_named_spec_paths(specs_dir: Path, results_dir: Path) -> list[Path]:
    if not specs_dir.exists():
        return []
    paths: list[Path] = []
    for path in sorted(specs_dir.glob("SPEC_*.md")):
        if parse_spec(path) is not None:
            continue
        if (results_dir / f"{path.stem}.result.md").exists():
            continue
        paths.append(path)
    return paths


def connect() -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(f"psycopg unavailable: {exc}") from exc
    return psycopg.connect(DB_URL, autocommit=True)


def existing_decision_ids(conn: Any, decision_ids: Iterable[str]) -> set[str]:
    ids = sorted(set(decision_ids))
    if not ids:
        return set()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id::text
              FROM brain_index.decisions
             WHERE id::text = ANY(%s)
            """,
            (ids,),
        )
        return {str(row[0]) for row in cur.fetchall()}


def existing_named_spec_names(conn: Any, spec_names: Iterable[str]) -> set[str]:
    names = sorted(set(spec_names))
    if not names:
        return set()
    patterns = [f"%{name}%" for name in names]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COALESCE(question, ''),
                COALESCE(answer, ''),
                COALESCE(build_spec, ''),
                COALESCE(proof_expected, '')
              FROM brain_index.decisions
             WHERE answer LIKE ANY(%s)
                OR build_spec LIKE ANY(%s)
                OR proof_expected LIKE ANY(%s)
            """,
            (patterns, patterns, patterns),
        )
        found: set[str] = set()
        for row in cur.fetchall():
            haystack = "\n".join(str(value) for value in row)
            for name in names:
                if name in haystack:
                    found.add(name)
        return found


def max_decision_number(conn: Any) -> int:
    with conn.cursor() as cur:
        cur.execute(r"SELECT id FROM brain_index.decisions WHERE id ~ '^d[0-9]+$'")
        nums = []
        for row in cur.fetchall():
            value = str(row[0])
            if re.fullmatch(r"d\d+", value):
                nums.append(int(value[1:]))
        return max(nums) if nums else 0


def insert_candidate(conn: Any, candidate: SpecCandidate) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO brain_index.decisions
                (id, question, status, answer, needs_build, build_spec, proof_expected, spec_written, build_status)
            VALUES
                (%s, %s, 'answered', %s, true, %s, %s, false, 'queued')
            ON CONFLICT (id) DO NOTHING
            RETURNING id::text
            """,
            (
                candidate.decision_id,
                candidate.question,
                candidate.answer,
                candidate.build_spec,
                candidate.proof_expected,
            ),
        )
        return cur.fetchone() is not None


def rename_candidate(candidate: SpecCandidate) -> None:
    if candidate.rename_from is None or candidate.rename_from == candidate.path:
        return
    if candidate.path.exists():
        raise FileExistsError(f"cannot rename {candidate.rename_from} to existing {candidate.path}")
    if _is_relative_to(candidate.rename_from.resolve(), REPO_ROOT.resolve()):
        result = subprocess.run(
            ["git", "mv", str(candidate.rename_from), str(candidate.path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
    candidate.rename_from.rename(candidate.path)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def seed_orphaned_specs(specs_dir: Path, results_dir: Path, *, dry_run: bool = False) -> list[str]:
    parsed = [candidate for candidate in (parse_spec(path) for path in sorted(specs_dir.glob("SPEC_d*.md"))) if candidate]
    named_paths = discover_named_spec_paths(specs_dir, results_dir)
    with connect() as conn:
        existing = existing_decision_ids(conn, (candidate.decision_id for candidate in parsed))
        named_existing = existing_named_spec_names(conn, (path.name for path in named_paths))
        named_paths = [path for path in named_paths if path.name not in named_existing]
        candidates = discover_specs(specs_dir, results_dir, existing_ids=existing)
        reserved_ids = {candidate.decision_id for candidate in parsed}
        next_num = max_decision_number(conn) + 1
        for path in named_paths:
            while True:
                decision_id = f"d{next_num:03d}"
                next_num += 1
                target = path.with_name(f"SPEC_{decision_id}_{slug_from_named_spec(path)}.md")
                if decision_id not in reserved_ids and not target.exists():
                    break
            candidate = parse_named_spec(path, decision_id)
            if candidate is not None:
                reserved_ids.add(candidate.decision_id)
                candidates.append(candidate)
        seeded: list[str] = []
        for candidate in candidates:
            if dry_run:
                seeded.append(candidate.decision_id)
            elif insert_candidate(conn, candidate):
                rename_candidate(candidate)
                seeded.append(candidate.decision_id)
        return seeded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--specs-dir", type=Path)
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true", help="return non-zero on DB/import failures")
    args = parser.parse_args(argv)

    if os.environ.get("ORPHAN_SPEC_SEED_DISABLE") == "1":
        print("orphan spec seed disabled (ORPHAN_SPEC_SEED_DISABLE=1)")
        return 0

    specs_dir = args.specs_dir or args.repo / "core" / "BUILD" / "specs"
    results_dir = args.results_dir or args.repo / "core" / "BUILD" / "results"
    try:
        seeded = seed_orphaned_specs(specs_dir, results_dir, dry_run=args.dry_run)
    except Exception as exc:
        print(f"warning: orphan spec seed skipped: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1 if args.strict else 0
    if seeded:
        verb = "would seed" if args.dry_run else "seeded"
        print(f"{verb} orphan specs: {', '.join(seeded)}")
    else:
        print("no orphan specs to seed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
