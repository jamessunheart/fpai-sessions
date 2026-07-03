#!/usr/bin/env python3
"""Brain versioning — orderly, revertible progression.

The revert substrate James asked for: a semantic BRAIN_VERSION plus a git tag on
every bump, so `git checkout brain-v<X.Y.Z>` returns the brain to any point.

  MAJOR  architecture change (new subsystem, breaking reorg)
  MINOR  new capability (a spec batch that adds function)
  PATCH  bug fix (a BUG_LOG batch)

Usage:
  brain_version.py                      # print current version
  brain_version.py bump patch|minor|major [--tag] [--note "..."]
  brain_version.py current

--tag creates an annotated git tag brain-v<X.Y.Z> (revert anchor). Never bumps
without an explicit subcommand; reversible (tags are deletable, file is git-tracked).
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VERSION_FILE = REPO / "core" / "STATE" / "BRAIN_VERSION"


def read_version() -> tuple[int, int, int]:
    try:
        raw = VERSION_FILE.read_text().strip()
        major, minor, patch = (int(x) for x in raw.split("."))
        return major, minor, patch
    except (OSError, ValueError):
        return (1, 0, 0)


def write_version(v: tuple[int, int, int]) -> None:
    VERSION_FILE.write_text(f"{v[0]}.{v[1]}.{v[2]}\n")


def bump(kind: str, v: tuple[int, int, int]) -> tuple[int, int, int]:
    major, minor, patch = v
    if kind == "major":
        return (major + 1, 0, 0)
    if kind == "minor":
        return (major, minor + 1, 0)
    if kind == "patch":
        return (major, minor, patch + 1)
    raise ValueError(f"unknown bump kind: {kind}")


def git_tag(version_str: str, note: str) -> bool:
    tag = f"brain-v{version_str}"
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO), "tag", "-a", tag, "-m", note or f"brain {tag}"],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode == 0
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("bump")
    b.add_argument("kind", choices=["patch", "minor", "major"])
    b.add_argument("--tag", action="store_true", help="Create annotated git tag brain-v<X.Y.Z>")
    b.add_argument("--note", default="", help="Tag/changelog note")
    sub.add_parser("current")
    args = ap.parse_args(argv)

    cur = read_version()
    if args.cmd == "bump":
        nv = bump(args.kind, cur)
        write_version(nv)
        vs = f"{nv[0]}.{nv[1]}.{nv[2]}"
        print(f"{cur[0]}.{cur[1]}.{cur[2]} -> {vs}")
        if args.tag:
            print(f"tag brain-v{vs}: {'created' if git_tag(vs, args.note) else 'FAILED (commit the version bump first)'}")
        return 0
    # default / current
    print(f"{cur[0]}.{cur[1]}.{cur[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
