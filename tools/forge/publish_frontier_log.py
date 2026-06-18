#!/usr/bin/env python3
"""Prepare or publish the sanitized public FRONTIER_LOG artifact."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from tools.forge.security_gate import assert_public

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRONTIER_LOG = REPO_ROOT / "core" / "STATE" / "FRONTIER_LOG.md"
DEFAULT_PUBLIC_OUT = REPO_ROOT / "core" / "STATE" / "FRONTIER_LOG.public.md"


def prepare_public_frontier_log(
    *,
    source: Path = DEFAULT_FRONTIER_LOG,
    output: Path = DEFAULT_PUBLIC_OUT,
    current: dt.datetime | None = None,
) -> dict[str, Any]:
    if not source.exists():
        raise FileNotFoundError(f"missing frontier log: {source}")
    now = current or dt.datetime.now(dt.timezone.utc)
    gate = assert_public(source.read_text(encoding="utf-8", errors="replace"))
    body = (
        "# FPOS Frontier Log\n\n"
        f"Public sanitized export generated {now.strftime('%Y-%m-%dT%H:%M:%SZ')}.\n\n"
        "This artifact contains only architecture patterns, benchmark signals, and public contribution opportunities.\n\n"
        + gate.sanitized
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    return {
        "source": str(source),
        "output": str(output),
        "warnings": list(gate.warnings),
        "blocked": gate.blocked,
        "bytes": len(body.encode("utf-8")),
    }


def publish_release(
    *,
    artifact: Path,
    tag: str,
    title: str,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    if os.environ.get("FRONTIER_PUBLISH_APPROVED") != "1":
        return {"published": False, "reason": "FRONTIER_PUBLISH_APPROVED not set"}
    cmd = [
        "gh",
        "release",
        "create",
        tag,
        str(artifact),
        "--title",
        title,
        "--notes-file",
        str(artifact),
    ]
    completed = runner(cmd, check=False, text=True, capture_output=True)
    return {
        "published": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "cmd": cmd,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare/publish sanitized FRONTIER_LOG.")
    parser.add_argument("--source", type=Path, default=DEFAULT_FRONTIER_LOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_OUT)
    parser.add_argument("--tag", default=f"frontier-log-{dt.datetime.now(dt.timezone.utc).date().isoformat()}")
    parser.add_argument("--title", default="FPOS Frontier Log")
    parser.add_argument("--execute", action="store_true", help="Call gh release create after security gate")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = prepare_public_frontier_log(source=args.source, output=args.output)
    if args.execute:
        result["release"] = publish_release(artifact=args.output, tag=args.tag, title=args.title)
    else:
        result["release"] = {"published": False, "reason": "dry-run; pass --execute and FRONTIER_PUBLISH_APPROVED=1"}
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"wrote {args.output}")
        print(result["release"]["reason"] if not result["release"].get("published") else "published")
    return 0 if not result.get("blocked") and result["release"].get("returncode", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

