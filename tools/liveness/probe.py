#!/usr/bin/env python3
"""Read-only typed post-merge liveness probes.

Supported declaration shapes:

    liveness:
      - type: systemd
        unit: fpai-build-loop.timer
      - type: table
        table: probe_sessions
      - type: file
        path: core/STATE/HOT_STATE.md
      - type: endpoint
        url: http://127.0.0.1:8000/health
      - type: port
        port: 5432

JSON with the same fields is also accepted. Probes never mutate the target; the
only write this module performs is an optional append-only ops-ledger row.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
)

KIND_ALIASES = {
    "db": "table",
    "database": "table",
    "systemctl": "systemd",
    "unit": "systemd",
    "service": "systemd",
    "timer": "systemd",
    "http": "endpoint",
    "url": "endpoint",
    "listen": "port",
    "listening": "port",
    "process": "port",
}


@dataclasses.dataclass(frozen=True)
class LivenessCheck:
    kind: str
    target: str
    label: str = ""

    def display(self) -> str:
        if self.label:
            return self.label
        if self.kind == "systemd":
            return f"systemd active: {self.target}"
        if self.kind == "table":
            return f"table has rows: {self.target}"
        if self.kind == "file":
            return f"file exists: {self.target}"
        if self.kind == "endpoint":
            return f"endpoint 2xx: {self.target}"
        if self.kind == "port":
            return f"port listening: {self.target}"
        if self.kind == "command":
            return "legacy command"
        return f"{self.kind}: {self.target}"


@dataclasses.dataclass(frozen=True)
class CheckResult:
    check: LivenessCheck
    status: str
    detail: str

    def to_json(self) -> dict[str, Any]:
        return {
            "type": self.check.kind,
            "target": self.check.target,
            "label": self.check.display(),
            "status": self.status,
            "detail": self.detail,
        }


@dataclasses.dataclass(frozen=True)
class ProbeReport:
    status: str
    checks: tuple[CheckResult, ...]
    spec_id: str = ""
    decision_id: str = ""
    branch: str = ""
    followup_queued: bool = False

    def event(self) -> str:
        if self.status == "live":
            return "liveness:pass"
        if self.status == "planned":
            return "liveness:planned"
        if self.status == "partial":
            return "liveness:partial"
        return "liveness:fail"

    def detail(self) -> str:
        prefix = self.spec_id or self.decision_id or "build"
        if self.status == "planned":
            return f"{prefix} planned (no liveness declaration)"
        bits = [f"{item.check.display()} -> {item.status} ({item.detail})" for item in self.checks]
        return f"{prefix} {self.status}: " + "; ".join(bits[:5])

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "event": self.event(),
            "spec_id": self.spec_id,
            "decision_id": self.decision_id,
            "branch": self.branch,
            "followup_queued": self.followup_queued,
            "checks": [item.to_json() for item in self.checks],
        }


class ProbeRunner:
    def __init__(
        self,
        repo_root: Path,
        *,
        timeout: float = 5.0,
        allow_external_endpoints: bool = False,
        db_url: str = DB_URL,
    ) -> None:
        self.repo_root = repo_root
        self.timeout = timeout
        self.allow_external_endpoints = allow_external_endpoints
        self.db_url = db_url

    def check(self, item: LivenessCheck) -> CheckResult:
        if item.kind == "systemd":
            status, detail = self._check_systemd(item.target)
        elif item.kind == "table":
            status, detail = self._check_table(item.target)
        elif item.kind == "file":
            status, detail = self._check_file(item.target)
        elif item.kind == "endpoint":
            status, detail = self._check_endpoint(item.target)
        elif item.kind == "port":
            status, detail = self._check_port(item.target)
        elif item.kind == "command":
            status, detail = self._check_command(item.target)
        else:
            status, detail = "unknown", f"unsupported liveness type {item.kind}"
        return CheckResult(item, status, detail)

    def _check_file(self, target: str) -> tuple[str, str]:
        path = Path(target)
        if not path.is_absolute():
            path = self.repo_root / target
        return ("live", "exists") if path.exists() else ("dead", "missing")

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

    def _check_table(self, target: str) -> tuple[str, str]:
        schema, table = _split_table(target)
        try:
            import psycopg
        except ImportError:
            return "unknown", "psycopg unavailable"
        try:
            with psycopg.connect(self.db_url, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT to_regclass(%s)", (f"{schema}.{table}",))
                    exists = cur.fetchone()[0]
                    if not exists:
                        return "dead", "table missing"
                    cur.execute(f"SELECT COUNT(*) FROM {_safe_identifier(schema)}.{_safe_identifier(table)}")
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
        return ("live", f"HTTP {code}") if 200 <= code < 300 else ("dead", f"HTTP {code}")

    def _check_port(self, target: str) -> tuple[str, str]:
        host, port = _split_host_port(target)
        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                return "live", f"{host}:{port} accepts TCP"
        except OSError as exc:
            return "dead", f"{host}:{port} not listening: {exc}"

    def _check_command(self, command: str) -> tuple[str, str]:
        try:
            result = subprocess.run(
                ["bash", "-lc", command],
                cwd=self.repo_root,
                timeout=self.timeout,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "unknown", f"legacy command failed to run: {exc}"
        detail = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        if not detail:
            detail = f"rc={result.returncode}"
        return ("live", detail[:180]) if result.returncode == 0 else ("dead", f"rc={result.returncode} {detail[:160]}")


def parse_liveness(text: str) -> tuple[LivenessCheck, ...]:
    raw = str(text or "").strip()
    if not raw:
        return ()
    json_checks = _parse_json_checks(raw)
    if json_checks is not None:
        return tuple(json_checks)
    block = _extract_liveness_block(raw)
    if not block:
        return ()
    return tuple(_parse_block_checks(block))


def _parse_json_checks(raw: str) -> list[LivenessCheck] | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    payload = data.get("liveness") if isinstance(data, dict) and "liveness" in data else data
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    return [_check_from_mapping(item) for item in payload if isinstance(item, dict) and _check_from_mapping(item)]


def _extract_liveness_block(raw: str) -> str:
    lines = raw.splitlines()
    out: list[str] = []
    capture = False
    base_indent = 0
    for line in lines:
        if not capture:
            if re.match(r"^\s*liveness\s*:\s*$", line, re.I):
                capture = True
                base_indent = len(line) - len(line.lstrip())
            continue
        if line.strip() == "":
            out.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base_indent and re.match(r"^\S", line):
            break
        if indent <= base_indent and line.lstrip().startswith("#"):
            break
        out.append(line[base_indent + 1 :] if len(line) > base_indent else line)
    return "\n".join(out)


def _parse_block_checks(block: str) -> list[LivenessCheck]:
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if current:
                items.append(current)
            current = {}
            line = line[2:].strip()
            if line:
                _parse_key_value_into(current, line)
            continue
        if current is None:
            current = {}
        _parse_key_value_into(current, line)
    if current:
        items.append(current)
    checks = [_check_from_mapping(item) for item in items]
    return [item for item in checks if item]


def _parse_key_value_into(target: dict[str, str], line: str) -> None:
    if ":" not in line:
        return
    key, value = line.split(":", 1)
    target[key.strip().lower().replace("-", "_")] = value.strip().strip("'\"")


def _check_from_mapping(item: dict[str, Any]) -> LivenessCheck | None:
    lower = {str(k).lower().replace("-", "_"): str(v).strip() for k, v in item.items() if v is not None}
    kind = lower.get("type") or lower.get("kind") or ""
    target = ""
    for key, candidate_kind in (
        ("unit", "systemd"),
        ("systemd", "systemd"),
        ("table", "table"),
        ("db_table", "table"),
        ("path", "file"),
        ("file", "file"),
        ("url", "endpoint"),
        ("endpoint", "endpoint"),
        ("port", "port"),
        ("listen", "port"),
        ("command", "command"),
    ):
        if lower.get(key):
            target = lower[key]
            kind = kind or candidate_kind
            break
    kind = KIND_ALIASES.get(kind, kind)
    if not kind or not target:
        return None
    return LivenessCheck(kind=kind, target=target, label=lower.get("label", ""))


def run_probe(
    declaration: str,
    *,
    repo_root: Path = REPO_ROOT,
    spec_text: str = "",
    legacy_command: str = "",
    spec_id: str = "",
    decision_id: str = "",
    branch: str = "",
    runner: ProbeRunner | None = None,
) -> ProbeReport:
    checks = list(parse_liveness(declaration))
    if not checks and spec_text:
        checks = list(parse_liveness(spec_text))
    if not checks and legacy_command.strip():
        checks = [LivenessCheck("command", legacy_command.strip())]
    if not checks:
        return ProbeReport("planned", (), spec_id=spec_id, decision_id=decision_id, branch=branch)
    runner = runner or ProbeRunner(
        repo_root,
        timeout=float(os.environ.get("LIVENESS_PROBE_TIMEOUT", "120")),
        allow_external_endpoints=os.environ.get("LIVENESS_ALLOW_EXTERNAL_ENDPOINTS", "").lower() in {"1", "true", "yes", "on"},
    )
    results = tuple(runner.check(item) for item in checks)
    statuses = [item.status for item in results]
    if statuses and all(status == "live" for status in statuses):
        status = "live"
    elif "live" in statuses:
        status = "partial"
    else:
        status = "dead"
    return ProbeReport(status, results, spec_id=spec_id, decision_id=decision_id, branch=branch)


def append_ops_ledger(path: Path, report: ProbeReport) -> bool:
    payload = {
        "ts": utc_now(),
        "loop": "liveness",
        "event": report.event(),
        "detail": report.detail(),
        "cost": "$0",
        "artifact": report.branch,
        "next": "Auto-queued activation follow-up spec." if report.status in {"dead", "partial"} else "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "liveness_status": report.status,
        "spec_id": report.spec_id,
        "decision_id": report.decision_id,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return True
    except OSError:
        return False


def _has_command(name: str) -> bool:
    return subprocess.run(["/usr/bin/env", "bash", "-lc", f"command -v {name} >/dev/null 2>&1"], check=False).returncode == 0


def _split_table(value: str) -> tuple[str, str]:
    text = value.strip()
    if "." in text:
        schema, table = text.split(".", 1)
        return schema, table
    return "brain_index", text


def _split_host_port(value: str) -> tuple[str, int]:
    text = value.strip()
    if ":" in text:
        host, raw_port = text.rsplit(":", 1)
    else:
        host, raw_port = "127.0.0.1", text
    return host or "127.0.0.1", int(raw_port)


def _safe_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"unsafe SQL identifier: {value}")
    return value


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--declaration", default="")
    parser.add_argument("--spec-file", type=Path)
    parser.add_argument("--legacy-command", default="")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--spec-id", default=os.environ.get("SPECID", ""))
    parser.add_argument("--decision-id", default=os.environ.get("DID", ""))
    parser.add_argument("--branch", default=os.environ.get("BR", ""))
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--no-ledger", action="store_true")
    args = parser.parse_args(argv)

    spec_text = ""
    if args.spec_file and args.spec_file.exists():
        spec_text = args.spec_file.read_text(encoding="utf-8", errors="replace")
    report = run_probe(
        args.declaration,
        repo_root=args.repo_root,
        spec_text=spec_text,
        legacy_command=args.legacy_command,
        spec_id=args.spec_id,
        decision_id=args.decision_id,
        branch=args.branch,
    )
    if not args.no_ledger:
        append_ops_ledger(args.ops_ledger, report)
    print(json.dumps(report.to_json(), sort_keys=True))
    return 0 if report.status in {"live", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
