#!/usr/bin/env python3
"""Self-Model refresh — surface the system's Buildstream + Upgrades from the PROOF LOG.

Both horizons are derived from the one source the system already writes (PROOF LOG),
via the Buildstream-Law fields:
  - ⬆️ Upgrades   = recent "Intent solved" (what shipped)
  - 🔮 Buildstream = recent "Next move" / "Unlocks next" (the live forward intents)

Injects into 00_MEMORY/SYSTEM SELF-MODEL.md between the BUILDSTREAM / UPGRADES markers.
Leaves the curated spine + reflections blocks untouched.

Usage:  python3 tools/selfmodel/refresh.py [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from pathlib import Path

HOME = Path.home()
VAULT = Path(
    os.environ.get(
        "FPAI_VAULT",
        HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian"
        / "Documents" / "FPOS" / "Full Potential OS",
    )
)
PROOF = VAULT / "00_MEMORY" / "PROOF LOG.md"
SELFMODEL = VAULT / "00_MEMORY" / "SYSTEM SELF-MODEL.md"

UP_START, UP_END = "<!-- UPGRADES:START -->", "<!-- UPGRADES:END -->"
BS_START, BS_END = "<!-- BUILDSTREAM:START -->", "<!-- BUILDSTREAM:END -->"
N_UPGRADES = 8
N_BUILDSTREAM = 6


def parse_proof() -> list[dict]:
    """Newest-first list of {stamp, solved, unlocks, next} from the PROOF LOG."""
    if not PROOF.exists():
        return []
    out = []
    started = False
    for ln in PROOF.read_text(encoding="utf-8").splitlines():
        if not started:
            if ln.strip() == "---":
                started = True
            continue
        if not ln.startswith("- "):
            continue
        stamp_m = re.match(r"- (\d{4}-\d{2}-\d{2}[^·]*)·", ln)
        stamp = stamp_m.group(1).strip() if stamp_m else ""
        solved = _field(ln, "Intent solved")
        if not solved:  # old-format row → text after [stream]
            parts = ln.split("·", 2)
            solved = parts[2].strip() if len(parts) > 2 else ln[2:].strip()
        out.append({
            "stamp": stamp,
            "solved": _clip(solved),
            "unlocks": _clip(_field(ln, "Unlocks next")),
            "next": _clip(_field(ln, "Next move")),
        })
    return out


def _field(line: str, name: str) -> str:
    m = re.search(rf"{name}:\s*(.+?)(?:· Unlocks next:|· Proof:|· Files:|· Next move:|· [A-Z]\w+\(|$)", line)
    return m.group(1).strip() if m else ""


def _clip(s: str, n: int = 120) -> str:
    s = re.sub(r"\s+", " ", s).strip(" ·")
    return (s[: n - 1] + "…") if len(s) > n else s


def build_blocks(now: dt.datetime) -> tuple[str, str]:
    rows = parse_proof()
    gen = now.strftime("%Y-%m-%d %H:%M %Z")

    # Upgrades = what shipped
    ups = "\n".join(f"- `{r['stamp']}` — {r['solved']}" for r in rows[:N_UPGRADES] if r["solved"]) or "_none yet_"
    up_block = f"{UP_START}\n### ⬆️ Upgrades  *(what shipped — live from [[PROOF LOG]] · {gen})*\n\n{ups}\n{UP_END}"

    # Buildstream = the live forward intents (unlocks/next from recent ships), deduped
    seen, intents = set(), []
    for r in rows:
        for fld in (r["next"], r["unlocks"]):
            key = fld.lower()[:40]
            if fld and key not in seen:
                seen.add(key)
                intents.append(fld)
        if len(intents) >= N_BUILDSTREAM:
            break
    bs = "\n".join(f"- 🔮 {x}" for x in intents[:N_BUILDSTREAM]) or "_none yet_"
    bs_block = (
        f"{BS_START}\n### 🔮 Buildstream  *(open intents — what recent ships unlocked · live from [[PROOF LOG]])*\n\n"
        f"{bs}\n\n_Curated build order + rungs: [[INTENT BUILDSTREAM]] · [[SPEC LOG]] · [[AI PROTOCOLS]] (the 4 Rungs)._\n{BS_END}"
    )
    return bs_block, up_block


def inject(text: str, start: str, end: str, block: str) -> str:
    if start in text and end in text:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block, text, count=1, flags=re.DOTALL)
    return text  # markers must pre-exist


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Refresh Self-Model Buildstream + Upgrades from PROOF LOG.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not SELFMODEL.exists():
        print(f"MISSING: {SELFMODEL}")
        return 1
    now = dt.datetime.now().astimezone()
    bs_block, up_block = build_blocks(now)
    text = SELFMODEL.read_text(encoding="utf-8")
    new = inject(text, BS_START, BS_END, bs_block)
    new = inject(new, UP_START, UP_END, up_block)
    if args.dry_run:
        print("would update SYSTEM SELF-MODEL")
        print(bs_block + "\n\n" + up_block)
    elif new != text:
        SELFMODEL.write_text(new, encoding="utf-8")
        print(f"refreshed → {SELFMODEL}")
    else:
        print("unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
