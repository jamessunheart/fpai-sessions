#!/usr/bin/env python3
"""The Cartographer v1 — unified map of EVERY territory the substrate owns.

v0 (build_memory_map.py, 2026-06-12 morning) mapped the 305 memory files after
the Camp Zen plan sat invisible during liquidity strategy. The same day's full
system review found the deeper version of the failure: seven indexes, none
joined — vault knowledge, repo state, server truth, and config state were each
invisible to sessions that didn't think to look. James: "deeply review the
entire system ... so that nothing is lost and everything is ready to be fully
utilized."

This walks all territories and emits ONE map, memory/SYSTEM_MAP.md:
  MEMORY   ~/.claude/.../memory/            305 episodic/feedback/project files
  VAULT    ~/Documents/FPOS/Full Potential OS/   519 pages (local git since 2026-06-12)
  REPO     FPAI_Cockpit knowledge layer     core/STATE, docs/codex, BUILD, INTENT
  CONFIG   ~/.config/fpai/                  operational state dirs (pointers, no secrets)
  FLEET    core/STATE/FLEET_SNAPSHOT.md     cached server truth (verified-at dated)

One line per resource: TERRITORY | name | description | path.
Consumed by .claude/hooks/memory-recall.sh — every prompt is keyword-matched
against the whole map, so any resource in any territory can surface.

Also emits a FRESHNESS section: SSOT-grade files past their freshness contract
(per core/STATE/SSOT_REGISTRY.md) are flagged at the top of the map.
"""
import os
import re
import sys
import time
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
MEM_DIR = os.path.join(HOME, ".claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory")
VAULT_DIR = os.path.join(HOME, "Documents/FPOS/Full Potential OS")
VAULT_FALLBACK = os.path.join(
    HOME, "Documents/FPOS/Full Potential OS"
)
REPO_DIR = os.path.join(HOME, "FPAI_Cockpit")
CONFIG_DIR = os.path.join(HOME, ".config/fpai")
MAP_PATH = os.path.join(MEM_DIR, "SYSTEM_MAP.md")

SKIP_FILES = {"MEMORY.md", "MEMORY_MAP.md", "SYSTEM_MAP.md"}
MEM_SKIP_DIRS = {"observations", "background_log"}
VAULT_SKIP_DIRS = {".git", ".obsidian", ".trash"}

# Repo knowledge layer — the index/state/coordination surfaces, not service code.
REPO_KNOWLEDGE = [
    "core/STATE",
    "core/BUILD/SESSION_NOTES",
    "core/BUILD/specs",
    "core/INTENT/SPECS",
    "docs/codex",
    "docs/coordination",
]

# Freshness contracts (days) for SSOT-grade files, per SSOT_REGISTRY.md.
FRESHNESS = {
    "core/STATE/NOW.md": 7,
    "core/STATE/AI_GOALS.md": 14,
    "core/STATE/FLEET_SNAPSHOT.md": 14,
    "core/STATE/HUMAN_EDGE_QUEUE.json": 14,
}


