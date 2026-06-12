#!/usr/bin/env python3
"""
concept_surfacer · v1 · 2026-05-31

Proactively surface the concepts most relevant to James RIGHT NOW.
Reads the live state notes (already-safe vault mirrors), scores every concept
in 05_CONCEPTS against that signal, and writes the top few — with a reason —
into the vault so the INTELLIGENCE HUB can surface them.

  vault 00_MEMORY/{INTENT RADAR, NEXT ACTION, NOW MIRROR, TREASURY TODAY,
                   GOALS MIRROR, COMMS INBOX, SCENES}.md   (read-only signal)
  vault 05_CONCEPTS/**/*.md                                 (the 261 concepts)
        │  term-frequency relevance scoring + verbatim title/alias match
        ▼
  vault 00_MEMORY/SURFACED CONCEPTS.md   (top N + why-surfaced)

SAFETY: reads already-redacted vault notes only; writes one vault note. No
secrets, no network, no background job. Manual command, like the other pulls.

Usage:
  python3 concept_surfacer.py            # write SURFACED CONCEPTS.md
  python3 concept_surfacer.py --print    # print, write nothing
  python3 concept_surfacer.py --top 8    # how many to surface (default 7)
"""
import argparse, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
VAULT = HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
MEM = VAULT / "00_MEMORY"
CONCEPTS = VAULT / "05_CONCEPTS"
OUT = MEM / "SURFACED CONCEPTS.md"

# state notes → weight (higher = stronger pull on what's surfaced)
SIGNALS = {
    "INTENT RADAR.md": 3, "NEXT ACTION.md": 3, "COMMS INBOX.md": 3,
    "NOW MIRROR.md": 2, "GOALS MIRROR.md": 2, "TREASURY TODAY.md": 1, "SCENES.md": 1,
}
STOP = set("""the a an and or of to in is it for on with as at by be are was this that these those
your you our we us i me my his her their they them from into out up down over under not no yes
will would can could should may might do does did has have had been being more most very just
than then so if but about also which who what when where how why all any each only own same
system systems ai james sunheart concept concepts note notes vault stream streams now today live
make makes made get gets got use uses using need needs want wants like via per etc one two via
full potential thing things move moves work works build builds building lane value""".split())

def words(t):
    return [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", t.lower()) if w not in STOP]

def load_concepts():
    out = []
    for p in CONCEPTS.rglob("*.md"):
        name = p.stem
        if name in ("CONCEPTS INDEX", "SIX SEEDS") or p.parent.name == "_Hubs":
            continue
        t = p.read_text(errors="ignore")
        al = re.search(r"^aliases:\s*\[(.+?)\]", t, re.M)
        aliases = [a.strip() for a in al.group(1).split(",")] if al else []
        body = re.sub(r"^---.*?---", "", t, flags=re.S)
        out.append({"name": name, "aliases": aliases, "title_terms": set(words(name)),
                    "body_terms": Counter(words(body))})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="pr", action="store_true")
    ap.add_argument("--top", type=int, default=7)
    a = ap.parse_args()

    sig = Counter()
    sig_text = ""
    present = []
    for fn, w in SIGNALS.items():
        f = MEM / fn
        if not f.exists():
            continue
        txt = f.read_text(errors="ignore")
        present.append(fn.replace(".md", ""))
        sig_text += " " + txt.lower()
        for term, c in Counter(words(txt)).items():
            sig[term] += c * w

    # latest daily workspace note = strong signal for what James is working on now
    daily_dir = VAULT / "07_DAILY"
    if daily_dir.is_dir():
        dailies = sorted(p for p in daily_dir.glob("*.md") if not p.name.startswith("_"))
        if dailies:
            txt = dailies[-1].read_text(errors="ignore")
            present.append("DAILY:" + dailies[-1].stem)
            sig_text += " " + txt.lower()
            for term, c in Counter(words(txt)).items():
                sig[term] += c * 3

    concepts = load_concepts()
    scored = []
    for c in concepts:
        score = 0.0
        why = Counter()
        verbatim = c["name"].lower() in sig_text or any(al.lower() in sig_text for al in c["aliases"])
        if verbatim:
            score += 40
        for term, sf in sig.items():
            if term in c["title_terms"]:
                score += 6 * sf; why[term] += 6 * sf
            elif term in c["body_terms"]:
                add = min(c["body_terms"][term], 3) * sf * 0.5
                score += add; why[term] += add
        if score > 0:
            top_terms = [t for t, _ in why.most_common(3)]
            scored.append((score, c["name"], verbatim, top_terms))
    scored.sort(key=lambda x: -x[0])
    top = scored[: a.top]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["---", "type: generated", "status: live", f"source: concept_surfacer · {ts}", "---", "",
             "# 🌱 SURFACED CONCEPTS", "",
             "*Auto-ranked by relevance to your live state (intents · next action · comms · treasury · now). "
             "Generated — re-run `concept_surfacer.py` to refresh. Surfaced so the most useful ideas reach awareness without you hunting.*", "",
             f"**Signal from:** {' · '.join(present)}", "", "## Top surfaced", ""]
    if not top:
        lines.append("*(no signal yet — populate the state notes / inbox, then re-run)*")
    for i, (sc, name, vb, terms) in enumerate(top, 1):
        flag = " · 🔗 named in your live state" if vb else ""
        why = ", ".join(terms) if terms else "thematic overlap"
        lines.append(f"{i}. [[{name}]] — _why:_ {why}{flag}")
    lines += ["", "---", "", "*Surfaced into [[INTELLIGENCE HUB]] · full map [[CONCEPTS INDEX]] · gestalt [[SIX SEEDS]]*", ""]
    out = "\n".join(lines)
    if a.pr:
        print(out)
    else:
        OUT.write_text(out)
        print(f"surfaced {len(top)} concepts → {OUT.name}  (signal: {', '.join(present)})")

if __name__ == "__main__":
    main()
