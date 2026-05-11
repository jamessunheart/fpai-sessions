#!/usr/bin/env python3
"""Preflight validation before deployment."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CHECKS = {
    "missing_env": [],
    "missing_secrets": [],
    "failed_imports": [],
    "missing_manifests": [],
    "outdated_paths": [],
}

REQUIRED_ENVS = [
    "env/global.env",
    "env/treasury.env",
]

MANIFEST_TARGETS = [
    ("agents/services", ["requirements.txt", "Dockerfile", "package.json"]),
    ("core/applications", ["requirements.txt", "Dockerfile", "package.json"]),
]

PATH_STRINGS = ["SERVICES/", "fullpotential_claude1", "fullpotential_hteam1"]
SKIP_PATHS = {Path(__file__).resolve()}


def check_env_files() -> None:
    for rel in REQUIRED_ENVS:
        if not (ROOT / rel).exists():
            CHECKS["missing_env"].append(rel)


def check_secrets_placeholder() -> None:
    secrets_file = ROOT / "env" / "secrets.json"
    if secrets_file.exists():
        data = json.loads(secrets_file.read_text())
        missing = [k for k, v in data.items() if not v or "PLACEHOLDER" in v.upper()]
        CHECKS["missing_secrets"].extend(missing)
    else:
        CHECKS["missing_secrets"].append("env/secrets.json (missing)")


def check_imports() -> None:
    modules = ["orchestration.tools.spec_task_sync", "orchestration.scripts.generate_intent_snapshot"]
    for mod in modules:
        try:
            importlib.import_module(mod)
        except Exception as exc:
            CHECKS["failed_imports"].append(f"{mod}: {exc}")


def check_manifests() -> None:
    for base, manifests in MANIFEST_TARGETS:
        base_path = ROOT / base
        for service in base_path.glob("*"):
            if not service.is_dir():
                continue
            present = {m for m in manifests if (service / m).exists()}
            if not present:
                CHECKS["missing_manifests"].append(f"{service.relative_to(ROOT)} lacks manifests {manifests}")


def check_paths() -> None:
    for path in ROOT.rglob("*.*"):
        if any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
            continue
        if path.resolve() in SKIP_PATHS:
            continue
        try:
            text = path.read_text()
        except Exception:
            continue
        for needle in PATH_STRINGS:
            if needle in text:
                CHECKS["outdated_paths"].append(f"{needle} -> {path.relative_to(ROOT)}")


def main() -> None:
    check_env_files()
    check_secrets_placeholder()
    check_imports()
    check_manifests()
    check_paths()

    report = json.dumps(CHECKS, indent=2)
    print(report)
    (ROOT / "infra" / "preflight_report.json").write_text(report)

    has_issues = any(CHECKS[key] for key in ("missing_env", "missing_secrets", "failed_imports", "outdated_paths"))
    if has_issues:
        exit(1)


if __name__ == "__main__":
    main()
