#!/usr/bin/env python3
"""Security Sentinel agent.

Report-only scanner for local evidence of security exposure, exploit-ready
system posture, adversarial user behavior, and guardrail circumvention attempts.
It does not probe networks, read external secret stores, inspect private key
material, install services, restart daemons, or enforce policy. It scans
repo-local text/config files and redacts emitted evidence. Alerts are opt-in and
only counted as sent when the notifier explicitly reports a send.
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
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = REPO_ROOT / "core" / "BUILD" / "signals" / "security_sentinel.json"
DEFAULT_MD = REPO_ROOT / "core" / "BUILD" / "signals" / "security_sentinel.md"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_DISABLE_FILE = Path(os.environ.get("SECURITY_SENTINEL_DISABLE_FILE", "/opt/fpai-build/.security_sentinel_disabled"))
DEFAULT_COOLDOWN_FILE = Path(os.environ.get("SECURITY_SENTINEL_COOLDOWN_FILE", "/opt/fpai-build/.security_sentinel_last_alert"))
SCHEMA = "security-sentinel.v1"

CATEGORIES = ("hardware", "system", "adversarial_behavior", "circumvention", "control_plane")
ACTIVE_DIRS = ("tools", "SERVICES", "scripts", "core/BUILD/cron", "core/BUILD/systemd")
TEXT_SUFFIXES = {".py", ".sh", ".md", ".json", ".yml", ".yaml", ".service", ".timer", ".conf", ".toml", ".txt"}
RUNNABLE_SUFFIXES = {".py", ".sh", ".json", ".yml", ".yaml", ".service", ".timer", ".conf", ".toml"}
EXCLUDED_PARTS = {"venv", ".venv", "node_modules", "__pycache__", "site-packages", ".tox", ".mypy_cache"}
SECRET_FILE_RE = re.compile(r"(^\.env$|creds|credential|secret|private[_-]?key|id_rsa|\.pem$|\.key$)", re.I)

PRIVILEGE_RE = re.compile(
    r"\b(User=root|sudo\b|--privileged\b|network_mode\s*:\s*host|--network=host|"
    r"CAP_SYS_ADMIN|SYS_ADMIN|/var/run/docker\.sock|docker\.sock|/dev/kvm|"
    r"/dev/mem|/dev/sd[a-z]|chmod\s+777|setenforce\s+0)\b",
    re.I,
)
INSECURE_FETCH_RE = re.compile(r"(curl|wget)[^\n|;&]{0,120}(\|\s*(bash|sh)|>\s*/tmp/)", re.I)
CIRCUMVENTION_RE = re.compile(
    r"\b(ignore (the )?(contract|guardrail|safety|instructions)|bypass|circumvent|"
    r"disable (the )?(guard|sentinel|watchdog|tests|review)|skip (tests|review|merge gate)|"
    r"force[- ]?push|push to main|no review|jailbreak|exfiltrat|leak secret|dump token)\b",
    re.I,
)
SECRET_SHAPE_RE = re.compile(r"\b(api[_-]?key|token|secret|private[_-]?key|password)\b", re.I)
LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_=-]{24,}\b")
URL_RE = re.compile(r"https?://[^\s\"']+")
LEDGER_EVIDENCE_KEYS = ("ts", "loop", "event", "status", "surface", "detail", "next", "artifact")


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


def ascii_clean(value: str) -> str:
    return value.encode("ascii", "replace").decode("ascii").replace("?", "-")


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


def iter_text_files(repo_root: Path, dirs: Iterable[str] = ACTIVE_DIRS) -> Iterable[Path]:
    for dirname in dirs:
        root = repo_root / dirname
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if SECRET_FILE_RE.search(path.name):
                continue
            rel = path.relative_to(repo_root).parts
            if EXCLUDED_PARTS.intersection(rel):
                continue
            if path.resolve() == Path(__file__).resolve():
                continue
            if "test" in path.stem or path.stem.startswith("test_"):
                continue
            if rel[:3] in {("core", "BUILD", "signals"), ("core", "BUILD", "results"), ("core", "BUILD", "reviews")}:
                continue
            yield path


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


def load_registry(repo_root: Path) -> dict[str, Any]:
    try:
        data = json.loads((repo_root / "core" / "BUILD" / "REGISTRY.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _line_hits(path: Path, pattern: re.Pattern[str], repo_root: Path) -> list[str]:
    hits: list[str] = []
    for number, line in enumerate(read_text(path).splitlines(), start=1):
        if pattern.search(line):
            snippet = line.strip()
            if SECRET_SHAPE_RE.search(snippet):
                snippet = SECRET_SHAPE_RE.sub("[secret-keyword]", snippet)
            hits.append(ascii_clean(f"{path.relative_to(repo_root)}:{number}: {snippet[:180]}"))
    return hits


def scan_hardware_and_system(repo_root: Path) -> list[Finding]:
    privilege_hits: list[str] = []
    fetch_hits: list[str] = []
    for path in iter_text_files(repo_root):
        if path.suffix not in RUNNABLE_SUFFIXES:
            continue
        privilege_hits.extend(_line_hits(path, PRIVILEGE_RE, repo_root))
        fetch_hits.extend(_line_hits(path, INSECURE_FETCH_RE, repo_root))

    findings: list[Finding] = []
    if privilege_hits:
        findings.append(Finding(
            "hardware",
            5 if len(privilege_hits) >= 4 else 4,
            "Privileged host or hardware access appears in runnable artifacts",
            "Root users, host networking, docker socket access, device mounts, or broad capabilities make hardware/system exploits more consequential.",
            tuple(privilege_hits[:24]),
            "Review each privileged path; move live units toward least privilege, named users, bounded capabilities, and explicit installation approval.",
        ))
    if fetch_hits:
        findings.append(Finding(
            "system",
            4,
            "Shell-fetch execution patterns are present",
            "Download-and-execute flows are high-risk when run from autonomous jobs or build hosts.",
            tuple(fetch_hits[:16]),
            "Replace with pinned artifacts, checksums, or reviewed package-manager installs before live use.",
        ))
    return findings


def scan_adversarial_repo_text(repo_root: Path) -> list[Finding]:
    hits: list[str] = []
    for path in iter_text_files(repo_root):
        if path.suffix not in RUNNABLE_SUFFIXES:
            continue
        hits.extend(_line_hits(path, CIRCUMVENTION_RE, repo_root))
    if not hits:
        return []
    return [Finding(
        "circumvention",
        4 if len(hits) < 8 else 5,
        "Guardrail circumvention language appears in active runnable surfaces",
        "Instructions or scripts that mention bypassing reviews, tests, guards, or main-branch protections deserve review before autonomous execution.",
        tuple(hits[:24]),
        "Classify each hit as test fixture, benign warning, or actionable bypass path; remove or gate actionable paths.",
    )]


def scan_ops_ledger(ops_ledger: Path, now: dt.datetime) -> list[Finding]:
    rows = read_jsonl(ops_ledger)
    if not rows:
        return [Finding(
            "adversarial_behavior",
            3,
            "No ops-ledger evidence available for behavior monitoring",
            "The sentinel cannot detect recent circumvention attempts without the append-only ops ledger.",
            (str(ops_ledger),),
            "Run the sentinel on a host with ops-ledger access or pass --ops-ledger to a current JSONL ledger.",
        )]

    recent_rows: list[dict[str, Any]] = []
    for row in rows:
        ts = parse_time(row.get("ts") or row.get("timestamp") or row.get("created_at"))
        if ts is None or (now - ts).total_seconds() <= 7 * 24 * 3600:
            recent_rows.append(row)

    suspicious: list[str] = []
    failed_security = 0
    for row in recent_rows:
        blob = " ".join(str(row.get(key, "")) for key in ("loop", "event", "detail", "next", "artifact", "status"))
        if CIRCUMVENTION_RE.search(blob):
            suspicious.append(summarize_suspicious_row(row))
        if row.get("event") in {"failed", "error"} and re.search(r"security|sentinel|guard|smoke|merge", blob, re.I):
            failed_security += 1

    findings: list[Finding] = []
    if suspicious:
        findings.append(Finding(
            "adversarial_behavior",
            5,
            "Recent ops-ledger rows look like guardrail circumvention attempts",
            "Recent operational evidence includes language about bypassing, disabling, skipping tests/reviews, force-pushing, or leaking secrets.",
            tuple(suspicious[:12]),
            "Route these rows to Ember/James for review before increasing autonomy on the affected path.",
        ))
    if failed_security >= 3:
        findings.append(Finding(
            "control_plane",
            4,
            "Repeated security/control-plane failures in recent ops ledger",
            f"{failed_security} recent rows mention failed security, sentinel, guard, smoke, or merge checks.",
            (str(ops_ledger),),
            "Treat repeated control-plane failure as a blocker for more autonomous live action until one clean proof run passes.",
        ))
    return findings


def redact_row(row: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in row.items():
        if SECRET_SHAPE_RE.search(str(key)):
            redacted[str(key)] = "[redacted]"
        elif isinstance(value, str) and SECRET_SHAPE_RE.search(value):
            redacted[str(key)] = SECRET_SHAPE_RE.sub("[secret-keyword]", value)
        else:
            redacted[str(key)] = value
    return redacted


def redact_text(value: str) -> str:
    redacted = SECRET_SHAPE_RE.sub("[secret-keyword]", value)
    redacted = URL_RE.sub("[url]", redacted)
    redacted = LONG_TOKEN_RE.sub("[long-token]", redacted)
    return ascii_clean(redacted)


def summarize_suspicious_row(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in LEDGER_EVIDENCE_KEYS:
        value = row.get(key)
        if value is None:
            continue
        text = str(value)
        if key in {"detail", "next", "artifact", "status"} and not CIRCUMVENTION_RE.search(text):
            continue
        if key in {"detail", "next", "artifact"}:
            text = redact_text(text)[:220]
        else:
            text = redact_text(text)[:80]
        parts.append(f"{key}={text}")
    return "; ".join(parts) if parts else "ops-ledger row matched circumvention pattern; fields redacted"


def scan_registry(repo_root: Path, now: dt.datetime) -> list[Finding]:
    registry = load_registry(repo_root)
    builds = [row for row in registry.get("active_builds", []) if isinstance(row, dict)]
    findings: list[Finding] = []
    unsafe_done = [
        str(row.get("id") or row.get("slug"))
        for row in builds
        if row.get("status") == "done" and row.get("tests_passed") is not True
    ]
    main_branch = [
        f"{row.get('id') or row.get('slug')}: {row.get('branch')}"
        for row in builds
        if str(row.get("branch", "")).strip() in {"main", "master"} or str(row.get("base_branch", "")).strip() in {"main", "master"}
    ]
    stale_building: list[str] = []
    for row in builds:
        if row.get("status") != "building":
            continue
        ts = parse_time(row.get("updated_at") or row.get("started_at") or registry.get("updated_at"))
        if ts and (now - ts).total_seconds() > 24 * 3600:
            stale_building.append(str(row.get("id") or row.get("slug")))

    if unsafe_done:
        findings.append(Finding(
            "control_plane",
            6,
            "Registry has done builds without passing tests",
            "Merge readiness should never mark a build done while tests_passed is false or missing.",
            tuple(unsafe_done[:16]),
            "Move each entry back to building/blocked or run the missing tests before merge review.",
        ))
    if main_branch:
        findings.append(Finding(
            "control_plane",
            6,
            "Registry references main/master for build work",
            "The build contract requires feat/headless-build based branches, never main.",
            tuple(main_branch[:16]),
            "Correct registry metadata and verify the branch ancestry before merge review.",
        ))
    if stale_building:
        findings.append(Finding(
            "control_plane",
            3,
            "Building entries appear stale",
            "Stale active-build rows can hide abandoned work and confuse autonomous routing.",
            tuple(stale_building[:16]),
            "Close, block, or refresh the stale build rows before routing more parallel work.",
        ))
    return findings


def summarize(findings: list[Finding]) -> dict[str, Any]:
    by_category = Counter(f.category for f in findings)
    return {
        "total_findings": len(findings),
        "max_severity": max((f.severity for f in findings), default=0),
        "p0": sum(1 for f in findings if f.severity >= 6),
        "p1": sum(1 for f in findings if 4 <= f.severity < 6),
        "p2": sum(1 for f in findings if f.severity < 4),
        "by_category": {category: by_category.get(category, 0) for category in CATEGORIES},
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Security Sentinel Report",
        "",
        f"**Generated:** {report['generated_at']}",
        "**Mode:** report-only local scan of repo-local text/config files; no network probing, external secret-store reads, private-key inspection, enforcement, deployment, spend, outreach, or service mutation. Emitted evidence is redacted.",
        "",
        "## Summary",
        "",
        f"- Total findings: {summary['total_findings']}",
        f"- Max severity: {summary['max_severity']}",
        f"- P0 findings: {summary['p0']}",
        f"- P1 findings: {summary['p1']}",
        f"- P2 findings: {summary['p2']}",
        "",
        "| Category | Findings |",
        "|---|---:|",
    ]
    for category, count in summary["by_category"].items():
        lines.append(f"| {category} | {count} |")
    lines.extend(["", "## Findings", ""])
    for finding in report["findings"]:
        lines.extend([
            f"### {finding['category']} - severity {finding['severity']} - {finding['title']}",
            f"- **Detail:** {finding['detail']}",
            f"- **Next action:** {finding['next_action']}",
            "- **Evidence:**",
        ])
        for item in finding["evidence"][:12]:
            lines.append(f"  - `{item}`")
        lines.append("")
    if not report["findings"]:
        lines.extend(["No deterministic security-sentinel findings crossed the current thresholds.", ""])
    return "\n".join(lines)


def append_ops(ops_ledger: Path, report_path: Path, summary: dict[str, Any]) -> bool:
    row = {
        "ts": utc_stamp(),
        "loop": "security_sentinel",
        "event": "failed" if summary["p0"] else ("proposed" if summary["total_findings"] else "ran"),
        "detail": f"security sentinel findings={summary['total_findings']} max_severity={summary['max_severity']}",
        "cost": "$0",
        "artifact": str(report_path),
        "next": "Review P0/P1 security findings before expanding autonomous authority." if summary["p0"] or summary["p1"] else "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    try:
        ops_ledger.parent.mkdir(parents=True, exist_ok=True)
        with ops_ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return True
    except OSError:
        return False


def should_alert(report: dict[str, Any], cooldown_file: Path, now: dt.datetime, cooldown_hours: int = 4) -> bool:
    if report["summary"]["max_severity"] < 4:
        return False
    latest = parse_time(read_text(cooldown_file).strip())
    if latest and (now - latest).total_seconds() < cooldown_hours * 3600:
        return False
    return True


def alert_message(report: dict[str, Any], markdown_path: Path = DEFAULT_MD) -> str:
    summary = report["summary"]
    top = report["findings"][0] if report["findings"] else None
    title = top["title"] if top else "No findings"
    return (
        "<b>Security Sentinel</b>\n"
        f"Findings: {summary['total_findings']} - max severity {summary['max_severity']} - P0 {summary['p0']} - P1 {summary['p1']}\n"
        f"Top: {html.escape(title)}\n"
        f"Report: {html.escape(str(markdown_path))}"
    )


def send_alert(repo_root: Path, message: str) -> bool:
    notifier = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    if not notifier.exists():
        return False
    try:
        result = subprocess.run(
            [str(notifier), message],
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    output = f"{result.stdout}\n{result.stderr}"
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
    send_alert_flag: bool = False,
    no_ledger: bool = False,
) -> dict[str, Any]:
    current = now or utc_now()
    if disable_file.exists():
        return {
            "schema": SCHEMA,
            "generated_at": utc_stamp(current),
            "disabled": True,
            "findings": [],
            "summary": summarize([]),
            "ledger_written": False,
            "alert_sent": False,
        }

    findings: list[Finding] = []
    findings.extend(scan_hardware_and_system(repo_root))
    findings.extend(scan_adversarial_repo_text(repo_root))
    findings.extend(scan_ops_ledger(ops_ledger, current))
    findings.extend(scan_registry(repo_root, current))
    findings = sorted(findings, key=lambda item: (-item.severity, item.category, item.title))
    summary = summarize(findings)
    report = {
        "schema": SCHEMA,
        "generated_at": utc_stamp(current),
        "disabled": False,
        "repo_root": str(repo_root),
        "ops_ledger": str(ops_ledger),
        "summary": summary,
        "findings": [finding.to_json() for finding in findings],
        "ledger_written": False,
        "alert_sent": False,
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    if not no_ledger:
        report["ledger_written"] = append_ops(ops_ledger, markdown_path, summary)
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if send_alert_flag and should_alert(report, cooldown_file, current):
        sent = send_alert(repo_root, alert_message(report, markdown_path))
        report["alert_sent"] = sent
        if sent:
            cooldown_file.parent.mkdir(parents=True, exist_ok=True)
            cooldown_file.write_text(utc_stamp(current), encoding="utf-8")
            json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the report-only Security Sentinel agent.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", dest="json_path", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", dest="markdown_path", type=Path, default=DEFAULT_MD)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--disable-file", type=Path, default=DEFAULT_DISABLE_FILE)
    parser.add_argument("--cooldown-file", type=Path, default=DEFAULT_COOLDOWN_FILE)
    parser.add_argument("--send-alert", action="store_true", help="Send Telegram alert only when notifier reports notify: sent.")
    parser.add_argument("--no-ledger", action="store_true", help="Do not append an ops-ledger row.")
    parser.add_argument("--print-json", action="store_true", help="Print the report JSON to stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        repo_root=args.repo_root,
        json_path=args.json_path,
        markdown_path=args.markdown_path,
        ops_ledger=args.ops_ledger,
        disable_file=args.disable_file,
        cooldown_file=args.cooldown_file,
        send_alert_flag=args.send_alert,
        no_ledger=args.no_ledger,
    )
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "security-sentinel: "
            f"findings={summary['total_findings']} "
            f"p0={summary['p0']} p1={summary['p1']} max={summary['max_severity']} "
            f"report={args.markdown_path}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
