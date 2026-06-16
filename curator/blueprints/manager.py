"""Living module blueprint manager.

Blueprints are repo-local contracts under docs/blueprints. Runtime hooks call
this module best-effort; failures must not block chat, council, or build-loop
work.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT_DIR = REPO_ROOT / "docs" / "blueprints"
REGISTRY_PATH = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"
SPEC_DIR = REPO_ROOT / "core" / "BUILD" / "specs"

BLUEPRINT_MODULES = (
    "forge",
    "council",
    "ember",
    "spark",
    "ledger",
    "hermes",
    "cora",
    "steward",
    "beacon",
    "learning_loop",
    "health",
)

MODULE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "forge": ("forge", "build loop", "build_loop", "server_build_loop", "run_codex", "merge_gate", "autobuild"),
    "council": ("council", "debate", "proposal pipeline", "self-diagnostic"),
    "ember": ("ember", "memory", "context steward", "tgbot", "build_context", "thread", "continuity"),
    "spark": ("spark", "routing", "onboarding", "triage", "first-touch", "intake"),
    "ledger": ("ledger", "ops_ledger", "ops_log", "cost", "track.py", "corrections"),
    "hermes": ("hermes", "channel gateway", "telegram", "sms", "whatsapp", "email", "comms"),
    "cora": ("cora", "reward", "monetary policy", "earn", "burn", "credit"),
    "steward": ("steward", "per-user", "agent passport", "user_agents", "agent namespace"),
    "beacon": ("beacon", "growth", "content bank", "campaign", "attribution"),
    "learning_loop": ("learning", "preference", "correction", "feedback", "d010", "d022", "d023"),
    "health": ("health", "smoke", "selftest", "health_check", "status"),
}

PATH_HINTS: tuple[tuple[str, str], ...] = (
    ("tools/build_loop/", "forge"),
    ("tools/autobuild/", "forge"),
    ("tools/merge/", "forge"),
    ("tools/council/", "council"),
    ("tools/decisions/", "council"),
    ("SERVICES/sunheart-brain/curator/build_context.py", "ember"),
    ("SERVICES/sunheart-brain/curator/tgbot.py", "ember"),
    ("SERVICES/sunheart-brain/curator/triage.py", "spark"),
    ("tools/beacon/", "beacon"),
    ("docs/content_bank/", "beacon"),
    ("tools/learn/", "learning_loop"),
    ("SERVICES/sunheart-brain/curator/corrections.py", "learning_loop"),
    ("docs/policy/CORA", "cora"),
    ("tools/comms/", "hermes"),
    ("tools/selftest/", "health"),
    ("tools/build_loop/health_check.sh", "health"),
    ("tools/build_loop/ops_log.py", "ledger"),
)


def disabled() -> bool:
    return os.environ.get("BLUEPRINTS_DISABLE") == "1"


def today() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def normalize_module(module_name: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", (module_name or "").strip().lower()).strip("_")


def blueprint_path(module_name: str, *, repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / "docs" / "blueprints" / f"{normalize_module(module_name)}.md"


def get_blueprint(module_name: str) -> str:
    """Return the full blueprint text, or empty string if absent."""
    if not module_name:
        return ""
    path = blueprint_path(module_name)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def detect_module_from_paths(paths: Iterable[str]) -> str:
    joined = "\n".join(paths)
    for hint, module in PATH_HINTS:
        if hint in joined:
            return module
    return detect_module_from_text(joined)


def detect_module_from_text(text: str) -> str:
    haystack = (text or "").lower()
    if not haystack:
        return ""
    scores: dict[str, int] = {}
    for module, keywords in MODULE_KEYWORDS.items():
        scores[module] = sum(1 for keyword in keywords if keyword.lower() in haystack)
    best, score = max(scores.items(), key=lambda item: item[1])
    return best if score > 0 else ""


def build_blueprint_context(*parts: str, include_council: bool = False) -> str:
    """Return relevant blueprint context for a prompt/spec."""
    modules: list[str] = []
    if include_council:
        modules.append("council")
    module = detect_module_from_text("\n".join(part for part in parts if part))
    if module and module not in modules:
        modules.append(module)
    blocks = [get_blueprint(module).strip() for module in modules]
    return "\n\n".join(block for block in blocks if block)


def _read_registry() -> dict:
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _find_registry_entry(decision_id: str, branch: str) -> dict:
    registry = _read_registry()
    for item in registry.get("active_builds", []):
        if item.get("id") == decision_id or item.get("slug") == decision_id or item.get("branch") == branch:
            return item
    return {}


def _spec_text(decision_id: str, entry: dict | None = None) -> str:
    candidates: list[Path] = []
    if entry and entry.get("spec"):
        candidates.append(Path(str(entry["spec"])))
    candidates.append(SPEC_DIR / f"{decision_id}.md")
    for candidate in candidates:
        path = candidate if candidate.is_absolute() else REPO_ROOT / candidate
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            continue
    return ""


def _changed_paths(branch: str) -> list[str]:
    if not branch:
        return []
    result = subprocess.run(
        ["git", "diff", "--name-only", "feat/headless-build..." + branch],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    result = subprocess.run(
        ["git", "show", "--name-only", "--format=", branch],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _diff_summary(branch: str) -> str:
    if not branch:
        return ""
    result = subprocess.run(
        ["git", "diff", "--stat", "feat/headless-build..." + branch],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.stdout.strip():
        return result.stdout.strip()
    result = subprocess.run(
        ["git", "show", "--stat", "--format=%s", branch],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.stdout.strip()


def _run_claude(prompt: str, timeout: int = 180) -> str:
    claude = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    result = subprocess.run(
        [claude, "-p", "--effort", "high", prompt],
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "claude failed").strip())
    return result.stdout.strip()


def _replace_section(content: str, section: str, replacement_body: str) -> str:
    heading = f"## {section}"
    pattern = re.compile(rf"(^## {re.escape(section)}\s*\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(content)
    body = replacement_body.strip() + "\n\n"
    if match:
        return content[: match.start(2)] + body + content[match.end(2) :]
    suffix = "" if content.endswith("\n") else "\n"
    return content + suffix + f"\n{heading}\n{body}"


def _append_known_gap(content: str, correction: str, *, date: str) -> str:
    line = f"- {date}: {correction.strip()}"
    pattern = re.compile(r"(^## Known gaps\s*\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(content)
    if not match:
        return content.rstrip() + f"\n\n## Known gaps\n\n{line}\n"
    body = match.group(2).rstrip()
    updated_body = (body + "\n" + line + "\n\n").lstrip()
    return content[: match.start(2)] + updated_body + content[match.end(2) :]


def update_blueprint_after_build(
    decision_id: str,
    branch: str,
    *,
    claude_runner: Callable[[str], str] = _run_claude,
    commit: bool = True,
) -> None:
    """Regenerate the affected module blueprint after a merged build."""
    if disabled():
        return
    entry = _find_registry_entry(decision_id, branch)
    spec = _spec_text(decision_id, entry)
    paths = _changed_paths(branch)
    module = (
        normalize_module(str(entry.get("module", "")))
        or detect_module_from_paths(paths)
        or detect_module_from_text(" ".join([decision_id, branch, spec, str(entry.get("notes", ""))]))
    )
    if not module:
        return
    current = get_blueprint(module)
    if not current:
        seed_blueprint(module)
        current = get_blueprint(module)
    if not current:
        return
    prompt = (
        "Update this module blueprint to reflect what this build added or changed. "
        "Update sections: Current behavior, Known gaps, Improvement history. "
        "Do NOT change: What it does, Quality standard (unless explicitly improved). "
        "Be specific and dated. Output the FULL updated blueprint.\n\n"
        f"Blueprint:\n{current}\n\n"
        f"Build diff summary:\n{_diff_summary(branch)}\n\n"
        f"Build spec:\n{spec}"
    )
    updated = claude_runner(prompt).strip()
    if not updated.startswith("#"):
        return
    if "## Quality standard" not in updated:
        updated = _replace_section(updated, "Quality standard", _extract_section(current, "Quality standard"))
    path = blueprint_path(module)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    if commit and os.environ.get("BLUEPRINTS_NO_COMMIT") != "1":
        subprocess.run(["git", "add", str(path.relative_to(REPO_ROOT))], cwd=REPO_ROOT, check=False)
        subprocess.run(
            ["git", "commit", "-m", f"docs(blueprint): update {module} after {decision_id}"],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _extract_section(content: str, section: str) -> str:
    pattern = re.compile(rf"^## {re.escape(section)}\s*\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(content or "")
    return (match.group(1).strip() if match else "").strip()


def update_blueprint_after_correction(module_name: str, correction: str) -> None:
    """Append a real correction to Known gaps without regenerating the document."""
    if disabled() or not correction.strip():
        return
    module = normalize_module(module_name) or detect_module_from_text(correction)
    if not module:
        module = "ember"
    current = get_blueprint(module)
    if not current:
        seed_blueprint(module)
        current = get_blueprint(module)
    path = blueprint_path(module)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_append_known_gap(current, correction, date=today()).rstrip() + "\n", encoding="utf-8")


def sharpen_quality_standard(
    module_name: str,
    *,
    claude_runner: Callable[[str], str] = _run_claude,
    send_func: Callable[[str], None] | None = None,
) -> str:
    """Propose a measurable quality-standard upgrade. Does not auto-adopt."""
    if disabled():
        return ""
    module = normalize_module(module_name)
    blueprint = get_blueprint(module)
    if not blueprint:
        return ""
    prompt = (
        "Given current behavior and recent improvements, propose a higher quality standard "
        "for this module. One paragraph. Must be measurable. Must be achievable in next 3 builds.\n\n"
        f"Module: {module}\n\nBlueprint:\n{blueprint}"
    )
    proposal = claude_runner(prompt).strip()
    message = f"Quality standard proposed for {module}. Reply yes to adopt.\n\n{proposal}"
    if send_func:
        send_func(message)
    else:
        _send_telegram_best_effort(message)
    return proposal


def _send_telegram_best_effort(message: str) -> None:
    script = REPO_ROOT / "tools" / "build_loop" / "notify_telegram.sh"
    if script.exists():
        subprocess.run([str(script), message], cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def seed_blueprint(module_name: str) -> None:
    module = normalize_module(module_name)
    if module not in BLUEPRINT_MODULES:
        return
    path = blueprint_path(module)
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    title = module.replace("_", " ").title()
    path.write_text(_seed_text(module, title), encoding="utf-8")


def seed_all() -> None:
    for module in BLUEPRINT_MODULES:
        seed_blueprint(module)


def list_blueprints() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for module in BLUEPRINT_MODULES:
        content = get_blueprint(module)
        path = blueprint_path(module)
        rows.append(
            {
                "module": module,
                "last_updated": _last_updated(content, path),
                "quality_standard": _first_quality_line(content),
            }
        )
    return rows


def _last_updated(content: str, path: Path) -> str:
    match = re.search(r"Last updated:\*\*\s*([0-9-]+)|Last updated:\s*([0-9-]+)", content)
    if match:
        return next(group for group in match.groups() if group)
    try:
        return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


def _first_quality_line(content: str) -> str:
    body = _extract_section(content, "Quality standard")
    for line in body.splitlines():
        cleaned = line.strip(" -*")
        if cleaned:
            return cleaned[:140]
    return ""


def _seed_text(module: str, title: str) -> str:
    owner = {
        "hermes": "curator/hermes/ and channel adapters",
        "cora": "docs/policy/CORA_POLICY_v0.2.md",
        "steward": "curator/agent/ and user namespace tables",
        "beacon": "tools/beacon/ and docs/content_bank/",
        "learning_loop": "tools/learn/ and SERVICES/sunheart-brain/curator/corrections.py",
        "health": "tools/selftest/ and tools/build_loop/health_check.sh",
    }.get(module, "repo module owner")
    return f"""# {title} Blueprint
