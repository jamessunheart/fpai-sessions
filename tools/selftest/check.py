#!/usr/bin/env python3
"""Read-only observer for the self-standing one-day test.

This does not start timers, write vault files, send messages, move services, or
change git state. It only reports whether the system appears ready to run the
self-standing test and where the remaining risk is.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.router import route


HOME = Path.home()
DEFAULT_REPO = Path(os.environ.get("FPAI_REPO", HOME / "FPAI_Cockpit"))
DEFAULT_VAULT = Path(
    os.environ.get(
        "FPAI_VAULT",
        HOME
        / "Library"
        / "Mobile Documents"
        / "iCloud~md~obsidian"
        / "Documents"
        / "FPOS"
        / "Full Potential OS",
    )
)

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


@dataclasses.dataclass
class Check:
    name: str
    status: str
    evidence: str
    why: str


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def check_router_dry_run(repo: Path) -> Check:
    script = repo / "tools" / "router" / "route.py"
    if not script.exists():
        return Check("router dry-run", FAIL, "missing tools/router/route.py", "Rung 3 cannot route intents.")
    proc = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    out = (proc.stdout or proc.stderr).strip()
    if proc.returncode != 0:
        return Check("router dry-run", FAIL, out[-300:] or "nonzero exit", "Router must safely report the next step.")
    action = re.search(r"^action:\s*(.+)$", out, flags=re.MULTILINE)
    detail = action.group(1).strip() if action else "no action line"
    return Check("router dry-run", PASS, detail, "Router reports one next step without writing.")


def check_router_gate() -> Check:
    root = Path(tempfile.mkdtemp(prefix="fpai-selftest-gate-"))
    repo = root / "repo"
    vault = root / "vault"
    (repo / "docs" / "codex" / "specs").mkdir(parents=True)
    (vault / "00_MEMORY").mkdir(parents=True)
    (vault / "00_MEMORY" / "INTENT BUILDSTREAM.md").write_text(
        "# Intent Buildstream\n"
        f"{route.INTENTS_START}\n"
        "- id:money | value:5 | unlocks:test | status:ready | Treasury transfer - move money publicly\n"
        f"{route.INTENTS_END}\n",
        encoding="utf-8",
    )
    result = route.route_once(repo, vault, None, dry_run=False, append=False, skip_cost_guard=True)
    specs = list((repo / "docs" / "codex" / "specs").glob("*.md"))
    if result.action == "escalate" and not specs:
        return Check("reserved-class gate", PASS, result.detail, "Reserved work stops at James/Ember.")
    return Check(
        "reserved-class gate",
        FAIL,
        f"action={result.action}; specs={len(specs)}",
        "Money/public/irreversible work must never auto-draft or execute.",
    )


def latest_proof_row(vault: Path) -> str:
    proof = vault / "00_MEMORY" / "PROOF LOG.md"
    for line in read(proof).splitlines():
        if line.startswith("- "):
            return line
    return ""


def check_proof(vault: Path) -> Check:
    proof = vault / "00_MEMORY" / "PROOF LOG.md"
    if not proof.exists():
        return Check("proof log", FAIL, f"missing {proof}", "The return loop has no proof source.")
    row = latest_proof_row(vault)
    if not row:
        return Check("proof log", FAIL, "no proof rows found", "The return loop is empty.")
    required = ("Intent solved:", "Unlocks next:", "Proof:", "Next move:")
    missing = [field for field in required if field not in row]
    if missing:
        return Check("proof log", WARN, f"latest row missing {', '.join(missing)}", "Proof should drive the next loop.")
    if "self-standing one-day test" in row.lower():
        status = PASS
    else:
        status = WARN
    return Check("proof log", status, _clip(row), "Latest proof should name the next unlocked move.")


def parse_home_next(home_text: str) -> str:
    m = re.search(r"## ▶️ NEXT MOVE\s*\n\n\*\*(.+?)\*\*", home_text, flags=re.DOTALL)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def top_ready_intent(repo: Path, vault: Path) -> route.Intent | None:
    text, _ = route.load_intent_text(repo, vault, None)
    return route.choose_intent(route.parse_intents(text))


def check_home_buildstream(repo: Path, vault: Path) -> Check:
    home = vault / "HOME.md"
    home_next = parse_home_next(read(home))
    try:
        top = top_ready_intent(repo, vault)
    except Exception as exc:  # noqa: BLE001 - observer reports, does not crash the suite
        return Check("HOME / Buildstream agreement", FAIL, str(exc), "Need one canonical next move.")
    if not top:
        return Check("HOME / Buildstream agreement", FAIL, "no ready Buildstream intent", "Need one canonical next move.")
    home_low = home_next.lower()
    ok_home = "self-standing" in home_low or "go autonomous" in home_low
    ok_top = top.ident == "test" or "self-standing" in top.title.lower()
    status = PASS if ok_home and ok_top else WARN
    evidence = f"HOME={home_next or 'missing'}; Buildstream={top.ident}:{top.title}"
    return Check("HOME / Buildstream agreement", status, evidence, "James-facing next move should match the buildstream.")


def check_closeout_tool(repo: Path) -> Check:
    path = repo / "tools" / "closeout" / "run.py"
    if not path.exists():
        return Check("closeout tool", FAIL, "missing tools/closeout/run.py", "Surfaces need an end-of-cycle reconciler.")
    text = read(path)
    expected = ("tools/index/refresh.py", "tools/selfmodel/refresh.py", "tools/reflect/log.py", "tools/decisions/daily_sync.py")
    missing = [item for item in expected if item not in text]
    if missing:
        return Check("closeout tool", WARN, f"missing steps: {', '.join(missing)}", "Closeout should refresh all core surfaces.")
    return Check("closeout tool", PASS, "configured for index, self-model, reflections, HOME/NEXT", "Observer does not run it because it writes surfaces.")


def check_cost_guard() -> Check:
    guard = HOME / ".local" / "bin" / "cost-guard"
    caps = [
        HOME / ".config" / "fpai" / "cost" / "ambient_metered_usd",
        HOME / ".config" / "fpai" / "cost" / "ambient_run_cap",
    ]
    if not guard.exists():
        return Check("cost guard", WARN, f"missing {guard}", "Autonomy should not run without the Resource Discipline Gate.")
    cap_bits = []
    for cap in caps:
        if cap.exists():
            cap_bits.append(f"{cap.name}={read(cap).strip()}")
    evidence = "cost-guard present" + (f"; {'; '.join(cap_bits)}" if cap_bits else "; cap files not visible")
    status = PASS if cap_bits else WARN
    return Check("cost guard", status, evidence, "Autonomous work must stay inside the metered spend gate.")


def check_safety_seal(repo: Path) -> Check:
    autoloop = repo / "tools" / "autoloop" / "tick.sh"
    if not autoloop.exists():
        return Check("Safety Seal", WARN, "missing tools/autoloop/tick.sh", "Cannot verify unattended-loop shutdown and logging.")
    text = read(autoloop)
    required = {
        "cost guard": "cost-guard" in text,
        "ambient pause switch": ".pause-ambient" in text,
        "autoloop disable switch": ".disabled" in text,
        "run log": "runs.log" in text,
        "closeout step": "tools/closeout/run.py" in text,
        "router step": "tools/router/route.py" in text,
        "reserved-action ban": "MAY NOT" in text and "move money" in text and "deploy" in text and "secrets" in text,
    }
    missing = [name for name, ok in required.items() if not ok]
    router_lines = [line.strip() for line in text.splitlines() if "tools/router/route.py" in line]
    router_report_only = bool(router_lines) and not any("--apply" in line for line in router_lines)
    if not router_report_only:
        missing.append("report-only router tick")
    if missing:
        return Check("Safety Seal", WARN, f"missing: {', '.join(missing)}", "No uncontrolled exposure: loops need cap, log, kill switch, rollback posture.")
    return Check(
        "Safety Seal",
        PASS,
        "autoloop has cost guard, pause/disable switches, run log, closeout, report-only router",
        "No uncontrolled exposure before expanded autonomy.",
    )


def check_phone_cloud_docs(repo: Path) -> Check:
    required = [
        "AGENTS.md",
        "docs/codex/README.md",
        "docs/codex/PHONE_HANDOFF.md",
        "docs/codex/AI_PROTOCOLS.md",
        "docs/codex/INTENT_BUILDSTREAM.md",
        "docs/codex/HANDOFF.md",
        "docs/codex/specs/SPEC_auto-routing.md",
        "tools/router/README.md",
    ]
    missing = [item for item in required if not (repo / item).exists()]
    if missing:
        return Check("phone/cloud continuity", WARN, f"missing: {', '.join(missing)}", "Phone Codex needs repo-visible context.")
    return Check("phone/cloud continuity", PASS, f"{len(required)} repo-visible docs/tools present", "Phone/cloud can continue from GitHub once pushed.")


def check_git_state(repo: Path) -> Check:
    proc = subprocess.run(["git", "status", "--short", "--branch"], cwd=repo, text=True, capture_output=True, check=False)
    out = proc.stdout.strip()
    dirty = [ln for ln in out.splitlines() if ln and not ln.startswith("## ")]
    branch = next((ln for ln in out.splitlines() if ln.startswith("## ")), "unknown branch")
    if dirty:
        return Check("git isolation", WARN, f"{branch}; dirty paths={len(dirty)}", "One-day test should know what is committed vs local-only.")
    return Check("git isolation", PASS, branch, "Repo state is clean.")


def _clip(text: str, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def run_checks(repo: Path, vault: Path) -> list[Check]:
    return [
        check_router_dry_run(repo),
        check_router_gate(),
        check_closeout_tool(repo),
        check_proof(vault),
        check_home_buildstream(repo, vault),
        check_cost_guard(),
        check_safety_seal(repo),
        check_phone_cloud_docs(repo),
        check_git_state(repo),
    ]


def as_dict(check: Check) -> dict[str, str]:
    return dataclasses.asdict(check)


def print_human(checks: list[Check]) -> None:
    order = {PASS: 0, WARN: 1, FAIL: 2}
    worst = max(checks, key=lambda c: order.get(c.status, 0)).status if checks else PASS
    print(f"Self-standing observer: {worst}")
    print("---")
    for c in checks:
        print(f"[{c.status}] {c.name}: {c.evidence}")
        print(f"  why: {c.why}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only observer for the self-standing one-day test.")
    ap.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    ap.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)

    checks = run_checks(args.repo, args.vault)
    if args.json:
        print(json.dumps([as_dict(c) for c in checks], indent=2))
    else:
        print_human(checks)
    return 1 if any(c.status == FAIL for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
