#!/usr/bin/env python3
"""Proactive failure watchdog.

Scans repo-local and ledger evidence for single points of failure across the
server, memory, revenue, agent, and dependency layers. It is report-only by
default; live alerting is opt-in through ``--send-alert`` and still mutates no
production service state.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import html
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = REPO_ROOT / "core" / "BUILD" / "signals" / "failure_watchdog.json"
DEFAULT_MD = REPO_ROOT / "core" / "BUILD" / "signals" / "failure_watchdog.md"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_DISABLE_FILE = Path(os.environ.get("FAILURE_WATCHDOG_DISABLE_FILE", "/opt/fpai-build/.failure_watchdog_disabled"))
DEFAULT_COOLDOWN_FILE = Path(os.environ.get("FAILURE_WATCHDOG_COOLDOWN_FILE", "/opt/fpai-build/.failure_watchdog_last_alert"))
SCHEMA = "failure-watchdog.v1"

WATCH_CATEGORIES = ("server", "memory", "revenue", "agents", "dependencies")
ACTIVE_SCAN_DIRS = ("tools", "SERVICES", "scripts", "core")
DIRECT_IP_RE = re.compile(r"\b(?:(?:\d{1,3}\.){3}\d{1,3})(?::[0-9]{2,5})?\b")
REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+(?:\[[^\]]+\])?)\s*([<>=!~]=|==|>=|<=|~=|>|<)?\s*([^#;\s]+)?")
NODE_VERSION_RE = re.compile(r"^(?:npm:)?(?:[~^]|>=|<=|>|<|=)?\s*([0-9][^|\s]*)")


@dataclasses.dataclass(frozen=True)
class Finding:
    category: str
    severity: int
    title: str
    detail: str
    evidence: tuple[str, ...]
    next_action: str

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_stamp(now: dt.datetime | None = None) -> str:
    return (now or utc_now()).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def iter_text_files(repo_root: Path, dirs: Iterable[str] = ACTIVE_SCAN_DIRS) -> Iterable[Path]:
    suffixes = {".py", ".sh", ".md", ".txt", ".json", ".yml", ".yaml", ".service", ".timer", ".conf", ".env", ".toml"}
    for dirname in dirs:
        root = repo_root / dirname
        if not root.exists():
            continue
        for path in root.rglob("*"):
            rel_parts = path.relative_to(repo_root).parts
            if "test" in path.stem or path.stem.startswith("test_"):
                continue
            if rel_parts[:3] == ("core", "BUILD", "signals"):
                continue
            if rel_parts[:3] == ("core", "BUILD", "results"):
                continue
            if path.is_file() and path.suffix in suffixes and ".git" not in path.parts:
                yield path


def parse_time(value: Any) -> dt.datetime | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        raw = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(raw)
        except ValueError:
            try:
                parsed = dt.datetime.strptime(str(value).strip(), "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def is_fixed_endpoint(token: str) -> bool:
    host = token.split(":", 1)[0]
    try:
        parts = [int(part) for part in host.split(".")]
    except ValueError:
        return False
    if len(parts) != 4 or any(part < 0 or part > 255 for part in parts):
        return False
    first, second = parts[0], parts[1]
    if host == "127.0.0.1":
        return ":" in token
    if first == 0 or first == 10 or first == 127:
        return False
    if first == 172 and 16 <= second <= 31:
        return False
    if first == 192 and second == 168:
        return False
    if first >= 224:
        return False
    return True


def endpoint_matches(text: str) -> list[str]:
    return sorted({match.group(0) for match in DIRECT_IP_RE.finditer(text) if is_fixed_endpoint(match.group(0))})


def scan_server(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    direct_refs: list[str] = []
    for path in iter_text_files(repo_root):
        text = read_text(path)
        if not text:
            continue
        matches = endpoint_matches(text)
        if matches:
            rel = path.relative_to(repo_root)
            direct_refs.append(f"{rel}: {', '.join(matches[:3])}")
    active_refs = [ref for ref in direct_refs if not ref.startswith(("docs/codex/SERVER_162_REDUNDANCY_FAILOVER.md",))]
    if active_refs:
        severity = 5 if len(active_refs) >= 8 else 4
        findings.append(Finding(
            "server",
            severity,
            "Direct host/IP dependencies remain in active repo surfaces",
            "Direct IP or localhost endpoint references make failover dependent on manual edits or exact host topology.",
            tuple(active_refs[:20]),
            "Replace active direct-IP defaults with named aliases or env-driven endpoints, then re-run d059 failover proof.",
        ))

    host_registry = read_text(repo_root / "docs" / "codex" / "HOST_REGISTRY.md")
    if not host_registry or re.search(r"Live heartbeat coverage\s*\|\s*none yet", host_registry, re.I):
        findings.append(Finding(
            "server",
            4,
            "Host heartbeat coverage is not proved",
            "The host registry still separates repo metadata from live heartbeat truth, so server death may be noticed late.",
            ("docs/codex/HOST_REGISTRY.md has no live heartbeat coverage",),
            "Run or build the read-only live heartbeat proof from an approved host lane.",
        ))
    return findings


def scan_memory(repo_root: Path, ops_ledger: Path, now: dt.datetime) -> list[Finding]:
    findings: list[Finding] = []
    required = (
        repo_root / "docs" / "codex" / "AI_PROTOCOLS.md",
        repo_root / "docs" / "codex" / "HANDOFF.md",
        repo_root / "docs" / "codex" / "INDEX_OF_INDEXES.md",
    )
    missing = [str(path.relative_to(repo_root)) for path in required if not path.exists()]
    if missing:
        findings.append(Finding(
            "memory",
            6,
            "Core memory mirror files are missing",
            "Fresh Codex/Ember sessions would lose orientation without these repo-side mirrors.",
            tuple(missing),
            "Restore the missing mirror files before running more autonomous build work.",
        ))

    rows = read_jsonl(ops_ledger)
    smoke_rows = [row for row in rows if row.get("loop") == "smoke_test" and str(row.get("event", "")).startswith("smoke")]
    if not smoke_rows:
        findings.append(Finding(
            "memory",
            4,
            "No recent smoke-test proof in ops ledger",
            "Memory and pipeline canary checks may be absent from the regular proof stream.",
            (str(ops_ledger),),
            "Install/verify the d049 smoke-test timer or run one silent smoke proof from the live host.",
        ))
    else:
        latest = max(smoke_rows, key=lambda row: parse_time(row.get("ts")) or dt.datetime.min.replace(tzinfo=dt.timezone.utc))
        latest_ts = parse_time(latest.get("ts"))
        age_hours = ((now - latest_ts).total_seconds() / 3600.0) if latest_ts else 9999
        status = str(latest.get("status") or latest.get("event") or "").upper()
        if "FAIL" in status or latest.get("event") == "smoke_fail":
            findings.append(Finding(
                "memory",
                6,
                "Latest smoke-test proof failed",
                str(latest.get("detail") or "smoke test failed"),
                (json.dumps(latest, sort_keys=True)[:500],),
                "Inspect the failed smoke check before routing new autonomous work.",
            ))
        elif age_hours > 8:
            findings.append(Finding(
                "memory",
                4,
                "Smoke-test proof is stale",
                f"Latest smoke-test row is {age_hours:.1f} hours old.",
                (json.dumps(latest, sort_keys=True)[:500],),
                "Restart or verify fpai-smoke-test.timer on the live host.",
            ))
    return findings


def scan_revenue(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    results_engine = read_text(repo_root / "tools" / "results" / "engine.py")
    if "tier: human" in results_engine or "warm leads" in results_engine.lower():
        findings.append(Finding(
            "revenue",
            3,
            "Revenue front door still has a human-edge dependency",
            "The results engine names revenue opportunities, but warm lead selection and final outreach remain James/human gated.",
            ("tools/results/engine.py contains human-tier revenue next steps",),
            "Keep the watchdog reporting this as a dependency until a separate approved intake/lead-capture proof exists.",
        ))
    revenue_paths = []
    for path in iter_text_files(repo_root, ("tools", "scripts", "SERVICES")):
        rel = str(path.relative_to(repo_root)).lower()
        if not any(term in rel for term in ("revenue", "financial", "treasury", "payment", "stripe", "outbound")):
            continue
        matches = endpoint_matches(read_text(path))
        if matches:
            revenue_paths.append(f"{path.relative_to(repo_root)}: {', '.join(matches)}")
    if revenue_paths:
        findings.append(Finding(
            "revenue",
            4,
            "Revenue surfaces contain direct endpoint dependencies",
            "Revenue-related paths still reference concrete host endpoints, which can break income flow when a server moves.",
            tuple(revenue_paths[:12]),
            "Move revenue endpoints behind env vars or host aliases and add a live heartbeat check.",
        ))
    return findings


def load_registry(repo_root: Path) -> dict[str, Any]:
    try:
        data = json.loads((repo_root / "core" / "BUILD" / "REGISTRY.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def scan_agents(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    registry = load_registry(repo_root)
    builds = [row for row in registry.get("active_builds", []) if isinstance(row, dict)]
    building = [row for row in builds if row.get("status") == "building"]
    blocked = [row for row in builds if row.get("status") == "blocked"]
    if len(building) > 1:
        findings.append(Finding(
            "agents",
            4,
            "Multiple builds are marked building",
            "Parallel build registrations raise collision risk unless each has isolated files and branch ownership.",
            tuple(str(row.get("id") or row.get("slug")) for row in building[:10]),
            "Clear stale building entries or confirm each active branch with the merge gate before starting more work.",
        ))
    if blocked:
        findings.append(Finding(
            "agents",
            3,
            "Blocked build entries remain in the registry",
            "Blocked agent work can become invisible backlog and repeated failure if not routed.",
            tuple(str(row.get("id") or row.get("slug")) for row in blocked[:10]),
            "Route one blocked entry to Ember/James or close it with an explicit result.",
        ))
    subscription_map = repo_root / "docs" / "codex" / "SUBSCRIPTION_DEPENDENCY_MAP.md"
    if not subscription_map.exists():
        findings.append(Finding(
            "agents",
            5,
            "Agent subscription dependency map is missing",
            "Claude/Codex subscription pull failure modes would be implicit again.",
            ("docs/codex/SUBSCRIPTION_DEPENDENCY_MAP.md",),
            "Restore or rebuild d055 before relying on autonomous agent routing.",
        ))
    scoring_ledger = repo_root / "core" / "BUILD" / "signals" / "agent_scoring_ledger.jsonl"
    if not scoring_ledger.exists() or not read_jsonl(scoring_ledger):
        findings.append(Finding(
            "agents",
            3,
            "Agent scoring ledger is absent or empty",
            "Agent/model placement has no recent advisory score memory.",
            ("core/BUILD/signals/agent_scoring_ledger.jsonl",),
            "Run the advisory agent benchmark intelligence timer on a reviewed host.",
        ))
    return findings


def requirement_files(repo_root: Path) -> list[Path]:
    roots = ("SERVICES", "PRODUCTS", "DASHBOARDS", "droplets")
    out: list[Path] = []
    for dirname in roots:
        root = repo_root / dirname
        if root.exists():
            out.extend(root.rglob("requirements*.txt"))
            out.extend(root.rglob("pyproject.toml"))
            out.extend(root.rglob("package.json"))
    return sorted(set(path for path in out if path.is_file()))


def scan_dependencies(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    req_files = requirement_files(repo_root)
    if len(req_files) >= 50:
        findings.append(Finding(
            "dependencies",
            3,
            "Large dependency surface spans many service manifests",
            f"{len(req_files)} requirement/package manifests are present across the repo.",
            tuple(str(path.relative_to(repo_root)) for path in req_files[:12]),
            "Prioritize a dependency BOM/lock audit for live services before broad service activation.",
        ))
    specs: dict[str, set[str]] = defaultdict(set)
    unpinned: list[str] = []
    for path in req_files:
        if path.name.startswith("requirements"):
            for line in read_text(path).splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                    continue
                match = REQ_RE.match(stripped)
                if not match:
                    continue
                name, operator, version = match.groups()
                package = name.split("[", 1)[0].lower().replace("_", "-")
                if operator == "==" and version:
                    specs[package].add(version)
                elif not operator:
                    unpinned.append(f"{path.relative_to(repo_root)}: {stripped}")
        elif path.name == "pyproject.toml":
            for dep in pyproject_dependencies(path):
                package, operator, version = parse_python_dependency(dep)
                if not package:
                    continue
                if operator == "==" and version:
                    specs[package].add(version)
                elif not operator:
                    unpinned.append(f"{path.relative_to(repo_root)}: {dep}")
        elif path.name == "package.json":
            for package, version in package_json_dependencies(path).items():
                normalized = package.lower()
                pinned = NODE_VERSION_RE.match(version or "")
                if pinned and not version.startswith(("^", "~", ">", "<", "*")):
                    specs[normalized].add(pinned.group(1))
                else:
                    unpinned.append(f"{path.relative_to(repo_root)}: {package}@{version}")
    conflicts = [f"{package}: {', '.join(sorted(versions))}" for package, versions in sorted(specs.items()) if len(versions) > 1]
    if conflicts:
        findings.append(Finding(
            "dependencies",
            4,
            "Conflicting pinned dependency versions exist",
            "Different services pin the same package to different versions, increasing deploy/restore drift risk.",
            tuple(conflicts[:20]),
            "Create a reviewed dependency BOM for live services and reconcile conflicts service by service.",
        ))
    if len(unpinned) >= 25:
        findings.append(Finding(
            "dependencies",
            3,
            "Many dependencies are unpinned or floating",
            f"{len(unpinned)} dependency entries have no explicit fixed version.",
            tuple(unpinned[:20]),
            "For live services, pin direct dependencies or record why floating versions are acceptable.",
        ))
    return findings


def parse_python_dependency(raw: str) -> tuple[str, str | None, str | None]:
    stripped = raw.strip()
    match = REQ_RE.match(stripped)
    if not match:
        return "", None, None
    name, operator, version = match.groups()
    package = name.split("[", 1)[0].lower().replace("_", "-")
    return package, operator, version


def pyproject_dependencies(path: Path) -> list[str]:
    text = read_text(path)
    if not text:
        return []
    deps: list[str] = []
    for match in re.finditer(r"(?ms)^\s*dependencies\s*=\s*\[(.*?)\]", text):
        deps.extend(re.findall(r'"([^"]+)"|\'([^\']+)\'', match.group(1)))
    normalized: list[str] = []
    for item in deps:
        if isinstance(item, tuple):
            normalized.append(next((part for part in item if part), ""))
        else:
            normalized.append(str(item))
    deps = [item for item in normalized if item]

    current_section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line.strip("[]")
            continue
        if current_section != "tool.poetry.dependencies" or "=" not in line:
            continue
        package, version = [part.strip() for part in line.split("=", 1)]
        if package.lower() == "python":
            continue
        version = version.strip('"\'')
        deps.append(f"{package}=={version}" if version[:1].isdigit() else package)
    return deps


def package_json_dependencies(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        values = data.get(key)
        if isinstance(values, dict):
            for package, version in values.items():
                out[str(package)] = str(version)
    return out


def summarize(findings: list[Finding]) -> dict[str, Any]:
    by_category = Counter(f.category for f in findings)
    max_severity = max((f.severity for f in findings), default=0)
    p0 = sum(1 for f in findings if f.severity >= 6)
    p1 = sum(1 for f in findings if 4 <= f.severity < 6)
    p2 = sum(1 for f in findings if f.severity < 4)
    return {
        "total_findings": len(findings),
        "max_severity": max_severity,
        "p0": p0,
        "p1": p1,
        "p2": p2,
        "by_category": {category: by_category.get(category, 0) for category in WATCH_CATEGORIES},
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Proactive Failure Watchdog Report",
        "",
        f"**Generated:** {report['generated_at']}",
        "**Mode:** report-only local scan; no SSH, deploy, service restart, spend, outreach, or secret access.",
        "",
        "## Summary",
        "",
    ]
    summary = report["summary"]
    lines.extend([
        f"- Total findings: {summary['total_findings']}",
        f"- Max severity: {summary['max_severity']}",
        f"- P0 findings: {summary['p0']}",
        f"- P1 findings: {summary['p1']}",
        f"- P2 findings: {summary['p2']}",
        "",
        "| Category | Findings |",
        "|---|---:|",
    ])
    for category, count in summary["by_category"].items():
        lines.append(f"| {category} | {count} |")
    lines.extend(["", "## Findings", ""])
    for finding in report["findings"]:
        lines.extend([
            f"### {finding['category']} · severity {finding['severity']} · {finding['title']}",
            f"- **Detail:** {finding['detail']}",
            f"- **Next action:** {finding['next_action']}",
            "- **Evidence:**",
        ])
        for item in finding["evidence"][:12]:
            lines.append(f"  - `{item}`")
        lines.append("")
    if not report["findings"]:
        lines.extend(["No single-point-of-failure findings crossed the current deterministic thresholds.", ""])
    return "\n".join(lines)


def append_ops(ops_ledger: Path, report_path: Path, summary: dict[str, Any]) -> bool:
    row = {
        "ts": utc_stamp(),
        "loop": "failure_watchdog",
        "event": "failed" if summary["p0"] else ("proposed" if summary["total_findings"] else "ran"),
        "detail": f"failure watchdog findings={summary['total_findings']} max_severity={summary['max_severity']}",
        "cost": "$0",
        "artifact": str(report_path),
        "next": "review P0/P1 watchdog findings" if summary["p0"] or summary["p1"] else "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    try:
        ops_ledger.parent.mkdir(parents=True, exist_ok=True)
        with ops_ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return True
    except OSError:
        return False


def alert_message(report: dict[str, Any]) -> str:
    summary = report["summary"]
    top = report["findings"][0] if report["findings"] else None
    parts = [
        "<b>FPAI failure watchdog</b>",
        f"findings={summary['total_findings']} p0={summary['p0']} p1={summary['p1']} max={summary['max_severity']}",
    ]
    if top:
        parts.append(f"top: {html.escape(top['category'])} / severity {top['severity']} / {html.escape(top['title'])}")
        parts.append(f"next: {html.escape(top['next_action'])}")
    return "\n".join(parts)


def should_alert(report: dict[str, Any], cooldown_file: Path, now: dt.datetime, *, threshold: int = 4, cooldown_hours: int = 12) -> bool:
    if int(report["summary"]["max_severity"]) < threshold:
        return False
    last = parse_time(read_text(cooldown_file).strip())
    if last and (now - last).total_seconds() < cooldown_hours * 3600:
        return False
    return True


def send_alert(repo_root: Path, message: str) -> bool:
    script = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    if not script.exists():
        return False
    try:
        result = subprocess.run([str(script), message], cwd=repo_root, text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    output = f"{result.stdout}\n{result.stderr}".lower()
    return result.returncode == 0 and "notify: sent" in output


def run(
    *,
    repo_root: Path = REPO_ROOT,
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MD,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    disable_file: Path = DEFAULT_DISABLE_FILE,
    cooldown_file: Path = DEFAULT_COOLDOWN_FILE,
    now: dt.datetime | None = None,
    no_ledger: bool = False,
    send: bool = False,
) -> dict[str, Any]:
    now = now or utc_now()
    if disable_file.exists():
        report = {
            "schema": SCHEMA,
            "generated_at": utc_stamp(now),
            "disabled": True,
            "summary": summarize([]),
            "findings": [],
            "alert_sent": False,
            "ledger_written": False,
        }
        return report

    findings: list[Finding] = []
    findings.extend(scan_server(repo_root))
    findings.extend(scan_memory(repo_root, ops_ledger, now))
    findings.extend(scan_revenue(repo_root))
    findings.extend(scan_agents(repo_root))
    findings.extend(scan_dependencies(repo_root))
    findings = sorted(findings, key=lambda item: (item.severity, item.category, item.title), reverse=True)
    report = {
        "schema": SCHEMA,
        "generated_at": utc_stamp(now),
        "disabled": False,
        "summary": summarize(findings),
        "findings": [finding.to_json() for finding in findings],
        "alert_sent": False,
        "ledger_written": False,
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")

    if not no_ledger:
        report["ledger_written"] = append_ops(ops_ledger, markdown_path, report["summary"])
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if send and should_alert(report, cooldown_file, now):
        report["alert_sent"] = send_alert(repo_root, alert_message(report))
        if report["alert_sent"]:
            cooldown_file.parent.mkdir(parents=True, exist_ok=True)
            cooldown_file.write_text(utc_stamp(now), encoding="utf-8")
            json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan the FPAI stack for single points of failure.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--disable-file", type=Path, default=DEFAULT_DISABLE_FILE)
    parser.add_argument("--cooldown-file", type=Path, default=DEFAULT_COOLDOWN_FILE)
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--send-alert", action="store_true", help="send a Telegram alert for P1/P0 findings, honoring cooldown")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args(argv)
    report = run(
        repo_root=args.repo_root,
        json_path=args.json,
        markdown_path=args.markdown,
        ops_ledger=args.ops_ledger,
        disable_file=args.disable_file,
        cooldown_file=args.cooldown_file,
        no_ledger=args.no_ledger,
        send=args.send_alert,
    )
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "failure-watchdog: "
            f"findings={summary['total_findings']} "
            f"p0={summary['p0']} p1={summary['p1']} max={summary['max_severity']} "
            f"report={args.markdown}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