**Version:** 0.1 (seed)
**Last updated:** {today()}

## Identity

- **Function:** {title}
- **Owner:** `{owner}`
- **Status:** building
- **Decision:** d050 seed

## What it does

{title} holds the living contract for this module until live evidence sharpens it. It states the module boundary, current behavior, gaps, integrations, and quality standard future builds must improve against.

## How it works

- **Input:** Module-specific signals, specs, corrections, smoke tests, and ops ledger events.
- **Process:** The module runs through its owner files and records behavior into repo docs, ledgers, or brain_index tables.
- **Output:** Module-specific artifacts consumed by the rest of FPOS.
- **Side effects:** Future builds and reviews use this blueprint as context instead of reconstructing module state from old specs.

## Quality standard

Within the next 3 builds touching this module, every live behavior listed here should have at least one focused test or smoke proof, a clear kill switch where runtime side effects exist, and a dated current-behavior entry backed by repo or ops-ledger evidence.

## Current behavior (verified)

- {today()}: Seed blueprint created by d050. Live behavior still needs a post-merge refresh from build specs, diffs, and ops-ledger evidence.

## Known gaps

- {today()}: Initial seed is conservative and not yet independently regenerated from live ops evidence.

## Integration map

- **Depends on:** To be verified from live code paths.
- **Used by:** Council, Codex spec generation, review, corrections, and future builds.
- **DB tables:** To be verified.
- **Kill switch:** `BLUEPRINTS_DISABLE=1` disables blueprint automation.

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| {today()} | d050 | Seeded living blueprint | Future builds have a module contract to sharpen instead of a stale one-time spec |

