#!/usr/bin/env python3
"""Retroactively audit merged d001-d092 builds for live artifacts.

The audit is read-only except for append-only ops ledger rows, optional Telegram
notification, and optional `brain_index.decisions` follow-up seeding for
concrete dead artifacts.
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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "liveness_audit.md"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
)

DECISION_RE = re.compile(r"SPEC_(d\d{3,})(?:_|-|$)")
FILE_RE = re.compile(r"`([^`\n]+)`")
UNIT_RE = re.compile(r"\b([\w@.+:-]+\.(?:service|timer|socket|path))\b")
TABLE_RE = re.compile(r"\b(?:brain_index\.)?([a-zA-Z_][a-zA-Z0-9_]{2,})\b")
URL_RE = re.compile(r"https?://[^\s)`>]+")

TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".sh",
    ".sql",
    ".json",
    ".jsonl",
    ".yml",
    ".yaml",
    ".service",
    ".timer",
    ".toml",
    ".txt",
}

REPO_PATH_PREFIXES = (
    "SERVICES/",
    "core/",
    "docs/",
    "migrations/",
    "scripts/",
    "tools/",
)

TABLE_HINT_WORDS = ("table", "rows", "schema", "migration", "brain_index")
IGNORE_TABLE_WORDS = {
    "added",
    "build",
    "changed",
    "context",
    "create",
    "decision",
    "decisions",
    "expected",
    "files",
    "from",
    "into",
    "merge",
    "proof",
    "result",
    "select",
    "status",
    "summary",
    "tests",
    "where",
}


@dataclasses.dataclass(frozen=True)
class Artifact:
    kind: str
    value: str
    source: str

    def label(self) -> str:
        if self.kind == "file":
            return f"file exists: {self.value}"
        if self.kind == "systemd":
            return f"systemd unit active: {self.value}"
        if self.kind == "table":
            return f"table has rows: brain_index.{self.value}"
        if self.kind == "endpoint":
            return f"endpoint responds: {self.value}"
        return self.value


@dataclasses.dataclass(frozen=True)
class DecisionAudit:
    decision_id: str
    spec_id: str
    expected_artifacts: tuple[Artifact, ...]
    status: str
    details: tuple[str, ...]

    def expected_label(self) -> str:
        if not self.expected_artifacts:
            return "unknown expected artifact"
        labels = [artifact.label() for artifact in self.expected_artifacts[:4]]
        if len(self.expected_artifacts) > 4:
            labels.append(f"+{len(self.expected_artifacts) - 4} more")
        return "; ".join(labels)


@dataclasses.dataclass(frozen=True)
class AuditResult:
    rows: tuple[DecisionAudit, ...]
    output_path: Path
    seeded_decisions: tuple[str, ...]
    ledger_written: bool
    notified: bool

    def counts(self) -> dict[str, int]:
        out = {"live": 0, "dead": 0, "unknown": 0}
        for row in self.rows:
            out[row.status] = out.get(row.status, 0) + 1
        return out


class ProbeRunner:
    def __init__(self, repo_root: Path, *, timeout: float = 3.0, allow_external_endpoints: bool = False) -> None:
        self.repo_root = repo_root
        self.timeout = timeout
        self.allow_external_endpoints = allow_external_endpoints

    def check(self, artifact: Artifact) -> tuple[str, str]:
        if artifact.kind == "file":
            path = self.repo_root / artifact.value
            return ("live", "exists") if path.exists() else ("dead", "missing")
        if artifact.kind == "systemd":
            return self._check_systemd(artifact.value)
        if artifact.kind == "table":
            return self._check_table(artifact.value)
        if artifact.kind == "endpoint":
            return self._check_endpoint(artifact.value)
        return "unknown", f"unsupported artifact kind {artifact.kind}"

    def _check_systemd(self, unit: str) -> tuple[str, str]:
        if not _has_command("systemctl"):
            return "unknown", "systemctl unavailable"
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "--quiet", unit],
                timeout=self.timeout,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "unknown", f"systemctl probe failed: {exc}"
        stderr = (result.stderr or "").strip()
        if "Failed to connect to bus" in stderr or "System has not been booted with systemd" in stderr:
            return "unknown", stderr
        return ("live", "active") if result.returncode == 0 else ("dead", "inactive")

    def _check_table(self, table: str) -> tuple[str, str]:
        try:
            import psycopg
        except ImportError:
            return "unknown", "psycopg unavailable"
        try:
            with psycopg.connect(DB_URL, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT to_regclass(%s)", (f"brain_index.{table}",))
                    exists = cur.fetchone()[0]
                    if not exists:
                        return "dead", "table missing"
                    cur.execute(f"SELECT COUNT(*) FROM brain_index.{_safe_identifier(table)}")
                    count = int(cur.fetchone()[0] or 0)
        except Exception as exc:
            return "unknown", f"table probe failed: {type(exc).__name__}: {exc}"
        return ("live", f"{count} rows") if count > 0 else ("dead", "0 rows")

    def _check_endpoint(self, url: str) -> tuple[str, str]:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        if host not in local_hosts and not self.allow_external_endpoints:
            return "unknown", "external endpoint probe disabled"
        try:
            request = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                code = int(response.status)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return "dead", f"endpoint failed: {exc}"
        return ("live", f"HTTP {code}") if 200 <= code < 500 else ("dead", f"HTTP {code}")


def _has_command(name: str) -> bool:
    return subprocess.run(["/usr/bin/env", "bash", "-lc", f"command -v {name} >/dev/null 2>&1"], check=False).returncode == 0


def _safe_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"unsafe SQL identifier: {value}")
    return value


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_decision_id(path: Path) -> str | None:
    match = DECISION_RE.search(path.stem)
    return match.group(1) if match else None


def collect_merged_decisions(repo_root: Path, *, start: int = 1, end: int = 92, ops_ledger: Path = DEFAULT_OPS_LEDGER) -> dict[str, str]:
    merged: dict[str, str] = {}
    results_dir = repo_root / "core" / "BUILD" / "results"
    for path in sorted(results_dir.glob("SPEC_d*.result.md")):
        decision_id = parse_decision_id(path)
        if decision_id and start <= int(decision_id[1:]) <= end:
            merged[decision_id] = path.stem.removesuffix(".result")

    activate_dir = repo_root / "core" / "BUILD" / "activate"
    for path in sorted(activate_dir.glob("SPEC_d*.sh")):
        decision_id = parse_decision_id(path)
        if decision_id and start <= int(decision_id[1:]) <= end:
            merged.setdefault(decision_id, path.stem)

    for row in read_jsonl(ops_ledger):
        decision_id = str(row.get("decision_id") or row.get("did") or "")
        if not decision_id:
            detail = " ".join(str(row.get(key) or "") for key in ("detail", "artifact", "next"))
            found = re.search(r"\b(d\d{3,})\b", detail)
            decision_id = found.group(1) if found else ""
        if not decision_id or not decision_id.startswith("d"):
            continue
        try:
            number = int(decision_id[1:])
        except ValueError:
            continue
        if start <= number <= end and str(row.get("event") or "").lower() in {"merged", "succeeded", "liveness:pass"}:
            specid = _specid_from_text(" ".join(str(row.get(key) or "") for key in ("detail", "artifact")))
            merged.setdefault(decision_id, specid or decision_id)
    return dict(sorted(merged.items()))


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


def _specid_from_text(text: str) -> str:
    match = re.search(r"\bSPEC_d\d{3,}[_A-Za-z0-9-]*", text)
    return match.group(0) if match else ""


def find_spec_file(repo_root: Path, decision_id: str, spec_id: str) -> Path | None:
    specs_dir = repo_root / "core" / "BUILD" / "specs"
    preferred = specs_dir / f"{spec_id}.md"
    if preferred.exists():
        return preferred
    matches = sorted(specs_dir.glob(f"SPEC_{decision_id}*.md"))
    return matches[0] if matches else None


def find_result_file(repo_root: Path, decision_id: str, spec_id: str) -> Path | None:
    results_dir = repo_root / "core" / "BUILD" / "results"
    preferred = results_dir / f"{spec_id}.result.md"
    if preferred.exists():
        return preferred
    matches = sorted(results_dir.glob(f"SPEC_{decision_id}*.result.md"))
    return matches[0] if matches else None


def find_activation_file(repo_root: Path, decision_id: str, spec_id: str) -> Path | None:
    activate_dir = repo_root / "core" / "BUILD" / "activate"
    preferred = activate_dir / f"{spec_id}.sh"
    if preferred.exists():
        return preferred
    matches = sorted(activate_dir.glob(f"SPEC_{decision_id}*.sh"))
    return matches[0] if matches else None


def infer_artifacts(repo_root: Path, decision_id: str, spec_id: str) -> tuple[Artifact, ...]:
    spec_file = find_spec_file(repo_root, decision_id, spec_id)
    result_file = find_result_file(repo_root, decision_id, spec_id)
    activation_file = find_activation_file(repo_root, decision_id, spec_id)
    texts: list[tuple[str, str]] = []
    for label, path in (("activation", activation_file), ("result", result_file), ("spec", spec_file)):
        if path and path.exists():
            texts.append((label, path.read_text(encoding="utf-8", errors="replace")))

    artifacts: list[Artifact] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: str, source: str) -> None:
        key = (kind, value)
        if key not in seen:
            artifacts.append(Artifact(kind=kind, value=value, source=source))
            seen.add(key)

    for source, text in texts:
        for unit in infer_systemd_units(text):
            add("systemd", unit, source)
        for url in URL_RE.findall(text):
            cleaned = url.rstrip(".,")
            add("endpoint", cleaned, source)
        for table in infer_tables(text):
            add("table", table, source)

    for source, text in texts:
        for path_text in infer_file_paths(text):
            if path_text.startswith("core/BUILD/specs/") or path_text.startswith("core/BUILD/results/"):
                continue
            add("file", path_text, source)

    if not artifacts and result_file:
        add("file", str(result_file.relative_to(repo_root)), "result")
    elif not artifacts and spec_file:
        add("file", str(spec_file.relative_to(repo_root)), "spec")
    return tuple(artifacts)


def infer_file_paths(text: str) -> list[str]:
    out: list[str] = []
    for value in FILE_RE.findall(text):
        item = value.strip()
        if not item.startswith(REPO_PATH_PREFIXES):
            continue
        suffix = Path(item).suffix
        if suffix and suffix not in TEXT_EXTENSIONS:
            continue
        out.append(item)
    return out


def infer_systemd_units(text: str) -> list[str]:
    units: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        lowered = line.lower()
        if not any(marker in lowered for marker in ("systemctl", "systemd", "service", "timer", "unit")):
            continue
        for unit in UNIT_RE.findall(line):
            if unit == "sys.path":
                continue
            if unit not in seen:
                units.append(unit)
                seen.add(unit)
    return units


def infer_tables(text: str) -> list[str]:
    lowered = text.lower()
    if not any(word in lowered for word in TABLE_HINT_WORDS):
        return []
    tables: set[str] = set()
    for match in re.finditer(r"\bbrain_index\.([a-zA-Z_][a-zA-Z0-9_]*)\b", text):
        tables.add(match.group(1))
    for match in re.finditer(r"\bCREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+(?:brain_index\.)?([a-zA-Z_][a-zA-Z0-9_]*)", text, re.I):
        tables.add(match.group(1))
    for match in re.finditer(r"\b(?:New|existing|additive)\s+(?:DB\s+)?table:?\s+`?(?:brain_index\.)?([a-zA-Z_][a-zA-Z0-9_]*)`?", text, re.I):
        tables.add(match.group(1))
    return sorted(table for table in tables if table.lower() not in IGNORE_TABLE_WORDS)


def classify(artifacts: Iterable[Artifact], runner: ProbeRunner) -> tuple[str, tuple[str, ...]]:
    details: list[str] = []
    statuses: list[str] = []
    for artifact in artifacts:
        status, detail = runner.check(artifact)
        statuses.append(status)
        details.append(f"{artifact.label()} -> {status} ({detail})")
    if not statuses:
        return "unknown", ("no expected artifact inferred",)
    if "dead" in statuses:
        return "dead", tuple(details)
    if all(status == "live" for status in statuses):
        return "live", tuple(details)
    return "unknown", tuple(details)


def render_markdown(rows: Iterable[DecisionAudit]) -> str:
    lines = [
        "| decision | expected artifact | status |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row.decision_id} | {_md_escape(row.expected_label())} | {row.status} |")
    return "\n".join(lines) + "\n"


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def append_ops_ledger(path: Path, rows: Iterable[DecisionAudit], output_path: Path) -> bool:
    counts = {"live": 0, "dead": 0, "unknown": 0}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    payload = {
        "ts": utc_now(),
        "loop": "liveness",
        "event": "retroactive_audit",
        "detail": f"d001-d092 live={counts.get('live', 0)} dead={counts.get('dead', 0)} unknown={counts.get('unknown', 0)}",
        "cost": "$0",
        "artifact": str(output_path),
        "next": "Build queued activation follow-ups for concrete dead rows.",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return True
    except OSError:
        return False


def connect() -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(f"psycopg unavailable: {exc}") from exc
    return psycopg.connect(DB_URL, autocommit=True)


def seed_dead_followups(rows: Iterable[DecisionAudit], *, dry_run: bool = False) -> list[str]:
    dead = [row for row in rows if row.status == "dead"]
    if not dead:
        return []
    seeded: list[str] = []
    if dry_run:
        return [f"{row.decision_id}-activate" for row in dead]
    with connect() as conn:
        for row in dead:
            decision_id = f"{row.decision_id}-activate"
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
                        decision_id,
                        f"Activate dead merged build {row.decision_id}",
                        f"auto-seeded by d116 retroactive liveness audit at {utc_now()}",
                        build_followup_spec(row),
                        f"{row.expected_label()} reports live in the retroactive liveness audit.",
                    ),
                )
                if cur.fetchone() is not None:
                    seeded.append(decision_id)
    return seeded


def build_followup_spec(row: DecisionAudit) -> str:
    details = "\n".join(f"- {detail}" for detail in row.details)
    return (
        f"# {row.decision_id}-activate - Activate dead merged build\n\n"
        "## Build\n"
        f"Investigate and activate the expected artifact for merged decision `{row.decision_id}`. "
        "Keep the fix scoped, reversible, tested, and limited to activation wiring or the missing artifact. "
        "Do not deploy broadly, push, merge, touch secrets, send outreach, stop/delete services, or move money.\n\n"
        "## Expected artifact\n"
        f"{row.expected_label()}\n\n"
        "## Audit details\n"
        f"{details}\n"
    )


def notify_telegram(repo_root: Path, rows: Iterable[DecisionAudit], output_path: Path) -> bool:
    counts = {"live": 0, "dead": 0, "unknown": 0}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    message = (
        "d116 retroactive liveness audit complete: "
        f"live={counts.get('live', 0)} dead={counts.get('dead', 0)} unknown={counts.get('unknown', 0)}. "
        f"Report: {output_path}"
    )
    script = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    if not script.exists():
        return False
    try:
        result = subprocess.run([str(script), message], check=False, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def run_audit(
    *,
    repo_root: Path = REPO_ROOT,
    output: Path = DEFAULT_OUTPUT,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    start: int = 1,
    end: int = 92,
    seed: bool = True,
    seed_dry_run: bool = False,
    notify: bool = True,
    allow_external_endpoints: bool = False,
    runner: ProbeRunner | None = None,
) -> AuditResult:
    runner = runner or ProbeRunner(repo_root, allow_external_endpoints=allow_external_endpoints)
    merged = collect_merged_decisions(repo_root, start=start, end=end, ops_ledger=ops_ledger)
    rows: list[DecisionAudit] = []
    for decision_id, spec_id in merged.items():
        artifacts = infer_artifacts(repo_root, decision_id, spec_id)
        status, details = classify(artifacts, runner)
        rows.append(DecisionAudit(decision_id, spec_id, artifacts, status, details))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(rows), encoding="utf-8")
    ledger_written = append_ops_ledger(ops_ledger, rows, output)

    seeded: list[str] = []
    if seed:
        try:
            seeded = seed_dead_followups(rows, dry_run=seed_dry_run)
        except Exception as exc:
            print(f"warning: dead follow-up seeding skipped: {type(exc).__name__}: {exc}", file=sys.stderr)

    notified = notify_telegram(repo_root, rows, output) if notify else False
    return AuditResult(tuple(rows), output, tuple(seeded), ledger_written, notified)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=92)
    parser.add_argument("--no-seed", action="store_true", help="do not insert dead activation decisions")
    parser.add_argument("--seed-dry-run", action="store_true", help="report which activation decisions would be seeded")
    parser.add_argument("--no-notify", action="store_true", help="skip Telegram notification")
    parser.add_argument("--allow-external-endpoints", action="store_true", help="probe non-local HTTP endpoints")
    args = parser.parse_args(argv)

    result = run_audit(
        repo_root=args.repo_root,
        output=args.output,
        ops_ledger=args.ops_ledger,
        start=args.start,
        end=args.end,
        seed=not args.no_seed,
        seed_dry_run=args.seed_dry_run,
        notify=not args.no_notify,
        allow_external_endpoints=args.allow_external_endpoints,
    )
    counts = result.counts()
    print(
        f"wrote {result.output_path} "
        f"(live={counts.get('live', 0)} dead={counts.get('dead', 0)} unknown={counts.get('unknown', 0)}; "
        f"seeded={len(result.seeded_decisions)}; ledger={result.ledger_written}; notified={result.notified})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
