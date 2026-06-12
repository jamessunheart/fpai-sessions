#!/usr/bin/env python3
"""
scout_adopt · v2 · 2026-05-31  ·  graded recursive self-improvement loop
Reads AI GROWTH FEED proposals. Each carries a **Score** line + verdict tier (see ADOPTION RUBRIC):
  🔵 AUTO  → route automatically (reversible build queued; no tap needed)
  🟡 TAP   → route only if James tapped `[x] adopt`
Routing = spec stub in 02_SPECS + intent in INTENT RADAR + mark queued in feed + PROOF.
Deterministic, file-only, no build executed (queue only). When James's tap disagrees with
the rubric, append a CALIBRATION row to ADOPTION RUBRIC. Runs with `fpull`.
"""
import re, datetime
from pathlib import Path

VAULT = Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
FEED = VAULT / "00_MEMORY" / "AI GROWTH FEED.md"
RADAR = VAULT / "00_MEMORY" / "INTENT RADAR.md"
SPECS = VAULT / "02_SPECS"
PROOF = VAULT / "00_MEMORY" / "PROOF LOG.md"
RUBRIC = VAULT / "00_MEMORY" / "ADOPTION RUBRIC.md"

def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]

def main():
    if not FEED.exists(): print("no feed"); return
    t = FEED.read_text(errors="ignore")
    try:
        start = t.index("## ⚙️ Proposed adoptions"); end = t.index("## 🔭 Scanned")
    except ValueError:
        print("no proposed-adoptions section"); return
    sec = t[start:end]
    blocks = re.split(r"\n- \*\*", sec)
    queued, calib = [], []
    for b in blocks[1:]:
        name = b.split("**", 1)[0].strip()
        if "✅ queued" in b: continue
        score = int((re.search(r"=\s*(\d+)\s*/\s*15", b) or [None, "0"])[1])
        gate_clear = "gate ✅" in b  # 🟡/🔴 gate → tripped → can't AUTO regardless of score
        # verdict derived from score + gate (code is source of truth · AUTO bar = 10):
        AUTO_BAR = 10
        verdict = "AUTO" if (score >= AUTO_BAR and gate_clear) else ("TAP" if score >= 8 else "WATCH")
        tapped = bool(re.search(r"- \[x\] \*\*adopt\*\*", b, re.I))
        route = (verdict == "AUTO") or tapped
        if not route: continue
        # calibration: James tapped something the rubric did NOT auto-adopt → disagreement signal
        if tapped and verdict != "AUTO":
            calib.append((name, f"{verdict} (score {score})", "tapped adopt", "James adopts faster than rubric — consider raising leverage weight"))
        why = (re.search(r"Why it matters[^:]*:\*\*\s*(.+?)(?:\*\*Proposed|→|\n)", b, re.S) or [None, ""])[1].strip()[:300]
        use = (re.search(r"Proposed use[:\*]*\s*(.+?)(?:→|—|verdict|\n)", b, re.S) or [None, ""])[1].strip()[:300]
        link = (re.search(r"(https?://\S+)", b) or [None, ""])[1]
        sg = slug(name)
        (SPECS / f"SPEC_adopt-{sg}.md").write_text(
            f"---\ntype: spec\nstatus: queued (scout-adopted · {verdict})\nsource: AI GROWTH FEED · {datetime.date.today().isoformat()}\n---\n\n"
            f"# Adopt: {name}\n\n**Rubric:** score {score}/15 · verdict {verdict}\n\n**Why:** {why}\n\n**Proposed use:** {use}\n\n**Source:** {link}\n\n"
            f"**Definition of done:** evaluate + integrate (or prototype) the proposed use; reversible; proof in [[PROOF LOG]].\n"
            f"**Who:** Codex (build) / AI(Ember) (light integration). One spec = one branch.\n")
        queued.append((name, verdict, score))
    if not queued:
        print("no items to route (no AUTO, none tapped)"); return
    # route to INTENT RADAR
    r = RADAR.read_text(errors="ignore")
    line = "".join(f"\n- ⚙️ **ADOPT: {n}** ({v} · {s}/15) — scout-graded upgrade → SPEC_adopt-{slug(n)} (Codex/Ember)" for n, v, s in queued)
    if "AI AUTOMATION CANDIDATES" in r:
        r = re.sub(r"(## ⚙️ AI AUTOMATION CANDIDATES[^\n]*\n)", r"\1" + line + "\n", r, count=1)
    else:
        r += "\n" + line + "\n"
    RADAR.write_text(r)
    # mark each routed item queued in feed — AUTO has no checkbox (append to its Score line);
    # TAP has a checkbox (replace it). Anchor strictly inside the named item's own block.
    for n, v, s in queued:
        sg = slug(n)
        if v == "AUTO":
            # append the queued marker to this item's Score line (the one without an existing marker)
            pat = re.compile(r"(\*\*" + re.escape(n) + r"\*\*.*?→ 🔵 \*\*AUTO\*\*)(?! · ✅)", re.S)
            t = pat.sub(lambda m: m.group(1) + f" · ✅ queued → SPEC_adopt-{sg}", t, count=1)
        else:
            pat = re.compile(r"(\*\*" + re.escape(n) + r"\*\*.*?)- \[[ x]\] \*\*adopt\*\*[^\n]*", re.S)
            t = pat.sub(lambda m: m.group(1) + f"- [x] **adopt** ✅ queued ({v}) → SPEC_adopt-{sg}", t, count=1)
    FEED.write_text(t)
    # proof
    auto = [n for n, v, s in queued if v == "AUTO"]; tap = [n for n, v, s in queued if v != "AUTO"]
    pr = PROOF.read_text(errors="ignore")
    e = (f"- **{datetime.date.today().isoformat()}** · [Game] · **Scout-adopt routed {len(queued)}** "
         f"(graded by [[ADOPTION RUBRIC]]): AUTO={auto or '—'} · TAP={tap or '—'} → spec stubs + intents. "
         f"Obvious wins routed themselves; judgment calls waited for the tap. · AI(Ember)\n")
    PROOF.write_text(pr.replace("## 2026\n", "## 2026\n\n" + e, 1))
    # calibration rows
    if calib and RUBRIC.exists():
        rt = RUBRIC.read_text(errors="ignore")
        rows = "".join(f"| {datetime.date.today().isoformat()} | {n} | {said} | {did} | {lesson} |\n" for n, said, did, lesson in calib)
        rt = rt.replace("| 2026-05-31 | (baseline — rubric goes live) | — | — | start tracking |\n",
                        "| 2026-05-31 | (baseline — rubric goes live) | — | — | start tracking |\n" + rows, 1)
        RUBRIC.write_text(rt)
    print(f"routed {len(queued)}: AUTO={auto} TAP={tap}")

if __name__ == "__main__":
    main()