def parse_frontmatter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                m = re.match(r"^\s*(name|description|type)\s*:\s*(.+?)\s*$", line)
                if m:
                    meta[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return meta


def first_meaningful_line(text):
    in_fm = text.startswith("---")
    fm_end = text.find("\n---", 3) + 4 if in_fm else 0
    for line in text[fm_end:].splitlines():
        s = line.strip().lstrip("#").strip()
        if s and not s.startswith(("<!--", "---", "```", "|")):
            return s
    return ""


def clean(s, n=200):
    return re.sub(r"\s+", " ", s or "").replace("|", "/")[:n]


def walk_md(root, skip_dirs, skip_files=frozenset()):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for fname in sorted(files):
            if fname.endswith(".md") and fname not in skip_files:
                yield os.path.join(dirpath, fname)


def read_head(path, n=6000):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(n)
    except OSError:
        return ""


def main():
    lines_by_territory = {}
    counts = {}

    def add(territory, name, desc, path):
        lines_by_territory.setdefault(territory, []).append(
            f"{territory} | {clean(name, 90)} | {clean(desc)} | {path}"
        )
        counts[territory] = counts.get(territory, 0) + 1

    # ── MEMORY ──────────────────────────────────────────────────────
    if os.path.isdir(MEM_DIR):
        for path in walk_md(MEM_DIR, MEM_SKIP_DIRS, SKIP_FILES):
            head = read_head(path)
            meta = parse_frontmatter(head)
            name = meta.get("name") or os.path.splitext(os.path.basename(path))[0]
            desc = meta.get("description") or first_meaningful_line(head) or "(no description)"
            add("memory", name, desc, os.path.relpath(path, MEM_DIR))

    # ── VAULT ───────────────────────────────────────────────────────
    vault = VAULT_DIR if os.path.isdir(VAULT_DIR) else VAULT_FALLBACK
    if os.path.isdir(vault):
        for path in walk_md(vault, VAULT_SKIP_DIRS):
            rel = os.path.relpath(path, vault)
            folder = os.path.dirname(rel) or "root"
            name = os.path.splitext(os.path.basename(path))[0]
            desc = first_meaningful_line(read_head(path, 2500)) or f"vault page in {folder}"
            add("vault", name, f"[{folder}] {desc}", rel)

    # ── REPO knowledge layer ────────────────────────────────────────
    for sub in REPO_KNOWLEDGE:
        root = os.path.join(REPO_DIR, sub)
        if not os.path.isdir(root):
            continue
        for path in walk_md(root, {".git"}):
            rel = os.path.relpath(path, REPO_DIR)
            name = os.path.splitext(os.path.basename(path))[0]
            desc = first_meaningful_line(read_head(path, 2500)) or sub
            add("repo", name, desc, rel)

    # ── CONFIG state dirs (pointers only — never contents/secrets) ──
    if os.path.isdir(CONFIG_DIR):
        for entry in sorted(os.listdir(CONFIG_DIR)):
            full = os.path.join(CONFIG_DIR, entry)
            if os.path.isdir(full):
                try:
                    n = len(os.listdir(full))
                except OSError:
                    n = 0
                add("config", entry, f"operational state dir ({n} entries)", f"~/.config/fpai/{entry}/")

    # ── FLEET (each server gets a greppable line from the snapshot) ─
    fleet_path = os.path.join(REPO_DIR, "core/STATE/FLEET_SNAPSHOT.md")
    if os.path.isfile(fleet_path):
        text = read_head(fleet_path, 20000)
        for m in re.finditer(r"^## (\S+) · ([^\n]+)$", text, re.M):
            ip, label = m.group(1), m.group(2)
            seg_start = m.end()
            nxt = text.find("\n## ", seg_start)
            seg = text[seg_start: nxt if nxt != -1 else len(text)]
            svcs = re.search(r"\*\*(\d+ FP services running:)\*\*([^\n]*)", seg)
            desc = (svcs.group(1) + svcs.group(2)) if svcs else (seg.strip().splitlines()[0] if seg.strip() else label)
            desc = clean(desc, 400)  # fleet lines carry full service rosters — keep them greppable
            add("fleet", f"{ip} {label}", desc, "core/STATE/FLEET_SNAPSHOT.md")

    # ── FRESHNESS check ─────────────────────────────────────────────
    now = time.time()
    stale = []
    for rel, days in FRESHNESS.items():
        p = os.path.join(REPO_DIR, rel)
        if os.path.isfile(p):
            age = (now - os.path.getmtime(p)) / 86400
            if age > days:
                stale.append(f"- 🔴 {rel} — {age:.0f}d old (contract: {days}d). Verify before asserting.")

    # ── Emit ────────────────────────────────────────────────────────
    total = sum(counts.values())
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    out = [
        "# SYSTEM MAP — every territory, one map (auto-generated, do not hand-edit)",
        f"# Generated {stamp} by tools/memory/build_system_map.py · {total} resources",
        f"# Territories: {' · '.join(f'{k}:{v}' for k, v in sorted(counts.items()))}",
        "# One line per resource: TERRITORY | name | description | path",
        "# SSOT designations + conflict rules: core/STATE/SSOT_REGISTRY.md",
        "",
    ]
    if stale:
        out += ["## ⚠ STALE SSOTs (past freshness contract)"] + stale + [""]
    for territory in ("memory", "vault", "repo", "config", "fleet"):
        if territory in lines_by_territory:
            out.append(f"## {territory.upper()} ({counts[territory]})")
            out.extend(sorted(lines_by_territory[territory]))
            out.append("")

    with open(MAP_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"SYSTEM_MAP.md written: {total} resources ({', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}), {len(stale)} stale SSOTs")


if __name__ == "__main__":
    sys.exit(main())
