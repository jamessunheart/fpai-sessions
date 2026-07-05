#!/usr/bin/env python3
"""Enforce activate-or-declare-inert policy for generated build specs."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_KIND_RE = re.compile(r"\bbuild_kind\s*[:=]\s*(library|inert)\b", re.I)


@dataclass(frozen=True)
class PolicyResult:
    ok: bool
    reason: str
    build_kind: str = ""
    activation_script: str = ""


def check_policy(
    repo_root: Path,
    *,
    spec_id: str,
    base_ref: str = "feat/headless-build",
    head_ref: str = "HEAD",
) -> PolicyResult:
    activation = repo_root / "core" / "BUILD" / "activate" / f"{spec_id}.sh"
    if activation.exists():
        return PolicyResult(True, "activation script present", activation_script=str(activation.relative_to(repo_root)))

    kind = declared_build_kind(repo_root, spec_id)
    if kind in {"library", "inert"}:
        return PolicyResult(True, f"build_kind={kind} declared", build_kind=kind)

    changed = changed_files(repo_root, base_ref=base_ref, head_ref=head_ref)
    if not changed:
        return PolicyResult(True, "no changed files detected")

    return PolicyResult(
        False,
        (
            "missing activation policy: ship "
            f"core/BUILD/activate/{spec_id}.sh or declare build_kind=library/inert "
            f"in core/BUILD/specs/{spec_id}.md or core/BUILD/results/{spec_id}.result.md"
        ),
    )


def declared_build_kind(repo_root: Path, spec_id: str) -> str:
    for path in (
        repo_root / "core" / "BUILD" / "specs" / f"{spec_id}.md",
        repo_root / "core" / "BUILD" / "results" / f"{spec_id}.result.md",
    ):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = BUILD_KIND_RE.search(text)
        if match:
            return match.group(1).lower()
    return ""


def changed_files(repo_root: Path, *, base_ref: str, head_ref: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--name-only", f"{base_ref}..{head_ref}"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--spec-id", required=True)
    parser.add_argument("--base-ref", default=os.environ.get("BASE", "feat/headless-build"))
    parser.add_argument("--head-ref", default="HEAD")
    args = parser.parse_args(argv)
    result = check_policy(args.repo_root, spec_id=args.spec_id, base_ref=args.base_ref, head_ref=args.head_ref)
    print(("OK: " if result.ok else "FAIL: ") + result.reason)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
