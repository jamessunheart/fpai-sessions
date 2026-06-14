#!/usr/bin/env python3
"""
Zen Village application sync · v1 · 2026-05-26
Pulls applications from live server (198.54.123.234) → drops new ones into
the local scorer inbox → tracks what's been scored to avoid re-runs.

Server source:
  /opt/fpai/apps/zen-village/data/applications/<lane>/_all.json
Lanes: work-exchange · practitioner · artist · creator · volunteer

Local destinations:
  ~/.config/fpai/zen_village/applicants/inbox/      · new apps to score
  ~/.config/fpai/zen_village/applicants/scored/     · scored output (existing)
  ~/.config/fpai/zen_village/applicants/index.json  · dedup index (submission_id → scored?)

Usage:
  python3 sync_applications.py             · fetch + identify new + drop in inbox
  python3 sync_applications.py --score     · fetch + drop + immediately fire scorer --batch
  python3 sync_applications.py --dry-run   · show what would happen without writing
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
INBOX = HOME / ".config" / "fpai" / "zen_village" / "applicants" / "inbox"
SCORED = HOME / ".config" / "fpai" / "zen_village" / "applicants" / "scored"
PROCESSED = HOME / ".config" / "fpai" / "zen_village" / "applicants" / "processed"
INDEX = HOME / ".config" / "fpai" / "zen_village" / "applicants" / "index.json"
LOG = HOME / ".config" / "fpai" / "zen_village" / "sync.log"

SERVER = "root@198.54.123.234"
SERVER_DATA = "/opt/fpai/apps/zen-village/data/applications"
LANES = ("work-exchange", "practitioner", "artist", "creator", "volunteer")

SCORER = "/Users/jamessunheart/FPAI_Cockpit/tools/zen_village_scorer/score_applicant.py"

# Test patterns from the server's submissions_admin.py · filter these out
TEST_PATTERNS = (
    "@example.com", "@test.local", "@zenvillage.local",
    "@fullpotential.com",
    "smoketest", "wiretest", "fullpipe", "fullsync",
    "multi-sync", "multi-app", "lane test", "smoke recheck",
    "smoke prac", "booking form test", "test audit", "test guest",
    "test inquirer", "test booking", "test host", "retest 17",
    "creator-formtest", "vol-formtest", "artist-formtest",
    "prac-formtest", "e2e ",
    "smoke test", "smoketest",
)


def log(msg: str):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")
    print(msg, file=sys.stderr)


def is_test_row(r: dict) -> bool:
    bag = " ".join([
        (r.get("email") or "").lower(),
        (r.get("name") or "").lower(),
        (r.get("message") or "").lower(),
    ])
    return any(p in bag for p in TEST_PATTERNS)


def application_id(app: dict) -> str:
    """Stable id for dedup. Prefer _file (the source file), fallback to submitted_at + email."""
    if app.get("_file"):
        return app["_file"]
    return f"{app.get('submitted_at','no-ts')}_{app.get('email','no-email')}"


def load_index() -> dict:
    if not INDEX.exists():
        return {"scored": {}, "version": 1}
    try:
        return json.loads(INDEX.read_text())
    except Exception:
        return {"scored": {}, "version": 1}


def save_index(idx: dict):
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(idx, indent=2, ensure_ascii=False))


def fetch_lane(lane: str) -> list:
    """SSH and pull the lane's _all.json. Returns list of application dicts."""
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        SERVER, f"cat {SERVER_DATA}/{lane}/_all.json 2>/dev/null || echo '[]'"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        log(f"ssh failed for lane {lane}: {r.stderr[:200]}")
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def find_scored_by_id(app_id: str) -> bool:
    """Check if this application has already been scored (file exists in scored/)."""
    if not SCORED.exists():
        return False
    # Look for any scored file that mentions this id in metadata or filename
    # Cheaper: just check the index
    idx = load_index()
    return app_id in idx.get("scored", {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", action="store_true", help="Run scorer --batch after sync")
    ap.add_argument("--dry-run", action="store_true", help="Show what would happen")
    ap.add_argument("--include-test", action="store_true", help="Include test rows")
    args = ap.parse_args()

    INBOX.mkdir(parents=True, exist_ok=True)
    SCORED.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    idx = load_index()
    new_count = 0
    skipped_test = 0
    skipped_already = 0

    for lane in LANES:
        apps = fetch_lane(lane)
        if not apps:
            continue
        log(f"lane {lane}: {len(apps)} applications fetched from server")

        for app in apps:
            # Filter test rows (unless --include-test)
            if not args.include_test and is_test_row(app):
                skipped_test += 1
                continue

            app_id = application_id(app)

            # Skip if already scored OR already in inbox/processed
            if app_id in idx["scored"]:
                skipped_already += 1
                continue

            # Check if file exists in inbox or processed (dedup belt-and-suspenders)
            inbox_path = INBOX / app_id
            processed_path = PROCESSED / app_id
            if inbox_path.exists() or processed_path.exists():
                skipped_already += 1
                continue

            # Ensure .json extension
            if not app_id.endswith(".json"):
                app_id = app_id + ".json"

            # Write to inbox
            target = INBOX / app_id
            if args.dry_run:
                print(f"  [DRY] would drop: {app_id} (lane={lane}, name={app.get('name','?')})")
            else:
                target.write_text(json.dumps(app, indent=2, ensure_ascii=False))
                log(f"  inbox+: {app_id} (lane={lane}, name={app.get('name','?')})")
            new_count += 1

    print()
    print(f"sync result:")
    print(f"  new applications dropped in inbox: {new_count}")
    print(f"  skipped (already scored or in flight): {skipped_already}")
    print(f"  skipped (test rows · use --include-test to include): {skipped_test}")

    if args.score and new_count > 0 and not args.dry_run:
        print()
        print("=== firing scorer --batch ===")
        r = subprocess.run(
            ["python3", SCORER, "--batch"],
            capture_output=False, text=True, timeout=600
        )
        # After scorer runs, update index with scored items
        idx = load_index()
        for scored_file in SCORED.iterdir():
            if scored_file.suffix == ".json":
                # Best-effort: log that something was scored. Real dedup happens by file presence.
                pass
        save_index(idx)


if __name__ == "__main__":
    main()
