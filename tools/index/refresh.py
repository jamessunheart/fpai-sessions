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
REPO = Path(os.environ.get("FPAI_REPO", HOME / "FPAI_Cockpit"))

VAULT_INDEX = VAULT / "00_MEMORY" / "INDEX OF INDEXES.md"
REPO_INDEX = REPO / "docs" / "codex" / "INDEX_OF_INDEXES.md"
PROOF = VAULT / "00_MEMORY" / "PROOF LOG.md"

START = "<!-- AUTO:START -->"
END = "<!-- AUTO:END -->"
LATEST_N = 6


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


def fmt_mtime(path: Path) -> str:
    try:
        ts = path.stat().st_mtime
    except OSError:
        return "—"
    return dt.datetime.fromtimestamp(ts).astimezone().strftime("%Y-%m-%d %H:%M %Z")


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


def build_auto_block(index_text: str, now: dt.datetime) -> str:
    stems = vault_note_stems()
    link_body, ok, broken = link_health(index_text, stems)
    outlinks, backlinks, paths = build_link_graph()

    def degree(stem: str) -> tuple[int, int]:
        return len(backlinks.get(stem, ())), len(outlinks.get(stem, ()))

    # --- Surface freshness (tracked paths), now with clickable links + connectivity ---
    tokens = re.findall(r"`((?:00_MEMORY|02_SPECS|04_VISUALS|docs/codex|tools)/[^`]+|AGENTS\.md|HOME\.md|FPOS COCKPIT\.md)`", index_text)
    seen = set()
    tokens = [t for t in tokens if not (t in seen or seen.add(t))]
    rows = []
    miss = 0
    for tk in tokens:
        if tk.endswith("/*") or tk.endswith("/"):
            continue
        path, label = resolve_tracked_path(tk)
        exists = label != "missing"
        if not exists:
            miss += 1
        mark = "✓" if exists else "✗ MISSING"
        stem = Path(tk).stem
        # vault notes → clickable wikilink + in/out connectivity; repo files → path
        if label == "vault" and stem in stems:
            ind, outd = degree(stem)
            surface = f"[[{stem}]]"
            conn = f"{ind}·{outd}"
        else:
            surface = f"`{tk}`"
            conn = "—"
        rows.append(f"| {surface} | {label} | {fmt_mtime(path) if exists else '—'} | {conn} | {mark} |")
    table = "\n".join(rows)

    # --- Hubs: the system's centers of gravity (highest total link degree) ---
    deg_all = sorted(stems, key=lambda s: (len(backlinks[s]) + len(outlinks.get(s, ()))), reverse=True)
    hub_rows = []
    for s in deg_all[:12]:
        ind, outd = degree(s)
        if ind + outd == 0:
            break
        hub_rows.append(f"| [[{s}]] | {ind} | {outd} | {ind + outd} |")
    hubs = "\n".join(hub_rows)

    # --- Orphans: operational notes with no links in OR out (invisible to the system) ---
    orphans = [
        s for s in stems
        if len(backlinks[s]) == 0 and len(outlinks.get(s, ())) == 0 and is_operational(paths[s])
    ]
    orphans.sort()
    orphan_sample = ", ".join(f"[[{s}]]" for s in orphans[:10])
    orphan_more = f" … +{len(orphans) - 10} more" if len(orphans) > 10 else ""
    orphan_line = (
        f"✅ none in operational dirs" if not orphans
        else f"⚠️ **{len(orphans)}** unlinked: {orphan_sample}{orphan_more}"
    )

    gen = now.strftime("%Y-%m-%d %H:%M %Z")
    health_flag = "🟢" if broken == 0 and miss == 0 else "🔴"
    total_notes = len(stems)

    return f"""{START}
## 🔄 Live Status  *(auto-generated by `tools/index/refresh.py` — do not edit by hand)*

**Generated:** {gen}  ·  {health_flag} link health: {link_body}  ·  tracked surfaces missing: {miss}  ·  vault notes: {total_notes}

### Latest updates (live from PROOF LOG)

{latest_updates()}

### 🕸️ Link graph — what the system sees

**Hubs** (most-linked notes — the real centers of gravity · in·out):

| Note | In | Out | Total |
|---|---|---|---|
{hubs}

**Orphans** (operational notes with no links in *or* out — the system never reaches them): {orphan_line}

### Surface freshness (real mtimes · links in·out)

| Surface | Lane | Last updated (mtime) | in·out | Exists |
|---|---|---|---|---|
{table}
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
