#!/usr/bin/env python3
"""
local_index_pull · v1 · 2026-05-31  ·  first context-intake pipe

Read-only scan of approved local project folders → a clean, low-cognitive-load
index inside the Obsidian vault. Helps James see what project context exists on
the computer, from inside Obsidian.

  approved local roots (FPAI_Cockpit, fullpotential-ai, SunheartBrainData, vault)
        │  read-only walk · prune noise · flag (never read) sensitive files
        ▼
  vault  00_MEMORY/SOURCE MAP.md     (what was scanned / excluded · the registry)
         00_MEMORY/LOCAL INDEX.md    (the actual folder/file index)

Guarantees:
  - READ-ONLY: never writes, moves, or deletes anything in the scanned roots.
  - NO SECRETS: likely-sensitive files are flagged by NAME only; contents never read.
  - Manual command. No background job.

Usage:
  python3 local_index_pull.py          # scan + write SOURCE MAP.md + LOCAL INDEX.md
  python3 local_index_pull.py --print  # print summary to stdout, write nothing
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()

# Approved roots for this pass (confirmed with James 2026-05-31).
VAULT = HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
ROOTS = [
    HOME / "FPAI_Cockpit",
    HOME / "fullpotential-ai",
    HOME / "SunheartBrainData",
    VAULT,
]

# Broad areas intentionally NOT scanned (require explicit ask to add).
EXCLUDED_BROAD = ["Desktop", "Documents", "Downloads", "Google Drive", "iCloud Drive (other)"]

SOURCE_MAP_FILE = VAULT / "00_MEMORY" / "SOURCE MAP.md"
LOCAL_INDEX_FILE = VAULT / "00_MEMORY" / "LOCAL INDEX.md"

# Directories pruned from the walk (noise / vendored / heavy).
PRUNE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env", "__pycache__",
    ".cache", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    ".next", ".nuxt", "site-packages", ".archive", "backups", ".terraform",
    ".gradle", "target", ".obsidian", ".DS_Store", "wpengine_archive",
}

# Likely-sensitive files — flagged by NAME, contents NEVER read.
SENS_SUFFIXES = (".env", ".token", ".key", ".pem", ".p12", ".pfx", ".keystore",
                 ".kdbx", ".ovpn", ".cer", ".crt")
SENS_SUBSTRINGS = ("cred", "secret", "password", "passwd", "id_rsa", "id_ed25519",
                   ".npmrc", ".pgpass", "apikey", "api_key", "api-key", ".htpasswd",
                   "private_key", "privatekey", ".aws", "token")


def is_sensitive(name: str) -> bool:
    low = name.lower()
    if low.endswith(SENS_SUFFIXES):
        return True
    return any(s in low for s in SENS_SUBSTRINGS)


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n/1:.0f}{unit}" if False else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def scan_root(root: Path) -> dict:
    """Read-only walk with pruning. Returns a summary dict (no file contents)."""
    info = {
        "root": str(root),
        "exists": root.exists(),
        "total_files": 0,
        "total_bytes": 0,
        "subdirs": {},          # top-level subdir name -> file count (recursive, pruned)
        "top_docs": [],         # notable docs at the root level
        "sensitive": [],        # relative paths flagged by name
        "ext_counts": {},       # extension -> count
    }
    if not root.exists():
        return info

    for dirpath, dirnames, filenames in os.walk(root):
        # prune noise + dot-directories in place (keeps the walk fast and readable)
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS and not d.startswith(".")]

        rel = Path(dirpath).relative_to(root)
        top = rel.parts[0] if rel.parts else ""

        for fn in filenames:
            if fn == ".DS_Store":
                continue
            full = Path(dirpath) / fn
            try:
                sz = full.stat().st_size
            except OSError:
                sz = 0
            info["total_files"] += 1
            info["total_bytes"] += sz

            ext = full.suffix.lower() or "(none)"
            info["ext_counts"][ext] = info["ext_counts"].get(ext, 0) + 1

            if top:
                info["subdirs"][top] = info["subdirs"].get(top, 0) + 1

            if is_sensitive(fn):
                info["sensitive"].append(str(full.relative_to(root)))

            # notable docs sitting at the root level
            if rel == Path(".") and (fn.lower().startswith("readme")
                                     or fn.lower().endswith((".md", ".txt"))):
                info["top_docs"].append(fn)

    return info


def render_local_index(scans: list[dict], when: str) -> str:
    out = ["# LOCAL INDEX", "",
           "*Read-only index of approved local project folders. "
           "Sensitive files are flagged by name, never opened. "
           "Re-run `local_index_pull.py` to refresh.*", "",
           f"**Scanned:** {when}", "", "---", ""]

    for s in scans:
        name = Path(s["root"]).name
        out.append(f"## {name}")
        out.append("")
        if not s["exists"]:
            out.append("_(folder not found)_")
            out.append("")
            out.append("---")
            out.append("")
            continue
        out.append(f"`{s['root']}`")
        out.append("")
        out.append(f"- **{s['total_files']:,} files** · {human(s['total_bytes'])}")
        # top extensions
        top_ext = sorted(s["ext_counts"].items(), key=lambda x: -x[1])[:6]
        if top_ext:
            out.append("- File types: " + ", ".join(f"`{e}`×{c}" for e, c in top_ext))
        # top subdirs by file count
        subs = sorted(s["subdirs"].items(), key=lambda x: -x[1])[:20]
        if subs:
            out.append("- Top folders:")
            for d, c in subs:
                out.append(f"    - `{d}/` — {c:,} files")
            if len(s["subdirs"]) > 20:
                out.append(f"    - …and {len(s['subdirs'])-20} more folders")
        # notable docs
        if s["top_docs"]:
            docs = sorted(set(s["top_docs"]))[:12]
            out.append("- Notable docs: " + ", ".join(f"`{d}`" for d in docs))
        # sensitive flags
        sens = s["sensitive"]
        if sens:
            out.append(f"- 🟡 **{len(sens)} likely-sensitive file(s) flagged (not read):**")
            for p in sens[:25]:
                out.append(f"    - 🟡 `{p}`")
            if len(sens) > 25:
                out.append(f"    - 🟡 …and {len(sens)-25} more — left unopened")
        else:
            out.append("- 🟢 No likely-sensitive files detected by name.")
        out.append("")
        out.append("---")
        out.append("")

    return "\n".join(out) + "\n"


def render_source_map(scans: list[dict], when: str) -> str:
    total_files = sum(s["total_files"] for s in scans)
    total_sens = sum(len(s["sensitive"]) for s in scans)
    lines = ["# SOURCE MAP", "",
             "*The registry of what the local scan covers — and what it deliberately "
             "does not. Edit the approved roots only with James's say-so.*", "",
             f"**Generated:** {when}", "", "---", "",
             "## Scanned roots (approved)", ""]
    for s in scans:
        status = "✅" if s["exists"] else "⚠️ missing"
        lines.append(f"- {status} `{s['root']}` — {s['total_files']:,} files")
    lines += ["",
              f"**Totals:** {total_files:,} files indexed · "
              f"🟡 {total_sens} sensitive files flagged (none opened).", "",
              "---", "", "## Excluded for now (require explicit approval)", ""]
    for b in EXCLUDED_BROAD:
        lines.append(f"- ⛔ {b}")
    lines += ["",
              "## Scan rules", "",
              "- Read-only. Never moves, deletes, or edits scanned files.",
              "- Prunes noise: " + ", ".join(f"`{d}`" for d in sorted(PRUNE_DIRS)[:10]) + ", …",
              "- Sensitive files flagged by name (`.env`, `*token*`, `*cred*`, keys, …) — contents never read.",
              "",
              "*See [[LOCAL INDEX]] for the contents · [[PIPELINE MAP]] for how the pipes connect.*",
              ""]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", dest="print_only")
    args = ap.parse_args()

    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    scans = [scan_root(r) for r in ROOTS]

    local_index = render_local_index(scans, when)
    source_map = render_source_map(scans, when)

    if args.print_only:
        print(source_map)
        print(local_index)
        return 0

    LOCAL_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_MAP_FILE.write_text(source_map)
    LOCAL_INDEX_FILE.write_text(local_index)
    tf = sum(s["total_files"] for s in scans)
    ts = sum(len(s["sensitive"]) for s in scans)
    print(f"wrote SOURCE MAP.md + LOCAL INDEX.md · {tf:,} files · {ts} sensitive flagged (not read)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