## Test coverage

- `curator/blueprints/test_manager.py` covers blueprint retrieval, update, correction append, quality-standard preservation, and prompt context inclusion.
- NOT tested yet: live ops-ledger-backed regeneration for this module.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage living module blueprints.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    get_p = sub.add_parser("get")
    get_p.add_argument("module")
    update_p = sub.add_parser("update-after-build")
    update_p.add_argument("decision_id")
    update_p.add_argument("branch")
    update_p.add_argument("--no-commit", action="store_true")
    refresh_p = sub.add_parser("update")
    refresh_p.add_argument("module")
    refresh_p.add_argument("--no-commit", action="store_true")
    corr_p = sub.add_parser("correction")
    corr_p.add_argument("module")
    corr_p.add_argument("correction")
    sharpen_p = sub.add_parser("sharpen")
    sharpen_p.add_argument("module")
    seed_p = sub.add_parser("seed")
    seed_p.add_argument("module", nargs="?")
    sub.add_parser("list")
    detect_p = sub.add_parser("detect")
    detect_p.add_argument("parts", nargs="*")

    args = parser.parse_args(argv)
    if args.cmd == "get":
        print(get_blueprint(args.module), end="")
    elif args.cmd == "update-after-build":
        update_blueprint_after_build(args.decision_id, args.branch, commit=not args.no_commit)
    elif args.cmd == "update":
        update_blueprint_after_build(args.module, f"build/{args.module}", commit=not args.no_commit)
    elif args.cmd == "correction":
        update_blueprint_after_correction(args.module, args.correction)
    elif args.cmd == "sharpen":
        print(sharpen_quality_standard(args.module))
    elif args.cmd == "seed":
        seed_all() if not args.module else seed_blueprint(args.module)
    elif args.cmd == "list":
        for row in list_blueprints():
            print(f"{row['module']}\t{row['last_updated']}\t{row['quality_standard']}")
    elif args.cmd == "detect":
        print(detect_module_from_text(" ".join(args.parts)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
