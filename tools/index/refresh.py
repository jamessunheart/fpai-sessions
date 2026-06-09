#!/usr/bin/env python3
"""Self-refreshing Index of Indexes — Rung 2 (self-refreshing surfaces).

Regenerates the AUTO blocks inside the Index of Indexes (vault + repo mirror)
from GROUND TRUTH, so the system mirror can never quietly drift:

  - Link health: validate every [[wikilink]] against real vault notes.
  - Surface freshness: real file mtimes + existence for every tracked path.
  - Latest updates: the newest PROOF LOG entries, pulled live.

It only rewrites content between `<!-- AUTO:START -->` and `<!-- AUTO:END -->`;
all hand-written sections are left untouched. Writes both the vault canonical
and the repo mirror so Ember and Codex see the same picture.

Usage:
    python3 tools/index/refresh.py [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback for very old Python builds
    ZoneInfo = None

HOME = Path.home()
VAULT = Path(
    os.environ.get(
        "FPAI_VAULT",
        HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian"
        / "Documents" / "FPOS" / "Full Potential OS",
    )
)
REPO = Path(os.environ.get("FPAI_REPO", HOME / "FPAI_Cockpit"))
LOC = Path(os.environ.get("FPAI_LOCATION_FILE", HOME / ".config" / "fpai" / "location.json"))

VAULT_INDEX = VAULT / "00_MEMORY" / "INDEX OF INDEXES.md"
REPO_INDEX = REPO / "docs" / "codex" / "INDEX_OF_INDEXES.md"
PROOF = VAULT / "00_MEMORY" / "PROOF LOG.md"
SELFMODEL = VAULT / "00_MEMORY" / "SYSTEM SELF-MODEL.md"


def parse_spine() -> list[str]:
    """Curated operating spine — the single source of truth is SYSTEM SELF-MODEL.md.

    Reads `- [[Name]] — why` lines between <!-- SPINE:START --> and <!-- SPINE:END -->.
    """
    if not SELFMODEL.exists():
        return []
    text = SELFMODEL.read_text(encoding="utf-8")
    m = re.search(r"<!-- SPINE:START -->(.*?)<!-- SPINE:END -->", text, re.DOTALL)
    if not m:
        return []
    spine = []
    for ln in m.group(1).splitlines():
        lm = re.match(r"\s*-\s*\[\[([^\]|#]+)", ln)
        if lm:
            spine.append(lm.group(1).strip())
    return spine

START = "<!-- AUTO:START -->"
END = "<!-- AUTO:END -->"
LATEST_N = 6


def time_label(tz_name: str, place: str | None = None) -> str:
    labels = {
        "America/Costa_Rica": "CR Time",
        "Europe/Athens": "Greece Time",
        "America/Denver": "MT Time",
        "America/Los_Angeles": "PT Time",
        "America/New_York": "ET Time",
    }
    if tz_name in labels:
        return labels[tz_name]
    if place:
        cleaned = re.sub(r"[^\w\s/-]", "", place).strip()
        if "costa rica" in cleaned.lower():
            return "CR Time"
        if "greece" in cleaned.lower():
            return "Greece Time"
        if cleaned:
            first = cleaned.split()[0]
            return f"{first} Time"
    return "Local Time"


def display_time_context() -> tuple[dt.tzinfo, str]:
    tz_name = os.environ.get("FPAI_DISPLAY_TZ")
    label = os.environ.get("FPAI_DISPLAY_TZ_LABEL")
    place = None
    if not tz_name:
        try:
            loc = json.loads(LOC.read_text(encoding="utf-8"))
            tz_name = loc.get("tz")
            place = loc.get("place")
        except Exception:
            tz_name = None
    if tz_name and ZoneInfo:
        try:
            zone = ZoneInfo(tz_name)
            return zone, label or time_label(tz_name, place)
        except Exception:
            pass
    local = dt.datetime.now().astimezone().tzinfo
    return local or dt.timezone.utc, label or time_label(dt.datetime.now().astimezone().tzname() or "", place)


DISPLAY_TZ, DISPLAY_LABEL = display_time_context()


def clock(d: dt.datetime) -> str:
    hour = d.hour % 12 or 12
    return f"{hour}:{d:%M} {d:%p}"


def fmt_time(d: dt.datetime, now: dt.datetime | None = None, *, force_date: bool = False) -> str:
    local = d.astimezone(DISPLAY_TZ)
    current = (now or dt.datetime.now(tz=DISPLAY_TZ)).astimezone(DISPLAY_TZ)
    if not force_date and local.date() == current.date():
        return f"{clock(local)} {DISPLAY_LABEL}"
    if local.year == current.year:
        return f"{local:%b} {local.day} · {clock(local)} {DISPLAY_LABEL}"
    return f"{local:%b} {local.day}, {local.year} · {clock(local)} {DISPLAY_LABEL}"


def vault_note_stems() -> set[str]:
    return {p.stem for p in VAULT.rglob("*.md")}


# Operational dirs where an orphan is actionable (mindmaps/sessions are imported, noise as orphans).
OPERATIONAL = ("00_MEMORY/", "02_SPECS/", "01_OFFERS/", "05_CONCEPTS/", "06_SHOW FRAMES/")


def build_link_graph() -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, Path]]:
    """Return (outlinks, backlinks, stem→path) over the whole vault link graph.

    outlinks[stem] = set of note stems this note links TO (resolved to real notes).
    backlinks[stem] = set of note stems that link TO this note.
    """
    paths: dict[str, Path] = {}
    raw_out: dict[str, set[str]] = {}
    for p in VAULT.rglob("*.md"):
        stem = p.stem
        paths[stem] = p
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            text = ""
        links = re.findall(r"\[\[([^\]]+)\]\]", text)
        targets = {l.split("|")[0].split("#")[0].strip() for l in links}
        raw_out[stem] = targets

    stems = set(paths)
    outlinks = {s: {t for t in tgts if t in stems and t != s} for s, tgts in raw_out.items()}
    backlinks: dict[str, set[str]] = {s: set() for s in stems}
    for s, tgts in outlinks.items():
        for t in tgts:
            backlinks[t].add(s)
    return outlinks, backlinks, paths


def is_operational(path: Path) -> bool:
    rel = str(path.relative_to(VAULT)) if str(path).startswith(str(VAULT)) else str(path)
    return any(rel.startswith(d) for d in OPERATIONAL) or "/" not in rel  # root-level too


def fmt_mtime(path: Path, now: dt.datetime | None = None) -> str:
    try:
        ts = path.stat().st_mtime
    except OSError:
        return "—"
    return fmt_time(dt.datetime.fromtimestamp(ts, tz=DISPLAY_TZ), now)


def resolve_tracked_path(token: str) -> tuple[Path, str]:
    """Map a backticked path token to an actual file under vault or repo."""
    token = token.rstrip("/")
    for root, label in ((VAULT, "vault"), (REPO, "repo")):
        cand = root / token
        if cand.exists():
            return cand, label
    return (VAULT / token), "missing"


def link_health(index_text: str, stems: set[str]) -> tuple[str, int, int]:
    links = re.findall(r"\[\[([^\]]+)\]\]", index_text)
    targets = []
    seen = set()
    for l in links:
        t = l.split("|")[0].split("#")[0].strip()
        if t and t not in seen:
            seen.add(t)
            targets.append(t)
    broken = [t for t in targets if t not in stems]
    ok = len(targets) - len(broken)
    if broken:
        body = f"⚠️ **{len(broken)} broken** of {len(targets)} wikilinks: " + ", ".join(
            f"`[[{b}]]`" for b in broken
        )
    else:
        body = f"✅ all {len(targets)} wikilinks resolve"
    return body, ok, len(broken)


def latest_updates() -> str:
    if not PROOF.exists():
        return "_(no PROOF LOG found)_"
    lines = PROOF.read_text(encoding="utf-8").splitlines()
    # entries are bullet lines after the first '---'
    started = False
    out = []
    for ln in lines:
        if not started:
            if ln.strip() == "---":
                started = True
            continue
        if ln.startswith("- "):
            # stamp = first segment; intent = 'Intent solved:' chunk if present
            stamp_m = re.match(r"- (\d{4}-\d{2}-\d{2}[^·]*)·", ln)
            stamp = stamp_m.group(1).strip() if stamp_m else ""
            m = re.search(r"Intent solved:\s*(.+?)(?:· Unlocks next:|· Proof:|$)", ln)
            if m:
                desc = m.group(1).strip()
            else:
                # fallback: text after the [stream] tag
                parts = ln.split("·", 2)
                desc = parts[2].strip() if len(parts) > 2 else ln[2:]
            desc = re.sub(r"\s+", " ", desc)
            if len(desc) > 130:
                desc = desc[:127] + "…"
            out.append(f"- `{stamp}` — {desc}")
        if len(out) >= LATEST_N:
            break
    return "\n".join(out) if out else "_(no entries parsed)_"


# Category display order + icon. Anything else falls through to alphabetical.
CATEGORY_ORDER = [
    ("🏠 Root", "🏠 Root"),
    ("00_MEMORY", "🧠 Memory · 00_MEMORY"),
    ("02_SPECS", "📐 Specs · 02_SPECS"),
    ("01_OFFERS", "💵 Offers · 01_OFFERS"),
    ("04_VISUALS", "🖼️ Visuals · 04_VISUALS"),
    ("Mindmaps", "🗺️ Mindmaps"),
    ("05_CONCEPTS", "💡 Concepts · 05_CONCEPTS"),
    ("06_SHOW FRAMES", "🎬 Show Frames · 06_SHOW FRAMES"),
    ("03_TICKETS", "🎟️ Tickets · 03_TICKETS"),
    ("07_DAILY", "🌤️ Daily · 07_DAILY"),
    ("08_JOURNAL", "📓 Journal · 08_JOURNAL"),
]
ACTIVE_WINDOW_S = 24 * 3600  # "actively working" = touched in the last 24h
SKIP_PARTS = ("_ember_memory", "_archive", "node_modules", ".trash", ".obsidian")


def categorize(path: Path) -> str | None:
    rel = path.relative_to(VAULT)
    parts = rel.parts
    if any(p in SKIP_PARTS or p.startswith(".") for p in parts):
        return None
    if len(parts) == 1:
        return "🏠 Root"
    if parts[0] == "04_VISUALS" and len(parts) > 1 and parts[1] == "Mindmaps":
        return "Mindmaps"
    return parts[0]


def pagerank(outlinks: dict[str, set[str]], nodes: set[str], d: float = 0.85, iters: int = 50) -> dict[str, float]:
    """PageRank over the wikilink graph → each page's share of system importance (Σ=1.0)."""
    n = len(nodes)
    if n == 0:
        return {}
    rank = {s: 1.0 / n for s in nodes}
    outdeg = {s: len(outlinks.get(s, ())) for s in nodes}
    for _ in range(iters):
        dangling = sum(rank[s] for s in nodes if outdeg[s] == 0)
        new = {s: (1 - d) / n + d * dangling / n for s in nodes}
        for s in nodes:
            if outdeg[s]:
                share = d * rank[s] / outdeg[s]
                for t in outlinks[s]:
                    if t in new:
                        new[t] += share
        rank = new
    total = sum(rank.values()) or 1.0
    return {s: rank[s] / total for s in nodes}


