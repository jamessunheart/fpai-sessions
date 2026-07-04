#!/usr/bin/env python3
"""Guard live-service activation with backup, smoke test, and rollback.

The server build loop calls this instead of running activation scripts directly.
Repo-only builds never reach this file. Activation scripts are the live-service
boundary: if a build ships one, the guard snapshots mapped live files, runs the
script, verifies the running service, and restores the snapshot on failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


ERROR_RE = re.compile(r"Traceback|No module(?: named)?|No such file", re.IGNORECASE)
DEFAULT_BACKUP_ROOT = Path(os.environ.get("LIVE_DEPLOY_BACKUP_ROOT", "/opt/fpai-build/deploy-backups"))


@dataclass(frozen=True)
class LiveTarget:
    name: str
    patterns: tuple[str, ...]
    services: tuple[str, ...]
    backup_paths: tuple[str, ...] = ()
    kind: str = "generic"
    healthcheck: tuple[str, ...] = ()
    root_env: str = ""


TARGETS: tuple[LiveTarget, ...] = (
    LiveTarget(
        name="sunheart-brain-tgbot",
        patterns=(
            "SERVICES/sunheart-brain/",
            "core/BUILD/activate/SPEC_d163_",
            "core/BUILD/activate/SPEC_d174_",
            "core/BUILD/activate/SPEC_d177_",
        ),
        services=("sh-brain-tgbot.service",),
        backup_paths=(
            "curator/tgbot.py",
            "curator/llm.py",
            "curator/build_context.py",
            "curator/voice_pipeline.py",
        ),
        kind="bot",
        root_env="SH_BRAIN_SRC",
    ),
    LiveTarget(
        name="fullpotential-intake",
        patterns=("SERVICES/champion-sign/", "sites/fullpotential-com/"),
        services=("champion-sign.service",),
        kind="generic",
        root_env="FPAI_ROOT",
    ),
    LiveTarget(
        name="fp-guide",
        patterns=("deploy-tools/intake-agent.py", "SERVICES/champion-bot/", "SERVICES/fp-guide/"),
        services=("fp-guide.service",),
        kind="generic",
        root_env="FPAI_ROOT",
    ),
)


@dataclass
class GuardResult:
    ok: bool
    reason: str
    backup_dir: Path | None = None
    targets: list[str] = field(default_factory=list)


Runner = Callable[..., subprocess.CompletedProcess[str]]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_cmd(
    args: list[str],
    *,
    runner: Runner = subprocess.run,
    timeout: int = 30,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return runner(args, cwd=str(cwd) if cwd else None, env=env, text=True, capture_output=True, timeout=timeout)


def changed_files(repo: Path, base_ref: str, head_ref: str, *, runner: Runner = subprocess.run) -> list[str]:
    if not base_ref or not head_ref:
        return []
    result = run_cmd(
        ["git", "-C", str(repo), "diff", "--name-only", f"{base_ref}..{head_ref}"],
        runner=runner,
        timeout=15,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def detect_targets(files: Iterable[str], activate_script: Path | None = None) -> list[LiveTarget]:
    haystack = list(files)
    if activate_script is not None:
        haystack.append(str(activate_script))
        try:
            haystack.append(activate_script.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass

    found: list[LiveTarget] = []
    for target in TARGETS:
        if any(pattern in item for pattern in target.patterns for item in haystack):
            found.append(target)

    if not found and activate_script is not None:
        services = tuple(sorted(set(re.findall(r"systemctl\s+(?:restart|start|enable\s+--now)\s+([A-Za-z0-9_.@-]+)", "\n".join(haystack)))))
        if services:
            found.append(LiveTarget("generic-activation", patterns=(), services=services))
    return found


def live_root_for(target: LiveTarget) -> Path | None:
    if target.name == "sunheart-brain-tgbot":
        return Path(os.environ.get(target.root_env, "/opt/sh-brain-src"))
    if target.root_env:
        return Path(os.environ.get(target.root_env, "/opt/fpai"))
    return None


def create_backup(targets: Iterable[LiveTarget], backup_root: Path, spec_id: str) -> Path:
    backup_dir = backup_root / f"{spec_id}-{utc_stamp()}"
    manifest: list[dict[str, str]] = []
    for target in targets:
        root = live_root_for(target)
        if root is None:
            continue
        for rel in target.backup_paths:
            src = root / rel
            if not src.exists() or not src.is_file():
                continue
            dst = backup_dir / target.name / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            manifest.append({"target": target.name, "root": str(root), "rel": rel, "backup": str(dst)})
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return backup_dir


def restore_backup(backup_dir: Path, targets: Iterable[LiveTarget], *, runner: Runner = subprocess.run) -> None:
    manifest_path = backup_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = []
    for row in manifest:
        src = Path(row["backup"])
        dst = Path(row["root"]) / row["rel"]
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    for service in sorted({svc for target in targets for svc in target.services}):
        run_cmd(["systemctl", "restart", service], runner=runner, timeout=20)


def smoke_generic(target: LiveTarget, *, runner: Runner = subprocess.run) -> tuple[bool, str]:
    for service in target.services:
        active = run_cmd(["systemctl", "is-active", "--quiet", service], runner=runner, timeout=8)
        if active.returncode != 0:
            return False, f"{service} is not active"
        logs = run_cmd(["journalctl", "-u", service, "--since", "60 seconds ago", "--no-pager"], runner=runner, timeout=10)
        log_text = (logs.stdout or "") + "\n" + (logs.stderr or "")
        match = ERROR_RE.search(log_text)
        if match:
            return False, f"{service} fresh logs contain {match.group(0)}"
    if target.healthcheck:
        check = run_cmd(list(target.healthcheck), runner=runner, timeout=15)
        if check.returncode != 0:
            detail = (check.stderr or check.stdout or "").strip()[:240]
            return False, f"{target.name} healthcheck failed: {detail}"
    return True, f"{target.name} smoke passed"


def smoke_bot(target: LiveTarget, repo_root: Path, *, runner: Runner = subprocess.run) -> tuple[bool, str]:
    ok, reason = smoke_generic(target, runner=runner)
    if not ok:
        return ok, reason

    live = live_root_for(target) or Path("/opt/sh-brain-src")
    py = live / ".venv" / "bin" / "python"
    if not py.exists():
        py = Path("/usr/bin/python3")

    voice_code = (
        "from curator import voice_pipeline; "
        "s=voice_pipeline.dependency_status(); "
        "import os; "
        "assert s.faster_whisper or os.environ.get('OPENAI_API_KEY'), 'no STT provider importable'; "
        "print('voice-stt-ok')"
    )
    voice = run_cmd([str(py), "-c", voice_code], runner=runner, timeout=10, cwd=live)
    if voice.returncode != 0:
        detail = (voice.stderr or voice.stdout or "").strip()[:240]
        return False, f"voice STT module not importable: {detail}"

    model_code = """
