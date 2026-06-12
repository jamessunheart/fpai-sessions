#!/usr/bin/env python3
"""
treasury_chart · v1 · 2026-05-31

Read the treasury breakdown from the vault's TREASURY TODAY.md and render it as a
Mermaid pie chart (Obsidian renders Mermaid natively — no image files, no plugins,
stays in version control). The INTELLIGENCE HUB embeds the chart section.

  vault 00_MEMORY/TREASURY TODAY.md  (## Net spendable table — read-only)
        │  parse Banks / Crypto / Bullion $ values
        ▼
  vault 00_MEMORY/TREASURY CHART.md   (Mermaid pie + bars, regenerated each run)

SAFETY: reads one already-safe vault note (no addresses/keys), writes one vault
note. No network, no secrets. Manual; runs with `fpull`. Never invents numbers —
if it can't parse a value it omits it and says so.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

VAULT = Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
SRC = VAULT / "00_MEMORY" / "TREASURY TODAY.md"
OUT = VAULT / "00_MEMORY" / "TREASURY CHART.md"

def parse_k(s):
    m = re.search(r"\$?([\d,]+(?:\.\d+)?)\s*k", s, re.I)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"\$([\d,]+(?:\.\d+)?)", s)
    return float(m.group(1).replace(",", "")) / 1000 if m else None

def main():
    if not SRC.exists():
        print("no TREASURY TODAY.md"); return
    txt = SRC.read_text(errors="ignore")
    buckets = {}
    for label in ("Banks", "Crypto", "Bullion"):
        m = re.search(rf"\|\s*{label}\s*\|([^|]+)\|", txt)
        if m:
            v = parse_k(m.group(1))
            if v is not None:
                buckets[label] = v
    net = re.search(r"Net spendable\*\*\s*\|\s*\*\*~?\$?([\d.,]+)k", txt)
    net_s = f"~${net.group(1)}k" if net else "see TREASURY TODAY"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    L = ["---", "type: generated", "status: live", f"source: treasury_chart · {ts}", "---", "",
         "# 📊 TREASURY CHART", "",
         f"*Auto-rendered from [[TREASURY TODAY]] · {ts}. Re-run `treasury_chart.py` (or `fpull`) to refresh. Mermaid renders in Obsidian natively.*", "",
         "## Allocation", ""]
    if buckets:
        L += ["```mermaid", f"pie showData title Net spendable {net_s}"]
        for k, v in sorted(buckets.items(), key=lambda x: -x[1]):
            L.append(f'    "{k}" : {v}')
        L.append("```")
        L += ["", "## Bars", ""]
        mx = max(buckets.values())
        for k, v in sorted(buckets.items(), key=lambda x: -x[1]):
            bar = "█" * max(1, round(20 * v / mx))
            L.append(f"- `{k:<8}` {bar} ${v:.1f}k")
    else:
        L.append("*(couldn't parse buckets from TREASURY TODAY — left blank, not invented)*")
    L += ["", "---", "", "*Embedded in [[INTELLIGENCE HUB]] · numbers from [[TREASURY TODAY]] (the canonical source).*", ""]
    OUT.write_text("\n".join(L))
    print(f"treasury chart → {OUT.name}  ({', '.join(f'{k} ${v:.1f}k' for k,v in buckets.items()) or 'no buckets'})")

if __name__ == "__main__":
    main()