TOP_WEIGHTED = 30
CLAIMS = Path(os.environ.get("FPAI_INDEX_CLAIMS", HOME / ".config" / "fpai" / "index" / "claims.json"))


def load_claims() -> dict:
    """Active work-claims: {page_stem: {owner, started}} — a 🔴 page is being edited; don't collide."""
    try:
        import json
        return json.loads(CLAIMS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_auto_block(index_text: str, now: dt.datetime) -> str:
    stems = vault_note_stems()
    link_body, ok, broken = link_health(index_text, stems)
    outlinks, backlinks, paths = build_link_graph()
    weight = pagerank(outlinks, stems)

    # --- ⭐ Operating spine (curated — source of truth: SYSTEM SELF-MODEL.md) ---
    spine = parse_spine()
    spine_set = set(spine)
    claims = load_claims()
    if spine:
        spine_rows = "\n".join(
            f"| {i} | [[{s}]] | {weight.get(s, 0) * 100:.1f}% | {fmt_mtime(paths[s], now) if s in paths else '—'} "
            f"| {('🔴 ' + claims[s].get('owner', 'working')) if s in claims else '🟢 clear'} |"
            for i, s in enumerate(spine, 1)
        )
        spine_section = (
            "### ⭐ Operating spine  *(curated — what RUNS the system · "
            "see [[SYSTEM SELF-MODEL]] for how these were chosen)*\n\n"
            "| # | Page | Weight | Updated | Status |\n|---|---|---|---|---|\n" + spine_rows + "\n"
        )
    else:
        spine_section = ""

    # group every note by category + collect active
    cats: dict[str, list[Path]] = {}
    active: list[tuple[float, Path]] = []
    cutoff = now.timestamp() - ACTIVE_WINDOW_S
    total = 0
    for p in sorted(VAULT.rglob("*.md")):
        cat = categorize(p)
        if cat is None:
            continue
        total += 1
        cats.setdefault(cat, []).append(p)
        try:
            mt = p.stat().st_mtime
        except OSError:
            mt = 0
        if mt >= cutoff:
            active.append((mt, p))

    # --- ⭐ Most weighted pages (the headline: importance, Σ=100%) ---
    # rank only the SAME categorized notes the directory counts, so counts stay consistent
    cat_stems = {p.stem for lst in cats.values() for p in lst}
    ranked = [kv for kv in sorted(weight.items(), key=lambda kv: kv[1], reverse=True) if kv[0] in cat_stems]
    shown = sum(w for _, w in ranked[:TOP_WEIGHTED]) * 100
    top_rows = "\n".join(
        f"| {i} | [[{s}]] | {w * 100:.1f}% |"
        for i, (s, w) in enumerate(ranked[:TOP_WEIGHTED], 1)
    )
    tail = sum(w for _, w in ranked[TOP_WEIGHTED:]) * 100
    tail_line = f"_top {TOP_WEIGHTED} = {shown:.1f}% · + {len(ranked) - TOP_WEIGHTED} more pages = {tail:.1f}%_" if len(ranked) > TOP_WEIGHTED else ""

    # --- 🔴 Active now (highlights — the only dated entries) ---
    active.sort(reverse=True)
    if active:
        active_lines = "\n".join(
            f"- 🔴 [[{p.stem}]] · {fmt_time(dt.datetime.fromtimestamp(mt, tz=DISPLAY_TZ), now)}"
            for mt, p in active[:10]
        )
        if len(active) > 10:
            active_lines += f"\n- … +{len(active) - 10} more touched today"
    else:
        active_lines = "_nothing touched in the last 24h_"

    # --- 🗂️ Full directory: ONE collapsed toggle, categories inside (links only) ---
    ordered = [c for c, _ in CATEGORY_ORDER if c in cats]
    ordered += sorted(c for c in cats if c not in {c0 for c0, _ in CATEGORY_ORDER})
    label = {c0: lbl for c0, lbl in CATEGORY_ORDER}
    inner = []
    for cat in ordered:
        files = sorted(cats[cat], key=lambda p: weight.get(p.stem, 0), reverse=True)
        inner.append(f"> **{label.get(cat, cat)} · {len(files)}**")
        inner.extend(f"> - [[{p.stem}]]" for p in files)
        inner.append(">")
    directory = f"> [!abstract]- 🗂️ Full directory — every page by category · {total}\n" + "\n".join(inner)

    # --- 🧭 Orphans: collapsed ---
    orphans = sorted(
        p.stem for p in (q for lst in cats.values() for q in lst)
        if len(backlinks.get(p.stem, ())) == 0 and len(outlinks.get(p.stem, ())) == 0 and is_operational(p)
    )
    if orphans:
        orphan_block = (
            f"> [!warning]- 🧭 Orphans (unlinked — wire or archive) · {len(orphans)}\n"
            + "\n".join(f"> - [[{s}]]" for s in orphans)
        )
    else:
        orphan_block = "> [!success] 🧭 Orphans · 0 — every operational note is linked"

    gen = fmt_time(now, now, force_date=True)
    health = "🟢" if broken == 0 else "🔴"

    return f"""{START}
## 🗂️ Index of Indexes  *(auto-generated · do not edit by hand)*

{spine_section}
### 📊 Most weighted pages  *(computed — what the system is ABOUT, by link-density)*

| # | Page | Weight |
|---|---|---|
{top_rows}

{tail_line}

### 🔴 Active now  *(touched in last 24h)*

{active_lines}

{directory}

{orphan_block}

---
### 📋 Reference  *(metadata + protocol — kept at the bottom so the index leads)*

_{gen} · {total} pages · {health} links {ok}/{ok + broken} · weight = PageRank over wikilinks (Σ = 100%) · refresh: `python3 tools/index/refresh.py`_

> ⚙️ **Work-claim protocol (no collisions):** before editing a surface, claim it →
> `python3 tools/index/claim.py --page "<Page>" --owner <you>` (sets 🔴 in the spine Status above) · clear after →
> `python3 tools/index/claim.py --clear --page "<Page>"`. **Never edit a 🔴 page another AI holds.** Drift rules, repo & layer maps → [[INDEX OF INDEXES — PROTOCOL]].
{END}"""


def inject(text: str, block: str) -> str:
    if START in text and END in text:
        return re.sub(
            re.escape(START) + r".*?" + re.escape(END),
            lambda _: block,
            text,
            count=1,
            flags=re.DOTALL,
        )
    # no markers yet → insert after the first H1 line
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            lines.insert(i + 1, "\n" + block + "\n")
            return "\n".join(lines)
    return block + "\n\n" + text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Refresh the Index of Indexes AUTO blocks.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    now = dt.datetime.now().astimezone()

    # The vault index is canonical for computing link health (it has the wikilinks).
    if not VAULT_INDEX.exists():
        print(f"MISSING vault index: {VAULT_INDEX}")
        return 1
    vault_text = VAULT_INDEX.read_text(encoding="utf-8")
    block = build_auto_block(vault_text, now)

    for target in (VAULT_INDEX, REPO_INDEX):
        if not target.exists():
            print(f"skip (missing): {target}")
            continue
        text = target.read_text(encoding="utf-8")
        new = inject(text, block)
        if args.dry_run:
            print(f"would update → {target}")
        elif new != text:
            target.write_text(new, encoding="utf-8")
            print(f"refreshed → {target}")
        else:
            print(f"unchanged → {target}")

    print("\n" + block.split("\n", 2)[2].split("### Latest")[0].strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
