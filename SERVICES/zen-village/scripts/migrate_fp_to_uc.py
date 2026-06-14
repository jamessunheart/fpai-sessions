#!/usr/bin/env python3
"""
One-time migration: fp_credits → uc on the fp-credits-gateway.

For every zenpass:* and member:* account that currently holds an `fp_credits`
balance, debit that fp_credits and credit the same amount as `uc`. Idempotent
when run multiple times (only acts on accounts that still hold fp_credits).

Run:
    cd /opt/fpai/apps/zen-village
    CREDITS_GATEWAY_URL=http://127.0.0.1:8765 \
    CREDITS_GATEWAY_KEY=$ZV_CREDITS_GATEWAY_KEY \
    python3 scripts/migrate_fp_to_uc.py --dry-run
    python3 scripts/migrate_fp_to_uc.py --apply

The script first fetches the list of accounts via /api/accounts (paginated). If
that endpoint isn't available, you can pass --account-id repeatedly to migrate
specific known accounts.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Iterable

import httpx

GATEWAY = os.environ.get("CREDITS_GATEWAY_URL", "http://127.0.0.1:8765")
KEY = os.environ.get("CREDITS_GATEWAY_KEY", "")


def _h() -> dict:
    return {"X-API-Key": KEY, "Content-Type": "application/json"}


def list_accounts(client: httpx.Client) -> list[dict]:
    """Try a few common endpoints. Returns [] if the gateway doesn't expose a list."""
    for path in ("/api/accounts", "/api/accounts/list", "/api/admin/accounts"):
        try:
            r = client.get(GATEWAY + path, headers=_h(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and "accounts" in data:
                    return data["accounts"]
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def fetch_balance(client: httpx.Client, account_id: str) -> dict:
    r = client.get(f"{GATEWAY}/api/balance/{account_id}", headers=_h(), timeout=10)
    if r.status_code != 200:
        return {}
    data = r.json() or {}
    return data.get("balances") or {"_legacy": data.get("balance", 0.0)}


def migrate_one(client: httpx.Client, account_id: str, dry_run: bool) -> tuple[bool, str]:
    bal = fetch_balance(client, account_id)
    fp = float(bal.get("fp_credits") or 0)
    if fp <= 0:
        return False, f"{account_id}: no fp_credits balance"
    if dry_run:
        return True, f"{account_id}: would migrate {fp:.2f} fp_credits → uc"
    debit = client.post(
        f"{GATEWAY}/api/debit",
        headers=_h(),
        json={
            "account_id": account_id,
            "amount": fp,
            "credit_type": "fp_credits",
            "reason": "migrate fp_credits → uc",
        },
        timeout=10,
    )
    if debit.status_code >= 300:
        return False, f"{account_id}: debit failed {debit.status_code} {debit.text[:200]}"
    credit = client.post(
        f"{GATEWAY}/api/credit",
        headers=_h(),
        json={
            "account_id": account_id,
            "amount": fp,
            "credit_type": "uc",
            "reason": "migrate fp_credits → uc",
        },
        timeout=10,
    )
    if credit.status_code >= 300:
        return False, f"{account_id}: credit failed {credit.status_code} {credit.text[:200]}"
    return True, f"{account_id}: migrated {fp:.2f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually run the migration")
    ap.add_argument("--dry-run", action="store_true", help="show what would happen")
    ap.add_argument("--account-id", action="append", default=[], help="migrate specific id(s)")
    ap.add_argument("--prefix", action="append", default=["zenpass:", "member:"], help="account_id prefixes to scan")
    args = ap.parse_args()

    if not KEY:
        print("CREDITS_GATEWAY_KEY env var required", file=sys.stderr)
        return 2
    dry_run = not args.apply
    if not args.apply and not args.dry_run:
        print("Defaulting to --dry-run. Use --apply to actually migrate.")

    targets: list[str] = list(args.account_id)
    with httpx.Client() as client:
        if not targets:
            accounts = list_accounts(client)
            if not accounts:
                print("Could not list accounts. Pass --account-id IDS explicitly.")
                return 1
            for a in accounts:
                aid = a.get("account_id") or a.get("id") or ""
                if not aid:
                    continue
                if any(aid.startswith(p) for p in args.prefix):
                    targets.append(aid)
        print(f"Scanning {len(targets)} accounts (apply={args.apply})…")
        migrated = 0
        for aid in targets:
            try:
                ok, msg = migrate_one(client, aid, dry_run=dry_run)
                if ok:
                    migrated += 1
                print(("✓ " if ok else "  ") + msg)
                time.sleep(0.05)
            except Exception as e:
                print(f"  {aid}: error {e}")
        print(f"\nDone. {migrated} accounts {'would be ' if dry_run else ''}migrated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
