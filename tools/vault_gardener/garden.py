#!/usr/bin/env python3
"""
Vault Gardener — nightly hygiene for the FPOS Obsidian vault (readable brain mirror).
Martell stage 6 ("Compound the Brain") applied to the vault specifically:
the substrate self-compounds (HOT_STATE, build loop) but the readable mirror did not.

REPORT-ONLY by default (safe). It never edits/deletes notes — it writes a dated
report and, if `claude` CLI is on PATH, appends an AI review. James reads the report,
then decides what to action. Set GARDEN_APPLY=1 later to allow light auto-fixes.

Run: python3 garden.py   (or via the launchd job com.fpai.vault-gardener, nightly)
$0 — uses the `claude` CLI (Max subscription), no metered API.
"""
import os, re, sys, subprocess, datetime, collections

VAULT = os.path.expanduser("~/Documents/FPOS/Full Potential OS")
REPORT_DIR = os.path.join(VAULT, "00_MEMORY")
LINK_RE = re.compile(r"\[\[([^\]|#]+)")

def md_files():
    out = []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in (".obsidian", ".git", "_archive")]
        for f in files:
            if f.endswith(".md"):
                out.append(os.path.join(root, f))
    return out

def stem(path):
    return os.path.splitext(os.path.basename(path))[0]

def main():
    # date via env (scripts must not call datetime.now under the harness cron? fine locally)
    today = datetime.date.today().isoformat()
    files = md_files()
    stems = {stem(p): p for p in files}

    # inbound link map
    inbound = collections.defaultdict(int)
    for p in files:
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for m in LINK_RE.findall(txt):
            inbound[m.strip()] += 1

    # orphans: notes nothing links to (skip hubs/templates/daily/index by convention)
    def is_infra(s):
        low = s.lower()
        return any(k in low for k in ("hub", "template", "index", "moc", "home", "start here", "readme")) \
            or re.match(r"\d{4}-\d{2}-\d{2}", s)
    orphans = sorted(s for s in stems if inbound.get(s, 0) == 0 and not is_infra(s))

    # near-duplicate filenames (same normalized stem)
    norm = collections.defaultdict(list)
    for s in stems:
        key = re.sub(r"[^a-z0-9]", "", s.lower())
        norm[key].append(s)
    dupes = {k: v for k, v in norm.items() if len(v) > 1}

    # notes touched today
    touched = []
    for p in files:
        try:
            mt = datetime.date.fromtimestamp(os.path.getmtime(p)).isoformat()
            if mt == today:
                touched.append(stem(p))
        except Exception:
            pass

    touched_lines = [f"- [[{t}]]" for t in sorted(touched)[:40]] or ["- (none)"]
    orphan_lines = [f"- [[{o}]]" for o in orphans[:40]]
    if len(orphans) > 40:
        orphan_lines.append(f"- …and {len(orphans)-40} more")
    dupe_lines = [f"- {' · '.join('[['+x+']]' for x in v)}" for v in list(dupes.values())[:20]] or ["- (none)"]

    lines = [
        f"# 🌱 Vault Garden Log — {today}",
        "",
        f"_Auto-run by the Vault Gardener (report-only). {len(files)} notes scanned._",
        "",
        f"## Touched today ({len(touched)})",
        *touched_lines,
        "",
        f"## Orphans — nothing links to these ({len(orphans)})",
        "_Candidates to link into a hub/MOC or archive._",
        *orphan_lines,
        "",
        f"## Possible duplicate filenames ({len(dupes)})",
        *dupe_lines,
        "",
    ]
    report = "\n".join(l for l in lines if l != "")

    # optional AI pass via claude CLI ($0) — summarize + suggest MOC updates
    ai = ""
    try:
        prompt = ("You are the FPOS vault gardener. Below is tonight's mechanical scan. "
                  "In <=8 bullets: which orphans clearly belong under which existing hub, "
                  "which duplicates should merge, and the single highest-value cleanup. "
                  "Be terse.\n\n" + report)
        r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=180)
        if r.returncode == 0 and r.stdout.strip():
            ai = "\n## 🤖 AI review\n\n" + r.stdout.strip() + "\n"
    except Exception as e:
        ai = f"\n## 🤖 AI review\n\n_(claude CLI unavailable: {e})_\n"

    os.makedirs(REPORT_DIR, exist_ok=True)
    out_path = os.path.join(REPORT_DIR, "VAULT GARDEN LOG.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report + ai)
    print(f"garden: wrote {out_path} — {len(orphans)} orphans, {len(dupes)} dupe-sets, {len(touched)} touched")

if __name__ == "__main__":
    main()
