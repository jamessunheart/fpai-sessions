#!/usr/bin/env python3
"""
Seed founding affiliates: Atlas + Halley.

Per the 5 Day Reset Retreat launch (2026-05-17):
  - Each gets 50% commission on their FIRST 2 retreat sales (founding bonus)
  - After 2 sales, drops to standard 15% per retreat sale
  - Both pre-seeded as 'active' with ZV refcodes ATLAS and HALLEY

Idempotent: re-running will SKIP existing partners (won't overwrite progress).
Use --reset to force a fresh seed (zeroes their sales count + restores founding rate).

Run on the server:
  cd /opt/fpai/apps/zen-village
  python3 scripts/seed_founding_partners.py

Or with reset (be careful — wipes founding progress):
  python3 scripts/seed_founding_partners.py --reset
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ─── Allow running from anywhere ────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
APP_ROOT = HERE.parent  # SERVICES/zen-village (local) or /opt/fpai/apps/zen-village (server)
sys.path.insert(0, str(APP_ROOT))

DATA_DIR = Path(os.environ.get("ZV_DATA_DIR", str(APP_ROOT / "data")))
if not DATA_DIR.exists():
    # Server default
    server_default = Path("/opt/fpai/apps/zen-village/data")
    if server_default.exists():
        DATA_DIR = server_default
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

PARTNERS_FILE = DATA_DIR / "partners.json"

# ─── Founding cohort definition ─────────────────────────────────────────────
SITE_BASE = os.environ.get("ZV_SITE_BASE", "https://zenvillage.live").rstrip("/")

FOUNDING_COHORT = [
    {
        "code": "ATLAS",
        "name": "Atlas",
        "email": "",  # set when known — partner can link wallet by email later
        "founding_rate": 0.50,
        "founding_sales_remaining": 2,
        "standard_rate": 0.15,
        "notes": "Founding affiliate — 5 Day Reset Retreat launch cohort (2026-05-17). 50% × first 2 sales → 15% standard.",
    },
    {
        "code": "HALLEY",
        "name": "Halley",
        "email": "",
        "founding_rate": 0.50,
        "founding_sales_remaining": 2,
        "standard_rate": 0.15,
        "notes": "Founding affiliate — 5 Day Reset Retreat launch cohort (2026-05-17). 50% × first 2 sales → 15% standard.",
    },
]


def _load(p: Path) -> dict:
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception as e:
            print(f"  ! failed to load {p}: {e}", file=sys.stderr)
            return {}
    return {}


def _save(p: Path, data: dict) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    os.replace(tmp, p)


def seed(reset: bool = False) -> int:
    p = PARTNERS_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    partners = _load(p)

    created = 0
    reset_count = 0
    skipped = 0

    for spec in FOUNDING_COHORT:
        code = spec["code"]
        existing = partners.get(code)

        if existing and not reset:
            print(f"  · {code} ({spec['name']}) — already exists, skipping")
            print(f"      ref link:    {SITE_BASE}/reset?ref={code}")
            print(f"      founding remaining: {existing.get('founding_sales_remaining', '—')}")
            print(f"      total earned:       ${existing.get('total_earned', 0):.2f}")
            skipped += 1
            continue

        if existing and reset:
            # Preserve totals but restore founding state
            partners[code] = {
                **existing,
                "founding_rate": spec["founding_rate"],
                "founding_sales_remaining": spec["founding_sales_remaining"],
                "standard_rate": spec["standard_rate"],
                "founding_completed_at": None,
                "status": "active",
            }
            print(f"  ↻ {code} ({spec['name']}) — founding rates RESET to 50% × 2")
            reset_count += 1
            continue

        partners[code] = {
            "code": code,
            "name": spec["name"],
            "email": spec.get("email") or "",
            "phone": "",
            "payout_method": "credits",
            "notes": spec.get("notes", ""),
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "total_referrals": 0,
            "total_earned": 0,
            "pending_payout": 0,
            "is_producer": False,
            "founding_rate": spec["founding_rate"],
            "founding_sales_remaining": spec["founding_sales_remaining"],
            "standard_rate": spec["standard_rate"],
            "founding_cohort": "5day_reset_2026-05-17",
        }
        print(f"  + {code} ({spec['name']}) — CREATED")
        print(f"      ref link: {SITE_BASE}/reset?ref={code}")
        created += 1

    _save(p, partners)
    print()
    print(f"  → Wrote {p}")
    print(f"  → Created: {created}  ·  Reset: {reset_count}  ·  Skipped (already existed): {skipped}")
    print()
    print("Pre-seeded founding affiliates can be shared immediately:")
    for spec in FOUNDING_COHORT:
        print(f"  • {spec['name']:8s}  {SITE_BASE}/reset?ref={spec['code']}")
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Restore founding rate + count for existing partners (preserves totals)",
    )
    args = parser.parse_args()

    print(f"Seeding founding partners → {PARTNERS_FILE}")
    print()
    return seed(reset=args.reset)


if __name__ == "__main__":
    raise SystemExit(main())