import asyncio
from curator import tgbot
async def main():
    tgbot._context_blocks_for_route = lambda _route: {
        "system_state": False,
        "buildstream": False,
        "corrections": False,
        "becoming": False,
        "brain_search": False,
    }
    async def no_history(_conversation_id):
        return ""
    tgbot._recent_chat_history_context = no_history
    answer = await tgbot._synthesize_answer("live deploy smoke ping", [], conversation_id="live-smoke")
    print(answer)
    assert "Brain synthesis hit an error" not in answer, answer
    assert "Model:" in answer, answer
    assert "llama-fallback" not in answer, answer
asyncio.run(main())
""".strip()
    env = os.environ.copy()
    env["FPAI_REPO_ROOT"] = str(repo_root)
    model = run_cmd([str(py), "-c", model_code], runner=runner, timeout=25, cwd=live, env=env)
    if model.returncode != 0:
        detail = (model.stderr or model.stdout or "").strip()[:300]
        return False, f"bot reply smoke failed or used ollama fallback: {detail}"
    return True, "bot reply path used Claude and voice STT is importable"


def run_smoke(targets: Iterable[LiveTarget], repo_root: Path, *, runner: Runner = subprocess.run) -> tuple[bool, str]:
    details: list[str] = []
    for target in targets:
        if target.kind == "bot":
            ok, detail = smoke_bot(target, repo_root, runner=runner)
        else:
            ok, detail = smoke_generic(target, runner=runner)
        details.append(detail)
        if not ok:
            return False, detail
    return True, "; ".join(details) or "no live targets"


def append_ops(ops_ledger: Path, event: str, detail: str, spec_id: str, branch: str) -> None:
    ops_ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "live_service_guard",
        "event": event,
        "detail": detail,
        "cost": "$0",
        "artifact": "tools/build_loop/live_service_guard.py",
        "next": "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "spec_id": spec_id,
        "branch": branch,
    }
    with ops_ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def send_alert(message: str, repo_root: Path, *, runner: Runner = subprocess.run) -> None:
    notify = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    if notify.exists():
        run_cmd(["bash", str(notify), message], runner=runner, timeout=20)


def activate_with_guard(args: argparse.Namespace, *, runner: Runner = subprocess.run) -> GuardResult:
    repo = Path(args.repo_root)
    script = Path(args.activate_script)
    files = changed_files(repo, args.base_ref, args.head_ref, runner=runner)
    targets = detect_targets(files, script)
    if not targets:
        targets = [LiveTarget("generic-activation", patterns=(), services=())]
    backup_dir = create_backup(targets, Path(args.backup_root), args.spec_id)
    append_ops(Path(args.ops_ledger), "backup", f"{args.spec_id} backup={backup_dir}", args.spec_id, args.branch)

    activated = run_cmd(["bash", str(script)], runner=runner, timeout=int(args.activate_timeout), cwd=repo)
    if activated.returncode != 0:
        reason = (activated.stderr or activated.stdout or "activation failed").strip()[:300]
        restore_backup(backup_dir, targets, runner=runner)
        alert = f"{args.decision_id} deploy failed smoke-test, auto-reverted: activation failed: {reason}"
        send_alert(alert, repo, runner=runner)
        append_ops(Path(args.ops_ledger), "auto-reverted", alert, args.spec_id, args.branch)
        return GuardResult(False, alert, backup_dir, [target.name for target in targets])

    ok, reason = run_smoke(targets, repo, runner=runner)
    if ok:
        append_ops(Path(args.ops_ledger), "smoke-pass", f"{args.spec_id}: {reason}", args.spec_id, args.branch)
        return GuardResult(True, reason, backup_dir, [target.name for target in targets])

    restore_backup(backup_dir, targets, runner=runner)
    alert = f"{args.decision_id} deploy failed smoke-test, auto-reverted: {reason}"
    send_alert(alert, repo, runner=runner)
    append_ops(Path(args.ops_ledger), "auto-reverted", alert, args.spec_id, args.branch)
    return GuardResult(False, alert, backup_dir, [target.name for target in targets])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default="/opt/fpai-build/FPAI_Cockpit")
    parser.add_argument("--spec-id", required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--activate-script", required=True)
    parser.add_argument("--base-ref", default="")
    parser.add_argument("--head-ref", default="")
    parser.add_argument("--backup-root", default=str(DEFAULT_BACKUP_ROOT))
    parser.add_argument("--ops-ledger", default=os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
    parser.add_argument("--activate-timeout", default=os.environ.get("LIVE_DEPLOY_ACTIVATE_TIMEOUT", "120"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = activate_with_guard(args)
    print(json.dumps({"ok": result.ok, "reason": result.reason, "targets": result.targets, "backup_dir": str(result.backup_dir or "")}))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
