#!/usr/bin/env python3
"""Read-only audit for merged builds that landed but may not be used.

The audit classifies merged specs as:

- auto-activated: activate script ran and smoke passed per ops ledger;
- library: explicitly declared library, referenced by code, or scheduled;
- INERT: no activation evidence and no reference/schedule evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_DECLARATIONS = REPO_ROOT / "core" / "BUILD" / "activation_declarations.json"
SPEC_RE = re.compile(r"\bSPEC_[A-Za-z0-9][A-Za-z0-9_.-]*")
BUILD_KIND_RE = re.compile(r"\bbuild_kind\s*[:=]\s*(library|inert)\b", re.I)
LIVE_SCAN_SUFFIXES = {
    ".py",
    ".sh",
    ".service",
    ".timer",
    ".conf",
    ".md",
    ".html",
    ".js",
    ".ts",
    ".tsx",
}
SKIP_SCAN_PARTS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}


@dataclass(frozen=True)
class BuildRecord:
    spec_id: str
    branch: str = ""
    status: str = "merged"
    sources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuditRow:
    spec_id: str
    branch: str
    classification: str
    explained: bool
    explicit_build_kind: str
    activation_script: str
    activation_evidence: list[str]
    reference_evidence: list[str]
    changed_files: list[str]
    sources: list[str]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def discover_merged_builds(
    repo_root: Path = REPO_ROOT,
    *,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
) -> list[BuildRecord]:
    found: dict[str, BuildRecord] = {}

    def add(spec_id: str, *, branch: str = "", status: str = "merged", source: str) -> None:
        if not spec_id:
            return
        existing = found.get(spec_id)
        if existing:
            sources = [*existing.sources, source] if source not in existing.sources else existing.sources
            found[spec_id] = BuildRecord(
                spec_id=spec_id,
                branch=existing.branch or branch,
                status=existing.status or status,
                sources=sources,
            )
        else:
            found[spec_id] = BuildRecord(spec_id=spec_id, branch=branch, status=status, sources=[source])

    registry = repo_root / "core" / "BUILD" / "REGISTRY.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    rows = data.get("active_builds") if isinstance(data, dict) else []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "").strip()
        if status != "merged":
            continue
        spec_id = str(row.get("id") or row.get("slug") or "").strip()
        add(spec_id, branch=str(row.get("branch") or ""), status=status, source="registry")

    proof_log = repo_root / "core" / "BUILD" / "PROOF_LOG.md"
    try:
        proof_text = proof_log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        proof_text = ""
    for line in proof_text.splitlines():
        if "· merged" not in line:
            continue
        specs = SPEC_RE.findall(line)
        if specs:
            branch = next((part.strip() for part in line.split("·") if part.strip().startswith("build/")), "")
            add(specs[0], branch=branch, source="proof_log")

    for row in read_jsonl(ops_ledger):
        event = str(row.get("event") or "").lower()
        if event not in {"auto-merged", "backlog-merged", "merged", "activated"}:
            continue
        haystack = " ".join(str(row.get(key) or "") for key in ("detail", "artifact", "spec_id", "branch"))
        specs = SPEC_RE.findall(haystack)
        if specs:
            add(specs[0], branch=str(row.get("artifact") or row.get("branch") or ""), source="ops_ledger")

    return [found[key] for key in sorted(found)]


def audit(
    repo_root: Path = REPO_ROOT,
    *,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    records: Iterable[BuildRecord] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    ops_rows = read_jsonl(ops_ledger)
    build_records = list(records) if records is not None else discover_merged_builds(root, ops_ledger=ops_ledger)
    rows = [classify_record(root, record, ops_rows) for record in build_records]
    counts = Counter(row.classification for row in rows)
    unexplained = [row for row in rows if row.classification == "INERT" and not row.explained]
    return {
        "schema": "activation-audit.v1",
        "repo_root": str(root),
        "ops_ledger": str(ops_ledger),
        "counts": dict(sorted(counts.items())),
        "total": len(rows),
        "unexplained_inert_count": len(unexplained),
        "unexplained_inert": [row.spec_id for row in unexplained],
        "rows": [asdict(row) for row in rows],
    }


def classify_record(repo_root: Path, record: BuildRecord, ops_rows: list[dict[str, Any]]) -> AuditRow:
    spec_id = record.spec_id
    activation_script = repo_root / "core" / "BUILD" / "activate" / f"{spec_id}.sh"
    activation_evidence = activation_events(spec_id, ops_rows)
    changed = changed_files_for_spec(repo_root, spec_id)
    kind = explicit_build_kind(repo_root, spec_id)
    references = reference_evidence(repo_root, changed)

    if activation_script.exists() and activation_evidence:
        classification = "auto-activated"
        explained = True
    elif kind == "library" or references:
        classification = "library"
        explained = True
    else:
        classification = "INERT"
        explained = kind == "inert"

    return AuditRow(
        spec_id=spec_id,
        branch=record.branch,
        classification=classification,
        explained=explained,
        explicit_build_kind=kind,
        activation_script=str(activation_script.relative_to(repo_root)) if activation_script.exists() else "",
        activation_evidence=activation_evidence,
        reference_evidence=references,
        changed_files=changed,
        sources=record.sources,
    )


def activation_events(spec_id: str, rows: list[dict[str, Any]]) -> list[str]:
    evidence: list[str] = []
    for row in rows:
        event = str(row.get("event") or "").lower()
        detail = str(row.get("detail") or "")
        if spec_id not in json.dumps(row, sort_keys=True):
            continue
        if event == "activated" and ("smoke passed" in detail.lower() or "guarded activate" in detail.lower()):
            evidence.append(compact(f"activated: {detail}")[:220])
        elif event == "smoke-pass":
            evidence.append(compact(f"smoke-pass: {detail}")[:220])
    return evidence[:5]


def changed_files_for_spec(repo_root: Path, spec_id: str) -> list[str]:
    result = repo_root / "core" / "BUILD" / "results" / f"{spec_id}.result.md"
    text = ""
    try:
        text = result.read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    paths = []
    in_files = False
    for line in text.splitlines():
        stripped = line.strip().lstrip("-* ").strip()
        if re.match(r"^#{1,4}\s*files?\s+changed\b", stripped, flags=re.I):
            in_files = True
            continue
        if in_files and stripped.startswith("#"):
            break
        if not in_files:
            continue
        for token in re.findall(r"`([^`]+)`", line):
            if is_repo_path_token(token):
                paths.append(token.strip())
        if is_repo_path_token(stripped):
            paths.append(stripped)
    seen: set[str] = set()
    out: list[str] = []
    for path in paths:
        clean = path.strip().strip(".,;:")
        if clean and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out[:80]


def is_repo_path_token(token: str) -> bool:
    clean = token.strip().strip(".,;:")
    if not clean or clean.startswith("/") or " " in clean or "\n" in clean:
        return False
    if "/" not in clean:
        return False
    return bool(re.match(r"^[A-Za-z0-9_./@+-]+$", clean))


def explicit_build_kind(repo_root: Path, spec_id: str) -> str:
    declared = explicit_build_kind_from_declarations(repo_root, spec_id)
    if declared:
        return declared
    candidates = [
        repo_root / "core" / "BUILD" / "specs" / f"{spec_id}.md",
        repo_root / "core" / "BUILD" / "results" / f"{spec_id}.result.md",
    ]
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = BUILD_KIND_RE.search(text)
        if match:
            return match.group(1).lower()
    return ""


def explicit_build_kind_from_declarations(repo_root: Path, spec_id: str) -> str:
    path = repo_root / "core" / "BUILD" / "activation_declarations.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    declarations = data.get("declarations") if isinstance(data, dict) else None
    if not isinstance(declarations, dict):
        return ""
    row = declarations.get(spec_id)
    if isinstance(row, str):
        kind = row.strip().lower()
    elif isinstance(row, dict):
        kind = str(row.get("build_kind") or "").strip().lower()
    else:
        kind = ""
    return kind if kind in {"library", "inert"} else ""


def reference_evidence(repo_root: Path, changed_files: list[str]) -> list[str]:
    probes = reference_probes(changed_files)
    if not probes:
        return []
    evidence: list[str] = []
    for path in iter_scan_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        if rel in changed_files or rel.startswith("core/BUILD/results/") or rel.startswith("core/BUILD/specs/"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for probe in probes:
            if probe and probe in text:
                evidence.append(f"{rel} references {probe}")
                break
        if len(evidence) >= 8:
            break
    return evidence


def reference_probes(changed_files: list[str]) -> list[str]:
    probes: set[str] = set()
    for raw in changed_files:
        path = Path(raw)
        if raw.startswith("core/BUILD/cron/") and path.suffix in {".service", ".timer", ".conf"}:
            probes.add(raw)
            probes.add(path.name)
        if path.suffix == ".py" and not path.name.startswith("test_"):
            probes.add(raw)
            probes.add(path.name)
            module = raw[:-3].replace("/", ".")
            probes.add(module)
            probes.add(f"import {module}")
            probes.add(f"from {module} import")
        elif path.suffix in {".sh", ".service", ".timer"}:
            probes.add(raw)
            probes.add(path.name)
    return sorted(probes, key=len, reverse=True)


def iter_scan_files(repo_root: Path) -> Iterable[Path]:
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = set(path.relative_to(repo_root).parts)
        if rel_parts & SKIP_SCAN_PARTS:
            continue
        if path.suffix in LIVE_SCAN_SUFFIXES:
            yield path


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Build Activation Audit",
        "",
        f"- Total merged builds audited: {payload['total']}",
        f"- Unexplained inert builds: {payload['unexplained_inert_count']}",
        f"- Counts: {json.dumps(payload['counts'], sort_keys=True)}",
        "",
        "| Spec | Classification | Explained | Evidence |",
        "|---|---:|---:|---|",
    ]
    for row in payload["rows"]:
        evidence = row["activation_evidence"] or row["reference_evidence"] or [row["explicit_build_kind"] or "none"]
        lines.append(
            f"| `{row['spec_id']}` | {row['classification']} | {str(row['explained']).lower()} | "
            f"{compact('; '.join(evidence))[:220]} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--fail-on-unexplained-inert", action="store_true")
    args = parser.parse_args(argv)

    payload = audit(args.repo_root, ops_ledger=args.ops_ledger)
    rendered = render_markdown(payload) if args.markdown else json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if args.fail_on_unexplained_inert and payload["unexplained_inert_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
