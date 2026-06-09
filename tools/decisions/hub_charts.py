#!/usr/bin/env python3
"""
hub_charts · v1 · 2026-05-31
Render the vault's shape as Mermaid charts so James can see the 'huge brain' at a glance.
Reads concept folders + INTENT RADAR (read-only), writes 00_MEMORY/HUB CHARTS.md.
Native Mermaid (no images). Runs with `fpull`. Invents nothing.
"""
import re, glob, os
from datetime import datetime, timezone
from pathlib import Path

VAULT = Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
CONCEPTS = VAULT / "05_CONCEPTS"
RADAR = VAULT / "00_MEMORY" / "INTENT RADAR.md"
MAPS = VAULT / "04_VISUALS" / "Mindmaps"
OUT = VAULT / "00_MEMORY" / "HUB CHARTS.md"

STREAMS = ["_Foundations", "Treasury", "Ventures", "Game", "Legal", "Zen Village", "Play", "Relationship"]

def main():
    # concepts per stream
    per = {}
    for s in STREAMS:
        d = CONCEPTS / s
        if d.is_dir():
            per[s.lstrip("_")] = len(list(d.glob("*.md")))
    total_c = sum(per.values())
    n_maps = len([p for p in MAPS.glob("*.md") if p.name != "MINDMAPS INDEX.md"]) if MAPS.is_dir() else 0
    n_hubs = len(list((CONCEPTS / "_Hubs").glob("*.md"))) if (CONCEPTS / "_Hubs").is_dir() else 0

    # intent-lane balance
    lanes = {"AI": 0, "Human": 0, "James": 0}
    if RADAR.exists():
        t = RADAR.read_text(errors="ignore")
        for key, pat in (("AI", r"🔵 AI LANE"), ("Human", r"🟡 HUMAN LANE"), ("James", r"🔴 JAMES LANE")):
            m = re.search(pat + r".*?(?=\n## |\Z)", t, re.S)
            if m:
                seg = m.group(0)
                # items = table data rows with a bold entry + numbered list items
                rows = len(re.findall(r"^\|.*\*\*.*\|", seg, re.M))
                nums = len(re.findall(r"^\s*\d+\.\s+\S", seg, re.M))
                lanes[key] = rows + nums

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = ["---", "type: generated", "status: live", f"source: hub_charts · {ts}", "---", "",
         "# 📊 HUB CHARTS", "",
         f"*The brain at a glance · {ts} · re-run `hub_charts.py` (or `fpull`).*", "",
         f"**{total_c} concepts · {n_hubs} hubs · {n_maps} mind maps**", "",
         "## Brain shape — concepts per stream", ""]
    if per:
        L += ["```mermaid", f"pie showData title {total_c} concepts by stream"]
        for k, v in sorted(per.items(), key=lambda x: -x[1]):
            L.append(f'    "{k}" : {v}')
        L.append("```")
    L += ["", "## Where the work sits — intent lanes", ""]
    if sum(lanes.values()):
        L += ["```mermaid", "pie showData title Open intents by lane"]
        for k, v in lanes.items():
            if v:
                L.append(f'    "{k}" : {v}')
        L.append("```")
        L += ["", f"- 🔵 AI: {lanes['AI']} · 🟡 Human: {lanes['Human']} · 🔴 **You: {lanes['James']}** "
              f"({round(100*lanes['James']/max(1,sum(lanes.values())))}% of open work on your plate)"]
    else:
        L.append("*(no lanes parsed)*")
    L += ["", "---", "", "*Embedded in [[INTELLIGENCE HUB]] · full map [[CONCEPTS INDEX]] · system [[ARCHITECTURE MAP]].*", ""]
    OUT.write_text("\n".join(L))
    print(f"hub charts → {OUT.name}  ({total_c} concepts, lanes {lanes})")

if __name__ == "__main__":
    main()
