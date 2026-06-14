#!/usr/bin/env python3
"""Audit core/STATE/catalog.json against SERVICES/ directory.

Reports:
  - Untagged services (in SERVICES/ but not in catalog.tags)
  - Stale catalog entries (tagged but no matching directory)
  - Tag suggestions for untagged services based on name patterns

Usage:
  python3 tools/audit_catalog.py            # human-readable report
  python3 tools/audit_catalog.py --json     # machine-readable
  python3 tools/audit_catalog.py --apply    # write suggestions into catalog.json
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "core/STATE/catalog.json"
SERVICES_DIR = ROOT / "SERVICES"

# Pattern → suggested tag. Earlier patterns win.
# These reflect James's "deprioritize, don't add" bias and the historical
# noise in this repo (consciousness/autonomous/breakthrough sprawl).
PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"^(zen-village|village)"), "P1", "named for the P1 engine"),
    (re.compile(r"^concierge"), "P2", "named for the P2 product"),
    (re.compile(r"^(alerts|chief-of-staff|proactive-monitor|brain|sunheart-brain|sh-brain|nginx|api-gateway|auto-healer|credentials-manager|email-dashboard)"), "infra", "core plumbing"),
    (re.compile(r"^(consciousness|autonomous|breakthrough|god-mode|swarm|mesh|apprentice|evolution|conscious|soul|spirit|divine|sacred|manifest|harvest|magnet|oracle|sage|wisdom|mystic|transcend|cosmic|quantum|infinity|infinite|coherence|alignment-economics)"), "cruft", "historical sprawl pattern"),
    (re.compile(r".*(_test|-test|-demo|-example|-experiment)$"), "cruft", "test/demo/experiment"),
]


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def list_service_dirs() -> list[str]:
    if not SERVICES_DIR.exists():
        return []
    return sorted(
        p.name for p in SERVICES_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def suggest_tag(name: str) -> tuple[str, str] | None:
    for pat, tag, reason in PATTERNS:
        if pat.match(name):
            return tag, reason
    return None


def audit() -> dict:
    cat = load_catalog()
    tagged: dict[str, str] = cat.get("tags", {})
    dirs = list_service_dirs()
    in_dir = set(dirs)
    in_cat = set(tagged.keys())

    untagged = sorted(in_dir - in_cat)
    stale = sorted(in_cat - in_dir)

    suggestions: dict[str, dict] = {}
    unsuggested: list[str] = []
    for name in untagged:
        s = suggest_tag(name)
        if s:
            tag, reason = s
            suggestions[name] = {"tag": tag, "reason": reason}
        else:
            unsuggested.append(name)

    return {
        "totals": {
            "service_dirs": len(dirs),
            "catalog_entries": len(tagged),
            "untagged": len(untagged),
            "stale": len(stale),
        },
        "untagged": untagged,
        "stale": [{"name": s, "current_tag": tagged.get(s)} for s in stale],
        "suggestions": suggestions,
        "unsuggested": unsuggested,
    }


def report_human(result: dict) -> None:
    t = result["totals"]
    print(f"Service dirs:    {t['service_dirs']}")
    print(f"Catalog entries: {t['catalog_entries']}")
    print(f"Untagged:        {t['untagged']}")
    print(f"Stale (no dir):  {t['stale']}")
    print()

    if result["untagged"]:
        print("--- Untagged services ---")
        for name in result["untagged"]:
            s = result["suggestions"].get(name)
            if s:
                print(f"  {name:40s}  → suggest {s['tag']:6s}  ({s['reason']})")
            else:
                print(f"  {name:40s}  → no pattern match (manual decision)")
        print()

    if result["stale"]:
        print("--- Stale catalog entries (tagged but no directory) ---")
        for entry in result["stale"]:
            print(f"  {entry['name']:40s}  was: {entry['current_tag']}")
        print()

    if not result["untagged"] and not result["stale"]:
        print("Catalog is clean.")


def apply_suggestions(result: dict) -> int:
    """Write suggestions into catalog.json. Returns count applied."""
    cat = load_catalog()
    tags = cat.setdefault("tags", {})
    applied = 0
    for name, s in result["suggestions"].items():
        if name not in tags:
            tags[name] = s["tag"]
            applied += 1
    if applied:
        # Preserve key order: existing keys first, new keys appended
        CATALOG.write_text(
            json.dumps(cat, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return applied


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--apply", action="store_true", help="write suggestions into catalog.json")
    args = ap.parse_args()

    result = audit()

    if args.apply:
        n = apply_suggestions(result)
        print(f"Applied {n} suggestion(s) to {CATALOG}")
        return 0

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        report_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
