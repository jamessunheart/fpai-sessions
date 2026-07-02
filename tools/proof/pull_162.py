#!/usr/bin/env python3
"""
proof_pull · pulls REAL execution proof from 162's build loop into James's readable surfaces.

Root cause this fixes (found 2026-07-02): execution moved server-side on 2026-06-14
(laptop-free build loop) but PROOF LOG + BUILDSTREAM BOARD were only written by
laptop sessions — so they went dark on ~June 5 while 244 build commits landed on 162.

Reads:  ssh 162 → git log feat/headless-build (build/merge/feat commits)
Writes: vault 06_RESULTS/PROOF LOG.md          (appends new entries, dedup by hash)
        vault 02_CONTEXT/Memory/BUILDSTREAM BOARD.md  (rewritten: live board)
State:  ~/.config/fpai/proof_pull/seen_hashes.txt
Run:    part of fpull · safe to run any time · read-only on 162.
"""
import os, re, subprocess, datetime
from pathlib import Path

VAULT = Path(os.environ.get("FPAI_VAULT", Path.home() / "Documents" / "FPOS" / "Full Potential OS"))
PROOF = VAULT / "06_RESULTS" / "PROOF LOG.md"
BOARD = VAULT / "02_CONTEXT/Memory" / "BUILDSTREAM BOARD.md"
STATE_DIR = Path.home() / ".config" / "fpai" / "proof_pull"
SEEN = STATE_DIR / "seen_hashes.txt"
HOST = "root@162.0.208.88"
REPO = "/opt/fpai-build/FPAI_Cockpit"
SINCE = "2026-06-05"  # backfill horizon; dedup makes re-runs cheap

def sh(cmd, timeout=25):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip()

def fetch_commits():
    out = sh(f"ssh -o ConnectTimeout=10 {HOST} 'cd {REPO} && git log feat/headless-build "
             f"--pretty=\"%h|%ad|%s\" --date=short --since={SINCE}'")
    rows = []
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        h, d, s = parts
        if re.match(r"(build\(|Merge branch 'build/|Merge d\d|feat\(|fix\()", s):
            rows.append((h, d, s))
    return rows

def nice(subject):
    m = re.match(r"build\(SPEC_(d?\w+)_([^)]+)\): server build loop", subject)
    if m:
        return f"`{m.group(1)}` {m.group(2).replace('-', ' ')}"
    m = re.match(r"Merge branch 'build/SPEC_(d?\w+)_([^']+)'", subject)
    if m:
        return f"`{m.group(1)}` {m.group(2).replace('-', ' ')} — MERGED"
    return subject

def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    seen = set(SEEN.read_text().split()) if SEEN.exists() else set()
    rows = fetch_commits()
    if not rows:
        print("proof_pull: 162 unreachable or no commits"); return
    fresh = [(h, d, s) for h, d, s in rows if h not in seen]

    # ---- PROOF LOG: append fresh entries under the header (newest-first file) ----
    if fresh and PROOF.exists():
        txt = PROOF.read_text()
        by_day = {}
        for h, d, s in fresh:
            by_day.setdefault(d, []).append(nice(s))
        block_lines = []
        for d in sorted(by_day, reverse=True):
            items = by_day[d]
            head = items[:8]
            more = f" · +{len(items)-8} more" if len(items) > 8 else ""
            block_lines.append(f"- **{d}** · [Game/Build] · 162 build loop: " + " · ".join(head) + more + " · AI(build-loop)")
        block = "\n".join(block_lines) + "\n"
        # insert after the first "---" following the title/intro (before first existing entry)
        m = re.search(r"^- \*\*20", txt, re.M)
        txt = (txt[:m.start()] + block + txt[m.start():]) if m else txt + "\n" + block
        PROOF.write_text(txt)
    for h, _, _ in fresh:
        seen.add(h)
    SEEN.write_text("\n".join(sorted(seen)))

    # ---- BUILDSTREAM BOARD: rewrite as a live board ----
    now = datetime.date.today().isoformat()
    recent = [r for r in rows if r[1] >= (datetime.date.today() - datetime.timedelta(days=14)).isoformat()]
    lines = ["---", "type: generated", "status: live", f"source: proof_pull · {now} · 162 feat/headless-build", "---", "",
             "# 🚦 BUILDSTREAM BOARD",
             "",
             f"*Live from 162's build loop (auto-refreshed by `proof_pull` via fpull). {len(rows)} build/merge commits since {SINCE}.*",
             "",
             f"## Merged / built — last 14 days ({len(recent)})", ""]
    for h, d, s in recent[:40]:
        lines.append(f"- `{d}` {nice(s)}")
    lines += ["", "## Where the rest lives",
              "- Full history: `git log feat/headless-build` on 162",
              "- Decisions/status DB: `brain_index.decisions` · surfaced in [[HOT STATE]]",
              "- Shipped record: [[PROOF LOG]]", ""]
    BOARD.write_text("\n".join(lines))
    print(f"proof_pull: {len(fresh)} new proof entries · board rebuilt ({len(recent)} recent)")

if __name__ == "__main__":
    main()
