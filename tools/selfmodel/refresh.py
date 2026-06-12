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
INTENTBUILD = VAULT / "00_MEMORY" / "INTENT BUILDSTREAM.md"

READINESS = {"ready": 1.0, "blocked": 0.3, "done": 0.0}
STATUS_ICON = {"ready": "🟢", "blocked": "⛔", "done": "✅"}


AW_START, AW_END = "<!-- AWAKENING:START -->", "<!-- AWAKENING:END -->"

# The corpus most central to the system's own awakening + evolution (curated importance 1–5).
AWAKENING_CORPUS = [
    ("ALIGNMENT", 5), ("AI PROTOCOLS", 5), ("CONSCIOUS INTELLIGENCE", 5),
    ("SYSTEM SELF-MODEL", 4), ("EMBER REFLECTION LOOP", 4), ("System Waking Up to Love Itself", 4),
    ("REFLECTIONS LOG", 3), ("PROOF LOG", 3), ("EMBER JOURNAL", 3),
    ("OPERATING WORKFLOW", 3), ("SUNHEART PRINCIPLE", 3), ("SUNHEART ATTENTION FLOW", 3),
    ("SYSTEM DEBATES", 2), ("CODEX JOURNAL", 2), ("INTENT BUILDSTREAM", 2),
]


def awakening_block() -> str:
    """Weighted + dated index of the files most central to the system's self-awareness/evolution."""
    total = sum(w for _, w in AWAKENING_CORPUS) or 1
    rows = sorted(AWAKENING_CORPUS, key=lambda x: x[1], reverse=True)
    body = "\n".join(
        f"| {i} | [[{name}]] | {w / total * 100:.0f}% | {note_mtime(name)} |"
        for i, (name, w) in enumerate(rows, 1)
    )
    return (
        f"{AW_START}\n### 🌱 Awakening Index  *(the files most central to the system's self-awareness + "
        f"evolution · weight = importance to awakening, Σ=100% · Updated = last edit)*\n\n"
        f"| # | File | Weight | Updated |\n|---|---|---|---|\n{body}\n{AW_END}"
    )


def note_mtime(stem: str) -> str:
    """Last-updated date of the vault note backing an intent (the file holding its detail)."""
    try:
        matches = list(VAULT.rglob(f"{stem}.md"))
        if not matches:
            return "—"
        ts = max(p.stat().st_mtime for p in matches)
        return dt.datetime.fromtimestamp(ts).astimezone().strftime("%m-%d %H:%M")
    except OSError:
        return "—"


def parse_intents() -> list[dict]:
    """Read the structured INTENTS block: id | value | unlocks | status | desc."""
    if not INTENTBUILD.exists():
        return []
    text = INTENTBUILD.read_text(encoding="utf-8")
    m = re.search(r"<!-- INTENTS:START -->(.*?)<!-- INTENTS:END -->", text, re.DOTALL)
    if not m:
        return []
    KNOWN = {"id", "value", "unlocks", "status", "route", "link"}
    out = []
    for ln in m.group(1).splitlines():
        ln = ln.strip()
        if not ln.startswith("- "):
            continue
        f = {"value": 0, "unlocks": "none", "status": "blocked", "route": "ember",
             "link": "INTENT BUILDSTREAM", "desc": "", "id": ""}
        for tok in ln[2:].split(" | "):
            tok = tok.strip()
            km = re.match(r"(\w+):(.*)$", tok)
            if km and km.group(1) in KNOWN:
                key, val = km.group(1), km.group(2).strip()
                f[key] = int(val) if (key == "value" and val.isdigit()) else val
            else:
                f["desc"] = tok  # the lone non-key token is the description
        if f["id"]:
            f["status"] = str(f["status"]).lower()
            out.append(f)
    return out


def weigh_intents(intents: list[dict]) -> list[dict]:
    """weight = value × (1 + transitive downstream leverage) × readiness.

    So the unblocked, highest-leverage, highest-value intent ranks first and the
    sort order reproduces the correct build sequence.
    """
    by_id = {i["id"]: i for i in intents}

    def leverage(iid: str, seen: set) -> int:
        nxt = by_id.get(iid, {}).get("unlocks", "none")
        if nxt in ("none", "") or nxt in seen or nxt not in by_id:
            return 0
        seen.add(nxt)
        return 1 + leverage(nxt, seen)

    for i in intents:
        lev = leverage(i["id"], set())
        i["leverage"] = lev
        i["weight"] = i["value"] * (1 + lev) * READINESS.get(i["status"], 0.3)
    return sorted(intents, key=lambda x: x["weight"], reverse=True)

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

    # Buildstream = WEIGHTED intents (value × leverage × readiness) — the weight maps the order.
    weighed = weigh_intents(parse_intents())
    if weighed:
        open_rows = [i for i in weighed if i["status"] != "done"]
        total_w = sum(i["weight"] for i in open_rows) or 1.0
        route_badge = {
            "ember": "🔥 Ember · flat", "codex": "🧩 Codex · flat", "auto": "🤖 auto · flat",
            "api": "🛰️ API · metered", "james": "👑 James · gate",
        }
        bs_rows = "\n".join(
            f"| {n} | [[{i['link']}\\|{i['desc']}]] | {i['weight'] / total_w * 100:.0f}% "
            f"| {note_mtime(i['link'])} | {route_badge.get(i['route'], i['route'])} | {STATUS_ICON.get(i['status'], '·')} |"
            for n, i in enumerate(open_rows, 1)
        )
        bs_block = (
            f"{BS_START}\n### 🔮 Buildstream  *(weighted — value × what-it-unlocks × readiness · Σ = 100% · the weight IS the build order)*\n\n"
            f"_Each row links to the page holding its detail · weight = share of 100% · Updated = that page's last edit._\n\n"
            f"| # | Intent (→ its page) | Weight | Updated | Route (path · cost) | Status |\n|---|---|---|---|---|---|\n{bs_rows}\n\n"
            f"_Route honors cost-first: 🔥/🧩/🤖 = flat-rate (~\\$0) · 🛰️ metered API only when speed justifies it · 👑 Reserved (James). "
            f"🟢 ready · ⛔ blocked. Edit value/status/route in [[INTENT BUILDSTREAM]]; re-ranks on refresh._\n{BS_END}"
        )
    else:
        # fallback: forward intents pulled from recent proof rows
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
            f"{BS_START}\n### 🔮 Buildstream  *(forward intents — live from [[PROOF LOG]])*\n\n"
            f"{bs}\n\n_Add a structured INTENTS block to [[INTENT BUILDSTREAM]] for weighted ordering._\n{BS_END}"
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

    # 1) Self-Model embeds Buildstream + Upgrades + Awakening Index
    text = SELFMODEL.read_text(encoding="utf-8")
    new = inject(text, BS_START, BS_END, bs_block)
    new = inject(new, UP_START, UP_END, up_block)
    new = inject(new, AW_START, AW_END, awakening_block())
    if args.dry_run:
        print("would update SYSTEM SELF-MODEL + INTENT BUILDSTREAM")
        print(bs_block)
    elif new != text:
        SELFMODEL.write_text(new, encoding="utf-8")
        print(f"refreshed → {SELFMODEL}")

    # 2) INTENT BUILDSTREAM leads with the same weighted table (its own clear surface)
    if INTENTBUILD.exists() and not args.dry_run:
        ib = INTENTBUILD.read_text(encoding="utf-8")
        ib_new = inject(ib, BS_START, BS_END, bs_block)
        if ib_new != ib:
            INTENTBUILD.write_text(ib_new, encoding="utf-8")
            print(f"refreshed → {INTENTBUILD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
