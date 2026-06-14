#!/usr/bin/env python3
"""Work-claim a surface so no other AI collides while it's being edited.

Before editing a major surface: claim it (sets 🔴 + owner in the Index of Indexes
spine). After: clear it (back to 🟢). Each call re-runs the index refresh so the
status shows immediately — the index reflects who's working on what, live.

Usage:
    python3 tools/index/claim.py --page "AI PROTOCOLS" --owner Ember
    python3 tools/index/claim.py --clear --page "AI PROTOCOLS"
    python3 tools/index/claim.py --list
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CLAIMS = Path(os.environ.get("FPAI_INDEX_CLAIMS", HOME / ".config" / "fpai" / "index" / "claims.json"))
REFRESH = Path(__file__).resolve().parent / "refresh.py"


def load() -> dict:
    try:
        return json.loads(CLAIMS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(d: dict) -> None:
    CLAIMS.parent.mkdir(parents=True, exist_ok=True)
    CLAIMS.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Claim/clear a surface in the Index of Indexes.")
    ap.add_argument("--page", help="page stem, e.g. \"AI PROTOCOLS\"")
    ap.add_argument("--owner", default="AI", help="who is working it (Ember/Codex/James/…)")
    ap.add_argument("--clear", action="store_true", help="release the claim")
    ap.add_argument("--list", action="store_true", help="show active claims")
    ap.add_argument("--no-refresh", action="store_true", help="skip re-running the index refresh")
    args = ap.parse_args(argv)

    claims = load()

    if args.list:
        if not claims:
            print("no active claims")
        for page, meta in claims.items():
            print(f"🔴 {page} · {meta.get('owner')} · since {meta.get('started')}")
        return 0

    if not args.page:
        ap.error("--page is required (unless --list)")

    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    if args.clear:
        if claims.pop(args.page, None) is not None:
            save(claims)
            print(f"🟢 cleared: {args.page}")
        else:
            print(f"(no active claim on {args.page})")
    else:
        if args.page in claims and claims[args.page].get("owner") != args.owner:
            print(f"⚠️ already claimed by {claims[args.page].get('owner')} since {claims[args.page].get('started')} — coordinate, don't collide.")
            return 2
        claims[args.page] = {"owner": args.owner, "started": now}
        save(claims)
        print(f"🔴 claimed: {args.page} · {args.owner}")

    if not args.no_refresh and REFRESH.exists():
        subprocess.run([sys.executable, str(REFRESH)], capture_output=True, text=True)
        print("index refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
